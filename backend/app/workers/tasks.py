from __future__ import annotations

import logging

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.domain import DataSource, InfrastructureMetric
from app.services.ingestion import IngestionError, MetricIngestionService
from app.services.pipeline import RealDataPipelineService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="system.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="data_sources.sync_all")
def sync_all_data_sources() -> dict[str, object]:
    """Synchronize configured pull-based real data sources and refresh planning.

    CSV and authenticated push sources are event-driven and are not polled.
    No synthetic fallback is created when a connector is unavailable.
    """
    db = SessionLocal()
    result: dict[str, object] = {"synced": [], "failed": []}
    try:
        sources = list(db.scalars(select(DataSource).where(DataSource.source_type == "prometheus")))
        for source in sources:
            try:
                sync = MetricIngestionService.sync_data_source(db, source)
                dc_ids = list(db.scalars(
                    select(InfrastructureMetric.data_center_id)
                    .where(InfrastructureMetric.source_id == source.id)
                    .distinct()
                ))
                pipeline = RealDataPipelineService.refresh_after_ingestion(db, dc_ids) if sync.metrics_inserted > 0 else []
                result["synced"].append({
                    "source_id": source.id,
                    "metrics_inserted": sync.metrics_inserted,
                    "pipeline_scopes": [p.scope for p in pipeline],
                })
            except Exception as exc:
                logger.warning("scheduled_source_sync_failed source_id=%s", source.id, exc_info=True)
                result["failed"].append({"source_id": source.id, "error": str(exc)})
        return result
    finally:
        db.close()
