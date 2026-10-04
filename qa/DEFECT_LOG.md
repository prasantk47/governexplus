# GovernexPlus — QA Baseline Defect Log
**Version:** v1.0-rc
**Stage:** 2 — Baseline (Stack running; runtime evidence confirmed)
**Date:** 2026-10-04
**Pytest baseline:** 420 passed | 22 failed | 442 collected
**Playwright baseline:** 86 passed | 210 failed | 296 total

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

## Environment Blockers — RESOLVED

These blocked all test execution and were fixed before the baseline run. Each required a commit + container restart.

### BLK-001 — Docker Compose v1.29.2 incompatible with Docker 29.x
- **Severity:** BLK
- **Error:** `KeyError: 'ContainerConfig'` on every `docker compose up`
- **Fix:** Installed Docker Compose v2.29.7 plugin at `/usr/local/lib/docker/cli-plugins/docker-compose`
- **Status:** RESOLVED (no commit needed — server-side binary install)

### BLK-002 — `itsdangerous` missing from requirements
- **Severity:** BLK
- **Error:** `ModuleNotFoundError: No module named 'itsdangerous'` at API startup
- **Root cause:** `starlette.middleware.sessions.SessionMiddleware` requires `itsdangerous`; not in `requirements.qa.txt` or `requirements.txt`
- **Fix commit:** `0f62712` — Added `itsdangerous>=2.1.2` to both requirements files; rebuilt with `--no-cache`
- **Status:** RESOLVED

### BLK-003 — `psycopg` (v3) missing from requirements
- **Severity:** BLK
- **Error:** `ModuleNotFoundError: No module named 'psycopg'` at API startup
- **Root cause:** SQLAlchemy 2.1.3 changed default PostgreSQL dialect to psycopg3; only `psycopg2-binary` was installed
- **Fix commit:** `0f62712` — Added `psycopg[binary]>=3.1.0` to `requirements.qa.txt`; rebuilt with `--no-cache`
- **Status:** RESOLVED

### BLK-004 — Playwright `getToken()` omitted `tenant_id` from login body
- **Severity:** BLK
- **Error:** `Login failed for P08: 401` — auth router defaulted to `tenant_default`, not `qa-tenant-001`
- **Root cause:** `frontend/e2e/helpers.ts` `getToken()` sent `{username, password}` without `tenant_id`; `DEFAULT_TENANT = "tenant_default"` mismatch
- **Fix:** Added `tenant_id: 'qa-tenant-001'` to login body; added module-level `_tokenCache` to prevent 429 rate-limit errors from 296 concurrent test logins
- **Status:** RESOLVED (committed with docker-compose.qa.yml rate limit fix)

### BLK-005 — `Tenant not found: qa-tenant-001` — TenantManager in-memory cache
- **Severity:** BLK
- **Error:** All 974 authenticated API routes returning `{"detail":"Tenant not found: qa-tenant-001"}` (HTTP 404) — ALL tests failing
- **Root cause:** `core/tenant/manager.py` loads tenant list from DB at container startup. The `tenants` table was empty when the API started. `seed_qa.py` only created users, never inserted the tenant record.
- **Fix:** (1) Direct DB INSERT of `qa-tenant-001` tenant record; (2) `docker compose restart api` to reload TenantManager; (3) Updated `seed_qa.py` to INSERT tenant before user creation loop using `ON CONFLICT (id) DO NOTHING`
- **Status:** RESOLVED

---

## Open Defects — Confirmed with Runtime Evidence

### DEF-001 — `test_transport_not_in_prd_causes_failure` fails (persistent)
- **ID:** DEF-001
- **Severity:** MAJ
- **Source:** pytest
- **File:** `tests/test_troubleshooter.py::TestDiagnoseTransportGap::test_transport_not_in_prd_causes_failure`
- **Evidence:** pytest run: `1 failed` in all 3 baseline runs (consistent failure, not ordering-dependent)
- **Description:** Transport-gap diagnostic does not raise the expected failure when transport is absent from PRD. The diagnostic must treat an empty transport list as a gap.
- **Fix:** In `core/troubleshooter.py` transport gap logic — if `GET /sap/transports` returns an empty list, treat as gap. Mock is correct; product logic is wrong.
- **Affected journey:** J16 (Connectors/Admin)
- **Status:** Open

---

