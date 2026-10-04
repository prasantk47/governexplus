"""
Reports API Router

Provides:
- Dashboard summary endpoint aggregating data from real database tables
- Basic report run and download operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import io

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.rules import RuleEngine
from audit.logger import audit_logger
from db.database import get_db
from db.models.user import User
from db.models.risk import RiskViolation
from db.models.audit import AccessRequestLog, CertificationCampaignLog
from db.models.firefighter import FirefighterRequest, FirefighterSession
from core.export import PPTXExportService
from api.dependencies import get_current_user

PPTX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Reports"])

_rule_engine = RuleEngine()


# =============================================================================
# Dashboard Summary Endpoint
# =============================================================================

@router.get("/dashboard-summary")
async def get_dashboard_summary(
    days: int = Query(30, description="Number of days to report on"),
    db: Session = Depends(get_db),
):
    """
    Aggregated reports dashboard — pulls stats from real database tables.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    end_date = datetime.utcnow()

    # --- Access Requests (from DB) ---
    total_requests = db.query(func.count(AccessRequestLog.id)).scalar() or 0
    pending_requests = (
        db.query(func.count(AccessRequestLog.id))
        .filter(AccessRequestLog.status == "pending")
        .scalar()
    ) or 0
    approved_requests = (
        db.query(func.count(AccessRequestLog.id))
        .filter(AccessRequestLog.status == "approved")
        .scalar()
    ) or 0
    rejected_requests = (
        db.query(func.count(AccessRequestLog.id))
        .filter(AccessRequestLog.status == "rejected")
        .scalar()
    ) or 0

    # SLA: count requests pending > 48 hours as overdue
    sla_hours = 48
    overdue_cutoff = datetime.utcnow() - timedelta(hours=sla_hours)
    overdue_count = (
        db.query(func.count(AccessRequestLog.id))
        .filter(
            AccessRequestLog.status == "pending_approval",
            AccessRequestLog.submitted_at < overdue_cutoff,
        )
        .scalar()
    ) or 0
    sla_compliance_rate = (
        ((pending_requests - overdue_count) / pending_requests * 100)
        if pending_requests > 0
        else 100.0
    )

    access_requests_data = {
        "total": total_requests,
        "pending": pending_requests,
        "approved": approved_requests,
        "rejected": rejected_requests,
        "sla": {
            "total_pending": pending_requests,
            "overdue_count": overdue_count,
            "sla_compliance_rate": round(sla_compliance_rate, 1),
            "average_approval_hours": 0,
        },
    }

    # --- Firefighter (from DB) ---
    ff_total_requests = db.query(func.count(FirefighterRequest.id)).scalar() or 0
    ff_active_sessions = (
        db.query(func.count(FirefighterSession.id))
        .filter(FirefighterSession.status == "active")
        .scalar()
    ) or 0
    ff_completed_sessions = (
        db.query(func.count(FirefighterSession.id))
        .filter(FirefighterSession.status == "completed")
        .scalar()
    ) or 0

    firefighter_data = {
        "total_requests": ff_total_requests,
        "active_sessions": ff_active_sessions,
        "completed_sessions": ff_completed_sessions,
    }

    # --- Risk ---
    risk_stats = _rule_engine.get_statistics()
    active_violations = (
        db.query(func.count(RiskViolation.id))
        .filter(RiskViolation.status.in_(["open", "active", "new"]))
        .scalar()
    ) or 0

    risk_data = {
        "total_rules": risk_stats.get("rules_loaded", 0),
        "active_violations": active_violations,
        "rules_by_category": risk_stats.get("rules_by_category", {}),
        "rules_by_type": risk_stats.get("rules_by_type", {}),
    }

    # --- Certification (from DB) ---
    cert_total = db.query(func.count(CertificationCampaignLog.id)).scalar() or 0
    cert_active = (
        db.query(func.count(CertificationCampaignLog.id))
        .filter(CertificationCampaignLog.status == "active")
        .scalar()
    ) or 0

    certification_data = {
        "total_campaigns": cert_total,
        "active_campaigns": cert_active,
    }

    # --- Users ---
    total_users = db.query(func.count(User.id)).scalar() or 0

    # --- Audit ---
    try:
        audit_logs = audit_logger.query(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )

        by_category = {}
        failed_count = 0
        compliance_count = 0
        for log in audit_logs:
            cat = log.action_category or 'system'
            by_category[cat] = by_category.get(cat, 0) + 1
            if not log.success:
                failed_count += 1
            if log.compliance_relevant:
                compliance_count += 1

        audit_data = {
            "total_entries": len(audit_logs),
            "failed_actions": failed_count,
            "compliance_entries": compliance_count,
            "by_category": by_category,
        }
    except Exception as e:
        logger.warning(f"Failed to fetch audit data: {e}")
        audit_data = {"total_entries": 0, "failed_actions": 0, "compliance_entries": 0, "by_category": {}}

    return {
        "period_days": days,
        "generated_at": datetime.utcnow().isoformat(),
        "total_users": total_users,
        "access_requests": access_requests_data,
        "firefighter": firefighter_data,
        "risk": risk_data,
        "certification": certification_data,
        "audit": audit_data,
    }


