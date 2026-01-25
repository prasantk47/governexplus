"""
Access Request Manager

Central manager for the access request lifecycle including:
- Request creation and submission
- Risk analysis before approval
- Workflow orchestration
- Provisioning coordination
- Expiry management
"""

import uuid
import logging
from dataclasses import asdict
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta

from .models import (
    AccessRequest, AccessRequestStatus, RequestType,
    RequestedAccess, ApprovalStep, ApprovalStatus, ApprovalAction
)
from .workflow import WorkflowEngine, ApprovalRule
from core.rules import RuleEngine
from core.rules.models import UserAccess, Entitlement

logger = logging.getLogger(__name__)


class AccessRequestManager:
    """
    Central manager for access request operations.

    Coordinates between:
    - Risk analysis engine
    - Approval workflow engine
    - User/role connectors
    - Provisioning systems
    - Notification services
    """

    def __init__(self,
                 rule_engine: Optional[RuleEngine] = None,
                 workflow_engine: Optional[WorkflowEngine] = None,
                 user_connector=None,
                 notification_handler: Optional[Callable] = None):
        """
        Initialize Access Request Manager.

        Args:
            rule_engine: Risk analysis engine
            workflow_engine: Approval workflow engine
            user_connector: Connector for user/role data
            notification_handler: Function to send notifications
        """
        self.rule_engine = rule_engine or RuleEngine()
        self.workflow_engine = workflow_engine or WorkflowEngine(
            notification_handler=notification_handler
        )
        self.user_connector = user_connector
        self.notification_handler = notification_handler

        # In-memory storage (replace with database in production)
        self.requests: Dict[str, AccessRequest] = {}

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

    def _load_role_catalog(self) -> Dict[str, Dict]:
        """Load role catalog with business-friendly descriptions"""
        return {
            "Z_AP_CLERK": {
                "name": "AP Clerk",
                "description": "Accounts Payable processing - invoice entry and vendor inquiries",
                "system": "SAP",
                "risk_level": "medium",
                "owner": "finance.lead@company.com",
                "business_process": "Purchase to Pay"
            },
            "Z_AP_MANAGER": {
                "name": "AP Manager",
                "description": "Accounts Payable management - approvals and reporting",
                "system": "SAP",
                "risk_level": "high",
                "owner": "finance.director@company.com",
                "business_process": "Purchase to Pay"
            },
            "Z_PURCHASER": {
                "name": "Purchaser",
                "description": "Purchase order creation and management",
                "system": "SAP",
                "risk_level": "medium",
                "owner": "procurement.lead@company.com",
                "business_process": "Procurement"
            },
            "Z_HR_SPECIALIST": {
                "name": "HR Specialist",
                "description": "Employee master data maintenance",
                "system": "SAP",
                "risk_level": "high",
                "owner": "hr.director@company.com",
                "business_process": "Hire to Retire"
            },
            "Z_PAYROLL_ADMIN": {
                "name": "Payroll Administrator",
                "description": "Payroll processing and reporting",
                "system": "SAP",
                "risk_level": "critical",
                "owner": "payroll.manager@company.com",
                "business_process": "Hire to Retire"
            }
        }

    # =========================================================================
    # Request Creation
    # =========================================================================

    async def create_request(self,
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
        """
        Create a new access request.

        Args:
            requester_user_id: ID of user creating request
            requester_name: Name of requester
            requester_email: Email of requester
            target_user_id: User who will receive access
            target_user_name: Name of target user
            requested_roles: List of role IDs to request
            business_justification: Reason for request
            request_type: Type of request
            is_temporary: Whether access should expire
            end_date: Expiry date for temporary access
            ticket_reference: Related ticket number

        Returns:
            Created AccessRequest
        """

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

        # Store request
        self.requests[request.request_id] = request

        logger.info(f"Created access request {request.request_id}")

        return request

    # =========================================================================
    # Risk Preview (Before Submission)
    # =========================================================================

    async def preview_risk(self, request: AccessRequest) -> Dict:
        """
        Preview risk analysis before request submission.

        Shows what violations would be introduced by the requested access.
        """
        if not self.config["enable_risk_preview"]:
            return {"enabled": False}

        # Get target user's current entitlements
        current_entitlements = await self._get_user_entitlements(request.target_user_id)

        # Get entitlements from requested roles
        new_entitlements = await self._get_role_entitlements(
            [item.access_name for item in request.requested_items]
        )

        # Build current user access model
        current_user = UserAccess(
            user_id=request.target_user_id,
            username=request.target_user_name,
            full_name=request.target_user_name,
            department=request.target_user_department or "Unknown",
            entitlements=current_entitlements
        )

        # Analyze current state
        current_violations = self.rule_engine.evaluate_user(current_user)
        current_summary = self.rule_engine.get_risk_summary(current_violations)

        # Build future user access model
        future_user = UserAccess(
            user_id=request.target_user_id,
            username=request.target_user_name,
            full_name=request.target_user_name,
            department=request.target_user_department or "Unknown",
            entitlements=current_entitlements + new_entitlements
        )

        # Analyze future state
        future_violations = self.rule_engine.evaluate_user(future_user)
        future_summary = self.rule_engine.get_risk_summary(future_violations)

        # Find NEW violations (introduced by this request)
        current_rule_ids = {v.rule_id for v in current_violations}
        new_violations = [v for v in future_violations if v.rule_id not in current_rule_ids]

        # Determine risk level
        risk_level = self._calculate_risk_level(future_summary['aggregate_risk_score'])

        preview = {
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

        return preview

    def _calculate_risk_level(self, score: float) -> str:
        """Calculate risk level from score"""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 30:
            return "medium"
        return "low"

    def _get_recommendation(self, violations: List, risk_level: str) -> Dict:
        """Generate recommendation based on analysis"""
        if not violations:
            return {
                "action": "PROCEED",
                "message": "No new violations detected. Request can proceed."
            }

        if risk_level == "critical":
            return {
                "action": "REVIEW_REQUIRED",
                "message": "Critical risk detected. Security review required before approval.",
                "requires_mitigation": True
            }
        elif risk_level == "high":
            return {
                "action": "REVIEW_REQUIRED",
                "message": "High risk detected. Additional approval required.",
                "requires_mitigation": True
            }
        else:
            return {
                "action": "PROCEED_WITH_CAUTION",
                "message": "Some risks detected. Review violations before proceeding."
            }

    # =========================================================================
    # Request Submission
    # =========================================================================

    async def submit_request(self, request_id: str) -> AccessRequest:
        """
        Submit a draft request for approval.

        This triggers:
        1. Full risk analysis
        2. Workflow generation
        3. Notification to approvers
        """
        request = self.requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        if request.status != AccessRequestStatus.DRAFT:
            raise ValueError(f"Request is not in draft status (current: {request.status.value})")

        # Perform full risk analysis
        await self._perform_risk_analysis(request)

        # Generate approval workflow
        request.approval_steps = self.workflow_engine.generate_workflow(request)
        request.current_step = 0

        # Update status
        request.status = AccessRequestStatus.PENDING_APPROVAL
        request.submitted_at = datetime.now()

        # Check for auto-approval
        if self.config["auto_approve_low_risk"]:
            if request.overall_risk_score <= self.config["low_risk_threshold"]:
                if not request.sod_violations:
                    # Auto-approve
                    request.status = AccessRequestStatus.APPROVED
                    request.final_decision = "auto_approved"
                    request.final_decision_at = datetime.now()
                    logger.info(f"Request {request_id} auto-approved (low risk)")

        # Notify first approvers
        if request.status == AccessRequestStatus.PENDING_APPROVAL:
            await self._notify_approvers(request)

        logger.info(f"Request {request_id} submitted for approval")

        return request

    async def _perform_risk_analysis(self, request: AccessRequest):
        """Perform comprehensive risk analysis"""

        # Get current + future entitlements
        current_entitlements = await self._get_user_entitlements(request.target_user_id)
        new_entitlements = await self._get_role_entitlements(
            [item.access_name for item in request.requested_items]
        )

        # Build user model
        user = UserAccess(
            user_id=request.target_user_id,
            username=request.target_user_name,
            full_name=request.target_user_name,
            department=request.target_user_department or "Unknown",
            entitlements=current_entitlements + new_entitlements
        )

        # Run analysis
        violations = self.rule_engine.evaluate_user(user)
        summary = self.rule_engine.get_risk_summary(violations)

        # Update request with results
        request.overall_risk_score = summary['aggregate_risk_score']
        request.risk_level = self._calculate_risk_level(summary['aggregate_risk_score'])

        # Store SoD violations
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

        # Store sensitive access flags
        request.sensitive_access_flags = [
            {
                "rule_id": v.rule_id,
                "rule_name": v.rule_name,
                "severity": v.severity.name
            }
            for v in violations
            if v.rule_type.value == "sensitive_access"
        ]

        # Update individual items with their risk scores
        for item in request.requested_items:
            item_violations = [
                v for v in violations
                if any(item.access_name in str(e) for e in v.conflicting_entitlements)
            ]
            item.risk_score = sum(v.severity.value for v in item_violations)
            item.violations = [
                {"rule_id": v.rule_id, "rule_name": v.rule_name}
                for v in item_violations
            ]

    async def _get_user_entitlements(self, user_id: str) -> List[Entitlement]:
        """Get user's current entitlements"""
        if self.user_connector:
            try:
                return self.user_connector.get_user_entitlements_as_objects(user_id)
            except Exception as e:
                logger.warning(f"Could not get entitlements for {user_id}: {e}")

        return []

    async def _get_role_entitlements(self, role_ids: List[str]) -> List[Entitlement]:
        """Get entitlements from roles"""
        entitlements = []

        # Mock entitlements for demo
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
        """Notify current approvers"""
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
                              delegate_to: Optional[str] = None) -> AccessRequest:
        """
        Process an approval action.
        """
        request = self.requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        # Delegate to workflow engine
        updated_request = await self.workflow_engine.process_approval_action(
            request=request,
            step_id=step_id,
            action=action,
            actor_id=actor_id,
            comments=comments,
            delegate_to=delegate_to
        )

        # If approved, start provisioning
        if updated_request.status == AccessRequestStatus.APPROVED:
            await self._provision_access(updated_request)

        return updated_request

    async def _provision_access(self, request: AccessRequest):
        """Provision approved access"""
        request.status = AccessRequestStatus.PROVISIONING
        request.provisioning_status = "in_progress"

        try:
            # Would call SAP connector to provision
            # For demo, just mark as complete
            for item in request.requested_items:
                logger.info(f"Provisioning {item.access_name} for {request.target_user_id}")

            request.status = AccessRequestStatus.PROVISIONED
            request.provisioning_status = "success"
            request.provisioned_at = datetime.now()
            request.completed_at = datetime.now()

            # Set expiry if temporary
            if request.is_temporary and request.requested_end_date:
                request.access_expires_at = request.requested_end_date

            # Notify requester
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
    # Query Methods
    # =========================================================================

    def get_request(self, request_id: str) -> Optional[AccessRequest]:
        """Get request by ID"""
        return self.requests.get(request_id)

    def get_requests_for_user(self, user_id: str) -> List[AccessRequest]:
        """Get all requests created by a user"""
        return [
            r for r in self.requests.values()
            if r.requester_user_id == user_id
        ]

    def get_requests_for_target(self, user_id: str) -> List[AccessRequest]:
        """Get all requests for a target user"""
        return [
            r for r in self.requests.values()
            if r.target_user_id == user_id
        ]

    def get_pending_approvals(self, approver_id: str) -> List[Dict]:
        """Get pending approvals for an approver"""
        return self.workflow_engine.get_pending_approvals_for_user(
            approver_id,
            list(self.requests.values())
        )

    def get_role_catalog(self, search: Optional[str] = None,
                        business_process: Optional[str] = None) -> List[Dict]:
        """Get available roles for request"""
        roles = []

        for role_id, role_info in self.role_catalog.items():
            if search:
                if search.lower() not in role_id.lower() and \
                   search.lower() not in role_info.get("description", "").lower():
                    continue

            if business_process:
                if role_info.get("business_process") != business_process:
                    continue

            roles.append({
                "role_id": role_id,
                **role_info
            })

        return roles

    def get_statistics(self) -> Dict:
        """Get request statistics"""
        total = len(self.requests)
        by_status = {}

        for request in self.requests.values():
            status = request.status.value
            by_status[status] = by_status.get(status, 0) + 1

        pending = sum(1 for r in self.requests.values()
                     if r.status == AccessRequestStatus.PENDING_APPROVAL)

        overdue = sum(1 for r in self.requests.values()
                     if r.status == AccessRequestStatus.PENDING_APPROVAL
                     and any(s.is_overdue() for s in r.approval_steps))

        return {
            "total_requests": total,
            "by_status": by_status,
            "pending_approval": pending,
            "overdue": overdue,
            "average_risk_score": sum(r.overall_risk_score for r in self.requests.values()) / total if total > 0 else 0
        }

    # =========================================================================
    # Expiry Management
    # =========================================================================

    async def check_expiring_access(self, days_ahead: int = 7) -> List[AccessRequest]:
        """Find requests with access expiring soon"""
        threshold = datetime.now() + timedelta(days=days_ahead)
        expiring = []

        for request in self.requests.values():
            if request.access_expires_at and request.access_expires_at <= threshold:
                if not request.expiry_notification_sent:
                    expiring.append(request)
                    await self._send_expiry_notification(request, days_ahead)

        return expiring

    async def _send_expiry_notification(self, request: AccessRequest, days: int):
        """Send expiry notification"""
        if self.notification_handler:
            await self.notification_handler(
                recipient=request.target_user_email or request.requester_email,
                subject=f"Access Expiring Soon: {request.request_id}",
                message=f"Your access granted in request {request.request_id} "
                       f"will expire in {days} days. "
                       f"Please submit an extension request if needed."
            )
            request.expiry_notification_sent = True

    async def revoke_expired_access(self):
        """Revoke access for expired requests"""
        now = datetime.now()

        for request in self.requests.values():
            if request.access_expires_at and request.access_expires_at <= now:
                if request.status == AccessRequestStatus.PROVISIONED:
                    await self._revoke_access(request)

    async def _revoke_access(self, request: AccessRequest):
        """Revoke access for a request"""
        logger.info(f"Revoking expired access for {request.request_id}")

        # Would call SAP connector to revoke
        request.status = AccessRequestStatus.EXPIRED

        if self.notification_handler:
            await self.notification_handler(
                recipient=request.target_user_email or request.requester_email,
                subject=f"Access Expired: {request.request_id}",
                message=f"Your temporary access has expired and been revoked."
            )
