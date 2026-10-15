"""Minimal local Prometheus fixture for end-to-end connector testing.

Serves /-/ready and /api/v1/query_range with deterministic 30-day daily series
for the default collector expressions. This is a testing fixture that stands in
for a real Prometheus server; point the data source base_url at your actual
Prometheus for production data.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

METRIC_HINTS = [
    ("gpu_utilization", 55.0, 0.9),
    ("installed_gpus", 128.0, 0.0),
    ("power_usage_mw", 18.0, 0.35),
    ("power_capacity_mw", 50.0, 0.0),
    ("cooling_power_mw", 4.5, 0.02),
    ("storage_used_tb", 900.0, 12.0),
    ("storage_capacity_tb", 2000.0, 0.0),
    ("network_throughput_gbps", 120.0, 6.0),
]


def _series_for(query: str, start: datetime, end: datetime) -> list[tuple[int, float]]:
    name = next((n for n, _, _ in METRIC_HINTS if n in query), None)
    if name is None:
        return []
    base, slope = next((b, s) for n, b, s in METRIC_HINTS if n == name)
    points = []
    current = start.replace(hour=0, minute=0, second=0, microsecond=0)
    step = 0
    while current <= end:
        if name == "installed_gpus" or name == "power_capacity_mw" or name == "storage_capacity_tb":
            value = base
        else:
            value = base + slope * (step / 7.0) + (math.sin(step / 3.0) * slope * 0.2 if slope else 0.0)
        points.append((int(current.timestamp()), round(max(value, 0.0), 4)))
        current += timedelta(days=1)
        step += 1
    return points


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep fixture output quiet
        pass

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/-/ready":
            return self._json({"status": "ready"})
        if parsed.path == "/api/v1/query_range":
            params = parse_qs(parsed.query)
            query = params.get("query", [""])[0]
            start = datetime.fromisoformat(params.get("start", ["1970-01-01T00:00:00+00:00"])[0])
            end = datetime.fromisoformat(params.get("end", ["1970-01-02T00:00:00+00:00"])[0])
            values = _series_for(query, start, end)
            match = re.search(r'datacenter="([^"]+)"', query)
            metric = METRIC_HINTS[0][0] if match is None else next((n for n, _, _ in METRIC_HINTS if n in query), METRIC_HINTS[0][0])
            result = [{
                "metric": {"datacenter": match.group(1) if match else "PROM-DC", "__name__": metric},
                "values": [[str(ts), repr(v)] for ts, v in values],
            }]
            return self._json({"status": "success", "data": {"resultType": "matrix", "result": result}})
        return self._json({"status": "error", "errorType": "bad_path", "error": self.path}, 404)


def main() -> None:
    server = HTTPServer(("127.0.0.1", 9090), Handler)
    print("Prometheus fixture listening on http://127.0.0.1:9090")
    server.serve_forever()


if __name__ == "__main__":
    main()
