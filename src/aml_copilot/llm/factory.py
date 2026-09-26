"""LLM Provider Factory — constructs LangChain-compatible chat model instances.

Single point of construction for all supported providers. Agent code
never imports provider SDKs directly; it always goes through this factory.
"""

from __future__ import annotations

from typing import List, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from aml_copilot.config import Settings, get_settings
from aml_copilot.exceptions import AgentConfigurationError
from aml_copilot.llm.models import ProviderConfig
from aml_copilot.logger import get_logger

logger = get_logger(__name__)

# Default model identifiers — can be overridden via environment
_DEFAULTS: dict[str, str] = {
    "groq": "openai/gpt-oss-120b",
    "gemini": "gemini-3.8-flash",
    "openrouter": "inclusionai/ling-3.0-flash-fin:free",
    "nvidia": "meta/llama-3.3-70b-instruct",
    "openai": "gpt-4o-mini",
}


def build_chat_model(config: ProviderConfig) -> BaseChatModel:
    """Instantiate a LangChain-compatible chat model for the given provider config.

    Supported providers: 'groq', 'gemini', 'openrouter', 'nvidia', 'openai'

    Raises:
        AgentConfigurationError: If API key is missing or provider is unsupported.
    """
    name = config.name.strip().lower()

    if name == "groq":
        return _build_groq(config)
    if name == "gemini":
        return _build_gemini(config)
    if name == "openrouter":
        return _build_openrouter(config)
    if name == "nvidia":
        return _build_nvidia(config)
    if name == "openai":
        return _build_openai(config)

    raise AgentConfigurationError(
        f"Unsupported LLM provider '{name}'. Supported: 'groq', 'gemini', 'openrouter', 'nvidia', 'openai'."
    )


def _build_groq(config: ProviderConfig) -> BaseChatModel:
    if not config.has_credentials():
        raise AgentConfigurationError(
            "Groq API key not configured. Set GROQ_API_KEY in .env or environment."
        )
    try:
        from langchain_groq import ChatGroq  # type: ignore

        model = ChatGroq(
            model=config.model,
            temperature=config.temperature,
            api_key=config.api_key,
        )
        logger.info(f"[LLM Factory] Initialized ChatGroq with model '{config.model}'")
        return model
    except ImportError:
        raise AgentConfigurationError("langchain-groq is not installed. Run: uv add langchain-groq")
    except Exception as exc:
        raise AgentConfigurationError(f"Failed to initialize ChatGroq: {exc}") from exc


def _build_gemini(config: ProviderConfig) -> BaseChatModel:
    if not config.has_credentials():
        raise AgentConfigurationError(
            "Gemini API key not configured. Set GEMINI_API_KEY in .env or environment."
        )
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore

        model = ChatGoogleGenerativeAI(
            model=config.model,
            temperature=config.temperature,
            google_api_key=config.api_key,
        )
        logger.info(f"[LLM Factory] Initialized ChatGoogleGenerativeAI with model '{config.model}'")
        return model
    except ImportError:
        raise AgentConfigurationError(
            "langchain-google-genai is not installed. Run: uv add langchain-google-genai"
        )
    except Exception as exc:
        raise AgentConfigurationError(f"Failed to initialize ChatGoogleGenerativeAI: {exc}") from exc


def _build_openai(config: ProviderConfig) -> BaseChatModel:
    if not config.has_credentials():
        raise AgentConfigurationError(
            "OpenAI API key not configured. Set OPENAI_API_KEY in .env or environment."
        )
    try:
        from langchain_openai import ChatOpenAI  # type: ignore

        model = ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            api_key=config.api_key,
        )
        logger.info(f"[LLM Factory] Initialized ChatOpenAI with model '{config.model}'")
        return model
    except ImportError:
        raise AgentConfigurationError("langchain-openai is not installed.")
    except Exception as exc:
        raise AgentConfigurationError(f"Failed to initialize ChatOpenAI: {exc}") from exc


