"""
Document Retention + Legal Hold API Router (NF-05)

All endpoints operate within the caller's tenant scope (resolved via the
standard tenant middleware / context-var).

Endpoints
---------
GET  /retention/policies                   — effective retention policies
POST /retention/policies                   — set/update a retention policy
POST /retention/apply                      — run the retention batch job
PUT  /retention/legal-hold/{evidence_id}   — toggle legal hold
GET  /retention/report                     — retention status report
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from db.database import get_db
from core.retention import RetentionManager

router = APIRouter(tags=["Document Retention & Legal Hold"])


# ---------------------------------------------------------------------------
# Tenant helper — same pattern used across process_ctrl, risk_mgmt, etc.
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


# ---------------------------------------------------------------------------
# Manager factory — per-request, re-uses the open DB session
# ---------------------------------------------------------------------------

def _get_manager(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
) -> RetentionManager:
    return RetentionManager(tenant_id=tenant_id, db_session=db)


# ===========================================================================
# Policy endpoints
# ===========================================================================

@router.get("/policies")
def get_policies(
    manager: RetentionManager = Depends(_get_manager),
):
    """
    Return the current effective retention policies for this tenant.

    Policies list platform defaults merged with any tenant-specific overrides
    that were set via ``POST /retention/policies``.
    """
    return manager.get_policies()


@router.post("/policies")
def set_retention_policy(
    body: Dict[str, Any] = Body(default={}),
    manager: RetentionManager = Depends(_get_manager),
):
    """
    Set or update the retention period for a document object_type.

    Body
    ----
    object_type : str
        Evidence type (``document``, ``screenshot``, ``system_extract``,
        ``attestation``, ``export``) or source module code
        (``pc``, ``rm``, ``am``, ``ac``).
    retention_days : int
        Days to retain documents of this type after their upload_date.
        Minimum 1.

    Example
    -------
    ```json
    {"object_type": "attestation", "retention_days": 3650}
    ```
    """
    object_type = body.get("object_type", "").strip()
    retention_days = body.get("retention_days")

    if not object_type:
        raise HTTPException(status_code=400, detail="'object_type' is required")
    if retention_days is None:
        raise HTTPException(status_code=400, detail="'retention_days' is required")
    try:
        retention_days = int(retention_days)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="'retention_days' must be an integer")

    try:
        return manager.set_retention_policy(object_type, retention_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ===========================================================================
# Batch apply
# ===========================================================================

def _run_retention_async(tenant_id: str, db: Session) -> None:
    """Background task wrapper — separate manager so it can commit independently."""
    try:
        m = RetentionManager(tenant_id=tenant_id, db_session=db)
        result = m.apply_retention()
        import logging
        logging.getLogger(__name__).info("retention.batch_complete", extra=result)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "retention.batch_error",
            exc_info=True,
            extra={"tenant_id": tenant_id, "error": str(exc)},
        )


@router.post("/apply")
def apply_retention(
    background_tasks: BackgroundTasks,
    body: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
    manager: RetentionManager = Depends(_get_manager),
):
    """
    Trigger the document retention batch job.

    By default the job runs synchronously and returns a result summary.
    Pass ``{"async": true}`` in the body to queue it as a background task
    (returns immediately with ``{"status": "queued"}``).

    The batch job:
      1. Stamps ``retention_until`` on any evidence record that lacks it.
      2. Archives (status → ARCHIVED) all active records whose
         ``retention_until`` has passed AND whose ``legal_hold`` is False.
    """
    body = body or {}
    run_async = body.get("async", False)

    if run_async:
        background_tasks.add_task(_run_retention_async, tenant_id, db)
        return {"status": "queued", "tenant_id": tenant_id}

    # Synchronous run
    try:
        result = manager.apply_retention()
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retention job failed: {exc}")


# ===========================================================================
# Legal hold
# ===========================================================================

@router.put("/legal-hold/{evidence_id}")
def set_legal_hold(
    evidence_id: str,
    body: Dict[str, Any] = Body(default={}),
    manager: RetentionManager = Depends(_get_manager),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Place or release a legal hold on an evidence record.

    A legal hold prevents the retention job from archiving the document
    even after its retention_until date has passed.

    Body
    ----
    hold : bool
        ``true`` to place a hold; ``false`` to release.
    reason : str
        Mandatory reason string — recorded in the audit log.
    applied_by : str, optional
        User ID of the person applying / releasing the hold.

    Example
    -------
    ```json
    {
        "hold": true,
        "reason": "Litigation hold — case #2026-FR-0042",
        "applied_by": "user_admin_001"
    }
    ```
    """
    hold = body.get("hold")
    reason = body.get("reason", "").strip()
    applied_by: Optional[str] = body.get("applied_by")

    if hold is None:
        raise HTTPException(status_code=400, detail="'hold' (bool) is required")
    if not isinstance(hold, bool):
        raise HTTPException(status_code=400, detail="'hold' must be a boolean (true/false)")
    if not reason:
        raise HTTPException(
            status_code=400,
            detail="'reason' is required and must not be empty",
        )

    try:
        return manager.set_legal_hold(
            evidence_id=evidence_id,
            hold=hold,
            reason=reason,
            applied_by=applied_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ===========================================================================
# Report
# ===========================================================================

@router.get("/report")
def get_retention_report(
    manager: RetentionManager = Depends(_get_manager),
):
    """
    Return a full retention status report for this tenant.

    Report sections
    ---------------
    summary          — aggregate counts (total, active, archived, legal holds,
                       expiring soon, overdue)
    expiring_soon    — evidence expiring within the next 90 days (not on hold)
    overdue          — active evidence past its retention_until (awaiting batch)
    legal_holds      — all evidence currently under legal hold
    """
    return manager.get_retention_report()
