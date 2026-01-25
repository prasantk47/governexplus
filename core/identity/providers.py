# Unified Identity Provider Abstraction
# Central identity management for GOVERNEX+

"""
Unified Identity Provider Module for GOVERNEX+.

This module provides a unified abstraction layer over multiple identity sources:
- LDAP / Active Directory
- SSO (SAML 2.0, OAuth 2.0, OIDC)
- Azure AD (via Graph API)
- Okta
- SAP systems (via SNC)
- HR systems (Workday, SuccessFactors)

Features:
- Unified user model
- Automatic identity correlation
- Multi-source synchronization
- Identity lifecycle events
- Attribute mapping and transformation
- Conflict resolution
- Master data management
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set, Union, Tuple
from datetime import datetime, date, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import uuid


# ============================================================
# ENUMS
# ============================================================

class IdentitySourceType(Enum):
    """Types of identity sources."""
    LDAP = "ldap"
    ACTIVE_DIRECTORY = "active_directory"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    SAML_IDP = "saml_idp"
    OIDC_PROVIDER = "oidc_provider"
    SAP_SYSTEM = "sap"
    HR_SYSTEM = "hr"
    MANUAL = "manual"


class IdentitySyncStatus(Enum):
    """Sync status for identity."""
    SYNCED = "synced"
    PENDING = "pending"
    CONFLICT = "conflict"
    ERROR = "error"
    NOT_FOUND = "not_found"


class IdentityEventType(Enum):
    """Identity lifecycle events."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ENABLED = "enabled"
    DISABLED = "disabled"
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_EXPIRED = "password_expired"
    GROUP_ADDED = "group_added"
    GROUP_REMOVED = "group_removed"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    ATTRIBUTE_CHANGED = "attribute_changed"


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving identity conflicts."""
    SOURCE_PRIORITY = "source_priority"  # Use defined source priority
    MOST_RECENT = "most_recent"  # Use most recently updated value
    HR_AUTHORITATIVE = "hr_authoritative"  # HR system is authoritative
    MANUAL = "manual"  # Require manual resolution


# ============================================================
# UNIFIED IDENTITY MODEL
# ============================================================

@dataclass
class UnifiedIdentity:
    """
    Unified identity record combining data from multiple sources.

    This is the master identity record that correlates identities
    from different systems (LDAP, SSO, HR, SAP, etc.)
    """

    identity_id: str = field(default_factory=lambda: f"ID-{str(uuid.uuid4())[:8]}")

    # Core attributes
    username: str = ""
    email: str = ""
    employee_id: str = ""
    upn: str = ""  # User Principal Name

    # Name
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    display_name: str = ""
    preferred_name: str = ""

    # Organization
    department: str = ""
    division: str = ""
    company: str = ""
    cost_center: str = ""
    location: str = ""
    job_title: str = ""
    job_code: str = ""

    # Manager
    manager_id: str = ""
    manager_name: str = ""
    manager_email: str = ""

    # Contact
    phone: str = ""
    mobile: str = ""
    office_location: str = ""

    # Status
    is_active: bool = True
    is_locked: bool = False
    account_status: str = "active"  # active, disabled, terminated, suspended

    # Employment
    employment_type: str = ""  # full_time, contractor, vendor, etc.
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    last_working_day: Optional[date] = None

    # Source identities
    source_identities: Dict[str, str] = field(default_factory=dict)  # source_type: source_id

    # Groups and roles (aggregated from all sources)
    groups: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    entitlements: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_synced: Optional[datetime] = None
    last_login: Optional[datetime] = None

    # Sync status
    sync_status: IdentitySyncStatus = IdentitySyncStatus.SYNCED
    sync_errors: List[str] = field(default_factory=list)

    # Source tracking
    authoritative_source: str = ""  # Which source is authoritative for this identity
    attribute_sources: Dict[str, str] = field(default_factory=dict)  # attribute: source

    # Risk
    risk_score: int = 0
    risk_factors: List[str] = field(default_factory=list)

    # Custom attributes
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

    def get_source_identity(self, source_type: str) -> Optional[str]:
        """Get identity ID from a specific source."""
        return self.source_identities.get(source_type)

    def add_source_identity(self, source_type: str, source_id: str) -> None:
        """Add or update source identity."""
        self.source_identities[source_type] = source_id
        self.updated_at = datetime.now()

    def is_terminated(self) -> bool:
        """Check if identity is terminated."""
        if self.termination_date:
            return self.termination_date <= date.today()
        return self.account_status == "terminated"

    def is_contractor(self) -> bool:
        """Check if identity is a contractor."""
        return self.employment_type in ("contractor", "vendor", "consultant", "external")

    def days_since_last_login(self) -> Optional[int]:
        """Get days since last login."""
        if self.last_login:
            return (datetime.now() - self.last_login).days
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity_id": self.identity_id,
            "username": self.username,
            "email": self.email,
            "employee_id": self.employee_id,
            "full_name": self.full_name,
            "department": self.department,
            "job_title": self.job_title,
            "manager_name": self.manager_name,
            "is_active": self.is_active,
            "account_status": self.account_status,
            "groups": self.groups,
            "roles": self.roles,
            "source_identities": self.source_identities,
            "sync_status": self.sync_status.value,
            "last_synced": self.last_synced.isoformat() if self.last_synced else None,
        }


# ============================================================
# IDENTITY EVENTS
# ============================================================

@dataclass
class IdentityEvent:
    """Identity lifecycle event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: IdentityEventType = IdentityEventType.UPDATED

    # Identity
    identity_id: str = ""
    username: str = ""

    # Source
    source_type: str = ""
    source_id: str = ""

    # Details
    timestamp: datetime = field(default_factory=datetime.now)
    changed_by: str = ""
    change_details: Dict[str, Any] = field(default_factory=dict)
    old_values: Dict[str, Any] = field(default_factory=dict)
    new_values: Dict[str, Any] = field(default_factory=dict)

    # Processing
    processed: bool = False
    processed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "identity_id": self.identity_id,
            "username": self.username,
            "source_type": self.source_type,
            "timestamp": self.timestamp.isoformat(),
            "change_details": self.change_details,
        }


