from __future__ import annotations

from app.ai.state import PlanningState


def forecast_analysis_node(state: PlanningState) -> dict:
    forecasts = state.get("forecasts") or {}
    summary: dict[str, dict] = {}
    evidence = list(state.get("evidence") or [])
    warnings = list(state.get("warnings") or [])

    for resource, forecast in forecasts.items():
        if not isinstance(forecast, dict) or forecast.get("error"):
            warnings.append(f"{resource}: {forecast.get('error', 'forecast unavailable') if isinstance(forecast, dict) else 'forecast unavailable'}")
            continue
        capacity = forecast.get("capacity") or {}
        accuracy = forecast.get("accuracy") or {}
        item = {
            "run_id": forecast.get("run_id"),
            "model": forecast.get("model"),
            "model_engine": forecast.get("model_engine"),
            "frequency": forecast.get("frequency"),
            "confidence": forecast.get("confidence"),
            "current_usage": capacity.get("current_usage"),
            "current_capacity": capacity.get("current_capacity"),
            "utilization_percent": capacity.get("utilization_percent"),
            "headroom": capacity.get("headroom"),
            "peak_demand": capacity.get("peak_demand"),
            "peak_demand_at": capacity.get("peak_demand_at"),
            "shortage_date": capacity.get("shortage_date"),
            "required_expansion": capacity.get("required_expansion"),
            "unit": forecast.get("unit"),
            "accuracy": accuracy,
        }
        summary[resource] = item
        evidence.append({
            "node": "forecast_analysis",
            "source": f"database.forecast_runs:{item['run_id']}",
            "resource_type": resource,
            "facts": item,
        })
    return {"forecast_analysis": summary, "capacity": summary, "warnings": warnings, "evidence": evidence}
