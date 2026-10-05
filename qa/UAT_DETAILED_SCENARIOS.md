# GovernexPlus — Detailed E2E UAT Scenarios (All Modules)

**Version:** 1.0 · **Date:** 2026-10-05
**Convention:** Every step is a real user action (click/type/navigate). Assertions are what the user **sees on screen**. No API shortcuts unless explicitly stated.

---

## Module 1 — Authentication & Session Management

### 1A · Happy-Path Login (per persona)

```
Step 1:  Navigate to /login
         → Assert: GovernexPlus branding, username field, password field, Sign In button
Step 2:  Enter username "qa_requestor", password "QaP@ss2026!Request"
Step 3:  Click "Sign In"
         → Assert: redirect to /dashboard (or Command Center)
         → Assert: welcome message shows "Robert Requestor"
         → Assert: JWT present in localStorage
Step 4:  Refresh page (F5)
         → Assert: still on dashboard, not redirected to login (session persists)
```

Repeat for all 22 personas (P01–P22). Each persona verifies:
- Their name appears in the header
- Their allowed nav items are visible
- Their denied nav items are NOT visible

### 1B · Invalid Login

```
Step 1:  Enter username "qa_requestor", password "WRONG"
Step 2:  Click "Sign In"
         → Assert: error toast "Invalid credentials"
         → Assert: still on /login page
         → Assert: no JWT in storage
```

### 1C · Account Lockout

```
Step 1:  Enter wrong password 6 times consecutively
         → Assert: after threshold, message "Account locked"
         → Assert: even correct password now fails
Step 2:  Wait for lockout period (or admin unlock)
Step 3:  Login with correct password
         → Assert: success
```

### 1D · Logout

```
Step 1:  Logged in as any user
Step 2:  Click profile menu → "Sign Out"
         → Assert: redirect to /login
         → Assert: JWT removed from localStorage
Step 3:  Navigate directly to /dashboard
         → Assert: redirect to /login (auth guard works)
Step 4:  Press browser back button
         → Assert: does NOT return to authenticated page
```

### 1E · Session Timeout

```
Step 1:  Login successfully
Step 2:  Wait beyond configured session timeout (e.g., 30 min idle)
Step 3:  Click any link
         → Assert: redirect to /login
         → Assert: toast "Session expired, please log in again"
```

### 1F · Concurrent Sessions

```
Step 1:  Login as P08 in Browser A
Step 2:  Login as P08 in Browser B
         → Assert: both sessions active (or previous invalidated, depending on policy)
Step 3:  Logout in Browser A
Step 4:  Refresh Browser B
         → Assert: Browser B still works (sessions independent) OR redirected (single-session policy)
```

**Test count: 40** (22 persona logins + 6 negative + 6 session + 6 edge)

---

## Module 2 — Dashboard & Command Center

### 2A · Dashboard Load

```
Step 1:  Login as P02 (Tenant Admin)
Step 2:  Land on / or /dashboard
         → Assert: stat cards visible (Total Users, Active Risks, Open Requests, Pending Reviews)
         → Assert: each stat card shows a number ≥ 0
         → Assert: health score widget shows 0–100
         → Assert: attention items list shows ≥ 0 items
Step 3:  Click on a stat card (e.g., "Open Requests")
         → Assert: navigates to the relevant page (/access-requests)
Step 4:  Click on an attention item
         → Assert: navigates to the item's detail page
```

### 2B · Dark Mode

```
Step 1:  Click theme toggle (sun/moon icon)
         → Assert: background changes to dark navy (#060c1a)
         → Assert: text is white/light gray
         → Assert: sidebar is dark slate
         → Assert: stat cards have dark backgrounds
         → Assert: all text remains readable (contrast)
Step 2:  Refresh page
         → Assert: dark mode persists (localStorage)
Step 3:  Toggle back to light
         → Assert: white backgrounds restored
         → Assert: no visual glitches
```

### 2C · Responsive / Mobile

```
Step 1:  Set viewport to 375×812 (iPhone)
         → Assert: sidebar collapses, hamburger icon appears
Step 2:  Click hamburger
         → Assert: navigation drawer slides in
         → Assert: all module links visible
Step 3:  Click a link
         → Assert: page loads, drawer closes
Step 4:  Set viewport to 768×1024 (tablet)
         → Assert: sidebar may be collapsed or narrow
Step 5:  Set viewport to 1920×1080 (desktop)
         → Assert: full sidebar visible
```

### 2D · Sidebar Navigation — Every Page

For each of the following pages, navigate and assert no blank screen, no 500 error:
- Dashboard, Access Requests, Certification, Firefighter, Risk Dashboard,
  Risk Rules, Risk Violations, Risk Management, Risk Heatmap, KRI Dashboard,
  Process Control, Audit Management, JML, TPRM, Fraud, BCM, Whistleblower,
  Surveys, Reports, Template Library, Settings, Users, Roles, Security Controls,
  AI Assistant, Identity Correlation

**Test count: 30** (dashboard + dark mode + responsive + 20 nav checks)

---

## Module 3 — User Management

### 3A · User List

```
Step 1:  Login as P02 (Tenant Admin)
Step 2:  Navigate to /users
         → Assert: user table loads with columns: Name, Username, Email, Department, Status, Roles
         → Assert: stats bar shows Total Users, Active, Inactive counts
Step 3:  Search "requestor"
         → Assert: table filters to show qa_requestor
Step 4:  Clear search
         → Assert: all users shown again
Step 5:  Filter by department "Finance"
         → Assert: only Finance users shown
Step 6:  Filter by status "Active"
         → Assert: only active users shown
Step 7:  Sort by Name (click column header)
         → Assert: alphabetical order
Step 8:  Click pagination "Next"
         → Assert: page 2 loads (if enough users)
```

### 3B · Create User

```
Step 1:  Click "Create User" button
         → Assert: modal/form opens with fields: Username, Full Name, Email, Department, Roles
Step 2:  Leave all fields empty, click Save
         → Assert: validation errors on required fields
Step 3:  Fill: username="uat_new_user", full_name="UAT New User",
         email="uat@test.com", department="QA", role=business_user
Step 4:  Click Save
         → Assert: toast "User created successfully"
         → Assert: user appears in table
Step 5:  Search "uat_new_user"
         → Assert: found in results
```

### 3C · Edit User

```
Step 1:  Click user row for "uat_new_user"
         → Assert: user detail page loads
Step 2:  Click "Edit"
         → Assert: edit form opens, pre-populated
Step 3:  Change department to "Engineering"
Step 4:  Click Save
         → Assert: toast "User updated"
         → Assert: table shows new department
```

### 3D · User Detail — Tabs

```
Step 1:  Click user "qa_requestor"
Step 2:  View "Roles" tab
         → Assert: assigned roles listed
Step 3:  View "Entitlements" tab
         → Assert: auth objects shown (if any)
Step 4:  View "Risk Profile" tab
         → Assert: risk score, violations count
Step 5:  View "Activity Log" tab
         → Assert: recent actions timestamped
```

### 3E · Deactivate / Reactivate

```
Step 1:  Find "uat_new_user"
Step 2:  Click "Deactivate"
         → Assert: status badge changes to "Inactive"
Step 3:  Filter by "Inactive"
         → Assert: user appears
Step 4:  Click "Reactivate"
         → Assert: status badge changes to "Active"
```

### 3F · Assign / Remove Role

```
Step 1:  Open user detail for "uat_new_user"
Step 2:  Go to Roles tab → Click "Assign Role"
Step 3:  Select ROLE_FI_VIEWER → Save
         → Assert: role appears in user's role list
Step 4:  Click "Remove" on the role
         → Assert: confirmation dialog
Step 5:  Confirm
         → Assert: role removed from list
```

### 3G · Inactive Users Page

```
Step 1:  Navigate to /users/inactive
         → Assert: only inactive users shown
Step 2:  Verify "uat_new_user" appears (if deactivated)
```

**Test count: 30** (list + create + edit + detail tabs + deactivate + roles + edge cases)

