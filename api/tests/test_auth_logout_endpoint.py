"""`POST /auth/logout`。09_API設計4章、完了条件「ログアウトで`fs_guest`を再発行しない」の確認。

P3-1/P3-3が指摘したhttpx CookieJarのドメイン属性の落とし穴(手動投入したCookieの削除が
別エントリとして扱われ、永続ジャーから消えたように見えない)を避けるため、削除の確認は
`client.cookies`ではなく、レスポンスの`Set-Cookie`ヘッダを直接見る。
"""

import uuid

from fastapi.testclient import TestClient

from app.core.security import GUEST_COOKIE_NAME, SESSION_COOKIE_NAME
from app.domain.session import create_session, get_active_session
from app.main import app


def _uid() -> str:
    return uuid.uuid4().hex


def _client_with_session_cookie(token: str) -> TestClient:
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    return client


def test_returns_204_clears_session_cookie_and_invalidates_the_session() -> None:
    token, _ = create_session(_uid())
    client = _client_with_session_cookie(token)

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    set_cookie_headers = response.headers.get_list("set-cookie")
    assert any(
        header.startswith(f'{SESSION_COOKIE_NAME}=""') and "Max-Age=0" in header
        for header in set_cookie_headers
    )
    assert get_active_session(token) is None


def test_does_not_reissue_fs_guest() -> None:
    token, _ = create_session(_uid())
    client = _client_with_session_cookie(token)

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    set_cookie_headers = response.headers.get_list("set-cookie")
    assert not any(header.startswith(f"{GUEST_COOKIE_NAME}=") for header in set_cookie_headers)


def test_returns_401_without_session_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_returns_401_for_an_already_invalidated_session_token() -> None:
    token, _ = create_session(_uid())
    _client_with_session_cookie(token).post("/api/v1/auth/logout")

    # 同じトークンを新しいクライアントに載せ直し、「Cookie自体は送られてくるが指す
    # SESSIONが既に無効」という経路を、Cookieジャーの状態に左右されずに確認する。
    response = _client_with_session_cookie(token).post("/api/v1/auth/logout")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
