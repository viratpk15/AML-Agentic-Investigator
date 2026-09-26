"""Unit tests for Context Budgeting and Payload Optimization in AML Investigations."""

import json
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
import pytest

from aml_copilot.agents.context_budget import (
    compact_tool_output,
    estimate_tokens,
    prepare_context_for_llm,
)
from aml_copilot.agents.investigation_agent import (
    SYSTEM_PROMPT,
)
from aml_copilot.models.transaction import Transaction, TransactionStatement


@pytest.fixture
def sample_statement() -> TransactionStatement:
    """Fixture providing a statement with suspicious pass-through transactions."""
    import datetime as dt
    return TransactionStatement(
        customer_name="Arjun Mehta",
        account_number="AC-9988",
        statement_period="2026-08-01 to 2026-08-31",
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN005",
                description="ORION TRADING CREDIT",
                credit=480000.0,
                debit=None,
                balance=480000.0,
                counterparty="ORION TRADING",
            ),
            Transaction(
                date=dt.date(2026, 8, 10),
                transaction_id="TXN006",
                description="RAHUL SERVICES WIRE OUT",
                credit=None,
                debit=465000.0,
                balance=15000.0,
                counterparty="RAHUL SERVICES",
            ),
        ],
    )


def test_context_below_budget():
    """Verify that messages well within budget are preserved unchanged."""
    messages = [
        SystemMessage(content="You are an AML copilot."),
        HumanMessage(content="Investigate account AC-9988."),
    ]
    budget = 4000
    prepared, report = prepare_context_for_llm(messages, max_tokens=budget)

    assert report.reduction_applied is False
    assert report.initial_estimated_tokens == report.final_estimated_tokens
    assert len(prepared) == 2
    assert prepared[0].content == messages[0].content
    assert prepared[1].content == messages[1].content


def test_context_above_budget():
    """Verify that excessive context triggers progressive reduction to fit budget."""
    huge_tool_content = json.dumps({
        "rule_signals": [
            {
                "rule_id": f"RULE_{i}",
                "rule_name": f"Rule {i}",
                "severity": "HIGH",
                "transaction_ids": [f"TXN{i:03d}"],
                "explanation": "Detailed explanation of potential unusual structuring patterns and thresholds." * 5,
            }
            for i in range(25)
        ],
        "anomaly_signals": [
            {
                "transaction_id": f"TXN{i:03d}",
                "anomaly_score": 0.05,
                "is_anomaly": False,
                "feature_context": {f"feature_{f}": float(f * 100) for f in range(15)},
            }
            for i in range(25)
        ],
        "flagged_transaction_ids": [f"TXN{i:03d}" for i in range(25)],
    })

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content="Analyze transactions for Arjun Mehta."),
        ToolMessage(content=huge_tool_content, tool_call_id="call_detect_1"),
    ]

    initial_tokens = estimate_tokens(messages)
    budget = 1500
    assert initial_tokens > budget

    prepared, report = prepare_context_for_llm(messages, max_tokens=budget)

    assert report.reduction_applied is True
    assert "compact_tool_messages" in report.stages_applied
    assert report.final_estimated_tokens < initial_tokens
    assert len(prepared) == 3


def test_large_tool_result_reduction(sample_statement: TransactionStatement):
    """Verify detect_anomalies compaction preserves anomalies and flagged IDs while stripping normal feature bloat."""
    raw_output = {
        "customer_name": "Arjun Mehta",
        "total_rule_signals": 2,
        "total_anomaly_signals": 1,
        "flagged_transaction_ids": ["TXN005", "TXN006"],
        "rule_signals": [
            {
                "rule_id": "RULE_LARGE_TRANSACTION",
                "rule_name": "Unusually Large Transaction",
                "severity": "HIGH",
                "transaction_ids": ["TXN005"],
                "explanation": "Transaction TXN005 of ₹480,000 exceeds threshold.",
                "supporting_values": {"amount": 480000.0, "ratio": 5.6},
            }
        ],
        "anomaly_signals": [
            {
                "transaction_id": "TXN001",
                "anomaly_score": 0.12,
                "is_anomaly": False,
                "feature_context": {f"feat_{k}": float(k) for k in range(12)},
            },
            {
                "transaction_id": "TXN005",
                "anomaly_score": -0.0548,
                "is_anomaly": True,
                "feature_context": {"amount": 480000.0, "balance_change": 480000.0},
            },
        ],
    }

    compacted = compact_tool_output("detect_anomalies", raw_output)
    compact_data = json.loads(compacted)

    # Flagged IDs and critical evidence preserved
    assert "TXN005" in compact_data["flagged_ids"]
    assert "TXN006" in compact_data["flagged_ids"]

    # Only anomalous transactions included with features
    anomalies = compact_data["anomalies"]
    assert len(anomalies) == 1
    assert anomalies[0]["txn"] == "TXN005"
    assert anomalies[0]["score"] == -0.0548

    # Much smaller than raw
    assert len(compacted) < len(json.dumps(raw_output))


