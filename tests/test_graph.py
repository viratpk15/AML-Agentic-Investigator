"""Unit and integration tests for LangGraph investigation workflow (M10)."""

import datetime as dt
from pathlib import Path
from typing import Any, List, Optional
import uuid
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END
import pytest

from aml_copilot.agents.graph import (
    build_investigation_graph,
    create_agent_node,
    create_tool_node,
    should_continue,
)
from aml_copilot.agents.state import (
    InvestigationState,
    ToolExecutionRecord,
)
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.tools.tool_registry import ToolRegistry

STATEMENTS_DIR = Path("data/statements")


# ---------------------------------------------------------------------------
# Test Fixtures & Mock LLM
# ---------------------------------------------------------------------------

class DeterministicMockLLM(BaseChatModel):
    """Deterministic mock ChatModel for testing graph nodes and loops."""

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
        if self.call_count < len(self.scripted_responses):
            response = self.scripted_responses[self.call_count]
        else:
            response = AIMessage(content="Final summary after review.")
        self.call_count += 1

        # Assign unique ID to prevent LangGraph add_messages from overwriting identical references
        response_copy = response.model_copy(update={"id": str(uuid.uuid4())})
        return ChatResult(generations=[ChatGeneration(message=response_copy)])

    @property
    def _llm_type(self) -> str:
        return "deterministic-mock-llm"


@pytest.fixture
def sample_statement() -> TransactionStatement:
    """Fixture providing a sample statement with known transactions."""
    return TransactionStatement(
        customer_name="Arjun Mehta",
        account_number="AC123456",
        statement_period="01 Aug 2026 to 15 Aug 2026",
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 1),
                transaction_id="TXN001",
                description="SALARY CREDIT",
                credit=75000.0,
                balance=75000.0,
                counterparty="ACME TECH",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN005",
                description="LARGE CREDIT FROM ORION TRADING",
                credit=480000.0,
                balance=555000.0,
                counterparty="ORION TRADING",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# 1. State Tests
# ---------------------------------------------------------------------------

def test_investigation_state_representation(sample_statement: TransactionStatement):
    """Verify all required state fields can be represented cleanly."""
    record = ToolExecutionRecord(
        tool_name="search_transactions",
        tool_args={"min_amount": 100000.0},
        tool_output_snippet="{'total_matched': 1}",
    )
    state: InvestigationState = {
        "messages": [HumanMessage(content="Analyze transactions")],
        "statement": sample_statement,
        "question": "What is unusual?",
        "tools_used": ["search_transactions"],
        "tool_calls": [record],
        "iteration_count": 1,
        "max_iterations": 5,
        "final_response": "Preliminary review complete.",
    }

    assert len(state["messages"]) == 1
    assert state["statement"].customer_name == "Arjun Mehta"
    assert state["tools_used"] == ["search_transactions"]
    assert len(state["tool_calls"]) == 1
    assert state["iteration_count"] == 1
    assert state["max_iterations"] == 5
    assert state["final_response"] == "Preliminary review complete."


# ---------------------------------------------------------------------------
# 2. Agent Node Tests
# ---------------------------------------------------------------------------

def test_agent_node_execution(sample_statement: TransactionStatement):
    """Verify agent node invokes LLM, appends AIMessage, and increments iteration count."""
    expected_ai = AIMessage(content="Reviewing transactions.")
    mock_llm = DeterministicMockLLM(scripted_responses=[expected_ai])

    agent_fn = create_agent_node(mock_llm)

    initial_state: InvestigationState = {
        "messages": [HumanMessage(content="Hello")],
        "statement": sample_statement,
        "question": "Hello",
        "tools_used": [],
        "tool_calls": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "final_response": "",
    }

    update = agent_fn(initial_state)

    assert "messages" in update
    assert len(update["messages"]) == 1
    assert isinstance(update["messages"][0], AIMessage)
    assert update["messages"][0].content == "Reviewing transactions."
    assert update["iteration_count"] == 1
    assert update["final_response"] == "Reviewing transactions."


# ---------------------------------------------------------------------------
# 3. Tool Node Tests
# ---------------------------------------------------------------------------

