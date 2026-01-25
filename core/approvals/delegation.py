# Delegation and Fallback Logic
# Enterprise-safe approval routing when primary approvers unavailable

"""
Delegation Manager for GOVERNEX+.

Handles:
- Automatic delegation when approver OOO
- SLA breach prevention escalation
- Conflict of interest detection
- Fallback chain: Primary → Delegate → Escalation Manager → Governance Desk
- Complete audit trail
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

from .models import Approver, ApproverType, ApprovalRequest, ApprovalStatus

logger = logging.getLogger(__name__)


class DelegationType(Enum):
    """Type of delegation."""
    PLANNED = "PLANNED"           # Scheduled OOO
    AUTOMATIC = "AUTOMATIC"       # System-triggered (SLA risk)
    CONFLICT = "CONFLICT"         # Conflict of interest
    ESCALATION = "ESCALATION"     # SLA breach escalation
    EMERGENCY = "EMERGENCY"       # Emergency override


class DelegationStatus(Enum):
    """Status of a delegation."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"


class ConflictType(Enum):
    """Types of conflict of interest."""
    SELF_APPROVAL = "SELF_APPROVAL"           # Approving own request
    DIRECT_REPORT = "DIRECT_REPORT"           # Approving direct report
    RECIPROCAL = "RECIPROCAL"                 # Recent mutual approvals
    FINANCIAL_INTEREST = "FINANCIAL_INTEREST" # Shared cost center
    ORGANIZATIONAL = "ORGANIZATIONAL"          # Same team/department


@dataclass
class Delegation:
    """A delegation of approval authority."""
    delegation_id: str
    delegator_id: str           # Who is delegating
    delegator_name: str
    delegate_id: str            # Who receives authority
    delegate_name: str

    delegation_type: DelegationType = DelegationType.PLANNED
    status: DelegationStatus = DelegationStatus.ACTIVE

    # Scope
    all_requests: bool = True
    request_types: List[str] = field(default_factory=list)
    systems: List[str] = field(default_factory=list)
    max_risk_level: Optional[int] = None  # Delegate can't approve above this

    # Validity
    valid_from: datetime = field(default_factory=datetime.now)
    valid_until: Optional[datetime] = None

    # Audit
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    reason: str = ""

    def is_valid(self) -> bool:
        """Check if delegation is currently valid."""
        now = datetime.now()
        if self.status != DelegationStatus.ACTIVE:
            return False
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def covers_request(self, request: ApprovalRequest) -> bool:
        """Check if this delegation covers a request."""
        if not self.is_valid():
            return False

        # Check risk level
        if self.max_risk_level is not None:
            if request.risk_score > self.max_risk_level:
                return False

        # Check scope
        if self.all_requests:
            return True

        if self.request_types and request.request_type not in self.request_types:
            return False

        if self.systems and request.system_id not in self.systems:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delegation_id": self.delegation_id,
            "delegator_id": self.delegator_id,
            "delegator_name": self.delegator_name,
            "delegate_id": self.delegate_id,
            "delegate_name": self.delegate_name,
            "delegation_type": self.delegation_type.value,
            "status": self.status.value,
            "scope": {
                "all_requests": self.all_requests,
                "request_types": self.request_types,
                "systems": self.systems,
                "max_risk_level": self.max_risk_level,
            },
            "valid_from": self.valid_from.isoformat(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "reason": self.reason,
        }


@dataclass
class ConflictOfInterest:
    """Detected conflict of interest."""
    conflict_type: ConflictType
    approver_id: str
    requester_id: str
    severity: str  # HIGH, MEDIUM, LOW
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_type": self.conflict_type.value,
            "approver_id": self.approver_id,
            "requester_id": self.requester_id,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
        }


@dataclass
class FallbackResult:
    """Result of fallback chain resolution."""
    success: bool
    original_approver: Approver
    resolved_approver: Approver

    # Chain
    fallback_chain: List[str] = field(default_factory=list)
    fallback_reason: str = ""

    # Delegation used
    delegation_used: Optional[Delegation] = None

    # Conflicts detected
    conflicts_bypassed: List[ConflictOfInterest] = field(default_factory=list)

    # Warnings
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "original_approver": self.original_approver.to_dict(),
            "resolved_approver": self.resolved_approver.to_dict(),
            "fallback_chain": self.fallback_chain,
            "fallback_reason": self.fallback_reason,
            "delegation_used": self.delegation_used.to_dict() if self.delegation_used else None,
            "conflicts_bypassed": [c.to_dict() for c in self.conflicts_bypassed],
            "warnings": self.warnings,
        }


