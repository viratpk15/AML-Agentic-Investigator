"""Canonical Structured Evidence representation and deterministic provenance tracking.

Serves as the single source of truth for all investigation evidence:
- Deterministic rule findings
- Statistical anomalies (Isolation Forest)
- Customer profiling metrics
- Topological network findings
- Retrieved AML knowledge (RAG)
- Deterministic Human Review prioritization
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from aml_copilot.models.findings import DetectionResult
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.network.models import NetworkAnalysisResult
from aml_copilot.profiling.customer_profile import CustomerProfile


# ---------------------------------------------------------------------------
# Canonical Evidence Models
# ---------------------------------------------------------------------------

class CanonicalTransaction(BaseModel):
    """Universal canonical transaction model independent of input source (PDF, CSV, Excel, API, DB)."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    date: Optional[str] = Field(default=None, description="ISO format date (YYYY-MM-DD)")
    direction: str = Field(..., description="Flow direction ('credit' or 'debit')")
    amount: float = Field(..., description="Monetary amount of transaction")
    currency: str = Field(default="INR", description="Currency symbol or ISO code")
    counterparty: Optional[str] = Field(default=None, description="Counterparty entity name")
    description: Optional[str] = Field(default=None, description="Transaction narrative description")
    balance: Optional[float] = Field(default=None, description="Running account balance after transaction")
    source: str = Field(default="canonical_statement", description="Source provenance identifier")


class CanonicalRuleFinding(BaseModel):
    """Factual finding from a deterministic rule engine trigger."""

    finding_id: str = Field(..., description="Unique deterministic identifier for the finding")
    rule_id: str = Field(..., description="Programmatic identifier of the detection rule")
    rule_name: str = Field(..., description="Human-readable rule title")
    severity: str = Field(default="MEDIUM", description="Assigned severity (INFO, LOW, MEDIUM, HIGH)")
    observation: str = Field(..., description="Factual description of the triggered condition")
    evidence: str = Field(default="", description="Factual evidence string")
    supporting_transaction_ids: List[str] = Field(
        default_factory=list, description="Exact transactions triggering this rule"
    )
    supporting_transaction_details: List[Dict[str, Any]] = Field(
        default_factory=list, description="Factual transaction details verified against statement"
    )
    supporting_values: Dict[str, Any] = Field(
        default_factory=dict, description="Deterministic numeric values, ratios, and thresholds"
    )
    provenance: str = Field(default="rule_engine", description="Source provenance tracking")


class CanonicalAnomalyFinding(BaseModel):
    """Factual finding from unsupervised Isolation Forest anomaly detection."""

    transaction_id: str = Field(..., description="Flagged transaction identifier")
    anomaly_score: float = Field(..., description="Isolation Forest decision score")
    model: str = Field(default="isolation_forest", description="Model used for anomaly detection")
    status: str = Field(default="Statistical Outlier", description="Anomaly status label")
    feature_summary: Dict[str, float] = Field(
        default_factory=dict, description="Key numerical feature values for this transaction"
    )
    features: Dict[str, float] = Field(
        default_factory=dict, description="Key numerical feature values alias"
    )
    supporting_transaction_details: Dict[str, Any] = Field(
        default_factory=dict, description="Verified statement transaction fields"
    )
    provenance: str = Field(default="isolation_forest", description="Source provenance tracking")


class CanonicalProfile(BaseModel):
    """Deterministic behavioral profile metrics computed directly from statement."""

    customer_name: Optional[str] = None
    account_number: Optional[str] = None
    statement_period: Optional[str] = None
    total_transactions: int = 0
    total_credits: float = 0.0
    total_debits: float = 0.0
    net_cash_flow: float = 0.0
    average_transaction_amount: float = 0.0
    credit_to_debit_ratio: Optional[float] = None
    unique_counterparties: int = 0
    active_days: int = 0
    dominant_type: str = "balanced"
    largest_credit_amount: Optional[float] = None
    largest_debit_amount: Optional[float] = None
    indicators: List[str] = Field(default_factory=list)
    provenance: str = Field(default="customer_profiler", description="Source provenance tracking")

    @property
    def transaction_count(self) -> int:
        return self.total_transactions

    @property
    def net_flow(self) -> float:
        return self.net_cash_flow

    @property
    def average_transaction(self) -> float:
        return self.average_transaction_amount

    @property
    def peak_credit(self) -> Optional[float]:
        return self.largest_credit_amount

    @property
    def peak_debit(self) -> Optional[float]:
        return self.largest_debit_amount


