"""Unit and integration tests for transaction analytics service."""

import datetime as dt
from pathlib import Path
import pytest

from aml_copilot.analysis import AnalyticsResult, DailyVolume, analyze_transactions
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_parser import parse_transactions

STATEMENTS_DIR = Path("data/statements")


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

def test_analyze_empty_statement():
    """Verify analytics behavior on an empty statement."""
    empty_stmt = TransactionStatement(transactions=[])
    res = analyze_transactions(empty_stmt)

    assert isinstance(res, AnalyticsResult)
    assert res.total_transactions == 0
    assert res.total_credits == 0.0
    assert res.total_debits == 0.0
    assert res.average_transaction == 0.0
    assert res.median_transaction == 0.0
    assert res.maximum_transaction == 0.0
    assert res.credit_debit_ratio is None
    assert res.unique_counterparties == []
    assert res.transaction_frequency == 0.0
    assert res.daily_volume == []
    assert res.transaction_time_gaps == []
    assert res.new_counterparties == []


def test_analyze_credits_only():
    """Verify credit_debit_ratio handles zero debits correctly."""
    stmt = TransactionStatement(
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 1),
                transaction_id="TXN001",
                description="SALARY",
                credit=5000.0,
                balance=5000.0,
            )
        ]
    )
    res = analyze_transactions(stmt)

    assert res.total_transactions == 1
    assert res.total_credits == 5000.0
    assert res.total_debits == 0.0
    assert res.credit_debit_ratio is None
    assert res.transaction_frequency == 1.0


def test_analyze_time_gaps_and_frequency():
    """Verify chronological time gaps and frequency calculations."""
    stmt = TransactionStatement(
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 1),
                description="T1",
                debit=100.0,
                balance=900.0,
            ),
            Transaction(
                date=dt.date(2026, 8, 3),
                description="T2",
                debit=200.0,
                balance=700.0,
            ),
            Transaction(
                date=dt.date(2026, 8, 3),
                description="T3",
                debit=50.0,
                balance=650.0,
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                description="T4",
                debit=150.0,
                balance=500.0,
            ),
        ]
    )
    res = analyze_transactions(stmt)

    assert res.total_transactions == 4
    # Gaps between Aug 1 -> Aug 3 (2 days), Aug 3 -> Aug 3 (0 days), Aug 3 -> Aug 10 (7 days)
    assert res.transaction_time_gaps == [2, 0, 7]
    # Span from Aug 1 to Aug 10 is 10 days inclusive: 4 / 10 = 0.4
    assert res.transaction_frequency == 0.4
    # Daily volumes: 3 distinct days
    assert len(res.daily_volume) == 3


def test_new_counterparties_chronology():
    """Verify that new counterparties are captured in first-seen order."""
    stmt = TransactionStatement(
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 5),
                description="NEFT - VENDOR B",
                credit=1000.0,
                balance=1000.0,
                counterparty="VENDOR B",
            ),
            Transaction(
                date=dt.date(2026, 8, 1),
                description="SALARY - VENDOR A",
                credit=2000.0,
                balance=2000.0,
                counterparty="VENDOR A",
            ),
            Transaction(
                date=dt.date(2026, 8, 6),
                description="REPEAT - VENDOR A",
                credit=500.0,
                balance=2500.0,
                counterparty="VENDOR A",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                description="TRANSFER - VENDOR C",
                credit=700.0,
                balance=3200.0,
                counterparty="VENDOR C",
            ),
        ]
    )
    res = analyze_transactions(stmt)

    # Sorted order: Aug 1 (VENDOR A), Aug 5 (VENDOR B), Aug 6 (VENDOR A - seen), Aug 10 (VENDOR C)
    assert res.new_counterparties == ["VENDOR A", "VENDOR B", "VENDOR C"]
    assert res.unique_counterparties == ["VENDOR A", "VENDOR B", "VENDOR C"]


# ---------------------------------------------------------------------------
# Integration Tests on Synthetic PDF Statements
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not (STATEMENTS_DIR / "normal_statement.pdf").exists(),
    reason="Synthetic statements directory not available",
)
def test_analytics_normal_statement():
    """Verify analytics on normal_statement.pdf."""
    doc = extract_pdf_text(STATEMENTS_DIR / "normal_statement.pdf")
    stmt = parse_transactions(doc)
    res = analyze_transactions(stmt)

    assert res.total_transactions == 14
    assert res.total_credits == 90000.00
    assert res.total_debits == 45698.00
    assert res.maximum_transaction == 75000.00
    assert res.average_transaction == 9692.71
    assert res.median_transaction == 3025.00

    assert res.credit_debit_ratio == pytest.approx(1.9695, rel=1e-3)
    assert res.unique_counterparties == ["ACME TECH", "GROCERY MART", "RENT", "RESTAURANT"]
    assert res.new_counterparties == ["ACME TECH", "RENT", "GROCERY MART", "RESTAURANT"]
    assert len(res.daily_volume) == 14
    # Statement period: 01 Aug to 30 Aug = 30 days; 14/30 = 0.4667
    assert res.transaction_frequency == pytest.approx(0.4667, rel=1e-3)


@pytest.mark.skipif(
    not (STATEMENTS_DIR / "suspicious_statement.pdf").exists(),
    reason="Synthetic statements directory not available",
)
def test_analytics_suspicious_statement():
    """Verify analytics on suspicious_statement.pdf with high turnover and rapid transfers."""
    doc = extract_pdf_text(STATEMENTS_DIR / "suspicious_statement.pdf")
    stmt = parse_transactions(doc)
    res = analyze_transactions(stmt)

    assert res.total_transactions == 15
    assert res.total_credits == 1065000.00
    assert res.total_debits == 1627100.00
    assert res.maximum_transaction == 480000.00
    assert res.average_transaction == 179473.33
    assert res.credit_debit_ratio == pytest.approx(0.6545, rel=1e-3)
    # Check that new high-value counterparties are identified
    assert "ORION TRADING" in res.new_counterparties
    assert "RAHUL SERVICES" in res.new_counterparties
    assert "KIRAN ENTERPRISE" in res.new_counterparties
    assert "NEW COUNTERPARTY 01" in res.new_counterparties


@pytest.mark.skipif(
    not (STATEMENTS_DIR / "mixed_statement.pdf").exists(),
    reason="Synthetic statements directory not available",
)
def test_analytics_mixed_statement():
    """Verify analytics on mixed_statement.pdf."""
    doc = extract_pdf_text(STATEMENTS_DIR / "mixed_statement.pdf")
    stmt = parse_transactions(doc)
    res = analyze_transactions(stmt)

    assert res.total_transactions == 14
    assert res.total_credits == 470000.00
    assert res.total_debits == 630450.00
    assert res.maximum_transaction == 320000.00
    assert "NOVA EXPORTS" in res.new_counterparties
    assert "APEX CONSULTING" in res.new_counterparties
    assert "RAVI TRADERS" in res.new_counterparties
