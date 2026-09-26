"""Strongly typed Pydantic models for AML Investigation Reports."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """Factual transaction evidence verified directly against the customer statement."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    date: Optional[str] = Field(default=None, description="ISO format date of transaction")
    amount: Optional[float] = Field(default=None, description="Monetary transaction amount")
    flow_type: Optional[str] = Field(default=None, description="Flow classification: 'credit' or 'debit'")
    counterparty: Optional[str] = Field(default=None, description="Counterparty entity or recipient")
    description: Optional[str] = Field(default=None, description="Transaction narrative text")
    verified_in_statement: bool = Field(
        default=True,
        description="Whether this transaction was verified deterministically against statement records",
    )


class DetectionFindingItem(BaseModel):
    """Deterministic AML rule signal identified during screening."""

    rule_id: str = Field(..., description="Programmatic identifier of the detection rule")
    rule_name: str = Field(..., description="Human-readable title of the rule")
    severity: str = Field(default="MEDIUM", description="Assigned severity level (e.g. LOW, MEDIUM, HIGH)")
    explanation: str = Field(..., description="Objective explanation of the triggered rule condition")
    supporting_transaction_ids: List[str] = Field(
        default_factory=list, description="Transactions triggering this rule signal"
    )
    supporting_values: Dict[str, Any] = Field(
        default_factory=dict, description="Deterministic metrics, computed ratios, and thresholds"
    )


class AnomalyFindingItem(BaseModel):
    """Statistical outlier identified by Isolation Forest unsupervised detection."""

    transaction_id: str = Field(..., description="Identifier of the flagged transaction")
    anomaly_score: float = Field(..., description="Isolation Forest decision score")
    is_anomaly: bool = Field(default=True, description="Whether flagged as a statistical outlier")
    feature_context: Dict[str, float] = Field(
        default_factory=dict, description="Key numerical feature metrics for this transaction"
    )


class CustomerProfileSummary(BaseModel):
    """Concise behavioral profile summary for the customer."""

    customer_name: Optional[str] = Field(default=None, description="Account holder name")
    account_number: Optional[str] = Field(default=None, description="Account number")
    statement_period: Optional[str] = Field(default=None, description="Covered statement period")
    total_transactions: int = Field(default=0, description="Total count of transactions")
    total_credits: float = Field(default=0.0, description="Sum of incoming credits")
    total_debits: float = Field(default=0.0, description="Sum of outgoing debits")
    net_cash_flow: float = Field(default=0.0, description="Net difference between credits and debits")
    average_transaction_amount: float = Field(default=0.0, description="Average transaction size")
    credit_to_debit_ratio: Optional[float] = Field(default=None, description="Ratio of credits to debits")
    unique_counterparties: int = Field(default=0, description="Count of distinct counterparties")
    active_days: int = Field(default=0, description="Number of active transactional days")
    dominant_type: str = Field(default="balanced", description="Dominant cash flow direction")
    largest_credit_amount: Optional[float] = Field(default=None, description="Peak single incoming amount")
    largest_debit_amount: Optional[float] = Field(default=None, description="Peak single outgoing amount")
    indicators: List[str] = Field(
        default_factory=list, description="Observed behavioral indicator descriptions"
    )


class NetworkFindingItem(BaseModel):
    """Topological counterparty pattern identified via NetworkX analysis."""

    pattern_name: str = Field(..., description="Identifier of the topological pattern")
    description: str = Field(..., description="Objective description of the relational flow structure")
    involved_nodes: List[str] = Field(
        default_factory=list, description="Entities involved in the network pattern"
    )
    supporting_transaction_ids: List[str] = Field(
        default_factory=list, description="Transactions establishing this network connection"
    )


class KnowledgeReferenceItem(BaseModel):
    """Educational AML typology or compliance guidance retrieved via RAG."""

    source: str = Field(..., description="Document filename or source identifier")
    title: Optional[str] = Field(default=None, description="Reference title or topic")
    snippet: Optional[str] = Field(default=None, description="Explanatory excerpt from guidance text")


