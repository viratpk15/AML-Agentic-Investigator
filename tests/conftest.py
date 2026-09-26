"""Pytest fixtures for AML Copilot M1 tests."""

import pytest
from aml_copilot.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear lru_cache for get_settings before and after each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def default_settings() -> Settings:
    """Fixture providing default settings instance."""
    return Settings()
