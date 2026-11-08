"""
GAP-5: Evidence Management Service
====================================
Evidence as first-class objects with common schema, integrity hash,
retention class, legal hold, chain-of-custody, disposal lifecycle.
"""
from sqlalchemy import Column, String, Text, JSON, DateTime, Integer, Boolean, Float, func
from .base import Base, TimestampMixin


class EvidenceItem(Base, TimestampMixin):
    __tablename__ = "evidence_items"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    evidence_id = Column(String(50), nullable=False, unique=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)

    # Classification
    evidence_type = Column(String(50), nullable=False)  # document, screenshot, log_extract, report, attestation, system_export
    category = Column(String(50))  # control_test, audit, investigation, compliance, change, access
    sensitivity = Column(String(30), default="internal")  # public, internal, confidential, restricted

    # Source
    source_system = Column(String(100))
    source_module = Column(String(100))
    source_record_id = Column(String(200))
    source_record_type = Column(String(100))
    collected_by = Column(String(100), nullable=False)
    collected_at = Column(DateTime, nullable=False)

    # Content
    file_name = Column(String(300))
    file_type = Column(String(50))
    file_size_bytes = Column(Integer)
    storage_path = Column(String(500))
    content_text = Column(Text)  # for searchable text evidence
    metadata_ = Column("metadata", JSON)

    # Integrity
    checksum_sha256 = Column(String(64))
    is_tamper_evident = Column(Boolean, default=False)
    version_number = Column(Integer, default=1)
    supersedes_evidence_id = Column(String(50))

    # Retention
    retention_class = Column(String(50), default="standard")  # standard, extended, permanent
    retention_period_days = Column(Integer, default=2555)  # ~7 years
    retention_expiry_date = Column(DateTime)
    legal_hold = Column(Boolean, default=False)
    legal_hold_reason = Column(Text)
    legal_hold_set_by = Column(String(100))
    legal_hold_set_at = Column(DateTime)
    disposal_eligible = Column(Boolean, default=False)
    disposed_at = Column(DateTime)
    disposed_by = Column(String(100))

    # Chain of custody
    custody_chain = Column(JSON)  # [{actor, action, timestamp, notes}]

    # Links to GRC objects
    linked_control_ids = Column(JSON)
    linked_risk_ids = Column(JSON)
    linked_issue_ids = Column(JSON)
    linked_finding_ids = Column(JSON)
    linked_audit_ids = Column(JSON)
    linked_obligation_ids = Column(JSON)

    # Status
    status = Column(String(50), default="active")  # active, archived, disposed, superseded

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}


class EvidencePackage(Base, TimestampMixin):
    """A curated collection of evidence items for audit/compliance use."""
    __tablename__ = "evidence_packages"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    package_id = Column(String(50), nullable=False, unique=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    package_type = Column(String(50))  # audit_engagement, control_test, compliance_assessment, investigation
    purpose = Column(Text)

    # Contents
    evidence_item_ids = Column(JSON, default=[])
    item_count = Column(Integer, default=0)

    # Ownership
    compiled_by = Column(String(100), nullable=False)
    compiled_at = Column(DateTime)
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    approved_by = Column(String(100))
    approved_at = Column(DateTime)

    # Links
    linked_engagement_id = Column(String(50))
    linked_assessment_id = Column(String(50))
    linked_change_request_id = Column(String(50))

    # Access
    access_restricted_to = Column(JSON)  # list of roles/users
    access_log = Column(JSON)  # [{actor, action, timestamp}]

    status = Column(String(50), default="draft")  # draft, compiled, reviewed, approved, sealed

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}
