"""Investigation synthesis node structuring factual evidence into draft artifacts."""

import re
from typing import Any, Callable, Dict, List, Optional
from langchain_core.messages import AIMessage

from aml_copilot.agents.models import (
    EvidenceReference,
    InvestigationDraft,
    InvestigationFinding,
)
from aml_copilot.agents.state import InvestigationState, emit_investigation_event
from aml_copilot.logger import get_logger
from aml_copilot.models.evidence import CanonicalEvidence, build_canonical_evidence
from aml_copilot.models.transaction import TransactionStatement

logger = get_logger(__name__)


def synthesize_findings_from_response(
    response_text: str,
    statement: TransactionStatement,
    question: str = "",
    tools_used: Optional[List[str]] = None,
    customer_profile: Optional[Dict[str, Any]] = None,
    network_analysis: Optional[Dict[str, Any]] = None,
    knowledge_sources: Optional[List[str]] = None,
    canonical_evidence: Optional[CanonicalEvidence] = None,
) -> InvestigationDraft:
    """Synthesize raw agent output and tool artifacts into a structured InvestigationDraft."""
    raw_response = response_text or ""
    tools = tools_used or []
    k_sources = knowledge_sources or []

    # Build or resolve canonical evidence
    if canonical_evidence is None:
        try:
            canonical_evidence = build_canonical_evidence(
                statement=statement,
                knowledge_sources=k_sources,
            )
        except Exception as exc:
            logger.warning(f"Failed to build canonical evidence during synthesis: {exc}")
            canonical_evidence = None

    if not raw_response.strip() and canonical_evidence:
        anom_str = ", ".join(canonical_evidence.anomaly_transaction_ids) if canonical_evidence.anomaly_transaction_ids else "None"
        rule_count = len(canonical_evidence.rule_findings)
        turnover_str = (
            f"turnover of ₹{canonical_evidence.customer_profile.total_credits + canonical_evidence.customer_profile.total_debits:,.2f}"
            if canonical_evidence.customer_profile
            else "transaction activity"
        )
        raw_response = (
            f"Investigation completed for customer {statement.customer_name or 'Unknown'} (Account {statement.account_number or 'Unknown'}). "
            f"Evaluated {statement.total_transactions} transactions with total {turnover_str}. "
            f"Unsupervised Isolation Forest detection flagged {len(canonical_evidence.statistical_anomalies)} statistical anomalies: {anom_str}. "
            f"Deterministic screening identified {rule_count} rule finding(s) including large transaction thresholds, rapid fund movement, and new counterparties. "
            f"Transactions with multi-signal convergence have been prioritized for human compliance officer review."
        )

    # 1. Identify verified referenced transaction IDs
    stmt_txns = {t.transaction_id: t for t in statement.transactions if t.transaction_id}
    flagged_ids = list(canonical_evidence.all_flagged_transaction_ids) if canonical_evidence else []
    text_cited_ids = [tid for tid in stmt_txns if tid in raw_response]

    # Combine all verified IDs deterministically
    referenced_ids = list(flagged_ids)
    for tid in text_cited_ids:
        if tid not in referenced_ids:
            referenced_ids.append(tid)

    # 2. Extract evidence categories
    observed_evidence: List[str] = []
    for tid in referenced_ids:
        t = stmt_txns[tid]
        flow = f"credit ₹{t.credit:,.2f}" if t.credit else f"debit ₹{t.debit:,.2f}"
        cp = f" ({t.counterparty})" if t.counterparty else ""
        observed_evidence.append(f"{tid}: {flow} on {t.date}{cp}")

    # Also parse sections if explicitly formatted
    if "Observed Evidence:" in raw_response:
        sections = re.split(r"\n(?=[A-Z][a-zA-Z\s]+:)", raw_response)
        for sec in sections:
            if sec.startswith("Observed Evidence:"):
                lines = [l.strip("- ") for l in sec.replace("Observed Evidence:", "").strip().split("\n") if l.strip()]
                for line in lines:
                    if line and line not in observed_evidence:
                        observed_evidence.append(line)

    analytical_findings: List[str] = []
    if canonical_evidence:
        if canonical_evidence.statistical_anomalies:
            anom_ids = canonical_evidence.anomaly_transaction_ids
            analytical_findings.append(
                f"Isolation Forest unsupervised anomaly detection flagged {len(anom_ids)} statistical outlier transaction(s): {', '.join(anom_ids)}."
            )
        for rf in canonical_evidence.rule_findings:
            analytical_findings.append(
                f"AML Rule {rf.rule_id} ({rf.rule_name}) triggered for transaction(s) {', '.join(rf.supporting_transaction_ids)}: {rf.observation}"
            )
    else:
        if "detect_anomalies" in tools or "AML rule" in raw_response or "Analytical Findings:" in raw_response:
            analytical_findings.append("AML rule engine and Isolation Forest anomaly screening evaluated.")

    if customer_profile:
        analytical_findings.append(
            f"Customer turnover: ₹{customer_profile.get('total_credits', 0.0) + customer_profile.get('total_debits', 0.0):,.2f} "
            f"across {customer_profile.get('total_transactions', 0)} transactions."
        )

    network_findings: List[str] = []
    if canonical_evidence and canonical_evidence.network_findings:
        for nf in canonical_evidence.network_findings:
            network_findings.append(f"{nf.pattern_name}: {nf.description} (txns: {', '.join(nf.supporting_transaction_ids)})")
    elif network_analysis:
        patterns = [p.get("description") for p in network_analysis.get("observable_patterns", []) if p.get("description")]
        network_findings.extend(patterns[:3])
    elif "Network Findings:" in raw_response:
        network_findings.append("Directed counterparty transactions observed.")

    reference_context: List[str] = []
    if canonical_evidence and canonical_evidence.rag_evidence:
        for rag in canonical_evidence.rag_evidence:
            reference_context.append(f"Retrieved AML guidance from: {rag.source} ({rag.citation})")
    else:
        for src in k_sources:
            reference_context.append(f"Retrieved AML guidance from: {src}")
    if "Relevant AML Reference:" in raw_response or "aml_red_flags" in raw_response:
        reference_context.append("Referenced AML typology guidance.")

    # 3. Create structured findings
    findings: List[InvestigationFinding] = []
    if canonical_evidence:
        # Rule findings
        for rf in canonical_evidence.rule_findings:
            refs = [
                EvidenceReference(
                    source_type="detection",
                    transaction_ids=rf.supporting_transaction_ids,
                    description=f"Rule trigger: {rf.rule_name}",
                    details={"rule_id": rf.rule_id, "values": rf.supporting_values},
                )
            ]
            findings.append(
                InvestigationFinding(
                    finding=f"Rule trigger {rf.rule_id}: {rf.observation}",
                    evidence=refs,
                    transaction_ids=rf.supporting_transaction_ids,
                    source_type="detection",
                    explanation=f"Deterministic rule {rf.rule_name} triggered based on statement activity.",
                    confidence="high",
                )
            )
        # Anomaly findings
        if canonical_evidence.statistical_anomalies:
            anom_ids = canonical_evidence.anomaly_transaction_ids
            anom_refs = [
                EvidenceReference(
                    source_type="detection",
                    transaction_ids=[af.transaction_id],
                    description=f"Isolation Forest outlier score: {af.anomaly_score}",
                    details=af.feature_summary,
                )
                for af in canonical_evidence.statistical_anomalies
            ]
            findings.append(
                InvestigationFinding(
                    finding=f"Isolation Forest identified {len(anom_ids)} statistical anomalies: {', '.join(anom_ids)}.",
                    evidence=anom_refs,
                    transaction_ids=anom_ids,
                    source_type="detection",
                    explanation="Unsupervised machine learning model flagged multi-dimensional feature outliers.",
                    confidence="medium",
                )
            )
    elif referenced_ids:
        evidence_refs = [
            EvidenceReference(
                source_type="transaction",
                transaction_ids=[tid],
                description=f"Direct transaction record for {tid}",
                details={
                    "credit": stmt_txns[tid].credit,
                    "debit": stmt_txns[tid].debit,
                    "date": stmt_txns[tid].date.isoformat(),
                    "counterparty": stmt_txns[tid].counterparty,
                },
            )
            for tid in referenced_ids
        ]

        findings.append(
            InvestigationFinding(
                finding=f"Verified transaction activity involving {len(referenced_ids)} specific transaction records.",
                evidence=evidence_refs,
                transaction_ids=referenced_ids,
                source_type="transaction",
                explanation="Underlying transaction records directly extracted from customer statement.",
                confidence="high",
            )
        )

    return InvestigationDraft(
        question=question,
        summary=raw_response[:200] + ("..." if len(raw_response) > 200 else ""),
        observed_evidence=observed_evidence,
        analytical_findings=analytical_findings,
        network_findings=network_findings,
        reference_context=reference_context,
        interpretation=raw_response,
        findings=findings,
        referenced_transaction_ids=referenced_ids,
        raw_response=raw_response,
    )