# ============================================================
# IDENTITY SOURCE INTERFACE
# ============================================================

class IdentitySource(ABC):
    """Abstract base class for identity sources."""

    @property
    @abstractmethod
    def source_type(self) -> IdentitySourceType:
        """Return the type of this identity source."""
        pass

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Return unique identifier for this source."""
        pass

    @abstractmethod
    def get_user(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get user by identifier (username, email, or ID)."""
        pass

    @abstractmethod
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users from this source."""
        pass

    @abstractmethod
    def get_groups(self, user_id: str) -> List[str]:
        """Get groups/roles for a user."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test connection to the identity source."""
        pass


# ============================================================
# ATTRIBUTE MAPPING
# ============================================================

@dataclass
class AttributeMapping:
    """Mapping configuration for identity attributes."""
    mapping_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_type: IdentitySourceType = IdentitySourceType.LDAP

    # Mappings: unified_attribute -> source_attribute
    mappings: Dict[str, str] = field(default_factory=dict)

    # Transformations: unified_attribute -> transformation_function_name
    transformations: Dict[str, str] = field(default_factory=dict)

    # Default values
    defaults: Dict[str, Any] = field(default_factory=dict)


# Standard attribute mappings
LDAP_ATTRIBUTE_MAPPING = AttributeMapping(
    source_type=IdentitySourceType.LDAP,
    mappings={
        "username": "sAMAccountName",
        "email": "mail",
        "employee_id": "employeeID",
        "first_name": "givenName",
        "last_name": "sn",
        "full_name": "displayName",
        "department": "department",
        "job_title": "title",
        "manager_id": "manager",
        "phone": "telephoneNumber",
        "mobile": "mobile",
        "company": "company",
    },
)

AZURE_AD_ATTRIBUTE_MAPPING = AttributeMapping(
    source_type=IdentitySourceType.AZURE_AD,
    mappings={
        "username": "userPrincipalName",
        "email": "mail",
        "employee_id": "employeeId",
        "first_name": "givenName",
        "last_name": "surname",
        "full_name": "displayName",
        "department": "department",
        "job_title": "jobTitle",
        "manager_id": "manager.id",
        "phone": "businessPhones[0]",
        "mobile": "mobilePhone",
        "company": "companyName",
        "office_location": "officeLocation",
    },
)

OKTA_ATTRIBUTE_MAPPING = AttributeMapping(
    source_type=IdentitySourceType.OKTA,
    mappings={
        "username": "login",
        "email": "email",
        "employee_id": "employeeNumber",
        "first_name": "firstName",
        "last_name": "lastName",
        "full_name": "displayName",
        "department": "department",
        "job_title": "title",
        "manager_id": "managerId",
        "phone": "primaryPhone",
        "mobile": "mobilePhone",
    },
)

