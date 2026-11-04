"""
Database Models - SOX / ICFR Module

Internal Controls over Financial Reporting (ICFR) for SOX 302/404 compliance.
Covers control matrix, management assessment, deficiency classification,
sign-off workflow, and financial close management.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Float, ForeignKey
from datetime import datetime
import enum

from .base import Base, TimestampMixin


class ICFRControlType(enum.Enum):
    ENTITY_LEVEL = "entity_level"
    PROCESS_LEVEL = "process_level"
    IT_GENERAL = "it_general"
    IT_APPLICATION = "it_application"
    DISCLOSURE = "disclosure"


class ICFRFrequency(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    AD_HOC = "ad_hoc"


class ICFREffectiveness(enum.Enum):
    EFFECTIVE = "effective"
    DEFICIENCY = "deficiency"
    SIGNIFICANT_DEFICIENCY = "significant_deficiency"
    MATERIAL_WEAKNESS = "material_weakness"
    NOT_TESTED = "not_tested"


class SOXSignoffStatus(enum.Enum):
    PENDING = "pending"
    SIGNED = "signed"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class FinancialCloseStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"


class ICFRControl(Base, TimestampMixin):
    """SOX ICFR control — mapped to financial statement assertions."""
    __tablename__ = 'icfr_controls'

    id = Column(Integer, primary_key=True, autoincrement=True)
    control_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    # Identity
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    control_type = Column(String(50), nullable=False, default="process_level")
    frequency = Column(String(50), nullable=False, default="monthly")

    # Financial statement linkage
    financial_statement_area = Column(String(255), nullable=True)   # e.g. Revenue, Payroll
    assertions = Column(JSON, nullable=True)                         # completeness, accuracy, existence, etc.
    account_codes = Column(JSON, nullable=True)                      # GL account codes covered

    # Process linkage
    process_name = Column(String(255), nullable=True)
    sub_process = Column(String(255), nullable=True)

    # Ownership
    control_owner = Column(String(255), nullable=True)
    control_performer = Column(String(255), nullable=True)
    reviewer = Column(String(255), nullable=True)

    # Assessment
    design_effectiveness = Column(String(50), nullable=True)
    operating_effectiveness = Column(String(50), nullable=True)
    overall_effectiveness = Column(String(50), nullable=True, default="not_tested")

    # Deficiency tracking
    deficiency_type = Column(String(50), nullable=True)             # deficiency/significant_deficiency/material_weakness
    deficiency_description = Column(Text, nullable=True)
    remediation_plan = Column(Text, nullable=True)
    remediation_due_date = Column(DateTime, nullable=True)
    remediation_status = Column(String(50), nullable=True)

    # SOX section
    sox_section = Column(String(20), nullable=True)                 # 302 or 404
    is_key_control = Column(Boolean, default=False, nullable=False)
    is_automated = Column(Boolean, default=False, nullable=False)

    # Evidence
    evidence_requirements = Column(Text, nullable=True)
    evidence_links = Column(JSON, nullable=True)

    # Last test
    last_tested_at = Column(DateTime, nullable=True)
    last_tested_by = Column(String(255), nullable=True)
    next_test_date = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    extra = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'control_id': self.control_id,
            'tenant_id': self.tenant_id,
            'title': self.title,
            'description': self.description,
            'control_type': getattr(self.control_type, 'value', self.control_type),
            'frequency': getattr(self.frequency, 'value', self.frequency),
            'financial_statement_area': self.financial_statement_area,
            'assertions': self.assertions,
            'account_codes': self.account_codes,
            'process_name': self.process_name,
            'sub_process': self.sub_process,
            'control_owner': self.control_owner,
            'control_performer': self.control_performer,
            'reviewer': self.reviewer,
            'design_effectiveness': getattr(self.design_effectiveness, 'value', self.design_effectiveness),
            'operating_effectiveness': getattr(self.operating_effectiveness, 'value', self.operating_effectiveness),
            'overall_effectiveness': getattr(self.overall_effectiveness, 'value', self.overall_effectiveness),
            'deficiency_type': getattr(self.deficiency_type, 'value', self.deficiency_type),
            'deficiency_description': self.deficiency_description,
            'remediation_plan': self.remediation_plan,
            'remediation_due_date': self.remediation_due_date.isoformat() if self.remediation_due_date else None,
            'remediation_status': self.remediation_status,
            'sox_section': self.sox_section,
            'is_key_control': self.is_key_control,
            'is_automated': self.is_automated,
            'evidence_requirements': self.evidence_requirements,
            'evidence_links': self.evidence_links,
            'last_tested_at': self.last_tested_at.isoformat() if self.last_tested_at else None,
            'last_tested_by': self.last_tested_by,
            'next_test_date': self.next_test_date.isoformat() if self.next_test_date else None,
            'is_active': self.is_active,
            'extra': self.extra,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SOXSignoff(Base, TimestampMixin):
    """SOX 302/404 management sign-off record."""
    __tablename__ = 'sox_signoffs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    signoff_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    period = Column(String(50), nullable=False)                     # e.g. Q4 2026
    sox_section = Column(String(10), nullable=False)                # 302 or 404
    signoff_type = Column(String(50), nullable=False)               # ceo, cfo, controller, external_auditor

    signer_name = Column(String(255), nullable=False)
    signer_title = Column(String(255), nullable=True)
    signer_email = Column(String(255), nullable=True)

    status = Column(String(50), nullable=False, default="pending")
    signed_at = Column(DateTime, nullable=True)

    # Assessment summary
    total_key_controls = Column(Integer, nullable=True)
    effective_controls = Column(Integer, nullable=True)
    deficiencies = Column(Integer, nullable=True)
    significant_deficiencies = Column(Integer, nullable=True)
    material_weaknesses = Column(Integer, nullable=True)

    # Conclusion
    conclusion = Column(String(50), nullable=True)                  # effective / ineffective
    conclusion_notes = Column(Text, nullable=True)
    exceptions_noted = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'signoff_id': self.signoff_id,
            'tenant_id': self.tenant_id,
            'period': self.period,
            'sox_section': self.sox_section,
            'signoff_type': self.signoff_type,
            'signer_name': self.signer_name,
            'signer_title': self.signer_title,
            'signer_email': self.signer_email,
            'status': getattr(self.status, 'value', self.status),
            'signed_at': self.signed_at.isoformat() if self.signed_at else None,
            'total_key_controls': self.total_key_controls,
            'effective_controls': self.effective_controls,
            'deficiencies': self.deficiencies,
            'significant_deficiencies': self.significant_deficiencies,
            'material_weaknesses': self.material_weaknesses,
            'conclusion': self.conclusion,
            'conclusion_notes': self.conclusion_notes,
            'exceptions_noted': self.exceptions_noted,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialCloseTask(Base, TimestampMixin):
    """Financial close checklist task."""
    __tablename__ = 'financial_close_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    period = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=True)                   # reconciliation, journal, approval, etc.
    sequence_order = Column(Integer, nullable=True)

    assigned_to = Column(String(255), nullable=True)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(String(255), nullable=True)

    status = Column(String(50), nullable=False, default="open")
    is_critical_path = Column(Boolean, default=False)
    linked_control_id = Column(String(100), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'tenant_id': self.tenant_id,
            'period': self.period,
            'title': self.title,
            'description': self.description,
            'task_type': self.task_type,
            'sequence_order': self.sequence_order,
            'assigned_to': self.assigned_to,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'completed_by': self.completed_by,
            'status': getattr(self.status, 'value', self.status),
            'is_critical_path': self.is_critical_path,
            'linked_control_id': self.linked_control_id,
            'notes': self.notes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
