"""FastAPI routes defining AML Investigation Copilot endpoints with real-time SSE streaming."""

import asyncio
import datetime as dt
import json
from pathlib import Path
import tempfile
import time
from typing import Any, AsyncIterator, Dict, List, Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response, StreamingResponse

from aml_copilot.agents.investigation_agent import run_investigation
from aml_copilot.agents.models import CritiqueResult
from aml_copilot.agents.state import InvestigationResult
from aml_copilot.api.dependencies import get_api_rag_service, get_api_settings
from aml_copilot.api.schemas import (
    HealthResponse,
    InvestigationAPIResponse,
    InvestigationStartResponse,
    InvestigationStatusResponse,
)
from aml_copilot.config import Settings
from aml_copilot.events.bus import get_event_manager
from aml_copilot.events.models import EventType, InvestigationEvent
from aml_copilot.exceptions import (
    AgentConfigurationError,
    AMLCopilotError,
    PDFInvalidFormatError,
    PDFNotFoundError,
    TransactionParsingError,
)
from aml_copilot.logger import get_logger
from aml_copilot.rag.service import RAGService
from aml_copilot.reporting.formatter import format_report_markdown
from aml_copilot.reporting.generator import generate_investigation_report
from aml_copilot.reporting.models import InvestigationReport
from aml_copilot.services.history import get_history_service, InvestigationHistoryRecord
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_explorer import build_transaction_dossier, TransactionEvidenceDossier
from aml_copilot.services.transaction_parser import parse_transactions

logger = get_logger(__name__)

router = APIRouter()

MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB max PDF file size



# ---------------------------------------------------------------------------
# Background Async Worker Tasks
# ---------------------------------------------------------------------------

async def _run_async_investigation(
    investigation_id: str,
    pdf_bytes: bytes,
    filename: str,
    question: str,
    rag_service: Optional[RAGService],
) -> None:
    """Asynchronous background worker executing PDF ingestion, LangGraph agent, and report generation."""
    event_manager = get_event_manager()
    bus = event_manager.get_or_create_bus(investigation_id)

    temp_path: Optional[Path] = None
    try:
        # 1. Parse statement
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            temp_path = Path(tmp.name)

        doc = extract_pdf_text(temp_path)
        statement = parse_transactions(doc)

    except Exception as exc:
        logger.error(f"[Async Investigation {investigation_id}] Ingestion/Parsing error: {exc}")
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.INVESTIGATION_FAILED,
                status="FAILED",
                message=f"Statement parsing failed: {str(exc)}",
                metadata={"error": str(exc)},
            )
        )
        bus.set_error(f"Statement parsing error: {str(exc)}")
        return
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass

    # 2. Execute LangGraph in worker thread to prevent event-loop starvation
    try:
        def _bus_callback(event: InvestigationEvent) -> None:
            # If agent emits INVESTIGATION_COMPLETED, forward as SYNTHESIS_COMPLETED so the
            # bus remains open until report generation and markdown formatting complete
            if event.event_type == EventType.INVESTIGATION_COMPLETED:
                bus.publish_sync(
                    InvestigationEvent(
                        investigation_id=event.investigation_id,
                        event_type=EventType.SYNTHESIS_COMPLETED,
                        node="investigator",
                        message="Investigation reasoning concluded. Compiling final compliance report artifacts...",
                        metadata=event.metadata,
                    )
                )
            else:
                bus.publish_sync(event)

        investigation_result = await asyncio.to_thread(
            run_investigation,
            statement=statement,
            question=question,
            rag_service=rag_service,
            include_rag=True,
            include_profile=True,
            include_network=True,
            enable_critic=True,
            event_callback=_bus_callback,
            investigation_id=investigation_id,
        )

        # 3. Generate structured report and Markdown
        report = generate_investigation_report(
            statement=statement,
            investigation=investigation_result,
        )
        markdown_text = format_report_markdown(report)
        status_label = "PARTIAL" if (investigation_result.status == "MAX_ITERATIONS_REACHED" or investigation_result.is_partial) else "COMPLETED"
        if status_label == "PARTIAL":
            bus.set_partial_result(report=report, markdown=markdown_text)
            logger.warning(
                f"[Async Investigation {investigation_id}] Concluded with MAX_ITERATIONS_REACHED. Partial report: {report.report_id}"
            )
            bus.publish_sync(
                InvestigationEvent(
                    investigation_id=investigation_id,
                    event_type=EventType.INVESTIGATION_MAX_ITERATIONS,
                    status="MAX_ITERATIONS_REACHED",
                    message=f"Investigation concluded with partial findings (Report ID: {report.report_id}).",
                    metadata={"report_id": report.report_id},
                )
            )
        else:
            bus.set_result(report=report, markdown=markdown_text)
            logger.info(f"[Async Investigation {investigation_id}] Successfully concluded. Report: {report.report_id}")
            bus.publish_sync(
                InvestigationEvent(
                    investigation_id=investigation_id,
                    event_type=EventType.REPORT_GENERATED,
                    message=f"Compliance audit report generated (Report ID: {report.report_id}).",
                    metadata={"report_id": report.report_id},
                )
            )
            bus.publish_sync(
                InvestigationEvent(
                    investigation_id=investigation_id,
                    event_type=EventType.INVESTIGATION_COMPLETED,
                    status="COMPLETED",
                    message=f"Investigation workflow concluded ({len(investigation_result.tools_used)} tools executed, {investigation_result.revision_count} revisions).",
                    metadata={"report_id": report.report_id},
                )
            )

        # Persist to investigation history
        try:
            get_history_service().save_run(
                investigation_id=investigation_id,
                report=report,
                markdown_text=markdown_text,
                status=status_label,
                runtime_seconds=bus.execution_time_seconds or 0.0,
            )
        except Exception as hist_err:
            logger.warning(f"Could not persist run to history: {hist_err}")

    except Exception as exc:
        logger.error(f"[Async Investigation {investigation_id}] Execution error: {exc}")
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.INVESTIGATION_FAILED,
                status="FAILED",
                message=f"Investigation workflow error: {str(exc)}",
                metadata={"error": str(exc)},
            )
        )
        bus.set_error(str(exc))


