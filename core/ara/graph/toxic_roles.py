# Toxic Role Detection
# Identifies single roles that enable multiple forbidden business actions

"""
Toxic Role Detection for GOVERNEX+.

A toxic role is a single role (or minimal role set) that enables
multiple forbidden business actions through direct or indirect
privilege paths.

SAP GRC limitation: detects role pairs.
GOVERNEX+: detects role-centric risk concentration.

This enables:
- Proactive role remediation
- Role design improvement
- Risk concentration identification
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
class RoleToxicityScore:
    """
    Toxicity score for a role.

    Measures how dangerous a role is based on:
    - Number of forbidden actions enabled
    - Severity of patterns matched
    - Privilege breadth
    """
    role_id: str
    toxicity_score: float  # 0-100
    risk_concentration: float  # 0-1

    # Forbidden actions this role enables
    forbidden_actions_enabled: Set[str] = field(default_factory=set)

    # Patterns this role contributes to
    patterns_matched: List[str] = field(default_factory=list)

    # All actions reachable through this role
    total_actions: int = 0
    total_privileges: int = 0

    # Users affected
    users_with_role: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "toxicity_score": round(self.toxicity_score, 2),
            "risk_concentration": round(self.risk_concentration, 4),
            "forbidden_actions_enabled": list(self.forbidden_actions_enabled),
            "patterns_matched": self.patterns_matched,
            "total_actions": self.total_actions,
            "total_privileges": self.total_privileges,
            "users_with_role": self.users_with_role,
        }


@dataclass
class ToxicRoleFinding:
    """
    Finding for a toxic role.

    Contains full analysis of why a role is considered toxic
    and recommendations for remediation.
    """
    finding_id: str
    role_id: str
    toxicity_score: RoleToxicityScore
    severity: PatternSeverity
    risk_score: int

    # Patterns fully enabled by this role alone
    fully_enabled_patterns: List[RiskPattern] = field(default_factory=list)

    # Patterns this role contributes to (in combination with others)
    contributing_patterns: List[RiskPattern] = field(default_factory=list)

    # Actions breakdown
    sensitive_actions: Set[str] = field(default_factory=set)
    conflicting_action_pairs: List[Tuple[str, str]] = field(default_factory=list)

    # Remediation
    remediation_recommendations: List[str] = field(default_factory=list)
    suggested_role_split: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "role_id": self.role_id,
            "toxicity_score": self.toxicity_score.to_dict(),
            "severity": self.severity.value,
            "risk_score": self.risk_score,
            "fully_enabled_patterns": [p.pattern_id for p in self.fully_enabled_patterns],
            "contributing_patterns": [p.pattern_id for p in self.contributing_patterns],
            "sensitive_actions": list(self.sensitive_actions),
            "conflicting_action_pairs": [
                {"action1": a1, "action2": a2} for a1, a2 in self.conflicting_action_pairs
            ],
            "remediation_recommendations": self.remediation_recommendations,
            "suggested_role_split": self.suggested_role_split,
            "detected_at": self.detected_at.isoformat(),
        }


class ToxicRoleDetector:
    """
    Detects toxic roles in the access graph.

    A role is toxic if it alone enables:
    - Multiple forbidden business actions
    - One or more complete risk patterns
    - Excessive privilege concentration

    This goes beyond SAP GRC which only detects role pairs.
    """

    # Thresholds
    MIN_TOXICITY_SCORE = 50  # Minimum score to report
    HIGH_TOXICITY_THRESHOLD = 75
    CRITICAL_TOXICITY_THRESHOLD = 90

    def __init__(
        self,
        graph: SoDGraph,
        pattern_library: Optional[RiskPatternLibrary] = None
    ):
        """
        Initialize detector.

        Args:
            graph: SoD graph with access relationships
            pattern_library: Library of risk patterns
        """
        self.graph = graph
        self.pattern_library = pattern_library or RiskPatternLibrary()
        self._finding_counter = 0

    def calculate_toxicity_score(self, role_id: str) -> RoleToxicityScore:
        """
        Calculate toxicity score for a role.

        Args:
            role_id: Role identifier

        Returns:
            RoleToxicityScore with detailed metrics
        """
        # Get all actions reachable through this role
        role_actions = self.graph.get_role_actions(role_id)
        role_privileges = self.graph.get_role_privileges(role_id)

        score = RoleToxicityScore(
            role_id=role_id,
            toxicity_score=0,
            risk_concentration=0,
            total_actions=len(role_actions),
            total_privileges=len(role_privileges),
        )

        # Count users with this role
        score.users_with_role = len(self.graph.get_role_users(role_id))

        # Find forbidden actions this role enables
        all_forbidden_actions = set()
        for pattern in self.pattern_library.get_active_patterns():
            all_forbidden_actions.update(pattern.forbidden_actions)

        score.forbidden_actions_enabled = role_actions & all_forbidden_actions

        # Find patterns this role matches
        for pattern in self.pattern_library.get_active_patterns():
            if pattern.forbidden_actions.issubset(role_actions):
                score.patterns_matched.append(pattern.pattern_id)

        # Calculate toxicity score
        base_score = 0

        # Score for forbidden actions (up to 40 points)
        forbidden_ratio = len(score.forbidden_actions_enabled) / max(len(all_forbidden_actions), 1)
        base_score += forbidden_ratio * 40

        # Score for patterns matched (up to 40 points)
        if score.patterns_matched:
            pattern_score = min(len(score.patterns_matched) * 15, 40)
            base_score += pattern_score

        # Score for privilege breadth (up to 20 points)
        if len(role_privileges) > 50:
            base_score += 20
        elif len(role_privileges) > 25:
            base_score += 10
        elif len(role_privileges) > 10:
            base_score += 5

        score.toxicity_score = min(base_score, 100)

        # Risk concentration
        if score.total_actions > 0:
            score.risk_concentration = len(score.forbidden_actions_enabled) / score.total_actions

        return score

    def find_toxic_roles(
        self,
        min_score: Optional[float] = None
    ) -> List[ToxicRoleFinding]:
        """
        Find all toxic roles in the graph.

        Args:
            min_score: Minimum toxicity score to report (default: MIN_TOXICITY_SCORE)

        Returns:
            List of ToxicRoleFinding sorted by toxicity score
        """
        min_score = min_score or self.MIN_TOXICITY_SCORE
        findings = []

        role_nodes = self.graph.get_nodes_by_type(NodeType.ROLE)

        for node in role_nodes:
            toxicity = self.calculate_toxicity_score(node.node_id)

            if toxicity.toxicity_score >= min_score:
                finding = self._create_finding(node.node_id, toxicity)
                findings.append(finding)

        # Sort by toxicity score descending
        findings.sort(key=lambda f: f.toxicity_score.toxicity_score, reverse=True)

        return findings

    def analyze_role(self, role_id: str) -> Optional[ToxicRoleFinding]:
        """
        Perform detailed analysis of a specific role.

        Args:
            role_id: Role identifier

        Returns:
            ToxicRoleFinding with full analysis
        """
        toxicity = self.calculate_toxicity_score(role_id)
        return self._create_finding(role_id, toxicity)

    def _create_finding(
        self,
        role_id: str,
        toxicity: RoleToxicityScore
    ) -> ToxicRoleFinding:
        """Create a detailed finding for a toxic role."""
        self._finding_counter += 1
        finding_id = f"TOXIC-{role_id}-{self._finding_counter}"

        # Determine severity
        if toxicity.toxicity_score >= self.CRITICAL_TOXICITY_THRESHOLD:
            severity = PatternSeverity.CRITICAL
            risk_score = 95
        elif toxicity.toxicity_score >= self.HIGH_TOXICITY_THRESHOLD:
            severity = PatternSeverity.HIGH
            risk_score = 80
        elif toxicity.toxicity_score >= self.MIN_TOXICITY_SCORE:
            severity = PatternSeverity.MEDIUM
            risk_score = 60
        else:
            severity = PatternSeverity.LOW
            risk_score = 40

        finding = ToxicRoleFinding(
            finding_id=finding_id,
            role_id=role_id,
            toxicity_score=toxicity,
            severity=severity,
            risk_score=risk_score,
        )

        # Find patterns fully enabled vs contributing
        role_actions = self.graph.get_role_actions(role_id)

        for pattern in self.pattern_library.get_active_patterns():
            if pattern.forbidden_actions.issubset(role_actions):
                finding.fully_enabled_patterns.append(pattern)
            elif pattern.forbidden_actions & role_actions:
                finding.contributing_patterns.append(pattern)

        # Find conflicting action pairs within this role
        forbidden_actions_list = list(toxicity.forbidden_actions_enabled)
        for i, action1 in enumerate(forbidden_actions_list):
            for action2 in forbidden_actions_list[i + 1:]:
                # Check if these form a conflict
                for pattern in self.pattern_library.get_active_patterns():
                    if {action1, action2}.issubset(pattern.forbidden_actions):
                        finding.conflicting_action_pairs.append((action1, action2))
                        break

        # Identify sensitive actions
        finding.sensitive_actions = toxicity.forbidden_actions_enabled

        # Generate remediation recommendations
        finding.remediation_recommendations = self._generate_recommendations(finding)

        # Suggest role split
        finding.suggested_role_split = self._suggest_role_split(role_id, finding)

        return finding

    def _generate_recommendations(self, finding: ToxicRoleFinding) -> List[str]:
        """Generate remediation recommendations."""
        recommendations = []

        if finding.fully_enabled_patterns:
            recommendations.append(
                f"CRITICAL: Role '{finding.role_id}' enables complete risk patterns. "
                "Split immediately into separate roles."
            )

        if len(finding.conflicting_action_pairs) > 0:
            recommendations.append(
                f"Role contains {len(finding.conflicting_action_pairs)} conflicting action pairs. "
                "Redesign role to separate conflicting functions."
            )

        if finding.toxicity_score.users_with_role > 10:
            recommendations.append(
                f"Role is assigned to {finding.toxicity_score.users_with_role} users. "
                "Consider creating specialized sub-roles."
            )

        if finding.toxicity_score.total_privileges > 50:
            recommendations.append(
                f"Role has {finding.toxicity_score.total_privileges} privileges. "
                "Review for privilege creep and remove unused authorizations."
            )

        recommendations.append(
            "Document business justification if role cannot be split."
        )

        return recommendations

    def _suggest_role_split(
        self,
        role_id: str,
        finding: ToxicRoleFinding
    ) -> List[Dict[str, Any]]:
        """Suggest how to split a toxic role."""
        suggestions = []

        if not finding.fully_enabled_patterns:
            return suggestions

        # Group forbidden actions by pattern business process
        process_actions: Dict[str, Set[str]] = {}

        for pattern in finding.fully_enabled_patterns:
            process = pattern.business_process or "General"
            if process not in process_actions:
                process_actions[process] = set()
            process_actions[process].update(pattern.forbidden_actions)

        # Suggest split by business process
        for i, (process, actions) in enumerate(process_actions.items()):
            suggestions.append({
                "new_role_name": f"{role_id}_{process.replace(' ', '_').upper()}_{i + 1}",
                "business_process": process,
                "actions_to_include": list(actions),
                "actions_to_exclude": list(
                    finding.toxicity_score.forbidden_actions_enabled - actions
                ),
                "rationale": f"Separate {process} functions into dedicated role",
            })

        return suggestions

    def get_toxic_role_summary(self) -> Dict[str, Any]:
        """Get summary of all toxic roles."""
        findings = self.find_toxic_roles(min_score=0)

        total_roles = len(self.graph.get_nodes_by_type(NodeType.ROLE))
        toxic_roles = len([f for f in findings if f.toxicity_score.toxicity_score >= self.MIN_TOXICITY_SCORE])
        critical_roles = len([f for f in findings if f.severity == PatternSeverity.CRITICAL])

        # Calculate total user exposure
        total_users_affected = sum(
            f.toxicity_score.users_with_role
            for f in findings
            if f.toxicity_score.toxicity_score >= self.MIN_TOXICITY_SCORE
        )

        # Average toxicity
        if findings:
            avg_toxicity = sum(f.toxicity_score.toxicity_score for f in findings) / len(findings)
        else:
            avg_toxicity = 0

        # Most toxic roles
        top_toxic = [
            {
                "role_id": f.role_id,
                "toxicity_score": round(f.toxicity_score.toxicity_score, 2),
                "patterns_matched": len(f.fully_enabled_patterns),
                "users_affected": f.toxicity_score.users_with_role,
            }
            for f in findings[:10]
        ]

        return {
            "total_roles": total_roles,
            "toxic_roles": toxic_roles,
            "critical_roles": critical_roles,
            "total_users_affected": total_users_affected,
            "average_toxicity": round(avg_toxicity, 2),
            "top_toxic_roles": top_toxic,
        }
