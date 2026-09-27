"""
Phase 1: verify config loads with defaults and the cache works.
"""

from app.config import Settings, get_settings


def test_settings_defaults() -> None:
    s = Settings()
    assert s.environment == "local"
    assert s.database_pool_size == 20
    assert s.log_level == "INFO"


def test_log_level_uppercased() -> None:
    s = Settings(log_level="debug")  # type: ignore[call-arg]
    assert s.log_level == "DEBUG"


def test_get_settings_is_cached() -> None:
    a = get_settings()
    b = get_settings()
    assert a is b