class RuleSummaryGroup(BaseModel):
    """Grouped summary of deterministic rule findings by rule type to prevent repetitive narrative output."""

    rule_id: str = Field(..., description="Programmatic identifier of the detection rule")
    rule_name: str = Field(..., description="Human-readable title of the rule")
    count: int = Field(..., description="Total count of transactions/instances triggering this rule")
    severity_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Counts of triggers categorized by severity"
    )
    supporting_transaction_ids: List[str] = Field(
        default_factory=list, description="All unique transaction IDs triggering this rule"
    )
    representative_examples: List[str] = Field(
        default_factory=list, description="Key representative examples with amounts and dates"
    )
    observation_summary: str = Field(
        default="", description="Objective description of the triggered rule condition"
    )


class NetworkSummary(BaseModel):
    """Clear structural breakdown of network graph topology distinguishing entities from nodes."""

    unique_counterparties: int = Field(
        default=0, description="Count of distinct external counterparty entities identified"
    )
    graph_nodes: int = Field(
        default=0, description="Total nodes in graph (customer account node + distinct counterparties)"
    )
    graph_edges: int = Field(
        default=0, description="Total directed transaction edges connecting entities"
    )
    dominant_counterparties: List[str] = Field(
        default_factory=list, description="Prominent counterparties by volume or concentration"
    )


