"""
Access Troubleshooter API Router

Provides the REST interface for the GovernexPlus Access Troubleshooter module —
the AI-powered diagnostic engine that answers:

    "Why can't user X execute transaction Y in system Z?"

This is a key differentiator of GovernexPlus over legacy GRC tools: instead of
telling administrators that a violation exists, it tells them exactly where the
chain broke, why, and what to do about it.

Endpoints
---------
POST /diagnose
    Run a full diagnostic chain for one user + transaction + system.

GET /transactions
    List all transactions in the GovernexPlus knowledge base.

GET /transactions/{tcode}/requirements
    Return the full authorization requirements for a single tcode.

GET /common-issues
    Return the curated list of top SAP access failure patterns.

POST /batch-diagnose
    Diagnose multiple users against the same transaction and system.

GET /history
    Return recent diagnosis history with optional filters.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.troubleshooter import (
    AccessTroubleshooter,
    TroubleshootRequest,
    get_common_issues,
    get_diagnosis_history,
    get_transaction_list,
    get_transaction_requirements,
)

router = APIRouter(tags=["Access Troubleshooter"])

# Module-level engine instance.  The engine is stateless with respect to the
# request being processed, so a single shared instance is safe under concurrent
# requests.
_engine = AccessTroubleshooter()


# ---------------------------------------------------------------------------
# Request / Response Pydantic models
# ---------------------------------------------------------------------------

class DiagnoseRequest(BaseModel):
    """Request body for a single-user diagnosis."""

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=12,
        description="SAP user logon name (max 12 chars, case-insensitive).",
        examples=["JDOE"],
    )
    transaction: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description=(
            "SAP transaction code (e.g. 'FB01') or Fiori app ID (e.g. 'F0718').  "
            "Case-insensitive."
        ),
        examples=["FB01"],
    )
    system: str = Field(
        ...,
        min_length=2,
        max_length=8,
        description="Target system SID or name (e.g. 'PRD', 'S4H_PROD').",
        examples=["PRD"],
    )
    tenant_id: str = Field(
        default="tenant_default",
        description="GovernexPlus tenant identifier.",
    )
    requested_by: str = Field(
        default="api_user",
        description="User ID of the analyst triggering the diagnosis.",
    )
    context: Optional[str] = Field(
        default=None,
        max_length=500,
        description=(
            "Optional free-form context: incident ticket number, business justification, etc."
        ),
    )


class BatchDiagnoseRequest(BaseModel):
    """Request body for diagnosing multiple users against one transaction."""

    user_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of SAP user logon names (max 50 per batch).",
        examples=[["JDOE", "SSMITH", "BWILSON"]],
    )
    transaction: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Transaction code or Fiori app ID to diagnose for all users.",
        examples=["FB01"],
    )
    system: str = Field(
        ...,
        min_length=2,
        max_length=8,
        description="Target system SID.",
        examples=["PRD"],
    )
    tenant_id: str = Field(default="tenant_default")
    requested_by: str = Field(default="api_user")


class BatchDiagnoseResponse(BaseModel):
    """Response envelope for a batch diagnosis run."""

    total_users: int
    transaction: str
    system: str
    results: List[Dict[str, Any]]
    summary: Dict[str, int] = Field(
        description=(
            "Count of results grouped by status: access_granted, access_denied, "
            "partial_access."
        )
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/diagnose",
    summary="Run Full Access Diagnosis",
    response_description=(
        "Structured diagnosis result with root cause, all check steps, "
        "recommended fix, and risk impact."
    ),
)
async def diagnose(body: DiagnoseRequest) -> Dict[str, Any]:
    """
    Run a full AI-powered diagnostic chain for a user, transaction, and system.

    The engine checks, in order:

    1. User account existence
    2. Account lock / inactive status
    3. User validity dates (Valid From / Valid To)
    4. Whether any roles are assigned at all
    5. Whether the transaction is known in the GovernexPlus KB
    6. Whether any assigned role contains the transaction
    7. Authorization objects — presence and field values
    8. Organizational level values (company code, plant, etc.)
    9. Role assignment validity dates
    10. User authorization buffer staleness
    11. Transport consistency (role exists in source but not target system)
    12. Fiori-specific checks (catalog, target mapping, OData service, backend auth)
        — only when the input looks like a Fiori app ID

    Returns a ``DiagnosisResult`` with:

    - ``status`` — ``access_granted`` | ``access_denied`` | ``partial_access``
    - ``root_cause`` — one-sentence primary finding
    - ``diagnosis_steps`` — every check performed (pass / fail / warning / info)
    - ``recommended_fix`` — concrete administrator action
    - ``estimated_fix_time`` — rough calendar time to resolve
    - ``risk_impact`` — SoD or sensitive-access risks from applying the fix
    - ``confidence_score`` — engine confidence in the root cause (0 – 1)
    """
    try:
        request = TroubleshootRequest(
            user_id=body.user_id,
            transaction=body.transaction,
            system=body.system,
            tenant_id=body.tenant_id,
            requested_by=body.requested_by,
            context=body.context,
        )
        result = _engine.diagnose(request)
        return result.to_dict()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Diagnosis engine error: {str(exc)}",
        ) from exc


@router.get(
    "/transactions",
    summary="List Known Transactions",
    response_description="List of all transactions in the GovernexPlus knowledge base.",
)
async def list_transactions(
    module: Optional[str] = Query(
        default=None,
        description="Filter by SAP module (e.g. 'FI', 'MM', 'SD', 'BASIS', 'HR').",
    ),
    sensitive_only: bool = Query(
        default=False,
        description="If true, return only transactions classified as sensitive.",
    ),
) -> Dict[str, Any]:
    """
    Return all transactions known to the GovernexPlus knowledge base.

    Each entry includes the tcode, description, module, sensitivity flag, and
    optional Fiori app ID mapping.

    Use the ``module`` and ``sensitive_only`` query parameters to filter.
    """
    transactions = get_transaction_list()

    if module:
        transactions = [t for t in transactions if t["module"].upper() == module.upper()]

    if sensitive_only:
        transactions = [t for t in transactions if t["sensitive"]]

    return {
        "total": len(transactions),
        "filters": {
            "module": module,
            "sensitive_only": sensitive_only,
        },
        "transactions": transactions,
    }


@router.get(
    "/transactions/{tcode}/requirements",
    summary="Get Transaction Authorization Requirements",
    response_description="Full authorization profile for the requested transaction code.",
)
async def get_tcode_requirements(tcode: str) -> Dict[str, Any]:
    """
    Return the complete authorization requirements for a specific transaction code.

    The response includes every authorization object, field, and required value
    that the GovernexPlus engine checks when diagnosing access to this tcode.

    This endpoint is useful for:

    - Role design and review (what auth objects does this tcode actually need?)
    - Access request pre-screening (what will the requester need?)
    - SU24 validation (does the maintained proposal match the KB?)

    Returns 404 if the tcode is not in the GovernexPlus knowledge base.
    """
    reqs = get_transaction_requirements(tcode.upper())
    if reqs is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Transaction '{tcode.upper()}' is not in the GovernexPlus knowledge base.  "
                "Use SU24 in SAP to view the authorization objects for this tcode."
            ),
        )
    return reqs


@router.get(
    "/common-issues",
    summary="List Common Access Issues",
    response_description="Curated list of the top SAP access failure patterns.",
)
async def list_common_issues(
    module: Optional[str] = Query(
        default=None,
        description="Filter by affected SAP module.",
    ),
    frequency: Optional[str] = Query(
        default=None,
        description=(
            "Filter by occurrence frequency: 'very_high', 'high', 'medium', 'low'."
        ),
    ),
) -> Dict[str, Any]:
    """
    Return the curated library of the most common SAP access failure patterns.

    Each entry includes:

    - ``symptom`` — what the end user or administrator observes
    - ``root_cause`` — the underlying technical reason
    - ``fix`` — step-by-step resolution instructions
    - ``prevention`` — how to prevent recurrence
    - ``affected_modules`` — which SAP modules are typically involved

    This endpoint is designed to power a self-service troubleshooting FAQ and
    to pre-populate the diagnosis engine's knowledge base for pattern matching.
    """
    issues = get_common_issues()

    if module:
        issues = [
            i for i in issues
            if module.upper() in [m.upper() for m in i["affected_modules"]]
        ]

    if frequency:
        issues = [i for i in issues if i["frequency"] == frequency.lower()]

    return {
        "total": len(issues),
        "filters": {
            "module": module,
            "frequency": frequency,
        },
        "issues": issues,
    }


@router.post(
    "/batch-diagnose",
    summary="Batch Diagnose Multiple Users",
    response_description=(
        "Diagnosis results for every user in the request, plus a summary breakdown."
    ),
)
async def batch_diagnose(body: BatchDiagnoseRequest) -> BatchDiagnoseResponse:
    """
    Diagnose multiple users for the same transaction and target system in a
    single API call.

    This is particularly useful for:

    - **Role change impact analysis**: before removing a tcode from a role,
      identify which users would lose access.
    - **Transport validation**: after a transport, verify all expected users
      now have access.
    - **Emergency access review**: during an incident, quickly check whether
      a set of users can execute a sensitive transaction.
    - **Regression testing**: after a role redesign, confirm that the user
      population retains their required access.

    Maximum 50 users per request.  For larger batches, paginate by splitting
    the ``user_ids`` list and calling this endpoint multiple times.
    """
    if len(body.user_ids) > 50:
        raise HTTPException(
            status_code=422,
            detail="Batch size exceeds the maximum of 50 users per request.",
        )

    try:
        results = _engine.batch_diagnose(
            user_ids=body.user_ids,
            transaction=body.transaction,
            system=body.system,
            tenant_id=body.tenant_id,
            requested_by=body.requested_by,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Batch diagnosis engine error: {str(exc)}",
        ) from exc

    serialized = [r.to_dict() for r in results]

    summary: Dict[str, int] = {
        "access_granted": 0,
        "access_denied": 0,
        "partial_access": 0,
    }
    for r in results:
        summary[r.status.value] += 1

    return BatchDiagnoseResponse(
        total_users=len(results),
        transaction=body.transaction.upper(),
        system=body.system.upper(),
        results=serialized,
        summary=summary,
    )


@router.get(
    "/history",
    summary="Get Recent Diagnosis History",
    response_description="Recent diagnosis runs, newest first.",
)
async def get_history(
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of history records to return (1 – 200).",
    ),
    user_id: Optional[str] = Query(
        default=None,
        description="Filter history to a specific user.",
    ),
    transaction: Optional[str] = Query(
        default=None,
        description="Filter history to a specific transaction code.",
    ),
) -> Dict[str, Any]:
    """
    Return the most recent access diagnosis runs recorded by the engine,
    newest first.

    The history is scoped to the current GovernexPlus instance.  In production,
    this should be backed by the database rather than the in-memory store used
    here.

    Use the ``user_id`` and ``transaction`` query parameters to narrow results
    to a specific investigation context.

    History records contain the same fields as a live ``/diagnose`` response,
    enabling re-review of past diagnoses without re-running the engine.
    """
    history = get_diagnosis_history(
        limit=limit,
        user_filter=user_id,
        transaction_filter=transaction,
    )

    return {
        "total": len(history),
        "limit": limit,
        "filters": {
            "user_id": user_id.upper() if user_id else None,
            "transaction": transaction.upper() if transaction else None,
        },
        "records": history,
    }
