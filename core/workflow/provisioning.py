# Provisioning Engine
# Item-level workflow with partial provisioning support

"""
Provisioning Engine for GOVERNEX+.

THIS IS THE KEY DIFFERENCE FROM MSMP:
- MSMP: Workflow finishes → Provision everything
- GOVERNEX+: Each item is an independent decision unit

Key Capabilities:
1. Item-Level Workflows
   - Each role/access in a request has its own approval chain
   - Different approvers for different items
   - Independent SLAs

2. Partial Provisioning (Vendor-Configurable)
   - Provision approved items immediately
   - Don't wait for entire request
   - Configurable strategies

3. Continuous Re-Evaluation
   - Risk changes → Re-evaluate provisioning
   - New approvals → Check provisioning gates
   - Event-driven, not path-locked

4. Vendor Customization
   - ALL_OR_NOTHING (MSMP-compatible)
   - PARTIAL_ALLOWED (default)
   - RISK_BASED_PARTIAL (smart hybrid)
   - TAG_BASED (business rules)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


# ============================================================
# PROVISIONING STRATEGIES (VENDOR-CONFIGURABLE)
# ============================================================

class ProvisioningStrategy(Enum):
    """
    Vendor-configurable provisioning strategies.

    Determines when items can be provisioned.
    """
    # MSMP-compatible: Wait for everything
    ALL_OR_NOTHING = "ALL_OR_NOTHING"

    # GOVERNEX+ default: Provision as items approve
    PER_ITEM = "PER_ITEM"

    # Smart: Partial only for low-risk items
    RISK_BASED = "RISK_BASED"

    # Business rules: Partial based on tags/categories
    TAG_BASED = "TAG_BASED"

    # Custom: Vendor-defined function
    CUSTOM = "CUSTOM"


class ItemStatus(Enum):
    """Status of an access item."""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"
    PROVISIONED = "PROVISIONED"
    PROVISION_FAILED = "PROVISION_FAILED"
    CANCELLED = "CANCELLED"
    ON_HOLD = "ON_HOLD"


class ProvisioningAction(Enum):
    """Actions that can be taken on an item."""
    PROVISION = "PROVISION"
    HOLD = "HOLD"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"
    RE_EVALUATE = "RE_EVALUATE"


# ============================================================
# ACCESS ITEM MODEL
# ============================================================

@dataclass
class AccessItem:
    """
    A single access item within a request.

    Each item is an independent decision unit with:
    - Its own risk score
    - Its own approvers
    - Its own provisioning gate
    - Its own SLA
    """
    item_id: str = field(default_factory=lambda: f"ITEM-{str(uuid.uuid4())[:8]}")

    # What is being requested
    access_type: str = "ROLE"  # ROLE, TCODE, PROFILE, ENTITLEMENT
    access_id: str = ""        # Role ID, TCode, etc.
    access_name: str = ""      # Human-readable name
    system_id: str = ""
    system_name: str = ""

    # Risk assessment (per item)
    risk_score: int = 0
    risk_level: str = "LOW"
    sod_conflicts: List[str] = field(default_factory=list)
    sensitive_data: List[str] = field(default_factory=list)

    # Categorization (for TAG_BASED provisioning)
    tags: List[str] = field(default_factory=list)
    category: str = ""  # FINANCIAL, HR, IT, GENERAL
    is_critical: bool = False
    is_privileged: bool = False

    # Status
    status: ItemStatus = ItemStatus.PENDING
    decision: Optional[str] = None  # APPROVED, REJECTED

    # Approvers (item-specific)
    required_approvers: List[str] = field(default_factory=list)
    approvals_received: List[Dict[str, Any]] = field(default_factory=list)
    rejections_received: List[Dict[str, Any]] = field(default_factory=list)

    # Provisioning
    provisioning_allowed: bool = False
    provisioned: bool = False
    provisioned_at: Optional[datetime] = None
    provision_result: str = ""

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    decided_at: Optional[datetime] = None

    # Audit
    history: List[Dict[str, Any]] = field(default_factory=list)

    def is_approved(self) -> bool:
        """Check if item is fully approved."""
        return self.status == ItemStatus.APPROVED

    def is_rejected(self) -> bool:
        """Check if item is rejected."""
        return self.status == ItemStatus.REJECTED

    def is_pending(self) -> bool:
        """Check if item is still pending."""
        return self.status in [ItemStatus.PENDING, ItemStatus.IN_PROGRESS]

    def is_provisionable(self) -> bool:
        """Check if item can be provisioned."""
        return self.is_approved() and self.provisioning_allowed and not self.provisioned

    def add_approval(self, approver_id: str, approver_name: str, comments: str = "") -> None:
        """Record an approval."""
        self.approvals_received.append({
            "approver_id": approver_id,
            "approver_name": approver_name,
            "comments": comments,
            "timestamp": datetime.now().isoformat(),
        })
        self._add_history("APPROVAL_RECEIVED", {
            "approver": approver_id,
            "comments": comments,
        })

    def add_rejection(self, approver_id: str, approver_name: str, reason: str = "") -> None:
        """Record a rejection."""
        self.rejections_received.append({
            "approver_id": approver_id,
            "approver_name": approver_name,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })
        self.status = ItemStatus.REJECTED
        self.decision = "REJECTED"
        self.decided_at = datetime.now()
        self._add_history("REJECTION_RECEIVED", {
            "approver": approver_id,
            "reason": reason,
        })

    def mark_approved(self) -> None:
        """Mark item as approved."""
        self.status = ItemStatus.APPROVED
        self.decision = "APPROVED"
        self.decided_at = datetime.now()
        self._add_history("ITEM_APPROVED", {
            "approvals": len(self.approvals_received),
        })

    def mark_provisioned(self, result: str = "SUCCESS") -> None:
        """Mark item as provisioned."""
        self.provisioned = True
        self.provisioned_at = datetime.now()
        self.provision_result = result
        self.status = ItemStatus.PROVISIONED
        self._add_history("ITEM_PROVISIONED", {
            "result": result,
        })

    def _add_history(self, event: str, details: Dict[str, Any]) -> None:
        """Add history entry."""
        self.history.append({
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "access_type": self.access_type,
            "access_id": self.access_id,
            "access_name": self.access_name,
            "system_id": self.system_id,
            "risk": {
                "score": self.risk_score,
                "level": self.risk_level,
                "sod_conflicts": self.sod_conflicts,
            },
            "tags": self.tags,
            "category": self.category,
            "status": self.status.value,
            "decision": self.decision,
            "approvals": len(self.approvals_received),
            "provisioned": self.provisioned,
            "provisioned_at": self.provisioned_at.isoformat() if self.provisioned_at else None,
        }


@dataclass
class AccessRequest:
    """
    A complete access request containing multiple items.

    In GOVERNEX+, the request is a container.
    Each item is an independent decision unit.
    """
    request_id: str = field(default_factory=lambda: f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6]}")

    # Requester
    requester_id: str = ""
    requester_name: str = ""
    requester_department: str = ""

    # Target user (may differ from requester)
    target_user_id: str = ""
    target_user_name: str = ""

    # Items (the independent decision units)
    items: List[AccessItem] = field(default_factory=list)

    # Request-level settings
    justification: str = ""
    business_case: str = ""
    is_emergency: bool = False
    is_temporary: bool = False
    duration_days: Optional[int] = None

    # Status (aggregate)
    status: str = "PENDING"  # PENDING, IN_PROGRESS, PARTIALLY_APPROVED, APPROVED, REJECTED

    # Timing
    submitted_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def get_pending_items(self) -> List[AccessItem]:
        """Get items still pending approval."""
        return [i for i in self.items if i.is_pending()]

    def get_approved_items(self) -> List[AccessItem]:
        """Get approved items."""
        return [i for i in self.items if i.is_approved()]

    def get_rejected_items(self) -> List[AccessItem]:
        """Get rejected items."""
        return [i for i in self.items if i.is_rejected()]

    def get_provisionable_items(self) -> List[AccessItem]:
        """Get items ready for provisioning."""
        return [i for i in self.items if i.is_provisionable()]

    def get_provisioned_items(self) -> List[AccessItem]:
        """Get already provisioned items."""
        return [i for i in self.items if i.provisioned]

    def update_status(self) -> None:
        """Update aggregate status based on items."""
        pending = len(self.get_pending_items())
        approved = len(self.get_approved_items())
        rejected = len(self.get_rejected_items())
        total = len(self.items)

        if rejected == total:
            self.status = "REJECTED"
        elif approved == total:
            self.status = "APPROVED"
        elif approved > 0 and pending > 0:
            self.status = "PARTIALLY_APPROVED"
        elif pending == 0:
            self.status = "COMPLETED"
        else:
            self.status = "IN_PROGRESS"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "requester": {
                "id": self.requester_id,
                "name": self.requester_name,
            },
            "target_user": {
                "id": self.target_user_id,
                "name": self.target_user_name,
            },
            "status": self.status,
            "items": [i.to_dict() for i in self.items],
            "summary": {
                "total": len(self.items),
                "pending": len(self.get_pending_items()),
                "approved": len(self.get_approved_items()),
                "rejected": len(self.get_rejected_items()),
                "provisioned": len(self.get_provisioned_items()),
            },
        }


# ============================================================
# PROVISIONING POLICY (VENDOR-CONFIGURABLE)
# ============================================================

@dataclass
class ProvisioningPolicy:
    """
    Vendor-configurable provisioning policy.

    This is where vendors customize behavior.
    """
    policy_id: str = "DEFAULT"
    name: str = "Default Provisioning Policy"

    # Strategy
    strategy: ProvisioningStrategy = ProvisioningStrategy.PER_ITEM

    # Risk-based settings (for RISK_BASED strategy)
    max_risk_for_partial: int = 50  # Only partial provision if risk <= this
    block_sod_items: bool = True    # Don't partial provision items with SoD

    # Tag-based settings (for TAG_BASED strategy)
    allowed_tags_for_partial: List[str] = field(default_factory=lambda: ["NON_CRITICAL", "STANDARD"])
    blocked_tags: List[str] = field(default_factory=lambda: ["FINANCIAL", "PRIVILEGED"])

    # Category-based settings
    allowed_categories_for_partial: List[str] = field(default_factory=lambda: ["GENERAL", "IT"])
    blocked_categories: List[str] = field(default_factory=lambda: ["FINANCIAL", "HR_SENSITIVE"])

    # Additional rules
    require_all_approvers: bool = False      # All approvers must approve
    allow_partial_on_rejection: bool = True  # Still provision approved items if some rejected
    provision_on_each_approval: bool = True  # Evaluate provisioning after each approval

    # Custom conditions (YAML-like)
    custom_conditions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "strategy": self.strategy.value,
            "risk_based": {
                "max_risk_for_partial": self.max_risk_for_partial,
                "block_sod_items": self.block_sod_items,
            },
            "tag_based": {
                "allowed_tags": self.allowed_tags_for_partial,
                "blocked_tags": self.blocked_tags,
            },
            "category_based": {
                "allowed_categories": self.allowed_categories_for_partial,
                "blocked_categories": self.blocked_categories,
            },
            "rules": {
                "require_all_approvers": self.require_all_approvers,
                "allow_partial_on_rejection": self.allow_partial_on_rejection,
                "provision_on_each_approval": self.provision_on_each_approval,
            },
        }

    def to_yaml(self) -> str:
        """Export policy to YAML format."""
        lines = []
        lines.append(f"policy_id: {self.policy_id}")
        lines.append(f"name: {self.name}")
        lines.append(f"strategy: {self.strategy.value}")
        lines.append("")
        lines.append("risk_based:")
        lines.append(f"  max_risk_for_partial: {self.max_risk_for_partial}")
        lines.append(f"  block_sod_items: {self.block_sod_items}")
        lines.append("")
        lines.append("tag_based:")
        lines.append(f"  allowed_tags: {self.allowed_tags_for_partial}")
        lines.append(f"  blocked_tags: {self.blocked_tags}")
        lines.append("")
        lines.append("rules:")
        lines.append(f"  require_all_approvers: {self.require_all_approvers}")
        lines.append(f"  allow_partial_on_rejection: {self.allow_partial_on_rejection}")
        lines.append(f"  provision_on_each_approval: {self.provision_on_each_approval}")
        return "\n".join(lines)


# ============================================================
# PROVISIONING GATE
# ============================================================

@dataclass
class ProvisioningGateResult:
    """Result of provisioning gate evaluation."""
    item_id: str
    action: ProvisioningAction
    allowed: bool
    reason: str
    conditions_checked: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "action": self.action.value,
            "allowed": self.allowed,
            "reason": self.reason,
            "conditions_checked": self.conditions_checked,
        }


class ProvisioningGate:
    """
    Evaluates whether an item can be provisioned.

    This is the decision engine that makes GOVERNEX+ different from MSMP.
    """

    def __init__(self, policy: Optional[ProvisioningPolicy] = None):
        """Initialize gate with policy."""
        self.policy = policy or ProvisioningPolicy()
        self._custom_evaluators: Dict[str, Callable] = {}

    def register_custom_evaluator(self, name: str, evaluator: Callable) -> None:
        """Register a custom provisioning evaluator."""
        self._custom_evaluators[name] = evaluator

    def evaluate(self, item: AccessItem, request: AccessRequest) -> ProvisioningGateResult:
        """
        Evaluate whether an item should be provisioned.

        This is called:
        - After each approval
        - After risk changes
        - After any relevant event
        """
        conditions_checked = []

        # Already provisioned
        if item.provisioned:
            return ProvisioningGateResult(
                item_id=item.item_id,
                action=ProvisioningAction.HOLD,
                allowed=False,
                reason="Item already provisioned",
            )

        # Not approved yet
        if not item.is_approved():
            conditions_checked.append("APPROVED: NO")
            return ProvisioningGateResult(
                item_id=item.item_id,
                action=ProvisioningAction.HOLD,
                allowed=False,
                reason="Item not yet approved",
                conditions_checked=conditions_checked,
            )

        conditions_checked.append("APPROVED: YES")

        # Apply strategy
        if self.policy.strategy == ProvisioningStrategy.ALL_OR_NOTHING:
            return self._evaluate_all_or_nothing(item, request, conditions_checked)

        elif self.policy.strategy == ProvisioningStrategy.PER_ITEM:
            return self._evaluate_per_item(item, request, conditions_checked)

        elif self.policy.strategy == ProvisioningStrategy.RISK_BASED:
            return self._evaluate_risk_based(item, request, conditions_checked)

        elif self.policy.strategy == ProvisioningStrategy.TAG_BASED:
            return self._evaluate_tag_based(item, request, conditions_checked)

        elif self.policy.strategy == ProvisioningStrategy.CUSTOM:
            return self._evaluate_custom(item, request, conditions_checked)

        # Default: allow
        return ProvisioningGateResult(
            item_id=item.item_id,
            action=ProvisioningAction.PROVISION,
            allowed=True,
            reason="Default: approved item can be provisioned",
            conditions_checked=conditions_checked,
        )

    def _evaluate_all_or_nothing(
        self,
        item: AccessItem,
        request: AccessRequest,
        conditions_checked: List[str]
    ) -> ProvisioningGateResult:
        """
        ALL_OR_NOTHING: MSMP-compatible behavior.

        Only provision when ALL items are approved.
        """
        pending = request.get_pending_items()
        rejected = request.get_rejected_items()

        conditions_checked.append(f"PENDING_ITEMS: {len(pending)}")
        conditions_checked.append(f"REJECTED_ITEMS: {len(rejected)}")

        if pending:
            return ProvisioningGateResult(
                item_id=item.item_id,
                action=ProvisioningAction.HOLD,
                allowed=False,
                reason=f"ALL_OR_NOTHING: {len(pending)} items still pending",
                conditions_checked=conditions_checked,
            )

        if rejected and not self.policy.allow_partial_on_rejection:
            return ProvisioningGateResult(
                item_id=item.item_id,
                action=ProvisioningAction.HOLD,
                allowed=False,
                reason=f"ALL_OR_NOTHING: {len(rejected)} items rejected, partial not allowed",
                conditions_checked=conditions_checked,
            )

        return ProvisioningGateResult(
            item_id=item.item_id,
            action=ProvisioningAction.PROVISION,
            allowed=True,
            reason="ALL_OR_NOTHING: All items decided, provisioning allowed",
            conditions_checked=conditions_checked,
        )

    def _evaluate_per_item(
        self,
        item: AccessItem,
        request: AccessRequest,
        conditions_checked: List[str]
    ) -> ProvisioningGateResult:
        """
        PER_ITEM: GOVERNEX+ default.

        Provision each approved item immediately.
        """
        conditions_checked.append("STRATEGY: PER_ITEM")

        return ProvisioningGateResult(
            item_id=item.item_id,
            action=ProvisioningAction.PROVISION,
            allowed=True,
            reason="PER_ITEM: Approved item can be provisioned immediately",
            conditions_checked=conditions_checked,
        )

    def _evaluate_risk_based(
        self,
        item: AccessItem,
        request: AccessRequest,
        conditions_checked: List[str]
    ) -> ProvisioningGateResult:
        """
        RISK_BASED: Smart partial provisioning.

        Only provision low-risk items early.
        """
        conditions_checked.append(f"ITEM_RISK: {item.risk_score}")
        conditions_checked.append(f"MAX_RISK_FOR_PARTIAL: {self.policy.max_risk_for_partial}")

        # Check risk threshold
        if item.risk_score > self.policy.max_risk_for_partial:
            conditions_checked.append("RISK_CHECK: FAILED")

            # Check if all high-risk items are decided
            pending_high_risk = [
                i for i in request.get_pending_items()
                if i.risk_score > self.policy.max_risk_for_partial
            ]

            if pending_high_risk:
                return ProvisioningGateResult(
                    item_id=item.item_id,
                    action=ProvisioningAction.HOLD,
                    allowed=False,
                    reason=f"RISK_BASED: High-risk item ({item.risk_score}), waiting for all high-risk items",
                    conditions_checked=conditions_checked,
                )

        conditions_checked.append("RISK_CHECK: PASSED")

        # Check SoD
        if self.policy.block_sod_items and item.sod_conflicts:
            conditions_checked.append(f"SOD_CONFLICTS: {len(item.sod_conflicts)}")
            return ProvisioningGateResult(
                item_id=item.item_id,
                action=ProvisioningAction.HOLD,
                allowed=False,
                reason=f"RISK_BASED: Item has SoD conflicts, partial not allowed",
                conditions_checked=conditions_checked,
            )

        return ProvisioningGateResult(
            item_id=item.item_id,
            action=ProvisioningAction.PROVISION,
            allowed=True,
            reason=f"RISK_BASED: Risk {item.risk_score} <= {self.policy.max_risk_for_partial}, provisioning allowed",
            conditions_checked=conditions_checked,
        )

    def _evaluate_tag_based(
        self,
        item: AccessItem,
        request: AccessRequest,
        conditions_checked: List[str]
    ) -> ProvisioningGateResult:
        """
        TAG_BASED: Business rule partial provisioning.

        Provision based on item tags/categories.
        """
        conditions_checked.append(f"ITEM_TAGS: {item.tags}")
        conditions_checked.append(f"ITEM_CATEGORY: {item.category}")

        # Check blocked tags
        for tag in item.tags:
            if tag in self.policy.blocked_tags:
                conditions_checked.append(f"BLOCKED_TAG: {tag}")
                return ProvisioningGateResult(
                    item_id=item.item_id,
                    action=ProvisioningAction.HOLD,
                    allowed=False,
                    reason=f"TAG_BASED: Item has blocked tag '{tag}'",
                    conditions_checked=conditions_checked,
                )

        # Check blocked categories
        if item.category in self.policy.blocked_categories:
            conditions_checked.append(f"BLOCKED_CATEGORY: {item.category}")
            return ProvisioningGateResult(
                item_id=item.item_id,
                action=ProvisioningAction.HOLD,
                allowed=False,
                reason=f"TAG_BASED: Item in blocked category '{item.category}'",
                conditions_checked=conditions_checked,
            )

        # Check allowed tags
        has_allowed_tag = any(tag in self.policy.allowed_tags_for_partial for tag in item.tags)
        in_allowed_category = item.category in self.policy.allowed_categories_for_partial

        if has_allowed_tag or in_allowed_category:
            conditions_checked.append("TAG_CHECK: PASSED")
            return ProvisioningGateResult(
                item_id=item.item_id,
                action=ProvisioningAction.PROVISION,
                allowed=True,
                reason="TAG_BASED: Item has allowed tag/category for partial provisioning",
                conditions_checked=conditions_checked,
            )

        # Default: hold for items without explicit allow
        return ProvisioningGateResult(
            item_id=item.item_id,
            action=ProvisioningAction.HOLD,
            allowed=False,
            reason="TAG_BASED: Item not in allowed tags/categories",
            conditions_checked=conditions_checked,
        )

    def _evaluate_custom(
        self,
        item: AccessItem,
        request: AccessRequest,
        conditions_checked: List[str]
    ) -> ProvisioningGateResult:
        """
        CUSTOM: Vendor-defined evaluation.

        Uses registered custom evaluators.
        """
        conditions_checked.append("STRATEGY: CUSTOM")

        for name, evaluator in self._custom_evaluators.items():
            try:
                result = evaluator(item, request, self.policy)
                if result is not None:
                    conditions_checked.append(f"CUSTOM_EVALUATOR: {name}")
                    return result
            except Exception as e:
                logger.error(f"Custom evaluator {name} failed: {e}")

        # Fallback to PER_ITEM
        return self._evaluate_per_item(item, request, conditions_checked)


# ============================================================
# PROVISIONING ENGINE
# ============================================================

@dataclass
class ProvisioningResult:
    """Result of provisioning execution."""
    request_id: str
    items_evaluated: int = 0
    items_provisioned: int = 0
    items_held: int = 0
    items_failed: int = 0
    details: List[ProvisioningGateResult] = field(default_factory=list)
    provisioned_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "items_evaluated": self.items_evaluated,
            "items_provisioned": self.items_provisioned,
            "items_held": self.items_held,
            "items_failed": self.items_failed,
            "provisioned_items": self.provisioned_items,
            "details": [d.to_dict() for d in self.details],
        }


class ProvisioningEngine:
    """
    Executes provisioning for access requests.

    This engine:
    1. Evaluates provisioning gates for all items
    2. Executes provisioning for allowed items
    3. Logs all decisions for audit
    """

    def __init__(
        self,
        policy: Optional[ProvisioningPolicy] = None,
        provision_callback: Optional[Callable[[AccessItem], bool]] = None
    ):
        """
        Initialize engine.

        Args:
            policy: Provisioning policy
            provision_callback: Function to execute actual provisioning
        """
        self.policy = policy or ProvisioningPolicy()
        self.gate = ProvisioningGate(self.policy)
        self._provision_callback = provision_callback or self._default_provision

        # Event log
        self._events: List[Dict[str, Any]] = []

    def _default_provision(self, item: AccessItem) -> bool:
        """Default provisioning callback (placeholder)."""
        logger.info(f"Provisioning item {item.item_id}: {item.access_name}")
        return True

    def set_provision_callback(self, callback: Callable[[AccessItem], bool]) -> None:
        """Set the provisioning callback."""
        self._provision_callback = callback

    def evaluate_request(self, request: AccessRequest) -> ProvisioningResult:
        """
        Evaluate provisioning for all items in a request.

        Called after:
        - Each approval
        - Risk score changes
        - Any relevant event
        """
        result = ProvisioningResult(request_id=request.request_id)

        for item in request.items:
            result.items_evaluated += 1

            # Evaluate gate
            gate_result = self.gate.evaluate(item, request)
            result.details.append(gate_result)

            # Update item provisioning flag
            item.provisioning_allowed = gate_result.allowed

            if gate_result.allowed:
                # Execute provisioning
                success = self._execute_provision(item)
                if success:
                    result.items_provisioned += 1
                    result.provisioned_items.append(item.item_id)
                else:
                    result.items_failed += 1
            else:
                result.items_held += 1

        # Log event
        self._log_event("PROVISIONING_EVALUATED", {
            "request_id": request.request_id,
            "result": result.to_dict(),
        })

        return result

    def _execute_provision(self, item: AccessItem) -> bool:
        """Execute provisioning for an item."""
        try:
            success = self._provision_callback(item)
            if success:
                item.mark_provisioned("SUCCESS")
                self._log_event("ITEM_PROVISIONED", {
                    "item_id": item.item_id,
                    "access": f"{item.access_type}:{item.access_id}",
                })
            else:
                item.status = ItemStatus.PROVISION_FAILED
                item.provision_result = "CALLBACK_FAILED"
                self._log_event("PROVISION_FAILED", {
                    "item_id": item.item_id,
                    "reason": "Callback returned failure",
                })
            return success
        except Exception as e:
            logger.error(f"Provisioning failed for {item.item_id}: {e}")
            item.status = ItemStatus.PROVISION_FAILED
            item.provision_result = str(e)
            self._log_event("PROVISION_ERROR", {
                "item_id": item.item_id,
                "error": str(e),
            })
            return False

    def record_approval(
        self,
        request: AccessRequest,
        item_id: str,
        approver_id: str,
        approver_name: str,
        comments: str = ""
    ) -> ProvisioningResult:
        """
        Record an approval and re-evaluate provisioning.

        This is the key integration point.
        """
        # Find item
        item = next((i for i in request.items if i.item_id == item_id), None)
        if not item:
            raise ValueError(f"Item {item_id} not found in request")

        # Record approval
        item.add_approval(approver_id, approver_name, comments)

        # Check if item is now fully approved
        if self._is_item_fully_approved(item):
            item.mark_approved()

        # Re-evaluate provisioning
        if self.policy.provision_on_each_approval:
            return self.evaluate_request(request)

        return ProvisioningResult(request_id=request.request_id)

    def record_rejection(
        self,
        request: AccessRequest,
        item_id: str,
        approver_id: str,
        approver_name: str,
        reason: str = ""
    ) -> ProvisioningResult:
        """Record a rejection and re-evaluate provisioning."""
        item = next((i for i in request.items if i.item_id == item_id), None)
        if not item:
            raise ValueError(f"Item {item_id} not found in request")

        item.add_rejection(approver_id, approver_name, reason)

        # Re-evaluate if partial provisioning allowed on rejection
        if self.policy.allow_partial_on_rejection:
            return self.evaluate_request(request)

        return ProvisioningResult(request_id=request.request_id)

    def _is_item_fully_approved(self, item: AccessItem) -> bool:
        """Check if item has all required approvals."""
        if self.policy.require_all_approvers:
            return len(item.approvals_received) >= len(item.required_approvers)
        else:
            # Any one approval is enough
            return len(item.approvals_received) > 0

    def _log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log an event."""
        self._events.append({
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        })

    def get_events(self, request_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get event log."""
        if request_id:
            return [e for e in self._events if e["details"].get("request_id") == request_id]
        return list(self._events)

    def explain_provisioning(self, request: AccessRequest) -> str:
        """
        Generate human-readable explanation of provisioning state.

        For requesters and auditors.
        """
        lines = []

        lines.append("=" * 60)
        lines.append("PROVISIONING STATUS")
        lines.append("=" * 60)
        lines.append("")

        lines.append(f"Request: {request.request_id}")
        lines.append(f"Strategy: {self.policy.strategy.value}")
        lines.append("")

        lines.append("Items Summary:")
        lines.append(f"  Total: {len(request.items)}")
        lines.append(f"  Provisioned: {len(request.get_provisioned_items())}")
        lines.append(f"  Approved (pending provision): {len([i for i in request.get_approved_items() if not i.provisioned])}")
        lines.append(f"  Pending approval: {len(request.get_pending_items())}")
        lines.append(f"  Rejected: {len(request.get_rejected_items())}")
        lines.append("")

        lines.append("Item Details:")
        lines.append("-" * 40)

        for item in request.items:
            icon = "✓" if item.provisioned else ("○" if item.is_pending() else ("✗" if item.is_rejected() else "⏳"))
            lines.append(f"{icon} {item.access_name} ({item.access_id})")
            lines.append(f"   Status: {item.status.value}")
            lines.append(f"   Risk: {item.risk_score} ({item.risk_level})")
            if item.provisioned:
                lines.append(f"   Provisioned: {item.provisioned_at.isoformat() if item.provisioned_at else 'Yes'}")
            elif item.is_approved():
                gate_result = self.gate.evaluate(item, request)
                lines.append(f"   Provision Status: {gate_result.reason}")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)


# ============================================================
# SAMPLE VENDOR POLICIES
# ============================================================

# MSMP-Compatible: Wait for everything
MSMP_COMPATIBLE_POLICY = ProvisioningPolicy(
    policy_id="MSMP_COMPATIBLE",
    name="MSMP-Compatible (All or Nothing)",
    strategy=ProvisioningStrategy.ALL_OR_NOTHING,
    allow_partial_on_rejection=False,
)

# GOVERNEX+ Default: Immediate partial provisioning
GOVERNEX_DEFAULT_POLICY = ProvisioningPolicy(
    policy_id="GOVERNEX_DEFAULT",
    name="GOVERNEX+ Default (Per Item)",
    strategy=ProvisioningStrategy.PER_ITEM,
    provision_on_each_approval=True,
)

# Risk-Based: Smart partial provisioning
RISK_BASED_POLICY = ProvisioningPolicy(
    policy_id="RISK_BASED",
    name="Risk-Based Partial Provisioning",
    strategy=ProvisioningStrategy.RISK_BASED,
    max_risk_for_partial=50,
    block_sod_items=True,
)

# Financial Sector: Strict for financial, lenient for others
FINANCIAL_SECTOR_POLICY = ProvisioningPolicy(
    policy_id="FINANCIAL_SECTOR",
    name="Financial Sector Policy",
    strategy=ProvisioningStrategy.TAG_BASED,
    blocked_tags=["FINANCIAL", "PAYMENT", "TREASURY"],
    blocked_categories=["FINANCIAL", "AP", "AR"],
    allowed_tags_for_partial=["DISPLAY", "REPORT", "NON_FINANCIAL"],
    allowed_categories_for_partial=["GENERAL", "HR_BASIC", "IT_BASIC"],
)
