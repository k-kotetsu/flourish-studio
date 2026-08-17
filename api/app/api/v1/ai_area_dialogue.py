"""`POST /ai/area-dialogue`(SSE)。09_API設計6章「画面とAPIの対応」、10_AIプロンプト設計4.5、
05_質問・コンテンツ設計9.3、スキル`flourish-api`。

S-52。選択式3問(S-51)の回答と、それまでの対話履歴を毎回すべて受け取り、AIの応答を
ストリーミングで返す。対話履歴はサーバーに残さない(P-03`ai_purpose_dialogue.py`と同じ、
09_API設計3.2)。

**確定済みの「ありたい姿」はクライアントから送らせず、サーバーが`PURPOSE#CURRENT`から読む。**
4.5の個別ブロックは「一字一句そのまま使う」ことを前提にしており、クライアント入力に
委ねると改変・別ユーザーの文言の混入を防げない。S-52自身も表示のために
`GET /purposes/current`を独自に呼ぶ(S-51と同じパターン)ため、二重取得にはなるが
対話履歴を持たないステートレスな設計(3.2)と矛盾しない。現行の`PURPOSE`が無ければ
`09_API設計`5.11が`POST /area-plans`向けに定義済みの`409 PURPOSE_REQUIRED`をそのまま
流用する(判断の記録。ルートレベルの認証・前提画面ガードがまだ無く〔P4-2完了メモ〕、
S-51を経ずに直接この画面に到達した場合の防御にもなる)。

**`Idempotency-Key`は受け付けない。** `ai_purpose_dialogue.py`と同じ理由(ジョブを
作らないSSEエンドポイントには、ジョブベースの冪等性の仕組みがそのまま当てはまらない)。
"""

from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.ai.prompts import area_dialogue
from app.ai.prompts.purpose_dialogue import DialogueMessage, compute_turn
from app.api.deps import require_session
from app.core.errors import ConflictError
from app.db.keys import user_pk
from app.domain import rate_limit
from app.domain.area_choices import ChoiceAnswer, validate_area_choices
from app.domain.purpose import get_current_purpose

router = APIRouter()

_AREAS = Literal["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL"]


class ChoiceIn(BaseModel):
    question_code: Literal["Q1", "Q2", "Q3"]
    option_codes: list[str]


class MessageIn(BaseModel):
    role: Literal["AI", "USER"]
    body: str


class AreaDialogueRequest(BaseModel):
    area: _AREAS
    choices: list[ChoiceIn]
    messages: list[MessageIn]


@router.post("/ai/area-dialogue")
def create_area_dialogue_stream(
    body: AreaDialogueRequest,
    user_id: str = Depends(require_session),
) -> StreamingResponse:
    choices = [
        ChoiceAnswer(question_code=choice.question_code, option_codes=choice.option_codes)
        for choice in body.choices
    ]
    validate_area_choices(body.area, choices)

    messages = [
        DialogueMessage(role=message.role, body=message.body) for message in body.messages
    ]
    turn = compute_turn(messages)

    purpose = get_current_purpose(user_id)
    if purpose is None:
        raise ConflictError("PURPOSE_REQUIRED", "purpose must be confirmed before area dialogue")

    owner = user_pk(user_id)
    rate_limit.check_and_increment_user(owner)

    return StreamingResponse(
        area_dialogue.stream_reply(
            purpose["statement"],
            body.area,
            choices,
            messages,
            turn,
            identifiers={"owner": owner},
        ),
        media_type="text/event-stream",
    )
