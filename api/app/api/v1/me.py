"""`GET /me`・`PATCH /me`。09_API設計4章、スキルflourish-api。

どちらも要ログイン。08_データモデル6.1のPROFILEのうち、クライアントに公開する必要がある
唯一の属性`theme_preference`(AUTO/LIGHT/DARK)だけを扱う。メールアドレス等はCognitoに
一本化されアプリ側に複製が無いため、ここでは返さない(08_データモデル6.1)。
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_session
from app.domain import user

router = APIRouter()


@router.get("/me")
def get_me(user_id: str = Depends(require_session)) -> dict[str, Any]:
    profile = user.get_profile(user_id)
    assert profile is not None  # 有効なセッションの持ち主は登録時に必ずPROFILEを持つ
    return {"theme_preference": profile["theme_preference"]}


class UpdateMeRequest(BaseModel):
    theme_preference: Literal["AUTO", "LIGHT", "DARK"]


@router.patch("/me")
def patch_me(body: UpdateMeRequest, user_id: str = Depends(require_session)) -> dict[str, Any]:
    profile = user.update_theme_preference(user_id, body.theme_preference)
    return {"theme_preference": profile["theme_preference"]}
