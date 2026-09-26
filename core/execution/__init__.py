"""
Execution & Verification Engine

Manages the provisioning lifecycle:
    Plan → Simulate → Execute → Target Response →
    Repository Sync → Verify Actual State →
    Recalculate Risk → Close
"""

from .engine import ExecutionEngine
from .models import (
    ActionType,
    ExecutionAction,
    ExecutionPhase,
    ExecutionPlan,
    VerificationResult,
)

__all__ = [
    "ExecutionEngine",
    "ActionType",
    "ExecutionAction",
    "ExecutionPhase",
    "ExecutionPlan",
    "VerificationResult",
]
