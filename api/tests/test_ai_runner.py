"""ダミープロンプトでの生成・検証・記録の動作確認(P1-14完了条件)。

`app.ai.runner.get_client`をフェイクに差し替え、実際にBedrockへは接続しない。
"""

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from anthropic.types import MessageParam

from app.ai import models
from app.ai.errors import AI_MAX_TOKENS, AI_OUTPUT_INVALID, AI_PROVIDER_ERROR, AI_REFUSED
from app.ai.runner import OutputValidationError, PromptSpec, generate

DUMMY_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string", "minLength": 1, "maxLength": 60},
        "safety_flag": {"type": "boolean"},
    },
    "required": ["message", "safety_flag"],
    "additionalProperties": False,
}

DUMMY_SPEC = PromptSpec(
    kind="TEST_DUMMY",
    model=models.HAIKU,
    prompt_version="test-v1",
    effort="low",
    max_tokens=100,
    individual_block="ダミーの個別ブロック。テスト専用で、実際のプロンプトではない。",
    schema=DUMMY_SCHEMA,
)

DUMMY_MESSAGES: list[MessageParam] = [
    {"role": "user", "content": "<user_input>test</user_input>"}
]


def _response(
    *,
    text: str | None = "",
    stop_reason: str = "end_turn",
    input_tokens: int = 100,
    output_tokens: int = 20,
    cache_read_input_tokens: int = 0,
) -> SimpleNamespace:
    content = [] if text is None else [SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
        ),
    )


def _valid_output_text(message: str = "受け止めました") -> str:
    return json.dumps({"message": message, "safety_flag": False})


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
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)
    return fake_client


def _rate_limit_error() -> Exception:
    import anthropic

    request = httpx.Request("POST", "https://bedrock.example/invoke")
    response = httpx.Response(429, request=request)
    return anthropic.RateLimitError("rate limited", response=response, body=None)


def _bad_request_error() -> Exception:
    import anthropic

    request = httpx.Request("POST", "https://bedrock.example/invoke")
    response = httpx.Response(400, request=request)
    return anthropic.BadRequestError("bad request", response=response, body=None)


def test_generate_succeeds_on_first_call_and_validates_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _install_fake_client(
        monkeypatch, [_response(text=_valid_output_text("だいじょうぶ"))]
    )

    result = generate(DUMMY_SPEC, DUMMY_MESSAGES, attempt=1, identifiers={"job_id": "job-1"})

    assert result.status == "SUCCEEDED"
    assert result.output == {"message": "だいじょうぶ", "safety_flag": False}
    assert result.safety_flag is False
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 20
    assert len(fake_client.messages.calls) == 1

    # Bedrockへ渡すsystemは共通ブロック＋個別ブロックの2層で、個別側にのみキャッシュを張る
    system = fake_client.messages.calls[0]["system"]
    assert len(system) == 2
    assert "cache_control" not in system[0]
    assert system[1]["cache_control"] == {"type": "ephemeral"}
    assert system[1]["text"] == DUMMY_SPEC.individual_block

    # Bedrockへ渡すJSON SchemaからはminLength/maxLengthが取り除かれている(3.3)
    wire_schema = fake_client.messages.calls[0]["output_config"]["format"]["schema"]
    assert "minLength" not in wire_schema["properties"]["message"]


def test_generate_retries_once_on_schema_violation_then_succeeds(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_client = _install_fake_client(
        monkeypatch,
        [
            _response(text=json.dumps({"message": "スキーマ違反"})),  # safety_flag欠落
            _response(text=_valid_output_text()),
        ],
    )

    result = generate(DUMMY_SPEC, DUMMY_MESSAGES, attempt=1)

    assert result.status == "SUCCEEDED"
    assert len(fake_client.messages.calls) == 2

    logs = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines()]
    assert len(logs) == 2
    assert logs[0]["status"] == "FAILED"
    assert logs[0]["retry_reason"] is None
    assert logs[1]["status"] == "SUCCEEDED"
    assert logs[1]["retry_reason"] == "SCHEMA_INVALID"


def test_generate_fails_after_second_schema_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = _install_fake_client(
        monkeypatch,
        [
            _response(text="{ not json"),
            _response(text="{ not json"),
        ],
    )

    result = generate(DUMMY_SPEC, DUMMY_MESSAGES, attempt=1)

    assert result.status == "FAILED"
    assert result.output is None
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 20
    assert result.error is not None
    assert result.error.code == AI_OUTPUT_INVALID
    assert result.error.retryable is True
    assert len(fake_client.messages.calls) == 2


