from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class TimePoint:
    timestamp: datetime
    value: float


@dataclass(frozen=True, slots=True)
class ForecastRequest:
    history: Sequence[TimePoint]
    horizon: int
    frequency: str
    confidence: float
    seasonal_period: int | None = None


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    timestamp: datetime
    predicted: float
    lower: float | None = None
    upper: float | None = None


@dataclass(frozen=True, slots=True)
class ForecastSeries:
    points: Sequence[ForecastPoint]
    model_name: str
    metrics: dict[str, float | str | None] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ForecastModel(ABC):
    name: str

    @abstractmethod
    def fit_predict(self, request: ForecastRequest) -> ForecastSeries:
        raise NotImplementedError
