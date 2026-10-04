"""
Copy-on-Write (CoW) Resolution — Template Library Phase 1
==========================================================

How it works
------------
A functional-content row (e.g. a risk rule, a process control, a KRI)
can be either:

  • Shipped   — source_template_item_id is set, is_customized = False.
                Reads serve the payload from the global TemplateItem.
  • Customized— source_template_item_id is set, is_customized = True.
                Reads serve the tenant's own copy of the payload.
  • Custom-built — source_template_item_id is NULL.
                Reads serve the row itself (no template involved).

The first time a tenant *edits* a shipped item the caller must use
``mark_customized()`` to flip is_customized=True on that row.  After
that all writes go to the tenant's row; the global TemplateItem is left
untouched.

Usage in the risk engine / test-plan generator / request router:

    from core.library.copy_on_write import resolve_payload, mark_customized

    # Reading — get effective payload for a functional row
    payload = resolve_payload(row, db)

    # Writing — tenant is editing a shipped item for the first time
    mark_customized(row, db)
    # ... update row columns as usual ...
    db.commit()
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from core.feature_flags import flags

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def resolve_payload(row: Any, db: Session) -> dict | None:
    """
    Return the effective JSON payload for a functional-content row.

    Resolution order:
      1. If TEMPLATE_LIBRARY_COW is disabled → return None (caller uses own
         fields directly, legacy behaviour preserved).
      2. If row.source_template_item_id is NULL → row is custom-built,
         return None (caller uses its own fields).
      3. If row.is_customized is True → row has a tenant copy; return None
         so the caller uses the row's own fields (the tenant copy IS the row).
      4. Otherwise (shipped, not yet customized) → fetch the global
         TemplateItem and return its payload.

    Returns None to signal "use the row's own fields as-is".
    Returns a dict when the global template payload should override.
    """
    if not flags.TEMPLATE_LIBRARY_COW:
        return None

    source_id = getattr(row, "source_template_item_id", None)
    if not source_id:
        return None

    if getattr(row, "is_customized", False):
        return None

    # Fetch global item
    from db.models.template_library import TemplateItem  # late import to avoid circular
    item = db.query(TemplateItem).filter(TemplateItem.id == source_id).first()
    if item is None:
        logger.warning(
            "CoW: template item %s not found for row %s.%s — treating as custom",
            source_id, type(row).__tablename__, getattr(row, "id", "?"),
        )
        return None

    return item.payload


def mark_customized(row: Any, db: Session) -> None:
    """
    Mark a shipped row as customized (first-edit copy-on-write).

    Call this BEFORE making any changes to a row whose
    source_template_item_id is set and is_customized is False.
    The db.commit() is left to the caller so it can batch with the edit.
    """
    if not flags.TEMPLATE_LIBRARY_COW:
        return

    source_id = getattr(row, "source_template_item_id", None)
    if not source_id:
        return  # custom-built, nothing to do

    if getattr(row, "is_customized", False):
        return  # already customized

    row.is_customized = True
    logger.info(
        "CoW: row %s.id=%s marked customized (template %s v%s)",
        type(row).__tablename__ if hasattr(type(row), "__tablename__") else type(row).__name__,
        getattr(row, "id", "?"),
        source_id,
        getattr(row, "template_version", "?"),
    )

    # Also update the TenantItemActivation so the library UI shows "Customized"
    _sync_activation_customized(row, db)


def create_from_template(
    item,  # TemplateItem ORM instance
    row_class: type,
    tenant_id: str,
    mapping_overrides: dict | None = None,
    extra_fields: dict | None = None,
    db: Session | None = None,
) -> Any:
    """
    Instantiate a functional-content row from a TemplateItem.

    The payload from the template is merged with mapping_overrides (org units,
    owners, connected system IDs) and any extra_fields the caller needs.
    source_template_item_id and template_version are wired automatically.
    is_customized is left False — the row is still "shipped".

    The caller is responsible for db.add(row) and db.commit().
    """
    payload: dict = (item.payload or {}).copy()
    if mapping_overrides:
        payload.update(mapping_overrides)

    kwargs: dict = {
        "tenant_id": tenant_id,
        "source_template_item_id": item.id,
        "template_version": item.version,
        "is_customized": False,
    }
    if extra_fields:
        kwargs.update(extra_fields)

    # Spread payload fields that the row class knows about
    import inspect
    known_cols = {
        c.key for c in inspect.getmembers(row_class)
        if hasattr(c[1], "property")
    }
    # Simpler approach: try to set payload fields, skip unknown ones silently
    for key, val in payload.items():
        if key not in kwargs:
            kwargs[key] = val

    try:
        row = row_class(**kwargs)
    except TypeError:
        # If the row class doesn't accept all payload keys, build minimally
        safe_kwargs = {k: v for k, v in kwargs.items() if k in {
            "tenant_id", "source_template_item_id", "template_version", "is_customized"
        }}
        if extra_fields:
            safe_kwargs.update(extra_fields)
        row = row_class(**safe_kwargs)

    return row


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _sync_activation_customized(row: Any, db: Session) -> None:
    """
    When a row is marked customized, flip the corresponding
    TenantItemActivation.copy_payload so the library UI shows "Customized".
    """
    try:
        from db.models.template_library import TenantItemActivation  # late import
        tenant_id = getattr(row, "tenant_id", None)
        source_id = getattr(row, "source_template_item_id", None)
        if not tenant_id or not source_id:
            return

        act = (
            db.query(TenantItemActivation)
            .filter_by(tenant_id=tenant_id, template_item_id=source_id)
            .first()
        )
        if act and act.copy_payload is None:
            # Store a sentinel so effective_payload() returns the tenant copy
            act.copy_payload = {"__cow_marker": True, "row_id": str(getattr(row, "id", ""))}
    except Exception as exc:
        logger.debug("CoW: could not sync activation record: %s", exc)
