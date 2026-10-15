from __future__ import annotations

from app.ai.state import PlanningState


def scenario_analysis_node(state: PlanningState) -> dict:
    scenarios = state.get("scenarios") or []
    analysis: dict = {"count": len(scenarios), "scenarios": []}
    evidence = list(state.get("evidence") or [])
    for item in scenarios:
        record = {
            "id": item.get("id"),
            "name": item.get("name"),
            "scenario_type": item.get("scenario_type"),
            "planning_horizon_months": item.get("planning_horizon_months"),
            "risk_level": item.get("risk_level"),
            "risk_score": item.get("risk_score"),
            "gpu_demand": item.get("gpu_demand"),
            "power_demand_mw": item.get("power_demand_mw"),
            "storage_demand_tb": item.get("storage_demand_tb"),
            "network_demand_gbps": item.get("network_demand_gbps"),
            "estimated_capex": item.get("estimated_capex"),
            "assumptions": item.get("assumptions") or {},
        }
        analysis["scenarios"].append(record)
        evidence.append({"node": "scenario_analysis", "source": f"database.scenarios:{record['id']}", "facts": record})
    return {"scenario_analysis": analysis, "evidence": evidence}