class CanonicalNetworkFinding(BaseModel):
    """Topological relationship pattern identified from counterparty graph."""

    pattern_name: str = Field(..., description="Identifier of the topological network pattern")
    description: str = Field(..., description="Objective description of the graph pattern")
    counterparties: List[str] = Field(
        default_factory=list, description="Counterparties involved in the pattern"
    )
    involved_nodes: List[str] = Field(
        default_factory=list, description="Customer and counterparty entities involved"
    )
    supporting_transaction_ids: List[str] = Field(
        default_factory=list, description="Transactions establishing this network link"
    )
    details: Dict[str, Any] = Field(default_factory=dict)
    provenance: str = Field(default="network_analyzer", description="Source provenance tracking")


class CanonicalRAGEvidence(BaseModel):
    """Retrieved AML compliance typology or guidance reference."""

    source: str = Field(..., description="Guidance filename or document key")
    section: str = Field(default="General", description="Guidance section or topic heading")
    title: str = Field(default="", description="Reference document title")
    citation: str = Field(default="", description="Citation string")
    content: str = Field(default="", description="Relevant reference text")
    retrieved_text: str = Field(default="", description="Relevant guidance excerpt")
    relevance: float = Field(default=1.0, description="Relevance score")
    provenance: str = Field(default="aml_knowledge_base", description="Source provenance tracking")


class HumanReviewItem(BaseModel):
    """Deterministic priority item recommended for human compliance officer review."""

    transaction_id: str = Field(..., description="Unique transaction ID requiring review")
    date: Optional[str] = Field(default=None, description="Transaction date (ISO format)")
    amount: Optional[float] = Field(default=None, description="Transaction monetary amount")
    direction: Optional[str] = Field(default=None, description="Flow classification ('credit' or 'debit')")
    flow_type: Optional[str] = Field(default=None, description="Flow classification alias ('credit' or 'debit')")
    currency: str = Field(default="INR", description="Currency symbol or code")
    counterparty: Optional[str] = Field(default=None, description="Counterparty entity name")
    reasons: List[str] = Field(
        default_factory=list,
        description="Documented detection reasons qualifying this transaction for review",
    )
    domains: List[str] = Field(
        default_factory=list,
        description="Independent signal domains qualifying this transaction",
    )
    supporting_finding_ids: List[str] = Field(
        default_factory=list,
        description="IDs of rules or anomaly findings directly supporting this recommendation",
    )
    priority: str = Field(
        default="MEDIUM",
        description="Prioritized urgency based on signal convergence ('HIGH', 'MEDIUM', 'LOW')",
    )
    evidence_summary: str = Field(
        default="",
        description="Factual summary of evidence convergence for human reviewer",
    )
    provenance: str = Field(
        default="evidence_convergence",
        description="Source provenance tracking",
    )


class CanonicalEvidence(BaseModel):
    """Single source of truth containing all structured, factual investigation evidence."""

    customer_name: Optional[str] = None
    account_number: Optional[str] = None
    statement_period: Optional[str] = None
    total_transactions: int = 0

    canonical_transactions: List[CanonicalTransaction] = Field(default_factory=list)
    rule_findings: List[CanonicalRuleFinding] = Field(default_factory=list)
    statistical_anomalies: List[CanonicalAnomalyFinding] = Field(default_factory=list)
    customer_profile: Optional[CanonicalProfile] = None
    network_findings: List[CanonicalNetworkFinding] = Field(default_factory=list)
    network_unique_counterparties: int = 0
    network_graph_nodes: int = 0
    network_graph_edges: int = 0
    network_dominant_counterparties: List[str] = Field(default_factory=list)
    rag_evidence: List[CanonicalRAGEvidence] = Field(default_factory=list)

    human_review_items: List[HumanReviewItem] = Field(default_factory=list)
    all_flagged_transaction_ids: List[str] = Field(default_factory=list)

    def get_transaction(self, transaction_id: str) -> Optional[CanonicalTransaction]:
        """Retrieve a specific canonical transaction by ID."""
        for t in self.canonical_transactions:
            if t.transaction_id == transaction_id:
                return t
        return None

    def high_value_transactions(self, threshold: float = 200000.0) -> List[CanonicalTransaction]:
        """Deterministically filter transactions meeting or exceeding configured monitoring threshold."""
        return [t for t in self.canonical_transactions if t.amount >= threshold]


    @property
    def anomaly_transaction_ids(self) -> List[str]:
        """Return the exact list of transaction IDs flagged by Isolation Forest."""
        return [a.transaction_id for a in self.statistical_anomalies]

    @property
    def rule_transaction_ids(self) -> List[str]:
        """Return all transaction IDs that triggered at least one deterministic rule."""
        ids: List[str] = []
        for rf in self.rule_findings:
            for tid in rf.supporting_transaction_ids:
                if tid not in ids:
                    ids.append(tid)
        return ids


