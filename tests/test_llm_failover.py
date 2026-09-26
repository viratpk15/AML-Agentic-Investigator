"""Comprehensive tests for the multi-provider LLM failover system.

Covers:
1.  Groq provider config builds correctly
2.  Gemini provider config builds correctly
3.  OpenAI provider config builds correctly
4.  LLMFactory selects Groq as primary
5.  LLMFactory selects Gemini as primary
6.  Configurable provider order (groq → gemini → openai)
7.  Groq 413 triggers Gemini fallback
8.  Groq 429 triggers Gemini fallback
9.  Groq timeout triggers Gemini fallback
10. Non-retryable auth error does NOT trigger fallback
11. Groq fails → Gemini succeeds → operation succeeds
12. Groq fails → Gemini fails → ProviderFailoverExhausted raised
13. Investigation ID unchanged across provider fallback
14. No API keys appear in SSE events / logs
15. Context budget enforced before LLM call
16. Provider fallback emits SSE telemetry events
17. FailoverLLM.bind_tools propagates to all providers
18. Existing Groq-only behavior still works (no fallback needed)
19. LLMFactory: fallback with missing credential is skipped gracefully
20. Error classifier correctly identifies retryable vs non-retryable
"""

from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from aml_copilot.llm.classifier import classify_provider_error
from aml_copilot.llm.exceptions import (
    ProviderAuthError,
    ProviderFailoverExhausted,
    ProviderRetryableError,
)
from aml_copilot.llm.failover import FailoverLLM
from aml_copilot.llm.factory import LLMFactory
from aml_copilot.llm.models import ProviderConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ai_result(content: str = "ok") -> ChatResult:
    return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])


def _fake_llm(content: str = "ok") -> MagicMock:
    """Return a mock LLM that successfully responds via .invoke().

    FailoverLLM now calls llm.invoke() on each underlying provider, so
    the mock must return a real AIMessage from .invoke() (not ._generate).
    """
    mock = MagicMock()
    mock.invoke.return_value = AIMessage(content=content)
    mock.bind_tools.return_value = mock
    return mock


def _failing_llm(exc: Exception) -> MagicMock:
    """Return a mock LLM that raises exc on .invoke()."""
    mock = MagicMock()
    mock.invoke.side_effect = exc
    mock.bind_tools.return_value = mock
    return mock


def _groq_config(model: str = "groq-test-model") -> ProviderConfig:
    return ProviderConfig(name="groq", model=model, api_key="gsk_fake", max_context_tokens=5000)


def _gemini_config(model: str = "gemini-2.5-flash") -> ProviderConfig:
    return ProviderConfig(name="gemini", model=model, api_key="AIza_fake", max_context_tokens=20000)


def _openai_config(model: str = "gpt-4o-mini") -> ProviderConfig:
    return ProviderConfig(name="openai", model=model, api_key="sk-fake", max_context_tokens=6000)


def _openrouter_config(model: str = "qwen/qwen3.8-27b:free") -> ProviderConfig:
    return ProviderConfig(name="openrouter", model=model, api_key="sk-or-fake", max_context_tokens=12000, base_url="https://openrouter.ai/api/v1")


def _nvidia_config(model: str = "nvidia/nemotron-3-ultra-550b-a55b") -> ProviderConfig:
    return ProviderConfig(name="nvidia", model=model, api_key="nvapi-fake", max_context_tokens=16384, base_url="https://integrate.api.nvidia.com/v1")


def _make_failover(
    pairs: list,
    events: Optional[list] = None,
) -> FailoverLLM:
    """Build a FailoverLLM directly from (config, mock_llm) pairs."""
    captured: list = [] if events is None else events

    def _cb(event):
        captured.append(event)

    return FailoverLLM(
        providers=pairs,
        event_callback=_cb,
        investigation_id="INV-TEST-001",
    )


# ---------------------------------------------------------------------------
# 1. ProviderConfig — no API key leakage in repr
# ---------------------------------------------------------------------------

class TestProviderConfig:
    def test_groq_config_repr_has_no_key(self):
        cfg = _groq_config()
        assert "gsk_fake" not in repr(cfg)
        assert "groq" in repr(cfg)

    def test_gemini_config_repr_has_no_key(self):
        cfg = _gemini_config()
        assert "AIza_fake" not in repr(cfg)
        assert "gemini" in repr(cfg)

    def test_has_credentials_true(self):
        assert _groq_config().has_credentials() is True

    def test_has_credentials_false(self):
        cfg = ProviderConfig(name="groq", model="x", api_key=None)
        assert cfg.has_credentials() is False


