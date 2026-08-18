"""P-08 `REFLECTION_SUMMARY`(10_AIプロンプト設計4.8)。S-62→S-63のWeekly Reflection整理。

3段階評価・自由記述・ありたい姿・目標一覧から、振り返り/気づき/次の一歩の3要素を
全体で1つだけ生成する(領域ごとに分けない)。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from anthropic.types import MessageParam

from app.ai import models
from app.ai.runner import GenerationResult, OutputValidationError, PromptSpec, generate
from app.domain.questions import AREA_LABELS, AREAS
from app.domain.reflection import STATUS_LABELS, ResolvedStatus

PROMPT_VERSION = "2026-08-v1"

# 3項目とも300文字以内(4.8「サーバ側の検証」)。
_MAX_FIELD_LENGTH = 300
# next_stepが複数提案を含まないことの検証(4.8「必ず1つに絞ります」)。
_MULTI_PROPOSAL_MARKERS = ("または", "もしくは")

INDIVIDUAL_BLOCK = """# あなたの仕事
1週間の振り返りを、3つの要素に整理します。

looking_back（振り返り）: 今週どのような動きがあったか。2〜3文。
insight（気づき）: 目標の進み方や課題から見える傾向。2〜3文。
next_step（次の一歩）: 翌週に取り組める、小さく具体的な行動。1つだけ。

# 全体に対して1つ返す
領域ごとに4つのコメントを返しません。
人生全体と Flourish Map のつながりをふまえ、まとまりとして1つ返します。

# 3段階の扱い
「進んでいる」: 前に進んでいる状態です。
「止まっている」: 動きがなかった状態です。否定的に扱いません。責めません。
  止まった理由を決めつけません。自由記述に理由が書かれている場合だけ、それに触れます。
「見直したい」: 目標そのものを変えたいという意思表示です。
  肯定的に受け止めます。変えることは失敗ではありません。

# next_step のルール
- 必ず1つに絞ります。複数提示して選ばせません。
- 来週の1週間で取り組める大きさにします。
- 「止まっている」「見直したい」が選ばれた目標の中から選ぶことを基本とします。
  すべて「進んでいる」の場合は、その勢いを続けるための一歩にします。
- 「〜すべき」ではなく「〜してみるのはどうでしょう」の形にします。
- 商品やサービスの購入・契約を伴う提案をしません。

# ありたい姿とのつながり
insight または looking_back のどこかで、ありたい姿とのつながりに一度だけ触れます。
毎回すべての文で結びつけません。くどくなります。

# 自由記述が空欄のとき
3段階評価だけをもとに書きます。空欄であることに触れません。

# 使わない表現
ユーザーを評価する語を使いません。
「頑張っていますね」「素晴らしい」「よくできています」「もっと〜すべき」

# 感嘆符
使いません。"""

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "looking_back": {"type": "string"},
        "insight": {"type": "string"},
        "next_step": {"type": "string"},
        "safety_flag": {"type": "boolean"},
    },
    "required": ["looking_back", "insight", "next_step", "safety_flag"],
    "additionalProperties": False,
}


def _escape_user_input(body: str | None) -> str:
    """`<`はタグの入れ子と誤読されうるため事前にエスケープする(スキルflourish-ai)。"""
    if not body:
        return ""
    return body.replace("<", "&lt;")


def build_messages(
    purpose_statement: str,
    statuses: Sequence[ResolvedStatus],
    area_ideal_states: Mapping[str, str],
    note: str | None,
) -> list[MessageParam]:
    """4.8「入力の組み立て」のとおりに<purpose>・<goals>・<note>を組み立てる。

    未作成の領域は含めない(4.8「存在しない領域について言及させないため、渡さない」)。
    """
    lines = ["<purpose>", f"ありたい姿: {purpose_statement}", "</purpose>", "", "<goals>"]
    for area in AREAS:
        area_statuses = [status for status in statuses if status.area == area]
        if not area_statuses:
            continue
        lines.append(f"領域: {AREA_LABELS[area]}")
        lines.append(f"  理想の状態: {area_ideal_states[area]}")
        for index, status in enumerate(area_statuses, start=1):
            lines.append(f"  目標{index}「{status.goal_body}」: {STATUS_LABELS[status.status]}")
    lines.append("</goals>")
    lines.append("")
    lines.append("<note>")
    lines.append(f"<user_input>{_escape_user_input(note)}</user_input>")
    lines.append("</note>")
    return [{"role": "user", "content": "\n".join(lines)}]


def validate_output(output: dict[str, Any]) -> None:
    """4.8「サーバ側の検証」。スキーマで表現できない件数・文字数・複数提案の禁止を確認する。"""
    for field in ("looking_back", "insight", "next_step"):
        value = output.get(field)
        if not isinstance(value, str) or not value:
            raise OutputValidationError(f"{field} must be a non-empty string")
        if len(value) > _MAX_FIELD_LENGTH:
            raise OutputValidationError(f"{field} must be at most {_MAX_FIELD_LENGTH} characters")

    next_step = output["next_step"]
    if any(marker in next_step for marker in _MULTI_PROPOSAL_MARKERS):
        raise OutputValidationError("next_step must not contain multiple proposals")


def generate_reflection_summary(
    purpose_statement: str,
    statuses: Sequence[ResolvedStatus],
    area_ideal_states: Mapping[str, str],
    note: str | None,
    *,
    identifiers: dict[str, str] | None = None,
) -> GenerationResult:
    spec = PromptSpec(
        kind="REFLECTION_SUMMARY",
        model=models.SONNET,
        prompt_version=PROMPT_VERSION,
        effort="medium",
        max_tokens=6000,
        individual_block=INDIVIDUAL_BLOCK,
        schema=OUTPUT_SCHEMA,
    )
    messages = build_messages(purpose_statement, statuses, area_ideal_states, note)
    return generate(
        spec,
        messages,
        validate_output=validate_output,
        identifiers=identifiers,
    )
