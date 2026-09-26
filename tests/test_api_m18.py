"""Integration tests for M18 real-time asynchronous endpoints and SSE streaming."""

from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from aml_copilot.agents.models import CritiqueResult
from aml_copilot.agents.state import InvestigationResult
from aml_copilot.api.main import create_app
from aml_copilot.events.bus import get_event_manager
from aml_copilot.events.models import EventType, InvestigationEvent


@pytest.fixture
def client():
    app = create_app()
    get_event_manager().clear()
    return TestClient(app)


def test_start_investigation_validation_errors(client):
    """Verify POST /investigations rejects non-PDF, empty PDF, and missing questions."""
    # 1. Non-pdf file
    res = client.post(
        "/investigations",
        files={"file": ("statement.txt", b"plain text", "text/plain")},
        data={"question": "Analyze statement."},
    )
    assert res.status_code == 400
    assert "not a PDF" in res.json()["detail"]

    # 2. Empty file
    res = client.post(
        "/investigations",
        files={"file": ("statement.pdf", b"", "application/pdf")},
        data={"question": "Analyze statement."},
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"]

    # 3. Missing question
    res = client.post(
        "/investigations",
        files={"file": ("statement.pdf", b"%PDF-1.4...", "application/pdf")},
        data={"question": "   "},
    )
    assert res.status_code == 400
    assert "question cannot be empty" in res.json()["detail"]


def test_investigation_not_found(client):
    """Verify 404 response for non-existent investigation ID."""
    res = client.get("/investigations/INV-NONEXISTENT")
    assert res.status_code == 404

    res_events = client.get("/investigations/INV-NONEXISTENT/events")
    assert res_events.status_code == 404


def test_demo_async_investigation_and_sse_streaming(client):
    """Verify POST /investigations/demo queues demo and streams events via SSE."""
    start_res = client.post("/investigations/demo")
    assert start_res.status_code == 200
    data = start_res.json()
    assert "investigation_id" in data
    assert data["status"] == "QUEUED"
    inv_id = data["investigation_id"]

    # Connect to SSE endpoint with stream=True
    with client.stream("GET", f"/investigations/{inv_id}/events") as sse_res:
        assert sse_res.status_code == 200
        assert "text/event-stream" in sse_res.headers["content-type"]

        lines = []
        for line in sse_res.iter_lines():
            if line:
                lines.append(line)
            if "INVESTIGATION_COMPLETED" in line:
                break

    # Verify structured events were streamed
    event_lines = [line for line in lines if line.startswith("data:")]
    assert len(event_lines) > 0
    assert any("INVESTIGATION_STARTED" in line for line in event_lines)
    assert any("CRITIC_PASSED" in line for line in event_lines)
    assert any("INVESTIGATION_COMPLETED" in line for line in event_lines)

    # Query status endpoint
    status_res = client.get(f"/investigations/{inv_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["status"] == "COMPLETED"
    assert status_data["report"] is not None
    assert status_data["report"]["report_id"].startswith("REP-")


def test_start_investigation_mocked_e2e_streaming(client):
    """Verify POST /investigations with valid PDF and mocked LLM streams real events."""
    sample_pdf = Path("data/statements/suspicious_statement.pdf")
    if not sample_pdf.exists():
        pytest.skip("Sample statement PDF not found")

    pdf_bytes = sample_pdf.read_bytes()

    mock_result = InvestigationResult(
        question="Investigate unusual funds.",
        response="Observed Evidence: TXN005 was a ₹480,000 credit.",
        tools_used=["get_transaction_statistics"],
        tool_calls=[],
        referenced_transaction_ids=["TXN005"],
        knowledge_sources=[],
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
        limitations_warnings=["Review required."],
    )

    with patch("aml_copilot.api.routes.run_investigation") as mock_run:
        def side_effect(*args, **kwargs):
            cb = kwargs.get("event_callback")
            inv_id = kwargs.get("investigation_id", "INV-MOCK")
            if cb:
                cb(
                    InvestigationEvent(
                        investigation_id=inv_id,
                        event_type=EventType.INVESTIGATION_STARTED,
                        message="Starting mock investigation.",
                    )
                )
                cb(
                    InvestigationEvent(
                        investigation_id=inv_id,
                        event_type=EventType.NODE_STARTED,
                        node="investigator",
                        message="Mock investigator running.",
                    )
                )
                cb(
                    InvestigationEvent(
                        investigation_id=inv_id,
                        event_type=EventType.CRITIC_PASSED,
                        node="critic",
                        message="Critic audit passed.",
                    )
                )
                cb(
                    InvestigationEvent(
                        investigation_id=inv_id,
                        event_type=EventType.INVESTIGATION_COMPLETED,
                        message="Mock investigation completed.",
                    )
                )
            return mock_result

        mock_run.side_effect = side_effect

        start_res = client.post(
            "/investigations",
            files={"file": ("suspicious_statement.pdf", pdf_bytes, "application/pdf")},
            data={"question": "Investigate unusual funds."},
        )
        assert start_res.status_code == 200
        inv_id = start_res.json()["investigation_id"]

        with client.stream("GET", f"/investigations/{inv_id}/events") as sse_res:
            assert sse_res.status_code == 200
            lines = []
            for line in sse_res.iter_lines():
                if line:
                    lines.append(line)
                if "INVESTIGATION_COMPLETED" in line:
                    break

        event_lines = [line for line in lines if line.startswith("data:")]
        assert any("INVESTIGATION_STARTED" in line for line in event_lines)
        assert any("CRITIC_PASSED" in line for line in event_lines)
        assert any("INVESTIGATION_COMPLETED" in line for line in event_lines)

        # Verify completed status
        status_res = client.get(f"/investigations/{inv_id}")
        assert status_res.status_code == 200
        assert status_res.json()["status"] == "COMPLETED"
        assert status_res.json()["report"] is not None


def test_critic_failure_and_revision_events_streamed(client):
    """Verify that CRITIC_FAILED and REVISION_STARTED events stream with actual metadata."""
    sample_pdf = Path("data/statements/suspicious_statement.pdf")
    if not sample_pdf.exists():
        pytest.skip("Sample statement PDF not found")

    pdf_bytes = sample_pdf.read_bytes()

    mock_result = InvestigationResult(
        question="Investigate unusual funds.",
        response="Observed Evidence: TXN005 was a ₹480,000 credit.",
        tools_used=["get_transaction_statistics"],
        tool_calls=[],
        referenced_transaction_ids=["TXN005"],
        knowledge_sources=[],
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
        revision_count=1,
        limitations_warnings=["Review required."],
    )

    with patch("aml_copilot.api.routes.run_investigation") as mock_run:
        def side_effect(*args, **kwargs):
            cb = kwargs.get("event_callback")
            inv_id = kwargs.get("investigation_id", "INV-CRITIC-REV")
            if cb:
                cb(
                    InvestigationEvent(
                        investigation_id=inv_id,
                        event_type=EventType.CRITIC_FAILED,
                        node="critic",
                        status="FAIL",
                        message="Critic audit FAILED: 1 issue identified.",
                        metadata={"issues": ["Non-existent transaction TXN999 cited."]},
                    )
                )
                cb(
                    InvestigationEvent(
                        investigation_id=inv_id,
                        event_type=EventType.REVISION_STARTED,
                        node="revision",
                        message="Initiating revision 1...",
                        revision=1,
                    )
                )
                cb(
                    InvestigationEvent(
                        investigation_id=inv_id,
                        event_type=EventType.CRITIC_PASSED,
                        node="critic",
                        status="PASS",
                        message="Critic audit passed after revision.",
                    )
                )
                cb(
                    InvestigationEvent(
                        investigation_id=inv_id,
                        event_type=EventType.INVESTIGATION_COMPLETED,
                        message="Investigation completed.",
                    )
                )
            return mock_result

        mock_run.side_effect = side_effect

        start_res = client.post(
            "/investigations",
            files={"file": ("suspicious_statement.pdf", pdf_bytes, "application/pdf")},
            data={"question": "Investigate unusual funds."},
        )
        assert start_res.status_code == 200
        inv_id = start_res.json()["investigation_id"]

        with client.stream("GET", f"/investigations/{inv_id}/events") as sse_res:
            lines = [line for line in sse_res.iter_lines() if line]

        event_lines = [line for line in lines if line.startswith("data:")]
        assert any("CRITIC_FAILED" in line for line in event_lines)
        assert any("Non-existent transaction TXN999 cited" in line for line in event_lines)
        assert any("REVISION_STARTED" in line for line in event_lines)
        assert any("CRITIC_PASSED" in line for line in event_lines)


def test_investigation_failure_event_handling(client):
    """Verify that an exception in investigation emits INVESTIGATION_FAILED and sets status FAILED."""
    sample_pdf = Path("data/statements/suspicious_statement.pdf")
    if not sample_pdf.exists():
        pytest.skip("Sample statement PDF not found")

    pdf_bytes = sample_pdf.read_bytes()

    with patch("aml_copilot.api.routes.run_investigation") as mock_run:
        mock_run.side_effect = RuntimeError("OpenAI rate limit exceeded")

        start_res = client.post(
            "/investigations",
            files={"file": ("suspicious_statement.pdf", pdf_bytes, "application/pdf")},
            data={"question": "Investigate unusual funds."},
        )
        assert start_res.status_code == 200
        inv_id = start_res.json()["investigation_id"]

        with client.stream("GET", f"/investigations/{inv_id}/events") as sse_res:
            lines = [line for line in sse_res.iter_lines() if line]

        event_lines = [line for line in lines if line.startswith("data:")]
        assert any("INVESTIGATION_FAILED" in line for line in event_lines)
        assert any("OpenAI rate limit exceeded" in line for line in event_lines)

        status_res = client.get(f"/investigations/{inv_id}")
        assert status_res.status_code == 200
        assert status_res.json()["status"] == "FAILED"
        assert "OpenAI rate limit exceeded" in status_res.json()["error"]
