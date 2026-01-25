"""
Identity Risk Scoring System

Provides per-identity risk assessment because auditors audit IDENTITIES, not just access.

Key Capabilities:
- Identity risk score per user
- Dormant/ghost identity detection
- Cross-system identity correlation
- Identity hygiene dashboard
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics
import hashlib


class IdentityStatus(Enum):
    """Identity lifecycle status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DORMANT = "dormant"       # No activity for extended period
    GHOST = "ghost"           # Should not exist (orphaned)
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class IdentityRiskLevel(Enum):
    """Overall identity risk level"""
    MINIMAL = "minimal"       # 0-20
    LOW = "low"               # 21-40
    MODERATE = "moderate"     # 41-60
    HIGH = "high"             # 61-80
    CRITICAL = "critical"     # 81-100


class IdentityAnomaly(Enum):
    """Types of identity anomalies"""
    ORPHANED = "orphaned"                   # No manager/owner
    DORMANT = "dormant"                     # No recent activity
    GHOST = "ghost"                         # Terminated but active
    PRIVILEGE_CREEP = "privilege_creep"     # Accumulated excess access
    IMPOSSIBLE_TRAVEL = "impossible_travel" # Login from impossible locations
    MULTI_SYSTEM_INCONSISTENT = "multi_system_inconsistent"
    UNAUTHORIZED_ELEVATION = "unauthorized_elevation"
    SHARED_ACCOUNT = "shared_account"
    SERVICE_ACCOUNT_MISUSE = "service_account_misuse"


@dataclass
class SystemAccess:
    """Access details for a specific system"""
    system_id: str
    system_name: str
    account_id: str
    account_type: str  # human, service, shared, emergency
    status: str
    roles: List[str]
    entitlements: List[str]
    last_login: Optional[datetime]
    last_activity: Optional[datetime]
    login_count_30d: int = 0
    failed_login_count_30d: int = 0
    privilege_level: str = "standard"  # standard, elevated, admin, super


@dataclass
class IdentityProfile:
    """Comprehensive identity profile across all systems"""
    identity_id: str
    employee_id: Optional[str]
    email: str
    full_name: str
    department: str
    job_title: str
    manager_id: Optional[str]
    manager_name: Optional[str]

    # HR status
    hr_status: str  # active, leave, terminated
    hire_date: Optional[datetime] = None
    termination_date: Optional[datetime] = None
    last_position_change: Optional[datetime] = None

    # Identity status
    identity_status: IdentityStatus = IdentityStatus.ACTIVE
    status_reason: str = ""

    # Cross-system access
    system_access: Dict[str, SystemAccess] = field(default_factory=dict)

    # Risk scores
    overall_risk_score: float = 0.0
    risk_level: IdentityRiskLevel = IdentityRiskLevel.LOW

    # Component scores (0-100)
    access_risk_score: float = 0.0      # Based on what they can do
    behavior_risk_score: float = 0.0    # Based on what they've done
    hygiene_risk_score: float = 0.0     # Account health issues
    anomaly_risk_score: float = 0.0     # Detected anomalies

    # Anomalies
    anomalies: List[Dict] = field(default_factory=list)
    anomaly_count: int = 0

    # Risk factors
    risk_factors: List[str] = field(default_factory=list)
    risk_mitigations: List[str] = field(default_factory=list)

    # Peer comparison
    peer_group: str = ""
    above_peer_average: bool = False
    percentile_in_peer_group: float = 50.0

    # Activity summary
    total_systems: int = 0
    total_roles: int = 0
    total_entitlements: int = 0
    days_since_last_activity: int = 0
    days_since_access_review: int = 0

    # Computed at
    last_assessment: Optional[datetime] = None


@dataclass
class IdentityHygieneIssue:
    """An identity hygiene issue"""
    issue_id: str
    identity_id: str
    issue_type: str
    severity: str  # low, medium, high, critical
    description: str
    detected_at: datetime
    remediation_action: str
    auto_remediable: bool = False


