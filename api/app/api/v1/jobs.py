"""`GET /jobs/{id}`。09_API設計3.1・5.15、スキルflourish-api「非同期ジョブ」。"""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import current_owner
from app.core.errors import ForbiddenError, NotFoundError
from app.domain import job as job_domain

router = APIRouter()

# 09_API設計3.1のシーケンス図にある唯一の具体値をそのまま使う(仕様はkindごとの間隔を
# 明記していない)。ジョブ登録側(例: ai_assessment_questions.POLL_AFTER_MS)と同じ値。
_POLL_AFTER_MS = 1500


@router.get("/jobs/{job_id}")
def get_job(job_id: str, owner: str = Depends(current_owner)) -> dict[str, Any]:
    item = job_domain.get_job(job_id)
    if item is None:
        raise NotFoundError("JOB_NOT_FOUND", "job does not exist")
    if item["owner"] != owner:
        # 発行元のセッションからのみ参照できる(スキルflourish-api)。存在有無は漏らさない。
        raise ForbiddenError("JOB_FORBIDDEN", "job belongs to another owner")

    body: dict[str, Any] = {"status": item["status"]}
    if item["status"] == "SUCCEEDED":
        body["result"] = item["result"]
    elif item["status"] == "FAILED":
        body["error"] = item["error"]
    else:
        # QUEUED/RUNNING中はpoll_after_msを返す(5.15、`web/src/api/jobs.ts`が必須とする値。
        # P1-17完了メモの積み残しをP2-5で解消)。
        body["poll_after_ms"] = _POLL_AFTER_MS
    return body
