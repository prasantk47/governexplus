"""
GAP-3: Risk-Control Matrix (RCM) Router
Joins risks → control objectives → controls into a matrix view.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db

router = APIRouter()


@router.get("/matrix")
def get_rcm_matrix(db: Session = Depends(get_db)):
    """Build the Risk-Control Matrix by joining risks, objectives, and controls."""
    from db.models.risk_management import EnterpriseRisk
    from db.models.process_control import ProcessControl, ControlObjective

    risks = db.query(EnterpriseRisk).limit(500).all()
    controls = db.query(ProcessControl).limit(500).all()
    objectives = db.query(ControlObjective).limit(500).all()

    obj_map = {}
    for o in objectives:
        d = {c.name: getattr(o, c.name, None) for c in o.__table__.columns}
        d["linked_controls"] = []
        d["linked_risks"] = []
        obj_map[d.get("id")] = d

    ctrl_list = []
    for c in controls:
        d = {col.name: getattr(c, col.name, None) for col in c.__table__.columns}
        ctrl_list.append(d)
        linked_obj_ids = d.get("linked_objective_ids") or d.get("control_objective_id") or []
        if isinstance(linked_obj_ids, str):
            linked_obj_ids = [linked_obj_ids]
        for oid in (linked_obj_ids if isinstance(linked_obj_ids, list) else []):
            if oid in obj_map:
                obj_map[oid]["linked_controls"].append({"id": d.get("id"), "name": d.get("control_name") or d.get("name")})

    risk_list = []
    for r in risks:
        d = {col.name: getattr(r, col.name, None) for col in r.__table__.columns}
        risk_list.append(d)

    matrix_rows = []
    for r in risk_list:
        row = {
            "risk_id": r.get("id"),
            "risk_title": r.get("title"),
            "risk_category": r.get("category"),
            "risk_score": r.get("inherent_score") or r.get("risk_score"),
            "objectives": [],
            "controls": [],
            "coverage": "none",
        }
        linked_ctrl_ids = r.get("linked_control_ids") or []
        if isinstance(linked_ctrl_ids, list):
            for cid in linked_ctrl_ids:
                match = next((c for c in ctrl_list if c.get("id") == cid), None)
                if match:
                    row["controls"].append({"id": cid, "name": match.get("control_name") or match.get("name")})
        row["coverage"] = "full" if len(row["controls"]) >= 2 else ("partial" if row["controls"] else "none")
        matrix_rows.append(row)

    return {
        "matrix": matrix_rows,
        "summary": {
            "total_risks": len(risk_list),
            "total_controls": len(ctrl_list),
            "total_objectives": len(objectives),
            "risks_with_controls": sum(1 for r in matrix_rows if r["controls"]),
            "risks_without_controls": sum(1 for r in matrix_rows if not r["controls"]),
            "coverage_pct": round(sum(1 for r in matrix_rows if r["controls"]) / max(len(matrix_rows), 1) * 100, 1),
        },
    }


@router.get("/coverage-gaps")
def rcm_coverage_gaps(db: Session = Depends(get_db)):
    """Identify risks with no linked controls."""
    from db.models.risk_management import EnterpriseRisk
    risks = db.query(EnterpriseRisk).limit(500).all()
    gaps = []
    for r in risks:
        d = {c.name: getattr(r, c.name, None) for c in r.__table__.columns}
        linked = d.get("linked_control_ids") or []
        if not linked:
            gaps.append({
                "risk_id": d.get("id"),
                "risk_title": d.get("title"),
                "risk_category": d.get("category"),
                "risk_score": d.get("inherent_score") or d.get("risk_score"),
            })
    return {"gaps": gaps, "count": len(gaps)}


@router.get("/control-effectiveness")
def control_effectiveness(db: Session = Depends(get_db)):
    """Show control coverage and effectiveness summary."""
    from db.models.process_control import ProcessControl
    controls = db.query(ProcessControl).limit(500).all()
    total = len(controls)
    effective = sum(1 for c in controls if getattr(c, "effectiveness", None) == "effective")
    return {
        "total_controls": total,
        "effective": effective,
        "ineffective": total - effective,
        "effectiveness_rate": round(effective / max(total, 1) * 100, 1),
    }
