"""ログインセッション(SESSION)。08_データモデル6.3、11_技術構成7.2・9.3。"""

import time
from typing import Any

from app.core.security import generate_token, hash_token
from app.db import repository
from app.db.keys import SESSION_SK, session_pk

Item = dict[str, Any]

# 30日(08_データモデル6.3)
_TTL_SECONDS = 60 * 60 * 24 * 30

# 前回の延長から24時間以上経っている場合のみ延長する(08_データモデル6.3)
_EXTEND_THRESHOLD_SECONDS = 60 * 60 * 24


def build_session_item(user_id: str) -> tuple[str, Item]:
    """SESSIONアイテムを組み立てるだけで書き込みは行わない。

    登録時(P3-1)は他のPut/UpdateとまとめてTransactWriteItemsで書くため、
    アイテムの組み立てと永続化を分けている。
    """
    token = generate_token()
    now = int(time.time())
    item: Item = {
        "PK": session_pk(hash_token(token)),
        "SK": SESSION_SK,
        "entity": "SESSION",
        "user_id": user_id,
        "created_at": now,
        "last_seen_at": now,
        "expires_at": now + _TTL_SECONDS,
    }
    return token, item


def create_session(user_id: str) -> tuple[str, Item]:
    """ログイン成功時に呼ぶ(09_API設計5.5)。トークンはハッシュ化してから保存する。"""
    token, item = build_session_item(user_id)
    repository.put_item(item)
    return token, item


def get_active_session(token: str) -> Item | None:
    """有効なセッションを引く。期限切れはDynamoDBのTTL反映を待たずアプリ側で判定する。"""
    item = repository.get_item(session_pk(hash_token(token)), SESSION_SK)
    if item is None:
        return None
    if int(item["expires_at"]) <= int(time.time()):
        return None
    return item


def touch_session(item: Item) -> Item:
    """有効期限を延長する。前回の延長から24時間未満なら何もしない(間引き)。"""
    now = int(time.time())
    if now - int(item["last_seen_at"]) < _EXTEND_THRESHOLD_SECONDS:
        return item
    return repository.update_item(
        item["PK"],
        SESSION_SK,
        update_expression="SET last_seen_at = :now, expires_at = :exp",
        expression_attribute_values={":now": now, ":exp": now + _TTL_SECONDS},
    )
