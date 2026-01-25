"""
Cross-System Correlation Module

Provides multi-system identity correlation, unified access views,
and cross-system SoD analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime
from enum import Enum
import uuid


class SystemType(Enum):
    """Types of connected systems"""
    SAP_ECC = "sap_ecc"
    SAP_S4HANA = "sap_s4hana"
    SAP_BW = "sap_bw"
    ACTIVE_DIRECTORY = "active_directory"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    SALESFORCE = "salesforce"
    SERVICENOW = "servicenow"
    ORACLE_EBS = "oracle_ebs"
    WORKDAY = "workday"
    CUSTOM = "custom"


class CorrelationStatus(Enum):
    """Status of identity correlation"""
    CORRELATED = "correlated"
    PARTIAL = "partial"
    UNCORRELATED = "uncorrelated"
    CONFLICT = "conflict"


class ConflictSeverity(Enum):
    """Severity of cross-system conflicts"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SystemAccount:
    """An account in a specific system"""
    account_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    system_id: str = ""
    system_type: SystemType = SystemType.SAP_ECC
    username: str = ""
    display_name: str = ""
    email: str = ""
    status: str = "active"  # active, disabled, locked
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "account_id": self.account_id,
            "system_id": self.system_id,
            "system_type": self.system_type.value,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "status": self.status,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "attributes": self.attributes
        }


@dataclass
class SystemAccess:
    """Access/entitlements in a specific system"""
    access_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    system_id: str = ""
    system_type: SystemType = SystemType.SAP_ECC
    account_id: str = ""

    # Access details (varies by system)
    roles: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    entitlements: List[Dict] = field(default_factory=list)

    # Normalized access for cross-system analysis
    normalized_permissions: List[str] = field(default_factory=list)

    # Risk
    risk_level: str = "low"
    is_privileged: bool = False

    def to_dict(self) -> Dict:
        return {
            "access_id": self.access_id,
            "system_id": self.system_id,
            "system_type": self.system_type.value,
            "account_id": self.account_id,
            "roles": self.roles,
            "groups": self.groups,
            "permissions": self.permissions,
            "entitlements": self.entitlements,
            "normalized_permissions": self.normalized_permissions,
            "risk_level": self.risk_level,
            "is_privileged": self.is_privileged
        }


@dataclass
class Identity:
    """A correlated identity across systems"""
    identity_id: str = field(default_factory=lambda: f"ID_{str(uuid.uuid4())[:8].upper()}")
    correlation_status: CorrelationStatus = CorrelationStatus.UNCORRELATED

    # Core identity attributes
    display_name: str = ""
    email: str = ""
    employee_id: str = ""
    department: str = ""
    job_title: str = ""
    manager_id: str = ""
    location: str = ""

    # Linked accounts
    accounts: List[SystemAccount] = field(default_factory=list)

    # Access across systems
    system_access: List[SystemAccess] = field(default_factory=list)

    # Correlation metadata
    correlation_confidence: float = 0.0
    correlation_method: str = ""  # email, employee_id, manual, etc.
    correlation_date: Optional[datetime] = None
    correlated_by: str = ""

    # Risk
    aggregate_risk_level: str = "low"
    has_cross_system_conflicts: bool = False
    conflict_count: int = 0

    # Lifecycle
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "identity_id": self.identity_id,
            "correlation_status": self.correlation_status.value,
            "display_name": self.display_name,
            "email": self.email,
            "employee_id": self.employee_id,
            "department": self.department,
            "job_title": self.job_title,
            "manager_id": self.manager_id,
            "location": self.location,
            "accounts": [a.to_dict() for a in self.accounts],
            "system_access": [s.to_dict() for s in self.system_access],
            "correlation_confidence": self.correlation_confidence,
            "correlation_method": self.correlation_method,
            "correlation_date": self.correlation_date.isoformat() if self.correlation_date else None,
            "correlated_by": self.correlated_by,
            "aggregate_risk_level": self.aggregate_risk_level,
            "has_cross_system_conflicts": self.has_cross_system_conflicts,
            "conflict_count": self.conflict_count,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat()
        }


