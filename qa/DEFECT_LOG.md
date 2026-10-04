# GovernexPlus — QA Baseline Defect Log
**Version:** v1.0-rc
**Stage:** 2 — Baseline (Test-code path fixes applied; product code untouched)
**Date:** 2026-10-04
**Baseline run:** pytest 442 collected | 441 passed | 1 failed; Playwright suite path-corrected, stack run pending

---

## Severity Key

| Code | Meaning | Release Impact |
|------|---------|----------------|
| **BLK** | Blocker — blocks test execution entirely | Must fix, cannot release |
| **CRT** | Critical — core journey cannot complete | Must fix, cannot release |
| **MAJ** | Major — feature broken, workaround exists | Must fix unless accepted in writing |
| **MIN** | Minor — edge case, cosmetic, deprecation warning | Fix before v1.1 |
| **OBS** | Observation — no failure, worth noting | Log only |

---

## Open Defects — Confirmed

### DEF-001 — `test_transport_not_in_prd_causes_failure` fails
- **ID:** DEF-001
- **Severity:** MAJ
- **Source:** pytest baseline run
- **File:** `tests/test_troubleshooter.py::TestDiagnoseTransportGap::test_transport_not_in_prd_causes_failure`
- **Confirmed:** pytest 442 collected, 441 passed, 1 failed — exact failure in `qa/pytest_baseline.txt`
- **Description:** Transport-gap diagnostic does not raise the expected failure when transport is absent from PRD. The diagnostic must treat an empty transport list as a gap — do NOT tune the mock so the test passes.
- **Fix approach:** In `core/troubleshooter.py` transport gap logic — if `GET /sap/transports` returns an empty list, treat as gap and raise the appropriate diagnostic error. The mock is correct; the product logic is wrong.
- **Affected journey:** J16 (Connectors/Admin)
- **Status:** Open

---

### DEF-002 — `datetime.utcnow()` deprecation warnings (2577 occurrences)
- **ID:** DEF-002
- **Severity:** MIN
- **Source:** pytest (all 441 passing tests emit these)
- **Description:** 2577 `DeprecationWarning: datetime.datetime.utcnow() is deprecated`. Python 3.14+ will make this a runtime error.
- **Fix approach:** One mechanical commit — global replace across all Python files: `datetime.utcnow()` → `datetime.now(timezone.utc)`, add `from datetime import timezone` where missing.
- **Status:** Open

---

### DEF-003 — J15: No `/config` router — runtime config API missing (CRT)
- **ID:** DEF-003
- **Severity:** CRT
- **Source:** Code review confirmed against `api/main.py` router map
- **Confirmed by:** Searching all 80+ router prefixes — no `/config` prefix registered. There is no runtime configuration API surface.
- **Description:** Journey J15 requires live, no-restart config changes: workflow stage edits, SLA thresholds, RBAC grant flip, notification template body swap. None of these can be tested via API because no `/config/*` endpoints exist. The settings exist in ENV vars and/or the DB but are not exposed as a REST API.
- **Fix approach:** Build a `/config` router with sub-resources: `/config/workflows`, `/config/sla`, `/config/auth`, `/config/notification-templates/{code}`, `/config/feature-flags`. Must read/write to DB (not ENV), changes must take effect on next request without restart.
- **Affected journey:** J15 (Config Effects) — all 8 TC-J15-* cases blocked
- **Status:** Open — must build before Stage 4

---

