"""Unit and integration tests for M14 & M15: Investigation Agent & Critic/Revision Loop."""

import datetime as dt
from typing import Any, List, Optional
import uuid
import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from aml_copilot.agents.critic import evaluate_investigation_draft
from aml_copilot.agents.graph import (
    build_investigation_graph,
    route_after_critic,
    should_continue_investigator,
)
from aml_copilot.agents.investigation_agent import InvestigationAgent, run_investigation
from aml_copilot.agents.models import (
    CritiqueResult,
    EvidenceReference,
    InvestigationDraft,
    InvestigationFinding,
)
from aml_copilot.agents.revision import create_revision_node
from aml_copilot.agents.state import InvestigationResult, InvestigationState
from aml_copilot.agents.synthesis import synthesize_findings_from_response
from aml_copilot.models.transaction import Transaction, TransactionStatement


# ---------------------------------------------------------------------------
# Test Fixtures & Scripted LLM
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_statement() -> TransactionStatement:
    """Fixture providing a test statement with known transactions."""
    return TransactionStatement(
        customer_name="Orion Ventures Ltd",
        account_number="AC-112233",
        statement_period="2026-08-01 to 2026-08-20",
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 1),
                transaction_id="TXN001",
                description="CAPITAL INJECTION",
                credit=100000.0,
                debit=None,
                balance=100000.0,
                counterparty="FOUNDER",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN005",
                description="LARGE CREDIT FROM APEX CORP",
                credit=480000.0,
                debit=None,
                balance=580000.0,
                counterparty="APEX CORP",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN006",
                description="WIRE OUT TO RAHUL SERVICES",
                credit=None,
                debit=475000.0,
                balance=105000.0,
                counterparty="RAHUL SERVICES",
            ),
        ],
    )


class ScriptedChatModel(BaseChatModel):
    """Deterministic mock ChatModel yielding a sequence of scripted AIMessages."""

    scripted_responses: List[AIMessage]
    call_count: int = 0
    received_messages: List[List[BaseMessage]] = []

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        return self

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.received_messages.append(list(messages))
        if self.call_count < len(self.scripted_responses):
            resp = self.scripted_responses[self.call_count]
        else:
            resp = AIMessage(content="Fallback concluding summary.", id=str(uuid.uuid4()))
        self.call_count += 1
        resp_copy = resp.model_copy(update={"id": str(uuid.uuid4())})
        return ChatResult(generations=[ChatGeneration(message=resp_copy)])

    @property
    def _llm_type(self) -> str:
        return "scripted-critic-test-llm"


# ---------------------------------------------------------------------------
# 1. Investigation State & Finding Models Tests
# ---------------------------------------------------------------------------

def test_investigation_finding_models():
    """Verify structured Pydantic models for findings and evidence references."""
    ref = EvidenceReference(
        source_type="transaction",
        transaction_ids=["TXN005", "TXN006"],
        description="Rapid fund pass-through on 2026-08-10.",
        details={"credit": 480000.0, "debit": 475000.0},
    )
    assert ref.source_type == "transaction"
    assert "TXN005" in ref.transaction_ids

    finding = InvestigationFinding(
        finding="Rapid movement of funds observed.",
        evidence="TXN005 credit ₹480,000 followed by TXN006 debit ₹475,000.",
        transaction_ids=["TXN005", "TXN006"],
        source_type="detection + transaction + network",
        explanation="₹480,000 received from APEX CORP and ₹475,000 transferred to RAHUL SERVICES.",
        confidence="high",
    )
    assert finding.confidence == "high"
    assert len(finding.transaction_ids) == 2

    critique = CritiqueResult(
        passed=False,
        issues=["Missing debit leg."],
        missing_evidence=["TXN006"],
        unsupported_claims=["Customer committed fraud."],
        required_revisions=["Remove fraud accusation."],
        checked_transaction_ids=["TXN005"],
        invalid_transaction_ids=[],
        safety_violations=["Declaring criminal guilt"],
    )
    assert not critique.passed
    assert critique.safety_violations[0] == "Declaring criminal guilt"


