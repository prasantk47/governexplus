# GovernexPlus — User Acceptance Test Script

**Version:** 1.0
**Date:** 2026-10-05
**Product:** GovernexPlus v1.0-RC
**Environment:** QA stack (docker-compose.qa.yml)
**Tenant:** qa-tenant-001

> This document is the **customer-facing UAT pack**. Automation specs reference it
> but never rewrite it. If code and script disagree, that is a defect in the product,
> not in this script.

---

## Persona Mapping

| ID | Role | Username | Used In |
|----|------|----------|---------|
| P01 | Platform Admin | qa_platform_admin | UAT-01, UAT-26, UAT-27 |
| P02 | Tenant Admin | qa_tenant_admin | UAT-02, UAT-03, UAT-26, UAT-27 |
| P03 | CISO | qa_ciso | UAT-12, UAT-19 |
| P04 | Compliance Officer | qa_compliance | UAT-09, UAT-13 |
| P05 | Risk Manager | qa_risk_manager | UAT-11, UAT-20 |
| P06 | IT Security Admin | qa_it_security | UAT-06, UAT-10, UAT-17 |
| P07 | Line Manager | qa_line_manager | UAT-05, UAT-15 |
| P08 | Business User | qa_requestor | UAT-04, UAT-05, UAT-22 |
| P09 | External Auditor | qa_ext_auditor | UAT-13 |
| P10 | SOX Control Owner | qa_sox_owner | UAT-14 |
| P11 | Firefighter Owner | qa_ff_owner | UAT-17, UAT-18 |
| P12 | Firefighter Controller | qa_ff_controller | UAT-17 |
| P13 | HR Manager | qa_hr_manager | UAT-15, UAT-16 |
| P14 | Process Owner | qa_process_owner | UAT-14 |
| P17 | Firefighter (Session User) | qa_firefighter | UAT-18 |
| P19 | Internal Auditor | qa_int_auditor | UAT-13, UAT-19 |
| P20 | Vendor Manager | qa_vendor_manager | UAT-20 |
| P21 | Role Owner | qa_role_owner | UAT-07, UAT-08 |

---

## Priority Key

| Tag | Meaning | Gate Rule |
|-----|---------|-----------|
| **@P0** | Core journey — must pass for release | All P0 PASS required for sign-off |
| **@P1** | Important but deferrable | Failures accepted in writing by product owner |

---

## Group A — Authentication & Navigation

### UAT-01 · Login & Session Management · @P0

**Persona:** P08 (Business User)
**Pre-condition:** User `qa_requestor` exists with password `QaP@ss2026!Request`

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Navigate to `/login` | Login page renders with GovernexPlus branding, username and password fields visible |
| 2 | Enter valid username `qa_requestor` and password `QaP@ss2026!Request`, click **Sign In** | Redirect to `/dashboard`, welcome message shows "Robert Requestor" |
| 3 | Refresh the page (F5) | Dashboard reloads — session persists, no redirect to login |
| 4 | Open browser dev-tools → Application → Local Storage | JWT token present under auth key |
| 5 | Click user avatar / profile menu → **Sign Out** | Redirect to `/login`, JWT cleared from storage |
| 6 | Navigate directly to `/dashboard` while logged out | Redirect to `/login` — unauthenticated access blocked |
| 7 | Enter invalid password `WrongPass!`, click **Sign In** | Error toast: "Invalid credentials" — no redirect |
| 8 | Attempt login 6 times with wrong password | Account lockout message after configured threshold |

---

### UAT-02 · Dashboard & Navigation · @P0

**Persona:** P02 (Tenant Admin)
**Pre-condition:** Logged in as `qa_tenant_admin`

