"""`GET /jobs/{id}`。09_API設計3.1、スキルflourish-api「発行者のみ参照できる」を確認する。"""

import uuid

from fastapi.testclient import TestClient

from app.core.security import GUEST_COOKIE_NAME, SESSION_COOKIE_NAME
from app.db.keys import guest_pk, user_pk
from app.domain import guest_session, session
from app.domain import job as job_domain
from app.main import app


def _uid() -> str:
    return uuid.uuid4().hex


def _client_with_cookie(name: str, value: str) -> TestClient:
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(name, value)
    return client


def test_get_job_returns_queued_status_for_the_owner() -> None:
    user_id = _uid()
    token, _ = session.create_session(user_id)
    job_id, _ = job_domain.create_job(user_pk(user_id), "ASSESSMENT_REPORT")

    response = _client_with_cookie(SESSION_COOKIE_NAME, token).get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json() == {"status": "QUEUED", "poll_after_ms": 1500}


def test_get_job_returns_succeeded_with_result() -> None:
    user_id = _uid()
    token, _ = session.create_session(user_id)
    job_id, _ = job_domain.create_job(user_pk(user_id), "ASSESSMENT_REPORT")
    job_domain.mark_running(job_id)
    job_domain.mark_succeeded(job_id, {"assessment_id": "a1"})

    response = _client_with_cookie(SESSION_COOKIE_NAME, token).get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json() == {"status": "SUCCEEDED", "result": {"assessment_id": "a1"}}


def test_get_job_returns_failed_with_error() -> None:
    user_id = _uid()
    token, _ = session.create_session(user_id)
    job_id, _ = job_domain.create_job(user_pk(user_id), "ASSESSMENT_REPORT")
    job_domain.mark_running(job_id)
    job_domain.mark_failed(job_id, "AI_PROVIDER_ERROR", retryable=True)

    response = _client_with_cookie(SESSION_COOKIE_NAME, token).get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["error"] == {"code": "AI_PROVIDER_ERROR", "retryable": True}


def test_get_job_allows_the_owning_guest() -> None:
    guest_token, _ = guest_session.issue_guest_session()
    job_id, _ = job_domain.create_job(guest_pk(guest_token), "ASSESSMENT_QUESTIONS")

    response = _client_with_cookie(GUEST_COOKIE_NAME, guest_token).get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json() == {"status": "QUEUED", "poll_after_ms": 1500}


def test_get_job_returns_403_for_another_owner() -> None:
    job_id, _ = job_domain.create_job(f"USER#{_uid()}", "ASSESSMENT_REPORT")
    other_token, _ = session.create_session(_uid())

    response = _client_with_cookie(SESSION_COOKIE_NAME, other_token).get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "JOB_FORBIDDEN"


def test_get_job_returns_404_for_unknown_job() -> None:
    token, _ = session.create_session(_uid())

    response = _client_with_cookie(SESSION_COOKIE_NAME, token).get(f"/api/v1/jobs/{_uid()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_get_job_returns_401_without_any_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.get(f"/api/v1/jobs/{_uid()}")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
