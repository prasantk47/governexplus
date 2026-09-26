"""
GRC Intelligence API Router — AI-native layer for the GovernexPlus Command Center.

This is the core differentiator: a single, self-contained router that queries
all four GRC pillars (Access Control, Process Control, Risk Management, Audit
Management) and exposes seven intelligence capabilities over HTTP.

All endpoints are authenticated via the shared get_current_user dependency
wired at include_router time in api/main.py.

Endpoints
---------
GET  /grc-intelligence/health          — GRC Health Score (0-100) across 4 pillars
GET  /grc-intelligence/attention       — Proactive attention items
POST /grc-intelligence/explain         — Plain-language explanation of any GRC object
POST /grc-intelligence/investigate     — Deep-dive why something is happening
POST /grc-intelligence/recommend       — Actionable fix recommendations
GET  /grc-intelligence/dashboard/{role}— Role-personalised dashboard view
POST /grc-intelligence/fix-preview     — Preview what a fix action would change
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func

from core.tenant import get_current_tenant
from db.database import db_manager

router = APIRouter(tags=["GRC Intelligence"])


# ---------------------------------------------------------------------------
# Tenant resolution — consistent with the existing per-tenant engine pattern
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    """Resolve current tenant from middleware context."""
    try:
        ctx = get_current_tenant()
        return ctx.tenant_id if ctx else "default"
    except Exception:
        return "default"


# ===========================================================================
# 1. GRC HEALTH SCORE
# ===========================================================================

@router.get(
    "/health",
    summary="GRC Health Score",
    description=(
        "Compute the overall GRC health score (0-100) from four weighted pillars: "
        "Access Control (30%), Process Control (25%), Risk Management (25%), "
        "and Audit Management (20%). Returns per-pillar breakdown and trend."
    ),
)
def get_grc_health(tenant_id: str = Depends(_get_tenant_id)) -> Dict[str, Any]:
    """Compute overall GRC health score (0-100) from all 4 pillars."""
    with db_manager.session_scope() as db:
        from db.models.risk import RiskViolation, ViolationStatus
        from db.models.process_control import (
            ProcessControl, ControlDeficiency, ControlTest,
        )
        from db.models.risk_management import EnterpriseRisk
        from db.models.audit_management import AuditFinding, AuditManagementAction

        # ── Access Control: each open violation costs 3 pts ─────────────────
        total_violations = (
            db.query(func.count(RiskViolation.id))
            .filter(RiskViolation.tenant_id == tenant_id)
            .scalar() or 0
        )
        open_violations = (
            db.query(func.count(RiskViolation.id))
            .filter(
                RiskViolation.tenant_id == tenant_id,
                RiskViolation.status == ViolationStatus.OPEN,
            )
            .scalar() or 0
        )
        ac_score = (
            max(0, 100 - (open_violations * 3)) if total_violations > 0 else 90
        )
        ac_score = min(100, ac_score)

        # ── Process Control: each serious deficiency costs 5 pts ─────────────
        total_controls = (
            db.query(func.count(ProcessControl.id))
            .filter(ProcessControl.tenant_id == tenant_id, ProcessControl.is_active.is_(True))
            .scalar() or 0
        )
        open_deficiencies = (
            db.query(func.count(ControlDeficiency.id))
            .filter(
                ControlDeficiency.tenant_id == tenant_id,
                ControlDeficiency.status.in_(["open", "in_remediation"]),
            )
            .scalar() or 0
        )
        pc_score = (
            max(0, 100 - (open_deficiencies * 5)) if total_controls > 0 else 90
        )
        pc_score = min(100, pc_score)

        # ── Risk Management: avg residual inverted ───────────────────────────
        risks = (
            db.query(EnterpriseRisk)
            .filter(EnterpriseRisk.tenant_id == tenant_id, EnterpriseRisk.is_active.is_(True))
            .all()
        )
        if risks:
            avg_residual = sum(
                (r.residual_score or r.inherent_score or 12.5) for r in risks
            ) / len(risks)
            rm_score = max(0, 100 - (avg_residual * 4))  # score 25 → 0 health
        else:
            avg_residual = 0.0
            rm_score = 90
        rm_score = min(100, rm_score)

        # ── Audit Management: open findings + overdue actions ────────────────
        total_findings = (
            db.query(func.count(AuditFinding.id))
            .filter(AuditFinding.tenant_id == tenant_id)
            .scalar() or 0
        )
        open_findings = (
            db.query(func.count(AuditFinding.id))
            .filter(
                AuditFinding.tenant_id == tenant_id,
                AuditFinding.status.notin_(["closed", "management_response_received"]),
            )
            .scalar() or 0
        )
        overdue_actions = (
            db.query(func.count(AuditManagementAction.id))
            .filter(
                AuditManagementAction.tenant_id == tenant_id,
                AuditManagementAction.status.in_(["open", "in_progress"]),
                AuditManagementAction.due_date < datetime.utcnow(),
            )
            .scalar() or 0
        )
        am_score = max(0, 100 - (open_findings * 4) - (overdue_actions * 6))
        am_score = min(100, am_score)

        # ── Weighted composite ───────────────────────────────────────────────
        overall = round(
            ac_score * 0.30
            + pc_score * 0.25
            + rm_score * 0.25
            + am_score * 0.20
        )

        return {
            "overall_score": overall,
            "trend": "stable",
            "pillars": {
                "access_control": {
                    "score": round(ac_score),
                    "label": "Access Risk",
                    "open_violations": open_violations,
                    "total_violations": total_violations,
                },
                "process_control": {
                    "score": round(pc_score),
                    "label": "Control Health",
                    "total_controls": total_controls,
                    "open_deficiencies": open_deficiencies,
                },
                "risk_management": {
                    "score": round(rm_score),
                    "label": "Enterprise Risk",
                    "total_risks": len(risks),
                    "avg_residual": round(avg_residual, 1),
                },
                "audit_management": {
                    "score": round(am_score),
                    "label": "Audit Status",
                    "total_findings": total_findings,
                    "open_findings": open_findings,
                    "overdue_actions": overdue_actions,
                },
            },
            "computed_at": datetime.utcnow().isoformat(),
        }


# ===========================================================================
# 2. ATTENTION ITEMS
# ===========================================================================

@router.get(
    "/attention",
    summary="Attention Items",
    description=(
        "Proactive list of items that need immediate attention, scanned from all "
        "four GRC pillars and returned in priority order."
    ),
)
def get_attention_items(tenant_id: str = Depends(_get_tenant_id)) -> Dict[str, Any]:
    """Return prioritised items that need immediate attention."""
    items: List[Dict[str, Any]] = []

    with db_manager.session_scope() as db:
        from db.models.risk import RiskViolation, ViolationStatus, RiskSeverityLevel
        from db.models.process_control import ControlDeficiency
        from db.models.risk_management import EnterpriseRisk
        from db.models.audit_management import AuditFinding, AuditManagementAction

        # ── Critical / High SoD violations ──────────────────────────────────
        critical_violations = (
            db.query(func.count(RiskViolation.id))
            .filter(
                RiskViolation.tenant_id == tenant_id,
                RiskViolation.status == ViolationStatus.OPEN,
                RiskViolation.severity.in_(
                    [RiskSeverityLevel.CRITICAL, RiskSeverityLevel.HIGH]
                ),
            )
            .scalar() or 0
        )
        if critical_violations > 0:
            s = "s" if critical_violations > 1 else ""
            items.append({
                "type": "critical",
                "module": "ac",
                "title": f"{critical_violations} critical access risk{s}",
                "description": (
                    f"{critical_violations} high/critical SoD conflict{s} need resolution"
                ),
                "action": "Review",
                "action_url": "/risk/violations",
                "priority": 1,
            })

        # ── Control failures (material weakness / significant deficiency) ────
        severe_defs = (
            db.query(ControlDeficiency)
            .filter(
                ControlDeficiency.tenant_id == tenant_id,
                ControlDeficiency.status.in_(["open", "in_remediation"]),
            )
            .all()
        )
        failed_count = sum(
            1 for d in severe_defs
            if str(
                d.severity.value if hasattr(d.severity, "value") else d.severity
            ) in ("material_weakness", "significant_deficiency")
        )
        if failed_count > 0:
            s = "s" if failed_count > 1 else ""
            items.append({
                "type": "warning",
                "module": "pc",
                "title": f"{failed_count} control failure{s}",
                "description": (
                    "Controls with material weakness or significant deficiency"
                ),
                "action": "Review",
                "action_url": "/process-control/deficiencies",
                "priority": 2,
            })

        # ── Overdue audit actions ────────────────────────────────────────────
        overdue_actions = (
            db.query(AuditManagementAction)
            .filter(
                AuditManagementAction.tenant_id == tenant_id,
                AuditManagementAction.status.in_(["open", "in_progress"]),
                AuditManagementAction.due_date < datetime.utcnow(),
            )
            .all()
        )
        if overdue_actions:
            n = len(overdue_actions)
            s = "s" if n > 1 else ""
            items.append({
                "type": "warning",
                "module": "am",
                "title": f"{n} overdue audit action{s}",
                "description": "Remediation actions past their due date",
                "action": "Escalate",
                "action_url": "/audit-management/actions/overdue",
                "priority": 3,
            })

        # ── Risks exceeding appetite ─────────────────────────────────────────
        risks_over_appetite = (
            db.query(EnterpriseRisk)
            .filter(
                EnterpriseRisk.tenant_id == tenant_id,
                EnterpriseRisk.is_active.is_(True),
                EnterpriseRisk.risk_appetite.isnot(None),
                EnterpriseRisk.residual_score > EnterpriseRisk.risk_appetite,
            )
            .all()
        )
        if risks_over_appetite:
            n = len(risks_over_appetite)
            s = "s" if n > 1 else ""
            items.append({
                "type": "info",
                "module": "rm",
                "title": f"{n} risk{s} exceeding appetite",
                "description": (
                    "Enterprise risks where residual score exceeds defined appetite"
                ),
                "action": "Review",
                "action_url": "/risk-management/risks",
                "priority": 4,
            })

    items.sort(key=lambda x: x.get("priority", 99))
    return {"count": len(items), "items": items}


# ===========================================================================
# 3. AI EXPLAIN
# ===========================================================================

@router.post(
    "/explain",
    summary="Explain Any GRC Object",
    description=(
        "Return a plain-language explanation of any GRC object. "
        "Supported object_type values: risk, violation, control, finding. "
        "Returns a summary, why-it-matters narrative, and recommended actions."
    ),
)
def explain_object(
    body: Dict[str, Any] = Body(
        ...,
        example={
            "object_type": "violation",
            "object_id": "VIO-001",
        },
    ),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    """Plain-language explanation of any GRC object.

    Body: {"object_type": "risk|violation|control|finding", "object_id": "..."}
    """
    object_type: str = body.get("object_type", "")
    object_id: str = body.get("object_id", "")

    if not object_type or not object_id:
        raise HTTPException(
            status_code=400,
            detail="Both 'object_type' and 'object_id' are required.",
        )

    with db_manager.session_scope() as db:

        # ── Risk ─────────────────────────────────────────────────────────────
        if object_type == "risk":
            from db.models.risk_management import EnterpriseRisk

            obj = (
                db.query(EnterpriseRisk)
                .filter(
                    EnterpriseRisk.tenant_id == tenant_id,
                    EnterpriseRisk.risk_id == object_id,
                )
                .first()
            )
            if not obj:
                raise HTTPException(status_code=404, detail="Risk not found")

            score = obj.residual_score or obj.inherent_score or 0
            if score > 20:
                severity = "Critical"
            elif score > 12:
                severity = "High"
            elif score > 6:
                severity = "Medium"
            else:
                severity = "Low"

            coverage = obj.control_coverage or "unknown"
            coverage_notes = {
                "uncontrolled": "This risk has no controls assigned.",
                "failed": "Some linked controls are failing, which increases the effective risk.",
                "degraded": "Linked controls show partial degradation.",
                "effective": "Linked controls are operating effectively.",
            }
            explanation = (
                f"**{obj.title}** is rated **{severity}** (score: {score}/25). "
                + coverage_notes.get(coverage, "")
            )
            if obj.related_control_ids:
                explanation += f" {len(obj.related_control_ids)} control(s) are linked."
            if obj.related_finding_ids:
                explanation += (
                    f" {len(obj.related_finding_ids)} audit finding(s) reference this risk."
                )

            recommended = (
                [
                    "Review linked controls for effectiveness",
                    "Check if mitigation plans are on track",
                    "Consider scheduling a risk assessment",
                ]
                if score > 12
                else ["Monitor during next review cycle"]
            )
            return {
                "object_type": "risk",
                "object_id": object_id,
                "title": obj.title,
                "severity": severity,
                "explanation": explanation,
                "recommended_actions": recommended,
            }

        # ── Violation ────────────────────────────────────────────────────────
        elif object_type == "violation":
            from db.models.risk import RiskViolation

            obj = (
                db.query(RiskViolation)
                .filter(
                    RiskViolation.tenant_id == tenant_id,
                    RiskViolation.violation_id == object_id,
                )
                .first()
            )
            if not obj:
                raise HTTPException(status_code=404, detail="Violation not found")

            sev = obj.severity.value if hasattr(obj.severity, "value") else str(obj.severity)
            explanation = (
                f"User **{obj.username or obj.user_external_id}** has a **{sev}** "
                f"SoD conflict (rule: {obj.rule_id}). "
                f"{'This is mitigated by a compensating control.' if obj.is_mitigated else 'No compensating control is assigned.'} "
                f"Status: {obj.status.value if hasattr(obj.status, 'value') else obj.status}."
            )
            return {
                "object_type": "violation",
                "object_id": object_id,
                "title": obj.rule_name,
                "severity": sev,
                "explanation": explanation,
                "recommended_actions": [
                    (
                        "Remove conflicting access"
                        if not obj.is_mitigated
                        else "Review mitigation effectiveness"
                    ),
                    "Run what-if simulation for role changes",
                ],
            }

        # ── Control ──────────────────────────────────────────────────────────
        elif object_type == "control":
            from db.models.process_control import (
                ProcessControl, ControlDeficiency, ControlTest,
            )

            obj = (
                db.query(ProcessControl)
                .filter(
                    ProcessControl.tenant_id == tenant_id,
                    ProcessControl.control_id == object_id,
                )
                .first()
            )
            if not obj:
                raise HTTPException(status_code=404, detail="Control not found")

            open_defs = (
                db.query(func.count(ControlDeficiency.id))
                .filter(
                    ControlDeficiency.tenant_id == tenant_id,
                    ControlDeficiency.control_id == obj.id,
                    ControlDeficiency.status.in_(["open", "in_remediation"]),
                )
                .scalar() or 0
            )
            latest_test = (
                db.query(ControlTest)
                .filter(
                    ControlTest.tenant_id == tenant_id,
                    ControlTest.control_id == obj.id,
                )
                .order_by(ControlTest.created_at.desc())
                .first()
            )

            if latest_test:
                result_val = (
                    latest_test.result.value
                    if hasattr(latest_test.result, "value")
                    else str(latest_test.result)
                )
                test_status = f"Last tested: {result_val}"
            else:
                test_status = "Not yet tested"

            ctrl_type = (
                obj.control_type.value
                if hasattr(obj.control_type, "value")
                else (obj.control_type or "")
            )
            ctrl_nature = (
                obj.control_nature.value
                if hasattr(obj.control_nature, "value")
                else (obj.control_nature or "")
            )
            explanation = (
                f"**{obj.name}** is a {ctrl_type} {ctrl_nature} control "
                f"in the {obj.process_name} process. {test_status}. "
                f"{f'{open_defs} open deficienc(ies).' if open_defs > 0 else 'No open deficiencies.'} "
                f"{'This is a key/SOX control.' if obj.key_control else ''}"
            )
            return {
                "object_type": "control",
                "object_id": object_id,
                "title": obj.name,
                "explanation": explanation,
                "recommended_actions": [
                    (
                        "Schedule operating effectiveness test"
                        if not latest_test
                        else "Review test results"
                    ),
                    (
                        "Remediate open deficiencies"
                        if open_defs > 0
                        else "Maintain current effectiveness"
                    ),
                ],
            }

        # ── Finding ──────────────────────────────────────────────────────────
        elif object_type == "finding":
            from db.models.audit_management import AuditFinding, AuditManagementAction

            obj = (
                db.query(AuditFinding)
                .filter(
                    AuditFinding.tenant_id == tenant_id,
                    AuditFinding.finding_id == object_id,
                )
                .first()
            )
            if not obj:
                raise HTTPException(status_code=404, detail="Finding not found")

            actions = (
                db.query(AuditManagementAction)
                .filter(
                    AuditManagementAction.tenant_id == tenant_id,
                    AuditManagementAction.finding_id == obj.id,
                )
                .all()
            )
            overdue = sum(
                1
                for a in actions
                if a.due_date
                and a.due_date < datetime.utcnow()
                and str(
                    a.status.value if hasattr(a.status, "value") else a.status
                ) in ("open", "in_progress")
            )
            sev = (
                obj.severity.value
                if hasattr(obj.severity, "value")
                else str(obj.severity)
            )
            explanation = (
                f"**{obj.title}** — {sev} finding. "
                f"**Condition:** {(obj.condition or '')[:200]}. "
                f"**Cause:** {(obj.cause or '')[:200]}. "
                f"{len(actions)} remediation action(s)"
                f"{f', {overdue} overdue' if overdue else ''}."
            )
            return {
                "object_type": "finding",
                "object_id": object_id,
                "title": obj.title,
                "severity": sev,
                "explanation": explanation,
                "recommended_actions": [
                    (
                        "Escalate overdue actions"
                        if overdue
                        else "Track action completion"
                    ),
                    (
                        "Link to enterprise risk if not already linked"
                        if not obj.risk_id
                        else "Review risk impact"
                    ),
                ],
            }

        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unknown object_type: '{object_type}'. "
                    "Use one of: risk, violation, control, finding."
                ),
            )


# ===========================================================================
# 4. AI INVESTIGATE
# ===========================================================================

@router.post(
    "/investigate",
    summary="AI Investigate",
    description=(
        "Deep-dive investigation into why something is happening. "
        "Provide a risk_id for focused risk investigation, or a free-text question. "
        "The engine gathers evidence from all GRC modules and returns a summary with "
        "contributing factors and recommended remediation steps."
    ),
)
def investigate(
    body: Dict[str, Any] = Body(
        ...,
        example={"risk_id": "RSK-00000001"},
    ),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    """Deep investigation: why is something happening?

    Body: {"risk_id": "RSK-xxx"} for focused risk investigation,
    or {"question": "..."} for a generic query.
    """
    with db_manager.session_scope() as db:
        risk_id: Optional[str] = body.get("risk_id")

        if risk_id:
            from db.models.risk_management import EnterpriseRisk
            from db.models.risk import RiskViolation, ViolationStatus
            from db.models.process_control import ProcessControl, ControlDeficiency
            from db.models.audit_management import AuditFinding

            risk = (
                db.query(EnterpriseRisk)
                .filter(
                    EnterpriseRisk.tenant_id == tenant_id,
                    EnterpriseRisk.risk_id == risk_id,
                )
                .first()
            )
            if not risk:
                raise HTTPException(status_code=404, detail="Risk not found")

            factors: List[str] = []

            # AC: open violations in the landscape
            violation_count = (
                db.query(func.count(RiskViolation.id))
                .filter(
                    RiskViolation.tenant_id == tenant_id,
                    RiskViolation.status == ViolationStatus.OPEN,
                )
                .scalar() or 0
            )
            if violation_count:
                factors.append(f"{violation_count} open SoD violations in the landscape")

            # PC: deficiencies on linked controls
            control_ids = risk.related_control_ids or []
            if control_ids:
                ctrls = (
                    db.query(ProcessControl)
                    .filter(
                        ProcessControl.tenant_id == tenant_id,
                        ProcessControl.control_id.in_(control_ids),
                    )
                    .all()
                )
                ctrl_db_ids = [c.id for c in ctrls]
                if ctrl_db_ids:
                    def_count = (
                        db.query(func.count(ControlDeficiency.id))
                        .filter(
                            ControlDeficiency.tenant_id == tenant_id,
                            ControlDeficiency.control_id.in_(ctrl_db_ids),
                            ControlDeficiency.status.in_(["open", "in_remediation"]),
                        )
                        .scalar() or 0
                    )
                    if def_count:
                        factors.append(f"{def_count} open deficiencies on linked controls")

            # AM: findings referencing this risk
            finding_count = (
                db.query(func.count(AuditFinding.id))
                .filter(
                    AuditFinding.tenant_id == tenant_id,
                    AuditFinding.risk_id == risk.id,
                )
                .scalar() or 0
            )
            if finding_count:
                factors.append(f"{finding_count} audit findings reference this risk")

            coverage = risk.control_coverage or "unknown"
            if coverage in ("failed", "degraded"):
                factors.append(f"Control coverage is {coverage}")

            recommendations = [
                "Remediate open control deficiencies",
                "Resolve critical SoD violations",
                "Close overdue audit findings",
                "Schedule risk re-assessment",
            ][: max(1, len(factors))]

            return {
                "risk_id": risk_id,
                "title": risk.title,
                "inherent_score": risk.inherent_score,
                "residual_score": risk.residual_score,
                "system_indicated_residual": getattr(
                    risk, "system_indicated_residual", None
                ),
                "control_coverage": coverage,
                "contributing_factors": factors,
                "summary": (
                    f"{risk.title} has a residual score of "
                    f"{risk.residual_score or 'N/A'}. "
                    + (
                        f"Contributing factors: {'; '.join(factors)}."
                        if factors
                        else "No significant contributing factors detected."
                    )
                ),
                "recommended_actions": recommendations,
            }

        # Generic question fallback
        return {
            "message": "Provide a risk_id for focused investigation.",
            "example": {"risk_id": "RSK-XXXXXXXX"},
        }


# ===========================================================================
# 5. AI RECOMMEND
# ===========================================================================

@router.post(
    "/recommend",
    summary="AI Recommend",
    description=(
        "Generate actionable fix recommendations for a GRC object. "
        "Supported object_type values: violation, deficiency. "
        "Returns ranked options with effort, impact, and risk-reduction estimates."
    ),
)
def recommend_actions(
    body: Dict[str, Any] = Body(
        ...,
        example={"object_type": "violation", "object_id": "VIO-001"},
    ),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    """Generate actionable fix recommendations.

    Body: {"object_type": "violation|deficiency", "object_id": "..."}
    """
    object_type: str = body.get("object_type", "")
    object_id: str = body.get("object_id", "")

    if not object_type or not object_id:
        raise HTTPException(
            status_code=400,
            detail="Both 'object_type' and 'object_id' are required.",
        )

    with db_manager.session_scope() as db:

        if object_type == "violation":
            from db.models.risk import RiskViolation

            v = (
                db.query(RiskViolation)
                .filter(
                    RiskViolation.tenant_id == tenant_id,
                    RiskViolation.violation_id == object_id,
                )
                .first()
            )
            if not v:
                raise HTTPException(status_code=404, detail="Violation not found")

            sev = v.severity.value if hasattr(v.severity, "value") else str(v.severity)
            return {
                "object_type": "violation",
                "object_id": object_id,
                "severity": sev,
                "recommendations": [
                    {
                        "action": "Remove conflicting access",
                        "impact": "Eliminates SoD conflict",
                        "effort": "low",
                        "risk_reduction": "high",
                        "details": (
                            f"Remove one of the conflicting roles from user "
                            f"{v.user_external_id}"
                        ),
                    },
                    {
                        "action": "Assign compensating control",
                        "impact": "Mitigates but does not eliminate risk",
                        "effort": "medium",
                        "risk_reduction": "medium",
                        "details": (
                            "Create a detective control to monitor transactions"
                        ),
                    },
                    {
                        "action": "Accept risk",
                        "impact": "No change to access",
                        "effort": "low",
                        "risk_reduction": "none",
                        "details": (
                            "Document business justification and accept residual risk"
                        ),
                    },
                ],
                "estimated_risk_reduction": "60-80% with option 1",
            }

        elif object_type == "deficiency":
            from db.models.process_control import ControlDeficiency

            d = (
                db.query(ControlDeficiency)
                .filter(
                    ControlDeficiency.tenant_id == tenant_id,
                    ControlDeficiency.deficiency_id == object_id,
                )
                .first()
            )
            if not d:
                raise HTTPException(status_code=404, detail="Deficiency not found")

            sev = (
                d.severity.value
                if hasattr(d.severity, "value")
                else str(d.severity)
            )
            effort = "high" if sev == "material_weakness" else "medium"
            return {
                "object_type": "deficiency",
                "object_id": object_id,
                "severity": sev,
                "recommendations": [
                    {
                        "action": "Implement remediation plan",
                        "impact": "Closes deficiency",
                        "effort": effort,
                        "details": (
                            d.remediation_plan
                            or "Define and execute remediation steps"
                        ),
                    },
                    {
                        "action": "Strengthen control design",
                        "impact": "Prevents recurrence",
                        "effort": "high",
                        "details": (
                            "Redesign control to address root cause"
                        ),
                    },
                ],
            }

        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Provide object_type ('violation' or 'deficiency') and object_id."
                ),
            )


# ===========================================================================
# 6. ROLE-PERSONALISED DASHBOARD
# ===========================================================================

_VALID_ROLES = frozenset(
    {"cfo", "ciso", "cae", "control_owner", "auditor", "employee", "risk_manager"}
)


@router.get(
    "/dashboard/{role}",
    summary="Role-Personalised Dashboard",
    description=(
        "Return dashboard data tailored to the user's role. "
        "Supported roles: cfo, ciso, cae, control_owner, auditor, employee, risk_manager. "
        "Each role sees a different set of metrics and top-line KPIs."
    ),
)
def get_personalized_dashboard(
    role: str,
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    """Role-specific dashboard view."""
    role_lower = role.lower()
    if role_lower not in _VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid role '{role}'. "
                f"Valid roles: {sorted(_VALID_ROLES)}"
            ),
        )

    with db_manager.session_scope() as db:
        from db.models.risk import RiskViolation, ViolationStatus, RiskSeverityLevel
        from db.models.risk_management import EnterpriseRisk
        from db.models.process_control import ProcessControl, ControlDeficiency
        from db.models.audit_management import (
            AuditFinding, AuditEngagement, AuditManagementAction,
        )

        base: Dict[str, Any] = {
            "role": role_lower,
            "generated_at": datetime.utcnow().isoformat(),
        }

        if role_lower == "cfo":
            top_risks = (
                db.query(EnterpriseRisk)
                .filter(
                    EnterpriseRisk.tenant_id == tenant_id,
                    EnterpriseRisk.is_active.is_(True),
                )
                .order_by(EnterpriseRisk.residual_score.desc())
                .limit(5)
                .all()
            )
            total_controls = (
                db.query(func.count(ProcessControl.id))
                .filter(
                    ProcessControl.tenant_id == tenant_id,
                    ProcessControl.is_active.is_(True),
                )
                .scalar() or 0
            )
            open_defs = (
                db.query(func.count(ControlDeficiency.id))
                .filter(
                    ControlDeficiency.tenant_id == tenant_id,
                    ControlDeficiency.status.in_(["open", "in_remediation"]),
                )
                .scalar() or 0
            )
            open_findings = (
                db.query(func.count(AuditFinding.id))
                .filter(
                    AuditFinding.tenant_id == tenant_id,
                    AuditFinding.status.notin_(["closed"]),
                )
                .scalar() or 0
            )
            base.update({
                "sections": [
                    "enterprise_risk", "control_health",
                    "compliance", "critical_findings",
                ],
                "top_risks": [
                    {
                        "risk_id": r.risk_id,
                        "title": r.title,
                        "residual_score": r.residual_score,
                    }
                    for r in top_risks
                ],
                "control_effectiveness": round(
                    ((total_controls - open_defs) / max(total_controls, 1)) * 100
                ),
                "open_findings": open_findings,
            })

        elif role_lower == "ciso":
            critical_violations = (
                db.query(func.count(RiskViolation.id))
                .filter(
                    RiskViolation.tenant_id == tenant_id,
                    RiskViolation.status == ViolationStatus.OPEN,
                    RiskViolation.severity.in_(
                        [RiskSeverityLevel.CRITICAL, RiskSeverityLevel.HIGH]
                    ),
                )
                .scalar() or 0
            )
            total_open_violations = (
                db.query(func.count(RiskViolation.id))
                .filter(
                    RiskViolation.tenant_id == tenant_id,
                    RiskViolation.status == ViolationStatus.OPEN,
                )
                .scalar() or 0
            )
            base.update({
                "sections": [
                    "access_risk", "privileged_access",
                    "sod_conflicts", "security_controls",
                ],
                "critical_violations": critical_violations,
                "total_open_violations": total_open_violations,
            })

        elif role_lower == "cae":
            engagements = (
                db.query(AuditEngagement)
                .filter(
                    AuditEngagement.tenant_id == tenant_id,
                    AuditEngagement.status.notin_(["closed"]),
                )
                .all()
            )
            overdue = (
                db.query(func.count(AuditManagementAction.id))
                .filter(
                    AuditManagementAction.tenant_id == tenant_id,
                    AuditManagementAction.status.in_(["open", "in_progress"]),
                    AuditManagementAction.due_date < datetime.utcnow(),
                )
                .scalar() or 0
            )
            base.update({
                "sections": [
                    "audit_plan", "engagements", "findings", "overdue_actions",
                ],
                "active_engagements": len(engagements),
                "overdue_actions": overdue,
            })

        elif role_lower == "control_owner":
            base.update({
                "sections": [
                    "my_controls", "tests_due", "failed_tests", "evidence_required",
                ],
            })

        elif role_lower == "auditor":
            base.update({
                "sections": [
                    "my_engagements", "procedures", "workpapers", "findings",
                ],
            })

        elif role_lower == "risk_manager":
            risks = (
                db.query(EnterpriseRisk)
                .filter(
                    EnterpriseRisk.tenant_id == tenant_id,
                    EnterpriseRisk.is_active.is_(True),
                )
                .order_by(EnterpriseRisk.residual_score.desc())
                .limit(10)
                .all()
            )
            base.update({
                "sections": [
                    "risk_register", "kri_dashboard", "risk_responses", "incidents",
                ],
                "top_risks": [
                    {
                        "risk_id": r.risk_id,
                        "title": r.title,
                        "residual_score": r.residual_score,
                    }
                    for r in risks
                ],
            })

        else:  # employee
            base.update({
                "sections": ["my_access", "pending_approvals", "certifications"],
            })

        return base


# ===========================================================================
# 7. ONE-CLICK FIX PREVIEW
# ===========================================================================

@router.post(
    "/fix-preview",
    summary="One-Click Fix Preview",
    description=(
        "Preview exactly what a fix action would change before applying it. "
        "Supported actions: remove_access, assign_mitigation, remediate_deficiency. "
        "Always call this before executing a fix to review the impact."
    ),
)
def fix_preview(
    body: Dict[str, Any] = Body(
        ...,
        example={
            "action": "remove_access",
            "target_id": "VIO-001",
            "params": {},
        },
    ),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    """Preview what a fix action would change before applying.

    Body: {
        "action": "remove_access|assign_mitigation|remediate_deficiency",
        "target_id": "...",
        "params": {...}   # optional extra parameters
    }
    """
    action: str = body.get("action", "")
    target_id: str = body.get("target_id", "")

    if not action or not target_id:
        raise HTTPException(
            status_code=400,
            detail="Both 'action' and 'target_id' are required.",
        )

    if action == "remove_access":
        return {
            "action": "remove_access",
            "target": target_id,
            "preview": {
                "changes": [
                    f"Remove conflicting role from user {target_id}",
                    "Recalculate SoD risk score",
                    "Notify user's manager",
                    "Create audit trail entry",
                ],
                "risk_reduction": "Eliminates 1 SoD conflict",
                "affected_users": 1,
                "reversible": True,
            },
            "confirm_url": f"/access-requests/revoke/{target_id}",
        }

    elif action == "assign_mitigation":
        return {
            "action": "assign_mitigation",
            "target": target_id,
            "preview": {
                "changes": [
                    f"Assign compensating control to violation {target_id}",
                    "Mark violation as mitigated",
                    "Schedule monitoring review",
                ],
                "risk_reduction": "Reduces effective risk by 40-60%",
                "reversible": True,
            },
        }

    elif action == "remediate_deficiency":
        return {
            "action": "remediate_deficiency",
            "target": target_id,
            "preview": {
                "changes": [
                    f"Mark deficiency {target_id} as remediated",
                    "Trigger verification workflow",
                    "Update control effectiveness score",
                    "Recompute linked risk coverage (XL-A)",
                ],
                "risk_reduction": "Restores control effectiveness",
                "reversible": False,
            },
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown action '{action}'. "
                "Use one of: remove_access, assign_mitigation, remediate_deficiency."
            ),
        )


# ===========================================================================
# 8. XI-04 Audit Risk Scores — configurable weights
# ===========================================================================

@router.get(
    "/audit-risk-scores",
    summary="XI-04 Composite Audit Risk Scores",
    description=(
        "Compute composite audit risk scores for all auditable entities. "
        "Weights for RM (risk management), PC (process control), and AC (access control) "
        "are configurable via query parameters. Defaults: rm=0.40, pc=0.35, ac=0.25."
    ),
)
def get_audit_risk_scores(
    rm_weight: float = Query(0.40, ge=0.0, le=1.0, description="RM component weight"),
    pc_weight: float = Query(0.35, ge=0.0, le=1.0, description="PC component weight"),
    ac_weight: float = Query(0.25, ge=0.0, le=1.0, description="AC component weight"),
    tenant_id: str = Depends(_get_tenant_id),
) -> Dict[str, Any]:
    """
    Compute composite risk scores for auditable entities using configurable weights.

    Weight validation: weights are normalised if they don't sum to 1.0.
    """
    total_weight = rm_weight + pc_weight + ac_weight
    if total_weight <= 0:
        raise HTTPException(status_code=400, detail="Weights must sum to a positive value")

    # Normalise weights to sum to 1.0
    rm_w = rm_weight / total_weight
    pc_w = pc_weight / total_weight
    ac_w = ac_weight / total_weight

    try:
        from core.xi_bridge import GRCIntegrationBridge
        from db.database import db_manager

        if not db_manager._initialized:
            db_manager.init()

        with db_manager.session_scope() as session:
            bridge = GRCIntegrationBridge(tenant_id=tenant_id, db_session=session)
            scores = bridge.compute_audit_risk_scores(
                rm_weight=rm_w,
                pc_weight=pc_w,
                ac_weight=ac_w,
            )
            return {
                "tenant_id": tenant_id,
                "weights_applied": {"rm": round(rm_w, 4), "pc": round(pc_w, 4), "ac": round(ac_w, 4)},
                "entity_count": len(scores),
                "scores": scores,
                "generated_at": datetime.utcnow().isoformat(),
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Audit risk score computation failed: {exc}")
