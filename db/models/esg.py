"""
GAP-7: ESG Module
==================
Sustainability commitments, metrics, risks, controls, evidence, reporting.
"""
from sqlalchemy import Column, String, Text, JSON, DateTime, Integer, Boolean, Float, func
from .base import Base, TimestampMixin


class ESGCommitment(Base, TimestampMixin):
    __tablename__ = "esg_commitments"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    commitment_id = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    pillar = Column(String(20), nullable=False)  # environmental, social, governance
    category = Column(String(100))  # carbon, water, diversity, labor, board_composition, etc.
    framework = Column(String(100))  # GRI, SASB, TCFD, CSRD, UN_SDG, etc.
    framework_reference = Column(String(100))

    # Target
    target_description = Column(Text)
    target_value = Column(Float)
    target_unit = Column(String(50))
    target_date = Column(DateTime)
    baseline_value = Column(Float)
    baseline_date = Column(DateTime)

    # Current state
    current_value = Column(Float)
    current_date = Column(DateTime)
    progress_pct = Column(Float, default=0)

    # Ownership
    owner = Column(String(100))
    responsible_team = Column(String(100))

    # Risk & controls
    linked_risk_ids = Column(JSON)
    linked_control_ids = Column(JSON)
    linked_obligation_ids = Column(JSON)

    # Status
    status = Column(String(50), default="active")  # active, on_track, at_risk, behind, achieved, retired
    last_reviewed = Column(DateTime)
    review_frequency_days = Column(Integer, default=90)

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}


class ESGMetric(Base, TimestampMixin):
    __tablename__ = "esg_metrics"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    metric_id = Column(String(50), nullable=False)
    commitment_id = Column(String(50))
    name = Column(String(300), nullable=False)
    description = Column(Text)
    pillar = Column(String(20), nullable=False)
    category = Column(String(100))
    unit = Column(String(50))

    # Data
    value = Column(Float, nullable=False)
    period = Column(String(50))  # Q1-2026, 2026, Jan-2026
    reporting_date = Column(DateTime)
    data_source = Column(String(200))
    verified = Column(Boolean, default=False)
    verified_by = Column(String(100))
    verified_at = Column(DateTime)

    # Evidence
    evidence_ids = Column(JSON)
    methodology_notes = Column(Text)

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}


class ESGDisclosure(Base, TimestampMixin):
    __tablename__ = "esg_disclosures"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    framework = Column(String(100), nullable=False)
    reporting_period = Column(String(50), nullable=False)
    status = Column(String(50), default="draft")  # draft, review, approved, published
    disclosure_data = Column(JSON)
    commitment_ids = Column(JSON)
    metric_ids = Column(JSON)
    prepared_by = Column(String(100))
    reviewed_by = Column(String(100))
    approved_by = Column(String(100))
    published_at = Column(DateTime)

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}
