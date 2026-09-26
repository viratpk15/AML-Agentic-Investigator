"""Unit and mock tests for the First Single Tool-Using AML Investigation Agent."""

import datetime as dt
from pathlib import Path
from typing import Any, List, Optional
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
import pytest

from unittest.mock import MagicMock, patch

from aml_copilot.agents.investigation_agent import (
    InvestigationAgent,
    InvestigationResult,
    run_investigation,
)
from aml_copilot.config import Settings
from aml_copilot.exceptions import AgentConfigurationError
from aml_copilot.models.transaction import Transaction, TransactionStatement

STATEMENTS_DIR = Path("data/statements")


# ---------------------------------------------------------------------------
# Deterministic Mock Chat Model for Testing Tool Loops
# ---------------------------------------------------------------------------

class MockInvestigativeLLM(BaseChatModel):
    """Deterministic mock ChatModel to simulate the agent tool-calling loop without network/API."""

    scripted_responses: List[AIMessage]
    call_count: int = 0
    bound_tools: List[Any] = []

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        self.bound_tools = list(tools)
        return self

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        import uuid

        if self.call_count < len(self.scripted_responses):
            response = self.scripted_responses[self.call_count]
        else:
            response = AIMessage(content="Final summary after review.")
        self.call_count += 1

        # Ensure each generated message has a distinct ID for LangGraph add_messages reducer
        response_copy = response.model_copy(update={"id": str(uuid.uuid4())})
        return ChatResult(generations=[ChatGeneration(message=response_copy)])

    @property
    def _llm_type(self) -> str:
        return "mock-investigative-llm"


@pytest.fixture
def mock_statement() -> TransactionStatement:
    """Fixture providing a mock statement with realistic transactions."""
    return TransactionStatement(
        customer_name="Arjun Mehta",
        account_number="AC987654",
        statement_period="01 Aug 2026 to 20 Aug 2026",
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 1),
                transaction_id="TXN001",
                description="SALARY",
                credit=75000.0,
                balance=75000.0,
                counterparty="ACME TECH",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN005",
                description="LARGE INFLOW FROM ORION TRADING",
                credit=480000.0,
                balance=555000.0,
                counterparty="ORION TRADING",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN006",
                description="OUTGOING TRANSFER TO RAHUL SERVICES",
                debit=465000.0,
                balance=90000.0,
                counterparty="RAHUL SERVICES",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Configuration and Error Handling Tests
# ---------------------------------------------------------------------------

