"""
Database Models - User and Role Management

Models for storing user information, roles, and entitlements
synchronized from SAP and other connected systems.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, Table, JSON, Float, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import Base, TimestampMixin


class UserType(enum.Enum):
    """User account types"""
    DIALOG = "dialog"           # Interactive user
    SERVICE = "service"         # Technical/service account
    SYSTEM = "system"           # System account
    COMMUNICATION = "comm"      # RFC/Communication user
    REFERENCE = "reference"     # Reference user


class UserStatus(enum.Enum):
    """User account status"""
    ACTIVE = "active"
    LOCKED = "locked"
    EXPIRED = "expired"
    DISABLED = "disabled"


class User(Base, TimestampMixin):
    """
    User model representing identities from connected systems.

    Stores both local GRC user info and synchronized data from SAP.
    """
    __tablename__ = 'users'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'user_id', name='uq_tenant_user_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    user_id = Column(String(50), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)

    # Source system
    source_system = Column(String(50), default='SAP')  # SAP, AzureAD, Okta, etc.
    system_client = Column(String(10), nullable=True)   # SAP client

    # Organizational data
    department = Column(String(100), nullable=True)
    cost_center = Column(String(50), nullable=True)
    company_code = Column(String(10), nullable=True)
    manager_user_id = Column(String(50), nullable=True)
    location = Column(String(100), nullable=True)

    # User type and status
    user_type = Column(SQLEnum(UserType), default=UserType.DIALOG)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE)

    # Validity
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)

    # Authentication
    last_login = Column(DateTime, nullable=True)
    failed_login_count = Column(Integer, default=0)
    password_changed_at = Column(DateTime, nullable=True)

    # Risk metrics
    risk_score = Column(Float, default=0.0)
    violation_count = Column(Integer, default=0)

    # Sync metadata
    last_synced_at = Column(DateTime, nullable=True)
    sync_source = Column(String(100), nullable=True)

    # Relationships
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    entitlements = relationship("UserEntitlement", back_populates="user", cascade="all, delete-orphan")
    violations = relationship("RiskViolation", back_populates="user")

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', name='{self.full_name}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'department': self.department,
            'cost_center': self.cost_center,
            'user_type': self.user_type.value if self.user_type else None,
            'status': self.status.value if self.status else None,
            'risk_score': self.risk_score,
            'violation_count': self.violation_count,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Role(Base, TimestampMixin):
    """
    Role model representing authorization roles from connected systems.
    """
    __tablename__ = 'roles'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'role_id', name='uq_tenant_role_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Role identity
    role_id = Column(String(100), nullable=False, index=True)
    role_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Source system
    source_system = Column(String(50), default='SAP')
    system_client = Column(String(10), nullable=True)

    # Role type
    role_type = Column(String(50), default='single')  # single, composite, derived

    # Parent role for derived/composite roles
    parent_role_id = Column(String(100), nullable=True)

    # Risk classification
    risk_level = Column(String(20), default='medium')  # low, medium, high, critical
    is_sensitive = Column(Boolean, default=False)

    # Ownership
    owner_user_id = Column(String(50), nullable=True)
    owner_email = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)

    # Statistics
    user_count = Column(Integer, default=0)
    transaction_count = Column(Integer, default=0)

    # Sync metadata
    last_synced_at = Column(DateTime, nullable=True)

    # Relationships
    user_assignments = relationship("UserRole", back_populates="role")

    def __repr__(self):
        return f"<Role(role_id='{self.role_id}', name='{self.role_name}')>"


class UserRole(Base, TimestampMixin):
    """
    Association table for User-Role assignments.

    Tracks role assignments with validity periods and assignment metadata.
    """
    __tablename__ = 'user_roles'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Foreign keys
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)

    # Assignment details
    assigned_by = Column(String(50), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    # Validity
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)

    # Request reference
    request_id = Column(String(100), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="user_assignments")

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class UserEntitlement(Base, TimestampMixin):
    """
    Detailed entitlements/authorizations for a user.

    Stores the expanded authorization values from all assigned roles.
    """
    __tablename__ = 'user_entitlements'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Authorization object details (SAP format)
    auth_object = Column(String(50), nullable=False, index=True)  # e.g., S_TCODE
    field = Column(String(50), nullable=False)                     # e.g., TCD
    value = Column(String(255), nullable=False)                    # e.g., FK01
    activity = Column(String(10), nullable=True)                   # e.g., 01, 02, 03

    # Source
    source_role = Column(String(100), nullable=True)
    source_system = Column(String(50), default='SAP')

    # Classification
    is_sensitive = Column(Boolean, default=False)
    risk_level = Column(String(20), default='low')

    # Relationships
    user = relationship("User", back_populates="entitlements")

    def __repr__(self):
        return f"<UserEntitlement({self.auth_object}:{self.field}={self.value})>"

    def to_key(self) -> str:
        """Generate unique key matching core.rules.models.Entitlement format"""
        base = f"{self.source_system}:{self.auth_object}:{self.field}:{self.value}"
        if self.activity:
            base += f":{self.activity}"
        return base