class DelegationManager:
    """
    Manages approval delegation and fallback.

    Fallback chain:
    1. Primary Approver
    2. Active Delegate
    3. Escalation Manager
    4. Governance Desk

    All transitions logged for audit.
    """

    def __init__(self):
        """Initialize delegation manager."""
        self._delegations: Dict[str, Delegation] = {}
        self._approver_delegations: Dict[str, List[str]] = {}  # approver_id -> delegation_ids

        # Escalation config
        self._escalation_managers: Dict[str, str] = {}  # approver_id -> escalation_manager_id
        self._governance_desk_id: str = "GOVERNANCE_DESK"

        # SLA thresholds
        self._sla_warning_hours: float = 2.0   # Warn when 2 hours remaining
        self._sla_escalate_hours: float = 0.5  # Escalate when 30 min remaining

        # Conflict detection config
        self._reciprocal_window_days: int = 30
        self._reciprocal_threshold: int = 3  # 3+ mutual approvals = conflict

        # Audit log
        self._audit_log: List[Dict[str, Any]] = []

    def create_delegation(
        self,
        delegator: Approver,
        delegate: Approver,
        delegation_type: DelegationType = DelegationType.PLANNED,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        reason: str = "",
        scope: Optional[Dict[str, Any]] = None,
        created_by: str = ""
    ) -> Delegation:
        """
        Create a new delegation.

        Args:
            delegator: Approver delegating authority
            delegate: Approver receiving authority
            delegation_type: Type of delegation
            valid_from: Start of validity
            valid_until: End of validity
            reason: Reason for delegation
            scope: Optional scope restrictions
            created_by: User creating delegation

        Returns:
            Created Delegation
        """
        delegation_id = f"DEL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{delegator.approver_id[:8]}"

        delegation = Delegation(
            delegation_id=delegation_id,
            delegator_id=delegator.approver_id,
            delegator_name=delegator.approver_name,
            delegate_id=delegate.approver_id,
            delegate_name=delegate.approver_name,
            delegation_type=delegation_type,
            valid_from=valid_from or datetime.now(),
            valid_until=valid_until,
            reason=reason,
            created_by=created_by,
        )

        # Apply scope restrictions
        if scope:
            delegation.all_requests = scope.get("all_requests", True)
            delegation.request_types = scope.get("request_types", [])
            delegation.systems = scope.get("systems", [])
            delegation.max_risk_level = scope.get("max_risk_level")

        # Store
        self._delegations[delegation_id] = delegation

        if delegator.approver_id not in self._approver_delegations:
            self._approver_delegations[delegator.approver_id] = []
        self._approver_delegations[delegator.approver_id].append(delegation_id)

        # Audit
        self._log_event("DELEGATION_CREATED", {
            "delegation_id": delegation_id,
            "delegator": delegator.approver_id,
            "delegate": delegate.approver_id,
            "type": delegation_type.value,
            "reason": reason,
        })

        logger.info(f"Created delegation {delegation_id}: {delegator.approver_name} → {delegate.approver_name}")

        return delegation

    def revoke_delegation(self, delegation_id: str, revoked_by: str, reason: str = "") -> bool:
        """Revoke an active delegation."""
        delegation = self._delegations.get(delegation_id)
        if not delegation:
            return False

        delegation.status = DelegationStatus.REVOKED

        self._log_event("DELEGATION_REVOKED", {
            "delegation_id": delegation_id,
            "revoked_by": revoked_by,
            "reason": reason,
        })

        return True

    def get_active_delegate(
        self,
        approver: Approver,
        request: ApprovalRequest
    ) -> Optional[Tuple[Approver, Delegation]]:
        """
        Get active delegate for an approver.

        Args:
            approver: Primary approver
            request: Request needing approval

        Returns:
            Tuple of (delegate Approver, Delegation) or None
        """
        delegation_ids = self._approver_delegations.get(approver.approver_id, [])

        for delegation_id in delegation_ids:
            delegation = self._delegations.get(delegation_id)
            if delegation and delegation.covers_request(request):
                # Create delegate Approver object
                delegate = Approver(
                    approver_id=delegation.delegate_id,
                    approver_name=delegation.delegate_name,
                    approver_type=ApproverType.DELEGATE,
                )
                return (delegate, delegation)

        return None

    def detect_conflicts(
        self,
        approver: Approver,
        request: ApprovalRequest,
        approval_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[ConflictOfInterest]:
        """
        Detect conflicts of interest.

        Args:
            approver: Potential approver
            request: Request to approve
            approval_history: Optional history for reciprocal detection

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Self-approval
        if approver.approver_id == request.requester_id:
            conflicts.append(ConflictOfInterest(
                conflict_type=ConflictType.SELF_APPROVAL,
                approver_id=approver.approver_id,
                requester_id=request.requester_id,
                severity="HIGH",
                description="Approver cannot approve their own request",
                evidence={"same_user": True},
            ))

        # Direct report (if manager info available)
        if hasattr(request, 'requester_manager_id'):
            if approver.approver_id == request.requester_manager_id:
                pass  # This is expected - manager approving direct report
            elif hasattr(approver, 'manager_id') and approver.manager_id == request.requester_id:
                conflicts.append(ConflictOfInterest(
                    conflict_type=ConflictType.DIRECT_REPORT,
                    approver_id=approver.approver_id,
                    requester_id=request.requester_id,
                    severity="HIGH",
                    description="Approver reports to requester",
                    evidence={"reporting_relationship": "approver_reports_to_requester"},
                ))

        # Reciprocal approvals
        if approval_history:
            recent_mutual = self._check_reciprocal_approvals(
                approver.approver_id,
                request.requester_id,
                approval_history
            )
            if recent_mutual >= self._reciprocal_threshold:
                conflicts.append(ConflictOfInterest(
                    conflict_type=ConflictType.RECIPROCAL,
                    approver_id=approver.approver_id,
                    requester_id=request.requester_id,
                    severity="MEDIUM",
                    description=f"Found {recent_mutual} mutual approvals in last {self._reciprocal_window_days} days",
                    evidence={
                        "mutual_approval_count": recent_mutual,
                        "window_days": self._reciprocal_window_days,
                    },
                ))

        # Same cost center (financial interest)
        if hasattr(approver, 'cost_center') and hasattr(request, 'cost_center'):
            if approver.cost_center == request.cost_center:
                conflicts.append(ConflictOfInterest(
                    conflict_type=ConflictType.FINANCIAL_INTEREST,
                    approver_id=approver.approver_id,
                    requester_id=request.requester_id,
                    severity="LOW",
                    description="Approver shares cost center with request",
                    evidence={"cost_center": approver.cost_center},
                ))

        return conflicts

    def _check_reciprocal_approvals(
        self,
        approver_id: str,
        requester_id: str,
        history: List[Dict[str, Any]]
    ) -> int:
        """Check for reciprocal approval pattern."""
        cutoff = datetime.now() - timedelta(days=self._reciprocal_window_days)

        # Count where requester approved for approver
        count = 0
        for record in history:
            approved_at = record.get("approved_at")
            if isinstance(approved_at, str):
                approved_at = datetime.fromisoformat(approved_at)

            if approved_at and approved_at > cutoff:
                if (record.get("approver_id") == requester_id and
                    record.get("requester_id") == approver_id):
                    count += 1

        return count

    def resolve_fallback(
        self,
        primary_approver: Approver,
        request: ApprovalRequest,
        all_approvers: Dict[str, Approver],
        approval_history: Optional[List[Dict[str, Any]]] = None
    ) -> FallbackResult:
        """
        Resolve fallback chain for an unavailable approver.

        Chain:
        1. Primary Approver (if available and no conflicts)
        2. Active Delegate
        3. Escalation Manager
        4. Governance Desk

        Args:
            primary_approver: Original approver
            request: Request needing approval
            all_approvers: Available approvers
            approval_history: For conflict detection

        Returns:
            FallbackResult with resolved approver
        """
        result = FallbackResult(
            success=False,
            original_approver=primary_approver,
            resolved_approver=primary_approver,
            fallback_chain=[primary_approver.approver_id],
        )

        # Step 1: Check if primary is available and no conflicts
        if primary_approver.is_available and not primary_approver.is_ooo:
            conflicts = self.detect_conflicts(primary_approver, request, approval_history)
            high_severity = [c for c in conflicts if c.severity == "HIGH"]

            if not high_severity:
                result.success = True
                result.resolved_approver = primary_approver
                result.conflicts_bypassed = [c for c in conflicts if c.severity != "HIGH"]
                return result
            else:
                result.conflicts_bypassed = high_severity
                result.fallback_reason = f"Primary has conflict: {high_severity[0].description}"
        else:
            if primary_approver.is_ooo:
                result.fallback_reason = "Primary approver is out of office"
            else:
                result.fallback_reason = "Primary approver is unavailable"

        # Step 2: Try delegate
        delegate_result = self.get_active_delegate(primary_approver, request)
        if delegate_result:
            delegate, delegation = delegate_result
            result.fallback_chain.append(delegate.approver_id)

            # Check delegate conflicts
            conflicts = self.detect_conflicts(delegate, request, approval_history)
            high_severity = [c for c in conflicts if c.severity == "HIGH"]

            if not high_severity:
                result.success = True
                result.resolved_approver = delegate
                result.delegation_used = delegation
                result.conflicts_bypassed.extend([c for c in conflicts if c.severity != "HIGH"])

                self._log_event("DELEGATION_USED", {
                    "delegation_id": delegation.delegation_id,
                    "request_id": request.request_id,
                    "reason": result.fallback_reason,
                })

                return result
            else:
                result.fallback_reason = f"Delegate has conflict: {high_severity[0].description}"
                result.conflicts_bypassed.extend(high_severity)

        # Step 3: Try escalation manager
        escalation_manager_id = self._escalation_managers.get(primary_approver.approver_id)
        if escalation_manager_id and escalation_manager_id in all_approvers:
            escalation_manager = all_approvers[escalation_manager_id]
            result.fallback_chain.append(escalation_manager_id)

            conflicts = self.detect_conflicts(escalation_manager, request, approval_history)
            high_severity = [c for c in conflicts if c.severity == "HIGH"]

            if not high_severity:
                result.success = True
                result.resolved_approver = escalation_manager
                result.fallback_reason = "Escalated to escalation manager"

                self._log_event("ESCALATION_TRIGGERED", {
                    "request_id": request.request_id,
                    "from": primary_approver.approver_id,
                    "to": escalation_manager_id,
                    "reason": "primary_and_delegate_unavailable",
                })

                return result

        # Step 4: Governance Desk (last resort)
        if self._governance_desk_id in all_approvers:
            governance_desk = all_approvers[self._governance_desk_id]
            result.fallback_chain.append(self._governance_desk_id)
            result.success = True
            result.resolved_approver = governance_desk
            result.fallback_reason = "Escalated to Governance Desk"
            result.warnings.append("Request escalated to Governance Desk - manual review required")

            self._log_event("GOVERNANCE_DESK_ESCALATION", {
                "request_id": request.request_id,
                "original_approver": primary_approver.approver_id,
                "chain_attempted": result.fallback_chain,
            })

            return result

        # No resolution found
        result.success = False
        result.fallback_reason = "No available approver in fallback chain"
        result.warnings.append("CRITICAL: No approver available - request requires manual intervention")

        self._log_event("FALLBACK_FAILED", {
            "request_id": request.request_id,
            "original_approver": primary_approver.approver_id,
            "chain_attempted": result.fallback_chain,
        })

        return result

    def check_sla_risk(
        self,
        request: ApprovalRequest,
        current_approver: Approver,
        sla_hours: float
    ) -> Dict[str, Any]:
        """
        Check if request is at risk of SLA breach.

        Returns escalation recommendation if needed.
        """
        if not request.submitted_at:
            return {"at_risk": False}

        elapsed = (datetime.now() - request.submitted_at).total_seconds() / 3600
        remaining = sla_hours - elapsed

        result = {
            "elapsed_hours": round(elapsed, 2),
            "remaining_hours": round(remaining, 2),
            "sla_hours": sla_hours,
            "at_risk": False,
            "action": None,
        }

        if remaining <= 0:
            result["at_risk"] = True
            result["action"] = "SLA_BREACHED"
            result["recommendation"] = "Immediate escalation required"
        elif remaining <= self._sla_escalate_hours:
            result["at_risk"] = True
            result["action"] = "ESCALATE_NOW"
            result["recommendation"] = f"Only {remaining:.1f}h remaining - escalate immediately"
        elif remaining <= self._sla_warning_hours:
            result["at_risk"] = True
            result["action"] = "SEND_REMINDER"
            result["recommendation"] = f"{remaining:.1f}h remaining - send reminder to approver"

        return result

    def auto_escalate_sla_risk(
        self,
        request: ApprovalRequest,
        current_approver: Approver,
        sla_hours: float,
        all_approvers: Dict[str, Approver]
    ) -> Optional[FallbackResult]:
        """
        Automatically escalate if SLA breach imminent.

        Returns FallbackResult if escalation triggered.
        """
        sla_check = self.check_sla_risk(request, current_approver, sla_hours)

        if sla_check["action"] == "ESCALATE_NOW":
            # Create automatic delegation
            escalation_manager_id = self._escalation_managers.get(current_approver.approver_id)

            if escalation_manager_id and escalation_manager_id in all_approvers:
                escalation_manager = all_approvers[escalation_manager_id]

                # Create emergency delegation
                delegation = self.create_delegation(
                    delegator=current_approver,
                    delegate=escalation_manager,
                    delegation_type=DelegationType.AUTOMATIC,
                    valid_until=datetime.now() + timedelta(hours=24),
                    reason=f"Auto-escalation: SLA breach imminent for {request.request_id}",
                    created_by="SYSTEM",
                )

                result = FallbackResult(
                    success=True,
                    original_approver=current_approver,
                    resolved_approver=escalation_manager,
                    fallback_chain=[current_approver.approver_id, escalation_manager_id],
                    fallback_reason=f"Auto-escalated: {sla_check['remaining_hours']:.1f}h until SLA breach",
                    delegation_used=delegation,
                )

                self._log_event("AUTO_ESCALATION", {
                    "request_id": request.request_id,
                    "from": current_approver.approver_id,
                    "to": escalation_manager_id,
                    "remaining_hours": sla_check["remaining_hours"],
                })

                return result

        return None

    def set_escalation_manager(self, approver_id: str, escalation_manager_id: str) -> None:
        """Configure escalation manager for an approver."""
        self._escalation_managers[approver_id] = escalation_manager_id

    def set_governance_desk(self, governance_desk_id: str) -> None:
        """Configure governance desk ID."""
        self._governance_desk_id = governance_desk_id

    def get_delegations_for_approver(self, approver_id: str) -> List[Delegation]:
        """Get all delegations where approver is delegator."""
        delegation_ids = self._approver_delegations.get(approver_id, [])
        return [self._delegations[d_id] for d_id in delegation_ids if d_id in self._delegations]

    def get_delegations_as_delegate(self, delegate_id: str) -> List[Delegation]:
        """Get all delegations where user is delegate."""
        return [
            d for d in self._delegations.values()
            if d.delegate_id == delegate_id and d.is_valid()
        ]

    def _log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log audit event."""
        self._audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details,
        })

    def get_audit_log(
        self,
        since: Optional[datetime] = None,
        event_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        entries = self._audit_log

        if since:
            entries = [
                e for e in entries
                if datetime.fromisoformat(e["timestamp"]) >= since
            ]

        if event_types:
            entries = [e for e in entries if e["event_type"] in event_types]

        return entries

    def generate_delegation_report(self) -> Dict[str, Any]:
        """Generate delegation status report."""
        active = [d for d in self._delegations.values() if d.is_valid()]
        expired = [d for d in self._delegations.values() if d.status == DelegationStatus.EXPIRED]
        revoked = [d for d in self._delegations.values() if d.status == DelegationStatus.REVOKED]

        by_type = {}
        for d in active:
            t = d.delegation_type.value
            by_type[t] = by_type.get(t, 0) + 1

        return {
            "generated_at": datetime.now().isoformat(),
            "total_delegations": len(self._delegations),
            "active_delegations": len(active),
            "expired_delegations": len(expired),
            "revoked_delegations": len(revoked),
            "by_type": by_type,
            "recent_events": self._audit_log[-10:],
        }
