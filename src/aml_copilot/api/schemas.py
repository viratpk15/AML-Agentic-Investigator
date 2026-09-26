"""FastAPI request and response schemas for the AML Investigation Copilot API."""

import datetime as dt
from typing import Optional
from pydantic import BaseModel, Field

from aml_copilot.events.models import InvestigationEvent
from aml_copilot.reporting.models import InvestigationReport


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="ok", description="Service health status")
    service: str = Field(default="aml-copilot", description="Name of the service")
    version: str = Field(default="0.1.0", description="API version")
    timestamp: str = Field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat(),
        description="Current server UTC timestamp",
    )


class InvestigationAPIResponse(BaseModel):
    """Full structured response returned by the synchronous investigation endpoint."""

    report: InvestigationReport = Field(..., description="Complete structured AML investigation report")
    markdown: str = Field(..., description="Human-readable formatted Markdown report")
    execution_time_seconds: float = Field(..., description="Elapsed wall-clock processing time")


class InvestigationStartResponse(BaseModel):
    """Immediate acknowledgment response returned when an asynchronous investigation starts."""

    investigation_id: str = Field(..., description="Unique tracking identifier for this investigation")
    status: str = Field(default="QUEUED", description="Initial lifecycle state (QUEUED or RUNNING)")
    message: str = Field(..., description="Status announcement")


class InvestigationStatusResponse(BaseModel):
    """Lifecycle status and result query response for an ongoing or completed investigation."""

    investigation_id: str = Field(..., description="Unique tracking identifier for this investigation")
    status: str = Field(
        ...,
        description="Current status: QUEUED, RUNNING, COMPLETED, MAX_ITERATIONS_REACHED, or FAILED",
    )
    latest_event: Optional[InvestigationEvent] = Field(
        default=None, description="Most recent lifecycle event emitted"
    )
    report: Optional[InvestigationReport] = Field(
        default=None, description="Final structured investigation report if completed"
    )
    markdown: Optional[str] = Field(
        default=None, description="Formatted Markdown version of report if completed"
    )
    execution_time_seconds: Optional[float] = Field(
        default=None, description="Total execution time in seconds"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if investigation failed"
    )


class ErrorResponse(BaseModel):
    """Standardized API error schema."""

    error: str = Field(..., description="Error message summary")
    detail: Optional[str] = Field(default=None, description="Detailed explanatory context")
