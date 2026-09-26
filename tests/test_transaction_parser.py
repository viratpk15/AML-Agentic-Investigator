"""Unit and integration tests for transaction parsing and validation."""

import datetime as dt
from pathlib import Path
import pytest
from pydantic import ValidationError

from aml_copilot.exceptions import TransactionParsingError
from aml_copilot.models.pdf import PDFDocumentExtraction, PDFPage
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_parser import (
    extract_counterparty,
    parse_amount,
    parse_date,
    parse_row_tokens,
    parse_transactions,
)

STATEMENTS_DIR = Path("data/statements")


# ---------------------------------------------------------------------------
# Unit Tests for Helper Functions
# ---------------------------------------------------------------------------

def test_parse_date_valid():
    """Verify parsing supported date string formats."""
    assert parse_date("01 Aug 2026") == dt.date(2026, 8, 1)
    assert parse_date("15 August 2026") == dt.date(2026, 8, 15)
    assert parse_date("2026-08-01") == dt.date(2026, 8, 1)
    assert parse_date("01/08/2026") == dt.date(2026, 8, 1)
    assert parse_date("01-08-2026") == dt.date(2026, 8, 1)


def test_parse_date_invalid():
    """Verify invalid date strings return None."""
    assert parse_date("Not A Date") is None
    assert parse_date("32 Aug 2026") is None
    assert parse_date("2026-13-45") is None


def test_parse_amount_valid():
    """Verify amount cleaning including commas, currency symbols, and negatives."""
    assert parse_amount("75,000.00") == 75000.0
    assert parse_amount("INR 18,000.00") == 18000.0
    assert parse_amount("₹ 3,250.50") == 3250.50
    assert parse_amount("$500") == 500.0
    assert parse_amount("-206,200.00") == -206200.0
    assert parse_amount("(1,500.00)") == -1500.0


def test_parse_amount_empty_markers():
    """Verify empty/dash markers return None when allowed."""
    assert parse_amount("—", allow_none=True) is None
    assert parse_amount("–", allow_none=True) is None
    assert parse_amount("-", allow_none=True) is None
    assert parse_amount("N/A", allow_none=True) is None
    assert parse_amount("", allow_none=True) is None

    with pytest.raises(ValueError):
        parse_amount("—", allow_none=False)


def test_extract_counterparty():
    """Verify deterministic counterparty extraction from descriptions."""
    assert extract_counterparty("SALARY CREDIT - ACME TECH") == "ACME TECH"
    assert extract_counterparty("NEFT - ORION TRADING") == "ORION TRADING"
    assert extract_counterparty("IMPS - RAHUL SERVICES") == "RAHUL SERVICES"
    assert extract_counterparty("UPI - NEW COUNTERPARTY 01") == "NEW COUNTERPARTY 01"
    assert extract_counterparty("RENT - UPI") == "RENT"
    assert extract_counterparty("GROCERY MART - UPI") == "GROCERY MART"
    assert extract_counterparty("ELECTRICITY BILL") is None
    assert extract_counterparty("ATM CASH WITHDRAWAL") is None
    assert extract_counterparty("ONLINE SHOPPING") is None


# ---------------------------------------------------------------------------
# Invariant and Model Validation Tests
# ---------------------------------------------------------------------------

def test_transaction_model_valid():
    """Verify creating a valid Transaction."""
    txn = Transaction(
        date=dt.date(2026, 8, 1),
        transaction_id="TXN001",
        description="SALARY CREDIT - ACME TECH",
        debit=None,
        credit=75000.0,
        balance=165000.0,
        counterparty="ACME TECH",
    )
    assert txn.credit == 75000.0
    assert txn.debit is None
    assert txn.balance == 165000.0


def test_transaction_both_debit_and_credit_rejected():
    """Verify transaction cannot have both positive debit and credit."""
    with pytest.raises(ValidationError) as exc_info:
        Transaction(
            date=dt.date(2026, 8, 1),
            description="INVALID TRANSACTION",
            debit=100.0,
            credit=200.0,
            balance=500.0,
        )
    assert "Transaction cannot have both positive debit" in str(exc_info.value)


