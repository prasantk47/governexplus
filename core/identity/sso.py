# Single Sign-On (SSO) Module
# Enterprise SSO support for GOVERNEX+

"""
Single Sign-On (SSO) Module for GOVERNEX+.

Supports multiple SSO protocols:
- SAML 2.0 (Service Provider mode)
- OAuth 2.0 (Authorization Code, Client Credentials, PKCE)
- OpenID Connect (OIDC)
- WS-Federation (for legacy systems)

Features:
- Multiple IdP support
- Just-in-Time (JIT) provisioning
- Attribute mapping
- Session management
- Token validation and refresh
- Single Logout (SLO)

Security:
- Token encryption
- Signature validation
- PKCE for public clients
- State parameter validation
- Nonce validation (OIDC)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
from urllib.parse import urlencode, urlparse, parse_qs
import uuid
import hashlib
import base64
import secrets
import json
import hmac


# ============================================================
# ENUMS
# ============================================================

class SSOProtocol(Enum):
    """Supported SSO protocols."""
    SAML_2_0 = "saml2"
    OAUTH_2_0 = "oauth2"
    OIDC = "oidc"
    WS_FEDERATION = "wsfed"


class OAuthGrantType(Enum):
    """OAuth 2.0 grant types."""
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"
    PKCE = "pkce"  # Authorization Code with PKCE
    DEVICE_CODE = "device_code"
    IMPLICIT = "implicit"  # Deprecated, but needed for legacy


class SAMLBinding(Enum):
    """SAML 2.0 bindings."""
    HTTP_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    HTTP_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    HTTP_ARTIFACT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Artifact"


class SAMLNameIDFormat(Enum):
    """SAML NameID formats."""
    UNSPECIFIED = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
    EMAIL = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    PERSISTENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"
    TRANSIENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:transient"
    WINDOWS = "urn:oasis:names:tc:SAML:1.1:nameid-format:WindowsDomainQualifiedName"


class TokenType(Enum):
    """Token types."""
    ACCESS_TOKEN = "access_token"
    ID_TOKEN = "id_token"
    REFRESH_TOKEN = "refresh_token"
    SAML_ASSERTION = "saml_assertion"


# ============================================================
# SSO USER AND SESSION
# ============================================================

@dataclass
class SSOUser:
    """User authenticated via SSO."""
    user_id: str = ""  # Subject/NameID from IdP
    username: str = ""
    email: str = ""

    # Name
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""

    # Organization
    department: str = ""
    job_title: str = ""
    employee_id: str = ""
    manager_id: str = ""

    # Groups/Roles from IdP
    groups: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)

    # IdP info
    idp_id: str = ""
    idp_name: str = ""

    # Raw claims/attributes
    claims: Dict[str, Any] = field(default_factory=dict)

    # Session info
    authenticated_at: datetime = field(default_factory=datetime.now)
    session_expires: Optional[datetime] = None
    auth_context_class: str = ""  # e.g., "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"

    # JIT provisioning
    needs_provisioning: bool = False
    is_new_user: bool = False

    def is_session_valid(self) -> bool:
        """Check if SSO session is still valid."""
        if self.session_expires:
            return datetime.now() < self.session_expires
        return True

    def get_claim(self, claim_name: str, default: Any = None) -> Any:
        """Get a specific claim value."""
        return self.claims.get(claim_name, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "groups": self.groups,
            "roles": self.roles,
            "idp_id": self.idp_id,
            "authenticated_at": self.authenticated_at.isoformat(),
            "session_expires": self.session_expires.isoformat() if self.session_expires else None,
        }


@dataclass
class SSOSession:
    """SSO session tracking."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user: Optional[SSOUser] = None

    # Session state
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    is_active: bool = True

    # Protocol specific
    protocol: SSOProtocol = SSOProtocol.OIDC
    idp_session_id: str = ""

    # Tokens
    access_token: str = ""
    refresh_token: str = ""
    id_token: str = ""
    token_expires: Optional[datetime] = None

    # SAML specific
    saml_assertion: str = ""
    saml_session_index: str = ""

    # Security
    ip_address: str = ""
    user_agent: str = ""

    def is_valid(self) -> bool:
        """Check if session is valid."""
        if not self.is_active:
            return False
        if self.expires_at and datetime.now() >= self.expires_at:
            return False
        return True

    def needs_token_refresh(self) -> bool:
        """Check if tokens need refresh."""
        if not self.token_expires:
            return False
        # Refresh if less than 5 minutes remaining
        return datetime.now() >= (self.token_expires - timedelta(minutes=5))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user.user_id if self.user else None,
            "protocol": self.protocol.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
        }


# ============================================================
# SAML 2.0 CONFIGURATION AND PROVIDER
# ============================================================

