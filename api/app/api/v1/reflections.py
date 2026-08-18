"""`GET /reflections/context`、`POST /reflections`、`GET /reflections/{id}`。
09_API設計5.13〜5.15、10_AIプロンプト設計4.8、04_画面設計S-61〜S-63。

S-61到達時に回答対象の目標一覧を返し、S-62で回答を受け取ってP-08(REFLECTION_SUMMARY)を
非同期ジョブとして生成、S-63で結果を返す。成功した時点ではじめてREFLECTIONアイテムが
保存される(`app/worker/handler.py`)。
"""

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from app.api.deps import require_session
from app.core.errors import ForbiddenError
from app.db.keys import user_pk
from app.domain import idempotency
from app.domain import job as job_domain
from app.domain.reflection import (
    StatusAnswer,
    get_reflection,
    get_reflection_context,
    now_iso,
    resolve_generation_input,
)
from app.queue.jobs import send_job_message

router = APIRouter()

# GET /jobs/{id}のQUEUED/RUNNING応答と同じ固定値(P2-5完了メモ参照)。
POLL_AFTER_MS = 1500


@router.get("/reflections/context")
def get_reflection_context_endpoint(user_id: str = Depends(require_session)) -> dict[str, Any]:
    return {"goals": get_reflection_context(user_id)}


class StatusAnswerIn(BaseModel):
    goal_key: str
    status: Literal["ON_TRACK", "STALLED", "REVISE"]


class ReflectionRequest(BaseModel):
    statuses: list[StatusAnswerIn]
    note: str | None = None


@router.post("/reflections", status_code=202)
def create_reflection_job(
    body: ReflectionRequest,
    user_id: str = Depends(require_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    """S-62。09_API設計5.14「網羅」「目標0件」の検証は`resolve_generation_input`が行う。

    頻度は制限しない(5.14「同じ日に何度でも記録できる」。2.4の生成系一般則の例外)。
    """
    statuses = [
        StatusAnswer(goal_key=answer.goal_key, status=answer.status) for answer in body.statuses
    ]
    generation_input = resolve_generation_input(user_id, statuses)

    owner = user_pk(user_id)
    candidate_job_id = uuid.uuid4().hex
    job_id = candidate_job_id
    if idempotency_key:
        job_id = idempotency.reserve_job_id(owner, idempotency_key, candidate_job_id)

    if job_id == candidate_job_id:
        reflection_id = uuid.uuid4().hex
        job_domain.create_job(owner, "REFLECTION_SUMMARY", job_id=job_id)
        send_job_message(
            job_id,
            "REFLECTION_SUMMARY",
            payload={
                "reflection_id": reflection_id,
                "purpose_statement": generation_input.purpose_statement,
                "statuses": [
                    {
                        "goal_key": status.goal_key,
                        "area": status.area,
                        "goal_body": status.goal_body,
                        "status": status.status,
                    }
                    for status in generation_input.statuses
                ],
                "area_ideal_states": generation_input.area_ideal_states,
                "note": body.note,
                "answered_at": now_iso(),
            },
        )

    return {"job_id": job_id, "poll_after_ms": POLL_AFTER_MS}


@router.get("/reflections/{reflection_id}")
def get_reflection_endpoint(
    reflection_id: str, user_id: str = Depends(require_session)
) -> dict[str, Any]:
    """S-63。`GET /assessments/{id}`と同じ考え方で、未存在と他人の所有を区別せず403にまとめる
    (存在有無を漏らさない)。
    """
    item = get_reflection(user_id, reflection_id)
    if item is None:
        raise ForbiddenError("REFLECTION_FORBIDDEN", "reflection does not belong to this owner")
    result: dict[str, Any] = item["result"]
    return {**result, "answered_at": item["answered_at"]}
