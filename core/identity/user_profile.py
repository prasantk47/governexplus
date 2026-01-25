"""
Unified User Profile Service

Aggregates user data from multiple sources (HR, Identity Provider, SAP, GRC)
to provide a complete user profile for access requests, certifications, and audits.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
import uuid


class UserSource(Enum):
    """Data source types for user information"""
    HR_SYSTEM = "hr_system"           # SAP HCM, Workday, SuccessFactors
    IDENTITY_PROVIDER = "idp"         # Azure AD, Okta, LDAP
    SAP_SYSTEM = "sap"                # SAP User Master
    ACTIVE_DIRECTORY = "ad"           # On-prem AD
    GRC_PLATFORM = "grc"              # Internal GRC data
    MANUAL = "manual"                 # Manual entry


class UserStatus(Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    PENDING = "pending"
    TERMINATED = "terminated"
    ON_LEAVE = "on_leave"


class EmploymentType(Enum):
    """Employment type"""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACTOR = "contractor"
    VENDOR = "vendor"
    INTERN = "intern"
    TEMPORARY = "temporary"


@dataclass
class ManagerInfo:
    """Manager information"""
    user_id: str
    employee_id: Optional[str] = None
    name: str = ""
    email: str = ""
    title: str = ""
    department: str = ""

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "name": self.name,
            "email": self.email,
            "title": self.title,
            "department": self.department
        }


@dataclass
class OrganizationInfo:
    """Organizational placement information"""
    company_code: str = ""
    company_name: str = ""
    cost_center: str = ""
    cost_center_name: str = ""
    department: str = ""
    department_name: str = ""
    org_unit: str = ""
    org_unit_name: str = ""
    location: str = ""
    location_name: str = ""
    country: str = ""
    region: str = ""
    business_unit: str = ""
    division: str = ""

    def to_dict(self) -> Dict:
        return {
            "company_code": self.company_code,
            "company_name": self.company_name,
            "cost_center": self.cost_center,
            "cost_center_name": self.cost_center_name,
            "department": self.department,
            "department_name": self.department_name,
            "org_unit": self.org_unit,
            "org_unit_name": self.org_unit_name,
            "location": self.location,
            "location_name": self.location_name,
            "country": self.country,
            "region": self.region,
            "business_unit": self.business_unit,
            "division": self.division
        }


@dataclass
class RiskProfile:
    """User risk profile from GRC analysis"""
    overall_risk_level: str = "low"  # low, medium, high, critical
    risk_score: float = 0.0
    sod_violation_count: int = 0
    sensitive_access_count: int = 0
    high_risk_roles: List[str] = field(default_factory=list)
    active_mitigations: int = 0
    last_certification_date: Optional[datetime] = None
    certification_status: str = "not_certified"
    firefighter_usage_count: int = 0
    policy_violations: int = 0
    anomaly_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "overall_risk_level": self.overall_risk_level,
            "risk_score": self.risk_score,
            "sod_violation_count": self.sod_violation_count,
            "sensitive_access_count": self.sensitive_access_count,
            "high_risk_roles": self.high_risk_roles,
            "active_mitigations": self.active_mitigations,
            "last_certification_date": self.last_certification_date.isoformat() if self.last_certification_date else None,
            "certification_status": self.certification_status,
            "firefighter_usage_count": self.firefighter_usage_count,
            "policy_violations": self.policy_violations,
            "anomaly_score": self.anomaly_score
        }


@dataclass
class AccessSummary:
    """Summary of user's current access"""
    total_roles: int = 0
    total_profiles: int = 0
    total_transactions: int = 0
    systems: List[str] = field(default_factory=list)
    role_list: List[Dict] = field(default_factory=list)
    profile_list: List[Dict] = field(default_factory=list)
    sensitive_transactions: List[str] = field(default_factory=list)
    privileged_access: bool = False
    firefighter_eligible: bool = False

    def to_dict(self) -> Dict:
        return {
            "total_roles": self.total_roles,
            "total_profiles": self.total_profiles,
            "total_transactions": self.total_transactions,
            "systems": self.systems,
            "role_list": self.role_list,
            "profile_list": self.profile_list,
            "sensitive_transactions": self.sensitive_transactions,
            "privileged_access": self.privileged_access,
            "firefighter_eligible": self.firefighter_eligible
        }


