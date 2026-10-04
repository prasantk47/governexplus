"""
Process Control API Router

Full process control lifecycle (PC-01 through PC-32):
  - Control library CRUD with versioning
  - Framework mapping
  - Operating effectiveness testing
  - Deficiency management and remediation
  - Control self-assessment campaigns
  - Continuous Control Monitoring (CCM)
  - Evidence repository
  - SOX-style cascading sign-offs
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.process_control import (
    ProcessControl, ControlType, ControlNature, ControlFrequency, ControlStatus,
    ControlTest, TestType, TestResult, TestStatus,
    ControlDeficiency, DeficiencySeverity, DeficiencyStatus,
    ControlSelfAssessment, CSAStatus,
    CCMRule, CCMRuleType, CCMExecution, CCMResult,
    GRCEvidence, EvidenceStatus,
    SignOffCertification, SignOffStatus,
)

router = APIRouter(tags=["Process Control"])


# ---------------------------------------------------------------------------
# Tenant helpers
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _ctrl_or_404(db: Session, control_id: str, tenant_id: str) -> ProcessControl:
    c = db.query(ProcessControl).filter(
        ProcessControl.control_id == control_id,
        ProcessControl.tenant_id == tenant_id,
        ProcessControl.is_active.is_(True),
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"Control '{control_id}' not found")
    return c


def _test_or_404(db: Session, test_id: str, tenant_id: str) -> ControlTest:
    t = db.query(ControlTest).filter(
        ControlTest.test_id == test_id,
        ControlTest.tenant_id == tenant_id,
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail=f"Test '{test_id}' not found")
    return t


def _def_or_404(db: Session, deficiency_id: str, tenant_id: str) -> ControlDeficiency:
    d = db.query(ControlDeficiency).filter(
        ControlDeficiency.deficiency_id == deficiency_id,
        ControlDeficiency.tenant_id == tenant_id,
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail=f"Deficiency '{deficiency_id}' not found")
    return d


def _csa_or_404(db: Session, assessment_id: str, tenant_id: str) -> ControlSelfAssessment:
    a = db.query(ControlSelfAssessment).filter(
        ControlSelfAssessment.assessment_id == assessment_id,
        ControlSelfAssessment.tenant_id == tenant_id,
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail=f"Self-assessment '{assessment_id}' not found")
    return a


def _ccm_or_404(db: Session, rule_id: str, tenant_id: str) -> CCMRule:
    r = db.query(CCMRule).filter(
        CCMRule.rule_id == rule_id,
        CCMRule.tenant_id == tenant_id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"CCM rule '{rule_id}' not found")
    return r


def _evidence_or_404(db: Session, evidence_id: str, tenant_id: str) -> GRCEvidence:
    e = db.query(GRCEvidence).filter(
        GRCEvidence.evidence_id == evidence_id,
        GRCEvidence.tenant_id == tenant_id,
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
    return e


def _signoff_or_404(db: Session, certification_id: str, tenant_id: str) -> SignOffCertification:
    s = db.query(SignOffCertification).filter(
        SignOffCertification.certification_id == certification_id,
        SignOffCertification.tenant_id == tenant_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail=f"Sign-off '{certification_id}' not found")
    return s


# ===========================================================================
# Controls  (PC-01)
# ===========================================================================

@router.post("/controls", status_code=201)
def create_control(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new control library entry."""
    try:
        control_type = ControlType(body.get("control_type", "preventive"))
        control_nature = ControlNature(body.get("control_nature", "manual"))
        frequency = ControlFrequency(body.get("frequency", "monthly"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ctrl = ProcessControl(
        tenant_id=tenant_id,
        control_id=body.get("control_id") or _new_id("CTRL"),
        name=body["name"],
        objective=body.get("objective"),
        description=body.get("description"),
        control_type=control_type,
        control_nature=control_nature,
        frequency=frequency,
        org_unit_id=body.get("org_unit_id"),
        process_name=body.get("process_name"),
        subprocess_name=body.get("subprocess_name"),
        owner_id=body.get("owner_id"),
        owner_name=body.get("owner_name"),
        owner_email=body.get("owner_email"),
        framework_mappings=body.get("framework_mappings", []),
        risk_ids=body.get("risk_ids", []),
        regulation_ids=body.get("regulation_ids", []),
        version=1,
        effective_date=datetime.fromisoformat(body["effective_date"]) if body.get("effective_date") else None,
        key_control=body.get("key_control", False),
        status=ControlStatus.DRAFT,
        is_active=True,
        change_history=[],
    )
    db.add(ctrl)
    db.commit()
    db.refresh(ctrl)
    return ctrl.to_dict()


@router.get("/controls")
def list_controls(
    control_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    process_name: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(ProcessControl).filter(
        ProcessControl.tenant_id == tenant_id,
        ProcessControl.is_active.is_(True),
    )
    if control_type:
        q = q.filter(ProcessControl.control_type == ControlType(control_type))
    if status:
        q = q.filter(ProcessControl.status == ControlStatus(status))
    if process_name:
        q = q.filter(ProcessControl.process_name.ilike(f"%{process_name}%"))
    if owner_id:
        q = q.filter(ProcessControl.owner_id == owner_id)
    if search:
        q = q.filter(ProcessControl.name.ilike(f"%{search}%"))
    controls = q.order_by(ProcessControl.created_at.desc()).all()
    return {"total": len(controls), "controls": [c.to_dict() for c in controls]}


@router.get("/controls/{control_id}")
def get_control(
    control_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    return _ctrl_or_404(db, control_id, tenant_id).to_dict()


@router.put("/controls/{control_id}")
def update_control(
    control_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    ctrl = _ctrl_or_404(db, control_id, tenant_id)
    updatable = [
        "name", "objective", "description", "process_name", "subprocess_name",
        "owner_id", "owner_name", "owner_email", "framework_mappings",
        "risk_ids", "regulation_ids", "key_control",
    ]
    for field in updatable:
        if field in body:
            setattr(ctrl, field, body[field])
    if "control_type" in body:
        ctrl.control_type = ControlType(body["control_type"])
    if "control_nature" in body:
        ctrl.control_nature = ControlNature(body["control_nature"])
    if "frequency" in body:
        ctrl.frequency = ControlFrequency(body["frequency"])
    if "status" in body:
        ctrl.status = ControlStatus(body["status"])
    # Version bump on substantive update
    history = ctrl.change_history or []
    history.append({
        "version": ctrl.version,
        "changed_by": body.get("changed_by", "system"),
        "changed_at": datetime.utcnow().isoformat(),
        "summary": body.get("change_summary", "Updated"),
    })
    ctrl.version += 1
    ctrl.change_history = history
    db.commit()
    db.refresh(ctrl)
    return ctrl.to_dict()


@router.put("/controls/{control_id}/retire")
def retire_control(
    control_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    ctrl = _ctrl_or_404(db, control_id, tenant_id)
    ctrl.status = ControlStatus.RETIRED
    ctrl.is_active = False
    db.commit()
    return {"control_id": control_id, "status": "retired"}


# ===========================================================================
# Framework Mapping  (PC-03)
# ===========================================================================

@router.post("/controls/{control_id}/framework-mappings")
def add_framework_mapping(
    control_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    ctrl = _ctrl_or_404(db, control_id, tenant_id)
    mapping = {
        "framework_id": body["framework_id"],
        "requirement_id": body["requirement_id"],
        "added_at": datetime.utcnow().isoformat(),
    }
    mappings = ctrl.framework_mappings or []
    # Prevent duplicate
    existing_keys = {(m.get("framework_id"), m.get("requirement_id")) for m in mappings}
    if (mapping["framework_id"], mapping["requirement_id"]) not in existing_keys:
        mappings.append(mapping)
        ctrl.framework_mappings = mappings
        db.commit()
    return {"control_id": control_id, "framework_mappings": ctrl.framework_mappings}


@router.delete("/controls/{control_id}/framework-mappings")
def remove_framework_mapping(
    control_id: str,
    framework_id: str = Query(...),
    requirement_id: str = Query(...),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    ctrl = _ctrl_or_404(db, control_id, tenant_id)
    mappings = ctrl.framework_mappings or []
    ctrl.framework_mappings = [
        m for m in mappings
        if not (m.get("framework_id") == framework_id and m.get("requirement_id") == requirement_id)
    ]
    db.commit()
    return {"control_id": control_id, "framework_mappings": ctrl.framework_mappings}


@router.get("/controls/{control_id}/frameworks")
def get_control_frameworks(
    control_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    ctrl = _ctrl_or_404(db, control_id, tenant_id)
    return {"control_id": control_id, "framework_mappings": ctrl.framework_mappings or []}


@router.get("/frameworks/{framework_id}/coverage")
def get_framework_coverage(
    framework_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Controls mapped to a given framework."""
    controls = db.query(ProcessControl).filter(
        ProcessControl.tenant_id == tenant_id,
        ProcessControl.is_active.is_(True),
    ).all()
    matched = [
        c.to_dict() for c in controls
        if any(m.get("framework_id") == framework_id for m in (c.framework_mappings or []))
    ]
    return {"framework_id": framework_id, "control_count": len(matched), "controls": matched}


# ===========================================================================
# Control Tests  (PC-11)
# ===========================================================================

@router.post("/controls/{control_id}/tests", status_code=201)
def create_test(
    control_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    ctrl = _ctrl_or_404(db, control_id, tenant_id)
    try:
        test_type = TestType(body.get("test_type", "operating_effectiveness"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test_type")

    t = ControlTest(
        tenant_id=tenant_id,
        test_id=_new_id("TEST"),
        control_id=ctrl.id,
        test_type=test_type,
        testing_period_start=datetime.fromisoformat(body["testing_period_start"]) if body.get("testing_period_start") else None,
        testing_period_end=datetime.fromisoformat(body["testing_period_end"]) if body.get("testing_period_end") else None,
        sample_size=body.get("sample_size"),
        population_size=body.get("population_size"),
        tester_id=body.get("tester_id"),
        tester_name=body.get("tester_name"),
        test_steps=body.get("test_steps", []),
        status=TestStatus.PLANNED,
        exceptions_found=0,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t.to_dict()


@router.put("/tests/{test_id}/result")
def record_test_result(
    test_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    t = _test_or_404(db, test_id, tenant_id)
    try:
        t.result = TestResult(body["result"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Missing or invalid 'result'")
    t.exceptions_found = body.get("exceptions_found", 0)
    t.exception_details = body.get("exception_details")
    t.conclusion = body.get("conclusion")
    t.evidence_ids = body.get("evidence_ids", [])
    t.status = TestStatus.COMPLETED
    db.commit()
    db.refresh(t)
    # Auto-create deficiency if ineffective
    if t.result in (TestResult.INEFFECTIVE, TestResult.PARTIALLY_EFFECTIVE) and body.get("create_deficiency", True):
        sev = DeficiencySeverity.OBSERVATION if t.result == TestResult.PARTIALLY_EFFECTIVE else DeficiencySeverity.CONTROL_GAP
        deficiency = ControlDeficiency(
            tenant_id=tenant_id,
            deficiency_id=_new_id("DEF"),
            control_id=t.control_id,
            test_id=t.id,
            source="test",
            title=f"Deficiency from test {test_id}",
            description=t.conclusion,
            severity=sev,
            status=DeficiencyStatus.OPEN,
        )
        db.add(deficiency)
        db.commit()
    return t.to_dict()


@router.get("/controls/{control_id}/tests")
def get_control_tests(
    control_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    ctrl = _ctrl_or_404(db, control_id, tenant_id)
    tests = db.query(ControlTest).filter(
        ControlTest.control_id == ctrl.id,
        ControlTest.tenant_id == tenant_id,
    ).order_by(ControlTest.created_at.desc()).all()
    return {"total": len(tests), "tests": [t.to_dict() for t in tests]}


# ===========================================================================
# Deficiencies  (PC-13)
# ===========================================================================

@router.post("/deficiencies", status_code=201)
def create_deficiency(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        severity = DeficiencySeverity(body.get("severity", "control_gap"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid severity")

    # Resolve control pk from control_id string
    ctrl = _ctrl_or_404(db, body["control_id"], tenant_id)

    d = ControlDeficiency(
        tenant_id=tenant_id,
        deficiency_id=_new_id("DEF"),
        control_id=ctrl.id,
        source=body.get("source", "manual"),
        title=body["title"],
        description=body.get("description"),
        severity=severity,
        root_cause=body.get("root_cause"),
        remediation_plan=body.get("remediation_plan"),
        remediation_owner_id=body.get("remediation_owner_id"),
        remediation_owner_name=body.get("remediation_owner_name"),
        due_date=datetime.fromisoformat(body["due_date"]) if body.get("due_date") else None,
        status=DeficiencyStatus.OPEN,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d.to_dict()


@router.get("/deficiencies")
def list_deficiencies(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    control_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(ControlDeficiency).filter(ControlDeficiency.tenant_id == tenant_id)
    if status:
        q = q.filter(ControlDeficiency.status == DeficiencyStatus(status))
    if severity:
        q = q.filter(ControlDeficiency.severity == DeficiencySeverity(severity))
    if control_id:
        ctrl = db.query(ProcessControl).filter(
            ProcessControl.control_id == control_id,
            ProcessControl.tenant_id == tenant_id,
        ).first()
        if ctrl:
            q = q.filter(ControlDeficiency.control_id == ctrl.id)
    deficiencies = q.order_by(ControlDeficiency.created_at.desc()).all()
    return {"total": len(deficiencies), "deficiencies": [d.to_dict() for d in deficiencies]}


@router.put("/deficiencies/{deficiency_id}")
def update_deficiency(
    deficiency_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    d = _def_or_404(db, deficiency_id, tenant_id)
    for field in ["title", "description", "root_cause", "remediation_plan",
                  "remediation_owner_id", "remediation_owner_name", "related_risk_ids"]:
        if field in body:
            setattr(d, field, body[field])
    if "severity" in body:
        d.severity = DeficiencySeverity(body["severity"])
    if "due_date" in body and body["due_date"]:
        d.due_date = datetime.fromisoformat(body["due_date"])
    db.commit()
    db.refresh(d)
    return d.to_dict()


@router.put("/deficiencies/{deficiency_id}/remediate")
def remediate_deficiency(
    deficiency_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    d = _def_or_404(db, deficiency_id, tenant_id)
    d.status = DeficiencyStatus.REMEDIATED
    d.completed_at = datetime.utcnow()
    d.remediation_plan = body.get("remediation_notes", d.remediation_plan)
    db.commit()
    db.refresh(d)
    return d.to_dict()


@router.put("/deficiencies/{deficiency_id}/verify")
def verify_deficiency(
    deficiency_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    d = _def_or_404(db, deficiency_id, tenant_id)
    d.status = DeficiencyStatus.VERIFIED_CLOSED
    d.verified_by = body.get("verified_by")
    d.verified_at = datetime.utcnow()
    db.commit()
    db.refresh(d)
    return d.to_dict()


# ===========================================================================
# Self-Assessments  (PC-12)
# ===========================================================================

@router.post("/self-assessment-campaigns")
def create_self_assessment_campaign(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Launch a CSA campaign across a set of controls."""
    campaign_name = body.get("campaign_name", f"CSA Campaign {datetime.utcnow().date()}")
    campaign_type = body.get("campaign_type", "quarterly")
    due_date = datetime.fromisoformat(body["due_date"]) if body.get("due_date") else None

    q = db.query(ProcessControl).filter(
        ProcessControl.tenant_id == tenant_id,
        ProcessControl.is_active.is_(True),
        ProcessControl.status == ControlStatus.ACTIVE,
    )
    if body.get("control_ids"):
        q = q.filter(ProcessControl.control_id.in_(body["control_ids"]))

    controls = q.all()
    created = []
    for ctrl in controls:
        a = ControlSelfAssessment(
            tenant_id=tenant_id,
            assessment_id=_new_id("CSA"),
            campaign_name=campaign_name,
            campaign_type=campaign_type,
            control_id=ctrl.id,
            assessor_id=ctrl.owner_id,
            assessor_name=ctrl.owner_name,
            status=CSAStatus.PENDING,
            due_date=due_date,
        )
        db.add(a)
        created.append(a.assessment_id)

    db.commit()
    return {
        "campaign_name": campaign_name,
        "assessments_created": len(created),
        "assessment_ids": created,
    }


@router.put("/self-assessments/{assessment_id}/submit")
def submit_self_assessment(
    assessment_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    a = _csa_or_404(db, assessment_id, tenant_id)
    a.design_adequate = body.get("design_adequate", True)
    a.operating_effectively = body.get("operating_effectively", True)
    a.questionnaire_responses = body.get("questionnaire_responses", {})
    a.attestation = body.get("attestation")
    a.attested_at = datetime.utcnow()
    a.status = CSAStatus.COMPLETED
    db.commit()
    db.refresh(a)
    return a.to_dict()


@router.get("/self-assessments/pending")
def get_pending_self_assessments(
    assessor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(ControlSelfAssessment).filter(
        ControlSelfAssessment.tenant_id == tenant_id,
        ControlSelfAssessment.status == CSAStatus.PENDING,
    )
    if assessor_id:
        q = q.filter(ControlSelfAssessment.assessor_id == assessor_id)
    assessments = q.all()
    return {"total": len(assessments), "assessments": [a.to_dict() for a in assessments]}


# ===========================================================================
# CCM  (PC-20, PC-22)
# ===========================================================================

@router.post("/ccm-rules/validate")
def validate_ccm_rule(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Validate a CCM rule definition without executing it (no-code builder support).

    Accepts rule definition JSON and returns validation result + estimated match count.
    Does not persist anything — dry-run only.
    """
    errors = []
    warnings = []

    # Validate required fields
    if not body.get("name"):
        errors.append("'name' is required")
    rule_type_str = body.get("rule_type")
    if not rule_type_str:
        errors.append("'rule_type' is required")
    else:
        try:
            CCMRuleType(rule_type_str)
        except ValueError:
            errors.append(f"Invalid rule_type '{rule_type_str}'. Valid: config_check, data_pattern, threshold, sod_bridge")

    rule_def = body.get("rule_definition")
    if rule_def is None:
        errors.append("'rule_definition' is required")
    elif not isinstance(rule_def, dict):
        errors.append("'rule_definition' must be a JSON object")

    # Type-specific validation
    if not errors and rule_type_str == "threshold":
        if body.get("threshold_value") is None:
            warnings.append("'threshold_value' not set; rule will always pass")
        if not body.get("threshold_operator"):
            warnings.append("'threshold_operator' not set; defaulting to 'gt'")

    if not errors and rule_type_str == "data_pattern":
        rd = rule_def or {}
        if not rd.get("pattern_field"):
            errors.append("data_pattern rules require 'rule_definition.pattern_field'")
        if rd.get("pattern_value") is None:
            warnings.append("'rule_definition.pattern_value' not set; all records will match")

    if not errors and rule_type_str == "config_check":
        rd = rule_def or {}
        if rd.get("expected_value") is None:
            warnings.append("'rule_definition.expected_value' not set; check will always pass")

    # Estimate match count from dataset if provided
    estimated_match_count = None
    if not errors and rule_type_str == "data_pattern" and isinstance(rule_def, dict):
        dataset = rule_def.get("dataset", [])
        if dataset:
            pattern_field = rule_def.get("pattern_field", "")
            pattern_value = rule_def.get("pattern_value")
            estimated_match_count = sum(
                1 for row in dataset
                if str(row.get(pattern_field, "")) == str(pattern_value)
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "estimated_match_count": estimated_match_count,
        "rule_name": body.get("name"),
        "rule_type": rule_type_str,
    }


@router.get("/ccm-rules")
def list_ccm_rules(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """List all CCM rules for this tenant."""
    rules = db.query(CCMRule).filter(CCMRule.tenant_id == tenant_id).all()
    return [r.to_dict() for r in rules]


@router.post("/ccm-rules", status_code=201)
def create_ccm_rule(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        rule_type = CCMRuleType(body.get("rule_type", "config_check"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule_type")

    # Resolve optional control FK
    control_pk = None
    if body.get("control_id"):
        ctrl = db.query(ProcessControl).filter(
            ProcessControl.control_id == body["control_id"],
            ProcessControl.tenant_id == tenant_id,
        ).first()
        if ctrl:
            control_pk = ctrl.id

    rule = CCMRule(
        tenant_id=tenant_id,
        rule_id=body.get("rule_id") or _new_id("CCM"),
        name=body["name"],
        description=body.get("description"),
        control_id=control_pk,
        source_system=body.get("source_system"),
        rule_type=rule_type,
        rule_definition=body.get("rule_definition", {}),
        threshold_operator=body.get("threshold_operator"),
        threshold_value=body.get("threshold_value"),
        frequency=body.get("frequency", "daily"),
        is_active=True,
        auto_create_deficiency=body.get("auto_create_deficiency", True),
        severity_on_breach=body.get("severity_on_breach", "observation"),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule.to_dict()


@router.post("/ccm-rules/{rule_id}/execute")
def execute_ccm_rule(
    rule_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Simulate a CCM rule execution and record the result."""
    rule = _ccm_or_404(db, rule_id, tenant_id)
    result_val = body.get("result", "pass")
    try:
        result = CCMResult(result_val)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid result")

    findings_count = body.get("findings_count", 0)
    exec_record = CCMExecution(
        tenant_id=tenant_id,
        rule_id=rule.id,
        executed_at=datetime.utcnow(),
        execution_duration_ms=body.get("duration_ms"),
        result=result,
        findings_count=findings_count,
        findings_detail=body.get("findings_detail"),
    )
    db.add(exec_record)
    rule.last_run_at = datetime.utcnow()
    rule.last_result = result_val

    # Auto-create deficiency on breach
    deficiency_id = None
    if result == CCMResult.FAIL and rule.auto_create_deficiency:
        try:
            sev = DeficiencySeverity(rule.severity_on_breach)
        except ValueError:
            sev = DeficiencySeverity.OBSERVATION
        deficiency = ControlDeficiency(
            tenant_id=tenant_id,
            deficiency_id=_new_id("DEF"),
            control_id=rule.control_id,
            source="ccm",
            title=f"CCM breach: {rule.name}",
            description=f"Rule {rule_id} failed with {findings_count} findings",
            severity=sev,
            status=DeficiencyStatus.OPEN,
        )
        db.add(deficiency)
        db.flush()
        exec_record.deficiency_id = deficiency.id
        deficiency_id = deficiency.deficiency_id

    db.commit()
    db.refresh(exec_record)
    return {
        "execution": exec_record.to_dict(),
        "auto_deficiency_id": deficiency_id,
    }


@router.post("/ccm/run-all")
def run_all_ccm(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Trigger all active CCM rules (dry-run — records pass for each)."""
    rules = db.query(CCMRule).filter(
        CCMRule.tenant_id == tenant_id,
        CCMRule.is_active.is_(True),
    ).all()
    results = []
    for rule in rules:
        exec_record = CCMExecution(
            tenant_id=tenant_id,
            rule_id=rule.id,
            executed_at=datetime.utcnow(),
            result=CCMResult.PASS,
            findings_count=0,
        )
        db.add(exec_record)
        rule.last_run_at = datetime.utcnow()
        rule.last_result = "pass"
        results.append(rule.rule_id)
    db.commit()
    return {"executed_rules": len(results), "rule_ids": results}


@router.get("/ccm/dashboard")
def get_ccm_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    rules = db.query(CCMRule).filter(
        CCMRule.tenant_id == tenant_id,
        CCMRule.is_active.is_(True),
    ).all()
    total = len(rules)
    passing = sum(1 for r in rules if r.last_result == "pass")
    failing = sum(1 for r in rules if r.last_result == "fail")
    never_run = sum(1 for r in rules if r.last_run_at is None)
    return {
        "total_rules": total,
        "passing": passing,
        "failing": failing,
        "never_run": never_run,
        "pass_rate": round(passing / total * 100, 1) if total else 0,
        "rules": [r.to_dict() for r in rules],
    }


@router.post("/ccm/sod-bridge")
def ccm_sod_bridge(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Bridge SoD violations from the ARA module into CCM as a monitoring rule result."""
    violation_ids = body.get("violation_ids", [])
    control_id_str = body.get("control_id")
    ctrl_pk = None
    if control_id_str:
        ctrl = db.query(ProcessControl).filter(
            ProcessControl.control_id == control_id_str,
            ProcessControl.tenant_id == tenant_id,
        ).first()
        if ctrl:
            ctrl_pk = ctrl.id

    # Ensure a SOD_BRIDGE CCM rule exists for this control
    rule = db.query(CCMRule).filter(
        CCMRule.tenant_id == tenant_id,
        CCMRule.rule_type == CCMRuleType.SOD_BRIDGE,
        CCMRule.control_id == ctrl_pk,
    ).first()

    if not rule:
        rule = CCMRule(
            tenant_id=tenant_id,
            rule_id=_new_id("CCM"),
            name=f"SoD Bridge for control {control_id_str or 'N/A'}",
            rule_type=CCMRuleType.SOD_BRIDGE,
            control_id=ctrl_pk,
            rule_definition={"source": "ara_module"},
            is_active=True,
            auto_create_deficiency=True,
            severity_on_breach="significant_deficiency",
        )
        db.add(rule)
        db.flush()

    result = CCMResult.FAIL if violation_ids else CCMResult.PASS
    exec_record = CCMExecution(
        tenant_id=tenant_id,
        rule_id=rule.id,
        executed_at=datetime.utcnow(),
        result=result,
        findings_count=len(violation_ids),
        findings_detail={"violation_ids": violation_ids},
    )
    db.add(exec_record)
    rule.last_run_at = datetime.utcnow()
    rule.last_result = result.value
    db.commit()
    return {
        "rule_id": rule.rule_id,
        "violations_bridged": len(violation_ids),
        "result": result.value,
    }


# ===========================================================================
# Evidence  (PC-15)
# ===========================================================================

@router.post("/evidence", status_code=201)
def create_evidence(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    e = GRCEvidence(
        tenant_id=tenant_id,
        evidence_id=_new_id("EVID"),
        title=body["title"],
        description=body.get("description"),
        evidence_type=body.get("evidence_type", "document"),
        file_name=body.get("file_name"),
        file_path=body.get("file_path"),
        file_size=body.get("file_size"),
        mime_type=body.get("mime_type"),
        content_hash=body.get("content_hash"),
        source_module=body.get("source_module", "pc"),
        linked_object_type=body.get("linked_object_type"),
        linked_object_id=body.get("linked_object_id"),
        uploaded_by=body.get("uploaded_by"),
        upload_date=datetime.utcnow(),
        retention_until=datetime.fromisoformat(body["retention_until"]) if body.get("retention_until") else None,
        legal_hold=body.get("legal_hold", False),
        status=EvidenceStatus.ACTIVE,
        version=1,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e.to_dict()


@router.get("/evidence")
def list_evidence(
    source_module: Optional[str] = Query(None),
    linked_object_type: Optional[str] = Query(None),
    linked_object_id: Optional[str] = Query(None),
    legal_hold: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(GRCEvidence).filter(
        GRCEvidence.tenant_id == tenant_id,
        GRCEvidence.status == EvidenceStatus.ACTIVE,
    )
    if source_module:
        q = q.filter(GRCEvidence.source_module == source_module)
    if linked_object_type:
        q = q.filter(GRCEvidence.linked_object_type == linked_object_type)
    if linked_object_id:
        q = q.filter(GRCEvidence.linked_object_id == linked_object_id)
    if legal_hold is not None:
        q = q.filter(GRCEvidence.legal_hold == legal_hold)
    items = q.order_by(GRCEvidence.upload_date.desc()).all()
    return {"total": len(items), "evidence": [e.to_dict() for e in items]}


@router.get("/evidence/{evidence_id}")
def get_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    return _evidence_or_404(db, evidence_id, tenant_id).to_dict()


@router.put("/evidence/{evidence_id}/legal-hold")
def set_legal_hold(
    evidence_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    e = _evidence_or_404(db, evidence_id, tenant_id)
    e.legal_hold = body.get("legal_hold", True)
    db.commit()
    return {"evidence_id": evidence_id, "legal_hold": e.legal_hold}


# ===========================================================================
# Sign-offs  (PC-14)
# ===========================================================================

@router.post("/signoffs", status_code=201)
def create_signoff(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    s = SignOffCertification(
        tenant_id=tenant_id,
        certification_id=_new_id("CERT"),
        period=body["period"],
        org_unit_id=body.get("org_unit_id"),
        certifier_id=body["certifier_id"],
        certifier_name=body.get("certifier_name"),
        certifier_role=body.get("certifier_role"),
        parent_certification_id=body.get("parent_certification_id"),
        scope_summary=body.get("scope_summary"),
        controls_in_scope=body.get("controls_in_scope", 0),
        controls_effective=body.get("controls_effective", 0),
        deficiencies_open=body.get("deficiencies_open", 0),
        status=SignOffStatus.PENDING,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s.to_dict()


@router.put("/signoffs/{certification_id}/submit")
def submit_signoff(
    certification_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    s = _signoff_or_404(db, certification_id, tenant_id)
    s.statement = body.get("statement")
    s.exceptions = body.get("exceptions", [])
    s.comments = body.get("comments")
    has_exceptions = bool(s.exceptions)
    s.status = SignOffStatus.CERTIFIED_WITH_EXCEPTIONS if has_exceptions else SignOffStatus.CERTIFIED
    s.certified_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return s.to_dict()


@router.get("/signoffs/hierarchy")
def get_signoff_hierarchy(
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(SignOffCertification).filter(
        SignOffCertification.tenant_id == tenant_id,
    )
    if period:
        q = q.filter(SignOffCertification.period == period)
    signoffs = q.all()
    # Build tree: top-level (no parent) with children attached
    by_id = {s.id: s.to_dict() for s in signoffs}
    for s in signoffs:
        by_id[s.id]["children"] = []
    roots = []
    for s in signoffs:
        if s.parent_certification_id and s.parent_certification_id in by_id:
            by_id[s.parent_certification_id]["children"].append(by_id[s.id])
        elif not s.parent_certification_id:
            roots.append(by_id[s.id])
    return {"period": period, "hierarchy": roots}


@router.get("/signoffs/pending")
def get_pending_signoffs(
    certifier_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(SignOffCertification).filter(
        SignOffCertification.tenant_id == tenant_id,
        SignOffCertification.status == SignOffStatus.PENDING,
    )
    if certifier_id:
        q = q.filter(SignOffCertification.certifier_id == certifier_id)
    signoffs = q.all()
    return {"total": len(signoffs), "signoffs": [s.to_dict() for s in signoffs]}


# ===========================================================================
# Dashboard  (PC-31, PC-32)
# ===========================================================================

@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Aggregate process control health metrics."""
    total_controls = db.query(ProcessControl).filter(
        ProcessControl.tenant_id == tenant_id,
        ProcessControl.is_active.is_(True),
    ).count()
    active_controls = db.query(ProcessControl).filter(
        ProcessControl.tenant_id == tenant_id,
        ProcessControl.is_active.is_(True),
        ProcessControl.status == ControlStatus.ACTIVE,
    ).count()
    open_deficiencies = db.query(ControlDeficiency).filter(
        ControlDeficiency.tenant_id == tenant_id,
        ControlDeficiency.status == DeficiencyStatus.OPEN,
    ).count()
    pending_tests = db.query(ControlTest).filter(
        ControlTest.tenant_id == tenant_id,
        ControlTest.status == TestStatus.PLANNED,
    ).count()
    pending_signoffs = db.query(SignOffCertification).filter(
        SignOffCertification.tenant_id == tenant_id,
        SignOffCertification.status == SignOffStatus.PENDING,
    ).count()
    effective_count = db.query(ControlTest).filter(
        ControlTest.tenant_id == tenant_id,
        ControlTest.result == TestResult.EFFECTIVE,
    ).count()
    total_tested = db.query(ControlTest).filter(
        ControlTest.tenant_id == tenant_id,
        ControlTest.result.isnot(None),
    ).count()

    return {
        "total_controls": total_controls,
        "active_controls": active_controls,
        "open_deficiencies": open_deficiencies,
        "pending_tests": pending_tests,
        "pending_signoffs": pending_signoffs,
        "effectiveness_rate": round(effective_count / total_tested * 100, 1) if total_tested else None,
    }


@router.get("/controls/{control_id}/audit-package")
def get_audit_package(
    control_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Return a complete audit evidence package for a control."""
    ctrl = _ctrl_or_404(db, control_id, tenant_id)
    tests = db.query(ControlTest).filter(
        ControlTest.control_id == ctrl.id,
        ControlTest.tenant_id == tenant_id,
    ).order_by(ControlTest.created_at.desc()).limit(5).all()
    deficiencies = db.query(ControlDeficiency).filter(
        ControlDeficiency.control_id == ctrl.id,
        ControlDeficiency.tenant_id == tenant_id,
    ).all()
    evidence = db.query(GRCEvidence).filter(
        GRCEvidence.tenant_id == tenant_id,
        GRCEvidence.linked_object_type == "process_control",
        GRCEvidence.linked_object_id == ctrl.control_id,
    ).all()
    return {
        "control": ctrl.to_dict(),
        "recent_tests": [t.to_dict() for t in tests],
        "deficiencies": [d.to_dict() for d in deficiencies],
        "evidence": [e.to_dict() for e in evidence],
        "generated_at": datetime.utcnow().isoformat(),
    }
