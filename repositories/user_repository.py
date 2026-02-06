"""
User Repository
Database operations for User management with tenant isolation
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, case
from datetime import datetime

from .base import BaseRepository
from db.models.user import User, Role, UserRole, UserEntitlement
from db.models.risk import RiskViolation


class UserRepository(BaseRepository[User]):
    """
    Repository for User CRUD operations.
    All operations are tenant-isolated.
    """

    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_users(
        self,
        tenant_id: str,
        search: Optional[str] = None,
        status: Optional[str] = None,
        department: Optional[str] = None,
        risk_level: Optional[str] = None,
        user_type: Optional[str] = None,
        has_violations: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[User], int]:
        """
        Get paginated list of users with filters.
        Returns tuple of (users, total_count)
        """
        query = self._get_base_query(tenant_id)

        # Search filter (name, email, user_id)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.full_name.ilike(search_term),
                    User.email.ilike(search_term),
                    User.user_id.ilike(search_term),
                    User.username.ilike(search_term),
                    User.department.ilike(search_term)
                )
            )

        # Status filter
        if status:
            query = query.filter(User.status == status)

        # Department filter
        if department:
            query = query.filter(User.department == department)

        # User type filter
        if user_type:
            query = query.filter(User.user_type == user_type)

        # Risk level filter (based on risk_score ranges)
        if risk_level:
            if risk_level == "low":
                query = query.filter(User.risk_score < 30)
            elif risk_level == "medium":
                query = query.filter(and_(User.risk_score >= 30, User.risk_score < 60))
            elif risk_level == "high":
                query = query.filter(and_(User.risk_score >= 60, User.risk_score < 80))
            elif risk_level == "critical":
                query = query.filter(User.risk_score >= 80)

        # Has violations filter
        if has_violations is not None:
            if has_violations:
                query = query.filter(User.violation_count > 0)
            else:
                query = query.filter(User.violation_count == 0)

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering
        users = query.order_by(User.full_name).offset(skip).limit(limit).all()

        return users, total

    def get_user_by_user_id(
        self,
        tenant_id: str,
        user_id: str
    ) -> Optional[User]:
        """Get user by their user_id (not primary key)"""
        return self._get_base_query(tenant_id).filter(
            User.user_id == user_id
        ).first()

    def get_user_by_email(
        self,
        tenant_id: str,
        email: str
    ) -> Optional[User]:
        """Get user by email"""
        return self._get_base_query(tenant_id).filter(
            User.email == email
        ).first()

    def get_user_by_username(
        self,
        tenant_id: str,
        username: str
    ) -> Optional[User]:
        """Get user by username"""
        return self._get_base_query(tenant_id).filter(
            User.username == username
        ).first()

    def get_user_with_details(
        self,
        tenant_id: str,
        user_id: str
    ) -> Optional[User]:
        """Get user with all related data (roles, violations, entitlements)"""
        return self._get_base_query(tenant_id).options(
            joinedload(User.roles).joinedload(UserRole.role),
            joinedload(User.entitlements),
            joinedload(User.violations)
        ).filter(User.user_id == user_id).first()

    def create_user(
        self,
        tenant_id: str,
        user_data: dict
    ) -> User:
        """Create a new user"""
        user_data['tenant_id'] = tenant_id
        user_data['status'] = user_data.get('status', 'active')
        user_data['risk_score'] = 0.0
        user_data['violation_count'] = 0

        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(
        self,
        tenant_id: str,
        user_id: str,
        user_data: dict
    ) -> Optional[User]:
        """Update user by user_id"""
        user = self.get_user_by_user_id(tenant_id, user_id)
        if not user:
            return None

        for key, value in user_data.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(
        self,
        tenant_id: str,
        user_id: str,
        soft_delete: bool = True
    ) -> bool:
        """Delete user (soft delete by default)"""
        user = self.get_user_by_user_id(tenant_id, user_id)
        if not user:
            return False

        if soft_delete:
            user.status = 'deleted'
            self.db.commit()
        else:
            self.db.delete(user)
            self.db.commit()

        return True

    # ============== Role Operations ==============

    def get_user_roles(
        self,
        tenant_id: str,
        user_id: str
    ) -> List[UserRole]:
        """Get all roles assigned to a user"""
        user = self.get_user_by_user_id(tenant_id, user_id)
        if not user:
            return []

        return self.db.query(UserRole).options(
            joinedload(UserRole.role)
        ).filter(
            UserRole.user_id == user.id,
            UserRole.is_active == True
        ).all()

    def assign_role(
        self,
        tenant_id: str,
        user_id: str,
        role_id: str,
        assigned_by: str,
        valid_from: Optional[datetime] = None,
        valid_to: Optional[datetime] = None
    ) -> Optional[UserRole]:
        """Assign a role to a user"""
        user = self.get_user_by_user_id(tenant_id, user_id)
        if not user:
            return None

        role = self.db.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.role_id == role_id
        ).first()
        if not role:
            return None

        # Check if assignment already exists
        existing = self.db.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
            UserRole.is_active == True
        ).first()
        if existing:
            return existing

        user_role = UserRole(
            user_id=user.id,
            role_id=role.id,
            tenant_id=tenant_id,
            assigned_by=assigned_by,
            assigned_at=datetime.utcnow(),
            valid_from=valid_from or datetime.utcnow(),
            valid_to=valid_to,
            is_active=True
        )
        self.db.add(user_role)
        self.db.commit()
        self.db.refresh(user_role)
        return user_role

    def revoke_role(
        self,
        tenant_id: str,
        user_id: str,
        role_id: str
    ) -> bool:
        """Revoke a role from a user"""
        user = self.get_user_by_user_id(tenant_id, user_id)
        if not user:
            return False

        role = self.db.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.role_id == role_id
        ).first()
        if not role:
            return False

        user_role = self.db.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
            UserRole.is_active == True
        ).first()
        if not user_role:
            return False

        user_role.is_active = False
        self.db.commit()
        return True

    # ============== Entitlement Operations ==============

    def get_user_entitlements(
        self,
        tenant_id: str,
        user_id: str
    ) -> List[UserEntitlement]:
        """Get all entitlements for a user"""
        user = self.get_user_by_user_id(tenant_id, user_id)
        if not user:
            return []

        return self.db.query(UserEntitlement).filter(
            UserEntitlement.user_id == user.id
        ).all()

    # ============== Violation Operations ==============

    def get_user_violations(
        self,
        tenant_id: str,
        user_id: str,
        status: Optional[str] = None
    ) -> List[RiskViolation]:
        """Get violations for a user"""
        user = self.get_user_by_user_id(tenant_id, user_id)
        if not user:
            return []

        query = self.db.query(RiskViolation).filter(
            RiskViolation.user_id == user.id
        )
        if status:
            query = query.filter(RiskViolation.status == status)

        return query.order_by(RiskViolation.detected_at.desc()).all()

    # ============== Statistics ==============

    def get_user_stats(self, tenant_id: str) -> dict:
        """Get user statistics for dashboard"""
        base_query = self._get_base_query(tenant_id)

        total = base_query.count()
        active = base_query.filter(User.status == 'active').count()
        inactive = base_query.filter(User.status == 'inactive').count()
        suspended = base_query.filter(User.status == 'suspended').count()
        high_risk = base_query.filter(User.risk_score >= 60).count()
        with_violations = base_query.filter(User.violation_count > 0).count()

        # Department breakdown
        departments = self.db.query(
            User.department,
            func.count(User.id).label('count')
        ).filter(
            User.tenant_id == tenant_id,
            User.status == 'active'
        ).group_by(User.department).all()

        return {
            "total_users": total,
            "active_users": active,
            "inactive_users": inactive,
            "suspended_users": suspended,
            "high_risk_users": high_risk,
            "users_with_violations": with_violations,
            "departments": [
                {"name": dept or "Unknown", "count": count}
                for dept, count in departments
            ]
        }

    def update_risk_score(
        self,
        tenant_id: str,
        user_id: str,
        risk_score: float,
        violation_count: int
    ) -> Optional[User]:
        """Update user's risk score and violation count"""
        user = self.get_user_by_user_id(tenant_id, user_id)
        if not user:
            return None

        user.risk_score = risk_score
        user.violation_count = violation_count
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_departments(self, tenant_id: str) -> List[str]:
        """Get list of unique departments"""
        results = self.db.query(User.department).filter(
            User.tenant_id == tenant_id,
            User.department.isnot(None)
        ).distinct().all()
        return [r[0] for r in results if r[0]]

    def check_user_exists(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        username: Optional[str] = None
    ) -> bool:
        """Check if user exists with given identifiers"""
        query = self._get_base_query(tenant_id)

        conditions = []
        if user_id:
            conditions.append(User.user_id == user_id)
        if email:
            conditions.append(User.email == email)
        if username:
            conditions.append(User.username == username)

        if not conditions:
            return False

        return query.filter(or_(*conditions)).first() is not None
