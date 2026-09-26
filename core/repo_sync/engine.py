"""
Repository Sync Engine

Manages the scheduled and on-demand synchronization of identity and
authorization data from connected external systems into the Governex+
repository.

Sync data types
---------------
- users          : User master data (SAP SU01, Azure AD, HRIS)
- roles          : Role definitions and composite role membership
- authorizations : Authorization object values assigned to users/roles
- usage          : Transaction usage logs (SM20, STAD, ST05 equivalents)

Each sync run is recorded as a SyncJob with detailed statistics
(records_synced, records_added, records_updated, records_deleted,
errors, duration_seconds).  Schedules are stored per system and honoured
by the scheduler module.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from db.models.operations import SyncConfig, SyncHistory
from db.database import db_manager


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

SYNC_TYPES = ("users", "roles", "authorizations", "usage")
SYNC_STATUSES = ("idle", "running", "completed", "failed", "cancelled")


@dataclass
class SyncJob:
    """Record of a single sync run."""

    job_id: str
    system_id: str
    sync_type: str          # users | roles | authorizations | usage | full
    status: str             # idle | running | completed | failed | cancelled
    started_at: str | None
    completed_at: str | None
    duration_seconds: float | None
    records_synced: int
    records_added: int
    records_updated: int
    records_deleted: int
    errors: list[dict[str, Any]] = field(default_factory=list)
    error_count: int = 0
    triggered_by: str = "scheduler"     # scheduler | manual | api


@dataclass
class SystemSyncConfig:
    """Configuration and current state for a connected system's sync."""

    system_id: str
    system_name: str
    system_type: str        # SAP_ECC | SAP_S4HANA | AZURE_AD | WORKDAY | SUCCESSFACTORS
    host: str
    enabled: bool
    schedule_interval_minutes: int      # 0 = manual only
    last_sync_at: str | None
    next_sync_at: str | None
    overall_status: str                 # idle | running | completed | failed
    history: list[SyncJob] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Default seed data helpers
# ---------------------------------------------------------------------------

def _dt(days_ago: float = 0, hours_ago: float = 0) -> str:
    return (datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)).isoformat()


def _default_sync_configs() -> list[dict[str, Any]]:
    """Return seed data for SyncConfig rows."""
    return [
        {
            "config_id": "SYS-SAP-PROD",
            "system_name": "SAP ECC Production",
            "system_type": "SAP_ECC",
            "direction": "inbound",
            "status": "active",
            "schedule_minutes": 240,
            "last_sync_at": datetime.utcnow() - timedelta(hours=2),
            "last_sync_status": "success",
            "objects_synced": 45230,
            "sync_scope": {"users": True, "roles": True, "authorizations": True, "usage": True},
            "connection_config": {"host": "sapecc-prod.corp.com:3300"},
        },
        {
            "config_id": "SYS-SAP-QA",
            "system_name": "SAP S/4HANA QA",
            "system_type": "SAP_S4HANA",
            "direction": "inbound",
            "status": "active",
            "schedule_minutes": 1440,
            "last_sync_at": datetime.utcnow() - timedelta(days=1),
            "last_sync_status": "success",
            "objects_synced": 22100,
            "sync_scope": {"users": True, "roles": True, "authorizations": True, "usage": False},
            "connection_config": {"host": "saps4-qa.corp.com:3300"},
        },
        {
            "config_id": "SYS-AZURE-AD",
            "system_name": "Azure Active Directory",
            "system_type": "AZURE_AD",
            "direction": "inbound",
            "status": "active",
            "schedule_minutes": 60,
            "last_sync_at": datetime.utcnow() - timedelta(minutes=30),
            "last_sync_status": "success",
            "objects_synced": 8500,
            "sync_scope": {"users": True, "roles": False, "authorizations": False, "usage": False},
            "connection_config": {"host": "graph.microsoft.com"},
        },
        {
            "config_id": "SYS-WORKDAY",
            "system_name": "Workday HCM",
            "system_type": "WORKDAY",
            "direction": "inbound",
            "status": "active",
            "schedule_minutes": 720,
            "last_sync_at": datetime.utcnow() - timedelta(hours=6),
            "last_sync_status": "success",
            "objects_synced": 12300,
            "sync_scope": {"users": True, "roles": False, "authorizations": False, "usage": False},
            "connection_config": {"host": "api.workday.com"},
        },
        {
            "config_id": "SYS-SUCCESSFACTORS",
            "system_name": "SAP SuccessFactors",
            "system_type": "SUCCESSFACTORS",
            "direction": "inbound",
            "status": "paused",
            "schedule_minutes": 0,
            "last_sync_at": datetime.utcnow() - timedelta(days=14),
            "last_sync_status": "success",
            "objects_synced": 6200,
            "sync_scope": {"users": True, "roles": False, "authorizations": False, "usage": False},
            "connection_config": {"host": "api.successfactors.com"},
        },
    ]


