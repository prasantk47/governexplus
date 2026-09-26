"""
Risk Management Module (RM-01 through RM-31)

Provides full enterprise risk management lifecycle:
  - Risk Register (RM-01)
  - Risk Assessment (RM-10, RM-11)
  - Risk Appetite (RM-03)
  - KRI Management (RM-13)
  - Risk Response (RM-20)
  - Incident Management (RM-22)
  - Heat Map & Reporting (RM-12, RM-30, RM-31)
  - Review Cycles (RM-23)
"""

from .manager import RiskManagementManager

__all__ = ["RiskManagementManager"]
