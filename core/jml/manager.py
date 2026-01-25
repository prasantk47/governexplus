"""
JML Manager Module

Manages the complete JML lifecycle including profile matching,
provisioning orchestration, and event processing.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import copy

from .models import (
    JMLEvent, JMLEventType, AccessProfile, ProvisioningAction,
    ProvisioningStatus, ProvisioningActionType, JMLProcessingRule
)


class JMLManager:
    """
    Manages Joiner/Mover/Leaver lifecycle automation.

    Key features:
    - Profile-based access provisioning
    - Automatic role assignment/revocation
    - Mover transition handling (remove old, add new)
    - Leaver access termination with configurable timing
    - Integration with approval workflows
    - Scheduled provisioning
    """

    def __init__(self, sap_connector=None, rule_engine=None):
        self.sap_connector = sap_connector
        self.rule_engine = rule_engine

        self.events: Dict[str, JMLEvent] = {}
        self.profiles: Dict[str, AccessProfile] = {}
        self.rules: Dict[str, JMLProcessingRule] = {}

        # Index for lookups
        self.events_by_employee: Dict[str, List[str]] = defaultdict(list)
        self.events_by_status: Dict[ProvisioningStatus, List[str]] = defaultdict(list)

        # Create sample profiles and rules
        self._create_sample_profiles()
        self._create_sample_rules()

    def _create_sample_profiles(self):
        """Create sample access profiles"""

        # Finance Analyst Profile
        finance_analyst = AccessProfile(
            profile_id="PROF-FIN-ANALYST",
            name="Finance Analyst",
            description="Standard access for Finance Analysts",
            job_titles=["Finance Analyst", "Financial Analyst", "Jr. Finance Analyst"],
            departments=["Finance", "Accounting", "FP&A"],
            employee_types=["FTE"],
            roles=[
                {"system": "SAP", "role_name": "Z_FIN_ANALYST", "description": "Financial reporting"},
                {"system": "SAP", "role_name": "Z_FIN_DISPLAY", "description": "Financial display"},
            ],
            groups=[
                {"system": "AD", "group_name": "Finance_Users"},
                {"system": "AD", "group_name": "Report_Viewers"}
            ],
            priority=100
        )
        self.profiles[finance_analyst.profile_id] = finance_analyst

        # Procurement Specialist Profile
        procurement = AccessProfile(
            profile_id="PROF-PROC-SPEC",
            name="Procurement Specialist",
            description="Standard access for Procurement team",
            job_titles=["Procurement Specialist", "Buyer", "Purchasing Agent"],
            departments=["Procurement", "Purchasing", "Supply Chain"],
            employee_types=["FTE"],
            roles=[
                {"system": "SAP", "role_name": "Z_PROC_BUYER", "description": "Purchase order creation"},
                {"system": "SAP", "role_name": "Z_VENDOR_DISPLAY", "description": "Vendor display"},
            ],
            groups=[
                {"system": "AD", "group_name": "Procurement_Team"}
            ],
            priority=100
        )
        self.profiles[procurement.profile_id] = procurement

        # IT Support Profile
        it_support = AccessProfile(
            profile_id="PROF-IT-SUPPORT",
            name="IT Support",
            description="Standard access for IT Support staff",
            job_titles=["IT Support Analyst", "Help Desk Analyst", "Technical Support"],
            departments=["IT", "Information Technology", "Tech Support"],
            employee_types=["FTE", "contractor"],
            roles=[
                {"system": "SAP", "role_name": "Z_IT_DISPLAY", "description": "IT system display"},
            ],
            groups=[
                {"system": "AD", "group_name": "IT_Support"},
                {"system": "AD", "group_name": "ServiceDesk_Users"}
            ],
            auto_expire_days=365,  # Annual review
            priority=100
        )
        self.profiles[it_support.profile_id] = it_support

        # Manager Profile (add-on)
        manager = AccessProfile(
            profile_id="PROF-MGR-ADDON",
            name="Manager Add-on",
            description="Additional access for managers",
            job_titles=["Manager", "Sr. Manager", "Director", "VP"],
            departments=[],  # Applies to all departments
            employee_types=["FTE"],
            roles=[
                {"system": "SAP", "role_name": "Z_MGR_APPROVAL", "description": "Approval workflows"},
                {"system": "SAP", "role_name": "Z_TEAM_REPORTS", "description": "Team reporting"},
            ],
            groups=[
                {"system": "AD", "group_name": "Managers"}
            ],
            priority=50  # Lower priority, applied after department-specific
        )
        self.profiles[manager.profile_id] = manager

        # Contractor Base Profile
        contractor = AccessProfile(
            profile_id="PROF-CONTRACTOR",
            name="Contractor Base",
            description="Base access for all contractors",
            job_titles=[],
            departments=[],
            employee_types=["contractor", "temp", "consultant"],
            roles=[
                {"system": "SAP", "role_name": "Z_BASIC_ACCESS", "description": "Basic system access"},
            ],
            groups=[
                {"system": "AD", "group_name": "External_Users"}
            ],
            auto_expire_days=90,
            requires_approval=True,
            priority=200  # High priority for contractors
        )
        self.profiles[contractor.profile_id] = contractor

    def _create_sample_rules(self):
        """Create sample processing rules"""

        # Immediate leaver lockout rule
        leaver_lockout = JMLProcessingRule(
            rule_id="RULE-LEAVER-LOCK",
            name="Immediate Leaver Lockout",
            description="Lock accounts immediately on termination",
            event_types=[JMLEventType.LEAVER],
            conditions={},
            actions=[
                {"type": "disable_account", "systems": ["SAP", "AD"]},
                {"type": "revoke_all_roles"}
            ],
            delay_days=0,
            requires_approval=False,
            is_active=True,
            priority=1000  # Highest priority
        )
        self.rules[leaver_lockout.rule_id] = leaver_lockout

        # Delayed account deletion
        leaver_delete = JMLProcessingRule(
            rule_id="RULE-LEAVER-DELETE",
            name="Delayed Account Deletion",
            description="Delete accounts 90 days after termination",
            event_types=[JMLEventType.LEAVER],
            conditions={},
            actions=[
                {"type": "delete_account", "systems": ["SAP"]}
            ],
            delay_days=90,
            requires_approval=True,
            approver_type="security",
            is_active=True,
            priority=100
        )
        self.rules[leaver_delete.rule_id] = leaver_delete

        # Mover role transfer
        mover_transfer = JMLProcessingRule(
            rule_id="RULE-MOVER-TRANSFER",
            name="Mover Access Transfer",
            description="Revoke old access and provision new on department change",
            event_types=[JMLEventType.MOVER],
            conditions={"attribute_changed": "department"},
            actions=[
                {"type": "revoke_profile_roles", "profile_source": "previous"},
                {"type": "provision_profile_roles", "profile_source": "current"}
            ],
            delay_days=0,
            requires_approval=False,
            is_active=True,
            priority=500
        )
        self.rules[mover_transfer.rule_id] = mover_transfer

        # Extended leave suspension
        leave_suspend = JMLProcessingRule(
            rule_id="RULE-LEAVE-SUSPEND",
            name="Leave Access Suspension",
            description="Suspend access during extended leave",
            event_types=[JMLEventType.LEAVE_START],
            conditions={},
            actions=[
                {"type": "disable_account", "systems": ["SAP", "AD"]}
            ],
            delay_days=0,
            requires_approval=False,
            is_active=True,
            priority=500
        )
        self.rules[leave_suspend.rule_id] = leave_suspend

    async def process_hr_event(self, event_data: Dict) -> JMLEvent:
        """
        Process an incoming HR event.

        Creates a JML event and generates provisioning actions.
        """
        # Map event type
        event_type_map = {
            "new_hire": JMLEventType.JOINER,
            "joiner": JMLEventType.JOINER,
            "transfer": JMLEventType.MOVER,
            "mover": JMLEventType.MOVER,
            "promotion": JMLEventType.MOVER,
            "termination": JMLEventType.LEAVER,
            "leaver": JMLEventType.LEAVER,
            "resignation": JMLEventType.LEAVER,
            "contractor_start": JMLEventType.CONTRACTOR_START,
            "contractor_end": JMLEventType.CONTRACTOR_END,
            "leave_start": JMLEventType.LEAVE_START,
            "leave_end": JMLEventType.LEAVE_END
        }

        event_type_str = event_data.get("event_type", "joiner").lower()
        event_type = event_type_map.get(event_type_str, JMLEventType.JOINER)

        # Create JML event
        event = JMLEvent(
            event_type=event_type,
            employee_id=event_data.get("employee_id", ""),
            employee_name=event_data.get("employee_name", ""),
            employee_email=event_data.get("employee_email", ""),
            job_title=event_data.get("job_title", ""),
            department=event_data.get("department", ""),
            manager_id=event_data.get("manager_id", ""),
            manager_name=event_data.get("manager_name", ""),
            location=event_data.get("location", ""),
            cost_center=event_data.get("cost_center", ""),
            employee_type=event_data.get("employee_type", "FTE"),
            company_code=event_data.get("company_code", ""),
            effective_date=event_data.get("effective_date", datetime.now()),
            termination_date=event_data.get("termination_date"),
            contract_end_date=event_data.get("contract_end_date"),
            source_system=event_data.get("source_system", "HR"),
            source_event_id=event_data.get("source_event_id"),
            notes=event_data.get("notes", "")
        )

        # For movers, capture previous attributes
        if event_type == JMLEventType.MOVER:
            event.previous_job_title = event_data.get("previous_job_title")
            event.previous_department = event_data.get("previous_department")
            event.previous_manager_id = event_data.get("previous_manager_id")
            event.previous_location = event_data.get("previous_location")
            event.previous_cost_center = event_data.get("previous_cost_center")

        # Generate provisioning actions
        await self._generate_actions(event)

        # Store event
        self.events[event.event_id] = event
        self.events_by_employee[event.employee_id].append(event.event_id)
        self.events_by_status[event.status].append(event.event_id)

        return event

    async def _generate_actions(self, event: JMLEvent):
        """Generate provisioning actions for an event"""

        if event.event_type == JMLEventType.JOINER:
            await self._generate_joiner_actions(event)
        elif event.event_type == JMLEventType.MOVER:
            await self._generate_mover_actions(event)
        elif event.event_type == JMLEventType.LEAVER:
            await self._generate_leaver_actions(event)
        elif event.event_type == JMLEventType.CONTRACTOR_START:
            await self._generate_joiner_actions(event)
        elif event.event_type == JMLEventType.CONTRACTOR_END:
            await self._generate_leaver_actions(event)
        elif event.event_type == JMLEventType.LEAVE_START:
            await self._generate_leave_start_actions(event)
        elif event.event_type == JMLEventType.LEAVE_END:
            await self._generate_leave_end_actions(event)

        # Check if any actions require approval
        for rule in self._get_matching_rules(event):
            if rule.requires_approval:
                event.requires_approval = True
                event.approval_status = "pending"
                break

    async def _generate_joiner_actions(self, event: JMLEvent):
        """Generate actions for new joiners"""

        # Create account action
        create_account = ProvisioningAction(
            event_id=event.event_id,
            action_type=ProvisioningActionType.CREATE_ACCOUNT,
            target_system="SAP",
            target_user_id=event.employee_id,
            status=ProvisioningStatus.PENDING
        )
        event.actions.append(create_account)

        # Match profiles and add role grants
        matched_profiles = self._match_profiles(event.get_employee_attributes())
        event.matched_profiles = [p.profile_id for p in matched_profiles]

        for profile in matched_profiles:
            for role in profile.roles:
                action = ProvisioningAction(
                    event_id=event.event_id,
                    action_type=ProvisioningActionType.GRANT_ROLE,
                    target_system=role.get("system", "SAP"),
                    target_user_id=event.employee_id,
                    role_name=role.get("role_name"),
                    status=ProvisioningStatus.PENDING
                )
                event.actions.append(action)

            for group in profile.groups:
                action = ProvisioningAction(
                    event_id=event.event_id,
                    action_type=ProvisioningActionType.GRANT_ROLE,
                    target_system=group.get("system", "AD"),
                    target_user_id=event.employee_id,
                    group_name=group.get("group_name"),
                    status=ProvisioningStatus.PENDING
                )
                event.actions.append(action)

            # Set expiry if profile has auto-expire
            if profile.auto_expire_days:
                expire_action = ProvisioningAction(
                    event_id=event.event_id,
                    action_type=ProvisioningActionType.SET_EXPIRY,
                    target_system="SAP",
                    target_user_id=event.employee_id,
                    result_details={"expiry_days": profile.auto_expire_days},
                    status=ProvisioningStatus.PENDING
                )
                event.actions.append(expire_action)

    async def _generate_mover_actions(self, event: JMLEvent):
        """Generate actions for movers (department/role changes)"""

        # Find profiles to remove (based on previous attributes)
        previous_attrs = event.get_previous_attributes()
        previous_attrs = {k: v for k, v in previous_attrs.items() if v}  # Remove None values

        if previous_attrs:
            # Create synthetic attributes for matching old profiles
            old_attrs = {**event.get_employee_attributes(), **previous_attrs}
            old_profiles = self._match_profiles(old_attrs)

            # Revoke old profile roles
            for profile in old_profiles:
                for role in profile.roles:
                    action = ProvisioningAction(
                        event_id=event.event_id,
                        action_type=ProvisioningActionType.REVOKE_ROLE,
                        target_system=role.get("system", "SAP"),
                        target_user_id=event.employee_id,
                        role_name=role.get("role_name"),
                        status=ProvisioningStatus.PENDING
                    )
                    event.actions.append(action)

        # Match new profiles and add grants
        new_profiles = self._match_profiles(event.get_employee_attributes())
        event.matched_profiles = [p.profile_id for p in new_profiles]

        for profile in new_profiles:
            for role in profile.roles:
                action = ProvisioningAction(
                    event_id=event.event_id,
                    action_type=ProvisioningActionType.GRANT_ROLE,
                    target_system=role.get("system", "SAP"),
                    target_user_id=event.employee_id,
                    role_name=role.get("role_name"),
                    status=ProvisioningStatus.PENDING
                )
                event.actions.append(action)

    async def _generate_leaver_actions(self, event: JMLEvent):
        """Generate actions for leavers"""

        # Disable account immediately
        disable_action = ProvisioningAction(
            event_id=event.event_id,
            action_type=ProvisioningActionType.DISABLE_ACCOUNT,
            target_system="SAP",
            target_user_id=event.employee_id,
            status=ProvisioningStatus.PENDING
        )
        event.actions.append(disable_action)

        # Reset password
        reset_pwd = ProvisioningAction(
            event_id=event.event_id,
            action_type=ProvisioningActionType.RESET_PASSWORD,
            target_system="SAP",
            target_user_id=event.employee_id,
            status=ProvisioningStatus.PENDING
        )
        event.actions.append(reset_pwd)

        # Get all roles to revoke (would query actual system)
        matched_profiles = self._match_profiles(event.get_employee_attributes())
        for profile in matched_profiles:
            for role in profile.roles:
                action = ProvisioningAction(
                    event_id=event.event_id,
                    action_type=ProvisioningActionType.REVOKE_ROLE,
                    target_system=role.get("system", "SAP"),
                    target_user_id=event.employee_id,
                    role_name=role.get("role_name"),
                    status=ProvisioningStatus.PENDING
                )
                event.actions.append(action)

        # Schedule account deletion (90 days)
        delete_action = ProvisioningAction(
            event_id=event.event_id,
            action_type=ProvisioningActionType.DELETE_ACCOUNT,
            target_system="SAP",
            target_user_id=event.employee_id,
            scheduled_time=datetime.now() + timedelta(days=90),
            status=ProvisioningStatus.SCHEDULED
        )
        event.actions.append(delete_action)

        # Transfer ownership action
        if event.manager_id:
            transfer = ProvisioningAction(
                event_id=event.event_id,
                action_type=ProvisioningActionType.TRANSFER_OWNERSHIP,
                target_system="SAP",
                target_user_id=event.employee_id,
                result_details={"new_owner": event.manager_id},
                status=ProvisioningStatus.PENDING
            )
            event.actions.append(transfer)

    async def _generate_leave_start_actions(self, event: JMLEvent):
        """Generate actions for extended leave start"""

        disable_action = ProvisioningAction(
            event_id=event.event_id,
            action_type=ProvisioningActionType.DISABLE_ACCOUNT,
            target_system="SAP",
            target_user_id=event.employee_id,
            status=ProvisioningStatus.PENDING
        )
        event.actions.append(disable_action)

    async def _generate_leave_end_actions(self, event: JMLEvent):
        """Generate actions for return from leave"""

        enable_action = ProvisioningAction(
            event_id=event.event_id,
            action_type=ProvisioningActionType.ENABLE_ACCOUNT,
            target_system="SAP",
            target_user_id=event.employee_id,
            status=ProvisioningStatus.PENDING
        )
        event.actions.append(enable_action)

        # May need password reset
        reset_pwd = ProvisioningAction(
            event_id=event.event_id,
            action_type=ProvisioningActionType.RESET_PASSWORD,
            target_system="SAP",
            target_user_id=event.employee_id,
            status=ProvisioningStatus.PENDING
        )
        event.actions.append(reset_pwd)

    def _match_profiles(self, employee_attrs: Dict) -> List[AccessProfile]:
        """Find all profiles matching employee attributes"""
        matched = []

        for profile in self.profiles.values():
            if profile.matches(employee_attrs):
                matched.append(profile)

        # Sort by priority (higher first)
        return sorted(matched, key=lambda p: p.priority, reverse=True)

    def _get_matching_rules(self, event: JMLEvent) -> List[JMLProcessingRule]:
        """Get processing rules matching the event"""
        matched = []

        for rule in self.rules.values():
            if not rule.is_active:
                continue
            if event.event_type not in rule.event_types:
                continue
            # Additional condition matching would go here
            matched.append(rule)

        return sorted(matched, key=lambda r: r.priority, reverse=True)

    async def execute_event(self, event_id: str) -> JMLEvent:
        """
        Execute all pending actions for an event.
        """
        event = self.events.get(event_id)
        if not event:
            raise ValueError(f"Event {event_id} not found")

        if event.requires_approval and event.approval_status != "approved":
            raise ValueError("Event requires approval before execution")

        event.status = ProvisioningStatus.IN_PROGRESS

        for action in event.actions:
            if action.status != ProvisioningStatus.PENDING:
                continue

            try:
                await self._execute_action(action)
            except Exception as e:
                action.status = ProvisioningStatus.FAILED
                action.error_message = str(e)
                action.retry_count += 1

        # Check if all completed
        all_done = all(
            a.status in [ProvisioningStatus.COMPLETED, ProvisioningStatus.SCHEDULED]
            for a in event.actions
        )
        any_failed = any(a.status == ProvisioningStatus.FAILED for a in event.actions)

        if all_done:
            event.status = ProvisioningStatus.COMPLETED
            event.processed_at = datetime.now()
        elif any_failed:
            event.status = ProvisioningStatus.FAILED

        return event

    async def _execute_action(self, action: ProvisioningAction):
        """Execute a single provisioning action"""
        action.status = ProvisioningStatus.IN_PROGRESS
        action.started_at = datetime.now()

        # In production, this would call the actual connectors
        # For now, simulate execution

        if action.action_type == ProvisioningActionType.CREATE_ACCOUNT:
            # Would call: self.sap_connector.create_user(...)
            action.result_details = {"user_created": True}

        elif action.action_type == ProvisioningActionType.GRANT_ROLE:
            # Would call: self.sap_connector.assign_role(...)
            action.result_details = {"role_assigned": True}

        elif action.action_type == ProvisioningActionType.REVOKE_ROLE:
            # Would call: self.sap_connector.remove_role(...)
            action.result_details = {"role_revoked": True}

        elif action.action_type == ProvisioningActionType.DISABLE_ACCOUNT:
            # Would call: self.sap_connector.lock_user(...)
            action.result_details = {"account_disabled": True}

        elif action.action_type == ProvisioningActionType.ENABLE_ACCOUNT:
            # Would call: self.sap_connector.unlock_user(...)
            action.result_details = {"account_enabled": True}

        elif action.action_type == ProvisioningActionType.DELETE_ACCOUNT:
            # Would call: self.sap_connector.delete_user(...)
            action.result_details = {"account_deleted": True}

        action.status = ProvisioningStatus.COMPLETED
        action.completed_at = datetime.now()
        action.success = True

    async def approve_event(self, event_id: str, approver_id: str, comments: str = "") -> JMLEvent:
        """Approve a JML event for execution"""
        event = self.events.get(event_id)
        if not event:
            raise ValueError(f"Event {event_id} not found")

        if not event.requires_approval:
            raise ValueError("Event does not require approval")

        event.approval_status = "approved"
        event.approved_by = approver_id
        event.notes = comments

        return event

    async def reject_event(self, event_id: str, rejector_id: str, reason: str) -> JMLEvent:
        """Reject a JML event"""
        event = self.events.get(event_id)
        if not event:
            raise ValueError(f"Event {event_id} not found")

        event.approval_status = "rejected"
        event.status = ProvisioningStatus.CANCELLED
        event.notes = f"Rejected by {rejector_id}: {reason}"

        return event

    def get_event(self, event_id: str) -> Optional[JMLEvent]:
        """Get an event by ID"""
        return self.events.get(event_id)

    def get_events(
        self,
        event_type: JMLEventType = None,
        status: ProvisioningStatus = None,
        employee_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[JMLEvent]:
        """Get events with filters"""
        results = []

        for event in self.events.values():
            if event_type and event.event_type != event_type:
                continue
            if status and event.status != status:
                continue
            if employee_id and event.employee_id != employee_id:
                continue
            if start_date and event.effective_date < start_date:
                continue
            if end_date and event.effective_date > end_date:
                continue

            results.append(event)

        return sorted(results, key=lambda e: e.created_at, reverse=True)

    def get_pending_approvals(self) -> List[JMLEvent]:
        """Get events pending approval"""
        return [
            e for e in self.events.values()
            if e.requires_approval and e.approval_status == "pending"
        ]

    def get_employee_history(self, employee_id: str) -> List[JMLEvent]:
        """Get all JML events for an employee"""
        event_ids = self.events_by_employee.get(employee_id, [])
        return [self.events[eid] for eid in event_ids if eid in self.events]

    # Profile Management

    def create_profile(
        self,
        name: str,
        description: str,
        job_titles: List[str] = None,
        departments: List[str] = None,
        employee_types: List[str] = None,
        roles: List[Dict] = None,
        groups: List[Dict] = None,
        **kwargs
    ) -> AccessProfile:
        """Create a new access profile"""
        profile = AccessProfile(
            name=name,
            description=description,
            job_titles=job_titles or [],
            departments=departments or [],
            employee_types=employee_types or [],
            roles=roles or [],
            groups=groups or [],
            **kwargs
        )

        self.profiles[profile.profile_id] = profile
        return profile

    def get_profile(self, profile_id: str) -> Optional[AccessProfile]:
        """Get a profile by ID"""
        return self.profiles.get(profile_id)

    def get_profiles(self, active_only: bool = True) -> List[AccessProfile]:
        """Get all profiles"""
        profiles = list(self.profiles.values())
        if active_only:
            profiles = [p for p in profiles if p.is_active]
        return profiles

    def preview_profile_matches(self, employee_attrs: Dict) -> List[Dict]:
        """Preview which profiles would match given attributes"""
        matched = self._match_profiles(employee_attrs)

        result = []
        for profile in matched:
            result.append({
                "profile_id": profile.profile_id,
                "name": profile.name,
                "priority": profile.priority,
                "roles": profile.roles,
                "groups": profile.groups,
                "requires_approval": profile.requires_approval
            })

        return result

    def get_statistics(self) -> Dict:
        """Get JML processing statistics"""
        by_type = defaultdict(int)
        by_status = defaultdict(int)

        for event in self.events.values():
            by_type[event.event_type.value] += 1
            by_status[event.status.value] += 1

        pending_actions = sum(
            len([a for a in e.actions if a.status == ProvisioningStatus.PENDING])
            for e in self.events.values()
        )

        return {
            "total_events": len(self.events),
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "pending_approvals": len(self.get_pending_approvals()),
            "pending_actions": pending_actions,
            "total_profiles": len(self.profiles),
            "active_profiles": len([p for p in self.profiles.values() if p.is_active]),
            "total_rules": len(self.rules)
        }
