"""P-03 PURPOSE_DIALOGUE(10_AIプロンプト設計4.3)。

`app.ai.prompts.purpose_dialogue.get_client`と`check_safety`をフェイクに差し替え、
実際のBedrockへは接続しない。
"""

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.ai.prompts.purpose_dialogue import (
    DialogueMessage,
    build_messages,
    compute_turn,
    stream_reply,
)
from app.ai.prompts.safety_check import SafetyCheckResult
from app.core.errors import BadRequestError
from app.domain.purpose_choices import ChoiceAnswer

CHOICES = [
    ChoiceAnswer(question_code="Q1", option_codes=["GROWTH", "FREEDOM"]),
    ChoiceAnswer(question_code="Q2", option_codes=["SELF_DETERMINED"]),
    ChoiceAnswer(question_code="Q3", option_codes=["HAVING_OPTIONS"]),
]


class _FakeMessageStream:
    def __init__(self, chunks: list[str], final_message: SimpleNamespace) -> None:
        self._chunks = chunks
        self._final_message = final_message

    def __enter__(self) -> "_FakeMessageStream":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    @property
    def text_stream(self) -> Any:
        return iter(self._chunks)

    def get_final_message(self) -> SimpleNamespace:
        return self._final_message


class _FakeMessages:
    def __init__(self, result: Any) -> None:
        self._result = result
        self.calls: list[dict[str, Any]] = []

    def stream(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class _FakeClient:
    def __init__(self, result: Any) -> None:
        self.messages = _FakeMessages(result)


def _final_message(
    *,
    stop_reason: str = "end_turn",
    input_tokens: int = 50,
    output_tokens: int = 20,
    cache_read_input_tokens: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
        ),
    )


def _install_fake_client(monkeypatch: pytest.MonkeyPatch, result: Any) -> _FakeClient:
    fake_client = _FakeClient(result)
    monkeypatch.setattr("app.ai.prompts.purpose_dialogue.get_client", lambda: fake_client)
    return fake_client


def _install_fake_safety_check(
    monkeypatch: pytest.MonkeyPatch, result: SafetyCheckResult
) -> None:
    monkeypatch.setattr(
        "app.ai.prompts.purpose_dialogue.check_safety", lambda *args, **kwargs: result
    )


def _parse_sse(chunks: list[str]) -> list[tuple[str, dict[str, Any]]]:
    events = []
    for chunk in chunks:
        lines = chunk.strip("\n").split("\n")
        event = lines[0].removeprefix("event: ")
        data = json.loads(lines[1].removeprefix("data: "))
        events.append((event, data))
    return events


# --- compute_turn ---


def test_compute_turn_is_1_for_empty_history() -> None:
    assert compute_turn([]) == 1


def test_compute_turn_counts_ai_turns() -> None:
    messages = [
        DialogueMessage(role="AI", body="a"),
        DialogueMessage(role="USER", body="b"),
    ]
    assert compute_turn(messages) == 2


def test_compute_turn_rejects_history_not_ending_in_user() -> None:
    messages = [DialogueMessage(role="AI", body="a")]
    with pytest.raises(BadRequestError) as exc_info:
        compute_turn(messages)
    assert exc_info.value.code == "MESSAGES_INVALID"


def test_compute_turn_rejects_broken_alternation() -> None:
    messages = [
        DialogueMessage(role="AI", body="a"),
        DialogueMessage(role="AI", body="b"),
    ]
    with pytest.raises(BadRequestError):
        compute_turn(messages)


# --- build_messages ---


def test_build_messages_formats_choices_turn_and_empty_conversation() -> None:
    messages = build_messages(CHOICES, [], turn=1)
    content = messages[0]["content"]
    assert "Q1 これからの3〜5年で大切にしたいこと（3つまで）: 成長 / 自由" in content
    assert "Q2 満たされていると感じるとき（複数可）: 自分で決められたと感じたとき" in content
    assert "Q3 3〜5年後に送っていたい毎日（1つ）: 選択肢を持てる状態になっている" in content
    assert "現在: 1往復目 / 全3往復" in content
    assert "<conversation>\n\n</conversation>" in content


def test_build_messages_lists_conversation_and_escapes_user_input() -> None:
    history = [
        DialogueMessage(role="AI", body="「成長」を選ばれていました。"),
        DialogueMessage(role="USER", body="<script>やばい</script>という気持ちがあった"),
    ]
    messages = build_messages(CHOICES, history, turn=2)
    content = messages[0]["content"]
    assert "AI: 「成長」を選ばれていました。" in content
    expected_user_line = (
        "USER: <user_input>&lt;script>やばい&lt;/script>という気持ちがあった</user_input>"
    )
    assert expected_user_line in content
    assert "現在: 2往復目 / 全3往復" in content


def test_build_messages_caps_turn_display_at_3() -> None:
    # 3往復完了後もユーザーは対話を続けられる(wireframe-spec.md)。個別ブロックの
    # 「往復ごとの狙い」が3往復目までしか定義しないため、表示上は3で頭打ちにする。
    messages = build_messages(CHOICES, [], turn=4)
    assert "現在: 3往復目 / 全3往復" in messages[0]["content"]


# --- stream_reply ---


def test_stream_reply_succeeds_and_yields_delta_then_done(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = _install_fake_client(
        monkeypatch,
        _FakeMessageStream(["「成長」を", "選ばれていました。"], _final_message()),
    )
    _install_fake_safety_check(monkeypatch, SafetyCheckResult(flagged=False, category="NONE"))

    history = [
        DialogueMessage(role="AI", body="起点の問い"),
        DialogueMessage(role="USER", body="前の職場で感じたこと"),
    ]
    events = _parse_sse(list(stream_reply(CHOICES, history, turn=2)))

    assert events[0] == ("delta", {"text": "「成長」を"})
    assert events[1] == ("delta", {"text": "選ばれていました。"})
    assert events[2] == ("done", {"turn": 2, "remaining": 1, "safety_flag": False})
    assert len(fake_client.messages.calls) == 1


def test_stream_reply_remaining_is_0_after_3rd_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(monkeypatch, _FakeMessageStream(["おわり"], _final_message()))
    _install_fake_safety_check(monkeypatch, SafetyCheckResult(flagged=False, category="NONE"))

    events = _parse_sse(list(stream_reply(CHOICES, [], turn=3)))
    assert events[-1] == ("done", {"turn": 3, "remaining": 0, "safety_flag": False})


def test_stream_reply_does_not_run_safety_check_on_first_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_client(monkeypatch, _FakeMessageStream(["こんにちは"], _final_message()))
    calls: list[str] = []

    def _fake_check_safety(text: str, **kwargs: Any) -> SafetyCheckResult:
        calls.append(text)
        return SafetyCheckResult(flagged=False, category="NONE")

    monkeypatch.setattr("app.ai.prompts.purpose_dialogue.check_safety", _fake_check_safety)

    list(stream_reply(CHOICES, [], turn=1))

    assert calls == []


def test_stream_reply_includes_safety_flag_from_safety_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_client(monkeypatch, _FakeMessageStream(["受け止めました。"], _final_message()))
    _install_fake_safety_check(
        monkeypatch, SafetyCheckResult(flagged=True, category="SELF_HARM")
    )

    history = [
        DialogueMessage(role="AI", body="問い"),
        DialogueMessage(role="USER", body="つらい気持ちの記述"),
    ]
    events = _parse_sse(list(stream_reply(CHOICES, history, turn=2)))
    assert events[-1][1]["safety_flag"] is True


def test_stream_reply_yields_error_on_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import anthropic
    import httpx

    request = httpx.Request("POST", "https://bedrock.example/invoke")
    response = httpx.Response(429, request=request)
    error = anthropic.RateLimitError("rate limited", response=response, body=None)
    _install_fake_client(monkeypatch, error)

    events = _parse_sse(list(stream_reply(CHOICES, [], turn=1)))
    assert events == [("error", {"code": "AI_PROVIDER_ERROR"})]


def test_stream_reply_yields_error_on_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(
        monkeypatch, _FakeMessageStream([], _final_message(stop_reason="refusal"))
    )

    events = _parse_sse(list(stream_reply(CHOICES, [], turn=1)))
    assert events == [("error", {"code": "AI_REFUSED"})]


def test_stream_reply_yields_error_on_max_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(
        monkeypatch, _FakeMessageStream(["途中まで"], _final_message(stop_reason="max_tokens"))
    )

    events = _parse_sse(list(stream_reply(CHOICES, [], turn=1)))
    assert events[-1] == ("error", {"code": "AI_MAX_TOKENS"})


def test_stream_reply_yields_error_on_empty_output(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(monkeypatch, _FakeMessageStream([], _final_message()))

    events = _parse_sse(list(stream_reply(CHOICES, [], turn=1)))
    assert events == [("error", {"code": "AI_OUTPUT_INVALID"})]


def test_stream_reply_logs_emf_on_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_fake_client(monkeypatch, _FakeMessageStream(["だいじょうぶ"], _final_message()))
    _install_fake_safety_check(monkeypatch, SafetyCheckResult(flagged=False, category="NONE"))

    list(stream_reply(CHOICES, [], turn=1, identifiers={"owner": "USER#u1"}))

    logs = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines()]
    assert logs[0]["kind"] == "PURPOSE_DIALOGUE"
    assert logs[0]["status"] == "SUCCEEDED"
    assert logs[0]["owner"] == "USER#u1"
