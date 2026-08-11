"""生成系POSTの冪等性(IDEM)。09_API設計2.5、スキルflourish-api「冪等性」。

先に読んでから書かない: 条件付きPutItemの成功/失敗がそのまま「新規/既存」の判定になる
(08_データモデル8.2)。同時リクエストでも、勝った一方だけが挿入に成功する。
"""

import time
from typing import Any

from app.db import repository
from app.db.keys import IDEM_SK, idem_pk

Item = dict[str, Any]

# 24時間(08_データモデル2.2、8.2)
_TTL_SECONDS = 60 * 60 * 24


def reserve_job_id(owner: str, idempotency_key: str, candidate_job_id: str) -> str:
    """`idempotency_key`にjob_idを予約する。

    既に同じキーで予約済みなら、そちらのjob_idを返す(`candidate_job_id`は使われない)。
    呼び出し側は、戻り値が`candidate_job_id`と一致した場合に限りジョブを新規作成する。
    一致しない場合は、返ってきたjob_idを既存のジョブとしてそのまま使う。
    """
    now = int(time.time())
    item: Item = {
        "PK": idem_pk(owner, idempotency_key),
        "SK": IDEM_SK,
        "job_id": candidate_job_id,
        "expires_at": now + _TTL_SECONDS,
    }
    try:
        repository.put_item(item, condition_expression="attribute_not_exists(PK)")
    except repository.ConditionalCheckFailed:
        existing = repository.get_item(idem_pk(owner, idempotency_key), IDEM_SK)
        if existing is None:
            return candidate_job_id
        return str(existing["job_id"])
    return candidate_job_id
