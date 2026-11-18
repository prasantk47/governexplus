"""
License Intelligence Module — Database Models
16 tables covering FUE classification, contracts, usage, reclamation, and rule packs.
All tables are tenant-scoped via tenant_id.
"""
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date,
    Text, JSON, ForeignKey, Index, UniqueConstraint,
)
from .base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class FUEUseType(str, enum.Enum):
    advanced = "advanced"
    core = "core"
    self_service = "self_service"
    developer = "developer"
    unclassified = "unclassified"


class RulePackStatus(str, enum.Enum):
    draft = "draft"
    review = "review"
    approved = "approved"
    active = "active"
    superseded = "superseded"
    archived = "archived"


class ReclamationStatus(str, enum.Enum):
    candidate = "candidate"
    under_review = "under_review"
    approved = "approved"
    executing = "executing"
    completed = "completed"
    rejected = "rejected"
    exception = "exception"


class ReclamationTrigger(str, enum.Enum):
    termination = "termination"
    transfer = "transfer"
    contractor_end = "contractor_end"
    inactivity = "inactivity"
    duplicate_identity = "duplicate_identity"
    orphaned_account = "orphaned_account"
    manual = "manual"


class ContractStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    expired = "expired"
    renewed = "renewed"
    terminated = "terminated"


class CountingRule(str, enum.Enum):
    highest_across_systems = "highest_across_systems"
    per_system = "per_system"
    named_user = "named_user"


# ── LI-008: Rule Pack Management ─────────────────────────────────────────────

class LIRulePack(Base, TimestampMixin):
    """Master rule pack definition — versioned, effective-dated."""
    __tablename__ = "li_rule_packs"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    target_platform = Column(String(50), default="S4HANA")  # S4HANA, ECC, PUBLIC
    is_base_pack = Column(Boolean, default=False)
    status = Column(String(30), default="draft")
    created_by = Column(String(100))
    approved_by = Column(String(100))
    approved_at = Column(DateTime)

    __table_args__ = (
        Index("ix_li_rule_packs_tenant", "tenant_id"),
    )


class LIRulePackVersion(Base, TimestampMixin):
    """Versioned snapshot of a rule pack."""
    __tablename__ = "li_rule_pack_versions"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    rule_pack_id = Column(String(50), ForeignKey("li_rule_packs.id"), nullable=False)
    version = Column(String(20), nullable=False)  # e.g., "1.0.0"
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    conversion_ratios = Column(JSON, nullable=False)
    # Default: {"advanced": 1.0, "core": 0.2, "self_service": 0.0333, "developer": 1.0}
    notes = Column(Text)
    status = Column(String(30), default="draft")
    drafted_by = Column(String(100))
    reviewed_by = Column(String(100))
    approved_by = Column(String(100))
    approved_at = Column(DateTime)
    mapping_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("rule_pack_id", "version", name="uq_li_rpv_pack_version"),
        Index("ix_li_rpv_tenant", "tenant_id"),
    )


class LIAuthMapping(Base, TimestampMixin):
    """Maps an authorization object/field/value to a FUE use type."""
    __tablename__ = "li_auth_mappings"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    rule_pack_version_id = Column(String(50), ForeignKey("li_rule_pack_versions.id"), nullable=False)
    auth_object = Column(String(50), nullable=False)   # e.g., S_TCODE
    auth_field = Column(String(50))                      # e.g., TCD
    auth_value = Column(String(200))                     # e.g., FB01, wildcard *
    auth_value_pattern = Column(String(200))             # regex/glob for flexible matching
    mapped_use_type = Column(String(30), nullable=False) # advanced, core, self_service, developer
    source_reference = Column(String(500))               # SAP doc reference
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=100)              # higher = overrides lower

    __table_args__ = (
        Index("ix_li_am_tenant_rpv", "tenant_id", "rule_pack_version_id"),
        Index("ix_li_am_auth", "auth_object", "auth_field"),
    )