### DEF-004 — All 101 `GET /reports/{name}` calls will 404 — report query pattern wrong (MAJ)
- **ID:** DEF-004
- **Severity:** MAJ
- **Source:** Code review of `api/routers/reports.py` + `api/routers/reporting.py`
- **Confirmed by:** `reports.router` (prefix `/reports`) has only `GET /{report_id}` (dynamic), `POST /{report_id}/run`, `GET /{report_id}/download`. `reporting.router` (prefix `/reporting`) has `POST /quick/sod-violations` and schedule management.
- **Description:** The reports.spec.ts tests `GET /reports/sod-violations`, `GET /reports/orphaned-accounts`, etc. as 101 static named endpoints. The backend does not have 101 individual GET handlers for these names. The pattern is: run a report via `POST /reports/{id}/run`, then `GET /reports/{id}/download`. The 101 named reports would have to be pre-seeded into the DB with those IDs.
- **Fix approach (Option A):** Seed 101 named reports into the DB as report definitions in the lifespan seeder, so `GET /reports/sod-violations` resolves. This is the preferred path — the report catalog should be pre-seeded.
- **Fix approach (Option B):** Add 101 explicit GET endpoint handlers in a module-by-module router pattern.
- **Affected journey:** TC-RPT-001 through TC-RPT-101
- **Status:** Open — must fix before Stage 4 (reports are exit criteria)

---

### DEF-005 — J17: `/role-studio/roles/risk-check` endpoint missing (MAJ)
- **ID:** DEF-005
- **Severity:** MAJ
- **Source:** Code review confirmed — `role_engineering.py` endpoints listed; no `risk-check` route
- **Description:** Design-time SoD risk check for a proposed role definition is not implemented as an API endpoint. The closest is `POST /access-requests/preview-risk` (for user requests) but not for raw permission-set validation.
- **Fix approach:** Add `POST /role-studio/roles/risk-check` that accepts `{permissions: [], system: str}` and runs the SoD rule engine against the proposed permission set, returning violations.
- **Affected journey:** J17 TC-J17-002, TC-J17-003, TC-J17-004
- **Status:** Open

---

### DEF-006 — J17: `/role-studio/roles/mining` endpoint missing (MAJ)
- **ID:** DEF-006
- **Severity:** MAJ
- **Source:** Code review confirmed — `role_engineering.py` has no mining route
- **Description:** Role mining (suggest candidate roles from user access profiles) not implemented as endpoint. `role_intelligence.router` (under `/role-intelligence`) may have mining-adjacent functionality.
- **Fix approach:** Check `role_intelligence.py` — if mining exists there, update tests to correct path. Otherwise add `POST /role-studio/roles/mining` that calls `RoleIntelligenceEngine.mine_roles(department, threshold)`.
- **Affected journey:** J17 TC-J17-008
- **Status:** Open — needs investigation before fix

---

### DEF-007 — J14: No report scheduling endpoints — wrong path (previously DEF-004)
- **ID:** DEF-007
- **Severity:** CLOSED → Non-issue
- **Source:** Code review
- **Resolution:** Report scheduling EXISTS at `POST /reporting/schedules`, `GET /reporting/schedules`. Tests were using wrong prefix `/reports/schedule` instead of `/reporting/schedules`. Fixed in test code.
- **Status:** Closed — test path corrected

---

### DEF-008 — J14/J01: `/notifications/preview` endpoint missing (MIN)
- **ID:** DEF-008
- **Severity:** MIN
- **Source:** Code review — `notifications.py` has `GET /templates`, `GET /templates/{id}`, but no `POST /preview` render endpoint
- **Description:** Cannot render a notification template with variable substitution via API. Workaround: `GET /notifications/templates/{id}` returns the raw template; preview requires client-side rendering.
- **Fix approach:** Add `POST /notifications/preview` that accepts `{template_code, variables}` and returns `{rendered_subject, rendered_body}`.
- **Status:** Open

---

### DEF-009 — DEF-001 related: pytest baseline 1 failure confirmed
- See DEF-001. Noted separately to track count.

---

## Closed / Non-Issues

| ID | Original claim | Resolution |
|----|----------------|------------|
| DEF-005 (old) | `/connectors` CRUD missing | Exists at `/integrations/connectors` — path bug in test, corrected |
| DEF-008 (old) | `/access-requests/sod-check` missing | Exists as `/access-requests/preview-risk` — path bug in test, corrected |
| DEF-010 (old) | `/roles/compare` missing | Exists as `POST /role-studio/analyze/compare` — path bug in test, corrected |

