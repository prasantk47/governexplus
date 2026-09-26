"""
Role Drift Detection Package

Detects and reports on role definition drift across system landscapes
(DEV, QA, PROD) by comparing authorization values, org levels, and
version metadata.
"""

from core.drift.detector import DriftDetector, DriftReport, DriftSummary

__all__ = ["DriftDetector", "DriftReport", "DriftSummary"]
