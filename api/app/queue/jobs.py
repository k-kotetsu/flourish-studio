"""JOBのSQS送信。11_技術構成5.5、スキルflourish-api「非同期ジョブ」。

キューへの送信のみを行う。受信・処理は`app/worker/handler.py`が担う。

JOBアイテム自体は生成の入力を持たない(09_API設計5.2「保存しない」)ため、AIの生成に
入力が要るkind(P2-5以降)は`payload`にそれを乗せてワーカーへ渡す。
"""

import json
from typing import Any

from app.core.config import get_settings
from app.queue.client import get_sqs_client


def send_job_message(job_id: str, kind: str, payload: dict[str, Any] | None = None) -> None:
    settings = get_settings()
    if not settings.job_queue_url:
        raise RuntimeError("JOB_QUEUE_URL is not configured")

    body: dict[str, Any] = {"job_id": job_id, "kind": kind}
    if payload is not None:
        body["payload"] = payload

    get_sqs_client().send_message(
        QueueUrl=settings.job_queue_url,
        MessageBody=json.dumps(body),
    )