---

## Module 4 — Access Requests (already detailed above — 130 tests)

See previous breakdown: Submit (30) + Approve/Reject (30) + SoD/Risk (30) + Cart (20) + Provisioning (10) + RBAC (10)

---

## Module 5 — Certification Campaigns

### 5A · Campaign List

```
Step 1:  Login as P04 (Compliance Officer)
Step 2:  Navigate to /certification
         → Assert: campaign table loads
         → Assert: stats: Total Campaigns, Active, Completed, items pending
Step 3:  Search campaigns
         → Assert: filter works
Step 4:  Filter by status (Active/Completed/Draft)
         → Assert: filter works
```

### 5B · Create Campaign

```
Step 1:  Click "Create Campaign"
         → Assert: form opens
Step 2:  Fill: name="Q4 User Access Review"
         type="User Access Review"
         scope="All Users" (or specific department)
         reviewers=qa_line_manager
         deadline=2026-11-01
Step 3:  Click "Create" (or Save as Draft)
         → Assert: campaign appears in list with status "Draft"
Step 4:  Click "Launch Campaign"
         → Assert: status → "Active"
         → Assert: toast "Campaign launched"
         → Assert: review items generated for all in-scope users
```

### 5C · Reviewer — Perform Reviews

```
Step 1:  Logout → Login as P07 (Line Manager)
Step 2:  Navigate to /certification/review (or "My Reviews")
         → Assert: review items for the launched campaign visible
Step 3:  Click first review item
         → Assert: user's current roles listed
         → Assert: user's last login date shown
         → Assert: user's risk level shown
         → Assert: user's department/manager shown
Step 4:  Click "Certify" (approve — keep access)
         → Assert: item marked with green checkmark
         → Assert: moves to "Reviewed" list
Step 5:  Click next item → Click "Revoke"
         → Assert: reason field appears
Step 6:  Enter reason: "User transferred to new department, no longer needs this access"
Step 7:  Confirm revoke
         → Assert: item marked with red X
         → Assert: revocation queued
Step 8:  Click "Flag for Review" on another item
         → Assert: item flagged, comment field opens
Step 9:  Bulk select 5 items → Click "Bulk Certify"
         → Assert: all 5 marked certified
```

### 5D · Campaign Progress

```
Step 1:  Login as P04 (Compliance Officer)
Step 2:  Navigate to /certification → click the campaign
         → Assert: progress bar shows % complete (e.g., 8/20 = 40%)
         → Assert: per-reviewer breakdown visible
         → Assert: certified vs revoked vs pending counts
Step 3:  Wait for all items reviewed
         → Assert: campaign auto-closes (status → "Completed") OR manual close button appears
```

### 5E · Campaign Report

```
Step 1:  Click "Generate Report" on completed campaign
         → Assert: report shows all decisions
         → Assert: who certified/revoked what and when
Step 2:  Export to PDF
         → Assert: PDF downloads with all evidence
```

### 5F · Revocation Execution

```
Step 1:  After campaign with revocations completes:
Step 2:  Check the revoked user's profile
         → Assert: the revoked role is NO LONGER assigned
         → Assert: audit trail shows "Removed by certification review"
```

### 5G · Edge Cases

```
- Campaign with 0 items (empty scope) → meaningful error
- Campaign with 500 items → performance OK
- Reviewer reviews own access → allowed or blocked (configurable)
- Two campaigns covering same user → both show the user
- Campaign deadline passed with unreviewed items → escalation or auto-action
- External Auditor (P09) views campaign → read-only, no certify/revoke buttons
```

**Test count: 40** (list + create + reviewer flows + progress + report + revocation + edge)

---

## Module 6 — SoD Rule Management

### 6A · Rule Library

```
Step 1:  Login as P06 (IT Security Admin)
Step 2:  Navigate to /risk/sod-rules (or /risk/rules)
         → Assert: table loads with 120+ rules
         → Assert: columns: Rule ID, Name, Module, Conflicting Functions, Risk Level
Step 3:  Search "FI"
         → Assert: Finance rules filtered
Step 4:  Filter by module (FI, MM, SD, HR)
         → Assert: correct rules shown
Step 5:  Click a rule
         → Assert: detail view: description, function 1, function 2, tcodes, risk level
```

### 6B · Create Custom Rule

```
Step 1:  Click "Create Rule"
         → Assert: form opens
Step 2:  Fill: name="Custom Test Rule"
         function1="ZFI_CUSTOM_01"
         function2="ZFI_CUSTOM_02"
         risk_level="High"
         description="Test custom rule for UAT"
Step 3:  Save
         → Assert: rule appears in list, marked as "Custom"
Step 4:  Edit the rule → change risk_level to "Critical"
         → Assert: updated in list
Step 5:  Delete the rule
         → Assert: removed from list
```

### 6C · Enable/Disable Rules

```
Step 1:  Find a built-in rule (e.g., "FI-001")
Step 2:  Toggle "Enabled" off
         → Assert: rule marked disabled
         → Assert: disabled rules skip during analysis
Step 3:  Toggle back on
         → Assert: rule active again
```

### 6D · Rule Impact

```
Step 1:  Disable a rule that was catching violations
Step 2:  Run ARA analysis
         → Assert: violations from that rule no longer appear
Step 3:  Re-enable
Step 4:  Re-run ARA
         → Assert: violations reappear
```

**Test count: 25** (library + create/edit/delete + enable/disable + impact verification)

---

## Module 7 — Access Risk Analysis (ARA)

### 7A · Run Analysis

```
Step 1:  Login as P05 (Risk Manager)
Step 2:  Navigate to /risk (ARA dashboard) or /risk/violations
         → Assert: page loads with violation summary
Step 3:  Click "Run Analysis" (scope: All Users)
         → Assert: progress indicator appears
         → Assert: analysis completes (may take seconds)
Step 4:  View results
         → Assert: violations listed with columns: User, Rule, Conflicting Roles, Severity
Step 5:  Click a violation
         → Assert: detail view: rule description, affected tcodes, user info
         → Assert: AI narrative section explains the risk in business language
```

### 7B · Single-User Analysis

```
Step 1:  Select specific user (qa_requestor)
Step 2:  Run analysis
         → Assert: only violations for that user shown
Step 3:  Results match known role assignments
```

### 7C · Violation Lifecycle

```
Step 1:  Find an open violation
Step 2:  Click "In Progress" → status changes
Step 3:  Attach a mitigation control
         → Assert: mitigation linked to violation
Step 4:  Mark as "Mitigated"
         → Assert: status updated
Step 5:  Alternatively: "Accept Risk"
         → Assert: risk acceptance recorded with reason
Step 6:  Alternatively: "False Positive"
         → Assert: marked and excluded from future reports
Step 7:  Alternatively: "Remediate" → remove conflicting role
         → Assert: violation status → Remediated
```

### 7D · Violation Persistence

```
Step 1:  Run analysis → violations found
Step 2:  Navigate away
Step 3:  Come back
         → Assert: violations still there (DB-persisted, not just in-memory)
Step 4:  Refresh page
         → Assert: same violations
```

### 7E · AI Explanations

```
Step 1:  Click a violation
Step 2:  View "AI Explanation" section
         → Assert: plain-language narrative like "This user can both CREATE purchase orders
         AND approve them, bypassing the four-eyes principle in procurement"
Step 3:  Click "Investigate"
         → Assert: deeper analysis / recommended actions
Step 4:  Click "Quick Fix"
         → Assert: suggested remediation steps
```

### 7F · Filtering & Export

```
Step 1:  Filter violations by severity "Critical"
         → Assert: only critical shown
Step 2:  Filter by user
Step 3:  Filter by rule
Step 4:  Sort by date (newest first)
Step 5:  Export to CSV
         → Assert: CSV downloads with all filtered violations
Step 6:  Export to PDF
         → Assert: PDF report generates
```

**Test count: 30** (analysis + lifecycle + persistence + AI + filtering)

---

## Module 8 — Firefighter (Emergency Access)