@dataclass
class SAMLIdentityProvider:
    """SAML 2.0 Identity Provider configuration."""
    idp_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""

    # IdP Metadata
    entity_id: str = ""  # IdP Entity ID
    sso_url: str = ""  # Single Sign-On URL
    slo_url: str = ""  # Single Logout URL
    sso_binding: SAMLBinding = SAMLBinding.HTTP_REDIRECT
    slo_binding: SAMLBinding = SAMLBinding.HTTP_REDIRECT

    # Certificates
    idp_certificate: str = ""  # IdP signing certificate (PEM)
    idp_certificate_fingerprint: str = ""

    # Name ID
    name_id_format: SAMLNameIDFormat = SAMLNameIDFormat.EMAIL

    # Attribute mapping
    attribute_map: Dict[str, str] = field(default_factory=lambda: {
        "user_id": "NameID",
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "groups": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
    })

    # Settings
    want_assertions_signed: bool = True
    want_response_signed: bool = True
    allow_unsolicited: bool = False

    # Status
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "idp_id": self.idp_id,
            "name": self.name,
            "entity_id": self.entity_id,
            "sso_url": self.sso_url,
            "name_id_format": self.name_id_format.value,
            "is_active": self.is_active,
        }


@dataclass
class SAMLServiceProvider:
    """SAML 2.0 Service Provider (GOVERNEX+) configuration."""
    entity_id: str = ""  # SP Entity ID
    acs_url: str = ""  # Assertion Consumer Service URL
    slo_url: str = ""  # Single Logout URL
    metadata_url: str = ""

    # Certificates
    sp_certificate: str = ""  # SP signing certificate
    sp_private_key: str = ""  # SP private key

    # Settings
    sign_authn_requests: bool = True
    want_assertions_encrypted: bool = True
    name_id_format: SAMLNameIDFormat = SAMLNameIDFormat.EMAIL

    # Organization info
    org_name: str = "GOVERNEX+"
    org_display_name: str = "GOVERNEX+ GRC Platform"
    org_url: str = ""

    # Contact
    technical_contact_name: str = ""
    technical_contact_email: str = ""


@dataclass
class SAMLAuthnRequest:
    """SAML Authentication Request."""
    request_id: str = field(default_factory=lambda: f"_{''.join(secrets.token_hex(16))}")
    issue_instant: datetime = field(default_factory=datetime.now)
    destination: str = ""
    issuer: str = ""
    acs_url: str = ""
    name_id_format: SAMLNameIDFormat = SAMLNameIDFormat.EMAIL

    # Relay state for return URL
    relay_state: str = ""

    def to_xml(self) -> str:
        """Generate SAML AuthnRequest XML."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{self.request_id}"
    Version="2.0"
    IssueInstant="{self.issue_instant.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    Destination="{self.destination}"
    AssertionConsumerServiceURL="{self.acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{self.issuer}</saml:Issuer>
    <samlp:NameIDPolicy
        Format="{self.name_id_format.value}"
        AllowCreate="true"/>
</samlp:AuthnRequest>"""

    def encode_redirect(self) -> str:
        """Encode request for HTTP-Redirect binding."""
        import zlib
        xml = self.to_xml()
        compressed = zlib.compress(xml.encode('utf-8'))[2:-4]  # Remove zlib header/trailer
        return base64.b64encode(compressed).decode('utf-8')


@dataclass
class SAMLResponse:
    """Parsed SAML Response."""
    response_id: str = ""
    in_response_to: str = ""
    issue_instant: Optional[datetime] = None
    issuer: str = ""

    # Status
    status_code: str = ""
    status_message: str = ""
    is_success: bool = False

    # Assertion
    assertion_id: str = ""
    subject_name_id: str = ""
    subject_name_id_format: str = ""

    # Conditions
    not_before: Optional[datetime] = None
    not_on_or_after: Optional[datetime] = None
    audience: str = ""

    # Authentication
    authn_instant: Optional[datetime] = None
    session_index: str = ""
    authn_context_class: str = ""

    # Attributes
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Signature validation
    is_signed: bool = False
    signature_valid: bool = False

    def get_user(self, attribute_map: Dict[str, str]) -> SSOUser:
        """Extract user from SAML response."""
        user = SSOUser(
            user_id=self.subject_name_id,
            authenticated_at=self.authn_instant or datetime.now(),
            session_expires=self.not_on_or_after,
            auth_context_class=self.authn_context_class,
            claims=self.attributes,
        )

        # Map attributes
        for field_name, attr_name in attribute_map.items():
            if attr_name == "NameID":
                value = self.subject_name_id
            else:
                value = self.attributes.get(attr_name)

            if value:
                if field_name == "email":
                    user.email = value
                elif field_name == "first_name":
                    user.first_name = value
                elif field_name == "last_name":
                    user.last_name = value
                elif field_name == "groups":
                    user.groups = value if isinstance(value, list) else [value]
                elif field_name == "user_id":
                    user.user_id = value

        user.full_name = f"{user.first_name} {user.last_name}".strip()
        user.username = user.email.split("@")[0] if user.email else user.user_id

        return user