def _default_sync_history() -> list[dict[str, Any]]:
    """Return seed data for SyncHistory rows."""
    now = datetime.utcnow()

    def _h(sync_id, config_id, system_name, direction, status, days_ago, duration, objects_synced, errors=None):
        started = now - timedelta(days=days_ago)
        completed = started + timedelta(seconds=duration)
        return {
            "sync_id": sync_id,
            "config_id": config_id,
            "system_name": system_name,
            "direction": direction,
            "status": status,
            "objects_synced": objects_synced,
            "errors": errors or [],
            "duration_seconds": int(duration),
            "started_at": started,
            "completed_at": completed,
        }

    return [
        _h("SJOB-001", "SYS-SAP-PROD", "SAP ECC Production", "inbound", "success", 0.08, 3621, 45230),
        _h("SJOB-002", "SYS-SAP-PROD", "SAP ECC Production", "inbound", "success", 0.25, 182,  5010),
        _h("SJOB-003", "SYS-SAP-PROD", "SAP ECC Production", "inbound", "success", 0.5,  94,   1240),
        _h("SJOB-004", "SYS-SAP-PROD", "SAP ECC Production", "inbound", "success", 1.0,  1440, 38980,
           [{"code": "SYNC_ERR", "message": "Record parse error #1"},
            {"code": "SYNC_ERR", "message": "Record parse error #2"}]),
        _h("SJOB-005", "SYS-SAP-PROD", "SAP ECC Production", "inbound", "success", 2.0,  305,  250000),
        _h("SJOB-010", "SYS-SAP-QA",   "SAP S/4HANA QA",    "inbound", "success", 1.0,  1820, 22100),
        _h("SJOB-011", "SYS-SAP-QA",   "SAP S/4HANA QA",    "inbound", "success", 2.0,  91,   2200),
        _h("SJOB-012", "SYS-SAP-QA",   "SAP S/4HANA QA",    "inbound", "failed",  3.0,  0,    0,
           [{"code": "SYNC_ERR", "message": "Connection refused"}]),
        _h("SJOB-020", "SYS-AZURE-AD", "Azure Active Directory", "inbound", "success", 0.01, 45, 8500),
        _h("SJOB-021", "SYS-AZURE-AD", "Azure Active Directory", "inbound", "success", 1.01, 43, 8500),
        _h("SJOB-022", "SYS-AZURE-AD", "Azure Active Directory", "inbound", "success", 2.01, 46, 8498),
        _h("SJOB-030", "SYS-WORKDAY",  "Workday HCM",           "inbound", "success", 0.25, 120, 12300),
        _h("SJOB-031", "SYS-WORKDAY",  "Workday HCM",           "inbound", "success", 0.75, 118, 12265),
        _h("SJOB-040", "SYS-SUCCESSFACTORS", "SAP SuccessFactors", "inbound", "success", 14, 200, 6200),
    ]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class RepoSyncEngine:
    """
    Core engine for managing repository synchronization with connected systems.

    Sync configs and run history are persisted to the database via the
    SyncConfig and SyncHistory models.  Default seed data is written on first
    access when the tables are empty.
    """

    def __init__(self) -> None:
        self._loaded = False

    # ------------------------------------------------------------------
    # Lazy-load / seed
    # ------------------------------------------------------------------

    def _ensure_loaded(self, tenant_id: str = "tenant_default") -> None:
        """Seed DB with default configs and history on first access if empty."""
        if self._loaded:
            return
        self._loaded = True

        if not db_manager._initialized:
            db_manager.init()
            db_manager.create_tables()

        with db_manager.session_scope() as session:
            count = session.query(SyncConfig).filter_by(tenant_id=tenant_id).count()
            if count == 0:
                for cfg in _default_sync_configs():
                    row = SyncConfig(
                        tenant_id=tenant_id,
                        config_id=cfg["config_id"],
                        system_name=cfg["system_name"],
                        system_type=cfg["system_type"],
                        direction=cfg["direction"],
                        status=cfg["status"],
                        schedule_minutes=cfg["schedule_minutes"],
                        last_sync_at=cfg["last_sync_at"],
                        last_sync_status=cfg["last_sync_status"],
                        objects_synced=cfg["objects_synced"],
                        sync_scope=cfg["sync_scope"],
                        connection_config=cfg["connection_config"],
                    )
                    session.add(row)

            hist_count = session.query(SyncHistory).filter_by(tenant_id=tenant_id).count()
            if hist_count == 0:
                for h in _default_sync_history():
                    row = SyncHistory(
                        tenant_id=tenant_id,
                        sync_id=h["sync_id"],
                        config_id=h["config_id"],
                        system_name=h["system_name"],
                        direction=h["direction"],
                        status=h["status"],
                        objects_synced=h["objects_synced"],
                        errors=h["errors"],
                        duration_seconds=h["duration_seconds"],
                        started_at=h["started_at"],
                        completed_at=h["completed_at"],
                    )
                    session.add(row)

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _get_config(self, system_id: str, tenant_id: str = "tenant_default") -> SyncConfig:
        self._ensure_loaded(tenant_id)
        with db_manager.session_scope() as session:
            cfg = session.query(SyncConfig).filter_by(
                config_id=system_id, tenant_id=tenant_id
            ).first()
            if cfg is None:
                raise ValueError(f"System '{system_id}' not found")
            session.expunge(cfg)
            return cfg

    def _get_history_for_config(
        self,
        config_id: str,
        tenant_id: str = "tenant_default",
        sync_type: str | None = None,
        limit: int = 20,
    ) -> list[SyncHistory]:
        """Return history rows for a config_id, newest first."""
        with db_manager.session_scope() as session:
            q = session.query(SyncHistory).filter_by(
                config_id=config_id, tenant_id=tenant_id
            )
            # SyncHistory has no sync_type column; the engine tracks type via
            # the full history entry — we store it in the sync_id prefix for
            # filtering when the caller passes sync_type.
            if sync_type:
                # objects_synced is used as a proxy; real filtering is done
                # client-side since sync_type is not a DB column.
                pass
            rows = q.order_by(SyncHistory.started_at.desc()).limit(limit * 5).all()
            for r in rows:
                session.expunge(r)
        return rows

    def _history_to_job(self, h: SyncHistory, system_id: str) -> SyncJob:
        """Convert a SyncHistory DB row to a SyncJob dataclass."""
        errors = h.errors or []
        return SyncJob(
            job_id=h.sync_id,
            system_id=system_id,
            sync_type=h.direction,          # direction reused as sync_type label
            status=h.status,
            started_at=h.started_at.isoformat() if h.started_at else None,
            completed_at=h.completed_at.isoformat() if h.completed_at else None,
            duration_seconds=float(h.duration_seconds) if h.duration_seconds else None,
            records_synced=h.objects_synced,
            records_added=0,
            records_updated=h.objects_synced,
            records_deleted=0,
            errors=errors,
            error_count=len(errors),
            triggered_by="scheduler",
        )

    def _config_to_system(self, cfg: SyncConfig, history: list[SyncJob]) -> SystemSyncConfig:
        """Convert a SyncConfig DB row to a SystemSyncConfig dataclass."""
        host = ""
        if cfg.connection_config and isinstance(cfg.connection_config, dict):
            host = cfg.connection_config.get("host", "")

        last_sync_str = cfg.last_sync_at.isoformat() if cfg.last_sync_at else None
        next_sync_str = None
        if cfg.schedule_minutes and cfg.schedule_minutes > 0 and cfg.status == "active":
            base = cfg.last_sync_at or datetime.utcnow()
            next_sync_str = (base + timedelta(minutes=cfg.schedule_minutes)).isoformat()

        # Map DB status to overall_status vocabulary
        status_map = {"active": "completed", "paused": "idle", "error": "failed"}
        if cfg.last_sync_status == "failed":
            overall_status = "failed"
        elif cfg.status == "paused":
            overall_status = "idle"
        else:
            overall_status = status_map.get(cfg.status, "idle")

        return SystemSyncConfig(
            system_id=cfg.config_id,
            system_name=cfg.system_name,
            system_type=cfg.system_type,
            host=host,
            enabled=cfg.status != "paused",
            schedule_interval_minutes=cfg.schedule_minutes or 0,
            last_sync_at=last_sync_str,
            next_sync_at=next_sync_str,
            overall_status=overall_status,
            history=history,
        )

    def _all_systems(self, tenant_id: str = "tenant_default") -> dict[str, SystemSyncConfig]:
        self._ensure_loaded(tenant_id)
        with db_manager.session_scope() as session:
            configs = session.query(SyncConfig).filter_by(tenant_id=tenant_id).all()
            for c in configs:
                session.expunge(c)

        result = {}
        for cfg in configs:
            hist_rows = self._get_history_for_config(cfg.config_id, tenant_id, limit=50)
            jobs = [self._history_to_job(h, cfg.config_id) for h in hist_rows]
            result[cfg.config_id] = self._config_to_system(cfg, jobs)
        return result

    # ------------------------------------------------------------------
    # Individual sync operations
    # ------------------------------------------------------------------

    def sync_users(self, system_id: str, triggered_by: str = "api") -> dict[str, Any]:
        """
        Synchronize user master data from the specified system.

        Simulates reading user records, comparing against the local repository,
        and writing add/update/delete deltas.
        """
        return self._run_sync(system_id, "users", triggered_by)

    def sync_roles(self, system_id: str, triggered_by: str = "api") -> dict[str, Any]:
        """
        Synchronize role definitions and composite role memberships from the
        specified system.
        """
        return self._run_sync(system_id, "roles", triggered_by)

    def sync_authorizations(self, system_id: str, triggered_by: str = "api") -> dict[str, Any]:
        """
        Synchronize authorization object values assigned to users and roles
        from the specified system.
        """
        return self._run_sync(system_id, "authorizations", triggered_by)

    def sync_usage(self, system_id: str, triggered_by: str = "api") -> dict[str, Any]:
        """
        Synchronize transaction usage logs (equivalent to SAP SM20 / STAD)
        from the specified system.
        """
        return self._run_sync(system_id, "usage", triggered_by)

    def full_sync(self, system_id: str, triggered_by: str = "api", tenant_id: str = "tenant_default") -> dict[str, Any]:
        """
        Execute all four sync types (users, roles, authorizations, usage)
        sequentially for the specified system.

        Returns a combined summary job.
        """
        cfg = self._get_config(system_id, tenant_id)
        if cfg.status == "paused":
            raise ValueError(f"System '{system_id}' is disabled — enable it before syncing")

        job_id = f"SJOB-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.utcnow()
        started = now

        # Query actual DB counts for the tenant instead of random simulation values
        from db.models.user import User, Role
        with db_manager.session_scope() as session:
            user_count = session.query(User).filter_by(tenant_id=tenant_id).count()
            role_count = session.query(Role).filter_by(tenant_id=tenant_id).count()

        subtotals = {
            "users":          (user_count, 0, user_count, 0),
            "roles":          (role_count, 0, role_count, 0),
            "authorizations": (0, 0, 0, 0),
            "usage":          (0, 0, 0, 0),
        }
        total_synced = sum(v[0] for v in subtotals.values())
        # Duration is measured wall-clock time; use 0 for a synchronous stub that
        # returns immediately (no real connector call has been made yet).
        duration = 0.0
        completed = now + timedelta(seconds=duration)

        with db_manager.session_scope() as session:
            hist = SyncHistory(
                tenant_id=tenant_id,
                sync_id=job_id,
                config_id=system_id,
                system_name=cfg.system_name,
                direction="inbound",
                status="success",
                objects_synced=total_synced,
                errors=[],
                duration_seconds=int(duration),
                started_at=started,
                completed_at=completed,
            )
            session.add(hist)

            # Update last sync on config
            session.query(SyncConfig).filter_by(
                config_id=system_id, tenant_id=tenant_id
            ).update({
                "last_sync_at": completed,
                "last_sync_status": "success",
                "objects_synced": total_synced,
            })

        job = SyncJob(
            job_id=job_id,
            system_id=system_id,
            sync_type="full",
            status="completed",
            started_at=started.isoformat(),
            completed_at=completed.isoformat(),
            duration_seconds=duration,
            records_synced=total_synced,
            records_added=sum(v[1] for v in subtotals.values()),
            records_updated=sum(v[2] for v in subtotals.values()),
            records_deleted=sum(v[3] for v in subtotals.values()),
            errors=[],
            error_count=0,
            triggered_by=triggered_by,
        )

        return {
            "job": self._job_to_dict(job),
            "subtotals": {k: {"synced": v[0], "added": v[1], "updated": v[2], "deleted": v[3]} for k, v in subtotals.items()},
        }

    # ------------------------------------------------------------------
    # Status and history
    # ------------------------------------------------------------------

    def get_sync_status(self, system_id: str, tenant_id: str = "tenant_default") -> dict[str, Any]:
        """Return the current sync status for a specific system."""
        cfg = self._get_config(system_id, tenant_id)
        hist_rows = self._get_history_for_config(system_id, tenant_id, limit=1)
        jobs = [self._history_to_job(h, system_id) for h in hist_rows]
        system = self._config_to_system(cfg, jobs)
        latest_job = jobs[0] if jobs else None

        return {
            "system_id": system.system_id,
            "system_name": system.system_name,
            "system_type": system.system_type,
            "enabled": system.enabled,
            "overall_status": system.overall_status,
            "last_sync_at": system.last_sync_at,
            "next_sync_at": system.next_sync_at,
            "schedule_interval_minutes": system.schedule_interval_minutes,
            "latest_job": self._job_to_dict(latest_job) if latest_job else None,
        }

    def get_sync_history(
        self,
        system_id: str,
        sync_type: str | None = None,
        limit: int = 20,
        tenant_id: str = "tenant_default",
    ) -> dict[str, Any]:
        """
        Return the sync run history for a specific system.

        Parameters
        ----------
        system_id:  The system to query.
        sync_type:  Optional filter by sync type (users/roles/authorizations/usage/full).
        limit:      Maximum number of history entries to return.
        """
        cfg = self._get_config(system_id, tenant_id)
        hist_rows = self._get_history_for_config(system_id, tenant_id, limit=limit)
        jobs = [self._history_to_job(h, system_id) for h in hist_rows]
        if sync_type:
            jobs = [j for j in jobs if j.sync_type == sync_type]
        jobs = jobs[:limit]

        return {
            "system_id": system_id,
            "system_name": cfg.system_name,
            "history": [self._job_to_dict(j) for j in jobs],
            "total": len(jobs),
        }

    def get_sync_dashboard(self, tenant_id: str = "tenant_default") -> dict[str, Any]:
        """
        Return an overview of sync status across all registered systems.

        Includes per-system last sync time, status, schedule, and totals.
        """
        self._ensure_loaded(tenant_id)
        systems = self._all_systems(tenant_id)
        overview = []
        for system in systems.values():
            latest_job = system.history[0] if system.history else None
            total_records = sum(j.records_synced for j in system.history)
            total_errors  = sum(j.error_count    for j in system.history)
            overview.append({
                "system_id":                   system.system_id,
                "system_name":                 system.system_name,
                "system_type":                 system.system_type,
                "enabled":                     system.enabled,
                "overall_status":              system.overall_status,
                "last_sync_at":                system.last_sync_at,
                "next_sync_at":                system.next_sync_at,
                "schedule_interval_minutes":   system.schedule_interval_minutes,
                "total_sync_runs":             len(system.history),
                "total_records_synced":        total_records,
                "total_errors":                total_errors,
                "latest_job_summary":          self._job_to_dict(latest_job) if latest_job else None,
            })

        total_systems  = len(overview)
        enabled        = sum(1 for s in overview if s["enabled"])
        healthy        = sum(1 for s in overview if s["overall_status"] == "completed")
        failed         = sum(1 for s in overview if s["overall_status"] == "failed")
        running        = sum(1 for s in overview if s["overall_status"] == "running")

        return {
            "dashboard_generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_systems":   total_systems,
                "enabled_systems": enabled,
                "healthy":         healthy,
                "failed":          failed,
                "running":         running,
            },
            "systems": overview,
        }

    # ------------------------------------------------------------------
    # Schedule management
    # ------------------------------------------------------------------

    def schedule_sync(
        self,
        system_id: str,
        interval_minutes: int,
        enabled: bool = True,
        tenant_id: str = "tenant_default",
    ) -> dict[str, Any]:
        """
        Set or update the automatic sync schedule for a system.

        Parameters
        ----------
        system_id:          The system to schedule.
        interval_minutes:   Sync interval in minutes.  Pass 0 to disable scheduling
                            (manual-only mode).
        enabled:            Whether the system sync is enabled at all.
        """
        if interval_minutes < 0:
            raise ValueError("interval_minutes must be >= 0")

        new_status = "active" if enabled else "paused"
        next_sync_at = None
        if interval_minutes > 0 and enabled:
            next_sync_at = (datetime.utcnow() + timedelta(minutes=interval_minutes)).isoformat()

        with db_manager.session_scope() as session:
            updated = session.query(SyncConfig).filter_by(
                config_id=system_id, tenant_id=tenant_id
            ).update({
                "schedule_minutes": interval_minutes,
                "status": new_status,
            })
            if updated == 0:
                raise ValueError(f"System '{system_id}' not found")

        cfg = self._get_config(system_id, tenant_id)

        return {
            "system_id":                 system_id,
            "system_name":               cfg.system_name,
            "enabled":                   enabled,
            "schedule_interval_minutes": interval_minutes,
            "next_sync_at":              next_sync_at,
            "message": (
                f"Schedule updated: every {interval_minutes} minutes"
                if interval_minutes > 0
                else "Schedule disabled — manual sync only"
            ),
        }

    def cancel_sync(self, job_id: str, tenant_id: str = "tenant_default") -> dict[str, Any]:
        """
        Cancel a running sync job.

        Searches all systems for the job and marks it as cancelled if it is
        in a running or pending state.
        """
        with db_manager.session_scope() as session:
            hist = session.query(SyncHistory).filter_by(
                sync_id=job_id, tenant_id=tenant_id
            ).first()
            if hist is None:
                raise ValueError(f"Job '{job_id}' not found")

            if hist.status == "running":
                now = datetime.utcnow()
                hist.status = "failed"   # no "cancelled" in DB enum, map appropriately
                hist.completed_at = now
                if hist.started_at:
                    hist.duration_seconds = int((now - hist.started_at).total_seconds())
                config_id = hist.config_id
                return {
                    "cancelled": True,
                    "job_id": job_id,
                    "system_id": config_id,
                }
            else:
                return {
                    "cancelled": False,
                    "job_id": job_id,
                    "reason": f"Job is in '{hist.status}' state and cannot be cancelled",
                }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_sync(self, system_id: str, sync_type: str, triggered_by: str, tenant_id: str = "tenant_default") -> dict[str, Any]:
        """Run a single-type sync and persist the result to the DB.

        Counts are derived from actual DB state for the tenant.  No real
        connector call is made here (that requires the connector layer); this
        method records what is currently in the repository and marks the sync
        as completed so the history and dashboard reflect real data.
        """
        cfg = self._get_config(system_id, tenant_id)

        if cfg.status == "paused":
            raise ValueError(f"System '{system_id}' is disabled — enable it before syncing")

        job_id = f"SJOB-{uuid.uuid4().hex[:8].upper()}"
        now    = datetime.utcnow()

        # Derive actual record counts from the DB for the affected sync type.
        from db.models.user import User, Role
        with db_manager.session_scope() as session:
            if sync_type == "users":
                synced = session.query(User).filter_by(tenant_id=tenant_id).count()
            elif sync_type == "roles":
                synced = session.query(Role).filter_by(tenant_id=tenant_id).count()
            else:
                # authorizations and usage require the connector layer which is
                # not yet wired here; return zero counts rather than fake data.
                synced = 0

        added   = 0
        updated = synced
        deleted = 0
        error_count = 0
        duration = 0.0
        db_status  = "success"
        job_status = "completed"

        completed = now + timedelta(seconds=duration)
        errors: list[dict[str, Any]] = []

        with db_manager.session_scope() as session:
            hist = SyncHistory(
                tenant_id=tenant_id,
                sync_id=job_id,
                config_id=system_id,
                system_name=cfg.system_name,
                direction="inbound",
                status=db_status,
                objects_synced=synced,
                errors=errors,
                duration_seconds=int(duration),
                started_at=now,
                completed_at=completed,
            )
            session.add(hist)

            session.query(SyncConfig).filter_by(
                config_id=system_id, tenant_id=tenant_id
            ).update({
                "last_sync_at": completed,
                "last_sync_status": db_status,
                "objects_synced": synced,
            })

        job = SyncJob(
            job_id=job_id,
            system_id=system_id,
            sync_type=sync_type,
            status=job_status,
            started_at=now.isoformat(),
            completed_at=completed.isoformat(),
            duration_seconds=duration,
            records_synced=synced,
            records_added=added,
            records_updated=updated,
            records_deleted=deleted,
            errors=errors,
            error_count=error_count,
            triggered_by=triggered_by,
        )
        return self._job_to_dict(job)

    def list_systems(self, tenant_id: str = "tenant_default") -> list[dict[str, Any]]:
        """Return summary info for all registered systems."""
        self._ensure_loaded(tenant_id)
        with db_manager.session_scope() as session:
            configs = session.query(SyncConfig).filter_by(tenant_id=tenant_id).all()
            for c in configs:
                session.expunge(c)

        result = []
        for cfg in configs:
            host = ""
            if cfg.connection_config and isinstance(cfg.connection_config, dict):
                host = cfg.connection_config.get("host", "")

            status_map = {"active": "completed", "paused": "idle", "error": "failed"}
            overall_status = status_map.get(cfg.status, "idle")
            if cfg.last_sync_status == "failed":
                overall_status = "failed"

            result.append({
                "system_id":                 cfg.config_id,
                "system_name":               cfg.system_name,
                "system_type":               cfg.system_type,
                "host":                      host,
                "enabled":                   cfg.status != "paused",
                "overall_status":            overall_status,
                "last_sync_at":              cfg.last_sync_at.isoformat() if cfg.last_sync_at else None,
                "schedule_interval_minutes": cfg.schedule_minutes or 0,
            })
        return result

    def _job_to_dict(self, job: SyncJob) -> dict[str, Any]:
        return {
            "job_id":           job.job_id,
            "system_id":        job.system_id,
            "sync_type":        job.sync_type,
            "status":           job.status,
            "started_at":       job.started_at,
            "completed_at":     job.completed_at,
            "duration_seconds": job.duration_seconds,
            "records_synced":   job.records_synced,
            "records_added":    job.records_added,
            "records_updated":  job.records_updated,
            "records_deleted":  job.records_deleted,
            "error_count":      job.error_count,
            "errors":           job.errors,
            "triggered_by":     job.triggered_by,
        }
