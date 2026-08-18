"""`GET /reflections/context`。09_API設計5.13、05_質問・コンテンツ設計10.1〜10.2、04_画面設計S-61。

S-61で回答する対象の目標一覧を、4領域のAREA_PLANから1回の`BatchGetItem`でまとめて
取得する(`app/domain/home.py`と同じ集約パターン、スキルflourish-data)。

`08_データモデル`5.3は`goal_id`(Version 0.2)を廃止し、`goal_key`＋回答時点の文言スナップショット
(`goal_body`)に置き換えたと明記している。`09_API設計`5.13/5.14のJSON例は`goal_id`を含むが、
この置き換えが反映されていない古い記述と判断し(ユーザー確認済み)、`goal_key`のみを返す。
"""

from __future__ import annotations

from typing import Any

from app.db import repository
from app.db.keys import area_current_sk, user_pk
from app.domain.questions import AREAS


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
