"""`GET /home`。09_API設計5.9、04_画面設計S-41、07_デザイン原則 原則2、スキルflourish-data。

S-41専用の集約。ありたい姿・4領域・振り返り導線の可否・テーマ設定を、
1回の`BatchGetItem`(スキルflourish-data)でまとめて返す
(09_API設計5.9「ホームで4〜5回のリクエストを往復させないため」)。
"""

from __future__ import annotations

from typing import Any

from app.db import repository
from app.db.keys import area_current_sk, purpose_current_sk, user_pk
from app.domain import user as user_domain
from app.domain.questions import AREAS

Item = dict[str, Any]


def _area_status(item: Item | None) -> dict[str, Any]:
    """screen-list.md S-41「作成済みは内容の要約＋目標数、未作成は破線」。

    未作成を`EMPTY`と表すのはAPI内部の状態名であり、原則2が禁じる画面上の語
    (「未完成」「空欄」)ではない。フロント側はこの値を見て破線カードに出し分ける。
    【判断】`ideal_state_summary`の切り詰め方法は09_API設計・08_データモデルのどちらにも
    文字数の定めが無い(`ideal_state`自体にも上限が無い)。ここで独自の文字数上限を発明せず
    `ideal_state`をそのまま返し、カード内での省略表示(CSSでの折り返し・省略)はフロント側に
    委ねる判断とした(破ってはいけない規則2「ユーザーの言葉を消さない」の精神を優先)。
    """
    if item is None:
        return {"status": "EMPTY"}
    return {
        "status": "CREATED",
        "ideal_state_summary": item["ideal_state"],
        "goal_count": len(item["goals"]),
    }


def get_home(user_id: str) -> dict[str, Any]:
    """09_API設計5.9のレスポンス形。"""
    pk = user_pk(user_id)
    keys = [(pk, purpose_current_sk()), *[(pk, area_current_sk(area)) for area in AREAS]]
    by_sk = {item["SK"]: item for item in repository.batch_get_items(keys)}

    purpose = by_sk.get(purpose_current_sk())
    areas = [{"area": area, **_area_status(by_sk.get(area_current_sk(area)))} for area in AREAS]

    # screen-list.md「Weekly Reflection: 目標1個以上で有効、0個で無効」。4領域の合計で判定する
    # (`09_API設計`5.13 `GET /reflections/context`が領域を問わず全目標を対象にするのと同じ考え方)。
    goal_total = sum(area["goal_count"] for area in areas if area["status"] == "CREATED")

    profile = user_domain.get_profile(user_id)
    assert profile is not None  # 有効なセッションの持ち主は登録時に必ずPROFILEを持つ(user.py)

    return {
        "purpose": (
            {"statement": purpose["statement"], "version": int(purpose["version"])}
            if purpose is not None
            else None
        ),
        "areas": areas,
        "reflection_available": goal_total > 0,
        "theme_preference": profile["theme_preference"],
    }
