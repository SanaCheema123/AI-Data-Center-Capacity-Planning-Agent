"""Smoke-check FastAPI contracts consumed by the React frontend.

Two modes are supported:

1. Safe fixture mode (used only by ``validate_project.py`` against a temporary DB):
   ``SMOKE_FIXTURE_MODE=true``. The script registers a temporary admin and imports
   deterministic test telemetry into that temporary database.
2. Existing real database: provide ``SMOKE_ADMIN_EMAIL`` and
   ``SMOKE_ADMIN_PASSWORD``. No telemetry is created in this mode.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dateutil.relativedelta import relativedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from app.main import app


def fixture_csv() -> str:
    rows = [
        "timestamp,data_center,cluster,gpu_utilization,installed_gpus,power_usage_mw,power_capacity_mw,storage_used_tb,storage_capacity_tb,network_throughput_gbps,cooling_power_mw,network_capacity_gbps"
    ]
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for i in range(30):
        ts = start + relativedelta(months=i)
        rows.append(
            f"{ts.isoformat()},SMOKE-REAL-DC,gpu-a,{48+i*0.7:.2f},128,"
            f"{10+i*0.2:.2f},28,{450+i*15:.2f},1400,{70+i*2.6:.2f},3.0,350"
        )
    return "\n".join(rows)


def main() -> None:
    client = TestClient(app)
    fixture_mode = os.getenv("SMOKE_FIXTURE_MODE", "").lower() == "true"
    if fixture_mode:
        email = "smoke-owner@example.org"
        password = "SmokeOwner123!"
        registered = client.post('/api/v1/auth/register', json={'email': email, 'full_name': 'Smoke Owner', 'password': password})
        if registered.status_code not in (201, 409):
            raise RuntimeError(f'fixture registration failed: {registered.status_code} {registered.text}')
    else:
        email = os.getenv("SMOKE_ADMIN_EMAIL", "")
        password = os.getenv("SMOKE_ADMIN_PASSWORD", "")
        if not email or not password:
            raise SystemExit("Set SMOKE_ADMIN_EMAIL/SMOKE_ADMIN_PASSWORD, or use SMOKE_FIXTURE_MODE=true only with a disposable database")

    login = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    login.raise_for_status()
    token = login.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    data_center_id = None
    if fixture_mode:
        imported = client.post(
            '/api/v1/data-sources/csv/import', headers=headers,
            files={'file': ('smoke-real-metrics.csv', fixture_csv(), 'text/csv')},
        )
        if imported.status_code != 200 or imported.json()['rows_imported'] < 24:
            raise RuntimeError(f'fixture CSV import failed: {imported.status_code} {imported.text}')
        centers = client.get('/api/v1/data-centers', headers=headers).json()
        data_center_id = next(dc['id'] for dc in centers if dc['name'] == 'SMOKE-REAL-DC')

        settings = client.get('/api/v1/settings', headers=headers).json()
        forecast = next(item for item in settings if item['key'] == 'forecast')['value']
        forecast_payload = {
            'model': 'xgboost',
            'horizon': min(12, int(forecast['horizon_months'])),
            'frequency': 'monthly',
            'confidence': float(forecast['confidence_interval']),
            'data_center_id': data_center_id,
        }
        for resource in ('gpu', 'power', 'storage', 'network'):
            path = f'/api/v1/{resource}/forecast/run'
            response = client.post(path, headers=headers, json=forecast_payload)
            if response.status_code != 200 or not response.json().get('points'):
                raise RuntimeError(f'POST {path}: {response.status_code} {response.text}')
            print(f'POST  {path:<42} 200 ({len(response.json()["points"])} points)')

    params = {'data_center_id': data_center_id} if data_center_id else None
    reads = [
        '/api/v1/auth/me', '/api/v1/dashboard/summary', '/api/v1/data-centers',
        '/api/v1/data-sources', '/api/v1/alerts', '/api/v1/procurement',
        '/api/v1/reports', '/api/v1/reports/catalog', '/api/v1/scenarios',
        '/api/v1/scenarios/compare', '/api/v1/ai/recommendations', '/api/v1/settings',
        '/api/v1/settings/notifications/me', '/api/v1/settings/appearance/me',
    ]
    for path in reads:
        response = client.get(path, headers=headers, params=params if path not in {'/api/v1/auth/me','/api/v1/data-sources','/api/v1/reports/catalog','/api/v1/settings','/api/v1/settings/notifications/me','/api/v1/settings/appearance/me'} else None)
        if response.status_code != 200:
            raise RuntimeError(f'GET {path}: {response.status_code} {response.text}')
        print(f'GET   {path:<42} 200')

    if fixture_mode:
        mutations = [
            ('/api/v1/scenarios/run', None),
            ('/api/v1/procurement/generate', {'data_center_id': data_center_id}),
            ('/api/v1/alerts/evaluate', {'data_center_id': data_center_id}),
        ]
        for path, body in mutations:
            response = client.post(path, headers=headers, json=body, params=params if path.endswith('/run') else None)
            if response.status_code != 200:
                raise RuntimeError(f'POST {path}: {response.status_code} {response.text}')
            print(f'POST  {path:<42} 200')

        report = client.post('/api/v1/reports/generate', headers=headers, json={'report_type': 'executive', 'data_center_id': data_center_id})
        if report.status_code != 200:
            raise RuntimeError(f'POST /api/v1/reports/generate: {report.status_code} {report.text}')
        report_id = report.json()['id']
        csv_artifact = client.get(f'/api/v1/reports/{report_id}/csv', headers=headers)
        if csv_artifact.status_code != 200:
            raise RuntimeError(f'GET report csv: {csv_artifact.status_code}')
        print(f'GET   {f"/api/v1/reports/{report_id}/csv":<42} 200')

    print('\nFrontend/backend API contract smoke check passed.')


if __name__ == '__main__':
    main()
