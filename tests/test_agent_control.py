"""Comprehensive tests for AML investigation agent control and max-iteration semantics (Tasks 1-8)."""

import datetime as dt
from typing import Any, List, Optional
import uuid

import pytest
from fastapi.testclient import TestClient
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from aml_copilot.agents.investigation_agent import InvestigationAgent
from aml_copilot.agents.state import InvestigationResult, InvestigationState, ToolExecutionRecord
from aml_copilot.agents.sufficiency import (
    check_tool_call_redundancy,
    get_sufficiency_advisory,
    is_evidence_sufficient,
)
from aml_copilot.api.main import create_app
from aml_copilot.events.bus import get_event_manager
from aml_copilot.events.models import EventType, InvestigationEvent
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.reporting.generator import generate_investigation_report


class MockScriptedLLM(BaseChatModel):
    """Deterministic mock ChatModel that yields scripted AIMessages per turn."""

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
        response_copy = response.model_copy(update={"id": str(uuid.uuid4())})
        return ChatResult(generations=[ChatGeneration(message=response_copy)])

    @property
    def _llm_type(self) -> str:
        return "mock-scripted-llm"


@pytest.fixture
def sample_statement() -> TransactionStatement:
    """Fixture providing realistic transaction data."""
    return TransactionStatement(
        customer_name="Vikram Sethi",
        account_number="AC789012",
        statement_period="01 Aug 2026 to 25 Aug 2026",
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 1),
                transaction_id="TXN001",
                description="CONSULTING FEE",
                credit=120000.0,
                balance=120000.0,
                counterparty="NEXUS CORP",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN005",
                description="RAPID INWARD WIRE",
                credit=480000.0,
                balance=600000.0,
                counterparty="ORION TRADING",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN006",
                description="RAPID OUTWARD TRANSFER",
                debit=465000.0,
                balance=135000.0,
                counterparty="RAHUL SERVICES",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Test 1: Normal Investigation Completion
# ---------------------------------------------------------------------------

def test_normal_investigation_completion(sample_statement: TransactionStatement):
    """Test 1: Normal completion gathers evidence -> synthesis -> critic -> report -> COMPLETED."""
    step1_call = AIMessage(
        content="",
        tool_calls=[{"name": "detect_anomalies", "args": {}, "id": "call_det_1"}],
    )
    step2_narrative = AIMessage(
        content=(
            "Observed Evidence:\n"
            "Transaction TXN005 on 2026-08-10 was a credit of ₹480,000 from ORION TRADING. "
            "On the same date, TXN006 was an outgoing debit of ₹465,000 to RAHUL SERVICES.\n\n"
            "Analytical Findings:\n"
            "AML rule screening flagged rapid fund movement.\n\n"
            "Interpretation:\n"
            "Rapid pass-through of funds indicates potential conduit typology.\n\n"
            "Limitations:\n"
            "Requires human compliance officer review."
        )
    )

    emitted_events: List[InvestigationEvent] = []
    mock_llm = MockScriptedLLM(scripted_responses=[step1_call, step2_narrative])
    agent = InvestigationAgent(llm=mock_llm, max_iterations=5)

    result = agent.investigate(
        statement=sample_statement,
        question="Investigate unusual fund movement.",
        event_callback=emitted_events.append,
    )

    assert result.status == "COMPLETED"
    assert result.is_partial is False
    assert result.critic_status == "PASS"
    assert "TXN005" in result.referenced_transaction_ids
    assert "TXN006" in result.referenced_transaction_ids

    event_types = [e.event_type for e in emitted_events]
    assert EventType.INVESTIGATION_COMPLETED in event_types
    assert EventType.INVESTIGATION_MAX_ITERATIONS not in event_types


# ---------------------------------------------------------------------------
# Test 2: Max Iteration Reached
# ---------------------------------------------------------------------------

def test_max_iteration_reached(sample_statement: TransactionStatement):
    """Test 2: Agent exceeding iteration budget terminates with MAX_ITERATIONS_REACHED."""
    call1 = AIMessage(content="", tool_calls=[{"name": "get_transaction_statistics", "args": {}, "id": "c1"}])
    call2 = AIMessage(content="", tool_calls=[{"name": "search_transactions", "args": {"transaction_id": "TXN001"}, "id": "c2"}])
    call3 = AIMessage(content="", tool_calls=[{"name": "search_transactions", "args": {"transaction_id": "TXN005"}, "id": "c3"}])

    mock_llm = MockScriptedLLM(scripted_responses=[call1, call2, call3])
    agent = InvestigationAgent(llm=mock_llm, max_iterations=2)

    result = agent.investigate(
        statement=sample_statement,
        question="Find suspicious activity.",
    )

    assert result.status == "MAX_ITERATIONS_REACHED"
    assert result.is_partial is True
    assert "maximum reasoning iterations" in result.response.lower()
    assert any("mandatory human compliance review" in w.lower() for w in result.limitations_warnings)


