"""AML Knowledge RAG package."""

from aml_copilot.rag.documents import (
    DocumentChunk,
    KnowledgeDocument,
    chunk_document,
    load_knowledge_documents,
)
from aml_copilot.rag.embeddings import (
    BaseEmbeddingService,
    DeterministicLocalEmbedder,
    OpenAIEmbeddingService,
    get_embedding_service,
)
from aml_copilot.rag.retriever import AMLKnowledgeRetriever
from aml_copilot.rag.service import RAGService, get_rag_service
from aml_copilot.rag.vector_store import LocalVectorStore

__all__ = [
    "BaseEmbeddingService",
    "DeterministicLocalEmbedder",
    "DocumentChunk",
    "KnowledgeDocument",
    "LocalVectorStore",
    "OpenAIEmbeddingService",
    "AMLKnowledgeRetriever",
    "RAGService",
    "chunk_document",
    "get_embedding_service",
    "get_rag_service",
    "load_knowledge_documents",
]