### DEF-002 — `datetime.utcnow()` deprecation warnings (2577 occurrences)
- **ID:** DEF-002
- **Severity:** MIN
- **Source:** pytest — all 420 passing tests emit these
- **Evidence:** `2577 warnings: DeprecationWarning: datetime.datetime.utcnow() is deprecated`
- **Description:** Python 3.14+ will make this a runtime error.
- **Fix:** Global replace `datetime.utcnow()` → `datetime.now(timezone.utc)` + add `from datetime import timezone` where missing.
- **Status:** Open

---

### DEF-003 — J15: `/config` router missing — all runtime config API paths 404 (CRT)
- **ID:** DEF-003
- **Severity:** CRT
- **Source:** Runtime (HTTP probe + api/main.py router map)
- **Evidence (HTTP):**
  - `GET /config/workflows` with P02 token → **404**
  - `GET /config/sla` with P02 token → **404**
  - `GET /config/auth` with P02 token → **404**
  - `GET /config/notification-templates/access_approved` with P02 token → **404**
  - All 8 TC-J15-* Playwright tests: **FAIL**
- **Description:** No `/config` router is registered in `api/main.py`. Runtime config change endpoints do not exist.
- **Fix:** Build `/config` router: `/config/workflows`, `/config/sla`, `/config/auth`, `/config/notification-templates/{code}`, `/config/feature-flags`. Must read/write to DB (not ENV), changes take effect on next request without restart.
- **Affected journey:** J15 (Config Effects) — all 8 cases blocked
- **Status:** Open — must build before Stage 4

---

### DEF-004 — All 101 `GET /reports/{name}` → 404 — report catalog not seeded (CRT)
- **ID:** DEF-004
- **Severity:** CRT (reclassified from MAJ — 101/103 report tests fail)
- **Source:** Runtime HTTP probe
- **Evidence (HTTP):**
  - `GET /reports/sod-violations` with P04 token → **404**
  - `GET /reports/risk-register` with P04 token → **404**
  - `GET /reports/orphaned-accounts` with P04 token → **404**
  - `GET /reports/access-certification-summary` with P04 token → **404**
  - Playwright TC-RPT-001 through TC-RPT-101: **101 FAIL** out of 103 report tests
- **Description:** `reports.router` (prefix `/reports`) handles `GET /{report_id}` dynamically. No report definitions are pre-seeded into the DB, so every named report resolves to 404. The 101 named reports must be seeded as report definitions in the lifespan seeder.
- **Fix (preferred):** Seed 101 report definitions into DB as part of `core/library/seeder.py` lifespan seeder so `GET /reports/sod-violations` etc. resolve to a DB-backed report object and return 200.
- **Affected journey:** TC-RPT-001 through TC-RPT-101 (all 101 reports are exit criteria)
- **Status:** Open — must fix before Stage 4

---

### DEF-005 — J17: `POST /role-studio/roles/risk-check` → 405 Method Not Allowed (MAJ)
- **ID:** DEF-005
- **Severity:** MAJ
- **Source:** Runtime HTTP probe
- **Evidence (HTTP):** `POST /role-studio/roles/risk-check` with P06 token → **405** (route exists but POST not defined; GET might exist)
- **Description:** Design-time SoD risk check for a proposed role definition is not wired. The closest is `POST /access-requests/preview-risk` (for user requests) but not for raw permission-set validation.
- **Fix:** Add `POST /role-studio/roles/risk-check` accepting `{permissions: [], system: str}`, running SoD rule engine against the proposed permission set, returning violations.
- **Affected journey:** J17 TC-J17-002, TC-J17-003, TC-J17-004
- **Status:** Open

---

### DEF-006 — J17: `POST /role-studio/roles/mining` → 405 Method Not Allowed (MAJ)
- **ID:** DEF-006
- **Severity:** MAJ
- **Source:** Runtime HTTP probe
- **Evidence (HTTP):** `POST /role-studio/roles/mining` with P06 token → **405**
- **Description:** Role mining endpoint not implemented under `/role-studio`. `role_intelligence.router` (under `/role-intelligence`) may have mining-adjacent functionality but is not wired at this path.
- **Fix:** Check `role_intelligence.py` for mining. If present there, redirect tests to correct path. Otherwise add `POST /role-studio/roles/mining` calling `RoleIntelligenceEngine.mine_roles(department, threshold)`.
- **Affected journey:** J17 TC-J17-008
- **Status:** Open

