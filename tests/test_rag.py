"""Unit tests for M11 Agentic RAG system."""

import datetime as dt
from pathlib import Path
from typing import Any, List, Optional
import uuid

import pytest
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult

from aml_copilot.agents.investigation_agent import InvestigationAgent, run_investigation
from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.rag.documents import (
    DocumentChunk,
    KnowledgeDocument,
    chunk_document,
    load_knowledge_documents,
)
from aml_copilot.rag.embeddings import DeterministicLocalEmbedder
from aml_copilot.rag.retriever import AMLKnowledgeRetriever
from aml_copilot.rag.service import RAGService, get_rag_service
from aml_copilot.rag.vector_store import LocalVectorStore
from aml_copilot.tools.rag_tools import (
    SearchAMLKnowledgeInput,
    create_search_aml_knowledge_tool,
)
from aml_copilot.tools.tool_registry import ToolRegistry


# ---------------------------------------------------------------------------
# Test Helpers & Mock LLM
# ---------------------------------------------------------------------------

def _sample_statement() -> TransactionStatement:
    return TransactionStatement(
        customer_name="Alpha Exports Ltd",
        account_number="ACC-998877",
        statement_period="2026-08-01 to 2026-08-31",
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN005",
                description="ORION TRADING CREDIT",
                credit=480000.0,
                debit=None,
                balance=480000.0,
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN006",
                description="IMMEDIATE WIRE TRANSFER OUT",
                credit=None,
                debit=475000.0,
                balance=5000.0,
            ),
        ],
    )


class ScriptedChatModel(BaseChatModel):
    """Deterministic mock LLM yielding a predefined sequence of AIMessages."""

    responses: List[AIMessage]
    call_count: int = 0

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        return self

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
        else:
            resp = AIMessage(content="Final synthesized response.", id=str(uuid.uuid4()))
        self.call_count += 1
        return ChatResult(generations=[ChatGeneration(message=resp)])

    @property
    def _llm_type(self) -> str:
        return "scripted-rag-test-llm"


# ---------------------------------------------------------------------------
# 1. Document Loading Tests
# ---------------------------------------------------------------------------

def test_load_knowledge_documents():
    """Verify document loader finds and loads all knowledge documents in data/knowledge/."""
    knowledge_dir = Path("data/knowledge")
    docs = load_knowledge_documents(knowledge_dir)

    assert len(docs) >= 4
    filenames = {d.source for d in docs}
    assert "aml_red_flags.md" in filenames
    assert "aml_transaction_monitoring.md" in filenames
    assert "aml_customer_due_diligence.md" in filenames
    assert "aml_investigation_guidance.md" in filenames

    for doc in docs:
        assert isinstance(doc, KnowledgeDocument)
        assert len(doc.content) > 100
        assert doc.source.endswith(".md")
        assert "Educational AML Reference Material" in doc.content or "AML" in doc.content


def test_load_nonexistent_directory():
    """Verify document loader returns empty list when directory does not exist."""
    docs = load_knowledge_documents("data/nonexistent_knowledge_path")
    assert docs == []


# ---------------------------------------------------------------------------
# 2. Chunking & Metadata Preservation Tests
# ---------------------------------------------------------------------------

def test_chunk_document_preserves_metadata():
    """Verify chunk_document divides text into section-aware chunks with preserved provenance."""
    sample_doc = KnowledgeDocument(
        source="aml_red_flags.md",
        path="/data/knowledge/aml_red_flags.md",
        title="AML Red Flags",
        content=(
            "# AML Red Flags\n\n"
            "## Rapid Movement of Funds\n"
            "Incoming funds followed shortly by outgoing transactions draining the balance.\n\n"
            "## Structuring\n"
            "Multiple transactions clustered below reporting thresholds."
        ),
    )

    chunks = chunk_document(sample_doc, chunk_size=200)
    assert len(chunks) == 2

    # Verify first chunk
    c1 = chunks[0]
    assert c1.source == "aml_red_flags.md"
    assert "Rapid Movement of Funds" in c1.section
    assert "Incoming funds" in c1.content
    assert c1.chunk_index == 0
    assert c1.metadata["source"] == "aml_red_flags.md"

    # Verify second chunk
    c2 = chunks[1]
    assert c2.source == "aml_red_flags.md"
    assert "Structuring" in c2.section
    assert "Multiple transactions" in c2.content
    assert c2.chunk_index == 1


# ---------------------------------------------------------------------------
# 3. Embeddings & Vector Store Tests
# ---------------------------------------------------------------------------

def test_deterministic_local_embedder():
    """Verify local embedder produces deterministic vectors and positive similarity."""
    embedder = DeterministicLocalEmbedder()
    corpus = [
        "Rapid movement of funds involves swift pass-through transactions draining balances.",
        "Customer due diligence verifies identity and beneficial ownership.",
        "Structuring breaks large cash deposits into amounts below threshold limits.",
    ]
    doc_vectors = embedder.embed_documents(corpus)
    assert len(doc_vectors) == 3
    assert len(doc_vectors[0]) > 0

    query_vec = embedder.embed_query("rapid movement of funds pass-through")
    assert len(query_vec) == len(doc_vectors[0])

    # Dot product of query with corpus
    import numpy as np
    sims = [float(np.dot(query_vec, doc_vec)) for doc_vec in doc_vectors]
    # The first document (rapid movement) must have the highest similarity
    assert sims[0] > sims[1]
    assert sims[0] > sims[2]


