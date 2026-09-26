"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application runtime configuration settings."""

    app_name: str = "AML Investigation Copilot"
    environment: str = "development"
    log_level: str = "INFO"
    data_dir: str = "data"

    # ---------------------------------------------------------------------------
    # Primary LLM provider
    # ---------------------------------------------------------------------------
    llm_provider: str = "openai"
    """Primary LLM provider: 'groq', 'gemini', or 'openai'."""

    llm_fallback_providers: str = ""
    """Comma-separated ordered fallback providers, e.g. 'gemini,openai'. Empty = no fallback."""

    # Legacy/OpenAI provider
    openai_api_key: Optional[str] = None
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_max_iterations: int = 5
    llm_max_context_tokens: int = 6000

    # ---------------------------------------------------------------------------
    # Groq provider
    # ---------------------------------------------------------------------------
    groq_api_key: Optional[str] = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_max_context_tokens: int = 5000
    """Groq-specific context token budget (default lower due to 8000 TPM limit)."""

    # ---------------------------------------------------------------------------
    # Gemini provider
    # ---------------------------------------------------------------------------
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.8-flash"
    gemini_max_context_tokens: int = 20000
    """Gemini context token budget (much larger context window available)."""

    # ---------------------------------------------------------------------------
    # OpenRouter provider
    # ---------------------------------------------------------------------------
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "inclusionai/ling-3.0-flash-fin:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_max_context_tokens: int = 12000
    """OpenRouter context token budget."""

    # ---------------------------------------------------------------------------
    # NVIDIA provider (build.nvidia.com)
    # ---------------------------------------------------------------------------
    nvidia_api_key: Optional[str] = None
    nvidia_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_max_context_tokens: int = 16384
    """NVIDIA context token budget."""

    # ---------------------------------------------------------------------------
    # RAG Knowledge Base configuration
    # ---------------------------------------------------------------------------
    knowledge_dir: str = "data/knowledge"
    vector_store_dir: Optional[str] = None
    embedding_provider: str = "local"
    embedding_model: str = "text-embedding-3-small"
    retrieval_top_k: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def _get_cached_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    """Return an application settings instance refreshed from .env."""
    from pathlib import Path
    env_file = Path(".env")
    if env_file.exists():
        try:
            import dotenv
            dotenv.load_dotenv(dotenv_path=env_file, override=True)
        except Exception:
            pass
    return _get_cached_settings()


get_settings.cache_clear = _get_cached_settings.cache_clear  # type: ignore[attr-defined]
