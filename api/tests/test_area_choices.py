"""S-51選択肢マスタのサーバー側対応表(app/domain/area_choices.py)。"""

import pytest

from app.core.errors import UnprocessableEntityError
from app.domain.area_choices import ChoiceAnswer, option_labels, validate_area_choices


def _valid_choices() -> list[ChoiceAnswer]:
    return [
        ChoiceAnswer(question_code="Q1", option_codes=["CAREER_OUTLOOK"]),
        ChoiceAnswer(
            question_code="Q2", option_codes=["CAREER_VALUE_GROWTH", "CAREER_VALUE_AUTONOMY"]
        ),
        ChoiceAnswer(question_code="Q3", option_codes=["CAREER_POSITION_GROWTH"]),
    ]


def test_option_labels_translates_q1_from_the_area_item_master() -> None:
    assert option_labels("CAREER", "Q1", ["CAREER_OUTLOOK"]) == ["今後のキャリアの見通し"]


def test_option_labels_translates_q2_and_q3_per_area() -> None:
    assert option_labels("CAREER", "Q2", ["CAREER_VALUE_GROWTH"]) == ["自分の成長を実感できること"]
    assert option_labels("FINANCIAL", "Q3", ["FINANCIAL_POSITION_FOUNDATION"]) == [
        "安心の土台であってほしい"
    ]


def test_option_labels_are_area_scoped() -> None:
    # Careerのcodeは他領域では未知の扱いになる(混在防止)
    with pytest.raises(KeyError):
        option_labels("FINANCIAL", "Q1", ["CAREER_OUTLOOK"])


def test_validate_area_choices_accepts_a_valid_set() -> None:
    validate_area_choices("CAREER", _valid_choices())  # raises on failure


def test_validate_area_choices_rejects_missing_question() -> None:
    choices = _valid_choices()[:2]
    with pytest.raises(UnprocessableEntityError) as exc_info:
        validate_area_choices("CAREER", choices)
    assert exc_info.value.code == "CHOICES_INVALID"


def test_validate_area_choices_rejects_duplicate_question() -> None:
    choices = _valid_choices()
    choices[2] = ChoiceAnswer(question_code="Q1", option_codes=["CAREER_GROWTH"])
    with pytest.raises(UnprocessableEntityError):
        validate_area_choices("CAREER", choices)


def test_validate_area_choices_rejects_unknown_option_code() -> None:
    choices = _valid_choices()
    choices[0] = ChoiceAnswer(question_code="Q1", option_codes=["NOT_A_REAL_CODE"])
    with pytest.raises(UnprocessableEntityError):
        validate_area_choices("CAREER", choices)


def test_validate_area_choices_rejects_an_item_code_from_another_area() -> None:
    choices = _valid_choices()
    choices[0] = ChoiceAnswer(question_code="Q1", option_codes=["FINANCIAL_SAVINGS"])
    with pytest.raises(UnprocessableEntityError):
        validate_area_choices("CAREER", choices)


def test_validate_area_choices_rejects_q1_with_more_than_one() -> None:
    choices = _valid_choices()
    choices[0] = ChoiceAnswer(
        question_code="Q1", option_codes=["CAREER_OUTLOOK", "CAREER_GROWTH"]
    )
    with pytest.raises(UnprocessableEntityError):
        validate_area_choices("CAREER", choices)


def test_validate_area_choices_rejects_q1_empty() -> None:
    choices = _valid_choices()
    choices[0] = ChoiceAnswer(question_code="Q1", option_codes=[])
    with pytest.raises(UnprocessableEntityError):
        validate_area_choices("CAREER", choices)


def test_validate_area_choices_rejects_q2_empty() -> None:
    choices = _valid_choices()
    choices[1] = ChoiceAnswer(question_code="Q2", option_codes=[])
    with pytest.raises(UnprocessableEntityError):
        validate_area_choices("CAREER", choices)


def test_validate_area_choices_allows_q2_and_q3_without_an_upper_limit() -> None:
    choices = _valid_choices()
    choices[1] = ChoiceAnswer(
        question_code="Q2",
        option_codes=[
            "CAREER_VALUE_GROWTH",
            "CAREER_VALUE_CONTRIBUTION",
            "CAREER_VALUE_RECOGNITION",
            "CAREER_VALUE_RELATIONSHIPS",
            "CAREER_VALUE_AUTONOMY",
            "CAREER_VALUE_STABILITY",
            "CAREER_VALUE_INCOME_GROWTH",
            "CAREER_VALUE_CHALLENGE",
            "CAREER_VALUE_EXPERTISE",
            "CAREER_VALUE_WORK_LIFE_BALANCE",
        ],
    )
    validate_area_choices("CAREER", choices)  # raises on failure