| Step | Action | → Expected |
|------|--------|------------|
| 1 | View dashboard after login | Dashboard loads with stat cards: Total Users, Active Risks, Open Requests, Pending Reviews |
| 2 | Verify sidebar navigation is visible | Left sidebar shows module groups: Dashboard, Access Governance, Risk & Compliance, Identity, Emergency Access, Extended Modules, Reports, Settings |
| 3 | Click each top-level sidebar item | Each page loads without error (no blank page, no 500) |
| 4 | Toggle dark mode via theme switcher | UI switches to dark theme — backgrounds change to navy/slate, text remains readable |
| 5 | Toggle back to light mode | UI returns to light theme — no visual glitches |
| 6 | Resize browser to mobile width (375px) | Sidebar collapses to hamburger menu, content remains accessible |
| 7 | Open hamburger menu on mobile | Navigation drawer slides in, all items visible |

---

### UAT-03 · User Management (CRUD) · @P0

**Persona:** P02 (Tenant Admin)
**Pre-condition:** Logged in as `qa_tenant_admin`

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Navigate to **Settings → Users** | User list table loads showing existing QA personas |
| 2 | Click **Create User** button | Create user modal/form opens with fields: Username, Full Name, Email, Department, Roles |
| 3 | Fill form: username=`uat_test_user`, full_name=`UAT Test User`, email=`uat@test.com`, department=`QA`, role=`business_user`. Click **Save** | Success toast "User created", user appears in table |
| 4 | Search for `uat_test_user` in search box | Table filters to show only the new user |
| 5 | Click the new user row → click **Edit** | Edit form opens pre-populated with user's data |
| 6 | Change department to `Engineering`, click **Save** | Success toast "User updated", table reflects new department |
| 7 | Click **Deactivate** / toggle active status on the user | User status changes to inactive, visual indicator updates |

---

## Group B — Access Request Lifecycle

### UAT-04 · Submit Access Request · @P0

**Persona:** P08 (Business User)
**Pre-condition:** Logged in as `qa_requestor`; at least one requestable role exists

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Navigate to **Access Governance → Request Access** | Access request page loads with role catalog / search |
| 2 | Search or browse available roles | Role list displays with name, description, risk level |
| 3 | Select role `ROLE_FI_VIEWER`, click **Add to Cart** | Role added to shopping cart, cart badge increments |
| 4 | Open cart / review selected roles | Cart shows `ROLE_FI_VIEWER` with remove option |
| 5 | Enter business justification: "Need read access to financial reports for quarterly audit" | Justification text accepted |
| 6 | Click **Submit Request** | Success toast "Access request submitted", request ID displayed (e.g., `AR-xxxx`) |
| 7 | Navigate to **My Requests** | New request visible with status "Pending Approval" |

---

### UAT-05 · Approve Access Request · @P0

**Persona:** P07 (Line Manager)
**Pre-condition:** UAT-04 completed — pending request from `qa_requestor` exists

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_line_manager` | Dashboard shows pending approval count > 0 |
| 2 | Navigate to **Access Governance → Pending Approvals** | List of pending requests visible, includes request from UAT-04 |
| 3 | Click the request from `Robert Requestor` | Request detail view: requested role, justification, risk preview |
| 4 | Review the SoD risk preview section | Risk analysis shows whether the requested role creates SoD conflicts |
| 5 | Click **Approve** | Success toast "Request approved", request status changes to "Approved" |
| 6 | **(Verify as P08)** Log back in as `qa_requestor`, check **My Requests** | Request status shows "Approved" |

---

### UAT-06 · Access Request with SoD Violation · @P0

**Persona:** P08 (Business User) then P06 (IT Security Admin)
**Pre-condition:** SoD rule exists that conflicts with a requestable role

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_requestor` | Dashboard loads |
| 2 | Navigate to **Request Access** | Role catalog loads |
| 3 | Select a role that triggers an SoD conflict (e.g., `ROLE_FI_POSTER` when user already has `ROLE_FI_VIEWER` and an SoD rule covers this pair) | SoD warning displayed before/during submission |
| 4 | Submit the request despite warning (if allowed) or note the block | Request either submitted with risk flag or blocked with explanation |
| 5 | **(As P06)** Log in as `qa_it_security`, navigate to **Risk → SoD Violations** | Violation logged for the conflicting request |
| 6 | View violation details | Shows: user, conflicting roles/tcodes, rule ID, severity |

