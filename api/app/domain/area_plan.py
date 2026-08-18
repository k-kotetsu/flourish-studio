"""AREA_PLAN(領域の計画)アイテムの組み立てと保存。08_データモデル4.2〜4.4、09_API設計5.11。

`POST /area-plans`(S-56、P4-6)で確定した時点ではじめて保存される(スキルflourish-data
「集約を1アイテムにまとめる」)。それまでの選択式回答(S-51)・対話履歴(S-52)・選んだ案と
編集後の理想状態(S-54/S-55)は`areaChoices`/`areaDialogue`/`areaProposals`ストアが
クライアント保持のみで持つ。

08_データモデル4.4「領域の確定」のとおり、`ConditionCheck`で「ありたい姿なしに領域は
作れない」を守りつつ、旧版があれば`HIST#AREA#<area>#<N>`へ退避して新版を書き込む
(スキルflourish-data「外部キーの代わりにConditionCheck」)。
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import UTC, datetime
from typing import Any

from app.ai.prompts.purpose_dialogue import DialogueMessage
from app.core.errors import ConflictError, UnprocessableEntityError
from app.db import repository
from app.db.keys import area_current_sk, history_sk, purpose_current_sk, user_pk
from app.domain.area_choices import ChoiceAnswer

Item = dict[str, Any]

# 09_API設計5.11の検証表「目標の件数 | 1〜3件。0件は422 GOALS_REQUIRED」。
MIN_GOALS = 1
MAX_GOALS = 3


@dataclasses.dataclass(frozen=True)
class GoalInput:
    body: str


def now_iso() -> str:
    """08_データモデル4.2の`created_at`と同じ形式(`...Z`)。purpose.pyのnow_isoと同じ。"""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_conversation(messages: list[DialogueMessage]) -> list[dict[str, Any]]:
    """purpose.py `_build_conversation`と同じ考え方。受け取った順序で`seq`を1から採番する。"""
    return [
        {"seq": index + 1, "role": message.role, "body": message.body}
        for index, message in enumerate(messages)
    ]


def _build_goals(goals: list[GoalInput]) -> list[dict[str, Any]]:
    """08_データモデル4.2「並び順の一意性: sort_orderが1から連番で重複しない → リストの
    位置そのもの」。S-56に目標の並べ替え機能は無い(9.6「+ 目標を追加」で末尾に足すのみ)ため、
    `sort_order`は配列の位置から採番し直し、クライアントの値には依存しない(purpose.pyの
    `_build_conversation`が`seq`を採番し直すのと同じ考え方)。`goal_key`は新規作成時に
    サーバーが採番する(09_API設計5.11)。job_id等と同じくプレフィックス無しのhex文字列とする
    (08_データモデル4.2の例`"g-7f3a..."`は例示であり、既存の`assessment_id`/`job_id`同様
    プレフィックスを付けない判断とした)。
    """
    return [
        {"goal_key": uuid.uuid4().hex, "body": goal.body, "sort_order": index + 1}
        for index, goal in enumerate(goals)
    ]


def validate_goals(goals: list[GoalInput]) -> None:
    """1〜3件。0件・4件以上のどちらも同じ`GOALS_REQUIRED`で扱う(purposes.pyが
    `STATEMENT_TOO_LONG`を空文字・超過の両方に使う判断と同じ考え方。5.11は0件の場合の
    コードのみ明記しているが、専用コードを増やさず範囲外全体をこれで表す)。
    """
    if not (MIN_GOALS <= len(goals) <= MAX_GOALS):
        raise UnprocessableEntityError(
            "GOALS_REQUIRED",
            f"goals must have {MIN_GOALS}-{MAX_GOALS} items (received {len(goals)})",
        )


def save_area_plan(
    *,
    user_id: str,
    area: str,
    choices: list[ChoiceAnswer],
    conversation: list[DialogueMessage],
    selected_direction: str,
    selected_label: str,
    original_ideal_state: str,
    ideal_state: str,
    goals: list[GoalInput],
) -> Item:
    """領域の計画を確定する。現行の`PURPOSE`が無ければ`409 PURPOSE_REQUIRED`。"""
    pk = user_pk(user_id)
    purpose = repository.get_item(pk, purpose_current_sk())
    if purpose is None:
        raise ConflictError("PURPOSE_REQUIRED", "purpose must be confirmed before area plan")

    current_sk = area_current_sk(area)
    old = repository.get_item(pk, current_sk)
    version = int(old["version"]) if old is not None else 0

    new_item: Item = {
        "PK": pk,
        "SK": current_sk,
        "entity": "AREA_PLAN",
        "area": area,
        "version": version + 1,
        "purpose_version": int(purpose["version"]),
        "ideal_state": ideal_state,
        "original_ideal_state": original_ideal_state,
        "selected_direction": selected_direction,
        "selected_label": selected_label,
        "choices": [dataclasses.asdict(choice) for choice in choices],
        "conversation": _build_conversation(conversation),
        "goals": _build_goals(goals),
        "created_at": now_iso(),
    }

    transact_items: list[dict[str, Any]] = [
        {
            "ConditionCheck": {
                "Key": {"PK": pk, "SK": purpose_current_sk()},
                "ConditionExpression": "attribute_exists(PK)",
            },
        },
    ]
    if old is not None:
        transact_items.append(
            {"Put": {"Item": {**old, "SK": history_sk(f"AREA#{area}", version)}}},
        )
    transact_items.append(
        {
            "Put": {
                "Item": new_item,
                "ConditionExpression": "attribute_not_exists(PK) OR version = :v",
                "ExpressionAttributeValues": {":v": version},
            },
        },
    )
    repository.transact_write_items(transact_items)
    return new_item
