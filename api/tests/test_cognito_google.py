"""`app.domain.cognito`のGoogle連携部分(P3-3、11_技術構成7.5)。

`GET /auth/google`・`GET /auth/google/callback`本体はエンドポイントのテスト
(test_auth_google_endpoint.py)で確認する。ここではトークン交換の成功・失敗と、
認可URLの組み立てのみを確認する。実際のCognito呼び出し(urllib・boto3)はフェイクに
差し替える。
"""

import json
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

import pytest

from app.core.config import get_settings
from app.domain import cognito


class _FakeTokenResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeTokenResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class _FakeCognitoClient:
    def __init__(self, sub: str, client_secret: str = "shh") -> None:
        self._sub = sub
        self._client_secret = client_secret

    def describe_user_pool_client(self, **kwargs: Any) -> dict[str, Any]:
        return {"UserPoolClient": {"ClientSecret": self._client_secret}}

    def get_user(self, **kwargs: Any) -> dict[str, Any]:
        return {"UserAttributes": [{"Name": "sub", "Value": self._sub}]}


@pytest.fixture(autouse=True)
def _configured_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "pool-id")
    monkeypatch.setenv("COGNITO_USER_POOL_CLIENT_ID", "client-id")
    monkeypatch.setenv("COGNITO_DOMAIN_PREFIX", "flourish-st-test")
    get_settings.cache_clear()
    cognito._get_app_client_secret.cache_clear()
    yield
    get_settings.cache_clear()
    cognito._get_app_client_secret.cache_clear()


def test_google_authorize_url_targets_hosted_domain_with_google_idp() -> None:
    url = cognito.google_authorize_url("https://example.com/callback", "state-123")

    assert url.startswith(
        "https://flourish-st-test.auth.ap-northeast-1.amazoncognito.com/oauth2/authorize?",
    )
    assert "identity_provider=Google" in url
    assert "state=state-123" in url
    assert "redirect_uri=https%3A%2F%2Fexample.com%2Fcallback" in url


def test_exchange_google_code_returns_sub_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cognito, "get_client", lambda: _FakeCognitoClient(sub="google-sub-1"))
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request, timeout=10: _FakeTokenResponse({"access_token": "at-1"}),
    )

    sub = cognito.exchange_google_code("auth-code", "https://example.com/callback")

    assert sub == "google-sub-1"


def test_exchange_google_code_raises_google_auth_failed_on_token_endpoint_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cognito, "get_client", lambda: _FakeCognitoClient(sub="unused"))

    def fake_urlopen(request: Any, timeout: int = 10) -> Any:
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(cognito.GoogleAuthFailedError):
        cognito.exchange_google_code("bad-code", "https://example.com/callback")


def test_exchange_google_code_raises_google_auth_failed_when_access_token_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cognito, "get_client", lambda: _FakeCognitoClient(sub="unused"))
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request, timeout=10: _FakeTokenResponse({"error": "invalid_grant"}),
    )

    with pytest.raises(cognito.GoogleAuthFailedError):
        cognito.exchange_google_code("bad-code", "https://example.com/callback")
