"""Deterministic evidence provenance validator for AML Investigation Reports.

Enforces strict factual grounding:
1. Transaction existence: All cited transaction IDs must exist in the customer statement.
2. Anomaly provenance: Transactions claimed to be Isolation Forest anomalies must be present in canonical anomaly results.
3. Rule provenance: Transactions claimed to trigger a rule must be present in that rule's supporting transactions.
4. Human review provenance: Transactions recommended for human review must have valid documented reasons and finding IDs.
5. Factual correctness: Monetary amounts, dates, and flow directions must match statement records.
"""

import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from aml_copilot.models.evidence import CanonicalEvidence
from aml_copilot.models.transaction import TransactionStatement
from aml_copilot.reporting.models import InvestigationReport


class EvidenceValidationResult(BaseModel):
    """Validation report verifying evidence provenance of an investigation report."""

    passed: bool = Field(..., description="Whether all claims and transaction references have verified provenance")
    errors: List[str] = Field(default_factory=list, description="Fatal provenance violations or hallucinated claims")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal observations or limitations")
    verified_transaction_ids: List[str] = Field(
        default_factory=list, description="Transactions verified against statement records"
    )
    unverified_transaction_ids: List[str] = Field(
        default_factory=list, description="Transactions cited that do not exist in statement"
    )
    provenance_failures: List[str] = Field(
        default_factory=list, description="Claims where transaction exists but source attribution is incorrect"
    )