def test_generate_does_not_retry_when_retry_on_invalid_is_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = PromptSpec(
        kind="GOAL_HINTS",
        model=models.SONNET,
        prompt_version="test-v1",
        effort="low",
        max_tokens=100,
        individual_block=DUMMY_SPEC.individual_block,
        schema=DUMMY_SCHEMA,
        retry_on_invalid=False,
    )
    fake_client = _install_fake_client(monkeypatch, [_response(text="{ not json")])

    result = generate(spec, DUMMY_MESSAGES, attempt=1)

    assert result.status == "FAILED"
    assert result.error is not None
    assert result.error.code == AI_OUTPUT_INVALID
    assert len(fake_client.messages.calls) == 1


def test_generate_fails_on_refusal_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = _install_fake_client(
        monkeypatch, [_response(text=None, stop_reason="refusal")]
    )

    result = generate(DUMMY_SPEC, DUMMY_MESSAGES, attempt=1)

    assert result.status == "FAILED"
    assert result.error is not None
    assert result.error.code == AI_REFUSED
    assert result.error.retryable is False
    assert len(fake_client.messages.calls) == 1


def test_generate_fails_on_max_tokens_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = _install_fake_client(
        monkeypatch, [_response(text="", stop_reason="max_tokens")]
    )

    result = generate(DUMMY_SPEC, DUMMY_MESSAGES, attempt=1)

    assert result.status == "FAILED"
    assert result.error is not None
    assert result.error.code == AI_MAX_TOKENS
    assert result.error.retryable is True
    assert len(fake_client.messages.calls) == 1


def test_generate_classifies_retryable_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = _install_fake_client(monkeypatch, [_rate_limit_error()])

    result = generate(DUMMY_SPEC, DUMMY_MESSAGES, attempt=1)

    assert result.status == "FAILED"
    assert result.error is not None
    assert result.error.code == AI_PROVIDER_ERROR
    assert result.error.retryable is True
    assert len(fake_client.messages.calls) == 1


def test_generate_passes_spec_timeout_to_the_client(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = PromptSpec(
        kind="GOAL_HINTS",
        model=models.SONNET,
        prompt_version="test-v1",
        effort="low",
        max_tokens=100,
        individual_block=DUMMY_SPEC.individual_block,
        schema=DUMMY_SCHEMA,
        retry_on_invalid=False,
        timeout=10.0,
    )
    fake_client = _install_fake_client(monkeypatch, [_response(text=_valid_output_text())])

    generate(spec, DUMMY_MESSAGES, attempt=1)

    assert fake_client.messages.calls[0]["timeout"] == 10.0


def test_generate_omits_timeout_kwarg_when_spec_does_not_set_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _install_fake_client(monkeypatch, [_response(text=_valid_output_text())])

    generate(DUMMY_SPEC, DUMMY_MESSAGES, attempt=1)

    assert "timeout" not in fake_client.messages.calls[0]


def test_generate_classifies_non_retryable_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(monkeypatch, [_bad_request_error()])

    result = generate(DUMMY_SPEC, DUMMY_MESSAGES, attempt=1)

    assert result.status == "FAILED"
    assert result.error is not None
    assert result.error.code == AI_PROVIDER_ERROR
    assert result.error.retryable is False


def test_generate_uses_custom_validation_for_constraints_the_schema_cannot_express(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # minLength/maxLengthはBedrockのformatでは拘束できないため、呼び出し側の
    # validate_outputで検証する(3.3)。ここでは1文字だけを許すダミー検証を行う。
    _install_fake_client(
        monkeypatch,
        [
            _response(text=_valid_output_text("ながすぎるもじれつ")),
            _response(text=_valid_output_text("短い")),
        ],
    )

    def validate_output(output: dict[str, Any]) -> None:
        if len(output["message"]) > 4:
            raise OutputValidationError("長すぎる")

    result = generate(DUMMY_SPEC, DUMMY_MESSAGES, attempt=1, validate_output=validate_output)

    assert result.status == "SUCCEEDED"
    assert result.output == {"message": "短い", "safety_flag": False}


def test_generate_passes_extra_log_fields_derived_from_the_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_fake_client(monkeypatch, [_response(text=_valid_output_text("だいじょうぶ"))])

    result = generate(
        DUMMY_SPEC,
        DUMMY_MESSAGES,
        attempt=1,
        extra_log_fields=lambda output: {"echoed_message": output["message"]},
    )

    assert result.status == "SUCCEEDED"
    logs = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines()]
    assert logs[0]["echoed_message"] == "だいじょうぶ"


def test_generate_does_not_call_extra_log_fields_when_generation_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_fake_client(monkeypatch, [_response(text=None, stop_reason="refusal")])
    calls: list[dict[str, Any]] = []

    def _record_and_return_extra(output: dict[str, Any]) -> dict[str, Any]:
        calls.append(output)
        return {}

    result = generate(
        DUMMY_SPEC, DUMMY_MESSAGES, attempt=1, extra_log_fields=_record_and_return_extra
    )

    assert result.status == "FAILED"
    assert calls == []
