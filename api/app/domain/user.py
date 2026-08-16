"""ユーザー本体(USER/PROFILE)。08_データモデル6.1。

メールアドレス・パスワード・Google連携は保持しない(Cognitoに一本化。11_技術構成7章)。
"""

from datetime import UTC, datetime
from typing import Any

from app.db import repository
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


def get_profile(user_id: str) -> Item | None:
    """`GET /me`が使う。有効なセッションの持ち主は登録時に必ずPROFILEを持つ。"""
    return repository.get_item(user_pk(user_id), PROFILE_SK)


def update_theme_preference(user_id: str, theme_preference: str) -> Item:
    """`PATCH /me`(S-41のテーマ切替)が使う。`theme_preference`はAUTO/LIGHT/DARKのいずれか。"""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return repository.update_item(
        user_pk(user_id),
        PROFILE_SK,
        update_expression="SET theme_preference = :theme, updated_at = :now",
        expression_attribute_values={":theme": theme_preference, ":now": now},
    )
