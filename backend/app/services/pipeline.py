"""Real-data processing pipeline.

This service mirrors the project workflow after ingestion:
validation/normalization -> persisted metrics -> feature aggregation -> forecasts ->
scenario simulation -> shortage alerts -> procurement recommendations.

It never creates synthetic telemetry. If a scope does not have enough real
history, that step is skipped with an explicit warning.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import User
from app.models.system_setting import SystemSetting
from app.schemas.forecasting import ForecastRunRequest
from app.schemas.planning import PipelineStatus
from app.services.data_scope import real_data_center_ids
from app.services.forecasting import ForecastingService
from app.services.planning import AlertService, ProcurementService, ScenarioService


class RealDataPipelineService:
    RESOURCES = ("gpu", "power", "storage", "network")

    @staticmethod
    def _forecast_defaults(db: Session) -> tuple[str, int, float]:
        setting = db.scalar(select(SystemSetting).where(SystemSetting.key == "forecast"))
        value = (setting.value if setting else {}) or {}
        model = str(value.get("default_model") or "prophet").lower()
        if model not in {"prophet", "xgboost"}:
            model = "prophet"
        horizon = int(value.get("horizon_months") or 12)
        horizon = min(60, max(1, horizon))
        confidence = float(value.get("confidence_interval") or 0.90)
        confidence = min(0.99, max(0.50, confidence))
        return model, horizon, confidence

    @staticmethod
    def refresh_scope(db: Session, data_center_id: int | None, user: User | None = None) -> PipelineStatus:
        scope = "all-real-data-centers" if data_center_id is None else f"data-center:{data_center_id}"
        status = PipelineStatus(scope=scope)
        model, horizon, confidence = RealDataPipelineService._forecast_defaults(db)

        for resource in RealDataPipelineService.RESOURCES:
            try:
                ForecastingService.run(
                    db,
                    ForecastRunRequest(
                        resource_type=resource,
                        model=model,
                        data_center_id=data_center_id,
                        horizon=horizon,
                        frequency="monthly",
                        confidence=confidence,
                    ),
                    user,
                )
                status.forecasts_completed.append(resource)
            except Exception as exc:
                status.warnings.append(f"{resource} forecast: {exc}")

        # Downstream services are refreshed only from persisted real forecasts.
        try:
            ScenarioService.compare(db, data_center_id, persist=True)
            status.scenarios_refreshed = True
        except Exception as exc:
            status.warnings.append(f"scenario analysis: {exc}")

        try:
            ProcurementService.generate(db, data_center_id)
            status.procurement_refreshed = True
        except Exception as exc:
            status.warnings.append(f"procurement: {exc}")

        # Alerts are data-center records. All-scope evaluation delegates to each
        # current real center; individual scope evaluates only that center.
        try:
            AlertService.evaluate(db, data_center_id)
            status.alerts_refreshed = True
        except Exception as exc:
            status.warnings.append(f"alerts: {exc}")

        return status

    @staticmethod
    def refresh_after_ingestion(db: Session, imported_data_center_ids: list[int], user: User | None = None) -> list[PipelineStatus]:
        current_real = set(real_data_center_ids(db))
        scopes = [dc_id for dc_id in sorted(set(imported_data_center_ids)) if dc_id in current_real]
        statuses = [RealDataPipelineService.refresh_scope(db, dc_id, user) for dc_id in scopes]
        if current_real:
            statuses.append(RealDataPipelineService.refresh_scope(db, None, user))
        return statuses
