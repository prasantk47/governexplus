"""
SSO Router — SAML 2.0 Service Provider + OAuth2/OIDC endpoints.

Supports:
  - SAML 2.0 SP (python3-saml / xmlsec)
  - OAuth 2.0 Authorization Code + PKCE (authlib)
  - OpenID Connect (authlib)

Env vars — SAML:
  SAML_SP_ENTITY_ID          — e.g. https://governexplus.com/saml/metadata
  SAML_SP_ACS_URL            — e.g. https://governexplus.com/auth/sso/saml/acs
  SAML_SP_SLS_URL            — e.g. https://governexplus.com/auth/sso/saml/sls
  SAML_SP_CERT_FILE          — path to SP certificate PEM
  SAML_SP_KEY_FILE           — path to SP private key PEM
  SAML_IDP_ENTITY_ID         — IdP entity ID
  SAML_IDP_SSO_URL           — IdP SSO redirect URL
  SAML_IDP_SLO_URL           — IdP SLO redirect URL
  SAML_IDP_CERT_FILE         — path to IdP certificate PEM

Env vars — OAuth2/OIDC:
  OIDC_CLIENT_ID             — OAuth2 client ID
  OIDC_CLIENT_SECRET         — OAuth2 client secret
  OIDC_DISCOVERY_URL         — OIDC well-known URL (e.g. https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration)
  OIDC_REDIRECT_URI          — Callback URL (e.g. https://governexplus.com/auth/sso/oidc/callback)
  OIDC_SCOPES                — Comma-separated scopes (default: openid,profile,email)

Frontend redirect:
  FRONTEND_URL               — Where to redirect after SSO (default: http://localhost:4500)
"""

import os
import json
import logging
from typing import Optional, Dict
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.user import User
from services.auth_service import AuthService, JWT_SECRET, JWT_ALGORITHM
from audit.logger import AuditLogger
from db.models.audit import AuditAction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sso", tags=["Single Sign-On"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4500")

# ═══════════════════════════════════════════════════════════════════════════
# SAML 2.0 Service Provider
# ═══════════════════════════════════════════════════════════════════════════

