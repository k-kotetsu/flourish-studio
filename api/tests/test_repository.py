import uuid

import pytest

from app.db import repository
from app.db.keys import history_sk, idem_pk, rate_pk, user_pk


def _uid() -> str:
    return uuid.uuid4().hex


def test_get_item_returns_none_when_missing() -> None:
    assert repository.get_item(user_pk(_uid()), "PROFILE") is None


def test_put_item_then_get_item_roundtrips() -> None:
    pk = user_pk(_uid())
    repository.put_item({"PK": pk, "SK": "PROFILE", "nickname": "aoi"})

    item = repository.get_item(pk, "PROFILE")

    assert item is not None
    assert item["nickname"] == "aoi"


def test_conditional_put_item_fails_on_duplicate_idempotency_key() -> None:
    pk = idem_pk("guest#1", _uid())
    repository.put_item(
        {"PK": pk, "SK": "IDEM", "job_id": "job-1"},
        condition_expression="attribute_not_exists(PK)",
    )

    with pytest.raises(repository.ConditionalCheckFailed):
        repository.put_item(
            {"PK": pk, "SK": "IDEM", "job_id": "job-2"},
            condition_expression="attribute_not_exists(PK)",
        )


def test_conditional_update_item_enforces_rate_limit() -> None:
    pk = rate_pk("guest#1", _uid())
    limit = 3

    for _ in range(limit):
        repository.update_item(
            pk,
            "RATE",
            update_expression="ADD #c :one",
            expression_attribute_values={":one": 1, ":limit": limit},
            expression_attribute_names={"#c": "count"},
            condition_expression="attribute_not_exists(#c) OR #c < :limit",
        )

    with pytest.raises(repository.ConditionalCheckFailed):
        repository.update_item(
            pk,
            "RATE",
            update_expression="ADD #c :one",
            expression_attribute_values={":one": 1, ":limit": limit},
            expression_attribute_names={"#c": "count"},
            condition_expression="attribute_not_exists(#c) OR #c < :limit",
        )


def test_put_versioned_creates_first_version_without_history() -> None:
    pk = user_pk(_uid())

    new_item = repository.put_versioned(pk, "PURPOSE#CURRENT", "PURPOSE", {"text": "v1"})

    assert new_item["version"] == 1
    current = repository.get_item(pk, "PURPOSE#CURRENT")
    assert current is not None
    assert current["text"] == "v1"
    assert repository.get_item(pk, history_sk("PURPOSE", 0)) is None


def test_put_versioned_moves_previous_version_to_history() -> None:
    pk = user_pk(_uid())
    repository.put_versioned(pk, "PURPOSE#CURRENT", "PURPOSE", {"text": "v1"})

    new_item = repository.put_versioned(pk, "PURPOSE#CURRENT", "PURPOSE", {"text": "v2"})

    assert new_item["version"] == 2
    current = repository.get_item(pk, "PURPOSE#CURRENT")
    assert current is not None
    assert current["text"] == "v2"
    history = repository.get_item(pk, history_sk("PURPOSE", 1))
    assert history is not None
    assert history["text"] == "v1"


def test_transact_write_items_rolls_back_when_condition_check_fails() -> None:
    pk = user_pk(_uid())

    with pytest.raises(repository.ConditionalCheckFailed):
        repository.transact_write_items(
            [
                {
                    "ConditionCheck": {
                        "Key": {"PK": pk, "SK": "PURPOSE#CURRENT"},
                        "ConditionExpression": "attribute_exists(PK)",
                    },
                },
                {"Put": {"Item": {"PK": pk, "SK": "AREA#CAREER#CURRENT", "text": "x"}}},
            ],
        )

    assert repository.get_item(pk, "AREA#CAREER#CURRENT") is None


def test_batch_get_items_returns_all_requested_items() -> None:
    pk = user_pk(_uid())
    repository.put_item({"PK": pk, "SK": "PROFILE", "nickname": "aoi"})
    repository.put_item({"PK": pk, "SK": "PURPOSE#CURRENT", "text": "v1"})

    items = repository.batch_get_items([(pk, "PROFILE"), (pk, "PURPOSE#CURRENT")])

    assert {item["SK"] for item in items} == {"PROFILE", "PURPOSE#CURRENT"}


def test_query_by_sk_prefix_excludes_other_prefixes() -> None:
    pk = user_pk(_uid())
    repository.put_item({"PK": pk, "SK": "AREA#CAREER#CURRENT"})
    repository.put_item({"PK": pk, "SK": "AREA#FINANCIAL#CURRENT"})
    repository.put_item({"PK": pk, "SK": "PURPOSE#CURRENT"})

    items = repository.query_by_sk_prefix(pk, "AREA#")

    assert {item["SK"] for item in items} == {"AREA#CAREER#CURRENT", "AREA#FINANCIAL#CURRENT"}
