"""
Approver Repository
Database operations for Approver management with tenant isolation
"""

from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from datetime import datetime

from .base import BaseRepository
from db.models.approver import ApproverModel


class ApproverRepository(BaseRepository[ApproverModel]):
    """Repository for Approver CRUD operations with tenant isolation."""

    def __init__(self, db: Session):
        super().__init__(db, ApproverModel)

    def get_approvers(
        self,
        tenant_id: str,
        search: Optional[str] = None,
        approver_type: Optional[str] = None,
        status: Optional[str] = None,
        is_available: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[ApproverModel], int]:
        """Paginated, filterable approver list"""
        query = self._get_base_query(tenant_id)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    ApproverModel.approver_id.ilike(search_term),
                    ApproverModel.name.ilike(search_term),
                    ApproverModel.email.ilike(search_term),
                    ApproverModel.department.ilike(search_term),
                )
            )

        if approver_type:
            query = query.filter(ApproverModel.approver_type == approver_type)

        if status:
            query = query.filter(ApproverModel.status == status)

        if is_available is not None:
            query = query.filter(ApproverModel.is_available == is_available)

        total = query.count()
        approvers = query.order_by(ApproverModel.name).offset(skip).limit(limit).all()
        return approvers, total

    def get_by_approver_id(
        self, tenant_id: str, approver_id: str
    ) -> Optional[ApproverModel]:
        """Get approver by business ID"""
        return self._get_base_query(tenant_id).filter(
            ApproverModel.approver_id == approver_id
        ).first()

    def get_by_type(
        self, tenant_id: str, approver_type: str
    ) -> List[ApproverModel]:
        """Get all active approvers of a specific type"""
        return self._get_base_query(tenant_id).filter(
            ApproverModel.approver_type == approver_type,
            ApproverModel.is_active == True,
            ApproverModel.status == 'active'
        ).all()

    def get_available_by_type(
        self,
        tenant_id: str,
        approver_type: str,
        process_scope: Optional[str] = None,
        system_scope: Optional[str] = None
    ) -> List[ApproverModel]:
        """Get available (not OOO) approvers of a specific type"""
        query = self._get_base_query(tenant_id).filter(
            ApproverModel.approver_type == approver_type,
            ApproverModel.is_active == True,
            ApproverModel.is_available == True,
            ApproverModel.is_ooo == False,
            ApproverModel.status == 'active'
        )
        return query.all()

    def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get approver statistics"""
        base = self._get_base_query(tenant_id)
        total = base.count()
        active = base.filter(ApproverModel.status == 'active').count()
        available = base.filter(
            ApproverModel.is_available == True,
            ApproverModel.status == 'active'
        ).count()
        ooo = base.filter(ApproverModel.is_ooo == True).count()

        type_counts = self.db.query(
            ApproverModel.approver_type,
            func.count(ApproverModel.id).label('count')
        ).filter(
            ApproverModel.tenant_id == tenant_id,
            ApproverModel.status == 'active'
        ).group_by(ApproverModel.approver_type).all()

        return {
            "total": total,
            "active": active,
            "available": available,
            "ooo": ooo,
            "by_type": {t: c for t, c in type_counts}
        }
