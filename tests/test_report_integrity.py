"""Phase 14 — Regression tests for AML investigation report integrity and provenance.

Validates all 12 specific Phase 14 criteria:
1. test_no_anomaly_range_reconstruction
2. test_exact_anomaly_ids
3. test_review_queue_not_equal_statement_by_default
4. test_no_stale_granular_details_limitation
5. test_critic_verification_count
6. test_counterparty_count_consistency
7. test_no_regulatory_threshold_inference
8. test_rag_source_wording
9. test_report_section_consistency
10. test_evidence_convergence_provenance
11. test_transaction_detail_drawer_data
12. test_report_json_matches_canonical_evidence
"""

import json
from pathlib import Path
import pytest

from aml_copilot.agents.models import CritiqueResult
from aml_copilot.agents.state import InvestigationResult
from aml_copilot.models.evidence import build_canonical_evidence
from aml_copilot.reporting.formatter import format_report_markdown
from aml_copilot.reporting.generator import (
    align_narrative_with_canonical_evidence,
    generate_investigation_report,
)
from aml_copilot.reporting.validation import validate_report_evidence
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_explorer import build_transaction_dossier
from aml_copilot.services.transaction_parser import parse_transactions


STRESS_PDF_PATH = Path("data/statements/ultimate_publish_stress_statement.pdf")


@pytest.fixture(scope="module")
def parsed_stress_statement():
    """Load and parse the 54-transaction stress statement once for the module."""
    if not STRESS_PDF_PATH.exists():
        pytest.skip(f"Stress statement PDF not found: {STRESS_PDF_PATH}")
    doc = extract_pdf_text(STRESS_PDF_PATH)
    return parse_transactions(doc)


@pytest.fixture(scope="module")
def canonical_stress_evidence(parsed_stress_statement):
    """Build canonical evidence for the stress statement."""
    return build_canonical_evidence(parsed_stress_statement)


@pytest.fixture(scope="module")
def standard_investigation_result():
    """Build grounded InvestigationResult referencing canonical stress findings."""
    return InvestigationResult(
        question="Investigate unusual movement of funds in this account and highlight transactions requiring human review.",
        response=(
            "Observed Evidence:\n"
            "During October 2026, 54 transactions were processed for customer Arjun Malhotra (Account XX6384). "
            "Key transactions include TXN445 (a ₹575,000 credit from WESTBROOK MATERIALS on 2026-10-20), "
            "followed by disbursements including TXN446 (a ₹255,000 debit to LUMEN CONSULTING on 2026-10-20).\n\n"
            "Analytical Findings:\n"
            "Deterministic screening triggered the configured monitoring threshold for large transactions (RULE_LARGE_TRANSACTION), "
            "rapid movement of funds (RULE_RAPID_MOVEMENT_OF_FUNDS), and velocity bursts. "
            "Isolation Forest unsupervised anomaly detection identified exactly 6 statistical outliers: "
            "TXN401, TXN404, TXN434, TXN442, TXN445, and TXN451 based on amount, directional velocity, and inter-transaction time deltas.\n\n"
            "Customer Profile and Network Findings:\n"
            "The profile reflects 54 transactions across 28 unique counterparties with net outflow of ₹771,960. "
            "Directed counterparty analysis establishes a 29-node graph with 37 flow edges.\n\n"
            "AML Reference Guidance:\n"
            "Guidance from the AML reference knowledge base (aml_red_flags.md, aml_transaction_monitoring.md) notes that "
            "rapid pass-through conduit flows and high transaction velocity warrant elevated compliance scrutiny.\n\n"
            "Evidence Convergence & Review Prioritization:\n"
            "50 transactions generated review signals, with 25 prioritized as HIGH priority. "
            "The highest convergence was observed on TXN445 and TXN434.\n\n"
            "Investigative Scope & Limitations:\n"
            "These findings represent investigative risk signals and evidence summaries to assist compliance personnel. "
            "They do not constitute a determination of fraud, money laundering, criminal conduct, or legal liability."
        ),
        tools_used=[
            "get_transaction_statistics",
            "detect_anomalies",
            "get_customer_profile",
            "analyze_transaction_network",
            "search_aml_knowledge",
        ],
        tool_calls=[],
        referenced_transaction_ids=[
            "TXN401", "TXN404", "TXN434", "TXN442", "TXN445", "TXN451", "TXN406", "TXN415", "TXN422"
        ],
        knowledge_sources=["aml_red_flags.md", "aml_transaction_monitoring.md", "aml_investigation_guidance.md"],
        critic_result=CritiqueResult(
            passed=True,
            issues=[],
            missing_evidence=[],
            unsupported_claims=[],
            required_revisions=[],
            checked_transaction_ids=[
                "TXN401", "TXN404", "TXN434", "TXN442", "TXN445", "TXN451", "TXN406", "TXN415", "TXN422"
            ],
            invalid_transaction_ids=[],
            safety_violations=[],
            statement_transaction_count=54,
            narrative_transaction_reference_count=9,
            human_review_transaction_count=50,
            verified_transaction_reference_count=9,
            unverified_transaction_reference_count=0,
        ),
        critic_status="PASS",
        revision_count=1,
        limitations_warnings=[
            "Investigation findings are an analytical aid for compliance analysis and do not establish guilt or fraud.",
            "Analysis is bounded by the transactions presented within the statement period.",
        ],
    )


