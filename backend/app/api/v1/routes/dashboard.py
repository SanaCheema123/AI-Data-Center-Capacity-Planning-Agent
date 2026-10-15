from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.domain import User
from app.schemas.domain import DashboardSummary
from app.services.domain import DashboardService

router = APIRouter()

@router.get("/summary", response_model=DashboardSummary)
def summary(data_center_id: int | None = Query(default=None), db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> DashboardSummary:
    return DashboardService.summary(db, data_center_id)
