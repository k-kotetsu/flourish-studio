"""`POST /ai/area-dialogue`(SSE)。09_API設計6章の検証・認証・レート制限・
`PURPOSE_REQUIRED`(409)を確認する。

実際のBedrock呼び出しは行わない。`app.ai.prompts.area_dialogue.get_client`を
フェイクに差し替える(test_ai_purpose_dialogue_endpoint.pyと同じ手法)。
"""

import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.errors import RateLimitedError
from app.core.security import SESSION_COOKIE_NAME
from app.db import repository
from app.domain import purpose as purpose_domain
from app.domain.session import create_session
from app.domain.user import build_profile_item
from app.main import app

_VALID_CHOICES = [
    {"question_code": "Q1", "option_codes": ["CAREER_OUTLOOK"]},
    {"question_code": "Q2", "option_codes": ["CAREER_VALUE_GROWTH"]},
    {"question_code": "Q3", "option_codes": ["CAREER_POSITION_GROWTH"]},
]


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


def _request_body(messages: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"area": "CAREER", "choices": _VALID_CHOICES, "messages": messages or []}


class _FakeMessageStream:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    def __enter__(self) -> "_FakeMessageStream":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    @property
    def text_stream(self) -> Any:
        return iter(self._chunks)

    def get_final_message(self) -> SimpleNamespace:
        return SimpleNamespace(
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=50, output_tokens=20, cache_read_input_tokens=0),
        )


def _install_fake_bedrock_client(monkeypatch: pytest.MonkeyPatch, chunks: list[str]) -> None:
    fake_stream = _FakeMessageStream(chunks)
    fake_client = SimpleNamespace(
        messages=SimpleNamespace(stream=lambda **kwargs: fake_stream)
    )
    monkeypatch.setattr("app.ai.prompts.area_dialogue.get_client", lambda: fake_client)
    monkeypatch.setattr(
        "app.ai.prompts.area_dialogue.check_safety",
        lambda *args, **kwargs: SimpleNamespace(flagged=False, category="NONE"),
    )


def test_returns_401_without_session_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.post("/api/v1/ai/area-dialogue", json=_request_body())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_returns_422_when_choices_are_missing_a_question() -> None:
    client = _client_with_logged_in_user()
    body = _request_body()
    body["choices"] = _VALID_CHOICES[:2]

    response = client.post("/api/v1/ai/area-dialogue", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CHOICES_INVALID"


def test_returns_422_when_q1_item_code_belongs_to_another_area() -> None:
    client = _client_with_logged_in_user()
    body = _request_body()
    body["choices"] = [
        {"question_code": "Q1", "option_codes": ["FINANCIAL_SAVINGS"]},
        _VALID_CHOICES[1],
        _VALID_CHOICES[2],
    ]

    response = client.post("/api/v1/ai/area-dialogue", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CHOICES_INVALID"


def test_returns_400_when_messages_do_not_end_with_user() -> None:
    client = _client_with_logged_in_user()
    body = _request_body(messages=[{"role": "AI", "body": "こんにちは"}])

    response = client.post("/api/v1/ai/area-dialogue", json=body)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MESSAGES_INVALID"


def test_returns_409_when_no_purpose_is_confirmed_yet() -> None:
    client = _client_with_logged_in_user(with_purpose=False)

    response = client.post("/api/v1/ai/area-dialogue", json=_request_body())

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PURPOSE_REQUIRED"


def test_returns_429_when_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_logged_in_user()

    def _raise_rate_limited(owner: str) -> None:
        raise RateLimitedError("RATE_LIMITED", "hourly generation limit exceeded", retry_after=10)

    monkeypatch.setattr(
        "app.api.v1.ai_area_dialogue.rate_limit.check_and_increment_user",
        _raise_rate_limited,
    )

    response = client.post("/api/v1/ai/area-dialogue", json=_request_body())

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert response.headers["Retry-After"] == "10"


def test_streams_delta_events_then_done_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_logged_in_user()
    _install_fake_bedrock_client(monkeypatch, ["キャリアの見通しを", "選ばれていました"])

    response = client.post("/api/v1/ai/area-dialogue", json=_request_body())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'event: delta\ndata: {"text": "キャリアの見通しを"}' in response.text
    assert 'event: done\ndata: {"turn": 1, "remaining": 1, "safety_flag": false}' in response.text


def test_remaining_is_0_after_the_2nd_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_logged_in_user()
    _install_fake_bedrock_client(monkeypatch, ["ありたい姿につながる問い"])

    messages = [
        {"role": "AI", "body": "1問目"},
        {"role": "USER", "body": "回答1"},
    ]
    response = client.post("/api/v1/ai/area-dialogue", json=_request_body(messages=messages))

    assert response.status_code == 200
    assert '"turn": 2, "remaining": 0' in response.text
