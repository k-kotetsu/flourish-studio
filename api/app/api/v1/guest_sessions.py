"""`POST /guest-sessions`。09_API設計5.1、スキルflourish-api「非同期ジョブ」以外の単純な作成系。"""

from typing import Any

from fastapi import APIRouter, Cookie, Response

from app.core.security import GUEST_COOKIE_NAME, set_auth_cookie
from app.domain import guest_session

router = APIRouter()


@router.post("/guest-sessions")
def create_guest_session(
    response: Response,
    fs_guest: str | None = Cookie(default=None),
) -> dict[str, Any]:
    # 既に有効なfs_guestがあれば新規発行しない(09_API設計5.1)。再読み込みでセッションが増えない
    if fs_guest is not None and guest_session.get_active_guest_session(fs_guest) is not None:
        response.status_code = 200
        return {}

    token, _ = guest_session.issue_guest_session()
    set_auth_cookie(response, GUEST_COOKIE_NAME, token)
    response.status_code = 201
    return {}
