from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.domain import User
from app.schemas.forecasting import ForecastResponse, ForecastRunRequest, ResourceForecastRunRequest
from app.services.forecasting import ForecastingService


def create_resource_router(resource_type: str) -> APIRouter:
    router = APIRouter()

    @router.get("/forecast", response_model=ForecastResponse)
    def latest_forecast(
        data_center_id: int | None = Query(default=None),
        db: Session = Depends(get_db),
        _: User = Depends(get_current_user),
    ) -> ForecastResponse:
        return ForecastingService.latest(db, resource_type, data_center_id)

    @router.post("/forecast/run", response_model=ForecastResponse)
    def run_forecast(
        payload: ResourceForecastRunRequest,
        db: Session = Depends(get_db),
        user: User = Depends(require_roles("Admin", "Infrastructure Planner", "Analyst")),
    ) -> ForecastResponse:
        request = ForecastRunRequest(resource_type=resource_type, **payload.model_dump())
        return ForecastingService.run(db, request, user)

    return router


gpu_router = create_resource_router("gpu")
power_router = create_resource_router("power")
storage_router = create_resource_router("storage")
network_router = create_resource_router("network")
