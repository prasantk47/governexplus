# Graph-Based SoD Detection Engine
# Detects indirect, multi-step, transitive conflicts

"""
Graph-Based SoD Detection.

What SAP GRC detects:
    User has Role A AND Role B -> SoD conflict

What GOVERNEX+ detects:
    User -> Role A -> FK01 -> CREATE_VENDOR
    User -> Role B -> F-53 -> EXECUTE_PAYMENT
    = Complete fraud path (even if roles seem harmless individually)

This catches:
- Indirect SoD violations
- Multi-role escalation paths
- "Harmless alone, dangerous together" access
- Control bypass chains
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime
import logging

from .sod_graph import SoDGraph, NodeType
from .risk_patterns import (
    RiskPattern,
    RiskPatternLibrary,
    PatternSeverity,
)

logger = logging.getLogger(__name__)


@dataclass
class PathExplanation:
    """
    Explanation of how a user reaches a forbidden action.

    Provides audit trail for each violation path.
    """
    action: str
    path: List[str]
    path_description: str
    roles_involved: List[str]
    tcodes_involved: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "path": self.path,
            "path_description": self.path_description,
            "roles_involved": self.roles_involved,
            "tcodes_involved": self.tcodes_involved,
        }


@dataclass
class GraphSoDFinding:
    """
    A graph-based SoD finding.

    Contains:
    - Pattern that was matched
    - Path explanations for each forbidden action
    - Risk score and severity
    - Remediation hints
    """
    finding_id: str
    user_id: str
    pattern: RiskPattern
    severity: PatternSeverity
    risk_score: int

    # Paths explaining how user reaches each forbidden action
    path_explanations: List[PathExplanation] = field(default_factory=list)

    # Roles and tcodes involved in the violation
    roles_involved: Set[str] = field(default_factory=set)
    tcodes_involved: Set[str] = field(default_factory=set)

    # Remediation
    remediation_options: List[str] = field(default_factory=list)

    # Metadata
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "user_id": self.user_id,
            "pattern_id": self.pattern.pattern_id,
            "pattern_name": self.pattern.name,
            "severity": self.severity.value,
            "risk_score": self.risk_score,
            "path_explanations": [p.to_dict() for p in self.path_explanations],
            "roles_involved": list(self.roles_involved),
            "tcodes_involved": list(self.tcodes_involved),
            "remediation_options": self.remediation_options,
            "detected_at": self.detected_at.isoformat(),
            "business_process": self.pattern.business_process,
            "control_objective": self.pattern.control_objective,
        }


class GraphSoDDetector:
    """
    Graph-based SoD detection engine.

    Uses graph traversal to detect multi-step, transitive conflicts
    that pairwise rule engines cannot find.

    Example:
        User → Role A → FK01 → CREATE_VENDOR
        User → Role B → F-53 → EXECUTE_PAYMENT

        SAP GRC sees: two roles
        GOVERNEX+ sees: one fraud path
    """

    def __init__(
        self,
        graph: SoDGraph,
        pattern_library: Optional[RiskPatternLibrary] = None
    ):
        """
        Initialize detector.

        Args:
            graph: SoD graph with access relationships
            pattern_library: Library of risk patterns (uses default if not provided)
        """
        self.graph = graph
        self.pattern_library = pattern_library or RiskPatternLibrary()
        self._finding_counter = 0

    def detect_user(self, user_id: str) -> List[GraphSoDFinding]:
        """
        Detect all SoD violations for a user.

        Args:
            user_id: User identifier

        Returns:
            List of GraphSoDFinding for all matched patterns
        """
        findings = []

        # Get all reachable actions for this user
        reachable_actions = self.graph.get_user_actions(user_id)

        if not reachable_actions:
            logger.debug(f"No reachable actions for user {user_id}")
            return findings

        # Check each active pattern
        for pattern in self.pattern_library.get_active_patterns():
            if pattern.forbidden_actions.issubset(reachable_actions):
                finding = self._create_finding(user_id, pattern)
                findings.append(finding)

        return findings

    def detect_all_users(self) -> Dict[str, List[GraphSoDFinding]]:
        """
        Detect SoD violations for all users in the graph.

        Returns:
            Dictionary mapping user_id to list of findings
        """
        results = {}
        user_nodes = self.graph.get_nodes_by_type(NodeType.USER)

        for node in user_nodes:
            findings = self.detect_user(node.node_id)
            if findings:
                results[node.node_id] = findings

        return results

    def detect_with_pattern(
        self,
        user_id: str,
        pattern: RiskPattern
    ) -> Optional[GraphSoDFinding]:
        """
        Check if user matches a specific pattern.

        Args:
            user_id: User identifier
            pattern: Pattern to check

        Returns:
            Finding if matched, None otherwise
        """
        reachable_actions = self.graph.get_user_actions(user_id)

        if pattern.forbidden_actions.issubset(reachable_actions):
            return self._create_finding(user_id, pattern)

        return None

    def simulate_access_change(
        self,
        user_id: str,
        add_roles: Optional[List[str]] = None,
        remove_roles: Optional[List[str]] = None
    ) -> Tuple[List[GraphSoDFinding], List[GraphSoDFinding]]:
        """
        Simulate impact of role changes on SoD violations.

        Args:
            user_id: User identifier
            add_roles: Roles to be added
            remove_roles: Roles to be removed

        Returns:
            Tuple of (new_violations, resolved_violations)
        """
        # Get current violations
        current_findings = self.detect_user(user_id)
        current_patterns = {f.pattern.pattern_id for f in current_findings}

        # Simulate changes by temporarily modifying graph
        # (This is a simplified simulation - in production, use a copy of the graph)

        # Calculate new reachable actions
        current_roles = self.graph.get_user_roles(user_id)
        simulated_roles = current_roles.copy()

        if add_roles:
            simulated_roles.update(add_roles)
        if remove_roles:
            simulated_roles -= set(remove_roles)

        # Get actions from simulated role set
        simulated_actions = set()
        for role in simulated_roles:
            simulated_actions.update(self.graph.get_role_actions(role))

        # Find patterns that would match
        simulated_patterns = set()
        simulated_findings = []

        for pattern in self.pattern_library.get_active_patterns():
            if pattern.forbidden_actions.issubset(simulated_actions):
                simulated_patterns.add(pattern.pattern_id)
                if pattern.pattern_id not in current_patterns:
                    # New violation
                    finding = self._create_finding(user_id, pattern)
                    simulated_findings.append(finding)

        # Find resolved patterns
        resolved_findings = [
            f for f in current_findings
            if f.pattern.pattern_id not in simulated_patterns
        ]

        return simulated_findings, resolved_findings

    def _create_finding(
        self,
        user_id: str,
        pattern: RiskPattern
    ) -> GraphSoDFinding:
        """Create a detailed finding for a matched pattern."""
        self._finding_counter += 1
        finding_id = f"GRAPH-{user_id}-{pattern.pattern_id}-{self._finding_counter}"

        finding = GraphSoDFinding(
            finding_id=finding_id,
            user_id=user_id,
            pattern=pattern,
            severity=pattern.severity,
            risk_score=pattern.base_risk_score,
        )

        # Build path explanations for each forbidden action
        for action in pattern.forbidden_actions:
            path_explanation = self._explain_path(user_id, action)
            if path_explanation:
                finding.path_explanations.append(path_explanation)
                finding.roles_involved.update(path_explanation.roles_involved)
                finding.tcodes_involved.update(path_explanation.tcodes_involved)

        # Generate remediation options
        finding.remediation_options = self._generate_remediation(finding)

        return finding

    def _explain_path(self, user_id: str, action: str) -> Optional[PathExplanation]:
        """Explain how a user reaches a specific action."""
        path = self.graph.find_shortest_path(user_id, action)

        if not path:
            return None

        # Extract roles and tcodes from path
        roles_involved = []
        tcodes_involved = []

        for node_id in path:
            node = self.graph.get_node(node_id)
            if node:
                if node.node_type == NodeType.ROLE:
                    roles_involved.append(node_id)
                elif node.node_type == NodeType.PRIVILEGE:
                    tcodes_involved.append(node_id)

        # Build description
        path_parts = []
        for i, node_id in enumerate(path):
            node = self.graph.get_node(node_id)
            if node:
                if node.node_type == NodeType.USER:
                    path_parts.append(f"User {node_id}")
                elif node.node_type == NodeType.ROLE:
                    path_parts.append(f"Role '{node_id}'")
                elif node.node_type == NodeType.PRIVILEGE:
                    path_parts.append(f"TCode {node_id}")
                elif node.node_type == NodeType.ACTION:
                    path_parts.append(f"Action '{node_id}'")

        path_description = " → ".join(path_parts)

        return PathExplanation(
            action=action,
            path=path,
            path_description=path_description,
            roles_involved=roles_involved,
            tcodes_involved=tcodes_involved,
        )

    def _generate_remediation(self, finding: GraphSoDFinding) -> List[str]:
        """Generate remediation options for a finding."""
        options = []

        roles = list(finding.roles_involved)

        if len(roles) >= 2:
            options.append(f"Remove role '{roles[0]}' to eliminate {list(finding.pattern.forbidden_actions)[0]} capability")
            options.append(f"Remove role '{roles[1]}' to eliminate {list(finding.pattern.forbidden_actions)[-1]} capability")

        if len(roles) == 1:
            options.append(f"Split role '{roles[0]}' into separate roles for each business function")

        options.append("Implement compensating control (dual approval, enhanced monitoring)")
        options.append("Apply mitigation control to document business justification")

        return options

    def get_violation_summary(self) -> Dict[str, Any]:
        """Get summary statistics of all violations."""
        all_findings = self.detect_all_users()

        total_findings = sum(len(f) for f in all_findings.values())
        users_with_violations = len(all_findings)

        severity_counts = {
            PatternSeverity.CRITICAL.value: 0,
            PatternSeverity.HIGH.value: 0,
            PatternSeverity.MEDIUM.value: 0,
            PatternSeverity.LOW.value: 0,
        }

        pattern_counts = {}
        role_violation_counts = {}

        for user_findings in all_findings.values():
            for finding in user_findings:
                severity_counts[finding.severity.value] += 1

                pattern_id = finding.pattern.pattern_id
                pattern_counts[pattern_id] = pattern_counts.get(pattern_id, 0) + 1

                for role in finding.roles_involved:
                    role_violation_counts[role] = role_violation_counts.get(role, 0) + 1

        # Top violated patterns
        top_patterns = sorted(
            pattern_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Top contributing roles
        top_roles = sorted(
            role_violation_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "total_violations": total_findings,
            "users_with_violations": users_with_violations,
            "severity_breakdown": severity_counts,
            "top_violated_patterns": [
                {"pattern_id": p, "count": c} for p, c in top_patterns
            ],
            "top_contributing_roles": [
                {"role": r, "violation_count": c} for r, c in top_roles
            ],
        }
