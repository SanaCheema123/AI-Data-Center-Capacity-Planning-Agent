from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ReportSection:
    title: str
    payload: dict[str, Any]


@dataclass(slots=True)
class ReportDocument:
    title: str
    sections: list[ReportSection] = field(default_factory=list)