### 8A · Request Emergency Access

```
Step 1:  Login as P06 (IT Security Admin)
Step 2:  Navigate to /privileged-access
         → Assert: FF dashboard loads with active sessions, stats
Step 3:  Click "Request Emergency Access"
         → Assert: form opens with: FF ID selector, reason, duration, priority
Step 4:  Select FF ID (e.g., "FF_SAP_ALL_01")
Step 5:  Select reason code: "Production Issue"
Step 6:  Enter reason text: "P1 incident #4532 — posting error blocking month-end close"
Step 7:  Set duration: 2 hours
Step 8:  Set priority: High
Step 9:  Submit
         → Assert: toast "Request submitted"
         → Assert: request visible with status "Pending Approval"
```

### 8B · FF Owner Approves

```
Step 1:  Login as P11 (FF Owner)
Step 2:  Navigate to FF Approvals
         → Assert: pending request from P06 visible
Step 3:  Click request
         → Assert: full details: requester, FF ID, reason, duration, priority
Step 4:  Click "Approve"
         → Assert: status → "Approved"
         → Assert: notification sent to requester
```

### 8C · FF Owner Rejects

```
Step 1:  Different request
Step 2:  Click "Reject"
         → Assert: reason field required
Step 3:  Enter: "Insufficient justification — please escalate through change management"
         → Assert: status → "Rejected"
```

### 8D · Start Firefighter Session

```
Step 1:  Login as P17 (Firefighter Session User) — or P06 with approved request
Step 2:  Navigate to Active Sessions
         → Assert: approved FF access visible
Step 3:  Click "Start Session" (check-in)
         → Assert: session timer starts
         → Assert: activity logging begins
         → Assert: session ID generated
Step 4:  Perform actions during session (navigate pages, view data)
         → Assert: each action logged in session log
Step 5:  Click "End Session" (check-out)
         → Assert: session closed
         → Assert: duration recorded
         → Assert: toast "Session ended"
```

### 8E · FF Controller Monitoring

```
Step 1:  Login as P12 (FF Controller)
Step 2:  Navigate to /privileged-access/monitor
         → Assert: live session visible (if active)
         → Assert: activity log streams in real-time
Step 3:  Click session → view details
         → Assert: all actions performed during session listed
         → Assert: timestamps on each action
Step 4:  Click "Complete Review"
         → Assert: review form: findings, risk assessment
Step 5:  Submit review
         → Assert: review recorded in audit trail
```

### 8F · Session Timeout / Auto-Expire

```
Step 1:  Start a session with 1-hour duration
Step 2:  Wait past duration (or simulate)
         → Assert: session auto-closed
         → Assert: notification to requester, owner, controller
         → Assert: session log shows "Auto-expired"
```

### 8G · Session Extension

```
Step 1:  During active session, click "Request Extension"
Step 2:  Enter: additional 1 hour, reason "Issue not yet resolved"
         → Assert: extension request sent to FF Owner
Step 3:  (As FF Owner) Approve extension
         → Assert: session duration extended
         → Assert: timer updated
```

### 8H · Post-Session Audit

```
Step 1:  Login as P11 (FF Owner)
Step 2:  Navigate to FF Session Logs
         → Assert: completed sessions listed
Step 3:  Click a completed session
         → Assert: full activity log with every action and timestamp
Step 4:  Verify log cannot be modified
         → Assert: read-only view, no edit buttons
```

### 8I · FF + CCM Integration

```
Step 1:  After FF session completes
Step 2:  Login as P03 (CISO)
Step 3:  Navigate to /process-control/ccm
         → Assert: CCM exception flagged for FF session
         → Assert: exception references the FF session ID
Step 4:  Review exception
         → Assert: can mark as "Reviewed" or "Accepted Risk"
```

**Test count: 60** (request + approve/reject + session + monitoring + extend + audit + CCM)

---

## Module 9 — Enterprise Risk Management

### 9A · Risk Register

```
Step 1:  Login as P05 (Risk Manager)
Step 2:  Navigate to /risk-management/register
         → Assert: risk register table loads
         → Assert: columns: Risk ID, Title, Category, Status, Likelihood, Impact, Score, Owner
Step 3:  Click "Create Risk"
         → Assert: form opens
Step 4:  Fill: title="Cybersecurity breach risk"
         category=IT_CYBER
         description="Risk of data breach through phishing attacks"
         likelihood=4, impact=5
         owner=qa_ciso
Step 5:  Save
         → Assert: risk appears in register with calculated score (4×5=20)
         → Assert: status = "Identified"
```

### 9B · Risk Assessment

```
Step 1:  Click the new risk → "Add Assessment"
Step 2:  Fill: type=Periodic, likelihood=4, impact=5, notes="Based on recent phishing attempts"
Step 3:  Save
         → Assert: assessment recorded, status → "Assessed"
Step 4:  Add another assessment (different type: Ad-hoc)
         → Assert: assessment history grows
```

### 9C · Risk Heatmap

```
Step 1:  Navigate to /risk-management/heatmap
         → Assert: 5×5 matrix loads (Likelihood vs Impact)
         → Assert: risks plotted as dots/badges in correct cells
Step 2:  Click a cell (e.g., High Likelihood × High Impact)
         → Assert: drill-down shows risks in that zone
Step 3:  Hover over a risk dot
         → Assert: tooltip shows risk title and score
```

### 9D · Risk Response

```
Step 1:  Open a risk → "Add Response"
Step 2:  Fill: type=Mitigate, description="Implement MFA + phishing training"
         responsible=qa_it_security, due_date=2026-12-01
Step 3:  Save
         → Assert: response attached to risk
         → Assert: response status = "Planned"
Step 4:  Update status → "In Progress"
Step 5:  Update status → "Completed"
         → Assert: risk status may update to "Mitigated"
```

### 9E · KRI Dashboard

```
Step 1:  Navigate to /risk-management/kri
         → Assert: KRI dashboard loads with all indicators
Step 2:  Click "Create KRI"
Step 3:  Fill: name="Phishing click rate"
         linked_risk=cybersecurity_risk
         warning_threshold=5%, breach_threshold=10%
         current_value=3%
Step 4:  Save
         → Assert: KRI appears, status = "Normal" (green)
Step 5:  Record new measurement: value=7%
         → Assert: status → "Warning" (yellow)
Step 6:  Record new measurement: value=12%
         → Assert: status → "Breach" (red)
         → Assert: alert/notification triggered
Step 7:  View trend chart
         → Assert: line chart shows 3% → 7% → 12% over time
```

### 9F · Risk Incidents

```
Step 1:  Navigate to /risk-management/incidents
Step 2:  Click "Report Incident"
Step 3:  Fill: title="Phishing attack on Finance team"
         severity=HIGH
         linked_risk=cybersecurity_risk
         description="5 employees clicked phishing link, credentials potentially compromised"
Step 4:  Save
         → Assert: incident created, status = "Reported"
Step 5:  Update → "Investigating"
Step 6:  Add investigation notes
Step 7:  Update → "Resolved"
Step 8:  Update → "Closed"
         → Assert: full lifecycle completed
```

### 9G · Risk Scenarios & Monte Carlo

```
Step 1:  Navigate to risk scenarios
Step 2:  Create scenario: type=Cascading, velocity=Rapid
Step 3:  Configure Monte Carlo simulation: distribution=Triangular, iterations=1000
Step 4:  Run simulation
         → Assert: results show probability distribution
         → Assert: 95th percentile loss estimate shown
```

### 9H · Risk Appetite

```
Step 1:  Navigate to risk appetite settings
Step 2:  Set appetite for IT_CYBER: tolerance=Medium, threshold_score=15
Step 3:  Save
Step 4:  View risk register
         → Assert: risks exceeding appetite highlighted with "Appetite Breach" badge
```

**Test count: 60** (register CRUD + assessments + heatmap + responses + KRI + incidents + scenarios + appetite)

---

## Module 10 — Process Control

### 10A · Control Library

