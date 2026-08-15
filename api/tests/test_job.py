import uuid

from app.db import repository
from app.domain import job as job_domain


def _uid() -> str:
    return uuid.uuid4().hex


def test_create_job_starts_as_queued() -> None:
    owner = f"USER#{_uid()}"

    job_id, item = job_domain.create_job(owner, "ASSESSMENT_REPORT")

    assert item["status"] == "QUEUED"
    assert item["owner"] == owner
    assert item["kind"] == "ASSESSMENT_REPORT"
    assert item["result"] is None
    assert item["error"] is None
    assert job_domain.get_job(job_id) == item


def test_create_job_uses_the_given_job_id() -> None:
    owner = f"USER#{_uid()}"
    candidate = _uid()

    job_id, _ = job_domain.create_job(owner, "ASSESSMENT_REPORT", job_id=candidate)

    assert job_id == candidate


def test_get_job_returns_none_for_unknown_id() -> None:
    assert job_domain.get_job(_uid()) is None


def test_mark_running_transitions_from_queued() -> None:
    job_id, _ = job_domain.create_job(f"USER#{_uid()}", "ASSESSMENT_REPORT")

    updated = job_domain.mark_running(job_id)

    assert updated["status"] == "RUNNING"


def test_mark_succeeded_stores_the_result() -> None:
    job_id, _ = job_domain.create_job(f"USER#{_uid()}", "ASSESSMENT_REPORT")
    job_domain.mark_running(job_id)

    updated = job_domain.mark_succeeded(job_id, {"assessment_id": "a1"})

    assert updated["status"] == "SUCCEEDED"
    assert updated["result"] == {"assessment_id": "a1"}


def test_mark_succeeded_with_item_saves_both_in_one_transaction() -> None:
    owner = f"USER#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "ASSESSMENT_REPORT")
    job_domain.mark_running(job_id)
    item = {"PK": owner, "SK": "ASSESSMENT#a1", "entity": "ASSESSMENT", "assessment_id": "a1"}

    job_domain.mark_succeeded_with_item(job_id, result={"assessment_id": "a1"}, item=item)

    updated_job = job_domain.get_job(job_id)
    assert updated_job is not None
    assert updated_job["status"] == "SUCCEEDED"
    assert updated_job["result"] == {"assessment_id": "a1"}

    saved_item = repository.get_item(owner, "ASSESSMENT#a1")
    assert saved_item is not None
    assert saved_item["assessment_id"] == "a1"


def test_mark_failed_stores_code_and_retryable() -> None:
    job_id, _ = job_domain.create_job(f"USER#{_uid()}", "ASSESSMENT_REPORT")
    job_domain.mark_running(job_id)

    updated = job_domain.mark_failed(job_id, "AI_PROVIDER_ERROR", retryable=True)

    assert updated["status"] == "FAILED"
    assert updated["error"] == {"code": "AI_PROVIDER_ERROR", "retryable": True}