def test_local_vector_store_similarity_search(tmp_path):
    """Verify LocalVectorStore indexes chunks, executes similarity search, and persists."""
    store = LocalVectorStore()
    chunks = [
        DocumentChunk(
            chunk_id="c1",
            content="Rapid movement of funds indicates transit accounts.",
            source="aml_red_flags.md",
            section="Rapid Movement",
        ),
        DocumentChunk(
            chunk_id="c2",
            content="Customer due diligence requires verification of beneficial owners.",
            source="aml_cdd.md",
            section="CDD",
        ),
    ]

    embedder = DeterministicLocalEmbedder()
    embeddings = embedder.embed_documents([c.content for c in chunks])
    store.add_chunks(chunks, embeddings)

    assert len(store) == 2

    # Query for rapid movement
    q_vec = embedder.embed_query("rapid movement of transit funds")
    matches = store.similarity_search(q_vec, top_k=1)
    assert len(matches) == 1
    top_chunk, score = matches[0]
    assert top_chunk.chunk_id == "c1"
    assert score > 0.3

    # Test persistence save and load
    save_file = tmp_path / "test_store.json"
    store.save(save_file)
    assert save_file.exists()

    new_store = LocalVectorStore().load(save_file)
    assert len(new_store) == 2
    assert new_store.chunks[0].chunk_id == "c1"


# ---------------------------------------------------------------------------
# 4. Retriever & Service Tests
# ---------------------------------------------------------------------------

def test_aml_knowledge_retriever():
    """Verify AMLKnowledgeRetriever searches and formats educational evidence."""
    rag_service = RAGService(knowledge_dir="data/knowledge")
    retriever = rag_service.get_retriever()

    results = retriever.search(query="rapid movement of funds", limit=2)
    assert len(results) > 0
    top_result = results[0]

    assert "source" in top_result
    assert "section" in top_result
    assert "content" in top_result
    assert "similarity_score" in top_result

    evidence = retriever.format_evidence(results)
    assert "Source:" in evidence
    assert "Section:" in evidence
    assert "Relevance Score:" in evidence


# ---------------------------------------------------------------------------
# 5. RAG Tool & Tool Registry Tests
# ---------------------------------------------------------------------------

def test_search_aml_knowledge_tool():
    """Verify the RAG tool can be executed deterministically without LLM."""
    rag_service = RAGService(knowledge_dir="data/knowledge")
    tool = create_search_aml_knowledge_tool(rag_service=rag_service)

    assert tool.name == "search_aml_knowledge"
    assert "AML" in tool.description

    output = tool.invoke({"query": "structuring smurfing thresholds", "limit": 2})
    assert isinstance(output, dict)
    assert output["query"] == "structuring smurfing thresholds"
    assert output["total_results"] > 0
    assert len(output["sources"]) > 0
    assert "formatted_evidence" in output
    assert "aml_red_flags.md" in output["formatted_evidence"] or len(output["sources"]) > 0


def test_tool_registry_with_rag():
    """Verify ToolRegistry registers search_aml_knowledge when include_rag is True."""
    stmt = _sample_statement()
    rag_service = RAGService(knowledge_dir="data/knowledge")

    registry = ToolRegistry.from_statement(stmt, include_rag=True, rag_service=rag_service)
    assert "search_aml_knowledge" in registry.tool_names
    assert len(registry.get_tools()) == 5

    rag_tool = registry.get_tool("search_aml_knowledge")
    assert rag_tool is not None
    assert rag_tool.name == "search_aml_knowledge"


# ---------------------------------------------------------------------------
# 6. LangGraph Agent RAG Routing Test
# ---------------------------------------------------------------------------

def test_agent_routes_to_rag_tool():
    """Verify LangGraph workflow: Agent -> RAG Tool -> Agent -> END."""
    stmt = _sample_statement()
    rag_service = RAGService(knowledge_dir="data/knowledge")

    call_id = str(uuid.uuid4())
    mock_llm = ScriptedChatModel(
        responses=[
            # Step 1: Agent decides to look up rapid movement of funds in AML knowledge base
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_aml_knowledge",
                        "args": {"query": "rapid movement of funds", "limit": 2},
                        "id": call_id,
                    }
                ],
                id=str(uuid.uuid4()),
            ),
            # Step 2: Agent synthesizes final grounded answer citing knowledge
            AIMessage(
                content=(
                    "Observed Evidence:\n"
                    "Customer received ₹480,000 via TXN005 and transferred out ₹475,000 via TXN006 within hours.\n\n"
                    "Relevant AML Reference:\n"
                    "The knowledge base (aml_red_flags.md) defines rapid movement of funds as incoming "
                    "funds followed shortly by outgoing transactions draining the majority of the balance.\n\n"
                    "Interpretation:\n"
                    "The observed transactions resemble a conduit pass-through pattern.\n\n"
                    "Limitation:\n"
                    "This pattern alone does not establish illicit activity."
                ),
                id=str(uuid.uuid4()),
            ),
        ]
    )

    agent = InvestigationAgent(
        llm=mock_llm,
        rag_service=rag_service,
        include_rag=True,
    )
    result = agent.investigate(
        statement=stmt,
        question="What does rapid movement of funds mean, and do TXN005 and TXN006 resemble this?",
    )

    assert "search_aml_knowledge" in result.tools_used
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "search_aml_knowledge"
    assert "TXN005" in result.referenced_transaction_ids
    assert "TXN006" in result.referenced_transaction_ids
    assert len(result.knowledge_sources) > 0
    assert any("aml_red_flags.md" in src for src in result.knowledge_sources)
    assert "Limitation:" in result.response