```
Step 1:  Login as P10 (SOX Control Owner) or P14 (Process Owner)
Step 2:  Navigate to /process-control/controls
         → Assert: control list loads
Step 3:  Click "Create Control"
Step 4:  Fill: name="Invoice Approval Control"
         type=Preventive, nature=Manual, frequency=Daily
         description="All invoices > $10K require dual approval"
Step 5:  Save
         → Assert: control created, status = "Draft"
Step 6:  Activate → status = "Active"
```

### 10B · Control Testing

```
Step 1:  Navigate to /process-control/testing
Step 2:  Select a control → Click "Create Test"
Step 3:  Fill: type=Operating Effectiveness, period="Q3 2026"
Step 4:  Execute test: sample 25 invoices
Step 5:  Record result: 24/25 compliant → "Effective"
         → Assert: test result saved
         → Assert: evidence can be attached
Step 6:  Test another: 18/25 compliant → "Ineffective"
         → Assert: deficiency auto-created
```

### 10C · Deficiency Management

```
Step 1:  Navigate to /process-control/deficiencies
         → Assert: deficiency from failed test visible
Step 2:  Click deficiency
         → Assert: severity classified (Significant Deficiency / Material Weakness / Control Gap)
Step 3:  Add remediation plan
Step 4:  Track: Open → In Remediation → Remediated → Verified Closed
Step 5:  Verify control re-test passes after remediation
```

### 10D · CCM (Continuous Controls Monitoring)

```
Step 1:  Navigate to /process-control/ccm
         → Assert: CCM dashboard loads
Step 2:  Create CCM rule: type=Threshold, control=Invoice Approval
         condition="invoices_approved_without_dual_sign > 0"
Step 3:  Execute rule
         → Assert: PASS or FAIL result
Step 4:  If FAIL: exception flagged
Step 5:  Review exception → Accept / Investigate
```

### 10E · Sign-Off Certification

```
Step 1:  Navigate to sign-off area
Step 2:  Create SOX sign-off for Q3
Step 3:  Review all controls in scope
Step 4:  Sign: "Certified" or "Certified with Exceptions" or "Refused"
         → Assert: sign-off recorded with timestamp and signer
```

### 10F · Sub-Processes

```
Step 1:  Create process "Order to Cash"
Step 2:  Add sub-process "Order Entry"
Step 3:  Add sub-process "Shipping"
Step 4:  Link controls to each sub-process
         → Assert: hierarchy view shows parent → children
         → Assert: controls mapped to sub-processes
```

### 10G · Evidence Management

```
Step 1:  Upload evidence file (screenshot, PDF)
Step 2:  Link to a control test
         → Assert: evidence attached, visible in test detail
Step 3:  View evidence gallery
         → Assert: all evidence items shown with metadata
Step 4:  Archive old evidence
         → Assert: status → "Archived"
```

**Test count: 40** (controls CRUD + testing + deficiency lifecycle + CCM + sign-off + processes + evidence)

---

## Module 11 — Audit Management

### 11A · Audit Planning

```
Step 1:  Login as P19 (Internal Auditor)
Step 2:  Navigate to /audit-management/planning
         → Assert: audit plan list loads
Step 3:  Click "Create Plan"
Step 4:  Fill: name="FY2027 Annual Audit Plan"
         type=Annual, fiscal_year=2027
Step 5:  Save
         → Assert: plan created, status = "Draft"
Step 6:  Click "Generate Risk-Based Plan"
         → Assert: plan auto-populated based on risk register data
Step 7:  Submit for approval → status = "Pending Approval"
Step 8:  (As approver) Approve → status = "Approved"
```

### 11B · Audit Engagement

```
Step 1:  Click "Create Engagement" under the plan
Step 2:  Fill: title="Finance Access Controls Audit"
         type=IT, scope="SAP FI module"
         team=[qa_int_auditor]
Step 3:  Save → status = "Planned"
Step 4:  Send announcement → status = "Announced"
Step 5:  Start fieldwork → status = "Fieldwork"
```

### 11C · Audit Findings

```
Step 1:  Within engagement, click "Add Finding"
Step 2:  Fill: title="Excessive SAP_ALL assignments"
         severity=Critical
         description="12 users have SAP_ALL in production with no justification"
         recommendation="Remove SAP_ALL from all non-emergency users within 30 days"
Step 3:  Save
         → Assert: finding attached to engagement
Step 4:  Status: Draft → Discussed (with management)
Step 5:  Record management response:
         "We will remove SAP_ALL from 10 users immediately and establish FF process for remaining 2"
Step 6:  Create management action: deadline=2026-11-15
Step 7:  Track action: Open → In Progress → Completed
Step 8:  Verify action → status = "Closed Verified"
```

### 11D · Workpapers

```
Step 1:  Create workpaper: title="SAP_ALL User List"
Step 2:  Attach evidence
Step 3:  Submit for review → status = "Pending Review"
Step 4:  (Senior auditor) Review → "Reviewed" or "Revision Needed"
Step 5:  If revision needed → update → re-submit
```

### 11E · Engagement Completion

```
Step 1:  All procedures completed
Step 2:  Draft report → status = "Draft Report"
Step 3:  Finalize → status = "Final Report"
Step 4:  Close engagement → status = "Closed"
Step 5:  Generate committee report
         → Assert: summary across all engagements
```

### 11F · External Auditor (Read-Only)

```
Step 1:  Login as P09 (External Auditor)
Step 2:  Navigate to /audit-management
         → Assert: engagements visible
Step 3:  Click an engagement
         → Assert: findings, workpapers visible (read-only)
Step 4:  Attempt to create finding
         → Assert: button not visible or action blocked
```

### 11G · Auditable Entities

```
Step 1:  Navigate to entity management
Step 2:  Create entity: type=Process, name="Procure to Pay"
Step 3:  Set risk rating
Step 4:  Link to audit plan
```

**Test count: 40** (planning + engagement lifecycle + findings + workpapers + completion + read-only + entities)

---

## Module 12 — JML (Joiner / Mover / Leaver)

### 12A · JML Policies

```
Step 1:  Login as P13 (HR Manager)
Step 2:  Navigate to /jml/policies
         → Assert: policy list loads
         → Assert: stats: Total, Active, Joiners, Leavers
Step 3:  Click "Create Policy"
Step 4:  Fill: policy_name="Finance Joiner Provisioning"
         event_type="joiner"
         org_unit="Finance"
         birthright_roles="ROLE_FI_VIEWER, ROLE_HR_SELF_SERVICE"
         description="Auto-provision finance joiners with read access"
         is_active=true
Step 5:  Save
         → Assert: policy created, "Joiner" badge shown
Step 6:  Search "Finance"
         → Assert: policy found
Step 7:  Filter by event type "Joiner"
         → Assert: only joiner policies shown
Step 8:  Edit: change org_unit to "Finance & Accounting"
         → Assert: updated
Step 9:  Toggle active off
         → Assert: policy deactivated
Step 10: Toggle active on
         → Assert: policy reactivated
Step 11: Delete policy
         → Assert: removed from list
```

### 12B · Joiner Event

```
Step 1:  Create a joiner event (or trigger via HR feed):
         employee="New Hire", department="Finance"
Step 2:  Event matches "Finance Joiner" policy
         → Assert: event processed
         → Assert: birthright roles ROLE_FI_VIEWER, ROLE_HR_SELF_SERVICE auto-assigned
Step 3:  Check user profile
         → Assert: roles assigned
Step 4:  Check audit trail
         → Assert: "JML Joiner: roles provisioned" logged
```

### 12C · Mover Event

```
Step 1:  Trigger mover event: employee transfers Finance → Marketing
         → Assert: Finance roles (ROLE_FI_VIEWER) queued for removal
         → Assert: Marketing birthright roles queued for grant (if policy exists)
Step 2:  Line Manager (P07) reviews move
         → Assert: pending JML items visible
Step 3:  Approve removal + grant
         → Assert: old roles removed, new roles assigned
```

### 12D · Leaver Event

