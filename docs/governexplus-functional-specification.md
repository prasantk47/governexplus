# Governex+ Platform - Functional Specification
**Version:** 1.0 | **Date:** September 4, 2026 | **Status:** Production-Ready

---

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [Access Control (AC)](#2-access-control-ac)
3. [Risk Management (RM)](#3-risk-management-rm)
4. [Process Control (PC)](#4-process-control-pc)
5. [Audit Management (AM)](#5-audit-management-am)
6. [Cross-Module Integration (XI)](#6-cross-module-integration-xi)
7. [Non-Functional Capabilities (NF)](#7-non-functional-capabilities-nf)
8. [System Architecture](#8-system-architecture)
9. [API Reference Summary](#9-api-reference-summary)
10. [Data Model Summary](#10-data-model-summary)

---

## 1. Platform Overview

Governex+ is an enterprise Governance, Risk, and Compliance (GRC) platform built to replace SAP GRC Access Control 12.0 and expand into full GRC suite coverage. It provides four integrated pillars:

- **Access Control (AC)** - SoD risk analysis, access requests, emergency access, certification
- **Risk Management (RM)** - Enterprise risk register, assessments, KRIs, incidents
- **Process Control (PC)** - Control library, testing, CCM, deficiency management, SOX sign-off
- **Audit Management (AM)** - Audit planning, engagements, findings (CCCE), action tracking

### Platform Statistics
| Metric | Value |
|--------|-------|
| API Routes | 912 |
| Database Tables | 81 |
| SoD Rules (delivered) | 128 |
| Frontend Pages | 50+ |
| Supported Connectors | SAP RFC, Azure AD, Okta, Workday, SuccessFactors, ServiceNow |

---

## 2. Access Control (AC)

### 2.1 Risk & Ruleset Library (AC-01 to AC-06)

**Purpose:** Manage the SoD conflict rules and risk definitions that drive risk analysis.

**Flow:**
```
Rule Library (121 built-in rules)
    |
    v
Tenant loads rules at startup --> SoDRulesetLibrary
    |
    v
Rules bridge into two engines:
    - core/rules/engine.py (128 rules)
    - core/ara/rules.py (129 rules)
    |
    v
Custom rules created via API --> RiskRuleModel (DB)
    |
    v
Tenant can enable/disable built-in rules --> TenantRulePreference
```

**Key Capabilities:**
- 121 pre-built SoD rules covering: FI, MM, SD, HR, BA, TR, AA, WM, QM, PM, PS, XP
- Custom risk/function/rule creation with Z-transaction support
- Rule attributes: ID, description, severity (Critical/High/Medium/Low), business process, risk type
- Rule versioning and change history
- Import/export via Excel/CSV
- Rules are idempotent on load - existing custom rules never overwritten

**API Endpoints:**
- `GET /sod-rules/` - List all rules
- `POST /sod-rules/` - Create custom rule
- `PUT /sod-rules/{rule_id}` - Update rule
- `GET /risk/rules` - Get rule engine stats
- `POST /sod-rules/import` - Import rules from file

---

### 2.2 Access Risk Analysis - ARA (AC-10 to AC-18)

**Purpose:** Detect SoD conflicts, sensitive access, and critical permissions across users and roles.

**Flow:**
```
Trigger: User request / Scheduled batch / Ad-hoc
    |
    v
ARA Engine loads user access (roles, entitlements)
    |
    v
Per-User Analysis:
    1. SoD Conflict Detection (function-pair conflicts)
    2. Sensitive Access Check (critical tcodes, auth objects)
    3. Cross-Role Conflict Detection
    |
    v
Risk Scoring:
    - Base score from rule severity
    - Context modifiers (user department, location)
    - Usage modifiers (does user actually execute conflicting tcodes?)
    |
    v
Results persisted --> RiskViolation (DB) via RiskViolationRepository
    |
    v
Dashboard / Reports / Remediation
```

**Key Capabilities:**
- **User-level analysis** - All SoD conflicts for a single user
- **Role-level analysis** - Conflicts within a role definition
- **Cross-role analysis** - Conflicts across multiple assigned roles
- **What-if simulation** - Test impact of adding/removing roles before assignment
- **Usage-aware scoring** - Reduce false positives by checking actual tcode usage
- **Batch analysis** - Scheduled full-landscape scan with delta processing (AC-12)
- **Org-level ranking** - Violations aggregated by department/company code (AC-16)
- **Dormant detection** - Flag inactive accounts with sensitive access (AC-18)

**Analysis Output per Violation:**
| Field | Description |
|-------|-------------|
| violation_id | Unique identifier |
| rule_id | Which SoD rule triggered |
| user_id | Affected user |
| severity / severity_score | Risk level (0-100) |
| conflicting_functions | List of conflicting business functions |
| conflicting_entitlements | Specific auth object values |
| business_impact | Plain-text impact description |
| status | open / in_progress / mitigated / remediated / accepted |
| is_mitigated | Whether a compensating control is assigned |

**API Endpoints:**
- `GET /ara/analyze/user/{user_id}` - Analyze single user
- `POST /ara/simulate` - What-if simulation
- `GET /risk/violations` - List all violations
- `GET /risk/org-ranking` - Org-level violation ranking
- `GET /users/dormant` - Dormant account detection

---

### 2.3 Mitigation Controls (AC-13)

**Purpose:** Compensating controls assigned to SoD violations that cannot be remediated.

**Flow:**
```
SoD Violation detected
    |
    v
Cannot remediate (business requirement for dual access)
    |
    v
Assign Mitigation Control:
    - Control type: preventive / detective / manual
    - Owner, validity period, monitoring frequency
    - Links to specific rule IDs
    |
    v
Monitor: periodic effectiveness testing
    |
    v
Recertify: mitigation control review campaigns
```

**Key Capabilities:**
- Define controls with owner, validity dates, monitoring frequency
- Link controls to specific risk rule IDs
- Track effectiveness testing (passed/failed/partial)
- Mitigation monitoring dashboard with recertification

**API Endpoints:**
- `GET/POST /mitigation/controls` - List/create controls
- `PUT /mitigation/controls/{id}` - Update control
- `GET /mitigation-monitoring/` - Monitoring dashboard

---

### 2.4 Access Request Management - ARM (AC-20 to AC-24)

**Purpose:** Self-service role requests with risk-aware approval workflows.

**Flow:**
```
User submits access request:
    - Select roles from catalog (or copy from Model User)
    - Provide business justification
    - Set priority
        |
        v
Shopping Cart (optional):
    - Add multiple roles to cart
    - Local SoD check per item
    - Submit all at once
        |
        v
Inline Risk Analysis:
    - ARA engine runs what-if simulation
    - Violations flagged with severity
        |
        v
Multi-Stage Approval (MSMP-style):
    Stage 1: Manager approval
    Stage 2: Role owner approval
    Stage 3: Security team (if high risk)
    Custom stages via workflow engine
        |
        v
Risk-Aware Decisions:
    - Auto-hold if critical violations found
    - Require mitigation assignment before approval
    - Auto-inject additional approval stages
        |
        v
Approved --> Provisioning:
    - SAP RFC: assign roles via BAPI
    - Azure AD: add group membership
    - Okta: assign application
        |
        v
Audit Trail: AccessRequestLog (DB)
```

**Key Capabilities:**
- Role catalog with business-friendly descriptions
- Model User: copy access from a reference user
- Shopping cart for bulk requests
- Inline risk preview during request and approval
- Multi-stage configurable workflows with delegation and escalation
- Automated provisioning to SAP, Azure AD, Okta
- JML automation from HR events (Workday, SuccessFactors)

**API Endpoints:**
- `GET/POST /access-requests/` - List/create requests
- `GET /access-requests/pending` - Pending approvals
- `POST /access-requests/{id}/approve` - Approve request
- `POST /access-requests/{id}/reject` - Reject request
- `GET /arm/cart` - Get shopping cart
- `POST /arm/cart/items` - Add to cart

---

### 2.5 Emergency Access Management - EAM / Firefighter (AC-30 to AC-33)

**Purpose:** Controlled elevated access for emergency situations with full audit trail.

**Flow:**
```
User requests firefighter access:
    - Select firefighter ID
    - Provide reason code + justification
    - Specify duration
        |
        v
Approval:
    - Firefighter ID owner/controller reviews
    - Reason code validated against vocabulary
    - Ticket reference checked (if policy requires)
        |
        v
Session Activation:
    - SAP: lock firefighter user, set temp password via RFC
    - Timer starts (countdown)
    - Live monitoring active
        |
        v
During Session:
    - All transactions logged (via SAP SM20/STAD)
    - Real-time activity capture
    - Can extend (with re-approval) or terminate early
        |
        v
Session End:
    - Auto-terminate at expiry
    - SAP: re-lock firefighter user
    - Transaction log captured
        |
        v
Post-Session Review:
    - Controller reviews activity log
    - AI summary: "3 txns consistent with reason; 1 anomalous"
    - Controller signs off or flags
        |
        v
Audit Trail: FirefighterRequest + FirefighterSession + FirefighterActivity (DB)
```

**Key Capabilities:**
- Reason-coded requests with ticket reference policies
- Timed sessions with remaining time tracking
- Real SAP RFC operations (lock/unlock/temp password)
- Live session monitoring
- Post-session review workflow with controller sign-off
- Usage reporting dashboards
- Per-tenant manager instances (production-grade isolation)

**API Endpoints:**
- `GET /firefighter/dashboard` - FF dashboard
- `POST /firefighter/request` - Request FF access
- `POST /firefighter/approve/{id}` - Approve request
- `GET /firefighter/sessions` - List sessions
- `GET /firefighter/monitoring/live` - Live monitoring

---

### 2.6 Access Certification - UAR (AC-40 to AC-43)

**Purpose:** Periodic review of user access with campaign management.

**Flow:**
```
Create Certification Campaign:
    - Define scope (department, role type, etc.)
    - Set due date and reviewers
    - Select type: user_access / role_membership
        |
        v
Generate Review Items:
    - Query actual user-role assignments from DB
    - For each user-role pair, create CertificationItem
    - Assign to appropriate reviewer (manager/role owner)
        |
        v
Review Process:
    - Reviewer sees all items in their queue
    - For each item: Certify (keep) or Revoke
    - Risk context shown per item
        |
        v
Revocation:
    - Rejected items trigger de-provisioning workflow
    - Completion tracking and audit trail
        |
        v
Campaign Dashboard:
    - Progress tracking
    - Escalation for overdue reviewers
    - Completion report
```

**Key Capabilities:**
- User access review campaigns
- Role membership review campaigns
- Mitigating control certification
- Auto-removal workflows for rejected access
- Campaign progress dashboards with escalation
- DB-persisted campaigns (CertificationCampaignLog, CertificationItemLog)

**API Endpoints:**
- `GET/POST /certification/campaigns` - List/create campaigns
- `GET /certification/campaigns/{id}/items` - Get review items
- `POST /certification/items/{id}/decide` - Certify/revoke

---

### 2.7 Role Engineering (AC-50 to AC-52)

**Purpose:** Design, test, and maintain authorization roles with built-in SoD checks.

**Key Capabilities:**
- Role design with inline SoD check at build time
- Role mining from usage data (heuristic clustering)
- Business role model (composite roles mapped to technical roles)
- Role comparison and consolidation suggestions
- Role drift detection (production vs. designed)

**API Endpoints:**
- `GET /role-engineering/catalog` - Role catalog
- `GET /role-engineering/mining` - Role mining
- `POST /role-engineering/design` - Design role
- `GET /drift/` - Drift detection

---

## 3. Risk Management (RM)

### 3.1 Risk Register (RM-01 to RM-04)

**Purpose:** Central register of all enterprise risks with structured taxonomy.

**Flow:**
```
Identify Risk:
    - Title, description (EN + AR bilingual)
    - Category: strategic / operational / financial / compliance / IT-cyber
    - Assign to org unit and risk owner
        |
        v
Score Risk:
    - Inherent: Likelihood (1-5) x Impact (1-5) = Score
    - Score auto-computed on create/update
        |
        v
Risk Register:
    - Searchable, filterable list
    - Linked to controls (PC), findings (AM), violations (AC)
    - Review frequency and next review date
```

**Data Model:**
| Field | Type | Description |
|-------|------|-------------|
| risk_id | String | Auto-generated RSK-XXXXXXXX |
| title | String | Risk title |
| description_ar | String | Arabic description (NF-04) |
| category | Enum | strategic/operational/financial/compliance/it_cyber |
| inherent_likelihood | Int 1-5 | Likelihood before controls |
| inherent_impact | Int 1-5 | Impact before controls |
| inherent_score | Float | Auto-computed L x I |
| residual_likelihood | Int 1-5 | After controls |
| residual_impact | Int 1-5 | After controls |
| residual_score | Float | Auto-computed |
| risk_appetite | Float | Acceptable risk level |
| risk_tolerance | Float | Maximum tolerable risk |
| related_control_ids | JSON | Links to PC controls |
| related_finding_ids | JSON | Links to AM findings |

**API Endpoints:**
- `GET/POST /risk-management/risks` - CRUD
- `GET /risk-management/risks/{risk_id}` - Detail with counts
- `PUT /risk-management/risks/{risk_id}` - Update (recomputes scores)
- `DELETE /risk-management/risks/{risk_id}` - Soft delete

---

### 3.2 Risk Assessment (RM-10 to RM-12)

**Purpose:** Periodic and ad-hoc risk assessments with multi-assessor workflows.

**Flow:**
```
Create Assessment (periodic / ad-hoc / consensus):
    - Assessor scores likelihood + impact
    - Provides rationale and monetary impact estimate
        |
        v
Submit --> Review:
    - Reviewer validates scores
    - On approval: updates risk's residual scores
        |
        v
Assessment Campaign:
    - Bulk-create assessments for all risks matching filters
    - Track completion across assessors
```

**API Endpoints:**
- `POST /risk-management/risks/{id}/assessments` - Create
- `PUT /risk-management/assessments/{id}/submit` - Submit
- `PUT /risk-management/assessments/{id}/review` - Review (updates residual)
- `POST /risk-management/assessment-campaigns` - Bulk campaign

---

### 3.3 Risk Appetite & Tolerance (RM-03)

**Purpose:** Define acceptable risk levels per category and org unit.

**Flow:**
```
Set Appetite (per category / org unit):
    - appetite_score: target risk level
    - tolerance_score: maximum acceptable
        |
        v
Appetite Breach Check:
    - Compare risk's residual_score to appetite
    - Returns: within_appetite / approaching_tolerance / breach
```

**API Endpoints:**
- `POST /risk-management/appetites` - Set appetite
- `GET /risk-management/appetites` - Get appetites
- `GET /risk-management/risks/{id}/appetite-check` - Check breach

---

### 3.4 Key Risk Indicators - KRI (RM-13)

**Purpose:** Early warning metrics with traffic-light monitoring.

**Flow:**
```
Define KRI:
    - Name, linked risk, data source
    - Thresholds: green / amber / red
    - Measurement frequency
        |
        v
Record Measurements:
    - Manual or automated data feed
    - Auto-compute status: normal / warning / breach
    - Historical trend tracking
        |
        v
KRI Dashboard:
    - All KRIs grouped by status
    - Sparkline history per KRI
    - Breach alerts
```

**Status Logic:**
```
value <= threshold_green  --> NORMAL (green)
value <= threshold_amber  --> WARNING (amber)
value > threshold_amber   --> BREACH (red)
```

**API Endpoints:**
- `POST /risk-management/kris` - Create KRI
- `POST /risk-management/kris/{id}/measurements` - Record value
- `GET /risk-management/kris/dashboard` - Traffic-light dashboard
- `GET /risk-management/kris/{id}/history` - History

---

### 3.5 Risk Response (RM-20)

**Purpose:** Document and track response plans for identified risks.

**Response Types:** Accept / Mitigate / Transfer / Avoid

**Flow:**
```
Create Response Plan:
    - Type, description, owner
    - Action items with due dates
        |
        v
Track Progress:
    - Status: planned --> in_progress --> completed
    - Effectiveness rating on completion
```

**API Endpoints:**
- `POST /risk-management/risks/{id}/responses` - Create plan
- `PUT /risk-management/responses/{id}/status` - Update status
- `GET /risk-management/risks/{id}/responses` - List responses

---

### 3.6 Incidents & Loss Events (RM-22)

**Purpose:** Capture loss events and link them to risks for likelihood recalibration.

**Flow:**
```
Report Incident:
    - Title, description, severity
    - Financial impact + currency
    - Occurred/detected/resolved dates
        |
        v
Link to Risk:
    - Associates incident with enterprise risk
    - Recalibrates likelihood based on occurrence
        |
        v
Track Resolution:
    - Root cause analysis
    - Corrective actions
    - Status: reported --> investigating --> resolved --> closed
```

**API Endpoints:**
- `POST /risk-management/incidents` - Report
- `POST /risk-management/incidents/{id}/link-risk` - Link
- `GET /risk-management/incidents` - List

---

### 3.7 RM Reporting (RM-12, RM-30, RM-31)

**Key Reports:**
| Report | Endpoint | Description |
|--------|----------|-------------|
| Risk Heatmap | `GET /risk-management/heatmap` | 5x5 grid, inherent + residual views |
| Risk Trends | `GET /risk-management/trends` | Monthly avg scores over time |
| Top Risks | `GET /risk-management/top-risks` | By residual score descending |
| Risk-Control Coverage | `GET /risk-management/risk-control-coverage` | Gaps where risks lack controls |
| Overdue Reviews | `GET /risk-management/overdue-reviews` | Past next_review_date |
| PPTX Export | `GET /reports/export/risk-report` | Full presentation deck |

---

## 4. Process Control (PC)

### 4.1 Control Library (PC-01 to PC-05)

**Purpose:** Central repository of all internal controls with full lifecycle management.

**Flow:**
```
Define Control:
    - Name, objective, description
    - Type: preventive / detective / corrective
    - Nature: manual / automated / IT-dependent
    - Frequency: continuous / daily / weekly / monthly / quarterly / annual
    - Process and subprocess classification
    - Key control flag (SOX material)
    - Owner assignment
        |
        v
Version Management:
    - Version auto-increments on update
    - Change history recorded as JSON
    - Status lifecycle: draft --> active --> under_review --> retired
        |
        v
Framework Mapping:
    - Link to COSO principles, COBIT objectives, ISO 27001, SOX
    - Coverage analysis per framework
```

**API Endpoints:**
- `GET/POST /process-control/controls` - CRUD
- `PUT /process-control/controls/{id}/retire` - Retire control
- `POST /process-control/controls/{id}/framework-mappings` - Map to framework
- `GET /process-control/frameworks/{id}/coverage` - Coverage analysis

---

### 4.2 Control Testing (PC-10 to PC-11)

**Purpose:** Test control design adequacy and operating effectiveness.

**Flow:**
```
Create Test:
    - Select control
    - Test type: design / operating_effectiveness / walkthrough
    - Define testing period, sample size, population
        |
        v
Execute Test:
    - Follow test steps
    - Document exceptions
    - Record evidence
        |
        v
Record Result:
    - Effective / Ineffective / Partially Effective
    - Exception count and details
    - Conclusion narrative
        |
        v
Auto-Deficiency Creation:
    - If result = "ineffective"
    - ControlDeficiency auto-created with source = "test"
    - Linked to the control and test
```

**API Endpoints:**
- `POST /process-control/controls/{id}/tests` - Create test
- `PUT /process-control/tests/{id}/result` - Record result
- `GET /process-control/controls/{id}/tests` - Test history

---

### 4.3 Deficiency Management (PC-13)

**Purpose:** Track control gaps from discovery through remediation to verified closure.

**Flow:**
```
Deficiency Identified (from test, CCM, self-assessment, or SoD bridge):
    |
    v
Status Machine:
    OPEN --> IN_REMEDIATION --> REMEDIATED --> VERIFIED_CLOSED
    |
    |-- severity: significant_deficiency / material_weakness / control_gap / observation
    |-- root cause analysis
    |-- remediation plan with owner and due date
    |
    v
Verify Closure:
    - Independent verification of remediation
    - Evidence of closure required
    - Verifier sign-off
```

**Severity Levels:**
| Level | Description |
|-------|-------------|
| Material Weakness | Reasonable possibility material misstatement not prevented/detected |
| Significant Deficiency | Less severe than MW but warrants attention |
| Control Gap | Missing or incomplete control |
| Observation | Minor issue, opportunity for improvement |

**API Endpoints:**
- `GET/POST /process-control/deficiencies` - CRUD
- `PUT /process-control/deficiencies/{id}/remediate` - Remediate
- `PUT /process-control/deficiencies/{id}/verify` - Verify closure

---

### 4.4 Continuous Control Monitoring - CCM (PC-20 to PC-25)

**Purpose:** Automated, scheduled monitoring of control effectiveness.

**Flow:**
```
Define CCM Rule:
    - Source system (SAP, Azure AD, etc.)
    - Rule type: config_check / data_pattern / threshold / sod_bridge
    - Check definition (JSON)
    - Frequency: realtime / hourly / daily / weekly
    - Auto-create deficiency on breach
        |
        v
Execution (scheduled or manual):
    - Run check against source system
    - Record CCMExecution result: pass / fail / error
    - If fail + auto_create_deficiency: create ControlDeficiency
        |
        v
SoD Bridge (XI-02):
    - When SoD violation count exceeds threshold
    - Auto-create deficiency with source = "sod_bridge"
    - Links AC violations to PC deficiency management
```

**Rule Types:**
| Type | Description | Example |
|------|-------------|---------|
| config_check | SAP parameter validation | Password length >= 8 |
| data_pattern | Transaction pattern detection | Duplicate vendor bank accounts |
| threshold | Metric threshold monitoring | Open PO value > $1M |
| sod_bridge | SoD violation count bridge | > 50 open violations = deficiency |

**API Endpoints:**
- `POST /process-control/ccm-rules` - Create rule
- `POST /process-control/ccm-rules/{id}/execute` - Execute single
- `POST /process-control/ccm/run-all` - Execute all due
- `GET /process-control/ccm/dashboard` - Pass/fail rates

---

### 4.5 Evidence Management (PC-15)

**Purpose:** Central evidence repository with integrity, versioning, and legal hold.

**Key Capabilities:**
- SHA-256 content hash for integrity verification
- Version chain (previous_version_id)
- Legal hold flag (prevents deletion/archival)
- Retention policies per document type
- Source module tracking (PC/RM/AM/AC)

**API Endpoints:**
- `POST /process-control/evidence` - Upload
- `GET /process-control/evidence/{id}` - Retrieve
- `PUT /process-control/evidence/{id}/legal-hold` - Toggle hold
- `GET /retention/policies` - Retention policies
- `POST /retention/apply` - Run retention batch
- `GET /retention/report` - Retention status

---

### 4.6 SOX Sign-Off Certification (PC-14)

**Purpose:** Cascading management certifications rolling up to CFO/CEO.

**Flow:**
```
Control Owner Sign-Off:
    - Certifies controls in scope are effective
    - Declares exceptions if any
        |
        v
Process Owner Sign-Off:
    - Rolls up control owner certifications
    - parent_certification_id links to child certs
        |
        v
CFO / CEO Sign-Off:
    - Top-level certification
    - Covers all process owner roll-ups
    - Status: certified / certified_with_exceptions / refused
```

**API Endpoints:**
- `POST /process-control/signoffs` - Create
- `PUT /process-control/signoffs/{id}/submit` - Submit certification
- `GET /process-control/signoffs/hierarchy` - Roll-up tree
- `GET /process-control/signoffs/pending` - Pending sign-offs

---

### 4.7 PC Reporting (PC-30 to PC-32)

**Key Reports:**
| Report | Endpoint | Description |
|--------|----------|-------------|
| Control Dashboard | `GET /process-control/dashboard` | By org, process, framework; failed controls; open issues |
| Framework Coverage | `GET /process-control/frameworks/{id}/coverage` | COSO/COBIT gap analysis |
| Audit-Ready Package | `GET /process-control/controls/{id}/audit-package` | Control + tests + evidence + sign-offs |
| PPTX Export | `GET /reports/export/control-report` | Presentation deck |

---

## 5. Audit Management (AM)

### 5.1 Audit Universe (AM-01)

**Purpose:** Inventory of all auditable entities with risk-based prioritization.

**Entity Types:** org_unit / process / system / project / vendor

**Risk Score Computation (XI-04):**
```
Composite Score = (RM weight x 0.40) + (PC weight x 0.35) + (AC weight x 0.25)
    - RM: max residual_score of linked risks
    - PC: open deficiency count for controls in org unit
    - AC: open violation count for users in org unit
```

**API Endpoints:**
- `GET/POST /audit-management/entities` - CRUD
- `POST /audit-management/entities/{id}/compute-risk` - Compute risk score

---

### 5.2 Audit Planning (AM-02 to AM-04)

**Purpose:** Risk-based annual/multi-year audit plans.

**Flow:**
```
Create Plan:
    - Name, fiscal year, type (annual/multi_year/special)
    - Total audit hours budget
        |
        v
Risk-Based Generation:
    - Auto-rank entities by composite risk score
    - Allocate top-N to plan
    - Distribute audit hours
        |
        v
Approval Workflow:
    draft --> pending_approval --> approved --> in_progress --> completed
        |
        v
Link Engagements to Plan
```

**API Endpoints:**
- `GET/POST /audit-management/plans` - CRUD
- `PUT /audit-management/plans/{id}/submit` - Submit for approval
- `PUT /audit-management/plans/{id}/approve` - Approve
- `POST /audit-management/plans/generate-risk-based` - Auto-generate

---

### 5.3 Audit Engagement Lifecycle (AM-10)

**Purpose:** Manage individual audit engagements from planning through closure.

**Lifecycle Pipeline:**
```
PLANNED --> ANNOUNCED --> FIELDWORK --> DRAFT_REPORT --> FINAL_REPORT --> CLOSED
    |           |            |              |               |             |
    |           |            |              |               |             |
    Plan &      Notify       Execute        Write           Issue         Archive
    Resource    auditee      procedures     findings        report        workpapers
    assign      team         & workpapers   & recommendations
```

Each stage advance is explicit and audited.

**API Endpoints:**
- `GET/POST /audit-management/engagements` - CRUD
- `PUT /audit-management/engagements/{id}/advance` - Move to next stage
- `GET /audit-management/engagements/{id}/report` - Generate report

---

### 5.4 Audit Procedures & Workpapers (AM-11 to AM-12)

**Purpose:** Structured audit execution with dual sign-off.

**Flow:**
```
Work Program (reusable template):
    - Ordered procedure steps
    - Clone for each engagement
        |
        v
Procedure Execution:
    - Assigned to auditor
    - Status: not_started --> in_progress --> completed --> reviewed
    - Conclusion documented
    - Hours tracked
        |
        v
Dual Sign-Off:
    1. Preparer completes and documents conclusion
    2. Reviewer validates work and adds review notes
        |
        v
Workpapers:
    - Narrative documents, schedules, extracts
    - Version chain with previous_version_id
    - Review workflow: pending_review --> reviewed / revision_needed
    - Cross-references to other procedures
```

**API Endpoints:**
- `POST /audit-management/work-programs` - Create template
- `POST /audit-management/engagements/{id}/procedures` - Create procedure
- `PUT /audit-management/procedures/{id}/complete` - Complete
- `PUT /audit-management/procedures/{id}/review` - Review
- `POST /audit-management/engagements/{id}/workpapers` - Create workpaper

---

### 5.5 Audit Findings - CCCE Format (AM-20, AM-22)

**Purpose:** Formal findings structured as Condition-Criteria-Cause-Effect.

**Finding Structure:**
| Field | Description |
|-------|-------------|
| **Condition** | What was found (the gap) |
| **Criteria** | What should be (the standard) |
| **Cause** | Why it happened (root cause) |
| **Effect** | Risk/impact of the gap |
| **Recommendation** | Proposed remediation |

**Cross-Module Links (XI-03):**
- `risk_id` --> EnterpriseRisk (RM)
- `control_id` --> ProcessControl (PC)
- `violation_id` --> RiskViolation (AC)

**Severity:** Critical / High / Medium / Low / Observation

**Repeat Finding Detection:** `prior_finding_id` links to previous findings; `check_repeat_finding` searches prior engagements for similar issues.

**API Endpoints:**
- `POST /audit-management/engagements/{id}/findings` - Create (CCCE)
- `PUT /audit-management/findings/{id}/management-response` - Record response
- `POST /audit-management/findings/{id}/link-risk` - Link to RM
- `POST /audit-management/findings/{id}/link-control` - Link to PC

---

### 5.6 Action Tracking (AM-21)

**Purpose:** Track management remediation actions with escalation.

**Flow:**
```
Action Created (from finding):
    - Description, owner, due date
        |
        v
Track Progress:
    open --> in_progress --> completed --> closed_verified
        |
        v
Close with Evidence:
    - Evidence of closure text
    - Link to evidence documents
        |
        v
Verify Closure:
    - Independent verification
    - Verifier sign-off
        |
        v
Overdue Escalation:
    - Auto-detect overdue actions
    - Escalation level increments
    - Management notification
```

**API Endpoints:**
- `POST /audit-management/findings/{id}/actions` - Create
- `PUT /audit-management/actions/{id}/close` - Close with evidence
- `GET /audit-management/actions/overdue` - Overdue list
- `POST /audit-management/actions/escalate` - Escalate overdue

---

### 5.7 AM Reporting (AM-30 to AM-32)

**Key Reports:**
| Report | Endpoint | Description |
|--------|----------|-------------|
| Engagement Report | `GET /audit-management/engagements/{id}/report` | Full report with findings & recommendations |
| Audit Dashboard | `GET /audit-management/dashboard` | Plan progress, findings by severity, overdue actions |
| Committee Report | `GET /audit-management/committee-report` | Board-level summary |
| PPTX Export | `GET /reports/export/audit-report/{id}` | Presentation deck |

---

## 6. Cross-Module Integration (XI)

### 6.1 Shared Infrastructure (XI-01, XI-06)

| Capability | Implementation |
|-----------|---------------|
| Single org hierarchy | `OrgUnit` model shared across all modules |
| Shared user model | `User` model with tenant scoping |
| Common workflow engine | `core/workflow/orchestrator.py` |
| Common notification engine | `core/notifications/delivery.py` |
| Common delegation model | `services/approver_service.py` |

### 6.2 SoD --> PC Deficiency Bridge (XI-02)

```
AC: SoD violation count per rule exceeds threshold
    |
    v
XI Bridge: sync_sod_to_deficiencies(threshold=10)
    |
    v
PC: ControlDeficiency created with source="sod_bridge"
    |
    v
PC: Deficiency remediated/closed
    |
    v
XI Bridge: sync_deficiency_resolution_to_violations()
    |
    v
AC: Related violations marked as REMEDIATED
```

### 6.3 Risk-Control-Finding Map (XI-03)

```
EnterpriseRisk (RM)
    |-- related_control_ids --> ProcessControl (PC)
    |                              |-- control_id <-- AuditFinding (AM)
    |-- risk_id <-- AuditFinding (AM)
```

Navigate from any object to all related objects across modules.

### 6.4 Audit Risk Feed (XI-04)

```
AuditableEntity.risk_score = weighted composite:
    40% * max(RM residual scores)
    35% * PC deficiency rate
    25% * AC violation count
```

### 6.5 Unified GRC Dashboard (XI-05)

Single executive view: `GET /grc/dashboard`

Returns:
- Access risk: open violations, severity breakdown
- Control health: total controls, % effective, open deficiencies
- Enterprise risk: top-5 risks, avg residual score, appetite breaches
- Audit status: engagements in progress, open findings, overdue actions

### 6.6 Framework Mapping (XI-07)

Shared framework definitions (COSO/COBIT/ISO 27001/SOX) used by both PC and AM.

---

## 7. Non-Functional Capabilities (NF)

### NF-01: Multi-Tenant Isolation
- Every DB model has `tenant_id` column with index
- Automatic ORM SELECT filtering via `with_loader_criteria`
- Automatic INSERT stamping with current tenant
- Cross-tenant write prevention (`TenantIsolationError`)
- `tenant_scoping_disabled()` escape hatch for system jobs (logged)

### NF-02: RBAC & Auditor Independence
- Role-based access: admin, security_admin, risk_manager, auditor, compliance_officer, etc.
- Auditor role: read-only on AC/RM/PC, write only on AM objects
- 4 audit-specific permissions: VIEW_AUDIT_MANAGEMENT, MANAGE_AUDIT_PLANS, EXECUTE_AUDIT_WORK, VIEW_AUDIT_READONLY

### NF-03: Full Audit Trail
- `AuditLog` model captures all CRUD operations
- Structured logging with request timing, tenant tagging
- Before/after values for sensitive changes

### NF-04: Internationalization (EN + AR)
- Backend: `core/i18n/translations.py` with 70+ translation keys
- Frontend: `useTranslation()` hook, RTL CSS overrides
- Language toggle (EN/AR) in top navbar
- Arabic font stack (Noto Sans Arabic)
- RTL layout flipping: sidebar, nav, tables, stat cards

### NF-05: Document Retention & Legal Hold
- Per-type retention policies (7yr documents, 10yr attestations)
- Batch archival job respecting legal holds
- Legal hold toggle with reason and audit trail
- Retention report: upcoming expirations, overdue, hold items

### NF-06: Multi-Factor Authentication (MFA)
- TOTP via pyotp (RFC 6238)
- QR code setup flow
- MFA challenge during login (short-lived session token)
- Enable/disable with verification

### NF-07: API-First
- 912 REST endpoints
- OpenAPI/Swagger at /docs
- ReDoc at /redoc

### NF-08: Report Export
- PDF export via WeasyPrint
- PPTX export via python-pptx (risk, audit, control, GRC executive)
- Excel export via openpyxl
- 4 branded PPTX templates with charts and tables

### NF-09: Performance
- Risk analysis: 0.11ms/user (8 rules in-process)
- Precompiled rule index for batch analysis
- React Query caching (5-min stale time)

### NF-10: Deployment
- Docker multi-stage builds
- docker-compose.prod.yml
- Kubernetes manifests
- SQLite (dev) / PostgreSQL (prod)

---

## 8. System Architecture

```
                    +-------------------+
                    |   React Frontend  |
                    |  (Vite + TS + TW) |
                    +--------+----------+
                             |
                    +--------v----------+
                    |   FastAPI Backend  |
                    |   (912 routes)     |
                    +--------+----------+
                             |
            +----------------+----------------+
            |                |                |
   +--------v------+  +-----v------+  +------v-------+
   | Tenant        |  | Auth       |  | Rate         |
   | Middleware     |  | (JWT+MFA)  |  | Limiting     |
   | (JWT-verified) |  |            |  | (slowapi)    |
   +--------+------+  +-----+------+  +------+-------+
            |                |                |
   +--------v----------------v----------------v-------+
   |                    Core Modules                    |
   |                                                    |
   |  AC: ARA, ARM, EAM, UAR, Role Eng                |
   |  RM: Risk Register, Assessment, KRI, Response      |
   |  PC: Controls, Testing, CCM, Deficiency, Sign-Off  |
   |  AM: Universe, Plans, Engagements, Findings, Actions|
   |  XI: Bridge, GRC Dashboard                         |
   |  AI: LLM Narratives, NLP, Risk Intelligence        |
   +--------+------------------------------------------+
            |
   +--------v----------+
   |   SQLAlchemy ORM   |
   |   (81 tables)      |
   |   + Tenant Scoping |
   +--------+----------+
            |
   +--------v----------+
   |  PostgreSQL / SQLite|
   +--------------------+
            |
   +--------v----------------------------------+
   |           Connectors                       |
   |  SAP RFC | Azure AD | Okta | Workday      |
   |  SuccessFactors | ServiceNow | LDAP        |
   +-------------------------------------------+
```

---

## 9. API Reference Summary

| Module | Prefix | Route Count | Key Operations |
|--------|--------|-------------|----------------|
| Auth | `/auth` | 12 | Login, MFA, profile, logout |
| Risk Analysis (AC) | `/risk`, `/ara` | 35 | ARA analysis, violations, simulation |
| Access Requests (AC) | `/access-requests` | 15 | CRUD, approve, reject |
| Firefighter (AC) | `/firefighter` | 20 | Request, approve, sessions, monitor |
| Certification (AC) | `/certification` | 12 | Campaigns, items, decisions |
| Role Engineering (AC) | `/role-engineering` | 10 | Catalog, mining, design |
| Risk Management (RM) | `/risk-management` | 30 | Risks, assessments, KRIs, incidents |
| Process Control (PC) | `/process-control` | 35 | Controls, tests, CCM, deficiencies |
| Audit Management (AM) | `/audit-management` | 40 | Plans, engagements, findings, actions |
| Org Hierarchy (XI) | `/org` | 6 | Org tree CRUD |
| Frameworks (XI) | `/frameworks` | 8 | Framework + requirement CRUD |
| GRC Dashboard (XI) | `/grc` | 2 | Unified dashboard, risk-control matrix |
| Reports | `/reports` | 8 | PPTX/PDF export |
| Retention | `/retention` | 5 | Policies, legal hold, batch |
| i18n | `/i18n` | 3 | Locales, translations |
| Other (Users, Settings, Intelligence, etc.) | Various | 670+ | Full platform |

---

## 10. Data Model Summary

### Core Tables (existing)
| Table | Module | Purpose |
|-------|--------|---------|
| users | Shared | User identities from all systems |
| roles | Shared | Authorization roles |
| user_roles | Shared | User-role assignments |
| user_entitlements | Shared | Expanded auth object values |
| risk_violations | AC | Detected SoD/risk violations |
| mitigation_controls | AC | Compensating controls |
| risk_rules | AC | Risk rule definitions |
| firefighter_requests | AC | FF access requests |
| firefighter_sessions | AC | FF active sessions |
| certification_campaigns | AC | UAR campaigns |
| certification_items | AC | Individual review items |
| access_request_logs | AC | ARM audit trail |
| orchestration_contexts | AC | Workflow state |

### GRC Foundation (new)
| Table | Purpose |
|-------|---------|
| org_units | Hierarchical org structure |
| framework_definitions | COSO/COBIT/ISO/SOX frameworks |
| framework_requirements | Individual principles/objectives |

### Risk Management (new)
| Table | Purpose |
|-------|---------|
| enterprise_risks | Risk register |
| risk_assessments | Periodic assessments |
| risk_appetites | Appetite/tolerance per category |
| key_risk_indicators | KRI definitions |
| kri_measurements | KRI readings history |
| risk_responses | Response plans |
| risk_incidents | Loss events |

### Process Control (new)
| Table | Purpose |
|-------|---------|
| process_controls | Control library |
| control_tests | OE/design tests |
| control_deficiencies | Gaps and remediation |
| control_self_assessments | Owner attestations |
| ccm_rules | Monitoring rule definitions |
| ccm_executions | Monitoring results |
| grc_evidence | Evidence repository |
| signoff_certifications | SOX cascading sign-offs |

### Audit Management (new)
| Table | Purpose |
|-------|---------|
| auditable_entities | Audit universe |
| audit_plans | Annual/multi-year plans |
| audit_engagements | Individual audits |
| audit_work_programs | Procedure templates |
| audit_procedures | Procedure execution |
| audit_workpapers | Electronic workpapers |
| audit_findings | CCCE findings |
| audit_actions | Remediation actions |
| auditor_time_entries | Time tracking |
| auditor_resources | Auditor skills/capacity |

---

*Document generated: September 4, 2026*
*Platform version: 1.0.0*
*Total: 912 API routes | 81 DB tables | 128 SoD rules | 50+ frontend pages*
