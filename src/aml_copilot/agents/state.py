"""State definitions and data contracts for the LangGraph investigation workflow."""

from typing import Annotated, Any, Dict, List, Optional, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from aml_copilot.agents.models import (
    CritiqueResult,
    InvestigationDraft,
    InvestigationFinding,
)
from aml_copilot.models.transaction import TransactionStatement


class ToolExecutionRecord(BaseModel):
    """Log entry of an executed tool call during agent reasoning."""

    tool_name: str
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    tool_output_snippet: str = ""


class InvestigationRequest(BaseModel):
    """Request payload to initiate an agent investigation."""

    statement: TransactionStatement
    question: str
    max_iterations: Optional[int] = None
    max_revisions: Optional[int] = None


class InvestigationStatus(str):
    """Investigation execution status with backward compatibility.

    Distinguishes:
    - NORMAL_COMPLETION: Completed investigation with sufficient evidence and report.
    - MAX_ITERATIONS_REACHED: Exceeded iteration budget before sufficient evidence was gathered.
    - PROVIDER_FAILURE: LLM provider failure occurred during execution.
    - ALL_PROVIDERS_FAILED: All failover providers exhausted.
    - INVESTIGATION_FAILED: Unexpected error during investigation workflow.
    """

    NORMAL_COMPLETION: "InvestigationStatus"
    MAX_ITERATIONS_REACHED: "InvestigationStatus"
    PROVIDER_FAILURE: "InvestigationStatus"
    ALL_PROVIDERS_FAILED: "InvestigationStatus"
    INVESTIGATION_FAILED: "InvestigationStatus"

    def __eq__(self, other: Any) -> bool:
        if str(self) == "NORMAL_COMPLETION" and other == "COMPLETED":
            return True
        if str(self) == "COMPLETED" and other == "NORMAL_COMPLETION":
            return True
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(str(self))


InvestigationStatus.NORMAL_COMPLETION = InvestigationStatus("NORMAL_COMPLETION")
InvestigationStatus.MAX_ITERATIONS_REACHED = InvestigationStatus("MAX_ITERATIONS_REACHED")
InvestigationStatus.PROVIDER_FAILURE = InvestigationStatus("PROVIDER_FAILURE")
InvestigationStatus.ALL_PROVIDERS_FAILED = InvestigationStatus("ALL_PROVIDERS_FAILED")
InvestigationStatus.INVESTIGATION_FAILED = InvestigationStatus("INVESTIGATION_FAILED")


class InvestigationResult(BaseModel):
    """Structured response from the investigation agent preserving audit trail."""

    question: str
    response: str
    tools_used: List[str] = Field(default_factory=list)
    tool_calls: List[ToolExecutionRecord] = Field(default_factory=list)
    referenced_transaction_ids: List[str] = Field(default_factory=list)
    knowledge_sources: List[str] = Field(
        default_factory=list,
        description="AML reference knowledge sources cited or retrieved during investigation",
    )
    customer_profile: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Customer behavioral profile if computed or retrieved during investigation",
    )
    network_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Network analysis findings if computed or retrieved during investigation",
    )
    findings: List[InvestigationFinding] = Field(
        default_factory=list,
        description="Structured findings discovered during investigation",
    )
    draft: Optional[InvestigationDraft] = Field(
        default=None,
        description="Structured investigation draft before critique and revision",
    )
    critic_result: Optional[CritiqueResult] = Field(
        default=None,
        description="Critique result evaluating factual grounding and compliance standards",
    )
    critic_status: Optional[str] = Field(
        default=None,
        description="Status of Critic evaluation ('PASS' or 'FAIL')",
    )
    revision_count: int = Field(
        default=0,
        description="Number of revision cycles performed before final synthesis",
    )
    status: Any = Field(
        default=InvestigationStatus.NORMAL_COMPLETION,
        description="Investigation lifecycle status ('NORMAL_COMPLETION', 'MAX_ITERATIONS_REACHED', 'ALL_PROVIDERS_FAILED', 'PROVIDER_FAILURE', 'INVESTIGATION_FAILED')",
    )
    is_partial: bool = Field(
        default=False,
        description="Indicates whether investigation completed partially due to reaching reasoning iteration limit",
    )
    canonical_evidence: Optional[Any] = Field(
        default=None,
        description="Canonical structured single source of truth evidence for reporting",
    )
    limitations_warnings: List[str] = Field(default_factory=list)


