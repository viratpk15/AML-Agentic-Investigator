"""Canonical Rule Finding Semantics Regression Tests.

Covers Phase 2-10 audit criteria from engineering quality audit:

A. Rapid Movement aggregation — finding_count vs associated_transaction_count
B. Event-level rule semantics (one finding per event/window)
C. Transaction-level rule semantics (one finding per transaction)
D. Severity reconciliation — finding_count == sum(severity_distribution.values())
E. associated_transaction_count != finding_count for EVENT_LEVEL
F. High Transaction Frequency — day-level event semantics
G. Interpretation cannot invent aggregate counts
H. Internal agent chatter rejection
I. Anomaly count grounding
J. Human-review queue reconciliation
K. Profile reconciliation
L. Network reconciliation
M. Unsupported entity validation
N. Critic catches report contradictions
O. Clean report passes all quality gates
P. Existing report behavior compatibility
"""

import datetime as dt
import pytest

from aml_copilot.agents.models import CritiqueResult
from aml_copilot.agents.state import InvestigationResult
from aml_copilot.models.evidence import build_canonical_evidence
from aml_copilot.models.findings import (
    FindingGranularity,
    granularity_for_rule,
)
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.reporting.generator import generate_investigation_report
from aml_copilot.reporting.formatter import format_report_markdown
from aml_copilot.reporting.validation import validate_report_evidence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_date(offset_days: int = 0) -> dt.date:
    return dt.date(2026, 9, 1) + dt.timedelta(days=offset_days)


def _make_txn(tid: str, credit=None, debit=None, offset_days: int = 0,
              cp: str = "COUNTERPARTY_A") -> Transaction:
    return Transaction(
        date=_make_date(offset_days),
        transaction_id=tid,
        description=f"Test transaction {tid}",
        credit=credit,
        debit=debit,
        balance=500_000.0,
        counterparty=cp,
    )


def _make_statement(txns, name="Test Customer", account="TEST001") -> TransactionStatement:
    return TransactionStatement(
        customer_name=name,
        account_number=account,
        statement_period="01 Sep 2026 - 30 Sep 2026",
        transactions=txns,
    )


