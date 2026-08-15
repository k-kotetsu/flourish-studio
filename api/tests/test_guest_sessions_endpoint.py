"""`POST /guest-sessions`。09_API設計5.1、完了条件「Cookieが発行され、再読込で増えない」の確認。"""

from fastapi.testclient import TestClient

from app.core.security import GUEST_COOKIE_NAME
from app.db import repository
from app.domain import guest_session
from app.main import app


def test_first_call_issues_a_new_guest_session_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.post("/api/v1/guest-sessions")

    assert response.status_code == 201
    assert GUEST_COOKIE_NAME in client.cookies
    token = client.cookies[GUEST_COOKIE_NAME]
    assert guest_session.get_active_guest_session(token) is not None


def test_reload_with_an_existing_valid_cookie_does_not_issue_a_new_session() -> None:
    client = TestClient(app, base_url="https://testserver")
    first_response = client.post("/api/v1/guest-sessions")
    first_token = client.cookies[GUEST_COOKIE_NAME]

    second_response = client.post("/api/v1/guest-sessions")

    assert second_response.status_code == 200
    # Set-Cookieを送り返していない = トークンが変わっていない(再読込で増えない)
    assert client.cookies[GUEST_COOKIE_NAME] == first_token
    assert first_response.status_code == 201


def test_call_with_an_expired_cookie_issues_a_new_session() -> None:
    client = TestClient(app, base_url="https://testserver")
    client.post("/api/v1/guest-sessions")
    expired_token = client.cookies[GUEST_COOKIE_NAME]
    item = guest_session.get_active_guest_session(expired_token)
    assert item is not None
    repository.update_item(
        item["PK"],
        item["SK"],
        update_expression="SET expires_at = :past",
        expression_attribute_values={":past": 1},
    )

    response = client.post("/api/v1/guest-sessions")

    assert response.status_code == 201
    assert client.cookies[GUEST_COOKIE_NAME] != expired_token