@dataclass
class UnifiedUserProfile:
    """
    Unified user profile aggregating data from all sources.
    This is the canonical user representation for GRC operations.
    """
    # Primary identifiers
    user_id: str                          # SAP/System user ID
    employee_id: Optional[str] = None     # HR employee number
    ad_account: Optional[str] = None      # Active Directory sAMAccountName
    upn: Optional[str] = None             # User Principal Name (email-like)
    object_id: Optional[str] = None       # Azure AD Object ID

    # Personal information
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    display_name: str = ""
    email: str = ""
    phone: str = ""
    mobile: str = ""

    # Job information
    job_title: str = ""
    job_code: str = ""
    job_family: str = ""
    job_level: str = ""
    employment_type: EmploymentType = EmploymentType.FULL_TIME

    # Organization
    organization: OrganizationInfo = field(default_factory=OrganizationInfo)

    # Manager
    manager: Optional[ManagerInfo] = None
    secondary_manager: Optional[ManagerInfo] = None  # Matrix reporting

    # Dates
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    last_promotion_date: Optional[date] = None
    position_start_date: Optional[date] = None

    # Account status
    status: UserStatus = UserStatus.ACTIVE
    is_locked: bool = False
    lock_reason: str = ""

    # SAP-specific
    sap_user_type: str = ""               # Dialog, System, Service, etc.
    sap_valid_from: Optional[date] = None
    sap_valid_to: Optional[date] = None
    sap_last_login: Optional[datetime] = None
    sap_password_status: str = ""
    sap_license_type: str = ""

    # Access summary
    access_summary: AccessSummary = field(default_factory=AccessSummary)

    # Risk profile
    risk_profile: RiskProfile = field(default_factory=RiskProfile)

    # Compliance
    requires_sod_review: bool = False
    requires_certification: bool = False
    last_access_review: Optional[datetime] = None
    compliance_flags: List[str] = field(default_factory=list)

    # Source tracking
    data_sources: List[UserSource] = field(default_factory=list)
    source_timestamps: Dict[str, datetime] = field(default_factory=dict)
    last_sync: Optional[datetime] = None

    # Request history
    pending_requests: int = 0
    total_requests: int = 0
    last_request_date: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            # Identifiers
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "ad_account": self.ad_account,
            "upn": self.upn,
            "object_id": self.object_id,

            # Personal
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "email": self.email,
            "phone": self.phone,
            "mobile": self.mobile,

            # Job
            "job_title": self.job_title,
            "job_code": self.job_code,
            "job_family": self.job_family,
            "job_level": self.job_level,
            "employment_type": self.employment_type.value,

            # Organization
            "organization": self.organization.to_dict(),

            # Manager
            "manager": self.manager.to_dict() if self.manager else None,
            "secondary_manager": self.secondary_manager.to_dict() if self.secondary_manager else None,

            # Dates
            "hire_date": self.hire_date.isoformat() if self.hire_date else None,
            "termination_date": self.termination_date.isoformat() if self.termination_date else None,
            "last_promotion_date": self.last_promotion_date.isoformat() if self.last_promotion_date else None,
            "position_start_date": self.position_start_date.isoformat() if self.position_start_date else None,

            # Status
            "status": self.status.value,
            "is_locked": self.is_locked,
            "lock_reason": self.lock_reason,

            # SAP
            "sap_user_type": self.sap_user_type,
            "sap_valid_from": self.sap_valid_from.isoformat() if self.sap_valid_from else None,
            "sap_valid_to": self.sap_valid_to.isoformat() if self.sap_valid_to else None,
            "sap_last_login": self.sap_last_login.isoformat() if self.sap_last_login else None,
            "sap_password_status": self.sap_password_status,
            "sap_license_type": self.sap_license_type,

            # Access & Risk
            "access_summary": self.access_summary.to_dict(),
            "risk_profile": self.risk_profile.to_dict(),

            # Compliance
            "requires_sod_review": self.requires_sod_review,
            "requires_certification": self.requires_certification,
            "last_access_review": self.last_access_review.isoformat() if self.last_access_review else None,
            "compliance_flags": self.compliance_flags,

            # Source tracking
            "data_sources": [s.value for s in self.data_sources],
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,

            # Request history
            "pending_requests": self.pending_requests,
            "total_requests": self.total_requests,
            "last_request_date": self.last_request_date.isoformat() if self.last_request_date else None,

            # Metadata
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def to_summary(self) -> Dict:
        """Return a brief summary for lists and dropdowns"""
        return {
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "full_name": self.full_name,
            "email": self.email,
            "job_title": self.job_title,
            "department": self.organization.department,
            "status": self.status.value,
            "risk_level": self.risk_profile.overall_risk_level
        }

    def to_request_context(self) -> Dict:
        """Return user context needed for access requests"""
        return {
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "email": self.email,
            "job_title": self.job_title,
            "employment_type": self.employment_type.value,
            "organization": {
                "company_code": self.organization.company_code,
                "cost_center": self.organization.cost_center,
                "department": self.organization.department,
                "location": self.organization.location,
                "country": self.organization.country
            },
            "manager": self.manager.to_dict() if self.manager else None,
            "status": self.status.value,
            "hire_date": self.hire_date.isoformat() if self.hire_date else None,
            "risk_profile": {
                "risk_level": self.risk_profile.overall_risk_level,
                "risk_score": self.risk_profile.risk_score,
                "sod_violations": self.risk_profile.sod_violation_count,
                "certification_status": self.risk_profile.certification_status
            },
            "current_access": {
                "total_roles": self.access_summary.total_roles,
                "systems": self.access_summary.systems,
                "privileged": self.access_summary.privileged_access
            }
        }


