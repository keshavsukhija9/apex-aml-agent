"""
Intent parser (regex-based deterministic fallback) + Dynamic DAG compiler.

Design principle: this parser must NEVER throw on malformed input.
Worst case it falls back to AMLPatternType.UNKNOWN with a safe default plan
(run everything) rather than crashing the request.
"""

import re
from agent.schemas import (
    QueryIntent, ExtractedFilters, AMLPatternType,
    StructuredPlan, ToolName
)


# ---------- Regex-based deterministic intent parser ----------

def parse_intent_regex(query: str) -> QueryIntent:
    """
    Deterministic fallback intent parser. No network calls, no LLM.
    Covers the exact query patterns from the problem statement's example table,
    plus reasonable variations.
    """
    q = query.lower().strip()
    filters = ExtractedFilters()

    # --- date range extraction: "last N days" ---
    date_match = re.search(r"last\s+(\d+)\s+day", q)
    if date_match:
        filters.date_range_days = int(date_match.group(1))

    # --- customer ID extraction: "customer 9011", "customer id 4521" ---
    cust_match = re.search(r"customer\s*(?:id)?\s*#?(\d{3,6})", q)
    if cust_match:
        filters.customer_id = int(cust_match.group(1))

    # --- transaction count threshold: "10+ transactions", "10 or more" ---
    count_match = re.search(r"(\d+)\+?\s*(?:or more\s*)?transactions?", q)
    if count_match:
        filters.min_transaction_count = int(count_match.group(1))

    # --- amount threshold: "under $10,000", "under 10000" ---
    amount_match = re.search(r"under\s*\$?([\d,]+)", q)
    if amount_match:
        filters.max_amount = float(amount_match.group(1).replace(",", ""))

    # --- pattern classification (order matters: most specific first) ---

    # Single entity lookup
    if filters.customer_id is not None and (
        "suspicious" in q or "risk" in q or "flag" in q or "explain" in q
    ):
        return QueryIntent(
            raw_query=query,
            pattern_type=AMLPatternType.ENTITY_LOOKUP,
            filters=filters,
            requires_eda=False,
            requires_graph=True,
            requires_ml=False,
            requires_rules=True,
            parsed_by="regex_fallback",
            confidence=0.95,
        )

    # Threshold aggregation query (structuring via direct count, no ML needed)
    if filters.min_transaction_count is not None and filters.max_amount is not None:
        return QueryIntent(
            raw_query=query,
            pattern_type=AMLPatternType.THRESHOLD_AGGREGATION,
            filters=filters,
            requires_eda=False,
            requires_graph=False,
            requires_ml=False,
            requires_rules=True,
            parsed_by="regex_fallback",
            confidence=0.95,
        )

    # Structuring pattern search
    if "structuring" in q or "smurf" in q:
        return QueryIntent(
            raw_query=query,
            pattern_type=AMLPatternType.STRUCTURING,
            filters=filters,
            requires_eda=False,
            requires_graph=False,
            requires_ml=True,
            requires_rules=True,
            parsed_by="regex_fallback",
            confidence=0.9,
        )

    # Layering pattern search
    if "layering" in q or "multi-hop" in q or "multi hop" in q:
        return QueryIntent(
            raw_query=query,
            pattern_type=AMLPatternType.LAYERING,
            filters=filters,
            requires_eda=False,
            requires_graph=True,
            requires_ml=False,
            requires_rules=True,
            parsed_by="regex_fallback",
            confidence=0.9,
        )

    # Global/broad exploration query
    if any(kw in q for kw in ["profile", "distribution", "overview", "explore", "global"]):
        return QueryIntent(
            raw_query=query,
            pattern_type=AMLPatternType.GLOBAL_PROFILE,
            filters=filters,
            requires_eda=True,
            requires_graph=False,
            requires_ml=False,
            requires_rules=False,
            parsed_by="regex_fallback",
            confidence=0.85,
        )

    # Fallback: unknown intent -> safe default, run everything except graph
    # (graph is expensive; only run it when explicitly relevant)
    return QueryIntent(
        raw_query=query,
        pattern_type=AMLPatternType.UNKNOWN,
        filters=filters,
        requires_eda=True,
        requires_graph=False,
        requires_ml=True,
        requires_rules=True,
        parsed_by="regex_fallback",
        confidence=0.3,
    )


# ---------- Dynamic DAG compiler ----------

def compile_execution_plan(intent: QueryIntent) -> StructuredPlan:
    """
    Given a parsed intent, decide which tools execute and in what order.
    This is the anti-fixed-pipeline core: NOT every query runs every tool.
    Fine-grained nodes (RULES, ML, GRAPH separately) so the visual DAG trace
    actually differs per query -- this is the core demo-magnetism requirement.
    """
    tools_to_execute: list[ToolName] = []

    if intent.requires_eda:
        tools_to_execute.append(ToolName.EDA)

    needs_detection = intent.requires_rules or intent.requires_ml or intent.requires_graph
    if needs_detection:
        tools_to_execute.append(ToolName.FEATURE_ENG)

    if intent.requires_rules:
        tools_to_execute.append(ToolName.RULES)

    if intent.requires_ml:
        tools_to_execute.append(ToolName.ML)

    if intent.requires_graph:
        tools_to_execute.append(ToolName.GRAPH)

    if needs_detection:
        tools_to_execute.append(ToolName.RISK)
        tools_to_execute.append(ToolName.EXPLAIN)

    all_tools = list(ToolName)
    tools_skipped = [t for t in all_tools if t not in tools_to_execute]

    return StructuredPlan(
        intent=intent,
        tools_to_execute=tools_to_execute,
        tools_skipped=tools_skipped,
        execution_order=tools_to_execute,
    )


# ---------- Public entry point (LLM hook goes here later) ----------

def plan_from_query(query: str) -> StructuredPlan:
    """
    Main entry point. For now, always uses the regex fallback.
    Step 5+ will insert an LLM-first path here, with this function
    as the guaranteed fallback if the LLM call fails or times out.
    """
    intent = parse_intent_regex(query)
    return compile_execution_plan(intent)
