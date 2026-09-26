"""
Identity Correlation Engine

Maps and correlates identities across multiple enterprise systems:
- SAP ECC
- SAP S/4HANA
- SuccessFactors (HCM)
- Azure Active Directory

Correlation methods used (in descending confidence weight):
1. Employee ID exact match        — highest confidence
2. Email address exact match      — high confidence
3. Full name fuzzy match          — medium confidence
4. Manager chain + department     — medium confidence
5. Department + location match    — lower confidence

Detects:
- Orphaned accounts (no correlation to any HR record)
- Ghost accounts (active accounts for terminated employees)
- Cross-system SoD risks (combined access across systems violates SoD)
- Conflicting attributes (name mismatch, department mismatch, etc.)

Data persistence:
- All accounts are stored in IdentityAccount (db.models.intelligence)
- All clusters are stored in IdentityClusterRecord (db.models.intelligence)
- On first use, if the DB tables are empty, hardcoded seed data is inserted
  via _ensure_loaded().  All subsequent reads hit the DB.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime
import uuid

from db.database import db_manager
from db.models.intelligence import IdentityAccount, IdentityClusterRecord


# ===========================================================================
# Enumerations
# ===========================================================================

class SystemType(Enum):
    """Supported enterprise system types."""
    SAP_ECC = "sap_ecc"
    SAP_S4HANA = "sap_s4hana"
    SUCCESSFACTORS = "successfactors"
    AZURE_AD = "azure_ad"


class CorrelationMethod(Enum):
    """Method used to correlate two accounts."""
    EMPLOYEE_ID = "employee_id"
    EMAIL = "email"
    FULL_NAME_FUZZY = "full_name_fuzzy"
    MANAGER_CHAIN = "manager_chain"
    DEPARTMENT_LOCATION = "department_location"
    MANUAL = "manual"
    UNMATCHED = "unmatched"


class AccountStatus(Enum):
    """Status of an account in a given system."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    TERMINATED = "terminated"
    PENDING = "pending"


class AnomalyType(Enum):
    """Types of identity anomaly detected by the engine."""
    GHOST_ACCOUNT = "ghost_account"             # Active in IT system, terminated in HR
    ORPHAN_ACCOUNT = "orphan_account"           # No HR correlation at all
    NAME_MISMATCH = "name_mismatch"             # Different display names across systems
    DEPARTMENT_MISMATCH = "department_mismatch" # Different department across systems
    DUPLICATE_ACCOUNT = "duplicate_account"     # Two accounts in same system for same person
    EXCESSIVE_ACCOUNTS = "excessive_accounts"   # More systems than expected for role
    CROSS_SYSTEM_SOD = "cross_system_sod"       # SoD violation only visible across systems
    STALE_ACCOUNT = "stale_account"             # No recent login but account is active


