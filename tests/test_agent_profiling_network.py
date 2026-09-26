"""Unit tests for LangGraph agent integration with profiling and network tools."""

import datetime as dt
from typing import Any, List, Optional
import uuid

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from aml_copilot.agents.investigation_agent import InvestigationAgent, run_investigation
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.rag.service import RAGService
from aml_copilot.tools.tool_registry import ToolRegistry


def _sample_statement() -> TransactionStatement:
    return TransactionStatement(
        customer_name="Pinnacle Enterprises",
        account_number="ACC-7711",
        statement_period="2026-08-01 to 2026-08-31",
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN005",
                description="ORION TRADING CREDIT",
                credit=480000.0,
                debit=None,
                balance=480000.0,
                counterparty="ORION TRADING",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN006",
                description="RAHUL SERVICES DEBIT",
                credit=None,
                debit=475000.0,
                balance=5000.0,
                counterparty="RAHUL SERVICES",
            ),
            Transaction(
                date=dt.date(2026, 8, 15),
                transaction_id="TXN007",
                description="ACME TECH CREDIT",
                credit=50000.0,
                debit=None,
                balance=55000.0,
                counterparty="ACME TECH",
            ),
        ],
    )


class ScriptedChatModel(BaseChatModel):
    """Deterministic mock LLM yielding a predefined sequence of AIMessages."""

    responses: List[AIMessage]
    call_count: int = 0

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        return self

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
        else:
            resp = AIMessage(content="Final synthesized conclusion.", id=str(uuid.uuid4()))
        self.call_count += 1
        return ChatResult(generations=[ChatGeneration(message=resp)])

    @property
    def _llm_type(self) -> str:
        return "scripted-profiling-network-llm"


def test_tool_registry_exposes_all_seven_tools():
    """Verify ToolRegistry exposes all 7 investigation tools when configured."""
    stmt = _sample_statement()
    rag_service = RAGService(knowledge_dir="data/knowledge")

    registry = ToolRegistry.from_statement(
        stmt,
        include_all=True,
        rag_service=rag_service,
    )

    expected_tools = {
        "analyze_transactions",
        "get_transaction_statistics",
        "search_transactions",
        "detect_anomalies",
        "search_aml_knowledge",
        "get_customer_profile",
        "analyze_transaction_network",
    }
    assert set(registry.tool_names) == expected_tools
    assert len(registry.get_tools()) == 7


def test_agent_routes_to_profile_tool():
    """Verify LangGraph workflow: Agent -> get_customer_profile -> Agent -> END."""
    stmt = _sample_statement()
    call_id = str(uuid.uuid4())

    mock_llm = ScriptedChatModel(
        responses=[
            # Step 1: Agent decides to request customer profile
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_customer_profile",
                        "args": {"include_indicators": True},
                        "id": call_id,
                    }
                ],
                id=str(uuid.uuid4()),
            ),
            # Step 2: Agent synthesizes the profile findings
            AIMessage(
                content=(
                    "Customer Profile Summary:\n"
                    "Pinnacle Enterprises recorded 3 transactions with net turnover of ₹1,005,000.\n"
                    "Peak transactions include TXN005 (credit ₹480,000) and TXN006 (debit ₹475,000).\n"
                    "Limitation: Historical baseline is limited to 3 transactions."
                ),
                id=str(uuid.uuid4()),
            ),
        ]
    )

    agent = InvestigationAgent(
        llm=mock_llm,
        include_profile=True,
        include_network=True,
    )
    result = agent.investigate(
        statement=stmt,
        question="What does this customer's overall transaction profile look like?",
    )

    assert "get_customer_profile" in result.tools_used
    assert result.customer_profile is not None
    assert result.customer_profile["total_transactions"] == 3
    assert result.customer_profile["customer_name"] == "Pinnacle Enterprises"
    assert "TXN005" in result.referenced_transaction_ids
    assert "TXN006" in result.referenced_transaction_ids


