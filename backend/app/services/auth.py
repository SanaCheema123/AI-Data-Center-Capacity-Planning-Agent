from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password, TokenError
from app.models.domain import Role, User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserRead
from app.core.config import settings

DEFAULT_ROLE = "Viewer"


class AuthService:
    @staticmethod
    def register(db: Session, data: UserCreate) -> User:
        if db.scalar(select(User).where(User.email == data.email.lower())):
            raise ConflictError("Email is already registered")
        if not settings.allow_public_registration:
            raise AppError("Public registration is disabled", code="REGISTRATION_DISABLED", status_code=403)
        user_count = db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None))) or 0
        role_name = "Admin" if user_count == 0 and settings.bootstrap_first_user_as_admin else DEFAULT_ROLE
        role = db.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            descriptions = {"Admin": "Full administrative access", "Viewer": "Read-only access"}
            role = Role(name=role_name, description=descriptions.get(role_name, role_name))
            db.add(role)
            db.flush()
        user = User(email=data.email.lower(), full_name=data.full_name, password_hash=hash_password(data.password), roles=[role])
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate(db: Session, data: LoginRequest) -> User:
        user = db.scalar(select(User).where(User.email == data.email.lower(), User.deleted_at.is_(None)))
        if not user or not verify_password(data.password, user.password_hash) or not user.is_active:
            raise AppError("Invalid email or password", code="INVALID_CREDENTIALS", status_code=401)
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def tokens_for(user: User) -> TokenResponse:
        claims = {"roles": [role.name for role in user.roles]}
        return TokenResponse(
            access_token=create_access_token(str(user.id), claims),
            refresh_token=create_refresh_token(str(user.id), claims),
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserRead.model_validate(user),
        )

    @staticmethod
    def refresh(db: Session, token: str) -> TokenResponse:
        try:
            payload = decode_token(token, expected_type="refresh")
        except TokenError as exc:
            raise AppError(str(exc), code="INVALID_REFRESH_TOKEN", status_code=401) from exc
        user = db.scalar(select(User).where(User.id == int(payload["sub"]), User.deleted_at.is_(None)))
        if not user or not user.is_active:
            raise AppError("User is inactive or does not exist", code="INVALID_REFRESH_TOKEN", status_code=401)
        return AuthService.tokens_for(user)
