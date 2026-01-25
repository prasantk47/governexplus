# Approval Module
# GOVERNEX+ Decision Intelligence Engine

"""
Approval System for GOVERNEX+.

SAP GRC (BRF+): "Route to whoever is configured."
GOVERNEX+: "Route to the right person, for the right reason,
            at the right risk level — and explain why."

This module replaces BRF+ with a modern decision intelligence platform:

1. Dynamic Approver Determination
   - Context-driven, not static
   - Risk-adaptive routing
   - Explainable decisions

2. BRF+ Rule Conversion
   - Import existing BRF+ logic
   - Convert to YAML DSL
   - Validate and simulate

3. AI-Assisted Optimization
   - Approver performance analysis
   - SLA prediction
   - Workload balancing

4. Complete Audit Trail
   - Decision path logging
   - Override tracking
   - Explainability for auditors
"""

from .models import (
    ApproverType,
    ApprovalStatus,
    ApprovalPriority,
    ApprovalRequest,
    Approver,
    ApprovalDecision,
    ApprovalRoute,
    ApprovalContext,
    RequestContext,
    RiskContext,
    UserContext,
)

from .engine import (
    ApproverDeterminationEngine,
    DeterminationResult,
    ApproverSelection,
)

from .rules import (
    ApprovalRule,
    RuleCondition,
    RuleLayer,
    ApprovalRuleEngine,
    ApproverSpec,
    BUILTIN_RULES,
)

from .converter import (
    BRFPlusConverter,
    BRFPlusRule,
    BRFPlusDecisionTable,
    ConversionResult,
)

from .workflow import (
    ApprovalWorkflow,
    WorkflowStage,
    WorkflowManager,
    WorkflowStatus,
)

from .optimizer import (
    ApproverOptimizer,
    OptimizationResult,
    ApproverScore,
    ApproverMetrics,
)

from .delegation import (
    DelegationManager,
    Delegation,
    DelegationType,
    DelegationStatus,
    ConflictOfInterest,
    ConflictType,
    FallbackResult,
)

from .explainability import (
    ExplainabilityEngine,
    ApprovalExplanation,
    Audience,
    ExplanationDepth,
    RiskFactor,
    WhatIfResult,
)

from .kpis import (
    ApprovalKPIEngine,
    KPIDefinition,
    KPIValue,
    KPICategory,
    SLABreach,
    BottleneckReport,
    APPROVAL_KPIS,
)

__all__ = [
    # Models
    "ApproverType",
    "ApprovalStatus",
    "ApprovalPriority",
    "ApprovalRequest",
    "Approver",
    "ApprovalDecision",
    "ApprovalRoute",
    "ApprovalContext",
    "RequestContext",
    "RiskContext",
    "UserContext",
    # Engine
    "ApproverDeterminationEngine",
    "DeterminationResult",
    "ApproverSelection",
    # Rules
    "ApprovalRule",
    "RuleCondition",
    "RuleLayer",
    "ApprovalRuleEngine",
    "ApproverSpec",
    "BUILTIN_RULES",
    # Converter
    "BRFPlusConverter",
    "BRFPlusRule",
    "BRFPlusDecisionTable",
    "ConversionResult",
    # Workflow
    "ApprovalWorkflow",
    "WorkflowStage",
    "WorkflowManager",
    "WorkflowStatus",
    # Optimizer
    "ApproverOptimizer",
    "OptimizationResult",
    "ApproverScore",
    "ApproverMetrics",
    # Delegation
    "DelegationManager",
    "Delegation",
    "DelegationType",
    "DelegationStatus",
    "ConflictOfInterest",
    "ConflictType",
    "FallbackResult",
    # Explainability
    "ExplainabilityEngine",
    "ApprovalExplanation",
    "Audience",
    "ExplanationDepth",
    "RiskFactor",
    "WhatIfResult",
    # KPIs
    "ApprovalKPIEngine",
    "KPIDefinition",
    "KPIValue",
    "KPICategory",
    "SLABreach",
    "BottleneckReport",
    "APPROVAL_KPIS",
]
