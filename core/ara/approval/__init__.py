# Risk-Based Auto-Approval Engine
# Reduce approval friction without reducing control

"""
Auto-Approval Engine for GOVERNEX+.

SAP GRC: approval = manual.
GOVERNEX+: approval = risk-adaptive.

Decision Model:
Risk Score | Decision
≤ 20       | Auto-approve
21–50      | Manager approval
51–80      | Security approval
> 80       | Deny + escalate

This enables:
- Faster low-risk provisioning
- Appropriate controls for high-risk access
- Audit trail for all decisions
"""

from .engine import (
    AutoApprovalEngine,
    ApprovalDecision,
    ApprovalLevel,
    ApprovalConfig,
    ApprovalRequest,
    ApprovalResult,
)

from .policies import (
    ApprovalPolicy,
    PolicyCondition,
    PolicyAction,
    PolicyEngine,
)

__all__ = [
    # Engine
    "AutoApprovalEngine",
    "ApprovalDecision",
    "ApprovalLevel",
    "ApprovalConfig",
    "ApprovalRequest",
    "ApprovalResult",
    # Policies
    "ApprovalPolicy",
    "PolicyCondition",
    "PolicyAction",
    "PolicyEngine",
]