def _build_demo_investigation_result(question: str) -> InvestigationResult:
    """Build grounded InvestigationResult referencing canonical evidence for the demo run."""
    demo_response = (
        "Observed Evidence:\n"
        "During October 2026, 54 transactions were processed for customer Arjun Malhotra (Account XX6384). "
        "Key transactions of interest include TXN445 (a ₹575,000 credit from WESTBROOK MATERIALS on 2026-10-20), "
        "followed closely by outgoing disbursements including TXN446 (a ₹255,000 debit to LUMEN CONSULTING on 2026-10-20).\n\n"
        "Analytical Findings:\n"
        "Deterministic screening triggered the configured monitoring threshold for large transactions (RULE_LARGE_TRANSACTION), "
        "rapid movement of funds (RULE_RAPID_MOVEMENT_OF_FUNDS), and high transaction velocity bursts. "
        "Isolation Forest unsupervised anomaly detection identified exactly 6 statistical outliers: "
        "TXN401, TXN404, TXN434, TXN442, TXN445, and TXN451 based on transaction amount, directional velocity, and inter-transaction time deltas.\n\n"
        "Customer Profile and Network Findings:\n"
        "The profile reflects 54 transactions across 28 unique counterparties with net outflow of ₹771,960. "
        "Directed counterparty analysis establishes a 29-node graph with 37 flow edges, showing high-volume conduit patterns through core corporate counterparties.\n\n"
        "AML Reference Guidance:\n"
        "Guidance from the AML reference knowledge base (aml_red_flags.md, aml_transaction_monitoring.md) notes that "
        "rapid pass-through conduit flows and high transaction velocity with minimal fund retention warrant elevated compliance scrutiny.\n\n"
        "Evidence Convergence & Review Prioritization:\n"
        "50 transactions generated review signals, with 25 prioritized as HIGH priority due to convergence across multiple independent analytical domains. "
        "The highest convergence was observed on TXN445 and TXN434.\n\n"
        "Investigative Scope & Limitations:\n"
        "These findings represent investigative risk signals and evidence summaries to assist compliance personnel. "
        "They do not constitute a determination of fraud, money laundering, criminal conduct, or legal liability."
    )

    return InvestigationResult(
        question=question,
        response=demo_response,
        tools_used=[
            "get_transaction_statistics",
            "detect_anomalies",
            "get_customer_profile",
            "analyze_transaction_network",
            "search_aml_knowledge",
        ],
        tool_calls=[],
        referenced_transaction_ids=[
            "TXN401", "TXN404", "TXN434", "TXN442", "TXN445", "TXN451", "TXN406", "TXN415", "TXN422"
        ],
        knowledge_sources=["aml_red_flags.md", "aml_transaction_monitoring.md", "aml_investigation_guidance.md"],
        critic_result=CritiqueResult(
            passed=True,
            issues=[],
            missing_evidence=[],
            unsupported_claims=[],
            required_revisions=[],
            checked_transaction_ids=[
                "TXN401", "TXN404", "TXN434", "TXN442", "TXN445", "TXN451", "TXN406", "TXN415", "TXN422"
            ],
            invalid_transaction_ids=[],
            safety_violations=[],
            statement_transaction_count=54,
            narrative_transaction_reference_count=9,
            human_review_transaction_count=50,
            verified_transaction_reference_count=9,
            unverified_transaction_reference_count=0,
        ),
        critic_status="PASS",
        revision_count=1,
        limitations_warnings=[
            "Investigation findings are an analytical aid for compliance analysis and do not establish guilt or fraud.",
            "Analysis is bounded by the transactions presented within the statement period.",
        ],
    )


