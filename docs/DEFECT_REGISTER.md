# Defect Register

**Date:** 2026-11-01 | **Baseline:** v1.0-rc-baseline

---

## Severity Definitions

- **Critical:** Tenant isolation leak, auth bypass, SoD false-negative, audit trail gap
- **High:** Data corruption, blocking workflow, security vulnerability
- **Medium:** Feature malfunction, incorrect data display, missing validation
- **Low:** Cosmetic, non-blocking UX issue, documentation gap

---

## Active Defects

### Critical (1)

| ID | Module | Description | Root Cause | Files Affected | Regression Test | Status |
|----|--------|-------------|------------|----------------|----------------|--------|
| DEF-C001 | Template Library | Activated template items NOT loaded into operational rule engines — activation is cosmetic only | Seeder creates TemplateItem records but NOT corresponding RiskRuleModel rows; resolver checks RiskRuleModel.source_template_item_id which is never populated | core/library/seeder.py, core/library/resolver.py, api/routers/risk_analysis.py | Activate SoD rule → verify it flags a violation | Open |
| DEF-C002 | Security/Audit | AuditLog model has NO tenant_id column — cross-tenant audit data exposure. Any user from any tenant can see ALL tenants' audit entries via GET /audit/logs | ORM tenant scoping only filters models with tenant_id; AuditLog doesn't have one | db/models/audit.py, audit/logger.py | Login as tenant A, GET /audit/logs, verify no tenant B entries | Open |
| DEF-C003 | Security/Auth | Token blacklist bypass — revoked tokens still accepted after logout | Logout endpoint passes "Bearer <token>" to blacklist but verify checks raw token (no prefix match) | api/routers/auth.py line 246 | Logout → reuse token → expect 401, currently gets 200 | Open |

### High (4)

| ID | Module | Description | Root Cause | Files Affected | Regression Test | Status |
|----|--------|-------------|------------|----------------|----------------|--------|
| DEF-H001 | Database | 27 ENUM columns altered to VARCHAR but no Alembic migration exists | Manual ALTER TABLE applied directly to prod DB | alembic/versions/ (missing migration) | Clean upgrade test | Open |
| DEF-H002 | All Routers | Enum constructor calls (`SomeEnum(value)`) store `"SomeEnum.VALUE"` in VARCHAR columns instead of `"value"` | Python `str()` on enum objects includes class name | api/routers/bcm.py, tprm.py, fraud.py, whistleblower.py (FIXED); Other routers may be affected | Insert + read-back test | Partially Fixed |
| DEF-H003 | Database | Automated model-vs-DB schema drift check does not exist | No CI tooling | tests/ | Schema drift test | Open |
| DEF-H004 | Tests | All existing pytest tests fail (16/23 fail in test_auth_service.py) | AuditAction enum not compatible with SQLite test DB; same enum-to-string issue | tests/conftest.py, audit/logger.py | Test suite must pass | Open |
| DEF-H005 | Access Requests | Missing reject endpoint: POST /access-requests/{id}/reject/{stepId} | Frontend calls it but backend route doesn't exist | api/routers/access_requests.py | Approval workflow test | Open |
| DEF-H006 | Frontend/Backend | 4 field name mismatches: first_name/last_name vs full_name, manager_id vs manager_user_id, risk_score vs severity_score, name vs role_name | Frontend API client uses different field names than backend Pydantic models | frontend/src/services/api.ts, provisioningApi.ts | Field mapping test | Open |
| DEF-H007 | Template Library | Deactivating a template item does not stop it from running in engines | Engines don't check TenantItemActivation.is_active; they check RiskRuleModel.source_template_item_id only | core/library/resolver.py | Deactivate rule → verify it stops flagging | Open |
| DEF-H008 | Template Library | Update acceptance overwrites tenant customizations | accept decision sets copy_payload = global payload, losing customized content | api/routers/library.py (review-update endpoint) | Customize → accept update → verify custom preserved | Open |

### Medium (8)

