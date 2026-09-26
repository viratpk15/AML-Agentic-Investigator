"""Strongly typed investigation event model for real-time streaming."""

import datetime as dt
from enum import Enum
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Categorized lifecycle events emitted during investigation execution."""

    INVESTIGATION_STARTED = "INVESTIGATION_STARTED"
    NODE_STARTED = "NODE_STARTED"
    NODE_COMPLETED = "NODE_COMPLETED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    RAG_STARTED = "RAG_STARTED"
    RAG_COMPLETED = "RAG_COMPLETED"
    SYNTHESIS_STARTED = "SYNTHESIS_STARTED"
    SYNTHESIS_COMPLETED = "SYNTHESIS_COMPLETED"
    CRITIC_STARTED = "CRITIC_STARTED"
    CRITIC_FAILED = "CRITIC_FAILED"
    REVISION_STARTED = "REVISION_STARTED"
    REVISION_COMPLETED = "REVISION_COMPLETED"
    CRITIC_PASSED = "CRITIC_PASSED"
    REPORT_GENERATED = "REPORT_GENERATED"
    INVESTIGATION_COMPLETED = "INVESTIGATION_COMPLETED"
    INVESTIGATION_MAX_ITERATIONS = "INVESTIGATION_MAX_ITERATIONS"
    INVESTIGATION_FAILED = "INVESTIGATION_FAILED"
    ALL_PROVIDERS_FAILED = "ALL_PROVIDERS_FAILED"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"

    # Provider failover telemetry events
    LLM_PROVIDER_ATTEMPT = "LLM_PROVIDER_ATTEMPT"
    """Emitted when an LLM request is dispatched to a provider."""
    LLM_PROVIDER_FAILED = "LLM_PROVIDER_FAILED"
    """Emitted when a provider returns an error (retryable or auth)."""
    LLM_PROVIDER_FALLBACK = "LLM_PROVIDER_FALLBACK"
    """Emitted when failover switches to the next provider."""
    LLM_PROVIDER_SELECTED = "LLM_PROVIDER_SELECTED"
    """Emitted when a provider returns a successful response."""



class InvestigationEvent(BaseModel):
    """Strongly typed event payload representing an agentic execution milestone."""

    event_id: str = Field(
        default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}",
        description="Unique identifier for this specific event",
    )
    investigation_id: str = Field(
        ...,
        description="Parent investigation case tracking identifier",
    )
    timestamp: str = Field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp when the event was generated",
    )
    event_type: str = Field(
        ...,
        description="Type identifier matching EventType enum or custom lifecycle name",
    )
    node: Optional[str] = Field(
        default=None,
        description="LangGraph workflow node name (e.g. investigator, tools, synthesis, critic, revision)",
    )
    status: Optional[str] = Field(
        default=None,
        description="Evaluation status if applicable (e.g. PASS, FAIL, RUNNING)",
    )
    message: str = Field(
        ...,
        description="Human-readable log or progress description",
    )
    tool_name: Optional[str] = Field(
        default=None,
        description="Name of specific tool executed if event represents tool invocation",
    )
    iteration: int = Field(
        default=0,
        description="Current reasoning iteration count within the agent loop",
    )
    revision: int = Field(
        default=0,
        description="Current revision cycle count within the critic loop",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured execution metadata (e.g. tool arguments, critic issues, sources)",
    )