# =============================================================================
# Report Library
# =============================================================================

REPORT_CATALOG = {
    # Legacy RPT-* IDs
    "RPT-001": {"id": "RPT-001", "name": "SoD Violations Summary", "format": "pdf"},
    "RPT-002": {"id": "RPT-002", "name": "User Access Review", "format": "excel"},
    "RPT-003": {"id": "RPT-003", "name": "Certification Campaign Status", "format": "pdf"},
    "RPT-004": {"id": "RPT-004", "name": "Firefighter Session Audit", "format": "excel"},
    "RPT-005": {"id": "RPT-005", "name": "High-Risk Users Report", "format": "pdf"},
    "RPT-006": {"id": "RPT-006", "name": "Access Request History", "format": "csv"},
    "RPT-007": {"id": "RPT-007", "name": "Role Assignment Matrix", "format": "excel"},
    "RPT-008": {"id": "RPT-008", "name": "Compliance Summary Report", "format": "pdf"},
    # ARA / SoD (001-015)
    "sod-violations": {"id": "sod-violations", "name": "SoD Violations Summary", "format": "pdf", "module": "ara"},
    "sod-violations-by-rule": {"id": "sod-violations-by-rule", "name": "Violations by Rule", "format": "pdf", "module": "ara"},
    "sod-violations-by-user": {"id": "sod-violations-by-user", "name": "Violations by User", "format": "pdf", "module": "ara"},
    "sod-violations-trend": {"id": "sod-violations-trend", "name": "Violations Trend", "format": "pdf", "module": "ara"},
    "mitigation-effectiveness": {"id": "mitigation-effectiveness", "name": "Mitigation Effectiveness", "format": "pdf", "module": "ara"},
    "open-vs-remediated": {"id": "open-vs-remediated", "name": "Open vs Remediated", "format": "pdf", "module": "ara"},
    "role-sod-risk": {"id": "role-sod-risk", "name": "Role-Level SoD Risk", "format": "pdf", "module": "ara"},
    "sod-ruleset-coverage": {"id": "sod-ruleset-coverage", "name": "SoD Ruleset Coverage", "format": "pdf", "module": "ara"},
    "top-violated-rules": {"id": "top-violated-rules", "name": "Top Violated Rules", "format": "pdf", "module": "ara"},
    "cross-system-sod": {"id": "cross-system-sod", "name": "Cross-System SoD", "format": "pdf", "module": "ara"},
    "sod-simulation": {"id": "sod-simulation", "name": "SoD Simulation", "format": "pdf", "module": "ara"},
    "access-risk-by-department": {"id": "access-risk-by-department", "name": "Risk by Department", "format": "pdf", "module": "ara"},
    "orphaned-accounts": {"id": "orphaned-accounts", "name": "Orphaned Accounts", "format": "pdf", "module": "ara"},
    "dormant-users": {"id": "dormant-users", "name": "Dormant Users", "format": "pdf", "module": "ara"},
    "access-pattern-anomalies": {"id": "access-pattern-anomalies", "name": "Access Anomalies", "format": "pdf", "module": "ara"},
    # ARM (016-023)
    "pending-approvals-aging": {"id": "pending-approvals-aging", "name": "Pending Approvals Aging", "format": "pdf", "module": "arm"},
    "request-volume": {"id": "request-volume", "name": "Request Volume", "format": "pdf", "module": "arm"},
    "approval-sla": {"id": "approval-sla", "name": "Approval SLA", "format": "pdf", "module": "arm"},
    "rejection-analysis": {"id": "rejection-analysis", "name": "Rejection Analysis", "format": "pdf", "module": "arm"},
    "auto-approved-vs-manual": {"id": "auto-approved-vs-manual", "name": "Auto vs Manual", "format": "pdf", "module": "arm"},
    "provisioning-lag": {"id": "provisioning-lag", "name": "Provisioning Lag", "format": "pdf", "module": "arm"},
    "requests-by-role": {"id": "requests-by-role", "name": "Requests by Role", "format": "pdf", "module": "arm"},
    "high-risk-requests": {"id": "high-risk-requests", "name": "High-Risk Requests", "format": "pdf", "module": "arm"},
    # EAM (024-031)
    "ff-activity": {"id": "ff-activity", "name": "FF Activity Log", "format": "pdf", "module": "eam"},
    "ff-usage-by-id": {"id": "ff-usage-by-id", "name": "FF Usage by ID", "format": "pdf", "module": "eam"},
    "ff-controller-signoff": {"id": "ff-controller-signoff", "name": "Controller Sign-Off", "format": "pdf", "module": "eam"},
    "ff-overdue-reviews": {"id": "ff-overdue-reviews", "name": "Overdue Reviews", "format": "pdf", "module": "eam"},
    "ff-session-duration": {"id": "ff-session-duration", "name": "Session Duration", "format": "pdf", "module": "eam"},
    "ff-transactions": {"id": "ff-transactions", "name": "Transactions by Session", "format": "pdf", "module": "eam"},
    "ff-critical-tcodes": {"id": "ff-critical-tcodes", "name": "Critical Tcodes", "format": "pdf", "module": "eam"},
    "ff-id-inventory": {"id": "ff-id-inventory", "name": "FF ID Inventory", "format": "pdf", "module": "eam"},
    # Certification (032-039)
    "certification-completion": {"id": "certification-completion", "name": "Campaign Completion", "format": "pdf", "module": "certification"},
    "certification-by-reviewer": {"id": "certification-by-reviewer", "name": "By Reviewer", "format": "pdf", "module": "certification"},
    "overdue-certifications": {"id": "overdue-certifications", "name": "Overdue Certs", "format": "pdf", "module": "certification"},
    "certification-revocations": {"id": "certification-revocations", "name": "Revocations", "format": "pdf", "module": "certification"},
    "certification-comparison": {"id": "certification-comparison", "name": "Campaign Comparison", "format": "pdf", "module": "certification"},
    "self-certification": {"id": "self-certification", "name": "Self-Certification", "format": "pdf", "module": "certification"},
    "sod-in-certifications": {"id": "sod-in-certifications", "name": "SoD in Certs", "format": "pdf", "module": "certification"},
    "certification-coverage": {"id": "certification-coverage", "name": "Cert Coverage", "format": "pdf", "module": "certification"},
    # JML (040-047)
    "jml-hire-sla": {"id": "jml-hire-sla", "name": "New Hire SLA", "format": "pdf", "module": "jml"},
    "jml-termination-sla": {"id": "jml-termination-sla", "name": "Termination SLA", "format": "pdf", "module": "jml"},
    "jml-transfer-recert": {"id": "jml-transfer-recert", "name": "Transfer Re-Cert", "format": "pdf", "module": "jml"},
    "jml-orphaned-post-transfer": {"id": "jml-orphaned-post-transfer", "name": "Orphaned Post-Transfer", "format": "pdf", "module": "jml"},
    "jml-event-volume": {"id": "jml-event-volume", "name": "JML Event Volume", "format": "pdf", "module": "jml"},
    "jml-role-mapping": {"id": "jml-role-mapping", "name": "Role Mapping by Job", "format": "pdf", "module": "jml"},
    "jml-dept-profile": {"id": "jml-dept-profile", "name": "Department Profile", "format": "pdf", "module": "jml"},
    "jml-compliance-score": {"id": "jml-compliance-score", "name": "JML Compliance Score", "format": "pdf", "module": "jml"},
    # BRM (048-053)
    "role-inventory": {"id": "role-inventory", "name": "Role Inventory", "format": "pdf", "module": "brm"},
    "role-assignment": {"id": "role-assignment", "name": "Role Assignment", "format": "pdf", "module": "brm"},
    "role-comparison": {"id": "role-comparison", "name": "Role Comparison", "format": "pdf", "module": "brm"},
    "composite-role-usage": {"id": "composite-role-usage", "name": "Composite Role Usage", "format": "pdf", "module": "brm"},
    "role-mining": {"id": "role-mining", "name": "Role Mining", "format": "pdf", "module": "brm"},
    "role-cleanup": {"id": "role-cleanup", "name": "Role Clean-Up", "format": "pdf", "module": "brm"},
    # Risk Management (054-065)
    "risk-register": {"id": "risk-register", "name": "Risk Register", "format": "pdf", "module": "risk"},
    "risk-heatmap": {"id": "risk-heatmap", "name": "Risk Heatmap", "format": "pdf", "module": "risk"},
    "risk-by-category": {"id": "risk-by-category", "name": "Risk by Category", "format": "pdf", "module": "risk"},
    "risk-trend": {"id": "risk-trend", "name": "Risk Trend", "format": "pdf", "module": "risk"},
    "kri-dashboard": {"id": "kri-dashboard", "name": "KRI Dashboard", "format": "pdf", "module": "risk"},
    "kri-breaches": {"id": "kri-breaches", "name": "KRI Breaches", "format": "pdf", "module": "risk"},
    "incident-log": {"id": "incident-log", "name": "Incident Log", "format": "pdf", "module": "risk"},
    "risk-by-owner": {"id": "risk-by-owner", "name": "Risk by Owner", "format": "pdf", "module": "risk"},
    "top-risks": {"id": "top-risks", "name": "Top 10 Risks", "format": "pdf", "module": "risk"},
    "residual-risk": {"id": "residual-risk", "name": "Residual Risk", "format": "pdf", "module": "risk"},
    "risk-treatment": {"id": "risk-treatment", "name": "Risk Treatment", "format": "pdf", "module": "risk"},
    "risk-appetite": {"id": "risk-appetite", "name": "Risk Appetite", "format": "pdf", "module": "risk"},
    # Process Control (066-073)
    "control-inventory": {"id": "control-inventory", "name": "Control Inventory", "format": "pdf", "module": "controls"},
    "control-testing": {"id": "control-testing", "name": "Control Test Results", "format": "pdf", "module": "controls"},
    "deficiency-tracker": {"id": "deficiency-tracker", "name": "Deficiency Tracker", "format": "pdf", "module": "controls"},
    "control-effectiveness": {"id": "control-effectiveness", "name": "Control Effectiveness", "format": "pdf", "module": "controls"},
    "overdue-tests": {"id": "overdue-tests", "name": "Overdue Tests", "format": "pdf", "module": "controls"},
    "deficiency-aging": {"id": "deficiency-aging", "name": "Deficiency Aging", "format": "pdf", "module": "controls"},
    "ccm-monitoring": {"id": "ccm-monitoring", "name": "CCM Monitoring", "format": "pdf", "module": "controls"},
    "sox-itgc-coverage": {"id": "sox-itgc-coverage", "name": "SOX ITGC Coverage", "format": "pdf", "module": "controls"},
    # Audit Management (074-079)
    "audit-plan": {"id": "audit-plan", "name": "Audit Plan Status", "format": "pdf", "module": "audit"},
    "audit-findings": {"id": "audit-findings", "name": "Audit Findings", "format": "pdf", "module": "audit"},
    "finding-closure": {"id": "finding-closure", "name": "Finding Closure Rate", "format": "pdf", "module": "audit"},
    "audit-engagement": {"id": "audit-engagement", "name": "Audit Engagement", "format": "pdf", "module": "audit"},
    "findings-by-risk": {"id": "findings-by-risk", "name": "Findings by Risk", "format": "pdf", "module": "audit"},
    "outstanding-remediation": {"id": "outstanding-remediation", "name": "Outstanding Remediation", "format": "pdf", "module": "audit"},
    # Compliance (080-083)
    "framework-coverage": {"id": "framework-coverage", "name": "Framework Coverage", "format": "pdf", "module": "compliance"},
    "compliance-posture": {"id": "compliance-posture", "name": "Compliance Posture", "format": "pdf", "module": "compliance"},
    "policy-attestation": {"id": "policy-attestation", "name": "Policy Attestation", "format": "pdf", "module": "compliance"},
    "compliance-gaps": {"id": "compliance-gaps", "name": "Compliance Gaps", "format": "pdf", "module": "compliance"},
    # TPRM (084-089)
    "vendor-inventory": {"id": "vendor-inventory", "name": "Vendor Inventory", "format": "pdf", "module": "tprm"},
    "assessment-completion": {"id": "assessment-completion", "name": "Assessment Completion", "format": "pdf", "module": "tprm"},
    "vendor-risk-distribution": {"id": "vendor-risk-distribution", "name": "Vendor Risk Distribution", "format": "pdf", "module": "tprm"},
    "fourth-party-risk": {"id": "fourth-party-risk", "name": "Fourth-Party Risk", "format": "pdf", "module": "tprm"},
    "overdue-reassessments": {"id": "overdue-reassessments", "name": "Overdue Reassessments", "format": "pdf", "module": "tprm"},
    "vendor-sla": {"id": "vendor-sla", "name": "Vendor SLA", "format": "pdf", "module": "tprm"},
    # BCM (090-093)
    "bia-summary": {"id": "bia-summary", "name": "BIA Summary", "format": "pdf", "module": "bcm"},
    "bcm-plan-test": {"id": "bcm-plan-test", "name": "BCM Plan Test", "format": "pdf", "module": "bcm"},
    "rto-rpo": {"id": "rto-rpo", "name": "RTO/RPO Achievement", "format": "pdf", "module": "bcm"},
    "critical-assets": {"id": "critical-assets", "name": "Critical Assets", "format": "pdf", "module": "bcm"},
    # Fraud (094-097)
    "fraud-alerts": {"id": "fraud-alerts", "name": "Fraud Alerts", "format": "pdf", "module": "fraud"},
    "fraud-cases": {"id": "fraud-cases", "name": "Fraud Cases", "format": "pdf", "module": "fraud"},
    "fraud-rule-effectiveness": {"id": "fraud-rule-effectiveness", "name": "Fraud Rule Effectiveness", "format": "pdf", "module": "fraud"},
    "alert-to-case": {"id": "alert-to-case", "name": "Alert-to-Case Rate", "format": "pdf", "module": "fraud"},
    # Survey (098-099)
    "survey-responses": {"id": "survey-responses", "name": "Survey Responses", "format": "pdf", "module": "survey"},
    "survey-completion": {"id": "survey-completion", "name": "Survey Completion", "format": "pdf", "module": "survey"},
    # Template Library (100-101)
    "library-adoption": {"id": "library-adoption", "name": "Library Adoption", "format": "pdf", "module": "library"},
    "pack-import-history": {"id": "pack-import-history", "name": "Pack Import History", "format": "pdf", "module": "library"},
}


