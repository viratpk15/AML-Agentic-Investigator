"""Embedding service abstractions for AML knowledge retrieval."""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np


class BaseEmbeddingService(ABC):
    """Abstract interface for generating numerical vector representations of text."""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a list of document chunks."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Generate an embedding vector for a user/agent search query."""
        pass


class DeterministicLocalEmbedder(BaseEmbeddingService):
    """A deterministic, zero-network, local embedding model using TF-IDF and n-grams.

    Ideal for fast, test-friendly, and cost-free retrieval in educational projects.
    Normalizes all generated vectors to unit length so that cosine similarity
    is identical to dot product.
    """

    def __init__(self, ngram_range: tuple = (1, 2)) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.ngram_range = ngram_range
        self.vectorizer = TfidfVectorizer(
            ngram_range=self.ngram_range,
            stop_words="english",
            norm="l2",
            sublinear_tf=True,
        )
        self._is_fitted = False
        self._fallback_dim = 128

    def fit(self, texts: List[str]) -> "DeterministicLocalEmbedder":
        """Fit the internal vocabulary on the provided text corpus."""
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            valid_texts = ["aml anti money laundering transaction monitoring compliance"]
        self.vectorizer.fit(valid_texts)
        self._is_fitted = True
        return self

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Fit vocabulary if not yet fitted and return normalized embeddings."""
        if not texts:
            return []

        if not self._is_fitted:
            self.fit(texts)

        matrix = self.vectorizer.transform(texts)
        dense = matrix.toarray()
        return [row.tolist() for row in dense]

    def embed_query(self, text: str) -> List[float]:
        """Transform a search query into the vector space."""
        if not self._is_fitted:
            # Fit on standard AML domain keywords as fallback
            self.fit([
                "aml anti money laundering transaction monitoring",
                "rapid movement of funds structuring cdd edd red flags",
                "investigation baseline high risk counterparty",
            ])

        vec = self.vectorizer.transform([text]).toarray()[0]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


class OpenAIEmbeddingService(BaseEmbeddingService):
    """External embedding provider using OpenAI models via LangChain."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as err:
            raise ImportError(
                "langchain-openai is required for OpenAI embeddings. Run `uv add langchain-openai`."
            ) from err

        self.client = OpenAIEmbeddings(
            openai_api_key=api_key,
            model=model,
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.client.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self.client.embed_query(text)


def get_embedding_service(
    provider: str = "local",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> BaseEmbeddingService:
    """Factory to instantiate the appropriate embedding provider.

    Args:
        provider: 'local' (deterministic TF-IDF) or 'openai'.
        api_key: Optional API key for external providers.
        model: Optional model name.

    Returns:
        Instance of BaseEmbeddingService.
    """
    if provider.lower() == "openai":
        if not api_key:
            raise ValueError("OpenAI embedding provider requested but no API key was provided.")
        return OpenAIEmbeddingService(api_key=api_key, model=model or "text-embedding-3-small")

    return DeterministicLocalEmbedder()
