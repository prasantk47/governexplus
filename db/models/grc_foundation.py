"""
Database Models - GRC Foundation

Shared foundation models used across all GRC modules:
  - OrgUnit          : hierarchical organisational structure (XI-01, RM-02, PC-02)
  - FrameworkDefinition  : COSO, COBIT, ISO 27001, SOX, custom frameworks (PC-03, XI-07)
  - FrameworkRequirement : individual principle / control objective within a framework
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import Base, TimestampMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OrgUnitType(enum.Enum):
    """Hierarchy levels in the organisational structure"""
    COMPANY = "company"
    DIVISION = "division"
    DEPARTMENT = "department"
    BRANCH = "branch"
    PLANT = "plant"
    COST_CENTER = "cost_center"


class FrameworkType(enum.Enum):
    """Supported GRC framework types"""
    COSO = "coso"
    COBIT = "cobit"
    ISO27001 = "iso27001"
    SOX = "sox"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# OrgUnit
# ---------------------------------------------------------------------------

class OrgUnit(Base, TimestampMixin):
    """
    Hierarchical organisational unit.

    Supports arbitrary depth via a self-referential parent FK and a
    materialised-path string for efficient ancestor / descendant queries.
    Used by Risk Management (RM-02), Process Control (PC-02), and the
    cross-module identity hierarchy (XI-01).
    """
    __tablename__ = 'org_units'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    unit_id = Column(String(100), nullable=False, index=True)   # unique within tenant
    name = Column(String(255), nullable=False)
    unit_type = Column(SQLEnum(OrgUnitType), nullable=False)

    # Hierarchy
    parent_id = Column(Integer, ForeignKey('org_units.id'), nullable=True, index=True)
    level = Column(Integer, nullable=False, default=0)           # 0 = root
    path = Column(String(1000), nullable=True)                   # e.g. "1/5/12"

    # Ownership & location
    manager_user_id = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Flexible extension bag
    metadata_ = Column('metadata', JSON, nullable=True)

    # Relationships
    parent = relationship('OrgUnit', remote_side='OrgUnit.id', back_populates='children')
    children = relationship('OrgUnit', back_populates='parent')

    def __repr__(self):
        return f"<OrgUnit(unit_id='{self.unit_id}', name='{self.name}', type='{self.unit_type}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'unit_id': self.unit_id,
            'name': self.name,
            'unit_type': self.unit_type.value if self.unit_type else None,
            'parent_id': self.parent_id,
            'level': self.level,
            'path': self.path,
            'manager_user_id': self.manager_user_id,
            'country': self.country,
            'region': self.region,
            'is_active': self.is_active,
            'metadata': self.metadata_,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# FrameworkDefinition
# ---------------------------------------------------------------------------

class FrameworkDefinition(Base, TimestampMixin):
    """
    Top-level GRC framework definition.

    Stores the full framework tree (components, principles, domains, etc.)
    as a JSON document.  Supports COSO 2013, COBIT 2019, ISO/IEC 27001:2022,
    SOX, and fully custom frameworks (PC-03, XI-07).
    """
    __tablename__ = 'framework_definitions'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Identity
    framework_id = Column(String(100), nullable=False, index=True)   # unique within tenant
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=True)                       # e.g. "2013", "2019"
    description = Column(Text, nullable=True)

    # Classification
    framework_type = Column(SQLEnum(FrameworkType), nullable=False)

    # Full hierarchical structure stored as a JSON document
    structure = Column(JSON, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    requirements = relationship(
        'FrameworkRequirement',
        back_populates='framework',
        foreign_keys='FrameworkRequirement.framework_id',
        primaryjoin='FrameworkDefinition.id == FrameworkRequirement.framework_id',
    )

    def __repr__(self):
        return (
            f"<FrameworkDefinition(framework_id='{self.framework_id}', "
            f"name='{self.name}', type='{self.framework_type}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'framework_id': self.framework_id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'framework_type': self.framework_type.value if self.framework_type else None,
            'structure': self.structure,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# FrameworkRequirement
# ---------------------------------------------------------------------------

class FrameworkRequirement(Base, TimestampMixin):
    """
    Individual principle / control objective within a GRC framework.

    Supports arbitrary nesting through a self-referential parent FK so that
    frameworks with multiple levels (e.g. COSO Component → Principle →
    Point-of-Focus) can be represented natively.
    """
    __tablename__ = 'framework_requirements'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Parent framework
    framework_id = Column(Integer, ForeignKey('framework_definitions.id'), nullable=False, index=True)

    # Identity
    requirement_id = Column(String(100), nullable=False, index=True)  # e.g. "COSO-P1"
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Hierarchy
    parent_requirement_id = Column(
        Integer, ForeignKey('framework_requirements.id'), nullable=True, index=True
    )
    level = Column(Integer, nullable=False, default=0)    # 0 = top-level within framework
    sort_order = Column(Integer, nullable=False, default=0)

    # Classification
    category = Column(String(100), nullable=True)   # e.g. "Control Environment", "Risk Assessment"

    # Relationships
    framework = relationship(
        'FrameworkDefinition',
        back_populates='requirements',
        foreign_keys=[framework_id],
    )
    parent = relationship(
        'FrameworkRequirement',
        remote_side='FrameworkRequirement.id',
        back_populates='children',
    )
    children = relationship('FrameworkRequirement', back_populates='parent')

    def __repr__(self):
        return (
            f"<FrameworkRequirement(requirement_id='{self.requirement_id}', "
            f"title='{self.title[:40]}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'framework_id': self.framework_id,
            'requirement_id': self.requirement_id,
            'title': self.title,
            'description': self.description,
            'parent_requirement_id': self.parent_requirement_id,
            'category': self.category,
            'level': self.level,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
