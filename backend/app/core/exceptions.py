from typing import Any


class AppError(Exception):
    def __init__(self, message: str, *, code: str = "APPLICATION_ERROR", status_code: int = 400, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication required", **kwargs: Any):
        super().__init__(message, code="UNAUTHORIZED", status_code=401, **kwargs)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", **kwargs: Any):
        super().__init__(message, code="NOT_FOUND", status_code=404, **kwargs)


class ConflictError(AppError):
    def __init__(self, message: str = "Resource already exists", **kwargs: Any):
        super().__init__(message, code="CONFLICT", status_code=409, **kwargs)


class PermissionDeniedError(AppError):
    def __init__(self, message: str = "Insufficient permissions", **kwargs: Any):
        super().__init__(message, code="FORBIDDEN", status_code=403, **kwargs)
