"""First single tool-using AML investigation agent orchestrated via LangGraph."""

import re
from typing import Any, Dict, List, Optional, cast
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from aml_copilot.agents.graph import build_investigation_graph
from aml_copilot.agents.state import (
    InvestigationRequest,
    InvestigationResult,
    InvestigationState,
    InvestigationStatus,
    ToolExecutionRecord,
)
from aml_copilot.config import Settings, get_settings
from aml_copilot.exceptions import AgentConfigurationError
from aml_copilot.logger import get_logger
from aml_copilot.models.transaction import TransactionStatement
from aml_copilot.rag.service import RAGService

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert Anti-Money Laundering (AML) Senior Compliance Copilot assisting human analysts.
Your duty is to investigate bank transaction activity objectively, identify unusual activity, evaluate risk signals, and present clear supporting evidence.

CRITICAL COMPLIANCE RULES:
1. You MUST NOT declare that a customer is guilty of money laundering, fraud, or criminal acts. You produce objective investigation signals and risk indicators for human review.
2. Use precise, non-judgmental professional compliance terms: "unusual activity", "investigation signal", "potential risk indicator", "requires review", "supporting evidence".
3. DO NOT fabricate, hallucinate, or assume transaction IDs, dates, or amounts. You MUST retrieve all factual evidence strictly using your available tools.
4. When citing evidence, always specify exact transaction IDs (e.g. TXN005), dates, counterparties, and amounts.
5. Highlight limitations, data boundaries, and uncertainties in your findings.
6. STRICT DETECTION GROUNDING: When reporting Isolation Forest anomalies, ONLY cite the exact transaction IDs flagged with 'is_anomaly': true in the detect_anomalies tool output. NEVER assume sequential transaction IDs (such as TXN401, TXN402, TXN403...) are anomalies. When reporting rule triggers, ONLY cite the exact supporting transaction IDs returned by that rule.

INVESTIGATION & GROUNDING WORKFLOW:
- Use available tools to retrieve factual statement evidence, detection signals, customer profile, network relationships, and AML reference typologies.
- Maintain a strict separation between customer facts and external reference knowledge:
  * Observed Evidence: Factual transaction records, customer profile metrics, or network links (IDs, dates, amounts, counterparties).
  * Relevant AML Reference: Retrieved knowledge concepts and typologies from the AML reference library.
  * Interpretation: Professional explanation of why the observed facts align or do not align with the reference typology.
  * Limitations: Explicit statement that the observed pattern does not prove illicit activity or guilt.

