import dataclasses
import json
import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.ai.prompts import assessment_questions
from app.db import repository
from app.db.keys import assessment_sk
from app.domain import job as job_domain
from app.domain import questions
from app.domain.assessment_precompute import FreeTextAnswer, ScaleAnswer, pick_free_text_targets
from app.worker.handler import handler

_QUESTION_SET = questions.get_question_set(questions.CURRENT_QUESTION_SET_VERSION)


def _uid() -> str:
    return uuid.uuid4().hex


def test_handler_returns_ok_for_empty_event() -> None:
    assert handler({}, object()) == {"status": "ok"}


def test_handler_processes_a_dummy_job_to_succeeded() -> None:
    # ASSESSMENT_QUESTIONS・ASSESSMENT_REPORTはP2-5/P2-8で実処理に分岐したため、
    # ここでは未実装のままダミー処理(雛形段階)が働くkindを使う。
    owner = f"USER#{_uid()}"
    job_id, item = job_domain.create_job(owner, "PURPOSE_PROPOSALS")
    assert item["status"] == "QUEUED"

    event = {"Records": [{"body": json.dumps({"job_id": job_id, "kind": "PURPOSE_PROPOSALS"})}]}
    result = handler(event, object())

    assert result == {"status": "ok"}
    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "SUCCEEDED"
    assert updated["result"] == {"echo": "PURPOSE_PROPOSALS"}


def test_handler_processes_multiple_records() -> None:
    # ASSESSMENT_QUESTIONS・ASSESSMENT_REPORTはP2-5/P2-8で実処理に分岐したため、ここでは
    # 未実装のままダミー処理(雛形段階)が働くkindを使う。
    owner = f"USER#{_uid()}"
    job_id_a, _ = job_domain.create_job(owner, "PURPOSE_PROPOSALS")
    job_id_b, _ = job_domain.create_job(owner, "AREA_PROPOSALS")
    event = {
        "Records": [
            {"body": json.dumps({"job_id": job_id_a, "kind": "PURPOSE_PROPOSALS"})},
            {"body": json.dumps({"job_id": job_id_b, "kind": "AREA_PROPOSALS"})},
        ],
    }

    handler(event, object())

    updated_a = job_domain.get_job(job_id_a)
    updated_b = job_domain.get_job(job_id_b)
    assert updated_a is not None
    assert updated_b is not None
    assert updated_a["status"] == "SUCCEEDED"
    assert updated_b["status"] == "SUCCEEDED"


QuestionTargets = list[assessment_questions.QuestionTarget]


def _assessment_questions_payload() -> tuple[dict[str, Any], QuestionTargets]:
    scale_answers = []
    for area in questions.AREAS:
        item_codes = [item.code for item in _QUESTION_SET.items if item.area == area]
        for code, score in zip(item_codes, [4, 3, 2, 1, 0], strict=True):
            scale_answers.append(
                ScaleAnswer(
                    area=area, question_kind=questions.SATISFACTION, item_code=code, score=score
                )
            )
        scale_answers.append(ScaleAnswer(area=area, question_kind=questions.COMMITMENT, score=2))
    targets = assessment_questions.build_targets(scale_answers, _QUESTION_SET)
    payload = {
        "question_set_version": _QUESTION_SET.version,
        "targets": [dataclasses.asdict(target) for target in targets],
    }
    return payload, targets


def _fake_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=500, output_tokens=200, cache_read_input_tokens=0),
    )


def _valid_questions_json(targets: list[assessment_questions.QuestionTarget]) -> str:
    questions_out = []
    for target in targets:
        questions_out.append(
            {
                "area": target.area,
                "slot": "SATISFIED",
                "target_item_code": target.satisfied_item_code,
                "text": "いまどんな状況ですか。",
            }
        )
        questions_out.append(
            {
                "area": target.area,
                "slot": "CONCERN",
                "target_item_code": target.concern_item_code,
                "text": "これからどうしていきたいですか。",
            }
        )
    return json.dumps({"questions": questions_out})


class _FakeMessages:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)

    def create(self, **kwargs: Any) -> Any:
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, responses: list[Any]) -> None:
        self.messages = _FakeMessages(responses)


