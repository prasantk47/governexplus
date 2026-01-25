"""
Users API Router

Endpoints for user management, role assignments, and entitlement queries.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

from connectors.sap.mock_connector import SAPMockConnector
from connectors.base import ConnectionConfig, ConnectionType
from db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(tags=["Users"])

# Initialize mock SAP connector
mock_config = ConnectionConfig(
    name="SAP_DEV",
    connection_type=ConnectionType.RFC,
    host="mock.sap.local",
    sap_client="100"
)
sap_connector = SAPMockConnector(mock_config)
sap_connector.connect()


# =============================================================================
# Request/Response Models
# =============================================================================

class UserSummary(BaseModel):
    """Brief user information"""
    user_id: str
    full_name: str
    system: str


class UserDetailResponse(BaseModel):
    """Detailed user information"""
    user_id: str
    username: str
    full_name: str
    email: Optional[str]
    department: str
    function: Optional[str]
    user_type: str
    cost_center: Optional[str]
    company_code: Optional[str]
    roles: List[Dict]
    profiles: List[Dict]
    valid_from: Optional[str]
    valid_to: Optional[str]
    last_login: Optional[str]
    lock_status: int


class RoleSummary(BaseModel):
    """Brief role information"""
    role_name: str
    description: Optional[str]


class EntitlementResponse(BaseModel):
    """Entitlement detail"""
    auth_object: str
    field: str
    value: str
    source_role: Optional[str]
    system: str


# =============================================================================
# User Endpoints
# =============================================================================

@router.get("/", response_model=List[UserSummary])
async def list_users(
    search: Optional[str] = Query(None, description="Search pattern for username"),
    limit: int = Query(100, le=1000, description="Maximum results")
):
    """
    List all users from connected SAP system.
    """
    filters = {}
    if search:
        filters['username_pattern'] = f"*{search}*"
    filters['max_rows'] = limit

    users = sap_connector.get_users(filters)
    return [UserSummary(**u) for u in users]


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(user_id: str):
    """
    Get detailed information for a specific user.
    """
    try:
        user = sap_connector.get_user_details(user_id)

        return UserDetailResponse(
            user_id=user['user_id'],
            username=user['username'],
            full_name=user['full_name'],
            email=user.get('email'),
            department=user['department'],
            function=user.get('function'),
            user_type=user['user_type'],
            cost_center=user.get('cost_center'),
            company_code=user.get('company_code'),
            roles=user.get('roles', []),
            profiles=user.get('profiles', []),
            valid_from=user.get('valid_from'),
            valid_to=user.get('valid_to'),
            last_login=user.get('last_login'),
            lock_status=user.get('lock_status', 0)
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{user_id}/roles", response_model=List[Dict])
async def get_user_roles(user_id: str):
    """
    Get all roles assigned to a user.
    """
    try:
        user = sap_connector.get_user_details(user_id)
        return user.get('roles', [])

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{user_id}/entitlements", response_model=List[EntitlementResponse])
async def get_user_entitlements(user_id: str):
    """
    Get all entitlements (authorizations) for a user.

    This returns the expanded authorization values from all assigned roles.
    """
    try:
        entitlements = sap_connector.get_user_entitlements(user_id)
        return [EntitlementResponse(**e) for e in entitlements]

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{user_id}/transactions")
async def get_user_transactions(user_id: str):
    """
    Get all transaction codes accessible by a user.
    """
    try:
        entitlements = sap_connector.get_user_entitlements(user_id)

        # Filter to just S_TCODE authorizations
        tcodes = [
            {
                'tcode': e['value'],
                'source_role': e.get('source_role')
            }
            for e in entitlements
            if e['auth_object'] == 'S_TCODE'
        ]

        # Remove duplicates while preserving source info
        unique_tcodes = {}
        for t in tcodes:
            if t['tcode'] not in unique_tcodes:
                unique_tcodes[t['tcode']] = t
            else:
                # Append source role if different
                existing = unique_tcodes[t['tcode']]
                if t['source_role'] and t['source_role'] not in existing.get('source_roles', [existing['source_role']]):
                    if 'source_roles' not in existing:
                        existing['source_roles'] = [existing.pop('source_role')]
                    existing['source_roles'].append(t['source_role'])

        return {
            'user_id': user_id,
            'transaction_count': len(unique_tcodes),
            'transactions': list(unique_tcodes.values())
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Role Endpoints
# =============================================================================

@router.get("/roles/", response_model=List[RoleSummary])
async def list_roles(
    search: Optional[str] = Query(None, description="Search pattern for role name"),
    limit: int = Query(100, le=1000)
):
    """
    List all roles from connected SAP system.
    """
    filters = {}
    if search:
        filters['role_pattern'] = f"*{search}*"
    filters['max_rows'] = limit

    roles = sap_connector.get_roles(filters)
    return [
        RoleSummary(
            role_name=r['role_name'],
            description=r.get('description')
        )
        for r in roles
    ]


@router.get("/roles/{role_id}")
async def get_role(role_id: str):
    """
    Get detailed information for a specific role.
    """
    try:
        role = sap_connector.get_role_details(role_id)
        return role

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/roles/{role_id}/users")
async def get_role_users(role_id: str):
    """
    Get all users assigned to a specific role.
    """
    # In production, this would query the database or SAP
    # For mock, we'll scan all users
    users_with_role = []

    for user in sap_connector.get_users():
        try:
            user_details = sap_connector.get_user_details(user['user_id'])
            user_roles = [r['role_name'] for r in user_details.get('roles', [])]

            if role_id in user_roles:
                users_with_role.append({
                    'user_id': user['user_id'],
                    'full_name': user_details['full_name'],
                    'department': user_details['department']
                })
        except Exception:
            continue

    return {
        'role_id': role_id,
        'user_count': len(users_with_role),
        'users': users_with_role
    }
