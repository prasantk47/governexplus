"""
Rate Limiting Middleware

Provides request rate limiting using slowapi (wraps the 'limits' library).
Configurable per-endpoint and global limits via environment variables.

Environment variables:
    RATE_LIMIT_DEFAULT: Default rate limit (e.g., "60/minute"). Default: "60/minute"
    RATE_LIMIT_AUTH: Rate limit for auth endpoints. Default: "10/minute"
    RATE_LIMIT_STORAGE: Backend for rate limit counters. Default: "memory://"
        Production: use "redis://localhost:6379" for distributed deployments
"""

import os
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# Configuration
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "10/minute")
RATE_LIMIT_STORAGE = os.getenv("RATE_LIMIT_STORAGE", "memory://")


def _key_func(request: Request) -> str:
    """Extract client identifier for rate limiting.

    Uses X-Forwarded-For header if behind a proxy, otherwise remote address.
    Includes tenant ID for multi-tenant isolation.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else get_remote_address(request)
    tenant_id = request.headers.get("X-Tenant-ID", "default")
    return f"{tenant_id}:{client_ip}"


# Create the limiter instance
limiter = Limiter(
    key_func=_key_func,
    default_limits=[RATE_LIMIT_DEFAULT],
    storage_uri=RATE_LIMIT_STORAGE,
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors."""
    retry_after = exc.detail.split("per")[-1].strip() if exc.detail else "unknown"
    logger.warning(
        "Rate limit exceeded",
        extra={"client": _key_func(request), "path": request.url.path},
    )
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": f"Too many requests. Try again later.",
            "retry_after": retry_after,
        },
        headers={"Retry-After": "60"},
    )


def setup_rate_limiting(app: FastAPI) -> Limiter:
    """Attach rate limiting to a FastAPI application.

    Usage in main.py:
        from api.middleware.rate_limit import setup_rate_limiting, limiter
        setup_rate_limiting(app)

    Then in routers, use the limiter decorator:
        from api.middleware.rate_limit import limiter, RATE_LIMIT_AUTH

        @router.post("/login")
        @limiter.limit(RATE_LIMIT_AUTH)
        async def login(request: Request, ...):
            ...
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    logger.info(f"Rate limiting enabled: default={RATE_LIMIT_DEFAULT}, auth={RATE_LIMIT_AUTH}")
    return limiter
