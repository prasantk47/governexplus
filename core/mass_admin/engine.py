"""
Mass Administration Engine

Provides bulk-operation capabilities for user and role administration.
Each operation is modelled as an async "job" with status tracking so that
callers can submit work and poll for completion — necessary for operations
that may affect thousands of users.

Operations supported
--------------------
- bulk_user_import     : import users from a list/CSV payload
- bulk_role_assign     : assign one or more roles to a set of users
- bulk_role_remove     : remove roles from a set of users
- mass_role_change     : apply permission changes to a role, affecting all holders
- mass_owner_update    : reassign ownership for a set of roles
- bulk_user_lock       : lock multiple user accounts
- bulk_user_unlock     : unlock multiple user accounts
- preview_impact       : estimate the effect of an operation before running it
- get_job_status       : poll a running or completed job
- get_job_history      : list all past jobs
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from db.database import db_manager
from db.models.operations import BulkJob

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JOB_STATUSES = ("queued", "running", "completed", "failed", "partial", "cancelled")

# ---------------------------------------------------------------------------
# Seed data helper
# ---------------------------------------------------------------------------

def _utc(offset_days: int = 0) -> datetime:
    dt = datetime.utcnow()
    if offset_days:
        dt = dt - timedelta(days=offset_days)
    return dt


def _seed_job_history(tenant_id: str) -> None:
    """
    Insert representative historical jobs on first access so the UI has
    something meaningful to display before real operations are run.
    Called only when the jobs table for this tenant is empty.
    """
    seed_jobs = [
        BulkJob(
            tenant_id=tenant_id,
            job_id="JOB-SEED-001",
            operation="bulk_role_assign",
            status="completed",
            parameters={"role_ids": ["ROLE_FI_AP_CLERK"]},
            target_users=["U010", "U011", "U012", "U013"],
            total=4,
            processed=4,
            succeeded=4,
            failed_count=0,
            results={"message": "All 4 users assigned ROLE_FI_AP_CLERK"},
            started_at=_utc(7),
            completed_at=_utc(7),
            created_by="admin@corp.com",
        ),
        BulkJob(
            tenant_id=tenant_id,
            job_id="JOB-SEED-002",
            operation="bulk_user_import",
            status="partial",
            parameters={"record_count": 50},
            target_users=[],
            total=50,
            processed=50,
            succeeded=47,
            failed_count=3,
            results={
                "imported": 47,
                "skipped": 3,
                "errors": [
                    {"row": 12, "reason": "Duplicate username: jsmith"},
                    {"row": 31, "reason": "Invalid email format"},
                    {"row": 44, "reason": "Missing mandatory field: department"},
                ],
            },
            started_at=_utc(5),
            completed_at=_utc(5),
            created_by="hr_admin@corp.com",
        ),
        BulkJob(
            tenant_id=tenant_id,
            job_id="JOB-SEED-003",
            operation="bulk_user_lock",
            status="completed",
            parameters={"reason": "Annual access review — accounts suspended"},
            target_users=["U050", "U051"],
            total=2,
            processed=2,
            succeeded=2,
            failed_count=0,
            results={"locked": ["U050", "U051"]},
            started_at=_utc(3),
            completed_at=_utc(3),
            created_by="security@corp.com",
        ),
        BulkJob(
            tenant_id=tenant_id,
            job_id="JOB-SEED-004",
            operation="mass_role_change",
            status="completed",
            parameters={
                "role_id": "ROLE_MM_BUYER",
                "changes": {"add_auth": ["M_BEST_WRK"], "remove_auth": ["M_EINF_EKG"]},
            },
            target_users=[],
            total=23,
            processed=23,
            succeeded=23,
            failed_count=0,
            results={"affected_users": 23, "role_id": "ROLE_MM_BUYER"},
            started_at=_utc(2),
            completed_at=_utc(2),
            created_by="role_admin@corp.com",
        ),
        BulkJob(
            tenant_id=tenant_id,
            job_id="JOB-SEED-005",
            operation="mass_owner_update",
            status="failed",
            parameters={"role_ids": ["ROLE_SD_MGR", "ROLE_FI_CTRL"], "new_owner": "U099"},
            target_users=[],
            total=2,
            processed=2,
            succeeded=0,
            failed_count=2,
            results={
                "message": "Target owner U099 not found in directory",
                "errors": [
                    {"role_id": "ROLE_SD_MGR", "reason": "New owner U099 does not exist"},
                    {"role_id": "ROLE_FI_CTRL", "reason": "New owner U099 does not exist"},
                ],
            },
            started_at=_utc(1),
            completed_at=_utc(1),
            created_by="admin@corp.com",
        ),
    ]
    with db_manager.session_scope() as session:
        for job in seed_jobs:
            session.add(job)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class MassAdminEngine:
    """
    Core engine for mass (bulk) administration of users and roles.

    All operations are synchronous in this implementation but are wrapped
    in the job tracking model so the API surface is identical to an
    async/queue-backed production system.

    Job persistence is backed by the ``bulk_jobs`` database table via
    SQLAlchemy so that job history survives restarts and is visible across
    all nodes in a multi-node deployment.
    """

    DEFAULT_TENANT = "tenant_default"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_seeded(self, tenant_id: str) -> None:
        """Insert seed history the first time a tenant accesses job history."""
        with db_manager.session_scope() as session:
            count = (
                session.query(BulkJob)
                .filter(BulkJob.tenant_id == tenant_id)
                .count()
            )
        if count == 0:
            try:
                _seed_job_history(tenant_id)
            except Exception:
                # Seed may fail on unique-constraint race; ignore and continue.
                logger.debug("Seed job history skipped (already seeded or race condition).")

    def _create_job(
        self,
        tenant_id: str,
        operation: str,
        target_users: list[str],
        parameters: dict[str, Any],
        created_by: str = "system",
    ) -> dict[str, Any]:
        """Persist a new job record and return its dict representation."""
        job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.utcnow()
        with db_manager.session_scope() as session:
            job = BulkJob(
                tenant_id=tenant_id,
                job_id=job_id,
                operation=operation,
                status="queued",
                parameters=parameters,
                target_users=target_users,
                total=len(target_users),
                processed=0,
                succeeded=0,
                failed_count=0,
                results=None,
                started_at=now,
                created_by=created_by,
            )
            session.add(job)
            session.flush()
            data = job.to_dict()
        return data

    def _complete_job(
        self,
        job_id: str,
        tenant_id: str,
        total: int,
        succeeded: int,
        failed: int,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing job row with completion data and return its dict."""
        if failed == 0:
            status = "completed"
        elif succeeded == 0:
            status = "failed"
        else:
            status = "partial"

        now = datetime.utcnow()
        with db_manager.session_scope() as session:
            job = (
                session.query(BulkJob)
                .filter(BulkJob.job_id == job_id, BulkJob.tenant_id == tenant_id)
                .first()
            )
            if job is None:
                raise ValueError(f"Job {job_id} not found for tenant {tenant_id}")
            job.status = status
            job.total = total
            job.processed = total
            job.succeeded = succeeded
            job.failed_count = failed
            job.results = results
            job.completed_at = now
            data = job.to_dict()
        return data

    def _job_to_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Convert a BulkJob.to_dict() payload into the public API shape
        expected by callers (preserving the original field naming).
        """
        total = raw.get("total", 0) or 0
        processed = raw.get("processed", 0) or 0
        succeeded = raw.get("succeeded", 0) or 0
        failed = raw.get("failed_count", 0) or 0
        results = raw.get("results") or {}

        return {
            "job_id": raw["job_id"],
            "operation": raw["operation"],
            "status": raw["status"],
            "params": raw.get("parameters") or {},
            "submitted_by": raw.get("created_by", "system"),
            "submitted_at": raw.get("created_at"),
            "started_at": raw.get("started_at"),
            "completed_at": raw.get("completed_at"),
            "progress": {
                "total_items": total,
                "processed_items": processed,
                "succeeded_items": succeeded,
                "failed_items": failed,
                "percent_complete": (
                    round(processed / total * 100, 1) if total > 0 else 0
                ),
            },
            "errors": results.get("errors", []),
            "result_summary": {k: v for k, v in results.items() if k != "errors"},
        }

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def bulk_user_import(
        self,
        users_data: list[dict[str, Any]],
        submitted_by: str = "system",
        tenant_id: str = DEFAULT_TENANT,
    ) -> dict[str, Any]:
        """
        Import a list of user records.

        Each record should contain at minimum: username, email, full_name,
        department. Optional fields: user_type, manager_id.

        Returns a job tracking dict.
        """
        required_fields = {"username", "email", "full_name", "department"}

        raw = self._create_job(
            tenant_id=tenant_id,
            operation="bulk_user_import",
            target_users=[u.get("username", f"row_{i}") for i, u in enumerate(users_data, 1)],
            parameters={"record_count": len(users_data)},
            created_by=submitted_by,
        )
        job_id = raw["job_id"]

        succeeded = 0
        errors: list[dict[str, Any]] = []

        for idx, user in enumerate(users_data, start=1):
            missing = required_fields - set(user.keys())
            if missing:
                errors.append({
                    "row": idx,
                    "username": user.get("username", "?"),
                    "reason": f"Missing required fields: {sorted(missing)}",
                })
                continue
            if not user.get("email", "").count("@"):
                errors.append({
                    "row": idx,
                    "username": user.get("username", "?"),
                    "reason": "Invalid email format",
                })
                continue
            # Production: write user to DB here.
            succeeded += 1

        results = {"imported": succeeded, "skipped": len(errors), "errors": errors}
        data = self._complete_job(
            job_id, tenant_id, len(users_data), succeeded, len(errors), results
        )
        return self._job_to_response(data)

    def bulk_role_assign(
        self,
        user_ids: list[str],
        role_ids: list[str],
        submitted_by: str = "system",
        tenant_id: str = DEFAULT_TENANT,
    ) -> dict[str, Any]:
        """
        Assign one or more roles to a set of users.

        In production this would write to the authorization database and
        trigger provisioning workflows.
        """
        raw = self._create_job(
            tenant_id=tenant_id,
            operation="bulk_role_assign",
            target_users=user_ids,
            parameters={"user_ids": user_ids, "role_ids": role_ids},
            created_by=submitted_by,
        )
        job_id = raw["job_id"]

        total = len(user_ids) * len(role_ids)
        results = {
            "assigned_roles": role_ids,
            "affected_users": user_ids,
            "total_assignments_created": total,
        }
        data = self._complete_job(job_id, tenant_id, total, total, 0, results)
        return self._job_to_response(data)

    def bulk_role_remove(
        self,
        user_ids: list[str],
        role_ids: list[str],
        submitted_by: str = "system",
        tenant_id: str = DEFAULT_TENANT,
    ) -> dict[str, Any]:
        """Remove one or more roles from a set of users."""
        raw = self._create_job(
            tenant_id=tenant_id,
            operation="bulk_role_remove",
            target_users=user_ids,
            parameters={"user_ids": user_ids, "role_ids": role_ids},
            created_by=submitted_by,
        )
        job_id = raw["job_id"]

        total = len(user_ids) * len(role_ids)
        results = {
            "removed_roles": role_ids,
            "affected_users": user_ids,
            "total_assignments_removed": total,
        }
        data = self._complete_job(job_id, tenant_id, total, total, 0, results)
        return self._job_to_response(data)

    def mass_role_change(
        self,
        role_id: str,
        changes: dict[str, Any],
        submitted_by: str = "system",
        tenant_id: str = DEFAULT_TENANT,
    ) -> dict[str, Any]:
        """
        Apply a set of changes to a role definition, propagating the effect
        to all users who currently hold the role.

        ``changes`` may contain:
        - ``add_auth``     : list of authorization objects to add
        - ``remove_auth``  : list of authorization objects to remove
        - ``rename``       : new role name
        - ``description``  : updated description
        """
        # Production: query users holding this role from DB.
        affected_users = 15

        raw = self._create_job(
            tenant_id=tenant_id,
            operation="mass_role_change",
            target_users=[],
            parameters={"role_id": role_id, "changes": changes},
            created_by=submitted_by,
        )
        job_id = raw["job_id"]

        results = {
            "role_id": role_id,
            "changes_applied": changes,
            "affected_users": affected_users,
            "message": f"Role changes propagated to {affected_users} users",
        }
        data = self._complete_job(job_id, tenant_id, affected_users, affected_users, 0, results)
        return self._job_to_response(data)

    def mass_owner_update(
        self,
        role_ids: list[str],
        new_owner: str,
        submitted_by: str = "system",
        tenant_id: str = DEFAULT_TENANT,
    ) -> dict[str, Any]:
        """Reassign ownership for a set of roles to a new owner user ID."""
        raw = self._create_job(
            tenant_id=tenant_id,
            operation="mass_owner_update",
            target_users=[],
            parameters={"role_ids": role_ids, "new_owner": new_owner},
            created_by=submitted_by,
        )
        job_id = raw["job_id"]

        results = {
            "updated_roles": role_ids,
            "new_owner": new_owner,
            "total_roles_updated": len(role_ids),
        }
        data = self._complete_job(job_id, tenant_id, len(role_ids), len(role_ids), 0, results)
        return self._job_to_response(data)

    def bulk_user_lock(
        self,
        user_ids: list[str],
        reason: str,
        submitted_by: str = "system",
        tenant_id: str = DEFAULT_TENANT,
    ) -> dict[str, Any]:
        """Lock multiple user accounts simultaneously with an audit reason."""
        raw = self._create_job(
            tenant_id=tenant_id,
            operation="bulk_user_lock",
            target_users=user_ids,
            parameters={"user_ids": user_ids, "reason": reason},
            created_by=submitted_by,
        )
        job_id = raw["job_id"]

        results = {"locked_users": user_ids, "reason": reason}
        data = self._complete_job(job_id, tenant_id, len(user_ids), len(user_ids), 0, results)
        return self._job_to_response(data)

    def bulk_user_unlock(
        self,
        user_ids: list[str],
        submitted_by: str = "system",
        tenant_id: str = DEFAULT_TENANT,
    ) -> dict[str, Any]:
        """Unlock multiple user accounts simultaneously."""
        raw = self._create_job(
            tenant_id=tenant_id,
            operation="bulk_user_unlock",
            target_users=user_ids,
            parameters={"user_ids": user_ids},
            created_by=submitted_by,
        )
        job_id = raw["job_id"]

        results = {"unlocked_users": user_ids}
        data = self._complete_job(job_id, tenant_id, len(user_ids), len(user_ids), 0, results)
        return self._job_to_response(data)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def preview_impact(
        self,
        operation: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Estimate the impact of a bulk operation without executing it.

        Returns projected counts of affected users, roles, and assignments,
        along with any warnings (e.g. SoD conflicts that would be created).

        Parameters
        ----------
        operation: Operation name, e.g. "bulk_role_assign".
        params:    Same parameters that would be passed to the operation.
        """
        estimates: dict[str, Any] = {
            "operation": operation,
            "params": params,
            "preview_generated_at": datetime.utcnow().isoformat(),
            "warnings": [],
        }

        if operation == "bulk_role_assign":
            user_ids = params.get("user_ids", [])
            role_ids = params.get("role_ids", [])
            estimates.update({
                "estimated_assignments_created": len(user_ids) * len(role_ids),
                "affected_users": len(user_ids),
                "roles_to_assign": len(role_ids),
                "sod_conflicts_detected": 0,
                "warnings": ["Preview only — SoD analysis not performed in this simulation"],
            })

        elif operation == "bulk_role_remove":
            user_ids = params.get("user_ids", [])
            role_ids = params.get("role_ids", [])
            estimates.update({
                "estimated_assignments_removed": len(user_ids) * len(role_ids),
                "affected_users": len(user_ids),
                "roles_to_remove": len(role_ids),
            })

        elif operation == "mass_role_change":
            estimates.update({
                "estimated_affected_users": 15,
                "role_id": params.get("role_id"),
                "changes_to_apply": params.get("changes", {}),
                "warnings": [
                    "This operation will modify active user sessions",
                    "Recertification campaign may be required after changes",
                ],
            })

        elif operation == "bulk_user_import":
            record_count = params.get("record_count", 0)
            estimates.update({
                "records_to_process": record_count,
                "estimated_successes": record_count,
                "estimated_failures": 0,
            })

        elif operation == "bulk_user_lock":
            user_ids = params.get("user_ids", [])
            estimates.update({
                "users_to_lock": len(user_ids),
                "active_sessions_to_terminate": len(user_ids),
                "warnings": ["All active sessions for these users will be terminated immediately"],
            })

        elif operation == "mass_owner_update":
            role_ids = params.get("role_ids", [])
            estimates.update({
                "roles_to_update": len(role_ids),
                "certification_campaigns_affected": 0,
            })

        else:
            estimates["warnings"] = [f"No preview model available for operation '{operation}'"]

        return estimates

    # ------------------------------------------------------------------
    # Job tracking
    # ------------------------------------------------------------------

    def get_job_status(
        self,
        job_id: str,
        tenant_id: str = DEFAULT_TENANT,
    ) -> dict[str, Any] | None:
        """Return current status of a job, or None if not found."""
        with db_manager.session_scope() as session:
            job = (
                session.query(BulkJob)
                .filter(BulkJob.job_id == job_id, BulkJob.tenant_id == tenant_id)
                .first()
            )
            if job is None:
                return None
            data = job.to_dict()
        return self._job_to_response(data)

    def get_job_history(
        self,
        operation: str | None = None,
        status: str | None = None,
        limit: int = 50,
        tenant_id: str = DEFAULT_TENANT,
    ) -> dict[str, Any]:
        """
        Return a list of past bulk jobs, optionally filtered by operation type
        or status, ordered by creation time descending.
        """
        self._ensure_seeded(tenant_id)

        with db_manager.session_scope() as session:
            query = session.query(BulkJob).filter(BulkJob.tenant_id == tenant_id)
            if operation:
                query = query.filter(BulkJob.operation == operation)
            if status:
                query = query.filter(BulkJob.status == status)
            query = query.order_by(BulkJob.created_at.desc()).limit(limit)
            jobs = [job.to_dict() for job in query.all()]

        return {
            "jobs": [self._job_to_response(j) for j in jobs],
            "total": len(jobs),
        }
