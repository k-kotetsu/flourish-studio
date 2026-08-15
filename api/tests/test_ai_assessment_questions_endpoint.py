"""`POST /ai/assessment-questions`。09_API設計5.2の検証と非同期ジョブ登録を確認する。

実際のBedrock呼び出し・SQS送信は行わない。`send_job_message`をフェイクに差し替える。
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.security import GUEST_COOKIE_NAME
from app.domain import guest_session, questions
from app.domain import job as job_domain
from app.main import app

_QUESTION_SET = questions.get_question_set(questions.CURRENT_QUESTION_SET_VERSION)


def _uid() -> str:
    return uuid.uuid4().hex


def _full_scale_answers() -> list[dict[str, Any]]:
    answers = []
    for area in questions.AREAS:
        item_codes = [item.code for item in _QUESTION_SET.items if item.area == area]
        for code, score in zip(item_codes, [4, 3, 2, 1, 0], strict=True):
            answers.append(
                {"area": area, "question_kind": "SATISFACTION", "item_code": code, "score": score}
            )
        answers.append({"area": area, "question_kind": "COMMITMENT", "score": 2})
    return answers


def _guest_client() -> TestClient:
    guest_token, _ = guest_session.issue_guest_session()
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(GUEST_COOKIE_NAME, guest_token)
    return client


def _request_body(scale_answers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "scale_answers": scale_answers,
        "question_set_version": questions.CURRENT_QUESTION_SET_VERSION,
    }


class _FakeSendJobMessage:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, job_id: str, kind: str, payload: dict[str, Any] | None = None) -> None:
        self.calls.append({"job_id": job_id, "kind": kind, "payload": payload})


def test_returns_422_when_scale_answers_are_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_send = _FakeSendJobMessage()
    monkeypatch.setattr("app.api.v1.ai_assessment_questions.send_job_message", fake_send)

    body = _request_body(_full_scale_answers()[:-1])  # 23件

    response = _guest_client().post("/api/v1/ai/assessment-questions", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ANSWERS_INCOMPLETE"
    assert fake_send.calls == []


def test_returns_202_and_queues_a_job(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_send = _FakeSendJobMessage()
    monkeypatch.setattr("app.api.v1.ai_assessment_questions.send_job_message", fake_send)

    body = _request_body(_full_scale_answers())

    response = _guest_client().post("/api/v1/ai/assessment-questions", json=body)

    assert response.status_code == 202
    response_body = response.json()
    assert response_body["poll_after_ms"] == 1500
    job_id = response_body["job_id"]

    job_item = job_domain.get_job(job_id)
    assert job_item is not None
    assert job_item["kind"] == "ASSESSMENT_QUESTIONS"
    assert job_item["status"] == "QUEUED"

    assert len(fake_send.calls) == 1
    payload = fake_send.calls[0]["payload"]
    assert payload["question_set_version"] == questions.CURRENT_QUESTION_SET_VERSION
    assert len(payload["targets"]) == 4


def test_idempotency_key_reuses_the_same_job(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_send = _FakeSendJobMessage()
    monkeypatch.setattr("app.api.v1.ai_assessment_questions.send_job_message", fake_send)

    body = _request_body(_full_scale_answers())
    client = _guest_client()
    headers = {"Idempotency-Key": "retry-key-1"}

    first = client.post("/api/v1/ai/assessment-questions", json=body, headers=headers)
    second = client.post("/api/v1/ai/assessment-questions", json=body, headers=headers)

    assert first.json()["job_id"] == second.json()["job_id"]
    assert len(fake_send.calls) == 1  # 2回目はジョブを作らない
