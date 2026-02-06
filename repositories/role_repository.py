"""
Role Repository
Database operations for Role management with tenant isolation
"""

from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from datetime import datetime

from .base import BaseRepository
from db.models.user import Role, UserRole, User


class RoleRepository(BaseRepository[Role]):
    """
    Repository for Role CRUD operations.
    All operations are tenant-isolated.
    """

    def __init__(self, db: Session):
        super().__init__(db, Role)

    def get_roles(
        self,
        tenant_id: str,
        search: Optional[str] = None,
        status: Optional[str] = None,
        role_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        department: Optional[str] = None,
        owner_user_id: Optional[str] = None,
        source_system: Optional[str] = None,
        is_sensitive: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Role], int]:
        """
        Get paginated list of roles with filters.
        Returns tuple of (roles, total_count)
        """
        query = self._get_base_query(tenant_id).filter(Role.is_active == True)

        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Role.role_id.ilike(search_term),
                    Role.role_name.ilike(search_term),
                    Role.description.ilike(search_term)
                )
            )

        # Status filter (using is_active for now, can extend with status column)
        if status:
            if status == "active":
                query = query.filter(Role.is_active == True)
            elif status == "inactive":
                query = query.filter(Role.is_active == False)

        # Role type filter
        if role_type:
            query = query.filter(Role.role_type == role_type)

        # Risk level filter
        if risk_level:
            query = query.filter(Role.risk_level == risk_level)

        # Department filter (if column exists)
        if department and hasattr(Role, 'department'):
            query = query.filter(Role.department == department)

        # Owner filter
        if owner_user_id:
            query = query.filter(Role.owner_user_id == owner_user_id)

        # Source system filter
        if source_system:
            query = query.filter(Role.source_system == source_system)

        # Sensitivity filter
        if is_sensitive is not None:
            query = query.filter(Role.is_sensitive == is_sensitive)

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering
        roles = query.order_by(Role.role_name).offset(skip).limit(limit).all()

        return roles, total

    def get_role_by_role_id(
        self,
        tenant_id: str,
        role_id: str
    ) -> Optional[Role]:
        """Get role by role_id"""
        return self._get_base_query(tenant_id).filter(
            Role.role_id == role_id
        ).first()

    def get_role_with_details(
        self,
        tenant_id: str,
        role_id: str
    ) -> Optional[Role]:
        """Get role with user assignments"""
        return self._get_base_query(tenant_id).options(
            joinedload(Role.user_assignments).joinedload(UserRole.user)
        ).filter(Role.role_id == role_id).first()

    def create_role(
        self,
        tenant_id: str,
        role_data: dict
    ) -> Role:
        """Create a new role"""
        role_data['tenant_id'] = tenant_id
        role_data['is_active'] = True
        role_data['user_count'] = 0
        role_data['transaction_count'] = 0

        role = Role(**role_data)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def update_role(
        self,
        tenant_id: str,
        role_id: str,
        role_data: dict
    ) -> Optional[Role]:
        """Update role by role_id"""
        role = self.get_role_by_role_id(tenant_id, role_id)
        if not role:
            return None

        for key, value in role_data.items():
            if hasattr(role, key) and value is not None:
                setattr(role, key, value)

        self.db.commit()
        self.db.refresh(role)
        return role

    def delete_role(
        self,
        tenant_id: str,
        role_id: str,
        soft_delete: bool = True
    ) -> bool:
        """Delete role (soft delete by default)"""
        role = self.get_role_by_role_id(tenant_id, role_id)
        if not role:
            return False

        if soft_delete:
            role.is_active = False
            self.db.commit()
        else:
            self.db.delete(role)
            self.db.commit()

        return True

    # ============== User Assignment Operations ==============

    def get_role_users(
        self,
        tenant_id: str,
        role_id: str
    ) -> List[Dict[str, Any]]:
        """Get all users assigned to a role"""
        role = self.get_role_by_role_id(tenant_id, role_id)
        if not role:
            return []

        user_roles = self.db.query(UserRole).options(
            joinedload(UserRole.user)
        ).filter(
            UserRole.role_id == role.id,
            UserRole.is_active == True
        ).all()

        return [
            {
                "user_id": ur.user.user_id,
                "username": ur.user.username,
                "full_name": ur.user.full_name,
                "department": ur.user.department,
                "assigned_at": ur.assigned_at.isoformat() if ur.assigned_at else None,
                "assigned_by": ur.assigned_by,
                "valid_from": ur.valid_from.isoformat() if ur.valid_from else None,
                "valid_to": ur.valid_to.isoformat() if ur.valid_to else None
            }
            for ur in user_roles
        ]

    def get_user_count_for_role(
        self,
        tenant_id: str,
        role_id: str
    ) -> int:
        """Get count of active users assigned to a role"""
        role = self.get_role_by_role_id(tenant_id, role_id)
        if not role:
            return 0

        return self.db.query(UserRole).filter(
            UserRole.role_id == role.id,
            UserRole.is_active == True
        ).count()

    def update_user_count(
        self,
        tenant_id: str,
        role_id: str
    ) -> Optional[Role]:
        """Update the cached user_count for a role"""
        role = self.get_role_by_role_id(tenant_id, role_id)
        if not role:
            return None

        count = self.get_user_count_for_role(tenant_id, role_id)
        role.user_count = count
        self.db.commit()
        self.db.refresh(role)
        return role

    # ============== Statistics ==============

    def get_role_stats(self, tenant_id: str) -> dict:
        """Get role statistics for dashboard"""
        base_query = self._get_base_query(tenant_id)

        total = base_query.count()
        active = base_query.filter(Role.is_active == True).count()
        inactive = base_query.filter(Role.is_active == False).count()
        high_risk = base_query.filter(
            Role.risk_level.in_(["high", "critical"])
        ).count()
        sensitive = base_query.filter(Role.is_sensitive == True).count()

        # By type
        type_counts = self.db.query(
            Role.role_type,
            func.count(Role.id).label('count')
        ).filter(
            Role.tenant_id == tenant_id,
            Role.is_active == True
        ).group_by(Role.role_type).all()

        # By system
        system_counts = self.db.query(
            Role.source_system,
            func.count(Role.id).label('count')
        ).filter(
            Role.tenant_id == tenant_id,
            Role.is_active == True
        ).group_by(Role.source_system).all()

        # Total assignments
        total_assignments = self.db.query(func.sum(Role.user_count)).filter(
            Role.tenant_id == tenant_id,
            Role.is_active == True
        ).scalar() or 0

        return {
            "total_roles": total,
            "active_roles": active,
            "inactive_roles": inactive,
            "high_risk_roles": high_risk,
            "sensitive_roles": sensitive,
            "total_assignments": int(total_assignments),
            "by_type": {t: c for t, c in type_counts if t},
            "by_system": {s: c for s, c in system_counts if s}
        }

    def get_role_types(self, tenant_id: str) -> List[str]:
        """Get list of unique role types"""
        results = self.db.query(Role.role_type).filter(
            Role.tenant_id == tenant_id,
            Role.role_type.isnot(None)
        ).distinct().all()
        return [r[0] for r in results if r[0]]

    def get_source_systems(self, tenant_id: str) -> List[str]:
        """Get list of unique source systems"""
        results = self.db.query(Role.source_system).filter(
            Role.tenant_id == tenant_id,
            Role.source_system.isnot(None)
        ).distinct().all()
        return [r[0] for r in results if r[0]]

    def check_role_exists(
        self,
        tenant_id: str,
        role_id: str
    ) -> bool:
        """Check if role exists"""
        return self._get_base_query(tenant_id).filter(
            Role.role_id == role_id
        ).first() is not None

    # ============== Composite Role Operations ==============

    def get_child_roles(
        self,
        tenant_id: str,
        parent_role_id: str
    ) -> List[Role]:
        """Get child roles of a composite/derived role"""
        return self._get_base_query(tenant_id).filter(
            Role.parent_role_id == parent_role_id,
            Role.is_active == True
        ).all()

    def get_parent_role(
        self,
        tenant_id: str,
        role_id: str
    ) -> Optional[Role]:
        """Get parent role of a derived role"""
        role = self.get_role_by_role_id(tenant_id, role_id)
        if not role or not role.parent_role_id:
            return None

        return self.get_role_by_role_id(tenant_id, role.parent_role_id)

    # ============== Search and Analysis ==============

    def find_similar_roles(
        self,
        tenant_id: str,
        role_id: str,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find roles similar to the given role.
        Uses simple name/description matching for now.
        """
        role = self.get_role_by_role_id(tenant_id, role_id)
        if not role:
            return []

        # Get all other active roles
        other_roles = self._get_base_query(tenant_id).filter(
            Role.role_id != role_id,
            Role.is_active == True
        ).all()

        similar = []
        for other in other_roles:
            # Simple similarity based on same type and system
            score = 0.0
            if other.role_type == role.role_type:
                score += 0.3
            if other.source_system == role.source_system:
                score += 0.2
            if other.risk_level == role.risk_level:
                score += 0.2
            if other.is_sensitive == role.is_sensitive:
                score += 0.1
            # Name similarity (basic)
            if role.role_name and other.role_name:
                common_words = set(role.role_name.lower().split()) & set(other.role_name.lower().split())
                if common_words:
                    score += min(0.2, len(common_words) * 0.05)

            if score >= threshold:
                similar.append({
                    "role_id": other.role_id,
                    "role_name": other.role_name,
                    "similarity_score": round(score, 2),
                    "role_type": other.role_type,
                    "user_count": other.user_count
                })

        return sorted(similar, key=lambda x: x["similarity_score"], reverse=True)[:10]
