"""Network analysis engine constructing customer-counterparty graphs via NetworkX."""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
import networkx as nx

from aml_copilot.logger import get_logger
from aml_copilot.models.transaction import TransactionStatement
from aml_copilot.network.models import (
    NetworkAnalysisResult,
    NetworkEdge,
    NetworkMetrics,
    NetworkNode,
    ObservablePattern,
)

logger = get_logger(__name__)


def build_transaction_network(statement: TransactionStatement) -> NetworkAnalysisResult:
    """Build a directed transaction graph and calculate network metrics using NetworkX.

    Args:
        statement: Validated TransactionStatement under review.

    Returns:
        Structured NetworkAnalysisResult containing nodes, edges, metrics, and patterns.
    """
    customer_id = (statement.customer_name or "CUSTOMER").strip()
    txns = statement.transactions

    G = nx.DiGraph()
    G.add_node(customer_id, node_type="customer", label=customer_id)

    if not txns:
        empty_metrics = NetworkMetrics(
            number_of_nodes=1,
            number_of_edges=0,
            unique_counterparties=0,
            customer_degree=0,
            incoming_counterparty_count=0,
            outgoing_counterparty_count=0,
            largest_counterparty_by_volume=None,
            largest_counterparty_by_transaction_count=None,
            degree_centrality={customer_id: 0.0},
            counterparty_degree_distribution={},
        )
        return NetworkAnalysisResult(
            customer_name=customer_id,
            nodes=[
                NetworkNode(
                    id=customer_id,
                    label=customer_id,
                    node_type="customer",
                    total_volume=0.0,
                    in_degree=0,
                    out_degree=0,
                    degree=0,
                )
            ],
            edges=[],
            metrics=empty_metrics,
            observable_patterns=[],
        )

    # Track edge aggregations: (source, target) -> edge data
    # Node volume tracking: node_id -> cumulative volume
    edge_records: Dict[Tuple[str, str], Dict[str, Any]] = defaultdict(
        lambda: {
            "transaction_ids": [],
            "transaction_count": 0,
            "total_amount": 0.0,
            "credit_amount": 0.0,
            "debit_amount": 0.0,
            "first_seen": None,
            "last_seen": None,
            "flow_type": "",
        }
    )
    node_volumes: Dict[str, float] = defaultdict(float)

    for txn in txns:
        cp_name = (txn.counterparty or "").strip()
        amt = txn.credit if (txn.credit and txn.credit > 0) else (txn.debit if (txn.debit and txn.debit > 0) else 0.0)
        node_volumes[customer_id] += amt

        # Transactions without a verified external counterparty entity affect customer balance
        # but do not introduce a counterparty node in the relational graph.
        if not cp_name:
            continue

        date_str = txn.date.isoformat()

        if txn.credit and txn.credit > 0:
            # Funds flow: Counterparty -> Customer
            src, tgt = cp_name, customer_id
            flow_type = "credit_to_customer"

            G.add_node(cp_name, node_type="counterparty", label=cp_name)
            node_volumes[cp_name] += amt

            rec = edge_records[(src, tgt)]
            rec["transaction_ids"].append(txn.transaction_id)
            rec["transaction_count"] += 1
            rec["total_amount"] += amt
            rec["credit_amount"] += amt
            rec["flow_type"] = flow_type

            if rec["first_seen"] is None or date_str < rec["first_seen"]:
                rec["first_seen"] = date_str
            if rec["last_seen"] is None or date_str > rec["last_seen"]:
                rec["last_seen"] = date_str

            G.add_edge(src, tgt)

        elif txn.debit and txn.debit > 0:
            # Funds flow: Customer -> Counterparty
            src, tgt = customer_id, cp_name
            flow_type = "debit_from_customer"

            G.add_node(cp_name, node_type="counterparty", label=cp_name)
            node_volumes[cp_name] += amt

            rec = edge_records[(src, tgt)]
            rec["transaction_ids"].append(txn.transaction_id)
            rec["transaction_count"] += 1
            rec["total_amount"] += amt
            rec["debit_amount"] += amt
            rec["flow_type"] = flow_type

            if rec["first_seen"] is None or date_str < rec["first_seen"]:
                rec["first_seen"] = date_str
            if rec["last_seen"] is None or date_str > rec["last_seen"]:
                rec["last_seen"] = date_str

            G.add_edge(src, tgt)

    # 1. Build serialized nodes
    network_nodes: List[NetworkNode] = []
    for node_id in G.nodes():
        node_type = G.nodes[node_id].get("node_type", "counterparty")
        in_deg = G.in_degree(node_id)
        out_deg = G.out_degree(node_id)
        deg = G.degree(node_id)
        vol = round(node_volumes.get(node_id, 0.0), 2)

        network_nodes.append(
            NetworkNode(
                id=node_id,
                label=node_id,
                node_type=node_type,
                total_volume=vol,
                in_degree=in_deg,
                out_degree=out_deg,
                degree=deg,
            )
        )

    # 2. Build serialized edges
    network_edges: List[NetworkEdge] = []
    for (src, tgt), data in edge_records.items():
        network_edges.append(
            NetworkEdge(
                source=src,
                target=tgt,
                flow_type=data["flow_type"],
                transaction_count=data["transaction_count"],
                total_amount=round(data["total_amount"], 2),
                credit_amount=round(data["credit_amount"], 2),
                debit_amount=round(data["debit_amount"], 2),
                transaction_ids=data["transaction_ids"],
                first_seen=data["first_seen"],
                last_seen=data["last_seen"],
            )
        )

    # 3. Calculate NetworkX metrics
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    counterparty_nodes = [n for n in G.nodes() if n != customer_id]
    num_cp = len(counterparty_nodes)
    cust_degree = G.degree(customer_id) if customer_id in G else 0

    incoming_cps = list(G.predecessors(customer_id)) if customer_id in G else []
    outgoing_cps = list(G.successors(customer_id)) if customer_id in G else []

    centrality_raw = nx.degree_centrality(G)
    centrality_formatted = {str(k): round(v, 4) for k, v in centrality_raw.items()}

    # Degree distribution for counterparties
    degree_dist: Dict[str, int] = defaultdict(int)
    for cp in counterparty_nodes:
        degree_dist[str(G.degree(cp))] += 1

    # Largest counterparties
    largest_cp_vol: Optional[str] = None
    largest_cp_txn: Optional[str] = None
    if counterparty_nodes:
        cp_volumes = {cp: node_volumes[cp] for cp in counterparty_nodes}
        largest_cp_vol = max(cp_volumes, key=lambda k: cp_volumes[k])

        cp_txn_counts = defaultdict(int)
        for (src, tgt), data in edge_records.items():
            cp = src if src != customer_id else tgt
            cp_txn_counts[cp] += data["transaction_count"]
        largest_cp_txn = max(cp_txn_counts, key=lambda k: cp_txn_counts[k])

    metrics = NetworkMetrics(
        number_of_nodes=num_nodes,
        number_of_edges=num_edges,
        unique_counterparties=num_cp,
        customer_degree=cust_degree,
        incoming_counterparty_count=len(incoming_cps),
        outgoing_counterparty_count=len(outgoing_cps),
        largest_counterparty_by_volume=largest_cp_vol,
        largest_counterparty_by_transaction_count=largest_cp_txn,
        degree_centrality=centrality_formatted,
        counterparty_degree_distribution=dict(degree_dist),
    )

    # 4. Identify observable topological patterns
    patterns: List[ObservablePattern] = []

    # Pattern 1: One-to-many customer relationship
    if num_cp >= 5:
        patterns.append(
            ObservablePattern(
                pattern_name="one_to_many_topology",
                description=(
                    f"Customer displays a one-to-many star network connecting with {num_cp} distinct counterparties."
                ),
                involved_nodes=[customer_id] + counterparty_nodes[:5],
                supporting_transaction_ids=[
                    t.transaction_id
                    for t in sorted(
                        [t for t in txns if t.counterparty in counterparty_nodes[:5]],
                        key=lambda x: (x.credit or 0.0) + (x.debit or 0.0),
                        reverse=True,
                    )
                    if t.transaction_id
                ],
                details={"unique_counterparties_count": num_cp},
            )
        )

    # Pattern 2: Dominant / High-Value counterparty
    total_network_turnover = sum(node_volumes[cp] for cp in counterparty_nodes)
    if largest_cp_vol and total_network_turnover > 0:
        vol_pct = round((node_volumes[largest_cp_vol] / total_network_turnover) * 100, 1)
        if vol_pct >= 30.0 or node_volumes[largest_cp_vol] >= 200000.0:
            relevant_txns = []
            for (src, tgt), data in edge_records.items():
                if largest_cp_vol in (src, tgt):
                    relevant_txns.extend(data["transaction_ids"])

            patterns.append(
                ObservablePattern(
                    pattern_name="dominant_high_value_counterparty",
                    description=(
                        f"Counterparty '{largest_cp_vol}' represents a dominant high-volume entity, "
                        f"accounting for ₹{node_volumes[largest_cp_vol]:,.2f} ({vol_pct}% of counterparty volume)."
                    ),
                    involved_nodes=[largest_cp_vol, customer_id],
                    supporting_transaction_ids=relevant_txns,
                    details={
                        "counterparty": largest_cp_vol,
                        "volume": node_volumes[largest_cp_vol],
                        "percentage_of_network": vol_pct,
                    },
                )
            )

    # Pattern 3: Rapid flow between counterparties (Conduit / Passthrough relationship)
    # Detect when credit from CP_A is followed shortly by debit to CP_B
    sorted_txns = sorted(txns, key=lambda t: t.date)
    for i, c_txn in enumerate(sorted_txns):
        if c_txn.credit and c_txn.credit >= 100000.0:
            cp_in = (c_txn.counterparty or c_txn.description).strip()
            for d_txn in sorted_txns[i + 1 :]:
                gap_days = (d_txn.date - c_txn.date).days
                if gap_days > 2:
                    break
                if d_txn.debit and d_txn.debit >= 0.7 * c_txn.credit:
                    cp_out = (d_txn.counterparty or d_txn.description).strip()
                    patterns.append(
                        ObservablePattern(
                            pattern_name="rapid_flow_between_counterparties",
                            description=(
                                f"Incoming transfer of ₹{c_txn.credit:,.2f} from '{cp_in}' ({c_txn.transaction_id}) "
                                f"was followed within {gap_days} days by outgoing transfer of ₹{d_txn.debit:,.2f} "
                                f"to '{cp_out}' ({d_txn.transaction_id})."
                            ),
                            involved_nodes=[cp_in, customer_id, cp_out],
                            supporting_transaction_ids=[
                                tid for tid in (c_txn.transaction_id, d_txn.transaction_id) if tid
                            ],
                            details={
                                "incoming_counterparty": cp_in,
                                "outgoing_counterparty": cp_out,
                                "credit_amount": c_txn.credit,
                                "debit_amount": d_txn.debit,
                                "day_gap": gap_days,
                            },
                        )
                    )
                    break

    return NetworkAnalysisResult(
        customer_name=customer_id,
        nodes=network_nodes,
        edges=network_edges,
        metrics=metrics,
        observable_patterns=patterns,
    )
