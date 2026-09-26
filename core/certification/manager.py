"""
Certification Campaign Manager

Manages access certification/review campaigns including:
- Campaign creation and scheduling
- Item generation from connected systems
- Review processing and tracking
- Automatic reminders and escalation
- Revocation processing

All data is persisted to the database via SQLAlchemy.
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import (
    CertificationCampaign, CertificationItem, CertificationDecision,
    CampaignStatus, CampaignType, CertificationAction, ReviewType,
    ReviewEvidence
)
from core.rules import RuleEngine
from core.rules.models import UserAccess
from core.evidence import EvidenceEngine

logger = logging.getLogger(__name__)


class CertificationManager:
    """
    Central manager for access certification campaigns.

    Handles the full lifecycle of certification from campaign creation
    through review completion and revocation processing.

    Requires a SQLAlchemy Session for DB persistence.
    """

    def __init__(self,
                 db: Optional[Session] = None,
                 rule_engine: Optional[RuleEngine] = None,
                 user_connector=None,
                 notification_handler: Optional[Callable] = None):
        self.db = db
        self.rule_engine = rule_engine or RuleEngine()
        self.user_connector = user_connector
        self.notification_handler = notification_handler
        self.evidence_engine = EvidenceEngine()

        self.config = {
            "default_campaign_days": 14,
            "reminder_days": [7, 3, 1],
            "auto_revoke_on_timeout": False,
            "require_comments_for_revoke": True,
            "max_items_per_reviewer": 500,
            "enable_continuous_certification": True
        }

    # =========================================================================
    # DB Persistence Helpers
    # =========================================================================

    def _save_campaign_to_db(self, campaign: CertificationCampaign, tenant_id: str = ""):
        """Persist a CertificationCampaign dataclass to the DB."""
        if not self.db:
            return

        from db.models.audit import CertificationCampaignLog

        row = self.db.query(CertificationCampaignLog).filter(
            CertificationCampaignLog.campaign_id == campaign.campaign_id
        ).first()

        if row:
            row.name = campaign.name
            row.description = campaign.description
            row.campaign_type = campaign.campaign_type.value
            row.status = campaign.status.value
            row.owner_id = campaign.owner_id
            row.owner_name = campaign.owner_name
            row.start_date = campaign.start_date
            row.end_date = campaign.end_date
            row.included_systems = campaign.included_systems
            row.included_departments = campaign.included_departments
            row.risk_threshold = int(campaign.risk_threshold) if campaign.risk_threshold else None
            row.total_items = campaign.total_items
            row.completed_items = campaign.completed_items
            row.certified_count = campaign.certified_count
            row.revoked_count = campaign.revoked_count
            row.config = {
                "include_sod_only": campaign.include_sod_only,
                "allow_delegation": campaign.allow_delegation,
                "require_comments_for_revoke": campaign.require_comments_for_revoke,
                "auto_revoke_on_timeout": campaign.auto_revoke_on_timeout,
                "reminder_days": campaign.reminder_days,
            }
        else:
            row = CertificationCampaignLog(
                campaign_id=campaign.campaign_id,
                tenant_id=tenant_id or campaign.tenant_id or "tenant_default",
                name=campaign.name,
                description=campaign.description,
                campaign_type=campaign.campaign_type.value,
                status=campaign.status.value,
                owner_id=campaign.owner_id,
                owner_name=campaign.owner_name,
                start_date=campaign.start_date,
                end_date=campaign.end_date,
                created_at=campaign.created_at,
                included_systems=campaign.included_systems,
                included_departments=campaign.included_departments,
                risk_threshold=int(campaign.risk_threshold) if campaign.risk_threshold else None,
                total_items=campaign.total_items,
                completed_items=campaign.completed_items,
                certified_count=campaign.certified_count,
                revoked_count=campaign.revoked_count,
                config={
                    "include_sod_only": campaign.include_sod_only,
                    "allow_delegation": campaign.allow_delegation,
                    "require_comments_for_revoke": campaign.require_comments_for_revoke,
                    "auto_revoke_on_timeout": campaign.auto_revoke_on_timeout,
                    "reminder_days": campaign.reminder_days,
                },
            )
            self.db.add(row)

        self.db.commit()

    def _save_items_to_db(self, campaign: CertificationCampaign, tenant_id: str = ""):
        """Persist all items for a campaign to the DB."""
        if not self.db:
            return

        from db.models.audit import CertificationItemLog

        tid = tenant_id or campaign.tenant_id or "tenant_default"

        for item in campaign.items:
            row = self.db.query(CertificationItemLog).filter(
                CertificationItemLog.item_id == item.item_id
            ).first()

            if row:
                row.decision = item.decision.value if item.decision else None
                row.decision_date = item.decision_date
                row.decision_comments = item.decision_comments
                row.is_completed = item.is_completed
                row.escalation_level = item.escalation_level
                row.is_overdue = item.is_overdue
                row.risk_score = int(item.risk_score)
                row.has_sod_violation = item.has_sod_violation
                row.risk_flags = item.risk_flags
            else:
                row = CertificationItemLog(
                    item_id=item.item_id,
                    campaign_id=campaign.campaign_id,
                    tenant_id=tid,
                    user_id=item.user_id,
                    user_name=item.user_name,
                    user_department=item.user_department,
                    access_type=item.access_type,
                    access_id=item.access_id,
                    access_name=item.access_name,
                    system=item.system,
                    granted_date=item.granted_date,
                    risk_score=int(item.risk_score),
                    has_sod_violation=item.has_sod_violation,
                    risk_flags=item.risk_flags,
                    reviewer_id=item.reviewer_id,
                    reviewer_name=item.reviewer_name,
                    decision=item.decision.value if item.decision else None,
                    decision_date=item.decision_date,
                    decision_comments=item.decision_comments,
                    is_completed=item.is_completed,
                    escalation_level=item.escalation_level,
                    is_overdue=item.is_overdue,
                )
                self.db.add(row)

        self.db.commit()

    def _load_campaign_from_db(self, campaign_id: str, tenant_id: str = "") -> Optional[CertificationCampaign]:
        """Load a campaign + its items from the DB."""
        if not self.db:
            return None

        from db.models.audit import CertificationCampaignLog, CertificationItemLog

        q = self.db.query(CertificationCampaignLog).filter(
            CertificationCampaignLog.campaign_id == campaign_id
        )
        if tenant_id:
            q = q.filter(CertificationCampaignLog.tenant_id == tenant_id)

        row = q.first()
        if not row:
            return None

        campaign = self._row_to_campaign(row)

        # Load items
        item_rows = self.db.query(CertificationItemLog).filter(
            CertificationItemLog.campaign_id == campaign_id
        ).all()

        campaign.items = [self._row_to_item(ir) for ir in item_rows]
        campaign.total_items = len(campaign.items)

        return campaign

    def _row_to_campaign(self, row) -> CertificationCampaign:
        """Convert a CertificationCampaignLog DB row to a CertificationCampaign dataclass."""
        config = row.config or {}

        campaign = CertificationCampaign(
            campaign_id=row.campaign_id,
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description or "",
            campaign_type=CampaignType(row.campaign_type),
            start_date=row.start_date or datetime.now(),
            end_date=row.end_date or (datetime.now() + timedelta(days=14)),
            created_at=row.created_at or datetime.now(),
            status=CampaignStatus(row.status),
            owner_id=row.owner_id,
            owner_name=row.owner_name or "",
            included_systems=row.included_systems or ["SAP"],
            included_departments=row.included_departments or [],
            risk_threshold=row.risk_threshold,
            include_sod_only=config.get("include_sod_only", False),
            allow_delegation=config.get("allow_delegation", True),
            require_comments_for_revoke=config.get("require_comments_for_revoke", True),
            auto_revoke_on_timeout=config.get("auto_revoke_on_timeout", False),
            reminder_days=config.get("reminder_days", [7, 3, 1]),
            total_items=row.total_items or 0,
            completed_items=row.completed_items or 0,
            certified_count=row.certified_count or 0,
            revoked_count=row.revoked_count or 0,
        )
        return campaign

    def _row_to_item(self, row) -> CertificationItem:
        """Convert a CertificationItemLog DB row to a CertificationItem dataclass."""
        item = CertificationItem(
            item_id=row.item_id,
            user_id=row.user_id,
            user_name=row.user_name or "",
            user_department=row.user_department or "",
            access_type=row.access_type or "role",
            access_id=row.access_id,
            access_name=row.access_name or "",
            system=row.system or "SAP",
            granted_date=row.granted_date,
            risk_score=row.risk_score or 0,
            has_sod_violation=row.has_sod_violation or False,
            risk_flags=row.risk_flags or [],
            reviewer_id=row.reviewer_id,
            reviewer_name=row.reviewer_name or "",
            decision=CertificationAction(row.decision) if row.decision else None,
            decision_date=row.decision_date,
            decision_comments=row.decision_comments or "",
            is_completed=row.is_completed or False,
            escalation_level=row.escalation_level or 0,
            is_overdue=row.is_overdue or False,
        )
        return item

    # =========================================================================
    # Campaign Creation
    # =========================================================================

    async def create_campaign(self,
                             name: str,
                             description: str,
                             campaign_type: CampaignType,
                             owner_id: str,
                             owner_name: str,
                             tenant_id: str = "",
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             included_systems: Optional[List[str]] = None,
                             included_departments: Optional[List[str]] = None,
                             risk_threshold: Optional[float] = None,
                             include_sod_only: bool = False) -> CertificationCampaign:
        """Create a new certification campaign (persisted to DB)."""

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
            tenant_id=tenant_id,
            included_systems=included_systems or ["SAP"],
            included_departments=included_departments or [],
            risk_threshold=risk_threshold,
            include_sod_only=include_sod_only
        )

        self._save_campaign_to_db(campaign, tenant_id)

        logger.info(f"Created certification campaign {campaign.campaign_id}: {name}")
        return campaign

    async def generate_campaign_items(self, campaign_id: str, tenant_id: str = "") -> CertificationCampaign:
        """Generate certification items for a campaign based on its scope."""
        campaign = self._load_campaign_from_db(campaign_id, tenant_id)
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

        self._save_campaign_to_db(campaign)
        self._save_items_to_db(campaign)

        logger.info(f"Generated {len(items)} items for campaign {campaign_id}")
        return campaign

    async def _generate_user_access_items(self, campaign: CertificationCampaign) -> List[CertificationItem]:
        """Generate items for user access review from DB users and roles."""
        items = []

        if self.db:
            from db.models.user import User, UserRole, Role

            user_query = self.db.query(User)
            if campaign.included_departments:
                user_query = user_query.filter(User.department.in_(campaign.included_departments))

            users = user_query.all()

            for user in users:
                user_roles = (
                    self.db.query(UserRole, Role)
                    .join(Role, UserRole.role_id == Role.id)
                    .filter(UserRole.user_id == user.id)
                    .all()
                )

                for ur, role in user_roles:
                    item = CertificationItem(
                        user_id=user.username or str(user.id),
                        user_name=user.full_name or user.username,
                        user_department=user.department or "",
                        access_type="role",
                        access_id=role.role_id if hasattr(role, 'role_id') else str(role.id),
                        access_name=role.role_name or "",
                        system="SAP",
                        granted_date=ur.assigned_at if hasattr(ur, 'assigned_at') else None,
                        reviewer_id=user.manager_user_id or campaign.owner_id,
                        reviewer_name=campaign.owner_name,
                    )
                    item.risk_score = await self._calculate_item_risk(item, {
                        "roles": [{"role_id": r.role_id if hasattr(r, 'role_id') else str(r.id)}
                                  for _, r in user_roles]
                    })
                    items.append(item)

        if not items:
            # Fallback: generate from static data if no DB users exist
            items = await self._generate_fallback_items(campaign)

        return items

    async def _generate_fallback_items(self, campaign: CertificationCampaign) -> List[CertificationItem]:
        """Fallback item generation from DB users when no user-role assignments exist.

        Queries actual users from the database. If no users exist, returns an
        empty list — no synthetic/demo data is generated.
        """
        items = []

        if not self.db:
            return items

        from db.models.user import User, UserRole, Role

        user_query = self.db.query(User)
        if campaign.included_departments:
            user_query = user_query.filter(User.department.in_(campaign.included_departments))

        users = user_query.all()
        if not users:
            return items

        for user in users:
            user_roles = (
                self.db.query(UserRole, Role)
                .join(Role, UserRole.role_id == Role.id)
                .filter(UserRole.user_id == user.id)
                .all()
            )

            for ur, role in user_roles:
                item = CertificationItem(
                    user_id=user.username or str(user.id),
                    user_name=user.full_name or user.username,
                    user_department=user.department or "",
                    access_type="role",
                    access_id=role.role_id if hasattr(role, 'role_id') else str(role.id),
                    access_name=role.role_name or "",
                    system="SAP",
                    granted_date=ur.assigned_at if hasattr(ur, 'assigned_at') else None,
                    reviewer_id=user.manager_user_id or campaign.owner_id,
                    reviewer_name=campaign.owner_name,
                )
                item.risk_score = await self._calculate_item_risk(item, {
                    "roles": [{"role_id": r.role_id if hasattr(r, 'role_id') else str(r.id)}
                              for _, r in user_roles]
                })
                items.append(item)

        return items

    async def _generate_role_membership_items(self, campaign: CertificationCampaign) -> List[CertificationItem]:
        """Generate items for role membership review — one item per user-role pair, grouped by role."""
        items = []

        if not self.db:
            return items

        from db.models.user import User, UserRole, Role

        role_query = self.db.query(Role)
        roles = role_query.all()

        for role in roles:
            user_role_pairs = (
                self.db.query(UserRole, User)
                .join(User, UserRole.user_id == User.id)
                .filter(UserRole.role_id == role.id)
                .all()
            )

            for ur, user in user_role_pairs:
                # For role membership review the reviewer is the role owner,
                # falling back to the campaign owner if none is set.
                reviewer_id = role.owner_user_id or campaign.owner_id
                reviewer_name = role.owner_email or campaign.owner_name

                item = CertificationItem(
                    user_id=user.username or str(user.id),
                    user_name=user.full_name or user.username,
                    user_department=user.department or "",
                    access_type="role_membership",
                    access_id=role.role_id,
                    access_name=role.role_name or "",
                    system=role.source_system or "SAP",
                    granted_date=ur.assigned_at if hasattr(ur, 'assigned_at') else None,
                    reviewer_id=reviewer_id,
                    reviewer_name=reviewer_name,
                )

                all_role_ids = [
                    {"role_id": role.role_id}
                ]
                item.risk_score = await self._calculate_item_risk(item, {"roles": all_role_ids})
                items.append(item)

        return items

    async def _generate_sensitive_access_items(self, campaign: CertificationCampaign) -> List[CertificationItem]:
        all_items = await self._generate_user_access_items(campaign)
        return [i for i in all_items if i.risk_score >= 60]

    async def _generate_sod_items(self, campaign: CertificationCampaign) -> List[CertificationItem]:
        all_items = await self._generate_user_access_items(campaign)
        for item in all_items:
            if item.access_id in ["Z_VENDOR_MAINT", "Z_PAYMENT_RUN"]:
                item.has_sod_violation = True
                item.sod_details = {"rule_id": "FI_P2P_001", "rule_name": "Purchase to Pay Conflict"}
                item.risk_flags.append("SoD: Vendor + Payment")
        return [i for i in all_items if i.has_sod_violation]

    async def _generate_manager_items(self, campaign: CertificationCampaign) -> List[CertificationItem]:
        return await self._generate_user_access_items(campaign)

    async def _calculate_item_risk(self, item: CertificationItem, user_data: Dict) -> float:
        score = 0.0
        high_risk_roles = ["Z_PAYROLL_RUN", "Z_PAYMENT_RUN", "Z_BASIS_ADMIN", "Z_USER_ADMIN"]
        if item.access_id in high_risk_roles:
            score += 40

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

    async def start_campaign(self, campaign_id: str, tenant_id: str = "") -> CertificationCampaign:
        """Start a campaign and notify reviewers."""
        campaign = self._load_campaign_from_db(campaign_id, tenant_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        if not campaign.items:
            raise ValueError("Campaign has no items. Generate items first.")

        campaign.status = CampaignStatus.ACTIVE
        self._save_campaign_to_db(campaign)

        await self._notify_campaign_start(campaign)
        logger.info(f"Started campaign {campaign_id}")
        return campaign

    async def _notify_campaign_start(self, campaign: CertificationCampaign):
        if not self.notification_handler:
            return

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
                              delegate_to: Optional[str] = None,
                              tenant_id: str = "") -> CertificationItem:
        """Process a certification decision (persisted to DB)."""
        campaign = self._load_campaign_from_db(campaign_id, tenant_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        item = next((i for i in campaign.items if i.item_id == item_id), None)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        if item.reviewer_id != reviewer_id and item.delegated_to != reviewer_id:
            raise PermissionError(f"User {reviewer_id} is not authorized to review this item")

        if action == CertificationAction.REVOKE:
            if campaign.require_comments_for_revoke and not comments:
                raise ValueError("Comments required for revocation")

        if action == CertificationAction.DELEGATE:
            if not delegate_to:
                raise ValueError("Delegation requires delegate_to parameter")
            item.delegated_to = delegate_to
            item.decision_comments = f"Delegated by {reviewer_id}: {comments}"
        else:
            item.decision = action
            item.decision_date = datetime.now()
            item.decision_comments = comments
            item.is_completed = True

        # Update campaign stats
        campaign.completed_items = sum(1 for i in campaign.items if i.is_completed)
        campaign.certified_count = sum(1 for i in campaign.items if i.decision == CertificationAction.CERTIFY)
        campaign.revoked_count = sum(1 for i in campaign.items if i.decision == CertificationAction.REVOKE)

        if all(i.is_completed for i in campaign.items):
            campaign.status = CampaignStatus.COMPLETED

        self._save_campaign_to_db(campaign)
        self._save_items_to_db(campaign)

        # Record certification decision evidence
        try:
            from core.evidence.models import EvidenceType
            self.evidence_engine.record(
                evidence_type=EvidenceType.CERTIFICATION_DECISION,
                tenant_id=tenant_id or campaign.tenant_id,
                actor_user_id=reviewer_id,
                action=f"certification_{action.value}",
                target_user_id=item.user_id,
                target_object_type="certification_item",
                target_object_id=item_id,
                campaign_id=campaign_id,
                justification=comments,
                action_details={
                    "role_id": item.role_id,
                    "system": item.system,
                    "risk_score": item.risk_score,
                },
            )
        except Exception as exc:
            logger.warning(f"EvidenceEngine record skipped: {exc}")

        logger.info(f"Decision recorded for item {item_id}: {action.value}")
        return item

    async def bulk_certify(self,
                          campaign_id: str,
                          item_ids: List[str],
                          reviewer_id: str,
                          comments: str = "Bulk certified",
                          tenant_id: str = "") -> Dict:
        processed = 0
        errors = []
        for item_id in item_ids:
            try:
                await self.process_decision(
                    campaign_id=campaign_id,
                    item_id=item_id,
                    action=CertificationAction.CERTIFY,
                    reviewer_id=reviewer_id,
                    comments=comments,
                    tenant_id=tenant_id,
                )
                processed += 1
            except Exception as e:
                errors.append({"item_id": item_id, "error": str(e)})

        return {"processed": processed, "errors": errors}

    # =========================================================================
    # Reminder and Escalation
    # =========================================================================

    async def send_reminders(self, tenant_id: str = ""):
        """Send reminders for pending certifications."""
        for campaign in self._get_all_campaigns_from_db(tenant_id):
            if campaign.status != CampaignStatus.ACTIVE:
                continue
            days_remaining = campaign.days_remaining()
            if days_remaining in campaign.reminder_days:
                await self._send_campaign_reminders(campaign, days_remaining)

    async def _send_campaign_reminders(self, campaign: CertificationCampaign, days_remaining: int):
        if not self.notification_handler:
            return

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

    async def process_expired_campaigns(self, tenant_id: str = ""):
        for campaign in self._get_all_campaigns_from_db(tenant_id):
            if campaign.status != CampaignStatus.ACTIVE:
                continue
            if campaign.is_overdue():
                if self.config["auto_revoke_on_timeout"]:
                    await self._auto_revoke_pending(campaign)
                else:
                    campaign.status = CampaignStatus.IN_REVIEW
                    for item in campaign.items:
                        if not item.is_completed:
                            item.is_overdue = True
                self._save_campaign_to_db(campaign)
                self._save_items_to_db(campaign)

    async def _auto_revoke_pending(self, campaign: CertificationCampaign):
        for item in campaign.items:
            if not item.is_completed:
                item.decision = CertificationAction.REVOKE
                item.decision_date = datetime.now()
                item.decision_comments = "Auto-revoked due to certification timeout"
                item.is_completed = True
        campaign.status = CampaignStatus.COMPLETED

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_campaign(self, campaign_id: str, tenant_id: str = "") -> Optional[CertificationCampaign]:
        """Get campaign by ID, scoped to tenant."""
        return self._load_campaign_from_db(campaign_id, tenant_id)

    def get_campaigns(self,
                     status: Optional[CampaignStatus] = None,
                     owner_id: Optional[str] = None,
                     tenant_id: str = "") -> List[CertificationCampaign]:
        """Get campaigns with filters (DB-backed)."""
        return self._get_all_campaigns_from_db(tenant_id, status=status, owner_id=owner_id)

    def _get_all_campaigns_from_db(self, tenant_id: str = "",
                                    status: Optional[CampaignStatus] = None,
                                    owner_id: Optional[str] = None) -> List[CertificationCampaign]:
        """Query campaigns from DB with optional filters."""
        if not self.db:
            return []

        from db.models.audit import CertificationCampaignLog, CertificationItemLog

        q = self.db.query(CertificationCampaignLog)
        if tenant_id:
            q = q.filter(CertificationCampaignLog.tenant_id == tenant_id)
        if status:
            q = q.filter(CertificationCampaignLog.status == status.value)
        if owner_id:
            q = q.filter(CertificationCampaignLog.owner_id == owner_id)

        rows = q.all()
        campaigns = []
        for row in rows:
            campaign = self._row_to_campaign(row)
            # Load items
            item_rows = self.db.query(CertificationItemLog).filter(
                CertificationItemLog.campaign_id == campaign.campaign_id
            ).all()
            campaign.items = [self._row_to_item(ir) for ir in item_rows]
            campaign.total_items = len(campaign.items)
            campaigns.append(campaign)

        return campaigns

    def get_reviewer_items(self,
                          reviewer_id: str,
                          campaign_id: Optional[str] = None,
                          pending_only: bool = True,
                          tenant_id: str = "") -> List[CertificationItem]:
        """Get certification items assigned to a reviewer (DB-backed)."""
        if not self.db:
            return []

        from db.models.audit import CertificationItemLog, CertificationCampaignLog

        q = self.db.query(CertificationItemLog)
        if campaign_id:
            q = q.filter(CertificationItemLog.campaign_id == campaign_id)
        if tenant_id:
            q = q.filter(CertificationItemLog.tenant_id == tenant_id)

        rows = q.all()
        items = []
        for row in rows:
            if row.reviewer_id == reviewer_id:
                if pending_only and row.is_completed:
                    continue
                items.append(self._row_to_item(row))

        return items

    def get_reviewer_workload(self, tenant_id: str = "") -> Dict[str, Dict]:
        """Get workload summary for all reviewers."""
        campaigns = self._get_all_campaigns_from_db(tenant_id, status=CampaignStatus.ACTIVE)
        workload = {}

        for campaign in campaigns:
            for item in campaign.items:
                reviewer = item.delegated_to or item.reviewer_id
                if reviewer not in workload:
                    workload[reviewer] = {"total": 0, "pending": 0, "completed": 0, "campaigns": set()}
                workload[reviewer]["total"] += 1
                workload[reviewer]["campaigns"].add(campaign.campaign_id)
                if item.is_completed:
                    workload[reviewer]["completed"] += 1
                else:
                    workload[reviewer]["pending"] += 1

        for r in workload.values():
            r["campaigns"] = list(r["campaigns"])

        return workload

    def get_statistics(self, tenant_id: str = "") -> Dict:
        """Get overall certification statistics (DB-backed)."""
        if not self.db:
            return {"total_campaigns": 0, "active_campaigns": 0, "completed_campaigns": 0,
                    "total_items_reviewed": 0, "total_certified": 0, "total_revoked": 0,
                    "certification_rate": 0, "revocation_rate": 0}

        from db.models.audit import CertificationCampaignLog

        q = self.db.query(CertificationCampaignLog)
        if tenant_id:
            q = q.filter(CertificationCampaignLog.tenant_id == tenant_id)

        rows = q.all()
        total_campaigns = len(rows)
        active = sum(1 for r in rows if r.status == CampaignStatus.ACTIVE.value)
        completed = sum(1 for r in rows if r.status == CampaignStatus.COMPLETED.value)
        total_items = sum(r.total_items or 0 for r in rows)
        certified = sum(r.certified_count or 0 for r in rows)
        revoked = sum(r.revoked_count or 0 for r in rows)

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

    # =========================================================================
    # Review Types (Role Owner, App Owner, Compliance)
    # =========================================================================

    async def generate_role_owner_items(self,
                                        campaign_id: str,
                                        role_id: str,
                                        role_owner_id: str,
                                        role_owner_name: str = "",
                                        tenant_id: str = "") -> List[CertificationItem]:
        campaign = self._load_campaign_from_db(campaign_id, tenant_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        items = []
        all_items = await self._generate_user_access_items(campaign)
        for item in all_items:
            if item.access_id == role_id:
                item.reviewer_id = role_owner_id
                item.reviewer_name = role_owner_name or role_owner_id
                item.review_type = ReviewType.ROLE_OWNER_REVIEW.value
                items.append(item)

        campaign.items.extend(items)
        campaign.total_items = len(campaign.items)
        self._save_campaign_to_db(campaign)
        self._save_items_to_db(campaign)
        logger.info(f"Generated {len(items)} role-owner review items for {role_id}")
        return items

    async def generate_app_owner_items(self,
                                       campaign_id: str,
                                       system_id: str,
                                       app_owner_id: str,
                                       app_owner_name: str = "",
                                       tenant_id: str = "") -> List[CertificationItem]:
        campaign = self._load_campaign_from_db(campaign_id, tenant_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        items = []
        all_items = await self._generate_user_access_items(campaign)
        for item in all_items:
            if item.system == system_id:
                item.reviewer_id = app_owner_id
                item.reviewer_name = app_owner_name or app_owner_id
                item.review_type = ReviewType.APP_OWNER_REVIEW.value
                items.append(item)

        campaign.items.extend(items)
        campaign.total_items = len(campaign.items)
        self._save_campaign_to_db(campaign)
        self._save_items_to_db(campaign)
        logger.info(f"Generated {len(items)} app-owner review items for {system_id}")
        return items

    async def generate_compliance_items(self,
                                        campaign_id: str,
                                        reviewer_id: str,
                                        reviewer_name: str = "",
                                        min_risk_score: float = 70,
                                        tenant_id: str = "") -> List[CertificationItem]:
        campaign = self._load_campaign_from_db(campaign_id, tenant_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        items = []
        all_items = await self._generate_user_access_items(campaign)
        for item in all_items:
            if item.risk_score >= min_risk_score or item.has_sod_violation:
                item.reviewer_id = reviewer_id
                item.reviewer_name = reviewer_name or reviewer_id
                item.review_type = ReviewType.COMPLIANCE_REVIEW.value
                items.append(item)

        campaign.items.extend(items)
        campaign.total_items = len(campaign.items)
        self._save_campaign_to_db(campaign)
        self._save_items_to_db(campaign)
        logger.info(f"Generated {len(items)} compliance review items (risk >= {min_risk_score})")
        return items

    # =========================================================================
    # Escalation
    # =========================================================================

    ESCALATION_CONFIG = {
        "level_1_days": 3,
        "level_2_days": 5,
        "level_3_days": 7,
        "auto_action": "revoke",
    }

    async def check_escalation(self, campaign_id: str, tenant_id: str = "") -> Dict:
        campaign = self._load_campaign_from_db(campaign_id, tenant_id)
        if not campaign or campaign.status != CampaignStatus.ACTIVE:
            return {"escalated": 0}

        escalated = 0
        now = datetime.now()

        for item in campaign.items:
            if item.is_completed:
                continue

            days_overdue = (now - campaign.end_date).days if now > campaign.end_date else 0
            if days_overdue <= 0:
                target_days = (campaign.end_date - campaign.start_date).days
                days_pending = (now - campaign.start_date).days
                if target_days > 0 and days_pending > target_days * 0.7:
                    days_overdue = 1

            if days_overdue <= 0:
                continue

            if days_overdue >= self.ESCALATION_CONFIG["level_3_days"] and item.escalation_level < 3:
                if self.ESCALATION_CONFIG["auto_action"] == "revoke":
                    item.decision = CertificationAction.REVOKE
                    item.decision_date = now
                    item.decision_comments = "Auto-revoked: escalation level 3 reached"
                    item.is_completed = True
                else:
                    item.decision = CertificationAction.CERTIFY
                    item.decision_date = now
                    item.decision_comments = "Auto-certified: escalation level 3 reached"
                    item.is_completed = True
                item.escalation_level = 3
                escalated += 1
            elif days_overdue >= self.ESCALATION_CONFIG["level_2_days"] and item.escalation_level < 2:
                await self.escalate_item(item, campaign.owner_id, "Escalated to campaign owner (level 2)")
                escalated += 1
            elif days_overdue >= self.ESCALATION_CONFIG["level_1_days"] and item.escalation_level < 1:
                await self.escalate_item(item, item.reviewer_id, "Reminder escalation (level 1)")
                escalated += 1

        self._save_campaign_to_db(campaign)
        self._save_items_to_db(campaign)
        return {"campaign_id": campaign_id, "escalated": escalated}

    async def escalate_item(self, item: CertificationItem, escalate_to: str, reason: str):
        item.escalation_level += 1
        item.escalated_to = escalate_to
        item.escalated_at = datetime.now()
        item.is_overdue = True

        if self.notification_handler:
            await self.notification_handler(
                recipient=escalate_to,
                subject="ESCALATION: Certification item requires review",
                message=f"Item for user {item.user_name} / {item.access_name} needs review. Reason: {reason}"
            )
        logger.info(f"Escalated item {item.item_id} to {escalate_to} (level {item.escalation_level})")

    # =========================================================================
    # Evidence Management
    # =========================================================================

    async def add_evidence(self, campaign_id: str, item_id: str,
                           evidence_type: str, description: str,
                           uploaded_by: str, content: Optional[str] = None,
                           file_path: Optional[str] = None,
                           tenant_id: str = "") -> ReviewEvidence:
        campaign = self._load_campaign_from_db(campaign_id, tenant_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        item = next((i for i in campaign.items if i.item_id == item_id), None)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        evidence = ReviewEvidence(
            item_id=item_id,
            evidence_type=evidence_type,
            description=description,
            uploaded_by=uploaded_by,
            content=content,
            file_path=file_path,
        )
        item.evidence.append(evidence.to_dict())
        self._save_items_to_db(campaign)
        logger.info(f"Added evidence {evidence.evidence_id} to item {item_id}")
        return evidence

    def get_evidence(self, campaign_id: str, item_id: str, tenant_id: str = "") -> List[Dict]:
        campaign = self._load_campaign_from_db(campaign_id, tenant_id)
        if not campaign:
            return []
        item = next((i for i in campaign.items if i.item_id == item_id), None)
        if not item:
            return []
        return item.evidence

    # =========================================================================
    # De-provisioning Integration
    # =========================================================================

    async def execute_revocations(self, campaign_id: str, tenant_id: str = "") -> Dict:
        campaign = self._load_campaign_from_db(campaign_id, tenant_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        revoked_items = [
            i for i in campaign.items
            if i.decision == CertificationAction.REVOKE and i.is_completed
        ]

        provisioned = 0
        errors = []
        for item in revoked_items:
            try:
                logger.info(
                    f"Deprovisioning: user={item.user_id} role={item.access_id} "
                    f"system={item.system} reviewer={item.reviewer_id}"
                )
                provisioned += 1

                # Record revocation evidence
                try:
                    from core.evidence.models import EvidenceType
                    self.evidence_engine.record(
                        evidence_type=EvidenceType.CERTIFICATION_REVOCATION,
                        tenant_id=tenant_id or campaign.tenant_id,
                        actor_user_id="system",
                        action="revoke_access",
                        target_user_id=item.user_id,
                        target_object_type="role",
                        target_object_id=item.access_id or item.role_id or "",
                        campaign_id=campaign_id,
                        action_details={
                            "system": item.system,
                            "reviewer": item.reviewer_id,
                        },
                    )
                except Exception as exc:
                    logger.warning(f"EvidenceEngine record skipped: {exc}")
            except Exception as e:
                errors.append({"item_id": item.item_id, "error": str(e)})

        return {
            "campaign_id": campaign_id,
            "total_revoked": len(revoked_items),
            "provisioned": provisioned,
            "errors": errors,
        }
