"""選択式24問(S-12)から、自由記述(S-14)の対象項目とコミット度の段階を確定する。

05_質問・コンテンツ設計3.3(自由記述の例外パターン)・4.1(コミット度)。
同じ入力から同じ結果が出るこの判定は、AIではなくコードが行う
(スキルflourish-ai「AIにやらせないこと」)。P-01(P2-5)はこの結果を受け取り、
どの項目を取り上げるかを考えずに問い文を書くだけになる。
"""

from dataclasses import dataclass

from app.core.errors import UnprocessableEntityError
from app.domain.growth_stage import SEED, SEEDLING, SPROUT, TREE
from app.domain.questions import AREAS, COMMITMENT, SATISFACTION, QuestionSet

SATISFIED = "SATISFIED"
CONCERN = "CONCERN"
FREE_TEXT_SLOTS = (SATISFIED, CONCERN)

# 05_質問・コンテンツ設計4.1「合計スコア→段階」
_COMMITMENT_STAGE_THRESHOLDS = (
    (0, 3, SEED),
    (4, 7, SPROUT),
    (8, 11, SEEDLING),
    (12, 16, TREE),
)


@dataclass(frozen=True)
class ScaleAnswer:
    area: str
    question_kind: str
    score: int
    item_code: str | None = None


@dataclass(frozen=True)
class FreeTextTarget:
    """1領域につき、自由記述2問(SATISFIED/CONCERN)それぞれの対象項目。"""

    area: str
    satisfied_item_code: str
    concern_item_code: str
    all_high: bool  # 5項目すべて3以上(3.3)。問い2の文言を切り替える判断材料
    all_low: bool  # 5項目すべて1以下(3.3)。問い1の文言を切り替える判断材料
    all_same: bool  # 5項目すべて同スコア(3.3)


@dataclass(frozen=True)
class CommitmentResult:
    score: int  # 4領域のQ6合計。0〜16
    stage: str  # GrowthStage


@dataclass(frozen=True)
class FreeTextAnswer:
    area: str
    slot: str  # SATISFIED/CONCERN
    target_item_code: str
    generated_question: str
    body: str | None


def validate_scale_answers(scale_answers: list[ScaleAnswer], question_set: QuestionSet) -> None:
    """`scale_answers`がちょうど24件で、(area, question_kind, item_code)の組が揃うことを確認する。

    `09_API設計`5.2の「件数」「重複」の2検証をまとめて行う。件数が24件ちょうどでも組に重複が
    あれば、必然的に別の組が欠ける。**どちらも同じ`ANSWERS_INCOMPLETE`として扱う判断とした**
    (5.2は重複時のcodeを明記していない。件数不足と同じ「揃っていない」事実であるため)。
    `POST /assessments`(P2-8)も同じ検証を使う(5.3「整合」)。
    """
    expected: set[tuple[str, str, str | None]] = {
        (item.area, SATISFACTION, item.code) for item in question_set.items
    }
    expected |= {(area, COMMITMENT, None) for area in AREAS}
    received = {(answer.area, answer.question_kind, answer.item_code) for answer in scale_answers}

    if len(scale_answers) != 24 or received != expected:
        raise UnprocessableEntityError(
            "ANSWERS_INCOMPLETE",
            f"scale_answers must be exactly 24 unique (area, question_kind, item_code) "
            f"combinations (received {len(scale_answers)})",
        )


def validate_free_text_answers(free_text_answers: list[FreeTextAnswer]) -> None:
    """`free_text_answers`がちょうど8件で、(area, slot)の組が4領域×2スロット揃うことを確認する。

    `09_API設計`5.3「自由記述の件数」「問い文」の検証。`body`はnull/空文字を許容する
    (全問空欄でも成立する)一方、`generated_question`は必須(AIが毎回変わるため、
    回答だけでは意味が復元できない)。件数不足・組の不整合は`validate_scale_answers`と
    同じ`ANSWERS_INCOMPLETE`を再利用する判断とした(P2-5完了メモの重複時の判断を踏襲。
    どちらも「揃っていない」という同じ事実であるため)。
    """
    expected = {(area, slot) for area in AREAS for slot in FREE_TEXT_SLOTS}
    received = {(answer.area, answer.slot) for answer in free_text_answers}

    if len(free_text_answers) != 8 or received != expected:
        raise UnprocessableEntityError(
            "ANSWERS_INCOMPLETE",
            f"free_text_answers must be exactly 8 unique (area, slot) "
            f"combinations (received {len(free_text_answers)})",
        )

    for answer in free_text_answers:
        if not answer.target_item_code:
            raise UnprocessableEntityError(
                "ANSWERS_INCOMPLETE", "free_text_answers.target_item_code is required"
            )
        if not answer.generated_question:
            raise UnprocessableEntityError(
                "ANSWERS_INCOMPLETE", "free_text_answers.generated_question is required"
            )


def pick_free_text_targets(
    scale_answers: list[ScaleAnswer], question_set: QuestionSet
) -> tuple[FreeTextTarget, ...]:
    """領域ごとに、最高／最低の充足感項目を選ぶ(3.3)。

    並び順は`question_set`が定める領域内の項目順(2.3)を基準とする。
    同スコアは並び順が先のものを優先し、5項目すべて同スコアのときだけ
    先頭を問い1、末尾を問い2の対象にする(3.3「5項目すべて同スコア」)。
    """
    scores_by_item_code = {
        answer.item_code: answer.score
        for answer in scale_answers
        if answer.question_kind == SATISFACTION
    }

    targets = []
    for area in AREAS:
        area_items = [item for item in question_set.items if item.area == area]
        scored_items = [(item, scores_by_item_code[item.code]) for item in area_items]
        scores = [score for _, score in scored_items]

        all_same = len(set(scores)) == 1
        all_high = all(score >= 3 for score in scores)
        all_low = all(score <= 1 for score in scores)

        if all_same:
            satisfied_item = scored_items[0][0]
            concern_item = scored_items[-1][0]
        else:
            max_score = max(scores)
            min_score = min(scores)
            satisfied_item = next(item for item, score in scored_items if score == max_score)
            concern_item = next(item for item, score in scored_items if score == min_score)

        targets.append(
            FreeTextTarget(
                area=area,
                satisfied_item_code=satisfied_item.code,
                concern_item_code=concern_item.code,
                all_high=all_high,
                all_low=all_low,
                all_same=all_same,
            )
        )

    return tuple(targets)


def compute_commitment(scale_answers: list[ScaleAnswer]) -> CommitmentResult:
    """コミット度(Q6)4領域分の合計と段階(4.1)。"""
    score = sum(answer.score for answer in scale_answers if answer.question_kind == COMMITMENT)

    for low, high, stage in _COMMITMENT_STAGE_THRESHOLDS:
        if low <= score <= high:
            return CommitmentResult(score=score, stage=stage)

    raise ValueError(f"commitment score out of range (0-16): {score}")
