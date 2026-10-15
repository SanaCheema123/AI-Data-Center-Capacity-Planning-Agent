from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.domain import Scenario, User
from app.schemas.domain import ScenarioRead
from app.schemas.planning import ScenarioComparison, ScenarioCreateRequest, ScenarioUpdateRequest
from app.services.planning import ScenarioService

router = APIRouter()


@router.get("", response_model=list[ScenarioRead])
def list_scenarios(
    data_center_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Scenario)
    if data_center_id is not None:
        stmt = stmt.where((Scenario.data_center_id == data_center_id) | (Scenario.data_center_id.is_(None)))
    return list(db.scalars(stmt.order_by(Scenario.created_at.desc()).limit(100)))


@router.post("", response_model=ScenarioRead, status_code=status.HTTP_201_CREATED)
def create_scenario(
    payload: ScenarioCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Admin", "Infrastructure Planner", "Analyst")),
):
    assumptions = {
        "gpu_multiplier": payload.gpu_multiplier,
        "power_multiplier": payload.power_multiplier,
        "storage_multiplier": payload.storage_multiplier,
        "network_multiplier": payload.network_multiplier,
        "budget_limit": payload.budget_limit,
        "source": "user",
    }
    obj = Scenario(
        name=payload.name,
        description=payload.description,
        scenario_type="custom",
        data_center_id=payload.data_center_id,
        planning_horizon_months=payload.planning_horizon_months,
        assumptions=assumptions,
        created_by=user.id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# Static paths intentionally precede /{scenario_id} to prevent route shadowing.
@router.get("/compare", response_model=list[ScenarioComparison])
def compare(
    data_center_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ScenarioService.compare(db, data_center_id)


@router.post("/run", response_model=list[ScenarioComparison])
def run(
    data_center_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Infrastructure Planner", "Analyst")),
):
    return ScenarioService.compare(db, data_center_id, persist=True)


@router.get("/{scenario_id}", response_model=ScenarioRead)
def get_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = db.get(Scenario, scenario_id)
    if not obj:
        raise NotFoundError("Scenario not found")
    return obj


@router.patch("/{scenario_id}", response_model=ScenarioRead)
def update_scenario(
    scenario_id: int,
    payload: ScenarioUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Infrastructure Planner", "Analyst")),
):
    obj = db.get(Scenario, scenario_id)
    if not obj:
        raise NotFoundError("Scenario not found")
    data = payload.model_dump(exclude_unset=True)
    for field in ("name", "description", "planning_horizon_months"):
        if field in data:
            setattr(obj, field, data.pop(field))
    assumptions = dict(obj.assumptions or {})
    for field in ("gpu_multiplier", "power_multiplier", "storage_multiplier", "network_multiplier", "budget_limit"):
        if field in data:
            assumptions[field] = data[field]
    obj.assumptions = assumptions
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Infrastructure Planner")),
):
    obj = db.get(Scenario, scenario_id)
    if not obj:
        raise NotFoundError("Scenario not found")
    if obj.scenario_type in {"conservative", "base", "aggressive"}:
        raise ValueError("Seeded baseline scenarios cannot be deleted")
    db.delete(obj)
    db.commit()
