"""Network analysis models for customer-counterparty graph representation."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class NetworkNode(BaseModel):
    """An entity in the transaction network (Customer or Counterparty)."""

    id: str = Field(..., description="Unique node identifier (canonical name)")
    label: str = Field(..., description="Display label for the entity")
    node_type: Literal["customer", "counterparty"] = Field(
        ..., description="Entity classification: 'customer' or 'counterparty'"
    )
    total_volume: float = Field(default=0.0, description="Cumulative transactional volume transacted")
    in_degree: int = Field(default=0, description="Incoming edge count")
    out_degree: int = Field(default=0, description="Outgoing edge count")
    degree: int = Field(default=0, description="Total connection degree")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional entity attributes")


class NetworkEdge(BaseModel):
    """A directed relationship representing transactional fund flow between entities."""

    source: str = Field(..., description="Source entity ID (sender of funds)")
    target: str = Field(..., description="Target entity ID (receiver of funds)")
    flow_type: Literal["credit_to_customer", "debit_from_customer"] = Field(
        ..., description="Direction of fund flow relative to customer"
    )
    transaction_count: int = Field(..., description="Number of distinct transactions along this edge")
    total_amount: float = Field(..., description="Total cumulative amount transacted")
    credit_amount: float = Field(default=0.0, description="Cumulative credit amount")
    debit_amount: float = Field(default=0.0, description="Cumulative debit amount")
    transaction_ids: List[str] = Field(
        default_factory=list, description="All underlying transaction IDs on this edge"
    )
    first_seen: Optional[str] = Field(default=None, description="ISO date of first transaction")
    last_seen: Optional[str] = Field(default=None, description="ISO date of latest transaction")


class ObservablePattern(BaseModel):
    """Factual, non-accusatory network topological observation."""

    pattern_name: str = Field(..., description="Machine-readable pattern identifier")
    description: str = Field(..., description="Objective description of the observed topological structure")
    involved_nodes: List[str] = Field(default_factory=list, description="Entities involved in the pattern")
    supporting_transaction_ids: List[str] = Field(
        default_factory=list, description="Transaction IDs directly establishing this relationship"
    )
    details: Dict[str, Any] = Field(default_factory=dict, description="Metrics backing the observation")


class NetworkMetrics(BaseModel):
    """Deterministic graph topology metrics computed via NetworkX."""

    number_of_nodes: int = Field(..., description="Total nodes in the graph")
    number_of_edges: int = Field(..., description="Total directed edges in the graph")
    unique_counterparties: int = Field(..., description="Number of counterparty nodes")
    customer_degree: int = Field(..., description="Customer node degree (total connections)")
    incoming_counterparty_count: int = Field(..., description="Counterparties sending funds to customer")
    outgoing_counterparty_count: int = Field(..., description="Counterparties receiving funds from customer")
    largest_counterparty_by_volume: Optional[str] = Field(
        default=None, description="Counterparty associated with greatest monetary volume"
    )
    largest_counterparty_by_transaction_count: Optional[str] = Field(
        default=None, description="Counterparty with highest transaction frequency"
    )
    degree_centrality: Dict[str, float] = Field(
        default_factory=dict, description="Normalized NetworkX degree centrality per node"
    )
    counterparty_degree_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of connection counts among counterparties"
    )


class NetworkAnalysisResult(BaseModel):
    """Complete network analysis artifact capturing nodes, edges, metrics, and patterns."""

    customer_name: str = Field(..., description="Primary account holder / central node")
    nodes: List[NetworkNode] = Field(default_factory=list, description="All entities in the network")
    edges: List[NetworkEdge] = Field(default_factory=list, description="All directed connections")
    metrics: NetworkMetrics = Field(..., description="Summary topological metrics")
    observable_patterns: List[ObservablePattern] = Field(
        default_factory=list, description="Identified factual network patterns"
    )
