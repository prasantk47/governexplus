"""
Database Models - Intelligence / Knowledge-Base Modules

Models for the nine intelligence modules that previously used in-memory mock data:
Access Troubleshooter, Role Intelligence, Role Drift Detection, Fiori Security Analyzer,
Identity Correlation, Migration Analyzer, Access Timeline, and Audit Evidence Center.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    JSON, Float, Enum as SQLEnum
)
from datetime import datetime

from .base import Base, TimestampMixin


# ---------------------------------------------------------------------------
# 1. Access Troubleshooter – SAP User knowledge base
# ---------------------------------------------------------------------------

class TroubleshooterKBUser(Base, TimestampMixin):
    """
    Mock SAP user records used by the Access Troubleshooter diagnostic engine.

    Stores user status, assigned roles, and organisational context so the
    12-step diagnostic chain can query them without hitting a live SAP system.
    """
    __tablename__ = 'troubleshooter_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # SAP user identity
    user_ext_id = Column(String(20), nullable=False, index=True)   # e.g. JDOE
    full_name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=True)

    # Account status
    status = Column(String(20), nullable=False, default='active')  # active | locked | expired

    # Validity period
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)

    # Role assignment (list of role name strings)
    roles = Column(JSON, nullable=True)

    # Target system
    system = Column(String(20), nullable=False, default='PRD')

    def __repr__(self):
        return f"<TroubleshooterKBUser(user_ext_id='{self.user_ext_id}', system='{self.system}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'user_ext_id': self.user_ext_id,
            'full_name': self.full_name,
            'department': self.department,
            'status': self.status,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'roles': self.roles,
            'system': self.system,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# 2. Access Troubleshooter – SAP Role knowledge base
# ---------------------------------------------------------------------------

class TroubleshooterKBRole(Base, TimestampMixin):
    """
    Mock SAP role definitions used by the Access Troubleshooter.

    Captures the transactions, authorisation objects, org levels, and system
    deployment scope of each role so the diagnostic chain can verify whether
    a user's roles grant the requested access.
    """
    __tablename__ = 'troubleshooter_roles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Role identity
    role_name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    role_type = Column(String(20), nullable=False, default='single')  # single | composite

    # Role contents
    transactions = Column(JSON, nullable=True)    # list of tcode strings
    auth_objects = Column(JSON, nullable=True)    # list of {object, field, values}
    org_levels = Column(JSON, nullable=True)

    # Deployment scope (e.g. ["DEV", "QA", "PRD"])
    systems_deployed = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<TroubleshooterKBRole(role_name='{self.role_name}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'role_name': self.role_name,
            'description': self.description,
            'role_type': self.role_type,
            'transactions': self.transactions,
            'auth_objects': self.auth_objects,
            'org_levels': self.org_levels,
            'systems_deployed': self.systems_deployed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# 3. Access Troubleshooter – Transaction knowledge base
# ---------------------------------------------------------------------------

class TroubleshooterKBTransaction(Base, TimestampMixin):
    """
    SAP transaction code knowledge base for the Access Troubleshooter.

    Records which authorisation objects and field values are required to
    execute each transaction so the engine can explain exactly why access
    is being denied.
    """
    __tablename__ = 'troubleshooter_transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Transaction identity
    tcode = Column(String(20), nullable=False, unique=True, index=True)
    description = Column(String(500), nullable=True)
    module = Column(String(20), nullable=True)          # FI | FI-AP | MM | SD | HR | …

    # Risk flag
    is_sensitive = Column(Boolean, nullable=False, default=False)

    # Auth requirements: list of {auth_object, field, required_values}
    auth_requirements = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<TroubleshooterKBTransaction(tcode='{self.tcode}', module='{self.module}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'tcode': self.tcode,
            'description': self.description,
            'module': self.module,
            'is_sensitive': self.is_sensitive,
            'auth_requirements': self.auth_requirements,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# 4. Role Intelligence – Role catalog
# ---------------------------------------------------------------------------

class RoleIntelligenceRecord(Base, TimestampMixin):
    """
    Role catalog used by the Role Intelligence engine.

    Stores enriched metadata for each role — usage statistics, SoD conflict
    flags, risk level, and naming-convention compliance — so the engine can
    produce similarity scores, deduplication candidates, and health reports
    without querying the live SAP system on every request.
    """
    __tablename__ = 'role_intelligence'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Role identity
    role_name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    role_type = Column(String(20), nullable=False, default='single')  # single | composite | derived

    # Ownership / classification
    owner = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)

    # Role contents
    transactions = Column(JSON, nullable=True)   # list of tcode strings
    auth_objects = Column(JSON, nullable=True)   # list of auth object name strings
    org_values = Column(JSON, nullable=True)     # dict mapping org-key -> list of values
                                                 # e.g. {"BUKRS": ["1000", "2000"]}

    # Usage metrics
    user_count = Column(Integer, nullable=False, default=0)
    last_used = Column(DateTime, nullable=True)

    # Risk / compliance flags
    has_sod_conflicts = Column(Boolean, nullable=False, default=False)
    risk_level = Column(String(20), nullable=False, default='low')   # low | medium | high | critical
    naming_convention_ok = Column(Boolean, nullable=False, default=True)

    # Source system
    system = Column(String(20), nullable=False, default='PRD')

    # Business process / module grouping (FI | MM | SD | HR | BASIS | …)
    business_process = Column(String(50), nullable=True)

    # Seed tracking: True for records inserted by the engine seed routine
    is_seed = Column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<RoleIntelligenceRecord(role_name='{self.role_name}', system='{self.system}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'role_name': self.role_name,
            'description': self.description,
            'role_type': self.role_type,
            'owner': self.owner,
            'department': self.department,
            'transactions': self.transactions,
            'auth_objects': self.auth_objects,
            'org_values': self.org_values,
            'user_count': self.user_count,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'has_sod_conflicts': self.has_sod_conflicts,
            'risk_level': self.risk_level,
            'naming_convention_ok': self.naming_convention_ok,
            'system': self.system,
            'business_process': self.business_process,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_catalogue_dict(self) -> dict:
        """
        Return the record in the shape expected by RoleIntelligenceEngine
        internal helpers (matches the original _ROLE_CATALOGUE entry format).
        """
        return {
            # Engine uses role_name as the logical identifier
            "id": self.role_name,
            "db_id": self.id,
            "name": self.role_name,
            "type": self.role_type,
            "owner": self.owner,
            "description": self.description or "",
            "user_count": self.user_count,
            "last_used": self.last_used,
            "transactions": self.transactions or [],
            "auth_objects": self.auth_objects or [],
            "org_values": self.org_values or {},
            "has_sod_conflict": self.has_sod_conflicts,
            "business_process": self.business_process or "UNKNOWN",
        }


# ---------------------------------------------------------------------------
# 5. Role Drift Detection – System snapshots
# ---------------------------------------------------------------------------

class DriftSnapshot(Base, TimestampMixin):
    """
    Point-in-time snapshot of a role in a specific system landscape tier.

    The drift detection engine compares SHA-256 hashes across DEV / QA / PRD
    snapshots to identify unauthorised or unintended divergence.
    """
    __tablename__ = 'drift_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Snapshot identity
    snapshot_id = Column(String(50), nullable=False, unique=True, index=True)
    role_name = Column(String(100), nullable=False, index=True)
    system = Column(String(20), nullable=False)   # DEV | QA | PRD

    # Content hash for fast comparison
    snapshot_hash = Column(String(64), nullable=False)   # SHA-256

    # Role definition at snapshot time
    transactions = Column(JSON, nullable=True)
    auth_objects = Column(JSON, nullable=True)
    org_levels = Column(JSON, nullable=True)
    menu_nodes = Column(JSON, nullable=True)

    # When the snapshot was taken
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<DriftSnapshot(snapshot_id='{self.snapshot_id}', "
            f"role='{self.role_name}', system='{self.system}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'snapshot_id': self.snapshot_id,
            'role_name': self.role_name,
            'system': self.system,
            'snapshot_hash': self.snapshot_hash,
            'transactions': self.transactions,
            'auth_objects': self.auth_objects,
            'org_levels': self.org_levels,
            'menu_nodes': self.menu_nodes,
            'captured_at': self.captured_at.isoformat() if self.captured_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# 6. Fiori Security Analyzer – Application catalog
# ---------------------------------------------------------------------------

class FioriAppRecord(Base, TimestampMixin):
    """
    Fiori application catalog for the Fiori Security Analyzer.

    Each record captures the full 8-layer authorisation chain for a Fiori app:
    catalog, space, OData services, backend RFC transactions, and the explicit
    authorisation objects required end-to-end.
    """
    __tablename__ = 'fiori_apps'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Application identity
    app_id = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Launchpad hierarchy
    catalog_id = Column(String(100), nullable=True)
    catalog_name = Column(String(255), nullable=True)
    space_id = Column(String(100), nullable=True)

    # Backend links
    odata_services = Column(JSON, nullable=True)           # list of service names
    backend_transactions = Column(JSON, nullable=True)     # list of tcode strings

    # Auth requirements
    required_auth_objects = Column(JSON, nullable=True)    # list of auth object dicts

    # Navigation / target mapping
    target_mapping_id = Column(String(100), nullable=True)
    semantic_object = Column(String(100), nullable=True)
    semantic_action = Column(String(100), nullable=True)

    # Risk classification
    risk_level = Column(String(20), nullable=True)         # low | medium | high | critical
    business_area = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<FioriAppRecord(app_id='{self.app_id}', name='{self.name}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'app_id': self.app_id,
            'name': self.name,
            'description': self.description,
            'catalog_id': self.catalog_id,
            'catalog_name': self.catalog_name,
            'space_id': self.space_id,
            'odata_services': self.odata_services,
            'backend_transactions': self.backend_transactions,
            'required_auth_objects': self.required_auth_objects,
            'target_mapping_id': self.target_mapping_id,
            'semantic_object': self.semantic_object,
            'semantic_action': self.semantic_action,
            'risk_level': self.risk_level,
            'business_area': self.business_area,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# 7. Identity Correlation – Individual accounts
# ---------------------------------------------------------------------------

class IdentityAccount(Base, TimestampMixin):
    """
    Cross-system identity account record.

    Represents a single account in any connected system (SAP ECC, Azure AD,
    SuccessFactors, Active Directory, …).  Multiple IdentityAccount rows are
    grouped into an IdentityClusterRecord to represent one real person.
    """
    __tablename__ = 'identity_accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Account identity
    account_id = Column(String(50), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    employee_id = Column(String(50), nullable=True)

    # Source system
    system_type = Column(
        String(50), nullable=False
    )  # sap_ecc | azure_ad | successfactors | active_directory

    # Account status
    status = Column(String(20), nullable=False, default='active')  # active | inactive | locked | disabled

    # HR context
    department = Column(String(100), nullable=True)
    job_title = Column(String(255), nullable=True)

    # Activity
    last_login = Column(DateTime, nullable=True)

    # Entitlements (roles, groups, etc.)
    entitlements = Column(JSON, nullable=True)

    def __repr__(self):
        return (
            f"<IdentityAccount(account_id='{self.account_id}', "
            f"system='{self.system_type}', username='{self.username}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'account_id': self.account_id,
            'username': self.username,
            'display_name': self.display_name,
            'email': self.email,
            'employee_id': self.employee_id,
            'system_type': self.system_type,
            'status': self.status,
            'department': self.department,
            'job_title': self.job_title,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'entitlements': self.entitlements,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# 8. Identity Correlation – Correlated identity clusters
# ---------------------------------------------------------------------------

class IdentityClusterRecord(Base, TimestampMixin):
    """
    Correlated identity cluster — a single real person represented across
    multiple systems.

    The correlation engine groups IdentityAccount records by matching on
    employee ID, email address, or display-name similarity and computes a
    confidence score.  Anomalies (e.g. cross-system SoD conflicts or stale
    accounts) are stored in the anomalies JSON field.
    """
    __tablename__ = 'identity_clusters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Cluster identity
    cluster_id = Column(String(50), nullable=False, unique=True, index=True)
    canonical_name = Column(String(255), nullable=False)
    canonical_email = Column(String(255), nullable=True)
    employee_id = Column(String(50), nullable=True)
    department = Column(String(100), nullable=True)

    # Member accounts (list of account_id strings)
    account_ids = Column(JSON, nullable=False, default=list)

    # Correlation metadata
    correlation_confidence = Column(Float, nullable=False, default=1.0)  # 0.0 – 1.0
    risk_level = Column(String(20), nullable=False, default='low')
    anomalies = Column(JSON, nullable=True)

    # Maintenance
    last_correlated = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<IdentityClusterRecord(cluster_id='{self.cluster_id}', "
            f"name='{self.canonical_name}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'cluster_id': self.cluster_id,
            'canonical_name': self.canonical_name,
            'canonical_email': self.canonical_email,
            'employee_id': self.employee_id,
            'department': self.department,
            'account_ids': self.account_ids,
            'correlation_confidence': self.correlation_confidence,
            'risk_level': self.risk_level,
            'anomalies': self.anomalies,
            'last_correlated': self.last_correlated.isoformat() if self.last_correlated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# 9. Migration Analyzer – ECC to S/4 transaction mappings
# ---------------------------------------------------------------------------

class MigrationMapping(Base, TimestampMixin):
    """
    ECC → S/4HANA transaction code mapping for the Migration Analyzer.

    Covers 60+ mappings including replaced, Fiori-only, and removed
    transactions so the engine can assess role migration impact without a
    live S/4 connection.
    """
    __tablename__ = 'migration_mappings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Source / target
    ecc_tcode = Column(String(20), nullable=False, index=True)
    s4_tcode = Column(String(20), nullable=True)   # None when removed or Fiori-only

    # Migration status
    status = Column(
        String(20), nullable=False
    )  # compatible | replaced | fiori_only | removed | new

    # Fiori replacement apps (list of app_id strings)
    fiori_app_ids = Column(JSON, nullable=True)

    # Human-readable migration guidance
    notes = Column(Text, nullable=True)

    # Business context
    business_process = Column(String(100), nullable=True)
    risk_level = Column(String(20), nullable=True)   # low | medium | high | critical

    def __repr__(self):
        return (
            f"<MigrationMapping(ecc='{self.ecc_tcode}', s4='{self.s4_tcode}', "
            f"status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'ecc_tcode': self.ecc_tcode,
            's4_tcode': self.s4_tcode,
            'status': self.status,
            'fiori_app_ids': self.fiori_app_ids,
            'notes': self.notes,
            'business_process': self.business_process,
            'risk_level': self.risk_level,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# 10. Access Timeline – Change events
# ---------------------------------------------------------------------------

class TimelineEvent(Base, TimestampMixin):
    """
    Immutable record of a user or role access-change event.

    Used by the Access Timeline module to reconstruct when a user gained or
    lost access, who performed the action, and on which system — enabling
    both access-loss investigations and forensic audit trails.
    """
    __tablename__ = 'timeline_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Event identity
    event_id = Column(String(50), nullable=False, unique=True, index=True)

    # Event classification
    event_type = Column(
        String(50), nullable=False
    )  # role_assigned | role_removed | user_created | user_locked | …

    # Subject
    user_ext_id = Column(String(50), nullable=False, index=True)
    username = Column(String(100), nullable=True)

    # Object of the change (e.g. role name, tcode, system ID)
    target_object = Column(String(255), nullable=True)

    # Free-text detail / JSON payload
    detail = Column(Text, nullable=True)

    # Actor
    performed_by = Column(String(100), nullable=True)

    # Source landscape
    system = Column(String(50), nullable=True)

    # When the event actually occurred in the source system
    event_timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<TimelineEvent(event_id='{self.event_id}', type='{self.event_type}', "
            f"user='{self.user_ext_id}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'event_id': self.event_id,
            'event_type': self.event_type,
            'user_ext_id': self.user_ext_id,
            'username': self.username,
            'target_object': self.target_object,
            'detail': self.detail,
            'performed_by': self.performed_by,
            'system': self.system,
            'event_timestamp': self.event_timestamp.isoformat() if self.event_timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# 11. Audit Evidence Center – Evidence items
# ---------------------------------------------------------------------------

class AuditEvidenceItem(Base, TimestampMixin):
    """
    Structured audit evidence record for the Audit Evidence Center.

    Evidence items are categorised, tagged with a compliance framework, and
    carry a validity window so the one-click evidence-package generator can
    assemble current, in-scope evidence for SOX, ISO 27001, GDPR, and other
    frameworks automatically.
    """
    __tablename__ = 'audit_evidence'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True, default='tenant_default')

    # Evidence identity
    evidence_id = Column(String(50), nullable=False, unique=True, index=True)

    # Classification
    category = Column(
        String(50), nullable=False
    )  # user_access | role_changes | approvals | sod_violations |
    #    mitigations | firefighter | certifications | provisioning

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Origin
    source_system = Column(String(100), nullable=True)
    compliance_framework = Column(String(100), nullable=True)   # SOX | ISO27001 | GDPR | …

    # Payload — flexible JSON bag holding the actual evidence data
    evidence_data = Column(JSON, nullable=True)

    # Validity window
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)

    # Lifecycle
    status = Column(String(20), nullable=False, default='current')  # current | archived | expired

    def __repr__(self):
        return (
            f"<AuditEvidenceItem(evidence_id='{self.evidence_id}', "
            f"category='{self.category}', status='{self.status}')>"
        )

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'evidence_id': self.evidence_id,
            'category': self.category,
            'title': self.title,
            'description': self.description,
            'source_system': self.source_system,
            'compliance_framework': self.compliance_framework,
            'evidence_data': self.evidence_data,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
