"""Unit tests for the central ToolRegistry."""

import datetime as dt
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from aml_copilot.models.transaction import Transaction, TransactionStatement
from aml_copilot.tools.tool_registry import ToolRegistry, get_default_tools


def _sample_statement(name: str = "Test Customer") -> TransactionStatement:
    return TransactionStatement(
        customer_name=name,
        transactions=[
            Transaction(
                date=dt.date(2026, 8, 1),
                transaction_id="TXN001",
                description="SALARY",
                credit=50000.0,
                balance=50000.0,
            )
        ],
    )


def test_tool_registry_empty_initialization():
    """Verify registry starts empty if no statement is passed."""
    registry = ToolRegistry()
    assert registry.statement is None
    assert registry.get_tools() == []
    assert registry.tool_names == []


def test_tool_registry_with_statement():
    """Verify registry initializes all standard tools when provided a statement."""
    stmt = _sample_statement()
    registry = ToolRegistry.from_statement(stmt)

    assert registry.statement is not None
    assert registry.statement.customer_name == "Test Customer"

    expected_names = {
        "analyze_transactions",
        "get_transaction_statistics",
        "search_transactions",
        "detect_anomalies",
    }
    assert set(registry.tool_names) == expected_names
    assert len(registry.get_tools()) == 4

    for name in expected_names:
        tool = registry.get_tool(name)
        assert tool is not None
        assert isinstance(tool, StructuredTool)
        assert len(tool.description) > 20


def test_tool_registry_set_statement_switches_context():
    """Verify set_statement dynamically updates bound tools."""
    stmt1 = _sample_statement("Customer A")
    stmt2 = _sample_statement("Customer B")

    registry = ToolRegistry.from_statement(stmt1)
    tool_a = registry.get_tool("analyze_transactions")
    assert tool_a is not None
    out_a = tool_a.invoke({})
    assert out_a["customer_name"] == "Customer A"

    registry.set_statement(stmt2)
    tool_b = registry.get_tool("analyze_transactions")
    assert tool_b is not None
    out_b = tool_b.invoke({})
    assert out_b["customer_name"] == "Customer B"


def test_tool_registry_custom_tool():
    """Verify registering a custom tool."""
    registry = ToolRegistry.from_statement(_sample_statement())

    class EchoInput(BaseModel):
        text: str

    def echo_fn(text: str) -> str:
        return text

    custom_tool = StructuredTool.from_function(
        func=echo_fn,
        name="custom_echo",
        description="Echoes input back",
        args_schema=EchoInput,
    )
    registry.register_tool(custom_tool)

    assert "custom_echo" in registry.tool_names
    assert registry.get_tool("custom_echo") == custom_tool


def test_get_default_tools_helper():
    """Verify get_default_tools returns 4 tools directly."""
    stmt = _sample_statement()
    tools = get_default_tools(stmt)
    assert len(tools) == 4
    names = {t.name for t in tools}
    assert "search_transactions" in names
    assert "detect_anomalies" in names
