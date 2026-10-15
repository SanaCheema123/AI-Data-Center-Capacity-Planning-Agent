from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.domain import Cluster, DataCenter, ForecastModel, InfrastructureMetric, Scenario
from app.models.system_setting import SystemSetting
from app.services.forecasting import ForecastingService
from test_backend_foundation import TestingSessionLocal, client, login


def _metric(db, dc_id, name, value, metric_type, unit, ts, cluster_id=None):
    db.add(InfrastructureMetric(
        data_center_id=dc_id,
        cluster_id=cluster_id,
        timestamp=ts,
        metric_type=metric_type,
        metric_name=name,
        value=value,
        unit=unit,
        tags={"data_origin": "real", "source": "test"},
    ))


def test_capacity_aggregation_preserves_physical_units_and_gpu_clusters():
    with TestingSessionLocal() as db:
        dc = DataCenter(name="Aggregation Real DC", code="AGG-REAL-DC", region="test", country="PK", timezone="UTC", meta={"data_origin": "real"})
        db.add(dc); db.flush()
        a = Cluster(data_center_id=dc.id, name="a", cluster_type="gpu", installed_gpu_count=100)
        b = Cluster(data_center_id=dc.id, name="b", cluster_type="gpu", installed_gpu_count=200)
        db.add_all([a, b]); db.flush()
        t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 20, tzinfo=timezone.utc)
        _metric(db, dc.id, "gpu_utilization", 50, "gpu", "%", t1, a.id)
        _metric(db, dc.id, "installed_gpus", 100, "gpu", "GPUs", t1, a.id)
        _metric(db, dc.id, "gpu_utilization", 25, "gpu", "%", t1, b.id)
        _metric(db, dc.id, "installed_gpus", 200, "gpu", "GPUs", t1, b.id)
        for ts, power, storage, network in [(t1, 10, 100, 70), (t2, 12, 110, 80)]:
            _metric(db, dc.id, "power_usage_mw", power, "power", "MW", ts)
            _metric(db, dc.id, "power_capacity_mw", 20, "power", "MW", ts)
            _metric(db, dc.id, "storage_used_tb", storage, "storage", "TB", ts)
            _metric(db, dc.id, "storage_capacity_tb", 200, "storage", "TB", ts)
            _metric(db, dc.id, "network_throughput_gbps", network, "network", "Gbps", ts)
            _metric(db, dc.id, "network_capacity_gbps", 100, "network", "Gbps", ts)
        db.commit()

        gpu, gpu_cap, _ = ForecastingService.history_and_capacity(db, "gpu", dc.id, "monthly")
        power, power_cap, _ = ForecastingService.history_and_capacity(db, "power", dc.id, "monthly")
        storage, storage_cap, _ = ForecastingService.history_and_capacity(db, "storage", dc.id, "monthly")
        network, network_cap, _ = ForecastingService.history_and_capacity(db, "network", dc.id, "monthly")
        assert gpu[0].value == 100.0  # 50%*100 + 25%*200
        assert gpu_cap == 300.0
        assert power[0].value == 12.0 and power_cap == 20.0
        assert storage[0].value == 110.0 and storage_cap == 200.0
        assert network[0].value == 80.0 and network_cap == 100.0


def test_csv_import_runs_real_workflow_pipeline_without_demo_fallback():
    with TestingSessionLocal() as db:
        if db.scalar(select(ForecastModel).where(ForecastModel.model_type == "xgboost")) is None:
            db.add(ForecastModel(name="XGBoost workflow test", model_type="xgboost", version="test", config={}, is_enabled=True))
        forecast = db.scalar(select(SystemSetting).where(SystemSetting.key == "forecast"))
        if forecast is None:
            db.add(SystemSetting(key="forecast", value={"default_model": "xgboost", "horizon_months": 6, "confidence_interval": 0.9}))
        else:
            forecast.value = {"default_model": "xgboost", "horizon_months": 6, "confidence_interval": 0.9}
        thresholds = db.scalar(select(SystemSetting).where(SystemSetting.key == "capacity_thresholds"))
        if thresholds is None:
            db.add(SystemSetting(key="capacity_thresholds", value={"gpu":80,"power":85,"storage":80,"network":75}))
        if db.scalar(select(Scenario).where(Scenario.name == "Workflow Base", Scenario.data_center_id.is_(None))) is None:
            db.add(Scenario(name="Workflow Base", scenario_type="base", planning_horizon_months=24, assumptions={"growth_multiplier":1.0,"source":"system_config"}))
        db.commit()

    token = login("admin@example.com", "Admin123!")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    rows = ["timestamp,data_center,cluster,gpu_utilization,installed_gpus,power_usage_mw,power_capacity_mw,storage_used_tb,storage_capacity_tb,network_throughput_gbps,cooling_power_mw,network_capacity_gbps"]
    for month in range(1, 13):
        rows.append(
            f"2025-{month:02d}-01T00:00:00Z,PIPELINE-REAL-DC,gpu-a,{45+month},128,{8+month*0.25:.2f},20,{300+month*20},800,{80+month*5},2.5,300"
        )
    response = client.post(
        "/api/v1/data-sources/csv/import",
        headers=headers,
        files={"file": ("pipeline-real.csv", "\n".join(rows), "text/csv")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["metrics_inserted"] == 12 * 9
    assert body["data_center_names"] == ["PIPELINE-REAL-DC"]
    assert len(body["pipeline"]) == 2  # specific center + all-real scope
    assert all(set(p["forecasts_completed"]) == {"gpu","power","storage","network"} for p in body["pipeline"])

    centers = client.get("/api/v1/data-centers", headers=headers).json()
    dc_id = next(x["id"] for x in centers if x["name"] == "PIPELINE-REAL-DC")
    for resource in ("gpu", "power", "storage", "network"):
        forecast = client.get(f"/api/v1/{resource}/forecast", headers=headers, params={"data_center_id": dc_id})
        assert forecast.status_code == 200, forecast.text
        assert forecast.json()["points"]

    sources = client.get("/api/v1/data-sources", headers=headers).json()
    source = next(x for x in sources if x["name"].startswith("CSV · pipeline-real.csv"))
    assert source["data_center_names"] == ["PIPELINE-REAL-DC"]
