"""P-04 `PURPOSE_PROPOSALS`の入力組み立てと出力検証(10_AIプロンプト設計4.4)。"""

from typing import Any

import pytest

from app.ai.prompts.purpose_dialogue import DialogueMessage
from app.ai.prompts.purpose_proposals import build_messages, validate_output
from app.ai.runner import OutputValidationError
from app.domain.purpose_choices import ChoiceAnswer

CHOICES = [
    ChoiceAnswer(question_code="Q1", option_codes=["GROWTH", "FREEDOM"]),
    ChoiceAnswer(question_code="Q2", option_codes=["SELF_DETERMINED"]),
    ChoiceAnswer(question_code="Q3", option_codes=["HAVING_OPTIONS"]),
]

HISTORY = [
    DialogueMessage(role="AI", body="「成長」を選ばれていました。"),
    DialogueMessage(role="USER", body="前の職場で任される範囲が広がったときに実感しました。"),
]


def _valid_output() -> dict[str, Any]:
    return {
        "proposals": [
            {
                "direction": "SELF",
                "label": "自分の納得を軸に",
                "statement": "自分で選んだと言えることを積み重ねて生きていきたい。",
            },
            {
                "direction": "OTHERS",
                "label": "まわりの人とともに",
                "statement": "まわりの人が安心して力を出せる存在でありたい。",
            },
            {
                "direction": "SOCIETY",
                "label": "もっと広く",
                "statement": "人の可能性が広がる場をつくっていきたい。",
            },
        ],
        "safety_flag": False,
    }


# --- build_messages ---


def test_build_messages_includes_choices_and_conversation_no_turn() -> None:
    messages = build_messages(CHOICES, HISTORY)

    assert len(messages) == 1
    content = messages[0]["content"]
    assert "<choices>" in content
    assert "Q1 これからの3〜5年で大切にしたいこと（3つまで）: 成長 / 自由" in content
    assert "<conversation>" in content
    assert "AI: 「成長」を選ばれていました。" in content
    assert (
        "USER: <user_input>前の職場で任される範囲が広がったときに実感しました。</user_input>"
        in content
    )
    # P-03と違い往復目の概念が無いため<turn>は含まない
    assert "<turn>" not in content


# --- validate_output ---


def test_validate_output_accepts_a_valid_response() -> None:
    validate_output(_valid_output())  # 例外を送出しなければ合格


def test_validate_output_rejects_fewer_than_three_proposals() -> None:
    output = _valid_output()
    output["proposals"].pop()

    with pytest.raises(OutputValidationError):
        validate_output(output)


def test_validate_output_rejects_duplicate_direction() -> None:
    output = _valid_output()
    output["proposals"][1]["direction"] = "SELF"

    with pytest.raises(OutputValidationError):
        validate_output(output)


def test_validate_output_rejects_statement_over_60_chars() -> None:
    output = _valid_output()
    output["proposals"][0]["statement"] = "あ" * 61

    with pytest.raises(OutputValidationError):
        validate_output(output)


def test_validate_output_rejects_empty_label() -> None:
    output = _valid_output()
    output["proposals"][0]["label"] = ""

    with pytest.raises(OutputValidationError):
        validate_output(output)


def test_validate_output_rejects_identical_statements() -> None:
    output = _valid_output()
    output["proposals"][1]["statement"] = output["proposals"][0]["statement"]

    with pytest.raises(OutputValidationError):
        validate_output(output)