@dataclass
class UnifiedAccessView:
    """Unified view of access across all systems for an identity"""
    view_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    identity_id: str = ""
    generated_at: datetime = field(default_factory=datetime.now)

    # Aggregated access
    all_roles: List[Dict] = field(default_factory=list)  # [{system, role, risk}]
    all_permissions: List[Dict] = field(default_factory=list)
    all_groups: List[Dict] = field(default_factory=list)

    # Normalized/deduplicated
    unique_capabilities: List[str] = field(default_factory=list)

    # By system
    access_by_system: Dict[str, List[Dict]] = field(default_factory=dict)

    # Risk summary
    total_roles: int = 0
    total_permissions: int = 0
    privileged_access_count: int = 0
    high_risk_access_count: int = 0
    systems_with_access: int = 0

    def to_dict(self) -> Dict:
        return {
            "view_id": self.view_id,
            "identity_id": self.identity_id,
            "generated_at": self.generated_at.isoformat(),
            "all_roles": self.all_roles,
            "all_permissions": self.all_permissions,
            "all_groups": self.all_groups,
            "unique_capabilities": self.unique_capabilities,
            "access_by_system": self.access_by_system,
            "summary": {
                "total_roles": self.total_roles,
                "total_permissions": self.total_permissions,
                "privileged_access_count": self.privileged_access_count,
                "high_risk_access_count": self.high_risk_access_count,
                "systems_with_access": self.systems_with_access
            }
        }


@dataclass
class CorrelationRule:
    """Rule for correlating identities across systems"""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    is_active: bool = True
    priority: int = 1

    # Matching criteria
    source_system: str = ""
    target_system: str = ""
    match_fields: List[Dict] = field(default_factory=list)  # [{source_field, target_field, match_type}]
    confidence_threshold: float = 0.8

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "priority": self.priority,
            "source_system": self.source_system,
            "target_system": self.target_system,
            "match_fields": self.match_fields,
            "confidence_threshold": self.confidence_threshold
        }


@dataclass
class CrossSystemConflict:
    """A detected cross-system SoD or access conflict"""
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    identity_id: str = ""
    severity: ConflictSeverity = ConflictSeverity.MEDIUM

    # Conflict details
    conflict_type: str = ""  # sod, toxic_combination, privileged_accumulation
    description: str = ""

    # Systems involved
    systems_involved: List[str] = field(default_factory=list)

    # Access causing conflict
    conflicting_access: List[Dict] = field(default_factory=list)

    # Rule reference
    rule_id: str = ""
    rule_name: str = ""

    # Status
    status: str = "open"  # open, mitigated, accepted, resolved
    mitigating_control_id: Optional[str] = None

    # Timestamps
    detected_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "conflict_id": self.conflict_id,
            "identity_id": self.identity_id,
            "severity": self.severity.value,
            "conflict_type": self.conflict_type,
            "description": self.description,
            "systems_involved": self.systems_involved,
            "conflicting_access": self.conflicting_access,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "status": self.status,
            "mitigating_control_id": self.mitigating_control_id,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


