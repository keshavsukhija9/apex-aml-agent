"""
Pydantic contract for Apex-AML.
This is the frozen shape shared between planner, tools, orchestrator, and frontend.
Do not change field names casually once frontend work starts.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


# ---------- Intent & Filters ----------

class AMLPatternType(str, Enum):
    STRUCTURING = "structuring"
    LAYERING = "layering"
    THRESHOLD_AGGREGATION = "threshold_aggregation"
    ENTITY_LOOKUP = "entity_lookup"
    GLOBAL_PROFILE = "global_profile"
    UNKNOWN = "unknown"


class ExtractedFilters(BaseModel):
    """Parameters extracted from the natural language query."""
    date_range_days: Optional[int] = Field(
        default=None, description="e.g. 'last 30 days' -> 30"
    )
    customer_id: Optional[int] = Field(
        default=None, description="Specific customer ID if query targets one entity"
    )
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    min_transaction_count: Optional[int] = Field(
        default=None, description="e.g. '10+ transactions' -> 10"
    )
    channel: Optional[str] = None
    country: Optional[str] = None


class QueryIntent(BaseModel):
    """Structured output of the intent parser (LLM or regex fallback)."""
    raw_query: str
    pattern_type: AMLPatternType
    filters: ExtractedFilters
    requires_eda: bool = False
    requires_graph: bool = False
    requires_ml: bool = False
    requires_rules: bool = True
    parsed_by: Literal["llm", "regex_fallback"] = "regex_fallback"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ---------- Execution Plan ----------

class ToolName(str, Enum):
    EDA = "eda"
    FEATURE_ENG = "feature_eng"
    RULES = "rules"
    ML = "ml"
    GRAPH = "graph"
    RISK = "risk"
    EXPLAIN = "explain"


class StructuredPlan(BaseModel):
    """The dynamic DAG compiler's output: which tools run, in what order."""
    intent: QueryIntent
    tools_to_execute: list[ToolName]
    tools_skipped: list[ToolName]
    execution_order: list[ToolName]


# ---------- Execution Trace / Output ----------

class ToolExecutionRecord(BaseModel):
    tool: ToolName
    status: Literal["executed", "skipped"]
    duration_ms: Optional[float] = None
    reason: str = Field(description="Why this tool ran or was skipped, tied to query intent")


class RiskTier(str, Enum):
    LOW = "LOW_MONITOR"
    MEDIUM = "MEDIUM_REVIEW"
    HIGH = "HIGH_REPORT"


class EvidenceItem(BaseModel):
    customer_id: int
    risk_tier: RiskTier
    rule_triggered: Optional[str] = None
    statute_reference: Optional[str] = None
    detection_source: Literal["rule_engine", "ml_engine", "graph_engine", "hybrid"]
    explanation: str
    supporting_metrics: dict = Field(default_factory=dict)
    ml_deviation_drivers: list[dict] = Field(default_factory=list, description="Top z-score deviation features from ML layer, if it ran")
    ml_anomaly_score: Optional[float] = None
    hop_trace: list[str] = Field(default_factory=list, description="Multi-hop layering trace, if graph engine ran")
    recommended_action: str


class AgentTrace(BaseModel):
    """Final structured response returned to the frontend."""
    query: str
    intent: QueryIntent
    tool_trace: list[ToolExecutionRecord]
    total_duration_ms: float
    evidence: list[EvidenceItem]
    summary: str
    low_confidence: bool = False
