"""`GET /jobs/{id}`。09_API設計3.1、スキルflourish-api「非同期ジョブ」。"""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import current_owner
from app.core.errors import ForbiddenError, NotFoundError
from app.domain import job as job_domain

router = APIRouter()


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
    return body