def validate_report_evidence(
    report: InvestigationReport,
    canonical_evidence: CanonicalEvidence,
    statement: TransactionStatement,
) -> EvidenceValidationResult:
    """Perform rigorous deterministic provenance verification on an InvestigationReport.

    Args:
        report: Final generated InvestigationReport.
        canonical_evidence: Canonical single source of truth evidence object.
        statement: Verified TransactionStatement.

    Returns:
        EvidenceValidationResult indicating pass/fail and listing any provenance errors.
    """
    errors: List[str] = []
    warnings: List[str] = []
    provenance_failures: List[str] = []
    verified_tids: Set[str] = set()
    unverified_tids: Set[str] = set()

    stmt_txns = {t.transaction_id: t for t in statement.transactions if t.transaction_id}
    canonical_anomaly_ids = set(canonical_evidence.anomaly_transaction_ids)

    # Build map of rule_id -> set of actual supporting transaction IDs
    canonical_rule_map: Dict[str, Set[str]] = {}
    for rf in canonical_evidence.rule_findings:
        canonical_rule_map.setdefault(rf.rule_id, set()).update(rf.supporting_transaction_ids)

    # 1. Validate structured anomaly findings
    for af in report.anomaly_findings:
        tid = af.transaction_id
        if tid not in stmt_txns:
            msg = f"Anomaly finding cites transaction '{tid}' which does not exist in statement."
            errors.append(msg)
            unverified_tids.add(tid)
        elif tid not in canonical_anomaly_ids:
            msg = (
                f"Provenance failure: Transaction '{tid}' is listed under anomaly_findings, "
                f"but was NOT flagged by Isolation Forest detection."
            )
            errors.append(msg)
            provenance_failures.append(msg)
        else:
            verified_tids.add(tid)

    # 2. Validate structured detection rule findings
    for df in report.detection_findings:
        actual_tids = canonical_rule_map.get(df.rule_id, set())
        for tid in df.supporting_transaction_ids:
            if tid not in stmt_txns:
                msg = f"Rule finding '{df.rule_id}' cites non-existent transaction '{tid}'."
                errors.append(msg)
                unverified_tids.add(tid)
            elif tid not in actual_tids:
                msg = (
                    f"Provenance failure: Transaction '{tid}' is claimed to trigger rule '{df.rule_id}', "
                    f"but is not in actual rule output."
                )
                errors.append(msg)
                provenance_failures.append(msg)
            else:
                verified_tids.add(tid)

    # 3. Validate Human Review items
    canonical_hr_ids = {item.transaction_id for item in canonical_evidence.human_review_items}
    for hr in getattr(report, "human_review_items", []):
        tid = hr.transaction_id
        if tid not in stmt_txns:
            msg = f"Human review item cites non-existent transaction '{tid}'."
            errors.append(msg)
            unverified_tids.add(tid)
        elif tid not in canonical_hr_ids:
            msg = (
                f"Provenance failure: Transaction '{tid}' is listed for Human Review, "
                f"but lacks supporting detection signals (anomaly, rule, or network)."
            )
            errors.append(msg)
            provenance_failures.append(msg)
        else:
            verified_tids.add(tid)
            # Verify claims made in reasons
            for reason in hr.reasons:
                if reason == "STATISTICAL_ANOMALY" and tid not in canonical_anomaly_ids:
                    msg = f"Provenance failure: Human review claims '{tid}' is a STATISTICAL_ANOMALY, but it was not flagged."
                    errors.append(msg)
                    provenance_failures.append(msg)
                elif reason.startswith("RULE_"):
                    rid = reason.replace("RULE_", "")
                    valid_rule_tids = canonical_rule_map.get(reason, canonical_rule_map.get(rid, set()))
                    if tid not in valid_rule_tids:
                        msg = f"Provenance failure: Human review claims '{tid}' triggered {reason}, but it is not in rule output."
                        errors.append(msg)
                        provenance_failures.append(msg)

    # 4. Validate Observed Evidence items
    for ev in report.observed_evidence:
        tid = ev.transaction_id
        if tid not in stmt_txns:
            if ev.verified_in_statement:
                msg = f"Observed evidence marks '{tid}' as verified, but it is not in statement."
                errors.append(msg)
            unverified_tids.add(tid)
        else:
            t = stmt_txns[tid]
            verified_tids.add(tid)
            actual_amt = t.credit if t.credit is not None else t.debit
            if ev.amount is not None and actual_amt is not None:
                if abs(ev.amount - actual_amt) > 0.01:
                    errors.append(
                        f"Amount mismatch for '{tid}': reported ₹{ev.amount:,.2f}, statement record is ₹{actual_amt:,.2f}."
                    )
            if ev.date and str(t.date) != ev.date:
                errors.append(f"Date mismatch for '{tid}': reported {ev.date}, statement record is {t.date}.")
            # Direction check
            if ev.flow_type:
                expected_flow = "credit" if t.credit is not None else "debit"
                if ev.flow_type.lower() != expected_flow:
                    errors.append(
                        f"Flow direction mismatch for '{tid}': reported '{ev.flow_type}', statement record is '{expected_flow}'."
                    )
            # Counterparty check
            if ev.counterparty and t.counterparty:
                if ev.counterparty.strip().lower() != t.counterparty.strip().lower():
                    errors.append(
                        f"Counterparty mismatch for '{tid}': reported '{ev.counterparty}', statement record is '{t.counterparty}'."
                    )

    # 5. Validate Human Review Priority against Canonical Prioritizer
    canonical_hr_map = {item.transaction_id: item.priority for item in canonical_evidence.human_review_items}
    for hr in getattr(report, "human_review_items", []):
        tid = getattr(hr, "transaction_id", hr.get("transaction_id") if isinstance(hr, dict) else "")
        prio = getattr(hr, "priority", hr.get("priority") if isinstance(hr, dict) else "")
        if tid in canonical_hr_map and prio and canonical_hr_map[tid] != prio:
            errors.append(
                f"Priority divergence for review item '{tid}': report specifies '{prio}', "
                f"canonical prioritizer determined '{canonical_hr_map[tid]}'."
            )

    # 6. Validate Counterparty Count Consistency (Bug 5)
    if report.customer_profile and report.network_summary:
        cp_profile = report.customer_profile.unique_counterparties
        cp_network = report.network_summary.unique_counterparties
        if cp_profile != cp_network:
            errors.append(
                f"Counterparty count mismatch: Customer Profile reports {cp_profile} unique counterparties, "
                f"while Network Analysis reports {cp_network} unique counterparties."
            )

    # 7. Validate Internal Transaction Count Consistency
    if statement.total_transactions > 0:
        if report.total_transactions_analyzed and report.total_transactions_analyzed != statement.total_transactions:
            errors.append(
                f"Transaction count mismatch: Report overview reports {report.total_transactions_analyzed} transactions, "
                f"statement contains {statement.total_transactions}."
            )
        if report.customer_profile and report.customer_profile.total_transactions != statement.total_transactions:
            errors.append(
                f"Transaction count mismatch: Customer Profile reports {report.customer_profile.total_transactions} transactions, "
                f"statement contains {statement.total_transactions}."
            )

    # 8. Validate against Range Reconstruction (Bug 1)
    all_report_text = f"{report.executive_summary} {report.interpretation}"
    for b in report.executive_summary_bullets:
        all_report_text += f" {b}"

    range_matches = re.findall(r"\b(TXN\d+)\s*(?:through|to|–|-)\s*(TXN\d+)\b", all_report_text, flags=re.IGNORECASE)
    for start_id, end_id in range_matches:
        # Check if this range pattern is asserting an anomaly or review span
        context_window = all_report_text[max(0, all_report_text.find(start_id) - 40) : min(len(all_report_text), all_report_text.find(end_id) + 50)].lower()
        if any(kw in context_window for kw in ["anomal", "outlier", "isolation forest", "flagged"]):
            errors.append(
                f"Range reconstruction violation: Text states '{start_id} through {end_id}' in anomaly context. "
                "The system must never infer a contiguous transaction ID range for statistical anomalies."
            )

    # 9. Validate against Regulatory Threshold Claims (Bug 6)
    if re.search(r"\bregulatory\s+(?:reporting\s+)?threshold\b", all_report_text, flags=re.IGNORECASE):
        errors.append(
            "Regulatory threshold inference violation: Report prose refers to 'regulatory reporting threshold'. "
            "Use 'configured monitoring threshold' or 'configured absolute threshold' unless supported by explicit regulatory evidence."
        )

    # 10. Validate against Stale 'Details Unavailable' Claims (Bug 3)
    if statement.total_transactions > 0:
        stale_phrases = [
            "granular details not",
            "granular details were not",
            "granular details unavailable",
            "transaction-level amounts, dates and counterparties were not available",
            "counterparties were not available",
            "amounts and dates were not available",
            "lack of transaction details",
        ]
        for lim in report.limitations:
            low_lim = lim.lower()
            if any(sp in low_lim for sp in stale_phrases):
                errors.append(
                    f"Stale limitation violation: Limitation claims '{lim}', "
                    "but canonical statement contains verified dates, amounts, and counterparties."
                )

    # 11. Validate AML Non-Judgmental Safety Boundaries
    safety_patterns = [
        (r"\b(guilty\s+of\s+(?:money\s+laundering|fraud|crime))\b", "Declaring customer guilt"),
        (r"\b(is\s+laundering\s+money)\b", "Definitive money laundering claim"),
        (r"\b(committed\s+(?:a\s+)?crime)\b", "Criminal accusation"),
        (r"\b(criminal\s+(?:act|conduct|liability)\s+established)\b", "Declaring criminal liability"),
        (r"\b(close\s+(?:the\s+)?account)\b", "Mandating account closure"),
        (r"\b(file\s+(?:a\s+|an\s+)?(?:sar|str|suspicious\s+transaction\s+report))\b", "Autonomous regulatory reporting order"),
    ]
    for pattern, desc in safety_patterns:
        matches = re.findall(pattern, all_report_text, flags=re.IGNORECASE)
        if matches:
            errors.append(f"Compliance safety violation ({desc}): Found prohibited assertion matching '{pattern}'.")

    # 12. Validate text prose for ungrounded detection claims
    sentences = [s.strip() for s in re.split(r"[.\n]", all_report_text) if s.strip()]
    for s in sentences:
        s_tids = re.findall(r"\bTXN\d+\b", s)
        if not s_tids:
            continue

        low_s = s.lower()
        is_anomaly_claim = any(
            kw in low_s for kw in ["isolation forest", "statistical anomal", "statistical outlier", "flagged as anomal", "anomalous transaction"]
        )
        if is_anomaly_claim:
            for tid in s_tids:
                if tid not in stmt_txns:
                    errors.append(f"Text cites non-existent transaction '{tid}' in anomaly context.")
                    unverified_tids.add(tid)
                elif tid not in canonical_anomaly_ids:
                    msg = (
                        f"Provenance failure in narrative: Text claims transaction '{tid}' is an anomaly, "
                        f"but '{tid}' was NOT flagged by Isolation Forest (actual anomalies: {sorted(list(canonical_anomaly_ids))})."
                    )
                    errors.append(msg)
                    provenance_failures.append(msg)

    passed = len(errors) == 0 and len(provenance_failures) == 0

    return EvidenceValidationResult(
        passed=passed,
        errors=errors,
        warnings=warnings,
        verified_transaction_ids=sorted(list(verified_tids)),
        unverified_transaction_ids=sorted(list(unverified_tids)),
        provenance_failures=provenance_failures,
    )
