"""
GAP-6: Continuous Monitoring Rules Engine
==========================================
General-purpose monitoring: detect unauthorized changes, missing logs,
unusual activity, interface failures across all modules.
"""
from sqlalchemy import Column, String, Text, JSON, DateTime, Integer, Boolean, Float, func
from .base import Base, TimestampMixin


class MonitoringRule(Base, TimestampMixin):
    __tablename__ = "monitoring_rules"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    rule_id = Column(String(50), nullable=False)
    name = Column(String(300), nullable=False)
    description = Column(Text)

    # What to monitor
    module = Column(String(50), nullable=False)  # access, risk, controls, compliance, audit, master_data, integration
    event_type = Column(String(100), nullable=False)  # unauthorized_change, missing_log, threshold_breach, unusual_activity, interface_failure, overdue_review
    data_source = Column(String(100))
    target_object_type = Column(String(100))

    # Rule logic
    condition_type = Column(String(50), nullable=False)  # threshold, pattern, absence, frequency, anomaly
    condition_config = Column(JSON, nullable=False)  # {field, operator, value, window_minutes, etc.}
    severity = Column(String(20), default="medium")  # low, medium, high, critical

    # Execution
    frequency_minutes = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    last_executed_at = Column(DateTime)
    last_result = Column(String(50))
    consecutive_fires = Column(Integer, default=0)

    # Response
    auto_create_issue = Column(Boolean, default=False)
    notify_roles = Column(JSON)  # list of roles to notify
    escalation_minutes = Column(Integer)
    escalation_to = Column(String(100))

    # Owner
    owner = Column(String(100))
    approved_by = Column(String(100))
    approved_at = Column(DateTime)

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}


class MonitoringAlert(Base, TimestampMixin):
    __tablename__ = "monitoring_alerts"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    alert_id = Column(String(50), nullable=False)
    rule_id = Column(String(50), nullable=False)
    rule_name = Column(String(300))

    # What triggered
    module = Column(String(50), nullable=False)
    event_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    trigger_data = Column(JSON)  # the data that matched the rule

    # Affected objects
    target_object_type = Column(String(100))
    target_object_id = Column(String(200))
    affected_user = Column(String(100))

    # Status
    status = Column(String(50), default="open")  # open, acknowledged, investigating, resolved, dismissed, escalated
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime)
    resolved_by = Column(String(100))
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)

    # Linked records
    linked_issue_id = Column(String(50))
    linked_incident_id = Column(String(50))

    # Escalation
    escalated = Column(Boolean, default=False)
    escalated_to = Column(String(100))
    escalated_at = Column(DateTime)

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}