# ---------------------------------------------------------------------------
# Deterministic Builder Functions
# ---------------------------------------------------------------------------

# Signal domain mapping to identify truly independent detection categories
SIGNAL_DOMAINS: Dict[str, str] = {
    # ML Anomaly
    "STATISTICAL_ANOMALY": "ML_ANOMALY",
    # Specific Behavioral Typology Rules
    "RULE_RAPID_MOVEMENT_OF_FUNDS": "FLOW_TYPOLOGY",
    "RULE_LARGE_INFLOW_RAPID_OUTFLOW": "FLOW_TYPOLOGY",
    "RULE_SUDDEN_VOLUME_INCREASE": "FLOW_TYPOLOGY",
    "RULE_STRUCTURING_SUSPECTED": "FLOW_TYPOLOGY",
    # Specific Monetary Threshold Rules
    "RULE_LARGE_TRANSACTION": "THRESHOLD",
    "RULE_ROUND_AMOUNT": "THRESHOLD",
    # Network Graph Relational Hub Patterns
    "NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY": "NETWORK_HUB",
    "NETWORK_CYCLE": "NETWORK_HUB",
    "NETWORK_FAN_OUT_RAPID": "NETWORK_HUB",
    # Broad Structural Baseline Rules (statement/account level)
    "RULE_MANY_NEW_COUNTERPARTIES": "COUNTERPARTY_BURST",
    "NETWORK_ONE_TO_MANY_TOPOLOGY": "NETWORK_TOPOLOGY",
}


