"""Deterministic Transaction Evidence Explorer service.

Assembles the complete factual and analytical evidence dossier for a specific transaction.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from aml_copilot.reporting.models import InvestigationReport


class TransactionEvidenceDossier(BaseModel):
    """Complete evidence dossier for a single transaction."""

    transaction_id: str
    date: Optional[str] = None
    amount: Optional[float] = None
    flow_type: Optional[str] = None
    counterparty: Optional[str] = None
    description: Optional[str] = None
    verified_in_statement: bool = True

    # Detection layers
    is_anomaly: bool = False
    anomaly_score: Optional[float] = None
    anomaly_features: Dict[str, float] = Field(default_factory=dict)

    rules_triggered: List[Dict[str, Any]] = Field(default_factory=list)
    network_patterns: List[Dict[str, Any]] = Field(default_factory=list)

    # Human review & convergence
    human_review_priority: Optional[str] = None
    human_review_reasons: List[str] = Field(default_factory=list)
    evidence_convergence_summary: Optional[str] = None
    signal_domains: List[str] = Field(default_factory=list)

    # Contextual typology guidance
    related_rag_guidance: List[Dict[str, str]] = Field(default_factory=list)


def build_transaction_dossier(
    report: InvestigationReport,
    transaction_id: str,
) -> Optional[TransactionEvidenceDossier]:
    """Deterministically assemble all evidence layers for a specific transaction."""
    tid = transaction_id.strip()

    # 1. Base statement evidence
    ev_item = next((e for e in report.observed_evidence if e.transaction_id == tid), None)
    if not ev_item:
        return None

    # 2. Anomaly findings
    anom_item = next((a for a in report.anomaly_findings if a.transaction_id == tid), None)
    is_anom = anom_item is not None
    anom_score = anom_item.anomaly_score if anom_item else None
    anom_features = anom_item.feature_context if anom_item else {}

    # 3. Rule triggers
    rules_triggered = []
    for r in report.detection_findings:
        if tid in r.supporting_transaction_ids:
            rules_triggered.append({
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "severity": r.severity,
                "explanation": r.explanation,
                "supporting_values": r.supporting_values,
            })

    # 4. Network findings
    network_patterns = []
    for n in report.network_findings:
        if tid in n.supporting_transaction_ids or (ev_item.counterparty and ev_item.counterparty in n.involved_nodes):
            network_patterns.append({
                "pattern_name": n.pattern_name,
                "description": n.description,
                "involved_nodes": n.involved_nodes,
            })

    # 5. Human review priority & reasons
    hr_item = None
    for h in report.human_review_items:
        h_tid = getattr(h, "transaction_id", h.get("transaction_id") if isinstance(h, dict) else "")
        if h_tid == tid:
            hr_item = h
            break

    prio = getattr(hr_item, "priority", hr_item.get("priority") if isinstance(hr_item, dict) else None) if hr_item else None
    reasons = getattr(hr_item, "reasons", hr_item.get("reasons", []) if isinstance(hr_item, dict) else []) if hr_item else []
    ev_summary = getattr(hr_item, "evidence_summary", hr_item.get("evidence_summary") if isinstance(hr_item, dict) else None) if hr_item else None

    # 6. Convergence
    conv_item = next((c for c in report.evidence_convergence if c.transaction_id == tid), None)
    domains = conv_item.signal_domains if conv_item else []
    if conv_item and conv_item.convergence_summary:
        ev_summary = conv_item.convergence_summary

    # 7. Related RAG guidance
    rag_guidance = [
        {
            "source": r.source,
            "title": r.title or r.source,
            "snippet": r.snippet or "",
        }
        for r in report.aml_reference_context
    ]

    return TransactionEvidenceDossier(
        transaction_id=tid,
        date=ev_item.date,
        amount=ev_item.amount,
        flow_type=ev_item.flow_type,
        counterparty=ev_item.counterparty,
        description=ev_item.description,
        verified_in_statement=ev_item.verified_in_statement,
        is_anomaly=is_anom,
        anomaly_score=anom_score,
        anomaly_features=anom_features,
        rules_triggered=rules_triggered,
        network_patterns=network_patterns,
        human_review_priority=prio,
        human_review_reasons=reasons,
        evidence_convergence_summary=ev_summary,
        signal_domains=domains,
        related_rag_guidance=rag_guidance,
    )
