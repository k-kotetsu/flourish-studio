"""`POST /ai/goal-hints`(同期)。09_API設計5.10、10_AIプロンプト設計4.7、スキルflourish-ai。

S-56。画面遷移を伴わず、ユーザーが「AIにヒントをもらう」を押したときだけ動く
(唯一の同期生成)。まだ保存されていない理想状態(S-55での編集後の文)とすでに入力済みの
目標をリクエストから受け取り、目標候補を3件返す。10秒でタイムアウトし、失敗しても
常に`503`を返すだけで進行は止めない(候補が出なくてもユーザーは自分で書ける。4.7)。

`ai_area_dialogue.py`と同じく、確定済みの「ありたい姿」はクライアントから送らせず
サーバーが`PURPOSE#CURRENT`から読む。現行の`PURPOSE`が無ければ同じ`409 PURPOSE_REQUIRED`
を流用する。`Idempotency-Key`は受け付けない(ジョブを作らない同期エンドポイントのため)。
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai.prompts import goal_hints
from app.api.deps import require_session
from app.core.errors import ConflictError, ServiceUnavailableError
from app.db.keys import user_pk
from app.domain import rate_limit
from app.domain.purpose import get_current_purpose

router = APIRouter()

_AREAS = Literal["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL"]


class GoalHintsRequest(BaseModel):
    area: _AREAS
    ideal_state: str
    existing_goals: list[str] = []


@router.post("/ai/goal-hints")
def create_goal_hints(
    body: GoalHintsRequest,
    user_id: str = Depends(require_session),
) -> dict[str, Any]:
    purpose = get_current_purpose(user_id)
    if purpose is None:
        raise ConflictError("PURPOSE_REQUIRED", "purpose must be confirmed before goal hints")

    owner = user_pk(user_id)
    rate_limit.check_and_increment_user(owner)

    result = goal_hints.generate_goal_hints(
        purpose["statement"],
        body.area,
        body.ideal_state,
        body.existing_goals,
        identifiers={"owner": owner},
    )
    if result.status != "SUCCEEDED":
        assert result.error is not None
        raise ServiceUnavailableError(result.error.code, "goal hints generation failed")

    assert result.output is not None
    return {"hints": result.output["hints"]}