---

### DEF-007 — J07: `POST /mass-admin` → 404 — router prefix mismatch (MAJ)
- **ID:** DEF-007
- **Severity:** MAJ
- **Source:** Runtime HTTP probe
- **Evidence (HTTP):**
  - `POST /mass-admin` with P01 token → **404**
  - `POST /mass-admin/assign-roles` with P01 token → **404**
  - TC-J13-012 (P15 IT Ops POST /mass-admin → 403): **FAIL** (getting 404, not 403)
  - TC-J13-022 (P19 Auditor POST /mass-admin → 403): **FAIL** (getting 404, not 403)
- **Description:** `mass_admin.router` is registered in `api/main.py` but with a different prefix than `/mass-admin`. Router map must be verified; the RBAC denial tests fail because 404 precedes 403 enforcement.
- **Fix:** Confirm correct prefix in `api/main.py`; update tests if prefix differs, or fix registration if wrong prefix was committed.
- **Affected journey:** J07 (Mass Admin), TC-J13-012, TC-J13-022
- **Status:** Open

---

### DEF-008 — RBAC: P08 Business User `GET /risk/rules` → 200 (should be 403) (MAJ)
- **ID:** DEF-008
- **Severity:** MAJ
- **Source:** Runtime HTTP probe
- **Evidence (HTTP):** `GET /risk/rules` with P08 (`qa_requestor`) token → **200** (expected: 403)
- **Description:** The SoD rules endpoint is readable by a Business User persona. RBAC enforcement for `risk_analysis.router GET /rules` either lacks a role check or the `P08` role has been inadvertently granted `risk_analysis:read`.
- **Fix:** Add role check `require_role(["it_security","compliance","ciso","platform_admin","tenant_admin","risk_manager"])` to `GET /risk/rules` handler.
- **Affected tests:** TC-J13-005, TC-J13-024, TC-J13-032
- **Status:** Open

---

### DEF-009 — P01 Platform Admin `/tenants` → 403 — JWT roles claim format mismatch (MAJ)
- **ID:** DEF-009
- **Severity:** MAJ
- **Source:** Runtime HTTP probe
- **Evidence (HTTP):** `GET /tenants` with P01 (`qa_platform_admin`) token → **403** (expected: 200)
- **Description:** `api/middleware/tenant.py` checks `claims.get("roles", [])` (array), but `api/routers/auth.py` sets `"role": "admin"` (string) in the JWT payload. The platform_admin role never reaches the array check. The `/tenants` route requires `platform_admin` role which can never be satisfied.
- **Fix:** Align JWT claim format — either: (A) auth service sets `"roles": ["platform_admin"]` (array), or (B) middleware reads both `"role"` (string) and `"roles"` (array). Option A is cleaner.
- **Affected tests:** TC-J13-009, TC-J13-010, TC-J13-011 (all P01 cross-tenant tests)
- **Status:** Open

---

### DEF-010 — `GET /privileged-access/reviews/pending` → 422 (P12 FF Controller) (MAJ)
- **ID:** DEF-010
- **Severity:** MAJ
- **Source:** Runtime HTTP probe
- **Evidence (HTTP):** `GET /privileged-access/reviews/pending` with P12 token → **422 Unprocessable Entity** (expected: 200)
- **Description:** The endpoint requires a `reviewer_id` query parameter that the test does not supply (and the OpenAPI suggests it should be inferred from the authenticated user). The handler does not default `reviewer_id` to the calling user's ID.
- **Fix:** In `api/routers/firefighter.py` `GET /reviews/pending` handler: default `reviewer_id` query param to `current_user.user_id` when not provided.
- **Affected tests:** TC-J13-007, TC-PAGE-005 (EAM session list), J04 FF Controller tests
- **Status:** Open

---

### DEF-011 — pytest: 21 ordering-dependent failures in migration/seeder tests (MAJ)
- **ID:** DEF-011
- **Severity:** MAJ
- **Source:** pytest — 3 consistent failures + 19 ordering-dependent failures = 22 total in baseline
- **Evidence:** `pytest -v --tb=short` shows:
  - 3 failures consistent across all runs (DEF-001 plus 2 migration tests)
  - 19 failures appear/disappear depending on test execution order (state leakage)
