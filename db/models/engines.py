"""
DB models for the 4 core engines:
- Evidence (hash-chained audit trail)
- Findings (unified risk findings)
- Execution (provisioning plans)
- Decision (approval workflows)

Uses JSON columns for nested structures to keep schema simple.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, JSON
from db.models.base import Base, TimestampMixin


class EvidenceRecord(Base, TimestampMixin):
    """Hash-chained evidence record for the Evidence Engine."""
    __tablename__ = "engine_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evidence_id = Column(String(100), nullable=False, unique=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    evidence_type = Column(String(50), nullable=False)
    actor_user_id = Column(String(100), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Target
    target_user_id = Column(String(100), nullable=True, index=True)
    target_object_type = Column(String(100), nullable=True)
    target_object_id = Column(String(200), nullable=True)

    # Links
    request_id = Column(String(100), nullable=True, index=True)
    workflow_id = Column(String(100), nullable=True)
    finding_id = Column(String(100), nullable=True)
    plan_id = Column(String(100), nullable=True)
    campaign_id = Column(String(100), nullable=True)
    session_id = Column(String(100), nullable=True)

    # State snapshots (JSON)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    action_details = Column(JSON, nullable=True)
    system_response = Column(JSON, nullable=True)

    # Hash chain integrity
    previous_hash = Column(String(128), nullable=True)
    record_hash = Column(String(128), nullable=False)
    integrity = Column(String(20), nullable=False, default="valid")

    def __repr__(self):
        return f"<EvidenceRecord({self.evidence_id}, {self.action})>"


class FindingRecord(Base, TimestampMixin):
    """Unified risk finding from the Findings Engine."""
    __tablename__ = "engine_findings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    finding_id = Column(String(100), nullable=False, unique=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    finding_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    source = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="open")

    # Target
    user_id = Column(String(100), nullable=True, index=True)
    system_id = Column(String(100), nullable=True)

    # Description
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)

    # Risk
    risk_score = Column(Float, nullable=True)
    business_impact = Column(String(50), nullable=True)
    sox_relevant = Column(Boolean, default=False)

    # Links
    rule_id = Column(String(100), nullable=True)
    violation_id = Column(String(100), nullable=True)
    campaign_id = Column(String(100), nullable=True)
    request_id = Column(String(100), nullable=True)

    # Nested data (JSON)
    related_roles = Column(JSON, nullable=True)
    related_transactions = Column(JSON, nullable=True)
    related_auth_objects = Column(JSON, nullable=True)
    org_scope = Column(JSON, nullable=True)
    regulatory_refs = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    evidence_ids = Column(JSON, nullable=True)

    # Resolution
    detected_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<FindingRecord({self.finding_id}, {self.severity})>"


class ExecutionPlanRecord(Base, TimestampMixin):
    """Provisioning execution plan from the Execution Engine."""
    __tablename__ = "engine_execution_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(String(100), nullable=False, unique=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    workflow_id = Column(String(100), nullable=True)
    user_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    phase = Column(String(30), nullable=False, default="planned")
    execution_mode = Column(String(20), nullable=True)
    executed_by = Column(String(100), nullable=True)

    # Risk snapshots
    pre_risk_score = Column(Float, nullable=True)
    pre_violation_count = Column(Integer, nullable=True)
    post_risk_score = Column(Float, nullable=True)
    post_violation_count = Column(Integer, nullable=True)

    # Actions (JSON array of action dicts)
    actions = Column(JSON, nullable=True)

    # Timestamps
    simulated_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ExecutionPlanRecord({self.plan_id}, {self.phase})>"


class DecisionWorkflowRecord(Base, TimestampMixin):
    """Approval workflow from the Decision Engine."""
    __tablename__ = "engine_decision_workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(100), nullable=False, unique=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    request_type = Column(String(50), nullable=True)
    policy_id = Column(String(100), nullable=True)
    user_id = Column(String(100), nullable=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    # State
    current_step = Column(Integer, default=0)
    is_complete = Column(Boolean, default=False)
    final_decision = Column(String(20), nullable=True)  # approved, rejected

    # Risk snapshot
    risk_score = Column(Float, nullable=True)
    sod_violations_count = Column(Integer, nullable=True)
    new_violations_count = Column(Integer, nullable=True)

    # Steps (JSON array of step dicts)
    steps = Column(JSON, nullable=True)
    context = Column(JSON, nullable=True)

    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<DecisionWorkflowRecord({self.workflow_id}, {self.final_decision})>"
