from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.domain import Report, User
from app.schemas.domain import ReportRead
from app.schemas.planning import ReportCatalogItem, ReportGenerateRequest
from app.services.planning import ReportService
from app.services.reporting import ProductionReportService
from app.services.data_scope import real_data_center_ids

router = APIRouter()

@router.get("", response_model=list[ReportRead])
def list_reports(data_center_id: int | None = Query(default=None), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(Report)
    expected_ids = set(real_data_center_ids(db)) if data_center_id is None else {data_center_id}
    if data_center_id is None:
        stmt = stmt.where(Report.data_center_id.is_(None))
    else:
        stmt = stmt.where(Report.data_center_id == data_center_id)
    rows = list(db.scalars(stmt.order_by(Report.created_at.desc()).limit(200)))
    return [
        row for row in rows
        if (row.metadata_json or {}).get("data_origin") == "real"
        and set((row.metadata_json or {}).get("data_center_ids") or []) == expected_ids
    ][:100]

@router.get("/catalog", response_model=list[ReportCatalogItem])
def catalog(_: User = Depends(get_current_user)):
    return [ReportCatalogItem(report_type=x[0], title=x[1], description=x[2]) for x in ReportService.CATALOG]

@router.post("/generate", response_model=ReportRead)
def generate(payload: ReportGenerateRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("Admin", "Infrastructure Planner", "Analyst"))):
    return ReportService.generate(db, payload.report_type, payload.data_center_id, user)

@router.get("/{report_id}", response_model=ReportRead)
def get_report(report_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    report = db.get(Report, report_id)
    if not report or (report.metadata_json or {}).get("data_origin") != "real":
        raise NotFoundError("Report not found")
    return report

@router.get("/{report_id}/pdf")
def download_pdf(report_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    report = db.get(Report, report_id)
    if not report or (report.metadata_json or {}).get("data_origin") != "real":
        raise NotFoundError("Report not found")
    path = ProductionReportService.artifact(report, "pdf")
    return FileResponse(path, media_type="application/pdf", filename=f"{report.report_type}-{report.id}.pdf")

@router.get("/{report_id}/csv")
def download_csv(report_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    report = db.get(Report, report_id)
    if not report or (report.metadata_json or {}).get("data_origin") != "real":
        raise NotFoundError("Report not found")
    path = ProductionReportService.artifact(report, "csv")
    return FileResponse(path, media_type="text/csv", filename=f"{report.report_type}-{report.id}.csv")
