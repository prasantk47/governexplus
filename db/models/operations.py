"""
Database Models - Operational Modules

Models for org rules, bulk jobs, sync configuration/history,
transport records, notifications, custom tcodes, model templates,
mitigation monitoring, and ARM shopping carts.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    JSON, Float, Enum as SQLEnum
)
from datetime import datetime

from .base import Base, TimestampMixin


class OrgRule(Base, TimestampMixin):
    """
    Organizational segmentation rules.

    Defines access restrictions based on organizational fields
    such as company code, plant, purchasing org, etc.
    """
    __tablename__ = 'org_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Rule identity
    rule_id = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Organizational dimension
    # BUKRS=company code, WERKS=plant, EKORG=purchasing org,
    # VKORG=sales org, GSBER=business area, KOKRS=controlling area
    org_field = Column(String(20), nullable=False)

    # Condition definition
    condition_type = Column(String(20), nullable=False)   # equals, in_list, range, hierarchy
    condition_value = Column(String(500), nullable=False)

    # Status and priority
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=100, nullable=False)

    # Audit
    created_by = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<OrgRule(rule_id='{self.rule_id}', org_field='{self.org_field}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'name': self.name,
            'description': self.description,
            'org_field': self.org_field,
            'condition_type': self.condition_type,
            'condition_value': self.condition_value,
            'is_active': self.is_active,
            'priority': self.priority,
            'created_by': self.created_by,
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class BulkJob(Base, TimestampMixin):
    """
    Bulk operation jobs.

    Tracks asynchronous bulk operations such as role assignment,
    user locking, department changes, and role expiry/extension.
    """
    __tablename__ = 'bulk_jobs'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Job identity
    job_id = Column(String(50), nullable=False, unique=True, index=True)

    # Operation type
    # assign_role, remove_role, lock_user, unlock_user,
    # change_department, expire_role, extend_role
    operation = Column(String(50), nullable=False)

    # Lifecycle status
    status = Column(String(20), nullable=False, default='queued')  # queued, running, completed, failed, cancelled

    # Job parameters (role name, department, etc.)
    parameters = Column(JSON, nullable=True)

    # Target population
    target_users = Column(JSON, nullable=True)  # list of usernames

    # Progress counters
    total = Column(Integer, nullable=False, default=0)
    processed = Column(Integer, default=0, nullable=False)
    succeeded = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)

    # Per-user results
    results = Column(JSON, nullable=True)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Audit
    created_by = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<BulkJob(job_id='{self.job_id}', operation='{self.operation}', status='{self.status}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'operation': self.operation,
            'status': self.status,
            'parameters': self.parameters,
            'target_users': self.target_users,
            'total': self.total,
            'processed': self.processed,
            'succeeded': self.succeeded,
            'failed_count': self.failed_count,
            'results': self.results,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_by': self.created_by,
            'error_message': self.error_message,
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SyncConfig(Base, TimestampMixin):
    """
    Identity synchronisation configuration.

    Defines how and when the platform synchronises with external
    systems such as SAP, Azure AD, LDAP, and SuccessFactors.
    """
    __tablename__ = 'sync_configs'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Config identity
    config_id = Column(String(50), nullable=False, unique=True, index=True)
    system_name = Column(String(100), nullable=False)

    # System type: sap, azure_ad, ldap, successfactors
    system_type = Column(String(50), nullable=False)

    # Sync direction: inbound, outbound, bidirectional
    direction = Column(String(20), nullable=False)

    # Runtime status: active, paused, error
    status = Column(String(20), nullable=False, default='active')

    # Schedule
    schedule_minutes = Column(Integer, default=60, nullable=False)

    # Last run info
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(20), nullable=True)  # success, partial, failed
    objects_synced = Column(Integer, default=0, nullable=False)

    # Scope: {users: true, roles: true, groups: true}
    sync_scope = Column(JSON, nullable=True)

    # Connection details (encrypted at rest in production)
    connection_config = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<SyncConfig(config_id='{self.config_id}', system='{self.system_name}', status='{self.status}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'config_id': self.config_id,
            'system_name': self.system_name,
            'system_type': self.system_type,
            'direction': self.direction,
            'status': self.status,
            'schedule_minutes': self.schedule_minutes,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'last_sync_status': self.last_sync_status,
            'objects_synced': self.objects_synced,
            'sync_scope': self.sync_scope,
            # connection_config intentionally omitted from to_dict to avoid leaking credentials
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SyncHistory(Base, TimestampMixin):
    """
    Individual synchronisation run records.

    Each row represents a single sync execution initiated by a SyncConfig.
    """
    __tablename__ = 'sync_history'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Run identity
    sync_id = Column(String(50), nullable=False, unique=True, index=True)

    # Parent config reference
    config_id = Column(String(50), nullable=False, index=True)
    system_name = Column(String(100), nullable=False)

    # Direction: inbound, outbound, bidirectional
    direction = Column(String(20), nullable=False)

    # Outcome: success, partial, failed
    status = Column(String(20), nullable=False)

    # Results
    objects_synced = Column(Integer, nullable=False, default=0)
    errors = Column(JSON, nullable=True)
    duration_seconds = Column(Integer, nullable=False, default=0)

    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<SyncHistory(sync_id='{self.sync_id}', config='{self.config_id}', status='{self.status}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'sync_id': self.sync_id,
            'config_id': self.config_id,
            'system_name': self.system_name,
            'direction': self.direction,
            'status': self.status,
            'objects_synced': self.objects_synced,
            'errors': self.errors,
            'duration_seconds': self.duration_seconds,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class TransportRecord(Base, TimestampMixin):
    """
    SAP transport management records.

    Tracks the lifecycle of transports carrying roles, profiles,
    and authorisation objects across SAP landscapes.
    """
    __tablename__ = 'transport_records'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Transport identity
    transport_id = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(String(500), nullable=False)

    # Landscape
    source_system = Column(String(50), nullable=False)
    target_system = Column(String(50), nullable=False)

    # Lifecycle status: created, released, in_transit, imported, error
    status = Column(String(20), nullable=False, default='created')

    # Category: role, profile, auth_object
    category = Column(String(50), nullable=False)

    # Content
    objects = Column(JSON, nullable=True)       # list of objects in this transport
    dependencies = Column(JSON, nullable=True)  # list of transport_ids that must precede this one
    conflicts = Column(JSON, nullable=True)     # detected conflicts

    # Ownership
    owner = Column(String(50), nullable=False)

    # Timing
    released_at = Column(DateTime, nullable=True)
    imported_at = Column(DateTime, nullable=True)

    # Error details
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<TransportRecord(transport_id='{self.transport_id}', status='{self.status}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'transport_id': self.transport_id,
            'description': self.description,
            'source_system': self.source_system,
            'target_system': self.target_system,
            'status': self.status,
            'category': self.category,
            'objects': self.objects,
            'dependencies': self.dependencies,
            'conflicts': self.conflicts,
            'owner': self.owner,
            'released_at': self.released_at.isoformat() if self.released_at else None,
            'imported_at': self.imported_at.isoformat() if self.imported_at else None,
            'error_message': self.error_message,
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class NotificationRecord(Base, TimestampMixin):
    """
    Outbound notification records.

    Stores each notification dispatched via email or Slack,
    including delivery status and retry information.
    """
    __tablename__ = 'notification_records'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Notification identity
    notification_id = Column(String(50), nullable=False, unique=True, index=True)
    notification_type = Column(String(50), nullable=False)

    # Recipient
    recipient_id = Column(String(50), nullable=False)
    recipient_email = Column(String(255), nullable=True)
    recipient_slack_channel = Column(String(100), nullable=True)

    # Delivery channel: email, slack
    channel = Column(String(20), nullable=False)

    # Lifecycle status: pending, delivered, failed, retrying
    status = Column(String(20), nullable=False, default='pending')

    # Content
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    context = Column(JSON, nullable=True)  # additional structured context

    # Timing
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    # Retry tracking
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return (
            f"<NotificationRecord(notification_id='{self.notification_id}', "
            f"type='{self.notification_type}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'notification_id': self.notification_id,
            'notification_type': self.notification_type,
            'recipient_id': self.recipient_id,
            'recipient_email': self.recipient_email,
            'recipient_slack_channel': self.recipient_slack_channel,
            'channel': self.channel,
            'status': self.status,
            'subject': self.subject,
            'body': self.body,
            'context': self.context,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'retry_count': self.retry_count,
            'error_message': self.error_message,
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class NotificationPreference(Base, TimestampMixin):
    """
    Per-user notification channel preferences.

    Controls which channels are enabled and which notification
    types the user has opted out of.
    """
    __tablename__ = 'notification_preferences'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Owner
    user_id = Column(String(50), nullable=False, index=True)

    # Channel flags
    email_enabled = Column(Boolean, default=True, nullable=False)
    slack_enabled = Column(Boolean, default=False, nullable=False)
    slack_channel = Column(String(100), nullable=True)

    # Suppressed notification types (JSON list of type strings)
    disabled_types = Column(JSON, default=list, nullable=False)

    def __repr__(self):
        return f"<NotificationPreference(user_id='{self.user_id}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email_enabled': self.email_enabled,
            'slack_enabled': self.slack_enabled,
            'slack_channel': self.slack_channel,
            'disabled_types': self.disabled_types,
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CustomTcodeRecord(Base, TimestampMixin):
    """
    Custom / non-standard SAP transaction code records.

    Stores analysis results for Z/Y-tcodes and other custom
    programs that are not covered by the built-in tcode library.
    """
    __tablename__ = 'custom_tcodes'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Tcode identity
    tcode = Column(String(20), nullable=False, unique=True, index=True)
    description = Column(String(500), nullable=False)
    program = Column(String(100), nullable=False)

    # Risk classification: high, medium, low, unanalyzed
    risk_level = Column(String(20), nullable=False, default='unanalyzed')
    risk_score = Column(Integer, default=0, nullable=False)  # 0-100

    # Analysis results
    auth_objects = Column(JSON, nullable=True)         # list of auth objects used
    behavior_patterns = Column(JSON, nullable=True)    # detected behaviour patterns
    recommendations = Column(JSON, nullable=True)      # remediation recommendations

    # Usage statistics
    last_used = Column(DateTime, nullable=True)
    users_assigned = Column(Integer, default=0, nullable=False)

    # Analysis tracking
    analyzed_at = Column(DateTime, nullable=True)
    analyzed_by = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<CustomTcodeRecord(tcode='{self.tcode}', risk_level='{self.risk_level}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'tcode': self.tcode,
            'description': self.description,
            'program': self.program,
            'risk_level': self.risk_level,
            'risk_score': self.risk_score,
            'auth_objects': self.auth_objects,
            'behavior_patterns': self.behavior_patterns,
            'recommendations': self.recommendations,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'users_assigned': self.users_assigned,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'analyzed_by': self.analyzed_by,
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ModelTemplate(Base, TimestampMixin):
    """
    Access model templates.

    Pre-defined role and system bundles for specific job positions
    used to accelerate provisioning and enforce consistency.
    """
    __tablename__ = 'model_templates'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Template identity
    template_id = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Scope
    department = Column(String(100), nullable=False)
    position = Column(String(100), nullable=False)

    # Role / system bundle
    roles = Column(JSON, nullable=True)    # list of role names
    systems = Column(JSON, nullable=True)  # list of system IDs

    # Quality metrics
    compliance_rate = Column(Float, default=100.0, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit
    created_by = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<ModelTemplate(template_id='{self.template_id}', name='{self.name}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'template_id': self.template_id,
            'name': self.name,
            'description': self.description,
            'department': self.department,
            'position': self.position,
            'roles': self.roles,
            'systems': self.systems,
            'compliance_rate': self.compliance_rate,
            'usage_count': self.usage_count,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class OrgUserAssignment(Base, TimestampMixin):
    """
    Organisational-field assignments for a user within a tenant.

    One row per (tenant_id, user_id, org_field) combination.
    The `values` column holds a JSON list of SAP org-field values
    (e.g. ["1000", "1100"] for BUKRS).
    """
    __tablename__ = 'org_user_assignments'

    id         = Column(Integer,      primary_key=True, autoincrement=True)
    tenant_id  = Column(String(100),  nullable=False, index=True, default='tenant_default')
    user_id    = Column(String(100),  nullable=False, index=True)
    org_field  = Column(String(20),   nullable=False)
    values     = Column(JSON,         nullable=False, default=list)
    assigned_at = Column(DateTime,    nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<OrgUserAssignment(user='{self.user_id}', "
            f"field='{self.org_field}', tenant='{self.tenant_id}')>"
        )

    def to_dict(self) -> dict:
        return {
            'id':          self.id,
            'tenant_id':   self.tenant_id,
            'user_id':     self.user_id,
            'org_field':   self.org_field,
            'values':      self.values or [],
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
        }


class OrgRoleRestriction(Base, TimestampMixin):
    """
    Maps a role to the set of OrgRule IDs that must all be satisfied
    before a user may hold that role.

    `rule_ids` is a JSON list of rule_id strings
    (e.g. ["ORG-001", "ORG-014"]).
    """
    __tablename__ = 'org_role_restrictions'

    id        = Column(Integer,      primary_key=True, autoincrement=True)
    tenant_id = Column(String(100),  nullable=False, index=True, default='tenant_default')
    role_id   = Column(String(255),  nullable=False, index=True)
    rule_ids  = Column(JSON,         nullable=False, default=list)

    def __repr__(self) -> str:
        return (
            f"<OrgRoleRestriction(role='{self.role_id}', "
            f"tenant='{self.tenant_id}')>"
        )

    def to_dict(self) -> dict:
        return {
            'id':        self.id,
            'tenant_id': self.tenant_id,
            'role_id':   self.role_id,
            'rule_ids':  self.rule_ids or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class OrchestrationContextRecord(Base, TimestampMixin):
    """
    Persisted workflow orchestration contexts.

    Stores the serialised state of active OrchestrationContext instances
    so they survive process restarts.  The full context is kept as a JSON
    blob; lookup is by (tenant_id, context_id).
    """
    __tablename__ = 'orchestration_contexts'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Context identity (matches OrchestrationContext.request_id)
    context_id = Column(String(100), nullable=False, index=True)

    # Process type for quick filtering
    process_type = Column(String(50), nullable=False, default='ACCESS_REQUEST')

    # Workflow status snapshot for quick queries without deserialising
    workflow_status = Column(String(30), nullable=True)

    # Full serialised OrchestrationContext as JSON
    context_data = Column(JSON, nullable=False)

    def __repr__(self):
        return (
            f"<OrchestrationContextRecord(context_id='{self.context_id}', "
            f"process_type='{self.process_type}', tenant='{self.tenant_id}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'context_id': self.context_id,
            'process_type': self.process_type,
            'workflow_status': self.workflow_status,
            'context_data': self.context_data,
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class MitigationMonitorRecord(Base, TimestampMixin):
    """
    Mitigation control monitoring records.

    Tracks the operational health, expiry, and certification status
    of each active mitigation control across tenant violations.
    """
    __tablename__ = 'mitigation_monitor'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Monitor identity
    monitor_id = Column(String(50), nullable=False, unique=True, index=True)

    # Reference to mitigation_controls table
    control_id = Column(String(50), nullable=False, index=True)
    control_name = Column(String(255), nullable=False)
    control_type = Column(String(50), nullable=False)

    # Health status: active, expiring, expired, suspended
    status = Column(String(20), nullable=False, default='active')
    health_score = Column(Integer, default=100, nullable=False)  # 0-100

    # Coverage
    assigned_violations = Column(Integer, default=0, nullable=False)

    # Validity
    expiry_date = Column(DateTime, nullable=True)

    # Last review
    last_reviewed = Column(DateTime, nullable=True)
    reviewed_by = Column(String(50), nullable=True)

    # Last certification
    last_certified = Column(DateTime, nullable=True)
    certified_by = Column(String(50), nullable=True)

    # Ownership
    owner = Column(String(50), nullable=False)

    def __repr__(self):
        return (
            f"<MitigationMonitorRecord(monitor_id='{self.monitor_id}', "
            f"control_id='{self.control_id}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'monitor_id': self.monitor_id,
            'control_id': self.control_id,
            'control_name': self.control_name,
            'control_type': self.control_type,
            'status': self.status,
            'health_score': self.health_score,
            'assigned_violations': self.assigned_violations,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'last_reviewed': self.last_reviewed.isoformat() if self.last_reviewed else None,
            'reviewed_by': self.reviewed_by,
            'last_certified': self.last_certified.isoformat() if self.last_certified else None,
            'certified_by': self.certified_by,
            'owner': self.owner,
            'tenant_id': self.tenant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ShoppingCartModel(Base):
    """
    ARM Shopping Cart persistence.

    Stores the serialised state of each shopping cart so that carts
    survive process restarts.  The items are kept as a JSON text blob
    containing the full CartItem.to_dict() representations, including
    the embedded catalog_item data, so the cart can be fully
    reconstructed without hitting the catalog again.

    Lifecycle statuses mirror CartStatus:
        open       — draft / checking / ready (mutable)
        submitted  — permanently submitted, read-only
        cancelled  — cancelled / deleted
    """
    __tablename__ = "shopping_carts"

    # Primary key is the cart UUID generated by ShoppingCart
    id = Column(String(100), primary_key=True)

    # Owner
    requester_id = Column(String(100), nullable=False, index=True)

    # Multi-tenant support
    tenant_id = Column(String(100), nullable=False, default="tenant_default", index=True)

    # Coarse lifecycle status for quick queries
    # Values: open | submitted | cancelled
    status = Column(String(20), nullable=False, default="open")

    # Full serialised CartItem list as a JSON text blob.
    # Each element is the dict produced by CartItem.to_dict(), which
    # embeds the catalog_item dict so reconstruction is self-contained.
    items_json = Column(Text, nullable=False, default="[]")

    # ISO timestamps carried from ShoppingCart (set by the application)
    cart_created_at = Column(String(50), nullable=True)
    cart_updated_at = Column(String(50), nullable=True)

    # Row-level timestamps managed by SQLAlchemy
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return (
            f"<ShoppingCartModel(id='{self.id}', "
            f"requester='{self.requester_id}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'requester_id': self.requester_id,
            'tenant_id': self.tenant_id,
            'status': self.status,
            'items_json': self.items_json,
            'cart_created_at': self.cart_created_at,
            'cart_updated_at': self.cart_updated_at,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
