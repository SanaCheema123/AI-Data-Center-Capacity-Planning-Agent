from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.grounding import narrative_is_grounded
from app.ai.providers.base import AIProvider
from app.db.base import Base
from app.models.domain import DataCenter, ForecastModel, InfrastructureMetric, ProcurementItem, Scenario
from app.schemas.forecasting import ForecastRunRequest
from app.services.ai_planning import AIPlanningService
from app.services.forecasting import ForecastingService


def make_ai_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()
    dc = DataCenter(name="AI Test", code="AI-1", region="test", country="PK", timezone="UTC", meta={})
    db.add(dc)
    db.flush()
    db.add(ForecastModel(name="Prophet", model_type="prophet", version="1.1", config={}, is_enabled=True))
    for name, kind, multiplier in [
        ("Conservative", "conservative", 0.9),
        ("Base Case", "base", 1.0),
        ("Aggressive", "aggressive", 1.2),
    ]:
        db.add(Scenario(name=name, description=name, scenario_type=kind, planning_horizon_months=36, assumptions={"growth_multiplier": multiplier}))
    for category, capacity, cost in [("gpu", 8, 1000), ("power", 1, 2000), ("storage", 100, 3000), ("network", 100, 4000)]:
        db.add(ProcurementItem(name=category, category=category, unit_capacity=capacity, unit=category, unit_cost=cost, lead_time_days=30))
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for i in range(30):
        ts = start + timedelta(days=30 * i)
        rows = [
            ("gpu", "gpu_utilization", 55 + i * 1.0, "%"),
            ("gpu", "installed_gpus", 256, "gpus"),
            ("power", "power_usage_mw", 20 + i * 0.8, "MW"),
            ("power", "power_capacity_mw", 50, "MW"),
            ("storage", "storage_used_tb", 3000 + i * 150, "TB"),
            ("storage", "storage_capacity_tb", 7000, "TB"),
            ("network", "network_throughput_gbps", 200 + i * 15, "Gbps"),
            ("network", "network_capacity_gbps", 600, "Gbps"),
        ]
        for metric_type, metric_name, value, unit in rows:
            db.add(InfrastructureMetric(data_center_id=dc.id, timestamp=ts, metric_type=metric_type, metric_name=metric_name, value=value, unit=unit, tags={"dataset": "ai-test"}))
    db.commit()
    for resource in ("gpu", "power", "storage", "network"):
        ForecastingService.run(db, ForecastRunRequest(resource_type=resource, model="prophet", data_center_id=dc.id, horizon=6, frequency="monthly", confidence=0.9))
    return db, dc.id


def test_langgraph_workflow_is_grounded_in_database_and_forecast_results():
    db, dc_id = make_ai_db()
    try:
        state = AIPlanningService.run(db, SimpleNamespace(id=1), dc_id)
        assert state["analysis"]["metric_row_count"] > 0
        assert set(state["forecast_analysis"]) == {"gpu", "power", "storage", "network"}
        assert len(state["scenario_analysis"]["scenarios"]) == 3
        assert len(state["recommendations"]) == 4
        assert len(state["evidence"]) >= 10
        for rec in state["recommendations"]:
            assert rec["supporting_metrics"]["forecast_run_id"] is not None
            assert "forecast_peak" in rec["supporting_metrics"]
        assert state["provider"] == "local"
    finally:
        db.close()


def test_grounding_validator_rejects_unsupported_numeric_claims():
    evidence = [{"facts": {"capacity": 100.0, "forecast": 120.0}}]
    assert narrative_is_grounded("Capacity is 100 and forecast is 120.", evidence)
    assert not narrative_is_grounded("Capacity will be 999999.", evidence)


def test_missing_provider_key_falls_back_to_local(monkeypatch):
    from app.ai.providers.factory import get_ai_provider
    provider = get_ai_provider("gemini")
    assert provider.name == "local"
