from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ScenarioComparison(BaseModel):
    id: int
    name: str
    scenario_type: str
    description: str | None
    planning_horizon_months: int
    risk_level: str
    risk_score: float
    gpu_demand: float
    power_demand_mw: float
    storage_demand_tb: float
    network_demand_gbps: float
    estimated_capex: float | None
    assumptions: dict[str, Any]


class RecommendationRead(BaseModel):
    resource_type: str
    recommendation: str
    reason: str
    supporting_metrics: dict[str, Any]
    expected_impact: str
    risk: str
    dependencies: list[str]
    time_horizon: str
    confidence: float
    assumptions: list[str]


class ReportCatalogItem(BaseModel):
    report_type: str
    title: str
    description: str
    supports_pdf: bool = True
    supports_csv: bool = True


class ReportGenerateRequest(BaseModel):
    report_type: str
    data_center_id: int | None = None


class NotificationSettingsRead(BaseModel):
    email_alerts: bool
    webhook_alerts: bool
    capacity_alerts: bool
    forecast_completion: bool
    weekly_summary: bool
    webhook_url: str | None = None


class NotificationSettingsUpdate(BaseModel):
    email_alerts: bool | None = None
    webhook_alerts: bool | None = None
    capacity_alerts: bool | None = None
    forecast_completion: bool | None = None
    weekly_summary: bool | None = None
    webhook_url: str | None = None


class ProcurementGenerateRequest(BaseModel):
    data_center_id: int | None = None


class AlertEvaluateRequest(BaseModel):
    data_center_id: int | None = None




class MetricPushItem(BaseModel):
    timestamp: datetime
    data_center: str = Field(min_length=1, max_length=120)
    metric_name: str = Field(min_length=1, max_length=100)
    value: float
    cluster: str | None = Field(default=None, max_length=120)
    attributes: dict[str, Any] = Field(default_factory=dict)


class MetricPushRequest(BaseModel):
    metrics: list[MetricPushItem] = Field(min_length=1, max_length=10000)

class CSVImportError(BaseModel):
    row: int
    field: str | None = None
    message: str


class DataSourceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    source_type: str
    configuration: dict[str, Any] | None = None


class PipelineStatus(BaseModel):
    scope: str
    forecasts_completed: list[str] = Field(default_factory=list)
    scenarios_refreshed: bool = False
    procurement_refreshed: bool = False
    alerts_refreshed: bool = False
    warnings: list[str] = Field(default_factory=list)


class DataSourceSyncResult(BaseModel):
    source_id: int
    status: str
    metrics_received: int
    metrics_inserted: int
    duplicates_skipped: int
    clusters_registered: int
    data_center_registered: str | None = None
    started_at: datetime
    finished_at: datetime
    pipeline: list[PipelineStatus] = Field(default_factory=list)
    errors: list[CSVImportError] = Field(default_factory=list)




class CSVImportResult(BaseModel):
    filename: str
    rows_received: int
    rows_imported: int
    metrics_inserted: int
    duplicates_skipped: int
    source_id: int | None = None
    data_center_ids: list[int] = Field(default_factory=list)
    data_center_names: list[str] = Field(default_factory=list)
    pipeline: list[PipelineStatus] = Field(default_factory=list)
    errors: list[CSVImportError] = Field(default_factory=list)

class AppearanceSettingsRead(BaseModel):
    theme: str
    accent: str
    compact_mode: bool


class AppearanceSettingsUpdate(BaseModel):
    theme: str | None = None
    accent: str | None = None
    compact_mode: bool | None = None

class ScenarioCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    planning_horizon_months: int = Field(default=36, ge=1, le=120)
    data_center_id: int | None = None
    gpu_multiplier: float = Field(default=1.0, gt=0, le=5)
    power_multiplier: float = Field(default=1.0, gt=0, le=5)
    storage_multiplier: float = Field(default=1.0, gt=0, le=5)
    network_multiplier: float = Field(default=1.0, gt=0, le=5)
    budget_limit: float | None = Field(default=None, ge=0)


class ScenarioUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    planning_horizon_months: int | None = Field(default=None, ge=1, le=120)
    gpu_multiplier: float | None = Field(default=None, gt=0, le=5)
    power_multiplier: float | None = Field(default=None, gt=0, le=5)
    storage_multiplier: float | None = Field(default=None, gt=0, le=5)
    network_multiplier: float | None = Field(default=None, gt=0, le=5)
    budget_limit: float | None = Field(default=None, ge=0)


class ProcurementUpdateRequest(BaseModel):
    status: str | None = None
    priority: str | None = None
