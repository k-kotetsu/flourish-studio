"""非同期ジョブ(JOB)。09_API設計3.1、11_技術構成5.5、08_データモデル8.1。

成果物を別アイテムに書く生成系ジョブ(P2以降)は、この`mark_succeeded`を使わず
`repository.transact_write_items`でJOB更新と成果物保存を1トランザクションにまとめる
(スキルflourish-api「成果物とジョブ完了を同一トランザクションで書く」)。
"""

import time
import uuid
from typing import Any

from app.db import repository
from app.db.keys import JOB_SK, job_pk

Item = dict[str, Any]

# 7日(08_データモデル2.2、8.1)
_TTL_SECONDS = 60 * 60 * 24 * 7


def create_job(owner: str, kind: str, job_id: str | None = None) -> tuple[str, Item]:
    """QUEUEDのJOBアイテムを作る。

    `job_id`を渡すと、それをそのまま使う(冪等性`idempotency.reserve_job_id`で予約した
    IDと組み合わせる場合に使う)。省略すると新規に採番する。
    """
    job_id = job_id or uuid.uuid4().hex
    now = int(time.time())
    item: Item = {
        "PK": job_pk(job_id),
        "SK": JOB_SK,
        "entity": "JOB",
        "owner": owner,
        "kind": kind,
        "status": "QUEUED",
        "result": None,
        "error": None,
        "created_at": now,
        "expires_at": now + _TTL_SECONDS,
    }
    repository.put_item(item)
    return job_id, item


def get_job(job_id: str) -> Item | None:
    return repository.get_item(job_pk(job_id), JOB_SK)


def mark_running(job_id: str) -> Item:
    return repository.update_item(
        job_pk(job_id),
        JOB_SK,
        update_expression="SET #status = :running",
        expression_attribute_names={"#status": "status"},
        expression_attribute_values={":running": "RUNNING", ":queued": "QUEUED"},
        condition_expression="#status = :queued",
    )


def mark_succeeded(job_id: str, result: dict[str, Any]) -> Item:
    return repository.update_item(
        job_pk(job_id),
        JOB_SK,
        update_expression="SET #status = :succeeded, #result = :result",
        expression_attribute_names={"#status": "status", "#result": "result"},
        expression_attribute_values={":succeeded": "SUCCEEDED", ":result": result},
    )


def mark_failed(job_id: str, code: str, retryable: bool) -> Item:
    """`retryable`はクライアントが再試行ボタンを出すかの判断に使う(09_API設計3.1)。"""
    return repository.update_item(
        job_pk(job_id),
        JOB_SK,
        update_expression="SET #status = :failed, #error = :error",
        expression_attribute_names={"#status": "status", "#error": "error"},
        expression_attribute_values={
            ":failed": "FAILED",
            ":error": {"code": code, "retryable": retryable},
        },
    )
