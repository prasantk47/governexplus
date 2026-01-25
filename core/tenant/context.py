# Tenant Context Management
# Thread-safe tenant context for request handling

from dataclasses import dataclass, field
from typing import Optional, Any, Dict
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
import threading


# Context variable for current tenant (async-safe)
_current_tenant: ContextVar[Optional['TenantContext']] = ContextVar(
    'current_tenant', default=None
)


@dataclass
class TenantContext:
    """
    Tenant context for the current request

    This object is attached to each request and provides:
    - Tenant identification
    - User identification within tenant
    - Permission context
    - Request metadata
    """
    tenant_id: str
    tenant_slug: str
    tenant_name: str

    # User context
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_roles: list = field(default_factory=list)

    # Permissions
    is_tenant_admin: bool = False
    is_super_admin: bool = False  # Platform admin

    # Request metadata
    request_id: str = ""
    request_timestamp: datetime = field(default_factory=datetime.utcnow)
    source_ip: str = ""

    # Tenant configuration (cached)
    config: Dict[str, Any] = field(default_factory=dict)
    limits: Dict[str, Any] = field(default_factory=dict)
    features: Dict[str, bool] = field(default_factory=dict)

    def has_feature(self, feature: str) -> bool:
        """Check if tenant has a specific feature enabled"""
        return self.features.get(feature, False)

    def has_module(self, module: str) -> bool:
        """Check if tenant has a module enabled"""
        enabled_modules = self.config.get("enabled_modules", [])
        return module in enabled_modules

    def can_access(self, resource: str, action: str = "read") -> bool:
        """Check if current user can access a resource"""
        if self.is_super_admin:
            return True
        if self.is_tenant_admin:
            return True

        # Would check against RBAC here
        return True  # Default allow for demo


def get_current_tenant() -> Optional[TenantContext]:
    """Get the current tenant context"""
    return _current_tenant.get()


def set_current_tenant(context: Optional[TenantContext]) -> None:
    """Set the current tenant context"""
    _current_tenant.set(context)


class tenant_context:
    """
    Context manager for tenant operations

    Usage:
        with tenant_context(tenant_id="tenant_123"):
            # All operations here are scoped to this tenant
            users = get_users()  # Returns only this tenant's users
    """

    def __init__(
        self,
        tenant_id: str,
        tenant_slug: str = "",
        tenant_name: str = "",
        user_id: str = None,
        **kwargs
    ):
        self.context = TenantContext(
            tenant_id=tenant_id,
            tenant_slug=tenant_slug or tenant_id,
            tenant_name=tenant_name or tenant_id,
            user_id=user_id,
            **kwargs
        )
        self.previous_context = None

    def __enter__(self) -> TenantContext:
        self.previous_context = get_current_tenant()
        set_current_tenant(self.context)
        return self.context

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_current_tenant(self.previous_context)
        return False


def require_tenant(func):
    """
    Decorator that requires a tenant context

    Raises TenantRequiredError if no tenant context is set.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        ctx = get_current_tenant()
        if ctx is None:
            raise TenantRequiredError(
                "This operation requires a tenant context. "
                "Ensure the request has a valid tenant identifier."
            )
        return func(*args, **kwargs)
    return wrapper


def require_feature(feature: str):
    """
    Decorator that requires a specific feature

    Usage:
        @require_feature("ai_features")
        def analyze_with_ai():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ctx = get_current_tenant()
            if ctx is None:
                raise TenantRequiredError("Tenant context required")
            if not ctx.has_feature(feature):
                raise FeatureNotAvailableError(
                    f"Feature '{feature}' is not available for your subscription tier. "
                    "Please upgrade to access this feature."
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_module(module: str):
    """
    Decorator that requires a specific module

    Usage:
        @require_module("firefighter")
        def start_firefighter_session():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ctx = get_current_tenant()
            if ctx is None:
                raise TenantRequiredError("Tenant context required")
            if not ctx.has_module(module):
                raise ModuleNotEnabledError(
                    f"Module '{module}' is not enabled for your organization. "
                    "Contact your administrator to enable this module."
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


class TenantRequiredError(Exception):
    """Raised when tenant context is required but not present"""
    pass


class FeatureNotAvailableError(Exception):
    """Raised when a feature is not available for the tenant's tier"""
    pass


class ModuleNotEnabledError(Exception):
    """Raised when a module is not enabled for the tenant"""
    pass


class TenantSuspendedError(Exception):
    """Raised when trying to access a suspended tenant"""
    pass


# ==================== Request Middleware Helper ====================

def create_tenant_context_from_request(
    tenant_id: str,
    tenant_data: Dict[str, Any],
    user_data: Dict[str, Any] = None,
    request_id: str = "",
    source_ip: str = ""
) -> TenantContext:
    """
    Create tenant context from request data

    Called by middleware to establish context for each request.
    """
    user_data = user_data or {}

    return TenantContext(
        tenant_id=tenant_id,
        tenant_slug=tenant_data.get("slug", tenant_id),
        tenant_name=tenant_data.get("name", ""),
        user_id=user_data.get("user_id"),
        user_email=user_data.get("email"),
        user_roles=user_data.get("roles", []),
        is_tenant_admin=user_data.get("is_admin", False),
        is_super_admin=user_data.get("is_super_admin", False),
        request_id=request_id,
        source_ip=source_ip,
        config=tenant_data.get("config", {}),
        limits=tenant_data.get("limits", {}),
        features={
            "sso_enabled": tenant_data.get("limits", {}).get("sso_enabled", False),
            "ai_features": tenant_data.get("limits", {}).get("ai_features", False),
            "advanced_analytics": tenant_data.get("limits", {}).get("advanced_analytics", False),
            "custom_branding": tenant_data.get("limits", {}).get("custom_branding", False),
        }
    )


# ==================== Tenant-Scoped Operations ====================

class TenantScoped:
    """
    Base class for tenant-scoped services

    Ensures all operations are automatically scoped to current tenant.
    """

    @property
    def tenant_id(self) -> str:
        """Get current tenant ID"""
        ctx = get_current_tenant()
        if ctx is None:
            raise TenantRequiredError("No tenant context")
        return ctx.tenant_id

    @property
    def tenant_context(self) -> TenantContext:
        """Get current tenant context"""
        ctx = get_current_tenant()
        if ctx is None:
            raise TenantRequiredError("No tenant context")
        return ctx

    def _scope_query(self, query: str) -> str:
        """Add tenant scope to a database query"""
        # Would modify query to include tenant_id filter
        return query

    def _scope_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add tenant ID to data being saved"""
        data["tenant_id"] = self.tenant_id
        return data
