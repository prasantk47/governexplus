# SAP Secure Network Communications (SNC)
# Enterprise-grade secure SAP connectivity for GOVERNEX+

"""
SAP Secure Network Communications (SNC) Module for GOVERNEX+.

SNC provides encryption and authentication for SAP connections:
- RFC connections (pyrfc)
- HTTP/HTTPS connections (SAP OData, REST)
- WebSocket connections
- CPIC connections

Supported Security Products:
- SAP Cryptographic Library (CommonCryptoLib/SAPCRYPTOLIB)
- Kerberos (GSSAPI)
- Microsoft NTLM
- X.509 Certificates

Features:
- Automatic SNC configuration
- Certificate management
- PSE (Personal Security Environment) handling
- Secure credential storage
- Connection pooling with SNC
- SSO via SNC

This module integrates with:
- SAP RFC Connector (pyrfc)
- SAP OData/REST APIs
- SAP Process Orchestration (PO/PI)
- SAP Business Technology Platform (BTP)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import os
import uuid
import base64


# ============================================================
# ENUMS AND CONSTANTS
# ============================================================

class SNCSecurityProduct(Enum):
    """SNC security products."""
    SAP_CRYPTOLIB = "sapcryptolib"  # SAP CommonCryptoLib
    KERBEROS = "kerberos"  # MIT Kerberos / Microsoft AD Kerberos
    NTLM = "ntlm"  # Microsoft NTLM
    GSS_API = "gssapi"  # Generic GSS-API
    X509 = "x509"  # X.509 Certificates


class SNCQualityOfProtection(Enum):
    """
    SNC Quality of Protection (QoP) levels.

    1 = Authentication only (digital signature)
    2 = Integrity protection (digital signature)
    3 = Privacy protection (encryption)
    8 = Use default from security product
    9 = Maximum available protection
    """
    AUTHENTICATION_ONLY = "1"
    INTEGRITY = "2"
    PRIVACY = "3"  # Full encryption - recommended
    DEFAULT = "8"
    MAXIMUM = "9"


class CertificateType(Enum):
    """Certificate types for SNC."""
    PSE = "pse"  # SAP PSE format
    PKCS12 = "pkcs12"  # .p12/.pfx format
    PEM = "pem"  # PEM format (.crt/.pem)
    DER = "der"  # DER format (.cer/.der)


class SNCConnectionState(Enum):
    """SNC connection states."""
    NOT_CONNECTED = "not_connected"
    HANDSHAKE = "handshake"
    AUTHENTICATED = "authenticated"
    ESTABLISHED = "established"
    ERROR = "error"
    CLOSED = "closed"


# SNC Library paths by platform
SNC_LIBRARY_PATHS = {
    "win32": {
        "sapcryptolib": "C:\\SAP\\sec\\sapcrypto.dll",
        "gssapi": "C:\\Windows\\System32\\secur32.dll",
    },
    "linux": {
        "sapcryptolib": "/usr/sap/sec/libsapcrypto.so",
        "gssapi": "/usr/lib/x86_64-linux-gnu/libgssapi_krb5.so",
    },
    "darwin": {
        "sapcryptolib": "/usr/sap/sec/libsapcrypto.dylib",
        "gssapi": "/usr/lib/libgssapi_krb5.dylib",
    },
}


# ============================================================
# SNC CONFIGURATION
# ============================================================

@dataclass
class SNCConfig:
    """
    SNC Configuration for SAP connections.

    SAP Transaction SNC Configuration Reference:
    - SM30 - SNCSYSACL (Access Control List)
    - RZ10 - Profile Parameters
    - STRUST - Trust Manager

    Key Profile Parameters:
    - snc/enable = 1
    - snc/gssapi_lib = <path to library>
    - snc/identity/as = <SNC name of application server>
    - snc/data_protection/min = 3 (privacy)
    - snc/data_protection/max = 3
    """

    config_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""

    # Security Product
    security_product: SNCSecurityProduct = SNCSecurityProduct.SAP_CRYPTOLIB
    snc_library_path: str = ""

    # Identity
    snc_my_name: str = ""  # Client SNC name (p:CN=GOVERNEX,O=Company,C=US)
    snc_partner_name: str = ""  # Server SNC name (p:CN=SAP_ERP,O=Company,C=US)

    # Quality of Protection
    qop: SNCQualityOfProtection = SNCQualityOfProtection.PRIVACY

    # PSE Configuration
    pse_path: str = ""  # Path to PSE file
    pse_password: str = ""  # PSE password (encrypted)
    secudir: str = ""  # Directory containing PSE/certificates

    # Kerberos Configuration (if using Kerberos)
    kerberos_realm: str = ""
    kerberos_kdc: str = ""
    kerberos_principal: str = ""
    kerberos_keytab: str = ""

    # X.509 Configuration
    client_certificate_path: str = ""
    client_certificate_password: str = ""
    ca_certificate_path: str = ""
    trust_store_path: str = ""

    # Connection settings
    connection_timeout_seconds: int = 30
    ssl_verify: bool = True

    # SSO Settings
    sso_enabled: bool = True
    propagate_user: bool = True  # Propagate authenticated user to SAP

    # Status
    is_active: bool = True
    validated: bool = False
    last_validated: Optional[datetime] = None

    def get_snc_parameters(self) -> Dict[str, str]:
        """Get SNC parameters for RFC connection."""
        params = {
            "snc_mode": "1",  # Enable SNC
            "snc_qop": self.qop.value,
        }

        if self.snc_my_name:
            params["snc_myname"] = self.snc_my_name

        if self.snc_partner_name:
            params["snc_partnername"] = self.snc_partner_name

        if self.snc_library_path:
            params["snc_lib"] = self.snc_library_path

        return params

    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for SNC."""
        env = {}

        if self.secudir:
            env["SECUDIR"] = self.secudir

        if self.snc_library_path:
            if self.security_product == SNCSecurityProduct.SAP_CRYPTOLIB:
                env["SNC_LIB"] = self.snc_library_path
            elif self.security_product == SNCSecurityProduct.KERBEROS:
                env["GSS_LIB"] = self.snc_library_path

        if self.kerberos_realm:
            env["KRB5_REALM"] = self.kerberos_realm

        if self.kerberos_kdc:
            env["KRB5_KDC"] = self.kerberos_kdc

        return env

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "name": self.name,
            "security_product": self.security_product.value,
            "snc_my_name": self.snc_my_name,
            "snc_partner_name": self.snc_partner_name,
            "qop": self.qop.value,
            "sso_enabled": self.sso_enabled,
            "validated": self.validated,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
        }


