"""
Approver Service
Business logic for managing approver personas
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from repositories.approver_repository import ApproverRepository
from api.schemas.approver import (
    ApproverCreate, ApproverUpdate, ApproverSummary,
    ApproverDetailResponse, PaginatedApproversResponse,
    ApproverStatsResponse, ApproverTypeInfo,
)
from audit.logger import AuditLogger
from db.models.audit import AuditAction


# Approver type metadata
APPROVER_TYPE_INFO = {
    "LINE_MANAGER": {
        "label": "Line Manager",
        "description": "Direct reporting manager who approves access for their team members"
    },
    "ROLE_OWNER": {
        "label": "Role Owner",
        "description": "Business owner responsible for a specific SAP role or role set"
    },
    "PROCESS_OWNER": {
        "label": "Process Owner",
        "description": "Owner of a business process (e.g., P2P, O2C) who approves process-related access"
    },
    "DATA_OWNER": {
        "label": "Data Owner",
        "description": "Owner of sensitive data assets who approves data access requests"
    },
    "SECURITY_OFFICER": {
        "label": "Security Officer",
        "description": "IT Security team member who reviews high-risk and SoD-conflicting requests"
    },
    "COMPLIANCE_OFFICER": {
        "label": "Compliance Officer",
        "description": "Compliance team member who reviews requests for regulatory compliance"
    },
    "SYSTEM_OWNER": {
        "label": "System Owner",
        "description": "Technical owner of a target system (e.g., SAP PRD) who approves system access"
    },
    "DELEGATE": {
        "label": "Delegate",
        "description": "Temporary delegate acting on behalf of an unavailable approver"
    },
    "AI_RECOMMENDED": {
        "label": "AI Recommended",
        "description": "AI-suggested approver based on workload balancing and response patterns"
    },
    "GOVERNANCE_DESK": {
        "label": "Governance Desk",
        "description": "Central GRC team that handles escalated and unresolved approval requests"
    },
    "CISO": {
        "label": "CISO",
        "description": "Chief Information Security Officer for critical-risk approval decisions"
    },
}


class ApproverService:
    """Service layer for approver management."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ApproverRepository(db)
        self.audit = AuditLogger()

    def list_approvers(
        self,
        tenant_id: str,
        search: Optional[str] = None,
        approver_type: Optional[str] = None,
        status: Optional[str] = None,
        is_available: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> PaginatedApproversResponse:
        """List approvers with pagination and filters"""
        approvers, total = self.repo.get_approvers(
            tenant_id=tenant_id,
            search=search,
            approver_type=approver_type,
            status=status,
            is_available=is_available,
            skip=offset,
            limit=limit
        )

        items = [self._to_summary(a) for a in approvers]

        return PaginatedApproversResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total
        )

    def get_approver(
        self, tenant_id: str, approver_id: str
    ) -> Optional[ApproverDetailResponse]:
        """Get approver detail by business ID"""
        approver = self.repo.get_by_approver_id(tenant_id, approver_id)
        if not approver:
            return None
        return self._to_detail(approver)

    def create_approver(
        self, tenant_id: str, data: ApproverCreate, current_user: str
    ) -> ApproverSummary:
        """Create a new approver"""
        existing = self.repo.get_by_approver_id(tenant_id, data.approver_id)
        if existing:
            raise ValueError(f"Approver with ID '{data.approver_id}' already exists")

        obj_data = {
            "approver_id": data.approver_id,
            "name": data.name,
            "email": data.email,
            "approver_type": data.approver_type.value,
            "process_scope": data.process_scope,
            "system_scope": data.system_scope,
            "department": data.department,
            "job_title": data.job_title,
            "status": "active",
            "is_active": True,
            "is_available": True,
            "is_ooo": False,
        }

        approver = self.repo.create(obj_data, tenant_id)

        self.audit.log(
            action=AuditAction.APPROVER_CREATED,
            actor_user_id=current_user,
            target_type="Approver",
            target_id=approver.approver_id,
            target_name=approver.name,
            new_values=obj_data,
            compliance_relevant=True
        )

        return self._to_summary(approver)

    def update_approver(
        self,
        tenant_id: str,
        approver_id: str,
        data: ApproverUpdate,
        current_user: str
    ) -> Optional[ApproverSummary]:
        """Update an existing approver"""
        approver = self.repo.get_by_approver_id(tenant_id, approver_id)
        if not approver:
            return None

        old_values = {
            "name": approver.name,
            "email": approver.email,
            "approver_type": approver.approver_type,
            "status": approver.status,
        }

        update_data = data.model_dump(exclude_unset=True)
        if "approver_type" in update_data and update_data["approver_type"]:
            update_data["approver_type"] = update_data["approver_type"].value if hasattr(update_data["approver_type"], 'value') else update_data["approver_type"]
        if "status" in update_data and update_data["status"]:
            update_data["status"] = update_data["status"].value if hasattr(update_data["status"], 'value') else update_data["status"]

        updated = self.repo.update(approver.id, update_data, tenant_id)
        if not updated:
            return None

        self.audit.log(
            action=AuditAction.APPROVER_MODIFIED,
            actor_user_id=current_user,
            target_type="Approver",
            target_id=approver_id,
            target_name=updated.name,
            old_values=old_values,
            new_values=update_data,
            compliance_relevant=True
        )

        return self._to_summary(updated)

    def delete_approver(
        self, tenant_id: str, approver_id: str, current_user: str
    ) -> bool:
        """Soft delete an approver"""
        approver = self.repo.get_by_approver_id(tenant_id, approver_id)
        if not approver:
            return False

        self.repo.soft_delete(approver.id, tenant_id)

        self.audit.log(
            action=AuditAction.APPROVER_DELETED,
            actor_user_id=current_user,
            target_type="Approver",
            target_id=approver_id,
            target_name=approver.name,
            compliance_relevant=True
        )

        return True

    def toggle_availability(
        self, tenant_id: str, approver_id: str, is_available: bool, current_user: str
    ) -> Optional[ApproverSummary]:
        """Toggle approver availability"""
        approver = self.repo.get_by_approver_id(tenant_id, approver_id)
        if not approver:
            return None

        updated = self.repo.update(
            approver.id,
            {"is_available": is_available},
            tenant_id
        )

        self.audit.log(
            action=AuditAction.APPROVER_AVAILABILITY_TOGGLED,
            actor_user_id=current_user,
            target_type="Approver",
            target_id=approver_id,
            details={"is_available": is_available}
        )

        return self._to_summary(updated) if updated else None

    def set_ooo(
        self,
        tenant_id: str,
        approver_id: str,
        ooo_until: datetime,
        delegate_id: Optional[str],
        current_user: str,
        reason: Optional[str] = None
    ) -> Optional[ApproverSummary]:
        """Set approver out-of-office with optional delegate"""
        approver = self.repo.get_by_approver_id(tenant_id, approver_id)
        if not approver:
            return None

        update_data = {
            "is_ooo": True,
            "ooo_until": ooo_until,
            "delegate_id": delegate_id,
            "ooo_reason": reason,
            "ooo_approved_by": current_user,
        }

        updated = self.repo.update(approver.id, update_data, tenant_id)

        self.audit.log(
            action=AuditAction.APPROVER_OOO_SET,
            actor_user_id=current_user,
            target_type="Approver",
            target_id=approver_id,
            target_name=approver.name,
            details={
                "ooo_until": ooo_until.isoformat(),
                "delegate_id": delegate_id,
                "reason": reason,
                "approved_by": current_user,
            },
            compliance_relevant=True
        )

        return self._to_summary(updated) if updated else None

    def clear_ooo(
        self, tenant_id: str, approver_id: str, current_user: str
    ) -> Optional[ApproverSummary]:
        """Clear out-of-office status"""
        approver = self.repo.get_by_approver_id(tenant_id, approver_id)
        if not approver:
            return None

        old_ooo_details = {
            "ooo_until": approver.ooo_until.isoformat() if approver.ooo_until else None,
            "delegate_id": approver.delegate_id,
            "reason": approver.ooo_reason,
            "approved_by": approver.ooo_approved_by,
        }

        updated = self.repo.update(
            approver.id,
            {
                "is_ooo": False,
                "ooo_until": None,
                "delegate_id": None,
                "ooo_reason": None,
                "ooo_approved_by": None,
            },
            tenant_id
        )

        self.audit.log(
            action=AuditAction.APPROVER_OOO_SET,
            actor_user_id=current_user,
            target_type="Approver",
            target_id=approver_id,
            target_name=approver.name,
            details={"action": "cleared", "previous_ooo": old_ooo_details},
            compliance_relevant=True
        )

        return self._to_summary(updated) if updated else None

    def get_stats(self, tenant_id: str) -> ApproverStatsResponse:
        """Get approver statistics"""
        stats = self.repo.get_stats(tenant_id)
        return ApproverStatsResponse(**stats)

    @staticmethod
    def get_approver_types() -> List[ApproverTypeInfo]:
        """Get all approver types with descriptions"""
        return [
            ApproverTypeInfo(
                type=type_key,
                label=info["label"],
                description=info["description"]
            )
            for type_key, info in APPROVER_TYPE_INFO.items()
        ]

    # ============== Private Transform Methods ==============

    def _to_summary(self, approver) -> ApproverSummary:
        return ApproverSummary(
            id=approver.id,
            approver_id=approver.approver_id,
            name=approver.name,
            email=approver.email,
            approver_type=approver.approver_type,
            department=approver.department,
            status=approver.status,
            is_available=approver.is_available,
            is_ooo=approver.is_ooo,
            ooo_until=approver.ooo_until,
            delegate_id=approver.delegate_id,
            ooo_reason=approver.ooo_reason,
            ooo_approved_by=approver.ooo_approved_by,
            avg_response_hours=approver.avg_response_hours or 0.0,
            approval_rate=approver.approval_rate or 0.0,
            current_queue_size=approver.current_queue_size or 0,
            created_at=approver.created_at,
            updated_at=approver.updated_at,
        )

    def _to_detail(self, approver) -> ApproverDetailResponse:
        return ApproverDetailResponse(
            id=approver.id,
            approver_id=approver.approver_id,
            name=approver.name,
            email=approver.email,
            approver_type=approver.approver_type,
            department=approver.department,
            status=approver.status,
            is_available=approver.is_available,
            is_ooo=approver.is_ooo,
            ooo_until=approver.ooo_until,
            delegate_id=approver.delegate_id,
            ooo_reason=approver.ooo_reason,
            ooo_approved_by=approver.ooo_approved_by,
            avg_response_hours=approver.avg_response_hours or 0.0,
            approval_rate=approver.approval_rate or 0.0,
            current_queue_size=approver.current_queue_size or 0,
            created_at=approver.created_at,
            updated_at=approver.updated_at,
            process_scope=approver.process_scope or [],
            system_scope=approver.system_scope or [],
            job_title=approver.job_title,
            is_active=approver.is_active,
        )
