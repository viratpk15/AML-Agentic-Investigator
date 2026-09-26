"""Detection tools wrapping the M5-M7 AML detection pipeline for investigation agents."""

from typing import Any, Dict, List, Literal, Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from aml_copilot.logger import get_logger
from aml_copilot.ml.pipeline import run_detection
from aml_copilot.models.findings import DetectionResult, SignalSeverity
from aml_copilot.models.transaction import TransactionStatement

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Schemas for Detection Tool Contracts
# ---------------------------------------------------------------------------

class RuleSignalRecord(BaseModel):
    """Structured rule detection signal preserving full factual evidence."""

    rule_id: str
    rule_name: str
    severity: str
    transaction_ids: List[str]
    explanation: str
    supporting_values: Dict[str, Any]


class AnomalySignalRecord(BaseModel):
    """Structured Isolation Forest anomaly signal preserving score and feature context."""

    transaction_id: str
    anomaly_score: float
    is_anomaly: bool
    feature_context: Dict[str, float]


class DetectAnomaliesInput(BaseModel):
    """Input parameters for running AML anomaly and rule detection."""

    min_severity: Optional[Literal["INFO", "LOW", "MEDIUM", "HIGH"]] = Field(
        default=None,
        description="Filter rule signals to those at or above this severity level (INFO < LOW < MEDIUM < HIGH)",
    )
    include_rule_signals: bool = Field(
        default=True,
        description="Whether to include deterministic rule-based screening signals",
    )
    include_anomaly_signals: bool = Field(
        default=True,
        description="Whether to include unsupervised Isolation Forest anomaly signals",
    )


class DetectAnomaliesOutput(BaseModel):
    """Consolidated detection findings for the investigating agent."""

    customer_name: Optional[str] = None
    statement_period: Optional[str] = None
    total_rule_signals: int
    total_anomaly_signals: int
    flagged_transaction_ids: List[str] = Field(
        default_factory=list,
        description="Unique deduplicated transaction IDs flagged by either rules or Isolation Forest",
    )
    rule_signals: List[RuleSignalRecord] = Field(default_factory=list)
    anomaly_signals: List[AnomalySignalRecord] = Field(default_factory=list)
    limitations_warnings: List[str] = Field(default_factory=list)


SEVERITY_ORDER = {
    "INFO": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
}


# ---------------------------------------------------------------------------
# Direct Deterministic Execution
# ---------------------------------------------------------------------------

def execute_detect_anomalies(
    statement: TransactionStatement,
    params: Optional[DetectAnomaliesInput] = None,
) -> DetectAnomaliesOutput:
    """Run the complete M5-M7 detection pipeline on the statement and return structured findings.

    Args:
        statement: Validated TransactionStatement.
        params: Optional filtering parameters.

    Returns:
        DetectAnomaliesOutput containing rule signals, anomaly signals, and flagged transaction IDs.
    """
    if params is None:
        params = DetectAnomaliesInput()

    # Call the established M5-M7 combined detection pipeline
    result: DetectionResult = run_detection(statement)

    flagged_ids = set()
    rule_records: List[RuleSignalRecord] = []

    if params.include_rule_signals:
        min_rank = SEVERITY_ORDER.get(params.min_severity, 0) if params.min_severity else 0

        for r in result.rule_signals:
            rank = SEVERITY_ORDER.get(r.severity.value, 0)
            if rank >= min_rank:
                rule_records.append(
                    RuleSignalRecord(
                        rule_id=r.rule_id,
                        rule_name=r.rule_name,
                        severity=r.severity.value,
                        transaction_ids=r.transaction_ids,
                        explanation=r.explanation,
                        supporting_values=r.supporting_values,
                    )
                )
                flagged_ids.update(r.transaction_ids)

    anomaly_records: List[AnomalySignalRecord] = []
    if params.include_anomaly_signals:
        for a in result.anomaly_signals:
            if a.is_anomaly:
                flagged_ids.add(a.transaction_id)
            anomaly_records.append(
                AnomalySignalRecord(
                    transaction_id=a.transaction_id,
                    anomaly_score=a.anomaly_score,
                    is_anomaly=a.is_anomaly,
                    feature_context=a.feature_context if a.is_anomaly else {},
                )
            )

    sorted_flagged_ids = sorted(list(flagged_ids))

    return DetectAnomaliesOutput(
        customer_name=statement.customer_name,
        statement_period=statement.statement_period,
        total_rule_signals=len(rule_records),
        total_anomaly_signals=sum(1 for a in anomaly_records if a.is_anomaly),
        flagged_transaction_ids=sorted_flagged_ids,
        rule_signals=rule_records,
        anomaly_signals=anomaly_records,
        limitations_warnings=result.limitations_warnings,
    )


# ---------------------------------------------------------------------------
# LangChain Tool Factory
# ---------------------------------------------------------------------------

def create_detect_anomalies_tool(statement: TransactionStatement) -> StructuredTool:
    """Create a LangChain tool for running AML anomaly and rule detection on the active statement."""

    def _tool_fn(
        min_severity: Optional[Literal["INFO", "LOW", "MEDIUM", "HIGH"]] = None,
        include_rule_signals: bool = True,
        include_anomaly_signals: bool = True,
    ) -> Dict[str, Any]:
        params = DetectAnomaliesInput(
            min_severity=min_severity,
            include_rule_signals=include_rule_signals,
            include_anomaly_signals=include_anomaly_signals,
        )
        result = execute_detect_anomalies(statement, params)
        return result.model_dump()

    return StructuredTool.from_function(
        func=_tool_fn,
        name="detect_anomalies",
        description=(
            "Use this tool to execute the deterministic AML rule engine and unsupervised Isolation Forest "
            "anomaly detection pipeline over the customer's transactions. Returns structured investigation signals, "
            "including rule triggers (e.g. unusually large transactions, sudden volume surges, rapid pass-through / "
            "layering patterns, rapid funds movement, high counterparty counts), Isolation Forest outlier scores, "
            "and all associated transaction IDs with factual supporting values. Detection results produce investigative "
            "leads only and do not establish legal guilt or crime."
        ),
        args_schema=DetectAnomaliesInput,
    )
