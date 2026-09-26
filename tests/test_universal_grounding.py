"""Universal Report Grounding & Evidence Integrity Regression Tests (Criteria A through O).

Verifies Section 23 of Master Prompt:
A. Direction preservation (CREDIT remains CREDIT, DEBIT remains DEBIT)
B. Transaction ID preservation (No transaction becomes "-")
C. Amount preservation (Rendered amount == canonical amount)
D. Date preservation (Rendered date == canonical date)
E. Counterparty preservation (Rendered counterparty exists in canonical evidence)
F. Anomaly provenance (Every anomaly ID exists in canonical anomaly findings)
G. Rule provenance (Every rule transaction exists in canonical rule findings)
H. Profile reconciliation (Report totals match source data; invariants strictly enforced)
I. Network grounding (Every transaction-derived network entity exists in source evidence)
J. Human-review grounding (Every human review item exists in canonical evidence)
K. Unsupported entity rejection (LLM mentioning unknown entity fails validation)
L. Unsupported transaction rejection (LLM mentioning nonexistent transaction ID fails validation)
M. Direction contradiction rejection (LLM calling a credit a debit fails validation)
N. Count contradiction rejection (LLM miscounting rules/anomalies fails validation)
O. Duplicate report prevention (Final report contains only one canonical report)
"""

from pathlib import Path
import re
import pytest

from aml_copilot.agents.critic import evaluate_investigation_draft
from aml_copilot.agents.state import InvestigationResult
from aml_copilot.exceptions import ReportReconciliationError
from aml_copilot.models.evidence import (
    CanonicalEvidence,
    CanonicalTransaction,
    build_canonical_evidence,
    reconcile_customer_profile,
)
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.reporting.formatter import format_report_markdown
from aml_copilot.reporting.generator import generate_investigation_report
from aml_copilot.reporting.validation import validate_report_evidence
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_parser import parse_transactions

STRESS_STATEMENT_PATH = Path("data/statements/ultimate_publish_stress_statement.pdf")


@pytest.fixture(scope="module")
def canonical_statement() -> TransactionStatement:
    """Load and parse stress statement."""
    assert STRESS_STATEMENT_PATH.exists(), f"Missing statement at {STRESS_STATEMENT_PATH}"
    doc = extract_pdf_text(str(STRESS_STATEMENT_PATH))
    statement = parse_transactions(doc)
    assert len(statement.transactions) == 54
    return statement


@pytest.fixture(scope="module")
def canonical_evidence(canonical_statement: TransactionStatement) -> CanonicalEvidence:
    """Build universal canonical evidence from statement."""
    return build_canonical_evidence(canonical_statement)


@pytest.fixture(scope="module")
def generated_report(canonical_statement: TransactionStatement, canonical_evidence: CanonicalEvidence):
    """Generate canonical investigation report."""
    inv = InvestigationResult(
        question="Comprehensive universal grounding regression audit",
        response="Objective investigation findings based on canonical statement evidence.",
    )
    return generate_investigation_report(
        statement=canonical_statement,
        investigation=inv,
        canonical_evidence=canonical_evidence,
    )


# Test A: Direction preservation
def test_a_direction_preservation(generated_report, canonical_statement: TransactionStatement):
    """CREDIT remains CREDIT. DEBIT remains DEBIT in both ReportDTO and rendered report."""
    stmt_txns = {t.transaction_id: t for t in canonical_statement.transactions}
    dto = generated_report.report_dto
    assert dto is not None, "ReportDTO must be present"

    for ctx in dto.transactions.canonical_transactions:
        orig = stmt_txns[ctx.transaction_id]
        expected_dir = "credit" if orig.credit is not None else "debit"
        assert ctx.direction == expected_dir, (
            f"Direction mismatch for {ctx.transaction_id}: {ctx.direction} != {expected_dir}"
        )

    for ev in generated_report.observed_evidence:
        orig = stmt_txns[ev.transaction_id]
        expected_dir = "credit" if orig.credit is not None else "debit"
        assert ev.flow_type.lower() == expected_dir


# Test B: Transaction ID preservation
def test_b_transaction_id_preservation(generated_report):
    """No transaction becomes '-' in ReportDTO or observed evidence."""
    dto = generated_report.report_dto
    assert dto is not None
    for ctx in dto.transactions.canonical_transactions:
        assert ctx.transaction_id and ctx.transaction_id != "-", "Transaction ID cannot be empty or '-'"
    for ev in generated_report.observed_evidence:
        assert ev.transaction_id and ev.transaction_id != "-"


