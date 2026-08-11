import json

import pytest
from botocore.stub import Stubber

from app.core.config import get_settings
from app.queue import jobs as queue_jobs
from app.queue.client import get_sqs_client

_QUEUE_URL = "https://sqs.ap-northeast-1.amazonaws.com/123456789012/flourish-job-queue"


def test_send_job_message_sends_job_id_and_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOB_QUEUE_URL", _QUEUE_URL)
    get_settings.cache_clear()
    stubber = Stubber(get_sqs_client())
    expected_body = json.dumps({"job_id": "job-1", "kind": "ASSESSMENT_REPORT"})
    stubber.add_response(
        "send_message",
        {"MessageId": "m1", "MD5OfMessageBody": "x"},
        {"QueueUrl": _QUEUE_URL, "MessageBody": expected_body},
    )
    stubber.activate()
    try:
        queue_jobs.send_job_message("job-1", "ASSESSMENT_REPORT")
        stubber.assert_no_pending_responses()
    finally:
        stubber.deactivate()
        get_settings.cache_clear()


def test_send_job_message_raises_when_queue_url_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("JOB_QUEUE_URL", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError):
            queue_jobs.send_job_message("job-1", "ASSESSMENT_REPORT")
    finally:
        get_settings.cache_clear()