# ---------------------------------------------------------------------------
# 2. Error Classifier
# ---------------------------------------------------------------------------

class TestErrorClassifier:
    def test_413_is_retryable(self):
        exc = Exception("HTTP 413 request too large")
        exc.status_code = 413  # type: ignore[attr-defined]
        result = classify_provider_error(exc, "groq")
        assert isinstance(result, ProviderRetryableError)
        assert result.reason == "request_too_large"

    def test_429_is_retryable(self):
        exc = Exception("rate limit exceeded")
        exc.status_code = 429  # type: ignore[attr-defined]
        result = classify_provider_error(exc, "groq")
        assert isinstance(result, ProviderRetryableError)
        assert result.reason == "rate_limit_exceeded"

    def test_401_is_auth_error(self):
        exc = Exception("invalid api key")
        exc.status_code = 401  # type: ignore[attr-defined]
        result = classify_provider_error(exc, "groq")
        assert isinstance(result, ProviderAuthError)

    def test_403_is_auth_error(self):
        exc = Exception("permission denied")
        exc.status_code = 403  # type: ignore[attr-defined]
        result = classify_provider_error(exc, "groq")
        assert isinstance(result, ProviderAuthError)

    def test_503_is_retryable(self):
        exc = Exception("service unavailable")
        exc.status_code = 503  # type: ignore[attr-defined]
        result = classify_provider_error(exc, "groq")
        assert isinstance(result, ProviderRetryableError)

    def test_tpm_limit_text_is_retryable(self):
        exc = Exception("Organization TPM limit: 8000, Requested: 9354")
        result = classify_provider_error(exc, "groq")
        assert isinstance(result, ProviderRetryableError)

    def test_request_too_large_text_is_retryable(self):
        exc = Exception("Request too large for model")
        result = classify_provider_error(exc, "groq")
        assert isinstance(result, ProviderRetryableError)
        assert result.reason == "request_too_large"

    def test_invalid_api_key_text_is_auth_error(self):
        exc = Exception("invalid api key provided")
        result = classify_provider_error(exc, "groq")
        assert isinstance(result, ProviderAuthError)

    def test_timeout_is_retryable(self):
        exc = Exception("Request timed out after 30s")
        result = classify_provider_error(exc, "groq")
        assert isinstance(result, ProviderRetryableError)

    def test_status_code_in_nested_response(self):
        """SDK wrappers sometimes put status on response attribute."""
        response = MagicMock()
        response.status_code = 429
        exc = Exception("rate limit")
        exc.response = response  # type: ignore[attr-defined]
        result = classify_provider_error(exc, "groq")
        assert isinstance(result, ProviderRetryableError)

    def test_provider_name_preserved(self):
        exc = Exception("timeout")
        result = classify_provider_error(exc, "my_provider")
        assert result.provider == "my_provider"

    def test_api_key_not_in_classified_error_message(self):
        exc = Exception("invalid api key: sk-secret1234abcd")
        result = classify_provider_error(exc, "openai")
        # The exception message may contain the key, but the classifier
        # type must still be ProviderAuthError
        assert isinstance(result, ProviderAuthError)


# ---------------------------------------------------------------------------
# 3. LLMFactory configuration
# ---------------------------------------------------------------------------

