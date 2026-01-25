# Role Foundation Models
# Business-aligned role modeling with full lifecycle management

"""
Role Models for GOVERNEX+.

Provides:
- Business-aligned role structures
- Permission and authorization modeling
- Lifecycle state management
- Full versioning and metadata
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from enum import Enum
import logging
import hashlib

logger = logging.getLogger(__name__)


class RoleType(Enum):
    """Types of roles in the system."""
    BUSINESS = "BUSINESS"  # Business function role (Accounts Payable Clerk)
    TECHNICAL = "TECHNICAL"  # Technical role (SAP_ALL, S_TCODE_*)
    COMPOSITE = "COMPOSITE"  # Composite of other roles
    DERIVED = "DERIVED"  # Derived from master role with org restrictions
    FIREFIGHTER = "FIREFIGHTER"  # Emergency access role
    TEMPORARY = "TEMPORARY"  # Time-limited role


class RoleStatus(Enum):
    """Operational status of a role."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"
    DEPRECATED = "DEPRECATED"


class RoleLifecycleState(Enum):
    """Lifecycle states for role governance."""
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    MODIFICATION_PENDING = "MODIFICATION_PENDING"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class PermissionType(Enum):
    """Types of permissions."""
    TCODE = "TCODE"  # Transaction code
    AUTH_OBJECT = "AUTH_OBJECT"  # Authorization object
    FIELD_VALUE = "FIELD_VALUE"  # Specific field value in auth object
    PROGRAM = "PROGRAM"  # Program/report execution
    TABLE = "TABLE"  # Table access
    RFC = "RFC"  # RFC function
    SERVICE = "SERVICE"  # Web service


@dataclass
class AuthorizationObject:
    """
    SAP Authorization Object with field values.

    Example:
        S_TCODE with TCD = ['FK01', 'FK02', 'FK03']
    """
    object_id: str
    object_name: str
    object_class: str = ""
    description: str = ""

    # Field values
    field_values: Dict[str, List[str]] = field(default_factory=dict)

    # Risk classification
    is_sensitive: bool = False
    sensitivity_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "object_name": self.object_name,
            "object_class": self.object_class,
            "description": self.description,
            "field_values": self.field_values,
            "is_sensitive": self.is_sensitive,
            "sensitivity_reason": self.sensitivity_reason,
        }

    def has_wildcard(self) -> bool:
        """Check if any field has wildcard value."""
        for values in self.field_values.values():
            if "*" in values or "**" in values:
                return True
        return False

    def get_wildcard_fields(self) -> List[str]:
        """Get fields with wildcard values."""
        return [
            field_name for field_name, values in self.field_values.items()
            if "*" in values or "**" in values
        ]


@dataclass
class Permission:
    """
    A single permission entry.

    Can be a tcode, authorization object, or other access right.
    """
    permission_id: str
    permission_type: PermissionType
    value: str  # Tcode, program name, table, etc.
    description: str = ""

    # For auth objects
    auth_object: Optional[AuthorizationObject] = None

    # Classification
    is_sensitive: bool = False
    sensitivity_level: int = 0  # 0=normal, 1=elevated, 2=high, 3=critical
    business_action: str = ""  # e.g., "CREATE_VENDOR", "EXECUTE_PAYMENT"

    # Usage tracking
    last_used: Optional[datetime] = None
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "permission_id": self.permission_id,
            "permission_type": self.permission_type.value,
            "value": self.value,
            "description": self.description,
            "auth_object": self.auth_object.to_dict() if self.auth_object else None,
            "is_sensitive": self.is_sensitive,
            "sensitivity_level": self.sensitivity_level,
            "business_action": self.business_action,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_count": self.usage_count,
        }