@pytest.fixture(scope="module")
def standard_report(parsed_stress_statement, standard_investigation_result):
    """Generate canonical investigation report on stress statement."""
    return generate_investigation_report(
        statement=parsed_stress_statement,
        investigation=standard_investigation_result,
    )


# ---------------------------------------------------------------------------
# Test 1: No Anomaly Range Reconstruction
# ---------------------------------------------------------------------------

def test_no_anomaly_range_reconstruction(canonical_stress_evidence):
    """Test that anomaly narratives and generator never reconstruct a contiguous ID range like 'TXN401 through TXN454'."""
    raw_draft_with_range = (
        "Statistical analysis flagged transactions spanning TXN401 through TXN454 as anomalies. "
        "Also TXN401 to TXN454 were highlighted."
    )
    cleaned = align_narrative_with_canonical_evidence(raw_draft_with_range, canonical_stress_evidence)

    assert "TXN401 through TXN454" not in cleaned
    assert "TXN401 to TXN454" not in cleaned
    # Ensure exact canonical anomalies are listed instead
    for aid in ["TXN401", "TXN404", "TXN434", "TXN442", "TXN445", "TXN451"]:
        assert aid in cleaned


# ---------------------------------------------------------------------------
# Test 2: Exact Anomaly IDs Preserved
# ---------------------------------------------------------------------------

def test_exact_anomaly_ids(standard_report, canonical_stress_evidence):
    """Test that canonical Isolation Forest anomaly set is preserved with 0 non-anomalies."""
    expected_ids = {"TXN401", "TXN404", "TXN434", "TXN442", "TXN445", "TXN451"}

    # From canonical evidence
    canon_ids = {a.transaction_id for a in canonical_stress_evidence.statistical_anomalies}
    assert canon_ids == expected_ids

    # From report anomaly findings
    report_anom_ids = {a.transaction_id for a in standard_report.anomaly_findings}
    assert report_anom_ids == expected_ids

    # Ensure no non-anomaly transaction is labeled as an anomaly
    for non_anom in ["TXN402", "TXN403", "TXN405", "TXN410", "TXN420", "TXN430"]:
        assert non_anom not in report_anom_ids


# ---------------------------------------------------------------------------
# Test 3: Review Queue Not Equal to Full Statement by Default
# ---------------------------------------------------------------------------

