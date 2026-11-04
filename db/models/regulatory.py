"""
Regulatory Intelligence — Obligation tracking, compliance mapping,
evidence linkage, and regulatory change management.
"""

import enum
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin


class ObligationStatus(str, enum.Enum):
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    SUPERSEDED = "superseded"
    RETIRED = "retired"


class ComplianceStatus(str, enum.Enum):
    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"
    EXEMPTED = "exempted"


class RegulationRegion(str, enum.Enum):
    GLOBAL = "global"
    US = "us"
    EU = "eu"
    APAC = "apac"
    EMEA = "emea"
    UK = "uk"
    INDIA = "india"
    SINGAPORE = "singapore"
    OTHER = "other"


class RegulatoryFramework(Base, TimestampMixin):
    """A regulation or compliance framework (SOX, GDPR, ISO 27001, etc.)."""
    __tablename__ = "regulatory_frameworks"

    framework_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    name = Column(String(300), nullable=False)           # SOX, GDPR, ISO 27001
    short_name = Column(String(50), nullable=True)       # SOX
    description = Column(Text, nullable=True)
    region = Column(String(50), nullable=False, default="global")
    effective_date = Column(DateTime, nullable=True)
    next_review_date = Column(DateTime, nullable=True)
    is_mandatory = Column(Boolean, default=True)
    external_reference = Column(String(500), nullable=True)  # URL to official doc
    owner_id = Column(String(100), nullable=True)
    owner_name = Column(String(200), nullable=True)
    status = Column(String(50), nullable=False, default="active")
    created_by = Column(String(100), nullable=True)

    obligations = relationship("RegulatoryObligation", back_populates="framework",
                               cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "framework_id": self.framework_id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "short_name": self.short_name,
            "description": self.description,
            "region": self.region,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "next_review_date": self.next_review_date.isoformat() if self.next_review_date else None,
            "is_mandatory": self.is_mandatory,
            "external_reference": self.external_reference,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RegulatoryObligation(Base, TimestampMixin):
    """A specific requirement within a regulatory framework."""
    __tablename__ = "regulatory_obligations"

    obligation_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    framework_id = Column(String(50), ForeignKey("regulatory_frameworks.framework_id"), nullable=False, index=True)

    reference_code = Column(String(100), nullable=True)   # e.g. SOX 302, GDPR Art.17
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    requirement_text = Column(Text, nullable=True)        # exact regulatory language
    obligation_type = Column(String(100), nullable=True)  # technical, process, reporting, documentation

    # Ownership
    owner_id = Column(String(100), nullable=True)
    owner_name = Column(String(200), nullable=True)
    accountable_department = Column(String(200), nullable=True)

    # Assessment
    compliance_status = Column(String(50), nullable=False, default="not_assessed")
    compliance_score = Column(Float, nullable=True)       # 0-100
    last_assessed_date = Column(DateTime, nullable=True)
    next_assessment_date = Column(DateTime, nullable=True)
    assessed_by = Column(String(100), nullable=True)

    # Status
    status = Column(String(50), nullable=False, default="active")
    is_key_obligation = Column(Boolean, default=False)
    penalty_risk = Column(String(50), nullable=True)      # low/medium/high/critical

    # Evidence
    evidence_summary = Column(Text, nullable=True)
    gaps_identified = Column(Text, nullable=True)

    # Linkage
    linked_control_ids = Column(JSON, default=list)       # process_control IDs
    linked_risk_ids = Column(JSON, default=list)          # enterprise_risk IDs
    linked_policy_ids = Column(JSON, default=list)        # policy_document IDs

    created_by = Column(String(100), nullable=True)

    framework = relationship("RegulatoryFramework", back_populates="obligations")
    evidence_records = relationship("ObligationEvidence", back_populates="obligation",
                                    cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "obligation_id": self.obligation_id,
            "tenant_id": self.tenant_id,
            "framework_id": self.framework_id,
            "reference_code": self.reference_code,
            "title": self.title,
            "description": self.description,
            "requirement_text": self.requirement_text,
            "obligation_type": self.obligation_type,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "accountable_department": self.accountable_department,
            "compliance_status": self.compliance_status,
            "compliance_score": self.compliance_score,
            "last_assessed_date": self.last_assessed_date.isoformat() if self.last_assessed_date else None,
            "next_assessment_date": self.next_assessment_date.isoformat() if self.next_assessment_date else None,
            "assessed_by": self.assessed_by,
            "status": self.status,
            "is_key_obligation": self.is_key_obligation,
            "penalty_risk": self.penalty_risk,
            "evidence_summary": self.evidence_summary,
            "gaps_identified": self.gaps_identified,
            "linked_control_ids": self.linked_control_ids or [],
            "linked_risk_ids": self.linked_risk_ids or [],
            "linked_policy_ids": self.linked_policy_ids or [],
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ObligationEvidence(Base, TimestampMixin):
    """Evidence record proving compliance with an obligation."""
    __tablename__ = "obligation_evidence"

    evidence_id = Column(String(50), primary_key=True)
    obligation_id = Column(String(50), ForeignKey("regulatory_obligations.obligation_id"), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    evidence_type = Column(String(100), nullable=True)    # document/screenshot/report/test_result
    file_reference = Column(String(500), nullable=True)
    collected_by = Column(String(100), nullable=True)
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)
    is_sufficient = Column(Boolean, nullable=True)

    obligation = relationship("RegulatoryObligation", back_populates="evidence_records")

    def to_dict(self):
        return {
            "evidence_id": self.evidence_id,
            "obligation_id": self.obligation_id,
            "title": self.title,
            "description": self.description,
            "evidence_type": self.evidence_type,
            "file_reference": self.file_reference,
            "collected_by": self.collected_by,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "is_sufficient": self.is_sufficient,
        }
