# Identity & User Profile Module
# Enterprise identity management for GOVERNEX+

"""
Identity Module for GOVERNEX+.

Provides comprehensive identity management:
- User profile aggregation
- Identity risk assessment
- LDAP/Active Directory integration
- SSO (SAML 2.0, OAuth 2.0, OIDC)
- SAP SNC (Secure Network Communications)
- Unified identity provider abstraction
"""

from .user_profile import (
    UserProfileService, UnifiedUserProfile, UserSource,
    ManagerInfo, OrganizationInfo, RiskProfile, AccessSummary
)
from .identity_risk import (
    IdentityRiskEngine, IdentityProfile, IdentityStatus,
    IdentityRiskLevel, IdentityAnomaly, SystemAccess,
    IdentityHygieneIssue
)

# LDAP/Active Directory
from .ldap_connector import (
    LDAPConnector, LDAPConfig, LDAPUser, LDAPGroup,
    LDAPServerType, LDAPAuthType, LDAPConnectionSecurity,
    LDAPOrganizationalUnit, LDAPPasswordPolicy, LDAPSyncResult,
    create_ad_connector, create_openldap_connector, create_azure_ad_ds_connector,
)

# SSO (SAML, OAuth, OIDC)
from .sso import (
    # SAML
    SAMLProvider, SAMLServiceProvider, SAMLIdentityProvider,
    SAMLAuthnRequest, SAMLResponse, SAMLBinding, SAMLNameIDFormat,
    # OAuth/OIDC
    OIDCProvider, OAuthProvider, OAuthToken, OAuthGrantType,
    OAuthAuthorizationRequest,
    # Session
    SSOUser, SSOSession, SSOManager, SSOProtocol,
    # Factory functions
    create_azure_ad_oidc, create_okta_oidc, create_google_oidc,
    create_adfs_saml,
)

# SNC (Secure Network Communications)
from .snc import (
    SNCConnector, SNCConfig, SNCManager,
    SNCSecurityProduct, SNCQualityOfProtection, SNCConnectionState,
    SNCCertificate, PSEFile, CertificateManager,
    SNCConnectionInfo, CertificateType,
    create_sap_cryptolib_config, create_kerberos_config, create_x509_config,
)

# Unified Identity Providers
from .providers import (
    IdentityProviderManager, UnifiedIdentity, IdentitySource,
    IdentitySourceType, IdentitySyncStatus, IdentityEventType,
    IdentitySourceConfig, IdentityEvent, IdentityCorrelator,
    AttributeMapping, CorrelationRule, ConflictResolutionStrategy,
    create_identity_manager, create_hr_authoritative_manager,
    # Standard mappings
    LDAP_ATTRIBUTE_MAPPING, AZURE_AD_ATTRIBUTE_MAPPING,
    OKTA_ATTRIBUTE_MAPPING, HR_ATTRIBUTE_MAPPING,
)

__all__ = [
    # User Profile
    "UserProfileService",
    "UnifiedUserProfile",
    "UserSource",
    "ManagerInfo",
    "OrganizationInfo",
    "RiskProfile",
    "AccessSummary",
    # Identity Risk
    "IdentityRiskEngine",
    "IdentityProfile",
    "IdentityStatus",
    "IdentityRiskLevel",
    "IdentityAnomaly",
    "SystemAccess",
    "IdentityHygieneIssue",
    # LDAP
    "LDAPConnector",
    "LDAPConfig",
    "LDAPUser",
    "LDAPGroup",
    "LDAPServerType",
    "LDAPAuthType",
    "LDAPConnectionSecurity",
    "LDAPOrganizationalUnit",
    "LDAPPasswordPolicy",
    "LDAPSyncResult",
    "create_ad_connector",
    "create_openldap_connector",
    "create_azure_ad_ds_connector",
    # SAML
    "SAMLProvider",
    "SAMLServiceProvider",
    "SAMLIdentityProvider",
    "SAMLAuthnRequest",
    "SAMLResponse",
    "SAMLBinding",
    "SAMLNameIDFormat",
    # OAuth/OIDC
    "OIDCProvider",
    "OAuthProvider",
    "OAuthToken",
    "OAuthGrantType",
    "OAuthAuthorizationRequest",
    # SSO Session
    "SSOUser",
    "SSOSession",
    "SSOManager",
    "SSOProtocol",
    # SSO Factory
    "create_azure_ad_oidc",
    "create_okta_oidc",
    "create_google_oidc",
    "create_adfs_saml",
    # SNC
    "SNCConnector",
    "SNCConfig",
    "SNCManager",
    "SNCSecurityProduct",
    "SNCQualityOfProtection",
    "SNCConnectionState",
    "SNCCertificate",
    "PSEFile",
    "CertificateManager",
    "SNCConnectionInfo",
    "CertificateType",
    "create_sap_cryptolib_config",
    "create_kerberos_config",
    "create_x509_config",
    # Unified Identity Providers
    "IdentityProviderManager",
    "UnifiedIdentity",
    "IdentitySource",
    "IdentitySourceType",
    "IdentitySyncStatus",
    "IdentityEventType",
    "IdentitySourceConfig",
    "IdentityEvent",
    "IdentityCorrelator",
    "AttributeMapping",
    "CorrelationRule",
    "ConflictResolutionStrategy",
    "create_identity_manager",
    "create_hr_authoritative_manager",
    # Standard mappings
    "LDAP_ATTRIBUTE_MAPPING",
    "AZURE_AD_ATTRIBUTE_MAPPING",
    "OKTA_ATTRIBUTE_MAPPING",
    "HR_ATTRIBUTE_MAPPING",
]
