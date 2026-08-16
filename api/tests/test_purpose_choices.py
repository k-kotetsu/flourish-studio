"""S-31選択肢マスタのサーバー側対応表(app/domain/purpose_choices.py)。"""

import pytest

from app.core.errors import UnprocessableEntityError
from app.domain.purpose_choices import ChoiceAnswer, option_labels, validate_choices


def _valid_choices() -> list[ChoiceAnswer]:
    return [
        ChoiceAnswer(question_code="Q1", option_codes=["GROWTH", "FREEDOM"]),
        ChoiceAnswer(question_code="Q2", option_codes=["SELF_DETERMINED"]),
        ChoiceAnswer(question_code="Q3", option_codes=["HAVING_OPTIONS"]),
    ]


def test_option_labels_translates_codes_to_japanese() -> None:
    assert option_labels("Q1", ["GROWTH", "FREEDOM"]) == ["成長", "自由"]
    assert option_labels("Q3", ["HAVING_OPTIONS"]) == ["選択肢を持てる状態になっている"]


def test_validate_choices_accepts_a_valid_set() -> None:
    validate_choices(_valid_choices())  # raises on failure


def test_validate_choices_rejects_missing_question() -> None:
    choices = _valid_choices()[:2]
    with pytest.raises(UnprocessableEntityError) as exc_info:
        validate_choices(choices)
    assert exc_info.value.code == "CHOICES_INVALID"


def test_validate_choices_rejects_duplicate_question() -> None:
    choices = _valid_choices()
    choices[2] = ChoiceAnswer(question_code="Q1", option_codes=["GROWTH"])
    with pytest.raises(UnprocessableEntityError):
        validate_choices(choices)


def test_validate_choices_rejects_unknown_option_code() -> None:
    choices = _valid_choices()
    choices[0] = ChoiceAnswer(question_code="Q1", option_codes=["NOT_A_REAL_CODE"])
    with pytest.raises(UnprocessableEntityError):
        validate_choices(choices)


def test_validate_choices_rejects_q1_over_max_selection() -> None:
    choices = _valid_choices()
    choices[0] = ChoiceAnswer(
        question_code="Q1", option_codes=["GROWTH", "FREEDOM", "STABILITY", "CHALLENGE"]
    )
    with pytest.raises(UnprocessableEntityError):
        validate_choices(choices)


def test_validate_choices_rejects_q1_empty() -> None:
    choices = _valid_choices()
    choices[0] = ChoiceAnswer(question_code="Q1", option_codes=[])
    with pytest.raises(UnprocessableEntityError):
        validate_choices(choices)


def test_validate_choices_rejects_q3_with_more_than_one() -> None:
    choices = _valid_choices()
    choices[2] = ChoiceAnswer(
        question_code="Q3", option_codes=["HAVING_OPTIONS", "ROOM_TO_BREATHE"]
    )
    with pytest.raises(UnprocessableEntityError):
        validate_choices(choices)


def test_validate_choices_rejects_q3_empty() -> None:
    choices = _valid_choices()
    choices[2] = ChoiceAnswer(question_code="Q3", option_codes=[])
    with pytest.raises(UnprocessableEntityError):
        validate_choices(choices)
