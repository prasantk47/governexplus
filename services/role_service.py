"""
Role Service
Business logic for Role management
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from repositories.role_repository import RoleRepository
from api.schemas.role import (
    RoleCreate, RoleUpdate, RoleFilters,
    RoleSummary, RoleDetailResponse, RoleResponse,
    PaginatedRolesResponse, RoleStatsResponse,
    PermissionInfo, CompositeRoleCreate, DerivedRoleCreate,
    BusinessRoleCreate
)
from audit.logger import AuditLogger


class RoleService:
    """
    Service layer for Role management.
    Handles business logic, validation, and audit logging.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = RoleRepository(db)
        self.audit = AuditLogger()

    def list_roles(
        self,
        tenant_id: str,
        filters: RoleFilters,
        limit: int = 100,
        offset: int = 0
    ) -> PaginatedRolesResponse:
        """List roles with pagination and filters"""
        roles, total = self.repo.get_roles(
            tenant_id=tenant_id,
            search=filters.search,
            status=filters.status.value if filters.status else None,
            role_type=filters.role_type.value if filters.role_type else None,
            risk_level=filters.risk_level.value if filters.risk_level else None,
            department=filters.department,
            owner_user_id=filters.owner_user_id,
            source_system=filters.source_system,
            is_sensitive=filters.is_sensitive,
            skip=offset,
            limit=limit
        )

        items = [self._to_role_summary(role) for role in roles]

        return PaginatedRolesResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total
        )

    def get_role(
        self,
        tenant_id: str,
        role_id: str
    ) -> Optional[RoleDetailResponse]:
        """Get detailed role information"""
        role = self.repo.get_role_with_details(tenant_id, role_id)
        if not role:
            return None

        return self._to_role_detail(role, tenant_id)

    def create_role(
        self,
        tenant_id: str,
        data: RoleCreate,
        created_by: str
    ) -> RoleResponse:
        """Create a new role"""
        # Check if role_id already exists
        if self.repo.check_role_exists(tenant_id, data.role_id):
            raise ValueError(f"Role with ID {data.role_id} already exists")

        role_data = data.model_dump(exclude_none=True)
        role = self.repo.create_role(tenant_id, role_data)

        # Audit log
        self.audit.log_action(
            action="role.created",
            resource_type="role",
            resource_id=role.role_id,
            tenant_id=tenant_id,
            user_id=created_by,
            details={"role_name": role.role_name, "role_type": role.role_type}
        )

        return self._to_role_response(role)

    def update_role(
        self,
        tenant_id: str,
        role_id: str,
        data: RoleUpdate,
        updated_by: str
    ) -> Optional[RoleResponse]:
        """Update an existing role"""
        role_data = data.model_dump(exclude_none=True)
        if not role_data:
            return None

        role = self.repo.update_role(tenant_id, role_id, role_data)
        if not role:
            return None

        # Audit log
        self.audit.log_action(
            action="role.updated",
            resource_type="role",
            resource_id=role_id,
            tenant_id=tenant_id,
            user_id=updated_by,
            details={"updated_fields": list(role_data.keys())}
        )

        return self._to_role_response(role)

    def delete_role(
        self,
        tenant_id: str,
        role_id: str,
        deleted_by: str
    ) -> bool:
        """Delete a role (soft delete)"""
        # Check if role has active assignments
        user_count = self.repo.get_user_count_for_role(tenant_id, role_id)
        if user_count > 0:
            raise ValueError(f"Cannot delete role with {user_count} active assignments")

        result = self.repo.delete_role(tenant_id, role_id)

        if result:
            self.audit.log_action(
                action="role.deleted",
                resource_type="role",
                resource_id=role_id,
                tenant_id=tenant_id,
                user_id=deleted_by
            )

        return result

    def get_role_stats(self, tenant_id: str) -> RoleStatsResponse:
        """Get role statistics"""
        stats = self.repo.get_role_stats(tenant_id)
        return RoleStatsResponse(
            total_roles=stats["total_roles"],
            active_roles=stats["active_roles"],
            draft_roles=0,  # Would need status column
            deprecated_roles=stats["inactive_roles"],
            high_risk_roles=stats["high_risk_roles"],
            roles_with_sod_conflicts=0,  # Would need SoD analysis
            total_assignments=stats["total_assignments"],
            by_type=stats["by_type"],
            by_system=stats["by_system"],
            by_department=[]  # Would need department data
        )

    def get_role_users(
        self,
        tenant_id: str,
        role_id: str
    ) -> List[Dict[str, Any]]:
        """Get users assigned to a role"""
        return self.repo.get_role_users(tenant_id, role_id)

    def get_role_types(self, tenant_id: str) -> List[str]:
        """Get available role types"""
        return self.repo.get_role_types(tenant_id)

    def get_source_systems(self, tenant_id: str) -> List[str]:
        """Get available source systems"""
        return self.repo.get_source_systems(tenant_id)

    def find_similar_roles(
        self,
        tenant_id: str,
        role_id: str,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Find similar roles"""
        return self.repo.find_similar_roles(tenant_id, role_id, threshold)

    def create_composite_role(
        self,
        tenant_id: str,
        data: CompositeRoleCreate,
        created_by: str
    ) -> RoleResponse:
        """Create a composite role from multiple child roles"""
        # Validate child roles exist
        for child_id in data.child_role_ids:
            if not self.repo.check_role_exists(tenant_id, child_id):
                raise ValueError(f"Child role {child_id} not found")

        role_data = {
            "role_id": data.role_id,
            "role_name": data.role_name,
            "description": data.description,
            "role_type": "composite",
            "owner_user_id": data.owner_user_id,
            "is_active": True
        }

        role = self.repo.create_role(tenant_id, role_data)

        self.audit.log_action(
            action="role.composite_created",
            resource_type="role",
            resource_id=role.role_id,
            tenant_id=tenant_id,
            user_id=created_by,
            details={"child_roles": data.child_role_ids}
        )

        return self._to_role_response(role)

    def create_derived_role(
        self,
        tenant_id: str,
        data: DerivedRoleCreate,
        created_by: str
    ) -> RoleResponse:
        """Create a derived role from a parent role"""
        # Validate parent role exists
        if not self.repo.check_role_exists(tenant_id, data.parent_role_id):
            raise ValueError(f"Parent role {data.parent_role_id} not found")

        role_data = {
            "role_id": data.role_id,
            "role_name": data.role_name,
            "description": data.description,
            "role_type": "derived",
            "parent_role_id": data.parent_role_id,
            "owner_user_id": data.owner_user_id,
            "is_active": True
        }

        role = self.repo.create_role(tenant_id, role_data)

        self.audit.log_action(
            action="role.derived_created",
            resource_type="role",
            resource_id=role.role_id,
            tenant_id=tenant_id,
            user_id=created_by,
            details={
                "parent_role": data.parent_role_id,
                "org_levels": data.org_level_values
            }
        )

        return self._to_role_response(role)

    def create_business_role(
        self,
        tenant_id: str,
        data: BusinessRoleCreate,
        created_by: str
    ) -> RoleResponse:
        """Create a business role"""
        role_data = {
            "role_id": data.role_id,
            "role_name": data.role_name,
            "description": data.description,
            "role_type": "business",
            "owner_user_id": data.owner_user_id,
            "is_active": True
        }

        role = self.repo.create_role(tenant_id, role_data)

        self.audit.log_action(
            action="role.business_created",
            resource_type="role",
            resource_id=role.role_id,
            tenant_id=tenant_id,
            user_id=created_by,
            details={
                "department": data.department,
                "process": data.business_process,
                "technical_roles": data.technical_role_ids
            }
        )

        return self._to_role_response(role)

    # ============== Private Methods ==============

    def _to_role_summary(self, role) -> RoleSummary:
        """Convert Role model to RoleSummary"""
        return RoleSummary(
            id=role.id,
            role_id=role.role_id,
            role_name=role.role_name,
            description=role.description,
            role_type=role.role_type or "single",
            status="active" if role.is_active else "inactive",
            risk_level=role.risk_level or "medium",
            is_sensitive=role.is_sensitive or False,
            source_system=role.source_system or "SAP",
            user_count=role.user_count or 0,
            permission_count=role.transaction_count or 0,
            sod_conflict_count=0,  # Would need SoD analysis
            owner_user_id=role.owner_user_id,
            owner_email=role.owner_email,
            department=getattr(role, 'department', None),
            created_at=role.created_at,
            updated_at=role.updated_at
        )

    def _to_role_detail(self, role, tenant_id: str) -> RoleDetailResponse:
        """Convert Role model to RoleDetailResponse"""
        # Get assigned users
        assigned_users = self.repo.get_role_users(tenant_id, role.role_id)

        # Get child roles if composite
        child_roles = []
        if role.role_type == "composite":
            children = self.repo.get_child_roles(tenant_id, role.role_id)
            child_roles = [c.role_id for c in children]

        return RoleDetailResponse(
            id=role.id,
            role_id=role.role_id,
            role_name=role.role_name,
            description=role.description,
            role_type=role.role_type or "single",
            status="active" if role.is_active else "inactive",
            risk_level=role.risk_level or "medium",
            is_sensitive=role.is_sensitive or False,
            source_system=role.source_system or "SAP",
            system_client=role.system_client,
            parent_role_id=role.parent_role_id,
            owner_user_id=role.owner_user_id,
            owner_email=role.owner_email,
            department=getattr(role, 'department', None),
            business_process=getattr(role, 'business_process', None),
            user_count=role.user_count or 0,
            transaction_count=role.transaction_count or 0,
            permissions=[],  # Would need permission model
            child_roles=child_roles,
            assigned_users=assigned_users,
            sod_conflicts=[],  # Would need SoD analysis
            valid_from=role.valid_from,
            valid_to=role.valid_to,
            created_at=role.created_at,
            updated_at=role.updated_at
        )

    def _to_role_response(self, role) -> RoleResponse:
        """Convert Role model to RoleResponse"""
        return RoleResponse(
            id=role.id,
            role_id=role.role_id,
            role_name=role.role_name,
            description=role.description,
            role_type=role.role_type or "single",
            status="active" if role.is_active else "inactive",
            risk_level=role.risk_level or "medium",
            source_system=role.source_system or "SAP",
            created_at=role.created_at,
            updated_at=role.updated_at
        )
