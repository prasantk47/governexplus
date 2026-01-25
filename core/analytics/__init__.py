"""
Analytics Module

Real-time dashboards and analytics for GRC monitoring.
"""

from .dashboard import DashboardManager
from .metrics import MetricsCollector
from .approval_behavior import (
    ApprovalBehaviorEngine,
    ApproverProfile,
    ApprovalRecord,
    ApprovalAction,
    RiskBehaviorPattern,
    ApprovalAnomaly
)

__all__ = [
    'DashboardManager',
    'MetricsCollector',
    'ApprovalBehaviorEngine',
    'ApproverProfile',
    'ApprovalRecord',
    'ApprovalAction',
    'RiskBehaviorPattern',
    'ApprovalAnomaly'
]