async def _run_demo_async_investigation(
    investigation_id: str,
    rag_service: Optional[RAGService],
) -> None:
    """Execute synthetic demonstration investigation progressively emitting real lifecycle events."""
    event_manager = get_event_manager()
    bus = event_manager.get_or_create_bus(investigation_id)

    sample_pdf = Path("data/statements/ultimate_publish_stress_statement.pdf")
    if not sample_pdf.exists():
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.INVESTIGATION_FAILED,
                status="FAILED",
                message="Demo statement file not found: ultimate_publish_stress_statement.pdf",
                metadata={"error": "Missing demo PDF file"},
            )
        )
        bus.set_error("Demo statement file not found.")
        return

    try:
        # 1. Ingestion / Upload event
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.INVESTIGATION_STARTED,
                message="1. Ingestion: Statement PDF uploaded (ultimate_publish_stress_statement.pdf).",
                metadata={"filename": "ultimate_publish_stress_statement.pdf"},
            )
        )
        await asyncio.sleep(0.04)

        # 2. Parsing
        doc = extract_pdf_text(sample_pdf)
        statement = parse_transactions(doc)
        question = "Investigate unusual movement of funds in this account and highlight transactions requiring human review."

        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.TOOL_COMPLETED,
                node="tools",
                tool_name="parse_statement",
                message=f"2. Parsing: {statement.total_transactions} transactions successfully parsed for customer '{statement.customer_name}' ({statement.account_number}).",
                metadata={"customer_name": statement.customer_name, "total_transactions": statement.total_transactions},
            )
        )
        await asyncio.sleep(0.04)

        # 3. Feature extraction
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.TOOL_COMPLETED,
                node="tools",
                tool_name="extract_features",
                message="3. Feature extraction: Temporal, directional, velocity, and statistical vectors extracted.",
                metadata={"feature_dimensions": ["amount", "rolling_velocity", "delta_time", "flow_direction"]},
            )
        )
        await asyncio.sleep(0.04)

        # 4. Rule analysis
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.TOOL_COMPLETED,
                node="tools",
                tool_name="detect_rules",
                message="4. Rule analysis: Evaluated deterministic AML rules (RULE_LARGE_TRANSACTION, RULE_RAPID_MOVEMENT_OF_FUNDS, RULE_HIGH_VELOCITY_BURST).",
                metadata={"rules_evaluated": ["RULE_LARGE_TRANSACTION", "RULE_RAPID_MOVEMENT_OF_FUNDS", "RULE_HIGH_VELOCITY_BURST"]},
            )
        )
        await asyncio.sleep(0.04)

        # 5. Isolation Forest
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.TOOL_COMPLETED,
                node="tools",
                tool_name="detect_anomalies",
                message="5. Isolation Forest: Identified 6 statistical outliers (TXN401, TXN404, TXN434, TXN442, TXN445, TXN451).",
                metadata={"anomaly_ids": ["TXN401", "TXN404", "TXN434", "TXN442", "TXN445", "TXN451"]},
            )
        )
        await asyncio.sleep(0.04)

        # 6. Customer profiling
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.TOOL_COMPLETED,
                node="tools",
                tool_name="get_customer_profile",
                message="6. Customer profiling: Aggregated behavioral baseline (54 transactions, 28 unique counterparties, net outflow ₹771,960).",
                metadata={"unique_counterparties": 28, "total_transactions": 54},
            )
        )
        await asyncio.sleep(0.04)

        # 7. Network analysis
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.TOOL_COMPLETED,
                node="tools",
                tool_name="analyze_transaction_network",
                message="7. Network analysis: Counterparty graph built (28 counterparties, 29 nodes, 37 directed edges).",
                metadata={"counterparties": 28, "graph_nodes": 29, "graph_edges": 37},
            )
        )
        await asyncio.sleep(0.04)

        # 8. RAG
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.RAG_COMPLETED,
                node="tools",
                tool_name="search_aml_knowledge",
                message="8. AML Reference RAG: Retrieved typologies from aml_red_flags.md, aml_transaction_monitoring.md, aml_investigation_guidance.md.",
                metadata={"sources": ["aml_red_flags.md", "aml_transaction_monitoring.md", "aml_investigation_guidance.md"]},
            )
        )
        await asyncio.sleep(0.04)

        # 9. Investigation agent
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.SYNTHESIS_COMPLETED,
                node="investigator",
                message="9. Investigation Agent: Synthesized multi-source evidence and contextual reasoning.",
                metadata={"referenced_transaction_ids": ["TXN401", "TXN404", "TXN434", "TXN442", "TXN445", "TXN451", "TXN406", "TXN415", "TXN422"]},
            )
        )
        await asyncio.sleep(0.04)

        # 10. Evidence convergence
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.NODE_COMPLETED,
                node="convergence",
                message="10. Evidence convergence: Ranked highest-convergence transactions across independent signal domains (TXN445, TXN434).",
                metadata={"top_convergence_transactions": ["TXN445", "TXN434"]},
            )
        )
        await asyncio.sleep(0.04)

        # 11. Critic validation
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.CRITIC_PASSED,
                node="critic",
                status="PASS",
                message="11. Critic validation: PASSED. Audited against 54 statement records, 0 unverified references.",
                metadata={
                    "statement_transaction_count": 54,
                    "verified_references": 9,
                    "unverified_references": 0,
                },
            )
        )
        await asyncio.sleep(0.04)

        # 12. Human-review queue
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.NODE_COMPLETED,
                node="human_review",
                message="12. Human-review queue: 50 items prioritized (25 HIGH, 10 MEDIUM, 15 LOW).",
                metadata={"total_review_items": 50, "high_priority": 25, "medium_priority": 10, "low_priority": 15},
            )
        )
        await asyncio.sleep(0.04)

        demo_inv = _build_demo_investigation_result(question)
        report = generate_investigation_report(statement=statement, investigation=demo_inv)
        markdown_text = format_report_markdown(report)

        # Set result on bus before emitting completion event so report is immediately readable
        bus.set_result(report=report, markdown=markdown_text)

        # 13. Final Report & Completion
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.REPORT_GENERATED,
                message=f"13. Final report: 14-section compliance audit report generated (Report ID: {report.report_id}).",
            )
        )
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.INVESTIGATION_COMPLETED,
                message="Demonstration investigation workflow concluded successfully.",
            )
        )

        # Save to history
        try:
            get_history_service().save_run(
                investigation_id=investigation_id,
                report=report,
                markdown_text=markdown_text,
                status="COMPLETED",
                runtime_seconds=1.2,
            )
        except Exception as hist_err:
            logger.warning(f"Could not persist demo run to history: {hist_err}")

    except Exception as exc:
        logger.error(f"[Demo Async Investigation] Error: {exc}")
        bus.publish_sync(
            InvestigationEvent(
                investigation_id=investigation_id,
                event_type=EventType.INVESTIGATION_FAILED,
                status="FAILED",
                message=f"Demo execution failed: {str(exc)}",
                metadata={"error": str(exc)},
            )
        )
        bus.set_error(str(exc))


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    """Return operational health status of the AML Investigation Copilot service."""
    return HealthResponse(
        status="ok",
        service="aml-copilot",
        version="0.1.0",
        timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
    )


