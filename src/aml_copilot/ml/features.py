"""Deterministic feature engineering for bank transactions."""

import datetime as dt
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from aml_copilot.analysis.transaction_analytics import AnalyticsResult, analyze_transactions
from aml_copilot.logger import get_logger
from aml_copilot.models.transaction import TransactionStatement

logger = get_logger(__name__)

NUMERICAL_FEATURE_NAMES = [
    "amount",
    "is_credit",
    "days_since_previous",
    "rolling_frequency_7d",
    "rolling_volume_7d",
    "counterparty_frequency",
    "is_new_counterparty",
    "amount_to_mean_ratio",
    "amount_to_median_ratio",
    "running_balance",
    "balance_change",
    "running_net_flow",
]


class TransactionFeatureVector(BaseModel):
    """Deterministic numerical feature vector computed for an individual transaction."""

    transaction_id: str = Field(..., description="Transaction identifier")
    date: dt.date = Field(..., description="Calendar date of transaction")
    amount: float = Field(..., ge=0.0, description="Absolute transaction value")
    is_credit: float = Field(..., description="1.0 for incoming credit, 0.0 for outgoing debit")
    days_since_previous: float = Field(
        ..., ge=0.0, description="Calendar days elapsed since previous consecutive transaction"
    )
    rolling_frequency_7d: float = Field(
        ..., ge=1.0, description="Number of transactions occurring in trailing 7-day window"
    )
    rolling_volume_7d: float = Field(
        ..., ge=0.0, description="Total transaction monetary volume in trailing 7-day window"
    )
    counterparty_frequency: float = Field(
        ..., ge=0.0, description="Historical occurrence count of this counterparty up to this transaction"
    )
    is_new_counterparty: float = Field(
        ..., description="1.0 if counterparty is observed for the first time, 0.0 otherwise"
    )
    amount_to_mean_ratio: float = Field(
        ..., ge=0.0, description="Transaction amount normalized by statement mean transaction amount"
    )
    amount_to_median_ratio: float = Field(
        ..., ge=0.0, description="Transaction amount normalized by statement median transaction amount"
    )
    running_balance: float = Field(..., description="Account balance after transaction execution")
    balance_change: float = Field(
        ..., description="Net balance difference compared to the immediately preceding transaction"
    )
    running_net_flow: float = Field(
        ..., description="Cumulative net funds flow (total credits minus total debits) up to this transaction"
    )

    def to_dict(self) -> Dict[str, float]:
        """Return the dictionary of engineered numerical features."""
        return {
            "amount": self.amount,
            "is_credit": self.is_credit,
            "days_since_previous": self.days_since_previous,
            "rolling_frequency_7d": self.rolling_frequency_7d,
            "rolling_volume_7d": self.rolling_volume_7d,
            "counterparty_frequency": self.counterparty_frequency,
            "is_new_counterparty": self.is_new_counterparty,
            "amount_to_mean_ratio": self.amount_to_mean_ratio,
            "amount_to_median_ratio": self.amount_to_median_ratio,
            "running_balance": self.running_balance,
            "balance_change": self.balance_change,
            "running_net_flow": self.running_net_flow,
        }

    def to_array(self) -> List[float]:
        """Return numerical features ordered identically to NUMERICAL_FEATURE_NAMES."""
        return [
            self.amount,
            self.is_credit,
            self.days_since_previous,
            self.rolling_frequency_7d,
            self.rolling_volume_7d,
            self.counterparty_frequency,
            self.is_new_counterparty,
            self.amount_to_mean_ratio,
            self.amount_to_median_ratio,
            self.running_balance,
            self.balance_change,
            self.running_net_flow,
        ]