@dataclass
class RoleMetadata:
    """
    Mandatory metadata for role governance.

    Every role must have:
    - Owner
    - Business justification
    - Risk rating
    - Review schedule
    """
    # Ownership
    owner_id: str
    owner_name: str
    owner_department: str = ""

    # Business context
    business_justification: str = ""
    business_process: str = ""
    job_function: str = ""

    # Risk classification
    risk_rating: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    risk_score: float = 0.0

    # Review
    review_frequency_days: int = 90
    last_review_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None
    last_reviewer: Optional[str] = None

    # Certification
    last_certified_date: Optional[datetime] = None
    certified_by: Optional[str] = None
    certification_expires: Optional[datetime] = None

    # Regulatory
    regulatory_references: List[str] = field(default_factory=list)
    compliance_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "owner_department": self.owner_department,
            "business_justification": self.business_justification,
            "business_process": self.business_process,
            "job_function": self.job_function,
            "risk_rating": self.risk_rating,
            "risk_score": round(self.risk_score, 2),
            "review_frequency_days": self.review_frequency_days,
            "last_review_date": self.last_review_date.isoformat() if self.last_review_date else None,
            "next_review_date": self.next_review_date.isoformat() if self.next_review_date else None,
            "last_certified_date": self.last_certified_date.isoformat() if self.last_certified_date else None,
            "certified_by": self.certified_by,
            "regulatory_references": self.regulatory_references,
            "compliance_tags": self.compliance_tags,
        }


@dataclass
class RoleVersion:
    """
    Version record for role changes.

    Provides full audit trail of role modifications.
    """
    version_id: str
    role_id: str
    version_number: int
    version_hash: str  # Hash of role content for comparison

    # Change details
    change_type: str  # "CREATED", "MODIFIED", "ACTIVATED", "DEPRECATED"
    change_description: str = ""
    changed_by: str = ""
    changed_at: datetime = field(default_factory=datetime.now)

    # Approval
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    # Permissions snapshot
    permissions_added: List[str] = field(default_factory=list)
    permissions_removed: List[str] = field(default_factory=list)

    # Full content hash for drift detection
    content_snapshot: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "role_id": self.role_id,
            "version_number": self.version_number,
            "version_hash": self.version_hash,
            "change_type": self.change_type,
            "change_description": self.change_description,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat(),
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "permissions_added": self.permissions_added,
            "permissions_removed": self.permissions_removed,
        }


