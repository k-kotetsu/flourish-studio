"""P-06 `AREA_PROPOSALS`(10_AIプロンプト設計4.6)。S-53→S-54の理想状態3案生成。

確定済みの「ありたい姿」・対象領域・S-51の選択式回答・S-52の対話全文を渡す。`<choices>`の
組み立ては`area_dialogue`(P-05)と、`<conversation>`・`DialogueMessage`は`purpose_dialogue`
(P-03)と共有する(`PURPOSE_PROPOSALS`が`purpose_dialogue`のビルダー関数を共有する
のと同じ考え方)。`<turn>`は含めない(往復目の概念が無い、`PURPOSE_PROPOSALS`と同じ)。

**サーバ側の検証は`PURPOSE_PROPOSALS`と異なり、3案の順序も固定で確認する。**
4.6「順序は DEEPEN、CHANGE、EXPAND で固定します。ユーザーの回答で並べ替えません」
(サーバ側の検証欄も「P-04と同じ（3件、direction重複なし、順序固定、相互不一致）」と、
P-04には無かった「順序固定」を明示的に加えている)。
"""

from __future__ import annotations

from typing import Any

from anthropic.types import MessageParam

from app.ai import models
from app.ai.prompts.area_dialogue import build_choices_block
from app.ai.prompts.purpose_dialogue import DialogueMessage, build_conversation_block
from app.ai.runner import GenerationResult, OutputValidationError, PromptSpec, generate
from app.domain.area_choices import ChoiceAnswer
from app.domain.questions import AREA_LABELS

PROMPT_VERSION = "2026-08-v1"

DIRECTIONS = ("DEEPEN", "CHANGE", "EXPAND")
_MAX_IDEAL_STATE_LENGTH = 200
_MAX_LABEL_LENGTH = 20

INDIVIDUAL_BLOCK = """# あなたの仕事
この領域における「1年後の理想の状態」の候補を3案作ります。

# 3案の軸
深める / 変える / 広げる の3方向で差をつけます。この軸は固定です。
ありたい姿の3案（自分/他者/社会）とは別の軸です。

DEEPEN（深める）: 今あるものの質を上げる
CHANGE（変える）: やり方や進め方を変える
EXPAND（広げる）: 新しい場所や関係に出ていく

順序は DEEPEN、CHANGE、EXPAND で固定します。ユーザーの回答で並べ替えません。
どの方向にも等しく可能性があることを示すためです。

# 案の中身
Q2（大切にしたいこと）と Q3（人生の中での位置づけ）を、各案の中身を作る材料として使います。
3案すべてに、選ばれた価値観と位置づけが反映されている必要があります。

# 出力の形式
ideal_state:
  1年後の状態として、原則1〜2文。
  「〜になっている」「〜できている」の形を基本とします。
  100文字以内を目安にします。
label:
  方向を示す短い言葉。10文字程度。

例（Career・「今後のキャリアの見通し」を選択した場合）:
  DEEPEN / 今の場所で深める /
    今の仕事の中で自分の強みが言葉になっていて、次に何を任されたいかを自分から言えている。
  CHANGE / やり方を変える   / 働き方や役割を一度組み替えて、自分に合う進め方が見つかっている。
  EXPAND / 外に出る         / 社外の人と接点があり、今の会社の外でも通用する選択肢を持てている。

# ルール
- 確定済みの「ありたい姿」につながっている必要があります。ただし文中で復唱はしません。
- 対話でユーザーが使った言葉を、できる限りそのまま活かします。
- 転職、退職、引っ越し、借入、投資商品の購入など、
  大きな決断そのものを理想状態として書きません。
- Physical 領域では、体重、体脂肪率、数値目標を書きません。
  診断や治療に関わる表現も使いません。
- Financial 領域では、具体的な金額、利率、商品名を書きません。
- 3案の内容が相互に言い換えにならないようにします。"""

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
                    "ideal_state": {"type": "string"},
                },
                "required": ["direction", "label", "ideal_state"],
                "additionalProperties": False,
            },
        },
        "safety_flag": {"type": "boolean"},
    },
    "required": ["proposals", "safety_flag"],
    "additionalProperties": False,
}


def _escape_user_input(text: str) -> str:
    """`<`はタグの入れ子と誤読されうるため事前にエスケープする(area_dialogue.pyと同じ)。"""
    return text.replace("<", "&lt;")


def build_messages(
    purpose_statement: str,
    area: str,
    choices: list[ChoiceAnswer],
    messages: list[DialogueMessage],
) -> list[MessageParam]:
    """`<purpose>`・`<area>`・`<choices>`・`<conversation>`を組み立てる(`<turn>`は含めない)。"""
    escaped_purpose = _escape_user_input(purpose_statement)
    content = (
        f"<purpose>\n確定した「ありたい姿」: {escaped_purpose}\n</purpose>\n\n"
        f"<area>\n対象領域: {AREA_LABELS[area]}\n</area>\n\n"
        f"<choices>\n{build_choices_block(area, choices)}\n</choices>\n\n"
        f"<conversation>\n{build_conversation_block(messages)}\n</conversation>"
    )
    return [{"role": "user", "content": content}]


def validate_output(output: dict[str, Any]) -> None:
    """4.6「サーバ側の検証」。P-04と同じ検証に加え、3案の順序がDIRECTIONS固定であることも確認する。"""
    proposals = output.get("proposals")
    if not isinstance(proposals, list) or len(proposals) != 3:
        raise OutputValidationError("proposals must have exactly 3 items")

    ideal_states: list[str] = []
    for expected_direction, proposal in zip(DIRECTIONS, proposals, strict=True):
        direction = proposal.get("direction")
        if direction != expected_direction:
            raise OutputValidationError(
                f"proposals must be ordered as {DIRECTIONS}, got {direction} "
                f"where {expected_direction} was expected"
            )

        label = proposal.get("label")
        if not isinstance(label, str) or not label or len(label) > _MAX_LABEL_LENGTH:
            raise OutputValidationError(
                f"label must be 1-{_MAX_LABEL_LENGTH} chars for {direction}"
            )

        ideal_state = proposal.get("ideal_state")
        if (
            not isinstance(ideal_state, str)
            or not ideal_state
            or len(ideal_state) > _MAX_IDEAL_STATE_LENGTH
        ):
            raise OutputValidationError(
                f"ideal_state must be 1-{_MAX_IDEAL_STATE_LENGTH} chars for {direction}"
            )
        ideal_states.append(ideal_state)

    if len(set(ideal_states)) != len(ideal_states):
        raise OutputValidationError("ideal_state must not be identical to each other")


def generate_area_proposals(
    purpose_statement: str,
    area: str,
    choices: list[ChoiceAnswer],
    messages: list[DialogueMessage],
    *,
    identifiers: dict[str, str] | None = None,
) -> GenerationResult:
    spec = PromptSpec(
        kind="AREA_PROPOSALS",
        model=models.SONNET,
        prompt_version=PROMPT_VERSION,
        effort="high",
        max_tokens=8000,
        individual_block=INDIVIDUAL_BLOCK,
        schema=OUTPUT_SCHEMA,
    )
    built_messages = build_messages(purpose_statement, area, choices, messages)
    return generate(
        spec, built_messages, validate_output=validate_output, identifiers=identifiers
    )
