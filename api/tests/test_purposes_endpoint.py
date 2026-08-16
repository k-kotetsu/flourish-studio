"""`POST /purposes` ／ `GET`/`PUT /purposes/current`。09_API設計5.8・5.8.1、
08_データモデル4.1・4.4の保存・バージョン管理を確認する。
"""

import uuid
from typing import Any

from fastapi.testclient import TestClient

from app.core.security import SESSION_COOKIE_NAME
from app.db import repository
from app.db.keys import history_sk, purpose_current_sk, user_pk
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


def _client_with_logged_in_user() -> tuple[TestClient, str]:
    user_id = uuid.uuid4().hex
    repository.put_item(build_profile_item(user_id, guest_session_id=None))
    token, _ = create_session(user_id)
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    return client, user_id


def _request_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "choices": _VALID_CHOICES,
        "messages": _VALID_MESSAGES,
        "selected_direction": "SELF",
        "selected_label": "自分の納得を軸に",
        "original_statement": "自分で選んだと言えることを積み重ねて生きていきたい。",
        "statement": "自分で選んだと言える選択を積み重ねていきたい。",
    }
    body.update(overrides)
    return body


def test_returns_401_without_session_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.post("/api/v1/purposes", json=_request_body())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_returns_422_when_statement_exceeds_60_chars() -> None:
    client, _ = _client_with_logged_in_user()

    response = client.post(
        "/api/v1/purposes", json=_request_body(statement="あ" * 61)
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "STATEMENT_TOO_LONG"


def test_returns_422_when_statement_is_empty() -> None:
    client, _ = _client_with_logged_in_user()

    response = client.post("/api/v1/purposes", json=_request_body(statement=""))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "STATEMENT_TOO_LONG"


def test_returns_422_when_choices_are_missing_a_question() -> None:
    client, _ = _client_with_logged_in_user()

    response = client.post(
        "/api/v1/purposes", json=_request_body(choices=_VALID_CHOICES[:2])
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CHOICES_INVALID"


def test_creates_purpose_and_saves_conversation() -> None:
    client, user_id = _client_with_logged_in_user()

    response = client.post("/api/v1/purposes", json=_request_body())

    assert response.status_code == 201
    body = response.json()
    assert body["version"] == 1
    assert body["statement"] == "自分で選んだと言える選択を積み重ねていきたい。"
    assert body["selected_direction"] == "SELF"

    item = repository.get_item(user_pk(user_id), purpose_current_sk())
    assert item is not None
    assert item["entity"] == "PURPOSE"
    assert item["original_statement"] == "自分で選んだと言えることを積み重ねて生きていきたい。"
    assert item["selected_label"] == "自分の納得を軸に"
    assert len(item["choices"]) == 3
    assert item["conversation"] == [
        {"seq": 1, "role": "AI", "body": "「成長」を選ばれていました。"},
        {"seq": 2, "role": "USER", "body": "前の職場で実感しました。"},
    ]


def test_second_create_makes_a_new_version_and_moves_old_to_history() -> None:
    client, user_id = _client_with_logged_in_user()
    client.post("/api/v1/purposes", json=_request_body(statement="最初の一文"))

    response = client.post("/api/v1/purposes", json=_request_body(statement="書き直した一文"))

    assert response.status_code == 201
    assert response.json()["version"] == 2

    current = repository.get_item(user_pk(user_id), purpose_current_sk())
    assert current is not None
    assert current["statement"] == "書き直した一文"

    history = repository.get_item(user_pk(user_id), history_sk("PURPOSE", 1))
    assert history is not None
    assert history["statement"] == "最初の一文"


def test_get_current_returns_401_without_session_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.get("/api/v1/purposes/current")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_get_current_returns_404_when_not_created_yet() -> None:
    client, _ = _client_with_logged_in_user()

    response = client.get("/api/v1/purposes/current")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PURPOSE_NOT_FOUND"


def test_get_current_returns_the_saved_purpose() -> None:
    client, _ = _client_with_logged_in_user()
    client.post("/api/v1/purposes", json=_request_body())

    response = client.get("/api/v1/purposes/current")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert body["statement"] == "自分で選んだと言える選択を積み重ねていきたい。"
    assert body["selected_direction"] == "SELF"


def test_put_current_returns_404_when_not_created_yet() -> None:
    client, _ = _client_with_logged_in_user()

    response = client.put("/api/v1/purposes/current", json={"statement": "新しい一文"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PURPOSE_NOT_FOUND"


def test_put_current_returns_422_when_statement_exceeds_60_chars() -> None:
    client, _ = _client_with_logged_in_user()
    client.post("/api/v1/purposes", json=_request_body())

    response = client.put("/api/v1/purposes/current", json={"statement": "あ" * 61})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "STATEMENT_TOO_LONG"


def test_put_current_makes_a_new_version_and_keeps_other_fields() -> None:
    client, user_id = _client_with_logged_in_user()
    client.post("/api/v1/purposes", json=_request_body())

    response = client.put("/api/v1/purposes/current", json={"statement": "書き換えた一文"})

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2
    assert body["statement"] == "書き換えた一文"

    current = repository.get_item(user_pk(user_id), purpose_current_sk())
    assert current is not None
    assert current["statement"] == "書き換えた一文"
    # PUTで作られた版のoriginal_statementは「前の版の文言」(AI原文ではない、09_API設計5.8.1)
    assert current["original_statement"] == "自分で選んだと言える選択を積み重ねていきたい。"
    assert current["selected_direction"] == "SELF"
    assert current["selected_label"] == "自分の納得を軸に"
    assert len(current["choices"]) == 3
    assert len(current["conversation"]) == 2

    history = repository.get_item(user_pk(user_id), history_sk("PURPOSE", 1))
    assert history is not None
    assert history["statement"] == "自分で選んだと言える選択を積み重ねていきたい。"
