# GovernexPlus v1.0 — Test Cases

**Version:** 1.1 (revised per Stage 1 review)
**Date:** 2026-10-04
Total: **18 journeys · 156 named cases + 101 report parametrized cases = 257 cases**

---

## J01 — Authentication & Session Management

### TC-J01-001: Valid Login Returns JWT
- **Persona:** P08 | **Steps:** POST /auth/login with valid creds | **Expected:** 200, access_token present

### TC-J01-002: Invalid Password Returns 401
- **Persona:** P08 | **Steps:** Wrong password | **Expected:** 401 "Invalid credentials"

### TC-J01-003: Account Lockout After 5 Failed Attempts
- **Persona:** P16 | **Steps:** 5 wrong attempts | **Expected:** 6th → 423, account_locked: true

### TC-J01-004: Locked Account Cannot Login with Correct Password
- **Persona:** P16 (locked) | **Expected:** 423

### TC-J01-005: Token Expiry Produces 401
- **Steps:** Use expired JWT on /auth/me | **Expected:** 401

### TC-J01-006: Logout Blacklists Token
- **Steps:** Login → POST /auth/logout → use old token | **Expected:** 401

### TC-J01-007: X-User-ID Header Ignored (Hardened Middleware)
- **Steps:** GET /users/me with X-User-ID: ADMIN001 header, no JWT | **Expected:** 401

### TC-J01-008: Cross-Tenant Data Isolation
- **Steps:** P02 user in qa-tenant-001; P01 accesses different tenant; tries GET /users
- **Expected:** Cannot see qa-tenant-001 users without escalation log entry

---

## J02 — Access Request Full Approval Chain

### TC-J02-001: Submit Access Request
- **Persona:** P08 | **Steps:** POST /access-requests/submit {role: Z_FI_AP_CLERK, system: PRD}
- **Expected:** 201, pending_approval, email to P07 (verify Mailpit subject)

### TC-J02-002: Line Manager (P07) Approves First Stage
- **Steps:** GET /access-requests/pending → approve
- **Expected:** status → pending_role_owner (2-stage) or approved (single-stage)

### TC-J02-003: Role Owner (P21) Approves Second Stage
- **Steps:** P21 approves own-role request
- **Expected:** status → provisioned; SAP mock receives POST RoleAssignmentSet; email to P08 (verify Mailpit body contains role name)

### TC-J02-004: Rejection Notification
- **Persona:** P21 | **Steps:** reject {reason: "Not required"}
- **Expected:** status → rejected; rejection email body contains reason (verify Mailpit)

### TC-J02-005: SoD Conflict Blocks Auto-Approve
- **Steps:** Submit role that conflicts with Alice's existing Z_FI_PAYMENT_APPROVER
- **Expected:** SoD warning in response, request not auto-approved

### TC-J02-006: High-Risk Request → 3-Stage Workflow
- **Steps:** Submit SAP_ALL equivalent
- **Expected:** 3-stage: manager → role owner → security (P06)

### TC-J02-007: Shopping Cart — Multi-Role Request
- **Steps:** P08 adds 3 roles to cart → submits
- **Expected:** 3 separate request items created, each tracked independently

---

## J03 — SoD Conflict Detection & Mitigation

### TC-J03-001: Violations Detected for Alice (AP + Payment roles)
- **Persona:** P06 | **Steps:** POST /risk-analysis/analyze {user_id: ALICE.J}
- **Expected:** violations include SOD-FI-001; severity critical/high

### TC-J03-002: Clean User Returns No Violations
- **Persona:** P06 | **Steps:** analyze BOB.S (IT role only) | **Expected:** violations empty

### TC-J03-003: Violation Severity Classification
- **Steps:** Analyze user with critical SoD | **Expected:** violation.severity = critical or high

### TC-J03-004: Mitigation Assignment
- **Persona:** P06 | **Steps:** POST /risk-analysis/violations/{id}/mitigate {mitigation_id: …}
- **Expected:** status → mitigated; P18 (Mitigation Monitor) has review task

### TC-J03-005: Bulk Analysis (10 users)
- **Persona:** P04 | **Steps:** POST /risk-analysis/bulk-analyze {user_ids: [×10]}
- **Expected:** 200, results for all 10, no 500

