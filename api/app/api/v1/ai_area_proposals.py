"""`POST /ai/area-proposals`。09_API設計6章「画面とAPIの対応」、10_AIプロンプト設計4.6。

S-53。対象領域・S-51の選択式回答・S-52の対話全文から、理想状態の3案を非同期ジョブとして
生成する。**保存しない。** 確定時の保存はS-55経由の`POST /area-plans`(P4-6、未実装)で行う。

`POST /ai/area-dialogue`(P4-3、`ai_area_dialogue.py`)と同じ判断を踏襲する。
**確定済みの「ありたい姿」はクライアントから送らせず、サーバーが`PURPOSE#CURRENT`から読む**
(4.6「確定済みの『ありたい姿』につながっている必要がある」を、クライアント入力に委ねず
改変・混入を防ぐため)。現行の`PURPOSE`が無ければ`ai_area_dialogue.py`と同じく
`09_API設計`5.11の`409 PURPOSE_REQUIRED`を流用する。
"""

import dataclasses
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from app.ai.prompts.purpose_dialogue import DialogueMessage
from app.api.deps import require_session
from app.core.errors import ConflictError
from app.db.keys import user_pk
from app.domain import idempotency, rate_limit
from app.domain import job as job_domain
from app.domain.area_choices import ChoiceAnswer, validate_area_choices
from app.domain.purpose import get_current_purpose
from app.queue.jobs import send_job_message

router = APIRouter()

_AREAS = Literal["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL"]

# GET /jobs/{id}のQUEUED/RUNNING応答と同じ固定値(P2-5完了メモ参照)。
POLL_AFTER_MS = 1500


class ChoiceIn(BaseModel):
    question_code: Literal["Q1", "Q2", "Q3"]
    option_codes: list[str]


class MessageIn(BaseModel):
    role: Literal["AI", "USER"]
    body: str


class AreaProposalsRequest(BaseModel):
    area: _AREAS
    choices: list[ChoiceIn]
    messages: list[MessageIn]


@router.post("/ai/area-proposals", status_code=202)
def create_area_proposals_job(
    body: AreaProposalsRequest,
    user_id: str = Depends(require_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    choices = [
        ChoiceAnswer(question_code=choice.question_code, option_codes=choice.option_codes)
        for choice in body.choices
    ]
    validate_area_choices(body.area, choices)

    messages = [
        DialogueMessage(role=message.role, body=message.body) for message in body.messages
    ]

    purpose = get_current_purpose(user_id)
    if purpose is None:
        raise ConflictError("PURPOSE_REQUIRED", "purpose must be confirmed before area proposals")

    owner = user_pk(user_id)
    rate_limit.check_and_increment_user(owner)

    candidate_job_id = uuid.uuid4().hex
    job_id = candidate_job_id
    if idempotency_key:
        job_id = idempotency.reserve_job_id(owner, idempotency_key, candidate_job_id)

    if job_id == candidate_job_id:
        job_domain.create_job(owner, "AREA_PROPOSALS", job_id=job_id)
        send_job_message(
            job_id,
            "AREA_PROPOSALS",
            payload={
                "purpose_statement": purpose["statement"],
                "area": body.area,
                "choices": [dataclasses.asdict(choice) for choice in choices],
                "messages": [dataclasses.asdict(message) for message in messages],
            },
        )

    return {"job_id": job_id, "poll_after_ms": POLL_AFTER_MS}