def test_agent_routes_to_network_tool():
    """Verify LangGraph workflow: Agent -> analyze_transaction_network -> Agent -> END."""
    stmt = _sample_statement()
    call_id = str(uuid.uuid4())

    mock_llm = ScriptedChatModel(
        responses=[
            # Step 1: Agent decides to inspect network relationships
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "analyze_transaction_network",
                        "args": {"include_patterns": True},
                        "id": call_id,
                    }
                ],
                id=str(uuid.uuid4()),
            ),
            # Step 2: Agent synthesizes network topology
            AIMessage(
                content=(
                    "Network Analysis Findings:\n"
                    "Customer interacts with 3 counterparties (ORION TRADING, RAHUL SERVICES, ACME TECH).\n"
                    "ORION TRADING is the primary incoming entity (TXN005, ₹480,000).\n"
                    "Funds were transferred out to RAHUL SERVICES (TXN006, ₹475,000)."
                ),
                id=str(uuid.uuid4()),
            ),
        ]
    )

    agent = InvestigationAgent(
        llm=mock_llm,
        include_profile=True,
        include_network=True,
    )
    result = agent.investigate(
        statement=stmt,
        question="Analyze the relationship network between the customer and counterparties.",
    )

    assert "analyze_transaction_network" in result.tools_used
    assert result.network_analysis is not None
    assert len(result.network_analysis["nodes"]) == 4  # Customer + 3 counterparties
    assert result.network_analysis["metrics"]["customer_degree"] == 3


def test_agent_multi_tool_reasoning_profile_network_rag():
    """Verify LangGraph workflow executing Profile -> Network -> RAG in a coherent multi-step loop."""
    stmt = _sample_statement()
    rag_service = RAGService(knowledge_dir="data/knowledge")

    call1_id = str(uuid.uuid4())
    call2_id = str(uuid.uuid4())
    call3_id = str(uuid.uuid4())

    mock_llm = ScriptedChatModel(
        responses=[
            # Turn 1: Agent checks behavioral profile
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_customer_profile",
                        "args": {"include_indicators": True},
                        "id": call1_id,
                    }
                ],
                id=str(uuid.uuid4()),
            ),
            # Turn 2: Agent analyzes counterparty network
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "analyze_transaction_network",
                        "args": {"include_patterns": True},
                        "id": call2_id,
                    }
                ],
                id=str(uuid.uuid4()),
            ),
            # Turn 3: Agent searches AML reference knowledge
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_aml_knowledge",
                        "args": {"query": "rapid movement of funds conduit accounts", "limit": 1},
                        "id": call3_id,
                    }
                ],
                id=str(uuid.uuid4()),
            ),
            # Turn 4: Final grounded synthesis
            AIMessage(
                content=(
                    "Observed Evidence:\n"
                    "Customer profile indicates high turnover with rapid fund movement.\n"
                    "Network analysis shows funds received from ORION TRADING via TXN005 (₹480,000) "
                    "were transferred to RAHUL SERVICES via TXN006 (₹475,000).\n\n"
                    "Relevant AML Reference:\n"
                    "The knowledge base defines rapid movement of funds in conduit accounts.\n\n"
                    "Interpretation:\n"
                    "The flow matches the conduit account typology.\n\n"
                    "Limitation:\n"
                    "This observation does not establish criminal intent or guilt."
                ),
                id=str(uuid.uuid4()),
            ),
        ]
    )

    result = run_investigation(
        statement=stmt,
        question="Provide a comprehensive investigation covering customer profile, network relations, and AML guidance.",
        llm=mock_llm,
        rag_service=rag_service,
        include_rag=True,
        include_profile=True,
        include_network=True,
    )

    assert "get_customer_profile" in result.tools_used
    assert "analyze_transaction_network" in result.tools_used
    assert "search_aml_knowledge" in result.tools_used
    assert len(result.tool_calls) == 3
    assert result.customer_profile is not None
    assert result.network_analysis is not None
    assert len(result.knowledge_sources) > 0
    assert "TXN005" in result.referenced_transaction_ids
    assert "TXN006" in result.referenced_transaction_ids
