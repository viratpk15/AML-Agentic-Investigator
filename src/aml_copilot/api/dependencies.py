"""FastAPI dependency providers for AML Investigation Copilot services."""

from functools import lru_cache
from typing import Optional
from pathlib import Path

from aml_copilot.config import Settings, get_settings
from aml_copilot.rag.service import RAGService, get_rag_service


@lru_cache()
def get_api_settings() -> Settings:
    """Provide cached system settings."""
    return get_settings()


@lru_cache()
def get_api_rag_service() -> Optional[RAGService]:
    """Provide cached RAGService if knowledge directory exists."""
    knowledge_dir = Path("data/knowledge")
    if knowledge_dir.exists():
        try:
            return get_rag_service(knowledge_dir=str(knowledge_dir))
        except Exception:
            return None
    return None