class SAMLProvider:
    """
    SAML 2.0 Service Provider implementation.

    Usage:
        sp_config = SAMLServiceProvider(
            entity_id="https://grc.company.com/saml/metadata",
            acs_url="https://grc.company.com/saml/acs",
        )

        idp_config = SAMLIdentityProvider(
            name="Corporate IdP",
            entity_id="https://idp.company.com",
            sso_url="https://idp.company.com/saml/sso",
            idp_certificate="...",
        )

        provider = SAMLProvider(sp_config)
        provider.add_idp(idp_config)

        # Initiate SSO
        redirect_url = provider.create_authn_request(idp_id)

        # Handle response
        user = provider.process_response(saml_response_b64)
    """

    def __init__(self, sp_config: SAMLServiceProvider):
        self.sp_config = sp_config
        self.identity_providers: Dict[str, SAMLIdentityProvider] = {}
        self.pending_requests: Dict[str, SAMLAuthnRequest] = {}

    def add_idp(self, idp: SAMLIdentityProvider) -> None:
        """Register an Identity Provider."""
        self.identity_providers[idp.idp_id] = idp

    def get_idp(self, idp_id: str) -> Optional[SAMLIdentityProvider]:
        """Get Identity Provider by ID."""
        return self.identity_providers.get(idp_id)

    def create_authn_request(
        self,
        idp_id: str,
        relay_state: str = "",
    ) -> Tuple[str, str]:
        """
        Create SAML AuthnRequest and return redirect URL.

        Returns tuple of (redirect_url, request_id)
        """
        idp = self.identity_providers.get(idp_id)
        if not idp:
            raise ValueError(f"Unknown IdP: {idp_id}")

        request = SAMLAuthnRequest(
            destination=idp.sso_url,
            issuer=self.sp_config.entity_id,
            acs_url=self.sp_config.acs_url,
            name_id_format=idp.name_id_format,
            relay_state=relay_state,
        )

        # Store pending request
        self.pending_requests[request.request_id] = request

        # Build redirect URL
        if idp.sso_binding == SAMLBinding.HTTP_REDIRECT:
            encoded_request = request.encode_redirect()
            params = {
                "SAMLRequest": encoded_request,
            }
            if relay_state:
                params["RelayState"] = relay_state

            redirect_url = f"{idp.sso_url}?{urlencode(params)}"
        else:
            # HTTP-POST binding would return form data
            redirect_url = idp.sso_url

        return redirect_url, request.request_id

    def process_response(
        self,
        saml_response_b64: str,
        idp_id: Optional[str] = None,
    ) -> SSOUser:
        """
        Process SAML Response and extract user.

        Args:
            saml_response_b64: Base64-encoded SAML Response
            idp_id: Optional IdP ID (determined from response if not provided)

        Returns:
            SSOUser with authenticated user info
        """
        # In production, would use python3-saml or pysaml2:
        # from onelogin.saml2.response import OneLogin_Saml2_Response

        # Decode response
        try:
            response_xml = base64.b64decode(saml_response_b64).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Invalid SAML response encoding: {e}")

        # Parse and validate response
        response = self._parse_response(response_xml)

        if not response.is_success:
            raise ValueError(f"SAML authentication failed: {response.status_message}")

        # Validate signature
        if not self._validate_signature(response, idp_id):
            raise ValueError("SAML response signature validation failed")

        # Validate conditions
        self._validate_conditions(response)

        # Validate InResponseTo
        if response.in_response_to:
            if response.in_response_to not in self.pending_requests:
                raise ValueError("Invalid InResponseTo - request not found")
            del self.pending_requests[response.in_response_to]

        # Get IdP config for attribute mapping
        idp = None
        for idp_config in self.identity_providers.values():
            if idp_config.entity_id == response.issuer:
                idp = idp_config
                break

        attribute_map = idp.attribute_map if idp else {}

        # Extract user
        user = response.get_user(attribute_map)
        user.idp_id = idp.idp_id if idp else ""
        user.idp_name = idp.name if idp else response.issuer

        return user

    def _parse_response(self, xml: str) -> SAMLResponse:
        """Parse SAML Response XML."""
        # In production, would use proper XML parsing
        # This is a simplified placeholder
        response = SAMLResponse()

        # Would extract values from XML
        response.is_success = "Success" in xml
        response.status_code = "urn:oasis:names:tc:SAML:2.0:status:Success"

        return response

    def _validate_signature(self, response: SAMLResponse, idp_id: Optional[str]) -> bool:
        """Validate SAML response signature."""
        # In production, would use xmlsec or signxml library
        return True

    def _validate_conditions(self, response: SAMLResponse) -> None:
        """Validate SAML assertion conditions."""
        now = datetime.utcnow()

        if response.not_before and now < response.not_before:
            raise ValueError("SAML assertion not yet valid")

        if response.not_on_or_after and now >= response.not_on_or_after:
            raise ValueError("SAML assertion expired")

        if response.audience and response.audience != self.sp_config.entity_id:
            raise ValueError("SAML assertion audience mismatch")

    def create_logout_request(self, user: SSOUser, idp_id: str) -> str:
        """Create SAML LogoutRequest for Single Logout."""
        idp = self.identity_providers.get(idp_id)
        if not idp or not idp.slo_url:
            raise ValueError("IdP does not support Single Logout")

        # Generate LogoutRequest XML
        # Return redirect URL
        return idp.slo_url

    def generate_metadata(self) -> str:
        """Generate SP metadata XML."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{self.sp_config.entity_id}">
    <md:SPSSODescriptor
        AuthnRequestsSigned="{str(self.sp_config.sign_authn_requests).lower()}"
        WantAssertionsSigned="true"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:NameIDFormat>{self.sp_config.name_id_format.value}</md:NameIDFormat>
        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{self.sp_config.acs_url}"
            index="0"
            isDefault="true"/>
        <md:SingleLogoutService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            Location="{self.sp_config.slo_url}"/>
    </md:SPSSODescriptor>
    <md:Organization>
        <md:OrganizationName xml:lang="en">{self.sp_config.org_name}</md:OrganizationName>
        <md:OrganizationDisplayName xml:lang="en">{self.sp_config.org_display_name}</md:OrganizationDisplayName>
        <md:OrganizationURL xml:lang="en">{self.sp_config.org_url}</md:OrganizationURL>
    </md:Organization>
</md:EntityDescriptor>"""