class FeatureSet(BaseModel):
    """Structured collection of engineered features across a transaction statement."""

    customer_name: Optional[str] = Field(default=None, description="Account holder name")
    account_number: Optional[str] = Field(default=None, description="Account identifier")
    statement_period: Optional[str] = Field(default=None, description="Statement period range string")
    feature_names: List[str] = Field(
        default_factory=lambda: list(NUMERICAL_FEATURE_NAMES),
        description="Names of numerical features extracted",
    )
    vectors: List[TransactionFeatureVector] = Field(
        default_factory=list, description="Per-transaction engineered feature vectors"
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict, description="Summary statistics across all feature vectors"
    )

    @property
    def total_transactions(self) -> int:
        """Count of feature vectors."""
        return len(self.vectors)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert feature vectors to a pandas DataFrame."""
        if not self.vectors:
            cols = ["transaction_id", "date"] + self.feature_names
            return pd.DataFrame(columns=cols)

        records = []
        for v in self.vectors:
            rec = {"transaction_id": v.transaction_id, "date": v.date}
            rec.update(v.to_dict())
            records.append(rec)
        return pd.DataFrame(records)

    def to_numpy(self) -> np.ndarray:
        """Convert feature vectors to a 2D numpy array of shape (N, num_features)."""
        if not self.vectors:
            return np.empty((0, len(self.feature_names)), dtype=float)
        return np.array([v.to_array() for v in self.vectors], dtype=float)


def extract_transaction_features(
    statement: TransactionStatement,
    analytics: Optional[AnalyticsResult] = None,
) -> FeatureSet:
    """Extract deterministic numerical features for all transactions in a statement.

    Args:
        statement: Validated TransactionStatement.
        analytics: Optional pre-computed AnalyticsResult. If None, will be computed.

    Returns:
        FeatureSet containing typed TransactionFeatureVector instances and summary metrics.
    """
    if not statement.transactions:
        logger.info("Empty statement provided to feature extractor.")
        return FeatureSet(
            customer_name=statement.customer_name,
            account_number=statement.account_number,
            statement_period=statement.statement_period,
            feature_names=list(NUMERICAL_FEATURE_NAMES),
            vectors=[],
            summary={
                "total_transactions": 0,
                "feature_count": len(NUMERICAL_FEATURE_NAMES),
            },
        )

    if analytics is None:
        analytics = analyze_transactions(statement)

    # Sort transactions chronologically
    sorted_txns = sorted(
        statement.transactions,
        key=lambda t: (t.date, t.transaction_id or "")
    )

    vectors: List[TransactionFeatureVector] = []
    seen_counterparties_count: Dict[str, int] = {}
    cum_credits = 0.0
    cum_debits = 0.0

    mean_amount = analytics.average_transaction
    median_amount = analytics.median_transaction

    for idx, txn in enumerate(sorted_txns):
        txn_id = txn.transaction_id or f"TXN_{idx + 1:03d}"
        amount = txn.credit if txn.credit is not None else (txn.debit if txn.debit is not None else 0.0)
        is_credit = 1.0 if (txn.credit is not None and txn.credit > 0) else 0.0

        if is_credit == 1.0:
            cum_credits += amount
        else:
            cum_debits += amount

        # Days since previous transaction
        if idx == 0:
            days_since_prev = 0.0
            balance_change = amount if is_credit == 1.0 else -amount
        else:
            prev_txn = sorted_txns[idx - 1]
            days_since_prev = float((txn.date - prev_txn.date).days)
            balance_change = round(txn.balance - prev_txn.balance, 2)

        # 7-day rolling window context (inclusive of current date)
        window_start = txn.date - dt.timedelta(days=7)
        window_txns = [
            t for t in sorted_txns[: idx + 1]
            if window_start <= t.date <= txn.date
        ]
        rolling_freq_7d = float(len(window_txns))
        rolling_vol_7d = float(
            sum(t.credit if t.credit is not None else (t.debit if t.debit is not None else 0.0) for t in window_txns)
        )

        # Counterparty dynamics
        cp = txn.counterparty
        if cp:
            prev_count = seen_counterparties_count.get(cp, 0)
            is_new_cp = 1.0 if prev_count == 0 else 0.0
            seen_counterparties_count[cp] = prev_count + 1
            cp_freq = float(seen_counterparties_count[cp])
        else:
            is_new_cp = 0.0
            cp_freq = 0.0

        # Relative amounts compared to statement baseline
        amt_to_mean = round(amount / mean_amount, 4) if mean_amount > 0 else 1.0
        amt_to_med = round(amount / median_amount, 4) if median_amount > 0 else 1.0

        running_net = round(cum_credits - cum_debits, 2)

        vector = TransactionFeatureVector(
            transaction_id=txn_id,
            date=txn.date,
            amount=round(amount, 2),
            is_credit=is_credit,
            days_since_previous=days_since_prev,
            rolling_frequency_7d=rolling_freq_7d,
            rolling_volume_7d=round(rolling_vol_7d, 2),
            counterparty_frequency=cp_freq,
            is_new_counterparty=is_new_cp,
            amount_to_mean_ratio=amt_to_mean,
            amount_to_median_ratio=amt_to_med,
            running_balance=round(txn.balance, 2),
            balance_change=balance_change,
            running_net_flow=running_net,
        )
        vectors.append(vector)

    # Compute summary statistics across feature set
    amounts = [v.amount for v in vectors]
    summary = {
        "total_transactions": len(vectors),
        "feature_count": len(NUMERICAL_FEATURE_NAMES),
        "mean_amount": round(float(np.mean(amounts)), 2),
        "median_amount": round(float(np.median(amounts)), 2),
        "max_amount": round(float(np.max(amounts)), 2),
        "max_rolling_volume_7d": round(max((v.rolling_volume_7d for v in vectors), default=0.0), 2),
        "new_counterparties_count": sum(int(v.is_new_counterparty) for v in vectors),
    }

    logger.info(
        f"Extracted {len(vectors)} feature vectors across {len(NUMERICAL_FEATURE_NAMES)} features."
    )

    return FeatureSet(
        customer_name=statement.customer_name,
        account_number=statement.account_number,
        statement_period=statement.statement_period,
        feature_names=list(NUMERICAL_FEATURE_NAMES),
        vectors=vectors,
        summary=summary,
    )
