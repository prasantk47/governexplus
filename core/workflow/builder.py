# Visual Workflow Builder Schema
# Zero-code, drag-and-drop workflow design

"""
Visual Workflow Builder for GOVERNEX+.

THIS IS THE KILLER FEATURE:
Customers design workflows via drag & drop, not code or YAML.

The builder provides:
1. Building Blocks (palette of reusable components)
2. Canvas (where customers assemble workflows)
3. Simulation (preview what happens before saving)
4. Validation (safety guardrails enforced)
5. Export (generates internal policy, invisible to user)

Key Insight:
Customers design INTENT, not LOGIC.
The engine converts intent into executable policy.

SAP MSMP → Configure paths
GOVERNEX+ → Compose decisions
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import uuid
import json


# ============================================================
# BLOCK TYPES (THE BUILDING BLOCKS)
# ============================================================

class BlockType(Enum):
    """Types of blocks available in the palette."""

    # Triggers (Blue)
    TRIGGER = "TRIGGER"

    # Conditions (Yellow)
    CONDITION = "CONDITION"
    CONDITION_GROUP = "CONDITION_GROUP"

    # Approvals (Green)
    APPROVAL = "APPROVAL"
    APPROVAL_GROUP = "APPROVAL_GROUP"

    # Provisioning (Purple)
    PROVISIONING_GATE = "PROVISIONING_GATE"

    # Actions (Red)
    ACTION = "ACTION"

    # Flow Control
    SPLIT = "SPLIT"
    JOIN = "JOIN"
    PARALLEL = "PARALLEL"


class TriggerType(Enum):
    """Types of workflow triggers."""
    ACCESS_REQUEST = "ACCESS_REQUEST"
    FIREFIGHTER_REQUEST = "FIREFIGHTER_REQUEST"
    ROLE_CHANGE = "ROLE_CHANGE"
    RISK_SPIKE = "RISK_SPIKE"
    PREDICTIVE_ALERT = "PREDICTIVE_ALERT"
    SCHEDULED_REVIEW = "SCHEDULED_REVIEW"
    EMERGENCY_ACCESS = "EMERGENCY_ACCESS"
    TERMINATION = "TERMINATION"
    TRANSFER = "TRANSFER"
    CERTIFICATION = "CERTIFICATION"


class ConditionAttribute(Enum):
    """Attributes that can be used in conditions."""
    RISK_SCORE = "RISK_SCORE"
    SYSTEM = "SYSTEM"
    SYSTEM_TYPE = "SYSTEM_TYPE"
    ACCESS_TYPE = "ACCESS_TYPE"
    ROLE_TAG = "ROLE_TAG"
    USER_TYPE = "USER_TYPE"
    DEPARTMENT = "DEPARTMENT"
    TIME_OF_DAY = "TIME_OF_DAY"
    IS_TEMPORARY = "IS_TEMPORARY"
    IS_EMERGENCY = "IS_EMERGENCY"
    HAS_SOD = "HAS_SOD"
    COUNTRY = "COUNTRY"
    BUSINESS_UNIT = "BUSINESS_UNIT"
    COST_CENTER = "COST_CENTER"
    SENSITIVITY = "SENSITIVITY"


class ConditionOperator(Enum):
    """Operators for conditions."""
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    GREATER_OR_EQUAL = "GREATER_OR_EQUAL"
    LESS_OR_EQUAL = "LESS_OR_EQUAL"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    IN_LIST = "IN_LIST"
    NOT_IN_LIST = "NOT_IN_LIST"
    IS_TRUE = "IS_TRUE"
    IS_FALSE = "IS_FALSE"
    BETWEEN = "BETWEEN"


class ApproverType(Enum):
    """Types of approvers."""
    LINE_MANAGER = "LINE_MANAGER"
    ROLE_OWNER = "ROLE_OWNER"
    PROCESS_OWNER = "PROCESS_OWNER"
    SECURITY_OFFICER = "SECURITY_OFFICER"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
    DATA_OWNER = "DATA_OWNER"
    SYSTEM_OWNER = "SYSTEM_OWNER"
    CUSTOM_GROUP = "CUSTOM_GROUP"
    AI_RECOMMENDED = "AI_RECOMMENDED"
    ESCALATION_MANAGER = "ESCALATION_MANAGER"


class ProvisioningMode(Enum):
    """Provisioning modes for the gate."""
    PER_ITEM = "PER_ITEM"                    # Provision each approved item immediately
    ALL_OR_NOTHING = "ALL_OR_NOTHING"        # Wait for all approvals
    RISK_BASED = "RISK_BASED"                # Low-risk first
    TEMPORARY_FIRST = "TEMPORARY_FIRST"      # Temporary access first
    CRITICAL_LAST = "CRITICAL_LAST"          # Critical access after all else


class ActionType(Enum):
    """Types of post-approval actions."""
    PROVISION_ACCESS = "PROVISION_ACCESS"
    REVOKE_ACCESS = "REVOKE_ACCESS"
    NOTIFY_USER = "NOTIFY_USER"
    NOTIFY_MANAGER = "NOTIFY_MANAGER"
    NOTIFY_SECURITY = "NOTIFY_SECURITY"
    START_POST_REVIEW = "START_POST_REVIEW"
    TRIGGER_AUDIT = "TRIGGER_AUDIT"
    CLOSE_REQUEST = "CLOSE_REQUEST"
    SCHEDULE_REVIEW = "SCHEDULE_REVIEW"
    LOG_EVENT = "LOG_EVENT"
    CALL_WEBHOOK = "CALL_WEBHOOK"


# ============================================================
# BLOCK DEFINITIONS (THE LEGO PIECES)
# ============================================================

@dataclass
class BlockPosition:
    """Position on the canvas."""
    x: int = 0
    y: int = 0


@dataclass
class Connection:
    """Connection between blocks."""
    from_block_id: str = ""
    from_port: str = "output"  # output, true, false, item_1, etc.
    to_block_id: str = ""
    to_port: str = "input"


@dataclass
class BaseBlock:
    """Base class for all blocks."""
    block_id: str = field(default_factory=lambda: f"BLK-{str(uuid.uuid4())[:8]}")
    block_type: BlockType = BlockType.TRIGGER
    name: str = ""
    description: str = ""
    position: BlockPosition = field(default_factory=BlockPosition)
    enabled: bool = True

    # UI metadata
    color: str = "#3B82F6"  # Default blue
    icon: str = "play"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "block_type": self.block_type.value,
            "name": self.name,
            "description": self.description,
            "position": {"x": self.position.x, "y": self.position.y},
            "enabled": self.enabled,
            "color": self.color,
            "icon": self.icon,
        }


@dataclass
class TriggerBlock(BaseBlock):
    """Trigger block - starts the workflow."""
    block_type: BlockType = BlockType.TRIGGER
    trigger_type: TriggerType = TriggerType.ACCESS_REQUEST
    color: str = "#3B82F6"  # Blue
    icon: str = "play"

    # Settings
    auto_start: bool = True
    require_justification: bool = True

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "trigger_type": self.trigger_type.value,
            "settings": {
                "auto_start": self.auto_start,
                "require_justification": self.require_justification,
            }
        })
        return base

    def to_human_readable(self) -> str:
        """Generate human-readable description."""
        return f"When a {self.trigger_type.value.replace('_', ' ').lower()} is submitted"


@dataclass
class ConditionBlock(BaseBlock):
    """Condition block - routes based on conditions."""
    block_type: BlockType = BlockType.CONDITION
    color: str = "#F59E0B"  # Yellow/Amber
    icon: str = "filter"

    # Condition definition
    attribute: ConditionAttribute = ConditionAttribute.RISK_SCORE
    operator: ConditionOperator = ConditionOperator.GREATER_THAN
    value: Any = 0
    value_end: Any = None  # For BETWEEN operator

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "condition": {
                "attribute": self.attribute.value,
                "operator": self.operator.value,
                "value": self.value,
                "value_end": self.value_end,
            }
        })
        return base

    def to_human_readable(self) -> str:
        """Generate human-readable description."""
        attr = self.attribute.value.replace("_", " ").lower()
        op_map = {
            ConditionOperator.EQUALS: "equals",
            ConditionOperator.NOT_EQUALS: "does not equal",
            ConditionOperator.GREATER_THAN: "is greater than",
            ConditionOperator.LESS_THAN: "is less than",
            ConditionOperator.GREATER_OR_EQUAL: "is at least",
            ConditionOperator.LESS_OR_EQUAL: "is at most",
            ConditionOperator.CONTAINS: "contains",
            ConditionOperator.IN_LIST: "is one of",
            ConditionOperator.IS_TRUE: "is true",
            ConditionOperator.IS_FALSE: "is false",
            ConditionOperator.BETWEEN: "is between",
        }
        op = op_map.get(self.operator, self.operator.value)

        if self.operator == ConditionOperator.BETWEEN:
            return f"If {attr} {op} {self.value} and {self.value_end}"
        elif self.operator in [ConditionOperator.IS_TRUE, ConditionOperator.IS_FALSE]:
            return f"If {attr} {op}"
        else:
            return f"If {attr} {op} {self.value}"


@dataclass
class ConditionGroupBlock(BaseBlock):
    """Group of conditions with AND/OR logic."""
    block_type: BlockType = BlockType.CONDITION_GROUP
    color: str = "#F59E0B"
    icon: str = "filter-circle"

    # Logic
    logic: str = "AND"  # AND, OR
    conditions: List["ConditionBlock"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "logic": self.logic,
            "conditions": [c.to_dict() for c in self.conditions],
        })
        return base

    def to_human_readable(self) -> str:
        if not self.conditions:
            return "No conditions"
        parts = [c.to_human_readable() for c in self.conditions]
        connector = f" {self.logic.lower()} "
        return connector.join(parts)


@dataclass
class ApprovalBlock(BaseBlock):
    """Approval block - requires human approval."""
    block_type: BlockType = BlockType.APPROVAL
    color: str = "#10B981"  # Green
    icon: str = "check-circle"

    # Approver settings
    approver_type: ApproverType = ApproverType.LINE_MANAGER
    custom_group_id: Optional[str] = None  # For CUSTOM_GROUP

    # Behavior
    is_required: bool = True
    allow_delegate: bool = True
    allow_skip_if_unavailable: bool = False

    # SLA
    sla_hours: int = 48
    warning_hours: int = 24
    escalate_to: Optional[ApproverType] = None

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "approver": {
                "type": self.approver_type.value,
                "custom_group_id": self.custom_group_id,
            },
            "behavior": {
                "is_required": self.is_required,
                "allow_delegate": self.allow_delegate,
                "allow_skip_if_unavailable": self.allow_skip_if_unavailable,
            },
            "sla": {
                "hours": self.sla_hours,
                "warning_hours": self.warning_hours,
                "escalate_to": self.escalate_to.value if self.escalate_to else None,
            }
        })
        return base

    def to_human_readable(self) -> str:
        approver = self.approver_type.value.replace("_", " ").title()
        required = "required" if self.is_required else "optional"
        return f"{approver} approval ({required}, {self.sla_hours}h SLA)"


@dataclass
class ApprovalGroupBlock(BaseBlock):
    """Group of approvals in parallel or sequence."""
    block_type: BlockType = BlockType.APPROVAL_GROUP
    color: str = "#10B981"
    icon: str = "users"

    # Execution mode
    mode: str = "PARALLEL"  # PARALLEL, SEQUENTIAL, ANY_ONE
    approvals: List[ApprovalBlock] = field(default_factory=list)

    # Parallel settings
    require_all: bool = True  # For PARALLEL
    minimum_approvals: int = 1  # For ANY_ONE

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "mode": self.mode,
            "require_all": self.require_all,
            "minimum_approvals": self.minimum_approvals,
            "approvals": [a.to_dict() for a in self.approvals],
        })
        return base

    def to_human_readable(self) -> str:
        if not self.approvals:
            return "No approvers"
        names = [a.approver_type.value.replace("_", " ").title() for a in self.approvals]
        if self.mode == "PARALLEL":
            return f"All of: {', '.join(names)} (in parallel)"
        elif self.mode == "SEQUENTIAL":
            return f"In order: {' → '.join(names)}"
        else:
            return f"Any {self.minimum_approvals} of: {', '.join(names)}"


@dataclass
class ProvisioningGateBlock(BaseBlock):
    """
    Provisioning Gate - THE DIFFERENTIATOR.

    This single block beats MSMP.
    Customer chooses when/how provisioning happens.
    """
    block_type: BlockType = BlockType.PROVISIONING_GATE
    color: str = "#8B5CF6"  # Purple
    icon: str = "shield-check"

    # Provisioning mode (THE KEY CHOICE)
    mode: ProvisioningMode = ProvisioningMode.PER_ITEM

    # Settings per mode
    risk_threshold: int = 50  # For RISK_BASED
    allow_partial: bool = True
    provision_immediately: bool = True

    # Safety settings
    require_all_mandatory_approvals: bool = True
    block_sod_items: bool = True
    log_all_decisions: bool = True

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "provisioning": {
                "mode": self.mode.value,
                "risk_threshold": self.risk_threshold,
                "allow_partial": self.allow_partial,
                "provision_immediately": self.provision_immediately,
            },
            "safety": {
                "require_all_mandatory_approvals": self.require_all_mandatory_approvals,
                "block_sod_items": self.block_sod_items,
                "log_all_decisions": self.log_all_decisions,
            }
        })
        return base

    def to_human_readable(self) -> str:
        mode_desc = {
            ProvisioningMode.PER_ITEM: "Provision each approved item immediately",
            ProvisioningMode.ALL_OR_NOTHING: "Wait for all approvals before provisioning",
            ProvisioningMode.RISK_BASED: f"Provision low-risk items (≤{self.risk_threshold}) first",
            ProvisioningMode.TEMPORARY_FIRST: "Provision temporary access first",
            ProvisioningMode.CRITICAL_LAST: "Provision critical access last",
        }
        return mode_desc.get(self.mode, self.mode.value)


@dataclass
class ActionBlock(BaseBlock):
    """Action block - post-approval actions."""
    block_type: BlockType = BlockType.ACTION
    color: str = "#EF4444"  # Red
    icon: str = "bolt"

    # Action type
    action_type: ActionType = ActionType.NOTIFY_USER

    # Settings per action type
    template_id: Optional[str] = None  # For notifications
    webhook_url: Optional[str] = None  # For webhooks
    review_days: int = 90  # For scheduled reviews

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "action": {
                "type": self.action_type.value,
                "template_id": self.template_id,
                "webhook_url": self.webhook_url,
                "review_days": self.review_days,
            }
        })
        return base

    def to_human_readable(self) -> str:
        action_desc = {
            ActionType.PROVISION_ACCESS: "Provision the approved access",
            ActionType.REVOKE_ACCESS: "Revoke the access",
            ActionType.NOTIFY_USER: "Notify the requester",
            ActionType.NOTIFY_MANAGER: "Notify the user's manager",
            ActionType.NOTIFY_SECURITY: "Notify the security team",
            ActionType.START_POST_REVIEW: "Start post-provisioning review",
            ActionType.TRIGGER_AUDIT: "Create audit evidence",
            ActionType.CLOSE_REQUEST: "Close the request",
            ActionType.SCHEDULE_REVIEW: f"Schedule review in {self.review_days} days",
        }
        return action_desc.get(self.action_type, self.action_type.value)


@dataclass
class SplitBlock(BaseBlock):
    """Split block - splits flow by access items."""
    block_type: BlockType = BlockType.SPLIT
    color: str = "#6366F1"  # Indigo
    icon: str = "arrows-split-up-and-left"

    # Split by
    split_by: str = "ACCESS_ITEM"  # ACCESS_ITEM, SYSTEM, RISK_LEVEL

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "split_by": self.split_by,
        })
        return base

    def to_human_readable(self) -> str:
        return f"Split by {self.split_by.replace('_', ' ').lower()}"


@dataclass
class JoinBlock(BaseBlock):
    """Join block - merges parallel paths."""
    block_type: BlockType = BlockType.JOIN
    color: str = "#6366F1"  # Indigo
    icon: str = "arrows-pointing-in"

    # Join behavior
    wait_for_all: bool = True
    timeout_hours: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "wait_for_all": self.wait_for_all,
            "timeout_hours": self.timeout_hours,
        })
        return base


# ============================================================
# WORKFLOW CANVAS (THE COMPLETE WORKFLOW)
# ============================================================

@dataclass
class WorkflowCanvas:
    """
    Complete workflow design on the canvas.

    This is what the customer builds visually.
    """
    canvas_id: str = field(default_factory=lambda: f"WF-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    name: str = "New Workflow"
    description: str = ""
    version: int = 1

    # Blocks on the canvas
    blocks: List[BaseBlock] = field(default_factory=list)

    # Connections between blocks
    connections: List[Connection] = field(default_factory=list)

    # Global settings
    global_settings: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = False
    is_template: bool = False

    def add_block(self, block: BaseBlock) -> str:
        """Add a block to the canvas."""
        self.blocks.append(block)
        return block.block_id

    def connect(self, from_id: str, to_id: str, from_port: str = "output", to_port: str = "input") -> None:
        """Connect two blocks."""
        self.connections.append(Connection(
            from_block_id=from_id,
            to_block_id=to_id,
            from_port=from_port,
            to_port=to_port,
        ))

    def get_block(self, block_id: str) -> Optional[BaseBlock]:
        """Get a block by ID."""
        return next((b for b in self.blocks if b.block_id == block_id), None)

    def remove_block(self, block_id: str) -> None:
        """Remove a block and its connections."""
        self.blocks = [b for b in self.blocks if b.block_id != block_id]
        self.connections = [
            c for c in self.connections
            if c.from_block_id != block_id and c.to_block_id != block_id
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canvas_id": self.canvas_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "blocks": [b.to_dict() for b in self.blocks],
            "connections": [
                {
                    "from": c.from_block_id,
                    "from_port": c.from_port,
                    "to": c.to_block_id,
                    "to_port": c.to_port,
                }
                for c in self.connections
            ],
            "global_settings": self.global_settings,
            "metadata": {
                "created_by": self.created_by,
                "created_at": self.created_at.isoformat(),
                "is_active": self.is_active,
                "is_template": self.is_template,
            }
        }

    def to_json(self) -> str:
        """Export to JSON for storage."""
        return json.dumps(self.to_dict(), indent=2)

    def generate_preview(self) -> str:
        """
        Generate human-readable preview of what the workflow does.

        This is shown in the right panel so customer understands the impact.
        """
        lines = []
        lines.append(f"📋 Workflow: {self.name}")
        lines.append("=" * 40)
        lines.append("")

        # Find trigger
        triggers = [b for b in self.blocks if b.block_type == BlockType.TRIGGER]
        for trigger in triggers:
            lines.append(f"🔵 TRIGGER: {trigger.to_human_readable()}")
            lines.append("")

        # Find conditions
        conditions = [b for b in self.blocks if b.block_type in [BlockType.CONDITION, BlockType.CONDITION_GROUP]]
        if conditions:
            lines.append("🟡 CONDITIONS:")
            for cond in conditions:
                lines.append(f"   • {cond.to_human_readable()}")
            lines.append("")

        # Find approvals
        approvals = [b for b in self.blocks if b.block_type in [BlockType.APPROVAL, BlockType.APPROVAL_GROUP]]
        if approvals:
            lines.append("🟢 APPROVALS REQUIRED:")
            for appr in approvals:
                lines.append(f"   • {appr.to_human_readable()}")
            lines.append("")

        # Find provisioning gate
        gates = [b for b in self.blocks if b.block_type == BlockType.PROVISIONING_GATE]
        for gate in gates:
            lines.append(f"🟣 PROVISIONING: {gate.to_human_readable()}")
            lines.append("")

        # Find actions
        actions = [b for b in self.blocks if b.block_type == BlockType.ACTION]
        if actions:
            lines.append("🔴 ACTIONS:")
            for action in actions:
                lines.append(f"   • {action.to_human_readable()}")
            lines.append("")

        # Impact summary
        lines.append("-" * 40)
        lines.append("📊 IMPACT PREVIEW:")

        # Check provisioning mode
        for gate in gates:
            if gate.mode == ProvisioningMode.PER_ITEM:
                lines.append("   • If 3 roles requested and 2 approved, 2 will be provisioned immediately")
            elif gate.mode == ProvisioningMode.ALL_OR_NOTHING:
                lines.append("   • All items must be approved before any provisioning")
            elif gate.mode == ProvisioningMode.RISK_BASED:
                lines.append(f"   • Low-risk items (≤{gate.risk_threshold}) provisioned first")

        # SLA info
        total_sla = sum(a.sla_hours for a in approvals if isinstance(a, ApprovalBlock))
        if total_sla:
            lines.append(f"   • Expected completion: {total_sla}h SLA total")

        return "\n".join(lines)


# ============================================================
# WORKFLOW BUILDER (THE ENGINE THAT POWERS THE UI)
# ============================================================

class WorkflowBuilder:
    """
    The engine that powers the visual workflow builder.

    Provides:
    - Block palette (available blocks)
    - Validation (safety guardrails)
    - Export (convert to internal policy)
    - Templates (pre-built workflows)
    """

    def __init__(self):
        self._templates: Dict[str, WorkflowCanvas] = {}
        self._guardrails: List[Dict[str, Any]] = self._default_guardrails()

    def _default_guardrails(self) -> List[Dict[str, Any]]:
        """Default safety guardrails."""
        return [
            {
                "id": "CRITICAL_ACCESS_SECURITY",
                "name": "Critical access requires security approval",
                "condition": "role_tag == 'CRITICAL'",
                "required_block": "SECURITY_OFFICER",
                "message": "Critical access cannot bypass Security approval",
            },
            {
                "id": "PROD_NO_AUTO_APPROVE",
                "name": "PROD cannot auto-approve",
                "condition": "system_type == 'PROD'",
                "disallow": "auto_approve",
                "message": "Production access cannot be auto-approved",
            },
            {
                "id": "PARTIAL_PROVISION_LOGGED",
                "name": "Partial provisioning always logged",
                "condition": "provisioning_mode == 'PER_ITEM'",
                "required_action": "LOG_EVENT",
                "message": "Partial provisioning requires audit logging",
            },
            {
                "id": "SOD_REQUIRES_REVIEW",
                "name": "SoD conflicts require compliance review",
                "condition": "has_sod == True",
                "required_block": "COMPLIANCE_OFFICER",
                "message": "SoD conflicts require Compliance review",
            },
        ]

    def get_block_palette(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get available blocks for the UI palette.

        Returns blocks grouped by category.
        """
        return {
            "triggers": [
                {"type": "TRIGGER", "trigger_type": "ACCESS_REQUEST", "name": "Access Request", "icon": "key", "color": "#3B82F6"},
                {"type": "TRIGGER", "trigger_type": "FIREFIGHTER_REQUEST", "name": "Firefighter Request", "icon": "fire", "color": "#3B82F6"},
                {"type": "TRIGGER", "trigger_type": "ROLE_CHANGE", "name": "Role Change", "icon": "user-cog", "color": "#3B82F6"},
                {"type": "TRIGGER", "trigger_type": "RISK_SPIKE", "name": "Risk Spike", "icon": "trending-up", "color": "#3B82F6"},
                {"type": "TRIGGER", "trigger_type": "PREDICTIVE_ALERT", "name": "Predictive Alert", "icon": "brain", "color": "#3B82F6"},
                {"type": "TRIGGER", "trigger_type": "SCHEDULED_REVIEW", "name": "Scheduled Review", "icon": "calendar", "color": "#3B82F6"},
            ],
            "conditions": [
                {"type": "CONDITION", "attribute": "RISK_SCORE", "name": "Risk Score", "icon": "chart-bar", "color": "#F59E0B"},
                {"type": "CONDITION", "attribute": "SYSTEM", "name": "System", "icon": "server", "color": "#F59E0B"},
                {"type": "CONDITION", "attribute": "SYSTEM_TYPE", "name": "System Type", "icon": "cube", "color": "#F59E0B"},
                {"type": "CONDITION", "attribute": "ACCESS_TYPE", "name": "Access Type", "icon": "key", "color": "#F59E0B"},
                {"type": "CONDITION", "attribute": "ROLE_TAG", "name": "Role Tag", "icon": "tag", "color": "#F59E0B"},
                {"type": "CONDITION", "attribute": "USER_TYPE", "name": "User Type", "icon": "user", "color": "#F59E0B"},
                {"type": "CONDITION", "attribute": "IS_TEMPORARY", "name": "Is Temporary", "icon": "clock", "color": "#F59E0B"},
                {"type": "CONDITION", "attribute": "HAS_SOD", "name": "Has SoD Conflict", "icon": "exclamation-triangle", "color": "#F59E0B"},
            ],
            "approvals": [
                {"type": "APPROVAL", "approver_type": "LINE_MANAGER", "name": "Line Manager", "icon": "user-tie", "color": "#10B981"},
                {"type": "APPROVAL", "approver_type": "ROLE_OWNER", "name": "Role Owner", "icon": "user-shield", "color": "#10B981"},
                {"type": "APPROVAL", "approver_type": "PROCESS_OWNER", "name": "Process Owner", "icon": "briefcase", "color": "#10B981"},
                {"type": "APPROVAL", "approver_type": "SECURITY_OFFICER", "name": "Security", "icon": "shield", "color": "#10B981"},
                {"type": "APPROVAL", "approver_type": "COMPLIANCE_OFFICER", "name": "Compliance", "icon": "check-square", "color": "#10B981"},
                {"type": "APPROVAL", "approver_type": "DATA_OWNER", "name": "Data Owner", "icon": "database", "color": "#10B981"},
                {"type": "APPROVAL", "approver_type": "CUSTOM_GROUP", "name": "Custom Group", "icon": "users", "color": "#10B981"},
                {"type": "APPROVAL", "approver_type": "AI_RECOMMENDED", "name": "AI Recommended", "icon": "brain", "color": "#10B981"},
            ],
            "provisioning": [
                {"type": "PROVISIONING_GATE", "mode": "PER_ITEM", "name": "Per Item", "icon": "check-circle", "color": "#8B5CF6", "description": "Provision each approved item immediately"},
                {"type": "PROVISIONING_GATE", "mode": "ALL_OR_NOTHING", "name": "All or Nothing", "icon": "shield", "color": "#8B5CF6", "description": "Wait for all approvals"},
                {"type": "PROVISIONING_GATE", "mode": "RISK_BASED", "name": "Risk Based", "icon": "chart-bar", "color": "#8B5CF6", "description": "Provision low-risk first"},
                {"type": "PROVISIONING_GATE", "mode": "TEMPORARY_FIRST", "name": "Temporary First", "icon": "clock", "color": "#8B5CF6", "description": "Provision temporary access first"},
            ],
            "actions": [
                {"type": "ACTION", "action_type": "NOTIFY_USER", "name": "Notify User", "icon": "mail", "color": "#EF4444"},
                {"type": "ACTION", "action_type": "NOTIFY_MANAGER", "name": "Notify Manager", "icon": "mail", "color": "#EF4444"},
                {"type": "ACTION", "action_type": "NOTIFY_SECURITY", "name": "Notify Security", "icon": "shield", "color": "#EF4444"},
                {"type": "ACTION", "action_type": "START_POST_REVIEW", "name": "Start Post Review", "icon": "eye", "color": "#EF4444"},
                {"type": "ACTION", "action_type": "TRIGGER_AUDIT", "name": "Trigger Audit", "icon": "file-text", "color": "#EF4444"},
                {"type": "ACTION", "action_type": "SCHEDULE_REVIEW", "name": "Schedule Review", "icon": "calendar", "color": "#EF4444"},
            ],
            "flow": [
                {"type": "SPLIT", "split_by": "ACCESS_ITEM", "name": "Split by Item", "icon": "git-branch", "color": "#6366F1"},
                {"type": "SPLIT", "split_by": "SYSTEM", "name": "Split by System", "icon": "git-branch", "color": "#6366F1"},
                {"type": "JOIN", "name": "Join", "icon": "git-merge", "color": "#6366F1"},
            ]
        }

    def validate_canvas(self, canvas: WorkflowCanvas) -> Dict[str, Any]:
        """
        Validate workflow against guardrails.

        Returns validation result with any errors/warnings.
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }

        # Check for trigger
        triggers = [b for b in canvas.blocks if b.block_type == BlockType.TRIGGER]
        if not triggers:
            result["valid"] = False
            result["errors"].append({
                "code": "NO_TRIGGER",
                "message": "Workflow must have at least one trigger",
            })

        # Check for at least one approval
        approvals = [b for b in canvas.blocks if b.block_type in [BlockType.APPROVAL, BlockType.APPROVAL_GROUP]]
        if not approvals:
            result["warnings"].append({
                "code": "NO_APPROVAL",
                "message": "Workflow has no approval steps - access will be auto-approved",
            })

        # Check for provisioning gate
        gates = [b for b in canvas.blocks if b.block_type == BlockType.PROVISIONING_GATE]
        if not gates:
            result["warnings"].append({
                "code": "NO_PROVISIONING_GATE",
                "message": "No provisioning gate - using default behavior",
            })

        # Apply guardrails
        for guardrail in self._guardrails:
            violation = self._check_guardrail(canvas, guardrail)
            if violation:
                result["errors"].append(violation)
                result["valid"] = False

        return result

    def _check_guardrail(self, canvas: WorkflowCanvas, guardrail: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check a single guardrail."""
        # This is simplified - real implementation would parse conditions
        required_block = guardrail.get("required_block")
        if required_block:
            has_block = any(
                isinstance(b, ApprovalBlock) and b.approver_type.value == required_block
                for b in canvas.blocks
            )
            # Only check if condition is met (simplified check)
            # In real implementation, evaluate the condition against workflow
            if not has_block:
                return {
                    "code": guardrail["id"],
                    "message": guardrail["message"],
                    "guardrail": guardrail["name"],
                }
        return None

    def export_to_policy(self, canvas: WorkflowCanvas) -> Dict[str, Any]:
        """
        Convert visual workflow to internal policy format.

        This is what gets stored and executed by the engine.
        The customer never sees this.
        """
        policy = {
            "policy_id": canvas.canvas_id,
            "name": canvas.name,
            "version": canvas.version,
            "rules": [],
            "approvers": [],
            "provisioning": {},
            "actions": [],
        }

        # Extract trigger
        for block in canvas.blocks:
            if isinstance(block, TriggerBlock):
                policy["trigger"] = {
                    "type": block.trigger_type.value,
                    "auto_start": block.auto_start,
                }

        # Extract conditions and build rules
        for block in canvas.blocks:
            if isinstance(block, ConditionBlock):
                policy["rules"].append({
                    "attribute": block.attribute.value,
                    "operator": block.operator.value,
                    "value": block.value,
                })

        # Extract approvers
        for block in canvas.blocks:
            if isinstance(block, ApprovalBlock):
                policy["approvers"].append({
                    "type": block.approver_type.value,
                    "required": block.is_required,
                    "sla_hours": block.sla_hours,
                    "allow_delegate": block.allow_delegate,
                })
            elif isinstance(block, ApprovalGroupBlock):
                policy["approvers"].append({
                    "type": "GROUP",
                    "mode": block.mode,
                    "approvers": [
                        {"type": a.approver_type.value, "required": a.is_required}
                        for a in block.approvals
                    ]
                })

        # Extract provisioning gate
        for block in canvas.blocks:
            if isinstance(block, ProvisioningGateBlock):
                policy["provisioning"] = {
                    "mode": block.mode.value,
                    "allow_partial": block.allow_partial,
                    "risk_threshold": block.risk_threshold,
                    "require_all_mandatory": block.require_all_mandatory_approvals,
                }

        # Extract actions
        for block in canvas.blocks:
            if isinstance(block, ActionBlock):
                policy["actions"].append({
                    "type": block.action_type.value,
                    "template_id": block.template_id,
                })

        return policy

    def create_template(self, canvas: WorkflowCanvas, template_name: str) -> str:
        """Save workflow as a reusable template."""
        template_id = f"TPL-{template_name.upper().replace(' ', '_')}"
        canvas.is_template = True
        self._templates[template_id] = canvas
        return template_id

    def get_templates(self) -> List[Dict[str, Any]]:
        """Get available templates."""
        return [
            {
                "template_id": tid,
                "name": t.name,
                "description": t.description,
            }
            for tid, t in self._templates.items()
        ]

    def load_template(self, template_id: str) -> Optional[WorkflowCanvas]:
        """Load a template as a new canvas."""
        template = self._templates.get(template_id)
        if template:
            # Create a copy with new ID
            import copy
            canvas = copy.deepcopy(template)
            canvas.canvas_id = f"WF-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            canvas.is_template = False
            return canvas
        return None


