from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.domain import DataCenter, User
from app.schemas.domain import DataCenterCreate, DataCenterRead
from app.services.domain import DataCenterService

router = APIRouter()


@router.get("", response_model=list[DataCenterRead])
def list_data_centers(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[DataCenter]:
    return DataCenterService.list(db)


@router.post("", response_model=DataCenterRead, status_code=status.HTTP_201_CREATED)
def create_data_center(payload: DataCenterCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin", "Infrastructure Planner"))) -> DataCenter:
    return DataCenterService.create(db, payload)
