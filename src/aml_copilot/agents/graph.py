"""LangGraph workflow definition for the AML Investigation Copilot."""

import json
from typing import Any, Callable, Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from aml_copilot.agents.context_budget import (
    compact_tool_output,
    prepare_context_for_llm,
)
from aml_copilot.agents.critic import create_critic_node
from aml_copilot.agents.revision import create_revision_node
from aml_copilot.agents.synthesis import create_synthesis_node
from aml_copilot.agents.state import (
    InvestigationState,
    ToolExecutionRecord,
    emit_investigation_event,
)
from aml_copilot.agents.sufficiency import (
    check_tool_call_redundancy,
    get_sufficiency_advisory,
    is_evidence_sufficient,
)
from aml_copilot.config import get_settings
from aml_copilot.exceptions import AgentConfigurationError
from aml_copilot.logger import get_logger
from aml_copilot.models.transaction import TransactionStatement
from aml_copilot.tools.tool_registry import ToolRegistry

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Node Factories
# ---------------------------------------------------------------------------

def create_agent_node(
    llm_with_tools: Any,
    max_context_tokens: int = 6000,
    tools: Optional[List[Any]] = None,
) -> Callable[[InvestigationState], Dict[str, Any]]:
    """Create the Agent Node function.

    Responsibilities:
    1. Receive current state and message history.
    2. Enforce context token budget to prevent provider rate limit errors.
    3. Call the LLM with budget-compliant messages (with tools bound).
    4. Append the resulting AIMessage to state.
    5. Increment iteration counter.
    6. Return updated state.
    Note: The agent node does NOT execute tools directly.
    """

    def agent_node(state: InvestigationState) -> Dict[str, Any]:
        curr_iter = state.get("iteration_count", 0) + 1
        logger.debug(f"[Graph: Agent Node] Calling LLM (iteration {curr_iter})")

        messages = state["messages"]
        prepared_messages, budget_report = prepare_context_for_llm(
            messages,
            max_tokens=max_context_tokens,
            tools=tools,
        )

        emit_investigation_event(
            state,
            event_type="NODE_STARTED",
            node="investigator",
            message=f"Investigator evaluating transaction evidence and analytical reasoning (iteration {curr_iter})...",
            metadata={
                "context_estimated_tokens": budget_report.final_estimated_tokens,
                "context_budget": budget_report.budget_limit,
                "context_reduction_applied": budget_report.reduction_applied,
            },
        )

        ai_msg: AIMessage = llm_with_tools.invoke(prepared_messages)

        final_response = str(ai_msg.content) if not ai_msg.tool_calls else ""

        if ai_msg.tool_calls:
            tool_names = [c["name"] for c in ai_msg.tool_calls]
            emit_investigation_event(
                state,
                event_type="NODE_COMPLETED",
                node="investigator",
                message=f"Investigator formulated plan requesting tool(s): {', '.join(tool_names)}.",
                metadata={"tool_calls": tool_names},
            )
        else:
            emit_investigation_event(
                state,
                event_type="NODE_COMPLETED",
                node="investigator",
                message="Investigator concluded reasoning and prepared draft narrative.",
            )

        return {
            "messages": [ai_msg],
            "iteration_count": curr_iter,
            "final_response": final_response,
        }

    return agent_node


