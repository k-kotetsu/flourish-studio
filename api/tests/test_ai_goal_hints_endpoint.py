"""`POST /ai/goal-hints`(同期)。09_API設計5.10の検証・認証・`PURPOSE_REQUIRED`(409)・
レート制限・タイムアウト時の`503`を確認する。

実際のBedrock呼び出しは行わない。`app.ai.runner.get_client`をフェイクに差し替える
(test_ai_runner.pyと同じ手法)。
"""

import json
import uuid
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.errors import RateLimitedError
from app.core.security import SESSION_COOKIE_NAME
from app.db import repository
from app.domain import purpose as purpose_domain
from app.domain.session import create_session
from app.domain.user import build_profile_item
from app.main import app


def _client_with_logged_in_user(*, with_purpose: bool = True) -> TestClient:
    user_id = uuid.uuid4().hex
    repository.put_item(build_profile_item(user_id, guest_session_id=None))
    if with_purpose:
        purpose_domain.save_purpose(
            user_id=user_id,
            statement="まわりの人が安心して力を出せる存在でありたい。",
            original_statement="まわりの人が安心して力を出せる存在でありたい。",
            selected_direction="OTHERS",
            selected_label="まわりの人とともに",
            choices=[],
            conversation=[],
        )
    token, _ = create_session(user_id)
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    return client


def _request_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "area": "CAREER",
        "ideal_state": "今の仕事の中で自分の強みが言葉になっている。",
        "existing_goals": ["職務経歴書を書き上げる"],
    }
    body.update(overrides)
    return body


def _response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=100, output_tokens=20, cache_read_input_tokens=0),
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


def _install_fake_client(monkeypatch: pytest.MonkeyPatch, responses: list[Any]) -> _FakeMessages:
    fake_messages = _FakeMessages(responses)
    monkeypatch.setattr(
        "app.ai.runner.get_client", lambda: SimpleNamespace(messages=fake_messages)
    )
    return fake_messages


def _timeout_error() -> Exception:
    request = httpx.Request("POST", "https://bedrock.example/invoke")
    return anthropic.APITimeoutError(request=request)


def test_returns_401_without_session_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.post("/api/v1/ai/goal-hints", json=_request_body())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_returns_409_when_no_purpose_is_confirmed_yet() -> None:
    client = _client_with_logged_in_user(with_purpose=False)

    response = client.post("/api/v1/ai/goal-hints", json=_request_body())

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PURPOSE_REQUIRED"


def test_returns_429_when_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_logged_in_user()

    def _raise_rate_limited(owner: str) -> None:
        raise RateLimitedError("RATE_LIMITED", "hourly generation limit exceeded", retry_after=10)

    monkeypatch.setattr(
        "app.api.v1.ai_goal_hints.rate_limit.check_and_increment_user",
        _raise_rate_limited,
    )

    response = client.post("/api/v1/ai/goal-hints", json=_request_body())

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert response.headers["Retry-After"] == "10"


def test_returns_200_with_three_hints_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_logged_in_user()
    fake_messages = _install_fake_client(
        monkeypatch,
        [_response(json.dumps({"hints": ["候補1", "候補2", "候補3"]}))],
    )

    response = client.post("/api/v1/ai/goal-hints", json=_request_body())

    assert response.status_code == 200
    assert response.json() == {"hints": ["候補1", "候補2", "候補3"]}
    # 09_API設計5.10「タイムアウトは10秒」がBedrock呼び出しに渡っていることを確認する
    assert fake_messages.calls[0]["timeout"] == 10.0


def test_returns_503_and_does_not_retry_on_schema_violation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client_with_logged_in_user()
    fake_messages = _install_fake_client(monkeypatch, [_response("{ not json")])

    response = client.post("/api/v1/ai/goal-hints", json=_request_body())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_OUTPUT_INVALID"
    # GOAL_HINTSはretry_on_invalid=Falseのため、1回しか呼ばれない(4.7)
    assert len(fake_messages.calls) == 1


def test_returns_503_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_logged_in_user()
    _install_fake_client(monkeypatch, [_timeout_error()])

    response = client.post("/api/v1/ai/goal-hints", json=_request_body())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_PROVIDER_ERROR"
