"""
Audit Evidence Center Package

Collects, packages, and exports structured audit evidence across all GRC
modules to support internal and external compliance reviews.
"""

from core.audit_evidence.collector import AuditEvidenceCollector, EvidencePackage, AuditSummary

__all__ = ["AuditEvidenceCollector", "EvidencePackage", "AuditSummary"]
