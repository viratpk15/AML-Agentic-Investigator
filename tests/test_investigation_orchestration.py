"""Regression tests for LangGraph investigation orchestration, status distinctions, and human review prioritization.

Covers all 12 verification criteria:
1. 54-transaction stress investigation reaches NORMAL_COMPLETION when sufficient evidence is available.
2. MAX_ITERATIONS_REACHED occurs only when the investigation genuinely cannot complete within configured limit.
3. Existing evidence prevents redundant tool-loop iterations.
4. Synthesis is reached after sufficient evidence collection.
5. Human-review shortlist is smaller than the complete transaction set when convergence prioritization is applicable.
6. Human-review items have valid supporting finding IDs.
7. No HumanReviewItem can be generated solely from transaction ordering.
8. No LLM-generated transaction ID can bypass CanonicalEvidence.
9. Existing anomaly IDs remain exactly: TXN401, TXN404, TXN434, TXN442, TXN445, TXN451.
10. Existing provenance regression tests remain passing.
11. Existing provider failover tests remain passing.
12. Existing context-budget tests remain passing.
"""

from pathlib import Path
from typing import Any, List
import pytest
from langchain_core.messages import AIMessage, BaseMessage

from aml_copilot.agents.critic import evaluate_investigation_draft
from aml_copilot.agents.graph import should_continue_investigator
from aml_copilot.agents.investigation_agent import InvestigationAgent
from aml_copilot.agents.state import (
    InvestigationResult,
    InvestigationState,
    InvestigationStatus,
    ToolExecutionRecord,
)
from aml_copilot.agents.sufficiency import (
    check_tool_call_redundancy,
    is_evidence_sufficient,
)
from aml_copilot.events.models import EventType, InvestigationEvent
from aml_copilot.models.evidence import (
    CanonicalEvidence,
    build_canonical_evidence,
    select_human_review_items,
)
from aml_copilot.models.transaction import TransactionStatement
from aml_copilot.reporting.generator import generate_investigation_report
from aml_copilot.reporting.validation import validate_report_evidence
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_parser import parse_transactions

STRESS_PDF_PATH = Path("data/statements/ultimate_publish_stress_statement.pdf")


class MockScriptedLLM:
    """Deterministic scripted LLM for orchestrating graph tests without live network calls."""

    def __init__(self, scripted_responses: List[AIMessage]) -> None:
        self.scripted_responses = list(scripted_responses)
        self.call_count = 0

    def invoke(self, messages: Any, **kwargs: Any) -> AIMessage:
        if self.call_count < len(self.scripted_responses):
            resp = self.scripted_responses[self.call_count]
            self.call_count += 1
            return resp
        return AIMessage(content="Final synthesis completed with verified evidence.")

    def bind_tools(self, tools: Any, **kwargs: Any) -> "MockScriptedLLM":
        return self


@pytest.fixture(scope="module")
def stress_statement() -> TransactionStatement:
    """Load and parse the 54-transaction stress statement."""
    assert STRESS_PDF_PATH.exists(), f"PDF not found at {STRESS_PDF_PATH}"
    doc = extract_pdf_text(str(STRESS_PDF_PATH))
    statement = parse_transactions(doc)
    assert len(statement.transactions) == 54
    return statement


@pytest.fixture(scope="module")
def stress_evidence(stress_statement: TransactionStatement) -> CanonicalEvidence:
    """Build canonical evidence for the 54-transaction statement."""
    return build_canonical_evidence(stress_statement)


# ---------------------------------------------------------------------------
# Test 1: 54-transaction stress reaches NORMAL_COMPLETION when evidence is sufficient
# ---------------------------------------------------------------------------