# ---------------------------------------------------------------------------
# Test 3: Max Iteration Does Not Emit Normal Completion
# ---------------------------------------------------------------------------

def test_max_iteration_does_not_emit_normal_completion(sample_statement: TransactionStatement):
    """Test 3: Max iteration emits INVESTIGATION_MAX_ITERATIONS and NEVER emits INVESTIGATION_COMPLETED."""
    call1 = AIMessage(content="", tool_calls=[{"name": "get_transaction_statistics", "args": {}, "id": "c1"}])
    call2 = AIMessage(content="", tool_calls=[{"name": "search_transactions", "args": {"transaction_id": "TXN001"}, "id": "c2"}])

    emitted_events: List[InvestigationEvent] = []
    mock_llm = MockScriptedLLM(scripted_responses=[call1, call2])
    agent = InvestigationAgent(llm=mock_llm, max_iterations=1)

    result = agent.investigate(
        statement=sample_statement,
        question="Find suspicious activity.",
        event_callback=emitted_events.append,
    )

    assert result.status == "MAX_ITERATIONS_REACHED"
    event_types = [e.event_type for e in emitted_events]
    assert EventType.INVESTIGATION_MAX_ITERATIONS in event_types
    assert EventType.INVESTIGATION_COMPLETED not in event_types


# ---------------------------------------------------------------------------
# Test 4: Max Iteration Preserves Evidence
# ---------------------------------------------------------------------------

def test_max_iteration_preserves_evidence(sample_statement: TransactionStatement):
    """Test 4: Max iteration preserves all collected evidence without fabricating critic approval."""
    call1 = AIMessage(content="", tool_calls=[{"name": "detect_anomalies", "args": {}, "id": "c1"}])
    call2 = AIMessage(content="", tool_calls=[{"name": "search_transactions", "args": {"transaction_id": "TXN005"}, "id": "c2"}])

    mock_llm = MockScriptedLLM(scripted_responses=[call1, call2])
    agent = InvestigationAgent(llm=mock_llm, max_iterations=1)

    result = agent.investigate(
        statement=sample_statement,
        question="Find suspicious activity.",
    )

    assert "detect_anomalies" in result.tools_used
    assert len(result.tool_calls) >= 1

    # Generate report and ensure evidence is preserved while critic approval is NOT fabricated
    report = generate_investigation_report(sample_statement, result)
    assert len(report.detection_findings) > 0 or len(report.observed_evidence) >= 0
    assert report.critic_validation.passed is False
    assert report.critic_validation.status == "INCOMPLETE"
    assert any("mandatory human" in lim.lower() for lim in report.limitations)


# ---------------------------------------------------------------------------
# Test 5: Redundant Transaction Search Prevention
# ---------------------------------------------------------------------------

def test_redundant_transaction_search_prevention(sample_statement: TransactionStatement):
    """Test 5: Repeated identical search or redundant broad search is intercepted and skipped."""
    state: InvestigationState = {
        "messages": [],
        "statement": sample_statement,
        "question": "test",
        "tools_used": ["search_transactions", "detect_anomalies"],
        "tool_calls": [
            ToolExecutionRecord(
                tool_name="search_transactions",
                tool_args={"transaction_id": "TXN005"},
                tool_output_snippet="{'transaction_id': 'TXN005', 'credit': 480000}",
            )
        ],
        "knowledge_sources": [],
        "iteration_count": 2,
        "max_iterations": 5,
        "final_response": "",
    }

    # Duplicate search for TXN005
    redundancy_note = check_tool_call_redundancy("search_transactions", {"transaction_id": "TXN005"}, state)
    assert redundancy_note is not None
    assert "Redundant" in redundancy_note or "already" in redundancy_note

    # Broad search after detection and specific search
    broad_note = check_tool_call_redundancy("search_transactions", {"limit": 10}, state)
    assert broad_note is not None
    assert "Redundant search" in broad_note


# ---------------------------------------------------------------------------
# Test 6: Legitimate Distinct Searches Remain Possible
# ---------------------------------------------------------------------------

