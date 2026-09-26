"""FailoverLLM — provider-transparent BaseChatModel with automatic failover.

Wraps an ordered list of (ProviderConfig, BaseChatModel) pairs.  On any
retryable provider error it immediately tries the next provider in order,
emitting SSE telemetry at each transition.  The calling LangGraph node
never sees the transition; it only receives the final successful response
or a ProviderFailoverExhausted exception if all providers fail.

Key guarantees:
- Does NOT restart the investigation.
- Does NOT reset message state.
- Does NOT re-run tools, PDF parsing, or detection.
- The same prepared messages are forwarded to each provider in turn.
- Investigation ID is unchanged across provider switches.
- API keys are never logged or emitted in SSE metadata.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from aml_copilot.llm.classifier import classify_provider_error
from aml_copilot.llm.exceptions import (
    ProviderAuthError,
    ProviderFailoverExhausted,
)
from aml_copilot.llm.factory import LLMFactory, build_chat_model
from aml_copilot.llm.models import ProviderConfig
from aml_copilot.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal telemetry helper
# ---------------------------------------------------------------------------

def _emit_provider_event(
    event_callback: Optional[Callable],
    investigation_id: Optional[str],
    event_type: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a provider-switch event to the SSE bus if a callback is available."""
    if not event_callback:
        return
    try:
        from aml_copilot.events.models import InvestigationEvent

        event = InvestigationEvent(
            investigation_id=investigation_id or "unknown",
            event_type=event_type,
            node="llm_failover",
            message=message,
            metadata=metadata or {},
        )
        event_callback(event)
    except Exception as exc:
        logger.debug(f"[FailoverLLM] Failed to emit provider event: {exc}")


# ---------------------------------------------------------------------------
# FailoverLLM
# ---------------------------------------------------------------------------

