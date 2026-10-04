"""
Risk Scenarios, Monte Carlo Simulation, Opportunities, and Business Objectives Router

Covers:
  RM-SAP-GAP-02 : Multi-driver cascading risk scenarios
  RM-SAP-GAP-03 : Monte Carlo simulation engine (pure-Python, no numpy)
  RM-SAP-GAP-04 : Positive risk / opportunity tracking
  RM-SAP-GAP-01 : Business objective — risk linkage
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid
import random
import math
import statistics
import time as _time

from db.database import get_db
from db.models.risk_management import (
    RiskScenario, ScenarioType, ScenarioVelocity, ScenarioStatus,
    MonteCarloSimulation, DistributionType,
    RiskOpportunity, OpportunityCategory, OpportunityStatus,
    BusinessObjective, ObjectiveCategory, ObjectiveStatus,
    EnterpriseRisk,
)

router = APIRouter(tags=["Risk Scenarios & Opportunities"])


# ---------------------------------------------------------------------------
# Tenant helpers
# ---------------------------------------------------------------------------

def _get_tenant_id() -> str:
    from core.tenant import get_current_tenant
    ctx = get_current_tenant()
    return ctx.tenant_id if ctx else "default"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _scenario_or_404(db: Session, scenario_id: str, tenant_id: str) -> RiskScenario:
    s = db.query(RiskScenario).filter(
        RiskScenario.scenario_id == scenario_id,
        RiskScenario.tenant_id == tenant_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return s


def _opportunity_or_404(db: Session, opportunity_id: str, tenant_id: str) -> RiskOpportunity:
    o = db.query(RiskOpportunity).filter(
        RiskOpportunity.opportunity_id == opportunity_id,
        RiskOpportunity.tenant_id == tenant_id,
    ).first()
    if not o:
        raise HTTPException(status_code=404, detail=f"Opportunity '{opportunity_id}' not found")
    return o


def _objective_or_404(db: Session, objective_id: str, tenant_id: str) -> BusinessObjective:
    o = db.query(BusinessObjective).filter(
        BusinessObjective.objective_id == objective_id,
        BusinessObjective.tenant_id == tenant_id,
        BusinessObjective.is_active.is_(True),
    ).first()
    if not o:
        raise HTTPException(status_code=404, detail=f"Objective '{objective_id}' not found")
    return o


# ---------------------------------------------------------------------------
# Pure-Python Monte Carlo Engine
# ---------------------------------------------------------------------------

def _run_monte_carlo(distribution_type: str, params: Dict[str, Any], iterations: int = 10000) -> Dict[str, Any]:
    """
    Pure-Python Monte Carlo engine.  No numpy dependency.

    Supported distributions: normal, triangular, uniform, lognormal, pert.
    Returns full distributional output: p5/p25/p50/p75/p95, mean, std_dev,
    var_95 (VaR), cvar_95 (CVaR), max_loss.
    """
    samples: List[float] = []
    start_ns = _time.monotonic_ns()

    for _ in range(iterations):
        if distribution_type == "normal":
            s = random.gauss(params["mean"], params["std_dev"])
        elif distribution_type == "triangular":
            low = params["low"]
            high = params["high"]
            mode = params.get("mode", (low + high) / 2)
            s = random.triangular(low, high, mode)
        elif distribution_type == "uniform":
            s = random.uniform(params["low"], params["high"])
        elif distribution_type == "lognormal":
            # random.lognormvariate takes mu=log(mean), sigma
            mu = math.log(max(params["mean"], 1e-9))
            s = random.lognormvariate(mu, params["std_dev"])
        elif distribution_type == "pert":
            a = params["low"]
            c = params["high"]
            b = params.get("mode", (a + c) / 2)
            mu = (a + 4 * b + c) / 6
            if c > a:
                denom = (b - mu) * (c - a)
                if abs(denom) < 1e-12:
                    s = b
                else:
                    alpha = ((mu - a) * (2 * b - a - c)) / denom
                    beta_p = alpha * (c - mu) / max(mu - a, 1e-9)
                    s = a + (c - a) * random.betavariate(max(alpha, 0.1), max(beta_p, 0.1))
            else:
                s = a
        else:
            raise ValueError(f"Unsupported distribution_type: '{distribution_type}'")

        samples.append(max(s, 0.0))  # losses are non-negative

    elapsed_ms = int((_time.monotonic_ns() - start_ns) / 1_000_000)
    samples.sort()
    n = len(samples)

    p5_idx  = int(n * 0.05)
    p25_idx = int(n * 0.25)
    p50_idx = int(n * 0.50)
    p75_idx = int(n * 0.75)
    p95_idx = int(n * 0.95)

    mean_val   = statistics.mean(samples)
    std_dev    = statistics.stdev(samples) if n > 1 else 0.0
    var_95     = samples[p95_idx]
    tail       = samples[p95_idx:]
    cvar_95    = statistics.mean(tail) if tail else var_95

    return {
        "iterations":  n,
        "mean":        round(mean_val, 4),
        "std_dev":     round(std_dev, 4),
        "p5":          round(samples[p5_idx], 4),
        "p25":         round(samples[p25_idx], 4),
        "p50":         round(samples[p50_idx], 4),
        "p75":         round(samples[p75_idx], 4),
        "p95":         round(samples[p95_idx], 4),
        "var_95":      round(var_95, 4),
        "cvar_95":     round(cvar_95, 4),
        "max_loss":    round(samples[-1], 4),
        "distribution": distribution_type,
        "execution_time_ms": elapsed_ms,
    }


# ===========================================================================
# Scenarios  (RM-SAP-GAP-02)
# ===========================================================================

@router.post("/scenarios", status_code=201)
def create_scenario(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Create a new multi-driver cascading risk scenario."""
    try:
        scenario_type = ScenarioType(body.get("scenario_type", "single_event"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scenario_type")

    velocity = None
    if body.get("velocity"):
        try:
            velocity = ScenarioVelocity(body["velocity"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid velocity")

    s = RiskScenario(
        tenant_id=tenant_id,
        scenario_id=body.get("scenario_id") or _new_id("SCN"),
        name=body["name"],
        description=body.get("description"),
        scenario_type=scenario_type,
        risk_ids=body.get("risk_ids", []),
        trigger_events=body.get("trigger_events", []),
        cascading_effects=body.get("cascading_effects", []),
        probability=body.get("probability"),
        impact_low=body.get("impact_low", 0.0),
        impact_mid=body.get("impact_mid", 0.0),
        impact_high=body.get("impact_high", 0.0),
        time_horizon=body.get("time_horizon"),
        velocity=velocity,
        status=ScenarioStatus.DRAFT,
        created_by=body.get("created_by"),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s.to_dict()


@router.get("/scenarios")
def list_scenarios(
    status: Optional[str] = Query(None),
    scenario_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(RiskScenario).filter(RiskScenario.tenant_id == tenant_id)
    if status:
        try:
            q = q.filter(RiskScenario.status == ScenarioStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    if scenario_type:
        try:
            q = q.filter(RiskScenario.scenario_type == ScenarioType(scenario_type))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid scenario_type")
    scenarios = q.order_by(RiskScenario.created_at.desc()).all()
    return {"total": len(scenarios), "scenarios": [s.to_dict() for s in scenarios]}


@router.get("/scenarios/{scenario_id}")
def get_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    return _scenario_or_404(db, scenario_id, tenant_id).to_dict()


@router.put("/scenarios/{scenario_id}")
def update_scenario(
    scenario_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    s = _scenario_or_404(db, scenario_id, tenant_id)
    scalar_fields = [
        "name", "description", "risk_ids", "trigger_events", "cascading_effects",
        "probability", "impact_low", "impact_mid", "impact_high", "time_horizon",
    ]
    for field in scalar_fields:
        if field in body:
            setattr(s, field, body[field])
    if "scenario_type" in body:
        s.scenario_type = ScenarioType(body["scenario_type"])
    if "velocity" in body and body["velocity"]:
        s.velocity = ScenarioVelocity(body["velocity"])
    if "status" in body:
        s.status = ScenarioStatus(body["status"])
    db.commit()
    db.refresh(s)
    return s.to_dict()


@router.post("/scenarios/{scenario_id}/simulate")
def simulate_scenario(
    scenario_id: str,
    body: Dict[str, Any] = Body(default={}),
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Run a Monte Carlo simulation for a risk scenario.

    Body fields:
      distribution_type : normal | triangular | uniform | lognormal | pert
      iterations        : int (default 10000, max 100000)
      input_parameters  : dict of distribution parameters
      executed_by       : str (optional)
    """
    s = _scenario_or_404(db, scenario_id, tenant_id)

    dist_str = body.get("distribution_type", "triangular")
    try:
        dist_enum = DistributionType(dist_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid distribution_type '{dist_str}'")

    raw_iterations = int(body.get("iterations", 10000))
    iterations = min(max(raw_iterations, 100), 100_000)
    input_params = body.get("input_parameters", {})

    # Provide sensible defaults from scenario impact range if params are sparse
    if not input_params:
        input_params = {
            "low":  s.impact_low,
            "mode": s.impact_mid,
            "high": s.impact_high,
            "mean": s.impact_mid or ((s.impact_low + s.impact_high) / 2),
            "std_dev": max((s.impact_high - s.impact_low) / 6, 1.0),
        }

    try:
        results = _run_monte_carlo(dist_str, input_params, iterations)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=f"Simulation failed: {exc}")

    # Persist simulation record
    sim = MonteCarloSimulation(
        tenant_id=tenant_id,
        simulation_id=_new_id("MCS"),
        scenario_id=s.id,
        distribution_type=dist_enum,
        iterations=iterations,
        input_parameters=input_params,
        results=results,
        executed_at=datetime.utcnow(),
        executed_by=body.get("executed_by"),
        execution_time_ms=results.get("execution_time_ms"),
    )
    db.add(sim)

    # Cache latest result on scenario
    s.simulation_results = results
    s.last_simulated_at = datetime.utcnow()

    db.commit()
    db.refresh(sim)
    return {
        "simulation_id": sim.simulation_id,
        "scenario_id": scenario_id,
        **results,
    }


@router.get("/scenarios/{scenario_id}/simulations")
def list_simulations(
    scenario_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    s = _scenario_or_404(db, scenario_id, tenant_id)
    sims = db.query(MonteCarloSimulation).filter(
        MonteCarloSimulation.scenario_id == s.id,
        MonteCarloSimulation.tenant_id == tenant_id,
    ).order_by(MonteCarloSimulation.executed_at.desc()).all()
    return {"total": len(sims), "simulations": [sim.to_dict() for sim in sims]}


# ===========================================================================
# Opportunities  (RM-SAP-GAP-04)
# ===========================================================================

@router.post("/opportunities", status_code=201)
def create_opportunity(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        category = OpportunityCategory(body.get("category", "strategic"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category")

    o = RiskOpportunity(
        tenant_id=tenant_id,
        opportunity_id=body.get("opportunity_id") or _new_id("OPP"),
        title=body["title"],
        description=body.get("description"),
        category=category,
        org_unit_id=body.get("org_unit_id"),
        owner_id=body.get("owner_id"),
        owner_name=body.get("owner_name"),
        probability=body.get("probability"),
        potential_upside=body.get("potential_upside"),
        investment_required=body.get("investment_required"),
        currency=body.get("currency", "USD"),
        time_horizon=body.get("time_horizon"),
        status=OpportunityStatus.IDENTIFIED,
        linked_risk_ids=body.get("linked_risk_ids", []),
        actions=body.get("actions", []),
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return o.to_dict()


@router.get("/opportunities")
def list_opportunities(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(RiskOpportunity).filter(RiskOpportunity.tenant_id == tenant_id)
    if category:
        try:
            q = q.filter(RiskOpportunity.category == OpportunityCategory(category))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category")
    if status:
        try:
            q = q.filter(RiskOpportunity.status == OpportunityStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    opps = q.order_by(RiskOpportunity.created_at.desc()).all()
    return {"total": len(opps), "opportunities": [o.to_dict() for o in opps]}


@router.put("/opportunities/{opportunity_id}")
def update_opportunity(
    opportunity_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    o = _opportunity_or_404(db, opportunity_id, tenant_id)
    scalar_fields = [
        "title", "description", "owner_id", "owner_name", "probability",
        "potential_upside", "investment_required", "currency",
        "time_horizon", "linked_risk_ids", "actions",
    ]
    for field in scalar_fields:
        if field in body:
            setattr(o, field, body[field])
    if "category" in body:
        o.category = OpportunityCategory(body["category"])
    if "status" in body:
        o.status = OpportunityStatus(body["status"])
    db.commit()
    db.refresh(o)
    return o.to_dict()


@router.put("/opportunities/{opportunity_id}/realize")
def realize_opportunity(
    opportunity_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """Mark an opportunity as realized with captured value."""
    o = _opportunity_or_404(db, opportunity_id, tenant_id)
    if "realized_value" not in body:
        raise HTTPException(status_code=400, detail="realized_value is required")
    o.realized_value = body["realized_value"]
    o.realized_at = datetime.utcnow()
    o.status = OpportunityStatus.REALIZED
    db.commit()
    db.refresh(o)
    return o.to_dict()


# ===========================================================================
# Business Objectives  (RM-SAP-GAP-01)
# ===========================================================================

@router.post("/objectives", status_code=201)
def create_objective(
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    try:
        category = ObjectiveCategory(body.get("category", "strategic"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category")

    obj = BusinessObjective(
        tenant_id=tenant_id,
        objective_id=body.get("objective_id") or _new_id("RSOBJ"),
        title=body["title"],
        description=body.get("description"),
        category=category,
        org_unit_id=body.get("org_unit_id"),
        owner_id=body.get("owner_id"),
        owner_name=body.get("owner_name"),
        target_date=datetime.fromisoformat(body["target_date"]) if body.get("target_date") else None,
        status=ObjectiveStatus.ACTIVE,
        linked_risk_ids=body.get("linked_risk_ids", []),
        is_active=True,
        metadata_=body.get("metadata"),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj.to_dict()


@router.get("/objectives")
def list_objectives(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    q = db.query(BusinessObjective).filter(
        BusinessObjective.tenant_id == tenant_id,
        BusinessObjective.is_active.is_(True),
    )
    if category:
        try:
            q = q.filter(BusinessObjective.category == ObjectiveCategory(category))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category")
    if status:
        try:
            q = q.filter(BusinessObjective.status == ObjectiveStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    objs = q.order_by(BusinessObjective.created_at.desc()).all()
    return {"total": len(objs), "objectives": [o.to_dict() for o in objs]}


@router.put("/objectives/{objective_id}")
def update_objective(
    objective_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    obj = _objective_or_404(db, objective_id, tenant_id)
    scalar_fields = ["title", "description", "owner_id", "owner_name", "metadata_"]
    for field in scalar_fields:
        if field in body:
            setattr(obj, field, body[field])
    if "category" in body:
        obj.category = ObjectiveCategory(body["category"])
    if "status" in body:
        obj.status = ObjectiveStatus(body["status"])
    if "target_date" in body and body["target_date"]:
        obj.target_date = datetime.fromisoformat(body["target_date"])
    db.commit()
    db.refresh(obj)
    return obj.to_dict()


@router.post("/objectives/{objective_id}/link-risks")
def link_risks_to_objective(
    objective_id: str,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(_get_tenant_id),
):
    """
    Link one or more risks to a business objective.

    Body: { "risk_ids": ["RISK_001", "RISK_002"], "replace": false }

    If replace=true the existing linked_risk_ids list is replaced entirely;
    otherwise the supplied IDs are merged (no duplicates).
    """
    obj = _objective_or_404(db, objective_id, tenant_id)
    new_ids: List[str] = body.get("risk_ids", [])
    if not new_ids:
        raise HTTPException(status_code=400, detail="risk_ids list is required")

    # Validate that each risk_id exists in the tenant
    validated: List[str] = []
    not_found: List[str] = []
    for rid in new_ids:
        exists = db.query(EnterpriseRisk).filter(
            EnterpriseRisk.risk_id == rid,
            EnterpriseRisk.tenant_id == tenant_id,
        ).first()
        if exists:
            validated.append(rid)
        else:
            not_found.append(rid)

    existing = list(obj.linked_risk_ids or [])
    if body.get("replace", False):
        obj.linked_risk_ids = validated
    else:
        merged = existing + [r for r in validated if r not in existing]
        obj.linked_risk_ids = merged

    db.commit()
    return {
        "objective_id": objective_id,
        "linked_risk_ids": obj.linked_risk_ids,
        "not_found": not_found,
    }
