from pathlib import Path

import pytest

from app.core.config import settings
from app.models.domain import InfrastructureMetric
from sqlalchemy import select

from test_backend_foundation import TestingSessionLocal, client, login


def _pdf_engine_available() -> bool:
    try:
        import reportlab  # noqa: F401
        return True
    except Exception:
        try:
            import weasyprint  # noqa: F401
            return True
        except Exception:
            return False


requires_pdf_engine = pytest.mark.skipif(
    not _pdf_engine_available(),
    reason="WeasyPrint native libraries (GTK/Pango) are not installed on this host",
)


def _auth():
    tokens = login("admin@example.com", "Admin123!")
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_csv_import_validates_and_deduplicates():
    headers = _auth()
    body = "\n".join([
        "timestamp,data_center,cluster,gpu_utilization,installed_gpus,power_usage_mw,power_capacity_mw,storage_used_tb,storage_capacity_tb,network_throughput_gbps,cooling_power_mw,network_capacity_gbps",
        "2026-01-01T00:00:00Z,TEST-DC,training-a,72,128,20,40,1000,2000,250,5,500",
    ])
    r = client.post("/api/v1/data-sources/csv/import", headers=headers, files={"file": ("metrics.csv", body, "text/csv")})
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["rows_imported"] == 1
    assert result["metrics_inserted"] == 9

    again = client.post("/api/v1/data-sources/csv/import", headers=headers, files={"file": ("metrics.csv", body, "text/csv")})
    assert again.status_code == 200
    assert again.json()["metrics_inserted"] == 0
    assert again.json()["duplicates_skipped"] == 9


@requires_pdf_engine
def test_report_generates_real_pdf_and_csv_artifacts():
    headers = _auth()
    r = client.post("/api/v1/reports/generate", headers=headers, json={"report_type": "executive", "data_center_id": None})
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["status"] == "completed"
    pdf = client.get(f"/api/v1/reports/{report['id']}/pdf", headers=headers)
    csv = client.get(f"/api/v1/reports/{report['id']}/csv", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")
    assert csv.status_code == 200
    assert "section,resource_or_name,metric,value" in csv.text


def test_report_csv_artifact_is_generated_even_without_pdf_engine():
    """On hosts without WeasyPrint native libraries the report must still be
    honestly recorded as completed with a real CSV artifact and an explicit
    pdf_error note, and PDF download must 404 instead of crashing."""
    if _pdf_engine_available():
        pytest.skip("PDF engine is available; degradation path only applies without native libraries")
    headers = _auth()
    r = client.post("/api/v1/reports/generate", headers=headers, json={"report_type": "executive", "data_center_id": None})
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["status"] == "completed"
    csv = client.get(f"/api/v1/reports/{report['id']}/csv", headers=headers)
    assert csv.status_code == 200
    assert "section,resource_or_name,metric,value" in csv.text
    pdf = client.get(f"/api/v1/reports/{report['id']}/pdf", headers=headers)
    assert pdf.status_code == 404
    with TestingSessionLocal() as db:
        from app.models.domain import Report
        row = db.get(Report, report["id"])
        assert row is not None
        assert row.metadata_json.get("pdf_available") is False
        assert "PDF rendering is unavailable" in row.metadata_json.get("pdf_error", "")

def test_appearance_scenario_and_procurement_mutation_contracts():
    headers = _auth()
    appearance = client.patch('/api/v1/settings/appearance/me', headers=headers, json={'theme':'dark','accent':'purple','compact_mode':True})
    assert appearance.status_code == 200
    assert appearance.json()['theme'] == 'dark'

    scenario = client.post('/api/v1/scenarios', headers=headers, json={
        'name':'Audit Custom', 'description':'audit', 'planning_horizon_months':24,
        'data_center_id':None, 'gpu_multiplier':1.1, 'power_multiplier':1.05,
        'storage_multiplier':1.08, 'network_multiplier':1.09
    })
    assert scenario.status_code == 201, scenario.text
    assert scenario.json()['scenario_type'] == 'custom'


def test_report_csv_neutralizes_spreadsheet_formulas():
    from app.services.reporting import ProductionReportService
    assert ProductionReportService._safe_csv_cell('=1+1') == "'=1+1"
    assert ProductionReportService._safe_csv_cell('+cmd') == "'+cmd"
    assert ProductionReportService._safe_csv_cell('normal') == 'normal'
