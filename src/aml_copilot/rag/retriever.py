"""Retriever implementation for AML knowledge base."""

from typing import Any, Dict, List

from aml_copilot.rag.embeddings import BaseEmbeddingService
from aml_copilot.rag.vector_store import LocalVectorStore


class AMLKnowledgeRetriever:
    """Retrieves relevant AML policy, typology, and guidance chunks for a given query."""

    def __init__(
        self,
        vector_store: LocalVectorStore,
        embedding_service: BaseEmbeddingService,
        default_limit: int = 3,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.default_limit = default_limit

    def search(self, query: str, limit: int | None = None) -> List[Dict[str, Any]]:
        """Retrieve most relevant knowledge chunks matching query.

        Args:
            query: The conceptual AML search query.
            limit: Optional override for number of chunks to return.

        Returns:
            List of dictionaries with chunk content, source filename, section, and score.
        """
        top_k = limit if limit is not None else self.default_limit
        if not query or not query.strip():
            return []

        query_vec = self.embedding_service.embed_query(query)
        matches = self.vector_store.similarity_search(query_vec, top_k=top_k)

        results: List[Dict[str, Any]] = []
        for chunk, score in matches:
            results.append({
                "content": chunk.content,
                "source": chunk.source,
                "title": chunk.title,
                "section": chunk.section,
                "chunk_index": chunk.chunk_index,
                "similarity_score": round(score, 4),
            })

        return results

    def format_evidence(self, results: List[Dict[str, Any]]) -> str:
        """Format retrieved knowledge chunks as structured evidence for LLM / agent tools.

        Args:
            results: List of retrieved chunk dictionaries.

        Returns:
            Cleanly formatted string with source citations and section titles.
        """
        if not results:
            return "No relevant AML reference documents found matching the query."

        sections: List[str] = []
        for idx, res in enumerate(results, 1):
            source = res.get("source", "Unknown Source")
            section = res.get("section", "General")
            score = res.get("similarity_score", 0.0)
            content = res.get("content", "").strip()

            block = (
                f"[Evidence {idx}]\n"
                f"Source: {source}\n"
                f"Section: {section}\n"
                f"Relevance Score: {score}\n\n"
                f"{content}"
            )
            sections.append(block)

        return "\n\n---\n\n".join(sections)
