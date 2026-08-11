"""エンドポイントが使う認証の依存関係。09_API設計2.1、スキルflourish-api「認証」。"""

from fastapi import Cookie

from app.core.errors import UnauthorizedError
from app.db.keys import guest_pk, user_pk
from app.domain.guest_session import get_active_guest_session
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


def current_owner(
    fs_session: str | None = Cookie(default=None),
    fs_guest: str | None = Cookie(default=None),
) -> str:
    """`GET /jobs/{id}`で使う。JOBアイテムの`owner`と同じ形(`USER#<id>` / `GUEST#<id>`)を返す。

    ゲスト可のジョブ(S-13/S-15)と要ログインのジョブ(S-33/S-53/S-62)の両方があるため、
    `fs_session`と`fs_guest`のどちらでも識別できるようにする(スキルflourish-api
    「GET /jobs/{id} 発行者のみ」)。どちらも無効なら401。
    """
    if fs_session is not None:
        session_item = get_active_session(fs_session)
        if session_item is not None:
            touch_session(session_item)
            return user_pk(str(session_item["user_id"]))

    if fs_guest is not None:
        guest_item = get_active_guest_session(fs_guest)
        if guest_item is not None:
            return guest_pk(fs_guest)

    raise UnauthorizedError("UNAUTHENTICATED", "no valid fs_session or fs_guest cookie")
