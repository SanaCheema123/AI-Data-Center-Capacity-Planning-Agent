from __future__ import annotations

from app.ai.state import PlanningState

DEPENDENCIES = {
    "gpu": ["power capacity", "cooling", "network throughput"],
    "power": ["utility / electrical infrastructure", "cooling"],
    "storage": ["storage fabric", "rack space"],
    "network": ["switching capacity", "uplinks"],
}


def recommendation_node(state: PlanningState) -> dict:
    forecasts = state.get("forecast_analysis") or {}
    risks = state.get("capacity_risk") or {}
    procurement = state.get("procurement_analysis") or {}
    procurement_items = procurement.get("items") or []
    by_resource = {x.get("resource_type"): x for x in procurement_items}
    recommendations: list[dict] = []
    evidence = list(state.get("evidence") or [])

    for resource, f in forecasts.items():
        required = float(f.get("required_expansion") or 0)
        unit = f.get("unit") or "units"
        shortage = f.get("shortage_date")
        procurement_item = by_resource.get(resource)
        needs = required > 0
        risk = (risks.get(resource) or {}).get("risk_level", "unknown")
        rec = {
            "resource_type": resource,
            "recommendation": (
                f"Increase {resource} capacity by {required:.1f} {unit}."
                if needs else f"Maintain current {resource} capacity."
            ),
            "reason": (
                "Persisted forecast peak exceeds current capacity within the selected horizon."
                if needs else "Persisted forecast peak remains within current capacity for the selected horizon."
            ),
            "supporting_metrics": {
                "forecast_run_id": f.get("run_id"),
                "current_capacity": f.get("current_capacity"),
                "current_usage": f.get("current_usage"),
                "forecast_peak": f.get("peak_demand"),
                "utilization_percent": f.get("utilization_percent"),
                "forecast_utilization_percent": (risks.get(resource) or {}).get("forecast_utilization_percent"),
                "headroom": f.get("headroom"),
                "shortage_date": shortage,
            },
            "expected_impact": (
                "Restore capacity headroom relative to the persisted forecast peak."
                if needs else "Preserve current forecast capacity headroom."
            ),
            "risk": risk,
            "dependencies": DEPENDENCIES.get(resource, []),
            "time_horizon": shortage or f"{f.get('frequency', 'forecast')} planning horizon",
            "confidence": f.get("confidence") or 0.0,
            "assumptions": [
                f"Forecast model: {f.get('model_engine') or f.get('model')}",
                "Recommendation is based only on persisted forecast and capacity results.",
            ],
            "procurement": procurement_item,
        }
        recommendations.append(rec)
        evidence.append({
            "node": "recommendations",
            "source": f"derived.from_forecast_run:{f.get('run_id')}",
            "resource_type": resource,
            "facts": rec,
        })
    return {"recommendations": recommendations, "evidence": evidence}
