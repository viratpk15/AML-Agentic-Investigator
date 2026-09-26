"""Lightweight local vector store with similarity search."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from aml_copilot.rag.documents import DocumentChunk


class LocalVectorStore:
    """Lightweight in-memory vector store supporting cosine similarity search and local persistence."""

    def __init__(self) -> None:
        self.chunks: List[DocumentChunk] = []
        self.embeddings: Optional[np.ndarray] = None  # Shape (N, D)

    def __len__(self) -> int:
        return len(self.chunks)

    def add_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
    ) -> None:
        """Add document chunks and their corresponding embedding vectors to the store.

        Args:
            chunks: List of DocumentChunk instances.
            embeddings: Corresponding numerical embedding vectors.
        """
        if not chunks or not embeddings:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: received {len(chunks)} chunks but {len(embeddings)} embedding vectors."
            )

        new_embeddings = np.array(embeddings, dtype=np.float32)

        if self.embeddings is None or len(self.chunks) == 0:
            self.chunks = list(chunks)
            self.embeddings = new_embeddings
        else:
            self.chunks.extend(chunks)
            self.embeddings = np.vstack([self.embeddings, new_embeddings])

    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 3,
    ) -> List[Tuple[DocumentChunk, float]]:
        """Search for top_k most similar chunks using cosine similarity.

        Args:
            query_vector: Vector representation of the search query.
            top_k: Maximum number of chunks to return.

        Returns:
            List of (DocumentChunk, similarity_score) tuples sorted descending by score.
        """
        if self.embeddings is None or len(self.chunks) == 0:
            return []

        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return [(self.chunks[i], 0.0) for i in range(min(top_k, len(self.chunks)))]

        # Compute cosine similarity
        chunk_norms = np.linalg.norm(self.embeddings, axis=1)
        # Avoid division by zero
        chunk_norms = np.where(chunk_norms == 0, 1e-10, chunk_norms)
        similarities = np.dot(self.embeddings, q_vec) / (chunk_norms * q_norm)

        # Get top indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results: List[Tuple[DocumentChunk, float]] = []
        for idx in top_indices:
            results.append((self.chunks[idx], float(similarities[idx])))

        return results

    def save(self, filepath: Path | str) -> None:
        """Persist vector store chunks and embeddings to local disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload: Dict[str, Any] = {
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "content": c.content,
                    "source": c.source,
                    "title": c.title,
                    "section": c.section,
                    "chunk_index": c.chunk_index,
                    "metadata": c.metadata,
                }
                for c in self.chunks
            ],
            "embeddings": self.embeddings.tolist() if self.embeddings is not None else [],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def load(self, filepath: Path | str) -> "LocalVectorStore":
        """Load stored chunks and embeddings from local disk."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Vector store file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        self.chunks = [
            DocumentChunk(
                chunk_id=item["chunk_id"],
                content=item["content"],
                source=item["source"],
                title=item.get("title", ""),
                section=item.get("section", ""),
                chunk_index=item.get("chunk_index", 0),
                metadata=item.get("metadata", {}),
            )
            for item in payload.get("chunks", [])
        ]

        raw_embeds = payload.get("embeddings", [])
        if raw_embeds:
            self.embeddings = np.array(raw_embeds, dtype=np.float32)
        else:
            self.embeddings = None

        return self
