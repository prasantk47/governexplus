"""
Productive Test Simulation (PTS) for Governex+

Test role changes in a virtual environment before deploying to production.
Simulates user access scenarios to identify potential issues.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import uuid
import random


class SimulationStatus(Enum):
    """Status of a simulation"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImpactLevel(Enum):
    """Impact level of changes"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeType(Enum):
    """Type of role/access change"""
    ADD_ROLE = "add_role"
    REMOVE_ROLE = "remove_role"
    MODIFY_ROLE = "modify_role"
    ADD_PERMISSION = "add_permission"
    REMOVE_PERMISSION = "remove_permission"
    USER_TRANSFER = "user_transfer"
    ROLE_CONSOLIDATION = "role_consolidation"


@dataclass
class AccessChange:
    """A proposed access change to simulate"""
    change_id: str
    change_type: ChangeType
    target_user: str = ""
    target_users: List[str] = field(default_factory=list)
    role_id: str = ""
    role_name: str = ""
    permissions: List[Dict[str, Any]] = field(default_factory=list)
    effective_date: Optional[datetime] = None
    justification: str = ""


@dataclass
class ImpactAnalysis:
    """Analysis of change impact"""
    change_id: str
    impact_level: ImpactLevel
    affected_users: int
    affected_transactions: List[str]

    # Risk assessment
    sod_conflicts: List[Dict[str, Any]]
    sensitive_access_grants: List[Dict[str, Any]]
    privilege_escalations: List[Dict[str, Any]]

    # Access changes
    new_permissions: List[str]
    removed_permissions: List[str]
    unchanged_permissions: int

    # Compliance impact
    compliance_frameworks_affected: List[str]
    audit_findings_risk: int

    # Recommendations
    recommendations: List[str]
    warnings: List[str]
    blockers: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "impact_level": self.impact_level.value,
            "affected_users": self.affected_users,
            "affected_transactions": self.affected_transactions,
            "sod_conflicts": self.sod_conflicts,
            "sensitive_access_grants": self.sensitive_access_grants,
            "privilege_escalations": self.privilege_escalations,
            "new_permissions": self.new_permissions,
            "removed_permissions": self.removed_permissions,
            "unchanged_permissions": self.unchanged_permissions,
            "compliance_frameworks_affected": self.compliance_frameworks_affected,
            "audit_findings_risk": self.audit_findings_risk,
            "recommendations": self.recommendations,
            "warnings": self.warnings,
            "blockers": self.blockers
        }


@dataclass
class TestScenario:
    """A test scenario to execute during simulation"""
    scenario_id: str
    name: str
    description: str
    user_id: str
    transaction_code: str
    expected_result: str  # success, failure
    actual_result: Optional[str] = None
    execution_time_ms: int = 0
    error_message: str = ""
    permissions_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "transaction_code": self.transaction_code,
            "expected_result": self.expected_result,
            "actual_result": self.actual_result,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "permissions_used": self.permissions_used,
            "passed": self.actual_result == self.expected_result if self.actual_result else None
        }


@dataclass
class SimulationScenario:
    """Configuration for a simulation run"""
    scenario_id: str
    name: str
    description: str
    created_by: str
    created_at: datetime

    # Changes to simulate
    changes: List[AccessChange]

    # Test scenarios
    test_scenarios: List[TestScenario] = field(default_factory=list)

    # Options
    include_sod_check: bool = True
    include_sensitive_check: bool = True
    include_compliance_check: bool = True
    include_usage_analysis: bool = True

    # Target
    target_system: str = "SAP ECC"
    target_client: str = "100"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "changes_count": len(self.changes),
            "test_scenarios_count": len(self.test_scenarios),
            "options": {
                "include_sod_check": self.include_sod_check,
                "include_sensitive_check": self.include_sensitive_check,
                "include_compliance_check": self.include_compliance_check,
                "include_usage_analysis": self.include_usage_analysis
            },
            "target_system": self.target_system,
            "target_client": self.target_client
        }


@dataclass
class SimulationResult:
    """Result of a simulation run"""
    simulation_id: str
    scenario: SimulationScenario
    status: SimulationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Results
    overall_impact: ImpactLevel = ImpactLevel.NONE
    impact_analyses: List[ImpactAnalysis] = field(default_factory=list)
    test_results: List[TestScenario] = field(default_factory=list)

    # Summary
    total_changes: int = 0
    changes_with_issues: int = 0
    total_tests: int = 0
    tests_passed: int = 0
    tests_failed: int = 0

    # Recommendations
    can_proceed: bool = True
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Execution details
    execution_time_seconds: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "scenario": self.scenario.to_dict(),
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "overall_impact": self.overall_impact.value,
            "impact_analyses": [ia.to_dict() for ia in self.impact_analyses],
            "test_results": [tr.to_dict() for tr in self.test_results],
            "summary": {
                "total_changes": self.total_changes,
                "changes_with_issues": self.changes_with_issues,
                "total_tests": self.total_tests,
                "tests_passed": self.tests_passed,
                "tests_failed": self.tests_failed,
                "pass_rate": (self.tests_passed / self.total_tests * 100) if self.total_tests > 0 else 0
            },
            "can_proceed": self.can_proceed,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "execution_time_seconds": self.execution_time_seconds,
            "error_message": self.error_message
        }


class PTSSimulator:
    """
    Productive Test Simulation Engine

    Features:
    - Virtual role assignment testing
    - What-if scenario analysis
    - SoD conflict detection
    - Sensitive access validation
    - Compliance impact assessment
    - Automated test execution
    """

    def __init__(self):
        self.simulations: Dict[str, SimulationResult] = {}
        self.scenarios: Dict[str, SimulationScenario] = {}
        self.statistics = {
            "total_simulations": 0,
            "completed_simulations": 0,
            "failed_simulations": 0,
            "blockers_found": 0,
            "changes_tested": 0
        }

        # Demo data
        self._demo_transactions = [
            "FB01", "FB02", "FB03", "ME21N", "ME22N", "ME23N",
            "VA01", "VA02", "VA03", "MM01", "MM02", "MM03",
            "XK01", "XK02", "XK03", "FK01", "FK02", "FK03",
            "SU01", "SU10", "PFCG", "SE38", "SE16", "SM37"
        ]

        self._demo_sod_rules = [
            {"function1": "Vendor Master", "function2": "Payment Processing"},
            {"function1": "PO Creation", "function2": "PO Approval"},
            {"function1": "User Admin", "function2": "Audit Log Access"},
            {"function1": "Customer Master", "function2": "Credit Management"}
        ]

    def create_scenario(
        self,
        name: str,
        description: str,
        created_by: str,
        changes: List[Dict[str, Any]],
        **options
    ) -> SimulationScenario:
        """Create a new simulation scenario"""
        scenario_id = str(uuid.uuid4())

        access_changes = []
        for change in changes:
            access_changes.append(AccessChange(
                change_id=str(uuid.uuid4()),
                change_type=ChangeType(change.get("change_type", "add_role")),
                target_user=change.get("target_user", ""),
                target_users=change.get("target_users", []),
                role_id=change.get("role_id", ""),
                role_name=change.get("role_name", ""),
                permissions=change.get("permissions", []),
                justification=change.get("justification", "")
            ))

        scenario = SimulationScenario(
            scenario_id=scenario_id,
            name=name,
            description=description,
            created_by=created_by,
            created_at=datetime.now(),
            changes=access_changes,
            include_sod_check=options.get("include_sod_check", True),
            include_sensitive_check=options.get("include_sensitive_check", True),
            include_compliance_check=options.get("include_compliance_check", True),
            include_usage_analysis=options.get("include_usage_analysis", True),
            target_system=options.get("target_system", "SAP ECC"),
            target_client=options.get("target_client", "100")
        )

        self.scenarios[scenario_id] = scenario
        return scenario

    def add_test_scenario(
        self,
        scenario_id: str,
        name: str,
        user_id: str,
        transaction_code: str,
        expected_result: str = "success",
        description: str = ""
    ) -> TestScenario:
        """Add a test scenario to a simulation"""
        if scenario_id not in self.scenarios:
            raise ValueError(f"Scenario not found: {scenario_id}")

        test = TestScenario(
            scenario_id=str(uuid.uuid4()),
            name=name,
            description=description or f"Test {transaction_code} for {user_id}",
            user_id=user_id,
            transaction_code=transaction_code,
            expected_result=expected_result
        )

        self.scenarios[scenario_id].test_scenarios.append(test)
        return test

    def run_simulation(self, scenario_id: str) -> SimulationResult:
        """
        Run a complete simulation for a scenario

        Args:
            scenario_id: ID of the scenario to simulate

        Returns:
            SimulationResult with detailed analysis
        """
        if scenario_id not in self.scenarios:
            raise ValueError(f"Scenario not found: {scenario_id}")

        scenario = self.scenarios[scenario_id]
        simulation_id = str(uuid.uuid4())
        start_time = datetime.now()

        self.statistics["total_simulations"] += 1

        result = SimulationResult(
            simulation_id=simulation_id,
            scenario=scenario,
            status=SimulationStatus.RUNNING,
            started_at=start_time,
            total_changes=len(scenario.changes)
        )

        try:
            # Analyze each change
            for change in scenario.changes:
                impact = self._analyze_change(change, scenario)
                result.impact_analyses.append(impact)

                if impact.blockers:
                    result.changes_with_issues += 1
                    result.blockers.extend(impact.blockers)

                if impact.warnings:
                    result.warnings.extend(impact.warnings)

                if impact.recommendations:
                    result.recommendations.extend(impact.recommendations)

                # Update overall impact
                if impact.impact_level.value == "critical":
                    result.overall_impact = ImpactLevel.CRITICAL
                elif impact.impact_level.value == "high" and result.overall_impact != ImpactLevel.CRITICAL:
                    result.overall_impact = ImpactLevel.HIGH
                elif impact.impact_level.value == "medium" and result.overall_impact.value in ["none", "low"]:
                    result.overall_impact = ImpactLevel.MEDIUM
                elif impact.impact_level.value == "low" and result.overall_impact.value == "none":
                    result.overall_impact = ImpactLevel.LOW

            # Run test scenarios
            for test in scenario.test_scenarios:
                executed_test = self._execute_test(test, scenario)
                result.test_results.append(executed_test)
                result.total_tests += 1

                if executed_test.actual_result == executed_test.expected_result:
                    result.tests_passed += 1
                else:
                    result.tests_failed += 1

            # Determine if can proceed
            result.can_proceed = len(result.blockers) == 0

            # Complete simulation
            result.status = SimulationStatus.COMPLETED
            result.completed_at = datetime.now()
            result.execution_time_seconds = (result.completed_at - start_time).total_seconds()

            self.statistics["completed_simulations"] += 1
            self.statistics["changes_tested"] += len(scenario.changes)
            self.statistics["blockers_found"] += len(result.blockers)

        except Exception as e:
            result.status = SimulationStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            self.statistics["failed_simulations"] += 1

        self.simulations[simulation_id] = result
        return result

    def _analyze_change(self, change: AccessChange, scenario: SimulationScenario) -> ImpactAnalysis:
        """Analyze the impact of a single change"""
        sod_conflicts = []
        sensitive_grants = []
        privilege_escalations = []
        new_permissions = []
        removed_permissions = []
        warnings = []
        blockers = []
        recommendations = []

        affected_users = 1 if change.target_user else len(change.target_users)
        affected_transactions = random.sample(self._demo_transactions, min(5, len(self._demo_transactions)))

        # Simulate SoD check
        if scenario.include_sod_check and change.change_type in [ChangeType.ADD_ROLE, ChangeType.ADD_PERMISSION]:
            # Randomly generate some SoD conflicts for demo
            if random.random() > 0.6:
                conflict = random.choice(self._demo_sod_rules)
                sod_conflicts.append({
                    "rule_id": f"SOD-{random.randint(100, 999)}",
                    "function1": conflict["function1"],
                    "function2": conflict["function2"],
                    "risk_level": random.choice(["HIGH", "CRITICAL"]),
                    "mitigation_required": True
                })
                warnings.append(f"SoD conflict: {conflict['function1']} vs {conflict['function2']}")

        # Simulate sensitive access check
        if scenario.include_sensitive_check:
            sensitive_tcodes = ["SU01", "SU10", "PFCG", "SE38", "SE16", "SM37"]
            for tcode in affected_transactions:
                if tcode in sensitive_tcodes and random.random() > 0.5:
                    sensitive_grants.append({
                        "transaction": tcode,
                        "sensitivity_level": "HIGH",
                        "requires_approval": True
                    })

        # Simulate privilege escalation detection
        if change.change_type == ChangeType.ADD_ROLE:
            if "ADMIN" in change.role_name.upper() or "ALL" in change.role_id.upper():
                privilege_escalations.append({
                    "type": "Admin Role Assignment",
                    "risk": "HIGH",
                    "justification_required": True
                })
                blockers.append(f"Privilege escalation detected: {change.role_name}")

        # Generate permissions
        new_permissions = [f"P-{random.randint(1000, 9999)}" for _ in range(random.randint(3, 10))]

        if change.change_type == ChangeType.REMOVE_ROLE:
            removed_permissions = [f"P-{random.randint(1000, 9999)}" for _ in range(random.randint(3, 8))]

        # Determine impact level
        impact_level = ImpactLevel.LOW
        if sod_conflicts:
            impact_level = ImpactLevel.HIGH
        if privilege_escalations:
            impact_level = ImpactLevel.CRITICAL
        if affected_users > 10:
            impact_level = ImpactLevel.MEDIUM if impact_level == ImpactLevel.LOW else impact_level

        # Generate recommendations
        if sod_conflicts:
            recommendations.append("Request mitigation control before proceeding")
        if sensitive_grants:
            recommendations.append("Ensure security approval is obtained")
        if affected_users > 50:
            recommendations.append("Consider phased rollout for large user groups")

        return ImpactAnalysis(
            change_id=change.change_id,
            impact_level=impact_level,
            affected_users=affected_users,
            affected_transactions=affected_transactions,
            sod_conflicts=sod_conflicts,
            sensitive_access_grants=sensitive_grants,
            privilege_escalations=privilege_escalations,
            new_permissions=new_permissions,
            removed_permissions=removed_permissions,
            unchanged_permissions=random.randint(10, 50),
            compliance_frameworks_affected=["SOX", "GDPR"] if sod_conflicts else [],
            audit_findings_risk=len(sod_conflicts) + len(sensitive_grants),
            recommendations=recommendations,
            warnings=warnings,
            blockers=blockers
        )

    def _execute_test(self, test: TestScenario, scenario: SimulationScenario) -> TestScenario:
        """Execute a single test scenario"""
        start = datetime.now()

        # Simulate test execution
        # In production, this would actually test against a sandbox
        permissions_used = [f"AUTH-{random.randint(100, 999)}" for _ in range(random.randint(1, 5))]

        # Simulate result (mostly pass for demo)
        if random.random() > 0.15:
            test.actual_result = test.expected_result
            test.error_message = ""
        else:
            test.actual_result = "failure" if test.expected_result == "success" else "success"
            test.error_message = f"Authorization check failed for {test.transaction_code}"

        test.permissions_used = permissions_used
        test.execution_time_ms = random.randint(50, 500)

        return test

    def get_simulation(self, simulation_id: str) -> Optional[SimulationResult]:
        """Get a simulation result by ID"""
        return self.simulations.get(simulation_id)

    def get_scenario(self, scenario_id: str) -> Optional[SimulationScenario]:
        """Get a scenario by ID"""
        return self.scenarios.get(scenario_id)

    def list_simulations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent simulations"""
        sims = list(self.simulations.values())[-limit:]
        return [
            {
                "simulation_id": s.simulation_id,
                "scenario_name": s.scenario.name,
                "status": s.status.value,
                "overall_impact": s.overall_impact.value,
                "can_proceed": s.can_proceed,
                "started_at": s.started_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "summary": {
                    "changes": s.total_changes,
                    "issues": s.changes_with_issues,
                    "tests_passed": s.tests_passed,
                    "tests_failed": s.tests_failed
                }
            }
            for s in sims
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get simulator statistics"""
        return {
            **self.statistics,
            "active_scenarios": len(self.scenarios),
            "pending_simulations": sum(1 for s in self.simulations.values() if s.status == SimulationStatus.PENDING)
        }


# Global simulator instance
pts_simulator = PTSSimulator()