HR_ATTRIBUTE_MAPPING = AttributeMapping(
    source_type=IdentitySourceType.HR_SYSTEM,
    mappings={
        "username": "work_email",
        "email": "work_email",
        "employee_id": "employee_number",
        "first_name": "legal_first_name",
        "last_name": "legal_last_name",
        "full_name": "legal_full_name",
        "preferred_name": "preferred_name",
        "department": "department_name",
        "division": "division_name",
        "job_title": "job_title",
        "job_code": "job_code",
        "manager_id": "manager_employee_number",
        "company": "company_name",
        "cost_center": "cost_center",
        "location": "work_location",
        "hire_date": "hire_date",
        "termination_date": "termination_date",
        "employment_type": "employment_type",
    },
)


# ============================================================
# IDENTITY CORRELATION
# ============================================================

@dataclass
class CorrelationRule:
    """Rule for correlating identities across sources."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""

    # Match criteria (in priority order)
    match_attributes: List[str] = field(default_factory=lambda: [
        "email",
        "employee_id",
        "username",
    ])

    # Match options
    case_sensitive: bool = False
    fuzzy_match: bool = False
    fuzzy_threshold: float = 0.9


@dataclass
class CorrelationResult:
    """Result of identity correlation."""
    source_id: str = ""
    source_type: str = ""
    matched_identity_id: Optional[str] = None
    match_attribute: str = ""
    match_value: str = ""
    confidence: float = 0.0
    is_new: bool = False


class IdentityCorrelator:
    """
    Correlate identities across multiple sources.

    Matches identities from different systems to create unified view.
    """

    def __init__(self, rules: Optional[List[CorrelationRule]] = None):
        self.rules = rules or [CorrelationRule(name="default")]

    def correlate(
        self,
        source_identity: Dict[str, Any],
        existing_identities: List[UnifiedIdentity],
    ) -> CorrelationResult:
        """
        Find matching unified identity for a source identity.

        Args:
            source_identity: Identity data from source system
            existing_identities: Existing unified identities to match against

        Returns:
            CorrelationResult with match information
        """
        result = CorrelationResult(
            source_id=source_identity.get("id", ""),
            source_type=source_identity.get("source_type", ""),
        )

        for rule in self.rules:
            for attr in rule.match_attributes:
                source_value = source_identity.get(attr)
                if not source_value:
                    continue

                for identity in existing_identities:
                    identity_value = getattr(identity, attr, None)
                    if not identity_value:
                        continue

                    # Normalize for comparison
                    if not rule.case_sensitive:
                        source_value = source_value.lower()
                        identity_value = identity_value.lower()

                    if source_value == identity_value:
                        result.matched_identity_id = identity.identity_id
                        result.match_attribute = attr
                        result.match_value = source_value
                        result.confidence = 1.0
                        return result

                    # Fuzzy matching (if enabled)
                    if rule.fuzzy_match:
                        similarity = self._calculate_similarity(source_value, identity_value)
                        if similarity >= rule.fuzzy_threshold:
                            result.matched_identity_id = identity.identity_id
                            result.match_attribute = attr
                            result.match_value = source_value
                            result.confidence = similarity
                            return result

        # No match found - new identity
        result.is_new = True
        return result

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity (Levenshtein ratio)."""
        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0

        # Simple Levenshtein distance
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                matrix[i][j] = min(
                    matrix[i - 1][j] + 1,
                    matrix[i][j - 1] + 1,
                    matrix[i - 1][j - 1] + cost,
                )

        distance = matrix[len1][len2]
        max_len = max(len1, len2)
        return 1 - (distance / max_len)


# ============================================================
# IDENTITY PROVIDER MANAGER
# ============================================================

@dataclass
class IdentitySourceConfig:
    """Configuration for an identity source."""
    config_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    source_type: IdentitySourceType = IdentitySourceType.LDAP

    # Priority (lower = higher priority)
    priority: int = 100

    # Sync settings
    sync_enabled: bool = True
    sync_interval_minutes: int = 60
    sync_full_on_start: bool = True

    # Attribute mapping
    attribute_mapping: Optional[AttributeMapping] = None

    # Authoritative attributes (this source is authoritative for these)
    authoritative_for: List[str] = field(default_factory=list)

    # Status
    is_active: bool = True
    last_sync: Optional[datetime] = None
    last_sync_status: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "name": self.name,
            "source_type": self.source_type.value,
            "priority": self.priority,
            "sync_enabled": self.sync_enabled,
            "is_active": self.is_active,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
        }


