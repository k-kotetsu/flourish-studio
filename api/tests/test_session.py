import uuid

from app.core.security import generate_token, hash_token
from app.db import repository
from app.domain import session


def _uid() -> str:
    return uuid.uuid4().hex


def test_create_session_can_be_read_back_by_the_returned_token() -> None:
    user_id = _uid()

    token, item = session.create_session(user_id)
    fetched = session.get_active_session(token)

    assert fetched is not None
    assert fetched["PK"] == item["PK"]
    assert fetched["user_id"] == user_id


def test_session_pk_stores_a_hash_not_the_raw_token() -> None:
    token, item = session.create_session(_uid())

    assert item["PK"] != token
    assert item["PK"].endswith(hash_token(token))


def test_get_active_session_returns_none_for_unknown_token() -> None:
    assert session.get_active_session(generate_token()) is None


def test_get_active_session_returns_none_when_expired() -> None:
    token, item = session.create_session(_uid())
    repository.update_item(
        item["PK"],
        item["SK"],
        update_expression="SET expires_at = :past",
        expression_attribute_values={":past": 1},
    )

    assert session.get_active_session(token) is None


def test_touch_session_skips_write_within_24_hours() -> None:
    _, item = session.create_session(_uid())

    updated = session.touch_session(item)

    assert updated["last_seen_at"] == item["last_seen_at"]
    assert updated["expires_at"] == item["expires_at"]


def test_touch_session_extends_when_last_seen_is_older_than_24_hours() -> None:
    _, item = session.create_session(_uid())
    stale_last_seen = int(item["last_seen_at"]) - (60 * 60 * 24 + 1)
    stale_item = repository.update_item(
        item["PK"],
        item["SK"],
        update_expression="SET last_seen_at = :stale",
        expression_attribute_values={":stale": stale_last_seen},
    )

    updated = session.touch_session(stale_item)

    assert updated["last_seen_at"] > stale_item["last_seen_at"]
    assert updated["expires_at"] == updated["last_seen_at"] + 60 * 60 * 24 * 30


def test_invalidate_session_makes_the_session_immediately_inactive() -> None:
    token, item = session.create_session(_uid())

    session.invalidate_session(item)

    assert session.get_active_session(token) is None