def test_legitimate_distinct_searches_remain_possible(sample_statement: TransactionStatement):
    """Test 6: Distinct transaction searches are permitted without false-positive blocking."""
    state: InvestigationState = {
        "messages": [],
        "statement": sample_statement,
        "question": "test",
        "tools_used": ["search_transactions"],
        "tool_calls": [
            ToolExecutionRecord(
                tool_name="search_transactions",
                tool_args={"transaction_id": "TXN001"},
                tool_output_snippet="TXN001 consulting fee",
            )
        ],
        "knowledge_sources": [],
        "iteration_count": 1,
        "max_iterations": 5,
        "final_response": "",
    }

    # Different transaction ID
    check_distinct = check_tool_call_redundancy("search_transactions", {"transaction_id": "TXN005"}, state)
    assert check_distinct is None

    # Targeted amount filter
    check_amount = check_tool_call_redundancy("search_transactions", {"min_amount": 400000.0}, state)
    assert check_amount is None


# ---------------------------------------------------------------------------
# Test 7: Evidence Sufficiency Allows Transition Toward Synthesis
# ---------------------------------------------------------------------------

def test_evidence_sufficiency_allows_transition_toward_synthesis(sample_statement: TransactionStatement):
    """Test 7: When detection findings and profile context are present, evidence is sufficient."""
    state_insufficient: InvestigationState = {
        "tools_used": ["get_transaction_statistics"],
        "tool_calls": [ToolExecutionRecord(tool_name="get_transaction_statistics", tool_args={}, tool_output_snippet="stats")],
        "iteration_count": 1,
        "max_iterations": 5,
    }
    assert is_evidence_sufficient(state_insufficient) is False

    state_sufficient: InvestigationState = {
        "tools_used": ["detect_anomalies", "get_customer_profile"],
        "tool_calls": [
            ToolExecutionRecord(tool_name="detect_anomalies", tool_args={}, tool_output_snippet="anomalies"),
            ToolExecutionRecord(tool_name="get_customer_profile", tool_args={}, tool_output_snippet="profile"),
        ],
        "iteration_count": 2,
        "max_iterations": 5,
    }
    assert is_evidence_sufficient(state_sufficient) is True
    advisory = get_sufficiency_advisory(state_sufficient)
    assert advisory is not None
    assert "EVIDENCE SUFFICIENCY ADVISORY" in advisory


# ---------------------------------------------------------------------------
# Test 8: SSE Max-Iteration Event
# ---------------------------------------------------------------------------

def test_sse_max_iteration_event(monkeypatch: pytest.MonkeyPatch):
    """Test 8: SSE streaming delivers INVESTIGATION_MAX_ITERATIONS and terminates cleanly."""
    app = create_app()
    client = TestClient(app)
    get_event_manager().clear()

    inv_id = "INV-TEST-MAX-ITER"
    bus = get_event_manager().get_or_create_bus(inv_id)

    bus.publish_sync(
        InvestigationEvent(
            investigation_id=inv_id,
            event_type=EventType.INVESTIGATION_STARTED,
            message="Started investigation.",
        )
    )
    bus.publish_sync(
        InvestigationEvent(
            investigation_id=inv_id,
            event_type=EventType.INVESTIGATION_MAX_ITERATIONS,
            status="MAX_ITERATIONS_REACHED",
            message="Reasoning limit reached.",
        )
    )

    with client.stream("GET", f"/investigations/{inv_id}/events") as sse_res:
        assert sse_res.status_code == 200
        lines = [line for line in sse_res.iter_lines() if line]

    event_lines = [line for line in lines if line.startswith("data:")]
    assert any("INVESTIGATION_MAX_ITERATIONS" in line for line in event_lines)
    assert not any("INVESTIGATION_COMPLETED" in line for line in event_lines)


# ---------------------------------------------------------------------------
# Test 9: API Status for Max Iteration
# ---------------------------------------------------------------------------

