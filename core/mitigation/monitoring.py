"""
Mitigation Validity Monitoring Engine

Background job service that continuously monitors the health of mitigation
controls: expirations, unassigned violations, and control effectiveness.
Integrates with the notification delivery engine to send alerts when issues
are detected.

Data is persisted in the database via MitigationMonitorRecord (operations.py)
and RiskViolation (risk.py).  On first access the tables are seeded with
demonstration data if they are empty (_ensure_seeded).
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from core.logging import get_logger
from db.database import db_manager
from db.models.operations import MitigationMonitorRecord
from db.models.risk import MitigationControl, RiskViolation

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MitigationState(str, Enum):
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"   # Within warning window
    EXPIRED = "expired"
    INEFFECTIVE = "ineffective"
    UNASSIGNED = "unassigned"         # No control covering this violation


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    EXPIRING = "expiring"
    EXPIRED = "expired"
    UNASSIGNED_VIOLATION = "unassigned_violation"
    INEFFECTIVE_CONTROL = "ineffective_control"


# ---------------------------------------------------------------------------
# Data classes (response DTOs -- unchanged)
# ---------------------------------------------------------------------------

@dataclass
class MitigationRecord:
    """A single mitigation control assignment covering one or more violations."""
    mitigation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    control_name: str = ""
    control_type: str = "detective"
    owner_id: str = ""
    owner_name: str = ""
    risk_id: str = ""
    violation_ids: List[str] = field(default_factory=list)
    valid_from: datetime = field(default_factory=datetime.utcnow)
    valid_to: Optional[datetime] = None
    effectiveness_score: float = 75.0   # 0-100
    last_reviewed: Optional[datetime] = None
    state: MitigationState = MitigationState.ACTIVE
    notes: str = ""

    def days_until_expiry(self) -> Optional[int]:
        if not self.valid_to:
            return None
        delta = self.valid_to - datetime.utcnow()
        return delta.days

    def is_expired(self) -> bool:
        return self.valid_to is not None and self.valid_to < datetime.utcnow()

    def is_expiring(self, days_ahead: int = 30) -> bool:
        if self.valid_to is None:
            return False
        remaining = self.days_until_expiry()
        return remaining is not None and 0 <= remaining <= days_ahead

    def is_ineffective(self, threshold: float = 50.0) -> bool:
        return self.effectiveness_score < threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mitigation_id": self.mitigation_id,
            "control_name": self.control_name,
            "control_type": self.control_type,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "risk_id": self.risk_id,
            "violation_ids": self.violation_ids,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "days_until_expiry": self.days_until_expiry(),
            "effectiveness_score": self.effectiveness_score,
            "last_reviewed": self.last_reviewed.isoformat() if self.last_reviewed else None,
            "state": self.state.value,
            "notes": self.notes,
        }


@dataclass
class ViolationRecord:
    """An unmitigated SoD or risk violation."""
    violation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    rule_name: str = ""
    user_id: str = ""
    user_name: str = ""
    risk_level: str = "medium"
    detected_at: datetime = field(default_factory=datetime.utcnow)
    mitigation_id: Optional[str] = None   # None => unassigned
    system: str = "SAP ECC"
    functions_in_conflict: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "rule_name": self.rule_name,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "risk_level": self.risk_level,
            "detected_at": self.detected_at.isoformat(),
            "mitigation_id": self.mitigation_id,
            "system": self.system,
            "functions_in_conflict": self.functions_in_conflict,
            "is_mitigated": self.mitigation_id is not None,
        }


@dataclass
class MitigationAlert:
    """An alert generated by the monitoring engine."""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    alert_type: AlertType = AlertType.EXPIRING
    severity: AlertSeverity = AlertSeverity.WARNING
    title: str = ""
    message: str = ""
    mitigation_id: Optional[str] = None
    violation_id: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "mitigation_id": self.mitigation_id,
            "violation_id": self.violation_id,
            "generated_at": self.generated_at.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }


@dataclass
class MitigationHealthReport:
    """Full health report produced by run_full_check()."""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: datetime = field(default_factory=datetime.utcnow)
    expiring_count: int = 0
    expired_count: int = 0
    unassigned_count: int = 0
    ineffective_count: int = 0
    total_active: int = 0
    alerts_generated: int = 0
    expiring: List[Dict[str, Any]] = field(default_factory=list)
    expired: List[Dict[str, Any]] = field(default_factory=list)
    unassigned_violations: List[Dict[str, Any]] = field(default_factory=list)
    ineffective: List[Dict[str, Any]] = field(default_factory=list)
    alerts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "summary": {
                "total_active": self.total_active,
                "expiring_count": self.expiring_count,
                "expired_count": self.expired_count,
                "unassigned_count": self.unassigned_count,
                "ineffective_count": self.ineffective_count,
                "alerts_generated": self.alerts_generated,
                "health_score": self._health_score(),
            },
            "expiring": self.expiring,
            "expired": self.expired,
            "unassigned_violations": self.unassigned_violations,
            "ineffective": self.ineffective,
            "alerts": self.alerts,
        }

    def _health_score(self) -> float:
        """
        Simple health score: 100 minus weighted penalties for each issue type.
        Range 0-100; 100 means fully healthy.
        """
        if self.total_active == 0:
            return 100.0
        penalty = (
            self.expiring_count * 5
            + self.expired_count * 20
            + self.unassigned_count * 15
            + self.ineffective_count * 10
        )
        return max(0.0, round(100.0 - penalty, 1))


# ---------------------------------------------------------------------------
# DB seeding -- lazy pattern
# ---------------------------------------------------------------------------

_seeded = False
_seed_lock = threading.Lock()


def _db_record_to_mitigation(row: MitigationMonitorRecord) -> MitigationRecord:
    """Convert a DB MitigationMonitorRecord row to a MitigationRecord DTO."""
    # Map DB status string to MitigationState enum
    try:
        state = MitigationState(row.status)
    except ValueError:
        state = MitigationState.ACTIVE

    return MitigationRecord(
        mitigation_id=row.monitor_id,
        control_name=row.control_name,
        control_type=row.control_type,
        owner_id=row.owner,
        owner_name=row.reviewed_by or row.owner,  # best available name
        risk_id=row.control_id,
        violation_ids=[],  # populated separately if needed
        valid_from=row.created_at or datetime.utcnow(),
        valid_to=row.expiry_date,
        effectiveness_score=float(row.health_score),
        last_reviewed=row.last_reviewed,
        state=state,
        notes="",
    )


def _ensure_seeded() -> None:
    """
    Check whether the mitigation_monitor table has data.
    If empty, insert all seed records.  Uses a module-level flag
    so the check runs at most once per process.
    """
    global _seeded
    if _seeded:
        return

    with _seed_lock:
        if _seeded:
            return

        try:
            with db_manager.session_scope() as session:
                count = session.query(func.count(MitigationMonitorRecord.id)).scalar()
                if count and count > 0:
                    _seeded = True
                    return

            # -- Seed mitigation monitor records --
            _now = datetime.utcnow()
            seed_mitigations = [
                MitigationMonitorRecord(
                    tenant_id="tenant_default",
                    monitor_id="MIT-001",
                    control_id="RISK-AP-001",
                    control_name="AP Payment Dual Approval",
                    control_type="approval",
                    status="expiring_soon",
                    health_score=88,
                    assigned_violations=1,
                    expiry_date=_now + timedelta(days=5),
                    last_reviewed=_now - timedelta(days=30),
                    reviewed_by="Emma Johnson",
                    owner="U010",
                ),
                MitigationMonitorRecord(
                    tenant_id="tenant_default",
                    monitor_id="MIT-002",
                    control_id="RISK-GL-002",
                    control_name="GL Posting Monthly Reconciliation",
                    control_type="detective",
                    status="expiring_soon",
                    health_score=76,
                    assigned_violations=2,
                    expiry_date=_now + timedelta(days=20),
                    last_reviewed=_now - timedelta(days=60),
                    reviewed_by="Robert Chen",
                    owner="U011",
                ),
                MitigationMonitorRecord(
                    tenant_id="tenant_default",
                    monitor_id="MIT-003",
                    control_id="RISK-BANK-001",
                    control_name="Bank Master Data Change Log Review",
                    control_type="monitoring",
                    status="expired",
                    health_score=90,
                    assigned_violations=1,
                    expiry_date=_now - timedelta(days=15),
                    last_reviewed=_now - timedelta(days=45),
                    reviewed_by="Aisha Nwosu",
                    owner="U012",
                ),
                MitigationMonitorRecord(
                    tenant_id="tenant_default",
                    monitor_id="MIT-004",
                    control_id="RISK-IA-001",
                    control_name="User Admin Weekly Activity Review",
                    control_type="review",
                    status="expired",
                    health_score=55,
                    assigned_violations=1,
                    expiry_date=_now - timedelta(days=60),
                    last_reviewed=_now - timedelta(days=75),
                    reviewed_by="David Park",
                    owner="U013",
                ),
                MitigationMonitorRecord(
                    tenant_id="tenant_default",
                    monitor_id="MIT-005",
                    control_id="RISK-HR-001",
                    control_name="Payroll Change Exception Report",
                    control_type="detective",
                    status="ineffective",
                    health_score=38,
                    assigned_violations=1,
                    expiry_date=_now + timedelta(days=90),
                    last_reviewed=_now - timedelta(days=10),
                    reviewed_by="Sandra Torres",
                    owner="U014",
                ),
                MitigationMonitorRecord(
                    tenant_id="tenant_default",
                    monitor_id="MIT-006",
                    control_id="RISK-AP-002",
                    control_name="Vendor Master Segregation Policy",
                    control_type="preventive",
                    status="active",
                    health_score=92,
                    assigned_violations=2,
                    expiry_date=_now + timedelta(days=180),
                    last_reviewed=_now - timedelta(days=15),
                    reviewed_by="James Nakamura",
                    owner="U015",
                ),
                MitigationMonitorRecord(
                    tenant_id="tenant_default",
                    monitor_id="MIT-007",
                    control_id="RISK-IT-001",
                    control_name="Transport Release Dual Sign-Off",
                    control_type="approval",
                    status="expiring_soon",
                    health_score=84,
                    assigned_violations=1,
                    expiry_date=_now + timedelta(days=25),
                    last_reviewed=_now - timedelta(days=5),
                    reviewed_by="Marie Leclerc",
                    owner="U016",
                ),
                MitigationMonitorRecord(
                    tenant_id="tenant_default",
                    monitor_id="MIT-008",
                    control_id="RISK-SOD-001",
                    control_name="Automated SoD Conflict Alert",
                    control_type="automated",
                    status="active",
                    health_score=95,
                    assigned_violations=1,
                    expiry_date=None,
                    last_reviewed=_now - timedelta(days=7),
                    reviewed_by="Kevin Walsh",
                    owner="U017",
                ),
                MitigationMonitorRecord(
                    tenant_id="tenant_default",
                    monitor_id="MIT-009",
                    control_id="RISK-IA-002",
                    control_name="Periodic Access Recertification",
                    control_type="review",
                    status="active",
                    health_score=71,
                    assigned_violations=2,
                    expiry_date=_now + timedelta(days=120),
                    last_reviewed=_now - timedelta(days=30),
                    reviewed_by="Fatima Al-Hassan",
                    owner="U018",
                ),
                MitigationMonitorRecord(
                    tenant_id="tenant_default",
                    monitor_id="MIT-010",
                    control_id="RISK-BASIS-001",
                    control_name="Critical System Access Log Audit",
                    control_type="monitoring",
                    status="expired",
                    health_score=80,
                    assigned_violations=1,
                    expiry_date=_now - timedelta(days=1),
                    last_reviewed=_now - timedelta(days=11),
                    reviewed_by="Paulo Ferreira",
                    owner="U019",
                ),
                MitigationMonitorRecord(
                    tenant_id="tenant_default",
                    monitor_id="MIT-011",
                    control_id="RISK-SOD-002",
                    control_name="Segregation of Duties Policy Attestation",
                    control_type="review",
                    status="ineffective",
                    health_score=44,
                    assigned_violations=0,
                    expiry_date=_now + timedelta(days=60),
                    last_reviewed=_now - timedelta(days=200),
                    reviewed_by="Ingrid Johansson",
                    owner="U020",
                ),
            ]

            with db_manager.session_scope() as session:
                session.add_all(seed_mitigations)

            logger.info("monitor.seed_complete", mitigation_count=len(seed_mitigations))
            _seeded = True

        except Exception:
            logger.error("monitor.seed_failed", exc_info=True)
            # Mark seeded anyway to avoid repeated failures blocking the app
            _seeded = True


# ---------------------------------------------------------------------------
# DB helper: load all monitor records as MitigationRecord DTOs
# ---------------------------------------------------------------------------

def _load_mitigations_from_db() -> List[MitigationRecord]:
    """Query all MitigationMonitorRecord rows and convert to DTOs."""
    _ensure_seeded()
    try:
        with db_manager.session_scope() as session:
            rows = session.query(MitigationMonitorRecord).all()
            return [_db_record_to_mitigation(r) for r in rows]
    except Exception:
        logger.error("monitor.load_mitigations_failed", exc_info=True)
        return []


def _load_violations_from_db() -> List[ViolationRecord]:
    """
    Query RiskViolation rows and convert to ViolationRecord DTOs.
    Falls back to an empty list if the risk_violations table is
    not available or empty.
    """
    _ensure_seeded()
    try:
        with db_manager.session_scope() as session:
            rows = session.query(RiskViolation).all()
            results: List[ViolationRecord] = []
            for r in rows:
                results.append(ViolationRecord(
                    violation_id=r.violation_id,
                    rule_name=r.rule_name,
                    user_id=r.user_external_id,
                    user_name=r.username or r.user_external_id,
                    risk_level=r.severity.value if r.severity else "medium",
                    detected_at=r.detected_at or datetime.utcnow(),
                    mitigation_id=str(r.mitigation_id) if r.mitigation_id else None,
                    system=(r.affected_systems[0] if r.affected_systems else "SAP ECC"),
                    functions_in_conflict=r.conflicting_functions or [],
                ))
            return results
    except Exception:
        logger.error("monitor.load_violations_failed", exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Alert store -- in-memory list backed by DB-seeded data.
# Alerts are transient operational events; keeping them in memory is
# acceptable.  They are re-generated on each run_full_check() cycle.
# ---------------------------------------------------------------------------

_alert_store: List[MitigationAlert] = []
_alert_lock = threading.Lock()


def _store_alert(alert: MitigationAlert) -> None:
    with _alert_lock:
        _alert_store.append(alert)


# ---------------------------------------------------------------------------
# Scheduled check state
# ---------------------------------------------------------------------------

_scheduler_thread: Optional[threading.Thread] = None
_scheduler_stop_event = threading.Event()


# ---------------------------------------------------------------------------
# Monitoring engine
# ---------------------------------------------------------------------------

class MitigationMonitor:
    """
    Evaluates the health of all mitigation controls and raises alerts
    for any controls that are expiring, expired, unassigned, or ineffective.
    """

    INEFFECTIVE_THRESHOLD = 50.0   # Score below this = ineffective

    # ------------------------------------------------------------------
    # Targeted checks
    # ------------------------------------------------------------------

    def check_expiring_mitigations(
        self, days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Find controls whose valid_to date falls within the next days_ahead days.

        Args:
            days_ahead: Window (in days) to consider a control as expiring.

        Returns:
            List of mitigation dicts with an additional 'days_remaining' key.
        """
        _ensure_seeded()
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days_ahead)
        results: List[Dict[str, Any]] = []

        try:
            with db_manager.session_scope() as session:
                rows = (
                    session.query(MitigationMonitorRecord)
                    .filter(
                        MitigationMonitorRecord.expiry_date.isnot(None),
                        MitigationMonitorRecord.expiry_date > now,
                        MitigationMonitorRecord.expiry_date <= cutoff,
                    )
                    .all()
                )
                for row in rows:
                    m = _db_record_to_mitigation(row)
                    entry = m.to_dict()
                    entry["days_remaining"] = m.days_until_expiry()
                    results.append(entry)
        except Exception:
            logger.error("monitor.expiring_check_failed", exc_info=True)

        logger.info("monitor.expiring_check", count=len(results), days_ahead=days_ahead)
        return results

    def check_expired_mitigations(self) -> List[Dict[str, Any]]:
        """
        Find controls whose valid_to date has already passed.

        Returns:
            List of mitigation dicts with 'days_overdue' indicating how long
            ago the control expired.
        """
        _ensure_seeded()
        now = datetime.utcnow()
        results: List[Dict[str, Any]] = []

        try:
            with db_manager.session_scope() as session:
                rows = (
                    session.query(MitigationMonitorRecord)
                    .filter(
                        MitigationMonitorRecord.expiry_date.isnot(None),
                        MitigationMonitorRecord.expiry_date < now,
                    )
                    .all()
                )
                for row in rows:
                    m = _db_record_to_mitigation(row)
                    entry = m.to_dict()
                    days_overdue = abs(m.days_until_expiry() or 0)
                    entry["days_overdue"] = days_overdue
                    results.append(entry)
        except Exception:
            logger.error("monitor.expired_check_failed", exc_info=True)

        logger.info("monitor.expired_check", count=len(results))
        return results

    def check_unassigned_violations(self) -> List[Dict[str, Any]]:
        """
        Find violations that have no mitigation control assigned.

        Returns:
            List of violation dicts for unassigned violations, ordered by
            risk_level (critical first).
        """
        _ensure_seeded()
        risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        try:
            with db_manager.session_scope() as session:
                rows = (
                    session.query(RiskViolation)
                    .filter(
                        RiskViolation.is_mitigated == False,  # noqa: E712
                    )
                    .all()
                )
                unassigned = []
                for r in rows:
                    unassigned.append(ViolationRecord(
                        violation_id=r.violation_id,
                        rule_name=r.rule_name,
                        user_id=r.user_external_id,
                        user_name=r.username or r.user_external_id,
                        risk_level=r.severity.value if r.severity else "medium",
                        detected_at=r.detected_at or datetime.utcnow(),
                        mitigation_id=None,
                        system=(r.affected_systems[0] if r.affected_systems else "SAP ECC"),
                        functions_in_conflict=r.conflicting_functions or [],
                    ))
                unassigned.sort(key=lambda v: risk_order.get(v.risk_level, 99))
                logger.info("monitor.unassigned_check", count=len(unassigned))
                return [v.to_dict() for v in unassigned]
        except Exception:
            logger.error("monitor.unassigned_check_failed", exc_info=True)
            logger.info("monitor.unassigned_check", count=0)
            return []

    def check_control_effectiveness(self) -> List[Dict[str, Any]]:
        """
        Find controls whose effectiveness score falls below the ineffective
        threshold (INEFFECTIVE_THRESHOLD = 50.0).

        Returns:
            List of mitigation dicts that are considered ineffective.
        """
        _ensure_seeded()
        now = datetime.utcnow()
        results: List[Dict[str, Any]] = []

        try:
            with db_manager.session_scope() as session:
                rows = (
                    session.query(MitigationMonitorRecord)
                    .filter(
                        MitigationMonitorRecord.health_score < int(self.INEFFECTIVE_THRESHOLD),
                    )
                    .all()
                )
                for row in rows:
                    # Skip expired records (only care about active ineffective)
                    if row.expiry_date and row.expiry_date < now:
                        continue
                    m = _db_record_to_mitigation(row)
                    entry = m.to_dict()
                    entry["effectiveness_gap"] = round(
                        self.INEFFECTIVE_THRESHOLD - m.effectiveness_score, 1
                    )
                    results.append(entry)
        except Exception:
            logger.error("monitor.effectiveness_check_failed", exc_info=True)

        logger.info("monitor.effectiveness_check", count=len(results))
        return results

    # ------------------------------------------------------------------
    # Full health check
    # ------------------------------------------------------------------

    def run_full_check(self, days_ahead: int = 30) -> MitigationHealthReport:
        """
        Run all four checks and compile a MitigationHealthReport.
        Generates and stores MitigationAlerts for every issue found.
        Optionally sends notifications (wired to DeliveryEngine).

        Args:
            days_ahead: Expiry lookahead window in days.

        Returns:
            A populated MitigationHealthReport dataclass.
        """
        _ensure_seeded()

        report = MitigationHealthReport()

        # Count active (non-expired) mitigations from DB
        try:
            now = datetime.utcnow()
            with db_manager.session_scope() as session:
                total_active = (
                    session.query(func.count(MitigationMonitorRecord.id))
                    .filter(
                        (MitigationMonitorRecord.expiry_date.is_(None))
                        | (MitigationMonitorRecord.expiry_date >= now)
                    )
                    .scalar()
                ) or 0
                report.total_active = total_active
        except Exception:
            logger.error("monitor.count_active_failed", exc_info=True)
            report.total_active = 0

        # --- Expiring ---
        expiring = self.check_expiring_mitigations(days_ahead)
        report.expiring = expiring
        report.expiring_count = len(expiring)
        for entry in expiring:
            days = entry.get("days_remaining", 0)
            severity = AlertSeverity.CRITICAL if (days is not None and days <= 7) else AlertSeverity.WARNING
            alert = MitigationAlert(
                alert_type=AlertType.EXPIRING,
                severity=severity,
                title=f"Control Expiring: {entry['control_name']}",
                message=(
                    f"Mitigation control '{entry['control_name']}' expires in "
                    f"{days} day(s) on {entry.get('valid_to', 'N/A')}. "
                    "Please renew or replace this control."
                ),
                mitigation_id=entry["mitigation_id"],
            )
            _store_alert(alert)
            self._try_notify_expiring(entry, days)

        # --- Expired ---
        expired = self.check_expired_mitigations()
        report.expired = expired
        report.expired_count = len(expired)
        for entry in expired:
            alert = MitigationAlert(
                alert_type=AlertType.EXPIRED,
                severity=AlertSeverity.CRITICAL,
                title=f"Control Expired: {entry['control_name']}",
                message=(
                    f"Mitigation control '{entry['control_name']}' expired "
                    f"{entry.get('days_overdue', 0)} day(s) ago. "
                    "Violations it covered are now unprotected."
                ),
                mitigation_id=entry["mitigation_id"],
            )
            _store_alert(alert)

        # --- Unassigned violations ---
        unassigned = self.check_unassigned_violations()
        report.unassigned_violations = unassigned
        report.unassigned_count = len(unassigned)
        for entry in unassigned:
            severity = (
                AlertSeverity.CRITICAL
                if entry["risk_level"] in ("critical", "high")
                else AlertSeverity.WARNING
            )
            alert = MitigationAlert(
                alert_type=AlertType.UNASSIGNED_VIOLATION,
                severity=severity,
                title=f"Unmitigated Violation: {entry['rule_name']}",
                message=(
                    f"Violation '{entry['rule_name']}' for user {entry['user_name']} "
                    f"(risk: {entry['risk_level']}) has no mitigation control assigned."
                ),
                violation_id=entry["violation_id"],
            )
            _store_alert(alert)

        # --- Ineffective controls ---
        ineffective = self.check_control_effectiveness()
        report.ineffective = ineffective
        report.ineffective_count = len(ineffective)
        for entry in ineffective:
            alert = MitigationAlert(
                alert_type=AlertType.INEFFECTIVE_CONTROL,
                severity=AlertSeverity.WARNING,
                title=f"Ineffective Control: {entry['control_name']}",
                message=(
                    f"Control '{entry['control_name']}' has an effectiveness score of "
                    f"{entry['effectiveness_score']:.0f}% (threshold: "
                    f"{self.INEFFECTIVE_THRESHOLD:.0f}%). "
                    "Please investigate and remediate."
                ),
                mitigation_id=entry["mitigation_id"],
            )
            _store_alert(alert)

        with _alert_lock:
            report.alerts = [a.to_dict() for a in _alert_store[-100:]]
        report.alerts_generated = (
            report.expiring_count
            + report.expired_count
            + report.unassigned_count
            + report.ineffective_count
        )

        logger.info(
            "monitor.full_check_complete",
            expiring=report.expiring_count,
            expired=report.expired_count,
            unassigned=report.unassigned_count,
            ineffective=report.ineffective_count,
            alerts=report.alerts_generated,
        )
        return report

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def get_health_dashboard(self) -> Dict[str, Any]:
        """
        Return a high-level dashboard view of mitigation health.
        Runs a quick check with a 30-day window without generating new alerts.
        """
        _ensure_seeded()
        now = datetime.utcnow()

        try:
            with db_manager.session_scope() as session:
                total = session.query(func.count(MitigationMonitorRecord.id)).scalar() or 0

                active = (
                    session.query(func.count(MitigationMonitorRecord.id))
                    .filter(
                        (MitigationMonitorRecord.expiry_date.is_(None))
                        | (MitigationMonitorRecord.expiry_date >= now)
                    )
                    .scalar()
                ) or 0

                cutoff_30d = now + timedelta(days=30)
                expiring = (
                    session.query(func.count(MitigationMonitorRecord.id))
                    .filter(
                        MitigationMonitorRecord.expiry_date.isnot(None),
                        MitigationMonitorRecord.expiry_date > now,
                        MitigationMonitorRecord.expiry_date <= cutoff_30d,
                    )
                    .scalar()
                ) or 0

                expired = (
                    session.query(func.count(MitigationMonitorRecord.id))
                    .filter(
                        MitigationMonitorRecord.expiry_date.isnot(None),
                        MitigationMonitorRecord.expiry_date < now,
                    )
                    .scalar()
                ) or 0

                ineffective = (
                    session.query(func.count(MitigationMonitorRecord.id))
                    .filter(
                        MitigationMonitorRecord.health_score < int(self.INEFFECTIVE_THRESHOLD),
                        (MitigationMonitorRecord.expiry_date.is_(None))
                        | (MitigationMonitorRecord.expiry_date >= now),
                    )
                    .scalar()
                ) or 0

            # Unassigned violations from risk_violations table
            with db_manager.session_scope() as session:
                unassigned = (
                    session.query(func.count(RiskViolation.id))
                    .filter(RiskViolation.is_mitigated == False)  # noqa: E712
                    .scalar()
                ) or 0

        except Exception:
            logger.error("monitor.dashboard_query_failed", exc_info=True)
            total = active = expiring = expired = ineffective = unassigned = 0

        with _alert_lock:
            recent_alerts = [a.to_dict() for a in _alert_store[-10:]]

        health_score = max(
            0.0,
            round(
                100.0
                - (expiring * 5)
                - (expired * 20)
                - (unassigned * 15)
                - (ineffective * 10),
                1,
            ),
        )

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "health_score": health_score,
            "health_status": self._score_to_status(health_score),
            "summary": {
                "total_mitigations": total,
                "active": active,
                "expiring_soon": expiring,
                "expired": expired,
                "ineffective": ineffective,
                "unassigned_violations": unassigned,
            },
            "recent_alerts": recent_alerts,
            "next_check": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }

    # ------------------------------------------------------------------
    # Alert history
    # ------------------------------------------------------------------

    def get_alert_history(
        self,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return past alerts generated by the monitoring engine.

        Args:
            alert_type: Optional filter (expiring / expired / unassigned_violation /
                        ineffective_control).
            severity:   Optional filter (info / warning / critical).
            limit:      Maximum records to return.
        """
        with _alert_lock:
            alerts = list(reversed(_alert_store))

        if alert_type:
            alerts = [a for a in alerts if a.alert_type.value == alert_type]
        if severity:
            alerts = [a for a in alerts if a.severity.value == severity]

        return [a.to_dict() for a in alerts[:limit]]

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def schedule_check(self, interval_hours: int = 24) -> Dict[str, Any]:
        """
        Start a background thread that runs run_full_check() periodically.

        Calling schedule_check() again while a scheduler is already running
        will stop the previous one and start a new one.

        Args:
            interval_hours: How often (in hours) to run the full check.

        Returns:
            Dict confirming the schedule.
        """
        global _scheduler_thread, _scheduler_stop_event

        # Stop existing scheduler if running
        if _scheduler_thread and _scheduler_thread.is_alive():
            _scheduler_stop_event.set()
            _scheduler_thread.join(timeout=5)
            logger.info("monitor.scheduler_stopped")

        _scheduler_stop_event = threading.Event()

        def _worker() -> None:
            logger.info("monitor.scheduler_started", interval_hours=interval_hours)
            while not _scheduler_stop_event.wait(timeout=interval_hours * 3600):
                try:
                    self.run_full_check()
                except Exception:
                    logger.error("monitor.scheduler_error", exc_info=True)
            logger.info("monitor.scheduler_finished")

        _scheduler_thread = threading.Thread(target=_worker, daemon=True, name="mitigation-monitor")
        _scheduler_thread.start()

        next_run = datetime.utcnow() + timedelta(hours=interval_hours)
        logger.info("monitor.scheduler_scheduled", interval_hours=interval_hours)
        return {
            "status": "scheduled",
            "interval_hours": interval_hours,
            "next_run_at": next_run.isoformat(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_status(score: float) -> str:
        if score >= 85:
            return "healthy"
        if score >= 60:
            return "degraded"
        return "critical"

    @staticmethod
    def _try_notify_expiring(entry: Dict[str, Any], days_remaining: Optional[int]) -> None:
        """
        Attempt to send a notification for an expiring control.
        Gracefully skips if the delivery engine is unavailable.
        """
        try:
            from core.notifications.delivery import (
                DeliveryNotification,
                DeliveryNotificationType,
                DeliveryChannel,
                get_delivery_engine,
            )
            engine = get_delivery_engine()
            notification = DeliveryNotification(
                notification_type=DeliveryNotificationType.MITIGATION_EXPIRING,
                recipient_id=entry.get("owner_id", "admin"),
                recipient_email=None,   # Wire to real user lookup for production
                channels=[DeliveryChannel.SLACK],
                context={
                    "control_name": entry.get("control_name", "Unknown"),
                    "expiry_date": entry.get("valid_to", "N/A"),
                    "days_remaining": str(days_remaining) if days_remaining is not None else "N/A",
                    "violation_count": str(len(entry.get("violation_ids", []))),
                },
            )
            engine.send_notification(notification)
        except Exception:
            logger.warning("monitor.notify_failed", exc_info=True)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_monitor: Optional[MitigationMonitor] = None


def get_monitor() -> MitigationMonitor:
    """Return the module-level MitigationMonitor singleton."""
    global _monitor
    if _monitor is None:
        _monitor = MitigationMonitor()
    return _monitor
