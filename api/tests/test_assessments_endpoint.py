"""`POST /assessments`。09_API設計5.3の検証と非同期ジョブ登録を確認する。

実際のBedrock呼び出し・SQS送信は行わない。`send_job_message`をフェイクに差し替える。
生成成功時の保存・失敗時に何も残らないことは`test_worker_handler.py`で確認する。
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.security import GUEST_COOKIE_NAME, SESSION_COOKIE_NAME
from app.domain import guest_session, questions, session
from app.domain import job as job_domain
from app.domain.rate_limit import GUEST_SESSION_LIMIT
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


def _full_free_text_answers() -> list[dict[str, Any]]:
    answers = []
    for area in questions.AREAS:
        for slot in ("SATISFIED", "CONCERN"):
            answers.append(
                {
                    "area": area,
                    "slot": slot,
                    "target_item_code": f"{area}_ITEM",
                    "generated_question": "問い文",
                    "body": "回答本文" if slot == "SATISFIED" else None,
                }
            )
    return answers


def _request_body(
    scale_answers: list[dict[str, Any]] | None = None,
    free_text_answers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "scale_answers": scale_answers if scale_answers is not None else _full_scale_answers(),
        "free_text_answers": (
            free_text_answers if free_text_answers is not None else _full_free_text_answers()
        ),
        "question_set_version": questions.CURRENT_QUESTION_SET_VERSION,
    }


def _client_with_cookie(name: str, value: str) -> TestClient:
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(name, value)
    return client


def _guest_client() -> TestClient:
    guest_token, _ = guest_session.issue_guest_session()
    return _client_with_cookie(GUEST_COOKIE_NAME, guest_token)


def _user_client() -> TestClient:
    token, _ = session.create_session(_uid())
    return _client_with_cookie(SESSION_COOKIE_NAME, token)


class _FakeSendJobMessage:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, job_id: str, kind: str, payload: dict[str, Any] | None = None) -> None:
        self.calls.append({"job_id": job_id, "kind": kind, "payload": payload})


def _install_fake_send(monkeypatch: pytest.MonkeyPatch) -> _FakeSendJobMessage:
    fake_send = _FakeSendJobMessage()
    monkeypatch.setattr("app.api.v1.assessments.send_job_message", fake_send)
    return fake_send


def test_returns_422_when_scale_answers_are_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_send = _install_fake_send(monkeypatch)

    body = _request_body(scale_answers=_full_scale_answers()[:-1])  # 23件

    response = _guest_client().post("/api/v1/assessments", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ANSWERS_INCOMPLETE"
    assert fake_send.calls == []


def test_returns_422_when_free_text_answers_are_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_send = _install_fake_send(monkeypatch)

    body = _request_body(free_text_answers=_full_free_text_answers()[:-1])  # 7件

    response = _guest_client().post("/api/v1/assessments", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ANSWERS_INCOMPLETE"
    assert fake_send.calls == []


def test_returns_202_and_queues_a_job_for_guest(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_send = _install_fake_send(monkeypatch)

    response = _guest_client().post("/api/v1/assessments", json=_request_body())

    assert response.status_code == 202
    response_body = response.json()
    assert response_body["poll_after_ms"] == 1500
    job_id = response_body["job_id"]

    job_item = job_domain.get_job(job_id)
    assert job_item is not None
    assert job_item["kind"] == "ASSESSMENT_REPORT"
    assert job_item["status"] == "QUEUED"

    assert len(fake_send.calls) == 1
    payload = fake_send.calls[0]["payload"]
    assert payload["question_set_version"] == questions.CURRENT_QUESTION_SET_VERSION
    assert len(payload["scale_answers"]) == 24
    assert len(payload["free_text_answers"]) == 8
    assert "assessment_id" in payload
    assert "started_at" in payload


def test_returns_202_and_queues_a_job_for_user(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_send = _install_fake_send(monkeypatch)

    response = _user_client().post("/api/v1/assessments", json=_request_body())

    assert response.status_code == 202
    assert len(fake_send.calls) == 1


def test_idempotency_key_reuses_the_same_job(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_send = _install_fake_send(monkeypatch)
    client = _guest_client()
    headers = {"Idempotency-Key": "retry-key-1"}
    body = _request_body()

    first = client.post("/api/v1/assessments", json=body, headers=headers)
    second = client.post("/api/v1/assessments", json=body, headers=headers)

    assert first.json()["job_id"] == second.json()["job_id"]
    assert len(fake_send.calls) == 1  # 2回目はジョブを作らない


def test_guest_report_generation_limit_returns_429_after_the_session_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """09_API設計2.4「ゲスト: レポート生成は1セッション3回まで」がこのエンドポイントに効くこと。"""
    _install_fake_send(monkeypatch)
    client = _guest_client()
    body = _request_body()

    for _ in range(GUEST_SESSION_LIMIT):
        response = client.post("/api/v1/assessments", json=body)
        assert response.status_code == 202

    response = client.post("/api/v1/assessments", json=body)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
