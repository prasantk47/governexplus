"""
Execution & Verification Engine — Data Models

Tracks the full provisioning lifecycle:
    Plan → Simulate → Execute → Target Response → Verify → Recalculate → Close
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any


class ExecutionPhase(enum.Enum):
    PLANNED = "planned"
    SIMULATED = "simulated"
    EXECUTING = "executing"
    EXECUTED = "executed"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ActionType(enum.Enum):
    ASSIGN_ROLE = "assign_role"
    REMOVE_ROLE = "remove_role"
    MODIFY_ROLE = "modify_role"
    LOCK_USER = "lock_user"
    UNLOCK_USER = "unlock_user"
    RESET_PASSWORD = "reset_password"
    CREATE_USER = "create_user"
    MODIFY_ORG_VALUES = "modify_org_values"
    TRANSPORT_ROLE = "transport_role"


class VerificationResult(enum.Enum):
    CONFIRMED = "confirmed"     # target state matches expected
    MISMATCH = "mismatch"       # target state differs from expected
    TIMEOUT = "timeout"         # verification timed out
    ERROR = "error"             # couldn't verify


@dataclass
class ExecutionAction:
    """A single provisioning action to execute on a target system."""
    action_id: str
    action_type: ActionType
    target_system: str = "SAP"
    target_client: str = ""

    # What to do
    user_id: str = ""
    role_id: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    # e.g., {"valid_from": "2026-01-01", "valid_to": "2026-12-31", "org_values": {"BUKRS": "1000"}}

    # Phase tracking
    phase: ExecutionPhase = ExecutionPhase.PLANNED

    # Simulation result
    simulation_result: Optional[str] = None
    simulation_warnings: list[str] = field(default_factory=list)

    # Execution result
    executed_at: Optional[datetime] = None
    target_response: Optional[str] = None
    target_message_id: Optional[str] = None  # SAP message/transport number

    # Verification
    verified_at: Optional[datetime] = None
    verification_result: Optional[VerificationResult] = None
    verification_details: str = ""

    # Rollback
    rollback_action_id: Optional[str] = None
    can_rollback: bool = True

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "target_system": self.target_system,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "parameters": self.parameters,
            "phase": self.phase.value,
            "simulation_result": self.simulation_result,
            "verification_result": self.verification_result.value if self.verification_result else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }


@dataclass
class ExecutionPlan:
    """A plan containing one or more actions to execute.

    Linked to an approved workflow/request.
    """
    plan_id: str
    request_id: str
    workflow_id: str
    user_id: str
    tenant_id: str

    actions: list[ExecutionAction] = field(default_factory=list)

    # Overall phase
    phase: ExecutionPhase = ExecutionPhase.PLANNED

    # Pre-execution risk snapshot
    pre_risk_score: float = 0.0
    pre_violation_count: int = 0

    # Post-execution risk (after verification)
    post_risk_score: Optional[float] = None
    post_violation_count: Optional[int] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    simulated_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    # Execution metadata
    executed_by: Optional[str] = None
    execution_mode: str = "manual"  # manual, scheduled, auto

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "phase": self.phase.value,
            "actions": [a.to_dict() for a in self.actions],
            "pre_risk_score": self.pre_risk_score,
            "post_risk_score": self.post_risk_score,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }
