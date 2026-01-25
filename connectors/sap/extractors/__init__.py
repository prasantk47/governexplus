# SAP RFC Extractors Package
# Production-grade extractors for GOVERNEX+ Firefighter audit data

"""
SAP RFC Extractors for GOVERNEX+ Firefighter

This package provides audit-grade data extraction from SAP systems using
RFC (Remote Function Call) interfaces. All extractors use only SAP-supported
data sources and methods.

Data Sources:
- USR02: User master data
- AGR_USERS: Role assignments
- AGR_DEFINE: Role definitions
- AGR_1251: Role authorization content
- SM20/RSAU: Security audit log
- STAD: Transaction usage statistics
- CDHDR/CDPOS: Change documents

Usage:
    from connectors.sap.extractors import FirefighterExtractor

    extractor = FirefighterExtractor()
    session_data = extractor.extract_session(
        ff_user="FF_FIN_01",
        from_date="20240101",
        to_date="20240131"
    )
"""

from .config import SAPExtractorConfig, DEFAULT_CONFIG
from .connection import SAPRFCConnectionManager
from .base import BaseExtractor
from .users import UserMasterExtractor
from .roles import RoleExtractor
from .authorizations import AuthorizationExtractor
from .audit_logs import SecurityAuditLogExtractor
from .tcode_usage import TransactionUsageExtractor
from .change_documents import ChangeDocumentExtractor
from .firefighter import FirefighterSessionExtractor
from .integration import FirefighterSAPIntegration, create_sap_integration

# HANA-optimized and enterprise features
from .tcode_usage_hana import HANAOptimizedTCodeExtractor, create_hana_extractor
from .state import (
    ExtractionStateManager,
    ExtractionState,
    get_last_run,
    update_last_run,
    get_delta_window,
)
from .utils import (
    retry,
    metrics,
    timed,
    rate_limited,
    RateLimiter,
    SAPErrorClassifier,
    get_metrics,
)

__all__ = [
    # Configuration
    "SAPExtractorConfig",
    "DEFAULT_CONFIG",
    # Connection
    "SAPRFCConnectionManager",
    # Base
    "BaseExtractor",
    # Extractors
    "UserMasterExtractor",
    "RoleExtractor",
    "AuthorizationExtractor",
    "SecurityAuditLogExtractor",
    "TransactionUsageExtractor",
    "ChangeDocumentExtractor",
    "FirefighterSessionExtractor",
    # HANA-optimized
    "HANAOptimizedTCodeExtractor",
    "create_hana_extractor",
    # State management (delta extraction)
    "ExtractionStateManager",
    "ExtractionState",
    "get_last_run",
    "update_last_run",
    "get_delta_window",
    # Utilities
    "retry",
    "metrics",
    "timed",
    "rate_limited",
    "RateLimiter",
    "SAPErrorClassifier",
    "get_metrics",
    # Integration
    "FirefighterSAPIntegration",
    "create_sap_integration",
]
