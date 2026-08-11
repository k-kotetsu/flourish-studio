"""JOBのSQS送信。11_技術構成5.5、スキルflourish-api「非同期ジョブ」。

キューへの送信のみを行う。受信・処理は`app/worker/handler.py`が担う。
"""

import json

from app.core.config import get_settings
from app.queue.client import get_sqs_client


def send_job_message(job_id: str, kind: str) -> None:
    settings = get_settings()
    if not settings.job_queue_url:
        raise RuntimeError("JOB_QUEUE_URL is not configured")

    get_sqs_client().send_message(
        QueueUrl=settings.job_queue_url,
        MessageBody=json.dumps({"job_id": job_id, "kind": kind}),
    )