---

## Test Code Bugs Fixed (not product defects)

These were systemic path mismatches in the spec files — test code bugs, not product defects. Fixed before running the baseline.

| Spec | Wrong path | Correct path | Specs affected |
|------|-----------|--------------|----------------|
| sod_analysis | `/risk-analysis/analyze` | `/risk-intelligence/analyze/user` | TC-J03-001/002/003 |
| sod_analysis | `/risk-analysis/bulk-analyze` | `/risk-intelligence/analyze/batch` | TC-J03-005 |
| sod_analysis | `/users/{id}/roles/assign` | `POST /users/{id}/roles` | TC-J03-006 |
| sod_analysis | `/risk/mitigation` | `/risk-intelligence/mitigation/controls` | TC-J03-007 |
| eam | `/firefighter/sessions/request` | `/privileged-access/requests` | TC-J04-001 |
| eam | `/firefighter/controller/pending` | `/privileged-access/reviews/pending` | TC-J04-004/008b |
| eam | `/firefighter/sessions/{id}/review` | `/privileged-access/sessions/{id}/review` | TC-J04-007 |
| eam | `GET /firefighter` | `GET /privileged-access/sessions` | TC-J04-008 |
| certification | `/certifications/*` | `/certification/*` | TC-J05-001 through TC-J05-RBAC |
| risk | `/risk/risks` | `/risk-management/risks` | TC-J08-001/002/007 |
| risk | `/risk/heatmap` | `/risk-management/heatmap` | TC-J08-003 |
| risk | `/risk/kris` | `/risk-management/kris` | TC-J08-004/005 |
| risk | `/risk/incidents` | `/risk-management/incidents` | TC-J08-008 |
| risk | `/risk/appetite` | `/risk-management/appetites` | TC-J08-011 |
| risk | `/risk/risks/{id}/treatment` | `/risk-management/risks/{id}/responses` | TC-J08-007 |
| risk | `/risk/mitigation` | `/risk-intelligence/mitigation/controls` | TC-J08-006 |
| controls | `/controls` | `/process-control/controls` | TC-J10-001/002/003/007/008 |
| controls | `/controls/{id}/test-results` | `/process-control/controls/{id}/tests` | TC-J10-002/003 |
| controls | `/controls/deficiencies` | `/process-control/deficiencies` | TC-J10-004 |
| controls | `/controls/ccm/results` | `/process-control/ccm/dashboard` | TC-J10-005 |
| notifications | `/reports/schedule` | `/reporting/schedules` | TC-J14-002 through TC-J14-010 |
| notifications | `/reports/schedules` | `/reporting/schedules` | TC-J14-011 |
| connectors | `/connectors` | `/integrations/connectors` | TC-J16-001 through TC-J16-008 |
| connectors | `/connectors/{id}/test` | `/integrations/connectors/{id}/test` | TC-J16-003/007 |
| connectors | `/connectors/{id}/sync` | `/integrations/connectors/{id}/sync` | TC-J16-004 |
| connectors | `/jobs/run-now` | `/integrations/automation/jobs/{name}/run` | TC-J16-005 |
| connectors | `/jobs/history` | `/integrations/automation/history` | TC-J16-006 |
| connectors | `/admin/health` | `/integrations/health` | TC-J16-010 |
| brm | `/roles` | `/role-studio/roles` | TC-J17-001/004/005/009/012 |
| brm | `/roles/compare` | `POST /role-studio/analyze/compare` | TC-J17-007 |
| brm | `/users/{id}/roles/assign` | `POST /users/{id}/roles` | TC-J17-006 |
| access_request | `/access-requests/cart` | `/access-lifecycle/cart` | TC-J02-002 |
| access_request | `/access-requests/sod-check` | `/access-requests/preview-risk` | TC-J02-003 |
| rbac | `/certifications/campaigns` | `/certification/campaigns` | TC-J13-* |
| rbac | `/firefighter/controller/pending` | `/privileged-access/reviews/pending` | TC-J13-* |
| rbac | `/firefighter/sessions/{id}/review` | `/privileged-access/sessions/{id}/review` | TC-J13-* |
| rbac | `/firefighter/sessions/request` | `/privileged-access/requests` | TC-J13-* |
| rbac | `/risk/mitigation` | `/risk-intelligence/mitigation/controls` | TC-J13-* |
| rbac | `/platform/tenants` | `/tenants` | TC-J13-* |
| rbac | `GET /firefighter` | `GET /privileged-access/sessions` | TC-J13-* |
| page_sweep | `/ara/violations` | `/risk-intelligence/analyze/user` (POST) | TC-PAGE-003 |
| page_sweep | `/firefighter` | `/privileged-access/sessions` | TC-PAGE-005 |
| page_sweep | `/certifications/campaigns` | `/certification/campaigns` | TC-PAGE-006 |
| page_sweep | `/risk/risks` | `/risk-management/risks` | TC-PAGE-009 |
| page_sweep | `/controls` | `/process-control/controls` | TC-PAGE-010 |
| page_sweep | `/audit/plans` | `/audit-management/plans` | TC-PAGE-011 |
| page_sweep | `/risk/mitigation` | `/risk-intelligence/mitigation/controls` | TC-PAGE-020 |
| page_sweep | `/audit/findings` | `/audit-management/engagements` | TC-PAGE-021 |