class IdentityProviderManager:
    """
    Central manager for all identity providers.

    Orchestrates:
    - Identity source registration
    - Synchronization
    - Correlation
    - Conflict resolution
    - Event processing

    Usage:
        manager = IdentityProviderManager()

        # Register sources
        manager.register_source(ldap_config, ldap_connector)
        manager.register_source(azure_config, azure_connector)
        manager.register_source(hr_config, hr_connector)

        # Sync all sources
        manager.sync_all()

        # Get unified identity
        identity = manager.get_identity(email="john@company.com")

        # Subscribe to events
        manager.subscribe(IdentityEventType.CREATED, on_user_created)
    """

    def __init__(
        self,
        conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.SOURCE_PRIORITY,
    ):
        self.sources: Dict[str, Tuple[IdentitySourceConfig, IdentitySource]] = {}
        self.identities: Dict[str, UnifiedIdentity] = {}
        self.correlator = IdentityCorrelator()
        self.conflict_strategy = conflict_strategy

        # Event handlers
        self.event_handlers: Dict[IdentityEventType, List[Callable]] = {}
        self.event_queue: List[IdentityEvent] = []

        # Index for fast lookup
        self._email_index: Dict[str, str] = {}  # email -> identity_id
        self._username_index: Dict[str, str] = {}  # username -> identity_id
        self._employee_id_index: Dict[str, str] = {}  # employee_id -> identity_id

    def register_source(
        self,
        config: IdentitySourceConfig,
        source: IdentitySource,
    ) -> None:
        """Register an identity source."""
        self.sources[config.config_id] = (config, source)

        # Set default attribute mapping
        if not config.attribute_mapping:
            config.attribute_mapping = self._get_default_mapping(config.source_type)

    def _get_default_mapping(self, source_type: IdentitySourceType) -> AttributeMapping:
        """Get default attribute mapping for source type."""
        mappings = {
            IdentitySourceType.LDAP: LDAP_ATTRIBUTE_MAPPING,
            IdentitySourceType.ACTIVE_DIRECTORY: LDAP_ATTRIBUTE_MAPPING,
            IdentitySourceType.AZURE_AD: AZURE_AD_ATTRIBUTE_MAPPING,
            IdentitySourceType.OKTA: OKTA_ATTRIBUTE_MAPPING,
            IdentitySourceType.HR_SYSTEM: HR_ATTRIBUTE_MAPPING,
        }
        return mappings.get(source_type, AttributeMapping())

    def get_identity(
        self,
        identity_id: Optional[str] = None,
        email: Optional[str] = None,
        username: Optional[str] = None,
        employee_id: Optional[str] = None,
    ) -> Optional[UnifiedIdentity]:
        """Get unified identity by various identifiers."""
        # Direct lookup
        if identity_id and identity_id in self.identities:
            return self.identities[identity_id]

        # Index lookup
        if email:
            identity_id = self._email_index.get(email.lower())
            if identity_id:
                return self.identities.get(identity_id)

        if username:
            identity_id = self._username_index.get(username.lower())
            if identity_id:
                return self.identities.get(identity_id)

        if employee_id:
            identity_id = self._employee_id_index.get(employee_id)
            if identity_id:
                return self.identities.get(identity_id)

        return None

    def get_all_identities(
        self,
        active_only: bool = True,
        source_type: Optional[IdentitySourceType] = None,
    ) -> List[UnifiedIdentity]:
        """Get all unified identities."""
        identities = list(self.identities.values())

        if active_only:
            identities = [i for i in identities if i.is_active]

        if source_type:
            identities = [
                i for i in identities
                if source_type.value in i.source_identities
            ]

        return identities

    def sync_source(self, config_id: str) -> Dict[str, Any]:
        """Sync identities from a specific source."""
        if config_id not in self.sources:
            raise ValueError(f"Source not found: {config_id}")

        config, source = self.sources[config_id]
        result = {
            "source": config.name,
            "started_at": datetime.now(),
            "users_processed": 0,
            "users_created": 0,
            "users_updated": 0,
            "errors": [],
        }

        try:
            # Get all users from source
            source_users = source.get_all_users()

            for source_user in source_users:
                try:
                    # Map attributes
                    mapped_user = self._map_attributes(source_user, config.attribute_mapping)
                    mapped_user["source_type"] = config.source_type.value

                    # Correlate with existing identities
                    correlation = self.correlator.correlate(
                        mapped_user,
                        list(self.identities.values()),
                    )

                    if correlation.is_new:
                        # Create new identity
                        identity = self._create_identity(mapped_user, config)
                        result["users_created"] += 1
                        self._emit_event(IdentityEventType.CREATED, identity)
                    else:
                        # Update existing identity
                        identity = self.identities[correlation.matched_identity_id]
                        updated = self._update_identity(identity, mapped_user, config)
                        if updated:
                            result["users_updated"] += 1
                            self._emit_event(IdentityEventType.UPDATED, identity)

                    result["users_processed"] += 1

                except Exception as e:
                    result["errors"].append(f"Error processing user: {str(e)}")

            config.last_sync = datetime.now()
            config.last_sync_status = "success"

        except Exception as e:
            config.last_sync_status = f"error: {str(e)}"
            result["errors"].append(str(e))

        result["completed_at"] = datetime.now()
        return result

    def sync_all(self) -> Dict[str, Any]:
        """Sync all active identity sources."""
        results = {}

        # Sort by priority
        sorted_sources = sorted(
            self.sources.items(),
            key=lambda x: x[1][0].priority,
        )

        for config_id, (config, source) in sorted_sources:
            if config.is_active and config.sync_enabled:
                results[config.name] = self.sync_source(config_id)

        return results

    def _map_attributes(
        self,
        source_user: Dict[str, Any],
        mapping: AttributeMapping,
    ) -> Dict[str, Any]:
        """Map source attributes to unified attributes."""
        result = {}

        for unified_attr, source_attr in mapping.mappings.items():
            value = source_user.get(source_attr)

            # Apply transformation if defined
            if unified_attr in mapping.transformations:
                transform = mapping.transformations[unified_attr]
                value = self._apply_transformation(value, transform)

            # Use default if no value
            if value is None and unified_attr in mapping.defaults:
                value = mapping.defaults[unified_attr]

            if value is not None:
                result[unified_attr] = value

        return result

    def _apply_transformation(self, value: Any, transform: str) -> Any:
        """Apply transformation to attribute value."""
        if not value:
            return value

        if transform == "lowercase":
            return str(value).lower()
        elif transform == "uppercase":
            return str(value).upper()
        elif transform == "strip":
            return str(value).strip()
        elif transform == "extract_username":
            # Extract username from email
            if "@" in str(value):
                return str(value).split("@")[0]

        return value

    def _create_identity(
        self,
        mapped_user: Dict[str, Any],
        config: IdentitySourceConfig,
    ) -> UnifiedIdentity:
        """Create new unified identity."""
        identity = UnifiedIdentity(
            username=mapped_user.get("username", ""),
            email=mapped_user.get("email", ""),
            employee_id=mapped_user.get("employee_id", ""),
            first_name=mapped_user.get("first_name", ""),
            last_name=mapped_user.get("last_name", ""),
            full_name=mapped_user.get("full_name", ""),
            department=mapped_user.get("department", ""),
            job_title=mapped_user.get("job_title", ""),
            manager_id=mapped_user.get("manager_id", ""),
            company=mapped_user.get("company", ""),
            authoritative_source=config.source_type.value,
            last_synced=datetime.now(),
        )

        # Add source identity
        source_type = mapped_user.get("source_type", config.source_type.value)
        source_id = mapped_user.get("id", mapped_user.get("username", ""))
        identity.add_source_identity(source_type, source_id)

        # Track attribute sources
        for attr in mapped_user:
            if attr not in ("id", "source_type"):
                identity.attribute_sources[attr] = source_type

        # Store identity
        self.identities[identity.identity_id] = identity
        self._update_indexes(identity)

        return identity

    def _update_identity(
        self,
        identity: UnifiedIdentity,
        mapped_user: Dict[str, Any],
        config: IdentitySourceConfig,
    ) -> bool:
        """Update existing unified identity with source data."""
        updated = False
        source_type = mapped_user.get("source_type", config.source_type.value)

        # Add/update source identity
        source_id = mapped_user.get("id", mapped_user.get("username", ""))
        identity.add_source_identity(source_type, source_id)

        for attr, value in mapped_user.items():
            if attr in ("id", "source_type"):
                continue

            current_value = getattr(identity, attr, None)

            # Determine if we should update
            should_update = False

            if current_value is None:
                should_update = True
            elif attr in config.authoritative_for:
                should_update = True
            elif self.conflict_strategy == ConflictResolutionStrategy.SOURCE_PRIORITY:
                current_source = identity.attribute_sources.get(attr)
                if current_source:
                    current_priority = self._get_source_priority(current_source)
                    new_priority = config.priority
                    should_update = new_priority < current_priority
                else:
                    should_update = True
            elif self.conflict_strategy == ConflictResolutionStrategy.MOST_RECENT:
                should_update = True

            if should_update and value != current_value:
                setattr(identity, attr, value)
                identity.attribute_sources[attr] = source_type
                updated = True

        if updated:
            identity.updated_at = datetime.now()
            identity.last_synced = datetime.now()
            self._update_indexes(identity)

        return updated

    def _get_source_priority(self, source_type: str) -> int:
        """Get priority for a source type."""
        for config_id, (config, source) in self.sources.items():
            if config.source_type.value == source_type:
                return config.priority
        return 999

    def _update_indexes(self, identity: UnifiedIdentity) -> None:
        """Update lookup indexes for an identity."""
        if identity.email:
            self._email_index[identity.email.lower()] = identity.identity_id
        if identity.username:
            self._username_index[identity.username.lower()] = identity.identity_id
        if identity.employee_id:
            self._employee_id_index[identity.employee_id] = identity.identity_id

    # ============================================================
    # EVENT HANDLING
    # ============================================================

    def subscribe(
        self,
        event_type: IdentityEventType,
        handler: Callable[[IdentityEvent], None],
    ) -> None:
        """Subscribe to identity events."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: IdentityEventType,
        handler: Callable[[IdentityEvent], None],
    ) -> None:
        """Unsubscribe from identity events."""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].remove(handler)

    def _emit_event(
        self,
        event_type: IdentityEventType,
        identity: UnifiedIdentity,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an identity event."""
        event = IdentityEvent(
            event_type=event_type,
            identity_id=identity.identity_id,
            username=identity.username,
            change_details=details or {},
        )

        self.event_queue.append(event)

        # Notify handlers
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass

    def process_events(self) -> int:
        """Process pending events. Returns count of processed events."""
        processed = 0
        while self.event_queue:
            event = self.event_queue.pop(0)
            event.processed = True
            event.processed_at = datetime.now()
            processed += 1
        return processed

    # ============================================================
    # UTILITIES
    # ============================================================

    def get_source_status(self) -> List[Dict[str, Any]]:
        """Get status of all identity sources."""
        status = []
        for config_id, (config, source) in self.sources.items():
            status.append({
                "config_id": config_id,
                "name": config.name,
                "source_type": config.source_type.value,
                "is_active": config.is_active,
                "sync_enabled": config.sync_enabled,
                "last_sync": config.last_sync.isoformat() if config.last_sync else None,
                "last_sync_status": config.last_sync_status,
                "connected": source.test_connection(),
            })
        return status

    def get_identity_stats(self) -> Dict[str, Any]:
        """Get identity statistics."""
        identities = list(self.identities.values())
        return {
            "total_identities": len(identities),
            "active_identities": len([i for i in identities if i.is_active]),
            "terminated": len([i for i in identities if i.is_terminated()]),
            "contractors": len([i for i in identities if i.is_contractor()]),
            "by_source": {
                source_type.value: len([
                    i for i in identities
                    if source_type.value in i.source_identities
                ])
                for source_type in IdentitySourceType
            },
            "sync_status": {
                status.value: len([
                    i for i in identities
                    if i.sync_status == status
                ])
                for status in IdentitySyncStatus
            },
        }

    def find_orphaned_identities(self) -> List[UnifiedIdentity]:
        """Find identities that exist in unified store but not in any source."""
        # Would check each identity against sources
        return []

    def find_conflicts(self) -> List[Dict[str, Any]]:
        """Find identities with conflicting data from multiple sources."""
        conflicts = []
        # Would compare attribute values across sources
        return conflicts


# ============================================================
# FACTORY FUNCTIONS
# ============================================================

def create_identity_manager(
    sources: Optional[List[Tuple[IdentitySourceConfig, IdentitySource]]] = None,
) -> IdentityProviderManager:
    """Create and configure identity provider manager."""
    manager = IdentityProviderManager()

    if sources:
        for config, source in sources:
            manager.register_source(config, source)

    return manager


def create_hr_authoritative_manager() -> IdentityProviderManager:
    """Create manager where HR system is authoritative."""
    return IdentityProviderManager(
        conflict_strategy=ConflictResolutionStrategy.HR_AUTHORITATIVE,
    )