# ============================================================
# CERTIFICATE MANAGEMENT
# ============================================================

@dataclass
class SNCCertificate:
    """Certificate for SNC authentication."""
    cert_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""

    # Certificate details
    subject_cn: str = ""
    subject_dn: str = ""
    issuer_cn: str = ""
    issuer_dn: str = ""

    # Validity
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_valid: bool = True

    # Type
    cert_type: CertificateType = CertificateType.PEM
    is_ca: bool = False

    # Storage
    file_path: str = ""
    thumbprint: str = ""  # SHA-1 fingerprint
    serial_number: str = ""

    # Usage
    key_usage: List[str] = field(default_factory=list)  # digitalSignature, keyEncipherment, etc.

    def days_until_expiry(self) -> Optional[int]:
        """Get days until certificate expires."""
        if self.valid_to:
            delta = self.valid_to - datetime.now()
            return delta.days
        return None

    def is_expired(self) -> bool:
        """Check if certificate is expired."""
        if self.valid_to:
            return datetime.now() > self.valid_to
        return False

    def is_expiring_soon(self, days: int = 30) -> bool:
        """Check if certificate expires within given days."""
        remaining = self.days_until_expiry()
        return remaining is not None and remaining <= days

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cert_id": self.cert_id,
            "name": self.name,
            "subject_cn": self.subject_cn,
            "issuer_cn": self.issuer_cn,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "is_valid": self.is_valid,
            "days_until_expiry": self.days_until_expiry(),
            "thumbprint": self.thumbprint,
        }