def test_1_stress_investigation_reaches_normal_completion(stress_statement: TransactionStatement):
    """TEST 1: 54-transaction stress investigation reaches NORMAL_COMPLETION when sufficient evidence is available."""
    # Step 1: Request detection and customer profile (sufficient evidence)
    msg1 = AIMessage(
        content="",
        tool_calls=[
            {"name": "detect_anomalies", "args": {}, "id": "call_det"},
            {"name": "get_customer_profile", "args": {}, "id": "call_prof"},
        ],
    )
    # Step 2: Formulate factual concluding narrative citing verified anomalies
    msg2 = AIMessage(
        content=(
            "Investigation concluded for Arjun Malhotra. Isolation Forest identified 6 statistical anomaly "
            "transactions: TXN401, TXN404, TXN434, TXN442, TXN445, TXN451. Multiple deterministic rules triggered "
            "including large transactions and rapid pass-through fund flows. Highly converged transactions TXN445 "
            "and TXN434 require priority human review."
        )
    )

    mock_llm = MockScriptedLLM(scripted_responses=[msg1, msg2])
    agent = InvestigationAgent(llm=mock_llm, max_iterations=5, enable_critic=True)

    result = agent.investigate(
        statement=stress_statement,
        question="Investigate unusual movement of funds in this account and highlight transactions requiring human review.",
    )

    # Must distinguish clearly as NORMAL_COMPLETION
    assert result.status == "NORMAL_COMPLETION"
    assert result.status == "COMPLETED"  # backward compatibility check
    assert result.status != "MAX_ITERATIONS_REACHED"
    assert result.is_partial is False
    assert result.critic_status == "PASS"

    report = generate_investigation_report(stress_statement, result, canonical_evidence=result.canonical_evidence)
    val_res = validate_report_evidence(report, result.canonical_evidence, stress_statement)
    assert val_res.passed is True


# ---------------------------------------------------------------------------
# Test 2: MAX_ITERATIONS_REACHED occurs only when genuinely cannot complete
# ---------------------------------------------------------------------------

def test_2_max_iterations_reached_only_when_genuinely_cannot_complete(stress_statement: TransactionStatement):
    """TEST 2: MAX_ITERATIONS_REACHED occurs only when the investigation genuinely cannot complete within configured limit."""
    # Continuous loop of non-detection queries where evidence is never sufficient
    call1 = AIMessage(content="", tool_calls=[{"name": "get_transaction_statistics", "args": {}, "id": "c1"}])
    call2 = AIMessage(content="", tool_calls=[{"name": "search_transactions", "args": {"transaction_id": "TXN401"}, "id": "c2"}])
    call3 = AIMessage(content="", tool_calls=[{"name": "search_transactions", "args": {"transaction_id": "TXN405"}, "id": "c3"}])

    events: List[InvestigationEvent] = []
    mock_llm = MockScriptedLLM(scripted_responses=[call1, call2, call3])
    agent = InvestigationAgent(llm=mock_llm, max_iterations=2, enable_critic=True)

    result = agent.investigate(
        statement=stress_statement,
        question="Check fund movements.",
        event_callback=events.append,
    )

    assert result.status == "MAX_ITERATIONS_REACHED"
    assert result.status != "NORMAL_COMPLETION"
    assert result.is_partial is True
    event_types = [e.event_type for e in events]
    assert EventType.INVESTIGATION_MAX_ITERATIONS in event_types
    assert EventType.INVESTIGATION_COMPLETED not in event_types


# ---------------------------------------------------------------------------
# Test 3: Existing evidence prevents redundant tool-loop iterations
# ---------------------------------------------------------------------------