def test_review_queue_not_equal_statement_by_default(standard_report):
    """Test that the report distinguishes total analyzed (54) from prioritized review queue (50)."""
    assert standard_report.total_transactions_analyzed == 54
    assert len(standard_report.human_review_items) == 50
    assert len(standard_report.human_review_items) < standard_report.total_transactions_analyzed

    # Markdown must never claim all 54 require review
    md = format_report_markdown(standard_report)
    assert "All 54 transactions require review" not in md
    assert "all 54 require review" not in md.lower()
    assert "50 transactions generated prioritized human-review signals" in md


# ---------------------------------------------------------------------------
# Test 4: No Stale "Granular Details Unavailable" Limitation
# ---------------------------------------------------------------------------

def test_no_stale_granular_details_limitation(standard_report):
    """Test that report cannot claim granular transaction amounts/dates/counterparties were unavailable."""
    md = format_report_markdown(standard_report)
    assert "granular details not" not in md.lower()
    assert "granular transaction-level amounts, dates, or counterparty identities were not" not in md

    # Check limitations list directly
    for lim in standard_report.limitations:
        assert "granular details" not in lim.lower()
        assert "not fully accessible during synthesis" not in lim


# ---------------------------------------------------------------------------
# Test 5: Critic Verification Count Accuracy
# ---------------------------------------------------------------------------

def test_critic_verification_count(standard_report):
    """Test that Critic verification metrics are accurate and never report a misleading count like '2 confirmed'."""
    critic = standard_report.critic_validation
    assert critic.statement_transaction_count == 54
    assert critic.narrative_transaction_reference_count == 9
    assert critic.human_review_transaction_count == 50
    assert critic.verified_transaction_reference_count == 9
    assert critic.unverified_transaction_reference_count == 0

    md = format_report_markdown(standard_report)
    assert "Transaction IDs Verified: 2 confirmed" not in md
    assert "**Evidence References Checked**: 9 confirmed" in md
    assert "**Unverified References**: 0" in md


# ---------------------------------------------------------------------------
# Test 6: Counterparty Count Consistency
# ---------------------------------------------------------------------------

def test_counterparty_count_consistency(standard_report):
    """Test that profile counterparty count (28) matches network counterparty count (28), and distinguishes nodes (29)."""
    profile_cp = standard_report.customer_profile.unique_counterparties
    net_cp = standard_report.network_summary.unique_counterparties
    graph_nodes = standard_report.network_summary.graph_nodes
    graph_edges = standard_report.network_summary.graph_edges

    assert profile_cp == 28
    assert net_cp == 28
    assert profile_cp == net_cp, "Profile and network unique counterparties must be internally consistent"
    assert graph_nodes == 29  # 1 customer + 28 counterparties
    assert graph_edges == 28


# ---------------------------------------------------------------------------
# Test 7: No Regulatory Threshold Inference
# ---------------------------------------------------------------------------

def test_no_regulatory_threshold_inference(standard_report):
    """Test that the internal ₹100,000 threshold is called configured monitoring threshold, not regulatory reporting threshold."""
    md = format_report_markdown(standard_report)
    assert "regulatory reporting threshold" not in md.lower()

    # Generator aligner must normalize this phrasing
    raw = "The transactions exceeded the regulatory reporting threshold of ₹100,000."
    cleaned = align_narrative_with_canonical_evidence(raw, None)
    assert "regulatory reporting threshold" not in cleaned
    assert "configured monitoring threshold" in cleaned


# ---------------------------------------------------------------------------
# Test 8: RAG Source Wording
# ---------------------------------------------------------------------------

def test_rag_source_wording(standard_report):
    """Test that local RAG sources are referred to as 'AML reference knowledge base', not 'external AML knowledge base'."""
    md = format_report_markdown(standard_report)
    assert "external aml knowledge base" not in md.lower()

    # Generator aligner must normalize external RAG references
    raw = "Retrieved from the external AML knowledge base."
    cleaned = align_narrative_with_canonical_evidence(raw, None)
    assert "external AML knowledge base" not in cleaned
    assert "AML reference knowledge base" in cleaned


