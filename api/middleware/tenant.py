# Tenant Middleware
# Extracts and validates tenant context for every request

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Callable
import re

from core.tenant import (
    TenantManager, TenantStatus,
    set_current_tenant, TenantContext,
    create_tenant_context_from_request
)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Multi-Tenant Middleware

    Extracts tenant context from request and makes it available
    throughout the request lifecycle.

    Tenant identification methods (in order of priority):
    1. X-Tenant-ID header (for API clients)
    2. Subdomain (tenant.grc-platform.com)
    3. Custom domain mapping
    4. Default tenant (for public endpoints)

    Features:
    - Automatic tenant context injection
    - Tenant status validation (active, suspended, etc.)
    - Rate limiting per tenant
    - Usage tracking per tenant
    """

    def __init__(self, app, tenant_manager: TenantManager = None):
        super().__init__(app)
        self.tenant_manager = tenant_manager or TenantManager()

        # Paths that don't require tenant context
        # In production, reduce this list and require tenant for most paths
        self.public_paths = [
            "/",
            "/health",
            "/info",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth",
            "/tenants/signup",
            "/tenants/verify-email",
            "/tenants/onboarding",
            "/tenants/tiers",
            "/tenants/plans",
            "/tenants/info",
            "/demo",
            # Development/Demo paths - allow without tenant for now
            "/dashboard",
            "/security-controls",
            "/provisioning",
            "/access-requests",
            "/users",
            "/roles",
            "/risk",
            "/compliance",
            "/certification",
            "/reports",
            "/audit",
            "/settings",
            "/ai",
            "/ml",
            "/siem",
            "/pts",
            "/firefighter",
            "/admin",
            "/mobile",
            "/workflows",
            "/notifications",
            "/setup",
            "/sod-rules",
            "/jml",
            "/policy",
            "/mitigation",
            "/cross-system",
            "/integrations",
            "/user-profiles",
            "/reporting",
            "/role-engineering",
            "/approvals",
        ]

        # Admin-only paths (require platform admin, not tenant)
        self.admin_paths = [
            "/tenants",  # Tenant management
        ]

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with tenant context"""
        path = request.url.path
        method = request.method

        # Always allow OPTIONS requests for CORS preflight
        if method == "OPTIONS":
            return await call_next(request)

        # Check if public path
        if self._is_public_path(path):
            return await call_next(request)

        # Extract tenant identifier
        tenant_id = self._extract_tenant_id(request)

        if not tenant_id:
            # Check if admin path
            if self._is_admin_path(path):
                # Would validate admin authentication here
                return await call_next(request)

            # No tenant context required for some operations
            if path.startswith("/tenants/"):
                return await call_next(request)

            return self._error_response(
                status_code=400,
                message="Tenant identification required. "
                       "Provide X-Tenant-ID header or use subdomain."
            )

        # Get tenant
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return self._error_response(
                status_code=404,
                message=f"Tenant not found: {tenant_id}"
            )

        # Validate tenant status
        if tenant.status == TenantStatus.SUSPENDED:
            return self._error_response(
                status_code=403,
                message="This account has been suspended. "
                       "Please contact support."
            )

        if tenant.status == TenantStatus.DEACTIVATED:
            return self._error_response(
                status_code=403,
                message="This account has been deactivated."
            )

        if tenant.status != TenantStatus.ACTIVE:
            return self._error_response(
                status_code=403,
                message=f"Tenant is not active (status: {tenant.status.value})"
            )

        # Extract user context from JWT (simplified)
        user_data = self._extract_user_context(request)

        # Create and set tenant context
        context = TenantContext(
            tenant_id=tenant.id,
            tenant_slug=tenant.slug,
            tenant_name=tenant.name,
            user_id=user_data.get("user_id"),
            user_email=user_data.get("email"),
            user_roles=user_data.get("roles", []),
            is_tenant_admin=user_data.get("is_admin", False),
            request_id=request.headers.get("X-Request-ID", ""),
            source_ip=request.client.host if request.client else "",
            config={
                "timezone": tenant.config.timezone,
                "language": tenant.config.language,
                "enabled_modules": tenant.config.enabled_modules
            },
            limits={
                "max_users": tenant.limits.max_users,
                "max_systems": tenant.limits.max_systems,
                "max_api_calls_per_day": tenant.limits.max_api_calls_per_day
            },
            features={
                "sso_enabled": tenant.limits.sso_enabled,
                "ai_features": tenant.limits.ai_features,
                "advanced_analytics": tenant.limits.advanced_analytics,
                "custom_branding": tenant.limits.custom_branding
            }
        )

        # Set context for this request
        set_current_tenant(context)

        # Track API usage (would be async in production)
        # billing.track_api_call(tenant_id)

        try:
            # Process request
            response = await call_next(request)

            # Add tenant info to response headers
            response.headers["X-Tenant-ID"] = tenant_id
            response.headers["X-Tenant-Slug"] = tenant.slug

            return response

        finally:
            # Clear context after request
            set_current_tenant(None)

    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request"""
        # Method 1: Header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id

        # Method 2: Subdomain
        host = request.headers.get("Host", "")
        subdomain = self._extract_subdomain(host)
        if subdomain:
            # Look up tenant by slug
            tenant = self.tenant_manager.get_tenant_by_slug(subdomain)
            if tenant:
                return tenant.id

        # Method 3: Custom domain
        tenant = self.tenant_manager.get_tenant_by_domain(host)
        if tenant:
            return tenant.id

        return None

    def _extract_subdomain(self, host: str) -> Optional[str]:
        """Extract subdomain from host"""
        # Match: tenant.grc-platform.com or tenant.localhost
        match = re.match(r'^([a-z0-9-]+)\.(grc-platform\.com|localhost)', host)
        if match:
            subdomain = match.group(1)
            # Exclude common non-tenant subdomains
            if subdomain not in ['www', 'api', 'app', 'admin']:
                return subdomain
        return None

    def _extract_user_context(self, request: Request) -> dict:
        """Extract user context from authentication"""
        # Would decode JWT token here
        # For demo, extract from headers
        return {
            "user_id": request.headers.get("X-User-ID"),
            "email": request.headers.get("X-User-Email"),
            "roles": request.headers.get("X-User-Roles", "").split(","),
            "is_admin": request.headers.get("X-Is-Admin", "false").lower() == "true"
        }

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public"""
        for public_path in self.public_paths:
            if path == public_path or path.startswith(f"{public_path}/"):
                return True
        return False

    def _is_admin_path(self, path: str) -> bool:
        """Check if path requires admin access"""
        for admin_path in self.admin_paths:
            if path == admin_path or path.startswith(f"{admin_path}/"):
                return True
        return False

    def _error_response(self, status_code: int, message: str):
        """Create error response with CORS headers"""
        from fastapi.responses import JSONResponse
        response = JSONResponse(
            status_code=status_code,
            content={"error": message}
        )
        # Add CORS headers to error responses
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response


def get_tenant_context(request: Request) -> TenantContext:
    """
    Dependency to get current tenant context

    Usage:
        @router.get("/something")
        async def something(tenant: TenantContext = Depends(get_tenant_context)):
            # tenant.tenant_id is available
    """
    from core.tenant import get_current_tenant, TenantRequiredError

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
