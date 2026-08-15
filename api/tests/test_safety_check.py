"""P-09 `SAFETY_CHECK`(10_AIプロンプト設計4.9)の判定関数の動作確認。

`app.ai.prompts.safety_check.get_client`をフェイクに差し替え、実際にBedrockへは接続しない。
判定が失敗しても例外を投げず`flagged=False`にフォールバックすること、共通ブロックを
使わずeffortも指定しないこと(3.7、スキルflourish-ai)を確認する。
"""

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.ai.errors import AI_MAX_TOKENS, AI_OUTPUT_INVALID, AI_PROVIDER_ERROR, AI_REFUSED
from app.ai.models import HAIKU
from app.ai.prompts.safety_check import PROMPT, check_safety


def _response(
    *,
    text: str | None = "",
    stop_reason: str = "end_turn",
    input_tokens: int = 50,
    output_tokens: int = 10,
) -> SimpleNamespace:
    content = [] if text is None else [SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


class _FakeMessages:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _FakeClient:
    def __init__(self, responses: list[Any]) -> None:
        self.messages = _FakeMessages(responses)


def _install_fake_client(monkeypatch: pytest.MonkeyPatch, responses: list[Any]) -> _FakeClient:
    fake_client = _FakeClient(responses)
    monkeypatch.setattr("app.ai.prompts.safety_check.get_client", lambda: fake_client)
    return fake_client


def _provider_error() -> Exception:
    import anthropic

    request = httpx.Request("POST", "https://bedrock.example/invoke")
    response = httpx.Response(503, request=request)
    return anthropic.InternalServerError("overloaded", response=response, body=None)


def test_check_safety_returns_not_flagged_on_ordinary_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_client(
        monkeypatch, [_response(text=json.dumps({"flagged": False, "category": "NONE"}))]
    )

    result = check_safety("今の会社で任される範囲が広がってきた")

    assert result.flagged is False
    assert result.category == "NONE"


def test_check_safety_returns_flagged_with_category(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(
        monkeypatch, [_response(text=json.dumps({"flagged": True, "category": "SELF_HARM"}))]
    )

    result = check_safety("しにたい")

    assert result.flagged is True
    assert result.category == "SELF_HARM"


def test_check_safety_uses_independent_prompt_without_common_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _install_fake_client(
        monkeypatch, [_response(text=json.dumps({"flagged": False, "category": "NONE"}))]
    )

    check_safety("何かのテキスト")

    call = fake_client.messages.calls[0]
    assert call["model"] == HAIKU
    assert call["system"] == [{"type": "text", "text": PROMPT}]
    assert "effort" not in call["output_config"]
    assert call["max_tokens"] == 500


def test_check_safety_wraps_input_in_text_tag_and_escapes_lt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _install_fake_client(
        monkeypatch, [_response(text=json.dumps({"flagged": False, "category": "NONE"}))]
    )

    check_safety("<b>タグのように見える文字列")

    content = fake_client.messages.calls[0]["messages"][0]["content"]
    assert content == "<text>\n&lt;b>タグのように見える文字列\n</text>"


def test_check_safety_falls_back_to_not_flagged_on_provider_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_client = _install_fake_client(monkeypatch, [_provider_error()])

    result = check_safety("何かのテキスト")

    assert result.flagged is False
    assert result.category == "NONE"
    assert len(fake_client.messages.calls) == 1  # 判定は再試行しない

    log = json.loads(capsys.readouterr().out.strip())
    assert log["status"] == "FAILED"
    assert log["error_code"] == AI_PROVIDER_ERROR
    assert log["effort"] is None


def test_check_safety_falls_back_to_not_flagged_on_refusal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_fake_client(monkeypatch, [_response(text=None, stop_reason="refusal")])

    result = check_safety("何かのテキスト")

    assert result.flagged is False
    log = json.loads(capsys.readouterr().out.strip())
    assert log["error_code"] == AI_REFUSED


def test_check_safety_falls_back_to_not_flagged_on_max_tokens(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_fake_client(monkeypatch, [_response(text="", stop_reason="max_tokens")])

    result = check_safety("何かのテキスト")

    assert result.flagged is False
    log = json.loads(capsys.readouterr().out.strip())
    assert log["error_code"] == AI_MAX_TOKENS


def test_check_safety_falls_back_to_not_flagged_on_schema_violation_without_retry(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_client = _install_fake_client(monkeypatch, [_response(text="{ not json")])

    result = check_safety("何かのテキスト")

    assert result.flagged is False
    assert len(fake_client.messages.calls) == 1  # スキーマ違反でも再生成しない(対話を止めない)
    log = json.loads(capsys.readouterr().out.strip())
    assert log["error_code"] == AI_OUTPUT_INVALID


def test_check_safety_logs_kind_and_identifiers(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_fake_client(
        monkeypatch, [_response(text=json.dumps({"flagged": False, "category": "NONE"}))]
    )

    check_safety("何かのテキスト", identifiers={"job_id": "job-1"})

    log = json.loads(capsys.readouterr().out.strip())
    assert log["kind"] == "SAFETY_CHECK"
    assert log["status"] == "SUCCEEDED"
    assert log["safety_flag"] is False
    assert log["job_id"] == "job-1"