# ---------------------------------------------------------------------------
# Test 9: Report Section Consistency
# ---------------------------------------------------------------------------

def test_report_section_consistency(standard_report):
    """Test that all 14 required sections are present in order and internally consistent."""
    md = format_report_markdown(standard_report)

    required_sections = [
        "## 1. Investigation Overview",
        "## 2. Executive Summary",
        "## 3. Observed Transaction Evidence",
        "## 4. Detection Findings",
        "## 5. Customer Profile",
        "## 6. Network Analysis",
        "## 7. AML Knowledge Context",
        "## 8. Evidence Convergence",
        "## 9. Human Review Queue",
        "## 10. Interpretation",
        "## 11. Limitations",
        "## 12. Recommended Next Steps",
        "## 13. Critic Validation",
        "## 14. Human Review",
    ]

    for section in required_sections:
        assert section in md, f"Missing required section: {section}"

    # Verify order of appearance
    indices = [md.index(s) for s in required_sections]
    assert indices == sorted(indices), "Report sections are not in canonical sequential order"


# ---------------------------------------------------------------------------
# Test 10: Evidence Convergence Provenance
# ---------------------------------------------------------------------------

def test_evidence_convergence_provenance(standard_report):
    """Test that Evidence Convergence section items are derived strictly from canonical evidence."""
    assert len(standard_report.evidence_convergence) > 0

    top_item = standard_report.evidence_convergence[0]
    assert top_item.transaction_id in ["TXN445", "TXN434"]
    assert top_item.amount > 0
    assert len(top_item.signal_domains) >= 3
    assert any("Statistical" in d for d in top_item.signal_domains)

    # Validate that every convergence item exists in observed evidence
    observed_ids = {e.transaction_id for e in standard_report.observed_evidence}
    for item in standard_report.evidence_convergence:
        assert item.transaction_id in observed_ids


# ---------------------------------------------------------------------------
# Test 11: Transaction Detail Drawer Data
# ---------------------------------------------------------------------------

def test_transaction_detail_drawer_data(standard_report):
    """Test that Transaction Evidence Explorer produces a complete, factual dossier for TXN445."""
    dossier = build_transaction_dossier(standard_report, "TXN445")
    assert dossier is not None
    assert dossier.transaction_id == "TXN445"
    assert dossier.amount == 575000.0
    assert (dossier.flow_type or "").upper() == "CREDIT"
    assert dossier.counterparty == "WESTBROOK MATERIALS"
    assert dossier.is_anomaly is True
    assert dossier.human_review_priority == "HIGH"
    assert len(dossier.rules_triggered) > 0
    assert len(dossier.signal_domains) >= 3

    # Non-existent transaction returns None
    assert build_transaction_dossier(standard_report, "TXN999_NON_EXISTENT") is None


# ---------------------------------------------------------------------------
# Test 12: Report JSON Matches Canonical Evidence
# ---------------------------------------------------------------------------

def test_report_json_matches_canonical_evidence(standard_report, canonical_stress_evidence, parsed_stress_statement):
    """Test that JSON export reconciles 100% with canonical evidence."""
    data = json.loads(standard_report.model_dump_json())

    assert data["total_transactions_analyzed"] == 54
    assert len(data["observed_evidence"]) == 54
    assert len(data["anomaly_findings"]) == 6
    assert len(data["human_review_items"]) == 50

    # Ensure deterministic evidence and provenance validation passes completely
    val_res = validate_report_evidence(standard_report, canonical_stress_evidence, parsed_stress_statement)
    assert val_res.passed is True, f"Evidence validation errors: {val_res.errors}"
    assert val_res.provenance_failures == []
    assert len(val_res.verified_transaction_ids) > 0
    assert len(val_res.unverified_transaction_ids) == 0
