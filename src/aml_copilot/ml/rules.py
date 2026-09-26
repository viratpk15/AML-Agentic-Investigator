"""Deterministic AML rule engine producing structured investigation signals."""

import datetime as dt
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from aml_copilot.analysis.transaction_analytics import AnalyticsResult, analyze_transactions
from aml_copilot.logger import get_logger
from aml_copilot.models.findings import RuleSignal, SignalSeverity
from aml_copilot.models.transaction import TransactionStatement

logger = get_logger(__name__)


class RuleConfig(BaseModel):
    """Configurable thresholds for deterministic AML screening rules."""

    # Unusually large transaction rule
    large_transaction_abs_threshold: float = Field(
        default=100_000.0,
        description="Absolute amount threshold above which a transaction is flagged as large",
    )
    large_transaction_multiplier: float = Field(
        default=4.0,
        description="Multiplier over customer median transaction amount to flag as unusually large",
    )
    large_transaction_min_relative_amount: float = Field(
        default=100_000.0,
        description="Minimum absolute amount required when using the median multiplier threshold",
    )

    # Sudden volume increase rule
    volume_increase_spike_multiplier: float = Field(
        default=3.0,
        description="Daily volume multiplier relative to statement daily average to flag a spike",
    )
    volume_increase_min_amount: float = Field(
        default=100_000.0,
        description="Minimum daily total volume required to flag volume increase",
    )

    # Large incoming followed by rapid outgoing (pass-through / layering)
    pass_through_min_credit: float = Field(
        default=100_000.0,
        description="Minimum incoming credit amount to evaluate for rapid outgoing pass-through",
    )
    pass_through_lookforward_days: int = Field(
        default=2,
        description="Calendar days window after credit to monitor for rapid draining debits",
    )
    pass_through_turnover_ratio: float = Field(
        default=0.80,
        description="Fraction of incoming credit drained by subsequent debits (80% default)",
    )

    # Rapid movement of funds (aggregate velocity across rolling window)
    rapid_flow_window_days: int = Field(
        default=3,
        description="Rolling window in days for assessing rapid velocity and fund movement",
    )
    rapid_flow_min_volume: float = Field(
        default=150_000.0,
        description="Minimum total credit volume in rolling window to assess rapid movement",
    )
    rapid_flow_turnover_ratio: float = Field(
        default=0.80,
        description="Minimum debit-to-credit turnover ratio within rolling window to flag rapid flow",
    )

    # Many new counterparties rule
    many_new_counterparties_threshold: int = Field(
        default=5,
        description="Count of previously unseen counterparties in statement to trigger signal",
    )

    # High transaction frequency rule
    high_frequency_daily_count: int = Field(
        default=4,
        description="Number of transactions on a single day to trigger high frequency signal",
    )
    high_frequency_statement_rate: float = Field(
        default=2.0,
        description="Overall statement daily transaction rate (txns/day) to trigger frequency signal",
    )


