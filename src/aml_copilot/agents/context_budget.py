"""Deterministic LLM Context Budgeting and Payload Optimization for AML Investigations.

Manages token budget constraints to prevent 413 rate limit errors (such as Groq's 8,000 TPM limit)
while strictly preserving:
- AML compliance safety instructions
- Traceable factual transaction evidence (IDs, amounts, dates, counterparties)
- RAG source attributions
- Observable network patterns and customer profiling metrics
"""

import json
import math
import re
from typing import Any, List, Optional, Sequence, Tuple
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from pydantic import BaseModel, Field

from aml_copilot.logger import get_logger

logger = get_logger(__name__)


class ContextBudgetReport(BaseModel):
    """Telemetry report describing context budgeting decisions."""

    budget_limit: int
    initial_estimated_tokens: int
    final_estimated_tokens: int
    reduction_applied: bool
    stages_applied: List[str] = Field(default_factory=list)


def estimate_tokens(
    messages: Sequence[BaseMessage],
    tools: Optional[Sequence[Any]] = None,
) -> int:
    """Heuristically estimate input token count without assuming a specific tokenizer.

    Standard rule of thumb: ~4 characters per token + message envelope overhead.
    """
    total_chars = 0

    for msg in messages:
        # Message content
        if isinstance(msg.content, str):
            total_chars += len(msg.content)
        elif isinstance(msg.content, list):
            for part in msg.content:
                if isinstance(part, dict):
                    total_chars += len(json.dumps(part))
                elif isinstance(part, str):
                    total_chars += len(part)
                else:
                    total_chars += len(str(part))
        else:
            total_chars += len(str(msg.content or ""))

        # Tool calls payload on AIMessage
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                total_chars += len(tc.get("name", ""))
                total_chars += len(json.dumps(tc.get("args", {})))

        # Envelope overhead (~4 tokens / 16 chars per message)
        total_chars += 16

    # Tool definition schemas overhead if bound
    if tools:
        for tool in tools:
            name = getattr(tool, "name", "")
            desc = getattr(tool, "description", "")
            total_chars += len(name) + len(desc) + 120

    return max(1, math.ceil(total_chars / 4.0))


