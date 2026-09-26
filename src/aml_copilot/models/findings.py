"""Pydantic schemas for AML detection findings, signals, and results."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SignalSeverity(str, Enum):
    """Severity classification for investigation signals."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RuleSignal(BaseModel):
    """Structured signal emitted by a deterministic detection rule."""

    rule_id: str = Field(..., description="Unique programmatic identifier for the rule")
    rule_name: str = Field(..., description="Human-readable rule title")
    transaction_ids: List[str] = Field(
        default_factory=list, description="IDs of transactions that triggered this rule"
    )
    severity: SignalSeverity = Field(
        default=SignalSeverity.MEDIUM, description="Signal severity level"
    )
    explanation: str = Field(
        ..., description="Factual explanation of why the rule triggered without declaring illegality"
    )
    supporting_values: Dict[str, Any] = Field(
        default_factory=dict,
        description="Factual measurements, computed ratios, and thresholds used by the rule",
    )


class AnomalySignal(BaseModel):
    """Structured signal emitted by unsupervised anomaly detection (Isolation Forest)."""

    transaction_id: str = Field(..., description="Identifier of the transaction analyzed")
    anomaly_score: float = Field(
        ...,
        description="Isolation Forest decision score (lower/negative indicates higher abnormality)",
    )
    is_anomaly: bool = Field(
        ..., description="Whether the transaction meets the anomaly threshold"
    )
    feature_context: Dict[str, float] = Field(
        default_factory=dict,
        description="Key numerical feature values associated with this transaction",
    )


class DetectionResult(BaseModel):
    """Consolidated detection findings combining deterministic rules and unsupervised anomaly signals.

    Note:
        Detection signals represent investigative leads and flags for human AML analyst review.
        They do not establish fraud, illegal conduct, or money laundering, and do not convey guilt.
    """

    statement_metadata: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Metadata from the evaluated statement (customer, account, period)",
    )
    feature_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of engineered numerical features across transactions",
    )
    rule_signals: List[RuleSignal] = Field(
        default_factory=list, description="Deterministic rule-based investigation signals"
    )
    anomaly_signals: List[AnomalySignal] = Field(
        default_factory=list, description="Unsupervised anomaly detection signals"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metadata including parameters, model versions, and run timestamp",
    )
    limitations_warnings: List[str] = Field(
        default_factory=list,
        description="Disclaimers, data constraints, or sample size warnings",
    )

    @property
    def total_rule_signals(self) -> int:
        """Count of rule signals triggered."""
        return len(self.rule_signals)

    @property
    def total_anomaly_signals(self) -> int:
        """Count of transactions flagged as anomalies."""
        return sum(1 for s in self.anomaly_signals if s.is_anomaly)
