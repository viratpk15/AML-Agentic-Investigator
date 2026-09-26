"""Unit tests for M12 customer profiling and behavioral indicators."""

import datetime as dt

from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.profiling.customer_profile import CustomerProfile
from aml_copilot.profiling.profiler import build_customer_profile
from aml_copilot.tools.profile_tools import (
    GetCustomerProfileInput,
    create_get_customer_profile_tool,
)


def _sample_retail_statement() -> TransactionStatement:
    """Standard retail employee statement."""
    return TransactionStatement(
        customer_name="John Doe",
        account_number="ACC-1001",
        statement_period="2026-08-01 to 2026-08-31",
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 1),
                transaction_id="TXN001",
                description="SALARY CREDIT",
                credit=75000.0,
                debit=None,
                balance=75000.0,
                counterparty="ACME CORP",
            ),
            Transaction(
                date=dt.date(2026, 8, 5),
                transaction_id="TXN002",
                description="GROCERY STORE",
                credit=None,
                debit=4500.0,
                balance=70500.0,
                counterparty="SUPERMART",
            ),
            Transaction(
                date=dt.date(2026, 8, 15),
                transaction_id="TXN003",
                description="UTILITIES",
                credit=None,
                debit=3000.0,
                balance=67500.0,
                counterparty="CITY POWER",
            ),
        ],
    )


def _sample_commercial_statement() -> TransactionStatement:
    """High-volume statement with rapid fund movement and multiple counterparties."""
    return TransactionStatement(
        customer_name="Alpha Global Trading",
        account_number="ACC-9999",
        statement_period="2026-08-01 to 2026-08-31",
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN005",
                description="ORION TRADING CREDIT",
                credit=480000.0,
                debit=None,
                balance=480000.0,
                counterparty="ORION TRADING",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN006",
                description="RAHUL EXPORTS WIRE OUT",
                credit=None,
                debit=475000.0,
                balance=5000.0,
                counterparty="RAHUL EXPORTS",
            ),
            Transaction(
                date=dt.date(2026, 8, 12),
                transaction_id="TXN007",
                description="INVOICE 101",
                credit=120000.0,
                debit=None,
                balance=125000.0,
                counterparty="BETA SUPPLIES",
            ),
            Transaction(
                date=dt.date(2026, 8, 14),
                transaction_id="TXN008",
                description="VENDOR PAYMENT",
                credit=None,
                debit=80000.0,
                balance=45000.0,
                counterparty="GAMMA LOGISTICS",
            ),
            Transaction(
                date=dt.date(2026, 8, 18),
                transaction_id="TXN009",
                description="OFFICE SUPPLIES",
                credit=None,
                debit=15000.0,
                balance=30000.0,
                counterparty="DELTA CORP",
            ),
            Transaction(
                date=dt.date(2026, 8, 20),
                transaction_id="TXN010",
                description="EQUIPMENT",
                credit=None,
                debit=20000.0,
                balance=10000.0,
                counterparty="EPSILON TECH",
            ),
        ],
    )


def test_build_customer_profile_retail():
    """Verify profile calculation on retail statement."""
    stmt = _sample_retail_statement()
    profile = build_customer_profile(stmt)

    assert isinstance(profile, CustomerProfile)
    assert profile.customer_name == "John Doe"
    assert profile.total_transactions == 3
    assert profile.total_credits == 75000.0
    assert profile.total_debits == 7500.0
    assert profile.net_cash_flow == 67500.0
    assert profile.credit_transaction_count == 1
    assert profile.debit_transaction_count == 2
    assert profile.dominant_transaction_type == "debit"
    assert profile.unique_counterparty_count == 3
    assert profile.largest_credit is not None
    assert profile.largest_credit.amount == 75000.0
    assert profile.largest_credit.transaction_id == "TXN001"
    assert profile.largest_debit is not None
    assert profile.largest_debit.amount == 4500.0
    assert profile.largest_debit.transaction_id == "TXN002"


def test_build_customer_profile_commercial_with_indicators():
    """Verify behavioral indicators triggered on commercial high-turnover statement."""
    stmt = _sample_commercial_statement()
    profile = build_customer_profile(stmt)

    assert profile.total_transactions == 6
    assert profile.total_credits == 600000.0
    assert profile.total_debits == 590000.0
    assert profile.maximum_transaction_amount == 480000.0

    indicator_names = {ind.name for ind in profile.indicators}
    assert "high_value_activity" in indicator_names
    assert "high_transaction_volume" in indicator_names
    assert "many_counterparties" in indicator_names
    assert "rapid_fund_movement" in indicator_names

    # Check evidence traceability for rapid fund movement
    rapid_ind = next(ind for ind in profile.indicators if ind.name == "rapid_fund_movement")
    assert "TXN005" in rapid_ind.supporting_transaction_ids
    assert "TXN006" in rapid_ind.supporting_transaction_ids

    # Check safety: No accusatory language
    for ind in profile.indicators:
        assert "crime" not in ind.description.lower()
        assert "guilt" not in ind.description.lower()
        assert "laundering" not in ind.description.lower()
        assert "suspicious" not in ind.description.lower()


def test_build_customer_profile_empty():
    """Verify graceful handling of empty statement."""
    empty_stmt = TransactionStatement(customer_name="Empty Customer", transactions=[])
    profile = build_customer_profile(empty_stmt)

    assert profile.total_transactions == 0
    assert profile.total_credits == 0.0
    assert profile.total_debits == 0.0
    assert profile.indicators == []


def test_get_customer_profile_tool():
    """Verify get_customer_profile tool invocation via LangChain StructuredTool."""
    stmt = _sample_commercial_statement()
    tool = create_get_customer_profile_tool(stmt)

    assert tool.name == "get_customer_profile"
    assert "profile" in tool.description.lower()

    output = tool.invoke({"include_indicators": True})
    assert isinstance(output, dict)
    assert output["customer_name"] == "Alpha Global Trading"
    assert output["total_transactions"] == 6
    assert len(output["indicators"]) > 0

    # Test with include_indicators=False
    output_no_ind = tool.invoke({"include_indicators": False})
    assert output_no_ind["indicators"] == []


def test_profile_tool_schema_validation():
    """Verify GetCustomerProfileInput schema constraints."""
    valid_input = GetCustomerProfileInput(include_indicators=True)
    assert valid_input.include_indicators is True
