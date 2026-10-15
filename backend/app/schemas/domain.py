from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DataCenterCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=64)
    region: str
    country: str
    timezone: str = "UTC"


class DataCenterRead(ORMBase):
    id: int
    name: str
    code: str
    region: str
    country: str
    timezone: str
    status: str
    meta: dict[str, Any]
    created_at: datetime


class DataSourceRead(ORMBase):
    id: int
    name: str
    source_type: str
    status: str
    last_sync_at: datetime | None
    last_sync_status: str | None
    metric_count: int = 0
    data_center_names: list[str] = []


class ForecastRunRead(ORMBase):
    id: int
    resource_type: str
    data_center_id: int | None
    status: str
    horizon_months: int
    frequency: str
    confidence_interval: float
    created_at: datetime


class ScenarioRead(ORMBase):
    id: int
    name: str
    description: str | None
    scenario_type: str
    planning_horizon_months: int
    assumptions: dict[str, Any]
    created_at: datetime


class ProcurementRead(ORMBase):
    id: int
    data_center_id: int | None
    resource_type: str
    current_capacity: float | None
    required_capacity: float | None
    quantity: float | None
    required_by: datetime | None
    priority: str
    status: str
    estimated_cost: float | None
    reason: str | None


class AlertRead(ORMBase):
    id: int
    data_center_id: int
    resource_type: str
    severity: str
    title: str
    description: str
    current_value: float | None
    threshold_value: float | None
    forecast_value: float | None
    predicted_shortage_at: datetime | None
    status: str
    triggered_at: datetime


class AlertUpdate(BaseModel):
    status: str = Field(pattern="^(open|acknowledged|investigating|monitoring|resolved)$")


class ReportRead(ORMBase):
    id: int
    data_center_id: int | None
    report_type: str
    title: str
    status: str
    generated_at: datetime | None
    created_at: datetime


class SettingRead(ORMBase):
    id: int
    key: str
    value: dict[str, Any]


class SettingUpdate(BaseModel):
    value: dict[str, Any]


class DashboardSummary(BaseModel):
    data_centers: int
    clusters: int
    active_alerts: int
    completed_forecasts: int
    pending_procurement: int
    latest_metric_at: datetime | None