class UserProfileService:
    """
    Service for managing unified user profiles.
    Aggregates data from multiple sources and provides caching.
    """

    def __init__(self):
        self.profiles: Dict[str, UnifiedUserProfile] = {}
        self.employee_index: Dict[str, str] = {}  # employee_id -> user_id
        self.email_index: Dict[str, str] = {}     # email -> user_id
        self._init_demo_data()

    def _init_demo_data(self):
        """Initialize with demo user profiles"""
        demo_profiles = [
            UnifiedUserProfile(
                user_id="JSMITH",
                employee_id="EMP001",
                ad_account="john.smith",
                upn="john.smith@company.com",
                first_name="John",
                last_name="Smith",
                full_name="John Smith",
                display_name="John Smith",
                email="john.smith@company.com",
                phone="+1-555-0101",
                job_title="Senior Financial Analyst",
                job_code="FIN-003",
                job_family="Finance",
                job_level="Senior",
                employment_type=EmploymentType.FULL_TIME,
                organization=OrganizationInfo(
                    company_code="1000",
                    company_name="ACME Corporation",
                    cost_center="CC1001",
                    cost_center_name="Finance Operations",
                    department="FIN",
                    department_name="Finance",
                    org_unit="FIN-001",
                    org_unit_name="Accounts Payable",
                    location="NYC",
                    location_name="New York Office",
                    country="US",
                    region="North America",
                    business_unit="Corporate",
                    division="Finance & Accounting"
                ),
                manager=ManagerInfo(
                    user_id="RJOHNSON",
                    employee_id="EMP010",
                    name="Robert Johnson",
                    email="robert.johnson@company.com",
                    title="Finance Director",
                    department="Finance"
                ),
                hire_date=date(2019, 3, 15),
                position_start_date=date(2022, 1, 1),
                status=UserStatus.ACTIVE,
                sap_user_type="Dialog",
                sap_last_login=datetime(2024, 1, 15, 9, 30),
                sap_license_type="Professional",
                access_summary=AccessSummary(
                    total_roles=5,
                    total_profiles=0,
                    total_transactions=45,
                    systems=["SAP_ECC", "SAP_S4"],
                    role_list=[
                        {"role_name": "Z_FI_AP_CLERK", "description": "AP Clerk"},
                        {"role_name": "Z_FI_VENDOR_MAINT", "description": "Vendor Maintenance"},
                        {"role_name": "Z_MM_PO_CREATE", "description": "PO Creation"},
                        {"role_name": "Z_FI_PAYMENT", "description": "Payment Processing"},
                        {"role_name": "Z_REPORTING_FIN", "description": "Financial Reports"}
                    ],
                    sensitive_transactions=["F110", "FK01", "ME21N"],
                    privileged_access=False,
                    firefighter_eligible=True
                ),
                risk_profile=RiskProfile(
                    overall_risk_level="high",
                    risk_score=75.0,
                    sod_violation_count=2,
                    sensitive_access_count=5,
                    high_risk_roles=["Z_FI_PAYMENT"],
                    active_mitigations=1,
                    last_certification_date=datetime(2023, 12, 1),
                    certification_status="certified",
                    firefighter_usage_count=3,
                    policy_violations=0,
                    anomaly_score=0.2
                ),
                requires_sod_review=True,
                requires_certification=False,
                data_sources=[UserSource.HR_SYSTEM, UserSource.SAP_SYSTEM, UserSource.GRC_PLATFORM],
                last_sync=datetime.now(),
                pending_requests=0,
                total_requests=8
            ),
            UnifiedUserProfile(
                user_id="MBROWN",
                employee_id="EMP002",
                ad_account="mary.brown",
                upn="mary.brown@company.com",
                first_name="Mary",
                last_name="Brown",
                full_name="Mary Brown",
                display_name="Mary Brown",
                email="mary.brown@company.com",
                phone="+1-555-0102",
                job_title="Procurement Specialist",
                job_code="PROC-002",
                job_family="Procurement",
                job_level="Mid",
                employment_type=EmploymentType.FULL_TIME,
                organization=OrganizationInfo(
                    company_code="1000",
                    company_name="ACME Corporation",
                    cost_center="CC2001",
                    cost_center_name="Procurement",
                    department="PROC",
                    department_name="Procurement",
                    org_unit="PROC-001",
                    org_unit_name="Strategic Sourcing",
                    location="CHI",
                    location_name="Chicago Office",
                    country="US",
                    region="North America",
                    business_unit="Operations",
                    division="Supply Chain"
                ),
                manager=ManagerInfo(
                    user_id="SWILLIAMS",
                    employee_id="EMP011",
                    name="Sarah Williams",
                    email="sarah.williams@company.com",
                    title="Procurement Manager",
                    department="Procurement"
                ),
                hire_date=date(2020, 6, 1),
                position_start_date=date(2020, 6, 1),
                status=UserStatus.ACTIVE,
                sap_user_type="Dialog",
                sap_last_login=datetime(2024, 1, 15, 8, 45),
                sap_license_type="Professional",
                access_summary=AccessSummary(
                    total_roles=3,
                    total_profiles=0,
                    total_transactions=30,
                    systems=["SAP_ECC"],
                    role_list=[
                        {"role_name": "Z_MM_PURCHASER", "description": "Purchaser"},
                        {"role_name": "Z_MM_PO_CREATE", "description": "PO Creation"},
                        {"role_name": "Z_MM_GR_POST", "description": "Goods Receipt"}
                    ],
                    sensitive_transactions=["ME21N", "ME22N", "MIGO"],
                    privileged_access=False,
                    firefighter_eligible=False
                ),
                risk_profile=RiskProfile(
                    overall_risk_level="medium",
                    risk_score=45.0,
                    sod_violation_count=1,
                    sensitive_access_count=3,
                    high_risk_roles=[],
                    active_mitigations=0,
                    last_certification_date=datetime(2023, 11, 15),
                    certification_status="certified",
                    firefighter_usage_count=0,
                    policy_violations=0,
                    anomaly_score=0.1
                ),
                requires_sod_review=True,
                requires_certification=False,
                data_sources=[UserSource.HR_SYSTEM, UserSource.SAP_SYSTEM, UserSource.GRC_PLATFORM],
                last_sync=datetime.now(),
                pending_requests=1,
                total_requests=5
            ),
            UnifiedUserProfile(
                user_id="TDAVIS",
                employee_id="EMP003",
                ad_account="tom.davis",
                upn="tom.davis@company.com",
                first_name="Tom",
                last_name="Davis",
                full_name="Tom Davis",
                display_name="Tom Davis",
                email="tom.davis@company.com",
                phone="+1-555-0103",
                job_title="SAP Basis Administrator",
                job_code="IT-005",
                job_family="IT",
                job_level="Senior",
                employment_type=EmploymentType.FULL_TIME,
                organization=OrganizationInfo(
                    company_code="1000",
                    company_name="ACME Corporation",
                    cost_center="CC3001",
                    cost_center_name="IT Operations",
                    department="IT",
                    department_name="Information Technology",
                    org_unit="IT-002",
                    org_unit_name="SAP Administration",
                    location="NYC",
                    location_name="New York Office",
                    country="US",
                    region="North America",
                    business_unit="Corporate",
                    division="IT"
                ),
                manager=ManagerInfo(
                    user_id="MTHOMPSON",
                    employee_id="EMP012",
                    name="Michael Thompson",
                    email="michael.thompson@company.com",
                    title="IT Director",
                    department="IT"
                ),
                hire_date=date(2018, 9, 1),
                position_start_date=date(2021, 4, 1),
                status=UserStatus.ACTIVE,
                sap_user_type="Dialog",
                sap_last_login=datetime(2024, 1, 15, 7, 0),
                sap_license_type="Professional",
                access_summary=AccessSummary(
                    total_roles=2,
                    total_profiles=1,
                    total_transactions=500,
                    systems=["SAP_ECC", "SAP_S4", "SAP_BW"],
                    role_list=[
                        {"role_name": "SAP_ALL", "description": "Full Authorization"},
                        {"role_name": "Z_BASIS_ADMIN", "description": "Basis Admin"}
                    ],
                    profile_list=[
                        {"profile_name": "SAP_ALL", "description": "All Authorizations"}
                    ],
                    sensitive_transactions=["SU01", "SM21", "SE16", "SA38"],
                    privileged_access=True,
                    firefighter_eligible=False
                ),
                risk_profile=RiskProfile(
                    overall_risk_level="critical",
                    risk_score=95.0,
                    sod_violation_count=0,
                    sensitive_access_count=50,
                    high_risk_roles=["SAP_ALL"],
                    active_mitigations=2,
                    last_certification_date=datetime(2024, 1, 1),
                    certification_status="certified",
                    firefighter_usage_count=0,
                    policy_violations=0,
                    anomaly_score=0.05
                ),
                requires_sod_review=False,
                requires_certification=True,
                compliance_flags=["SAP_ALL_PROFILE", "PRIVILEGED_ACCESS"],
                data_sources=[UserSource.HR_SYSTEM, UserSource.SAP_SYSTEM, UserSource.GRC_PLATFORM],
                last_sync=datetime.now(),
                pending_requests=0,
                total_requests=2
            ),
            UnifiedUserProfile(
                user_id="AWILSON",
                employee_id="EMP004",
                ad_account="alice.wilson",
                upn="alice.wilson@company.com",
                first_name="Alice",
                last_name="Wilson",
                full_name="Alice Wilson",
                display_name="Alice Wilson",
                email="alice.wilson@company.com",
                phone="+1-555-0104",
                job_title="HR Business Partner",
                job_code="HR-003",
                job_family="Human Resources",
                job_level="Senior",
                employment_type=EmploymentType.FULL_TIME,
                organization=OrganizationInfo(
                    company_code="1000",
                    company_name="ACME Corporation",
                    cost_center="CC4001",
                    cost_center_name="Human Resources",
                    department="HR",
                    department_name="Human Resources",
                    org_unit="HR-001",
                    org_unit_name="HR Operations",
                    location="NYC",
                    location_name="New York Office",
                    country="US",
                    region="North America",
                    business_unit="Corporate",
                    division="Human Resources"
                ),
                manager=ManagerInfo(
                    user_id="LMARTINEZ",
                    employee_id="EMP013",
                    name="Lisa Martinez",
                    email="lisa.martinez@company.com",
                    title="VP Human Resources",
                    department="Human Resources"
                ),
                hire_date=date(2017, 2, 1),
                position_start_date=date(2020, 7, 1),
                status=UserStatus.ACTIVE,
                sap_user_type="Dialog",
                sap_last_login=datetime(2024, 1, 14, 16, 30),
                sap_license_type="Professional",
                access_summary=AccessSummary(
                    total_roles=4,
                    total_profiles=0,
                    total_transactions=60,
                    systems=["SAP_ECC", "SAP_HCM"],
                    role_list=[
                        {"role_name": "Z_HR_PA_MAINT", "description": "Personnel Admin"},
                        {"role_name": "Z_HR_PAYROLL", "description": "Payroll Processing"},
                        {"role_name": "Z_HR_OM_MAINT", "description": "Org Management"},
                        {"role_name": "Z_HR_REPORTING", "description": "HR Reports"}
                    ],
                    sensitive_transactions=["PA30", "PA40", "PC00_M99_CALC"],
                    privileged_access=False,
                    firefighter_eligible=True
                ),
                risk_profile=RiskProfile(
                    overall_risk_level="critical",
                    risk_score=85.0,
                    sod_violation_count=1,
                    sensitive_access_count=15,
                    high_risk_roles=["Z_HR_PAYROLL"],
                    active_mitigations=1,
                    last_certification_date=datetime(2023, 12, 15),
                    certification_status="certified",
                    firefighter_usage_count=1,
                    policy_violations=0,
                    anomaly_score=0.15
                ),
                requires_sod_review=True,
                requires_certification=True,
                compliance_flags=["PII_ACCESS", "PAYROLL_ACCESS"],
                data_sources=[UserSource.HR_SYSTEM, UserSource.SAP_SYSTEM, UserSource.GRC_PLATFORM],
                last_sync=datetime.now(),
                pending_requests=0,
                total_requests=12
            ),
            UnifiedUserProfile(
                user_id="CONTRACTOR01",
                employee_id="CTR001",
                ad_account="ext.contractor1",
                upn="contractor1@vendor.com",
                first_name="External",
                last_name="Contractor",
                full_name="External Contractor",
                display_name="Ext. Contractor (Vendor Corp)",
                email="contractor1@vendor.com",
                phone="+1-555-9999",
                job_title="SAP Consultant",
                job_code="EXT-001",
                job_family="External",
                job_level="Consultant",
                employment_type=EmploymentType.CONTRACTOR,
                organization=OrganizationInfo(
                    company_code="1000",
                    company_name="ACME Corporation",
                    cost_center="CC3001",
                    cost_center_name="IT Operations",
                    department="IT",
                    department_name="Information Technology",
                    org_unit="IT-EXT",
                    org_unit_name="External Resources",
                    location="REMOTE",
                    location_name="Remote",
                    country="US",
                    region="North America",
                    business_unit="Corporate",
                    division="IT"
                ),
                manager=ManagerInfo(
                    user_id="MTHOMPSON",
                    employee_id="EMP012",
                    name="Michael Thompson",
                    email="michael.thompson@company.com",
                    title="IT Director",
                    department="IT"
                ),
                hire_date=date(2024, 1, 1),
                termination_date=date(2024, 6, 30),
                position_start_date=date(2024, 1, 1),
                status=UserStatus.ACTIVE,
                sap_user_type="Dialog",
                sap_valid_from=date(2024, 1, 1),
                sap_valid_to=date(2024, 6, 30),
                sap_last_login=datetime(2024, 1, 15, 10, 0),
                sap_license_type="Limited Professional",
                access_summary=AccessSummary(
                    total_roles=2,
                    total_profiles=0,
                    total_transactions=20,
                    systems=["SAP_ECC"],
                    role_list=[
                        {"role_name": "Z_DEV_DISPLAY", "description": "Development Display"},
                        {"role_name": "Z_CONFIG_CHANGE", "description": "Config Changes"}
                    ],
                    sensitive_transactions=["SE16", "SM30"],
                    privileged_access=False,
                    firefighter_eligible=False
                ),
                risk_profile=RiskProfile(
                    overall_risk_level="high",
                    risk_score=70.0,
                    sod_violation_count=0,
                    sensitive_access_count=2,
                    high_risk_roles=[],
                    active_mitigations=0,
                    last_certification_date=datetime(2024, 1, 5),
                    certification_status="certified",
                    firefighter_usage_count=0,
                    policy_violations=0,
                    anomaly_score=0.3
                ),
                requires_sod_review=False,
                requires_certification=True,
                compliance_flags=["EXTERNAL_USER", "TIME_LIMITED"],
                data_sources=[UserSource.HR_SYSTEM, UserSource.SAP_SYSTEM, UserSource.GRC_PLATFORM],
                last_sync=datetime.now(),
                pending_requests=0,
                total_requests=1
            )
        ]

        for profile in demo_profiles:
            self.profiles[profile.user_id] = profile
            if profile.employee_id:
                self.employee_index[profile.employee_id] = profile.user_id
            if profile.email:
                self.email_index[profile.email.lower()] = profile.user_id

    def get_profile(self, user_id: str) -> Optional[UnifiedUserProfile]:
        """Get user profile by user ID"""
        return self.profiles.get(user_id)

    def get_profile_by_employee_id(self, employee_id: str) -> Optional[UnifiedUserProfile]:
        """Get user profile by employee ID"""
        user_id = self.employee_index.get(employee_id)
        if user_id:
            return self.profiles.get(user_id)
        return None

    def get_profile_by_email(self, email: str) -> Optional[UnifiedUserProfile]:
        """Get user profile by email"""
        user_id = self.email_index.get(email.lower())
        if user_id:
            return self.profiles.get(user_id)
        return None

    def search_profiles(
        self,
        search: Optional[str] = None,
        department: Optional[str] = None,
        status: Optional[UserStatus] = None,
        risk_level: Optional[str] = None,
        employment_type: Optional[EmploymentType] = None,
        has_sod_violations: Optional[bool] = None,
        requires_certification: Optional[bool] = None,
        limit: int = 100
    ) -> List[UnifiedUserProfile]:
        """Search user profiles with filters"""
        results = list(self.profiles.values())

        if search:
            search_lower = search.lower()
            results = [
                p for p in results
                if search_lower in p.user_id.lower()
                or search_lower in p.full_name.lower()
                or search_lower in p.email.lower()
                or (p.employee_id and search_lower in p.employee_id.lower())
            ]

        if department:
            results = [p for p in results if p.organization.department == department]

        if status:
            results = [p for p in results if p.status == status]

        if risk_level:
            results = [p for p in results if p.risk_profile.overall_risk_level == risk_level]

        if employment_type:
            results = [p for p in results if p.employment_type == employment_type]

        if has_sod_violations is not None:
            if has_sod_violations:
                results = [p for p in results if p.risk_profile.sod_violation_count > 0]
            else:
                results = [p for p in results if p.risk_profile.sod_violation_count == 0]

        if requires_certification is not None:
            results = [p for p in results if p.requires_certification == requires_certification]

        return results[:limit]

    def get_manager_direct_reports(self, manager_user_id: str) -> List[UnifiedUserProfile]:
        """Get all direct reports for a manager"""
        return [
            p for p in self.profiles.values()
            if p.manager and p.manager.user_id == manager_user_id
        ]

    def sync_from_hr(self, user_id: str, hr_data: Dict) -> UnifiedUserProfile:
        """Sync user profile with HR system data"""
        profile = self.profiles.get(user_id)
        if not profile:
            profile = UnifiedUserProfile(user_id=user_id)
            self.profiles[user_id] = profile

        # Update HR fields
        profile.employee_id = hr_data.get("employee_id", profile.employee_id)
        profile.first_name = hr_data.get("first_name", profile.first_name)
        profile.last_name = hr_data.get("last_name", profile.last_name)
        profile.full_name = hr_data.get("full_name", f"{profile.first_name} {profile.last_name}")
        profile.email = hr_data.get("email", profile.email)
        profile.job_title = hr_data.get("job_title", profile.job_title)
        profile.job_code = hr_data.get("job_code", profile.job_code)

        if hr_data.get("hire_date"):
            profile.hire_date = hr_data["hire_date"]
        if hr_data.get("termination_date"):
            profile.termination_date = hr_data["termination_date"]

        # Update organization
        if hr_data.get("organization"):
            org = hr_data["organization"]
            profile.organization.company_code = org.get("company_code", profile.organization.company_code)
            profile.organization.cost_center = org.get("cost_center", profile.organization.cost_center)
            profile.organization.department = org.get("department", profile.organization.department)
            profile.organization.location = org.get("location", profile.organization.location)
            profile.organization.country = org.get("country", profile.organization.country)

        # Update manager
        if hr_data.get("manager"):
            mgr = hr_data["manager"]
            profile.manager = ManagerInfo(
                user_id=mgr.get("user_id", ""),
                employee_id=mgr.get("employee_id"),
                name=mgr.get("name", ""),
                email=mgr.get("email", ""),
                title=mgr.get("title", ""),
                department=mgr.get("department", "")
            )

        # Track source
        if UserSource.HR_SYSTEM not in profile.data_sources:
            profile.data_sources.append(UserSource.HR_SYSTEM)
        profile.source_timestamps[UserSource.HR_SYSTEM.value] = datetime.now()
        profile.last_sync = datetime.now()
        profile.updated_at = datetime.now()

        # Update indices
        if profile.employee_id:
            self.employee_index[profile.employee_id] = user_id
        if profile.email:
            self.email_index[profile.email.lower()] = user_id

        return profile

    def sync_from_sap(self, user_id: str, sap_data: Dict) -> UnifiedUserProfile:
        """Sync user profile with SAP system data"""
        profile = self.profiles.get(user_id)
        if not profile:
            profile = UnifiedUserProfile(user_id=user_id)
            self.profiles[user_id] = profile

        # Update SAP fields
        profile.sap_user_type = sap_data.get("user_type", profile.sap_user_type)
        profile.sap_license_type = sap_data.get("license_type", profile.sap_license_type)
        profile.sap_password_status = sap_data.get("password_status", profile.sap_password_status)

        if sap_data.get("valid_from"):
            profile.sap_valid_from = sap_data["valid_from"]
        if sap_data.get("valid_to"):
            profile.sap_valid_to = sap_data["valid_to"]
        if sap_data.get("last_login"):
            profile.sap_last_login = sap_data["last_login"]

        # Update lock status
        profile.is_locked = sap_data.get("lock_status", 0) != 0

        # Update access summary
        if sap_data.get("roles"):
            profile.access_summary.role_list = sap_data["roles"]
            profile.access_summary.total_roles = len(sap_data["roles"])
        if sap_data.get("profiles"):
            profile.access_summary.profile_list = sap_data["profiles"]
            profile.access_summary.total_profiles = len(sap_data["profiles"])

        # Track source
        if UserSource.SAP_SYSTEM not in profile.data_sources:
            profile.data_sources.append(UserSource.SAP_SYSTEM)
        profile.source_timestamps[UserSource.SAP_SYSTEM.value] = datetime.now()
        profile.last_sync = datetime.now()
        profile.updated_at = datetime.now()

        return profile

    def update_risk_profile(self, user_id: str, risk_data: Dict) -> Optional[UnifiedUserProfile]:
        """Update user's risk profile from GRC analysis"""
        profile = self.profiles.get(user_id)
        if not profile:
            return None

        rp = profile.risk_profile
        rp.overall_risk_level = risk_data.get("risk_level", rp.overall_risk_level)
        rp.risk_score = risk_data.get("risk_score", rp.risk_score)
        rp.sod_violation_count = risk_data.get("sod_violations", rp.sod_violation_count)
        rp.sensitive_access_count = risk_data.get("sensitive_access", rp.sensitive_access_count)
        rp.high_risk_roles = risk_data.get("high_risk_roles", rp.high_risk_roles)
        rp.active_mitigations = risk_data.get("mitigations", rp.active_mitigations)
        rp.anomaly_score = risk_data.get("anomaly_score", rp.anomaly_score)

        # Update flags
        profile.requires_sod_review = rp.sod_violation_count > 0
        profile.requires_certification = rp.overall_risk_level in ["high", "critical"]

        # Track source
        if UserSource.GRC_PLATFORM not in profile.data_sources:
            profile.data_sources.append(UserSource.GRC_PLATFORM)
        profile.source_timestamps[UserSource.GRC_PLATFORM.value] = datetime.now()
        profile.updated_at = datetime.now()

        return profile

    def sync_from_ldap(self, user_id: str, ldap_data: Dict) -> UnifiedUserProfile:
        """
        Sync user profile with LDAP/Active Directory data.

        LDAP provides authoritative identity data:
        - Username (sAMAccountName)
        - UPN (userPrincipalName)
        - Email (mail)
        - Name (givenName, sn, displayName)
        - Department, Title, Company
        - Manager (manager DN)
        - Phone, Mobile
        - Account status (userAccountControl)
        - Group memberships (memberOf)
        - Last login (lastLogonTimestamp)
        - Password expiry (pwdLastSet)

        Args:
            user_id: The user ID (typically sAMAccountName or username)
            ldap_data: Dictionary containing LDAP attributes

        Returns:
            Updated UnifiedUserProfile
        """
        profile = self.profiles.get(user_id)
        if not profile:
            profile = UnifiedUserProfile(user_id=user_id)
            self.profiles[user_id] = profile

        # Core identity from LDAP (authoritative)
        profile.ad_account = ldap_data.get("username", ldap_data.get("sAMAccountName", profile.ad_account))
        profile.upn = ldap_data.get("upn", ldap_data.get("userPrincipalName", profile.upn))
        profile.object_id = ldap_data.get("object_guid", ldap_data.get("objectGUID", profile.object_id))

        # Name fields
        profile.first_name = ldap_data.get("first_name", ldap_data.get("givenName", profile.first_name))
        profile.last_name = ldap_data.get("last_name", ldap_data.get("sn", profile.last_name))
        profile.full_name = ldap_data.get("full_name", ldap_data.get("displayName", profile.full_name))
        profile.display_name = ldap_data.get("display_name", ldap_data.get("displayName", profile.display_name))

        # If full_name not set, construct it
        if not profile.full_name and profile.first_name and profile.last_name:
            profile.full_name = f"{profile.first_name} {profile.last_name}"
        if not profile.display_name:
            profile.display_name = profile.full_name

        # Contact info
        profile.email = ldap_data.get("email", ldap_data.get("mail", profile.email))
        profile.phone = ldap_data.get("phone", ldap_data.get("telephoneNumber", profile.phone))
        profile.mobile = ldap_data.get("mobile", ldap_data.get("mobile", profile.mobile))

        # Job info
        profile.job_title = ldap_data.get("title", ldap_data.get("title", profile.job_title))

        # Organization info from LDAP
        profile.organization.department = ldap_data.get("department", profile.organization.department)
        profile.organization.department_name = ldap_data.get("department", profile.organization.department_name)
        profile.organization.company_name = ldap_data.get("company", profile.organization.company_name)
        profile.organization.location = ldap_data.get("office", ldap_data.get("physicalDeliveryOfficeName", profile.organization.location))
        profile.organization.location_name = ldap_data.get("office", profile.organization.location_name)
        profile.organization.country = ldap_data.get("country", ldap_data.get("co", profile.organization.country))
        profile.organization.region = ldap_data.get("state", ldap_data.get("st", profile.organization.region))

        # Employee ID (if stored in AD)
        if ldap_data.get("employee_id") or ldap_data.get("employeeID"):
            profile.employee_id = ldap_data.get("employee_id", ldap_data.get("employeeID"))
        if ldap_data.get("employee_number") or ldap_data.get("employeeNumber"):
            profile.employee_id = ldap_data.get("employee_number", ldap_data.get("employeeNumber", profile.employee_id))

        # Manager info from LDAP
        manager_dn = ldap_data.get("manager_dn", ldap_data.get("manager"))
        if manager_dn:
            manager_username = ldap_data.get("manager_username")
            manager_name = ldap_data.get("manager_name")
            manager_email = ldap_data.get("manager_email")

            # Extract CN from DN if no explicit name
            if not manager_name and manager_dn:
                import re
                match = re.search(r'CN=([^,]+)', manager_dn, re.IGNORECASE)
                if match:
                    manager_name = match.group(1)

            profile.manager = ManagerInfo(
                user_id=manager_username or "",
                employee_id=ldap_data.get("manager_employee_id"),
                name=manager_name or "",
                email=manager_email or "",
                title=ldap_data.get("manager_title", ""),
                department=ldap_data.get("manager_department", "")
            )

        # Account status from userAccountControl (AD specific)
        is_enabled = ldap_data.get("is_enabled", True)
        is_locked = ldap_data.get("is_locked", False)
        is_expired = ldap_data.get("is_expired", False)
        password_expired = ldap_data.get("password_expired", False)

        if not is_enabled or is_expired:
            profile.status = UserStatus.INACTIVE
        elif is_locked:
            profile.status = UserStatus.LOCKED
            profile.is_locked = True
            profile.lock_reason = ldap_data.get("lock_reason", "Account locked in Active Directory")
        else:
            profile.status = UserStatus.ACTIVE
            profile.is_locked = False

        # Password status
        if password_expired:
            profile.sap_password_status = "EXPIRED"
            profile.compliance_flags.append("PASSWORD_EXPIRED") if "PASSWORD_EXPIRED" not in profile.compliance_flags else None

        # Timestamps from LDAP
        if ldap_data.get("last_logon") or ldap_data.get("lastLogonTimestamp"):
            last_logon = ldap_data.get("last_logon") or ldap_data.get("lastLogonTimestamp")
            if isinstance(last_logon, datetime):
                profile.sap_last_login = last_logon  # Reusing SAP field for consistency

        if ldap_data.get("created") or ldap_data.get("whenCreated"):
            created = ldap_data.get("created") or ldap_data.get("whenCreated")
            if isinstance(created, datetime):
                profile.created_at = created

        # Group memberships from LDAP (important for role mapping)
        member_of = ldap_data.get("member_of", ldap_data.get("memberOf", []))
        if member_of:
            # Store raw group DNs for role mapping
            if not hasattr(profile, 'ldap_groups'):
                profile.ldap_groups = []
            profile.ldap_groups = member_of

            # Extract group names for display
            group_names = ldap_data.get("group_names", [])
            if not group_names and member_of:
                import re
                for dn in member_of:
                    match = re.search(r'CN=([^,]+)', dn, re.IGNORECASE)
                    if match:
                        group_names.append(match.group(1))

            # Store for access summary
            if group_names:
                profile.access_summary.systems.extend([
                    g for g in group_names
                    if g not in profile.access_summary.systems
                ])

        # Direct reports from LDAP
        direct_reports = ldap_data.get("direct_reports", ldap_data.get("directReports", []))
        if direct_reports:
            if not hasattr(profile, 'ldap_direct_reports'):
                profile.ldap_direct_reports = []
            profile.ldap_direct_reports = direct_reports

        # Track source
        if UserSource.ACTIVE_DIRECTORY not in profile.data_sources:
            profile.data_sources.append(UserSource.ACTIVE_DIRECTORY)
        if UserSource.IDENTITY_PROVIDER not in profile.data_sources:
            profile.data_sources.append(UserSource.IDENTITY_PROVIDER)
        profile.source_timestamps[UserSource.ACTIVE_DIRECTORY.value] = datetime.now()
        profile.last_sync = datetime.now()
        profile.updated_at = datetime.now()

        # Update indices
        if profile.employee_id:
            self.employee_index[profile.employee_id] = user_id
        if profile.email:
            self.email_index[profile.email.lower()] = user_id
        if profile.ad_account:
            self.email_index[profile.ad_account.lower()] = user_id
        if profile.upn:
            self.email_index[profile.upn.lower()] = user_id

        return profile

    def sync_from_ldap_user(self, ldap_user: "LDAPUser") -> UnifiedUserProfile:
        """
        Sync user profile from LDAPUser object.

        This is the preferred method when using the LDAPConnector directly.

        Args:
            ldap_user: LDAPUser object from LDAPConnector

        Returns:
            Updated UnifiedUserProfile
        """
        # Convert LDAPUser to dict format
        ldap_data = {
            "username": ldap_user.username,
            "sAMAccountName": ldap_user.username,
            "upn": ldap_user.upn,
            "userPrincipalName": ldap_user.upn,
            "object_guid": ldap_user.object_guid,
            "objectGUID": ldap_user.object_guid,
            "first_name": ldap_user.first_name,
            "givenName": ldap_user.first_name,
            "last_name": ldap_user.last_name,
            "sn": ldap_user.last_name,
            "full_name": ldap_user.full_name,
            "displayName": ldap_user.full_name,
            "email": ldap_user.email,
            "mail": ldap_user.email,
            "phone": ldap_user.phone,
            "telephoneNumber": ldap_user.phone,
            "mobile": ldap_user.mobile,
            "title": ldap_user.title,
            "department": ldap_user.department,
            "company": ldap_user.company,
            "office": ldap_user.office,
            "physicalDeliveryOfficeName": ldap_user.office,
            "country": ldap_user.country,
            "state": ldap_user.state,
            "employee_id": ldap_user.employee_id,
            "employeeID": ldap_user.employee_id,
            "manager_dn": ldap_user.manager_dn,
            "manager": ldap_user.manager_dn,
            "is_enabled": ldap_user.is_enabled,
            "is_locked": ldap_user.is_locked,
            "is_expired": ldap_user.is_expired,
            "password_expired": ldap_user.password_expired,
            "last_logon": ldap_user.last_logon,
            "lastLogonTimestamp": ldap_user.last_logon,
            "created": ldap_user.created,
            "whenCreated": ldap_user.created,
            "member_of": ldap_user.member_of,
            "memberOf": ldap_user.member_of,
            "direct_reports": ldap_user.direct_reports,
            "directReports": ldap_user.direct_reports,
            "group_names": ldap_user.get_group_names() if hasattr(ldap_user, 'get_group_names') else [],
            "manager_username": ldap_user.get_manager_username() if hasattr(ldap_user, 'get_manager_username') else None,
        }

        # Use username as user_id
        user_id = ldap_user.username

        return self.sync_from_ldap(user_id, ldap_data)

    def bulk_sync_from_ldap(self, ldap_users: List["LDAPUser"]) -> Dict[str, Any]:
        """
        Bulk sync multiple LDAP users.

        Args:
            ldap_users: List of LDAPUser objects

        Returns:
            Sync statistics
        """
        stats = {
            "total": len(ldap_users),
            "created": 0,
            "updated": 0,
            "errors": [],
        }

        for ldap_user in ldap_users:
            try:
                user_id = ldap_user.username
                is_new = user_id not in self.profiles

                self.sync_from_ldap_user(ldap_user)

                if is_new:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1

            except Exception as e:
                stats["errors"].append({
                    "username": ldap_user.username if ldap_user else "unknown",
                    "error": str(e)
                })

        return stats

    def get_profile_by_ad_account(self, ad_account: str) -> Optional[UnifiedUserProfile]:
        """Get user profile by Active Directory sAMAccountName"""
        # Check direct lookup first
        for profile in self.profiles.values():
            if profile.ad_account and profile.ad_account.lower() == ad_account.lower():
                return profile
        # Fallback to index
        user_id = self.email_index.get(ad_account.lower())
        if user_id:
            return self.profiles.get(user_id)
        return None

    def get_profile_by_upn(self, upn: str) -> Optional[UnifiedUserProfile]:
        """Get user profile by User Principal Name"""
        for profile in self.profiles.values():
            if profile.upn and profile.upn.lower() == upn.lower():
                return profile
        user_id = self.email_index.get(upn.lower())
        if user_id:
            return self.profiles.get(user_id)
        return None

    def get_statistics(self) -> Dict:
        """Get user profile statistics"""
        profiles = list(self.profiles.values())

        return {
            "total_users": len(profiles),
            "by_status": {
                status.value: len([p for p in profiles if p.status == status])
                for status in UserStatus
            },
            "by_employment_type": {
                et.value: len([p for p in profiles if p.employment_type == et])
                for et in EmploymentType
            },
            "by_risk_level": {
                level: len([p for p in profiles if p.risk_profile.overall_risk_level == level])
                for level in ["low", "medium", "high", "critical"]
            },
            "by_source": {
                source.value: len([p for p in profiles if source in p.data_sources])
                for source in UserSource
            },
            "users_with_sod_violations": len([p for p in profiles if p.risk_profile.sod_violation_count > 0]),
            "users_requiring_certification": len([p for p in profiles if p.requires_certification]),
            "privileged_users": len([p for p in profiles if p.access_summary.privileged_access]),
            "external_users": len([p for p in profiles if p.employment_type in [EmploymentType.CONTRACTOR, EmploymentType.VENDOR]]),
            "synced_from_ldap": len([p for p in profiles if UserSource.ACTIVE_DIRECTORY in p.data_sources]),
        }
