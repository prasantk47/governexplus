"""
Template Library — Tenant-Aware Resolver
=========================================

Provides helpers used by the risk engine, request router, and test-plan
generator to load only ACTIVE library content for a given tenant.

Rule:
  active = custom-built (source_template_item_id IS NULL)
         OR  (has a TenantItemActivation where is_active=True)

When a row is "shipped" (is_customized=False) and active, the effective
payload is the global TemplateItem.payload.  Once customized, the row's
own columns are authoritative.
"""

from __future__ import annotations

import logging
from typing import Any, Type

from sqlalchemy.orm import Session
from sqlalchemy import or_

from core.feature_flags import flags

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Generic active-content query helper
# ---------------------------------------------------------------------------

def filter_active_for_tenant(
    query,
    model_class: Type[Any],
    tenant_id: str,
    db: Session,
):
    """
    Restrict a SQLAlchemy query on a functional-content model to rows that
    are either:
      • custom-built (source_template_item_id IS NULL), or
      • have an active TenantItemActivation for this tenant

    Returns the filtered query.  If TEMPLATE_LIBRARY_COW is off, the query
    is returned unchanged (legacy behaviour).
    """
    if not flags.TEMPLATE_LIBRARY_COW:
        return query

    from db.models.template_library import TenantItemActivation  # late import

    # subquery: template item IDs that are active for this tenant
    active_ids_sq = (
        db.query(TenantItemActivation.template_item_id)
        .filter(
            TenantItemActivation.tenant_id == tenant_id,
            TenantItemActivation.is_active == True,  # noqa: E712
        )
        .subquery()
    )

    src_col = getattr(model_class, "source_template_item_id", None)
    if src_col is None:
        # Model wasn't updated yet — skip filtering
        return query

    return query.filter(
        or_(
            src_col == None,                      # custom-built  # noqa: E711
            src_col.in_(active_ids_sq),            # active library item
        )
    )


# ---------------------------------------------------------------------------
# Risk-engine rule loading
# ---------------------------------------------------------------------------

def load_active_db_rules(tenant_id: str, db: Session) -> list:
    """
    Return RiskRuleModel rows from DB for this tenant, filtered to only
    active (or custom-built) ones.

    Returns an empty list if TEMPLATE_LIBRARY_COW is off or if no DB rules
    exist — the caller falls back to the in-memory ruleset in that case.
    """
    if not flags.TEMPLATE_LIBRARY_COW:
        return []

    try:
        from db.models.risk import RiskRuleModel

        q = db.query(RiskRuleModel).filter(
            RiskRuleModel.tenant_id == tenant_id,
            RiskRuleModel.is_enabled == True,  # noqa: E712
        )
        q = filter_active_for_tenant(q, RiskRuleModel, tenant_id, db)
        return q.all()
    except Exception as exc:
        logger.warning("resolver.load_active_db_rules failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Mitigation loading
# ---------------------------------------------------------------------------

def load_active_mitigations(tenant_id: str, db: Session) -> dict:
    """
    Return {rule_id: [MitigationControl]} for all active mitigations for
    this tenant.  Filtered to custom-built or actively-activated ones.
    """
    try:
        from db.models.risk import MitigationControl

        q = db.query(MitigationControl).filter(
            MitigationControl.tenant_id == tenant_id,
            MitigationControl.is_active == True,  # noqa: E712
        )
        q = filter_active_for_tenant(q, MitigationControl, tenant_id, db)
        mitigations: dict = {}
        for mc in q.all():
            for rule_id in (mc.applicable_rule_ids or []):
                mitigations.setdefault(rule_id, []).append(mc)
        return mitigations
    except Exception as exc:
        logger.warning("resolver.load_active_mitigations failed: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Process-control content loading
# ---------------------------------------------------------------------------

def load_active_controls(tenant_id: str, db: Session) -> list:
    """Return ProcessControl rows that are active (or custom-built) for tenant."""
    try:
        from db.models.process_control import ProcessControl

        q = db.query(ProcessControl).filter(
            ProcessControl.tenant_id == tenant_id,
            ProcessControl.is_active == True,  # noqa: E712
        )
        return filter_active_for_tenant(q, ProcessControl, tenant_id, db).all()
    except Exception as exc:
        logger.warning("resolver.load_active_controls failed: %s", exc)
        return []


def load_active_test_plans(tenant_id: str, db: Session) -> list:
    """Return ControlTest rows for active controls for tenant."""
    try:
        from db.models.process_control import ControlTest

        q = db.query(ControlTest).filter(ControlTest.tenant_id == tenant_id)
        return filter_active_for_tenant(q, ControlTest, tenant_id, db).all()
    except Exception as exc:
        logger.warning("resolver.load_active_test_plans failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Survey loading
# ---------------------------------------------------------------------------

def load_active_surveys(tenant_id: str, db: Session) -> list:
    """Return StandaloneSurvey rows active (or custom-built) for tenant."""
    try:
        from db.models.extended_modules import StandaloneSurvey

        q = db.query(StandaloneSurvey).filter(
            StandaloneSurvey.tenant_id == tenant_id,
        )
        return filter_active_for_tenant(q, StandaloneSurvey, tenant_id, db).all()
    except Exception as exc:
        logger.warning("resolver.load_active_surveys failed: %s", exc)
        return []
