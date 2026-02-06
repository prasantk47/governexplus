"""
Risk Repository
Database operations for Risk/Violation management with tenant isolation
"""

from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
import uuid

from .base import BaseRepository
from db.models.risk import RiskViolation, RiskRuleModel, MitigationControl, ViolationStatus, RiskSeverityLevel


class RiskViolationRepository(BaseRepository[RiskViolation]):
    """
    Repository for RiskViolation CRUD operations.
    All operations are tenant-isolated.
    """

    def __init__(self, db: Session):
        super().__init__(db, RiskViolation)

    def get_violations(
        self,
        tenant_id: str,
        search: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        violation_type: Optional[str] = None,
        user_id: Optional[str] = None,
        rule_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[RiskViolation], int]:
        """Get paginated list of violations with filters"""
        query = self._get_base_query(tenant_id)

        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    RiskViolation.violation_id.ilike(search_term),
                    RiskViolation.rule_name.ilike(search_term),
                    RiskViolation.user_external_id.ilike(search_term),
                    RiskViolation.username.ilike(search_term)
                )
            )

        # Status filter
        if status:
            try:
                status_enum = ViolationStatus(status)
                query = query.filter(RiskViolation.status == status_enum)
            except ValueError:
                pass

        # Severity filter
        if severity:
            try:
                severity_enum = RiskSeverityLevel(severity)
                query = query.filter(RiskViolation.severity == severity_enum)
            except ValueError:
                pass

        # Type filter
        if violation_type:
            query = query.filter(RiskViolation.rule_type == violation_type)

        # User filter
        if user_id:
            query = query.filter(RiskViolation.user_external_id == user_id)

        # Rule filter
        if rule_id:
            query = query.filter(RiskViolation.rule_id == rule_id)

        # Date range
        if date_from:
            query = query.filter(RiskViolation.detected_at >= date_from)
        if date_to:
            query = query.filter(RiskViolation.detected_at <= date_to)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        violations = query.order_by(
            RiskViolation.detected_at.desc()
        ).offset(skip).limit(limit).all()

        return violations, total

    def get_violation_by_id(
        self,
        tenant_id: str,
        violation_id: str
    ) -> Optional[RiskViolation]:
        """Get violation by violation_id"""
        return self._get_base_query(tenant_id).filter(
            RiskViolation.violation_id == violation_id
        ).first()

    def create_violation(
        self,
        tenant_id: str,
        violation_data: dict
    ) -> RiskViolation:
        """Create a new violation"""
        violation_data['tenant_id'] = tenant_id
        if 'violation_id' not in violation_data:
            violation_data['violation_id'] = f"VIO-{uuid.uuid4().hex[:8].upper()}"
        violation_data['status'] = ViolationStatus.OPEN
        violation_data['detected_at'] = datetime.utcnow()

        violation = RiskViolation(**violation_data)
        self.db.add(violation)
        self.db.commit()
        self.db.refresh(violation)
        return violation

    def update_violation(
        self,
        tenant_id: str,
        violation_id: str,
        violation_data: dict
    ) -> Optional[RiskViolation]:
        """Update violation by violation_id"""
        violation = self.get_violation_by_id(tenant_id, violation_id)
        if not violation:
            return None

        for key, value in violation_data.items():
            if hasattr(violation, key) and value is not None:
                setattr(violation, key, value)

        self.db.commit()
        self.db.refresh(violation)
        return violation

    def get_user_violations(
        self,
        tenant_id: str,
        user_id: str,
        status: Optional[str] = None
    ) -> List[RiskViolation]:
        """Get violations for a specific user"""
        query = self._get_base_query(tenant_id).filter(
            RiskViolation.user_external_id == user_id
        )

        if status:
            try:
                status_enum = ViolationStatus(status)
                query = query.filter(RiskViolation.status == status_enum)
            except ValueError:
                pass

        return query.order_by(RiskViolation.detected_at.desc()).all()

    def get_violation_stats(self, tenant_id: str) -> dict:
        """Get violation statistics"""
        base_query = self._get_base_query(tenant_id)

        total = base_query.count()
        open_count = base_query.filter(
            RiskViolation.status == ViolationStatus.OPEN
        ).count()

        # By severity
        severity_counts = self.db.query(
            RiskViolation.severity,
            func.count(RiskViolation.id).label('count')
        ).filter(
            RiskViolation.tenant_id == tenant_id,
            RiskViolation.status == ViolationStatus.OPEN
        ).group_by(RiskViolation.severity).all()

        # By type
        type_counts = self.db.query(
            RiskViolation.rule_type,
            func.count(RiskViolation.id).label('count')
        ).filter(
            RiskViolation.tenant_id == tenant_id,
            RiskViolation.status == ViolationStatus.OPEN
        ).group_by(RiskViolation.rule_type).all()

        # By status
        status_counts = self.db.query(
            RiskViolation.status,
            func.count(RiskViolation.id).label('count')
        ).filter(
            RiskViolation.tenant_id == tenant_id
        ).group_by(RiskViolation.status).all()

        # Mitigated in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        mitigated_30d = base_query.filter(
            RiskViolation.status == ViolationStatus.MITIGATED,
            RiskViolation.resolved_at >= thirty_days_ago
        ).count()

        critical_open = base_query.filter(
            RiskViolation.status == ViolationStatus.OPEN,
            RiskViolation.severity == RiskSeverityLevel.CRITICAL
        ).count()

        high_open = base_query.filter(
            RiskViolation.status == ViolationStatus.OPEN,
            RiskViolation.severity == RiskSeverityLevel.HIGH
        ).count()

        return {
            "total_violations": total,
            "open_violations": open_count,
            "critical_violations": critical_open,
            "high_violations": high_open,
            "mitigated_last_30_days": mitigated_30d,
            "by_severity": {s.value if s else 'unknown': c for s, c in severity_counts},
            "by_type": {t or 'unknown': c for t, c in type_counts},
            "by_status": {s.value if s else 'unknown': c for s, c in status_counts}
        }


