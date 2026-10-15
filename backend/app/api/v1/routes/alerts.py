from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.domain import Alert, AlertEvent, User
from app.schemas.domain import AlertRead, AlertUpdate
from app.schemas.planning import AlertEvaluateRequest
from app.services.planning import AlertService
from app.services.data_scope import real_data_center_ids

router = APIRouter()


@router.get("", response_model=list[AlertRead])
def list_alerts(
    data_center_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Alert)
    if data_center_id is not None:
        stmt = stmt.where(Alert.data_center_id == data_center_id)
    else:
        ids = real_data_center_ids(db)
        stmt = stmt.where(Alert.data_center_id.in_(ids)) if ids else stmt.where(Alert.id == -1)
    return list(db.scalars(stmt.order_by(Alert.triggered_at.desc()).limit(200)))


@router.post("/evaluate", response_model=list[AlertRead])
def evaluate(
    payload: AlertEvaluateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Infrastructure Planner", "Analyst")),
):
    return AlertService.evaluate(db, payload.data_center_id)


@router.get("/{alert_id}", response_model=AlertRead)
def get_alert(alert_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise NotFoundError("Alert not found")
    return alert


def _change_status(db: Session, alert: Alert, new_status: str, actor_id: int) -> Alert:
    old = alert.status
    alert.status = new_status
    if new_status == "resolved":
        alert.resolved_at = datetime.now(timezone.utc)
    elif old == "resolved":
        alert.resolved_at = None
    db.add(AlertEvent(
        alert_id=alert.id,
        event_type="status_changed",
        actor_user_id=actor_id,
        metadata_json={"old": old, "new": new_status},
    ))
    db.commit()
    db.refresh(alert)
    return alert


@router.patch("/{alert_id}", response_model=AlertRead)
def update_alert(
    alert_id: int,
    payload: AlertUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Admin", "Infrastructure Planner")),
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise NotFoundError("Alert not found")
    return _change_status(db, alert, payload.status, user.id)


@router.post("/{alert_id}/resolve", response_model=AlertRead)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Admin", "Infrastructure Planner")),
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise NotFoundError("Alert not found")
    return _change_status(db, alert, "resolved", user.id)
