"""
ANAO Security Controls Seeder
==============================
Loads 1,003 controls extracted from the ANAO 'Security and Control for SAP R/3'
handbook into the GovernexPlus Template Library as a dedicated pack.

Idempotent: skips items whose item_code already exists.
Run during app startup (lifespan) or manually via /library/seed endpoint.
"""

import json
import hashlib
import logging
import os
import uuid as uuid_mod
from datetime import datetime
from sqlalchemy.orm import Session
from db.models.template_library import TemplatePack, TemplatePackVersion, TemplateItem

logger = logging.getLogger(__name__)

CONTROLS_JSON = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "anao_controls.json")
PROCESSES_JSON = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "anao_processes.json")

ANAO_PACK = {
    "pack_code": "ANAO_SAP_SECURITY_V1",
    "name": "ANAO SAP Security & Control Handbook",
    "description": (
        "1,003 security controls extracted from the Australian National Audit Office "
        "'Security and Control for SAP R/3' handbook. Covers MM, FI, FI-AA, CO, HR, "
        "Basis (security, change control, interfaces, data conversion). "
        "Each control includes priority (critical/important/desirable), control type "
        "(preventive/detective/corrective), risk domain, and framework mappings "
        "(COBIT, SOX, ISO27001, NIST CSF)."
    ),
    "module": "all",
    "tags": ["anao", "sap", "security", "controls", "audit", "sox", "iso27001", "best-practice"],
    "status": "published",
    "author": "Australian National Audit Office (ANAO)",
    "version": "1.0.0",
}


