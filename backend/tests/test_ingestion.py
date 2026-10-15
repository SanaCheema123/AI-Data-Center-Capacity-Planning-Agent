"""Tests for collector ingestion and the data-source create/sync API."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.integrations.base import MetricSource, NormalizedMetric
from app.services.ingestion import MetricIngestionService
from test_backend_foundation import TestingSessionLocal, client, login


def _auth():
    tokens = login("admin@example.com", "Admin123!")
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _viewer_auth():
    # test_backend_foundation creates the viewer lazily via register; do the same here.
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "viewer@example.com", "full_name": "Test Viewer", "password": "Viewer123!"},
    )
    assert register.status_code in (201, 409), register.text
    tokens = login("viewer@example.com", "Viewer123!")
    return {"Authorization": f"Bearer {tokens['access_token']}"}


class _StubCollector(MetricSource):
    """Deterministic collector fixture: two days of GPU + power samples.

    Timestamps are aligned to whole days (like Prometheus scrape steps) so
    repeated syncs observe identical samples.
    """

    _BASE = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def __init__(self, code: str = "STUB-DC") -> None:
        self.code = code

    def test_connection(self) -> bool:
        return True

    def collect(self) -> Iterable[NormalizedMetric]:
        base = self._BASE
        for day in range(2):
            ts = base + timedelta(days=day)
            yield NormalizedMetric(ts, self.code, "gpu_utilization", 60.0 + day, "%")
            yield NormalizedMetric(ts, self.code, "installed_gpus", 128.0, "GPUs", cluster="train-a")
            yield NormalizedMetric(ts, self.code, "power_usage_mw", 20.0 + day, "MW")
            yield NormalizedMetric(ts, self.code, "power_capacity_mw", 50.0, "MW")
            yield NormalizedMetric(ts, self.code, "storage_used_tb", 900.0 + day, "TB")
            yield NormalizedMetric(ts, self.code, "storage_capacity_tb", 2000.0, "TB")
            yield NormalizedMetric(ts, self.code, "network_throughput_gbps", 120.0 + day, "Gbps")
            yield NormalizedMetric(ts, self.code, "network_capacity_gbps", 400.0, "Gbps")
            yield NormalizedMetric(ts, self.code, "cooling_power_mw", 4.0, "MW")


def _make_source(name: str = "Stub Collector") -> int:
    response = client.post(
        "/api/v1/data-sources",
        headers=_auth(),
        json={"name": name, "source_type": "prometheus", "configuration": {"base_url": "http://stub:9090"}},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_data_source_create_requires_planner_role():
    denied = client.post(
        "/api/v1/data-sources",
        headers=_viewer_auth(),
        json={"name": "Denied Source", "source_type": "prometheus", "configuration": {}},
    )
    assert denied.status_code == 403


def test_data_source_create_rejects_duplicate_names():
    headers = _auth()
    url = "/api/v1/data-sources"
    first = client.post(url, headers=headers, json={"name": "Dup Source", "source_type": "prometheus", "configuration": {}})
    assert first.status_code == 201
    second = client.post(url, headers=headers, json={"name": "Dup Source", "source_type": "prometheus", "configuration": {}})
    assert second.status_code == 409


def test_sync_ingests_collector_data_and_registers_data_center():
    source_id = _make_source("Stub Prometheus")
    with TestingSessionLocal() as db:
        from app.models.domain import DataSource
        source = db.get(DataSource, source_id)

        class _DirectStub(_StubCollector):
            pass

        result = MetricIngestionService.ingest(db, source, _DirectStub())
        assert result.status == "success"
        assert result.metrics_inserted == 18
        assert result.data_center_registered == "STUB-DC"
        assert result.clusters_registered == 1

        # Second sync deduplicates identical samples.
        again = MetricIngestionService.ingest(db, source, _DirectStub())
        assert again.metrics_inserted == 0
        assert again.duplicates_skipped == 18
        db.refresh(source)
        assert source.status == "connected"
        assert source.last_sync_status == "success"


def test_sync_api_reports_connection_failure_honestly():
    source_id = _make_source("Unreachable Prom")
    response = client.post(f"/api/v1/data-sources/{source_id}/sync", headers=_auth())
    assert response.status_code == 502
    assert "Cannot reach" in response.json()["detail"]
    with TestingSessionLocal() as db:
        from app.models.domain import DataSource
        source = db.get(DataSource, source_id)
        assert source.status == "error"
        assert source.last_sync_status == "connection_failed"


def test_empty_collector_window_reports_no_data_without_fabricating():
    class _Empty(MetricSource):
        def test_connection(self) -> bool:
            return True

        def collect(self) -> Iterable[NormalizedMetric]:
            return []

    with TestingSessionLocal() as db:
        from app.models.domain import DataSource
        source = db.get(DataSource, _make_source("Empty Prom"))
        result = MetricIngestionService.ingest(db, source, _Empty())
        assert result.status == "no_data"
        assert result.metrics_inserted == 0
        assert result.errors, "empty sync must explain why no data was stored"
        db.refresh(source)
        assert source.last_sync_status == "no_data"


def test_authenticated_internal_api_push_ingests_real_metrics():
    response = client.post(
        "/api/v1/data-sources",
        headers=_auth(),
        json={"name": "Internal Metrics Push", "source_type": "internal_api", "configuration": {}},
    )
    assert response.status_code in (201, 409), response.text
    if response.status_code == 201:
        source_id = response.json()["id"]
    else:
        with TestingSessionLocal() as db:
            from app.models.domain import DataSource
            from sqlalchemy import select
            source_id = db.scalar(select(DataSource.id).where(DataSource.name == "Internal Metrics Push"))
    ts = "2026-03-01T00:00:00Z"
    metrics = [
        {"timestamp":ts,"data_center":"PUSH-REAL-DC","cluster":"gpu-a","metric_name":"gpu_utilization","value":60},
        {"timestamp":ts,"data_center":"PUSH-REAL-DC","cluster":"gpu-a","metric_name":"installed_gpus","value":64},
        {"timestamp":ts,"data_center":"PUSH-REAL-DC","metric_name":"power_usage_mw","value":8},
        {"timestamp":ts,"data_center":"PUSH-REAL-DC","metric_name":"power_capacity_mw","value":20},
        {"timestamp":ts,"data_center":"PUSH-REAL-DC","metric_name":"cooling_power_mw","value":2},
        {"timestamp":ts,"data_center":"PUSH-REAL-DC","metric_name":"storage_used_tb","value":300},
        {"timestamp":ts,"data_center":"PUSH-REAL-DC","metric_name":"storage_capacity_tb","value":800},
        {"timestamp":ts,"data_center":"PUSH-REAL-DC","metric_name":"network_throughput_gbps","value":80},
        {"timestamp":ts,"data_center":"PUSH-REAL-DC","metric_name":"network_capacity_gbps","value":300},
    ]
    pushed = client.post(f"/api/v1/data-sources/{source_id}/metrics", headers=_auth(), json={"metrics": metrics})
    assert pushed.status_code == 200, pushed.text
    assert pushed.json()["metrics_inserted"] == 9
    assert pushed.json()["data_center_registered"] == "PUSH-REAL-DC"
