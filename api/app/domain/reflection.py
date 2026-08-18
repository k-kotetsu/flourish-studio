"""Weekly Reflection。09_API設計5.13〜5.15、05_質問・コンテンツ設計10.1〜10.2、08_データモデル5章、
04_画面設計S-61〜S-63。

`GET /reflections/context`(S-61到達時)は現行の全目標を返し、`POST /reflections`(S-62)は
その全目標に対する回答を受け取ってP-08を生成、`GET /reflections/{id}`(S-63)は結果を返す。

`08_データモデル`5.3は`goal_id`(Version 0.2)を廃止し、`goal_key`＋回答時点の文言スナップショット
(`goal_body`)に置き換えたと明記している。`09_API設計`5.13/5.14のJSON例は`goal_id`を含むが、
この置き換えが反映されていない古い記述と判断し(ユーザー確認済み、P5-1)、`goal_key`のみを使う。
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import Any

from app.core.errors import ConflictError, UnprocessableEntityError
from app.db import repository
from app.db.keys import area_current_sk, purpose_current_sk, reflection_sk, user_pk
from app.domain.questions import AREAS

Item = dict[str, Any]

# 08_データモデル5.1 ReflectionStatus。プロンプト入力(4.8)の表記に使う日本語ラベルも兼ねる。
STATUS_LABELS: dict[str, str] = {
    "ON_TRACK": "進んでいる",
    "STALLED": "止まっている",
    "REVISE": "見直したい",
}
STATUSES = tuple(STATUS_LABELS)


def now_iso() -> str:
    """08_データモデル5.1の`answered_at`/`result.generated_at`と同じ形式(`...Z`)。"""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclasses.dataclass(frozen=True)
class StatusAnswer:
    """クライアントから届く回答そのもの(`goal_body`を持たない、09_API設計5.14)。"""

    goal_key: str
    status: str


@dataclasses.dataclass(frozen=True)
class ResolvedStatus:
    """現行のAREA_PLANと突き合わせて`area`/`goal_body`を確定させたもの。

    REFLECTIONアイテムの`statuses`(08_データモデル5.1)にそのまま保存する。
    """

    goal_key: str
    area: str
    goal_body: str
    status: str


@dataclasses.dataclass(frozen=True)
class ReflectionGenerationInput:
    purpose_statement: str
    statuses: list[ResolvedStatus]
    area_ideal_states: dict[str, str]


def get_reflection_context(user_id: str) -> list[dict[str, Any]]:
    """現行の全目標を領域→sort_orderの順に返す。目標が0件でも空配列(409にしない、5.13)。"""
    pk = user_pk(user_id)
    keys = [(pk, area_current_sk(area)) for area in AREAS]
    by_sk = {item["SK"]: item for item in repository.batch_get_items(keys)}

    goals: list[dict[str, Any]] = []
    for area in AREAS:
        plan = by_sk.get(area_current_sk(area))
        if plan is None:
            continue
        for goal in sorted(plan["goals"], key=lambda g: int(g["sort_order"])):
            goals.append({"goal_key": goal["goal_key"], "area": area, "body": goal["body"]})
    return goals


def resolve_generation_input(
    user_id: str, statuses: list[StatusAnswer]
) -> ReflectionGenerationInput:
    """`POST /reflections`の検証(5.14「網羅」「目標0件」)を行い、生成に必要な入力を組み立てる。

    現行のPURPOSE・4領域のAREA_PLANを1回の`BatchGetItem`でまとめて取得し(スキルflourish-data)、
    回答時点の`goal_body`をスナップショットとして確定させる(08_データモデル5.3)。
    """
    pk = user_pk(user_id)
    keys = [(pk, purpose_current_sk()), *[(pk, area_current_sk(area)) for area in AREAS]]
    by_sk = {item["SK"]: item for item in repository.batch_get_items(keys)}

    current_goals: list[tuple[str, str, str]] = []  # (area, goal_key, goal_body)
    area_ideal_states: dict[str, str] = {}
    for area in AREAS:
        plan = by_sk.get(area_current_sk(area))
        if plan is None:
            continue
        area_ideal_states[area] = plan["ideal_state"]
        for goal in sorted(plan["goals"], key=lambda g: int(g["sort_order"])):
            current_goals.append((area, goal["goal_key"], goal["body"]))

    if not current_goals:
        raise ConflictError("NO_GOALS", "no goals exist yet")

    submitted = {answer.goal_key: answer.status for answer in statuses}
    current_keys = {goal_key for _, goal_key, _ in current_goals}
    if set(submitted) != current_keys:
        raise UnprocessableEntityError(
            "STATUSES_INCOMPLETE",
            f"statuses must cover exactly the current {len(current_keys)} goals "
            f"(received {len(submitted)})",
        )

    purpose = by_sk.get(purpose_current_sk())
    # 目標が1件でも存在する時点でPURPOSEは必ず確定済み(area_plan.save_area_planの
    # PURPOSE_REQUIRED条件チェックにより、PURPOSE無しでAREA_PLANは作れない)。
    assert purpose is not None

    resolved = [
        ResolvedStatus(
            goal_key=goal_key, area=area, goal_body=goal_body, status=submitted[goal_key]
        )
        for area, goal_key, goal_body in current_goals
    ]
    return ReflectionGenerationInput(
        purpose_statement=purpose["statement"],
        statuses=resolved,
        area_ideal_states=area_ideal_states,
    )


def build_reflection_item(
    *,
    user_id: str,
    reflection_id: str,
    statuses: list[ResolvedStatus],
    note: str | None,
    ai_output: dict[str, Any],
    answered_at: str,
    generated_at: str,
) -> Item:
    """生成に成功した時点ではじめてこのアイテムを作る(09_API設計5.14「成功時に…まとめて保存する」)。"""
    return {
        "PK": user_pk(user_id),
        "SK": reflection_sk(answered_at, reflection_id),
        "entity": "REFLECTION",
        "reflection_id": reflection_id,
        "statuses": [dataclasses.asdict(status) for status in statuses],
        "note": note,
        "result": {
            "looking_back": ai_output["looking_back"],
            "insight": ai_output["insight"],
            "next_step": ai_output["next_step"],
            "safety_flag": ai_output["safety_flag"],
            "generated_at": generated_at,
        },
        "answered_at": answered_at,
    }


def get_reflection(user_id: str, reflection_id: str) -> Item | None:
    """`GET /reflections/{id}`(S-63)。

    SKは`REFLECTION#<answered_at>#<id>`(08_データモデル5.1)で`answered_at`を含むため、
    `reflection_id`だけでは`get_item`できない。5.4の一覧クエリ(新しい順)を`reflection_id`の
    一致で絞り込む判断とした。この画面には生成直後にしか到達しないため、実質的に
    先頭付近での一致になる。
    """
    items = repository.query_by_sk_prefix(user_pk(user_id), "REFLECTION#", scan_index_forward=False)
    return next((item for item in items if item["reflection_id"] == reflection_id), None)
