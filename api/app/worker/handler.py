"""ワーカーLambdaのエントリポイント。SQSからジョブを受け取り処理する(11_技術構成5.5)。

kindごとに実際の生成処理(Bedrock呼び出し)へ分岐する。未実装のkindは雛形段階(P1-13)の
ままダミーの結果ですぐSUCCEEDEDにする。

SQSはmaxReceiveCount=1で自動リトライしない(破ってはいけない規則5)。失敗はFAILEDとして
記録するだけで、ここから再送はしない。
"""

import json
from typing import Any

from app.ai.prompts import assessment_questions
from app.domain import job as job_domain
from app.domain.questions import get_question_set


def handler(event: dict[str, Any], context: object) -> dict[str, str]:
    records = event.get("Records", [])
    for record in records:
        _process_record(record)
    return {"status": "ok"}


def _process_record(record: dict[str, Any]) -> None:
    body = json.loads(record["body"])
    job_id = body["job_id"]
    kind = body["kind"]

    job_domain.mark_running(job_id)
    current = job_domain.get_job(job_id)
    if current is None:
        return

    if kind == "ASSESSMENT_QUESTIONS":
        _process_assessment_questions(job_id, body.get("payload", {}))
        return

    job_domain.mark_succeeded(job_id, result={"echo": current["kind"]})


def _process_assessment_questions(job_id: str, payload: dict[str, Any]) -> None:
    question_set = get_question_set(payload["question_set_version"])
    targets = [
        assessment_questions.QuestionTarget(**target) for target in payload["targets"]
    ]

    result = assessment_questions.generate_assessment_questions(
        targets, question_set, identifiers={"job_id": job_id}
    )
    if result.status == "SUCCEEDED":
        assert result.output is not None
        job_domain.mark_succeeded(job_id, result=result.output)
    else:
        assert result.error is not None
        job_domain.mark_failed(job_id, code=result.error.code, retryable=result.error.retryable)