class LITenantOverride(Base, TimestampMixin):
    """Per-tenant override of a base rule pack mapping (contract-specific)."""
    __tablename__ = "li_tenant_overrides"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    base_mapping_id = Column(String(50), ForeignKey("li_auth_mappings.id"))
    auth_object = Column(String(50), nullable=False)
    auth_field = Column(String(50))
    auth_value = Column(String(200))
    override_use_type = Column(String(30), nullable=False)
    justification = Column(Text, nullable=False)
    contract_reference = Column(String(200))
    approved_by = Column(String(100))
    approved_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("ix_li_to_tenant", "tenant_id"),
    )


# ── LI-005: Contract Entitlement Repository ──────────────────────────────────

class LIContract(Base, TimestampMixin):
    """SAP license contract with FUE entitlements."""
    __tablename__ = "li_contracts"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    contract_reference = Column(String(200), nullable=False)
    contract_type = Column(String(50), default="S4HANA_FUE")
    status = Column(String(30), default="active")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    renewal_date = Column(Date)
    contracted_fue = Column(Float, nullable=False)
    price_per_fue = Column(Float)
    currency = Column(String(10), default="USD")
    conversion_ratios = Column(JSON)
    # Override ratios for this contract; null = use rule pack defaults
    counting_rule = Column(String(50), default="highest_across_systems")
    developer_terms = Column(Text)
    use_type_definitions = Column(JSON)
    system_ids = Column(JSON)  # List of connected system IDs under this contract
    rule_pack_version_id = Column(String(50), ForeignKey("li_rule_pack_versions.id"))
    alert_threshold_pct = Column(Float, default=85.0)  # Alert when utilisation exceeds this
    notes = Column(Text)

    __table_args__ = (
        Index("ix_li_contracts_tenant", "tenant_id"),
    )


class LIContractAmendment(Base, TimestampMixin):
    """Amendment history for a contract."""
    __tablename__ = "li_contract_amendments"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    contract_id = Column(String(50), ForeignKey("li_contracts.id"), nullable=False)
    amendment_date = Column(Date, nullable=False)
    amendment_type = Column(String(50))  # increase, decrease, renewal, ratio_change
    previous_values = Column(JSON)
    new_values = Column(JSON)
    reason = Column(Text)
    amended_by = Column(String(100))

    __table_args__ = (
        Index("ix_li_ca_contract", "contract_id"),
    )


class LIEntitlementSnapshot(Base, TimestampMixin):
    """Point-in-time snapshot of contract entitlements."""
    __tablename__ = "li_entitlement_snapshots"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    contract_id = Column(String(50), ForeignKey("li_contracts.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    contracted_fue = Column(Float, nullable=False)
    conversion_ratios = Column(JSON, nullable=False)
    counting_rule = Column(String(50))
    system_ids = Column(JSON)

    __table_args__ = (
        Index("ix_li_es_contract_date", "contract_id", "snapshot_date"),
    )


# ── LI-001: FUE Classification ───────────────────────────────────────────────

class LIClassification(Base, TimestampMixin):
    """FUE classification result per user."""
    __tablename__ = "li_classifications"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False)        # FK to users table
    username = Column(String(100), nullable=False)
    system_id = Column(String(50))
    use_type = Column(String(30), nullable=False)         # advanced, core, self_service, developer, unclassified
    fue_value = Column(Float, nullable=False)              # e.g., 1.0, 0.2, 0.0333
    rule_pack_version_id = Column(String(50), ForeignKey("li_rule_pack_versions.id"))
    calculation_date = Column(DateTime, nullable=False)
    is_current = Column(Boolean, default=True)
    previous_use_type = Column(String(30))
    previous_fue_value = Column(Float)
    change_reason = Column(String(200))
    is_flagged = Column(Boolean, default=False)            # True if engine couldn't classify
    flag_reason = Column(String(500))
    department = Column(String(100))
    business_unit = Column(String(100))
    cost_center = Column(String(50))
    last_activity_date = Column(DateTime)
    inactive_days = Column(Integer)
    is_review_candidate = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_li_cls_tenant_user", "tenant_id", "username"),
        Index("ix_li_cls_tenant_current", "tenant_id", "is_current"),
        Index("ix_li_cls_use_type", "tenant_id", "use_type"),
    )


