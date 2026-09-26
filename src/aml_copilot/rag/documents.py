"""Document loading and chunking for AML knowledge base."""

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from typing import Any, Dict, List


@dataclass
class KnowledgeDocument:
    """Represents a loaded raw knowledge document."""

    source: str  # Filename, e.g. "aml_red_flags.md"
    path: str
    content: str
    title: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentChunk:
    """Represents a chunk of a knowledge document with preserved provenance."""

    chunk_id: str
    content: str
    source: str
    title: str = ""
    section: str = ""
    chunk_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


def load_knowledge_documents(knowledge_dir: Path | str) -> List[KnowledgeDocument]:
    """Deterministically load text and Markdown documents from the knowledge directory.

    Args:
        knowledge_dir: Path to directory containing knowledge documents.

    Returns:
        List of KnowledgeDocument objects sorted by filename.
    """
    dir_path = Path(knowledge_dir)
    if not dir_path.exists():
        return []

    documents: List[KnowledgeDocument] = []
    # Deterministic alphabetical ordering
    for entry in sorted(os.listdir(dir_path)):
        file_path = dir_path / entry
        if not file_path.is_file():
            continue
        if not (entry.endswith(".md") or entry.endswith(".txt")):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        # Extract title from first markdown header if present
        title = ""
        for line in content.splitlines():
            line_stripped = line.strip()
            if line_stripped.startswith("# "):
                title = line_stripped.lstrip("# ").strip()
                break

        doc = KnowledgeDocument(
            source=entry,
            path=str(file_path.resolve()),
            content=content,
            title=title,
            metadata={"filename": entry, "size_chars": len(content)},
        )
        documents.append(doc)

    return documents


def chunk_document(
    document: KnowledgeDocument,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[DocumentChunk]:
    """Chunk a knowledge document into section-aware, traceable pieces.

    Parses markdown sections (## Header) to retain semantic section metadata,
    and subdivides sections if they exceed chunk_size.

    Args:
        document: The KnowledgeDocument to chunk.
        chunk_size: Maximum approximate chunk size in characters.
        chunk_overlap: Overlap in characters when splitting long sections.

    Returns:
        List of DocumentChunk instances with preserved source and section metadata.
    """
    content = document.content.strip()
    if not content:
        return []

    chunks: List[DocumentChunk] = []
    # Split content by markdown section headers (## ...)
    header_pattern = re.compile(r"^(##\s+.+)$", re.MULTILINE)
    splits = header_pattern.split(content)

    # If document has no ## headers, process as a single section
    if len(splits) == 1:
        raw_sections = [("", splits[0].strip())]
    else:
        raw_sections = []
        # Leading text before first ## header
        if splits[0].strip():
            text_without_h1 = re.sub(r"^#\s+.*$", "", splits[0], flags=re.MULTILINE).strip()
            if text_without_h1:
                raw_sections.append(("", text_without_h1))

        # Pair header with section body
        for i in range(1, len(splits), 2):
            header = splits[i].replace("##", "").strip()
            body = splits[i + 1].strip() if i + 1 < len(splits) else ""
            raw_sections.append((header, body))

    chunk_idx = 0
    for section_title, section_body in raw_sections:
        if not section_body:
            continue

        full_section_text = f"{section_title}\n{section_body}".strip() if section_title else section_body

        # If section fits within chunk_size, keep it intact
        if len(full_section_text) <= chunk_size:
            chunk = DocumentChunk(
                chunk_id=f"{document.source}_chunk_{chunk_idx}",
                content=full_section_text,
                source=document.source,
                title=document.title,
                section=section_title or document.title or "General",
                chunk_index=chunk_idx,
                metadata={
                    "source": document.source,
                    "section": section_title or "General",
                    "chunk_index": chunk_idx,
                },
            )
            chunks.append(chunk)
            chunk_idx += 1
        else:
            # Subdivide section by paragraphs or sentences
            paragraphs = [p.strip() for p in section_body.split("\n\n") if p.strip()]
            current_buffer: List[str] = []
            current_len = 0

            for para in paragraphs:
                para_len = len(para)
                if current_len + para_len > chunk_size and current_buffer:
                    chunk_text = "\n\n".join(current_buffer)
                    if section_title:
                        chunk_text = f"[{section_title}]\n{chunk_text}"
                    chunk = DocumentChunk(
                        chunk_id=f"{document.source}_chunk_{chunk_idx}",
                        content=chunk_text,
                        source=document.source,
                        title=document.title,
                        section=section_title or "General",
                        chunk_index=chunk_idx,
                        metadata={
                            "source": document.source,
                            "section": section_title or "General",
                            "chunk_index": chunk_idx,
                        },
                    )
                    chunks.append(chunk)
                    chunk_idx += 1
                    current_buffer = [para]
                    current_len = para_len
                else:
                    current_buffer.append(para)
                    current_len += para_len + 2

            if current_buffer:
                chunk_text = "\n\n".join(current_buffer)
                if section_title:
                    chunk_text = f"[{section_title}]\n{chunk_text}"
                chunk = DocumentChunk(
                    chunk_id=f"{document.source}_chunk_{chunk_idx}",
                    content=chunk_text,
                    source=document.source,
                    title=document.title,
                    section=section_title or "General",
                    chunk_index=chunk_idx,
                    metadata={
                        "source": document.source,
                        "section": section_title or "General",
                        "chunk_index": chunk_idx,
                    },
                )
                chunks.append(chunk)
                chunk_idx += 1

    return chunks