# =============================================================================
# PPTX Export Endpoints (NF-08)
# =============================================================================

def _get_tenant_name(db: Session) -> str:
    """Best-effort: return a display name for the current tenant."""
    try:
        from core.tenant import get_current_tenant
        ctx = get_current_tenant()
        return getattr(ctx, "tenant_name", None) or getattr(ctx, "tenant_id", None) or "Governex+"
    except Exception:
        return "Governex+"


@router.get("/export/risk-report", summary="Export Risk Report as PPTX (NF-08)")
async def export_risk_report_pptx(
    db: Session = Depends(get_db),
):
    """
    Generate and download a full Enterprise Risk Report as a PowerPoint file.

    Includes:
    - Executive summary KPIs
    - Severity heatmap table and bar chart
    - Top violations table
    - Full violation detail table

    Returns a .pptx binary stream.
    """
    try:
        # Fetch all violations from DB
        violations_q = db.query(RiskViolation).all()

        risks = []
        for v in violations_q:
            risks.append({
                "user_id": v.user_external_id or "",
                "username": v.username or "",
                "rule_id": v.rule_id,
                "rule_name": v.rule_name,
                "severity": v.severity.value if hasattr(v.severity, "value") else str(v.severity),
                "severity_score": v.severity_score or 0,
                "risk_category": v.risk_category or "",
                "status": v.status.value if hasattr(v.status, "value") else str(v.status),
                "detected_at": v.detected_at.isoformat() if v.detected_at else "",
            })

        # Build heatmap
        heatmap: dict = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for r in risks:
            sev = r["severity"].lower()
            if sev in heatmap:
                heatmap[sev] += 1

        # Top risks = top 20 by severity_score desc
        top_risks = sorted(risks, key=lambda x: x.get("severity_score", 0), reverse=True)[:20]

        tenant_name = _get_tenant_name(db)
        svc = PPTXExportService(tenant_name=tenant_name)
        pptx_bytes = svc.export_risk_report(risks, heatmap, top_risks)

        filename = f"risk-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pptx"
        return StreamingResponse(
            io.BytesIO(pptx_bytes),
            media_type=PPTX_CONTENT_TYPE,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        logger.error("PPTX risk report export failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/audit-report/{engagement_id}", summary="Export Audit Engagement Report as PPTX (NF-08)")
async def export_audit_report_pptx(
    engagement_id: str,
    db: Session = Depends(get_db),
):
    """
    Generate and download an Audit Engagement Report as a PowerPoint file.

    Includes:
    - Engagement overview KPIs
    - Findings table and severity chart
    - Remediation actions table

    Returns a .pptx binary stream.
    """
    try:
        # Attempt to load engagement from DB (graceful fallback if model not present)
        engagement: dict = {"id": engagement_id, "title": f"Audit Engagement {engagement_id}",
                            "period": datetime.now().strftime("%B %Y"), "owner": "Audit Team",
                            "type": "Internal", "status": "In Progress"}
        findings: List[dict] = []
        actions: List[dict] = []

        try:
            from db.models.audit_management import AuditEngagement, AuditFinding, RemediationAction
            eng_obj = db.query(AuditEngagement).filter(
                AuditEngagement.id == engagement_id
            ).first()
            if not eng_obj:
                raise HTTPException(status_code=404, detail=f"Engagement {engagement_id} not found")

            engagement = {
                "id": str(eng_obj.id),
                "title": getattr(eng_obj, "title", engagement_id),
                "period": getattr(eng_obj, "period", ""),
                "owner": getattr(eng_obj, "owner", ""),
                "type": getattr(eng_obj, "audit_type", ""),
                "status": getattr(eng_obj, "status", ""),
            }

            finding_objs = db.query(AuditFinding).filter(
                AuditFinding.engagement_id == eng_obj.id
            ).all()
            findings = [
                {
                    "id": str(f.id),
                    "title": getattr(f, "title", ""),
                    "severity": getattr(f, "severity", ""),
                    "status": getattr(f, "status", ""),
                    "owner": getattr(f, "owner", ""),
                    "due_date": getattr(f, "due_date", ""),
                    "description": getattr(f, "description", ""),
                }
                for f in finding_objs
            ]

            action_objs = db.query(RemediationAction).filter(
                RemediationAction.engagement_id == eng_obj.id
            ).all()
            actions = [
                {
                    "id": str(a.id),
                    "description": getattr(a, "description", ""),
                    "owner": getattr(a, "owner", ""),
                    "due_date": getattr(a, "due_date", ""),
                    "status": getattr(a, "status", ""),
                }
                for a in action_objs
            ]
        except ImportError:
            # audit_management models not available yet; use empty defaults
            pass
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Could not load audit models: %s — using stubs", str(e))

        tenant_name = _get_tenant_name(db)
        svc = PPTXExportService(tenant_name=tenant_name)
        pptx_bytes = svc.export_audit_report(engagement, findings, actions)

        filename = f"audit-report-{engagement_id}-{datetime.now().strftime('%Y%m%d')}.pptx"
        return StreamingResponse(
            io.BytesIO(pptx_bytes),
            media_type=PPTX_CONTENT_TYPE,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("PPTX audit report export failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/control-report", summary="Export Process Control Status Report as PPTX (NF-08)")
async def export_control_report_pptx(
    db: Session = Depends(get_db),
):
    """
    Generate and download a Process Control Status Report as a PowerPoint file.

    Includes:
    - Control dashboard KPIs
    - Effectiveness pie chart
    - Controls detail table
    - Deficiencies table

    Returns a .pptx binary stream.
    """
    try:
        controls: List[dict] = []
        deficiencies: List[dict] = []
        dashboard: dict = {}

        try:
            from db.models.process_control import ProcessControl, ControlDeficiency
            ctrl_objs = db.query(ProcessControl).all()
            controls = [
                {
                    "id": str(c.id),
                    "name": getattr(c, "name", ""),
                    "type": getattr(c, "control_type", ""),
                    "status": getattr(c, "status", ""),
                    "owner": getattr(c, "owner", ""),
                    "last_tested": getattr(c, "last_tested_at", ""),
                    "effectiveness": getattr(c, "effectiveness", ""),
                }
                for c in ctrl_objs
            ]

            deficiency_objs = db.query(ControlDeficiency).all()
            deficiencies = [
                {
                    "control_id": str(d.control_id),
                    "description": getattr(d, "description", ""),
                    "severity": getattr(d, "severity", ""),
                    "remediation_due": getattr(d, "remediation_due", ""),
                    "status": getattr(d, "status", "open"),
                }
                for d in deficiency_objs
            ]
        except ImportError:
            pass
        except Exception as e:
            logger.warning("Could not load process_control models: %s — using stubs", str(e))

        total = len(controls)
        effective = sum(1 for c in controls if str(c.get("effectiveness", "")).lower() in ("effective", "high"))
        ineffective = sum(1 for c in controls if str(c.get("effectiveness", "")).lower() in ("ineffective", "low"))
        not_tested = sum(1 for c in controls if str(c.get("status", "")).lower() in ("not_tested", "pending"))
        coverage_pct = ((effective + ineffective) / total * 100) if total > 0 else 0.0

        dashboard = {
            "total_controls": total,
            "effective": effective,
            "ineffective": ineffective,
            "not_tested": not_tested,
            "coverage_pct": coverage_pct,
        }

        tenant_name = _get_tenant_name(db)
        svc = PPTXExportService(tenant_name=tenant_name)
        pptx_bytes = svc.export_control_report(controls, deficiencies, dashboard)

        filename = f"control-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pptx"
        return StreamingResponse(
            io.BytesIO(pptx_bytes),
            media_type=PPTX_CONTENT_TYPE,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        logger.error("PPTX control report export failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/grc-executive", summary="Export GRC Executive Summary as PPTX (NF-08)")
async def export_grc_executive_pptx(
    db: Session = Depends(get_db),
):
    """
    Generate and download a unified GRC Executive Summary as a PowerPoint file.

    Includes sections for:
    - Risk Management (violations, severity, risk score)
    - Audit Management (findings, open items, past due)
    - Compliance (frameworks, coverage)
    - Process Controls (effectiveness, deficiencies)

    Returns a .pptx binary stream.
    """
    try:
        # --- Risk ---
        violations_q = db.query(RiskViolation).all()
        total_violations = len(violations_q)
        sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        total_score = 0.0
        for v in violations_q:
            sev = (v.severity.value if hasattr(v.severity, "value") else str(v.severity)).lower()
            if sev in sev_counts:
                sev_counts[sev] += 1
            total_score += float(v.severity_score or 0)

        risk_score = (total_score / total_violations) if total_violations > 0 else 0.0

        # --- Audit ---
        total_findings = 0
        open_findings = 0
        past_due = 0
        try:
            from db.models.audit_management import AuditFinding, RemediationAction
            total_findings = db.query(func.count(AuditFinding.id)).scalar() or 0
            open_findings = db.query(func.count(AuditFinding.id)).filter(
                AuditFinding.status.notin_(["closed", "resolved"])
            ).scalar() or 0
            from sqlalchemy import and_
            today_str = datetime.utcnow().date()
            past_due = db.query(func.count(RemediationAction.id)).filter(
                RemediationAction.status.notin_(["completed", "closed"]),
                RemediationAction.due_date < today_str,
            ).scalar() or 0
        except Exception:
            pass

        # --- Compliance ---
        compliance_data: dict = {"frameworks": 0, "compliant": 0, "non_compliant": 0, "coverage_pct": 0}
        try:
            from db.models.grc_foundation import Framework, FrameworkRequirement
            compliance_data["frameworks"] = db.query(func.count(Framework.id)).scalar() or 0
        except Exception:
            pass

        # --- Controls ---
        ctrl_data: dict = {"total": 0, "effective": 0, "deficiencies": 0}
        try:
            from db.models.process_control import ProcessControl, ControlDeficiency
            ctrl_data["total"] = db.query(func.count(ProcessControl.id)).scalar() or 0
            ctrl_data["effective"] = db.query(func.count(ProcessControl.id)).filter(
                ProcessControl.effectiveness.in_(["effective", "high"])
            ).scalar() or 0
            ctrl_data["deficiencies"] = db.query(func.count(ControlDeficiency.id)).scalar() or 0
        except Exception:
            pass

        grc_dashboard = {
            "period": datetime.now().strftime("%B %Y"),
            "risk": {
                "total_violations": total_violations,
                "critical": sev_counts["critical"],
                "high": sev_counts["high"],
                "medium": sev_counts["medium"],
                "low": sev_counts["low"],
                "risk_score": round(risk_score, 1),
            },
            "audit": {
                "total_findings": total_findings,
                "open_findings": open_findings,
                "past_due": past_due,
            },
            "compliance": compliance_data,
            "controls": ctrl_data,
        }

        tenant_name = _get_tenant_name(db)
        svc = PPTXExportService(tenant_name=tenant_name)
        pptx_bytes = svc.export_grc_executive(grc_dashboard)

        filename = f"grc-executive-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pptx"
        return StreamingResponse(
            io.BytesIO(pptx_bytes),
            media_type=PPTX_CONTENT_TYPE,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        logger.error("PPTX GRC executive export failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/{report_id}/run")
async def run_report(report_id: str):
    """Trigger report generation."""
    if report_id not in REPORT_CATALOG:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    report = REPORT_CATALOG[report_id]
    return {
        "success": True,
        "report_id": report_id,
        "name": report["name"],
        "status": "generating",
        "message": f"Report '{report['name']}' generation started",
        "started_at": datetime.now().isoformat()
    }


@router.get("/{report_id}/download")
async def download_report(report_id: str):
    """Download a report."""
    if report_id not in REPORT_CATALOG:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    report = REPORT_CATALOG[report_id]
    content = (
        f"GRC Zero Trust Platform\n========================\n"
        f"Report: {report['name']}\nID: {report_id}\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )

    return JSONResponse(content={
        "success": True,
        "report_id": report_id,
        "filename": f"report-{report_id}.{report['format']}",
        "content": content,
        "message": "Report ready for download"
    })


_REPORTS_ALLOWED_ROLES = {
    "platform_admin", "tenant_admin", "admin", "super_admin",
    "ciso", "compliance_officer", "risk_manager",
    "security_admin", "it_security",
    "internal_auditor", "external_auditor",
    "control_owner", "sox_owner",
    "process_owner", "firefighter_controller", "firefighter_owner",
    "role_owner", "risk_owner", "mitigation_monitor",
}


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get report details."""
    caller_roles = set(current_user.get("roles", []) or [current_user.get("role", "")])
    if not (caller_roles & _REPORTS_ALLOWED_ROLES):
        raise HTTPException(status_code=403, detail="Insufficient permissions to access reports")
    if report_id not in REPORT_CATALOG:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return REPORT_CATALOG[report_id]
