"""ユーザー本体(USER/PROFILE)。08_データモデル6.1。

メールアドレス・パスワード・Google連携は保持しない(Cognitoに一本化。11_技術構成7章)。
"""

from datetime import UTC, datetime
from typing import Any

from app.db.keys import PROFILE_SK, user_pk

Item = dict[str, Any]


def build_profile_item(user_id: str, guest_session_id: str | None) -> Item:
    """登録時(`POST /auth/register`)にはじめて作る。`user_id`はCognitoの`sub`。"""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "PK": user_pk(user_id),
        "SK": PROFILE_SK,
        "entity": "USER",
        "theme_preference": "AUTO",
        "guest_session_id": guest_session_id,
        "deleted_at": None,
        "created_at": now,
        "updated_at": now,
    }