def _build_openrouter(config: ProviderConfig) -> BaseChatModel:
    if not config.has_credentials():
        raise AgentConfigurationError(
            "OpenRouter API key not configured. Set OPENROUTER_API_KEY in .env or environment."
        )
    try:
        from langchain_openai import ChatOpenAI  # type: ignore

        model = ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            api_key=config.api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/aml-copilot",
                "X-Title": "AML Investigation Copilot",
            },
        )
        logger.info(f"[LLM Factory] Initialized ChatOpenAI (OpenRouter) with model '{config.model}'")
        return model
    except ImportError:
        raise AgentConfigurationError("langchain-openai is not installed.")
    except Exception as exc:
        raise AgentConfigurationError(f"Failed to initialize ChatOpenAI (OpenRouter): {exc}") from exc


def _build_nvidia(config: ProviderConfig) -> BaseChatModel:
    if not config.has_credentials():
        raise AgentConfigurationError(
            "NVIDIA API key not configured. Set NVIDIA_API_KEY in .env or environment."
        )
    try:
        from langchain_openai import ChatOpenAI  # type: ignore

        model = ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            api_key=config.api_key,
            base_url=config.base_url or "https://integrate.api.nvidia.com/v1",
        )
        logger.info(f"[LLM Factory] Initialized ChatOpenAI (NVIDIA) with model '{config.model}'")
        return model
    except ImportError:
        raise AgentConfigurationError("langchain-openai is not installed.")
    except Exception as exc:
        raise AgentConfigurationError(f"Failed to initialize ChatOpenAI (NVIDIA): {exc}") from exc


class LLMFactory:
    """Top-level factory that reads application Settings and produces ProviderConfigs.

    Usage::

        factory = LLMFactory()
        primary_cfg = factory.primary_config()
        fallback_cfgs = factory.fallback_configs()
        llm = factory.build_primary()
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()

    def primary_config(self) -> ProviderConfig:
        """Build a ProviderConfig for the primary (LLM_PROVIDER) provider."""
        return self._config_for(self._settings.llm_provider)

    def fallback_configs(self) -> List[ProviderConfig]:
        """Build ProviderConfig objects for each fallback provider in order."""
        if not self._settings.llm_fallback_providers:
            return []
        names = [p.strip().lower() for p in self._settings.llm_fallback_providers.split(",") if p.strip()]
        configs = []
        for name in names:
            try:
                cfg = self._config_for(name)
                configs.append(cfg)
            except AgentConfigurationError as exc:
                # Log but don't crash — unavailable fallback is skipped at init
                logger.warning(f"[LLM Factory] Fallback provider '{name}' skipped at init: {exc}")
        return configs

    def build_primary(self) -> BaseChatModel:
        """Construct and return a chat model for the primary provider."""
        return build_chat_model(self.primary_config())

    def _config_for(self, name: str) -> ProviderConfig:
        """Build a ProviderConfig for a named provider using Settings values."""
        name = (name or "").strip().lower()
        s = self._settings

        if name == "groq":
            return ProviderConfig(
                name="groq",
                model=s.groq_model,
                api_key=s.groq_api_key,
                temperature=s.llm_temperature,
                max_context_tokens=s.groq_max_context_tokens,
                max_iterations=s.llm_max_iterations,
            )
        if name == "gemini":
            return ProviderConfig(
                name="gemini",
                model=s.gemini_model,
                api_key=s.gemini_api_key,
                temperature=s.llm_temperature,
                max_context_tokens=s.gemini_max_context_tokens,
                max_iterations=s.llm_max_iterations,
            )
        if name == "openrouter":
            return ProviderConfig(
                name="openrouter",
                model=s.openrouter_model,
                api_key=s.openrouter_api_key,
                temperature=s.llm_temperature,
                max_context_tokens=s.openrouter_max_context_tokens,
                max_iterations=s.llm_max_iterations,
                base_url=s.openrouter_base_url,
            )
        if name == "nvidia":
            return ProviderConfig(
                name="nvidia",
                model=s.nvidia_model,
                api_key=s.nvidia_api_key,
                temperature=s.llm_temperature,
                max_context_tokens=s.nvidia_max_context_tokens,
                max_iterations=s.llm_max_iterations,
                base_url=s.nvidia_base_url,
            )
        if name == "openai":
            return ProviderConfig(
                name="openai",
                model=s.llm_model,
                api_key=s.openai_api_key,
                temperature=s.llm_temperature,
                max_context_tokens=s.llm_max_context_tokens,
                max_iterations=s.llm_max_iterations,
            )

        raise AgentConfigurationError(
            f"Unknown provider '{name}'. Supported: 'groq', 'gemini', 'openrouter', 'nvidia', 'openai'."
        )