```
Step 1:  Trigger leaver event: employee terminated
         → Assert: ALL roles queued for revocation
         → Assert: account marked for deactivation
Step 2:  Review the revocation list
Step 3:  Execute
         → Assert: all roles removed
         → Assert: user status → Inactive
Step 4:  Verify user cannot log in
```

### 12E · HR Event Monitor

```
Step 1:  Navigate to /jml/events
         → Assert: event log loads
         → Assert: events listed with: employee, event type, status, timestamp
Step 2:  Filter by event type
Step 3:  Filter by status (pending/completed/failed)
Step 4:  Click event → detail view
```

**Test count: 30** (policies CRUD + joiner + mover + leaver + event monitor)

---

## Module 13 — Identity Correlation

### 13A · Overview

```
Step 1:  Login as P13 (HR Manager)
Step 2:  Navigate to /intelligence/identity
         → Assert: overview stats: total identities, correlated, orphaned, conflicting
```

### 13B · Run Correlation

```
Step 1:  Click "Run Correlation"
         → Assert: engine executes, progress shown
Step 2:  View results
         → Assert: matched identities listed
         → Assert: orphan accounts identified
         → Assert: conflicts flagged
```

### 13C · Orphan Management

```
Step 1:  View orphan accounts
         → Assert: accounts with no HR record match
Step 2:  Select an orphan → "Link to HR Record"
Step 3:  Select the matching HR record
         → Assert: account linked, removed from orphan list
```

### 13D · Conflict Resolution

```
Step 1:  View conflicts
         → Assert: accounts with mismatched attributes across systems
Step 2:  Click conflict → see both versions
Step 3:  Choose "Use HR system data" or "Use SAP data"
         → Assert: conflict resolved
```

**Test count: 15** (overview + correlation + orphans + conflicts)

---

## Module 14 — TPRM (Third-Party Risk Management)

### 14A · Vendor Registry

```
Step 1:  Login as P20 (Vendor Manager)
Step 2:  Navigate to /tprm/vendors
         → Assert: vendor list loads
Step 3:  Click "Add Vendor"
Step 4:  Fill: vendor_name="Acme Cloud Services"
         category="Cloud Provider"
         risk_tier="High"
         contact_name="Jane Doe"
         contact_email="jane@acme.example"
         status="Active"
Step 5:  Save
         → Assert: vendor appears in list with "High" risk badge
Step 6:  Search "Acme"
         → Assert: vendor found
Step 7:  Filter by risk tier "High"
         → Assert: correct vendors shown
Step 8:  Click vendor → detail page
         → Assert: vendor info, tabs for assessments/issues/contracts
```

### 14B · Vendor Assessment

```
Step 1:  On vendor detail → "Start Assessment"
Step 2:  Fill questionnaire: security controls, compliance status, data handling
Step 3:  Submit assessment
         → Assert: risk score calculated (e.g., 7.2/10)
         → Assert: status = "Submitted"
Step 4:  Review assessment → Approve
         → Assert: status = "Approved"
Step 5:  View assessment history
         → Assert: past assessments listed with scores and dates
```

### 14C · Vendor Issues

```
Step 1:  On vendor detail → Issues tab → "Create Issue"
Step 2:  Fill: title="Data breach notification delay"
         severity=High
         description="Vendor took 72 hours to notify us of breach, exceeding 24-hour SLA"
Step 3:  Save
         → Assert: issue created, status = "Open"
Step 4:  Add remediation plan
Step 5:  Track: Open → In Progress → Resolved
Step 6:  Close issue
```

### 14D · Vendor Contracts

```
Step 1:  On vendor detail → Contracts tab → "Add Contract"
Step 2:  Fill: contract name, start/end dates, value
Step 3:  Save
         → Assert: contract listed
Step 4:  Monitor contract expiry
         → Assert: expiring contracts highlighted
```

### 14E · TPRM Dashboard

```
Step 1:  Navigate to /tprm (overview)
         → Assert: vendor count, risk distribution, overdue assessments
Step 2:  Login as P05 (Risk Manager)
Step 3:  Navigate to TPRM
         → Assert: risk manager sees vendor risk overview
```

**Test count: 30** (vendor CRUD + assessments + issues + contracts + dashboard)

---

## Module 15 — Fraud Detection

### 15A · Fraud Rules

```
Step 1:  Login as P06 (IT Security Admin)
Step 2:  Navigate to /fraud/rules
         → Assert: rule list loads
Step 3:  Click "Create Rule"
Step 4:  Fill: rule_name="Duplicate Payment Detection"
         rule_type="transaction"
         conditions="amount > 10000 AND duplicate vendor+amount within 24h"
         severity="High"
Step 5:  Save
         → Assert: rule created, visible in list
Step 6:  Enable/disable toggle
         → Assert: works
Step 7:  Edit rule
         → Assert: changes saved
Step 8:  Delete rule
         → Assert: removed
```

### 15B · Fraud Alerts

```
Step 1:  Navigate to /fraud/alerts
         → Assert: alert inbox loads (seeded alert visible from fraud-rule hit fixture)
Step 2:  Click an alert
         → Assert: detail view: triggered rule, affected transaction, user, amount, timestamp
Step 3:  Dismiss alert
         → Assert: alert marked dismissed
Step 4:  Escalate another alert
         → Assert: alert escalated
Step 5:  Click "Open Case" on an alert
         → Assert: case creation form pre-populated with alert data
```

### 15C · Fraud Case Management

```
Step 1:  Navigate to /fraud/cases
         → Assert: case list loads
Step 2:  Create standalone case (not from alert):
         title="Suspected expense fraud"
         description="Multiple expense reports with suspicious round-number amounts"
         severity=Medium
Step 3:  Save
         → Assert: case created, status = "Open", case_reference = "FRC-XXXXXXXX"
Step 4:  Assign investigator
Step 5:  Add investigation notes: "Reviewed 15 expense reports, found 3 with fabricated receipts"
Step 6:  Update status → "Investigating"
Step 7:  Record loss amount: $15,000
Step 8:  Link related alert (if any)
Step 9:  Update status → "Closed"
Step 10: Record outcome: "Employee terminated, $12,000 recovered"
         → Assert: case closed with full audit trail
```

### 15D · Case from Alert

```
Step 1:  Start from alert → "Open Case"
         → Assert: case title pre-filled from alert
         → Assert: alert linked to case
Step 2:  Complete investigation flow (same as 15C steps 4–10)
```

### 15E · Fraud Dashboard

```
Step 1:  Navigate to /fraud
         → Assert: overview: open cases, active alerts, rules count
         → Assert: severity distribution chart
```

**Test count: 30** (rules CRUD + alerts + cases lifecycle + dashboard)

---

## Module 16 — BCM (Business Continuity Management)

### 16A · Business Impact Analysis (BIA)

```
Step 1:  Login as P05 (Risk Manager)
Step 2:  Navigate to /bcm/bia
         → Assert: BIA list loads
Step 3:  Click "Create BIA"
Step 4:  Fill: process_name="Payment Processing"
         rto_hours=4, rpo_hours=1
         impact_level="Critical"
         description="Core payment processing system"
Step 5:  Save
         → Assert: BIA record created
Step 6:  Edit → change RTO to 2 hours
Step 7:  Search/filter by criticality
```

### 16B · BCM Plans

```
Step 1:  Navigate to /bcm/plans
Step 2:  Click "Create Plan"
Step 3:  Fill: plan_name="IT Disaster Recovery Plan"
         plan_type="DR"
         description="DR plan for core IT infrastructure"
         priority="Critical"
Step 4:  Save
         → Assert: plan created, status = "Draft"
Step 5:  Activate plan → status = "Active"
Step 6:  Edit plan details
Step 7:  Link BIA record to plan
```

### 16C · BCM Exercises

```
Step 1:  Navigate to exercises (or within plan → "Create Exercise")
Step 2:  Fill: exercise_name="Annual DR Drill"
         linked_plan=IT DR Plan
         type="Full Exercise"
         scheduled_date=2026-11-15
Step 3:  Save
Step 4:  Execute exercise
Step 5:  Record outcome: "Partial Success — failover completed in 6h (target was 4h)"
Step 6:  Record lessons learned
```

