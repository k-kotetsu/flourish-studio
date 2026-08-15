import dataclasses

from app.domain import questions


def test_areas_has_four_values() -> None:
    assert questions.AREAS == ("CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL")


def test_question_kinds_has_satisfaction_and_commitment() -> None:
    assert questions.QUESTION_KINDS == ("SATISFACTION", "COMMITMENT")


def test_current_version_is_registered() -> None:
    assert questions.CURRENT_QUESTION_SET_VERSION in questions.QUESTION_SETS


def test_get_question_set_returns_the_matching_version() -> None:
    question_set = questions.get_question_set(questions.CURRENT_QUESTION_SET_VERSION)

    assert question_set.version == questions.CURRENT_QUESTION_SET_VERSION


def test_get_question_set_raises_for_unknown_version() -> None:
    try:
        questions.get_question_set("does-not-exist")
    except KeyError:
        pass
    else:
        raise AssertionError("KeyError が送出されるはず")


def test_items_has_five_per_area_with_no_duplicate_codes() -> None:
    question_set = questions.get_question_set(questions.CURRENT_QUESTION_SET_VERSION)

    assert len(question_set.items) == 20
    codes = [item.code for item in question_set.items]
    assert len(set(codes)) == 20

    for area in questions.AREAS:
        area_items = [item for item in question_set.items if item.area == area]
        assert len(area_items) == 5


def test_choices_are_five_stages_scored_zero_to_four() -> None:
    question_set = questions.get_question_set(questions.CURRENT_QUESTION_SET_VERSION)

    for choices in (question_set.satisfaction_choices, question_set.commitment_choices):
        assert [choice.score for choice in choices] == [0, 1, 2, 3, 4]


def test_adding_a_new_version_does_not_remove_the_old_one() -> None:
    """08_データモデル1.2「過去バージョンの定義は消さない」を、辞書のキー追加で満たせることを確認する。"""
    original = questions.get_question_set(questions.CURRENT_QUESTION_SET_VERSION)
    hypothetical_next = dataclasses.replace(original, version="2099-01-v2")

    extended_sets = {**questions.QUESTION_SETS, "2099-01-v2": hypothetical_next}

    assert extended_sets[questions.CURRENT_QUESTION_SET_VERSION] is original
    assert extended_sets["2099-01-v2"] is hypothetical_next