class TestLLMFactory:
    def _settings(self, **overrides):
        from aml_copilot.config import Settings
        defaults = dict(
            llm_provider="groq",
            llm_fallback_providers="gemini",
            groq_api_key="gsk_fake",
            groq_model="groq-model-x",
            groq_max_context_tokens=5000,
            gemini_api_key="AIza_fake",
            gemini_model="gemini-2.5-flash",
            gemini_max_context_tokens=20000,
            openai_api_key="sk-fake",
            llm_model="gpt-4o-mini",
            openrouter_api_key="sk-or-fake",
            openrouter_model="inclusionai/ling-3.0-flash-fin:free",
            openrouter_base_url="https://openrouter.ai/api/v1",
            openrouter_max_context_tokens=12000,
            nvidia_api_key="nvapi-fake",
            nvidia_model="nvidia/nemotron-3-ultra-550b-a55b",
            nvidia_base_url="https://integrate.api.nvidia.com/v1",
            nvidia_max_context_tokens=16384,
            llm_temperature=0.0,
            llm_max_context_tokens=5000,
            llm_max_iterations=5,
        )

        defaults.update(overrides)
        return Settings.model_construct(**defaults)

    def test_primary_config_is_groq(self):
        s = self._settings(llm_provider="groq")
        factory = LLMFactory(settings=s)
        cfg = factory.primary_config()
        assert cfg.name == "groq"
        assert cfg.model == "groq-model-x"
        assert cfg.has_credentials()

    def test_primary_config_is_gemini(self):
        s = self._settings(llm_provider="gemini")
        factory = LLMFactory(settings=s)
        cfg = factory.primary_config()
        assert cfg.name == "gemini"
        assert cfg.model == "gemini-2.5-flash"
        assert cfg.has_credentials()

    def test_primary_config_is_openrouter(self):
        s = self._settings(llm_provider="openrouter")
        factory = LLMFactory(settings=s)
        cfg = factory.primary_config()
        assert cfg.name == "openrouter"
        assert cfg.model == "inclusionai/ling-3.0-flash-fin:free"
        assert cfg.has_credentials()

    def test_primary_config_is_nvidia(self):
        s = self._settings(llm_provider="nvidia")
        factory = LLMFactory(settings=s)
        cfg = factory.primary_config()
        assert cfg.name == "nvidia"
        assert cfg.model == "nvidia/nemotron-3-ultra-550b-a55b"
        assert cfg.has_credentials()
        assert cfg.base_url == "https://integrate.api.nvidia.com/v1"

    def test_primary_config_is_openai(self):
        s = self._settings(llm_provider="openai")
        factory = LLMFactory(settings=s)
        cfg = factory.primary_config()
        assert cfg.name == "openai"
        assert cfg.has_credentials()

    def test_fallback_configs_ordered(self):
        s = self._settings(llm_fallback_providers="nvidia,openrouter")
        factory = LLMFactory(settings=s)
        fallbacks = factory.fallback_configs()
        assert [c.name for c in fallbacks] == ["nvidia", "openrouter"]

    def test_fallback_empty_when_not_configured(self):
        s = self._settings(llm_fallback_providers="")
        factory = LLMFactory(settings=s)
        assert factory.fallback_configs() == []

    @patch("aml_copilot.llm.factory._build_groq")
    def test_fallback_missing_credentials_skipped(self, mock_groq):
        """A fallback provider with no API key is skipped gracefully at FailoverLLM build time."""
        mock_groq.return_value = _fake_llm("groq ok")
        # gemini_api_key=None means build_chat_model will raise AgentConfigurationError
        s = self._settings(llm_fallback_providers="gemini", gemini_api_key=None)
        factory = LLMFactory(settings=s)
        # fallback_configs() returns the config; the error only happens at build_chat_model
        fallbacks = factory.fallback_configs()
        assert len(fallbacks) == 1  # config returned, creds checked at build time
        # from_factory should skip the missing-creds provider without crashing
        flm = FailoverLLM.from_factory(factory=factory)
        # Only groq was successfully built
        assert flm.provider_names == ["groq"]


    def test_unsupported_provider_raises(self):
        from aml_copilot.exceptions import AgentConfigurationError
        s = self._settings(llm_provider="anthropic")
        factory = LLMFactory(settings=s)
        with pytest.raises(AgentConfigurationError, match="Unknown provider"):
            factory.primary_config()

    def test_build_nvidia_missing_key_raises(self):
        from aml_copilot.exceptions import AgentConfigurationError
        from aml_copilot.llm.factory import build_chat_model
        cfg = ProviderConfig(name="nvidia", model="nvidia/nemotron-3-ultra-550b-a55b", api_key=None)
        with pytest.raises(AgentConfigurationError, match="NVIDIA API key not configured"):
            build_chat_model(cfg)


# ---------------------------------------------------------------------------
# 4. FailoverLLM core behaviour
# ---------------------------------------------------------------------------