# Test C: Amount preservation
def test_c_amount_preservation(generated_report, canonical_statement: TransactionStatement):
    """Rendered amount equals canonical amount."""
    stmt_txns = {t.transaction_id: t for t in canonical_statement.transactions}
    dto = generated_report.report_dto
    assert dto is not None
    for ctx in dto.transactions.canonical_transactions:
        orig = stmt_txns[ctx.transaction_id]
        expected_amt = orig.credit if orig.credit is not None else orig.debit
        assert abs(ctx.amount - expected_amt) < 0.01

    for ev in generated_report.observed_evidence:
        orig = stmt_txns[ev.transaction_id]
        expected_amt = orig.credit if orig.credit is not None else orig.debit
        assert abs(ev.amount - expected_amt) < 0.01


# Test D: Date preservation
def test_d_date_preservation(generated_report, canonical_statement: TransactionStatement):
    """Rendered date equals canonical date."""
    stmt_txns = {t.transaction_id: t for t in canonical_statement.transactions}
    dto = generated_report.report_dto
    assert dto is not None
    for ctx in dto.transactions.canonical_transactions:
        orig = stmt_txns[ctx.transaction_id]
        assert str(ctx.date) == str(orig.date)


# Test E: Counterparty preservation
def test_e_counterparty_preservation(generated_report, canonical_statement: TransactionStatement):
    """Rendered counterparty exists in canonical evidence."""
    stmt_cps = {t.counterparty.strip().lower() for t in canonical_statement.transactions if t.counterparty}
    dto = generated_report.report_dto
    assert dto is not None
    for ctx in dto.transactions.canonical_transactions:
        if ctx.counterparty:
            assert ctx.counterparty.strip().lower() in stmt_cps


# Test F: Anomaly provenance
def test_f_anomaly_provenance(generated_report, canonical_evidence: CanonicalEvidence):
    """Every anomaly ID in report exists in canonical anomaly findings."""
    canonical_anom_ids = set(canonical_evidence.anomaly_transaction_ids)
    for af in generated_report.anomaly_findings:
        assert af.transaction_id in canonical_anom_ids, (
            f"Anomaly ID {af.transaction_id} not in canonical anomaly findings"
        )


# Test G: Rule provenance
def test_g_rule_provenance(generated_report, canonical_evidence: CanonicalEvidence):
    """Every rule transaction exists in canonical rule findings."""
    canonical_rule_map = {}
    for rf in canonical_evidence.rule_findings:
        canonical_rule_map.setdefault(rf.rule_id, set()).update(rf.supporting_transaction_ids)

    for df in generated_report.detection_findings:
        assert df.rule_id in canonical_rule_map
        for tid in df.supporting_transaction_ids:
            assert tid in canonical_rule_map[df.rule_id]


# Test H: Profile reconciliation
def test_h_profile_reconciliation(canonical_statement: TransactionStatement, canonical_evidence: CanonicalEvidence):
    """Report totals exactly match source transaction data, and deliberate discrepancy raises ReportReconciliationError."""
    # Strict reconciliation passes on clean evidence
    assert reconcile_customer_profile(canonical_evidence.customer_profile, canonical_evidence.canonical_transactions)

    # Deliberate discrepancy raises ReportReconciliationError
    from aml_copilot.models.evidence import CanonicalProfile
    corrupt_profile = CanonicalProfile(
        transaction_count=canonical_evidence.customer_profile.transaction_count + 5,  # Mismatch!
        total_credits=canonical_evidence.customer_profile.total_credits,
        total_debits=canonical_evidence.customer_profile.total_debits,
        net_flow=canonical_evidence.customer_profile.net_flow,
        average_transaction=canonical_evidence.customer_profile.average_transaction,
        unique_counterparties=canonical_evidence.customer_profile.unique_counterparties,
        peak_credit=canonical_evidence.customer_profile.peak_credit,
        peak_debit=canonical_evidence.customer_profile.peak_debit,
        active_days=canonical_evidence.customer_profile.active_days,
    )
    with pytest.raises(ReportReconciliationError):
        reconcile_customer_profile(corrupt_profile, canonical_evidence.canonical_transactions)


