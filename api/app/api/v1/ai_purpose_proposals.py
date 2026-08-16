"""`POST /ai/purpose-proposals`。09_API設計5.7、10_AIプロンプト設計4.4、スキルflourish-api。

S-33。選択式3問の回答と対話全文から、ありたい姿の3案を非同期ジョブとして生成する。**保存しない。**
確定時の保存は`POST /purposes`(P3-8、未実装)で行う。
"""

import dataclasses
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from app.ai.prompts.purpose_dialogue import DialogueMessage
from app.api.deps import require_session
from app.db.keys import user_pk
from app.domain import idempotency, rate_limit
from app.domain import job as job_domain
from app.domain.purpose_choices import ChoiceAnswer, validate_choices
from app.queue.jobs import send_job_message

router = APIRouter()

# GET /jobs/{id}のQUEUED/RUNNING応答と同じ固定値(P2-5完了メモ参照)。
POLL_AFTER_MS = 1500


class ChoiceIn(BaseModel):
    question_code: Literal["Q1", "Q2", "Q3"]
    option_codes: list[str]


class MessageIn(BaseModel):
    role: Literal["AI", "USER"]
    body: str


class PurposeProposalsRequest(BaseModel):
    choices: list[ChoiceIn]
    messages: list[MessageIn]


@router.post("/ai/purpose-proposals", status_code=202)
def create_purpose_proposals_job(
    body: PurposeProposalsRequest,
    user_id: str = Depends(require_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    choices = [
        ChoiceAnswer(question_code=choice.question_code, option_codes=choice.option_codes)
        for choice in body.choices
    ]
    validate_choices(choices)

    messages = [
        DialogueMessage(role=message.role, body=message.body) for message in body.messages
    ]

    owner = user_pk(user_id)
    rate_limit.check_and_increment_user(owner)

    candidate_job_id = uuid.uuid4().hex
    job_id = candidate_job_id
    if idempotency_key:
        job_id = idempotency.reserve_job_id(owner, idempotency_key, candidate_job_id)

    if job_id == candidate_job_id:
        job_domain.create_job(owner, "PURPOSE_PROPOSALS", job_id=job_id)
        send_job_message(
            job_id,
            "PURPOSE_PROPOSALS",
            payload={
                "choices": [dataclasses.asdict(choice) for choice in choices],
                "messages": [dataclasses.asdict(message) for message in messages],
            },
        )

    return {"job_id": job_id, "poll_after_ms": POLL_AFTER_MS}