class IdentityRiskEngine:
    """
    Engine for calculating and managing identity risk.

    Auditors audit identities - this gives them what they need.
    """

    def __init__(self):
        self.identity_profiles: Dict[str, IdentityProfile] = {}
        self.hygiene_issues: List[IdentityHygieneIssue] = []
        self.peer_groups: Dict[str, List[str]] = {}  # group_name -> identity_ids

    def create_identity_profile(
        self,
        identity_id: str,
        employee_id: Optional[str],
        email: str,
        full_name: str,
        department: str,
        job_title: str,
        manager_id: Optional[str] = None,
        manager_name: Optional[str] = None,
        hr_status: str = "active",
        hire_date: Optional[datetime] = None
    ) -> IdentityProfile:
        """Create or update an identity profile"""

        profile = IdentityProfile(
            identity_id=identity_id,
            employee_id=employee_id,
            email=email,
            full_name=full_name,
            department=department,
            job_title=job_title,
            manager_id=manager_id,
            manager_name=manager_name,
            hr_status=hr_status,
            hire_date=hire_date
        )

        # Assign to peer group
        profile.peer_group = f"{department}_{job_title}".lower().replace(" ", "_")

        self.identity_profiles[identity_id] = profile

        # Index in peer group
        if profile.peer_group not in self.peer_groups:
            self.peer_groups[profile.peer_group] = []
        if identity_id not in self.peer_groups[profile.peer_group]:
            self.peer_groups[profile.peer_group].append(identity_id)

        return profile

    def add_system_access(
        self,
        identity_id: str,
        system_id: str,
        system_name: str,
        account_id: str,
        account_type: str,
        status: str,
        roles: List[str],
        entitlements: List[str],
        last_login: Optional[datetime] = None,
        last_activity: Optional[datetime] = None,
        login_count_30d: int = 0,
        failed_login_count_30d: int = 0,
        privilege_level: str = "standard"
    ):
        """Add or update system access for an identity"""

        if identity_id not in self.identity_profiles:
            raise ValueError(f"Identity not found: {identity_id}")

        profile = self.identity_profiles[identity_id]

        access = SystemAccess(
            system_id=system_id,
            system_name=system_name,
            account_id=account_id,
            account_type=account_type,
            status=status,
            roles=roles,
            entitlements=entitlements,
            last_login=last_login,
            last_activity=last_activity,
            login_count_30d=login_count_30d,
            failed_login_count_30d=failed_login_count_30d,
            privilege_level=privilege_level
        )

        profile.system_access[system_id] = access

    def calculate_identity_risk(self, identity_id: str) -> IdentityProfile:
        """Calculate comprehensive risk score for an identity"""

        if identity_id not in self.identity_profiles:
            raise ValueError(f"Identity not found: {identity_id}")

        profile = self.identity_profiles[identity_id]

        # Reset
        profile.risk_factors = []
        profile.anomalies = []

        # Calculate component scores
        profile.access_risk_score = self._calculate_access_risk(profile)
        profile.behavior_risk_score = self._calculate_behavior_risk(profile)
        profile.hygiene_risk_score = self._calculate_hygiene_risk(profile)
        profile.anomaly_risk_score = self._calculate_anomaly_risk(profile)

        # Weighted overall score
        profile.overall_risk_score = (
            profile.access_risk_score * 0.35 +
            profile.behavior_risk_score * 0.25 +
            profile.hygiene_risk_score * 0.20 +
            profile.anomaly_risk_score * 0.20
        )

        # Determine risk level
        profile.risk_level = self._get_risk_level(profile.overall_risk_score)

        # Update summary stats
        profile.total_systems = len(profile.system_access)
        profile.total_roles = sum(len(a.roles) for a in profile.system_access.values())
        profile.total_entitlements = sum(len(a.entitlements) for a in profile.system_access.values())

        # Days since activity
        last_activity = None
        for access in profile.system_access.values():
            if access.last_activity:
                if not last_activity or access.last_activity > last_activity:
                    last_activity = access.last_activity

        if last_activity:
            profile.days_since_last_activity = (datetime.utcnow() - last_activity).days

        # Compare to peers
        self._compare_to_peers(profile)

        # Timestamp
        profile.last_assessment = datetime.utcnow()
        profile.anomaly_count = len(profile.anomalies)

        return profile

    def _calculate_access_risk(self, profile: IdentityProfile) -> float:
        """Calculate risk based on access permissions"""

        score = 0.0

        for access in profile.system_access.values():
            # Privilege level contribution
            if access.privilege_level == "super":
                score += 30
                profile.risk_factors.append(f"Super user access in {access.system_name}")
            elif access.privilege_level == "admin":
                score += 20
                profile.risk_factors.append(f"Admin access in {access.system_name}")
            elif access.privilege_level == "elevated":
                score += 10

            # Number of roles
            role_count = len(access.roles)
            if role_count > 10:
                score += 15
                profile.risk_factors.append(f"High role count ({role_count}) in {access.system_name}")
            elif role_count > 5:
                score += 8

            # Entitlement count
            ent_count = len(access.entitlements)
            if ent_count > 50:
                score += 15
                profile.risk_factors.append(f"Excessive entitlements ({ent_count}) in {access.system_name}")
            elif ent_count > 25:
                score += 8

        # Cross-system access amplification
        if profile.total_systems > 5:
            score += 10
            profile.risk_factors.append(f"Access across {profile.total_systems} systems")

        return min(score, 100)

    def _calculate_behavior_risk(self, profile: IdentityProfile) -> float:
        """Calculate risk based on behavior patterns"""

        score = 0.0

        for access in profile.system_access.values():
            # Failed logins
            if access.failed_login_count_30d > 10:
                score += 20
                profile.risk_factors.append(f"High failed logins ({access.failed_login_count_30d}) in {access.system_name}")
            elif access.failed_login_count_30d > 5:
                score += 10

            # Low activity with high privilege
            if access.privilege_level in ["admin", "super"] and access.login_count_30d < 3:
                score += 15
                profile.risk_factors.append(f"Privileged access with low usage in {access.system_name}")

        return min(score, 100)

    def _calculate_hygiene_risk(self, profile: IdentityProfile) -> float:
        """Calculate risk based on identity hygiene"""

        score = 0.0

        # No manager
        if not profile.manager_id:
            score += 25
            profile.risk_factors.append("No manager assigned (orphaned identity)")
            self._add_hygiene_issue(profile, "orphaned", "high",
                "Identity has no manager assigned",
                "Assign a manager or owner to this identity")

        # HR terminated but has active access
        if profile.hr_status == "terminated":
            active_access = [a for a in profile.system_access.values() if a.status == "active"]
            if active_access:
                score += 40
                profile.risk_factors.append("GHOST IDENTITY: Terminated user with active access")
                profile.identity_status = IdentityStatus.GHOST
                profile.anomalies.append({
                    "type": IdentityAnomaly.GHOST.value,
                    "severity": "critical",
                    "description": f"Terminated user has active access in {len(active_access)} systems"
                })

        # Dormant check
        dormant_threshold_days = 90
        for sys_id, access in profile.system_access.items():
            if access.last_activity:
                days_inactive = (datetime.utcnow() - access.last_activity).days
                if days_inactive > dormant_threshold_days and access.status == "active":
                    score += 15
                    profile.risk_factors.append(f"Dormant access ({days_inactive} days) in {access.system_name}")
                    profile.anomalies.append({
                        "type": IdentityAnomaly.DORMANT.value,
                        "severity": "medium",
                        "description": f"No activity for {days_inactive} days in {access.system_name}"
                    })

        # Service account being used by human
        for access in profile.system_access.values():
            if access.account_type == "service" and access.login_count_30d > 100:
                # Might be interactive use
                score += 20
                profile.risk_factors.append(f"Possible interactive use of service account in {access.system_name}")

        # Shared account
        for access in profile.system_access.values():
            if access.account_type == "shared":
                score += 15
                profile.risk_factors.append(f"Using shared account in {access.system_name}")

        return min(score, 100)

    def _calculate_anomaly_risk(self, profile: IdentityProfile) -> float:
        """Calculate risk from detected anomalies"""

        score = 0.0

        # Each anomaly contributes based on severity
        severity_scores = {
            "critical": 30,
            "high": 20,
            "medium": 10,
            "low": 5
        }

        for anomaly in profile.anomalies:
            score += severity_scores.get(anomaly.get("severity", "low"), 5)

        return min(score, 100)

    def _get_risk_level(self, score: float) -> IdentityRiskLevel:
        """Convert score to risk level"""
        if score <= 20:
            return IdentityRiskLevel.MINIMAL
        elif score <= 40:
            return IdentityRiskLevel.LOW
        elif score <= 60:
            return IdentityRiskLevel.MODERATE
        elif score <= 80:
            return IdentityRiskLevel.HIGH
        else:
            return IdentityRiskLevel.CRITICAL

    def _compare_to_peers(self, profile: IdentityProfile):
        """Compare identity to peer group"""

        peer_ids = self.peer_groups.get(profile.peer_group, [])
        if len(peer_ids) < 3:
            return

        peer_scores = []
        for pid in peer_ids:
            if pid != profile.identity_id and pid in self.identity_profiles:
                peer = self.identity_profiles[pid]
                if peer.overall_risk_score > 0:
                    peer_scores.append(peer.overall_risk_score)

        if peer_scores:
            avg_peer_score = statistics.mean(peer_scores)
            profile.above_peer_average = profile.overall_risk_score > avg_peer_score

            # Calculate percentile
            below_count = len([s for s in peer_scores if s < profile.overall_risk_score])
            profile.percentile_in_peer_group = (below_count / len(peer_scores)) * 100

            if profile.percentile_in_peer_group > 90:
                profile.risk_factors.append("Risk significantly higher than peers (>90th percentile)")

    def _add_hygiene_issue(
        self,
        profile: IdentityProfile,
        issue_type: str,
        severity: str,
        description: str,
        remediation: str
    ):
        """Add a hygiene issue"""

        issue = IdentityHygieneIssue(
            issue_id=f"HYG-{len(self.hygiene_issues)+1}",
            identity_id=profile.identity_id,
            issue_type=issue_type,
            severity=severity,
            description=description,
            detected_at=datetime.utcnow(),
            remediation_action=remediation,
            auto_remediable=issue_type in ["dormant"]
        )
        self.hygiene_issues.append(issue)

    def detect_ghost_identities(self) -> List[IdentityProfile]:
        """Find all ghost identities (terminated but with active access)"""

        ghosts = []
        for profile in self.identity_profiles.values():
            if profile.hr_status == "terminated":
                active_access = [a for a in profile.system_access.values() if a.status == "active"]
                if active_access:
                    profile.identity_status = IdentityStatus.GHOST
                    ghosts.append(profile)

        return ghosts

    def detect_dormant_identities(self, days_threshold: int = 90) -> List[IdentityProfile]:
        """Find identities with no activity for specified days"""

        dormant = []
        now = datetime.utcnow()

        for profile in self.identity_profiles.values():
            if profile.hr_status != "active":
                continue

            is_dormant = True
            for access in profile.system_access.values():
                if access.last_activity:
                    if (now - access.last_activity).days < days_threshold:
                        is_dormant = False
                        break

            if is_dormant and profile.system_access:
                profile.identity_status = IdentityStatus.DORMANT
                dormant.append(profile)

        return dormant

    def detect_orphaned_identities(self) -> List[IdentityProfile]:
        """Find identities with no manager assigned"""

        orphaned = []
        for profile in self.identity_profiles.values():
            if not profile.manager_id and profile.hr_status == "active":
                orphaned.append(profile)

        return orphaned

    def get_identity_risk_report(self, identity_id: str) -> Dict:
        """Generate detailed risk report for an identity"""

        if identity_id not in self.identity_profiles:
            return {"error": "Identity not found"}

        profile = self.calculate_identity_risk(identity_id)

        return {
            "identity": {
                "identity_id": profile.identity_id,
                "full_name": profile.full_name,
                "email": profile.email,
                "department": profile.department,
                "job_title": profile.job_title,
                "manager": profile.manager_name,
                "hr_status": profile.hr_status,
                "identity_status": profile.identity_status.value
            },
            "risk_assessment": {
                "overall_risk_score": round(profile.overall_risk_score, 1),
                "risk_level": profile.risk_level.value,
                "component_scores": {
                    "access_risk": round(profile.access_risk_score, 1),
                    "behavior_risk": round(profile.behavior_risk_score, 1),
                    "hygiene_risk": round(profile.hygiene_risk_score, 1),
                    "anomaly_risk": round(profile.anomaly_risk_score, 1)
                }
            },
            "peer_comparison": {
                "peer_group": profile.peer_group,
                "above_peer_average": profile.above_peer_average,
                "percentile": round(profile.percentile_in_peer_group, 1)
            },
            "access_summary": {
                "total_systems": profile.total_systems,
                "total_roles": profile.total_roles,
                "total_entitlements": profile.total_entitlements,
                "systems": [
                    {
                        "system": a.system_name,
                        "account_type": a.account_type,
                        "privilege_level": a.privilege_level,
                        "roles_count": len(a.roles),
                        "last_activity": a.last_activity.isoformat() if a.last_activity else None
                    }
                    for a in profile.system_access.values()
                ]
            },
            "risk_factors": profile.risk_factors,
            "anomalies": profile.anomalies,
            "recommendations": self._generate_identity_recommendations(profile),
            "assessed_at": profile.last_assessment.isoformat() if profile.last_assessment else None
        }

    def _generate_identity_recommendations(self, profile: IdentityProfile) -> List[str]:
        """Generate recommendations for identity risk reduction"""

        recommendations = []

        if profile.risk_level in [IdentityRiskLevel.HIGH, IdentityRiskLevel.CRITICAL]:
            recommendations.append("PRIORITY: Immediate review required for this high-risk identity")

        if profile.identity_status == IdentityStatus.GHOST:
            recommendations.append("URGENT: Revoke all access for terminated identity")

        if profile.identity_status == IdentityStatus.DORMANT:
            recommendations.append("Review dormant access - consider deprovisioning unused accounts")

        if not profile.manager_id:
            recommendations.append("Assign a manager to this identity for proper governance")

        if profile.above_peer_average:
            recommendations.append("Review access - risk higher than peer group average")

        if profile.total_roles > 15:
            recommendations.append("Consider role consolidation - excessive role count")

        return recommendations

    def get_identity_hygiene_dashboard(self) -> Dict:
        """Generate identity hygiene dashboard"""

        profiles = list(self.identity_profiles.values())

        if not profiles:
            return {"error": "No identity data available"}

        # Calculate all risks first
        for profile in profiles:
            self.calculate_identity_risk(profile.identity_id)

        # Categorize
        ghosts = self.detect_ghost_identities()
        dormant = self.detect_dormant_identities()
        orphaned = self.detect_orphaned_identities()

        # Risk distribution
        risk_distribution = {level.value: 0 for level in IdentityRiskLevel}
        for profile in profiles:
            risk_distribution[profile.risk_level.value] += 1

        # Average scores
        avg_risk = statistics.mean([p.overall_risk_score for p in profiles]) if profiles else 0

        return {
            "summary": {
                "total_identities": len(profiles),
                "average_risk_score": round(avg_risk, 1),
                "ghost_identities": len(ghosts),
                "dormant_identities": len(dormant),
                "orphaned_identities": len(orphaned),
                "high_risk_identities": len([p for p in profiles if p.risk_level in [IdentityRiskLevel.HIGH, IdentityRiskLevel.CRITICAL]])
            },
            "risk_distribution": risk_distribution,
            "hygiene_issues": {
                "total": len(self.hygiene_issues),
                "critical": len([i for i in self.hygiene_issues if i.severity == "critical"]),
                "high": len([i for i in self.hygiene_issues if i.severity == "high"]),
                "auto_remediable": len([i for i in self.hygiene_issues if i.auto_remediable])
            },
            "ghost_identities": [
                {
                    "identity_id": p.identity_id,
                    "name": p.full_name,
                    "termination_date": p.termination_date.isoformat() if p.termination_date else "Unknown",
                    "active_systems": len([a for a in p.system_access.values() if a.status == "active"])
                }
                for p in ghosts[:10]
            ],
            "dormant_identities": [
                {
                    "identity_id": p.identity_id,
                    "name": p.full_name,
                    "days_inactive": p.days_since_last_activity
                }
                for p in dormant[:10]
            ],
            "top_risk_identities": [
                {
                    "identity_id": p.identity_id,
                    "name": p.full_name,
                    "risk_score": round(p.overall_risk_score, 1),
                    "risk_level": p.risk_level.value,
                    "top_risk_factor": p.risk_factors[0] if p.risk_factors else "N/A"
                }
                for p in sorted(profiles, key=lambda x: x.overall_risk_score, reverse=True)[:10]
            ],
            "audit_summary": self._generate_identity_audit_summary(profiles, ghosts, dormant, orphaned)
        }

    def _generate_identity_audit_summary(
        self,
        profiles: List[IdentityProfile],
        ghosts: List[IdentityProfile],
        dormant: List[IdentityProfile],
        orphaned: List[IdentityProfile]
    ) -> str:
        """Generate audit summary for identity governance"""

        total = len(profiles)
        issues = len(ghosts) + len(dormant) + len(orphaned)

        if total == 0:
            return "No identity data available for assessment."

        issue_rate = issues / total

        if issue_rate < 0.05 and not ghosts:
            return (
                "Identity governance demonstrates STRONG hygiene. No ghost identities detected, "
                f"and only {issue_rate*100:.1f}% of identities have hygiene issues."
            )
        elif issue_rate < 0.15 and len(ghosts) < 5:
            return (
                f"Identity governance is ADEQUATE with {issues} identities requiring attention. "
                f"{len(ghosts)} ghost identities and {len(dormant)} dormant identities need review."
            )
        else:
            return (
                f"SIGNIFICANT IDENTITY GOVERNANCE ISSUES detected. {len(ghosts)} ghost identities "
                f"represent immediate security risks. {len(dormant)} dormant and {len(orphaned)} "
                f"orphaned identities require cleanup. Immediate remediation recommended."
            )
