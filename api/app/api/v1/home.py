"""`GET /home`。09_API設計5.9、04_画面設計S-41。

S-41。複数リソース(ありたい姿・4領域・テーマ設定)をまとめて返す画面専用エンドポイント。
"""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import require_session
from app.domain.home import get_home

router = APIRouter()


@router.get("/home")
def get_home_endpoint(user_id: str = Depends(require_session)) -> dict[str, Any]:
    return get_home(user_id)
