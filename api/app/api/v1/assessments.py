"""`POST /assessments`。09_API設計5.3、10_AIプロンプト設計4.2、スキルflourish-api。

S-15。選択式・自由記述・問い文をすべて受け取り、生成と保存をまとめて非同期ジョブで行う。
成功した時点ではじめてASSESSMENTアイテムが保存される(`app/worker/handler.py`)。
"""

import dataclasses
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from app.api.deps import current_owner
from app.core.errors import BadRequestError
from app.domain import idempotency, rate_limit
from app.domain import job as job_domain
from app.domain.assessment import now_iso
from app.domain.assessment_precompute import (
    FreeTextAnswer,
    ScaleAnswer,
    validate_free_text_answers,
    validate_scale_answers,
)
from app.domain.questions import get_question_set
from app.queue.jobs import send_job_message

router = APIRouter()

# 09_API設計3.1のシーケンス図にある唯一の具体値をそのまま定数化した(仕様はkindごとの
# 間隔を明記していない)。ai_assessment_questions.POLL_AFTER_MS・GET /jobs/{id}と同じ値。
POLL_AFTER_MS = 1500


class ScaleAnswerIn(BaseModel):
    area: Literal["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL"]
    question_kind: Literal["SATISFACTION", "COMMITMENT"]
    item_code: str | None = None
    score: int = Field(ge=0, le=4)


class FreeTextAnswerIn(BaseModel):
    area: Literal["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL"]
    slot: Literal["SATISFIED", "CONCERN"]
    target_item_code: str
    generated_question: str
    body: str | None = None


class AssessmentRequest(BaseModel):
    scale_answers: list[ScaleAnswerIn]
    free_text_answers: list[FreeTextAnswerIn]
    question_set_version: str


@router.post("/assessments", status_code=202)
def create_assessment_job(
    body: AssessmentRequest,
    owner: str = Depends(current_owner),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    try:
        question_set = get_question_set(body.question_set_version)
    except KeyError as exc:
        # ai_assessment_questionsと同じ判断(仕様に明記のない経路。フロントの実装不備として400)。
        raise BadRequestError(
            "QUESTION_SET_VERSION_UNKNOWN",
            f"unknown question_set_version: {body.question_set_version}",
        ) from exc

    scale_answers = [
        ScaleAnswer(
            area=answer.area,
            question_kind=answer.question_kind,
            item_code=answer.item_code,
            score=answer.score,
        )
        for answer in body.scale_answers
    ]
    validate_scale_answers(scale_answers, question_set)

    free_text_answers = [
        FreeTextAnswer(
            area=answer.area,
            slot=answer.slot,
            target_item_code=answer.target_item_code,
            generated_question=answer.generated_question,
            body=answer.body,
        )
        for answer in body.free_text_answers
    ]
    validate_free_text_answers(free_text_answers)

    # レポート生成のレート制限(09_API設計2.4「ゲスト: レポート生成は1セッション3回まで」、
    # 08_データモデル6.2 report_generation_count)。ai_assessment_questionsと異なりゲストにも
    # 掛ける対象そのもの。
    if owner.startswith("USER#"):
        rate_limit.check_and_increment_user(owner)
    else:
        rate_limit.check_and_increment_guest(owner.removeprefix("GUEST#"))

    candidate_job_id = uuid.uuid4().hex
    job_id = candidate_job_id
    if idempotency_key:
        job_id = idempotency.reserve_job_id(owner, idempotency_key, candidate_job_id)

    if job_id == candidate_job_id:
        assessment_id = uuid.uuid4().hex
        job_domain.create_job(owner, "ASSESSMENT_REPORT", job_id=job_id)
        send_job_message(
            job_id,
            "ASSESSMENT_REPORT",
            payload={
                "assessment_id": assessment_id,
                "question_set_version": question_set.version,
                "scale_answers": [dataclasses.asdict(answer) for answer in scale_answers],
                "free_text_answers": [dataclasses.asdict(answer) for answer in free_text_answers],
                "started_at": now_iso(),
            },
        )

    return {"job_id": job_id, "poll_after_ms": POLL_AFTER_MS}
