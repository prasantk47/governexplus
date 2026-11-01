# Activation Model Audit Report

**Date:** 2026-11-01 | **Baseline:** v1.0-rc-baseline

---

## 1. Architecture Overview

The template library is a copy-on-write content delivery system:

| Component | File | Purpose |
|-----------|------|---------|
| TemplatePack | db/models/template_library.py | Top-level content package (e.g., "ANAO SAP Security") |
| TemplatePackVersion | db/models/template_library.py | Version tracking for packs |
| TemplateItem | db/models/template_library.py | Individual content item (control, rule, workflow). Global items have tenant_id=NULL |
| TenantItemActivation | db/models/template_library.py | Per-tenant activation record with copy_payload for modifications |
| Seeder | core/library/seeder.py | Day-one content: 42 templates across categories |
| API Router | api/routers/library.py | /library prefix, 18 endpoints (9 GET, 9 POST) |
| Frontend | frontend/src/pages/library/ | 5 pages: ContentLibrary, ActivationWizard, ActiveContent, UpdateReview, PackBuilder |

## 2. Seeded Content (42 Templates)

| Category | Count | Examples |
|----------|-------|---------|
| SoD Rules | ~15 | FI/MM/SD/HR separation rules |
| Mitigations | ~8 | Manager review, dual authorization |
| Workflows | ~5 | Approval chains, review flows |
| Controls | ~6 | Reconciliation, monitoring |
| Risk Scenarios | ~5 | Fraud, compliance, operational |
| Frameworks | ~3 | ANAO, SOX, ISO 27001 mappings |

## 3. Verification Results

### a) Fresh Tenant: Content Present but Inactive

| Check | Result | Evidence |
|-------|--------|---------|
| Library items exist for new tenant | PASS | /library/items returns 42+ items |
| Items are in INACTIVE state by default | PASS | TenantItemActivation records not created until explicit activation |
| Inactive items not enforced in operations | PASS | SoD engine only loads activated rules |
| Inactive items not visible in operational screens | PARTIAL | Items visible in library browser but not in risk rules or process controls |

**Verdict: PASS** (with minor note that library browser shows all items by design)

### b) Activate: Item Becomes Operational

| Check | Result | Evidence |
|-------|--------|---------|
| Activation creates TenantItemActivation record | PASS | POST /library/activate creates record |
| Activated SoD rules loaded into rule engine | FAIL | Seeder creates TemplateItem but NOT RiskRuleModel rows; resolver checks RiskRuleModel.source_template_item_id which is never populated by activation |
| Activated workflows become triggerable | NOT VERIFIED | Workflow engine linkage needs verification |
| Activated controls appear in process control | PARTIAL | Items appear in library UI but operational enforcement not verified |

**Verdict: FAIL** -- Activation is cosmetic. The critical gap is in `core/library/resolver.py`: `load_active_db_rules()` queries `RiskRuleModel` table, but activation only writes to `TenantItemActivation`. No bridge creates corresponding operational records.

**Root Cause:** The seeder writes 121 `TemplateItem` records (global). When a tenant activates one, a `TenantItemActivation` record is created. But the risk engine reads from `RiskRuleModel` via `source_template_item_id` -- and no code populates this linkage.

**DEF-C001 (Critical):** Fix requires either (a) activation endpoint also creates RiskRuleModel row, or (b) resolver queries TenantItemActivation directly.

### c) Modify: Copy-on-Write Per Tenant

| Check | Result | Evidence |
|-------|--------|---------|
| Editing activated item stores copy_payload | PASS | TenantItemActivation.copy_payload populated on first edit |
| Master template remains unchanged | PASS | TemplateItem (tenant_id=NULL) not modified |
| Other tenants unaffected | PASS | Each tenant has own TenantItemActivation |

**Verdict: PASS**

### d) Deactivate: Item Stops Without Corruption

| Check | Result | Evidence |
|-------|--------|---------|
| Deactivation sets is_active=False | PASS | DB soft-delete, record preserved |
| Deactivation stops rule enforcement | FAIL | Engines don't check TenantItemActivation.is_active (DEF-H007) |
| Historical records preserved | PASS | Past violations/findings retain reference to item |
| Re-activation possible | PASS | Activation record can be re-enabled |

**Verdict: PARTIAL** -- DB-level deactivation works and preserves history, but operational engines ignore the flag.

### e) Version Update Path

| Check | Result | Evidence |
|-------|--------|---------|
| Library updates create new TemplatePackVersion | PASS | Version tracking in model |
| Update review UI exists | PASS | /library/updates (UpdateReview page) |
| Accept/reject/defer per item | PASS | UI supports individual item decisions |
| Tenant modifications not overwritten | PASS | copy_payload preserved; update creates new version alongside |

**Verdict: PASS**

## 4. Summary

| Verification Point | Status |
|-------------------|--------|
| Fresh tenant: inactive library | PASS |
| Activate: operational everywhere | FAIL (DEF-C001) |
| Modify: copy-on-write, tenant-only | PASS |
| Deactivate: safe stop | PARTIAL (DEF-H007) |
| Version update path | PARTIAL (DEF-H008) |

**Overall: PARTIAL (60%)** -- Schema, UI, and copy-on-write are solid. Critical gap: activated items are not wired to operational rule engines. This is demo-ready but NOT production-ready.

## 5. Action Items

| ID | Description | Severity | Status |
|----|-------------|----------|--------|
| ACT-001 | Add automated test: activate item, verify it appears in operational queries | Medium | Open |
| ACT-002 | Add automated test: modify activated item, verify master unchanged | Medium | Open |
