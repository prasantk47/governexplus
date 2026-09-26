"""
Core - Audit Management Module

Exposes the AuditManagementManager as the primary entry point for all
internal audit business logic (AM-01 through AM-31).
"""

from .manager import AuditManagementManager

__all__ = ["AuditManagementManager"]
