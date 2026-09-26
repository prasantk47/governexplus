"""
Process Control Module

Provides the full Process Control lifecycle for the GovernexPlus GRC platform:
  PC-01 / PC-04  — Control library CRUD and versioning
  PC-03 / XI-07  — Framework mapping (COSO, COBIT, ISO 27001, SOX, custom)
  PC-11          — Control testing (design / operating effectiveness)
  PC-12          — Control self-assessment campaigns
  PC-13          — Deficiency management and remediation tracking
  PC-14          — SOX-style cascading management sign-off
  PC-15          — Centralised evidence repository (with legal hold)
  PC-20 / PC-22  — Continuous Control Monitoring (CCM) rules and execution
  PC-24          — CCM dashboard
  PC-30 / PC-31  — Control and framework coverage dashboards
  PC-32          — Audit-ready package per control
"""

from .manager import ProcessControlManager

__all__ = ["ProcessControlManager"]
