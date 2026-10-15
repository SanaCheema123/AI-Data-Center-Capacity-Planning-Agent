from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.models.domain import DataCenter, Role
from app.schemas.auth import UserCreate
from app.services.auth import AuthService
from test_backend_foundation import client, login


def test_first_local_registration_can_bootstrap_admin(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(settings, 'allow_public_registration', True)
    monkeypatch.setattr(settings, 'bootstrap_first_user_as_admin', True)
    with Session() as db:
        db.add_all([
            Role(name='Admin', description='Admin'),
            Role(name='Viewer', description='Viewer'),
        ])
        db.commit()
        user = AuthService.register(db, UserCreate(email='first@company.com', full_name='First Owner', password='StrongPass123!'))
        assert [role.name for role in user.roles] == ['Admin']


def test_csv_import_registers_unknown_real_data_center():
    tokens = login('admin@example.com', 'Admin123!')
    headers = {'Authorization': f"Bearer {tokens['access_token']}"}
    body = '\n'.join([
        'timestamp,data_center,cluster,gpu_utilization,installed_gpus,power_usage_mw,power_capacity_mw,storage_used_tb,storage_capacity_tb,network_throughput_gbps,cooling_power_mw,network_capacity_gbps',
        '2026-02-01T00:00:00Z,REAL-IMPORT-DC,gpu-a,62,64,8,20,400,1000,90,2,200',
    ])
    response = client.post('/api/v1/data-sources/csv/import', headers=headers, files={'file': ('real.csv', body, 'text/csv')})
    assert response.status_code == 200, response.text
    assert response.json()['rows_imported'] == 1
    centers = client.get('/api/v1/data-centers', headers=headers)
    assert any(dc['name'] == 'REAL-IMPORT-DC' for dc in centers.json())


def test_data_center_list_hides_demo_and_empty_centers():
    tokens = login('admin@example.com', 'Admin123!')
    headers = {'Authorization': f"Bearer {tokens['access_token']}"}
    centers = client.get('/api/v1/data-centers', headers=headers)
    assert centers.status_code == 200
    names = {dc['name'] for dc in centers.json()}
    assert 'REAL-IMPORT-DC' in names
    # Reference/demo-only centers without real telemetry must not leak into selector.
    assert all('US-East' not in name and 'Development Cluster' not in name for name in names)


def test_csv_source_reports_covered_data_centers():
    tokens = login('admin@example.com', 'Admin123!')
    headers = {'Authorization': f"Bearer {tokens['access_token']}"}
    response = client.get('/api/v1/data-sources', headers=headers)
    assert response.status_code == 200
    csv_sources = [x for x in response.json() if x['source_type'] == 'csv']
    assert csv_sources
    assert csv_sources[0]['metric_count'] > 0
    assert any('REAL-IMPORT-DC' in source['data_center_names'] for source in csv_sources)
