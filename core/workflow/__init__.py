# Universal Workflow Engine
# GOVERNEX+ Dynamic Workflow Orchestration

"""
Universal Workflow Engine for GOVERNEX+.

MSMP answers: "Which predefined workflow applies?"
GOVERNEX+ answers: "What is the safest, fastest, most accountable
                    workflow for THIS exact request — and why?"

This module provides:

1. Legacy MSMP Support (msmp.py)
   - SAP GRC-compatible workflow paths
   - Agent determination rules
   - Parallel path execution

2. Next-Gen Workflow Engine (NEW)
   - Process-agnostic
   - Policy-driven
   - Risk-adaptive
   - AI-ready
   - Fully auditable
"""

# Legacy MSMP support
from .msmp import (
    MSMPEngine, WorkflowPath, WorkflowStage, StageType,
    ParallelPath, AgentRule, AgentRuleType
)

# Core Models
from .models import (
    WorkflowContext,
    WorkflowStep,
    Workflow,
    WorkflowStatus,
    StepStatus,
    ProcessType,
    AccessType,
    TriggerType,
    ApproverTypeEnum,
    WorkflowDecision,
    StepDecision,
    WorkflowConfig,
    StepConfig,
    EscalationConfig,
)

# Policy Engine
from .policy import (
    PolicyEngine,
    PolicyRule,
    PolicyCondition,
    PolicyAction,
    PolicySet,
    RuleMatch,
    ActionType,
    ConditionOperator,
)

# Workflow Assembler
from .assembler import (
    WorkflowAssembler,
    AssemblyResult,
    AssemblyContext,
)

# Approver Resolver
from .resolver import (
    ApproverResolver,
    ResolverRegistry,
    ResolutionResult,
    ResolvedApprover,
    ApproverSource,
    LineManagerResolver,
    RoleOwnerResolver,
    ProcessOwnerResolver,
    StaticResolver,
)

# Workflow Executor
from .executor import (
    WorkflowExecutor,
    ExecutionResult,
    ExecutionEvent,
    EventType,
)

# SLA Manager
from .sla import (
    SLAManager,
    SLAConfig,
    SLAStatus,
    SLACheck,
    EscalationAction,
    EscalationTrigger,
)

# MSMP Converter
from .converter import (
    MSMPConverter,
    MSMPProcess,
    MSMPPath,
    MSMPStage,
    MSMPAgent,
    ConversionResult,
)

# Audit Engine
from .audit import (
    WorkflowAuditEngine,
    AuditEvent,
    AuditTrail,
    DecisionPath,
    AuditEventType,
)

# Provisioning Engine
from .provisioning import (
    ProvisioningEngine,
    ProvisioningGate,
    ProvisioningPolicy,
    ProvisioningStrategy,
    ProvisioningResult,
    ProvisioningGateResult,
    ProvisioningAction,
    AccessItem,
    AccessRequest,
    ItemStatus,
    # Pre-built policies
    MSMP_COMPATIBLE_POLICY,
    GOVERNEX_DEFAULT_POLICY,
    RISK_BASED_POLICY,
    FINANCIAL_SECTOR_POLICY,
)

# Event-Driven Re-Evaluation
from .events import (
    ReEvaluationEngine,
    EventBus,
    WorkflowEvent,
    EventType as WorkflowEventType,
    EventPriority,
    EventSource,
    ReEvaluationAction,
    ReEvaluationResult,
    # Handlers
    EventHandler,
    RiskChangeHandler,
    SLAEventHandler,
    FraudAlertHandler,
    UserEventHandler,
    ProvisioningEventHandler,
    # Integrations
    KafkaEventAdapter,
    WebhookEventAdapter,
    ScheduledReEvaluator,
    # Factory
    create_default_engine,
)

# Unified Orchestrator
from .orchestrator import (
    WorkflowOrchestrator,
    OrchestrationContext,
    OrchestrationResult,
    create_default_orchestrator,
    create_msmp_compatible_orchestrator,
    create_governex_orchestrator,
)

# Visual Workflow Builder (Zero-Code UI)
from .builder import (
    WorkflowBuilder,
    WorkflowCanvas,
    # Block Types
    BlockType,
    TriggerBlock,
    ConditionBlock,
    ConditionGroupBlock,
    ApprovalBlock,
    ApprovalGroupBlock,
    ProvisioningGateBlock,
    ActionBlock,
    SplitBlock,
    JoinBlock,
    # Enums for UI
    TriggerType as BuilderTriggerType,
    ConditionAttribute,
    ConditionOperator as BuilderConditionOperator,
    ApproverType as BuilderApproverType,
    ProvisioningMode,
    ActionType as BuilderActionType,
    # Templates
    create_simple_access_template,
    create_multi_approver_template,
    create_partial_provisioning_template,
)