def test_rag_reduction():
    """Verify RAG compaction keeps citations, section metadata, and top guidance while reducing size."""
    raw_rag = {
        "query": "rapid movement of funds",
        "total_results": 3,
        "sources": [
            "aml_red_flags.md:Rapid Movement of Funds",
            "aml_red_flags.md:Structuring",
            "aml_transaction_monitoring.md:Conduit Accounts",
        ],
        "results": [
            {
                "source": "aml_red_flags.md",
                "section": "Rapid Movement of Funds",
                "content": "Substantial incoming funds followed shortly by outgoing transfers draining the account.",
            },
            {
                "source": "aml_red_flags.md",
                "section": "Structuring",
                "content": "Splitting currency transactions into amounts below regulatory thresholds.",
            },
            {
                "source": "aml_transaction_monitoring.md",
                "section": "Conduit Accounts",
                "content": "Pass-through entities acting as temporary conduits without substantive commercial justification.",
            },
        ],
        "formatted_evidence": "Extremely verbose formatted duplicate text here " * 50,
    }

    compacted = compact_tool_output("search_aml_knowledge", raw_rag)
    data = json.loads(compacted)

    assert data["query"] == "rapid movement of funds"
    assert "aml_red_flags.md:Rapid Movement of Funds" in data["sources"]
    assert len(data["excerpts"]) <= 2
    assert data["excerpts"][0]["source"] == "aml_red_flags.md"
    assert data["excerpts"][0]["section"] == "Rapid Movement of Funds"
    assert len(compacted) < len(json.dumps(raw_rag))


def test_history_reduction():
    """Verify that multiple iterations of older ToolMessages are summarized to conserve budget."""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content="Investigate customer statement."),
        # Iteration 1
        AIMessage(content="", tool_calls=[{"id": "c1", "name": "detect_anomalies", "args": {}}]),
        ToolMessage(content='{"flagged": ["TXN005", "TXN006"], "data": "verbose info 1" * 100}', tool_call_id="c1"),
        # Iteration 2
        AIMessage(content="", tool_calls=[{"id": "c2", "name": "get_customer_profile", "args": {}}]),
        ToolMessage(content='{"turnover": 945000, "data": "verbose info 2" * 100}', tool_call_id="c2"),
        # Iteration 3
        AIMessage(content="", tool_calls=[{"id": "c3", "name": "search_aml_knowledge", "args": {}}]),
        ToolMessage(content='{"query": "rapid funds", "data": "latest guidance"}', tool_call_id="c3"),
    ]

    # Set tight budget forcing history reduction
    budget = 400
    prepared, report = prepare_context_for_llm(messages, max_tokens=budget)

    assert report.reduction_applied is True
    # The oldest tool messages should be summarized
    assert any("[Intermediate Tool Evidence Recorded" in str(m.content) for m in prepared if isinstance(m, ToolMessage))


