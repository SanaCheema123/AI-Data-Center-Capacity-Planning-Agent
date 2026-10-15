from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.domain import Role, User

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def seed_roles_and_admin() -> None:
    with TestingSessionLocal() as db:
        for name in ["Admin", "Infrastructure Planner", "Analyst", "Viewer"]:
            if not db.scalar(select(Role).where(Role.name == name)):
                db.add(Role(name=name, description=name))
        db.commit()
        admin_role = db.scalar(select(Role).where(Role.name == "Admin"))
        if not db.scalar(select(User).where(User.email == "admin@example.com")):
            db.add(
                User(
                    email="admin@example.com",
                    full_name="Test Admin",
                    password_hash=hash_password("Admin123!"),
                    roles=[admin_role],
                )
            )
            db.commit()


seed_roles_and_admin()


def login(email: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def test_register_login_and_me() -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "viewer@example.com", "full_name": "Test Viewer", "password": "Viewer123!"},
    )
    assert response.status_code in (201, 409)
    tokens = login("viewer@example.com", "Viewer123!")
    assert tokens["token_type"] == "bearer"
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "viewer@example.com"
    assert me.json()["roles"][0]["name"] == "Viewer"


def test_rbac_blocks_viewer_write_and_allows_admin() -> None:
    viewer = login("viewer@example.com", "Viewer123!")
    payload = {"name": "Test DC", "code": "TEST-DC", "region": "test", "country": "PK", "timezone": "UTC"}
    denied = client.post("/api/v1/data-centers", json=payload, headers={"Authorization": f"Bearer {viewer['access_token']}"})
    assert denied.status_code == 403

    admin = login("admin@example.com", "Admin123!")
    created = client.post("/api/v1/data-centers", json=payload, headers={"Authorization": f"Bearer {admin['access_token']}"})
    assert created.status_code in (201, 409)


def test_dashboard_requires_auth_and_returns_database_counts() -> None:
    unauth = client.get("/api/v1/dashboard/summary")
    assert unauth.status_code == 401
    admin = login("admin@example.com", "Admin123!")
    response = client.get("/api/v1/dashboard/summary", headers={"Authorization": f"Bearer {admin['access_token']}"})
    assert response.status_code == 200
    body = response.json()
    assert body["data_centers"] >= 0
    assert "latest_metric_at" in body


def test_production_settings_reject_unsafe_defaults() -> None:
    import pytest
    from pydantic import ValidationError
    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="production",
            app_debug=False,
            database_url="sqlite:///unsafe.db",
            jwt_secret="development-only-change-me-32-byte-secret-key",
            frontend_origin="*",
        )

    safe = Settings(
        _env_file=None,
        app_env="production",
        app_debug=False,
        database_url="postgresql+psycopg://capacity:secret@postgres:5432/capacity",
        jwt_secret="9fa5c46995764ce8a17717692457e361e2ae873c95ff4f85",
        frontend_origin="https://capacity.example.com",
    )
    assert safe.app_env == "production"


def test_rbac_protects_planning_mutations() -> None:
    viewer = login("viewer@example.com", "Viewer123!")
    viewer_headers = {"Authorization": f"Bearer {viewer['access_token']}"}
    assert client.post('/api/v1/procurement/generate', headers=viewer_headers, json={'data_center_id': None}).status_code == 403
    assert client.post('/api/v1/reports/generate', headers=viewer_headers, json={'report_type': 'executive', 'data_center_id': None}).status_code == 403
    assert client.post('/api/v1/scenarios/run', headers=viewer_headers).status_code == 403
    assert client.post('/api/v1/alerts/evaluate', headers=viewer_headers, json={'data_center_id': None}).status_code == 403
