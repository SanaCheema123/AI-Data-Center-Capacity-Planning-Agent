from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import TokenError, decode_token
from app.db.session import get_db
from app.models.domain import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if credentials is None:
        raise AuthenticationError("Authentication required")
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = int(payload["sub"])
    except (TokenError, ValueError, KeyError):
        raise AuthenticationError("Invalid or expired authentication token")
    user = db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    if not user:
        raise AuthenticationError("Authentication user no longer exists")
    if not user.is_active:
        raise PermissionDeniedError("User account is inactive")
    return user


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        role_names = {role.name for role in user.roles}
        if not role_names.intersection(allowed_roles):
            raise PermissionDeniedError()
        return user
    return dependency