def _checksum(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _map_module(mod_id: str) -> str:
    """Map ANAO module codes to GovernexPlus module names."""
    mapping = {
        "MM": "process_control",
        "FI": "process_control",
        "FI-AA": "process_control",
        "CO": "process_control",
        "HR": "process_control",
        "BC": "security_controls",
        "BC-SEC": "security_controls",
        "BC-CHG": "security_controls",
        "BC-INT": "security_controls",
        "BC-CNV": "security_controls",
    }
    return mapping.get(mod_id, "security_controls")


def _map_item_type(risk_domain: str) -> str:
    """Map risk domain to GovernexPlus item type."""
    if risk_domain == "segregation_of_duties":
        return "sod_rule"
    elif risk_domain in ("access_control", "authentication"):
        return "security_control"
    elif risk_domain == "change_management":
        return "change_control"
    elif risk_domain == "monitoring_logging":
        return "monitoring_control"
    elif risk_domain == "reconciliation":
        return "reconciliation_control"
    elif risk_domain == "interface_controls":
        return "interface_control"
    elif risk_domain == "business_continuity":
        return "bcm_control"
    elif risk_domain == "master_data_governance":
        return "master_data_control"
    elif risk_domain == "payroll_hr":
        return "hr_control"
    return "security_control"


def seed_anao_controls(db: Session) -> dict:
    """
    Seed ANAO controls into the template library.
    Idempotent — skips existing item_codes.
    """
    if not os.path.exists(CONTROLS_JSON):
        logger.warning("ANAO controls JSON not found: %s", CONTROLS_JSON)
        return {"inserted": 0, "skipped": 0, "error": "controls file not found"}

    with open(CONTROLS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    controls = data.get("controls", [])
    if not controls:
        return {"inserted": 0, "skipped": 0, "error": "no controls in file"}

    # Ensure pack exists
    pack = db.query(TemplatePack).filter_by(pack_code=ANAO_PACK["pack_code"]).first()
    if not pack:
        pack = TemplatePack(
            id=str(uuid_mod.uuid4()),
            **{k: v for k, v in ANAO_PACK.items() if k != "version"},
        )
        db.add(pack)
        db.flush()
        logger.info("Created ANAO template pack: %s", pack.id)

        ver = TemplatePackVersion(
            id=str(uuid_mod.uuid4()),
            pack_id=pack.id,
            version=ANAO_PACK["version"],
            changelog="Initial import — 1,003 controls from ANAO SAP R/3 handbook",
            published_at=datetime.utcnow(),
            item_count=len(controls),
            is_latest=True,
        )
        db.add(ver)
    else:
        logger.info("ANAO pack already exists: %s", pack.id)

    # Check existing codes
    existing_codes = {code for (code,) in db.query(TemplateItem.item_code).all()}

    inserted = 0
    skipped = 0

    for ctrl in controls:
        item_code = ctrl["id"]
        if item_code in existing_codes:
            skipped += 1
            continue

        payload = {
            "source_module": ctrl["module"],
            "source_module_name": ctrl["module_name"],
            "section": ctrl.get("section", ""),
            "source_page": ctrl.get("page", 0),
            "control_type": ctrl["control_type"],
            "control_nature": ctrl["control_nature"],
            "risk_domain": ctrl["risk_domain"],
            "sap_tcodes": ctrl.get("sap_tcodes", []),
            "sap_auth_objects": ctrl.get("sap_auth_objects", []),
            "sap_tables": ctrl.get("sap_tables", []),
            "framework_mappings": ctrl.get("framework_mappings", []),
        }

        # Extract framework names for the compliance_frameworks field
        frameworks = list({m["framework"] for m in ctrl.get("framework_mappings", [])})

        severity = ctrl.get("priority", "important")
        if severity == "desirable":
            severity = "low"
        elif severity == "important":
            severity = "medium"
        elif severity == "critical":
            severity = "critical"

        # Truncate description if too long
        desc = ctrl["description"]
        name = desc[:120] + "..." if len(desc) > 120 else desc

        item = TemplateItem(
            id=str(uuid_mod.uuid4()),
            item_code=item_code,
            name=name,
            description=desc,
            module=_map_module(ctrl["module"]),
            item_type=_map_item_type(ctrl["risk_domain"]),
            compliance_frameworks=frameworks,
            industry_tags=["government", "all"],
            payload=payload,
            checksum=_checksum(payload),
            version="1.0.0",
            status="published",
            pack_id=pack.id,
            pack_version="1.0.0",
            severity=severity,
        )
        db.add(item)
        inserted += 1

        # Batch commits every 200
        if inserted % 200 == 0:
            db.flush()
            logger.info("Flushed %d ANAO controls", inserted)

    # ── Seed process flows ──────────────────────────────────────
    proc_inserted = 0
    if os.path.exists(PROCESSES_JSON):
        with open(PROCESSES_JSON, "r", encoding="utf-8") as f:
            proc_data = json.load(f)

        for proc in proc_data.get("processes", []):
            item_code = proc["id"]
            if item_code in existing_codes:
                skipped += 1
                continue

            payload = {
                "module": proc["module"],
                "module_name": proc["module_name"],
                "steps": proc["steps"],
                "sod_risks": proc.get("sod_risks", []),
                "key_reports": proc.get("key_reports", []),
                "config_hotspots": proc.get("config_hotspots", []),
            }

            item = TemplateItem(
                id=str(uuid_mod.uuid4()),
                item_code=item_code,
                name=proc["name"],
                description=proc["description"],
                module="process_control",
                item_type="process_flow",
                compliance_frameworks=["SOX", "COBIT"],
                industry_tags=["government", "all"],
                payload=payload,
                checksum=_checksum(payload),
                version="1.0.0",
                status="published",
                pack_id=pack.id,
                pack_version="1.0.0",
                severity="high",
            )
            db.add(item)
            proc_inserted += 1
            inserted += 1

        logger.info("ANAO process flows seeded: %d", proc_inserted)

    db.commit()
    total = len(controls) + proc_inserted
    logger.info("ANAO seeder complete: %d inserted, %d skipped (total: %d)", inserted, skipped, total)
    return {"inserted": inserted, "skipped": skipped, "total": total, "controls": len(controls), "processes": proc_inserted}
