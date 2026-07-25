"""
Orchestrator: the custom state machine that executes the compiled DAG plan.

This is the anti-fixed-pipeline core at runtime -- not just in planning.
Each tool call is timed and logged into the trace regardless of whether it
ran or was skipped, which is what the frontend DAG viewer renders.
"""

import time
import pandas as pd

from agent.schemas import (
    ToolName, AgentTrace, ToolExecutionRecord, EvidenceItem, RiskTier
)
from agent.planner import plan_from_query
from tools.feature_eng import (
    load_transactions, engineer_features, get_customer_summary,
    build_transaction_graph, detect_layering_pattern,
)
from tools.detection import (
    apply_structuring_rules, apply_layering_rule,
    run_isolation_forest, get_ml_result_for_customer,
)
from tools.risk import classify_risk
from tools.explain import build_explanation


class ApexOrchestrator:
    """
    Loads the dataset once (cached in memory), then executes dynamic plans
    per query. In a real production system this would be backed by a database;
    for the hackathon scope, in-memory pandas is the correct trade-off.
    """

    def __init__(self, data_path: str = "data/transactions.csv"):
        self.df_raw = load_transactions(data_path)
        self.df_featured = None
        self.graph = None
        self.ml_results = None

    def _ensure_features(self):
        if self.df_featured is None:
            self.df_featured = engineer_features(self.df_raw)

    def _ensure_graph(self):
        if self.graph is None:
            self.graph = build_transaction_graph(self.df_raw)

    def _ensure_ml(self):
        if self.ml_results is None:
            self._ensure_features()
            self.ml_results = run_isolation_forest(self.df_featured)

    def _get_target_customer_ids(self, intent) -> list[int]:
        """
        Determine which customers this query applies to.
        Entity lookup -> single customer. Otherwise -> scan candidates,
        narrowed by date_range_days if the query specified one -- this is
        what makes "last 30 days" actually restrict the evaluated population
        rather than just being displayed and ignored.
        """
        if intent.filters.customer_id is not None:
            return [intent.filters.customer_id]

        df = self.df_raw
        if intent.filters.date_range_days is not None:
            cutoff = df["timestamp"].max() - pd.Timedelta(days=intent.filters.date_range_days)
            df = df[df["timestamp"] >= cutoff]

        return df["customer_id"].unique().tolist()

    def run_query(self, query: str) -> AgentTrace:
        start_total = time.perf_counter()
        plan = plan_from_query(query)
        intent = plan.intent

        tool_trace: list[ToolExecutionRecord] = []
        evidence: list[EvidenceItem] = []

        # ---------- EDA ----------
        if ToolName.EDA in plan.tools_to_execute:
            t0 = time.perf_counter()
            eda_summary = {
                "total_transactions": len(self.df_raw),
                "unique_customers": int(self.df_raw["customer_id"].nunique()),
                "date_range": [
                    str(self.df_raw["timestamp"].min()),
                    str(self.df_raw["timestamp"].max()),
                ],
                "mean_amount": float(self.df_raw["amount"].mean()),
                "channels": self.df_raw["channel"].value_counts().to_dict(),
            }
            duration = (time.perf_counter() - t0) * 1000
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.EDA, status="executed", duration_ms=round(duration, 2),
                reason="Query requires broad exploratory profiling of the dataset."
            ))
        else:
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.EDA, status="skipped", duration_ms=None,
                reason="Query is targeted (specific pattern or entity), not exploratory -- EDA bypassed."
            ))

        # ---------- FEATURE ENG ----------
        if ToolName.FEATURE_ENG in plan.tools_to_execute:
            t0 = time.perf_counter()
            self._ensure_features()
            duration = (time.perf_counter() - t0) * 1000
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.FEATURE_ENG, status="executed", duration_ms=round(duration, 2),
                reason="Downstream detection (rules/ML/graph) requires engineered features."
            ))
        else:
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.FEATURE_ENG, status="skipped", duration_ms=None,
                reason="No detection tool requires engineered features for this query."
            ))

        # ---------- GRAPH ----------
        graph_results_by_customer = {}
        if ToolName.GRAPH in plan.tools_to_execute:
            t0 = time.perf_counter()
            self._ensure_graph()
            target_ids = self._get_target_customer_ids(intent)
            for cid in target_ids:
                graph_results_by_customer[cid] = detect_layering_pattern(self.graph, cid)
            duration = (time.perf_counter() - t0) * 1000
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.GRAPH, status="executed", duration_ms=round(duration, 2),
                reason="Query intent involves multi-hop / layering / entity-relationship analysis."
            ))
        else:
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.GRAPH, status="skipped", duration_ms=None,
                reason="Query does not require multi-hop relationship analysis."
            ))

        # ---------- RULES ----------
        rule_results_by_customer = {}
        if ToolName.RULES in plan.tools_to_execute:
            t0 = time.perf_counter()
            target_ids = self._get_target_customer_ids(intent)
            for cid in target_ids:
                summary = get_customer_summary(self.df_featured, cid)
                rule_results_by_customer[cid] = apply_structuring_rules(summary)
            duration = (time.perf_counter() - t0) * 1000
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.RULES, status="executed", duration_ms=round(duration, 2),
                reason="Query requires deterministic regulatory threshold evaluation."
            ))
        else:
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.RULES, status="skipped", duration_ms=None,
                reason="Query does not require rule-based threshold evaluation."
            ))

        # ---------- ML ----------
        ml_results_by_customer = {}
        if ToolName.ML in plan.tools_to_execute:
            t0 = time.perf_counter()
            self._ensure_ml()
            target_ids = self._get_target_customer_ids(intent)
            for cid in target_ids:
                ml_results_by_customer[cid] = get_ml_result_for_customer(self.ml_results, cid)
            duration = (time.perf_counter() - t0) * 1000
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.ML, status="executed", duration_ms=round(duration, 2),
                reason="Query intent explicitly calls for statistical anomaly detection."
            ))
        else:
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.ML, status="skipped", duration_ms=None,
                reason="Rule-based path is sufficient for this query type; ML skipped to avoid unnecessary latency."
            ))

        # ---------- RISK + EXPLAIN ----------
        needs_risk = ToolName.RISK in plan.tools_to_execute
        if needs_risk:
            t0 = time.perf_counter()
            target_ids = self._get_target_customer_ids(intent)

            for cid in target_ids:
                rule_result = rule_results_by_customer.get(cid, {"rule_triggered": False})
                layering_result = apply_layering_rule(
                    graph_results_by_customer.get(cid, {"is_layering_intermediate": False})
                )
                ml_result = ml_results_by_customer.get(cid, {"is_anomaly": False, "anomaly_score": None, "deviation_drivers": []})

                risk_result = classify_risk(
                    rule_triggered=rule_result.get("rule_triggered", False),
                    layering_triggered=layering_result.get("rule_triggered", False),
                    ml_is_anomaly=ml_result.get("is_anomaly", False),
                    ml_anomaly_score=ml_result.get("anomaly_score"),
                )

                # Only surface as evidence if something actually triggered --
                # avoids flooding the response with 500 "LOW_MONITOR, nothing happened" rows
                is_flagged = (
                    rule_result.get("rule_triggered", False)
                    or layering_result.get("rule_triggered", False)
                    or ml_result.get("is_anomaly", False)
                )

                if is_flagged or intent.filters.customer_id is not None:
                    explanation = build_explanation(
                        cid, rule_result, layering_result, ml_result, risk_result
                    )
                    detection_source = "hybrid"
                    if rule_result.get("rule_triggered") and not layering_result.get("rule_triggered"):
                        detection_source = "rule_engine"
                    elif layering_result.get("rule_triggered"):
                        detection_source = "graph_engine"
                    elif ml_result.get("is_anomaly"):
                        detection_source = "ml_engine"

                    evidence.append(EvidenceItem(
                        customer_id=int(cid),
                        risk_tier=RiskTier(risk_result["risk_tier"]),
                        rule_triggered=rule_result.get("rule_name") or layering_result.get("rule_name"),
                        statute_reference=rule_result.get("statute_reference") or layering_result.get("statute_reference"),
                        detection_source=detection_source,
                        explanation=explanation,
                        supporting_metrics={
                            "rolling_24h_sub_threshold_count": rule_result.get("trigger_detail", ""),
                        },
                        recommended_action=risk_result["recommended_action"],
                    ))

            duration = (time.perf_counter() - t0) * 1000
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.RISK, status="executed", duration_ms=round(duration, 2),
                reason="Detection layer(s) ran; risk tiering applied to results."
            ))
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.EXPLAIN, status="executed", duration_ms=0.0,
                reason="Evidence explanations generated inline with risk classification."
            ))
        else:
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.RISK, status="skipped", duration_ms=None,
                reason="No detection tool ran; risk classification not applicable."
            ))
            tool_trace.append(ToolExecutionRecord(
                tool=ToolName.EXPLAIN, status="skipped", duration_ms=None,
                reason="No risk classification was performed."
            ))

        total_duration = (time.perf_counter() - start_total) * 1000

        # Sort evidence by risk severity, highest first
        severity_order = {"HIGH_REPORT": 0, "MEDIUM_REVIEW": 1, "LOW_MONITOR": 2}
        evidence.sort(key=lambda e: severity_order.get(e.risk_tier.value, 99))

        summary = (
            f"Query processed in {total_duration:.1f}ms. "
            f"{len(evidence)} entities flagged out of "
            f"{len(self._get_target_customer_ids(intent))} evaluated."
        )

        return AgentTrace(
            query=query,
            intent=intent,
            tool_trace=tool_trace,
            total_duration_ms=round(total_duration, 2),
            evidence=evidence,
            summary=summary,
        )
