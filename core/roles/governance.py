# Role Governance Engine
# Continuous role governance with drift detection

"""
Role Governance for GOVERNEX+.

Provides:
- Continuous control monitoring on roles
- Drift detection (current vs baseline)
- Compliance status tracking
- Automated re-approval workflows
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging
import hashlib

from .models import Role, RoleVersion, RoleLifecycleState, RoleStatus

logger = logging.getLogger(__name__)


class ComplianceLevel(Enum):
    """Compliance levels for roles."""
    COMPLIANT = "COMPLIANT"
    MINOR_DEVIATION = "MINOR_DEVIATION"
    MAJOR_DEVIATION = "MAJOR_DEVIATION"
    NON_COMPLIANT = "NON_COMPLIANT"


class DriftType(Enum):
    """Types of role drift."""
    PERMISSION_ADDED = "PERMISSION_ADDED"
    PERMISSION_REMOVED = "PERMISSION_REMOVED"
    PERMISSION_MODIFIED = "PERMISSION_MODIFIED"
    METADATA_CHANGED = "METADATA_CHANGED"
    ASSIGNMENT_CHANGED = "ASSIGNMENT_CHANGED"


@dataclass
class GovernancePolicy:
    """Policy for role governance."""
    policy_id: str
    name: str
    description: str

    # Review requirements
    max_days_without_review: int = 90
    max_days_without_certification: int = 365

    # Change requirements
    require_approval_for_changes: bool = True
    require_justification_for_changes: bool = True

    # Drift tolerance
    max_permission_changes_before_reapproval: int = 5
    auto_revert_unauthorized_changes: bool = False

    # Notifications
    notify_owner_on_drift: bool = True
    notify_security_on_major_drift: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "max_days_without_review": self.max_days_without_review,
            "max_days_without_certification": self.max_days_without_certification,
            "require_approval_for_changes": self.require_approval_for_changes,
            "max_permission_changes_before_reapproval": self.max_permission_changes_before_reapproval,
        }


@dataclass
class DriftItem:
    """A single drift item."""
    drift_type: DriftType
    item_id: str
    description: str

    # Values
    baseline_value: Optional[Any] = None
    current_value: Optional[Any] = None

    # Impact
    severity: str = "LOW"  # LOW, MEDIUM, HIGH
    risk_impact: float = 0.0

    # Timestamps
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_type": self.drift_type.value,
            "item_id": self.item_id,
            "description": self.description,
            "baseline_value": str(self.baseline_value) if self.baseline_value else None,
            "current_value": str(self.current_value) if self.current_value else None,
            "severity": self.severity,
            "risk_impact": round(self.risk_impact, 2),
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class DriftReport:
    """Complete drift report for a role."""
    report_id: str
    role_id: str
    role_name: str

    # Baseline
    baseline_version: int = 0
    baseline_hash: str = ""
    baseline_date: Optional[datetime] = None

    # Current state
    current_version: int = 0
    current_hash: str = ""

    # Drift analysis
    has_drifted: bool = False
    drift_items: List[DriftItem] = field(default_factory=list)
    total_changes: int = 0

    # Severity
    max_severity: str = "NONE"
    requires_reapproval: bool = False

    # Compliance
    compliance_level: ComplianceLevel = ComplianceLevel.COMPLIANT

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    # Timestamps
    analyzed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "role_id": self.role_id,
            "role_name": self.role_name,
            "baseline_version": self.baseline_version,
            "current_version": self.current_version,
            "has_drifted": self.has_drifted,
            "drift_items": [d.to_dict() for d in self.drift_items],
            "total_changes": self.total_changes,
            "max_severity": self.max_severity,
            "requires_reapproval": self.requires_reapproval,
            "compliance_level": self.compliance_level.value,
            "recommendations": self.recommendations,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


@dataclass
class ComplianceStatus:
    """Compliance status for a role."""
    role_id: str
    role_name: str

    # Overall status
    is_compliant: bool = True
    compliance_level: ComplianceLevel = ComplianceLevel.COMPLIANT
    compliance_score: float = 100.0  # 0-100

    # Violations
    violations: List[Dict[str, Any]] = field(default_factory=list)

    # Review status
    review_overdue: bool = False
    days_since_review: int = 0
    days_until_review_due: int = 0

    # Certification status
    certification_overdue: bool = False
    days_since_certification: int = 0

    # Drift status
    drift_detected: bool = False
    drift_report: Optional[DriftReport] = None

    # Timestamps
    checked_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "is_compliant": self.is_compliant,
            "compliance_level": self.compliance_level.value,
            "compliance_score": round(self.compliance_score, 2),
            "violations": self.violations,
            "review_overdue": self.review_overdue,
            "days_since_review": self.days_since_review,
            "certification_overdue": self.certification_overdue,
            "drift_detected": self.drift_detected,
            "checked_at": self.checked_at.isoformat(),
        }


class DriftDetector:
    """
    Detects drift between role baseline and current state.

    Key capabilities:
    - Compare role versions
    - Identify specific changes
    - Assess drift severity
    - Trigger re-approval workflows
    """

    def __init__(self):
        """Initialize detector."""
        self._baselines: Dict[str, Dict[str, Any]] = {}

    def set_baseline(self, role: Role):
        """Set baseline for a role."""
        self._baselines[role.role_id] = {
            "version": role.current_version,
            "hash": role.content_hash,
            "permissions": {p.permission_id: p.to_dict() for p in role.permissions},
            "child_roles": set(role.child_roles),
            "assignment_count": role.assignment_count,
            "timestamp": datetime.now(),
        }

    def detect_drift(
        self,
        role: Role,
        policy: Optional[GovernancePolicy] = None
    ) -> DriftReport:
        """
        Detect drift for a role.

        Args:
            role: Current role state
            policy: Governance policy for threshold checks

        Returns:
            DriftReport with detailed analysis
        """
        policy = policy or GovernancePolicy(
            policy_id="DEFAULT",
            name="Default Policy",
            description="Default governance policy"
        )

        report = DriftReport(
            report_id=f"DRIFT-{role.role_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            role_id=role.role_id,
            role_name=role.role_name,
            current_version=role.current_version,
            current_hash=role.content_hash,
        )

        # Get baseline
        baseline = self._baselines.get(role.role_id)

        if not baseline:
            report.recommendations.append("No baseline set - establish baseline first")
            return report

        report.baseline_version = baseline["version"]
        report.baseline_hash = baseline["hash"]
        report.baseline_date = baseline["timestamp"]

        # Quick check - if hash matches, no drift
        if baseline["hash"] == role.content_hash:
            report.has_drifted = False
            report.compliance_level = ComplianceLevel.COMPLIANT
            return report

        # Detailed comparison
        report.has_drifted = True

        # Check permission changes
        baseline_perms = set(baseline["permissions"].keys())
        current_perms = {p.permission_id for p in role.permissions}

        # Added permissions
        added = current_perms - baseline_perms
        for perm_id in added:
            perm = next((p for p in role.permissions if p.permission_id == perm_id), None)
            report.drift_items.append(DriftItem(
                drift_type=DriftType.PERMISSION_ADDED,
                item_id=perm_id,
                description=f"Permission added: {perm.value if perm else perm_id}",
                current_value=perm.value if perm else None,
                severity="MEDIUM" if perm and perm.is_sensitive else "LOW",
                risk_impact=10 if perm and perm.is_sensitive else 5,
            ))

        # Removed permissions
        removed = baseline_perms - current_perms
        for perm_id in removed:
            baseline_perm = baseline["permissions"].get(perm_id, {})
            report.drift_items.append(DriftItem(
                drift_type=DriftType.PERMISSION_REMOVED,
                item_id=perm_id,
                description=f"Permission removed: {baseline_perm.get('value', perm_id)}",
                baseline_value=baseline_perm.get("value"),
                severity="LOW",
                risk_impact=2,
            ))

        # Child role changes
        baseline_children = baseline.get("child_roles", set())
        current_children = set(role.child_roles)

        if baseline_children != current_children:
            report.drift_items.append(DriftItem(
                drift_type=DriftType.PERMISSION_MODIFIED,
                item_id="child_roles",
                description="Child roles changed",
                baseline_value=list(baseline_children),
                current_value=list(current_children),
                severity="MEDIUM",
                risk_impact=15,
            ))

        # Assignment count change
        baseline_assignments = baseline.get("assignment_count", 0)
        if abs(role.assignment_count - baseline_assignments) > 10:
            report.drift_items.append(DriftItem(
                drift_type=DriftType.ASSIGNMENT_CHANGED,
                item_id="assignments",
                description=f"Assignment count changed: {baseline_assignments} → {role.assignment_count}",
                baseline_value=baseline_assignments,
                current_value=role.assignment_count,
                severity="LOW",
            ))

        # Calculate totals
        report.total_changes = len(report.drift_items)

        # Determine max severity
        severities = [d.severity for d in report.drift_items]
        if "HIGH" in severities:
            report.max_severity = "HIGH"
        elif "MEDIUM" in severities:
            report.max_severity = "MEDIUM"
        elif severities:
            report.max_severity = "LOW"
        else:
            report.max_severity = "NONE"

        # Check if re-approval required
        report.requires_reapproval = (
            report.total_changes > policy.max_permission_changes_before_reapproval or
            report.max_severity == "HIGH"
        )

        # Determine compliance level
        if report.max_severity == "HIGH" or report.requires_reapproval:
            report.compliance_level = ComplianceLevel.MAJOR_DEVIATION
        elif report.max_severity == "MEDIUM":
            report.compliance_level = ComplianceLevel.MINOR_DEVIATION
        elif report.has_drifted:
            report.compliance_level = ComplianceLevel.MINOR_DEVIATION
        else:
            report.compliance_level = ComplianceLevel.COMPLIANT

        # Generate recommendations
        if report.requires_reapproval:
            report.recommendations.append("Submit role for re-approval")

        if len(added) > 0:
            report.recommendations.append(f"Review {len(added)} added permissions")

        if report.max_severity == "HIGH":
            report.recommendations.append("Immediate security review required")

        return report

    def get_baseline(self, role_id: str) -> Optional[Dict[str, Any]]:
        """Get baseline for a role."""
        return self._baselines.get(role_id)


class RoleGovernanceEngine:
    """
    Continuous role governance engine.

    Key capabilities:
    - Monitor role changes in real-time
    - Enforce governance policies
    - Detect and report drift
    - Manage compliance status
    """

    def __init__(self, policy: Optional[GovernancePolicy] = None):
        """Initialize governance engine."""
        self.policy = policy or GovernancePolicy(
            policy_id="DEFAULT",
            name="Default Policy",
            description="Default governance policy"
        )
        self.drift_detector = DriftDetector()
        self._change_handlers: List[Callable] = []

    def register_change_handler(self, handler: Callable[[Role, DriftReport], None]):
        """Register a handler for role changes."""
        self._change_handlers.append(handler)

    def check_compliance(self, role: Role) -> ComplianceStatus:
        """
        Check compliance status for a role.

        Args:
            role: Role to check

        Returns:
            ComplianceStatus with detailed analysis
        """
        status = ComplianceStatus(
            role_id=role.role_id,
            role_name=role.role_name,
        )

        violations = []

        # Check review status
        if role.metadata and role.metadata.last_review_date:
            days_since = (datetime.now() - role.metadata.last_review_date).days
            status.days_since_review = days_since
            status.days_until_review_due = self.policy.max_days_without_review - days_since

            if days_since > self.policy.max_days_without_review:
                status.review_overdue = True
                violations.append({
                    "type": "REVIEW_OVERDUE",
                    "description": f"Review overdue by {days_since - self.policy.max_days_without_review} days",
                    "severity": "HIGH",
                })
        else:
            status.review_overdue = True
            violations.append({
                "type": "NEVER_REVIEWED",
                "description": "Role has never been reviewed",
                "severity": "MEDIUM",
            })

        # Check certification status
        if role.metadata and role.metadata.last_certified_date:
            days_since = (datetime.now() - role.metadata.last_certified_date).days
            status.days_since_certification = days_since

            if days_since > self.policy.max_days_without_certification:
                status.certification_overdue = True
                violations.append({
                    "type": "CERTIFICATION_OVERDUE",
                    "description": f"Certification overdue by {days_since - self.policy.max_days_without_certification} days",
                    "severity": "HIGH",
                })

        # Check for drift
        drift_report = self.drift_detector.detect_drift(role, self.policy)
        if drift_report.has_drifted:
            status.drift_detected = True
            status.drift_report = drift_report

            if drift_report.requires_reapproval:
                violations.append({
                    "type": "DRIFT_REQUIRES_REAPPROVAL",
                    "description": f"{drift_report.total_changes} changes detected, re-approval required",
                    "severity": "HIGH",
                })

        # Check metadata completeness
        if not role.metadata:
            violations.append({
                "type": "MISSING_METADATA",
                "description": "Role missing required governance metadata",
                "severity": "MEDIUM",
            })
        elif not role.metadata.business_justification:
            violations.append({
                "type": "MISSING_JUSTIFICATION",
                "description": "Role missing business justification",
                "severity": "LOW",
            })

        status.violations = violations

        # Determine overall compliance
        if violations:
            high_violations = sum(1 for v in violations if v["severity"] == "HIGH")

            if high_violations >= 2:
                status.is_compliant = False
                status.compliance_level = ComplianceLevel.NON_COMPLIANT
                status.compliance_score = 0
            elif high_violations == 1:
                status.is_compliant = False
                status.compliance_level = ComplianceLevel.MAJOR_DEVIATION
                status.compliance_score = 40
            else:
                status.is_compliant = True
                status.compliance_level = ComplianceLevel.MINOR_DEVIATION
                status.compliance_score = 70
        else:
            status.is_compliant = True
            status.compliance_level = ComplianceLevel.COMPLIANT
            status.compliance_score = 100

        return status

    def on_role_change(self, role: Role, change_type: str, changed_by: str):
        """
        Handle a role change event.

        Args:
            role: Changed role
            change_type: Type of change
            changed_by: User who made the change
        """
        # Create version record
        version = role.create_version(change_type, changed_by)

        # Check for drift
        drift_report = self.drift_detector.detect_drift(role, self.policy)

        # Notify handlers
        for handler in self._change_handlers:
            try:
                handler(role, drift_report)
            except Exception as e:
                logger.error(f"Change handler error: {e}")

        # Log significant changes
        if drift_report.requires_reapproval:
            logger.warning(
                f"Role {role.role_id} requires re-approval: "
                f"{drift_report.total_changes} changes detected"
            )

    def set_baseline(self, role: Role):
        """Set baseline for a role (after approval)."""
        self.drift_detector.set_baseline(role)

    def get_roles_requiring_action(
        self,
        roles: List[Role]
    ) -> Dict[str, List[Role]]:
        """Get roles grouped by required action."""
        result = {
            "review_overdue": [],
            "certification_overdue": [],
            "reapproval_required": [],
            "non_compliant": [],
        }

        for role in roles:
            status = self.check_compliance(role)

            if status.review_overdue:
                result["review_overdue"].append(role)

            if status.certification_overdue:
                result["certification_overdue"].append(role)

            if status.drift_report and status.drift_report.requires_reapproval:
                result["reapproval_required"].append(role)

            if status.compliance_level == ComplianceLevel.NON_COMPLIANT:
                result["non_compliant"].append(role)

        return result
