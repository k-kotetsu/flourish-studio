"""Cookieとトークンの基盤。11_技術構成7.2・9.3、スキルflourish-api「認証」を参照。"""

import hashlib
import secrets

from fastapi import Response

GUEST_COOKIE_NAME = "fs_guest"
SESSION_COOKIE_NAME = "fs_session"
# Google連携(P3-3)のCSRF対策用。認可リクエストからコールバックまでの短時間だけ生きる。
OAUTH_STATE_COOKIE_NAME = "fs_oauth_state"

# 30日(11_技術構成9.3)
COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30

# 10分。Google側での認証操作にかかる時間を見込む
OAUTH_STATE_MAX_AGE_SECONDS = 60 * 10

# 256bit。9.3の「128ビット以上」を満たす
_TOKEN_BYTES = 32


def generate_token() -> str:
    """Cookieに載せる不透明なランダム文字列。IDを埋め込まない(9.3)。"""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """`SESSION#<hash>`のPKに使う。生のトークンはDBに残さない(7.2)。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_auth_cookie(response: Response, name: str, token: str) -> None:
    response.set_cookie(
        key=name,
        value=token,
        max_age=COOKIE_MAX_AGE_SECONDS,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )


def clear_auth_cookie(response: Response, name: str) -> None:
    response.delete_cookie(
        key=name,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )


def set_oauth_state_cookie(response: Response, state: str) -> None:
    response.set_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        value=state,
        max_age=OAUTH_STATE_MAX_AGE_SECONDS,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )


def clear_oauth_state_cookie(response: Response) -> None:
    response.delete_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )
