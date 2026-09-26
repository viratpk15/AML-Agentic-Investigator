"""Unit tests for M16: Investigation Report Engine."""

import datetime as dt
import json
import pytest

from aml_copilot.agents.models import CritiqueResult
from aml_copilot.agents.state import InvestigationResult
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.reporting.formatter import format_report_json, format_report_markdown
from aml_copilot.reporting.generator import generate_investigation_report
from aml_copilot.reporting.models import (
    CriticSummary,
    EvidenceItem,
    InvestigationReport,
    RevisionSummary,
)


@pytest.fixture
def sample_statement() -> TransactionStatement:
    """Fixture providing a test statement with known transactions."""
    return TransactionStatement(
        customer_name="Orion Trading Co",
        account_number="AC-889900",
        statement_period="2026-08-01 to 2026-08-15",
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 2),
                transaction_id="TXN001",
                description="CAPITAL ADVANCE",
                credit=50000.0,
                debit=None,
                balance=50000.0,
                counterparty="FOUNDER",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN005",
                description="OVERSEAS CREDIT WIRE",
                credit=480000.0,
                debit=None,
                balance=530000.0,
                counterparty="GLOBAL TRADER",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN006",
                description="OUTGOING TRANSFER",
                credit=None,
                debit=475000.0,
                balance=55000.0,
                counterparty="RAHUL EXPORTS",
            ),
        ],
    )


@pytest.fixture
def sample_investigation_result() -> InvestigationResult:
    """Fixture providing an InvestigationResult with verified transaction citations."""
    return InvestigationResult(
        question="Investigate unusual fund movement in account AC-889900.",
        response=(
            "Observed Evidence:\n"
            "Transaction TXN005 was a ₹480,000 credit from GLOBAL TRADER on 2026-08-10.\n"
            "Transaction TXN006 was an immediate outgoing debit of ₹475,000 to RAHUL EXPORTS.\n\n"
            "Interpretation:\n"
            "This pattern indicates rapid fund pass-through requiring senior compliance review."
        ),
        tools_used=["get_transaction_statistics", "detect_anomalies"],
        tool_calls=[],
        referenced_transaction_ids=["TXN005", "TXN006"],
        knowledge_sources=["aml_red_flags.md"],
        customer_profile=None,
        network_analysis=None,
        critic_result=CritiqueResult(
            passed=True,
            issues=[],
            missing_evidence=[],
            unsupported_claims=[],
            required_revisions=[],
            checked_transaction_ids=["TXN005", "TXN006"],
            invalid_transaction_ids=[],
            safety_violations=[],
        ),
        critic_status="PASS",
        revision_count=1,
        limitations_warnings=[
            "Investigation findings are an analytical aid and do not establish guilt."
        ],
    )


def test_report_model_creation_and_serialization(sample_statement, sample_investigation_result):
    """Verify InvestigationReport models create properly and serialize to JSON and dict."""
    report = generate_investigation_report(
        statement=sample_statement,
        investigation=sample_investigation_result,
    )

    assert isinstance(report, InvestigationReport)
    assert report.customer_name == "Orion Trading Co"
    assert report.account_number == "AC-889900"
    assert "TXN005" in [e.transaction_id for e in report.observed_evidence]
    assert "TXN006" in [e.transaction_id for e in report.observed_evidence]

    # Serialization
    json_str = format_report_json(report)
    parsed = json.loads(json_str)
    assert parsed["report_id"].startswith("REP-AML-")
    assert parsed["customer_name"] == "Orion Trading Co"
    assert parsed["critic_validation"]["passed"] is True
    assert parsed["revision_history"]["revision_count"] == 1


def test_evidence_traceability_guarantee(sample_statement, sample_investigation_result):
    """Verify that transaction evidence is pulled deterministically from the statement."""
    report = generate_investigation_report(
        statement=sample_statement,
        investigation=sample_investigation_result,
    )

    evidence_by_id = {e.transaction_id: e for e in report.observed_evidence}

    # TXN005
    assert "TXN005" in evidence_by_id
    txn5 = evidence_by_id["TXN005"]
    assert txn5.amount == 480000.0
    assert txn5.flow_type == "credit"
    assert txn5.date == "2026-08-10"
    assert txn5.counterparty == "GLOBAL TRADER"
    assert txn5.verified_in_statement is True

    # TXN006
    assert "TXN006" in evidence_by_id
    txn6 = evidence_by_id["TXN006"]
    assert txn6.amount == 475000.0
    assert txn6.flow_type == "debit"
    assert txn6.date == "2026-08-10"
    assert txn6.counterparty == "RAHUL EXPORTS"
    assert txn6.verified_in_statement is True


