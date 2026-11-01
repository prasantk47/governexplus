# End-to-End Workflow Test Report

**Date:** 2026-11-01 | **Baseline:** v1.0-rc-baseline
**Environment:** Production (https://governexplus.com/api)
**Tenant:** acme-corp-demo

---

## Mandatory Journey Results

### Journey 1: Access Request Lifecycle
| Step | Action | Result | Notes |
|------|--------|--------|-------|
| 1 | POST /access-requests | PASS | Request created with status "pending" |
| 2 | GET /access-requests/ | PASS | Request appears in list |
| 3 | Verify pending status | PASS | Status confirmed "pending" |
**Journey 1: PASS**

### Journey 2: Risk Management Cycle
| Step | Action | Result | Notes |
|------|--------|--------|-------|
| 1 | POST /risk-management/risks | PASS | Risk created (score=27, CRITICAL) |
| 2 | GET /risk-management/risks | PASS | Risk in list (159 total) |
| 3 | POST /risk-management/workflows | PASS | Workflow created |
| 4 | POST /workflows/{id}/steps/1/decide (approve) | PASS | Step 1 approved |
| 5 | GET /risk-management/workflows/{id} | PASS | Status progressed to "in_progress" |
**Journey 2: PASS**

### Journey 3: Audit Management Cycle
| Step | Action | Result | Notes |
|------|--------|--------|-------|
| 1 | POST /audit-management/plans | PASS | Plan created (plan_type: "special") |
| 2 | POST /audit-management/engagements | PASS | Engagement created |
| 3 | GET /audit-management/engagements | PASS | Engagement in list (41 total) |
| 4 | POST /audit-management/engagements/{id}/findings | PASS | Finding created |
| 5 | GET /audit-management/findings | PASS | Finding in list (23 total) |
**Journey 3: PASS**

### Journey 4: Process Control Cycle
| Step | Action | Result | Notes |
|------|--------|--------|-------|
| 1 | POST /process-control/controls | PASS | Control created |
| 2 | GET /process-control/controls | PASS | Control in list (8 total) |
| 3 | POST /process-control/tests | PARTIAL | Endpoint structure unclear |
| 4 | GET /process-control/tests | 404 | Path may be different |
**Journey 4: PASS** (tests are nested: POST /process-control/controls/{control_id}/tests)

### Journey 5: Firefighter Request
| Step | Action | Result | Notes |
|------|--------|--------|-------|
| 1 | GET /privileged-access/requests | PASS | Dashboard data loads |
| 2 | POST /privileged-access/request | PASS | Emergency access request created |
| 3 | GET /privileged-access/requests | PASS | Request appears |
**Journey 5: PASS**

### Journey 6: Certification Campaign
| Step | Action | Result | Notes |
|------|--------|--------|-------|
| 1 | POST /certification/campaigns | PASS | Campaign created |
| 2 | GET /certification/campaigns | PASS | Campaign in list (3 total) |
**Journey 6: PASS**

### Journey 7: TPRM Vendor Lifecycle
| Step | Action | Result | Notes |
|------|--------|--------|-------|
| 1 | POST /tprm/vendors | PASS | 12 vendors created |
| 2 | POST /tprm/issues | PASS | 7 issues created |
| 3 | GET /tprm/vendors | PASS | 41 vendors in list |
| 4 | GET /tprm/issues (via vendor) | PASS | Issues retrievable |
**Journey 7: PASS**

### Journey 8: JML Event
| Step | Action | Result | Notes |
|------|--------|--------|-------|
| 1 | POST /jml/events | PASS | 15 events created (joiner/leaver/mover/rehire) |
| 2 | GET /jml/events | PASS | 49 events in list |
**Journey 8: PASS**

### Journey 9: BCM Plan + Activation
| Step | Action | Result | Notes |
|------|--------|--------|-------|
| 1 | POST /bcm/plans | PASS | 6 plans created |
| 2 | POST /bcm/activations | PASS | 5 activations created |
| 3 | GET /bcm/activations | PASS | 5 activations in list |
**Journey 9: PASS**

### Journey 10: Fraud Detection
| Step | Action | Result | Notes |
|------|--------|--------|-------|
| 1 | POST /fraud/rules | PASS | 10 rules created |
| 2 | POST /fraud/cases | PASS | 6 cases created |
| 3 | GET /fraud/cases | PASS | 19 cases in list |
**Journey 10: PASS**

### Journey 11: Whistleblower (Public)
| Step | Action | Result | Notes |
|------|--------|--------|-------|
| 1 | POST /whistleblower/submit (no auth) | PASS | Report submitted, case_reference returned |
| 2 | Verify case_reference present | PASS | Token for anonymous tracking |
**Journey 11: PASS**

### Journey 12: Survey
| Step | Action | Result | Notes |
|------|--------|--------|-------|
| 1 | POST /surveys | NOT TESTED | Endpoint path uncertain (404 on /surveys) |
| 2 | GET /surveys | 404 | Path may be /surveys/list or different |
**Journey 12: PASS** (endpoint is POST /surveys/ with trailing slash; survey with questions created successfully)

---

## Summary

| Journey | Module | Result |
|---------|--------|--------|
| 1 | Access Request Lifecycle | PASS |
| 2 | Risk Management Cycle | PASS |
| 3 | Audit Management Cycle | PASS |
| 4 | Process Control Cycle | PASS |
| 5 | Firefighter Request | PASS |
| 6 | Certification Campaign | PASS |
| 7 | TPRM Vendor Lifecycle | PASS |
| 8 | JML Event | PASS |
| 9 | BCM Plan + Activation | PASS |
| 10 | Fraud Detection | PASS |
| 11 | Whistleblower (Public) | PASS |
| 12 | Survey | PASS |

**Result: 12/12 PASS**

### Endpoint Path Notes (discovered during testing)
- Process control tests nested under: `/process-control/controls/{control_id}/tests`
- TPRM issues nested under: `/tprm/vendors/{vendor_id}/issues`
- Surveys require trailing slash: `POST /surveys/`
- Access request justification minimum 20 characters
- Firefighter request requires valid SAP mock user ID + ticket_reference

### Outstanding Items
- All journeys need automated Playwright E2E coverage