def test_tool_node_execution(sample_statement: TransactionStatement):
    """Verify tool node inspects AIMessage tool_calls and emits ToolMessage with records."""
    registry = ToolRegistry.from_statement(sample_statement)
    tools = registry.get_tools()
    tools_by_name = {t.name: t for t in tools}

    tool_fn = create_tool_node(tools_by_name)

    ai_with_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_transaction_statistics",
                "args": {},
                "id": "call_stat_1",
            }
        ],
    )

    state: InvestigationState = {
        "messages": [HumanMessage(content="stats"), ai_with_call],
        "statement": sample_statement,
        "question": "stats",
        "tools_used": [],
        "tool_calls": [],
        "iteration_count": 1,
        "max_iterations": 3,
        "final_response": "",
    }

    update = tool_fn(state)

    assert "messages" in update
    assert len(update["messages"]) == 1
    tool_msg = update["messages"][0]
    assert isinstance(tool_msg, ToolMessage)
    assert tool_msg.tool_call_id == "call_stat_1"
    assert "transaction_count" in tool_msg.content

    assert update["tools_used"] == ["get_transaction_statistics"]
    assert len(update["tool_calls"]) == 1
    assert update["tool_calls"][0].tool_name == "get_transaction_statistics"


# ---------------------------------------------------------------------------
# 4. Conditional Routing Tests
# ---------------------------------------------------------------------------

def test_should_continue_routing(sample_statement: TransactionStatement):
    """Verify routing decisions based on tool_calls and iteration limit."""
    # Case 1: AI message with tool calls -> "tools"
    ai_with_tools = AIMessage(
        content="",
        tool_calls=[{"name": "search_transactions", "args": {}, "id": "call_1"}],
    )
    state_with_tools: InvestigationState = {
        "messages": [ai_with_tools],
        "statement": sample_statement,
        "question": "q",
        "tools_used": [],
        "tool_calls": [],
        "iteration_count": 1,
        "max_iterations": 3,
        "final_response": "",
    }
    assert should_continue(state_with_tools) == "tools"

    # Case 2: AI message without tool calls -> END
    ai_no_tools = AIMessage(content="Final summary.")
    state_no_tools: InvestigationState = {
        "messages": [ai_no_tools],
        "statement": sample_statement,
        "question": "q",
        "tools_used": [],
        "tool_calls": [],
        "iteration_count": 1,
        "max_iterations": 3,
        "final_response": "Final summary.",
    }
    assert should_continue(state_no_tools) == END

    # Case 3: Iteration limit exceeded -> END
    state_exceeded: InvestigationState = {
        "messages": [ai_with_tools],
        "statement": sample_statement,
        "question": "q",
        "tools_used": [],
        "tool_calls": [],
        "iteration_count": 4,  # > max_iterations of 3
        "max_iterations": 3,
        "final_response": "",
    }
    assert should_continue(state_exceeded) == END


# ---------------------------------------------------------------------------
# 5. Full Compiled Graph Tests
# ---------------------------------------------------------------------------

def test_compiled_graph_agent_to_end(sample_statement: TransactionStatement):
    """Verify graph path: START -> Agent -> END (direct answer without tools)."""
    direct_answer = AIMessage(content="No tool calls needed for this policy question.")
    mock_llm = DeterministicMockLLM(scripted_responses=[direct_answer])

    graph = build_investigation_graph(mock_llm, sample_statement)

    initial_state: InvestigationState = {
        "messages": [HumanMessage(content="What is AML?")],
        "statement": sample_statement,
        "question": "What is AML?",
        "tools_used": [],
        "tool_calls": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "final_response": "",
    }

    final_state = graph.invoke(initial_state)

    assert final_state["tools_used"] == []
    assert len(final_state["tool_calls"]) == 0
    assert final_state["final_response"] == "No tool calls needed for this policy question."
    assert mock_llm.call_count == 1


def test_compiled_graph_agent_tool_agent_end(sample_statement: TransactionStatement):
    """Verify graph path: START -> Agent -> Tool -> Agent -> END."""
    # Step 1: Agent calls get_transaction_statistics
    step1_ai = AIMessage(
        content="",
        tool_calls=[{"name": "get_transaction_statistics", "args": {}, "id": "call_1"}],
    )
    # Step 2: Agent synthesizes final answer after receiving tool output
    step2_ai = AIMessage(
        content="Customer has 2 transactions with total credit volume of 555,000."
    )

    mock_llm = DeterministicMockLLM(scripted_responses=[step1_ai, step2_ai])
    graph = build_investigation_graph(mock_llm, sample_statement)

    initial_state: InvestigationState = {
        "messages": [HumanMessage(content="Summarize volume.")],
        "statement": sample_statement,
        "question": "Summarize volume.",
        "tools_used": [],
        "tool_calls": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "final_response": "",
    }

    final_state = graph.invoke(initial_state)

    assert final_state["tools_used"] == ["get_transaction_statistics"]
    assert len(final_state["tool_calls"]) == 1
    assert "total credit volume of 555,000" in final_state["final_response"]
    assert mock_llm.call_count == 2
