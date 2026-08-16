"""`POST /purposes` ／ `GET`/`PUT /purposes/current`。09_API設計5.8・5.8.1、
08_データモデル4.1・4.4、スキルflourish-api。

S-35。選択式回答・対話全文・選ばれた案・確定文を受け取り、ここではじめて保存する
(スキルflourish-data「集約を1アイテムにまとめる」で1回の`PutItem`相当にまとまる)。
S-36/S-37は保存済みのありたい姿を閲覧・編集する。
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai.prompts.purpose_dialogue import DialogueMessage
from app.api.deps import require_session
from app.core.errors import NotFoundError, UnprocessableEntityError
from app.domain.purpose import (
    STATEMENT_MAX_LENGTH,
    Item,
    get_current_purpose,
    save_purpose,
    update_purpose_statement,
)
from app.domain.purpose_choices import ChoiceAnswer, validate_choices

router = APIRouter()


def _serialize(item: Item) -> dict[str, Any]:
    # DynamoDBから読み込んだ`version`はDecimalになりうる(put_versionedの戻り値は
    # Python int、get_current_purposeの戻り値はDecimal)。GET側で文字列化されないよう
    # 明示的にintへ揃える。
    return {
        "version": int(item["version"]),
        "statement": item["statement"],
        "selected_direction": item["selected_direction"],
        "selected_label": item["selected_label"],
        "created_at": item["created_at"],
    }


class ChoiceIn(BaseModel):
    question_code: Literal["Q1", "Q2", "Q3"]
    option_codes: list[str]


class MessageIn(BaseModel):
    role: Literal["AI", "USER"]
    body: str


class PurposeCreateRequest(BaseModel):
    choices: list[ChoiceIn]
    messages: list[MessageIn]
    selected_direction: Literal["SELF", "OTHERS", "SOCIETY"]
    selected_label: str
    original_statement: str
    statement: str


def _validate_statement(statement: str) -> None:
    """09_API設計5.8.1の検証表(60文字以内・空文字不可)は`PUT /purposes/current`の節にあるが、
    完了条件が明記する「60文字上限」と合わせ、確定時の`POST /purposes`にも同じ制約を適用する
    判断とした。空文字はS-35側で「確定する」を無効化して防ぐ想定(S-12と同じ型)だが、
    直接APIを叩かれた場合の保険として、専用コードを増やさず同じ`STATEMENT_TOO_LONG`で
    まとめて範囲外(1〜60文字)を扱う。
    """
    if not statement or len(statement) > STATEMENT_MAX_LENGTH:
        raise UnprocessableEntityError(
            "STATEMENT_TOO_LONG",
            f"statement must be 1-{STATEMENT_MAX_LENGTH} chars (received {len(statement)})",
        )


@router.post("/purposes", status_code=201)
def create_purpose(
    body: PurposeCreateRequest,
    user_id: str = Depends(require_session),
) -> dict[str, Any]:
    _validate_statement(body.statement)

    choices = [
        ChoiceAnswer(question_code=choice.question_code, option_codes=choice.option_codes)
        for choice in body.choices
    ]
    validate_choices(choices)

    messages = [
        DialogueMessage(role=message.role, body=message.body) for message in body.messages
    ]

    item = save_purpose(
        user_id=user_id,
        statement=body.statement,
        original_statement=body.original_statement,
        selected_direction=body.selected_direction,
        selected_label=body.selected_label,
        choices=choices,
        conversation=messages,
    )
    return _serialize(item)


class PurposeUpdateRequest(BaseModel):
    statement: str


@router.get("/purposes/current")
def get_current_purpose_endpoint(user_id: str = Depends(require_session)) -> dict[str, Any]:
    """S-36。09_API設計5.8.1は取得できなかった場合の応答を明記していないが、他のエンドポイントの
    404の使い方(`GET /assessments/{id}`など)に合わせ、未作成なら404とした
    (通常の導線ではホームのありたい姿カードから開くため到達しない経路だが、直接アクセスの保険)。
    """
    item = get_current_purpose(user_id)
    if item is None:
        raise NotFoundError("PURPOSE_NOT_FOUND", "purpose has not been created yet")
    return _serialize(item)


@router.put("/purposes/current")
def update_current_purpose_endpoint(
    body: PurposeUpdateRequest,
    user_id: str = Depends(require_session),
) -> dict[str, Any]:
    _validate_statement(body.statement)

    current = get_current_purpose(user_id)
    if current is None:
        raise NotFoundError("PURPOSE_NOT_FOUND", "purpose has not been created yet")

    item = update_purpose_statement(user_id=user_id, statement=body.statement, current=current)
    return _serialize(item)
