"""Unit and integration tests for AML detection tools."""

from pathlib import Path
import pytest

from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_parser import parse_transactions
from aml_copilot.tools.detection_tools import (
    DetectAnomaliesInput,
    DetectAnomaliesOutput,
    create_detect_anomalies_tool,
    execute_detect_anomalies,
)

STATEMENTS_DIR = Path("data/statements")


def test_execute_detect_anomalies_suspicious_statement():
    """Verify detect_anomalies calls the M5-M7 detection pipeline and preserves evidence."""
    pdf_path = STATEMENTS_DIR / "suspicious_statement.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)

    out = execute_detect_anomalies(stmt)

    assert isinstance(out, DetectAnomaliesOutput)
    assert out.customer_name == "Arjun Mehta"
    assert out.total_rule_signals > 0
    assert out.total_anomaly_signals > 0
    assert len(out.flagged_transaction_ids) > 0

    # Verify that suspicious high-value IDs are included in flagged IDs
    assert "TXN005" in out.flagged_transaction_ids
    assert "TXN008" in out.flagged_transaction_ids

    # Verify rule signals preserve details
    rule_ids = {r.rule_id for r in out.rule_signals}
    assert "RULE_LARGE_TRANSACTION" in rule_ids
    assert "RULE_LARGE_INFLOW_RAPID_OUTFLOW" in rule_ids

    # Verify limitations and compliance warnings
    assert len(out.limitations_warnings) > 0
    assert any("not constitute a finding of guilt" in w.lower() for w in out.limitations_warnings)


def test_detect_anomalies_severity_filter():
    """Verify filtering detection signals by minimum severity."""
    pdf_path = STATEMENTS_DIR / "suspicious_statement.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)

    # All signals
    out_all = execute_detect_anomalies(stmt, DetectAnomaliesInput())

    # Only HIGH severity
    out_high = execute_detect_anomalies(stmt, DetectAnomaliesInput(min_severity="HIGH"))

    assert out_high.total_rule_signals <= out_all.total_rule_signals
    assert all(r.severity == "HIGH" for r in out_high.rule_signals)


def test_detect_anomalies_langchain_tool():
    """Verify LangChain detect_anomalies tool returns serialized dictionary."""
    pdf_path = STATEMENTS_DIR / "mixed_statement.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)

    tool = create_detect_anomalies_tool(stmt)
    assert tool.name == "detect_anomalies"

    output = tool.invoke({"include_anomaly_signals": True})
    assert isinstance(output, dict)
    assert output["total_rule_signals"] > 0
    assert "flagged_transaction_ids" in output
    assert "TXN007" in output["flagged_transaction_ids"]