def create_tool_node(
    tools_by_name: Dict[str, Any]
) -> Callable[[InvestigationState], Dict[str, Any]]:
    """Create the Tool Node function.

    Responsibilities:
    1. Inspect tool calls produced by the latest AI message.
    2. Execute the corresponding registered tools locally.
    3. Create proper ToolMessage objects with results.
    4. Record tool execution metadata into state audit logs.
    Note: The tool node does NOT decide what to do next; the graph controls that.
    """

    def tool_node(state: InvestigationState) -> Dict[str, Any]:
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", [])

        new_messages: List[BaseMessage] = []
        new_tools_used = list(state.get("tools_used", []))
        new_tool_records = list(state.get("tool_calls", []))
        new_knowledge_sources = list(state.get("knowledge_sources", []))
        customer_profile = state.get("customer_profile")
        network_analysis = state.get("network_analysis")

        for call in tool_calls:
            tool_name = call["name"]
            tool_args = call.get("args", {})
            call_id = call.get("id") or f"call_{len(new_tool_records)}"

            if tool_name not in new_tools_used:
                new_tools_used.append(tool_name)

            # Check if this tool call is redundant or duplicate
            redundancy_note = check_tool_call_redundancy(tool_name, tool_args, state)
            if redundancy_note:
                logger.info(f"[Graph: Tool Node] Intercepted redundant tool call '{tool_name}': {redundancy_note}")
                output_str = json.dumps({"status": "redundant_skipped", "note": redundancy_note})
                snippet = f"[SKIPPED REDUNDANT] {redundancy_note[:250]}"
                new_tool_records.append(
                    ToolExecutionRecord(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        tool_output_snippet=snippet,
                    )
                )
                new_messages.append(ToolMessage(content=output_str, tool_call_id=call_id))
                emit_investigation_event(
                    state,
                    event_type="TOOL_COMPLETED",
                    node="tools",
                    tool_name=tool_name,
                    message=f"Tool '{tool_name}' skipped (redundant evidence already in history).",
                    metadata={"redundant_skipped": True, "reason": redundancy_note},
                )
                continue

            tool = tools_by_name.get(tool_name)
            if not tool:
                err_msg = f"Tool '{tool_name}' not found in registry."
                logger.warning(err_msg)
                new_messages.append(ToolMessage(content=json.dumps({"error": err_msg}), tool_call_id=call_id))
                continue

            if tool_name == "search_aml_knowledge":
                emit_investigation_event(
                    state,
                    event_type="RAG_STARTED",
                    node="tools",
                    tool_name=tool_name,
                    message="Querying AML reference knowledge base for typologies and monitoring guidance...",
                    metadata={"tool_args": tool_args},
                )
            else:
                emit_investigation_event(
                    state,
                    event_type="TOOL_STARTED",
                    node="tools",
                    tool_name=tool_name,
                    message=f"Executing tool '{tool_name}'...",
                    metadata={"tool_args": tool_args},
                )

            try:
                logger.info(f"[Graph: Tool Node] Executing '{tool_name}' with args: {tool_args}")
                tool_output = tool.invoke(tool_args)
                output_str = compact_tool_output(tool_name, tool_output)

                # Capture knowledge sources if RAG search tool was called
                if tool_name == "search_aml_knowledge" and isinstance(tool_output, dict):
                    rag_sources = tool_output.get("sources", [])
                    for src in rag_sources:
                        if src not in new_knowledge_sources:
                            new_knowledge_sources.append(src)
                    emit_investigation_event(
                        state,
                        event_type="RAG_COMPLETED",
                        node="tools",
                        tool_name=tool_name,
                        message=f"AML knowledge search completed ({len(rag_sources)} sources retrieved).",
                        metadata={"sources": rag_sources},
                    )

                # Capture customer profile if profiling tool was called
                if tool_name == "get_customer_profile" and isinstance(tool_output, dict):
                    customer_profile = tool_output

                # Capture network analysis if network tool was called
                if tool_name == "analyze_transaction_network" and isinstance(tool_output, dict):
                    network_analysis = tool_output

            except Exception as exc:
                logger.error(f"[Graph: Tool Node] Error executing '{tool_name}': {exc}")
                output_str = json.dumps({"error": str(exc)})

            emit_investigation_event(
                state,
                event_type="TOOL_COMPLETED",
                node="tools",
                tool_name=tool_name,
                message=f"Tool '{tool_name}' execution completed.",
            )

            snippet = output_str[:300] + ("..." if len(output_str) > 300 else "")
            new_tool_records.append(
                ToolExecutionRecord(
                    tool_name=tool_name,
                    tool_args=tool_args,
                    tool_output_snippet=snippet,
                )
            )
            new_messages.append(ToolMessage(content=output_str, tool_call_id=call_id))

        # Check if gathered evidence is now sufficient or reasoning budget is near limit
        updated_state: InvestigationState = {
            **state,
            "tools_used": new_tools_used,
            "tool_calls": new_tool_records,
            "knowledge_sources": new_knowledge_sources,
            "customer_profile": customer_profile,
            "network_analysis": network_analysis,
        }
        advisory = get_sufficiency_advisory(updated_state)
        if advisory and new_messages and isinstance(new_messages[-1], ToolMessage):
            last_msg = new_messages[-1]
            new_messages[-1] = ToolMessage(
                content=last_msg.content + f"\n\n{advisory}",
                tool_call_id=last_msg.tool_call_id,
            )

        return {
            "messages": new_messages,
            "tools_used": new_tools_used,
            "tool_calls": new_tool_records,
            "knowledge_sources": new_knowledge_sources,
            "customer_profile": customer_profile,
            "network_analysis": network_analysis,
        }

    return tool_node


# ---------------------------------------------------------------------------
# Conditional Routing
# ---------------------------------------------------------------------------

