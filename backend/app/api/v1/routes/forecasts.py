from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.domain import ForecastRun, User
from app.schemas.domain import ForecastRunRead
from app.schemas.forecasting import ForecastResponse, ForecastRunRequest
from app.services.forecasting import ForecastingService

router = APIRouter()


@router.get("", response_model=list[ForecastRunRead])
def list_forecasts(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = list(db.scalars(select(ForecastRun).order_by(ForecastRun.created_at.desc()).limit(200)))
    return [row for row in rows if (row.metrics or {}).get("data_origin") == "real"][:100]


@router.post("/run", response_model=ForecastResponse)
def run_forecast(
    payload: ForecastRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Admin", "Infrastructure Planner", "Analyst")),
) -> ForecastResponse:
    return ForecastingService.run(db, payload, user)


@router.get("/{run_id}", response_model=ForecastResponse)
def get_forecast(run_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> ForecastResponse:
    return ForecastingService.response_for_run(db, run_id)