# ---------------------------------------------------------------------------
# 2. Deterministic Critic Verification Tests (Python Factual Layer)
# ---------------------------------------------------------------------------

def test_critic_valid_transaction_passes(sample_statement: TransactionStatement):
    """Verify that accurate statements referencing real transactions pass critique."""
    draft_text = (
        "Observed Evidence:\n"
        "Transaction TXN005 was a credit of ₹480,000 from APEX CORP on 2026-08-10.\n"
        "Transaction TXN006 was an immediate debit of ₹475,000 to RAHUL SERVICES.\n\n"
        "Interpretation:\n"
        "This activity represents rapid movement of funds and warrants compliance review.\n\n"
        "Limitation:\n"
        "This pattern indicates an investigation signal and does not establish guilt."
    )
    critique = evaluate_investigation_draft(draft_text, sample_statement)
    assert critique.passed is True
    assert len(critique.issues) == 0
    assert len(critique.unsupported_claims) == 0
    assert critique.checked_transaction_ids == ["TXN005", "TXN006"]
    assert critique.invalid_transaction_ids == []


def test_critic_flags_fake_transaction_id(sample_statement: TransactionStatement):
    """Verify critic flags non-existent transaction IDs as unsupported claims."""
    draft_text = (
        "Observed Evidence:\n"
        "Transaction TXN999 was a suspicious transfer of ₹500,000.\n"
        "Requires further human review."
    )
    critique = evaluate_investigation_draft(draft_text, sample_statement)
    assert critique.passed is False
    assert "TXN999" in critique.invalid_transaction_ids
    assert any("TXN999" in iss for iss in critique.issues)
    assert any("does not exist" in claim for claim in critique.unsupported_claims)


def test_critic_flags_amount_mismatch(sample_statement: TransactionStatement):
    """Verify critic detects when cited amount does not match statement records."""
    draft_text = (
        "Observed Evidence:\n"
        "Transaction TXN005 had an amount of ₹999,000 credited to the account.\n"
        "Requires review."
    )
    critique = evaluate_investigation_draft(draft_text, sample_statement)
    assert critique.passed is False
    assert any("Amount" in iss and "does not match" in iss for iss in critique.issues)
    assert any("Verify and correct amount" in rev for rev in critique.required_revisions)


def test_critic_flags_date_mismatch(sample_statement: TransactionStatement):
    """Verify critic detects when cited date does not match statement records."""
    draft_text = (
        "Observed Evidence:\n"
        "Transaction TXN005 occurred on 2026-08-25 as a large inflow.\n"
        "Requires compliance review."
    )
    critique = evaluate_investigation_draft(draft_text, sample_statement)
    assert critique.passed is False
    assert any("Date 2026-08-25 cited for 'TXN005' does not match" in iss for iss in critique.issues)


def test_critic_flags_safety_and_guilt_violations(sample_statement: TransactionStatement):
    """Verify critic strictly rejects legal conclusions or autonomous enforcement orders."""
    draft_text = (
        "Investigation Findings:\n"
        "The customer is guilty of money laundering through TXN005.\n"
        "We must close the account and file a SAR immediately."
    )
    critique = evaluate_investigation_draft(draft_text, sample_statement)
    assert critique.passed is False
    assert len(critique.safety_violations) >= 2
    assert any("Declaring customer guilt" in v for v in critique.safety_violations)
    assert any("Mandating account closure" in v for v in critique.safety_violations)
    assert any("Prohibited compliance assertion" in claim for claim in critique.unsupported_claims)