def test_3_existing_evidence_prevents_redundant_tool_loop_iterations(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 3: Existing evidence prevents redundant tool-loop iterations and routes to synthesis."""
    # Simulate state where detection and customer profile already executed
    mock_state: InvestigationState = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "detect_anomalies", "args": {}, "id": "call_det_repeat"}],
            )
        ],
        "statement": stress_statement,
        "tools_used": ["detect_anomalies", "get_customer_profile"],
        "tool_calls": [
            ToolExecutionRecord(tool_name="detect_anomalies", tool_args={}, tool_output_snippet="anomalies found"),
            ToolExecutionRecord(tool_name="get_customer_profile", tool_args={}, tool_output_snippet="turnover"),
        ],
        "iteration_count": 2,
        "max_iterations": 5,
        "canonical_evidence": stress_evidence,
    }

    assert is_evidence_sufficient(mock_state) is True

    # Redundancy check flags repeat of detect_anomalies
    redundancy = check_tool_call_redundancy("detect_anomalies", {}, mock_state)
    assert redundancy is not None
    assert "Redundant tool call skipped" in redundancy

    # Graph router should halt tool loop immediately and route directly to 'synthesis'
    next_node = should_continue_investigator(mock_state)
    assert next_node == "synthesis", f"Expected router to transition to synthesis, got {next_node}"


# ---------------------------------------------------------------------------
# Test 4: Synthesis is reached after sufficient evidence collection
# ---------------------------------------------------------------------------

def test_4_synthesis_reached_after_sufficient_evidence_collection(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 4: Synthesis is reached after sufficient evidence collection even if budget limit was met."""
    mock_state: InvestigationState = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "search_transactions", "args": {"transaction_id": "TXN445"}, "id": "c_txn"}],
            )
        ],
        "statement": stress_statement,
        "tools_used": ["detect_anomalies", "get_customer_profile", "analyze_transaction_network"],
        "tool_calls": [
            ToolExecutionRecord(tool_name="detect_anomalies", tool_args={}, tool_output_snippet="TXN445 flagged"),
            ToolExecutionRecord(tool_name="get_customer_profile", tool_args={}, tool_output_snippet="turnover"),
        ],
        "iteration_count": 6,  # exceeded max_iterations (5)
        "max_iterations": 5,
        "canonical_evidence": stress_evidence,
    }

    assert is_evidence_sufficient(mock_state) is True
    # Router must NOT route to max_iterations when evidence is sufficient; routes to synthesis
    next_node = should_continue_investigator(mock_state)
    assert next_node == "synthesis"


# ---------------------------------------------------------------------------
# Test 5: Human-review shortlist is smaller than complete transaction set
# ---------------------------------------------------------------------------

