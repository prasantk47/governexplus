"""
Database Models - Tenant Management

Represents an organizational tenant on the GovernexPlus platform.
Each tenant is an isolated organizational unit with its own users,
rules, and configuration.
"""

import enum
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Text
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class TenantStatus(enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class TenantTier(enum.Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# Tier defaults: max_users per tier
TIER_MAX_USERS: dict = {
    TenantTier.STARTER.value: 25,
    TenantTier.PROFESSIONAL.value: 100,
    TenantTier.ENTERPRISE.value: 500,
}

# Default modules enabled per tier
TIER_DEFAULT_MODULES: dict = {
    TenantTier.STARTER.value: ["access_management"],
    TenantTier.PROFESSIONAL.value: ["access_management", "compliance", "risk_analytics"],
    TenantTier.ENTERPRISE.value: [
        "access_management", "compliance", "risk_analytics",
        "ai_assistant", "advanced_ml",
    ],
}


class Tenant(Base, TimestampMixin):
    """
    Tenant model representing a single organizational customer.

    All platform resources (users, rules, violations, audit logs) are
    scoped to a tenant via tenant_id foreign key references.

    The TimestampMixin provides created_at and updated_at columns.
    The explicit created_at below overrides the mixin so it can have
    a nullable-False constraint consistent with other models.
    """
    __tablename__ = "tenants"

    # Primary identifier — human-readable slug-based ID (e.g. "tenant_acme")
    id = Column(String(100), primary_key=True)

    # Display name of the organisation
    name = Column(String(255), nullable=False)

    # URL-safe unique slug used in routing and API isolation
    slug = Column(String(100), unique=True, nullable=False, index=True)

    # Lifecycle status: active | suspended | trial
    status = Column(String(20), nullable=False, default=TenantStatus.ACTIVE.value)

    # Subscription tier: starter | professional | enterprise
    tier = Column(String(20), nullable=False, default=TenantTier.ENTERPRISE.value)

    # Optional domain used for SSO / email validation
    domain = Column(String(255), nullable=True)

    # Contact details
    admin_email = Column(String(255), nullable=True)
    admin_name = Column(String(255), nullable=True)

    # Capacity
    max_users = Column(Integer, nullable=False, default=1000)

    # JSON list of module identifiers that are enabled for this tenant
    # Example: ["access_management", "compliance", "risk_analytics"]
    modules_enabled = Column(JSON, nullable=False, default=list)

    # Arbitrary tenant-level configuration bag
    settings = Column(JSON, nullable=False, default=dict)

    # Trial expiry — only set when status == 'trial'
    trial_ends = Column(DateTime, nullable=True)

    # Suspension metadata
    suspended_at = Column(DateTime, nullable=True)
    suspended_reason = Column(Text, nullable=True)

    # Soft-delete flag (future use)
    is_deleted = Column(Boolean, nullable=False, default=False)

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary suitable for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "status": self.status,
            "tier": self.tier,
            "domain": self.domain,
            "admin_email": self.admin_email,
            "admin_name": self.admin_name,
            "max_users": self.max_users,
            "modules_enabled": self.modules_enabled or [],
            "settings": self.settings or {},
            "trial_ends": self.trial_ends.isoformat() if self.trial_ends else None,
            "suspended_at": self.suspended_at.isoformat() if self.suspended_at else None,
            "suspended_reason": self.suspended_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Tenant(id='{self.id}', name='{self.name}', status='{self.status}')>"


class AdminSession(Base):
    """
    Persistent admin session — replaces the in-memory admin_sessions dict.

    Tokens survive restarts.  Expired rows are pruned lazily on each
    verify / login call.
    """
    __tablename__ = "admin_sessions"

    token = Column(String(128), primary_key=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    logged_in_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at

    def to_dict(self) -> dict:
        return {
            "email": self.email,
            "name": self.name,
            "logged_in_at": self.logged_in_at.isoformat(),
        }