class RiskLevel(Enum):
    """Risk level for a cross-system or individual risk."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ===========================================================================
# Data classes (in-memory domain objects used by all public methods)
# ===========================================================================

@dataclass
class SystemAccount:
    """A single user account in one enterprise system."""
    account_id: str
    system: SystemType
    username: str
    display_name: str
    email: Optional[str]
    employee_id: Optional[str]
    department: Optional[str]
    location: Optional[str]
    manager_id: Optional[str]
    job_title: Optional[str]
    status: AccountStatus
    last_login: Optional[str]
    roles: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class CorrelationLink:
    """A single correlation between two accounts across systems."""
    account_a_id: str
    account_b_id: str
    system_a: SystemType
    system_b: SystemType
    method: CorrelationMethod
    confidence: float           # 0.0 to 100.0
    evidence: List[str]         # Explanation of why these were matched
    created_at: str
    created_by: str = "engine"  # "engine" or "manual"


@dataclass
class IdentityCluster:
    """
    A cluster of accounts across systems believed to belong to the same person.

    The cluster has a canonical identity derived from the authoritative source
    (SuccessFactors / HR system is authoritative for identity attributes).
    """
    cluster_id: str
    canonical_name: str
    canonical_email: Optional[str]
    employee_id: Optional[str]
    department: Optional[str]
    location: Optional[str]
    job_title: Optional[str]
    accounts: List[SystemAccount]
    correlation_links: List[CorrelationLink]
    overall_confidence: float       # Minimum confidence across all links
    risk_level: RiskLevel
    anomalies: List[str]            # Short descriptions of anomalies in this cluster
    last_correlated: str


@dataclass
class OrphanAccount:
    """An account with no confirmed correlation to any other system or HR record."""
    account: SystemAccount
    reason: str                     # Why it is considered an orphan
    risk_level: RiskLevel
    last_login: Optional[str]
    days_since_login: Optional[int]
    recommended_action: str


@dataclass
class CrossSystemRisk:
    """
    A security risk that is only visible when combining access across systems.

    Example: user has AP posting in SAP ECC and payment approval in Azure AD
    workflow — combined, this is a payment SoD violation invisible in either
    system alone.
    """
    cluster_id: str
    canonical_name: str
    risk_id: str
    risk_name: str
    risk_level: RiskLevel
    contributing_accounts: List[Dict[str, str]]     # [{"system": "sap_ecc", "username": "...", "access": "..."}]
    description: str
    sod_rule: Optional[str]
    remediation: str


@dataclass
class IdentityAnomaly:
    """A detected anomaly in the identity landscape."""
    anomaly_id: str
    anomaly_type: AnomalyType
    cluster_id: Optional[str]
    affected_accounts: List[Dict[str, str]]
    description: str
    risk_level: RiskLevel
    detected_at: str
    recommended_action: str
    evidence: List[str]


@dataclass
class CorrelationResult:
    """Result of correlating a single user account to other systems."""
    source_account: SystemAccount
    matched_accounts: List[SystemAccount]
    correlation_links: List[CorrelationLink]
    cluster_id: Optional[str]
    overall_confidence: float
    unmatched_systems: List[SystemType]
    summary: str


@dataclass
class CorrelationStats:
    """Overview statistics for the identity correlation landscape."""
    total_accounts: int
    total_clusters: int
    fully_correlated: int           # Clusters with accounts in all 4 systems
    partially_correlated: int
    orphan_accounts: int
    anomaly_count: int
    cross_system_risks: int
    average_confidence: float
    by_system: Dict[str, int]       # account counts per system
    last_run: str


# ===========================================================================
# Seed data — 28 accounts across 4 systems
# Inserted into DB on first use when the tables are empty.
# ===========================================================================

def _get_tenant_id() -> str:
    """Return the active tenant_id from request context, or env default."""
    try:
        from core.tenant import get_current_tenant
        ctx = get_current_tenant()
        if ctx is not None:
            return ctx.tenant_id
    except Exception:
        pass
    return os.getenv("DEFAULT_TENANT_ID", "tenant_default")


# ---------------------------------------------------------------------------
# Raw seed rows for IdentityAccount
# ---------------------------------------------------------------------------

_SEED_ACCOUNTS = [
    # --- User 1: Alice Johnson — fully correlated, finance ---
    dict(
        account_id="ECC-001", system_type="sap_ecc",
        username="AJOHNSON", display_name="Alice Johnson",
        email="alice.johnson@acme.com", employee_id="EMP001",
        department="Finance", job_title="Senior Accountant", status="active",
        last_login=datetime(2026, 8, 20, 9, 15, 0),
        entitlements={"roles": ["Z_FI_GL_ACCOUNTANT", "Z_FI_AP_ACCOUNTANT"],
                      "location": "New York", "manager_id": "EMP010",
                      "created_at": "2020-03-01T00:00:00Z"},
    ),
    dict(
        account_id="S4-001", system_type="sap_s4hana",
        username="AJOHNSON", display_name="Alice Johnson",
        email="alice.johnson@acme.com", employee_id="EMP001",
        department="Finance", job_title="Senior Accountant", status="active",
        last_login=datetime(2026, 8, 20, 10, 0, 0),
        entitlements={"roles": ["BR_FINANCE_ACCOUNTANT"],
                      "location": "New York", "manager_id": "EMP010",
                      "created_at": "2023-01-15T00:00:00Z"},
    ),
    dict(
        account_id="SF-001", system_type="successfactors",
        username="ajohnson@acme.com", display_name="Alice Johnson",
        email="alice.johnson@acme.com", employee_id="EMP001",
        department="Finance", job_title="Senior Accountant", status="active",
        last_login=datetime(2026, 8, 19, 8, 0, 0),
        entitlements={"groups": ["Finance_US"],
                      "location": "New York", "manager_id": "EMP010",
                      "created_at": "2019-06-01T00:00:00Z"},
    ),
    dict(
        account_id="AAD-001", system_type="azure_ad",
        username="alice.johnson@acme.com", display_name="Alice Johnson",
        email="alice.johnson@acme.com", employee_id="EMP001",
        department="Finance", job_title="Senior Accountant", status="active",
        last_login=datetime(2026, 8, 21, 7, 30, 0),
        entitlements={"groups": ["Finance-Users", "AP-Approvers"],
                      "location": "New York", "manager_id": "EMP010",
                      "created_at": "2019-06-01T00:00:00Z"},
    ),

    # --- User 2: Bob Chen — cross-system SoD risk ---
    dict(
        account_id="ECC-002", system_type="sap_ecc",
        username="BCHEN", display_name="Bob Chen",
        email="bob.chen@acme.com", employee_id="EMP002",
        department="Procurement", job_title="Procurement Specialist", status="active",
        last_login=datetime(2026, 8, 21, 8, 0, 0),
        entitlements={"roles": ["Z_MM_PURCHASER"],
                      "location": "Chicago", "manager_id": "EMP011",
                      "created_at": "2021-04-01T00:00:00Z"},
    ),
    dict(
        account_id="S4-002", system_type="sap_s4hana",
        username="B.CHEN", display_name="Bob Chen",
        email="bob.chen@acme.com", employee_id="EMP002",
        department="Procurement", job_title="Procurement Specialist", status="active",
        last_login=datetime(2026, 8, 20, 14, 0, 0),
        entitlements={"roles": ["BR_MM_PURCHASER"],
                      "location": "Chicago", "manager_id": "EMP011",
                      "created_at": "2023-02-01T00:00:00Z"},
    ),
    dict(
        account_id="SF-002", system_type="successfactors",
        username="bchen@acme.com", display_name="Bob Chen",
        email="bob.chen@acme.com", employee_id="EMP002",
        department="Procurement", job_title="Procurement Specialist", status="active",
        last_login=datetime(2026, 8, 18, 9, 0, 0),
        entitlements={"groups": ["Procurement_US"],
                      "location": "Chicago", "manager_id": "EMP011",
                      "created_at": "2021-04-01T00:00:00Z"},
    ),
    dict(
        account_id="AAD-002", system_type="azure_ad",
        username="bob.chen@acme.com", display_name="Bob Chen",
        email="bob.chen@acme.com", employee_id="EMP002",
        department="Procurement", job_title="Procurement Specialist", status="active",
        last_login=datetime(2026, 8, 21, 7, 55, 0),
        entitlements={"groups": ["Finance-Users", "PO-Approvers"],
                      "location": "Chicago", "manager_id": "EMP011",
                      "created_at": "2021-04-01T00:00:00Z"},
    ),

    # --- User 3: Carol White — ghost account ---
    dict(
        account_id="ECC-003", system_type="sap_ecc",
        username="CWHITE", display_name="Carol White",
        email="carol.white@acme.com", employee_id="EMP003",
        department="HR", job_title="HR Specialist", status="active",
        last_login=datetime(2026, 7, 15, 10, 0, 0),
        entitlements={"roles": ["Z_HR_PAYROLL_ADMIN"],
                      "location": "Houston", "manager_id": "EMP012",
                      "created_at": "2018-01-01T00:00:00Z"},
    ),
    dict(
        account_id="SF-003", system_type="successfactors",
        username="cwhite@acme.com", display_name="Carol White",
        email="carol.white@acme.com", employee_id="EMP003",
        department="HR", job_title="HR Specialist", status="terminated",
        last_login=datetime(2026, 6, 30, 0, 0, 0),
        entitlements={"groups": [],
                      "location": "Houston", "manager_id": "EMP012",
                      "created_at": "2018-01-01T00:00:00Z"},
    ),

    # --- User 4: David Park — orphan accounts (no HR record) ---
    dict(
        account_id="ECC-004", system_type="sap_ecc",
        username="DPARK", display_name="David Park",
        email=None, employee_id=None,
        department="IT", job_title="System Administrator", status="active",
        last_login=datetime(2026, 8, 10, 11, 0, 0),
        entitlements={"roles": ["Z_BASIS_USER_ADMIN", "Z_DEVELOPER"],
                      "location": "Seattle",
                      "created_at": "2019-11-01T00:00:00Z"},
    ),
    dict(
        account_id="AAD-004", system_type="azure_ad",
        username="david.park@acme.com", display_name="David Park",
        email="david.park@acme.com", employee_id=None,
        department="IT", job_title="System Administrator", status="active",
        last_login=datetime(2026, 8, 21, 6, 0, 0),
        entitlements={"groups": ["IT-Admins", "Global-Admins"],
                      "location": "Seattle",
                      "created_at": "2019-11-01T00:00:00Z"},
    ),

    # --- User 5: Emma Rodriguez — name/department mismatch ---
    dict(
        account_id="ECC-005", system_type="sap_ecc",
        username="ERODRIGU", display_name="Emma Rodriguez",
        email="emma.rodriguez@acme.com", employee_id="EMP005",
        department="Sales", job_title="Sales Manager", status="active",
        last_login=datetime(2026, 8, 21, 9, 30, 0),
        entitlements={"roles": ["Z_SD_SALES_REP"],
                      "location": "Miami", "manager_id": "EMP013",
                      "created_at": "2020-07-01T00:00:00Z"},
    ),
    dict(
        account_id="SF-005", system_type="successfactors",
        username="erodriguez@acme.com", display_name="Emma Rodriguez-Vega",
        email="emma.rodriguez@acme.com", employee_id="EMP005",
        department="Sales & Marketing", job_title="Sales Manager", status="active",
        last_login=datetime(2026, 8, 20, 11, 0, 0),
        entitlements={"groups": ["Sales_US", "Marketing_US"],
                      "location": "Miami", "manager_id": "EMP013",
                      "created_at": "2020-07-01T00:00:00Z"},
    ),
    dict(
        account_id="AAD-005", system_type="azure_ad",
        username="emma.rodriguez@acme.com", display_name="Emma Rodriguez",
        email="emma.rodriguez@acme.com", employee_id="EMP005",
        department="Sales", job_title="Sales Manager", status="active",
        last_login=datetime(2026, 8, 21, 8, 0, 0),
        entitlements={"groups": ["Sales-Users", "CRM-Access"],
                      "location": "Miami", "manager_id": "EMP013",
                      "created_at": "2020-07-01T00:00:00Z"},
    ),

    # --- User 6: Frank Kim — stale S/4HANA account ---
    dict(
        account_id="ECC-006", system_type="sap_ecc",
        username="FKIM", display_name="Frank Kim",
        email="frank.kim@acme.com", employee_id="EMP006",
        department="Controlling", job_title="Cost Controller", status="active",
        last_login=datetime(2026, 8, 19, 14, 0, 0),
        entitlements={"roles": ["Z_CO_PROFIT_CENTER_MGR"],
                      "location": "Los Angeles", "manager_id": "EMP014",
                      "created_at": "2021-02-01T00:00:00Z"},
    ),
    dict(
        account_id="S4-006", system_type="sap_s4hana",
        username="FKIM", display_name="Frank Kim",
        email="frank.kim@acme.com", employee_id="EMP006",
        department="Controlling", job_title="Cost Controller", status="active",
        last_login=datetime(2025, 11, 1, 0, 0, 0),  # Stale — 9+ months ago
        entitlements={"roles": ["BR_CO_CONTROLLER"],
                      "location": "Los Angeles", "manager_id": "EMP014",
                      "created_at": "2023-03-01T00:00:00Z"},
    ),
    dict(
        account_id="SF-006", system_type="successfactors",
        username="fkim@acme.com", display_name="Frank Kim",
        email="frank.kim@acme.com", employee_id="EMP006",
        department="Controlling", job_title="Cost Controller", status="active",
        last_login=datetime(2026, 8, 15, 10, 0, 0),
        entitlements={"groups": ["Finance_US", "Controlling_US"],
                      "location": "Los Angeles", "manager_id": "EMP014",
                      "created_at": "2021-02-01T00:00:00Z"},
    ),
    dict(
        account_id="AAD-006", system_type="azure_ad",
        username="frank.kim@acme.com", display_name="Frank Kim",
        email="frank.kim@acme.com", employee_id="EMP006",
        department="Controlling", job_title="Cost Controller", status="active",
        last_login=datetime(2026, 8, 20, 8, 0, 0),
        entitlements={"groups": ["Finance-Users"],
                      "location": "Los Angeles", "manager_id": "EMP014",
                      "created_at": "2021-02-01T00:00:00Z"},
    ),

    # --- User 7: Grace Lee — duplicate SAP account ---
    dict(
        account_id="ECC-007A", system_type="sap_ecc",
        username="GLEE", display_name="Grace Lee",
        email="grace.lee@acme.com", employee_id="EMP007",
        department="Finance", job_title="AP Accountant", status="active",
        last_login=datetime(2026, 8, 21, 10, 0, 0),
        entitlements={"roles": ["Z_FI_AP_ACCOUNTANT"],
                      "location": "Boston", "manager_id": "EMP015",
                      "created_at": "2022-01-01T00:00:00Z"},
    ),
    dict(
        account_id="ECC-007B", system_type="sap_ecc",  # Duplicate in same system
        username="GRACE.LEE", display_name="Grace Lee",
        email="grace.lee@acme.com", employee_id="EMP007",
        department="Finance", job_title="AP Accountant", status="active",
        last_login=datetime(2026, 7, 1, 0, 0, 0),
        entitlements={"roles": ["Z_FI_AP_ACCOUNTANT", "Z_FI_GL_ACCOUNTANT"],
                      "location": "Boston", "manager_id": "EMP015",
                      "created_at": "2023-06-01T00:00:00Z"},
    ),
    dict(
        account_id="SF-007", system_type="successfactors",
        username="glee@acme.com", display_name="Grace Lee",
        email="grace.lee@acme.com", employee_id="EMP007",
        department="Finance", job_title="AP Accountant", status="active",
        last_login=datetime(2026, 8, 20, 9, 0, 0),
        entitlements={"groups": ["Finance_US"],
                      "location": "Boston", "manager_id": "EMP015",
                      "created_at": "2022-01-01T00:00:00Z"},
    ),
    dict(
        account_id="AAD-007", system_type="azure_ad",
        username="grace.lee@acme.com", display_name="Grace Lee",
        email="grace.lee@acme.com", employee_id="EMP007",
        department="Finance", job_title="AP Accountant", status="active",
        last_login=datetime(2026, 8, 21, 7, 0, 0),
        entitlements={"groups": ["Finance-Users", "AP-Approvers"],
                      "location": "Boston", "manager_id": "EMP015",
                      "created_at": "2022-01-01T00:00:00Z"},
    ),

    # --- User 8: Service account orphan ---
    dict(
        account_id="S4-SVC-001", system_type="sap_s4hana",
        username="SVC_INTEGRATION", display_name="Integration Service Account",
        email=None, employee_id=None,
        department=None, job_title="Service Account", status="active",
        last_login=datetime(2026, 8, 21, 0, 1, 0),
        entitlements={"roles": ["BR_INTEGRATION_RFC"],
                      "created_at": "2023-01-01T00:00:00Z"},
    ),

    # --- User 9: Henry Brown — fully matched, low risk ---
    dict(
        account_id="ECC-009", system_type="sap_ecc",
        username="HBROWN", display_name="Henry Brown",
        email="henry.brown@acme.com", employee_id="EMP009",
        department="IT", job_title="Basis Administrator", status="active",
        last_login=datetime(2026, 8, 21, 9, 0, 0),
        entitlements={"roles": ["Z_BASIS_USER_ADMIN"],
                      "location": "Austin", "manager_id": "EMP016",
                      "created_at": "2022-05-01T00:00:00Z"},
    ),
    dict(
        account_id="S4-009", system_type="sap_s4hana",
        username="HBROWN", display_name="Henry Brown",
        email="henry.brown@acme.com", employee_id="EMP009",
        department="IT", job_title="Basis Administrator", status="active",
        last_login=datetime(2026, 8, 21, 9, 0, 0),
        entitlements={"roles": ["BR_BASIS_ADMIN"],
                      "location": "Austin", "manager_id": "EMP016",
                      "created_at": "2023-01-01T00:00:00Z"},
    ),
    dict(
        account_id="SF-009", system_type="successfactors",
        username="hbrown@acme.com", display_name="Henry Brown",
        email="henry.brown@acme.com", employee_id="EMP009",
        department="IT", job_title="Basis Administrator", status="active",
        last_login=datetime(2026, 8, 20, 15, 0, 0),
        entitlements={"groups": ["IT_US"],
                      "location": "Austin", "manager_id": "EMP016",
                      "created_at": "2022-05-01T00:00:00Z"},
    ),
    dict(
        account_id="AAD-009", system_type="azure_ad",
        username="henry.brown@acme.com", display_name="Henry Brown",
        email="henry.brown@acme.com", employee_id="EMP009",
        department="IT", job_title="Basis Administrator", status="active",
        last_login=datetime(2026, 8, 21, 8, 30, 0),
        entitlements={"groups": ["IT-Admins"],
                      "location": "Austin", "manager_id": "EMP016",
                      "created_at": "2022-05-01T00:00:00Z"},
    ),
]

# ---------------------------------------------------------------------------
# Seed cluster definitions
# Each entry contains all fields needed to build an IdentityClusterRecord row
# plus a "links" list used to reconstruct CorrelationLink objects at query time
# (links are stored inside IdentityClusterRecord.anomalies-adjacent JSON but
# kept separate here for seeding clarity).
# ---------------------------------------------------------------------------

_SEED_CLUSTERS = [
    dict(
        cluster_id="CLU-001", canonical_name="Alice Johnson",
        canonical_email="alice.johnson@acme.com", employee_id="EMP001",
        department="Finance", account_ids=["ECC-001", "S4-001", "SF-001", "AAD-001"],
        correlation_confidence=95.0, risk_level="low", anomalies=[],
        links=[
            dict(a="ECC-001", b="SF-001", method="employee_id", confidence=98.0,
                 evidence=["employee_id=EMP001 matches in both systems"]),
            dict(a="SF-001", b="AAD-001", method="email", confidence=95.0,
                 evidence=["email=alice.johnson@acme.com matches exactly"]),
            dict(a="AAD-001", b="S4-001", method="employee_id", confidence=98.0,
                 evidence=["employee_id=EMP001 matches in both systems"]),
        ],
    ),
    dict(
        cluster_id="CLU-002", canonical_name="Bob Chen",
        canonical_email="bob.chen@acme.com", employee_id="EMP002",
        department="Procurement", account_ids=["ECC-002", "S4-002", "SF-002", "AAD-002"],
        correlation_confidence=92.0, risk_level="critical",
        anomalies=[
            "CROSS_SYSTEM_SOD: Creates purchase orders in SAP ECC (Z_MM_PURCHASER) "
            "AND is member of PO-Approvers group in Azure AD — payment SoD violation."
        ],
        links=[
            dict(a="ECC-002", b="SF-002", method="employee_id", confidence=98.0,
                 evidence=["employee_id=EMP002 matches in both systems"]),
            dict(a="SF-002", b="AAD-002", method="email", confidence=95.0,
                 evidence=["email=bob.chen@acme.com matches exactly"]),
            dict(a="AAD-002", b="S4-002", method="email", confidence=92.0,
                 evidence=["email matches; username differs (BCHEN vs B.CHEN — known pattern)"]),
        ],
    ),
    dict(
        cluster_id="CLU-003", canonical_name="Carol White",
        canonical_email="carol.white@acme.com", employee_id="EMP003",
        department="HR", account_ids=["ECC-003", "SF-003"],
        correlation_confidence=97.0, risk_level="critical",
        anomalies=[
            "GHOST_ACCOUNT: Account ECC-003 (CWHITE) is ACTIVE in SAP ECC but "
            "employee EMP003 is TERMINATED in SuccessFactors. Payroll admin role "
            "Z_HR_PAYROLL_ADMIN must be revoked immediately."
        ],
        links=[
            dict(a="ECC-003", b="SF-003", method="employee_id", confidence=97.0,
                 evidence=["employee_id=EMP003 matches in both systems"]),
        ],
    ),
    dict(
        cluster_id="CLU-004", canonical_name="David Park",
        canonical_email="david.park@acme.com", employee_id=None,
        department="IT", account_ids=["ECC-004", "AAD-004"],
        correlation_confidence=72.0, risk_level="high",
        anomalies=[
            "ORPHAN_ACCOUNT: No SuccessFactors or S/4HANA record found. "
            "Cannot confirm employment status. Z_DEVELOPER and Global-Admins "
            "group represent significant privilege without HR verification.",
            "EXCESSIVE_ACCOUNTS: Global-Admins in Azure AD combined with "
            "Z_BASIS_USER_ADMIN and Z_DEVELOPER in SAP creates excessive "
            "administrative access.",
        ],
        links=[
            dict(a="ECC-004", b="AAD-004", method="full_name_fuzzy", confidence=72.0,
                 evidence=[
                     "Display name 'David Park' matches with 100% string similarity",
                     "Both in IT department and Seattle location",
                     "No employee_id — confidence capped at 72%",
                 ]),
        ],
    ),
    dict(
        cluster_id="CLU-005", canonical_name="Emma Rodriguez",
        canonical_email="emma.rodriguez@acme.com", employee_id="EMP005",
        department="Sales", account_ids=["ECC-005", "SF-005", "AAD-005"],
        correlation_confidence=95.0, risk_level="medium",
        anomalies=[
            "NAME_MISMATCH: SAP ECC has 'Emma Rodriguez' but SuccessFactors has "
            "'Emma Rodriguez-Vega'. Possible legal name change not propagated.",
            "DEPARTMENT_MISMATCH: SAP shows 'Sales' but SuccessFactors shows "
            "'Sales & Marketing'. Department assignment may need alignment.",
        ],
        links=[
            dict(a="ECC-005", b="SF-005", method="employee_id", confidence=97.0,
                 evidence=["employee_id=EMP005 matches"]),
            dict(a="SF-005", b="AAD-005", method="email", confidence=95.0,
                 evidence=["email matches exactly"]),
        ],
    ),
    dict(
        cluster_id="CLU-006", canonical_name="Frank Kim",
        canonical_email="frank.kim@acme.com", employee_id="EMP006",
        department="Controlling", account_ids=["ECC-006", "S4-006", "SF-006", "AAD-006"],
        correlation_confidence=95.0, risk_level="medium",
        anomalies=[
            "STALE_ACCOUNT: S/4HANA account S4-006 (FKIM) last logged in "
            "2025-11-01 — over 9 months ago. Active in all other systems. "
            "S/4HANA role BR_CO_CONTROLLER should be reviewed or revoked."
        ],
        links=[
            dict(a="ECC-006", b="SF-006", method="employee_id", confidence=98.0,
                 evidence=["employee_id=EMP006"]),
            dict(a="SF-006", b="AAD-006", method="email", confidence=95.0,
                 evidence=["email matches"]),
            dict(a="AAD-006", b="S4-006", method="employee_id", confidence=98.0,
                 evidence=["employee_id=EMP006"]),
        ],
    ),
    dict(
        cluster_id="CLU-007", canonical_name="Grace Lee",
        canonical_email="grace.lee@acme.com", employee_id="EMP007",
        department="Finance", account_ids=["ECC-007A", "ECC-007B", "SF-007", "AAD-007"],
        correlation_confidence=95.0, risk_level="high",
        anomalies=[
            "DUPLICATE_ACCOUNT: Two active SAP ECC accounts found for EMP007: "
            "GLEE (ECC-007A) and GRACE.LEE (ECC-007B). The secondary account "
            "has additional GL accountant role which may grant excessive access.",
        ],
        links=[
            dict(a="ECC-007A", b="SF-007", method="employee_id", confidence=98.0,
                 evidence=["employee_id=EMP007"]),
            dict(a="SF-007", b="AAD-007", method="email", confidence=95.0,
                 evidence=["email matches"]),
            dict(a="ECC-007A", b="ECC-007B", method="employee_id", confidence=99.0,
                 evidence=[
                     "Same employee_id EMP007 in two SAP ECC accounts",
                     "DUPLICATE ACCOUNT DETECTED in same system",
                 ]),
        ],
    ),
    dict(
        cluster_id="CLU-008", canonical_name="Integration Service Account",
        canonical_email=None, employee_id=None,
        department=None, account_ids=["S4-SVC-001"],
        correlation_confidence=0.0, risk_level="medium",
        anomalies=[
            "ORPHAN_ACCOUNT: Service account SVC_INTEGRATION exists only in "
            "S/4HANA with no corresponding record in any other system. "
            "Verify ownership and confirm this is an authorized service account."
        ],
        links=[],
    ),
    dict(
        cluster_id="CLU-009", canonical_name="Henry Brown",
        canonical_email="henry.brown@acme.com", employee_id="EMP009",
        department="IT", account_ids=["ECC-009", "S4-009", "SF-009", "AAD-009"],
        correlation_confidence=95.0, risk_level="low", anomalies=[],
        links=[
            dict(a="ECC-009", b="SF-009", method="employee_id", confidence=98.0,
                 evidence=["employee_id=EMP009"]),
            dict(a="SF-009", b="AAD-009", method="email", confidence=95.0,
                 evidence=["email matches"]),
            dict(a="AAD-009", b="S4-009", method="employee_id", confidence=98.0,
                 evidence=["employee_id=EMP009"]),
        ],
    ),
]

# ---------------------------------------------------------------------------
# Static cross-system risks (not persisted; derived from cluster data)
# ---------------------------------------------------------------------------

_CROSS_SYSTEM_RISKS: List[CrossSystemRisk] = [
    CrossSystemRisk(
        cluster_id="CLU-002",
        canonical_name="Bob Chen",
        risk_id="XSOD-001",
        risk_name="Purchase Order Create + Approve (Cross-System)",
        risk_level=RiskLevel.CRITICAL,
        contributing_accounts=[
            {"system": "sap_ecc", "username": "BCHEN",
             "access": "Z_MM_PURCHASER — can create purchase orders (ME21N)"},
            {"system": "azure_ad", "username": "bob.chen@acme.com",
             "access": "PO-Approvers group — can approve purchase orders in workflow"},
        ],
        description=(
            "User Bob Chen has purchase order creation capability in SAP ECC via "
            "role Z_MM_PURCHASER and purchase order approval capability in Azure AD "
            "via the PO-Approvers group (connected to the SAP workflow approval app). "
            "This combined access violates the Procure-to-Pay SoD rule: "
            "PO_CREATE + PO_APPROVE must be separated."
        ),
        sod_rule="SOD-MM-001: Purchase Order Create vs Approve",
        remediation=(
            "Remove Bob Chen from the PO-Approvers group in Azure AD, "
            "OR remove the Z_MM_PURCHASER role in SAP ECC. "
            "If both functions are required, implement a mitigating control: "
            "mandatory manager counter-approval and spend limit restrictions."
        ),
    ),
    CrossSystemRisk(
        cluster_id="CLU-001",
        canonical_name="Alice Johnson",
        risk_id="XSOD-002",
        risk_name="AP Posting + AP Payment Approval (Cross-System)",
        risk_level=RiskLevel.HIGH,
        contributing_accounts=[
            {"system": "sap_ecc", "username": "AJOHNSON",
             "access": "Z_FI_AP_ACCOUNTANT — can post AP invoices"},
            {"system": "azure_ad", "username": "alice.johnson@acme.com",
             "access": "AP-Approvers group — can approve payment runs"},
        ],
        description=(
            "Alice Johnson can post accounts payable invoices in SAP ECC and "
            "approve payment runs via the AP-Approvers Azure AD group (connected "
            "to the payment approval Fiori workflow). Combined, this allows "
            "creating a fictitious invoice and approving its payment."
        ),
        sod_rule="SOD-FI-002: AP Invoice Post vs Payment Approve",
        remediation=(
            "Remove Alice from AP-Approvers in Azure AD if she should only post. "
            "Consider adding a second approver requirement for payments above "
            "threshold as a compensating control."
        ),
    ),
    CrossSystemRisk(
        cluster_id="CLU-004",
        canonical_name="David Park",
        risk_id="XSOD-003",
        risk_name="SAP Basis Admin + Azure Global Admin (Segregation of Privilege)",
        risk_level=RiskLevel.CRITICAL,
        contributing_accounts=[
            {"system": "sap_ecc", "username": "DPARK",
             "access": "Z_BASIS_USER_ADMIN + Z_DEVELOPER — full SAP admin and development"},
            {"system": "azure_ad", "username": "david.park@acme.com",
             "access": "Global-Admins — full Azure AD administrative rights"},
        ],
        description=(
            "David Park holds unrestricted administrative access in both SAP (Basis "
            "administrator and developer roles) and Azure AD (Global Administrator). "
            "No single administrator should have this level of combined privilege. "
            "Additionally, no HR record exists to verify employment status."
        ),
        sod_rule="PRIV-001: SAP Admin vs Azure Global Admin combination",
        remediation=(
            "Verify David Park's employment status with HR immediately. "
            "If authorized, require dual approval for all administrative actions. "
            "Split SAP Basis and Development roles between separate accounts. "
            "Remove Global Admin from Azure AD — assign only required delegated roles."
        ),
    ),
    CrossSystemRisk(
        cluster_id="CLU-007",
        canonical_name="Grace Lee",
        risk_id="XSOD-004",
        risk_name="Duplicate SAP Account with Escalated Access",
        risk_level=RiskLevel.HIGH,
        contributing_accounts=[
            {"system": "sap_ecc", "username": "GLEE",
             "access": "Z_FI_AP_ACCOUNTANT"},
            {"system": "sap_ecc", "username": "GRACE.LEE",
             "access": "Z_FI_AP_ACCOUNTANT + Z_FI_GL_ACCOUNTANT"},
            {"system": "azure_ad", "username": "grace.lee@acme.com",
             "access": "AP-Approvers — can approve payments"},
        ],
        description=(
            "Grace Lee has two active SAP ECC accounts. The secondary account "
            "GRACE.LEE has additional GL accountant role access. Combined with "
            "AP-Approvers in Azure AD, this creates AP+GL posting and payment "
            "approval access — a critical financial SoD violation."
        ),
        sod_rule="SOD-FI-001: AP Post + GL Post + Payment Approve",
        remediation=(
            "Lock and investigate the secondary account GRACE.LEE immediately. "
            "Determine how it was created and whether it was authorized. "
            "Remove AP-Approvers from Azure AD pending investigation."
        ),
    ),
]


# ===========================================================================
# DB ↔ domain-object converters
# ===========================================================================

def _db_account_to_domain(row: IdentityAccount) -> SystemAccount:
    """Convert a DB IdentityAccount row to a SystemAccount dataclass."""
    try:
        system = SystemType(row.system_type)
    except ValueError:
        system = SystemType.SAP_ECC

    try:
        status = AccountStatus(row.status)
    except ValueError:
        status = AccountStatus.ACTIVE

    entitlements = row.entitlements or {}
    roles = entitlements.get("roles", [])
    groups = entitlements.get("groups", [])
    location = entitlements.get("location")
    manager_id = entitlements.get("manager_id")
    created_at = entitlements.get("created_at")

    last_login_str: Optional[str] = None
    if row.last_login is not None:
        last_login_str = row.last_login.isoformat() + "Z"

    return SystemAccount(
        account_id=row.account_id,
        system=system,
        username=row.username,
        display_name=row.display_name or row.username,
        email=row.email,
        employee_id=row.employee_id,
        department=row.department,
        location=location,
        manager_id=manager_id,
        job_title=row.job_title,
        status=status,
        last_login=last_login_str,
        roles=roles,
        groups=groups,
        created_at=created_at,
    )


def _db_cluster_to_domain(
    row: IdentityClusterRecord,
    account_index: Dict[str, SystemAccount],
) -> IdentityCluster:
    """Convert a DB IdentityClusterRecord row to an IdentityCluster dataclass."""
    try:
        risk = RiskLevel(row.risk_level)
    except ValueError:
        risk = RiskLevel.LOW

    account_ids: List[str] = row.account_ids or []
    accounts = [account_index[aid] for aid in account_ids if aid in account_index]

    # Reconstruct CorrelationLink objects from the stored link metadata inside
    # anomalies-adjacent JSON.  Clusters seeded from _SEED_CLUSTERS carry their
    # links inside a special "__links__" key of the anomalies list (see seeding
    # logic below).  Manually-merged clusters store links the same way.
    raw_anomalies: list = row.anomalies or []
    links: List[CorrelationLink] = []
    text_anomalies: List[str] = []

    for item in raw_anomalies:
        if isinstance(item, dict) and item.get("__type__") == "link":
            a_id = item["a"]
            b_id = item["b"]
            a_acc = account_index.get(a_id)
            b_acc = account_index.get(b_id)
            if a_acc and b_acc:
                try:
                    method = CorrelationMethod(item.get("method", "unmatched"))
                except ValueError:
                    method = CorrelationMethod.UNMATCHED
                links.append(CorrelationLink(
                    account_a_id=a_id,
                    account_b_id=b_id,
                    system_a=a_acc.system,
                    system_b=b_acc.system,
                    method=method,
                    confidence=float(item.get("confidence", 0.0)),
                    evidence=item.get("evidence", []),
                    created_at=item.get("created_at", datetime.utcnow().isoformat() + "Z"),
                    created_by=item.get("created_by", "engine"),
                ))
        elif isinstance(item, str):
            text_anomalies.append(item)

    last_correlated: str = (
        row.last_correlated.isoformat() + "Z"
        if row.last_correlated
        else datetime.utcnow().isoformat() + "Z"
    )

    return IdentityCluster(
        cluster_id=row.cluster_id,
        canonical_name=row.canonical_name,
        canonical_email=row.canonical_email,
        employee_id=row.employee_id,
        department=row.department,
        location=None,  # not stored in IdentityClusterRecord schema
        job_title=None,  # not stored in IdentityClusterRecord schema
        accounts=accounts,
        correlation_links=links,
        overall_confidence=float(row.correlation_confidence),
        risk_level=risk,
        anomalies=text_anomalies,
        last_correlated=last_correlated,
    )


def _build_seed_anomalies_json(seed: dict) -> list:
    """
    Combine text anomaly strings + link dicts into the JSON list stored in
    IdentityClusterRecord.anomalies.

    Text anomalies are stored as plain strings.
    Links are stored as dicts with "__type__": "link".
    """
    result: list = list(seed.get("anomalies", []))
    now = datetime.utcnow().isoformat() + "Z"
    for lnk in seed.get("links", []):
        result.append({
            "__type__": "link",
            "a": lnk["a"],
            "b": lnk["b"],
            "method": lnk["method"],
            "confidence": lnk["confidence"],
            "evidence": lnk["evidence"],
            "created_at": now,
            "created_by": "engine",
        })
    return result


# ===========================================================================
# DB seeding / lazy-load guard
# ===========================================================================

def _ensure_loaded(tenant_id: str) -> None:
    """
    If the identity_accounts and identity_clusters tables are empty for this
    tenant, insert the hardcoded seed data.  This is called at the start of
    every public engine method so data is always available without a separate
    migration or seed script.
    """
    with db_manager.session_scope() as session:
        existing = (
            session.query(IdentityAccount)
            .filter(IdentityAccount.tenant_id == tenant_id)
            .first()
        )
        if existing is not None:
            return  # Already seeded — nothing to do

        # Insert accounts
        for seed in _SEED_ACCOUNTS:
            session.add(IdentityAccount(
                tenant_id=tenant_id,
                account_id=seed["account_id"],
                username=seed["username"],
                display_name=seed.get("display_name"),
                email=seed.get("email"),
                employee_id=seed.get("employee_id"),
                system_type=seed["system_type"],
                status=seed.get("status", "active"),
                department=seed.get("department"),
                job_title=seed.get("job_title"),
                last_login=seed.get("last_login"),
                entitlements=seed.get("entitlements"),
            ))

        # Insert clusters
        for seed in _SEED_CLUSTERS:
            session.add(IdentityClusterRecord(
                tenant_id=tenant_id,
                cluster_id=seed["cluster_id"],
                canonical_name=seed["canonical_name"],
                canonical_email=seed.get("canonical_email"),
                employee_id=seed.get("employee_id"),
                department=seed.get("department"),
                account_ids=seed["account_ids"],
                correlation_confidence=seed["correlation_confidence"],
                risk_level=seed["risk_level"],
                anomalies=_build_seed_anomalies_json(seed),
                last_correlated=datetime.utcnow(),
            ))


# ===========================================================================
# Helpers to load domain objects from DB
# ===========================================================================

def _load_accounts(tenant_id: str) -> Dict[str, SystemAccount]:
    """Return all accounts for the tenant keyed by account_id."""
    with db_manager.session_scope() as session:
        rows = (
            session.query(IdentityAccount)
            .filter(IdentityAccount.tenant_id == tenant_id)
            .all()
        )
        return {row.account_id: _db_account_to_domain(row) for row in rows}


def _load_clusters(
    tenant_id: str,
    account_index: Dict[str, SystemAccount],
) -> Dict[str, IdentityCluster]:
    """Return all clusters for the tenant keyed by cluster_id."""
    with db_manager.session_scope() as session:
        rows = (
            session.query(IdentityClusterRecord)
            .filter(IdentityClusterRecord.tenant_id == tenant_id)
            .all()
        )
        return {
            row.cluster_id: _db_cluster_to_domain(row, account_index)
            for row in rows
        }


def _save_cluster(tenant_id: str, cluster: IdentityCluster) -> None:
    """Upsert a single IdentityCluster back into the DB."""
    # Re-encode anomalies + links into the mixed JSON list
    mixed: list = [a for a in cluster.anomalies]  # text strings first
    for lnk in cluster.correlation_links:
        mixed.append({
            "__type__": "link",
            "a": lnk.account_a_id,
            "b": lnk.account_b_id,
            "method": lnk.method.value,
            "confidence": lnk.confidence,
            "evidence": lnk.evidence,
            "created_at": lnk.created_at,
            "created_by": lnk.created_by,
        })

    with db_manager.session_scope() as session:
        existing = (
            session.query(IdentityClusterRecord)
            .filter(
                IdentityClusterRecord.tenant_id == tenant_id,
                IdentityClusterRecord.cluster_id == cluster.cluster_id,
            )
            .first()
        )
        if existing:
            existing.canonical_name = cluster.canonical_name
            existing.canonical_email = cluster.canonical_email
            existing.employee_id = cluster.employee_id
            existing.department = cluster.department
            existing.account_ids = [a.account_id for a in cluster.accounts]
            existing.correlation_confidence = cluster.overall_confidence
            existing.risk_level = cluster.risk_level.value
            existing.anomalies = mixed
            existing.last_correlated = datetime.utcnow()
        else:
            session.add(IdentityClusterRecord(
                tenant_id=tenant_id,
                cluster_id=cluster.cluster_id,
                canonical_name=cluster.canonical_name,
                canonical_email=cluster.canonical_email,
                employee_id=cluster.employee_id,
                department=cluster.department,
                account_ids=[a.account_id for a in cluster.accounts],
                correlation_confidence=cluster.overall_confidence,
                risk_level=cluster.risk_level.value,
                anomalies=mixed,
                last_correlated=datetime.utcnow(),
            ))


def _delete_cluster(tenant_id: str, cluster_id: str) -> None:
    """Delete a cluster row from the DB."""
    with db_manager.session_scope() as session:
        row = (
            session.query(IdentityClusterRecord)
            .filter(
                IdentityClusterRecord.tenant_id == tenant_id,
                IdentityClusterRecord.cluster_id == cluster_id,
            )
            .first()
        )
        if row:
            session.delete(row)


# ===========================================================================
# Correlation engine
# ===========================================================================

class IdentityCorrelationEngine:
    """
    Correlates identities across SAP ECC, S/4HANA, SuccessFactors, and Azure AD.

    All data is read from and written to the database via db_manager.
    On the first call for any tenant the hardcoded seed data is inserted
    automatically (_ensure_loaded pattern).

    Confidence scoring model:
    - Employee ID match:          98 points
    - Email exact match:          95 points
    - Full name + dept match:     80 points
    - Full name fuzzy match:      65-75 points
    - Manager + dept match:       60 points
    - Department + location only: 40 points
    """

    def _load_data(self, tenant_id: str):
        """
        Return (account_index, cluster_index) for the given tenant.

        Calls _ensure_loaded first so seed data is present on first use.
        """
        _ensure_loaded(tenant_id)
        account_index = _load_accounts(tenant_id)
        cluster_index = _load_clusters(tenant_id, account_index)
        return account_index, cluster_index

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_overview(self) -> CorrelationStats:
        """Return high-level identity correlation statistics."""
        tenant_id = _get_tenant_id()
        account_index, cluster_index = self._load_data(tenant_id)

        accounts = list(account_index.values())
        clusters = list(cluster_index.values())

        by_system: Dict[str, int] = {s.value: 0 for s in SystemType}
        for acc in accounts:
            by_system[acc.system.value] += 1

        fully_correlated = sum(
            1 for c in clusters
            if len({a.system for a in c.accounts}) == 4
        )
        partially_correlated = sum(
            1 for c in clusters
            if 1 < len({a.system for a in c.accounts}) < 4
        )
        orphan_count = len(self._find_orphans_from(clusters))
        anomaly_count = sum(len(c.anomalies) for c in clusters)
        non_zero_clusters = [c for c in clusters if c.overall_confidence > 0]
        average_confidence = (
            round(sum(c.overall_confidence for c in non_zero_clusters) / len(non_zero_clusters), 1)
            if non_zero_clusters else 0.0
        )

        return CorrelationStats(
            total_accounts=len(accounts),
            total_clusters=len(clusters),
            fully_correlated=fully_correlated,
            partially_correlated=partially_correlated,
            orphan_accounts=orphan_count,
            anomaly_count=anomaly_count,
            cross_system_risks=len(_CROSS_SYSTEM_RISKS),
            average_confidence=average_confidence,
            by_system=by_system,
            last_run=datetime.utcnow().isoformat() + "Z",
        )

    def correlate_all(self) -> List[IdentityCluster]:
        """Return all identity clusters from the database."""
        tenant_id = _get_tenant_id()
        _, cluster_index = self._load_data(tenant_id)
        return list(cluster_index.values())

    def get_cluster(self, cluster_id: str) -> IdentityCluster:
        """Return a specific cluster by ID. Raises ValueError if not found."""
        tenant_id = _get_tenant_id()
        _, cluster_index = self._load_data(tenant_id)
        cluster = cluster_index.get(cluster_id)
        if not cluster:
            raise ValueError(f"Unknown cluster: {cluster_id}")
        return cluster

    def correlate_user(self, user_id: str, system: str) -> CorrelationResult:
        """
        Find the cluster for a specific account and report how it correlates
        to accounts in other systems.

        user_id is the account_id (e.g. "ECC-001") or username (e.g. "AJOHNSON").
        system is the SystemType value string (e.g. "sap_ecc").
        """
        tenant_id = _get_tenant_id()
        account_index, cluster_index = self._load_data(tenant_id)

        # Try account_id first, then username match
        source: Optional[SystemAccount] = account_index.get(user_id)
        if not source:
            try:
                sys_type = SystemType(system)
            except ValueError:
                raise ValueError(
                    f"Unknown system: {system}. Valid values: "
                    f"{[s.value for s in SystemType]}"
                )
            for acc in account_index.values():
                if acc.system == sys_type and acc.username == user_id:
                    source = acc
                    break

        if not source:
            raise ValueError(f"Account not found: {user_id} in system {system}")

        # Find which cluster contains this account
        cluster: Optional[IdentityCluster] = None
        for c in cluster_index.values():
            if any(a.account_id == source.account_id for a in c.accounts):
                cluster = c
                break

        if not cluster:
            return CorrelationResult(
                source_account=source,
                matched_accounts=[],
                correlation_links=[],
                cluster_id=None,
                overall_confidence=0.0,
                unmatched_systems=list(SystemType),
                summary=f"Account {source.account_id} is not correlated to any cluster.",
            )

        matched = [a for a in cluster.accounts if a.account_id != source.account_id]
        matched_systems = {a.system for a in matched}
        unmatched = [s for s in SystemType if s not in matched_systems and s != source.system]
        relevant_links = [
            lnk for lnk in cluster.correlation_links
            if lnk.account_a_id == source.account_id
            or lnk.account_b_id == source.account_id
        ]

        return CorrelationResult(
            source_account=source,
            matched_accounts=matched,
            correlation_links=relevant_links,
            cluster_id=cluster.cluster_id,
            overall_confidence=cluster.overall_confidence,
            unmatched_systems=unmatched,
            summary=(
                f"Account {source.account_id} is correlated to {len(matched)} account(s) "
                f"across {len(matched_systems)} system(s) "
                f"(confidence: {cluster.overall_confidence}%)."
            ),
        )

    def find_orphans(self) -> List[OrphanAccount]:
        """
        Return accounts that have no correlation to any other system.

        An account is an orphan if:
        - It belongs to a cluster of size 1 (no cross-system matches), OR
        - Its cluster has zero correlation links
        """
        tenant_id = _get_tenant_id()
        _, cluster_index = self._load_data(tenant_id)
        return self._find_orphans_from(list(cluster_index.values()))

    def _find_orphans_from(self, clusters: List[IdentityCluster]) -> List[OrphanAccount]:
        """Internal helper: compute orphans from an already-loaded cluster list."""
        orphans: List[OrphanAccount] = []
        for cluster in clusters:
            if len(cluster.accounts) == 1 or not cluster.correlation_links:
                acc = cluster.accounts[0]
                days = None
                if acc.last_login:
                    try:
                        login_dt = datetime.fromisoformat(acc.last_login.rstrip("Z"))
                        days = (datetime.utcnow() - login_dt).days
                    except (ValueError, TypeError):
                        days = None

                risk = (
                    RiskLevel.HIGH
                    if acc.status == AccountStatus.ACTIVE and acc.roles
                    else RiskLevel.MEDIUM
                )

                orphans.append(OrphanAccount(
                    account=acc,
                    reason=(
                        "No matching account found in any other system. "
                        "Cannot confirm employment or authorization status."
                    ),
                    risk_level=risk,
                    last_login=acc.last_login,
                    days_since_login=days,
                    recommended_action=(
                        "Verify with HR whether this is an active employee or authorized "
                        "service account. If no business justification exists, lock the account."
                    ),
                ))
        return orphans

    def get_cross_system_risk(self, cluster_id: str) -> List[CrossSystemRisk]:
        """Return cross-system SoD risks for a specific cluster."""
        tenant_id = _get_tenant_id()
        _, cluster_index = self._load_data(tenant_id)
        if cluster_id not in cluster_index:
            raise ValueError(f"Unknown cluster: {cluster_id}")
        return [r for r in _CROSS_SYSTEM_RISKS if r.cluster_id == cluster_id]

    def get_all_cross_system_risks(self) -> List[CrossSystemRisk]:
        """Return all detected cross-system SoD risks."""
        return list(_CROSS_SYSTEM_RISKS)

    def detect_anomalies(self) -> List[IdentityAnomaly]:
        """
        Detect identity anomalies across all clusters.

        Returns structured anomaly objects for each anomaly found in the dataset.
        """
        tenant_id = _get_tenant_id()
        _, cluster_index = self._load_data(tenant_id)

        anomalies: List[IdentityAnomaly] = []
        now = datetime.utcnow().isoformat() + "Z"

        for cluster in cluster_index.values():
            for anomaly_text in cluster.anomalies:
                atype = AnomalyType.ORPHAN_ACCOUNT
                action = "Review and remediate per cluster risk level."

                if "GHOST_ACCOUNT" in anomaly_text:
                    atype = AnomalyType.GHOST_ACCOUNT
                    action = (
                        "Lock the ghost account in the active system immediately. "
                        "Initiate a leaver process review for the terminated employee."
                    )
                elif "ORPHAN_ACCOUNT" in anomaly_text:
                    atype = AnomalyType.ORPHAN_ACCOUNT
                    action = "Verify employment status with HR. Lock if unverified."
                elif "NAME_MISMATCH" in anomaly_text:
                    atype = AnomalyType.NAME_MISMATCH
                    action = (
                        "Align display name across all systems to the legal name "
                        "in the HR system of record (SuccessFactors)."
                    )
                elif "DEPARTMENT_MISMATCH" in anomaly_text:
                    atype = AnomalyType.DEPARTMENT_MISMATCH
                    action = (
                        "Align department assignment across all systems to the "
                        "authoritative HR record."
                    )
                elif "DUPLICATE_ACCOUNT" in anomaly_text:
                    atype = AnomalyType.DUPLICATE_ACCOUNT
                    action = (
                        "Lock duplicate account and investigate how it was created. "
                        "Consolidate access onto the primary account."
                    )
                elif "EXCESSIVE_ACCOUNTS" in anomaly_text:
                    atype = AnomalyType.EXCESSIVE_ACCOUNTS
                    action = (
                        "Review all role and group assignments across systems. "
                        "Apply principle of least privilege."
                    )
                elif "STALE_ACCOUNT" in anomaly_text:
                    atype = AnomalyType.STALE_ACCOUNT
                    action = (
                        "Disable the stale account after confirming with the user "
                        "and their manager. Remove associated roles."
                    )
                elif "CROSS_SYSTEM_SOD" in anomaly_text:
                    atype = AnomalyType.CROSS_SYSTEM_SOD
                    action = (
                        "Remediate per cross-system risk details. "
                        "Segregate conflicting access across the two systems."
                    )

                anomalies.append(IdentityAnomaly(
                    anomaly_id=f"ANOM-{cluster.cluster_id}-{len(anomalies)+1:03d}",
                    anomaly_type=atype,
                    cluster_id=cluster.cluster_id,
                    affected_accounts=[
                        {"account_id": a.account_id, "system": a.system.value,
                         "username": a.username}
                        for a in cluster.accounts
                    ],
                    description=anomaly_text,
                    risk_level=cluster.risk_level,
                    detected_at=now,
                    recommended_action=action,
                    evidence=[anomaly_text],
                ))

        return anomalies

    def merge_clusters(
        self, cluster_id_a: str, cluster_id_b: str, merged_by: str = "admin"
    ) -> IdentityCluster:
        """
        Manually merge two clusters into one.

        This is used when the engine has not automatically correlated two accounts
        that a security administrator knows belong to the same person (e.g. a
        contractor with a different last name in one system).

        The resulting cluster takes the cluster_id and canonical attributes from
        cluster_a.  The merge is persisted to the database: cluster_a's row is
        updated and cluster_b's row is deleted.
        """
        tenant_id = _get_tenant_id()
        _, cluster_index = self._load_data(tenant_id)

        cluster_a = cluster_index.get(cluster_id_a)
        cluster_b = cluster_index.get(cluster_id_b)

        if not cluster_a:
            raise ValueError(f"Cluster not found: {cluster_id_a}")
        if not cluster_b:
            raise ValueError(f"Cluster not found: {cluster_id_b}")
        if cluster_id_a == cluster_id_b:
            raise ValueError("Cannot merge a cluster with itself.")

        # Build a manual correlation link between the first accounts of each cluster
        manual_link = CorrelationLink(
            account_a_id=cluster_a.accounts[0].account_id,
            account_b_id=cluster_b.accounts[0].account_id,
            system_a=cluster_a.accounts[0].system,
            system_b=cluster_b.accounts[0].system,
            method=CorrelationMethod.MANUAL,
            confidence=100.0,
            evidence=[f"Manually merged by {merged_by}"],
            created_at=datetime.utcnow().isoformat() + "Z",
            created_by=merged_by,
        )

        merged_accounts = cluster_a.accounts + cluster_b.accounts
        merged_links = cluster_a.correlation_links + cluster_b.correlation_links + [manual_link]
        merged_anomalies = cluster_a.anomalies + cluster_b.anomalies

        # Worst-case risk
        risk_order = [RiskLevel.INFO, RiskLevel.LOW, RiskLevel.MEDIUM,
                      RiskLevel.HIGH, RiskLevel.CRITICAL]
        merged_risk = max(cluster_a.risk_level, cluster_b.risk_level,
                          key=lambda r: risk_order.index(r))

        merged_cluster = IdentityCluster(
            cluster_id=cluster_id_a,
            canonical_name=cluster_a.canonical_name,
            canonical_email=cluster_a.canonical_email or cluster_b.canonical_email,
            employee_id=cluster_a.employee_id or cluster_b.employee_id,
            department=cluster_a.department or cluster_b.department,
            location=cluster_a.location or cluster_b.location,
            job_title=cluster_a.job_title or cluster_b.job_title,
            accounts=merged_accounts,
            correlation_links=merged_links,
            overall_confidence=min(
                cluster_a.overall_confidence,
                cluster_b.overall_confidence,
            ),
            risk_level=merged_risk,
            anomalies=merged_anomalies,
            last_correlated=datetime.utcnow().isoformat() + "Z",
        )

        # Persist: update cluster_a row, delete cluster_b row
        _save_cluster(tenant_id, merged_cluster)
        _delete_cluster(tenant_id, cluster_id_b)

        return merged_cluster
