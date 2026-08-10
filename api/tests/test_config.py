import pytest

from app.core.config import Settings, get_settings


def test_settings_defaults_to_local_environment() -> None:
    assert Settings().environment == "local"


def test_get_settings_reads_environment_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    get_settings.cache_clear()
    try:
        assert get_settings().environment == "dev"
    finally:
        get_settings.cache_clear()
