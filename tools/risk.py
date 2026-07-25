"""
Risk Classification Tool.
Maps rule triggers + ML anomaly signals to a risk tier and escalation action.
Deliberately simple, deterministic mapping -- this is a place where an auditor
must be able to reproduce the tier from the inputs by hand, no black box.
"""

from agent.schemas import RiskTier


def classify_risk(
    rule_triggered: bool = False,
    layering_triggered: bool = False,
    ml_is_anomaly: bool = False,
    ml_anomaly_score: float = None,
) -> dict:
    """
    Risk tiering logic:
      HIGH/REPORT   -> any hard rule violation (structuring OR layering)
      MEDIUM/REVIEW -> ML flags anomaly but no rule violation
      LOW/MONITOR   -> no rule violation, no ML anomaly

    Rules take precedence over ML: a statutory threshold violation is HIGH
    regardless of what the ML layer says, since rules are the primary,
    auditable signal and ML is explicitly the fallback/assistive layer.
    """
    if rule_triggered or layering_triggered:
        tier = RiskTier.HIGH
        action = "REPORT (File SAR - Suspicious Activity Report)"
        rationale = "Deterministic regulatory rule violation detected -- mandatory escalation regardless of ML signal."
    elif ml_is_anomaly:
        tier = RiskTier.MEDIUM
        action = "REVIEW (Manual analyst review recommended)"
        rationale = f"No hard rule violation, but ML anomaly detection flagged this entity (score: {ml_anomaly_score})."
    else:
        tier = RiskTier.LOW
        action = "MONITOR (No action required, continue routine monitoring)"
        rationale = "No rule violations and no ML anomaly signal detected."

    return {
        "risk_tier": tier.value,
        "recommended_action": action,
        "rationale": rationale,
    }
