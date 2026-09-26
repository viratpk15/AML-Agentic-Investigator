"""Evidence sufficiency evaluation and redundant tool call protection for AML investigations."""

from typing import Any, Dict, List, Optional, Set
import re

from aml_copilot.agents.state import InvestigationState, ToolExecutionRecord
from aml_copilot.logger import get_logger

logger = get_logger(__name__)

# Single-execution analysis tools that evaluate statement-wide records deterministically
SINGLE_RUN_TOOLS: Set[str] = {
    "get_transaction_statistics",
    "detect_anomalies",
    "get_customer_profile",
    "analyze_transaction_network",
}


def check_tool_call_redundancy(
    tool_name: str,
    tool_args: Dict[str, Any],
    state: InvestigationState,
) -> Optional[str]:
    """Inspect proposed tool call against previous execution history to prevent redundant queries.

    Args:
        tool_name: Name of tool the agent wants to execute.
        tool_args: Dictionary of arguments provided for the tool call.
        state: Current LangGraph execution state.

    Returns:
        A concise deterministic explanation string if the call is redundant/duplicate,
        or None if the call is legitimate and should proceed.
    """
    previous_calls: List[ToolExecutionRecord] = state.get("tool_calls", [])
    tools_used: List[str] = state.get("tools_used", [])

    # 1. Exact identical tool call with same arguments
    for record in previous_calls:
        if record.tool_name == tool_name:
            if record.tool_args == tool_args:
                return (
                    f"Redundant tool call skipped: '{tool_name}' was already executed with identical arguments {tool_args}. "
                    "Its complete output is already in your conversation history. "
                    "Do not repeat identical queries; proceed to synthesize your findings."
                )

    # 2. Single-run tools that evaluate the entire statement deterministically
    if tool_name in SINGLE_RUN_TOOLS and tool_name in tools_used:
        return (
            f"Redundant tool call skipped: '{tool_name}' has already evaluated customer statement records. "
            "Results are already available in your conversation history. "
            "Proceed to synthesize your findings."
        )

    # 3. Transaction Search redundancy checks
    if tool_name == "search_transactions":
        target_tid = tool_args.get("transaction_id")
        # 3a. Specific transaction ID already searched or evaluated in previous tools
        if target_tid:
            for record in previous_calls:
                # Exact ID already queried in search_transactions
                if record.tool_name == "search_transactions" and record.tool_args.get("transaction_id") == target_tid:
                    return (
                        f"Redundant search skipped: Transaction '{target_tid}' was already retrieved in a previous search. "
                        "Full transaction details are present in history. Proceed to synthesis."
                    )
                # ID was returned in the snippet of any previous tool (detect_anomalies, profile, search)
                if target_tid in record.tool_output_snippet:
                    return (
                        f"Redundant search skipped: Details for transaction '{target_tid}' were already retrieved in "
                        f"'{record.tool_name}' output. Full transaction details are present in history. Proceed to synthesis."
                    )

            # If detect_anomalies has already executed, all transactions in statement are evaluated
            if "detect_anomalies" in tools_used:
                statement = state.get("statement")
                if statement:
                    stmt_tids = {t.transaction_id for t in statement.transactions if t.transaction_id}
                    if target_tid in stmt_tids:
                        return (
                            f"Redundant search skipped: Transaction '{target_tid}' has already been screened by detection rules and anomaly models. "
                            "Its status is documented in detection findings. Proceed to synthesis."
                        )

        # 3b. Generic unconstrained broad search after specific searches or detection
        filter_keys = ["transaction_id", "min_amount", "max_amount", "counterparty", "start_date", "end_date", "transaction_type"]
        is_broad = not any(tool_args.get(k) is not None for k in filter_keys)
        if is_broad:
            has_searched = any(r.tool_name == "search_transactions" for r in previous_calls)
            has_detected = "detect_anomalies" in tools_used
            if has_searched or has_detected:
                return (
                    "Redundant search skipped: Statement transactions and anomalies have already been retrieved "
                    "and profiled in previous steps. Do not run unconstrained broad searches; proceed to synthesize findings."
                )

    # 4. AML Knowledge (RAG) search redundancy checks
    if tool_name == "search_aml_knowledge":
        query = (tool_args.get("query") or "").strip().lower()
        if query:
            # Tokenize query ignoring stop words
            stop_words = {"the", "a", "an", "and", "or", "in", "on", "of", "for", "to", "with", "aml", "what", "is"}
            query_tokens = {w for w in re.findall(r"\w+", query) if w not in stop_words}
            
            for record in previous_calls:
                if record.tool_name == "search_aml_knowledge":
                    prev_query = (record.tool_args.get("query") or "").strip().lower()
                    prev_tokens = {w for w in re.findall(r"\w+", prev_query) if w not in stop_words}
                    
                    if query_tokens and prev_tokens:
                        intersection = query_tokens & prev_tokens
                        smaller_len = min(len(query_tokens), len(prev_tokens))
                        overlap = len(intersection) / smaller_len if smaller_len > 0 else 0.0
                        if overlap >= 0.75:
                            sources = state.get("knowledge_sources", [])
                            return (
                                f"Redundant AML knowledge search skipped: Typology concepts for '{query}' overlap heavily with "
                                f"prior query '{prev_query}' (sources: {', '.join(sources) if sources else 'RAG'}). "
                                "Proceed to synthesize your findings."
                            )

    return None


def is_evidence_sufficient(state: InvestigationState) -> bool:
    """Determine deterministically whether gathered evidence is sufficient to synthesize findings.

    Checks:
    - Detection findings available (detect_anomalies)
    - Behavioral profile available (get_customer_profile or get_transaction_statistics)
    - Network relationships analyzed (analyze_transaction_network) or transaction search performed
    """
    tools_used = set(state.get("tools_used", []))
    tool_calls = state.get("tool_calls", [])

    has_detection = "detect_anomalies" in tools_used
    has_profile = "get_customer_profile" in tools_used or "get_transaction_statistics" in tools_used
    has_network = "analyze_transaction_network" in tools_used
    has_search = "search_transactions" in tools_used

    # Core combination 1: Detection + Behavioral Profile
    if has_detection and has_profile:
        return True

    # Core combination 2: Detection + Network Analysis
    if has_detection and has_network:
        return True

    # Core combination 3: Detection + Targeted Search
    if has_detection and has_search and len(tool_calls) >= 2:
        return True

    # Breadth fallback: 3 or more distinct analysis tools executed
    if len(tools_used) >= 3:
        return True

    # Volume fallback: 3 or more total tool reasoning calls executed
    if len(tool_calls) >= 3:
        return True

    return False


def get_sufficiency_advisory(state: InvestigationState) -> Optional[str]:
    """Produce an advisory prompt instruction when evidence is sufficient or budget is nearly exhausted."""
    curr_iter = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 5)

    if is_evidence_sufficient(state):
        return (
            "[EVIDENCE SUFFICIENCY ADVISORY]: You have retrieved sufficient evidence to answer the investigation "
            "question (detection findings, behavioral/network metrics, and transaction records). "
            "Do NOT perform additional exploratory searches. Proceed immediately to synthesize your final report "
            "narrative into the required sections (Observed Evidence, Relevant AML Reference, Interpretation, Limitations)."
        )

    if curr_iter >= max_iter - 1:
        return (
            "[FINAL REASONING ITERATION BUDGET]: You have reached the final reasoning iteration within your tool budget. "
            "You MUST conclude tool usage and synthesize your draft findings narrative immediately."
        )

    return None