---

### UAT-07 · Role Engineering — Pack Builder · @P1

**Persona:** P21 (Role Owner)
**Pre-condition:** Role Studio module accessible; at least one role exists

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_role_owner` | Dashboard loads |
| 2 | Navigate to **Role Studio → Pack Builder** | Pack Builder page loads with existing packs (if any) |
| 3 | Click **Create Pack** | Pack creation form opens |
| 4 | Enter pack name "Q4 Finance Roles", add roles `ROLE_FI_VIEWER`, `ROLE_FI_POSTER` | Roles added to pack |
| 5 | Click **Save Pack** | Pack saved, version `v1` created |
| 6 | Click **New Version** on the saved pack | Version incremented to `v2`, editable copy created |
| 7 | Add role `ROLE_FI_APPROVER` to v2, click **Save** | Pack v2 saved with 3 roles |
| 8 | Run **Risk Check** on the pack | SoD analysis runs, results displayed (conflicts if any) |

---

### UAT-08 · Role Mining · @P1

**Persona:** P21 (Role Owner)
**Pre-condition:** Usage/assignment data available for mining

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Navigate to **Role Studio → Role Mining** | Role mining page loads |
| 2 | Configure mining parameters: min users = 3, similarity threshold = 70% | Parameters accepted |
| 3 | Click **Run Mining** | Mining job starts, progress indicator shown |
| 4 | Wait for results | Mining results displayed: suggested role clusters with member users and common permissions |
| 5 | Select a suggested cluster, click **Create Role from Cluster** | Role creation form pre-populated with mined permissions |
| 6 | Save the new role | Role created, visible in role catalog |

---

## Group C — Risk & Compliance

### UAT-09 · Certification Campaign · @P0

**Persona:** P04 (Compliance Officer)
**Pre-condition:** Users with role assignments exist for review

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_compliance` | Dashboard loads |
| 2 | Navigate to **Compliance → Certifications** | Certification campaigns list loads |
| 3 | Click **Create Campaign** | Campaign creation form opens |
| 4 | Fill: name="Q4 Access Review", type="User Access Review", scope="All Users", reviewers=`qa_line_manager` | Form accepts all fields |
| 5 | Click **Launch Campaign** | Success toast, campaign appears in list with status "Active" |
| 6 | **(As P07)** Log in as `qa_line_manager`, navigate to **My Reviews** | Review items visible for the launched campaign |
| 7 | Open a review item — user access details shown | User's current roles, last login, risk level displayed |
| 8 | Click **Certify** (approve) on the item | Item marked as certified, visual checkmark |
| 9 | Click **Revoke** on another item, provide reason | Item marked for revocation, reason recorded |
| 10 | **(As P04)** Return to campaign dashboard | Progress bar shows completed reviews, status summary |

---

### UAT-10 · SoD Rule Management · @P0

**Persona:** P06 (IT Security Admin)
**Pre-condition:** SoD ruleset loaded

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_it_security` | Dashboard loads |
| 2 | Navigate to **Risk → SoD Rules** | SoD rule list loads with existing rules from ruleset library |
| 3 | Verify rule count > 100 | Table shows 120+ rules across modules (FI, MM, SD, HR, etc.) |
| 4 | Search for rules containing "FI" | Filter works, showing Finance-related SoD rules |
| 5 | Click a rule to view details | Rule detail: ID, description, conflicting actions/tcodes, risk level, module |
| 6 | Click **Create Rule** | Rule creation form opens |
| 7 | Fill: name="Custom Test Rule", function1="ZFI_CUSTOM_01", function2="ZFI_CUSTOM_02", risk_level="High" | Form accepts custom rule |
| 8 | Save the rule | Rule appears in list, marked as custom |

---

### UAT-11 · Access Risk Analysis (ARA) · @P0

**Persona:** P05 (Risk Manager)
**Pre-condition:** Users with role assignments exist; SoD rules loaded

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_risk_manager` | Dashboard loads |
| 2 | Navigate to **Risk → Access Risk Analysis** | ARA page loads |
| 3 | Select analysis scope: "All Users" or specific user | Scope selector works |
| 4 | Click **Run Analysis** | Analysis executes, progress shown |
| 5 | View results | Violations listed: user, rule violated, conflicting roles, severity |
| 6 | Click a violation row | Detail view: full rule description, affected transactions, mitigation options |
| 7 | Verify violations are persisted | Navigate away and back — violations still present (DB-backed) |

