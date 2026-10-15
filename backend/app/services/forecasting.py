from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from math import ceil
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.forecasting import ForecastRequest, TimePoint, default_registry
from app.forecasting.utils import capacity_headroom, peak_demand, required_expansion, shortage_date, utilization_percent
from app.models.domain import DataCenter, ForecastModel as ForecastModelRecord, ForecastResult, ForecastRun, InfrastructureMetric, User
from app.services.data_scope import ensure_real_data_center, real_data_center_ids
from app.schemas.forecasting import (
    AccuracyMetrics,
    CapacitySummary,
    ForecastPointRead,
    ForecastResponse,
    ForecastRunRequest,
)

RESOURCE_CONFIG = {
    # Capacity planning forecasts must aggregate *across data centers*, not sum
    # repeated samples inside the same month. Power/network use the peak sample
    # per data center per period; storage uses the latest sample per period.
    "power": {"usage": "power_usage_mw", "capacity": "power_capacity_mw", "unit": "MW", "aggregation": "max"},
    "storage": {"usage": "storage_used_tb", "capacity": "storage_capacity_tb", "unit": "TB", "aggregation": "latest"},
    "network": {"usage": "network_throughput_gbps", "capacity": "network_capacity_gbps", "unit": "Gbps", "aggregation": "max"},
}


