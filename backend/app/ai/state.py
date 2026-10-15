from __future__ import annotations

from typing import Any, TypedDict


class PlanningState(TypedDict, total=False):
    user_id: str
    question: str
    intent: str
    data_center_id: int | None
    data_center_ids: list[int]
    metrics: dict[str, Any]
    forecasts: dict[str, Any]
    capacity: dict[str, Any]
    scenarios: list[dict[str, Any]]
    procurement: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    analysis: dict[str, Any]
    forecast_analysis: dict[str, Any]
    capacity_risk: dict[str, Any]
    scenario_analysis: dict[str, Any]
    procurement_analysis: dict[str, Any]
    recommendations: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    warnings: list[str]
    provider: str
    final_response: str