def _saml_settings() -> Optional[dict]:
    """Build python3-saml settings from environment variables."""
    sp_entity = os.getenv("SAML_SP_ENTITY_ID", "")
    sp_acs = os.getenv("SAML_SP_ACS_URL", "")
    idp_entity = os.getenv("SAML_IDP_ENTITY_ID", "")
    idp_sso = os.getenv("SAML_IDP_SSO_URL", "")

    if not all([sp_entity, sp_acs, idp_entity, idp_sso]):
        return None

    sp_cert = ""
    sp_key = ""
    idp_cert = ""

    cert_file = os.getenv("SAML_SP_CERT_FILE", "")
    if cert_file and os.path.exists(cert_file):
        sp_cert = open(cert_file).read()

    key_file = os.getenv("SAML_SP_KEY_FILE", "")
    if key_file and os.path.exists(key_file):
        sp_key = open(key_file).read()

    idp_cert_file = os.getenv("SAML_IDP_CERT_FILE", "")
    if idp_cert_file and os.path.exists(idp_cert_file):
        idp_cert = open(idp_cert_file).read()

    return {
        "strict": True,
        "debug": os.getenv("APP_ENV", "") != "production",
        "sp": {
            "entityId": sp_entity,
            "assertionConsumerService": {
                "url": sp_acs,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": os.getenv("SAML_SP_SLS_URL", ""),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": sp_cert,
            "privateKey": sp_key,
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        },
        "idp": {
            "entityId": idp_entity,
            "singleSignOnService": {
                "url": idp_sso,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "singleLogoutService": {
                "url": os.getenv("SAML_IDP_SLO_URL", ""),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": idp_cert,
        },
        "security": {
            "authnRequestsSigned": bool(sp_cert and sp_key),
            "wantAssertionsSigned": True,
            "wantNameIdEncrypted": False,
            "signMetadata": bool(sp_cert and sp_key),
        },
    }


def _prepare_saml_request(request: Request) -> dict:
    """Build the request dict python3-saml expects from a FastAPI request."""
    url_parts = str(request.url).split("?")
    return {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.headers.get("host", "localhost"),
        "server_port": request.url.port or (443 if request.url.scheme == "https" else 80),
        "script_name": request.url.path,
        "get_data": dict(request.query_params),
        "post_data": {},
    }


def _ensure_user_from_saml(
    db: Session, attrs: Dict, tenant_id: str
) -> User:
    """Find or create a local user from SAML assertion attributes."""
    email = attrs.get("email", [""])[0] if isinstance(attrs.get("email"), list) else attrs.get("email", "")
    username = attrs.get("username", [""])[0] if isinstance(attrs.get("username"), list) else attrs.get("username", "")
    full_name = attrs.get("displayName", [""])[0] if isinstance(attrs.get("displayName"), list) else attrs.get("displayName", "")
    department = attrs.get("department", [""])[0] if isinstance(attrs.get("department"), list) else attrs.get("department", "")

    if not username and email:
        username = email.split("@")[0]

    # Look up by email or username
    user = db.query(User).filter(
        User.tenant_id == tenant_id,
        User.email == email
    ).first() if email else None

    if not user and username:
        user = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.username == username
        ).first()

    if not user:
        # JIT provisioning
        user = User(
            tenant_id=tenant_id,
            user_id=username.upper() or email.split("@")[0].upper(),
            username=username or email.split("@")[0],
            email=email,
            full_name=full_name or username,
            department=department,
            source_system="saml",
            status="active",
            is_platform_user=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("JIT provisioned SAML user: %s", username)
    else:
        # Update profile
        if full_name:
            user.full_name = full_name
        if department:
            user.department = department
        user.last_login = datetime.utcnow()
        user.sync_source = "saml"
        db.commit()

    return user


@router.get("/saml/metadata")
async def saml_metadata():
    """Return SAML SP metadata XML for IdP configuration."""
    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
        from onelogin.saml2.settings import OneLogin_Saml2_Settings
    except ImportError:
        raise HTTPException(503, "python3-saml not installed")

    settings = _saml_settings()
    if not settings:
        raise HTTPException(503, "SAML not configured. Set SAML_SP_* and SAML_IDP_* env vars.")

    saml_settings = OneLogin_Saml2_Settings(settings, sp_validation_only=True)
    metadata = saml_settings.get_sp_metadata()
    errors = saml_settings.validate_metadata(metadata)

    if errors:
        raise HTTPException(500, f"SAML metadata validation errors: {errors}")

    return HTMLResponse(content=metadata, media_type="application/xml")


@router.get("/saml/login")
async def saml_login(
    request: Request,
    tenant_id: str = Query("tenant_default"),
    relay_state: Optional[str] = Query(None),
):
    """Initiate SAML SSO — redirect to IdP."""
    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
    except ImportError:
        raise HTTPException(503, "python3-saml not installed")

    settings = _saml_settings()
    if not settings:
        raise HTTPException(503, "SAML not configured")

    req = _prepare_saml_request(request)
    auth = OneLogin_Saml2_Auth(req, settings)

    # Encode tenant_id in RelayState so we get it back in the callback
    state = json.dumps({"tenant_id": tenant_id, "redirect": relay_state or "/"})
    redirect_url = auth.login(return_to=state)

    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/saml/acs")
async def saml_acs(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    SAML Assertion Consumer Service — receives POST from IdP after authentication.
    Validates the SAML response, extracts user, issues JWT, redirects to frontend.
    """
    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
    except ImportError:
        raise HTTPException(503, "python3-saml not installed")

    settings = _saml_settings()
    if not settings:
        raise HTTPException(503, "SAML not configured")

    form_data = await request.form()
    req = _prepare_saml_request(request)
    req["post_data"] = dict(form_data)

    auth = OneLogin_Saml2_Auth(req, settings)
    auth.process_response()
    errors = auth.get_errors()

    if errors:
        logger.error("SAML ACS errors: %s (reason: %s)", errors, auth.get_last_error_reason())
        raise HTTPException(401, f"SAML authentication failed: {', '.join(errors)}")

    if not auth.is_authenticated():
        raise HTTPException(401, "SAML authentication failed: not authenticated")

    # Extract user attributes
    attrs = auth.get_attributes()
    name_id = auth.get_nameid()
    attrs["email"] = attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                               attrs.get("email", [name_id]))
    attrs["username"] = attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
                                  attrs.get("username", []))
    attrs["displayName"] = attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
                                     attrs.get("displayName", []))
    attrs["department"] = attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/department",
                                    attrs.get("department", []))

    # Parse RelayState for tenant_id
    relay_state = form_data.get("RelayState", "{}")
    try:
        state = json.loads(relay_state)
    except (json.JSONDecodeError, TypeError):
        state = {"tenant_id": "tenant_default", "redirect": "/"}

    tenant_id = state.get("tenant_id", "tenant_default")

    # Find or create user
    user = _ensure_user_from_saml(db, attrs, tenant_id)

    # Issue JWT tokens
    auth_service = AuthService(db)
    user_role = auth_service._determine_role(user)
    token_response = auth_service._create_tokens(user, tenant_id, user_role)

    # Audit
    AuditLogger().log(
        action=AuditAction.USER_LOGIN,
        actor_user_id=user.user_id,
        target_type="auth",
        target_id=user.user_id,
        details={"backend": "saml", "idp": settings["idp"]["entityId"]},
    )

    # Redirect to frontend with tokens in URL fragment (not query — keeps tokens out of server logs)
    redirect_path = state.get("redirect", "/")
    redirect_url = (
        f"{FRONTEND_URL}/sso-callback"
        f"#access_token={token_response.access_token}"
        f"&refresh_token={token_response.refresh_token}"
        f"&redirect={redirect_path}"
    )

    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/saml/sls")
async def saml_sls(request: Request):
    """SAML Single Logout Service."""
    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
    except ImportError:
        raise HTTPException(503, "python3-saml not installed")

    settings = _saml_settings()
    if not settings:
        raise HTTPException(503, "SAML not configured")

    req = _prepare_saml_request(request)
    auth = OneLogin_Saml2_Auth(req, settings)
    auth.process_slo()

    return RedirectResponse(url=f"{FRONTEND_URL}/login?slo=1", status_code=302)


# ═══════════════════════════════════════════════════════════════════════════
# OAuth 2.0 / OpenID Connect
# ═══════════════════════════════════════════════════════════════════════════

_oidc_client = None


def _get_oidc_client():
    """Lazy-init the OIDC client from authlib."""
    global _oidc_client
    if _oidc_client:
        return _oidc_client

    try:
        from authlib.integrations.starlette_client import OAuth
    except ImportError:
        raise HTTPException(503, "authlib not installed")

    client_id = os.getenv("OIDC_CLIENT_ID", "")
    client_secret = os.getenv("OIDC_CLIENT_SECRET", "")
    discovery_url = os.getenv("OIDC_DISCOVERY_URL", "")

    if not all([client_id, discovery_url]):
        raise HTTPException(503, "OIDC not configured. Set OIDC_CLIENT_ID and OIDC_DISCOVERY_URL.")

    scopes = os.getenv("OIDC_SCOPES", "openid,profile,email").replace(",", " ")

    oauth = OAuth()
    oauth.register(
        name="oidc",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url=discovery_url,
        client_kwargs={"scope": scopes},
    )
    _oidc_client = oauth
    return _oidc_client


def _ensure_user_from_oidc(db: Session, userinfo: dict, tenant_id: str) -> User:
    """Find or create a local user from OIDC userinfo."""
    email = userinfo.get("email", "")
    username = userinfo.get("preferred_username", email.split("@")[0] if email else "")
    full_name = userinfo.get("name", "")
    department = userinfo.get("department", "")

    user = db.query(User).filter(
        User.tenant_id == tenant_id, User.email == email
    ).first() if email else None

    if not user and username:
        user = db.query(User).filter(
            User.tenant_id == tenant_id, User.username == username
        ).first()

    if not user:
        user = User(
            tenant_id=tenant_id,
            user_id=username.upper(),
            username=username,
            email=email,
            full_name=full_name or username,
            department=department,
            source_system="oidc",
            status="active",
            is_platform_user=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("JIT provisioned OIDC user: %s", username)
    else:
        if full_name:
            user.full_name = full_name
        if department:
            user.department = department
        user.last_login = datetime.utcnow()
        user.sync_source = "oidc"
        db.commit()

    return user


@router.get("/oidc/login")
async def oidc_login(
    request: Request,
    tenant_id: str = Query("tenant_default"),
):
    """Initiate OIDC login — redirect to authorization endpoint."""
    oauth = _get_oidc_client()
    redirect_uri = os.getenv("OIDC_REDIRECT_URI", str(request.url_for("oidc_callback")))

    # Store tenant_id in session-like state param
    request.session["sso_tenant_id"] = tenant_id

    return await oauth.oidc.authorize_redirect(request, redirect_uri)


@router.get("/oidc/callback")
async def oidc_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """OIDC callback — exchange code for tokens, extract user, issue JWT."""
    oauth = _get_oidc_client()

    try:
        token = await oauth.oidc.authorize_access_token(request)
    except Exception as e:
        logger.error("OIDC token exchange failed: %s", str(e))
        raise HTTPException(401, f"OIDC authentication failed: {str(e)}")

    userinfo = token.get("userinfo")
    if not userinfo:
        # Fetch from userinfo endpoint
        try:
            userinfo = await oauth.oidc.userinfo(token=token)
        except Exception:
            userinfo = {}

    if not userinfo:
        raise HTTPException(401, "OIDC: could not retrieve user info")

    tenant_id = request.session.pop("sso_tenant_id", "tenant_default")

    user = _ensure_user_from_oidc(db, dict(userinfo), tenant_id)

    # Issue JWT
    auth_service = AuthService(db)
    user_role = auth_service._determine_role(user)
    token_response = auth_service._create_tokens(user, tenant_id, user_role)

    AuditLogger().log(
        action=AuditAction.USER_LOGIN,
        actor_user_id=user.user_id,
        target_type="auth",
        target_id=user.user_id,
        details={"backend": "oidc", "provider": os.getenv("OIDC_DISCOVERY_URL", "")},
    )

    redirect_url = (
        f"{FRONTEND_URL}/sso-callback"
        f"#access_token={token_response.access_token}"
        f"&refresh_token={token_response.refresh_token}"
        f"&redirect=/"
    )

    return RedirectResponse(url=redirect_url, status_code=302)


# ═══════════════════════════════════════════════════════════════════════════
# SSO Status & Configuration
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/status")
async def sso_status():
    """Return which SSO methods are configured and available."""
    saml_configured = bool(_saml_settings())
    oidc_configured = bool(os.getenv("OIDC_CLIENT_ID") and os.getenv("OIDC_DISCOVERY_URL"))
    ldap_configured = bool(os.getenv("LDAP_SERVER"))
    graph_configured = bool(os.getenv("AZURE_CLIENT_ID") and os.getenv("AZURE_TENANT_ID"))

    return {
        "saml": {
            "configured": saml_configured,
            "metadata_url": "/auth/sso/saml/metadata" if saml_configured else None,
            "login_url": "/auth/sso/saml/login" if saml_configured else None,
        },
        "oidc": {
            "configured": oidc_configured,
            "login_url": "/auth/sso/oidc/login" if oidc_configured else None,
        },
        "ldap": {
            "configured": ldap_configured,
        },
        "graph_api": {
            "configured": graph_configured,
        },
        "local": {
            "configured": True,
            "login_url": "/auth/login",
        },
    }
