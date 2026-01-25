# SAP RFC Extractor Configuration
# Production settings for GOVERNEX+ SAP data extraction

"""
Configuration module for SAP RFC extractors.

Supports:
- Direct application server connection
- Message server load balancing
- SAProuter connections
- Connection pooling
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import os


@dataclass
class SAPExtractorConfig:
    """
    SAP RFC connection configuration.

    Attributes:
        ashost: Application server hostname
        sysnr: System number (00-99)
        client: SAP client number
        user: Service user for extraction
        passwd: Password (use environment variables in production)
        lang: Language code
        mshost: Message server host (for load balancing)
        group: Logon group (for load balancing)
        saprouter: SAProuter string (for external access)
        pool_size: Connection pool size
        timeout: RFC call timeout in seconds
    """
    # Required connection parameters
    ashost: str = ""
    sysnr: str = "00"
    client: str = "100"
    user: str = ""
    passwd: str = ""
    lang: str = "EN"

    # Optional: Message server for load balancing
    mshost: Optional[str] = None
    group: str = "PUBLIC"

    # Optional: SAProuter for external connections
    saprouter: Optional[str] = None

    # Connection pool settings
    pool_size: int = 5
    timeout: int = 120

    # Extraction settings
    batch_size: int = 1000
    max_rows: int = 100000

    # Audit settings
    audit_log_enabled: bool = True

    @classmethod
    def from_env(cls) -> "SAPExtractorConfig":
        """
        Load configuration from environment variables.

        Environment variables:
            SAP_ASHOST, SAP_SYSNR, SAP_CLIENT, SAP_USER, SAP_PASSWORD,
            SAP_LANG, SAP_MSHOST, SAP_GROUP, SAP_SAPROUTER
        """
        return cls(
            ashost=os.getenv("SAP_ASHOST", ""),
            sysnr=os.getenv("SAP_SYSNR", "00"),
            client=os.getenv("SAP_CLIENT", "100"),
            user=os.getenv("SAP_USER", ""),
            passwd=os.getenv("SAP_PASSWORD", ""),
            lang=os.getenv("SAP_LANG", "EN"),
            mshost=os.getenv("SAP_MSHOST"),
            group=os.getenv("SAP_GROUP", "PUBLIC"),
            saprouter=os.getenv("SAP_SAPROUTER"),
            pool_size=int(os.getenv("SAP_POOL_SIZE", "5")),
            timeout=int(os.getenv("SAP_TIMEOUT", "120")),
        )

    def to_rfc_params(self) -> Dict[str, Any]:
        """Convert to pyrfc connection parameters."""
        params = {
            "sysnr": self.sysnr,
            "client": self.client,
            "user": self.user,
            "passwd": self.passwd,
            "lang": self.lang,
        }

        # Direct connection vs. load balancing
        if self.mshost:
            params["mshost"] = self.mshost
            params["group"] = self.group
        else:
            params["ashost"] = self.ashost

        # SAProuter
        if self.saprouter:
            params["saprouter"] = self.saprouter

        return params


# Default configuration (override in production)
DEFAULT_CONFIG = SAPExtractorConfig(
    ashost="sap.example.com",
    sysnr="00",
    client="100",
    user="GOVERNEX_SVC",
    passwd="********",
    lang="EN"
)


# Sensitive tables for monitoring (from data dictionary)
SENSITIVE_TABLES = [
    "USR02",    # User master passwords
    "BSEG",     # Accounting line items
    "BKPF",     # Accounting document headers
    "EKKO",     # Purchasing document headers
    "EKPO",     # Purchasing line items
    "PA0008",   # HR Basic Pay
    "PA0001",   # HR Organizational Assignment
]


# Restricted transaction codes for firefighter monitoring
RESTRICTED_TCODES = [
    "SE38",     # ABAP Editor
    "SA38",     # ABAP Reporting
    "SM59",     # RFC Destinations
    "STMS",     # Transport Management
    "SCC4",     # Client Administration
    "SE16",     # Data Browser
    "SE16N",    # General Table Display
    "SM21",     # System Log
    "SM37",     # Background Jobs
    "SU01",     # User Maintenance
    "PFCG",     # Role Maintenance
    "SE11",     # ABAP Dictionary
    "SE80",     # Object Navigator
]


# Authorization objects tracked for audit
TRACKED_AUTH_OBJECTS = [
    "S_TCODE",      # Transaction execution
    "S_TABU_DIS",   # Table access
    "S_RFC",        # RFC calls
    "S_USER_GRP",   # User administration
    "S_DEVELOP",    # ABAP development
    "S_PROGRAM",    # Program execution
    "F_BKPF_BUK",   # Accounting company code
    "F_BKPF_KOA",   # Accounting account type
    "M_BEST_EKO",   # Purchasing organization
    "P_ORGIN",      # HR org authorization
]
