"""
Role Transport Management
Tracks SAP transports carrying role changes across DEV/QA/PROD systems.

Transport states: created, released, imported_qa, imported_prod, failed, rolled_back
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from db.models.operations import TransportRecord
from db.database import db_manager


# ---------------------------------------------------------------------------
# Default seed data — 15+ realistic scenarios
# ---------------------------------------------------------------------------

def _default_transports() -> List[Dict[str, Any]]:
    """Return default transport seed rows."""
    return [
        {
            "transport_id": "DEV900001",
            "description": "Finance role cleanup - remove excessive GL posting access",
            "source_system": "DEV",
            "target_system": "PROD",
            "status": "imported_prod",
            "category": "role",
            "objects": ["Z:FI_AP_PROCESSOR", "Z:FI_AP_SENIOR"],
            "dependencies": [],
            "conflicts": [],
            "owner": "basis_admin",
            "released_at": datetime(2026, 7, 2, 10, 30, 0),
            "imported_at": datetime(2026, 7, 5, 6, 0, 0),
            "error_message": None,
            # Extra fields stored in objects for lifecycle tracking
            "_imports": [
                {"system": "QA",   "status": "success", "imported_at": "2026-07-03T09:00:00Z"},
                {"system": "PROD", "status": "success", "imported_at": "2026-07-05T06:00:00Z"},
            ],
            "_priority": "high",
            "_sod_impact": True,
            "_affected_users": 42,
            "_created_at": datetime(2026, 7, 1, 8, 0, 0),
        },
        {
            "transport_id": "DEV900002",
            "description": "New procurement role for MM module",
            "source_system": "DEV",
            "target_system": "QA",
            "status": "imported_qa",
            "category": "role",
            "objects": ["Z:MM_PO_CREATOR", "Z:MM_PO_APPROVER"],
            "dependencies": ["DEV900001"],
            "conflicts": [],
            "owner": "role_designer",
            "released_at": datetime(2026, 7, 6, 14, 0, 0),
            "imported_at": datetime(2026, 7, 7, 8, 30, 0),
            "error_message": None,
            "_imports": [
                {"system": "QA", "status": "success", "imported_at": "2026-07-07T08:30:00Z"},
            ],
            "_priority": "medium",
            "_sod_impact": True,
            "_affected_users": 18,
            "_created_at": datetime(2026, 7, 5, 11, 0, 0),
        },
        {
            "transport_id": "DEV900003",
            "description": "HR payroll role restriction - limit payroll execution",
            "source_system": "DEV",
            "target_system": "PROD",
            "status": "created",
            "category": "role",
            "objects": ["Z:HR_PAYROLL_EXEC"],
            "dependencies": [],
            "conflicts": [],
            "owner": "hr_basis",
            "released_at": None,
            "imported_at": None,
            "error_message": None,
            "_imports": [],
            "_priority": "critical",
            "_sod_impact": True,
            "_affected_users": 5,
            "_created_at": datetime(2026, 7, 8, 9, 0, 0),
        },
        {
            "transport_id": "DEV900004",
            "description": "SD sales order role - new authorization values",
            "source_system": "DEV",
            "target_system": "QA",
            "status": "failed",
            "category": "role",
            "objects": ["Z:SD_ORDER_CREATOR"],
            "dependencies": [],
            "conflicts": [],
            "owner": "basis_admin",
            "released_at": datetime(2026, 7, 11, 9, 0, 0),
            "imported_at": None,
            "error_message": "Authorization object S_CARRID not found in QA",
            "_imports": [
                {"system": "QA", "status": "failed", "imported_at": "2026-07-12T10:00:00Z",
                 "error": "Authorization object S_CARRID not found in QA"},
            ],
            "_priority": "medium",
            "_sod_impact": False,
            "_affected_users": 23,
            "_created_at": datetime(2026, 7, 10, 7, 0, 0),
        },
        {
            "transport_id": "DEV900005",
            "description": "Basis role for background processing",
            "source_system": "DEV",
            "target_system": "PROD",
            "status": "imported_prod",
            "category": "role",
            "objects": ["Z:BC_JOB_ADMIN"],
            "dependencies": [],
            "conflicts": [],
            "owner": "basis_admin",
            "released_at": datetime(2026, 7, 13, 12, 0, 0),
            "imported_at": datetime(2026, 7, 16, 5, 30, 0),
            "error_message": None,
            "_imports": [
                {"system": "QA",   "status": "success", "imported_at": "2026-07-14T08:00:00Z"},
                {"system": "PROD", "status": "success", "imported_at": "2026-07-16T05:30:00Z"},
            ],
            "_priority": "low",
            "_sod_impact": False,
            "_affected_users": 3,
            "_created_at": datetime(2026, 7, 12, 8, 0, 0),
        },
        {
            "transport_id": "DEV900006",
            "description": "Treasury role - bank account management",
            "source_system": "DEV",
            "target_system": "QA",
            "status": "imported_qa",
            "category": "role",
            "objects": ["Z:FI_BANK_MANAGER", "Z:FI_TREASURY_VIEWER"],
            "dependencies": ["DEV900001", "DEV900002"],
            "conflicts": [],
            "owner": "fi_security",
            "released_at": datetime(2026, 7, 16, 11, 0, 0),
            "imported_at": datetime(2026, 7, 17, 9, 30, 0),
            "error_message": None,
            "_imports": [
                {"system": "QA", "status": "success", "imported_at": "2026-07-17T09:30:00Z"},
            ],
            "_priority": "critical",
            "_sod_impact": True,
            "_affected_users": 8,
            "_created_at": datetime(2026, 7, 15, 10, 0, 0),
        },
        {
            "transport_id": "DEV900007",
            "description": "Rolled back - vendor creation role caused SoD conflict",
            "source_system": "DEV",
            "target_system": "PROD",
            "status": "rolled_back",
            "category": "role",
            "objects": ["Z:MM_VENDOR_CREATOR"],
            "dependencies": [],
            "conflicts": [],
            "owner": "basis_admin",
            "released_at": datetime(2026, 7, 18, 14, 0, 0),
            "imported_at": datetime(2026, 7, 20, 6, 0, 0),
            "error_message": "SoD violation detected post-import: FI-MM conflict",
            "_imports": [
                {"system": "QA",   "status": "success",     "imported_at": "2026-07-19T08:00:00Z"},
                {"system": "PROD", "status": "rolled_back",  "imported_at": "2026-07-20T06:00:00Z",
                 "error": "SoD violation detected post-import: FI-MM conflict"},
            ],
            "_priority": "high",
            "_sod_impact": True,
            "_affected_users": 12,
            "_created_at": datetime(2026, 7, 18, 9, 0, 0),
        },
        {
            "transport_id": "DEV900008",
            "description": "CO cost center reporting role",
            "source_system": "DEV",
            "target_system": "PROD",
            "status": "imported_prod",
            "category": "role",
            "objects": ["Z:CO_CC_REPORTER"],
            "dependencies": [],
            "conflicts": [],
            "owner": "co_team",
            "released_at": datetime(2026, 7, 21, 9, 0, 0),
            "imported_at": datetime(2026, 7, 24, 5, 30, 0),
            "error_message": None,
            "_imports": [
                {"system": "QA",   "status": "success", "imported_at": "2026-07-22T08:00:00Z"},
                {"system": "PROD", "status": "success", "imported_at": "2026-07-24T05:30:00Z"},
            ],
            "_priority": "low",
            "_sod_impact": False,
            "_affected_users": 67,
            "_created_at": datetime(2026, 7, 20, 11, 0, 0),
        },
        {
            "transport_id": "DEV900009",
            "description": "Plant maintenance role - work order creation",
            "source_system": "DEV",
            "target_system": "QA",
            "status": "imported_qa",
            "category": "role",
            "objects": ["Z:PM_WO_CREATOR", "Z:PM_WO_APPROVER"],
            "dependencies": ["DEV900005"],
            "conflicts": [],
            "owner": "pm_admin",
            "released_at": datetime(2026, 7, 23, 10, 0, 0),
            "imported_at": datetime(2026, 7, 24, 9, 30, 0),
            "error_message": None,
            "_imports": [
                {"system": "QA", "status": "success", "imported_at": "2026-07-24T09:30:00Z"},
            ],
            "_priority": "medium",
            "_sod_impact": False,
            "_affected_users": 34,
            "_created_at": datetime(2026, 7, 22, 8, 0, 0),
        },
        {
            "transport_id": "DEV900010",
            "description": "QM quality inspection role update",
            "source_system": "DEV",
            "target_system": "PROD",
            "status": "created",
            "category": "role",
            "objects": ["Z:QM_INSPECTOR"],
            "dependencies": ["DEV900009"],
            "conflicts": [],
            "owner": "qm_basis",
            "released_at": None,
            "imported_at": None,
            "error_message": None,
            "_imports": [],
            "_priority": "low",
            "_sod_impact": False,
            "_affected_users": 15,
            "_created_at": datetime(2026, 7, 25, 9, 0, 0),
        },
        {
            "transport_id": "DEV900011",
            "description": "GRC role for risk analysts",
            "source_system": "DEV",
            "target_system": "QA",
            "status": "failed",
            "category": "role",
            "objects": ["Z:GRC_RISK_ANALYST"],
            "dependencies": ["DEV900006"],
            "conflicts": [],
            "owner": "grc_admin",
            "released_at": datetime(2026, 7, 29, 11, 0, 0),
            "imported_at": None,
            "error_message": "Transport prerequisite DEV900006 not yet imported into QA",
            "_imports": [
                {"system": "QA", "status": "failed", "imported_at": "2026-07-30T09:00:00Z",
                 "error": "Transport prerequisite DEV900006 not yet imported into QA"},
            ],
            "_priority": "high",
            "_sod_impact": False,
            "_affected_users": 7,
            "_created_at": datetime(2026, 7, 28, 10, 0, 0),
        },
        {
            "transport_id": "DEV900012",
            "description": "Emergency access firefighter role",
            "source_system": "DEV",
            "target_system": "PROD",
            "status": "imported_prod",
            "category": "role",
            "objects": ["Z:EAM_FIREFIGHTER"],
            "dependencies": [],
            "conflicts": [],
            "owner": "security_admin",
            "released_at": datetime(2026, 8, 1, 10, 0, 0),
            "imported_at": datetime(2026, 8, 3, 5, 0, 0),
            "error_message": None,
            "_imports": [
                {"system": "QA",   "status": "success", "imported_at": "2026-08-02T09:00:00Z"},
                {"system": "PROD", "status": "success", "imported_at": "2026-08-03T05:00:00Z"},
            ],
            "_priority": "critical",
            "_sod_impact": True,
            "_affected_users": 2,
            "_created_at": datetime(2026, 8, 1, 8, 0, 0),
        },
        {
            "transport_id": "DEV900013",
            "description": "PP production planner role",
            "source_system": "DEV",
            "target_system": "QA",
            "status": "imported_qa",
            "category": "role",
            "objects": ["Z:PP_PLANNER", "Z:PP_VIEWER"],
            "dependencies": [],
            "conflicts": [],
            "owner": "pp_admin",
            "released_at": datetime(2026, 8, 6, 10, 0, 0),
            "imported_at": datetime(2026, 8, 7, 9, 30, 0),
            "error_message": None,
            "_imports": [
                {"system": "QA", "status": "success", "imported_at": "2026-08-07T09:30:00Z"},
            ],
            "_priority": "medium",
            "_sod_impact": False,
            "_affected_users": 28,
            "_created_at": datetime(2026, 8, 5, 9, 0, 0),
        },
        {
            "transport_id": "DEV900014",
            "description": "Audit read-only role for external auditors",
            "source_system": "DEV",
            "target_system": "PROD",
            "status": "created",
            "category": "role",
            "objects": ["Z:AUDIT_READONLY"],
            "dependencies": ["DEV900011", "DEV900012"],
            "conflicts": [],
            "owner": "grc_admin",
            "released_at": None,
            "imported_at": None,
            "error_message": None,
            "_imports": [],
            "_priority": "high",
            "_sod_impact": False,
            "_affected_users": 4,
            "_created_at": datetime(2026, 8, 10, 11, 0, 0),
        },
        {
            "transport_id": "DEV900015",
            "description": "CRM opportunity management role",
            "source_system": "DEV",
            "target_system": "QA",
            "status": "imported_qa",
            "category": "role",
            "objects": ["Z:CRM_OPP_MANAGER"],
            "dependencies": [],
            "conflicts": [],
            "owner": "crm_admin",
            "released_at": datetime(2026, 8, 13, 11, 0, 0),
            "imported_at": datetime(2026, 8, 14, 9, 0, 0),
            "error_message": None,
            "_imports": [
                {"system": "QA", "status": "success", "imported_at": "2026-08-14T09:00:00Z"},
            ],
            "_priority": "medium",
            "_sod_impact": False,
            "_affected_users": 19,
            "_created_at": datetime(2026, 8, 12, 9, 0, 0),
        },
        {
            "transport_id": "DEV900016",
            "description": "S/4HANA Fiori tile group for AP clerks",
            "source_system": "DEV",
            "target_system": "QA",
            "status": "imported_qa",
            "category": "role",
            "objects": ["Z:FI_AP_FIORI_GROUP"],
            "dependencies": ["DEV900001"],
            "conflicts": [],
            "owner": "basis_admin",
            "released_at": datetime(2026, 8, 16, 9, 0, 0),
            "imported_at": datetime(2026, 8, 17, 9, 0, 0),
            "error_message": None,
            "_imports": [
                {"system": "QA", "status": "success", "imported_at": "2026-08-17T09:00:00Z"},
            ],
            "_priority": "medium",
            "_sod_impact": False,
            "_affected_users": 42,
            "_created_at": datetime(2026, 8, 15, 8, 0, 0),
        },
    ]


# State ordering for lifecycle tracking
_STATE_ORDER = [
    "created",
    "released",
    "imported_qa",
    "imported_prod",
]

_TERMINAL_STATES = {"failed", "rolled_back"}

_PROD_STATE = "imported_prod"


# ---------------------------------------------------------------------------
# Helper: convert a DB row to the in-memory dict shape used by business logic
# ---------------------------------------------------------------------------

def _row_to_dict(row: TransportRecord) -> Dict[str, Any]:
    """
    Convert a TransportRecord ORM row to the flat dict shape that the
    business logic (dependency checking, conflict detection, etc.) operates on.

    The `objects` JSON column stores role names.
    The `dependencies` JSON column stores depends_on transport IDs.
    The `conflicts` JSON column stores detected conflict dicts.

    Extra per-transport metadata (_imports, _priority, _sod_impact,
    _affected_users, _created_at) is stored in the `objects` JSON column
    as a sub-key when present, or falls back to sensible defaults.
    """
    objects = row.objects or {}
    if isinstance(objects, list):
        # Legacy format: objects is just a list of role names
        roles = objects
        imports = []
        priority = "medium"
        sod_impact = False
        affected_users = 0
        created_at = row.created_at.isoformat() + "Z" if row.created_at else datetime.utcnow().isoformat() + "Z"
    else:
        # Extended format stored as dict
        roles = objects.get("roles", [])
        imports = objects.get("imports", [])
        priority = objects.get("priority", "medium")
        sod_impact = objects.get("sod_impact", False)
        affected_users = objects.get("affected_users", 0)
        created_at_raw = objects.get("created_at")
        if created_at_raw:
            created_at = created_at_raw
        else:
            created_at = row.created_at.isoformat() + "Z" if row.created_at else datetime.utcnow().isoformat() + "Z"

    return {
        "transport_id":   row.transport_id,
        "description":    row.description,
        "roles":          roles,
        "source_system":  row.source_system,
        "owner":          row.owner,
        "created_at":     created_at,
        "released_at":    row.released_at.isoformat() + "Z" if row.released_at else None,
        "state":          row.status,
        "imports":        imports,
        "depends_on":     row.dependencies or [],
        "priority":       priority,
        "sod_impact":     sod_impact,
        "affected_users": affected_users,
    }


def _build_objects_payload(
    roles: List[str],
    imports: List[Dict[str, Any]],
    priority: str,
    sod_impact: bool,
    affected_users: int,
    created_at: str,
) -> Dict[str, Any]:
    """Pack per-transport metadata into the `objects` JSON column."""
    return {
        "roles":          roles,
        "imports":        imports,
        "priority":       priority,
        "sod_impact":     sod_impact,
        "affected_users": affected_users,
        "created_at":     created_at,
    }


class TransportManager:
    """
    Manages SAP transport lifecycle tracking for role changes.

    Data is persisted in the TransportRecord DB table.  Default seed data is
    written on first access when the table is empty (_ensure_loaded pattern).
    All dependency checking and conflict detection business logic is unchanged.
    """

    def __init__(self, tenant_id: str = "tenant_default") -> None:
        self._tenant_id = tenant_id
        self._loaded = False

    # ------------------------------------------------------------------
    # Lazy-load / seed
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Seed DB with default transport records on first access if empty."""
        if self._loaded:
            return
        self._loaded = True

        if not db_manager._initialized:
            db_manager.init()
            db_manager.create_tables()

        with db_manager.session_scope() as session:
            count = session.query(TransportRecord).filter_by(
                tenant_id=self._tenant_id
            ).count()
            if count == 0:
                for t in _default_transports():
                    objects_payload = _build_objects_payload(
                        roles=t["objects"],
                        imports=t.get("_imports", []),
                        priority=t.get("_priority", "medium"),
                        sod_impact=t.get("_sod_impact", False),
                        affected_users=t.get("_affected_users", 0),
                        created_at=t["_created_at"].isoformat() + "Z",
                    )
                    row = TransportRecord(
                        tenant_id=self._tenant_id,
                        transport_id=t["transport_id"],
                        description=t["description"],
                        source_system=t["source_system"],
                        target_system=t["target_system"],
                        status=t["status"],
                        category=t["category"],
                        objects=objects_payload,
                        dependencies=t["dependencies"],
                        conflicts=t["conflicts"],
                        owner=t["owner"],
                        released_at=t["released_at"],
                        imported_at=t["imported_at"],
                        error_message=t["error_message"],
                    )
                    # Override created_at if possible
                    row.created_at = t["_created_at"]
                    session.add(row)

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _all_rows(self) -> List[Dict[str, Any]]:
        """Fetch all transport records for this tenant as dicts."""
        self._ensure_loaded()
        with db_manager.session_scope() as session:
            rows = session.query(TransportRecord).filter_by(
                tenant_id=self._tenant_id
            ).order_by(TransportRecord.id).all()
            for r in rows:
                session.expunge(r)
        return [_row_to_dict(r) for r in rows]

    def _find_row(self, transport_id: str) -> Optional[TransportRecord]:
        """Return the raw ORM row (expunged) or None."""
        self._ensure_loaded()
        with db_manager.session_scope() as session:
            row = session.query(TransportRecord).filter_by(
                transport_id=transport_id,
                tenant_id=self._tenant_id,
            ).first()
            if row:
                session.expunge(row)
            return row

    def _find(self, transport_id: str) -> Optional[Dict[str, Any]]:
        """Return the transport as a dict or None."""
        row = self._find_row(transport_id)
        if row is None:
            return None
        return _row_to_dict(row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_transport(
        self,
        transport_id: str,
        description: str,
        roles: List[str],
        source_system: str,
        owner: str = "basis_admin",
        depends_on: Optional[List[str]] = None,
        priority: str = "medium",
    ) -> Dict[str, Any]:
        """Register a new transport in the system."""
        self._ensure_loaded()
        if self._find(transport_id) is not None:
            raise ValueError(f"Transport {transport_id} already exists")

        now_str = datetime.utcnow().isoformat() + "Z"
        objects_payload = _build_objects_payload(
            roles=roles,
            imports=[],
            priority=priority,
            sod_impact=False,
            affected_users=0,
            created_at=now_str,
        )

        with db_manager.session_scope() as session:
            row = TransportRecord(
                tenant_id=self._tenant_id,
                transport_id=transport_id,
                description=description,
                source_system=source_system,
                target_system="PROD",
                status="created",
                category="role",
                objects=objects_payload,
                dependencies=depends_on or [],
                conflicts=[],
                owner=owner,
                released_at=None,
                imported_at=None,
                error_message=None,
            )
            session.add(row)
            session.flush()
            session.expunge(row)

        return self._find(transport_id)

    def track_import(
        self,
        transport_id: str,
        target_system: str,
        status: str,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record a transport import event.

        target_system: QA | PROD
        status: success | failed | rolled_back
        """
        self._ensure_loaded()
        row = self._find_row(transport_id)
        if row is None:
            raise ValueError(f"Transport {transport_id} not found")

        target_upper = target_system.upper()
        import_record: Dict[str, Any] = {
            "system": target_upper,
            "status": status,
            "imported_at": datetime.utcnow().isoformat() + "Z",
        }
        if error:
            import_record["error"] = error

        # Load current objects payload and update imports list
        objects = row.objects if isinstance(row.objects, dict) else {}
        existing_imports = [
            imp for imp in objects.get("imports", [])
            if imp["system"] != target_upper
        ]
        existing_imports.append(import_record)
        objects["imports"] = existing_imports

        # Determine new state
        if status == "success":
            if target_upper == "QA":
                new_state = "imported_qa"
            elif target_upper == "PROD":
                new_state = "imported_prod"
            else:
                new_state = row.status
        elif status == "failed":
            new_state = "failed"
        elif status == "rolled_back":
            new_state = "rolled_back"
        else:
            new_state = row.status

        now = datetime.utcnow()
        error_msg = error if error else row.error_message

        with db_manager.session_scope() as session:
            session.query(TransportRecord).filter_by(
                transport_id=transport_id,
                tenant_id=self._tenant_id,
            ).update({
                "status": new_state,
                "objects": objects,
                "imported_at": now if status == "success" else row.imported_at,
                "error_message": error_msg,
            })

        return self._find(transport_id)

    def get_transport_chain(self, transport_id: str) -> Dict[str, Any]:
        """Return the full lifecycle of a transport as an ordered chain of events."""
        transport = self._find(transport_id)
        if transport is None:
            raise ValueError(f"Transport {transport_id} not found")

        events: List[Dict[str, Any]] = []

        events.append({
            "step": 1,
            "stage": "created",
            "system": transport["source_system"],
            "timestamp": transport["created_at"],
            "status": "complete",
            "details": f"Transport registered: {transport['description']}",
        })

        if transport.get("released_at"):
            events.append({
                "step": 2,
                "stage": "released",
                "system": transport["source_system"],
                "timestamp": transport["released_at"],
                "status": "complete",
                "details": "Released to transport queue",
            })
        elif transport["state"] != "created":
            events.append({
                "step": 2,
                "stage": "released",
                "system": transport["source_system"],
                "timestamp": None,
                "status": "pending",
                "details": "Not yet released",
            })

        for imp in sorted(transport["imports"], key=lambda x: x.get("imported_at", "")):
            step_num = 3 if imp["system"] == "QA" else 4
            events.append({
                "step": step_num,
                "stage": f"imported_{imp['system'].lower()}",
                "system": imp["system"],
                "timestamp": imp.get("imported_at"),
                "status": imp["status"],
                "details": imp.get("error", f"Imported into {imp['system']}"),
            })

        return {
            "transport_id": transport_id,
            "description": transport["description"],
            "current_state": transport["state"],
            "chain": sorted(events, key=lambda e: e["step"]),
            "roles": transport["roles"],
            "depends_on": transport["depends_on"],
        }

    def get_pending_transports(self) -> List[Dict[str, Any]]:
        """Return transports that have not yet reached PROD and are not terminal."""
        all_transports = self._all_rows()
        pending = []
        for t in all_transports:
            if t["state"] not in (_PROD_STATE, "rolled_back"):
                age_days = self._age_days(t["created_at"])
                entry = {**t, "age_days": age_days}
                pending.append(entry)
        return sorted(pending, key=lambda x: self._priority_order(x["priority"]))

    def get_transport_history(
        self,
        role_id: Optional[str] = None,
        system: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Return transport history with optional filters.

        role_id: filter by role name (substring match)
        system: filter by source_system
        state: filter by state
        """
        results = self._all_rows()

        if role_id:
            role_lower = role_id.lower()
            results = [
                t for t in results
                if any(role_lower in r.lower() for r in t.get("roles", []))
            ]

        if system:
            sys_upper = system.upper()
            results = [t for t in results if t["source_system"].upper() == sys_upper]

        if state:
            results = [t for t in results if t["state"] == state]

        return results[:limit]

    def check_dependencies(self, transport_id: str) -> Dict[str, Any]:
        """
        Check whether all dependent transports are imported into PROD before
        this one should proceed.
        """
        transport = self._find(transport_id)
        if transport is None:
            raise ValueError(f"Transport {transport_id} not found")

        deps = transport.get("depends_on", [])
        missing: List[str] = []
        not_in_prod: List[Dict[str, str]] = []
        satisfied: List[str] = []

        for dep_id in deps:
            dep = self._find(dep_id)
            if dep is None:
                missing.append(dep_id)
            elif dep["state"] != _PROD_STATE:
                not_in_prod.append({"transport_id": dep_id, "current_state": dep["state"]})
            else:
                satisfied.append(dep_id)

        all_clear = len(missing) == 0 and len(not_in_prod) == 0

        return {
            "transport_id": transport_id,
            "dependencies": deps,
            "satisfied": satisfied,
            "missing_transports": missing,
            "not_yet_in_prod": not_in_prod,
            "all_dependencies_met": all_clear,
            "recommendation": (
                "Safe to proceed" if all_clear
                else "Resolve dependencies before importing to PROD"
            ),
        }

    def detect_conflicts(self, transport_id: str) -> Dict[str, Any]:
        """
        Detect whether this transport conflicts with other transports that
        touch the same roles or are currently in-flight.
        """
        transport = self._find(transport_id)
        if transport is None:
            raise ValueError(f"Transport {transport_id} not found")

        target_roles = set(transport.get("roles", []))
        conflicts: List[Dict[str, Any]] = []
        in_flight_states = {"released", "imported_qa"}

        for other in self._all_rows():
            if other["transport_id"] == transport_id:
                continue
            other_roles = set(other.get("roles", []))
            overlap = target_roles & other_roles
            if overlap and other["state"] in in_flight_states:
                conflicts.append({
                    "conflicting_transport": other["transport_id"],
                    "state": other["state"],
                    "shared_roles": list(overlap),
                    "description": other["description"],
                    "risk": "Role modified by multiple in-flight transports",
                })

        return {
            "transport_id": transport_id,
            "roles": list(target_roles),
            "conflicts_found": len(conflicts) > 0,
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
            "recommendation": (
                "No conflicts detected" if not conflicts
                else f"{len(conflicts)} conflict(s) found — coordinate with transport owners"
            ),
        }

    def get_dashboard(self) -> Dict[str, Any]:
        """Return overview statistics for the transport dashboard."""
        all_transports = self._all_rows()
        state_counts: Dict[str, int] = {}
        for t in all_transports:
            state_counts[t["state"]] = state_counts.get(t["state"], 0) + 1

        pending = self.get_pending_transports()
        failed = [t for t in all_transports if t["state"] == "failed"]
        critical_pending = [t for t in pending if t["priority"] == "critical"]
        sod_impacted = [t for t in pending if t.get("sod_impact")]

        return {
            "total_transports": len(all_transports),
            "state_breakdown": state_counts,
            "pending_count": len(pending),
            "failed_count": len(failed),
            "rolled_back_count": state_counts.get("rolled_back", 0),
            "in_prod_count": state_counts.get("imported_prod", 0),
            "critical_pending": len(critical_pending),
            "sod_impacted_pending": len(sod_impacted),
            "oldest_pending_days": (
                max((t.get("age_days", 0) for t in pending), default=0)
            ),
            "recent_failures": [
                {
                    "transport_id": t["transport_id"],
                    "description": t["description"],
                    "last_error": next(
                        (imp.get("error") for imp in reversed(t["imports"])
                         if imp["status"] in ("failed", "rolled_back")),
                        None,
                    ),
                }
                for t in failed[:5]
            ],
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _age_days(created_at: str) -> int:
        try:
            dt = datetime.fromisoformat(created_at.rstrip("Z"))
            return (datetime.utcnow() - dt).days
        except Exception:
            return 0

    @staticmethod
    def _priority_order(priority: str) -> int:
        return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(priority, 99)


# Module-level singleton for router use
_manager: Optional[TransportManager] = None


def get_transport_manager() -> TransportManager:
    global _manager
    if _manager is None:
        _manager = TransportManager()
    return _manager
