"""Customer profile models and behavioral indicators."""

import datetime as dt
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BehavioralIndicator(BaseModel):
    """Factual, non-judgmental behavioral observation derived from transaction patterns."""

    name: str = Field(..., description="Machine-readable indicator identifier")
    description: str = Field(..., description="Objective, non-accusatory observation description")
    supporting_transaction_ids: List[str] = Field(
        default_factory=list,
        description="Transaction IDs that directly support this behavioral observation",
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Factual values and metrics triggering this indicator",
    )


class LargestTransactionRecord(BaseModel):
    """Details of the largest single credit or debit transaction."""

    transaction_id: str
    amount: float
    date: dt.date
    description: str
    counterparty: Optional[str] = None


class CustomerProfile(BaseModel):
    """Structured behavioral profile summarizing a customer's transaction activity."""

    customer_name: Optional[str] = Field(default=None, description="Account holder name")
    account_number: Optional[str] = Field(default=None, description="Customer account number")
    statement_period: Optional[str] = Field(default=None, description="Statement duration period")

    # Transaction volume & Cash flow
    total_transactions: int = Field(..., description="Total count of transactions in statement")
    total_credits: float = Field(..., description="Sum of all incoming credit amounts")
    total_debits: float = Field(..., description="Sum of all outgoing debit amounts")
    net_cash_flow: float = Field(..., description="Net flow: total credits minus total debits")

    # Transaction statistics
    average_transaction_amount: float = Field(..., description="Mean transaction amount")
    median_transaction_amount: float = Field(..., description="Median transaction amount")
    maximum_transaction_amount: float = Field(..., description="Maximum single transaction amount")

    # Breakdown by flow direction
    credit_transaction_count: int = Field(..., description="Count of credit transactions")
    debit_transaction_count: int = Field(..., description="Count of debit transactions")
    dominant_transaction_type: str = Field(
        ..., description="Dominant flow direction: 'credit', 'debit', or 'balanced'"
    )
    credit_to_debit_ratio: Optional[float] = Field(
        default=None, description="Ratio of total credits to total debits"
    )

    # Counterparty metrics
    unique_counterparty_count: int = Field(..., description="Total count of distinct counterparties")
    new_counterparty_count: int = Field(..., description="Count of newly introduced counterparties")
    unique_counterparties: List[str] = Field(
        default_factory=list, description="List of distinct counterparties"
    )

    # Temporal & Velocity metrics
    active_days: int = Field(..., description="Count of days with transaction activity")
    transaction_frequency: float = Field(
        ..., description="Average transactions per day across statement calendar span"
    )
    average_daily_volume: float = Field(..., description="Average total turnover on active days")
    maximum_daily_volume: float = Field(..., description="Peak single-day total turnover")

    # Peak individual transactions
    largest_credit: Optional[LargestTransactionRecord] = Field(
        default=None, description="Largest single incoming credit record"
    )
    largest_debit: Optional[LargestTransactionRecord] = Field(
        default=None, description="Largest single outgoing debit record"
    )

    # Behavioral classification indicators
    indicators: List[BehavioralIndicator] = Field(
        default_factory=list,
        description="Factual, non-judgmental behavioral indicators observed in the customer profile",
    )
