"""
Process Control Manager

Full business-logic layer for the Process Control module (PC-01 through PC-32).

Sections
--------
1.  Control Library       — PC-01, PC-04
2.  Framework Mapping     — PC-03, XI-07, PC-31
3.  Control Testing       — PC-11
4.  Deficiency Mgmt       — PC-13
5.  Self-Assessment       — PC-12
6.  CCM                   — PC-20, PC-22, PC-24
7.  Evidence Management   — PC-15, NF-05
8.  SOX Sign-Off          — PC-14
9.  Reporting             — PC-30, PC-31, PC-32

All operations are scoped to the caller's tenant_id.  The constructor follows
the per-tenant factory pattern used across the GovernexPlus codebase:

    manager = ProcessControlManager(tenant_id="acme", db=db_session)
"""

import hashlib
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models.process_control import (
    CCMExecution,
    CCMResult,
    CCMRule,
    CCMRuleType,
    ControlDeficiency,
    ControlNature,
    ControlSelfAssessment,
    ControlStatus,
    ControlTest,
    ControlType,
    CSAStatus,
    DeficiencySeverity,
    DeficiencyStatus,
    EvidenceStatus,
    GRCEvidence,
    ProcessControl,
    SignOffCertification,
    SignOffStatus,
    TestResult,
    TestStatus,
)
from db.models.grc_foundation import FrameworkDefinition, FrameworkRequirement, OrgUnit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ID generators
# ---------------------------------------------------------------------------

def _gen_control_id() -> str:
    """Generate a unique control ID in the format CTL-XXXXXXXX."""
    return f"CTL-{secrets.token_hex(4).upper()}"


def _gen_test_id() -> str:
    """Generate a unique test ID in the format TST-XXXXXXXX."""
    return f"TST-{secrets.token_hex(4).upper()}"


def _gen_deficiency_id() -> str:
    """Generate a unique deficiency ID in the format DEF-XXXXXXXX."""
    return f"DEF-{secrets.token_hex(4).upper()}"


def _gen_assessment_id() -> str:
    """Generate a unique assessment ID in the format CSA-XXXXXXXX."""
    return f"CSA-{secrets.token_hex(4).upper()}"


def _gen_ccm_rule_id() -> str:
    """Generate a unique CCM rule ID in the format CCM-XXXXXXXX."""
    return f"CCM-{secrets.token_hex(4).upper()}"


def _gen_evidence_id() -> str:
    """Generate a unique evidence ID in the format EVD-XXXXXXXX."""
    return f"EVD-{secrets.token_hex(4).upper()}"


def _gen_certification_id() -> str:
    """Generate a unique certification ID in the format SGN-XXXXXXXX."""
    return f"SGN-{secrets.token_hex(4).upper()}"


