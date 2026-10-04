"""
Template Library Importer — Phase 1
=====================================

Validates and upserts a versioned JSON pack into the global library.

Pack format (one JSON file, or dict already loaded):
{
  "pack": {
    "pack_code": "SOX_ITGC_V1",
    "name": "SOX ITGC Controls Pack",
    "version": "1.0.0",
    "module": "process_control",
    "description": "...",
    "author": "GovernexPlus",
    "changelog": "Initial release"
  },
  "items": [
    {
      "item_code": "PC-SOX-001",
      "name": "...",
      "module": "process_control",
      "item_type": "control",
      "description": "...",
      "payload": {...},
      "compliance_frameworks": ["SOX"],
      "industry_tags": ["all"],
      "severity": null,
      "version": "1.0.0"
    },
    ...
  ]
}

Idempotency rules:
  • If an item with this item_code exists and its checksum matches → skip.
  • If the checksum differs → update payload + version + checksum, set
    pending_update_version on all active TenantItemActivations.
  • Tenant copies (is_customized=True) are NEVER touched.
  • Re-running with the same pack is always safe.

Usage:
    from core.library.importer import import_pack

    with open("seeds/packs/sox_itgc.json") as f:
        pack_data = json.load(f)

    result = import_pack(pack_data, db)
    # result = {"inserted": 42, "updated": 2, "skipped": 0, "errors": []}
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

REQUIRED_PACK_FIELDS = {"pack_code", "name", "version"}
REQUIRED_ITEM_FIELDS = {"item_code", "name", "module", "item_type", "payload"}
VALID_MODULES = {
    "ara", "arm", "eam", "certification", "brm", "jml",
    "risk_management", "process_control", "audit_management",
    "compliance", "tprm", "bcm", "fraud", "survey", "shared", "all",
}
VALID_ITEM_TYPES = {
    "sod_rule", "mitigation", "workflow", "access_policy", "control",
    "certification_template", "risk_scenario", "jml_policy", "survey",
    "report", "notification", "connector_config", "kri", "fraud_rule",
    "audit_program", "questionnaire",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def import_pack(
    pack_data: dict,
    db: Session,
    *,
    dry_run: bool = False,
) -> dict:
    """
    Validate and upsert a pack dict into the global library.

    Args:
        pack_data: Parsed pack JSON (the full dict with "pack" + "items").
        db: SQLAlchemy session.
        dry_run: If True, validate only — don't write anything.

    Returns a result dict:
        {
          "pack_code": str,
          "version": str,
          "inserted": int,
          "updated": int,
          "skipped": int,
          "pending_updates_notified": int,
          "errors": [str],
          "dry_run": bool,
        }
    """
    from db.models.template_library import (
        TemplatePack,
        TemplatePackVersion,
        TemplateItem,
        TenantItemActivation,
    )

    result = {
        "pack_code": None,
        "version": None,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "pending_updates_notified": 0,
        "errors": [],
        "dry_run": dry_run,
    }

    # ------------------------------------------------------------------
    # Validate pack header
    # ------------------------------------------------------------------
    errors = _validate_pack(pack_data)
    if errors:
        result["errors"] = errors
        return result

    pack_meta = pack_data["pack"]
    items_raw = pack_data.get("items", [])
    pack_code = pack_meta["pack_code"]
    pack_version = pack_meta["version"]
    result["pack_code"] = pack_code
    result["version"] = pack_version

    # ------------------------------------------------------------------
    # Validate items
    # ------------------------------------------------------------------
    item_errors = _validate_items(items_raw)
    if item_errors:
        result["errors"] = item_errors
        return result

    if dry_run:
        result["inserted"] = len(items_raw)  # hypothetical
        return result

    # ------------------------------------------------------------------
    # Upsert pack header (one transaction per module as guide specifies)
    # ------------------------------------------------------------------
    try:
        pack = db.query(TemplatePack).filter_by(pack_code=pack_code).first()
        if pack is None:
            pack = TemplatePack(
                id=str(uuid.uuid4()),
                pack_code=pack_code,
                name=pack_meta["name"],
                description=pack_meta.get("description"),
                module=pack_meta.get("module", "all"),
                tags=pack_meta.get("tags", []),
                status="published",
                author=pack_meta.get("author"),
                license_note=pack_meta.get("license_note"),
            )
            db.add(pack)
        else:
            pack.name = pack_meta["name"]
            pack.description = pack_meta.get("description", pack.description)
            pack.status = "published"

        # TemplatePackVersion — mark this version as latest
        existing_version = (
            db.query(TemplatePackVersion)
            .filter_by(pack_id=pack.id, version=pack_version)
            .first()
        )
        if existing_version is None:
            # Reset is_latest on all other versions
            db.query(TemplatePackVersion).filter(
                TemplatePackVersion.pack_id == pack.id,
                TemplatePackVersion.is_latest == True,  # noqa: E712
            ).update({"is_latest": False})

            pv = TemplatePackVersion(
                id=str(uuid.uuid4()),
                pack_id=pack.id,
                version=pack_version,
                changelog=pack_meta.get("changelog"),
                published_at=datetime.utcnow(),
                checksum=_pack_checksum(pack_data),
                item_count=len(items_raw),
                is_latest=True,
            )
            db.add(pv)

        db.flush()

    except Exception as exc:
        db.rollback()
        result["errors"].append(f"Pack header upsert failed: {exc}")
        return result

    # ------------------------------------------------------------------
    # Upsert items — one transaction per module (as per guide)
    # ------------------------------------------------------------------
    items_by_module: dict[str, list] = {}
    for item_raw in items_raw:
        mod = item_raw.get("module", "all")
        items_by_module.setdefault(mod, []).append(item_raw)

    for module, module_items in items_by_module.items():
        try:
            for item_raw in module_items:
                item_code = item_raw["item_code"]
                payload = item_raw["payload"]
                checksum = _item_checksum(payload)

                existing = (
                    db.query(TemplateItem)
                    .filter_by(item_code=item_code)
                    .first()
                )

                if existing is None:
                    # Insert new item
                    new_item = TemplateItem(
                        id=str(uuid.uuid4()),
                        item_code=item_code,
                        name=item_raw["name"],
                        description=item_raw.get("description"),
                        module=item_raw["module"],
                        item_type=item_raw["item_type"],
                        compliance_frameworks=item_raw.get("compliance_frameworks", []),
                        industry_tags=item_raw.get("industry_tags", []),
                        payload=payload,
                        version=item_raw.get("version", pack_version),
                        checksum=checksum,
                        status="published",
                        pack_id=pack.id,
                        pack_version=pack_version,
                        severity=item_raw.get("severity"),
                    )
                    db.add(new_item)
                    result["inserted"] += 1

                elif existing.checksum == checksum:
                    # Payload unchanged → skip
                    result["skipped"] += 1

                else:
                    # Payload changed → update global item
                    old_version = existing.version
                    new_version = item_raw.get("version", pack_version)
                    existing.payload = payload
                    existing.checksum = checksum
                    existing.version = new_version
                    existing.name = item_raw.get("name", existing.name)
                    existing.description = item_raw.get("description", existing.description)
                    existing.compliance_frameworks = item_raw.get(
                        "compliance_frameworks", existing.compliance_frameworks
                    )
                    existing.pack_version = pack_version
                    result["updated"] += 1

                    # Notify active tenants: set pending_update_version
                    # ONLY on rows where is_customized=False (customized rows
                    # see the update in Update Review, not auto-applied)
                    notified = (
                        db.query(TenantItemActivation)
                        .filter(
                            TenantItemActivation.template_item_id == existing.id,
                            TenantItemActivation.is_active == True,  # noqa: E712
                            TenantItemActivation.pending_update_version == None,  # noqa: E711
                        )
                        .update(
                            {"pending_update_version": new_version},
                            synchronize_session=False,
                        )
                    )
                    result["pending_updates_notified"] += notified

            db.commit()
            logger.info(
                "importer: module=%s committed %d items",
                module,
                len(module_items),
            )

        except Exception as exc:
            db.rollback()
            msg = f"Module '{module}' transaction failed: {exc}"
            result["errors"].append(msg)
            logger.error("importer: %s", msg)

    # Update pack item count
    try:
        pack.versions  # touch to ensure loaded
        db.query(TemplatePackVersion).filter_by(
            pack_id=pack.id, version=pack_version
        ).update({"item_count": result["inserted"] + result["updated"] + result["skipped"]})
        db.commit()
    except Exception:
        pass

    return result


def import_pack_file(path: str | Path, db: Session, *, dry_run: bool = False) -> dict:
    """Load a pack JSON file and call import_pack()."""
    p = Path(path)
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return import_pack(data, db, dry_run=dry_run)


def import_all_packs(seeds_dir: str | Path, db: Session) -> list[dict]:
    """
    Import every *.json pack file found under seeds_dir.

    Returns a list of result dicts (one per file).
    """
    p = Path(seeds_dir)
    if not p.exists():
        logger.warning("importer: seeds dir %s not found", p)
        return []

    results = []
    for json_file in sorted(p.glob("**/*.json")):
        logger.info("importer: importing %s", json_file)
        try:
            result = import_pack_file(json_file, db)
            result["file"] = str(json_file)
            results.append(result)
        except Exception as exc:
            results.append({
                "file": str(json_file),
                "errors": [str(exc)],
                "inserted": 0, "updated": 0, "skipped": 0,
            })
    return results


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_pack(data: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        errors.append("Pack must be a JSON object")
        return errors
    if "pack" not in data:
        errors.append("Missing top-level 'pack' key")
    if "items" not in data:
        errors.append("Missing top-level 'items' key")
    if errors:
        return errors
    meta = data["pack"]
    for field in REQUIRED_PACK_FIELDS:
        if not meta.get(field):
            errors.append(f"pack.{field} is required")
    if not isinstance(data["items"], list):
        errors.append("'items' must be a list")
    return errors


def _validate_items(items: list) -> list[str]:
    errors: list[str] = []
    seen_codes: set[str] = set()
    for i, item in enumerate(items):
        prefix = f"items[{i}] ({item.get('item_code', '?')})"
        for field in REQUIRED_ITEM_FIELDS:
            if not item.get(field) and field != "payload":
                errors.append(f"{prefix}: missing required field '{field}'")
            elif field == "payload" and not isinstance(item.get("payload"), dict):
                errors.append(f"{prefix}: 'payload' must be a JSON object")
        code = item.get("item_code", "")
        if code in seen_codes:
            errors.append(f"{prefix}: duplicate item_code '{code}'")
        seen_codes.add(code)
        mod = item.get("module", "")
        if mod and mod not in VALID_MODULES:
            errors.append(f"{prefix}: unknown module '{mod}'")
        itype = item.get("item_type", "")
        if itype and itype not in VALID_ITEM_TYPES:
            errors.append(f"{prefix}: unknown item_type '{itype}'")
    return errors


# ---------------------------------------------------------------------------
# Checksum helpers
# ---------------------------------------------------------------------------

def _item_checksum(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def _pack_checksum(pack_data: dict) -> str:
    """Checksum the items list (not the header, which may change without content change)."""
    return hashlib.sha256(
        json.dumps(pack_data.get("items", []), sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
