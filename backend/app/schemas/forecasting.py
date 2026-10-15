from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ResourceType = Literal["gpu", "power", "storage", "network"]
ModelType = Literal["prophet", "xgboost"]
FrequencyType = Literal["daily", "weekly", "monthly"]


class ForecastRunRequest(BaseModel):
    resource_type: ResourceType
    model: ModelType = "prophet"
    data_center_id: int | None = None
    horizon: int = Field(default=12, ge=1, le=60)
    frequency: FrequencyType = "monthly"
    confidence: float = Field(default=0.90, ge=0.50, lt=1.0)


class ResourceForecastRunRequest(BaseModel):
    model: ModelType = "prophet"
    data_center_id: int | None = None
    horizon: int = Field(default=12, ge=1, le=60)
    frequency: FrequencyType = "monthly"
    confidence: float = Field(default=0.90, ge=0.50, lt=1.0)


class ForecastPointRead(BaseModel):
    timestamp: datetime
    predicted: float
    lower: float | None
    upper: float | None
    capacity: float | None


class AccuracyMetrics(BaseModel):
    mae: float
    rmse: float
    mape: float
    r2: float


class CapacitySummary(BaseModel):
    current_usage: float
    current_capacity: float
    utilization_percent: float
    headroom: float
    peak_demand: float
    peak_demand_at: datetime
    shortage_date: datetime | None
    required_expansion: float


class ForecastResponse(BaseModel):
    run_id: int
    resource_type: ResourceType
    model: str
    model_engine: str
    unit: str
    data_center_id: int | None
    frequency: str
    confidence: float
    capacity: CapacitySummary
    accuracy: AccuracyMetrics
    points: list[ForecastPointRead]


class ForecastListQuery(BaseModel):
    resource_type: ResourceType | None = None
    data_center_id: int | None = None
