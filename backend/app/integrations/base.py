from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class NormalizedMetric:
    timestamp: datetime
    data_center: str
    metric_name: str
    value: float
    unit: str
    cluster: str | None = None
    attributes: dict[str, Any] | None = None


class MetricSource(ABC):
    @abstractmethod
    def test_connection(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def collect(self) -> Iterable[NormalizedMetric]:
        raise NotImplementedError
