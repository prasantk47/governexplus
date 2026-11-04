"""
Database Models - Governance Extended Modules

Covers:
- Regulatory Change Management
- Operational Loss Events / RCSA
- SoD Remediation Workflow
- IT Change Risk (ITGC)
- Insurance / Risk Transfer
- Sanctions / Watchlist Screening
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Float
from datetime import datetime
import enum

from .base import Base, TimestampMixin


# ─────────────────────────────────────────────────────────────────
# Regulatory Change Management
# ─────────────────────────────────────────────────────────────────

class RegChangeStatus(enum.Enum):
    NEW = "new"
    UNDER_REVIEW = "under_review"
    IMPACT_ASSESSED = "impact_assessed"
    ACTION_PLANNED = "action_planned"
    IMPLEMENTED = "implemented"
    CLOSED = "closed"


class RegChangeImpact(enum.Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RegulatoryChange(Base, TimestampMixin):
    """Incoming regulatory change / alert."""
    __tablename__ = 'regulatory_changes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    change_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    regulator = Column(String(255), nullable=True)
    jurisdiction = Column(String(100), nullable=True)
    regulation_name = Column(String(255), nullable=True)
    change_type = Column(String(100), nullable=True)                # new_regulation, amendment, guidance, enforcement
    effective_date = Column(DateTime, nullable=True)
    comment_deadline = Column(DateTime, nullable=True)
    source_url = Column(String(1000), nullable=True)

    impact_level = Column(String(50), nullable=False, default="medium")
    impact_description = Column(Text, nullable=True)
    affected_obligations = Column(JSON, nullable=True)              # list of obligation IDs
    affected_controls = Column(JSON, nullable=True)
    affected_policies = Column(JSON, nullable=True)

    assigned_to = Column(String(255), nullable=True)
    action_plan = Column(Text, nullable=True)
    action_due_date = Column(DateTime, nullable=True)
    implementation_notes = Column(Text, nullable=True)
    implemented_at = Column(DateTime, nullable=True)

    status = Column(String(50), nullable=False, default="new")
    is_active = Column(Boolean, default=True, nullable=False)
    extra = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 'change_id': self.change_id, 'tenant_id': self.tenant_id,
            'title': self.title, 'description': self.description, 'regulator': self.regulator,
            'jurisdiction': self.jurisdiction, 'regulation_name': self.regulation_name,
            'change_type': self.change_type,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'comment_deadline': self.comment_deadline.isoformat() if self.comment_deadline else None,
            'source_url': self.source_url,
            'impact_level': getattr(self.impact_level, 'value', self.impact_level),
            'impact_description': self.impact_description,
            'affected_obligations': self.affected_obligations, 'affected_controls': self.affected_controls,
            'affected_policies': self.affected_policies, 'assigned_to': self.assigned_to,
            'action_plan': self.action_plan,
            'action_due_date': self.action_due_date.isoformat() if self.action_due_date else None,
            'implementation_notes': self.implementation_notes,
            'implemented_at': self.implemented_at.isoformat() if self.implemented_at else None,
            'status': getattr(self.status, 'value', self.status), 'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ─────────────────────────────────────────────────────────────────
# Operational Loss Events / RCSA
# ─────────────────────────────────────────────────────────────────

class LossEventStatus(enum.Enum):
    REPORTED = "reported"
    UNDER_REVIEW = "under_review"
    CONFIRMED = "confirmed"
    CLOSED = "closed"
    REJECTED = "rejected"


class OperationalLossEvent(Base, TimestampMixin):
    """Operational risk loss event (Basel II/III compliant)."""
    __tablename__ = 'operational_loss_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    event_type = Column(String(100), nullable=True)                 # Basel II event type
    business_line = Column(String(255), nullable=True)              # Basel II business line
    org_unit = Column(String(255), nullable=True)

    occurred_at = Column(DateTime, nullable=True)
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reported_by = Column(String(255), nullable=True)

    gross_loss = Column(Float, nullable=True)
    recoveries = Column(Float, nullable=True)
    net_loss = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True, default="USD")
    is_near_miss = Column(Boolean, default=False)

    root_cause_category = Column(String(100), nullable=True)
    root_cause_description = Column(Text, nullable=True)
    contributing_factors = Column(JSON, nullable=True)

    corrective_actions = Column(Text, nullable=True)
    preventive_actions = Column(Text, nullable=True)
    linked_risk_ids = Column(JSON, nullable=True)
    linked_control_ids = Column(JSON, nullable=True)

    status = Column(String(50), nullable=False, default="reported")
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    extra = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 'event_id': self.event_id, 'tenant_id': self.tenant_id,
            'title': self.title, 'description': self.description,
            'event_type': self.event_type, 'business_line': self.business_line, 'org_unit': self.org_unit,
            'occurred_at': self.occurred_at.isoformat() if self.occurred_at else None,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'reported_by': self.reported_by, 'gross_loss': self.gross_loss,
            'recoveries': self.recoveries, 'net_loss': self.net_loss, 'currency': self.currency,
            'is_near_miss': self.is_near_miss, 'root_cause_category': self.root_cause_category,
            'root_cause_description': self.root_cause_description,
            'contributing_factors': self.contributing_factors,
            'corrective_actions': self.corrective_actions, 'preventive_actions': self.preventive_actions,
            'linked_risk_ids': self.linked_risk_ids, 'linked_control_ids': self.linked_control_ids,
            'status': getattr(self.status, 'value', self.status),
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ─────────────────────────────────────────────────────────────────
# SoD Remediation Workflow
# ─────────────────────────────────────────────────────────────────

class SoDRemediationStatus(enum.Enum):
    OPEN = "open"
    IN_REMEDIATION = "in_remediation"
    PENDING_VALIDATION = "pending_validation"
    VALIDATED = "validated"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class SoDRemediation(Base, TimestampMixin):
    """Dedicated remediation workflow for SoD violations."""
    __tablename__ = 'sod_remediations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    remediation_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    violation_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    rule_id = Column(String(100), nullable=False)
    rule_description = Column(String(500), nullable=True)
    severity = Column(String(50), nullable=True)

    # Remediation plan
    remediation_type = Column(String(50), nullable=True)            # role_removal, access_reduction, compensating_control, exception
    remediation_description = Column(Text, nullable=True)
    assigned_to = Column(String(255), nullable=True)
    due_date = Column(DateTime, nullable=True)

    # Progress
    actions_taken = Column(JSON, nullable=True)                     # list of actions with dates
    evidence_links = Column(JSON, nullable=True)

    # Validation
    validated_by = Column(String(255), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    validation_notes = Column(Text, nullable=True)

    # Exception path
    exception_requested = Column(Boolean, default=False)
    exception_rationale = Column(Text, nullable=True)
    exception_approved_by = Column(String(255), nullable=True)
    exception_expiry = Column(DateTime, nullable=True)

    status = Column(String(50), nullable=False, default="open")
    closed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id, 'remediation_id': self.remediation_id, 'tenant_id': self.tenant_id,
            'violation_id': self.violation_id, 'user_id': self.user_id,
            'rule_id': self.rule_id, 'rule_description': self.rule_description,
            'severity': getattr(self.severity, 'value', self.severity),
            'remediation_type': self.remediation_type, 'remediation_description': self.remediation_description,
            'assigned_to': self.assigned_to,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'actions_taken': self.actions_taken, 'evidence_links': self.evidence_links,
            'validated_by': self.validated_by,
            'validated_at': self.validated_at.isoformat() if self.validated_at else None,
            'validation_notes': self.validation_notes,
            'exception_requested': self.exception_requested, 'exception_rationale': self.exception_rationale,
            'exception_approved_by': self.exception_approved_by,
            'exception_expiry': self.exception_expiry.isoformat() if self.exception_expiry else None,
            'status': getattr(self.status, 'value', self.status),
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ─────────────────────────────────────────────────────────────────
# IT Change Risk (ITGC)
# ─────────────────────────────────────────────────────────────────

class ITChangeRisk(Base, TimestampMixin):
    """IT change risk assessment (ITGC change management)."""
    __tablename__ = 'it_change_risks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    change_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    change_type = Column(String(100), nullable=True)                # normal, standard, emergency, major
    system_name = Column(String(255), nullable=True)
    systems_affected = Column(JSON, nullable=True)

    requested_by = Column(String(255), nullable=True)
    assigned_to = Column(String(255), nullable=True)
    planned_date = Column(DateTime, nullable=True)
    actual_date = Column(DateTime, nullable=True)

    risk_level = Column(String(50), nullable=False, default="medium")
    risk_description = Column(Text, nullable=True)
    rollback_plan = Column(Text, nullable=True)
    testing_evidence = Column(Text, nullable=True)

    approval_status = Column(String(50), nullable=False, default="pending")
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    post_change_review = Column(Text, nullable=True)
    post_change_status = Column(String(50), nullable=True)         # successful, partial, failed, rolled_back
    reviewed_at = Column(DateTime, nullable=True)

    linked_sox_control_ids = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    extra = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 'change_id': self.change_id, 'tenant_id': self.tenant_id,
            'title': self.title, 'description': self.description,
            'change_type': self.change_type, 'system_name': self.system_name,
            'systems_affected': self.systems_affected,
            'requested_by': self.requested_by, 'assigned_to': self.assigned_to,
            'planned_date': self.planned_date.isoformat() if self.planned_date else None,
            'actual_date': self.actual_date.isoformat() if self.actual_date else None,
            'risk_level': getattr(self.risk_level, 'value', self.risk_level),
            'risk_description': self.risk_description, 'rollback_plan': self.rollback_plan,
            'testing_evidence': self.testing_evidence,
            'approval_status': getattr(self.approval_status, 'value', self.approval_status),
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejection_reason': self.rejection_reason,
            'post_change_review': self.post_change_review, 'post_change_status': self.post_change_status,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'linked_sox_control_ids': self.linked_sox_control_ids,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ─────────────────────────────────────────────────────────────────
# Insurance / Risk Transfer
# ─────────────────────────────────────────────────────────────────

class InsurancePolicy(Base, TimestampMixin):
    """Insurance policy record — maps coverage to enterprise risks."""
    __tablename__ = 'insurance_policies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    policy_number = Column(String(255), nullable=False)
    insurer_name = Column(String(255), nullable=False)
    policy_type = Column(String(100), nullable=True)                # cyber, D&O, E&O, property, liability, etc.
    description = Column(Text, nullable=True)

    coverage_amount = Column(Float, nullable=True)
    deductible = Column(Float, nullable=True)
    annual_premium = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True, default="USD")

    effective_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    renewal_reminder_days = Column(Integer, default=60)

    policy_owner = Column(String(255), nullable=True)
    broker_name = Column(String(255), nullable=True)
    broker_contact = Column(String(255), nullable=True)

    covered_risk_categories = Column(JSON, nullable=True)
    linked_risk_ids = Column(JSON, nullable=True)
    exclusions = Column(Text, nullable=True)
    coverage_conditions = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, default="active")
    is_active = Column(Boolean, default=True, nullable=False)
    extra = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 'policy_id': self.policy_id, 'tenant_id': self.tenant_id,
            'policy_number': self.policy_number, 'insurer_name': self.insurer_name,
            'policy_type': self.policy_type, 'description': self.description,
            'coverage_amount': self.coverage_amount, 'deductible': self.deductible,
            'annual_premium': self.annual_premium, 'currency': self.currency,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'renewal_reminder_days': self.renewal_reminder_days,
            'policy_owner': self.policy_owner, 'broker_name': self.broker_name,
            'broker_contact': self.broker_contact,
            'covered_risk_categories': self.covered_risk_categories,
            'linked_risk_ids': self.linked_risk_ids,
            'exclusions': self.exclusions, 'coverage_conditions': self.coverage_conditions,
            'status': getattr(self.status, 'value', self.status), 'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ─────────────────────────────────────────────────────────────────
# Sanctions / Watchlist Screening
# ─────────────────────────────────────────────────────────────────

class ScreeningStatus(enum.Enum):
    PENDING = "pending"
    CLEAR = "clear"
    POTENTIAL_MATCH = "potential_match"
    CONFIRMED_MATCH = "confirmed_match"
    FALSE_POSITIVE = "false_positive"


class SanctionsScreening(Base, TimestampMixin):
    """Sanctions and watchlist screening record."""
    __tablename__ = 'sanctions_screenings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    screening_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    entity_name = Column(String(500), nullable=False)
    entity_type = Column(String(50), nullable=True)                 # vendor, individual, counterparty
    entity_id = Column(String(100), nullable=True, index=True)      # vendor_id or user_id
    country = Column(String(100), nullable=True)

    lists_checked = Column(JSON, nullable=True)                     # OFAC, UN, EU, UK, etc.
    screened_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    screened_by = Column(String(255), nullable=True)                # user or "auto"
    next_screening_date = Column(DateTime, nullable=True)
    screening_frequency = Column(String(50), nullable=True)         # daily, weekly, monthly, on_change

    status = Column(String(50), nullable=False, default="pending")
    match_details = Column(JSON, nullable=True)                     # list of potential matches
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(String(255), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    extra = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 'screening_id': self.screening_id, 'tenant_id': self.tenant_id,
            'entity_name': self.entity_name, 'entity_type': self.entity_type,
            'entity_id': self.entity_id, 'country': self.country,
            'lists_checked': self.lists_checked,
            'screened_at': self.screened_at.isoformat() if self.screened_at else None,
            'screened_by': self.screened_by,
            'next_screening_date': self.next_screening_date.isoformat() if self.next_screening_date else None,
            'screening_frequency': self.screening_frequency,
            'status': getattr(self.status, 'value', self.status),
            'match_details': self.match_details, 'resolution_notes': self.resolution_notes,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
