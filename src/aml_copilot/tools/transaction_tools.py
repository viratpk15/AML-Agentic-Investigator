"""Deterministic transaction analysis and search tools for AML investigation."""

import datetime as dt
from typing import Any, Dict, List, Literal, Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from aml_copilot.analysis.transaction_analytics import AnalyticsResult, analyze_transactions
from aml_copilot.logger import get_logger
from aml_copilot.models.transaction import Transaction, TransactionStatement

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pydantic Schemas for Tool Inputs and Outputs
# ---------------------------------------------------------------------------

class DailyVolumeSummary(BaseModel):
    """Daily aggregated transaction volume."""

    date: str
    credit_total: float
    debit_total: float
    net_flow: float
    transaction_count: int


class TimeGapSummary(BaseModel):
    """Summary of intervals between consecutive transactions."""

    min_gap_days: int
    max_gap_days: int
    mean_gap_days: float
    gaps: List[int]


class TransactionAnalyticsOutput(BaseModel):
    """Detailed behavioral and statistical analytics across transactions."""

    customer_name: Optional[str] = None
    account_number: Optional[str] = None
    statement_period: Optional[str] = None
    transaction_count: int
    total_credits: float
    total_debits: float
    net_cash_flow: float
    average_transaction: float
    median_transaction: float
    maximum_transaction: float
    credit_debit_ratio: Optional[float] = None
    unique_counterparties: List[str]
    transaction_frequency: float
    daily_volume: List[DailyVolumeSummary]
    time_gap_information: TimeGapSummary


class TopCounterparty(BaseModel):
    """Aggregated volume and activity for a specific counterparty."""

    counterparty: str
    transaction_count: int
    total_amount: float
    is_credit: bool


class TransactionStatisticsOutput(BaseModel):
    """Concise transaction statistics tailored for quick investigative screening."""

    customer_name: Optional[str] = None
    transaction_count: int
    total_volume: float
    net_flow: float
    credit_count: int
    debit_count: int
    credit_sum: float
    debit_sum: float
    credit_debit_ratio: Optional[float] = None
    average_amount: float
    median_amount: float
    max_credit: float
    max_debit: float
    statement_span_days: int
    active_days_count: int
    unique_counterparties_count: int
    top_counterparties: List[TopCounterparty]


class TransactionRecord(BaseModel):
    """Structured representation of a single matching transaction preserving audit trail."""

    transaction_id: str
    date: str
    description: str
    debit: Optional[float] = None
    credit: Optional[float] = None
    amount: float
    balance: float
    counterparty: Optional[str] = None
    is_credit: bool


class SearchTransactionsInput(BaseModel):
    """Parameters for filtering transactions within a customer statement."""

    transaction_id: Optional[str] = Field(
        default=None,
        description="Filter by specific transaction ID (e.g., 'TXN005' or partial match)",
    )
    counterparty: Optional[str] = Field(
        default=None,
        description="Filter transactions containing this counterparty name (case-insensitive)",
    )
    min_amount: Optional[float] = Field(
        default=None, ge=0.0, description="Minimum absolute transaction amount"
    )
    max_amount: Optional[float] = Field(
        default=None, ge=0.0, description="Maximum absolute transaction amount"
    )
    transaction_type: Literal["all", "credit", "debit"] = Field(
        default="all",
        description="Filter by flow direction: 'credit' for incoming, 'debit' for outgoing, or 'all'",
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Earliest transaction date in ISO format YYYY-MM-DD",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Latest transaction date in ISO format YYYY-MM-DD",
    )
    keyword: Optional[str] = Field(
        default=None,
        description="Search keyword within transaction description (case-insensitive)",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of matching transaction records to return",
    )


class SearchTransactionsOutput(BaseModel):
    """Result of searching/filtering transactions."""

    total_matched: int
    returned_count: int
    transactions: List[TransactionRecord]


# ---------------------------------------------------------------------------
# Direct Deterministic Execution Functions
# ---------------------------------------------------------------------------