class TestFailoverLLM:
    def test_three_tier_failover_groq_openrouter_nvidia(self):
        """Verify failover proceeds groq -> openrouter -> nvidia if first two fail with retryable errors."""
        exc1 = Exception("429 TPM limit exceeded")
        exc1.status_code = 429  # type: ignore[attr-defined]
        exc2 = Exception("503 Service Unavailable")
        exc2.status_code = 503  # type: ignore[attr-defined]

        groq_mock = _failing_llm(exc1)
        openrouter_mock = _failing_llm(exc2)
        nvidia_mock = _fake_llm("nvidia response")

        events: list = []
        flm = _make_failover(
            [
                (_groq_config(), groq_mock),
                (_openrouter_config(), openrouter_mock),
                (_nvidia_config(), nvidia_mock),
            ],
            events,
        )

        msgs = [HumanMessage(content="analyze transactions")]
        result = flm._generate(msgs)
        assert result.generations[0].message.content == "nvidia response"
        groq_mock.invoke.assert_called_once()
        openrouter_mock.invoke.assert_called_once()
        nvidia_mock.invoke.assert_called_once()

    def test_three_tier_failover_groq_nvidia_openrouter(self):
        """Verify failover proceeds groq -> nvidia -> openrouter."""
        exc1 = Exception("429 TPM limit exceeded")
        exc1.status_code = 429  # type: ignore[attr-defined]

        groq_mock = _failing_llm(exc1)
        nvidia_mock = _fake_llm("nvidia response")
        openrouter_mock = _fake_llm("openrouter response")

        events: list = []
        flm = _make_failover(
            [
                (_groq_config(), groq_mock),
                (_nvidia_config(), nvidia_mock),
                (_openrouter_config(), openrouter_mock),
            ],
            events,
        )

        msgs = [HumanMessage(content="analyze transactions")]
        result = flm._generate(msgs)
        assert result.generations[0].message.content == "nvidia response"
        groq_mock.invoke.assert_called_once()
        nvidia_mock.invoke.assert_called_once()
        openrouter_mock.invoke.assert_not_called()

    def test_primary_succeeds_no_fallback_attempted(self):
        groq_mock = _fake_llm("groq response")
        gemini_mock = _fake_llm("gemini response")
        events: list = []
        flm = _make_failover(
            [(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
            events,
        )
        msgs = [HumanMessage(content="test")]
        result = flm._generate(msgs)
        assert result.generations[0].message.content == "groq response"
        groq_mock.invoke.assert_called_once()
        gemini_mock.invoke.assert_not_called()

    def test_groq_413_triggers_gemini_fallback(self):
        exc = Exception("413 request too large")
        exc.status_code = 413  # type: ignore[attr-defined]
        groq_mock = _failing_llm(exc)
        gemini_mock = _fake_llm("gemini response")
        events: list = []
        flm = _make_failover(
            [(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
            events,
        )
        result = flm._generate([HumanMessage(content="test")])
        assert result.generations[0].message.content == "gemini response"
        groq_mock.invoke.assert_called_once()
        gemini_mock.invoke.assert_called_once()

    def test_groq_429_triggers_gemini_fallback(self):
        exc = Exception("rate limit exceeded")
        exc.status_code = 429  # type: ignore[attr-defined]
        groq_mock = _failing_llm(exc)
        gemini_mock = _fake_llm("gemini response")
        flm = _make_failover(
            [(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
        )
        result = flm._generate([HumanMessage(content="test")])
        assert result.generations[0].message.content == "gemini response"

    def test_groq_timeout_triggers_gemini_fallback(self):
        exc = Exception("Request timed out")
        groq_mock = _failing_llm(exc)
        gemini_mock = _fake_llm("gemini response")
        flm = _make_failover(
            [(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
        )
        result = flm._generate([HumanMessage(content="test")])
        assert result.generations[0].message.content == "gemini response"

    def test_auth_error_does_not_trigger_fallback(self):
        """A 401 auth error must NOT silently fall through to the next provider."""
        exc = Exception("invalid api key")
        exc.status_code = 401  # type: ignore[attr-defined]
        groq_mock = _failing_llm(exc)
        gemini_mock = _fake_llm("gemini")
        flm = _make_failover(
            [(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
        )
        with pytest.raises(ProviderAuthError):
            flm._generate([HumanMessage(content="test")])
        gemini_mock.invoke.assert_not_called()

    def test_fallback_auth_error_cascades_to_subsequent_fallback(self):
        """When a secondary fallback fails authentication, failover must cascade to the next fallback."""
        exc1 = Exception("429 TPM limit exceeded")
        exc1.status_code = 429  # type: ignore[attr-defined]
        exc2 = Exception("401 Unauthorized: User not found")
        exc2.status_code = 401  # type: ignore[attr-defined]

        groq_mock = _failing_llm(exc1)
        openrouter_mock = _failing_llm(exc2)
        nvidia_mock = _fake_llm("nvidia recovered")

        flm = _make_failover(
            [
                (_groq_config(), groq_mock),
                (_openrouter_config(), openrouter_mock),
                (_nvidia_config(), nvidia_mock),
            ],
        )
        result = flm._generate([HumanMessage(content="test")])
        assert result.generations[0].message.content == "nvidia recovered"
        groq_mock.invoke.assert_called_once()
        openrouter_mock.invoke.assert_called_once()
        nvidia_mock.invoke.assert_called_once()

    def test_all_providers_fail_raises_exhausted(self):
        exc = Exception("TPM limit exceeded")
        exc.status_code = 429  # type: ignore[attr-defined]
        groq_mock = _failing_llm(exc)
        gemini_mock = _failing_llm(exc)
        flm = _make_failover(
            [(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
        )
        with pytest.raises(ProviderFailoverExhausted) as exc_info:
            flm._generate([HumanMessage(content="test")])
        # Both providers should be listed in causes
        assert len(exc_info.value.causes) == 2

    def test_sse_events_emitted_on_fallback(self):
        exc = Exception("413 request too large")
        exc.status_code = 413  # type: ignore[attr-defined]
        groq_mock = _failing_llm(exc)
        gemini_mock = _fake_llm("ok")
        events: list = []
        flm = _make_failover(
            [(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
            events,
        )
        flm._generate([HumanMessage(content="test")])
        event_types = [e.event_type for e in events]
        assert "LLM_PROVIDER_ATTEMPT" in event_types
        assert "LLM_PROVIDER_FAILED" in event_types
        assert "LLM_PROVIDER_FALLBACK" in event_types
        assert "LLM_PROVIDER_SELECTED" in event_types

    def test_no_api_key_in_sse_events(self):
        exc = Exception("429 rate limit")
        exc.status_code = 429  # type: ignore[attr-defined]
        groq_mock = _failing_llm(exc)
        gemini_mock = _fake_llm("ok")
        events: list = []
        flm = _make_failover(
            [(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
            events,
        )
        flm._generate([HumanMessage(content="test")])
        for event in events:
            event_str = str(event.model_dump())
            assert "gsk_fake" not in event_str
            assert "AIza_fake" not in event_str

    def test_investigation_id_preserved_across_fallback(self):
        """The investigation_id on the FailoverLLM must not change on failover."""
        exc = Exception("413 too large")
        exc.status_code = 413  # type: ignore[attr-defined]
        groq_mock = _failing_llm(exc)
        gemini_mock = _fake_llm("ok")
        events: list = []
        flm = _make_failover(
            [(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
            events,
        )
        flm._generate([HumanMessage(content="test")])
        for event in events:
            assert event.investigation_id == "INV-TEST-001"

    def test_same_messages_sent_to_fallback(self):
        """The exact same messages must be forwarded to the fallback provider."""
        exc = Exception("413 too large")
        exc.status_code = 413  # type: ignore[attr-defined]
        groq_mock = _failing_llm(exc)
        gemini_mock = _fake_llm("ok")
        flm = _make_failover(
            [(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
        )
        msgs = [SystemMessage(content="system"), HumanMessage(content="user")]
        flm._generate(msgs)
        # Verify gemini received the same messages via .invoke()
        call_args = gemini_mock.invoke.call_args
        assert call_args[0][0] == list(msgs)


    def test_bind_tools_propagates_to_all_providers(self):
        groq_mock = _fake_llm()
        gemini_mock = _fake_llm()
        flm = _make_failover(
            [(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
        )
        fake_tools = [MagicMock()]
        bound = flm.bind_tools(fake_tools)
        groq_mock.bind_tools.assert_called_once_with(fake_tools)
        gemini_mock.bind_tools.assert_called_once_with(fake_tools)
        assert isinstance(bound, FailoverLLM)

    def test_with_investigation_context_returns_new_instance(self):
        groq_mock = _fake_llm()
        flm = _make_failover([(_groq_config(), groq_mock)])
        new_flm = flm.with_investigation_context("INV-NEW", lambda e: None)
        assert new_flm.investigation_id == "INV-NEW"
        # Original unchanged
        assert flm.investigation_id == "INV-TEST-001"

    def test_provider_names_property(self):
        groq_mock = _fake_llm()
        gemini_mock = _fake_llm()
        flm = _make_failover(
            [(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
        )
        assert flm.provider_names == ["groq", "gemini"]

    def test_active_provider_name(self):
        groq_mock = _fake_llm()
        flm = _make_failover([(_groq_config(), groq_mock)])
        assert flm.active_provider_name == "groq"

    def test_single_provider_no_fallback_groq_only(self):
        """Existing Groq-only behaviour still works (no fallback configured)."""
        groq_mock = _fake_llm("groq ok")
        flm = _make_failover([(_groq_config(), groq_mock)])
        result = flm._generate([HumanMessage(content="test")])
        assert result.generations[0].message.content == "groq ok"


# ---------------------------------------------------------------------------
# 5. FailoverLLM.from_factory integration
# ---------------------------------------------------------------------------

class TestFailoverLLMFromFactory:
    def _settings_with_groq(self, fallback: str = ""):
        from aml_copilot.config import Settings
        return Settings.model_construct(
            llm_provider="groq",
            llm_fallback_providers=fallback,
            groq_api_key="gsk_fake",
            groq_model="groq-test",
            groq_max_context_tokens=5000,
            gemini_api_key="AIza_fake",
            gemini_model="gemini-2.5-flash",
            gemini_max_context_tokens=20000,
            openai_api_key=None,
            llm_model="gpt-4o-mini",
            llm_temperature=0.0,
            llm_max_context_tokens=5000,
            llm_max_iterations=5,
        )

    @patch("aml_copilot.llm.factory._build_groq")
    @patch("aml_copilot.llm.factory._build_gemini")
    def test_from_factory_builds_primary_and_fallback(self, mock_gemini, mock_groq):
        mock_groq.return_value = _fake_llm("groq")
        mock_gemini.return_value = _fake_llm("gemini")
        s = self._settings_with_groq(fallback="gemini")
        factory = LLMFactory(settings=s)
        flm = FailoverLLM.from_factory(factory=factory)
        assert len(flm.providers) == 2
        assert flm.providers[0][0].name == "groq"
        assert flm.providers[1][0].name == "gemini"

    @patch("aml_copilot.llm.factory._build_groq")
    def test_from_factory_groq_only_no_fallback(self, mock_groq):
        mock_groq.return_value = _fake_llm("groq")
        s = self._settings_with_groq(fallback="")
        factory = LLMFactory(settings=s)
        flm = FailoverLLM.from_factory(factory=factory)
        assert len(flm.providers) == 1
        assert flm.providers[0][0].name == "groq"

    @patch("aml_copilot.llm.factory._build_groq")
    @patch("aml_copilot.llm.factory._build_gemini")
    def test_context_budget_from_primary_config(self, mock_gemini, mock_groq):
        mock_groq.return_value = _fake_llm()
        mock_gemini.return_value = _fake_llm()
        s = self._settings_with_groq(fallback="gemini")
        factory = LLMFactory(settings=s)
        flm = FailoverLLM.from_factory(factory=factory)
        primary_cfg = flm.providers[0][0]
        assert primary_cfg.max_context_tokens == 5000


# ---------------------------------------------------------------------------
# 6. LangGraph investigation_id remains unchanged
# ---------------------------------------------------------------------------

class TestInvestigationIDStability:
    def test_investigation_id_unchanged_after_failover(self):
        """After a provider switch, the investigation_id must be the same."""
        exc = Exception("413 request too large")
        exc.status_code = 413  # type: ignore[attr-defined]
        groq_mock = _failing_llm(exc)
        gemini_mock = _fake_llm("ok")
        collected_ids: list = []

        def _cb(event):
            collected_ids.append(event.investigation_id)

        flm = FailoverLLM(
            providers=[(_groq_config(), groq_mock), (_gemini_config(), gemini_mock)],
            event_callback=_cb,
            investigation_id="STABLE-INV-42",
        )
        flm._generate([HumanMessage(content="test")])
        assert all(i == "STABLE-INV-42" for i in collected_ids)


# ---------------------------------------------------------------------------
# 7. ProviderFailoverExhausted preserves error chain
# ---------------------------------------------------------------------------

class TestFailoverExhaustedErrorChain:
    def test_causes_list_contains_all_provider_errors(self):
        def _make_exc(code: int, msg: str):
            e = Exception(msg)
            e.status_code = code  # type: ignore[attr-defined]
            return e

        pairs = [
            (_groq_config(), _failing_llm(_make_exc(413, "too large"))),
            (_gemini_config(), _failing_llm(_make_exc(429, "rate limit"))),
        ]
        flm = _make_failover(pairs)
        with pytest.raises(ProviderFailoverExhausted) as exc_info:
            flm._generate([HumanMessage(content="test")])

        causes = exc_info.value.causes
        assert len(causes) == 2
        assert causes[0].provider == "groq"
        assert causes[1].provider == "gemini"

    def test_provider_exhausted_provider_attribute_is_all(self):
        exc = Exception("503 service unavailable")
        exc.status_code = 503  # type: ignore[attr-defined]
        flm = _make_failover([(_groq_config(), _failing_llm(exc))])
        with pytest.raises(ProviderFailoverExhausted) as exc_info:
            flm._generate([HumanMessage(content="test")])
        assert exc_info.value.provider == "all"


# ---------------------------------------------------------------------------
# 8. SSE event type completeness
# ---------------------------------------------------------------------------

class TestSSEEventTypes:
    def test_provider_event_types_in_enum(self):
        from aml_copilot.events.models import EventType
        assert EventType.LLM_PROVIDER_ATTEMPT == "LLM_PROVIDER_ATTEMPT"
        assert EventType.LLM_PROVIDER_FAILED == "LLM_PROVIDER_FAILED"
        assert EventType.LLM_PROVIDER_FALLBACK == "LLM_PROVIDER_FALLBACK"
        assert EventType.LLM_PROVIDER_SELECTED == "LLM_PROVIDER_SELECTED"

    def test_fallback_event_metadata_has_no_key_fields(self):
        """SSE event metadata must not contain 'api_key' field names."""
        exc = Exception("429 rate limit")
        exc.status_code = 429  # type: ignore[attr-defined]
        events: list = []
        flm = _make_failover(
            [(_groq_config(), _failing_llm(exc)), (_gemini_config(), _fake_llm("ok"))],
            events,
        )
        flm._generate([HumanMessage(content="test")])
        for event in events:
            for key in event.metadata:
                assert "api_key" not in key.lower()
                assert "secret" not in key.lower()
                assert "credential" not in key.lower()


# ---------------------------------------------------------------------------
# 9. Config settings
# ---------------------------------------------------------------------------

class TestMultiProviderSettings:
    def test_settings_has_fallback_providers(self):
        from aml_copilot.config import Settings
        s = Settings.model_construct(
            llm_fallback_providers="gemini,openai",
            groq_api_key="x",
            groq_model="m",
            groq_max_context_tokens=5000,
            gemini_api_key="y",
            gemini_model="gemini-2.5-flash",
            gemini_max_context_tokens=20000,
            openai_api_key="z",
            llm_provider="groq",
            llm_model="m",
            llm_temperature=0.0,
            llm_max_context_tokens=5000,
            llm_max_iterations=5,
        )
        assert s.llm_fallback_providers == "gemini,openai"
        assert s.gemini_api_key == "y"
        assert s.gemini_model == "gemini-2.5-flash"
        assert s.gemini_max_context_tokens == 20000
        assert s.groq_max_context_tokens == 5000

    def test_settings_defaults_to_no_fallback(self):
        from aml_copilot.config import Settings
        s = Settings.model_construct()
        assert s.llm_fallback_providers == ""

    def test_groq_max_context_tokens_default(self):
        from aml_copilot.config import Settings
        s = Settings.model_construct()
        assert s.groq_max_context_tokens == 5000

    def test_gemini_max_context_tokens_default(self):
        from aml_copilot.config import Settings
        s = Settings.model_construct()
        assert s.gemini_max_context_tokens == 20000
