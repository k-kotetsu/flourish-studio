import json
import uuid

from app.domain import job as job_domain
from app.worker.handler import handler


def _uid() -> str:
    return uuid.uuid4().hex


def test_handler_returns_ok_for_empty_event() -> None:
    assert handler({}, object()) == {"status": "ok"}


def test_handler_processes_a_dummy_job_to_succeeded() -> None:
    owner = f"USER#{_uid()}"
    job_id, item = job_domain.create_job(owner, "ASSESSMENT_REPORT")
    assert item["status"] == "QUEUED"

    event = {"Records": [{"body": json.dumps({"job_id": job_id, "kind": "ASSESSMENT_REPORT"})}]}
    result = handler(event, object())

    assert result == {"status": "ok"}
    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "SUCCEEDED"
    assert updated["result"] == {"echo": "ASSESSMENT_REPORT"}


def test_handler_processes_multiple_records() -> None:
    owner = f"USER#{_uid()}"
    job_id_a, _ = job_domain.create_job(owner, "ASSESSMENT_REPORT")
    job_id_b, _ = job_domain.create_job(owner, "ASSESSMENT_QUESTIONS")
    event = {
        "Records": [
            {"body": json.dumps({"job_id": job_id_a, "kind": "ASSESSMENT_REPORT"})},
            {"body": json.dumps({"job_id": job_id_b, "kind": "ASSESSMENT_QUESTIONS"})},
        ],
    }

    handler(event, object())

    updated_a = job_domain.get_job(job_id_a)
    updated_b = job_domain.get_job(job_id_b)
    assert updated_a is not None
    assert updated_b is not None
    assert updated_a["status"] == "SUCCEEDED"
    assert updated_b["status"] == "SUCCEEDED"