def compact_tool_output(tool_name: str, output: Any) -> str:
    """Transform raw tool output into a concise, evidence-dense representation for LLM context.

    Preserves exact transaction IDs, dates, amounts, counterparties, and signals
    while stripping repetitive metadata and voluminous normal feature records.
    """
    if isinstance(output, str):
        try:
            data = json.loads(output)
        except Exception:
            return output
    elif isinstance(output, dict):
        data = output
    else:
        return str(output)

    # 1. detect_anomalies
    if tool_name == "detect_anomalies":
        compact_rules = []
        for r in data.get("rule_signals", []):
            compact_rules.append({
                "rule_id": r.get("rule_id"),
                "severity": r.get("severity"),
                "txns": r.get("transaction_ids", []),
                "summary": r.get("explanation", "")[:180],
            })

        # Only retain anomalous records with their score
        compact_anomalies = []
        for a in data.get("anomaly_signals", []):
            if a.get("is_anomaly"):
                top_feats = {
                    k: round(v, 2)
                    for k, v in a.get("feature_context", {}).items()
                    if k in ["amount", "balance_change", "rolling_volume_7d", "amount_to_median_ratio"]
                }
                compact_anomalies.append({
                    "txn": a.get("transaction_id"),
                    "score": round(a.get("anomaly_score", 0.0), 4),
                    "features": top_feats,
                })

        compact_payload = {
            "total_rules": data.get("total_rule_signals", len(compact_rules)),
            "total_anomalies": data.get("total_anomaly_signals", len(compact_anomalies)),
            "flagged_ids": data.get("flagged_transaction_ids", []),
            "rules": compact_rules,
            "anomalies": compact_anomalies,
        }
        return json.dumps(compact_payload, default=str)

    # 2. analyze_transaction_network
    elif tool_name == "analyze_transaction_network":
        compact_patterns = []
        for p in data.get("observable_patterns", []):
            compact_patterns.append({
                "pattern": p.get("pattern_name"),
                "description": p.get("description"),
                "nodes": p.get("involved_nodes", []),
                "txns": p.get("supporting_transaction_ids", []),
            })

        compact_edges = []
        for e in data.get("edges", []):
            compact_edges.append({
                "source": e.get("source"),
                "target": e.get("target"),
                "amount": e.get("weight"),
                "count": e.get("transaction_count"),
                "txns": e.get("transaction_ids", []),
            })

        compact_payload = {
            "customer": data.get("customer_name"),
            "patterns": compact_patterns,
            "flows": compact_edges,
            "metrics": {
                "unique_counterparties": data.get("metrics", {}).get("unique_counterparties"),
                "degree": data.get("metrics", {}).get("customer_degree"),
            },
        }
        return json.dumps(compact_payload, default=str)

    # 3. search_aml_knowledge
    elif tool_name == "search_aml_knowledge":
        # Format compact knowledge excerpts preserving source attribution
        compact_results = []
        for r in data.get("results", []):
            compact_results.append({
                "source": r.get("source"),
                "section": r.get("section", "General"),
                "guidance": r.get("content", "")[:350],
            })

        compact_payload = {
            "query": data.get("query"),
            "sources": data.get("sources", []),
            "excerpts": compact_results[:2],  # Keep top 2 most relevant excerpts
        }
        return json.dumps(compact_payload, default=str)

    # 4. get_customer_profile
    elif tool_name == "get_customer_profile":
        compact_payload = {
            "customer": data.get("customer_name"),
            "turnover": {
                "txns": data.get("total_transactions"),
                "credits": data.get("total_credits"),
                "debits": data.get("total_debits"),
                "net_flow": data.get("net_cash_flow"),
                "max_txn": data.get("maximum_transaction"),
            },
            "flow_type": data.get("dominant_flow_type"),
            "counterparties": data.get("unique_counterparties"),
            "active_days": data.get("active_days"),
            "indicators": data.get("indicators", []),
        }
        return json.dumps(compact_payload, default=str)

    # 5. search_transactions
    elif tool_name == "search_transactions":
        txns = data.get("transactions", [])
        compact_txns = []
        for t in txns:
            compact_txns.append({
                "id": t.get("transaction_id"),
                "date": t.get("date"),
                "amount": t.get("amount"),
                "type": "credit" if t.get("is_credit") else "debit",
                "counterparty": t.get("counterparty"),
                "balance": t.get("balance"),
            })
        compact_payload = {
            "total_matched": data.get("total_matched", len(txns)),
            "transactions": compact_txns,
        }
        return json.dumps(compact_payload, default=str)

    # 6. analyze_transactions / get_transaction_statistics
    elif tool_name in ["analyze_transactions", "get_transaction_statistics"]:
        compact_payload = {
            "customer": data.get("customer_name"),
            "transactions": data.get("transaction_count"),
            "credits": data.get("total_credits", data.get("credit_sum")),
            "debits": data.get("total_debits", data.get("debit_sum")),
            "net_flow": data.get("net_cash_flow", data.get("net_flow")),
            "top_counterparties": data.get("top_counterparties", [])[:5],
            "unique_counterparties": data.get("unique_counterparties_count", len(data.get("unique_counterparties", []))),
        }
        return json.dumps(compact_payload, default=str)

    # Default fallback
    return json.dumps(data, default=str)


