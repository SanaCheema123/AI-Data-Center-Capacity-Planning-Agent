"""Prometheus collector implementing the MetricSource contract.

Pulls daily history for every canonical infrastructure metric through the
Prometheus HTTP API (``/api/v1/query_range``). Expressions, the data-center
label, and the lookback window are configurable per data source; the defaults
target common GPU/node exporter metric names.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import httpx

from app.integrations.base import MetricSource, NormalizedMetric
from app.integrations.metrics import CANONICAL_METRICS

DEFAULT_EXPRESSIONS: dict[str, str] = {
    "gpu_utilization": 'avg(DCGM_FI_DEV_GPU_UTIL{datacenter="{dc}"})',
    "installed_gpus": 'count(DCGM_FI_DEV_GPU_UTIL{datacenter="{dc}"})',
    "power_usage_mw": 'sum(node_rapl_package_power_watt{datacenter="{dc}"}) / 1e6',
    "power_capacity_mw": 'sum(node_power_capacity_watts{datacenter="{dc}"}) / 1e6',
    "cooling_power_mw": 'sum(cooling_power_watts{datacenter="{dc}"}) / 1e6',
    "storage_used_tb": 'sum(node_filesystem_size_bytes{datacenter="{dc}"} - node_filesystem_free_bytes{datacenter="{dc}"}) / 1e12',
    "storage_capacity_tb": 'sum(node_filesystem_size_bytes{datacenter="{dc}"}) / 1e12',
    "network_throughput_gbps": 'sum(rate(node_network_receive_bytes_total{datacenter="{dc}"}[5m]) + rate(node_network_transmit_bytes_total{datacenter="{dc}"}[5m])) * 8 / 1e9',
    "network_capacity_gbps": 'sum(node_network_capacity_bps{datacenter="{dc}"}) / 1e9',
}

DEFAULT_LOOKBACK_DAYS = 90
_STEP_SECONDS = 86400  # daily resolution keeps query_range payloads bounded


class PrometheusCollector(MetricSource):
    def __init__(
        self,
        base_url: str,
        data_center_code: str,
        *,
        api_path: str = "/api/v1/query_range",
        expressions: dict[str, str] | None = None,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
        timeout_seconds: float = 30.0,
        verify_tls: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_path = api_path if api_path.startswith("/") else f"/{api_path}"
        self.data_center_code = data_center_code
        self.expressions = {**DEFAULT_EXPRESSIONS, **(expressions or {})}
        self.lookback_days = lookback_days
        self.timeout_seconds = timeout_seconds
        self.verify_tls = verify_tls

    def _params(self, expression: str, start: datetime, end: datetime) -> dict[str, str]:
        return {
            "query": expression.format(dc=self.data_center_code),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "step": f"{_STEP_SECONDS}s",
        }

    def _query_range(self, client: httpx.Client, expression: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
        response = client.get(self.base_url + self.api_path, params=self._params(expression, start, end))
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise ValueError(f"Prometheus query failed: {payload.get('errorType')}: {payload.get('error')}")
        return payload.get("data", {}).get("result", [])

    @staticmethod
    def _series_points(result: dict[str, Any]) -> list[tuple[datetime, float]]:
        points: list[tuple[datetime, float]] = []
        for timestamp_seconds, raw_value in result.get("values", []):
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            # NaN/Inf sentinels from Prometheus are not valid metric samples.
            if value != value or value in (float("inf"), float("-inf")):
                continue
            points.append((datetime.fromtimestamp(float(timestamp_seconds), tz=timezone.utc), value))
        return points

    def test_connection(self) -> bool:
        try:
            with httpx.Client(timeout=self.timeout_seconds, verify=self.verify_tls) as client:
                response = client.get(self.base_url + "/-/ready")
                return response.status_code == 200
        except Exception:
            return False

    def collect(self) -> Iterable[NormalizedMetric]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=self.lookback_days)
        with httpx.Client(timeout=self.timeout_seconds, verify=self.verify_tls) as client:
            for name, definition in CANONICAL_METRICS.items():
                for timestamp, value in self._series_points(
                    self._query_range(client, self.expressions[name], start, end)
                ):
                    yield NormalizedMetric(
                        timestamp=timestamp,
                        data_center=self.data_center_code,
                        metric_name=name,
                        value=value,
                        unit=definition.unit,
                        attributes={"source": "prometheus"},
                    )
