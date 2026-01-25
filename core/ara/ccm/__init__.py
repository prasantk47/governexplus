# Continuous Control Monitoring (CCM)
# Controls validated continuously, not annually

"""
Continuous Control Monitoring for GOVERNEX+.

CCM = controls continuously validated, not annually attested.

Control Types:
- Preventive: SoD enforcement
- Detective: Firefighter log review
- Corrective: Auto-revoke unused access
- Compensating: Dual approval

SAP GRC mostly stops at periodic review.
GOVERNEX+ runs controls as code, continuously.
"""

from .controls import (
    Control,
    ControlType,
    ControlFrequency,
    ControlStatus,
    ControlAssertion,
    ControlEvidence,
)

from .engine import (
    ControlEngine,
    ControlEvaluationResult,
    ControlViolation,
    ControlConfig,
)

from .monitoring import (
    ControlMonitor,
    MonitoringDashboard,
    ControlMetrics,
    ControlHealthScore,
)

from .library import (
    ControlLibrary,
    BUILTIN_CONTROLS,
)

__all__ = [
    # Controls
    "Control",
    "ControlType",
    "ControlFrequency",
    "ControlStatus",
    "ControlAssertion",
    "ControlEvidence",
    # Engine
    "ControlEngine",
    "ControlEvaluationResult",
    "ControlViolation",
    "ControlConfig",
    # Monitoring
    "ControlMonitor",
    "MonitoringDashboard",
    "ControlMetrics",
    "ControlHealthScore",
    # Library
    "ControlLibrary",
    "BUILTIN_CONTROLS",
]
