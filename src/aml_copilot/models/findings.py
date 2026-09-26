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


class FindingGranularity(str, Enum):
    """Canonical unit of a rule finding.

    TRANSACTION_LEVEL: one finding per triggering transaction.
    EVENT_LEVEL: one finding per independent event (day, window, statement-level pattern).
    Associated transactions on an event-level finding are participants, not extra findings.
    """

    TRANSACTION_LEVEL = "TRANSACTION_LEVEL"
    EVENT_LEVEL = "EVENT_LEVEL"


# Explicit per-rule semantics. Unknown future rules default to EVENT_LEVEL so
# associated transactions are never silently counted as findings.
RULE_GRANULARITY: Dict[str, FindingGranularity] = {
    "RULE_LARGE_TRANSACTION": FindingGranularity.TRANSACTION_LEVEL,
    "RULE_SUDDEN_VOLUME_INCREASE": FindingGranularity.EVENT_LEVEL,
    "RULE_LARGE_INFLOW_RAPID_OUTFLOW": FindingGranularity.EVENT_LEVEL,
    "RULE_RAPID_MOVEMENT_OF_FUNDS": FindingGranularity.EVENT_LEVEL,
    "RULE_MANY_NEW_COUNTERPARTIES": FindingGranularity.EVENT_LEVEL,
    "RULE_HIGH_TRANSACTION_FREQUENCY": FindingGranularity.EVENT_LEVEL,
    "RULE_HIGH_STATEMENT_FREQUENCY": FindingGranularity.EVENT_LEVEL,
}


def granularity_for_rule(rule_id: str) -> FindingGranularity:
    """Return canonical finding granularity for a rule identifier."""
    return RULE_GRANULARITY.get(rule_id, FindingGranularity.EVENT_LEVEL)


class RuleSignal(BaseModel):
    """Structured signal emitted by a deterministic detection rule."""

    rule_id: str = Field(..., description="Unique programmatic identifier for the rule")
    rule_name: str = Field(..., description="Human-readable rule title")
    transaction_ids: List[str] = Field(
        default_factory=list, description="IDs of transactions associated with this finding"
    )
    granularity: FindingGranularity = Field(
        default=FindingGranularity.EVENT_LEVEL,
        description="Whether this signal is one finding per transaction or per independent event",
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
