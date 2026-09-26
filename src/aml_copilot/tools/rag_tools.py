"""RAG tool for retrieving external AML educational reference knowledge."""

from typing import Any, Dict, List, Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from aml_copilot.logger import get_logger
from aml_copilot.rag.service import RAGService, get_rag_service

logger = get_logger(__name__)


class SearchAMLKnowledgeInput(BaseModel):
    """Input parameters for searching the external AML knowledge base."""

    query: str = Field(
        ...,
        description=(
            "The AML regulatory concept, typology, or investigative topic to look up. "
            "Examples: 'rapid movement of funds', 'structuring', 'customer due diligence', "
            "'enhanced due diligence', 'conduit accounts', 'unusual velocity'."
        ),
    )
    limit: Optional[int] = Field(
        default=2,
        description="Maximum number of relevant knowledge excerpts to retrieve (default 2).",
    )


def execute_search_aml_knowledge(
    query: str,
    limit: int = 2,
    rag_service: Optional[RAGService] = None,
) -> Dict[str, Any]:
    """Execute retrieval against the AML knowledge base and format evidence.

    Args:
        query: Conceptual AML query string.
        limit: Max number of results.
        rag_service: Optional injected RAGService instance.

    Returns:
        Structured dictionary containing query, retrieved results, source citations, and formatted text.
    """
    service = rag_service or get_rag_service()
    retriever = service.get_retriever()
    results = retriever.search(query=query, limit=limit)
    formatted_evidence = retriever.format_evidence(results)

    sources = [
        f"{r['source']}:{r.get('section', 'General')}"
        for r in results
    ]

    compact_results = [
        {
            "source": r["source"],
            "section": r.get("section", "General"),
            "content": r["content"],
        }
        for r in results
    ]

    return {
        "query": query,
        "total_results": len(results),
        "sources": sources,
        "formatted_evidence": formatted_evidence,
        "results": compact_results,
    }


def create_search_aml_knowledge_tool(
    rag_service: Optional[RAGService] = None,
) -> StructuredTool:
    """Create a LangChain StructuredTool for retrieving AML reference knowledge.

    Args:
        rag_service: Optional RAGService instance.

    Returns:
        StructuredTool configured for model tool calling.
    """
    def _search_tool(query: str, limit: Optional[int] = 3) -> Dict[str, Any]:
        return execute_search_aml_knowledge(
            query=query,
            limit=limit or 3,
            rag_service=rag_service,
        )

    return StructuredTool.from_function(
        func=_search_tool,
        name="search_aml_knowledge",
        description=(
            "Search the AML reference knowledge base for guidance on AML typologies, monitoring concepts, "
            "investigation procedures, and regulatory definitions (e.g. rapid movement of funds, structuring, "
            "customer due diligence, source of wealth vs funds). Use this tool whenever answering questions "
            "about AML compliance policy or interpreting why a specific observed pattern represents a known typology. "
            "This tool provides educational reference knowledge, NOT customer transaction data."
        ),
        args_schema=SearchAMLKnowledgeInput,
    )
