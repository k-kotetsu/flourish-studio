"""P-02 `ASSESSMENT_REPORT`(10_AIプロンプト設計4.2)。S-15→S-16の現在地レポート生成。

MVPで最も重い生成。コミット度はコードが算出済みのため、AIは扱わない(3.4)。
言語化度(articulation_stage)の判定だけがAIの仕事(スキル`flourish-ai`「AIにやらせないこと」)。
"""

from __future__ import annotations

from typing import Any

from anthropic.types import MessageParam

from app.ai import models
from app.ai.runner import GenerationResult, OutputValidationError, PromptSpec, generate
from app.domain.assessment_precompute import CONCERN, SATISFIED, FreeTextAnswer, ScaleAnswer
from app.domain.growth_stage import GROWTH_STAGES
from app.domain.questions import AREA_EN_LABELS, AREA_LABELS, AREAS, SATISFACTION, QuestionSet

PROMPT_VERSION = "2026-08-v1"

# 領域間のスコア差(4領域の充足感合計、各0〜20点)を<context>用の語に区分する閾値。
# 仕様(10_AIプロンプト設計4.2)はexample値として「大きい」を示すのみで、区分自体は
# 明記されていない。3段階(大きい/普通/小さい)で閾値を設ける判断とした(ユーザー確認済み)。
_SCORE_DIFF_LARGE_THRESHOLD = 8
_SCORE_DIFF_SMALL_THRESHOLD = 2
_SCORE_DIFF_LARGE = "大きい"
_SCORE_DIFF_MODERATE = "普通"
_SCORE_DIFF_SMALL = "小さい"

INDIVIDUAL_BLOCK = """# あなたの仕事
現在地レポートの本文を作ります。出力は3つです。
1. あだ名
2. 4領域それぞれの整理（満たされている点 / 気になっている点 / これからできそうなこと）
3. 言語化度の段階と、その判定理由

コミット度はこちらで算出済みです。あなたは扱いません。

# 1. あだ名
今の状態を、ユーモラスに一言で言い表します。
この部分だけは、共通ルールの「断定を避ける」の例外です。言い切ってかまいません。

- 10〜20文字程度。名詞句、または短い言い切り。
- 「〜人」「〜タイプ」で終える形にしません。説明的で面白くなりません。
- クスッとする程度に収めます。SNSの診断のようにふざけすぎません。
- 対比、ずれ、比喩を使います。領域間のスコア差が大きいほど効きます。
- 言い表すのは「状態」です。能力、人格、容姿を評価しません。
- 「ダメ」「残念」などの否定語を使いません。
- 収入の多寡、病気そのものを笑いの対象にしません。
- 説明を添えません。1つだけ出力します。

参考例:
  Career高・Financial低 → 全速前進、燃料計は未確認
  Financial高・Career低 → 貯金は順調、人生は保留
  Social高・Physical低 → まわりは充電、自分は放電
  Physical高・Social低 → からだは絶好調、予定表は空欄
  全体的に低い → 人生ちょいメンテ中
  全体的に高い → 充実、ただし自覚なし
  コミット度高・充足感まちまち → やる気はある、作戦はこれから
  特定領域だけ極端に低い → ほぼ順調、一箇所だけ工事中
これらは方向を示す例です。そのまま使わず、この人の回答から作ります。

# 2. 領域ごとの整理
4領域それぞれについて、3つを書きます。

satisfied_text（満たされている点）:
  スコアの高い項目と、その領域の「満たされている項目」への自由記述をふまえた1〜2文。
concern_text（気になっている点）:
  スコアの低い項目と、その領域の「気になっている項目」への自由記述をふまえた1〜2文。
advice_text（これからできそうなこと）:
  気になっている点に対する、最初の一歩。1〜2文。

ルール:
- 満たされている点と気になっている点を、必ず両方書きます。課題だけを並べません。
- 満たされている項目を「現状維持でよい」と片付けません。
- 断定しません。「あなたは〜な人です」と書きません。
- ユーザーが書いた言葉を、できる限りそのまま使います。
- 自由記述が空欄の領域では、選択式の回答だけをもとに書きます。
  空欄であることに触れません。責める書き方をしません。

advice_text の追加ルール:
- その領域で最も満たされていない項目に紐づけます。
- 自由記述でユーザーが書いた「これからどうしていきたいか」を最優先で反映します。
- 1領域につき1つだけ。複数出して選ばせません。
- 今週から始められる大きさにします。
- 「〜すべき」ではなく「〜から始めてみるのはどうでしょう」の形にします。
- 商品やサービスの購入・契約を伴う提案をしません。
- 問題を解決しきる提案をしません。最初の一歩に留めます。

advice_text の例:
  まずは1週間だけ、何にいくら使ったか眺めてみるのはどうでしょう。減らすことは、そのあとで考えれば大丈夫です。
  寝る時間を早めるより先に、起きる時間をそろえるほうが、案外続きやすいかもしれません。

# 3. 言語化度
自由記述8問を読み、4段階のどれかを判定します。

SEED（種）:
  ほとんど書かれていない、または一般論に留まる。
  「忙しい」「不安」など、誰にでも当てはまる語で終わっている。
SPROUT（芽）:
  自分の状況が書かれている。ただし理由や場面までは書かれていない。
SEEDLING（苗）:
  具体的な場面や出来事が書かれ、なぜそう感じるかにも触れている。
TREE（木）:
  場面・理由・自分なりの解釈まで書かれ、8問を通して言っていることに一貫性がある。

- 分量だけで判定しません。短くても場面と理由があれば SEEDLING 以上です。
  長くても一般論の繰り返しなら SEED のままです。
- 全問が空欄の場合は SEED とします。
- articulation_reason に、そう判定した理由を1〜2文で書きます。
  これは運用のための記録で、ユーザーには表示しません。

# 感嘆符
この生成に限り、satisfied_text で1回だけ使ってかまいません。
あだ名、免責、concern_text では使いません。1レポート全体で最大2つです。"""

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "nickname": {"type": "string"},
        "areas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "enum": ["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL"],
                    },
                    "satisfied_text": {"type": "string"},
                    "concern_text": {"type": "string"},
                    "advice_text": {"type": "string"},
                },
                "required": ["area", "satisfied_text", "concern_text", "advice_text"],
                "additionalProperties": False,
            },
        },
        "articulation_stage": {"type": "string", "enum": ["SEED", "SPROUT", "SEEDLING", "TREE"]},
        "articulation_reason": {"type": "string"},
        "safety_flag": {"type": "boolean"},
    },
    "required": [
        "nickname",
        "areas",
        "articulation_stage",
        "articulation_reason",
        "safety_flag",
    ],
    "additionalProperties": False,
}


