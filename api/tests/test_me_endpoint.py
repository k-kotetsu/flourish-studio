"""`GET /me`・`PATCH /me`。09_API設計4章、08_データモデル6.1。"""

import uuid

from fastapi.testclient import TestClient

from app.core.security import SESSION_COOKIE_NAME
from app.db import repository
from app.domain.session import create_session
from app.domain.user import build_profile_item
from app.main import app


def _client_with_logged_in_user() -> TestClient:
    user_id = uuid.uuid4().hex
    repository.put_item(build_profile_item(user_id, guest_session_id=None))
    token, _ = create_session(user_id)
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    return client


def test_get_me_returns_the_default_theme_preference() -> None:
    client = _client_with_logged_in_user()

    response = client.get("/api/v1/me")

    assert response.status_code == 200
    assert response.json() == {"theme_preference": "AUTO"}


def test_get_me_returns_401_without_session_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_patch_me_updates_and_persists_the_theme_preference() -> None:
    client = _client_with_logged_in_user()

    response = client.patch("/api/v1/me", json={"theme_preference": "DARK"})

    assert response.status_code == 200
    assert response.json() == {"theme_preference": "DARK"}
    assert client.get("/api/v1/me").json() == {"theme_preference": "DARK"}


def test_patch_me_returns_400_for_an_unknown_theme_preference() -> None:
    client = _client_with_logged_in_user()

    response = client.patch("/api/v1/me", json={"theme_preference": "NEON"})

    assert response.status_code == 400


def test_patch_me_returns_401_without_session_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.patch("/api/v1/me", json={"theme_preference": "DARK"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
