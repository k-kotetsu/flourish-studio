"""PURPOSE(ありたい姿)アイテムの組み立てと保存。08_データモデル4.1、4.3、4.4。

`POST /purposes`(S-35、P3-8)で確定した時点ではじめて保存される(09_API設計5.8
「ここではじめて保存される」)。それまでの選択式回答・対話履歴は
`purposeChoices`/`purposeDialogue`ストアがクライアント保持のみで持つ。

`PUT /purposes/current`(S-37、P3-9)も同じ`save_purpose`を使い、新しいバージョンを作る
(08_データモデル4.3「編集は上書きではなく、新しいアイテムの追加とする」)。
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import Any

from app.ai.prompts.purpose_dialogue import DialogueMessage
from app.db import repository
from app.db.keys import purpose_current_sk, user_pk
from app.domain.purpose_choices import ChoiceAnswer

Item = dict[str, Any]

# 09_API設計5.8.1の検証表、`10_AIプロンプト設計`4.4の`_MAX_STATEMENT_LENGTH`と同じ値。
STATEMENT_MAX_LENGTH = 60


def now_iso() -> str:
    """08_データモデル4.1の`created_at`と同じ形式(`...Z`)。"""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_conversation(messages: list[DialogueMessage]) -> list[dict[str, Any]]:
    """08_データモデル4.1の`conversation`(`seq`付き)を組み立てる。

    リクエストの`messages`(09_API設計5.6)には`seq`が無いため、受け取った順序で
    1から採番する。
    """
    return [
        {"seq": index + 1, "role": message.role, "body": message.body}
        for index, message in enumerate(messages)
    ]


def save_purpose(
    *,
    user_id: str,
    statement: str,
    original_statement: str,
    selected_direction: str,
    selected_label: str,
    choices: list[ChoiceAnswer],
    conversation: list[DialogueMessage],
) -> Item:
    """確定したありたい姿を保存する。`repository.put_versioned`が現行版を新しいバージョンへ
    差し替える(旧版があれば`HIST#PURPOSE#<N>`へ退避)。初回作成時は旧版が無いため`version`は1になる。
    """
    new_attributes: Item = {
        "entity": "PURPOSE",
        "statement": statement,
        "original_statement": original_statement,
        "selected_direction": selected_direction,
        "selected_label": selected_label,
        "choices": [dataclasses.asdict(choice) for choice in choices],
        "conversation": _build_conversation(conversation),
        "created_at": now_iso(),
    }
    return repository.put_versioned(
        user_pk(user_id), purpose_current_sk(), "PURPOSE", new_attributes
    )