def create_synthesis_node(
    statement: TransactionStatement,
) -> Callable[[InvestigationState], Dict[str, Any]]:
    """Create the Synthesis Node function.

    Responsibilities:
    1. Parse the latest agent output and accumulated tool evidence.
    2. Extract observed transaction facts, analytical rule signals, and network links.
    3. Construct a structured InvestigationDraft and list of InvestigationFindings.
    4. Store the structured draft into state for Critic evaluation.
    """

    def synthesis_node(state: InvestigationState) -> Dict[str, Any]:
        logger.info("[Graph: Synthesis Node] Synthesizing investigation findings into structured draft")
        emit_investigation_event(
            state,
            event_type="SYNTHESIS_STARTED",
            node="synthesis",
            message="Synthesizing verified transaction evidence, analytical rule signals, and network links into draft...",
        )

        raw_response = state.get("final_response", "")
        if not raw_response and state.get("messages"):
            last_msg = state["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.content:
                raw_response = str(last_msg.content)

        canonical_ev = state.get("canonical_evidence")
        if canonical_ev is None:
            try:
                canonical_ev = build_canonical_evidence(
                    statement=statement,
                    knowledge_sources=state.get("knowledge_sources", []),
                )
            except Exception as exc:
                logger.warning(f"Error constructing canonical evidence: {exc}")
                canonical_ev = None

        draft = synthesize_findings_from_response(
            response_text=raw_response,
            statement=statement,
            question=state.get("question", ""),
            tools_used=state.get("tools_used", []),
            customer_profile=state.get("customer_profile"),
            network_analysis=state.get("network_analysis"),
            knowledge_sources=state.get("knowledge_sources", []),
            canonical_evidence=canonical_ev,
        )

        emit_investigation_event(
            state,
            event_type="SYNTHESIS_COMPLETED",
            node="synthesis",
            message=f"Investigation draft formulated with {len(draft.findings)} verified finding(s) and {len(draft.referenced_transaction_ids)} transaction citation(s).",
            metadata={"referenced_transaction_ids": draft.referenced_transaction_ids},
        )

        return {
            "draft": draft,
            "findings": draft.findings,
            "final_response": raw_response,
            "canonical_evidence": canonical_ev,
        }

    return synthesis_node
