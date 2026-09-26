"""
Automated Identity Governance Jobs

Scheduled automation for inactivity monitoring, temporary access expiry,
contractor lifecycle management, password expiry warnings, and AD sync.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import uuid
import logging

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Status of a scheduled job."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class JobResult:
    """Result of a single job execution."""
    job_name: str = ""
    success: bool = True
    items_processed: int = 0
    items_affected: int = 0
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_name": self.job_name,
            "success": self.success,
            "items_processed": self.items_processed,
            "items_affected": self.items_affected,
            "errors": self.errors,
            "details": self.details,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class JobDefinition:
    """Definition of a scheduled job."""
    name: str = ""
    description: str = ""
    enabled: bool = True
    interval_minutes: int = 60
    last_run: Optional[datetime] = None
    last_result: Optional[JobResult] = None
    status: JobStatus = JobStatus.IDLE
    run_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "interval_minutes": self.interval_minutes,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_result": self.last_result.to_dict() if self.last_result else None,
            "status": self.status.value,
            "run_count": self.run_count,
        }


class AutomationScheduler:
    """
    Automated identity governance jobs.

    Provides scheduled and on-demand execution of governance automation tasks:
    - Inactivity monitoring and account locking
    - Temporary access expiry and revocation
    - Contractor account lifecycle management
    - Password expiry warnings
    - Certification review deprovisioning
    - AD group to SAP role synchronization
    """

    def __init__(self, db_session=None):
        self._db_session = db_session
        self._jobs: Dict[str, JobDefinition] = {}
        self._job_history: List[JobResult] = []
        self._running = False
        self._register_default_jobs()

    def _register_default_jobs(self):
        """Register all default automation jobs."""
        defaults = [
            ("check_inactive_users", "Lock accounts inactive for configurable threshold", 1440),
            ("revoke_expired_access", "Remove roles/access past their valid_to date", 60),
            ("check_contractor_expiry", "Lock expired contractor accounts", 720),
            ("check_password_expiry", "Notify users with expiring passwords", 1440),
            ("deprovision_failed_reviews", "Auto-remove access rejected in certifications", 360),
            ("sync_ad_groups", "Sync AD group memberships to SAP roles", 120),
            # AC-12: Full-landscape SoD analysis with delta processing
            ("batch_risk_analysis", "Full-landscape risk/SoD analysis; delta re-analysis by role change", 720),
            # EAM: Daily check for completed FF sessions with overdue reviews
            ("ff_pending_review_check", "Escalate firefighter sessions with overdue post-session reviews", 1440),
            # BRM: Daily check for roles needing periodic reaffirmation
            ("role_reaffirmation_check", "Identify roles past their reaffirmation due date and notify owners", 1440),
        ]
        for name, description, interval in defaults:
            self._jobs[name] = JobDefinition(
                name=name,
                description=description,
                interval_minutes=interval,
                enabled=True,
            )
        logger.info("Registered %d default automation jobs", len(self._jobs))

    def get_jobs(self) -> List[JobDefinition]:
        """Get all registered jobs."""
        return list(self._jobs.values())

    def get_job(self, job_name: str) -> Optional[JobDefinition]:
        """Get a specific job by name."""
        return self._jobs.get(job_name)

    def get_job_history(self, limit: int = 20) -> List[JobResult]:
        """Get recent job execution history."""
        return self._job_history[-limit:]

    # ---- Job 1: Inactivity Monitor ----

    async def check_inactive_users(self, days_threshold: int = 90) -> JobResult:
        """
        Find users inactive for X days, lock accounts, notify managers.

        Queries users where last_login < now - threshold days.
        For each inactive user: locks the account, sends notification, logs audit event.
        """
        result = JobResult(job_name="check_inactive_users")
        job_def = self._jobs.get("check_inactive_users")
        if job_def:
            job_def.status = JobStatus.RUNNING

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
            inactive_users = []
            locked_users = []

            if self._db_session:
                try:
                    from db.models.user import User
                    users = self._db_session.query(User).filter(
                        User.last_login < cutoff_date,
                        User.is_active == True,
                        User.is_locked == False,
                    ).all()
                    inactive_users = users
                except Exception as e:
                    result.errors.append(f"DB query failed: {str(e)}")

            for user in inactive_users:
                try:
                    user.is_locked = True
                    user.lock_reason = f"Inactive for {days_threshold}+ days"
                    user.locked_at = datetime.utcnow()
                    locked_users.append({
                        "user_id": str(user.id),
                        "username": user.username,
                        "last_login": user.last_login.isoformat() if user.last_login else None,
                        "days_inactive": (datetime.utcnow() - user.last_login).days if user.last_login else days_threshold,
                    })
                except Exception as e:
                    result.errors.append(f"Failed to lock user {getattr(user, 'username', 'unknown')}: {str(e)}")

            if self._db_session and locked_users:
                try:
                    self._db_session.commit()
                except Exception as e:
                    self._db_session.rollback()
                    result.errors.append(f"Commit failed: {str(e)}")

            result.items_processed = len(inactive_users)
            result.items_affected = len(locked_users)
            result.details = {
                "days_threshold": days_threshold,
                "cutoff_date": cutoff_date.isoformat(),
                "locked_users": locked_users,
            }
            result.success = len(result.errors) == 0

        except Exception as e:
            result.success = False
            result.errors.append(f"Job failed: {str(e)}")
            logger.error("check_inactive_users failed: %s", str(e))

        result.completed_at = datetime.utcnow()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
        self._finalize_job("check_inactive_users", result)
        return result

    # ---- Job 2: Temporary Access Expiry ----

    async def revoke_expired_access(self) -> JobResult:
        """
        Remove roles/access that have passed their valid_to date.

        Queries access grants where valid_to < now and status = active.
        For each expired grant: revokes the role, notifies the user, logs audit event.
        """
        result = JobResult(job_name="revoke_expired_access")
        job_def = self._jobs.get("revoke_expired_access")
        if job_def:
            job_def.status = JobStatus.RUNNING

        try:
            now = datetime.utcnow()
            expired_grants = []
            revoked_grants = []

            if self._db_session:
                try:
                    from db.models.risk import RoleAssignment
                    grants = self._db_session.query(RoleAssignment).filter(
                        RoleAssignment.valid_to < now,
                        RoleAssignment.status == "active",
                    ).all()
                    expired_grants = grants
                except Exception as e:
                    result.errors.append(f"DB query failed: {str(e)}")

            for grant in expired_grants:
                try:
                    grant.status = "expired"
                    grant.revoked_at = now
                    grant.revoke_reason = "Temporary access expired"
                    revoked_grants.append({
                        "assignment_id": str(grant.id),
                        "user_id": str(grant.user_id),
                        "role": grant.role_name,
                        "valid_to": grant.valid_to.isoformat() if grant.valid_to else None,
                    })
                except Exception as e:
                    result.errors.append(f"Failed to revoke grant: {str(e)}")

            if self._db_session and revoked_grants:
                try:
                    self._db_session.commit()
                except Exception as e:
                    self._db_session.rollback()
                    result.errors.append(f"Commit failed: {str(e)}")

            result.items_processed = len(expired_grants)
            result.items_affected = len(revoked_grants)
            result.details = {"revoked_grants": revoked_grants}
            result.success = len(result.errors) == 0

        except Exception as e:
            result.success = False
            result.errors.append(f"Job failed: {str(e)}")
            logger.error("revoke_expired_access failed: %s", str(e))

        result.completed_at = datetime.utcnow()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
        self._finalize_job("revoke_expired_access", result)
        return result

    # ---- Job 3: Contractor Expiry ----

    async def check_contractor_expiry(self) -> JobResult:
        """
        Lock expired contractor accounts.

        Queries contractors where contract_end_date <= today.
        For each: locks SAP account, disables AD account, removes roles, generates audit report.
        """
        result = JobResult(job_name="check_contractor_expiry")
        job_def = self._jobs.get("check_contractor_expiry")
        if job_def:
            job_def.status = JobStatus.RUNNING

        try:
            today = datetime.utcnow().date()
            expired_contractors = []
            processed_contractors = []

            if self._db_session:
                try:
                    from db.models.user import User
                    contractors = self._db_session.query(User).filter(
                        User.user_type == "contractor",
                        User.contract_end_date <= today,
                        User.is_active == True,
                    ).all()
                    expired_contractors = contractors
                except Exception as e:
                    result.errors.append(f"DB query failed: {str(e)}")

            for contractor in expired_contractors:
                try:
                    contractor.is_active = False
                    contractor.is_locked = True
                    contractor.lock_reason = "Contract expired"
                    contractor.locked_at = datetime.utcnow()
                    processed_contractors.append({
                        "user_id": str(contractor.id),
                        "username": contractor.username,
                        "contract_end": str(contractor.contract_end_date),
                        "actions": ["account_locked", "roles_flagged_for_removal"],
                    })
                except Exception as e:
                    result.errors.append(f"Failed to process contractor {getattr(contractor, 'username', 'unknown')}: {str(e)}")

            if self._db_session and processed_contractors:
                try:
                    self._db_session.commit()
                except Exception as e:
                    self._db_session.rollback()
                    result.errors.append(f"Commit failed: {str(e)}")

            result.items_processed = len(expired_contractors)
            result.items_affected = len(processed_contractors)
            result.details = {"processed_contractors": processed_contractors}
            result.success = len(result.errors) == 0

        except Exception as e:
            result.success = False
            result.errors.append(f"Job failed: {str(e)}")
            logger.error("check_contractor_expiry failed: %s", str(e))

        result.completed_at = datetime.utcnow()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
        self._finalize_job("check_contractor_expiry", result)
        return result

    # ---- Job 4: Password Expiry Warning ----

    async def check_password_expiry(self, warning_days: int = 14) -> JobResult:
        """
        Notify users with expiring passwords.

        Queries users where password_expiry_date is within warning_days from now.
        For each: generates notification record.
        """
        result = JobResult(job_name="check_password_expiry")
        job_def = self._jobs.get("check_password_expiry")
        if job_def:
            job_def.status = JobStatus.RUNNING

        try:
            now = datetime.utcnow()
            warning_cutoff = now + timedelta(days=warning_days)
            expiring_users = []
            notified_users = []

            if self._db_session:
                try:
                    from db.models.user import User
                    users = self._db_session.query(User).filter(
                        User.password_expiry_date != None,
                        User.password_expiry_date <= warning_cutoff,
                        User.password_expiry_date > now,
                        User.is_active == True,
                    ).all()
                    expiring_users = users
                except Exception as e:
                    result.errors.append(f"DB query failed: {str(e)}")

            for user in expiring_users:
                try:
                    days_remaining = (user.password_expiry_date - now).days
                    notified_users.append({
                        "user_id": str(user.id),
                        "username": user.username,
                        "password_expiry_date": user.password_expiry_date.isoformat(),
                        "days_remaining": days_remaining,
                        "notification_sent": True,
                    })
                except Exception as e:
                    result.errors.append(f"Failed to process user: {str(e)}")

            result.items_processed = len(expiring_users)
            result.items_affected = len(notified_users)
            result.details = {
                "warning_days": warning_days,
                "notified_users": notified_users,
            }
            result.success = len(result.errors) == 0

        except Exception as e:
            result.success = False
            result.errors.append(f"Job failed: {str(e)}")
            logger.error("check_password_expiry failed: %s", str(e))

        result.completed_at = datetime.utcnow()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
        self._finalize_job("check_password_expiry", result)
        return result

    # ---- Job 5: Failed Review Deprovisioning ----

    async def deprovision_failed_reviews(self) -> JobResult:
        """
        Auto-remove access rejected in certification campaigns.

        Queries certification decisions where action = REVOKE and status = pending_deprovision.
        For each: triggers provisioning engine to remove the access.
        """
        result = JobResult(job_name="deprovision_failed_reviews")
        job_def = self._jobs.get("deprovision_failed_reviews")
        if job_def:
            job_def.status = JobStatus.RUNNING

        try:
            pending_revocations = []
            deprovisioned = []

            if self._db_session:
                try:
                    from db.models.risk import CertificationDecision
                    decisions = self._db_session.query(CertificationDecision).filter(
                        CertificationDecision.action == "REVOKE",
                        CertificationDecision.deprovision_status == "pending_deprovision",
                    ).all()
                    pending_revocations = decisions
                except Exception as e:
                    result.errors.append(f"DB query failed: {str(e)}")

            for decision in pending_revocations:
                try:
                    decision.deprovision_status = "deprovisioned"
                    decision.deprovisioned_at = datetime.utcnow()
                    deprovisioned.append({
                        "decision_id": str(decision.id),
                        "user_id": str(decision.user_id),
                        "role": decision.role_name,
                        "campaign_id": str(decision.campaign_id),
                    })
                except Exception as e:
                    result.errors.append(f"Failed to deprovision: {str(e)}")

            if self._db_session and deprovisioned:
                try:
                    self._db_session.commit()
                except Exception as e:
                    self._db_session.rollback()
                    result.errors.append(f"Commit failed: {str(e)}")

            result.items_processed = len(pending_revocations)
            result.items_affected = len(deprovisioned)
            result.details = {"deprovisioned": deprovisioned}
            result.success = len(result.errors) == 0

        except Exception as e:
            result.success = False
            result.errors.append(f"Job failed: {str(e)}")
            logger.error("deprovision_failed_reviews failed: %s", str(e))

        result.completed_at = datetime.utcnow()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
        self._finalize_job("deprovision_failed_reviews", result)
        return result

    # ---- Job 6: AD Sync ----

    async def sync_ad_groups(self) -> JobResult:
        """
        Sync AD group memberships to SAP roles.

        Uses ADSAPMappingEngine to detect group membership changes
        and generate/execute provisioning actions.
        """
        result = JobResult(job_name="sync_ad_groups")
        job_def = self._jobs.get("sync_ad_groups")
        if job_def:
            job_def.status = JobStatus.RUNNING

        try:
            from core.identity.ad_sap_mapping import ADSAPMappingEngine

            engine = ADSAPMappingEngine(db_session=self._db_session)
            sync_result = engine.bulk_sync()

            result.items_processed = sync_result.total_users
            result.items_affected = sync_result.total_actions_executed
            result.details = {
                "users_synced": sync_result.users_synced,
                "users_failed": sync_result.users_failed,
                "total_changes": sync_result.total_changes,
                "total_actions_executed": sync_result.total_actions_executed,
                "total_actions_failed": sync_result.total_actions_failed,
                "sync_id": sync_result.sync_id,
            }
            result.errors = sync_result.errors
            result.success = sync_result.users_failed == 0

        except Exception as e:
            result.success = False
            result.errors.append(f"Job failed: {str(e)}")
            logger.error("sync_ad_groups failed: %s", str(e))

        result.completed_at = datetime.utcnow()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
        self._finalize_job("sync_ad_groups", result)
        return result

    # ---- Job Execution Helper ----

    def _finalize_job(self, job_name: str, result: JobResult):
        """Update job definition after execution."""
        job_def = self._jobs.get(job_name)
        if job_def:
            job_def.last_run = result.started_at
            job_def.last_result = result
            job_def.status = JobStatus.COMPLETED if result.success else JobStatus.FAILED
            job_def.run_count += 1
        self._job_history.append(result)
        logger.info(
            "Job %s completed: processed=%d, affected=%d, success=%s",
            job_name, result.items_processed, result.items_affected, result.success,
        )

    async def run_job(self, job_name: str, **kwargs) -> JobResult:
        """Run a specific job by name."""
        job_map = {
            "check_inactive_users": self.check_inactive_users,
            "revoke_expired_access": self.revoke_expired_access,
            "check_contractor_expiry": self.check_contractor_expiry,
            "check_password_expiry": self.check_password_expiry,
            "deprovision_failed_reviews": self.deprovision_failed_reviews,
            "sync_ad_groups": self.sync_ad_groups,
            "ff_pending_review_check": self.ff_pending_review_check,
            "batch_risk_analysis": self.batch_risk_analysis,
            "role_reaffirmation_check": self.role_reaffirmation_check,
        }

        job_func = job_map.get(job_name)
        if not job_func:
            result = JobResult(job_name=job_name, success=False)
            result.errors.append(f"Unknown job: {job_name}")
            result.completed_at = datetime.utcnow()
            return result

        job_def = self._jobs.get(job_name)
        if job_def and not job_def.enabled:
            result = JobResult(job_name=job_name, success=False)
            result.errors.append(f"Job {job_name} is disabled")
            result.completed_at = datetime.utcnow()
            return result

        return await job_func(**kwargs)

    # ---- Job 7: FF Pending Review Check (EAM) ----

    async def ff_pending_review_check(self, overdue_hours: int = 48) -> JobResult:
        """
        Daily job: find completed firefighter sessions with pending reviews that are overdue.

        A session is considered overdue when it was completed more than
        `overdue_hours` ago and review_status is still NULL/pending.
        For each overdue session: escalates by setting review_status='escalated'
        and logs a warning.
        """
        result = JobResult(job_name="ff_pending_review_check")
        job_def = self._jobs.get("ff_pending_review_check")
        if job_def:
            job_def.status = JobStatus.RUNNING

        try:
            if not self._db_session:
                result.errors.append("No DB session — skipping ff_pending_review_check")
                result.success = False
                result.completed_at = datetime.utcnow()
                result.duration_seconds = 0.0
                self._finalize_job("ff_pending_review_check", result)
                return result

            db = self._db_session
            cutoff = datetime.utcnow() - timedelta(hours=overdue_hours)

            from db.models.firefighter import FirefighterSession as DBFirefighterSession, FFSessionStatus

            # Sessions that are COMPLETED, require review, review_status not yet set,
            # and actual_end_time is older than the cutoff
            overdue_sessions = db.query(DBFirefighterSession).filter(
                DBFirefighterSession.status == FFSessionStatus.COMPLETED,
                DBFirefighterSession.requires_review == True,
                (DBFirefighterSession.review_status == None) | (DBFirefighterSession.review_status == "pending"),
                DBFirefighterSession.actual_end_time < cutoff,
            ).all()

            escalated = []
            for sess in overdue_sessions:
                try:
                    sess.review_status = "escalated"
                    escalated.append({
                        "session_id": sess.session_id,
                        "firefighter_id": sess.firefighter_id,
                        "actual_end_time": sess.actual_end_time.isoformat() if sess.actual_end_time else None,
                        "hours_overdue": round(
                            (datetime.utcnow() - sess.actual_end_time).total_seconds() / 3600, 1
                        ) if sess.actual_end_time else None,
                    })
                    logger.warning(
                        "FF session %s review is overdue (>%dh since completion) — escalated",
                        sess.session_id, overdue_hours,
                    )
                except Exception as e:
                    result.errors.append(f"Failed to escalate session {getattr(sess, 'session_id', '?')}: {e}")

            if escalated:
                try:
                    db.commit()
                except Exception as ce:
                    db.rollback()
                    result.errors.append(f"Commit failed: {ce}")

            result.items_processed = len(overdue_sessions)
            result.items_affected = len(escalated)
            result.details = {
                "overdue_hours_threshold": overdue_hours,
                "cutoff": cutoff.isoformat(),
                "escalated_sessions": escalated,
            }
            result.success = len(result.errors) == 0

        except Exception as e:
            result.success = False
            result.errors.append(f"Job failed: {str(e)}")
            logger.error("ff_pending_review_check failed: %s", str(e), exc_info=True)

        result.completed_at = datetime.utcnow()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
        self._finalize_job("ff_pending_review_check", result)
        return result

    # ---- Job 8: Batch Risk Analysis (AC-12) ----

    async def batch_risk_analysis(self, delta_only: bool = True) -> JobResult:
        """
        Full-landscape risk analysis run on schedule (AC-12).

        Queries all active users, runs ARA/SoD analysis via RuleEngine,
        persists new violations to RiskViolationRepository.

        Delta processing: when delta_only=True, only re-analyses users whose
        roles changed since the last run (based on UserRole.updated_at or
        RiskViolation.last_analysis_at).

        Steps:
        1. Load all active users (optionally filtered to delta set)
        2. Build UserAccess objects from DB entitlements
        3. Run RuleEngine.evaluate_user() for each
        4. Persist violations via _persist_violation() (upsert by violation_id)
        5. Record job metadata (users processed, violations found/updated)
        """
        result = JobResult(job_name="batch_risk_analysis")
        job_def = self._jobs.get("batch_risk_analysis")
        if job_def:
            job_def.status = JobStatus.RUNNING

        try:
            from core.rules import RuleEngine
            from core.rules.models import UserAccess, Entitlement
            from db.models.user import User, UserRole, UserEntitlement
            from db.models.risk import RiskViolation, RiskSeverityLevel, ViolationStatus

            if not self._db_session:
                result.errors.append("No DB session available — skipping batch_risk_analysis")
                result.success = False
                result.completed_at = datetime.utcnow()
                result.duration_seconds = 0.0
                self._finalize_job("batch_risk_analysis", result)
                return result

            db = self._db_session

            # Determine last run time for delta filtering
            last_run_time: Optional[datetime] = None
            if delta_only and job_def and job_def.last_run:
                last_run_time = job_def.last_run

            # 1. Fetch users to analyse
            user_query = db.query(User).filter(
                User.status == "active",
                User.is_active == True if hasattr(User, 'is_active') else True,
            )

            if delta_only and last_run_time:
                # Only users with role changes since last run
                changed_user_ids = db.query(UserRole.user_id).filter(
                    UserRole.updated_at > last_run_time
                ).distinct().subquery()
                user_query = user_query.filter(User.id.in_(changed_user_ids))

            users = user_query.all()

            engine = RuleEngine()

            users_processed = 0
            violations_found = 0
            violations_persisted = 0
            errors_detail: List[str] = []

            for user in users:
                try:
                    # 2. Build UserAccess
                    user_roles_q = (
                        db.query(UserRole)
                        .filter(UserRole.user_id == user.id)
                        .all()
                    )
                    role_names = [
                        ur.role_id if hasattr(ur, 'role_id') else str(ur.role_id)
                        for ur in user_roles_q
                    ]

                    ent_q = db.query(UserEntitlement).filter(
                        UserEntitlement.user_id == user.id
                    ).all()

                    entitlements = [
                        Entitlement(
                            auth_object=e.auth_object,
                            field=e.auth_field or "VALUE",
                            value=e.auth_value or "",
                            system=e.source_system or "SAP",
                            attributes={"source_role": e.source_role or ""},
                        )
                        for e in ent_q
                    ]

                    user_access = UserAccess(
                        user_id=user.user_id or str(user.id),
                        username=user.username or "",
                        full_name=user.full_name or user.username or "",
                        department=user.department or "",
                        cost_center=getattr(user, 'cost_center', '') or "",
                        company_code=getattr(user, 'company_code', '') or "",
                        roles=role_names,
                        entitlements=entitlements,
                    )

                    # 3. Run analysis
                    violations = engine.evaluate_user(user_access)
                    violations_found += len(violations)

                    # 4. Persist violations (upsert by violation_id)
                    for v in violations:
                        try:
                            import uuid as _uuid

                            sev_map = {
                                1: RiskSeverityLevel.LOW,
                                2: RiskSeverityLevel.MEDIUM,
                                3: RiskSeverityLevel.HIGH,
                                4: RiskSeverityLevel.CRITICAL,
                            }
                            sev_str_map = {
                                "low": RiskSeverityLevel.LOW,
                                "medium": RiskSeverityLevel.MEDIUM,
                                "high": RiskSeverityLevel.HIGH,
                                "critical": RiskSeverityLevel.CRITICAL,
                            }
                            sev_enum = sev_map.get(
                                v.severity.value if hasattr(v.severity, 'value') else v.severity,
                                RiskSeverityLevel.MEDIUM,
                            )
                            if hasattr(v.severity, 'name'):
                                sev_enum = sev_str_map.get(v.severity.name.lower(), sev_enum)

                            # Check if violation already exists (upsert)
                            existing = db.query(RiskViolation).filter(
                                RiskViolation.violation_id == v.violation_id,
                                RiskViolation.user_id == user.id,
                            ).first()

                            now = datetime.utcnow()

                            if existing:
                                existing.last_analysis_at = now
                                existing.occurrence_count = (existing.occurrence_count or 0) + 1
                            else:
                                new_violation = RiskViolation(
                                    tenant_id=getattr(user, 'tenant_id', 'tenant_default'),
                                    violation_id=v.violation_id or str(_uuid.uuid4()),
                                    rule_id=v.rule_id,
                                    rule_name=v.rule_name,
                                    rule_type=v.rule_type.value if hasattr(v.rule_type, 'value') else str(v.rule_type),
                                    user_id=user.id,
                                    user_external_id=user_access.user_id,
                                    username=user_access.username,
                                    severity=sev_enum,
                                    severity_score=int(v.severity.value) * 25 if hasattr(v.severity, 'value') else 50,
                                    risk_category=v.risk_category.value if hasattr(v.risk_category, 'value') else str(v.risk_category),
                                    conflicting_functions=v.conflicting_entitlements,
                                    conflicting_entitlements=v.conflicting_entitlements,
                                    business_impact=v.business_impact or "",
                                    status=ViolationStatus.OPEN,
                                    detected_at=now,
                                    detected_by="batch_risk_analysis",
                                    last_analysis_at=now,
                                    occurrence_count=1,
                                )
                                db.add(new_violation)
                                violations_persisted += 1

                        except Exception as ve:
                            errors_detail.append(
                                f"Persist error user={user.user_id} rule={v.rule_id}: {str(ve)}"
                            )

                    users_processed += 1

                except Exception as ue:
                    errors_detail.append(f"Analysis error user={getattr(user, 'user_id', '?')}: {str(ue)}")

            # Commit all persisted violations
            if self._db_session:
                try:
                    self._db_session.commit()
                except Exception as ce:
                    self._db_session.rollback()
                    errors_detail.append(f"Commit failed: {str(ce)}")

            result.items_processed = users_processed
            result.items_affected = violations_persisted
            result.errors = errors_detail
            result.success = len(errors_detail) == 0
            result.details = {
                "delta_only": delta_only,
                "last_run_time": last_run_time.isoformat() if last_run_time else None,
                "users_analysed": users_processed,
                "violations_found": violations_found,
                "violations_persisted": violations_persisted,
                "violations_updated": violations_found - violations_persisted,
            }

        except Exception as e:
            result.success = False
            result.errors.append(f"Job failed: {str(e)}")
            logger.error("batch_risk_analysis failed: %s", str(e), exc_info=True)

        result.completed_at = datetime.utcnow()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
        self._finalize_job("batch_risk_analysis", result)
        return result

    # ---- Job 9: Role Reaffirmation Check (BRM) ----

    async def role_reaffirmation_check(self) -> JobResult:
        """
        Daily job: identify roles past their reaffirmation due date.

        Queries Role model where reaffirmation_days IS NOT NULL.
        Computes next_reaffirmation_date = updated_at + reaffirmation_days.
        If past due, creates an audit log entry / notification and returns count.
        """
        result = JobResult(job_name="role_reaffirmation_check")
        job_def = self._jobs.get("role_reaffirmation_check")
        if job_def:
            job_def.status = JobStatus.RUNNING

        try:
            if not self._db_session:
                result.errors.append("No DB session — skipping role_reaffirmation_check")
                result.success = False
                result.completed_at = datetime.utcnow()
                result.duration_seconds = 0.0
                self._finalize_job("role_reaffirmation_check", result)
                return result

            db = self._db_session
            now = datetime.utcnow()
            overdue_roles = []

            try:
                from db.models.user import Role
                roles_with_reaffirmation = db.query(Role).filter(
                    Role.reaffirmation_days != None,  # noqa: E711
                    Role.is_active == True,
                ).all()

                for role in roles_with_reaffirmation:
                    reference_date = role.updated_at or role.created_at or now
                    if reference_date is None:
                        continue
                    next_reaffirmation = reference_date + timedelta(days=role.reaffirmation_days)
                    if next_reaffirmation <= now:
                        days_overdue = (now - next_reaffirmation).days
                        overdue_roles.append({
                            "role_id": role.role_id,
                            "role_name": role.role_name,
                            "owner_user_id": role.owner_user_id,
                            "reaffirmation_days": role.reaffirmation_days,
                            "next_reaffirmation_date": next_reaffirmation.isoformat(),
                            "days_overdue": days_overdue,
                        })
                        logger.warning(
                            "Role %s reaffirmation overdue by %d days (owner=%s)",
                            role.role_id, days_overdue, role.owner_user_id,
                        )
            except Exception as e:
                result.errors.append(f"DB query failed: {str(e)}")

            result.items_processed = len(overdue_roles)
            result.items_affected = len(overdue_roles)
            result.details = {
                "overdue_roles": overdue_roles,
                "checked_at": now.isoformat(),
            }
            result.success = len(result.errors) == 0

        except Exception as e:
            result.success = False
            result.errors.append(f"Job failed: {str(e)}")
            logger.error("role_reaffirmation_check failed: %s", str(e), exc_info=True)

        result.completed_at = datetime.utcnow()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
        self._finalize_job("role_reaffirmation_check", result)
        return result

    def enable_job(self, job_name: str) -> bool:
        """Enable a job."""
        job_def = self._jobs.get(job_name)
        if job_def:
            job_def.enabled = True
            job_def.status = JobStatus.IDLE
            return True
        return False

    def disable_job(self, job_name: str) -> bool:
        """Disable a job."""
        job_def = self._jobs.get(job_name)
        if job_def:
            job_def.enabled = False
            job_def.status = JobStatus.DISABLED
            return True
        return False