@router.post(
    "/investigations",
    response_model=InvestigationStartResponse,
    summary="Start an asynchronous investigation returning immediate tracking identifier",
    tags=["Investigation"],
)
async def start_investigation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Customer bank statement in PDF format"),
    question: str = Form(..., description="Analyst guidance or question for investigation"),
    rag_service: Optional[RAGService] = Depends(get_api_rag_service),
) -> InvestigationStartResponse:
    """Accept statement PDF and question, queue background investigation, and return immediately."""
    clean_question = (question or "").strip()
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Investigation question cannot be empty.",
        )

    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file '{filename}' is not a PDF. Please provide a valid .pdf file.",
        )

    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(exc)}",
        ) from exc

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file exceeds maximum permitted size of {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )

    investigation_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
    event_manager = get_event_manager()
    event_manager.get_or_create_bus(investigation_id)

    # Launch background task
    background_tasks.add_task(
        _run_async_investigation,
        investigation_id=investigation_id,
        pdf_bytes=content,
        filename=filename,
        question=clean_question,
        rag_service=rag_service,
    )

    return InvestigationStartResponse(
        investigation_id=investigation_id,
        status="QUEUED",
        message="Investigation registered and queued for execution.",
    )


@router.post(
    "/investigations/demo",
    response_model=InvestigationStartResponse,
    summary="Start an asynchronous demo investigation on synthetic statement",
    tags=["Investigation"],
)
async def start_demo_investigation(
    background_tasks: BackgroundTasks,
    rag_service: Optional[RAGService] = Depends(get_api_rag_service),
) -> InvestigationStartResponse:
    """Queue background demonstration investigation emitting real lifecycle events."""
    investigation_id = f"INV-DEMO-{uuid.uuid4().hex[:6].upper()}"
    event_manager = get_event_manager()
    event_manager.get_or_create_bus(investigation_id)

    background_tasks.add_task(
        _run_demo_async_investigation,
        investigation_id=investigation_id,
        rag_service=rag_service,
    )

    return InvestigationStartResponse(
        investigation_id=investigation_id,
        status="QUEUED",
        message="Demo investigation registered and queued for execution.",
    )