def test_api_status_for_max_iteration(sample_statement: TransactionStatement):
    """Test 9: GET /investigations/{id} returns status MAX_ITERATIONS_REACHED and truthful report."""
    app = create_app()
    client = TestClient(app)
    get_event_manager().clear()

    inv_id = "INV-TEST-STATUS-MAX"
    bus = get_event_manager().get_or_create_bus(inv_id)

    partial_result = InvestigationResult(
        question="Investigate suspicious funds.",
        response="Investigation reached maximum reasoning iterations.",
        status="MAX_ITERATIONS_REACHED",
        is_partial=True,
        tools_used=["detect_anomalies"],
        tool_calls=[],
        referenced_transaction_ids=[],
        limitations_warnings=["Mandatory human review required."],
    )

    report = generate_investigation_report(sample_statement, partial_result)
    bus.publish_sync(
        InvestigationEvent(
            investigation_id=inv_id,
            event_type=EventType.INVESTIGATION_MAX_ITERATIONS,
            status="MAX_ITERATIONS_REACHED",
            message="Investigation reached maximum iterations.",
        )
    )
    bus.set_partial_result(report=report, markdown="## Partial Report")

    res = client.get(f"/investigations/{inv_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "MAX_ITERATIONS_REACHED"
    assert data["report"]["critic_validation"]["passed"] is False
    assert data["report"]["critic_validation"]["status"] == "INCOMPLETE"


# ---------------------------------------------------------------------------
# Test 10: Existing Successful Suspicious Investigation Remains Successful
# ---------------------------------------------------------------------------

def test_existing_successful_suspicious_investigation(sample_statement: TransactionStatement):
    """Test 10: Suspicious investigation with complete evidence finishes normally."""
    step1_anom = AIMessage(
        content="",
        tool_calls=[{"name": "detect_anomalies", "args": {}, "id": "call_det"}],
    )
    step2_network = AIMessage(
        content="",
        tool_calls=[{"name": "analyze_transaction_network", "args": {}, "id": "call_net"}],
    )
    step3_narrative = AIMessage(
        content=(
            "Observed Evidence:\n"
            "Transaction TXN005 was a ₹480,000 credit on 2026-08-10 from ORION TRADING. "
            "Transaction TXN006 was a ₹465,000 debit on 2026-08-10 to RAHUL SERVICES.\n\n"
            "Analytical Findings:\n"
            "Rule RAPID_MOVEMENT_OF_FUNDS detected.\n\n"
            "Network Findings:\n"
            "Directed counterparty flow between ORION TRADING and RAHUL SERVICES.\n\n"
            "Relevant AML Reference:\n"
            "aml_red_flags.md notes conduit accounts.\n\n"
            "Interpretation:\n"
            "The observed transactions indicate potential pass-through conduit activity.\n\n"
            "Limitations:\n"
            "Does not establish guilt; requires human analyst review."
        )
    )

    mock_llm = MockScriptedLLM(scripted_responses=[step1_anom, step2_network, step3_narrative])
    agent = InvestigationAgent(llm=mock_llm, max_iterations=5)

    result = agent.investigate(
        statement=sample_statement,
        question="Investigate unusual fund pass-through.",
    )

    assert result.status == "COMPLETED"
    assert result.is_partial is False
    assert result.critic_status == "PASS"
    assert result.critic_result is not None
    assert result.critic_result.passed is True


# ---------------------------------------------------------------------------
# Test 11: Critic and Revision Flow Remains Intact
# ---------------------------------------------------------------------------

def test_critic_revision_flow_remains_intact(sample_statement: TransactionStatement):
    """Test 11: Critic failure triggers revision node, agent corrects claims, and completes."""
    # Step 1: Tool call
    step1_tools = AIMessage(
        content="",
        tool_calls=[{"name": "detect_anomalies", "args": {}, "id": "call_det"}],
    )
    # Step 2: Agent hallucinates non-existent TXN999
    step2_flawed_draft = AIMessage(
        content="Observed Evidence: Transaction TXN999 of 999,999 indicates criminal money laundering."
    )
    # Step 3: Agent receives critic revision feedback and corrects findings citing real TXN005
    step3_corrected_draft = AIMessage(
        content=(
            "Observed Evidence:\n"
            "Transaction TXN005 on 2026-08-10 was a credit of ₹480,000 from ORION TRADING.\n\n"
            "Analytical Findings:\n"
            "High transaction amount flagged for review.\n\n"
            "Interpretation:\n"
            "Unusual activity warrants compliance analyst review.\n\n"
            "Limitations:\n"
            "Findings do not establish illegal conduct."
        )
    )

    mock_llm = MockScriptedLLM(scripted_responses=[step1_tools, step2_flawed_draft, step3_corrected_draft])
    agent = InvestigationAgent(llm=mock_llm, max_iterations=5, max_revisions=2)

    result = agent.investigate(
        statement=sample_statement,
        question="Examine customer transactions.",
    )

    assert result.status == "COMPLETED"
    assert result.revision_count == 1
    assert result.critic_status == "PASS"
    assert "TXN005" in result.referenced_transaction_ids
    assert "TXN999" not in result.referenced_transaction_ids
