"""Unit and integration tests for transaction investigation tools."""

import datetime as dt
from pathlib import Path
import pytest

from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_parser import parse_transactions
from aml_copilot.tools.transaction_tools import (
    SearchTransactionsInput,
    SearchTransactionsOutput,
    TransactionAnalyticsOutput,
    TransactionStatisticsOutput,
    create_analyze_transactions_tool,
    create_get_transaction_statistics_tool,
    create_search_transactions_tool,
    execute_analyze_transactions,
    execute_get_transaction_statistics,
    execute_search_transactions,
)

STATEMENTS_DIR = Path("data/statements")


@pytest.fixture
def sample_statement() -> TransactionStatement:
    """Provide a validated statement with known transactions for testing."""
    txns = [
        Transaction(
            date=dt.date(2026, 8, 1),
            transaction_id="TXN001",
            description="SALARY CREDIT FROM ACME TECH",
            credit=75000.0,
            balance=75000.0,
            counterparty="ACME TECH",
        ),
        Transaction(
            date=dt.date(2026, 8, 2),
            transaction_id="TXN002",
            description="MONTHLY APARTMENT RENT",
            debit=18000.0,
            balance=57000.0,
            counterparty="LANDLORD",
        ),
        Transaction(
            date=dt.date(2026, 8, 5),
            transaction_id="TXN003",
            description="GROCERY STORE PURCHASE",
            debit=3250.0,
            balance=53750.0,
            counterparty="SUPERMART",
        ),
        Transaction(
            date=dt.date(2026, 8, 15),
            transaction_id="TXN004",
            description="CONSULTING FEE CREDIT",
            credit=25000.0,
            balance=78750.0,
            counterparty="ACME TECH",
        ),
    ]
    return TransactionStatement(
        customer_name="Arjun Mehta",
        account_number="AC123456",
        statement_period="01 Aug 2026 to 15 Aug 2026",
        transactions=txns,
    )


# ---------------------------------------------------------------------------
# Test execute_analyze_transactions
# ---------------------------------------------------------------------------

def test_execute_analyze_transactions(sample_statement: TransactionStatement):
    """Verify analyze_transactions produces structured output and accurate calculations."""
    res = execute_analyze_transactions(sample_statement)

    assert isinstance(res, TransactionAnalyticsOutput)
    assert res.customer_name == "Arjun Mehta"
    assert res.transaction_count == 4
    assert res.total_credits == 100000.0
    assert res.total_debits == 21250.0
    assert res.net_cash_flow == 78750.0
    assert res.maximum_transaction == 75000.0
    assert set(res.unique_counterparties) == {"ACME TECH", "LANDLORD", "SUPERMART"}
    assert len(res.daily_volume) == 4
    assert res.time_gap_information.max_gap_days == 10


def test_analyze_transactions_langchain_tool(sample_statement: TransactionStatement):
    """Verify the LangChain analyze_transactions tool invocation."""
    tool = create_analyze_transactions_tool(sample_statement)
    assert tool.name == "analyze_transactions"
    assert "behavioral analytics" in tool.description

    output = tool.invoke({})
    assert isinstance(output, dict)
    assert output["transaction_count"] == 4
    assert output["net_cash_flow"] == 78750.0


# ---------------------------------------------------------------------------
# Test execute_get_transaction_statistics
# ---------------------------------------------------------------------------

def test_execute_get_transaction_statistics(sample_statement: TransactionStatement):
    """Verify get_transaction_statistics produces concise structured summary."""
    stats = execute_get_transaction_statistics(sample_statement)

    assert isinstance(stats, TransactionStatisticsOutput)
    assert stats.transaction_count == 4
    assert stats.credit_count == 2
    assert stats.debit_count == 2
    assert stats.total_volume == 121250.0
    assert stats.net_flow == 78750.0
    assert stats.max_credit == 75000.0
    assert stats.max_debit == 18000.0
    assert stats.statement_span_days == 15
    assert len(stats.top_counterparties) >= 1
    assert stats.top_counterparties[0].counterparty == "ACME TECH"
    assert stats.top_counterparties[0].total_amount == 100000.0


def test_get_transaction_statistics_langchain_tool(sample_statement: TransactionStatement):
    """Verify the LangChain statistics tool invocation."""
    tool = create_get_transaction_statistics_tool(sample_statement)
    assert tool.name == "get_transaction_statistics"

    output = tool.invoke({})
    assert isinstance(output, dict)
    assert output["credit_count"] == 2
    assert output["debit_count"] == 2


# ---------------------------------------------------------------------------
# Test execute_search_transactions
# ---------------------------------------------------------------------------