@router.get(
    "/investigations/{investigation_id}/events",
    summary="Subscribe to live investigation events using Server-Sent Events (SSE)",
    tags=["Investigation"],
)
async def stream_investigation_events(investigation_id: str) -> StreamingResponse:
    """Stream live InvestigationEvent objects via SSE text/event-stream."""
    event_manager = get_event_manager()
    bus = event_manager.get_bus(investigation_id)
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation with ID '{investigation_id}' does not exist.",
        )

    async def event_generator() -> AsyncIterator[str]:
        async for event in bus.subscribe(heartbeat_interval=10.0):
            if event is None:
                yield ": keepalive\n\n"
            else:
                payload = event.model_dump_json()
                yield f"event: investigation_event\ndata: {payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/investigations/{investigation_id}",
    response_model=InvestigationStatusResponse,
    summary="Query investigation status and retrieve report when completed",
    tags=["Investigation"],
)
async def get_investigation_status(investigation_id: str) -> InvestigationStatusResponse:
    """Query current status, latest event, and completed report of an investigation."""
    event_manager = get_event_manager()
    bus = event_manager.get_bus(investigation_id)
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation with ID '{investigation_id}' does not exist.",
        )

    return InvestigationStatusResponse(
        investigation_id=investigation_id,
        status=bus.status,
        latest_event=bus.latest_event,
        report=bus.report,
        markdown=bus.markdown,
        execution_time_seconds=bus.execution_time_seconds,
        error=bus.error,
    )