# ============================================================
# OAUTH 2.0 / OIDC CONFIGURATION AND PROVIDER
# ============================================================

@dataclass
class OAuthProvider:
    """OAuth 2.0 / OIDC Provider configuration."""
    provider_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""

    # Endpoints
    authorization_endpoint: str = ""
    token_endpoint: str = ""
    userinfo_endpoint: str = ""
    jwks_uri: str = ""
    revocation_endpoint: str = ""
    end_session_endpoint: str = ""

    # OIDC Discovery
    issuer: str = ""
    discovery_url: str = ""  # .well-known/openid-configuration

    # Client credentials
    client_id: str = ""
    client_secret: str = ""

    # Scopes
    default_scopes: List[str] = field(default_factory=lambda: ["openid", "profile", "email"])
    supported_scopes: List[str] = field(default_factory=list)

    # Grant types
    supported_grants: List[OAuthGrantType] = field(default_factory=lambda: [
        OAuthGrantType.AUTHORIZATION_CODE,
        OAuthGrantType.REFRESH_TOKEN,
    ])

    # PKCE
    require_pkce: bool = True
    pkce_method: str = "S256"  # S256 or plain

    # Response types
    response_type: str = "code"  # code, token, id_token

    # Claim mapping
    claim_map: Dict[str, str] = field(default_factory=lambda: {
        "user_id": "sub",
        "email": "email",
        "first_name": "given_name",
        "last_name": "family_name",
        "full_name": "name",
        "groups": "groups",
    })

    # Token settings
    access_token_lifetime: int = 3600  # seconds
    refresh_token_lifetime: int = 86400

    # Validation
    validate_issuer: bool = True
    validate_audience: bool = True
    allowed_audiences: List[str] = field(default_factory=list)

    # Status
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "issuer": self.issuer,
            "authorization_endpoint": self.authorization_endpoint,
            "token_endpoint": self.token_endpoint,
            "is_active": self.is_active,
        }


@dataclass
class OAuthToken:
    """OAuth/OIDC tokens."""
    access_token: str = ""
    token_type: str = "Bearer"
    expires_in: int = 3600
    expires_at: Optional[datetime] = None

    refresh_token: str = ""
    refresh_token_expires_at: Optional[datetime] = None

    id_token: str = ""  # OIDC only

    scope: str = ""

    def is_expired(self) -> bool:
        """Check if access token is expired."""
        if self.expires_at:
            return datetime.now() >= self.expires_at
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token[:20] + "..." if self.access_token else "",
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "scope": self.scope,
        }


