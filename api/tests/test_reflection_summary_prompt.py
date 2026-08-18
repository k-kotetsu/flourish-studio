"""P-08 `REFLECTION_SUMMARY`の入力組み立てと出力検証(10_AIプロンプト設計4.8)。"""

from typing import Any

import pytest

from app.ai.prompts.reflection_summary import build_messages, validate_output
from app.ai.runner import OutputValidationError
from app.domain.reflection import ResolvedStatus

STATUSES = [
    ResolvedStatus(
        goal_key="g-career-1",
        area="CAREER",
        goal_body="職務経歴書を書き上げる",
        status="ON_TRACK",
    ),
    ResolvedStatus(
        goal_key="g-career-2",
        area="CAREER",
        goal_body="月に1回、社外の人と話す",
        status="STALLED",
    ),
    ResolvedStatus(
        goal_key="g-financial-1",
        area="FINANCIAL",
        goal_body="毎月の支出を把握する",
        status="REVISE",
    ),
]

AREA_IDEAL_STATES = {
    "CAREER": "今の仕事の中で自分の強みが言葉になっている状態。",
    "FINANCIAL": "毎月の収支を自分で把握できている状態。",
}


def _valid_output() -> dict[str, Any]:
    return {
        "looking_back": "Careerの2つは前に進み、職務経歴書も書き上げられたようですね。",
        "insight": "動けた目標には、その日のうちに終わる大きさがありました。",
        "next_step": "来週は、1日1回アプリを開くだけにしてみるのはどうでしょう。",
        "safety_flag": False,
    }


# --- build_messages ---


def test_build_messages_includes_purpose_goals_and_note() -> None:
    messages = build_messages(
        "まわりの人が安心して力を出せる存在でありたい。",
        STATUSES,
        AREA_IDEAL_STATES,
        "今週は残業が続いて、時間が取れなかった",
    )

    assert len(messages) == 1
    content = messages[0]["content"]
    assert "<purpose>" in content
    assert "ありたい姿: まわりの人が安心して力を出せる存在でありたい。" in content
    assert "<goals>" in content
    assert "領域: Career（仕事・働き方）" in content
    assert "理想の状態: 今の仕事の中で自分の強みが言葉になっている状態。" in content
    assert "目標1「職務経歴書を書き上げる」: 進んでいる" in content
    assert "目標2「月に1回、社外の人と話す」: 止まっている" in content
    assert "領域: Financial（お金・生活設計）" in content
    assert "目標1「毎月の支出を把握する」: 見直したい" in content
    assert "<note>" in content
    assert "<user_input>今週は残業が続いて、時間が取れなかった</user_input>" in content


def test_build_messages_omits_areas_without_goals() -> None:
    """4.8「未作成の領域は入力に含めない」。"""
    messages = build_messages("ありたい姿。", STATUSES, AREA_IDEAL_STATES, None)

    content = messages[0]["content"]
    assert "領域: Physical" not in content
    assert "領域: Social" not in content


def test_build_messages_with_empty_note_has_empty_user_input_tag() -> None:
    messages = build_messages("ありたい姿。", STATUSES, AREA_IDEAL_STATES, None)

    content = messages[0]["content"]
    assert "<note>\n<user_input></user_input>\n</note>" in content


def test_build_messages_escapes_less_than_in_note() -> None:
    messages = build_messages("ありたい姿。", STATUSES, AREA_IDEAL_STATES, "5<10だと感じた")

    content = messages[0]["content"]
    assert "5&lt;10だと感じた" in content


# --- validate_output ---


def test_validate_output_accepts_a_valid_response() -> None:
    validate_output(_valid_output())  # 例外を送出しなければ合格


@pytest.mark.parametrize("field", ["looking_back", "insight", "next_step"])
def test_validate_output_rejects_empty_field(field: str) -> None:
    output = _valid_output()
    output[field] = ""

    with pytest.raises(OutputValidationError):
        validate_output(output)


@pytest.mark.parametrize("field", ["looking_back", "insight", "next_step"])
def test_validate_output_rejects_field_over_300_chars(field: str) -> None:
    output = _valid_output()
    output[field] = "あ" * 301

    with pytest.raises(OutputValidationError):
        validate_output(output)


@pytest.mark.parametrize("marker", ["または", "もしくは"])
def test_validate_output_rejects_next_step_with_multiple_proposals(marker: str) -> None:
    output = _valid_output()
    output["next_step"] = f"1日1回開く{marker}週末にまとめて見返すのはどうでしょう。"

    with pytest.raises(OutputValidationError):
        validate_output(output)