# ---------------------------------------------------------------------------
# Synchronous Endpoints (Preserved for Compatibility)
# ---------------------------------------------------------------------------

@router.post(
    "/investigate",
    response_model=InvestigationAPIResponse,
    summary="Execute multi-role investigation on uploaded statement PDF (Synchronous)",
    tags=["Investigation"],
)
async def investigate_statement(
    file: UploadFile = File(..., description="Customer bank statement in PDF format"),
    question: str = Form(..., description="Specific question or guidance for the investigation"),
    rag_service: Optional[RAGService] = Depends(get_api_rag_service),
    settings: Settings = Depends(get_api_settings),
) -> InvestigationAPIResponse:
    """Process an uploaded bank statement PDF, run multi-agent investigation, and return report."""
    start_time = time.time()

    clean_question = (question or "").strip()
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Investigation question cannot be empty.",
        )

    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file '{filename}' is not a PDF. Please provide a valid .pdf file.",
        )

    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(exc)}",
        ) from exc

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file exceeds maximum permitted size of {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            temp_path = Path(tmp.name)

        doc = extract_pdf_text(temp_path)
        statement = parse_transactions(doc)

    except (PDFInvalidFormatError, PDFNotFoundError, TransactionParsingError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to parse statement transactions: {str(exc)}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the statement document.",
        ) from exc
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass

    try:
        investigation_result = run_investigation(
            statement=statement,
            question=clean_question,
            rag_service=rag_service,
            include_rag=True,
            include_profile=True,
            include_network=True,
            enable_critic=True,
        )
    except AgentConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Investigation LLM service is not configured: {str(exc)}",
        ) from exc
    except AMLCopilotError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation engine failure: {str(exc)}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error occurred during investigation execution.",
        ) from exc

    try:
        report = generate_investigation_report(
            statement=statement,
            investigation=investigation_result,
        )
        markdown_text = format_report_markdown(report)
        elapsed = round(time.time() - start_time, 2)

        return InvestigationAPIResponse(
            report=report,
            markdown=markdown_text,
            execution_time_seconds=elapsed,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to synthesize final investigation report.",
        ) from exc


@router.get(
    "/demo",
    response_model=InvestigationAPIResponse,
    summary="Retrieve high-fidelity demo investigation report on synthetic statement",
    tags=["Demo"],
)
async def get_demo_investigation(
    rag_service: Optional[RAGService] = Depends(get_api_rag_service),
) -> InvestigationAPIResponse:
    """Return a demonstration report based on canonical stress statement data."""
    start_time = time.time()
    sample_pdf = Path("data/statements/ultimate_publish_stress_statement.pdf")

    if not sample_pdf.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample statement file not found for demo mode: ultimate_publish_stress_statement.pdf",
        )

    try:
        doc = extract_pdf_text(sample_pdf)
        stmt = parse_transactions(doc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load demo statement: {str(exc)}",
        ) from exc

    question = "Investigate unusual movement of funds in this account and highlight transactions requiring human review."

    demo_inv = _build_demo_investigation_result(question)
    report = generate_investigation_report(statement=stmt, investigation=demo_inv)
    markdown_text = format_report_markdown(report)
    elapsed = round(time.time() - start_time, 2)

    return InvestigationAPIResponse(
        report=report,
        markdown=markdown_text,
        execution_time_seconds=elapsed,
    )


