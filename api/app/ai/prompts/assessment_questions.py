"""P-01 `ASSESSMENT_QUESTIONS`(10_AIプロンプト設計4.1)。S-13→S-14の自由記述8問の問い文を生成する。

対象項目(領域ごとの最高/最低スコア項目、例外パターン)はコードが選び終えており
(P2-4 `assessment_precompute.pick_free_text_targets`)、AIは渡された項目について
問い文を書くだけになる(スキル`flourish-ai`「AIにやらせないこと」)。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anthropic.types import MessageParam

from app.ai import models
from app.ai.runner import GenerationResult, OutputValidationError, PromptSpec, generate
from app.domain.assessment_precompute import ScaleAnswer, pick_free_text_targets
from app.domain.questions import AREA_LABELS, SATISFACTION, QuestionSet

PROMPT_VERSION = "2026-08-v1"

_EXCEPTION_NONE = "なし"
_EXCEPTION_ALL_HIGH = "全項目が高い"
_EXCEPTION_ALL_LOW = "全項目が低い"

SATISFIED = "SATISFIED"
CONCERN = "CONCERN"

_MAX_TEXT_LENGTH = 200

INDIVIDUAL_BLOCK = """# あなたの仕事
渡された8つの対象項目について、ユーザーが自分の状況を書きやすくなる問い文を1つずつ作ります。
対象項目を選ぶ作業は済んでいます。あなたは選ばれた項目について問いを書くだけです。

# 問いの型
「満たされている項目」への問い：
  いまどんな状況で、なぜそう感じているのかを聞きます。
「気になっている項目」への問い：
  いまどう感じていて、これからどうしていきたいかを聞きます。

# 基本の言い回し
満たされている項目:
  {領域}の中では「{項目名}」が満たされているようですね。いまどんな状況で、なぜそう感じているのか、書ける範囲で教えてもらえますか。
気になっている項目:
  一方で「{項目名}」は、少し気になっているようですね。いまどう感じていて、これからどうしていきたいですか。

# 例外パターンの言い換え
例外パターンが「全項目が高い」のとき、その領域の気になっている項目への問いを次に差し替えます:
  あえて挙げるとすれば「{項目名}」でしょうか。ここについて、思うところはありますか。
例外パターンが「全項目が低い」のとき、その領域の満たされている項目への問いを次に差し替えます:
  この中では「{項目名}」が比較的まだ保たれているようです。どんな状況ですか。

