"""Revision node incorporating structured Critic feedback into the investigation loop."""

from typing import Any, Callable, Dict, List
from langchain_core.messages import HumanMessage

from aml_copilot.agents.state import InvestigationState, emit_investigation_event
from aml_copilot.logger import get_logger

logger = get_logger(__name__)


def create_revision_node() -> Callable[[InvestigationState], Dict[str, Any]]:
    """Create the Revision Node function.

    Responsibilities:
    1. Read Critic feedback and issue descriptions from state.
    2. Increment the revision_count counter.
    3. Formulate an actionable feedback message for the Investigator agent.
    4. Append the revision request to dialogue history so the agent can gather missing evidence or correct claims.
    """

    def revision_node(state: InvestigationState) -> Dict[str, Any]:
        curr_revision = state.get("revision_count", 0) + 1
        max_revisions = state.get("max_revisions", 2)
        feedback = state.get("critic_feedback") or "Please address identified inaccuracies and provide supporting evidence."

        logger.info(f"[Graph: Revision Node] Initiating revision cycle {curr_revision} of {max_revisions}")
        emit_investigation_event(
            state,
            event_type="REVISION_STARTED",
            node="revision",
            message=f"Self-correction loop triggered: Initiating revision cycle {curr_revision}/{max_revisions}...",
            metadata={"revision": curr_revision, "max_revisions": max_revisions, "feedback": feedback[:200]},
        )

        revision_prompt = (
            f"[CRITIC AUDIT FEEDBACK — REVISION CYCLE {curr_revision}/{max_revisions}]\n"
            f"The Senior Compliance Critic evaluated your previous draft and rejected it for the following reasons:\n\n"
            f"{feedback}\n\n"
            "Actionable Instructions:\n"
            "1. If missing evidence or specific transaction details were noted, call the appropriate tools (e.g. search_transactions) to verify them.\n"
            "2. Remove or correct any hallucinated, inaccurate, or unverified transaction IDs, dates, or amounts.\n"
            "3. Ensure all language remains strictly objective and non-judgmental (do not declare criminal guilt or demand account actions).\n"
            "4. Provide a revised, fully grounded investigation narrative addressing each point above."
        )

        revision_message = HumanMessage(content=revision_prompt)

        emit_investigation_event(
            state,
            event_type="REVISION_COMPLETED",
            node="revision",
            message=f"Revision cycle {curr_revision} feedback incorporated. Re-routing dialogue to Investigator.",
            metadata={"revision": curr_revision},
        )

        return {
            "messages": [revision_message],
            "revision_count": curr_revision,
            "final_response": "",  # Clear previous response to trigger fresh synthesis
        }

    return revision_node
