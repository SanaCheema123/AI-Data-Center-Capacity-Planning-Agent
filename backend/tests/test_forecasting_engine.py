from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.forecasting import ForecastRequest, TimePoint
from app.forecasting.models import ProphetForecastModel, XGBoostForecastModel
from app.forecasting.utils import (
    accuracy_metrics,
    capacity_headroom,
    peak_demand,
    required_expansion,
    shortage_date,
    utilization_percent,
)
from app.models.domain import DataCenter, ForecastModel, InfrastructureMetric
from app.schemas.forecasting import ForecastRunRequest
from app.services.forecasting import ForecastingService


def monthly_history(n: int = 30) -> list[TimePoint]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [TimePoint(start + timedelta(days=30 * i), 100.0 + i * 8.0 + (i % 3) * 2.0) for i in range(n)]


def test_capacity_calculations() -> None:
    assert capacity_headroom(1000, 720) == 280
    assert utilization_percent(720, 1000) == pytest.approx(72.0)
    assert required_expansion(1200, 1000) == pytest.approx(200.0)
    assert required_expansion(800, 1000) == 0
    assert required_expansion(850, 1000, target_utilization=0.8) == pytest.approx(62.5)


def test_peak_and_shortage_detection() -> None:
    model = ProphetForecastModel()
    result = model.fit_predict(ForecastRequest(monthly_history(), 6, "monthly", 0.9))
    peak = peak_demand(result.points)
    assert peak is not None
    assert peak.predicted == max(p.predicted for p in result.points)
    first = shortage_date(result.points, min(p.predicted for p in result.points))
    assert first == result.points[0].timestamp
    assert shortage_date(result.points, 10_000_000) is None


def test_accuracy_metrics_are_exact_for_perfect_prediction() -> None:
    metrics = accuracy_metrics([1, 2, 3, 4], [1, 2, 3, 4])
    assert metrics["mae"] == 0
    assert metrics["rmse"] == 0
    assert metrics["mape"] == 0
    assert metrics["r2"] == 1


def test_prophet_model_produces_data_driven_forecast_and_intervals() -> None:
    result = ProphetForecastModel().fit_predict(ForecastRequest(monthly_history(), 8, "monthly", 0.9))
    assert len(result.points) == 8
    assert result.metrics["mae"] >= 0
    assert result.metrics["rmse"] >= 0
    assert all(p.lower is not None and p.upper is not None for p in result.points)
    assert all(p.lower <= p.predicted <= p.upper for p in result.points)
    assert result.points[-1].predicted != result.points[0].predicted


def test_xgboost_model_produces_data_driven_forecast_and_intervals() -> None:
    result = XGBoostForecastModel().fit_predict(ForecastRequest(monthly_history(), 6, "monthly", 0.9))
    assert len(result.points) == 6
    assert result.metadata["engine"] == "xgboost"
    assert result.metrics["mape"] >= 0
    assert all(p.predicted >= 0 for p in result.points)
    assert all(p.lower <= p.predicted <= p.upper for p in result.points)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as db:
        dc = DataCenter(name="Forecast Test", code="FC-1", region="test", country="PK", timezone="UTC", meta={"dataset": "synthetic-test"})
        db.add(dc)
        db.flush()
        db.add_all([
            ForecastModel(name="Prophet", model_type="prophet", version="1.1", config={}, is_enabled=True),
            ForecastModel(name="XGBoost", model_type="xgboost", version="3", config={}, is_enabled=True),
        ])
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        for i in range(30):
            ts = start + timedelta(days=30 * i)
            utilization = 42.0 + i * 1.35 + (i % 4) * 0.5
            metrics = [
                ("gpu", "gpu_utilization", utilization, "%"),
                ("gpu", "installed_gpus", 256.0, "gpus"),
                ("power", "power_usage_mw", 18.0 + i * 0.9, "MW"),
                ("power", "power_capacity_mw", 50.0, "MW"),
                ("storage", "storage_used_tb", 2200.0 + i * 175.0, "TB"),
                ("storage", "storage_capacity_tb", 7000.0, "TB"),
                ("network", "network_throughput_gbps", 110.0 + i * 15.0, "Gbps"),
                ("network", "network_capacity_gbps", 600.0, "Gbps"),
            ]
            for metric_type, name, value, unit in metrics:
                db.add(InfrastructureMetric(data_center_id=dc.id, cluster_id=None, source_id=None, timestamp=ts, metric_type=metric_type, metric_name=name, value=value, unit=unit, tags={"dataset": "synthetic-test"}))
        db.commit()
        yield db, dc.id


@pytest.mark.parametrize(
    "resource,unit",
    [("gpu", "GPUs"), ("power", "MW"), ("storage", "TB"), ("network", "Gbps")],
)
def test_resource_forecasts_use_database_data(db_session, resource: str, unit: str) -> None:
    db, dc_id = db_session
    result = ForecastingService.run(
        db,
        ForecastRunRequest(resource_type=resource, model="prophet", data_center_id=dc_id, horizon=6, frequency="monthly", confidence=0.9),
    )
    assert result.resource_type == resource
    assert result.unit == unit
    assert len(result.points) == 6
    assert result.capacity.current_usage > 0
    assert result.capacity.current_capacity > 0
    assert result.capacity.headroom == pytest.approx(result.capacity.current_capacity - result.capacity.current_usage)
    assert result.capacity.peak_demand == pytest.approx(max(point.predicted for point in result.points))
    assert result.accuracy.mae >= 0
    assert result.accuracy.rmse >= 0


def test_xgboost_service_persists_results(db_session) -> None:
    db, dc_id = db_session
    result = ForecastingService.run(
        db,
        ForecastRunRequest(resource_type="gpu", model="xgboost", data_center_id=dc_id, horizon=4, frequency="monthly", confidence=0.8),
    )
    loaded = ForecastingService.response_for_run(db, result.run_id)
    assert loaded.run_id == result.run_id
    assert loaded.model == "xgboost"
    assert loaded.model_engine == "xgboost"
    assert len(loaded.points) == 4


def test_insufficient_history_is_rejected() -> None:
    history = monthly_history(5)
    with pytest.raises(ValueError, match="Insufficient data"):
        ProphetForecastModel().fit_predict(ForecastRequest(history, 3, "monthly", 0.9))