INVESTIGATION EFFICIENCY & STOPPING RULES:
- Aim to gather necessary evidence in 2-3 focused tool calls (e.g. detect_anomalies to evaluate rules and anomalies, followed by get_customer_profile or analyze_transaction_network, and search_aml_knowledge if reference typologies apply).
- Do NOT perform repetitive, redundant, or broad searches for transactions that have already been identified or retrieved.
- Once sufficient evidence is in hand to answer the investigation question, STOP calling tools and proceed directly to synthesize your draft findings narrative.
- Respect any [EVIDENCE SUFFICIENCY ADVISORY] notes by immediately concluding tool usage and synthesizing your report.
"""

STANDARD_AGENT_DISCLAIMER = (
    "Investigation findings and risk signals are generated for compliance review purposes only. "
    "They do not establish legal guilt, fraud, or criminal liability."
)


class InvestigationAgent:
    """Tool-using AML Investigation Agent powered by a compiled LangGraph workflow.

    Orchestrates the decision loop:
    START -> agent -> (conditional: tool calls?) -> tools -> agent -> END.
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        max_iterations: Optional[int] = None,
        rag_service: Optional[RAGService] = None,
        include_rag: bool = True,
        include_profile: bool = True,
        include_network: bool = True,
        enable_critic: bool = True,
        max_revisions: int = 2,
        critic_llm: Optional[BaseChatModel] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.max_iterations = max_iterations or self.settings.llm_max_iterations
        self.llm = llm or self._build_default_llm()
        self.rag_service = rag_service
        self.include_rag = include_rag
        self.include_profile = include_profile
        self.include_network = include_network
        self.enable_critic = enable_critic
        self.max_revisions = max_revisions
        self.critic_llm = critic_llm

    def _build_default_llm(self) -> BaseChatModel:
        """Construct a FailoverLLM from configured LLM_PROVIDER + LLM_FALLBACK_PROVIDERS.

        Raises:
            AgentConfigurationError: If no provider could be initialised.
        """
        from aml_copilot.llm.factory import LLMFactory
        from aml_copilot.llm.failover import FailoverLLM

        try:
            factory = LLMFactory(settings=self.settings)
            failover_llm = FailoverLLM.from_factory(factory=factory)
            provider_chain = " → ".join(failover_llm.provider_names)
            logger.info(f"[InvestigationAgent] Provider chain: {provider_chain}")
            return failover_llm
        except Exception as exc:
            msg = f"Failed to initialize LLM provider(s): {exc}"
            logger.error(msg)
            raise AgentConfigurationError(msg) from exc


    def investigate(
        self,
        statement: TransactionStatement,
        question: str,
        max_iterations: Optional[int] = None,
        event_callback: Optional[Any] = None,
        investigation_id: Optional[str] = None,
    ) -> InvestigationResult:
        """Execute the LangGraph investigation workflow on a customer statement.

        Args:
            statement: Validated TransactionStatement.
            question: Analyst investigation question or query.
            max_iterations: Optional limit on reasoning iterations.
            event_callback: Optional callable for streaming investigation events.
            investigation_id: Optional tracking identifier for event correlation.

        Returns:
            InvestigationResult with response, tools used, and cited evidence.
        """
        iter_limit = max_iterations or self.max_iterations

        # 1. Initialize dialogue state
        messages: List[BaseMessage] = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Customer Statement: '{statement.customer_name or 'Unknown'}', "
                    f"Account: '{statement.account_number or 'Unknown'}', "
                    f"Period: '{statement.statement_period or 'Unknown'}', "
                    f"Total Transactions: {statement.total_transactions}.\n\n"
                    f"Investigation Question: {question}"
                )
            ),
        ]

        initial_state: InvestigationState = {
            "messages": messages,
            "statement": statement,
            "question": question,
            "tools_used": [],
            "tool_calls": [],
            "knowledge_sources": [],
            "customer_profile": None,
            "network_analysis": None,
            "investigation_plan": [],
            "findings": [],
            "draft": None,
            "critic_result": None,
            "critic_status": None,
            "critic_feedback": None,
            "revision_count": 0,
            "max_revisions": self.max_revisions,
            "enable_critic": self.enable_critic,
            "iteration_count": 0,
            "max_iterations": iter_limit,
            "final_response": "",
            "event_callback": event_callback,
            "investigation_id": investigation_id,
        }

        from aml_copilot.agents.state import emit_investigation_event

        emit_investigation_event(
            initial_state,
            event_type="INVESTIGATION_STARTED",
            message=f"Starting investigation for customer '{statement.customer_name or 'Unknown'}'...",
            metadata={
                "customer_name": statement.customer_name,
                "total_transactions": statement.total_transactions,
            },
        )

        try:
            # 2. Wire event callback + investigation_id into FailoverLLM for SSE telemetry
            llm_for_graph = self.llm
            from aml_copilot.llm.failover import FailoverLLM

            if isinstance(llm_for_graph, FailoverLLM):
                llm_for_graph = llm_for_graph.with_investigation_context(
                    investigation_id=investigation_id,
                    event_callback=event_callback,
                )
                emit_investigation_event(
                    initial_state,
                    event_type="LLM_PROVIDER_ATTEMPT",
                    message=(
                        f"Provider chain active: "
                        f"{' → '.join(llm_for_graph.provider_names)}"
                    ),
                    metadata={"providers": llm_for_graph.provider_names},
                )

            # Determine context budget: prefer provider-specific limit if available
            context_budget = self.settings.llm_max_context_tokens
            if isinstance(llm_for_graph, FailoverLLM) and llm_for_graph.providers:
                primary_cfg = llm_for_graph.providers[0][0]
                context_budget = primary_cfg.max_context_tokens

            # 3. Compile and execute LangGraph workflow
            graph = build_investigation_graph(
                llm=llm_for_graph,
                statement=statement,
                include_rag=self.include_rag,
                rag_service=self.rag_service,
                include_profile=self.include_profile,
                include_network=self.include_network,
                enable_critic=self.enable_critic,
                critic_llm=self.critic_llm,
                max_context_tokens=context_budget,
            )
            final_state: InvestigationState = cast(
                InvestigationState,
                graph.invoke(initial_state),
            )


            # 3. Detect completion vs max_iterations state
            is_max_iter = (
                final_state.get("status") == "MAX_ITERATIONS_REACHED"
                or final_state.get("is_partial") is True
                or (final_state.get("iteration_count", 0) > iter_limit and not final_state.get("draft"))
            )

            # 4. Extract final response
            final_response = final_state.get("final_response", "")
            if not final_response:
                last_msg = final_state["messages"][-1]
                if isinstance(last_msg, AIMessage) and last_msg.content and not getattr(last_msg, "tool_calls", None):
                    final_response = str(last_msg.content)
                elif final_state.get("draft") and final_state["draft"].raw_response:
                    final_response = final_state["draft"].raw_response
                else:
                    final_response = (
                        "The investigation reached maximum reasoning iterations before full synthesis. "
                        "Please review the executed tool outputs for preliminary findings. "
                        "Mandatory human compliance review is required."
                    )

            # 5. Extract verified transaction IDs referenced in final response
            actual_txn_ids = {t.transaction_id for t in statement.transactions if t.transaction_id}
            referenced_ids = [tid for tid in actual_txn_ids if tid in final_response]

            warnings = [STANDARD_AGENT_DISCLAIMER]
            if statement.total_transactions < 10:
                warnings.append(
                    f"Customer statement has limited history ({statement.total_transactions} transactions)."
                )

            # If critic rejected and max revisions reached, append explicit limitation
            if final_state.get("critic_status") == "FAIL":
                warnings.append(
                    "Investigation draft concluded with unresolved Critic findings after reaching maximum revisions."
                )

            if is_max_iter:
                warnings.append(
                    f"Investigation reached maximum reasoning iterations ({iter_limit}) before completing full synthesis."
                )
                warnings.append(
                    "Investigation is partial and incomplete. Mandatory human compliance review is required."
                )

                emit_investigation_event(
                    final_state,
                    event_type="INVESTIGATION_MAX_ITERATIONS",
                    node="investigator",
                    status="MAX_ITERATIONS_REACHED",
                    message=(
                        f"Investigation halted: Maximum reasoning iterations ({iter_limit}) reached before synthesis. "
                        "Partial evidence preserved; human review required."
                    ),
                    metadata={
                        "iteration_count": final_state.get("iteration_count", 0),
                        "max_iterations": iter_limit,
                        "tools_used": final_state.get("tools_used", []),
                    },
                )

                investigation_status = "MAX_ITERATIONS_REACHED"
                is_partial = True
            else:
                emit_investigation_event(
                    final_state,
                    event_type="REPORT_GENERATED",
                    message="Investigation synthesis concluded. Preparing audit trail artifacts...",
                )
                emit_investigation_event(
                    final_state,
                    event_type="INVESTIGATION_COMPLETED",
                    message=f"Investigation workflow concluded ({len(final_state.get('tools_used', []))} tools executed, {final_state.get('revision_count', 0)} revisions).",
                )
                investigation_status = InvestigationStatus("NORMAL_COMPLETION")
                is_partial = False

            findings_list = final_state.get("findings")

            return InvestigationResult(
                question=question,
                response=final_response,
                status=investigation_status,
                is_partial=is_partial,
                tools_used=final_state.get("tools_used") or [],
                tool_calls=final_state.get("tool_calls") or [],
                referenced_transaction_ids=sorted(list(referenced_ids)),
                knowledge_sources=final_state.get("knowledge_sources") or [],
                customer_profile=final_state.get("customer_profile"),
                network_analysis=final_state.get("network_analysis"),
                findings=findings_list if findings_list is not None else [],
                draft=final_state.get("draft"),
                critic_result=final_state.get("critic_result"),
                critic_status=final_state.get("critic_status"),
                revision_count=final_state.get("revision_count", 0),
                canonical_evidence=final_state.get("canonical_evidence"),
                limitations_warnings=warnings,
            )

        except Exception as exc:
            from aml_copilot.llm.exceptions import ProviderFailoverExhausted, ProviderError
            if isinstance(exc, ProviderFailoverExhausted):
                fail_status = "ALL_PROVIDERS_FAILED"
                event_type = "ALL_PROVIDERS_FAILED"
                err_msg = f"All configured LLM providers failed: {str(exc)}"
            elif isinstance(exc, ProviderError):
                fail_status = "PROVIDER_FAILURE"
                event_type = "PROVIDER_FAILURE"
                err_msg = f"LLM provider failure: {str(exc)}"
            else:
                fail_status = "INVESTIGATION_FAILED"
                event_type = "INVESTIGATION_FAILED"
                err_msg = f"Investigation execution failed: {str(exc)}"

            emit_investigation_event(
                initial_state,
                event_type=event_type,
                status=fail_status,
                message=err_msg,
                metadata={"error": str(exc), "status": fail_status},
            )
            raise exc


def run_investigation(
    statement: TransactionStatement,
    question: str,
    llm: Optional[BaseChatModel] = None,
    max_iterations: Optional[int] = None,
    rag_service: Optional[RAGService] = None,
    include_rag: bool = True,
    include_profile: bool = True,
    include_network: bool = True,
    enable_critic: bool = True,
    max_revisions: int = 2,
    critic_llm: Optional[BaseChatModel] = None,
    event_callback: Optional[Any] = None,
    investigation_id: Optional[str] = None,
) -> InvestigationResult:
    """Convenience helper to initialize an investigation agent and run a query."""
    agent = InvestigationAgent(
        llm=llm,
        max_iterations=max_iterations,
        rag_service=rag_service,
        include_rag=include_rag,
        include_profile=include_profile,
        include_network=include_network,
        enable_critic=enable_critic,
        max_revisions=max_revisions,
        critic_llm=critic_llm,
    )
    return agent.investigate(
        statement=statement,
        question=question,
        event_callback=event_callback,
        investigation_id=investigation_id,
    )