### TC-J03-006: SoD Check on Role Assignment
- **Persona:** P02 | **Steps:** POST /users/{id}/roles/assign with conflicting role
- **Expected:** 409 or warning with conflict details

### TC-J03-007: Mitigation Monitor (P18) Can Attest Control
- **Persona:** P18 | **Steps:** GET /ara/mitigations/{id} → POST attest
- **Expected:** 200, attestation recorded with timestamp

---

## J04 — Emergency Access (Firefighter) Lifecycle

### TC-J04-001: Firefighter (P17) Requests FF Session
- **Steps:** POST /firefighter/sessions/request {ff_id: FF_PRD_001, reason_code: CIR-001, incident: INC-123}
- **Expected:** 201; alert email to P12 (Controller) and P03 (CISO) — verify Mailpit body has ff_id + reason

### TC-J04-002: Session Starts and Activity Log Initialized
- **Persona:** P17 | **Steps:** POST /firefighter/sessions/{id}/start
- **Expected:** status → active; SAP mock GET FFLogSet called

### TC-J04-003: Session Ends — Log Review Task Created
- **Persona:** P17 | **Steps:** POST /firefighter/sessions/{id}/end
- **Expected:** status → ended; review task for P12; email (verify Mailpit SLA deadline in body)

### TC-J04-004: Controller (P12) Reviews and Signs Off
- **Steps:** GET /firefighter/sessions/{id}/log → POST review {action: approve}
- **Expected:** status → reviewed; timestamp recorded; SAP activity log items visible in review

### TC-J04-005: Flag Violation in Log Review
- **Persona:** P12 | **Steps:** review {action: flag_violation, comment: Unauthorized vendor change}
- **Expected:** RiskViolation created, severity high; P03 notified (Mailpit)

### TC-J04-006: Overdue Review Escalation (73h+ ago)
- **Steps:** Backdate session end_time by 73 hours; call /firefighter/check-overdue
- **Expected:** KRI-PRIV-002 value increments; escalation notification sent

### TC-J04-007: Business User (P08) Cannot Review Logs
- **Steps:** POST /firefighter/sessions/{id}/review as P08
- **Expected:** 403

### TC-J04-008: FF Owner (P11) Can View Own FF ID — Not Others
- **Steps:** P11 GET /eam/ids/{own-id} → 200; GET /eam/ids/{other-id} → 403

---

## J05 — Access Certification Campaign

### TC-J05-001: Launch Campaign from Template
- **Persona:** P04 | **Steps:** POST /certifications/campaigns {template: CERT-TPL-001, start_now: true}
- **Expected:** campaign created; review tasks assigned to P07/line managers; emails sent (Mailpit)

### TC-J05-002: Reviewer Sees Assigned Items
- **Persona:** P07 | **Steps:** GET /certifications/campaigns/{id}/my-items
- **Expected:** list of assigned items

### TC-J05-003: Certify Item
- **Persona:** P07 | **Steps:** POST decision {decision: certify}
- **Expected:** item → certified

### TC-J05-004: Revoke Item
- **Persona:** P07 | **Steps:** decision {decision: revoke, comment: No longer required}
- **Expected:** item → revoked; access revocation task created

### TC-J05-005: Campaign Completion Report
- **Steps:** Complete all items → GET /certifications/campaigns/{id}/report
- **Expected:** completion_rate = 100%; report JSON/PDF generated

### TC-J05-006: External Auditor Read-Only
- **Persona:** P09 | **Steps:** GET campaigns → 200; POST campaigns → 403

### TC-J05-007: Role Owner (P21) Certifies Own-Role Items
- **Persona:** P21 | **Steps:** certify items for their role | **Expected:** 200; items certified

---

## J06 — JML — Hire, Transfer, and Terminate

### TC-J06-001: Create New Hire Event
- **Persona:** P13 | **Steps:** POST /jml/events {event_type: hire, employee_id: EMP-9001, job_title: AP Analyst}
- **Expected:** 201; provisioning workflow triggered

