"""Shared canonical metric definitions used by every ingestion path.

CSV import, the Prometheus collector, and future OpenTelemetry/internal-API
collectors all normalize into this single metric-name -> (type, unit) registry
so forecasting always consumes consistent metric semantics regardless of the
ingestion source.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    name: str
    metric_type: str
    unit: str
    required: bool = True
    minimum: float = 0.0
    maximum: float | None = None


CANONICAL_METRICS: dict[str, MetricDefinition] = {
    definition.name: definition
    for definition in (
        MetricDefinition("gpu_utilization", "gpu", "%", maximum=100.0),
        MetricDefinition("installed_gpus", "gpu", "GPUs"),
        MetricDefinition("power_usage_mw", "power", "MW"),
        MetricDefinition("power_capacity_mw", "power", "MW"),
        MetricDefinition("cooling_power_mw", "power", "MW"),
        MetricDefinition("storage_used_tb", "storage", "TB"),
        MetricDefinition("storage_capacity_tb", "storage", "TB"),
        MetricDefinition("network_throughput_gbps", "network", "Gbps"),
        MetricDefinition("network_capacity_gbps", "network", "Gbps"),
    )
}

METRIC_NAMES: tuple[str, ...] = tuple(CANONICAL_METRICS)


def metric_type_for(name: str) -> str:
    return CANONICAL_METRICS[name].metric_type


def unit_for(name: str) -> str:
    return CANONICAL_METRICS[name].unit
