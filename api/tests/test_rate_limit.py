import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.core.errors import RateLimitedError
from app.db import repository
from app.domain import guest_session, rate_limit


def _uid() -> str:
    return uuid.uuid4().hex


def test_check_and_increment_user_allows_up_to_the_limit() -> None:
    owner = f"USER#{_uid()}"

    for _ in range(3):
        rate_limit.check_and_increment_user(owner, limit=3)


def test_check_and_increment_user_blocks_after_the_limit() -> None:
    owner = f"USER#{_uid()}"
    for _ in range(3):
        rate_limit.check_and_increment_user(owner, limit=3)

    with pytest.raises(RateLimitedError) as exc_info:
        rate_limit.check_and_increment_user(owner, limit=3)

    assert exc_info.value.code == "RATE_LIMITED"
    assert exc_info.value.retry_after > 0


def test_check_and_increment_user_counters_are_independent_per_owner() -> None:
    owner_a = f"USER#{_uid()}"
    owner_b = f"USER#{_uid()}"

    rate_limit.check_and_increment_user(owner_a, limit=1)
    rate_limit.check_and_increment_user(owner_b, limit=1)


def test_concurrent_requests_do_not_exceed_the_user_limit() -> None:
    owner = f"USER#{_uid()}"
    limit = 3

    def attempt(_: int) -> bool:
        try:
            rate_limit.check_and_increment_user(owner, limit=limit)
        except RateLimitedError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(attempt, range(10)))

    assert sum(results) == limit


def test_check_and_increment_guest_allows_three_then_blocks() -> None:
    token, _ = guest_session.issue_guest_session()

    rate_limit.check_and_increment_guest(token)
    rate_limit.check_and_increment_guest(token)
    rate_limit.check_and_increment_guest(token)

    with pytest.raises(RateLimitedError) as exc_info:
        rate_limit.check_and_increment_guest(token)

    assert exc_info.value.code == "RATE_LIMITED"


def test_check_and_increment_guest_reads_the_stored_count() -> None:
    token, item = guest_session.issue_guest_session()

    rate_limit.check_and_increment_guest(token)

    stored = repository.get_item(item["PK"], item["SK"])
    assert stored is not None
    assert stored["report_generation_count"] == 1