def select_human_review_items(
    statement: TransactionStatement,
    rule_findings: List[CanonicalRuleFinding],
    statistical_anomalies: List[CanonicalAnomalyFinding],
    network_findings: Optional[List[CanonicalNetworkFinding]] = None,
) -> List[HumanReviewItem]:
    """Deterministically select and prioritize transactions for Human Review based on evidence convergence.

    Guiding Principles:
    1. Human Review is a prioritized actionable subset, not a replica of all statement transactions.
    2. Excludes transactions that only exhibit broad structural baseline characteristics
       (e.g., general new counterparty or one-to-many topology) without any specific transactional risk.
    3. Multi-signal convergence hierarchy:
       - HIGH: strong multi-signal convergence (e.g. ML anomaly corroborated by typology rules,
         or 3+ independent signal categories, or multiple high-risk typology rules converging).
         Never assigned merely because a transaction exists in a single rule output.
       - MEDIUM: meaningful independent signals (e.g. 2 independent signal categories,
         or standalone ML statistical anomaly).
       - LOW: isolated/weak signal (e.g. single threshold rule without corroboration).
    4. Deterministic sorting: priority (HIGH > MEDIUM > LOW), distinct domains descending,
       reason count descending, monetary amount descending.
    5. No positional statement-order fallbacks; all items traceable to real finding IDs.
    """
    stmt_txns = {t.transaction_id: t for t in statement.transactions if t.transaction_id}
    net_findings = network_findings or []

    # Map transaction ID -> list of reasons and finding IDs
    txn_reasons: Dict[str, List[str]] = {}
    txn_finding_ids: Dict[str, List[str]] = {}

    # 1. Collect rule signals
    for rf in rule_findings:
        for tid in rf.supporting_transaction_ids:
            if tid not in stmt_txns:
                continue
            r_tag = rf.rule_id if rf.rule_id.startswith("RULE_") else f"RULE_{rf.rule_id}"
            txn_reasons.setdefault(tid, []).append(r_tag)
            txn_finding_ids.setdefault(tid, []).append(rf.finding_id)

    # 2. Collect Isolation Forest anomalies
    for af in statistical_anomalies:
        tid = af.transaction_id
        if tid not in stmt_txns:
            continue
        txn_reasons.setdefault(tid, []).append("STATISTICAL_ANOMALY")
        txn_finding_ids.setdefault(tid, []).append(f"ANOMALY_{tid}")

    # 3. Collect network connections
    for nf in net_findings:
        for tid in nf.supporting_transaction_ids:
            if tid not in stmt_txns:
                continue
            n_tag = nf.pattern_name.upper()
            if not n_tag.startswith("NETWORK_"):
                n_tag = f"NETWORK_{n_tag}"
            txn_reasons.setdefault(tid, []).append(n_tag)
            txn_finding_ids.setdefault(tid, []).append(f"NET_{nf.pattern_name}")

    items: List[HumanReviewItem] = []

    for tid, reasons in txn_reasons.items():
        t = stmt_txns[tid]
        amt = t.credit if t.credit is not None else t.debit
        direction = "credit" if t.credit is not None else "debit"
        finding_ids = sorted(list(set(txn_finding_ids.get(tid, []))))
        distinct_reasons = sorted(list(set(reasons)))

        # Categorize into independent signal domains
        domains = {SIGNAL_DOMAINS.get(r, "OTHER") for r in distinct_reasons}
        specific_risk_domains = domains - {"COUNTERPARTY_BURST", "NETWORK_TOPOLOGY", "OTHER"}

        # Filter out transactions that only triggered broad structural background rules
        # (e.g., standard debit payments that only matched general counterparty surge or one-to-many graph)
        if not specific_risk_domains:
            continue

        has_anomaly = "ML_ANOMALY" in domains
        has_typology = "FLOW_TYPOLOGY" in domains
        has_threshold = "THRESHOLD" in domains
        has_hub = "NETWORK_HUB" in domains
        domain_count = len(domains)

        # Multi-signal convergence prioritization
        # - HIGH: strong multi-signal convergence (ML anomaly + rules/network, or >=3 independent domains,
        #   or high-risk typology + threshold/network). Never assigned merely for being in a rule output.
        if (
            (has_anomaly and (has_typology or has_threshold or has_hub))
            or domain_count >= 3
            or (has_typology and (has_threshold or has_hub))
        ):
            priority = "HIGH"
        elif domain_count >= 2 or has_anomaly or has_typology:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        # Construct clear evidence summary for human reviewer
        summary_parts = []
        if has_anomaly:
            summary_parts.append("flagged by Isolation Forest unsupervised anomaly model")
        typology_rules = [r.replace("RULE_", "") for r in distinct_reasons if SIGNAL_DOMAINS.get(r) == "FLOW_TYPOLOGY"]
        if typology_rules:
            summary_parts.append(f"triggered flow typology rule(s): {', '.join(typology_rules)}")
        threshold_rules = [r.replace("RULE_", "") for r in distinct_reasons if SIGNAL_DOMAINS.get(r) == "THRESHOLD"]
        if threshold_rules:
            summary_parts.append(f"triggered threshold signal(s): {', '.join(threshold_rules)}")
        if has_hub:
            summary_parts.append("involved in high-value counterparty hub or cyclical network flow")
        if "COUNTERPARTY_BURST" in domains:
            summary_parts.append("part of new counterparty volume surge")

        evidence_summary = (
            f"Transaction {tid} ({direction.upper()} of ₹{amt:,.2f} on {t.date}) "
            f"qualifies for review: {'; '.join(summary_parts)}."
            if amt is not None
            else f"Transaction {tid} qualifies for review: {'; '.join(summary_parts)}."
        )

        items.append(
            HumanReviewItem(
                transaction_id=tid,
                date=t.date.isoformat() if t.date else None,
                amount=amt,
                direction=direction,
                flow_type=direction,
                counterparty=t.counterparty,
                reasons=distinct_reasons,
                domains=sorted(list(domains)),
                supporting_finding_ids=finding_ids,
                priority=priority,
                evidence_summary=evidence_summary,
                provenance="evidence_convergence",
            )
        )

    # Fallback: if all transactions only had broad structural rules, retain them as LOW so shortlist is not empty
    if not items and txn_reasons:
        for tid, reasons in txn_reasons.items():
            t = stmt_txns[tid]
            amt = t.credit if t.credit is not None else t.debit
            dir_val = "credit" if t.credit is not None else "debit"
            fb_distinct = sorted(list(set(reasons)))
            fb_domains = sorted(list({SIGNAL_DOMAINS.get(r, "OTHER") for r in fb_distinct}))
            items.append(
                HumanReviewItem(
                    transaction_id=tid,
                    date=t.date.isoformat() if t.date else None,
                    amount=amt,
                    direction=dir_val,
                    flow_type=dir_val,
                    counterparty=t.counterparty,
                    reasons=fb_distinct,
                    domains=fb_domains,
                    supporting_finding_ids=sorted(list(set(txn_finding_ids.get(tid, [])))),
                    priority="LOW",
                    evidence_summary=f"Transaction {tid} noted under structural baseline rule screening.",
                    provenance="evidence_convergence",
                )
            )

    # Sort deterministically by convergence:
    # 1. Priority rank (HIGH: 3, MEDIUM: 2, LOW: 1)
    # 2. Statistical anomaly presence (Isolation Forest outliers prioritized)
    # 3. Number of distinct independent signal domains descending
    # 4. Number of distinct reasons descending
    # 5. Monetary amount descending
    priority_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    items.sort(
        key=lambda x: (
            priority_order.get(x.priority, 0),
            1 if "STATISTICAL_ANOMALY" in x.reasons else 0,
            len({SIGNAL_DOMAINS.get(r, 'OTHER') for r in x.reasons}),
            len(x.reasons),
            x.amount or 0.0,
        ),
        reverse=True,
    )

    return items