def test_unverified_transaction_id_marked_unverified(sample_statement, sample_investigation_result):
    """Verify that if an unverified transaction ID was referenced, it is explicitly flagged."""
    # Artificially inject a non-existent transaction ID
    sample_investigation_result.referenced_transaction_ids.append("TXN999")

    report = generate_investigation_report(
        statement=sample_statement,
        investigation=sample_investigation_result,
    )

    evidence_by_id = {e.transaction_id: e for e in report.observed_evidence}
    assert "TXN999" in evidence_by_id
    txn999 = evidence_by_id["TXN999"]
    assert txn999.verified_in_statement is False
    assert txn999.amount is None


def test_markdown_generation_structure(sample_statement, sample_investigation_result):
    """Verify formatted Markdown contains all 14 required compliance audit sections."""
    report = generate_investigation_report(
        statement=sample_statement,
        investigation=sample_investigation_result,
    )
    md = format_report_markdown(report)

    assert "# AML Investigation Report" in md
    assert "## 1. Investigation Overview" in md
    assert "## 2. Executive Summary" in md
    assert "## 3. Observed Transaction Evidence" in md
    assert "## 4. Detection Findings" in md
    assert "## 5. Customer Profile" in md
    assert "## 6. Network Analysis" in md
    assert "## 7. AML Knowledge Context" in md
    assert "## 8. Evidence Convergence" in md
    assert "## 9. Human Review Queue" in md
    assert "## 10. Interpretation" in md
    assert "## 11. Limitations" in md
    assert "## 12. Recommended Next Steps" in md
    assert "## 13. Critic Validation" in md
    assert "## 14. Human Review" in md

    # Ensure evidence table contains the exact verified numbers
    assert "₹480,000.00" in md
    assert "GLOBAL TRADER" in md
    assert "✓ Verified" in md


def test_critic_failure_and_unresolved_warning_preserved(sample_statement):
    """Verify that when Critic status is FAIL and max revisions reached, warning is explicit."""
    failing_investigation = InvestigationResult(
        question="Investigate account.",
        response="Unresolved investigation draft.",
        tools_used=[],
        tool_calls=[],
        referenced_transaction_ids=["TXN001"],
        knowledge_sources=[],
        critic_result=CritiqueResult(
            passed=False,
            issues=["Amount mismatch detected for TXN001."],
            missing_evidence=["Debit transactions not reviewed."],
            unsupported_claims=["Customer engaged in fraud."],
            required_revisions=["Remove fraud claim."],
            checked_transaction_ids=["TXN001"],
            invalid_transaction_ids=[],
            safety_violations=["Declaring criminal guilt"],
        ),
        critic_status="FAIL",
        revision_count=2,
        limitations_warnings=["Investigation concluded with unresolved Critic findings."],
    )

    report = generate_investigation_report(
        statement=sample_statement,
        investigation=failing_investigation,
    )

    assert report.critic_validation.passed is False
    assert report.critic_validation.status == "FAIL"
    assert report.revision_history.unresolved_limitations is True

    md = format_report_markdown(report)
    assert "**FAILED** ✗" in md
    assert "Investigation completed with unresolved validation limitations. Human review is required." in md
    assert "Amount mismatch detected for TXN001" in md


def test_compliance_safety_and_human_review_boundary(sample_statement, sample_investigation_result):
    """Verify report explicitly emphasizes human review and does not declare legal guilt."""
    report = generate_investigation_report(
        statement=sample_statement,
        investigation=sample_investigation_result,
    )

    assert "qualified human compliance officers" in report.human_review_recommendation
    assert any("not establish guilt" in lim.lower() for lim in report.limitations)
