"""Unit and integration tests for AML rule engine (M6)."""

import datetime as dt
from pathlib import Path
import pytest

from aml_copilot.ml.rules import RuleConfig, RuleEngine
from aml_copilot.models.findings import SignalSeverity
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_parser import parse_transactions

STATEMENTS_DIR = Path("data/statements")


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_rule_engine_empty_statement():
    """Verify empty statement yields zero rule signals."""
    stmt = TransactionStatement(customer_name="Test", transactions=[])
    engine = RuleEngine()
    signals = engine.evaluate(stmt)
    assert signals == []


def test_rule_engine_custom_config_thresholds():
    """Verify custom thresholds alter rule firing behavior deterministically."""
    # A single transaction of 150,000
    t = Transaction(
        date=dt.date(2026, 8, 1),
        transaction_id="TXN001",
        description="FUNDS",
        credit=150000.0,
        balance=150000.0,
    )
    stmt = TransactionStatement(customer_name="Alice", transactions=[t])

    # Default threshold is 100,000 -> should fire
    engine_default = RuleEngine()
    signals_default = engine_default.evaluate(stmt)
    assert any(s.rule_id == "RULE_LARGE_TRANSACTION" for s in signals_default)

    # High threshold 500,000 -> should not fire
    strict_config = RuleConfig(large_transaction_abs_threshold=500000.0)
    engine_strict = RuleEngine(config=strict_config)
    signals_strict = engine_strict.evaluate(stmt)
    assert not any(s.rule_id == "RULE_LARGE_TRANSACTION" for s in signals_strict)


def test_no_fabricated_evidence_in_rules():
    """Verify that every transaction_id reported in a signal actually exists in the statement."""
    pdf_path = STATEMENTS_DIR / "suspicious_statement.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)
    actual_txn_ids = {t.transaction_id for t in stmt.transactions if t.transaction_id}

    engine = RuleEngine()
    signals = engine.evaluate(stmt)

    assert len(signals) > 0
    for signal in signals:
        assert len(signal.transaction_ids) > 0
        for tid in signal.transaction_ids:
            assert tid in actual_txn_ids, f"Fabricated transaction ID detected: {tid}"


# ---------------------------------------------------------------------------
# Integration tests on synthetic PDFs
# ---------------------------------------------------------------------------

def test_rules_on_normal_statement():
    """Verify normal statement produces low/benign signals without rapid pass-through or sudden spikes."""
    pdf_path = STATEMENTS_DIR / "normal_statement.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)

    engine = RuleEngine()
    signals = engine.evaluate(stmt)

    rule_ids = [s.rule_id for s in signals]
    # In a normal retail account, there should be NO large inflow rapid outflow or sudden volume surges
    assert "RULE_LARGE_INFLOW_RAPID_OUTFLOW" not in rule_ids
    assert "RULE_SUDDEN_VOLUME_INCREASE" not in rule_ids
    assert "RULE_RAPID_MOVEMENT_OF_FUNDS" not in rule_ids


def test_rules_on_suspicious_statement():
    """Verify suspicious statement triggers expected AML pattern rules."""
    pdf_path = STATEMENTS_DIR / "suspicious_statement.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)

    engine = RuleEngine()
    signals = engine.evaluate(stmt)

    rule_ids = {s.rule_id for s in signals}

    # Should detect large transactions, volume increase, rapid pass-through, and rapid fund movement
    assert "RULE_LARGE_TRANSACTION" in rule_ids
    assert "RULE_SUDDEN_VOLUME_INCREASE" in rule_ids
    assert "RULE_LARGE_INFLOW_RAPID_OUTFLOW" in rule_ids
    assert "RULE_RAPID_MOVEMENT_OF_FUNDS" in rule_ids
    assert "RULE_MANY_NEW_COUNTERPARTIES" in rule_ids

    # Verify pass-through flags high severity
    pass_through_signals = [s for s in signals if s.rule_id == "RULE_LARGE_INFLOW_RAPID_OUTFLOW"]
    assert len(pass_through_signals) >= 1
    assert any(s.severity == SignalSeverity.HIGH for s in pass_through_signals)


def test_rules_on_mixed_statement():
    """Verify mixed statement correctly isolates the mid-period anomalous transactions."""
    pdf_path = STATEMENTS_DIR / "mixed_statement.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)

    engine = RuleEngine()
    signals = engine.evaluate(stmt)

    rule_ids = {s.rule_id for s in signals}
    assert "RULE_LARGE_TRANSACTION" in rule_ids
    assert "RULE_SUDDEN_VOLUME_INCREASE" in rule_ids
    assert "RULE_LARGE_INFLOW_RAPID_OUTFLOW" in rule_ids

    # Check that TXN007 (320k credit) and TXN008 (305k debit) are captured in pass-through
    pt_signals = [s for s in signals if s.rule_id == "RULE_LARGE_INFLOW_RAPID_OUTFLOW"]
    assert len(pt_signals) >= 1
    pt_txns = pt_signals[0].transaction_ids
    assert "TXN007" in pt_txns
    assert "TXN008" in pt_txns
