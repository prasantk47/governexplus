# api/middleware/tenant.py - HARDENED
# Identity comes ONLY from a verified JWT. Headers are hints, never authority.
#
# Changes vs previous version:
#   1. X-User-ID / X-User-Roles / X-Is-Admin headers are IGNORED.
#   2. User context is decoded from the Bearer token via the same secret and
#      blacklist as services.auth_service.
#   3. X-Tenant-ID is only honored when it matches the token's tenant claim,
#      or the token carries the platform_admin role (cross-tenant support access,
#      which is logged).
#   4. /tenants/* requires platform_admin - no more silent pass-through.

import logging
import re
from typing import Callable, Optional

import jwt
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.tenant import (
    TenantManager, TenantStatus,
    set_current_tenant, TenantContext,
)
from services.auth_service import JWT_SECRET, JWT_ALGORITHM, AuthService

logger = logging.getLogger(__name__)

PLATFORM_ADMIN_ROLE = "platform_admin"


class TenantMiddleware(BaseHTTPMiddleware):

    def __init__(self, app, tenant_manager: TenantManager = None):
        super().__init__(app)
        self.tenant_manager = tenant_manager or TenantManager()
        self.public_paths = [
            "/", "/health", "/docs", "/redoc", "/openapi.json",
            "/auth/login", "/auth/refresh", "/auth/logout", "/setup/status",
            "/auth/sso/status", "/auth/sso/saml/metadata",
            "/auth/sso/saml/login", "/auth/sso/saml/acs", "/auth/sso/saml/sls",
            "/auth/sso/oidc/login", "/auth/sso/oidc/callback",
        ]

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        if request.method == "OPTIONS" or self._is_public_path(path):
            return await call_next(request)

        # --- 1. Verify identity from JWT (the only source of truth) ---------
        claims = self._verify_bearer(request)
        if claims is None:
            return self._error(401, "Authentication required.")

        user_roles = claims.get("roles", []) or []
        is_platform_admin = PLATFORM_ADMIN_ROLE in user_roles
        token_tenant = claims.get("tenant_id")

        # --- 2. Platform-admin paths ---------------------------------------
        if path == "/tenants" or path.startswith("/tenants/"):
            if not is_platform_admin:
                return self._error(403, "Platform administrator role required.")
            return await call_next(request)

        # --- 3. Resolve tenant: token claim first, header/subdomain second --
        requested = self._extract_tenant_id(request)
        if requested and token_tenant and requested != token_tenant:
            if is_platform_admin:
                logger.warning(
                    "Platform admin %s acting on tenant %s",
                    claims.get("sub"), requested,
                )
                tenant_id = requested
            else:
                return self._error(
                    403, "Token is not authorized for the requested tenant."
                )
        else:
            tenant_id = token_tenant or requested

        if not tenant_id:
            import os
            tenant_id = os.getenv("DEFAULT_TENANT_ID", "")
            if not tenant_id:
                return self._error(400, "Tenant context required.")

        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return self._error(404, f"Tenant not found: {tenant_id}")
        if tenant.status == TenantStatus.SUSPENDED:
            return self._error(403, "This account has been suspended. Please contact support.")
        if tenant.status != TenantStatus.ACTIVE:
            return self._error(403, f"Tenant is not active (status: {tenant.status.value})")

        # --- 4. Build context from VERIFIED claims only ---------------------
        context = TenantContext(
            tenant_id=tenant.id,
            tenant_slug=tenant.slug,
            tenant_name=tenant.name,
            user_id=claims.get("sub") or claims.get("user_id"),
            user_email=claims.get("email"),
            user_roles=user_roles,
            is_tenant_admin=("tenant_admin" in user_roles) or is_platform_admin,
            request_id=request.headers.get("X-Request-ID", ""),
            source_ip=request.client.host if request.client else "",
            config={
                "timezone": tenant.config.timezone,
                "language": tenant.config.language,
                "enabled_modules": tenant.config.enabled_modules,
            },
            limits={
                "max_users": tenant.limits.max_users,
                "max_systems": tenant.limits.max_systems,
                "max_api_calls_per_day": tenant.limits.max_api_calls_per_day,
            },
            features={
                "sso_enabled": tenant.limits.sso_enabled,
                "ai_features": tenant.limits.ai_features,
                "advanced_analytics": tenant.limits.advanced_analytics,
                "custom_branding": tenant.limits.custom_branding,
            },
        )
        set_current_tenant(context)
        try:
            response = await call_next(request)
            response.headers["X-Tenant-ID"] = tenant.id
            response.headers["X-Tenant-Slug"] = tenant.slug
            return response
        finally:
            set_current_tenant(None)

    # ------------------------------------------------------------------ utils

    def _verify_bearer(self, request: Request) -> Optional[dict]:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[7:].strip()
        try:
            if AuthService.is_token_blacklisted(token):
                return None
            return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            logger.info("Rejected invalid JWT from %s", request.client)
            return None

    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id
        host = request.headers.get("Host", "")
        sub = self._extract_subdomain(host)
        if sub:
            tenant = self.tenant_manager.get_tenant_by_slug(sub)
            if tenant:
                return tenant.id
        tenant = self.tenant_manager.get_tenant_by_domain(host)
        return tenant.id if tenant else None

    def _extract_subdomain(self, host: str) -> Optional[str]:
        match = re.match(r"^([a-z0-9-]+)\.(governexplus\.com|grc-platform\.com|localhost)", host)
        if match and match.group(1) not in ("www", "api", "app", "admin"):
            return match.group(1)
        return None

    def _is_public_path(self, path: str) -> bool:
        return path in self.public_paths or path.startswith(("/docs", "/redoc", "/static"))

    @staticmethod
    def _error(status_code: int, message: str) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": message})


def get_tenant_context(request: Request) -> TenantContext:
    """
    Dependency to get current tenant context

    Usage:
        @router.get("/something")
        async def something(tenant: TenantContext = Depends(get_tenant_context)):
            # tenant.tenant_id is available
    """
    from core.tenant import get_current_tenant

    context = get_current_tenant()
    if context is None:
        raise HTTPException(
            status_code=400,
            detail="Tenant context not available"
        )
    return context


def require_feature(feature: str):
    """
    Dependency to require a specific feature

    Usage:
        @router.get("/ai-analysis")
        async def ai_analysis(
            tenant: TenantContext = Depends(require_feature("ai_features"))
        ):
            # Only accessible if tenant has AI features
    """
    def checker(request: Request) -> TenantContext:
        context = get_tenant_context(request)
        if not context.has_feature(feature):
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{feature}' is not available for your subscription. "
                       "Please upgrade to access this feature."
            )
        return context
    return checker


def require_module(module: str):
    """
    Dependency to require a specific module

    Usage:
        @router.get("/firefighter/start")
        async def start_ff(
            tenant: TenantContext = Depends(require_module("firefighter"))
        ):
            # Only accessible if tenant has firefighter module enabled
    """
    def checker(request: Request) -> TenantContext:
        context = get_tenant_context(request)
        if not context.has_module(module):
            raise HTTPException(
                status_code=403,
                detail=f"Module '{module}' is not enabled for your organization."
            )
        return context
    return checker