def test_transaction_neither_debit_nor_credit_rejected():
    """Verify transaction must specify either debit or credit."""
    with pytest.raises(ValidationError) as exc_info:
        Transaction(
            date=dt.date(2026, 8, 1),
            description="INVALID TRANSACTION",
            debit=None,
            credit=None,
            balance=500.0,
        )
    assert "Transaction must have either a debit or credit amount" in str(exc_info.value)


def test_transaction_negative_debit_or_credit_rejected():
    """Verify debit and credit must be non-negative."""
    with pytest.raises(ValidationError):
        Transaction(
            date=dt.date(2026, 8, 1),
            description="NEGATIVE DEBIT",
            debit=-50.0,
            balance=500.0,
        )


def test_parse_row_tokens_error_handling():
    """Verify explicit error raised on malformed token rows."""
    with pytest.raises(TransactionParsingError) as exc_info:
        parse_row_tokens(["01 Aug 2026", "TXN001"])  # Insufficient tokens
    assert "Insufficient tokens" in str(exc_info.value)

    with pytest.raises(TransactionParsingError) as exc_info:
        parse_row_tokens(["INVALID_DATE", "TXN001", "DESC", "100.00", "—", "500.00"])
    assert "Invalid transaction date" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Integration Tests with Synthetic PDF Statements
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not (STATEMENTS_DIR / "normal_statement.pdf").exists(),
    reason="Synthetic statements directory not available",
)
def test_parse_normal_statement():
    """Verify parsing normal_statement.pdf."""
    doc = extract_pdf_text(STATEMENTS_DIR / "normal_statement.pdf")
    stmt = parse_transactions(doc)

    assert isinstance(stmt, TransactionStatement)
    assert stmt.customer_name == "Arjun Mehta"
    assert stmt.account_number == "XXXXXX4821"
    assert "01 Aug 2026" in (stmt.statement_period or "")
    assert stmt.total_transactions == 14

    # Verify first transaction
    t0 = stmt.transactions[0]
    assert t0.transaction_id == "TXN001"
    assert t0.date == dt.date(2026, 8, 1)
    assert t0.description == "SALARY CREDIT - ACME TECH"
    assert t0.debit is None
    assert t0.credit == 75000.0
    assert t0.balance == 165000.0
    assert t0.counterparty == "ACME TECH"

    # Verify second transaction (debit)
    t1 = stmt.transactions[1]
    assert t1.transaction_id == "TXN002"
    assert t1.date == dt.date(2026, 8, 2)
    assert t1.description == "RENT - UPI"
    assert t1.debit == 18000.0
    assert t1.credit is None
    assert t1.balance == 147000.0
    assert t1.counterparty == "RENT"

    # Verify last transaction
    t_last = stmt.transactions[-1]
    assert t_last.transaction_id == "TXN014"
    assert t_last.date == dt.date(2026, 8, 30)
    assert t_last.debit == 799.0
    assert t_last.credit is None
    assert t_last.balance == 134302.0


@pytest.mark.skipif(
    not (STATEMENTS_DIR / "suspicious_statement.pdf").exists(),
    reason="Synthetic statements directory not available",
)
def test_parse_suspicious_statement():
    """Verify parsing suspicious_statement.pdf preserving all transaction balances."""
    doc = extract_pdf_text(STATEMENTS_DIR / "suspicious_statement.pdf")
    stmt = parse_transactions(doc)

    assert stmt.total_transactions == 15
    assert stmt.customer_name == "Arjun Mehta"

    # Check high value transaction
    t4 = stmt.transactions[4]  # TXN005
    assert t4.transaction_id == "TXN005"
    assert t4.description == "NEFT - ORION TRADING"
    assert t4.credit == 480000.0
    assert t4.balance == 698800.0
    assert t4.counterparty == "ORION TRADING"

    # Verify transaction with negative balance is preserved as-is
    t6 = stmt.transactions[6]  # TXN007
    assert t6.transaction_id == "TXN007"
    assert t6.debit == 440000.0
    assert t6.balance == -206200.0


