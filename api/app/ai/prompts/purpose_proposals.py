"""P-04 `PURPOSE_PROPOSALS`(10_AIプロンプト設計4.4)。S-33→S-34のありたい姿3案生成。

選択式3問の回答と対話全文を渡す(P-03と同じ入力形式)。`<choices>`・`<conversation>`の
組み立ては`purpose_dialogue`と共有する(`<turn>`は含めない。3往復完了後に一括で
3案を生成するため、往復目の概念自体が無い)。
"""

from __future__ import annotations

from typing import Any

from anthropic.types import MessageParam

from app.ai import models
from app.ai.prompts.purpose_dialogue import (
    DialogueMessage,
    build_choices_block,
    build_conversation_block,
)
from app.ai.runner import GenerationResult, OutputValidationError, PromptSpec, generate
from app.domain.purpose_choices import ChoiceAnswer

PROMPT_VERSION = "2026-08-v1"

DIRECTIONS = ("SELF", "OTHERS", "SOCIETY")
_MAX_STATEMENT_LENGTH = 60
_MAX_LABEL_LENGTH = 20

INDIVIDUAL_BLOCK = """# あなたの仕事
ユーザーの「ありたい姿」の候補を3案作ります。
3〜5年後を見据えたものです。

# 3案の軸
向かう先の広さで分けます。この軸は固定です。回答内容で変えません。

SELF（自分の内側）: 自分がどうありたいか
OTHERS（身近な他者）: 周囲の人との関係の中でどうありたいか
SOCIETY（より広い社会）: 社会や世の中に対して何をしたいか

3案は、同じ内容の言い換えにしません。異なる観点を持たせます。
選ぶこと自体に意味があるようにします。

# 出力の形式
statement:
  原則として一文。
  「〜でありたい」「〜していきたい」の形を基本とします。
  上限は60文字。40文字以内を推奨します。
  ホーム画面のカードで2行に収まる長さです。
label:
  その案がどの方向を向いているかを示す短い言葉。10文字程度。

例:
  SELF    / 自分の納得を軸に   / 自分で選んだと言えることを積み重ねて生きていきたい。
  OTHERS  / まわりの人とともに / まわりの人が安心して力を出せる存在でありたい。
  SOCIETY / もっと広く         / 人の可能性が広がる場をつくっていきたい。

# ルール
- 対話でユーザーが使った言葉を、できる限りそのまま活かします。
- 選択式で選ばれた価値観が、3案すべてに何らかの形で反映されている必要があります。
- ユーザーが言っていない価値観を持ち込みません。
- 職業名、会社名、具体的な役職を入れません。「ありたい姿」は領域横断の概念です。
- 3案を SELF、OTHERS、SOCIETY の順に出力します。"""

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "proposals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": list(DIRECTIONS)},
                    "label": {"type": "string"},
                    "statement": {"type": "string"},
                },
                "required": ["direction", "label", "statement"],
                "additionalProperties": False,
            },
        },
        "safety_flag": {"type": "boolean"},
    },
    "required": ["proposals", "safety_flag"],
    "additionalProperties": False,
}


def build_messages(
    choices: list[ChoiceAnswer], messages: list[DialogueMessage]
) -> list[MessageParam]:
    """4.4「入力」のとおり`<choices>`・`<conversation>`を組み立てる(P-03と同じ形式)。"""
    content = (
        f"<choices>\n{build_choices_block(choices)}\n</choices>\n\n"
        f"<conversation>\n{build_conversation_block(messages)}\n</conversation>"
    )
    return [{"role": "user", "content": content}]


def validate_output(output: dict[str, Any]) -> None:
    """4.4「サーバ側の検証」。件数・方向の網羅と重複、文字数、statementの相互不一致を確認する。"""
    proposals = output.get("proposals")
    if not isinstance(proposals, list) or len(proposals) != 3:
        raise OutputValidationError("proposals must have exactly 3 items")

    seen_directions: set[str] = set()
    statements: list[str] = []
    for proposal in proposals:
        direction = proposal.get("direction")
        if direction not in DIRECTIONS or direction in seen_directions:
            raise OutputValidationError(f"unexpected or duplicate direction: {direction}")
        seen_directions.add(direction)

        label = proposal.get("label")
        if not isinstance(label, str) or not label or len(label) > _MAX_LABEL_LENGTH:
            raise OutputValidationError(
                f"label must be 1-{_MAX_LABEL_LENGTH} chars for {direction}"
            )

        statement = proposal.get("statement")
        if (
            not isinstance(statement, str)
            or not statement
            or len(statement) > _MAX_STATEMENT_LENGTH
        ):
            raise OutputValidationError(
                f"statement must be 1-{_MAX_STATEMENT_LENGTH} chars for {direction}"
            )
        statements.append(statement)

    if seen_directions != set(DIRECTIONS):
        raise OutputValidationError("proposals do not cover all 3 directions")

    if len(set(statements)) != len(statements):
        raise OutputValidationError("statements must not be identical to each other")


def generate_purpose_proposals(
    choices: list[ChoiceAnswer],
    messages: list[DialogueMessage],
    *,
    identifiers: dict[str, str] | None = None,
) -> GenerationResult:
    spec = PromptSpec(
        kind="PURPOSE_PROPOSALS",
        model=models.SONNET,
        prompt_version=PROMPT_VERSION,
        effort="high",
        max_tokens=8000,
        individual_block=INDIVIDUAL_BLOCK,
        schema=OUTPUT_SCHEMA,
    )
    built_messages = build_messages(choices, messages)
    return generate(
        spec, built_messages, validate_output=validate_output, identifiers=identifiers
    )