### TC-J06-002: Role Assignment Based on Job Title
- **Steps:** Workflow completes
- **Expected:** user created with mapped roles for AP Analyst / Finance; SAP mock POST UserSet + POST RoleAssignmentSet called

### TC-J06-003: New Hire Welcome Email
- **Expected:** NOTIF-JML-ONBOARD email body contains employee name and system list (Mailpit)

### TC-J06-004: Create Transfer Event
- **Persona:** P13 | **Steps:** POST /jml/events {event_type: transfer, employee_id: EMP-1001, new_job_title: Finance Manager, new_dept: Finance}
- **Expected:** 201; re-certification task created; old role-set change workflow triggered

### TC-J06-005: Transfer — Old Roles Removed, Re-Cert Task Created
- **Steps:** Workflow completes
- **Expected:** roles from previous job title removed or flagged for cert; re-certification task visible to P07 (Line Manager)

### TC-J06-006: Termination Event Revokes Access Within 24h SLA
- **Persona:** P13 | **Steps:** POST /jml/events {event_type: termination, employee_id: EMP-1001, termination_date: today}
- **Expected:** 201; SAP mock PUT UserSet (lock) called within SLA; user.status → inactive

### TC-J06-007: Termination Confirmation Email
- **Expected:** NOTIF-JML-OFFBOARD body contains employee name + revocation timestamp (Mailpit)

### TC-J06-008: Terminated User Cannot Login
- **Steps:** POST /auth/login as EMP-1001 | **Expected:** 401 or 423

### TC-J06-009: KRI-TERM-001 Reflects SLA Breach
- **Steps:** Create termination with past date, skip SLA check
- **Expected:** KRI-TERM-001 amber or red status

---

## J08 — Risk Register & KRI Management

### TC-J08-001: Create Risk — Score Calculated
- **Persona:** P05 | **Steps:** POST /risk-management/risks {likelihood: 3, impact: 4}
- **Expected:** 201; inherent_score = 12; severity = high

### TC-J08-002: KRI Threshold Breach Alert
- **Steps:** Update KRI-SOD-001 value to 25
- **Expected:** escalation email to P03 and P04 (Mailpit); KRI status → red

### TC-J08-003: Risk Heatmap Renders
- **Persona:** P05 | **Steps:** GET /risk-management/heatmap
- **Expected:** 200; 5×5 matrix populated

### TC-J08-004: Risk Owner (P22) Can Update Own Risk
- **Persona:** P22 | **Steps:** PUT /risk-management/risks/{own-id} {residual_likelihood: 2}
- **Expected:** 200; updated; audit log entry

### TC-J08-005: Risk Owner Cannot Update Other's Risk
- **Persona:** P22 | **Steps:** PUT /risk-management/risks/{other-id}
- **Expected:** 403

---

## J09 — Template Library — Full Depth

### TC-J09-001: Browse Library Returns Seeded Items
- **Persona:** P02 | **Steps:** GET /library/items
- **Expected:** 200; items.length > 0 (day-one packs loaded)

### TC-J09-002: Activate a Template Item (single click)
- **Persona:** P02 | **Steps:** POST /library/items/{SOD-FI-001-id}/activate
- **Expected:** TenantItemActivation created; item.is_active = true; is_customized = false

### TC-J09-003: Copy-on-Write — Customizing Sets is_customized, Global Unchanged
- **Persona:** P02
- **Steps:** Activate SOD-FI-001 → PUT /library/activations/{id} {copy_payload: {risk_level: critical}}
- **Expected:** activation.is_customized = true; global TemplateItem.payload UNCHANGED (no mutation); copy_payload stored on activation row

### TC-J09-004: Pack Import is Idempotent
- **Persona:** P01 | **Steps:** POST /library/packs/import-file → repeat
- **Expected:** 2nd run: inserted = 0, updated = 0, skipped = N, errors = []

### TC-J09-004-b: Pack Builder Export
- **Persona:** P02 | **Steps:** POST /library/packs/export {item_codes: [SOD-FI-001, ARM-WF-001]}
- **Expected:** valid JSON pack with 2 items; pack_code present

### TC-J09-005: Update Review Shows Pending Updates
- **Steps:** Directly update a TemplateItem payload (checksum change) → GET /library/updates
- **Expected:** activation with pending_update_version appears in update review list