class FailoverLLM(BaseChatModel):
    """Provider-transparent BaseChatModel that transparently fails over.

    Satisfies the full LangChain BaseChatModel interface so it can be used
    anywhere a regular chat model is expected, including .bind_tools().

    Attributes:
        providers: Ordered list of (ProviderConfig, BaseChatModel) pairs.
        event_callback: Optional callable for SSE provider-transition events.
        investigation_id: Optional investigation ID for event correlation.
    """

    # Pydantic v2 configuration
    model_config = {"arbitrary_types_allowed": True}

    # Pydantic fields
    providers: List[Any] = []  # List[tuple[ProviderConfig, BaseChatModel]]
    event_callback: Optional[Any] = None
    investigation_id: Optional[str] = None

    @classmethod
    def from_factory(
        cls,
        factory: Optional[LLMFactory] = None,
        event_callback: Optional[Callable] = None,
        investigation_id: Optional[str] = None,
    ) -> "FailoverLLM":
        """Construct a FailoverLLM from an LLMFactory + its fallbacks.

        Providers that lack credentials are silently skipped rather than
        crashing the entire agent startup.
        """
        if factory is None:
            factory = LLMFactory()

        provider_pairs: list = []

        # Primary
        primary_cfg = factory.primary_config()
        try:
            primary_llm = build_chat_model(primary_cfg)
            provider_pairs.append((primary_cfg, primary_llm))
            logger.info(f"[FailoverLLM] Primary provider: {primary_cfg.name} / {primary_cfg.model}")
        except Exception as exc:
            logger.error(f"[FailoverLLM] Primary provider '{primary_cfg.name}' failed to initialise: {exc}")

        # Fallbacks
        for fb_cfg in factory.fallback_configs():
            try:
                fb_llm = build_chat_model(fb_cfg)
                provider_pairs.append((fb_cfg, fb_llm))
                logger.info(f"[FailoverLLM] Fallback provider: {fb_cfg.name} / {fb_cfg.model}")
            except Exception as exc:
                logger.warning(f"[FailoverLLM] Fallback provider '{fb_cfg.name}' skipped: {exc}")

        if not provider_pairs:
            from aml_copilot.exceptions import AgentConfigurationError
            raise AgentConfigurationError(
                "No LLM providers could be initialised. "
                "Check LLM_PROVIDER / LLM_FALLBACK_PROVIDERS and corresponding API keys."
            )

        return cls(
            providers=provider_pairs,
            event_callback=event_callback,
            investigation_id=investigation_id,
        )

    # ------------------------------------------------------------------
    # Required BaseChatModel abstract implementation
    # ------------------------------------------------------------------

    @property
    def _llm_type(self) -> str:  # type: ignore[override]
        return "failover"

    def _generate(  # type: ignore[override]
        self,
        messages: Sequence[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Invoke providers in order, failing over on retryable errors."""
        causes: list = []

        for idx, (cfg, llm) in enumerate(self.providers):
            provider_name: str = cfg.name
            is_primary = idx == 0

            _emit_provider_event(
                self.event_callback,
                self.investigation_id,
                "LLM_PROVIDER_ATTEMPT",
                f"LLM request dispatched to provider: {provider_name.upper()} / {cfg.model}",
                {"provider": provider_name, "model": cfg.model, "attempt": idx + 1},
            )
            logger.info(
                f"[FailoverLLM] Attempting provider {idx + 1}/{len(self.providers)}: "
                f"{provider_name} / {cfg.model}"
            )

            try:
                # Use .invoke() rather than ._generate() because the stored llm may be
                # a _ChatModelBinding (result of bind_tools), which is a RunnableBinding.
                # Calling ._generate() directly on a RunnableBinding is unreliable;
                # .invoke() is the correct public API for all LangChain models and bindings.
                ai_msg = llm.invoke(list(messages), stop=stop, **(kwargs if kwargs else {}))  # type: ignore[union-attr]
                result = ChatResult(generations=[ChatGeneration(message=ai_msg)])
                _emit_provider_event(
                    self.event_callback,
                    self.investigation_id,
                    "LLM_PROVIDER_SELECTED",
                    f"Provider {provider_name.upper()} responded successfully.",
                    {"provider": provider_name, "model": cfg.model},
                )
                if not is_primary:
                    logger.info(f"[FailoverLLM] Failover succeeded via {provider_name}")
                return result


            except Exception as raw_exc:
                # Log full exception detail before classification — essential for
                # diagnosing future 'unclassified' errors.
                logger.warning(
                    f"[FailoverLLM] Provider '{provider_name}' raised "
                    f"{type(raw_exc).__name__}: {str(raw_exc)[:400]}"
                    f" | status_code={getattr(raw_exc, 'status_code', None)}"
                    f" | status={getattr(raw_exc, 'status', None)}"
                )
                classified = classify_provider_error(raw_exc, provider=provider_name)

                if isinstance(classified, ProviderAuthError):
                    logger.error(
                        f"[FailoverLLM] Non-retryable auth error from '{provider_name}': {classified}"
                    )
                    _emit_provider_event(
                        self.event_callback,
                        self.investigation_id,
                        "LLM_PROVIDER_FAILED",
                        f"Provider {provider_name.upper()} returned an authentication error ({classified.status_code}).",
                        {
                            "provider": provider_name,
                            "reason": "auth_error",
                            "status_code": classified.status_code,
                        },
                    )
                    # Auth error on the primary provider must fail fast to alert operator of misconfiguration.
                    # Auth error on a secondary fallback cascades to any remaining fallbacks.
                    if is_primary:
                        raise classified from raw_exc

                    causes.append(classified)
                    next_idx = idx + 1
                    if next_idx < len(self.providers):
                        next_cfg: ProviderConfig = self.providers[next_idx][0]
                        _emit_provider_event(
                            self.event_callback,
                            self.investigation_id,
                            "LLM_PROVIDER_FALLBACK",
                            f"Fallback provider {provider_name.upper()} auth failed. Cascading to next fallback: {next_cfg.name.upper()} / {next_cfg.model}",
                            {
                                "primary_provider": self.providers[0][0].name,
                                "failed_provider": provider_name,
                                "fallback_provider": next_cfg.name,
                                "reason": "auth_error",
                                "status_code": classified.status_code,
                            },
                        )
                        continue
                    raise classified from raw_exc

                # Retryable error — log, emit telemetry, try next provider
                logger.warning(
                    f"[FailoverLLM] Retryable error from '{provider_name}' "
                    f"(status={classified.status_code}, reason={classified.reason}): {classified}"
                )
                causes.append(classified)

                _emit_provider_event(
                    self.event_callback,
                    self.investigation_id,
                    "LLM_PROVIDER_FAILED",
                    f"Provider {provider_name.upper()} failed ({classified.reason.replace('_', ' ').upper()}). "
                    f"Attempting failover...",
                    {
                        "failed_provider": provider_name,
                        "reason": classified.reason,
                        "status_code": classified.status_code,
                    },
                )

                # Announce the next provider if one exists
                next_idx = idx + 1
                if next_idx < len(self.providers):
                    next_cfg: ProviderConfig = self.providers[next_idx][0]
                    _emit_provider_event(
                        self.event_callback,
                        self.investigation_id,
                        "LLM_PROVIDER_FALLBACK",
                        f"Switching to fallback provider: {next_cfg.name.upper()} / {next_cfg.model}",
                        {
                            "primary_provider": self.providers[0][0].name,
                            "failed_provider": provider_name,
                            "fallback_provider": next_cfg.name,
                            "reason": classified.reason,
                            "status_code": classified.status_code,
                        },
                    )

        # All providers exhausted
        error_summary = "; ".join(f"{c.provider}({c.reason})" for c in causes)
        exc = ProviderFailoverExhausted(
            f"All configured LLM providers failed. Tried: {error_summary}",
            causes=causes,
        )
        logger.error(f"[FailoverLLM] All providers exhausted: {error_summary}")
        raise exc

    # ------------------------------------------------------------------
    # bind_tools / structured output forwarding
    # ------------------------------------------------------------------

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FailoverLLM":
        """Bind tools to ALL underlying providers and return a new FailoverLLM.

        This ensures that whichever provider ends up serving the request
        already has the tool definitions registered.
        """
        bound_pairs = []
        for cfg, llm in self.providers:
            try:
                bound_llm = llm.bind_tools(tools, **kwargs)
                bound_pairs.append((cfg, bound_llm))
            except Exception as exc:
                logger.warning(
                    f"[FailoverLLM] Provider '{cfg.name}' does not support bind_tools: {exc}. "
                    "It will be skipped for tool-call requests."
                )
                # Still include so _generate can raise a meaningful error
                bound_pairs.append((cfg, llm))

        new_instance = FailoverLLM(
            providers=bound_pairs,
            event_callback=self.event_callback,
            investigation_id=self.investigation_id,
        )
        return new_instance

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        """Forward structured output binding to the primary provider."""
        if not self.providers:
            raise RuntimeError("No providers configured")
        _cfg, primary_llm = self.providers[0]
        return primary_llm.with_structured_output(schema, **kwargs)

    # ------------------------------------------------------------------
    # Convenience: update event context for a specific investigation
    # ------------------------------------------------------------------

    def with_investigation_context(
        self,
        investigation_id: Optional[str],
        event_callback: Optional[Callable],
    ) -> "FailoverLLM":
        """Return a copy with updated investigation ID and event callback."""
        return FailoverLLM(
            providers=list(self.providers),
            event_callback=event_callback,
            investigation_id=investigation_id,
        )

    @property
    def active_provider_name(self) -> str:
        """Return the name of the first configured provider."""
        if self.providers:
            return self.providers[0][0].name
        return "none"

    @property
    def provider_names(self) -> List[str]:
        """Return names of all configured providers in order."""
        return [cfg.name for cfg, _ in self.providers]