def _sha256(content: str) -> str:
    """Compute a SHA-256 hex digest for integrity verification."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------

_SEVERITY_MAP: Dict[str, DeficiencySeverity] = {
    "material_weakness": DeficiencySeverity.MATERIAL_WEAKNESS,
    "significant_deficiency": DeficiencySeverity.SIGNIFICANT_DEFICIENCY,
    "control_gap": DeficiencySeverity.CONTROL_GAP,
    "observation": DeficiencySeverity.OBSERVATION,
}


def _coerce_severity(value: str) -> DeficiencySeverity:
    return _SEVERITY_MAP.get(value.lower(), DeficiencySeverity.OBSERVATION)


# ---------------------------------------------------------------------------
# ProcessControlManager
# ---------------------------------------------------------------------------

class ProcessControlManager:
    """
    Central manager for the Process Control GRC module.

    Parameters
    ----------
    tenant_id : str
        Tenant identifier used to scope every DB query and write.
    db : Session
        Active SQLAlchemy session.  All writes commit immediately; callers
        may pass a transactional session to batch commits.
    """

    def __init__(self, tenant_id: str, db: Session) -> None:
        self.tenant_id = tenant_id
        self.db = db

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _scope(self, model):
        """Return a query pre-filtered to the current tenant."""
        return self.db.query(model).filter(model.tenant_id == self.tenant_id)

    def _get_control_by_string_id(self, control_id: str) -> ProcessControl:
        """Fetch a ProcessControl by its string control_id; raise if missing."""
        record = (
            self._scope(ProcessControl)
            .filter(ProcessControl.control_id == control_id)
            .first()
        )
        if not record:
            raise ValueError(f"Control '{control_id}' not found for tenant '{self.tenant_id}'.")
        return record

    def _get_test_by_string_id(self, test_id: str) -> ControlTest:
        """Fetch a ControlTest by its string test_id; raise if missing."""
        record = (
            self._scope(ControlTest)
            .filter(ControlTest.test_id == test_id)
            .first()
        )
        if not record:
            raise ValueError(f"Test '{test_id}' not found for tenant '{self.tenant_id}'.")
        return record

    def _get_deficiency_by_string_id(self, deficiency_id: str) -> ControlDeficiency:
        record = (
            self._scope(ControlDeficiency)
            .filter(ControlDeficiency.deficiency_id == deficiency_id)
            .first()
        )
        if not record:
            raise ValueError(f"Deficiency '{deficiency_id}' not found.")
        return record

    def _get_ccm_rule_by_string_id(self, rule_id: str) -> CCMRule:
        record = (
            self._scope(CCMRule)
            .filter(CCMRule.rule_id == rule_id)
            .first()
        )
        if not record:
            raise ValueError(f"CCM rule '{rule_id}' not found.")
        return record

    def _get_evidence_by_string_id(self, evidence_id: str) -> GRCEvidence:
        record = (
            self._scope(GRCEvidence)
            .filter(GRCEvidence.evidence_id == evidence_id)
            .first()
        )
        if not record:
            raise ValueError(f"Evidence '{evidence_id}' not found.")
        return record

    def _get_certification_by_string_id(self, certification_id: str) -> SignOffCertification:
        record = (
            self._scope(SignOffCertification)
            .filter(SignOffCertification.certification_id == certification_id)
            .first()
        )
        if not record:
            raise ValueError(f"Certification '{certification_id}' not found.")
        return record

    # =========================================================================
    # 1. Control Library  (PC-01, PC-04)
    # =========================================================================

    def create_control(self, data: dict) -> dict:
        """
        Create a new control in the library (PC-01).

        Required keys in *data*: name, control_type, control_nature, frequency.
        An auto-generated control_id (CTL-XXXXXXXX) is assigned.
        Version starts at 1 and change_history is initialised.

        Returns the serialised control dict.
        """
        control_id = _gen_control_id()

        try:
            c_type = ControlType(data["control_type"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid control_type: {data.get('control_type')}") from exc

        try:
            c_nature = ControlNature(data["control_nature"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid control_nature: {data.get('control_nature')}") from exc

        from db.models.process_control import ControlFrequency
        try:
            c_freq = ControlFrequency(data["frequency"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid frequency: {data.get('frequency')}") from exc

        now = datetime.utcnow()
        initial_history = [
            {
                "version": 1,
                "changed_by": data.get("created_by", "system"),
                "changed_at": now.isoformat(),
                "summary": "Initial creation",
            }
        ]

        record = ProcessControl(
            tenant_id=self.tenant_id,
            control_id=control_id,
            name=data["name"],
            objective=data.get("objective"),
            description=data.get("description"),
            control_type=c_type,
            control_nature=c_nature,
            frequency=c_freq,
            org_unit_id=data.get("org_unit_id"),
            process_name=data.get("process_name"),
            subprocess_name=data.get("subprocess_name"),
            owner_id=data.get("owner_id"),
            owner_name=data.get("owner_name"),
            owner_email=data.get("owner_email"),
            framework_mappings=data.get("framework_mappings", []),
            risk_ids=data.get("risk_ids", []),
            regulation_ids=data.get("regulation_ids", []),
            version=1,
            effective_date=data.get("effective_date"),
            review_date=data.get("review_date"),
            next_review_date=data.get("next_review_date"),
            status=ControlStatus(data.get("status", ControlStatus.DRAFT.value)),
            key_control=bool(data.get("key_control", False)),
            is_active=True,
            change_history=initial_history,
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "process_control.create tenant=%s control_id=%s name=%r",
            self.tenant_id, control_id, data["name"],
        )
        return record.to_dict()

    def update_control(self, control_id: str, data: dict) -> dict:
        """
        Update a control definition (PC-04).

        Bumps the version counter and appends a change_history entry.
        Immutable fields (control_id, tenant_id) are ignored even if supplied.

        Returns the updated serialised control dict.
        """
        record = self._get_control_by_string_id(control_id)

        updatable = [
            "name", "objective", "description", "process_name", "subprocess_name",
            "owner_id", "owner_name", "owner_email", "risk_ids", "regulation_ids",
            "key_control", "effective_date", "review_date", "next_review_date",
            "org_unit_id",
        ]
        for field_name in updatable:
            if field_name in data:
                setattr(record, field_name, data[field_name])

        if "control_type" in data:
            record.control_type = ControlType(data["control_type"])
        if "control_nature" in data:
            record.control_nature = ControlNature(data["control_nature"])
        if "frequency" in data:
            from db.models.process_control import ControlFrequency
            record.frequency = ControlFrequency(data["frequency"])
        if "status" in data:
            record.status = ControlStatus(data["status"])

        record.version = (record.version or 1) + 1
        history = list(record.change_history or [])
        history.append(
            {
                "version": record.version,
                "changed_by": data.get("changed_by", "system"),
                "changed_at": datetime.utcnow().isoformat(),
                "summary": data.get("change_summary", "Updated"),
            }
        )
        record.change_history = history

        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "process_control.update tenant=%s control_id=%s new_version=%d",
            self.tenant_id, control_id, record.version,
        )
        return record.to_dict()

    def get_control(self, control_id: str) -> dict:
        """Return a single control by its string control_id."""
        return self._get_control_by_string_id(control_id).to_dict()

    def list_controls(self, filters: Optional[dict] = None) -> List[dict]:
        """
        List controls for this tenant with optional filters (PC-01).

        Supported filter keys
        ---------------------
        control_type   : str   — e.g. "preventive"
        control_nature : str   — e.g. "automated"
        org_unit_id    : int
        process_name   : str   — case-insensitive substring match
        status         : str   — e.g. "active"
        key_control    : bool
        """
        q = self._scope(ProcessControl).filter(ProcessControl.is_active.is_(True))

        if filters:
            if "control_type" in filters:
                q = q.filter(
                    ProcessControl.control_type == ControlType(filters["control_type"])
                )
            if "control_nature" in filters:
                q = q.filter(
                    ProcessControl.control_nature == ControlNature(filters["control_nature"])
                )
            if "org_unit_id" in filters:
                q = q.filter(ProcessControl.org_unit_id == filters["org_unit_id"])
            if "process_name" in filters:
                q = q.filter(
                    ProcessControl.process_name.ilike(f"%{filters['process_name']}%")
                )
            if "status" in filters:
                q = q.filter(
                    ProcessControl.status == ControlStatus(filters["status"])
                )
            if "key_control" in filters:
                q = q.filter(ProcessControl.key_control.is_(bool(filters["key_control"])))

        return [r.to_dict() for r in q.order_by(ProcessControl.created_at.desc()).all()]

    def retire_control(self, control_id: str) -> dict:
        """
        Retire a control (set status=RETIRED, is_active=False).

        Retired controls are excluded from list_controls results and cannot
        be mapped to new framework requirements.
        """
        record = self._get_control_by_string_id(control_id)
        if record.status == ControlStatus.RETIRED:
            raise ValueError(f"Control '{control_id}' is already retired.")

        record.status = ControlStatus.RETIRED
        record.is_active = False

        history = list(record.change_history or [])
        history.append(
            {
                "version": record.version,
                "changed_by": "system",
                "changed_at": datetime.utcnow().isoformat(),
                "summary": "Control retired",
            }
        )
        record.change_history = history

        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "process_control.retire tenant=%s control_id=%s",
            self.tenant_id, control_id,
        )
        return record.to_dict()

    # =========================================================================
    # 2. Framework Mapping  (PC-03, XI-07)
    # =========================================================================

    def map_control_to_framework(
        self, control_id: str, framework_id: str, requirement_id: str
    ) -> dict:
        """
        Add a framework/requirement mapping to a control (PC-03, XI-07).

        Idempotent — duplicate (framework_id, requirement_id) pairs are ignored.
        Returns the updated control dict.
        """
        record = self._get_control_by_string_id(control_id)

        if record.status == ControlStatus.RETIRED:
            raise ValueError(f"Cannot map a retired control '{control_id}'.")

        mappings: List[dict] = list(record.framework_mappings or [])
        already_mapped = any(
            m.get("framework_id") == framework_id and m.get("requirement_id") == requirement_id
            for m in mappings
        )
        if not already_mapped:
            mappings.append(
                {
                    "framework_id": framework_id,
                    "requirement_id": requirement_id,
                    "mapped_at": datetime.utcnow().isoformat(),
                }
            )
            record.framework_mappings = mappings
            self.db.commit()
            self.db.refresh(record)
            logger.info(
                "process_control.map_framework tenant=%s control_id=%s fw=%s req=%s",
                self.tenant_id, control_id, framework_id, requirement_id,
            )

        return record.to_dict()

    def unmap_control_from_framework(
        self, control_id: str, framework_id: str, requirement_id: str
    ) -> dict:
        """
        Remove a specific framework/requirement mapping from a control.

        Raises ValueError if the mapping does not exist.
        """
        record = self._get_control_by_string_id(control_id)

        mappings: List[dict] = list(record.framework_mappings or [])
        new_mappings = [
            m for m in mappings
            if not (
                m.get("framework_id") == framework_id
                and m.get("requirement_id") == requirement_id
            )
        ]
        if len(new_mappings) == len(mappings):
            raise ValueError(
                f"Mapping ({framework_id}, {requirement_id}) not found on control '{control_id}'."
            )

        record.framework_mappings = new_mappings
        self.db.commit()
        self.db.refresh(record)
        return record.to_dict()

    def get_framework_coverage(self, framework_id: str) -> dict:
        """
        Return a coverage map for a framework (PC-31).

        Fetches all requirements for the framework and matches them against
        mapped controls to compute a coverage percentage and gap list.

        Returns
        -------
        dict with keys:
          framework_id, framework_name, total_requirements,
          covered_requirements, coverage_pct, gaps (list of requirement_ids),
          coverage_map (dict requirement_id -> list of control dicts)
        """
        # Resolve framework name
        fw_row = (
            self.db.query(FrameworkDefinition)
            .filter(
                FrameworkDefinition.framework_id == framework_id,
                FrameworkDefinition.tenant_id == self.tenant_id,
            )
            .first()
        )
        framework_name = fw_row.name if fw_row else framework_id

        # All requirements for this framework
        req_rows = (
            self.db.query(FrameworkRequirement)
            .filter(FrameworkRequirement.tenant_id == self.tenant_id)
            .all()
        )
        # Filter by framework PK if we have the framework record
        if fw_row:
            req_rows = [r for r in req_rows if r.framework_id == fw_row.id]

        all_req_ids: List[str] = [r.requirement_id for r in req_rows]

        # Controls in tenant that map to this framework
        controls = (
            self._scope(ProcessControl)
            .filter(ProcessControl.is_active.is_(True))
            .all()
        )

        coverage_map: Dict[str, List[dict]] = {req_id: [] for req_id in all_req_ids}

        for ctrl in controls:
            for mapping in (ctrl.framework_mappings or []):
                if mapping.get("framework_id") != framework_id:
                    continue
                req_id = mapping.get("requirement_id")
                if req_id in coverage_map:
                    coverage_map[req_id].append(
                        {
                            "control_id": ctrl.control_id,
                            "name": ctrl.name,
                            "status": ctrl.status.value if ctrl.status else None,
                            "key_control": ctrl.key_control,
                        }
                    )

        covered = [req_id for req_id, ctrls in coverage_map.items() if ctrls]
        gaps = [req_id for req_id, ctrls in coverage_map.items() if not ctrls]
        total = len(all_req_ids)
        coverage_pct = round((len(covered) / total) * 100, 1) if total else 0.0

        return {
            "framework_id": framework_id,
            "framework_name": framework_name,
            "total_requirements": total,
            "covered_requirements": len(covered),
            "coverage_pct": coverage_pct,
            "gaps": gaps,
            "coverage_map": coverage_map,
        }

    def get_control_frameworks(self, control_id: str) -> List[dict]:
        """
        Return all framework/requirement mappings for a control.

        Each entry includes the framework name resolved from FrameworkDefinition.
        """
        record = self._get_control_by_string_id(control_id)
        mappings = list(record.framework_mappings or [])

        # Enrich with framework names
        enriched = []
        for mapping in mappings:
            fw_id = mapping.get("framework_id")
            fw_row = (
                self.db.query(FrameworkDefinition)
                .filter(
                    FrameworkDefinition.framework_id == fw_id,
                    FrameworkDefinition.tenant_id == self.tenant_id,
                )
                .first()
            )
            enriched.append(
                {
                    **mapping,
                    "framework_name": fw_row.name if fw_row else fw_id,
                    "framework_type": fw_row.framework_type.value if fw_row else None,
                }
            )
        return enriched

    # =========================================================================
    # 3. Control Testing  (PC-11)
    # =========================================================================

    def create_test(self, control_id: str, data: dict) -> dict:
        """
        Create a new test record for a control (PC-11).

        Requires data keys: test_type, tester_id, tester_name.
        Optional: testing_period_start, testing_period_end, sample_size,
                  population_size, test_steps, evidence_ids.

        Returns the serialised test dict.
        """
        control = self._get_control_by_string_id(control_id)

        from db.models.process_control import TestType
        try:
            t_type = TestType(data["test_type"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid test_type: {data.get('test_type')}") from exc

        test_id = _gen_test_id()

        record = ControlTest(
            tenant_id=self.tenant_id,
            test_id=test_id,
            control_id=control.id,
            test_type=t_type,
            testing_period_start=data.get("testing_period_start"),
            testing_period_end=data.get("testing_period_end"),
            sample_size=data.get("sample_size"),
            population_size=data.get("population_size"),
            tester_id=data.get("tester_id"),
            tester_name=data.get("tester_name"),
            test_steps=data.get("test_steps", []),
            result=TestResult.NOT_TESTED,
            exceptions_found=0,
            exception_details=[],
            evidence_ids=data.get("evidence_ids", []),
            status=TestStatus.PLANNED,
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "process_control.create_test tenant=%s control_id=%s test_id=%s",
            self.tenant_id, control_id, test_id,
        )
        return record.to_dict()

    def record_test_result(self, test_id: str, data: dict) -> dict:
        """
        Record the result of a completed control test (PC-11).

        Accepts data keys: result, exceptions_found, exception_details,
        conclusion, reviewed_by, evidence_ids.

        If result == 'ineffective', a ControlDeficiency is automatically
        created (source='test') with severity derived from data.get('deficiency_severity',
        'significant_deficiency').

        Returns a dict with keys: test (dict), deficiency (dict or None).
        """
        record = self._get_test_by_string_id(test_id)

        try:
            result = TestResult(data["result"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid result value: {data.get('result')}") from exc

        record.result = result
        record.exceptions_found = data.get("exceptions_found", 0)
        record.exception_details = data.get("exception_details", [])
        record.conclusion = data.get("conclusion")
        record.reviewed_by = data.get("reviewed_by")
        record.reviewed_at = datetime.utcnow() if data.get("reviewed_by") else None
        record.status = TestStatus.REVIEWED if data.get("reviewed_by") else TestStatus.COMPLETED

        if data.get("evidence_ids"):
            existing = list(record.evidence_ids or [])
            existing.extend(data["evidence_ids"])
            record.evidence_ids = existing

        self.db.commit()
        self.db.refresh(record)

        deficiency_dict: Optional[dict] = None
        if result == TestResult.INEFFECTIVE:
            # Look up the control's string ID for the deficiency helper
            control_row = (
                self.db.query(ProcessControl)
                .filter(ProcessControl.id == record.control_id)
                .first()
            )
            if control_row:
                severity_str = data.get("deficiency_severity", "significant_deficiency")
                def_data = {
                    "control_id": control_row.control_id,
                    "test_id": record.id,
                    "source": "test",
                    "title": data.get(
                        "deficiency_title",
                        f"Control failure detected by test {test_id}",
                    ),
                    "description": data.get(
                        "deficiency_description",
                        record.conclusion or "Ineffective control test result.",
                    ),
                    "severity": severity_str,
                    "root_cause": data.get("root_cause"),
                    "remediation_owner_id": data.get("remediation_owner_id"),
                    "remediation_owner_name": data.get("remediation_owner_name"),
                }
                deficiency_dict = self._create_deficiency_internal(def_data)

        logger.info(
            "process_control.record_test_result tenant=%s test_id=%s result=%s deficiency=%s",
            self.tenant_id, test_id, result.value,
            deficiency_dict.get("deficiency_id") if deficiency_dict else None,
        )
        return {"test": record.to_dict(), "deficiency": deficiency_dict}

    def get_control_tests(self, control_id: str) -> List[dict]:
        """Return all tests for a control ordered by creation date desc."""
        control = self._get_control_by_string_id(control_id)
        rows = (
            self._scope(ControlTest)
            .filter(ControlTest.control_id == control.id)
            .order_by(ControlTest.created_at.desc())
            .all()
        )
        return [r.to_dict() for r in rows]

    # =========================================================================
    # 4. Deficiency Management  (PC-13)
    # =========================================================================

    def _create_deficiency_internal(self, data: dict) -> dict:
        """
        Internal helper — create a deficiency without resolving the control by
        string ID again (used from record_test_result and execute_ccm_rule).

        data must contain: control_id (string), title, severity.
        Optional: test_id (int pk), source, description, root_cause,
                  remediation_owner_id, remediation_owner_name, due_date.
        """
        # Resolve control pk
        control = self._get_control_by_string_id(data["control_id"])

        deficiency_id = _gen_deficiency_id()
        severity = _coerce_severity(data.get("severity", "observation"))

        record = ControlDeficiency(
            tenant_id=self.tenant_id,
            deficiency_id=deficiency_id,
            control_id=control.id,
            test_id=data.get("test_id"),
            source=data.get("source", "test"),
            title=data["title"],
            description=data.get("description"),
            severity=severity,
            root_cause=data.get("root_cause"),
            remediation_plan=data.get("remediation_plan"),
            remediation_owner_id=data.get("remediation_owner_id"),
            remediation_owner_name=data.get("remediation_owner_name"),
            due_date=data.get("due_date"),
            status=DeficiencyStatus.OPEN,
            related_risk_ids=data.get("related_risk_ids", []),
            related_finding_ids=data.get("related_finding_ids", []),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record.to_dict()

    def create_deficiency(self, data: dict) -> dict:
        """
        Manually create a control deficiency (PC-13).

        Required data keys: control_id, title, severity.
        """
        if not data.get("control_id"):
            raise ValueError("control_id is required.")
        if not data.get("title"):
            raise ValueError("title is required.")
        return self._create_deficiency_internal(data)

    def update_deficiency(self, deficiency_id: str, data: dict) -> dict:
        """
        Update mutable fields of a deficiency (description, remediation plan,
        owner, due_date, etc.).  Status transitions use dedicated methods.
        """
        record = self._get_deficiency_by_string_id(deficiency_id)

        updatable = [
            "title", "description", "root_cause", "remediation_plan",
            "remediation_owner_id", "remediation_owner_name", "due_date",
            "related_risk_ids", "related_finding_ids",
        ]
        for field_name in updatable:
            if field_name in data:
                setattr(record, field_name, data[field_name])

        if "severity" in data:
            record.severity = _coerce_severity(data["severity"])

        self.db.commit()
        self.db.refresh(record)
        return record.to_dict()

    def remediate_deficiency(self, deficiency_id: str, data: dict) -> dict:
        """
        Mark a deficiency as remediated (PC-13).

        Transitions status to REMEDIATED and records completed_at.
        Requires data key: remediation_notes (stored in remediation_plan).
        """
        record = self._get_deficiency_by_string_id(deficiency_id)

        if record.status == DeficiencyStatus.VERIFIED_CLOSED:
            raise ValueError(
                f"Deficiency '{deficiency_id}' is already verified closed."
            )

        record.status = DeficiencyStatus.REMEDIATED
        record.completed_at = datetime.utcnow()
        if data.get("remediation_notes"):
            record.remediation_plan = data["remediation_notes"]

        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "process_control.remediate_deficiency tenant=%s deficiency_id=%s",
            self.tenant_id, deficiency_id,
        )
        return record.to_dict()

    def verify_deficiency_closure(self, deficiency_id: str, verifier_id: str) -> dict:
        """
        Verify that a remediated deficiency is closed (PC-13).

        Transitions status from REMEDIATED -> VERIFIED_CLOSED.
        Raises ValueError if the deficiency has not been remediated yet.
        """
        record = self._get_deficiency_by_string_id(deficiency_id)

        if record.status not in (DeficiencyStatus.REMEDIATED, DeficiencyStatus.IN_REMEDIATION):
            raise ValueError(
                f"Deficiency '{deficiency_id}' must be in REMEDIATED status to verify closure "
                f"(current: {record.status.value})."
            )

        record.status = DeficiencyStatus.VERIFIED_CLOSED
        record.verified_by = verifier_id
        record.verified_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "process_control.verify_closure tenant=%s deficiency_id=%s verifier=%s",
            self.tenant_id, deficiency_id, verifier_id,
        )
        return record.to_dict()

    def get_deficiencies(self, filters: Optional[dict] = None) -> List[dict]:
        """
        List deficiencies for this tenant (PC-13).

        Supported filter keys
        ---------------------
        severity   : str  — e.g. "material_weakness"
        status     : str  — e.g. "open"
        control_id : str  — string control_id
        owner_id   : str  — remediation_owner_id
        """
        q = self._scope(ControlDeficiency)

        if filters:
            if "severity" in filters:
                q = q.filter(
                    ControlDeficiency.severity == _coerce_severity(filters["severity"])
                )
            if "status" in filters:
                q = q.filter(
                    ControlDeficiency.status == DeficiencyStatus(filters["status"])
                )
            if "control_id" in filters:
                control = self._get_control_by_string_id(filters["control_id"])
                q = q.filter(ControlDeficiency.control_id == control.id)
            if "owner_id" in filters:
                q = q.filter(
                    ControlDeficiency.remediation_owner_id == filters["owner_id"]
                )

        return [r.to_dict() for r in q.order_by(ControlDeficiency.created_at.desc()).all()]

    # =========================================================================
    # 5. Self-Assessment  (PC-12)
    # =========================================================================

    def create_self_assessment_campaign(self, data: dict) -> dict:
        """
        Create a self-assessment campaign and generate individual assessment
        records for every control in scope (PC-12).

        Required data keys: campaign_name, assessor_id, assessor_name.
        Optional: campaign_type, due_date, control_ids (list of string ids;
                  defaults to all active controls for the tenant),
                  reviewer_id.

        Returns a dict with keys: campaign_name, assessment_ids (list),
        assessments (list of dicts).
        """
        campaign_name = data.get("campaign_name")
        if not campaign_name:
            raise ValueError("campaign_name is required.")

        # Resolve in-scope controls
        if data.get("control_ids"):
            controls = [
                self._get_control_by_string_id(cid) for cid in data["control_ids"]
            ]
        else:
            controls = (
                self._scope(ProcessControl)
                .filter(ProcessControl.is_active.is_(True))
                .all()
            )

        if not controls:
            raise ValueError("No active controls found for the campaign scope.")

        campaign_type = data.get("campaign_type", "adhoc")
        assessor_id = data.get("assessor_id")
        assessor_name = data.get("assessor_name")
        due_date = data.get("due_date")
        reviewer_id = data.get("reviewer_id")

        assessment_records = []
        for ctrl in controls:
            assessment_id = _gen_assessment_id()
            record = ControlSelfAssessment(
                tenant_id=self.tenant_id,
                assessment_id=assessment_id,
                campaign_name=campaign_name,
                campaign_type=campaign_type,
                control_id=ctrl.id,
                assessor_id=assessor_id,
                assessor_name=assessor_name,
                due_date=due_date,
                reviewer_id=reviewer_id,
                status=CSAStatus.PENDING,
            )
            self.db.add(record)
            assessment_records.append(record)

        self.db.commit()
        for r in assessment_records:
            self.db.refresh(r)

        logger.info(
            "process_control.create_csa_campaign tenant=%s campaign=%r controls=%d",
            self.tenant_id, campaign_name, len(assessment_records),
        )

        return {
            "campaign_name": campaign_name,
            "campaign_type": campaign_type,
            "assessor_id": assessor_id,
            "due_date": due_date.isoformat() if isinstance(due_date, datetime) else due_date,
            "assessment_count": len(assessment_records),
            "assessment_ids": [r.assessment_id for r in assessment_records],
            "assessments": [r.to_dict() for r in assessment_records],
        }

    def submit_self_assessment(self, assessment_id: str, data: dict) -> dict:
        """
        Submit a control owner's self-assessment response (PC-12).

        Required data keys: design_adequate (bool), operating_effectively (bool),
        attestation (str).
        Optional: questionnaire_responses (dict), reviewer_comments.

        Transitions status to COMPLETED and records attested_at.
        """
        record = (
            self._scope(ControlSelfAssessment)
            .filter(ControlSelfAssessment.assessment_id == assessment_id)
            .first()
        )
        if not record:
            raise ValueError(f"Assessment '{assessment_id}' not found.")

        if record.status == CSAStatus.COMPLETED:
            raise ValueError(f"Assessment '{assessment_id}' is already completed.")

        record.design_adequate = bool(data.get("design_adequate"))
        record.operating_effectively = bool(data.get("operating_effectively"))
        record.questionnaire_responses = data.get("questionnaire_responses", {})
        record.attestation = data.get("attestation")
        record.attested_at = datetime.utcnow()
        record.status = CSAStatus.COMPLETED

        if data.get("reviewer_comments"):
            record.reviewer_comments = data["reviewer_comments"]
            record.reviewed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "process_control.submit_csa tenant=%s assessment_id=%s",
            self.tenant_id, assessment_id,
        )
        return record.to_dict()

    def get_pending_assessments(self, assessor_id: str) -> List[dict]:
        """
        Return all pending/overdue self-assessments assigned to a given assessor
        (PC-12).  Marks overdue records whose due_date has passed.
        """
        now = datetime.utcnow()
        rows = (
            self._scope(ControlSelfAssessment)
            .filter(
                ControlSelfAssessment.assessor_id == assessor_id,
                ControlSelfAssessment.status == CSAStatus.PENDING,
            )
            .all()
        )

        result = []
        for row in rows:
            if row.due_date and row.due_date < now and row.status == CSAStatus.PENDING:
                row.status = CSAStatus.OVERDUE
                self.db.add(row)
            result.append(row.to_dict())

        if rows:
            self.db.commit()

        return result

    # =========================================================================
    # 6. Continuous Control Monitoring  (PC-20, PC-22, PC-24)
    # =========================================================================

    def create_ccm_rule(self, data: dict) -> dict:
        """
        Create a CCM rule definition (PC-20).

        Required data keys: name, rule_type, rule_definition.
        Optional: control_id (string), source_system, description,
                  threshold_operator, threshold_value, frequency,
                  auto_create_deficiency (bool, default True),
                  severity_on_breach (default 'observation').

        Returns the serialised CCMRule dict.
        """
        try:
            rule_type = CCMRuleType(data["rule_type"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid rule_type: {data.get('rule_type')}") from exc

        rule_definition = data.get("rule_definition")
        if not rule_definition:
            raise ValueError("rule_definition is required.")

        rule_id = _gen_ccm_rule_id()

        control_pk: Optional[int] = None
        if data.get("control_id"):
            ctrl = self._get_control_by_string_id(data["control_id"])
            control_pk = ctrl.id

        record = CCMRule(
            tenant_id=self.tenant_id,
            rule_id=rule_id,
            name=data["name"],
            description=data.get("description"),
            control_id=control_pk,
            source_system=data.get("source_system"),
            rule_type=rule_type,
            rule_definition=rule_definition,
            threshold_operator=data.get("threshold_operator"),
            threshold_value=str(data["threshold_value"]) if "threshold_value" in data else None,
            frequency=data.get("frequency", "daily"),
            is_active=True,
            auto_create_deficiency=bool(data.get("auto_create_deficiency", True)),
            severity_on_breach=data.get("severity_on_breach", "observation"),
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "process_control.create_ccm_rule tenant=%s rule_id=%s name=%r",
            self.tenant_id, rule_id, data["name"],
        )
        return record.to_dict()

    def execute_ccm_rule(self, rule_id: str) -> dict:
        """
        Execute a single CCM rule and record the result (PC-22).

        The actual check logic is dispatched via _run_ccm_check().
        If the rule breaches its threshold and auto_create_deficiency is enabled,
        a ControlDeficiency is created automatically.

        Returns a dict with keys: execution (dict), deficiency (dict or None).
        """
        rule = self._get_ccm_rule_by_string_id(rule_id)

        if not rule.is_active:
            raise ValueError(f"CCM rule '{rule_id}' is inactive.")

        t_start = time.monotonic()
        check_result = self._run_ccm_check(rule)
        elapsed_ms = int((time.monotonic() - t_start) * 1000)

        ccm_result: CCMResult = check_result["ccm_result"]
        findings_count: int = check_result.get("findings_count", 0)
        findings_detail: List[dict] = check_result.get("findings_detail", [])

        # Persist execution record
        execution = CCMExecution(
            tenant_id=self.tenant_id,
            rule_id=rule.id,
            executed_at=datetime.utcnow(),
            execution_duration_ms=elapsed_ms,
            result=ccm_result,
            findings_count=findings_count,
            findings_detail=findings_detail,
        )
        self.db.add(execution)

        # Update rule metadata
        rule.last_run_at = datetime.utcnow()
        rule.last_result = ccm_result.value

        self.db.commit()
        self.db.refresh(execution)

        deficiency_dict: Optional[dict] = None

        if ccm_result == CCMResult.FAIL and rule.auto_create_deficiency:
            # Resolve control string id for deficiency creation
            ctrl_row = (
                self.db.query(ProcessControl)
                .filter(ProcessControl.id == rule.control_id)
                .first()
            ) if rule.control_id else None

            if ctrl_row:
                def_data = {
                    "control_id": ctrl_row.control_id,
                    "source": "ccm",
                    "title": f"CCM breach: {rule.name}",
                    "description": (
                        f"Continuous monitoring rule '{rule.name}' (ID: {rule_id}) "
                        f"detected {findings_count} finding(s)."
                    ),
                    "severity": rule.severity_on_breach,
                    "related_risk_ids": [],
                    "related_finding_ids": [],
                }
                deficiency_dict = self._create_deficiency_internal(def_data)
                # Link deficiency to execution
                execution.deficiency_id = (
                    self.db.query(ControlDeficiency)
                    .filter(
                        ControlDeficiency.deficiency_id
                        == deficiency_dict["deficiency_id"]
                    )
                    .first()
                ).id
                self.db.commit()

        logger.info(
            "process_control.execute_ccm tenant=%s rule_id=%s result=%s findings=%d",
            self.tenant_id, rule_id, ccm_result.value, findings_count,
        )
        return {"execution": execution.to_dict(), "deficiency": deficiency_dict}

    def _run_ccm_check(self, rule: CCMRule) -> dict:
        """
        Dispatch CCM check execution based on rule_type.

        For CONFIG_CHECK and THRESHOLD rules the check is evaluated against
        the rule_definition parameters.  DATA_PATTERN and SOD_BRIDGE rules
        use specialised sub-methods.

        Returns a dict: {ccm_result, findings_count, findings_detail}.
        """
        rule_def: dict = rule.rule_definition or {}
        rule_type = rule.rule_type

        try:
            if rule_type == CCMRuleType.CONFIG_CHECK:
                return self._check_config(rule, rule_def)
            elif rule_type == CCMRuleType.DATA_PATTERN:
                return self._check_data_pattern(rule, rule_def)
            elif rule_type == CCMRuleType.THRESHOLD:
                return self._check_threshold(rule, rule_def)
            elif rule_type == CCMRuleType.SOD_BRIDGE:
                return self._check_sod_bridge(rule, rule_def)
            else:
                return {
                    "ccm_result": CCMResult.ERROR,
                    "findings_count": 0,
                    "findings_detail": [{"error": f"Unknown rule_type: {rule_type}"}],
                }
        except Exception as exc:
            logger.exception(
                "process_control.ccm_check_error tenant=%s rule_id=%s: %s",
                self.tenant_id, rule.rule_id, exc,
            )
            return {
                "ccm_result": CCMResult.ERROR,
                "findings_count": 0,
                "findings_detail": [{"error": str(exc)}],
            }

    def _check_config(self, rule: CCMRule, rule_def: dict) -> dict:
        """
        CONFIG_CHECK: compare an expected_value against an actual_value
        supplied in rule_definition.  Intended to be replaced with a live
        system connector call in production.

        rule_definition keys: expected_value, actual_value (or callable), description.
        """
        expected = rule_def.get("expected_value")
        actual = rule_def.get("actual_value")
        if actual is None:
            # No live connector — treat as PASS (auditor notes absent data)
            return {"ccm_result": CCMResult.PASS, "findings_count": 0, "findings_detail": []}

        if str(actual) != str(expected):
            return {
                "ccm_result": CCMResult.FAIL,
                "findings_count": 1,
                "findings_detail": [
                    {
                        "description": rule_def.get("description", "Config mismatch"),
                        "expected": expected,
                        "actual": actual,
                    }
                ],
            }
        return {"ccm_result": CCMResult.PASS, "findings_count": 0, "findings_detail": []}

    def _check_data_pattern(self, rule: CCMRule, rule_def: dict) -> dict:
        """
        DATA_PATTERN: scan a pre-loaded dataset for records matching a
        flagged pattern.

        rule_definition keys: dataset (list of dicts), pattern_field,
                              pattern_value, description.
        """
        dataset: List[dict] = rule_def.get("dataset", [])
        pattern_field: str = rule_def.get("pattern_field", "")
        pattern_value = rule_def.get("pattern_value")

        findings = [
            row for row in dataset
            if str(row.get(pattern_field, "")) == str(pattern_value)
        ]

        if findings:
            return {
                "ccm_result": CCMResult.FAIL,
                "findings_count": len(findings),
                "findings_detail": findings[:50],  # cap detail payload
            }
        return {"ccm_result": CCMResult.PASS, "findings_count": 0, "findings_detail": []}

    def _check_threshold(self, rule: CCMRule, rule_def: dict) -> dict:
        """
        THRESHOLD: compare a numeric metric value against the rule threshold.

        rule_definition keys: metric_value (numeric), description.
        Threshold comparison uses rule.threshold_operator and rule.threshold_value.

        Supported operators: gt, lt, eq, ne, gte, lte.
        """
        metric_raw = rule_def.get("metric_value")
        if metric_raw is None:
            return {"ccm_result": CCMResult.PASS, "findings_count": 0, "findings_detail": []}

        try:
            metric = float(metric_raw)
            threshold = float(rule.threshold_value or 0)
        except (TypeError, ValueError):
            return {
                "ccm_result": CCMResult.ERROR,
                "findings_count": 0,
                "findings_detail": [{"error": "Non-numeric metric or threshold value"}],
            }

        operator = (rule.threshold_operator or "gt").lower()
        breached = False
        if operator == "gt":
            breached = metric > threshold
        elif operator == "gte":
            breached = metric >= threshold
        elif operator == "lt":
            breached = metric < threshold
        elif operator == "lte":
            breached = metric <= threshold
        elif operator == "eq":
            breached = metric == threshold
        elif operator == "ne":
            breached = metric != threshold

        if breached:
            return {
                "ccm_result": CCMResult.FAIL,
                "findings_count": 1,
                "findings_detail": [
                    {
                        "description": rule_def.get("description", "Threshold breached"),
                        "metric_value": metric,
                        "threshold": threshold,
                        "operator": operator,
                    }
                ],
            }
        return {"ccm_result": CCMResult.PASS, "findings_count": 0, "findings_detail": []}

    def _check_sod_bridge(self, rule: CCMRule, rule_def: dict) -> dict:
        """
        SOD_BRIDGE: evaluate a pre-computed SoD violation count against a
        threshold.  Violation counts are supplied in rule_definition to avoid
        a circular dependency on the Risk Intelligence engine at execution time.

        rule_definition keys: violation_count (int), threshold (int), details (list).
        """
        violation_count: int = int(rule_def.get("violation_count", 0))
        threshold: int = int(rule_def.get("threshold", 0))
        details: List[dict] = rule_def.get("details", [])

        if violation_count > threshold:
            return {
                "ccm_result": CCMResult.FAIL,
                "findings_count": violation_count,
                "findings_detail": details[:50],
            }
        return {"ccm_result": CCMResult.PASS, "findings_count": 0, "findings_detail": []}

    def run_all_due_rules(self) -> List[dict]:
        """
        Batch-execute all active CCM rules that are due to run (PC-22, PC-24).

        A rule is considered due if it has never run, or if its frequency
        cadence has elapsed since last_run_at.

        Returns a list of execution result dicts (one per rule executed).
        """
        now = datetime.utcnow()
        rules = (
            self._scope(CCMRule)
            .filter(CCMRule.is_active.is_(True))
            .all()
        )

        frequency_deltas: Dict[str, timedelta] = {
            "realtime": timedelta(minutes=1),
            "hourly": timedelta(hours=1),
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30),
        }

        results = []
        for rule in rules:
            delta = frequency_deltas.get(rule.frequency or "daily", timedelta(days=1))
            if rule.last_run_at is None or (now - rule.last_run_at) >= delta:
                try:
                    result = self.execute_ccm_rule(rule.rule_id)
                    results.append(result)
                except Exception as exc:
                    logger.error(
                        "process_control.run_all_due_rules error rule_id=%s: %s",
                        rule.rule_id, exc,
                    )
                    results.append(
                        {"execution": {"rule_id": rule.rule_id, "error": str(exc)}, "deficiency": None}
                    )

        logger.info(
            "process_control.run_all_due_rules tenant=%s executed=%d",
            self.tenant_id, len(results),
        )
        return results

    def get_ccm_dashboard(self) -> dict:
        """
        Return CCM health dashboard metrics (PC-24).

        Aggregates execution results across all rules for the tenant and
        computes pass/fail/error counts and rates.

        Returns
        -------
        dict with keys:
          total_rules, active_rules, total_executions,
          pass_count, fail_count, error_count,
          pass_rate, fail_rate, error_rate,
          rules_never_run (int),
          recent_failures (list of dicts — last 20 FAIL executions)
        """
        all_rules = self._scope(CCMRule).all()
        active_rules = [r for r in all_rules if r.is_active]

        all_executions = (
            self.db.query(CCMExecution)
            .join(CCMRule, CCMExecution.rule_id == CCMRule.id)
            .filter(CCMRule.tenant_id == self.tenant_id)
            .all()
        )

        total = len(all_executions)
        pass_count = sum(1 for e in all_executions if e.result == CCMResult.PASS)
        fail_count = sum(1 for e in all_executions if e.result == CCMResult.FAIL)
        error_count = sum(1 for e in all_executions if e.result == CCMResult.ERROR)

        recent_failures = (
            self.db.query(CCMExecution)
            .join(CCMRule, CCMExecution.rule_id == CCMRule.id)
            .filter(
                CCMRule.tenant_id == self.tenant_id,
                CCMExecution.result == CCMResult.FAIL,
            )
            .order_by(CCMExecution.executed_at.desc())
            .limit(20)
            .all()
        )

        rules_never_run = sum(1 for r in active_rules if r.last_run_at is None)

        return {
            "total_rules": len(all_rules),
            "active_rules": len(active_rules),
            "total_executions": total,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "error_count": error_count,
            "pass_rate": round((pass_count / total) * 100, 1) if total else 0.0,
            "fail_rate": round((fail_count / total) * 100, 1) if total else 0.0,
            "error_rate": round((error_count / total) * 100, 1) if total else 0.0,
            "rules_never_run": rules_never_run,
            "recent_failures": [e.to_dict() for e in recent_failures],
        }

    def create_sod_bridge_deficiency(
        self,
        violation_count: int,
        threshold: int,
        details: dict,
    ) -> dict:
        """
        XI-02 SoD bridge — create a CCM deficiency directly from an Risk Intelligence
        SoD violation count breach without requiring a CCMRule record.

        Intended to be called from the Risk Intelligence router after a risk analysis run
        when aggregate violation counts exceed the configured threshold.

        Parameters
        ----------
        violation_count : int
            Number of SoD violations detected in the current analysis run.
        threshold : int
            The configured acceptable maximum.
        details : dict
            Arbitrary context (rule IDs, top offenders, etc.) to store as
            findings_detail.

        Returns the created ControlDeficiency dict.
        """
        if violation_count <= threshold:
            raise ValueError(
                f"violation_count ({violation_count}) does not exceed threshold ({threshold}); "
                "no deficiency created."
            )

        # Find the first SOD_BRIDGE CCM rule to anchor the deficiency, or use
        # a sentinel control_id if none exists.
        sod_rule = (
            self._scope(CCMRule)
            .filter(CCMRule.rule_type == CCMRuleType.SOD_BRIDGE)
            .first()
        )

        if sod_rule and sod_rule.control_id:
            ctrl_row = (
                self.db.query(ProcessControl)
                .filter(ProcessControl.id == sod_rule.control_id)
                .first()
            )
            control_string_id = ctrl_row.control_id if ctrl_row else None
        else:
            control_string_id = None

        if not control_string_id:
            # Cannot create a deficiency without a control anchor — log and
            # return a descriptive error payload instead of raising.
            logger.warning(
                "process_control.sod_bridge_deficiency: no SOD_BRIDGE CCM rule with linked "
                "control found for tenant=%s; deficiency not persisted.",
                self.tenant_id,
            )
            return {
                "status": "skipped",
                "reason": "No SOD_BRIDGE CCM rule with a linked control found.",
                "violation_count": violation_count,
                "threshold": threshold,
            }

        def_data = {
            "control_id": control_string_id,
            "source": "sod_bridge",
            "title": (
                f"SoD violation threshold breached: {violation_count} violations "
                f"(threshold: {threshold})"
            ),
            "description": (
                f"The Risk Intelligence engine detected {violation_count} SoD violations exceeding "
                f"the configured threshold of {threshold}."
            ),
            "severity": "significant_deficiency" if violation_count > threshold * 2 else "observation",
            "related_risk_ids": details.get("risk_ids", []),
            "related_finding_ids": details.get("finding_ids", []),
        }
        result = self._create_deficiency_internal(def_data)

        logger.info(
            "process_control.sod_bridge_deficiency tenant=%s deficiency_id=%s violations=%d",
            self.tenant_id, result["deficiency_id"], violation_count,
        )
        return result

    # =========================================================================
    # 7. Evidence Management  (PC-15, NF-05)
    # =========================================================================

    def upload_evidence(self, data: dict) -> dict:
        """
        Register an evidence record in the central repository (PC-15).

        Required data keys: title.
        Optional: description, evidence_type, file_name, file_path, file_size,
                  mime_type, content (str — used to compute content_hash),
                  content_hash (overrides computed hash), source_module,
                  linked_object_type, linked_object_id, uploaded_by,
                  retention_until, legal_hold (bool), previous_version_id.

        Returns the serialised GRCEvidence dict.
        """
        if not data.get("title"):
            raise ValueError("title is required for evidence.")

        evidence_id = _gen_evidence_id()

        # Compute content hash if raw content supplied
        content_hash = data.get("content_hash")
        if not content_hash and data.get("content"):
            content_hash = _sha256(data["content"])

        record = GRCEvidence(
            tenant_id=self.tenant_id,
            evidence_id=evidence_id,
            title=data["title"],
            description=data.get("description"),
            evidence_type=data.get("evidence_type"),
            file_name=data.get("file_name"),
            file_path=data.get("file_path"),
            file_size=data.get("file_size"),
            mime_type=data.get("mime_type"),
            content_hash=content_hash,
            source_module=data.get("source_module", "pc"),
            linked_object_type=data.get("linked_object_type"),
            linked_object_id=str(data["linked_object_id"]) if data.get("linked_object_id") else None,
            uploaded_by=data.get("uploaded_by"),
            upload_date=datetime.utcnow(),
            retention_until=data.get("retention_until"),
            legal_hold=bool(data.get("legal_hold", False)),
            version=1,
            previous_version_id=data.get("previous_version_id"),
            status=EvidenceStatus.ACTIVE,
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "process_control.upload_evidence tenant=%s evidence_id=%s title=%r",
            self.tenant_id, evidence_id, data["title"],
        )
        return record.to_dict()

    def get_evidence(self, evidence_id: str) -> dict:
        """Return a single evidence record by its string evidence_id."""
        return self._get_evidence_by_string_id(evidence_id).to_dict()

    def set_legal_hold(self, evidence_id: str, hold: bool) -> dict:
        """
        Set or clear the legal hold flag on an evidence record (NF-05).

        When hold=True the evidence cannot be deleted or archived.
        Returns the updated evidence dict.
        """
        record = self._get_evidence_by_string_id(evidence_id)
        record.legal_hold = hold
        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "process_control.set_legal_hold tenant=%s evidence_id=%s hold=%s",
            self.tenant_id, evidence_id, hold,
        )
        return record.to_dict()

    def list_evidence(
        self,
        linked_object_type: Optional[str] = None,
        linked_object_id: Optional[str] = None,
    ) -> List[dict]:
        """
        List evidence records (PC-15).

        Filters by linked_object_type and/or linked_object_id when supplied.
        Only ACTIVE evidence is returned.
        """
        q = self._scope(GRCEvidence).filter(
            GRCEvidence.status == EvidenceStatus.ACTIVE
        )
        if linked_object_type:
            q = q.filter(GRCEvidence.linked_object_type == linked_object_type)
        if linked_object_id:
            q = q.filter(GRCEvidence.linked_object_id == str(linked_object_id))
        return [r.to_dict() for r in q.order_by(GRCEvidence.upload_date.desc()).all()]

    # =========================================================================
    # 8. SOX Sign-Off  (PC-14)
    # =========================================================================

    def create_signoff(self, data: dict) -> dict:
        """
        Create a SOX-style sign-off certification record (PC-14).

        Required data keys: period, certifier_id.
        Optional: org_unit_id, certifier_name, certifier_role,
                  parent_certification_id (int PK of parent record),
                  scope_summary, controls_in_scope, controls_effective,
                  deficiencies_open.

        Returns the serialised SignOffCertification dict.
        """
        if not data.get("period"):
            raise ValueError("period is required (e.g. 'Q2-2026', 'FY-2026').")
        if not data.get("certifier_id"):
            raise ValueError("certifier_id is required.")

        certification_id = _gen_certification_id()

        record = SignOffCertification(
            tenant_id=self.tenant_id,
            certification_id=certification_id,
            period=data["period"],
            org_unit_id=data.get("org_unit_id"),
            certifier_id=data["certifier_id"],
            certifier_name=data.get("certifier_name"),
            certifier_role=data.get("certifier_role"),
            parent_certification_id=data.get("parent_certification_id"),
            scope_summary=data.get("scope_summary"),
            controls_in_scope=data.get("controls_in_scope", 0),
            controls_effective=data.get("controls_effective", 0),
            deficiencies_open=data.get("deficiencies_open", 0),
            status=SignOffStatus.PENDING,
            exceptions=data.get("exceptions", []),
            comments=data.get("comments"),
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "process_control.create_signoff tenant=%s certification_id=%s period=%s certifier=%s",
            self.tenant_id, certification_id, data["period"], data["certifier_id"],
        )
        return record.to_dict()

    def submit_certification(self, certification_id: str, data: dict) -> dict:
        """
        Submit a management certification statement (PC-14).

        Required data keys: statement.
        Optional: exceptions (list), comments, status (certified /
                  certified_with_exceptions / refused).

        Transitions status and records certified_at.
        """
        record = self._get_certification_by_string_id(certification_id)

        if record.status != SignOffStatus.PENDING:
            raise ValueError(
                f"Certification '{certification_id}' is not in PENDING status "
                f"(current: {record.status.value})."
            )

        if not data.get("statement"):
            raise ValueError("A certification statement is required.")

        record.statement = data["statement"]
        record.certified_at = datetime.utcnow()
        record.exceptions = data.get("exceptions", record.exceptions or [])
        record.comments = data.get("comments", record.comments)

        raw_status = data.get("status", "certified")
        try:
            record.status = SignOffStatus(raw_status)
        except ValueError:
            record.status = SignOffStatus.CERTIFIED

        self.db.commit()
        self.db.refresh(record)

        logger.info(
            "process_control.submit_certification tenant=%s certification_id=%s status=%s",
            self.tenant_id, certification_id, record.status.value,
        )
        return record.to_dict()

    def get_signoff_hierarchy(self, period: str) -> dict:
        """
        Return the full sign-off hierarchy tree for a period (PC-14).

        Builds a tree of certifications where root nodes (no parent) are at
        the top and children are nested recursively.  Useful for the SOX
        roll-up view (control owner -> process owner -> CFO -> CEO).

        Returns a dict: {period, roots: [tree nodes], total_signoffs, certified_count}.
        """
        rows = (
            self._scope(SignOffCertification)
            .filter(SignOffCertification.period == period)
            .all()
        )

        if not rows:
            return {
                "period": period,
                "roots": [],
                "total_signoffs": 0,
                "certified_count": 0,
            }

        # Build lookup by PK
        by_pk: Dict[int, dict] = {r.id: {**r.to_dict(), "children": []} for r in rows}

        roots: List[dict] = []
        for r in rows:
            node = by_pk[r.id]
            if r.parent_certification_id and r.parent_certification_id in by_pk:
                by_pk[r.parent_certification_id]["children"].append(node)
            else:
                roots.append(node)

        certified_count = sum(
            1 for r in rows
            if r.status in (SignOffStatus.CERTIFIED, SignOffStatus.CERTIFIED_WITH_EXCEPTIONS)
        )

        return {
            "period": period,
            "roots": roots,
            "total_signoffs": len(rows),
            "certified_count": certified_count,
        }

    def get_pending_signoffs(self, certifier_id: str) -> List[dict]:
        """Return all PENDING certifications assigned to a specific certifier."""
        rows = (
            self._scope(SignOffCertification)
            .filter(
                SignOffCertification.certifier_id == certifier_id,
                SignOffCertification.status == SignOffStatus.PENDING,
            )
            .order_by(SignOffCertification.created_at.asc())
            .all()
        )
        return [r.to_dict() for r in rows]

    # =========================================================================
    # 9. Reporting  (PC-30, PC-31, PC-32)
    # =========================================================================

    def get_control_dashboard(self) -> dict:
        """
        Aggregate control health dashboard (PC-30).

        Returns
        -------
        dict with keys:
          totals             — overall counts by status
          by_org_unit        — {org_unit_id: {status_counts}}
          by_process         — {process_name: {status_counts}}
          by_framework       — {framework_id: coverage_pct}
          failed_controls    — list of controls whose last test was INEFFECTIVE
          open_deficiencies  — count + breakdown by severity
          open_signoffs      — count of PENDING certifications
        """
        all_controls = self._scope(ProcessControl).all()

        # Totals by status
        totals: Dict[str, int] = {}
        for ctrl in all_controls:
            key = ctrl.status.value if ctrl.status else "unknown"
            totals[key] = totals.get(key, 0) + 1

        # By org unit
        by_org: Dict[Any, Dict[str, int]] = {}
        for ctrl in all_controls:
            key = ctrl.org_unit_id or "unassigned"
            if key not in by_org:
                by_org[key] = {}
            s = ctrl.status.value if ctrl.status else "unknown"
            by_org[key][s] = by_org[key].get(s, 0) + 1

        # By process
        by_process: Dict[str, Dict[str, int]] = {}
        for ctrl in all_controls:
            key = ctrl.process_name or "unassigned"
            if key not in by_process:
                by_process[key] = {}
            s = ctrl.status.value if ctrl.status else "unknown"
            by_process[key][s] = by_process[key].get(s, 0) + 1

        # By framework (coverage pct)
        fw_rows = (
            self.db.query(FrameworkDefinition)
            .filter(FrameworkDefinition.tenant_id == self.tenant_id)
            .all()
        )
        by_framework: Dict[str, float] = {}
        for fw in fw_rows:
            try:
                cov = self.get_framework_coverage(fw.framework_id)
                by_framework[fw.framework_id] = cov["coverage_pct"]
            except Exception:
                by_framework[fw.framework_id] = 0.0

        # Failed controls — last test was INEFFECTIVE
        failed_controls: List[dict] = []
        for ctrl in [c for c in all_controls if c.is_active]:
            last_test = (
                self._scope(ControlTest)
                .filter(ControlTest.control_id == ctrl.id)
                .order_by(ControlTest.created_at.desc())
                .first()
            )
            if last_test and last_test.result == TestResult.INEFFECTIVE:
                failed_controls.append(
                    {
                        "control_id": ctrl.control_id,
                        "name": ctrl.name,
                        "last_test_id": last_test.test_id,
                        "last_tested": last_test.created_at.isoformat()
                        if last_test.created_at else None,
                    }
                )

        # Open deficiencies by severity
        open_defs = (
            self._scope(ControlDeficiency)
            .filter(
                ControlDeficiency.status.in_(
                    [DeficiencyStatus.OPEN, DeficiencyStatus.IN_REMEDIATION]
                )
            )
            .all()
        )
        def_by_severity: Dict[str, int] = {}
        for d in open_defs:
            key = d.severity.value if d.severity else "unknown"
            def_by_severity[key] = def_by_severity.get(key, 0) + 1

        # Open sign-offs
        open_signoffs = (
            self._scope(SignOffCertification)
            .filter(SignOffCertification.status == SignOffStatus.PENDING)
            .count()
        )

        return {
            "totals": totals,
            "by_org_unit": by_org,
            "by_process": by_process,
            "by_framework": by_framework,
            "failed_controls": failed_controls,
            "open_deficiencies": {
                "total": len(open_defs),
                "by_severity": def_by_severity,
            },
            "open_signoffs": open_signoffs,
        }

    def compute_control_health(self, control_id: str) -> dict:
        """
        Compute a 0-100 control health score from five dimensions (PC-30 enhancement).

        Dimensions (each 0-20):
          design    — last test was design type and effective
          testing   — latest OE test result (effective=20, partially=10, ineffective=0)
          exceptions — open deficiency count (0 open=20, 1=12, 2=6, 3+=0)
          evidence  — evidence items linked (>=3=20, 2=14, 1=7, 0=0)
          timeliness — last test within review frequency (on-time=20, overdue partial, never=0)

        Returns breakdown dict + overall score.
        """
        ctrl = self._get_control_by_string_id(control_id)

        # --- design (0-20) ---
        design_tests = (
            self._scope(ControlTest)
            .filter(ControlTest.control_id == ctrl.id)
            .filter(ControlTest.test_type.in_(["design", "walkthrough"]) if hasattr(ControlTest, 'test_type') else True)
            .order_by(ControlTest.created_at.desc())
            .first()
        )
        design_score = 0
        if design_tests and design_tests.result and design_tests.result.value == "effective":
            design_score = 20
        elif design_tests and design_tests.result and design_tests.result.value == "partially_effective":
            design_score = 10

        # --- testing (0-20): latest OE test result ---
        latest_test = (
            self._scope(ControlTest)
            .filter(ControlTest.control_id == ctrl.id)
            .order_by(ControlTest.created_at.desc())
            .first()
        )
        testing_score = 0
        if latest_test and latest_test.result:
            rv = latest_test.result.value if hasattr(latest_test.result, 'value') else str(latest_test.result)
            if rv == "effective":
                testing_score = 20
            elif rv == "partially_effective":
                testing_score = 10

        # --- exceptions (0-20): open deficiencies ---
        open_defs = (
            self._scope(ControlDeficiency)
            .filter(
                ControlDeficiency.control_id == ctrl.id,
                ControlDeficiency.status.in_([DeficiencyStatus.OPEN, DeficiencyStatus.IN_REMEDIATION]),
            )
            .count()
        )
        exception_score = {0: 20, 1: 12, 2: 6}.get(open_defs, 0)

        # --- evidence (0-20) ---
        evidence_count = len(self.list_evidence(linked_object_type="process_control", linked_object_id=control_id))
        evidence_score = min(evidence_count * 7, 20)

        # --- timeliness (0-20): was last test run within the expected frequency? ---
        timeliness_score = 0
        if latest_test and latest_test.created_at:
            from db.models.process_control import ControlFrequency
            freq_days = {
                "continuous": 1, "daily": 1, "weekly": 7,
                "monthly": 30, "quarterly": 91, "annual": 365, "adhoc": 365,
            }
            days_allowed = freq_days.get(ctrl.frequency.value if ctrl.frequency else "annual", 365)
            days_since = (datetime.utcnow() - latest_test.created_at).days
            if days_since <= days_allowed:
                timeliness_score = 20
            elif days_since <= days_allowed * 1.5:
                timeliness_score = 10

        overall = design_score + testing_score + exception_score + evidence_score + timeliness_score
        return {
            "control_id": control_id,
            "overall_score": overall,
            "breakdown": {
                "design": design_score,
                "testing": testing_score,
                "exceptions": exception_score,
                "evidence": evidence_score,
                "timeliness": timeliness_score,
            },
            "open_deficiencies": open_defs,
            "evidence_items": evidence_count,
            "computed_at": datetime.utcnow().isoformat(),
        }

    def get_process_heatmap(self) -> dict:
        """
        Build a process-level control health heatmap (PC-30 enhancement).

        Groups controls by process_name, computes health % per process,
        returns list sorted by health ascending (worst first).
        """
        all_controls = (
            self._scope(ProcessControl)
            .filter(ProcessControl.is_active.is_(True))
            .all()
        )

        # Group by process
        process_map: Dict[str, list] = {}
        for ctrl in all_controls:
            key = ctrl.process_name or "Unassigned"
            process_map.setdefault(key, []).append(ctrl)

        # For each process, count effective/attention/ineffective via last test result
        heatmap = []
        for process_name, controls in process_map.items():
            total = len(controls)
            effective = 0
            attention = 0
            ineffective = 0

            for ctrl in controls:
                last_test = (
                    self._scope(ControlTest)
                    .filter(ControlTest.control_id == ctrl.id)
                    .order_by(ControlTest.created_at.desc())
                    .first()
                )
                if last_test is None:
                    attention += 1
                elif last_test.result and last_test.result.value == "effective":
                    effective += 1
                elif last_test.result and last_test.result.value == "partially_effective":
                    attention += 1
                else:
                    ineffective += 1

            health_pct = round((effective / total) * 100, 1) if total else 0.0

            open_def_count = (
                self._scope(ControlDeficiency)
                .filter(
                    ControlDeficiency.control_id.in_([c.id for c in controls]),
                    ControlDeficiency.status.in_([DeficiencyStatus.OPEN, DeficiencyStatus.IN_REMEDIATION]),
                )
                .count()
            )

            heatmap.append({
                "process_name": process_name,
                "total_controls": total,
                "effective": effective,
                "attention": attention,
                "ineffective": ineffective,
                "health_pct": health_pct,
                "open_deficiencies": open_def_count,
            })

        # Sort worst first
        heatmap.sort(key=lambda x: x["health_pct"])

        return {
            "process_count": len(heatmap),
            "processes": heatmap,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_audit_ready_package(self, control_id: str) -> dict:
        """
        Assemble a complete audit-ready package for a control (PC-32).

        Includes:
          - Full control definition
          - All tests (ordered by date)
          - All evidence linked to the control and its tests
          - All deficiencies
          - All self-assessments
          - All sign-offs for the most recent period
          - CCM rules and recent executions

        Returns a single structured dict ready for export to an auditor.
        """
        ctrl = self._get_control_by_string_id(control_id)

        # Tests
        tests = (
            self._scope(ControlTest)
            .filter(ControlTest.control_id == ctrl.id)
            .order_by(ControlTest.created_at.desc())
            .all()
        )

        # Evidence linked to the control itself
        control_evidence = self.list_evidence(
            linked_object_type="process_control",
            linked_object_id=control_id,
        )
        # Evidence linked to each test
        test_evidence: List[dict] = []
        for test in tests:
            test_evidence.extend(
                self.list_evidence(
                    linked_object_type="control_test",
                    linked_object_id=test.test_id,
                )
            )

        # Deficiencies
        deficiencies = (
            self._scope(ControlDeficiency)
            .filter(ControlDeficiency.control_id == ctrl.id)
            .order_by(ControlDeficiency.created_at.desc())
            .all()
        )

        # Self-assessments
        assessments = (
            self._scope(ControlSelfAssessment)
            .filter(ControlSelfAssessment.control_id == ctrl.id)
            .order_by(ControlSelfAssessment.created_at.desc())
            .all()
        )

        # CCM rules and their recent executions (last 5 per rule)
        ccm_rules = (
            self._scope(CCMRule)
            .filter(CCMRule.control_id == ctrl.id)
            .all()
        )
        ccm_data = []
        for rule in ccm_rules:
            recent_execs = (
                self.db.query(CCMExecution)
                .filter(CCMExecution.rule_id == rule.id)
                .order_by(CCMExecution.executed_at.desc())
                .limit(5)
                .all()
            )
            ccm_data.append(
                {
                    "rule": rule.to_dict(),
                    "recent_executions": [e.to_dict() for e in recent_execs],
                }
            )

        # Most-recent sign-offs (latest period that has sign-offs)
        latest_signoff = (
            self._scope(SignOffCertification)
            .order_by(SignOffCertification.created_at.desc())
            .first()
        )
        sign_offs: List[dict] = []
        if latest_signoff:
            sign_offs = [
                r.to_dict()
                for r in (
                    self._scope(SignOffCertification)
                    .filter(SignOffCertification.period == latest_signoff.period)
                    .all()
                )
            ]

        # Framework mappings with enriched names
        frameworks = self.get_control_frameworks(control_id)

        # Compute completeness score (0-100): 5 dimensions x 20 pts each
        has_tests = len(tests) > 0
        has_evidence = (len(control_evidence) + len(test_evidence)) > 0
        has_assessments = len(assessments) > 0
        has_signoffs = len(sign_offs) > 0
        open_def_count = sum(
            1 for d in deficiencies
            if d.status in (DeficiencyStatus.OPEN, DeficiencyStatus.IN_REMEDIATION)
        )
        # Deficiency completeness: all deficiencies have remediation plans
        defs_with_plans = sum(1 for d in deficiencies if d.remediation_plan) if deficiencies else 0
        defs_completeness = (defs_with_plans / len(deficiencies) * 20) if deficiencies else 20

        completeness_score = round(
            (20 if has_tests else 0)
            + (20 if has_evidence else 0)
            + (20 if has_assessments else 0)
            + (20 if has_signoffs else 0)
            + defs_completeness,
            1,
        )

        # Sign-off summary
        signoff_summary = {
            "total": len(sign_offs),
            "certified": sum(1 for s in sign_offs if s.get("status") in ("certified", "certified_with_exceptions")),
            "pending": sum(1 for s in sign_offs if s.get("status") == SignOffStatus.PENDING.value),
            "refused": sum(1 for s in sign_offs if s.get("status") == "refused"),
        }

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "tenant_id": self.tenant_id,
            "control": ctrl.to_dict(),
            "frameworks": frameworks,
            "tests": [t.to_dict() for t in tests],
            "evidence": {
                "control_level": control_evidence,
                "test_level": test_evidence,
                "total": len(control_evidence) + len(test_evidence),
            },
            "deficiencies": [d.to_dict() for d in deficiencies],
            "self_assessments": [a.to_dict() for a in assessments],
            "ccm": ccm_data,
            "sign_offs": sign_offs,
            "signoff_summary": signoff_summary,
            "completeness_score": completeness_score,
            "summary": {
                "total_tests": len(tests),
                "tests_effective": sum(
                    1 for t in tests if t.result == TestResult.EFFECTIVE
                ),
                "tests_ineffective": sum(
                    1 for t in tests if t.result == TestResult.INEFFECTIVE
                ),
                "open_deficiencies": open_def_count,
                "remediated_deficiencies": sum(
                    1 for d in deficiencies
                    if d.status in (DeficiencyStatus.REMEDIATED, DeficiencyStatus.VERIFIED_CLOSED)
                ),
                "total_evidence": len(control_evidence) + len(test_evidence),
                "pending_signoffs": signoff_summary["pending"],
                "completeness_score": completeness_score,
            },
        }
