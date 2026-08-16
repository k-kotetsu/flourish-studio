"""評価セット実行環境(P2-13)。`app.ai.runner.get_client`をフェイクに差し替え、
実際にBedrockへは接続しない。

完了条件「コマンド1つで(実装済みの2種の)出力が揃う」を、run_all()が全セット分の
JSONファイルを書き出すことで確認する。
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.ai.prompts.assessment_questions import build_targets
from app.domain.questions import AREAS, CURRENT_QUESTION_SET_VERSION, QuestionSet, get_question_set
from app.eval import fixtures as eval_fixtures
from app.eval.fixtures import EvalSet
from app.eval.run import run_all


def _response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=100, output_tokens=50, cache_read_input_tokens=0),
    )


def _questions_response_for(eval_set: EvalSet, question_set: QuestionSet) -> SimpleNamespace:
    scale_answers = eval_set.build_scale_answers(question_set)
    targets = build_targets(scale_answers, question_set)
    questions: list[dict[str, Any]] = []
    for target in targets:
        questions.append(
            {
                "area": target.area,
                "slot": "SATISFIED",
                "target_item_code": target.satisfied_item_code,
                "text": "テスト用の問いです。",
            }
        )
        questions.append(
            {
                "area": target.area,
                "slot": "CONCERN",
                "target_item_code": target.concern_item_code,
                "text": "テスト用の問いです。",
            }
        )
    return _response(json.dumps({"questions": questions}))


def _report_response(*, safety_flag: bool = False) -> SimpleNamespace:
    output = {
        "nickname": "テストのあだ名",
        "areas": [
            {
                "area": area,
                "satisfied_text": "満たされている点です。",
                "concern_text": "気になる点です。",
                "advice_text": "できそうなことです。",
            }
            for area in AREAS
        ],
        "articulation_stage": "SPROUT",
        "articulation_reason": "テスト用の理由です。",
        "safety_flag": safety_flag,
    }
    return _response(json.dumps(output))


class _FakeMessages:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _FakeClient:
    def __init__(self, responses: list[Any]) -> None:
        self.messages = _FakeMessages(responses)


def _install_fake_client(monkeypatch: pytest.MonkeyPatch, responses: list[Any]) -> _FakeClient:
    fake_client = _FakeClient(responses)
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)
    return fake_client


def test_run_all_writes_output_for_every_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    question_set = get_question_set(CURRENT_QUESTION_SET_VERSION)
    responses: list[Any] = []
    for eval_set in eval_fixtures.EVAL_SETS:
        responses.append(_questions_response_for(eval_set, question_set))
        responses.append(_report_response())

    fake_client = _install_fake_client(monkeypatch, responses)

    results = run_all(output_dir=tmp_path)

    assert len(results) == len(eval_fixtures.EVAL_SETS)
    assert all(r.assessment_questions.status == "SUCCEEDED" for r in results)
    assert all(
        r.assessment_report is not None and r.assessment_report.status == "SUCCEEDED"
        for r in results
    )
    # 1セットにつきASSESSMENT_QUESTIONS・ASSESSMENT_REPORTの2回
    assert len(fake_client.messages.calls) == len(eval_fixtures.EVAL_SETS) * 2

    written_files = sorted(tmp_path.glob("set_*.json"))
    assert len(written_files) == len(eval_fixtures.EVAL_SETS)

    first = json.loads(written_files[0].read_text(encoding="utf-8"))
    assert first["id"] == 1
    assert first["name"] == eval_fixtures.EVAL_SETS[0].name
    assert first["assessment_questions"]["status"] == "SUCCEEDED"
    assert first["assessment_report"]["status"] == "SUCCEEDED"


def test_run_all_skips_report_when_questions_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    question_set = get_question_set(CURRENT_QUESTION_SET_VERSION)
    responses: list[Any] = []
    for index, eval_set in enumerate(eval_fixtures.EVAL_SETS):
        if index == 0:
            # questionsフィールドを欠いたスキーマ違反を2回連続させ、
            # サーバ内再生成(3.8)も含めてASSESSMENT_QUESTIONS自体を失敗させる
            responses.append(_response(json.dumps({})))
            responses.append(_response(json.dumps({})))
        else:
            responses.append(_questions_response_for(eval_set, question_set))
            responses.append(_report_response())

    _install_fake_client(monkeypatch, responses)

    results = run_all(output_dir=tmp_path)

    assert results[0].assessment_questions.status == "FAILED"
    assert results[0].assessment_report is None
    assert all(r.assessment_questions.status == "SUCCEEDED" for r in results[1:])

    written = json.loads((tmp_path / "set_01.json").read_text(encoding="utf-8"))
    assert written["assessment_questions"]["status"] == "FAILED"
    assert written["assessment_report"] is None
