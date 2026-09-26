"""Unit and integration tests for deterministic feature engineering (M5)."""

import datetime as dt
from pathlib import Path
import numpy as np
import pytest

from aml_copilot.ml.features import (
    NUMERICAL_FEATURE_NAMES,
    FeatureSet,
    TransactionFeatureVector,
    extract_transaction_features,
)
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_parser import parse_transactions

STATEMENTS_DIR = Path("data/statements")


# ---------------------------------------------------------------------------
# Unit tests with synthetic fixture data
# ---------------------------------------------------------------------------

def test_feature_extraction_empty_statement():
    """Verify empty statement produces empty FeatureSet gracefully."""
    stmt = TransactionStatement(account_number="ACC000", customer_name="Empty Customer", transactions=[])
    features = extract_transaction_features(stmt)

    assert isinstance(features, FeatureSet)
    assert features.total_transactions == 0
    assert len(features.vectors) == 0
    assert features.feature_names == list(NUMERICAL_FEATURE_NAMES)
    assert features.summary["total_transactions"] == 0

    # Test conversion methods on empty
    df = features.to_dataframe()
    assert len(df) == 0
    arr = features.to_numpy()
    assert arr.shape == (0, len(NUMERICAL_FEATURE_NAMES))


def test_feature_extraction_single_transaction():
    """Verify feature calculation for a statement with a single transaction."""
    t = Transaction(
        date=dt.date(2026, 8, 1),
        transaction_id="TXN001",
        description="INITIAL SALARY",
        credit=50000.0,
        debit=None,
        balance=50000.0,
        counterparty="EMPLOYER CORP",
    )
    stmt = TransactionStatement(customer_name="Alice", transactions=[t])
    features = extract_transaction_features(stmt)

    assert features.total_transactions == 1
    v = features.vectors[0]
    assert v.transaction_id == "TXN001"
    assert v.amount == 50000.0
    assert v.is_credit == 1.0
    assert v.days_since_previous == 0.0
    assert v.rolling_frequency_7d == 1.0
    assert v.rolling_volume_7d == 50000.0
    assert v.counterparty_frequency == 1.0
    assert v.is_new_counterparty == 1.0
    assert v.amount_to_mean_ratio == 1.0
    assert v.amount_to_median_ratio == 1.0
    assert v.running_balance == 50000.0
    assert v.balance_change == 50000.0
    assert v.running_net_flow == 50000.0


def test_feature_vector_array_and_dict():
    """Verify to_array and to_dict preserve expected feature dimensions."""
    vec = TransactionFeatureVector(
        transaction_id="TXN1",
        date=dt.date(2026, 8, 1),
        amount=1000.0,
        is_credit=0.0,
        days_since_previous=2.0,
        rolling_frequency_7d=3.0,
        rolling_volume_7d=5000.0,
        counterparty_frequency=2.0,
        is_new_counterparty=0.0,
        amount_to_mean_ratio=0.5,
        amount_to_median_ratio=0.6,
        running_balance=10000.0,
        balance_change=-1000.0,
        running_net_flow=-1000.0,
    )
    arr = vec.to_array()
    d = vec.to_dict()

    assert len(arr) == len(NUMERICAL_FEATURE_NAMES)
    assert len(d) == len(NUMERICAL_FEATURE_NAMES)
    assert d["amount"] == 1000.0
    assert d["is_credit"] == 0.0


# ---------------------------------------------------------------------------
# Integration tests across all three PDF statements
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "pdf_filename, expected_txns",
    [
        ("normal_statement.pdf", 14),
        ("suspicious_statement.pdf", 15),
        ("mixed_statement.pdf", 14),
    ],
)
def test_feature_extraction_all_pdfs(pdf_filename: str, expected_txns: int):
    """Verify feature generation succeeds on all 3 synthetic PDFs with valid invariants."""
    pdf_path = STATEMENTS_DIR / pdf_filename
    if not pdf_path.exists():
        pytest.skip(f"PDF {pdf_filename} not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)
    features = extract_transaction_features(stmt)

    assert features.total_transactions == expected_txns
    assert len(features.vectors) == expected_txns

    # Verify numerical matrix properties
    df = features.to_dataframe()
    assert len(df) == expected_txns
    assert "amount" in df.columns
    assert "rolling_volume_7d" in df.columns

    arr = features.to_numpy()
    assert arr.shape == (expected_txns, len(NUMERICAL_FEATURE_NAMES))
    assert not np.isnan(arr).any(), "Feature matrix contains NaN values"
    assert not np.isinf(arr).any(), "Feature matrix contains Inf values"

    # Verify invariant ranges
    for v in features.vectors:
        assert v.amount >= 0.0
        assert v.is_credit in (0.0, 1.0)
        assert v.days_since_previous >= 0.0
        assert v.rolling_frequency_7d >= 1.0
        assert v.rolling_volume_7d >= v.amount
        assert v.is_new_counterparty in (0.0, 1.0)