---

### UAT-12 · Security Controls · @P1

**Persona:** P03 (CISO)
**Pre-condition:** Logged in as `qa_ciso`

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Navigate to **Compliance → Security Controls** | Security controls list loads |
| 2 | Click **Create Control** | Control creation form opens |
| 3 | Fill: control_name="Password Complexity Policy", business_area="IT General", control_type="Preventive", category="Access Control", description="Enforce minimum 12-char passwords with complexity requirements" | Form accepts all fields |
| 4 | Click **Save** | Control created, appears in list |
| 5 | Click the control → **Edit** | Edit form opens with pre-populated data |
| 6 | Add test evidence / update status to "Effective" | Changes saved |
| 7 | View control in list | Status badge shows "Effective" |

---

### UAT-13 · Audit Management · @P1

**Persona:** P19 (Internal Auditor)
**Pre-condition:** Logged in as `qa_int_auditor`

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Navigate to **Compliance → Audit Management** | Audit list page loads |
| 2 | Click **Create Audit** | Audit creation form opens |
| 3 | Fill: title="Q4 SOX Compliance Audit", audit_type="SOX", scope="Finance Controls", lead_auditor=`qa_int_auditor` | Form accepts all fields |
| 4 | Click **Save** | Audit created with status "Planning" |
| 5 | Open the audit → add a finding | Finding form: title, description, severity, recommendation |
| 6 | Save finding | Finding attached to audit, visible in findings tab |
| 7 | **(As P09)** Log in as `qa_ext_auditor` | Dashboard loads (read-only view) |
| 8 | Navigate to Audit Management | Audit visible in read-only mode |
| 9 | Attempt to create/edit audit | Action blocked or button not visible — read-only enforced |

---

## Group D — Identity & Lifecycle

### UAT-14 · Process Control · @P1

**Persona:** P14 (Process Owner), P10 (SOX Control Owner)
**Pre-condition:** Logged in as `qa_process_owner`

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Navigate to **Compliance → Process Control** | Process control page loads |
| 2 | Click **Create Process** | Process creation form opens |
| 3 | Fill: name="Procure to Pay", owner=`qa_process_owner`, description="End-to-end procurement process" | Form accepts |
| 4 | Save process | Process created, visible in list |
| 5 | Add a sub-process: "Purchase Order Creation" | Sub-process linked to parent |
| 6 | **(As P10)** Log in as `qa_sox_owner`, navigate to process | Process visible |
| 7 | Link a control to the sub-process | Control-to-process mapping saved |
| 8 | Run a control test | Test execution recorded with pass/fail result |

---

### UAT-15 · Joiner-Mover-Leaver (JML) · @P0