def _assessment_questions_event(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {"job_id": job_id, "kind": "ASSESSMENT_QUESTIONS", "payload": payload}
    return {"Records": [{"body": json.dumps(body)}]}


def test_handler_generates_assessment_questions_to_succeeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """完了条件「8件の問いが生成され、検証を通る」(P2-5)。"""
    payload, targets = _assessment_questions_payload()
    fake_client = _FakeClient([_fake_response(_valid_questions_json(targets))])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"GUEST#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "ASSESSMENT_QUESTIONS")

    handler(_assessment_questions_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "SUCCEEDED"
    assert len(updated["result"]["questions"]) == 8


def test_handler_fails_assessment_questions_job_after_schema_violation_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload, _targets = _assessment_questions_payload()
    invalid_text = json.dumps({"questions": []})  # 件数不足。再生成しても直らない
    fake_client = _FakeClient([_fake_response(invalid_text), _fake_response(invalid_text)])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"GUEST#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "ASSESSMENT_QUESTIONS")

    handler(_assessment_questions_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "FAILED"
    assert updated["error"]["code"] == "AI_OUTPUT_INVALID"
    assert updated["error"]["retryable"] is True


def _assessment_report_payload() -> dict[str, Any]:
    scale_answers = []
    for area in questions.AREAS:
        item_codes = [item.code for item in _QUESTION_SET.items if item.area == area]
        for code, score in zip(item_codes, [4, 3, 2, 1, 0], strict=True):
            scale_answers.append(
                ScaleAnswer(
                    area=area, question_kind=questions.SATISFACTION, item_code=code, score=score
                )
            )
        scale_answers.append(ScaleAnswer(area=area, question_kind=questions.COMMITMENT, score=2))

    free_text_answers: list[FreeTextAnswer] = []
    for target in pick_free_text_targets(scale_answers, _QUESTION_SET):
        free_text_answers.append(
            FreeTextAnswer(
                area=target.area,
                slot="SATISFIED",
                target_item_code=target.satisfied_item_code,
                generated_question="いまどんな状況で、なぜそう感じているのか教えてください。",
                body="今の会社で任される範囲が広がってきた",
            )
        )
        free_text_answers.append(
            FreeTextAnswer(
                area=target.area,
                slot="CONCERN",
                target_item_code=target.concern_item_code,
                generated_question="これからどうしていきたいですか。",
                body=None,
            )
        )

    return {
        "assessment_id": _uid(),
        "question_set_version": _QUESTION_SET.version,
        "scale_answers": [dataclasses.asdict(answer) for answer in scale_answers],
        "free_text_answers": [dataclasses.asdict(answer) for answer in free_text_answers],
        "started_at": "2026-08-15T00:00:00Z",
    }


def _valid_report_json() -> str:
    areas_out = [
        {
            "area": area,
            "satisfied_text": "満たされている点があります。",
            "concern_text": "気になる点もあります。",
            "advice_text": "少しずつ試してみるのはどうでしょう。",
        }
        for area in questions.AREAS
    ]
    return json.dumps(
        {
            "nickname": "全速前進、燃料計は未確認",
            "areas": areas_out,
            "articulation_stage": "SPROUT",
            "articulation_reason": "具体的な状況が書かれているため。",
            "safety_flag": False,
        }
    )


def _assessment_report_event(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {"job_id": job_id, "kind": "ASSESSMENT_REPORT", "payload": payload}
    return {"Records": [{"body": json.dumps(body)}]}


def test_handler_generates_assessment_report_to_succeeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """完了条件「検証をすべて通る。成功時のみ1アイテム保存」(P2-8)。"""
    payload = _assessment_report_payload()
    fake_client = _FakeClient([_fake_response(_valid_report_json())])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"GUEST#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "ASSESSMENT_REPORT")

    handler(_assessment_report_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "SUCCEEDED"
    assessment_id = payload["assessment_id"]
    assert updated["result"] == {"assessment_id": assessment_id}

    item = repository.get_item(owner, assessment_sk(assessment_id))
    assert item is not None
    assert item["result"]["nickname"] == "全速前進、燃料計は未確認"
    assert item["result"]["commitment_score"] == 8  # COMMITMENT各領域2点 x 4領域
    assert item["result"]["commitment_stage"] == "SEEDLING"  # 8〜11(4.1の閾値表)
    assert item["result"]["articulation_stage"] == "SPROUT"
    assert len(item["result"]["areas"]) == 4
    assert "articulation_reason" not in item["result"]  # ユーザーに見せない(4.2)
    assert item["guest_session_id"] == owner.removeprefix("GUEST#")
    assert "expires_at" in item  # ゲストの現在地レポートは30日TTL(08_データモデル2.2)


def test_handler_does_not_save_an_item_when_ai_output_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _assessment_report_payload()
    invalid_text = json.dumps({"nickname": "x"})  # 必須フィールド欠落。再生成しても直らない
    fake_client = _FakeClient([_fake_response(invalid_text), _fake_response(invalid_text)])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"USER#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "ASSESSMENT_REPORT")

    handler(_assessment_report_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "FAILED"
    assert updated["error"]["code"] == "AI_OUTPUT_INVALID"

    item = repository.get_item(owner, assessment_sk(payload["assessment_id"]))
    assert item is None  # 失敗時は何も残らない(09_API設計5.3)
