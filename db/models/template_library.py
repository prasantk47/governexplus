"""
Template Library models — global (tenant-null) + per-tenant activation.

Architecture:
  template_pack          — named collection of template_items (e.g. "SOX Compliance Pack")
  template_pack_version  — versioned snapshot of a pack (immutable once published)
  template_item          — individual template (rule, workflow, control, etc.) — tenant_id=NULL
  tenant_item_activation — per-tenant activation record; copy_payload populated on first edit
"""

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, DateTime,
    ForeignKey, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import relationship
from db.base import Base
from db.mixins import TimestampMixin
import datetime


class TemplatePack(Base, TimestampMixin):
    """Named collection of template items (e.g. 'SAP GRC Migration Pack')."""
    __tablename__ = "template_packs"

    id = Column(String(36), primary_key=True)
    pack_code = Column(String(100), nullable=False, unique=True)   # e.g. SAP_MIGRATION_V1
    name = Column(String(255), nullable=False)
    description = Column(Text)
    module = Column(String(50))    # ara | arm | jml | bcm | all
    tags = Column(JSON)            # list of strings
    status = Column(String(20), nullable=False, default="draft")  # draft|published|deprecated
    author = Column(String(100))
    license_note = Column(String(500))

    versions = relationship("TemplatePackVersion", back_populates="pack", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "pack_code": self.pack_code,
            "name": self.name,
            "description": self.description,
            "module": self.module,
            "tags": self.tags or [],
            "status": self.status,
            "author": self.author,
            "license_note": self.license_note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TemplatePackVersion(Base, TimestampMixin):
    """Immutable versioned snapshot of a pack. Once published, payload is frozen."""
    __tablename__ = "template_pack_versions"

    id = Column(String(36), primary_key=True)
    pack_id = Column(String(36), ForeignKey("template_packs.id"), nullable=False)
    version = Column(String(20), nullable=False)   # semver e.g. "1.0.0"
    changelog = Column(Text)
    published_at = Column(DateTime)
    checksum = Column(String(64))   # SHA-256 of payload
    item_count = Column(Integer, default=0)
    is_latest = Column(Boolean, default=False)

    pack = relationship("TemplatePack", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("pack_id", "version", name="uq_pack_version"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "pack_id": self.pack_id,
            "version": self.version,
            "changelog": self.changelog,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "checksum": self.checksum,
            "item_count": self.item_count,
            "is_latest": self.is_latest,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TemplateItem(Base, TimestampMixin):
    """
    Individual template — globally shared, tenant_id IS NULL.
    Types: sod_rule | mitigation | workflow | access_policy | control |
           certification_template | risk_scenario | jml_policy | survey |
           report | notification | connector_config
    """
    __tablename__ = "template_items"

    id = Column(String(36), primary_key=True)
    # No tenant_id — this is the global library
    item_code = Column(String(100), nullable=False, unique=True)  # e.g. SOD-FI-001
    name = Column(String(255), nullable=False)
    description = Column(Text)
    module = Column(String(50), nullable=False)   # ara|arm|jml|bcm|...
    item_type = Column(String(50), nullable=False)  # sod_rule|workflow|control|...
    compliance_frameworks = Column(JSON)   # ["SOX", "GDPR", ...]
    industry_tags = Column(JSON)           # ["manufacturing", "finance", ...]
    payload = Column(JSON, nullable=False)  # full template content
    version = Column(String(20), nullable=False, default="1.0.0")
    checksum = Column(String(64))          # SHA-256 of payload JSON
    status = Column(String(20), nullable=False, default="published")  # draft|published|deprecated
    pack_id = Column(String(36), ForeignKey("template_packs.id"), nullable=True)
    pack_version = Column(String(20))
    severity = Column(String(20))          # for rules/risks: critical|high|medium|low
    activation_count = Column(Integer, default=0)  # how many tenants activated

    activations = relationship("TenantItemActivation", back_populates="template_item", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_template_items_module", "module"),
        Index("ix_template_items_item_type", "item_type"),
        Index("ix_template_items_status", "status"),
    )

    def to_dict(self, include_payload=True):
        d = {
            "id": self.id,
            "item_code": self.item_code,
            "name": self.name,
            "description": self.description,
            "module": self.module,
            "item_type": self.item_type,
            "compliance_frameworks": self.compliance_frameworks or [],
            "industry_tags": self.industry_tags or [],
            "version": self.version,
            "checksum": self.checksum,
            "status": self.status,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "severity": self.severity,
            "activation_count": self.activation_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_payload:
            d["payload"] = self.payload
        return d


class TenantItemActivation(Base, TimestampMixin):
    """
    Per-tenant activation of a template item.
    copy_payload is NULL until the tenant first edits the item (copy-on-write).
    When copy_payload is set, the tenant's customization diverges from the global template.
    """
    __tablename__ = "tenant_item_activations"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    template_item_id = Column(String(36), ForeignKey("template_items.id"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    activated_at = Column(DateTime)
    activated_by = Column(String(100))
    # Copy-on-write: populated when tenant first customizes
    copy_payload = Column(JSON, nullable=True)
    customized_at = Column(DateTime, nullable=True)
    customized_by = Column(String(100), nullable=True)
    # Field mappings specific to this tenant (e.g. SAP system ID, org unit)
    mappings = Column(JSON, nullable=True)
    # Update tracking
    pending_update_version = Column(String(20), nullable=True)  # new global version available
    update_reviewed_at = Column(DateTime, nullable=True)
    update_review_decision = Column(String(20), nullable=True)  # accept|reject|defer
    notes = Column(Text, nullable=True)

    template_item = relationship("TemplateItem", back_populates="activations")

    __table_args__ = (
        UniqueConstraint("tenant_id", "template_item_id", name="uq_tenant_activation"),
        Index("ix_tenant_item_activations_tenant", "tenant_id"),
        Index("ix_tenant_item_activations_active", "tenant_id", "is_active"),
    )

    def effective_payload(self):
        """Return tenant's copy if customized, else global template payload."""
        if self.copy_payload:
            return self.copy_payload
        return self.template_item.payload if self.template_item else None

    def to_dict(self, include_item=False):
        d = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "template_item_id": self.template_item_id,
            "is_active": self.is_active,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "activated_by": self.activated_by,
            "is_customized": self.copy_payload is not None,
            "customized_at": self.customized_at.isoformat() if self.customized_at else None,
            "customized_by": self.customized_by,
            "mappings": self.mappings or {},
            "pending_update_version": self.pending_update_version,
            "update_reviewed_at": self.update_reviewed_at.isoformat() if self.update_reviewed_at else None,
            "update_review_decision": self.update_review_decision,
            "notes": self.notes,
        }
        if include_item and self.template_item:
            d["item"] = self.template_item.to_dict(include_payload=False)
        return d