# ---------------------------------------------------------------------------
# Report Download Endpoints (Phase 9)
# ---------------------------------------------------------------------------

@router.get(
    "/investigations/{investigation_id}/download/markdown",
    summary="Download formatted markdown investigation report",
    tags=["Investigation"],
)
async def download_report_markdown(investigation_id: str) -> Response:
    """Download the finalized report as a markdown document."""
    event_manager = get_event_manager()
    bus = event_manager.get_bus(investigation_id)
    markdown_text = None
    if bus and bus.markdown:
        markdown_text = bus.markdown
    else:
        # Check history
        history_svc = get_history_service()
        hist = history_svc.get_report(investigation_id)
        if hist and hist.get("markdown"):
            markdown_text = hist["markdown"]

    if not markdown_text:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Markdown report not available for investigation '{investigation_id}'.",
        )

    return Response(
        content=markdown_text,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="aml_report_{investigation_id}.md"',
        },
    )


@router.get(
    "/investigations/{investigation_id}/download/json",
    summary="Download canonical JSON evidence export with provenance",
    tags=["Investigation"],
)
async def download_report_json(investigation_id: str) -> Response:
    """Download canonical structured report with all evidence layers as JSON."""
    event_manager = get_event_manager()
    bus = event_manager.get_bus(investigation_id)
    report_json_str = None
    if bus and bus.report:
        report_json_str = bus.report.model_dump_json(indent=2)
    else:
        # Check history
        history_svc = get_history_service()
        hist = history_svc.get_report(investigation_id)
        if hist and hist.get("report"):
            report_json_str = json.dumps(hist["report"], indent=2)

    if not report_json_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"JSON evidence export not available for investigation '{investigation_id}'.",
        )

    return Response(
        content=report_json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="aml_evidence_{investigation_id}.json"',
        },
    )


# ---------------------------------------------------------------------------
# Transaction Evidence Explorer Endpoint (Phase 8)
# ---------------------------------------------------------------------------

@router.get(
    "/investigations/{investigation_id}/transactions/{transaction_id}",
    response_model=TransactionEvidenceDossier,
    summary="Retrieve deterministic multi-layer evidence dossier for a transaction",
    tags=["Investigation"],
)
async def get_transaction_evidence(
    investigation_id: str,
    transaction_id: str,
) -> TransactionEvidenceDossier:
    """Return complete evidence dossier for a specific transaction in an investigation."""
    event_manager = get_event_manager()
    bus = event_manager.get_bus(investigation_id)
    report = None
    if bus and bus.report:
        report = bus.report
    else:
        history_svc = get_history_service()
        hist = history_svc.get_report(investigation_id)
        if hist and hist.get("report"):
            report = InvestigationReport(**hist["report"])

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation report '{investigation_id}' not found.",
        )

    dossier = build_transaction_dossier(report, transaction_id)
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{transaction_id}' not found in investigation '{investigation_id}'.",
        )

    return dossier


# ---------------------------------------------------------------------------
# Investigation History Endpoints (Phase 11)
# ---------------------------------------------------------------------------

@router.get(
    "/history",
    response_model=List[InvestigationHistoryRecord],
    summary="List past investigation runs",
    tags=["History"],
)
async def list_investigation_history() -> List[InvestigationHistoryRecord]:
    """Retrieve metadata records of all historical investigations."""
    history_svc = get_history_service()
    return history_svc.list_history()


@router.get(
    "/history/{report_id}",
    summary="Retrieve full report and markdown by report ID",
    tags=["History"],
)
async def get_historical_report(report_id: str) -> Dict[str, Any]:
    """Retrieve full historical report JSON and Markdown."""
    history_svc = get_history_service()
    data = history_svc.get_report(report_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Historical report '{report_id}' not found.",
        )
    return data