**Persona:** P13 (HR Manager), P07 (Line Manager)
**Pre-condition:** JML policies exist for joiner/mover/leaver events; HR transfer/termination test data seeded

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_hr_manager` | Dashboard loads |
| 2 | Navigate to **Identity → JML Policies** | JML policies list loads |
| 3 | Click **Create Policy** | Policy creation form opens |
| 4 | Fill: policy_name="Finance Joiner Provisioning", event_type="joiner", org_unit="Finance", birthright_roles="ROLE_FI_VIEWER, ROLE_HR_SELF_SERVICE" | Form accepts all fields |
| 5 | Click **Create Policy** (submit) | Policy created, visible in list with "Joiner" badge |
| 6 | Navigate to **JML Events** (if available) or trigger via API | Event list loads |
| 7 | Create/trigger a joiner event for a new user in Finance | Event processed, birthright roles auto-assigned per policy |
| 8 | Create a mover event (department transfer) | Previous department roles queued for removal, new department roles queued for grant |
| 9 | Create a leaver event (termination) | All access queued for revocation, account marked for deactivation |
| 10 | **(As P07)** Log in as `qa_line_manager`, verify JML dashboard | JML events visible, approval items for direct reports |

---

### UAT-16 · Identity Correlation · @P1

**Persona:** P13 (HR Manager)
**Pre-condition:** Multiple identity sources configured (or mocked)

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_hr_manager` | Dashboard loads |
| 2 | Navigate to **Identity → Identity Correlation** | Identity correlation page loads with overview stats |
| 3 | View correlation overview | Stats show: total identities, correlated, orphaned, conflicting |
| 4 | Click **Run Correlation** (if available) | Correlation engine runs, matches identities across sources |
| 5 | View orphan accounts | List of accounts with no HR record match |
| 6 | View conflicts | List of accounts with conflicting attributes across sources |
| 7 | Select an orphan → **Link to HR Record** (manual correlation) | Account linked, removed from orphan list |

---

## Group E — Emergency Access & Monitoring

### UAT-17 · Firefighter Access — Request & Approval · @P0

**Persona:** P06 (IT Security Admin), P11 (FF Owner), P12 (FF Controller)
**Pre-condition:** Firefighter IDs configured; FF Owner and Controller assigned

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_it_security` | Dashboard loads |
| 2 | Navigate to **Emergency Access → Firefighter IDs** | FF ID list loads showing configured emergency accounts |
| 3 | Click **Request Emergency Access** | Request form opens: select FF ID, enter reason, expected duration |
| 4 | Fill: FF ID=any available, reason="Production issue P1-4532 — need SAP_ALL to debug posting error", duration="2 hours" | Form accepts |
| 5 | Submit request | Request created with status "Pending Approval" |
| 6 | **(As P11)** Log in as `qa_ff_owner`, navigate to **FF Approvals** | Pending FF request visible |
| 7 | Review request details: requester, reason, requested FF ID | All details displayed correctly |
| 8 | Click **Approve** | Request approved, status changes |
| 9 | **(As P12)** Log in as `qa_ff_controller` | FF controller dashboard shows active session alert |

---

### UAT-18 · Firefighter Session & Logging · @P0

**Persona:** P17 (Firefighter Session User), P11 (FF Owner)
**Pre-condition:** UAT-17 completed — approved FF access exists; guaranteed CCM exception seeded

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_firefighter` | Dashboard loads |
| 2 | Navigate to **Emergency Access → Active Sessions** | Active FF session visible (from UAT-17 approval) |
| 3 | Start the firefighter session (check-in) | Session timer starts, activity logging begins |
| 4 | Perform an action during the session (e.g., view a restricted page) | Action logged in FF session log |
| 5 | End the firefighter session (check-out) | Session closed, duration recorded |
| 6 | **(As P11)** Log in as `qa_ff_owner`, navigate to **FF Session Logs** | Completed session visible with full activity log |
| 7 | View session log details | All actions during the session are recorded with timestamps |
| 8 | Verify CCM exception is flagged | CCM exception for the FF session appears in monitoring |

---

### UAT-19 · Continuous Controls Monitoring (CCM) · @P1

