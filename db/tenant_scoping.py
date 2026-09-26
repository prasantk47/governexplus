# db/tenant_scoping.py
# Automatic, impossible-to-forget tenant isolation for every ORM query and write.
#
# Install once at startup (after models are imported):
#
#     from db.tenant_scoping import install_tenant_scoping
#     install_tenant_scoping()
#
# From then on:
#   * Every SELECT against a model that has a `tenant_id` column is automatically
#     filtered to the current tenant (from core.tenant context var).
#   * Every INSERT is automatically stamped with the current tenant_id.
#   * Writes with a mismatched tenant_id raise TenantIsolationError instead of
#     silently leaking into another tenant.
#   * Platform-admin / background jobs can opt out explicitly with
#     `tenant_scoping_disabled()` - the escape hatch is loud and auditable.

from contextlib import contextmanager
from contextvars import ContextVar
import logging

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from db.models.base import Base
from core.tenant import get_current_tenant

logger = logging.getLogger(__name__)

_scoping_disabled: ContextVar[bool] = ContextVar("tenant_scoping_disabled", default=False)


class TenantIsolationError(RuntimeError):
    """Raised when a write targets a different tenant than the request context."""


def _current_tenant_id() -> str | None:
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else None


@contextmanager
def tenant_scoping_disabled(reason: str):
    """Explicit, logged escape hatch for platform-admin and system jobs."""
    logger.warning("tenant_scoping disabled: %s", reason)
    token = _scoping_disabled.set(True)
    try:
        yield
    finally:
        _scoping_disabled.reset(token)


def _tenant_mappers():
    """All mapped classes that carry a tenant_id column."""
    for mapper in Base.registry.mappers:
        if "tenant_id" in mapper.columns:
            yield mapper.class_


def install_tenant_scoping() -> None:
    """Register global ORM listeners. Idempotent."""
    if getattr(install_tenant_scoping, "_installed", False):
        return
    install_tenant_scoping._installed = True

    tenant_classes = list(_tenant_mappers())
    logger.info("Tenant scoping active on %d models", len(tenant_classes))

    @event.listens_for(Session, "do_orm_execute")
    def _add_tenant_filter(execute_state):
        if not execute_state.is_select:
            return
        if _scoping_disabled.get():
            return
        tenant_id = _current_tenant_id()
        if tenant_id is None:
            # No request context (startup, migrations). Fail open here but log;
            # flip to fail-closed once all system paths use the escape hatch.
            logger.debug("SELECT without tenant context: %s", execute_state.statement)
            return
        for cls in tenant_classes:
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    cls,
                    lambda c: c.tenant_id == tenant_id,
                    include_aliases=True,
                )
            )

    @event.listens_for(Session, "before_flush")
    def _stamp_and_guard_writes(session, flush_context, instances):
        if _scoping_disabled.get():
            return
        tenant_id = _current_tenant_id()
        for obj in session.new:
            if hasattr(obj, "tenant_id"):
                current = getattr(obj, "tenant_id", None)
                if current in (None, "", "tenant_default") and tenant_id:
                    obj.tenant_id = tenant_id
                elif tenant_id and current not in (None, "", tenant_id):
                    raise TenantIsolationError(
                        f"INSERT into {type(obj).__name__} for tenant "
                        f"'{current}' from context of tenant '{tenant_id}'"
                    )
        for obj in session.dirty | session.deleted:
            if hasattr(obj, "tenant_id") and tenant_id:
                current = getattr(obj, "tenant_id", None)
                if current not in (None, "", tenant_id):
                    raise TenantIsolationError(
                        f"WRITE to {type(obj).__name__} of tenant "
                        f"'{current}' from context of tenant '{tenant_id}'"
                    )
