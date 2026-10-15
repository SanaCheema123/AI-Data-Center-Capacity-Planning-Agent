"""Ingestion service for MetricSource collectors (Prometheus today, more later).

Normalizes collector output against the canonical metric registry, validates
values, resolves/creates the scoped data center and clusters, and writes
InfrastructureMetric rows with duplicate suppression per (data center, cluster,
timestamp, metric).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.base import NormalizedMetric, MetricSource
from app.integrations.metrics import CANONICAL_METRICS
from app.models.domain import Cluster, DataCenter, DataSource, InfrastructureMetric
from app.schemas.planning import CSVImportError, DataSourceSyncResult


class IngestionError(Exception):
    pass


class MetricIngestionService:
    @staticmethod
    def _resolve_data_center(db: Session, code: str) -> DataCenter:
        dc = db.scalar(select(DataCenter).where((DataCenter.code == code) | (DataCenter.name == code)))
        if dc is None:
            # First sync from an external system auto-registers the data center it reports.
            dc = DataCenter(name=code, code=code, region="unspecified", country="unspecified", timezone="UTC", meta={"registered_by": "ingestion", "data_origin": "real"})
            db.add(dc)
            db.flush()
        return dc

    @staticmethod
    def _resolve_cluster(db: Session, dc_id: int, cluster_name: str) -> Cluster:
        cluster = db.scalar(select(Cluster).where(Cluster.data_center_id == dc_id, Cluster.name == cluster_name))
        if cluster is None:
            cluster = Cluster(data_center_id=dc_id, name=cluster_name, cluster_type="gpu", status="active")
            db.add(cluster)
            db.flush()
        return cluster

    @staticmethod
    def ingest(
        db: Session,
        source: DataSource,
        collector: MetricSource,
        *,
        dedupe: bool = True,
    ) -> DataSourceSyncResult:
        started = datetime.now(timezone.utc)
        batch: list[NormalizedMetric] = []
        for item in collector.collect():
            if item.metric_name not in CANONICAL_METRICS:
                raise IngestionError(f"Collector produced unknown metric '{item.metric_name}'")
            batch.append(item)
        if not batch:
            source.status = "connected"
            source.last_sync_at = datetime.now(timezone.utc)
            source.last_sync_status = "no_data"
            db.commit()
            return DataSourceSyncResult(
                source_id=source.id, status="no_data", metrics_received=0, metrics_inserted=0,
                duplicates_skipped=0, clusters_registered=0, data_center_registered=None,
                started_at=started, finished_at=datetime.now(timezone.utc),
                errors=[CSVImportError(row=0, message="The connector returned no metric samples for the configured window")],
            )

        # A real source must provide every metric required by downstream capacity
        # planning. Never fill missing capacity series with synthetic defaults.
        required = {name for name, definition in CANONICAL_METRICS.items() if definition.required}
        names_by_dc: dict[str, set[str]] = {}
        for item in batch:
            names_by_dc.setdefault(item.data_center, set()).add(item.metric_name)
        missing_by_dc = {dc: sorted(required - names) for dc, names in names_by_dc.items() if required - names}
        if missing_by_dc:
            details = "; ".join(f"{dc}: {', '.join(names)}" for dc, names in missing_by_dc.items())
            raise IngestionError(f"Connector data is incomplete; missing required metrics -> {details}")

        dc_cache: dict[str, DataCenter] = {}
        for code in sorted(names_by_dc):
            dc_cache[code] = MetricIngestionService._resolve_data_center(db, code)

        existing_cluster_keys = {(c.data_center_id, c.name.lower()) for c in db.scalars(select(Cluster))}
        cluster_cache: dict[tuple[int, str], Cluster] = {}
        clusters_registered = 0
        for item in batch:
            if item.cluster:
                dc = dc_cache[item.data_center]
                key = (dc.id, item.cluster.lower())
                if key not in cluster_cache:
                    cluster_cache[key] = MetricIngestionService._resolve_cluster(db, dc.id, item.cluster)
                    if key not in existing_cluster_keys:
                        existing_cluster_keys.add(key)
                        clusters_registered += 1
        db.flush()

        existing_keys: set[tuple[int, int | None, datetime, str]] = set()
        if dedupe:
            def norm(ts: datetime) -> datetime:
                return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
            stamps = [norm(item.timestamp) for item in batch]
            def stored_form(ts: datetime) -> datetime:
                return ts.replace(tzinfo=None) if db.bind.dialect.name == "sqlite" else ts
            window_low = stored_form(min(stamps))
            window_high = stored_form(max(stamps))
            dc_ids = [dc.id for dc in dc_cache.values()]
            rows = db.scalars(select(InfrastructureMetric).where(
                InfrastructureMetric.data_center_id.in_(dc_ids),
                InfrastructureMetric.timestamp >= window_low,
                InfrastructureMetric.timestamp <= window_high,
                InfrastructureMetric.metric_name.in_(list(CANONICAL_METRICS)),
            )).all()
            existing_keys = {(m.data_center_id, m.cluster_id, norm(m.timestamp), m.metric_name) for m in rows}
        else:
            def norm(ts: datetime) -> datetime:
                return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)

        inserted = 0
        duplicates = 0
        for item in batch:
            definition = CANONICAL_METRICS[item.metric_name]
            if item.value < definition.minimum:
                raise IngestionError(f"Metric {item.metric_name} below physical minimum: {item.value}")
            if definition.maximum is not None and item.value > definition.maximum:
                raise IngestionError(f"Metric {item.metric_name} above physical maximum: {item.value}")
            dc = dc_cache[item.data_center]
            cluster = cluster_cache.get((dc.id, item.cluster.lower())) if item.cluster else None
            cluster_id = cluster.id if cluster is not None and definition.metric_type == "gpu" else None
            stamp = norm(item.timestamp)
            key = (dc.id, cluster_id, stamp, item.metric_name)
            if dedupe and key in existing_keys:
                duplicates += 1
                continue
            db.add(InfrastructureMetric(
                data_center_id=dc.id, cluster_id=cluster_id, source_id=source.id,
                timestamp=stamp, metric_type=definition.metric_type, metric_name=item.metric_name,
                value=float(item.value), unit=definition.unit,
                tags={"source": "collector", "data_origin": "real", "collector": source.source_type, **(item.attributes or {})},
            ))
            existing_keys.add(key)
            inserted += 1
        db.commit()

        source.status = "connected"
        source.last_sync_at = datetime.now(timezone.utc)
        source.last_sync_status = "success"
        db.commit()
        return DataSourceSyncResult(
            source_id=source.id, status="success", metrics_received=len(batch), metrics_inserted=inserted,
            duplicates_skipped=duplicates, clusters_registered=clusters_registered,
            data_center_registered=", ".join(sorted(dc.code for dc in dc_cache.values())),
            started_at=started, finished_at=datetime.now(timezone.utc), errors=[],
        )

    @staticmethod
    def sync_data_source(db: Session, source: DataSource) -> DataSourceSyncResult:
        """Build the right collector from the stored configuration and sync it."""
        config = source.configuration or {}
        if source.source_type == "prometheus":
            from app.integrations.prometheus.collector import PrometheusCollector
            base_url = str(config.get("base_url") or "").strip()
            if not base_url:
                raise IngestionError("Prometheus data source requires configuration.base_url")
            collector = PrometheusCollector(
                base_url=base_url,
                data_center_code=str(config.get("data_center_code") or "").strip() or "PROM-DC",
                expressions=config.get("expressions") or None,
                lookback_days=int(config.get("lookback_days") or 90),
                verify_tls=bool(config.get("verify_tls", True)),
            )
        else:
            raise IngestionError(f"Sync is not implemented for source type '{source.source_type}'")
        if not collector.test_connection():
            source.status = "error"
            source.last_sync_at = datetime.now(timezone.utc)
            source.last_sync_status = "connection_failed"
            db.commit()
            raise IngestionError(f"Cannot reach {source.source_type} at the configured URL")
        return MetricIngestionService.ingest(db, source, collector)
