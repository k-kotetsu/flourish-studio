"""P-06 `AREA_PROPOSALS`の入力組み立てと出力検証(10_AIプロンプト設計4.6)。"""

from typing import Any

import pytest

from app.ai.prompts.area_proposals import build_messages, validate_output
from app.ai.prompts.purpose_dialogue import DialogueMessage
from app.ai.runner import OutputValidationError
from app.domain.area_choices import ChoiceAnswer

PURPOSE_STATEMENT = "まわりの人が安心して力を出せる存在でありたい。"

CHOICES = [
    ChoiceAnswer(question_code="Q1", option_codes=["CAREER_OUTLOOK"]),
    ChoiceAnswer(
        question_code="Q2", option_codes=["CAREER_VALUE_GROWTH", "CAREER_VALUE_AUTONOMY"]
    ),
    ChoiceAnswer(question_code="Q3", option_codes=["CAREER_POSITION_GROWTH"]),
]

HISTORY = [
    DialogueMessage(role="AI", body="「今後のキャリアの見通し」を選ばれていました。"),
    DialogueMessage(role="USER", body="前の職場で任される範囲が広がったときに実感しました。"),
]


def _valid_output() -> dict[str, Any]:
    return {
        "proposals": [
            {
                "direction": "DEEPEN",
                "label": "今の場所で深める",
                "ideal_state": "今の仕事の中で自分の強みが言葉になっている。",
            },
            {
                "direction": "CHANGE",
                "label": "やり方を変える",
                "ideal_state": "働き方や役割を一度組み替えて、自分に合う進め方が見つかっている。",
            },
            {
                "direction": "EXPAND",
                "label": "外に出る",
                "ideal_state": "社外の人と接点があり、今の会社の外でも通用する選択肢を持てている。",
            },
        ],
        "safety_flag": False,
    }


# --- build_messages ---


def test_build_messages_includes_purpose_area_choices_and_conversation_no_turn() -> None:
    messages = build_messages(PURPOSE_STATEMENT, "CAREER", CHOICES, HISTORY)

    assert len(messages) == 1
    content = messages[0]["content"]
    assert f"確定した「ありたい姿」: {PURPOSE_STATEMENT}" in content
    assert "対象領域: Career（仕事・働き方）" in content
    assert "Q1 3〜5年後にいちばん変わっていてほしいこと（1つ）: 今後のキャリアの見通し" in content
    assert "Q2 これからの仕事で特に大切にしたいこと（複数）:" in content
    assert "自分の成長を実感できること / 自分で決められる裁量があること" in content
    assert "<conversation>" in content
    assert "AI: 「今後のキャリアの見通し」を選ばれていました。" in content
    assert (
        "USER: <user_input>前の職場で任される範囲が広がったときに実感しました。</user_input>"
        in content
    )
    # P-04と違い往復目の概念が無いため<turn>は含まない
    assert "<turn>" not in content


def test_build_messages_escapes_purpose_statement() -> None:
    messages = build_messages("<script>やばい</script>", "CAREER", CHOICES, [])
    content = messages[0]["content"]
    assert "<script>" not in content
    assert "&lt;script>やばい&lt;/script>" in content


# --- validate_output ---


def test_validate_output_accepts_a_valid_response() -> None:
    validate_output(_valid_output())  # 例外を送出しなければ合格


def test_validate_output_rejects_fewer_than_three_proposals() -> None:
    output = _valid_output()
    output["proposals"].pop()

    with pytest.raises(OutputValidationError):
        validate_output(output)


def test_validate_output_rejects_out_of_order_directions() -> None:
    """4.6「順序は DEEPEN、CHANGE、EXPAND で固定します」。P-04と異なりorderも検証する。"""
    output = _valid_output()
    output["proposals"] = list(reversed(output["proposals"]))

    with pytest.raises(OutputValidationError):
        validate_output(output)


def test_validate_output_rejects_duplicate_direction() -> None:
    output = _valid_output()
    output["proposals"][1]["direction"] = "DEEPEN"

    with pytest.raises(OutputValidationError):
        validate_output(output)


def test_validate_output_rejects_ideal_state_over_200_chars() -> None:
    output = _valid_output()
    output["proposals"][0]["ideal_state"] = "あ" * 201

    with pytest.raises(OutputValidationError):
        validate_output(output)


def test_validate_output_rejects_empty_label() -> None:
    output = _valid_output()
    output["proposals"][0]["label"] = ""

    with pytest.raises(OutputValidationError):
        validate_output(output)


def test_validate_output_rejects_identical_ideal_states() -> None:
    output = _valid_output()
    output["proposals"][1]["ideal_state"] = output["proposals"][0]["ideal_state"]

    with pytest.raises(OutputValidationError):
        validate_output(output)
