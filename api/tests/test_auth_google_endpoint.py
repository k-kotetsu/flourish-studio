"""`GET /auth/google`・`GET /auth/google/callback`。11_技術構成7.5、09_API設計8章。

完了条件「トークンをブラウザに渡していないことを確認」の検証：レスポンスは302リダイレクトと
`Set-Cookie: fs_session`(不透明なトークン)のみで、CognitoのIDトークン・アクセストークンは
一切含まれないことをテストで確認する。実際のCognito呼び出し(トークン交換)は
`app.domain.cognito.exchange_google_code`をフェイクに差し替える。

Cookieは`client.cookies.set(...)`で手動投入せず、実際のエンドポイント経由でSet-Cookieさせる
(test_auth_register_endpoint.pyの判断を踏襲。手動投入だとドメイン属性が空文字になり、
後続のCookie削除がhttpxのCookieJarで別エントリとして扱われてしまう)。
"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import GUEST_COOKIE_NAME, SESSION_COOKIE_NAME
from app.db import repository
from app.db.keys import GUEST_SK, PROFILE_SK, assessment_sk, guest_pk, user_pk
from app.domain import cognito
from app.domain.assessment import build_assessment_item, now_iso
from app.domain.assessment_precompute import CommitmentResult
from app.main import app


@pytest.fixture(autouse=True)
def _configured_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("PUBLIC_DOMAIN_NAME", "dev.flourish-st.com")
    monkeypatch.setenv("COGNITO_DOMAIN_PREFIX", "flourish-st-test")
    monkeypatch.setenv("COGNITO_USER_POOL_CLIENT_ID", "test-client-id")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _client() -> TestClient:
    return TestClient(app, base_url="https://testserver", follow_redirects=False)


def _start_authorize(client: TestClient) -> str:
    """`GET /auth/google`を実際に呼び、`fs_oauth_state`を正規のSet-Cookieで発行させた上で
    その値を返す(コールバックの`state`クエリにそのまま使う)。
    """
    response = client.get("/api/v1/auth/google")
    assert response.status_code == 302
    return client.cookies["fs_oauth_state"]


def test_authorize_redirects_to_cognito_hosted_ui_and_sets_state_cookie() -> None:
    client = _client()

    response = client.get("/api/v1/auth/google")

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith(
        "https://flourish-st-test.auth.ap-northeast-1.amazoncognito.com/oauth2/authorize?",
    )
    assert "identity_provider=Google" in location
    assert (
        "redirect_uri=https%3A%2F%2Fdev.flourish-st.com%2Fapi%2Fv1%2Fauth%2Fgoogle%2Fcallback"
        in location
    )
    assert "fs_oauth_state" in response.cookies
    assert f"state={response.cookies['fs_oauth_state']}" in location
    # トークンの類はどこにも含まれない
    assert "token" not in location.lower()


def test_callback_creates_account_and_sets_only_opaque_session_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.uuid4().hex
    monkeypatch.setattr(cognito, "exchange_google_code", lambda code, redirect_uri: user_id)
    client = _client()
    state = _start_authorize(client)

    response = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "auth-code-1", "state": state},
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://dev.flourish-st.com/app/s-41"
    assert SESSION_COOKIE_NAME in client.cookies
    session_token = client.cookies[SESSION_COOKIE_NAME]
    # Cookieに乗るのは不透明なセッショントークンのみ。CognitoのIDトークン・アクセストークン
    # (JWT。ピリオド区切り3セグメント)がそのまま漏れていないことを確認する。
    assert session_token.count(".") == 0
    assert "fs_oauth_state" not in client.cookies

    profile = repository.get_item(user_pk(user_id), PROFILE_SK)
    assert profile is not None
    assert profile["entity"] == "USER"


def test_callback_does_not_recreate_profile_for_returning_google_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.uuid4().hex
    monkeypatch.setattr(cognito, "exchange_google_code", lambda code, redirect_uri: user_id)
    client = _client()

    state1 = _start_authorize(client)
    first = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "code-1", "state": state1},
    )
    assert first.status_code == 302
    profile_after_first = repository.get_item(user_pk(user_id), PROFILE_SK)
    assert profile_after_first is not None

    state2 = _start_authorize(client)
    second = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "code-2", "state": state2},
    )
    assert second.status_code == 302
    profile_after_second = repository.get_item(user_pk(user_id), PROFILE_SK)
    # 作り直されていない(同じ内容のまま)
    assert profile_after_second == profile_after_first


def test_callback_links_guest_assessment_to_new_google_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.uuid4().hex
    monkeypatch.setattr(cognito, "exchange_google_code", lambda code, redirect_uri: user_id)

    client = _client()
    client.post("/api/v1/guest-sessions")
    guest_token = client.cookies[GUEST_COOKIE_NAME]

    report_item = build_assessment_item(
        owner=guest_pk(guest_token),
        assessment_id=uuid.uuid4().hex,
        question_set_version="2026-08-v1",
        scale_answers=[],
        free_text_answers=[],
        ai_output={
            "nickname": "テストのあだ名",
            "articulation_stage": "SPROUT",
            "safety_flag": False,
            "areas": [],
        },
        commitment=CommitmentResult(stage="SEED", score=3),
        started_at=now_iso(),
        completed_at=now_iso(),
    )
    repository.put_item(report_item)

    state = _start_authorize(client)
    response = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "code-1", "state": state},
    )

    assert response.status_code == 302
    assert GUEST_COOKIE_NAME not in client.cookies
    assert SESSION_COOKIE_NAME in client.cookies

    migrated = repository.get_item(user_pk(user_id), assessment_sk(report_item["assessment_id"]))
    assert migrated is not None
    assert "expires_at" not in migrated

    guest_item = repository.get_item(guest_pk(guest_token), GUEST_SK)
    assert guest_item is not None
    assert guest_item["converted_user_id"] == user_id


def test_callback_redirects_to_login_when_state_does_not_match() -> None:
    client = _client()
    _start_authorize(client)

    response = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "auth-code-1", "state": "wrong-state"},
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://dev.flourish-st.com/app/s-02"
    assert SESSION_COOKIE_NAME not in client.cookies


def test_callback_redirects_to_login_when_code_missing() -> None:
    client = _client()
    state = _start_authorize(client)

    response = client.get("/api/v1/auth/google/callback", params={"state": state})

    assert response.status_code == 302
    assert response.headers["location"] == "https://dev.flourish-st.com/app/s-02"


def test_callback_redirects_to_login_when_token_exchange_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_exchange(code: str, redirect_uri: str) -> str:
        raise cognito.GoogleAuthFailedError

    monkeypatch.setattr(cognito, "exchange_google_code", fake_exchange)
    client = _client()
    state = _start_authorize(client)

    response = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "bad-code", "state": state},
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://dev.flourish-st.com/app/s-02"
    assert SESSION_COOKIE_NAME not in client.cookies