@pytest.mark.skipif(
    not (STATEMENTS_DIR / "mixed_statement.pdf").exists(),
    reason="Synthetic statements directory not available",
)
def test_parse_mixed_statement():
    """Verify parsing mixed_statement.pdf."""
    doc = extract_pdf_text(STATEMENTS_DIR / "mixed_statement.pdf")
    stmt = parse_transactions(doc)

    assert stmt.total_transactions == 14
    assert stmt.customer_name == "Arjun Mehta"
    assert stmt.transactions[6].transaction_id == "TXN007"
    assert stmt.transactions[6].counterparty == "NOVA EXPORTS"
    assert stmt.transactions[6].credit == 320000.0


def test_parse_independent_suspicious_statement():
    """Verify PDF ingestion and deterministic parsing for the newly generated independent statement."""
    pdf_path = STATEMENTS_DIR / "independent_suspicious_statement.pdf"
    if not pdf_path.exists():
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from scripts.generate_independent_statement import generate_independent_suspicious_statement
        generate_independent_suspicious_statement(pdf_path)

    assert pdf_path.exists()

    # 1. Ingestion via PyMuPDF
    doc = extract_pdf_text(pdf_path)
    assert doc.total_pages == 1
    assert not doc.pages[0].is_empty

    # Verify line token extraction contains at least 4 tokens per row
    all_lines = [line.strip() for line in doc.pages[0].text.splitlines() if line.strip()]
    date_indices = [idx for idx, line in enumerate(all_lines) if parse_date(line) is not None]
    assert len(date_indices) == 22, f"Expected 22 dates, found {len(date_indices)}"

    for i in range(len(date_indices)):
        start_idx = date_indices[i]
        end_idx = date_indices[i + 1] if i + 1 < len(date_indices) else len(all_lines)
        row_tokens = [t for t in all_lines[start_idx:end_idx] if not t.lower().startswith("dataset note:")]
        assert len(row_tokens) >= 4, f"Row {i+1} has fewer than 4 tokens: {row_tokens}"
        assert len(row_tokens) == 6, f"Row {i+1} expected 6 tokens (Date, TxnID, Desc, Debit, Credit, Balance): {row_tokens}"

    # 2. Transaction parsing and validation
    stmt = parse_transactions(doc)
    assert isinstance(stmt, TransactionStatement)
    assert stmt.customer_name == "Vikramaditya Singhania"
    assert stmt.account_number == "SYNTH-ACC-882194"
    assert "01 Jul 2026" in (stmt.statement_period or "")
    assert stmt.total_transactions == 22

    # Verify first transaction (Credit)
    t0 = stmt.transactions[0]
    assert t0.transaction_id == "TXN101"
    assert t0.date == dt.date(2026, 7, 1)
    assert t0.description == "SALARY CREDIT - NEXUS TECH LABS"
    assert t0.debit is None
    assert t0.credit == 110000.0
    assert t0.balance == 195000.0
    assert t0.counterparty == "NEXUS TECH LABS"

    # Verify second transaction (Debit)
    t1 = stmt.transactions[1]
    assert t1.transaction_id == "TXN102"
    assert t1.date == dt.date(2026, 7, 2)
    assert t1.description == "RENT - UPI"
    assert t1.debit == 28000.0
    assert t1.credit is None
    assert t1.balance == 167000.0
    assert t1.counterparty == "RENT"

    # Verify large credit transaction
    t4 = stmt.transactions[4]  # TXN105
    assert t4.transaction_id == "TXN105"
    assert t4.date == dt.date(2026, 7, 7)
    assert t4.credit == 520000.0
    assert t4.balance == 679450.0
    assert t4.counterparty == "APEX OVERSEAS LOGISTICS"

    # Verify conduit pass-through debit transaction
    t7 = stmt.transactions[7]  # TXN108
    assert t7.transaction_id == "TXN108"
    assert t7.date == dt.date(2026, 7, 9)
    assert t7.debit == 510000.0
    assert t7.balance == 1299450.0
    assert t7.counterparty == "KAVITA CONSULTING SERVICES"

    # Verify structured payment transaction
    t13 = stmt.transactions[13]  # TXN114
    assert t13.transaction_id == "TXN114"
    assert t13.debit == 95000.0
    assert t13.counterparty == "NEW COUNTERPARTY A1"

    # Verify last transaction
    t_last = stmt.transactions[-1]
    assert t_last.transaction_id == "TXN122"
    assert t_last.date == dt.date(2026, 7, 28)
    assert t_last.credit == 820.0
    assert t_last.balance == 220150.0

    # Verify all transactions have valid invariants
    for txn in stmt.transactions:
        assert (txn.debit is not None and txn.credit is None) or (txn.debit is None and txn.credit is not None)
        assert txn.balance > 0
        assert txn.date.year == 2026 and txn.date.month == 7


