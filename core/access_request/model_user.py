"""
Model User / Template Request Engine

Enables "give me the same access as Sarah" workflows by comparing two users'
roles and generating a filtered, risk-aware access request. Also supports
reusable access templates (New Finance Employee, New IT Admin, etc.).

Data is persisted in the database via the ModelTemplate, User, and Role models.
On first access the engine seeds reference data if the tables are empty.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from core.logging import get_logger
from db.database import db_manager
from db.models.operations import ModelTemplate
from db.models.user import User as DBUser, Role as DBRole, UserRole as DBUserRole

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RoleRecommendation(str, Enum):
    COPY = "COPY"          # Safe to copy as-is
    SKIP = "SKIP"          # Should not be copied (temp / unused / dept-specific)
    REVIEW = "REVIEW"      # Potentially valid but flagged for manual review (high-risk)


class RoleRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Data classes (DTOs)
# ---------------------------------------------------------------------------

@dataclass
class UserRole:
    """A single role assignment on a user."""
    role_id: str
    role_name: str
    system: str
    assigned_date: datetime
    expiry_date: Optional[datetime] = None
    last_used: Optional[datetime] = None
    department: Optional[str] = None
    risk_level: RoleRiskLevel = RoleRiskLevel.LOW
    is_sensitive: bool = False
    description: str = ""

    def is_temporary(self) -> bool:
        return self.expiry_date is not None

    def is_unused(self, days: int = 90) -> bool:
        if self.last_used is None:
            # Never used -- treat as unused if assigned >90 days ago
            return (datetime.utcnow() - self.assigned_date).days > days
        return (datetime.utcnow() - self.last_used).days > days

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "system": self.system,
            "assigned_date": self.assigned_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "department": self.department,
            "risk_level": self.risk_level.value,
            "is_sensitive": self.is_sensitive,
            "description": self.description,
        }


@dataclass
class UserProfile:
    """Lightweight profile of a user for comparison purposes."""
    user_id: str
    display_name: str
    email: str
    department: str
    job_title: str
    manager_id: Optional[str] = None
    roles: List[UserRole] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "email": self.email,
            "department": self.department,
            "job_title": self.job_title,
            "manager_id": self.manager_id,
            "role_count": len(self.roles),
        }


@dataclass
class RoleComparisonEntry:
    """Comparison result for one role between source and target users."""
    role_id: str
    role_name: str
    system: str
    in_source: bool
    in_target: bool
    recommendation: RoleRecommendation
    skip_reason: Optional[str] = None
    risk_level: RoleRiskLevel = RoleRiskLevel.LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "system": self.system,
            "in_source": self.in_source,
            "in_target": self.in_target,
            "recommendation": self.recommendation.value,
            "skip_reason": self.skip_reason,
            "risk_level": self.risk_level.value,
        }


@dataclass
class SmartRequestItem:
    """One role in a generated smart request."""
    role_id: str
    role_name: str
    system: str
    recommendation: RoleRecommendation
    justification: str
    risk_level: RoleRiskLevel
    skip_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "system": self.system,
            "recommendation": self.recommendation.value,
            "justification": self.justification,
            "risk_level": self.risk_level.value,
            "skip_reason": self.skip_reason,
        }


@dataclass
class AccessTemplate:
    """A reusable access template."""
    template_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    role_ids: List[str] = field(default_factory=list)
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "role_ids": self.role_ids,
            "role_count": len(self.role_ids),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "active": self.active,
        }


# ---------------------------------------------------------------------------
# Seed data definitions (used by _ensure_seeded)
# ---------------------------------------------------------------------------

_now = datetime.utcnow()

_SEED_ROLES_DATA: List[Dict[str, Any]] = [
    dict(role_id="R_FI_AP_CLERK", role_name="Accounts Payable Clerk", system="SAP ECC",
         assigned_days_ago=400, last_used_days_ago=2, department="Finance",
         risk_level="medium", is_sensitive=False,
         description="Post vendor invoices and process payments"),
    dict(role_id="R_FI_GL_POSTING", role_name="GL Account Posting", system="SAP ECC",
         assigned_days_ago=400, last_used_days_ago=5, department="Finance",
         risk_level="medium", is_sensitive=False,
         description="Post to General Ledger accounts"),
    dict(role_id="R_FI_BANK_ADMIN", role_name="Bank Account Administrator", system="SAP ECC",
         assigned_days_ago=200, last_used_days_ago=1, department="Finance",
         risk_level="critical", is_sensitive=True,
         description="Create and modify bank master data"),
    dict(role_id="R_FI_REPORT_VIEWER", role_name="Financial Report Viewer", system="SAP ECC",
         assigned_days_ago=500, last_used_days_ago=3, department="Finance",
         risk_level="low", is_sensitive=False,
         description="View-only access to financial reports"),
    dict(role_id="R_IT_BASIS_ADMIN", role_name="BASIS Administrator", system="SAP ECC",
         assigned_days_ago=730, last_used_days_ago=1, department="IT",
         risk_level="critical", is_sensitive=True,
         description="Full system administration access"),
    dict(role_id="R_IT_USER_ADMIN", role_name="User Administration", system="SAP ECC",
         assigned_days_ago=600, last_used_days_ago=7, department="IT",
         risk_level="high", is_sensitive=True,
         description="Create and manage user accounts"),
    dict(role_id="R_IT_TRANSPORT", role_name="Transport Management", system="SAP ECC",
         assigned_days_ago=600, last_used_days_ago=30, department="IT",
         risk_level="high", is_sensitive=False,
         description="Manage system transports"),
    dict(role_id="R_SD_ORDER_ENTRY", role_name="Sales Order Entry", system="SAP ECC",
         assigned_days_ago=300, last_used_days_ago=4, department="Sales",
         risk_level="low", is_sensitive=False,
         description="Create and modify sales orders"),
    dict(role_id="R_SD_PRICING", role_name="Sales Pricing Manager", system="SAP ECC",
         assigned_days_ago=300, last_used_days_ago=6, department="Sales",
         risk_level="medium", is_sensitive=False,
         description="Manage pricing conditions and discounts"),
    dict(role_id="R_HR_PAYROLL", role_name="Payroll Processor", system="SAP ECC",
         assigned_days_ago=180, last_used_days_ago=14, department="HR",
         risk_level="high", is_sensitive=True,
         description="Process payroll runs"),
    dict(role_id="R_HR_VIEWER", role_name="HR Data Viewer", system="SAP ECC",
         assigned_days_ago=200, last_used_days_ago=10, department="HR",
         risk_level="low", is_sensitive=False,
         description="Read-only access to HR data"),
    dict(role_id="R_TEMP_PROJECT", role_name="Project Alpha Temporary Access", system="SAP ECC",
         assigned_days_ago=60, last_used_days_ago=5, department="Finance",
         risk_level="medium", is_sensitive=False,
         description="Temporary access for Project Alpha",
         expiry_days_future=30),
    dict(role_id="R_UNUSED_OLD", role_name="Legacy Report Access", system="SAP ECC",
         assigned_days_ago=500, last_used_days_ago=200, department="Finance",
         risk_level="low", is_sensitive=False,
         description="Access to decommissioned legacy reports"),
    dict(role_id="R_AZ_READER", role_name="Azure AD Reader", system="Azure AD",
         assigned_days_ago=400, last_used_days_ago=3, department="IT",
         risk_level="low", is_sensitive=False,
         description="Read Azure AD directory data"),
]

_SEED_USERS_DATA: List[Dict[str, Any]] = [
    dict(user_id="U001", display_name="Sarah Mitchell",
         email="sarah.mitchell@company.com", department="Finance",
         job_title="Senior Accounts Payable Manager", manager_id="U010",
         role_ids=["R_FI_AP_CLERK", "R_FI_GL_POSTING", "R_FI_BANK_ADMIN",
                   "R_FI_REPORT_VIEWER", "R_TEMP_PROJECT", "R_UNUSED_OLD"]),
    dict(user_id="U002", display_name="James Okonkwo",
         email="james.okonkwo@company.com", department="Finance",
         job_title="Accounts Payable Analyst", manager_id="U001",
         role_ids=["R_FI_AP_CLERK", "R_FI_REPORT_VIEWER"]),
    dict(user_id="U003", display_name="Priya Sharma",
         email="priya.sharma@company.com", department="IT",
         job_title="SAP BASIS Engineer", manager_id="U010",
         role_ids=["R_IT_BASIS_ADMIN", "R_IT_USER_ADMIN", "R_IT_TRANSPORT", "R_AZ_READER"]),
    dict(user_id="U004", display_name="Carlos Rivera",
         email="carlos.rivera@company.com", department="Sales",
         job_title="Sales Representative", manager_id="U010",
         role_ids=["R_SD_ORDER_ENTRY", "R_SD_PRICING"]),
    dict(user_id="U005", display_name="New Employee",
         email="new.employee@company.com", department="Finance",
         job_title="Accounts Payable Analyst", manager_id="U001",
         role_ids=[]),
]

_SEED_TEMPLATES_DATA: List[Dict[str, Any]] = [
    dict(template_id="TPL-001", name="New Finance Employee",
         description="Standard access bundle for new Finance department employees. "
                     "Includes AP processing, GL viewing, and reporting.",
         department="Finance", position="Finance Employee",
         roles=["R_FI_AP_CLERK", "R_FI_REPORT_VIEWER"],
         created_by="admin", tags=["finance", "onboarding"]),
    dict(template_id="TPL-002", name="New IT Administrator",
         description="Access package for new IT/BASIS administrators. "
                     "Requires additional approval due to sensitive roles.",
         department="IT", position="IT Administrator",
         roles=["R_IT_USER_ADMIN", "R_IT_TRANSPORT", "R_AZ_READER"],
         created_by="admin", tags=["it", "admin", "onboarding"]),
    dict(template_id="TPL-003", name="New Sales Representative",
         description="Standard sales access for new Sales team members.",
         department="Sales", position="Sales Representative",
         roles=["R_SD_ORDER_ENTRY", "R_SD_PRICING"],
         created_by="admin", tags=["sales", "onboarding"]),
    dict(template_id="TPL-004", name="HR Read-Only Package",
         description="Read-only HR access for managers who need to view employee data.",
         department="HR", position="HR Viewer",
         roles=["R_HR_VIEWER"],
         created_by="admin", tags=["hr", "read-only"]),
    dict(template_id="TPL-005", name="Finance Report Viewer",
         description="Minimal finance access for stakeholders who need reporting only.",
         department="Finance", position="Report Viewer",
         roles=["R_FI_REPORT_VIEWER"],
         created_by="admin", tags=["finance", "reporting"]),
]


# ---------------------------------------------------------------------------
# In-memory caches (loaded from DB on first access)
# ---------------------------------------------------------------------------

_roles_cache: Optional[Dict[str, UserRole]] = None
_users_cache: Optional[Dict[str, UserProfile]] = None
_seeded: bool = False


def _build_user_role(rd: Dict[str, Any]) -> UserRole:
    """Build a UserRole DTO from a seed-data dictionary."""
    now = datetime.utcnow()
    expiry = None
    if rd.get("expiry_days_future"):
        expiry = now + timedelta(days=rd["expiry_days_future"])
    return UserRole(
        role_id=rd["role_id"],
        role_name=rd["role_name"],
        system=rd["system"],
        assigned_date=now - timedelta(days=rd["assigned_days_ago"]),
        expiry_date=expiry,
        last_used=now - timedelta(days=rd["last_used_days_ago"]),
        department=rd.get("department"),
        risk_level=RoleRiskLevel(rd["risk_level"]),
        is_sensitive=rd.get("is_sensitive", False),
        description=rd.get("description", ""),
    )


def _ensure_seeded() -> None:
    """
    Lazy-seed: check if model_templates table has data; if empty, insert all
    seed records into DB tables.  Then load roles/users into in-memory caches
    for fast comparison logic.
    """
    global _roles_cache, _users_cache, _seeded

    if _seeded:
        return

    # Ensure DB is initialised
    if not db_manager._initialized:
        db_manager.init()
        db_manager.create_tables()

    now = datetime.utcnow()

    with db_manager.session_scope() as session:
        template_count = session.query(ModelTemplate).count()

        if template_count == 0:
            logger.info("model_user.seeding", msg="Seeding model-user reference data into DB")

            # --- Seed DB roles (into the roles table) ---
            db_role_map: Dict[str, int] = {}  # role_id -> DB primary key
            for rd in _SEED_ROLES_DATA:
                existing = session.query(DBRole).filter_by(role_id=rd["role_id"]).first()
                if existing:
                    db_role_map[rd["role_id"]] = existing.id
                    continue
                db_role = DBRole(
                    role_id=rd["role_id"],
                    role_name=rd["role_name"],
                    description=rd.get("description", ""),
                    source_system=rd["system"],
                    risk_level=rd["risk_level"],
                    is_sensitive=rd.get("is_sensitive", False),
                    is_active=True,
                )
                session.add(db_role)
                session.flush()
                db_role_map[rd["role_id"]] = db_role.id

            # --- Seed DB users (into the users table) ---
            for ud in _SEED_USERS_DATA:
                existing = session.query(DBUser).filter_by(user_id=ud["user_id"]).first()
                if existing:
                    continue
                db_user = DBUser(
                    user_id=ud["user_id"],
                    username=ud["user_id"].lower(),
                    full_name=ud["display_name"],
                    email=ud["email"],
                    department=ud["department"],
                    title=ud["job_title"],
                    manager_user_id=ud.get("manager_id"),
                    status="active",
                    user_type="dialog",
                )
                session.add(db_user)
                session.flush()

                # Create user-role assignments
                for rid in ud["role_ids"]:
                    db_pk = db_role_map.get(rid)
                    if db_pk is None:
                        continue
                    assignment = DBUserRole(
                        user_id=db_user.id,
                        role_id=db_pk,
                        assigned_at=now,
                        is_active=True,
                    )
                    session.add(assignment)

            # --- Seed model templates ---
            for td in _SEED_TEMPLATES_DATA:
                tmpl = ModelTemplate(
                    template_id=td["template_id"],
                    name=td["name"],
                    description=td["description"],
                    department=td["department"],
                    position=td["position"],
                    roles=td["roles"],
                    systems=list({
                        r["system"]
                        for r in _SEED_ROLES_DATA
                        if r["role_id"] in td["roles"]
                    }),
                    compliance_rate=100.0,
                    usage_count=0,
                    is_active=True,
                    created_by=td["created_by"],
                )
                session.add(tmpl)

            logger.info("model_user.seed_complete", msg="Reference data seeded successfully")

    # --- Load caches from seed definitions for fast comparison logic ---
    _roles_cache = {}
    for rd in _SEED_ROLES_DATA:
        _roles_cache[rd["role_id"]] = _build_user_role(rd)

    _users_cache = {}
    for ud in _SEED_USERS_DATA:
        roles = [_roles_cache[rid] for rid in ud["role_ids"] if rid in _roles_cache]
        _users_cache[ud["user_id"]] = UserProfile(
            user_id=ud["user_id"],
            display_name=ud["display_name"],
            email=ud["email"],
            department=ud["department"],
            job_title=ud["job_title"],
            manager_id=ud.get("manager_id"),
            roles=roles,
        )

    _seeded = True


def _get_roles_cache() -> Dict[str, UserRole]:
    _ensure_seeded()
    assert _roles_cache is not None
    return _roles_cache


def _get_users_cache() -> Dict[str, UserProfile]:
    _ensure_seeded()
    assert _users_cache is not None
    return _users_cache


# ---------------------------------------------------------------------------
# Helper: convert ModelTemplate DB row -> AccessTemplate DTO
# ---------------------------------------------------------------------------

def _db_template_to_dto(row: ModelTemplate) -> AccessTemplate:
    """Convert a ModelTemplate ORM instance to an AccessTemplate dataclass."""
    return AccessTemplate(
        template_id=row.template_id,
        name=row.name,
        description=row.description or "",
        role_ids=row.roles or [],
        created_by=row.created_by or "system",
        created_at=row.created_at or datetime.utcnow(),
        updated_at=row.updated_at or datetime.utcnow(),
        tags=[],  # tags are derived from department/position in DB model
        active=row.is_active,
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ModelUserEngine:
    """
    Core engine for model-user comparisons and access template management.
    """

    # ------------------------------------------------------------------
    # User access queries
    # ------------------------------------------------------------------

    def get_model_user_access(self, user_id: str) -> Dict[str, Any]:
        """
        Return the full role list for a reference (model) user.

        Args:
            user_id: The ID of the model user.

        Returns:
            Dict with user profile and list of role dicts.

        Raises:
            ValueError: If the user is not found.
        """
        user = self._get_user(user_id)
        return {
            "user": user.to_dict(),
            "roles": [r.to_dict() for r in user.roles],
            "total_roles": len(user.roles),
            "high_risk_roles": [
                r.to_dict() for r in user.roles
                if r.risk_level in (RoleRiskLevel.HIGH, RoleRiskLevel.CRITICAL)
            ],
            "sensitive_roles": [r.to_dict() for r in user.roles if r.is_sensitive],
        }

    def compare_users(
        self,
        source_user_id: str,
        target_user_id: str,
    ) -> Dict[str, Any]:
        """
        Compare role assignments between source (model) and target users.

        Returns a list of RoleComparisonEntry objects describing which roles
        the source has, the target has, both, or neither.

        Args:
            source_user_id: The model user (e.g. Sarah).
            target_user_id: The user being provisioned.
        """
        _ensure_seeded()
        roles_cache = _get_roles_cache()

        source = self._get_user(source_user_id)
        target = self._get_user(target_user_id)

        source_ids = {r.role_id for r in source.roles}
        target_ids = {r.role_id for r in target.roles}
        all_ids = source_ids | target_ids

        entries: List[RoleComparisonEntry] = []
        for role_id in sorted(all_ids):
            role = roles_cache.get(role_id)
            if not role:
                continue
            in_source = role_id in source_ids
            in_target = role_id in target_ids
            entries.append(
                RoleComparisonEntry(
                    role_id=role_id,
                    role_name=role.role_name,
                    system=role.system,
                    in_source=in_source,
                    in_target=in_target,
                    recommendation=RoleRecommendation.COPY if in_source and not in_target
                    else RoleRecommendation.SKIP,
                    risk_level=role.risk_level,
                )
            )

        same_dept = source.department == target.department

        return {
            "source_user": source.to_dict(),
            "target_user": target.to_dict(),
            "same_department": same_dept,
            "comparison": [e.to_dict() for e in entries],
            "source_only": [e.to_dict() for e in entries if e.in_source and not e.in_target],
            "target_only": [e.to_dict() for e in entries if not e.in_source and e.in_target],
            "shared": [e.to_dict() for e in entries if e.in_source and e.in_target],
        }

    # ------------------------------------------------------------------
    # Smart request generation
    # ------------------------------------------------------------------

    def generate_smart_request(
        self,
        source_user_id: str,
        target_user_id: str,
        unused_days_threshold: int = 90,
    ) -> Dict[str, Any]:
        """
        Generate a filtered, risk-aware access request based on a model user.

        Filtering logic (in order):
        1. Only roles the source has and the target does NOT yet have.
        2. Temporary roles (with expiry_date) are SKIPPED.
        3. Unused roles (last_used > unused_days_threshold or never used) are SKIPPED.
        4. Department-specific roles are SKIPPED if departments differ.
        5. High-risk / critical / sensitive roles are flagged REVIEW.
        6. Remaining roles receive COPY.

        Args:
            source_user_id: Model user to copy from.
            target_user_id: User to provision.
            unused_days_threshold: Days of inactivity that classify a role as unused.

        Returns:
            Dict with recommended items, skipped items, and request metadata.
        """
        _ensure_seeded()

        source = self._get_user(source_user_id)
        target = self._get_user(target_user_id)

        target_role_ids = {r.role_id for r in target.roles}
        same_dept = source.department == target.department

        copy_items: List[SmartRequestItem] = []
        review_items: List[SmartRequestItem] = []
        skip_items: List[SmartRequestItem] = []

        for role in source.roles:
            # Already has this role
            if role.role_id in target_role_ids:
                continue

            skip_reason: Optional[str] = None

            if role.is_temporary():
                skip_reason = (
                    f"Temporary role (expires {role.expiry_date.date() if role.expiry_date else 'N/A'})"
                )
            elif role.is_unused(unused_days_threshold):
                days_since = (
                    (datetime.utcnow() - role.last_used).days
                    if role.last_used
                    else (datetime.utcnow() - role.assigned_date).days
                )
                skip_reason = f"Unused for {days_since} days (threshold: {unused_days_threshold})"
            elif not same_dept and role.department and role.department == source.department:
                skip_reason = (
                    f"Department-specific role for '{source.department}'; "
                    f"target is in '{target.department}'"
                )

            if skip_reason:
                skip_items.append(
                    SmartRequestItem(
                        role_id=role.role_id,
                        role_name=role.role_name,
                        system=role.system,
                        recommendation=RoleRecommendation.SKIP,
                        justification=skip_reason,
                        risk_level=role.risk_level,
                        skip_reason=skip_reason,
                    )
                )
                continue

            if role.risk_level in (RoleRiskLevel.HIGH, RoleRiskLevel.CRITICAL) or role.is_sensitive:
                review_items.append(
                    SmartRequestItem(
                        role_id=role.role_id,
                        role_name=role.role_name,
                        system=role.system,
                        recommendation=RoleRecommendation.REVIEW,
                        justification=(
                            f"High-risk role ({role.risk_level.value})"
                            + (" -- sensitive access" if role.is_sensitive else "")
                            + ". Manual review required before granting."
                        ),
                        risk_level=role.risk_level,
                    )
                )
            else:
                copy_items.append(
                    SmartRequestItem(
                        role_id=role.role_id,
                        role_name=role.role_name,
                        system=role.system,
                        recommendation=RoleRecommendation.COPY,
                        justification=(
                            f"Model user {source.display_name} holds this role; "
                            "low risk, same department."
                        ),
                        risk_level=role.risk_level,
                    )
                )

        all_items = copy_items + review_items + skip_items
        logger.info(
            "model_user.smart_request_generated",
            source=source_user_id,
            target=target_user_id,
            copy=len(copy_items),
            review=len(review_items),
            skip=len(skip_items),
        )

        return {
            "request_id": str(uuid.uuid4()),
            "source_user": source.to_dict(),
            "target_user": target.to_dict(),
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_source_roles": len(source.roles),
                "already_assigned": len(target_role_ids & {r.role_id for r in source.roles}),
                "to_copy": len(copy_items),
                "for_review": len(review_items),
                "skipped": len(skip_items),
            },
            "items": [i.to_dict() for i in all_items],
            "copy_items": [i.to_dict() for i in copy_items],
            "review_items": [i.to_dict() for i in review_items],
            "skip_items": [i.to_dict() for i in skip_items],
        }

    # ------------------------------------------------------------------
    # Template management (DB-backed via ModelTemplate)
    # ------------------------------------------------------------------

    def create_template(
        self,
        name: str,
        role_ids: List[str],
        description: str = "",
        created_by: str = "api",
        tags: Optional[List[str]] = None,
    ) -> AccessTemplate:
        """
        Create and persist a new access template.

        Args:
            name: Human-readable template name.
            role_ids: List of role IDs to include.
            description: Optional description.
            created_by: User or system that created this template.
            tags: Optional categorisation tags.
        """
        _ensure_seeded()
        roles_cache = _get_roles_cache()

        # Validate role IDs against known roles
        unknown = [rid for rid in role_ids if rid not in roles_cache]
        if unknown:
            logger.warning("template.unknown_roles", unknown=unknown)

        template_id = f"TPL-{uuid.uuid4().hex[:8].upper()}"

        # Derive department/position from tags or default
        department = (tags[0].title() if tags else "General")
        position = name

        # Resolve systems from role definitions
        systems = list({
            roles_cache[rid].system
            for rid in role_ids
            if rid in roles_cache
        }) or ["SAP ECC"]

        with db_manager.session_scope() as session:
            db_tmpl = ModelTemplate(
                template_id=template_id,
                name=name,
                description=description,
                department=department,
                position=position,
                roles=role_ids,
                systems=systems,
                compliance_rate=100.0,
                usage_count=0,
                is_active=True,
                created_by=created_by,
            )
            session.add(db_tmpl)
            session.flush()

            template = _db_template_to_dto(db_tmpl)
            template.tags = tags or []

        logger.info("template.created", template_id=template_id, name=name)
        return template

    def list_templates(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Return all access templates, optionally filtering to active ones only.
        Each entry includes the resolved role details.
        """
        _ensure_seeded()
        roles_cache = _get_roles_cache()

        with db_manager.session_scope() as session:
            query = session.query(ModelTemplate)
            if active_only:
                query = query.filter(ModelTemplate.is_active == True)
            rows = query.all()

            result = []
            for row in rows:
                dto = _db_template_to_dto(row)
                entry = dto.to_dict()
                entry["roles"] = [
                    roles_cache[rid].to_dict()
                    for rid in (row.roles or [])
                    if rid in roles_cache
                ]
                result.append(entry)

        return result

    def get_template(self, template_id: str) -> AccessTemplate:
        """Return a single template by ID."""
        _ensure_seeded()

        with db_manager.session_scope() as session:
            row = session.query(ModelTemplate).filter_by(template_id=template_id).first()
            if not row:
                raise ValueError(f"Template '{template_id}' not found")
            return _db_template_to_dto(row)

    def delete_template(self, template_id: str, deleted_by: str = "api") -> None:
        """Soft-delete a template by marking it inactive."""
        _ensure_seeded()

        with db_manager.session_scope() as session:
            row = session.query(ModelTemplate).filter_by(template_id=template_id).first()
            if not row:
                raise ValueError(f"Template '{template_id}' not found")
            row.is_active = False
            row.updated_at = datetime.utcnow()

        logger.info("template.deleted", template_id=template_id, deleted_by=deleted_by)

    def apply_template(
        self,
        template_id: str,
        target_user_id: str,
        requested_by: str = "api",
    ) -> Dict[str, Any]:
        """
        Apply a template to a user by generating a pre-populated access request.

        Roles the user already holds are excluded from the request.
        High-risk roles are flagged for review.

        Args:
            template_id: The template to apply.
            target_user_id: The user to provision.
            requested_by: Who is initiating the request.
        """
        _ensure_seeded()
        roles_cache = _get_roles_cache()

        tmpl = self.get_template(template_id)
        target = self._get_user(target_user_id)
        target_role_ids = {r.role_id for r in target.roles}

        items: List[SmartRequestItem] = []
        for role_id in tmpl.role_ids:
            if role_id in target_role_ids:
                continue
            role = roles_cache.get(role_id)
            if not role:
                continue
            if role.risk_level in (RoleRiskLevel.HIGH, RoleRiskLevel.CRITICAL) or role.is_sensitive:
                rec = RoleRecommendation.REVIEW
                justification = f"High-risk role from template '{tmpl.name}'. Manual approval required."
            else:
                rec = RoleRecommendation.COPY
                justification = f"Standard role from template '{tmpl.name}'."
            items.append(
                SmartRequestItem(
                    role_id=role_id,
                    role_name=role.role_name,
                    system=role.system,
                    recommendation=rec,
                    justification=justification,
                    risk_level=role.risk_level,
                )
            )

        # Increment usage count in DB
        with db_manager.session_scope() as session:
            row = session.query(ModelTemplate).filter_by(template_id=template_id).first()
            if row:
                row.usage_count = (row.usage_count or 0) + 1

        logger.info(
            "template.applied",
            template_id=template_id,
            target_user_id=target_user_id,
            items=len(items),
        )
        return {
            "request_id": str(uuid.uuid4()),
            "template": tmpl.to_dict(),
            "target_user": target.to_dict(),
            "applied_by": requested_by,
            "applied_at": datetime.utcnow().isoformat(),
            "items": [i.to_dict() for i in items],
            "already_assigned": list(target_role_ids & set(tmpl.role_ids)),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_user(user_id: str) -> UserProfile:
        users_cache = _get_users_cache()
        user = users_cache.get(user_id)
        if not user:
            raise ValueError(f"User '{user_id}' not found")
        return user


# Module-level singleton
_engine: Optional[ModelUserEngine] = None


def get_model_user_engine() -> ModelUserEngine:
    """Return the module-level ModelUserEngine singleton."""
    global _engine
    if _engine is None:
        _engine = ModelUserEngine()
    return _engine