### TC-J09-006: Activation Wizard UI — Org/Owner/System Mapping
- **Persona:** P02 (Playwright)
- **Steps:** Navigate /library/wizard → select 3 items → map {org: Finance, owner: qa_sox_owner, system: PRD} → submit
- **Expected:** wizard completes; 3 activations created with mapping stored; per-item status visible

### TC-J09-007: Activation Wizard — Background Job Results
- **Steps:** After wizard submit, check per-item job results
- **Expected:** each item shows status: success / skipped / error (no silent failures)

### TC-J09-008: Deactivate then Reactivate
- **Steps:** Deactivate SOD-FI-001 → GET /library/items/{id} → is_active = false
          Reactivate → is_active = true; is_customized state preserved from before deactivation

### TC-J09-009-a: Update Review — Apply Update (Unmodified Item)
- **Steps:** Item has pending_update_version, is_customized = false → POST apply
- **Expected:** activation payload updated to new version; pending_update_version cleared

### TC-J09-009-b: Update Review — Keep-Mine (Customized Item)
- **Steps:** Item has pending_update_version, is_customized = true → POST keep-mine
- **Expected:** copy_payload retained unchanged; pending_update_version cleared; global update NOT applied to this activation

### TC-J09-009-c: Global Update Does Not Touch Customized Activation
- **Steps:** Run importer with updated SOD-FI-001 payload; activation is_customized = true
- **Expected:** activation.copy_payload UNCHANGED; pending_update_version set on the activation row (not auto-applied)

### TC-J09-010: ARA Behavioral CoW — Engine Consumes Customized Tenant Copy
- **Steps:**
  1. Activate SOD-FI-001 → customize it to severity: low (copy_payload)
  2. Run ARA analysis for Alice (has AP + payment roles)
  3. Verify returned violation uses the TENANT's customized severity (low), not global (high)
- **Expected:** violation.severity = low (from tenant copy); demonstrates engine reads TenantItemActivation copy_payload

### TC-J09-011: ARA Simulation — Removing Role Clears Violation
- **Steps:** POST /ara/simulate {user_id: ALICE.J, remove_role: Z_FI_PAYMENT_APPROVER}
- **Expected:** simulation result shows 0 violations (SOD-FI-001 cleared); existing DB violations not affected

---

## J10 — Process Controls

### TC-J10-001: Create Process Control
- **Persona:** P10 | **Steps:** POST /process-control/controls {name: AP Invoice Approval, control_type: preventive}
- **Expected:** 201; control_id returned

### TC-J10-002: Schedule Control Test
- **Persona:** P10 | **Steps:** POST /process-control/tests {control_id: …, test_date: …}
- **Expected:** 201; test scheduled

### TC-J10-003: Fail Test → Raise Deficiency
- **Persona:** P10 | **Steps:** POST test result {result: fail} → POST deficiency {severity: significant}
- **Expected:** deficiency created; notification to P14 (Process Owner) — Mailpit

### TC-J10-004: Deficiency Remediation
- **Persona:** P14 | **Steps:** PUT /process-control/deficiencies/{id} {status: remediated, evidence: URL}
- **Expected:** status → remediated; audit log entry

### TC-J10-005: SOX Control Owner Cannot Delete Control (SOX immutability)
- **Persona:** P10 | **Steps:** DELETE /process-control/controls/{id}
- **Expected:** 405 or 403 (controls are not deleted, only deprecated)

---

## J11 — TPRM Vendor Assessment

### TC-J11-001: Onboard New Vendor
- **Persona:** P20 | **Steps:** POST /tprm/vendors {name: Acme Corp, tier: 1}
- **Expected:** 201; vendor_id returned

### TC-J11-002: Issue Questionnaire
- **Persona:** P20 | **Steps:** POST /tprm/assessments {vendor_id: …, questionnaire_id: SURV-TPRM-001}
- **Expected:** assessment created; questionnaire link emailed to vendor contact (Mailpit)

### TC-J11-003: Score Vendor After Response
- **Persona:** P20 | **Steps:** POST /tprm/assessments/{id}/submit {responses: {s1q1: yes, …}}
- **Expected:** score calculated; risk_rating assigned (Low/Medium/High/Critical)

