from __future__ import annotations

from app.ai.state import PlanningState


def data_analysis_node(state: PlanningState) -> dict:
    metrics = state.get("metrics") or {}
    warnings = list(state.get("warnings") or [])
    row_count = int(metrics.get("metric_row_count") or 0)
    coverage_start = metrics.get("coverage_start")
    coverage_end = metrics.get("coverage_end")
    counts = metrics.get("metric_counts") or {}

    if row_count == 0:
        warnings.append("Insufficient data for reliable forecast.")
    analysis = {
        "metric_row_count": row_count,
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "available_metric_types": sorted(counts.keys()),
        "data_centers": metrics.get("data_centers") or [],
        "data_sufficiency": "sufficient" if row_count > 0 else "insufficient",
    }
    evidence = list(state.get("evidence") or [])
    evidence.append({
        "node": "data_analysis",
        "source": "database.infrastructure_metrics",
        "facts": analysis,
    })
    return {"analysis": analysis, "warnings": warnings, "evidence": evidence}
