"""Unit tests for M13 network analysis and NetworkX graph construction."""

import datetime as dt

from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.network.analysis import build_transaction_network
from aml_copilot.network.models import NetworkAnalysisResult
from aml_copilot.tools.network_tools import (
    AnalyzeTransactionNetworkInput,
    create_analyze_transaction_network_tool,
)


def _sample_network_statement() -> TransactionStatement:
    """Statement with distinct counterparties and clear directional flows."""
    return TransactionStatement(
        customer_name="Starlight Corp",
        account_number="ACC-5544",
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
                debit=475000.0,
                balance=5000.0,
                counterparty="RAHUL SERVICES",
            ),
            Transaction(
                date=dt.date(2026, 8, 15),
                transaction_id="TXN007",
                description="ACME TECH CONSULTING",
                credit=None,
                debit=75000.0,
                balance=25000.0,
                counterparty="ACME TECH",
            ),
            Transaction(
                date=dt.date(2026, 8, 18),
                transaction_id="TXN008",
                description="ORION TRADING SECOND INVOICE",
                credit=120000.0,
                debit=None,
                balance=145000.0,
                counterparty="ORION TRADING",
            ),
            Transaction(
                date=dt.date(2026, 8, 22),
                transaction_id="TXN009",
                description="KAPOOR LOGISTICS",
                credit=None,
                debit=50000.0,
                balance=95000.0,
                counterparty="KAPOOR LOGISTICS",
            ),
            Transaction(
                date=dt.date(2026, 8, 25),
                transaction_id="TXN010",
                description="ZENITH SUPPLIES",
                credit=None,
                debit=30000.0,
                balance=65000.0,
                counterparty="ZENITH SUPPLIES",
            ),
        ],
    )


def test_build_transaction_network_nodes_and_edges():
    """Verify NetworkX graph builds nodes and edges with preserved transaction details."""
    stmt = _sample_network_statement()
    result = build_transaction_network(stmt)

    assert isinstance(result, NetworkAnalysisResult)
    assert result.customer_name == "Starlight Corp"

    # Entities: Customer + 5 counterparties (Orion, Rahul, Acme, Kapoor, Zenith)
    node_ids = {n.id for n in result.nodes}
    assert "Starlight Corp" in node_ids
    assert "ORION TRADING" in node_ids
    assert "RAHUL SERVICES" in node_ids
    assert "ACME TECH" in node_ids
    assert "KAPOOR LOGISTICS" in node_ids
    assert "ZENITH SUPPLIES" in node_ids
    assert len(result.nodes) == 6

    # Verify Customer Node attributes
    cust_node = next(n for n in result.nodes if n.id == "Starlight Corp")
    assert cust_node.node_type == "customer"
    assert cust_node.degree == 5

    # Verify Edge between ORION TRADING and Customer
    orion_edge = next(e for e in result.edges if e.source == "ORION TRADING" and e.target == "Starlight Corp")
    assert orion_edge.flow_type == "credit_to_customer"
    assert orion_edge.transaction_count == 2
    assert orion_edge.credit_amount == 600000.0
    assert "TXN005" in orion_edge.transaction_ids
    assert "TXN008" in orion_edge.transaction_ids

    # Verify Edge between Customer and RAHUL SERVICES
    rahul_edge = next(e for e in result.edges if e.source == "Starlight Corp" and e.target == "RAHUL SERVICES")
    assert rahul_edge.flow_type == "debit_from_customer"
    assert rahul_edge.debit_amount == 475000.0
    assert "TXN006" in rahul_edge.transaction_ids


def test_network_metrics_calculation():
    """Verify deterministic NetworkX topological metrics."""
    stmt = _sample_network_statement()
    result = build_transaction_network(stmt)
    metrics = result.metrics

    assert metrics.number_of_nodes == 6
    assert metrics.number_of_edges == 5
    assert metrics.unique_counterparties == 5
    assert metrics.customer_degree == 5
    assert metrics.incoming_counterparty_count == 1  # Only Orion sends funds
    assert metrics.outgoing_counterparty_count == 4  # Rahul, Acme, Kapoor, Zenith receive funds
    assert metrics.largest_counterparty_by_volume == "ORION TRADING"
    assert metrics.largest_counterparty_by_transaction_count == "ORION TRADING"
    assert "Starlight Corp" in metrics.degree_centrality


def test_observable_patterns_detection():
    """Verify observable patterns are identified with non-accusatory language and evidence citations."""
    stmt = _sample_network_statement()
    result = build_transaction_network(stmt)

    pattern_names = {p.pattern_name for p in result.observable_patterns}
    assert "one_to_many_topology" in pattern_names
    assert "dominant_high_value_counterparty" in pattern_names
    assert "rapid_flow_between_counterparties" in pattern_names

    # Check rapid flow pattern
    rapid_pattern = next(p for p in result.observable_patterns if p.pattern_name == "rapid_flow_between_counterparties")
    assert "TXN005" in rapid_pattern.supporting_transaction_ids
    assert "TXN006" in rapid_pattern.supporting_transaction_ids
    assert "ORION TRADING" in rapid_pattern.involved_nodes
    assert "RAHUL SERVICES" in rapid_pattern.involved_nodes

    # Check safety: No accusatory language
    for p in result.observable_patterns:
        assert "crime" not in p.description.lower()
        assert "guilt" not in p.description.lower()
        assert "laundering" not in p.description.lower()


def test_build_transaction_network_empty():
    """Verify empty statement builds minimal isolated customer graph."""
    empty_stmt = TransactionStatement(customer_name="Solo Customer", transactions=[])
    result = build_transaction_network(empty_stmt)

    assert result.customer_name == "Solo Customer"
    assert len(result.nodes) == 1
    assert result.nodes[0].id == "Solo Customer"
    assert result.edges == []
    assert result.metrics.number_of_nodes == 1
    assert result.metrics.unique_counterparties == 0


def test_analyze_transaction_network_tool():
    """Verify analyze_transaction_network tool execution via LangChain StructuredTool."""
    stmt = _sample_network_statement()
    tool = create_analyze_transaction_network_tool(stmt)

    assert tool.name == "analyze_transaction_network"
    assert "graph" in tool.description.lower()

    output = tool.invoke({"include_patterns": True})
    assert isinstance(output, dict)
    assert output["customer_name"] == "Starlight Corp"
    assert len(output["nodes"]) == 6
    assert len(output["edges"]) == 5
    assert len(output["observable_patterns"]) > 0

    # With include_patterns=False
    output_no_pat = tool.invoke({"include_patterns": False})
    assert output_no_pat["observable_patterns"] == []


def test_network_tool_schema_validation():
    """Verify AnalyzeTransactionNetworkInput schema constraints."""
    valid_input = AnalyzeTransactionNetworkInput(include_patterns=False)
    assert valid_input.include_patterns is False
