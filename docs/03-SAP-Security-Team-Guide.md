# GovernexPlus — SAP Security & GRC Team Guide

**Version:** 2.0 | **Date:** September 2026 | **Audience:** SAP Security Analysts, GRC Consultants | **Classification:** Internal

---

## Table of Contents

1. [Overview: What SAP Security Teams Do in GovernexPlus](#1-overview-what-sap-security-teams-do-in-governexplus)
2. [SoD Rule Management](#2-sod-rule-management)
3. [Risk Intelligence Engine (ARA)](#3-risk-intelligence-engine-ara)
4. [Mitigation Controls](#4-mitigation-controls)
5. [Access Lifecycle Manager (ARM)](#5-access-lifecycle-manager-arm)
6. [Firefighter / Privileged Access Governor (EAM)](#6-firefighter--privileged-access-governor-eam)
7. [Access Certification (UAR)](#7-access-certification-uar)
8. [Role Engineering (Role Design Studio)](#8-role-engineering-role-design-studio)
9. [AI-Assisted Features](#9-ai-assisted-features)
10. [Day-to-Day Workflows](#10-day-to-day-workflows)
11. [Reports for SAP Security Teams](#11-reports-for-sap-security-teams)

---

## 1. Overview: What SAP Security Teams Do in GovernexPlus

GovernexPlus is the operational home for everything your SAP Security and GRC team does. If you are migrating from SAP GRC Access Control 12.0 (or managing GRC processes manually in spreadsheets), GovernexPlus replaces all of those tools with a single, modern platform.

### 1.1 Your Daily Activities in GovernexPlus

As a SAP Security analyst, you will typically perform these activities:

**Daily:**
- Review and action the Approval Inbox (access requests pending security review)
- Monitor open firefighter sessions
- Review new SoD violations flagged overnight by the scheduled Risk Intelligence Engine run
- Action AI-generated attention items

**Weekly:**
- Review access certification campaign progress and follow up with overdue reviewers
- Review mitigation control monitoring results and flag ineffective controls
- Run what-if simulations for pending high-risk access requests
- Review role drift alerts

**Monthly:**
- Prepare SoD violation summary for management
- Review and update compensating control assignments
- Run ad-hoc Risk Intelligence Engine analysis for specific user populations or newly connected systems
- Review and purge firefighter session logs after controller sign-off

**Quarterly:**
- Launch and manage access certification campaigns
- Review and update the SoD rule library (new Z-transactions, regulatory changes)
- Conduct role landscape review (redundant roles, over-permissioned roles)
- Contribute to GRC health score reporting

### 1.2 Your Role in the Broader GRC Program

The AC pillar you manage feeds all other pillars:

- **SoD violations → RM**: Unmitigated violations are reflected in the risk register as access risk items
- **SoD violations → PC**: Confirmed violations can be linked to control deficiencies, which trigger remediation workflows
- **SoD violations → AM**: Audit findings can reference specific violations as supporting evidence
- **Firefighter sessions → AM**: Session logs are available to auditors as audit evidence
- **Certification decisions → AM**: Revocation decisions and certification campaign results are audit evidence

Understanding these connections makes your work more impactful — when you resolve a SoD violation, you are simultaneously reducing the organization's risk exposure, improving its control posture, and potentially closing an audit finding.

### 1.3 GovernexPlus vs. SAP GRC AC — Key Differences

| Capability | SAP GRC AC 12.0 | GovernexPlus |
|---|---|---|
| Risk scoring | Static rule match score | Usage-aware (frequency + recency modifier) |
| Interface | SAP Web Dynpro (dated) | Modern React SPA |
| Rule library | Import-only, no built-in library | 128 built-in rules + custom |
| Remediation | Manual | AI-recommended |
| Role design | No inline SoD | Inline SoD check during design |
| Reporting | Crystal Reports | Real-time dashboards + PDF/PPTX/Excel |
| Multi-system | SAP only | SAP + Azure AD + Okta + LDAP |
| Firefighter | FIDO (Firefighter) | Privileged Access Governor with live monitoring + AI analysis |
| Certification | UAR module | UAR with AI recommendations |
| API | Limited OData | 938 REST endpoints |

---

## 2. SoD Rule Management

### 2.1 Understanding the Built-in 128-Rule Library

GovernexPlus ships with a comprehensive SoD rule library developed from years of SAP security experience, regulatory guidance (SOX, GDPR), and SAP's own GRC best practices.

**Accessing the rule library:**

Navigate to **Risk → SoD Rule Library**

[Screenshot: SoD Rule Library with module filter tabs, severity filter, and rule cards]

**Rule structure:**

Each rule defines a conflict between two functions (Function A and Function B). A user violates the rule when they have access that can perform both Function A and Function B — either through a single role or through a combination of roles.

```
Rule: FI-012 — Post and Approve Vendor Invoices
Severity: Critical
Function A: Post Vendor Invoices
  T-codes: FB60, FB65, MIRO, FBR2
  Auth objects: F_BKPF_BUK (ACTVT=01), F_BKPF_KOA (KOART=K)
Function B: Approve/Release Vendor Invoices
  T-codes: FBW2, FBW3, MRBR
  Auth objects: M_RECH_WRK (ACTVT=23)
Business rationale: Prevents a single user from creating and approving fictitious vendor
invoices, which would enable embezzlement without detection.
Regulatory mapping: SOX Section 302/404, COSO Principle 10
```

**Module breakdown:**

| Module | Rule Range | Example Rules |
|---|---|---|
| **FI** — Financial Accounting | FI-001 to FI-022 | Post + approve invoices, create + release payment runs, maintain bank master + post payments |
| **MM** — Materials Management | MM-001 to MM-018 | Create + approve POs, receive goods + process invoice, maintain vendor master + create POs |
| **SD** — Sales & Distribution | SD-001 to SD-014 | Create + ship orders, billing + credit note approval, customer credit limit maintenance + billing |
| **HR** — Human Resources | HR-001 to HR-016 | Maintain payroll data + run payroll, create employees + assign pay, access PA0008 + run payroll |
| **BA** — Basis Administration | BA-001 to BA-012 | User maintenance + role assignment, debug production + modify data, CATT + transport |
| **TR** — Treasury | TR-001 to TR-010 | Create + confirm treasury deals, payment execution + payment release |
| **AA** — Asset Accounting | AA-001 to AA-008 | Create assets + post depreciation, retire assets + post acquisition |
| **WM** — Warehouse Management | WM-001 to WM-008 | Inventory adjustments + goods issue posting |
| **QM** — Quality Management | QM-001 to QM-006 | Usage decision + goods posting |
| **PM** — Plant Maintenance | PM-001 to PM-006 | Work order creation + settlement |
| **PS** — Project System | PS-001 to PS-005 | Project creation + cost posting |
| **XP** — Cross-Process | XP-001 to XP-003 | Basis admin + financial posting (high-risk cross-module) |

**Severity levels and their meaning:**

| Severity | Description | Recommended Action |
|---|---|---|
| **Critical** | Direct fraud enablement; regulatory-mandated separation | Remediate within 30 days; compensating control required immediately |
| **High** | Significant fraud risk; strong regulatory guidance | Remediate within 60 days; compensating control required |
| **Medium** | Elevated risk; commonly mitigated in practice | Remediate or mitigate within 90 days |
| **Low** | Technical violation with limited business impact | Document and accept, or remediate in next access review |

### 2.2 Creating Custom Rules (Z-Transactions)

Your organization likely has custom SAP developments (Z-transactions) that represent the same business risks as standard SAP transactions. GovernexPlus supports custom rule creation for any Z-transaction or custom authorization object.

**Step 1: Identify the conflict**

Before creating a rule, clearly define:
- What is Function A? (what business activity can be performed)
- What is Function B? (what business activity conflicts with A)
- What is the business risk if one user performs both?

**Step 2: Create the rule via UI**

1. Navigate to **Risk → SoD Rule Library → Create Rule**
2. Complete the rule definition form:

| Field | Example Value | Notes |
|---|---|---|
| Rule ID | Z-FI-001 | Z- prefix for custom rules |
| Rule Name | Post + Approve Custom Invoices | Plain-language name |
| Business Process | Accounts Payable | Module/process this protects |
| Severity | Critical | Critical/High/Medium/Low |
| Status | Active | Active/Draft/Disabled |
| Function A Name | Post Custom Invoices | |
| Function A T-codes | ZAP001, ZAP002 | Comma-separated |
| Function A Auth Objects | Z_AP_POST | SAP auth object name |
| Function A Field Values | ACTVT=01 | Auth object field values |
| Function B Name | Approve Custom Invoices | |
| Function B T-codes | ZAP010, ZAP011 | |
| Function B Auth Objects | Z_AP_APPR | |
| Regulatory Mapping | SOX 302, 404 | |
| Remediation Guidance | Remove Z_AP_APPR from AP clerks | |

3. Click **Save as Draft**
4. Have a second security analyst review and approve
5. Change status to **Active** to include in Risk Intelligence Engine runs

[Screenshot: Create Custom SoD Rule form with Function A/B panels and T-code entry]

**Step 3: Verify the rule**

After activation, run an on-demand Risk Intelligence Engine analysis for a known user who holds both functions to confirm the rule fires correctly:

```
1. Navigate to Risk Intelligence Engine → Run Analysis → Single User
2. Enter a user you know has both T-codes
3. Run analysis
4. Verify Z-FI-001 appears in the violations
```

### 2.3 Enabling and Disabling Rules Per Tenant

In multi-tenant or multi-landscape environments, some rules may not be relevant to certain system configurations.

**Disable a rule for specific system types:**

```
Navigate to Risk → SoD Rule Library → [Rule] → Settings
Toggle "Active in System Type" to enable/disable per:
  - ECC 6.0 / S/4HANA 1909 / S/4HANA 2023
  - Production / Development / Test
```

**Disable a rule entirely (for this tenant):**

```
Risk → SoD Rule Library → [Rule] → Status → Set to "Disabled"
```

> **Audit trail note**: Every rule status change is logged with the user who made the change and the timestamp. Disabling Critical-severity rules requires a mandatory business justification entry.

### 2.4 Importing Rules from SAP GRC (Excel/CSV)

If migrating from SAP GRC AC 12.0, use the rule import function to bring your custom rules across:

**Export from SAP GRC AC:**
1. In SAP GRC, navigate to Access Control → Rule Setup → Maintain Functions
2. Export the rule library as Excel

**Import into GovernexPlus:**
1. Navigate to **Risk → SoD Rule Library → Import**
2. Upload the Excel file
3. The import wizard maps SAP GRC fields to GovernexPlus fields:
   - SAP GRC Risk → GovernexPlus Rule
   - SAP GRC Function → GovernexPlus Function A/B
   - SAP GRC Permission → GovernexPlus T-codes/Auth Objects
4. Review the mapping and correct any unmapped fields
5. The import skips rules already present (matched by Rule ID) — safe to re-run
6. Review and activate imported rules

[Screenshot: Rule import wizard with field mapping and preview of rules to be created]

### 2.5 Rule Versioning

GovernexPlus maintains a version history for every rule:

- Every change to a rule (T-code list, auth object, severity, status) creates a new version
- Previous versions are preserved for audit trail
- You can view the diff between any two versions
- If a rule change causes unexpected violation count changes, you can review what changed

**Viewing rule history:**

```
Risk → SoD Rule Library → [Rule] → History tab
```

---

## 3. Risk Intelligence Engine (ARA)

### 3.1 How the Risk Intelligence Engine Works

The Risk Intelligence Engine evaluates every user's effective access against all active SoD rules. "Effective access" means the union of all permissions granted through all roles assigned to the user — not just direct assignments.

**The Risk Intelligence Engine algorithm:**

```
For each User:
  1. Resolve effective access:
     - Collect all assigned roles (direct + indirect)
     - Expand each role to its authorization objects
     - Expand auth objects to T-codes (via transaction auth check tables)
  2. For each active SoD rule:
     - Check if user's effective access covers Function A
     - Check if user's effective access covers Function B
     - If both: violation detected
  3. Calculate risk score:
     - Base score from rule severity (Critical=100, High=75, Medium=50, Low=25)
     - Context modifier (+/- based on user's org unit, system criticality, job function)
     - Usage modifier (-30 to +30 based on how recently/frequently user executed the transactions)
  4. Persist violation with full metadata
```

### 3.2 Running User-Level Analysis

**Single user analysis:**

1. Navigate to **Risk → Risk Intelligence Engine → Analyze User**
2. Enter username or search by name/department
3. Select systems to analyze (all connected systems, or specific)
4. Select rule set (all rules, or specific modules)
5. Click **Analyze**

Results appear within 30–60 seconds for a typical user.

**Reading the user analysis results:**

[Screenshot: User Risk Intelligence Engine results showing violation cards with severity badges, rule details, and usage context]

The results page shows:
- **Violation summary**: Total violations by severity (Critical/High/Medium/Low)
- **Violation cards**: Each card shows:
  - Rule ID and name
  - Severity badge
  - Function A evidence (what roles/T-codes give this function)
  - Function B evidence (what roles/T-codes give this function)
  - Risk score (base + context + usage modifiers)
  - Usage statistics (last used dates, execution frequency)
  - Remediation recommendation (AI-generated)
- **Risk timeline**: Historical violation trend for this user
- **Comparison**: How this user's risk compares to peers in the same department

**Exporting user analysis:**

```
Click "Export" → Choose format: PDF, Excel, or JSON
```

### 3.3 Running Role-Level Analysis

Role-level analysis identifies roles that are inherently risky — containing permissions for both Function A and Function B of a rule within a single role.

**Why this matters**: A role-level violation means that ANY user assigned this role will have a SoD violation, regardless of their other roles. These are the highest-priority items to remediate because a single role redesign can fix the violation for all users assigned to that role.

1. Navigate to **Risk → Risk Intelligence Engine → Analyze Role**
2. Search for or select a role
3. Click **Analyze**
4. Review intrinsic violations (within the role) vs. contextual violations (requires combining with other roles)

### 3.4 Cross-Role Analysis

Cross-role analysis identifies SoD conflicts that only emerge when specific pairs of roles are held together. This is the most common violation type.

**Example**: Role A grants F_BKPF_BUK with ACTVT=01 (post documents). Role B grants M_RECH_WRK with ACTVT=23 (release invoices). Neither role individually violates a rule. But a user holding both Role A and Role B violates FI-012.

**Running cross-role analysis:**

1. Navigate to **Risk → Risk Intelligence Engine → Cross-Role Analysis**
2. Select role pair(s) to analyze
3. Click **Analyze**
4. Review the violation matrix (which rule fires for which role combination)

**Using cross-role analysis for role design governance:**

Before approving a new role assignment, run cross-role analysis for the target user's existing roles + the proposed new role. This is exactly what the inline SoD check in the Access Lifecycle Manager module does automatically.

### 3.5 What-If Simulation

The What-If simulator lets you model access changes before making them in SAP. This is essential before approving high-risk access requests.

**What-If: Add a role:**

1. Navigate to **Risk → Risk Intelligence Engine → What-If Simulation** (or access directly from an access request)
2. Select target user
3. Select "Add Role" and choose the role to add
4. Click **Simulate**
5. Review the delta: which new violations appear?

**What-If: Remove a role:**

1. Select target user
2. Select "Remove Role" and choose the role to remove
3. Click **Simulate**
4. Review which violations are resolved by removing this role

**What-If: Role assignment batch:**

Simulate adding or removing multiple roles in a single operation:

1. Upload a CSV with user/role pairs
2. Run batch simulation
3. Download the impact report showing net risk change for each user

[Screenshot: What-If simulation showing before/after violation comparison with delta highlighted]

### 3.6 Understanding Risk Scores

GovernexPlus uses a three-dimensional scoring model:

**Base Score** (from rule severity):
- Critical rule: 100 points
- High rule: 75 points
- Medium rule: 50 points
- Low rule: 25 points

**Context Modifier** (-20 to +20):
- High-sensitivity org unit (Treasury, Payroll): +10
- Critical system (Production, Financial): +10
- Low-sensitivity org unit (Test system, archived entity): -10

**Usage Modifier** (-30 to +30):
- User executed both functions in the last 30 days: +30
- User executed both functions in the last 90 days: +15
- User executed neither function in the last 90 days: -15
- User executed neither function in the last 180 days: -25
- User has never executed either function: -30

**Score ranges and recommended actions:**

| Score Range | Risk Level | Recommended Action |
|---|---|---|
| 80–130 | Critical (Active) | Immediate remediation or immediate compensating control |
| 60–79 | High (Active) | Remediate within 30 days; compensating control required |
| 40–59 | Medium (Active) | Remediate within 60 days or document acceptance |
| 20–39 | Low (Dormant) | Review in next certification cycle |
| 0–19 | Minimal (Dormant) | Document and accept; no active compensating control needed |

### 3.7 Org-Level Risk Ranking

The org-level analysis provides a heat map and ranking of organizational units by aggregate risk exposure.

**Running org-level analysis:**

Navigate to **Risk → Risk Intelligence Engine → Org Analysis**

The system calculates:
- **Total violations**: Count of violations for all users in the org unit
- **Critical violations**: Count of critical violations
- **Average risk score**: Mean violation score for the org unit
- **Risk per user**: Aggregate risk / headcount (normalized comparison metric)
- **Trend**: Change vs. prior period

**Use cases:**
- Prioritize remediation effort by focusing on highest-risk org units first
- Report to business unit leadership on their team's access risk exposure
- Justify audit scope selection (highest-risk units get more audit attention)

[Screenshot: Org-level risk heatmap with company code / department / team hierarchy and risk scores]

### 3.8 Batch/Scheduled Analysis

**Scheduling automated Risk Intelligence Engine runs:**

1. Navigate to **Risk → Risk Intelligence Engine → Schedule**
2. Configure the schedule:
   - **Frequency**: Daily / Weekly / Monthly
   - **Time**: Off-peak hours (recommended: 2:00 AM tenant timezone)
   - **Scope**: All users / specific org units / users with recent role changes
   - **Systems**: All connected systems / specific systems
   - **Notification**: Email report to SAP Security team when complete

**Triggering a manual batch run:**

```bash
POST /api/ara/batch-analysis
{
  "scope": "all",
  "systems": ["PRD", "PRD2"],
  "notify_on_complete": ["sap-security@acme.com"]
}
```

**Monitoring batch progress:**

Navigate to **Risk → Risk Intelligence Engine → Analysis History** to see:
- Start time and current status
- Percentage complete (users processed / total)
- New violations detected vs. prior run
- Violations resolved vs. prior run
- Estimated completion time

---

## 4. Mitigation Controls

### 4.1 Purpose of Compensating Controls

When a SoD violation cannot be immediately remediated through role redesign (e.g., the business genuinely requires one person to perform both functions), a compensating control is the alternative. A compensating control is a monitoring activity that detects if the combined access is being misused.

**Example**: A small company's sole accountant must both post and approve invoices because there is no second person. The compensating control might be: "CFO reviews all vendor invoices above $10,000 monthly, comparing posted invoices to approved purchase orders."

GovernexPlus formalizes this by linking compensating controls to specific violations, tracking their effectiveness, and surfacing them in the Process Control pillar as monitored controls.

### 4.2 Creating a Compensating Control

1. Navigate to **Risk → Mitigation Controls → New Control**
2. Complete the control definition:

| Field | Example | Notes |
|---|---|---|
| Control ID | MC-FI-012-001 | Auto-generated or manual |
| Control Name | CFO Invoice Review | Descriptive name |
| Linked Violation Rule | FI-012 | The SoD rule being mitigated |
| Control Description | CFO reviews all vendor invoices... | Detailed description of what the control does |
| Control Type | Detective | Preventive / Detective / Corrective |
| Control Frequency | Monthly | How often performed |
| Control Owner | CFO | Person responsible for performing |
| Evidence Required | Invoice approval emails | What evidence of control execution |
| Effectiveness Criteria | All invoices reviewed, no unexplained variances | What constitutes effective control |

3. Click **Save**

### 4.3 Assigning Controls to Violations

After creating a control, assign it to the specific users/violations it covers:

1. Navigate to **Risk → Risk Intelligence Engine → [Violation]**
2. Click **Assign Mitigation Control**
3. Search for and select the control
4. Specify the coverage scope:
   - This user only
   - All users with this rule violation
   - This rule violation in this system
   - This rule violation across all systems
5. Set the control assignment expiry (recommend: 12 months, then re-evaluate)
6. Add approval notes (documenting business justification for accepting the risk)
7. Submit for approval (security manager or risk manager sign-off required)

[Screenshot: Violation detail page with Assign Mitigation panel showing control search and coverage scope]

### 4.4 Monitoring Frequency Setup

GovernexPlus can automatically remind control owners to perform and document their controls:

1. Navigate to **Risk → Mitigation Controls → [Control] → Monitoring Schedule**
2. Configure:
   - **Frequency**: Daily / Weekly / Monthly / Quarterly
   - **Reminder days in advance**: 7 days before due
   - **Escalation**: If not documented within 5 days of due date, escalate to control owner's manager
   - **Evidence requirements**: What the control owner must submit

When a monitoring cycle is due:
- Control owner receives email reminder
- Action item appears in their GovernexPlus dashboard
- Owner documents the control execution (attach evidence, provide narrative)
- Security admin reviews and approves the documentation
- Status updated to "Effective" or "Ineffective"

### 4.5 Effectiveness Testing

Periodically, compensating controls must be formally tested to confirm they are actually preventing or detecting misuse:

1. Navigate to **Risk → Mitigation Controls → [Control] → Test Control**
2. Define the test:
   - Test period
   - Population to test (all transactions covered by the control)
   - Test methodology (inspect evidence, re-perform, inquiry)
3. Execute the test and document results
4. Conclusion: **Effective** / **Partially Effective** / **Ineffective**

If the control is assessed **Ineffective**:
- The linked SoD violation's risk score is automatically elevated
- The risk manager is notified
- The linked risk record in the RM pillar is flagged for reassessment
- A deficiency record is created in the PC pillar

### 4.6 Unified Mitigation Register (XL-C)

The unified mitigation register (Cross-Module Link C) provides a single view of all mitigated violations:

Navigate to **Risk → Mitigation Controls → Register**

The register shows:
- Every active mitigation control
- The violation rules covered
- Users covered by each control
- Last monitoring execution date and result
- Control effectiveness trend
- Link to the PC control record (if the same control is formally tested in PC)
- Link to the RM risk record that this mitigates

This cross-module view is essential for annual SOX certification — you can demonstrate that every accepted SoD violation has a formal, tested compensating control.

---

## 5. Access Lifecycle Manager (ARM)

### 5.1 Your Role in the Approval Workflow

As a security admin, you typically appear in the approval workflow as the **Security Review** stage — required when a request contains items that trigger SoD violations.

The standard workflow for SAP role requests:

```
User Request → Manager Approval → Role Owner Approval → Security Review (your step) → Provisioning
```

Security review is automatically triggered when:
- The requested role(s) would create a Critical or High SoD violation
- The request is for a sensitive role (configurable sensitivity flag on roles)
- The requesting user already has a Critical unmitigated violation
- The request is for a firefighter ID

### 5.2 Processing the Approval Inbox

**Accessing your inbox:**

Navigate to **Access Requests → Approval Inbox**

[Screenshot: Approval inbox with request cards showing requestor, items requested, risk level badge, and action buttons]

**Inbox filters:**

- **My Pending**: Requests awaiting your specific approval
- **Security Review**: All requests pending any security team member's review
- **Overdue**: Requests past their SLA
- **Escalated to Me**: Requests escalated from another approver

**Reviewing an access request:**

1. Click on a request to open the detail view
2. Review:
   - **Requestor information**: Name, department, manager, current role assignments
   - **Requested items**: Each role or access item requested, with system and justification
   - **Inline SoD analysis**: The risk analysis run at submission time showing what violations the request would create
   - **Business justification**: Free-text entered by requestor
   - **Prior request history**: Has this user requested similar access before?
   - **Manager comment**: What the manager noted when approving
3. Options:
   - **Approve**: Access is granted as requested
   - **Approve with Condition**: Approve but require a compensating control to be set up
   - **Request More Information**: Send back to requestor with a question (does not reset the request, just adds a comment thread)
   - **Reject**: Deny the request with mandatory reason
   - **Escalate**: Route to another security team member or manager

[Screenshot: Access request detail page with inline SoD analysis panel showing violation preview]

### 5.3 Inline Risk Review During Approval

The inline SoD analysis is the most powerful tool in the approval flow. It shows you exactly what violations would be created if you approve the request.

**Reading the inline risk analysis:**

```
Request: Assign role MM60 to John Smith

Current violations (before approval): 2 Medium
New violations if approved:
  [CRITICAL] FI-012: Post and Approve Vendor Invoices
    - Function A (Post): Already held via role FI_AP_CLERK
    - Function B (Approve): Would be granted via new role MM60
    - Usage context: John executed FB60 on 47 occasions in last 90 days
    - Risk score: 118 (Critical active)
    Recommendation: Do not approve. Discuss with manager whether AP posting
    function should be removed from John's profile instead.

  [HIGH] FI-018: Vendor Master Maintenance + Payment Posting
    - New violation created by combination of existing roles + MM60
    - Usage context: Vendor master changes: 0 in last 180 days
    - Risk score: 65 (High dormant)
    Recommendation: Can be mitigated with monthly CFO payment review.
```

**Decision framework for inline violations:**

| Violation Type | Recommended Response |
|---|---|
| Critical, user is active in both functions | Reject the request; discuss role redesign with manager |
| Critical, user is dormant in one function | Consider removing the dormant role instead of denying new request |
| High, business necessity confirmed | Approve with condition: compensating control required |
| Medium, no business necessity clear | Request clarification from requestor/manager |
| Medium, business necessity confirmed | Approve and document; schedule review in next certification |

### 5.4 Requiring Mitigation Before Approval

For High-severity violations where business necessity is confirmed:

1. In the request detail, click **Approve with Condition**
2. Select **Require Mitigation Control**
3. Either:
   - Select an existing mitigation control (if one already covers this rule)
   - Create a new mitigation control (inline creation form)
4. Set the mitigation deadline (control must be activated before access is provisioned)
5. Click **Approve Conditionally**

The system will:
- Send the control creation task to the designated control owner
- Hold the provisioning step until the control is confirmed active
- Automatically provision access once the control is active
- Link the violation to the control in the mitigation register

### 5.5 Configuring Approval Workflows

Workflow configuration is done at the system/role level by a `security_admin` or `tenant_admin`.

**Navigate to: Admin → Workflows → Access Request Workflows**

**Configuring workflow stages:**

Each workflow can have up to 5 stages:

| Stage Parameter | Options | Notes |
|---|---|---|
| Stage type | Manager / Role Owner / Security / Custom | |
| Required | Yes / No | If No, stage is skipped when no approver is matched |
| Auto-approve condition | "Risk score < 30" | Automatically approve if condition met |
| SLA hours | 24 / 48 / 72 | Escalation trigger |
| Escalation target | Manager's manager / Security team | Who gets it if SLA breached |
| Delegation allowed | Yes / No | Can approver delegate? |

**Rule-based workflow routing:**

Different request types can route through different workflows:

```
Rule: IF requested role sensitivity = "Critical" THEN
  Add stage: CISO approval (before provisioning)

Rule: IF requesting user has existing Critical violations THEN
  Add stage: Security review (mandatory, cannot be bypassed)

Rule: IF system = "PRD" AND role = "SAP_ALL" THEN
  Reject automatically with message "SAP_ALL cannot be assigned in production"
```

### 5.6 Shopping Cart Management

The shopping cart allows users to request multiple access items in a single request. As a security reviewer, you see the entire cart and the aggregate SoD analysis for all items combined.

**Cart review best practices:**
- Review the aggregate SoD analysis, not just individual items — a single item might be low risk, but combined with other items in the same cart, it may create Critical violations
- Check for "sneaking" — occasionally requestors add low-risk items to the same cart as high-risk items, hoping the high-risk items are approved along with obvious business needs
- Look at the "net impact" summary at the top: total new violations, total violations resolved (if any items are removals)

---

## 6. Firefighter / Privileged Access Governor (EAM)

### 6.1 Setting Up Firefighter IDs

Before the Privileged Access Governor system can be used, firefighter IDs must be configured in GovernexPlus and in the target SAP system.

**Step 1: Create the firefighter ID in SAP**

In SAP (SU01), create a dialog user for emergency access:
```
User: FF_FIN_ACME         (naming convention: FF_<function>_<org>)
Type: Dialog
Password: <strong, stored in GovernexPlus>
Roles: Assign the broad but specific roles needed for financial emergencies
Lock: YES (locked by default; GovernexPlus unlocks when session approved)
```

**Step 2: Register the firefighter ID in GovernexPlus**

1. Navigate to **Firefighter → Manage IDs → New Firefighter ID**
2. Complete the form:

| Field | Example | Notes |
|---|---|---|
| Firefighter ID | FF_FIN_ACME | Must match SAP username exactly |
| Display Name | Finance Emergency Access | Human-readable description |
| System | PRD | Target SAP system |
| Purpose | Financial period-end emergency access | Business purpose |
| ID Owner | Jane Smith (CFO) | Responsible for usage review |
| Controllers | John Doe, Mary Johnson | Can approve sessions (2+ recommended) |
| Max Session Duration | 4 hours | Maximum time before automatic lockout |
| Reason Codes | PERIOD_END, DATA_FIX, AUDIT_REQUEST | Valid business reasons |
| Notification Email | sap-security@acme.com | Who gets notified of sessions |

3. Click **Save and Test** — GovernexPlus verifies it can reach the user in SAP via RFC

[Screenshot: Firefighter ID configuration form with controller assignment and reason codes]

### 6.2 Reason Code Configuration

Reason codes are the business justifications users must select when requesting firefighter access. Good reason codes:
- Are specific enough to be meaningful
- Cover the actual emergency scenarios your organization faces
- Enable post-session analysis ("was the stated reason code consistent with activity?")

**Creating reason codes:**

Navigate to **Firefighter → Reason Codes → New**

| Code | Description | Auto-approve | Documentation Required |
|---|---|---|---|
| PERIOD_END | Financial period-end processing | No | Closing checklist reference |
| DATA_FIX | Authorized data correction | No | Change request number |
| AUDIT_REQ | Auditor data extraction request | No | Audit engagement reference |
| SYSTEM_ISSUE | System outage response | Yes | Incident ticket number |
| PAYROLL_FIX | Payroll correction (time-sensitive) | No | HR authorization reference |

**Auto-approve reason codes** (SYSTEM_ISSUE in example above): When a user selects this code, the firefighter session is approved automatically without waiting for a controller. Use only for genuine emergencies where delay causes business damage. All auto-approved sessions are flagged for enhanced post-session review.

### 6.3 Approving and Rejecting Requests

**Receiving a firefighter request:**

Controllers receive an email notification and an in-platform alert immediately when a request is submitted. The notification contains:
- Requesting user's name and department
- Firefighter ID requested
- Stated reason code and business justification
- Requested duration
- Approval link (one-click from email, no need to navigate to UI)

**Reviewing the request:**

1. Navigate to **Firefighter → Approval Queue** (or click email link)
2. Review:
   - Is the stated reason code appropriate for the user's role?
   - Is the requested duration reasonable?
   - Has this user requested firefighter access recently? (History tab)
   - Is there an open change request or incident ticket supporting this?
3. Optionally: Request additional information from the user

**Approving:**

```
Click Approve → Optionally add notes → Confirm
```

GovernexPlus immediately:
- Unlocks the firefighter ID in SAP (via RFC)
- Starts the session timer
- Begins capturing session activity
- Notifies the requestor via email

**Rejecting:**

```
Click Reject → Enter mandatory rejection reason → Confirm
```

The rejection reason is visible to the requestor and logged in the audit trail.

### 6.4 Monitoring Live Sessions

During an active firefighter session:

Navigate to **Firefighter → Live Sessions**

[Screenshot: Live Sessions dashboard showing active sessions with T-codes executed counter and session timer]

**Live session view shows:**
- Session start time and elapsed duration
- Remaining time before automatic lockout
- T-codes executed (running count)
- Last T-code executed (real-time via RFC polling)
- High-risk activity alerts (yellow/red flags when sensitive T-codes used)

**High-risk activity alerts:**

The live monitoring engine flags these activities in real-time:
- Table maintenance (SE16, SE16N, SM30, SM31) — data manipulation risk
- User administration (SU01, SU10) — privilege escalation risk
- Authorization management (PFCG) — role modification risk
- Debugging (SA38 + SE37 in debug mode) — data manipulation risk
- Financial postings above $100,000 (configurable threshold) — fraud risk
- Backdated postings (transaction date significantly before system date)

When an alert fires, the controller receives an immediate notification and can:
- Review the activity in context
- Terminate the session immediately if warranted (emergency lockout)

**Terminating a session:**

```
Live Sessions → [Session] → Terminate Session → Enter reason → Confirm
```

GovernexPlus immediately locks the firefighter ID in SAP and logs the termination.

### 6.5 Post-Session Review Workflow

After a firefighter session ends (by timeout, user checkout, or controller termination):

**Controller review (required within 24 hours by default):**

1. Navigate to **Firefighter → Completed Sessions → [Session]**
2. Review:
   - Full T-code execution log with timestamps
   - Documents created, changed, or deleted
   - Compare activity against stated reason code: is the activity consistent?
3. Mark review:
   - **Approved**: Activity was appropriate for stated reason
   - **Concern Raised**: Activity seems inconsistent, requires follow-up
   - **Escalate to Audit**: Session contains activity requiring formal audit review

**AI-assisted session analysis:**

GovernexPlus AI automatically analyzes each completed session and produces a narrative:

```
Session Analysis — FF_FIN_ACME — John Smith — 2026-09-06

Summary: 47 T-code executions over 2h 15m. Activity is broadly consistent
with stated reason code PERIOD_END.

Notable observations:
1. User executed FB01 (General Journal Entry) 3 times. While not the primary
   purpose of PERIOD_END access, journal entries are common during period closing.
   Recommend verification of the specific documents posted.

2. User accessed table PA0008 (Basic Pay) via SE16. This is unusual for
   period-end financial processing and may indicate unauthorized data review.
   Controller should request explanation.

3. No access to vendor master or payment tables detected. Consistent with
   stated purpose.

Risk Assessment: LOW - MEDIUM. Recommend follow-up on PA0008 access.
```

### 6.6 ID Owner Periodic Review

The firefighter ID owner (typically a senior manager or CISO) should review all sessions for their IDs monthly:

1. Navigate to **Firefighter → My Firefighter IDs → [ID] → Session History**
2. Review all sessions for the period
3. Confirm each session was appropriate or raise concerns
4. Sign off on the monthly review

The signed-off monthly review is available as audit evidence in the Audit Management pillar.

---

## 7. Access Certification (UAR)

### 7.1 Creating a Certification Campaign

**Navigate to: Certification → Campaigns → New Campaign**

[Screenshot: Create Campaign form with scope, schedule, and reviewer assignment options]

**Campaign configuration:**

| Setting | Options | Notes |
|---|---|---|
| Campaign Name | "Q3 2026 Financial System Review" | Descriptive |
| Campaign Type | Full / Targeted / System-Specific / Critical-Role | Determines scope |
| Systems | All / Specific list | SAP PRD, Azure AD, etc. |
| User Scope | All active users / Specific departments / Specific job codes | |
| Role Scope | All roles / Sensitive roles only / Roles with SoD risk | |
| Review Method | Manager / Role Owner / Manager + Role Owner | Who reviews |
| AI Recommendations | Enabled / Disabled | AI-generated Certify/Review/Revoke hints |
| Campaign Duration | Start date + End date | Reviewers must complete by end date |
| Reminder Schedule | 7 days before / 3 days before / Day of | Email reminders |
| Escalation | If incomplete at end date: escalate to reviewer's manager | |

**Generating review items:**

After configuration, click **Generate Items**. The system:
1. Queries all connected systems for current access data
2. Applies your scope filters
3. Creates one review item per user-role-system combination
4. Enriches each item with usage data, SoD risk, and AI recommendation
5. Assigns items to reviewers based on org hierarchy (manager) or role catalog (role owner)

Generation typically takes 5–30 minutes depending on scope. You'll receive a notification when complete.

### 7.2 Understanding Review Items

Each review item presents:

```
[User] John Smith | Finance | Manager: Jane Doe
[Role] FI_AP_CLERK (AP Clerk) | System: SAP PRD
[Usage] Last used: 2026-08-15 | Transactions last 90 days: 47
[SoD Risk] 2 Medium violations with this role
[AI Recommendation] CERTIFY
  Rationale: Active user with appropriate usage. SoD violations are currently
  mitigated. No change in job function.

[Reviewer Actions] ◉ Certify  ○ Revoke  ○ Request More Info
[Comment] ___________________
```

**AI recommendation logic:**

| Recommendation | Trigger Conditions |
|---|---|
| CERTIFY | Active usage within 90 days; SoD risk is mitigated or Low; job function matches role purpose |
| REVIEW | No usage in 90+ days; or SoD risk is High/Critical unmitigated; or job function changed recently |
| REVOKE | No usage in 180+ days; or user's manager has changed indicating possible role change; or SoD risk is Critical with no mitigation |

> **Important**: AI recommendations are suggestions, not decisions. The human reviewer remains fully accountable for every certification decision.

### 7.3 Reviewer Workflows

**For managers reviewing their direct reports:**

1. Manager receives email invitation with link to their review items
2. Navigates to **Certification → My Reviews** (or follows email link)
3. Reviews items one by one or in bulk mode:
   - **Bulk certify**: Select multiple items with "CERTIFY" AI recommendation → Bulk Certify → Add comment → Submit
   - **Individual review**: For REVIEW/REVOKE items, review in detail before deciding
4. Progress bar shows completion percentage

**For security admins monitoring campaign progress:**

Navigate to **Certification → Campaigns → [Campaign] → Dashboard**

Campaign dashboard shows:
- Overall completion: XX% complete (YY items of ZZ total)
- Completion by reviewer: sortable table showing each reviewer's progress
- Overdue reviewers: highlighted in red with escalation status
- Certify/Revoke decision breakdown
- Critical access certified vs. revoked trend

**Sending reminders:**

```
Campaign Dashboard → Overdue Reviewers → Select All/Specific → Send Reminder
```

Customizable reminder message with campaign name, deadline, and item count automatically populated.

### 7.4 Revocation Processing

When a reviewer selects **Revoke**:

1. A revocation task is created in the provisioning queue
2. If auto-provisioning is configured (SAP RFC connector active), the role is removed from the user in SAP automatically
3. If manual provisioning is configured, a task is assigned to the provisioning team with deadline
4. The user and their manager receive notification of the revocation
5. The revocation is logged as a decision record (who decided, when, why)
6. The Risk Intelligence Engine violation record for this user is updated (removing violations contributed by this role)

**Bulk revocation processing:**

For campaigns with many revocations:

```
Provisioning Queue → Filter: "Revocation" → Select All → Process Batch
```

### 7.5 Campaign Dashboards and Reporting

**Campaign completion report:**

Available after campaign closes (or at any time during):
- Total items reviewed: N
- Certified: N (X%)
- Revoked: N (X%)
- Decisions pending: N (X%)
- Critical roles certified with SoD violations: N
- Time to complete (compared to SLA)

**Risk reduction report:**

Compares risk posture before and after the campaign:
- SoD violations before campaign: N
- Violations resolved through revocation: N
- Net violation reduction: X%
- Severity breakdown of resolved violations

Export as PDF for audit evidence or as Excel for further analysis.

---

## 8. Role Engineering (Role Design Studio)

### 8.1 Role Design with Inline SoD Check

The Role Designer allows you to build and modify SAP roles with real-time SoD checking — something SAP's native role maintenance (PFCG) does not provide.

**Opening the Role Designer:**

Navigate to **Roles → Role Designer**

**Design workflow:**

1. Create new role or open existing role for modification
2. Add authorization objects, field values, and transaction codes using the searchable permission picker
3. As you add permissions, the **Inline SoD Panel** on the right updates in real-time:
   - Shows which SoD rules fire based on current permissions
   - Highlights the specific permission that completes the violation
   - Suggests which permission to remove to resolve the conflict
4. Resolve all Critical violations before saving
5. Save and submit for approval (role owner + security admin sign-off required)

[Screenshot: Role Designer with permission tree on left, inline SoD check panel on right showing real-time violations]

**SoD check is mandatory for production roles:**

If you attempt to save a role with Critical SoD violations, the system requires:
- Either: resolve the violation (remove conflicting permission)
- Or: add a formal mitigation control (linked to the violation) and provide a business justification

This enforcement ensures no new intrinsically conflicting roles are introduced without awareness and documentation.

### 8.2 Role Mining from Usage Data

Role mining analyzes actual SAP system usage data to identify what users actually do, versus what they are authorized to do.

**Running role mining:**

1. Navigate to **Roles → Role Mining**
2. Select the target system and time period (recommend: 6-12 months)
3. Configure clustering parameters:
   - Minimum user count per role: 3 (don't create roles for unique individuals)
   - Usage similarity threshold: 75% (users must share 75% of their T-code usage)
4. Click **Run Mining**

**Reading mining results:**

The mining engine produces:
- **Usage clusters**: Groups of users with similar transaction usage patterns
- **Proposed role**: The minimal permission set that covers 90% of the cluster's usage
- **Current role landscape**: How the proposed role differs from existing roles
- **Consolidation opportunity**: If two similar roles could be merged

**Acting on mining results:**

For each proposed role:
- Review the clustered users and confirm they form a logical business group
- Review the proposed permissions and confirm they are appropriate
- Create the role in the Role Designer (with automatic SoD check)
- Propose a role assignment transition plan

### 8.3 Business Role Management

Business roles abstract the technical complexity of SAP authorization from business users:

**Example:**
```
Business Role: Accounts Payable Clerk
Technical Roles: FI_AP_CLERK + MM_VENDOR_DISPLAY + FI_AP_REPORT
Business Description: Access to post vendor invoices, view vendor master, run AP reports
Who can hold this role: Employees in Finance department with job code AP_ANALYST
SoD checks: Verified clean — no conflicts
```

**Creating a business role:**

1. Navigate to **Roles → Business Role Management → New Business Role**
2. Define:
   - Business role name and description
   - Target user population (department + job code rules)
   - Included technical roles (from the role catalog)
3. System automatically runs SoD check on the combined permissions
4. Set approval workflow for this role (who approves requests for it)
5. Publish to role catalog

**End users experience:**

When a user submits an access request, they see the business role catalog — plain-language role names with business descriptions, not technical SAP role names. They select what they need in business terms; GovernexPlus handles the technical role translation.

### 8.4 Role Drift Detection

Role drift occurs when the actual state of roles in SAP diverges from the approved baseline in GovernexPlus.

**Configuring drift monitoring:**

1. Navigate to **Roles → Drift Detection → Configure**
2. Select comparison frequency (daily recommended)
3. Select the "approved state" baseline (last approved role in GovernexPlus vs. current RFC query)

**Drift alert types:**

| Alert Type | Description | Risk Level |
|---|---|---|
| Role permissions added | Someone added T-codes/auth objects to a production role outside the normal workflow | High |
| Role permissions removed | Permissions removed without approval (may indicate access revocation or error) | Medium |
| Role assigned to unexpected user | Role assigned to user outside the defined population | High |
| Role no longer exists in SAP | Role present in GovernexPlus baseline but deleted in SAP | Medium |

When drift is detected:
1. Security team receives alert notification
2. Drift review task created in your dashboard
3. You investigate: Was this an authorized change? (Check change management system)
4. Resolve: Approve as legitimate change (update baseline) or raise as unauthorized change

### 8.5 Role Comparison and Consolidation

**Comparing two roles:**

1. Navigate to **Roles → Compare**
2. Select Role A and Role B
3. View side-by-side comparison:
   - Permissions in A but not B
   - Permissions in B but not A
   - Permissions in both A and B (overlap)
4. Overlap percentage: if >80%, roles are candidates for consolidation

**Role consolidation wizard:**

1. Navigate to **Roles → Consolidation**
2. Select roles to consolidate (2 or more)
3. System proposes the merged role (union of all permissions)
4. System shows:
   - How many users currently hold each role
   - What new SoD violations emerge from the merged role (if any)
   - A proposed assignment plan (who should get the new merged role)
5. Review and modify the merged role in the Role Designer
6. Approve and schedule the consolidation
7. GovernexPlus executes: assigns new role, removes old roles, verifies, decommissions old roles

---

## 9. AI-Assisted Features

### 9.1 Role Redesign Copilot

The Role Redesign Copilot provides intelligent analysis of the SAP role landscape and generates actionable proposals for SoD remediation.

**Accessing the Copilot:**

Navigate to **AI → Role Redesign Copilot**

**Phase 1 — Landscape Analysis:**

The Copilot analyzes your entire role landscape and produces:
- Inventory of all intrinsically conflicting roles (role-level violations)
- Inventory of all dangerous role combinations (cross-role violations)
- User impact: how many users are affected by each conflict
- Grouping: violations that share a common root cause

**Phase 2 — Consolidation Proposals:**

For roles that have grown too broad over time:
- "Role FI_ALL_ACME contains permissions spanning 8 different SoD rule functions. Recommend splitting into 3 focused roles: FI_AP_POST, FI_AR_RECEIVE, FI_REPORT_VIEW."
- Provides detailed split proposal with permission list for each new role
- Shows the user impact (how to re-assign the current role holders)
- Estimates the violation reduction: "This split would resolve 47 Critical violations affecting 23 users"

**Phase 3 — Remediation Roadmap:**

Produces a prioritized 90-day remediation plan:
- Week 1–2: Fix 5 intrinsic role conflicts (resolves 120 violations)
- Week 3–4: Restructure AP role (resolves 47 violations for 23 users)
- Week 5–8: User-level remediation for remaining 89 users
- Week 9–12: Policy and control updates, final verification

### 9.2 Migration Copilot (SAP GRC → GovernexPlus)

If you are migrating from SAP GRC AC 12.0, the Migration Copilot guides you through the process.

**Step 1: Export from SAP GRC AC**

In SAP GRC:
- Export rule library: AC → Rule Setup → Export (Excel)
- Export mitigation control assignments (report GRAC_MITIGATION_CONTROL_LIST)
- Export risk analysis results for current snapshot

**Step 2: Run Migration Analysis**

Navigate to **AI → Migration Copilot → Import SAP GRC Export**

Upload the exports. The Copilot:
1. Maps SAP GRC risk IDs to GovernexPlus rules (identifies matches and gaps)
2. Identifies SAP GRC custom rules with no GovernexPlus equivalent → queued for custom rule creation
3. Maps mitigation control assignments → recreates in GovernexPlus mitigation register
4. Assesses your ECC role landscape for S/4HANA compatibility (T-code → Fiori app mapping)

**Step 3: Review and Confirm**

The migration dashboard shows:
- Rules mapped successfully: N / N total
- Rules requiring manual mapping: N
- Rules already built-in (no action needed): N
- Mitigation controls to recreate: N
- Estimated migration effort: X person-days

**Step 4: Execute Migration**

Accept the mappings and GovernexPlus creates:
- Custom rules for unmapped items (in Draft status for your review)
- Mitigation control records
- Historical snapshot import (so you start with a complete baseline, not zero)

---

## 10. Day-to-Day Workflows

### 10.1 Morning Review Routine (15 minutes)

**1. Check AI Attention Items (5 minutes)**

Navigate to **Dashboard → AI Attention Items**

The AI surfaces 3–10 items requiring your attention today:
- "Critical violation created: John Smith now has FI-012 active violation after yesterday's role assignment"
- "Firefighter session overdue for controller review: FF_FIN_ACME session from 2026-09-05"
- "Certification campaign 'Q3 Financial Review' has 12 overdue reviewers with SLA breach in 2 days"

Action each item directly from the attention list.

**2. Approval Inbox (10 minutes)**

Navigate to **Access Requests → Approval Inbox → My Pending**

For each pending request:
- High-risk requests (Critical violations): Review in detail, 5–10 minutes each
- Low-risk requests (no violations): Bulk approve with comment

### 10.2 Processing a High-Risk Access Request (Step by Step)

**Scenario**: User John Smith requests role MM60. The inline SoD check shows Critical violation FI-012 would be created.

**Step 1**: Open the request. Read the business justification.

**Step 2**: Check John's current role portfolio. Does he genuinely need the AP posting access (Function A)? Or is it a legacy role he no longer uses?

**Step 3**: Run What-If simulation:
- Model 1: Approve MM60 → Critical violation (score: 118)
- Model 2: Remove FI_AP_CLERK + Add MM60 → No violation (score: 0)
- Model 3: Approve MM60 + Create compensating control → Mitigated violation (score: 118, mitigated)

**Step 4**: Contact John's manager with the analysis. "John's request would create a Critical SoD violation. We have two options: (A) We can approve if we remove his AP posting access, which you mentioned he no longer uses. (B) We can approve both with a monthly CFO review of AP postings."

**Step 5**: Based on manager's response:
- If Option A: Reject MM60 request. Submit separate request to remove FI_AP_CLERK + Add MM60 as a clean swap.
- If Option B: Approve conditionally with compensating control requirement.

**Step 6**: Document the decision with full rationale in the approval notes. This is your audit evidence.

### 10.3 Responding to a Firefighter Emergency Request

**Scenario**: It's 11 PM. You receive a firefighter request notification.

**Step 1**: Read the notification email. Is the reason code legitimate? Does the requester's identity and department match the stated emergency?

**Step 2**: If clearly legitimate (system outage, payroll run deadline):
- Click the approval link directly from the email
- Add a brief note ("Approved per phone call with John's manager at 11:02 PM")
- Approve immediately

**Step 3**: If unclear or concerning:
- Call the requester or their manager to verify
- If cannot verify: Reject with reason "Unable to verify emergency; please submit during business hours or contact security team"

**Step 4**: Monitor the live session for the first 15 minutes (set a phone reminder). Check:
- Are the T-codes being executed consistent with the stated emergency?
- Any red flags (table maintenance, user admin, etc.)?

**Step 5**: Next morning:
- Open completed session log
- Review AI analysis
- Sign off on the controller review
- Note any concerns for follow-up

### 10.4 Monthly SoD Reporting

**Step 1**: Run full landscape Risk Intelligence Engine analysis (or wait for the scheduled overnight run)

**Step 2**: Generate the Monthly SoD Report:
- Navigate to **Reports → SoD Summary → Generate**
- Select reporting period: current month
- Format: PDF (for distribution) + Excel (for detailed analysis)

**Step 3**: Review the report before distribution:
- New critical violations this month (investigate each)
- Resolved violations (confirm remediation was legitimate)
- Trend: are we improving or degrading?

**Step 4**: Distribute to:
- CISO / Security manager (full report)
- Business unit heads (their department's violations only — scoped report)
- Risk manager (for risk register update)

**Step 5**: Update the risk register in the RM pillar:
- Navigate to **Risk → Risk Register → [Access Risk Record]**
- Update the KRI: "Total unmitigated Critical violations"
- Update trend commentary

---

## 11. Reports for SAP Security Teams

### 11.1 Standard Reports

| Report Name | Location | Frequency | Audience |
|---|---|---|---|
| SoD Violation Summary | Reports → SoD | Monthly | Security team, CISO |
| User Access Profile | Reports → AC → User Profile | Ad-hoc | Security analyst |
| Role Risk Inventory | Reports → AC → Roles | Monthly | Security team |
| Mitigation Control Status | Reports → AC → Mitigation | Monthly | Security team, Compliance |
| Firefighter Session Log | Reports → Privileged Access Governor → Sessions | Monthly | ID owners, Auditors |
| Certification Campaign Results | Reports → UAR | Per campaign | Security team, CISO |
| Access Request SLA | Reports → Access Lifecycle Manager → SLA | Weekly | Security manager |
| New/Changed Violations | Reports → Risk Intelligence Engine → Delta | Weekly | Security team |
| Org Risk Ranking | Reports → Risk Intelligence Engine → Org | Monthly | CISO, Business heads |

### 11.2 Custom Report Builder

Navigate to **Reports → Custom** to build ad-hoc reports:

1. Select the data entity (Violations, Users, Roles, Sessions, Requests, Certifications)
2. Add filters (date range, severity, org unit, system, rule ID, etc.)
3. Select columns to display
4. Set grouping and sorting
5. Preview and export (PDF / Excel / CSV)

Save custom report configurations for reuse.

### 11.3 Executive Dashboard Metrics

The security section of the Command Center shows:

- **Violations Today**: Total active violations (clickable, drills to list)
- **Critical Violations**: Critical violations with no mitigation (red if >0)
- **Risk Score Trend**: 30-day trend line of aggregate risk score
- **Top 5 Riskiest Users**: Ranked by violation score
- **Certification Completion**: Current campaign completion %
- **Open Firefighter Sessions**: Active right now (real-time)
- **Approval Queue Depth**: Requests awaiting security review
- **SoD Remediation Progress**: % of identified violations with remediation plan

---

*This guide is maintained by the GovernexPlus Product Team. For questions or updates, contact product-docs@governexplus.io*

*Last updated: September 2026 | Version 2.0*