def build_canonical_evidence(
    statement: TransactionStatement,
    detection_result: Optional[DetectionResult] = None,
    profile: Optional[CustomerProfile] = None,
    network_result: Optional[NetworkAnalysisResult] = None,
    knowledge_sources: Optional[List[str]] = None,
) -> CanonicalEvidence:
    """Construct the canonical single source of truth for an investigation.

    All evidence layers are strictly reconciled against statement transactions.
    """
    from aml_copilot.ml.pipeline import run_detection
    from aml_copilot.network.analysis import build_transaction_network
    from aml_copilot.profiling.profiler import build_customer_profile

    stmt_txns = {t.transaction_id: t for t in statement.transactions if t.transaction_id}

    # Populate universal canonical transactions
    canonical_txns: List[CanonicalTransaction] = []
    for t in statement.transactions:
        if not t.transaction_id:
            continue
        dir_val = "credit" if t.credit is not None else "debit"
        amt_val = t.credit if t.credit is not None else (t.debit or 0.0)
        canonical_txns.append(
            CanonicalTransaction(
                transaction_id=t.transaction_id,
                date=t.date.isoformat() if t.date else None,
                direction=dir_val,
                amount=round(amt_val, 2),
                currency="INR",
                counterparty=t.counterparty,
                description=t.description,
                balance=round(t.balance, 2) if t.balance is not None else None,
                source="canonical_statement",
            )
        )

    # 1. Detection findings (Rules & Isolation Forest)
    if detection_result is None:
        try:
            detection_result = run_detection(statement)
        except Exception:
            detection_result = None

    rule_findings: List[CanonicalRuleFinding] = []
    statistical_anomalies: List[CanonicalAnomalyFinding] = []
    flagged_ids_set = set()

    if detection_result:
        for idx, rs in enumerate(detection_result.rule_signals):
            verified_tids = [tid for tid in rs.transaction_ids if tid in stmt_txns]
            verified_details = []
            for tid in verified_tids:
                t = stmt_txns[tid]
                verified_details.append({
                    "transaction_id": tid,
                    "date": t.date.isoformat() if t.date else None,
                    "amount": t.credit if t.credit is not None else t.debit,
                    "flow_type": "credit" if t.credit is not None else "debit",
                    "counterparty": t.counterparty,
                })
                flagged_ids_set.add(tid)

            finding_id = f"FINDING-RULE-{idx + 1:03d}-{rs.rule_id}"
            rule_findings.append(
                CanonicalRuleFinding(
                    finding_id=finding_id,
                    rule_id=rs.rule_id,
                    rule_name=rs.rule_name,
                    severity=rs.severity.value if hasattr(rs.severity, "value") else str(rs.severity),
                    observation=rs.explanation,
                    supporting_transaction_ids=verified_tids,
                    supporting_transaction_details=verified_details,
                    supporting_values=rs.supporting_values,
                )
            )

        for ans in detection_result.anomaly_signals:
            if ans.is_anomaly and ans.transaction_id in stmt_txns:
                t = stmt_txns[ans.transaction_id]
                t_details = {
                    "transaction_id": ans.transaction_id,
                    "date": t.date.isoformat() if t.date else None,
                    "amount": t.credit if t.credit is not None else t.debit,
                    "flow_type": "credit" if t.credit is not None else "debit",
                    "counterparty": t.counterparty,
                }
                flagged_ids_set.add(ans.transaction_id)
                statistical_anomalies.append(
                    CanonicalAnomalyFinding(
                        transaction_id=ans.transaction_id,
                        anomaly_score=round(ans.anomaly_score, 4),
                        status="Statistical Outlier",
                        feature_summary=ans.feature_context,
                        supporting_transaction_details=t_details,
                    )
                )

    # 2. Customer Profile
    if profile is None:
        try:
            profile = build_customer_profile(statement)
        except Exception:
            profile = None

    canonical_profile = None
    if profile:
        canonical_profile = CanonicalProfile(
            customer_name=profile.customer_name or statement.customer_name,
            account_number=profile.account_number or statement.account_number,
            statement_period=profile.statement_period or statement.statement_period,
            total_transactions=profile.total_transactions,
            total_credits=round(profile.total_credits, 2),
            total_debits=round(profile.total_debits, 2),
            net_cash_flow=round(profile.net_cash_flow, 2),
            average_transaction_amount=round(profile.average_transaction_amount, 2),
            credit_to_debit_ratio=round(profile.credit_to_debit_ratio, 4) if profile.credit_to_debit_ratio else None,
            unique_counterparties=profile.unique_counterparty_count,
            active_days=profile.active_days,
            dominant_type=profile.dominant_transaction_type,
            largest_credit_amount=profile.largest_credit.amount if profile.largest_credit else None,
            largest_debit_amount=profile.largest_debit.amount if profile.largest_debit else None,
            indicators=[ind.description for ind in profile.indicators],
        )

    # 3. Network Findings
    if network_result is None:
        try:
            network_result = build_transaction_network(statement)
        except Exception:
            network_result = None

    network_findings: List[CanonicalNetworkFinding] = []
    if network_result:
        for pat in network_result.observable_patterns:
            verified_net_tids = [tid for tid in pat.supporting_transaction_ids if tid in stmt_txns]
            for tid in verified_net_tids:
                flagged_ids_set.add(tid)
            network_findings.append(
                CanonicalNetworkFinding(
                    pattern_name=pat.pattern_name,
                    description=pat.description,
                    involved_nodes=pat.involved_nodes,
                    supporting_transaction_ids=verified_net_tids,
                    details=pat.details,
                )
            )

    # 4. RAG Evidence
    rag_evidence: List[CanonicalRAGEvidence] = []
    for src in (knowledge_sources or []):
        title = src.replace(".md", "").replace("_", " ").title()
        rag_evidence.append(
            CanonicalRAGEvidence(
                source=src,
                section="Typology Guidance",
                citation=title,
                retrieved_text=f"Retrieved reference guidance from {src}.",
            )
        )

    # 5. Deterministic Human Review Selection
    human_review_items = select_human_review_items(
        statement=statement,
        rule_findings=rule_findings,
        statistical_anomalies=statistical_anomalies,
        network_findings=network_findings,
    )

    all_flagged_list = sorted(list(flagged_ids_set))

    net_unique_cps = (
        network_result.metrics.unique_counterparties
        if (network_result and network_result.metrics)
        else (canonical_profile.unique_counterparties if canonical_profile else 0)
    )
    net_nodes = len(network_result.nodes) if network_result else (net_unique_cps + 1)
    net_edges = len(network_result.edges) if network_result else 0
    net_dom = (
        [network_result.metrics.largest_counterparty_by_volume]
        if (network_result and network_result.metrics and network_result.metrics.largest_counterparty_by_volume)
        else []
    )

    return CanonicalEvidence(
        customer_name=statement.customer_name,
        account_number=statement.account_number,
        statement_period=statement.statement_period,
        total_transactions=statement.total_transactions,
        canonical_transactions=canonical_txns,
        rule_findings=rule_findings,
        statistical_anomalies=statistical_anomalies,
        customer_profile=canonical_profile,
        network_findings=network_findings,
        network_unique_counterparties=net_unique_cps,
        network_graph_nodes=net_nodes,
        network_graph_edges=net_edges,
        network_dominant_counterparties=net_dom,
        rag_evidence=rag_evidence,
        human_review_items=human_review_items,
        all_flagged_transaction_ids=all_flagged_list,
    )