def test_agent_missing_api_key_raises_configuration_error(monkeypatch: pytest.MonkeyPatch):
    """Verify clean AgentConfigurationError is raised when OPENAI_API_KEY is missing."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "aml_copilot.agents.investigation_agent.get_settings",
        lambda: Settings(llm_provider="openai", openai_api_key=None, llm_fallback_providers="", _env_file=None),
    )

    with pytest.raises(AgentConfigurationError) as exc_info:
        InvestigationAgent()

    # FailoverLLM logs the root cause and raises with 'No LLM providers could be initialised'
    assert "No LLM providers could be initialised" in str(exc_info.value) or "OpenAI API key not configured" in str(exc_info.value)


def test_agent_missing_groq_api_key_raises_configuration_error(monkeypatch: pytest.MonkeyPatch):
    """Verify clean AgentConfigurationError is raised when GROQ_API_KEY is missing."""
    monkeypatch.setattr(
        "aml_copilot.agents.investigation_agent.get_settings",
        lambda: Settings(llm_provider="groq", groq_api_key=None, llm_fallback_providers="", _env_file=None),
    )

    with pytest.raises(AgentConfigurationError) as exc_info:
        InvestigationAgent()

    # FailoverLLM logs the root cause and raises with 'No LLM providers could be initialised'
    assert "No LLM providers could be initialised" in str(exc_info.value) or "Groq API key not configured" in str(exc_info.value)


def test_agent_unsupported_provider_raises_configuration_error(monkeypatch: pytest.MonkeyPatch):
    """Verify clean AgentConfigurationError is raised for unsupported LLM providers."""
    monkeypatch.setattr(
        "aml_copilot.agents.investigation_agent.get_settings",
        lambda: Settings(llm_provider="anthropic", llm_fallback_providers="", _env_file=None),
    )

    with pytest.raises(AgentConfigurationError) as exc_info:
        InvestigationAgent()

    # FailoverLLM wraps the factory error
    assert "anthropic" in str(exc_info.value)
    assert "Supported" in str(exc_info.value)


def test_agent_openai_provider_initialization(monkeypatch: pytest.MonkeyPatch):
    """Verify OpenAI provider initialises ChatOpenAI and agent.llm is a FailoverLLM wrapping it."""
    from aml_copilot.llm.failover import FailoverLLM
    monkeypatch.setattr(
        "aml_copilot.agents.investigation_agent.get_settings",
        lambda: Settings(
            llm_provider="openai",
            openai_api_key="mock-openai-key",
            llm_model="gpt-4o-mini",
            llm_temperature=0.2,
            llm_fallback_providers="",
            _env_file=None,
        ),
    )

    mock_chat = MagicMock(spec=BaseChatModel)
    with patch("langchain_openai.ChatOpenAI", return_value=mock_chat):
        agent = InvestigationAgent()
        # Agent now wraps providers in FailoverLLM
        assert isinstance(agent.llm, FailoverLLM)
        assert agent.llm.providers[0][0].name == "openai"


def test_agent_groq_provider_initialization(monkeypatch: pytest.MonkeyPatch):
    """Verify Groq provider initialises ChatGroq and agent.llm is a FailoverLLM wrapping it."""
    from aml_copilot.llm.failover import FailoverLLM
    monkeypatch.setattr(
        "aml_copilot.agents.investigation_agent.get_settings",
        lambda: Settings(
            llm_provider="groq",
            groq_api_key="mock-groq-key",
            groq_model="llama-3.3-70b-versatile",
            llm_temperature=0.0,
            llm_fallback_providers="",
            _env_file=None,
        ),
    )

    mock_chat = MagicMock(spec=BaseChatModel)
    with patch("langchain_groq.ChatGroq", return_value=mock_chat):
        agent = InvestigationAgent()
        assert isinstance(agent.llm, FailoverLLM)
        assert agent.llm.providers[0][0].name == "groq"


def test_agent_explicit_llm_injection_bypasses_provider_config(monkeypatch: pytest.MonkeyPatch):
    """Verify explicit LLM injection bypasses settings and API key checks completely."""
    monkeypatch.setattr(
        "aml_copilot.agents.investigation_agent.get_settings",
        lambda: Settings(
            llm_provider="invalid_provider",
            openai_api_key=None,
            groq_api_key=None,
            _env_file=None,
        ),
    )

    explicit_mock = MockInvestigativeLLM(scripted_responses=[])
    agent = InvestigationAgent(llm=explicit_mock)
    assert agent.llm == explicit_mock


def test_agent_accepts_explicit_settings():
    """Verify InvestigationAgent respects explicitly injected Settings instance."""
    from aml_copilot.llm.failover import FailoverLLM
    custom_settings = Settings(
        llm_provider="groq",
        groq_api_key="custom-groq-key",
        groq_model="llama-3.1-8b-instant",
        llm_temperature=0.1,
        llm_fallback_providers="",
        _env_file=None,
    )
    mock_chat = MagicMock(spec=BaseChatModel)
    with patch("langchain_groq.ChatGroq", return_value=mock_chat):
        agent = InvestigationAgent(settings=custom_settings)
        # llm is a FailoverLLM wrapping the mock
        assert isinstance(agent.llm, FailoverLLM)
        assert agent.llm.providers[0][0].name == "groq"


# ---------------------------------------------------------------------------
# Tool-Calling Loop Integration with Mock LLM
# ---------------------------------------------------------------------------

def test_investigation_agent_tool_calling_loop(mock_statement: TransactionStatement):
    """Verify end-to-end agent loop: question -> tool call -> tool result -> final response."""
    # Step 1: LLM decides to call `detect_anomalies`
    step1_tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "detect_anomalies",
                "args": {"include_rule_signals": True},
                "id": "call_123",
            }
        ],
    )
    # Step 2: After seeing the tool result, LLM delivers final compliance findings
    step2_final_text = AIMessage(
        content=(
            "Based on the detection tools, transaction TXN005 (480,000 credit) was immediately followed "
            "by TXN006 (465,000 debit) on the same day. This rapid pass-through of funds represents "
            "an unusual activity and an investigation signal requiring senior compliance review."
        )
    )

    mock_llm = MockInvestigativeLLM(scripted_responses=[step1_tool_call, step2_final_text])
    agent = InvestigationAgent(llm=mock_llm)

    result = agent.investigate(
        statement=mock_statement,
        question="What transactions should an investigator review first?",
    )

    assert isinstance(result, InvestigationResult)
    assert result.question == "What transactions should an investigator review first?"
    assert "TXN005" in result.response
    assert "TXN006" in result.response

    # Verify tools used and audit records
    assert result.tools_used == ["detect_anomalies"]
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "detect_anomalies"
    assert "TXN005" in result.tool_calls[0].tool_output_snippet

    # Verify transaction IDs verified and referenced
    assert "TXN005" in result.referenced_transaction_ids
    assert "TXN006" in result.referenced_transaction_ids

    # Verify disclaimers
    assert any("compliance review" in w.lower() or "not establish" in w.lower() for w in result.limitations_warnings)


def test_investigation_agent_search_tool_call(mock_statement: TransactionStatement):
    """Verify agent can call search_transactions tool and filter by amount."""
    step1_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_transactions",
                "args": {"min_amount": 400000.0},
                "id": "call_search_1",
            }
        ],
    )
    step2_response = AIMessage(
        content="Identified 2 large transactions over 400,000: TXN005 and TXN006."
    )

    mock_llm = MockInvestigativeLLM(scripted_responses=[step1_call, step2_response])
    agent = InvestigationAgent(llm=mock_llm)

    result = agent.investigate(
        statement=mock_statement,
        question="Find transactions above 400,000.",
    )

    assert result.tools_used == ["search_transactions"]
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "search_transactions"
    assert "TXN005" in result.referenced_transaction_ids


def test_investigation_agent_direct_response_without_tools(mock_statement: TransactionStatement):
    """Verify agent can answer general queries without invoking tools if none needed."""
    direct_msg = AIMessage(
        content="An AML investigation typically assesses velocity, counterparties, and fund pass-through."
    )
    mock_llm = MockInvestigativeLLM(scripted_responses=[direct_msg])
    agent = InvestigationAgent(llm=mock_llm)

    result = agent.investigate(
        statement=mock_statement,
        question="What factors do you typically examine?",
    )

    assert result.tools_used == []
    assert len(result.tool_calls) == 0
    assert "velocity" in result.response


def test_run_investigation_convenience_helper(mock_statement: TransactionStatement):
    """Verify run_investigation helper function."""
    direct_msg = AIMessage(content="Reviewed statement.")
    mock_llm = MockInvestigativeLLM(scripted_responses=[direct_msg])

    result = run_investigation(
        statement=mock_statement,
        question="Review this statement.",
        llm=mock_llm,
    )

    assert isinstance(result, InvestigationResult)
    assert result.response == "Reviewed statement."


def test_investigation_agent_multi_step_tool_loop(mock_statement: TransactionStatement):
    """Verify agent can execute multiple tool calls in sequence across reasoning iterations."""
    # Step 1: Agent calls get_transaction_statistics
    step1_call = AIMessage(
        content="",
        tool_calls=[{"name": "get_transaction_statistics", "args": {}, "id": "call_1"}],
    )
    # Step 2: Agent analyzes statistics and calls search_transactions for large credits
    step2_call = AIMessage(
        content="Transaction volume is elevated. Querying credits over 100,000.",
        tool_calls=[
            {
                "name": "search_transactions",
                "args": {"transaction_type": "credit", "min_amount": 100000.0},
                "id": "call_2",
            }
        ],
    )
    # Step 3: Agent synthesizes final findings
    step3_final = AIMessage(
        content="Identified major credit TXN005 of 480,000 from ORION TRADING requiring review."
    )

    mock_llm = MockInvestigativeLLM(scripted_responses=[step1_call, step2_call, step3_final])
    agent = InvestigationAgent(llm=mock_llm)

    result = agent.investigate(
        statement=mock_statement,
        question="Analyze the customer's transaction structure.",
    )

    assert result.tools_used == ["get_transaction_statistics", "search_transactions"]
    assert len(result.tool_calls) == 2
    assert "TXN005" in result.response
    assert "TXN005" in result.referenced_transaction_ids


def test_investigation_agent_hits_max_iterations(mock_statement: TransactionStatement):
    """Verify agent terminates gracefully when exceeding max_iterations."""
    # Continuous loop of tool calls with distinct tool call IDs
    inf_call1 = AIMessage(
        content="",
        tool_calls=[{"name": "get_transaction_statistics", "args": {}, "id": "call_inf_1"}],
    )
    inf_call2 = AIMessage(
        content="",
        tool_calls=[{"name": "get_transaction_statistics", "args": {}, "id": "call_inf_2"}],
    )
    inf_call3 = AIMessage(
        content="",
        tool_calls=[{"name": "get_transaction_statistics", "args": {}, "id": "call_inf_3"}],
    )
    mock_llm = MockInvestigativeLLM(scripted_responses=[inf_call1, inf_call2, inf_call3])
    agent = InvestigationAgent(llm=mock_llm, max_iterations=2)

    result = agent.investigate(
        statement=mock_statement,
        question="Continuous loop test.",
    )

    assert len(result.tool_calls) == 2
    assert "maximum reasoning iterations" in result.response.lower()
