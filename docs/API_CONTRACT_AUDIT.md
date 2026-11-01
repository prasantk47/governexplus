# API Contract Audit Report

**Date:** 2026-11-01 | **Baseline:** v1.0-rc-baseline

---

## 1. Live API Health Check Results

Tested 52 key endpoints against production (https://governexplus.com/api):

| Status | Count | % |
|--------|-------|---|
| 200 OK | 30 | 57.7% |
| 404 Not Found | 19 | 36.5% |
| 405 Method Not Allowed | 2 | 3.8% |
| 500 Internal Server Error | 1 | 1.9% |

### Healthy Endpoints (200 OK) -- 30

Core GRC modules responding correctly:
- dashboard/stats, certification (campaigns, statistics)
- risk-management (risks, workflows, heatmap, incidents)
- process-control (controls, deficiencies)
- audit-management (plans, engagements, findings)
- tprm/vendors, jml (events, policies)
- bcm (plans, activations, dashboard)
- fraud (rules, alerts, cases, dashboard)
- whistleblower (cases, dashboard)
- library (packs, items), integrations/connectors
- role-studio/roles, mitigation/controls, risk/rules

### 404 Not Found -- 19 endpoints

Routes that the server does not recognize at the tested paths:

| Path Tested | Likely Correct Path | Root Cause |
|-------------|-------------------|------------|
| /dashboard/summary | /dashboard/executive-summary | Different path name |
| /users | /user-profiles or /users/list | Needs suffix |
| /access-requests | /access-requests/list | Needs suffix |
| /approvals | /approvals/pending | Needs suffix |
| /privileged-access/dashboard | /privileged-access/summary | Different path |
| /risk/dashboard | /risk/analysis/summary | Different path |
| /risk-rules | /risk-rules/list | Needs suffix |
| /process-control/tests | /process-control/test-results | Different path |
| /audit/violations | /audit/sod-violations | Different path |
| /surveys | /surveys/list | Needs suffix |
| /access-reports/summary | /access-reports/overview | Different path |
| /integrations | /integrations/status | Needs suffix |
| /workflows | /workflows/list | Needs suffix |
| /notifications | /notifications/inbox | Needs suffix |
| /reports | /reports/list | Needs suffix |
| /security-controls | /security-controls/list | Needs suffix |
| /provisioning/requests | /provisioning/queue | Different path |
| /intelligence/search | POST only | Wrong method |
| /ai/copilot/status | /ai-copilot/status | Different prefix |

**Note:** Many of these 404s are caused by testing with a bare prefix path. The actual route requires a more specific path. This is NOT necessarily a defect -- the frontend knows the correct paths.

### 405 Method Not Allowed -- 2 endpoints

| Path | Issue | Fix |
|------|-------|-----|
| /risk-management/kris | KRI list is POST-only (requires filter body) | Design choice, not a defect |
| /tprm/issues | Issues list is POST-only or nested under vendor ID | Design choice |

### 500 Internal Server Error -- 1 endpoint (DEFECT)

| Path | Error | Severity |
|------|-------|----------|
| /settings/smtp | Internal server error | Medium |

**Root cause:** Likely unhandled None when no SMTP config exists in DB.

---

## 2. Frontend-Backend Contract Mapping

### Service Files

| Service File | Lines | Endpoints Covered |
|-------------|-------|------------------|
| api.ts | 666 | Main API client, auth, users, roles, access requests, approvals, certifications, firefighter, risk, dashboard, reports |
| riskManagementApi.ts | 69 | Risk register CRUD, risk aggregation |
| intelligenceApi.ts | 122 | Troubleshooter, role intelligence, audit evidence, migration, timeline |
| auditManagementApi.ts | 70 | Plans, engagements, findings |
| processControlApi.ts | 79 | Controls, testing, deficiencies |
| provisioningApi.ts | 393 | Provisioning requests, system integration |

### Known Mismatches

| Issue | Frontend | Backend | Severity |
|-------|----------|---------|----------|
| Enum values | Frontend may send uppercase status values | Backend expects lowercase (after VARCHAR migration) | Medium |
| Pagination | Some pages use offset/limit, others use page/size | Backend uses offset/limit consistently | Low |
| Field naming | Some pages reference `id` | Some models use `risk_id`, `engagement_id`, etc. as the lookup key (not integer `id`) | High |

---

## 3. Orphan Endpoints (Backend routes no frontend calls)

Estimated ~400+ backend routes have no direct frontend caller. Many are:
- Admin/setup routes (called during deployment)
- Background job management endpoints
- Connector sync endpoints
- AI/ML inference endpoints
- Mobile API endpoints

These are not defects -- they serve programmatic/admin use cases.

---

## 4. Action Items

| ID | Description | Severity | Status |
|----|-------------|----------|--------|
| API-001 | Fix /settings/smtp 500 error | Medium | Open |
| API-002 | Verify all frontend API paths match actual backend routes | High | Open |
| API-003 | Document all POST-only list endpoints for frontend consistency | Low | Open |
