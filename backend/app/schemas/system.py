from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    timestamp: datetime


class ReadinessCheck(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]
    environment: str
