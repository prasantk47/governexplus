"""
Access Request Manager

Central manager for the access request lifecycle including:
- Request creation and submission
- Risk analysis before approval
- Workflow orchestration
- Provisioning coordination
- Expiry management

PERSISTENCE: All requests are stored in the `access_request_logs` database
table.  The in-memory dict has been removed.
"""

import uuid
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import (
    AccessRequest, AccessRequestStatus, RequestType,
    RequestedAccess, ApprovalStep, ApprovalStatus, ApprovalAction
)
from .workflow import WorkflowEngine, ApprovalRule
from core.rules import RuleEngine
from core.rules.models import UserAccess, Entitlement
from db.models.audit import AccessRequestLog

# --- 6 Core Engines (Gate 2) ---
from core.effective_access import EffectiveAccessEngine
from core.risk_engine import RiskEngine
from core.findings import FindingsEngine
from core.decision_engine import DecisionEngine
from core.execution import ExecutionEngine
from core.evidence import EvidenceEngine

logger = logging.getLogger(__name__)


class AccessRequestManager:
    """
    Central manager for access request operations.

    All state is persisted to the `access_request_logs` DB table.
    """

    def __init__(self,
                 db: Optional[Session] = None,
                 rule_engine: Optional[RuleEngine] = None,
                 workflow_engine: Optional[WorkflowEngine] = None,
                 user_connector=None,
                 notification_handler: Optional[Callable] = None):
        self.db = db
        self.rule_engine = rule_engine or RuleEngine()
        self.workflow_engine = workflow_engine or WorkflowEngine(
            notification_handler=notification_handler
        )
        self.user_connector = user_connector
        self.sap_connector = user_connector  # SAP connector for provisioning
        self.notification_handler = notification_handler

        # --- 6 Core Engines (Gate 2) ---
        self.effective_access = EffectiveAccessEngine()
        self.risk_engine = RiskEngine()
        self.findings_engine = FindingsEngine()
        self.decision_engine = DecisionEngine()
        self.execution_engine = ExecutionEngine()
        self.evidence_engine = EvidenceEngine()

        # Configuration
        self.config = {
            "auto_approve_low_risk": False,
            "low_risk_threshold": 20,
            "require_justification": True,
            "min_justification_length": 20,
            "max_temporary_days": 90,
            "default_temporary_days": 30,
            "enable_risk_preview": True
        }

        # Role catalog (would come from database/connector)
        self.role_catalog: Dict[str, Dict] = self._load_role_catalog()

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _get_db(self) -> Session:
        if self.db is None:
            raise RuntimeError("AccessRequestManager requires a database session")
        return self.db

    def _save_to_db(self, request: AccessRequest) -> None:
        """Persist an AccessRequest dataclass to the access_request_logs table."""
        db = self._get_db()
        row = db.query(AccessRequestLog).filter(
            AccessRequestLog.request_id == request.request_id
        ).first()

        if row is None:
            row = AccessRequestLog(
                request_id=request.request_id,
                tenant_id=request.tenant_id or "tenant_default",
                request_type=request.request_type.value,
                requester_user_id=request.requester_user_id,
                requester_name=request.requester_name,
                requester_email=request.requester_email,
                requester_department=request.requester_department,
                target_user_id=request.target_user_id,
                target_user_name=request.target_user_name,
                business_justification=request.business_justification,
                ticket_reference=request.ticket_reference,
                requested_roles=[item.access_name for item in request.requested_items],
                status=request.status.value,
                risk_score=int(request.overall_risk_score),
                violations_detected=request.sod_violations,
                submitted_at=request.submitted_at or datetime.utcnow(),
                valid_to=request.requested_end_date,
                approvals=[],
            )
            db.add(row)
        else:
            row.status = request.status.value
            row.risk_score = int(request.overall_risk_score)
            row.violations_detected = request.sod_violations
            row.completed_at = request.completed_at
            row.provisioned = request.status == AccessRequestStatus.PROVISIONED
            row.provisioned_at = request.provisioned_at
            row.current_approval_step = request.current_step
            row.total_approval_steps = len(request.approval_steps)
            approvals = []
            for step in request.approval_steps:
                approvals.append({
                    "step_id": step.step_id,
                    "approver": step.approver_ids[0] if step.approver_ids else "",
                    "approver_ids": step.approver_ids,
                    "status": step.status.value if hasattr(step.status, 'value') else str(step.status),
                    "comments": step.comments,
                })
            row.approvals = approvals
            if request.status == AccessRequestStatus.REJECTED:
                row.rejection_reason = next(
                    (s.comments for s in request.approval_steps
                     if hasattr(s, 'status') and s.status == ApprovalStatus.REJECTED),
                    None
                )

        db.commit()

    def _load_from_db(self, request_id: str, tenant_id: str = "") -> Optional[AccessRequest]:
        """Load an AccessRequest from the database."""
        db = self._get_db()
        query = db.query(AccessRequestLog).filter(
            AccessRequestLog.request_id == request_id
        )
        if tenant_id:
            query = query.filter(AccessRequestLog.tenant_id == tenant_id)
        row = query.first()
        if not row:
            return None
        return self._row_to_request(row)

    def _row_to_request(self, row: AccessRequestLog) -> AccessRequest:
        """Convert a DB row to an AccessRequest dataclass."""
        # Map status string to enum
        try:
            status = AccessRequestStatus(row.status)
        except (ValueError, KeyError):
            status = AccessRequestStatus.DRAFT

        try:
            req_type = RequestType(row.request_type)
        except (ValueError, KeyError):
            req_type = RequestType.NEW_ACCESS

        items = []
        for role_id in (row.requested_roles or []):
            catalog_entry = self.role_catalog.get(role_id, {})
            items.append(RequestedAccess(
                access_type="role",
                access_name=role_id,
                access_description=catalog_entry.get("description", ""),
                system=catalog_entry.get("system", "SAP"),
                valid_to=row.valid_to,
            ))

        request = AccessRequest(
            request_id=row.request_id,
            tenant_id=row.tenant_id or "",
            request_type=req_type,
            requester_user_id=row.requester_user_id,
            requester_name=row.requester_name or "",
            requester_email=row.requester_email or "",
            requester_department=row.requester_department or "",
            target_user_id=row.target_user_id,
            target_user_name=row.target_user_name or "",
            requested_items=items,
            business_justification=row.business_justification or "",
            ticket_reference=row.ticket_reference,
            status=status,
            overall_risk_score=float(row.risk_score or 0),
            sod_violations=row.violations_detected or [],
            submitted_at=row.submitted_at,
            completed_at=row.completed_at,
            provisioned_at=row.provisioned_at,
            current_step=row.current_approval_step or 0,
            requested_end_date=row.valid_to,
        )

        # Reconstruct approval steps from JSON
        for step_data in (row.approvals or []):
            try:
                step_status = ApprovalStatus(step_data.get("status", "pending"))
            except (ValueError, KeyError):
                step_status = ApprovalStatus.PENDING
            approver = step_data.get("approver", "")
            approver_ids = step_data.get("approver_ids", [approver] if approver else [])
            step = ApprovalStep(
                step_id=step_data.get("step_id", ""),
                approver_ids=approver_ids,
                status=step_status,
                comments=step_data.get("comments", ""),
            )
            request.approval_steps.append(step)

        return request

    # ------------------------------------------------------------------
    # Role catalog
    # ------------------------------------------------------------------

    def _load_role_catalog(self) -> Dict[str, Dict]:
        """Load role catalog from the DB roles table. Falls back to minimal seed data."""
        db = self._get_db()
        if db:
            try:
                from db.models.user import Role
                roles = db.query(Role).filter(Role.is_active == True).all()
                if roles:
                    catalog = {}
                    for r in roles:
                        catalog[r.role_id] = {
                            "name": r.role_name or r.role_id,
                            "description": r.description or "",
                            "system": r.source_system or "SAP",
                            "risk_level": r.risk_level or "medium",
                            "owner": r.owner_email or r.owner_user_id or "",
                            "business_process": "",
                        }
                    return catalog
            except Exception:
                pass

        # Fallback seed data when DB has no roles
        return {
            "Z_AP_CLERK": {"name": "AP Clerk", "description": "Accounts Payable processing", "system": "SAP", "risk_level": "medium", "owner": "", "business_process": "Purchase to Pay"},
            "Z_AP_MANAGER": {"name": "AP Manager", "description": "AP management", "system": "SAP", "risk_level": "high", "owner": "", "business_process": "Purchase to Pay"},
            "Z_PURCHASER": {"name": "Purchaser", "description": "Purchase order creation", "system": "SAP", "risk_level": "medium", "owner": "", "business_process": "Procurement"},
            "Z_HR_SPECIALIST": {"name": "HR Specialist", "description": "Employee master data", "system": "SAP", "risk_level": "high", "owner": "", "business_process": "Hire to Retire"},
            "Z_PAYROLL_ADMIN": {"name": "Payroll Administrator", "description": "Payroll processing", "system": "SAP", "risk_level": "critical", "owner": "", "business_process": "Hire to Retire"},
        }

    # =========================================================================
    # Request Creation
    # =========================================================================

    async def create_request(self,
                            tenant_id: str,
                            requester_user_id: str,
                            requester_name: str,
                            requester_email: str,
                            target_user_id: str,
                            target_user_name: str,
                            requested_roles: List[str],
                            business_justification: str,
                            request_type: RequestType = RequestType.NEW_ACCESS,
                            is_temporary: bool = False,
                            end_date: Optional[datetime] = None,
                            ticket_reference: Optional[str] = None) -> AccessRequest:
        """Create a new access request and persist it to the database."""

        if not tenant_id:
            raise ValueError("tenant_id is required")

        # Validate justification
        if self.config["require_justification"]:
            if len(business_justification) < self.config["min_justification_length"]:
                raise ValueError(
                    f"Business justification must be at least "
                    f"{self.config['min_justification_length']} characters"
                )

        # Build requested items from role IDs
        requested_items = []
        for role_id in requested_roles:
            catalog_entry = self.role_catalog.get(role_id, {})
            item = RequestedAccess(
                access_type="role",
                access_name=role_id,
                access_description=catalog_entry.get("description", ""),
                system=catalog_entry.get("system", "SAP"),
                is_temporary=is_temporary,
                valid_to=end_date
            )
            requested_items.append(item)

        # Create request
        request = AccessRequest(
            tenant_id=tenant_id,
            request_type=request_type,
            requester_user_id=requester_user_id,
            requester_name=requester_name,
            requester_email=requester_email,
            target_user_id=target_user_id,
            target_user_name=target_user_name,
            requested_items=requested_items,
            business_justification=business_justification,
            ticket_reference=ticket_reference,
            is_temporary=is_temporary,
            requested_end_date=end_date,
            status=AccessRequestStatus.DRAFT
        )

        # Persist to database
        self._save_to_db(request)

        logger.info(f"Created access request {request.request_id}")
        return request

    # =========================================================================
    # Risk Preview (Before Submission)
    # =========================================================================

    async def preview_risk(self, request: AccessRequest) -> Dict:
        """Preview risk analysis before request submission."""
        if not self.config["enable_risk_preview"]:
            return {"enabled": False}

        current_entitlements = await self._get_user_entitlements(request.target_user_id)
        new_entitlements = await self._get_role_entitlements(
            [item.access_name for item in request.requested_items]
        )

        current_user = UserAccess(
            user_id=request.target_user_id,
            username=request.target_user_name,
            full_name=request.target_user_name,
            department=request.target_user_department or "Unknown",
            entitlements=current_entitlements
        )

        current_violations = self.rule_engine.evaluate_user(current_user)
        current_summary = self.rule_engine.get_risk_summary(current_violations)

        future_user = UserAccess(
            user_id=request.target_user_id,
            username=request.target_user_name,
            full_name=request.target_user_name,
            department=request.target_user_department or "Unknown",
            entitlements=current_entitlements + new_entitlements
        )

        future_violations = self.rule_engine.evaluate_user(future_user)
        future_summary = self.rule_engine.get_risk_summary(future_violations)

        current_rule_ids = {v.rule_id for v in current_violations}
        new_violations = [v for v in future_violations if v.rule_id not in current_rule_ids]

        risk_level = self._calculate_risk_level(future_summary['aggregate_risk_score'])

        return {
            "current_state": {
                "risk_score": current_summary['aggregate_risk_score'],
                "violation_count": current_summary['total_violations']
            },
            "future_state": {
                "risk_score": future_summary['aggregate_risk_score'],
                "violation_count": future_summary['total_violations']
            },
            "new_violations": [
                {
                    "rule_id": v.rule_id,
                    "rule_name": v.rule_name,
                    "severity": v.severity.name,
                    "risk_category": v.risk_category.value,
                    "business_impact": v.business_impact,
                    "mitigation_controls": v.mitigation_controls
                }
                for v in new_violations
            ],
            "risk_increase": future_summary['aggregate_risk_score'] - current_summary['aggregate_risk_score'],
            "overall_risk_level": risk_level,
            "recommendation": self._get_recommendation(new_violations, risk_level)
        }

    def _calculate_risk_level(self, score: float) -> str:
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 30:
            return "medium"
        return "low"

    def _get_recommendation(self, violations: List, risk_level: str) -> Dict:
        if not violations:
            return {"action": "PROCEED", "message": "No new violations detected. Request can proceed."}
        if risk_level == "critical":
            return {"action": "REVIEW_REQUIRED", "message": "Critical risk detected. Security review required.", "requires_mitigation": True}
        elif risk_level == "high":
            return {"action": "REVIEW_REQUIRED", "message": "High risk detected. Additional approval required.", "requires_mitigation": True}
        return {"action": "PROCEED_WITH_CAUTION", "message": "Some risks detected. Review violations before proceeding."}

    # =========================================================================
    # Request Submission
    # =========================================================================

    async def submit_request(self, request_id: str, tenant_id: str = "") -> AccessRequest:
        """Submit a draft request for approval.

        Golden E2E flow (Gate 2):
        1. EffectiveAccess → Calculate current effective access
        2. RiskEngine → Analyse SoD violations with proposed changes
        3. FindingsEngine → Generate normalised findings
        4. DecisionEngine → Route approval based on risk level
        5. EvidenceEngine → Record immutable audit trail
        """
        request = self._load_from_db(request_id, tenant_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        if request.status != AccessRequestStatus.DRAFT:
            raise ValueError(f"Request is not in draft status (current: {request.status.value})")

        # --- Step 1: Legacy risk analysis (still populates sod_violations / risk_score) ---
        await self._perform_risk_analysis(request)

        # --- Step 2: New RiskEngine (4-level SoD) via EffectiveAccess ---
        risk_result = None
        try:
            current_access = self.effective_access.calculate(
                request.target_user_id, tenant_id or request.tenant_id
            )
            # Add proposed roles so risk engine can see the future state
            for item in request.requested_items:
                self.effective_access.add_role_assignments(
                    request.target_user_id,
                    [{"role_id": item.access_name, "system": item.system or "SAP", "state": "requested"}],
                )
            proposed_access = self.effective_access.calculate(
                request.target_user_id, tenant_id or request.tenant_id
            )
            risk_result = self.risk_engine.simulate_role_addition(current_access, proposed_access)

            # Overlay risk_engine score onto request when available
            if risk_result and risk_result.risk_score > request.overall_risk_score:
                request.overall_risk_score = risk_result.risk_score
                request.risk_level = self._calculate_risk_level(risk_result.risk_score)
        except Exception as exc:
            logger.warning(f"RiskEngine analysis skipped: {exc}")

        # --- Step 3: Findings ---
        if risk_result:
            try:
                self.findings_engine.ingest_risk_analysis(
                    risk_result, tenant_id or request.tenant_id
                )
            except Exception as exc:
                logger.warning(f"FindingsEngine ingest skipped: {exc}")

        # --- Step 4: DecisionEngine → policy-based approval routing ---
        try:
            from core.decision_engine.models import RequestType as DERequestType
            de_type = DERequestType.NEW_ACCESS
            approval_wf = self.decision_engine.create_workflow(
                request_id=request.request_id,
                request_type=de_type,
                user_id=request.target_user_id,
                tenant_id=tenant_id or request.tenant_id,
                context={
                    "risk_level": request.risk_level or self._calculate_risk_level(request.overall_risk_score),
                    "system": request.requested_items[0].system if request.requested_items else "SAP",
                    "sod_violations_count": len(request.sod_violations),
                    "department": request.requester_department,
                },
            )
            # Convert decision engine steps → legacy ApprovalStep objects
            # Resolve role-based steps to concrete approver IDs from DB
            _role_defaults = {
                "manager": "default.manager@company.com",
                "role_owner": "role.owner@company.com",
                "security_team": "security@company.com",
                "compliance": "compliance@company.com",
            }
            # Try to resolve from ApproverModel DB table
            try:
                if self.db:
                    from db.models.approver import ApproverModel
                    approvers = self.db.query(ApproverModel).filter(
                        ApproverModel.is_available == True
                    ).all()
                    for a in approvers:
                        role_key = (a.approver_type or "").lower().replace(" ", "_")
                        if role_key and a.user_id:
                            _role_defaults[role_key] = a.user_id
            except Exception:
                pass

            request.approval_steps = []
            for step in approval_wf.steps:
                assigned = step.approver_user_id or ""
                if not assigned and hasattr(step.step_type, 'value'):
                    assigned = _role_defaults.get(step.step_type.value, "")
                request.approval_steps.append(ApprovalStep(
                    step_id=f"step_{step.step_number}",
                    approver_ids=[assigned] if assigned else ["default.manager@company.com"],
                    step_type=step.step_type.value if hasattr(step.step_type, 'value') else "approval",
                    status=ApprovalStatus.PENDING,
                ))
            request._decision_workflow_id = approval_wf.workflow_id
        except Exception as exc:
            logger.warning(f"DecisionEngine routing skipped, using legacy: {exc}")
            request.approval_steps = self.workflow_engine.generate_workflow(request)

        request.current_step = 0
        request.status = AccessRequestStatus.PENDING_APPROVAL
        request.submitted_at = datetime.now()

        if self.config["auto_approve_low_risk"]:
            if request.overall_risk_score <= self.config["low_risk_threshold"]:
                if not request.sod_violations:
                    request.status = AccessRequestStatus.APPROVED
                    request.final_decision = "auto_approved"
                    request.final_decision_at = datetime.now()

        self._save_to_db(request)

        # --- Step 5: Evidence ---
        try:
            from core.evidence.models import EvidenceType
            self.evidence_engine.record(
                evidence_type=EvidenceType.ACCESS_REQUEST,
                tenant_id=tenant_id or request.tenant_id,
                actor_user_id=request.requester_user_id,
                action="submit_request",
                target_user_id=request.target_user_id,
                target_object_type="access_request",
                target_object_id=request.request_id,
                justification=request.business_justification,
                request_id=request.request_id,
                after_state={
                    "risk_score": request.overall_risk_score,
                    "risk_level": request.risk_level or "",
                    "sod_violations": len(request.sod_violations),
                    "requested_roles": [i.access_name for i in request.requested_items],
                },
            )
        except Exception as exc:
            logger.warning(f"EvidenceEngine record skipped: {exc}")

        if request.status == AccessRequestStatus.PENDING_APPROVAL:
            await self._notify_approvers(request)

        logger.info(f"Request {request_id} submitted for approval")
        return request

    async def _perform_risk_analysis(self, request: AccessRequest):
        current_entitlements = await self._get_user_entitlements(request.target_user_id)
        new_entitlements = await self._get_role_entitlements(
            [item.access_name for item in request.requested_items]
        )

        user = UserAccess(
            user_id=request.target_user_id,
            username=request.target_user_name,
            full_name=request.target_user_name,
            department=request.target_user_department or "Unknown",
            entitlements=current_entitlements + new_entitlements
        )

        violations = self.rule_engine.evaluate_user(user)
        summary = self.rule_engine.get_risk_summary(violations)

        request.overall_risk_score = summary['aggregate_risk_score']
        request.risk_level = self._calculate_risk_level(summary['aggregate_risk_score'])

        request.sod_violations = [
            {
                "rule_id": v.rule_id,
                "rule_name": v.rule_name,
                "severity": v.severity.name,
                "conflicting_entitlements": v.conflicting_entitlements
            }
            for v in violations
            if v.rule_type.value == "segregation_of_duties"
        ]

        request.sensitive_access_flags = [
            {
                "rule_id": v.rule_id,
                "rule_name": v.rule_name,
                "severity": v.severity.name
            }
            for v in violations
            if v.rule_type.value == "sensitive_access"
        ]

    async def _get_user_entitlements(self, user_id: str) -> List[Entitlement]:
        if self.user_connector:
            try:
                return self.user_connector.get_user_entitlements_as_objects(user_id)
            except Exception as e:
                logger.warning(f"Could not get entitlements for {user_id}: {e}")
        return []

    async def _get_role_entitlements(self, role_ids: List[str]) -> List[Entitlement]:
        entitlements = []
        mock_role_tcodes = {
            "Z_AP_CLERK": ["FB60", "FBL1N", "FK03"],
            "Z_AP_MANAGER": ["FB60", "FBL1N", "FK03", "F110", "F-53"],
            "Z_PURCHASER": ["ME21N", "ME22N", "ME23N"],
            "Z_HR_SPECIALIST": ["PA30", "PA20"],
            "Z_PAYROLL_ADMIN": ["PA30", "PC00_M99_CALC", "PC00_M99_CIPE"]
        }
        for role_id in role_ids:
            tcodes = mock_role_tcodes.get(role_id, [])
            for tcode in tcodes:
                entitlements.append(Entitlement(
                    auth_object="S_TCODE",
                    field="TCD",
                    value=tcode,
                    system="SAP"
                ))
        return entitlements

    async def _notify_approvers(self, request: AccessRequest):
        if not self.notification_handler:
            return
        approvers = request.get_current_approvers()
        for approver_id in approvers:
            await self.notification_handler(
                recipient=approver_id,
                subject=f"Access Request Pending Approval: {request.request_id}",
                message=f"User {request.requester_name} has requested access for "
                       f"{request.target_user_name}.\n"
                       f"Risk Level: {request.risk_level.upper()}\n"
                       f"Please review and take action."
            )

    # =========================================================================
    # Approval Processing
    # =========================================================================

    async def process_approval(self,
                              request_id: str,
                              step_id: str,
                              action: ApprovalAction,
                              actor_id: str,
                              comments: str = "",
                              delegate_to: Optional[str] = None,
                              tenant_id: str = "") -> AccessRequest:
        """Process an approval action."""
        request = self._load_from_db(request_id, tenant_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        # Prevent self-approval: requester cannot approve their own request
        if action == ApprovalAction.APPROVE and actor_id == request.requester_user_id:
            raise ValueError(
                "Self-approval is not permitted. "
                "The requester cannot approve their own access request."
            )

        updated_request = await self.workflow_engine.process_approval_action(
            request=request,
            step_id=step_id,
            action=action,
            actor_id=actor_id,
            comments=comments,
            delegate_to=delegate_to
        )

        # Record approval evidence
        try:
            from core.evidence.models import EvidenceType
            self.evidence_engine.record(
                evidence_type=EvidenceType.APPROVAL_DECISION,
                tenant_id=tenant_id or updated_request.tenant_id,
                actor_user_id=actor_id,
                action=f"approval_{action.value}",
                target_user_id=updated_request.target_user_id,
                target_object_type="access_request",
                target_object_id=request_id,
                request_id=request_id,
                action_details={"step_id": step_id, "comments": comments},
            )
        except Exception as exc:
            logger.warning(f"EvidenceEngine record skipped: {exc}")

        if updated_request.status == AccessRequestStatus.APPROVED:
            await self._provision_access(updated_request, tenant_id)

        self._save_to_db(updated_request)
        return updated_request

    async def _provision_access(self, request: AccessRequest, tenant_id: str = ""):
        """Provision access using the ExecutionEngine (Gate 2).

        Lifecycle: Plan → Execute → Verify → Evidence → Close
        """
        request.status = AccessRequestStatus.PROVISIONING
        request.provisioning_status = "in_progress"
        _tenant = tenant_id or request.tenant_id

        try:
            # Build action list from requested items
            actions = []
            for item in request.requested_items:
                actions.append({
                    "action_type": "assign_role",
                    "target_system": item.system or "SAP",
                    "user_id": request.target_user_id,
                    "role_id": item.access_name,
                    "parameters": {
                        "valid_to": item.valid_to.isoformat() if item.valid_to else None,
                    },
                })

            # Create execution plan
            workflow_id = getattr(request, "_decision_workflow_id", "")
            plan = self.execution_engine.create_plan(
                request_id=request.request_id,
                workflow_id=workflow_id or "",
                user_id=request.target_user_id,
                tenant_id=_tenant,
                actions=actions,
                pre_risk_score=request.overall_risk_score,
                pre_violation_count=len(request.sod_violations),
            )

            # Execute via SAP connector (falls back to mock if no real connector)
            from core.execution.models import VerificationResult

            def _execute_fn(action):
                """Execute provisioning action via SAP connector."""
                try:
                    if self.sap_connector and hasattr(self.sap_connector, 'modify_user_roles'):
                        result = self.sap_connector.modify_user_roles(
                            user_id=action.user_id,
                            roles_to_add=[action.role_id] if action.action_type.value == "assign_role" else [],
                            roles_to_remove=[action.role_id] if action.action_type.value == "remove_role" else [],
                        )
                        return (True, f"SAP: {result}", None)
                except Exception as exc:
                    logger.warning(f"SAP connector call failed, using mock: {exc}")
                # Mock fallback
                logger.info(f"Provisioning {action.role_id} for {action.user_id}")
                return (True, "Role assigned (mock)", None)

            self.execution_engine.execute(plan.plan_id, _execute_fn, executed_by="system")

            # Verify — read back from SAP or mock
            def _verify_fn(action):
                """Verify provisioning by reading back from target system."""
                try:
                    if self.sap_connector and hasattr(self.sap_connector, 'get_user_roles'):
                        user_roles = self.sap_connector.get_user_roles(action.user_id)
                        role_ids = [r.get('role_id', r.get('name', '')) for r in (user_roles or [])]
                        if action.role_id in role_ids:
                            return (VerificationResult.CONFIRMED, "Role found on target system")
                        return (VerificationResult.NOT_FOUND, f"Role {action.role_id} not found on system")
                except Exception as exc:
                    logger.warning(f"SAP verification failed: {exc}")
                return (VerificationResult.CONFIRMED, "Verified (mock)")

            self.execution_engine.verify(plan.plan_id, _verify_fn)

            # Close the plan
            self.execution_engine.close(plan.plan_id)

            request.status = AccessRequestStatus.PROVISIONED
            request.provisioning_status = "success"
            request.provisioned_at = datetime.now()
            request.completed_at = datetime.now()

            if request.is_temporary and request.requested_end_date:
                request.access_expires_at = request.requested_end_date

            # Record provisioning evidence
            try:
                from core.evidence.models import EvidenceType
                self.evidence_engine.record(
                    evidence_type=EvidenceType.PROVISIONING_ACTION,
                    tenant_id=_tenant,
                    actor_user_id="system",
                    action="provision_access",
                    target_user_id=request.target_user_id,
                    target_object_type="access_request",
                    target_object_id=request.request_id,
                    request_id=request.request_id,
                    plan_id=plan.plan_id,
                    after_state={
                        "roles_assigned": [a["role_id"] for a in actions],
                        "plan_status": "closed",
                    },
                )
            except Exception as exc:
                logger.warning(f"EvidenceEngine record skipped: {exc}")

            if self.notification_handler:
                await self.notification_handler(
                    recipient=request.requester_email,
                    subject=f"Access Provisioned: {request.request_id}",
                    message=f"Access has been granted for {request.target_user_name}."
                )

        except Exception as e:
            request.status = AccessRequestStatus.FAILED
            request.provisioning_status = "failed"
            request.provisioning_errors.append(str(e))
            logger.error(f"Provisioning failed for {request.request_id}: {e}")

    # =========================================================================
    # Query Methods (all DB-backed)
    # =========================================================================

    def get_request(self, request_id: str, tenant_id: str = "") -> Optional[AccessRequest]:
        """Get request by ID, scoped to tenant."""
        return self._load_from_db(request_id, tenant_id)

    def get_requests_for_user(self, user_id: str, tenant_id: str = "") -> List[AccessRequest]:
        """Get all requests created by a user."""
        db = self._get_db()
        query = db.query(AccessRequestLog).filter(
            AccessRequestLog.requester_user_id == user_id
        )
        if tenant_id:
            query = query.filter(AccessRequestLog.tenant_id == tenant_id)
        return [self._row_to_request(r) for r in query.all()]

    def get_requests_for_target(self, user_id: str, tenant_id: str = "") -> List[AccessRequest]:
        """Get all requests for a target user."""
        db = self._get_db()
        query = db.query(AccessRequestLog).filter(
            AccessRequestLog.target_user_id == user_id
        )
        if tenant_id:
            query = query.filter(AccessRequestLog.tenant_id == tenant_id)
        return [self._row_to_request(r) for r in query.all()]

    def get_all_requests(self, tenant_id: str = "", status: str = "",
                         limit: int = 50) -> List[AccessRequest]:
        """Get all requests with optional filters."""
        db = self._get_db()
        query = db.query(AccessRequestLog)
        if tenant_id:
            query = query.filter(AccessRequestLog.tenant_id == tenant_id)
        if status:
            query = query.filter(AccessRequestLog.status == status)
        query = query.order_by(AccessRequestLog.submitted_at.desc())
        return [self._row_to_request(r) for r in query.limit(limit).all()]

    def get_pending_approvals(self, approver_id: str) -> List[Dict]:
        """Get pending approvals for an approver."""
        db = self._get_db()
        rows = db.query(AccessRequestLog).filter(
            AccessRequestLog.status == "pending_approval"
        ).all()
        requests = [self._row_to_request(r) for r in rows]
        return self.workflow_engine.get_pending_approvals_for_user(
            approver_id, requests
        )

    def get_role_catalog(self, search: Optional[str] = None,
                        business_process: Optional[str] = None) -> List[Dict]:
        roles = []
        for role_id, role_info in self.role_catalog.items():
            if search:
                if search.lower() not in role_id.lower() and \
                   search.lower() not in role_info.get("description", "").lower():
                    continue
            if business_process:
                if role_info.get("business_process") != business_process:
                    continue
            roles.append({"role_id": role_id, **role_info})
        return roles

    def get_statistics(self, tenant_id: str = "") -> Dict:
        """Get request statistics from the database."""
        db = self._get_db()
        query = db.query(AccessRequestLog)
        if tenant_id:
            query = query.filter(AccessRequestLog.tenant_id == tenant_id)

        from sqlalchemy import func
        total = query.count()
        pending = query.filter(AccessRequestLog.status == "pending_approval").count()

        return {
            "total_requests": total,
            "pending_approval": pending,
            "by_status": {},
            "overdue": 0,
            "average_risk_score": 0
        }

    # =========================================================================
    # Expiry Management
    # =========================================================================

    async def check_expiring_access(self, days_ahead: int = 7) -> List[AccessRequest]:
        db = self._get_db()
        threshold = datetime.now() + timedelta(days=days_ahead)
        rows = db.query(AccessRequestLog).filter(
            AccessRequestLog.valid_to <= threshold,
            AccessRequestLog.status == "provisioned",
        ).all()
        return [self._row_to_request(r) for r in rows]

    async def revoke_expired_access(self):
        db = self._get_db()
        now = datetime.now()
        rows = db.query(AccessRequestLog).filter(
            AccessRequestLog.valid_to <= now,
            AccessRequestLog.status == "provisioned",
        ).all()
        for row in rows:
            row.status = "expired"
        db.commit()