### TC-J11-004: Vendor Manager (P20) Cannot Access SoD Rules
- **Persona:** P20 | **Steps:** GET /risk/rules | **Expected:** 403

---

## J12 — Reports: All 101

Each report case (TC-RPT-001 through TC-RPT-101) follows this template:

**Standard assertions for every report:**
1. `GET /reports/{endpoint}` with at least one filter param → HTTP 200
2. Response body has `data` array with length > 0 (fixtures seeded)
3. `GET /reports/{endpoint}?format=csv` → 200, Content-Type: text/csv, non-empty body
4. `GET /reports/{endpoint}?format=xlsx` → 200, Content-Type: application/vnd.openxmlformats, non-empty body
5. `GET /reports/{endpoint}?format=pdf` → 200, Content-Type: application/pdf, non-empty body
6. P09 (External Auditor) can access reports → 200
7. P08 (Business User) cannot access restricted reports → 403 where applicable

**Scheduled delivery (one per module — 14 schedule cases):**

| TC | Module | Report Scheduled | Verified via |
|---|---|---|---|
| TC-J12-SCHED-01 | SoD/ARA | TC-RPT-001 | Mailpit — subject + CSV attachment |
| TC-J12-SCHED-02 | ARM | TC-RPT-018 | Mailpit |
| TC-J12-SCHED-03 | EAM | TC-RPT-024 | Mailpit |
| TC-J12-SCHED-04 | Certification | TC-RPT-032 | Mailpit |
| TC-J12-SCHED-05 | JML | TC-RPT-040 | Mailpit |
| TC-J12-SCHED-06 | BRM | TC-RPT-048 | Mailpit |
| TC-J12-SCHED-07 | Risk Management | TC-RPT-055 | Mailpit |
| TC-J12-SCHED-08 | Process Control | TC-RPT-066 | Mailpit |
| TC-J12-SCHED-09 | Audit | TC-RPT-074 | Mailpit |
| TC-J12-SCHED-10 | Compliance | TC-RPT-080 | Mailpit |
| TC-J12-SCHED-11 | TPRM | TC-RPT-084 | Mailpit |
| TC-J12-SCHED-12 | BCM | TC-RPT-090 | Mailpit |
| TC-J12-SCHED-13 | Fraud | TC-RPT-094 | Mailpit |
| TC-J12-SCHED-14 | Library | TC-RPT-101 | Mailpit |

Full per-report assertions are parametrized in `e2e/reports.spec.ts` and `tests/test_reports.py`.

---

## J13 — RBAC Enforcement Matrix — All 22 Personas

For each persona: verify nav-allowed (200) and nav-denied (403).
Full matrix is in `e2e/rbac.spec.ts` parametrized over personas.json.
Key spot-checks:

| TC | Persona | Action | Expected |
|---|---|---|---|
| TC-J13-001 | P16 Viewer | GET /dashboard | 200 |
| TC-J13-002 | P16 Viewer | POST /access-requests/submit | 403 |
| TC-J13-003 | P09 Ext Auditor | GET /certifications/campaigns | 200 |
| TC-J13-004 | P09 Ext Auditor | POST /certifications/campaigns | 403 |
| TC-J13-005 | P08 Business User | GET /risk/rules | 403 |
| TC-J13-006 | P08 Business User | POST /access-requests/submit | 200 (201) |
| TC-J13-007 | P12 FF Controller | POST /firefighter/sessions/{id}/review | 200 |
| TC-J13-008 | P08 Business User | POST /firefighter/sessions/{id}/review | 403 |
| TC-J13-009 | P02 Tenant Admin | GET /platform/tenants | 403 |
| TC-J13-010 | P01 Platform Admin | GET /platform/tenants | 200 |
| TC-J13-011 | P01 Platform Admin | Access qa-tenant-002 resource | 200 + audit log entry (escalation) |
| TC-J13-012 | P15 IT Ops | POST /settings/mass-admin | 403 |
| TC-J13-013 | P06 IT Security | POST /risk/rules | 200 (201) |
| TC-J13-014 | P04 Compliance | GET /certifications/campaigns | 200 |
| TC-J13-015 | P04 Compliance | DELETE /users/{id} | 403 |
| TC-J13-016 | P05 Risk Manager | POST /risk-management/risks | 200 (201) |
| TC-J13-017 | P17 FF User | POST /firefighter/sessions/{id}/review | 403 |
| TC-J13-018 | P17 FF User | POST /firefighter/sessions/request | 200 (201) |
| TC-J13-019 | P18 Mit Monitor | GET /ara/mitigations | 200 |
| TC-J13-020 | P18 Mit Monitor | POST /risk/rules | 403 |
| TC-J13-021 | P19 Int Auditor | POST /audit-management/programs | 200 (201) |
| TC-J13-022 | P19 Int Auditor | POST /settings/mass-admin | 403 |
| TC-J13-023 | P20 Vendor Mgr | POST /tprm/vendors | 200 (201) |
| TC-J13-024 | P20 Vendor Mgr | GET /risk/rules | 403 |
| TC-J13-025 | P21 Role Owner | POST /access-requests/{own-role}/approve | 200 |
| TC-J13-026 | P21 Role Owner | POST /access-requests/{other-role}/approve | 403 |
| TC-J13-027 | P22 Risk Owner | PUT /risk-management/risks/{own-id} | 200 |
| TC-J13-028 | P22 Risk Owner | PUT /risk-management/risks/{other-id} | 403 |
| TC-J13-029 | P11 FF Owner | GET /eam/ids/{own-id} | 200 |
| TC-J13-030 | P11 FF Owner | GET /eam/ids/{other-id} | 403 |
| TC-J13-031 | P13 HR Manager | POST /jml/events | 200 (201) |
| TC-J13-032 | P13 HR Manager | GET /risk/rules | 403 |

---

## J14 — Notifications & Audit Log

### TC-J14-001: Access Approved Email Body
- **Trigger:** TC-J02-003 | **Steps:** GET Mailpit messages
- **Expected:** subject matches "Has Been Approved"; body contains role name and effective_date

### TC-J14-002: SoD Violation Alert Email Body
- **Trigger:** TC-J03-001 | **Steps:** GET Mailpit messages
- **Expected:** subject matches "SoD Violation Detected"; body contains user_name and conflict_name

### TC-J14-003: Campaign Open Email Body
- **Trigger:** TC-J05-001 | **Steps:** GET Mailpit messages
- **Expected:** reviewer receives email; body contains campaign_name, item_count, campaign_deadline

### TC-J14-004: FF Session Alert Email Body
- **Trigger:** TC-J04-001 | **Steps:** GET Mailpit messages
- **Expected:** controller receives email; body contains ff_id, user_name, reason_code, incident_ticket

### TC-J14-005: Every Write Produces Audit Record
- **Steps:** POST any resource → GET /audit/logs → filter by resource_id
- **Expected:** audit entry with user_id, tenant_id, action, resource_type, timestamp

### TC-J14-006: Audit Log Delete Returns 405
- **Persona:** P01 | **Steps:** DELETE /audit/logs/{id}
- **Expected:** 405 Method Not Allowed

### TC-J14-007: Audit Log Cannot Be Modified
- **Persona:** P01 | **Steps:** PUT /audit/logs/{id} {action: REDACTED}
- **Expected:** 405 or 403

---

## J15 — Config Effects

### TC-J15-001: Add ARM Workflow Stage → Next Request Routes Through It
- **Persona:** P02
- **Steps:**
  1. GET current ARM workflow config; note current stages
  2. PUT /settings/org-rules/arm-workflow {stages: add new_stage at end}
  3. P08 submits new access request
  4. Track request status through stages
- **Expected:** request reaches new_stage; no restart required

### TC-J15-002: Change SLA Timer → Timers Reflect New Value
- **Persona:** P02
- **Steps:**
  1. PUT /settings/org-rules {arm_approval_sla_hours: 1}
  2. Create new access request
  3. GET request; check sla_deadline field
- **Expected:** sla_deadline = now + 1 hour (not old default 48h)

