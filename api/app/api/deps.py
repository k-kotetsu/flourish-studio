"""エンドポイントが使う認証の依存関係。09_API設計2.1、スキルflourish-api「認証」。"""

from fastapi import Cookie

from app.core.errors import UnauthorizedError
from app.domain.session import get_active_session, touch_session


def require_session(fs_session: str | None = Cookie(default=None)) -> str:
    """要ログインのエンドポイントで使う。未認証・期限切れは401(クライアントはS-01へ戻す)。"""
    if fs_session is None:
        raise UnauthorizedError("UNAUTHENTICATED", "fs_session cookie is missing")

    session_item = get_active_session(fs_session)
    if session_item is None:
        raise UnauthorizedError("UNAUTHENTICATED", "session is invalid or expired")

    touch_session(session_item)
    return str(session_item["user_id"])
