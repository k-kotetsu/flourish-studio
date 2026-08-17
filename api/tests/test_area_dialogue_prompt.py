"""P-05 AREA_DIALOGUE(10_AIプロンプト設計4.5)。

`app.ai.prompts.area_dialogue.get_client`と`check_safety`をフェイクに差し替え、
実際のBedrockへは接続しない。`compute_turn`・`build_conversation_block`は
`purpose_dialogue`側のテストで既に確認済みのため、ここでは再確認しない。
"""

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.ai.prompts.area_dialogue import build_messages, stream_reply
from app.ai.prompts.purpose_dialogue import DialogueMessage
from app.ai.prompts.safety_check import SafetyCheckResult
from app.domain.area_choices import ChoiceAnswer

CHOICES = [
    ChoiceAnswer(question_code="Q1", option_codes=["CAREER_OUTLOOK"]),
    ChoiceAnswer(
        question_code="Q2", option_codes=["CAREER_VALUE_GROWTH", "CAREER_VALUE_AUTONOMY"]
    ),
    ChoiceAnswer(question_code="Q3", option_codes=["CAREER_POSITION_GROWTH"]),
]
PURPOSE_STATEMENT = "まわりの人が安心して力を出せる存在でありたい。"


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
    monkeypatch.setattr("app.ai.prompts.area_dialogue.get_client", lambda: fake_client)
    return fake_client


def _install_fake_safety_check(
    monkeypatch: pytest.MonkeyPatch, result: SafetyCheckResult
) -> None:
    monkeypatch.setattr(
        "app.ai.prompts.area_dialogue.check_safety", lambda *args, **kwargs: result
    )


def _parse_sse(chunks: list[str]) -> list[tuple[str, dict[str, Any]]]:
    events = []
    for chunk in chunks:
        lines = chunk.strip("\n").split("\n")
        event = lines[0].removeprefix("event: ")
        data = json.loads(lines[1].removeprefix("data: "))
        events.append((event, data))
    return events


# --- build_messages ---


def test_build_messages_includes_purpose_area_choices_and_turn() -> None:
    messages = build_messages(PURPOSE_STATEMENT, "CAREER", CHOICES, [], turn=1)
    content = messages[0]["content"]
    assert f"確定した「ありたい姿」: {PURPOSE_STATEMENT}" in content
    assert "対象領域: Career（仕事・働き方）" in content
    assert "Q1 3〜5年後にいちばん変わっていてほしいこと（1つ）: 今後のキャリアの見通し" in content
    assert "Q2 これからの仕事で特に大切にしたいこと（複数）:" in content
    assert "自分の成長を実感できること / 自分で決められる裁量があること" in content
    assert "現在: 1往復目 / 全2往復" in content
    assert "<conversation>\n\n</conversation>" in content


def test_build_messages_escapes_purpose_statement() -> None:
    messages = build_messages("<script>やばい</script>", "CAREER", CHOICES, [], turn=1)
    content = messages[0]["content"]
    assert "<script>" not in content
    assert "&lt;script>やばい&lt;/script>" in content


def test_build_messages_caps_turn_display_at_2() -> None:
    # 2往復完了後もユーザーは対話を続けられる(purpose_dialogueと同じ判断)。
    messages = build_messages(PURPOSE_STATEMENT, "CAREER", CHOICES, [], turn=3)
    assert "現在: 2往復目 / 全2往復" in messages[0]["content"]


def test_build_messages_lists_conversation_history() -> None:
    history = [
        DialogueMessage(role="AI", body="「今後のキャリアの見通し」を選ばれていました。"),
        DialogueMessage(role="USER", body="前の職場で感じたことがあった"),
    ]
    messages = build_messages(PURPOSE_STATEMENT, "CAREER", CHOICES, history, turn=2)
    content = messages[0]["content"]
    assert "AI: 「今後のキャリアの見通し」を選ばれていました。" in content
    assert "USER: <user_input>前の職場で感じたことがあった</user_input>" in content


# --- stream_reply ---


def test_stream_reply_succeeds_and_yields_delta_then_done(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = _install_fake_client(
        monkeypatch,
        _FakeMessageStream(["ありたい姿に", "つながっていますね。"], _final_message()),
    )
    _install_fake_safety_check(monkeypatch, SafetyCheckResult(flagged=False, category="NONE"))

    history = [
        DialogueMessage(role="AI", body="起点の問い"),
        DialogueMessage(role="USER", body="前の職場で感じたこと"),
    ]
    events = _parse_sse(
        list(stream_reply(PURPOSE_STATEMENT, "CAREER", CHOICES, history, turn=2))
    )

    assert events[0] == ("delta", {"text": "ありたい姿に"})
    assert events[1] == ("delta", {"text": "つながっていますね。"})
    assert events[2] == ("done", {"turn": 2, "remaining": 0, "safety_flag": False})
    assert len(fake_client.messages.calls) == 1


def test_stream_reply_remaining_is_1_after_the_1st_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(monkeypatch, _FakeMessageStream(["問い"], _final_message()))
    _install_fake_safety_check(monkeypatch, SafetyCheckResult(flagged=False, category="NONE"))

    events = _parse_sse(list(stream_reply(PURPOSE_STATEMENT, "CAREER", CHOICES, [], turn=1)))
    assert events[-1] == ("done", {"turn": 1, "remaining": 1, "safety_flag": False})


def test_stream_reply_does_not_run_safety_check_on_first_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_client(monkeypatch, _FakeMessageStream(["こんにちは"], _final_message()))
    calls: list[str] = []

    def _fake_check_safety(text: str, **kwargs: Any) -> SafetyCheckResult:
        calls.append(text)
        return SafetyCheckResult(flagged=False, category="NONE")

    monkeypatch.setattr("app.ai.prompts.area_dialogue.check_safety", _fake_check_safety)

    list(stream_reply(PURPOSE_STATEMENT, "CAREER", CHOICES, [], turn=1))

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
    events = _parse_sse(
        list(stream_reply(PURPOSE_STATEMENT, "CAREER", CHOICES, history, turn=2))
    )
    assert events[-1][1]["safety_flag"] is True


def test_stream_reply_yields_error_on_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import anthropic
    import httpx

    request = httpx.Request("POST", "https://bedrock.example/invoke")
    response = httpx.Response(429, request=request)
    error = anthropic.RateLimitError("rate limited", response=response, body=None)
    _install_fake_client(monkeypatch, error)

    events = _parse_sse(list(stream_reply(PURPOSE_STATEMENT, "CAREER", CHOICES, [], turn=1)))
    assert events == [("error", {"code": "AI_PROVIDER_ERROR"})]


def test_stream_reply_yields_error_on_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(
        monkeypatch, _FakeMessageStream([], _final_message(stop_reason="refusal"))
    )

    events = _parse_sse(list(stream_reply(PURPOSE_STATEMENT, "CAREER", CHOICES, [], turn=1)))
    assert events == [("error", {"code": "AI_REFUSED"})]


def test_stream_reply_yields_error_on_max_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(
        monkeypatch, _FakeMessageStream(["途中まで"], _final_message(stop_reason="max_tokens"))
    )

    events = _parse_sse(list(stream_reply(PURPOSE_STATEMENT, "CAREER", CHOICES, [], turn=1)))
    assert events[-1] == ("error", {"code": "AI_MAX_TOKENS"})


def test_stream_reply_yields_error_on_empty_output(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(monkeypatch, _FakeMessageStream([], _final_message()))

    events = _parse_sse(list(stream_reply(PURPOSE_STATEMENT, "CAREER", CHOICES, [], turn=1)))
    assert events == [("error", {"code": "AI_OUTPUT_INVALID"})]


def test_stream_reply_logs_emf_on_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_fake_client(monkeypatch, _FakeMessageStream(["だいじょうぶ"], _final_message()))
    _install_fake_safety_check(monkeypatch, SafetyCheckResult(flagged=False, category="NONE"))

    list(
        stream_reply(
            PURPOSE_STATEMENT, "CAREER", CHOICES, [], turn=1, identifiers={"owner": "USER#u1"}
        )
    )

    logs = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines()]
    assert logs[0]["kind"] == "AREA_DIALOGUE"
    assert logs[0]["status"] == "SUCCEEDED"
    assert logs[0]["owner"] == "USER#u1"
