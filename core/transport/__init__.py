"""
Role Transport Management Module
Tracks SAP transports carrying role changes across DEV/QA/PROD systems.
"""

from .manager import TransportManager

__all__ = ["TransportManager"]
