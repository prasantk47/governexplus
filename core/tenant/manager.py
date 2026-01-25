# Tenant Manager
# Core multi-tenant management for SaaS

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
import uuid
import hashlib


class TenantStatus(Enum):
    """Tenant lifecycle status"""
    PENDING = "pending"           # Just created, awaiting setup
    PROVISIONING = "provisioning" # Resources being provisioned
    ACTIVE = "active"             # Fully operational
    SUSPENDED = "suspended"       # Temporarily disabled (billing, etc.)
    DEACTIVATED = "deactivated"   # Marked for deletion
    DELETED = "deleted"           # Soft deleted


class TenantTier(Enum):
    """Subscription tiers"""
    FREE = "free"                 # Free tier with limits
    STARTER = "starter"           # Small teams
    PROFESSIONAL = "professional" # Medium businesses
    ENTERPRISE = "enterprise"     # Large enterprises
    DEDICATED = "dedicated"       # Dedicated infrastructure


@dataclass
class TenantLimits:
    """Resource limits per tier"""
    max_users: int = 10
    max_systems: int = 1
    max_roles: int = 100
    max_rules: int = 50
    max_requests_per_month: int = 1000
    max_storage_gb: float = 1.0
    max_api_calls_per_day: int = 10000
    retention_days: int = 90

    # Feature flags
    sso_enabled: bool = False
    custom_branding: bool = False
    advanced_analytics: bool = False
    ai_features: bool = False
    dedicated_support: bool = False
    sla_guarantee: bool = False
    custom_integrations: bool = False
    audit_export: bool = False


@dataclass
class TenantConfig:
    """Tenant-specific configuration"""
    # Branding
    company_name: str = ""
    logo_url: str = ""
    primary_color: str = "#1976D2"
    custom_domain: str = ""

    # Localization
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    language: str = "en"
    currency: str = "USD"

    # Security
    password_policy: Dict[str, Any] = field(default_factory=lambda: {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_numbers": True,
        "require_special": False,
        "max_age_days": 90
    })
    session_timeout_minutes: int = 30
    mfa_required: bool = False
    ip_whitelist: List[str] = field(default_factory=list)

    # Features
    enabled_modules: List[str] = field(default_factory=lambda: [
        "risk_analysis", "access_requests", "firefighter",
        "certification", "audit"
    ])

    # Notifications
    email_notifications: bool = True
    webhook_url: str = ""

    # Data
    data_region: str = "us-east-1"  # For data residency


