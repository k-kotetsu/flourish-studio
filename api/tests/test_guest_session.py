import uuid

from app.core.security import generate_token
from app.db import repository
from app.domain import guest_session


def test_issue_guest_session_can_be_read_back_by_the_returned_token() -> None:
    token, item = guest_session.issue_guest_session()

    fetched = guest_session.get_active_guest_session(token)

    assert fetched is not None
    assert fetched["PK"] == item["PK"]
    assert fetched["converted_user_id"] is None
    assert fetched["report_generation_count"] == 0


def test_get_active_guest_session_returns_none_for_unknown_token() -> None:
    assert guest_session.get_active_guest_session(generate_token()) is None


def test_get_active_guest_session_returns_none_when_expired() -> None:
    token, item = guest_session.issue_guest_session()
    repository.update_item(
        item["PK"],
        item["SK"],
        update_expression="SET expires_at = :past",
        expression_attribute_values={":past": 1},
    )

    assert guest_session.get_active_guest_session(token) is None


def test_mark_guest_converted_records_the_linked_user() -> None:
    token, _ = guest_session.issue_guest_session()
    user_id = uuid.uuid4().hex

    guest_session.mark_guest_converted(token, user_id)

    item = guest_session.get_active_guest_session(token)
    assert item is not None
    assert item["converted_user_id"] == user_id
    assert item["converted_at"] is not None