**Persona:** P03 (CISO), P19 (Internal Auditor)
**Pre-condition:** CCM rules configured; monitoring data available

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_ciso` | Dashboard loads |
| 2 | Navigate to **Risk → Controls Monitoring** | CCM dashboard loads with monitoring status |
| 3 | View active monitors | List of configured monitors with last-run timestamp and status |
| 4 | Click a monitor to view details | Monitor config: rule, schedule, threshold, last results |
| 5 | View exceptions/alerts | List of detected exceptions with severity and affected entities |
| 6 | **(As P19)** Log in as `qa_int_auditor` | Dashboard loads |
| 7 | Navigate to CCM → view exceptions | Same exceptions visible for audit review |
| 8 | Mark an exception as "Reviewed" / "Accepted Risk" | Exception status updated |

---

## Group F — Extended Modules

### UAT-20 · Third-Party Risk Management (TPRM) · @P1

**Persona:** P20 (Vendor Manager), P05 (Risk Manager)
**Pre-condition:** Logged in as `qa_vendor_manager`

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Navigate to **Extended → TPRM → Vendors** | Vendor list page loads |
| 2 | Click **Add Vendor** | Vendor creation form opens |
| 3 | Fill: vendor_name="Acme Cloud Services", category="Cloud Provider", risk_tier="High", contact_name="Jane Doe", contact_email="jane@acme.example" | Form accepts |
| 4 | Click **Save** | Vendor created, visible in list with "High" risk badge |
| 5 | Click vendor row → view detail | Vendor detail page: info, assessments tab, issues tab |
| 6 | Click **Start Assessment** | Assessment form: questionnaire-based risk evaluation |
| 7 | Complete assessment with sample answers, submit | Assessment saved with calculated risk score |
| 8 | **(As P05)** Log in as `qa_risk_manager`, navigate to TPRM | Vendor risk overview visible with risk scores |

---

### UAT-21 · Business Continuity Management (BCM) · @P1

**Persona:** P05 (Risk Manager)
**Pre-condition:** Logged in as `qa_risk_manager`

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Navigate to **Extended → BCM → Plans** | BCP list loads |
| 2 | Click **Create Plan** | Plan creation form opens |
| 3 | Fill: plan_name="IT Disaster Recovery", description="DR plan for core IT systems", owner="IT Ops", priority="Critical" | Form accepts |
| 4 | Click **Save** | Plan created, visible in list |
| 5 | Navigate to **BCM → BIA** (Business Impact Analysis) | BIA list loads |
| 6 | Click **Create BIA** | BIA form opens |
| 7 | Fill: process_name="Payment Processing", rto_hours=4, rpo_hours=1, impact_level="Critical" | Form accepts |
| 8 | Save BIA | BIA record created |
| 9 | Navigate to **BCM → Exercises** | Exercise list loads |
| 10 | Create a DR exercise linked to the plan | Exercise created with schedule |

---

### UAT-22 · Surveys · @P1

**Persona:** P08 (Business User — as survey admin/creator via API, respondent via UI)
**Pre-condition:** Survey module accessible

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_tenant_admin` (P02) | Dashboard loads |
| 2 | Navigate to **Extended → Surveys** | Survey list loads |
| 3 | Click **Create Survey** | Survey creation form opens |
| 4 | Fill: title="Security Awareness Assessment", description="Annual security training survey" | Form accepts |
| 5 | Add questions: Q1 (multiple choice), Q2 (text), Q3 (rating) | Questions added to survey |
| 6 | Click **Save** / **Publish** | Survey saved/published |
| 7 | Click **Distribute** — add recipients | Distribution form: select users or groups |
| 8 | Distribute to `qa_requestor` | Distribution confirmed |
| 9 | **(As P08)** Log in as `qa_requestor`, navigate to **My Surveys** | Assigned survey visible |
| 10 | Open survey, answer all questions, submit | Survey response submitted, confirmation shown |
| 11 | **(As P02)** View survey results | Response summary with statistics |

---

### UAT-23 · Fraud Detection · @P0

