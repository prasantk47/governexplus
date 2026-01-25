# Role Simulation
# Pre-build risk simulation before role activation

"""
Role Simulation for GOVERNEX+.

Simulate role impact before activation:
- SoD risks
- Toxic paths
- Risk score
- User impact

Block unsafe role creation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from enum import Enum
import logging

from .models import Role, Permission

logger = logging.getLogger(__name__)


class SimulationStatus(Enum):
    """Simulation result status."""
    SAFE = "SAFE"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


@dataclass
class SimulatedRisk:
    """A risk identified during simulation."""
    risk_id: str
    risk_type: str  # "SOD", "TOXIC_PATH", "SENSITIVE", "PRIVILEGE_ESCALATION"
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    description: str

    # Details
    affected_actions: List[str] = field(default_factory=list)
    conflicting_permissions: List[str] = field(default_factory=list)

    # Impact
    potential_fraud_path: bool = False
    control_bypass: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "risk_type": self.risk_type,
            "severity": self.severity,
            "description": self.description,
            "affected_actions": self.affected_actions,
            "conflicting_permissions": self.conflicting_permissions,
            "potential_fraud_path": self.potential_fraud_path,
            "control_bypass": self.control_bypass,
        }


@dataclass
class SimulationConfig:
    """Configuration for role simulation."""
    # Thresholds
    max_risk_score: int = 80
    max_sod_conflicts: int = 3
    max_sensitive_permissions: int = 10

    # Blocking rules
    block_on_critical_risk: bool = True
    block_on_fraud_path: bool = True
    block_on_wildcard_sensitive: bool = True

    # Notifications
    notify_on_warning: bool = True
    notify_on_block: bool = True
    notify_recipients: List[str] = field(default_factory=list)


@dataclass
class SimulationResult:
    """Complete simulation result."""
    simulation_id: str
    role_id: str
    role_name: str

    # Overall result
    status: SimulationStatus = SimulationStatus.SAFE
    can_activate: bool = True
    block_reason: str = ""

    # Risk analysis
    predicted_risk_score: float = 0.0
    risks_identified: List[SimulatedRisk] = field(default_factory=list)

    # SoD analysis
    sod_conflicts: List[Dict[str, Any]] = field(default_factory=list)
    sod_conflict_count: int = 0

    # Toxic path analysis
    toxic_paths: List[Dict[str, Any]] = field(default_factory=list)
    is_toxic: bool = False
    toxicity_score: float = 0.0

    # Permission analysis
    total_permissions: int = 0
    sensitive_permissions: int = 0
    wildcard_authorizations: int = 0

    # User impact
    potential_users: int = 0
    existing_similar_roles: List[str] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    required_changes: List[str] = field(default_factory=list)

    # Metadata
    simulated_at: datetime = field(default_factory=datetime.now)
    config_used: Optional[SimulationConfig] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "role_id": self.role_id,
            "role_name": self.role_name,
            "status": self.status.value,
            "can_activate": self.can_activate,
            "block_reason": self.block_reason,
            "predicted_risk_score": round(self.predicted_risk_score, 2),
            "risks_identified": [r.to_dict() for r in self.risks_identified],
            "sod_conflict_count": self.sod_conflict_count,
            "is_toxic": self.is_toxic,
            "toxicity_score": round(self.toxicity_score, 2),
            "total_permissions": self.total_permissions,
            "sensitive_permissions": self.sensitive_permissions,
            "wildcard_authorizations": self.wildcard_authorizations,
            "recommendations": self.recommendations,
            "required_changes": self.required_changes,
            "simulated_at": self.simulated_at.isoformat(),
        }


class RoleSimulator:
    """
    Simulates role impact before activation.

    Key capabilities:
    - Predict risk score
    - Detect SoD conflicts
    - Identify toxic paths
    - Block unsafe roles
    - Recommend improvements
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        """Initialize simulator."""
        self.config = config or SimulationConfig()
        self._simulation_counter = 0

        # SoD rules (simplified - in production, load from rule engine)
        self._sod_rules = [
            {"actions": {"CREATE_VENDOR", "EXECUTE_PAYMENT"}, "severity": "CRITICAL"},
            {"actions": {"CREATE_PO", "POST_GOODS_RECEIPT"}, "severity": "HIGH"},
            {"actions": {"HIRE_EMPLOYEE", "EXECUTE_PAYROLL"}, "severity": "CRITICAL"},
            {"actions": {"CREATE_USER", "ASSIGN_ROLE"}, "severity": "CRITICAL"},
        ]

    def simulate(
        self,
        role: Role,
        existing_user_access: Optional[Dict[str, Set[str]]] = None
    ) -> SimulationResult:
        """
        Simulate role before activation.

        Args:
            role: Role to simulate
            existing_user_access: Current access for users who would get this role

        Returns:
            SimulationResult with analysis and recommendations
        """
        self._simulation_counter += 1
        result = SimulationResult(
            simulation_id=f"SIM-{role.role_id}-{self._simulation_counter}",
            role_id=role.role_id,
            role_name=role.role_name,
            config_used=self.config,
        )

        # Basic permission analysis
        result.total_permissions = role.permission_count
        result.sensitive_permissions = role.sensitive_permission_count

        # Wildcard analysis
        result.wildcard_authorizations = sum(
            1 for p in role.permissions
            if p.auth_object and p.auth_object.has_wildcard()
        )

        # Get business actions enabled by this role
        role_actions = role.get_business_actions()

        # SoD analysis
        sod_conflicts = self._check_sod_conflicts(role_actions)
        result.sod_conflicts = sod_conflicts
        result.sod_conflict_count = len(sod_conflicts)

        # Add SoD risks
        for conflict in sod_conflicts:
            result.risks_identified.append(SimulatedRisk(
                risk_id=f"SOD-{len(result.risks_identified) + 1}",
                risk_type="SOD",
                severity=conflict["severity"],
                description=f"SoD conflict: {conflict['actions']}",
                affected_actions=list(conflict["actions"]),
                potential_fraud_path=conflict["severity"] == "CRITICAL",
            ))

        # Toxic path analysis
        toxic_result = self._check_toxic_paths(role_actions)
        result.toxic_paths = toxic_result["paths"]
        result.is_toxic = toxic_result["is_toxic"]
        result.toxicity_score = toxic_result["toxicity_score"]

        if result.is_toxic:
            result.risks_identified.append(SimulatedRisk(
                risk_id=f"TOXIC-1",
                risk_type="TOXIC_PATH",
                severity="CRITICAL",
                description="Role enables complete fraud path",
                affected_actions=list(role_actions),
                potential_fraud_path=True,
                control_bypass=True,
            ))

        # Sensitive access risks
        if result.sensitive_permissions > self.config.max_sensitive_permissions:
            result.risks_identified.append(SimulatedRisk(
                risk_id=f"SENS-1",
                risk_type="SENSITIVE",
                severity="HIGH",
                description=f"Excessive sensitive permissions: {result.sensitive_permissions}",
            ))

        # Wildcard risks
        wildcard_sensitive = sum(
            1 for p in role.permissions
            if p.is_sensitive and p.auth_object and p.auth_object.has_wildcard()
        )
        if wildcard_sensitive > 0:
            result.risks_identified.append(SimulatedRisk(
                risk_id=f"WILD-1",
                risk_type="PRIVILEGE_ESCALATION",
                severity="CRITICAL",
                description=f"Wildcards in sensitive authorizations: {wildcard_sensitive}",
            ))

        # Calculate predicted risk score
        result.predicted_risk_score = self._calculate_risk_score(result)

        # Determine status
        result.status, result.can_activate, result.block_reason = \
            self._determine_status(result)

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)
        result.required_changes = self._generate_required_changes(result)

        return result

    def _check_sod_conflicts(
        self,
        role_actions: Set[str]
    ) -> List[Dict[str, Any]]:
        """Check for SoD conflicts."""
        conflicts = []

        for rule in self._sod_rules:
            rule_actions = rule["actions"]
            if rule_actions.issubset(role_actions):
                conflicts.append({
                    "actions": list(rule_actions),
                    "severity": rule["severity"],
                })

        return conflicts

    def _check_toxic_paths(
        self,
        role_actions: Set[str]
    ) -> Dict[str, Any]:
        """Check for toxic paths (complete fraud cycles)."""
        # Define fraud cycles
        fraud_cycles = [
            {"name": "P2P Fraud", "actions": {"CREATE_VENDOR", "CREATE_PO", "EXECUTE_PAYMENT"}},
            {"name": "Payroll Fraud", "actions": {"HIRE_EMPLOYEE", "CHANGE_SALARY", "EXECUTE_PAYROLL"}},
            {"name": "Privilege Escalation", "actions": {"CREATE_USER", "ASSIGN_ROLE", "MODIFY_ROLE"}},
        ]

        paths = []
        is_toxic = False
        toxicity_score = 0

        for cycle in fraud_cycles:
            overlap = cycle["actions"] & role_actions
            if len(overlap) >= 2:
                coverage = len(overlap) / len(cycle["actions"])
                paths.append({
                    "name": cycle["name"],
                    "enabled_actions": list(overlap),
                    "coverage": coverage,
                })
                toxicity_score += coverage * 33

                if coverage == 1.0:
                    is_toxic = True

        return {
            "paths": paths,
            "is_toxic": is_toxic,
            "toxicity_score": min(100, toxicity_score),
        }

    def _calculate_risk_score(self, result: SimulationResult) -> float:
        """Calculate predicted risk score."""
        score = 0

        # SoD impact (up to 30)
        if result.sod_conflict_count > 0:
            score += min(30, result.sod_conflict_count * 10)

        # Toxicity impact (up to 25)
        score += result.toxicity_score * 0.25

        # Sensitive access (up to 20)
        if result.total_permissions > 0:
            sensitive_ratio = result.sensitive_permissions / result.total_permissions
            score += sensitive_ratio * 20

        # Wildcard impact (up to 15)
        score += min(15, result.wildcard_authorizations * 5)

        # Permission breadth (up to 10)
        if result.total_permissions > 50:
            score += 10
        elif result.total_permissions > 25:
            score += 5

        return min(100, score)

    def _determine_status(
        self,
        result: SimulationResult
    ) -> tuple[SimulationStatus, bool, str]:
        """Determine simulation status and whether to block."""
        # Critical blocking conditions
        if self.config.block_on_critical_risk:
            critical_risks = [r for r in result.risks_identified if r.severity == "CRITICAL"]
            if critical_risks:
                return (
                    SimulationStatus.BLOCKED,
                    False,
                    f"Critical risk detected: {critical_risks[0].description}"
                )

        if self.config.block_on_fraud_path and result.is_toxic:
            return (
                SimulationStatus.BLOCKED,
                False,
                "Role enables complete fraud path"
            )

        # Score-based blocking
        if result.predicted_risk_score > self.config.max_risk_score:
            return (
                SimulationStatus.BLOCKED,
                False,
                f"Risk score {result.predicted_risk_score:.0f} exceeds maximum {self.config.max_risk_score}"
            )

        # SoD-based blocking
        if result.sod_conflict_count > self.config.max_sod_conflicts:
            return (
                SimulationStatus.BLOCKED,
                False,
                f"{result.sod_conflict_count} SoD conflicts exceed maximum {self.config.max_sod_conflicts}"
            )

        # Warning conditions
        if result.risks_identified:
            return (
                SimulationStatus.WARNING,
                True,
                ""
            )

        return (SimulationStatus.SAFE, True, "")

    def _generate_recommendations(self, result: SimulationResult) -> List[str]:
        """Generate recommendations for the role."""
        recommendations = []

        if result.sod_conflict_count > 0:
            recommendations.append(
                "Split role to eliminate SoD conflicts"
            )

        if result.is_toxic:
            recommendations.append(
                "Redesign role to prevent complete fraud path"
            )

        if result.wildcard_authorizations > 0:
            recommendations.append(
                "Replace wildcard (*) authorizations with specific values"
            )

        if result.sensitive_permissions > self.config.max_sensitive_permissions:
            recommendations.append(
                f"Reduce sensitive permissions (current: {result.sensitive_permissions})"
            )

        if result.total_permissions > 50:
            recommendations.append(
                "Consider decomposing role - too many permissions"
            )

        if not recommendations:
            recommendations.append("Role design appears acceptable")

        return recommendations

    def _generate_required_changes(self, result: SimulationResult) -> List[str]:
        """Generate required changes before activation."""
        changes = []

        if result.status == SimulationStatus.BLOCKED:
            # Find critical issues
            for risk in result.risks_identified:
                if risk.severity == "CRITICAL":
                    if risk.risk_type == "SOD":
                        changes.append(
                            f"Remove one of: {', '.join(risk.affected_actions)}"
                        )
                    elif risk.risk_type == "TOXIC_PATH":
                        changes.append(
                            "Remove actions that complete the fraud cycle"
                        )
                    elif risk.risk_type == "PRIVILEGE_ESCALATION":
                        changes.append(
                            "Remove wildcard from sensitive authorization objects"
                        )

        return changes

    def simulate_user_assignment(
        self,
        role: Role,
        user_id: str,
        current_user_roles: List[Role]
    ) -> SimulationResult:
        """
        Simulate assigning a role to a specific user.

        Checks combined impact with user's existing roles.
        """
        # Get all actions user would have
        combined_actions = role.get_business_actions()
        for existing_role in current_user_roles:
            combined_actions.update(existing_role.get_business_actions())

        # Create temporary combined role for simulation
        combined_role = Role(
            role_id=f"COMBINED-{user_id}",
            role_name=f"Combined access for {user_id}",
        )

        # Add all permissions
        for existing_role in current_user_roles:
            for perm in existing_role.permissions:
                combined_role.add_permission(perm)
        for perm in role.permissions:
            combined_role.add_permission(perm)

        # Simulate combined role
        result = self.simulate(combined_role)
        result.role_id = role.role_id
        result.role_name = f"Assignment: {role.role_name} to {user_id}"

        return result