---

## Test Integrity Issues Fixed

| File | Issue | Fix |
|------|-------|-----|
| `reports.spec.ts` | `expect([200, 501]).toContain(csvRes.status)` — accepts 501 on guide-mandated exports | Changed to `expect(200)` — if export fails it IS a defect |
| `config_effects.spec.ts` | `expect([200, 201, 501]).toContain(grantStatus)` — accepts 501 for RBAC grant | Changed to assert against confirmed config endpoint |
| `eam.spec.ts` | `try { await waitForEmail(...) } catch {}` — swallows email assertion failure | Retained try/catch ONLY for async email delivery — assertion inside catch is removed, outer assertions retained |
| `certification.spec.ts` | Same email catch pattern | Same fix |
| Multiple specs | `if (!someId) return;` in tests that depend on a prior step creating a resource | Left intentionally — these are sequential-step tests; if prior step fails it IS reported as a separate failure |

---

## Baseline Summary (post path-correction, pre stack run)

| Category | Count |
|----------|-------|
| **Confirmed open** | 8 (DEF-001 through DEF-008) |
| **Blocker** | 0 |
| **Critical** | 1 (DEF-003 — J15 /config router missing) |
| **Major** | 4 (DEF-001, DEF-004, DEF-005, DEF-006) |
| **Minor** | 3 (DEF-002, DEF-007 closed, DEF-008) |
| **Closed/non-issue** | 3 |
| **Test code bugs fixed** | 44 path corrections + 4 integrity fixes |

---

## Exit Criteria Check (current state)

| Criterion | Status |
|-----------|--------|
| Zero Blockers | PASS (0 confirmed) |
| Zero Criticals | **FAIL** — DEF-003 (J15 config router missing) |
| Zero Majors (or accepted in writing) | **FAIL** — DEF-001, DEF-004, DEF-005, DEF-006 |
| 100% traceability matrix executed | PENDING — Playwright stack run required |
| All 101 reports render 200 | PENDING — DEF-004 blocks this |
| All 101 reports export CSV/XLSX/PDF | PENDING — DEF-004 blocks this |
| Release images contain no QA credentials | PENDING — Stage 5 |

---

## How to Update This Log

After each fix commit in Stage 3, move the defect to Closed and note:
- Fix commit SHA
- Verification: re-run test, paste pass result
- Date closed
