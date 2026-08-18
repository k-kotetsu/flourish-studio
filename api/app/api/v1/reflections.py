"""`GET /reflections/context`。09_API設計5.13、04_画面設計S-61。

S-61到達時に回答対象の目標一覧を返す画面専用エンドポイント。
"""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import require_session
from app.domain.reflection import get_reflection_context

router = APIRouter()


@router.get("/reflections/context")
def get_reflection_context_endpoint(user_id: str = Depends(require_session)) -> dict[str, Any]:
    return {"goals": get_reflection_context(user_id)}
