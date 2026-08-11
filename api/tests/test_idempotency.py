import uuid
from concurrent.futures import ThreadPoolExecutor

from app.domain import idempotency


def _uid() -> str:
    return uuid.uuid4().hex


def test_reserve_job_id_returns_the_candidate_on_first_use() -> None:
    owner = f"USER#{_uid()}"

    job_id = idempotency.reserve_job_id(owner, _uid(), "job-a")

    assert job_id == "job-a"


def test_reserve_job_id_returns_the_existing_job_on_resend() -> None:
    owner = f"USER#{_uid()}"
    key = _uid()

    first = idempotency.reserve_job_id(owner, key, "job-a")
    second = idempotency.reserve_job_id(owner, key, "job-b")

    assert first == "job-a"
    assert second == "job-a"


def test_reserve_job_id_is_independent_per_key() -> None:
    owner = f"USER#{_uid()}"

    a = idempotency.reserve_job_id(owner, _uid(), "job-a")
    b = idempotency.reserve_job_id(owner, _uid(), "job-b")

    assert a == "job-a"
    assert b == "job-b"


def test_reserve_job_id_is_independent_per_owner() -> None:
    key = _uid()

    a = idempotency.reserve_job_id(f"USER#{_uid()}", key, "job-a")
    b = idempotency.reserve_job_id(f"USER#{_uid()}", key, "job-b")

    assert a == "job-a"
    assert b == "job-b"


def test_concurrent_requests_with_same_key_do_not_create_duplicate_jobs() -> None:
    owner = f"USER#{_uid()}"
    key = _uid()
    candidates = ["job-a", "job-b"]

    def attempt(candidate: str) -> str:
        return idempotency.reserve_job_id(owner, key, candidate)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, candidates))

    assert results[0] == results[1]
    assert results[0] in candidates
