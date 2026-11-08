"""
GAP-4: Obligation Management
=============================
Break regulations into actionable obligations, map to controls,
assess compliance per obligation. Full obligation lifecycle.
"""
from sqlalchemy import Column, String, Text, JSON, DateTime, Integer, Boolean, Float, func
from .base import Base, TimestampMixin


class Obligation(Base, TimestampMixin):
    __tablename__ = "obligations"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    obligation_id = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)

    # Source
    regulation_id = Column(String(50))
    regulation_name = Column(String(200))
    section_reference = Column(String(100))
    jurisdiction = Column(String(100))
    effective_date = Column(DateTime)

    # Classification
    category = Column(String(50))  # data_protection, financial, safety, environmental, etc.
    obligation_type = Column(String(50))  # mandatory, advisory, contractual
    applicability = Column(JSON)  # list of entities/units/processes this applies to
    applicable_entities = Column(JSON)

    # Ownership
    owner = Column(String(100))
    responsible_team = Column(String(100))

    # Mapping
    linked_policy_ids = Column(JSON)
    linked_control_ids = Column(JSON)
    linked_control_objective_ids = Column(JSON)
    linked_risk_ids = Column(JSON)

    # Assessment
    compliance_status = Column(String(50), default="not_assessed")  # not_assessed, compliant, partially_compliant, non_compliant, not_applicable
    last_assessed_date = Column(DateTime)
    last_assessed_by = Column(String(100))
    assessment_evidence = Column(Text)
    gap_description = Column(Text)
    remediation_plan = Column(Text)

    # Lifecycle
    status = Column(String(50), default="active")  # active, retired, superseded, pending_review
    review_frequency_days = Column(Integer, default=365)
    next_review_date = Column(DateTime)
    superseded_by = Column(String(50))

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}


class ObligationAssessment(Base, TimestampMixin):
    __tablename__ = "obligation_assessments"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    obligation_id = Column(String(50), nullable=False)
    assessment_period = Column(String(50))
    assessor = Column(String(100), nullable=False)
    compliance_rating = Column(String(50), nullable=False)  # compliant, partially_compliant, non_compliant
    evidence_summary = Column(Text)
    gaps_identified = Column(JSON)
    exceptions = Column(JSON)
    remediation_actions = Column(JSON)
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}
