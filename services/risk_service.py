"""
Risk Service
Business logic for Risk and Violation management
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from repositories.risk_repository import RiskViolationRepository, RiskRuleRepository
from api.schemas.risk import (
    ViolationCreate, ViolationUpdate, ViolationFilters,
    ViolationSummary, ViolationDetailResponse, ViolationResponse,
    PaginatedViolationsResponse, ViolationStatsResponse,
    SodRuleCreate, SodRuleUpdate,
    SodRuleSummary, SodRuleDetailResponse, PaginatedSodRulesResponse,
    RiskAnalysisResult, RoleSimulationResult
)
from audit.logger import AuditLogger


class RiskService:
    """
    Service layer for Risk management.
    Handles business logic, validation, and audit logging.
    """

    def __init__(self, db: Session):
        self.db = db
        self.violation_repo = RiskViolationRepository(db)
        self.rule_repo = RiskRuleRepository(db)
        self.audit = AuditLogger()

    # ============== Violation Operations ==============

    def list_violations(
        self,
        tenant_id: str,
        filters: ViolationFilters,
        limit: int = 100,
        offset: int = 0
    ) -> PaginatedViolationsResponse:
        """List violations with pagination and filters"""
        violations, total = self.violation_repo.get_violations(
            tenant_id=tenant_id,
            search=filters.search,
            status=filters.status.value if filters.status else None,
            severity=filters.severity.value if filters.severity else None,
            violation_type=filters.violation_type.value if filters.violation_type else None,
            user_id=filters.user_id,
            rule_id=filters.rule_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            skip=offset,
            limit=limit
        )

        items = [self._to_violation_summary(v) for v in violations]

        return PaginatedViolationsResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total
        )

    def get_violation(
        self,
        tenant_id: str,
        violation_id: str
    ) -> Optional[ViolationDetailResponse]:
        """Get detailed violation information"""
        violation = self.violation_repo.get_violation_by_id(tenant_id, violation_id)
        if not violation:
            return None
        return self._to_violation_detail(violation)

    def create_violation(
        self,
        tenant_id: str,
        data: ViolationCreate,
        created_by: str
    ) -> ViolationResponse:
        """Create a new violation"""
        violation_data = {
            "user_external_id": data.user_id,
            "rule_id": data.rule_id or "MANUAL",
            "rule_name": data.title,
            "rule_type": data.violation_type.value,
            "severity": data.severity.value,
            "risk_category": data.violation_type.value,
            "conflicting_functions": data.conflicting_roles,
            "conflicting_entitlements": data.conflicting_permissions,
            "business_impact": data.description,
            "affected_systems": [data.source_system] if data.source_system else ["SAP"],
            "detected_by": created_by
        }

        violation = self.violation_repo.create_violation(tenant_id, violation_data)

        self.audit.log_action(
            action="violation.created",
            resource_type="violation",
            resource_id=violation.violation_id,
            tenant_id=tenant_id,
            user_id=created_by,
            details={"user_id": data.user_id, "type": data.violation_type.value}
        )

        return self._to_violation_response(violation)

    def update_violation(
        self,
        tenant_id: str,
        violation_id: str,
        data: ViolationUpdate,
        updated_by: str
    ) -> Optional[ViolationResponse]:
        """Update a violation status/mitigation"""
        update_data = {}

        if data.status:
            update_data["status"] = data.status.value
            if data.status.value in ["mitigated", "closed", "accepted"]:
                update_data["resolved_at"] = datetime.utcnow()
                update_data["resolved_by"] = updated_by

        if data.severity:
            update_data["severity"] = data.severity.value

        if data.mitigation_notes:
            update_data["resolution_notes"] = data.mitigation_notes

        if data.reviewer_id:
            update_data["reviewed_by"] = data.reviewer_id
            update_data["reviewed_at"] = datetime.utcnow()

        if not update_data:
            return None

        violation = self.violation_repo.update_violation(tenant_id, violation_id, update_data)
        if not violation:
            return None

        self.audit.log_action(
            action="violation.updated",
            resource_type="violation",
            resource_id=violation_id,
            tenant_id=tenant_id,
            user_id=updated_by,
            details={"updated_fields": list(update_data.keys())}
        )

        return self._to_violation_response(violation)

    def get_violation_stats(self, tenant_id: str) -> ViolationStatsResponse:
        """Get violation statistics"""
        stats = self.violation_repo.get_violation_stats(tenant_id)
        return ViolationStatsResponse(
            total_violations=stats["total_violations"],
            open_violations=stats["open_violations"],
            critical_violations=stats["critical_violations"],
            high_violations=stats["high_violations"],
            mitigated_last_30_days=stats["mitigated_last_30_days"],
            by_type=stats["by_type"],
            by_severity=stats["by_severity"],
            by_status=stats["by_status"],
            trend=[]  # Would need time-series data
        )

    def get_user_violations(
        self,
        tenant_id: str,
        user_id: str,
        status: Optional[str] = None
    ) -> List[ViolationSummary]:
        """Get violations for a specific user"""
        violations = self.violation_repo.get_user_violations(tenant_id, user_id, status)
        return [self._to_violation_summary(v) for v in violations]

    # ============== Rule Operations ==============

    def list_rules(
        self,
        tenant_id: str,
        search: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> PaginatedSodRulesResponse:
        """List SoD rules"""
        rules, total = self.rule_repo.get_rules(
            tenant_id=tenant_id,
            search=search,
            category=category,
            severity=severity,
            is_enabled=is_enabled,
            skip=offset,
            limit=limit
        )

        items = [self._to_rule_summary(r) for r in rules]

        return PaginatedSodRulesResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total
        )

    def get_rule(
        self,
        tenant_id: str,
        rule_id: str
    ) -> Optional[SodRuleDetailResponse]:
        """Get detailed rule information"""
        rule = self.rule_repo.get_rule_by_id(tenant_id, rule_id)
        if not rule:
            return None
        return self._to_rule_detail(rule)

    def create_rule(
        self,
        tenant_id: str,
        data: SodRuleCreate,
        created_by: str
    ) -> SodRuleSummary:
        """Create a new SoD rule"""
        rule_data = {
            "rule_id": data.rule_id,
            "name": data.rule_name,
            "description": data.description,
            "rule_type": "sod",
            "severity": data.severity.value,
            "risk_category": data.category,
            "rule_definition": {
                "function1": data.function1,
                "function2": data.function2,
                "function1_transactions": data.function1_transactions,
                "function2_transactions": data.function2_transactions
            },
            "mitigation_controls": data.mitigation_controls,
            "applies_to_systems": [data.source_system] if data.source_system else ["SAP"],
            "is_enabled": True,
            "created_by": created_by
        }

        rule = self.rule_repo.create_rule(tenant_id, rule_data)

        self.audit.log_action(
            action="sod_rule.created",
            resource_type="sod_rule",
            resource_id=rule.rule_id,
            tenant_id=tenant_id,
            user_id=created_by,
            details={"rule_name": data.rule_name, "category": data.category}
        )

        return self._to_rule_summary(rule)

    def update_rule(
        self,
        tenant_id: str,
        rule_id: str,
        data: SodRuleUpdate,
        updated_by: str
    ) -> Optional[SodRuleSummary]:
        """Update a SoD rule"""
        update_data = {}

        if data.rule_name:
            update_data["name"] = data.rule_name
        if data.description:
            update_data["description"] = data.description
        if data.category:
            update_data["risk_category"] = data.category
        if data.severity:
            update_data["severity"] = data.severity.value
        if data.status:
            update_data["is_enabled"] = data.status.value == "active"
        if data.mitigation_controls is not None:
            update_data["mitigation_controls"] = data.mitigation_controls

        if not update_data:
            return None

        update_data["last_modified_by"] = updated_by

        rule = self.rule_repo.update_rule(tenant_id, rule_id, update_data)
        if not rule:
            return None

        self.audit.log_action(
            action="sod_rule.updated",
            resource_type="sod_rule",
            resource_id=rule_id,
            tenant_id=tenant_id,
            user_id=updated_by,
            details={"updated_fields": list(update_data.keys())}
        )

        return self._to_rule_summary(rule)

    def delete_rule(
        self,
        tenant_id: str,
        rule_id: str,
        deleted_by: str
    ) -> bool:
        """Delete a SoD rule"""
        result = self.rule_repo.delete_rule(tenant_id, rule_id)

        if result:
            self.audit.log_action(
                action="sod_rule.deleted",
                resource_type="sod_rule",
                resource_id=rule_id,
                tenant_id=tenant_id,
                user_id=deleted_by
            )

        return result

    def get_rule_categories(self, tenant_id: str) -> List[str]:
        """Get available rule categories"""
        return self.rule_repo.get_categories(tenant_id)

    # ============== Analysis Operations ==============

    def analyze_user_risk(
        self,
        tenant_id: str,
        user_id: str,
        include_details: bool = True
    ) -> RiskAnalysisResult:
        """Analyze risk for a user"""
        violations = self.violation_repo.get_user_violations(tenant_id, user_id, "open")

        # Calculate risk score
        risk_score = 0.0
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for v in violations:
            sev = v.severity.value if v.severity else "medium"
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

            # Score weights
            if sev == "critical":
                risk_score += 25
            elif sev == "high":
                risk_score += 15
            elif sev == "medium":
                risk_score += 8
            else:
                risk_score += 3

        risk_score = min(risk_score, 100)

        # Determine risk level
        if risk_score >= 80:
            risk_level = "critical"
        elif risk_score >= 60:
            risk_level = "high"
        elif risk_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        violation_summaries = []
        if include_details:
            violation_summaries = [self._to_violation_summary(v) for v in violations[:20]]

        return RiskAnalysisResult(
            user_id=user_id,
            risk_score=round(risk_score, 1),
            risk_level=risk_level,
            total_violations=len(violations),
            violations_by_severity=severity_counts,
            violations=violation_summaries,
            sensitive_access_count=0,
            high_risk_roles=[],
            analysis_timestamp=datetime.utcnow()
        )

    def simulate_role_assignment(
        self,
        tenant_id: str,
        user_id: str,
        role_ids: List[str],
        include_current: bool = True
    ) -> RoleSimulationResult:
        """Simulate adding roles to a user and predict risk impact"""
        # Get current risk
        current_analysis = self.analyze_user_risk(tenant_id, user_id, include_details=False)

        # Simulate new violations (simplified - would need full role analysis)
        # In production, this would check SoD rules against the new role combinations
        projected_score = current_analysis.risk_score + (len(role_ids) * 5)
        projected_score = min(projected_score, 100)

        risk_delta = projected_score - current_analysis.risk_score

        # Recommendation logic
        if risk_delta > 20:
            recommendation = "DENY"
            compliance_impact = "High Risk - Requires Exception Approval"
        elif risk_delta > 10:
            recommendation = "REVIEW_REQUIRED"
            compliance_impact = "Medium Risk - Manager Approval Required"
        else:
            recommendation = "APPROVE"
            compliance_impact = "Low Risk - Auto-Approve Eligible"

        return RoleSimulationResult(
            user_id=user_id,
            current_risk_score=current_analysis.risk_score,
            projected_risk_score=round(projected_score, 1),
            new_violations=[],  # Would be populated by SoD check
            recommendation=recommendation,
            risk_delta=round(risk_delta, 1),
            affected_users=1,
            compliance_impact=compliance_impact,
            insights=[
                f"Adding {len(role_ids)} role(s) would increase risk score by {round(risk_delta, 1)} points",
                f"Current risk level: {current_analysis.risk_level}"
            ]
        )

    # ============== Private Methods ==============

    def _to_violation_summary(self, violation) -> ViolationSummary:
        """Convert violation to summary"""
        return ViolationSummary(
            id=violation.id,
            violation_id=violation.violation_id,
            user_id=violation.user_external_id,
            user_name=violation.username,
            department=None,
            rule_id=violation.rule_id,
            rule_name=violation.rule_name,
            violation_type=violation.rule_type or "sod_conflict",
            severity=violation.severity.value if violation.severity else "medium",
            status=violation.status.value if violation.status else "open",
            title=violation.rule_name,
            source_system="SAP",
            detected_at=violation.detected_at or violation.created_at,
            updated_at=violation.updated_at
        )

    def _to_violation_detail(self, violation) -> ViolationDetailResponse:
        """Convert violation to detail response"""
        return ViolationDetailResponse(
            id=violation.id,
            violation_id=violation.violation_id,
            user_id=violation.user_external_id,
            user_name=violation.username,
            department=None,
            rule_id=violation.rule_id,
            rule_name=violation.rule_name,
            violation_type=violation.rule_type or "sod_conflict",
            severity=violation.severity.value if violation.severity else "medium",
            status=violation.status.value if violation.status else "open",
            title=violation.rule_name,
            description=violation.business_impact,
            conflicting_roles=violation.conflicting_functions or [],
            conflicting_permissions=violation.conflicting_entitlements or [],
            source_system="SAP",
            mitigation_notes=violation.resolution_notes,
            reviewer_id=violation.reviewed_by,
            resolution_date=violation.resolved_at,
            detected_at=violation.detected_at or violation.created_at,
            updated_at=violation.updated_at
        )

    def _to_violation_response(self, violation) -> ViolationResponse:
        """Convert violation to response"""
        return ViolationResponse(
            id=violation.id,
            violation_id=violation.violation_id,
            user_id=violation.user_external_id,
            violation_type=violation.rule_type or "sod_conflict",
            severity=violation.severity.value if violation.severity else "medium",
            status=violation.status.value if violation.status else "open",
            title=violation.rule_name,
            detected_at=violation.detected_at or violation.created_at
        )

    def _to_rule_summary(self, rule) -> SodRuleSummary:
        """Convert rule to summary"""
        rule_def = rule.rule_definition or {}
        return SodRuleSummary(
            id=rule.id,
            rule_id=rule.rule_id,
            rule_name=rule.name,
            description=rule.description,
            category=rule.risk_category or "General",
            severity=rule.severity.value if rule.severity else "high",
            status="active" if rule.is_enabled else "inactive",
            function1=rule_def.get("function1", ""),
            function2=rule_def.get("function2", ""),
            violation_count=rule.violation_count or 0,
            source_system="SAP",
            is_custom=False,
            created_at=rule.created_at
        )

    def _to_rule_detail(self, rule) -> SodRuleDetailResponse:
        """Convert rule to detail response"""
        rule_def = rule.rule_definition or {}
        return SodRuleDetailResponse(
            id=rule.id,
            rule_id=rule.rule_id,
            rule_name=rule.name,
            description=rule.description,
            category=rule.risk_category or "General",
            severity=rule.severity.value if rule.severity else "high",
            status="active" if rule.is_enabled else "inactive",
            function1=rule_def.get("function1", ""),
            function2=rule_def.get("function2", ""),
            function1_transactions=rule_def.get("function1_transactions", []),
            function2_transactions=rule_def.get("function2_transactions", []),
            violation_count=rule.violation_count or 0,
            source_system="SAP",
            business_process=None,
            mitigation_controls=rule.mitigation_controls or [],
            is_custom=False,
            last_run=rule.last_triggered_at,
            created_by=rule.created_by,
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )
