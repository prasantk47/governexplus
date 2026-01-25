# Graph-Based SoD Detection Module
# Beyond pairwise rules - detecting multi-step, transitive conflicts

"""
Graph-Based SoD Detection for GOVERNEX+

SAP GRC limitation: Pairwise conflicts only, static SoD rules
GOVERNEX+ advantage: Detects multi-step, transitive conflicts

Key capabilities:
- Models access as directed graphs
- Detects indirect SoD violations
- Finds multi-role escalation paths
- Explains risk chains
- Discovers toxic roles automatically
"""

from .sod_graph import (
    SoDGraph,
    NodeType,
    EdgeType,
)

from .risk_patterns import (
    RiskPattern,
    RiskPatternLibrary,
    BUILTIN_RISK_PATTERNS,
)

from .sod_detector import (
    GraphSoDDetector,
    GraphSoDFinding,
    PathExplanation,
)

from .toxic_roles import (
    ToxicRoleDetector,
    ToxicRoleFinding,
    RoleToxicityScore,
)

from .rule_generator import (
    SoDRuleGenerator,
    GeneratedSoDRule,
    RuleGenerationConfig,
)

__all__ = [
    # Graph
    "SoDGraph",
    "NodeType",
    "EdgeType",
    # Patterns
    "RiskPattern",
    "RiskPatternLibrary",
    "BUILTIN_RISK_PATTERNS",
    # Detection
    "GraphSoDDetector",
    "GraphSoDFinding",
    "PathExplanation",
    # Toxic Roles
    "ToxicRoleDetector",
    "ToxicRoleFinding",
    "RoleToxicityScore",
    # Rule Generation
    "SoDRuleGenerator",
    "GeneratedSoDRule",
    "RuleGenerationConfig",
]
