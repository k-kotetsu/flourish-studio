"""`POST /area-plans` ／ `GET`/`PUT /area-plans/{area}`。09_API設計5.11・5.12、
08_データモデル4.2〜4.5、スキルflourish-data。

S-56の確定。選択式回答(S-51)・対話全文(S-52)・選ばれた案(S-54)・編集後の理想状態(S-55)・
目標1〜3個を受け取り、ここではじめて保存する(スキルflourish-data「集約を1アイテムに
まとめる」で1回の`PutItem`相当にまとまる)。S-57/S-58は保存済みの領域の計画を閲覧・
直接編集する。
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai.prompts.purpose_dialogue import DialogueMessage
from app.api.deps import require_session
from app.core.errors import NotFoundError
from app.domain.area_choices import ChoiceAnswer, validate_area_choices
from app.domain.area_plan import (
    GoalInput,
    GoalUpdateInput,
    Item,
    get_area_plan,
    save_area_plan,
    update_area_plan,
    validate_goals,
)

router = APIRouter()

_AREAS = Literal["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL"]


def _serialize(item: Item) -> dict[str, Any]:
    # purposes.py `_serialize`と同じ理由(DynamoDBの`version`はDecimalになりうる)でintへ揃える。
    return {
        "version": int(item["version"]),
        "area": item["area"],
        "ideal_state": item["ideal_state"],
        "selected_direction": item["selected_direction"],
        "selected_label": item["selected_label"],
        "goals": [
            {
                "goal_key": goal["goal_key"],
                "body": goal["body"],
                "sort_order": int(goal["sort_order"]),
            }
            for goal in item["goals"]
        ],
        "created_at": item["created_at"],
    }


class ChoiceIn(BaseModel):
    question_code: Literal["Q1", "Q2", "Q3"]
    option_codes: list[str]


class MessageIn(BaseModel):
    role: Literal["AI", "USER"]
    body: str


class GoalIn(BaseModel):
    body: str
    sort_order: int


class AreaPlanCreateRequest(BaseModel):
    area: _AREAS
    choices: list[ChoiceIn]
    messages: list[MessageIn]
    selected_direction: Literal["DEEPEN", "CHANGE", "EXPAND"]
    selected_label: str
    original_ideal_state: str
    ideal_state: str
    goals: list[GoalIn]


@router.post("/area-plans", status_code=201)
def create_area_plan(
    body: AreaPlanCreateRequest,
    user_id: str = Depends(require_session),
) -> dict[str, Any]:
    choices = [
        ChoiceAnswer(question_code=choice.question_code, option_codes=choice.option_codes)
        for choice in body.choices
    ]
    validate_area_choices(body.area, choices)

    messages = [
        DialogueMessage(role=message.role, body=message.body) for message in body.messages
    ]

    # `sort_order`はサーバー側で配列の位置から採番し直すため、リクエストの値はここでは使わない
    # (area_plan.py `_build_goals`のコメント参照)。
    goals = [GoalInput(body=goal.body) for goal in body.goals]
    validate_goals(goals)

    item = save_area_plan(
        user_id=user_id,
        area=body.area,
        choices=choices,
        conversation=messages,
        selected_direction=body.selected_direction,
        selected_label=body.selected_label,
        original_ideal_state=body.original_ideal_state,
        ideal_state=body.ideal_state,
        goals=goals,
    )
    return _serialize(item)


class GoalUpdateIn(BaseModel):
    goal_key: str | None = None
    body: str
    sort_order: int


class AreaPlanUpdateRequest(BaseModel):
    ideal_state: str
    goals: list[GoalUpdateIn]


@router.get("/area-plans/{area}")
def get_area_plan_endpoint(
    area: _AREAS,
    user_id: str = Depends(require_session),
) -> dict[str, Any]:
    """S-57。09_API設計はこの場合の応答を明記していないが、`GET /purposes/current`と同じく
    未作成なら404とした(通常はホームの作成済み領域カードから開くため到達しない経路だが、
    直接アクセスの保険)。
    """
    item = get_area_plan(user_id, area)
    if item is None:
        raise NotFoundError("AREA_PLAN_NOT_FOUND", "area plan has not been created yet")
    return _serialize(item)


@router.put("/area-plans/{area}")
def update_area_plan_endpoint(
    area: _AREAS,
    body: AreaPlanUpdateRequest,
    user_id: str = Depends(require_session),
) -> dict[str, Any]:
    current = get_area_plan(user_id, area)
    if current is None:
        raise NotFoundError("AREA_PLAN_NOT_FOUND", "area plan has not been created yet")

    # `sort_order`はcreate_area_planと同じくサーバー側で採番し直す(area_plan.py
    # `_build_goals_for_update`のコメント参照)。
    goals = [
        GoalUpdateInput(goal_key=goal.goal_key, body=goal.body) for goal in body.goals
    ]
    validate_goals(goals)

    item = update_area_plan(
        user_id=user_id,
        area=area,
        ideal_state=body.ideal_state,
        goals=goals,
        current=current,
    )
    return _serialize(item)