# Workflow Simulator (Preview Panel)
from .simulator import (
    WorkflowSimulator,
    SimulationScenario,
    SimulationOutcome,
    quick_simulate,
    test_partial_provisioning,
)

# Notification Engine (Context-Aware Emails)
from .notifications import (
    NotificationEngine,
    NotificationContext,
    NotificationTemplate,
    NotificationRule,
    NotificationRuleEngine,
    RenderedNotification,
    TemplateRenderer,
    NotificationEvent,
    RecipientType,
    NotificationChannel,
    NotificationPriority,
    create_default_notification_engine,
    sample_context_for_testing,
)

__all__ = [
    # Legacy MSMP
    "MSMPEngine",
    "WorkflowPath",
    "WorkflowStage",
    "StageType",
    "ParallelPath",
    "AgentRule",
    "AgentRuleType",
    # Core Models
    "WorkflowContext",
    "WorkflowStep",
    "Workflow",
    "WorkflowStatus",
    "StepStatus",
    "ProcessType",
    "AccessType",
    "TriggerType",
    "ApproverTypeEnum",
    "WorkflowDecision",
    "StepDecision",
    "WorkflowConfig",
    "StepConfig",
    "EscalationConfig",
    # Policy
    "PolicyEngine",
    "PolicyRule",
    "PolicyCondition",
    "PolicyAction",
    "PolicySet",
    "RuleMatch",
    "ActionType",
    "ConditionOperator",
    # Assembler
    "WorkflowAssembler",
    "AssemblyResult",
    "AssemblyContext",
    # Resolver
    "ApproverResolver",
    "ResolverRegistry",
    "ResolutionResult",
    "ResolvedApprover",
    "ApproverSource",
    "LineManagerResolver",
    "RoleOwnerResolver",
    "ProcessOwnerResolver",
    "StaticResolver",
    # Executor
    "WorkflowExecutor",
    "ExecutionResult",
    "ExecutionEvent",
    "EventType",
    # SLA
    "SLAManager",
    "SLAConfig",
    "SLAStatus",
    "SLACheck",
    "EscalationAction",
    "EscalationTrigger",
    # Converter
    "MSMPConverter",
    "MSMPProcess",
    "MSMPPath",
    "MSMPStage",
    "MSMPAgent",
    "ConversionResult",
    # Audit
    "WorkflowAuditEngine",
    "AuditEvent",
    "AuditTrail",
    "DecisionPath",
    "AuditEventType",
    # Provisioning
    "ProvisioningEngine",
    "ProvisioningGate",
    "ProvisioningPolicy",
    "ProvisioningStrategy",
    "ProvisioningResult",
    "ProvisioningGateResult",
    "ProvisioningAction",
    "AccessItem",
    "AccessRequest",
    "ItemStatus",
    "MSMP_COMPATIBLE_POLICY",
    "GOVERNEX_DEFAULT_POLICY",
    "RISK_BASED_POLICY",
    "FINANCIAL_SECTOR_POLICY",
    # Events
    "ReEvaluationEngine",
    "EventBus",
    "WorkflowEvent",
    "WorkflowEventType",
    "EventPriority",
    "EventSource",
    "ReEvaluationAction",
    "ReEvaluationResult",
    "EventHandler",
    "RiskChangeHandler",
    "SLAEventHandler",
    "FraudAlertHandler",
    "UserEventHandler",
    "ProvisioningEventHandler",
    "KafkaEventAdapter",
    "WebhookEventAdapter",
    "ScheduledReEvaluator",
    "create_default_engine",
    # Orchestrator
    "WorkflowOrchestrator",
    "OrchestrationContext",
    "OrchestrationResult",
    "create_default_orchestrator",
    "create_msmp_compatible_orchestrator",
    "create_governex_orchestrator",
    # Builder
    "WorkflowBuilder",
    "WorkflowCanvas",
    "BlockType",
    "TriggerBlock",
    "ConditionBlock",
    "ConditionGroupBlock",
    "ApprovalBlock",
    "ApprovalGroupBlock",
    "ProvisioningGateBlock",
    "ActionBlock",
    "SplitBlock",
    "JoinBlock",
    "BuilderTriggerType",
    "ConditionAttribute",
    "BuilderConditionOperator",
    "BuilderApproverType",
    "ProvisioningMode",
    "BuilderActionType",
    "create_simple_access_template",
    "create_multi_approver_template",
    "create_partial_provisioning_template",
    # Simulator
    "WorkflowSimulator",
    "SimulationScenario",
    "SimulationOutcome",
    "quick_simulate",
    "test_partial_provisioning",
    # Notifications
    "NotificationEngine",
    "NotificationContext",
    "NotificationTemplate",
    "NotificationRule",
    "NotificationRuleEngine",
    "RenderedNotification",
    "TemplateRenderer",
    "NotificationEvent",
    "RecipientType",
    "NotificationChannel",
    "NotificationPriority",
    "create_default_notification_engine",
    "sample_context_for_testing",
]