# ============================================================
# PRE-BUILT TEMPLATES
# ============================================================

def create_simple_access_template() -> WorkflowCanvas:
    """Simple access request: Manager approval → Provision."""
    canvas = WorkflowCanvas(
        name="Simple Access Request",
        description="Basic access request with manager approval",
    )

    # Add blocks
    trigger = TriggerBlock(
        name="Access Request",
        trigger_type=TriggerType.ACCESS_REQUEST,
        position=BlockPosition(100, 50),
    )
    canvas.add_block(trigger)

    approval = ApprovalBlock(
        name="Manager Approval",
        approver_type=ApproverType.LINE_MANAGER,
        sla_hours=24,
        position=BlockPosition(100, 150),
    )
    canvas.add_block(approval)

    gate = ProvisioningGateBlock(
        name="Provision Access",
        mode=ProvisioningMode.PER_ITEM,
        position=BlockPosition(100, 250),
    )
    canvas.add_block(gate)

    notify = ActionBlock(
        name="Notify User",
        action_type=ActionType.NOTIFY_USER,
        position=BlockPosition(100, 350),
    )
    canvas.add_block(notify)

    # Connect blocks
    canvas.connect(trigger.block_id, approval.block_id)
    canvas.connect(approval.block_id, gate.block_id)
    canvas.connect(gate.block_id, notify.block_id)

    return canvas