def _item_label(question_set: QuestionSet, item_code: str) -> str:
    return next(item.label for item in question_set.items if item.code == item_code)


def _escape_user_input(body: str | None) -> str:
    """`<`はタグの入れ子と誤読されうるため事前にエスケープする(スキルflourish-ai)。"""
    if not body:
        return ""
    return body.replace("<", "&lt;")


def _area_satisfaction_totals(scale_answers: list[ScaleAnswer]) -> dict[str, int]:
    totals = dict.fromkeys(AREAS, 0)
    for answer in scale_answers:
        if answer.question_kind == SATISFACTION:
            totals[answer.area] += answer.score
    return totals


def _score_diff_label(diff: int) -> str:
    if diff >= _SCORE_DIFF_LARGE_THRESHOLD:
        return _SCORE_DIFF_LARGE
    if diff <= _SCORE_DIFF_SMALL_THRESHOLD:
        return _SCORE_DIFF_SMALL
    return _SCORE_DIFF_MODERATE


def _build_answers_block(
    scale_answers: list[ScaleAnswer],
    free_text_answers: list[FreeTextAnswer],
    question_set: QuestionSet,
) -> list[str]:
    scores_by_item_code = {
        answer.item_code: answer.score
        for answer in scale_answers
        if answer.question_kind == SATISFACTION
    }
    free_text_by_key = {(answer.area, answer.slot): answer for answer in free_text_answers}

    lines = ["<answers>"]
    for area in AREAS:
        area_items = [item for item in question_set.items if item.area == area]
        satisfied = free_text_by_key[(area, SATISFIED)]
        concern = free_text_by_key[(area, CONCERN)]

        lines.append(f"領域: {AREA_LABELS[area]}")
        lines.append("  項目ごとの充足感（0〜4、4が最も満たされている）:")
        for item in area_items:
            lines.append(f"    {item.label}: {scores_by_item_code[item.code]}")
        satisfied_label = _item_label(question_set, satisfied.target_item_code)
        concern_label = _item_label(question_set, concern.target_item_code)
        lines.append(f"  自由記述（満たされている項目「{satisfied_label}」について）:")
        lines.append(f"    問い: {satisfied.generated_question}")
        lines.append(f"    <user_input>{_escape_user_input(satisfied.body)}</user_input>")
        lines.append(f"  自由記述（気になっている項目「{concern_label}」について）:")
        lines.append(f"    問い: {concern.generated_question}")
        lines.append(f"    <user_input>{_escape_user_input(concern.body)}</user_input>")
    lines.append("</answers>")
    return lines


