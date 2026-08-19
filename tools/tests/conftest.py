import pytest

from insert_articles import ensure_table_exists, get_client


@pytest.fixture(scope="session", autouse=True)
def _dynamodb_table() -> None:
    ensure_table_exists(get_client())
