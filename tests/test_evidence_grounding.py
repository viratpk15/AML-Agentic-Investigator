"""Regression test suite for AML evidence grounding, provenance, and critic audits.

Tests all 12 required verification criteria from the final correction specification:
TEST 1: Final report anomaly IDs exactly match Isolation Forest output.
TEST 2: TXN402 cannot appear as an Isolation Forest anomaly unless explicitly in anomaly_results.
TEST 3: TXN403 cannot appear as an Isolation Forest anomaly unless explicitly present.
TEST 4: Rule-specific transaction provenance verification.
TEST 5: Human Review items have valid supporting finding IDs.
TEST 6: Every report transaction ID exists in source statement.
TEST 7: Every report detection claim maps to correct detection source.
TEST 8: Critic FAILS when valid transaction ID is assigned to wrong detection source.
TEST 9: Critic PASSES when provenance is correct.
TEST 10: No report evidence selected using positional ordering.
TEST 11: Large-transaction wording distinguishes absolute threshold from median-relative.
TEST 12: Complete 54-transaction integration test.
"""

from pathlib import Path
import pytest

from aml_copilot.agents.critic import evaluate_investigation_draft
from aml_copilot.agents.state import InvestigationResult
from aml_copilot.ml.rules import RuleConfig, RuleEngine
from aml_copilot.models.evidence import (
    CanonicalEvidence,
    build_canonical_evidence,
    select_human_review_items,
)
from aml_copilot.models.transaction import TransactionStatement
from aml_copilot.reporting.generator import generate_investigation_report
from aml_copilot.reporting.models import AnomalyFindingItem, DetectionFindingItem
from aml_copilot.reporting.validation import validate_report_evidence
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_parser import parse_transactions

STRESS_STATEMENT_PATH = Path("data/statements/ultimate_publish_stress_statement.pdf")


@pytest.fixture(scope="module")
def stress_statement() -> TransactionStatement:
    """Load and parse the 54-transaction stress statement once for all regression tests."""
    assert STRESS_STATEMENT_PATH.exists(), f"Statement PDF not found at {STRESS_STATEMENT_PATH}"
    doc = extract_pdf_text(str(STRESS_STATEMENT_PATH))
    statement = parse_transactions(doc)
    assert len(statement.transactions) == 54, f"Expected 54 transactions, got {len(statement.transactions)}"
    return statement


@pytest.fixture(scope="module")
def stress_evidence(stress_statement: TransactionStatement) -> CanonicalEvidence:
    """Build canonical structured evidence for the 54-transaction statement."""
    return build_canonical_evidence(stress_statement)


