"""Agents subpackage for AML investigation copilot orchestrated via LangGraph."""

from .critic import (
    create_critic_node,
    evaluate_investigation_draft,
)
from .graph import (
    build_investigation_graph,
    create_agent_node,
    create_tool_node,
    route_after_critic,
    should_continue,
    should_continue_investigator,
)
from .investigation_agent import (
    InvestigationAgent,
    run_investigation,
)
from .models import (
    CritiqueResult,
    EvidenceReference,
    InvestigationDraft,
    InvestigationFinding,
)
from .revision import create_revision_node
from .state import (
    InvestigationRequest,
    InvestigationResult,
    InvestigationState,
    ToolExecutionRecord,
)
from .synthesis import (
    create_synthesis_node,
    synthesize_findings_from_response,
)

__all__ = [
    "InvestigationState",
    "ToolExecutionRecord",
    "InvestigationRequest",
    "InvestigationResult",
    "InvestigationFinding",
    "EvidenceReference",
    "InvestigationDraft",
    "CritiqueResult",
    "create_agent_node",
    "create_tool_node",
    "create_synthesis_node",
    "create_critic_node",
    "create_revision_node",
    "synthesize_findings_from_response",
    "evaluate_investigation_draft",
    "should_continue",
    "should_continue_investigator",
    "route_after_critic",
    "build_investigation_graph",
    "InvestigationAgent",
    "run_investigation",
]