def test_critic_flags_missing_question_transaction(sample_statement: TransactionStatement):
    """Verify critic flags missing analysis when question specifically asks about a transaction."""
    draft_text = (
        "Observed Evidence:\n"
        "Transaction TXN005 represents a large inflow of ₹480,000."
    )
    # Analyst explicitly asked to inspect TXN006
    critique = evaluate_investigation_draft(
        draft_text=draft_text,
        statement=sample_statement,
        question="Please inspect TXN006 and explain the risk.",
    )
    assert critique.passed is False
    assert any("TXN006" in me for me in critique.missing_evidence)
    assert any("TXN006" in rev for rev in critique.required_revisions)


# ---------------------------------------------------------------------------
# 3. Investigation Synthesis Node Tests
# ---------------------------------------------------------------------------

def test_synthesize_findings_from_response(sample_statement: TransactionStatement):
    """Verify structured draft is extracted and partitioned from agent's response."""
    response_text = (
        "Observed Evidence:\n"
        "- TXN005: ₹480,000 credit from APEX CORP on 2026-08-10.\n"
        "- TXN006: ₹475,000 debit to RAHUL SERVICES on 2026-08-10.\n\n"
        "Analytical Findings:\n"
        "- Rapid fund pass-through rule triggered.\n"
        "- Anomaly score elevated at 0.72.\n\n"
        "Network Findings:\n"
        "- Directed fund flow observed from APEX CORP to customer to RAHUL SERVICES.\n\n"
        "Relevant AML Reference:\n"
        "- Pass-through conduit typologies indicate high velocity fund movement.\n\n"
        "Interpretation:\n"
        "- Warrants human analyst review as a possible conduit account pattern."
    )
    draft = synthesize_findings_from_response(
        response_text=response_text,
        statement=sample_statement,
        question="Analyze account flow.",
    )
    assert isinstance(draft, InvestigationDraft)
    assert "TXN005" in draft.referenced_transaction_ids
    assert "TXN006" in draft.referenced_transaction_ids
    assert len(draft.observed_evidence) >= 1
    assert len(draft.analytical_findings) >= 1
    assert len(draft.network_findings) >= 1
    assert len(draft.reference_context) >= 1
    assert len(draft.findings) >= 1


# ---------------------------------------------------------------------------
# 4. End-to-End Graph: Investigator -> Critic PASS -> END
# ---------------------------------------------------------------------------

def test_full_graph_investigator_to_critic_pass(sample_statement: TransactionStatement):
    """Verify happy path: Investigator calls tools, drafts well-grounded response, Critic passes."""
    call_id = str(uuid.uuid4())
    step1_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_transactions",
                "args": {"transaction_id": "TXN005"},
                "id": call_id,
            }
        ],
    )
    step2_synthesis = AIMessage(
        content=(
            "Observed Evidence:\n"
            "TXN005 is a credit of ₹480,000 from APEX CORP on 2026-08-10.\n\n"
            "Interpretation:\n"
            "This large single transaction represents an unusual activity for review.\n\n"
            "Limitation:\n"
            "Does not establish guilt or fraud."
        )
    )

    mock_llm = ScriptedChatModel(scripted_responses=[step1_call, step2_synthesis])
    agent = InvestigationAgent(llm=mock_llm, enable_critic=True)

    result = agent.investigate(
        statement=sample_statement,
        question="Analyze transaction TXN005.",
    )

    assert isinstance(result, InvestigationResult)
    assert result.critic_status == "PASS"
    assert result.critic_result.passed is True
    assert result.revision_count == 0
    assert "TXN005" in result.referenced_transaction_ids
    assert "search_transactions" in result.tools_used


# ---------------------------------------------------------------------------
# 5. End-to-End Graph: Revision Loop (Critic FAIL -> Revision -> Critic PASS)
# ---------------------------------------------------------------------------