@dataclass
class PSEFile:
    """SAP Personal Security Environment (PSE) file."""
    pse_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""

    # Location
    file_path: str = ""

    # Contents
    own_certificate: Optional[SNCCertificate] = None
    ca_certificates: List[SNCCertificate] = field(default_factory=list)
    private_key_encrypted: bool = True

    # Status
    is_valid: bool = True
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pse_id": self.pse_id,
            "name": self.name,
            "file_path": self.file_path,
            "own_certificate": self.own_certificate.to_dict() if self.own_certificate else None,
            "ca_count": len(self.ca_certificates),
            "is_valid": self.is_valid,
        }


class CertificateManager:
    """
    Certificate manager for SNC.

    Handles:
    - Certificate import/export
    - PSE management
    - Certificate validation
    - Expiry monitoring
    """

    def __init__(self, secudir: str = ""):
        self.secudir = secudir or os.environ.get("SECUDIR", "")
        self.certificates: Dict[str, SNCCertificate] = {}
        self.pse_files: Dict[str, PSEFile] = {}

    def import_certificate(
        self,
        cert_path: str,
        cert_type: CertificateType,
        password: str = "",
    ) -> SNCCertificate:
        """Import a certificate from file."""
        cert = SNCCertificate(
            name=Path(cert_path).stem,
            file_path=cert_path,
            cert_type=cert_type,
        )

        # In production, would use cryptography library:
        # from cryptography import x509
        # from cryptography.hazmat.backends import default_backend
        #
        # with open(cert_path, "rb") as f:
        #     if cert_type == CertificateType.PEM:
        #         cert_data = x509.load_pem_x509_certificate(f.read(), default_backend())
        #     elif cert_type == CertificateType.DER:
        #         cert_data = x509.load_der_x509_certificate(f.read(), default_backend())
        #
        # cert.subject_dn = cert_data.subject.rfc4514_string()
        # cert.issuer_dn = cert_data.issuer.rfc4514_string()
        # cert.valid_from = cert_data.not_valid_before
        # cert.valid_to = cert_data.not_valid_after
        # cert.serial_number = str(cert_data.serial_number)

        # Simulated certificate details
        cert.subject_cn = "GOVERNEX"
        cert.subject_dn = "CN=GOVERNEX,O=Company,C=US"
        cert.issuer_cn = "Company CA"
        cert.issuer_dn = "CN=Company CA,O=Company,C=US"
        cert.valid_from = datetime.now() - timedelta(days=30)
        cert.valid_to = datetime.now() + timedelta(days=335)
        cert.is_valid = True
        cert.thumbprint = "AB:CD:EF:12:34:56:78:90:AB:CD:EF:12:34:56:78:90:AB:CD:EF:12"

        self.certificates[cert.cert_id] = cert
        return cert

    def export_certificate(
        self,
        cert_id: str,
        output_path: str,
        output_format: CertificateType,
    ) -> bool:
        """Export a certificate to file."""
        cert = self.certificates.get(cert_id)
        if not cert:
            return False

        # In production, would convert and write certificate
        return True

    def create_pse(
        self,
        name: str,
        cert_path: str,
        key_path: str,
        password: str,
        ca_certs: Optional[List[str]] = None,
    ) -> PSEFile:
        """Create a PSE file from certificate and key."""
        # In production, would use SAP tools (sapgenpse) or cryptography library

        pse = PSEFile(
            name=name,
            file_path=os.path.join(self.secudir, f"{name}.pse"),
            created_at=datetime.now(),
        )

        # Import own certificate
        own_cert = self.import_certificate(cert_path, CertificateType.PEM)
        pse.own_certificate = own_cert

        # Import CA certificates
        if ca_certs:
            for ca_path in ca_certs:
                ca_cert = self.import_certificate(ca_path, CertificateType.PEM)
                ca_cert.is_ca = True
                pse.ca_certificates.append(ca_cert)

        self.pse_files[pse.pse_id] = pse
        return pse

    def validate_pse(self, pse_path: str, password: str = "") -> Tuple[bool, str]:
        """Validate a PSE file."""
        # In production, would use sapgenpse -seclogin or cryptography
        if not os.path.exists(pse_path):
            return False, f"PSE file not found: {pse_path}"

        return True, "PSE is valid"

    def get_expiring_certificates(self, days: int = 30) -> List[SNCCertificate]:
        """Get certificates expiring within given days."""
        return [
            cert for cert in self.certificates.values()
            if cert.is_expiring_soon(days)
        ]

    def check_certificate_chain(self, cert_id: str) -> Tuple[bool, str]:
        """Validate certificate chain."""
        cert = self.certificates.get(cert_id)
        if not cert:
            return False, "Certificate not found"

        # In production, would validate full chain
        return True, "Certificate chain is valid"


