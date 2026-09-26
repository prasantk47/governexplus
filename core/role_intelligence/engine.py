"""
Role Intelligence Engine

Analyzes the SAP role estate for duplication, sprawl, health issues, and
consolidation opportunities. Designed to tackle the root causes of role
explosion in enterprise SAP environments.

Capabilities:
- Role similarity analysis (shared transactions, auth objects, org values)
- Duplicate and near-duplicate detection
- Usage analytics (unused roles, stale assignments)
- Consolidation planning with effort/risk scoring
- Role health scoring (owner, description, SoD, naming, usage)
- Naming convention enforcement and suggestion

Data source:
- Primary: ``role_intelligence`` DB table (RoleIntelligenceRecord)
- Seed: if the table is empty for the active tenant the 44 hardcoded roles are
  inserted automatically and cached for the lifetime of the process.
- The in-memory cache (``self._catalogue`` / ``self._index``) is rebuilt from
  the DB on first use via ``_ensure_loaded()``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from db.database import db_manager
from db.models.intelligence import RoleIntelligenceRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RoleType(Enum):
    SINGLE = "single"
    COMPOSITE = "composite"
    DERIVED = "derived"


class HealthDimension(Enum):
    OWNER = "owner"
    DESCRIPTION = "description"
    SOD_CONFLICTS = "sod_conflicts"
    USER_COUNT = "user_count"
    RECENT_USAGE = "recent_usage"
    NAMING = "naming"


class ConsolidationRisk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Data-transfer objects
# ---------------------------------------------------------------------------

@dataclass
class SimilarityResult:
    role_a: str
    role_b: str
    overall_score: float          # 0.0 – 1.0
    transaction_score: float
    auth_object_score: float
    org_value_score: float
    shared_transactions: List[str]
    shared_auth_objects: List[str]
    unique_to_a: List[str]
    unique_to_b: List[str]
    recommendation: str

    def to_dict(self) -> Dict:
        return {
            "role_a": self.role_a,
            "role_b": self.role_b,
            "overall_score": round(self.overall_score * 100, 1),
            "transaction_score": round(self.transaction_score * 100, 1),
            "auth_object_score": round(self.auth_object_score * 100, 1),
            "org_value_score": round(self.org_value_score * 100, 1),
            "shared_transactions": self.shared_transactions,
            "shared_auth_objects": self.shared_auth_objects,
            "unique_to_a": self.unique_to_a,
            "unique_to_b": self.unique_to_b,
            "recommendation": self.recommendation,
        }


@dataclass
class DuplicateGroup:
    group_id: str
    roles: List[str]
    similarity_score: float       # highest pairwise score in the group
    shared_transactions: List[str]
    shared_auth_objects: List[str]
    recommended_canonical: str    # which role to keep
    retirement_candidates: List[str]
    reason: str

    def to_dict(self) -> Dict:
        return {
            "group_id": self.group_id,
            "roles": self.roles,
            "similarity_score": round(self.similarity_score * 100, 1),
            "shared_transactions": self.shared_transactions,
            "shared_auth_objects": self.shared_auth_objects,
            "recommended_canonical": self.recommended_canonical,
            "retirement_candidates": self.retirement_candidates,
            "reason": self.reason,
        }


@dataclass
class RoleUsageStat:
    role_id: str
    role_name: str
    user_count: int
    last_used: Optional[datetime]
    days_since_used: Optional[int]
    is_unused: bool
    usage_trend: str              # "growing", "stable", "declining", "dead"

    def to_dict(self) -> Dict:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "user_count": self.user_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "days_since_used": self.days_since_used,
            "is_unused": self.is_unused,
            "usage_trend": self.usage_trend,
        }


@dataclass
class UsageReport:
    total_roles: int
    unused_roles: List[RoleUsageStat]
    stale_roles: List[RoleUsageStat]        # used > 90 days ago
    low_usage_roles: List[RoleUsageStat]    # 1-2 users
    active_roles: List[RoleUsageStat]
    retirement_candidates: List[str]
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "total_roles": self.total_roles,
            "unused_count": len(self.unused_roles),
            "stale_count": len(self.stale_roles),
            "low_usage_count": len(self.low_usage_roles),
            "active_count": len(self.active_roles),
            "unused_roles": [r.to_dict() for r in self.unused_roles],
            "stale_roles": [r.to_dict() for r in self.stale_roles],
            "low_usage_roles": [r.to_dict() for r in self.low_usage_roles],
            "retirement_candidates": self.retirement_candidates,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class ConsolidationGroup:
    group_id: str
    roles: List[str]
    proposed_name: str
    similarity_score: float
    user_count_total: int
    effort_days: int
    risk: ConsolidationRisk
    risk_reason: str
    steps: List[str]
    estimated_roles_saved: int

    def to_dict(self) -> Dict:
        return {
            "group_id": self.group_id,
            "roles": self.roles,
            "proposed_name": self.proposed_name,
            "similarity_score": round(self.similarity_score * 100, 1),
            "user_count_total": self.user_count_total,
            "effort_days": self.effort_days,
            "risk": self.risk.value,
            "risk_reason": self.risk_reason,
            "steps": self.steps,
            "estimated_roles_saved": self.estimated_roles_saved,
        }


@dataclass
class ConsolidationPlan:
    total_roles_analysed: int
    consolidation_groups: List[ConsolidationGroup]
    total_roles_saveable: int
    total_effort_days: int
    high_priority_groups: List[str]
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "total_roles_analysed": self.total_roles_analysed,
            "consolidation_groups": [g.to_dict() for g in self.consolidation_groups],
            "total_roles_saveable": self.total_roles_saveable,
            "total_effort_days": self.total_effort_days,
            "high_priority_groups": self.high_priority_groups,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class RoleHealthScore:
    role_id: str
    role_name: str
    overall_score: int            # 0-100
    dimension_scores: Dict[str, int]   # dimension -> 0-100
    issues: List[str]
    recommendations: List[str]
    grade: str                    # A / B / C / D / F

    def to_dict(self) -> Dict:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "overall_score": self.overall_score,
            "grade": self.grade,
            "dimension_scores": self.dimension_scores,
            "issues": self.issues,
            "recommendations": self.recommendations,
        }


@dataclass
class NamingIssue:
    role_id: str
    role_name: str
    issue_type: str
    description: str
    suggested_name: str

    def to_dict(self) -> Dict:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "issue_type": self.issue_type,
            "description": self.description,
            "suggested_name": self.suggested_name,
        }


@dataclass
class NamingReport:
    total_roles: int
    compliant_count: int
    non_compliant_count: int
    issues: List[NamingIssue]
    convention_summary: Dict[str, Any]

    def to_dict(self) -> Dict:
        return {
            "total_roles": self.total_roles,
            "compliant_count": self.compliant_count,
            "non_compliant_count": self.non_compliant_count,
            "compliance_rate": round(self.compliant_count / self.total_roles * 100, 1) if self.total_roles else 0,
            "issues": [i.to_dict() for i in self.issues],
            "convention_summary": self.convention_summary,
        }


# ---------------------------------------------------------------------------
# Hardcoded seed data — 44 realistic SAP roles with deliberate problems
#
# These are inserted into the DB on first use when the table is empty for the
# active tenant. After seeding, all reads go through the DB.
# ---------------------------------------------------------------------------

_NOW = datetime.now()


def _days_ago(n: int) -> datetime:
    return _NOW - timedelta(days=n)


# Each entry:
#   id (logical), name, type, owner, description, user_count, last_used,
#   transactions, auth_objects, org_values, has_sod_conflict, business_process
_SEED_CATALOGUE: List[Dict[str, Any]] = [

    # ── Finance (FI) ──────────────────────────────────────────────────────
    {
        "id": "R001", "name": "Z_FI_AP_PROCESSOR", "type": "single",
        "owner": "Maria.Gonzalez", "description": "Accounts Payable processor — invoice entry and posting",
        "user_count": 14, "last_used": _days_ago(1),
        "transactions": ["FB60", "FB65", "F110", "FBL1N", "MIR7"],
        "auth_objects": ["F_BKPF_BUK", "F_BKPF_KOA", "F_LFA1_BUK"],
        "org_values": {"BUKRS": ["1000", "2000"]},
        "has_sod_conflict": False, "business_process": "FI",
    },
    {
        "id": "R002", "name": "Z_FI_AP_CLERK", "type": "single",
        "owner": "Maria.Gonzalez", "description": "Accounts Payable clerk — invoice entry",
        "user_count": 9, "last_used": _days_ago(2),
        "transactions": ["FB60", "FB65", "FBL1N", "MIR7"],
        "auth_objects": ["F_BKPF_BUK", "F_BKPF_KOA", "F_LFA1_BUK"],
        "org_values": {"BUKRS": ["1000", "2000"]},
        "has_sod_conflict": False, "business_process": "FI",
    },
    {
        "id": "R003", "name": "Z_FI_AR_PROCESSOR", "type": "single",
        "owner": "James.Okafor", "description": "Accounts Receivable processor — billing and collections",
        "user_count": 8, "last_used": _days_ago(3),
        "transactions": ["FB70", "VF01", "VF02", "FBL5N", "F150"],
        "auth_objects": ["F_BKPF_BUK", "F_KNA1_BUK", "V_VBRK_VKO"],
        "org_values": {"BUKRS": ["1000"], "VKORG": ["1000"]},
        "has_sod_conflict": False, "business_process": "FI",
    },
    {
        "id": "R004", "name": "Z_FI_GL_ACCOUNTANT", "type": "single",
        "owner": "James.Okafor", "description": "General Ledger accountant — journal entries and reconciliation",
        "user_count": 6, "last_used": _days_ago(4),
        "transactions": ["FB01", "FB02", "F-02", "FS00", "FBL3N"],
        "auth_objects": ["F_BKPF_BUK", "F_BKPF_GSB", "F_SKA1_BUK"],
        "org_values": {"BUKRS": ["1000", "2000", "3000"]},
        "has_sod_conflict": False, "business_process": "FI",
    },
    {
        "id": "R005", "name": "Z_FI_PAYMENT_APPROVER", "type": "single",
        "owner": "Sandra.Chen", "description": "Payment run approval and release authority",
        "user_count": 3, "last_used": _days_ago(1),
        "transactions": ["F110", "FBZ2", "F-53"],
        "auth_objects": ["F_BKPF_BUK", "F_PAYR_BUK"],
        "org_values": {"BUKRS": ["1000", "2000"]},
        "has_sod_conflict": False, "business_process": "FI",
    },
    {
        "id": "R006", "name": "Z_AP_TEMP", "type": "single",
        "owner": None, "description": "",
        "user_count": 2, "last_used": _days_ago(180),
        "transactions": ["FB60", "FB65", "F110", "FBL1N"],
        "auth_objects": ["F_BKPF_BUK", "F_BKPF_KOA"],
        "org_values": {"BUKRS": ["1000"]},
        "has_sod_conflict": True, "business_process": "FI",
    },
    {
        "id": "R007", "name": "Z_AP_FINAL2", "type": "single",
        "owner": None, "description": "Copy of AP role (v2)",
        "user_count": 0, "last_used": _days_ago(400),
        "transactions": ["FB60", "FB65", "F110", "FBL1N", "MIR7"],
        "auth_objects": ["F_BKPF_BUK", "F_BKPF_KOA", "F_LFA1_BUK"],
        "org_values": {"BUKRS": ["1000", "2000"]},
        "has_sod_conflict": True, "business_process": "FI",
    },
    {
        "id": "R008", "name": "Z_OLD_ROLE", "type": "single",
        "owner": None, "description": "",
        "user_count": 0, "last_used": _days_ago(730),
        "transactions": ["FB60", "F110"],
        "auth_objects": ["F_BKPF_BUK"],
        "org_values": {},
        "has_sod_conflict": False, "business_process": "FI",
    },

    # ── Procurement / Materials Management (MM) ───────────────────────────
    {
        "id": "R009", "name": "Z_MM_PURCHASER", "type": "single",
        "owner": "Linda.Park", "description": "Purchaser — create and manage purchase orders",
        "user_count": 18, "last_used": _days_ago(1),
        "transactions": ["ME21N", "ME22N", "ME23N", "ME51N", "ME52N"],
        "auth_objects": ["M_BEST_BSA", "M_BEST_EKO", "M_BEST_EKG"],
        "org_values": {"EKORG": ["1000"], "WERKS": ["1000", "2000"]},
        "has_sod_conflict": False, "business_process": "MM",
    },
    {
        "id": "R010", "name": "Z_MM_BUYER", "type": "single",
        "owner": "Linda.Park", "description": "Buyer — create purchase orders and requisitions",
        "user_count": 12, "last_used": _days_ago(2),
        "transactions": ["ME21N", "ME22N", "ME51N", "ME52N"],
        "auth_objects": ["M_BEST_BSA", "M_BEST_EKO"],
        "org_values": {"EKORG": ["1000"], "WERKS": ["1000"]},
        "has_sod_conflict": False, "business_process": "MM",
    },
    {
        "id": "R011", "name": "Z_MM_GR_PROCESSOR", "type": "single",
        "owner": "Tom.Fischer", "description": "Goods receipt processor — MIGO goods movements",
        "user_count": 22, "last_used": _days_ago(1),
        "transactions": ["MIGO", "MB51", "MB52", "MMBE"],
        "auth_objects": ["M_MSEG_BWA", "M_MSEG_WMB"],
        "org_values": {"WERKS": ["1000", "2000", "3000"]},
        "has_sod_conflict": False, "business_process": "MM",
    },
    {
        "id": "R012", "name": "Z_MM_INVOICE_VERIFY", "type": "single",
        "owner": "Tom.Fischer", "description": "Invoice verification — 3-way match processing",
        "user_count": 7, "last_used": _days_ago(3),
        "transactions": ["MIRO", "MIR4", "MIR6", "MIR7"],
        "auth_objects": ["M_RECH_WRK", "M_RECH_EKO"],
        "org_values": {"WERKS": ["1000"], "EKORG": ["1000"]},
        "has_sod_conflict": False, "business_process": "MM",
    },
    {
        "id": "R013", "name": "Z_MM_GR_PROC_COPY", "type": "single",
        "owner": None, "description": "Goods receipt role - copy",
        "user_count": 3, "last_used": _days_ago(95),
        "transactions": ["MIGO", "MB51", "MB52"],
        "auth_objects": ["M_MSEG_BWA", "M_MSEG_WMB"],
        "org_values": {"WERKS": ["1000"]},
        "has_sod_conflict": False, "business_process": "MM",
    },
    {
        "id": "R014", "name": "z_mm_purchaser_old", "type": "single",
        "owner": None, "description": "",
        "user_count": 0, "last_used": _days_ago(500),
        "transactions": ["ME21N", "ME22N", "ME23N"],
        "auth_objects": ["M_BEST_BSA", "M_BEST_EKO"],
        "org_values": {"EKORG": ["1000"]},
        "has_sod_conflict": False, "business_process": "MM",
    },

    # ── Sales / Order-to-Cash (SD) ─────────────────────────────────────────
    {
        "id": "R015", "name": "Z_SD_ORDER_ENTRY", "type": "single",
        "owner": "Rachel.Adeyemi", "description": "Sales order entry — VA01/VA02 access",
        "user_count": 25, "last_used": _days_ago(1),
        "transactions": ["VA01", "VA02", "VA03", "VA05"],
        "auth_objects": ["V_VBAK_AAT", "V_VBAK_VKO"],
        "org_values": {"VKORG": ["1000", "2000"], "VTWEG": ["10"]},
        "has_sod_conflict": False, "business_process": "SD",
    },
    {
        "id": "R016", "name": "Z_SD_BILLING", "type": "single",
        "owner": "Rachel.Adeyemi", "description": "Billing clerk — invoice creation and output",
        "user_count": 11, "last_used": _days_ago(2),
        "transactions": ["VF01", "VF02", "VF04", "VFX3"],
        "auth_objects": ["V_VBRK_VKO", "V_VBRK_FKA"],
        "org_values": {"VKORG": ["1000"], "FKART": ["F2"]},
        "has_sod_conflict": False, "business_process": "SD",
    },
    {
        "id": "R017", "name": "Z_SD_DELIVERY", "type": "single",
        "owner": "Rachel.Adeyemi", "description": "Shipping and delivery processing",
        "user_count": 15, "last_used": _days_ago(1),
        "transactions": ["VL01N", "VL02N", "VL10A", "VT01N"],
        "auth_objects": ["V_LIKP_VST", "V_LIKP_BND"],
        "org_values": {"VSTEL": ["1000"]},
        "has_sod_conflict": False, "business_process": "SD",
    },
    {
        "id": "R018", "name": "Z_SD_PRICING", "type": "single",
        "owner": "Carlos.Rivera", "description": "Pricing condition maintenance",
        "user_count": 4, "last_used": _days_ago(10),
        "transactions": ["VK11", "VK12", "VK13", "V/LD"],
        "auth_objects": ["V_KONH_VKO"],
        "org_values": {"VKORG": ["1000", "2000"]},
        "has_sod_conflict": False, "business_process": "SD",
    },
    {
        "id": "R019", "name": "Z_SD_ORDER_ENTRY_V2", "type": "single",
        "owner": None, "description": "Order entry role version 2",
        "user_count": 1, "last_used": _days_ago(200),
        "transactions": ["VA01", "VA02", "VA03"],
        "auth_objects": ["V_VBAK_AAT", "V_VBAK_VKO"],
        "org_values": {"VKORG": ["1000"], "VTWEG": ["10"]},
        "has_sod_conflict": False, "business_process": "SD",
    },

    # ── Human Resources (HR) ──────────────────────────────────────────────
    {
        "id": "R020", "name": "Z_HR_PA_ADMIN", "type": "single",
        "owner": "Priya.Sharma", "description": "HR PA administrator — employee master data maintenance",
        "user_count": 5, "last_used": _days_ago(2),
        "transactions": ["PA30", "PA40", "PA20", "PPIN"],
        "auth_objects": ["P_ORGIN", "P_PERNR"],
        "org_values": {"PERSA": ["1000"], "PERSG": ["1"]},
        "has_sod_conflict": False, "business_process": "HR",
    },
    {
        "id": "R021", "name": "Z_HR_PAYROLL_PROC", "type": "single",
        "owner": "Priya.Sharma", "description": "Payroll processor — run and release payroll",
        "user_count": 3, "last_used": _days_ago(5),
        "transactions": ["PC00_M99_CALC", "PC00_M99_CALE", "PU01"],
        "auth_objects": ["P_PYEVRUN", "P_ORGIN"],
        "org_values": {"PERSA": ["1000"]},
        "has_sod_conflict": False, "business_process": "HR",
    },
    {
        "id": "R022", "name": "Z_HR_TIME_ADMIN", "type": "single",
        "owner": "Priya.Sharma", "description": "Time management — absence and attendance recording",
        "user_count": 8, "last_used": _days_ago(1),
        "transactions": ["PA61", "PA62", "PA63", "PT60"],
        "auth_objects": ["P_ORGIN", "P_TCODE"],
        "org_values": {"PERSA": ["1000", "2000"]},
        "has_sod_conflict": False, "business_process": "HR",
    },
    {
        "id": "R023", "name": "Z_HR_SELF_SERVICE", "type": "single",
        "owner": "IT.Helpdesk", "description": "Employee self-service access",
        "user_count": 450, "last_used": _days_ago(1),
        "transactions": ["ESS"],
        "auth_objects": ["P_PERNR"],
        "org_values": {},
        "has_sod_conflict": False, "business_process": "HR",
    },
    {
        "id": "R024", "name": "Z_HR_PA_ADMIN_COPY", "type": "single",
        "owner": None, "description": "Copy of HR PA Admin",
        "user_count": 0, "last_used": _days_ago(300),
        "transactions": ["PA30", "PA40", "PA20"],
        "auth_objects": ["P_ORGIN", "P_PERNR"],
        "org_values": {"PERSA": ["1000"]},
        "has_sod_conflict": False, "business_process": "HR",
    },

    # ── Basis / Security ──────────────────────────────────────────────────
    {
        "id": "R025", "name": "Z_BASIS_USER_ADMIN", "type": "single",
        "owner": "Klaus.Bauer", "description": "User administration — create and maintain user accounts",
        "user_count": 4, "last_used": _days_ago(1),
        "transactions": ["SU01", "SU10", "SUIM"],
        "auth_objects": ["S_USR_GRP", "S_USR_PRF"],
        "org_values": {},
        "has_sod_conflict": False, "business_process": "BASIS",
    },
    {
        "id": "R026", "name": "Z_BASIS_ROLE_ADMIN", "type": "single",
        "owner": "Klaus.Bauer", "description": "Role and profile administration",
        "user_count": 3, "last_used": _days_ago(2),
        "transactions": ["PFCG", "SU25", "SU24"],
        "auth_objects": ["S_USR_GRP", "S_DEVELOP"],
        "org_values": {},
        "has_sod_conflict": True, "business_process": "BASIS",
    },
    {
        "id": "R027", "name": "Z_BASIS_TRANSPORT", "type": "single",
        "owner": "Klaus.Bauer", "description": "Transport management — CTS transport release",
        "user_count": 6, "last_used": _days_ago(3),
        "transactions": ["SE09", "SE10", "STMS"],
        "auth_objects": ["S_TRANSPRT", "S_DEVELOP"],
        "org_values": {},
        "has_sod_conflict": False, "business_process": "BASIS",
    },
    {
        "id": "R028", "name": "Z_BASIS_DEVELOPER", "type": "single",
        "owner": "Klaus.Bauer", "description": "ABAP developer access — restricted to non-production",
        "user_count": 8, "last_used": _days_ago(1),
        "transactions": ["SE38", "SE37", "SE11", "SE80", "SHDB"],
        "auth_objects": ["S_DEVELOP", "S_TRANSPRT"],
        "org_values": {},
        "has_sod_conflict": False, "business_process": "BASIS",
    },

    # ── Composite / Derived roles ─────────────────────────────────────────
    {
        "id": "R029", "name": "ZC_FI_FINANCE_USER", "type": "composite",
        "owner": "Finance.Team", "description": "Composite finance user — bundles AP, AR, GL display",
        "user_count": 30, "last_used": _days_ago(1),
        "transactions": ["FB60", "FB70", "FB01", "FBL1N", "FBL3N", "FBL5N"],
        "auth_objects": ["F_BKPF_BUK", "F_KNA1_BUK", "F_LFA1_BUK"],
        "org_values": {"BUKRS": ["1000", "2000"]},
        "has_sod_conflict": False, "business_process": "FI",
    },
    {
        "id": "R030", "name": "ZC_MM_PROCUREMENT", "type": "composite",
        "owner": "Procurement.Team", "description": "Composite procurement user role",
        "user_count": 20, "last_used": _days_ago(1),
        "transactions": ["ME21N", "ME22N", "MIGO", "MIRO"],
        "auth_objects": ["M_BEST_BSA", "M_MSEG_BWA", "M_RECH_WRK"],
        "org_values": {"EKORG": ["1000"], "WERKS": ["1000"]},
        "has_sod_conflict": True, "business_process": "MM",
    },

    # ── More problem roles ─────────────────────────────────────────────────
    {
        "id": "R031", "name": "TEST_ROLE_DO_NOT_USE", "type": "single",
        "owner": None, "description": "",
        "user_count": 5, "last_used": _days_ago(60),
        "transactions": ["SU01", "PFCG", "FB60", "ME21N"],
        "auth_objects": ["S_USR_GRP", "F_BKPF_BUK", "M_BEST_BSA"],
        "org_values": {},
        "has_sod_conflict": True, "business_process": "BASIS",
    },
    {
        "id": "R032", "name": "Z_FI_AP_PROCESSOR_NEW", "type": "single",
        "owner": None, "description": "New version of AP processor",
        "user_count": 0, "last_used": _days_ago(120),
        "transactions": ["FB60", "FB65", "F110", "FBL1N", "MIR7"],
        "auth_objects": ["F_BKPF_BUK", "F_BKPF_KOA", "F_LFA1_BUK"],
        "org_values": {"BUKRS": ["1000", "2000"]},
        "has_sod_conflict": False, "business_process": "FI",
    },
    {
        "id": "R033", "name": "Z_MM_PURCHASER_TEMP", "type": "single",
        "owner": None, "description": "",
        "user_count": 1, "last_used": _days_ago(250),
        "transactions": ["ME21N", "ME22N", "ME23N"],
        "auth_objects": ["M_BEST_BSA", "M_BEST_EKO"],
        "org_values": {"EKORG": ["1000"]},
        "has_sod_conflict": False, "business_process": "MM",
    },
    {
        "id": "R034", "name": "ZApFinanceRole", "type": "single",
        "owner": "Some.User", "description": "AP finance role",
        "user_count": 2, "last_used": _days_ago(150),
        "transactions": ["FB60", "FBL1N"],
        "auth_objects": ["F_BKPF_BUK"],
        "org_values": {"BUKRS": ["1000"]},
        "has_sod_conflict": False, "business_process": "FI",
    },
    {
        "id": "R035", "name": "financeUserRole", "type": "single",
        "owner": "Some.User", "description": "finance user role",
        "user_count": 3, "last_used": _days_ago(180),
        "transactions": ["FB60", "FB01", "FBL3N"],
        "auth_objects": ["F_BKPF_BUK", "F_SKA1_BUK"],
        "org_values": {"BUKRS": ["1000"]},
        "has_sod_conflict": False, "business_process": "FI",
    },
    {
        "id": "R036", "name": "Z_SD_SALES_REP", "type": "single",
        "owner": "Carlos.Rivera", "description": "Sales representative — order entry and customer display",
        "user_count": 35, "last_used": _days_ago(1),
        "transactions": ["VA01", "VA02", "VA03", "VD03"],
        "auth_objects": ["V_VBAK_AAT", "V_VBAK_VKO"],
        "org_values": {"VKORG": ["1000", "2000"]},
        "has_sod_conflict": False, "business_process": "SD",
    },
    {
        "id": "R037", "name": "Z_FI_CONTROLLER", "type": "single",
        "owner": "Sandra.Chen", "description": "Financial controller — reporting and analysis access",
        "user_count": 7, "last_used": _days_ago(2),
        "transactions": ["KE30", "KE31", "KE5Z", "S_ALR_87013543"],
        "auth_objects": ["K_CCA", "F_BKPF_BUK"],
        "org_values": {"BUKRS": ["1000", "2000", "3000"], "KOKRS": ["1000"]},
        "has_sod_conflict": False, "business_process": "FI",
    },
    {
        "id": "R038", "name": "Z_BASIS_MONITOR", "type": "single",
        "owner": "Klaus.Bauer", "description": "System monitoring — SM50, SM66, SM21 read-only",
        "user_count": 10, "last_used": _days_ago(1),
        "transactions": ["SM50", "SM66", "SM21", "SM37"],
        "auth_objects": ["S_ADMI_FCD"],
        "org_values": {},
        "has_sod_conflict": False, "business_process": "BASIS",
    },
    {
        "id": "R039", "name": "Z_HR_RECRUITER", "type": "single",
        "owner": "Priya.Sharma", "description": "HR recruiter — applicant tracking and position management",
        "user_count": 4, "last_used": _days_ago(5),
        "transactions": ["PB10", "PB30", "PQ01"],
        "auth_objects": ["P_APPL", "P_ORGIN"],
        "org_values": {"PERSA": ["1000"]},
        "has_sod_conflict": False, "business_process": "HR",
    },
    {
        "id": "R040", "name": "Z_MM_STOCK_CONTROLLER", "type": "single",
        "owner": "Tom.Fischer", "description": "Stock controller — inventory management and physical inventory",
        "user_count": 9, "last_used": _days_ago(2),
        "transactions": ["MI01", "MI04", "MI07", "MMBE", "MB51"],
        "auth_objects": ["M_MSEG_BWA", "M_MSEG_WMB"],
        "org_values": {"WERKS": ["1000", "2000"]},
        "has_sod_conflict": False, "business_process": "MM",
    },
    {
        "id": "R041", "name": "Z_SD_CREDIT_MGMT", "type": "single",
        "owner": "Rachel.Adeyemi", "description": "Credit management — FD32 credit limit maintenance",
        "user_count": 2, "last_used": _days_ago(14),
        "transactions": ["FD32", "FD33", "VKM1", "VKM3"],
        "auth_objects": ["F_KNA1_BUK", "V_VBAK_VKO"],
        "org_values": {"BUKRS": ["1000"], "VKORG": ["1000"]},
        "has_sod_conflict": False, "business_process": "SD",
    },
    {
        "id": "R042", "name": "ZTEST123", "type": "single",
        "owner": None, "description": "",
        "user_count": 0, "last_used": _days_ago(800),
        "transactions": ["SE38", "SU01", "FB60"],
        "auth_objects": ["S_DEVELOP", "S_USR_GRP", "F_BKPF_BUK"],
        "org_values": {},
        "has_sod_conflict": True, "business_process": "BASIS",
    },
    {
        "id": "R043", "name": "Z_FI_AP_PROCESSOR_BACKUP", "type": "single",
        "owner": None, "description": "Backup AP processor role",
        "user_count": 0, "last_used": None,
        "transactions": ["FB60", "FB65", "F110", "FBL1N"],
        "auth_objects": ["F_BKPF_BUK", "F_BKPF_KOA", "F_LFA1_BUK"],
        "org_values": {"BUKRS": ["1000"]},
        "has_sod_conflict": False, "business_process": "FI",
    },
    {
        "id": "R044", "name": "Z_FI_AUDITOR", "type": "single",
        "owner": "External.Audit", "description": "Read-only auditor access to FI postings",
        "user_count": 5, "last_used": _days_ago(30),
        "transactions": ["FBL1N", "FBL3N", "FBL5N", "FB03"],
        "auth_objects": ["F_BKPF_BUK"],
        "org_values": {"BUKRS": ["1000", "2000", "3000"]},
        "has_sod_conflict": False, "business_process": "FI",
    },
]


def _build_index(catalogue: List[Dict]) -> Dict[str, Dict]:
    return {r["id"]: r for r in catalogue}


# ---------------------------------------------------------------------------
# Naming convention patterns
# ---------------------------------------------------------------------------

# Z_ prefix, uppercase, using underscore delimiters, segment pattern:
#   Z_<PROCESS>_<FUNCTION>[_<DETAIL>]
# Composite roles: ZC_ prefix
_VALID_SINGLE_PATTERN = re.compile(r"^Z_[A-Z]{2,6}_[A-Z][A-Z0-9_]+$")
_VALID_COMPOSITE_PATTERN = re.compile(r"^ZC_[A-Z]{2,6}_[A-Z][A-Z0-9_]+$")

_KNOWN_ANTIPATTERNS = [
    (re.compile(r"(?i)temp", re.IGNORECASE), "contains 'TEMP' — use versioned names"),
    (re.compile(r"(?i)old", re.IGNORECASE), "contains 'OLD' — retire or rename"),
    (re.compile(r"(?i)copy", re.IGNORECASE), "contains 'COPY' — merge back to source"),
    (re.compile(r"(?i)test", re.IGNORECASE), "contains 'TEST' — test roles must not exist in production"),
    (re.compile(r"(?i)backup", re.IGNORECASE), "contains 'BACKUP' — redundant; use the canonical role"),
    (re.compile(r"\d+$"), "ends with a digit — suggests uncontrolled versioning"),
    (re.compile(r"(?i)final"), "contains 'FINAL' — suggests ad-hoc duplication"),
    (re.compile(r"(?i)new"), "contains 'NEW' — rename to reflect function, not lifecycle"),
]


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class RoleIntelligenceEngine:
    """
    Analyses the SAP role estate for duplication, sprawl, health issues,
    and consolidation opportunities.

    Data is loaded from the ``role_intelligence`` database table via
    ``RoleIntelligenceRecord``.  On the first call to any public method,
    ``_ensure_loaded()`` checks whether the table contains rows for the active
    tenant.  If empty, the 44 hardcoded seed roles are inserted and then
    cached in ``self._catalogue`` / ``self._index`` for the lifetime of the
    engine instance.

    Passing an explicit ``catalogue`` overrides DB loading entirely — this
    is used by unit tests.

    All analysis algorithms (similarity, dedup, health, naming) are unchanged
    from the original implementation.
    """

    def __init__(
        self,
        catalogue: Optional[List[Dict]] = None,
        tenant_id: str = "tenant_default",
    ) -> None:
        self._tenant_id = tenant_id
        self._loaded = False

        if catalogue is not None:
            # Test / override path — skip DB entirely
            self._catalogue = catalogue
            self._index: Dict[str, Dict] = _build_index(self._catalogue)
            self._loaded = True
        else:
            self._catalogue: List[Dict[str, Any]] = []
            self._index: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # DB loading
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """
        Guarantee that ``self._catalogue`` and ``self._index`` are populated.

        Strategy:
        1. Query the DB for all RoleIntelligenceRecord rows for this tenant.
        2. If zero rows exist, seed the DB with ``_SEED_CATALOGUE`` and re-query.
        3. Convert each ORM row to a catalogue dict via ``to_catalogue_dict()``.
        4. Cache the result so subsequent calls within the same engine instance
           are served from memory without hitting the DB again.
        """
        if self._loaded:
            return

        try:
            if not db_manager._initialized:
                db_manager.init()
                db_manager.create_tables()

            with db_manager.session_scope() as session:
                count = (
                    session.query(RoleIntelligenceRecord)
                    .filter(RoleIntelligenceRecord.tenant_id == self._tenant_id)
                    .count()
                )

                if count == 0:
                    logger.info(
                        "role_intelligence table is empty for tenant '%s' — seeding %d roles",
                        self._tenant_id,
                        len(_SEED_CATALOGUE),
                    )
                    self._seed_db(session)

                records = (
                    session.query(RoleIntelligenceRecord)
                    .filter(RoleIntelligenceRecord.tenant_id == self._tenant_id)
                    .order_by(RoleIntelligenceRecord.role_name)
                    .all()
                )

                self._catalogue = [r.to_catalogue_dict() for r in records]

        except Exception as exc:
            logger.warning(
                "DB load failed for RoleIntelligenceEngine (%s); "
                "falling back to in-memory seed data. Error: %s",
                self._tenant_id,
                exc,
            )
            self._catalogue = [self._seed_entry_to_catalogue(e) for e in _SEED_CATALOGUE]

        self._index = _build_index(self._catalogue)
        self._loaded = True
        logger.debug(
            "RoleIntelligenceEngine loaded %d roles for tenant '%s'",
            len(self._catalogue),
            self._tenant_id,
        )

    def _seed_db(self, session) -> None:
        """Insert all seed entries into the DB for the active tenant."""
        for entry in _SEED_CATALOGUE:
            record = RoleIntelligenceRecord(
                tenant_id=self._tenant_id,
                role_name=entry["name"],
                description=entry.get("description") or "",
                role_type=entry.get("type", "single"),
                owner=entry.get("owner"),
                department=None,
                transactions=entry.get("transactions", []),
                auth_objects=entry.get("auth_objects", []),
                org_values=entry.get("org_values", {}),
                user_count=entry.get("user_count", 0),
                last_used=entry.get("last_used"),
                has_sod_conflicts=bool(entry.get("has_sod_conflict", False)),
                risk_level="high" if entry.get("has_sod_conflict") else "low",
                naming_convention_ok=True,  # will be computed by the engine
                system="SAP_ERP",
                business_process=entry.get("business_process"),
                is_seed=True,
            )
            session.add(record)

    @staticmethod
    def _seed_entry_to_catalogue(entry: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a seed dict to the catalogue dict format (fallback path)."""
        return {
            "id": entry["name"],
            "db_id": None,
            "name": entry["name"],
            "type": entry.get("type", "single"),
            "owner": entry.get("owner"),
            "description": entry.get("description") or "",
            "user_count": entry.get("user_count", 0),
            "last_used": entry.get("last_used"),
            "transactions": entry.get("transactions", []),
            "auth_objects": entry.get("auth_objects", []),
            "org_values": entry.get("org_values", {}),
            "has_sod_conflict": bool(entry.get("has_sod_conflict", False)),
            "business_process": entry.get("business_process", "UNKNOWN"),
        }

    def invalidate_cache(self) -> None:
        """Force a reload from the DB on the next method call."""
        self._loaded = False
        self._catalogue = []
        self._index = {}

    # ------------------------------------------------------------------
    # 1. Role Similarity Analysis
    # ------------------------------------------------------------------

    def analyze_similarity(self, role_a_id: str, role_b_id: str) -> SimilarityResult:
        """
        Compare two roles and return a structured similarity result.

        Similarity is computed as a weighted average:
        - Transactions: 50 %
        - Auth objects: 35 %
        - Org values:   15 %
        """
        self._ensure_loaded()
        role_a = self._get_role(role_a_id)
        role_b = self._get_role(role_b_id)

        txn_score, shared_txn, only_a_txn, only_b_txn = self._jaccard(
            set(role_a["transactions"]),
            set(role_b["transactions"]),
        )
        obj_score, shared_obj, _, _ = self._jaccard(
            set(role_a["auth_objects"]),
            set(role_b["auth_objects"]),
        )
        org_score = self._org_similarity(role_a["org_values"], role_b["org_values"])

        overall = (txn_score * 0.50) + (obj_score * 0.35) + (org_score * 0.15)

        recommendation = self._similarity_recommendation(overall, role_a, role_b)

        return SimilarityResult(
            role_a=role_a_id,
            role_b=role_b_id,
            overall_score=overall,
            transaction_score=txn_score,
            auth_object_score=obj_score,
            org_value_score=org_score,
            shared_transactions=sorted(shared_txn),
            shared_auth_objects=sorted(shared_obj),
            unique_to_a=sorted(only_a_txn),
            unique_to_b=sorted(only_b_txn),
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------
    # 2. Duplicate Detection
    # ------------------------------------------------------------------

    def find_duplicates(self, threshold: float = 0.80) -> List[DuplicateGroup]:
        """
        Scan all roles and cluster near-duplicates where similarity >= threshold.
        Returns one DuplicateGroup per cluster.
        """
        self._ensure_loaded()
        ids = [r["id"] for r in self._catalogue]
        visited: Set[str] = set()
        groups: List[DuplicateGroup] = []

        for i, id_a in enumerate(ids):
            if id_a in visited:
                continue
            cluster = [id_a]
            best_score = 0.0
            for id_b in ids[i + 1:]:
                if id_b in visited:
                    continue
                result = self.analyze_similarity(id_a, id_b)
                if result.overall_score >= threshold:
                    cluster.append(id_b)
                    best_score = max(best_score, result.overall_score)

            if len(cluster) > 1:
                for rid in cluster:
                    visited.add(rid)
                canonical = self._pick_canonical(cluster)
                retirements = [r for r in cluster if r != canonical]
                # shared transactions from first pair analysis
                first_pair = self.analyze_similarity(canonical, retirements[0])
                groups.append(DuplicateGroup(
                    group_id=f"DUP_{len(groups)+1:03d}",
                    roles=cluster,
                    similarity_score=best_score,
                    shared_transactions=first_pair.shared_transactions,
                    shared_auth_objects=first_pair.shared_auth_objects,
                    recommended_canonical=canonical,
                    retirement_candidates=retirements,
                    reason=self._duplicate_reason(cluster),
                ))

        return groups

    # ------------------------------------------------------------------
    # 3. Usage Analytics
    # ------------------------------------------------------------------

    def get_usage_stats(self, stale_days: int = 90) -> UsageReport:
        """
        Analyse role usage across the catalogue.

        Roles with 0 users are unused. Roles last used > stale_days days
        ago are considered stale. Roles with 1-2 users are flagged as
        low-usage candidates for consolidation.
        """
        self._ensure_loaded()
        now = datetime.now()
        unused: List[RoleUsageStat] = []
        stale: List[RoleUsageStat] = []
        low_usage: List[RoleUsageStat] = []
        active: List[RoleUsageStat] = []
        retirement_candidates: List[str] = []

        for role in self._catalogue:
            last_used: Optional[datetime] = role["last_used"]
            user_count: int = role["user_count"]
            days_since: Optional[int] = None
            if last_used:
                days_since = (now - last_used).days

            trend = self._usage_trend(role)

            stat = RoleUsageStat(
                role_id=role["id"],
                role_name=role["name"],
                user_count=user_count,
                last_used=last_used,
                days_since_used=days_since,
                is_unused=user_count == 0,
                usage_trend=trend,
            )

            if user_count == 0:
                unused.append(stat)
                retirement_candidates.append(role["id"])
            elif last_used and days_since and days_since > stale_days:
                stale.append(stat)
                if user_count <= 2:
                    retirement_candidates.append(role["id"])
            elif user_count <= 2:
                low_usage.append(stat)
            else:
                active.append(stat)

        return UsageReport(
            total_roles=len(self._catalogue),
            unused_roles=sorted(unused, key=lambda s: s.role_name),
            stale_roles=sorted(stale, key=lambda s: s.days_since_used or 0, reverse=True),
            low_usage_roles=sorted(low_usage, key=lambda s: s.user_count),
            active_roles=sorted(active, key=lambda s: s.user_count, reverse=True),
            retirement_candidates=retirement_candidates,
        )

    # ------------------------------------------------------------------
    # 4. Consolidation Recommendations
    # ------------------------------------------------------------------

    def recommend_consolidation(self, threshold: float = 0.70) -> ConsolidationPlan:
        """
        Build a consolidation plan by grouping similar roles and estimating
        the effort and risk to merge each group.
        """
        self._ensure_loaded()
        dupe_groups = self.find_duplicates(threshold)
        consolidation_groups: List[ConsolidationGroup] = []
        total_saved = 0

        for i, dg in enumerate(dupe_groups):
            roles_in_group = [self._index[r] for r in dg.roles]
            user_total = sum(r["user_count"] for r in roles_in_group)
            similarity = dg.similarity_score
            roles_saved = len(dg.roles) - 1

            effort, risk, risk_reason = self._estimate_effort_risk(roles_in_group, user_total)
            proposed_name = self._propose_consolidated_name(roles_in_group)
            steps = self._consolidation_steps(roles_in_group, proposed_name)

            consolidation_groups.append(ConsolidationGroup(
                group_id=f"CONS_{i+1:03d}",
                roles=dg.roles,
                proposed_name=proposed_name,
                similarity_score=similarity,
                user_count_total=user_total,
                effort_days=effort,
                risk=risk,
                risk_reason=risk_reason,
                steps=steps,
                estimated_roles_saved=roles_saved,
            ))
            total_saved += roles_saved

        high_priority = [
            g.group_id for g in consolidation_groups
            if g.risk == ConsolidationRisk.LOW and g.estimated_roles_saved >= 1
        ]

        return ConsolidationPlan(
            total_roles_analysed=len(self._catalogue),
            consolidation_groups=consolidation_groups,
            total_roles_saveable=total_saved,
            total_effort_days=sum(g.effort_days for g in consolidation_groups),
            high_priority_groups=high_priority,
        )

    # ------------------------------------------------------------------
    # 5. Role Health Score
    # ------------------------------------------------------------------

    def calculate_health(self, role_id: str) -> RoleHealthScore:
        """
        Score a role 0-100 across six health dimensions.
        Each dimension contributes a weighted portion to the overall score.

        Weights:
        - Owner presence:        20
        - Description quality:   15
        - SoD conflicts:         25
        - User count:            10
        - Recent usage:          20
        - Naming convention:     10
        """
        self._ensure_loaded()
        now = datetime.now()
        role = self._get_role(role_id)
        issues: List[str] = []
        recommendations: List[str] = []
        dimensions: Dict[str, int] = {}

        # Owner (max 20)
        owner_score = 20 if role.get("owner") else 0
        dimensions["owner"] = owner_score
        if not role.get("owner"):
            issues.append("No role owner assigned.")
            recommendations.append("Assign a named business owner via the Role Engineering module.")

        # Description (max 15)
        desc = role.get("description", "").strip()
        if len(desc) >= 30:
            desc_score = 15
        elif len(desc) >= 10:
            desc_score = 8
        else:
            desc_score = 0
            issues.append("Description is missing or too short.")
            recommendations.append("Add a meaningful description (at least 30 characters) explaining the business purpose.")
        dimensions["description"] = desc_score

        # SoD conflicts (max 25)
        if role.get("has_sod_conflict"):
            sod_score = 0
            issues.append("Role contains unmitigated SoD conflicts.")
            recommendations.append("Run SoD analysis and apply mitigation controls or split the role.")
        else:
            sod_score = 25
        dimensions["sod_conflicts"] = sod_score

        # User count (max 10) — penalise 0 users and extreme outliers
        uc = role["user_count"]
        if uc == 0:
            uc_score = 0
            issues.append("Role has no assigned users — candidate for retirement.")
            recommendations.append("Evaluate for decommissioning or archival.")
        elif uc == 1:
            uc_score = 5
            issues.append("Role is assigned to only 1 user — possible personal role.")
            recommendations.append("Validate whether a shared business role is more appropriate.")
        elif uc > 200:
            uc_score = 7
            issues.append("Very high user count — review whether role scope is too broad.")
            recommendations.append("Consider splitting into more targeted roles with narrower scope.")
        else:
            uc_score = 10
        dimensions["user_count"] = uc_score

        # Recent usage (max 20)
        last_used: Optional[datetime] = role.get("last_used")
        if last_used is None:
            usage_score = 0
            issues.append("Role has never been used.")
            recommendations.append("Remove if there is no planned use.")
        else:
            days = (now - last_used).days
            if days <= 30:
                usage_score = 20
            elif days <= 90:
                usage_score = 12
            elif days <= 180:
                usage_score = 5
            else:
                usage_score = 0
                issues.append(f"Role last used {days} days ago — likely stale.")
                recommendations.append("Initiate a retirement review if no business case exists.")
        dimensions["recent_usage"] = usage_score

        # Naming (max 10)
        naming_ok, naming_issue = self._check_naming(role)
        naming_score = 10 if naming_ok else 0
        dimensions["naming"] = naming_score
        if not naming_ok and naming_issue:
            issues.append(f"Naming issue: {naming_issue.description}")
            recommendations.append(f"Rename to: {naming_issue.suggested_name}")

        overall = sum(dimensions.values())
        grade = self._grade(overall)

        return RoleHealthScore(
            role_id=role_id,
            role_name=role["name"],
            overall_score=overall,
            dimension_scores=dimensions,
            issues=issues,
            recommendations=recommendations,
            grade=grade,
        )

    def calculate_health_all(self) -> List[RoleHealthScore]:
        """Return health scores for every role in the catalogue, sorted by score ascending."""
        self._ensure_loaded()
        scores = [self.calculate_health(r["id"]) for r in self._catalogue]
        return sorted(scores, key=lambda s: s.overall_score)

    # ------------------------------------------------------------------
    # 6. Naming Convention Analysis
    # ------------------------------------------------------------------

    def analyze_naming(self) -> NamingReport:
        """
        Scan all roles for naming convention violations and return a
        structured report with suggested corrected names.
        """
        self._ensure_loaded()
        issues: List[NamingIssue] = []
        compliant = 0

        for role in self._catalogue:
            ok, issue = self._check_naming(role)
            if ok:
                compliant += 1
            elif issue:
                issues.append(issue)

        convention_summary = {
            "single_role_pattern": "Z_<PROCESS>_<FUNCTION>[_<DETAIL>] (all uppercase)",
            "composite_role_pattern": "ZC_<PROCESS>_<FUNCTION>[_<DETAIL>] (all uppercase)",
            "process_codes": ["FI", "MM", "SD", "HR", "BASIS", "TR", "AA", "WM", "QM", "PM", "PS"],
            "forbidden_tokens": ["TEMP", "OLD", "COPY", "TEST", "BACKUP", "FINAL", "NEW", "V2", "V3"],
        }

        return NamingReport(
            total_roles=len(self._catalogue),
            compliant_count=compliant,
            non_compliant_count=len(issues),
            issues=issues,
            convention_summary=convention_summary,
        )

    # ------------------------------------------------------------------
    # Full Analysis
    # ------------------------------------------------------------------

    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Run all analyses and return a consolidated result dictionary.
        Suitable for the POST /analyze endpoint.
        """
        self._ensure_loaded()
        usage = self.get_usage_stats()
        duplicates = self.find_duplicates()
        consolidation = self.recommend_consolidation()
        health_scores = self.calculate_health_all()
        naming = self.analyze_naming()

        avg_health = (
            sum(h.overall_score for h in health_scores) / len(health_scores)
            if health_scores else 0
        )
        critical_roles = [h for h in health_scores if h.overall_score < 30]

        return {
            "summary": {
                "total_roles": len(self._catalogue),
                "average_health_score": round(avg_health, 1),
                "duplicate_groups": len(duplicates),
                "unused_roles": len(usage.unused_roles),
                "stale_roles": len(usage.stale_roles),
                "naming_violations": naming.non_compliant_count,
                "roles_saveable_via_consolidation": consolidation.total_roles_saveable,
                "critical_health_roles": len(critical_roles),
            },
            "usage": usage.to_dict(),
            "duplicates": [d.to_dict() for d in duplicates],
            "consolidation": consolidation.to_dict(),
            "health_scores": [h.to_dict() for h in health_scores],
            "naming": naming.to_dict(),
            "analysed_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Estate Overview
    # ------------------------------------------------------------------

    def get_overview(self) -> Dict[str, Any]:
        """
        Lightweight overview of the role estate — no deep analysis.
        Returns headline metrics suitable for a dashboard card.
        """
        self._ensure_loaded()
        health_scores = self.calculate_health_all()
        avg_health = (
            sum(h.overall_score for h in health_scores) / len(health_scores)
            if health_scores else 0
        )

        by_process: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        roles_with_owner = 0
        roles_with_sod = 0

        for role in self._catalogue:
            bp = role.get("business_process", "UNKNOWN")
            by_process[bp] = by_process.get(bp, 0) + 1
            rt = role.get("type", "single")
            by_type[rt] = by_type.get(rt, 0) + 1
            if role.get("owner"):
                roles_with_owner += 1
            if role.get("has_sod_conflict"):
                roles_with_sod += 1

        unused_count = sum(1 for r in self._catalogue if r["user_count"] == 0)
        no_owner_count = len(self._catalogue) - roles_with_owner

        grade_distribution: Dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for h in health_scores:
            grade_distribution[h.grade] = grade_distribution.get(h.grade, 0) + 1

        return {
            "total_roles": len(self._catalogue),
            "average_health_score": round(avg_health, 1),
            "grade_distribution": grade_distribution,
            "roles_by_business_process": by_process,
            "roles_by_type": by_type,
            "unused_roles": unused_count,
            "roles_without_owner": no_owner_count,
            "roles_with_sod_conflicts": roles_with_sod,
            "ownership_rate_pct": round(roles_with_owner / len(self._catalogue) * 100, 1),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_role(self, role_id: str) -> Dict:
        if role_id not in self._index:
            raise KeyError(f"Role '{role_id}' not found in catalogue.")
        return self._index[role_id]

    @staticmethod
    def _jaccard(
        set_a: Set[str], set_b: Set[str]
    ) -> Tuple[float, Set[str], Set[str], Set[str]]:
        """Jaccard similarity with shared/unique breakdown."""
        if not set_a and not set_b:
            return 1.0, set(), set(), set()
        if not set_a or not set_b:
            return 0.0, set(), set_a, set_b
        intersection = set_a & set_b
        union = set_a | set_b
        score = len(intersection) / len(union)
        return score, intersection, set_a - set_b, set_b - set_a

    @staticmethod
    def _org_similarity(org_a: Dict, org_b: Dict) -> float:
        """
        Compare org-level values. Score is the average Jaccard across
        all org keys present in either role.
        """
        all_keys = set(org_a.keys()) | set(org_b.keys())
        if not all_keys:
            return 1.0
        scores = []
        for key in all_keys:
            vals_a = set(org_a.get(key, []))
            vals_b = set(org_b.get(key, []))
            if not vals_a and not vals_b:
                scores.append(1.0)
            elif not vals_a or not vals_b:
                scores.append(0.0)
            else:
                union = vals_a | vals_b
                inter = vals_a & vals_b
                scores.append(len(inter) / len(union))
        return sum(scores) / len(scores)

    @staticmethod
    def _similarity_recommendation(score: float, role_a: Dict, role_b: Dict) -> str:
        if score >= 0.95:
            return (
                f"Roles are near-identical ({score*100:.0f}% similar). "
                "One should be retired immediately after migrating its users."
            )
        if score >= 0.80:
            return (
                f"Roles are highly similar ({score*100:.0f}% similar). "
                "Evaluate consolidation — merge unique permissions into one canonical role."
            )
        if score >= 0.60:
            return (
                f"Roles share significant overlap ({score*100:.0f}%). "
                "Review whether a composite role structure would reduce maintenance overhead."
            )
        if score >= 0.30:
            return (
                f"Roles have moderate overlap ({score*100:.0f}%). "
                "No immediate consolidation needed; monitor for future drift."
            )
        return f"Roles are distinct ({score*100:.0f}% similar). No consolidation warranted."

    def _pick_canonical(self, cluster: List[str]) -> str:
        """
        Choose the role to keep from a duplicate cluster.
        Preference: has owner > higher user count > longer description > lowest ID.
        """
        scored = []
        for rid in cluster:
            role = self._index[rid]
            owner_pts = 100 if role.get("owner") else 0
            user_pts = role["user_count"]
            desc_pts = len(role.get("description", ""))
            scored.append((rid, owner_pts + user_pts + desc_pts))
        return max(scored, key=lambda x: x[1])[0]

    @staticmethod
    def _duplicate_reason(cluster: List[str]) -> str:
        if len(cluster) == 2:
            return "Two roles share nearly identical permission sets — likely a copy was created instead of using the original."
        return f"{len(cluster)} roles share nearly identical permission sets — indicates uncontrolled role copying over time."

    @staticmethod
    def _usage_trend(role: Dict) -> str:
        uc = role["user_count"]
        last_used = role.get("last_used")
        if uc == 0 or last_used is None:
            return "dead"
        days = (datetime.now() - last_used).days
        if days > 180:
            return "declining"
        if uc > 20:
            return "growing"
        if days <= 7:
            return "stable"
        return "stable"

    def _estimate_effort_risk(
        self, roles: List[Dict], user_total: int
    ) -> Tuple[int, ConsolidationRisk, str]:
        """
        Estimate effort (days) and risk level for merging a group of roles.
        """
        base_effort = 2 + len(roles)  # minimum two days per merge
        user_factor = max(1, user_total // 20)
        effort = base_effort + user_factor

        sod_roles = [r for r in roles if r.get("has_sod_conflict")]
        if sod_roles:
            return effort + 3, ConsolidationRisk.HIGH, (
                "One or more roles contain SoD conflicts; merging requires SoD re-analysis."
            )
        if user_total > 50:
            return effort, ConsolidationRisk.MEDIUM, (
                f"High combined user count ({user_total}) — change management effort required."
            )
        return effort, ConsolidationRisk.LOW, (
            "Low user count and no SoD conflicts — straightforward merge."
        )

    @staticmethod
    def _propose_consolidated_name(roles: List[Dict]) -> str:
        """
        Derive a proposed canonical name from the group's most-complete role name.
        """
        # Prefer the longest valid Z_ name
        valid = [r["name"] for r in roles if r["name"].startswith("Z_") and r["name"].isupper()]
        if valid:
            return max(valid, key=len)
        # Fall back to the most-used role's name
        return max(roles, key=lambda r: r["user_count"])["name"]

    @staticmethod
    def _consolidation_steps(roles: List[Dict], proposed_name: str) -> List[str]:
        return [
            f"1. Identify all users currently assigned to: {', '.join(r['name'] for r in roles)}.",
            f"2. Create or designate '{proposed_name}' as the canonical role.",
            "3. Run SoD analysis on the merged permission set before activating.",
            f"4. Re-assign all users from retirement candidates to '{proposed_name}'.",
            "5. Lock and deactivate retirement-candidate roles.",
            "6. After a 30-day observation period, delete retired roles and transport.",
        ]

    def _check_naming(self, role: Dict) -> Tuple[bool, Optional[NamingIssue]]:
        """
        Check a single role against naming conventions.
        Returns (compliant, NamingIssue | None).
        """
        name = role["name"]
        role_type = role.get("type", "single")

        pattern = _VALID_COMPOSITE_PATTERN if role_type == "composite" else _VALID_SINGLE_PATTERN
        if not pattern.match(name):
            issue_type = "pattern_mismatch"
            description = (
                f"Name '{name}' does not match the required pattern "
                f"({'ZC_' if role_type == 'composite' else 'Z_'}<PROCESS>_<FUNCTION>)."
            )
            suggested = self._suggest_name(name, role_type)
            return False, NamingIssue(
                role_id=role["id"],
                role_name=name,
                issue_type=issue_type,
                description=description,
                suggested_name=suggested,
            )

        # Check anti-patterns even if the outer pattern matches
        for antipattern, reason in _KNOWN_ANTIPATTERNS:
            if antipattern.search(name):
                suggested = self._suggest_name(name, role_type)
                return False, NamingIssue(
                    role_id=role["id"],
                    role_name=name,
                    issue_type="antipattern",
                    description=f"Name '{name}' {reason}.",
                    suggested_name=suggested,
                )

        return True, None

    @staticmethod
    def _suggest_name(name: str, role_type: str) -> str:
        """
        Best-effort suggestion: uppercase, replace camelCase with underscores,
        ensure correct prefix, strip anti-pattern tokens.
        """
        cleaned = re.sub(r"([a-z])([A-Z])", r"\1_\2", name).upper()
        cleaned = re.sub(r"[^A-Z0-9_]", "_", cleaned)
        # Strip anti-pattern tokens
        for token in ["_TEMP", "_OLD", "_COPY", "_TEST", "_BACKUP", "_FINAL2",
                      "_FINAL", "_NEW", "_V2", "_V3", "_BACKUP"]:
            cleaned = cleaned.replace(token, "")
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")

        prefix = "ZC_" if role_type == "composite" else "Z_"
        if not cleaned.startswith(prefix):
            # Remove existing Z_ / ZC_ prefix if present, reapply correct one
            cleaned = re.sub(r"^Z(C)?_", "", cleaned)
            cleaned = f"{prefix}{cleaned}"

        return cleaned

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 85:
            return "A"
        if score >= 70:
            return "B"
        if score >= 50:
            return "C"
        if score >= 30:
            return "D"
        return "F"