def create_multi_approver_template() -> WorkflowCanvas:
    """Multi-approver workflow: Manager + Security → Provision."""
    canvas = WorkflowCanvas(
        name="High-Risk Access Request",
        description="Access request requiring manager and security approval",
    )

    trigger = TriggerBlock(
        name="Access Request",
        trigger_type=TriggerType.ACCESS_REQUEST,
        position=BlockPosition(200, 50),
    )
    canvas.add_block(trigger)

    condition = ConditionBlock(
        name="High Risk Check",
        attribute=ConditionAttribute.RISK_SCORE,
        operator=ConditionOperator.GREATER_THAN,
        value=50,
        position=BlockPosition(200, 150),
    )
    canvas.add_block(condition)

    approval_group = ApprovalGroupBlock(
        name="Approvals",
        mode="PARALLEL",
        require_all=True,
        position=BlockPosition(200, 250),
    )
    approval_group.approvals = [
        ApprovalBlock(name="Manager", approver_type=ApproverType.LINE_MANAGER, sla_hours=24),
        ApprovalBlock(name="Security", approver_type=ApproverType.SECURITY_OFFICER, sla_hours=48),
    ]
    canvas.add_block(approval_group)

    gate = ProvisioningGateBlock(
        name="Provision Access",
        mode=ProvisioningMode.RISK_BASED,
        risk_threshold=50,
        position=BlockPosition(200, 350),
    )
    canvas.add_block(gate)

    canvas.connect(trigger.block_id, condition.block_id)
    canvas.connect(condition.block_id, approval_group.block_id, from_port="true")
    canvas.connect(approval_group.block_id, gate.block_id)

    return canvas


