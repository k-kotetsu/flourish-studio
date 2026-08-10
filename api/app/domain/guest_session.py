"""ゲストセッション(GUEST_SESSION)。08_データモデル6.2。

`fs_guest`はCognitoと無関係(11_技術構成7.3)。SESSIONと異なり、PKにはトークンを
そのまま使う(6.2はハッシュ化を要求していない)。
"""

import time
from typing import Any

from app.core.security import generate_token
from app.db import repository
from app.db.keys import GUEST_SK, guest_pk

Item = dict[str, Any]

# 30日(08_データモデル6.2)
_TTL_SECONDS = 60 * 60 * 24 * 30


def issue_guest_session() -> tuple[str, Item]:
    """新しいゲストセッションを作る。

    既存の`fs_guest`があるときに新規発行しない判断は呼び出し側(`POST /guest-sessions`)
    が行う(09_API設計5.1)。
    """
    token = generate_token()
    now = int(time.time())
    item: Item = {
        "PK": guest_pk(token),
        "SK": GUEST_SK,
        "entity": "GUEST_SESSION",
        "converted_user_id": None,
        "converted_at": None,
        "report_generation_count": 0,
        "created_at": now,
        "expires_at": now + _TTL_SECONDS,
    }
    repository.put_item(item)
    return token, item


def get_active_guest_session(token: str) -> Item | None:
    item = repository.get_item(guest_pk(token), GUEST_SK)
    if item is None:
        return None
    if int(item["expires_at"]) <= int(time.time()):
        return None
    return item


def mark_guest_converted(token: str, user_id: str) -> None:
    """登録時にゲストをアカウントへ紐付けたことを記録する(11_技術構成7.3)。

    ゲスト側のデータそのものはTTLに委ね、ここでは削除しない。
    """
    now = int(time.time())
    repository.update_item(
        guest_pk(token),
        GUEST_SK,
        update_expression="SET converted_user_id = :uid, converted_at = :now",
        expression_attribute_values={":uid": user_id, ":now": now, ":null": None},
        condition_expression="attribute_not_exists(converted_user_id) OR converted_user_id = :null",
    )