class LIClassificationDriver(Base, TimestampMixin):
    """The specific role/auth that caused a user's classification."""
    __tablename__ = "li_classification_drivers"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    classification_id = Column(String(50), ForeignKey("li_classifications.id"), nullable=False)
    role_name = Column(String(100), nullable=False)
    auth_object = Column(String(50), nullable=False)
    auth_field = Column(String(50))
    auth_value = Column(String(200))
    mapped_use_type = Column(String(30), nullable=False)
    mapping_id = Column(String(50))                        # ref to li_auth_mappings
    was_used_in_period = Column(Boolean)                   # True if this auth was actually exercised
    last_used_date = Column(DateTime)
    use_type_without_this = Column(String(30))             # What type the user would be without this driver
    fue_difference = Column(Float)                         # FUE saving if removed

    __table_args__ = (
        Index("ix_li_cd_classification", "classification_id"),
        Index("ix_li_cd_tenant", "tenant_id"),
    )


# ── LI-002: Consumption Snapshots ────────────────────────────────────────────

class LIConsumptionSnapshot(Base, TimestampMixin):
    """Point-in-time FUE consumption calculation."""
    __tablename__ = "li_consumption_snapshots"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    contract_id = Column(String(50), ForeignKey("li_contracts.id"), nullable=False)
    snapshot_date = Column(DateTime, nullable=False)
    rule_pack_version_id = Column(String(50))
    total_users = Column(Integer, nullable=False, default=0)
    advanced_count = Column(Integer, default=0)
    core_count = Column(Integer, default=0)
    self_service_count = Column(Integer, default=0)
    developer_count = Column(Integer, default=0)
    unclassified_count = Column(Integer, default=0)
    consumed_fue = Column(Float, nullable=False, default=0.0)
    contracted_fue = Column(Float, nullable=False, default=0.0)
    available_fue = Column(Float, default=0.0)
    utilisation_pct = Column(Float, default=0.0)
    over_consumed = Column(Boolean, default=False)
    by_system = Column(JSON)         # {system_id: {advanced: N, core: N, ...}}
    by_business_unit = Column(JSON)  # {unit: {advanced: N, core: N, ...}}
    by_department = Column(JSON)     # {dept: {advanced: N, ...}}
    by_cost_center = Column(JSON)    # {cc: {advanced: N, ...}}
    calculation_inputs = Column(JSON)  # Stored for reproducibility
    is_latest = Column(Boolean, default=True)

    __table_args__ = (
        Index("ix_li_cs_tenant_contract", "tenant_id", "contract_id"),
        Index("ix_li_cs_date", "snapshot_date"),
    )


# ── LI-003: Usage Data ───────────────────────────────────────────────────────

class LIUsageDaily(Base, TimestampMixin):
    """Daily aggregated usage per user per object."""
    __tablename__ = "li_usage_daily"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    system_id = Column(String(50), nullable=False)
    usage_date = Column(Date, nullable=False)
    transaction_code = Column(String(50))
    app_component = Column(String(100))
    execution_count = Column(Integer, default=0)
    is_advanced_mapped = Column(Boolean, default=False)
    source = Column(String(50))  # workload_stats, audit_log, last_logon, manual

    __table_args__ = (
        UniqueConstraint("tenant_id", "username", "system_id", "usage_date",
                         "transaction_code", name="uq_li_usage_daily"),
        Index("ix_li_ud_tenant_user", "tenant_id", "username"),
        Index("ix_li_ud_date", "usage_date"),
    )


class LIUsageRaw(Base, TimestampMixin):
    """Raw usage events — short retention, configurable per tenant."""
    __tablename__ = "li_usage_raw"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    system_id = Column(String(50), nullable=False)
    event_timestamp = Column(DateTime, nullable=False)
    event_type = Column(String(50))  # transaction, report, app_launch
    transaction_code = Column(String(50))
    program_name = Column(String(200))
    terminal = Column(String(100))
    source = Column(String(50))

    __table_args__ = (
        Index("ix_li_ur_tenant_user", "tenant_id", "username"),
        Index("ix_li_ur_timestamp", "event_timestamp"),
    )