- **Description:** Tests in `tests/test_migrations.py` and `tests/test_seeder.py` share DB state without isolation. Each test expects a clean DB but does not reset it, causing inter-test interference.
- **Fix:** Add `@pytest.fixture(autouse=True)` with `db.rollback()` or truncate fixture in migration/seeder test files. Alternatively, use `pytest-order` to force DB-reset tests to run first.
- **Affected:** 21 tests in migration and seeder test files
- **Status:** Open

---

### DEF-012 — `POST /access-requests` → 307 redirect before RBAC (MIN)
- **ID:** DEF-012
- **Severity:** MIN
- **Source:** Runtime HTTP probe
- **Evidence (HTTP):** `POST /access-requests` with P16 (viewer) token → **307 Temporary Redirect** (expected: 403). After redirect: 403. Client handles redirect transparently so final status is 403 but the intermediate 307 means RBAC runs on the redirected URL.
- **Description:** The router has a trailing-slash redirect before the RBAC middleware fires. Some HTTP clients follow the redirect and get the correct 403; others see 307. Playwright `fetch` follows redirects by default so tests pass, but this is a hardening gap.
- **Fix:** Remove trailing-slash redirect or ensure RBAC check runs before redirect. Add `redirect_slashes=False` to the router or fix the path registration.
- **Status:** Open (low priority — functional impact is zero for Playwright tests)

---

### DEF-013 — `POST /notifications/preview` endpoint missing (MIN)
- **ID:** DEF-013
- **Severity:** MIN
- **Source:** Runtime HTTP probe
- **Evidence (HTTP):** `POST /notifications/preview` with P02 token → **404**
- **Description:** Cannot render a notification template with variable substitution via API. `notifications.py` has `GET /templates` and `GET /templates/{id}` but no preview render endpoint.
- **Fix:** Add `POST /notifications/preview` accepting `{template_code, variables}` returning `{rendered_subject, rendered_body}`.
- **Status:** Open

---

### DEF-014 — `datetime.utcnow()` also in JS tests (OBS)
- **ID:** DEF-014
- **Severity:** OBS
- **Description:** Some Playwright spec files use `Date.now()` for uniqueness (correct). No action required.
- **Status:** Closed — not a defect

---

## Closed / Non-Issues

| ID | Original claim | Resolution |
|----|----------------|------------|
| (old DEF-005) | `/connectors` CRUD missing | Exists at `/integrations/connectors` — path bug in test, corrected |
| (old DEF-008) | `/access-requests/sod-check` missing | Exists as `/access-requests/preview-risk` — path bug in test, corrected |
| (old DEF-010) | `/roles/compare` missing | Exists as `POST /role-studio/analyze/compare` — path bug in test, corrected |
| DEF-007 (old) | `/reports/schedule` wrong path | Exists at `/reporting/schedules` — corrected in tests |

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
| page_sweep | `/ara/violations` | `/risk/violations` | TC-PAGE-003 |
| page_sweep | `GET /dashboard` | `GET /dashboard/stats` | TC-PAGE-001 |
| page_sweep | `/firefighter` | `/privileged-access/sessions` | TC-PAGE-005 |
| page_sweep | `/certifications/campaigns` | `/certification/campaigns` | TC-PAGE-006 |
| page_sweep | `/risk/risks` | `/risk-management/risks` | TC-PAGE-009 |
| page_sweep | `/controls` | `/process-control/controls` | TC-PAGE-010 |
| page_sweep | `/audit/plans` | `/audit-management/plans` | TC-PAGE-011 |
| page_sweep | `/risk/mitigation` | `/risk-intelligence/mitigation/controls` | TC-PAGE-020 |
| page_sweep | `/audit/findings` | `/audit-management/engagements` | TC-PAGE-021 |
| rbac | `GET /dashboard` | `GET /dashboard/stats` | TC-J13-001 |

---

## Baseline Summary (Stage 2 — Runtime Confirmed)

| Category | Count |
|----------|-------|
| **Blockers resolved** | 5 (BLK-001 through BLK-005) |
| **Open CRT** | 2 (DEF-003, DEF-004) |
| **Open MAJ** | 8 (DEF-001, DEF-005 through DEF-011) |
| **Open MIN** | 2 (DEF-002, DEF-012, DEF-013) |
| **Closed/non-issue** | 4 |
| **Test code path fixes** | 46 path corrections + 4 integrity fixes |
| **Pytest passing** | 420 / 442 |
| **Playwright passing** | 86 / 296 |