# ルール
- 項目名は渡された表記をそのまま使います。言い換えません。
- 1つの問いは2文以内に収めます。
- 問い文にユーザーへの評価を含めません。
- 答えを誘導する例示を入れません。
- 基本の言い回しをそのまま使ってかまいません。領域や項目に合わせて自然にする範囲の調整は認めます。
- 8件すべてを、渡された順序どおりに出力します。"""

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "enum": ["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL"],
                    },
                    "slot": {"type": "string", "enum": ["SATISFIED", "CONCERN"]},
                    "target_item_code": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["area", "slot", "target_item_code", "text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["questions"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class QuestionTarget:
    """`<targets>`ブロック1領域分。P2-4の`FreeTextTarget`に、問い文作成に要るスコアを添えたもの。

    SQSメッセージ経由でワーカーに渡すための平坦な形(dataclasses.asdict/**で変換できる)。
    """

    area: str
    satisfied_item_code: str
    concern_item_code: str
    satisfied_score: int
    concern_score: int
    all_high: bool
    all_low: bool


def build_targets(
    scale_answers: list[ScaleAnswer], question_set: QuestionSet
) -> list[QuestionTarget]:
    """P2-4の対象項目選定に、問い文作成用のスコアを添えて返す。"""
    scores_by_item_code = {
        answer.item_code: answer.score
        for answer in scale_answers
        if answer.question_kind == SATISFACTION
    }
    free_text_targets = pick_free_text_targets(scale_answers, question_set)
    return [
        QuestionTarget(
            area=target.area,
            satisfied_item_code=target.satisfied_item_code,
            concern_item_code=target.concern_item_code,
            satisfied_score=scores_by_item_code[target.satisfied_item_code],
            concern_score=scores_by_item_code[target.concern_item_code],
            all_high=target.all_high,
            all_low=target.all_low,
        )
        for target in free_text_targets
    ]


def _exception_pattern(target: QuestionTarget) -> str:
    if target.all_high:
        return _EXCEPTION_ALL_HIGH
    if target.all_low:
        return _EXCEPTION_ALL_LOW
    return _EXCEPTION_NONE


def _item_label(question_set: QuestionSet, item_code: str) -> str:
    return next(item.label for item in question_set.items if item.code == item_code)


def build_messages(
    targets: list[QuestionTarget], question_set: QuestionSet
) -> list[MessageParam]:
    """10_AIプロンプト設計4.1「入力の組み立て」のとおりに`<targets>`ブロックを組み立てる。"""
    lines = [
        "以下は、あるユーザーの現在地レポート選択式の回答から、",
        "問いの対象となる項目をこちらで選び出したものです。",
        "",
        "<targets>",
    ]
    for target in targets:
        satisfied_label = _item_label(question_set, target.satisfied_item_code)
        concern_label = _item_label(question_set, target.concern_item_code)
        lines.append(f"領域: {AREA_LABELS[target.area]}")
        lines.append(f"  満たされている項目: {satisfied_label}（5段階中{target.satisfied_score}）")
        lines.append(f"  気になっている項目: {concern_label}（5段階中{target.concern_score}）")
        lines.append(f"  例外パターン: {_exception_pattern(target)}")
    lines.append("</targets>")
    return [{"role": "user", "content": "\n".join(lines)}]


def validate_output(output: dict[str, Any], targets: list[QuestionTarget]) -> None:
    """4.1「サーバ側の検証」。件数・組の網羅と重複・対象項目の一致・文字数を確認する。"""
    questions = output.get("questions")
    if not isinstance(questions, list) or len(questions) != 8:
        raise OutputValidationError("questions must have exactly 8 items")

    expected_item_code: dict[tuple[str, str], str] = {}
    for target in targets:
        expected_item_code[(target.area, SATISFIED)] = target.satisfied_item_code
        expected_item_code[(target.area, CONCERN)] = target.concern_item_code

    seen_keys: set[tuple[str, str]] = set()
    for question in questions:
        key = (question.get("area"), question.get("slot"))
        if key not in expected_item_code:
            raise OutputValidationError(f"unexpected (area, slot) pair: {key}")
        if key in seen_keys:
            raise OutputValidationError(f"duplicate (area, slot) pair: {key}")
        seen_keys.add(key)

        if question.get("target_item_code") != expected_item_code[key]:
            raise OutputValidationError(
                f"target_item_code mismatch for {key}: {question.get('target_item_code')}"
            )

        text = question.get("text")
        if not isinstance(text, str) or not text or len(text) > _MAX_TEXT_LENGTH:
            raise OutputValidationError(f"text must be 1-{_MAX_TEXT_LENGTH} chars for {key}")

    if seen_keys != set(expected_item_code):
        raise OutputValidationError("questions do not cover all 8 (area, slot) pairs")


def generate_assessment_questions(
    targets: list[QuestionTarget],
    question_set: QuestionSet,
    *,
    identifiers: dict[str, str] | None = None,
) -> GenerationResult:
    spec = PromptSpec(
        kind="ASSESSMENT_QUESTIONS",
        model=models.SONNET,
        prompt_version=PROMPT_VERSION,
        effort="medium",
        max_tokens=8000,
        individual_block=INDIVIDUAL_BLOCK,
        schema=OUTPUT_SCHEMA,
    )
    messages = build_messages(targets, question_set)
    return generate(
        spec,
        messages,
        validate_output=lambda output: validate_output(output, targets),
        identifiers=identifiers,
    )