def execute_analyze_transactions(
    statement: TransactionStatement,
    analytics: Optional[AnalyticsResult] = None,
) -> TransactionAnalyticsOutput:
    """Execute transaction analytics over a validated statement.

    Args:
        statement: Validated TransactionStatement.
        analytics: Optional pre-computed AnalyticsResult.

    Returns:
        TransactionAnalyticsOutput model.
    """
    if analytics is None:
        analytics = analyze_transactions(statement)

    net_flow = round(analytics.total_credits - analytics.total_debits, 2)

    daily_vols = [
        DailyVolumeSummary(
            date=str(d.date),
            credit_total=d.credit_total,
            debit_total=d.debit_total,
            net_flow=d.net_flow,
            transaction_count=d.transaction_count,
        )
        for d in analytics.daily_volume
    ]

    gaps = analytics.transaction_time_gaps
    gap_summary = TimeGapSummary(
        min_gap_days=min(gaps, default=0),
        max_gap_days=max(gaps, default=0),
        mean_gap_days=round(sum(gaps) / len(gaps), 2) if gaps else 0.0,
        gaps=gaps,
    )

    return TransactionAnalyticsOutput(
        customer_name=statement.customer_name,
        account_number=statement.account_number,
        statement_period=statement.statement_period,
        transaction_count=analytics.total_transactions,
        total_credits=analytics.total_credits,
        total_debits=analytics.total_debits,
        net_cash_flow=net_flow,
        average_transaction=analytics.average_transaction,
        median_transaction=analytics.median_transaction,
        maximum_transaction=analytics.maximum_transaction,
        credit_debit_ratio=analytics.credit_debit_ratio,
        unique_counterparties=analytics.unique_counterparties,
        transaction_frequency=analytics.transaction_frequency,
        daily_volume=daily_vols,
        time_gap_information=gap_summary,
    )


def execute_get_transaction_statistics(
    statement: TransactionStatement,
    analytics: Optional[AnalyticsResult] = None,
) -> TransactionStatisticsOutput:
    """Compute concise statistical summary from statement transactions.

    Args:
        statement: Validated TransactionStatement.
        analytics: Optional pre-computed AnalyticsResult.

    Returns:
        TransactionStatisticsOutput model.
    """
    if analytics is None:
        analytics = analyze_transactions(statement)

    txns = statement.transactions
    credits = [t.credit for t in txns if t.credit is not None]
    debits = [t.debit for t in txns if t.debit is not None]

    credit_count = len(credits)
    debit_count = len(debits)
    credit_sum = round(sum(credits), 2)
    debit_sum = round(sum(debits), 2)
    total_volume = round(credit_sum + debit_sum, 2)
    net_flow = round(credit_sum - debit_sum, 2)

    max_credit = max(credits, default=0.0)
    max_debit = max(debits, default=0.0)

    # Date calculations
    if txns:
        sorted_dates = sorted(t.date for t in txns)
        span_days = max(1, (sorted_dates[-1] - sorted_dates[0]).days + 1)
        active_days = len(set(sorted_dates))
    else:
        span_days = 0
        active_days = 0

    # Top counterparties calculation
    cp_aggregates: Dict[str, Dict[str, Any]] = {}
    for t in txns:
        if t.counterparty:
            amt = t.credit if t.credit is not None else (t.debit if t.debit is not None else 0.0)
            is_c = t.credit is not None and t.credit > 0
            if t.counterparty not in cp_aggregates:
                cp_aggregates[t.counterparty] = {
                    "count": 0,
                    "total": 0.0,
                    "is_credit": is_c,
                }
            cp_aggregates[t.counterparty]["count"] += 1
            cp_aggregates[t.counterparty]["total"] += amt

    sorted_cps = sorted(
        cp_aggregates.items(),
        key=lambda item: item[1]["total"],
        reverse=True,
    )
    top_cps = [
        TopCounterparty(
            counterparty=name,
            transaction_count=data["count"],
            total_amount=round(data["total"], 2),
            is_credit=data["is_credit"],
        )
        for name, data in sorted_cps[:5]
    ]

    return TransactionStatisticsOutput(
        customer_name=statement.customer_name,
        transaction_count=len(txns),
        total_volume=total_volume,
        net_flow=net_flow,
        credit_count=credit_count,
        debit_count=debit_count,
        credit_sum=credit_sum,
        debit_sum=debit_sum,
        credit_debit_ratio=analytics.credit_debit_ratio,
        average_amount=analytics.average_transaction,
        median_amount=analytics.median_transaction,
        max_credit=round(max_credit, 2),
        max_debit=round(max_debit, 2),
        statement_span_days=span_days,
        active_days_count=active_days,
        unique_counterparties_count=len(analytics.unique_counterparties),
        top_counterparties=top_cps,
    )