@dataclass
class Tenant:
    """Tenant entity"""
    id: str = ""
    name: str = ""
    slug: str = ""  # URL-friendly identifier
    status: TenantStatus = TenantStatus.PENDING
    tier: TenantTier = TenantTier.FREE

    # Ownership
    owner_email: str = ""
    owner_user_id: str = ""

    # Configuration
    config: TenantConfig = field(default_factory=TenantConfig)
    limits: TenantLimits = field(default_factory=TenantLimits)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    activated_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None

    # Billing
    billing_email: str = ""
    stripe_customer_id: str = ""
    subscription_id: str = ""

    # Usage tracking
    current_users: int = 0
    current_systems: int = 0
    current_storage_gb: float = 0.0

    # Technical
    database_name: str = ""  # Isolated database/schema
    storage_bucket: str = ""  # Isolated storage
    encryption_key_id: str = ""  # Tenant-specific encryption

    def __post_init__(self):
        if not self.id:
            self.id = f"tenant_{uuid.uuid4().hex[:12]}"
        if not self.slug and self.name:
            self.slug = self._generate_slug(self.name)
        if not self.database_name:
            self.database_name = f"grc_{self.slug}"
        if not self.storage_bucket:
            self.storage_bucket = f"grc-{self.slug}-data"

    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from name"""
        slug = name.lower()
        slug = ''.join(c if c.isalnum() else '-' for c in slug)
        slug = '-'.join(filter(None, slug.split('-')))
        return slug[:50]

    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    def is_trial(self) -> bool:
        return self.trial_ends_at is not None and \
               self.trial_ends_at > datetime.utcnow()

    def is_within_limits(self, resource: str, current: int) -> bool:
        """Check if usage is within tier limits"""
        limit_map = {
            "users": self.limits.max_users,
            "systems": self.limits.max_systems,
            "roles": self.limits.max_roles,
            "rules": self.limits.max_rules,
        }
        max_val = limit_map.get(resource, float('inf'))
        return current < max_val


class TenantManager:
    """
    Multi-Tenant Manager

    Handles:
    - Tenant lifecycle (create, activate, suspend, delete)
    - Tier management and upgrades
    - Resource limit enforcement
    - Tenant isolation verification
    """

    def __init__(self):
        self.tenants: Dict[str, Tenant] = {}
        self.tenants_by_slug: Dict[str, str] = {}  # slug -> tenant_id
        self.tenants_by_domain: Dict[str, str] = {}  # custom_domain -> tenant_id

        # Tier configurations
        self.tier_limits = self._initialize_tier_limits()

        # Initialize demo tenant
        self._create_demo_tenant()

    def _initialize_tier_limits(self) -> Dict[TenantTier, TenantLimits]:
        """Define limits for each tier"""
        return {
            TenantTier.FREE: TenantLimits(
                max_users=5,
                max_systems=1,
                max_roles=50,
                max_rules=25,
                max_requests_per_month=100,
                max_storage_gb=0.5,
                max_api_calls_per_day=1000,
                retention_days=30,
                sso_enabled=False,
                custom_branding=False,
                advanced_analytics=False,
                ai_features=False,
                dedicated_support=False
            ),
            TenantTier.STARTER: TenantLimits(
                max_users=25,
                max_systems=3,
                max_roles=200,
                max_rules=100,
                max_requests_per_month=1000,
                max_storage_gb=5.0,
                max_api_calls_per_day=10000,
                retention_days=90,
                sso_enabled=False,
                custom_branding=True,
                advanced_analytics=False,
                ai_features=False,
                dedicated_support=False,
                audit_export=True
            ),
            TenantTier.PROFESSIONAL: TenantLimits(
                max_users=100,
                max_systems=10,
                max_roles=1000,
                max_rules=500,
                max_requests_per_month=10000,
                max_storage_gb=50.0,
                max_api_calls_per_day=100000,
                retention_days=365,
                sso_enabled=True,
                custom_branding=True,
                advanced_analytics=True,
                ai_features=True,
                dedicated_support=False,
                sla_guarantee=True,
                audit_export=True
            ),
            TenantTier.ENTERPRISE: TenantLimits(
                max_users=10000,
                max_systems=100,
                max_roles=50000,
                max_rules=10000,
                max_requests_per_month=1000000,
                max_storage_gb=1000.0,
                max_api_calls_per_day=10000000,
                retention_days=2555,  # 7 years
                sso_enabled=True,
                custom_branding=True,
                advanced_analytics=True,
                ai_features=True,
                dedicated_support=True,
                sla_guarantee=True,
                custom_integrations=True,
                audit_export=True
            ),
            TenantTier.DEDICATED: TenantLimits(
                max_users=100000,
                max_systems=1000,
                max_roles=500000,
                max_rules=100000,
                max_requests_per_month=10000000,
                max_storage_gb=10000.0,
                max_api_calls_per_day=100000000,
                retention_days=3650,  # 10 years
                sso_enabled=True,
                custom_branding=True,
                advanced_analytics=True,
                ai_features=True,
                dedicated_support=True,
                sla_guarantee=True,
                custom_integrations=True,
                audit_export=True
            )
        }

    def _create_demo_tenant(self):
        """Create demo tenant for testing"""
        demo = Tenant(
            id="tenant_demo",
            name="Demo Company",
            slug="demo",
            status=TenantStatus.ACTIVE,
            tier=TenantTier.PROFESSIONAL,
            owner_email="admin@demo.com",
            config=TenantConfig(
                company_name="Demo Company Inc.",
                timezone="America/New_York",
                enabled_modules=[
                    "risk_analysis", "access_requests", "firefighter",
                    "certification", "audit", "role_engineering",
                    "compliance", "ai"
                ]
            ),
            limits=self.tier_limits[TenantTier.PROFESSIONAL],
            activated_at=datetime.utcnow()
        )
        self.tenants[demo.id] = demo
        self.tenants_by_slug[demo.slug] = demo.id

    # ==================== Tenant Lifecycle ====================

    def create_tenant(
        self,
        name: str,
        owner_email: str,
        tier: TenantTier = TenantTier.FREE,
        trial_days: int = 14
    ) -> Dict[str, Any]:
        """Create a new tenant"""
        # Validate
        slug = self._generate_unique_slug(name)

        # Create tenant
        tenant = Tenant(
            name=name,
            slug=slug,
            status=TenantStatus.PENDING,
            tier=tier,
            owner_email=owner_email,
            billing_email=owner_email,
            limits=self.tier_limits[tier],
            trial_ends_at=datetime.utcnow() + timedelta(days=trial_days) if trial_days > 0 else None
        )

        # Store
        self.tenants[tenant.id] = tenant
        self.tenants_by_slug[tenant.slug] = tenant.id

        return {
            "success": True,
            "tenant_id": tenant.id,
            "slug": tenant.slug,
            "status": tenant.status.value,
            "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            "message": "Tenant created. Run provisioning to activate."
        }

    def _generate_unique_slug(self, name: str) -> str:
        """Generate unique slug"""
        base_slug = name.lower()
        base_slug = ''.join(c if c.isalnum() else '-' for c in base_slug)
        base_slug = '-'.join(filter(None, base_slug.split('-')))[:50]

        slug = base_slug
        counter = 1
        while slug in self.tenants_by_slug:
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def activate_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Activate a tenant after provisioning"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return {"success": False, "error": "Tenant not found"}

        if tenant.status not in [TenantStatus.PENDING, TenantStatus.PROVISIONING]:
            return {"success": False, "error": f"Cannot activate tenant in {tenant.status.value} status"}

        tenant.status = TenantStatus.ACTIVE
        tenant.activated_at = datetime.utcnow()
        tenant.updated_at = datetime.utcnow()

        return {
            "success": True,
            "tenant_id": tenant_id,
            "status": tenant.status.value,
            "message": "Tenant activated successfully"
        }

    def suspend_tenant(self, tenant_id: str, reason: str = "") -> Dict[str, Any]:
        """Suspend a tenant (e.g., for non-payment)"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return {"success": False, "error": "Tenant not found"}

        tenant.status = TenantStatus.SUSPENDED
        tenant.updated_at = datetime.utcnow()

        return {
            "success": True,
            "tenant_id": tenant_id,
            "status": tenant.status.value,
            "reason": reason,
            "message": "Tenant suspended. Users cannot access the system."
        }

    def reactivate_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Reactivate a suspended tenant"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return {"success": False, "error": "Tenant not found"}

        if tenant.status != TenantStatus.SUSPENDED:
            return {"success": False, "error": "Tenant is not suspended"}

        tenant.status = TenantStatus.ACTIVE
        tenant.updated_at = datetime.utcnow()

        return {
            "success": True,
            "tenant_id": tenant_id,
            "status": tenant.status.value,
            "message": "Tenant reactivated"
        }

    def deactivate_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Mark tenant for deletion (soft delete)"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return {"success": False, "error": "Tenant not found"}

        tenant.status = TenantStatus.DEACTIVATED
        tenant.updated_at = datetime.utcnow()

        return {
            "success": True,
            "tenant_id": tenant_id,
            "status": tenant.status.value,
            "message": "Tenant deactivated. Data will be deleted after retention period."
        }

    # ==================== Tier Management ====================

    def upgrade_tier(self, tenant_id: str, new_tier: TenantTier) -> Dict[str, Any]:
        """Upgrade tenant to a higher tier"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return {"success": False, "error": "Tenant not found"}

        old_tier = tenant.tier
        if list(TenantTier).index(new_tier) <= list(TenantTier).index(old_tier):
            return {"success": False, "error": "Can only upgrade to a higher tier"}

        tenant.tier = new_tier
        tenant.limits = self.tier_limits[new_tier]
        tenant.updated_at = datetime.utcnow()

        # Clear trial if upgrading
        if tenant.trial_ends_at:
            tenant.trial_ends_at = None

        return {
            "success": True,
            "tenant_id": tenant_id,
            "old_tier": old_tier.value,
            "new_tier": new_tier.value,
            "new_limits": {
                "max_users": tenant.limits.max_users,
                "max_systems": tenant.limits.max_systems,
                "ai_features": tenant.limits.ai_features,
                "sso_enabled": tenant.limits.sso_enabled
            },
            "message": f"Upgraded from {old_tier.value} to {new_tier.value}"
        }

    def downgrade_tier(self, tenant_id: str, new_tier: TenantTier) -> Dict[str, Any]:
        """Downgrade tenant (with validation)"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return {"success": False, "error": "Tenant not found"}

        new_limits = self.tier_limits[new_tier]

        # Check if current usage allows downgrade
        violations = []
        if tenant.current_users > new_limits.max_users:
            violations.append(f"Users: {tenant.current_users} > {new_limits.max_users}")
        if tenant.current_systems > new_limits.max_systems:
            violations.append(f"Systems: {tenant.current_systems} > {new_limits.max_systems}")

        if violations:
            return {
                "success": False,
                "error": "Cannot downgrade - usage exceeds new tier limits",
                "violations": violations
            }

        old_tier = tenant.tier
        tenant.tier = new_tier
        tenant.limits = new_limits
        tenant.updated_at = datetime.utcnow()

        return {
            "success": True,
            "tenant_id": tenant_id,
            "old_tier": old_tier.value,
            "new_tier": new_tier.value,
            "message": f"Downgraded from {old_tier.value} to {new_tier.value}"
        }

    # ==================== Resource Management ====================

    def check_limit(self, tenant_id: str, resource: str, requested: int = 1) -> Dict[str, Any]:
        """Check if action is within tenant limits"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return {"allowed": False, "error": "Tenant not found"}

        limit_map = {
            "users": (tenant.current_users, tenant.limits.max_users),
            "systems": (tenant.current_systems, tenant.limits.max_systems),
            "roles": (0, tenant.limits.max_roles),  # Would track actual
            "rules": (0, tenant.limits.max_rules),
        }

        if resource not in limit_map:
            return {"allowed": True, "message": "Resource not limited"}

        current, limit = limit_map[resource]
        new_total = current + requested
        allowed = new_total <= limit

        return {
            "allowed": allowed,
            "resource": resource,
            "current": current,
            "requested": requested,
            "limit": limit,
            "remaining": limit - current,
            "message": "Within limits" if allowed else f"Would exceed {resource} limit"
        }

    def update_usage(
        self,
        tenant_id: str,
        users: int = None,
        systems: int = None,
        storage_gb: float = None
    ) -> Dict[str, Any]:
        """Update tenant resource usage"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return {"success": False, "error": "Tenant not found"}

        if users is not None:
            tenant.current_users = users
        if systems is not None:
            tenant.current_systems = systems
        if storage_gb is not None:
            tenant.current_storage_gb = storage_gb

        tenant.updated_at = datetime.utcnow()

        return {
            "success": True,
            "usage": {
                "users": tenant.current_users,
                "systems": tenant.current_systems,
                "storage_gb": tenant.current_storage_gb
            }
        }

    # ==================== Queries ====================

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID"""
        return self.tenants.get(tenant_id)

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug"""
        tenant_id = self.tenants_by_slug.get(slug)
        return self.tenants.get(tenant_id) if tenant_id else None

    def get_tenant_by_domain(self, domain: str) -> Optional[Tenant]:
        """Get tenant by custom domain"""
        tenant_id = self.tenants_by_domain.get(domain)
        return self.tenants.get(tenant_id) if tenant_id else None

    def list_tenants(
        self,
        status: TenantStatus = None,
        tier: TenantTier = None,
        limit: int = 100
    ) -> List[Tenant]:
        """List tenants with optional filters"""
        tenants = list(self.tenants.values())

        if status:
            tenants = [t for t in tenants if t.status == status]
        if tier:
            tenants = [t for t in tenants if t.tier == tier]

        return tenants[:limit]

    def get_tenant_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Get comprehensive tenant summary"""
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return {"error": "Tenant not found"}

        return {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "status": tenant.status.value,
            "tier": tenant.tier.value,
            "is_trial": tenant.is_trial(),
            "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            "owner_email": tenant.owner_email,
            "usage": {
                "users": {
                    "current": tenant.current_users,
                    "limit": tenant.limits.max_users,
                    "percent": round(tenant.current_users / tenant.limits.max_users * 100, 1)
                },
                "systems": {
                    "current": tenant.current_systems,
                    "limit": tenant.limits.max_systems,
                    "percent": round(tenant.current_systems / tenant.limits.max_systems * 100, 1) if tenant.limits.max_systems > 0 else 0
                },
                "storage_gb": {
                    "current": tenant.current_storage_gb,
                    "limit": tenant.limits.max_storage_gb,
                    "percent": round(tenant.current_storage_gb / tenant.limits.max_storage_gb * 100, 1) if tenant.limits.max_storage_gb > 0 else 0
                }
            },
            "features": {
                "sso_enabled": tenant.limits.sso_enabled,
                "ai_features": tenant.limits.ai_features,
                "advanced_analytics": tenant.limits.advanced_analytics,
                "custom_branding": tenant.limits.custom_branding,
                "dedicated_support": tenant.limits.dedicated_support
            },
            "config": {
                "timezone": tenant.config.timezone,
                "language": tenant.config.language,
                "data_region": tenant.config.data_region,
                "enabled_modules": tenant.config.enabled_modules
            },
            "created_at": tenant.created_at.isoformat(),
            "activated_at": tenant.activated_at.isoformat() if tenant.activated_at else None
        }