def test_full_graph_critic_fail_and_revision_loop_to_pass(sample_statement: TransactionStatement):
    """Verify revision loop: Draft 1 has unsupported claim (fake ID), Critic fails, Revision prompt sent, Draft 2 passes."""
    # Step 1: LLM initially returns an unsupported draft citing non-existent TXN999
    step1_bad_draft = AIMessage(
        content=(
            "Observed Evidence:\n"
            "Identified suspicious transaction TXN999 involving ₹500,000.\n"
            "Requires review."
        )
    )

    # Step 2: After Critic rejects TXN999 and sends revision instructions, LLM corrects itself
    step2_corrected_draft = AIMessage(
        content=(
            "Observed Evidence:\n"
            "Correction applied: Reviewing confirmed records, transaction TXN005 was a ₹480,000 credit from APEX CORP.\n\n"
            "Interpretation:\n"
            "Requires compliance review.\n\n"
            "Limitation:\n"
            "Does not establish guilt or fraud."
        )
    )

    mock_llm = ScriptedChatModel(scripted_responses=[step1_bad_draft, step2_corrected_draft])
    agent = InvestigationAgent(llm=mock_llm, enable_critic=True, max_revisions=2)

    result = agent.investigate(
        statement=sample_statement,
        question="Investigate transactions.",
    )

    # Verify that a revision occurred
    assert result.revision_count == 1
    assert result.critic_status == "PASS"
    assert result.critic_result.passed is True
    assert "TXN005" in result.referenced_transaction_ids
    assert "TXN999" not in result.referenced_transaction_ids


# ---------------------------------------------------------------------------
# 6. Revision Limit Enforcement: Prevents Infinite Loops
# ---------------------------------------------------------------------------

def test_revision_limit_prevents_infinite_loop(sample_statement: TransactionStatement):
    """Verify that when the LLM persistently fails critique, the loop terminates at max_revisions."""
    persistent_bad_draft = AIMessage(
        content="Observed Evidence: TXN999 is suspicious. Customer is guilty of money laundering."
    )

    mock_llm = ScriptedChatModel(
        scripted_responses=[
            persistent_bad_draft,
            persistent_bad_draft,
            persistent_bad_draft,
            persistent_bad_draft,
        ]
    )
    # Allow at most 2 revisions
    agent = InvestigationAgent(llm=mock_llm, enable_critic=True, max_revisions=2)

    result = agent.investigate(
        statement=sample_statement,
        question="Investigate account.",
    )

    # Verify loop terminated strictly at max_revisions without infinite cycle
    assert result.revision_count == 2
    assert result.critic_status == "FAIL"
    assert result.critic_result.passed is False
    # Check that limitation warning was appended explaining unresolved findings
    assert any("unresolved Critic findings" in w for w in result.limitations_warnings)


# ---------------------------------------------------------------------------
# 7. Dynamic Tool Selection (Investigator Decides Tools Based on Query)
# ---------------------------------------------------------------------------

def test_dynamic_tool_selection_simple_volume_query(sample_statement: TransactionStatement):
    """Verify Investigator dynamically calls only get_transaction_statistics for volume query."""
    call_id = str(uuid.uuid4())
    step1_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_transaction_statistics",
                "args": {},
                "id": call_id,
            }
        ],
    )
    step2_synthesis = AIMessage(
        content=(
            "Observed Evidence:\n"
            "The customer total turnover is ₹1,055,000 across 3 transactions.\n\n"
            "Interpretation:\n"
            "Account statistics reviewed."
        )
    )

    mock_llm = ScriptedChatModel(scripted_responses=[step1_call, step2_synthesis])
    agent = InvestigationAgent(llm=mock_llm, enable_critic=True)

    result = agent.investigate(
        statement=sample_statement,
        question="What is the customer's total volume?",
    )

    # Agent called ONLY statistics, NOT detection, RAG, or network
    assert result.tools_used == ["get_transaction_statistics"]
    assert "detect_anomalies" not in result.tools_used
    assert "search_aml_knowledge" not in result.tools_used
    assert "analyze_transaction_network" not in result.tools_used
    assert result.critic_status == "PASS"
