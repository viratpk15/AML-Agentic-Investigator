"""Unit and integration tests for Isolation Forest anomaly detection (M7)."""

import datetime as dt
from pathlib import Path
import pytest

from aml_copilot.ml.anomaly import IsolationForestConfig, IsolationForestDetector
from aml_copilot.ml.features import extract_transaction_features
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_parser import parse_transactions

STATEMENTS_DIR = Path("data/statements")


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_anomaly_detector_small_dataset_safe_fallback():
    """Verify that fewer than min_samples_required returns safe signals and a clear warning."""
    txns = [
        Transaction(
            date=dt.date(2026, 8, i + 1),
            transaction_id=f"TXN00{i+1}",
            description=f"TXN {i+1}",
            credit=1000.0,
            balance=1000.0 * (i + 1),
        )
        for i in range(3)  # Only 3 transactions (min required is 5)
    ]
    stmt = TransactionStatement(customer_name="Small", transactions=txns)
    features = extract_transaction_features(stmt)

    detector = IsolationForestDetector(IsolationForestConfig(min_samples_required=5))
    signals, warning = detector.detect(features)

    assert warning is not None
    assert "Insufficient transaction sample size" in warning
    assert len(signals) == 3
    # All signals should be marked non-anomaly
    for s in signals:
        assert s.is_anomaly is False
        assert s.anomaly_score == 0.0
        assert s.feature_context != {}


def test_anomaly_detector_empty_features():
    """Verify empty feature set returns empty signals list and warning."""
    stmt = TransactionStatement(customer_name="Empty", transactions=[])
    features = extract_transaction_features(stmt)

    detector = IsolationForestDetector()
    signals, warning = detector.detect(features)

    assert len(signals) == 0
    assert warning is not None


def test_isolation_forest_reproducibility():
    """Verify that repeated runs with identical random_state produce identical scores and predictions."""
    pdf_path = STATEMENTS_DIR / "suspicious_statement.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)
    features = extract_transaction_features(stmt)

    detector1 = IsolationForestDetector(IsolationForestConfig(random_state=42, n_estimators=100, contamination=0.10))
    detector2 = IsolationForestDetector(IsolationForestConfig(random_state=42, n_estimators=100, contamination=0.10))

    signals1, _ = detector1.detect(features)
    signals2, _ = detector2.detect(features)

    assert len(signals1) == len(signals2)
    for s1, s2 in zip(signals1, signals2):
        assert s1.transaction_id == s2.transaction_id
        assert s1.anomaly_score == s2.anomaly_score
        assert s1.is_anomaly == s2.is_anomaly
        assert s1.feature_context == s2.feature_context


def test_isolation_forest_flags_outliers():
    """Verify that high-volume outliers are prioritized by the anomaly detector."""
    pdf_path = STATEMENTS_DIR / "mixed_statement.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)
    features = extract_transaction_features(stmt)

    detector = IsolationForestDetector(IsolationForestConfig(random_state=42, contamination=0.15))
    signals, warning = detector.detect(features)

    assert warning is None
    anomalies = [s for s in signals if s.is_anomaly]
    assert len(anomalies) > 0

    # Anomalies should have negative or near-negative decision function scores
    for a in anomalies:
        assert a.anomaly_score <= 0.05
        assert "amount" in a.feature_context
