"""Central registry for AML investigation tools."""

from typing import Dict, List, Optional
from langchain_core.tools import StructuredTool

from aml_copilot.logger import get_logger
from aml_copilot.models.transaction import TransactionStatement
from aml_copilot.network.analysis import build_transaction_network
from aml_copilot.profiling.profiler import build_customer_profile
from aml_copilot.rag.service import RAGService
from aml_copilot.tools.detection_tools import create_detect_anomalies_tool
from aml_copilot.tools.network_tools import create_analyze_transaction_network_tool
from aml_copilot.tools.profile_tools import create_get_customer_profile_tool
from aml_copilot.tools.rag_tools import create_search_aml_knowledge_tool
from aml_copilot.tools.transaction_tools import (
    create_analyze_transactions_tool,
    create_get_transaction_statistics_tool,
    create_search_transactions_tool,
)

logger = get_logger(__name__)


class ToolRegistry:
    """Central registry managing AML investigation tools and statement context.

    Provides a clean bridge to expose modular tools to LangChain agents and LangGraph orchestrators.
    """

    def __init__(
        self,
        statement: Optional[TransactionStatement] = None,
        rag_service: Optional[RAGService] = None,
        include_rag: bool = False,
        include_profile: bool = False,
        include_network: bool = False,
    ) -> None:
        self._statement = statement
        self._rag_service = rag_service
        self._tools: Dict[str, StructuredTool] = {}
        if statement is not None:
            self._initialize_statement_tools(statement)
        if include_rag:
            self.register_rag_tool(rag_service)
        if include_profile and statement is not None:
            self.register_profile_tool()
        if include_network and statement is not None:
            self.register_network_tool()

    @classmethod
    def from_statement(
        cls,
        statement: TransactionStatement,
        include_rag: bool = False,
        include_profile: bool = False,
        include_network: bool = False,
        include_all: bool = False,
        rag_service: Optional[RAGService] = None,
    ) -> "ToolRegistry":
        """Instantiate a registry initialized with a validated transaction statement."""
        if include_all:
            include_rag = True
            include_profile = True
            include_network = True

        return cls(
            statement=statement,
            rag_service=rag_service,
            include_rag=include_rag,
            include_profile=include_profile,
            include_network=include_network,
        )

    def register_rag_tool(self, rag_service: Optional[RAGService] = None) -> StructuredTool:
        """Register the search_aml_knowledge tool."""
        service = rag_service or self._rag_service
        tool = create_search_aml_knowledge_tool(rag_service=service)
        self.register_tool(tool)
        return tool

    def register_profile_tool(self) -> StructuredTool:
        """Register the get_customer_profile tool."""
        if self._statement is None:
            raise ValueError("Cannot initialize profile tool without an active statement.")
        tool = create_get_customer_profile_tool(self._statement)
        self.register_tool(tool)
        return tool

    def register_network_tool(self) -> StructuredTool:
        """Register the analyze_transaction_network tool."""
        if self._statement is None:
            raise ValueError("Cannot initialize network tool without an active statement.")
        tool = create_analyze_transaction_network_tool(self._statement)
        self.register_tool(tool)
        return tool

    def register_all_tools(self, rag_service: Optional[RAGService] = None) -> None:
        """Register all 7 investigation tools."""
        if self._statement is not None:
            self.register_profile_tool()
            self.register_network_tool()
        self.register_rag_tool(rag_service)

    def set_statement(self, statement: TransactionStatement) -> None:
        """Bind or update the active transaction statement and reinitialize tools."""
        self._statement = statement
        self._initialize_statement_tools(statement)

    @property
    def statement(self) -> Optional[TransactionStatement]:
        """Return the currently bound TransactionStatement, if any."""
        return self._statement

    def _initialize_statement_tools(self, statement: TransactionStatement) -> None:
        """Create and register the standard AML investigation tools for the statement."""
        self._tools.clear()

        analyze_tool = create_analyze_transactions_tool(statement)
        stats_tool = create_get_transaction_statistics_tool(statement)
        search_tool = create_search_transactions_tool(statement)
        detect_tool = create_detect_anomalies_tool(statement)

        for t in [analyze_tool, stats_tool, search_tool, detect_tool]:
            self._tools[t.name] = t

        logger.debug(
            f"Initialized {len(self._tools)} investigation tools for statement: "
            f"'{statement.customer_name or 'Unknown'}'"
        )

    def register_tool(self, tool: StructuredTool) -> None:
        """Register an additional or custom LangChain tool."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered custom tool: '{tool.name}'")

    def get_tool(self, name: str) -> Optional[StructuredTool]:
        """Retrieve a specific tool by programmatic name."""
        return self._tools.get(name)

    def get_tools(self) -> List[StructuredTool]:
        """Return a list of all registered LangChain tools ready for model binding."""
        return list(self._tools.values())

    @property
    def tool_names(self) -> List[str]:
        """List the names of all currently registered tools."""
        return list(self._tools.keys())

    def get_tool_descriptions(self) -> Dict[str, str]:
        """Return a dictionary mapping tool names to their descriptions."""
        return {name: tool.description for name, tool in self._tools.items()}


def get_default_tools(statement: TransactionStatement) -> List[StructuredTool]:
    """Convenience function returning the standard set of 4 LangChain investigation tools."""
    registry = ToolRegistry.from_statement(statement)
    return registry.get_tools()
