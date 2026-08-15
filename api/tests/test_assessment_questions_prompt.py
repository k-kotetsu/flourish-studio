"""P-01 `ASSESSMENT_QUESTIONS`の入力組み立てと出力検証(10_AIプロンプト設計4.1)。"""

from typing import Any

from app.ai.prompts.assessment_questions import (
    QuestionTarget,
    build_messages,
    build_targets,
    validate_output,
)
from app.ai.runner import OutputValidationError
from app.domain import questions
from app.domain.assessment_precompute import ScaleAnswer

_QUESTION_SET = questions.get_question_set(questions.CURRENT_QUESTION_SET_VERSION)


def _all_areas_scale_answers() -> list[ScaleAnswer]:
    answers = []
    for area in questions.AREAS:
        item_codes = [item.code for item in _QUESTION_SET.items if item.area == area]
        for code, score in zip(item_codes, [4, 3, 2, 1, 0], strict=True):
            answers.append(
                ScaleAnswer(
                    area=area, question_kind=questions.SATISFACTION, item_code=code, score=score
                )
            )
        answers.append(ScaleAnswer(area=area, question_kind=questions.COMMITMENT, score=2))
    return answers


def _targets() -> list[QuestionTarget]:
    return build_targets(_all_areas_scale_answers(), _QUESTION_SET)


def _valid_output(targets: list[QuestionTarget]) -> dict[str, Any]:
    questions_out = []
    for target in targets:
        questions_out.append(
            {
                "area": target.area,
                "slot": "SATISFIED",
                "target_item_code": target.satisfied_item_code,
                "text": "いまどんな状況ですか。",
            }
        )
        questions_out.append(
            {
                "area": target.area,
                "slot": "CONCERN",
                "target_item_code": target.concern_item_code,
                "text": "これからどうしていきたいですか。",
            }
        )
    return {"questions": questions_out}


def test_build_targets_returns_one_per_area_with_scores() -> None:
    targets = _targets()

    assert [target.area for target in targets] == list(questions.AREAS)
    for target in targets:
        assert target.satisfied_score == 4  # 各領域とも先頭項目(スコア4)が最高
        assert target.concern_score == 0  # 末尾項目(スコア0)が最低


def test_build_messages_renders_targets_block() -> None:
    targets = _targets()

    messages = build_messages(targets, _QUESTION_SET)

    assert len(messages) == 1
    content = messages[0]["content"]
    assert "<targets>" in content
    assert "</targets>" in content
    assert "領域: Career（仕事・働き方）" in content
    assert "例外パターン: なし" in content


def test_build_messages_switches_wording_for_all_high_and_all_low() -> None:
    question_set = questions.get_question_set(questions.CURRENT_QUESTION_SET_VERSION)
    career_codes = [item.code for item in question_set.items if item.area == "CAREER"]
    financial_codes = [item.code for item in question_set.items if item.area == "FINANCIAL"]
    targets = [
        QuestionTarget(
            area="CAREER",
            satisfied_item_code=career_codes[0],
            concern_item_code=career_codes[1],
            satisfied_score=4,
            concern_score=3,
            all_high=True,
            all_low=False,
        ),
        QuestionTarget(
            area="FINANCIAL",
            satisfied_item_code=financial_codes[0],
            concern_item_code=financial_codes[1],
            satisfied_score=1,
            concern_score=0,
            all_high=False,
            all_low=True,
        ),
    ]

    content = build_messages(targets, question_set)[0]["content"]

    assert "例外パターン: 全項目が高い" in content
    assert "例外パターン: 全項目が低い" in content


def test_validate_output_accepts_a_valid_response() -> None:
    targets = _targets()

    validate_output(_valid_output(targets), targets)  # 例外を送出しなければ合格


def test_validate_output_rejects_wrong_item_count() -> None:
    targets = _targets()
    output = _valid_output(targets)
    output["questions"].pop()

    try:
        validate_output(output, targets)
    except OutputValidationError:
        pass
    else:
        raise AssertionError("OutputValidationError が送出されるはず")


def test_validate_output_rejects_target_item_code_mismatch() -> None:
    targets = _targets()
    output = _valid_output(targets)
    output["questions"][0]["target_item_code"] = "WRONG_CODE"

    try:
        validate_output(output, targets)
    except OutputValidationError:
        pass
    else:
        raise AssertionError("OutputValidationError が送出されるはず")