### 16D · Incident Activation

```
Step 1:  Navigate to /bcm/activations
Step 2:  Click "Activate Incident"
Step 3:  Fill: plan=IT DR Plan
         activation_reason="Data center power failure"
         severity=Critical
Step 4:  Save
         → Assert: activation created, status = "Activated"
Step 5:  Track recovery steps
Step 6:  Update → "Recovered"
Step 7:  Close → "Closed"
         → Assert: full incident lifecycle recorded
```

**Test count: 25** (BIA + plans + exercises + activations)

---

## Module 17 — Whistleblower

### 17A · Anonymous Submission (PUBLIC — No Auth)

```
Step 1:  Navigate to /whistleblower/intake (NO login)
         → Assert: page loads without authentication
         → Assert: form visible: category, description, priority
Step 2:  Select category: "Fraud"
Step 3:  Enter description: "I observed my supervisor approving invoices from a company
         she co-owns. Invoices #INV-4401 and #INV-4402 appear to be for services never rendered."
Step 4:  Select priority: "High"
Step 5:  Click "Submit"
         → Assert: confirmation screen
         → Assert: unique reference code displayed (e.g., "WB-A1B2C3D4")
         → Assert: message "Save this code — you'll need it to track your report"
```

### 17B · Anonymous Tracking (PUBLIC — No Auth)

```
Step 1:  Navigate to /whistleblower/intake (tracking section)
Step 2:  Enter reference code from 17A
Step 3:  Click "Track"
         → Assert: case status shown (e.g., "Open")
         → Assert: submission details visible
         → Assert: no personally identifiable information shown
Step 4:  Enter invalid reference code
         → Assert: "Case not found" message
```

### 17C · Investigator View

```
Step 1:  Login as P06 (IT Security Admin / Investigator)
Step 2:  Navigate to /whistleblower/inbox
         → Assert: submitted case visible in list
         → Assert: columns: Reference, Category, Priority, Status, Date
Step 3:  Click case
         → Assert: full details: category, description, priority, timeline
Step 4:  Add investigator message:
         "Thank you for your report. We are initiating an investigation.
         Can you provide the approximate dates of the invoices?"
Step 5:  Save message
         → Assert: message added to thread
Step 6:  Change status → "Investigating"
         → Assert: status updated
```

### 17D · Anonymous Reply

```
Step 1:  (No login) Navigate to tracking, enter reference code
         → Assert: status now shows "Investigating"
         → Assert: investigator message visible:
         "Can you provide the approximate dates?"
Step 2:  Enter reply: "The invoices were dated September 12 and September 28, 2026.
         Both were for 'consulting services' totaling $45,000."
Step 3:  Submit reply
         → Assert: reply submitted confirmation
```

### 17E · Investigator Sees Reply

```
Step 1:  (As P06) Refresh case
         → Assert: anonymous reply visible in message thread
         → Assert: sender shows "Submitter" (anonymous)
         → Assert: message content visible
Step 2:  Continue investigation → add more messages
Step 3:  Eventually close case:
         status → "Closed"
         outcome notes recorded
```

### 17F · Closed Case — No More Replies

```
Step 1:  (No login) Track the closed case
         → Assert: status shows "Closed"
Step 2:  Try to submit reply
         → Assert: blocked — "This case is closed"
```

### 17G · Edge Cases

```
- Submit with empty description → validation error
- Submit with missing category → validation error
- Very long description (5000+ chars) → accepted or truncated
- Multiple reports with same content → each gets unique reference
- Case escalation → status = "Escalated"
```

**Test count: 30** (submit + track + investigator + reply + close + edges)

---

## Module 18 — Surveys

### 18A · Create Survey

```
Step 1:  Login as P02 (Tenant Admin)
Step 2:  Navigate to /surveys/designer
         → Assert: survey list loads
Step 3:  Click "Create Survey"
Step 4:  Fill: title="2026 Security Awareness Assessment"
         description="Annual security awareness evaluation"
Step 5:  Add questions:
         Q1: "What should you do if you receive a suspicious email?" (Multiple Choice)
             Options: a) Click the link, b) Report to IT, c) Forward to colleagues, d) Ignore
         Q2: "Rate your confidence in identifying phishing emails" (Rating 1-5)
         Q3: "Describe your department's data handling procedures" (Free Text)
Step 6:  Save as draft
         → Assert: survey saved with 3 questions
Step 7:  Click "Publish"
         → Assert: survey status → "Published"
```

### 18B · Distribute Survey

```
Step 1:  Navigate to /surveys/distribution
Step 2:  Select the published survey
Step 3:  Add recipients: qa_requestor, qa_line_manager, qa_compliance
Step 4:  Click "Distribute"
         → Assert: distribution sent to 3 recipients
         → Assert: status shows "3 pending, 0 completed"
```

### 18C · Respond to Survey

```
Step 1:  Login as P08 (Business User / qa_requestor)
Step 2:  Navigate to surveys (or notification link)
         → Assert: assigned survey visible
Step 3:  Open survey
         → Assert: questions displayed
Step 4:  Answer Q1: select "Report to IT"
Step 5:  Answer Q2: rate 4/5
Step 6:  Answer Q3: type response
Step 7:  Click "Submit"
         → Assert: toast "Survey submitted"
         → Assert: survey marked as completed for this user
```

### 18D · Survey Analytics

```
Step 1:  Login as P02
Step 2:  Navigate to /surveys/analytics
Step 3:  Select the survey
         → Assert: response rate shown (e.g., 1/3 = 33%)
         → Assert: Q1 shows response distribution (chart)
         → Assert: Q2 shows average rating
         → Assert: Q3 shows text responses
Step 4:  Export results to CSV
         → Assert: CSV downloads
```

### 18E · Survey Lifecycle

```
- Edit published survey → warning or blocked
- Close survey → no more responses accepted
- Delete survey → removed from list
- Partial response save → draft response saved
- Survey with 0 questions → validation error
```

**Test count: 20** (create + distribute + respond + analytics + lifecycle)

---

## Module 19 — Template Library

### 19A · Browse Library

```
Step 1:  Login as P02 (Tenant Admin)
Step 2:  Navigate to /library/content
         → Assert: template packs visible (≥42 from seeder)
         → Assert: categories: SoD Rules, Mitigations, Workflows, Controls, Risk Scenarios
Step 3:  Search templates
Step 4:  Filter by category
Step 5:  Click a pack → view items
         → Assert: versioned items listed with descriptions
```

### 19B · Activate Template Pack

```
Step 1:  Navigate to /library/wizard
Step 2:  Select a template pack (e.g., "SoD Rules — Finance")
Step 3:  Preview items
         → Assert: items listed with what will be activated
Step 4:  Click "Activate"
         → Assert: activation wizard runs
         → Assert: items copied to tenant
Step 5:  Navigate to /library/active
         → Assert: activated items visible with "Active" status
```

### 19C · Copy-on-Write Edit

```
Step 1:  Open an activated item
Step 2:  Click "Edit"
         → Assert: copy-on-write triggered — tenant-local copy created
Step 3:  Make changes
Step 4:  Save
         → Assert: changes saved to copy, original unchanged
```

### 19D · Update Review

```
Step 1:  Navigate to /library/updates
         → Assert: pending updates listed (if template pack has new version)
Step 2:  Click an update
         → Assert: diff view: what changed
Step 3:  Accept → updated
Step 4:  Reject → keeps current version
Step 5:  Defer → review later
```

### 19E · Pack Builder

```
Step 1:  Navigate to /library/pack-builder
Step 2:  Create custom pack: name, description
Step 3:  Add items to pack
Step 4:  Save pack
         → Assert: custom pack visible in library
```

### 19F · Platform Admin View

```
Step 1:  Login as P01 (Platform Admin)
Step 2:  Navigate to library
         → Assert: sees all packs across all tenants
         → Assert: management options available (create, version, publish)
```

