"""
Mass Administration Engine

Handles bulk operations on users and roles: import, role assignments,
role changes, ownership updates, locking, and async job tracking.
"""

from .engine import MassAdminEngine

__all__ = ["MassAdminEngine"]
