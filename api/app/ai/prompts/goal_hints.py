"""P-07 `GOAL_HINTS`(10_AIプロンプト設計4.7)。S-56「AIにヒントをもらう」ボタン。

**唯一、ユーザーが押したときだけ動く同期生成。** タイムアウトは10秒(09_API設計5.10)、
`retry_on_invalid=False`でサーバ内再生成もしない(4.7「同期呼び出しで10秒の上限があり、
2回目を試す余裕がない」)。`safety_flag`を持たない(4.7「この生成の入力はユーザーの
自由記述を含まない〔理想状態は確定済みの成果物〕」)。
"""

from __future__ import annotations

from typing import Any

from anthropic.types import MessageParam

from app.ai import models
from app.ai.runner import Effort, GenerationResult, OutputValidationError, PromptSpec, generate
from app.domain.questions import AREA_LABELS

PROMPT_VERSION = "2026-08-v1"

# 10_AIプロンプト設計4.7は`low`/2,000を指定するが、スキルflourish-aiの対応表は
# `low`/1,500で食い違っている。P2-5・P2-8・P3-6・P3-7・P4-3完了メモで確立した
# 「ドキュメント優先」を踏襲し、4.7の値を採用した(6件目の同種の食い違い。
# スキル側の表は未修正のまま残る)。
EFFORT: Effort = "low"
MAX_TOKENS = 2000
TIMEOUT_SECONDS = 10.0
_MAX_HINT_LENGTH = 50

INDIVIDUAL_BLOCK = """# あなたの仕事
ユーザーが今年取り組む目標の候補を3つ出します。
これは、ユーザーが「思いつかないとき」に自分から押したときだけ出るヒントです。

# ルール
- 理想の状態に近づくための、今年1年で取り組めることにします。
- 1つは20〜30文字程度。短い言い切りにします。「〜する」の形を基本とします。
- 3つは互いに異なる粒度・角度にします。同じことの言い換えにしません。
- すでに入力済みの目標と重複するものを出しません。
- 商品、サービス、資格スクール、アプリの利用を伴うものを出しません。
- 「毎日〜する」のような、破綻しやすい頻度を含めません。
- 転職、退職など、大きな決断そのものを目標にしません。
- 説明、前置き、補足を付けません。3つの目標文だけを出力します。

例（Career・上の理想状態の場合）:
  職務経歴書を書き上げる
  月に1回、社外の人と話す
  半期に1つ、新しい役割に手を挙げる"""

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "hints": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["hints"],
    "additionalProperties": False,
}


def _escape_user_input(text: str) -> str:
    """`<`はタグの入れ子と誤読されうるため事前にエスケープする(他のprompts/*.pyと同じ)。"""
    return text.replace("<", "&lt;")


def _build_existing_goals_block(existing_goals: list[str]) -> str:
    """4.7の入力例は既存の目標1件のみを`すでに入力済みの目標: <本文>`の1行で示す。
    複数件のときの表記は明記されていないため、同じ1行の形のまま「、」で連結する判断とした。
    1件も無い(初めて押した)場合は、AIに「重複を避ける対象が無い」ことが伝わるよう明記する。
    """
    if not existing_goals:
        return "すでに入力済みの目標: （まだ入力されていません）"
    joined = "、".join(_escape_user_input(goal) for goal in existing_goals)
    return f"すでに入力済みの目標: {joined}"


def build_messages(
    purpose_statement: str,
    area: str,
    ideal_state: str,
    existing_goals: list[str],
) -> list[MessageParam]:
    """4.7「入力の組み立て」のとおり`<purpose>`・`<ideal_state>`・`<existing_goals>`を組み立てる。"""
    escaped_purpose = _escape_user_input(purpose_statement)
    escaped_ideal_state = _escape_user_input(ideal_state)
    ideal_state_block = f"領域: {AREA_LABELS[area]}\n理想の状態: {escaped_ideal_state}"
    content = (
        f"<purpose>\nありたい姿: {escaped_purpose}\n</purpose>\n\n"
        f"<ideal_state>\n{ideal_state_block}\n</ideal_state>\n\n"
        f"<existing_goals>\n{_build_existing_goals_block(existing_goals)}\n</existing_goals>"
    )
    return [{"role": "user", "content": content}]


def validate_output(output: dict[str, Any]) -> None:
    """4.7「サーバ側の検証」。`hints`がちょうど3件、各要素が空でなく50文字以内。"""
    hints = output.get("hints")
    if not isinstance(hints, list) or len(hints) != 3:
        raise OutputValidationError("hints must have exactly 3 items")
    for hint in hints:
        if not isinstance(hint, str) or not hint or len(hint) > _MAX_HINT_LENGTH:
            raise OutputValidationError(f"each hint must be 1-{_MAX_HINT_LENGTH} chars")


def generate_goal_hints(
    purpose_statement: str,
    area: str,
    ideal_state: str,
    existing_goals: list[str],
    *,
    identifiers: dict[str, str] | None = None,
) -> GenerationResult:
    spec = PromptSpec(
        kind="GOAL_HINTS",
        model=models.SONNET,
        prompt_version=PROMPT_VERSION,
        effort=EFFORT,
        max_tokens=MAX_TOKENS,
        individual_block=INDIVIDUAL_BLOCK,
        schema=OUTPUT_SCHEMA,
        retry_on_invalid=False,
        timeout=TIMEOUT_SECONDS,
    )
    messages = build_messages(purpose_statement, area, ideal_state, existing_goals)
    return generate(spec, messages, validate_output=validate_output, identifiers=identifiers)
