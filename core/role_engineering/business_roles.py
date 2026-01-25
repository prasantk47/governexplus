"""
Business Role Framework

Manages business roles that map to technical roles,
providing a business-friendly layer for access management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid


class BusinessRoleStatus(Enum):
    """Status of business roles"""
    DRAFT = "draft"
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ApprovalRequirement(Enum):
    """Approval requirements for role requests"""
    NONE = "none"
    MANAGER = "manager"
    MANAGER_AND_OWNER = "manager_and_owner"
    MANAGER_OWNER_SECURITY = "manager_owner_security"
    CUSTOM = "custom"


@dataclass
class TechnicalRoleMapping:
    """Mapping from business role to technical roles"""
    mapping_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    technical_role_id: str = ""
    system_id: str = "SAP_ECC"
    is_required: bool = True  # False = optional/conditional
    condition: str = ""  # Condition for optional roles
    org_level_template: Dict[str, str] = field(default_factory=dict)  # Placeholders for org levels
    priority: int = 1  # For ordering

    def to_dict(self) -> Dict:
        return {
            "mapping_id": self.mapping_id,
            "technical_role_id": self.technical_role_id,
            "system_id": self.system_id,
            "is_required": self.is_required,
            "condition": self.condition,
            "org_level_template": self.org_level_template,
            "priority": self.priority
        }


@dataclass
class RoleOwnership:
    """Role ownership and stewardship"""
    owner_id: str = ""
    owner_name: str = ""
    owner_email: str = ""
    department: str = ""
    steward_id: Optional[str] = None
    steward_name: Optional[str] = None
    assigned_at: datetime = field(default_factory=datetime.now)
    review_frequency_days: int = 90
    last_review_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "owner_email": self.owner_email,
            "department": self.department,
            "steward_id": self.steward_id,
            "steward_name": self.steward_name,
            "assigned_at": self.assigned_at.isoformat(),
            "review_frequency_days": self.review_frequency_days,
            "last_review_date": self.last_review_date.isoformat() if self.last_review_date else None,
            "next_review_date": self.next_review_date.isoformat() if self.next_review_date else None
        }


@dataclass
class RoleCatalogEntry:
    """Entry in the role catalog for self-service"""
    catalog_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    business_role_id: str = ""
    display_name: str = ""
    short_description: str = ""
    long_description: str = ""
    category: str = ""
    subcategory: str = ""
    keywords: List[str] = field(default_factory=list)
    icon: str = ""
    is_requestable: bool = True
    is_featured: bool = False
    popularity_score: int = 0
    average_approval_days: float = 0.0
    request_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "catalog_id": self.catalog_id,
            "business_role_id": self.business_role_id,
            "display_name": self.display_name,
            "short_description": self.short_description,
            "long_description": self.long_description,
            "category": self.category,
            "subcategory": self.subcategory,
            "keywords": self.keywords,
            "icon": self.icon,
            "is_requestable": self.is_requestable,
            "is_featured": self.is_featured,
            "popularity_score": self.popularity_score,
            "average_approval_days": self.average_approval_days,
            "request_count": self.request_count
        }


@dataclass
class RequestTemplate:
    """Template for requesting a business role"""
    template_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    business_role_id: str = ""
    required_justification: bool = True
    justification_options: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    default_duration_days: Optional[int] = None
    max_duration_days: Optional[int] = None
    approval_workflow_id: Optional[str] = None
    auto_approve_conditions: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "template_id": self.template_id,
            "business_role_id": self.business_role_id,
            "required_justification": self.required_justification,
            "justification_options": self.justification_options,
            "required_fields": self.required_fields,
            "optional_fields": self.optional_fields,
            "default_duration_days": self.default_duration_days,
            "max_duration_days": self.max_duration_days,
            "approval_workflow_id": self.approval_workflow_id,
            "auto_approve_conditions": self.auto_approve_conditions
        }


@dataclass
class BusinessRole:
    """
    Business Role - High-level role representing a job function.

    Maps to one or more technical roles across systems.
    """
    role_id: str = field(default_factory=lambda: f"BR_{str(uuid.uuid4())[:8].upper()}")
    name: str = ""
    description: str = ""
    status: BusinessRoleStatus = BusinessRoleStatus.DRAFT

    # Business context
    business_process: str = ""
    department: str = ""
    job_function: str = ""
    job_titles: List[str] = field(default_factory=list)
    cost_centers: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)

    # Technical mappings
    technical_mappings: List[TechnicalRoleMapping] = field(default_factory=list)

    # Ownership
    ownership: Optional[RoleOwnership] = None

    # Catalog info
    catalog_entry: Optional[RoleCatalogEntry] = None

    # Request configuration
    request_template: Optional[RequestTemplate] = None
    approval_requirement: ApprovalRequirement = ApprovalRequirement.MANAGER

    # Risk & compliance
    risk_level: str = "low"
    is_sensitive: bool = False
    requires_certification: bool = True
    certification_frequency_days: int = 90
    sod_rule_ids: List[str] = field(default_factory=list)

    # Lifecycle
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    modified_at: datetime = field(default_factory=datetime.now)
    modified_by: str = ""
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None

    # Usage tracking
    current_assignments: int = 0
    total_requests: int = 0
    approval_rate: float = 0.0

    # Metadata
    tags: List[str] = field(default_factory=list)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "business_process": self.business_process,
            "department": self.department,
            "job_function": self.job_function,
            "job_titles": self.job_titles,
            "cost_centers": self.cost_centers,
            "locations": self.locations,
            "technical_mappings": [m.to_dict() for m in self.technical_mappings],
            "ownership": self.ownership.to_dict() if self.ownership else None,
            "catalog_entry": self.catalog_entry.to_dict() if self.catalog_entry else None,
            "request_template": self.request_template.to_dict() if self.request_template else None,
            "approval_requirement": self.approval_requirement.value,
            "risk_level": self.risk_level,
            "is_sensitive": self.is_sensitive,
            "requires_certification": self.requires_certification,
            "certification_frequency_days": self.certification_frequency_days,
            "sod_rule_ids": self.sod_rule_ids,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "modified_at": self.modified_at.isoformat(),
            "modified_by": self.modified_by,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "current_assignments": self.current_assignments,
            "total_requests": self.total_requests,
            "approval_rate": self.approval_rate,
            "tags": self.tags,
            "custom_attributes": self.custom_attributes
        }


@dataclass
class BusinessRoleAssignment:
    """Assignment of a business role to a user"""
    assignment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    business_role_id: str = ""
    user_id: str = ""
    assigned_at: datetime = field(default_factory=datetime.now)
    assigned_by: str = ""
    valid_from: datetime = field(default_factory=datetime.now)
    valid_to: Optional[datetime] = None
    request_id: Optional[str] = None
    status: str = "active"  # active, expired, revoked
    org_level_values: Dict[str, List[str]] = field(default_factory=dict)
    technical_roles_provisioned: List[str] = field(default_factory=list)
    last_certified: Optional[datetime] = None
    certified_by: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "assignment_id": self.assignment_id,
            "business_role_id": self.business_role_id,
            "user_id": self.user_id,
            "assigned_at": self.assigned_at.isoformat(),
            "assigned_by": self.assigned_by,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "request_id": self.request_id,
            "status": self.status,
            "org_level_values": self.org_level_values,
            "technical_roles_provisioned": self.technical_roles_provisioned,
            "last_certified": self.last_certified.isoformat() if self.last_certified else None,
            "certified_by": self.certified_by
        }


class BusinessRoleManager:
    """
    Business Role Manager.

    Manages business roles, their mappings to technical roles,
    catalog management, and role assignments.
    """

    # Standard categories for catalog
    STANDARD_CATEGORIES = [
        {"id": "finance", "name": "Finance & Accounting", "icon": "💰"},
        {"id": "procurement", "name": "Procurement & Sourcing", "icon": "🛒"},
        {"id": "hr", "name": "Human Resources", "icon": "👥"},
        {"id": "sales", "name": "Sales & Distribution", "icon": "📈"},
        {"id": "it", "name": "IT & Administration", "icon": "💻"},
        {"id": "operations", "name": "Operations & Production", "icon": "🏭"},
        {"id": "compliance", "name": "Compliance & Audit", "icon": "✅"},
        {"id": "management", "name": "Management & Reporting", "icon": "📊"}
    ]

    def __init__(self):
        self.business_roles: Dict[str, BusinessRole] = {}
        self.assignments: Dict[str, BusinessRoleAssignment] = {}
        self.user_assignments: Dict[str, List[str]] = {}  # user_id -> [assignment_ids]
        self._initialize_standard_roles()

    def _initialize_standard_roles(self):
        """Initialize standard business roles"""
        standard_roles = [
            {
                "name": "Accounts Payable Clerk",
                "description": "Process vendor invoices and manage payments",
                "business_process": "Procure-to-Pay",
                "department": "Finance",
                "job_function": "AP Processing",
                "category": "finance",
                "risk_level": "medium",
                "mappings": [
                    {"technical_role_id": "Z_FI_AP_CLERK", "system_id": "SAP_ECC"},
                ]
            },
            {
                "name": "Purchase Order Creator",
                "description": "Create and manage purchase orders",
                "business_process": "Procure-to-Pay",
                "department": "Procurement",
                "job_function": "Purchasing",
                "category": "procurement",
                "risk_level": "medium",
                "mappings": [
                    {"technical_role_id": "Z_MM_PO_CREATE", "system_id": "SAP_ECC"},
                ]
            },
            {
                "name": "HR Administrator",
                "description": "Manage employee master data and personnel actions",
                "business_process": "Hire-to-Retire",
                "department": "HR",
                "job_function": "HR Administration",
                "category": "hr",
                "risk_level": "high",
                "is_sensitive": True,
                "mappings": [
                    {"technical_role_id": "Z_HR_ADMIN", "system_id": "SAP_ECC"},
                ]
            },
            {
                "name": "Financial Analyst",
                "description": "Financial reporting and analysis",
                "business_process": "Record-to-Report",
                "department": "Finance",
                "job_function": "Financial Analysis",
                "category": "finance",
                "risk_level": "low",
                "mappings": [
                    {"technical_role_id": "Z_FI_ANALYST", "system_id": "SAP_ECC"},
                ]
            },
            {
                "name": "Warehouse Manager",
                "description": "Manage inventory and warehouse operations",
                "business_process": "Inventory Management",
                "department": "Operations",
                "job_function": "Warehouse Management",
                "category": "operations",
                "risk_level": "medium",
                "mappings": [
                    {"technical_role_id": "Z_MM_WM_MGR", "system_id": "SAP_ECC"},
                ]
            }
        ]

        for role_def in standard_roles:
            role = self.create_business_role(
                name=role_def["name"],
                description=role_def["description"],
                business_process=role_def["business_process"],
                department=role_def["department"],
                created_by="SYSTEM"
            )
            role.job_function = role_def["job_function"]
            role.risk_level = role_def.get("risk_level", "low")
            role.is_sensitive = role_def.get("is_sensitive", False)

            # Add mappings
            for mapping in role_def["mappings"]:
                role.technical_mappings.append(TechnicalRoleMapping(
                    technical_role_id=mapping["technical_role_id"],
                    system_id=mapping["system_id"]
                ))

            # Create catalog entry
            role.catalog_entry = RoleCatalogEntry(
                business_role_id=role.role_id,
                display_name=role.name,
                short_description=role.description[:100],
                long_description=role.description,
                category=role_def["category"],
                is_requestable=True
            )

            role.status = BusinessRoleStatus.ACTIVE

    # =========================================================================
    # Business Role CRUD
    # =========================================================================

    def create_business_role(
        self,
        name: str,
        description: str,
        business_process: str,
        department: str,
        created_by: str,
        **kwargs
    ) -> BusinessRole:
        """Create a new business role"""
        role = BusinessRole(
            name=name,
            description=description,
            business_process=business_process,
            department=department,
            created_by=created_by,
            modified_by=created_by
        )

        # Apply additional kwargs
        for key, value in kwargs.items():
            if hasattr(role, key):
                setattr(role, key, value)

        # Create default request template
        role.request_template = RequestTemplate(
            business_role_id=role.role_id,
            required_justification=True,
            justification_options=[
                "New hire requires access",
                "Job transfer/promotion",
                "Project requirement",
                "Temporary coverage",
                "Other (specify)"
            ]
        )

        self.business_roles[role.role_id] = role
        return role

    def update_business_role(
        self,
        role_id: str,
        modified_by: str,
        **updates
    ) -> BusinessRole:
        """Update a business role"""
        if role_id not in self.business_roles:
            raise ValueError(f"Business role {role_id} not found")

        role = self.business_roles[role_id]

        for key, value in updates.items():
            if hasattr(role, key) and key not in ['role_id', 'created_at', 'created_by']:
                setattr(role, key, value)

        role.modified_at = datetime.now()
        role.modified_by = modified_by

        return role

    def get_business_role(self, role_id: str) -> Optional[BusinessRole]:
        """Get a business role by ID"""
        return self.business_roles.get(role_id)

    def list_business_roles(
        self,
        status: BusinessRoleStatus = None,
        department: str = None,
        business_process: str = None,
        category: str = None,
        search: str = None,
        is_requestable: bool = None
    ) -> List[BusinessRole]:
        """List business roles with filters"""
        roles = list(self.business_roles.values())

        if status:
            roles = [r for r in roles if r.status == status]
        if department:
            roles = [r for r in roles if r.department.lower() == department.lower()]
        if business_process:
            roles = [r for r in roles if r.business_process.lower() == business_process.lower()]
        if category and roles:
            roles = [r for r in roles if r.catalog_entry and
                    r.catalog_entry.category == category]
        if is_requestable is not None:
            roles = [r for r in roles if r.catalog_entry and
                    r.catalog_entry.is_requestable == is_requestable]
        if search:
            search_lower = search.lower()
            roles = [r for r in roles if
                    search_lower in r.name.lower() or
                    search_lower in r.description.lower()]

        return roles

    # =========================================================================
    # Technical Mapping Management
    # =========================================================================

    def add_technical_mapping(
        self,
        role_id: str,
        technical_role_id: str,
        system_id: str,
        is_required: bool = True,
        condition: str = "",
        org_level_template: Dict[str, str] = None,
        modified_by: str = ""
    ) -> BusinessRole:
        """Add a technical role mapping to a business role"""
        if role_id not in self.business_roles:
            raise ValueError(f"Business role {role_id} not found")

        role = self.business_roles[role_id]

        mapping = TechnicalRoleMapping(
            technical_role_id=technical_role_id,
            system_id=system_id,
            is_required=is_required,
            condition=condition,
            org_level_template=org_level_template or {},
            priority=len(role.technical_mappings) + 1
        )

        role.technical_mappings.append(mapping)
        role.modified_at = datetime.now()
        role.modified_by = modified_by

        return role

    def remove_technical_mapping(
        self,
        role_id: str,
        mapping_id: str,
        modified_by: str
    ) -> BusinessRole:
        """Remove a technical mapping"""
        if role_id not in self.business_roles:
            raise ValueError(f"Business role {role_id} not found")

        role = self.business_roles[role_id]
        role.technical_mappings = [
            m for m in role.technical_mappings if m.mapping_id != mapping_id
        ]
        role.modified_at = datetime.now()
        role.modified_by = modified_by

        return role

    def get_technical_roles_for_business_role(
        self,
        role_id: str,
        org_level_values: Dict[str, List[str]] = None
    ) -> List[Dict]:
        """Get resolved technical roles for a business role"""
        if role_id not in self.business_roles:
            raise ValueError(f"Business role {role_id} not found")

        role = self.business_roles[role_id]
        result = []

        for mapping in role.technical_mappings:
            # Check conditions for conditional mappings
            if not mapping.is_required and mapping.condition:
                # Evaluate condition (simplified)
                # In real implementation, this would be more sophisticated
                pass

            tech_role = {
                "technical_role_id": mapping.technical_role_id,
                "system_id": mapping.system_id,
                "is_required": mapping.is_required,
                "org_levels": {}
            }

            # Resolve org level templates
            if org_level_values and mapping.org_level_template:
                for field, template in mapping.org_level_template.items():
                    if template.startswith("$"):
                        # Template variable like $COMPANY_CODE
                        var_name = template[1:]
                        if var_name in org_level_values:
                            tech_role["org_levels"][field] = org_level_values[var_name]
                    else:
                        tech_role["org_levels"][field] = [template]

            result.append(tech_role)

        return result

    # =========================================================================
    # Ownership Management
    # =========================================================================

    def assign_ownership(
        self,
        role_id: str,
        owner_id: str,
        owner_name: str,
        owner_email: str,
        department: str,
        steward_id: str = None,
        steward_name: str = None,
        review_frequency_days: int = 90
    ) -> BusinessRole:
        """Assign ownership to a business role"""
        if role_id not in self.business_roles:
            raise ValueError(f"Business role {role_id} not found")

        role = self.business_roles[role_id]

        role.ownership = RoleOwnership(
            owner_id=owner_id,
            owner_name=owner_name,
            owner_email=owner_email,
            department=department,
            steward_id=steward_id,
            steward_name=steward_name,
            review_frequency_days=review_frequency_days,
            next_review_date=datetime.now() + timedelta(days=review_frequency_days)
        )

        return role

    def record_ownership_review(
        self,
        role_id: str,
        reviewed_by: str
    ) -> BusinessRole:
        """Record that ownership was reviewed"""
        if role_id not in self.business_roles:
            raise ValueError(f"Business role {role_id} not found")

        role = self.business_roles[role_id]

        if role.ownership:
            role.ownership.last_review_date = datetime.now()
            role.ownership.next_review_date = datetime.now() + timedelta(
                days=role.ownership.review_frequency_days
            )

        return role

    def get_roles_needing_review(self) -> List[BusinessRole]:
        """Get roles where ownership review is due"""
        now = datetime.now()
        return [
            role for role in self.business_roles.values()
            if role.ownership and
            role.ownership.next_review_date and
            role.ownership.next_review_date <= now
        ]

    # =========================================================================
    # Catalog Management
    # =========================================================================

    def update_catalog_entry(
        self,
        role_id: str,
        display_name: str = None,
        short_description: str = None,
        long_description: str = None,
        category: str = None,
        subcategory: str = None,
        keywords: List[str] = None,
        is_requestable: bool = None,
        is_featured: bool = None
    ) -> BusinessRole:
        """Update the catalog entry for a business role"""
        if role_id not in self.business_roles:
            raise ValueError(f"Business role {role_id} not found")

        role = self.business_roles[role_id]

        if not role.catalog_entry:
            role.catalog_entry = RoleCatalogEntry(business_role_id=role_id)

        entry = role.catalog_entry
        if display_name:
            entry.display_name = display_name
        if short_description:
            entry.short_description = short_description
        if long_description:
            entry.long_description = long_description
        if category:
            entry.category = category
        if subcategory:
            entry.subcategory = subcategory
        if keywords:
            entry.keywords = keywords
        if is_requestable is not None:
            entry.is_requestable = is_requestable
        if is_featured is not None:
            entry.is_featured = is_featured

        return role

    def get_catalog(
        self,
        category: str = None,
        search: str = None,
        requestable_only: bool = True
    ) -> List[Dict]:
        """Get the role catalog for self-service"""
        roles = self.list_business_roles(
            status=BusinessRoleStatus.ACTIVE,
            is_requestable=requestable_only if requestable_only else None
        )

        if category:
            roles = [r for r in roles if r.catalog_entry and
                    r.catalog_entry.category == category]

        if search:
            search_lower = search.lower()
            filtered = []
            for r in roles:
                if r.catalog_entry:
                    if (search_lower in r.catalog_entry.display_name.lower() or
                        search_lower in r.catalog_entry.short_description.lower() or
                        any(search_lower in kw.lower() for kw in r.catalog_entry.keywords)):
                        filtered.append(r)
            roles = filtered

        # Sort by popularity
        roles.sort(key=lambda r: r.catalog_entry.popularity_score if r.catalog_entry else 0,
                  reverse=True)

        return [
            {
                "role_id": r.role_id,
                "catalog": r.catalog_entry.to_dict() if r.catalog_entry else None,
                "risk_level": r.risk_level,
                "is_sensitive": r.is_sensitive,
                "approval_requirement": r.approval_requirement.value,
                "department": r.department
            }
            for r in roles
        ]

    def get_catalog_categories(self) -> List[Dict]:
        """Get catalog categories with role counts"""
        categories = []

        for cat in self.STANDARD_CATEGORIES:
            count = len([
                r for r in self.business_roles.values()
                if r.catalog_entry and r.catalog_entry.category == cat["id"]
            ])
            categories.append({
                **cat,
                "role_count": count
            })

        return categories

    # =========================================================================
    # Role Assignment
    # =========================================================================

    def assign_role(
        self,
        role_id: str,
        user_id: str,
        assigned_by: str,
        valid_from: datetime = None,
        valid_to: datetime = None,
        request_id: str = None,
        org_level_values: Dict[str, List[str]] = None
    ) -> BusinessRoleAssignment:
        """Assign a business role to a user"""
        if role_id not in self.business_roles:
            raise ValueError(f"Business role {role_id} not found")

        role = self.business_roles[role_id]

        # Get technical roles to provision
        technical_roles = self.get_technical_roles_for_business_role(
            role_id, org_level_values
        )

        assignment = BusinessRoleAssignment(
            business_role_id=role_id,
            user_id=user_id,
            assigned_by=assigned_by,
            valid_from=valid_from or datetime.now(),
            valid_to=valid_to,
            request_id=request_id,
            org_level_values=org_level_values or {},
            technical_roles_provisioned=[t["technical_role_id"] for t in technical_roles]
        )

        self.assignments[assignment.assignment_id] = assignment

        # Track by user
        if user_id not in self.user_assignments:
            self.user_assignments[user_id] = []
        self.user_assignments[user_id].append(assignment.assignment_id)

        # Update role statistics
        role.current_assignments += 1
        role.total_requests += 1
        if role.catalog_entry:
            role.catalog_entry.request_count += 1
            role.catalog_entry.popularity_score += 1

        return assignment

    def revoke_assignment(
        self,
        assignment_id: str,
        revoked_by: str,
        reason: str = ""
    ) -> BusinessRoleAssignment:
        """Revoke a role assignment"""
        if assignment_id not in self.assignments:
            raise ValueError(f"Assignment {assignment_id} not found")

        assignment = self.assignments[assignment_id]
        assignment.status = "revoked"
        assignment.valid_to = datetime.now()

        # Update role statistics
        if assignment.business_role_id in self.business_roles:
            self.business_roles[assignment.business_role_id].current_assignments -= 1

        return assignment

    def get_user_assignments(
        self,
        user_id: str,
        include_expired: bool = False
    ) -> List[BusinessRoleAssignment]:
        """Get all role assignments for a user"""
        assignment_ids = self.user_assignments.get(user_id, [])
        assignments = [self.assignments[aid] for aid in assignment_ids]

        if not include_expired:
            now = datetime.now()
            assignments = [
                a for a in assignments
                if a.status == "active" and
                (a.valid_to is None or a.valid_to > now)
            ]

        return assignments

    def get_role_assignments(
        self,
        role_id: str,
        include_expired: bool = False
    ) -> List[BusinessRoleAssignment]:
        """Get all assignments for a role"""
        assignments = [
            a for a in self.assignments.values()
            if a.business_role_id == role_id
        ]

        if not include_expired:
            now = datetime.now()
            assignments = [
                a for a in assignments
                if a.status == "active" and
                (a.valid_to is None or a.valid_to > now)
            ]

        return assignments

    def certify_assignment(
        self,
        assignment_id: str,
        certified_by: str
    ) -> BusinessRoleAssignment:
        """Certify a role assignment"""
        if assignment_id not in self.assignments:
            raise ValueError(f"Assignment {assignment_id} not found")

        assignment = self.assignments[assignment_id]
        assignment.last_certified = datetime.now()
        assignment.certified_by = certified_by

        return assignment

    # =========================================================================
    # Request Template Management
    # =========================================================================

    def configure_request_template(
        self,
        role_id: str,
        required_justification: bool = True,
        justification_options: List[str] = None,
        required_fields: List[str] = None,
        optional_fields: List[str] = None,
        default_duration_days: int = None,
        max_duration_days: int = None,
        auto_approve_conditions: List[Dict] = None
    ) -> BusinessRole:
        """Configure the request template for a business role"""
        if role_id not in self.business_roles:
            raise ValueError(f"Business role {role_id} not found")

        role = self.business_roles[role_id]

        if not role.request_template:
            role.request_template = RequestTemplate(business_role_id=role_id)

        template = role.request_template
        template.required_justification = required_justification
        if justification_options:
            template.justification_options = justification_options
        if required_fields:
            template.required_fields = required_fields
        if optional_fields:
            template.optional_fields = optional_fields
        if default_duration_days:
            template.default_duration_days = default_duration_days
        if max_duration_days:
            template.max_duration_days = max_duration_days
        if auto_approve_conditions:
            template.auto_approve_conditions = auto_approve_conditions

        return role

    # =========================================================================
    # Statistics & Analytics
    # =========================================================================

    def get_statistics(self) -> Dict:
        """Get business role statistics"""
        roles = list(self.business_roles.values())

        by_status = {}
        for status in BusinessRoleStatus:
            by_status[status.value] = len([r for r in roles if r.status == status])

        by_category = {}
        for cat in self.STANDARD_CATEGORIES:
            by_category[cat["id"]] = len([
                r for r in roles
                if r.catalog_entry and r.catalog_entry.category == cat["id"]
            ])

        by_risk = {}
        for risk in ["low", "medium", "high", "critical"]:
            by_risk[risk] = len([r for r in roles if r.risk_level == risk])

        return {
            "total_business_roles": len(roles),
            "by_status": by_status,
            "by_category": by_category,
            "by_risk_level": by_risk,
            "total_assignments": len(self.assignments),
            "active_assignments": len([a for a in self.assignments.values() if a.status == "active"]),
            "roles_needing_review": len(self.get_roles_needing_review()),
            "sensitive_roles": len([r for r in roles if r.is_sensitive])
        }

    def get_popular_roles(self, limit: int = 10) -> List[Dict]:
        """Get most popular business roles"""
        roles = [r for r in self.business_roles.values() if r.catalog_entry]
        roles.sort(key=lambda r: r.catalog_entry.popularity_score, reverse=True)

        return [
            {
                "role_id": r.role_id,
                "name": r.name,
                "popularity_score": r.catalog_entry.popularity_score,
                "request_count": r.catalog_entry.request_count,
                "current_assignments": r.current_assignments
            }
            for r in roles[:limit]
        ]
