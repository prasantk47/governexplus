# Auto-Generated SoD Rules from Graphs
# Discovers SoD rules automatically from access structure analysis

"""
Auto SoD Rule Generation for GOVERNEX+.

Manual SoD rule maintenance is:
- Expensive
- Incomplete
- Reactive

GOVERNEX+ discovers SoD rules automatically from:
- Graph analysis of actual access structures
- Historical incident patterns
- Toxic role decomposition

Generated rules are marked as DRAFT and require governance approval.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import logging
import hashlib

from .sod_graph import SoDGraph, NodeType
from .risk_patterns import PatternSeverity, PatternType
from .toxic_roles import ToxicRoleFinding

logger = logging.getLogger(__name__)


class RuleStatus(Enum):
    """Status of generated rules."""
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ACTIVE = "ACTIVE"


class RuleSource(Enum):
    """Source of rule generation."""
    GRAPH_DISCOVERY = "GRAPH_DISCOVERY"
    TOXIC_ROLE_SPLIT = "TOXIC_ROLE_SPLIT"
    INCIDENT_ANALYSIS = "INCIDENT_ANALYSIS"
    PATTERN_EXPANSION = "PATTERN_EXPANSION"


@dataclass
class RuleGenerationConfig:
    """Configuration for rule generation."""
    # Minimum confidence to generate a rule
    min_confidence: float = 0.7

    # Include rules for role-level conflicts
    generate_role_rules: bool = True

    # Include rules for action-level conflicts
    generate_action_rules: bool = True

    # Maximum actions per rule
    max_actions_per_rule: int = 4

    # Auto-activate rules above this confidence
    auto_activate_threshold: float = 0.95


@dataclass
class GeneratedSoDRule:
    """
    An auto-generated SoD rule.

    Contains:
    - Rule definition
    - Generation source and rationale
    - Confidence score
    - Review status
    """
    rule_id: str
    name: str
    description: str

    # Rule definition
    rule_type: PatternType = PatternType.SOD
    severity: PatternSeverity = PatternSeverity.HIGH

    # Conflicting elements
    conflicting_actions: Set[str] = field(default_factory=set)
    conflicting_roles: Set[str] = field(default_factory=set)
    conflicting_tcodes: Set[str] = field(default_factory=set)

    # Risk scoring
    base_risk_score: int = 75

    # Generation metadata
    source: RuleSource = RuleSource.GRAPH_DISCOVERY
    confidence: float = 0.0
    generation_rationale: str = ""
    supporting_evidence: List[str] = field(default_factory=list)

    # Business context
    business_process: str = ""
    control_objective: str = ""

    # Status
    status: RuleStatus = RuleStatus.DRAFT
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type.value,
            "severity": self.severity.value,
            "conflicting_actions": list(self.conflicting_actions),
            "conflicting_roles": list(self.conflicting_roles),
            "conflicting_tcodes": list(self.conflicting_tcodes),
            "base_risk_score": self.base_risk_score,
            "source": self.source.value,
            "confidence": round(self.confidence, 4),
            "generation_rationale": self.generation_rationale,
            "supporting_evidence": self.supporting_evidence,
            "business_process": self.business_process,
            "control_objective": self.control_objective,
            "status": self.status.value,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat(),
        }

    def to_yaml_dict(self) -> Dict[str, Any]:
        """Convert to YAML-serializable format for rule export."""
        return {
            "id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "type": self.rule_type.value,
            "severity": self.severity.value,
            "base_risk_score": self.base_risk_score,
            "conditions": {
                "all_of": [
                    {"action": action} for action in self.conflicting_actions
                ]
            },
            "business_process": self.business_process,
            "control_objective": self.control_objective,
            "source": self.source.value,
            "status": self.status.value,
        }


class SoDRuleGenerator:
    """
    Generates SoD rules from graph analysis.

    Discovery methods:
    1. Toxic role decomposition - split toxic roles into conflict rules
    2. Action co-occurrence - find frequently combined dangerous actions
    3. Pattern expansion - extend existing patterns to related actions

    All generated rules require governance approval before activation.
    """

    def __init__(
        self,
        graph: SoDGraph,
        config: Optional[RuleGenerationConfig] = None
    ):
        """
        Initialize rule generator.

        Args:
            graph: SoD graph with access relationships
            config: Generation configuration
        """
        self.graph = graph
        self.config = config or RuleGenerationConfig()
        self._rule_counter = 0

    def generate_from_toxic_roles(
        self,
        toxic_findings: List[ToxicRoleFinding]
    ) -> List[GeneratedSoDRule]:
        """
        Generate SoD rules from toxic role findings.

        For each toxic role that enables multiple conflicting actions,
        generate a rule capturing that conflict pattern.

        Args:
            toxic_findings: List of toxic role findings

        Returns:
            List of generated rules
        """
        rules = []

        for finding in toxic_findings:
            if not finding.conflicting_action_pairs:
                continue

            # Generate rule for each conflicting pair
            for action1, action2 in finding.conflicting_action_pairs:
                rule = self._create_rule_from_actions(
                    actions={action1, action2},
                    source=RuleSource.TOXIC_ROLE_SPLIT,
                    rationale=f"Discovered in toxic role '{finding.role_id}'",
                    evidence=[
                        f"Role {finding.role_id} toxicity score: {finding.toxicity_score.toxicity_score:.1f}",
                        f"Role enables both {action1} and {action2}",
                        f"Users affected: {finding.toxicity_score.users_with_role}",
                    ],
                    confidence=0.85,
                )
                rules.append(rule)

        return self._deduplicate_rules(rules)

    def generate_from_action_analysis(self) -> List[GeneratedSoDRule]:
        """
        Generate rules by analyzing action co-occurrence patterns.

        Finds actions that frequently appear together in roles
        and could represent undocumented SoD conflicts.

        Returns:
            List of generated rules
        """
        rules = []

        # Get all action nodes
        action_nodes = self.graph.get_nodes_by_type(NodeType.ACTION)
        actions = [n.node_id for n in action_nodes]

        # Build action co-occurrence matrix
        # (actions that are reachable from the same roles)
        action_roles: Dict[str, Set[str]] = {}

        for action in actions:
            ancestors = self.graph.get_ancestors(action)
            action_roles[action] = {
                a for a in ancestors
                if self.graph.get_node(a) and
                   self.graph.get_node(a).node_type == NodeType.ROLE
            }

        # Find action pairs that share many roles
        # (indicating they are often granted together)
        for i, action1 in enumerate(actions):
            for action2 in actions[i + 1:]:
                shared_roles = action_roles.get(action1, set()) & action_roles.get(action2, set())

                if len(shared_roles) >= 3:  # Co-occur in 3+ roles
                    # Check if these look like a potential conflict
                    # (This is a simplified heuristic - in production, use domain knowledge)
                    if self._looks_like_conflict(action1, action2):
                        confidence = min(len(shared_roles) / 10, 0.9)

                        rule = self._create_rule_from_actions(
                            actions={action1, action2},
                            source=RuleSource.GRAPH_DISCOVERY,
                            rationale=f"Actions frequently combined in {len(shared_roles)} roles",
                            evidence=[
                                f"Shared roles: {', '.join(list(shared_roles)[:5])}",
                            ],
                            confidence=confidence,
                        )
                        rules.append(rule)

        return self._deduplicate_rules(rules)

    def generate_from_role_analysis(self) -> List[GeneratedSoDRule]:
        """
        Generate rules by analyzing role structures.

        Identifies roles that should never be combined based on
        the actions they enable.

        Returns:
            List of generated rules
        """
        if not self.config.generate_role_rules:
            return []

        rules = []

        # Get all roles
        role_nodes = self.graph.get_nodes_by_type(NodeType.ROLE)

        # Build role -> actions mapping
        role_actions: Dict[str, Set[str]] = {}
        for node in role_nodes:
            role_actions[node.node_id] = self.graph.get_role_actions(node.node_id)

        # Find role pairs where one role's actions conflict with another's
        roles = list(role_actions.keys())

        for i, role1 in enumerate(roles):
            for role2 in roles[i + 1:]:
                actions1 = role_actions.get(role1, set())
                actions2 = role_actions.get(role2, set())

                # Check for complementary danger
                # (role1 enables X, role2 enables Y, X+Y is dangerous)
                for action1 in actions1:
                    for action2 in actions2:
                        if action1 != action2 and self._looks_like_conflict(action1, action2):
                            rule = self._create_rule_from_roles(
                                roles={role1, role2},
                                actions={action1, action2},
                                source=RuleSource.GRAPH_DISCOVERY,
                                rationale=f"Roles grant complementary dangerous actions",
                                evidence=[
                                    f"Role {role1} enables {action1}",
                                    f"Role {role2} enables {action2}",
                                ],
                                confidence=0.75,
                            )
                            rules.append(rule)

        return self._deduplicate_rules(rules)

    def _create_rule_from_actions(
        self,
        actions: Set[str],
        source: RuleSource,
        rationale: str,
        evidence: List[str],
        confidence: float,
    ) -> GeneratedSoDRule:
        """Create a rule from conflicting actions."""
        self._rule_counter += 1

        # Generate deterministic rule ID
        action_hash = hashlib.md5(
            "-".join(sorted(actions)).encode()
        ).hexdigest()[:8]
        rule_id = f"AUTO-SOD-{action_hash}"

        # Determine severity based on action types
        severity = self._infer_severity(actions)

        name = f"Auto-discovered: {' + '.join(sorted(actions))}"
        description = f"Auto-generated rule detecting conflict between {', '.join(sorted(actions))}. {rationale}"

        return GeneratedSoDRule(
            rule_id=rule_id,
            name=name,
            description=description,
            conflicting_actions=actions,
            severity=severity,
            base_risk_score=self._calculate_risk_score(severity, confidence),
            source=source,
            confidence=confidence,
            generation_rationale=rationale,
            supporting_evidence=evidence,
            status=RuleStatus.DRAFT,
        )

    def _create_rule_from_roles(
        self,
        roles: Set[str],
        actions: Set[str],
        source: RuleSource,
        rationale: str,
        evidence: List[str],
        confidence: float,
    ) -> GeneratedSoDRule:
        """Create a rule from conflicting roles."""
        self._rule_counter += 1

        # Generate deterministic rule ID
        role_hash = hashlib.md5(
            "-".join(sorted(roles)).encode()
        ).hexdigest()[:8]
        rule_id = f"AUTO-ROLE-{role_hash}"

        severity = self._infer_severity(actions)

        name = f"Auto-discovered role conflict: {' + '.join(sorted(roles))}"
        description = f"Auto-generated rule: roles {', '.join(sorted(roles))} should not be combined. {rationale}"

        return GeneratedSoDRule(
            rule_id=rule_id,
            name=name,
            description=description,
            conflicting_roles=roles,
            conflicting_actions=actions,
            severity=severity,
            base_risk_score=self._calculate_risk_score(severity, confidence),
            source=source,
            confidence=confidence,
            generation_rationale=rationale,
            supporting_evidence=evidence,
            status=RuleStatus.DRAFT,
        )

    def _looks_like_conflict(self, action1: str, action2: str) -> bool:
        """
        Heuristic to determine if two actions might conflict.

        In production, this would use domain knowledge and ML.
        """
        # Keywords indicating potential conflicts
        create_keywords = {"CREATE", "ADD", "INSERT", "NEW", "HIRE"}
        approve_keywords = {"APPROVE", "RELEASE", "POST", "EXECUTE", "PAY"}
        modify_keywords = {"MODIFY", "CHANGE", "UPDATE", "EDIT"}
        delete_keywords = {"DELETE", "REMOVE", "RETIRE", "TERMINATE"}

        action1_upper = action1.upper()
        action2_upper = action2.upper()

        # Create + Approve conflict
        if any(k in action1_upper for k in create_keywords):
            if any(k in action2_upper for k in approve_keywords):
                return True

        if any(k in action2_upper for k in create_keywords):
            if any(k in action1_upper for k in approve_keywords):
                return True

        # Create + Delete conflict (lifecycle)
        if any(k in action1_upper for k in create_keywords):
            if any(k in action2_upper for k in delete_keywords):
                return True

        # Modify + Approve conflict
        if any(k in action1_upper for k in modify_keywords):
            if any(k in action2_upper for k in approve_keywords):
                return True

        # Same business object different operations
        # (simplified - in production, use actual business object mapping)
        words1 = set(action1_upper.replace("_", " ").split())
        words2 = set(action2_upper.replace("_", " ").split())
        common_objects = words1 & words2 - {"THE", "A", "AN", "AND", "OR"}

        if common_objects:
            # Same object, different operations
            ops1 = words1 - common_objects
            ops2 = words2 - common_objects
            if ops1 != ops2:
                return True

        return False

    def _infer_severity(self, actions: Set[str]) -> PatternSeverity:
        """Infer severity from action names."""
        action_str = " ".join(actions).upper()

        critical_keywords = {"PAYMENT", "PAYROLL", "BANK", "TRANSFER", "USER", "ROLE"}
        high_keywords = {"VENDOR", "CUSTOMER", "INVOICE", "PURCHASE", "CREDIT"}

        if any(k in action_str for k in critical_keywords):
            return PatternSeverity.CRITICAL

        if any(k in action_str for k in high_keywords):
            return PatternSeverity.HIGH

        return PatternSeverity.MEDIUM

    def _calculate_risk_score(
        self,
        severity: PatternSeverity,
        confidence: float
    ) -> int:
        """Calculate risk score based on severity and confidence."""
        base_scores = {
            PatternSeverity.CRITICAL: 95,
            PatternSeverity.HIGH: 80,
            PatternSeverity.MEDIUM: 60,
            PatternSeverity.LOW: 40,
        }

        base = base_scores.get(severity, 60)
        # Adjust by confidence
        return int(base * confidence)

    def _deduplicate_rules(
        self,
        rules: List[GeneratedSoDRule]
    ) -> List[GeneratedSoDRule]:
        """Remove duplicate rules based on conflicting elements."""
        seen = set()
        unique_rules = []

        for rule in rules:
            # Create key from sorted actions/roles
            key = tuple(sorted(rule.conflicting_actions)) + tuple(sorted(rule.conflicting_roles))

            if key not in seen:
                seen.add(key)
                unique_rules.append(rule)

        return unique_rules

    def generate_all(self) -> List[GeneratedSoDRule]:
        """
        Generate rules using all available methods.

        Returns:
            Combined list of generated rules
        """
        all_rules = []

        # From action analysis
        all_rules.extend(self.generate_from_action_analysis())

        # From role analysis
        all_rules.extend(self.generate_from_role_analysis())

        # Filter by minimum confidence
        filtered = [
            r for r in all_rules
            if r.confidence >= self.config.min_confidence
        ]

        return self._deduplicate_rules(filtered)

    def export_rules_yaml(self, rules: List[GeneratedSoDRule]) -> str:
        """Export rules to YAML format."""
        try:
            import yaml
            data = {
                "generated_rules": [r.to_yaml_dict() for r in rules],
                "generation_timestamp": datetime.now().isoformat(),
                "total_rules": len(rules),
            }
            return yaml.dump(data, default_flow_style=False, sort_keys=False)
        except ImportError:
            logger.warning("PyYAML not available")
            return ""

    def get_generation_summary(self, rules: List[GeneratedSoDRule]) -> Dict[str, Any]:
        """Get summary of generated rules."""
        by_source = {}
        by_severity = {}
        by_status = {}

        for rule in rules:
            by_source[rule.source.value] = by_source.get(rule.source.value, 0) + 1
            by_severity[rule.severity.value] = by_severity.get(rule.severity.value, 0) + 1
            by_status[rule.status.value] = by_status.get(rule.status.value, 0) + 1

        return {
            "total_generated": len(rules),
            "by_source": by_source,
            "by_severity": by_severity,
            "by_status": by_status,
            "avg_confidence": sum(r.confidence for r in rules) / len(rules) if rules else 0,
            "high_confidence_count": len([r for r in rules if r.confidence >= 0.8]),
        }