class CrossSystemManager:
    """
    Cross-System Identity & Access Manager.

    Provides:
    - Multi-system identity correlation
    - Unified access views
    - Cross-system SoD analysis
    - Identity governance across platforms
    """

    # Standard correlation rules
    STANDARD_CORRELATION_RULES = [
        {
            "name": "Email Match",
            "match_fields": [{"source_field": "email", "target_field": "email", "match_type": "exact"}],
            "confidence": 0.95
        },
        {
            "name": "Employee ID Match",
            "match_fields": [{"source_field": "employee_id", "target_field": "employee_id", "match_type": "exact"}],
            "confidence": 0.99
        },
        {
            "name": "Name + Department Match",
            "match_fields": [
                {"source_field": "display_name", "target_field": "display_name", "match_type": "fuzzy"},
                {"source_field": "department", "target_field": "department", "match_type": "exact"}
            ],
            "confidence": 0.80
        }
    ]

    # Cross-system SoD rules
    CROSS_SYSTEM_SOD_RULES = [
        {
            "id": "XSOD001",
            "name": "SAP Vendor Create + AD Payment System Admin",
            "severity": ConflictSeverity.CRITICAL,
            "systems": ["sap_ecc", "active_directory"],
            "condition": {
                "sap_ecc": {"roles": ["Z_FI_VENDOR_CREATE"], "transactions": ["XK01", "FK01"]},
                "active_directory": {"groups": ["Payment_System_Admins", "Treasury_Admin"]}
            }
        },
        {
            "id": "XSOD002",
            "name": "HR Admin across SAP and Workday",
            "severity": ConflictSeverity.HIGH,
            "systems": ["sap_ecc", "workday"],
            "condition": {
                "sap_ecc": {"transactions": ["PA30", "PA40"]},
                "workday": {"roles": ["HR_Administrator", "Compensation_Admin"]}
            }
        },
        {
            "id": "XSOD003",
            "name": "IT Admin across multiple systems",
            "severity": ConflictSeverity.CRITICAL,
            "systems": ["sap_ecc", "active_directory", "azure_ad"],
            "condition": {
                "sap_ecc": {"transactions": ["SU01", "PFCG"]},
                "active_directory": {"groups": ["Domain Admins", "Enterprise Admins"]},
                "azure_ad": {"roles": ["Global Administrator"]}
            }
        }
    ]

    # Permission normalization mapping
    PERMISSION_NORMALIZATION = {
        # SAP transactions to normalized permissions
        "XK01": "vendor:create",
        "FK01": "vendor:create",
        "XK02": "vendor:modify",
        "F110": "payment:execute",
        "ME21N": "purchase_order:create",
        "MIGO": "goods_receipt:post",
        "PA30": "hr_master:maintain",
        "SU01": "user:admin",
        "PFCG": "role:admin",

        # AD groups to normalized permissions
        "Domain Admins": "ad:domain_admin",
        "Enterprise Admins": "ad:enterprise_admin",
        "Account Operators": "ad:account_operator",

        # Azure AD roles
        "Global Administrator": "azure:global_admin",
        "User Administrator": "azure:user_admin",
        "Privileged Role Administrator": "azure:role_admin"
    }

    def __init__(self):
        self.identities: Dict[str, Identity] = {}
        self.correlation_rules: List[CorrelationRule] = []
        self.conflicts: Dict[str, CrossSystemConflict] = {}
        self.systems: Dict[str, Dict] = {}  # system_id -> system_info
        self._initialize_standard_rules()
        self._initialize_demo_systems()

    def _initialize_standard_rules(self):
        """Initialize standard correlation rules"""
        for rule_def in self.STANDARD_CORRELATION_RULES:
            rule = CorrelationRule(
                name=rule_def["name"],
                match_fields=rule_def["match_fields"],
                confidence_threshold=rule_def["confidence"]
            )
            self.correlation_rules.append(rule)

    def _initialize_demo_systems(self):
        """Initialize demo connected systems"""
        self.systems = {
            "SAP_ECC_PRD": {
                "system_id": "SAP_ECC_PRD",
                "name": "SAP ECC Production",
                "type": SystemType.SAP_ECC.value,
                "status": "connected",
                "last_sync": datetime.now().isoformat()
            },
            "AD_CORP": {
                "system_id": "AD_CORP",
                "name": "Corporate Active Directory",
                "type": SystemType.ACTIVE_DIRECTORY.value,
                "status": "connected",
                "last_sync": datetime.now().isoformat()
            },
            "AZURE_TENANT": {
                "system_id": "AZURE_TENANT",
                "name": "Azure AD Tenant",
                "type": SystemType.AZURE_AD.value,
                "status": "connected",
                "last_sync": datetime.now().isoformat()
            },
            "WORKDAY_HCM": {
                "system_id": "WORKDAY_HCM",
                "name": "Workday HCM",
                "type": SystemType.WORKDAY.value,
                "status": "connected",
                "last_sync": datetime.now().isoformat()
            }
        }

    # =========================================================================
    # Identity Management
    # =========================================================================

    def create_identity(
        self,
        display_name: str,
        email: str,
        employee_id: str = "",
        department: str = "",
        job_title: str = "",
        **kwargs
    ) -> Identity:
        """Create a new identity"""
        identity = Identity(
            display_name=display_name,
            email=email,
            employee_id=employee_id,
            department=department,
            job_title=job_title
        )

        for key, value in kwargs.items():
            if hasattr(identity, key):
                setattr(identity, key, value)

        self.identities[identity.identity_id] = identity
        return identity

    def link_account(
        self,
        identity_id: str,
        system_id: str,
        system_type: SystemType,
        username: str,
        **kwargs
    ) -> Identity:
        """Link a system account to an identity"""
        if identity_id not in self.identities:
            raise ValueError(f"Identity {identity_id} not found")

        identity = self.identities[identity_id]

        account = SystemAccount(
            system_id=system_id,
            system_type=system_type,
            username=username
        )

        for key, value in kwargs.items():
            if hasattr(account, key):
                setattr(account, key, value)

        identity.accounts.append(account)
        identity.modified_at = datetime.now()

        # Update correlation status
        if len(identity.accounts) > 1:
            identity.correlation_status = CorrelationStatus.CORRELATED
        else:
            identity.correlation_status = CorrelationStatus.PARTIAL

        return identity

    def add_system_access(
        self,
        identity_id: str,
        system_id: str,
        roles: List[str] = None,
        groups: List[str] = None,
        permissions: List[str] = None,
        is_privileged: bool = False
    ) -> Identity:
        """Add access information for a system"""
        if identity_id not in self.identities:
            raise ValueError(f"Identity {identity_id} not found")

        identity = self.identities[identity_id]

        # Find system type
        system_info = self.systems.get(system_id, {})
        system_type = SystemType(system_info.get("type", "custom"))

        access = SystemAccess(
            system_id=system_id,
            system_type=system_type,
            roles=roles or [],
            groups=groups or [],
            permissions=permissions or [],
            is_privileged=is_privileged
        )

        # Normalize permissions
        access.normalized_permissions = self._normalize_permissions(
            roles or [], groups or [], permissions or []
        )

        # Determine risk level
        if is_privileged:
            access.risk_level = "critical"
        elif any(p in ["user:admin", "role:admin", "ad:domain_admin"] for p in access.normalized_permissions):
            access.risk_level = "high"
        else:
            access.risk_level = "low"

        identity.system_access.append(access)
        identity.modified_at = datetime.now()

        return identity

    def _normalize_permissions(
        self,
        roles: List[str],
        groups: List[str],
        permissions: List[str]
    ) -> List[str]:
        """Normalize permissions across systems"""
        normalized = set()

        for item in roles + groups + permissions:
            if item in self.PERMISSION_NORMALIZATION:
                normalized.add(self.PERMISSION_NORMALIZATION[item])
            else:
                normalized.add(f"raw:{item}")

        return list(normalized)

    def get_identity(self, identity_id: str) -> Optional[Identity]:
        """Get an identity by ID"""
        return self.identities.get(identity_id)

    def find_identity_by_email(self, email: str) -> Optional[Identity]:
        """Find an identity by email"""
        for identity in self.identities.values():
            if identity.email.lower() == email.lower():
                return identity
        return None

    def list_identities(
        self,
        correlation_status: CorrelationStatus = None,
        department: str = None,
        has_conflicts: bool = None,
        search: str = None
    ) -> List[Identity]:
        """List identities with filters"""
        identities = list(self.identities.values())

        if correlation_status:
            identities = [i for i in identities if i.correlation_status == correlation_status]
        if department:
            identities = [i for i in identities if i.department.lower() == department.lower()]
        if has_conflicts is not None:
            identities = [i for i in identities if i.has_cross_system_conflicts == has_conflicts]
        if search:
            search_lower = search.lower()
            identities = [i for i in identities if
                        search_lower in i.display_name.lower() or
                        search_lower in i.email.lower() or
                        search_lower in i.employee_id.lower()]

        return identities

    # =========================================================================
    # Correlation
    # =========================================================================

    def correlate_accounts(
        self,
        source_account: Dict,
        target_accounts: List[Dict]
    ) -> List[Dict]:
        """Find matching accounts using correlation rules"""
        matches = []

        for target in target_accounts:
            for rule in self.correlation_rules:
                if not rule.is_active:
                    continue

                confidence = self._calculate_match_confidence(
                    source_account, target, rule.match_fields
                )

                if confidence >= rule.confidence_threshold:
                    matches.append({
                        "target_account": target,
                        "confidence": confidence,
                        "rule_used": rule.name
                    })
                    break

        return sorted(matches, key=lambda x: x["confidence"], reverse=True)

    def _calculate_match_confidence(
        self,
        source: Dict,
        target: Dict,
        match_fields: List[Dict]
    ) -> float:
        """Calculate confidence score for a match"""
        if not match_fields:
            return 0.0

        total_score = 0.0
        field_count = len(match_fields)

        for field_config in match_fields:
            source_field = field_config["source_field"]
            target_field = field_config["target_field"]
            match_type = field_config.get("match_type", "exact")

            source_value = source.get(source_field, "")
            target_value = target.get(target_field, "")

            if not source_value or not target_value:
                continue

            if match_type == "exact":
                if str(source_value).lower() == str(target_value).lower():
                    total_score += 1.0
            elif match_type == "fuzzy":
                # Simple fuzzy match - check if names are similar
                similarity = self._fuzzy_match(str(source_value), str(target_value))
                total_score += similarity

        return total_score / field_count if field_count > 0 else 0.0

    def _fuzzy_match(self, str1: str, str2: str) -> float:
        """Simple fuzzy string matching"""
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()

        if str1 == str2:
            return 1.0

        # Check if one contains the other
        if str1 in str2 or str2 in str1:
            return 0.8

        # Check common words
        words1 = set(str1.split())
        words2 = set(str2.split())
        common = words1 & words2

        if not words1 or not words2:
            return 0.0

        return len(common) / max(len(words1), len(words2))

    def auto_correlate(self) -> Dict:
        """Run automatic correlation across all uncorrelated accounts"""
        # This would normally pull from connected systems
        # For demo, we'll just return statistics
        return {
            "status": "completed",
            "accounts_analyzed": len(self.identities) * 3,
            "correlations_found": 0,
            "confidence_threshold": 0.8
        }

    # =========================================================================
    # Unified Access View
    # =========================================================================

    def get_unified_access_view(self, identity_id: str) -> UnifiedAccessView:
        """Generate unified access view for an identity"""
        if identity_id not in self.identities:
            raise ValueError(f"Identity {identity_id} not found")

        identity = self.identities[identity_id]
        view = UnifiedAccessView(identity_id=identity_id)

        # Aggregate all access
        for access in identity.system_access:
            system_name = access.system_id

            # Roles
            for role in access.roles:
                view.all_roles.append({
                    "system": system_name,
                    "role": role,
                    "risk_level": access.risk_level,
                    "is_privileged": access.is_privileged
                })

            # Groups
            for group in access.groups:
                view.all_groups.append({
                    "system": system_name,
                    "group": group
                })

            # Permissions
            for perm in access.normalized_permissions:
                view.all_permissions.append({
                    "system": system_name,
                    "permission": perm,
                    "risk_level": access.risk_level
                })

            # By system
            if system_name not in view.access_by_system:
                view.access_by_system[system_name] = []
            view.access_by_system[system_name].append({
                "roles": access.roles,
                "groups": access.groups,
                "permissions": access.normalized_permissions,
                "is_privileged": access.is_privileged
            })

        # Calculate unique capabilities
        view.unique_capabilities = list(set(
            p["permission"] for p in view.all_permissions
        ))

        # Summary
        view.total_roles = len(view.all_roles)
        view.total_permissions = len(view.all_permissions)
        view.privileged_access_count = sum(
            1 for r in view.all_roles if r.get("is_privileged")
        )
        view.high_risk_access_count = sum(
            1 for r in view.all_roles if r.get("risk_level") in ["high", "critical"]
        )
        view.systems_with_access = len(view.access_by_system)

        return view

    # =========================================================================
    # Cross-System SoD Analysis
    # =========================================================================

    def analyze_cross_system_sod(
        self,
        identity_id: str
    ) -> List[CrossSystemConflict]:
        """Analyze identity for cross-system SoD conflicts"""
        if identity_id not in self.identities:
            raise ValueError(f"Identity {identity_id} not found")

        identity = self.identities[identity_id]
        conflicts = []

        # Get all access indexed by system type
        access_by_type = {}
        for access in identity.system_access:
            type_key = access.system_type.value
            if type_key not in access_by_type:
                access_by_type[type_key] = {
                    "roles": set(),
                    "groups": set(),
                    "transactions": set(),
                    "permissions": set()
                }
            access_by_type[type_key]["roles"].update(access.roles)
            access_by_type[type_key]["groups"].update(access.groups)
            access_by_type[type_key]["permissions"].update(access.normalized_permissions)

        # Check against cross-system rules
        for rule in self.CROSS_SYSTEM_SOD_RULES:
            if self._check_cross_system_rule(access_by_type, rule):
                conflict = CrossSystemConflict(
                    identity_id=identity_id,
                    severity=rule["severity"],
                    conflict_type="cross_system_sod",
                    description=rule["name"],
                    systems_involved=rule["systems"],
                    rule_id=rule["id"],
                    rule_name=rule["name"],
                    conflicting_access=self._get_conflicting_access(access_by_type, rule)
                )
                conflicts.append(conflict)
                self.conflicts[conflict.conflict_id] = conflict

        # Update identity
        identity.has_cross_system_conflicts = len(conflicts) > 0
        identity.conflict_count = len(conflicts)

        return conflicts

    def _check_cross_system_rule(
        self,
        access_by_type: Dict,
        rule: Dict
    ) -> bool:
        """Check if a cross-system rule is violated"""
        conditions = rule.get("condition", {})

        for system_type, required in conditions.items():
            if system_type not in access_by_type:
                return False

            system_access = access_by_type[system_type]

            # Check roles
            if "roles" in required:
                if not any(r in system_access["roles"] for r in required["roles"]):
                    return False

            # Check groups
            if "groups" in required:
                if not any(g in system_access["groups"] for g in required["groups"]):
                    return False

            # Check transactions
            if "transactions" in required:
                if not any(t in system_access.get("transactions", set())
                          for t in required["transactions"]):
                    return False

        return True

    def _get_conflicting_access(
        self,
        access_by_type: Dict,
        rule: Dict
    ) -> List[Dict]:
        """Get the specific access causing the conflict"""
        conflicting = []
        conditions = rule.get("condition", {})

        for system_type, required in conditions.items():
            if system_type in access_by_type:
                system_access = access_by_type[system_type]
                matching = {}

                if "roles" in required:
                    matching["roles"] = list(
                        set(required["roles"]) & system_access["roles"]
                    )
                if "groups" in required:
                    matching["groups"] = list(
                        set(required["groups"]) & system_access["groups"]
                    )
                if "transactions" in required:
                    matching["transactions"] = list(
                        set(required["transactions"]) & system_access.get("transactions", set())
                    )

                conflicting.append({
                    "system": system_type,
                    "access": matching
                })

        return conflicting

    def analyze_all_identities(self) -> Dict:
        """Analyze all identities for cross-system conflicts"""
        results = {
            "total_analyzed": 0,
            "conflicts_found": 0,
            "identities_with_conflicts": 0,
            "by_severity": {s.value: 0 for s in ConflictSeverity}
        }

        for identity_id in self.identities:
            results["total_analyzed"] += 1
            conflicts = self.analyze_cross_system_sod(identity_id)

            if conflicts:
                results["identities_with_conflicts"] += 1
                results["conflicts_found"] += len(conflicts)

                for conflict in conflicts:
                    results["by_severity"][conflict.severity.value] += 1

        return results

    # =========================================================================
    # Conflict Management
    # =========================================================================

    def mitigate_conflict(
        self,
        conflict_id: str,
        control_id: str,
        mitigated_by: str
    ) -> CrossSystemConflict:
        """Mark a conflict as mitigated"""
        if conflict_id not in self.conflicts:
            raise ValueError(f"Conflict {conflict_id} not found")

        conflict = self.conflicts[conflict_id]
        conflict.status = "mitigated"
        conflict.mitigating_control_id = control_id

        return conflict

    def accept_conflict(
        self,
        conflict_id: str,
        accepted_by: str,
        justification: str
    ) -> CrossSystemConflict:
        """Accept a conflict (risk acceptance)"""
        if conflict_id not in self.conflicts:
            raise ValueError(f"Conflict {conflict_id} not found")

        conflict = self.conflicts[conflict_id]
        conflict.status = "accepted"

        return conflict

    def resolve_conflict(
        self,
        conflict_id: str,
        resolved_by: str
    ) -> CrossSystemConflict:
        """Mark a conflict as resolved"""
        if conflict_id not in self.conflicts:
            raise ValueError(f"Conflict {conflict_id} not found")

        conflict = self.conflicts[conflict_id]
        conflict.status = "resolved"
        conflict.resolved_at = datetime.now()

        # Update identity
        identity = self.identities.get(conflict.identity_id)
        if identity:
            identity.conflict_count = max(0, identity.conflict_count - 1)
            identity.has_cross_system_conflicts = identity.conflict_count > 0

        return conflict

    def list_conflicts(
        self,
        identity_id: str = None,
        severity: ConflictSeverity = None,
        status: str = None
    ) -> List[CrossSystemConflict]:
        """List conflicts with filters"""
        conflicts = list(self.conflicts.values())

        if identity_id:
            conflicts = [c for c in conflicts if c.identity_id == identity_id]
        if severity:
            conflicts = [c for c in conflicts if c.severity == severity]
        if status:
            conflicts = [c for c in conflicts if c.status == status]

        return conflicts

    # =========================================================================
    # System Management
    # =========================================================================

    def list_connected_systems(self) -> List[Dict]:
        """List all connected systems"""
        return list(self.systems.values())

    def get_system_statistics(self) -> Dict:
        """Get statistics by system"""
        stats = {}

        for system_id, system_info in self.systems.items():
            account_count = sum(
                1 for identity in self.identities.values()
                for account in identity.accounts
                if account.system_id == system_id
            )

            stats[system_id] = {
                "name": system_info["name"],
                "type": system_info["type"],
                "status": system_info["status"],
                "account_count": account_count
            }

        return stats

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict:
        """Get cross-system correlation statistics"""
        identities = list(self.identities.values())

        by_status = {}
        for status in CorrelationStatus:
            by_status[status.value] = len([i for i in identities if i.correlation_status == status])

        conflict_stats = {}
        for severity in ConflictSeverity:
            conflict_stats[severity.value] = len([
                c for c in self.conflicts.values() if c.severity == severity
            ])

        return {
            "total_identities": len(identities),
            "by_correlation_status": by_status,
            "total_conflicts": len(self.conflicts),
            "open_conflicts": len([c for c in self.conflicts.values() if c.status == "open"]),
            "conflicts_by_severity": conflict_stats,
            "identities_with_conflicts": len([i for i in identities if i.has_cross_system_conflicts]),
            "connected_systems": len(self.systems),
            "correlation_rules": len(self.correlation_rules)
        }