def create_max_iterations_node(
    statement: TransactionStatement,
) -> Callable[[InvestigationState], Dict[str, Any]]:
    """Create the Max Iterations Node function.

    Responsibilities:
    1. Mark state status as 'MAX_ITERATIONS_REACHED' and is_partial as True.
    2. Emit INVESTIGATION_MAX_ITERATIONS event with preserved execution metadata.
    3. Produce a transparent partial response noting that the iteration budget was reached
       and mandating human compliance review.
    """

    def max_iterations_node(state: InvestigationState) -> Dict[str, Any]:
        curr_iter = state.get("iteration_count", 0)
        max_iter = state.get("max_iterations", 5)
        tools_used = state.get("tools_used", [])
        logger.warning(
            f"[Graph: Max Iterations Node] Investigator reached maximum reasoning iterations ({curr_iter}/{max_iter})."
        )
        msg = (
            f"Investigation reached maximum reasoning iterations ({max_iter}) before concluding full synthesis. "
            f"Partial evidence gathered from {len(tools_used)} executed tools is preserved. "
            "Mandatory human compliance review is required."
        )
        emit_investigation_event(
            state,
            event_type="INVESTIGATION_MAX_ITERATIONS",
            node="investigator",
            status="MAX_ITERATIONS_REACHED",
            message=msg,
            metadata={
                "iteration_count": curr_iter,
                "max_iterations": max_iter,
                "tools_used": tools_used,
            },
        )
        return {
            "status": "MAX_ITERATIONS_REACHED",
            "is_partial": True,
            "final_response": msg,
        }

    return max_iterations_node


def should_continue(state: InvestigationState) -> str:
    """Legacy conditional edge decision function matching M10 test contract."""
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 5)

    if iteration_count > max_iterations:
        logger.warning(
            f"[Graph Router] Max iterations ({max_iterations}) exceeded ({iteration_count}). Halting loop -> END."
        )
        return END

    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"

    return END


def should_continue_investigator(state: InvestigationState) -> str:
    """Conditional edge decision function for the Investigator node in M14/M15 workflow.

    Inspects the latest message and evidence state:
    - If latest AIMessage has no tool calls: routes to 'synthesis' to formulate structured draft.
    - If latest AIMessage requested tool calls:
      - If evidence is already sufficient and all proposed tool calls are redundant:
        halts the tool loop immediately and routes to 'synthesis'.
      - If iteration budget reached (iteration_count >= max_iterations):
        - If gathered evidence is sufficient: routes to 'synthesis' to complete report.
        - If gathered evidence is NOT sufficient: routes to 'max_iterations' (genuine limit reached).
      - If within iteration budget with non-redundant tool call(s): routes to 'tools'.
    """
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 5)

    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None)

    # 1. No tool calls requested: Investigator completed narrative reasoning -> route to synthesis
    if not tool_calls:
        logger.info("[Graph Router] Investigator completed narrative reasoning -> routing to 'synthesis'")
        return "synthesis"

    # 2. Check evidence sufficiency
    evidence_sufficient = is_evidence_sufficient(state)

    # 3. Check redundancy of proposed tool calls
    all_redundant = all(
        check_tool_call_redundancy(call["name"], call.get("args", {}), state) is not None
        for call in tool_calls
    )

    # 4. If evidence is sufficient and all proposed tool calls are redundant:
    # Stop the investigative tool loop immediately and transition to synthesis
    if evidence_sufficient and all_redundant:
        logger.info(
            "[Graph Router] Gathered evidence is sufficient and all proposed tool calls are redundant. "
            "Stopping tool loop -> routing to 'synthesis'"
        )
        return "synthesis"

    # 5. Iteration budget checks:
    if iteration_count > max_iterations:
        if evidence_sufficient:
            # If evidence needed for synthesis is already available, do NOT fail with max_iterations
            logger.info(
                f"[Graph Router] Iteration limit ({max_iterations}) exceeded but sufficient evidence is in hand "
                f"({state.get('tools_used', [])}). Transitioning to 'synthesis' for report formulation."
            )
            return "synthesis"
        else:
            # Iteration limit genuinely reached before sufficient evidence was available
            logger.warning(
                f"[Graph Router] Max iterations ({max_iterations}) exceeded before sufficient evidence was gathered "
                f"(tools used: {state.get('tools_used', [])}). Halting -> 'max_iterations'"
            )
            return "max_iterations"

    # 6. Within iteration budget and has non-redundant tool call(s) -> proceed to tools
    return "tools"