**Test count: 20** (browse + activate + copy-on-write + updates + pack builder + admin)

---

## Module 20 — Reporting

### 20A · Report Catalog

```
Step 1:  Login as P02 (Tenant Admin)
Step 2:  Navigate to /reports
         → Assert: report catalog loads
         → Assert: categories visible (Risk, Compliance, Access, Audit)
Step 3:  Search reports
Step 4:  Click a report
         → Assert: report detail/config page
```

### 20B · Run Report

```
Step 1:  Select "SoD Violations Summary"
Step 2:  Set parameters: date range = last 30 days, scope = All Users
Step 3:  Click "Generate" / "Run"
         → Assert: report executes
         → Assert: results displayed (table and/or chart)
Step 4:  Drill-down: click a row
         → Assert: navigates to detail view
```

### 20C · Export

```
Step 1:  Click "Export → CSV"
         → Assert: CSV file downloads with report data
Step 2:  Click "Export → PDF"
         → Assert: PDF file downloads
Step 3:  Verify file contents match on-screen data
```

### 20D · Multiple Report Types

Run each of these and verify results render:
```
- SoD Violations Summary
- User Access Review
- Role Usage Analysis
- Certification Status
- Firefighter Activity Log
- Risk Heatmap
- KRI Dashboard
- Audit Findings Summary
- Control Testing Results
- Vendor Risk Overview
```

### 20E · RBAC on Reports

```
Step 1:  Login as P08 (Business User)
         → Assert: sees only reports allowed for their role
Step 2:  Login as P09 (External Auditor)
         → Assert: sees audit-focused reports only
Step 3:  Login as P01 (Platform Admin)
         → Assert: sees all reports
```

**Test count: 25** (catalog + run + export + report types + RBAC)

---

## Module 21 — Security Controls (SAP-Specific)

### 21A · Controls Dashboard

```
Step 1:  Login as P03 (CISO)
Step 2:  Navigate to /security-controls
         → Assert: dashboard loads with risk status overview
         → Assert: Green/Yellow/Red rating distribution
```

### 21B · Controls List

```
Step 1:  Navigate to /security-controls/list
         → Assert: all controls listed
Step 2:  Filter by category (Authentication, Basis Security, etc.)
Step 3:  Filter by business area
Step 4:  Click a control → detail page
         → Assert: control config, value mappings, evaluation history
```

### 21C · Create Control

```
Step 1:  Click "Create Control"
Step 2:  Fill: control_name="Password History Policy"
         business_area="IT General"
         control_type="Preventive"
         category="General Authentication"
         description="Enforce 12 password history to prevent reuse"
Step 3:  Save → control created
```

### 21D · Evaluate Controls

```
Step 1:  Navigate to /security-controls/evaluate
Step 2:  Select system/client
Step 3:  Click "Evaluate"
         → Assert: batch evaluation runs
         → Assert: each control gets Green/Yellow/Red rating
Step 4:  View results
         → Assert: parameter values from SAP shown
```

### 21E · Import Controls

```
Step 1:  Navigate to /security-controls/import
Step 2:  Download import template
         → Assert: CSV/JSON template downloads
Step 3:  Fill template with control data
Step 4:  Upload
         → Assert: validation runs
         → Assert: controls imported
```

**Test count: 20** (dashboard + list + create + evaluate + import)

---

## Module 22 — Mass Administration & Provisioning

### 22A · Provisioning Dashboard

```
Step 1:  Login as P06 (IT Security Admin) or P02 (Tenant Admin)
Step 2:  Navigate to /provisioning
         → Assert: connector status cards visible
         → Assert: task queue shown
Step 3:  View connector list
         → Assert: configured connectors with status (connected/disconnected)
Step 4:  Click connector → detail
         → Assert: connection parameters, last sync, health status
Step 5:  Click "Test Connection"
         → Assert: connection test runs, result shown
```

### 22B · Mass Admin — Bulk Job

```
Step 1:  Navigate to /settings/mass-admin
Step 2:  Click "Create Bulk Job"
Step 3:  Select operation: "Role Assignment"
Step 4:  Upload CSV: 10 users × role ROLE_FI_VIEWER
Step 5:  Preview
         → Assert: 10 items listed with user + role
Step 6:  Execute
         → Assert: progress bar
         → Assert: results: 9 succeeded, 1 failed (e.g., user not found)
Step 7:  View failure details
         → Assert: specific error for the failed item
Step 8:  Retry failed item
```

### 22C · Mass Admin — Job History

```
Step 1:  View job history
         → Assert: past jobs listed with status, date, result counts
Step 2:  Click a past job
         → Assert: full details, per-item results
```

### 22D · Cancel Running Job

```
Step 1:  Start a large bulk job
Step 2:  Click "Cancel"
         → Assert: job stopped, partial results shown
```

**Test count: 20** (provisioning + bulk jobs + history + cancel)

---

## Module 23 — System Configuration

### 23A · Platform Config

```
Step 1:  Login as P01 (Platform Admin)
Step 2:  Navigate to /settings (or /config)
         → Assert: system settings page loads
Step 3:  View session timeout → current value shown
Step 4:  Change to 15 minutes → Save
         → Assert: toast "Setting saved"
Step 5:  View password policy → current values
Step 6:  Change min length to 12 → Save
Step 7:  View rate limits → current values
Step 8:  Verify audit trail captures config changes
```

### 23B · Config Effects Verification

```
Step 1:  After changing session timeout to 15 min:
Step 2:  Login as P08
Step 3:  Wait 15+ minutes
         → Assert: session expires (redirect to login)

Step 4:  After changing password min length to 12:
Step 5:  Try to change password to "short1!"
         → Assert: validation error — password too short
Step 6:  Change to "LongEnough123!"
         → Assert: password changed successfully
```

### 23C · Tenant vs Platform Settings

```
Step 1:  Login as P02 (Tenant Admin)
Step 2:  Navigate to tenant settings
         → Assert: tenant-specific settings editable
Step 3:  Platform-level security settings
         → Assert: shown as read-only (cannot override platform admin)
```

### 23D · SMTP Configuration

```
Step 1:  Navigate to /settings/email
Step 2:  Fill SMTP: host, port, username, password
Step 3:  Save → Assert: saved
Step 4:  Click "Send Test Email"
         → Assert: test email sent, result shown
```

### 23E · Approver Management

```
Step 1:  Navigate to /settings/approvers
Step 2:  Create approver: user=qa_line_manager, scope="Finance dept"
Step 3:  Edit approver
Step 4:  Set OOO: start=2026-11-01, end=2026-11-05, delegate=qa_compliance
Step 5:  Toggle availability off/on
Step 6:  Delete approver
```

**Test count: 25** (config CRUD + effects + tenant isolation + SMTP + approvers)

---

## Module 24 — Cross-Module E2E Workflows

These are the **crown jewels** — they prove the product works as a system, not just as individual features.

### 24A · Full Access Lifecycle

```
Step 1:   (P08) Submit request for ROLE_FI_POSTER
Step 2:   System detects SoD conflict with existing ROLE_FI_VIEWER
Step 3:   → Assert: SoD warning shown with rule ID and severity
Step 4:   (P08) Submit anyway with risk justification
Step 5:   (P07) Review request, see SoD warning
Step 6:   (P07) Approve with risk acceptance
Step 7:   → Assert: request status = Approved
Step 8:   Provisioning executes → role assigned
Step 9:   (P06) Check /risk/violations
Step 10:  → Assert: new SoD violation for P08 logged
Step 11:  (P06) Apply mitigation control
Step 12:  → Assert: violation status → Mitigated
Step 13:  (P04) Launch certification campaign covering P08
Step 14:  (P07) Review P08's access — see the risky role
Step 15:  (P07) Revoke ROLE_FI_POSTER
Step 16:  → Assert: role removed from P08
Step 17:  → Assert: SoD violation resolved
Step 18:  Full audit trail verifiable at every step
```

