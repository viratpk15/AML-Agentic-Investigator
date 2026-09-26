"""Unit and integration tests for FastAPI backend endpoints."""

from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from aml_copilot.agents.models import CritiqueResult
from aml_copilot.agents.state import InvestigationResult
from aml_copilot.api.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify GET and HEAD on / and /api return 200 OK with API status and links."""
    for path in ["/", "/api"]:
        get_res = client.get(path)
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["service"] == "AML Investigation Copilot API"
        assert data["status"] == "online"
        assert "docs_url" in data

        head_res = client.head(path)
        assert head_res.status_code == 200

    favicon_res = client.get("/favicon.ico")
    assert favicon_res.status_code == 204


def test_health_check_endpoint():
    """Verify GET /health and GET /api/health return operational status."""
    for path in ["/health", "/api/health"]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "aml-copilot"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data


def test_investigate_non_pdf_file_rejected():
    """Verify uploading a non-PDF file returns HTTP 400 Bad Request."""
    file_content = b"This is plain text, not a PDF."
    response = client.post(
        "/investigate",
        files={"file": ("statement.txt", file_content, "text/plain")},
        data={"question": "Investigate transactions"},
    )
    assert response.status_code == 400
    assert "not a PDF" in response.json()["detail"]


def test_investigate_empty_file_rejected():
    """Verify uploading an empty file returns HTTP 400 Bad Request."""
    response = client.post(
        "/investigate",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        data={"question": "Investigate transactions"},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_investigate_missing_question_rejected():
    """Verify missing question returns HTTP 400 Bad Request."""
    file_content = b"%PDF-1.4 sample fake bytes"
    response = client.post(
        "/investigate",
        files={"file": ("statement.pdf", file_content, "application/pdf")},
        data={"question": "   "},
    )
    assert response.status_code == 400
    assert "question cannot be empty" in response.json()["detail"]


def test_demo_endpoint_returns_structured_report():
    """Verify GET /demo returns a complete, structured investigation report."""
    response = client.get("/demo")
    assert response.status_code == 200
    data = response.json()

    assert "report" in data
    assert "markdown" in data
    assert "execution_time_seconds" in data

    report = data["report"]
    assert report["customer_name"] in ["Arjun Malhotra", "Arjun Mehta"]
    assert report["report_id"].startswith("REP-AML-")
    assert len(report["observed_evidence"]) >= 2
    assert report["critic_validation"]["passed"] is True
    assert "# AML Investigation Report" in data["markdown"]


def test_investigate_endpoint_end_to_end_with_mock_agent(tmp_path):
    """Verify POST /investigate with valid PDF and mocked agent execution."""
    sample_pdf_path = Path("data/statements/suspicious_statement.pdf")
    if not sample_pdf_path.exists():
        pytest.skip("Sample statement PDF not found")

    pdf_bytes = sample_pdf_path.read_bytes()

    mock_investigation = InvestigationResult(
        question="Investigate TXN005.",
        response="Observed Evidence: TXN005 is a ₹480,000 credit from ORION TRADING.",
        tools_used=["search_transactions"],
        tool_calls=[],
        referenced_transaction_ids=["TXN005"],
        knowledge_sources=["aml_red_flags.md"],
        critic_result=CritiqueResult(
            passed=True,
            issues=[],
            missing_evidence=[],
            unsupported_claims=[],
            required_revisions=[],
            checked_transaction_ids=["TXN005"],
            invalid_transaction_ids=[],
            safety_violations=[],
        ),
        critic_status="PASS",
        revision_count=0,
        limitations_warnings=["Mock investigation warning."],
    )

    with patch("aml_copilot.api.routes.run_investigation", return_value=mock_investigation):
        response = client.post(
            "/investigate",
            files={"file": ("suspicious_statement.pdf", pdf_bytes, "application/pdf")},
            data={"question": "Investigate TXN005."},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["report"]["customer_name"] == "Arjun Mehta"
    assert data["report"]["critic_validation"]["status"] == "PASS"
    assert any(e["transaction_id"] == "TXN005" for e in data["report"]["observed_evidence"])
    assert "# AML Investigation Report" in data["markdown"]


def test_investigate_endpoint_with_independent_statement():
    """Verify POST /investigate successfully processes the newly generated independent statement."""
    pdf_path = Path("data/statements/independent_suspicious_statement.pdf")
    if not pdf_path.exists():
        pytest.skip("Independent statement PDF not found")

    pdf_bytes = pdf_path.read_bytes()

    mock_investigation = InvestigationResult(
        question="Investigate high-value rapid fund movement.",
        response="Observed Evidence: TXN105 credit 520,000 INR from APEX OVERSEAS LOGISTICS, followed by TXN108 debit 510,000 INR to KAVITA CONSULTING SERVICES.",
        tools_used=["search_transactions", "detect_anomalies"],
        tool_calls=[],
        referenced_transaction_ids=["TXN105", "TXN108"],
        knowledge_sources=["aml_red_flags.md"],
        critic_result=CritiqueResult(
            passed=True,
            issues=[],
            missing_evidence=[],
            unsupported_claims=[],
            required_revisions=[],
            checked_transaction_ids=["TXN105", "TXN108"],
            invalid_transaction_ids=[],
            safety_violations=[],
        ),
        critic_status="PASS",
        revision_count=0,
        limitations_warnings=["Fictional synthetic investigation statement."],
    )

    with patch("aml_copilot.api.routes.run_investigation", return_value=mock_investigation):
        response = client.post(
            "/investigate",
            files={"file": ("independent_suspicious_statement.pdf", pdf_bytes, "application/pdf")},
            data={"question": "Investigate high-value rapid fund movement."},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["report"]["customer_name"] == "Vikramaditya Singhania"
    assert data["report"]["account_number"] == "SYNTH-ACC-882194"
    assert data["report"]["critic_validation"]["status"] == "PASS"
    assert any(e["transaction_id"] == "TXN105" for e in data["report"]["observed_evidence"])
    assert "# AML Investigation Report" in data["markdown"]


def test_get_demo_endpoint():
    """Verify GET /demo returns a complete demonstration report."""
    response = client.get("/demo")
    assert response.status_code == 200
    data = response.json()
    assert "report" in data
    assert "markdown" in data
    assert data["report"]["total_transactions_analyzed"] == 54
    assert len(data["report"]["observed_evidence"]) == 54


def test_history_and_download_endpoints():
    """Verify history listing, report retrieval, and download endpoints."""
    # First call demo to ensure we have a report structure
    demo_res = client.get("/demo")
    assert demo_res.status_code == 200
    demo_data = demo_res.json()
    report_dict = demo_data["report"]
    report_id = report_dict["report_id"]

    # Test history listing
    hist_res = client.get("/history")
    assert hist_res.status_code == 200
    assert isinstance(hist_res.json(), list)

    # Test dossier for a known transaction (TXN401)
    _ = client.get(f"/investigations/{report_id}/transactions/TXN401")
    # If not saved yet in history, test saving then fetching
    from aml_copilot.services.history import get_history_service
    from aml_copilot.reporting.models import InvestigationReport

    history_svc = get_history_service()
    report_obj = InvestigationReport(**report_dict)
    history_svc.save_run(
        investigation_id=report_id,
        report=report_obj,
        markdown_text=demo_data["markdown"],
        status="COMPLETED",
    )

    # Test history item retrieval
    item_res = client.get(f"/history/{report_id}")
    assert item_res.status_code == 200
    assert item_res.json()["report"]["report_id"] == report_id

    # Test transaction evidence dossier
    dossier_res2 = client.get(f"/investigations/{report_id}/transactions/TXN401")
    assert dossier_res2.status_code == 200
    assert dossier_res2.json()["transaction_id"] == "TXN401"
    assert dossier_res2.json()["verified_in_statement"] is True

    # Test Markdown download
    md_res = client.get(f"/investigations/{report_id}/download/markdown")
    assert md_res.status_code == 200
    assert "text/markdown" in md_res.headers["content-type"]
    assert "# AML Investigation Report" in md_res.text

    # Test JSON download
    json_res = client.get(f"/investigations/{report_id}/download/json")
    assert json_res.status_code == 200
    assert "application/json" in json_res.headers["content-type"]
    assert json_res.json()["report_id"] == report_id

