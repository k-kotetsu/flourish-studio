"""P-02 `ASSESSMENT_REPORT`(10_AIプロンプト設計4.2)の入力組み立てと出力検証。"""

from typing import Any

import pytest

from app.ai.prompts import assessment_report
from app.ai.runner import OutputValidationError
from app.domain import questions
from app.domain.assessment_precompute import FreeTextAnswer, ScaleAnswer, pick_free_text_targets

_QUESTION_SET = questions.get_question_set(questions.CURRENT_QUESTION_SET_VERSION)


def _scale_answers(career_scores: list[int]) -> list[ScaleAnswer]:
    answers = []
    item_codes = {
        area: [item.code for item in _QUESTION_SET.items if item.area == area]
        for area in questions.AREAS
    }
    for code, score in zip(item_codes[questions.CAREER], career_scores, strict=True):
        answers.append(
            ScaleAnswer(area=questions.CAREER, question_kind=questions.SATISFACTION,
                        item_code=code, score=score)
        )
    for area in (questions.FINANCIAL, questions.PHYSICAL, questions.SOCIAL):
        for code, score in zip(item_codes[area], [4, 3, 2, 1, 0], strict=True):
            answers.append(
                ScaleAnswer(area=area, question_kind=questions.SATISFACTION,
                            item_code=code, score=score)
            )
    for area in questions.AREAS:
        answers.append(ScaleAnswer(area=area, question_kind=questions.COMMITMENT, score=2))
    return answers


def _free_text_answers(
    scale_answers: list[ScaleAnswer],
    *,
    career_satisfied_body: str | None = "任される範囲が広がった",
) -> list[FreeTextAnswer]:
    answers = []
    for target in pick_free_text_targets(scale_answers, _QUESTION_SET):
        answers.append(
            FreeTextAnswer(
                area=target.area,
                slot="SATISFIED",
                target_item_code=target.satisfied_item_code,
                generated_question="いまどんな状況ですか。",
                body=career_satisfied_body if target.area == questions.CAREER else "回答本文",
            )
        )
        answers.append(
            FreeTextAnswer(
                area=target.area,
                slot="CONCERN",
                target_item_code=target.concern_item_code,
                generated_question="これからどうしたいですか。",
                body=None,
            )
        )
    return answers


def test_build_messages_includes_all_five_items_per_area_and_context_block() -> None:
    # Career: 高スコア寄り(合計14) / Financial: 低スコア寄り(合計10、以下同値)。
    # 差は4(普通レンジ)になる想定。
    scale_answers = _scale_answers([4, 3, 3, 2, 2])
    free_text_answers = _free_text_answers(scale_answers)

    messages = assessment_report.build_messages(scale_answers, free_text_answers, _QUESTION_SET)

    content = messages[0]["content"]
    assert "<answers>" in content
    assert "領域: Career（仕事・働き方）" in content
    assert "項目ごとの充足感（0〜4、4が最も満たされている）:" in content
    assert "<user_input>任される範囲が広がった</user_input>" in content
    assert "<user_input></user_input>" in content  # bodyがNoneの場合は空文字
    assert "<context>" in content
    assert "充足感が最も高い領域: Career" in content
    assert "自由記述の記入状況: 8問中" in content


def test_build_messages_escapes_angle_bracket_in_user_input() -> None:
    scale_answers = _scale_answers([4, 3, 2, 1, 0])
    free_text_answers = _free_text_answers(scale_answers, career_satisfied_body="<script>だめ")

    messages = assessment_report.build_messages(scale_answers, free_text_answers, _QUESTION_SET)

    content = messages[0]["content"]
    assert "<script>" not in content
    assert "&lt;script&gt;だめ" not in content  # >はエスケープ対象外(仕様は<のみ)
    assert "&lt;script>だめ" in content


def test_build_messages_labels_large_score_gap_as_large() -> None:
    # Career合計20(満点)、Financial合計0。差20 → 大きい
    scale_answers = _scale_answers([4, 4, 4, 4, 4])
    for i, answer in enumerate(scale_answers):
        if answer.area == questions.FINANCIAL and answer.question_kind == questions.SATISFACTION:
            scale_answers[i] = ScaleAnswer(
                area=questions.FINANCIAL, question_kind=questions.SATISFACTION,
                item_code=answer.item_code, score=0,
            )
    free_text_answers = _free_text_answers(scale_answers)

    messages = assessment_report.build_messages(scale_answers, free_text_answers, _QUESTION_SET)

    content = messages[0]["content"]
    assert "領域間のスコア差: 大きい" in content


def _valid_output() -> dict[str, Any]:
    return {
        "nickname": "全速前進、燃料計は未確認",
        "areas": [
            {
                "area": area,
                "satisfied_text": "満たされている点があります。",
                "concern_text": "気になる点もあります。",
                "advice_text": "少しずつ試してみるのはどうでしょう。",
            }
            for area in questions.AREAS
        ],
        "articulation_stage": "SPROUT",
        "articulation_reason": "具体的な状況が書かれているため。",
        "safety_flag": False,
    }


def test_validate_output_accepts_a_well_formed_report() -> None:
    assessment_report.validate_output(_valid_output())  # 例外が出ないことを確認


def test_validate_output_rejects_missing_area() -> None:
    output = _valid_output()
    output["areas"] = output["areas"][:-1]  # 3件のみ

    with pytest.raises(OutputValidationError):
        assessment_report.validate_output(output)


def test_validate_output_rejects_duplicate_area() -> None:
    output = _valid_output()
    output["areas"][-1] = dict(output["areas"][0])  # SOCIALの代わりにCAREERを重複

    with pytest.raises(OutputValidationError):
        assessment_report.validate_output(output)


def test_validate_output_rejects_empty_advice_text() -> None:
    output = _valid_output()
    output["areas"][0]["advice_text"] = ""

    with pytest.raises(OutputValidationError):
        assessment_report.validate_output(output)


def test_validate_output_rejects_unknown_articulation_stage() -> None:
    output = _valid_output()
    output["articulation_stage"] = "UNKNOWN"

    with pytest.raises(OutputValidationError):
        assessment_report.validate_output(output)


def test_validate_output_rejects_empty_articulation_reason() -> None:
    output = _valid_output()
    output["articulation_reason"] = ""

    with pytest.raises(OutputValidationError):
        assessment_report.validate_output(output)