| ID | Module | Description | Root Cause | Files Affected | Status |
|----|--------|-------------|------------|----------------|--------|
| DEF-M001 | Settings | GET /settings/smtp returns 500 | Unhandled None when no SMTP config exists | api/routers/smtp_config.py | Open |
| DEF-M002 | Security | Audit log table has no immutability protection | No DB trigger/policy preventing DELETE | db/models/audit.py | Open |
| DEF-M003 | Security | Object-level auth (self-approval prevention) not verified | Missing multi-user integration tests | tests/ | Open |
| DEF-M004 | Router/Model | JML router used wrong column names for JmlEvent model | Router referenced source_system, previous_org_unit etc; model has hr_system, old_org_unit | api/routers/jml.py | Fixed |
| DEF-M005 | Router/Model | TPRM create_issue used wrong column names for VendorIssue | Router used title, owner_id; model has issue_title, owner | api/routers/tprm.py | Fixed |
| DEF-M006 | Router/Model | BCM activate_plan used wrong column names for IncidentActivation | Router used timeline, notification_list; model has timeline_events, communications_log | api/routers/bcm.py | Fixed |
| DEF-M007 | Database | tenant_id index audit not performed on extended module tables | Indexes may be missing on newer tables | db/models/extended_modules.py | Open |
| DEF-M008 | Connector | Credential storage is config-based, not encrypted at rest | connectors/ pass credentials in plain config | connectors/ | Open |

### Low (3)

| ID | Module | Description | Root Cause | Status |
|----|--------|-------------|------------|--------|
| DEF-L001 | API | 19 endpoint paths return 404 when tested with bare prefix | Frontend uses more specific paths; not a bug but confusing | Informational |
| DEF-L002 | API | KRI list and TPRM issues list are POST-only | Design choice, may confuse API consumers | Informational |
| DEF-L003 | Connector | Workday connector is a stub | Not implemented | Open |

---

## Fixed Defects (This Stabilization Cycle)

| ID | Description | Fix Date | Fix Commit |
|----|-------------|----------|------------|
| DEF-F001 | Tenant not found: JWT carried slug but TenantManager looked up by UUID | 2026-11-01 | 8c7a420 |
| DEF-F002 | 94 SQLEnum(X) columns caused LookupError with VARCHAR DB columns | 2026-11-01 | f013540 |
| DEF-F003 | 88 to_dict() methods called .value on plain strings | 2026-11-01 | f013540 |
| DEF-F004 | Workflow step approval: enum comparisons failed against string DB values | 2026-11-01 | 1345d71 |
| DEF-F005 | Missing DB columns: source_template_item_id, template_version, is_customized on 9 tables | 2026-11-01 | f013540 |
| DEF-F006 | Missing DB columns: metadata_ on 7 risk tables | 2026-11-01 | f013540 |
| DEF-F007 | 27 PG ENUM columns converted to VARCHAR(50) | 2026-11-01 | ebe9f11 |
| DEF-F008 | JML router column mismatch (source_system→hr_system etc) | 2026-11-01 | ebe9f11 |
| DEF-F009 | TPRM create_issue column mismatch (title→issue_title etc) | 2026-11-01 | ebe9f11 |
| DEF-F010 | BCM activate_plan column mismatch + enum bypass | 2026-11-01 | ebe9f11 |
| DEF-F011 | Fraud/WB router enum constructors stored wrong string repr | 2026-11-01 | ebe9f11 |
| DEF-F012 | WhistleblowerCategory missing bribery/data_privacy values | 2026-11-01 | ebe9f11 |

---

## Defect Summary

| Severity | Open | Fixed | Total |
|----------|------|-------|-------|
| Critical | 3 | 0 | 3 |
| High | 8 | 6 | 14 |
| Medium | 5 | 6 | 11 |
| Low | 2 | 0 | 2 |
| **Total** | **18** | **12** | **30** |

### Release Gate Status
- Critical defects: 3 open (FAIL -- must resolve before release)
- High defects: 8 open (FAIL -- must resolve before release)
