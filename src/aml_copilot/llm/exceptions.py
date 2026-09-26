"""LLM provider-specific exceptions, separate from core AMLCopilotError hierarchy."""

from aml_copilot.exceptions import AMLCopilotError


class ProviderError(AMLCopilotError):
    """Base exception for all LLM provider errors."""

    def __init__(self, message: str, provider: str = "unknown", status_code: int = 0) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class ProviderRetryableError(ProviderError):
    """A transient error that can be retried with a different provider.

    Examples: 429 rate limit, 413 request too large, 503 unavailable, timeout.
    """

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        status_code: int = 0,
        reason: str = "unknown",
    ) -> None:
        super().__init__(message, provider=provider, status_code=status_code)
        self.reason = reason


class ProviderAuthError(ProviderError):
    """Non-retryable authentication or configuration error.

    Examples: invalid API key, invalid request schema, malformed tool definition.
    These must NOT trigger provider fallback since another provider won't fix them.
    """


class ProviderFailoverExhausted(ProviderError):
    """All configured providers (primary + fallbacks) have been tried and all failed."""

    def __init__(self, message: str, causes: list) -> None:
        super().__init__(message, provider="all")
        self.causes = causes