def test_1_final_report_anomaly_ids_match_exact_isolation_forest(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 1: Given anomaly results: TXN401, TXN404, TXN434, TXN442, TXN445, TXN451,

    verify final report anomaly IDs are exactly those IDs.
    """
    expected_anomalies = ["TXN401", "TXN404", "TXN434", "TXN442", "TXN445", "TXN451"]
    actual_anomalies = sorted(stress_evidence.anomaly_transaction_ids)
    assert actual_anomalies == sorted(expected_anomalies), (
        f"Expected Isolation Forest anomaly IDs {expected_anomalies}, got {actual_anomalies}"
    )

    inv_result = InvestigationResult(
        question="Investigate anomalies",
        response=f"Isolation Forest flagged {', '.join(expected_anomalies)}.",
        canonical_evidence=stress_evidence,
    )
    report = generate_investigation_report(stress_statement, inv_result, canonical_evidence=stress_evidence)
    report_anomaly_ids = sorted([af.transaction_id for af in report.anomaly_findings])
    assert report_anomaly_ids == sorted(expected_anomalies), (
        f"Report anomaly IDs {report_anomaly_ids} do not match expected {expected_anomalies}"
    )


def test_2_txn402_cannot_appear_as_isolation_forest_anomaly(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 2: Verify TXN402 cannot appear as an Isolation Forest anomaly unless explicitly present."""
    assert "TXN402" not in stress_evidence.anomaly_transaction_ids

    # 1. Critic check
    critic_res = evaluate_investigation_draft(
        draft_text="Isolation Forest flagged TXN402 as a statistical anomaly.",
        statement=stress_statement,
        canonical_evidence=stress_evidence,
    )
    assert not critic_res.passed, "Critic must fail when TXN402 is claimed as an anomaly"
    assert any("TXN402" in issue and "anomaly" in issue.lower() for issue in critic_res.issues)

    # 2. Report validation check
    inv_result = InvestigationResult(question="q", response="r", canonical_evidence=stress_evidence)
    report = generate_investigation_report(stress_statement, inv_result, canonical_evidence=stress_evidence)
    # inject false claim
    report.anomaly_findings.append(AnomalyFindingItem(transaction_id="TXN402", anomaly_score=0.99, is_anomaly=True))
    val_res = validate_report_evidence(report, stress_evidence, stress_statement)
    assert not val_res.passed
    assert any("TXN402" in err and "Isolation Forest" in err for err in val_res.errors)


def test_3_txn403_cannot_appear_as_isolation_forest_anomaly(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 3: Verify TXN403 cannot appear as an Isolation Forest anomaly unless explicitly present."""
    assert "TXN403" not in stress_evidence.anomaly_transaction_ids

    # 1. Critic check
    critic_res = evaluate_investigation_draft(
        draft_text="Statistical outlier detection identified TXN403.",
        statement=stress_statement,
        canonical_evidence=stress_evidence,
    )
    assert not critic_res.passed, "Critic must fail when TXN403 is claimed as an anomaly"
    assert any("TXN403" in issue for issue in critic_res.issues)

    # 2. Report validation check
    inv_result = InvestigationResult(question="q", response="r", canonical_evidence=stress_evidence)
    report = generate_investigation_report(stress_statement, inv_result, canonical_evidence=stress_evidence)
    report.anomaly_findings.append(AnomalyFindingItem(transaction_id="TXN403", anomaly_score=0.95, is_anomaly=True))
    val_res = validate_report_evidence(report, stress_evidence, stress_statement)
    assert not val_res.passed
    assert any("TXN403" in err for err in val_res.errors)


def test_4_rule_specific_transaction_provenance(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 4: Verify rule-specific transaction provenance."""
    # Find all transactions triggering RULE_LARGE_TRANSACTION
    large_txn_rule = next(
        (rf for rf in stress_evidence.rule_findings if rf.rule_id == "RULE_LARGE_TRANSACTION"), None
    )
    assert large_txn_rule is not None
    supporting_tids = set(large_txn_rule.supporting_transaction_ids)

    # Pick a transaction that is NOT in this rule
    non_large_txns = [
        t.transaction_id for t in stress_statement.transactions
        if t.transaction_id and t.transaction_id not in supporting_tids
    ]
    assert len(non_large_txns) > 0
    fake_tid = non_large_txns[0]

    # Report validation with false rule claim must fail
    inv_result = InvestigationResult(question="q", response="r", canonical_evidence=stress_evidence)
    report = generate_investigation_report(stress_statement, inv_result, canonical_evidence=stress_evidence)
    report.detection_findings.append(
        DetectionFindingItem(
            rule_id="RULE_LARGE_TRANSACTION",
            rule_name="Unusually Large Transaction",
            severity="HIGH",
            explanation="Test",
            supporting_transaction_ids=[fake_tid],
        )
    )
    val_res = validate_report_evidence(report, stress_evidence, stress_statement)
    assert not val_res.passed
    assert any(fake_tid in err and "RULE_LARGE_TRANSACTION" in err for err in val_res.errors)


def test_5_human_review_transactions_have_supporting_finding_ids(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 5: Verify Human Review transactions have supporting finding IDs and valid reasons."""
    items = stress_evidence.human_review_items
    assert len(items) > 0

    for item in items:
        assert item.transaction_id.startswith("TXN")
        assert len(item.reasons) > 0, f"{item.transaction_id} has no documented reasons"
        assert len(item.supporting_finding_ids) > 0, f"{item.transaction_id} has no supporting finding IDs"
        assert item.priority in ["HIGH", "MEDIUM", "LOW"]
        # Verify transaction actually exists in statement
        stmt_txn = next((t for t in stress_statement.transactions if t.transaction_id == item.transaction_id), None)
        assert stmt_txn is not None
        assert item.amount is not None


def test_6_every_report_transaction_id_exists_in_source(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 6: Verify every report transaction ID exists in source transactions."""
    inv_result = InvestigationResult(
        question="Investigate unusual fund movements",
        response="Investigative review completed.",
        canonical_evidence=stress_evidence,
    )
    report = generate_investigation_report(stress_statement, inv_result, canonical_evidence=stress_evidence)
    val_res = validate_report_evidence(report, stress_evidence, stress_statement)
    assert val_res.passed, f"Report validation failed: {val_res.errors}"
    assert len(val_res.unverified_transaction_ids) == 0

    stmt_tids = {t.transaction_id for t in stress_statement.transactions if t.transaction_id}
    for ev in report.observed_evidence:
        assert ev.transaction_id in stmt_tids
        assert ev.verified_in_statement is True


def test_7_every_report_detection_claim_maps_to_correct_source(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 7: Verify every report detection claim maps to the correct detection source."""
    inv_result = InvestigationResult(
        question="Investigate",
        response=f"Isolation Forest flagged {', '.join(stress_evidence.anomaly_transaction_ids)}.",
        canonical_evidence=stress_evidence,
    )
    report = generate_investigation_report(stress_statement, inv_result, canonical_evidence=stress_evidence)
    val_res = validate_report_evidence(report, stress_evidence, stress_statement)
    assert val_res.passed
    assert len(val_res.provenance_failures) == 0


def test_8_critic_fails_when_valid_transaction_assigned_to_wrong_detection_source(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 8: Verify critic FAILS when a valid transaction ID is assigned to the wrong detection source."""
    # TXN402 exists in the statement, but was NOT an Isolation Forest anomaly
    assert any(t.transaction_id == "TXN402" for t in stress_statement.transactions)
    assert "TXN402" not in stress_evidence.anomaly_transaction_ids

    draft_text = (
        "During unsupervised screening, Isolation Forest flagged TXN402 as an anomalous transaction."
    )
    critic_res = evaluate_investigation_draft(
        draft_text=draft_text,
        statement=stress_statement,
        canonical_evidence=stress_evidence,
    )
    assert not critic_res.passed
    assert any("TXN402" in issue and "anomaly" in issue.lower() for issue in critic_res.issues)


def test_9_critic_passes_when_provenance_is_correct(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 9: Verify critic PASSES when provenance is correct."""
    anoms = stress_evidence.anomaly_transaction_ids
    # Grounded factual draft
    draft_text = (
        f"The investigation evaluated the account activity. "
        f"Isolation Forest anomaly screening flagged statistical outlier transactions: {', '.join(anoms)}. "
        f"Unusual activity was observed requiring compliance review."
    )
    critic_res = evaluate_investigation_draft(
        draft_text=draft_text,
        statement=stress_statement,
        canonical_evidence=stress_evidence,
    )
    assert critic_res.passed, f"Critic failed on correct provenance: {critic_res.issues}"
    assert len(critic_res.unsupported_claims) == 0


def test_10_no_report_evidence_selected_using_positional_ordering(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 10: Verify no report evidence is selected using positional ordering."""
    items = select_human_review_items(
        statement=stress_statement,
        rule_findings=stress_evidence.rule_findings,
        statistical_anomalies=stress_evidence.statistical_anomalies,
        network_findings=stress_evidence.network_findings,
    )
    item_ids = [item.transaction_id for item in items]
    statement_order_ids = [t.transaction_id for t in stress_statement.transactions]

    # Verify that the prioritized items are NOT simply statement order (e.g., TXN401, TXN402, TXN403...)
    # In fact, TXN445 and TXN434 have the highest signal convergence and rank at the top
    assert item_ids[:2] == ["TXN445", "TXN434"], (
        f"Expected top converged items TXN445 and TXN434, got {item_ids[:2]}"
    )
    assert item_ids[:6] != statement_order_ids[:6], (
        "Human review items must not match positional statement order"
    )


def test_11_large_transaction_wording_distinguishes_absolute_from_median(
    stress_statement: TransactionStatement
):
    """TEST 11: Verify large-transaction wording distinguishes absolute threshold from median-relative threshold."""
    # Test with custom rule engine
    engine = RuleEngine(RuleConfig(large_transaction_abs_threshold=100_000.0, large_transaction_multiplier=4.0))
    signals = engine.evaluate(stress_statement)
    large_signals = [s for s in signals if s.rule_id == "RULE_LARGE_TRANSACTION"]
    assert len(large_signals) > 0

    # For TXN401: amount is 102,500, customer median is 129,000. Amount < median
    txn401_signal = next((s for s in large_signals if "TXN401" in s.transaction_ids), None)
    assert txn401_signal is not None
    assert "below the customer's median transaction amount" in txn401_signal.explanation
    assert "exceeded the configured absolute transaction threshold" in txn401_signal.explanation
    assert "0.8x" not in txn401_signal.explanation or "unusually large" not in txn401_signal.explanation


def test_12_complete_54_transaction_integration_test(
    stress_statement: TransactionStatement, stress_evidence: CanonicalEvidence
):
    """TEST 12: Run complete 54-transaction integration validation on the final report."""
    inv_result = InvestigationResult(
        question="Investigate unusual movement of funds in this account and highlight transactions requiring human review.",
        response=(
            f"Investigation concluded. Isolation Forest identified statistical outlier transactions: "
            f"{', '.join(stress_evidence.anomaly_transaction_ids)}. Multiple deterministic rule triggers "
            f"were identified including large transactions, rapid pass-through fund flows, and volume surges. "
            f"Prioritized transactions have been highlighted for human compliance review."
        ),
        canonical_evidence=stress_evidence,
        tools_used=["detect_anomalies", "get_customer_profile", "analyze_transaction_network"],
    )

    report = generate_investigation_report(stress_statement, inv_result, canonical_evidence=stress_evidence)

    assert report.evidence_validation_passed is True
    assert report.critic_validation.passed is True
    assert len(report.anomaly_findings) == 6
    assert [af.transaction_id for af in report.anomaly_findings] == [
        "TXN401", "TXN404", "TXN434", "TXN442", "TXN445", "TXN451"
    ]
    assert len(report.human_review_items) < 54
    assert len(report.human_review_items) == 50
    assert report.human_review_items[0].transaction_id == "TXN445"
    assert report.human_review_items[1].transaction_id == "TXN434"
