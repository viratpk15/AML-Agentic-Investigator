"""End-to-end integration tests for the unified AML Detection Layer pipeline."""

import json
from pathlib import Path
import pytest

from aml_copilot.ml.pipeline import DetectionPipeline, run_detection
from aml_copilot.models.findings import DetectionResult
from aml_copilot.models.transaction import TransactionStatement
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_parser import parse_transactions

STATEMENTS_DIR = Path("data/statements")


# ---------------------------------------------------------------------------
# Pipeline Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "pdf_filename, min_expected_rule_signals",
    [
        ("normal_statement.pdf", 0),
        ("suspicious_statement.pdf", 5),
        ("mixed_statement.pdf", 3),
    ],
)
def test_full_detection_pipeline_synthetic_pdfs(pdf_filename: str, min_expected_rule_signals: int):
    """Verify end-to-end pipeline run on all three synthetic statements."""
    pdf_path = STATEMENTS_DIR / pdf_filename
    if not pdf_path.exists():
        pytest.skip(f"PDF {pdf_filename} not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)

    result = run_detection(stmt)

    assert isinstance(result, DetectionResult)
    assert result.statement_metadata["customer_name"] == stmt.customer_name
    assert result.total_rule_signals >= min_expected_rule_signals
    assert len(result.anomaly_signals) == stmt.total_transactions

    # Verify disclaimer and warnings present
    assert any("investigation leads" in w.lower() or "screening flags" in w.lower() for w in result.limitations_warnings)


def test_detection_result_json_serialization():
    """Verify DetectionResult models can be safely serialized to and deserialized from JSON."""
    pdf_path = STATEMENTS_DIR / "mixed_statement.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)
    result = run_detection(stmt)

    # Serialize to JSON string
    json_str = result.model_dump_json(indent=2)
    assert isinstance(json_str, str)

    # Validate JSON structure
    parsed_json = json.loads(json_str)
    assert "statement_metadata" in parsed_json
    assert "feature_summary" in parsed_json
    assert "rule_signals" in parsed_json
    assert "anomaly_signals" in parsed_json
    assert "metadata" in parsed_json
    assert "limitations_warnings" in parsed_json

    # Deserialize back to DetectionResult
    restored_result = DetectionResult.model_validate_json(json_str)
    assert restored_result.total_rule_signals == result.total_rule_signals
    assert restored_result.total_anomaly_signals == result.total_anomaly_signals
    assert restored_result.statement_metadata == result.statement_metadata


def test_no_fabricated_transaction_ids_in_detection_result():
    """Verify all transaction IDs in rule and anomaly signals strictly come from the statement."""
    pdf_path = STATEMENTS_DIR / "suspicious_statement.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)
    actual_ids = {t.transaction_id for t in stmt.transactions if t.transaction_id}

    result = run_detection(stmt)

    # Check rule signal transaction IDs
    for rule_sig in result.rule_signals:
        for tid in rule_sig.transaction_ids:
            assert tid in actual_ids, f"Fabricated rule transaction ID: {tid}"

    # Check anomaly signal transaction IDs
    for anom_sig in result.anomaly_signals:
        assert anom_sig.transaction_id in actual_ids, f"Fabricated anomaly transaction ID: {anom_sig.transaction_id}"


def test_detection_pipeline_small_empty_statement():
    """Verify pipeline handles empty statement gracefully without exceptions."""
    stmt = TransactionStatement(customer_name="Blank", transactions=[])
    pipeline = DetectionPipeline()
    result = pipeline.run(stmt)

    assert result.total_rule_signals == 0
    assert result.total_anomaly_signals == 0
    assert len(result.limitations_warnings) >= 1
    assert any("sample" in w.lower() or "insufficient" in w.lower() for w in result.limitations_warnings)


def test_no_guilt_score_in_detection_models():
    """Verify that models and outputs do NOT convey guilt or fraud scores."""
    pdf_path = STATEMENTS_DIR / "suspicious_statement.pdf"
    if not pdf_path.exists():
        pytest.skip("PDF not found")

    doc = extract_pdf_text(pdf_path)
    stmt = parse_transactions(doc)
    result = run_detection(stmt)

    # Validate that neither DetectionResult nor its fields have 'guilt' or 'fraud' keys
    dump = result.model_dump()
    assert "guilt" not in dump
    assert "fraud_score" not in dump
    assert "guilt_score" not in dump

    # Check explanations do not allege illegal conduct
    for r in result.rule_signals:
        lower_exp = r.explanation.lower()
        assert "illegal" not in lower_exp
        assert "guilty" not in lower_exp
        assert "criminal" not in lower_exp
