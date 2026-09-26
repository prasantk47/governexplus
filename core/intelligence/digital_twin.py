"""
GRC Digital Twin
Builds a live connected model of the organization:
People -> Roles -> Permissions -> Controls -> Risks -> Findings -> Remediation
Then answers questions by reasoning over the graph.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func


class GRCDigitalTwin:
    """Live model of the organization's GRC state."""

    def __init__(self, tenant_id: str, db: Session):
        self.tenant_id = tenant_id
        self.db = db

    def build_snapshot(self) -> dict:
        """Build a point-in-time snapshot of the full GRC state."""
        return {
            "snapshot_id": f"TWIN-{uuid.uuid4().hex[:8].upper()}",
            "generated_at": datetime.utcnow().isoformat(),
            "tenant_id": self.tenant_id,
            "people": self._snapshot_people(),
            "roles": self._snapshot_roles(),
            "risks": self._snapshot_risks(),
            "controls": self._snapshot_controls(),
            "findings": self._snapshot_findings(),
            "violations": self._snapshot_violations(),
            "graph_stats": self._compute_graph_stats(),
        }

    def _snapshot_people(self) -> dict:
        from db.models.user import User, UserRole
        total = (
            self.db.query(func.count(User.id))
            .filter_by(tenant_id=self.tenant_id)
            .scalar()
            or 0
        )
        active = (
            self.db.query(func.count(User.id))
            .filter(User.tenant_id == self.tenant_id, User.status == "active")
            .scalar()
            or 0
        )
        assignments = (
            self.db.query(func.count(UserRole.id))
            .filter_by(tenant_id=self.tenant_id, is_active=True)
            .scalar()
            or 0
        )
        return {"total": total, "active": active, "role_assignments": assignments}

    def _snapshot_roles(self) -> dict:
        from db.models.user import Role
        roles = (
            self.db.query(Role)
            .filter_by(tenant_id=self.tenant_id, is_active=True)
            .all()
        )
        by_type = defaultdict(int)
        by_risk = defaultdict(int)
        for r in roles:
            by_type[r.role_type or "single"] += 1
            by_risk[r.risk_level or "medium"] += 1
        return {
            "total": len(roles),
            "by_type": dict(by_type),
            "by_risk_level": dict(by_risk),
        }

    def _snapshot_risks(self) -> dict:
        from db.models.risk_management import EnterpriseRisk
        risks = (
            self.db.query(EnterpriseRisk)
            .filter_by(tenant_id=self.tenant_id, is_active=True)
            .all()
        )
        if not risks:
            return {"total": 0, "avg_inherent": 0, "avg_residual": 0, "by_category": {}}
        by_cat = defaultdict(int)
        for r in risks:
            cat = r.category.value if hasattr(r.category, "value") else str(r.category)
            by_cat[cat] += 1
        return {
            "total": len(risks),
            "avg_inherent": round(
                sum(r.inherent_score or 0 for r in risks) / len(risks), 1
            ),
            "avg_residual": round(
                sum(r.residual_score or r.inherent_score or 0 for r in risks) / len(risks), 1
            ),
            "by_category": dict(by_cat),
        }

    def _snapshot_controls(self) -> dict:
        from db.models.process_control import ProcessControl, ControlDeficiency
        controls = (
            self.db.query(func.count(ProcessControl.id))
            .filter_by(tenant_id=self.tenant_id, is_active=True)
            .scalar()
            or 0
        )
        open_defs = (
            self.db.query(func.count(ControlDeficiency.id))
            .filter(
                ControlDeficiency.tenant_id == self.tenant_id,
                ControlDeficiency.status.in_(["open", "in_remediation"]),
            )
            .scalar()
            or 0
        )
        return {
            "total": controls,
            "open_deficiencies": open_defs,
            "effectiveness_pct": round(
                ((controls - open_defs) / max(controls, 1)) * 100
            ),
        }

    def _snapshot_findings(self) -> dict:
        from db.models.audit_management import AuditFinding, AuditManagementAction
        findings = (
            self.db.query(AuditFinding).filter_by(tenant_id=self.tenant_id).all()
        )
        by_severity = defaultdict(int)
        by_status = defaultdict(int)
        for f in findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            stat = f.status.value if hasattr(f.status, "value") else str(f.status)
            by_severity[sev] += 1
            by_status[stat] += 1
        overdue_actions = (
            self.db.query(func.count(AuditManagementAction.id))
            .filter(
                AuditManagementAction.tenant_id == self.tenant_id,
                AuditManagementAction.status.in_(["open", "in_progress"]),
                AuditManagementAction.due_date < datetime.utcnow(),
            )
            .scalar()
            or 0
        )
        return {
            "total": len(findings),
            "by_severity": dict(by_severity),
            "by_status": dict(by_status),
            "overdue_actions": overdue_actions,
        }

    def _snapshot_violations(self) -> dict:
        from db.models.risk import RiskViolation, ViolationStatus
        total = (
            self.db.query(func.count(RiskViolation.id))
            .filter_by(tenant_id=self.tenant_id)
            .scalar()
            or 0
        )
        open_v = (
            self.db.query(func.count(RiskViolation.id))
            .filter(
                RiskViolation.tenant_id == self.tenant_id,
                RiskViolation.status == ViolationStatus.OPEN,
            )
            .scalar()
            or 0
        )
        mitigated = (
            self.db.query(func.count(RiskViolation.id))
            .filter(
                RiskViolation.tenant_id == self.tenant_id,
                RiskViolation.is_mitigated == True,
            )
            .scalar()
            or 0
        )
        return {"total": total, "open": open_v, "mitigated": mitigated}

    def _compute_graph_stats(self) -> dict:
        """Compute cross-module connection statistics."""
        from db.models.risk_management import EnterpriseRisk
        from db.models.audit_management import AuditFinding

        # Risks with controls / findings
        risks = (
            self.db.query(EnterpriseRisk)
            .filter_by(tenant_id=self.tenant_id, is_active=True)
            .all()
        )
        risks_with_controls = sum(1 for r in risks if r.related_control_ids)
        risks_with_findings = sum(1 for r in risks if r.related_finding_ids)

        # Findings linked to risks
        findings_with_risk = (
            self.db.query(func.count(AuditFinding.id))
            .filter(
                AuditFinding.tenant_id == self.tenant_id,
                AuditFinding.risk_id.isnot(None),
            )
            .scalar()
            or 0
        )

        # Findings linked to controls
        findings_with_control = (
            self.db.query(func.count(AuditFinding.id))
            .filter(
                AuditFinding.tenant_id == self.tenant_id,
                AuditFinding.control_id.isnot(None),
            )
            .scalar()
            or 0
        )

        return {
            "risks_with_controls": risks_with_controls,
            "risks_without_controls": len(risks) - risks_with_controls,
            "risks_with_findings": risks_with_findings,
            "findings_linked_to_risk": findings_with_risk,
            "findings_linked_to_control": findings_with_control,
            "integration_score": round(
                (risks_with_controls + findings_with_risk + findings_with_control)
                / max(len(risks) + findings_with_risk + findings_with_control, 1)
                * 100
            ),
        }

    def find_root_causes(self) -> dict:
        """AI: Group findings by underlying root causes."""
        from db.models.audit_management import AuditFinding
        findings = (
            self.db.query(AuditFinding)
            .filter(
                AuditFinding.tenant_id == self.tenant_id,
                AuditFinding.status.notin_(["closed"]),
            )
            .all()
        )

        # Group by linked risk (shared root cause)
        by_risk = defaultdict(list)
        unlinked = []
        for f in findings:
            if f.risk_id:
                by_risk[f.risk_id].append(f)
            else:
                unlinked.append(f)

        root_causes = []
        for risk_id, group in by_risk.items():
            root_causes.append({
                "root_cause_type": "shared_risk",
                "risk_id": risk_id,
                "finding_count": len(group),
                "findings": [
                    {
                        "finding_id": f.finding_id,
                        "title": f.title,
                        "severity": (
                            f.severity.value
                            if hasattr(f.severity, "value")
                            else str(f.severity)
                        ),
                    }
                    for f in group
                ],
                "insight": f"{len(group)} findings trace to the same underlying risk",
            })

        return {
            "total_open_findings": len(findings),
            "distinct_root_causes": len(root_causes),
            "root_causes": root_causes,
            "unlinked_findings": len(unlinked),
            "insight": (
                f"{len(findings)} open findings represent {len(root_causes)} distinct "
                f"root causes. {len(unlinked)} findings are not linked to any enterprise risk."
            ),
        }

    def what_if_user_move(self, user_id: str, new_department: str) -> dict:
        """Simulate: what happens if a user moves departments?"""
        from db.models.user import User, UserRole, Role

        user = (
            self.db.query(User)
            .filter_by(tenant_id=self.tenant_id, user_id=user_id)
            .first()
        )
        if not user:
            return {"error": "User not found"}

        current_roles = (
            self.db.query(UserRole)
            .filter_by(tenant_id=self.tenant_id, user_id=user.id, is_active=True)
            .all()
        )
        role_ids = [ur.role_id for ur in current_roles]
        roles = (
            self.db.query(Role).filter(Role.id.in_(role_ids)).all()
            if role_ids
            else []
        )

        # Determine which roles are department-specific
        dept_roles = [
            r
            for r in roles
            if r.description
            and user.department
            and user.department.lower() in (r.description or "").lower()
        ]
        keep_roles = [r for r in roles if r not in dept_roles]

        return {
            "user_id": user_id,
            "full_name": user.full_name,
            "current_department": user.department,
            "new_department": new_department,
            "current_roles": [
                {"role_id": r.role_id, "role_name": r.role_name} for r in roles
            ],
            "roles_to_review": [
                {
                    "role_id": r.role_id,
                    "role_name": r.role_name,
                    "reason": "Department-specific role",
                }
                for r in dept_roles
            ],
            "roles_to_keep": [
                {"role_id": r.role_id, "role_name": r.role_name} for r in keep_roles
            ],
            "recommended_actions": [
                (
                    f"Remove {len(dept_roles)} department-specific roles"
                    if dept_roles
                    else "No role removals needed"
                ),
                f"Request new roles for {new_department} department",
                "Run SoD analysis after role changes",
                "Update organizational assignment in SAP",
            ],
            "risk_assessment": (
                "Review required"
                if dept_roles
                else "Low risk — no department-specific roles detected"
            ),
        }

    def predict_repeat_findings(self) -> list:
        """Predict which findings are likely to recur based on patterns."""
        from db.models.audit_management import AuditFinding

        findings = (
            self.db.query(AuditFinding)
            .filter_by(tenant_id=self.tenant_id)
            .order_by(AuditFinding.created_at.desc())
            .all()
        )

        # Group by control_id to find controls with recurring issues
        by_control = defaultdict(list)
        for f in findings:
            if f.control_id:
                by_control[f.control_id].append(f)

        predictions = []
        for ctrl_id, ctrl_findings in by_control.items():
            if len(ctrl_findings) >= 2:
                predictions.append({
                    "control_id": ctrl_id,
                    "finding_count": len(ctrl_findings),
                    "latest_finding": ctrl_findings[0].finding_id,
                    "latest_severity": (
                        ctrl_findings[0].severity.value
                        if hasattr(ctrl_findings[0].severity, "value")
                        else str(ctrl_findings[0].severity)
                    ),
                    "recurrence_risk": "high" if len(ctrl_findings) >= 3 else "medium",
                    "recommendation": (
                        "Root cause not addressed — systemic control weakness likely"
                    ),
                })

        return sorted(predictions, key=lambda p: p["finding_count"], reverse=True)