@dataclass
class Role:
    """
    Complete role definition.

    Includes:
    - Identity and classification
    - Permissions
    - Metadata for governance
    - Version history
    - User assignments
    """
    role_id: str
    role_name: str
    description: str = ""

    # Classification
    role_type: RoleType = RoleType.BUSINESS
    status: RoleStatus = RoleStatus.ACTIVE
    lifecycle_state: RoleLifecycleState = RoleLifecycleState.DRAFT

    # Permissions
    permissions: List[Permission] = field(default_factory=list)

    # For composite roles
    child_roles: List[str] = field(default_factory=list)

    # For derived roles
    master_role_id: Optional[str] = None
    org_restrictions: Dict[str, List[str]] = field(default_factory=dict)

    # Metadata (required for governance)
    metadata: Optional[RoleMetadata] = None

    # Version history
    versions: List[RoleVersion] = field(default_factory=list)
    current_version: int = 1

    # User assignments
    assigned_users: Set[str] = field(default_factory=set)
    assignment_count: int = 0

    # System info
    system_id: str = ""
    client: str = ""

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    modified_at: Optional[datetime] = None
    modified_by: Optional[str] = None

    # Computed properties
    _content_hash: Optional[str] = field(default=None, repr=False)

    def __post_init__(self):
        """Initialize computed properties."""
        self._update_content_hash()

    def _update_content_hash(self):
        """Calculate hash of role content for drift detection."""
        content = f"{self.role_id}:{self.role_name}:{self.role_type.value}"
        content += ":" + ",".join(sorted(p.permission_id for p in self.permissions))
        content += ":" + ",".join(sorted(self.child_roles))
        self._content_hash = hashlib.md5(content.encode()).hexdigest()

    @property
    def content_hash(self) -> str:
        """Get current content hash."""
        if not self._content_hash:
            self._update_content_hash()
        return self._content_hash

    @property
    def permission_count(self) -> int:
        """Get total permission count."""
        return len(self.permissions)

    @property
    def sensitive_permission_count(self) -> int:
        """Get count of sensitive permissions."""
        return sum(1 for p in self.permissions if p.is_sensitive)

    @property
    def has_wildcards(self) -> bool:
        """Check if role has wildcard authorizations."""
        return any(
            p.auth_object and p.auth_object.has_wildcard()
            for p in self.permissions
        )

    @property
    def tcode_count(self) -> int:
        """Get count of transaction codes."""
        return sum(
            1 for p in self.permissions
            if p.permission_type == PermissionType.TCODE
        )

    def get_tcodes(self) -> List[str]:
        """Get list of transaction codes."""
        return [
            p.value for p in self.permissions
            if p.permission_type == PermissionType.TCODE
        ]

    def get_business_actions(self) -> Set[str]:
        """Get set of business actions enabled by this role."""
        return {
            p.business_action for p in self.permissions
            if p.business_action
        }

    def add_permission(self, permission: Permission):
        """Add a permission to the role."""
        self.permissions.append(permission)
        self._update_content_hash()

    def remove_permission(self, permission_id: str) -> bool:
        """Remove a permission from the role."""
        for i, p in enumerate(self.permissions):
            if p.permission_id == permission_id:
                del self.permissions[i]
                self._update_content_hash()
                return True
        return False

    def create_version(
        self,
        change_type: str,
        changed_by: str,
        description: str = ""
    ) -> RoleVersion:
        """Create a new version record."""
        self.current_version += 1
        version = RoleVersion(
            version_id=f"{self.role_id}-v{self.current_version}",
            role_id=self.role_id,
            version_number=self.current_version,
            version_hash=self.content_hash,
            change_type=change_type,
            change_description=description,
            changed_by=changed_by,
        )
        self.versions.append(version)
        return version

    def assign_user(self, user_id: str):
        """Assign role to a user."""
        self.assigned_users.add(user_id)
        self.assignment_count = len(self.assigned_users)

    def unassign_user(self, user_id: str):
        """Remove role from a user."""
        self.assigned_users.discard(user_id)
        self.assignment_count = len(self.assigned_users)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "description": self.description,
            "role_type": self.role_type.value,
            "status": self.status.value,
            "lifecycle_state": self.lifecycle_state.value,
            "permissions": [p.to_dict() for p in self.permissions],
            "permission_count": self.permission_count,
            "sensitive_permission_count": self.sensitive_permission_count,
            "tcode_count": self.tcode_count,
            "child_roles": self.child_roles,
            "master_role_id": self.master_role_id,
            "org_restrictions": self.org_restrictions,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "current_version": self.current_version,
            "content_hash": self.content_hash,
            "assignment_count": self.assignment_count,
            "system_id": self.system_id,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Role":
        """Deserialize from dictionary."""
        permissions = [
            Permission(
                permission_id=p["permission_id"],
                permission_type=PermissionType(p["permission_type"]),
                value=p["value"],
                description=p.get("description", ""),
                is_sensitive=p.get("is_sensitive", False),
                sensitivity_level=p.get("sensitivity_level", 0),
                business_action=p.get("business_action", ""),
            )
            for p in data.get("permissions", [])
        ]

        metadata = None
        if data.get("metadata"):
            m = data["metadata"]
            metadata = RoleMetadata(
                owner_id=m.get("owner_id", ""),
                owner_name=m.get("owner_name", ""),
                owner_department=m.get("owner_department", ""),
                business_justification=m.get("business_justification", ""),
                business_process=m.get("business_process", ""),
                risk_rating=m.get("risk_rating", "MEDIUM"),
            )

        return cls(
            role_id=data["role_id"],
            role_name=data["role_name"],
            description=data.get("description", ""),
            role_type=RoleType(data.get("role_type", "BUSINESS")),
            status=RoleStatus(data.get("status", "ACTIVE")),
            lifecycle_state=RoleLifecycleState(data.get("lifecycle_state", "DRAFT")),
            permissions=permissions,
            child_roles=data.get("child_roles", []),
            master_role_id=data.get("master_role_id"),
            org_restrictions=data.get("org_restrictions", {}),
            metadata=metadata,
            system_id=data.get("system_id", ""),
        )
