from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.domain import Alert, Cluster, DataCenter, ForecastRun, InfrastructureMetric, ProcurementRecommendation
from app.schemas.domain import DashboardSummary, DataCenterCreate
from app.services.data_scope import real_data_center_ids, real_data_centers


class DataCenterService:
    @staticmethod
    def list(db: Session) -> list[DataCenter]:
        # Only expose data centers backed by real telemetry. This keeps legacy
        # synthetic/demo centers out of selectors and the All Data Centers scope.
        return real_data_centers(db)

    @staticmethod
    def create(db: Session, data: DataCenterCreate) -> DataCenter:
        exists = db.scalar(select(DataCenter).where((DataCenter.code == data.code) | (DataCenter.name == data.name)))
        if exists:
            raise ConflictError("A data center with this name or code already exists")
        obj = DataCenter(**data.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj


class DashboardService:
    @staticmethod
    def summary(db: Session, data_center_id: int | None = None) -> DashboardSummary:
        real_ids = real_data_center_ids(db)
        if data_center_id is not None and data_center_id not in real_ids:
            raise NotFoundError("Data center not found or has no real telemetry")

        metric_stmt = select(func.max(InfrastructureMetric.timestamp))
        cluster_stmt = select(func.count()).select_from(Cluster)
        alert_stmt = select(func.count()).select_from(Alert).where(Alert.status != "resolved")

        if data_center_id is not None:
            metric_stmt = metric_stmt.where(InfrastructureMetric.data_center_id == data_center_id)
            cluster_stmt = cluster_stmt.where(Cluster.data_center_id == data_center_id)
            alert_stmt = alert_stmt.where(Alert.data_center_id == data_center_id)
            expected_ids = {data_center_id}
        else:
            expected_ids = set(real_ids)
            if real_ids:
                metric_stmt = metric_stmt.where(InfrastructureMetric.data_center_id.in_(real_ids))
                cluster_stmt = cluster_stmt.where(Cluster.data_center_id.in_(real_ids))
                alert_stmt = alert_stmt.where(Alert.data_center_id.in_(real_ids))
            else:
                metric_stmt = metric_stmt.where(InfrastructureMetric.id == -1)
                cluster_stmt = cluster_stmt.where(Cluster.id == -1)
                alert_stmt = alert_stmt.where(Alert.id == -1)

        forecast_stmt = select(ForecastRun).where(ForecastRun.status == "completed")
        if data_center_id is None:
            forecast_stmt = forecast_stmt.where(ForecastRun.data_center_id.is_(None))
        else:
            forecast_stmt = forecast_stmt.where(ForecastRun.data_center_id == data_center_id)
        forecast_rows = list(db.scalars(forecast_stmt))
        real_forecast_ids = {
            row.id for row in forecast_rows
            if (row.metrics or {}).get("data_origin") == "real"
            and set((row.metrics or {}).get("data_center_ids") or []) == expected_ids
        }

        procurement_stmt = select(ProcurementRecommendation).where(
            ProcurementRecommendation.status.notin_(["completed", "cancelled"])
        )
        if data_center_id is None:
            procurement_stmt = procurement_stmt.where(ProcurementRecommendation.data_center_id.is_(None))
        else:
            procurement_stmt = procurement_stmt.where(ProcurementRecommendation.data_center_id == data_center_id)
        procurement_rows = list(db.scalars(procurement_stmt))
        pending_procurement = sum(1 for row in procurement_rows if row.forecast_run_id in real_forecast_ids)

        return DashboardSummary(
            data_centers=1 if data_center_id is not None else len(real_ids),
            clusters=db.scalar(cluster_stmt) or 0,
            active_alerts=db.scalar(alert_stmt) or 0,
            completed_forecasts=len(real_forecast_ids),
            pending_procurement=pending_procurement,
            latest_metric_at=db.scalar(metric_stmt),
        )

