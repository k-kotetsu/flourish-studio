from app.domain import growth_stage, questions
from app.domain.assessment_precompute import (
    FreeTextTarget,
    ScaleAnswer,
    compute_commitment,
    pick_free_text_targets,
)

_QUESTION_SET = questions.get_question_set(questions.CURRENT_QUESTION_SET_VERSION)


def _career_items() -> list[str]:
    return [item.code for item in _QUESTION_SET.items if item.area == questions.CAREER]


def _satisfaction_answers(area: str, scores: list[int]) -> list[ScaleAnswer]:
    """指定領域の5項目に、領域内の並び順どおりスコアを割り当てる。"""
    item_codes = [item.code for item in _QUESTION_SET.items if item.area == area]
    return [
        ScaleAnswer(area=area, question_kind=questions.SATISFACTION, item_code=code, score=score)
        for code, score in zip(item_codes, scores, strict=True)
    ]


def _all_areas_scale_answers(career_scores: list[int]) -> list[ScaleAnswer]:
    """CAREERだけ`career_scores`を使い、他領域はタイブレークが起きない値で埋める。"""
    answers = _satisfaction_answers(questions.CAREER, career_scores)
    for area in (questions.FINANCIAL, questions.PHYSICAL, questions.SOCIAL):
        answers += _satisfaction_answers(area, [4, 3, 2, 1, 0])
    for area in questions.AREAS:
        answers.append(
            ScaleAnswer(area=area, question_kind=questions.COMMITMENT, score=2)
        )
    return answers


def _career_target(career_scores: list[int]) -> FreeTextTarget:
    targets = pick_free_text_targets(_all_areas_scale_answers(career_scores), _QUESTION_SET)
    return next(target for target in targets if target.area == questions.CAREER)


def test_returns_one_target_per_area() -> None:
    targets = pick_free_text_targets(_all_areas_scale_answers([2, 4, 1, 3, 0]), _QUESTION_SET)

    assert [target.area for target in targets] == list(questions.AREAS)


def test_normal_case_picks_highest_and_lowest_scored_item() -> None:
    codes = _career_items()
    target = _career_target([2, 4, 1, 3, 0])  # 最高=index1, 最低=index4

    assert target.satisfied_item_code == codes[1]
    assert target.concern_item_code == codes[4]
    assert (target.all_high, target.all_low, target.all_same) == (False, False, False)


def test_tie_breaks_to_the_earlier_item_in_area_order() -> None:
    codes = _career_items()
    # 最高(4)はindex0とindex1で同点、最低(1)はindex3とindex4で同点
    target = _career_target([4, 4, 2, 1, 1])

    assert target.satisfied_item_code == codes[0]
    assert target.concern_item_code == codes[3]


def test_all_high_flags_and_still_targets_the_relative_lowest() -> None:
    codes = _career_items()
    target = _career_target([3, 4, 3, 4, 3])  # すべて3以上

    assert target.all_high is True
    assert target.all_low is False
    assert target.all_same is False
    assert target.satisfied_item_code == codes[1]  # 最初に4を取った項目
    assert target.concern_item_code == codes[0]  # 最初に3を取った項目


def test_all_low_flags_and_still_targets_the_relative_highest() -> None:
    codes = _career_items()
    target = _career_target([1, 0, 1, 0, 1])  # すべて1以下

    assert target.all_low is True
    assert target.all_high is False
    assert target.all_same is False
    assert target.satisfied_item_code == codes[0]  # 最初に1を取った項目
    assert target.concern_item_code == codes[1]  # 最初に0を取った項目


def test_all_same_score_uses_first_item_and_last_item() -> None:
    codes = _career_items()
    target = _career_target([2, 2, 2, 2, 2])

    assert target.all_same is True
    assert target.satisfied_item_code == codes[0]
    assert target.concern_item_code == codes[4]


def test_all_same_high_score_still_uses_first_and_last_not_tiebreak() -> None:
    """5項目すべて同スコアの規則は、全部高い場合でも優先される(3.3)。"""
    codes = _career_items()
    target = _career_target([3, 3, 3, 3, 3])

    assert (target.all_same, target.all_high) == (True, True)
    assert target.satisfied_item_code == codes[0]
    assert target.concern_item_code == codes[4]


def test_commitment_score_sums_the_four_areas() -> None:
    answers = [
        ScaleAnswer(area=area, question_kind=questions.COMMITMENT, score=score)
        for area, score in zip(questions.AREAS, [1, 2, 3, 4], strict=True)
    ]

    result = compute_commitment(answers)

    assert result.score == 10


def test_commitment_stage_boundaries() -> None:
    expected_stage_by_score = {
        0: growth_stage.SEED,
        3: growth_stage.SEED,
        4: growth_stage.SPROUT,
        7: growth_stage.SPROUT,
        8: growth_stage.SEEDLING,
        11: growth_stage.SEEDLING,
        12: growth_stage.TREE,
        16: growth_stage.TREE,
    }

    for total_score, expected_stage in expected_stage_by_score.items():
        per_area_score, remainder = divmod(total_score, 4)
        scores = [per_area_score] * 4
        scores[0] += remainder
        answers = [
            ScaleAnswer(area=area, question_kind=questions.COMMITMENT, score=score)
            for area, score in zip(questions.AREAS, scores, strict=True)
        ]

        result = compute_commitment(answers)

        assert result.score == total_score
        assert result.stage == expected_stage