# ── LI-007: Reclamation Cases ────────────────────────────────────────────────

class LIReclamationCase(Base, TimestampMixin):
    """License reclamation candidate and its lifecycle."""
    __tablename__ = "li_reclamation_cases"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    user_id = Column(String(100))
    system_id = Column(String(50))
    trigger = Column(String(50), nullable=False)  # ReclamationTrigger value
    status = Column(String(30), default="candidate")
    current_use_type = Column(String(30))
    current_fue = Column(Float)
    projected_use_type = Column(String(30))  # After reclamation
    projected_fue = Column(Float)
    fue_released = Column(Float, default=0.0)
    roles_to_remove = Column(JSON)  # List of role names
    inactive_days = Column(Integer)
    last_activity_date = Column(DateTime)
    exception_reason = Column(Text)  # service account, seasonal, etc.
    is_exception = Column(Boolean, default=False)
    reviewer = Column(String(100))
    reviewed_at = Column(DateTime)
    approval_workflow_id = Column(String(100))
    access_lifecycle_request_id = Column(String(100))
    completed_at = Column(DateTime)
    evidence = Column(JSON)

    __table_args__ = (
        Index("ix_li_rc_tenant_status", "tenant_id", "status"),
        Index("ix_li_rc_tenant_user", "tenant_id", "username"),
    )


class LIReclamationAction(Base, TimestampMixin):
    """Individual action within a reclamation case."""
    __tablename__ = "li_reclamation_actions"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    case_id = Column(String(50), ForeignKey("li_reclamation_cases.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # lock, remove_role, deactivate
    target_role = Column(String(100))
    target_system = Column(String(50))
    status = Column(String(30), default="pending")  # pending, executing, completed, failed
    executed_at = Column(DateTime)
    executed_by = Column(String(100))
    result = Column(Text)

    __table_args__ = (
        Index("ix_li_ra_case", "case_id"),
    )


# ── LI-006: Position Snapshots ───────────────────────────────────────────────

class LIPositionSnapshot(Base, TimestampMixin):
    """High-level license position for dashboard and trend reporting."""
    __tablename__ = "li_position_snapshots"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False)
    contract_id = Column(String(50), ForeignKey("li_contracts.id"))
    contracted_fue = Column(Float, nullable=False)
    consumed_fue = Column(Float, nullable=False)
    available_fue = Column(Float, nullable=False)
    utilisation_pct = Column(Float, nullable=False)
    advanced_count = Column(Integer, default=0)
    core_count = Column(Integer, default=0)
    self_service_count = Column(Integer, default=0)
    developer_count = Column(Integer, default=0)
    unclassified_count = Column(Integer, default=0)
    total_users = Column(Integer, default=0)
    reclamation_fue_released = Column(Float, default=0.0)
    review_candidates = Column(Integer, default=0)
    open_reclamation_cases = Column(Integer, default=0)
    data_freshness = Column(JSON)  # {system_id: last_sync_date}
    rule_pack_version = Column(String(50))

    __table_args__ = (
        Index("ix_li_ps_tenant_date", "tenant_id", "snapshot_date"),
    )


# ── Collection Status ─────────────────────────────────────────────────────────

class LICollectionStatus(Base, TimestampMixin):
    """Tracks data freshness per system per data source."""
    __tablename__ = "li_collection_status"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    system_id = Column(String(50), nullable=False)
    source_type = Column(String(50), nullable=False)  # workload_stats, audit_log, last_logon
    last_collected_at = Column(DateTime)
    last_success_at = Column(DateTime)
    records_collected = Column(Integer, default=0)
    coverage_start = Column(Date)
    coverage_end = Column(Date)
    status = Column(String(30), default="pending")  # pending, collecting, success, failed, stale
    error_message = Column(Text)

    __table_args__ = (
        UniqueConstraint("tenant_id", "system_id", "source_type", name="uq_li_cs_sys_source"),
        Index("ix_li_cs_tenant", "tenant_id"),
    )