class ForecastingService:
    @staticmethod
    def _scope_filter(db: Session, stmt, data_center_id: int | None):
        if data_center_id is not None:
            return stmt.where(InfrastructureMetric.data_center_id == data_center_id)
        real_ids = real_data_center_ids(db)
        if not real_ids:
            return stmt.where(InfrastructureMetric.id == -1)
        return stmt.where(InfrastructureMetric.data_center_id.in_(real_ids))

    @staticmethod
    def _ensure_data_center(db: Session, data_center_id: int | None) -> None:
        if data_center_id is not None and ensure_real_data_center(db, data_center_id) is None:
            raise NotFoundError("Data center not found or has no real telemetry")

    @staticmethod
    def _metrics(db: Session, names: Iterable[str], data_center_id: int | None) -> list[InfrastructureMetric]:
        stmt = select(InfrastructureMetric).where(InfrastructureMetric.metric_name.in_(list(names))).order_by(InfrastructureMetric.timestamp)
        stmt = ForecastingService._scope_filter(db, stmt, data_center_id)
        return list(db.scalars(stmt))

    @staticmethod
    def _bucket(ts: datetime, frequency: str) -> tuple[int, ...]:
        if frequency == "daily":
            return ts.year, ts.month, ts.day
        if frequency == "weekly":
            iso = ts.isocalendar()
            return iso.year, iso.week
        return ts.year, ts.month

    @staticmethod
    def _aggregate(rows: list[InfrastructureMetric], metric_name: str, frequency: str, mode: str = "max") -> list[TimePoint]:
        """Aggregate telemetry without double-counting repeated samples.

        First reduce each data center to one representative value per period,
        then sum those period values across the selected real-data scope. This
        keeps monthly power/storage/network values in their physical units.
        """
        per_dc_bucket: dict[tuple[int, tuple[int, ...]], list[InfrastructureMetric]] = defaultdict(list)
        for row in rows:
            if row.metric_name == metric_name:
                per_dc_bucket[(row.data_center_id, ForecastingService._bucket(row.timestamp, frequency))].append(row)

        combined: dict[tuple[int, ...], float] = defaultdict(float)
        dates: dict[tuple[int, ...], datetime] = {}
        for (_, bucket), items in per_dc_bucket.items():
            items = sorted(items, key=lambda r: r.timestamp)
            values = [float(r.value) for r in items]
            if mode == "latest":
                value = float(items[-1].value)
                ts = items[-1].timestamp
            elif mode == "mean":
                value = sum(values) / len(values)
                ts = items[-1].timestamp
            elif mode == "sum":
                value = sum(values)
                ts = items[-1].timestamp
            else:  # peak demand for power/network capacity planning
                value = max(values)
                ts = max(items, key=lambda r: float(r.value)).timestamp
            combined[bucket] += value
            dates[bucket] = max(dates.get(bucket, ts), ts)

        return [TimePoint(timestamp=dates[b], value=combined[b]) for b in sorted(combined, key=lambda x: dates[x])]

    @staticmethod
    def _latest_capacity(rows: list[InfrastructureMetric], capacity_metric: str, data_center_id: int | None) -> float:
        relevant = [r for r in rows if r.metric_name == capacity_metric]
        if not relevant:
            raise ValueError("Insufficient data for reliable forecast.")
        if data_center_id is not None:
            latest = max(relevant, key=lambda r: r.timestamp)
            return float(latest.value)
        latest_by_dc: dict[int, InfrastructureMetric] = {}
        for row in relevant:
            current = latest_by_dc.get(row.data_center_id)
            if current is None or row.timestamp > current.timestamp:
                latest_by_dc[row.data_center_id] = row
        return float(sum(row.value for row in latest_by_dc.values()))

    @staticmethod
    def _gpu_history_and_capacity(db: Session, data_center_id: int | None, frequency: str) -> tuple[list[TimePoint], float]:
        rows = ForecastingService._metrics(db, ["gpu_utilization", "installed_gpus"], data_center_id)
        # Keep clusters separate. Averaging utilization across clusters and then
        # applying only the largest installed-GPU sample under-counts multi-cluster
        # data centers. Demand is calculated per cluster, then summed by period.
        by_cluster_bucket: dict[tuple[int, int | None, tuple[int, ...]], dict[str, list[InfrastructureMetric]]] = defaultdict(lambda: defaultdict(list))
        for row in rows:
            by_cluster_bucket[(row.data_center_id, row.cluster_id, ForecastingService._bucket(row.timestamp, frequency))][row.metric_name].append(row)

        demand_by_bucket: dict[tuple[int, ...], float] = defaultdict(float)
        date_by_bucket: dict[tuple[int, ...], datetime] = {}
        latest_capacity_by_cluster: dict[tuple[int, int | None], InfrastructureMetric] = {}
        for (dc_id, cluster_id, bucket), metrics in by_cluster_bucket.items():
            utils = metrics.get("gpu_utilization", [])
            installed = metrics.get("installed_gpus", [])
            if utils and installed:
                util = sum(float(x.value) for x in utils) / len(utils)
                capacity_sample = max(installed, key=lambda x: x.timestamp)
                demand_by_bucket[bucket] += util / 100.0 * float(capacity_sample.value)
                date_by_bucket[bucket] = max(date_by_bucket.get(bucket, utils[-1].timestamp), max(x.timestamp for x in utils))
            for cap in installed:
                key = (dc_id, cluster_id)
                current = latest_capacity_by_cluster.get(key)
                if current is None or cap.timestamp > current.timestamp:
                    latest_capacity_by_cluster[key] = cap
        history = [TimePoint(timestamp=date_by_bucket[b], value=demand_by_bucket[b]) for b in sorted(demand_by_bucket, key=lambda x: date_by_bucket[x])]
        capacity = float(sum(float(r.value) for r in latest_capacity_by_cluster.values()))
        if not history or capacity <= 0:
            raise ValueError("Insufficient data for reliable forecast.")
        return history, capacity

    @staticmethod
    def history_and_capacity(db: Session, resource_type: str, data_center_id: int | None, frequency: str) -> tuple[list[TimePoint], float, str]:
        ForecastingService._ensure_data_center(db, data_center_id)
        if resource_type == "gpu":
            history, capacity = ForecastingService._gpu_history_and_capacity(db, data_center_id, frequency)
            return history, capacity, "GPUs"
        try:
            config = RESOURCE_CONFIG[resource_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported resource type: {resource_type}") from exc
        rows = ForecastingService._metrics(db, [config["usage"], config["capacity"]], data_center_id)
        history = ForecastingService._aggregate(rows, config["usage"], frequency, config["aggregation"])
        capacity = ForecastingService._latest_capacity(rows, config["capacity"], data_center_id)
        if not history:
            raise ValueError("Insufficient data for reliable forecast.")
        return history, capacity, config["unit"]

    @staticmethod
    def run(db: Session, payload: ForecastRunRequest, user: User | None = None) -> ForecastResponse:
        history, capacity, unit = ForecastingService.history_and_capacity(db, payload.resource_type, payload.data_center_id, payload.frequency)
        model_record = db.scalar(select(ForecastModelRecord).where(ForecastModelRecord.model_type == payload.model, ForecastModelRecord.is_enabled.is_(True)))
        if model_record is None:
            raise NotFoundError(f"Forecast model '{payload.model}' is not configured")

        run = ForecastRun(
            resource_type=payload.resource_type,
            model_id=model_record.id,
            data_center_id=payload.data_center_id,
            requested_by=user.id if user else None,
            status="running",
            horizon_months=payload.horizon if payload.frequency == "monthly" else max(1, ceil(payload.horizon / 4.0) if payload.frequency == "weekly" else ceil(payload.horizon / 30.0)),
            frequency=payload.frequency,
            confidence_interval=payload.confidence,
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.flush()

        try:
            model = default_registry().create(payload.model)
            series = model.fit_predict(ForecastRequest(history=history, horizon=payload.horizon, frequency=payload.frequency, confidence=payload.confidence))
            peak = peak_demand(series.points)
            if peak is None:
                raise ValueError("Forecast produced no results.")
            shortage = shortage_date(series.points, capacity)
            current_usage = float(history[-1].value)
            headroom = capacity_headroom(capacity, current_usage)
            expansion = required_expansion(peak.predicted, capacity)
            util = utilization_percent(current_usage, capacity)

            for point in series.points:
                db.add(ForecastResult(
                    forecast_run_id=run.id,
                    timestamp=point.timestamp,
                    predicted_value=point.predicted,
                    lower_bound=point.lower,
                    upper_bound=point.upper,
                    capacity_value=capacity,
                    unit=unit,
                ))
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.metrics = {
                **series.metrics,
                "model_engine": series.metadata.get("engine", series.model_name),
                "current_usage": current_usage,
                "current_capacity": capacity,
                "utilization_percent": util,
                "headroom": headroom,
                "peak_demand": peak.predicted,
                "peak_demand_at": peak.timestamp.isoformat(),
                "shortage_date": shortage.isoformat() if shortage else None,
                "required_expansion": expansion,
                "history_points": len(history),
                "data_origin": "real",
                "data_center_ids": [payload.data_center_id] if payload.data_center_id is not None else real_data_center_ids(db),
            }
            db.commit()
            db.refresh(run)
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise

        return ForecastingService.response_for_run(db, run.id)

    @staticmethod
    def response_for_run(db: Session, run_id: int) -> ForecastResponse:
        run = db.get(ForecastRun, run_id)
        if run is None:
            raise NotFoundError("Forecast run not found")
        model_record = db.get(ForecastModelRecord, run.model_id)
        results = list(db.scalars(select(ForecastResult).where(ForecastResult.forecast_run_id == run.id).order_by(ForecastResult.timestamp)))
        if run.status != "completed" or not results:
            raise ValueError(run.error_message or "Forecast run has no completed results.")
        metrics = run.metrics or {}
        peak_at = datetime.fromisoformat(str(metrics["peak_demand_at"]))
        shortage_raw = metrics.get("shortage_date")
        accuracy = AccuracyMetrics(
            mae=float(metrics.get("mae", 0.0)), rmse=float(metrics.get("rmse", 0.0)),
            mape=float(metrics.get("mape", 0.0)), r2=float(metrics.get("r2", 0.0)),
        )
        capacity = CapacitySummary(
            current_usage=float(metrics["current_usage"]), current_capacity=float(metrics["current_capacity"]),
            utilization_percent=float(metrics["utilization_percent"]), headroom=float(metrics["headroom"]),
            peak_demand=float(metrics["peak_demand"]), peak_demand_at=peak_at,
            shortage_date=datetime.fromisoformat(shortage_raw) if shortage_raw else None,
            required_expansion=float(metrics["required_expansion"]),
        )
        return ForecastResponse(
            run_id=run.id,
            resource_type=run.resource_type,
            model=model_record.model_type if model_record else "unknown",
            model_engine=str(metrics.get("model_engine", model_record.model_type if model_record else "unknown")),
            unit=results[0].unit,
            data_center_id=run.data_center_id,
            frequency=run.frequency,
            confidence=run.confidence_interval,
            capacity=capacity,
            accuracy=accuracy,
            points=[ForecastPointRead(timestamp=r.timestamp, predicted=r.predicted_value, lower=r.lower_bound, upper=r.upper_bound, capacity=r.capacity_value) for r in results],
        )

    @staticmethod
    def latest(db: Session, resource_type: str, data_center_id: int | None = None) -> ForecastResponse:
        stmt = select(ForecastRun).where(ForecastRun.resource_type == resource_type, ForecastRun.status == "completed")
        if data_center_id is None:
            stmt = stmt.where(ForecastRun.data_center_id.is_(None))
            # Legacy builds persisted synthetic all-scope forecasts. Filter them
            # in Python so the All Data Centers selector only returns a forecast
            # generated from the current real-data scope.
            runs = list(db.scalars(stmt.order_by(ForecastRun.completed_at.desc()).limit(50)))
            real_ids = set(real_data_center_ids(db))
            run = next((r for r in runs if (r.metrics or {}).get("data_origin") == "real" and set((r.metrics or {}).get("data_center_ids") or []) == real_ids), None)
        else:
            stmt = stmt.where(ForecastRun.data_center_id == data_center_id)
            runs = list(db.scalars(stmt.order_by(ForecastRun.completed_at.desc()).limit(50)))
            run = next((
                r for r in runs
                if (r.metrics or {}).get("data_origin") == "real"
                and set((r.metrics or {}).get("data_center_ids") or []) == {data_center_id}
            ), None)
        if run is None:
            raise NotFoundError("No completed forecast found for the requested scope")
        return ForecastingService.response_for_run(db, run.id)
