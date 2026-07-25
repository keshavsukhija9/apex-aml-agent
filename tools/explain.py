"""
Grounded Explanation Tool.
Assembles a human-readable, auditable evidence summary from rule/ML/graph outputs.
Fully templated -- no LLM involved in generating the explanation itself, which is
the core anti-hallucination guarantee: every word here traces back to a computed
value, not a language model's guess.
"""


def build_explanation(
    customer_id: int,
    rule_result: dict = None,
    layering_result: dict = None,
    ml_result: dict = None,
    risk_result: dict = None,
) -> str:
    """
    Compose the final explanation string from whichever detection layers ran.
    Each layer is optional -- this reflects the dynamic DAG: not every query
    runs every tool, so not every field will be populated.
    """
    lines = [f"Customer {customer_id} -- Risk Tier: {risk_result['risk_tier']}"]

    if rule_result and rule_result.get("rule_triggered"):
        lines.append(
            f"RULE VIOLATION: {rule_result['trigger_detail']} "
            f"(Statute: {rule_result['statute_reference']})"
        )

    if layering_result and layering_result.get("rule_triggered"):
        lines.append(
            f"LAYERING DETECTED: {layering_result['trigger_detail']} "
            f"(Statute: {layering_result['statute_reference']})"
        )
        for hop in layering_result.get("hop_trace", []):
            lines.append(f"  {hop}")

    if ml_result and ml_result.get("is_anomaly"):
        drivers = ml_result.get("deviation_drivers", [])
        driver_str = ", ".join(
            f"{d['feature']} (z={d['zscore']})" for d in drivers
        ) if drivers else "no drivers computed"
        lines.append(
            f"ML ANOMALY: flagged as statistical outlier (score: {ml_result['anomaly_score']}). "
            f"Top deviation drivers: {driver_str}"
        )

    lines.append(f"RECOMMENDED ACTION: {risk_result['recommended_action']}")
    lines.append(f"RATIONALE: {risk_result['rationale']}")

    return "\n".join(lines)