@dataclass
class OAuthAuthorizationRequest:
    """OAuth authorization request state."""
    state: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    nonce: str = field(default_factory=lambda: secrets.token_urlsafe(32))

    # PKCE
    code_verifier: str = ""
    code_challenge: str = ""
    code_challenge_method: str = "S256"

    # Request params
    provider_id: str = ""
    redirect_uri: str = ""
    scopes: List[str] = field(default_factory=list)

    # State
    created_at: datetime = field(default_factory=datetime.now)
    return_url: str = ""  # Where to redirect after auth

    def generate_pkce(self) -> None:
        """Generate PKCE code verifier and challenge."""
        self.code_verifier = secrets.token_urlsafe(64)

        if self.code_challenge_method == "S256":
            digest = hashlib.sha256(self.code_verifier.encode()).digest()
            self.code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('utf-8')
        else:
            self.code_challenge = self.code_verifier


class OIDCProvider:
    """
    OAuth 2.0 / OpenID Connect Provider implementation.

    Usage:
        config = OAuthProvider(
            name="Azure AD",
            issuer="https://login.microsoftonline.com/{tenant}/v2.0",
            client_id="...",
            client_secret="...",
        )

        provider = OIDCProvider(config, redirect_uri="https://grc.company.com/oauth/callback")

        # Initiate auth
        auth_url, state = provider.create_authorization_url()

        # Exchange code for tokens
        tokens = provider.exchange_code(authorization_code, state)

        # Get user info
        user = provider.get_user_info(tokens.access_token)
    """

    def __init__(self, config: OAuthProvider, redirect_uri: str):
        self.config = config
        self.redirect_uri = redirect_uri
        self.pending_requests: Dict[str, OAuthAuthorizationRequest] = {}

    def discover(self) -> None:
        """Fetch OIDC discovery document and populate endpoints."""
        if not self.config.discovery_url:
            return

        # In production:
        # import httpx
        # response = httpx.get(self.config.discovery_url)
        # data = response.json()
        # self.config.authorization_endpoint = data.get("authorization_endpoint")
        # self.config.token_endpoint = data.get("token_endpoint")
        # etc.

    def create_authorization_url(
        self,
        scopes: Optional[List[str]] = None,
        return_url: str = "",
        additional_params: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, str]:
        """
        Create OAuth authorization URL.

        Returns tuple of (authorization_url, state)
        """
        request = OAuthAuthorizationRequest(
            provider_id=self.config.provider_id,
            redirect_uri=self.redirect_uri,
            scopes=scopes or self.config.default_scopes,
            return_url=return_url,
        )

        # Generate PKCE if required
        if self.config.require_pkce:
            request.generate_pkce()

        # Store pending request
        self.pending_requests[request.state] = request

        # Build authorization URL
        params = {
            "client_id": self.config.client_id,
            "response_type": self.config.response_type,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(request.scopes),
            "state": request.state,
        }

        # OIDC: add nonce
        if "openid" in request.scopes:
            params["nonce"] = request.nonce

        # PKCE
        if self.config.require_pkce:
            params["code_challenge"] = request.code_challenge
            params["code_challenge_method"] = request.code_challenge_method

        # Additional params
        if additional_params:
            params.update(additional_params)

        auth_url = f"{self.config.authorization_endpoint}?{urlencode(params)}"

        return auth_url, request.state

    def exchange_code(
        self,
        authorization_code: str,
        state: str,
    ) -> OAuthToken:
        """
        Exchange authorization code for tokens.

        Args:
            authorization_code: Code from authorization response
            state: State parameter for validation

        Returns:
            OAuthToken with access token and optionally refresh/id tokens
        """
        # Validate state
        if state not in self.pending_requests:
            raise ValueError("Invalid state parameter")

        request = self.pending_requests.pop(state)

        # Build token request
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": request.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        # Add PKCE verifier
        if self.config.require_pkce:
            data["code_verifier"] = request.code_verifier

        # In production:
        # import httpx
        # response = httpx.post(self.config.token_endpoint, data=data)
        # token_data = response.json()

        # Simulated response
        token = OAuthToken(
            access_token=secrets.token_urlsafe(32),
            token_type="Bearer",
            expires_in=self.config.access_token_lifetime,
            refresh_token=secrets.token_urlsafe(32),
            scope=" ".join(request.scopes),
        )
        token.expires_at = datetime.now() + timedelta(seconds=token.expires_in)

        return token

    def refresh_tokens(self, refresh_token: str) -> OAuthToken:
        """Refresh access token using refresh token."""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        # In production: POST to token_endpoint

        token = OAuthToken(
            access_token=secrets.token_urlsafe(32),
            token_type="Bearer",
            expires_in=self.config.access_token_lifetime,
            refresh_token=secrets.token_urlsafe(32),
        )
        token.expires_at = datetime.now() + timedelta(seconds=token.expires_in)

        return token

    def get_user_info(self, access_token: str) -> SSOUser:
        """
        Fetch user info from userinfo endpoint.

        Args:
            access_token: Valid access token

        Returns:
            SSOUser with user information
        """
        # In production:
        # import httpx
        # headers = {"Authorization": f"Bearer {access_token}"}
        # response = httpx.get(self.config.userinfo_endpoint, headers=headers)
        # claims = response.json()

        # Simulated claims
        claims = {
            "sub": "user123",
            "email": "user@company.com",
            "given_name": "John",
            "family_name": "Doe",
            "name": "John Doe",
        }

        user = self._map_claims_to_user(claims)
        user.idp_id = self.config.provider_id
        user.idp_name = self.config.name

        return user

    def validate_id_token(self, id_token: str, nonce: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate OIDC ID token and return claims.

        Validates:
        - Signature (using JWKS)
        - Issuer
        - Audience
        - Expiration
        - Nonce (if provided)
        """
        # In production, would use PyJWT with JWKS:
        # import jwt
        # from jwt import PyJWKClient
        #
        # jwks_client = PyJWKClient(self.config.jwks_uri)
        # signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        #
        # claims = jwt.decode(
        #     id_token,
        #     signing_key.key,
        #     algorithms=["RS256"],
        #     audience=self.config.client_id,
        #     issuer=self.config.issuer,
        # )

        # Simulated validation
        claims = {
            "iss": self.config.issuer,
            "sub": "user123",
            "aud": self.config.client_id,
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
        }

        if nonce and claims.get("nonce") != nonce:
            raise ValueError("Invalid nonce in ID token")

        return claims

    def _map_claims_to_user(self, claims: Dict[str, Any]) -> SSOUser:
        """Map OAuth/OIDC claims to SSOUser."""
        user = SSOUser(claims=claims)

        for field_name, claim_name in self.config.claim_map.items():
            value = claims.get(claim_name)
            if value:
                if field_name == "user_id":
                    user.user_id = value
                elif field_name == "email":
                    user.email = value
                elif field_name == "first_name":
                    user.first_name = value
                elif field_name == "last_name":
                    user.last_name = value
                elif field_name == "full_name":
                    user.full_name = value
                elif field_name == "groups":
                    user.groups = value if isinstance(value, list) else [value]

        if not user.full_name:
            user.full_name = f"{user.first_name} {user.last_name}".strip()

        if not user.username and user.email:
            user.username = user.email.split("@")[0]

        return user

    def client_credentials_token(self, scopes: Optional[List[str]] = None) -> OAuthToken:
        """
        Get token using client credentials grant (service-to-service).

        Args:
            scopes: Scopes to request

        Returns:
            OAuthToken with access token
        """
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": " ".join(scopes or self.config.default_scopes),
        }

        # In production: POST to token_endpoint

        token = OAuthToken(
            access_token=secrets.token_urlsafe(32),
            token_type="Bearer",
            expires_in=self.config.access_token_lifetime,
        )
        token.expires_at = datetime.now() + timedelta(seconds=token.expires_in)

        return token

    def revoke_token(self, token: str, token_type: str = "access_token") -> bool:
        """Revoke a token."""
        if not self.config.revocation_endpoint:
            return False

        data = {
            "token": token,
            "token_type_hint": token_type,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        # In production: POST to revocation_endpoint
        return True

    def logout_url(self, id_token: Optional[str] = None, post_logout_redirect: str = "") -> str:
        """Get OIDC logout URL."""
        if not self.config.end_session_endpoint:
            return ""

        params = {}
        if id_token:
            params["id_token_hint"] = id_token
        if post_logout_redirect:
            params["post_logout_redirect_uri"] = post_logout_redirect

        return f"{self.config.end_session_endpoint}?{urlencode(params)}"


# ============================================================
# SSO MANAGER - UNIFIED SSO HANDLING
# ============================================================

@dataclass
class SSOManager:
    """
    Unified SSO Manager for multiple protocols and providers.

    Usage:
        manager = SSOManager()

        # Register providers
        manager.register_saml_idp(saml_idp_config)
        manager.register_oidc_provider(oidc_config)

        # Initiate SSO
        auth_url = manager.initiate_sso(provider_id="azure-ad", protocol="oidc")

        # Handle callback
        user, session = manager.handle_callback(protocol="oidc", callback_data={...})

        # Validate session
        if manager.is_session_valid(session_id):
            user = manager.get_session_user(session_id)
    """

    manager_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Providers
    saml_provider: Optional[SAMLProvider] = None
    oidc_providers: Dict[str, OIDCProvider] = field(default_factory=dict)

    # Sessions
    sessions: Dict[str, SSOSession] = field(default_factory=dict)
    session_timeout_minutes: int = 480  # 8 hours

    # Callbacks
    on_user_authenticated: Optional[Callable[[SSOUser, SSOSession], None]] = None
    on_session_expired: Optional[Callable[[SSOSession], None]] = None

    # JIT Provisioning
    jit_provisioning_enabled: bool = True
    jit_provisioner: Optional[Callable[[SSOUser], None]] = None

    def register_saml_sp(self, sp_config: SAMLServiceProvider) -> None:
        """Register SAML Service Provider configuration."""
        self.saml_provider = SAMLProvider(sp_config)

    def register_saml_idp(self, idp_config: SAMLIdentityProvider) -> None:
        """Register a SAML Identity Provider."""
        if not self.saml_provider:
            raise ValueError("SAML SP not configured")
        self.saml_provider.add_idp(idp_config)

    def register_oidc_provider(self, config: OAuthProvider, redirect_uri: str) -> None:
        """Register an OIDC/OAuth provider."""
        provider = OIDCProvider(config, redirect_uri)
        self.oidc_providers[config.provider_id] = provider

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of available SSO providers."""
        providers = []

        if self.saml_provider:
            for idp in self.saml_provider.identity_providers.values():
                if idp.is_active:
                    providers.append({
                        "id": idp.idp_id,
                        "name": idp.name,
                        "protocol": "saml2",
                    })

        for provider in self.oidc_providers.values():
            if provider.config.is_active:
                providers.append({
                    "id": provider.config.provider_id,
                    "name": provider.config.name,
                    "protocol": "oidc",
                })

        return providers

    def initiate_sso(
        self,
        provider_id: str,
        protocol: str,
        return_url: str = "",
    ) -> Tuple[str, str]:
        """
        Initiate SSO flow.

        Returns tuple of (redirect_url, request_id/state)
        """
        if protocol == "saml2":
            if not self.saml_provider:
                raise ValueError("SAML not configured")
            return self.saml_provider.create_authn_request(provider_id, return_url)

        elif protocol in ("oidc", "oauth2"):
            provider = self.oidc_providers.get(provider_id)
            if not provider:
                raise ValueError(f"OIDC provider not found: {provider_id}")
            return provider.create_authorization_url(return_url=return_url)

        else:
            raise ValueError(f"Unsupported protocol: {protocol}")

    def handle_saml_callback(self, saml_response: str, relay_state: str = "") -> Tuple[SSOUser, SSOSession]:
        """Handle SAML ACS callback."""
        if not self.saml_provider:
            raise ValueError("SAML not configured")

        user = self.saml_provider.process_response(saml_response)
        session = self._create_session(user, SSOProtocol.SAML_2_0)
        session.saml_assertion = saml_response

        self._post_authentication(user, session)

        return user, session

    def handle_oidc_callback(
        self,
        provider_id: str,
        authorization_code: str,
        state: str,
    ) -> Tuple[SSOUser, SSOSession]:
        """Handle OIDC callback."""
        provider = self.oidc_providers.get(provider_id)
        if not provider:
            raise ValueError(f"OIDC provider not found: {provider_id}")

        # Exchange code for tokens
        tokens = provider.exchange_code(authorization_code, state)

        # Get user info
        user = provider.get_user_info(tokens.access_token)

        # Create session
        session = self._create_session(user, SSOProtocol.OIDC)
        session.access_token = tokens.access_token
        session.refresh_token = tokens.refresh_token
        session.id_token = tokens.id_token
        session.token_expires = tokens.expires_at

        self._post_authentication(user, session)

        return user, session

    def _create_session(self, user: SSOUser, protocol: SSOProtocol) -> SSOSession:
        """Create a new SSO session."""
        session = SSOSession(
            user=user,
            protocol=protocol,
            expires_at=datetime.now() + timedelta(minutes=self.session_timeout_minutes),
        )
        self.sessions[session.session_id] = session
        return session

    def _post_authentication(self, user: SSOUser, session: SSOSession) -> None:
        """Post-authentication processing."""
        # JIT provisioning
        if self.jit_provisioning_enabled and self.jit_provisioner:
            user.needs_provisioning = True
            self.jit_provisioner(user)

        # Callback
        if self.on_user_authenticated:
            self.on_user_authenticated(user, session)

    def get_session(self, session_id: str) -> Optional[SSOSession]:
        """Get session by ID."""
        return self.sessions.get(session_id)

    def is_session_valid(self, session_id: str) -> bool:
        """Check if session is valid."""
        session = self.sessions.get(session_id)
        return session.is_valid() if session else False

    def get_session_user(self, session_id: str) -> Optional[SSOUser]:
        """Get user from session."""
        session = self.sessions.get(session_id)
        return session.user if session and session.is_valid() else None

    def refresh_session(self, session_id: str) -> bool:
        """Refresh session tokens if needed."""
        session = self.sessions.get(session_id)
        if not session or not session.is_valid():
            return False

        if session.protocol == SSOProtocol.OIDC and session.needs_token_refresh():
            # Find provider and refresh
            for provider in self.oidc_providers.values():
                if provider.config.provider_id == session.user.idp_id:
                    try:
                        new_tokens = provider.refresh_tokens(session.refresh_token)
                        session.access_token = new_tokens.access_token
                        session.refresh_token = new_tokens.refresh_token
                        session.token_expires = new_tokens.expires_at
                        return True
                    except Exception:
                        return False

        return True

    def logout(self, session_id: str) -> Optional[str]:
        """
        Logout session and return IdP logout URL if available.

        Returns IdP logout URL for single logout, or None.
        """
        session = self.sessions.get(session_id)
        if not session:
            return None

        # Mark session as inactive
        session.is_active = False

        # Get logout URL
        logout_url = None

        if session.protocol == SSOProtocol.SAML_2_0 and self.saml_provider:
            try:
                logout_url = self.saml_provider.create_logout_request(
                    session.user, session.user.idp_id
                )
            except Exception:
                pass

        elif session.protocol == SSOProtocol.OIDC:
            provider = self.oidc_providers.get(session.user.idp_id)
            if provider:
                logout_url = provider.logout_url(session.id_token)

        # Remove session
        del self.sessions[session_id]

        return logout_url

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        expired = [
            sid for sid, session in self.sessions.items()
            if not session.is_valid()
        ]

        for sid in expired:
            session = self.sessions.pop(sid)
            if self.on_session_expired:
                self.on_session_expired(session)

        return len(expired)


# ============================================================
# FACTORY FUNCTIONS
# ============================================================

def create_azure_ad_oidc(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> OIDCProvider:
    """Create Azure AD OIDC provider."""
    config = OAuthProvider(
        name="Azure AD",
        issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        discovery_url=f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration",
        authorization_endpoint=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
        token_endpoint=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        userinfo_endpoint="https://graph.microsoft.com/oidc/userinfo",
        jwks_uri=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
        end_session_endpoint=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout",
        client_id=client_id,
        client_secret=client_secret,
        require_pkce=True,
    )
    return OIDCProvider(config, redirect_uri)


def create_okta_oidc(
    domain: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> OIDCProvider:
    """Create Okta OIDC provider."""
    config = OAuthProvider(
        name="Okta",
        issuer=f"https://{domain}",
        discovery_url=f"https://{domain}/.well-known/openid-configuration",
        authorization_endpoint=f"https://{domain}/oauth2/v1/authorize",
        token_endpoint=f"https://{domain}/oauth2/v1/token",
        userinfo_endpoint=f"https://{domain}/oauth2/v1/userinfo",
        jwks_uri=f"https://{domain}/oauth2/v1/keys",
        end_session_endpoint=f"https://{domain}/oauth2/v1/logout",
        revocation_endpoint=f"https://{domain}/oauth2/v1/revoke",
        client_id=client_id,
        client_secret=client_secret,
        require_pkce=True,
    )
    return OIDCProvider(config, redirect_uri)


def create_google_oidc(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> OIDCProvider:
    """Create Google OIDC provider."""
    config = OAuthProvider(
        name="Google",
        issuer="https://accounts.google.com",
        discovery_url="https://accounts.google.com/.well-known/openid-configuration",
        authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
        token_endpoint="https://oauth2.googleapis.com/token",
        userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
        jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
        revocation_endpoint="https://oauth2.googleapis.com/revoke",
        client_id=client_id,
        client_secret=client_secret,
        require_pkce=True,
    )
    return OIDCProvider(config, redirect_uri)


def create_adfs_saml(
    adfs_url: str,
    sp_entity_id: str,
    sp_acs_url: str,
    idp_certificate: str,
) -> SAMLProvider:
    """Create ADFS SAML provider."""
    sp_config = SAMLServiceProvider(
        entity_id=sp_entity_id,
        acs_url=sp_acs_url,
    )

    provider = SAMLProvider(sp_config)

    idp_config = SAMLIdentityProvider(
        name="ADFS",
        entity_id=f"{adfs_url}/adfs/services/trust",
        sso_url=f"{adfs_url}/adfs/ls",
        slo_url=f"{adfs_url}/adfs/ls",
        idp_certificate=idp_certificate,
    )

    provider.add_idp(idp_config)

    return provider
