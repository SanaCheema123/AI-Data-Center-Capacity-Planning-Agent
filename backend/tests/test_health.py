import os

os.environ["DATABASE_URL"] = "sqlite:///./test_health.db"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "AI Data Center Capacity Planning Agent"