class RuleEngine:
    """Deterministic AML rule evaluator for transaction statements."""

    def __init__(self, config: Optional[RuleConfig] = None) -> None:
        self.config = config or RuleConfig()

    def evaluate(
        self,
        statement: TransactionStatement,
        analytics: Optional[AnalyticsResult] = None,
    ) -> List[RuleSignal]:
        """Evaluate deterministic rules against a statement and return structured signals.

        Args:
            statement: Validated TransactionStatement.
            analytics: Optional pre-computed AnalyticsResult.

        Returns:
            List of RuleSignal objects. Signals represent investigative leads, not legal findings.
        """
        if not statement.transactions:
            return []

        if analytics is None:
            analytics = analyze_transactions(statement)

        sorted_txns = sorted(
            statement.transactions,
            key=lambda t: (t.date, t.transaction_id or "")
        )

        signals: List[RuleSignal] = []

        # 1. Unusually large transaction
        signals.extend(self._check_large_transactions(sorted_txns, analytics))

        # 2. Sudden transaction-volume increase
        signals.extend(self._check_sudden_volume_increase(sorted_txns, analytics))

        # 3. Large incoming transaction followed by rapid outgoing transaction
        signals.extend(self._check_large_inflow_rapid_outflow(sorted_txns))

        # 4. Rapid movement of funds (aggregate velocity)
        signals.extend(self._check_rapid_funds_movement(sorted_txns))

        # 5. Many new counterparties
        signals.extend(self._check_many_new_counterparties(sorted_txns))

        # 6. Unusually high transaction frequency
        signals.extend(self._check_high_transaction_frequency(sorted_txns, analytics))

        logger.info(f"RuleEngine evaluated {len(sorted_txns)} transactions; produced {len(signals)} signals.")
        return signals

    def _check_large_transactions(
        self, sorted_txns: List, analytics: AnalyticsResult
    ) -> List[RuleSignal]:
        """Flag individual transactions that exceed absolute or relative size thresholds."""
        signals = []
        median = analytics.median_transaction

        for t in sorted_txns:
            amount = t.credit if t.credit is not None else (t.debit if t.debit is not None else 0.0)
            txn_id = t.transaction_id or "UNKNOWN_ID"
            is_credit = t.credit is not None and t.credit > 0

            is_abs_large = amount >= self.config.large_transaction_abs_threshold
            ratio_to_median = (amount / median) if median > 0 else 1.0
            is_rel_large = (
                median > 0
                and ratio_to_median >= self.config.large_transaction_multiplier
                and amount >= self.config.large_transaction_min_relative_amount
            )

            if is_abs_large or is_rel_large:
                severity = (
                    SignalSeverity.HIGH
                    if amount >= self.config.large_transaction_abs_threshold * 2
                    else SignalSeverity.MEDIUM
                )
                flow_type = "incoming credit" if is_credit else "outgoing debit"
                if is_abs_large and is_rel_large:
                    explanation = (
                        f"Transaction {txn_id} of ₹{amount:,.2f} ({flow_type}) exceeded both the configured absolute "
                        f"transaction threshold of ₹{self.config.large_transaction_abs_threshold:,.2f} and the relative "
                        f"threshold ({ratio_to_median:.1f}x the customer median of ₹{median:,.2f})."
                    )
                elif is_abs_large:
                    if median > 0 and amount < median:
                        explanation = (
                            f"Transaction {txn_id} of ₹{amount:,.2f} ({flow_type}) exceeded the configured absolute "
                            f"transaction threshold of ₹{self.config.large_transaction_abs_threshold:,.2f}, although its "
                            f"value was below the customer's median transaction amount (₹{median:,.2f})."
                        )
                    else:
                        explanation = (
                            f"Transaction {txn_id} of ₹{amount:,.2f} ({flow_type}) exceeded the configured absolute "
                            f"transaction threshold of ₹{self.config.large_transaction_abs_threshold:,.2f} "
                            f"({ratio_to_median:.1f}x customer median of ₹{median:,.2f})."
                        )
                else:
                    explanation = (
                        f"Transaction {txn_id} of ₹{amount:,.2f} ({flow_type}) is {ratio_to_median:.1f}x "
                        f"the customer median transaction amount (₹{median:,.2f}), exceeding the relative-to-baseline threshold."
                    )
                supporting = {
                    "transaction_id": txn_id,
                    "date": str(t.date),
                    "amount": round(amount, 2),
                    "is_credit": is_credit,
                    "customer_median_amount": round(median, 2),
                    "ratio_to_median": round(ratio_to_median, 2),
                    "abs_threshold": self.config.large_transaction_abs_threshold,
                }
                signals.append(
                    RuleSignal(
                        rule_id="RULE_LARGE_TRANSACTION",
                        rule_name="Unusually Large Transaction",
                        transaction_ids=[txn_id],
                        severity=severity,
                        explanation=explanation,
                        supporting_values=supporting,
                    )
                )

        return signals

    def _check_sudden_volume_increase(
        self, sorted_txns: List, analytics: AnalyticsResult
    ) -> List[RuleSignal]:
        """Flag single calendar dates with aggregate volume spiking far above daily average."""
        if not analytics.daily_volume:
            return []

        signals = []
        daily_vols = [d.credit_total + d.debit_total for d in analytics.daily_volume]
        avg_daily_vol = sum(daily_vols) / len(daily_vols) if daily_vols else 0.0

        if avg_daily_vol <= 0:
            return []

        for d in analytics.daily_volume:
            total_day_vol = d.credit_total + d.debit_total
            if (
                total_day_vol >= self.config.volume_increase_min_amount
                and total_day_vol >= self.config.volume_increase_spike_multiplier * avg_daily_vol
            ):
                day_txns = [t.transaction_id or "UNKNOWN" for t in sorted_txns if t.date == d.date]
                ratio = total_day_vol / avg_daily_vol
                explanation = (
                    f"Aggregate volume on {d.date} reached {total_day_vol:,.2f}, which is "
                    f"{ratio:.1f}x the customer's average daily active volume of {avg_daily_vol:,.2f}."
                )
                supporting = {
                    "date": str(d.date),
                    "daily_volume": round(total_day_vol, 2),
                    "average_daily_volume": round(avg_daily_vol, 2),
                    "volume_ratio": round(ratio, 2),
                    "transaction_count": d.transaction_count,
                }
                signals.append(
                    RuleSignal(
                        rule_id="RULE_SUDDEN_VOLUME_INCREASE",
                        rule_name="Sudden Transaction Volume Increase",
                        transaction_ids=day_txns,
                        severity=SignalSeverity.MEDIUM,
                        explanation=explanation,
                        supporting_values=supporting,
                    )
                )

        return signals

    def _check_large_inflow_rapid_outflow(self, sorted_txns: List) -> List[RuleSignal]:
        """Detect large incoming credits followed within a short time by rapid draining debits."""
        signals = []
        n = len(sorted_txns)

        for i, t_in in enumerate(sorted_txns):
            if t_in.credit is None or t_in.credit < self.config.pass_through_min_credit:
                continue

            credit_amt = t_in.credit
            in_date = t_in.date
            cutoff_date = in_date + dt.timedelta(days=self.config.pass_through_lookforward_days)
            in_id = t_in.transaction_id or f"TXN_{i+1:03d}"

            subsequent_debits = []
            total_debit_amt = 0.0

            for j in range(i + 1, n):
                t_out = sorted_txns[j]
                if t_out.date > cutoff_date:
                    break
                if t_out.debit is not None and t_out.debit > 0:
                    subsequent_debits.append(t_out)
                    total_debit_amt += t_out.debit

            if total_debit_amt >= self.config.pass_through_turnover_ratio * credit_amt:
                debit_ids = [t.transaction_id or "UNKNOWN" for t in subsequent_debits]
                involved_ids = [in_id] + debit_ids
                turnover_pct = (total_debit_amt / credit_amt) * 100.0

                explanation = (
                    f"Incoming credit of {credit_amt:,.2f} ({in_id}) on {in_date} was followed "
                    f"within {self.config.pass_through_lookforward_days} day(s) by {len(debit_ids)} outgoing "
                    f"debit(s) totaling {total_debit_amt:,.2f} ({turnover_pct:.1f}% turnover)."
                )
                supporting = {
                    "credit_transaction_id": in_id,
                    "credit_amount": round(credit_amt, 2),
                    "credit_date": str(in_date),
                    "total_outflow": round(total_debit_amt, 2),
                    "turnover_ratio": round(total_debit_amt / credit_amt, 4),
                    "outgoing_transaction_count": len(debit_ids),
                    "lookforward_days": self.config.pass_through_lookforward_days,
                }
                signals.append(
                    RuleSignal(
                        rule_id="RULE_LARGE_INFLOW_RAPID_OUTFLOW",
                        rule_name="Large Incoming Transaction Followed by Rapid Outgoing",
                        transaction_ids=involved_ids,
                        severity=SignalSeverity.HIGH,
                        explanation=explanation,
                        supporting_values=supporting,
                    )
                )

        return signals

    def _check_rapid_funds_movement(self, sorted_txns: List) -> List[RuleSignal]:
        """Detect multi-transaction rapid velocity across a rolling temporal window."""
        signals = []
        n = len(sorted_txns)
        seen_window_starts = set()

        for i in range(n):
            start_date = sorted_txns[i].date
            if start_date in seen_window_starts:
                continue

            end_date = start_date + dt.timedelta(days=self.config.rapid_flow_window_days)
            window_txns = [t for t in sorted_txns if start_date <= t.date <= end_date]

            total_credits = sum(t.credit for t in window_txns if t.credit is not None)
            total_debits = sum(t.debit for t in window_txns if t.debit is not None)

            if total_credits >= self.config.rapid_flow_min_volume and total_debits > 0:
                turnover = total_debits / total_credits
                if turnover >= self.config.rapid_flow_turnover_ratio:
                    seen_window_starts.add(start_date)
                    txn_ids = [t.transaction_id or "UNKNOWN" for t in window_txns]
                    explanation = (
                        f"High-velocity fund turnover across {len(window_txns)} transactions between "
                        f"{start_date} and {end_date}: received {total_credits:,.2f} and disbursed "
                        f"{total_debits:,.2f} ({turnover * 100:.1f}% turnover)."
                    )
                    supporting = {
                        "window_start": str(start_date),
                        "window_end": str(end_date),
                        "window_credits": round(total_credits, 2),
                        "window_debits": round(total_debits, 2),
                        "turnover_ratio": round(turnover, 4),
                        "transaction_count": len(window_txns),
                    }
                    signals.append(
                        RuleSignal(
                            rule_id="RULE_RAPID_MOVEMENT_OF_FUNDS",
                            rule_name="Rapid Movement of Funds",
                            transaction_ids=txn_ids,
                            severity=SignalSeverity.HIGH if turnover >= 0.95 else SignalSeverity.MEDIUM,
                            explanation=explanation,
                            supporting_values=supporting,
                        )
                    )

        return signals

    def _check_many_new_counterparties(self, sorted_txns: List) -> List[RuleSignal]:
        """Flag introduction of many previously unseen counterparties."""
        seen_cps = set()
        new_cp_txns = []

        for t in sorted_txns:
            if t.counterparty:
                if t.counterparty not in seen_cps:
                    seen_cps.add(t.counterparty)
                    new_cp_txns.append(t)

        if len(new_cp_txns) >= self.config.many_new_counterparties_threshold:
            txn_ids = [t.transaction_id or "UNKNOWN" for t in new_cp_txns]
            cp_names = [t.counterparty for t in new_cp_txns if t.counterparty]
            explanation = (
                f"Observed {len(cp_names)} previously unseen counterparties introduced within the statement "
                f"period: {', '.join(cp_names)}."
            )
            supporting = {
                "new_counterparties_count": len(cp_names),
                "counterparty_names": cp_names,
                "threshold": self.config.many_new_counterparties_threshold,
            }
            return [
                RuleSignal(
                    rule_id="RULE_MANY_NEW_COUNTERPARTIES",
                    rule_name="Many New Counterparties",
                    transaction_ids=txn_ids,
                    severity=SignalSeverity.MEDIUM,
                    explanation=explanation,
                    supporting_values=supporting,
                )
            ]

        return []

    def _check_high_transaction_frequency(
        self, sorted_txns: List, analytics: AnalyticsResult
    ) -> List[RuleSignal]:
        """Flag abnormally high single-day clustering or statement-wide transaction bursts."""
        signals = []

        # Check single-day clustering
        for d in analytics.daily_volume:
            if d.transaction_count >= self.config.high_frequency_daily_count:
                day_txns = [t.transaction_id or "UNKNOWN" for t in sorted_txns if t.date == d.date]
                explanation = (
                    f"Concentration of {d.transaction_count} transactions recorded on a single day "
                    f"({d.date}), exceeding daily frequency threshold of {self.config.high_frequency_daily_count}."
                )
                supporting = {
                    "date": str(d.date),
                    "daily_count": d.transaction_count,
                    "threshold": self.config.high_frequency_daily_count,
                }
                signals.append(
                    RuleSignal(
                        rule_id="RULE_HIGH_TRANSACTION_FREQUENCY",
                        rule_name="Unusually High Transaction Frequency",
                        transaction_ids=day_txns,
                        severity=SignalSeverity.LOW,
                        explanation=explanation,
                        supporting_values=supporting,
                    )
                )

        # Check statement-wide frequency rate
        if (
            len(sorted_txns) >= 10
            and analytics.transaction_frequency >= self.config.high_frequency_statement_rate
        ):
            all_ids = [t.transaction_id or "UNKNOWN" for t in sorted_txns]
            explanation = (
                f"Overall statement transaction frequency of {analytics.transaction_frequency:.2f} txns/day "
                f"exceeds the screening threshold of {self.config.high_frequency_statement_rate:.2f} txns/day."
            )
            supporting = {
                "statement_frequency": analytics.transaction_frequency,
                "total_transactions": len(sorted_txns),
                "threshold": self.config.high_frequency_statement_rate,
            }
            signals.append(
                RuleSignal(
                    rule_id="RULE_HIGH_STATEMENT_FREQUENCY",
                    rule_name="High Overall Statement Velocity",
                    transaction_ids=all_ids,
                    severity=SignalSeverity.LOW,
                    explanation=explanation,
                    supporting_values=supporting,
                )
            )

        return signals
