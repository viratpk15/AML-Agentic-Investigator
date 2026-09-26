"""Network analysis tool for investigation agents."""

from typing import Any, Dict
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from aml_copilot.logger import get_logger
from aml_copilot.models.transaction import TransactionStatement
from aml_copilot.network.analysis import build_transaction_network

logger = get_logger(__name__)


class AnalyzeTransactionNetworkInput(BaseModel):
    """Input parameters for analyzing the customer transaction network."""

    include_patterns: bool = Field(
        default=True,
        description="Whether to include observable topological patterns and conduit relationship detections",
    )


def execute_analyze_transaction_network(
    statement: TransactionStatement,
    include_patterns: bool = True,
) -> Dict[str, Any]:
    """Execute network graph analysis over the statement and return structured topology data.

    Args:
        statement: Validated TransactionStatement under review.
        include_patterns: Whether to include observable patterns.

    Returns:
        Dictionary representation of NetworkAnalysisResult.
    """
    result = build_transaction_network(statement)
    dumped = result.model_dump()
    if not include_patterns:
        dumped["observable_patterns"] = []
    return dumped


def create_analyze_transaction_network_tool(statement: TransactionStatement) -> StructuredTool:
    """Create a LangChain StructuredTool for customer-counterparty network analysis.

    Args:
        statement: Validated TransactionStatement bound to the agent.

    Returns:
        StructuredTool configured for model tool calling.
    """
    def _tool_fn(include_patterns: bool = True) -> Dict[str, Any]:
        return execute_analyze_transaction_network(statement, include_patterns=include_patterns)

    return StructuredTool.from_function(
        func=_tool_fn,
        name="analyze_transaction_network",
        description=(
            "Construct a directed graph of the customer's transaction network with all counterparties using NetworkX. "
            "Returns graph nodes (entities, volumes, degrees), directed edges (flows, transaction counts, amounts, "
            "dates, transaction IDs), network topology metrics (customer degree, incoming/outgoing counterparties, "
            "degree centralities, largest counterparties), and observable topological patterns (dominant counterparties, "
            "rapid flows between counterparties, one-to-many relationships). "
            "Use this tool to analyze who the customer transacts with and map relationship structures."
        ),
        args_schema=AnalyzeTransactionNetworkInput,
    )