def test_search_transactions_by_id(sample_statement: TransactionStatement):
    """Filter by transaction ID."""
    params = SearchTransactionsInput(transaction_id="TXN002")
    res = execute_search_transactions(sample_statement, params)

    assert res.total_matched == 1
    assert res.transactions[0].transaction_id == "TXN002"
    assert res.transactions[0].amount == 18000.0


def test_search_transactions_by_counterparty(sample_statement: TransactionStatement):
    """Filter by counterparty case-insensitive."""
    params = SearchTransactionsInput(counterparty="acme")
    res = execute_search_transactions(sample_statement, params)

    assert res.total_matched == 2
    assert {t.transaction_id for t in res.transactions} == {"TXN001", "TXN004"}


def test_search_transactions_by_amount_range(sample_statement: TransactionStatement):
    """Filter by min and max amount."""
    params = SearchTransactionsInput(min_amount=10000.0, max_amount=30000.0)
    res = execute_search_transactions(sample_statement, params)

    assert res.total_matched == 2
    assert {t.transaction_id for t in res.transactions} == {"TXN002", "TXN004"}


def test_search_transactions_by_type(sample_statement: TransactionStatement):
    """Filter by credit or debit type."""
    res_credit = execute_search_transactions(sample_statement, SearchTransactionsInput(transaction_type="credit"))
    assert res_credit.total_matched == 2
    assert all(t.is_credit for t in res_credit.transactions)

    res_debit = execute_search_transactions(sample_statement, SearchTransactionsInput(transaction_type="debit"))
    assert res_debit.total_matched == 2
    assert all(not t.is_credit for t in res_debit.transactions)


def test_search_transactions_by_date_range(sample_statement: TransactionStatement):
    """Filter by start and end dates."""
    params = SearchTransactionsInput(start_date="2026-08-02", end_date="2026-08-05")
    res = execute_search_transactions(sample_statement, params)

    assert res.total_matched == 2
    assert {t.transaction_id for t in res.transactions} == {"TXN002", "TXN003"}


def test_search_transactions_by_keyword(sample_statement: TransactionStatement):
    """Filter by description keyword."""
    params = SearchTransactionsInput(keyword="apartment")
    res = execute_search_transactions(sample_statement, params)

    assert res.total_matched == 1
    assert res.transactions[0].transaction_id == "TXN002"


def test_search_transactions_combined_filters(sample_statement: TransactionStatement):
    """Filter combining counterparty, type, and minimum amount."""
    params = SearchTransactionsInput(
        counterparty="ACME",
        transaction_type="credit",
        min_amount=50000.0,
    )
    res = execute_search_transactions(sample_statement, params)

    assert res.total_matched == 1
    assert res.transactions[0].transaction_id == "TXN001"


def test_search_transactions_langchain_tool(sample_statement: TransactionStatement):
    """Verify LangChain search_transactions tool execution."""
    tool = create_search_transactions_tool(sample_statement)
    assert tool.name == "search_transactions"

    output = tool.invoke({"min_amount": 20000.0})
    assert isinstance(output, dict)
    assert output["total_matched"] == 2
    ids = {t["transaction_id"] for t in output["transactions"]}
    assert ids == {"TXN001", "TXN004"}


def test_search_transactions_negative_amount_validation():
    """Verify Pydantic validation catches invalid negative amounts."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SearchTransactionsInput(min_amount=-50.0)


def test_search_transactions_empty_statement():
    """Verify search returns 0 results cleanly on empty statement."""
    empty_stmt = TransactionStatement(customer_name="Empty", transactions=[])
    res = execute_search_transactions(empty_stmt, SearchTransactionsInput())
    assert res.total_matched == 0
    assert res.returned_count == 0
    assert res.transactions == []


@pytest.mark.parametrize(
    "pdf_filename, min_txns",
    [
        ("normal_statement.pdf", 14),
        ("suspicious_statement.pdf", 15),
        ("mixed_statement.pdf", 14),
    ],
)
def test_tools_on_synthetic_pdfs(pdf_filename: str, min_txns: int):
    """Verify tools execute deterministically on all three synthetic PDF statements."""
    pdf_path = STATEMENTS_DIR / pdf_filename
    if not pdf_path.exists():
        pytest.skip(f"PDF {pdf_filename} not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)

    analytics_out = execute_analyze_transactions(stmt)
    assert analytics_out.transaction_count == min_txns
    assert analytics_out.average_transaction > 0

    stats_out = execute_get_transaction_statistics(stmt)
    assert stats_out.transaction_count == min_txns
    assert stats_out.total_volume > 0

    search_out = execute_search_transactions(stmt, SearchTransactionsInput(limit=100))
    assert search_out.total_matched == min_txns
