# GovernexPlus — Auditor & Compliance Officer Guide

**Version:** 2.0 | **Date:** September 2026 | **Audience:** Internal Auditors, External Auditors, Compliance Officers | **Classification:** Internal / Auditor-Restricted

---

## Table of Contents

1. [Auditor Role in GovernexPlus](#1-auditor-role-in-governexplus)
2. [Audit Universe Management](#2-audit-universe-management)
3. [Audit Planning](#3-audit-planning)
4. [Engagement Lifecycle](#4-engagement-lifecycle)
5. [Work Programs & Procedures](#5-work-programs--procedures)
6. [Workpapers](#6-workpapers)
7. [Findings (CCCE Format)](#7-findings-ccce-format)
8. [Action Tracking](#8-action-tracking)
9. [Evidence Management](#9-evidence-management)
10. [Reporting](#10-reporting)
11. [Compliance Workflows](#11-compliance-workflows)

---

## 1. Auditor Role in GovernexPlus

### 1.1 What Auditors Can Access

GovernexPlus is designed with a principle of "trust but verify" for auditors: you have extensive read access across all four GRC pillars so you can gather evidence independently, and full write access within the Audit Management pillar where you document your work.

**Read Access (all four pillars):**

| Pillar | What You Can See |
|---|---|
| **Access Control (AC)** | All SoD violations and risk scores; user access profiles; role assignments; Risk Intelligence Engine analysis results; certification campaign decisions; firefighter session logs; access request history |
| **Risk Management (RM)** | Full risk register; risk assessment history; KRI data; incident records; response plans; risk approval workflows |
| **Process Control (PC)** | Control library; control test results; deficiency records; CCM results; SOX sign-off status; evidence submitted for control testing |
| **Audit Management (AM)** | Everything — full read + write access |

**Write Access (Audit Management pillar only):**
- Audit universe (create/update entities)
- Audit plans (create/update annual and multi-year plans)
- Engagements (full lifecycle management)
- Work programs and procedures
- Workpapers
- Findings (CCCE format)
- Actions
- Evidence uploads

**What Auditors Cannot Do:**
- Modify AC, RM, or PC data (you are an independent reviewer — changing the data you are reviewing would compromise independence)
- Approve or reject access requests (you review decisions, not make them)
- Modify SoD rules or risk ratings
- Modify or delete control test results
- Access another tenant's data

### 1.2 Independence Protections

GovernexPlus enforces auditor independence at the technical level:

1. **Read-only cross-pillar access**: The API enforces that `auditor` role users cannot write to AC, RM, or PC endpoints
2. **Engagement assignment**: An auditor cannot be assigned as both the preparer and the reviewer on the same procedure or workpaper
3. **Finding attribution**: Every finding clearly shows which auditor created it — findings cannot be anonymized
4. **Audit trail**: All auditor actions (evidence access, report generation, finding creation) are logged with identity and timestamp
5. **External auditor access**: External auditors can be given a time-limited guest `auditor` account scoped to specific engagements only

### 1.3 GovernexPlus vs. Manual Audit Processes

| Activity | Without GovernexPlus | With GovernexPlus |
|---|---|---|
| Evidence collection | Manually request from control owners via email | Evidence Agent auto-collects; supplemental upload |
| SoD violation evidence | Export from SAP GRC; maintain in Excel | Live query; automatically linked to findings |
| Workpaper management | SharePoint/network drive | Versioned, searchable, cross-referenced repository |
| Finding tracking | Email threads; Excel tracker | Structured CCCE findings with action tracking |
| Certification evidence | PDF exports from UAR tool | Direct link to certification decisions in GovernexPlus |
| Report generation | Word document + manual charts | Auto-generated with live data, PPTX/PDF export |
| Prior period comparison | Archive search | Built-in prior period comparison and trend |

---

## 2. Audit Universe Management

### 2.1 What is the Audit Universe?

The audit universe is the complete population of everything your internal audit function is responsible for reviewing. It is the starting point for every audit plan — you cannot plan what to audit if you don't know what exists.

GovernexPlus maintains a structured, risk-scored audit universe that automatically stays current because it is connected to live data from all four GRC pillars.

**Universe Entity Types:**

| Entity Type | Examples |
|---|---|
| Legal Entity | ACME Corp USA, ACME Corp UK, ACME GmbH |
| Business Division | Americas, EMEA, APAC |
| Business Department | Finance, Procurement, HR, IT |
| Business Process | Accounts Payable, Payroll, Procurement-to-Pay, Order-to-Cash |
| IT Application | SAP S/4HANA PRD, Salesforce, SAP SuccessFactors |
| IT Infrastructure | Data center, Network, Cloud (AWS account) |
| Regulatory Requirement | SOX Section 302, SOX Section 404, GDPR Article 32 |

### 2.2 Creating Auditable Entities

**Navigate to: Audit → Universe → New Entity**

[Screenshot: New Audit Universe Entity form with type selector, metadata fields, and risk score preview]

**Entity record fields:**

| Field | Example | Notes |
|---|---|---|
| Entity ID | AE-FIN-001 | Auto-generated |
| Entity Name | Accounts Payable Process | Descriptive, unique |
| Entity Type | Business Process | From type list above |
| Parent Entity | Finance Department | Hierarchy placement |
| Description | End-to-end AP including PO matching, invoice processing... | Scope description |
| Entity Owner | John Smith (AP Manager) | Management accountability |
| Regulatory Significance | SOX | Which regulations govern this entity |
| Inherent Risk | High | Pre-control risk assessment |
| Control Coverage | Good | Assessment of existing controls |
| Strategic Importance | High | Business criticality |
| IT Systems | SAP PRD, SAP SRM | Connected systems |
| Geographic Scope | US, UK, Germany | Where this entity operates |
| Staff Count | 12 | Number of personnel |
| Financial Materiality | $120M annual spend | Volume processed |
| Last Audit Date | 2025-Q3 | When last reviewed |

### 2.3 Automated Risk-Based Scoring (XI-04)

GovernexPlus automatically calculates a composite risk score for each universe entity by combining data from all four GRC pillars:

**Scoring Formula:**

```
Audit Universe Risk Score (0-100) =
  [RM Contribution: 40%]  Risk register average severity for this entity's processes
+ [PC Contribution: 35%]  Inverse of control maturity (higher maturity = lower audit priority)
+ [AC Contribution: 25%]  Access risk exposure for users in this entity's org unit

Where:
  RM Contribution = Average residual risk rating for linked risks × 0.40
  PC Contribution = (1 - Control Effectiveness Index) × 100 × 0.35
  AC Contribution = Mean SoD violation score for entity's users × 0.25
```

**Score interpretation:**

| Score Range | Priority | Typical Audit Frequency |
|---|---|---|
| 75–100 | Priority 1 | Annual (mandatory) |
| 50–74 | Priority 2 | Annual or bi-annual |
| 25–49 | Priority 3 | Every 2–3 years |
| 0–24 | Priority 4 | Every 3–5 years or risk-based |

**Score components are live:**

The composite score updates automatically when:
- A new risk is added to the RM register linked to this entity
- A control is assessed as ineffective in the PC pillar
- A new SoD violation is detected for users in this entity's org unit
- A prior finding is closed (score improves)

This means your audit universe is always current — no annual manual risk reassessment required.

[Screenshot: Audit Universe heatmap showing entities plotted by risk score with priority color coding]

### 2.4 Maintaining the Universe

**Periodic universe review (annual recommended):**

1. Navigate to **Audit → Universe → Review Mode**
2. Review each entity:
   - Is it still an accurate description of the entity?
   - Have ownership or organizational changes occurred?
   - Are there new entities that should be added (new systems, new processes, M&A)?
   - Have any entities been decommissioned?
3. Update and archive as needed

**Archiving entities:**

Retired entities (decommissioned systems, divested business units) should be archived, not deleted:
- Archived entities remain for historical reference (prior audits, evidence)
- They no longer appear in active universe lists or contribute to planning
- Archival is logged with reason and date

**Entity change history:**

Every change to an entity record is versioned:
- What changed, who changed it, when
- Available for audit trail review
- Auditors can view the entity as it existed during any historical period (important for prior-period audit reference)

---

## 3. Audit Planning

### 3.1 Creating an Annual Audit Plan

**Navigate to: Audit → Plans → New Plan**

**Plan parameters:**

| Parameter | Example | Notes |
|---|---|---|
| Plan Title | FY2027 Internal Audit Plan | |
| Plan Type | Annual | Annual / Multi-year / Rolling |
| Fiscal Year | 2027 | |
| Planning Horizon | Q1 2027 – Q4 2027 | |
| Available Auditor-Days | 800 | Total capacity across team |
| Buffer Capacity | 20% | Reserve for unplanned work |
| CAE | Sarah Johnson | Chief Audit Executive |
| Approval Required | Board Audit Committee | Who approves the plan |

### 3.2 Risk-Based Plan Generation

GovernexPlus can generate an initial draft audit plan automatically from the universe risk scores.

**Navigate to: Audit → Plans → [Plan] → Generate from Risk Scores**

The auto-generation algorithm:
1. Retrieves all active universe entities sorted by composite risk score (descending)
2. Starting with the highest-risk entity, assigns engagements to quarters
3. Respects resource constraints per quarter (available days after 20% buffer)
4. Considers time since last audit (entities not audited in 3+ years get prioritized regardless of current risk score)
5. Flags mandatory items (SOX scope, regulatory commitments) for every year
6. Produces a draft plan with estimated effort days per engagement

**Reviewing and adjusting the draft plan:**

The generated plan is a starting point, not a final decision. CAE review typically:
- Confirms coverage of all SOX-scoped entities
- Adjusts timing based on business cycle (avoid AP audit during year-end close)
- Confirms resource availability matches plan allocation
- Adds management-requested engagements
- Documents rationale for any departures from pure risk ranking

[Screenshot: Annual audit plan with quarter columns, engagement cards showing estimated effort and risk score, drag-drop reordering]

### 3.3 Resource Allocation

**Navigate to: Audit → Plans → [Plan] → Resources**

Resource planning shows:
- Each auditor's total planned days by quarter
- Utilization percentage vs. available capacity
- Skills matching (is the assigned auditor qualified for this engagement type?)
- Vacation and training blocks (imported from HR or manually entered)
- Warning indicators when any quarter exceeds 80% utilization (inadequate buffer)

**Capacity view:**

```
Q1 2027 Resource Summary:
  Sarah Johnson (Senior):   45 / 60 days planned  (75%)
  Mike Chen (Auditor II):   50 / 60 days planned  (83%) ⚠ High
  Lisa Park (Auditor I):    30 / 60 days planned  (50%)
  Team Total:              125 / 180 days planned  (69%)
  Unplanned buffer:         55 days
```

### 3.4 Plan Approval Workflow

1. CAE reviews and finalizes the draft plan
2. CAE submits plan for approval: **Plans → [Plan] → Submit for Approval**
3. Approver receives notification (typically Board Audit Committee Chair or Audit Committee)
4. Approver reviews plan summary and approves or requests changes
5. Approved plan is locked — changes require a formal plan amendment (tracked separately)

**Plan amendment process:**

When the approved plan needs to change (new risks emerge, resources change):
1. Navigate to **Plans → [Plan] → Request Amendment**
2. Document what changed and why
3. Amended plan goes through the same approval workflow
4. Original and amended plan both preserved in history

---

## 4. Engagement Lifecycle

### 4.1 Creating an Engagement

**Navigate to: Audit → Engagements → New Engagement**

**Engagement setup form:**

| Field | Example | Notes |
|---|---|---|
| Engagement Title | Accounts Payable Process Review Q3 2026 | |
| Engagement Type | Internal Audit | See types below |
| Audit Plan Reference | FY2026 Annual Plan | Link to plan |
| Universe Entity | Accounts Payable Process | From universe |
| Auditee Organization | Finance Department | Business unit being audited |
| Auditee Contact | John Smith (AP Manager) | Primary contact |
| Audit Lead | Mike Chen | Responsible auditor |
| Team Members | Lisa Park, External Co-source | |
| Planned Start | 2026-08-01 | |
| Planned End | 2026-09-30 | |
| Budget Hours | 80 | Total team hours budgeted |
| Scope Statement | Review of AP process controls including vendor setup, invoice processing, payment approval... | |
| Audit Objectives | 1. Assess adequacy of 3-way match controls. 2. Evaluate payment authorization controls. 3. Assess vendor master governance. | |

**Engagement types:**

| Type | Description | Typical Output |
|---|---|---|
| Internal Audit | Standard risk-based audit | Audit report with findings |
| IT General Controls | ITGC testing (SOX or standalone) | ITGC test results + findings |
| SOX Review | Annual SOX 302/404 support | Testing results + deficiency assessment |
| Special Investigation | Fraud, misconduct investigation | Investigation report |
| Advisory | Management-requested assessment | Advisory memo or report |
| Follow-Up | Prior finding remediation verification | Status update report |

### 4.2 The Six-Stage Pipeline

Every engagement moves through six defined stages. Stage advancement is controlled and logged.

**Stage 1: Planned**

Entry criteria: Engagement record created and approved
Key activities:
- Finalize scope and objectives
- Confirm team members and their roles
- Align on timeline with auditee
- Prepare preliminary risk assessment
- Review prior audit workpapers and findings

**Stage 2: Announced**

Entry criteria: Scope finalized and approved by CAE
Key activities:
- Issue formal engagement announcement letter to auditee
- Request preliminary documentation list (policies, procedures, org charts)
- Schedule introductory meeting with auditee management
- Confirm access to systems and people
- Distribute documentation requests to auditee via GovernexPlus portal

**Announcement letter generation:**

Navigate to **Engagement → Announce → Generate Letter**

GovernexPlus automatically generates an announcement letter with:
- Audit title, scope, and objectives
- Audit team members and their roles
- Timeline (fieldwork start, expected report date)
- Documentation requests (customizable list)
- Auditee contact instructions

[Screenshot: Engagement Announcement stage with letter preview and documentation request list]

**Stage 3: Fieldwork**

Entry criteria: Announcement sent and preliminary documentation received
Key activities:
- Execute work programs and procedures
- Gather and document evidence
- Conduct walkthroughs and interviews
- Identify observations and potential findings
- Clear procedures with team lead review
- Update budget vs. actual hours

**Budget monitoring:**

```
Fieldwork Progress — AP Review Q3 2026
Budget: 80 hours | Actual to date: 52 hours | Remaining: 28 hours
Procedures complete: 14 / 20 (70%)
Estimated at completion: 82 hours (102.5% of budget)
⚠ Warning: 2.5 hours over budget — discuss with audit lead
```

**Stage 4: Draft Report**

Entry criteria: All fieldwork procedures complete and cleared
Key activities:
- Compile all findings into draft engagement report
- Internal quality review (Audit Lead reviews all findings and conclusions)
- Issue draft report to management for response
- Track management responses (formal response required for each finding)
- Revise findings based on factual corrections from management

**Management response tracking:**

For each finding, management must provide:
- Agree / Partially Agree / Disagree
- If Agree/Partially Agree: specific remediation actions and due dates
- If Disagree: basis for disagreement and alternative remediation

GovernexPlus tracks the response status and automatically reminds management contacts when responses are due. The audit team can review and accept or challenge management responses.

**Stage 5: Final Report**

Entry criteria: All management responses received and reviewed
Key activities:
- Incorporate factual corrections (not opinion changes)
- Finalize finding text and ratings
- CAE reviews and signs off on final report
- Issue final report to auditee management and Board Audit Committee
- Report stored permanently in GovernexPlus

**Report generation:**

Navigate to **Engagement → Generate Report**

GovernexPlus generates a professional engagement report including:
- Executive summary with overall conclusion
- Background and scope
- Audit objectives and methodology
- Summary of findings by severity
- Detailed finding sections (CCCE format)
- Management responses
- Appendices (scope details, testing summary)

Format options:
- Word (for final editing and letterhead)
- PDF (for distribution)
- PPTX (for Committee presentation)

**Stage 6: Closed**

Entry criteria: All findings have management responses; all critical findings have confirmed remediation actions with owners
Key activities:
- Confirm all actions have been assigned and accepted by owners
- Archive engagement record
- Conduct engagement debrief (lessons learned)
- Update audit universe risk score (feeding back into next plan cycle)

---

## 5. Work Programs & Procedures

### 5.1 Work Program Templates

Work programs are structured plans of the audit procedures to be performed. GovernexPlus maintains a reusable template library.

**Accessing templates:**

Navigate to **Audit → Templates → Work Programs**

**Template categories:**

| Category | Available Templates |
|---|---|
| Financial Audit | AP Process, AR Process, Payroll, Treasury, Fixed Assets |
| IT Audit | ITGC (Access, Change, Operations, Backup/Recovery), Application Controls |
| SOX Testing | Control testing templates by COSO component |
| Procurement | P2P Process, Vendor Management, Contract Compliance |
| HR | Hire-to-Retire, Payroll, Benefits |
| Regulatory | GDPR Data Subject Rights, AML Controls, FCPA Third-Party Due Diligence |

**Anatomy of a work program:**

```
Work Program: Accounts Payable Controls
Engagement Type: Internal Audit
Version: 3.2 (updated 2026-07)
Procedures: 18

Section 1: Invoice Processing Controls (5 procedures)
  WP-1.1  Verify 3-way match control operation
  WP-1.2  Test invoice approval authorization
  WP-1.3  Duplicate invoice detection
  WP-1.4  Blocked invoice release process
  WP-1.5  Goods receipt verification

Section 2: Payment Controls (4 procedures)
  WP-2.1  Payment run authorization
  WP-2.2  Dual payment approval threshold
  WP-2.3  Bank account change authorization
  WP-2.4  Payment reconciliation

Section 3: Vendor Master Controls (4 procedures)
  WP-3.1  New vendor authorization
  WP-3.2  Vendor bank account maintenance
  WP-3.3  Vendor master access controls (SoD)
  WP-3.4  Vendor master periodic review

Section 4: SoD and Access Controls (5 procedures)
  WP-4.1  User access profile review (from Risk Intelligence Engine)
  WP-4.2  Firefighter session review (from Privileged Access Governor)
  WP-4.3  Certification campaign completeness
  WP-4.4  Privileged access review
  WP-4.5  System configuration change review
```

### 5.2 Cloning Templates for Engagements

1. Navigate to **Engagement → Work Programs → Add from Template**
2. Select the template
3. Customize for the specific engagement:
   - Remove inapplicable procedures (mark as "N/A — Not in scope")
   - Adjust sample sizes for the entity's transaction volume
   - Modify procedure steps for the specific system (SAP vs. another ERP)
   - Add engagement-specific procedures
4. Assign procedures to team members
5. Set completion deadlines per procedure

### 5.3 Procedure Execution

**Opening a procedure:**

Navigate to **Engagement → Work Programs → [Procedure]**

[Screenshot: Procedure detail page with steps checklist, evidence attachment zone, and dual sign-off panel]

**Procedure detail shows:**

- **Objective**: What this procedure is designed to test
- **Risk addressed**: Which control risk this procedure addresses
- **Procedure steps**: Numbered checklist of work to perform
- **Evidence attached**: All files uploaded as support
- **Observations**: Free-text notes per step
- **Exceptions noted**: Any deviations found (linked to potential findings)
- **Conclusion**: Overall step conclusion
- **Time tracking**: Hours logged

**Step-by-step execution:**

For each procedure step:

1. Read the step objective
2. Perform the audit work (query the system, inspect documentation, conduct interview)
3. Document the work performed:
   - "Reviewed 25 randomly selected vendor invoices for the period. All 25 had matching POs and goods receipts. Exception noted for invoice #INV-4521 which had a goods receipt variance of $1,250 (above $500 threshold). Documented in Observation Tab."
4. Upload supporting evidence (screenshot, export, document)
5. Note any exceptions
6. Mark step: Satisfactory / Exception Noted / Not Applicable
7. Log time spent on this step

**Completing the procedure:**

After all steps are complete:
1. Write the overall procedure conclusion:
   - Satisfactory: "Controls operated effectively for the sample tested. No exceptions noted."
   - Exception: "3 exceptions noted in the sample of 25 invoices (12%). Goods receipts did not match invoice amounts by more than the $500 threshold. See exceptions for detail."
2. Link any exceptions to potential findings (or create new potential findings)
3. Sign as Preparer

### 5.4 Dual Sign-Off

Every procedure requires two signatures:

1. **Preparer sign-off**: The auditor who performed the work confirms the procedure is complete and accurately documented
2. **Reviewer sign-off**: The Audit Lead (or designated senior) reviews the procedure, evidence, and conclusions, and either:
   - Signs off: "Reviewed and agreed"
   - Returns with comments: "Please clarify the basis for sample selection. Was it random or judgmental?"

**Reviewer commenting:**

The reviewer can add review notes to any step:

```
Review note (Mike Chen, Senior Auditor, 2026-08-15):
"The observation on step 3 does not quantify the exception rate. Please update with
'X of Y sample items had exceptions, representing Z%.' This is needed for finding
materiality assessment."
```

The preparer responds to review notes and resubmits.

**Clearing a procedure:**

Once the reviewer is satisfied, they "clear" the procedure (mark it reviewed and approved). Cleared procedures are locked from further editing — only a supervisor can re-open a cleared procedure.

### 5.5 Time Tracking

GovernexPlus tracks time spent on each procedure for:
- Budget vs. actual comparison
- Billing (for external audit or co-source arrangements)
- Audit efficiency analysis (which procedures consistently take longer than planned?)

**Logging time:**

At the bottom of each procedure page, click **Log Time**:
```
Date: 2026-08-12
Hours: 3.5
Activity: Performed data extraction; reviewed 25 invoice samples; documented exceptions
```

Time entries appear in the engagement's budget dashboard.

---

## 6. Workpapers

### 6.1 The Workpaper Filing System

GovernexPlus provides a structured electronic workpaper repository for each engagement. This replaces network folder structures and ensures all workpapers are versioned, searchable, and accessible to authorized team members.

**Workpaper index structure:**

```
Engagement: AP Process Review Q3 2026
├── 1.0 Planning and Administration
│   ├── 1.1 Engagement Announcement Letter
│   ├── 1.2 Preliminary Risk Assessment
│   ├── 1.3 Prior Audit Workpaper Summary
│   └── 1.4 Documentation Request and Response
├── 2.0 Internal Control Understanding
│   ├── 2.1 Process Narrative — Invoice Processing
│   ├── 2.2 Process Flowchart — Payment Execution
│   └── 2.3 System Description — SAP FI/MM Interface
├── 3.0 Fieldwork Documentation
│   ├── 3.1 Population Extract — Vendor Invoices (3-way match population)
│   ├── 3.2 Sample Selection Workpaper
│   ├── 3.3 Test Workpaper — WP-1.1 (3-way match)
│   └── 3.4 Test Workpaper — WP-2.1 (Payment authorization)
├── 4.0 Risk Intelligence Engine Evidence
│   ├── 4.1 AP User SoD Analysis Export
│   └── 4.2 Mitigation Control Assessment
├── 5.0 Findings
│   ├── 5.1 Finding F-001 — Duplicate Invoice Not Detected
│   └── 5.2 Finding F-002 — Vendor Bank Account Change Without Dual Authorization
└── 6.0 Report
    ├── 6.1 Draft Report (v1, v2, v3)
    └── 6.2 Final Report (signed)
```

### 6.2 Creating Workpapers

**Navigate to: Engagement → Workpapers → New Workpaper**

**Workpaper types:**

| Type | Description | Use When |
|---|---|---|
| Narrative | Descriptive text document | Process descriptions, understanding documentation, meeting notes |
| Schedule | Structured data table/spreadsheet | Sample populations, exception listings, comparative analysis |
| Extract | System-generated data export | SAP reports, ARA exports, database queries |
| Screenshot | Image capture | System configuration evidence, error messages, approval screens |
| Correspondence | Email or letter | Management responses, auditee communications, confirmations |

**Workpaper metadata:**

| Field | Example | Notes |
|---|---|---|
| WP Reference | 3.3 | Index number (follows agreed structure) |
| Title | Test of 3-Way Match Control — Sample of 25 | Descriptive |
| Type | Schedule | From type list |
| Prepared by | Lisa Park | Auto-populated from logged-in user |
| Prepared date | 2026-08-12 | Auto-populated |
| Period covered | July 2026 | What time period does this document cover |
| Finding references | F-001 | Links to related findings |
| Procedure references | WP-1.1 | Links to work program procedure |

### 6.3 Version Management

When you update a workpaper (e.g., after reviewer comments), GovernexPlus creates a new version:

- Prior versions are preserved and accessible
- Version history shows who changed what and when
- "Current version" is always the latest
- Prior versions are marked clearly: "Version 1 — Superseded"

**Version history example:**

```
Workpaper: 3.3 Test of 3-Way Match Control
Version 3 (CURRENT)  — Lisa Park — 2026-08-16 — Updated to add sample size justification
Version 2            — Lisa Park — 2026-08-14 — Revised after reviewer comments
Version 1            — Lisa Park — 2026-08-12 — Initial preparation
```

### 6.4 Review Workflow

Each workpaper follows a defined review path:

```
Prepared (Lisa Park, Auditor I)
→ Reviewed (Mike Chen, Senior Auditor)   ← must be different person from preparer
→ Approved (Sarah Johnson, CAE)           ← required for key workpapers
```

**Adding review comments:**

As a reviewer, you can annotate specific sections of a workpaper:

1. Open the workpaper
2. Navigate to the section with an issue
3. Highlight or note the concern
4. Click **Add Review Comment**:
   ```
   Reviewer: Mike Chen
   Date: 2026-08-13
   Comment: "The sample size of 25 is not documented as to whether it was
   selected using a random number generator or judgmental selection. Please
   document the sample selection methodology per our audit standards."
   Status: Open
   ```
5. Preparer receives notification
6. Preparer resolves the comment and marks it: **Resolved — [description of action taken]**
7. Reviewer confirms resolution and marks: **Agreed**

### 6.5 Cross-Referencing

Workpapers can be cross-referenced to:
- Work program procedures (the procedure that generated this workpaper)
- Findings (the finding supported by this workpaper)
- Other workpapers (e.g., "See WP 3.1 for population from which sample was drawn")
- Evidence records (the evidence object in the evidence repository)

Cross-references create two-way links — from the workpaper to the finding AND from the finding back to the workpaper. This enables "tracing" — from any finding, you can navigate to all supporting workpapers, and from any workpaper, you can see all findings it supports.

---

## 7. Findings (CCCE Format)

### 7.1 The CCCE Framework

All GovernexPlus findings are structured using the internationally recognized CCCE format:

**C — Condition**: What did we observe? (the fact — objective, specific, quantified)

**C — Criteria**: What should have happened? (the standard — policy, regulation, best practice)

**C — Cause**: Why did the gap occur? (root cause — not just symptoms)

**E — Effect**: What are the consequences? (actual or potential, quantified where possible)

**+ Recommendation**: What specific steps should management take?

**Guidance for each CCCE element:**

**Condition — Writing tips:**
- Always state facts, not opinions: "12 of 25 (48%) invoices reviewed did not have a matching goods receipt" NOT "many invoices were not properly supported"
- Quantify where possible (percentage, dollar amount, time period)
- Include specific examples with identifiers where useful ("Invoice INV-4521 for $45,000 was paid without a goods receipt")
- Avoid characterizations: "inadequate" is a conclusion, not a fact

**Criteria — Writing tips:**
- Cite the specific policy, regulation, or standard: "Per ACME Accounts Payable Policy v3.2, Section 4.1, all vendor invoices above $5,000 must be matched to a purchase order and goods receipt before payment is released"
- If no formal policy exists, cite industry standard: "COSO Framework Principle 10 requires management to implement control activities through relevant policies"
- Use "should" when criteria is best practice (not mandatory): "Industry best practice dictates that goods receipt matching should be performed at the invoice level, not the purchase order level"

**Cause — Writing tips:**
- Distinguish immediate cause from root cause: the immediate cause may be "the control was not performed," but the root cause is "why was the control not performed?"
- Common root causes in access/IT audits: lack of monitoring, lack of training, role design deficiencies, inadequate segregation, system configuration, policy not updated for new processes
- Avoid placing root cause entirely on individuals — system and process factors are usually the primary cause

**Effect — Writing tips:**
- Quantify when possible: "$X at risk," "N transactions undetected"
- If cannot quantify, clearly state potential impact: "Could result in unauthorized payments being processed without detection"
- Include regulatory consequence where applicable: "Non-compliance with SOX Section 302 management certification requirements"
- Distinguish actual effect (it happened) from potential effect (it could happen)

**Recommendation — Writing tips:**
- Be specific and actionable: "Implement system configuration in SAP to automatically block invoice payment when no matching goods receipt exists in the system (MIRO transaction, GR-based invoice verification flag)" NOT "Strengthen controls over invoice processing"
- Address root cause, not just symptoms
- Include a suggested completion timeframe
- If appropriate, suggest interim mitigating controls until permanent fix is implemented

### 7.2 Creating a Finding

**Navigate to: Engagement → Findings → New Finding**

[Screenshot: New Finding form with CCCE section fields, severity selector, and cross-module link panel]

**Step-by-step finding creation:**

**1. Title:**

A good finding title states the issue clearly in 5–10 words:
- "Duplicate Invoice Detection Control Not Operating Effectively"
- "Vendor Bank Account Changes Lack Dual Authorization"
- "SoD Violation: AP Clerk Can Post and Approve Invoices (FI-012)"

**2. Condition (draft):**

```
During testing of 25 vendor invoices randomly selected from the population of
1,247 invoices processed in Q2 2026, 3 invoices (12%) were paid without a matching
goods receipt in SAP. These invoices totaled $134,567. Specifically:
- Invoice INV-4521 (Vendor ABC, $45,000): No goods receipt referenced
- Invoice INV-5102 (Vendor DEF, $67,890): Goods receipt GR-2890 referenced but
  goods receipt was for a different vendor
- Invoice INV-5344 (Vendor GHI, $21,677): Goods receipt dated 45 days after
  invoice payment
```

**3. Criteria:**

```
ACME Accounts Payable Policy v3.2, Section 4.1 requires all vendor invoices above
$5,000 to be matched to a purchase order and a goods receipt before payment release.
Additionally, SAP S/4HANA is configured to enforce 3-way match; however, the system
configuration allows invoices to bypass the match requirement when a manual tolerance
exception is applied (transaction code MRBR).
```

**4. Cause:**

```
Root cause: The MRBR (blocked invoice release) transaction does not require
supervisory authorization before releasing blocked invoices. Any user with the
MM_PROC_CLERK role can release a blocked invoice without approval from the AP
manager or a second reviewer. This allows invoices that failed 3-way match to be
released by the same user who processed them (defeating the intended control).

Contributing cause: The AP department's documented procedure does not address
the blocked invoice release process, leaving staff without clear guidance on when
invoice release is appropriate.
```

**5. Effect:**

```
Actual effect: 3 invoices totaling $134,567 were paid without proper authorization.
While post-payment review by the CFO did not identify fraud, these payments were
made without adequate controls.

Potential effect: The absence of a dual-authorization requirement for blocked
invoice release creates risk that fraudulent or erroneous invoices could be paid
without detection. Based on the Q2 2026 population of 1,247 invoices, extrapolation
of the 12% exception rate suggests approximately 150 invoices per quarter may be
released without proper authorization, representing potential exposure of
approximately $15M–$20M annually.

Regulatory implication: This control failure affects SOX Section 404 management's
assessment of the effectiveness of internal controls over financial reporting.
```

**6. Recommendation:**

```
Management should:

Immediate actions (complete within 30 days):
1. Configure SAP MRBR transaction to require a second approver (different from the
   invoice processor) before a blocked invoice can be released. This is achievable
   through SAP workflow configuration and does not require ABAP development.
2. Implement a compensating control: CFO or AP Manager reviews all MRBR releases
   weekly until the system configuration is complete.

Longer-term actions (complete within 90 days):
3. Update the AP Accounts Payable Procedure document to clearly define when MRBR
   release is appropriate and required authorization steps.
4. Conduct a retrospective review of all MRBR releases in the last 12 months
   to identify any unauthorized releases requiring follow-up.
```

### 7.3 Severity Rating

**Severity definitions:**

| Severity | Definition | Examples |
|---|---|---|
| **Critical** | Represents a material weakness; significant financial exposure or immediate regulatory consequence | Fraud scheme undetected for 12 months; financial statements materially misstated; SAP_ALL in production |
| **High** | Significant deficiency; high probability of material misstatement if not addressed; significant audit findings in SOX context | Duplicate payment control not operating; payment made without authorization; Critical SoD violation unmitigated for 6+ months |
| **Medium** | Control deficiency with moderate risk; limited financial exposure; non-compliance with policy but no immediate harm | 3-way match exceptions for small-value invoices; procedure document out of date; High SoD violation unmitigated |
| **Low** | Minor weakness; limited control impact; easily remediated | Incomplete sign-off on one control test; filing error; duplicate vendor records (not paid) |
| **Observation** | Best practice improvement; no control failure; opportunity identified | Process inefficiency; manual process that could be automated; enhanced reporting opportunity |

**Common mistake**: Inflating severity. A finding classified Critical implies a material weakness requiring immediate escalation to the Audit Committee and disclosure implications in a SOX context. Reserve Critical for genuine material weaknesses.

### 7.4 Cross-Module Linking

One of GovernexPlus's most powerful features for auditors: every finding can be linked directly to evidence and records in other GRC pillars.

**Links available:**

| Link Type | What You Can Link | Why Useful |
|---|---|---|
| AC — SoD Violation | Specific violation record from Risk Intelligence Engine | "This finding is supported by the Risk Intelligence Engine violation record for user J.Smith showing FI-012 active" |
| AC — Firefighter Session | Specific session log | "The unauthorized access was executed under firefighter ID FF_FIN_ACME on 2026-08-05 (see session log)" |
| AC — Certification Decision | Prior UAR decision | "User's access was certified in the Q1 2026 UAR despite having this violation" |
| RM — Risk Record | Risk register entry | "This finding relates to Risk RM-056: AP Process Fraud Risk (rated High residual)" |
| PC — Control Record | Control in the PC library | "This finding indicates Control PC-AP-003 (3-Way Match) is not operating effectively" |
| PC — Deficiency | PC deficiency record | "A deficiency record has been created in the Process Control module (DC-2026-047)" |
| Prior Finding | Finding from prior engagement | "This is a repeat finding; identical issue noted in the 2025 AP audit (Finding F2025-012)" |

**Creating cross-module links:**

```
Finding Detail → Cross-Module Links tab → Add Link
Select link type → Search for the specific record → Add
```

When a link is added, the record in the other module is also notified:
- The linked risk record displays: "Referenced in Audit Finding F-2026-003"
- The linked SoD violation displays: "Referenced in Audit Finding F-2026-003"

This bi-directional linking creates a fully traceable GRC evidence graph.

### 7.5 Repeat Finding Detection

GovernexPlus automatically checks each new finding against all prior findings in your tenant to identify potential repeats:

**Detection logic:**

- Matches on: Same entity + Same control theme + Similar finding title keywords
- Presents potential matches for auditor review
- Auditor confirms: "Yes, this is a repeat" or "No, different issue"

**Consequences of marking as repeat:**

- Severity is automatically elevated one level (a prior High becomes Critical if repeated)
- Finding narrative automatically notes the prior occurrence and year
- Management response must acknowledge the repeat nature
- CAE receives special notification about the repeat finding
- Dashboard shows "Repeat Finding Count" as a KPI (high count indicates systemic management response issues)

### 7.6 Management Response Capture

After draft report is issued, management provides a formal response for each finding:

**Management response elements:**

1. **Agreement**: Agree / Partially Agree / Disagree
2. **Response narrative**: Management's explanation and position
3. **Remediation actions**: What specific steps will be taken (at least one action required if Agree/Partially Agree)
4. **Action owner**: Who is responsible
5. **Target completion date**: When will this be done

**Auditor review of management response:**

After receiving management responses, the auditor reviews each:
- Is the response adequate? Does it address the root cause, not just the symptom?
- Are the proposed actions specific enough to be verifiable?
- Is the timeline reasonable?
- If Disagree: is the basis for disagreement factually sound?

Auditor can add a **Closing Note** to the finding:
```
Auditor note: "Management response is adequate. The proposed system configuration
change (action A-001) will address the root cause. The interim compensating control
(action A-002) provides coverage until the permanent fix is implemented. Internal
Audit concurs with the proposed approach."
```

---

## 8. Action Tracking

### 8.1 Creating Remediation Actions

Each finding generates one or more remediation actions. Actions can be created by the auditor or by management in their response:

**Navigate to: Finding → Actions → New Action**

**Action fields:**

| Field | Example | Notes |
|---|---|---|
| Action Title | Configure MRBR dual authorization in SAP | Short, specific |
| Action Description | Configure SAP workflow to require... | Detailed steps |
| Action Owner | Jane Smith (IT SAP Team) | Individual accountable |
| Due Date | 2026-10-31 | Specific date |
| Priority | High | Inherited from finding severity |
| Evidence Required | Screenshot of SAP configuration + test evidence | What must be provided on completion |
| Verification Required | Yes — auditor will independently verify | Whether audit team verifies |
| Finding Reference | F-2026-003 | Auto-linked |

### 8.2 Owner Assignment and Acceptance

When an action is created, the assigned owner receives a notification:

```
Subject: Action Required — Audit Finding Remediation

You have been assigned an audit remediation action:
Finding: Duplicate Invoice Detection Control Not Operating Effectively (Finding F-2026-003)
Action: Configure SAP MRBR dual authorization
Due Date: 31 October 2026

Please review and accept or escalate this action via the GovernexPlus portal.
```

The owner must **accept** the action (acknowledging responsibility) or escalate to their manager if they cannot be accountable. Unaccepted actions are escalated automatically after 5 business days.

### 8.3 Progress Updates

Action owners provide progress updates throughout the remediation period:

1. Navigate to **Actions → [Action]**
2. Click **Add Update**:
   ```
   Date: 2026-09-15
   Update: SAP configuration change has been submitted as a change request (CR-4521).
   Change scheduled for the next maintenance window on 2026-10-05.
   Testing will be conducted 2026-10-06–10.
   Completion expected by 2026-10-15, ahead of the 2026-10-31 deadline.
   ```
3. Updates are timestamped and logged
4. The finding's action dashboard reflects the latest status

### 8.4 Closing with Evidence

When the action is complete:

1. Action owner navigates to the action and clicks **Submit for Closure**
2. Uploads completion evidence (screenshot, test results, confirmation email)
3. Writes completion narrative:
   ```
   MRBR dual authorization configured and tested. System now requires manager
   approval before any blocked invoice can be released. Test performed on
   2026-10-07 confirming control operates as designed (screenshots attached).
   Also attached: IT change request CR-4521 approved and implemented record.
   ```
4. Marks action as **Completed — Pending Verification**

### 8.5 Independent Verification by Auditor

After the owner submits for closure:

1. Auditor receives notification: "Action A-001 submitted for verification"
2. Navigate to **Actions → [Action]**
3. Review the completion evidence:
   - Is the evidence specific enough?
   - Does it demonstrate the control is now operating effectively?
   - Is it consistent with the finding's root cause being addressed?
4. Run a verification procedure if needed (e.g., test the control yourself)
5. Conclude:
   - **Verified — Closed**: Evidence is sufficient, action is complete, finding is remediated
   - **Verification Failed — Reopen**: Evidence is inadequate, action is not complete, return to owner with explanation

### 8.6 Overdue Escalation

GovernexPlus automatically escalates overdue actions:

| Days Past Due | Action |
|---|---|
| 7 days | Email reminder to action owner |
| 14 days | Email to action owner + their manager |
| 30 days | Email to action owner + manager + CAE |
| 60 days | CAE may escalate to Audit Committee |

**Action aging dashboard:**

Navigate to **Audit → Action Tracker** for a cross-engagement view:

```
Action Aging Summary — All Engagements
Open Actions: 47
  Current (not due): 28
  Due within 7 days: 6
  Overdue 1–30 days: 9
  Overdue 31–60 days: 3
  Overdue 60+ days: 1 ← Escalated to Audit Committee
```

---

## 9. Evidence Management

### 9.1 The Evidence Repository

GovernexPlus maintains a centralized evidence repository separate from (but linked to) the workpaper system:

- **Workpapers**: Auditor-prepared documentation (your analysis, narratives, test workpapers)
- **Evidence**: Source documents, system extracts, and raw material (what you obtained from management or systems)

Both are stored in GovernexPlus, but evidence has additional features: integrity hashing, legal hold, and auto-collection.

### 9.2 Uploading Evidence

**Navigate to: Evidence → New Evidence Item**

Or upload directly from a workpaper or finding: **[Workpaper] → Attach Evidence**

**Evidence metadata:**

| Field | Example | Notes |
|---|---|---|
| Title | Q2 2026 AP Invoice Population Extract | |
| Document Type | System Extract | Document/Screenshot/Email/Extract/Report |
| Source | SAP S/4HANA PRD — ME2M report | Who/what provided this |
| Collection Method | System query (automated) / Manual request / Evidence Agent | How obtained |
| Collection Date | 2026-08-10 | When obtained |
| Period Covered | April–June 2026 | Data period |
| Format | XLSX | File type |
| SHA-256 Hash | (auto-calculated on upload) | Integrity fingerprint |
| Engagement | AP Review Q3 2026 | |
| Procedure Reference | WP-1.1 | |
| Sensitivity | Standard / Restricted / Confidential | Access controls |

### 9.3 SHA-256 Integrity Verification

Every file uploaded to the evidence repository is:
1. **Hashed at upload time**: SHA-256 hash calculated and stored
2. **Periodically re-verified**: System re-hashes the file weekly and compares to stored hash
3. **Verified on access**: Hash is recalculated when you open the file and compared

If a hash mismatch is detected (indicating the file was altered after upload):
- An alert is generated for the CAE and the relevant auditor
- The file is marked "INTEGRITY ALERT — Do not use as evidence without investigation"
- A security incident is created for investigation

**Manual integrity check:**

At any time, an auditor can re-verify evidence integrity:
```
Evidence → [Item] → Verify Integrity
Result: "Verified — File matches stored hash (SHA-256: a1b2c3...)"
```

This is important for external audit or legal proceedings — you can demonstrate that evidence was not altered after collection.

### 9.4 Legal Hold

Evidence under legal hold cannot be deleted or modified:

**Placing legal hold:**

```
Evidence → [Item] → Actions → Apply Legal Hold
Reason: "SEC investigation, notice received 2026-08-01"
```

Effects:
- File is locked from modification or deletion by anyone (including admins)
- Hold reason and date are permanently recorded
- Deletion attempt generates an error and an audit log entry

**Releasing legal hold** (requires CAE authorization):

```
Evidence → [Item] → Actions → Release Legal Hold
Authorization: Requires second approval from CAE or legal team
```

### 9.5 Evidence Agent — Automated Collection

The Evidence Agent AI module automatically collects evidence from connected systems, dramatically reducing the time spent on manual evidence gathering.

**Navigate to: AI → Evidence Agent**

**Configuring Evidence Agent for an engagement:**

1. Select engagement
2. Select the procedures needing evidence
3. Agent presents a collection plan:
   ```
   Procedure WP-4.1 (AP User SoD Analysis):
   Auto-collect: Risk Intelligence Engine analysis for all AP department users
   Source: GovernexPlus Risk Intelligence Engine module
   Format: PDF report + Excel detail
   Status: Ready to collect

   Procedure WP-4.3 (Certification Campaign Completeness):
   Auto-collect: Q2 2026 UAR campaign results for Finance scope
   Source: GovernexPlus Certification module
   Format: PDF campaign report
   Status: Ready to collect

   Procedure WP-1.1 (3-Way Match Testing):
   Requires: Population extract from SAP (MIRO/LIV transactions)
   Manual request needed: Send documentation request to IT team
   Cannot auto-collect: SAP direct query requires admin approval
   Status: Manual request needed
   ```
4. Approve the collection plan
5. Agent collects what it can automatically (with timestamp and hash)
6. Agent generates documentation requests for items requiring manual collection

**Typical evidence reduction:**

For ITGC and access control procedures, Evidence Agent auto-collects 60–70% of required evidence, reducing manual collection burden significantly.

### 9.6 Evidence Inventory and Gap Analysis

Before concluding fieldwork, run the evidence gap analysis:

**Navigate to: Engagement → Evidence → Gap Analysis**

The system checks:
- Every procedure that is cleared has at least one piece of evidence linked
- Every finding has supporting workpapers and evidence
- Every exception has a corresponding source document
- No evidence is linked to a procedure that was marked N/A

Any gaps are flagged for resolution before the report is issued.

---

## 10. Reporting

### 10.1 Engagement Reports

**Navigate to: Engagement → Generate Report → Engagement Report**

**Report structure (auto-generated):**

```
INTERNAL AUDIT REPORT
Accounts Payable Process Review — Q3 2026

1. EXECUTIVE SUMMARY
   [Auto-generated from engagement objectives + finding summary]

2. BACKGROUND AND SCOPE
   Entity: Accounts Payable Process
   Audit Period: April–June 2026
   Systems: SAP S/4HANA PRD, SAP SRM
   Scope: Invoice processing, payment execution, vendor master management

3. AUDIT OBJECTIVES AND METHODOLOGY
   [From engagement setup + work program]

4. SUMMARY OF FINDINGS
   [Auto-generated table: Finding ID, Title, Severity, Action Count, Status]

5. DETAILED FINDINGS
   Finding F-2026-003: Duplicate Invoice Detection Control...
   [CCCE full text, management response, auditor note]

   Finding F-2026-004: Vendor Bank Account Changes...
   [CCCE full text, management response, auditor note]

6. MANAGEMENT RESPONSES
   [Compiled management responses with action due dates]

7. APPENDICES
   A. Scope details and population information
   B. Risk Intelligence Engine analysis summary for AP users
   C. Certification campaign completeness data
   D. Open action tracker
```

**Customizing the report:**

Before generating, you can:
- Select which sections to include/exclude
- Add an overall audit conclusion (Satisfactory / Needs Improvement / Unsatisfactory)
- Include/exclude specific appendices
- Select format: Word (editable), PDF (final), PPTX (committee presentation)

### 10.2 Audit Dashboard

**Navigate to: Audit → Dashboard**

The audit dashboard provides a real-time view of the internal audit program:

[Screenshot: Audit Dashboard with engagement pipeline, finding severity chart, action aging, and annual plan progress]

**Key metrics:**

- **Engagements by Stage**: Pipeline view showing how many engagements are in each stage
- **Finding Severity Distribution**: This period vs. prior period
- **Action Aging**: Open actions by age bucket
- **Plan Completion**: % of annual plan engagements in Closed status
- **Issue Recurrence Rate**: % of current findings that are repeats of prior findings
- **Average Issue Age**: How long findings stay open before being verified closed
- **Coverage by Risk Score**: % of Priority 1 entities audited this year

### 10.3 Board-Level / Committee Reports

For presentation to the Board Audit Committee or senior management:

**Navigate to: Audit → Reports → Committee Report**

**Committee report includes:**

- GRC Health Score (0–100 composite score from all four pillars)
- Risk profile summary (RM heat map, trend)
- Access risk exposure (AC violations, trend)
- Control effectiveness (PC testing results, deficiency count)
- Audit program status (plan completion, key findings, action status)
- Key metrics vs. prior quarter
- Forward look (upcoming engagements, key risks on horizon)

**PPTX generation:**

GovernexPlus generates a boardroom-ready PowerPoint presentation:
- Clean slide design with your organization's logo (configurable)
- Charts auto-generated from live data
- Narrative text from AI-generated summaries
- Presenter notes populated for each slide

### 10.4 Cross-Pillar Evidence for External Auditors

External auditors (Big 4 or local CPA firms) performing the annual financial statement audit often rely on internal audit's work. GovernexPlus facilitates this through:

**External auditor access:**

Create a time-limited guest account with `auditor` role scoped to specific engagements:
```
Admin → Users → New External Auditor
Access scope: Engagement ID: ENG-2026-047 (SOX Testing Q3)
Access expires: 2026-12-31
Can export: Yes (watermarked PDFs)
```

**SOX reliance package:**

Navigate to **Reports → SOX Reliance Package**

Auto-generates a structured package for the external auditor containing:
- Internal audit's SOX engagement reports
- ITGC testing results with evidence links
- Key control certifications with sign-off chain
- Open deficiency status
- Management representation letters

---

## 11. Compliance Workflows

### 11.1 SOX Sign-Off Cascade

The SOX sign-off cascade in GovernexPlus formalizes the management certification process required by SOX Section 302 and supports Section 404 attestation.

**The cascade structure:**

```
Level 1 — Control Owner Sign-Off
  Each control owner certifies their controls operated effectively
  Provides supporting evidence reference
  Discloses any exceptions

Level 2 — Process Owner Sign-Off
  Reviews and certifies all control sign-offs in their process
  Aggregates exceptions and assesses materiality
  Can override control owner's effective conclusion (with documentation)

Level 3 — Management Sign-Off (CFO/CEO)
  Reviews aggregated process certifications
  Certifies that internal controls over financial reporting are effective
  Discloses any material weaknesses or significant deficiencies
  This sign-off feeds the 302 certification language
```

**Configuring the cascade:**

Navigate to **Compliance → SOX → Configure Cascade**

1. Define the sign-off levels and who is responsible at each level
2. Map controls to the appropriate process owners
3. Map process owners to the CFO/CEO sign-off
4. Set the sign-off period and deadlines
5. Configure reminder and escalation schedule

**Running a sign-off cycle:**

1. Navigate to **Compliance → SOX → New Sign-Off Cycle**
2. Select the period (Q1 2026, Year-end 2026, etc.)
3. Click **Launch** — all Level 1 control owners receive notification
4. Monitor completion dashboard:
   - Level 1 completion: XX% complete
   - Exceptions disclosed: N
   - Issues escalated to Level 2: N
5. When Level 1 complete, auto-advance to Level 2
6. When Level 2 complete, auto-advance to Level 3 (CFO/CEO)

**Audit trail for sign-off:**

Every sign-off is digitally recorded with:
- Signer identity (verified against JWT — cannot be forged)
- Timestamp
- Representation text (standard language + any qualifications)
- Exception disclosures
- Supporting control test reference

This provides a legally defensible audit trail for management certifications.

[Screenshot: SOX Sign-Off cascade dashboard showing three levels with completion status and exception disclosures]

### 11.2 Framework Mapping

GovernexPlus maps controls to regulatory and best-practice frameworks:

**Supported frameworks:**

| Framework | Version | Coverage |
|---|---|---|
| COSO Internal Control — Integrated Framework | 2013 | 17 principles, 5 components |
| COBIT | 2019 | 40 governance objectives |
| ISO 27001 | 2022 | 93 Annex A controls |
| SOX | Section 302, 404 | Financial reporting controls |
| NIST CSF | 2.0 | 6 functions, 22 categories |
| GDPR | 2018 | 99 articles, key processing controls |
| HIPAA | Security Rule | Administrative, physical, technical safeguards |
| PCI DSS | 4.0 | 12 requirements |

**Configuring framework mappings:**

Each control in the PC library can be mapped to one or more framework requirements:

```
Control: AP-003 — 3-Way Match Verification
COSO Mapping:
  Component: Control Activities (Principle 10.3)
  Principle: Select and Develop Control Activities
ISO 27001 Mapping:
  A.12.4.1 — Event logging
SOX Mapping:
  Section 404: Financial reporting control
  PCAOB AS 2201 relevant assertion: Authorization
```

**Framework coverage report:**

Navigate to **Compliance → Framework Coverage**

Shows heat map of which framework requirements are covered by existing controls and which have gaps:
- Green: Covered by effective controls
- Yellow: Covered by controls with open deficiencies
- Red: Not covered (gap)

This is invaluable for framework gap assessments and regulatory readiness reviews.

### 11.3 Control Testing Schedules

Maintain a master control testing schedule aligned to risk and regulatory requirements:

**Navigate to: Compliance → Testing Schedule**

**Schedule view:**

```
Control Testing Schedule — FY2027

Control | Type | Frequency | Q1 | Q2 | Q3 | Q4 | Owner | Tester
AP-003  | Detective | Quarterly | ✓ | 🕐 | 📋 | 📋 | J.Smith | L.Park
AP-011  | Preventive | Annual | | | ✓ | | M.Chen | S.Johnson
IT-001  | Automated | Continuous | ∞ | ∞ | ∞ | ∞ | IT Team | CCM
SOX-FI-3| Manual | Semi-annual | ✓ | | 📋 | | CFO | M.Chen

Legend: ✓=Complete  🕐=In Progress  📋=Planned  ∞=Continuous
```

**Schedule management:**

- Automatically reminds testers 30 days before scheduled test
- Links to work program template for efficient setup
- Tracks actual vs. planned dates
- Generates testing calendar for CAE planning

### 11.4 Deficiency Tracking

**Navigate to: Compliance → Deficiencies**

All control deficiencies (from PC testing + Risk Intelligence Engine SoD bridge) are tracked in a unified register:

**Deficiency classification:**

| Classification | Definition | Disclosure |
|---|---|---|
| Control Deficiency | A deficiency in the design or operation of a control that does not rise to a significant deficiency | Internal management report |
| Significant Deficiency | A deficiency, or a combination of deficiencies, that is less severe than a material weakness yet important enough to merit attention by those responsible for oversight | Audit committee disclosure |
| Material Weakness | A deficiency, or a combination of deficiencies, that results in a reasonable possibility that a material misstatement of the company's annual or interim financial statements will not be prevented or detected on a timely basis | Public disclosure (SOX) |

**Deficiency lifecycle:**

```
Deficiency Identified
  → Classification Assessment
  → Management Response
  → Remediation Plan
  → Remediation Execution
  → Retesting
  → Closed (if remediated effectively)
  OR
  → Escalated (if remediation ineffective or delayed)
```

**Deficiency dashboard:**

- Open deficiencies by severity (Material Weakness / Significant Deficiency / Control Deficiency)
- Days open distribution (are deficiencies getting older?)
- Remediation plan status (on track / at risk / overdue)
- Deficiency source (internal audit finding / management self-assessment / external audit)
- Entity and process breakdown

### 11.5 GovernexPlus as Audit Evidence

When presenting GovernexPlus data as audit evidence (to external auditors or regulators):

**Citing GovernexPlus data:**

Always include:
- Data query date and time
- Tenant ID and environment (production)
- Query parameters (date range, filters applied)
- Record count at time of extraction
- GovernexPlus version

**Providing to external auditors:**

Use the export function which includes a cover page with:
- Organization name and tenant
- Report type and parameters
- Extraction date and time
- SHA-256 hash of the extract
- GovernexPlus version and environment

**Immutability representation:**

GovernexPlus audit logs are immutable (no update/delete operations). You can provide a representation letter to external auditors stating: "GovernexPlus [version] deployed at [organization] maintains an immutable audit trail for all state-changing operations. GovernexPlus data has not been modified since the period under audit."

---

*This guide is maintained by the GovernexPlus Product Team. For corrections or feedback, contact product-docs@governexplus.io*

*External Auditor Access: For questions about using GovernexPlus evidence in an external audit, contact your GovernexPlus engagement lead or support@governexplus.io*

*Last updated: September 2026 | Version 2.0*
