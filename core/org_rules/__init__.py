"""
Organizational Rules Engine

Manages SAP organizational-level access scoping rules including
Company Code, Plant, Purchasing Org, Sales Org, Cost Center, and Controlling Area.
"""

from .engine import OrgRulesEngine

__all__ = ["OrgRulesEngine"]
