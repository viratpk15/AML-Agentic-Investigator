"""Provider descriptor model — lightweight config DTO for one LLM provider."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProviderConfig:
    """Runtime configuration snapshot for a single LLM provider.

    This is a pure-data container passed to provider factories and the
    failover manager.  It intentionally does NOT hold raw API keys in
    string attributes visible from repr(); use the ``api_key`` property.
    """

    name: str
    """Short provider identifier used in logs and SSE events: 'groq', 'gemini', 'openai'."""

    model: str
    """Model identifier string forwarded to the provider SDK."""

    temperature: float = 0.0
    max_context_tokens: int = 6000
    max_iterations: int = 5

    base_url: Optional[str] = None
    _api_key: Optional[str] = field(default=None, repr=False)

    def __init__(
        self,
        name: str,
        model: str,
        api_key: Optional[str] = None,
        temperature: float = 0.0,
        max_context_tokens: int = 6000,
        max_iterations: int = 5,
        base_url: Optional[str] = None,
    ) -> None:
        self.name = name
        self.model = model
        self._api_key = api_key
        self.temperature = temperature
        self.max_context_tokens = max_context_tokens
        self.max_iterations = max_iterations
        self.base_url = base_url

    @property
    def api_key(self) -> Optional[str]:
        """Return the API key. Not included in repr() to prevent accidental logging."""
        return self._api_key

    def has_credentials(self) -> bool:
        """Return True if an API key is present."""
        return bool(self._api_key)

    def __repr__(self) -> str:
        return (
            f"ProviderConfig(name={self.name!r}, model={self.model!r}, "
            f"temperature={self.temperature}, max_context_tokens={self.max_context_tokens})"
        )
