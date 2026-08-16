"""`POST /ai/purpose-dialogue`(SSE)。09_API設計5.6、10_AIプロンプト設計4.3、スキルflourish-api。

S-32。選択式3問の回答と、それまでの対話履歴を毎回すべて受け取り、AIの応答を
ストリーミングで返す。対話履歴はサーバーに残さない(ステートレス。09_API設計3.2)。

**`Idempotency-Key`は受け付けない。** 09_API設計2.5の冪等性は「同じキーの再送に
既存の`job_id`を返す」というジョブベースの仕組みで、ジョブを作らないSSEエンドポイントには
そのまま当てはまらない。通信断時の二重課金は、非同期ジョブと違って「新しいAI応答が
2つ生成される」だけで、片方が保存されて片方が捨てられるような不整合を生まない
(対話全文は確定時にはじめてクライアントがまとめて送る。09_API設計3.2)ため、
このエンドポイント固有の冪等性の仕組みは持たない判断とした。
"""

from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.ai.prompts import purpose_dialogue
from app.api.deps import require_session
from app.db.keys import user_pk
from app.domain import rate_limit
from app.domain.purpose_choices import ChoiceAnswer, validate_choices

router = APIRouter()


class ChoiceIn(BaseModel):
    question_code: Literal["Q1", "Q2", "Q3"]
    option_codes: list[str]


class MessageIn(BaseModel):
    role: Literal["AI", "USER"]
    body: str


class PurposeDialogueRequest(BaseModel):
    choices: list[ChoiceIn]
    messages: list[MessageIn]


@router.post("/ai/purpose-dialogue")
def create_purpose_dialogue_stream(
    body: PurposeDialogueRequest,
    user_id: str = Depends(require_session),
) -> StreamingResponse:
    choices = [
        ChoiceAnswer(question_code=choice.question_code, option_codes=choice.option_codes)
        for choice in body.choices
    ]
    validate_choices(choices)

    messages = [
        purpose_dialogue.DialogueMessage(role=message.role, body=message.body)
        for message in body.messages
    ]
    turn = purpose_dialogue.compute_turn(messages)

    owner = user_pk(user_id)
    rate_limit.check_and_increment_user(owner)

    return StreamingResponse(
        purpose_dialogue.stream_reply(choices, messages, turn, identifiers={"owner": owner}),
        media_type="text/event-stream",
    )
