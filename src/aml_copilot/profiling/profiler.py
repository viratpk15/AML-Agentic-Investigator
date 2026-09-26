"""Deterministic customer profiler calculating behavioral metrics and indicators."""

import datetime as dt
from typing import Any, Dict, List, Optional
import numpy as np

from aml_copilot.analysis.transaction_analytics import analyze_transactions
from aml_copilot.logger import get_logger
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.profiling.customer_profile import (
    BehavioralIndicator,
    CustomerProfile,
    LargestTransactionRecord,
)

logger = get_logger(__name__)


def build_customer_profile(statement: TransactionStatement) -> CustomerProfile:
    """Generate a deterministic, factual behavioral profile for a customer statement.

    Args:
        statement: Validated TransactionStatement under review.

    Returns:
        Structured CustomerProfile populated with verified behavioral metrics and indicators.
    """
    txns = statement.transactions
    if not txns:
        return CustomerProfile(
            customer_name=statement.customer_name,
            account_number=statement.account_number,
            statement_period=statement.statement_period,
            total_transactions=0,
            total_credits=0.0,
            total_debits=0.0,
            net_cash_flow=0.0,
            average_transaction_amount=0.0,
            median_transaction_amount=0.0,
            maximum_transaction_amount=0.0,
            credit_transaction_count=0,
            debit_transaction_count=0,
            dominant_transaction_type="balanced",
            credit_to_debit_ratio=None,
            unique_counterparty_count=0,
            new_counterparty_count=0,
            unique_counterparties=[],
            active_days=0,
            transaction_frequency=0.0,
            average_daily_volume=0.0,
            maximum_daily_volume=0.0,
            largest_credit=None,
            largest_debit=None,
            indicators=[],
        )

    # 1. Base analytics
    analytics = analyze_transactions(statement)

    # 2. Credits vs Debits breakdown
    credit_txns = [t for t in txns if t.credit is not None and t.credit > 0]
    debit_txns = [t for t in txns if t.debit is not None and t.debit > 0]

    credit_count = len(credit_txns)
    debit_count = len(debit_txns)

    if credit_count > debit_count * 1.5:
        dominant_type = "credit"
    elif debit_count > credit_count * 1.5:
        dominant_type = "debit"
    else:
        dominant_type = "balanced"

    net_cash_flow = round(analytics.total_credits - analytics.total_debits, 2)

    # 3. Peak individual transactions
    largest_credit_rec: Optional[LargestTransactionRecord] = None
    if credit_txns:
        peak_credit = max(credit_txns, key=lambda t: t.credit or 0.0)
        largest_credit_rec = LargestTransactionRecord(
            transaction_id=peak_credit.transaction_id,
            amount=peak_credit.credit or 0.0,
            date=peak_credit.date,
            description=peak_credit.description,
            counterparty=peak_credit.counterparty,
        )

    largest_debit_rec: Optional[LargestTransactionRecord] = None
    if debit_txns:
        peak_debit = max(debit_txns, key=lambda t: t.debit or 0.0)
        largest_debit_rec = LargestTransactionRecord(
            transaction_id=peak_debit.transaction_id,
            amount=peak_debit.debit or 0.0,
            date=peak_debit.date,
            description=peak_debit.description,
            counterparty=peak_debit.counterparty,
        )

    # 4. Daily turnover metrics
    active_days_count = len(analytics.daily_volume)
    daily_turnovers = [
        round(dv.credit_total + dv.debit_total, 2)
        for dv in analytics.daily_volume
    ]
    avg_daily_volume = round(float(np.mean(daily_turnovers)), 2) if daily_turnovers else 0.0
    max_daily_volume = round(float(np.max(daily_turnovers)), 2) if daily_turnovers else 0.0

    # 5. Deterministic behavioral indicators
    indicators: List[BehavioralIndicator] = []

    # Indicator 1: High-value activity
    high_value_txns = [
        t.transaction_id
        for t in txns
        if (t.credit or 0.0) >= 200000.0 or (t.debit or 0.0) >= 200000.0
    ]
    if high_value_txns:
        indicators.append(
            BehavioralIndicator(
                name="high_value_activity",
                description="High-value transaction activity observed exceeding typical baseline parameters.",
                supporting_transaction_ids=high_value_txns,
                details={
                    "threshold": 200000.0,
                    "qualifying_transactions_count": len(high_value_txns),
                    "maximum_single_transaction": analytics.maximum_transaction,
                },
            )
        )

    # Indicator 2: High aggregate turnover volume
    total_turnover = analytics.total_credits + analytics.total_debits
    if total_turnover >= 500000.0:
        turnover_txns = [
            t.transaction_id
            for t in sorted(txns, key=lambda x: (x.credit or 0.0) + (x.debit or 0.0), reverse=True)[:5]
        ]
        indicators.append(
            BehavioralIndicator(
                name="high_transaction_volume",
                description="Elevated aggregate transaction volume observed across statement duration.",
                supporting_transaction_ids=turnover_txns,
                details={
                    "total_turnover": round(total_turnover, 2),
                    "total_credits": analytics.total_credits,
                    "total_debits": analytics.total_debits,
                },
            )
        )

    # Indicator 3: Many counterparties
    if len(analytics.unique_counterparties) >= 5:
        # Supporting transactions: representative transaction for each unique counterparty ranked by volume
        unique_cp_map = {}
        for t in sorted(txns, key=lambda x: (x.credit or 0.0) + (x.debit or 0.0), reverse=True):
            if t.counterparty and t.counterparty not in unique_cp_map and t.transaction_id:
                unique_cp_map[t.counterparty] = t.transaction_id
        cp_txns = list(unique_cp_map.values())
        indicators.append(
            BehavioralIndicator(
                name="many_counterparties",
                description="Multiple distinct counterparties observed across transactional flow.",
                supporting_transaction_ids=cp_txns,
                details={
                    "unique_counterparties_count": len(analytics.unique_counterparties),
                    "sample_counterparties": analytics.unique_counterparties[:5],
                },
            )
        )

    # Indicator 4: Frequent new counterparties
    if len(analytics.new_counterparties) >= 4:
        first_seen_txns: List[str] = []
        seen = set()
        for t in txns:
            if t.counterparty and t.counterparty not in seen:
                seen.add(t.counterparty)
                first_seen_txns.append(t.transaction_id)

        indicators.append(
            BehavioralIndicator(
                name="frequent_new_counterparties",
                description="Frequent introduction of newly observed counterparties.",
                supporting_transaction_ids=first_seen_txns,
                details={
                    "new_counterparties_count": len(analytics.new_counterparties),
                    "ratio_to_total_transactions": round(len(analytics.new_counterparties) / len(txns), 2),
                },
            )
        )

    # Indicator 5: Rapid fund movement pattern
    # Detect if incoming credit is swiftly followed within 48 hours by debit of >= 70% amount
    rapid_pairs: List[str] = []
    sorted_txns = sorted(txns, key=lambda t: t.date)
    for i, c_txn in enumerate(sorted_txns):
        if c_txn.credit and c_txn.credit >= 100000.0:
            for d_txn in sorted_txns[i + 1 :]:
                gap_days = (d_txn.date - c_txn.date).days
                if gap_days > 2:
                    break
                if d_txn.debit and d_txn.debit >= 0.7 * c_txn.credit:
                    if c_txn.transaction_id not in rapid_pairs:
                        rapid_pairs.append(c_txn.transaction_id)
                    if d_txn.transaction_id not in rapid_pairs:
                        rapid_pairs.append(d_txn.transaction_id)

    if rapid_pairs:
        indicators.append(
            BehavioralIndicator(
                name="rapid_fund_movement",
                description="Rapid movement of funds observed where incoming credits are followed shortly by outgoing transfers.",
                supporting_transaction_ids=rapid_pairs,
                details={"qualifying_transaction_ids": rapid_pairs},
            )
        )

    return CustomerProfile(
        customer_name=statement.customer_name,
        account_number=statement.account_number,
        statement_period=statement.statement_period,
        total_transactions=analytics.total_transactions,
        total_credits=analytics.total_credits,
        total_debits=analytics.total_debits,
        net_cash_flow=net_cash_flow,
        average_transaction_amount=analytics.average_transaction,
        median_transaction_amount=analytics.median_transaction,
        maximum_transaction_amount=analytics.maximum_transaction,
        credit_transaction_count=credit_count,
        debit_transaction_count=debit_count,
        dominant_transaction_type=dominant_type,
        credit_to_debit_ratio=analytics.credit_debit_ratio,
        unique_counterparty_count=len(analytics.unique_counterparties),
        new_counterparty_count=len(analytics.new_counterparties),
        unique_counterparties=analytics.unique_counterparties,
        active_days=active_days_count,
        transaction_frequency=analytics.transaction_frequency,
        average_daily_volume=avg_daily_volume,
        maximum_daily_volume=max_daily_volume,
        largest_credit=largest_credit_rec,
        largest_debit=largest_debit_rec,
        indicators=indicators,
    )