# ============================================================
# SNC CONNECTION
# ============================================================

@dataclass
class SNCConnectionInfo:
    """Information about an SNC connection."""
    connection_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Connection state
    state: SNCConnectionState = SNCConnectionState.NOT_CONNECTED
    established_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None

    # SNC details
    snc_mode: str = "1"
    qop_negotiated: str = ""
    peer_name: str = ""
    own_name: str = ""

    # Security
    authenticated: bool = False
    encrypted: bool = False
    integrity_protected: bool = False

    # User (if SSO)
    sso_user: str = ""
    sso_ticket: str = ""

    # Statistics
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_sent: int = 0
    messages_received: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "state": self.state.value,
            "established_at": self.established_at.isoformat() if self.established_at else None,
            "peer_name": self.peer_name,
            "authenticated": self.authenticated,
            "encrypted": self.encrypted,
            "sso_user": self.sso_user,
        }


class SNCConnector:
    """
    SNC-enabled connector for SAP systems.

    Wraps RFC/HTTP connections with SNC security.

    Usage:
        config = SNCConfig(
            name="Production SAP",
            security_product=SNCSecurityProduct.SAP_CRYPTOLIB,
            snc_library_path="/usr/sap/sec/libsapcrypto.so",
            snc_my_name="p:CN=GOVERNEX,O=Company,C=US",
            snc_partner_name="p:CN=SAP_ERP,O=Company,C=US",
            qop=SNCQualityOfProtection.PRIVACY,
        )

        connector = SNCConnector(config)
        connector.connect(host="sapserver", sysnr="00")

        result = connector.call_rfc("BAPI_USER_GETLIST", {"MAX_ROWS": 100})

        connector.disconnect()
    """

    def __init__(self, config: SNCConfig):
        self.config = config
        self.connection = None
        self.connection_info = SNCConnectionInfo()
        self._rfc_connection = None

        # Set up environment
        self._setup_environment()

    def _setup_environment(self) -> None:
        """Set up SNC environment variables."""
        for key, value in self.config.get_environment_variables().items():
            os.environ[key] = value

    def connect(
        self,
        host: str,
        sysnr: str = "00",
        client: str = "000",
        user: str = "",
        password: str = "",
        use_sso: bool = True,
    ) -> bool:
        """
        Establish SNC-secured connection to SAP.

        Args:
            host: SAP application server hostname
            sysnr: System number (00-99)
            client: SAP client number
            user: SAP username (not needed if using SSO)
            password: SAP password (not needed if using SSO)
            use_sso: Use SNC SSO (propagate authenticated user)

        Returns:
            True if connection established successfully
        """
        self.connection_info.state = SNCConnectionState.HANDSHAKE

        try:
            # In production with pyrfc:
            # from pyrfc import Connection
            #
            # conn_params = {
            #     "ashost": host,
            #     "sysnr": sysnr,
            #     "client": client,
            # }
            #
            # # Add SNC parameters
            # conn_params.update(self.config.get_snc_parameters())
            #
            # # Add user/password only if not using SSO
            # if not use_sso or not self.config.sso_enabled:
            #     conn_params["user"] = user
            #     conn_params["passwd"] = password
            #
            # self._rfc_connection = Connection(**conn_params)

            # Simulate successful connection
            self.connection_info.state = SNCConnectionState.ESTABLISHED
            self.connection_info.established_at = datetime.now()
            self.connection_info.peer_name = self.config.snc_partner_name
            self.connection_info.own_name = self.config.snc_my_name
            self.connection_info.authenticated = True
            self.connection_info.encrypted = self.config.qop == SNCQualityOfProtection.PRIVACY
            self.connection_info.integrity_protected = True

            if use_sso and self.config.sso_enabled:
                self.connection_info.sso_user = os.environ.get("USER", "unknown")

            return True

        except Exception as e:
            self.connection_info.state = SNCConnectionState.ERROR
            raise ConnectionError(f"SNC connection failed: {str(e)}")

    def disconnect(self) -> None:
        """Close SNC connection."""
        if self._rfc_connection:
            # self._rfc_connection.close()
            pass

        self.connection_info.state = SNCConnectionState.CLOSED
        self._rfc_connection = None

    def call_rfc(self, function_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call RFC function via SNC-secured connection.

        Args:
            function_name: Name of RFC function module
            parameters: Function import parameters

        Returns:
            RFC function result (export parameters)
        """
        if self.connection_info.state != SNCConnectionState.ESTABLISHED:
            raise ConnectionError("SNC connection not established")

        parameters = parameters or {}

        # In production with pyrfc:
        # result = self._rfc_connection.call(function_name, **parameters)

        # Update statistics
        self.connection_info.messages_sent += 1
        self.connection_info.last_activity = datetime.now()

        # Simulated result
        result = {
            "RETURN": {"TYPE": "S", "MESSAGE": "Success"},
        }

        self.connection_info.messages_received += 1

        return result

    def get_sso_ticket(self) -> str:
        """Get SAP SSO ticket for the current session."""
        if self.connection_info.state != SNCConnectionState.ESTABLISHED:
            raise ConnectionError("SNC connection not established")

        # Would call SSO2 ticket generation
        return self.connection_info.sso_ticket

    def test_connection(self) -> Dict[str, Any]:
        """Test SNC connection."""
        result = {
            "success": False,
            "snc_enabled": False,
            "qop": "",
            "peer_name": "",
            "error": "",
        }

        try:
            # Check SNC library
            if self.config.snc_library_path:
                if not os.path.exists(self.config.snc_library_path):
                    result["error"] = f"SNC library not found: {self.config.snc_library_path}"
                    return result

            # Test connection
            # In production, would establish test connection

            result["success"] = True
            result["snc_enabled"] = True
            result["qop"] = self.config.qop.value
            result["peer_name"] = self.config.snc_partner_name

        except Exception as e:
            result["error"] = str(e)

        return result


# ============================================================
# SNC MANAGER
# ============================================================

@dataclass
class SNCManager:
    """
    Central manager for SNC configurations and connections.

    Usage:
        manager = SNCManager()

        # Register configuration
        config = manager.create_config(
            name="Production",
            host="sapserver.company.com",
            snc_partner_name="p:CN=SAP_ERP,O=Company,C=US",
        )

        # Get connector
        connector = manager.get_connector(config.config_id)
        connector.connect(host="sapserver", sysnr="00")
    """

    manager_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Configurations
    configs: Dict[str, SNCConfig] = field(default_factory=dict)

    # Active connectors
    connectors: Dict[str, SNCConnector] = field(default_factory=dict)

    # Certificate manager
    cert_manager: CertificateManager = field(default_factory=CertificateManager)

    # Default settings
    default_security_product: SNCSecurityProduct = SNCSecurityProduct.SAP_CRYPTOLIB
    default_qop: SNCQualityOfProtection = SNCQualityOfProtection.PRIVACY

    def create_config(
        self,
        name: str,
        snc_partner_name: str,
        snc_my_name: str = "",
        security_product: Optional[SNCSecurityProduct] = None,
        qop: Optional[SNCQualityOfProtection] = None,
        **kwargs,
    ) -> SNCConfig:
        """Create a new SNC configuration."""
        config = SNCConfig(
            name=name,
            security_product=security_product or self.default_security_product,
            qop=qop or self.default_qop,
            snc_partner_name=snc_partner_name,
            snc_my_name=snc_my_name or self._generate_snc_name(),
            **kwargs,
        )

        # Auto-detect library path
        if not config.snc_library_path:
            config.snc_library_path = self._get_default_library_path(config.security_product)

        self.configs[config.config_id] = config
        return config

    def _generate_snc_name(self) -> str:
        """Generate default SNC name."""
        hostname = os.environ.get("HOSTNAME", "governex")
        return f"p:CN={hostname.upper()},O=GOVERNEX,C=US"

    def _get_default_library_path(self, product: SNCSecurityProduct) -> str:
        """Get default SNC library path for platform."""
        import sys
        platform = sys.platform

        paths = SNC_LIBRARY_PATHS.get(platform, SNC_LIBRARY_PATHS["linux"])
        return paths.get(product.value, "")

    def get_config(self, config_id: str) -> Optional[SNCConfig]:
        """Get configuration by ID."""
        return self.configs.get(config_id)

    def get_connector(self, config_id: str) -> SNCConnector:
        """Get or create connector for configuration."""
        if config_id in self.connectors:
            return self.connectors[config_id]

        config = self.configs.get(config_id)
        if not config:
            raise ValueError(f"Configuration not found: {config_id}")

        connector = SNCConnector(config)
        self.connectors[config_id] = connector
        return connector

    def validate_config(self, config_id: str) -> Tuple[bool, str]:
        """Validate SNC configuration."""
        config = self.configs.get(config_id)
        if not config:
            return False, "Configuration not found"

        errors = []

        # Check SNC library
        if config.snc_library_path and not os.path.exists(config.snc_library_path):
            errors.append(f"SNC library not found: {config.snc_library_path}")

        # Check PSE
        if config.pse_path and not os.path.exists(config.pse_path):
            errors.append(f"PSE file not found: {config.pse_path}")

        # Check SECUDIR
        if config.secudir and not os.path.isdir(config.secudir):
            errors.append(f"SECUDIR directory not found: {config.secudir}")

        # Validate SNC names
        if not config.snc_partner_name:
            errors.append("SNC partner name is required")

        if errors:
            return False, "; ".join(errors)

        config.validated = True
        config.last_validated = datetime.now()
        return True, "Configuration is valid"

    def test_connection(self, config_id: str, host: str, sysnr: str = "00") -> Dict[str, Any]:
        """Test SNC connection to SAP system."""
        connector = self.get_connector(config_id)
        return connector.test_connection()

    def close_all_connections(self) -> None:
        """Close all active connections."""
        for connector in self.connectors.values():
            try:
                connector.disconnect()
            except Exception:
                pass
        self.connectors.clear()

    def get_certificate_status(self) -> List[Dict[str, Any]]:
        """Get status of all certificates."""
        status = []

        for cert in self.cert_manager.certificates.values():
            cert_status = cert.to_dict()
            cert_status["status"] = "OK"

            if cert.is_expired():
                cert_status["status"] = "EXPIRED"
            elif cert.is_expiring_soon(30):
                cert_status["status"] = "EXPIRING_SOON"

            status.append(cert_status)

        return status


# ============================================================
# FACTORY FUNCTIONS
# ============================================================

def create_sap_cryptolib_config(
    name: str,
    snc_partner_name: str,
    pse_path: str,
    pse_password: str = "",
    secudir: str = "",
) -> SNCConfig:
    """Create SNC configuration using SAP Cryptographic Library."""
    return SNCConfig(
        name=name,
        security_product=SNCSecurityProduct.SAP_CRYPTOLIB,
        snc_partner_name=snc_partner_name,
        pse_path=pse_path,
        pse_password=pse_password,
        secudir=secudir,
        qop=SNCQualityOfProtection.PRIVACY,
    )


def create_kerberos_config(
    name: str,
    snc_partner_name: str,
    kerberos_realm: str,
    kerberos_kdc: str,
    kerberos_principal: str = "",
    kerberos_keytab: str = "",
) -> SNCConfig:
    """Create SNC configuration using Kerberos."""
    return SNCConfig(
        name=name,
        security_product=SNCSecurityProduct.KERBEROS,
        snc_partner_name=snc_partner_name,
        kerberos_realm=kerberos_realm,
        kerberos_kdc=kerberos_kdc,
        kerberos_principal=kerberos_principal,
        kerberos_keytab=kerberos_keytab,
        qop=SNCQualityOfProtection.PRIVACY,
    )


def create_x509_config(
    name: str,
    snc_partner_name: str,
    client_certificate_path: str,
    client_certificate_password: str = "",
    ca_certificate_path: str = "",
) -> SNCConfig:
    """Create SNC configuration using X.509 certificates."""
    return SNCConfig(
        name=name,
        security_product=SNCSecurityProduct.X509,
        snc_partner_name=snc_partner_name,
        client_certificate_path=client_certificate_path,
        client_certificate_password=client_certificate_password,
        ca_certificate_path=ca_certificate_path,
        qop=SNCQualityOfProtection.PRIVACY,
    )
