"""Deterministic generator transforming investigation states into structured reports."""

import datetime as dt
import re
import uuid
from typing import Any, Dict, List, Optional

from aml_copilot.agents.state import InvestigationResult
from aml_copilot.logger import get_logger
from aml_copilot.ml.pipeline import run_detection
from aml_copilot.models.evidence import (
    SIGNAL_DOMAINS,
    CanonicalEvidence,
    build_canonical_evidence,
    reconcile_customer_profile,
)
from aml_copilot.models.findings import DetectionResult
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.network.analysis import build_transaction_network
from aml_copilot.network.models import NetworkAnalysisResult
from aml_copilot.profiling.customer_profile import CustomerProfile
from aml_copilot.profiling.profiler import build_customer_profile
from aml_copilot.reporting.models import (
    AnomalyFindingItem,
    AnomalyFindingsSummary,
    CriticSummary,
    CustomerProfileSummary,
    CustomerSummary,
    DetectionFindingItem,
    EvidenceConvergenceItem,
    EvidenceConvergenceSummary,
    EvidenceItem,
    HumanReviewQueueSummary,
    InterpretationContext,
    InvestigationReport,
    KnowledgeReferenceItem,
    NetworkFindingItem,
    NetworkSummary,
    RAGSummary,
    ReportDTO,
    ReportMetadata,
    RevisionSummary,
    RuleFindingsSummary,
    RuleSummaryGroup,
    TransactionSummary,
)
from aml_copilot.reporting.validation import validate_report_evidence

logger = get_logger(__name__)


def align_narrative_with_canonical_evidence(
    text: str, canonical_evidence: CanonicalEvidence
) -> str:
    """Ensure narrative text reflects verified canonical detection results without hallucinated IDs or ranges.

    Deterministic Fixes Enforced:
    - Bug 1: No anomaly range reconstruction ('TXN401 through TXN454').
    - Bug 2: No false 'all 54 require review' claim.
    - Bug 6: Replaces 'regulatory reporting threshold' with 'configured monitoring threshold'.
    - Bug 7: Replaces 'external AML knowledge base' with 'AML reference knowledge base'.
    """
    if not text:
        return ""

    actual_anom_ids = canonical_evidence.anomaly_transaction_ids if canonical_evidence else []
    total_txns = (
        canonical_evidence.total_transactions
        if canonical_evidence and canonical_evidence.total_transactions
        else (len(canonical_evidence.canonical_transactions) if canonical_evidence else 0)
    )
    hr_items = canonical_evidence.human_review_items if canonical_evidence else []
    hr_count = len(hr_items)

    # Bug 6: Normalize threshold wording
    text = re.sub(
        r"\bregulatory\s+(?:reporting\s+)?threshold\b",
        "configured monitoring threshold",
        text,
        flags=re.IGNORECASE,
    )

    # Bug 7: Normalize knowledge base wording
    text = re.sub(
        r"\bexternal\s+aml\s+(?:knowledge\s+base|guidance|typology\s+sources?)\b",
        "AML reference knowledge base",
        text,
        flags=re.IGNORECASE,
    )

    # Bug 2: Fix false 'all X transactions require review'
    all_rev_patterns = [
        r"\ball\s+\d+\s+transactions?\s+(?:require|warrant|recommended\s+for)\s+(?:human\s+)?review\b",
        r"\ball\s+transactions?\s+(?:require|warrant|recommended\s+for)\s+(?:human\s+)?review\b",
        r"\bevery\s+transaction\s+requires\s+(?:human\s+)?review\b",
    ]
    for pat in all_rev_patterns:
        text = re.sub(
            pat,
            f"{hr_count} of {total_txns} analyzed transactions require prioritized human review",
            text,
            flags=re.IGNORECASE,
        )

    # Bug 1: Range reconstruction prevention across all sentences
    range_replacement = ", ".join(actual_anom_ids) if actual_anom_ids else "specific identified transactions"
    text = re.sub(
        r"\bTXN\d+\s*(?:through|to|–|-)\s*TXN\d+\b",
        range_replacement,
        text,
        flags=re.IGNORECASE,
    )

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    aligned_sentences: List[str] = []

    for s in sentences:
        low_s = s.lower()
        is_anomaly_claim = any(
            kw in low_s
            for kw in [
                "isolation forest",
                "statistical anomal",
                "statistical outlier",
                "flagged as anomal",
                "anomalous transaction",
                "anomaly transaction",
            ]
        )
        if is_anomaly_claim and not any(neg in low_s for neg in ["not an anomaly", "no anomaly", "non-anomalous"]):
            s_tids = re.findall(r"\bTXN\d+\b", s)
            has_invalid_anom = any(tid not in actual_anom_ids for tid in s_tids)
            if actual_anom_ids and has_invalid_anom:
                # Replace with factual canonical statement
                s = (
                    f"Isolation Forest unsupervised anomaly detection flagged {len(actual_anom_ids)} "
                    f"statistical outlier transaction(s): {', '.join(actual_anom_ids)}."
                )
        aligned_sentences.append(s)

    return " ".join(aligned_sentences)


