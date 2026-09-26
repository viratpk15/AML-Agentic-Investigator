"""Structured models for investigation findings, evidence references, drafts, and critique results."""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class EvidenceReference(BaseModel):
    """Reference to factual evidence supporting an investigative finding."""

    source_type: Literal["transaction", "detection", "profile", "network", "knowledge"] = Field(
        ..., description="Category of evidence source"
    )
    transaction_ids: List[str] = Field(
        default_factory=list, description="Associated transaction identifiers"
    )
    description: str = Field(default="", description="Summary of the supporting factual evidence")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Underlying numerical values, dates, or rule triggers"
    )


class InvestigationFinding(BaseModel):
    """A specific factual finding or observation discovered during an AML investigation."""

    finding: str = Field(..., description="Concise statement of the observed finding")
    evidence: Union[List[EvidenceReference], List[str], str] = Field(
        default_factory=list, description="Structured supporting evidence records"
    )
    transaction_ids: List[str] = Field(
        default_factory=list, description="Unique transaction IDs directly relevant to this finding"
    )
    source_type: str = Field(
        default="transaction", description="Primary source or tool providing the finding"
    )
    explanation: str = Field(
        default="", description="Detailed contextual explanation connecting evidence to finding"
    )
    confidence: Optional[str] = Field(
        default="preliminary", description="Preliminary confidence assessment (e.g. high, preliminary)"
    )


class InvestigationDraft(BaseModel):
    """Structured draft of the investigation before critique and revision."""

    question: str = Field(..., description="The original analyst investigation question")
    summary: str = Field(default="", description="High-level synthesis summary")
    observed_evidence: List[str] = Field(
        default_factory=list, description="Factual evidence directly observed in statements"
    )
    analytical_findings: List[str] = Field(
        default_factory=list, description="Findings produced by rules, metrics, or anomaly detection"
    )
    network_findings: List[str] = Field(
        default_factory=list, description="Observations regarding counterparty relationships and flows"
    )
    reference_context: List[str] = Field(
        default_factory=list, description="Educational AML typologies retrieved from knowledge base"
    )
    interpretation: str = Field(
        default="", description="Analytical synthesis connecting observed facts to typologies"
    )
    findings: List[InvestigationFinding] = Field(
        default_factory=list, description="Structured list of individual findings"
    )
    referenced_transaction_ids: List[str] = Field(
        default_factory=list, description="All transaction IDs cited in this draft"
    )
    raw_response: str = Field(default="", description="The complete synthesized narrative text")


class CritiqueResult(BaseModel):
    """Evaluation result produced by the Critic checking the investigation draft."""

    passed: bool = Field(..., description="Whether the draft meets all factual and safety standards")
    issues: List[str] = Field(
        default_factory=list, description="Specific discrepancies, inaccuracies, or omissions identified"
    )
    missing_evidence: List[str] = Field(
        default_factory=list, description="Required evidence or transaction details not yet provided"
    )
    unsupported_claims: List[str] = Field(
        default_factory=list, description="Claims made without sufficient factual grounding in statement"
    )
    required_revisions: List[str] = Field(
        default_factory=list, description="Actionable instructions for the Investigator to revise the draft"
    )
    checked_transaction_ids: List[str] = Field(
        default_factory=list, description="All transaction IDs verified against customer statement"
    )
    invalid_transaction_ids: List[str] = Field(
        default_factory=list, description="Transaction IDs cited in draft that do NOT exist in statement"
    )
    safety_violations: List[str] = Field(
        default_factory=list, description="Violations of AML non-judgmental / non-accusatory safety bounds"
    )
    statement_transaction_count: int = Field(
        default=0, description="Total count of transactions in the analyzed statement"
    )
    narrative_transaction_reference_count: int = Field(
        default=0, description="Count of distinct transaction IDs cited in the narrative text"
    )
    human_review_transaction_count: int = Field(
        default=0, description="Count of prioritized human review queue items"
    )
    verified_transaction_reference_count: int = Field(
        default=0, description="Count of cited transaction references confirmed in statement"
    )
    unverified_transaction_reference_count: int = Field(
        default=0, description="Count of cited transaction references that do not exist in statement"
    )
    factual_claim_count: int = Field(
        default=0, description="Total factual claims and transaction references audited"
    )
    validation_error_count: int = Field(
        default=0, description="Total validation issues, unsupported claims, and safety flags"
    )
