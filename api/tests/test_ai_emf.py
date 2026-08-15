import json

import pytest

from app.ai import emf


def test_emit_writes_one_emf_json_line(capsys: pytest.CaptureFixture[str]) -> None:
    emf.emit(
        kind="TEST_DUMMY",
        model="anthropic.claude-haiku-4-5",
        prompt_version="test-v1",
        effort="low",
        status="SUCCEEDED",
        attempt=1,
        prompt_tokens=120,
        completion_tokens=40,
        cache_read_tokens=0,
        safety_flag=False,
        identifiers={"job_id": "job-1", "user_id": "USER#u1"},
    )

    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])

    assert record["kind"] == "TEST_DUMMY"
    assert record["model"] == "anthropic.claude-haiku-4-5"
    assert record["status"] == "SUCCEEDED"
    assert record["attempt"] == 1
    assert record["retry_reason"] is None
    assert record["error_code"] is None
    assert record["safety_flag"] is False
    assert record["PromptTokens"] == 120
    assert record["CompletionTokens"] == 40
    assert record["job_id"] == "job-1"
    assert record["user_id"] == "USER#u1"
    assert record["_aws"]["CloudWatchMetrics"][0]["Namespace"] == "FlourishStudio/AIGeneration"


def test_emit_includes_kind_specific_extra_fields(capsys: pytest.CaptureFixture[str]) -> None:
    # ASSESSMENT_REPORTのarticulation_reasonのような、kind固有のフィールド
    # (10_AIプロンプト設計4.2「ASSESSMENT_RESULTに保存せず、AI_GENERATION側に記録する」)。
    emf.emit(
        kind="ASSESSMENT_REPORT",
        model="anthropic.claude-sonnet-5",
        prompt_version="test-v1",
        effort="high",
        status="SUCCEEDED",
        attempt=1,
        extra={"articulation_reason": "具体的な場面が書かれているため。"},
    )

    line = capsys.readouterr().out.strip()
    record = json.loads(line)
    assert record["articulation_reason"] == "具体的な場面が書かれているため。"


def test_emit_never_includes_prompt_or_output_body(capsys: pytest.CaptureFixture[str]) -> None:
    emf.emit(
        kind="TEST_DUMMY",
        model="anthropic.claude-haiku-4-5",
        prompt_version="test-v1",
        effort="low",
        status="FAILED",
        attempt=1,
        error_code="AI_OUTPUT_INVALID",
    )

    line = capsys.readouterr().out.strip()
    # プロンプトの入出力本文は出さない(10_AIプロンプト設計3.9)
    assert "user_input" not in line