### TC-J15-003: Flip RBAC Grant → Access Changes Without Restart
- **Persona:** P02
- **Steps:**
  1. Verify P16 cannot POST /access-requests/submit (403)
  2. PUT /settings/org-rules/rbac {role: read_only, grant: access_request_submit}
  3. P16 retries POST /access-requests/submit
- **Expected:** 201 (access granted) — no service restart

### TC-J15-004: Edit Notification Template → Mailpit Shows New Body
- **Persona:** P02
- **Steps:**
  1. PUT /library/activations/{NOTIF-ARM-REQUEST-activation-id} {copy_payload: {subject: CUSTOM SUBJECT TEST}}
  2. P08 submits new access request
  3. GET Mailpit messages
- **Expected:** email subject = "CUSTOM SUBJECT TEST" (tenant copy used, not global template)

---

## J16 — Admin & Connectors

### TC-J16-001: Add Demo SAP Connector
- **Persona:** P02 | **Steps:** POST /settings/connectors {type: sap, host: sap_mock, port: 1080, client: 100, username: RFC_USER, password: …}
- **Expected:** 201; connector_id returned; status = pending_test

### TC-J16-002: Test Connection → Success
- **Persona:** P02 | **Steps:** POST /settings/connectors/{id}/test
- **Expected:** {status: connected, latency_ms: >0}; SAP mock GET /sap/bc/ping was called

### TC-J16-003: Run Sync → Record Counts Match Mock Fixtures
- **Persona:** P02 | **Steps:** POST /settings/connectors/{id}/sync
- **Expected:** sync result {users_imported: 6, roles_imported: 4, errors: 0}; counts match mock data

### TC-J16-004: Job Scheduler Run-Now → History Entry
- **Persona:** P02 | **Steps:** POST /settings/connectors/{id}/jobs/sync/run-now
- **Expected:** job kicked off; GET /settings/connectors/{id}/jobs/history shows entry with status: completed + record counts

### TC-J16-005: Sync Counts Consistent with Mock
- **Steps:** After sync, GET /users?source_system=SAP → count matches mock UserSet response

---

## J17 — BRM Role Lifecycle

### TC-J17-001: Open Role Designer Stepper
- **Persona:** P06 | **Steps:** POST /role-management/designs {name: Z_QA_FI_ANALYST}
- **Expected:** 201; design_id returned; status = draft

### TC-J17-002: Design-Time Risk Check (Step 3)
- **Persona:** P06 | **Steps:** POST /role-management/designs/{id}/check-risk
- **Expected:** SoD pre-check returns list of potential conflicts for the tcodes/auth-objects defined

### TC-J17-003: Submit for Approval → P03 (CISO) Approves
- **Persona:** P06 → P03
- **Steps:** POST /role-management/designs/{id}/submit → P03: POST approve
- **Expected:** design.status → approved; approval email to P03 (Mailpit)

### TC-J17-004: Approved Role Generated in SAP (Mock)
- **Steps:** POST /role-management/designs/{id}/generate
- **Expected:** SAP mock POST /sap/opu/odata/sap/SUSR_USER_ADDR_SRV/RoleSet called; role_name in response

### TC-J17-005: Role Comparison Diff
- **Persona:** P06 | **Steps:** GET /role-management/comparison?role_a=Z_FI_AP_CLERK&role_b=Z_QA_FI_ANALYST
- **Expected:** diff object with added/removed auth objects listed

### TC-J17-006: Role Mining Renders
- **Persona:** P06 | **Steps:** GET /role-management/mining?department=Finance
- **Expected:** 200; mining_candidates list with suggested roles based on user-access patterns

---

## J18 — Extended Modules

### TC-J18-001: Whistleblower Anonymous Intake (No Auth)
- **Steps:** POST /whistleblower/intake {description: Suspicious vendor payment, category: fraud} — NO auth header
- **Expected:** 201; tracking_token in response; no user identity recorded

### TC-J18-002: Whistleblower Token Follow-Up (No Auth)
- **Steps:** GET /whistleblower/track/{tracking_token} — NO auth header
- **Expected:** 200; shows submission status and any internal response; reporter identity still anonymous

