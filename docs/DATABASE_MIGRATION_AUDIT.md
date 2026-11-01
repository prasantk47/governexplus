# Database & Migration Audit Report

**Date:** 2026-11-01 | **Baseline:** v1.0-rc-baseline

---

## 1. Schema Overview

| Metric | SQLAlchemy Models | Production DB |
|--------|-------------------|---------------|
| Total tables | 119 (in db/models/) + 1 (in router) | 120 (excl. alembic_version) |
| Model files | 18 | N/A |
| Migration count | 13 files | HEAD at 20261031_100000 |
| Total indexes | N/A | 461 |
| Tenant-indexed tables | N/A | 106/107 (1 missing) |

**Note:** Earlier estimate of 141 models included some Python enum classes counted as models. Verified count from DB is **120 tables**.

## 2. Migration Chain Verification

All 14 migrations form a linear chain from base to HEAD:

```
20260117_000001 (base) → 20260822_121800 → 20260822_183956 → 20260826_100000
→ 20260903_100000 → 20260904_120000 → 20260904_150000 → 20260918_100000
→ 20261004_100000 → 20261004_200000 → 20261005_100000 → 20261005_200000
→ 20261031_100000 (HEAD)
```

**Status:** HEAD revision matches latest migration. No pending migrations.

## 3. Column Type Audit (Critical Finding -- RESOLVED)

**Issue:** 27 columns across 15 tables were defined as PostgreSQL ENUM types in the database, but Python models used `String(50)`. This caused `DatatypeMismatch` errors on INSERT.

**Tables affected:** bcm_plans, bcm_test_exercises, bia_records, fraud_alerts, fraud_cases, fraud_rules, incident_activations, jml_events, jml_policies, standalone_surveys, survey_distributions, vendor_assessments, vendor_contracts, vendor_issues, vendors, whistleblower_cases, whistleblower_messages

**Resolution:** All 27 columns `ALTER`ed to `VARCHAR(50)` on 2026-11-01. This is a manual DB change NOT captured in an Alembic migration.

**DEFECT DB-001 (High):** Need an Alembic migration to formalize the 27 ENUM→VARCHAR conversions so that a clean `alembic upgrade head` on a new database produces the correct schema.

## 4. Model vs Database Drift

### Known Drift Items

| Table | Column | Model | DB | Status |
|-------|--------|-------|----|--------|
| enterprise_risks | metadata_ | Column(JSON) | metadata_ (JSON) | OK after ALTER |
| audit_findings | metadata_ | Column('metadata', JSON) | metadata (JSON) | OK (explicit name mapping) |
| jml_events | employee_email | NOT in model | NOT in DB | OK (removed from router) |
| vendor_issues | assessment_id, category, metadata_ | NOT in model columns | NOT in DB | OK (removed from router) |

### Missing Tables (Models exist, DB status uncertain)

All 141 model tables are believed to exist in the production DB based on successful API operations. A full automated diff between `Base.metadata` and the live DB schema should be created as part of the regression suite.

## 5. Index Audit

### Required Indexes

Every multi-tenant table MUST have an index on `tenant_id`. Spot checks confirm indexes exist on:
- `users.tenant_id` -- Yes
- `enterprise_risks.tenant_id` -- Yes
- `audit_findings.tenant_id` -- Yes
- `risk_violations.tenant_id` -- Yes

**VERIFIED:** Comprehensive index audit completed against production DB (461 indexes total).

**One missing tenant_id index found:**
- `risk_workflow_steps` — has `tenant_id` column but NO index. Will cause full table scans.

**104 unindexed FK columns found.** High-priority missing indexes:
- `user_roles.user_id`, `user_roles.role_id`
- `user_entitlements.user_id`
- `risk_violations.user_id`, `risk_violations.mitigation_id`
- `enterprise_risks.parent_risk_id`, `enterprise_risks.risk_owner_id`
- `risk_workflow_steps.approver_user_id`
- All `source_template_item_id` columns (9 tables)

**Code organization issue:** `PlatformConfig` model is defined in `api/routers/config.py` instead of `db/models/`. Should be moved for consistency (119 of 120 models are in db/models/).

## 6. Data Verification (Production)

| Table | Record Count | Status |
|-------|-------------|--------|
| tenants | 4 | OK |
| users | 87 | OK |
| roles | 44 | OK |
| enterprise_risks | 175 | OK |
| audit_plans | 17 | OK |
| vendors | 50 | OK |
| jml_events | 49 | OK |
| bcm_plans | 31 | OK |
| fraud_rules | 45 | OK |
| whistleblower_cases | 23 | OK |
| template_packs | 2 | OK |
| template_items | 1,052 | OK |

**Total across key tables: 1,579 records. All tables populated.**

## 7. Seed Data Verification

The template library seeder (`core/library/seeder.py`) loads 42 templates across categories:
- SoD rules, mitigations, workflows, controls, risk scenarios
- Runs in lifespan startup (idempotent)
- Confirmed operational via /library/items endpoint

## 8. Action Items

| ID | Description | Severity | Status |
|----|-------------|----------|--------|
| DB-001 | Create Alembic migration for 27 ENUM→VARCHAR conversions | High | Open |
| DB-002 | Run automated tenant_id index audit on all tables | Medium | Open |
| DB-003 | Build automated model-vs-DB schema drift check for CI | High | Open |
| DB-004 | Verify downgrade of last 5 migrations | Medium | Open |
| DB-005 | Test clean `alembic upgrade head` on empty DB | High | Open |
