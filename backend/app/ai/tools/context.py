from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.domain import Alert, DataCenter, InfrastructureMetric, ProcurementRecommendation
from app.services.forecasting import ForecastingService
from app.services.planning import ProcurementService, ScenarioService

RESOURCE_TYPES = ("gpu", "power", "storage", "network")


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def get_scope_metrics(db: Session, data_center_id: int | None) -> dict[str, Any]:
    """Return verified current metric values and data coverage from PostgreSQL."""
    stmt = select(InfrastructureMetric)
    if data_center_id is not None:
        stmt = stmt.where(InfrastructureMetric.data_center_id == data_center_id)
    rows = list(db.scalars(stmt.order_by(InfrastructureMetric.timestamp)))
    latest: dict[tuple[int, str], InfrastructureMetric] = {}
    counts: dict[str, int] = defaultdict(int)
    timestamps: list[datetime] = []
    for row in rows:
        counts[row.metric_name] += 1
        timestamps.append(row.timestamp)
        key = (row.data_center_id, row.metric_name)
        old = latest.get(key)
        if old is None or row.timestamp > old.timestamp:
            latest[key] = row

    totals: dict[str, float] = defaultdict(float)
    latest_by_metric: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (dc_id, metric_name), row in latest.items():
        totals[metric_name] += float(row.value)
        latest_by_metric[metric_name].append({
            "data_center_id": dc_id,
            "value": float(row.value),
            "unit": row.unit,
            "timestamp": row.timestamp.isoformat(),
        })

    dc_stmt = select(DataCenter)
    if data_center_id is not None:
        dc_stmt = dc_stmt.where(DataCenter.id == data_center_id)
    data_centers = [
        {"id": dc.id, "name": dc.name, "code": dc.code, "region": dc.region, "status": dc.status}
        for dc in db.scalars(dc_stmt)
    ]
    return {
        "data_centers": data_centers,
        "metric_row_count": len(rows),
        "coverage_start": min(timestamps).isoformat() if timestamps else None,
        "coverage_end": max(timestamps).isoformat() if timestamps else None,
        "metric_counts": dict(counts),
        "latest_totals": dict(totals),
        "latest_by_metric": dict(latest_by_metric),
    }


def get_forecasts(db: Session, data_center_id: int | None) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for resource in RESOURCE_TYPES:
        try:
            output[resource] = ForecastingService.latest(db, resource, data_center_id).model_dump(mode="json")
        except Exception as exc:  # no fabricated fallback
            output[resource] = {"error": str(exc)}
    return output


def get_scenarios(db: Session, data_center_id: int | None) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in ScenarioService.compare(db, data_center_id)]


def get_procurement(db: Session, data_center_id: int | None, generate_if_missing: bool = True) -> list[dict[str, Any]]:
    scope = ProcurementRecommendation.data_center_id.is_(None) if data_center_id is None else ProcurementRecommendation.data_center_id == data_center_id
    rows = list(db.scalars(select(ProcurementRecommendation).where(scope).order_by(ProcurementRecommendation.created_at.desc())))
    if not rows and generate_if_missing:
        rows = ProcurementService.generate(db, data_center_id)
    return [
        {
            "id": row.id,
            "resource_type": row.resource_type,
            "current_capacity": row.current_capacity,
            "required_capacity": row.required_capacity,
            "quantity": row.quantity,
            "required_by": row.required_by.isoformat() if row.required_by else None,
            "priority": row.priority,
            "status": row.status,
            "estimated_cost": row.estimated_cost,
            "reason": row.reason,
            "forecast_run_id": row.forecast_run_id,
        }
        for row in rows
    ]


def get_alerts(db: Session, data_center_id: int | None) -> list[dict[str, Any]]:
    stmt = select(Alert)
    if data_center_id is not None:
        stmt = stmt.where(Alert.data_center_id == data_center_id)
    rows = list(db.scalars(stmt.order_by(Alert.triggered_at.desc())))
    return [
        {
            "id": row.id,
            "data_center_id": row.data_center_id,
            "resource_type": row.resource_type,
            "severity": row.severity,
            "title": row.title,
            "description": row.description,
            "current_value": row.current_value,
            "threshold_value": row.threshold_value,
            "forecast_value": row.forecast_value,
            "predicted_shortage_at": row.predicted_shortage_at.isoformat() if row.predicted_shortage_at else None,
            "status": row.status,
            "triggered_at": row.triggered_at.isoformat(),
        }
        for row in rows
    ]