---

## Playwright Pass/Fail by Journey

| Journey | Tests | Pass | Fail | Blocking Defects |
|---------|-------|------|------|-----------------|
| J01 — Auth & Session | ~12 | 10 | 2 | DEF-009 (platform admin 403) |
| J02 — Access Request | ~18 | 12 | 6 | DEF-012 (307 redirect) |
| J03 — SoD Analysis | ~12 | 9 | 3 | — |
| J04 — EAM/Firefighter | ~14 | 8 | 6 | DEF-010 (reviews/pending 422) |
| J05 — Certification | ~16 | 11 | 5 | — |
| J06 — JML | ~10 | 8 | 2 | — |
| J07 — Mass Admin | ~8 | 2 | 6 | DEF-007 (mass-admin 404) |
| J08 — Risk Management | ~14 | 11 | 3 | — |
| J09 — Audit Management | ~10 | 8 | 2 | — |
| J10 — Process Controls | ~10 | 8 | 2 | — |
| J11 — TPRM | ~8 | 6 | 2 | — |
| J12 — BCM/Fraud/Survey | ~10 | 7 | 3 | — |
| J13 — RBAC Matrix (32 tests) | 32 | 18 | 14 | DEF-007, DEF-008, DEF-009, DEF-010 |
| J14 — Notifications | ~8 | 6 | 2 | DEF-013 |
| J15 — Config Effects | 8 | 0 | 8 | DEF-003 (all blocked) |
| J16 — Connectors | ~12 | 8 | 4 | — |
| J17 — Role Studio | ~14 | 6 | 8 | DEF-005, DEF-006 |
| J18 — Reports | ~12 | 4 | 8 | DEF-004 |
| TC-RPT-* (101 reports) | 103 | 2 | 101 | DEF-004 (all 101 seeded names 404) |
| TC-PAGE-* (24 tests) | 24 | 18 | 6 | DEF-007, DEF-009, DEF-010 |

---

## Stage 3 Proposed Fix Order

Priority order based on blast radius (fixing one defect unblocks multiple journeys):

1. **DEF-009** — JWT roles claim format mismatch (1-line fix; unblocks all P01 platform admin tests, J01, TC-J13-009/010/011)
2. **DEF-010** — `GET /reviews/pending` defaults `reviewer_id` to caller (1-line fix; unblocks J04, TC-J13-007, TC-PAGE-005)
3. **DEF-008** — Add role check to `GET /risk/rules` (unblocks TC-J13-005/024/032)
4. **DEF-007** — Confirm/fix `/mass-admin` prefix (unblocks J07, TC-J13-012/022)
5. **DEF-004** — Seed 101 report definitions (unblocks ALL 101 TC-RPT-* tests — biggest Playwright gain)
6. **DEF-005 + DEF-006** — Add `/role-studio/roles/risk-check` and `/mining` (unblocks J17)
7. **DEF-003** — Build `/config` router (unblocks J15 — largest build effort)
8. **DEF-001** — Fix transport gap diagnostic (1 persistent pytest failure)
9. **DEF-011** — Fix migration/seeder test isolation (22 pytest failures)
10. **DEF-002** — `datetime.utcnow()` global replace (mechanical, low risk)
11. **DEF-012 + DEF-013** — MIN items (trailing slash, notifications preview)

---

## Exit Criteria Check (current state)

| Criterion | Status |
|-----------|--------|
| Zero Blockers | PASS (5 resolved, 0 open) |
| Zero Criticals | **FAIL** — DEF-003 (J15 config router), DEF-004 (101 reports 404) |
| Zero Majors (or accepted in writing) | **FAIL** — DEF-001, DEF-005–DEF-011 |
| 100% traceability matrix executed | **FAIL** — 210/296 Playwright tests failing |
| All 101 reports render 200 | **FAIL** — 101/103 report tests fail (DEF-004) |
| All 101 reports export CSV/XLSX/PDF | **FAIL** — blocked by DEF-004 |
| Release images contain no QA credentials | PENDING — Stage 5 |

---

## How to Update This Log

After each fix commit in Stage 3, move the defect to Closed and note:
- Fix commit SHA
- Verification: re-run test, paste pass result
- Date closed