def route_after_critic(state: InvestigationState) -> str:
    """Conditional routing edge after Critic node evaluation.

    - If Critic PASSED: routes to END.
    - If Critic FAILED:
      - If revision_count < max_revisions: routes to 'revision'.
      - If revision_count >= max_revisions: logs warning and halts -> END.
    """
    critic_status = state.get("critic_status")
    critic_result = state.get("critic_result")

    passed = (critic_status == "PASS") or (critic_result is not None and critic_result.passed)
    if passed:
        logger.info("[Graph Router] Critic evaluation PASSED -> Concluding investigation at END")
        return END

    rev_count = state.get("revision_count", 0)
    max_rev = state.get("max_revisions", 2)

    if rev_count < max_rev:
        logger.info(f"[Graph Router] Critic evaluation FAILED -> Routing to revision ({rev_count + 1}/{max_rev})")
        return "revision"

    logger.warning(
        f"[Graph Router] Critic evaluation FAILED but maximum revisions ({max_rev}) reached. Halting loop -> END"
    )
    return END


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------

def build_investigation_graph(
    llm: BaseChatModel,
    statement: TransactionStatement,
    include_rag: bool = True,
    rag_service: Optional[Any] = None,
    include_profile: bool = True,
    include_network: bool = True,
    enable_critic: bool = True,
    critic_llm: Optional[BaseChatModel] = None,
    max_context_tokens: Optional[int] = None,
) -> CompiledStateGraph:
    r"""Build and compile the LangGraph StateGraph workflow for a statement investigation.

    Target Graph Topology (with Critic & Revision Loop):
            START
              │
              ▼
        Investigator ◄───────────────┐
              │                      │
       (tool calls?)                 │
           /     \                   │
     tools        synthesis          │
       │              │              │
       └────► agent   ▼              │
                    critic           │
                   /      \          │
                PASS      FAIL       │
                 │          │        │
                END      revision ───┘

    Args:
        llm: Configured BaseChatModel instance for Investigator role.
        statement: Validated TransactionStatement under investigation.
        include_rag: Whether to register and expose AML knowledge retrieval tool (default True).
        rag_service: Optional RAGService instance.
        include_profile: Whether to register customer profiling tool (default True).
        include_network: Whether to register network analysis tool (default True).
        enable_critic: Whether to include the Critic and Revision nodes (default True).
        critic_llm: Optional separate BaseChatModel instance for Critic role.
        max_context_tokens: Maximum token budget for LLM context window.

    Returns:
        CompiledStateGraph instance ready for invocation.
    """
    registry = ToolRegistry.from_statement(
        statement,
        include_rag=include_rag,
        rag_service=rag_service,
        include_profile=include_profile,
        include_network=include_network,
    )
    tools = registry.get_tools()
    tools_by_name = {t.name: t for t in tools}

    if not hasattr(llm, "bind_tools"):
        raise AgentConfigurationError(f"Configured LLM ({type(llm)}) does not support tool binding.")

    llm_with_tools = llm.bind_tools(tools)

    context_budget = max_context_tokens or get_settings().llm_max_context_tokens
    agent_node = create_agent_node(llm_with_tools, max_context_tokens=context_budget, tools=tools)
    tool_node = create_tool_node(tools_by_name)

    builder = StateGraph(InvestigationState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_edge("tools", "agent")

    # Add Max Iterations node to handle cases where agent exceeds iteration budget
    max_iter_node = create_max_iterations_node(statement)
    builder.add_node("max_iterations", max_iter_node)
    builder.add_edge("max_iterations", END)

    if enable_critic:
        synthesis_node = create_synthesis_node(statement)
        critic_node = create_critic_node(statement, critic_llm=critic_llm)
        revision_node = create_revision_node()

        builder.add_node("synthesis", synthesis_node)
        builder.add_node("critic", critic_node)
        builder.add_node("revision", revision_node)

        builder.add_edge("synthesis", "critic")
        builder.add_edge("revision", "agent")

        builder.add_conditional_edges(
            "agent",
            should_continue_investigator,
            {
                "tools": "tools",
                "synthesis": "synthesis",
                "max_iterations": "max_iterations",
                END: END,
            },
        )

        builder.add_conditional_edges(
            "critic",
            route_after_critic,
            {
                "revision": "revision",
                END: END,
            },
        )
    else:
        builder.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END,
            },
        )

    compiled = builder.compile()
    logger.debug(f"Compiled LangGraph investigation workflow for '{statement.customer_name}' (critic={enable_critic})")
    return compiled
