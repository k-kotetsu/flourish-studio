"""P1-11の完了条件: ゲスト発行→登録→ログインの経路がテストで通る。

実際の`POST /guest-sessions`・`POST /auth/register`・`POST /auth/login`はP2-2・P3-1・
P3-2で実装する。ここではCookie・セッションの基盤(app.core.security, app.domain.session,
app.domain.guest_session, app.api.deps)が正しく組み合わさることを、最小限のルートで確認する。
"""

import uuid

from fastapi import Cookie, Depends, FastAPI, Response
from fastapi.testclient import TestClient

from app.api.deps import require_session
from app.core.error_handlers import register_error_handlers
from app.core.security import (
    GUEST_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    clear_auth_cookie,
    set_auth_cookie,
)
from app.domain import guest_session, session


def _build_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.post("/test/guest-sessions")
    def issue_guest(
        response: Response,
        fs_guest: str | None = Cookie(default=None),
    ) -> dict[str, bool]:
        # 09_API設計5.1: 既に有効なfs_guestがあれば新規発行しない
        if fs_guest is not None and guest_session.get_active_guest_session(fs_guest) is not None:
            return {"issued": False}
        token, _ = guest_session.issue_guest_session()
        set_auth_cookie(response, GUEST_COOKIE_NAME, token)
        return {"issued": True}

    @app.post("/test/register")
    def register(
        response: Response,
        fs_guest: str | None = Cookie(default=None),
    ) -> dict[str, str]:
        # Cognito SignUpの代わりに、テストではsubに相当するIDをその場で採番する
        user_id = uuid.uuid4().hex
        if fs_guest is not None:
            guest_session.mark_guest_converted(fs_guest, user_id)
            clear_auth_cookie(response, GUEST_COOKIE_NAME)

        token, _ = session.create_session(user_id)
        set_auth_cookie(response, SESSION_COOKIE_NAME, token)
        return {"user_id": user_id}

    @app.get("/test/me")
    def me(user_id: str = Depends(require_session)) -> dict[str, str]:
        return {"user_id": user_id}

    return app


client = TestClient(_build_app(), base_url="https://testserver")


def test_guest_issue_then_register_then_login_round_trip() -> None:
    # 1. ゲスト発行(S-11到達)
    guest_response = client.post("/test/guest-sessions")
    assert guest_response.status_code == 200
    assert guest_response.json() == {"issued": True}
    assert GUEST_COOKIE_NAME in client.cookies

    # 再訪では新規発行しない
    replay_response = client.post("/test/guest-sessions")
    assert replay_response.json() == {"issued": False}

    # 2. 登録: ゲストのCookieがアカウントへ引き継がれ、fs_sessionが発行される
    register_response = client.post("/test/register")
    assert register_response.status_code == 200
    registered_user_id = register_response.json()["user_id"]
    assert SESSION_COOKIE_NAME in client.cookies
    assert GUEST_COOKIE_NAME not in client.cookies

    # 3. ログイン後の画面と同じ経路: fs_sessionだけでリソースへアクセスできる
    me_response = client.get("/test/me")
    assert me_response.status_code == 200
    assert me_response.json() == {"user_id": registered_user_id}


def test_protected_route_returns_401_without_session_cookie() -> None:
    anonymous_client = TestClient(_build_app(), base_url="https://testserver")

    response = anonymous_client.get("/test/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_protected_route_returns_401_for_unknown_session_token() -> None:
    tampered_client = TestClient(_build_app(), base_url="https://testserver")
    tampered_client.cookies.set(SESSION_COOKIE_NAME, "not-a-real-token")

    response = tampered_client.get("/test/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