# Test I: Network grounding
def test_i_network_grounding(canonical_statement: TransactionStatement, canonical_evidence: CanonicalEvidence):
    """Every transaction-derived network entity exists in source evidence."""
    stmt_cps = {t.counterparty.strip().upper() for t in canonical_statement.transactions if t.counterparty}
    for nf in canonical_evidence.network_findings:
        for node in nf.involved_nodes:
            # Involved nodes must be either customer name or statement counterparty
            assert node.strip().upper() in stmt_cps or node.strip().upper() == canonical_statement.customer_name.strip().upper()


# Test J: Human-review grounding
def test_j_human_review_grounding(generated_report, canonical_evidence: CanonicalEvidence):
    """Every human-review item exists in canonical evidence."""
    canonical_hr_ids = {item.transaction_id for item in canonical_evidence.human_review_items}
    for hr in generated_report.human_review_items:
        tid = hr.transaction_id if hasattr(hr, "transaction_id") else hr.get("transaction_id")
        assert tid in canonical_hr_ids


# Test K: Unsupported entity rejection
def test_k_unsupported_entity_rejection(canonical_statement: TransactionStatement, canonical_evidence: CanonicalEvidence):
    """An LLM mentioning an entity absent from canonical/reference evidence must fail validation."""
    draft_with_unsupported_entity = (
        "Investigation observed unusual transactions involving BOGUS OFFSHORE SHELL CORP and SHADY GLOBAL ENTERPRISES. "
        "Review of TXN401 indicates rapid fund flow."
    )
    res = evaluate_investigation_draft(
        draft_text=draft_with_unsupported_entity,
        statement=canonical_statement,
        canonical_evidence=canonical_evidence,
    )
    assert not res.passed
    assert any("BOGUS OFFSHORE SHELL CORP" in err or "Unsupported entity" in err for err in res.issues)


# Test L: Unsupported transaction rejection
def test_l_unsupported_transaction_rejection(canonical_statement: TransactionStatement, canonical_evidence: CanonicalEvidence):
    """An LLM mentioning a nonexistent transaction ID must fail validation."""
    draft_with_fake_tid = (
        "Transaction TXN9999 was flagged as an Isolation Forest statistical outlier with high risk."
    )
    res = evaluate_investigation_draft(
        draft_text=draft_with_fake_tid,
        statement=canonical_statement,
        canonical_evidence=canonical_evidence,
    )
    assert not res.passed
    assert any("TXN9999" in err for err in res.issues)


# Test M: Direction contradiction rejection
def test_m_direction_contradiction_rejection(canonical_statement: TransactionStatement, canonical_evidence: CanonicalEvidence):
    """If LLM claims a debit was a credit, critic must flag the contradiction."""
    # Find a debit transaction
    debit_tx = next(t for t in canonical_statement.transactions if t.debit is not None and t.credit is None)
    tid = debit_tx.transaction_id

    draft_with_wrong_dir = f"Transaction {tid} was a credit of ₹{debit_tx.debit:,.2f} received from counterparty."
    res = evaluate_investigation_draft(
        draft_text=draft_with_wrong_dir,
        statement=canonical_statement,
        canonical_evidence=canonical_evidence,
    )
    assert not res.passed
    assert any("Direction mismatch" in err or "Direction contradiction" in err for err in res.issues)


# Test N: Count contradiction rejection
def test_n_count_contradiction_rejection(canonical_statement: TransactionStatement, canonical_evidence: CanonicalEvidence):
    """If canonical rule count is 16 and LLM says 32, critic must flag the contradiction."""
    actual_rules = len(canonical_evidence.rule_findings)
    fake_rule_count = actual_rules + 16

    draft_with_wrong_count = f"During the screening period, exactly {fake_rule_count} rules were triggered across customer transactions."
    res = evaluate_investigation_draft(
        draft_text=draft_with_wrong_count,
        statement=canonical_statement,
        canonical_evidence=canonical_evidence,
    )
    assert not res.passed
    assert any("Count contradiction" in err for err in res.issues)


# Test O: Duplicate report prevention
def test_o_duplicate_report_prevention(generated_report):
    """Final report markdown must contain only one '# AML Investigation Report' header."""
    md = generated_report.to_markdown()
    headers = re.findall(r"^#\s+AML\s+Investigation\s+Report", md, flags=re.MULTILINE | re.IGNORECASE)
    assert len(headers) == 1, f"Expected exactly 1 title header, found {len(headers)}"
