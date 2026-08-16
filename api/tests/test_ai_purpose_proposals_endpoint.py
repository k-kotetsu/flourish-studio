"""`POST /ai/purpose-proposals`。09_API設計5.7の検証・認証・レート制限・非同期ジョブ登録を確認する。

実際のBedrock呼び出し・SQS送信は行わない。`send_job_message`をフェイクに差し替える。
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.errors import RateLimitedError
from app.core.security import SESSION_COOKIE_NAME
from app.db import repository
from app.domain import job as job_domain
from app.domain.session import create_session
from app.domain.user import build_profile_item
from app.main import app

_VALID_CHOICES = [
    {"question_code": "Q1", "option_codes": ["GROWTH", "FREEDOM"]},
    {"question_code": "Q2", "option_codes": ["SELF_DETERMINED"]},
    {"question_code": "Q3", "option_codes": ["HAVING_OPTIONS"]},
]
_VALID_MESSAGES = [
    {"role": "AI", "body": "「成長」を選ばれていました。"},
    {"role": "USER", "body": "前の職場で実感しました。"},
]


def _client_with_logged_in_user() -> TestClient:
    user_id = uuid.uuid4().hex
    repository.put_item(build_profile_item(user_id, guest_session_id=None))
    token, _ = create_session(user_id)
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    return client


def _request_body(messages: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "choices": _VALID_CHOICES,
        "messages": messages if messages is not None else _VALID_MESSAGES,
    }


class _FakeSendJobMessage:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, job_id: str, kind: str, payload: dict[str, Any] | None = None) -> None:
        self.calls.append({"job_id": job_id, "kind": kind, "payload": payload})


def test_returns_401_without_session_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.post("/api/v1/ai/purpose-proposals", json=_request_body())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_returns_422_when_choices_are_missing_a_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_send = _FakeSendJobMessage()
    monkeypatch.setattr("app.api.v1.ai_purpose_proposals.send_job_message", fake_send)
    client = _client_with_logged_in_user()
    body = _request_body()
    body["choices"] = _VALID_CHOICES[:2]

    response = client.post("/api/v1/ai/purpose-proposals", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CHOICES_INVALID"
    assert fake_send.calls == []


def test_returns_429_when_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_logged_in_user()

    def _raise_rate_limited(owner: str) -> None:
        raise RateLimitedError("RATE_LIMITED", "hourly generation limit exceeded", retry_after=10)

    monkeypatch.setattr(
        "app.api.v1.ai_purpose_proposals.rate_limit.check_and_increment_user",
        _raise_rate_limited,
    )

    response = client.post("/api/v1/ai/purpose-proposals", json=_request_body())

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert response.headers["Retry-After"] == "10"


def test_returns_202_and_queues_a_job(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_send = _FakeSendJobMessage()
    monkeypatch.setattr("app.api.v1.ai_purpose_proposals.send_job_message", fake_send)
    client = _client_with_logged_in_user()

    response = client.post("/api/v1/ai/purpose-proposals", json=_request_body())

    assert response.status_code == 202
    response_body = response.json()
    assert response_body["poll_after_ms"] == 1500
    job_id = response_body["job_id"]

    job_item = job_domain.get_job(job_id)
    assert job_item is not None
    assert job_item["kind"] == "PURPOSE_PROPOSALS"
    assert job_item["status"] == "QUEUED"

    assert len(fake_send.calls) == 1
    payload = fake_send.calls[0]["payload"]
    assert len(payload["choices"]) == 3
    assert len(payload["messages"]) == 2


def test_idempotency_key_reuses_the_same_job(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_send = _FakeSendJobMessage()
    monkeypatch.setattr("app.api.v1.ai_purpose_proposals.send_job_message", fake_send)
    client = _client_with_logged_in_user()
    headers = {"Idempotency-Key": "retry-key-1"}

    first = client.post("/api/v1/ai/purpose-proposals", json=_request_body(), headers=headers)
    second = client.post("/api/v1/ai/purpose-proposals", json=_request_body(), headers=headers)

    assert first.json()["job_id"] == second.json()["job_id"]
    assert len(fake_send.calls) == 1  # 2回目はジョブを作らない