def _make_investigation(response="Investigation complete.", **kwargs) -> InvestigationResult:
    defaults = dict(
        question="Investigate unusual movement of funds.",
        response=response,
        tools_used=[],
        tool_calls=[],
        referenced_transaction_ids=[],
        knowledge_sources=[],
        critic_result=CritiqueResult(
            passed=True, issues=[], missing_evidence=[], unsupported_claims=[],
            required_revisions=[], checked_transaction_ids=[],
            invalid_transaction_ids=[], safety_violations=[],
            statement_transaction_count=0, narrative_transaction_reference_count=0,
            human_review_transaction_count=0, verified_transaction_reference_count=0,
            unverified_transaction_reference_count=0,
        ),
        critic_status="PASS",
        revision_count=0,
        limitations_warnings=[],
    )
    defaults.update(kwargs)
    return InvestigationResult(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def stress_statement():
    from pathlib import Path
    from aml_copilot.services.pdf_parser import extract_pdf_text
    from aml_copilot.services.transaction_parser import parse_transactions
    for candidate in [
        "data/statements/Virat_AML_Production_E2E_Stress_Statement.pdf",
        "data/statements/ultimate_publish_stress_statement.pdf",
    ]:
        p = Path(candidate)
        if p.exists():
            doc = extract_pdf_text(p)
            return parse_transactions(doc)
    pytest.skip("No stress statement PDF found")


@pytest.fixture(scope="module")
def stress_evidence(stress_statement):
    return build_canonical_evidence(stress_statement)


@pytest.fixture(scope="module")
def stress_report(stress_statement, stress_evidence):
    inv = _make_investigation(
        response=(
            "The account exhibits high-velocity commercial fund flow patterns. "
            "Deterministic screening identified signals across the configured rules. "
            "Isolation Forest flagged statistical outliers. "
            "Multi-signal convergence items prioritized for human review."
        ),
        critic_result=CritiqueResult(
            passed=True, issues=[], missing_evidence=[], unsupported_claims=[],
            required_revisions=[], checked_transaction_ids=[],
            invalid_transaction_ids=[], safety_violations=[],
            statement_transaction_count=stress_statement.total_transactions,
            narrative_transaction_reference_count=0,
            human_review_transaction_count=0,
            verified_transaction_reference_count=0,
            unverified_transaction_reference_count=0,
        ),
        critic_status="PASS",
    )
    return generate_investigation_report(
        statement=stress_statement,
        investigation=inv,
        canonical_evidence=stress_evidence,
    )


# ===========================================================================
# A. Rapid Movement Aggregation
# ===========================================================================

def test_a_rapid_movement_severity_invariant(stress_report):
    """A. RAPID_MOVEMENT: finding_count == sum(severity_distribution)."""
    for rsg in stress_report.rule_summary_groups:
        if rsg.rule_id == "RULE_RAPID_MOVEMENT_OF_FUNDS":
            sev_sum = sum(rsg.severity_distribution.values())
            assert rsg.finding_count == sev_sum, (
                f"finding_count={rsg.finding_count} != sev_sum={sev_sum}. "
                f"Distribution: {dict(rsg.severity_distribution)}"
            )
            return
    pytest.skip("RULE_RAPID_MOVEMENT_OF_FUNDS not triggered")


def test_a_rapid_movement_associated_txn_gte_finding_count(stress_report):
    """A. RAPID_MOVEMENT: associated_transaction_count >= finding_count."""
    for rsg in stress_report.rule_summary_groups:
        if rsg.rule_id == "RULE_RAPID_MOVEMENT_OF_FUNDS":
            assert rsg.associated_transaction_count >= rsg.finding_count
            return
    pytest.skip("RULE_RAPID_MOVEMENT_OF_FUNDS not triggered")


# ===========================================================================
# B. Event-Level Rule Semantics
# ===========================================================================

def test_b_event_level_rules_registered():
    """B. All EVENT_LEVEL rules are registered correctly."""
    event_rules = [
        "RULE_SUDDEN_VOLUME_INCREASE",
        "RULE_LARGE_INFLOW_RAPID_OUTFLOW",
        "RULE_RAPID_MOVEMENT_OF_FUNDS",
        "RULE_MANY_NEW_COUNTERPARTIES",
        "RULE_HIGH_TRANSACTION_FREQUENCY",
        "RULE_HIGH_STATEMENT_FREQUENCY",
    ]
    for rule_id in event_rules:
        assert granularity_for_rule(rule_id) == FindingGranularity.EVENT_LEVEL, (
            f"{rule_id} should be EVENT_LEVEL"
        )


def test_b_severity_invariant_all_rules(stress_report):
    """B. For ALL rule groups: finding_count == sum(severity_distribution)."""
    for rsg in stress_report.rule_summary_groups:
        sev_sum = sum(rsg.severity_distribution.values())
        assert rsg.finding_count == sev_sum, (
            f"Rule '{rsg.rule_id}': finding_count={rsg.finding_count} != sev_sum={sev_sum}. "
            f"Distribution: {dict(rsg.severity_distribution)}"
        )


def test_b_synthetic_event_level_aggregation():
    """B. Synthetic: 2 separate windows -> 2 events, not 10 (5 txns each)."""
    txns = [
        _make_txn("T001", credit=500_000, offset_days=0),
        _make_txn("T002", debit=200_000, offset_days=0),
        _make_txn("T003", debit=200_000, offset_days=1),
        _make_txn("T004", debit=80_000, offset_days=2),
        _make_txn("T005", credit=400_000, offset_days=5),
        _make_txn("T006", debit=180_000, offset_days=5),
        _make_txn("T007", debit=150_000, offset_days=6),
        _make_txn("T008", debit=60_000, offset_days=7),
        _make_txn("T009", credit=300_000, offset_days=10),
        _make_txn("T010", debit=50_000, offset_days=11, cp="CP_B"),
    ]
    stmt = _make_statement(txns)
    evidence = build_canonical_evidence(stmt)
    report = generate_investigation_report(stmt, _make_investigation(), canonical_evidence=evidence)
    for rsg in report.rule_summary_groups:
        sev_sum = sum(rsg.severity_distribution.values())
        assert rsg.finding_count == sev_sum, (
            f"Synthetic: Rule '{rsg.rule_id}' finding_count={rsg.finding_count} != sev_sum={sev_sum}"
        )


# ===========================================================================
# C. Transaction-Level Rule Semantics
# ===========================================================================

def test_c_large_transaction_is_transaction_level():
    """C. RULE_LARGE_TRANSACTION must be TRANSACTION_LEVEL."""
    assert granularity_for_rule("RULE_LARGE_TRANSACTION") == FindingGranularity.TRANSACTION_LEVEL


def test_c_transaction_level_finding_equals_txn_count(stress_report):
    """C. RULE_LARGE_TRANSACTION: finding_count == associated_transaction_count."""
    for rsg in stress_report.rule_summary_groups:
        if rsg.rule_id == "RULE_LARGE_TRANSACTION":
            assert rsg.finding_count == rsg.associated_transaction_count, (
                f"TRANSACTION_LEVEL rule should have finding_count == associated_transaction_count. "
                f"Got finding_count={rsg.finding_count}, assoc={rsg.associated_transaction_count}"
            )
            return
    pytest.skip("RULE_LARGE_TRANSACTION not triggered")


def test_c_formatter_uses_transaction_label_for_txn_level(stress_report):
    """C. TRANSACTION_LEVEL rules display 'transaction(s)' in formatted markdown."""
    md = format_report_markdown(stress_report)
    assert "transaction(s)" in md


# ===========================================================================
# D. Severity Reconciliation Invariant
# ===========================================================================

def test_d_severity_invariant_global(stress_report):
    """D. finding_count == sum(severity_distribution.values()) for EVERY rule group."""
    for rsg in stress_report.rule_summary_groups:
        sev_sum = sum(rsg.severity_distribution.values())
        assert rsg.finding_count == sev_sum, (
            f"INVARIANT VIOLATED: Rule '{rsg.rule_id}' finding_count={rsg.finding_count} "
            f"!= sev_sum={sev_sum}. Distribution: {dict(rsg.severity_distribution)}"
        )


def test_d_validator_catches_corrupted_severity(stress_statement, stress_evidence):
    """D. Validator must fail when severity distribution is manually corrupted."""
    report = generate_investigation_report(
        stress_statement, _make_investigation(), canonical_evidence=stress_evidence
    )
    if not report.rule_summary_groups:
        pytest.skip("No rule summary groups")
    # Corrupt the first group's severity
    rsg = report.rule_summary_groups[0]
    rsg.severity_distribution["HIGH"] = rsg.finding_count + 99
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    assert not val.passed, "Validator must fail on corrupted severity distribution"
    assert any("severity" in e.lower() or "invariant" in e.lower() for e in val.errors)


# ===========================================================================
# E. associated_transaction_count != finding_count for EVENT_LEVEL
# ===========================================================================

def test_e_event_level_assoc_gte_finding(stress_report):
    """E. For EVENT_LEVEL rules: associated_transaction_count >= finding_count."""
    event_rules = {
        "RULE_LARGE_INFLOW_RAPID_OUTFLOW",
        "RULE_RAPID_MOVEMENT_OF_FUNDS",
        "RULE_MANY_NEW_COUNTERPARTIES",
    }
    for rsg in stress_report.rule_summary_groups:
        if rsg.rule_id in event_rules:
            assert rsg.associated_transaction_count >= rsg.finding_count, (
                f"Rule '{rsg.rule_id}': assoc={rsg.associated_transaction_count} "
                f"must be >= finding_count={rsg.finding_count}"
            )


# ===========================================================================
# F. High Transaction Frequency Semantics
# ===========================================================================

def test_f_high_freq_is_event_level():
    """F. RULE_HIGH_TRANSACTION_FREQUENCY is EVENT_LEVEL."""
    assert granularity_for_rule("RULE_HIGH_TRANSACTION_FREQUENCY") == FindingGranularity.EVENT_LEVEL


def test_f_high_freq_one_day_one_event():
    """F. 6 transactions on 1 day -> 1 event, 6 associated transactions."""
    txns = [_make_txn(f"HF{i:03d}", credit=10_000, offset_days=0, cp=f"CP_{i}") for i in range(6)]
    stmt = _make_statement(txns)
    evidence = build_canonical_evidence(stmt)
    report = generate_investigation_report(stmt, _make_investigation(), canonical_evidence=evidence)
    for rsg in report.rule_summary_groups:
        if rsg.rule_id == "RULE_HIGH_TRANSACTION_FREQUENCY":
            assert rsg.finding_count == 1, f"1 day -> 1 event. Got finding_count={rsg.finding_count}"
            assert rsg.associated_transaction_count == 6
            assert rsg.finding_count == sum(rsg.severity_distribution.values())
            return
    # Rule may not fire on small dataset
    pytest.skip("RULE_HIGH_TRANSACTION_FREQUENCY threshold not met")


def test_f_high_freq_two_days_two_events():
    """F. High-frequency transactions on 2 separate days -> 2 events."""
    txns = []
    for i in range(5):
        txns.append(_make_txn(f"HF1{i:02d}", credit=10_000, offset_days=0, cp=f"CP_A{i}"))
    for i in range(5):
        txns.append(_make_txn(f"HF2{i:02d}", credit=10_000, offset_days=5, cp=f"CP_B{i}"))
    stmt = _make_statement(txns)
    evidence = build_canonical_evidence(stmt)
    report = generate_investigation_report(stmt, _make_investigation(), canonical_evidence=evidence)
    for rsg in report.rule_summary_groups:
        if rsg.rule_id == "RULE_HIGH_TRANSACTION_FREQUENCY":
            assert rsg.finding_count == 2, (
                f"2 triggering days should be 2 events. Got finding_count={rsg.finding_count}"
            )
            assert rsg.associated_transaction_count == 10
            assert rsg.finding_count == sum(rsg.severity_distribution.values())
            return
    pytest.skip("RULE_HIGH_TRANSACTION_FREQUENCY threshold not met")


# ===========================================================================
# G. Interpretation Cannot Invent Counts
# ===========================================================================

def test_g_fabricated_rule_count_caught(stress_statement, stress_evidence):
    """G. Fabricated rule count in interpretation -> validator fails."""
    actual = len(stress_evidence.rule_findings)
    fake = actual + 99
    inv = _make_investigation(response=f"Deterministic screening identified {fake} rules were triggered.")
    report = generate_investigation_report(stress_statement, inv, canonical_evidence=stress_evidence)
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    count_errors = [e for e in val.errors if "count contradiction" in e.lower()]
    assert count_errors, f"Validator should catch fabricated count {fake} (actual={actual})"


def test_g_fabricated_anomaly_count_caught(stress_statement, stress_evidence):
    """G. Fabricated anomaly count in interpretation -> validator fails."""
    actual = len(stress_evidence.statistical_anomalies)
    fake = actual + 50
    inv = _make_investigation(
        response=f"Isolation Forest identified {fake} statistical anomalies."
    )
    report = generate_investigation_report(stress_statement, inv, canonical_evidence=stress_evidence)
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    count_errors = [e for e in val.errors if "count contradiction" in e.lower()]
    assert count_errors, f"Validator should catch fabricated anomaly count {fake}"


def test_g_grounded_interpretation_passes(stress_statement, stress_evidence):
    """G. Grounded interpretation with no invented numbers must pass validator."""
    inv = _make_investigation(
        response=(
            "The account exhibits high-velocity commercial fund flow patterns consistent with "
            "pass-through conduit typologies. Deterministic screening identified signals "
            "across the configured rules. Statistical outliers were flagged by Isolation Forest. "
            "Multi-signal convergence items have been prioritized for compliance officer review."
        ),
    )
    report = generate_investigation_report(stress_statement, inv, canonical_evidence=stress_evidence)
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    count_errors = [e for e in val.errors if "count contradiction" in e.lower()]
    assert not count_errors, f"Grounded interpretation should have no count contradictions: {count_errors}"


# ===========================================================================
# H. Internal Agent Chatter Rejection
# ===========================================================================

def test_h_i_need_to_rejected(stress_statement, stress_evidence):
    """H. 'I need to' in interpretation -> validator flags chatter."""
    inv = _make_investigation(response="I need to verify the transaction amounts before concluding.")
    report = generate_investigation_report(stress_statement, inv, canonical_evidence=stress_evidence)
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    chatter = [e for e in val.errors if "chatter" in e.lower()]
    assert chatter, "Validator must reject 'I need to' in report"


def test_h_let_me_verify_rejected(stress_statement, stress_evidence):
    """H. 'let me verify' in interpretation -> validator flags chatter."""
    inv = _make_investigation(response="Let me verify the evidence before making conclusions.")
    report = generate_investigation_report(stress_statement, inv, canonical_evidence=stress_evidence)
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    chatter = [e for e in val.errors if "chatter" in e.lower()]
    assert chatter, "Validator must reject 'let me verify'"


def test_h_critic_feedback_rejected(stress_statement, stress_evidence):
    """H. Critic feedback exposed in report -> validator flags chatter."""
    inv = _make_investigation(response="Critic feedback identified issues with the previous draft.")
    report = generate_investigation_report(stress_statement, inv, canonical_evidence=stress_evidence)
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    chatter = [e for e in val.errors if "chatter" in e.lower()]
    assert chatter, "Validator must reject critic feedback in final report"


def test_h_previous_draft_rejected(stress_statement, stress_evidence):
    """H. 'previous draft' in report -> validator flags chatter."""
    inv = _make_investigation(response="Based on the previous draft, I will correct the numbers.")
    report = generate_investigation_report(stress_statement, inv, canonical_evidence=stress_evidence)
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    chatter = [e for e in val.errors if "chatter" in e.lower()]
    assert chatter, "Validator must reject 'previous draft' in report"


def test_h_clean_interpretation_passes_chatter(stress_statement, stress_evidence):
    """H. Clean interpretation with no chatter -> no chatter errors."""
    inv = _make_investigation(
        response=(
            "High-velocity fund flow patterns observed. Compliance review is recommended "
            "for multi-signal convergence items. These findings are investigative risk "
            "indicators only and do not establish guilt."
        ),
    )
    report = generate_investigation_report(stress_statement, inv, canonical_evidence=stress_evidence)
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    chatter = [e for e in val.errors if "chatter" in e.lower()]
    assert not chatter, f"Clean interpretation should have no chatter errors: {chatter}"


# ===========================================================================
# I. Anomaly Count Grounding
# ===========================================================================

def test_i_anomaly_count_matches_canonical(stress_report, stress_evidence):
    """I. Report anomaly_findings count must match canonical."""
    assert len(stress_report.anomaly_findings) == len(stress_evidence.statistical_anomalies)


def test_i_anomaly_ids_match_canonical(stress_report, stress_evidence):
    """I. Report anomaly IDs must exactly match canonical."""
    canonical = {a.transaction_id for a in stress_evidence.statistical_anomalies}
    reported = {a.transaction_id for a in stress_report.anomaly_findings}
    assert reported == canonical, f"Anomaly IDs mismatch: report={reported}, canonical={canonical}"


def test_i_no_non_anomaly_in_report(stress_report, stress_evidence):
    """I. No non-anomaly transaction may appear in anomaly_findings."""
    canonical = {a.transaction_id for a in stress_evidence.statistical_anomalies}
    for af in stress_report.anomaly_findings:
        assert af.transaction_id in canonical, (
            f"'{af.transaction_id}' is NOT a canonical anomaly but appears in anomaly_findings"
        )


# ===========================================================================
# J. Human Review Queue Reconciliation
# ===========================================================================

def test_j_hr_count_matches_canonical(stress_report, stress_evidence):
    """J. Human review item count matches canonical evidence."""
    assert len(stress_report.human_review_items) == len(stress_evidence.human_review_items)


def test_j_priority_counts_sum_to_total(stress_report):
    """J. HIGH + MEDIUM + LOW == total prioritized_review_count."""
    hrs = stress_report.human_review_summary
    total = hrs.get("prioritized_review_count", 0)
    h = hrs.get("high_priority_count", 0)
    m = hrs.get("medium_priority_count", 0)
    low_count = hrs.get("low_priority_count", 0)
    assert h + m + low_count == total, f"Priority counts {h}+{m}+{low_count}={h+m+low_count} != total={total}"


def test_j_hr_txns_exist_in_statement(stress_report, stress_statement):
    """J. Every human review transaction must exist in statement."""
    stmt_ids = {t.transaction_id for t in stress_statement.transactions if t.transaction_id}
    for hr in stress_report.human_review_items:
        tid = getattr(hr, "transaction_id", None)
        assert tid in stmt_ids, f"Human review item '{tid}' not in statement"


# ===========================================================================
# K. Profile Reconciliation
# ===========================================================================

def test_k_profile_txn_count_matches_statement(stress_report, stress_statement):
    """K. Profile transaction count == statement total."""
    assert stress_report.customer_profile.total_transactions == stress_statement.total_transactions


def test_k_profile_credits_match(stress_report, stress_statement):
    """K. Profile total_credits matches sum of statement credits."""
    calc = round(sum(t.credit for t in stress_statement.transactions if t.credit), 2)
    assert abs(stress_report.customer_profile.total_credits - calc) < 0.05


def test_k_profile_debits_match(stress_report, stress_statement):
    """K. Profile total_debits matches sum of statement debits."""
    calc = round(sum(t.debit for t in stress_statement.transactions if t.debit), 2)
    assert abs(stress_report.customer_profile.total_debits - calc) < 0.05


def test_k_profile_net_flow_reconciles(stress_report, stress_statement):
    """K. Profile net_cash_flow == total_credits - total_debits."""
    calc_cr = sum(t.credit for t in stress_statement.transactions if t.credit)
    calc_db = sum(t.debit for t in stress_statement.transactions if t.debit)
    calc_net = round(calc_cr - calc_db, 2)
    assert abs(stress_report.customer_profile.net_cash_flow - calc_net) < 0.05


# ===========================================================================
# L. Network Reconciliation
# ===========================================================================

def test_l_profile_counterparties_match_network(stress_report):
    """L. Profile unique_counterparties == network unique_counterparties."""
    assert stress_report.customer_profile.unique_counterparties == \
           stress_report.network_summary.unique_counterparties


def test_l_graph_nodes_equals_counterparties_plus_one(stress_report):
    """L. graph_nodes == unique_counterparties + 1 (customer node)."""
    net_cp = stress_report.network_summary.unique_counterparties
    nodes = stress_report.network_summary.graph_nodes
    assert nodes == net_cp + 1, f"graph_nodes={nodes} should be {net_cp}+1={net_cp+1}"


# ===========================================================================
# M. Unsupported Entity Validation
# ===========================================================================

def test_m_fabricated_entity_caught(stress_statement, stress_evidence):
    """M. Fabricated entity name in interpretation must be caught by validator."""
    inv = _make_investigation(
        response=(
            "Significant transactions were identified with PHANTOM SHELL CORP OFFSHORE "
            "which does not appear in the statement records."
        ),
    )
    report = generate_investigation_report(stress_statement, inv, canonical_evidence=stress_evidence)
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    entity_errors = [e for e in val.errors if "unsupported entity" in e.lower()]
    assert entity_errors, (
        f"Validator should flag 'PHANTOM SHELL CORP OFFSHORE'. Errors: {val.errors}"
    )


# ===========================================================================
# N. Critic Catches Report Contradictions
# ===========================================================================

def test_n_wrong_severity_fails_validation(stress_statement, stress_evidence):
    """N. Corrupted severity distribution must fail validation."""
    report = generate_investigation_report(
        stress_statement, _make_investigation(), canonical_evidence=stress_evidence
    )
    if not report.rule_summary_groups:
        pytest.skip("No rule summary groups")
    rsg = report.rule_summary_groups[0]
    rsg.severity_distribution["HIGH"] = rsg.finding_count + 100
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    assert not val.passed


def test_n_non_existent_txn_in_evidence_caught(stress_statement, stress_evidence):
    """N. Non-existent transaction ID in observed evidence -> validation fails."""
    report = generate_investigation_report(
        stress_statement, _make_investigation(), canonical_evidence=stress_evidence
    )
    from aml_copilot.reporting.models import EvidenceItem
    report.observed_evidence.append(EvidenceItem(
        transaction_id="TXN_NONEXISTENT_9999",
        verified_in_statement=True,  # claiming verified when it is not
    ))
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    assert not val.passed, "Non-existent verified transaction should fail validation"


# ===========================================================================
# O. Clean Report Passes All Quality Gates
# ===========================================================================

def test_o_full_clean_report_passes_validation(stress_statement, stress_evidence):
    """O. Clean generation -> all validation checks pass."""
    inv = _make_investigation(
        response=(
            "Account exhibits high-velocity commercial fund flow consistent with "
            "pass-through conduit typologies. Deterministic screening identified signals "
            "across the configured rules. Statistical outliers were flagged by Isolation Forest. "
            "Multi-signal convergence items have been prioritized for human review. "
            "These findings are investigative risk indicators only."
        ),
    )
    report = generate_investigation_report(stress_statement, inv, canonical_evidence=stress_evidence)
    val = validate_report_evidence(report, stress_evidence, stress_statement)
    assert val.passed, "Clean report failed validation. Errors:\n" + "\n".join(val.errors)
    assert val.provenance_failures == []


def test_o_severity_invariant_clean_report(stress_statement, stress_evidence):
    """O. Clean report: finding_count == sum(severity_distribution) for ALL rules."""
    report = generate_investigation_report(
        stress_statement, _make_investigation(), canonical_evidence=stress_evidence
    )
    for rsg in report.rule_summary_groups:
        sev_sum = sum(rsg.severity_distribution.values())
        assert rsg.finding_count == sev_sum, (
            f"Rule '{rsg.rule_id}': finding_count={rsg.finding_count} != sev_sum={sev_sum}"
        )


# ===========================================================================
# P. Existing Report Behavior Compatibility
# ===========================================================================

def test_p_all_14_sections_present(stress_report):
    """P. All 14 report sections must be present in canonical order."""
    md = format_report_markdown(stress_report)
    for i in range(1, 15):
        assert f"## {i}." in md, f"Section {i} missing from report"


def test_p_statement_total_preserved(stress_report, stress_statement):
    """P. Total transactions analyzed equals statement count."""
    assert stress_report.total_transactions_analyzed == stress_statement.total_transactions


def test_p_legacy_count_equals_associated_txn_count(stress_report):
    """P. Legacy 'count' field must equal associated_transaction_count."""
    for rsg in stress_report.rule_summary_groups:
        assert rsg.count == rsg.associated_transaction_count, (
            f"Rule '{rsg.rule_id}': count={rsg.count} should equal "
            f"associated_transaction_count={rsg.associated_transaction_count}"
        )


def test_p_mandatory_disclaimer_present(stress_report):
    """P. Human review compliance disclaimer must always be present."""
    md = format_report_markdown(stress_report)
    assert "exclusive responsibility of qualified human compliance officers" in md


def test_p_report_dto_populated(stress_report):
    """P. ReportDTO must be populated with all canonical facts."""
    dto = stress_report.report_dto
    assert dto is not None
    assert dto.rules.total_rule_signals > 0
    assert dto.anomalies.total_anomalies > 0
    assert dto.transactions.total_transactions > 0
