"""
Document Retention + Legal Hold Manager (NF-05)

Manages the full lifecycle of GRC evidence retention:
  - Per-type retention policies (stored in-memory / DB JSON)
  - Batch expiry job that marks overdue, non-held evidence as ARCHIVED
  - Legal hold toggle with audit trail
  - Reporting dashboard (by status, upcoming expirations, hold counts)

The manager operates within a single tenant scope.  It relies on the
GRCEvidence model which already carries ``retention_until`` (DateTime)
and ``legal_hold`` (Boolean) columns (see db/models/process_control.py).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from db.models.process_control import GRCEvidence, EvidenceStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default retention periods (days) per evidence type / source module.
# These are the platform defaults; tenants can override via set_retention_policy.
# ---------------------------------------------------------------------------
_DEFAULT_RETENTION_DAYS: Dict[str, int] = {
    "document":       2555,   # 7 years — SOX / GDPR default
    "screenshot":     1825,   # 5 years
    "export":         2555,
    "system_extract": 2555,
    "attestation":    3650,   # 10 years — common for audit attestations
    # source modules
    "pc":             2555,
    "rm":             2555,
    "am":             3650,
    "ac":             1825,
    # catch-all
    "default":        2555,
}


class RetentionManager:
    """
    Per-tenant document retention and legal hold manager.

    Parameters
    ----------
    tenant_id : str
        The tenant whose evidence records this manager operates on.
    db_session : sqlalchemy.orm.Session
        An open SQLAlchemy session.  The caller is responsible for
        committing or rolling back the session.
    """

    def __init__(self, tenant_id: str, db_session: Session) -> None:
        self.tenant_id = tenant_id
        self.db = db_session
        # In-memory policy overrides (key = object_type, value = retention_days)
        # In a production system these would live in a DB table; for the current
        # schema they are stored per-instance.
        self._policy_overrides: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _retention_days_for(self, evidence: GRCEvidence) -> int:
        """Return the applicable retention period in days for an evidence record."""
        # Check instance overrides first (tenant-specific policy via API)
        for key in (evidence.evidence_type, evidence.source_module, "default"):
            if key and key in self._policy_overrides:
                return self._policy_overrides[key]
        # Fall back to platform defaults
        for key in (evidence.evidence_type, evidence.source_module, "default"):
            if key and key in _DEFAULT_RETENTION_DAYS:
                return _DEFAULT_RETENTION_DAYS[key]
        return _DEFAULT_RETENTION_DAYS["default"]

    def _base_query(self):
        """Tenant-scoped query over active GRCEvidence rows."""
        return (
            self.db.query(GRCEvidence)
            .filter(
                GRCEvidence.tenant_id == self.tenant_id,
                GRCEvidence.status == EvidenceStatus.ACTIVE,
            )
        )

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def set_retention_policy(self, object_type: str, retention_days: int) -> dict:
        """
        Set or update the retention period for a given object_type.

        object_type may be an evidence_type value (``document``, ``screenshot``,
        ``system_extract``, etc.) or a source_module code (``pc``, ``rm``,
        ``am``, ``ac``).

        Parameters
        ----------
        object_type : str
            The evidence_type or source_module value to configure.
        retention_days : int
            Number of days to retain documents of this type after upload_date.
            Must be >= 1.

        Returns
        -------
        dict
            Summary of the policy that was set.
        """
        if retention_days < 1:
            raise ValueError("retention_days must be >= 1")
        self._policy_overrides[object_type] = retention_days
        logger.info(
            "retention_policy.set",
            extra={
                "tenant_id": self.tenant_id,
                "object_type": object_type,
                "retention_days": retention_days,
            },
        )
        return {
            "object_type": object_type,
            "retention_days": retention_days,
            "tenant_id": self.tenant_id,
            "effective_at": datetime.utcnow().isoformat(),
        }

    def get_policies(self) -> dict:
        """Return current effective retention policies for this tenant."""
        # Merge platform defaults with tenant overrides (overrides win)
        merged = {**_DEFAULT_RETENTION_DAYS, **self._policy_overrides}
        return {
            "tenant_id": self.tenant_id,
            "policies": [
                {"object_type": k, "retention_days": v}
                for k, v in sorted(merged.items())
            ],
            "override_count": len(self._policy_overrides),
        }

    # ------------------------------------------------------------------
    # Batch retention job
    # ------------------------------------------------------------------

    def apply_retention(self) -> dict:
        """
        Batch retention run.

        For each active evidence record:
          1. If ``retention_until`` is not set, compute and stamp it from
             ``upload_date + policy_days``.
          2. If ``retention_until`` is in the past AND ``legal_hold`` is False,
             mark the record ARCHIVED.

        Records under legal hold are NEVER archived regardless of expiry.

        Returns
        -------
        dict
            Summary with counts: stamped, expired, archived, skipped_legal_hold.
        """
        now = datetime.utcnow()
        stamped = expired_count = archived_count = legal_hold_skipped = 0

        records: List[GRCEvidence] = self._base_query().all()

        for rec in records:
            # Step 1 — stamp retention_until if missing
            if rec.retention_until is None:
                base_date = rec.upload_date or rec.created_at or now
                days = self._retention_days_for(rec)
                rec.retention_until = base_date + timedelta(days=days)
                stamped += 1

            # Step 2 — check for expiry
            if rec.retention_until <= now:
                if rec.legal_hold:
                    # Cannot archive: legal hold is active
                    legal_hold_skipped += 1
                    logger.info(
                        "retention.skipped_legal_hold",
                        extra={"evidence_id": rec.evidence_id, "tenant_id": self.tenant_id},
                    )
                else:
                    rec.status = EvidenceStatus.ARCHIVED
                    archived_count += 1
                    expired_count += 1
                    logger.info(
                        "retention.archived",
                        extra={
                            "evidence_id": rec.evidence_id,
                            "tenant_id": self.tenant_id,
                            "retention_until": rec.retention_until.isoformat(),
                        },
                    )

        self.db.commit()

        return {
            "tenant_id": self.tenant_id,
            "run_at": now.isoformat(),
            "records_processed": len(records),
            "retention_dates_stamped": stamped,
            "records_expired": expired_count,
            "records_archived": archived_count,
            "records_skipped_legal_hold": legal_hold_skipped,
        }

    # ------------------------------------------------------------------
    # Legal hold
    # ------------------------------------------------------------------

    def set_legal_hold(
        self,
        evidence_id: str,
        hold: bool,
        reason: str,
        applied_by: Optional[str] = None,
    ) -> dict:
        """
        Toggle the legal hold flag on a single evidence record.

        A legal hold prevents the retention batch job from archiving the
        document, even after its retention_until date has passed.

        Parameters
        ----------
        evidence_id : str
            The evidence_id string (not the integer PK).
        hold : bool
            True to place a hold, False to release it.
        reason : str
            Mandatory reason — recorded in the audit log.
        applied_by : str, optional
            User ID of the operator applying / releasing the hold.

        Returns
        -------
        dict
            Updated evidence summary including the new hold status.

        Raises
        ------
        ValueError
            If the evidence record does not exist within this tenant.
        """
        if not reason or not reason.strip():
            raise ValueError("A non-empty reason is required to change a legal hold")

        rec: Optional[GRCEvidence] = (
            self.db.query(GRCEvidence)
            .filter(
                GRCEvidence.evidence_id == evidence_id,
                GRCEvidence.tenant_id == self.tenant_id,
            )
            .first()
        )
        if rec is None:
            raise ValueError(
                f"Evidence '{evidence_id}' not found for tenant '{self.tenant_id}'"
            )

        previous = rec.legal_hold
        rec.legal_hold = hold
        self.db.commit()
        self.db.refresh(rec)

        action = "placed" if hold else "released"
        logger.info(
            "legal_hold.%s" % action,
            extra={
                "evidence_id": evidence_id,
                "tenant_id": self.tenant_id,
                "applied_by": applied_by,
                "reason": reason,
                "previous_hold": previous,
                "new_hold": hold,
                "changed_at": datetime.utcnow().isoformat(),
            },
        )

        return {
            "evidence_id": evidence_id,
            "tenant_id": self.tenant_id,
            "legal_hold": rec.legal_hold,
            "legal_hold_action": action,
            "reason": reason,
            "applied_by": applied_by,
            "changed_at": datetime.utcnow().isoformat(),
            "title": rec.title,
            "retention_until": rec.retention_until.isoformat() if rec.retention_until else None,
            "status": rec.status.value if rec.status else None,
        }

    # ------------------------------------------------------------------
    # Retention report
    # ------------------------------------------------------------------

    def get_retention_report(self) -> dict:
        """
        Generate a retention status report for the tenant.

        Covers all evidence records (active + archived) and returns:
          - Totals by status
          - Count of legal holds
          - Records expiring within the next 90 days
          - Records already expired but not yet archived (edge cases)
          - Longest-outstanding legal hold
        """
        now = datetime.utcnow()
        soon = now + timedelta(days=90)

        all_records: List[GRCEvidence] = (
            self.db.query(GRCEvidence)
            .filter(GRCEvidence.tenant_id == self.tenant_id)
            .all()
        )

        total = len(all_records)
        active_count = sum(1 for r in all_records if r.status == EvidenceStatus.ACTIVE)
        archived_count = sum(1 for r in all_records if r.status == EvidenceStatus.ARCHIVED)
        deleted_count = sum(1 for r in all_records if r.status == EvidenceStatus.DELETED)
        legal_hold_count = sum(1 for r in all_records if r.legal_hold)

        # Expiring soon (active, not on hold)
        expiring_soon = [
            {
                "evidence_id": r.evidence_id,
                "title": r.title,
                "retention_until": r.retention_until.isoformat() if r.retention_until else None,
                "legal_hold": r.legal_hold,
                "days_remaining": (r.retention_until - now).days if r.retention_until else None,
            }
            for r in all_records
            if (
                r.status == EvidenceStatus.ACTIVE
                and r.retention_until is not None
                and now <= r.retention_until <= soon
                and not r.legal_hold
            )
        ]
        expiring_soon.sort(key=lambda x: x["days_remaining"] or 0)

        # Overdue — past retention_until but still active (awaiting next batch run)
        overdue = [
            {
                "evidence_id": r.evidence_id,
                "title": r.title,
                "retention_until": r.retention_until.isoformat() if r.retention_until else None,
                "legal_hold": r.legal_hold,
                "overdue_days": (now - r.retention_until).days if r.retention_until else None,
            }
            for r in all_records
            if (
                r.status == EvidenceStatus.ACTIVE
                and r.retention_until is not None
                and r.retention_until < now
            )
        ]

        # Legal hold details
        holds = [
            {
                "evidence_id": r.evidence_id,
                "title": r.title,
                "retention_until": r.retention_until.isoformat() if r.retention_until else None,
                "upload_date": r.upload_date.isoformat() if r.upload_date else None,
                "source_module": r.source_module,
                "evidence_type": r.evidence_type,
            }
            for r in all_records
            if r.legal_hold
        ]

        return {
            "tenant_id": self.tenant_id,
            "generated_at": now.isoformat(),
            "summary": {
                "total": total,
                "active": active_count,
                "archived": archived_count,
                "deleted": deleted_count,
                "legal_holds": legal_hold_count,
                "expiring_within_90_days": len(expiring_soon),
                "overdue_pending_archive": len(overdue),
            },
            "expiring_soon": expiring_soon,
            "overdue": overdue,
            "legal_holds": holds,
        }