class RiskRuleRepository(BaseRepository[RiskRuleModel]):
    """Repository for SoD Rule CRUD operations"""

    def __init__(self, db: Session):
        super().__init__(db, RiskRuleModel)

    def get_rules(
        self,
        tenant_id: str,
        search: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[RiskRuleModel], int]:
        """Get paginated list of rules"""
        query = self._get_base_query(tenant_id)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    RiskRuleModel.rule_id.ilike(search_term),
                    RiskRuleModel.name.ilike(search_term),
                    RiskRuleModel.description.ilike(search_term)
                )
            )

        if category:
            query = query.filter(RiskRuleModel.risk_category == category)

        if severity:
            try:
                severity_enum = RiskSeverityLevel(severity)
                query = query.filter(RiskRuleModel.severity == severity_enum)
            except ValueError:
                pass

        if is_enabled is not None:
            query = query.filter(RiskRuleModel.is_enabled == is_enabled)

        total = query.count()
        rules = query.order_by(RiskRuleModel.name).offset(skip).limit(limit).all()

        return rules, total

    def get_rule_by_id(
        self,
        tenant_id: str,
        rule_id: str
    ) -> Optional[RiskRuleModel]:
        """Get rule by rule_id"""
        return self._get_base_query(tenant_id).filter(
            RiskRuleModel.rule_id == rule_id
        ).first()

    def create_rule(
        self,
        tenant_id: str,
        rule_data: dict
    ) -> RiskRuleModel:
        """Create a new rule"""
        rule_data['tenant_id'] = tenant_id

        rule = RiskRuleModel(**rule_data)
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def update_rule(
        self,
        tenant_id: str,
        rule_id: str,
        rule_data: dict
    ) -> Optional[RiskRuleModel]:
        """Update rule by rule_id"""
        rule = self.get_rule_by_id(tenant_id, rule_id)
        if not rule:
            return None

        for key, value in rule_data.items():
            if hasattr(rule, key) and value is not None:
                setattr(rule, key, value)

        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(
        self,
        tenant_id: str,
        rule_id: str
    ) -> bool:
        """Delete rule by rule_id"""
        rule = self.get_rule_by_id(tenant_id, rule_id)
        if not rule:
            return False

        self.db.delete(rule)
        self.db.commit()
        return True

    def get_rule_stats(self, tenant_id: str) -> dict:
        """Get rule statistics"""
        base_query = self._get_base_query(tenant_id)

        total = base_query.count()
        active = base_query.filter(RiskRuleModel.is_enabled == True).count()

        # By category
        category_counts = self.db.query(
            RiskRuleModel.risk_category,
            func.count(RiskRuleModel.id).label('count')
        ).filter(
            RiskRuleModel.tenant_id == tenant_id
        ).group_by(RiskRuleModel.risk_category).all()

        # Total violations across rules
        total_violations = self.db.query(
            func.sum(RiskRuleModel.violation_count)
        ).filter(
            RiskRuleModel.tenant_id == tenant_id
        ).scalar() or 0

        return {
            "total_rules": total,
            "active_rules": active,
            "total_violations": int(total_violations),
            "by_category": {c or 'Unknown': count for c, count in category_counts}
        }

    def get_categories(self, tenant_id: str) -> List[str]:
        """Get list of unique categories"""
        results = self.db.query(RiskRuleModel.risk_category).filter(
            RiskRuleModel.tenant_id == tenant_id,
            RiskRuleModel.risk_category.isnot(None)
        ).distinct().all()
        return [r[0] for r in results if r[0]]
