"""P-07 `GOAL_HINTS`の入力組み立てと出力検証(10_AIプロンプト設計4.7)。"""

from typing import Any

import pytest

from app.ai.prompts.goal_hints import build_messages, validate_output
from app.ai.runner import OutputValidationError

PURPOSE_STATEMENT = "まわりの人が安心して力を出せる存在でありたい。"
IDEAL_STATE = (
    "今の仕事の中で自分の強みが言葉になっていて、次に何を任されたいかを自分から言えている。"
)


def _valid_output() -> dict[str, Any]:
    return {
        "hints": [
            "職務経歴書を書き上げる",
            "月に1回、社外の人と話す",
            "半期に1つ、新しい役割に手を挙げる",
        ],
    }


# --- build_messages ---


def test_build_messages_includes_purpose_ideal_state_and_existing_goals() -> None:
    messages = build_messages(
        PURPOSE_STATEMENT, "CAREER", IDEAL_STATE, ["職務経歴書を書き上げる"]
    )

    assert len(messages) == 1
    content = messages[0]["content"]
    assert f"ありたい姿: {PURPOSE_STATEMENT}" in content
    assert "領域: Career（仕事・働き方）" in content
    assert f"理想の状態: {IDEAL_STATE}" in content
    assert "すでに入力済みの目標: 職務経歴書を書き上げる" in content


def test_build_messages_lists_multiple_existing_goals_on_one_line() -> None:
    messages = build_messages(
        PURPOSE_STATEMENT,
        "CAREER",
        IDEAL_STATE,
        ["職務経歴書を書き上げる", "月に1回、社外の人と話す"],
    )

    content = messages[0]["content"]
    assert "すでに入力済みの目標: 職務経歴書を書き上げる、月に1回、社外の人と話す" in content


def test_build_messages_marks_no_existing_goals() -> None:
    messages = build_messages(PURPOSE_STATEMENT, "CAREER", IDEAL_STATE, [])

    content = messages[0]["content"]
    assert "すでに入力済みの目標: （まだ入力されていません）" in content


def test_build_messages_escapes_user_input() -> None:
    messages = build_messages(
        "<script>やばい</script>", "CAREER", "<b>理想</b>", ["<i>目標</i>"]
    )

    content = messages[0]["content"]
    assert "<script>" not in content
    assert "&lt;script>やばい&lt;/script>" in content
    assert "&lt;b>理想&lt;/b>" in content
    assert "&lt;i>目標&lt;/i>" in content


# --- validate_output ---


def test_validate_output_accepts_a_valid_response() -> None:
    validate_output(_valid_output())  # 例外を送出しなければ合格


def test_validate_output_rejects_fewer_than_three_hints() -> None:
    output = _valid_output()
    output["hints"].pop()

    with pytest.raises(OutputValidationError):
        validate_output(output)


def test_validate_output_rejects_more_than_three_hints() -> None:
    output = _valid_output()
    output["hints"].append("4つ目")

    with pytest.raises(OutputValidationError):
        validate_output(output)


def test_validate_output_rejects_empty_hint() -> None:
    output = _valid_output()
    output["hints"][0] = ""

    with pytest.raises(OutputValidationError):
        validate_output(output)


def test_validate_output_rejects_hint_over_50_chars() -> None:
    output = _valid_output()
    output["hints"][0] = "あ" * 51

    with pytest.raises(OutputValidationError):
        validate_output(output)