def create_partial_provisioning_template() -> WorkflowCanvas:
    """
    YOUR EXACT SCENARIO:
    2 roles → 2 approvers → provision approved role immediately.
    """
    canvas = WorkflowCanvas(
        name="Partial Provisioning Workflow",
        description="Provision approved roles immediately without waiting",
    )

    trigger = TriggerBlock(
        name="Access Request",
        trigger_type=TriggerType.ACCESS_REQUEST,
        position=BlockPosition(200, 50),
    )
    canvas.add_block(trigger)

    split = SplitBlock(
        name="Split by Role",
        split_by="ACCESS_ITEM",
        position=BlockPosition(200, 150),
    )
    canvas.add_block(split)

    # Per-item approval (the engine routes each item to appropriate approver)
    approval = ApprovalBlock(
        name="Role Owner Approval",
        approver_type=ApproverType.ROLE_OWNER,
        sla_hours=24,
        position=BlockPosition(200, 250),
    )
    canvas.add_block(approval)

    # THE KEY: Per-item provisioning
    gate = ProvisioningGateBlock(
        name="Provision Per Item",
        mode=ProvisioningMode.PER_ITEM,
        allow_partial=True,
        provision_immediately=True,
        position=BlockPosition(200, 350),
    )
    canvas.add_block(gate)

    notify = ActionBlock(
        name="Notify User",
        action_type=ActionType.NOTIFY_USER,
        position=BlockPosition(200, 450),
    )
    canvas.add_block(notify)

    canvas.connect(trigger.block_id, split.block_id)
    canvas.connect(split.block_id, approval.block_id)
    canvas.connect(approval.block_id, gate.block_id)
    canvas.connect(gate.block_id, notify.block_id)

    return canvas
