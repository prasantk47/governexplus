# API Middleware
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .tenant import TenantMiddleware, get_tenant_context, require_feature, require_module
from .rate_limit import setup_rate_limiting, limiter

_HTTPS_ENABLED = os.getenv("HTTPS_ENABLED", "false").lower() in ("1", "true", "yes")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security-related HTTP response headers to every response.

    Headers applied:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security (only when HTTPS_ENABLED=true)
    - Content-Security-Policy
    - Referrer-Policy
    - Permissions-Policy
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        if _HTTPS_ENABLED:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


__all__ = [
    "TenantMiddleware",
    "get_tenant_context",
    "require_feature",
    "require_module",
    "setup_rate_limiting",
    "limiter",
    "SecurityHeadersMiddleware",
]