**Persona:** P06 (IT Security Admin)
**Pre-condition:** Fraud rules configured; guaranteed fraud-rule hit seeded

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_it_security` | Dashboard loads |
| 2 | Navigate to **Extended → Fraud → Rules** | Fraud rule list loads |
| 3 | Click **Create Rule** | Rule creation form opens |
| 4 | Fill: rule_name="Duplicate Payment Detection", rule_type="transaction", conditions="amount > 10000 AND vendor duplicated within 24h", severity="High" | Form accepts |
| 5 | Save rule | Rule created, visible in list |
| 6 | Navigate to **Fraud → Alerts** | Alert list loads (seeded alert from fraud-rule hit visible) |
| 7 | Click an alert to view details | Alert detail: triggered rule, affected transaction, user, timestamp |
| 8 | Click **Open Case** from alert | Case creation form pre-populated from alert |
| 9 | Fill case details, save | Fraud case created with linked alert |
| 10 | Navigate to **Fraud → Cases** | Case visible with status "Open" |
| 11 | Update case: add investigation notes, change status to "Investigating" | Case updated |

---

### UAT-24 · Whistleblower Portal · @P0

**Persona:** Anonymous (public), then P06 (IT Security Admin as investigator)
**Pre-condition:** Whistleblower module accessible; `/whistleblower/submit` is PUBLIC (no auth)

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Navigate to `/whistleblower/submit` (unauthenticated) | Anonymous submission form loads — no login required |
| 2 | Fill: category="fraud", description="Suspected invoice manipulation in AP department", priority="high" | Form accepts |
| 3 | Click **Submit** | Submission accepted, reference code displayed (e.g., `WB-XXXXXXXX`) |
| 4 | Copy the reference code | Code available for tracking |
| 5 | Navigate to `/whistleblower/track` (unauthenticated) | Tracking page loads with reference code input |
| 6 | Enter the reference code from step 3 | Case status displayed: "Open", submission details visible |
| 7 | **(As P06)** Log in as `qa_it_security`, navigate to **Extended → Whistleblower → Cases** | Submitted case visible in case list |
| 8 | Open the case | Full details: category, description, priority, timeline |
| 9 | Add investigator message: "We are reviewing your report. Can you provide the invoice numbers?" | Message saved |
| 10 | Change case status to "Investigating" | Status updated |
| 11 | **(Anonymous)** Return to tracking page, enter reference code | Updated status "Investigating" shown, investigator message visible |
| 12 | Submit anonymous reply: "Invoice numbers: INV-2026-4401, INV-2026-4402" | Reply submitted |
| 13 | **(As P06)** Refresh case | Anonymous reply visible in message thread |

---

### UAT-25 · Reporting & Dashboards · @P1

**Persona:** P02 (Tenant Admin)
**Pre-condition:** Data exists from previous UAT scenarios

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_tenant_admin` | Dashboard loads |
| 2 | Navigate to **Reports** | Report catalog/list loads |
| 3 | Select a report: "SoD Violations Summary" | Report configuration page loads |
| 4 | Set parameters: date range = last 30 days | Parameters accepted |
| 5 | Click **Generate** / **Run** | Report executes, results displayed (table or chart) |
| 6 | Click **Export** → PDF or CSV | File downloads with report data |
| 7 | Navigate to **Dashboard** | Main dashboard with KPI widgets |
| 8 | Verify dashboard widgets show non-zero data | Stat cards reflect data created during UAT (requests, violations, etc.) |

---

## Group G — Platform & Configuration

### UAT-26 · Template Library · @P1

**Persona:** P02 (Tenant Admin)
**Pre-condition:** Template library seeded with day-one content (42 templates)

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Log in as `qa_tenant_admin` | Dashboard loads |
| 2 | Navigate to **Settings → Content Library** | Template library loads with seeded content |
| 3 | Verify template count ≥ 42 | Template packs visible: SoD rules, mitigations, workflows, controls, etc. |
| 4 | Click a template pack to view items | Pack detail shows versioned items with descriptions |
| 5 | Click **Activate** on a template pack | Activation wizard opens — preview items, confirm |
| 6 | Complete activation | Items copied to tenant, success confirmation |
| 7 | Navigate to **Active Content** | Activated items visible with "Active" status |
| 8 | Edit an activated item | Copy-on-write: edit creates tenant-local copy |
| 9 | **(As P01)** Log in as `qa_platform_admin` | Platform admin dashboard |
| 10 | Navigate to library as platform admin | All packs visible across tenants, management options available |

