"""`POST /auth/login`。09_API設計5.5.1、完了条件「ログインでホームへ」の確認。

実際のCognito呼び出しは行わない。`app.domain.cognito.authenticate`をフェイクに差し替える。
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import SESSION_COOKIE_NAME
from app.domain import cognito
from app.domain.session import get_active_session
from app.main import app

_LOGIN_BODY = {"email": "existing-user@example.com", "password": "correct-horse-battery-9"}


def test_returns_200_and_sets_session_cookie_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid.uuid4().hex

    def fake_authenticate(*, email: str, password: str) -> str:
        return user_id

    monkeypatch.setattr(cognito, "authenticate", fake_authenticate)
    client = TestClient(app, base_url="https://testserver")

    response = client.post("/api/v1/auth/login", json=_LOGIN_BODY)

    assert response.status_code == 200
    assert SESSION_COOKIE_NAME in client.cookies
    session = get_active_session(client.cookies[SESSION_COOKIE_NAME])
    assert session is not None
    assert session["user_id"] == user_id


def test_returns_401_invalid_credentials_for_wrong_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_authenticate(*, email: str, password: str) -> str:
        raise cognito.InvalidCredentialsError

    monkeypatch.setattr(cognito, "authenticate", fake_authenticate)
    client = TestClient(app, base_url="https://testserver")

    response = client.post("/api/v1/auth/login", json=_LOGIN_BODY)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert SESSION_COOKIE_NAME not in client.cookies


def test_returns_401_invalid_credentials_for_unknown_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # メール未登録もパスワード不一致と同じ扱いにする(総当たりでの登録有無の特定を防ぐ)
    def fake_authenticate(*, email: str, password: str) -> str:
        raise cognito.InvalidCredentialsError

    monkeypatch.setattr(cognito, "authenticate", fake_authenticate)
    client = TestClient(app, base_url="https://testserver")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever9"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