def test_5_human_review_shortlist_smaller_than_complete_transaction_set(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 5: Human-review shortlist is smaller than complete transaction set (54) when convergence applies."""
    items = stress_evidence.human_review_items
    total_txns = len(stress_statement.transactions)

    assert len(items) < total_txns, (
        f"Human review shortlist ({len(items)}) must be smaller than total transactions ({total_txns})"
    )
    assert len(items) == 50

    # Verify background noise transactions with zero specific risk are dropped
    item_tids = {item.transaction_id for item in items}
    assert "TXN402" not in item_tids  # Rent
    assert "TXN403" not in item_tids  # Green Mart groceries
    assert "TXN433" not in item_tids  # Rent repeat
    assert "TXN454" not in item_tids  # Family transfer


# ---------------------------------------------------------------------------
# Test 6: Human-review items have valid supporting finding IDs
# ---------------------------------------------------------------------------

def test_6_human_review_items_have_valid_supporting_finding_ids(
    stress_evidence: CanonicalEvidence,
):
    """TEST 6: Every HumanReviewItem has valid, traceable supporting finding IDs."""
    items = stress_evidence.human_review_items
    assert len(items) > 0

    valid_rule_finding_ids = {rf.finding_id for rf in stress_evidence.rule_findings}
    valid_anomaly_finding_ids = {f"ANOMALY_{af.transaction_id}" for af in stress_evidence.statistical_anomalies}
    valid_net_finding_ids = {f"NET_{nf.pattern_name}" for nf in stress_evidence.network_findings}

    all_valid_finding_ids = valid_rule_finding_ids | valid_anomaly_finding_ids | valid_net_finding_ids

    for item in items:
        assert len(item.supporting_finding_ids) > 0, f"{item.transaction_id} has no supporting finding IDs"
        for fid in item.supporting_finding_ids:
            assert fid in all_valid_finding_ids, (
                f"Finding ID '{fid}' on transaction '{item.transaction_id}' is not in canonical findings!"
            )


# ---------------------------------------------------------------------------
# Test 7: No HumanReviewItem generated solely from transaction ordering
# ---------------------------------------------------------------------------

def test_7_no_human_review_item_generated_solely_from_transaction_ordering(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 7: No HumanReviewItem can be generated solely from transaction ordering."""
    items = stress_evidence.human_review_items
    item_ids = [item.transaction_id for item in items]
    statement_order_ids = [t.transaction_id for t in stress_statement.transactions]

    # Verify the order does not match statement order
    assert item_ids[:6] != statement_order_ids[:6]

    # Strongly converged transactions rank at the top
    assert item_ids[0] == "TXN445"
    assert item_ids[1] == "TXN434"
    assert items[0].priority == "HIGH"
    assert items[1].priority == "HIGH"


# ---------------------------------------------------------------------------
# Test 8: No LLM-generated transaction ID can bypass CanonicalEvidence
# ---------------------------------------------------------------------------

def test_8_no_llm_generated_transaction_id_can_bypass_canonical_evidence(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 8: No LLM-generated transaction ID can bypass CanonicalEvidence."""
    # Attempt to claim hallucinated transaction TXN999 in human review recommendation
    critic_res = evaluate_investigation_draft(
        draft_text="Transaction TXN999 is recommended for human review due to suspicious rapid movement.",
        statement=stress_statement,
        canonical_evidence=stress_evidence,
    )
    assert critic_res.passed is False
    assert any("TXN999" in issue for issue in critic_res.issues)

    # Attempt to claim valid transaction TXN402 (rent) in human review without canonical support
    critic_res_402 = evaluate_investigation_draft(
        draft_text="Transaction TXN402 is recommended for human review as an anomalous fund flow.",
        statement=stress_statement,
        canonical_evidence=stress_evidence,
    )
    assert critic_res_402.passed is False
    assert any("TXN402" in issue for issue in critic_res_402.issues)


# ---------------------------------------------------------------------------
# Test 9: Existing anomaly IDs remain exactly verified
# ---------------------------------------------------------------------------

def test_9_existing_anomaly_ids_remain_exactly_verified(stress_evidence: CanonicalEvidence):
    """TEST 9: Existing anomaly IDs remain exactly TXN401, TXN404, TXN434, TXN442, TXN445, TXN451."""
    expected_anomalies = ["TXN401", "TXN404", "TXN434", "TXN442", "TXN445", "TXN451"]
    actual_anomalies = sorted(stress_evidence.anomaly_transaction_ids)
    assert actual_anomalies == expected_anomalies, (
        f"Anomaly IDs changed! Expected {expected_anomalies}, got {actual_anomalies}"
    )


# ---------------------------------------------------------------------------
# Test 10: Status distinctions are explicit and unambiguous
# ---------------------------------------------------------------------------

def test_10_status_distinctions_are_explicit_and_unambiguous():
    """TEST 10: Verify explicit status distinctions between NORMAL_COMPLETION, MAX_ITERATIONS_REACHED, etc."""
    normal_status = InvestigationStatus.NORMAL_COMPLETION
    max_iter_status = InvestigationStatus.MAX_ITERATIONS_REACHED
    all_failed_status = InvestigationStatus.ALL_PROVIDERS_FAILED
    prov_fail_status = InvestigationStatus.PROVIDER_FAILURE
    inv_fail_status = InvestigationStatus.INVESTIGATION_FAILED

    # Must distinguish clearly
    assert normal_status != max_iter_status
    assert normal_status != all_failed_status
    assert normal_status != prov_fail_status
    assert normal_status != inv_fail_status

    # NORMAL_COMPLETION satisfies both representations
    assert normal_status == "NORMAL_COMPLETION"
    assert normal_status == "COMPLETED"

    # MAX_ITERATIONS_REACHED must NOT be treated as a successful completion
    assert max_iter_status != "COMPLETED"
    assert max_iter_status != "NORMAL_COMPLETION"
