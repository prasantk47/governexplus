"""
Multi-Stage Multi-Path (MSMP) Workflow Engine

Implements SAP GRC-style MSMP workflow with:
- Parallel approval paths
- Dynamic agent (approver) determination
- BRF+ style rule engine
- Request splitting by system/role
- Automatic escalation
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import uuid


class StageType(Enum):
    """Types of workflow stages"""
    APPROVAL = "approval"           # Requires approve/reject decision
    REVIEW = "review"               # Review only, auto-advances
    NOTIFICATION = "notification"   # Notify only, auto-advances
    RISK_REVIEW = "risk_review"     # Security team risk review
    PROVISIONING = "provisioning"   # Auto-provisioning stage
    CUSTOM = "custom"               # Custom logic


class AgentRuleType(Enum):
    """Types of agent (approver) determination rules"""
    STATIC = "static"               # Fixed list of approvers
    MANAGER = "manager"             # Target user's manager
    ROLE_OWNER = "role_owner"       # Owner of requested role
    SECURITY_TEAM = "security_team" # Security team for risk level
    COST_CENTER_OWNER = "cost_center_owner"
    DEPARTMENT_HEAD = "department_head"
    CUSTOM_LOOKUP = "custom_lookup" # Custom table/logic
    EXPRESSION = "expression"       # Rule expression


@dataclass
class AgentRule:
    """
    Dynamic agent determination rule (BRF+ equivalent).
    Determines who should approve at each stage based on request attributes.
    """
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    rule_type: AgentRuleType = AgentRuleType.STATIC
    priority: int = 100  # Lower = higher priority

    # Conditions (when to apply this rule)
    conditions: Dict = field(default_factory=dict)
    # Example: {"risk_level": ["high", "critical"], "request_type": "new_access"}

    # Agent determination
    static_agents: List[str] = field(default_factory=list)  # For STATIC type
    agent_attribute: str = ""  # For lookup types (e.g., "manager_id")
    lookup_table: str = ""     # For CUSTOM_LOOKUP
    expression: str = ""       # For EXPRESSION type

    # Fallback
    fallback_agents: List[str] = field(default_factory=list)

    is_active: bool = True

    def evaluate_conditions(self, context: Dict) -> bool:
        """Check if this rule applies to the given context"""
        if not self.conditions:
            return True

        for key, expected in self.conditions.items():
            actual = context.get(key)
            if actual is None:
                return False

            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False

        return True

    def determine_agents(self, context: Dict) -> List[str]:
        """Determine agents based on rule type and context"""
        if self.rule_type == AgentRuleType.STATIC:
            return self.static_agents

        elif self.rule_type == AgentRuleType.MANAGER:
            manager_id = context.get("target_user_manager_id") or context.get("requester_manager_id")
            return [manager_id] if manager_id else self.fallback_agents

        elif self.rule_type == AgentRuleType.ROLE_OWNER:
            role_owners = context.get("role_owners", [])
            return role_owners if role_owners else self.fallback_agents

        elif self.rule_type == AgentRuleType.SECURITY_TEAM:
            return context.get("security_team", self.fallback_agents)

        elif self.rule_type == AgentRuleType.COST_CENTER_OWNER:
            cc_owner = context.get("cost_center_owner")
            return [cc_owner] if cc_owner else self.fallback_agents

        elif self.rule_type == AgentRuleType.DEPARTMENT_HEAD:
            dept_head = context.get("department_head")
            return [dept_head] if dept_head else self.fallback_agents

        elif self.rule_type == AgentRuleType.EXPRESSION:
            # Simple expression evaluation
            return self._evaluate_expression(context)

        return self.fallback_agents

    def _evaluate_expression(self, context: Dict) -> List[str]:
        """Evaluate rule expression (simplified)"""
        # Example expressions:
        # "context.target_user_details.manager.user_id"
        # "lookup('approvers_table', context.department)"
        try:
            if self.expression.startswith("context."):
                path = self.expression[8:].split(".")
                value = context
                for key in path:
                    value = value.get(key, {}) if isinstance(value, dict) else getattr(value, key, None)
                return [value] if value else self.fallback_agents
        except Exception:
            pass
        return self.fallback_agents

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type.value,
            "priority": self.priority,
            "conditions": self.conditions,
            "static_agents": self.static_agents,
            "is_active": self.is_active
        }


@dataclass
class WorkflowStage:
    """A single stage in the workflow"""
    stage_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    stage_number: int = 1
    name: str = ""
    description: str = ""
    stage_type: StageType = StageType.APPROVAL

    # Agent rules (evaluated in priority order)
    agent_rules: List[AgentRule] = field(default_factory=list)

    # Stage behavior
    require_all_agents: bool = False  # True = all must approve, False = any one
    allow_delegation: bool = True
    allow_rejection: bool = True
    auto_approve_conditions: Dict = field(default_factory=dict)  # Auto-approve if conditions met

    # Timing
    sla_hours: int = 48
    reminder_hours: int = 24
    escalation_hours: int = 72
    escalation_agents: List[str] = field(default_factory=list)

    # Notifications
    notify_on_entry: bool = True
    notify_on_completion: bool = True

    def get_agents(self, context: Dict) -> List[str]:
        """Determine agents for this stage based on rules"""
        # Sort rules by priority
        sorted_rules = sorted(
            [r for r in self.agent_rules if r.is_active],
            key=lambda r: r.priority
        )

        # Find first matching rule
        for rule in sorted_rules:
            if rule.evaluate_conditions(context):
                agents = rule.determine_agents(context)
                if agents:
                    return agents

        # No matching rule, return empty
        return []

    def check_auto_approve(self, context: Dict) -> bool:
        """Check if stage should auto-approve"""
        if not self.auto_approve_conditions:
            return False

        for key, expected in self.auto_approve_conditions.items():
            actual = context.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False

        return True

    def to_dict(self) -> Dict:
        return {
            "stage_id": self.stage_id,
            "stage_number": self.stage_number,
            "name": self.name,
            "description": self.description,
            "stage_type": self.stage_type.value,
            "agent_rules": [r.to_dict() for r in self.agent_rules],
            "require_all_agents": self.require_all_agents,
            "sla_hours": self.sla_hours
        }


@dataclass
class ParallelPath:
    """
    A parallel execution path within the workflow.
    Allows different parts of a request to be processed simultaneously.
    """
    path_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""

    # What this path handles
    filter_criteria: Dict = field(default_factory=dict)
    # Example: {"system": "SAP_ECC"} or {"role_prefix": "Z_FI_"}

    # Stages in this path
    stages: List[WorkflowStage] = field(default_factory=list)

    # Path behavior
    is_optional: bool = False  # Skip if no matching items
    continue_on_rejection: bool = False  # Continue other paths if this rejects

    def matches_item(self, item: Dict) -> bool:
        """Check if an item should be processed by this path"""
        if not self.filter_criteria:
            return True

        for key, expected in self.filter_criteria.items():
            actual = item.get(key, "")
            if key.endswith("_prefix"):
                actual_key = key[:-7]
                actual_value = item.get(actual_key, "")
                if not actual_value.startswith(expected):
                    return False
            elif key.endswith("_contains"):
                actual_key = key[:-9]
                actual_value = item.get(actual_key, "")
                if expected not in actual_value:
                    return False
            elif isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False

        return True

    def to_dict(self) -> Dict:
        return {
            "path_id": self.path_id,
            "name": self.name,
            "description": self.description,
            "filter_criteria": self.filter_criteria,
            "stages": [s.to_dict() for s in self.stages],
            "is_optional": self.is_optional
        }


@dataclass
class WorkflowPath:
    """
    Complete workflow definition with parallel paths.
    This is the main MSMP workflow configuration.
    """
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    version: str = "1.0"

    # Activation conditions
    activation_conditions: Dict = field(default_factory=dict)
    # Example: {"request_type": "new_access", "risk_level": ["medium", "high"]}

    # Parallel paths
    paths: List[ParallelPath] = field(default_factory=list)

    # Default path (used if no parallel paths match)
    default_stages: List[WorkflowStage] = field(default_factory=list)

    # Global settings
    allow_parallel_execution: bool = True
    require_all_paths_approved: bool = True
    auto_provision_on_approval: bool = True

    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def matches_request(self, context: Dict) -> bool:
        """Check if this workflow should handle the request"""
        if not self.activation_conditions:
            return True

        for key, expected in self.activation_conditions.items():
            actual = context.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False

        return True

    def to_dict(self) -> Dict:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "activation_conditions": self.activation_conditions,
            "paths": [p.to_dict() for p in self.paths],
            "default_stages": [s.to_dict() for s in self.default_stages],
            "allow_parallel_execution": self.allow_parallel_execution,
            "is_active": self.is_active
        }


class MSMPEngine:
    """
    Multi-Stage Multi-Path Workflow Engine.
    Provides SAP GRC-equivalent workflow capabilities with zero-training UX.
    """

    def __init__(self):
        self.workflows: Dict[str, WorkflowPath] = {}
        self.agent_rules: Dict[str, AgentRule] = {}
        self._init_default_workflows()
        self._init_default_agent_rules()

    def _init_default_agent_rules(self):
        """Initialize default agent determination rules"""
        rules = [
            # Manager approval for all requests
            AgentRule(
                rule_id="rule_manager",
                name="Manager Approval",
                description="Route to target user's manager",
                rule_type=AgentRuleType.MANAGER,
                priority=100,
                fallback_agents=["security_team@company.com"]
            ),

            # Role owner for specific roles
            AgentRule(
                rule_id="rule_role_owner",
                name="Role Owner Approval",
                description="Route to owner of requested role",
                rule_type=AgentRuleType.ROLE_OWNER,
                priority=90,
                conditions={"has_role_owner": True},
                fallback_agents=["role_admin@company.com"]
            ),

            # Security team for high risk
            AgentRule(
                rule_id="rule_security_high",
                name="Security Team - High Risk",
                description="Security team review for high/critical risk",
                rule_type=AgentRuleType.SECURITY_TEAM,
                priority=50,
                conditions={"risk_level": ["high", "critical"]},
                fallback_agents=["security_team@company.com"]
            ),

            # Cost center owner for financial roles
            AgentRule(
                rule_id="rule_cc_owner",
                name="Cost Center Owner",
                description="Cost center owner for financial access",
                rule_type=AgentRuleType.COST_CENTER_OWNER,
                priority=80,
                conditions={"role_category": ["finance", "accounting"]},
                fallback_agents=["finance_approvers@company.com"]
            ),

            # Department head for sensitive access
            AgentRule(
                rule_id="rule_dept_head",
                name="Department Head",
                description="Department head for sensitive access",
                rule_type=AgentRuleType.DEPARTMENT_HEAD,
                priority=70,
                conditions={"has_sensitive_access": True}
            ),

            # Static security team
            AgentRule(
                rule_id="rule_security_static",
                name="Security Team (Static)",
                description="Fixed security team approvers",
                rule_type=AgentRuleType.STATIC,
                priority=200,
                static_agents=["security_admin@company.com", "grc_admin@company.com"]
            ),
        ]

        for rule in rules:
            self.agent_rules[rule.rule_id] = rule

    def _init_default_workflows(self):
        """Initialize default workflow configurations for zero-training experience"""

        # Standard Access Request Workflow
        standard_workflow = WorkflowPath(
            workflow_id="wf_standard",
            name="Standard Access Request",
            description="Default workflow for new access requests",
            activation_conditions={"request_type": ["new_access", "modify_access"]},
            default_stages=[
                WorkflowStage(
                    stage_id="stage_manager",
                    stage_number=1,
                    name="Manager Approval",
                    description="Target user's manager approval",
                    stage_type=StageType.APPROVAL,
                    agent_rules=[
                        AgentRule(
                            name="Manager",
                            rule_type=AgentRuleType.MANAGER,
                            fallback_agents=["hr_manager@company.com"]
                        )
                    ],
                    sla_hours=48
                ),
                WorkflowStage(
                    stage_id="stage_role_owner",
                    stage_number=2,
                    name="Role Owner Approval",
                    description="Role owner/data owner approval",
                    stage_type=StageType.APPROVAL,
                    agent_rules=[
                        AgentRule(
                            name="Role Owner",
                            rule_type=AgentRuleType.ROLE_OWNER,
                            fallback_agents=["role_admin@company.com"]
                        )
                    ],
                    sla_hours=48
                ),
            ]
        )

        # High Risk Workflow (adds security review)
        high_risk_workflow = WorkflowPath(
            workflow_id="wf_high_risk",
            name="High Risk Access Request",
            description="Workflow for high/critical risk requests",
            activation_conditions={"risk_level": ["high", "critical"]},
            default_stages=[
                WorkflowStage(
                    stage_id="stage_manager_hr",
                    stage_number=1,
                    name="Manager Approval",
                    description="Manager approval required",
                    stage_type=StageType.APPROVAL,
                    agent_rules=[
                        AgentRule(rule_type=AgentRuleType.MANAGER)
                    ],
                    sla_hours=24  # Shorter SLA for high risk
                ),
                WorkflowStage(
                    stage_id="stage_security",
                    stage_number=2,
                    name="Security Review",
                    description="Security team risk review",
                    stage_type=StageType.RISK_REVIEW,
                    agent_rules=[
                        AgentRule(
                            rule_type=AgentRuleType.SECURITY_TEAM,
                            static_agents=["security_team@company.com"]
                        )
                    ],
                    sla_hours=24
                ),
                WorkflowStage(
                    stage_id="stage_role_owner_hr",
                    stage_number=3,
                    name="Role Owner Approval",
                    description="Role owner final approval",
                    stage_type=StageType.APPROVAL,
                    agent_rules=[
                        AgentRule(rule_type=AgentRuleType.ROLE_OWNER)
                    ],
                    sla_hours=24
                ),
            ]
        )

        # Multi-System Workflow (parallel paths)
        multi_system_workflow = WorkflowPath(
            workflow_id="wf_multi_system",
            name="Multi-System Access Request",
            description="Workflow for requests spanning multiple systems",
            activation_conditions={"multi_system": True},
            allow_parallel_execution=True,
            paths=[
                ParallelPath(
                    path_id="path_sap",
                    name="SAP Approvals",
                    description="SAP system specific approvals",
                    filter_criteria={"system": "SAP"},
                    stages=[
                        WorkflowStage(
                            stage_number=1,
                            name="SAP Role Owner",
                            stage_type=StageType.APPROVAL,
                            agent_rules=[
                                AgentRule(
                                    rule_type=AgentRuleType.STATIC,
                                    static_agents=["sap_security@company.com"]
                                )
                            ]
                        )
                    ]
                ),
                ParallelPath(
                    path_id="path_ad",
                    name="Active Directory Approvals",
                    description="AD/Azure AD specific approvals",
                    filter_criteria={"system_contains": "AD"},
                    stages=[
                        WorkflowStage(
                            stage_number=1,
                            name="AD Admin",
                            stage_type=StageType.APPROVAL,
                            agent_rules=[
                                AgentRule(
                                    rule_type=AgentRuleType.STATIC,
                                    static_agents=["ad_admin@company.com"]
                                )
                            ]
                        )
                    ]
                )
            ],
            default_stages=[
                WorkflowStage(
                    stage_number=1,
                    name="Manager Approval",
                    stage_type=StageType.APPROVAL,
                    agent_rules=[AgentRule(rule_type=AgentRuleType.MANAGER)]
                )
            ]
        )

        # Low Risk Auto-Approve Workflow
        low_risk_workflow = WorkflowPath(
            workflow_id="wf_low_risk",
            name="Low Risk Auto-Approve",
            description="Simplified workflow for low risk requests",
            activation_conditions={"risk_level": "low", "request_type": "new_access"},
            default_stages=[
                WorkflowStage(
                    stage_id="stage_auto",
                    stage_number=1,
                    name="Manager Approval",
                    description="Manager approval (auto-approve for standard roles)",
                    stage_type=StageType.APPROVAL,
                    agent_rules=[AgentRule(rule_type=AgentRuleType.MANAGER)],
                    auto_approve_conditions={"is_standard_role": True},
                    sla_hours=72
                )
            ]
        )

        # Emergency Access Workflow
        emergency_workflow = WorkflowPath(
            workflow_id="wf_emergency",
            name="Emergency Access",
            description="Fast-track workflow for emergency access",
            activation_conditions={"request_type": "emergency"},
            default_stages=[
                WorkflowStage(
                    stage_number=1,
                    name="Emergency Approver",
                    description="On-call emergency approver",
                    stage_type=StageType.APPROVAL,
                    agent_rules=[
                        AgentRule(
                            rule_type=AgentRuleType.STATIC,
                            static_agents=["emergency_oncall@company.com"]
                        )
                    ],
                    sla_hours=1,  # 1 hour SLA
                    escalation_hours=2
                )
            ]
        )

        # Store workflows
        for wf in [standard_workflow, high_risk_workflow, multi_system_workflow,
                   low_risk_workflow, emergency_workflow]:
            self.workflows[wf.workflow_id] = wf

    # =========================================================================
    # Workflow Selection
    # =========================================================================

    def select_workflow(self, context: Dict) -> Optional[WorkflowPath]:
        """
        Select the appropriate workflow for a request.
        Evaluates activation conditions to find the best match.
        """
        # Sort by specificity (more conditions = more specific)
        sorted_workflows = sorted(
            [w for w in self.workflows.values() if w.is_active],
            key=lambda w: len(w.activation_conditions),
            reverse=True
        )

        for workflow in sorted_workflows:
            if workflow.matches_request(context):
                return workflow

        # Return default if no match
        return self.workflows.get("wf_standard")

    # =========================================================================
    # Workflow Execution
    # =========================================================================

    def generate_approval_steps(self, workflow: WorkflowPath, context: Dict, items: List[Dict]) -> List[Dict]:
        """
        Generate approval steps for a request.
        Handles parallel paths and dynamic agent determination.
        """
        steps = []

        if workflow.allow_parallel_execution and workflow.paths:
            # Generate parallel paths
            for path in workflow.paths:
                # Filter items for this path
                path_items = [i for i in items if path.matches_item(i)]
                if not path_items and path.is_optional:
                    continue

                # Generate stages for this path
                for stage in path.stages:
                    step = self._create_step_from_stage(stage, context, path_items, path.path_id)
                    if step:
                        steps.append(step)

        # Add default stages
        for stage in workflow.default_stages:
            step = self._create_step_from_stage(stage, context, items)
            if step:
                steps.append(step)

        # Sort by stage number
        steps.sort(key=lambda s: s.get("stage_number", 0))

        return steps

    def _create_step_from_stage(
        self,
        stage: WorkflowStage,
        context: Dict,
        items: List[Dict],
        path_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Create an approval step from a stage definition"""

        # Check auto-approve
        if stage.check_auto_approve(context):
            return {
                "stage_id": stage.stage_id,
                "stage_number": stage.stage_number,
                "name": stage.name,
                "stage_type": stage.stage_type.value,
                "path_id": path_id,
                "status": "auto_approved",
                "auto_approved": True,
                "approvers": [],
                "items": items
            }

        # Determine agents
        agents = stage.get_agents(context)
        if not agents and stage.stage_type == StageType.APPROVAL:
            # No approvers found, use escalation
            agents = stage.escalation_agents

        return {
            "stage_id": stage.stage_id,
            "stage_number": stage.stage_number,
            "name": stage.name,
            "description": stage.description,
            "stage_type": stage.stage_type.value,
            "path_id": path_id,
            "status": "pending",
            "approvers": agents,
            "require_all": stage.require_all_agents,
            "allow_delegation": stage.allow_delegation,
            "sla_hours": stage.sla_hours,
            "due_date": (datetime.now() + timedelta(hours=stage.sla_hours)).isoformat(),
            "items": items
        }

    # =========================================================================
    # Workflow Management
    # =========================================================================

    def list_workflows(self, active_only: bool = True) -> List[WorkflowPath]:
        """List all workflows"""
        workflows = list(self.workflows.values())
        if active_only:
            workflows = [w for w in workflows if w.is_active]
        return workflows

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowPath]:
        """Get a workflow by ID"""
        return self.workflows.get(workflow_id)

    def create_workflow(self, workflow: WorkflowPath) -> WorkflowPath:
        """Create a new workflow"""
        self.workflows[workflow.workflow_id] = workflow
        return workflow

    def update_workflow(self, workflow_id: str, updates: Dict) -> Optional[WorkflowPath]:
        """Update a workflow"""
        if workflow_id not in self.workflows:
            return None

        workflow = self.workflows[workflow_id]
        for key, value in updates.items():
            if hasattr(workflow, key):
                setattr(workflow, key, value)
        workflow.updated_at = datetime.now()
        return workflow

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            return True
        return False

    # =========================================================================
    # Agent Rule Management
    # =========================================================================

    def list_agent_rules(self) -> List[AgentRule]:
        """List all agent rules"""
        return list(self.agent_rules.values())

    def get_agent_rule(self, rule_id: str) -> Optional[AgentRule]:
        """Get an agent rule by ID"""
        return self.agent_rules.get(rule_id)

    def create_agent_rule(self, rule: AgentRule) -> AgentRule:
        """Create a new agent rule"""
        self.agent_rules[rule.rule_id] = rule
        return rule

    def test_agent_rule(self, rule_id: str, context: Dict) -> Dict:
        """Test an agent rule with sample context"""
        rule = self.agent_rules.get(rule_id)
        if not rule:
            return {"error": "Rule not found"}

        matches = rule.evaluate_conditions(context)
        agents = rule.determine_agents(context) if matches else []

        return {
            "rule_id": rule_id,
            "conditions_match": matches,
            "determined_agents": agents,
            "context_used": context
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict:
        """Get workflow statistics"""
        return {
            "total_workflows": len(self.workflows),
            "active_workflows": len([w for w in self.workflows.values() if w.is_active]),
            "total_agent_rules": len(self.agent_rules),
            "workflows_by_type": {
                "standard": len([w for w in self.workflows.values()
                               if "new_access" in str(w.activation_conditions)]),
                "high_risk": len([w for w in self.workflows.values()
                                if "high" in str(w.activation_conditions) or "critical" in str(w.activation_conditions)]),
                "emergency": len([w for w in self.workflows.values()
                                if "emergency" in str(w.activation_conditions)])
            }
        }