def prepare_context_for_llm(
    messages: Sequence[BaseMessage],
    max_tokens: int = 6000,
    tools: Optional[Sequence[Any]] = None,
) -> Tuple[List[BaseMessage], ContextBudgetReport]:
    """Inspect and adjust message context to fit within the configured LLM token budget.

    Progressive reduction stages:
    1. Compact bulky ToolMessage JSON payloads.
    2. Summarize stale intermediate tool outputs from older iterations.
    3. Prune excess RAG chunks while preserving top source attribution.
    4. Guardrail truncation for extreme payload anomalies.

    Never deletes SystemMessage or initial HumanMessage.
    """
    initial_tokens = estimate_tokens(messages, tools=tools)

    if initial_tokens <= max_tokens:
        report = ContextBudgetReport(
            budget_limit=max_tokens,
            initial_estimated_tokens=initial_tokens,
            final_estimated_tokens=initial_tokens,
            reduction_applied=False,
            stages_applied=[],
        )
        logger.info(
            f"[ContextBudget] context_budget={report.budget_limit} "
            f"context_estimated_tokens={report.final_estimated_tokens} "
            f"context_reduction_applied=false"
        )
        return list(messages), report

    # Needs reduction
    stages_applied: List[str] = []
    processed_messages: List[BaseMessage] = list(messages)

    # Stage 1: Compact tool messages
    new_msgs: List[BaseMessage] = []
    for msg in processed_messages:
        if isinstance(msg, ToolMessage):
            # Attempt compacting known tool formats
            content_str = str(msg.content)
            # Try to identify tool type or format json
            try:
                raw_json = json.loads(content_str)
                # Check signatures
                if "rule_signals" in raw_json or "anomaly_signals" in raw_json:
                    content_str = compact_tool_output("detect_anomalies", raw_json)
                elif "observable_patterns" in raw_json and "nodes" in raw_json:
                    content_str = compact_tool_output("analyze_transaction_network", raw_json)
                elif "formatted_evidence" in raw_json or "sources" in raw_json:
                    content_str = compact_tool_output("search_aml_knowledge", raw_json)
                elif "indicators" in raw_json and "turnover" in raw_json:
                    content_str = compact_tool_output("get_customer_profile", raw_json)
                elif "transactions" in raw_json and "total_matched" in raw_json:
                    content_str = compact_tool_output("search_transactions", raw_json)
                new_msg = ToolMessage(
                    content=content_str,
                    tool_call_id=msg.tool_call_id,
                    name=getattr(msg, "name", None),
                )
                new_msgs.append(new_msg)
            except Exception:
                new_msgs.append(msg)
        else:
            new_msgs.append(msg)

    processed_messages = new_msgs
    stages_applied.append("compact_tool_messages")
    current_tokens = estimate_tokens(processed_messages, tools=tools)

    # Stage 2: Summarize older intermediate tool results if still over budget
    if current_tokens > max_tokens:
        # Find indices of ToolMessages
        tool_indices = [i for i, m in enumerate(processed_messages) if isinstance(m, ToolMessage)]
        # If more than 3 tool messages, condense older ones, keeping latest 2
        if len(tool_indices) > 2:
            stale_indices = tool_indices[:-2]
            summarized_msgs: List[BaseMessage] = []
            for i, msg in enumerate(processed_messages):
                if i in stale_indices:
                    # Replace with concise summary preserving transaction IDs
                    content_str = str(msg.content)
                    cited_txns = sorted(list(set(re.findall(r"\bTXN\d+\b", content_str))))
                    summary = f"[Intermediate Tool Evidence Recorded. Verified Txns: {', '.join(cited_txns) if cited_txns else 'none'}]"
                    summarized_msgs.append(
                        ToolMessage(
                            content=summary,
                            tool_call_id=cast_call_id(msg),
                            name=getattr(msg, "name", None),
                        )
                    )
                else:
                    summarized_msgs.append(msg)
            processed_messages = summarized_msgs
            stages_applied.append("summarize_stale_history")
            current_tokens = estimate_tokens(processed_messages, tools=tools)

    # Stage 3: Trim individual large ToolMessages if still over budget
    if current_tokens > max_tokens:
        trimmed_msgs: List[BaseMessage] = []
        for msg in processed_messages:
            if isinstance(msg, ToolMessage) and len(str(msg.content)) > 1200:
                # Truncate content while preserving referenced transaction IDs
                text = str(msg.content)
                cited_txns = sorted(list(set(re.findall(r"\bTXN\d+\b", text))))
                truncated_text = text[:1000] + f"... [Truncated for context budget. Key Txns: {', '.join(cited_txns)}]"
                trimmed_msgs.append(
                    ToolMessage(
                        content=truncated_text,
                        tool_call_id=cast_call_id(msg),
                        name=getattr(msg, "name", None),
                    )
                )
            else:
                trimmed_msgs.append(msg)
        processed_messages = trimmed_msgs
        stages_applied.append("trim_large_tool_messages")
        current_tokens = estimate_tokens(processed_messages, tools=tools)

    # Stage 4: Condense prior drafts in AIMessages from earlier revision cycles
    if current_tokens > max_tokens:
        condensed_msgs: List[BaseMessage] = []
        for i, msg in enumerate(processed_messages):
            # If an AIMessage is not the latest message in the sequence and has substantial text (a prior draft)
            if isinstance(msg, AIMessage) and i < len(processed_messages) - 1:
                content_str = str(msg.content or "")
                if len(content_str) > 600:
                    cited_txns = sorted(list(set(re.findall(r"\bTXN\d+\b", content_str))))
                    summary = (
                        content_str[:500]
                        + f"\n... [Prior draft condensed for context budget. Cited Txns: {', '.join(cited_txns)}]"
                    )
                    condensed_msgs.append(
                        AIMessage(
                            content=summary,
                            tool_calls=getattr(msg, "tool_calls", []),
                            id=getattr(msg, "id", None),
                        )
                    )
                else:
                    condensed_msgs.append(msg)
            else:
                condensed_msgs.append(msg)
        processed_messages = condensed_msgs
        stages_applied.append("condense_prior_drafts")
        current_tokens = estimate_tokens(processed_messages, tools=tools)

    # Stage 5: Condense older revision HumanMessages if still over budget
    if current_tokens > max_tokens:
        rev_indices = [
            i for i, m in enumerate(processed_messages)
            if isinstance(m, HumanMessage) and "[CRITIC AUDIT FEEDBACK" in str(m.content)
        ]
        if len(rev_indices) > 1:
            stale_rev_indices = rev_indices[:-1]
            trimmed_rev_msgs: List[BaseMessage] = []
            for i, msg in enumerate(processed_messages):
                if i in stale_rev_indices:
                    trimmed_rev_msgs.append(
                        HumanMessage(content="[Prior Critic Revision Feedback addressed in history.]")
                    )
                else:
                    trimmed_rev_msgs.append(msg)
            processed_messages = trimmed_rev_msgs
            stages_applied.append("condense_stale_revisions")
            current_tokens = estimate_tokens(processed_messages, tools=tools)

    # Stage 6: Hard budget enforcement — condense messages if still above max_tokens
    if current_tokens > max_tokens:
        final_pass_msgs: List[BaseMessage] = []
        for msg in processed_messages:
            if isinstance(msg, ToolMessage) and len(str(msg.content)) > 400:
                txt = str(msg.content)[:350] + "... [Condensed]"
                final_pass_msgs.append(
                    ToolMessage(content=txt, tool_call_id=cast_call_id(msg), name=getattr(msg, "name", None))
                )
            elif isinstance(msg, AIMessage) and len(str(msg.content)) > 500:
                txt = str(msg.content)[:450] + "... [Condensed]"
                final_pass_msgs.append(
                    AIMessage(content=txt, tool_calls=getattr(msg, "tool_calls", []), id=getattr(msg, "id", None))
                )
            else:
                final_pass_msgs.append(msg)
        processed_messages = final_pass_msgs
        stages_applied.append("hard_budget_enforcement")
        current_tokens = estimate_tokens(processed_messages, tools=tools)

    report = ContextBudgetReport(
        budget_limit=max_tokens,
        initial_estimated_tokens=initial_tokens,
        final_estimated_tokens=current_tokens,
        reduction_applied=True,
        stages_applied=stages_applied,
    )
    logger.info(
        f"[ContextBudget] context_budget={report.budget_limit} "
        f"context_estimated_tokens={report.final_estimated_tokens} "
        f"context_reduction_applied=true"
    )

    return processed_messages, report


def cast_call_id(msg: Any) -> str:
    """Safely extract tool_call_id from ToolMessage."""
    return getattr(msg, "tool_call_id", "call_default")
