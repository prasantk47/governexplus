"""
License Intelligence Router — LI-001 through LI-008
======================================================
FUE classification, consumption, usage, reclamation, contracts, rule packs,
driver analysis, and dashboard endpoints.

All endpoints are tenant-scoped via JWT. Heavy operations (classify, scan)
run via BackgroundTasks. No stubs, no mocks.
"""
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from db.database import get_db
from db.models.license_intelligence import (
    LIRulePack, LIRulePackVersion, LIAuthMapping, LITenantOverride,
    LIContract, LIContractAmendment, LIEntitlementSnapshot,
    LIClassification, LIClassificationDriver,
    LIConsumptionSnapshot, LIPositionSnapshot,
    LIUsageDaily, LIUsageRaw,
    LIReclamationCase, LIReclamationAction,
    LICollectionStatus,
)
from core.license_intelligence.fue_engine import (
    FUEClassificationEngine,
    seed_base_rule_pack,
    DEFAULT_CONVERSION_RATIOS,
)


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/license-intelligence", tags=["License Intelligence"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _id() -> str:
    return str(uuid.uuid4())


def _row(obj) -> dict:
    """Convert an ORM row to a plain dict, stripping SQLAlchemy internals."""
    d = {k: v for k, v in obj.__dict__.items() if k != "_sa_instance_state"}
    # Serialise enums and dates
    for k, v in d.items():
        if hasattr(v, "value"):
            d[k] = v.value
        elif isinstance(v, (datetime, date)):
            d[k] = v.isoformat()
    return d


def _get_tenant_id(request: Request) -> str:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant context missing from token")
    return tenant_id


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class RulePackCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_platform: str = "S4HANA"


class RulePackVersionCreate(BaseModel):
    version: str
    effective_from: date
    effective_to: Optional[date] = None
    conversion_ratios: Dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_CONVERSION_RATIOS))
    notes: Optional[str] = None


class AuthMappingCreate(BaseModel):
    auth_object: str
    auth_field: Optional[str] = None
    auth_value: Optional[str] = None
    auth_value_pattern: Optional[str] = None
    mapped_use_type: str
    source_reference: Optional[str] = None
    description: Optional[str] = None
    priority: int = 100


class ContractCreate(BaseModel):
    contract_reference: str
    contract_type: str = "S4HANA_FUE"
    start_date: date
    end_date: Optional[date] = None
    renewal_date: Optional[date] = None
    contracted_fue: float
    price_per_fue: Optional[float] = None
    currency: str = "USD"
    conversion_ratios: Optional[Dict[str, float]] = None
    counting_rule: str = "highest_across_systems"
    developer_terms: Optional[str] = None
    system_ids: Optional[List[str]] = None
    rule_pack_version_id: Optional[str] = None
    alert_threshold_pct: float = 85.0
    notes: Optional[str] = None


class ContractUpdate(BaseModel):
    contract_reference: Optional[str] = None
    status: Optional[str] = None
    end_date: Optional[date] = None
    renewal_date: Optional[date] = None
    contracted_fue: Optional[float] = None
    price_per_fue: Optional[float] = None
    conversion_ratios: Optional[Dict[str, float]] = None
    alert_threshold_pct: Optional[float] = None
    notes: Optional[str] = None
    rule_pack_version_id: Optional[str] = None


class AmendmentCreate(BaseModel):
    amendment_date: date
    amendment_type: str  # increase, decrease, renewal, ratio_change
    new_values: Dict[str, Any]
    reason: Optional[str] = None


class ClassifyRequest(BaseModel):
    contract_id: Optional[str] = None
    usernames: Optional[List[str]] = None


class ReclamationExceptionRequest(BaseModel):
    reason: str


class ReclamationRejectRequest(BaseModel):
    reason: Optional[str] = None


# ── Background task helpers ───────────────────────────────────────────────────

def _bg_classify(tenant_id: str, contract_id: Optional[str], usernames: Optional[List[str]]):
    """Background: run FUE classification and persist results."""
    from db.database import SessionLocal
    db = SessionLocal()
    try:
        engine = FUEClassificationEngine(session=db, tenant_id=tenant_id)
        engine.run_classification(contract_id=contract_id, usernames=usernames)
    finally:
        db.close()


def _bg_scan_reclamation(tenant_id: str, inactivity_days: int):
    """Background: scan for reclamation candidates."""
    from db.database import SessionLocal
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=inactivity_days)
        # Find currently-classified users who haven't been active
        candidates = db.query(LIClassification).filter(
            LIClassification.tenant_id == tenant_id,
            LIClassification.is_current == True,
            LIClassification.use_type.in_(["advanced", "developer"]),
        ).all()

        created = 0
        for cls in candidates:
            # Skip if already an open case
            existing = db.query(LIReclamationCase).filter(
                LIReclamationCase.tenant_id == tenant_id,
                LIReclamationCase.username == cls.username,
                LIReclamationCase.status.in_(["candidate", "under_review"]),
            ).first()
            if existing:
                continue

            inactive = cls.inactive_days or 0
            trigger = None
            if cls.last_activity_date and cls.last_activity_date < cutoff:
                trigger = "inactivity"
            elif inactive >= inactivity_days:
                trigger = "inactivity"

            if not trigger:
                continue

            case = LIReclamationCase(
                id=_id(),
                tenant_id=tenant_id,
                username=cls.username,
                user_id=cls.user_id,
                system_id=cls.system_id,
                trigger=trigger,
                status="candidate",
                current_use_type=cls.use_type,
                current_fue=cls.fue_value,
                projected_use_type="self_service",
                projected_fue=DEFAULT_CONVERSION_RATIOS.get("self_service", 0.0333),
                fue_released=round(cls.fue_value - DEFAULT_CONVERSION_RATIOS.get("self_service", 0.0333), 4),
                inactive_days=inactive,
                last_activity_date=cls.last_activity_date,
            )
            db.add(case)
            created += 1

        db.commit()
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# LI-008: Rule Packs
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/rule-packs")
def list_rule_packs(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    rows = db.query(LIRulePack).filter(
        LIRulePack.tenant_id == tenant_id,
    ).order_by(desc(LIRulePack.created_at)).all()
    return [_row(r) for r in rows]


@router.post("/rule-packs", status_code=201)
def create_rule_pack(
    payload: RulePackCreate,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    created_by = getattr(request.state, "user_id", "api")
    pack = LIRulePack(
        id=_id(),
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        target_platform=payload.target_platform,
        is_base_pack=False,
        status="draft",
        created_by=created_by,
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return _row(pack)


@router.get("/rule-packs/{pack_id}/versions")
def list_rule_pack_versions(
    pack_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    pack = db.query(LIRulePack).filter(
        LIRulePack.id == pack_id,
        LIRulePack.tenant_id == tenant_id,
    ).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Rule pack not found")

    rows = db.query(LIRulePackVersion).filter(
        LIRulePackVersion.rule_pack_id == pack_id,
        LIRulePackVersion.tenant_id == tenant_id,
    ).order_by(desc(LIRulePackVersion.effective_from)).all()
    return [_row(r) for r in rows]


@router.post("/rule-packs/{pack_id}/versions", status_code=201)
def create_rule_pack_version(
    pack_id: str,
    payload: RulePackVersionCreate,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    pack = db.query(LIRulePack).filter(
        LIRulePack.id == pack_id,
        LIRulePack.tenant_id == tenant_id,
    ).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Rule pack not found")

    # Duplicate version guard
    existing = db.query(LIRulePackVersion).filter(
        LIRulePackVersion.rule_pack_id == pack_id,
        LIRulePackVersion.version == payload.version,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Version already exists for this pack")

    drafted_by = getattr(request.state, "user_id", "api")
    version = LIRulePackVersion(
        id=_id(),
        tenant_id=tenant_id,
        rule_pack_id=pack_id,
        version=payload.version,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        conversion_ratios=payload.conversion_ratios,
        notes=payload.notes,
        status="draft",
        drafted_by=drafted_by,
        mapping_count=0,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return _row(version)


@router.get("/rule-packs/versions/{version_id}/mappings")
def list_auth_mappings(
    version_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    version = db.query(LIRulePackVersion).filter(
        LIRulePackVersion.id == version_id,
        LIRulePackVersion.tenant_id == tenant_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Rule pack version not found")

    rows = db.query(LIAuthMapping).filter(
        LIAuthMapping.rule_pack_version_id == version_id,
    ).order_by(desc(LIAuthMapping.priority)).all()
    return [_row(r) for r in rows]


@router.post("/rule-packs/versions/{version_id}/mappings", status_code=201)
def add_auth_mapping(
    version_id: str,
    payload: AuthMappingCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    version = db.query(LIRulePackVersion).filter(
        LIRulePackVersion.id == version_id,
        LIRulePackVersion.tenant_id == tenant_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Rule pack version not found")
    if version.status == "active":
        raise HTTPException(status_code=409, detail="Cannot add mappings to an active version; create a new version")

    mapping = LIAuthMapping(
        id=_id(),
        tenant_id=tenant_id,
        rule_pack_version_id=version_id,
        auth_object=payload.auth_object,
        auth_field=payload.auth_field,
        auth_value=payload.auth_value,
        auth_value_pattern=payload.auth_value_pattern,
        mapped_use_type=payload.mapped_use_type,
        source_reference=payload.source_reference,
        description=payload.description,
        is_active=True,
        priority=payload.priority,
    )
    db.add(mapping)

    # Update mapping count
    db.query(LIRulePackVersion).filter(LIRulePackVersion.id == version_id).update(
        {"mapping_count": LIRulePackVersion.mapping_count + 1}
    )
    db.commit()
    db.refresh(mapping)
    return _row(mapping)


@router.post("/rule-packs/versions/{version_id}/activate")
def activate_rule_pack_version(
    version_id: str,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    version = db.query(LIRulePackVersion).filter(
        LIRulePackVersion.id == version_id,
        LIRulePackVersion.tenant_id == tenant_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Rule pack version not found")
    if version.status == "active":
        raise HTTPException(status_code=409, detail="Version is already active")

    approved_by = getattr(request.state, "user_id", "api")

    # Supersede any currently active versions for the same pack
    db.query(LIRulePackVersion).filter(
        LIRulePackVersion.rule_pack_id == version.rule_pack_id,
        LIRulePackVersion.tenant_id == tenant_id,
        LIRulePackVersion.status == "active",
    ).update({"status": "superseded"})

    version.status = "active"
    version.approved_by = approved_by
    version.approved_at = datetime.utcnow()
    db.commit()
    return {"message": "Version activated", "version_id": version_id}


@router.post("/rule-packs/seed", status_code=201)
def seed_rule_pack(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    pack = seed_base_rule_pack(db, tenant_id)
    return {"message": "Base rule pack seeded", "pack_id": pack.id}


# ═══════════════════════════════════════════════════════════════════════════════
# LI-005: Contracts
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/contracts")
def list_contracts(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(LIContract).filter(LIContract.tenant_id == tenant_id)
    if status:
        q = q.filter(LIContract.status == status)
    rows = q.order_by(desc(LIContract.start_date)).all()
    return [_row(r) for r in rows]


@router.post("/contracts", status_code=201)
def create_contract(
    payload: ContractCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    contract = LIContract(
        id=_id(),
        tenant_id=tenant_id,
        contract_reference=payload.contract_reference,
        contract_type=payload.contract_type,
        status="active",
        start_date=payload.start_date,
        end_date=payload.end_date,
        renewal_date=payload.renewal_date,
        contracted_fue=payload.contracted_fue,
        price_per_fue=payload.price_per_fue,
        currency=payload.currency,
        conversion_ratios=payload.conversion_ratios,
        counting_rule=payload.counting_rule,
        developer_terms=payload.developer_terms,
        system_ids=payload.system_ids,
        rule_pack_version_id=payload.rule_pack_version_id,
        alert_threshold_pct=payload.alert_threshold_pct,
        notes=payload.notes,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return _row(contract)


@router.get("/contracts/{contract_id}")
def get_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    contract = db.query(LIContract).filter(
        LIContract.id == contract_id,
        LIContract.tenant_id == tenant_id,
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return _row(contract)


@router.put("/contracts/{contract_id}")
def update_contract(
    contract_id: str,
    payload: ContractUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    contract = db.query(LIContract).filter(
        LIContract.id == contract_id,
        LIContract.tenant_id == tenant_id,
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    for field, value in payload.dict(exclude_none=True).items():
        setattr(contract, field, value)
    contract.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(contract)
    return _row(contract)


@router.get("/contracts/{contract_id}/amendments")
def list_amendments(
    contract_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    contract = db.query(LIContract).filter(
        LIContract.id == contract_id,
        LIContract.tenant_id == tenant_id,
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    rows = db.query(LIContractAmendment).filter(
        LIContractAmendment.contract_id == contract_id,
    ).order_by(desc(LIContractAmendment.amendment_date)).all()
    return [_row(r) for r in rows]


@router.post("/contracts/{contract_id}/amend", status_code=201)
def create_amendment(
    contract_id: str,
    payload: AmendmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    contract = db.query(LIContract).filter(
        LIContract.id == contract_id,
        LIContract.tenant_id == tenant_id,
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    amended_by = getattr(request.state, "user_id", "api")

    # Capture current values for the fields being changed
    previous_values = {}
    for field in payload.new_values:
        previous_values[field] = getattr(contract, field, None)
        # Serialise non-JSON-safe types
        pv = previous_values[field]
        if isinstance(pv, (datetime, date)):
            previous_values[field] = pv.isoformat()

    amendment = LIContractAmendment(
        id=_id(),
        tenant_id=tenant_id,
        contract_id=contract_id,
        amendment_date=payload.amendment_date,
        amendment_type=payload.amendment_type,
        previous_values=previous_values,
        new_values=payload.new_values,
        reason=payload.reason,
        amended_by=amended_by,
    )
    db.add(amendment)

    # Apply new values to the contract
    for field, value in payload.new_values.items():
        if hasattr(contract, field):
            setattr(contract, field, value)
    contract.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(amendment)
    return _row(amendment)


# ═══════════════════════════════════════════════════════════════════════════════
# LI-001: Classification
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/classify")
def run_classification(
    payload: ClassifyRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(_get_tenant_id),
):
    background_tasks.add_task(
        _bg_classify, tenant_id, payload.contract_id, payload.usernames
    )
    return {"message": "Classification job queued", "tenant_id": tenant_id}


@router.get("/classifications")
def list_classifications(
    use_type: Optional[str] = None,
    department: Optional[str] = None,
    flagged: Optional[bool] = None,
    review_candidate: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(LIClassification).filter(
        LIClassification.tenant_id == tenant_id,
        LIClassification.is_current == True,
    )
    if use_type:
        q = q.filter(LIClassification.use_type == use_type)
    if department:
        q = q.filter(LIClassification.department == department)
    if flagged is not None:
        q = q.filter(LIClassification.is_flagged == flagged)
    if review_candidate is not None:
        q = q.filter(LIClassification.is_review_candidate == review_candidate)

    total = q.count()
    rows = q.order_by(desc(LIClassification.calculation_date)).offset(skip).limit(limit).all()
    return {"total": total, "skip": skip, "limit": limit, "items": [_row(r) for r in rows]}


@router.get("/classifications/summary")
def classification_summary(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    rows = db.query(
        LIClassification.use_type,
        func.count(LIClassification.id).label("count"),
        func.sum(LIClassification.fue_value).label("total_fue"),
    ).filter(
        LIClassification.tenant_id == tenant_id,
        LIClassification.is_current == True,
    ).group_by(LIClassification.use_type).all()

    result = {}
    for use_type, count, total_fue in rows:
        result[use_type] = {"count": count, "total_fue": round(total_fue or 0.0, 2)}

    total_users = sum(v["count"] for v in result.values())
    total_fue = sum(v["total_fue"] for v in result.values())
    return {"by_use_type": result, "total_users": total_users, "total_fue": round(total_fue, 2)}


@router.get("/classifications/by-department")
def classifications_by_department(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    rows = db.query(
        LIClassification.department,
        LIClassification.use_type,
        func.count(LIClassification.id).label("count"),
        func.sum(LIClassification.fue_value).label("total_fue"),
    ).filter(
        LIClassification.tenant_id == tenant_id,
        LIClassification.is_current == True,
    ).group_by(LIClassification.department, LIClassification.use_type).all()

    result: Dict[str, Any] = {}
    for dept, use_type, count, total_fue in rows:
        dept_key = dept or "Unknown"
        if dept_key not in result:
            result[dept_key] = {"department": dept_key, "breakdown": {}, "total_users": 0, "total_fue": 0.0}
        result[dept_key]["breakdown"][use_type] = {
            "count": count,
            "total_fue": round(total_fue or 0.0, 2),
        }
        result[dept_key]["total_users"] += count
        result[dept_key]["total_fue"] += total_fue or 0.0

    for d in result.values():
        d["total_fue"] = round(d["total_fue"], 2)

    return sorted(result.values(), key=lambda x: x["total_fue"], reverse=True)


@router.get("/classifications/by-role")
def classifications_by_role(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Top roles by FUE impact — roles that push users to advanced/developer."""
    rows = db.query(
        LIClassificationDriver.role_name,
        LIClassificationDriver.mapped_use_type,
        func.count(LIClassificationDriver.id).label("user_count"),
        func.sum(LIClassificationDriver.fue_difference).label("total_fue_impact"),
    ).filter(
        LIClassificationDriver.tenant_id == tenant_id,
        LIClassificationDriver.mapped_use_type.in_(["advanced", "developer"]),
        LIClassificationDriver.fue_difference > 0,
    ).group_by(
        LIClassificationDriver.role_name,
        LIClassificationDriver.mapped_use_type,
    ).order_by(desc("total_fue_impact")).limit(limit).all()

    return [
        {
            "role_name": role_name,
            "mapped_use_type": mapped_use_type,
            "user_count": user_count,
            "total_fue_impact": round(total_fue_impact or 0.0, 4),
        }
        for role_name, mapped_use_type, user_count, total_fue_impact in rows
    ]


@router.get("/classifications/{classification_id}")
def get_classification(
    classification_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    cls = db.query(LIClassification).filter(
        LIClassification.id == classification_id,
        LIClassification.tenant_id == tenant_id,
    ).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Classification not found")

    drivers = db.query(LIClassificationDriver).filter(
        LIClassificationDriver.classification_id == classification_id,
    ).order_by(desc(LIClassificationDriver.fue_difference)).all()

    result = _row(cls)
    result["drivers"] = [_row(d) for d in drivers]
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# LI-002: Consumption
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/consumption/calculate/{contract_id}")
def calculate_consumption(
    contract_id: str,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(_get_tenant_id),
    db: Session = Depends(get_db),
):
    contract = db.query(LIContract).filter(
        LIContract.id == contract_id,
        LIContract.tenant_id == tenant_id,
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Run synchronously so we can return the result immediately
    engine = FUEClassificationEngine(session=db, tenant_id=tenant_id)
    result = engine.calculate_consumption(contract_id)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@router.get("/consumption/latest/{contract_id}")
def latest_consumption(
    contract_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    snapshot = db.query(LIConsumptionSnapshot).filter(
        LIConsumptionSnapshot.tenant_id == tenant_id,
        LIConsumptionSnapshot.contract_id == contract_id,
        LIConsumptionSnapshot.is_latest == True,
    ).order_by(desc(LIConsumptionSnapshot.snapshot_date)).first()

    if not snapshot:
        raise HTTPException(status_code=404, detail="No consumption snapshot found; run calculate first")
    return _row(snapshot)


@router.get("/consumption/history/{contract_id}")
def consumption_history(
    contract_id: str,
    days: int = Query(90, ge=7, le=730),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.query(LIConsumptionSnapshot).filter(
        LIConsumptionSnapshot.tenant_id == tenant_id,
        LIConsumptionSnapshot.contract_id == contract_id,
        LIConsumptionSnapshot.snapshot_date >= since,
    ).order_by(LIConsumptionSnapshot.snapshot_date).all()
    return [_row(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════════
# LI-006: Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Full dashboard payload for the License Intelligence overview screen."""
    # Latest position from most recent contract
    latest_pos = db.query(LIPositionSnapshot).filter(
        LIPositionSnapshot.tenant_id == tenant_id,
    ).order_by(desc(LIPositionSnapshot.snapshot_date)).first()

    # Classification summary
    summary_rows = db.query(
        LIClassification.use_type,
        func.count(LIClassification.id).label("count"),
        func.sum(LIClassification.fue_value).label("total_fue"),
    ).filter(
        LIClassification.tenant_id == tenant_id,
        LIClassification.is_current == True,
    ).group_by(LIClassification.use_type).all()

    by_use_type = {}
    for use_type, count, total_fue in summary_rows:
        by_use_type[use_type] = {"count": count, "total_fue": round(total_fue or 0.0, 2)}

    # Top drivers
    top_drivers = db.query(
        LIClassificationDriver.role_name,
        LIClassificationDriver.mapped_use_type,
        func.count(LIClassificationDriver.id).label("user_count"),
        func.sum(LIClassificationDriver.fue_difference).label("fue_impact"),
    ).filter(
        LIClassificationDriver.tenant_id == tenant_id,
        LIClassificationDriver.fue_difference > 0,
    ).group_by(
        LIClassificationDriver.role_name,
        LIClassificationDriver.mapped_use_type,
    ).order_by(desc("fue_impact")).limit(10).all()

    # Review candidates and reclamation summary
    review_candidates = db.query(func.count(LIClassification.id)).filter(
        LIClassification.tenant_id == tenant_id,
        LIClassification.is_current == True,
        LIClassification.is_review_candidate == True,
    ).scalar() or 0

    flagged_count = db.query(func.count(LIClassification.id)).filter(
        LIClassification.tenant_id == tenant_id,
        LIClassification.is_current == True,
        LIClassification.is_flagged == True,
    ).scalar() or 0

    open_cases = db.query(func.count(LIReclamationCase.id)).filter(
        LIReclamationCase.tenant_id == tenant_id,
        LIReclamationCase.status.in_(["candidate", "under_review"]),
    ).scalar() or 0

    fue_released = db.query(func.sum(LIReclamationCase.fue_released)).filter(
        LIReclamationCase.tenant_id == tenant_id,
        LIReclamationCase.status == "completed",
    ).scalar() or 0.0

    # Data freshness
    collection_rows = db.query(LICollectionStatus).filter(
        LICollectionStatus.tenant_id == tenant_id,
    ).all()
    data_freshness = {
        r.system_id: {
            "source_type": r.source_type,
            "last_success_at": r.last_success_at.isoformat() if r.last_success_at else None,
            "status": r.status,
        }
        for r in collection_rows
    }

    return {
        "position": _row(latest_pos) if latest_pos else None,
        "classification_summary": {
            "by_use_type": by_use_type,
            "total_users": sum(v["count"] for v in by_use_type.values()),
            "total_fue": round(sum(v["total_fue"] for v in by_use_type.values()), 2),
        },
        "top_drivers": [
            {
                "role_name": role_name,
                "mapped_use_type": mapped_use_type,
                "user_count": user_count,
                "fue_impact": round(fue_impact or 0.0, 4),
            }
            for role_name, mapped_use_type, user_count, fue_impact in top_drivers
        ],
        "reclamation_summary": {
            "open_cases": open_cases,
            "fue_released_completed": round(fue_released, 2),
        },
        "review_candidates": review_candidates,
        "flagged_users": flagged_count,
        "data_freshness": data_freshness,
    }


@router.get("/dashboard/position")
def dashboard_position(
    contract_id: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Contracted vs consumed vs available FUE with utilisation percentage."""
    q = db.query(LIPositionSnapshot).filter(LIPositionSnapshot.tenant_id == tenant_id)
    if contract_id:
        q = q.filter(LIPositionSnapshot.contract_id == contract_id)

    pos = q.order_by(desc(LIPositionSnapshot.snapshot_date)).first()
    if not pos:
        # Try to derive from latest consumption snapshot
        cs_q = db.query(LIConsumptionSnapshot).filter(
            LIConsumptionSnapshot.tenant_id == tenant_id,
            LIConsumptionSnapshot.is_latest == True,
        )
        if contract_id:
            cs_q = cs_q.filter(LIConsumptionSnapshot.contract_id == contract_id)
        cs = cs_q.order_by(desc(LIConsumptionSnapshot.snapshot_date)).first()
        if not cs:
            return {"message": "No position data; run a consumption calculation first"}
        return {
            "contracted_fue": cs.contracted_fue,
            "consumed_fue": cs.consumed_fue,
            "available_fue": cs.available_fue,
            "utilisation_pct": cs.utilisation_pct,
            "over_consumed": cs.over_consumed,
            "snapshot_date": cs.snapshot_date.isoformat() if cs.snapshot_date else None,
        }

    return {
        "contracted_fue": pos.contracted_fue,
        "consumed_fue": pos.consumed_fue,
        "available_fue": pos.available_fue,
        "utilisation_pct": pos.utilisation_pct,
        "advanced_count": pos.advanced_count,
        "core_count": pos.core_count,
        "self_service_count": pos.self_service_count,
        "developer_count": pos.developer_count,
        "unclassified_count": pos.unclassified_count,
        "total_users": pos.total_users,
        "snapshot_date": pos.snapshot_date.isoformat() if isinstance(pos.snapshot_date, date) else pos.snapshot_date,
        "rule_pack_version": pos.rule_pack_version,
    }


@router.get("/dashboard/trends")
def dashboard_trends(
    contract_id: Optional[str] = None,
    days: int = Query(90, ge=7, le=730),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Historical FUE consumption trend from position snapshots."""
    since = date.today() - timedelta(days=days)
    q = db.query(LIPositionSnapshot).filter(
        LIPositionSnapshot.tenant_id == tenant_id,
        LIPositionSnapshot.snapshot_date >= since,
    )
    if contract_id:
        q = q.filter(LIPositionSnapshot.contract_id == contract_id)

    rows = q.order_by(LIPositionSnapshot.snapshot_date).all()
    return [
        {
            "date": r.snapshot_date.isoformat() if isinstance(r.snapshot_date, date) else r.snapshot_date,
            "contracted_fue": r.contracted_fue,
            "consumed_fue": r.consumed_fue,
            "available_fue": r.available_fue,
            "utilisation_pct": r.utilisation_pct,
            "total_users": r.total_users,
        }
        for r in rows
    ]


@router.get("/dashboard/drivers")
def dashboard_drivers(
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Top licence drivers ranked by total FUE impact across all users."""
    rows = db.query(
        LIClassificationDriver.role_name,
        LIClassificationDriver.auth_object,
        LIClassificationDriver.mapped_use_type,
        func.count(LIClassificationDriver.id).label("user_count"),
        func.sum(LIClassificationDriver.fue_difference).label("total_fue_impact"),
    ).filter(
        LIClassificationDriver.tenant_id == tenant_id,
        LIClassificationDriver.fue_difference > 0,
    ).group_by(
        LIClassificationDriver.role_name,
        LIClassificationDriver.auth_object,
        LIClassificationDriver.mapped_use_type,
    ).order_by(desc("total_fue_impact")).limit(limit).all()

    return [
        {
            "role_name": role_name,
            "auth_object": auth_object,
            "mapped_use_type": mapped_use_type,
            "user_count": user_count,
            "total_fue_impact": round(total_fue_impact or 0.0, 4),
        }
        for role_name, auth_object, mapped_use_type, user_count, total_fue_impact in rows
    ]


@router.get("/dashboard/candidates")
def dashboard_candidates(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Review candidates: inactive, flagged, and open reclamation cases."""
    inactive = db.query(LIClassification).filter(
        LIClassification.tenant_id == tenant_id,
        LIClassification.is_current == True,
        LIClassification.inactive_days >= 90,
    ).order_by(desc(LIClassification.inactive_days)).limit(50).all()

    flagged = db.query(LIClassification).filter(
        LIClassification.tenant_id == tenant_id,
        LIClassification.is_current == True,
        LIClassification.is_flagged == True,
    ).limit(50).all()

    open_cases = db.query(LIReclamationCase).filter(
        LIReclamationCase.tenant_id == tenant_id,
        LIReclamationCase.status.in_(["candidate", "under_review"]),
    ).order_by(desc(LIReclamationCase.current_fue)).limit(50).all()

    return {
        "inactive_users": [
            {
                "username": r.username,
                "use_type": r.use_type,
                "fue_value": r.fue_value,
                "inactive_days": r.inactive_days,
                "department": r.department,
            }
            for r in inactive
        ],
        "flagged_users": [
            {
                "username": r.username,
                "use_type": r.use_type,
                "flag_reason": r.flag_reason,
                "department": r.department,
            }
            for r in flagged
        ],
        "open_reclamation_cases": [_row(c) for c in open_cases],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LI-007: Reclamation
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/reclamation/cases")
def list_reclamation_cases(
    status: Optional[str] = None,
    trigger: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(LIReclamationCase).filter(LIReclamationCase.tenant_id == tenant_id)
    if status:
        q = q.filter(LIReclamationCase.status == status)
    if trigger:
        q = q.filter(LIReclamationCase.trigger == trigger)

    total = q.count()
    rows = q.order_by(desc(LIReclamationCase.created_at)).offset(skip).limit(limit).all()
    return {"total": total, "skip": skip, "limit": limit, "items": [_row(r) for r in rows]}


@router.post("/reclamation/scan")
def scan_reclamation(
    inactivity_days: int = Query(90, ge=1, le=365),
    background_tasks: BackgroundTasks = None,
    tenant_id: str = Depends(_get_tenant_id),
):
    background_tasks.add_task(_bg_scan_reclamation, tenant_id, inactivity_days)
    return {"message": "Reclamation scan queued", "inactivity_threshold_days": inactivity_days}


@router.post("/reclamation/cases/{case_id}/approve")
def approve_reclamation_case(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    case = db.query(LIReclamationCase).filter(
        LIReclamationCase.id == case_id,
        LIReclamationCase.tenant_id == tenant_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Reclamation case not found")
    if case.status not in ("candidate", "under_review"):
        raise HTTPException(status_code=409, detail=f"Case is in status '{case.status}'; cannot approve")

    reviewer = getattr(request.state, "user_id", "api")
    case.status = "approved"
    case.reviewer = reviewer
    case.reviewed_at = datetime.utcnow()
    db.commit()
    return {"message": "Case approved", "case_id": case_id, "fue_to_release": case.fue_released}


@router.post("/reclamation/cases/{case_id}/reject")
def reject_reclamation_case(
    case_id: str,
    payload: ReclamationRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    case = db.query(LIReclamationCase).filter(
        LIReclamationCase.id == case_id,
        LIReclamationCase.tenant_id == tenant_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Reclamation case not found")
    if case.status not in ("candidate", "under_review"):
        raise HTTPException(status_code=409, detail=f"Case is in status '{case.status}'; cannot reject")

    reviewer = getattr(request.state, "user_id", "api")
    case.status = "rejected"
    case.reviewer = reviewer
    case.reviewed_at = datetime.utcnow()
    if payload.reason:
        case.exception_reason = payload.reason
    db.commit()
    return {"message": "Case rejected", "case_id": case_id}


@router.post("/reclamation/cases/{case_id}/exception")
def exception_reclamation_case(
    case_id: str,
    payload: ReclamationExceptionRequest,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    case = db.query(LIReclamationCase).filter(
        LIReclamationCase.id == case_id,
        LIReclamationCase.tenant_id == tenant_id,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Reclamation case not found")

    reviewer = getattr(request.state, "user_id", "api")
    case.status = "exception"
    case.is_exception = True
    case.exception_reason = payload.reason
    case.reviewer = reviewer
    case.reviewed_at = datetime.utcnow()
    db.commit()
    return {"message": "Case marked as exception", "case_id": case_id, "reason": payload.reason}


# ═══════════════════════════════════════════════════════════════════════════════
# LI-003: Usage
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/usage/daily")
def list_daily_usage(
    username: Optional[str] = None,
    system_id: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    is_advanced_mapped: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(LIUsageDaily).filter(LIUsageDaily.tenant_id == tenant_id)
    if username:
        q = q.filter(LIUsageDaily.username == username)
    if system_id:
        q = q.filter(LIUsageDaily.system_id == system_id)
    if from_date:
        q = q.filter(LIUsageDaily.usage_date >= from_date)
    if to_date:
        q = q.filter(LIUsageDaily.usage_date <= to_date)
    if is_advanced_mapped is not None:
        q = q.filter(LIUsageDaily.is_advanced_mapped == is_advanced_mapped)

    total = q.count()
    rows = q.order_by(desc(LIUsageDaily.usage_date)).offset(skip).limit(limit).all()
    return {"total": total, "skip": skip, "limit": limit, "items": [_row(r) for r in rows]}


@router.get("/usage/summary/{username}")
def usage_summary(
    username: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """90/180/365-day usage metrics for a user."""
    today = date.today()
    result = {}
    for window_days in (90, 180, 365):
        since = today - timedelta(days=window_days)
        rows = db.query(
            func.count(LIUsageDaily.id).label("active_days"),
            func.sum(LIUsageDaily.execution_count).label("total_executions"),
            func.count(LIUsageDaily.transaction_code.distinct()).label("distinct_tcodes"),
        ).filter(
            LIUsageDaily.tenant_id == tenant_id,
            LIUsageDaily.username == username,
            LIUsageDaily.usage_date >= since,
        ).first()

        advanced_days = db.query(func.count(LIUsageDaily.id)).filter(
            LIUsageDaily.tenant_id == tenant_id,
            LIUsageDaily.username == username,
            LIUsageDaily.usage_date >= since,
            LIUsageDaily.is_advanced_mapped == True,
        ).scalar() or 0

        result[f"{window_days}d"] = {
            "active_days": rows.active_days or 0,
            "total_executions": rows.total_executions or 0,
            "distinct_tcodes": rows.distinct_tcodes or 0,
            "advanced_active_days": advanced_days,
            "advanced_usage_pct": round(advanced_days / window_days * 100, 1) if window_days else 0,
        }

    # Current classification
    cls = db.query(LIClassification).filter(
        LIClassification.tenant_id == tenant_id,
        LIClassification.username == username,
        LIClassification.is_current == True,
    ).first()

    return {
        "username": username,
        "current_use_type": cls.use_type if cls else None,
        "current_fue": cls.fue_value if cls else None,
        "usage_windows": result,
    }


@router.get("/usage/advanced-unused")
def advanced_unused(
    inactive_days: int = Query(60, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Users classified as advanced but with no advanced transaction usage in the last N days."""
    since = date.today() - timedelta(days=inactive_days)

    # Users with advanced classification
    advanced_users = db.query(LIClassification.username, LIClassification.fue_value,
                               LIClassification.department).filter(
        LIClassification.tenant_id == tenant_id,
        LIClassification.is_current == True,
        LIClassification.use_type.in_(["advanced", "developer"]),
    ).all()

    if not advanced_users:
        return []

    advanced_usernames = [r.username for r in advanced_users]

    # Users who have had advanced-mapped usage in the period
    active_users = db.query(LIUsageDaily.username.distinct()).filter(
        LIUsageDaily.tenant_id == tenant_id,
        LIUsageDaily.username.in_(advanced_usernames),
        LIUsageDaily.usage_date >= since,
        LIUsageDaily.is_advanced_mapped == True,
    ).all()
    active_set = {r.username for r in active_users}

    result = [
        {
            "username": r.username,
            "current_use_type": "advanced",
            "fue_value": r.fue_value,
            "department": r.department,
            "last_advanced_usage_in_period": False,
        }
        for r in advanced_users
        if r.username not in active_set
    ]

    return result[:limit]


@router.get("/collection-status")
def collection_status(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    rows = db.query(LICollectionStatus).filter(
        LICollectionStatus.tenant_id == tenant_id,
    ).order_by(LICollectionStatus.system_id).all()
    return [_row(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════════
# LI-004: Driver Analysis
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/drivers/{username}")
def drivers_for_user(
    username: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Full driver analysis for a single user."""
    cls = db.query(LIClassification).filter(
        LIClassification.tenant_id == tenant_id,
        LIClassification.username == username,
        LIClassification.is_current == True,
    ).first()
    if not cls:
        raise HTTPException(status_code=404, detail="No current classification found for user")

    drivers = db.query(LIClassificationDriver).filter(
        LIClassificationDriver.classification_id == cls.id,
    ).order_by(desc(LIClassificationDriver.fue_difference)).all()

    # Group drivers by role
    by_role: Dict[str, Any] = {}
    for drv in drivers:
        rn = drv.role_name or "Unknown"
        if rn not in by_role:
            by_role[rn] = {
                "role_name": rn,
                "highest_use_type": drv.mapped_use_type,
                "max_fue_difference": drv.fue_difference or 0.0,
                "auth_count": 0,
                "auths": [],
            }
        by_role[rn]["auth_count"] += 1
        by_role[rn]["auths"].append({
            "auth_object": drv.auth_object,
            "auth_field": drv.auth_field,
            "auth_value": drv.auth_value,
            "mapped_use_type": drv.mapped_use_type,
            "fue_difference": drv.fue_difference,
            "use_type_without_this": drv.use_type_without_this,
        })

    return {
        "username": username,
        "use_type": cls.use_type,
        "fue_value": cls.fue_value,
        "department": cls.department,
        "business_unit": cls.business_unit,
        "is_flagged": cls.is_flagged,
        "flag_reason": cls.flag_reason,
        "is_review_candidate": cls.is_review_candidate,
        "calculation_date": cls.calculation_date.isoformat() if cls.calculation_date else None,
        "total_drivers": len(drivers),
        "by_role": sorted(by_role.values(), key=lambda x: x["max_fue_difference"], reverse=True),
        "all_drivers": [_row(d) for d in drivers],
    }


@router.get("/drivers/role-impact")
def role_impact(
    limit: int = Query(25, ge=1, le=100),
    use_type: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Roles ranked by how many users they push to higher use types."""
    q = db.query(
        LIClassificationDriver.role_name,
        LIClassificationDriver.mapped_use_type,
        func.count(LIClassificationDriver.id).label("driver_count"),
        func.count(LIClassificationDriver.classification_id.distinct()).label("user_count"),
        func.sum(LIClassificationDriver.fue_difference).label("total_fue_impact"),
        func.avg(LIClassificationDriver.fue_difference).label("avg_fue_per_user"),
    ).filter(
        LIClassificationDriver.tenant_id == tenant_id,
        LIClassificationDriver.fue_difference > 0,
    )

    if use_type:
        q = q.filter(LIClassificationDriver.mapped_use_type == use_type)

    rows = q.group_by(
        LIClassificationDriver.role_name,
        LIClassificationDriver.mapped_use_type,
    ).order_by(desc("total_fue_impact")).limit(limit).all()

    return [
        {
            "role_name": role_name,
            "mapped_use_type": mapped_use_type,
            "driver_count": driver_count,
            "user_count": user_count,
            "total_fue_impact": round(total_fue_impact or 0.0, 4),
            "avg_fue_per_user": round(avg_fue_per_user or 0.0, 4),
        }
        for role_name, mapped_use_type, driver_count, user_count, total_fue_impact, avg_fue_per_user in rows
    ]
