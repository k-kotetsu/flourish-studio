"""ASSESSMENT(現在地レポート)アイテムの組み立て。08_データモデル3章。

生成に成功した時点ではじめてこのアイテムを作る(3.3「生成の成否とアイテムの存在」)。
生成前・失敗中はアイテムを作らない(`app.domain.job.mark_succeeded_with_item`が担う)。
"""

import dataclasses
import time
from datetime import UTC, datetime
from typing import Any

from app.db.keys import assessment_sk
from app.domain.assessment_precompute import CommitmentResult, FreeTextAnswer, ScaleAnswer

Item = dict[str, Any]


def now_iso() -> str:
    """08_データモデル3.1の`started_at`/`completed_at`/`generated_at`と同じ形式(`...Z`)。"""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

# 30日(08_データモデル2.2「8 ゲストの現在地レポート」)。GUESTパーティションのときのみ
# 設定する。ゲストセッション自体の残りTTLとは連動させず、このアイテム独自の30日とした
# (JOB・IDEM・RATEなど他のTTL付きアイテムと同じく、各アイテムが独立してTTLを持つ設計)。
_GUEST_TTL_SECONDS = 60 * 60 * 24 * 30


def build_assessment_item(
    *,
    owner: str,
    assessment_id: str,
    question_set_version: str,
    scale_answers: list[ScaleAnswer],
    free_text_answers: list[FreeTextAnswer],
    ai_output: dict[str, Any],
    commitment: CommitmentResult,
    started_at: str,
    completed_at: str,
) -> Item:
    """`ai_output`はAI生成の出力そのまま(`articulation_reason`を含む)を渡してよい。

    `articulation_reason`はここでは使わず、item側には残らない(ユーザーに見せない値のため。
    `app.ai.prompts.assessment_report`がEMF側に記録する)。
    """
    is_guest = owner.startswith("GUEST#")
    item: Item = {
        "PK": owner,
        "SK": assessment_sk(assessment_id),
        "entity": "ASSESSMENT",
        "assessment_id": assessment_id,
        "guest_session_id": owner.removeprefix("GUEST#") if is_guest else None,
        "question_set_version": question_set_version,
        "scale_answers": [dataclasses.asdict(answer) for answer in scale_answers],
        "free_text_answers": [dataclasses.asdict(answer) for answer in free_text_answers],
        "result": {
            "nickname": ai_output["nickname"],
            "articulation_stage": ai_output["articulation_stage"],
            "commitment_stage": commitment.stage,
            "commitment_score": commitment.score,
            "safety_flag": ai_output["safety_flag"],
            "areas": ai_output["areas"],
            "generated_at": completed_at,
        },
        "started_at": started_at,
        "completed_at": completed_at,
    }
    if is_guest:
        item["expires_at"] = int(time.time()) + _GUEST_TTL_SECONDS
    return item
