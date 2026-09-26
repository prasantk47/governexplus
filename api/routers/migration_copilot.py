"""
Migration Copilot API Router

Exposes the ECC → S/4HANA Migration Copilot engine: full impact analysis,
per-role migration planning with SoD validation, and executive readiness
reporting.
"""

from fastapi import APIRouter, Depends, HTTPException, Body

from core.tenant import get_current_tenant
from db.database import db_manager

router = APIRouter()


def _get_tenant_id() -> str:
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


@router.get("/analyze")
def analyze_migration_impact(tenant_id: str = Depends(_get_tenant_id)):
    """Full migration impact analysis across all active roles.

    Scans every active role for the current tenant, maps ECC transaction codes
    to their S/4HANA equivalents, flags deprecated transactions, identifies
    Business Partner consolidation requirements, and surfaces Fiori app
    opportunities.

    Returns per-role mapping details plus an aggregate impact summary.
    """
    from core.migration.copilot import MigrationCopilot
    with db_manager.session_scope() as db:
        copilot = MigrationCopilot(tenant_id, db)
        return copilot.analyze_migration_impact()


@router.post("/migrate-role")
def migrate_role(
    body: dict = Body(...),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Generate a detailed migration plan for a single role.

    Body: ``{"role_id": "<business role id>"}``

    Returns tcode mappings, deprecated transaction removals, Business Partner
    consolidation steps, affected user list, pre/post-migration validation
    checklist, and generated test cases for the migrated role.
    """
    from core.migration.copilot import MigrationCopilot
    role_id = body.get("role_id")
    if not role_id:
        raise HTTPException(status_code=400, detail="role_id is required")
    with db_manager.session_scope() as db:
        copilot = MigrationCopilot(tenant_id, db)
        result = copilot.migrate_role(role_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result


@router.get("/readiness-report")
def readiness_report(tenant_id: str = Depends(_get_tenant_id)):
    """Executive S/4HANA migration readiness report.

    Produces an executive-level summary including a readiness score (0-100),
    effort breakdown by migration complexity (low / medium / high), and a
    recommended three-phase migration sequence prioritised by effort and risk.
    """
    from core.migration.copilot import MigrationCopilot
    with db_manager.session_scope() as db:
        copilot = MigrationCopilot(tenant_id, db)
        return copilot.generate_migration_report()