class InvestigationState(TypedDict, total=False):
    """Shared execution memory of the LangGraph AML investigation workflow.

    In LangGraph, 'State' is the central memory passed from node to node.
    It allows information to survive the transitions between:
    Agent Node -> Tool Node -> Agent Node -> Synthesis -> Critic -> Revision -> Agent.
    """

    # 1. messages: Sequence of dialogue messages (System, Human, AI, Tool).
    # Uses the 'add_messages' reducer so new messages from nodes are appended rather than overwriting.
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 2. statement: Validated TransactionStatement under review.
    # Preserved in state so all tools can access the customer's real transaction data.
    statement: TransactionStatement

    # 3. question: The original analyst query guiding the investigation.
    question: str

    # 4. tools_used: Cumulative list of unique tool names called so far.
    tools_used: List[str]

    # 5. tool_calls: Audit trail of executed tool calls, arguments, and result snippets.
    tool_calls: List[ToolExecutionRecord]

    # 6. knowledge_sources: Cumulative list of AML reference citations retrieved.
    knowledge_sources: List[str]

    # 7. iteration_count: Tracks decision cycles to enforce max_iterations safeguard.
    iteration_count: int

    # 8. max_iterations: Maximum allowed reasoning steps before mandatory termination.
    max_iterations: int

    # 9. final_response: Final text output when agent concludes reasoning.
    final_response: str

    # 10. customer_profile: Behavioral customer profile if generated by tools.
    customer_profile: Optional[Dict[str, Any]]

    # 11. network_analysis: Network graph analysis if generated by tools.
    network_analysis: Optional[Dict[str, Any]]

    # 12. investigation_plan: Planned analytical steps for the investigation.
    investigation_plan: Optional[List[str]]

    # 13. findings: Structured list of verified findings discovered.
    findings: Optional[List[InvestigationFinding]]

    # 14. draft: Formulated investigation draft prior to critique.
    draft: Optional[InvestigationDraft]

    # 15. critic_result: Output from Critic evaluation.
    critic_result: Optional[CritiqueResult]

    # 16. critic_status: Status outcome of critique ('PASS' or 'FAIL').
    critic_status: Optional[str]

    # 17. critic_feedback: Human-readable critique feedback for revision.
    critic_feedback: Optional[str]

    # 18. revision_count: Number of revisions undertaken so far.
    revision_count: int

    # 19. max_revisions: Maximum allowed revision attempts to avoid infinite loops.
    max_revisions: int

    # 20. enable_critic: Whether the critique and revision loop is active.
    enable_critic: bool

    # 21. event_callback: Optional callable for real-time investigation lifecycle event emission.
    event_callback: Optional[Any]

    # 22. investigation_id: Optional tracking identifier for event correlation.
    investigation_id: Optional[str]

    # 23. status: Investigation lifecycle status ('COMPLETED', 'MAX_ITERATIONS_REACHED', 'FAILED').
    status: Optional[str]

    # 24. is_partial: Whether investigation was halted prematurely.
    is_partial: Optional[bool]

    # 25. canonical_evidence: Canonical structured single source of truth evidence.
    canonical_evidence: Optional[Any]


def emit_investigation_event(
    state: InvestigationState,
    event_type: str,
    message: str,
    node: Optional[str] = None,
    tool_name: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Helper to emit an event via the state's event_callback if registered."""
    cb = state.get("event_callback")
    if not cb or not callable(cb):
        return

    try:
        from aml_copilot.events.models import InvestigationEvent

        evt = InvestigationEvent(
            investigation_id=state.get("investigation_id") or "INV-UNKNOWN",
            event_type=event_type,
            node=node,
            status=status,
            message=message,
            tool_name=tool_name,
            iteration=state.get("iteration_count", 0),
            revision=state.get("revision_count", 0),
            metadata=metadata or {},
        )
        cb(evt)
    except Exception:
        # Event emission failure must never disrupt core investigation reasoning
        pass