def execute_search_transactions(
    statement: TransactionStatement,
    params: SearchTransactionsInput,
) -> SearchTransactionsOutput:
    """Filter transactions deterministically based on structured filter criteria.

    Args:
        statement: Validated TransactionStatement.
        params: SearchTransactionsInput filter parameters.

    Returns:
        SearchTransactionsOutput containing matched transaction records.
    """
    results: List[TransactionRecord] = []

    # Parse optional dates
    start_d: Optional[dt.date] = None
    end_d: Optional[dt.date] = None
    if params.start_date:
        start_d = dt.date.fromisoformat(params.start_date)
    if params.end_date:
        end_d = dt.date.fromisoformat(params.end_date)

    for idx, t in enumerate(statement.transactions):
        txn_id = t.transaction_id or f"TXN_{idx+1:03d}"
        amount = t.credit if t.credit is not None else (t.debit if t.debit is not None else 0.0)
        is_credit = t.credit is not None and t.credit > 0

        # Filter: transaction_id
        if params.transaction_id:
            if params.transaction_id.lower() not in txn_id.lower():
                continue

        # Filter: counterparty
        if params.counterparty:
            if not t.counterparty or params.counterparty.lower() not in t.counterparty.lower():
                continue

        # Filter: min_amount
        if params.min_amount is not None:
            if amount < params.min_amount:
                continue

        # Filter: max_amount
        if params.max_amount is not None:
            if amount > params.max_amount:
                continue

        # Filter: transaction_type
        if params.transaction_type == "credit" and not is_credit:
            continue
        if params.transaction_type == "debit" and is_credit:
            continue

        # Filter: date range
        if start_d and t.date < start_d:
            continue
        if end_d and t.date > end_d:
            continue

        # Filter: keyword in description
        if params.keyword:
            if params.keyword.lower() not in t.description.lower():
                continue

        results.append(
            TransactionRecord(
                transaction_id=txn_id,
                date=str(t.date),
                description=t.description,
                debit=t.debit,
                credit=t.credit,
                amount=round(amount, 2),
                balance=round(t.balance, 2),
                counterparty=t.counterparty,
                is_credit=is_credit,
            )
        )

    total_matched = len(results)
    limited_results = results[: params.limit]

    return SearchTransactionsOutput(
        total_matched=total_matched,
        returned_count=len(limited_results),
        transactions=limited_results,
    )


# ---------------------------------------------------------------------------
# LangChain Tool Factory
# ---------------------------------------------------------------------------

def create_analyze_transactions_tool(statement: TransactionStatement) -> StructuredTool:
    """Create a LangChain tool for computing behavioral analytics on the active statement."""

    def _tool_fn() -> Dict[str, Any]:
        result = execute_analyze_transactions(statement)
        return result.model_dump()

    return StructuredTool.from_function(
        func=_tool_fn,
        name="analyze_transactions",
        description=(
            "Use this tool to calculate transaction-level behavioral analytics from the customer's "
            "bank statement. Returns metrics such as total credits, total debits, net cash flow, "
            "average/median transaction amounts, credit-to-debit ratio, unique counterparties, "
            "daily volume breakdowns, and transaction time gaps."
        ),
    )


def create_get_transaction_statistics_tool(statement: TransactionStatement) -> StructuredTool:
    """Create a LangChain tool for retrieving concise transaction statistics."""

    def _tool_fn() -> Dict[str, Any]:
        result = execute_get_transaction_statistics(statement)
        return result.model_dump()

    return StructuredTool.from_function(
        func=_tool_fn,
        name="get_transaction_statistics",
        description=(
            "Use this tool to obtain concise, high-level summary statistics about the customer's "
            "transactions. Returns total volume, net flow, credit/debit counts and sums, maximum credit, "
            "maximum debit, active statement span, and top counterparties by monetary volume."
        ),
    )


def create_search_transactions_tool(statement: TransactionStatement) -> StructuredTool:
    """Create a LangChain tool for searching and filtering transactions in the active statement."""

    def _tool_fn(
        transaction_id: Optional[str] = None,
        counterparty: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        transaction_type: Literal["all", "credit", "debit"] = "all",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        params = SearchTransactionsInput(
            transaction_id=transaction_id,
            counterparty=counterparty,
            min_amount=min_amount,
            max_amount=max_amount,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword,
            limit=limit,
        )
        result = execute_search_transactions(statement, params)
        return result.model_dump()

    return StructuredTool.from_function(
        func=_tool_fn,
        name="search_transactions",
        description=(
            "Use this tool to search, query, and filter specific transactions from the customer's statement. "
            "Supports filtering by transaction ID, counterparty name, minimum/maximum amount, transaction type "
            "('credit' or 'debit'), date range (start_date/end_date in YYYY-MM-DD), and description keyword. "
            "Returns exact transaction IDs, dates, amounts, counterparties, and running balances for evidence gathering."
        ),
        args_schema=SearchTransactionsInput,
    )
