"""
Shared FastAPI dependencies for the Governex+ platform.

Provides reusable auth, tenant, and DB dependencies.
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, Any

from db.database import get_db
from services.auth_service import AuthService

_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Extract and verify user from JWT Bearer token.

    Returns the decoded JWT payload dict with keys:
        sub, username, role, tenant_id, permissions, type, iat, exp
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    auth_svc = AuthService(db)
    payload, error = auth_svc.verify_token(credentials.credentials)
    if error:
        raise HTTPException(status_code=401, detail=error)
    return payload
