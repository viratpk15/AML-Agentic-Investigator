"""Provider-agnostic LLM abstraction with automatic failover for AML Copilot."""

from aml_copilot.llm.factory import LLMFactory
from aml_copilot.llm.failover import FailoverLLM
from aml_copilot.llm.exceptions import (
    ProviderError,
    ProviderFailoverExhausted,
    ProviderAuthError,
    ProviderRetryableError,
)

__all__ = [
    "LLMFactory",
    "FailoverLLM",
    "ProviderError",
    "ProviderFailoverExhausted",
    "ProviderAuthError",
    "ProviderRetryableError",
]
