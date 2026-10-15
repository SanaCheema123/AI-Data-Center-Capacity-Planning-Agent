from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, require_roles
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.domain import NotificationSetting, User, UserPreference
from app.models.system_setting import SystemSetting
from app.schemas.domain import SettingRead, SettingUpdate
from app.schemas.planning import NotificationSettingsRead, NotificationSettingsUpdate, AppearanceSettingsRead, AppearanceSettingsUpdate

router = APIRouter()

@router.get("", response_model=list[SettingRead])
def list_settings(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(SystemSetting).order_by(SystemSetting.key)))

@router.patch("/{key}", response_model=SettingRead)
def update_setting(key: str, payload: SettingUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles("Admin", "Infrastructure Planner"))):
    setting = db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if not setting:
        raise NotFoundError("Setting not found")
    setting.value = payload.value
    db.commit(); db.refresh(setting)
    return setting

@router.get("/notifications/me", response_model=NotificationSettingsRead)
def get_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.scalar(select(NotificationSetting).where(NotificationSetting.user_id == user.id))
    if not obj:
        obj = NotificationSetting(user_id=user.id)
        db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.patch("/notifications/me", response_model=NotificationSettingsRead)
def update_notifications(payload: NotificationSettingsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.scalar(select(NotificationSetting).where(NotificationSetting.user_id == user.id))
    if not obj:
        obj = NotificationSetting(user_id=user.id); db.add(obj); db.flush()
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit(); db.refresh(obj); return obj


@router.get("/appearance/me", response_model=AppearanceSettingsRead)
def get_appearance(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    if not obj:
        obj = UserPreference(user_id=user.id)
        db.add(obj); db.commit(); db.refresh(obj)
    return obj


@router.patch("/appearance/me", response_model=AppearanceSettingsRead)
def update_appearance(payload: AppearanceSettingsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    if not obj:
        obj = UserPreference(user_id=user.id); db.add(obj); db.flush()
    data = payload.model_dump(exclude_unset=True)
    if "theme" in data and data["theme"] not in {"light", "dark", "system"}:
        raise ValueError("Unsupported theme")
    if "accent" in data and data["accent"] not in {"olive", "lavender", "blue", "purple", "pink"}:
        raise ValueError("Unsupported accent")
    for key, value in data.items(): setattr(obj, key, value)
    db.commit(); db.refresh(obj); return obj
