"""
GAP-2: GRC Platform Configuration Logging
==========================================
Track changes to GRC config: SoD rules, KRI thresholds, control defs,
workflow routing, approval matrix, scoring methodology.
Versioned config + maker-checker + privileged activity report.
"""
from sqlalchemy import Column, String, Text, JSON, DateTime, Integer, Boolean, func
from .base import Base, TimestampMixin


class ConfigChangeLog(Base, TimestampMixin):
    """Immutable log of every GRC configuration change."""
    __tablename__ = "config_change_logs"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    event_id = Column(String(50), nullable=False, unique=True)
    event_type = Column(String(50), nullable=False)  # create/update/delete/approve/reject/override

    # What changed
    module = Column(String(50), nullable=False)  # access_control, risk_mgmt, process_control, etc.
    object_type = Column(String(100), nullable=False)  # sod_rule, kri_threshold, control_def, workflow, etc.
    object_id = Column(String(200), nullable=False)
    object_name = Column(String(300))

    # Before / after
    before_value = Column(JSON)
    after_value = Column(JSON)
    changed_fields = Column(JSON)  # list of field names that changed

    # Actor
    actor = Column(String(100), nullable=False)
    actor_role = Column(String(100))
    delegated_by = Column(String(100))
    source = Column(String(50), default="ui")  # ui, api, batch, integration

    # Approval (maker-checker)
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(String(100))
    approved_at = Column(DateTime)
    change_request_id = Column(String(50))

    # Context
    reason = Column(Text)
    ip_address = Column(String(50))
    session_id = Column(String(100))

    # Integrity
    checksum = Column(String(128))  # SHA-256 of event payload
    sequence_number = Column(Integer)

    # Outcome
    result = Column(String(50), default="success")  # success, failure, blocked, overridden
    error_details = Column(Text)

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}


class ConfigVersion(Base, TimestampMixin):
    """Versioned snapshots of GRC configuration objects."""
    __tablename__ = "config_versions"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    module = Column(String(50), nullable=False)
    object_type = Column(String(100), nullable=False)
    object_id = Column(String(200), nullable=False)
    version_number = Column(Integer, nullable=False)
    config_snapshot = Column(JSON, nullable=False)
    changed_by = Column(String(100), nullable=False)
    change_reason = Column(Text)
    change_request_id = Column(String(50))
    is_active = Column(Boolean, default=True)
    deployed_at = Column(DateTime)
    deployed_by = Column(String(100))

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}
