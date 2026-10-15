from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import engine
from app.schemas.system import HealthResponse, ReadinessCheck

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        service=settings.app_name,
        version="0.2.0",
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/system/readiness", response_model=ReadinessCheck)
def readiness() -> ReadinessCheck:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = "ok"
        status = "ok"
    except SQLAlchemyError:
        database = "unavailable"
        status = "degraded"
    return ReadinessCheck(status=status, database=database, environment=settings.app_env)
