"""Coherent end-to-end detection pipeline integrating feature engineering, rules, and anomaly detection."""

import datetime as dt
from typing import List, Optional
from aml_copilot.analysis.transaction_analytics import AnalyticsResult, analyze_transactions
from aml_copilot.logger import get_logger
from aml_copilot.ml.anomaly import IsolationForestConfig, IsolationForestDetector
from aml_copilot.ml.features import FeatureSet, extract_transaction_features
from aml_copilot.ml.rules import RuleConfig, RuleEngine
from aml_copilot.models.findings import DetectionResult
from aml_copilot.models.transaction import TransactionStatement

logger = get_logger(__name__)

STANDARD_AML_DISCLAIMER = (
    "Detection signals represent automated analytical leads and screening flags for compliance "
    "analyst review. They do not constitute a finding of guilt, money laundering, fraud, or illegal conduct."
)


class DetectionPipeline:
    """End-to-end AML detection pipeline combining deterministic rules and unsupervised anomaly scoring."""

    def __init__(
        self,
        rule_config: Optional[RuleConfig] = None,
        anomaly_config: Optional[IsolationForestConfig] = None,
    ) -> None:
        self.rule_engine = RuleEngine(config=rule_config)
        self.anomaly_detector = IsolationForestDetector(config=anomaly_config)

    def run(
        self,
        statement: TransactionStatement,
        analytics: Optional[AnalyticsResult] = None,
    ) -> DetectionResult:
        """Execute the detection pipeline on a validated transaction statement.

        Pipeline Stages:
        1. Deterministic transaction analytics (if not supplied)
        2. Feature engineering across temporal and transactional dimensions
        3. Deterministic rule evaluation producing rule signals
        4. Isolation Forest unsupervised anomaly detection
        5. Consolidation into structured DetectionResult with disclaimers and warnings

        Args:
            statement: Validated TransactionStatement.
            analytics: Optional pre-computed AnalyticsResult.

        Returns:
            DetectionResult populated with rule signals, anomaly signals, and audit metadata.
        """
        if analytics is None:
            analytics = analyze_transactions(statement)

        # Stage 1: Feature Engineering
        feature_set: FeatureSet = extract_transaction_features(statement, analytics=analytics)

        # Stage 2: Rule Engine Evaluation
        rule_signals = self.rule_engine.evaluate(statement, analytics=analytics)

        # Stage 3: Isolation Forest Anomaly Detection
        anomaly_signals, anomaly_warning = self.anomaly_detector.detect(feature_set)

        # Compile warnings and disclaimers
        warnings: List[str] = [STANDARD_AML_DISCLAIMER]
        if anomaly_warning:
            warnings.append(anomaly_warning)

        if statement.total_transactions < 10:
            warnings.append(
                f"Small transaction sample ({statement.total_transactions} transactions) "
                "limits statistical baseline confidence."
            )

        # Metadata
        metadata = {
            "pipeline_name": "AML Combined Detection Layer (M5+M6+M7)",
            "execution_timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "rule_config": self.rule_engine.config.model_dump(),
            "anomaly_config": self.anomaly_detector.config.model_dump(),
        }

        statement_meta = {
            "customer_name": statement.customer_name,
            "account_number": statement.account_number,
            "statement_period": statement.statement_period,
            "total_transactions": str(statement.total_transactions),
        }

        result = DetectionResult(
            statement_metadata=statement_meta,
            feature_summary=feature_set.summary,
            rule_signals=rule_signals,
            anomaly_signals=anomaly_signals,
            metadata=metadata,
            limitations_warnings=warnings,
        )

        logger.info(
            f"Detection completed for '{statement.customer_name}': "
            f"{result.total_rule_signals} rule signal(s), {result.total_anomaly_signals} anomaly signal(s)."
        )

        return result


def run_detection(
    statement: TransactionStatement,
    analytics: Optional[AnalyticsResult] = None,
    rule_config: Optional[RuleConfig] = None,
    anomaly_config: Optional[IsolationForestConfig] = None,
) -> DetectionResult:
    """Convenience helper to instantiate and run the detection pipeline in one call."""
    pipeline = DetectionPipeline(rule_config=rule_config, anomaly_config=anomaly_config)
    return pipeline.run(statement, analytics=analytics)