### 24B · Employee Lifecycle (Joiner → Mover → Leaver)

```
Step 1:   (P13) New hire in Finance department
Step 2:   JML joiner policy fires → birthright roles assigned
Step 3:   → Assert: user gets ROLE_FI_VIEWER, ROLE_HR_SELF_SERVICE
Step 4:   (P08-equiv) User submits additional access request for ROLE_FI_POSTER
Step 5:   (P07) Approves
Step 6:   → Assert: user now has 3 roles
Step 7:   (P13) Employee transfers to Marketing (mover event)
Step 8:   → Assert: Finance roles queued for removal
Step 9:   → Assert: Marketing birthright roles queued for grant
Step 10:  (P07) Approves role changes
Step 11:  → Assert: Finance roles removed, Marketing roles added
Step 12:  (P13) Employee resigns (leaver event)
Step 13:  → Assert: ALL roles queued for revocation
Step 14:  Execute revocation
Step 15:  → Assert: all roles removed, account deactivated
Step 16:  → Assert: user cannot log in
Step 17:  → Assert: certification campaigns for this user auto-closed
```

### 24C · Fraud → Investigation → Audit

```
Step 1:   Fraud rule triggers alert (seeded data)
Step 2:   (P06) Views alert in fraud inbox
Step 3:   (P06) Opens case from alert
Step 4:   (P06) Assigns investigator, adds notes
Step 5:   (P06) Links to whistleblower report (if related)
Step 6:   (P19) Internal Auditor creates audit engagement
Step 7:   (P19) Adds finding referencing the fraud case
Step 8:   (P19) Management response recorded
Step 9:   (P19) Action plan created and tracked
Step 10:  Full audit trail from initial alert to resolution
```

### 24D · Emergency Access → CCM → Audit

```
Step 1:   (P06) Requests firefighter access
Step 2:   (P11) Approves
Step 3:   (P17) Starts FF session
Step 4:   (P17) Performs actions during session
Step 5:   (P17) Ends session
Step 6:   (P12) Controller reviews session log
Step 7:   CCM rule detects FF activity → exception flagged
Step 8:   (P03) CISO reviews CCM exception
Step 9:   (P19) Internal auditor includes in quarterly audit
Step 10:  Complete chain documented
```

### 24E · Risk Discovery → Response → KRI → Incident

```
Step 1:   (P05) Identifies new risk "Cloud vendor data breach"
Step 2:   (P05) Conducts risk assessment: L=4, I=5
Step 3:   → Assert: appears on heatmap in "Extreme" zone
Step 4:   (P05) Creates response plan: "Migrate to multi-cloud"
Step 5:   (P05) Sets up KRI: "Monthly vendor security score"
Step 6:   (P05) Records KRI measurement: 85 (Normal)
Step 7:   Next month: KRI = 62 (Warning)
Step 8:   Next month: KRI = 45 (Breach!)
Step 9:   → Assert: alert triggered
Step 10:  Actual incident occurs → incident reported
Step 11:  Incident linked to risk and KRI
Step 12:  Response plan activated
Step 13:  (P20) TPRM vendor assessment triggered
Step 14:  Full chain documented
```

### 24F · BCM Full Cycle

```
Step 1:   (P05) Create BIA for "Payment Processing" — RTO=4h, RPO=1h
Step 2:   (P05) Create BCM plan "Payment Systems DR"
Step 3:   (P05) Create exercise and run it
Step 4:   Exercise reveals gap: actual recovery = 6h (exceeds 4h RTO)
Step 5:   Update plan with improvements
Step 6:   Real incident → activate plan
Step 7:   Track recovery steps
Step 8:   Recovery achieved in 3.5h (within RTO)
Step 9:   Close activation, record lessons learned
```

### 24G · Survey → Compliance Action

```
Step 1:   (P02) Create security awareness survey
Step 2:   Distribute to all business users
Step 3:   Users complete survey
Step 4:   Analytics show 30% failed phishing question
Step 5:   → Compliance action: mandatory training
Step 6:   Follow-up survey after training
Step 7:   Pass rate improves to 85%
```

### 24H · Template Library → Working Rules

```
Step 1:   (P02) Browse template library
Step 2:   Activate "SoD Rules — Finance" pack
Step 3:   → Assert: SoD rules copied to tenant
Step 4:   Run ARA analysis
Step 5:   → Assert: new violations detected using activated rules
Step 6:   Edit an activated rule (copy-on-write)
Step 7:   New template version published
Step 8:   Update review: accept/reject/defer
```

### 24I · Config Change → Effect → Audit

```
Step 1:   (P01) Change session timeout to 10 minutes
Step 2:   → Assert: audit log shows config change
Step 3:   New session times out after 10 minutes
Step 4:   (P01) Change password policy
Step 5:   → Assert: new policy enforced on next password change
Step 6:   (P19) Audit log shows all config changes with before/after values
```

### 24J · Multi-Module Dashboard Sync

```
Step 1:   Create access request → dashboard "Open Requests" count increments
Step 2:   Approve request → "Pending Approvals" count decrements
Step 3:   Run ARA → "Active Violations" count updates
Step 4:   Launch certification → "Active Campaigns" count increments
Step 5:   Start FF session → "Active FF Sessions" count increments
Step 6:   All dashboard widgets reflect real-time data
```

**Test count: 20** (10 full E2E chains with multi-step verification)

---

## Grand Total Summary

| Module | Tests | Priority Split |
|--------|-------|----------------|
| 1. Authentication & Session | 40 | 30 P0 · 10 P1 |
| 2. Dashboard & Navigation | 30 | 20 P0 · 10 P1 |
| 3. User Management | 30 | 20 P0 · 10 P1 |
| 4. Access Requests | 130 | 90 P0 · 30 P1 · 10 P2 |
| 5. Certification | 40 | 30 P0 · 10 P1 |
| 6. SoD Rules | 25 | 15 P0 · 10 P1 |
| 7. ARA (Risk Analysis) | 30 | 20 P0 · 10 P1 |
| 8. Firefighter | 60 | 40 P0 · 15 P1 · 5 P2 |
| 9. Risk Management | 60 | 30 P0 · 20 P1 · 10 P2 |
| 10. Process Control | 40 | 20 P0 · 15 P1 · 5 P2 |
| 11. Audit Management | 40 | 20 P0 · 15 P1 · 5 P2 |
| 12. JML | 30 | 20 P0 · 10 P1 |
| 13. Identity Correlation | 15 | 5 P0 · 10 P1 |
| 14. TPRM | 30 | 10 P0 · 15 P1 · 5 P2 |
| 15. Fraud Detection | 30 | 20 P0 · 10 P1 |
| 16. BCM | 25 | 10 P0 · 10 P1 · 5 P2 |
| 17. Whistleblower | 30 | 25 P0 · 5 P1 |
| 18. Surveys | 20 | 10 P0 · 10 P1 |
| 19. Template Library | 20 | 5 P0 · 10 P1 · 5 P2 |
| 20. Reporting | 25 | 10 P0 · 10 P1 · 5 P2 |
| 21. Security Controls | 20 | 10 P0 · 10 P1 |
| 22. Mass Admin / Provisioning | 20 | 10 P0 · 10 P1 |
| 23. System Configuration | 25 | 10 P0 · 10 P1 · 5 P2 |
| 24. Cross-Module E2E Workflows | 20 | 20 P0 |
| **Subtotal** | **835** | **500 P0 · 280 P1 · 55 P2** |
| **RBAC Denial Tests** (each P0 × 3 personas) | 400 | all P1 |
| **Negative/Validation** (each form × 5 scenarios) | 250 | all P1 |
| **State Machine Invalid Transitions** | 150 | all P2 |
| **Pagination & Performance** | 50 | all P2 |
| **Dark Mode per Page** | 100 | all P2 |
| **Concurrency / Race Conditions** | 50 | all P2 |
| **Missing Multiplier Buffer** | 165 | mixed |
| **GRAND TOTAL** | **2000** | **500 P0 · 930 P1 · 570 P2** |
