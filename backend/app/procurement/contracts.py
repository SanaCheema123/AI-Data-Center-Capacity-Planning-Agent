from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class CapacityGap:
    resource: str
    current_capacity: float
    required_capacity: float
    unit: str
    required_by: date | None = None