class EvidenceConvergenceItem(BaseModel):
    """Multi-signal evidence convergence for a prioritized review item."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    date: Optional[str] = Field(default=None, description="ISO format date")
    amount: Optional[float] = Field(default=None, description="Monetary transaction amount")
    direction: Optional[str] = Field(default=None, description="Flow classification: 'credit' or 'debit'")
    flow_type: Optional[str] = Field(default=None, description="Flow classification alias: 'credit' or 'debit'")
    counterparty: Optional[str] = Field(default=None, description="Counterparty entity or recipient")
    priority: str = Field(default="MEDIUM", description="Assigned priority: 'HIGH', 'MEDIUM', 'LOW'")
    signal_domains: List[str] = Field(
        default_factory=list,
        description="Independent signal domains: Rule, Flow, Statistical, Volume, Network",
    )
    reasons: List[str] = Field(
        default_factory=list, description="Specific triggers qualifying this transaction"
    )
    supporting_finding_ids: List[str] = Field(
        default_factory=list, description="Underlying finding identifiers supporting convergence"
    )
    convergence_summary: str = Field(
        default="", description="Factual multi-signal convergence narrative"
    )


class CriticSummary(BaseModel):
    """Summary of adversarial audit performed by the Critic node."""

    passed: bool = Field(..., description="Whether the investigation draft satisfied all audit criteria")
    status: str = Field(default="PASS", description="Audit outcome status ('PASS' or 'FAIL')")
    statement_transaction_count: int = Field(
        default=0, description="Total transactions in statement"
    )
    narrative_transaction_reference_count: int = Field(
        default=0, description="Count of distinct transaction IDs cited in narrative text"
    )
    human_review_transaction_count: int = Field(
        default=0, description="Total transactions in prioritized human review queue"
    )
    verified_transaction_reference_count: int = Field(
        default=0, description="Count of cited transaction references confirmed in statement"
    )
    unverified_transaction_reference_count: int = Field(
        default=0, description="Count of cited transaction references that do not exist"
    )
    issues: List[str] = Field(
        default_factory=list, description="Discrepancies, unsupported claims, or omissions flagged"
    )
    missing_evidence: List[str] = Field(
        default_factory=list, description="Required evidence items identified as missing"
    )
    unsupported_claims: List[str] = Field(
        default_factory=list, description="Assertions flagged as lacking factual basis in statement"
    )
    safety_violations: List[str] = Field(
        default_factory=list, description="Violations of AML non-judgmental / non-accusatory bounds"
    )
    checked_transaction_ids: List[str] = Field(
        default_factory=list, description="Transaction identifiers verified against statement"
    )
    invalid_transaction_ids: List[str] = Field(
        default_factory=list, description="Cited identifiers that do not exist in statement"
    )
    required_revisions: List[str] = Field(
        default_factory=list, description="Actionable revision instructions issued to Investigator"
    )


class RevisionSummary(BaseModel):
    """Record of self-correction revision cycles executed."""

    revision_count: int = Field(default=0, description="Total number of revision cycles performed")
    max_revisions: int = Field(default=2, description="Maximum permitted revision attempts")
    revisions_applied: bool = Field(default=False, description="Whether revision feedback was incorporated")
    unresolved_limitations: bool = Field(
        default=False, description="Whether audit concluded with unaddressed Critic warnings"
    )


class InvestigationReport(BaseModel):
    """Comprehensive, evidence-grounded AML Investigation Report following the 14-section standard."""

    report_id: str = Field(..., description="Unique report identifier (e.g. REP-AML-2026-...)")
    generated_at: str = Field(..., description="ISO 8601 UTC timestamp of report generation")
    customer_name: str = Field(default="Unknown Customer", description="Name of the account holder under investigation")
    account_number: str = Field(default="Unknown Account", description="Account number under investigation")
    statement_period: str = Field(default="Unknown Period", description="Period covered by transaction statement")
    investigation_question: str = Field(..., description="The query guiding the investigation")
    total_transactions_analyzed: int = Field(default=0, description="Total count of analyzed transactions")

    # Section 2: Executive Summary
    executive_summary: str = Field(..., description="Concise high-level synthesis of investigative findings")
    executive_summary_bullets: List[str] = Field(
        default_factory=list, description="5-8 concise executive summary bullet points"
    )

    # Section 3: Observed Evidence
    observed_evidence: List[EvidenceItem] = Field(
        default_factory=list, description="Verified factual transactions referenced in findings"
    )

    # Section 4: Detection Findings
    rule_summary_groups: List[RuleSummaryGroup] = Field(
        default_factory=list, description="Grouped rule findings avoiding repetitive output"
    )
    detection_findings: List[DetectionFindingItem] = Field(
        default_factory=list, description="Triggered deterministic AML rule signals"
    )
    anomaly_findings: List[AnomalyFindingItem] = Field(
        default_factory=list, description="Statistical anomaly signals flagged by Isolation Forest"
    )

    # Section 5: Customer Profile
    customer_profile: Optional[CustomerProfileSummary] = Field(
        default=None, description="Behavioral profile and baseline metrics"
    )

    # Section 6: Network Analysis
    network_summary: Optional[NetworkSummary] = Field(
        default=None, description="Network topology summary distinguishing counterparties from nodes"
    )
    network_findings: List[NetworkFindingItem] = Field(
        default_factory=list, description="Topological counterparty relationship patterns"
    )

    # Section 7: AML Reference Context
    aml_reference_context: List[KnowledgeReferenceItem] = Field(
        default_factory=list, description="Educational AML guidance retrieved for contextual reference"
    )

    # Section 8: Evidence Convergence
    evidence_convergence: List[EvidenceConvergenceItem] = Field(
        default_factory=list, description="Top prioritized review items demonstrating multi-signal convergence"
    )

    # Section 9 & 14: Human Review Queue
    human_review_items: List[Any] = Field(
        default_factory=list,
        description="Deterministic list of prioritized transactions flagged for human compliance review",
    )
    human_review_summary: Dict[str, Any] = Field(
        default_factory=dict, description="Summary breakdown of review items by priority"
    )

    # Section 10: Interpretation
    interpretation: str = Field(
        default="", description="Objective interpretation connecting observed facts to typologies"
    )

    # Section 11: Limitations
    limitations: List[str] = Field(
        default_factory=list, description="Scope boundaries, sample size constraints, and disclaimers"
    )

    # Section 12: Recommended Next Steps
    next_steps: List[str] = Field(
        default_factory=list, description="Neutral compliance-investigation recommended next steps"
    )

    # Section 13: Critic Validation & Revision
    critic_validation: CriticSummary = Field(
        ..., description="Adversarial audit review and factual verification status"
    )
    revision_history: RevisionSummary = Field(
        ..., description="Record of revision cycles and loop guard enforcement"
    )

    human_review_recommendation: str = Field(
        default=(
            "This investigation report is an automated analytical aid for compliance analysis. "
            "Final determinations regarding regulatory reporting, customer due diligence, and account "
            "status remain the exclusive responsibility of qualified human compliance officers."
        ),
        description="Mandatory compliance boundary statement for human review",
    )
    evidence_validation_passed: bool = Field(
        default=True,
        description="Whether report passed deterministic provenance validation against canonical evidence",
    )

