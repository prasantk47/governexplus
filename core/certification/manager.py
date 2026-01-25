"""
Certification Campaign Manager

Manages access certification/review campaigns including:
- Campaign creation and scheduling
- Item generation from connected systems
- Review processing and tracking
- Automatic reminders and escalation
- Revocation processing
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import uuid

from .models import (
    CertificationCampaign, CertificationItem, CertificationDecision,
    CampaignStatus, CampaignType, CertificationAction
)
from core.rules import RuleEngine
from core.rules.models import UserAccess

logger = logging.getLogger(__name__)


class CertificationManager:
    """
    Central manager for access certification campaigns.

    Handles the full lifecycle of certification from campaign creation
    through review completion and revocation processing.
    """

    def __init__(self,
                 rule_engine: Optional[RuleEngine] = None,
                 user_connector=None,
                 notification_handler: Optional[Callable] = None):
        """
        Initialize Certification Manager.

        Args:
            rule_engine: Risk analysis engine for risk-prioritized reviews
            user_connector: Connector for user/role data
            notification_handler: Function to send notifications
        """
        self.rule_engine = rule_engine or RuleEngine()
        self.user_connector = user_connector
        self.notification_handler = notification_handler

        # In-memory storage (replace with database)
        self.campaigns: Dict[str, CertificationCampaign] = {}
        self.decisions: Dict[str, CertificationDecision] = {}

        # Configuration
        self.config = {
            "default_campaign_days": 14,
            "reminder_days": [7, 3, 1],
            "auto_revoke_on_timeout": False,
            "require_comments_for_revoke": True,
            "max_items_per_reviewer": 500,
            "enable_continuous_certification": True
        }

    # =========================================================================
    # Campaign Creation
    # =========================================================================

    async def create_campaign(self,
                             name: str,
                             description: str,
                             campaign_type: CampaignType,
                             owner_id: str,
                             owner_name: str,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             included_systems: Optional[List[str]] = None,
                             included_departments: Optional[List[str]] = None,
                             risk_threshold: Optional[float] = None,
                             include_sod_only: bool = False) -> CertificationCampaign:
        """
        Create a new certification campaign.

        Args:
            name: Campaign name
            description: Campaign description
            campaign_type: Type of certification
            owner_id: Campaign owner user ID
            owner_name: Campaign owner name
            start_date: When campaign starts
            end_date: When campaign ends
            included_systems: Systems to include (None = all)
            included_departments: Departments to include (None = all)
            risk_threshold: Only include items above this risk score
            include_sod_only: Only include items with SoD violations

        Returns:
            Created CertificationCampaign
        """

        start = start_date or datetime.now()
        end = end_date or (start + timedelta(days=self.config["default_campaign_days"]))

        campaign = CertificationCampaign(
            name=name,
            description=description,
            campaign_type=campaign_type,
            start_date=start,
            end_date=end,
            status=CampaignStatus.DRAFT,
            owner_id=owner_id,
            owner_name=owner_name,
            included_systems=included_systems or ["SAP"],
            included_departments=included_departments or [],
            risk_threshold=risk_threshold,
            include_sod_only=include_sod_only
        )

        # Store campaign
        self.campaigns[campaign.campaign_id] = campaign

        logger.info(f"Created certification campaign {campaign.campaign_id}: {name}")

        return campaign

    async def generate_campaign_items(self, campaign_id: str) -> CertificationCampaign:
        """
        Generate certification items for a campaign based on its scope.

        This pulls data from connected systems and creates items for review.
        """
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        if campaign.status != CampaignStatus.DRAFT:
            raise ValueError("Can only generate items for draft campaigns")

        items = []

        if campaign.campaign_type == CampaignType.USER_ACCESS:
            items = await self._generate_user_access_items(campaign)
        elif campaign.campaign_type == CampaignType.ROLE_MEMBERSHIP:
            items = await self._generate_role_membership_items(campaign)
        elif campaign.campaign_type == CampaignType.SENSITIVE_ACCESS:
            items = await self._generate_sensitive_access_items(campaign)
        elif campaign.campaign_type == CampaignType.SOD_VIOLATIONS:
            items = await self._generate_sod_items(campaign)
        elif campaign.campaign_type == CampaignType.MANAGER_CERTIFICATION:
            items = await self._generate_manager_items(campaign)

        # Apply filters
        if campaign.risk_threshold:
            items = [i for i in items if i.risk_score >= campaign.risk_threshold]

        if campaign.include_sod_only:
            items = [i for i in items if i.has_sod_violation]

        campaign.items = items
        campaign.total_items = len(items)

        logger.info(f"Generated {len(items)} items for campaign {campaign_id}")

        return campaign

    async def _generate_user_access_items(self, campaign: CertificationCampaign) -> List[CertificationItem]:
        """Generate items for user access review"""
        items = []

        # Mock data for demonstration
        mock_users = [
            {
                "user_id": "JSMITH",
                "user_name": "John Smith",
                "department": "Finance",
                "manager_id": "manager1@company.com",
                "roles": [
                    {"role_id": "Z_AP_MANAGER", "role_name": "AP Manager", "granted": "2023-01-15"},
                    {"role_id": "Z_VENDOR_MAINT", "role_name": "Vendor Maintenance", "granted": "2023-03-01"}
                ]
            },
            {
                "user_id": "MBROWN",
                "user_name": "Mary Brown",
                "department": "Procurement",
                "manager_id": "manager2@company.com",
                "roles": [
                    {"role_id": "Z_PURCHASER", "role_name": "Purchaser", "granted": "2022-06-10"},
                    {"role_id": "Z_GR_CLERK", "role_name": "Goods Receipt Clerk", "granted": "2022-06-10"}
                ]
            },
            {
                "user_id": "AWILSON",
                "user_name": "Alice Wilson",
                "department": "HR",
                "manager_id": "hr.director@company.com",
                "roles": [
                    {"role_id": "Z_HR_SPECIALIST", "role_name": "HR Specialist", "granted": "2021-09-01"},
                    {"role_id": "Z_PAYROLL_RUN", "role_name": "Payroll Processing", "granted": "2022-01-15"}
                ]
            }
        ]

        for user_data in mock_users:
            # Filter by department if specified
            if campaign.included_departments:
                if user_data["department"] not in campaign.included_departments:
                    continue

            for role in user_data["roles"]:
                # Create certification item
                item = CertificationItem(
                    user_id=user_data["user_id"],
                    user_name=user_data["user_name"],
                    user_department=user_data["department"],
                    access_type="role",
                    access_id=role["role_id"],
                    access_name=role["role_name"],
                    granted_date=datetime.strptime(role["granted"], "%Y-%m-%d"),
                    reviewer_id=user_data["manager_id"],
                    reviewer_name=user_data["manager_id"].split("@")[0].replace(".", " ").title()
                )

                # Calculate risk
                item.risk_score = await self._calculate_item_risk(item, user_data)

                items.append(item)

        return items

    async def _generate_role_membership_items(self, campaign: CertificationCampaign) -> List[CertificationItem]:
        """Generate items for role membership review"""
        # Would iterate roles and find all users with each role
        return []

    async def _generate_sensitive_access_items(self, campaign: CertificationCampaign) -> List[CertificationItem]:
        """Generate items for sensitive/high-risk access only"""
        all_items = await self._generate_user_access_items(campaign)

        # Filter to high-risk items
        sensitive_items = [i for i in all_items if i.risk_score >= 60]

        return sensitive_items

    async def _generate_sod_items(self, campaign: CertificationCampaign) -> List[CertificationItem]:
        """Generate items for users with SoD violations"""
        all_items = await self._generate_user_access_items(campaign)

        # Mark items with SoD violations
        # In production, this would query actual violations
        for item in all_items:
            if item.access_id in ["Z_VENDOR_MAINT", "Z_PAYMENT_RUN"]:
                item.has_sod_violation = True
                item.sod_details = {
                    "rule_id": "FI_P2P_001",
                    "rule_name": "Purchase to Pay Conflict"
                }
                item.risk_flags.append("SoD: Vendor + Payment")

        sod_items = [i for i in all_items if i.has_sod_violation]

        return sod_items

    async def _generate_manager_items(self, campaign: CertificationCampaign) -> List[CertificationItem]:
        """Generate items grouped by manager for team reviews"""
        return await self._generate_user_access_items(campaign)

    async def _calculate_item_risk(self, item: CertificationItem, user_data: Dict) -> float:
        """Calculate risk score for a certification item"""
        score = 0.0

        # Role-based risk
        high_risk_roles = ["Z_PAYROLL_RUN", "Z_PAYMENT_RUN", "Z_BASIS_ADMIN", "Z_USER_ADMIN"]
        if item.access_id in high_risk_roles:
            score += 40

        # Check for potential SoD
        user_roles = [r["role_id"] for r in user_data.get("roles", [])]
        sod_pairs = [
            (["Z_VENDOR_MAINT"], ["Z_PAYMENT_RUN"]),
            (["Z_PURCHASER"], ["Z_GR_CLERK"]),
            (["Z_HR_SPECIALIST"], ["Z_PAYROLL_RUN"])
        ]

        for role_a_list, role_b_list in sod_pairs:
            has_a = any(r in user_roles for r in role_a_list)
            has_b = any(r in user_roles for r in role_b_list)
            if has_a and has_b:
                score += 30
                item.has_sod_violation = True
                item.risk_flags.append("Potential SoD conflict")

        # Tenure-based risk (longer access = higher review priority)
        if item.granted_date:
            days_since_grant = (datetime.now() - item.granted_date).days
            if days_since_grant > 365:
                score += 10
            if days_since_grant > 730:
                score += 10

        return min(score, 100)

    # =========================================================================
    # Campaign Lifecycle
    # =========================================================================

    async def start_campaign(self, campaign_id: str) -> CertificationCampaign:
        """Start a campaign and notify reviewers"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        if not campaign.items:
            raise ValueError("Campaign has no items. Generate items first.")

        campaign.status = CampaignStatus.ACTIVE

        # Notify all reviewers
        await self._notify_campaign_start(campaign)

        logger.info(f"Started campaign {campaign_id}")

        return campaign

    async def _notify_campaign_start(self, campaign: CertificationCampaign):
        """Notify reviewers that campaign has started"""
        if not self.notification_handler:
            return

        # Group items by reviewer
        reviewers = {}
        for item in campaign.items:
            if item.reviewer_id not in reviewers:
                reviewers[item.reviewer_id] = []
            reviewers[item.reviewer_id].append(item)

        for reviewer_id, items in reviewers.items():
            await self.notification_handler(
                recipient=reviewer_id,
                subject=f"Access Certification Required: {campaign.name}",
                message=f"You have {len(items)} access items to review.\n"
                       f"Please complete your review by {campaign.end_date.strftime('%Y-%m-%d')}."
            )

    async def process_decision(self,
                              campaign_id: str,
                              item_id: str,
                              action: CertificationAction,
                              reviewer_id: str,
                              comments: str = "",
                              delegate_to: Optional[str] = None) -> CertificationItem:
        """
        Process a certification decision.

        Args:
            campaign_id: Campaign ID
            item_id: Item being reviewed
            action: Decision action
            reviewer_id: Reviewer making decision
            comments: Review comments
            delegate_to: For delegation, the new reviewer

        Returns:
            Updated CertificationItem
        """
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Find item
        item = next((i for i in campaign.items if i.item_id == item_id), None)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        # Verify reviewer
        if item.reviewer_id != reviewer_id and item.delegated_to != reviewer_id:
            raise PermissionError(f"User {reviewer_id} is not authorized to review this item")

        # Validate comments for revoke
        if action == CertificationAction.REVOKE:
            if campaign.require_comments_for_revoke and not comments:
                raise ValueError("Comments required for revocation")

        # Process action
        if action == CertificationAction.DELEGATE:
            if not delegate_to:
                raise ValueError("Delegation requires delegate_to parameter")
            item.delegated_to = delegate_to
            item.decision_comments = f"Delegated by {reviewer_id}: {comments}"
            # Item remains not completed
        else:
            item.decision = action
            item.decision_date = datetime.now()
            item.decision_comments = comments
            item.is_completed = True

            # Record decision
            decision = CertificationDecision(
                item_id=item_id,
                campaign_id=campaign_id,
                action=action,
                reviewer_id=reviewer_id,
                comments=comments
            )
            self.decisions[decision.decision_id] = decision

        # Update campaign stats
        campaign.completed_items = sum(1 for i in campaign.items if i.is_completed)
        if action == CertificationAction.CERTIFY:
            campaign.certified_count = sum(1 for i in campaign.items
                                          if i.decision == CertificationAction.CERTIFY)
        elif action == CertificationAction.REVOKE:
            campaign.revoked_count = sum(1 for i in campaign.items
                                        if i.decision == CertificationAction.REVOKE)

        # Check if campaign is complete
        if all(i.is_completed for i in campaign.items):
            campaign.status = CampaignStatus.COMPLETED

        logger.info(f"Decision recorded for item {item_id}: {action.value}")

        return item

    async def bulk_certify(self,
                          campaign_id: str,
                          item_ids: List[str],
                          reviewer_id: str,
                          comments: str = "Bulk certified") -> Dict:
        """Bulk certify multiple items"""
        processed = 0
        errors = []

        for item_id in item_ids:
            try:
                await self.process_decision(
                    campaign_id=campaign_id,
                    item_id=item_id,
                    action=CertificationAction.CERTIFY,
                    reviewer_id=reviewer_id,
                    comments=comments
                )
                processed += 1
            except Exception as e:
                errors.append({"item_id": item_id, "error": str(e)})

        return {
            "processed": processed,
            "errors": errors
        }

    # =========================================================================
    # Reminder and Escalation
    # =========================================================================

    async def send_reminders(self):
        """Send reminders for pending certifications"""
        for campaign in self.campaigns.values():
            if campaign.status != CampaignStatus.ACTIVE:
                continue

            days_remaining = campaign.days_remaining()

            if days_remaining in campaign.reminder_days:
                await self._send_campaign_reminders(campaign, days_remaining)

    async def _send_campaign_reminders(self, campaign: CertificationCampaign, days_remaining: int):
        """Send reminders for a specific campaign"""
        if not self.notification_handler:
            return

        # Group pending items by reviewer
        pending_by_reviewer = {}
        for item in campaign.items:
            if item.is_completed:
                continue

            reviewer = item.delegated_to or item.reviewer_id
            if reviewer not in pending_by_reviewer:
                pending_by_reviewer[reviewer] = 0
            pending_by_reviewer[reviewer] += 1

        for reviewer_id, count in pending_by_reviewer.items():
            urgency = "URGENT: " if days_remaining <= 1 else ""
            await self.notification_handler(
                recipient=reviewer_id,
                subject=f"{urgency}Access Certification Reminder: {campaign.name}",
                message=f"You have {count} items pending review.\n"
                       f"Campaign ends in {days_remaining} day(s)."
            )

    async def process_expired_campaigns(self):
        """Handle campaigns that have passed their end date"""
        for campaign in self.campaigns.values():
            if campaign.status != CampaignStatus.ACTIVE:
                continue

            if campaign.is_overdue():
                if self.config["auto_revoke_on_timeout"]:
                    await self._auto_revoke_pending(campaign)
                else:
                    campaign.status = CampaignStatus.IN_REVIEW
                    # Mark items as overdue
                    for item in campaign.items:
                        if not item.is_completed:
                            item.is_overdue = True

    async def _auto_revoke_pending(self, campaign: CertificationCampaign):
        """Auto-revoke access for items not reviewed"""
        for item in campaign.items:
            if not item.is_completed:
                item.decision = CertificationAction.REVOKE
                item.decision_date = datetime.now()
                item.decision_comments = "Auto-revoked due to certification timeout"
                item.is_completed = True

                # Record decision
                decision = CertificationDecision(
                    item_id=item.item_id,
                    campaign_id=campaign.campaign_id,
                    action=CertificationAction.REVOKE,
                    reviewer_id="SYSTEM",
                    comments="Auto-revoked due to certification timeout"
                )
                self.decisions[decision.decision_id] = decision

        campaign.status = CampaignStatus.COMPLETED

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_campaign(self, campaign_id: str) -> Optional[CertificationCampaign]:
        """Get campaign by ID"""
        return self.campaigns.get(campaign_id)

    def get_campaigns(self,
                     status: Optional[CampaignStatus] = None,
                     owner_id: Optional[str] = None) -> List[CertificationCampaign]:
        """Get campaigns with filters"""
        campaigns = list(self.campaigns.values())

        if status:
            campaigns = [c for c in campaigns if c.status == status]
        if owner_id:
            campaigns = [c for c in campaigns if c.owner_id == owner_id]

        return campaigns

    def get_reviewer_items(self,
                          reviewer_id: str,
                          campaign_id: Optional[str] = None,
                          pending_only: bool = True) -> List[CertificationItem]:
        """Get certification items assigned to a reviewer"""
        items = []

        campaigns = [self.campaigns[campaign_id]] if campaign_id else self.campaigns.values()

        for campaign in campaigns:
            if campaign.status not in [CampaignStatus.ACTIVE, CampaignStatus.IN_REVIEW]:
                continue

            for item in campaign.items:
                # Check if reviewer is assigned or delegated
                if item.reviewer_id == reviewer_id or item.delegated_to == reviewer_id:
                    if pending_only and item.is_completed:
                        continue
                    items.append(item)

        return items

    def get_reviewer_workload(self) -> Dict[str, Dict]:
        """Get workload summary for all reviewers"""
        workload = {}

        for campaign in self.campaigns.values():
            if campaign.status != CampaignStatus.ACTIVE:
                continue

            for item in campaign.items:
                reviewer = item.delegated_to or item.reviewer_id
                if reviewer not in workload:
                    workload[reviewer] = {
                        "total": 0,
                        "pending": 0,
                        "completed": 0,
                        "campaigns": set()
                    }

                workload[reviewer]["total"] += 1
                workload[reviewer]["campaigns"].add(campaign.campaign_id)
                if item.is_completed:
                    workload[reviewer]["completed"] += 1
                else:
                    workload[reviewer]["pending"] += 1

        # Convert sets to lists
        for r in workload.values():
            r["campaigns"] = list(r["campaigns"])

        return workload

    def get_statistics(self) -> Dict:
        """Get overall certification statistics"""
        total_campaigns = len(self.campaigns)
        active = sum(1 for c in self.campaigns.values() if c.status == CampaignStatus.ACTIVE)
        completed = sum(1 for c in self.campaigns.values() if c.status == CampaignStatus.COMPLETED)

        total_items = sum(len(c.items) for c in self.campaigns.values())
        certified = sum(c.certified_count for c in self.campaigns.values())
        revoked = sum(c.revoked_count for c in self.campaigns.values())

        return {
            "total_campaigns": total_campaigns,
            "active_campaigns": active,
            "completed_campaigns": completed,
            "total_items_reviewed": total_items,
            "total_certified": certified,
            "total_revoked": revoked,
            "certification_rate": round((certified / total_items) * 100, 1) if total_items > 0 else 0,
            "revocation_rate": round((revoked / total_items) * 100, 1) if total_items > 0 else 0
        }
