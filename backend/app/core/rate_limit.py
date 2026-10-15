"""Small production rate limiter for abuse-prone endpoints.

Redis is used when the optional runtime dependency is available. A process-local
fixed-window fallback keeps the API protected if Redis is temporarily unavailable;
the fallback is intentionally conservative and only enabled in production.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from hashlib import sha256
from typing import Deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)

try:  # installed by celery[redis] in the production image
    import redis.asyncio as redis_async  # type: ignore
except Exception:  # pragma: no cover - exercised in constrained test envs
    redis_async = None


@dataclass(frozen=True)
class RateRule:
    limit: int
    window_seconds: int


_RULES: dict[tuple[str, str], RateRule] = {
    ("POST", f"{settings.api_v1_prefix}/auth/login"): RateRule(20, 60),
    ("POST", f"{settings.api_v1_prefix}/auth/register"): RateRule(8, 300),
    ("POST", f"{settings.api_v1_prefix}/auth/refresh"): RateRule(60, 60),
    ("POST", f"{settings.api_v1_prefix}/ai/chat"): RateRule(30, 60),
    ("POST", f"{settings.api_v1_prefix}/ai/workflow"): RateRule(30, 60),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._memory: dict[str, Deque[float]] = defaultdict(deque)
        self._redis = None
        if settings.app_env.lower() == "production" and redis_async is not None:
            try:
                self._redis = redis_async.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
            except Exception:
                logger.exception("rate_limit_redis_initialization_failed")

    @staticmethod
    def _identity(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        host = forwarded or (request.client.host if request.client else "unknown")
        # Do not retain raw client IPs in limiter keys/logs.
        return sha256(host.encode("utf-8")).hexdigest()[:24]

    async def _redis_allowed(self, key: str, rule: RateRule) -> tuple[bool, int]:
        assert self._redis is not None
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, rule.window_seconds)
        ttl = max(await self._redis.ttl(key), 1)
        return count <= rule.limit, ttl

    def _memory_allowed(self, key: str, rule: RateRule) -> tuple[bool, int]:
        now = time.monotonic()
        bucket = self._memory[key]
        cutoff = now - rule.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= rule.limit:
            retry = max(1, int(rule.window_seconds - (now - bucket[0])))
            return False, retry
        bucket.append(now)
        return True, rule.window_seconds

    async def dispatch(self, request: Request, call_next):
        if settings.app_env.lower() != "production":
            return await call_next(request)
        rule = _RULES.get((request.method.upper(), request.url.path))
        if rule is None:
            return await call_next(request)

        identity = self._identity(request)
        window = int(time.time() // rule.window_seconds)
        key = f"capacity:rate:{request.method}:{request.url.path}:{identity}:{window}"
        try:
            if self._redis is not None:
                allowed, retry_after = await self._redis_allowed(key, rule)
            else:
                allowed, retry_after = self._memory_allowed(key, rule)
        except Exception:
            logger.warning("rate_limit_redis_unavailable_using_local_fallback", exc_info=True)
            allowed, retry_after = self._memory_allowed(key, rule)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMITED", "message": "Too many requests", "details": {} }},
                headers={"Retry-After": str(retry_after)},
            )
        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(rule.limit))
        return response