# ---------------------------------------------------------------------------
# 7. Combined Investigation (Transaction Tool + RAG Tool)
# ---------------------------------------------------------------------------

def test_combined_transaction_and_rag_investigation():
    """Verify an agent can use BOTH transaction tools and RAG tools in a multi-step investigation."""
    stmt = _sample_statement()
    rag_service = RAGService(knowledge_dir="data/knowledge")

    call1_id = str(uuid.uuid4())
    call2_id = str(uuid.uuid4())

    mock_llm = ScriptedChatModel(
        responses=[
            # Step 1: Agent inspects specific transactions
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_transactions",
                        "args": {"transaction_id": "TXN005"},
                        "id": call1_id,
                    }
                ],
                id=str(uuid.uuid4()),
            ),
            # Step 2: Agent checks AML knowledge base for conduit accounts
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_aml_knowledge",
                        "args": {"query": "rapid movement of funds conduit accounts", "limit": 1},
                        "id": call2_id,
                    }
                ],
                id=str(uuid.uuid4()),
            ),
            # Step 3: Agent synthesizes both evidence streams
            AIMessage(
                content=(
                    "Observed Evidence:\n"
                    "TXN005 represents a ₹480,000 credit from Orion Trading.\n\n"
                    "Relevant AML Reference:\n"
                    "aml_red_flags.md describes conduit accounts where large incoming funds are swiftly moved.\n\n"
                    "Interpretation:\n"
                    "The transaction warrants compliance scrutiny.\n\n"
                    "Limitation:\n"
                    "Does not establish guilt or fraud."
                ),
                id=str(uuid.uuid4()),
            ),
        ]
    )

    result = run_investigation(
        statement=stmt,
        question="Inspect TXN005 and explain how it relates to AML typologies.",
        llm=mock_llm,
        rag_service=rag_service,
        include_rag=True,
    )

    assert "search_transactions" in result.tools_used
    assert "search_aml_knowledge" in result.tools_used
    assert len(result.tool_calls) == 2
    assert "TXN005" in result.referenced_transaction_ids
    assert len(result.knowledge_sources) > 0
    assert any("aml_red_flags.md" in src for src in result.knowledge_sources)


# ---------------------------------------------------------------------------
# 8. Additional Edge Cases & Robustness Tests
# ---------------------------------------------------------------------------

def test_rag_empty_query_and_formatting():
    """Verify retriever handles empty strings gracefully."""
    store = LocalVectorStore()
    embedder = DeterministicLocalEmbedder()
    retriever = AMLKnowledgeRetriever(store, embedder)

    assert retriever.search("") == []
    assert retriever.search("   ") == []
    assert "No relevant AML reference documents found" in retriever.format_evidence([])


def test_chunk_long_document_subdivision():
    """Verify long sections exceeding chunk_size are properly subdivided."""
    long_body = "\n\n".join([f"Paragraph {i}: " + ("word " * 40) for i in range(10)])
    doc = KnowledgeDocument(
        source="test_long.md",
        path="/data/test_long.md",
        title="Long Test Document",
        content=f"# Long Test\n\n## Extended Section\n{long_body}",
    )

    chunks = chunk_document(doc, chunk_size=200)
    assert len(chunks) > 2
    for chunk in chunks:
        assert chunk.source == "test_long.md"
        assert "Extended Section" in chunk.section
        assert len(chunk.content) <= 350


def test_rag_service_singleton_and_reload():
    """Verify get_rag_service singleton caching and reload."""
    s1 = get_rag_service(knowledge_dir="data/knowledge")
    s2 = get_rag_service(knowledge_dir="data/knowledge")
    assert s1 is s2

    s3 = get_rag_service(knowledge_dir="data/knowledge", force_reload=True)
    assert s3 is not s1


def test_search_aml_knowledge_tool_schema():
    """Verify SearchAMLKnowledgeInput schema constraints."""
    valid_input = SearchAMLKnowledgeInput(query="rapid movement of funds", limit=5)
    assert valid_input.query == "rapid movement of funds"
    assert valid_input.limit == 5

    with pytest.raises(Exception):
        SearchAMLKnowledgeInput.model_validate({})  # query is required
