from __future__ import annotations

from app.ai.state import PlanningState


def _risk_level(peak: float, capacity: float, shortage_date: str | None) -> str:
    if capacity <= 0:
        return "unknown"
    ratio = peak / capacity * 100.0
    if ratio >= 100 or shortage_date:
        return "critical"
    if ratio >= 95:
        return "high"
    if ratio >= 85:
        return "medium"
    return "low"


def capacity_risk_node(state: PlanningState) -> dict:
    forecasts = state.get("forecast_analysis") or {}
    alerts = state.get("alerts") or []
    risks: dict[str, dict] = {}
    evidence = list(state.get("evidence") or [])

    for resource, item in forecasts.items():
        peak = float(item.get("peak_demand") or 0)
        capacity = float(item.get("current_capacity") or 0)
        shortage = item.get("shortage_date")
        forecast_util = peak / capacity * 100.0 if capacity > 0 else None
        risk = {
            "risk_level": _risk_level(peak, capacity, shortage),
            "forecast_utilization_percent": round(forecast_util, 2) if forecast_util is not None else None,
            "shortage_date": shortage,
            "headroom": item.get("headroom"),
            "required_expansion": item.get("required_expansion"),
            "active_alert_count": sum(1 for a in alerts if a.get("resource_type") == resource and a.get("status") != "resolved"),
        }
        risks[resource] = risk
        evidence.append({
            "node": "capacity_risk",
            "source": "calculation.from_persisted_forecast",
            "resource_type": resource,
            "facts": risk,
        })
    return {"capacity_risk": risks, "evidence": evidence}