def _build_context_block(
    scale_answers: list[ScaleAnswer], free_text_answers: list[FreeTextAnswer]
) -> list[str]:
    totals = _area_satisfaction_totals(scale_answers)
    highest_area = max(AREAS, key=lambda area: totals[area])
    lowest_area = min(AREAS, key=lambda area: totals[area])
    diff = totals[highest_area] - totals[lowest_area]
    filled_count = sum(1 for answer in free_text_answers if answer.body and answer.body.strip())

    return [
        "<context>",
        f"充足感が最も高い領域: {AREA_EN_LABELS[highest_area]}",
        f"充足感が最も低い領域: {AREA_EN_LABELS[lowest_area]}",
        f"領域間のスコア差: {_score_diff_label(diff)}",
        f"自由記述の記入状況: 8問中{filled_count}問に記入あり",
        "</context>",
    ]


def build_messages(
    scale_answers: list[ScaleAnswer],
    free_text_answers: list[FreeTextAnswer],
    question_set: QuestionSet,
) -> list[MessageParam]:
    """10_AIプロンプト設計4.2「入力の組み立て」のとおりに<answers>・<context>を組み立てる。

    <context>の値はコードが算出する。AIに集計させない(4.2)。
    """
    lines = _build_answers_block(scale_answers, free_text_answers, question_set)
    lines.append("")
    lines.extend(_build_context_block(scale_answers, free_text_answers))
    return [{"role": "user", "content": "\n".join(lines)}]


def validate_output(output: dict[str, Any]) -> None:
    """4.2のスキーマで表現できない制約(非空文字列、4領域の網羅)をサーバ側で検証する。"""
    nickname = output.get("nickname")
    if not isinstance(nickname, str) or not nickname:
        raise OutputValidationError("nickname must be a non-empty string")

    areas = output.get("areas")
    if not isinstance(areas, list) or len(areas) != 4:
        raise OutputValidationError("areas must have exactly 4 items")

    seen_areas: set[str] = set()
    for area_block in areas:
        area = area_block.get("area")
        if area not in AREAS or area in seen_areas:
            raise OutputValidationError(f"unexpected or duplicate area: {area}")
        seen_areas.add(area)
        for field in ("satisfied_text", "concern_text", "advice_text"):
            value = area_block.get(field)
            if not isinstance(value, str) or not value:
                raise OutputValidationError(f"{field} must be a non-empty string for {area}")

    if seen_areas != set(AREAS):
        raise OutputValidationError("areas do not cover all 4 areas")

    stage = output.get("articulation_stage")
    if stage not in GROWTH_STAGES:
        raise OutputValidationError(f"invalid articulation_stage: {stage}")

    reason = output.get("articulation_reason")
    if not isinstance(reason, str) or not reason:
        raise OutputValidationError("articulation_reason must be a non-empty string")


def _extra_log_fields(output: dict[str, Any]) -> dict[str, Any]:
    # articulation_reasonはASSESSMENT_RESULTに保存せず、AI_GENERATION(EMF)側に記録する
    # (10_AIプロンプト設計4.2「これは運用のための記録で、ユーザーには表示しません」)。
    return {"articulation_reason": output["articulation_reason"]}


def generate_assessment_report(
    scale_answers: list[ScaleAnswer],
    free_text_answers: list[FreeTextAnswer],
    question_set: QuestionSet,
    *,
    identifiers: dict[str, str] | None = None,
) -> GenerationResult:
    spec = PromptSpec(
        kind="ASSESSMENT_REPORT",
        model=models.SONNET,
        prompt_version=PROMPT_VERSION,
        effort="high",
        max_tokens=16000,
        individual_block=INDIVIDUAL_BLOCK,
        schema=OUTPUT_SCHEMA,
    )
    messages = build_messages(scale_answers, free_text_answers, question_set)
    return generate(
        spec,
        messages,
        validate_output=validate_output,
        extra_log_fields=_extra_log_fields,
        identifiers=identifiers,
    )