def test_parse_amount_with_ocr_artifacts():
    """Verify parse_amount handles OCR glyph artifacts and strictly rejects identifiers."""
    assert parse_amount("I96,500.00") == 96500.0
    assert parse_amount("l45,000.00") == 45000.0
    assert parse_amount("|12,500.00") == 12500.0
    assert parse_amount("TXN1028", allow_none=True) is None
    assert parse_amount("REF-20261027", allow_none=True) is None
    assert parse_amount("Page 2", allow_none=True) is None
    with pytest.raises(ValueError):
        parse_amount("TXN1028", allow_none=False)


def test_parse_multi_page_flow_layout_statement():
    """Verify multi-page Flow-based statement parsing handles page breaks and headers seamlessly."""
    page1_text = """
AML Investigation Copilot — Synthetic Stress Statement V2
Customer Name: Arjun Malhotra
Account Number: ACC-998877
Statement Period: 01 Jun 2026 - 30 Jun 2026
Transaction ID
Date
Flow
Amount (INR)
Counterparty
Description
Reference
TXN1027
2026-06-22
DEBIT
I96,500.00
COUNTERPARTY BURST 4
Repeated transfer
REF-20261027
"""
    page2_text = """
AML Investigation Copilot — Synthetic Stress Statement V2
Page 2
Transaction ID
Date
Flow
Amount (INR)
Counterparty
Description
Reference
TXN1028
2026-06-23
CREDIT
150,000.00
ALPHA TRADERS
Contract invoice
REF-20261028
"""
    extraction = PDFDocumentExtraction(
        file_path="dummy.pdf",
        file_name="dummy.pdf",
        total_pages=2,
        pages=[
            PDFPage(page_number=1, text=page1_text, is_empty=False),
            PDFPage(page_number=2, text=page2_text, is_empty=False),
        ],
    )

    stmt = parse_transactions(extraction)
    assert len(stmt.transactions) == 2
    assert stmt.customer_name == "Arjun Malhotra"
    assert stmt.account_number == "ACC-998877"

    t0 = stmt.transactions[0]
    assert t0.transaction_id == "TXN1027"
    assert t0.date == dt.date(2026, 6, 22)
    assert t0.debit == 96500.0
    assert t0.credit is None
    assert t0.counterparty == "COUNTERPARTY BURST 4"
    assert "Repeated transfer" in t0.description

    t1 = stmt.transactions[1]
    assert t1.transaction_id == "TXN1028"
    assert t1.date == dt.date(2026, 6, 23)
    assert t1.credit == 150000.0
    assert t1.debit is None
    assert t1.counterparty == "ALPHA TRADERS"
    assert "Contract invoice" in t1.description