def reconcile_customer_profile(
    profile: Optional[CanonicalProfile],
    canonical_transactions: List[CanonicalTransaction],
) -> None:
    """Enforce strict mathematical reconciliation invariants between customer profile and canonical transactions.

    Invariants:
    1. profile.transaction_count == len(transactions)
    2. profile.total_credits == calculated_total_credits
    3. profile.total_debits == calculated_total_debits
    4. profile.net_flow == total_credits - total_debits
    5. profile.unique_counterparties == calculated_unique_counterparties
    6. profile.peak_credit == calculated_peak_credit
    7. profile.peak_debit == calculated_peak_debit

    Raises:
        ReportReconciliationError: If any invariant is violated.
    """
    from aml_copilot.exceptions import ReportReconciliationError

    if profile is None or not canonical_transactions:
        return

    txns = canonical_transactions

    # Invariant 1: Transaction count
    if profile.total_transactions != len(txns):
        raise ReportReconciliationError(
            f"Profile transaction_count invariant failed: profile has {profile.total_transactions}, "
            f"canonical transactions count is {len(txns)}."
        )

    # Invariant 2: Total credits
    calc_credits = round(sum(t.amount for t in txns if t.direction == "credit"), 2)
    if abs(profile.total_credits - calc_credits) > 0.05:
        raise ReportReconciliationError(
            f"Profile total_credits invariant failed: profile has ₹{profile.total_credits:,.2f}, "
            f"reconciled sum is ₹{calc_credits:,.2f}."
        )

    # Invariant 3: Total debits
    calc_debits = round(sum(t.amount for t in txns if t.direction == "debit"), 2)
    if abs(profile.total_debits - calc_debits) > 0.05:
        raise ReportReconciliationError(
            f"Profile total_debits invariant failed: profile has ₹{profile.total_debits:,.2f}, "
            f"reconciled sum is ₹{calc_debits:,.2f}."
        )

    # Invariant 4: Net flow
    calc_net_flow = round(calc_credits - calc_debits, 2)
    if abs(profile.net_cash_flow - calc_net_flow) > 0.05:
        raise ReportReconciliationError(
            f"Profile net_flow invariant failed: profile has ₹{profile.net_cash_flow:,.2f}, "
            f"reconciled net flow is ₹{calc_net_flow:,.2f}."
        )

    # Invariant 5: Unique counterparties
    calc_cps = len(set(t.counterparty.strip() for t in txns if t.counterparty and t.counterparty.strip()))
    if profile.unique_counterparties != calc_cps:
        raise ReportReconciliationError(
            f"Profile unique_counterparties invariant failed: profile has {profile.unique_counterparties}, "
            f"reconciled count is {calc_cps}."
        )

    # Invariant 6: Peak credit
    credit_amts = [t.amount for t in txns if t.direction == "credit"]
    calc_peak_credit = max(credit_amts) if credit_amts else None
    if calc_peak_credit is not None and profile.largest_credit_amount is not None:
        if abs(profile.largest_credit_amount - calc_peak_credit) > 0.05:
            raise ReportReconciliationError(
                f"Profile peak_credit invariant failed: profile has ₹{profile.largest_credit_amount:,.2f}, "
                f"reconciled peak credit is ₹{calc_peak_credit:,.2f}."
            )

    # Invariant 7: Peak debit
    debit_amts = [t.amount for t in txns if t.direction == "debit"]
    calc_peak_debit = max(debit_amts) if debit_amts else None
    if calc_peak_debit is not None and profile.largest_debit_amount is not None:
        if abs(profile.largest_debit_amount - calc_peak_debit) > 0.05:
            raise ReportReconciliationError(
                f"Profile peak_debit invariant failed: profile has ₹{profile.largest_debit_amount:,.2f}, "
                f"reconciled peak debit is ₹{calc_peak_debit:,.2f}."
            )

    return True