def test_preservation_of_critical_transaction_evidence():
    """Verify TXN005 and TXN006 transaction amounts, dates, and counterparties are preserved."""
    raw_txns = {
        "total_matched": 2,
        "transactions": [
            {
                "transaction_id": "TXN005",
                "date": "2026-08-10",
                "description": "ORION TRADING CREDIT",
                "debit": None,
                "credit": 480000.0,
                "amount": 480000.0,
                "balance": 480000.0,
                "counterparty": "ORION TRADING",
                "is_credit": True,
            },
            {
                "transaction_id": "TXN006",
                "date": "2026-08-10",
                "description": "RAHUL SERVICES WIRE OUT",
                "debit": 465000.0,
                "credit": None,
                "amount": 465000.0,
                "balance": 15000.0,
                "counterparty": "RAHUL SERVICES",
                "is_credit": False,
            },
        ],
    }

    compacted = compact_tool_output("search_transactions", raw_txns)
    data = json.loads(compacted)

    txns = data["transactions"]
    assert len(txns) == 2

    t5 = next(t for t in txns if t["id"] == "TXN005")
    assert t5["amount"] == 480000.0
    assert t5["counterparty"] == "ORION TRADING"
    assert t5["type"] == "credit"
    assert t5["date"] == "2026-08-10"

    t6 = next(t for t in txns if t["id"] == "TXN006")
    assert t6["amount"] == 465000.0
    assert t6["counterparty"] == "RAHUL SERVICES"
    assert t6["type"] == "debit"
    assert t6["date"] == "2026-08-10"


def test_preservation_of_aml_safety_instructions():
    """Verify SYSTEM_PROMPT preserves core non-accusatory compliance rules and guidelines."""
    # Must preserve non-guilt requirement
    assert "MUST NOT declare that a customer is guilty" in SYSTEM_PROMPT
    assert "unusual activity" in SYSTEM_PROMPT
    assert "investigation signal" in SYSTEM_PROMPT
    assert "DO NOT fabricate" in SYSTEM_PROMPT
    assert "TXN005" in SYSTEM_PROMPT
    assert "Observed Evidence" in SYSTEM_PROMPT
    assert "Relevant AML Reference" in SYSTEM_PROMPT
    assert "Interpretation" in SYSTEM_PROMPT
    assert "Limitations" in SYSTEM_PROMPT


def test_preservation_of_source_attribution():
    """Verify RAG citations and source provenance are preserved in compaction."""
    raw_rag = {
        "query": "structuring",
        "sources": ["aml_red_flags.md:Structuring"],
        "results": [
            {
                "source": "aml_red_flags.md",
                "section": "Structuring",
                "content": "Structuring deposits into smaller amounts to evade regulatory thresholds.",
            }
        ],
    }

    compacted = compact_tool_output("search_aml_knowledge", raw_rag)
    data = json.loads(compacted)

    assert "aml_red_flags.md:Structuring" in data["sources"]
    assert data["excerpts"][0]["source"] == "aml_red_flags.md"
    assert data["excerpts"][0]["section"] == "Structuring"


def test_network_analysis_compaction():
    """Verify network analysis compaction preserves key counterparty flows and observable patterns."""
    raw_network = {
        "customer_name": "Arjun Mehta",
        "nodes": [
            {"id": "Arjun Mehta", "node_type": "customer"},
            {"id": "ORION TRADING", "node_type": "counterparty"},
            {"id": "RAHUL SERVICES", "node_type": "counterparty"},
        ],
        "edges": [
            {
                "source": "ORION TRADING",
                "target": "Arjun Mehta",
                "weight": 480000.0,
                "transaction_count": 1,
                "transaction_ids": ["TXN005"],
            },
            {
                "source": "Arjun Mehta",
                "target": "RAHUL SERVICES",
                "weight": 465000.0,
                "transaction_count": 1,
                "transaction_ids": ["TXN006"],
            },
        ],
        "observable_patterns": [
            {
                "pattern_name": "rapid_flow_between_counterparties",
                "description": "Rapid pass-through conduit flow from ORION TRADING to RAHUL SERVICES.",
                "involved_nodes": ["ORION TRADING", "RAHUL SERVICES"],
                "supporting_transaction_ids": ["TXN005", "TXN006"],
            }
        ],
        "metrics": {"unique_counterparties": 2, "customer_degree": 2},
    }

    compacted = compact_tool_output("analyze_transaction_network", raw_network)
    data = json.loads(compacted)

    assert data["customer"] == "Arjun Mehta"
    assert len(data["patterns"]) == 1
    assert data["patterns"][0]["pattern"] == "rapid_flow_between_counterparties"
    assert "TXN005" in data["patterns"][0]["txns"]
    assert "TXN006" in data["patterns"][0]["txns"]
    assert len(data["flows"]) == 2
