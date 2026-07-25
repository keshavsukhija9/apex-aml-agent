"""
Feature Engineering Tool -- the intellectual core.

Computes AML-relevant features per customer:
  - Rolling 24h sub-$10,000 transaction count/sum (structuring signal)
  - Velocity: time delta between consecutive transactions
  - Amount deviation from customer's own historical mean/std

Design note: functions take a filtered DataFrame (already scoped to relevant
customers/date range by the orchestrator) so this tool never assumes it owns
the full dataset -- consistent with "only preprocess what's relevant to the query."
"""

import pandas as pd
import numpy as np


def load_transactions(path: str = "data/transactions.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    df = df.sort_values(["customer_id", "timestamp"]).reset_index(drop=True)
    return df


def compute_rolling_sub_threshold_features(
    df: pd.DataFrame, threshold: float = 10000.0, window_hours: int = 24
) -> pd.DataFrame:
    """
    For each transaction, count how many sub-threshold transactions the same
    customer made in the preceding `window_hours`. This is the core structuring
    signal: FinCEN's CTR threshold is $10,000; smurfing deliberately stays under it.
    """
    df = df.copy()
    df["is_sub_threshold"] = df["amount"] < threshold

    rolling_counts = []
    rolling_sums = []

    for cust_id, group in df.groupby("customer_id"):
        group = group.sort_values("timestamp").reset_index(drop=True)
        times = pd.to_datetime(group["timestamp"]).reset_index(drop=True)
        amounts = group["amount"].to_numpy()
        sub_thresh = group["is_sub_threshold"].to_numpy()

        counts = np.zeros(len(group), dtype=int)
        sums = np.zeros(len(group))

        window = pd.Timedelta(hours=window_hours)

        for i in range(len(group)):
            current_time = times.iloc[i]
            window_start = current_time - window
            in_window = ((times >= window_start) & (times <= current_time)).to_numpy() & sub_thresh
            counts[i] = in_window.sum()
            sums[i] = amounts[in_window].sum()

        rolling_counts.extend(counts)
        rolling_sums.extend(sums)

    df["rolling_24h_sub_threshold_count"] = rolling_counts
    df["rolling_24h_sub_threshold_sum"] = rolling_sums
    return df


def compute_velocity_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Time delta (in minutes) between consecutive transactions for the same customer.
    Rapid-fire transactions are a structuring/layering indicator.
    """
    df = df.copy()
    df["prev_timestamp"] = df.groupby("customer_id")["timestamp"].shift(1)
    df["velocity_minutes"] = (
        (df["timestamp"] - df["prev_timestamp"]).dt.total_seconds() / 60.0
    )
    df["velocity_minutes"] = df["velocity_minutes"].fillna(np.inf)
    return df


def compute_deviation_features(df: pd.DataFrame, min_history: int = 5) -> pd.DataFrame:
    """
    Z-score of each transaction's amount against the customer's own historical
    mean/std. Requires a minimum transaction history to avoid degenerate stats
    on new customers (documented edge case, not silently ignored).
    """
    df = df.copy()
    stats = df.groupby("customer_id")["amount"].agg(["mean", "std", "count"]).reset_index()
    stats.columns = ["customer_id", "cust_mean_amount", "cust_std_amount", "cust_txn_count"]
    df = df.merge(stats, on="customer_id", how="left")

    df["has_sufficient_history"] = df["cust_txn_count"] >= min_history

    safe_std = df["cust_std_amount"].replace(0, np.nan)
    df["amount_zscore"] = (df["amount"] - df["cust_mean_amount"]) / safe_std
    df["amount_zscore"] = df["amount_zscore"].fillna(0)

    df.loc[~df["has_sufficient_history"], "amount_zscore"] = np.nan

    return df


def engineer_features(
    df: pd.DataFrame,
    threshold: float = 10000.0,
    window_hours: int = 24,
    min_history: int = 5,
) -> pd.DataFrame:
    """Full feature engineering pipeline, composed from the individual steps above."""
    df = compute_rolling_sub_threshold_features(df, threshold, window_hours)
    df = compute_velocity_features(df)
    df = compute_deviation_features(df, min_history)
    return df


def get_customer_summary(df: pd.DataFrame, customer_id: int) -> dict:
    """
    Aggregate feature summary for a single customer -- used by entity-lookup queries.
    Returns None-safe dict even if customer has zero transactions.
    """
    cust_df = df[df["customer_id"] == customer_id]
    if cust_df.empty:
        return {
            "customer_id": customer_id,
            "transaction_count": 0,
            "max_rolling_24h_sub_threshold_count": 0,
            "max_rolling_24h_sub_threshold_sum": 0.0,
            "min_velocity_minutes": None,
            "max_amount_zscore": None,
            "has_sufficient_history": False,
        }

    return {
        "customer_id": customer_id,
        "transaction_count": int(len(cust_df)),
        "max_rolling_24h_sub_threshold_count": int(cust_df["rolling_24h_sub_threshold_count"].max()),
        "max_rolling_24h_sub_threshold_sum": float(cust_df["rolling_24h_sub_threshold_sum"].max()),
        "min_velocity_minutes": (
            float(cust_df["velocity_minutes"].replace(np.inf, np.nan).min())
            if cust_df["velocity_minutes"].replace(np.inf, np.nan).notna().any()
            else None
        ),
        "max_amount_zscore": (
            float(cust_df["amount_zscore"].max())
            if cust_df["amount_zscore"].notna().any()
            else None
        ),
        "has_sufficient_history": bool(cust_df["has_sufficient_history"].iloc[0]),
    }

# ---------- Graph / Multi-hop Layering Detection ----------

import networkx as nx


def build_transaction_graph(df: pd.DataFrame) -> nx.DiGraph:
    """
    Build a directed multigraph of money flow: customer_id -> counterparty_id,
    weighted by amount and annotated with timestamp for time-window analysis.
    """
    G = nx.MultiDiGraph()
    for _, row in df.iterrows():
        G.add_edge(
            row["customer_id"],
            row["counterparty_id"],
            amount=row["amount"],
            timestamp=row["timestamp"],
            transaction_id=row["transaction_id"],
        )
    return G


def get_ego_subgraph(G: nx.MultiDiGraph, entity_id: int, k_hops: int = 2) -> nx.MultiDiGraph:
    """
    Bounded k-hop subgraph around a single entity -- NOT the full graph.
    This is the latency fix: entity-lookup queries must not pay the cost
    of global centrality computation across the entire transaction network.
    """
    if entity_id not in G:
        return nx.MultiDiGraph()

    # Treat as undirected for neighbor traversal (money flows both ways matter for layering)
    undirected = G.to_undirected()
    nodes_in_range = {entity_id}
    frontier = {entity_id}

    for _ in range(k_hops):
        next_frontier = set()
        for node in frontier:
            next_frontier.update(undirected.neighbors(node))
        nodes_in_range.update(next_frontier)
        frontier = next_frontier

    return G.subgraph(nodes_in_range).copy()


def detect_layering_pattern(
    G: nx.MultiDiGraph, entity_id: int, k_hops: int = 2,
    min_out_degree: int = 4, window_minutes: int = 60
) -> dict:
    """
    Checks if entity_id acts as a layering intermediate: receives a large inbound
    transfer, then rapidly (within window_minutes) splits it across >= min_out_degree
    distinct outbound accounts. Runs only on the bounded ego subgraph.
    """
    subgraph = get_ego_subgraph(G, entity_id, k_hops)

    if entity_id not in subgraph:
        return {
            "entity_id": entity_id,
            "is_layering_intermediate": False,
            "reason": "entity not found in transaction graph",
            "hop_trace": [],
        }

    # Inbound edges to entity_id
    inbound = []
    for u, v, data in subgraph.in_edges(entity_id, data=True):
        inbound.append({"from": u, "amount": data["amount"], "timestamp": data["timestamp"]})

    # Outbound edges from entity_id
    outbound = []
    for u, v, data in subgraph.out_edges(entity_id, data=True):
        outbound.append({"to": v, "amount": data["amount"], "timestamp": data["timestamp"]})

    if not inbound or len(outbound) < min_out_degree:
        return {
            "entity_id": entity_id,
            "is_layering_intermediate": False,
            "reason": f"insufficient fan-out (found {len(outbound)}, need >= {min_out_degree})",
            "hop_trace": [],
        }

    # Check if outbound transactions cluster within window_minutes of an inbound one
    inbound_sorted = sorted(inbound, key=lambda x: pd.Timestamp(x["timestamp"]))
    biggest_inbound = max(inbound_sorted, key=lambda x: x["amount"])
    inbound_time = pd.Timestamp(biggest_inbound["timestamp"])
    window = pd.Timedelta(minutes=window_minutes)

    clustered_outbound = [
        o for o in outbound
        if abs((pd.Timestamp(o["timestamp"]) - inbound_time).total_seconds() / 60) <= window_minutes
    ]

    is_layering = len(clustered_outbound) >= min_out_degree

    hop_trace = [f"[HOP 1] {biggest_inbound['from']} -> {entity_id} (${biggest_inbound['amount']:,.2f})"]
    for o in clustered_outbound:
        hop_trace.append(f"[HOP 2] {entity_id} -> {o['to']} (${o['amount']:,.2f})")

    return {
        "entity_id": entity_id,
        "is_layering_intermediate": is_layering,
        "reason": (
            f"{len(clustered_outbound)} outbound transfers within {window_minutes}min "
            f"of largest inbound (${biggest_inbound['amount']:,.2f})"
        ),
        "hop_trace": hop_trace,
        "num_clustered_outbound": len(clustered_outbound),
        "total_outbound_amount": sum(o["amount"] for o in clustered_outbound),
    }
