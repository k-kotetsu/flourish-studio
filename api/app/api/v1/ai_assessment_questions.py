"""`POST /ai/assessment-questions`。09_API設計5.2、10_AIプロンプト設計4.1、スキルflourish-api。

S-13。選択式24問を受け取り、非同期ジョブとして自由記述8問の問い文を生成する。**保存しない。**
"""

import dataclasses
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from app.ai.prompts import assessment_questions
from app.api.deps import current_owner
from app.core.errors import BadRequestError
from app.domain import idempotency, rate_limit
from app.domain import job as job_domain
from app.domain.assessment_precompute import ScaleAnswer, validate_scale_answers
from app.domain.questions import get_question_set
from app.queue.jobs import send_job_message

router = APIRouter()

# 09_API設計3.1のシーケンス図にある唯一の具体値をそのまま定数化した(仕様はkindごとの
# 間隔を明記していない)。GET /jobs/{id}のQUEUED/RUNNING応答でも同じ値を返す(P1-17完了メモ
# 「GET /jobs/{id}にpoll_after_msを足す作業もP2-5で一緒に行う」に対応)。
POLL_AFTER_MS = 1500


class ScaleAnswerIn(BaseModel):
    area: Literal["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL"]
    question_kind: Literal["SATISFACTION", "COMMITMENT"]
    item_code: str | None = None
    score: int = Field(ge=0, le=4)


class AssessmentQuestionsRequest(BaseModel):
    scale_answers: list[ScaleAnswerIn]
    question_set_version: str


@router.post("/ai/assessment-questions", status_code=202)
def create_assessment_questions_job(
    body: AssessmentQuestionsRequest,
    owner: str = Depends(current_owner),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    try:
        question_set = get_question_set(body.question_set_version)
    except KeyError as exc:
        # 仕様に明記のない経路(実際のUIは常に既知のバージョンを送る)。フロントの実装不備
        # として400にする判断とした。
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

    # ゲストのレート制限(1セッション3回)はレポート生成(POST /assessments)専用
    # (09_API設計2.4「ゲスト: レポート生成は1セッション3回まで」、08_データモデル6.2
    # `report_generation_count`)。ここでは登録済みユーザーの生成系共通の上限のみ掛ける。
    if owner.startswith("USER#"):
        rate_limit.check_and_increment_user(owner)

    candidate_job_id = uuid.uuid4().hex
    job_id = candidate_job_id
    if idempotency_key:
        job_id = idempotency.reserve_job_id(owner, idempotency_key, candidate_job_id)

    if job_id == candidate_job_id:
        targets = assessment_questions.build_targets(scale_answers, question_set)
        job_domain.create_job(owner, "ASSESSMENT_QUESTIONS", job_id=job_id)
        send_job_message(
            job_id,
            "ASSESSMENT_QUESTIONS",
            payload={
                "question_set_version": question_set.version,
                "targets": [dataclasses.asdict(target) for target in targets],
            },
        )

    return {"job_id": job_id, "poll_after_ms": POLL_AFTER_MS}
