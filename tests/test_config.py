"""Unit tests for configuration management."""

import pytest
from aml_copilot.config import Settings, get_settings


def test_default_settings(monkeypatch):
    """Verify default settings values."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(_env_file=None)
    assert settings.app_name == "AML Investigation Copilot"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.data_dir == "data"
    assert settings.llm_provider == "openai"
    assert settings.groq_api_key is None


def test_get_settings_caching():
    """Verify get_settings returns cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_settings_environment_override(monkeypatch):
    """Verify environment variables override default settings."""
    monkeypatch.setenv("APP_NAME", "Test AML Copilot")
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATA_DIR", "/tmp/aml_data")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    settings = Settings(_env_file=None)
    assert settings.app_name == "Test AML Copilot"
    assert settings.environment == "testing"
    assert settings.log_level == "DEBUG"
    assert settings.data_dir == "/tmp/aml_data"
    assert settings.llm_provider == "groq"
    assert settings.groq_api_key == "test-groq-key"
