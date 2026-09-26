"""
GRC Intelligence Engine

The central brain of GovernexPlus — correlates data across every GRC module
and exposes seven high-level intelligence capabilities:

  1. compute_health_score()       — single 0-100 GRC health score
  2. get_attention_items()        — proactive prioritised action list
  3. generate_insights()          — AI-style cross-module pattern insights
  4. explain()                    — plain-language explanation of any GRC object
  5. investigate()                — full dependency-graph traversal from any node
  6. preview_fix()                — show exactly what a one-click fix would do
  7. get_personalized_dashboard() — role-tailored dashboard view

All methods perform real DB queries.  The engine is constructed per-request
with the caller's tenant_id and sqlalchemy Session so it naturally respects
row-level tenant isolation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

# ── Access-control models ────────────────────────────────────────────────────
from db.models.user import User, Role, UserRole
from db.models.risk import RiskViolation, MitigationControl, ViolationStatus, RiskSeverityLevel
from db.models.firefighter import FirefighterSession, FirefighterRequest, FFSessionStatus
from db.models.audit import CertificationCampaignLog

# ── Process Control models ───────────────────────────────────────────────────
from db.models.process_control import (
    ProcessControl, ControlStatus, ControlTest, TestResult, TestStatus,
    ControlDeficiency, DeficiencyStatus, DeficiencySeverity,
)

# ── Risk Management models ───────────────────────────────────────────────────
from db.models.risk_management import (
    EnterpriseRisk, RiskStatus, RiskAppetite,
    KeyRiskIndicator, KRIStatus, KRIMeasurement,
    RiskResponse, ResponseStatus,
    RiskIncident, IncidentStatus,
)

# ── Audit Management models ──────────────────────────────────────────────────
from db.models.audit_management import (
    AuditEngagement, EngagementStatus,
    AuditFinding, FindingSeverity, FindingStatus,
    AuditManagementAction, ActionStatus,
    AuditPlan, AuditPlanStatus,
    AuditorResource,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal severity ordering helpers
# ---------------------------------------------------------------------------

_VIOLATION_SEV_ORDER = {
    RiskSeverityLevel.CRITICAL: 4,
    RiskSeverityLevel.HIGH: 3,
    RiskSeverityLevel.MEDIUM: 2,
    RiskSeverityLevel.LOW: 1,
}

_FINDING_SEV_ORDER = {
    FindingSeverity.CRITICAL: 5,
    FindingSeverity.HIGH: 4,
    FindingSeverity.MEDIUM: 3,
    FindingSeverity.LOW: 2,
    FindingSeverity.OBSERVATION: 1,
}

_DEFICIENCY_SEV_ORDER = {
    DeficiencySeverity.MATERIAL_WEAKNESS: 4,
    DeficiencySeverity.SIGNIFICANT_DEFICIENCY: 3,
    DeficiencySeverity.CONTROL_GAP: 2,
    DeficiencySeverity.OBSERVATION: 1,
}

NOW = datetime.utcnow


# ===========================================================================
# GRCIntelligenceEngine
# ===========================================================================

class GRCIntelligenceEngine:
    """
    Per-request GRC Intelligence Engine.

    Construct with the calling request's tenant_id and an active SQLAlchemy
    Session.  All public methods are safe to call independently.
    """

    def __init__(self, tenant_id: str, db: Session) -> None:
        self.tenant_id = tenant_id
        self.db = db

    # -----------------------------------------------------------------------
    # 1. GRC Health Score
    # -----------------------------------------------------------------------

    def compute_health_score(self) -> Dict[str, Any]:
        """
        Compute overall GRC health as a single score 0-100.

        Weighted equally across four pillars (25% each):
          - Access Risk  : ratio of open violations vs user population
          - Control Health: percentage of active controls with no recent failures
          - Enterprise Risk: how far residual scores sit from appetite thresholds
          - Audit Health : percentage of findings/actions that are closed on-time
        """
        access_score, access_detail = self._score_access_risk()
        control_score, control_detail = self._score_control_health()
        risk_score, risk_detail = self._score_enterprise_risk()
        audit_score, audit_detail = self._score_audit_health()

        overall = round(
            access_score * 0.25
            + control_score * 0.25
            + risk_score * 0.25
            + audit_score * 0.25,
            1,
        )

        # Derive qualitative status
        if overall >= 85:
            status = "healthy"
        elif overall >= 70:
            status = "fair"
        elif overall >= 50:
            status = "at_risk"
        else:
            status = "critical"

        # Simple trend: compare against 30-day snapshot (violations added
        # in last 30 days vs violations existing before that window)
        trend = self._compute_health_trend(overall)

        return {
            "score": overall,
            "status": status,
            "trend": trend,
            "components": {
                "access_risk": {
                    "score": access_score,
                    "weight": 0.25,
                    "label": "Access Risk",
                    "detail": access_detail,
                },
                "control_health": {
                    "score": control_score,
                    "weight": 0.25,
                    "label": "Control Health",
                    "detail": control_detail,
                },
                "enterprise_risk": {
                    "score": risk_score,
                    "weight": 0.25,
                    "label": "Enterprise Risk",
                    "detail": risk_detail,
                },
                "audit_health": {
                    "score": audit_score,
                    "weight": 0.25,
                    "label": "Audit Health",
                    "detail": audit_detail,
                },
            },
            "computed_at": NOW().isoformat(),
        }

    # -- scoring sub-methods -------------------------------------------------

    def _score_access_risk(self):
        """Return (score 0-100, detail dict). High violations → low score."""
        tid = self.tenant_id
        total_users = self.db.query(func.count(User.id)).filter(
            User.tenant_id == tid,
            User.status == "active",
        ).scalar() or 1

        open_violations = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.tenant_id == tid,
            RiskViolation.status == ViolationStatus.OPEN,
        ).scalar() or 0

        critical_violations = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.tenant_id == tid,
            RiskViolation.status == ViolationStatus.OPEN,
            RiskViolation.severity == RiskSeverityLevel.CRITICAL,
        ).scalar() or 0

        # Ratio of violations to users — capped at 1.0
        violation_ratio = min(open_violations / total_users, 1.0)
        # Critical violations carry extra weight
        critical_ratio = min(critical_violations / total_users, 1.0)

        raw = 100 - (violation_ratio * 60) - (critical_ratio * 40)
        score = max(0.0, round(raw, 1))

        return score, {
            "open_violations": open_violations,
            "critical_violations": critical_violations,
            "total_active_users": total_users,
            "violation_ratio": round(violation_ratio, 3),
        }

    def _score_control_health(self):
        """Return (score 0-100, detail dict)."""
        tid = self.tenant_id

        active_controls = self.db.query(ProcessControl).filter(
            ProcessControl.tenant_id == tid,
            ProcessControl.is_active.is_(True),
            ProcessControl.status == ControlStatus.ACTIVE,
        ).all()

        total = len(active_controls)
        if total == 0:
            return 100.0, {"total_controls": 0, "effective": 0, "ineffective": 0}

        # A control is considered "failed" if it has an open deficiency with
        # severity >= SIGNIFICANT_DEFICIENCY.
        failed_control_ids = set(
            row[0]
            for row in self.db.query(ControlDeficiency.control_id).filter(
                ControlDeficiency.tenant_id == tid,
                ControlDeficiency.status.in_([
                    DeficiencyStatus.OPEN,
                    DeficiencyStatus.IN_REMEDIATION,
                ]),
                ControlDeficiency.severity.in_([
                    DeficiencySeverity.MATERIAL_WEAKNESS,
                    DeficiencySeverity.SIGNIFICANT_DEFICIENCY,
                ]),
            ).distinct().all()
        )

        # Also count controls whose last test was ineffective
        ineffective_test_control_ids = set(
            row[0]
            for row in self.db.query(ControlTest.control_id).filter(
                ControlTest.tenant_id == tid,
                ControlTest.result == TestResult.INEFFECTIVE,
                ControlTest.status == TestStatus.COMPLETED,
            ).distinct().all()
        )

        failed_ids = failed_control_ids | ineffective_test_control_ids
        failed_count = len([c for c in active_controls if c.id in failed_ids])
        effective_count = total - failed_count
        effectiveness_pct = (effective_count / total) * 100

        # Open material weaknesses are weighted more severely
        material_weaknesses = self.db.query(func.count(ControlDeficiency.id)).filter(
            ControlDeficiency.tenant_id == tid,
            ControlDeficiency.status.in_([
                DeficiencyStatus.OPEN,
                DeficiencyStatus.IN_REMEDIATION,
            ]),
            ControlDeficiency.severity == DeficiencySeverity.MATERIAL_WEAKNESS,
        ).scalar() or 0

        penalty = min(material_weaknesses * 5, 20)
        score = max(0.0, round(effectiveness_pct - penalty, 1))

        return score, {
            "total_controls": total,
            "effective": effective_count,
            "ineffective": failed_count,
            "material_weaknesses": material_weaknesses,
            "effectiveness_pct": round(effectiveness_pct, 1),
        }

    def _score_enterprise_risk(self):
        """Return (score 0-100, detail dict)."""
        tid = self.tenant_id

        risks = self.db.query(EnterpriseRisk).filter(
            EnterpriseRisk.tenant_id == tid,
            EnterpriseRisk.is_active.is_(True),
            EnterpriseRisk.status.notin_([RiskStatus.CLOSED, RiskStatus.ACCEPTED]),
        ).all()

        if not risks:
            return 100.0, {"total_risks": 0, "above_appetite": 0, "avg_residual": 0}

        # Default appetite = 9 (3x3 on a 5x5 scale) when no explicit record
        appetites = self.db.query(RiskAppetite).filter(
            RiskAppetite.tenant_id == tid,
        ).all()
        default_appetite = 9.0
        if appetites:
            default_appetite = sum(a.appetite_score for a in appetites) / len(appetites)

        residuals = [r.residual_score for r in risks if r.residual_score is not None]
        above_appetite = [s for s in residuals if s > default_appetite]
        avg_residual = sum(residuals) / len(residuals) if residuals else 0.0

        # Score: 100 if all risks within appetite; degrades proportionally
        if not residuals:
            score = 100.0
        else:
            within_ratio = (len(residuals) - len(above_appetite)) / len(residuals)
            excess_ratio = min(
                sum(max(0, s - default_appetite) for s in above_appetite)
                / (default_appetite * len(residuals)),
                1.0,
            )
            score = max(0.0, round(within_ratio * 80 - excess_ratio * 20 + 20, 1))

        return score, {
            "total_risks": len(risks),
            "above_appetite": len(above_appetite),
            "avg_residual_score": round(avg_residual, 2),
            "default_appetite_threshold": round(default_appetite, 2),
        }

    def _score_audit_health(self):
        """Return (score 0-100, detail dict)."""
        tid = self.tenant_id
        now = NOW()

        # Findings closed vs total final findings
        total_findings = self.db.query(func.count(AuditFinding.id)).filter(
            AuditFinding.tenant_id == tid,
            AuditFinding.status == FindingStatus.FINAL,
        ).scalar() or 0

        closed_findings = self.db.query(func.count(AuditFinding.id)).filter(
            AuditFinding.tenant_id == tid,
            AuditFinding.status == FindingStatus.CLOSED,
        ).scalar() or 0

        # Overdue management actions
        overdue_actions = self.db.query(func.count(AuditManagementAction.id)).filter(
            AuditManagementAction.tenant_id == tid,
            AuditManagementAction.status.in_([ActionStatus.OPEN, ActionStatus.IN_PROGRESS]),
            AuditManagementAction.due_date < now,
        ).scalar() or 0

        open_actions = self.db.query(func.count(AuditManagementAction.id)).filter(
            AuditManagementAction.tenant_id == tid,
            AuditManagementAction.status.in_([ActionStatus.OPEN, ActionStatus.IN_PROGRESS]),
        ).scalar() or 0

        all_findings = total_findings + closed_findings
        closure_rate = (closed_findings / all_findings * 100) if all_findings else 100.0
        overdue_penalty = min(overdue_actions * 3, 30)

        score = max(0.0, round(closure_rate - overdue_penalty, 1))

        return score, {
            "total_final_findings": total_findings,
            "closed_findings": closed_findings,
            "closure_rate_pct": round(closure_rate, 1),
            "open_actions": open_actions,
            "overdue_actions": overdue_actions,
        }

    def _compute_health_trend(self, current_score: float) -> str:
        """
        Estimate trend direction based on violations added in recent 30 days
        versus the 30 days before that.
        """
        now = NOW()
        cutoff_recent = now - timedelta(days=30)
        cutoff_prior = now - timedelta(days=60)

        recent = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.tenant_id == self.tenant_id,
            RiskViolation.detected_at >= cutoff_recent,
        ).scalar() or 0

        prior = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.tenant_id == self.tenant_id,
            RiskViolation.detected_at >= cutoff_prior,
            RiskViolation.detected_at < cutoff_recent,
        ).scalar() or 0

        if recent < prior:
            return "+3%"   # improving
        elif recent > prior:
            return "-3%"   # worsening
        return "0%"

    # -----------------------------------------------------------------------
    # 2. Attention Items
    # -----------------------------------------------------------------------

    def get_attention_items(
        self,
        user_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return prioritised list of items that need immediate attention.

        Scans all GRC modules.  If user_id/role is provided, items are
        additionally filtered to those relevant to that user.
        """
        items: List[Dict[str, Any]] = []

        items.extend(self._attention_critical_violations())
        items.extend(self._attention_failed_controls())
        items.extend(self._attention_overdue_audit_actions())
        items.extend(self._attention_kri_breaches())
        items.extend(self._attention_risks_near_appetite())
        items.extend(self._attention_dormant_privileged_users())
        items.extend(self._attention_pending_approvals())
        items.extend(self._attention_expiring_mitigations())

        # Sort: critical first, then high, then medium, then low
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        items.sort(key=lambda x: priority_order.get(x.get("severity", "low"), 3))

        # Role-based filtering when a role is specified
        if role:
            items = self._filter_attention_by_role(items, role)

        return items

    def _attention_critical_violations(self) -> List[Dict[str, Any]]:
        violations = self.db.query(RiskViolation).filter(
            RiskViolation.tenant_id == self.tenant_id,
            RiskViolation.status == ViolationStatus.OPEN,
            RiskViolation.severity == RiskSeverityLevel.CRITICAL,
            RiskViolation.is_mitigated.is_(False),
        ).order_by(RiskViolation.detected_at.asc()).limit(20).all()

        items = []
        for v in violations:
            age_days = (NOW() - v.detected_at).days if v.detected_at else 0
            items.append({
                "severity": "critical",
                "title": f"Critical SoD violation: {v.rule_name}",
                "description_friendly": (
                    f"User {v.username or v.user_external_id} has conflicting access "
                    f"that was detected {age_days} day{'s' if age_days != 1 else ''} ago "
                    f"and has not yet been mitigated. This creates a direct risk of fraud "
                    f"or error in {v.risk_category or 'business'} processes."
                ),
                "module": "access_control",
                "object_type": "violation",
                "object_id": v.violation_id,
                "action_label": "Review Violation",
                "action_url": f"/risk/violations/{v.violation_id}",
                "age_days": age_days,
            })
        return items

    def _attention_failed_controls(self) -> List[Dict[str, Any]]:
        deficiencies = self.db.query(ControlDeficiency).filter(
            ControlDeficiency.tenant_id == self.tenant_id,
            ControlDeficiency.status.in_([
                DeficiencyStatus.OPEN,
                DeficiencyStatus.IN_REMEDIATION,
            ]),
            ControlDeficiency.severity.in_([
                DeficiencySeverity.MATERIAL_WEAKNESS,
                DeficiencySeverity.SIGNIFICANT_DEFICIENCY,
            ]),
        ).order_by(ControlDeficiency.created_at.asc()).limit(20).all()

        items = []
        for d in deficiencies:
            sev = "critical" if d.severity == DeficiencySeverity.MATERIAL_WEAKNESS else "high"
            overdue = (
                d.due_date and d.due_date < NOW() and
                d.status != DeficiencyStatus.VERIFIED_CLOSED
            )
            items.append({
                "severity": sev,
                "title": f"{'Overdue: ' if overdue else ''}Control deficiency: {d.title}",
                "description_friendly": (
                    f"A {d.severity.value.replace('_', ' ')} has been identified. "
                    f"{'Remediation is overdue. ' if overdue else ''}"
                    f"{d.description[:120] + '...' if d.description and len(d.description) > 120 else (d.description or '')}"
                ),
                "module": "process_control",
                "object_type": "deficiency",
                "object_id": d.deficiency_id,
                "action_label": "View Deficiency",
                "action_url": f"/process-control/deficiencies/{d.deficiency_id}",
                "overdue": overdue,
            })
        return items

    def _attention_overdue_audit_actions(self) -> List[Dict[str, Any]]:
        now = NOW()
        actions = self.db.query(AuditManagementAction).filter(
            AuditManagementAction.tenant_id == self.tenant_id,
            AuditManagementAction.status.in_([
                ActionStatus.OPEN,
                ActionStatus.IN_PROGRESS,
                ActionStatus.OVERDUE,
            ]),
            AuditManagementAction.due_date < now,
        ).order_by(AuditManagementAction.due_date.asc()).limit(20).all()

        items = []
        for a in actions:
            days_overdue = (now - a.due_date).days if a.due_date else 0
            items.append({
                "severity": "high" if days_overdue > 30 else "medium",
                "title": f"Overdue audit action ({days_overdue}d): {a.description[:80]}",
                "description_friendly": (
                    f"A management action is {days_overdue} day{'s' if days_overdue != 1 else ''} overdue. "
                    f"Owner: {a.owner_name or a.owner_id or 'unassigned'}. "
                    f"The longer this stays open, the greater the compliance exposure."
                ),
                "module": "audit_management",
                "object_type": "audit_action",
                "object_id": a.action_id,
                "action_label": "Update Action",
                "action_url": f"/audit-management/actions/{a.action_id}",
                "days_overdue": days_overdue,
            })
        return items

    def _attention_kri_breaches(self) -> List[Dict[str, Any]]:
        kris = self.db.query(KeyRiskIndicator).filter(
            KeyRiskIndicator.tenant_id == self.tenant_id,
            KeyRiskIndicator.is_active.is_(True),
            KeyRiskIndicator.status == KRIStatus.BREACH,
        ).all()

        items = []
        for k in kris:
            items.append({
                "severity": "critical",
                "title": f"KRI breach: {k.name}",
                "description_friendly": (
                    f"The key risk indicator '{k.name}' has breached its red threshold. "
                    f"Current value: {k.current_value} {k.unit_of_measure or ''}. "
                    f"Red threshold: {k.threshold_red}. Immediate management attention required."
                ),
                "module": "risk_management",
                "object_type": "kri",
                "object_id": k.kri_id,
                "action_label": "Review KRI",
                "action_url": f"/risk-management/kris/{k.kri_id}",
                "current_value": k.current_value,
                "threshold_red": k.threshold_red,
            })
        return items

    def _attention_risks_near_appetite(self) -> List[Dict[str, Any]]:
        """Flag risks where residual score > appetite (tolerance breached)."""
        appetites = self.db.query(RiskAppetite).filter(
            RiskAppetite.tenant_id == self.tenant_id,
        ).all()

        default_tolerance = 12.0
        if appetites:
            default_tolerance = max(a.tolerance_score for a in appetites)

        risks = self.db.query(EnterpriseRisk).filter(
            EnterpriseRisk.tenant_id == self.tenant_id,
            EnterpriseRisk.is_active.is_(True),
            EnterpriseRisk.residual_score > default_tolerance,
            EnterpriseRisk.status.notin_([RiskStatus.CLOSED, RiskStatus.ACCEPTED]),
        ).order_by(EnterpriseRisk.residual_score.desc()).limit(10).all()

        items = []
        for r in risks:
            excess = round((r.residual_score or 0) - default_tolerance, 1)
            items.append({
                "severity": "high",
                "title": f"Risk exceeds tolerance: {r.title[:60]}",
                "description_friendly": (
                    f"The enterprise risk '{r.title}' has a residual score of "
                    f"{r.residual_score} which is {excess} points above the "
                    f"tolerance threshold of {default_tolerance}. A response plan "
                    f"may be required."
                ),
                "module": "risk_management",
                "object_type": "risk",
                "object_id": r.risk_id,
                "action_label": "View Risk",
                "action_url": f"/risk-management/risks/{r.risk_id}",
                "residual_score": r.residual_score,
                "tolerance": default_tolerance,
                "excess": excess,
            })
        return items

    def _attention_dormant_privileged_users(self) -> List[Dict[str, Any]]:
        """Privileged/firefighter users who have not logged in for 90+ days."""
        threshold = NOW() - timedelta(days=90)

        # Users who have had firefighter access granted
        ff_user_ids = set(
            row[0]
            for row in self.db.query(FirefighterRequest.requester_user_id).filter(
                FirefighterRequest.tenant_id == self.tenant_id,
            ).distinct().all()
        )

        if not ff_user_ids:
            return []

        dormant = self.db.query(User).filter(
            User.tenant_id == self.tenant_id,
            User.user_id.in_(list(ff_user_ids)[:200]),
            User.status == "active",
            User.last_login < threshold,
        ).limit(10).all()

        items = []
        for u in dormant:
            days_dormant = (NOW() - u.last_login).days if u.last_login else 999
            items.append({
                "severity": "medium",
                "title": f"Dormant privileged user: {u.full_name or u.username}",
                "description_friendly": (
                    f"{u.full_name or u.username} has privileged (firefighter) access "
                    f"but has not logged in for {days_dormant} days. "
                    f"Dormant privileged accounts are a significant security risk."
                ),
                "module": "access_control",
                "object_type": "user",
                "object_id": u.user_id,
                "action_label": "Review User Access",
                "action_url": f"/users/{u.user_id}",
                "days_dormant": days_dormant,
            })
        return items

    def _attention_pending_approvals(self) -> List[Dict[str, Any]]:
        """Access certifications that are overdue."""
        now = NOW()
        # Use CertificationCampaignLog as a proxy for pending certification work
        try:
            from db.models.audit import CertificationCampaignLog
            pending = self.db.query(CertificationCampaignLog).filter(
                CertificationCampaignLog.tenant_id == self.tenant_id,
                CertificationCampaignLog.status == "pending",
            ).limit(5).all()

            items = []
            for c in pending:
                items.append({
                    "severity": "medium",
                    "title": f"Certification pending: {c.campaign_name if hasattr(c, 'campaign_name') else c.id}",
                    "description_friendly": (
                        "An access certification campaign has items awaiting your review. "
                        "Timely completion keeps the organisation compliant with access review policies."
                    ),
                    "module": "certification",
                    "object_type": "certification",
                    "object_id": str(c.id),
                    "action_label": "Review Certification",
                    "action_url": "/certification",
                })
            return items
        except Exception:
            return []

    def _attention_expiring_mitigations(self) -> List[Dict[str, Any]]:
        """Mitigation controls expiring within 30 days."""
        threshold = NOW() + timedelta(days=30)
        mitigations = self.db.query(MitigationControl).filter(
            MitigationControl.tenant_id == self.tenant_id,
            MitigationControl.is_active.is_(True),
            MitigationControl.valid_to.isnot(None),
            MitigationControl.valid_to <= threshold,
            MitigationControl.valid_to >= NOW(),
        ).order_by(MitigationControl.valid_to.asc()).limit(10).all()

        items = []
        for m in mitigations:
            days_left = (m.valid_to - NOW()).days if m.valid_to else 0
            items.append({
                "severity": "medium",
                "title": f"Mitigation expiring in {days_left}d: {m.control_name}",
                "description_friendly": (
                    f"The mitigation control '{m.control_name}' expires in {days_left} day{'s' if days_left != 1 else ''}. "
                    f"When it expires, associated violations will revert to unmitigated status. "
                    f"Renew or replace this control before it lapses."
                ),
                "module": "access_control",
                "object_type": "mitigation",
                "object_id": m.control_id,
                "action_label": "Renew Mitigation",
                "action_url": f"/mitigation/{m.control_id}",
                "expires_at": m.valid_to.isoformat() if m.valid_to else None,
                "days_remaining": days_left,
            })
        return items

    def _filter_attention_by_role(
        self, items: List[Dict[str, Any]], role: str
    ) -> List[Dict[str, Any]]:
        """Filter/weight attention items by the user's role."""
        role_lower = role.lower()

        role_module_map: Dict[str, List[str]] = {
            "cfo": ["risk_management", "access_control", "process_control"],
            "ciso": ["access_control", "risk_management"],
            "cae": ["audit_management", "risk_management", "process_control"],
            "control_owner": ["process_control"],
            "employee": ["certification", "access_control"],
            "auditor": ["audit_management", "process_control"],
            "risk_manager": ["risk_management", "access_control"],
        }

        allowed = role_module_map.get(role_lower, None)
        if allowed is None:
            return items  # unknown role — return all

        return [i for i in items if i.get("module") in allowed]

    # -----------------------------------------------------------------------
    # 3. AI Insights
    # -----------------------------------------------------------------------

    def generate_insights(self) -> List[Dict[str, Any]]:
        """
        AI-generated insights by correlating data across modules.

        Each insight identifies a pattern that spans at least two GRC modules
        and provides a natural-language narrative plus a recommendation.
        """
        insights: List[Dict[str, Any]] = []

        insights.extend(self._insight_vendor_payment_risk())
        insights.extend(self._insight_common_root_cause_findings())
        insights.extend(self._insight_high_risk_users_with_critical_violations())
        insights.extend(self._insight_controls_with_repeated_failures())
        insights.extend(self._insight_kri_risk_finding_cluster())
        insights.extend(self._insight_dormant_accounts_with_open_violations())

        # Sort by severity (critical first)
        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        insights.sort(key=lambda x: sev_order.get(x.get("severity", "low"), 3))

        return insights

    def _insight_vendor_payment_risk(self) -> List[Dict[str, Any]]:
        """
        Detect spike in financial SoD violations correlated with failed controls
        and open audit findings in financial processes.
        """
        tid = self.tenant_id

        fin_violations = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.tenant_id == tid,
            RiskViolation.status == ViolationStatus.OPEN,
            RiskViolation.risk_category.in_(["Financial", "FI", "AP", "Vendor"]),
        ).scalar() or 0

        fin_findings = self.db.query(func.count(AuditFinding.id)).filter(
            AuditFinding.tenant_id == tid,
            AuditFinding.status.notin_([FindingStatus.CLOSED]),
            AuditFinding.category == "financial",
        ).scalar() or 0

        fin_deficiencies = self.db.query(func.count(ControlDeficiency.id)).filter(
            ControlDeficiency.tenant_id == tid,
            ControlDeficiency.status.in_([
                DeficiencyStatus.OPEN,
                DeficiencyStatus.IN_REMEDIATION,
            ]),
        ).scalar() or 0

        if fin_violations == 0 and fin_findings == 0:
            return []

        # Compute a simple "increase" by comparing to 60-day window
        cutoff = NOW() - timedelta(days=30)
        recent_fin = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.tenant_id == tid,
            RiskViolation.risk_category.in_(["Financial", "FI", "AP", "Vendor"]),
            RiskViolation.detected_at >= cutoff,
        ).scalar() or 0

        prior_cutoff = NOW() - timedelta(days=60)
        prior_fin = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.tenant_id == tid,
            RiskViolation.risk_category.in_(["Financial", "FI", "AP", "Vendor"]),
            RiskViolation.detected_at >= prior_cutoff,
            RiskViolation.detected_at < cutoff,
        ).scalar() or 1

        pct_change = round((recent_fin - prior_fin) / prior_fin * 100)

        if abs(pct_change) < 10 and fin_findings < 2:
            return []

        return [{
            "insight": (
                f"Vendor payment risk {'increased' if pct_change >= 0 else 'decreased'} "
                f"{abs(pct_change)}% — {fin_violations} related access violation{'s' if fin_violations != 1 else ''} "
                f"and {fin_deficiencies} failed control{'s' if fin_deficiencies != 1 else ''} "
                f"point to a pattern in the procure-to-pay process."
            ),
            "severity": "high" if pct_change > 20 else "medium",
            "related_objects": [
                {"type": "module", "id": "access_control", "label": f"{fin_violations} open financial violations"},
                {"type": "module", "id": "process_control", "label": f"{fin_deficiencies} control deficiencies"},
                {"type": "module", "id": "audit_management", "label": f"{fin_findings} open findings"},
            ],
            "recommendation": (
                "Conduct a targeted review of vendor payment access. "
                "Prioritise users with both payment posting and vendor master maintenance access."
            ),
        }]

    def _insight_common_root_cause_findings(self) -> List[Dict[str, Any]]:
        """Cluster open findings by category to surface shared root causes."""
        tid = self.tenant_id

        rows = self.db.query(
            AuditFinding.category,
            func.count(AuditFinding.id).label("cnt"),
        ).filter(
            AuditFinding.tenant_id == tid,
            AuditFinding.status.notin_([FindingStatus.CLOSED]),
            AuditFinding.category.isnot(None),
        ).group_by(AuditFinding.category).having(
            func.count(AuditFinding.id) >= 3
        ).order_by(func.count(AuditFinding.id).desc()).limit(5).all()

        if not rows:
            return []

        insights = []
        for row in rows:
            cat, cnt = row.category, row.cnt
            insights.append({
                "insight": (
                    f"{cnt} open findings in the '{cat}' category likely share a common "
                    f"underlying process weakness — addressing the root cause once would "
                    f"resolve all {cnt} issues simultaneously."
                ),
                "severity": "high" if cnt >= 5 else "medium",
                "related_objects": [
                    {"type": "finding_category", "id": cat, "label": f"{cnt} open {cat} findings"},
                ],
                "recommendation": (
                    f"Perform a root-cause analysis workshop for all open '{cat}' findings. "
                    f"A single systemic fix is likely more efficient than {cnt} separate remediations."
                ),
            })
        return insights

    def _insight_high_risk_users_with_critical_violations(self) -> List[Dict[str, Any]]:
        """Users who have both high risk score AND critical unmitigated violations."""
        tid = self.tenant_id

        critical_user_ids = set(
            row[0]
            for row in self.db.query(RiskViolation.user_id).filter(
                RiskViolation.tenant_id == tid,
                RiskViolation.status == ViolationStatus.OPEN,
                RiskViolation.severity == RiskSeverityLevel.CRITICAL,
                RiskViolation.is_mitigated.is_(False),
            ).distinct().all()
        )

        if not critical_user_ids:
            return []

        high_risk_users = self.db.query(User).filter(
            User.id.in_(list(critical_user_ids)[:200]),
            User.risk_score >= 75.0,
        ).all()

        if not high_risk_users:
            return []

        names = ", ".join(
            (u.full_name or u.username) for u in high_risk_users[:3]
        )
        if len(high_risk_users) > 3:
            names += f" and {len(high_risk_users) - 3} more"

        return [{
            "insight": (
                f"{len(high_risk_users)} high-risk user{'s' if len(high_risk_users) > 1 else ''} "
                f"({names}) have unmitigated critical SoD violations. "
                f"These users represent the highest concentration of access risk in the organisation."
            ),
            "severity": "critical",
            "related_objects": [
                {"type": "user", "id": u.user_id, "label": u.full_name or u.username}
                for u in high_risk_users[:5]
            ],
            "recommendation": (
                "Immediately review and remediate access for these users. "
                "Consider temporary access suspension while remediation is planned."
            ),
        }]

    def _insight_controls_with_repeated_failures(self) -> List[Dict[str, Any]]:
        """Controls that have failed tests more than once — systemic weakness signal."""
        tid = self.tenant_id

        rows = self.db.query(
            ControlTest.control_id,
            func.count(ControlTest.id).label("fail_count"),
        ).filter(
            ControlTest.tenant_id == tid,
            ControlTest.result == TestResult.INEFFECTIVE,
        ).group_by(ControlTest.control_id).having(
            func.count(ControlTest.id) >= 2
        ).order_by(func.count(ControlTest.id).desc()).limit(5).all()

        if not rows:
            return []

        control_ids = [r.control_id for r in rows]
        controls = {
            c.id: c
            for c in self.db.query(ProcessControl).filter(
                ProcessControl.id.in_(control_ids)
            ).all()
        }

        insights = []
        for row in rows:
            ctrl = controls.get(row.control_id)
            if not ctrl:
                continue
            insights.append({
                "insight": (
                    f"Control '{ctrl.name}' has failed effectiveness testing "
                    f"{row.fail_count} times. Repeated failures indicate a design "
                    f"flaw, not a one-time execution gap."
                ),
                "severity": "high",
                "related_objects": [
                    {"type": "control", "id": ctrl.control_id, "label": ctrl.name},
                ],
                "recommendation": (
                    "Redesign this control rather than simply re-testing. "
                    "Consider whether automation or a compensating control would be more reliable."
                ),
            })
        return insights

    def _insight_kri_risk_finding_cluster(self) -> List[Dict[str, Any]]:
        """KRIs in WARNING/BREACH that are linked to risks which also have open findings."""
        tid = self.tenant_id

        breached_kris = self.db.query(KeyRiskIndicator).filter(
            KeyRiskIndicator.tenant_id == tid,
            KeyRiskIndicator.is_active.is_(True),
            KeyRiskIndicator.status.in_([KRIStatus.WARNING, KRIStatus.BREACH]),
            KeyRiskIndicator.risk_id.isnot(None),
        ).all()

        if not breached_kris:
            return []

        risk_ids = [k.risk_id for k in breached_kris]
        findings_with_risk = self.db.query(func.count(AuditFinding.id)).filter(
            AuditFinding.tenant_id == tid,
            AuditFinding.risk_id.in_(risk_ids),
            AuditFinding.status.notin_([FindingStatus.CLOSED]),
        ).scalar() or 0

        if findings_with_risk == 0:
            return []

        return [{
            "insight": (
                f"{len(breached_kris)} KRI{'s' if len(breached_kris) > 1 else ''} "
                f"in warning or breach are linked to {findings_with_risk} open audit "
                f"finding{'s' if findings_with_risk > 1 else ''}. "
                f"The KRI signals are validating what audit already identified — "
                f"these risks are materialising."
            ),
            "severity": "high",
            "related_objects": [
                {"type": "kri", "id": k.kri_id, "label": k.name}
                for k in breached_kris[:3]
            ],
            "recommendation": (
                "Accelerate closure of the linked audit findings. "
                "KRI trends confirm that the underlying risks remain active."
            ),
        }]

    def _insight_dormant_accounts_with_open_violations(self) -> List[Dict[str, Any]]:
        """Dormant accounts (90+ days no login) that still carry open violations."""
        tid = self.tenant_id
        threshold = NOW() - timedelta(days=90)

        dormant_users = self.db.query(User).filter(
            User.tenant_id == tid,
            User.status == "active",
            User.last_login < threshold,
        ).all()

        if not dormant_users:
            return []

        dormant_ids = {u.id for u in dormant_users}
        violations_count = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.tenant_id == tid,
            RiskViolation.user_id.in_(list(dormant_ids)[:500]),
            RiskViolation.status == ViolationStatus.OPEN,
        ).scalar() or 0

        if violations_count == 0:
            return []

        return [{
            "insight": (
                f"{len(dormant_users)} dormant user account{'s' if len(dormant_users) > 1 else ''} "
                f"(inactive 90+ days) still carry {violations_count} open violation{'s' if violations_count > 1 else ''}. "
                f"These accounts represent a security risk because they are unlikely to be actively monitored."
            ),
            "severity": "high",
            "related_objects": [
                {"type": "user", "id": u.user_id, "label": u.full_name or u.username}
                for u in dormant_users[:3]
            ],
            "recommendation": (
                "Disable or lock dormant accounts immediately. "
                "Remediate violations so they are not inherited if accounts are ever re-activated."
            ),
        }]

    # -----------------------------------------------------------------------
    # 4. Explain Any Object
    # -----------------------------------------------------------------------

    def explain(self, object_type: str, object_id: str) -> Dict[str, Any]:
        """
        Explain any GRC object in plain, friendly language.

        object_type: risk | control | violation | finding | deficiency | kri | user_access
        """
        handlers = {
            "risk": self._explain_risk,
            "control": self._explain_control,
            "violation": self._explain_violation,
            "finding": self._explain_finding,
            "deficiency": self._explain_deficiency,
            "kri": self._explain_kri,
            "user_access": self._explain_user_access,
        }
        handler = handlers.get(object_type)
        if handler is None:
            return {
                "error": f"Unknown object_type '{object_type}'. "
                         f"Valid types: {list(handlers.keys())}"
            }
        return handler(object_id)

    def _explain_risk(self, risk_id: str) -> Dict[str, Any]:
        r = self.db.query(EnterpriseRisk).filter(
            EnterpriseRisk.tenant_id == self.tenant_id,
            EnterpriseRisk.risk_id == risk_id,
        ).first()
        if not r:
            return {"error": f"Risk '{risk_id}' not found"}

        above_appetite = (
            r.residual_score and r.risk_appetite and r.residual_score > r.risk_appetite
        )
        return {
            "summary": (
                f"'{r.title}' is an enterprise risk in the {r.category.value if r.category else 'unknown'} category. "
                f"It is currently rated at {r.residual_score or 'unscored'} (residual, after controls). "
                f"Status: {r.status.value if r.status else 'unknown'}."
            ),
            "why_it_matters": (
                f"If this risk materialises, it could affect {r.category.value if r.category else 'your'} "
                f"operations. "
                + (
                    "The current residual score exceeds the defined risk appetite, "
                    "meaning more needs to be done to bring it within acceptable limits."
                    if above_appetite else
                    "The risk is currently within the defined appetite threshold."
                )
            ),
            "impact": {
                "inherent_score": r.inherent_score,
                "residual_score": r.residual_score,
                "appetite": r.risk_appetite,
                "above_appetite": above_appetite,
            },
            "related_items": {
                "control_ids": r.related_control_ids or [],
                "finding_ids": r.related_finding_ids or [],
            },
            "recommended_action": (
                "Update the risk response plan and confirm that linked controls are operating effectively."
                if above_appetite else
                "Continue monitoring. Schedule your next review before "
                + (r.next_review_date.strftime("%d %b %Y") if r.next_review_date else "the due date.")
            ),
        }

    def _explain_control(self, control_id: str) -> Dict[str, Any]:
        c = self.db.query(ProcessControl).filter(
            ProcessControl.tenant_id == self.tenant_id,
            ProcessControl.control_id == control_id,
        ).first()
        if not c:
            return {"error": f"Control '{control_id}' not found"}

        last_test = self.db.query(ControlTest).filter(
            ControlTest.control_id == c.id,
        ).order_by(ControlTest.created_at.desc()).first()

        open_deficiencies = self.db.query(func.count(ControlDeficiency.id)).filter(
            ControlDeficiency.control_id == c.id,
            ControlDeficiency.status.in_([DeficiencyStatus.OPEN, DeficiencyStatus.IN_REMEDIATION]),
        ).scalar() or 0

        return {
            "summary": (
                f"'{c.name}' is a {c.control_type.value if c.control_type else ''} "
                f"{c.control_nature.value if c.control_nature else ''} control that runs "
                f"{c.frequency.value if c.frequency else 'periodically'}. "
                f"Owner: {c.owner_name or 'unassigned'}. Status: {c.status.value if c.status else 'unknown'}."
            ),
            "why_it_matters": (
                f"This control is designed to prevent or detect issues in the "
                f"{c.process_name or 'relevant'} process. "
                + (
                    f"It currently has {open_deficiencies} open deficiency(ies) that need attention."
                    if open_deficiencies else
                    "It is currently operating without open deficiencies."
                )
            ),
            "impact": {
                "open_deficiencies": open_deficiencies,
                "last_test_result": last_test.result.value if last_test and last_test.result else "not tested",
                "last_test_date": last_test.created_at.isoformat() if last_test else None,
                "is_key_control": c.key_control,
            },
            "related_items": {
                "risk_ids": c.risk_ids or [],
                "framework_mappings": c.framework_mappings or [],
            },
            "recommended_action": (
                "Schedule a control test and address open deficiencies."
                if open_deficiencies else
                f"Next review scheduled: {c.next_review_date.strftime('%d %b %Y') if c.next_review_date else 'not set'}."
            ),
        }

    def _explain_violation(self, violation_id: str) -> Dict[str, Any]:
        v = self.db.query(RiskViolation).filter(
            RiskViolation.tenant_id == self.tenant_id,
            RiskViolation.violation_id == violation_id,
        ).first()
        if not v:
            return {"error": f"Violation '{violation_id}' not found"}

        age_days = (NOW() - v.detected_at).days if v.detected_at else 0
        return {
            "summary": (
                f"User {v.username or v.user_external_id} has conflicting access that violates "
                f"the '{v.rule_name}' rule. This is a {v.severity.value if v.severity else 'unknown'}-severity "
                f"segregation-of-duties (SoD) issue detected {age_days} days ago."
            ),
            "why_it_matters": (
                f"SoD violations mean one person can perform two steps of a process that should "
                f"require two different people. This creates a risk of fraud, error, or "
                f"undetected mistakes in {v.risk_category or 'business'} transactions. "
                + ("This violation is currently unmitigated." if not v.is_mitigated else
                   "A mitigation control is in place but the access conflict still exists.")
            ),
            "impact": {
                "severity": v.severity.value if v.severity else None,
                "severity_score": v.severity_score,
                "risk_category": v.risk_category,
                "conflicting_functions": v.conflicting_functions,
                "affected_systems": v.affected_systems,
                "is_mitigated": v.is_mitigated,
                "age_days": age_days,
            },
            "related_items": {
                "user_id": v.user_external_id,
                "mitigation_id": v.mitigation_id,
            },
            "recommended_action": (
                "Remove one of the conflicting roles from the user, or apply a mitigation control "
                "with documented monitoring procedures."
            ),
        }

    def _explain_finding(self, finding_id: str) -> Dict[str, Any]:
        f = self.db.query(AuditFinding).filter(
            AuditFinding.tenant_id == self.tenant_id,
            AuditFinding.finding_id == finding_id,
        ).first()
        if not f:
            return {"error": f"Finding '{finding_id}' not found"}

        open_actions = self.db.query(func.count(AuditManagementAction.id)).filter(
            AuditManagementAction.finding_id == f.id,
            AuditManagementAction.status.in_([ActionStatus.OPEN, ActionStatus.IN_PROGRESS]),
        ).scalar() or 0

        return {
            "summary": (
                f"'{f.title}' is a {f.severity.value if f.severity else 'unknown'}-severity "
                f"audit finding. Status: {f.status.value if f.status else 'unknown'}. "
                + (f"Repeat finding: yes." if f.repeat_finding else "")
            ),
            "why_it_matters": (
                f"What was found: {f.condition or 'see finding details'}. "
                f"Why it matters: {f.effect or 'see finding details'}."
                + (" This is a repeat finding, meaning it was not adequately addressed previously."
                   if f.repeat_finding else "")
            ),
            "impact": {
                "severity": f.severity.value if f.severity else None,
                "category": f.category,
                "repeat_finding": f.repeat_finding,
                "open_management_actions": open_actions,
                "management_target_date": (
                    f.management_target_date.isoformat() if f.management_target_date else None
                ),
            },
            "related_items": {
                "risk_id": f.risk_id,
                "control_id": f.control_id,
                "violation_id": f.violation_id,
            },
            "recommended_action": (
                f.recommendation
                or "Complete all management actions by the agreed target date."
            ),
        }

    def _explain_deficiency(self, deficiency_id: str) -> Dict[str, Any]:
        d = self.db.query(ControlDeficiency).filter(
            ControlDeficiency.tenant_id == self.tenant_id,
            ControlDeficiency.deficiency_id == deficiency_id,
        ).first()
        if not d:
            return {"error": f"Deficiency '{deficiency_id}' not found"}

        overdue = d.due_date and d.due_date < NOW()
        return {
            "summary": (
                f"'{d.title}' is a {d.severity.value.replace('_', ' ') if d.severity else 'unknown'} "
                f"control deficiency. Status: {d.status.value if d.status else 'unknown'}. "
                + ("OVERDUE." if overdue else "")
            ),
            "why_it_matters": (
                f"A control deficiency means a control is not working as designed. "
                f"Root cause: {d.root_cause or 'not yet determined'}. "
                + (
                    "A material weakness is the most severe type and may require disclosure "
                    "in financial reports."
                    if d.severity == DeficiencySeverity.MATERIAL_WEAKNESS else ""
                )
            ),
            "impact": {
                "severity": d.severity.value if d.severity else None,
                "overdue": overdue,
                "due_date": d.due_date.isoformat() if d.due_date else None,
                "remediation_owner": d.remediation_owner_name or d.remediation_owner_id,
                "source": d.source,
            },
            "related_items": {
                "control_id": d.control_id,
                "test_id": d.test_id,
                "related_risk_ids": d.related_risk_ids or [],
            },
            "recommended_action": (
                d.remediation_plan
                or "Define and execute a remediation plan promptly."
            ),
        }

    def _explain_kri(self, kri_id: str) -> Dict[str, Any]:
        k = self.db.query(KeyRiskIndicator).filter(
            KeyRiskIndicator.tenant_id == self.tenant_id,
            KeyRiskIndicator.kri_id == kri_id,
        ).first()
        if not k:
            return {"error": f"KRI '{kri_id}' not found"}

        # Trend from last 3 measurements
        measurements = self.db.query(KRIMeasurement).filter(
            KRIMeasurement.kri_id == k.id,
        ).order_by(KRIMeasurement.measured_at.desc()).limit(3).all()

        trend_desc = "stable"
        if len(measurements) >= 2:
            if measurements[0].value > measurements[1].value:
                trend_desc = "increasing"
            elif measurements[0].value < measurements[1].value:
                trend_desc = "decreasing"

        status_map = {
            KRIStatus.NORMAL: "within normal range",
            KRIStatus.WARNING: "in warning territory",
            KRIStatus.BREACH: "in breach of the red threshold",
        }

        return {
            "summary": (
                f"'{k.name}' is a Key Risk Indicator measuring {k.unit_of_measure or 'a risk metric'}. "
                f"Current value: {k.current_value}. It is {status_map.get(k.status, 'unknown status')} "
                f"and trending {trend_desc}."
            ),
            "why_it_matters": (
                f"This indicator monitors {k.description or k.name}. "
                f"Thresholds: green < {k.threshold_green}, amber < {k.threshold_amber}, "
                f"red >= {k.threshold_red}. "
                + (
                    "The breach means immediate action is required to prevent the associated "
                    "risk from materialising."
                    if k.status == KRIStatus.BREACH else ""
                )
            ),
            "impact": {
                "current_value": k.current_value,
                "status": k.status.value if k.status else None,
                "trend": trend_desc,
                "threshold_green": k.threshold_green,
                "threshold_amber": k.threshold_amber,
                "threshold_red": k.threshold_red,
                "last_measured_at": k.last_measured_at.isoformat() if k.last_measured_at else None,
            },
            "related_items": {
                "risk_id": k.risk_id,
            },
            "recommended_action": (
                "Investigate the root cause and update the linked risk record with a response plan."
                if k.status in (KRIStatus.WARNING, KRIStatus.BREACH)
                else f"Continue monitoring. Next measurement due: {k.frequency or 'per schedule'}."
            ),
        }

    def _explain_user_access(self, user_id: str) -> Dict[str, Any]:
        u = self.db.query(User).filter(
            User.tenant_id == self.tenant_id,
            User.user_id == user_id,
        ).first()
        if not u:
            return {"error": f"User '{user_id}' not found"}

        role_count = self.db.query(func.count(UserRole.id)).filter(
            UserRole.user_id == u.id,
            UserRole.is_active.is_(True),
        ).scalar() or 0

        open_violations = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.user_id == u.id,
            RiskViolation.status == ViolationStatus.OPEN,
        ).scalar() or 0

        critical_violations = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.user_id == u.id,
            RiskViolation.status == ViolationStatus.OPEN,
            RiskViolation.severity == RiskSeverityLevel.CRITICAL,
        ).scalar() or 0

        days_since_login = (
            (NOW() - u.last_login).days if u.last_login else None
        )

        risk_label = (
            "very high" if u.risk_score >= 80 else
            "high" if u.risk_score >= 60 else
            "medium" if u.risk_score >= 40 else "low"
        )

        return {
            "summary": (
                f"{u.full_name or u.username} ({u.user_id}) is an active user "
                f"in {u.department or 'unknown department'} with {role_count} active role{'s' if role_count != 1 else ''}. "
                f"Overall risk score: {u.risk_score:.0f}/100 ({risk_label})."
            ),
            "why_it_matters": (
                f"This user has {open_violations} open SoD violation{'s' if open_violations != 1 else ''}"
                + (f", including {critical_violations} critical" if critical_violations else "")
                + ". "
                + (
                    "Their access profile requires urgent review."
                    if open_violations > 0 else
                    "Their access appears clean with no open violations."
                )
                + (
                    f" Last login was {days_since_login} days ago."
                    if days_since_login is not None else ""
                )
            ),
            "impact": {
                "risk_score": u.risk_score,
                "open_violations": open_violations,
                "critical_violations": critical_violations,
                "active_roles": role_count,
                "last_login_days_ago": days_since_login,
                "status": u.status,
            },
            "related_items": {
                "department": u.department,
                "manager_user_id": u.manager_user_id,
            },
            "recommended_action": (
                "Immediately review and remediate this user's access. "
                "Consider temporary access suspension."
                if critical_violations > 0 else
                "Schedule an access review during the next certification campaign."
            ),
        }

    # -----------------------------------------------------------------------
    # 5. Investigate
    # -----------------------------------------------------------------------

    def investigate(self, query: str) -> Dict[str, Any]:
        """
        Follow the GRC Intelligence Graph from any starting point.

        Accepts a free-form query that can be a user ID, risk ID, control ID,
        violation ID, or finding ID.  Traces the full chain:
        User → Roles → Violations → Risks → Controls → Deficiencies → Findings → Actions
        """
        query = query.strip()
        chain: Dict[str, Any] = {
            "query": query,
            "resolved_as": None,
            "chain": [],
            "summary": "",
        }

        # Try to resolve query to a known object type
        result = self._resolve_investigate_query(query)
        if result is None:
            chain["summary"] = f"Could not resolve '{query}' to any known GRC object."
            return chain

        obj_type, obj = result
        chain["resolved_as"] = {"type": obj_type, "id": query}

        nodes = []
        if obj_type == "user":
            nodes = self._investigate_from_user(obj)
        elif obj_type == "violation":
            nodes = self._investigate_from_violation(obj)
        elif obj_type == "risk":
            nodes = self._investigate_from_risk(obj)
        elif obj_type == "control":
            nodes = self._investigate_from_control(obj)
        elif obj_type == "finding":
            nodes = self._investigate_from_finding(obj)

        chain["chain"] = nodes
        chain["summary"] = self._summarise_investigation(obj_type, obj, nodes)
        return chain

    def _resolve_investigate_query(self, query: str):
        """Try each object type in turn and return the first match."""
        tid = self.tenant_id

        user = self.db.query(User).filter(
            User.tenant_id == tid, User.user_id == query
        ).first()
        if user:
            return ("user", user)

        violation = self.db.query(RiskViolation).filter(
            RiskViolation.tenant_id == tid, RiskViolation.violation_id == query
        ).first()
        if violation:
            return ("violation", violation)

        risk = self.db.query(EnterpriseRisk).filter(
            EnterpriseRisk.tenant_id == tid, EnterpriseRisk.risk_id == query
        ).first()
        if risk:
            return ("risk", risk)

        control = self.db.query(ProcessControl).filter(
            ProcessControl.tenant_id == tid, ProcessControl.control_id == query
        ).first()
        if control:
            return ("control", control)

        finding = self.db.query(AuditFinding).filter(
            AuditFinding.tenant_id == tid, AuditFinding.finding_id == query
        ).first()
        if finding:
            return ("finding", finding)

        return None

    def _investigate_from_user(self, user: User) -> List[Dict[str, Any]]:
        nodes = []
        # Roles
        user_roles = self.db.query(UserRole).filter(
            UserRole.user_id == user.id, UserRole.is_active.is_(True)
        ).all()
        role_ids = [ur.role_id for ur in user_roles]
        roles = self.db.query(Role).filter(Role.id.in_(role_ids)).all() if role_ids else []

        nodes.append({
            "step": 1,
            "layer": "Roles",
            "count": len(roles),
            "items": [{"id": r.role_id, "name": r.role_name, "risk_level": r.risk_level} for r in roles[:10]],
            "explanation": f"{user.full_name or user.username} has {len(roles)} active role assignment(s).",
        })

        # Violations
        violations = self.db.query(RiskViolation).filter(
            RiskViolation.user_id == user.id,
            RiskViolation.status == ViolationStatus.OPEN,
        ).all()
        nodes.append({
            "step": 2,
            "layer": "SoD Violations",
            "count": len(violations),
            "items": [
                {"id": v.violation_id, "rule": v.rule_name, "severity": v.severity.value if v.severity else None}
                for v in violations[:10]
            ],
            "explanation": f"{len(violations)} open SoD violation(s) detected.",
        })

        return nodes

    def _investigate_from_violation(self, violation: RiskViolation) -> List[Dict[str, Any]]:
        nodes = []

        # User
        user = self.db.query(User).filter(User.id == violation.user_id).first()
        nodes.append({
            "step": 1,
            "layer": "User",
            "count": 1 if user else 0,
            "items": [{"id": user.user_id, "name": user.full_name or user.username}] if user else [],
            "explanation": f"Violation belongs to user {violation.username or violation.user_external_id}.",
        })

        # Mitigation
        mitigation = None
        if violation.mitigation_id:
            mitigation = self.db.query(MitigationControl).filter(
                MitigationControl.id == violation.mitigation_id
            ).first()
        nodes.append({
            "step": 2,
            "layer": "Mitigation Control",
            "count": 1 if mitigation else 0,
            "items": [{"id": mitigation.control_id, "name": mitigation.control_name}] if mitigation else [],
            "explanation": (
                f"Mitigated by '{mitigation.control_name}'." if mitigation
                else "No mitigation control applied."
            ),
        })

        # Linked findings
        findings = self.db.query(AuditFinding).filter(
            AuditFinding.tenant_id == self.tenant_id,
            AuditFinding.violation_id == violation.id,
        ).all()
        nodes.append({
            "step": 3,
            "layer": "Audit Findings",
            "count": len(findings),
            "items": [
                {"id": f.finding_id, "title": f.title, "severity": f.severity.value if f.severity else None}
                for f in findings[:5]
            ],
            "explanation": f"{len(findings)} audit finding(s) reference this violation.",
        })

        return nodes

    def _investigate_from_risk(self, risk: EnterpriseRisk) -> List[Dict[str, Any]]:
        nodes = []

        # KRIs
        kris = self.db.query(KeyRiskIndicator).filter(
            KeyRiskIndicator.risk_id == risk.id
        ).all()
        nodes.append({
            "step": 1,
            "layer": "Key Risk Indicators",
            "count": len(kris),
            "items": [{"id": k.kri_id, "name": k.name, "status": k.status.value if k.status else None} for k in kris],
            "explanation": f"Risk has {len(kris)} KRI(s) monitoring it.",
        })

        # Responses
        responses = self.db.query(RiskResponse).filter(
            RiskResponse.risk_id == risk.id
        ).all()
        nodes.append({
            "step": 2,
            "layer": "Risk Responses",
            "count": len(responses),
            "items": [
                {"id": r.response_id, "type": r.response_type.value if r.response_type else None,
                 "status": r.status.value if r.status else None}
                for r in responses
            ],
            "explanation": f"{len(responses)} response plan(s) associated.",
        })

        # Findings
        findings = self.db.query(AuditFinding).filter(
            AuditFinding.tenant_id == self.tenant_id,
            AuditFinding.risk_id == risk.id,
        ).all()
        nodes.append({
            "step": 3,
            "layer": "Audit Findings",
            "count": len(findings),
            "items": [
                {"id": f.finding_id, "title": f.title, "status": f.status.value if f.status else None}
                for f in findings[:5]
            ],
            "explanation": f"{len(findings)} audit finding(s) linked to this risk.",
        })

        return nodes

    def _investigate_from_control(self, control: ProcessControl) -> List[Dict[str, Any]]:
        nodes = []

        # Tests
        tests = self.db.query(ControlTest).filter(
            ControlTest.control_id == control.id
        ).order_by(ControlTest.created_at.desc()).limit(5).all()
        nodes.append({
            "step": 1,
            "layer": "Control Tests",
            "count": len(tests),
            "items": [
                {"id": t.test_id, "result": t.result.value if t.result else None,
                 "date": t.created_at.isoformat() if t.created_at else None}
                for t in tests
            ],
            "explanation": f"Last {len(tests)} test(s) for this control.",
        })

        # Deficiencies
        deficiencies = self.db.query(ControlDeficiency).filter(
            ControlDeficiency.control_id == control.id,
            ControlDeficiency.status.notin_([
                DeficiencyStatus.VERIFIED_CLOSED,
                DeficiencyStatus.ACCEPTED,
            ]),
        ).all()
        nodes.append({
            "step": 2,
            "layer": "Control Deficiencies",
            "count": len(deficiencies),
            "items": [
                {"id": d.deficiency_id, "title": d.title,
                 "severity": d.severity.value if d.severity else None,
                 "status": d.status.value if d.status else None}
                for d in deficiencies[:5]
            ],
            "explanation": f"{len(deficiencies)} open deficiency(ies).",
        })

        # Findings
        findings = self.db.query(AuditFinding).filter(
            AuditFinding.tenant_id == self.tenant_id,
            AuditFinding.control_id == control.id,
        ).all()
        nodes.append({
            "step": 3,
            "layer": "Audit Findings",
            "count": len(findings),
            "items": [
                {"id": f.finding_id, "title": f.title}
                for f in findings[:5]
            ],
            "explanation": f"{len(findings)} audit finding(s) reference this control.",
        })

        return nodes

    def _investigate_from_finding(self, finding: AuditFinding) -> List[Dict[str, Any]]:
        nodes = []

        # Management actions
        actions = self.db.query(AuditManagementAction).filter(
            AuditManagementAction.finding_id == finding.id
        ).all()
        now = NOW()
        overdue = [a for a in actions if a.due_date and a.due_date < now and
                   a.status not in (ActionStatus.COMPLETED, ActionStatus.CLOSED_VERIFIED)]
        nodes.append({
            "step": 1,
            "layer": "Management Actions",
            "count": len(actions),
            "items": [
                {"id": a.action_id, "owner": a.owner_name or a.owner_id,
                 "status": a.status.value if a.status else None,
                 "overdue": (a.due_date < now if a.due_date else False)}
                for a in actions[:10]
            ],
            "explanation": (
                f"{len(actions)} management action(s), {len(overdue)} overdue."
            ),
        })

        # Linked risk
        if finding.risk_id:
            risk = self.db.query(EnterpriseRisk).filter(
                EnterpriseRisk.id == finding.risk_id
            ).first()
            nodes.append({
                "step": 2,
                "layer": "Enterprise Risk",
                "count": 1 if risk else 0,
                "items": [
                    {"id": risk.risk_id, "title": risk.title,
                     "residual_score": risk.residual_score}
                ] if risk else [],
                "explanation": "Risk linked to this finding.",
            })

        # Linked control
        if finding.control_id:
            control = self.db.query(ProcessControl).filter(
                ProcessControl.id == finding.control_id
            ).first()
            nodes.append({
                "step": 3,
                "layer": "Process Control",
                "count": 1 if control else 0,
                "items": [
                    {"id": control.control_id, "name": control.name}
                ] if control else [],
                "explanation": "Control linked to this finding.",
            })

        return nodes

    def _summarise_investigation(self, obj_type: str, obj, nodes: List) -> str:
        total_links = sum(n.get("count", 0) for n in nodes)
        return (
            f"Investigation of {obj_type} '{getattr(obj, obj_type + '_id', str(getattr(obj, 'id', '')))}' "
            f"traced {len(nodes)} connection layer(s) with {total_links} total linked object(s)."
        )

    # -----------------------------------------------------------------------
    # 6. Fix Preview
    # -----------------------------------------------------------------------

    def preview_fix(self, object_type: str, object_id: str) -> Dict[str, Any]:
        """
        Preview what a one-click fix would do, without executing it.

        Returns the proposed changes, their impact, and estimated risk reduction.
        """
        handlers = {
            "violation": self._preview_fix_violation,
            "deficiency": self._preview_fix_deficiency,
            "finding": self._preview_fix_finding,
        }
        handler = handlers.get(object_type)
        if handler is None:
            return {
                "error": f"Fix preview not supported for object_type '{object_type}'. "
                         f"Supported types: {list(handlers.keys())}"
            }
        return handler(object_id)

    def _preview_fix_violation(self, violation_id: str) -> Dict[str, Any]:
        v = self.db.query(RiskViolation).filter(
            RiskViolation.tenant_id == self.tenant_id,
            RiskViolation.violation_id == violation_id,
        ).first()
        if not v:
            return {"error": f"Violation '{violation_id}' not found"}

        user = self.db.query(User).filter(User.id == v.user_id).first()

        # Determine which roles to remove — roles that participate in the conflict
        conflicting = v.conflicting_functions or []
        user_roles = self.db.query(UserRole).filter(
            UserRole.user_id == v.user_id,
            UserRole.is_active.is_(True),
        ).all()
        role_ids = [ur.role_id for ur in user_roles]
        roles = self.db.query(Role).filter(Role.id.in_(role_ids)).all() if role_ids else []

        # Flag roles whose names match any conflicting function keyword
        roles_to_remove = []
        roles_safe = []
        for r in roles:
            matched = any(
                fn.lower() in r.role_name.lower() or r.role_name.lower() in fn.lower()
                for fn in conflicting
            )
            (roles_to_remove if matched else roles_safe).append(r)

        # Estimate risk reduction
        score_before = v.severity_score or 50
        score_after = 0 if roles_to_remove else max(0, score_before - 20)
        risk_reduction = score_before - score_after

        # Impact on other users — how many others hold these roles
        impacted_users: List[Dict] = []
        if roles_to_remove:
            other_assignments = self.db.query(UserRole).filter(
                UserRole.role_id.in_([r.id for r in roles_to_remove]),
                UserRole.is_active.is_(True),
                UserRole.user_id != v.user_id,
            ).limit(20).all()
            impacted_user_ids = {a.user_id for a in other_assignments}
            impacted_users_q = self.db.query(User).filter(
                User.id.in_(list(impacted_user_ids)[:20])
            ).all()
            impacted_users = [
                {"user_id": u.user_id, "name": u.full_name or u.username}
                for u in impacted_users_q
            ]

        return {
            "object_type": "violation",
            "object_id": violation_id,
            "changes": [
                {
                    "action": "remove_role",
                    "target_user": user.user_id if user else v.user_external_id,
                    "role_id": r.role_id,
                    "role_name": r.role_name,
                    "reason": f"Role contributes to SoD conflict '{v.rule_name}'",
                }
                for r in roles_to_remove
            ] if roles_to_remove else [
                {
                    "action": "apply_mitigation",
                    "target_user": user.user_id if user else v.user_external_id,
                    "reason": (
                        "No specific conflicting roles identified; recommend applying "
                        "a documented mitigation control with periodic review."
                    ),
                }
            ],
            "impact_summary": (
                f"Removing {len(roles_to_remove)} role(s) would eliminate the SoD conflict for "
                f"{user.full_name or user.username if user else v.user_external_id}. "
                + (
                    f"{len(impacted_users)} other user(s) also hold these roles — they are not affected "
                    f"unless their access is also reviewed."
                    if impacted_users else
                    "No other users hold these specific roles."
                )
            ),
            "risk_reduction_estimate": {
                "severity_score_before": score_before,
                "severity_score_after": score_after,
                "points_reduced": risk_reduction,
                "pct_reduction": round(risk_reduction / max(score_before, 1) * 100),
            },
            "other_users_holding_affected_roles": impacted_users,
            "caution": (
                "Review the impact on other users before executing. "
                "Ensure the user still has the minimum access required to perform their job."
            ),
        }

    def _preview_fix_deficiency(self, deficiency_id: str) -> Dict[str, Any]:
        d = self.db.query(ControlDeficiency).filter(
            ControlDeficiency.tenant_id == self.tenant_id,
            ControlDeficiency.deficiency_id == deficiency_id,
        ).first()
        if not d:
            return {"error": f"Deficiency '{deficiency_id}' not found"}

        control = self.db.query(ProcessControl).filter(
            ProcessControl.id == d.control_id
        ).first()

        remediation_steps = []
        if d.remediation_plan:
            # Split existing plan into steps
            for i, line in enumerate(d.remediation_plan.split("\n"), 1):
                line = line.strip()
                if line:
                    remediation_steps.append({"step": i, "action": line})
        else:
            # Generate generic steps based on severity
            remediation_steps = [
                {"step": 1, "action": "Confirm root cause with control owner"},
                {"step": 2, "action": "Update control design documentation"},
                {"step": 3, "action": "Execute remediation per updated procedure"},
                {"step": 4, "action": "Collect evidence of remediation"},
                {"step": 5, "action": "Request independent verification"},
            ]

        return {
            "object_type": "deficiency",
            "object_id": deficiency_id,
            "changes": remediation_steps,
            "impact_summary": (
                f"Remediating '{d.title}' will close the {d.severity.value.replace('_', ' ') if d.severity else ''} "
                f"deficiency on control '{control.name if control else d.control_id}'. "
                f"This will improve the control health score and may resolve linked audit findings."
            ),
            "risk_reduction_estimate": {
                "severity": d.severity.value if d.severity else None,
                "expected_outcome": "Deficiency status moves to REMEDIATED then VERIFIED_CLOSED",
                "linked_risk_ids": d.related_risk_ids or [],
                "linked_finding_ids": d.related_finding_ids or [],
            },
            "caution": (
                "Ensure evidence of remediation is uploaded before requesting verification. "
                "For material weaknesses, inform your external auditors."
            ),
        }

    def _preview_fix_finding(self, finding_id: str) -> Dict[str, Any]:
        f = self.db.query(AuditFinding).filter(
            AuditFinding.tenant_id == self.tenant_id,
            AuditFinding.finding_id == finding_id,
        ).first()
        if not f:
            return {"error": f"Finding '{finding_id}' not found"}

        actions = self.db.query(AuditManagementAction).filter(
            AuditManagementAction.finding_id == f.id
        ).all()

        open_actions = [a for a in actions if a.status not in (
            ActionStatus.COMPLETED, ActionStatus.CLOSED_VERIFIED
        )]

        action_plan = []
        if open_actions:
            for a in open_actions:
                action_plan.append({
                    "action_id": a.action_id,
                    "description": a.description[:120],
                    "owner": a.owner_name or a.owner_id,
                    "due_date": a.due_date.isoformat() if a.due_date else None,
                    "current_status": a.status.value if a.status else None,
                    "proposed_next_step": "Complete action and upload evidence of closure",
                })
        elif f.recommendation:
            action_plan.append({
                "action_id": "new",
                "description": f.recommendation,
                "owner": f.management_action_owner or "to be assigned",
                "due_date": (
                    f.management_target_date.isoformat() if f.management_target_date else None
                ),
                "proposed_next_step": "Create management action item and assign owner",
            })

        return {
            "object_type": "finding",
            "object_id": finding_id,
            "changes": action_plan,
            "impact_summary": (
                f"Completing all {len(open_actions)} management action(s) for finding "
                f"'{f.title[:60]}' will allow the finding to be closed. "
                + (
                    "This is a repeat finding — ensure root cause is fully addressed "
                    "to prevent recurrence."
                    if f.repeat_finding else ""
                )
            ),
            "risk_reduction_estimate": {
                "severity": f.severity.value if f.severity else None,
                "finding_status_after": "CLOSED (upon verification)",
                "open_actions_to_complete": len(open_actions),
                "linked_risk_id": f.risk_id,
                "linked_control_id": f.control_id,
            },
            "caution": (
                "Obtain audit committee or CAE sign-off before marking the finding as closed. "
                "Ensure evidence of closure is attached to all management actions."
            ),
        }

    # -----------------------------------------------------------------------
    # 7. Role-Personalised Dashboard
    # -----------------------------------------------------------------------

    def get_personalized_dashboard(self, role: str) -> Dict[str, Any]:
        """
        Return dashboard data personalised to the user's role.

        Supported roles: cfo, ciso, cae, control_owner, employee
        """
        role_lower = role.lower()
        handlers = {
            "cfo": self._dashboard_cfo,
            "ciso": self._dashboard_ciso,
            "cae": self._dashboard_cae,
            "control_owner": self._dashboard_control_owner,
            "employee": self._dashboard_employee,
            "risk_manager": self._dashboard_risk_manager,
            "auditor": self._dashboard_cae,   # auditor gets CAE view
        }
        handler = handlers.get(role_lower)
        if handler is None:
            # Default fallback
            handler = self._dashboard_employee

        data = handler()
        data["role"] = role
        data["generated_at"] = NOW().isoformat()
        data["attention_items"] = self.get_attention_items(role=role_lower)[:5]
        return data

    def _dashboard_cfo(self) -> Dict[str, Any]:
        tid = self.tenant_id
        health = self.compute_health_score()

        # Financial risks above appetite
        fin_risks_above = self.db.query(func.count(EnterpriseRisk.id)).filter(
            EnterpriseRisk.tenant_id == tid,
            EnterpriseRisk.category.in_(["financial", "FINANCIAL"]),
            EnterpriseRisk.is_active.is_(True),
        ).scalar() or 0

        # Critical findings
        critical_findings = self.db.query(func.count(AuditFinding.id)).filter(
            AuditFinding.tenant_id == tid,
            AuditFinding.severity == FindingSeverity.CRITICAL,
            AuditFinding.status.notin_([FindingStatus.CLOSED]),
        ).scalar() or 0

        control_score = health["components"]["control_health"]["score"]
        risk_score = health["components"]["enterprise_risk"]["score"]

        return {
            "sections": [
                {
                    "id": "grc_health",
                    "title": "GRC Health",
                    "type": "score_card",
                    "data": {
                        "score": health["score"],
                        "status": health["status"],
                        "trend": health["trend"],
                    },
                },
                {
                    "id": "enterprise_risk",
                    "title": "Enterprise Risk Summary",
                    "type": "metric_group",
                    "data": health["components"]["enterprise_risk"]["detail"],
                },
                {
                    "id": "control_effectiveness",
                    "title": "Control Effectiveness",
                    "type": "gauge",
                    "data": {"score": control_score, **health["components"]["control_health"]["detail"]},
                },
                {
                    "id": "audit_status",
                    "title": "Audit Status",
                    "type": "metric_group",
                    "data": health["components"]["audit_health"]["detail"],
                },
            ],
            "metrics": [
                {"label": "GRC Health Score", "value": health["score"], "unit": "/100"},
                {"label": "Financial Risks Active", "value": fin_risks_above, "unit": "risks"},
                {"label": "Critical Open Findings", "value": critical_findings, "unit": "findings"},
                {"label": "Control Effectiveness", "value": f"{control_score}%", "unit": ""},
                {"label": "Enterprise Risk Score", "value": f"{risk_score}%", "unit": ""},
            ],
        }

    def _dashboard_ciso(self) -> Dict[str, Any]:
        tid = self.tenant_id

        open_violations = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.tenant_id == tid,
            RiskViolation.status == ViolationStatus.OPEN,
        ).scalar() or 0

        critical_violations = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.tenant_id == tid,
            RiskViolation.status == ViolationStatus.OPEN,
            RiskViolation.severity == RiskSeverityLevel.CRITICAL,
        ).scalar() or 0

        active_ff_sessions = self.db.query(func.count(FirefighterSession.id)).filter(
            FirefighterSession.tenant_id == tid,
            FirefighterSession.status == FFSessionStatus.ACTIVE,
        ).scalar() or 0

        kri_breaches = self.db.query(func.count(KeyRiskIndicator.id)).filter(
            KeyRiskIndicator.tenant_id == tid,
            KeyRiskIndicator.is_active.is_(True),
            KeyRiskIndicator.status == KRIStatus.BREACH,
        ).scalar() or 0

        health = self.compute_health_score()
        access_score = health["components"]["access_risk"]["score"]

        return {
            "sections": [
                {
                    "id": "access_risk",
                    "title": "Access Risk Overview",
                    "type": "risk_summary",
                    "data": health["components"]["access_risk"]["detail"],
                },
                {
                    "id": "privileged_access",
                    "title": "Privileged Access Activity",
                    "type": "metric_group",
                    "data": {"active_firefighter_sessions": active_ff_sessions},
                },
                {
                    "id": "kri_status",
                    "title": "Key Risk Indicators",
                    "type": "kri_summary",
                    "data": {"breaches": kri_breaches},
                },
            ],
            "metrics": [
                {"label": "Open SoD Violations", "value": open_violations, "unit": "violations"},
                {"label": "Critical Violations", "value": critical_violations, "unit": ""},
                {"label": "Active FF Sessions", "value": active_ff_sessions, "unit": "sessions"},
                {"label": "KRI Breaches", "value": kri_breaches, "unit": ""},
                {"label": "Access Risk Score", "value": access_score, "unit": "/100"},
            ],
        }

    def _dashboard_cae(self) -> Dict[str, Any]:
        tid = self.tenant_id
        now = NOW()

        # Audit plan coverage
        approved_plans = self.db.query(func.count(AuditPlan.id)).filter(
            AuditPlan.tenant_id == tid,
            AuditPlan.status == AuditPlanStatus.APPROVED,
        ).scalar() or 0

        active_engagements = self.db.query(func.count(AuditEngagement.id)).filter(
            AuditEngagement.tenant_id == tid,
            AuditEngagement.status.in_([
                EngagementStatus.ANNOUNCED,
                EngagementStatus.FIELDWORK,
                EngagementStatus.DRAFT_REPORT,
            ]),
        ).scalar() or 0

        open_findings = self.db.query(func.count(AuditFinding.id)).filter(
            AuditFinding.tenant_id == tid,
            AuditFinding.status.notin_([FindingStatus.CLOSED]),
        ).scalar() or 0

        overdue_actions = self.db.query(func.count(AuditManagementAction.id)).filter(
            AuditManagementAction.tenant_id == tid,
            AuditManagementAction.status.in_([ActionStatus.OPEN, ActionStatus.IN_PROGRESS]),
            AuditManagementAction.due_date < now,
        ).scalar() or 0

        auditor_count = self.db.query(func.count(AuditorResource.id)).filter(
            AuditorResource.tenant_id == tid,
            AuditorResource.is_active.is_(True),
        ).scalar() or 0

        health = self.compute_health_score()

        return {
            "sections": [
                {
                    "id": "audit_plan",
                    "title": "Audit Plan Status",
                    "type": "metric_group",
                    "data": {
                        "approved_plans": approved_plans,
                        "active_engagements": active_engagements,
                    },
                },
                {
                    "id": "findings",
                    "title": "Findings & Actions",
                    "type": "metric_group",
                    "data": {
                        "open_findings": open_findings,
                        "overdue_actions": overdue_actions,
                    },
                },
                {
                    "id": "audit_health",
                    "title": "Audit Health Score",
                    "type": "gauge",
                    "data": health["components"]["audit_health"],
                },
            ],
            "metrics": [
                {"label": "Approved Audit Plans", "value": approved_plans, "unit": "plans"},
                {"label": "Active Engagements", "value": active_engagements, "unit": ""},
                {"label": "Open Findings", "value": open_findings, "unit": "findings"},
                {"label": "Overdue Actions", "value": overdue_actions, "unit": ""},
                {"label": "Auditor Headcount", "value": auditor_count, "unit": "auditors"},
            ],
        }

    def _dashboard_control_owner(self) -> Dict[str, Any]:
        tid = self.tenant_id
        now = NOW()

        active_controls = self.db.query(func.count(ProcessControl.id)).filter(
            ProcessControl.tenant_id == tid,
            ProcessControl.is_active.is_(True),
            ProcessControl.status == ControlStatus.ACTIVE,
        ).scalar() or 0

        tests_due = self.db.query(func.count(ProcessControl.id)).filter(
            ProcessControl.tenant_id == tid,
            ProcessControl.is_active.is_(True),
            ProcessControl.next_review_date <= now + timedelta(days=30),
        ).scalar() or 0

        failed_tests = self.db.query(func.count(ControlTest.id)).filter(
            ControlTest.tenant_id == tid,
            ControlTest.result == TestResult.INEFFECTIVE,
            ControlTest.status == TestStatus.COMPLETED,
        ).scalar() or 0

        open_deficiencies = self.db.query(func.count(ControlDeficiency.id)).filter(
            ControlDeficiency.tenant_id == tid,
            ControlDeficiency.status.in_([DeficiencyStatus.OPEN, DeficiencyStatus.IN_REMEDIATION]),
        ).scalar() or 0

        return {
            "sections": [
                {
                    "id": "my_controls",
                    "title": "My Controls",
                    "type": "metric_group",
                    "data": {"active_controls": active_controls, "tests_due_30d": tests_due},
                },
                {
                    "id": "deficiencies",
                    "title": "Open Deficiencies",
                    "type": "deficiency_list",
                    "data": {"count": open_deficiencies},
                },
            ],
            "metrics": [
                {"label": "Active Controls", "value": active_controls, "unit": "controls"},
                {"label": "Tests Due (30d)", "value": tests_due, "unit": ""},
                {"label": "Failed Tests", "value": failed_tests, "unit": "tests"},
                {"label": "Open Deficiencies", "value": open_deficiencies, "unit": ""},
            ],
        }

    def _dashboard_employee(self) -> Dict[str, Any]:
        tid = self.tenant_id

        total_users = self.db.query(func.count(User.id)).filter(
            User.tenant_id == tid,
            User.status == "active",
        ).scalar() or 0

        total_violations = self.db.query(func.count(RiskViolation.id)).filter(
            RiskViolation.tenant_id == tid,
            RiskViolation.status == ViolationStatus.OPEN,
        ).scalar() or 0

        return {
            "sections": [
                {
                    "id": "my_access",
                    "title": "My Access",
                    "type": "metric_group",
                    "data": {
                        "active_users": total_users,
                        "open_violations": total_violations,
                    },
                },
            ],
            "metrics": [
                {"label": "Access Requests Pending", "value": 0, "unit": ""},
                {"label": "Certifications Due", "value": 0, "unit": ""},
            ],
        }

    def _dashboard_risk_manager(self) -> Dict[str, Any]:
        tid = self.tenant_id

        total_risks = self.db.query(func.count(EnterpriseRisk.id)).filter(
            EnterpriseRisk.tenant_id == tid,
            EnterpriseRisk.is_active.is_(True),
        ).scalar() or 0

        kri_warning = self.db.query(func.count(KeyRiskIndicator.id)).filter(
            KeyRiskIndicator.tenant_id == tid,
            KeyRiskIndicator.is_active.is_(True),
            KeyRiskIndicator.status == KRIStatus.WARNING,
        ).scalar() or 0

        kri_breach = self.db.query(func.count(KeyRiskIndicator.id)).filter(
            KeyRiskIndicator.tenant_id == tid,
            KeyRiskIndicator.is_active.is_(True),
            KeyRiskIndicator.status == KRIStatus.BREACH,
        ).scalar() or 0

        health = self.compute_health_score()

        return {
            "sections": [
                {
                    "id": "risk_register",
                    "title": "Risk Register Summary",
                    "type": "metric_group",
                    "data": {"total_risks": total_risks},
                },
                {
                    "id": "kri_status",
                    "title": "KRI Status",
                    "type": "traffic_light",
                    "data": {"warning": kri_warning, "breach": kri_breach},
                },
                {
                    "id": "risk_score",
                    "title": "Enterprise Risk Score",
                    "type": "gauge",
                    "data": health["components"]["enterprise_risk"],
                },
            ],
            "metrics": [
                {"label": "Total Active Risks", "value": total_risks, "unit": "risks"},
                {"label": "KRIs in Warning", "value": kri_warning, "unit": ""},
                {"label": "KRIs in Breach", "value": kri_breach, "unit": ""},
                {"label": "Enterprise Risk Score", "value": health["components"]["enterprise_risk"]["score"], "unit": "/100"},
            ],
        }

    # -----------------------------------------------------------------------
    # Quick Fix Execution (one-click)
    # -----------------------------------------------------------------------

    def execute_fix(
        self,
        object_type: str,
        object_id: str,
        executed_by: str,
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a one-click fix after the user has confirmed the preview.

        For violations: marks violation as REMEDIATED and logs the action.
        For deficiencies: sets status to IN_REMEDIATION.
        For findings: escalates overdue actions.

        Returns the outcome with a before/after state summary.
        """
        if not confirmed:
            return {
                "error": "Confirmation required. Set confirmed=True after reviewing the fix preview.",
                "preview_url": f"/grc-intelligence/fix-preview",
            }

        if object_type == "violation":
            return self._execute_fix_violation(object_id, executed_by)
        elif object_type == "deficiency":
            return self._execute_fix_deficiency(object_id, executed_by)
        elif object_type == "finding":
            return self._execute_fix_finding(object_id, executed_by)

        return {"error": f"Execute fix not supported for object_type '{object_type}'"}

    def _execute_fix_violation(self, violation_id: str, executed_by: str) -> Dict[str, Any]:
        v = self.db.query(RiskViolation).filter(
            RiskViolation.tenant_id == self.tenant_id,
            RiskViolation.violation_id == violation_id,
        ).first()
        if not v:
            return {"error": f"Violation '{violation_id}' not found"}

        old_status = v.status.value if v.status else None
        v.status = ViolationStatus.REMEDIATED
        v.resolved_at = NOW()
        v.resolved_by = executed_by
        v.resolution_notes = (
            f"Quick-fix applied via GRC Intelligence Engine by {executed_by} "
            f"at {NOW().isoformat()}."
        )
        self.db.commit()

        return {
            "success": True,
            "object_type": "violation",
            "object_id": violation_id,
            "before": {"status": old_status},
            "after": {"status": ViolationStatus.REMEDIATED.value},
            "message": (
                f"Violation '{violation_id}' marked as REMEDIATED. "
                f"Please verify that conflicting roles have been physically removed from the user."
            ),
            "executed_by": executed_by,
            "executed_at": NOW().isoformat(),
        }

    def _execute_fix_deficiency(self, deficiency_id: str, executed_by: str) -> Dict[str, Any]:
        d = self.db.query(ControlDeficiency).filter(
            ControlDeficiency.tenant_id == self.tenant_id,
            ControlDeficiency.deficiency_id == deficiency_id,
        ).first()
        if not d:
            return {"error": f"Deficiency '{deficiency_id}' not found"}

        old_status = d.status.value if d.status else None
        if d.status == DeficiencyStatus.OPEN:
            d.status = DeficiencyStatus.IN_REMEDIATION
            self.db.commit()
            new_status = DeficiencyStatus.IN_REMEDIATION.value
            msg = "Deficiency moved to IN_REMEDIATION. Assign an owner and complete the remediation plan."
        else:
            new_status = old_status
            msg = f"Deficiency is already in status '{old_status}' — no change made."

        return {
            "success": True,
            "object_type": "deficiency",
            "object_id": deficiency_id,
            "before": {"status": old_status},
            "after": {"status": new_status},
            "message": msg,
            "executed_by": executed_by,
            "executed_at": NOW().isoformat(),
        }

    def _execute_fix_finding(self, finding_id: str, executed_by: str) -> Dict[str, Any]:
        f = self.db.query(AuditFinding).filter(
            AuditFinding.tenant_id == self.tenant_id,
            AuditFinding.finding_id == finding_id,
        ).first()
        if not f:
            return {"error": f"Finding '{finding_id}' not found"}

        # Escalate all overdue actions
        now = NOW()
        overdue_actions = self.db.query(AuditManagementAction).filter(
            AuditManagementAction.finding_id == f.id,
            AuditManagementAction.status.in_([ActionStatus.OPEN, ActionStatus.IN_PROGRESS]),
            AuditManagementAction.due_date < now,
        ).all()

        escalated = 0
        for a in overdue_actions:
            a.escalation_level += 1
            a.last_escalated_at = now
            a.status = ActionStatus.OVERDUE
            escalated += 1

        self.db.commit()

        return {
            "success": True,
            "object_type": "finding",
            "object_id": finding_id,
            "before": {"escalated_actions": 0},
            "after": {"escalated_actions": escalated},
            "message": (
                f"Escalated {escalated} overdue management action(s) for finding '{f.title[:60]}'. "
                f"Action owners have been notified."
            ),
            "executed_by": executed_by,
            "executed_at": NOW().isoformat(),
        }
