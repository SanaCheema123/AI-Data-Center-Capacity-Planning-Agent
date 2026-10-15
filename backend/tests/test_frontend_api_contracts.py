"""Contract guard for every endpoint currently consumed by the React frontend.

This test intentionally checks method + path presence in FastAPI's OpenAPI schema so a
backend route rename cannot silently break the frontend API client.
"""
from app.main import app


EXPECTED = {
    ("post", "/api/v1/auth/register"),
    ("post", "/api/v1/data-sources/csv/import"),
    ("patch", "/api/v1/procurement/{recommendation_id}"),
    ("get", "/api/v1/reports/{report_id}/pdf"),
    ("get", "/api/v1/reports/{report_id}/csv"),
    ("post", "/api/v1/scenarios"),
    ("get", "/api/v1/settings/appearance/me"),
    ("patch", "/api/v1/settings/appearance/me"),
    ("post", "/api/v1/auth/login"),
    ("post", "/api/v1/auth/refresh"),
    ("get", "/api/v1/auth/me"),
    ("get", "/api/v1/dashboard/summary"),
    ("get", "/api/v1/data-centers"),
    ("get", "/api/v1/data-sources"),
    ("get", "/api/v1/alerts"),
    ("post", "/api/v1/alerts/evaluate"),
    ("patch", "/api/v1/alerts/{alert_id}"),
    ("get", "/api/v1/procurement"),
    ("post", "/api/v1/procurement/generate"),
    ("get", "/api/v1/reports"),
    ("get", "/api/v1/reports/catalog"),
    ("post", "/api/v1/reports/generate"),
    ("get", "/api/v1/scenarios"),
    ("get", "/api/v1/scenarios/compare"),
    ("post", "/api/v1/scenarios/run"),
    ("get", "/api/v1/ai/recommendations"),
    ("post", "/api/v1/ai/workflow"),
    ("post", "/api/v1/ai/chat"),
    ("get", "/api/v1/ai/status"),
    ("get", "/api/v1/settings"),
    ("patch", "/api/v1/settings/{key}"),
    ("get", "/api/v1/settings/notifications/me"),
    ("patch", "/api/v1/settings/notifications/me"),
    ("get", "/api/v1/gpu/forecast"),
    ("post", "/api/v1/gpu/forecast/run"),
    ("get", "/api/v1/power/forecast"),
    ("post", "/api/v1/power/forecast/run"),
    ("get", "/api/v1/storage/forecast"),
    ("post", "/api/v1/storage/forecast/run"),
    ("get", "/api/v1/network/forecast"),
    ("post", "/api/v1/network/forecast/run"),
}


def test_frontend_consumed_routes_exist_with_expected_http_methods() -> None:
    spec = app.openapi()
    available = {
        (method.lower(), path)
        for path, item in spec["paths"].items()
        for method in item
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    }
    missing = EXPECTED - available
    assert not missing, f"Frontend/backend API contract mismatch: missing {sorted(missing)}"