---

### UAT-27 · System Configuration & Effects · @P1

**Persona:** P01 (Platform Admin), P02 (Tenant Admin)
**Pre-condition:** Logged in as `qa_platform_admin`

| Step | Action | → Expected |
|------|--------|------------|
| 1 | Navigate to **Settings → System Configuration** | Config page loads (or API: `GET /config/settings`) |
| 2 | View current settings: session timeout, password policy, rate limits | Settings displayed with current values |
| 3 | Change session timeout to 15 minutes | Setting saved |
| 4 | Change password minimum length to 12 | Setting saved |
| 5 | **(Verify effect)** The next login session should respect the new timeout | Session expires after 15 minutes of inactivity |
| 6 | **(As P02)** Log in as `qa_tenant_admin` | Dashboard loads |
| 7 | Navigate to tenant-level settings | Tenant config page loads |
| 8 | Verify tenant cannot override platform-level security settings | Platform settings shown as read-only or not visible at tenant level |

---

## Results Register

| ID | Scenario | Priority | Result | Date | Evidence Path | Defect |
|----|----------|----------|--------|------|---------------|--------|
| UAT-01 | Login & Session Management | @P0 | | | | |
| UAT-02 | Dashboard & Navigation | @P0 | | | | |
| UAT-03 | User Management (CRUD) | @P0 | | | | |
| UAT-04 | Submit Access Request | @P0 | | | | |
| UAT-05 | Approve Access Request | @P0 | | | | |
| UAT-06 | Access Request with SoD Violation | @P0 | | | | |
| UAT-07 | Role Engineering — Pack Builder | @P1 | | | | |
| UAT-08 | Role Mining | @P1 | | | | |
| UAT-09 | Certification Campaign | @P0 | | | | |
| UAT-10 | SoD Rule Management | @P0 | | | | |
| UAT-11 | Access Risk Analysis (ARA) | @P0 | | | | |
| UAT-12 | Security Controls | @P1 | | | | |
| UAT-13 | Audit Management | @P1 | | | | |
| UAT-14 | Process Control | @P1 | | | | |
| UAT-15 | Joiner-Mover-Leaver (JML) | @P0 | | | | |
| UAT-16 | Identity Correlation | @P1 | | | | |
| UAT-17 | Firefighter Access — Request & Approval | @P0 | | | | |
| UAT-18 | Firefighter Session & Logging | @P0 | | | | |
| UAT-19 | Continuous Controls Monitoring (CCM) | @P1 | | | | |
| UAT-20 | Third-Party Risk Management (TPRM) | @P1 | | | | |
| UAT-21 | Business Continuity Management (BCM) | @P1 | | | | |
| UAT-22 | Surveys | @P1 | | | | |
| UAT-23 | Fraud Detection | @P0 | | | | |
| UAT-24 | Whistleblower Portal | @P0 | | | | |
| UAT-25 | Reporting & Dashboards | @P1 | | | | |
| UAT-26 | Template Library | @P1 | | | | |
| UAT-27 | System Configuration & Effects | @P1 | | | | |

### Summary

- **Total scenarios:** 27
- **P0 scenarios:** 14 (UAT-01–06, 09–11, 15, 17–18, 23–24)
- **P1 scenarios:** 13 (UAT-07–08, 12–14, 16, 19–22, 25–27)
- **P0 pass rate:** ___ / 14
- **P1 pass rate:** ___ / 13
- **Blocked scenarios:** (list with reasons)

### Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | | | |
| QA Lead | | | |
| CISO | | | |
| Project Manager | | | |
