"""High-level service coordinating document ingestion, indexing, and retrieval."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from aml_copilot.config import get_settings
from aml_copilot.rag.documents import (
    DocumentChunk,
    KnowledgeDocument,
    chunk_document,
    load_knowledge_documents,
)
from aml_copilot.rag.embeddings import BaseEmbeddingService, get_embedding_service
from aml_copilot.rag.retriever import AMLKnowledgeRetriever
from aml_copilot.rag.vector_store import LocalVectorStore


class RAGService:
    """Coordinates AML knowledge document loading, indexing, and retrieval."""

    def __init__(
        self,
        knowledge_dir: Path | str | None = None,
        embedding_service: Optional[BaseEmbeddingService] = None,
        vector_store: Optional[LocalVectorStore] = None,
        default_limit: int = 3,
    ) -> None:
        settings = get_settings()
        self.knowledge_dir = Path(knowledge_dir or settings.knowledge_dir)
        self.default_limit = default_limit or settings.retrieval_top_k

        if embedding_service is not None:
            self.embedding_service = embedding_service
        else:
            self.embedding_service = get_embedding_service(
                provider=settings.embedding_provider,
                api_key=settings.openai_api_key,
                model=settings.embedding_model,
            )

        self.vector_store = vector_store or LocalVectorStore()
        self._retriever: Optional[AMLKnowledgeRetriever] = None
        self._is_indexed: bool = False

    def index_documents(self) -> int:
        """Load knowledge documents, chunk them, embed, and store in vector store.

        Returns:
            Number of indexed chunks.
        """
        raw_docs: List[KnowledgeDocument] = load_knowledge_documents(self.knowledge_dir)
        all_chunks: List[DocumentChunk] = []

        for doc in raw_docs:
            chunks = chunk_document(doc)
            all_chunks.extend(chunks)

        if not all_chunks:
            self._is_indexed = True
            return 0

        # Generate embeddings
        chunk_texts = [c.content for c in all_chunks]
        embeddings = self.embedding_service.embed_documents(chunk_texts)

        # Store in vector store
        self.vector_store = LocalVectorStore()
        self.vector_store.add_chunks(all_chunks, embeddings)
        self._is_indexed = True

        return len(all_chunks)

    def get_retriever(self) -> AMLKnowledgeRetriever:
        """Return the active AML knowledge retriever, indexing on demand if needed."""
        if not self._is_indexed or self.vector_store is None:
            self.index_documents()

        if self._retriever is None:
            self._retriever = AMLKnowledgeRetriever(
                vector_store=self.vector_store,
                embedding_service=self.embedding_service,
                default_limit=self.default_limit,
            )
        return self._retriever

    def search(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge chunks for a query."""
        retriever = self.get_retriever()
        return retriever.search(query=query, limit=limit)

    def get_formatted_evidence(self, query: str, limit: Optional[int] = None) -> str:
        """Retrieve and format evidence for a query."""
        retriever = self.get_retriever()
        results = retriever.search(query=query, limit=limit)
        return retriever.format_evidence(results)


_GLOBAL_RAG_SERVICE: Optional[RAGService] = None


def get_rag_service(
    knowledge_dir: Path | str | None = None,
    embedding_service: Optional[BaseEmbeddingService] = None,
    force_reload: bool = False,
) -> RAGService:
    """Get or create singleton instance of RAGService."""
    global _GLOBAL_RAG_SERVICE
    if _GLOBAL_RAG_SERVICE is None or force_reload:
        _GLOBAL_RAG_SERVICE = RAGService(
            knowledge_dir=knowledge_dir,
            embedding_service=embedding_service,
        )
    return _GLOBAL_RAG_SERVICE
