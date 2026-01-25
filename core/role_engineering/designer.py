"""
Role Designer - Core Role Engineering Module

Provides comprehensive role creation, modification, testing,
and lifecycle management capabilities.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import uuid
import re
import copy


class RoleType(Enum):
    """Types of roles"""
    SINGLE = "single"              # Standard single role
    COMPOSITE = "composite"         # Contains other roles
    DERIVED = "derived"            # Inherits from parent role
    TEMPLATE = "template"          # Template for creating roles
    EMERGENCY = "emergency"        # Firefighter/emergency roles


class RoleStatus(Enum):
    """Role lifecycle status"""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class PermissionType(Enum):
    """Types of permissions"""
    TRANSACTION = "transaction"
    AUTHORIZATION = "authorization"
    MENU = "menu"
    ORG_LEVEL = "org_level"


@dataclass
class AuthorizationObject:
    """SAP Authorization Object definition"""
    object_id: str
    name: str
    description: str = ""
    fields: Dict[str, List[str]] = field(default_factory=dict)  # Field -> allowed values

    def to_dict(self) -> Dict:
        return {
            "object_id": self.object_id,
            "name": self.name,
            "description": self.description,
            "fields": self.fields
        }


@dataclass
class Permission:
    """A permission/authorization entry"""
    permission_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    permission_type: PermissionType = PermissionType.TRANSACTION
    auth_object: str = ""
    field_values: Dict[str, List[str]] = field(default_factory=dict)
    transaction_codes: List[str] = field(default_factory=list)
    org_levels: Dict[str, List[str]] = field(default_factory=dict)
    description: str = ""
    is_critical: bool = False
    risk_level: str = "low"

    def to_dict(self) -> Dict:
        return {
            "permission_id": self.permission_id,
            "permission_type": self.permission_type.value,
            "auth_object": self.auth_object,
            "field_values": self.field_values,
            "transaction_codes": self.transaction_codes,
            "org_levels": self.org_levels,
            "description": self.description,
            "is_critical": self.is_critical,
            "risk_level": self.risk_level
        }


@dataclass
class RoleVersion:
    """Version information for a role"""
    version_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    version_number: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    change_summary: str = ""
    permissions_snapshot: List[Dict] = field(default_factory=list)
    is_current: bool = True

    def to_dict(self) -> Dict:
        return {
            "version_id": self.version_id,
            "version_number": self.version_number,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "change_summary": self.change_summary,
            "permissions_count": len(self.permissions_snapshot),
            "is_current": self.is_current
        }


@dataclass
class Role:
    """Complete role definition"""
    role_id: str = field(default_factory=lambda: f"Z_ROLE_{str(uuid.uuid4())[:6].upper()}")
    name: str = ""
    description: str = ""
    role_type: RoleType = RoleType.SINGLE
    status: RoleStatus = RoleStatus.DRAFT

    # Permissions and access
    permissions: List[Permission] = field(default_factory=list)
    transaction_codes: List[str] = field(default_factory=list)
    menu_items: List[str] = field(default_factory=list)

    # Composite/Derived role links
    child_roles: List[str] = field(default_factory=list)  # For composite roles
    parent_role: Optional[str] = None  # For derived roles

    # Organizational restrictions
    org_level_values: Dict[str, List[str]] = field(default_factory=dict)

    # Metadata
    business_process: str = ""
    department: str = ""
    system_id: str = "SAP_ECC"
    owner: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    modified_at: datetime = field(default_factory=datetime.now)
    modified_by: str = ""
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None

    # Version control
    current_version: int = 1
    versions: List[RoleVersion] = field(default_factory=list)

    # Risk & compliance
    risk_level: str = "low"
    is_sensitive: bool = False
    requires_approval: bool = False
    sod_conflicts: List[str] = field(default_factory=list)

    # Documentation
    documentation: str = ""
    change_history: List[Dict] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "role_type": self.role_type.value,
            "status": self.status.value,
            "permissions": [p.to_dict() for p in self.permissions],
            "transaction_codes": self.transaction_codes,
            "menu_items": self.menu_items,
            "child_roles": self.child_roles,
            "parent_role": self.parent_role,
            "org_level_values": self.org_level_values,
            "business_process": self.business_process,
            "department": self.department,
            "system_id": self.system_id,
            "owner": self.owner,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "modified_at": self.modified_at.isoformat(),
            "modified_by": self.modified_by,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "current_version": self.current_version,
            "versions": [v.to_dict() for v in self.versions],
            "risk_level": self.risk_level,
            "is_sensitive": self.is_sensitive,
            "requires_approval": self.requires_approval,
            "sod_conflicts": self.sod_conflicts,
            "documentation": self.documentation,
            "tags": self.tags
        }


@dataclass
class RoleTestResult:
    """Result of role testing/simulation"""
    test_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role_id: str = ""
    test_type: str = ""  # "sod_check", "permission_test", "user_simulation"
    test_user: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    passed: bool = True
    issues: List[Dict] = field(default_factory=list)
    warnings: List[Dict] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "test_id": self.test_id,
            "role_id": self.role_id,
            "test_type": self.test_type,
            "test_user": self.test_user,
            "timestamp": self.timestamp.isoformat(),
            "passed": self.passed,
            "issues": self.issues,
            "warnings": self.warnings,
            "details": self.details
        }


class RoleDesigner:
    """
    Role Designer - Comprehensive role engineering tool.

    Provides:
    - Role creation with wizard-like flow
    - Permission assignment and management
    - Role testing and simulation
    - Version control
    - Naming standards enforcement
    - Documentation generation
    """

    # Naming convention patterns
    NAMING_PATTERNS = {
        "standard": r"^Z_[A-Z]{2,4}_[A-Z0-9_]+$",
        "composite": r"^ZC_[A-Z]{2,4}_[A-Z0-9_]+$",
        "derived": r"^ZD_[A-Z]{2,4}_[A-Z0-9_]+$",
        "template": r"^ZT_[A-Z]{2,4}_[A-Z0-9_]+$",
        "emergency": r"^ZE_FF_[A-Z0-9_]+$"
    }

    # Common authorization objects
    AUTH_OBJECTS = {
        "S_TCODE": AuthorizationObject(
            "S_TCODE", "Transaction Code Check",
            "Controls access to transactions",
            {"TCD": []}
        ),
        "F_BKPF_BUK": AuthorizationObject(
            "F_BKPF_BUK", "Accounting Document: Company Code",
            "Controls access to company codes in FI",
            {"BUKRS": [], "ACTVT": ["01", "02", "03", "06"]}
        ),
        "M_BEST_BSA": AuthorizationObject(
            "M_BEST_BSA", "Purchase Order: Document Type",
            "Controls PO document types",
            {"BSART": [], "ACTVT": ["01", "02", "03"]}
        ),
        "M_BEST_EKG": AuthorizationObject(
            "M_BEST_EKG", "Purchase Order: Purchasing Group",
            "Controls purchasing groups",
            {"EKGRP": [], "ACTVT": ["01", "02", "03"]}
        ),
        "M_BEST_EKO": AuthorizationObject(
            "M_BEST_EKO", "Purchase Order: Purchasing Org",
            "Controls purchasing organizations",
            {"EKORG": [], "ACTVT": ["01", "02", "03"]}
        ),
        "F_LFA1_BUK": AuthorizationObject(
            "F_LFA1_BUK", "Vendor: Company Code",
            "Controls vendor master access by company",
            {"BUKRS": [], "ACTVT": ["01", "02", "03", "06"]}
        ),
        "P_ORGIN": AuthorizationObject(
            "P_ORGIN", "HR Master Data",
            "Controls HR master data access",
            {"PERSA": [], "PERSG": [], "PERSK": [], "INFTY": [], "SUBTY": [], "AUTHC": []}
        ),
        "S_USER_GRP": AuthorizationObject(
            "S_USER_GRP", "User Master: User Groups",
            "Controls user administration",
            {"CLASS": [], "ACTVT": ["01", "02", "03", "05", "06", "22"]}
        )
    }

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.templates: Dict[str, Role] = {}
        self.test_history: List[RoleTestResult] = []
        self._initialize_templates()

    def _initialize_templates(self):
        """Initialize standard role templates"""
        # Display-only template
        self.templates["display_only"] = Role(
            role_id="ZT_DISPLAY_TEMPLATE",
            name="Display Only Template",
            description="Template for display-only access",
            role_type=RoleType.TEMPLATE,
            status=RoleStatus.ACTIVE,
            permissions=[
                Permission(
                    permission_type=PermissionType.AUTHORIZATION,
                    auth_object="ACTVT",
                    field_values={"ACTVT": ["03"]},
                    description="Display only activity"
                )
            ],
            risk_level="low"
        )

        # Procurement template
        self.templates["procurement"] = Role(
            role_id="ZT_PROCUREMENT_TEMPLATE",
            name="Procurement Template",
            description="Template for procurement roles",
            role_type=RoleType.TEMPLATE,
            status=RoleStatus.ACTIVE,
            business_process="Procure-to-Pay",
            permissions=[
                Permission(
                    permission_type=PermissionType.AUTHORIZATION,
                    auth_object="M_BEST_EKO",
                    field_values={"EKORG": ["*"], "ACTVT": ["01", "02", "03"]},
                    description="Purchasing organization access"
                ),
                Permission(
                    permission_type=PermissionType.AUTHORIZATION,
                    auth_object="M_BEST_EKG",
                    field_values={"EKGRP": ["*"], "ACTVT": ["01", "02", "03"]},
                    description="Purchasing group access"
                )
            ],
            risk_level="medium"
        )

        # Finance template
        self.templates["finance"] = Role(
            role_id="ZT_FINANCE_TEMPLATE",
            name="Finance Template",
            description="Template for finance roles",
            role_type=RoleType.TEMPLATE,
            status=RoleStatus.ACTIVE,
            business_process="Finance",
            permissions=[
                Permission(
                    permission_type=PermissionType.AUTHORIZATION,
                    auth_object="F_BKPF_BUK",
                    field_values={"BUKRS": ["*"], "ACTVT": ["01", "02", "03"]},
                    description="Company code access"
                )
            ],
            risk_level="high"
        )

    # =========================================================================
    # Role Creation
    # =========================================================================

    def create_role(
        self,
        name: str,
        description: str,
        role_type: RoleType = RoleType.SINGLE,
        created_by: str = "SYSTEM",
        template_id: Optional[str] = None,
        **kwargs
    ) -> Role:
        """
        Create a new role.

        Args:
            name: Role display name
            description: Role description
            role_type: Type of role
            created_by: User creating the role
            template_id: Optional template to base role on
            **kwargs: Additional role attributes

        Returns:
            Created Role object
        """
        # Generate role ID based on type
        role_id = self._generate_role_id(name, role_type)

        # Create base role
        role = Role(
            role_id=role_id,
            name=name,
            description=description,
            role_type=role_type,
            status=RoleStatus.DRAFT,
            created_at=datetime.now(),
            created_by=created_by,
            modified_at=datetime.now(),
            modified_by=created_by
        )

        # Apply template if specified
        if template_id and template_id in self.templates:
            template = self.templates[template_id]
            role.permissions = copy.deepcopy(template.permissions)
            role.business_process = template.business_process
            role.risk_level = template.risk_level

        # Apply additional kwargs
        for key, value in kwargs.items():
            if hasattr(role, key):
                setattr(role, key, value)

        # Create initial version
        role.versions.append(RoleVersion(
            version_number=1,
            created_at=datetime.now(),
            created_by=created_by,
            change_summary="Initial creation",
            permissions_snapshot=[p.to_dict() for p in role.permissions]
        ))

        # Validate naming
        validation = self.validate_role_name(role_id, role_type)
        if not validation["valid"]:
            role.tags.append("naming_violation")

        # Store role
        self.roles[role_id] = role

        return role

    def _generate_role_id(self, name: str, role_type: RoleType) -> str:
        """Generate role ID based on naming convention"""
        # Clean name for ID
        clean_name = re.sub(r'[^A-Za-z0-9]', '_', name.upper())[:20]

        prefixes = {
            RoleType.SINGLE: "Z",
            RoleType.COMPOSITE: "ZC",
            RoleType.DERIVED: "ZD",
            RoleType.TEMPLATE: "ZT",
            RoleType.EMERGENCY: "ZE_FF"
        }

        prefix = prefixes.get(role_type, "Z")
        unique = str(uuid.uuid4())[:4].upper()

        return f"{prefix}_{clean_name}_{unique}"

    def create_from_template(
        self,
        template_id: str,
        name: str,
        created_by: str,
        customizations: Dict = None
    ) -> Role:
        """Create a role from a template with customizations"""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")

        template = self.templates[template_id]

        role = self.create_role(
            name=name,
            description=f"Created from template: {template.name}",
            role_type=RoleType.SINGLE,
            created_by=created_by,
            template_id=template_id
        )

        # Apply customizations
        if customizations:
            if "org_levels" in customizations:
                role.org_level_values = customizations["org_levels"]
            if "transactions" in customizations:
                role.transaction_codes = customizations["transactions"]
            if "department" in customizations:
                role.department = customizations["department"]

        return role

    def create_composite_role(
        self,
        name: str,
        description: str,
        child_role_ids: List[str],
        created_by: str
    ) -> Role:
        """Create a composite role containing other roles"""
        # Validate child roles exist
        for role_id in child_role_ids:
            if role_id not in self.roles:
                raise ValueError(f"Child role {role_id} not found")

        role = self.create_role(
            name=name,
            description=description,
            role_type=RoleType.COMPOSITE,
            created_by=created_by
        )

        role.child_roles = child_role_ids

        # Aggregate permissions for analysis
        for child_id in child_role_ids:
            child = self.roles[child_id]
            role.transaction_codes.extend(child.transaction_codes)

        role.transaction_codes = list(set(role.transaction_codes))

        return role

    def create_derived_role(
        self,
        name: str,
        parent_role_id: str,
        org_level_values: Dict[str, List[str]],
        created_by: str
    ) -> Role:
        """Create a derived role from a parent with different org levels"""
        if parent_role_id not in self.roles:
            raise ValueError(f"Parent role {parent_role_id} not found")

        parent = self.roles[parent_role_id]

        role = self.create_role(
            name=name,
            description=f"Derived from {parent.name}",
            role_type=RoleType.DERIVED,
            created_by=created_by
        )

        role.parent_role = parent_role_id
        role.permissions = copy.deepcopy(parent.permissions)
        role.transaction_codes = parent.transaction_codes.copy()
        role.org_level_values = org_level_values
        role.business_process = parent.business_process

        return role

    # =========================================================================
    # Permission Management
    # =========================================================================

    def add_permission(
        self,
        role_id: str,
        permission: Permission,
        modified_by: str
    ) -> Role:
        """Add a permission to a role"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]
        role.permissions.append(permission)
        role.modified_at = datetime.now()
        role.modified_by = modified_by

        # Update risk level if critical permission
        if permission.is_critical:
            role.risk_level = "high"
            role.is_sensitive = True

        return role

    def add_transaction(
        self,
        role_id: str,
        transaction_code: str,
        modified_by: str
    ) -> Role:
        """Add a transaction code to a role"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]

        if transaction_code not in role.transaction_codes:
            role.transaction_codes.append(transaction_code)

            # Add S_TCODE permission
            tcode_perm = next(
                (p for p in role.permissions if p.auth_object == "S_TCODE"),
                None
            )
            if tcode_perm:
                tcode_perm.transaction_codes.append(transaction_code)
            else:
                role.permissions.append(Permission(
                    permission_type=PermissionType.TRANSACTION,
                    auth_object="S_TCODE",
                    transaction_codes=[transaction_code],
                    description=f"Transaction code access"
                ))

            role.modified_at = datetime.now()
            role.modified_by = modified_by

        return role

    def remove_permission(
        self,
        role_id: str,
        permission_id: str,
        modified_by: str
    ) -> Role:
        """Remove a permission from a role"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]
        role.permissions = [p for p in role.permissions if p.permission_id != permission_id]
        role.modified_at = datetime.now()
        role.modified_by = modified_by

        return role

    def set_org_levels(
        self,
        role_id: str,
        org_levels: Dict[str, List[str]],
        modified_by: str
    ) -> Role:
        """Set organizational level values for a role"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]
        role.org_level_values = org_levels
        role.modified_at = datetime.now()
        role.modified_by = modified_by

        return role

    # =========================================================================
    # Role Testing & Simulation
    # =========================================================================

    def test_role(
        self,
        role_id: str,
        test_types: List[str] = None
    ) -> List[RoleTestResult]:
        """
        Run comprehensive tests on a role.

        Test types: sod_check, permission_analysis, naming_check, completeness
        """
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]
        results = []

        test_types = test_types or ["sod_check", "permission_analysis", "naming_check", "completeness"]

        if "sod_check" in test_types:
            results.append(self._test_sod(role))

        if "permission_analysis" in test_types:
            results.append(self._test_permissions(role))

        if "naming_check" in test_types:
            results.append(self._test_naming(role))

        if "completeness" in test_types:
            results.append(self._test_completeness(role))

        self.test_history.extend(results)

        return results

    def _test_sod(self, role: Role) -> RoleTestResult:
        """Test role for SoD conflicts"""
        result = RoleTestResult(
            role_id=role.role_id,
            test_type="sod_check"
        )

        # Define conflicting transaction pairs
        conflicts = [
            (["ME21N", "ME22N"], ["MIGO", "MB01"]),  # PO vs GR
            (["XK01", "FK01"], ["F110"]),             # Vendor create vs Payment
            (["FB01"], ["F110"]),                     # Post doc vs Payment
            (["PA30"], ["PU30"]),                     # HR maintain vs Payroll
            (["SU01"], ["PFCG"]),                     # User admin vs Role admin
        ]

        tcodes = set(role.transaction_codes)

        for set1, set2 in conflicts:
            has_set1 = bool(tcodes & set(set1))
            has_set2 = bool(tcodes & set(set2))

            if has_set1 and has_set2:
                result.issues.append({
                    "type": "sod_conflict",
                    "severity": "high",
                    "description": f"SoD conflict: {set1} vs {set2}",
                    "conflicting_tcodes": list(tcodes & (set(set1) | set(set2)))
                })
                result.passed = False

        # Check for sensitive transactions
        sensitive_tcodes = ["SU01", "PFCG", "SE38", "SE16", "SM59", "SA38"]
        sensitive_found = tcodes & set(sensitive_tcodes)
        if sensitive_found:
            result.warnings.append({
                "type": "sensitive_access",
                "description": f"Contains sensitive transactions: {sensitive_found}"
            })

        result.details["transactions_checked"] = len(tcodes)
        result.details["conflicts_found"] = len(result.issues)

        return result

    def _test_permissions(self, role: Role) -> RoleTestResult:
        """Analyze permissions for issues"""
        result = RoleTestResult(
            role_id=role.role_id,
            test_type="permission_analysis"
        )

        for perm in role.permissions:
            # Check for wildcard values
            for field, values in perm.field_values.items():
                if "*" in values:
                    result.warnings.append({
                        "type": "wildcard_permission",
                        "permission_id": perm.permission_id,
                        "field": field,
                        "description": f"Wildcard (*) used in {perm.auth_object}.{field}"
                    })

            # Check for critical permissions
            if perm.is_critical:
                result.warnings.append({
                    "type": "critical_permission",
                    "permission_id": perm.permission_id,
                    "description": f"Critical permission: {perm.description}"
                })

        result.details["permissions_analyzed"] = len(role.permissions)
        result.details["warnings_count"] = len(result.warnings)

        return result

    def _test_naming(self, role: Role) -> RoleTestResult:
        """Check role naming conventions"""
        result = RoleTestResult(
            role_id=role.role_id,
            test_type="naming_check"
        )

        validation = self.validate_role_name(role.role_id, role.role_type)

        if not validation["valid"]:
            result.issues.append({
                "type": "naming_violation",
                "description": validation["message"],
                "expected_pattern": validation["pattern"]
            })
            result.passed = False

        # Check description length
        if len(role.description) < 20:
            result.warnings.append({
                "type": "short_description",
                "description": "Role description should be at least 20 characters"
            })

        return result

    def _test_completeness(self, role: Role) -> RoleTestResult:
        """Check role for completeness"""
        result = RoleTestResult(
            role_id=role.role_id,
            test_type="completeness"
        )

        missing = []

        if not role.owner:
            missing.append("owner")
        if not role.business_process:
            missing.append("business_process")
        if not role.department:
            missing.append("department")
        if not role.permissions and not role.transaction_codes:
            missing.append("permissions or transactions")
        if not role.documentation:
            missing.append("documentation")

        if missing:
            result.issues.append({
                "type": "incomplete_role",
                "missing_fields": missing
            })
            result.passed = False

        # Calculate completeness score
        total_fields = 6
        filled = total_fields - len(missing)
        result.details["completeness_score"] = round(filled / total_fields * 100, 1)

        return result

    def simulate_user_access(
        self,
        role_id: str,
        user_id: str,
        existing_roles: List[str] = None
    ) -> RoleTestResult:
        """Simulate what access a user would have with this role"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]
        result = RoleTestResult(
            role_id=role_id,
            test_type="user_simulation",
            test_user=user_id
        )

        # Aggregate all transactions
        all_transactions = set(role.transaction_codes)

        # Add transactions from existing roles
        if existing_roles:
            for existing_id in existing_roles:
                if existing_id in self.roles:
                    all_transactions.update(self.roles[existing_id].transaction_codes)

        # Check for conflicts with combined access
        result.details["total_transactions"] = len(all_transactions)
        result.details["new_transactions"] = len(set(role.transaction_codes))
        result.details["all_transactions"] = list(all_transactions)

        # Run SoD check on combined access
        temp_role = Role(transaction_codes=list(all_transactions))
        sod_result = self._test_sod(temp_role)

        if not sod_result.passed:
            result.passed = False
            result.issues.extend(sod_result.issues)

        return result

    # =========================================================================
    # Version Control
    # =========================================================================

    def create_version(
        self,
        role_id: str,
        change_summary: str,
        modified_by: str
    ) -> RoleVersion:
        """Create a new version of a role"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]

        # Mark previous version as not current
        for v in role.versions:
            v.is_current = False

        new_version = RoleVersion(
            version_number=role.current_version + 1,
            created_at=datetime.now(),
            created_by=modified_by,
            change_summary=change_summary,
            permissions_snapshot=[p.to_dict() for p in role.permissions],
            is_current=True
        )

        role.versions.append(new_version)
        role.current_version = new_version.version_number
        role.modified_at = datetime.now()
        role.modified_by = modified_by

        return new_version

    def rollback_version(
        self,
        role_id: str,
        version_number: int,
        modified_by: str
    ) -> Role:
        """Rollback role to a previous version"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]

        # Find target version
        target_version = next(
            (v for v in role.versions if v.version_number == version_number),
            None
        )

        if not target_version:
            raise ValueError(f"Version {version_number} not found")

        # Restore permissions from snapshot
        role.permissions = [
            Permission(**{
                **perm,
                "permission_type": PermissionType(perm["permission_type"])
            })
            for perm in target_version.permissions_snapshot
        ]

        # Create new version noting rollback
        self.create_version(
            role_id,
            f"Rolled back to version {version_number}",
            modified_by
        )

        return role

    def compare_versions(
        self,
        role_id: str,
        version_a: int,
        version_b: int
    ) -> Dict:
        """Compare two versions of a role"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]

        va = next((v for v in role.versions if v.version_number == version_a), None)
        vb = next((v for v in role.versions if v.version_number == version_b), None)

        if not va or not vb:
            raise ValueError("One or both versions not found")

        # Compare permissions
        perms_a = {p["permission_id"]: p for p in va.permissions_snapshot}
        perms_b = {p["permission_id"]: p for p in vb.permissions_snapshot}

        added = set(perms_b.keys()) - set(perms_a.keys())
        removed = set(perms_a.keys()) - set(perms_b.keys())
        common = set(perms_a.keys()) & set(perms_b.keys())

        modified = []
        for perm_id in common:
            if perms_a[perm_id] != perms_b[perm_id]:
                modified.append({
                    "permission_id": perm_id,
                    "version_a": perms_a[perm_id],
                    "version_b": perms_b[perm_id]
                })

        return {
            "role_id": role_id,
            "version_a": version_a,
            "version_b": version_b,
            "added_permissions": list(added),
            "removed_permissions": list(removed),
            "modified_permissions": modified,
            "summary": {
                "added": len(added),
                "removed": len(removed),
                "modified": len(modified)
            }
        }

    # =========================================================================
    # Naming Standards
    # =========================================================================

    def validate_role_name(self, role_id: str, role_type: RoleType) -> Dict:
        """Validate role name against naming conventions"""
        pattern_map = {
            RoleType.SINGLE: "standard",
            RoleType.COMPOSITE: "composite",
            RoleType.DERIVED: "derived",
            RoleType.TEMPLATE: "template",
            RoleType.EMERGENCY: "emergency"
        }

        pattern_name = pattern_map.get(role_type, "standard")
        pattern = self.NAMING_PATTERNS[pattern_name]

        is_valid = bool(re.match(pattern, role_id))

        return {
            "valid": is_valid,
            "role_id": role_id,
            "pattern": pattern,
            "pattern_name": pattern_name,
            "message": "Valid role name" if is_valid else f"Role name should match pattern: {pattern}"
        }

    def suggest_role_name(
        self,
        description: str,
        role_type: RoleType,
        department: str = ""
    ) -> str:
        """Suggest a role name based on description"""
        # Extract key words
        words = re.findall(r'\b[A-Za-z]+\b', description.upper())
        key_words = [w for w in words if len(w) > 3][:3]

        prefix_map = {
            RoleType.SINGLE: "Z",
            RoleType.COMPOSITE: "ZC",
            RoleType.DERIVED: "ZD",
            RoleType.TEMPLATE: "ZT",
            RoleType.EMERGENCY: "ZE_FF"
        }

        prefix = prefix_map.get(role_type, "Z")
        dept_code = department[:3].upper() if department else "GEN"

        name_part = "_".join(key_words) if key_words else "ROLE"

        return f"{prefix}_{dept_code}_{name_part}"

    # =========================================================================
    # Documentation Generation
    # =========================================================================

    def generate_documentation(self, role_id: str) -> str:
        """Generate comprehensive documentation for a role"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]

        doc = f"""
# Role Documentation: {role.name}

## Overview
- **Role ID**: {role.role_id}
- **Type**: {role.role_type.value}
- **Status**: {role.status.value}
- **Risk Level**: {role.risk_level}
- **Business Process**: {role.business_process or 'Not specified'}
- **Department**: {role.department or 'Not specified'}
- **Owner**: {role.owner or 'Not assigned'}

## Description
{role.description}

## Transaction Codes
{chr(10).join(f'- {tc}' for tc in role.transaction_codes) if role.transaction_codes else 'No direct transaction codes assigned'}

## Permissions ({len(role.permissions)} total)
"""

        for perm in role.permissions:
            doc += f"""
### {perm.auth_object}
- **Type**: {perm.permission_type.value}
- **Description**: {perm.description}
- **Risk Level**: {perm.risk_level}
- **Critical**: {'Yes' if perm.is_critical else 'No'}
"""
            if perm.field_values:
                doc += "- **Field Values**:\n"
                for field, values in perm.field_values.items():
                    doc += f"  - {field}: {', '.join(values)}\n"

        if role.org_level_values:
            doc += "\n## Organizational Levels\n"
            for org, values in role.org_level_values.items():
                doc += f"- **{org}**: {', '.join(values)}\n"

        if role.role_type == RoleType.COMPOSITE:
            doc += "\n## Child Roles\n"
            for child_id in role.child_roles:
                child = self.roles.get(child_id)
                doc += f"- {child_id}: {child.name if child else 'Unknown'}\n"

        if role.role_type == RoleType.DERIVED:
            doc += f"\n## Parent Role\n- {role.parent_role}\n"

        doc += f"""
## Version History
- **Current Version**: {role.current_version}
- **Created**: {role.created_at.strftime('%Y-%m-%d %H:%M')} by {role.created_by}
- **Last Modified**: {role.modified_at.strftime('%Y-%m-%d %H:%M')} by {role.modified_by}

### Version Log
"""
        for v in role.versions[-5:]:  # Last 5 versions
            doc += f"- v{v.version_number} ({v.created_at.strftime('%Y-%m-%d')}): {v.change_summary}\n"

        if role.sod_conflicts:
            doc += f"\n## ⚠️ SoD Conflicts\n"
            for conflict in role.sod_conflicts:
                doc += f"- {conflict}\n"

        return doc

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    def submit_for_review(self, role_id: str, submitted_by: str) -> Role:
        """Submit role for approval review"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]

        if role.status != RoleStatus.DRAFT:
            raise ValueError(f"Role must be in DRAFT status to submit for review")

        role.status = RoleStatus.IN_REVIEW
        role.modified_at = datetime.now()
        role.modified_by = submitted_by
        role.change_history.append({
            "action": "submitted_for_review",
            "by": submitted_by,
            "at": datetime.now().isoformat()
        })

        return role

    def approve_role(self, role_id: str, approved_by: str) -> Role:
        """Approve a role"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]

        if role.status != RoleStatus.IN_REVIEW:
            raise ValueError(f"Role must be IN_REVIEW to approve")

        role.status = RoleStatus.APPROVED
        role.modified_at = datetime.now()
        role.modified_by = approved_by
        role.change_history.append({
            "action": "approved",
            "by": approved_by,
            "at": datetime.now().isoformat()
        })

        return role

    def activate_role(self, role_id: str, activated_by: str) -> Role:
        """Activate an approved role"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]

        if role.status != RoleStatus.APPROVED:
            raise ValueError(f"Role must be APPROVED to activate")

        role.status = RoleStatus.ACTIVE
        role.valid_from = datetime.now()
        role.modified_at = datetime.now()
        role.modified_by = activated_by
        role.change_history.append({
            "action": "activated",
            "by": activated_by,
            "at": datetime.now().isoformat()
        })

        return role

    def deprecate_role(self, role_id: str, deprecated_by: str, reason: str) -> Role:
        """Deprecate a role"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]
        role.status = RoleStatus.DEPRECATED
        role.valid_to = datetime.now()
        role.modified_at = datetime.now()
        role.modified_by = deprecated_by
        role.change_history.append({
            "action": "deprecated",
            "by": deprecated_by,
            "reason": reason,
            "at": datetime.now().isoformat()
        })

        return role

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_role(self, role_id: str) -> Optional[Role]:
        """Get a role by ID"""
        return self.roles.get(role_id)

    def list_roles(
        self,
        status: RoleStatus = None,
        role_type: RoleType = None,
        department: str = None,
        owner: str = None,
        search: str = None
    ) -> List[Role]:
        """List roles with filters"""
        roles = list(self.roles.values())

        if status:
            roles = [r for r in roles if r.status == status]
        if role_type:
            roles = [r for r in roles if r.role_type == role_type]
        if department:
            roles = [r for r in roles if r.department.lower() == department.lower()]
        if owner:
            roles = [r for r in roles if r.owner == owner]
        if search:
            search_lower = search.lower()
            roles = [r for r in roles if
                    search_lower in r.name.lower() or
                    search_lower in r.description.lower() or
                    search_lower in r.role_id.lower()]

        return roles

    def get_templates(self) -> List[Role]:
        """Get all role templates"""
        return list(self.templates.values())

    def get_statistics(self) -> Dict:
        """Get role design statistics"""
        roles = list(self.roles.values())

        by_status = {}
        for status in RoleStatus:
            by_status[status.value] = len([r for r in roles if r.status == status])

        by_type = {}
        for rtype in RoleType:
            by_type[rtype.value] = len([r for r in roles if r.role_type == rtype])

        return {
            "total_roles": len(roles),
            "by_status": by_status,
            "by_type": by_type,
            "templates_available": len(self.templates),
            "tests_run": len(self.test_history),
            "tests_passed": len([t for t in self.test_history if t.passed]),
            "tests_failed": len([t for t in self.test_history if not t.passed])
        }
