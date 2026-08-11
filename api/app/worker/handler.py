"""ワーカーLambdaのエントリポイント。SQSからジョブを受け取り処理する(11_技術構成5.5)。

雛形段階(P1-13)ではkindを問わずダミーの結果ですぐSUCCEEDEDにする。実際の生成処理
(Bedrock呼び出し)は各生成系タスク(P1-14、P2以降)で、kindごとに分岐して実装する。

SQSはmaxReceiveCount=1で自動リトライしない(破ってはいけない規則5)。失敗はFAILEDとして
記録するだけで、ここから再送はしない。
"""

import json
from typing import Any

from app.domain import job as job_domain


def handler(event: dict[str, Any], context: object) -> dict[str, str]:
    records = event.get("Records", [])
    for record in records:
        _process_record(record)
    return {"status": "ok"}


def _process_record(record: dict[str, Any]) -> None:
    body = json.loads(record["body"])
    job_id = body["job_id"]

    job_domain.mark_running(job_id)
    current = job_domain.get_job(job_id)
    if current is None:
        return

    job_domain.mark_succeeded(job_id, result={"echo": current["kind"]})
