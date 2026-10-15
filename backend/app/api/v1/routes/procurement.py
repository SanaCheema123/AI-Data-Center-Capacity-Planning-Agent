from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, require_roles
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.domain import ForecastRun, ProcurementRecommendation, User
from app.schemas.domain import ProcurementRead
from app.schemas.planning import ProcurementGenerateRequest, ProcurementUpdateRequest
from app.services.planning import ProcurementService
from app.services.data_scope import real_data_center_ids

router = APIRouter()
VALID_STATUSES={"planned","approved","in_review","ordered","completed","cancelled"}
VALID_PRIORITIES={"low","medium","high"}

@router.get("", response_model=list[ProcurementRead])
def list_procurement(data_center_id: int | None = Query(default=None), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(ProcurementRecommendation)
    expected_ids = set(real_data_center_ids(db)) if data_center_id is None else {data_center_id}
    if data_center_id is None:
        stmt = stmt.where(ProcurementRecommendation.data_center_id.is_(None))
    else:
        stmt = stmt.where(ProcurementRecommendation.data_center_id == data_center_id)
    rows = list(db.scalars(stmt.order_by(ProcurementRecommendation.created_at.desc()).limit(100)))
    real_rows = []
    for row in rows:
        run = db.get(ForecastRun, row.forecast_run_id) if row.forecast_run_id else None
        if run and (run.metrics or {}).get("data_origin") == "real" and set((run.metrics or {}).get("data_center_ids") or []) == expected_ids:
            real_rows.append(row)
    return real_rows

@router.post("/generate", response_model=list[ProcurementRead])
def generate(payload: ProcurementGenerateRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin", "Infrastructure Planner"))):
    return ProcurementService.generate(db, payload.data_center_id)

@router.patch("/{recommendation_id}", response_model=ProcurementRead)
def update_recommendation(recommendation_id: int, payload: ProcurementUpdateRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin", "Infrastructure Planner"))):
    obj = db.get(ProcurementRecommendation, recommendation_id)
    if not obj: raise NotFoundError("Procurement recommendation not found")
    if payload.status is not None:
        if payload.status not in VALID_STATUSES: raise ValueError("Unsupported procurement status")
        obj.status = payload.status
    if payload.priority is not None:
        if payload.priority not in VALID_PRIORITIES: raise ValueError("Unsupported procurement priority")
        obj.priority = payload.priority
    db.commit(); db.refresh(obj); return obj
