import pytest

from app.db.local_bootstrap import ensure_table_exists


@pytest.fixture(scope="session", autouse=True)
def _dynamodb_table() -> None:
    ensure_table_exists()
