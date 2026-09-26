"""Isolation Forest unsupervised anomaly detection over engineered transaction features."""

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from sklearn.ensemble import IsolationForest

from aml_copilot.logger import get_logger
from aml_copilot.ml.features import FeatureSet
from aml_copilot.models.findings import AnomalySignal

logger = get_logger(__name__)


class IsolationForestConfig(BaseModel):
    """Reproducible configuration for unsupervised Isolation Forest anomaly detection."""

    n_estimators: int = Field(
        default=100,
        ge=10,
        description="Number of base estimators (trees) in the Isolation Forest ensemble",
    )
    contamination: float = Field(
        default=0.10,
        gt=0.0,
        le=0.5,
        description="Expected proportion of anomalies within the dataset",
    )
    random_state: int = Field(
        default=42,
        description="Deterministic random seed ensuring reproducible tree splits",
    )
    min_samples_required: int = Field(
        default=5,
        ge=2,
        description="Minimum sample size required to fit Isolation Forest reliably",
    )


class IsolationForestDetector:
    """Unsupervised anomaly detector leveraging scikit-learn Isolation Forest."""

    def __init__(self, config: Optional[IsolationForestConfig] = None) -> None:
        self.config = config or IsolationForestConfig()

    def detect(self, feature_set: FeatureSet) -> Tuple[List[AnomalySignal], Optional[str]]:
        """Fit Isolation Forest on feature matrix and return structured anomaly signals.

        Args:
            feature_set: FeatureSet containing engineered transaction vectors.

        Returns:
            Tuple of (list of AnomalySignal instances, optional warning message if insufficient data).
        """
        n_samples = len(feature_set.vectors)

        if n_samples < self.config.min_samples_required:
            msg = (
                f"Insufficient transaction sample size ({n_samples} < "
                f"{self.config.min_samples_required}) to fit Isolation Forest. Anomaly detection skipped."
            )
            logger.warning(msg)
            # Return baseline non-anomaly signals for existing vectors
            signals = [
                AnomalySignal(
                    transaction_id=v.transaction_id,
                    anomaly_score=0.0,
                    is_anomaly=False,
                    feature_context=v.to_dict(),
                )
                for v in feature_set.vectors
            ]
            return signals, msg

        X = feature_set.to_numpy()

        # Explicitly configure reproducible IsolationForest model
        model = IsolationForest(
            n_estimators=self.config.n_estimators,
            contamination=self.config.contamination,
            random_state=self.config.random_state,
        )
        model.fit(X)

        raw_scores = model.decision_function(X)
        predictions = model.predict(X)

        signals: List[AnomalySignal] = []
        for i, vector in enumerate(feature_set.vectors):
            is_anomaly = bool(predictions[i] == -1)
            score = round(float(raw_scores[i]), 4)

            signals.append(
                AnomalySignal(
                    transaction_id=vector.transaction_id,
                    anomaly_score=score,
                    is_anomaly=is_anomaly,
                    feature_context=vector.to_dict(),
                )
            )

        anomaly_count = sum(1 for s in signals if s.is_anomaly)
        logger.info(
            f"Isolation Forest fitted on {n_samples} vectors: identified {anomaly_count} anomalies."
        )

        return signals, None
