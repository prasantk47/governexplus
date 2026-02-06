"""
User Service
Business logic for User management operations
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
import hashlib
import secrets

from repositories.user_repository import UserRepository
from api.schemas.user import (
    UserCreate,
    UserUpdate,
    UserFilters,
    UserSummary,
    UserDetailResponse,
    UserResponse,
    PaginatedUsersResponse,
    UserStatsResponse,
    RoleInfo,
    ViolationInfo,
    EntitlementInfo,
    RoleAssignment,
)
from audit.logger import AuditLogger, AuditAction


class UserService:
    """
    Service layer for User management.
    Handles business logic, validation, and audit logging.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = UserRepository(db)
        self.audit_logger = AuditLogger()

    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level"""
        if risk_score < 30:
            return "low"
        elif risk_score < 60:
            return "medium"
        elif risk_score < 80:
            return "high"
        return "critical"

    def _user_to_summary(self, user) -> UserSummary:
        """Convert User model to UserSummary schema"""
        role_count = len([r for r in user.roles if r.is_active]) if user.roles else 0
        return UserSummary(
            id=user.id,
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            department=user.department,
            title=user.title,
            status=user.status,
            risk_score=user.risk_score or 0.0,
            risk_level=self._get_risk_level(user.risk_score or 0),
            violation_count=user.violation_count or 0,
            role_count=role_count,
            last_login=user.last_login
        )

    def _user_to_detail(self, user) -> UserDetailResponse:
        """Convert User model to UserDetailResponse schema"""
        roles = []
        for ur in (user.roles or []):
            if ur.is_active and ur.role:
                roles.append(RoleInfo(
                    id=ur.role.id,
                    role_id=ur.role.role_id,
                    role_name=ur.role.role_name,
                    role_type=ur.role.role_type,
                    risk_level=ur.role.risk_level,
                    assigned_at=ur.assigned_at,
                    valid_from=ur.valid_from,
                    valid_to=ur.valid_to,
                    is_active=ur.is_active
                ))

        violations = []
        for v in (user.violations or []):
            violations.append(ViolationInfo(
                id=v.id,
                violation_id=v.violation_id,
                rule_name=v.rule_name,
                severity=v.severity.value if hasattr(v.severity, 'value') else str(v.severity),
                status=v.status.value if hasattr(v.status, 'value') else str(v.status),
                detected_at=v.detected_at,
                description=getattr(v, 'description', None)
            ))

        entitlements = []
        for e in (user.entitlements or []):
            entitlements.append(EntitlementInfo(
                id=e.id,
                auth_object=e.auth_object,
                auth_field=e.auth_field,
                auth_value=e.auth_value,
                source_role=e.source_role,
                is_sensitive=e.is_sensitive or False
            ))

        active_violations = len([v for v in violations if v.status not in ['closed', 'remediated']])
        sensitive_count = len([e for e in entitlements if e.is_sensitive])

        return UserDetailResponse(
            id=user.id,
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            department=user.department,
            title=user.title,
            cost_center=user.cost_center,
            company_code=user.company_code,
            manager_user_id=user.manager_user_id,
            location=user.location,
            status=user.status,
            user_type=user.user_type or 'dialog',
            risk_score=user.risk_score or 0.0,
            risk_level=self._get_risk_level(user.risk_score or 0),
            violation_count=user.violation_count or 0,
            last_login=user.last_login,
            last_synced_at=user.last_synced_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=roles,
            violations=violations,
            entitlements=entitlements,
            total_roles=len(roles),
            active_violations=active_violations,
            sensitive_access_count=sensitive_count
        )

    # ============== User Operations ==============

    def list_users(
        self,
        tenant_id: str,
        filters: UserFilters,
        limit: int = 100,
        offset: int = 0
    ) -> PaginatedUsersResponse:
        """List users with pagination and filters"""
        users, total = self.repository.get_users(
            tenant_id=tenant_id,
            search=filters.search,
            status=filters.status.value if filters.status else None,
            department=filters.department,
            risk_level=filters.risk_level.value if filters.risk_level else None,
            user_type=filters.user_type.value if filters.user_type else None,
            has_violations=filters.has_violations,
            skip=offset,
            limit=limit
        )

        items = [self._user_to_summary(u) for u in users]

        return PaginatedUsersResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(items)) < total
        )

    def get_user(self, tenant_id: str, user_id: str) -> Optional[UserDetailResponse]:
        """Get user detail by user_id"""
        user = self.repository.get_user_with_details(tenant_id, user_id)
        if not user:
            return None
        return self._user_to_detail(user)

    def create_user(
        self,
        tenant_id: str,
        user_data: UserCreate,
        created_by: str
    ) -> UserResponse:
        """Create a new user"""
        # Check for duplicates
        if self.repository.check_user_exists(
            tenant_id,
            user_id=user_data.user_id,
            email=user_data.email,
            username=user_data.username
        ):
            raise ValueError("User with this ID, email, or username already exists")

        # Prepare user data
        data = user_data.model_dump(exclude={'password'})

        # Hash password if provided
        if user_data.password:
            salt = secrets.token_hex(16)
            hashed = hashlib.sha256(f"{salt}{user_data.password}".encode()).hexdigest()
            data['password_hash'] = f"{salt}:{hashed}"
            data['is_platform_user'] = True

        user = self.repository.create_user(tenant_id, data)

        # Audit log
        self.audit_logger.log(
            action=AuditAction.USER_CREATED,
            actor_user_id=created_by,
            target_type="user",
            target_id=user.user_id,
            target_name=user.full_name,
            details={"department": user.department, "user_type": user.user_type}
        )

        return UserResponse(
            id=user.id,
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            department=user.department,
            title=user.title,
            status=user.status,
            risk_score=user.risk_score or 0.0,
            violation_count=user.violation_count or 0,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    def update_user(
        self,
        tenant_id: str,
        user_id: str,
        user_data: UserUpdate,
        updated_by: str
    ) -> Optional[UserResponse]:
        """Update an existing user"""
        # Get current user for comparison
        current = self.repository.get_user_by_user_id(tenant_id, user_id)
        if not current:
            return None

        # Prepare update data (exclude None values)
        data = {k: v for k, v in user_data.model_dump().items() if v is not None}

        # Handle status enum
        if 'status' in data and hasattr(data['status'], 'value'):
            data['status'] = data['status'].value

        if 'user_type' in data and hasattr(data['user_type'], 'value'):
            data['user_type'] = data['user_type'].value

        user = self.repository.update_user(tenant_id, user_id, data)
        if not user:
            return None

        # Audit log
        self.audit_logger.log(
            action=AuditAction.USER_UPDATED,
            actor_user_id=updated_by,
            target_type="user",
            target_id=user.user_id,
            target_name=user.full_name,
            details={"updated_fields": list(data.keys())}
        )

        return UserResponse(
            id=user.id,
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            department=user.department,
            title=user.title,
            status=user.status,
            risk_score=user.risk_score or 0.0,
            violation_count=user.violation_count or 0,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    def delete_user(
        self,
        tenant_id: str,
        user_id: str,
        deleted_by: str
    ) -> bool:
        """Delete a user (soft delete)"""
        user = self.repository.get_user_by_user_id(tenant_id, user_id)
        if not user:
            return False

        result = self.repository.delete_user(tenant_id, user_id, soft_delete=True)

        if result:
            # Audit log
            self.audit_logger.log(
                action=AuditAction.USER_DELETED,
                actor_user_id=deleted_by,
                target_type="user",
                target_id=user_id,
                target_name=user.full_name,
                details={"soft_delete": True}
            )

        return result

    # ============== Role Operations ==============

    def get_user_roles(self, tenant_id: str, user_id: str) -> List[RoleInfo]:
        """Get roles assigned to a user"""
        user_roles = self.repository.get_user_roles(tenant_id, user_id)
        return [
            RoleInfo(
                id=ur.role.id,
                role_id=ur.role.role_id,
                role_name=ur.role.role_name,
                role_type=ur.role.role_type,
                risk_level=ur.role.risk_level,
                assigned_at=ur.assigned_at,
                valid_from=ur.valid_from,
                valid_to=ur.valid_to,
                is_active=ur.is_active
            )
            for ur in user_roles if ur.role
        ]

    def assign_role(
        self,
        tenant_id: str,
        user_id: str,
        assignment: RoleAssignment,
        assigned_by: str
    ) -> Optional[RoleInfo]:
        """Assign a role to a user"""
        user_role = self.repository.assign_role(
            tenant_id=tenant_id,
            user_id=user_id,
            role_id=assignment.role_id,
            assigned_by=assigned_by,
            valid_from=assignment.valid_from,
            valid_to=assignment.valid_to
        )

        if not user_role:
            return None

        # Audit log
        self.audit_logger.log(
            action=AuditAction.ROLE_ASSIGNED,
            actor_user_id=assigned_by,
            target_type="user_role",
            target_id=f"{user_id}:{assignment.role_id}",
            details={
                "user_id": user_id,
                "role_id": assignment.role_id,
                "justification": assignment.justification
            }
        )

        return RoleInfo(
            id=user_role.role.id,
            role_id=user_role.role.role_id,
            role_name=user_role.role.role_name,
            role_type=user_role.role.role_type,
            risk_level=user_role.role.risk_level,
            assigned_at=user_role.assigned_at,
            valid_from=user_role.valid_from,
            valid_to=user_role.valid_to,
            is_active=user_role.is_active
        )

    def revoke_role(
        self,
        tenant_id: str,
        user_id: str,
        role_id: str,
        revoked_by: str
    ) -> bool:
        """Revoke a role from a user"""
        result = self.repository.revoke_role(tenant_id, user_id, role_id)

        if result:
            self.audit_logger.log(
                action=AuditAction.ROLE_REVOKED,
                actor_user_id=revoked_by,
                target_type="user_role",
                target_id=f"{user_id}:{role_id}",
                details={"user_id": user_id, "role_id": role_id}
            )

        return result

    # ============== Statistics ==============

    def get_user_stats(self, tenant_id: str) -> UserStatsResponse:
        """Get user statistics"""
        stats = self.repository.get_user_stats(tenant_id)
        return UserStatsResponse(**stats)

    def get_departments(self, tenant_id: str) -> List[str]:
        """Get list of departments"""
        return self.repository.get_departments(tenant_id)

    # ============== Risk Operations ==============

    def recalculate_risk_score(
        self,
        tenant_id: str,
        user_id: str
    ) -> Optional[float]:
        """Recalculate user's risk score based on violations"""
        violations = self.repository.get_user_violations(tenant_id, user_id)

        # Calculate risk score based on violations
        total_score = 0
        violation_count = 0

        for v in violations:
            if v.status in ['open', 'in_progress']:
                violation_count += 1
                severity = v.severity.value if hasattr(v.severity, 'value') else str(v.severity)
                if severity == 'critical':
                    total_score += 25
                elif severity == 'high':
                    total_score += 15
                elif severity == 'medium':
                    total_score += 8
                else:
                    total_score += 3

        risk_score = min(total_score, 100)

        # Update user
        user = self.repository.update_risk_score(
            tenant_id, user_id, risk_score, violation_count
        )

        return risk_score if user else None
