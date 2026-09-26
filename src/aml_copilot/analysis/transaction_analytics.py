"""Deterministic transaction analytics service using pandas and Pydantic."""

import datetime as dt
from typing import List, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from aml_copilot.logger import get_logger
from aml_copilot.models.transaction import TransactionStatement

logger = get_logger(__name__)


class DailyVolume(BaseModel):
    """Aggregated transaction volume and net flow for a single date."""

    date: dt.date = Field(..., description="Transaction calendar date")
    debit_total: float = Field(..., description="Total debit amount on this date")
    credit_total: float = Field(..., description="Total credit amount on this date")
    net_flow: float = Field(..., description="Net flow (credit - debit) on this date")
    transaction_count: int = Field(..., ge=1, description="Count of transactions on this date")


class AnalyticsResult(BaseModel):
    """Comprehensive deterministic analytics computed from a transaction statement."""

    total_transactions: int = Field(..., description="Total count of transactions")
    total_credits: float = Field(..., description="Sum of all credit amounts")
    total_debits: float = Field(..., description="Sum of all debit amounts")
    average_transaction: float = Field(..., description="Mean transaction amount")
    median_transaction: float = Field(..., description="Median transaction amount")
    maximum_transaction: float = Field(..., description="Maximum single transaction amount")
    credit_debit_ratio: Optional[float] = Field(
        default=None, description="Ratio of total credits to total debits"
    )
    unique_counterparties: List[str] = Field(
        default_factory=list, description="Unique counterparty entities identified"
    )
    transaction_frequency: float = Field(
        ..., description="Average transaction frequency (transactions per day over statement span)"
    )
    daily_volume: List[DailyVolume] = Field(
        default_factory=list, description="Daily aggregated debit/credit volumes"
    )
    transaction_time_gaps: List[int] = Field(
        default_factory=list, description="Days between consecutive transactions in chronological order"
    )
    new_counterparties: List[str] = Field(
        default_factory=list, description="Chronological sequence of first-seen counterparties"
    )


def analyze_transactions(statement: TransactionStatement) -> AnalyticsResult:
    """Compute deterministic transaction analytics from a validated TransactionStatement.

    Args:
        statement: Validated TransactionStatement containing transaction records.

    Returns:
        AnalyticsResult with statistical and temporal metrics.
    """
    transactions = statement.transactions

    if not transactions:
        logger.info("Empty statement provided to analytics; returning baseline zero metrics.")
        return AnalyticsResult(
            total_transactions=0,
            total_credits=0.0,
            total_debits=0.0,
            average_transaction=0.0,
            median_transaction=0.0,
            maximum_transaction=0.0,
            credit_debit_ratio=None,
            unique_counterparties=[],
            transaction_frequency=0.0,
            daily_volume=[],
            transaction_time_gaps=[],
            new_counterparties=[],
        )

    # Sort transactions chronologically
    sorted_txns = sorted(
        transactions,
        key=lambda t: (t.date, t.transaction_id or "")
    )

    # Prepare data for DataFrame
    records = []
    for t in sorted_txns:
        amount = t.credit if t.credit is not None else (t.debit if t.debit is not None else 0.0)
        records.append({
            "date": t.date,
            "transaction_id": t.transaction_id,
            "description": t.description,
            "debit": t.debit if t.debit is not None else 0.0,
            "credit": t.credit if t.credit is not None else 0.0,
            "amount": amount,
            "balance": t.balance,
            "counterparty": t.counterparty,
        })

    df = pd.DataFrame(records)

    # Volume totals
    total_txns = len(sorted_txns)
    total_credits = round(float(df["credit"].sum()), 2)
    total_debits = round(float(df["debit"].sum()), 2)

    credit_debit_ratio: Optional[float] = None
    if total_debits > 0:
        credit_debit_ratio = round(total_credits / total_debits, 4)

    # Statistical metrics on individual transaction amounts
    amounts = df["amount"].values
    avg_txn = round(float(np.mean(amounts)), 2)
    med_txn = round(float(np.median(amounts)), 2)
    max_txn = round(float(np.max(amounts)), 2)

    # Counterparty tracking
    seen_counterparties = set()
    new_counterparties: List[str] = []
    for t in sorted_txns:
        if t.counterparty and t.counterparty not in seen_counterparties:
            seen_counterparties.add(t.counterparty)
            new_counterparties.append(t.counterparty)

    unique_counterparties = sorted(list(seen_counterparties))

    # Daily aggregation
    daily_groups = df.groupby("date", as_index=False).agg(
        debit_total=("debit", "sum"),
        credit_total=("credit", "sum"),
        transaction_count=("amount", "count"),
    )
    daily_groups["net_flow"] = daily_groups["credit_total"] - daily_groups["debit_total"]
    daily_groups = daily_groups.sort_values("date")

    daily_volumes: List[DailyVolume] = [
        DailyVolume(
            date=row["date"],
            debit_total=round(float(row["debit_total"]), 2),
            credit_total=round(float(row["credit_total"]), 2),
            net_flow=round(float(row["net_flow"]), 2),
            transaction_count=int(row["transaction_count"]),
        )
        for _, row in daily_groups.iterrows()
    ]

    # Time gaps between consecutive transactions
    time_gaps: List[int] = []
    for i in range(1, len(sorted_txns)):
        gap = (sorted_txns[i].date - sorted_txns[i - 1].date).days
        time_gaps.append(gap)

    # Transaction frequency (transactions per day across statement period)
    first_date = sorted_txns[0].date
    last_date = sorted_txns[-1].date
    span_days = max(1, (last_date - first_date).days + 1)
    txn_frequency = round(total_txns / span_days, 4)

    logger.info(
        f"Calculated analytics: {total_txns} txns, credits={total_credits}, debits={total_debits}, span={span_days} days"
    )

    return AnalyticsResult(
        total_transactions=total_txns,
        total_credits=total_credits,
        total_debits=total_debits,
        average_transaction=avg_txn,
        median_transaction=med_txn,
        maximum_transaction=max_txn,
        credit_debit_ratio=credit_debit_ratio,
        unique_counterparties=unique_counterparties,
        transaction_frequency=txn_frequency,
        daily_volume=daily_volumes,
        transaction_time_gaps=time_gaps,
        new_counterparties=new_counterparties,
    )
