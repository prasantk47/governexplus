# GovernexPlus — Process Control (PC) Module Guide

**Control Library, Testing, CCM, Deficiency Management, Evidence, SOX Sign-Off**

> Version: 2026-09 | Platform: GovernexPlus 1.x | Replaces: SAP GRC Process Control 12.0

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Control Library (PC-01 to PC-05)](#2-control-library)
3. [Framework Mapping (PC-03, XI-07)](#3-framework-mapping)
4. [Control Testing (PC-10 to PC-11)](#4-control-testing)
5. [Deficiency Management (PC-13)](#5-deficiency-management)
6. [Self-Assessment (PC-12)](#6-self-assessment)
7. [Continuous Control Monitoring — CCM (PC-20 to PC-25)](#7-continuous-control-monitoring-ccm)
8. [Evidence Management (PC-15, NF-05)](#8-evidence-management)
9. [SOX Sign-Off Certification (PC-14)](#9-sox-sign-off-certification)
10. [PC Reporting (PC-30 to PC-32)](#10-pc-reporting)
11. [Integration with Other Modules](#11-integration-with-other-modules)
12. [Configuration Reference](#12-configuration-reference)

---

## 1. Module Overview

### 1.1 What the PC Module Covers

The Process Control (PC) module is the internal controls management layer of GovernexPlus. It directly replaces SAP GRC Process Control 12.0 and covers the complete lifecycle of internal controls: defining them, testing whether they work, tracking failures, monitoring continuously, managing evidence, and producing the cascading sign-off chain required for SOX Section 302/404 compliance.

While the Access Control (AC) module answers "Who has access that creates risk?", Process Control answers "Are the controls we have in place actually working to manage that risk?"

The PC module operates in two modes:

- **Proactive**: Define and test controls on a schedule. Know whether your controls are effective before the auditors arrive.
- **Reactive**: When the Risk Intelligence Engine detects a SoD violation, the SoD Bridge (XI-02) feeds that violation into PC as a control deficiency, creating a closed-loop between access risk and internal controls.

### 1.2 Sub-Modules

| Sub-Module | Reference | SAP GRC PC Equivalent | Description |
|---|---|---|---|
| Control Library | PC-01 to PC-05 | Control Repository | Central catalog of all internal controls |
| Framework Mapping | PC-03, XI-07 | Regulatory Mapping | Map controls to COSO, COBIT, ISO 27001, SOX |
| Control Testing | PC-10, PC-11 | Control Testing | Design and operating effectiveness tests |
| Self-Assessment | PC-12 | Self-Assessment | Owner attestation campaigns |
| Deficiency Management | PC-13 | Issue Management | Track, remediate, and close control failures |
| CCM | PC-20 to PC-25 | Continuous Monitoring | Automated rule-based monitoring |
| Evidence Management | PC-15, NF-05 | Evidence Repository | Document storage with integrity hashing |
| SOX Sign-Off | PC-14 | Sign-Off | Cascading certification from owner to CFO/CEO |
| Reporting | PC-30 to PC-32 | Reports | Control status, framework coverage, audit packages |

### 1.3 How PC Integrates with Other Modules

```
  AC (Risk Intelligence Engine) ──── SoD violations ────► PC (CCM SoD Bridge)
                                         │ auto-deficiency
                                         ▼
  RM (Risk) ◄── control failure ──── PC (Deficiency)
                 impacts residual risk
                                         │
  AM (Audit) ◄── audit findings ──── PC (Deficiency + Evidence)
                  link to controls
                                         │
  AC (Mitigation) ◄── XL-C ──────── PC (Control Library)
                   unified register
```

### 1.4 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React/TS)                  │
│  Control Library │ Testing │ Deficiencies │ CCM │ Signoff│
└────────────────────────────┬────────────────────────────┘
                             │ REST API (JWT auth)
┌────────────────────────────▼────────────────────────────┐
│          /process-control (FastAPI router)               │
│  Controls │ Tests │ Deficiencies │ CCM │ Evidence │ Signoffs│
└─────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│              Database (PostgreSQL / SQLite)               │
│  process_controls │ control_tests │ control_deficiencies  │
│  ccm_rules │ ccm_executions │ grc_evidence │ signoffs    │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Control Library

*Reference codes: PC-01 (Control Catalog), PC-02 (Control Types), PC-03 (Framework Mapping), PC-04 (Ownership), PC-05 (Versioning)*

The Control Library is the master record of every internal control in your organization. Every other PC sub-module — testing, deficiencies, CCM, evidence, sign-offs — links back to a control record in this library.

### 2.1 Control Structure

The `ProcessControl` model (`db/models/process_control.py`) defines the complete control record:

```
ProcessControl
├── control_id          : str          — Unique within tenant, e.g. "CTRL-AP-001"
├── name                : str          — Short descriptive name
├── objective           : str          — What the control is designed to achieve
├── description         : str          — Detailed description of how the control operates
├── control_type        : ControlType  — preventive | detective | corrective
├── control_nature      : ControlNature — manual | automated | it_dependent
├── frequency           : ControlFrequency — continuous | daily | weekly | monthly | quarterly | annual | adhoc
├── process_name        : str          — Parent business process, e.g. "Accounts Payable"
├── subprocess_name     : str          — Sub-process, e.g. "Invoice Approval"
├── org_unit_id         : FK           — Organizational unit owner
├── owner_id            : str          — Control owner user ID
├── owner_name          : str          — Control owner display name
├── owner_email         : str          — Control owner email
├── key_control         : bool         — True = SOX material / key control
├── framework_mappings  : JSON         — [{framework_id, requirement_id}]
├── risk_ids            : JSON         — Linked enterprise risk IDs
├── regulation_ids      : JSON         — Linked regulation IDs
├── version             : int          — Auto-incremented on each update
├── effective_date      : datetime     — When the control became effective
├── review_date         : datetime     — Date of last review
├── next_review_date    : datetime     — Scheduled next review
├── status              : ControlStatus — draft | active | under_review | retired
├── is_active           : bool         — Soft delete flag
└── change_history      : JSON         — [{version, changed_by, changed_at, summary}]
```

### 2.2 Control Types

| Type | Enum Value | Description | When to Use |
|---|---|---|---|
| Preventive | `preventive` | Prevents errors or fraud from occurring | Approval workflows, access controls, segregation of duties |
| Detective | `detective` | Detects errors or fraud after they occur | Reconciliations, exception reports, audit logs |
| Corrective | `corrective` | Corrects identified errors | Remediation procedures, escalation processes |

**Choosing the right type:**

A dual-approval requirement on vendor payments is `preventive` — it stops an unauthorized payment from being processed. A monthly reconciliation of vendor payments to purchase orders is `detective` — it finds discrepancies after the fact. A procedure for reversing duplicate payments is `corrective`.

Strong internal control environments layer all three types. SOX auditors will ask about the mix — an environment with only detective controls is considered weaker because errors must occur before they are caught.

### 2.3 Control Nature

| Nature | Enum Value | Description |
|---|---|---|
| Manual | `manual` | Performed entirely by a human (e.g., manager reviews report and signs off) |
| Automated | `automated` | Performed entirely by a system (e.g., system blocks duplicate invoices) |
| IT-Dependent | `it_dependent` | Human action that relies on system-generated data (e.g., human reviews system-generated exception list) |

IT-dependent controls are the most common in SAP environments. They require testing of both the IT general controls (that the system is generating reliable data) and the manual review process.

### 2.4 Control Frequency

| Frequency | Enum Value | Typical Use |
|---|---|---|
| Continuous | `continuous` | Real-time system controls (e.g., duplicate invoice block) |
| Daily | `daily` | Daily exception report review |
| Weekly | `weekly` | Weekly bank reconciliation |
| Monthly | `monthly` | Monthly AP ledger review, payroll reconciliation |
| Quarterly | `quarterly` | Quarterly access reviews, variance analysis |
| Annual | `annual` | Annual policy review, SOX sign-off |
| Ad-hoc | `adhoc` | Event-driven controls |

### 2.5 Process/Subprocess Classification

Controls are organized into a two-level process hierarchy:

```
Process: "Accounts Payable"
  └── Subprocess: "Invoice Processing"
        ├── CTRL-AP-001: Dual approval for invoices > $10,000
        └── CTRL-AP-002: Three-way match verification

  └── Subprocess: "Payment Execution"
        ├── CTRL-AP-003: Payment run authorization
        └── CTRL-AP-004: Payment file integrity check
```

This hierarchy appears in the control dashboard, framework coverage maps, and audit packages. Processes map to SAP's transaction hierarchy for traceability.

### 2.6 Key Control Flag (SOX Material Controls)

The `key_control` boolean identifies controls that are in scope for SOX Section 404 testing. Marking a control as `key_control = true` includes it in:

- SOX sign-off roll-up trees
- Key control testing reports
- Audit evidence packages
- Deficiency escalation (any deficiency on a key control is immediately flagged as potentially material)

**Setting a control as a key control:**

Include `"key_control": true` in the create or update request body. Changes to the key control flag are logged in `change_history` with the actor's identity.

### 2.7 Control Ownership

Each control has exactly one owner (`owner_id`, `owner_name`, `owner_email`). The owner is responsible for:

1. Attesting that the control is designed adequately (in Self-Assessment campaigns)
2. Confirming the control is operating effectively (in Self-Assessment campaigns)
3. Providing evidence during testing
4. Remediating deficiencies assigned to their controls
5. Signing off on the control's effectiveness in the SOX cascade

The owner is automatically assigned as the assessor in Control Self-Assessment campaigns.

### 2.8 Version Management and Change History

Every update to a control record increments the `version` counter and appends an entry to `change_history`. This provides a complete audit trail of who changed what and when.

```json
{
  "control_id": "CTRL-AP-001",
  "version": 4,
  "change_history": [
    {
      "version": 1,
      "changed_by": "compliance.admin@company.com",
      "changed_at": "2026-01-15T09:00:00Z",
      "summary": "Initial creation"
    },
    {
      "version": 2,
      "changed_by": "process.owner@company.com",
      "changed_at": "2026-04-01T11:30:00Z",
      "summary": "Updated threshold from $5,000 to $10,000 per policy revision"
    },
    {
      "version": 3,
      "changed_by": "compliance.admin@company.com",
      "changed_at": "2026-07-01T08:00:00Z",
      "summary": "Marked as key control for SOX scope"
    }
  ]
}
```

Changes to the following fields trigger a version bump: name, objective, description, control_type, control_nature, frequency, framework_mappings, key_control.

### 2.9 Status Lifecycle

```
DRAFT
  │  (review complete, approved for use)
  ▼
ACTIVE ──────────────────────────────────────────────────► RETIRED
  │                                                         ▲
  │  (scheduled review opened)                             │
  ▼                                                         │
UNDER_REVIEW ──► ACTIVE (review passed, no changes)       │
              └──► RETIRED (control no longer needed) ────┘
```

| Status | Description |
|---|---|
| `draft` | Newly created, not yet approved for testing |
| `active` | In use, eligible for testing, CCM, and sign-off |
| `under_review` | Periodic review in progress |
| `retired` | No longer active; historical records preserved |

Only `active` controls are included in Self-Assessment campaigns, CCM monitoring, and SOX sign-off scopes.

### 2.10 Creating a Control: Step-by-Step

**Example: AP Invoice Dual Approval Control**

**Step 1: Create the control record**

```http
POST /process-control/controls
Content-Type: application/json
Authorization: Bearer <token>

{
  "control_id": "CTRL-AP-001",
  "name": "AP Invoice Dual Approval",
  "objective": "Ensure no single individual can both enter and approve vendor invoices above $10,000",
  "description": "All vendor invoices exceeding $10,000 require dual approval: the AP clerk enters the invoice in MIRO, and a separate AP Manager approves it before posting. The system enforces this via a workflow approval step configured in SAP. The AP Manager reviews the vendor details, invoice amount, and purchase order match before approving.",
  "control_type": "preventive",
  "control_nature": "it_dependent",
  "frequency": "continuous",
  "process_name": "Accounts Payable",
  "subprocess_name": "Invoice Processing",
  "owner_id": "ap.manager@company.com",
  "owner_name": "AP Manager",
  "owner_email": "ap.manager@company.com",
  "key_control": true,
  "effective_date": "2026-01-01T00:00:00Z",
  "framework_mappings": [
    {"framework_id": "COSO2013", "requirement_id": "CC8.1"},
    {"framework_id": "SOX404", "requirement_id": "AP-CTRL-1"}
  ],
  "risk_ids": ["RISK-AP-FRAUD-001", "RISK-AP-ERROR-002"]
}
```

**Step 2: Activate the control**

```http
PUT /process-control/controls/CTRL-AP-001
{
  "status": "active",
  "changed_by": "compliance.director@company.com",
  "change_summary": "Reviewed and approved for SOX scope"
}
```

**Step 3: Verify the control is visible in the library**

```http
GET /process-control/controls?status=active&process_name=Accounts+Payable

{
  "total": 4,
  "controls": [
    {
      "control_id": "CTRL-AP-001",
      "name": "AP Invoice Dual Approval",
      "status": "active",
      "key_control": true,
      "version": 2,
      ...
    }
  ]
}
```

### 2.11 Control Library API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/process-control/controls` | Create control |
| GET | `/process-control/controls` | List controls (filter by type, status, process, owner) |
| GET | `/process-control/controls/{id}` | Get control detail |
| PUT | `/process-control/controls/{id}` | Update control (auto-versions) |
| PUT | `/process-control/controls/{id}/retire` | Retire control |
| GET | `/process-control/controls/{id}/audit-package` | Full audit package |

---

## 3. Framework Mapping

*Reference codes: PC-03 (Framework Mapping), XI-07 (Cross-Module Framework Coverage)*

Framework mapping connects each internal control to the specific requirements it satisfies within regulatory and standards frameworks. This is the foundation of compliance reporting: given a requirement, which controls address it? And given a control, which requirements does it satisfy?

### 3.1 Supported Frameworks

GovernexPlus supports any named framework — there is no hard-coded framework list. The following frameworks are pre-configured in the default data set:

| Framework ID | Full Name | Applicable To |
|---|---|---|
| `COSO2013` | COSO Internal Control — Integrated Framework (2013) | All industries |
| `COBIT2019` | COBIT 2019 | IT governance |
| `ISO27001` | ISO/IEC 27001:2022 Information Security | All industries |
| `SOX302` | Sarbanes-Oxley Section 302 (Disclosure Controls) | Public companies (US) |
| `SOX404` | Sarbanes-Oxley Section 404 (Material Weakness) | Public companies (US) |
| `NIST_CSF` | NIST Cybersecurity Framework 2.0 | US Federal, Critical Infrastructure |
| `GDPR` | General Data Protection Regulation | EU data processors |
| `CUSTOM` | Organization-specific framework | Any |

Custom frameworks can be added without code changes by simply using a new `framework_id` value in framework mappings.

### 3.2 Framework Structure

Each framework is a hierarchy of requirements. For COSO 2013, the structure is:

```
COSO2013
├── Component: Control Environment (CC1)
│   ├── Principle 1: Demonstrates Commitment to Integrity (CC1.1)
│   ├── Principle 2: Exercises Oversight Responsibility (CC1.2)
│   └── ...
├── Component: Risk Assessment (CC4)
│   ├── Principle 6: Specifies Suitable Objectives (CC4.1)
│   └── ...
├── Component: Control Activities (CC8)
│   ├── Principle 10: Selects and Develops Control Activities (CC8.1)
│   │   ├── Point of Focus: Addresses Segregation of Duties (CC8.1.a)
│   │   └── ...
│   └── ...
└── ...
```

### 3.3 Mapping Controls to Framework Requirements

Framework mappings are stored as a JSON array on the control record. Each mapping entry contains the `framework_id` and the `requirement_id` within that framework.

**Adding a framework mapping:**

```http
POST /process-control/controls/CTRL-AP-001/framework-mappings

{
  "framework_id": "COSO2013",
  "requirement_id": "CC8.1"
}
```

**Adding multiple mappings on control creation:**

Include `framework_mappings` in the create request body:

```json
"framework_mappings": [
  {"framework_id": "COSO2013", "requirement_id": "CC8.1"},
  {"framework_id": "SOX404", "requirement_id": "AP-CTRL-1"},
  {"framework_id": "ISO27001", "requirement_id": "A.9.4.2"}
]
```

**Removing a mapping:**

```http
DELETE /process-control/controls/CTRL-AP-001/framework-mappings?framework_id=ISO27001&requirement_id=A.9.4.2
```

### 3.4 Coverage Analysis

Framework coverage analysis answers: "For this framework, which requirements are covered by active controls, and which have gaps?"

```http
GET /process-control/frameworks/COSO2013/coverage

{
  "framework_id": "COSO2013",
  "control_count": 12,
  "controls": [
    {
      "control_id": "CTRL-AP-001",
      "name": "AP Invoice Dual Approval",
      "status": "active",
      "key_control": true,
      "framework_mappings": [
        {"framework_id": "COSO2013", "requirement_id": "CC8.1", "added_at": "2026-01-15T09:00:00Z"}
      ]
    },
    ...
  ]
}
```

**Gap analysis:** Requirements that are not mapped to any active control appear in the gap report. This is particularly important for SOX 404 scoping — every material business process must have at least one key control mapped to the relevant SOX requirement.

### 3.5 Multi-Framework Mapping

One control can satisfy multiple framework requirements simultaneously. This is the recommended approach because it avoids maintaining separate control libraries for each compliance framework.

**Example: CTRL-AP-001 satisfies all of these simultaneously:**

| Framework | Requirement | Description |
|---|---|---|
| COSO 2013 | CC8.1 | Control Activities — Segregation of Duties |
| SOX 404 | AP-CTRL-1 | Material Control over AP Processing |
| ISO 27001 | A.9.4.2 | Secure log-on procedures |
| COBIT 2019 | DSS06.03 | Manage roles, responsibilities, access privileges |

### 3.6 Framework API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/process-control/controls/{id}/framework-mappings` | Add framework mapping |
| DELETE | `/process-control/controls/{id}/framework-mappings` | Remove framework mapping |
| GET | `/process-control/controls/{id}/frameworks` | Get control's framework mappings |
| GET | `/process-control/frameworks/{framework_id}/coverage` | Framework coverage analysis |

---

## 4. Control Testing

*Reference codes: PC-10 (Test Planning), PC-11 (Operating Effectiveness)*

Control testing provides the evidence that a control is not only well-designed but is actually operating as intended. GovernexPlus implements both design assessment and operating effectiveness testing, mirroring the methodology used by Big 4 auditors for SOX 404 engagements.

### 4.1 Test Types

| Type | Enum Value | Description |
|---|---|---|
| Design Assessment | `design` | Evaluates whether the control, if followed as designed, would prevent or detect the identified risk |
| Operating Effectiveness | `operating_effectiveness` | Evaluates whether the control actually operated as designed during the test period |
| Walkthrough | `walkthrough` | End-to-end trace of a transaction through all controls to confirm understanding |

**Testing approach by control nature:**

| Control Nature | Recommended Test Approach |
|---|---|
| Manual | Interview + re-performance. Review a sample of manually performed control instances |
| Automated | Inspect system configuration. Test one instance (automated controls are "all or nothing") |
| IT-Dependent | Test IT general controls first, then test the manual portion using system-generated data |

### 4.2 Creating a Test Plan

A test plan defines the parameters for a control test before execution begins.

```http
POST /process-control/controls/CTRL-AP-001/tests

{
  "test_type": "operating_effectiveness",
  "testing_period_start": "2026-07-01T00:00:00Z",
  "testing_period_end": "2026-09-30T23:59:59Z",
  "sample_size": 25,
  "population_size": 847,
  "tester_id": "internal.audit@company.com",
  "tester_name": "Internal Audit Team",
  "test_steps": [
    {
      "ref": "1",
      "step": "Obtain population",
      "description": "Pull all vendor invoices > $10,000 for the test period from MIRO using transaction code MIR4. Document count and date range."
    },
    {
      "ref": "2",
      "step": "Select sample",
      "description": "Using random number generator, select 25 invoices from the population of 847."
    },
    {
      "ref": "3",
      "step": "Inspect approval workflow",
      "description": "For each sampled invoice, verify in the SAP workflow log that: (a) the invoice was entered by one user, (b) the approval was performed by a different user, (c) the approver has the AP Manager role (Z_AP_MANAGER), (d) the approval occurred before the payment run."
    },
    {
      "ref": "4",
      "step": "Test SoD check",
      "description": "Confirm that the entering user does not also have the Z_AP_MANAGER role. Cross-reference against Risk Intelligence Engine analysis for the test period."
    },
    {
      "ref": "5",
      "step": "Document exceptions",
      "description": "Record any instances where the dual approval was not present or was performed by the same individual."
    }
  ]
}
```

**Response:**

```json
{
  "test_id": "TEST_a4b7c9d1e2f3",
  "control_id": 42,
  "test_type": "operating_effectiveness",
  "testing_period_start": "2026-07-01T00:00:00Z",
  "testing_period_end": "2026-09-30T23:59:59Z",
  "sample_size": 25,
  "population_size": 847,
  "tester_id": "internal.audit@company.com",
  "status": "planned",
  "result": null
}
```

### 4.3 Test Steps Definition

Test steps are stored as a JSON array of structured objects. Each step contains:

| Field | Description |
|---|---|
| `ref` | Step reference number (1, 2, 3...) |
| `step` | Short step title |
| `description` | Full procedure for performing this step |

Steps are displayed to the tester during execution and included in the audit package.

### 4.4 Recording Results

Once testing is complete, the tester records the outcome:

```http
PUT /process-control/tests/TEST_a4b7c9d1e2f3/result

{
  "result": "effective",
  "exceptions_found": 0,
  "exception_details": [],
  "conclusion": "For all 25 sampled invoices, dual approval was present and was performed by two different individuals. The entering user did not have AP Manager role in any case. Control is operating as designed.",
  "evidence_ids": ["EVID_001", "EVID_002", "EVID_003"],
  "create_deficiency": false,
  "reviewed_by": "audit.manager@company.com"
}
```

**Result values:**

| Result | Enum Value | Meaning |
|---|---|---|
| Effective | `effective` | Control operated as designed with no exceptions |
| Ineffective | `ineffective` | Control failed — exceptions found, or control not performed |
| Partially Effective | `partially_effective` | Control operated but with exceptions below the tolerable threshold |
| Not Tested | `not_tested` | Default — test planned but not yet executed |

### 4.5 Exception Documentation

When exceptions are found, each exception must be documented individually:

```json
"exception_details": [
  {
    "exception_ref": "E-001",
    "invoice_number": "INV-2026-004512",
    "amount": 45000,
    "description": "Invoice approved by JSMITH who is also the AP Clerk. JSMITH should not have approval rights.",
    "root_cause": "JSMITH was temporarily given Z_AP_MANAGER during vacation coverage of regular manager",
    "compensating_action": "Invoice reviewed and confirmed legitimate by CFO"
  }
]
```

### 4.6 Auto-Deficiency on Ineffective Result

When a test result is `ineffective` or `partially_effective`, the system automatically creates a deficiency record unless `create_deficiency: false` is specified.

**Auto-deficiency creation logic (from source):**

```python
if t.result in (TestResult.INEFFECTIVE, TestResult.PARTIALLY_EFFECTIVE) and body.get("create_deficiency", True):
    sev = DeficiencySeverity.OBSERVATION if t.result == TestResult.PARTIALLY_EFFECTIVE \
          else DeficiencySeverity.CONTROL_GAP
    deficiency = ControlDeficiency(
        source="test",
        title=f"Deficiency from test {test_id}",
        description=t.conclusion,
        severity=sev,
        status=DeficiencyStatus.OPEN,
    )
```

| Test Result | Auto-Deficiency Severity |
|---|---|
| `ineffective` | `control_gap` |
| `partially_effective` | `observation` |

The severity can be manually elevated to `significant_deficiency` or `material_weakness` by the test reviewer.

### 4.7 Evidence Attachment

Evidence items are linked to test records via `evidence_ids`. These are IDs from the Evidence Repository (see Section 8). The audit package for a control includes the test record and all linked evidence.

### 4.8 Test History per Control

```http
GET /process-control/controls/CTRL-AP-001/tests

{
  "total": 4,
  "tests": [
    {"test_id": "TEST_a4b7c9d1e2f3", "test_type": "operating_effectiveness", "result": "effective", "testing_period_start": "2026-07-01", "testing_period_end": "2026-09-30"},
    {"test_id": "TEST_b5c8d2f4a9e1", "test_type": "operating_effectiveness", "result": "effective", "testing_period_start": "2026-04-01", "testing_period_end": "2026-06-30"},
    {"test_id": "TEST_c6d9e3a5b0f2", "test_type": "operating_effectiveness", "result": "partially_effective", "exceptions_found": 1, "testing_period_start": "2026-01-01", "testing_period_end": "2026-03-31"},
    {"test_id": "TEST_d7e0f4b6c1a3", "test_type": "design", "result": "effective", "testing_period_start": "2025-12-01", "testing_period_end": "2025-12-31"}
  ]
}
```

### 4.9 Control Testing API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/process-control/controls/{id}/tests` | Create test plan |
| GET | `/process-control/controls/{id}/tests` | Get test history |
| PUT | `/process-control/tests/{test_id}/result` | Record test result (auto-creates deficiency if ineffective) |

---

## 5. Deficiency Management

*Reference code: PC-13*

A control deficiency represents a failure, gap, or weakness in a control. Deficiencies can originate from multiple sources — failed tests, CCM monitoring breaches, SoD violations bridged from the Risk Intelligence Engine, or manually reported issues. GovernexPlus tracks each deficiency through a structured status lifecycle until it is independently verified as closed.

### 5.1 Deficiency Sources

| Source | Enum Value | How Created |
|---|---|---|
| Control Test | `test` | Automatically created when test result is `ineffective` or `partially_effective` |
| CCM Monitoring | `ccm` | Automatically created when a CCM rule fails (if `auto_create_deficiency=true`) |
| Self-Assessment | `self_assessment` | Created when owner marks control as `operating_effectively=false` |
| SoD Bridge | `sod_bridge` | Created when Risk Intelligence Engine SoD violations exceed threshold via XI-02 bridge |
| Manual | `manual` | Created directly by compliance team or auditors |

### 5.2 Severity Classification

| Severity | Enum Value | Description | SOX Implication |
|---|---|---|---|
| Material Weakness | `material_weakness` | A significant deficiency, or combination of deficiencies, resulting in more than a remote likelihood that a material misstatement of financial statements would not be prevented or detected | Must be publicly disclosed in 10-K / annual report |
| Significant Deficiency | `significant_deficiency` | A deficiency, or combination of deficiencies, that is less severe than material weakness yet important enough to merit attention by those responsible for oversight | Must be reported to audit committee |
| Control Gap | `control_gap` | Control is present but has notable weaknesses that need remediation | Internal reporting and tracking |
| Observation | `observation` | Minor issue; control is substantially effective | Note for improvement; no mandatory disclosure |

**Severity escalation:** Deficiencies on `key_control = true` controls are automatically escalated one level. An `observation` on a key control becomes a `control_gap`. A `control_gap` becomes a `significant_deficiency`. This escalation is applied at reporting time.

### 5.3 Status Machine

```
OPEN
  │
  ├── [owner assigned, remediation begun]
  │
  ▼
IN_REMEDIATION
  │
  ├── [remediation action completed]
  │
  ▼
REMEDIATED
  │
  ├── [independent verifier reviews evidence]
  │
  ├──► VERIFIED_CLOSED (confirmed remediated)
  │
  └──► OPEN (verification failed, deficiency reopened)

[At any stage] ──► ACCEPTED (formal risk acceptance, time-bounded)
```

**Status transitions:**

| From | To | Who | Endpoint |
|---|---|---|---|
| OPEN | IN_REMEDIATION | Compliance Admin | `PUT /deficiencies/{id}` (update status) |
| IN_REMEDIATION | REMEDIATED | Remediation Owner | `PUT /deficiencies/{id}/remediate` |
| REMEDIATED | VERIFIED_CLOSED | Independent Verifier | `PUT /deficiencies/{id}/verify` |
| REMEDIATED | OPEN | Verifier (if failed) | `PUT /deficiencies/{id}` (reopen) |
| Any | ACCEPTED | CISO + sign-off | Formal acceptance with expiry |

### 5.4 Root Cause Analysis

Every deficiency should include a documented root cause. The root cause drives the remediation action — without understanding why the control failed, remediation may address the symptom without fixing the underlying issue.

**Deficiency creation with root cause:**

```http
POST /process-control/deficiencies

{
  "control_id": "CTRL-AP-001",
  "source": "manual",
  "title": "AP Clerk has approval rights during manager vacation",
  "description": "JSMITH (AP Clerk) was temporarily assigned Z_AP_MANAGER role during manager's vacation, creating a dual-approval control failure for 3 weeks.",
  "severity": "significant_deficiency",
  "root_cause": "No formal process exists for temporary role assignment during staff absences. The IT team granted the elevated role without notifying the compliance team or checking Risk Intelligence Engine violations.",
  "remediation_plan": "1. Immediately remove Z_AP_MANAGER from JSMITH. 2. Establish formal vacation coverage policy requiring compliance pre-approval for temporary elevated roles. 3. Configure Risk Intelligence Engine alert to notify compliance automatically when this SoD conflict (SOD-FI-003) is created.",
  "remediation_owner_id": "hr.director@company.com",
  "remediation_owner_name": "HR Director",
  "due_date": "2026-10-31T23:59:59Z"
}
```

### 5.5 Remediation Plan

The remediation plan documents the specific steps that will be taken to fix the control failure. It should include:

1. **Immediate action**: Stop the bleeding (e.g., remove conflicting access)
2. **Root cause fix**: Address the process or control that allowed the deficiency (e.g., create approval policy)
3. **Verification method**: How the verifier will confirm the fix (e.g., Risk Intelligence Engine re-analysis shows no violation)
4. **Due date**: Realistic deadline with owner accountability

**Recording remediation completion:**

```http
PUT /process-control/deficiencies/DEF_x9y8z7/remediate

{
  "remediation_notes": "1. Z_AP_MANAGER removed from JSMITH on 2026-09-07. Risk Intelligence Engine confirms no current SOD-FI-003 violation. 2. Vacation coverage policy published and signed by CHRO on 2026-09-20. 3. Risk Intelligence Engine alert configured in notification engine for SOD-FI-003."
}
```

### 5.6 Verification and Closure

Verification must be performed by an individual independent of the remediation owner. This segregation ensures objectivity.

```http
PUT /process-control/deficiencies/DEF_x9y8z7/verify

{
  "verified_by": "internal.audit@company.com",
  "verification_notes": "Confirmed JSMITH no longer has Z_AP_MANAGER role via SU01 extract dated 2026-10-01. Reviewed new vacation coverage policy document. Confirmed Risk Intelligence Engine alert is active via notification configuration review.",
  "evidence_ids": ["EVID_011", "EVID_012", "EVID_013"]
}
```

### 5.7 Aging and Escalation

Deficiencies that are not remediated within their due dates are automatically escalated:

| Condition | Escalation Action |
|---|---|
| Due date passed, status = OPEN | Email notification to owner + compliance team |
| 7 days past due, key control | Escalate to CISO |
| 30 days past due, material_weakness | Escalate to CFO |
| 60 days past due, any severity | Add to board audit committee report |

### 5.8 Deficiency API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/process-control/deficiencies` | Create deficiency |
| GET | `/process-control/deficiencies` | List deficiencies (filter by status, severity, control) |
| GET | `/process-control/deficiencies/{id}` | Get deficiency detail |
| PUT | `/process-control/deficiencies/{id}` | Update deficiency |
| PUT | `/process-control/deficiencies/{id}/remediate` | Mark as remediated |
| PUT | `/process-control/deficiencies/{id}/verify` | Verify and close |

---

## 6. Self-Assessment

*Reference code: PC-12*

Control Self-Assessment (CSA) is the process by which control owners attest to the design adequacy and operating effectiveness of their controls without waiting for formal testing. CSA campaigns are typically run quarterly and serve as an early-warning mechanism between formal audit testing cycles.

### 6.1 Campaign Creation

A CSA campaign creates assessment tasks for all active controls within a specified scope, assigning each to the control's owner as the assessor.

```http
POST /process-control/self-assessment-campaigns

{
  "campaign_name": "Q3 2026 Control Self-Assessment",
  "campaign_type": "quarterly",
  "due_date": "2026-09-30T23:59:59Z",
  "control_ids": ["CTRL-AP-001", "CTRL-AP-002", "CTRL-AP-003"]
}
```

If `control_ids` is omitted, the campaign includes all `active` controls for the tenant.

**Response:**

```json
{
  "campaign_name": "Q3 2026 Control Self-Assessment",
  "assessments_created": 47,
  "assessment_ids": ["CSA_abc123", "CSA_def456", ...]
}
```

### 6.2 Assessment Questionnaires

Each assessment presents the control owner with a structured questionnaire. The responses are stored in `questionnaire_responses` (JSON). Standard questions include:

- Is the control still in use?
- Has the control design changed since the last review?
- Are you aware of any instances where the control failed to operate?
- Is the control documentation current and accurate?
- Are all staff responsible for performing this control trained?

Custom questions can be defined per campaign type by including them in the `questionnaire_responses` schema.

### 6.3 Owner Attestation

The heart of the self-assessment is the dual attestation: the owner confirms both that the control is **designed adequately** and that it is **operating effectively**.

```http
PUT /process-control/self-assessments/CSA_abc123/submit

{
  "design_adequate": true,
  "operating_effectively": true,
  "questionnaire_responses": {
    "control_still_in_use": true,
    "design_changed": false,
    "known_failures": false,
    "documentation_current": true,
    "staff_trained": true
  },
  "attestation": "I, ap.manager@company.com, confirm that the AP Invoice Dual Approval control (CTRL-AP-001) is designed adequately and operated effectively during Q3 2026. No exceptions were noted during the quarter.",
  "comments": "Control performance is strong. Only 2 invoices required escalation for late approval, both within tolerance."
}
```

**When `operating_effectively = false`:** A deficiency is automatically created with source `self_assessment`, assigned to the owner, and included in the compliance team's review queue.

### 6.4 Pending Assessments and Overdue Tracking

```http
GET /process-control/self-assessments/pending?assessor_id=ap.manager@company.com

{
  "total": 3,
  "assessments": [
    {
      "assessment_id": "CSA_abc123",
      "campaign_name": "Q3 2026 Control Self-Assessment",
      "control_id": "CTRL-AP-001",
      "control_name": "AP Invoice Dual Approval",
      "assessor_id": "ap.manager@company.com",
      "due_date": "2026-09-30",
      "status": "pending",
      "days_until_due": 24
    }
  ]
}
```

The `status` field transitions to `overdue` automatically when the due date passes without a submission.

### 6.5 Self-Assessment API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/process-control/self-assessment-campaigns` | Create CSA campaign |
| GET | `/process-control/self-assessments/pending` | Get pending assessments |
| PUT | `/process-control/self-assessments/{id}/submit` | Submit attestation |

---

## 7. Continuous Control Monitoring — CCM

*Reference codes: PC-20 (CCM Framework), PC-21 (Rule Configuration), PC-22 (Rule Execution), PC-23 (Breach Management), PC-24 (SoD Bridge), PC-25 (Non-SAP Sources)*

Continuous Control Monitoring (CCM) moves internal controls from periodic testing to always-on automated surveillance. Rather than testing 25 transactions in a quarterly sample, CCM evaluates all transactions continuously and alerts immediately when a control breach is detected.

### 7.1 Rule Types

GovernexPlus CCM supports four types of monitoring rules:

| Type | Enum Value | Description |
|---|---|---|
| Configuration Check | `config_check` | Monitors a system configuration setting that must stay within defined bounds |
| Data Pattern | `data_pattern` | Monitors transactional data for suspicious patterns |
| Threshold | `threshold` | Monitors a metric against a numeric threshold |
| SoD Bridge | `sod_bridge` | Feeds Risk Intelligence Engine SoD violations into CCM as a monitoring signal |

### 7.2 Creating CCM Rules

**Example 1: Configuration Check**

Monitor that the SAP payment tolerance configuration has not been changed above the allowed threshold.

```http
POST /process-control/ccm-rules

{
  "rule_id": "CCM-CONFIG-001",
  "name": "AP Payment Tolerance Config Monitor",
  "description": "Alerts if the AP payment tolerance for company code 1000 is set above $5,000",
  "control_id": "CTRL-AP-003",
  "source_system": "SAP_PROD",
  "rule_type": "config_check",
  "rule_definition": {
    "table": "T043T",
    "field": "NETWR",
    "company_code": "1000",
    "expected_max": 5000
  },
  "threshold_operator": "<=",
  "threshold_value": 5000,
  "frequency": "daily",
  "auto_create_deficiency": true,
  "severity_on_breach": "significant_deficiency"
}
```

**Example 2: Data Pattern**

Monitor for vendor invoices that bypass the three-way match.

```http
POST /process-control/ccm-rules

{
  "rule_id": "CCM-PATTERN-001",
  "name": "Invoice Three-Way Match Bypass",
  "description": "Detects invoices posted to vendors that have no corresponding goods receipt",
  "control_id": "CTRL-AP-002",
  "source_system": "SAP_PROD",
  "rule_type": "data_pattern",
  "rule_definition": {
    "source_table": "RBKP",
    "join_table": "MKPF",
    "join_condition": "MBLNR IS NULL",
    "amount_threshold": 1000,
    "exclude_doctype": ["RE-V", "XR"]
  },
  "frequency": "daily",
  "auto_create_deficiency": true,
  "severity_on_breach": "control_gap"
}
```

**Example 3: Threshold**

Monitor that the number of manual journal entries posted without approval in a day does not exceed the policy threshold.

```http
POST /process-control/ccm-rules

{
  "rule_id": "CCM-THRESHOLD-001",
  "name": "Unapproved Journal Entries Daily Count",
  "description": "Alerts if more than 10 manual journal entries are posted without workflow approval in a single day",
  "control_id": "CTRL-GL-001",
  "source_system": "SAP_PROD",
  "rule_type": "threshold",
  "rule_definition": {
    "source_table": "BKPF",
    "count_field": "BELNR",
    "filter": "TCODE = 'FB50' AND APPR_STAT = 'NONE'",
    "group_by": "BUDAT"
  },
  "threshold_operator": "<=",
  "threshold_value": 10,
  "frequency": "daily",
  "auto_create_deficiency": true,
  "severity_on_breach": "observation"
}
```

**Example 4: SoD Bridge**

See Section 7.5 for the dedicated SoD Bridge rule configuration.

### 7.3 Rule Execution

**Manual execution (ad-hoc):**

```http
POST /process-control/ccm-rules/CCM-CONFIG-001/execute

{
  "result": "pass",
  "findings_count": 0,
  "findings_detail": {"checked_value": 4500, "threshold": 5000, "result": "within_bounds"},
  "duration_ms": 245
}
```

**Batch execution (run all active rules):**

```http
POST /process-control/ccm/run-all
{}
```

This triggers a dry-run execution for all active rules, recording a pass for each. In production, the execution engine (`core/scheduler/automation_jobs.py`) runs all CCM rules on their configured schedule and calls this endpoint with actual results from the SAP connector.

### 7.4 Auto-Deficiency on Breach

When a CCM rule executes with `result: "fail"` and `auto_create_deficiency = true`, a deficiency is created automatically:

```python
# From process_ctrl.py
if result == CCMResult.FAIL and rule.auto_create_deficiency:
    deficiency = ControlDeficiency(
        source="ccm",
        title=f"CCM breach: {rule.name}",
        description=f"Rule {rule_id} failed with {findings_count} findings",
        severity=DeficiencySeverity(rule.severity_on_breach),
        status=DeficiencyStatus.OPEN,
    )
```

The deficiency is linked to the CCM execution record (`exec_record.deficiency_id`) for full traceability.

### 7.5 SoD Bridge (XI-02)

The SoD Bridge is the most powerful CCM integration. It creates a live connection between the Risk Intelligence Engine module's access risk detection and Process Control monitoring.

**How the bridge works:**

1. The Risk Intelligence Engine detects SoD violations during a user analysis or scheduled scan
2. The Risk Intelligence Engine calls the SoD Bridge endpoint with the list of violation IDs
3. PC creates a `sod_bridge` CCM rule for the specified control (if one does not exist)
4. A CCM execution record is created: `FAIL` if violations exist, `PASS` if cleared
5. If `FAIL`, an automatic deficiency is created with `source="ccm"` and `severity="significant_deficiency"`
6. The deficiency appears in the PC deficiency dashboard and SOX sign-off scope

```http
POST /process-control/ccm/sod-bridge

{
  "control_id": "CTRL-AP-001",
  "violation_ids": ["ARA-JSMITH-001", "ARA-MBROWN-002", "ARA-RLOPEZ-003"]
}
```

**Response:**

```json
{
  "rule_id": "CCM_f4a9c2b1d8e7",
  "violations_bridged": 3,
  "result": "fail"
}
```

This creates or updates the `SOD_BRIDGE` CCM rule linked to `CTRL-AP-001` and records a FAIL execution with 3 findings. An auto-deficiency is created: "CCM breach: SoD Bridge for control CTRL-AP-001 — 3 violations detected."

**When SoD violations are remediated:**

```http
POST /process-control/ccm/sod-bridge

{
  "control_id": "CTRL-AP-001",
  "violation_ids": []
}
```

This records a PASS execution, indicating the SoD violations have been cleared. If no violations remain, the linked deficiency can be moved to `VERIFIED_CLOSED`.

### 7.6 CCM Dashboard

```http
GET /process-control/ccm/dashboard

{
  "total_rules": 24,
  "passing": 21,
  "failing": 2,
  "never_run": 1,
  "pass_rate": 87.5,
  "rules": [
    {
      "rule_id": "CCM-CONFIG-001",
      "name": "AP Payment Tolerance Config Monitor",
      "rule_type": "config_check",
      "last_run_at": "2026-09-06T02:00:00Z",
      "last_result": "pass",
      "is_active": true
    },
    {
      "rule_id": "CCM-THRESHOLD-001",
      "name": "Unapproved Journal Entries Daily Count",
      "rule_type": "threshold",
      "last_run_at": "2026-09-06T02:00:00Z",
      "last_result": "fail",
      "is_active": true
    }
  ]
}
```

### 7.7 Non-SAP Sources

CCM rules can monitor non-SAP systems by setting `source_system` to the appropriate connector identifier:

| Source System | Description |
|---|---|
| `SAP_PROD` | SAP production system |
| `AZURE_AD` | Azure Active Directory group membership |
| `SERVICENOW` | ServiceNow change tickets |
| `CUSTOM_DB` | Custom database via JDBC connector |

The `rule_definition` JSON adapts to the source system's data model. For Azure AD, a config check might monitor that no user is a member of both the Global Administrators and the Finance Approvers groups.

### 7.8 CCM API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/process-control/ccm-rules` | Create CCM rule |
| GET | `/process-control/ccm-rules` | List CCM rules |
| GET | `/process-control/ccm-rules/{id}` | Get CCM rule |
| POST | `/process-control/ccm-rules/{id}/execute` | Execute rule (record result) |
| POST | `/process-control/ccm/run-all` | Run all active rules |
| GET | `/process-control/ccm/dashboard` | CCM health dashboard |
| POST | `/process-control/ccm/sod-bridge` | Bridge SoD violations into CCM |
| GET | `/process-control/ccm/executions/{rule_id}` | Execution history for a rule |

---

## 8. Evidence Management

*Reference codes: PC-15 (Evidence Repository), NF-05 (Non-Functional: Evidence Integrity)*

The Evidence Repository stores and manages the supporting documentation that proves controls are designed and operating effectively. Every test result, CCM finding, deficiency, and sign-off can be linked to one or more evidence items. Evidence integrity is protected by SHA-256 content hashing.

### 8.1 Evidence Types

| Type | Description | Example |
|---|---|---|
| `document` | Word, PDF, or other document | Policy document, procedure manual |
| `screenshot` | Screen capture of a system configuration or transaction | SAP configuration screenshot |
| `export` | Spreadsheet or data export from a system | Invoice register extract from MIRO |
| `system_extract` | System-generated report output | Risk Intelligence Engine risk analysis report |
| `attestation` | Signed statement of fact | Manager sign-off form |

### 8.2 Upload and Metadata

```http
POST /process-control/evidence

{
  "title": "Q3 2026 AP Invoice Sample — Dual Approval Verification",
  "description": "Excel workbook showing 25 sampled invoices with approval workflow screenshots. Confirms dual approval present for all samples.",
  "evidence_type": "export",
  "file_name": "Q3-2026-AP-Dual-Approval-Sample.xlsx",
  "file_path": "/evidence/2026/Q3/CTRL-AP-001/Q3-2026-AP-Dual-Approval-Sample.xlsx",
  "file_size": 245760,
  "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "content_hash": "sha256:a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3",
  "source_module": "pc",
  "linked_object_type": "control_test",
  "linked_object_id": "TEST_a4b7c9d1e2f3",
  "uploaded_by": "internal.audit@company.com",
  "retention_until": "2033-12-31T23:59:59Z",
  "legal_hold": false
}
```

**Response:**

```json
{
  "evidence_id": "EVID_g1h2i3j4k5l6",
  "title": "Q3 2026 AP Invoice Sample — Dual Approval Verification",
  "status": "active",
  "version": 1,
  "upload_date": "2026-09-06T10:30:00Z",
  "content_hash": "sha256:a4b3c2d1..."
}
```

### 8.3 SHA-256 Integrity Hash

The `content_hash` field stores a SHA-256 hash of the file contents at the time of upload. This hash is computed by the client before upload and stored server-side. It serves two purposes:

1. **Integrity verification**: At any future point, the hash can be recomputed from the stored file and compared against the stored hash to detect tampering.
2. **Audit trail**: The hash is included in audit packages and can be presented to external auditors as proof that the evidence has not been modified since upload.

**Computing the hash (Python):**

```python
import hashlib

with open("Q3-2026-AP-Dual-Approval-Sample.xlsx", "rb") as f:
    content_hash = "sha256:" + hashlib.sha256(f.read()).hexdigest()
```

### 8.4 Version Chain

When an evidence item is updated (e.g., a corrected version of a document replaces the original), the version counter increments and the previous version is preserved. The version chain allows auditors to see all versions of an evidence item.

```http
PUT /process-control/evidence/EVID_g1h2i3j4k5l6

{
  "title": "Q3 2026 AP Invoice Sample — Dual Approval Verification (Rev 2)",
  "file_name": "Q3-2026-AP-Dual-Approval-Sample-v2.xlsx",
  "content_hash": "sha256:b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4",
  "change_reason": "Added 2 additional samples following auditor request"
}
```

### 8.5 Legal Hold

Legal hold prevents evidence from being deleted, modified, or expired during litigation or regulatory investigation.

**Setting a legal hold:**

```http
PUT /process-control/evidence/EVID_g1h2i3j4k5l6/legal-hold

{
  "legal_hold": true,
  "hold_reason": "SEC investigation — document preservation order received 2026-09-01"
}
```

**Effect of legal hold:**
- Evidence cannot be deleted (DELETE requests rejected with 403)
- Retention policy expiry is suspended
- Evidence is excluded from automated retention cleanup
- Legal hold status is prominently displayed in the UI

**Releasing a legal hold:**

```http
PUT /process-control/evidence/EVID_g1h2i3j4k5l6/legal-hold

{
  "legal_hold": false,
  "release_reason": "SEC investigation concluded 2026-11-30. Legal counsel authorization: LC-2026-4521"
}
```

All legal hold set/release operations are immutably logged in the audit trail.

### 8.6 Retention Policies

The `retention_until` date defines when an evidence item can be automatically deleted. For SOX purposes, the typical retention period is 7 years from the period-end date:

| Evidence Type | Recommended Retention |
|---|---|
| SOX control testing evidence | 7 years |
| Internal audit workpapers | 5 years |
| CCM execution logs | 3 years |
| Self-assessment attestations | 5 years |
| Sign-off certifications | 7 years |

The `retention_until` date is set at upload time and cannot be shortened without explicit override (requires GRC admin role). Lengthening is always permitted.

### 8.7 Linking Evidence to Objects

Evidence items link to other GRC objects via `linked_object_type` and `linked_object_id`:

| Object Type | `linked_object_type` Value | Example |
|---|---|---|
| Process Control | `process_control` | Link evidence to the control itself |
| Control Test | `control_test` | Link evidence to a specific test execution |
| Control Deficiency | `control_deficiency` | Link evidence showing a deficiency |
| Sign-Off | `signoff` | Link evidence supporting a SOX sign-off |
| CCM Execution | `ccm_execution` | Link evidence of a CCM monitoring result |

**Retrieving evidence linked to a specific object:**

```http
GET /process-control/evidence?linked_object_type=control_test&linked_object_id=TEST_a4b7c9d1e2f3

{
  "total": 3,
  "evidence": [
    {"evidence_id": "EVID_g1h2i3j4k5l6", "title": "Q3 2026 AP Invoice Sample..."},
    {"evidence_id": "EVID_h2i3j4k5l6m7", "title": "SAP SU01 Role Extract - JSMITH"},
    {"evidence_id": "EVID_i3j4k5l6m7n8", "title": "Risk Intelligence Engine Analysis Report - JSMITH Q3 2026"}
  ]
}
```

### 8.8 Evidence API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/process-control/evidence` | Create evidence record |
| GET | `/process-control/evidence` | List evidence (filter by module, object, legal_hold) |
| GET | `/process-control/evidence/{id}` | Get evidence detail |
| PUT | `/process-control/evidence/{id}` | Update evidence (versions) |
| PUT | `/process-control/evidence/{id}/legal-hold` | Set/release legal hold |
| DELETE | `/process-control/evidence/{id}` | Delete evidence (blocked if legal_hold=true) |

---

## 9. SOX Sign-Off Certification

*Reference code: PC-14*

SOX sign-off is the cascading certification process through which management formally attests to the effectiveness of internal controls over financial reporting. GovernexPlus implements a tree-structured sign-off hierarchy that mirrors real SOX certification: each level of management certifies their scope, and those certifications roll up to the CFO and CEO who sign the 10-K.

### 9.1 Sign-Off Hierarchy

```
CEO/CFO Sign-Off (Annual — covers all business processes)
  │
  ├── Process Owner: Finance (Q4 Certification)
  │     ├── Control Owner: AP Manager (CTRL-AP-001 through CTRL-AP-008)
  │     ├── Control Owner: AR Manager (CTRL-AR-001 through CTRL-AR-006)
  │     └── Control Owner: GL Manager (CTRL-GL-001 through CTRL-GL-005)
  │
  ├── Process Owner: Procurement (Q4 Certification)
  │     ├── Control Owner: Purchasing Manager (CTRL-MM-001 through CTRL-MM-007)
  │     └── Control Owner: Warehouse Manager (CTRL-WM-001 through CTRL-WM-004)
  │
  └── Process Owner: HR/Payroll (Q4 Certification)
        ├── Control Owner: HR Manager (CTRL-HR-001 through CTRL-HR-005)
        └── Control Owner: Payroll Manager (CTRL-PAY-001 through CTRL-PAY-004)
```

The hierarchy is implemented as a parent-child relationship on `SignOffCertification` records via `parent_certification_id`.

### 9.2 Creating Sign-Off Records

Sign-off records are created at each level of the hierarchy. The process typically starts at the control owner level and rolls up.

**Level 1: Control Owner Sign-Off**

```http
POST /process-control/signoffs

{
  "period": "Q4-2026",
  "org_unit_id": 12,
  "certifier_id": "ap.manager@company.com",
  "certifier_name": "AP Manager",
  "certifier_role": "Control Owner",
  "scope_summary": "Accounts Payable controls — AP Invoice Processing and Payment Execution subprocesses",
  "controls_in_scope": 8,
  "controls_effective": 7,
  "deficiencies_open": 1
}
```

**Level 2: Process Owner Sign-Off (parent = Level 1 sign-offs)**

```http
POST /process-control/signoffs

{
  "period": "Q4-2026",
  "certifier_id": "finance.director@company.com",
  "certifier_name": "Finance Director",
  "certifier_role": "Process Owner",
  "parent_certification_id": "CERT_ap_manager_q4",
  "scope_summary": "Finance process — all Accounts Payable, Accounts Receivable, and General Ledger controls",
  "controls_in_scope": 19,
  "controls_effective": 18,
  "deficiencies_open": 1
}
```

**Level 3: CFO/CEO Sign-Off (parent = all Process Owner sign-offs)**

```http
POST /process-control/signoffs

{
  "period": "Q4-2026",
  "certifier_id": "cfo@company.com",
  "certifier_name": "Chief Financial Officer",
  "certifier_role": "CFO",
  "scope_summary": "All business process controls for fiscal year 2026 annual report",
  "controls_in_scope": 85,
  "controls_effective": 83,
  "deficiencies_open": 2
}
```

### 9.3 Certification Statements

When a certifier submits their sign-off, they provide a formal certification statement. This statement is stored verbatim and included in the audit package.

```http
PUT /process-control/signoffs/CERT_cfo_q4_2026/submit

{
  "statement": "Based on my review and the representations of control owners and process owners, I certify that, to the best of my knowledge, the internal controls over financial reporting for Company X were designed adequately and operated effectively during the period ended December 31, 2026, with the exception of the two deficiencies described in the attached exceptions list.",
  "exceptions": [
    {
      "exception_ref": "EX-001",
      "description": "Temporary SoD violation (SOD-FI-001) in AP department during manager vacation coverage — remediated September 2026",
      "deficiency_id": "DEF_x9y8z7",
      "status_at_sign_off": "verified_closed"
    },
    {
      "exception_ref": "EX-002",
      "description": "Unapproved journal entries threshold breached 3 times in August 2026 — root cause identified as system configuration error, corrected",
      "deficiency_id": "DEF_a1b2c3",
      "status_at_sign_off": "verified_closed"
    }
  ],
  "comments": "Both exceptions were identified through our continuous monitoring program, remediated promptly, and verified closed before period-end. The control environment is considered effective."
}
```

**Sign-off status after submission:**

| Has Exceptions | Status |
|---|---|
| No | `certified` |
| Yes | `certified_with_exceptions` |

If the certifier refuses to certify, they submit with no statement and status becomes `refused`.

### 9.4 Exceptions Declaration

Exceptions in a sign-off are not the same as open deficiencies. Exceptions in a sign-off statement acknowledge deficiencies that occurred during the period but may now be resolved. The sign-off says: "These things happened, here is what we did about them, and we still certify that the overall control environment is effective."

A certifier who cannot make this statement should refuse to certify, triggering an escalation process.

### 9.5 Roll-Up Tree Visualization

The sign-off hierarchy is returned as a tree structure for the roll-up visualization:

```http
GET /process-control/signoffs/hierarchy?period=Q4-2026

{
  "period": "Q4-2026",
  "hierarchy": [
    {
      "certification_id": "CERT_cfo_q4_2026",
      "certifier_name": "Chief Financial Officer",
      "certifier_role": "CFO",
      "status": "certified_with_exceptions",
      "controls_in_scope": 85,
      "controls_effective": 83,
      "certified_at": "2026-12-28T14:00:00Z",
      "children": [
        {
          "certification_id": "CERT_finance_dir_q4",
          "certifier_name": "Finance Director",
          "certifier_role": "Process Owner",
          "status": "certified",
          "controls_in_scope": 19,
          "controls_effective": 19,
          "certified_at": "2026-12-20T10:00:00Z",
          "children": [
            {
              "certification_id": "CERT_ap_mgr_q4",
              "certifier_name": "AP Manager",
              "certifier_role": "Control Owner",
              "status": "certified",
              "controls_in_scope": 8,
              "controls_effective": 8,
              "certified_at": "2026-12-15T09:30:00Z",
              "children": []
            }
          ]
        }
      ]
    }
  ]
}
```

### 9.6 Pending Sign-Offs

```http
GET /process-control/signoffs/pending?certifier_id=ap.manager@company.com

{
  "total": 1,
  "signoffs": [
    {
      "certification_id": "CERT_ap_mgr_q4",
      "period": "Q4-2026",
      "certifier_role": "Control Owner",
      "scope_summary": "Accounts Payable controls",
      "controls_in_scope": 8,
      "open_deficiencies": 0,
      "status": "pending"
    }
  ]
}
```

### 9.7 Sign-Off API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/process-control/signoffs` | Create sign-off record |
| GET | `/process-control/signoffs` | List sign-offs |
| GET | `/process-control/signoffs/{id}` | Get sign-off detail |
| PUT | `/process-control/signoffs/{id}/submit` | Submit certification statement |
| GET | `/process-control/signoffs/hierarchy` | Roll-up tree (filter by period) |
| GET | `/process-control/signoffs/pending` | Pending sign-offs (filter by certifier) |

---

## 10. PC Reporting

*Reference codes: PC-30 (Control Status Report), PC-31 (Dashboard), PC-32 (Audit Package Export)*

### 10.1 Control Status Dashboard

The Process Control dashboard provides an aggregate health view:

```http
GET /process-control/dashboard

{
  "total_controls": 85,
  "active_controls": 78,
  "open_deficiencies": 4,
  "pending_tests": 12,
  "pending_signoffs": 8,
  "effectiveness_rate": 93.5
}
```

Key metrics:

| Metric | Description |
|---|---|
| `total_controls` | All non-retired controls |
| `active_controls` | Controls with `status = active` |
| `open_deficiencies` | Deficiencies with `status = open` |
| `pending_tests` | Tests with `status = planned` |
| `pending_signoffs` | Sign-offs with `status = pending` |
| `effectiveness_rate` | `(effective_test_count / total_tested) × 100` |

### 10.2 Framework Coverage Maps

Framework coverage reports show which regulatory requirements are covered by active controls and where gaps exist. This is the primary tool for compliance officers managing multi-framework environments.

```http
GET /process-control/frameworks/COSO2013/coverage
GET /process-control/frameworks/SOX404/coverage
GET /process-control/frameworks/ISO27001/coverage
```

**Gap analysis view:** Control requirements with no active controls mapped are highlighted as `gap`. Requirements with controls that are `inactive`, `under_review`, or have `open_deficiencies` are highlighted as `at_risk`.

### 10.3 Audit-Ready Evidence Packages

The audit package endpoint assembles the complete documentation for a control in a single API call — the control definition, recent test history (last 5 tests), all deficiencies, and all linked evidence:

```http
GET /process-control/controls/CTRL-AP-001/audit-package

{
  "control": {
    "control_id": "CTRL-AP-001",
    "name": "AP Invoice Dual Approval",
    "version": 4,
    "key_control": true,
    "status": "active",
    "framework_mappings": [...]
  },
  "recent_tests": [
    {"test_id": "TEST_a4b7c9d1e2f3", "result": "effective", "testing_period_end": "2026-09-30", "exceptions_found": 0},
    {"test_id": "TEST_b5c8d2f4a9e1", "result": "effective", "testing_period_end": "2026-06-30", "exceptions_found": 0},
    {"test_id": "TEST_c6d9e3a5b0f2", "result": "partially_effective", "testing_period_end": "2026-03-31", "exceptions_found": 1}
  ],
  "deficiencies": [
    {"deficiency_id": "DEF_x9y8z7", "severity": "significant_deficiency", "status": "verified_closed", "title": "AP Clerk has approval rights during manager vacation"}
  ],
  "evidence": [
    {"evidence_id": "EVID_g1h2i3j4k5l6", "title": "Q3 2026 AP Invoice Sample", "content_hash": "sha256:..."},
    {"evidence_id": "EVID_h2i3j4k5l6m7", "title": "SAP SU01 Role Extract"},
    {"evidence_id": "EVID_i3j4k5l6m7n8", "title": "Risk Intelligence Engine Analysis Report Q3 2026"}
  ],
  "generated_at": "2026-09-06T12:00:00Z"
}
```

This JSON package can be exported to PDF or PPTX for presentation to external auditors.

### 10.4 Failed Controls Report

```http
GET /process-control/controls?status=active
# Filter client-side or add server-side filter:
GET /process-control/deficiencies?status=open&severity=significant_deficiency
GET /process-control/deficiencies?status=open&severity=material_weakness
```

### 10.5 Open Issues Aging

```http
GET /process-control/deficiencies?status=open

# Response includes created_at for each deficiency
# Age = today - created_at
# Flag as "overdue" if created_at + due_date < today
```

The aging report shows deficiencies sorted by age, with visual indicators for overdue items (red), approaching due date (amber), and within SLA (green).

### 10.6 PPTX/PDF Export

```http
GET /reports/process-control/summary?format=pdf&period=Q3-2026
GET /reports/process-control/framework-coverage?framework_id=COSO2013&format=pptx
GET /reports/process-control/control/{control_id}/audit-package?format=pdf
```

The export engine generates formatted reports suitable for board presentations and external audit submission.

---

## 11. Integration with Other Modules

### 11.1 AC → PC: SoD Violations Create Deficiencies (XI-02)

**Trigger:** Risk Intelligence Engine detects SoD violations during analysis or scheduled scan.

**Integration Flow:**

```
Risk Intelligence Engine analysis detects SOD-FI-001 violation for users JSMITH, MBROWN, RLOPEZ
  │
  ▼
Risk Intelligence Engine persists violations to risk_violations table
  │
  ▼
Scheduled job or Risk Intelligence Engine webhook calls:
  POST /process-control/ccm/sod-bridge
  {
    "control_id": "CTRL-AP-001",   ← the relevant mitigating control
    "violation_ids": ["ARA-JSMITH-001", "ARA-MBROWN-002", "ARA-RLOPEZ-003"]
  }
  │
  ▼
PC creates CCM execution record: FAIL, 3 findings
PC creates deficiency: "CCM breach: SoD Bridge for CTRL-AP-001 — 3 violations detected"
  │
  ▼
Deficiency appears in PC dashboard, aging report, and SOX sign-off scope
```

**Configuration:** The mapping from SoD rule IDs to control IDs is maintained in the integration configuration. For example, violations of `SOD-FI-001`, `SOD-FI-002`, and `SOD-FI-003` all map to `CTRL-AP-001` (AP dual approval control).

### 11.2 PC → RM: Control Failure Impacts Residual Risk (XL-A)

When a control deficiency is created or updated, the Risk Management module recalculates the residual risk for all enterprise risks linked to that control.

**Data flow:**

```
ControlDeficiency created (source: "ccm", severity: "significant_deficiency")
  │
  ▼
RM module receives webhook: control CTRL-AP-001 is deficient
  │
  ▼
RM fetches all enterprise risks with risk_id in CTRL-AP-001.risk_ids
  (e.g., RISK-AP-FRAUD-001, RISK-AP-ERROR-002)
  │
  ▼
RM recalculates residual risk: inherent_risk × (1 - control_effectiveness)
  Control is deficient: control_effectiveness drops from 80% to 40%
  Residual risk increases accordingly
  │
  ▼
Risk owners notified of residual risk increase
```

**Control effectiveness lookup:**

| Control Status | Effectiveness Assumed |
|---|---|
| Active, last test effective | 80–100% |
| Active, last test partially effective | 50–70% |
| Active, last test ineffective or deficiency open | 20–40% |
| Under review (no current test) | 30% |
| No test history | 50% (conservative default) |

### 11.3 PC → AM: Audit Findings Link to Controls (XI-03)

Audit Management findings are linked to Process Control controls, allowing auditors to trace each finding to the specific control that failed and the evidence package supporting it.

```
AM Audit Finding: "Duplicate payment of $45,000 to vendor ACME Corp — September 2026"
  │
  ▼
AM links finding to control: CTRL-AP-003 (Payment Run Authorization)
  │
  ▼
Finding appears in CTRL-AP-003 audit package
  │
  ▼
PC auto-creates deficiency: "Audit finding linked to CTRL-AP-003"
  source="audit_management"
  │
  ▼
Deficiency follows standard remediation lifecycle
```

**API call from AM to PC:**

```http
POST /process-control/deficiencies

{
  "control_id": "CTRL-AP-003",
  "source": "manual",
  "title": "Audit Finding: Duplicate payment to ACME Corp",
  "description": "External auditor finding: duplicate payment of $45,000 processed in September 2026 without dual authorization",
  "severity": "significant_deficiency"
}
```

### 11.4 AC Mitigation → PC Control (XL-C Unified Register)

Mitigation controls created in the AC module (via `POST /ara/mitigation/controls`) are synchronized to the PC control library as `it_dependent` controls with `source = "ARA_MITIGATION"`. This creates a unified control register across both modules.

**Sync behavior:**

- A Risk Intelligence Engine mitigation control `MIT-FI-AP-001` (Monthly AP Payment Review by CFO) is created
- A PC control record `CTRL-MITI-MIT-FI-AP-001` is created automatically with `control_nature = "manual"` and `control_type = "detective"`
- Framework mappings and SOX key control flags can be set on the PC record independently
- The PC record shows `source_reference: "ARA_MITIGATION:MIT-FI-AP-001"` for traceability
- Updates to the mitigation control's description and validity dates propagate to the PC record

This means the compliance team sees a single unified control library, and auditors can ask "show me all controls" and receive both process controls and access mitigations in one list.

---

## 12. Configuration Reference

### 12.1 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PC_CCM_RUN_CRON` | `0 3 * * *` | Cron schedule for nightly CCM rule execution (3:00 AM) |
| `PC_CCM_ENABLED` | `true` | Enable/disable scheduled CCM runs |
| `PC_SOD_BRIDGE_ENABLED` | `true` | Enable automatic SoD bridge from Risk Intelligence Engine to PC |
| `PC_EVIDENCE_STORAGE_PATH` | `/data/evidence` | Base path for evidence file storage |
| `PC_EVIDENCE_MAX_FILE_MB` | `100` | Maximum evidence file size in megabytes |
| `PC_RETENTION_DEFAULT_YEARS` | `7` | Default evidence retention period |
| `PC_DEFICIENCY_ESCALATION_DAYS` | `7` | Days overdue before escalation to CISO |
| `PC_SIGNOFF_REMINDER_DAYS` | `7` | Days before signoff deadline to send reminder |
| `PC_KEY_CONTROL_SEVERITY_UPLIFT` | `true` | Auto-elevate deficiency severity on key controls |
| `PC_AUTO_DEFICIENCY_CCM` | `true` | Auto-create deficiency on CCM breach |
| `PC_FRAMEWORK_COVERAGE_CACHE_TTL` | `3600` | Seconds to cache framework coverage reports |

### 12.2 Complete PC API Endpoint Table

| Method | Path | Reference | Description |
|---|---|---|---|
| POST | `/process-control/controls` | PC-01 | Create control |
| GET | `/process-control/controls` | PC-01 | List controls |
| GET | `/process-control/controls/{id}` | PC-01 | Get control detail |
| PUT | `/process-control/controls/{id}` | PC-01 | Update control (auto-versions) |
| PUT | `/process-control/controls/{id}/retire` | PC-01 | Retire control |
| GET | `/process-control/controls/{id}/audit-package` | PC-32 | Full audit package |
| POST | `/process-control/controls/{id}/framework-mappings` | PC-03 | Add framework mapping |
| DELETE | `/process-control/controls/{id}/framework-mappings` | PC-03 | Remove framework mapping |
| GET | `/process-control/controls/{id}/frameworks` | PC-03 | Get framework mappings |
| GET | `/process-control/frameworks/{id}/coverage` | PC-03 | Framework coverage analysis |
| POST | `/process-control/controls/{id}/tests` | PC-11 | Create test plan |
| GET | `/process-control/controls/{id}/tests` | PC-11 | Get test history |
| PUT | `/process-control/tests/{test_id}/result` | PC-11 | Record test result |
| POST | `/process-control/deficiencies` | PC-13 | Create deficiency |
| GET | `/process-control/deficiencies` | PC-13 | List deficiencies |
| GET | `/process-control/deficiencies/{id}` | PC-13 | Get deficiency |
| PUT | `/process-control/deficiencies/{id}` | PC-13 | Update deficiency |
| PUT | `/process-control/deficiencies/{id}/remediate` | PC-13 | Mark remediated |
| PUT | `/process-control/deficiencies/{id}/verify` | PC-13 | Verify and close |
| POST | `/process-control/self-assessment-campaigns` | PC-12 | Create CSA campaign |
| GET | `/process-control/self-assessments/pending` | PC-12 | Pending assessments |
| PUT | `/process-control/self-assessments/{id}/submit` | PC-12 | Submit attestation |
| POST | `/process-control/ccm-rules` | PC-20 | Create CCM rule |
| GET | `/process-control/ccm-rules` | PC-20 | List CCM rules |
| POST | `/process-control/ccm-rules/{id}/execute` | PC-22 | Execute rule |
| POST | `/process-control/ccm/run-all` | PC-22 | Run all rules |
| GET | `/process-control/ccm/dashboard` | PC-25 | CCM health dashboard |
| POST | `/process-control/ccm/sod-bridge` | PC-24 | Bridge SoD violations |
| POST | `/process-control/evidence` | PC-15 | Create evidence record |
| GET | `/process-control/evidence` | PC-15 | List evidence |
| GET | `/process-control/evidence/{id}` | PC-15 | Get evidence detail |
| PUT | `/process-control/evidence/{id}` | PC-15 | Update evidence |
| PUT | `/process-control/evidence/{id}/legal-hold` | NF-05 | Set/release legal hold |
| POST | `/process-control/signoffs` | PC-14 | Create sign-off record |
| GET | `/process-control/signoffs` | PC-14 | List sign-offs |
| PUT | `/process-control/signoffs/{id}/submit` | PC-14 | Submit certification |
| GET | `/process-control/signoffs/hierarchy` | PC-14 | Roll-up tree view |
| GET | `/process-control/signoffs/pending` | PC-14 | Pending sign-offs |
| GET | `/process-control/dashboard` | PC-31 | PC health dashboard |
