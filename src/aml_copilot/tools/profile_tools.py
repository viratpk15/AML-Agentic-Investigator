"""Customer profiling tool for investigation agents."""

from typing import Any, Dict
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from aml_copilot.logger import get_logger
from aml_copilot.models.transaction import TransactionStatement
from aml_copilot.profiling.profiler import build_customer_profile

logger = get_logger(__name__)


class GetCustomerProfileInput(BaseModel):
    """Input parameters for generating a customer behavioral profile."""

    include_indicators: bool = Field(
        default=True,
        description="Whether to include deterministic behavioral classification indicators",
    )


def execute_get_customer_profile(
    statement: TransactionStatement,
    include_indicators: bool = True,
) -> Dict[str, Any]:
    """Execute customer profiling over the statement and return structured data.

    Args:
        statement: Validated TransactionStatement under review.
        include_indicators: Whether to include behavioral indicators.

    Returns:
        Dictionary representation of CustomerProfile.
    """
    profile = build_customer_profile(statement)
    dumped = profile.model_dump()
    if not include_indicators:
        dumped["indicators"] = []
    return dumped


def create_get_customer_profile_tool(statement: TransactionStatement) -> StructuredTool:
    """Create a LangChain StructuredTool for customer behavioral profiling.

    Args:
        statement: Validated TransactionStatement bound to the agent.

    Returns:
        StructuredTool configured for model tool calling.
    """
    def _tool_fn(include_indicators: bool = True) -> Dict[str, Any]:
        return execute_get_customer_profile(statement, include_indicators=include_indicators)

    return StructuredTool.from_function(
        func=_tool_fn,
        name="get_customer_profile",
        description=(
            "Retrieve a comprehensive, deterministic behavioral profile of the customer. "
            "Returns aggregate volume metrics, cash flow (credits, debits, net flow), average/median/max amounts, "
            "dominant flow direction, unique and newly observed counterparty counts, active days, transaction frequency, "
            "peak transaction details, and objective behavioral indicators (e.g. high-value activity, rapid fund movement). "
            "Use this tool to understand the customer's overall transactional baseline and behavioral patterns."
        ),
        args_schema=GetCustomerProfileInput,
    )