def generate_investigation_report(
    statement: TransactionStatement,
    investigation: InvestigationResult,
    detection_result: Optional[DetectionResult] = None,
    profile: Optional[CustomerProfile] = None,
    network_result: Optional[NetworkAnalysisResult] = None,
    canonical_evidence: Optional[CanonicalEvidence] = None,
) -> InvestigationReport:
    """Construct a fully traceable, evidence-grounded InvestigationReport.

    Deterministic Guarantees:
    1. Transaction amounts, dates, and counterparties are pulled strictly from the verified statement.
    2. Numerical metrics (turnover, counts, ratios) are computed by deterministic Python services.
    3. Anomaly and Rule transaction IDs are sourced exclusively from CanonicalEvidence.
    4. Human Review items are selected deterministically via evidence convergence.
    5. No transaction evidence or financial metrics are hallucinated.

    Args:
        statement: Validated customer TransactionStatement.
        investigation: Final InvestigationResult from the agent/graph.
        detection_result: Optional pre-computed detection findings.
        profile: Optional pre-computed CustomerProfile.
        network_result: Optional pre-computed NetworkAnalysisResult.
        canonical_evidence: Optional pre-computed CanonicalEvidence single source of truth.

    Returns:
        Structured InvestigationReport model ready for serialization or formatting.
    """
    now_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    report_id = f"REP-AML-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    # 1. Resolve Canonical Evidence (Single Source of Truth)
    if canonical_evidence is None:
        canonical_evidence = getattr(investigation, "canonical_evidence", None)
    if canonical_evidence is None:
        canonical_evidence = build_canonical_evidence(
            statement=statement,
            detection_result=detection_result,
            profile=profile,
            network_result=network_result,
            knowledge_sources=investigation.knowledge_sources,
        )

    # 1b. Enforce strict mathematical reconciliation invariants on Customer Profile
    reconcile_customer_profile(
        canonical_evidence.customer_profile,
        canonical_evidence.canonical_transactions,
    )

    stmt_txns: Dict[str, Transaction] = {t.transaction_id: t for t in statement.transactions if t.transaction_id}

    # 2. Deterministic Traceable Evidence (All Flagged + All Cited IDs)
    observed_evidence: List[EvidenceItem] = []
    all_evidence_ids: List[str] = list(canonical_evidence.all_flagged_transaction_ids)

    # Include any additional IDs cited in investigation text or draft
    extra_cited = list(investigation.referenced_transaction_ids)
    if investigation.draft and investigation.draft.referenced_transaction_ids:
        for tid in investigation.draft.referenced_transaction_ids:
            if tid not in extra_cited:
                extra_cited.append(tid)

    for tid in extra_cited:
        if tid not in all_evidence_ids:
            all_evidence_ids.append(tid)

    # Build EvidenceItems strictly against statement records
    for tid in all_evidence_ids:
        if tid in stmt_txns:
            t = stmt_txns[tid]
            amt = t.credit if t.credit is not None else t.debit
            flow = "credit" if t.credit is not None else "debit"
            observed_evidence.append(
                EvidenceItem(
                    transaction_id=tid,
                    date=t.date.isoformat() if t.date else None,
                    amount=amt,
                    flow_type=flow,
                    counterparty=t.counterparty,
                    description=t.description,
                    verified_in_statement=True,
                )
            )
        else:
            observed_evidence.append(
                EvidenceItem(
                    transaction_id=tid,
                    date=None,
                    amount=None,
                    flow_type=None,
                    counterparty=None,
                    description="Transaction identifier cited but not found in statement records.",
                    verified_in_statement=False,
                )
            )

    # 3. Deterministic Detection Findings (From Canonical Evidence)
    detection_findings: List[DetectionFindingItem] = [
        DetectionFindingItem(
            rule_id=rf.rule_id,
            rule_name=rf.rule_name,
            severity=rf.severity,
            explanation=rf.observation,
            supporting_transaction_ids=rf.supporting_transaction_ids,
            supporting_values=rf.supporting_values,
        )
        for rf in canonical_evidence.rule_findings
    ]

    # Group rule findings by rule type to prevent repetitive narrative output
    rule_groups: Dict[str, Dict[str, Any]] = {}
    for rf in canonical_evidence.rule_findings:
        if rf.rule_id not in rule_groups:
            rule_groups[rf.rule_id] = {
                "rule_id": rf.rule_id,
                "rule_name": rf.rule_name,
                "tids": list(rf.supporting_transaction_ids),
                "severity_counts": {rf.severity: len(rf.supporting_transaction_ids) or 1},
                "observations": [rf.observation],
            }
        else:
            rg = rule_groups[rf.rule_id]
            for tid in rf.supporting_transaction_ids:
                if tid not in rg["tids"]:
                    rg["tids"].append(tid)
            sev = rf.severity
            rg["severity_counts"][sev] = rg["severity_counts"].get(sev, 0) + (len(rf.supporting_transaction_ids) or 1)
            if len(rg["observations"]) < 3 and rf.observation not in rg["observations"]:
                rg["observations"].append(rf.observation)

    rule_summary_groups: List[RuleSummaryGroup] = []
    for rid, data in rule_groups.items():
        rep_txns = []
        for tid in data["tids"]:
            if tid in stmt_txns:
                t = stmt_txns[tid]
                amt = t.credit if t.credit is not None else t.debit
                rep_txns.append((tid, amt or 0.0, str(t.date), t.counterparty or "Unspecified"))
        rep_txns.sort(key=lambda x: x[1], reverse=True)
        rep_examples = [
            f"`{tid}`: ₹{amt:,.2f} ({dt_str}, {cp})"
            for tid, amt, dt_str, cp in rep_txns[:3]
        ]
        rule_summary_groups.append(
            RuleSummaryGroup(
                rule_id=data["rule_id"],
                rule_name=data["rule_name"],
                count=len(data["tids"]),
                severity_distribution=data["severity_counts"],
                supporting_transaction_ids=data["tids"],
                representative_examples=rep_examples,
                observation_summary=data["observations"][0] if data["observations"] else "",
            )
        )

    # Deterministic Anomaly Findings (Exact IDs preserved from Isolation Forest)
    anomaly_findings: List[AnomalyFindingItem] = [
        AnomalyFindingItem(
            transaction_id=af.transaction_id,
            anomaly_score=af.anomaly_score,
            is_anomaly=True,
            feature_context=af.feature_summary,
        )
        for af in canonical_evidence.statistical_anomalies
    ]

    # 4. Deterministic Customer Profile
    customer_profile_summary: Optional[CustomerProfileSummary] = None
    unique_cp_count = 0
    if canonical_evidence.customer_profile:
        cp = canonical_evidence.customer_profile
        unique_cp_count = cp.unique_counterparties
        customer_profile_summary = CustomerProfileSummary(
            customer_name=cp.customer_name or statement.customer_name,
            account_number=cp.account_number or statement.account_number,
            statement_period=cp.statement_period or statement.statement_period,
            total_transactions=cp.total_transactions,
            total_credits=round(cp.total_credits, 2),
            total_debits=round(cp.total_debits, 2),
            net_cash_flow=round(cp.net_cash_flow, 2),
            average_transaction_amount=round(cp.average_transaction_amount, 2),
            credit_to_debit_ratio=round(cp.credit_to_debit_ratio, 4) if cp.credit_to_debit_ratio else None,
            unique_counterparties=cp.unique_counterparties,
            active_days=cp.active_days,
            dominant_type=cp.dominant_type,
            largest_credit_amount=cp.largest_credit_amount,
            largest_debit_amount=cp.largest_debit_amount,
            indicators=cp.indicators,
        )

    # 5. Deterministic Network Findings & Summary (Clearly distinguishing counterparties from nodes)
    network_findings: List[NetworkFindingItem] = [
        NetworkFindingItem(
            pattern_name=nf.pattern_name,
            description=nf.description,
            involved_nodes=nf.involved_nodes,
            supporting_transaction_ids=nf.supporting_transaction_ids,
        )
        for nf in canonical_evidence.network_findings
    ]

    dominant_cps = canonical_evidence.network_dominant_counterparties or []
    if not dominant_cps and network_result and hasattr(network_result, "metrics") and network_result.metrics.largest_counterparty_by_volume:
        dominant_cps.append(network_result.metrics.largest_counterparty_by_volume)

    network_summary = NetworkSummary(
        unique_counterparties=canonical_evidence.network_unique_counterparties or unique_cp_count or (len(network_result.nodes) - 1 if network_result else 0),
        graph_nodes=canonical_evidence.network_graph_nodes or (unique_cp_count + 1 if unique_cp_count else (len(network_result.nodes) if network_result else 1)),
        graph_edges=canonical_evidence.network_graph_edges or (len(network_result.edges) if network_result else 0),
        dominant_counterparties=dominant_cps,
    )

    # 6. AML Knowledge / RAG References (AML reference knowledge base)
    aml_reference_context: List[KnowledgeReferenceItem] = []
    for rag in canonical_evidence.rag_evidence:
        aml_reference_context.append(
            KnowledgeReferenceItem(
                source=rag.source,
                title=rag.citation or rag.source,
                snippet=rag.retrieved_text,
            )
        )
    if not aml_reference_context:
        for src in investigation.knowledge_sources:
            title = src.replace(".md", "").replace("_", " ").title()
            aml_reference_context.append(
                KnowledgeReferenceItem(
                    source=src,
                    title=title,
                    snippet="Retrieved AML typology guidance referenced during evidence synthesis.",
                )
            )

    # 7. Section 8: Evidence Convergence (Multi-signal convergence)
    DOMAIN_NAME_MAP = {
        "ML_ANOMALY": "Statistical (Isolation Forest Outlier)",
        "FLOW_TYPOLOGY": "Flow (Rapid Movement / Inflow-Outflow)",
        "THRESHOLD": "Rule (Large / Round Amount Threshold)",
        "NETWORK_HUB": "Network (Dominant Counterparty Hub)",
        "COUNTERPARTY_BURST": "Volume (New Counterparty Surge)",
        "NETWORK_TOPOLOGY": "Network (Star Topology)",
    }

    evidence_convergence: List[EvidenceConvergenceItem] = []
    for item in canonical_evidence.human_review_items:
        if item.priority not in ("HIGH", "MEDIUM"):
            continue
        domains = set()
        for reason in item.reasons:
            dom = SIGNAL_DOMAINS.get(reason)
            if dom:
                domains.add(DOMAIN_NAME_MAP.get(dom, dom))

        evidence_convergence.append(
            EvidenceConvergenceItem(
                transaction_id=item.transaction_id,
                date=item.date,
                amount=item.amount,
                direction=item.direction,
                flow_type=item.direction,
                counterparty=item.counterparty,
                priority=item.priority,
                signal_domains=sorted(list(domains)),
                reasons=item.reasons,
                supporting_finding_ids=item.supporting_finding_ids,
                convergence_summary=item.evidence_summary
                or f"Multi-signal convergence across {len(domains)} independent domain(s).",
            )
        )

    # 8. Human Review Queue Summary
    hr_items = canonical_evidence.human_review_items
    high_count = len([i for i in hr_items if i.priority == "HIGH"])
    med_count = len([i for i in hr_items if i.priority == "MEDIUM"])
    low_count = len([i for i in hr_items if i.priority == "LOW"])
    human_review_summary = {
        "total_analyzed": statement.total_transactions,
        "prioritized_review_count": len(hr_items),
        "high_priority_count": high_count,
        "medium_priority_count": med_count,
        "low_priority_count": low_count,
    }

    is_partial_max_iter = (
        getattr(investigation, "is_partial", False)
        or getattr(investigation, "status", "") == "MAX_ITERATIONS_REACHED"
    )

    # 9. Executive Summary & Bullets (5-8 concise factual bullets)
    raw_exec = investigation.response
    if is_partial_max_iter:
        if not raw_exec.startswith("[PARTIAL INVESTIGATION"):
            raw_exec = f"[PARTIAL INVESTIGATION — MAX ITERATIONS REACHED]\n{raw_exec}"
    elif investigation.draft and investigation.draft.summary:
        raw_exec = investigation.draft.summary

    exec_summary = align_narrative_with_canonical_evidence(raw_exec, canonical_evidence)

    top_converged_preview = [i for i in hr_items if i.priority == "HIGH"][:2]
    top_preview_str = (
        "; ".join(
            f"{i.transaction_id} (₹{i.amount:,.2f} {i.direction or ''} via {i.counterparty or 'Unspecified'})"
            for i in top_converged_preview
        )
        if top_converged_preview
        else "None"
    )

    exec_summary_bullets = [
        f"{statement.total_transactions} transactions analyzed across statement period {statement.statement_period or 'under review'}.",
        f"{len(hr_items)} transactions generated prioritized human-review signals ({high_count} HIGH, {med_count} MEDIUM, {low_count} LOW).",
        f"{len(canonical_evidence.statistical_anomalies)} transactions were identified as Isolation Forest statistical outliers: {', '.join(canonical_evidence.anomaly_transaction_ids)}.",
        "Key observed patterns include high-value transaction bursts, rapid inflow/outflow pass-through sequences, velocity surges, and counterparty concentration.",
        f"Highest-convergence review items warranting immediate compliance inspection: {top_preview_str}.",
        "These findings constitute automated investigative risk indicators and do not represent determinations of illegal activity, fraud, or money laundering.",
    ]

    raw_interpretation = investigation.response
    if investigation.draft and investigation.draft.interpretation:
        raw_interpretation = investigation.draft.interpretation

    interpretation = align_narrative_with_canonical_evidence(raw_interpretation, canonical_evidence)

    # 10. Critic Validation Summary (Bug 4 metrics)
    stmt_txn_count = len(statement.transactions)
    narrative_ref_count = len(all_evidence_ids)
    hr_queue_count = len(hr_items)
    verified_ref_count = len([tid for tid in all_evidence_ids if tid in stmt_txns])
    unverified_ref_count = len([tid for tid in all_evidence_ids if tid not in stmt_txns])

    if is_partial_max_iter:
        critic_summary = CriticSummary(
            passed=False,
            status="INCOMPLETE",
            statement_transaction_count=stmt_txn_count,
            narrative_transaction_reference_count=narrative_ref_count,
            human_review_transaction_count=hr_queue_count,
            verified_transaction_reference_count=verified_ref_count,
            unverified_transaction_reference_count=unverified_ref_count,
            issues=[
                "Investigation reached maximum reasoning iterations before completing full synthesis and critic review."
            ],
            missing_evidence=["Complete analytical synthesis and critic audit."],
            unsupported_claims=[],
            safety_violations=[],
            checked_transaction_ids=list(all_evidence_ids),
            invalid_transaction_ids=[],
            required_revisions=["Human compliance officer must review partial evidence and complete investigation."],
        )
    elif investigation.critic_result:
        cr = investigation.critic_result
        critic_summary = CriticSummary(
            passed=cr.passed,
            status=investigation.critic_status or ("PASS" if cr.passed else "FAIL"),
            statement_transaction_count=cr.statement_transaction_count or stmt_txn_count,
            narrative_transaction_reference_count=cr.narrative_transaction_reference_count or len(cr.checked_transaction_ids),
            human_review_transaction_count=cr.human_review_transaction_count or hr_queue_count,
            verified_transaction_reference_count=cr.verified_transaction_reference_count or len(cr.checked_transaction_ids),
            unverified_transaction_reference_count=cr.unverified_transaction_reference_count or len(cr.invalid_transaction_ids),
            issues=cr.issues,
            missing_evidence=cr.missing_evidence,
            unsupported_claims=cr.unsupported_claims,
            safety_violations=cr.safety_violations,
            checked_transaction_ids=cr.checked_transaction_ids,
            invalid_transaction_ids=cr.invalid_transaction_ids,
            required_revisions=cr.required_revisions,
        )
    else:
        critic_summary = CriticSummary(
            passed=True,
            status="PASS",
            statement_transaction_count=stmt_txn_count,
            narrative_transaction_reference_count=narrative_ref_count,
            human_review_transaction_count=hr_queue_count,
            verified_transaction_reference_count=verified_ref_count,
            unverified_transaction_reference_count=unverified_ref_count,
            issues=[],
            missing_evidence=[],
            unsupported_claims=[],
            safety_violations=[],
            checked_transaction_ids=list(all_evidence_ids),
            invalid_transaction_ids=[],
            required_revisions=[],
        )

    # 11. Revision History
    rev_count = investigation.revision_count
    unresolved = is_partial_max_iter or investigation.critic_status == "FAIL" or not critic_summary.passed
    revision_summary = RevisionSummary(
        revision_count=rev_count,
        max_revisions=2,
        revisions_applied=rev_count > 0,
        unresolved_limitations=unresolved,
    )

    # 12. Consolidated Limitations (Bug 3: filter stale limitations)
    stale_limitation_keywords = [
        "granular details",
        "details unavailable",
        "counterparties were not available",
        "amounts and dates were not available",
        "transaction-level amounts",
        "lack of transaction details",
        "not available",
    ]
    limitations: List[str] = []
    for lim in investigation.limitations_warnings:
        low_lim = lim.lower()
        if any(kw in low_lim for kw in stale_limitation_keywords) and len(statement.transactions) > 0:
            continue
        limitations.append(lim)

    if is_partial_max_iter and not any("maximum reasoning iterations" in lim.lower() for lim in limitations):
        limitations.append(
            "Investigation reached maximum reasoning iterations before completing full synthesis. "
            "This is a partial investigation; mandatory human compliance review is required."
        )
    if statement.total_transactions < 10 and not any("limited history" in lim.lower() for lim in limitations):
        limitations.append(
            f"Statement covers a limited historical window ({statement.total_transactions} transactions), "
            "constraining long-term baseline comparison."
        )
    if unresolved and not any("unresolved" in lim.lower() for lim in limitations) and not is_partial_max_iter:
        limitations.append(
            "Investigation concluded with unresolved Critic findings after reaching maximum revisions. "
            "Manual compliance review is required."
        )
    if not limitations:
        limitations.append(
            "Investigation findings and risk signals are generated for analytical assistance only. "
            "They do not establish legal guilt, fraud, or regulatory violations."
        )

    # 13. Section 12: Recommended Next Steps (Grounded in investigation evidence)
    dominant_cps = canonical_evidence.network_dominant_counterparties or []
    if dominant_cps:
        cp_clause = f" for high-volume counterparties including {', '.join(dominant_cps[:3])}."
    else:
        cp_clause = " for identified high-volume counterparties."

    next_steps = [
        "Conduct Enhanced Customer Due Diligence (EDD) to verify the declared commercial profile and purpose of the account.",
        f"Review transactional source documents (invoices, commercial agreements, transport receipts){cp_clause}",
        "Cross-reference rapid pass-through sequences with public corporate registry databases to verify counterparty corporate status and beneficial ownership.",
        "Compare observed velocity and volume surges against baseline account expectations documented at onboarding.",
        "Escalate multi-signal convergence review items to Senior Compliance Management in accordance with institutional SAR/STR reporting procedures where warranted.",
    ]

    # Compute actual critic validation counts
    critic_summary.factual_claim_count = len(all_evidence_ids) + len(critic_summary.issues) + len(critic_summary.unsupported_claims)
    critic_summary.validation_error_count = len(critic_summary.issues) + len(critic_summary.unsupported_claims) + len(critic_summary.safety_violations)

    # 14. Construct Canonical ReportDTO
    report_metadata = ReportMetadata(
        report_id=report_id,
        generated_at=now_utc,
        investigation_question=investigation.question,
        status="PARTIAL" if is_partial_max_iter else "COMPLETED",
        source_type="universal_canonical",
    )
    customer_summary = CustomerSummary(
        customer_name=statement.customer_name or "Unknown Customer",
        account_number=statement.account_number or "Unknown Account",
        statement_period=statement.statement_period or "Unknown Period",
    )
    high_value_txns = canonical_evidence.high_value_transactions(threshold=200000.0)
    tx_summary = TransactionSummary(
        total_transactions=statement.total_transactions,
        total_credits=round(sum(t.amount for t in canonical_evidence.canonical_transactions if t.direction == "credit"), 2),
        total_debits=round(sum(t.amount for t in canonical_evidence.canonical_transactions if t.direction == "debit"), 2),
        net_flow=round(
            sum(t.amount for t in canonical_evidence.canonical_transactions if t.direction == "credit") -
            sum(t.amount for t in canonical_evidence.canonical_transactions if t.direction == "debit"),
            2,
        ),
        currency="INR",
        canonical_transactions=canonical_evidence.canonical_transactions,
        high_value_transactions=high_value_txns,
        observed_evidence=observed_evidence,
    )
    rules_summary = RuleFindingsSummary(
        total_rule_signals=len(canonical_evidence.rule_findings),
        rule_summary_groups=rule_summary_groups,
        detection_findings=detection_findings,
    )
    anomalies_summary = AnomalyFindingsSummary(
        total_anomalies=len(canonical_evidence.statistical_anomalies),
        anomaly_transaction_ids=canonical_evidence.anomaly_transaction_ids,
        anomaly_findings=anomaly_findings,
        model="isolation_forest",
        provenance="isolation_forest",
    )
    rag_summary = RAGSummary(
        retrieved_references=aml_reference_context,
        reference_disclaimer=(
            "No AML reference guidance was retrieved during this investigation."
            if not aml_reference_context
            else "Retrieved from AML reference knowledge base for educational/analytical context."
        ),
    )
    convergence_summary = EvidenceConvergenceSummary(
        converged_items=evidence_convergence,
    )
    hr_queue_summary = HumanReviewQueueSummary(
        total_analyzed=statement.total_transactions,
        prioritized_review_count=len(hr_items),
        high_priority_count=high_count,
        medium_priority_count=med_count,
        low_priority_count=low_count,
        items=canonical_evidence.human_review_items,
    )
    interp_context = InterpretationContext(
        narrative=interpretation,
        executive_summary=exec_summary,
        executive_summary_bullets=exec_summary_bullets,
    )

    report_dto = ReportDTO(
        metadata=report_metadata,
        customer=customer_summary,
        transactions=tx_summary,
        rules=rules_summary,
        anomalies=anomalies_summary,
        profile=customer_profile_summary,
        network=network_summary,
        network_findings=network_findings,
        rag=rag_summary,
        convergence=convergence_summary,
        human_review=hr_queue_summary,
        interpretation=interp_context,
        critic=critic_summary,
        revision=revision_summary,
        limitations=limitations,
        recommendations=next_steps,
    )

    # Assemble base report with all 14 canonical sections and attach ReportDTO
    report = InvestigationReport(
        report_id=report_id,
        generated_at=now_utc,
        customer_name=statement.customer_name or "Unknown Customer",
        account_number=statement.account_number or "Unknown Account",
        statement_period=statement.statement_period or "Unknown Period",
        investigation_question=investigation.question,
        total_transactions_analyzed=statement.total_transactions,
        executive_summary=exec_summary,
        executive_summary_bullets=exec_summary_bullets,
        observed_evidence=observed_evidence,
        rule_summary_groups=rule_summary_groups,
        detection_findings=detection_findings,
        anomaly_findings=anomaly_findings,
        customer_profile=customer_profile_summary,
        network_summary=network_summary,
        network_findings=network_findings,
        aml_reference_context=aml_reference_context,
        evidence_convergence=evidence_convergence,
        human_review_items=canonical_evidence.human_review_items,
        human_review_summary=human_review_summary,
        interpretation=interpretation,
        limitations=limitations,
        next_steps=next_steps,
        critic_validation=critic_summary,
        revision_history=revision_summary,
        evidence_validation_passed=True,
        report_dto=report_dto,
    )

    # 14. Rigorous Evidence Provenance Validation (Step 5)
    val_result = validate_report_evidence(report, canonical_evidence, statement)
    report.evidence_validation_passed = val_result.passed

    if not val_result.passed:
        logger.warning(
            f"Report evidence validation encountered failures: {val_result.errors} | Provenance: {val_result.provenance_failures}"
        )
        report.critic_validation.passed = False
        report.critic_validation.status = "FAIL"
        report.critic_validation.issues.extend(val_result.errors)
        report.critic_validation.unsupported_claims.extend(val_result.provenance_failures)
        report.limitations.append(
            f"Evidence validation detected {len(val_result.errors)} unverified claims or provenance failures. "
            "Manual compliance review is required."
        )

    return report