### TC-J18-003: Internal Auditor (P19) Works Whistleblower Inbox
- **Persona:** P19 | **Steps:** GET /whistleblower (inbox) → POST note → POST close-case
- **Expected:** inbox visible; note recorded; case status → closed

### TC-J18-004: Business User (P08) Cannot Access Whistleblower Inbox
- **Persona:** P08 | **Steps:** GET /whistleblower
- **Expected:** 403

### TC-J18-005: Whistleblower Intake Anonymous — Cannot Retrieve Without Token
- **Steps:** GET /whistleblower/track/INVALID-TOKEN
- **Expected:** 404 — no information leakage

### TC-J18-006: BCM BIA Creation and RTO/RPO
- **Persona:** P05 | **Steps:** POST /bcm/bia {asset: SAP ERP, rto_hours: 4, rpo_hours: 24}
- **Expected:** 201; BIA created; RTO and RPO stored

### TC-J18-007: BCM Plan Test
- **Persona:** P05 | **Steps:** POST /bcm/testing {plan_id: …, test_date: …} → POST result {outcome: pass}
- **Expected:** test recorded; plan.last_tested updated; TC-RPT-091 reflects result

### TC-J18-008: Fraud Rule Creates Alert
- **Persona:** P05 | **Steps:** POST /fraud/rules {name: AP > $10K no PO, threshold: 10000}
         → trigger rule evaluation (POST /fraud/evaluate or via transaction import)
- **Expected:** fraud alert created for matching transaction

### TC-J18-009: Fraud Alert Escalated to Case
- **Persona:** P05 | **Steps:** POST /fraud/alerts/{id}/escalate
- **Expected:** fraud case created; case_id returned; alert.status → escalated

### TC-J18-010: Survey Created and Distributed
- **Persona:** P04 | **Steps:** POST /surveys {name: Control Self-Assessment Q4, questions: [...]}
          → POST /surveys/{id}/distribute {audience: Finance}
- **Expected:** survey created; distribution task created; email to Finance group (Mailpit)

### TC-J18-011: Survey Logic Branching
- **Steps:** Survey has branch: if s1q1 = No → show s1q1_followup
          Submit response with s1q1 = No
- **Expected:** s1q1_followup appears in response data; skipped if s1q1 = Yes

---

## Page Sweep Cases (TC-PAGE-001 through TC-PAGE-018)

These are parametrized Playwright tests in `e2e/page_sweep.spec.ts`.
Each TC-PAGE case visits the page as the allowed persona and:
1. Confirms HTTP 200 / no crash
2. Confirms at least one data item loads (not empty state — requires fixture data)
3. Confirms denied persona receives 403 or redirect to unauthorized

| TC | Page Group | Personas Tested |
|---|---|---|
| TC-PAGE-001 | Dashboard | All 22 |
| TC-PAGE-002 | ARA dashboard | P03, P04, P06 |
| TC-PAGE-003 | ARA violations | P03, P04, P06; P08 → 403 |
| TC-PAGE-004 | Mitigations | P18, P06; P08 → 403 |
| TC-PAGE-005 | SoD rules | P06; P08 → 403 |
| TC-PAGE-006 | Entitlements/Contextual | P03, P06 |
| TC-PAGE-007 | Access requests | P08 submit; P07 approve; P21 role-owner approve |
| TC-PAGE-008 | EAM / FF | P11, P12, P17; P08 → 403 for controller view |
| TC-PAGE-009 | Certification | P04, P07, P09(read); P08 → 403 for campaigns |
| TC-PAGE-010 | JML | P13; P08 → 403 |
| TC-PAGE-011 | BRM | P06; P08 → 403 |
| TC-PAGE-012 | Risk management | P05, P22; P08 → 403 |
| TC-PAGE-013 | Process control | P10, P14; P08 → 403 for create |
| TC-PAGE-014 | Audit management | P19; P09 (read-only) |
| TC-PAGE-015 | Compliance | P04, P10; P08 → 403 |
| TC-PAGE-016 | TPRM | P20, P05; P08 → 403 |
| TC-PAGE-017 | Reports catalog | P09, P05, P04; P08 limited |
| TC-PAGE-018 | Settings / mass-admin | P02; P08, P15, P16 → 403 for mass-admin |
