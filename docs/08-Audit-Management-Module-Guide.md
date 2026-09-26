# GovernexPlus — Audit Management (AM) Module Guide

**Audit Universe, Planning, Engagements, Workpapers, Findings (CCCE), Action Tracking**

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Audit Universe (AM-01)](#2-audit-universe-am-01)
   - 2.1 [Auditable Entity Types](#21-auditable-entity-types)
   - 2.2 [Creating Entities](#22-creating-entities)
   - 2.3 [Risk-Based Scoring (XI-04)](#23-risk-based-scoring-xi-04)
   - 2.4 [Maintaining the Universe](#24-maintaining-the-universe)
3. [Audit Planning (AM-02 to AM-04)](#3-audit-planning-am-02-to-am-04)
   - 3.1 [Plan Types](#31-plan-types)
   - 3.2 [Creating a Plan](#32-creating-a-plan)
   - 3.3 [Risk-Based Plan Generation](#33-risk-based-plan-generation)
   - 3.4 [Resource Allocation](#34-resource-allocation)
   - 3.5 [Plan Approval Workflow](#35-plan-approval-workflow)
   - 3.6 [In-Year Plan Changes](#36-in-year-plan-changes)
4. [Auditor Resources (AM-03)](#4-auditor-resources-am-03)
   - 4.1 [Resource Profile](#41-resource-profile)
   - 4.2 [Capacity Planning](#42-capacity-planning)
   - 4.3 [Availability Query](#43-availability-query)
   - 4.4 [Utilization Reports](#44-utilization-reports)
   - 4.5 [External Auditors](#45-external-auditors)
5. [Engagement Lifecycle (AM-10)](#5-engagement-lifecycle-am-10)
   - 5.1 [Engagement Types](#51-engagement-types)
   - 5.2 [Creating an Engagement](#52-creating-an-engagement)
   - 5.3 [The 6-Stage Pipeline](#53-the-6-stage-pipeline)
   - 5.4 [Advancing Stages](#54-advancing-stages)
   - 5.5 [Budget vs Actual Tracking](#55-budget-vs-actual-tracking)
6. [Work Programs and Procedures (AM-11 to AM-12)](#6-work-programs-and-procedures-am-11-to-am-12)
   - 6.1 [Work Program Templates](#61-work-program-templates)
   - 6.2 [Creating Templates](#62-creating-templates)
   - 6.3 [Cloning for Engagement](#63-cloning-for-engagement)
   - 6.4 [Procedure Execution](#64-procedure-execution)
   - 6.5 [Dual Sign-Off](#65-dual-sign-off)
   - 6.6 [Cross-References](#66-cross-references)
7. [Electronic Workpapers (AM-12)](#7-electronic-workpapers-am-12)
   - 7.1 [Document Types](#71-document-types)
   - 7.2 [Creating Workpapers](#72-creating-workpapers)
   - 7.3 [Version Management](#73-version-management)
   - 7.4 [Review Workflow](#74-review-workflow)
   - 7.5 [Cross-References](#75-cross-references)
   - 7.6 [Inline Text vs File-Based](#76-inline-text-vs-file-based)
8. [Audit Findings — CCCE Format (AM-20, AM-22)](#8-audit-findings--ccce-format-am-20-am-22)
   - 8.1 [Finding Structure — CCCE](#81-finding-structure--ccce)
   - 8.2 [Severity Levels](#82-severity-levels)
   - 8.3 [Creating Findings](#83-creating-findings)
   - 8.4 [Cross-Module Links (XI-03)](#84-cross-module-links-xi-03)
   - 8.5 [Repeat Finding Detection](#85-repeat-finding-detection)
   - 8.6 [Management Response](#86-management-response)
   - 8.7 [Finding Status Lifecycle](#87-finding-status-lifecycle)
9. [Action Tracking (AM-21)](#9-action-tracking-am-21)
   - 9.1 [Creating Actions from Findings](#91-creating-actions-from-findings)
   - 9.2 [Status Lifecycle](#92-status-lifecycle)
   - 9.3 [Closing with Evidence](#93-closing-with-evidence)
   - 9.4 [Independent Verification](#94-independent-verification)
   - 9.5 [Due Date Extensions](#95-due-date-extensions)
   - 9.6 [Overdue Detection and Escalation](#96-overdue-detection-and-escalation)
   - 9.7 [Follow-Up Audits](#97-follow-up-audits)
10. [Time Tracking (AM-14)](#10-time-tracking-am-14)
    - 10.1 [Recording Time](#101-recording-time)
    - 10.2 [Activity Types](#102-activity-types)
    - 10.3 [Time Summary per Engagement](#103-time-summary-per-engagement)
    - 10.4 [Auditor Utilization](#104-auditor-utilization)
11. [Evidence in Audit Context](#11-evidence-in-audit-context)
    - 11.1 [Attaching Evidence to Procedures and Workpapers](#111-attaching-evidence-to-procedures-and-workpapers)
    - 11.2 [Evidence Agent (XL-D)](#112-evidence-agent-xl-d)
    - 11.3 [Supported Sources](#113-supported-sources)
    - 11.4 [Point-in-Time Snapshots](#114-point-in-time-snapshots)
    - 11.5 [Evidence in Engagement Reports](#115-evidence-in-engagement-reports)
12. [AM Reporting (AM-30 to AM-32)](#12-am-reporting-am-30-to-am-32)
    - 12.1 [Engagement Report](#121-engagement-report)
    - 12.2 [Audit Dashboard](#122-audit-dashboard)
    - 12.3 [Committee Report](#123-committee-report)
    - 12.4 [Auditor Utilization Report](#124-auditor-utilization-report)
    - 12.5 [Finding Aging Report](#125-finding-aging-report)
    - 12.6 [PPTX/PDF Export](#126-pptxpdf-export)
13. [Integration with Other Modules](#13-integration-with-other-modules)
14. [Configuration Reference](#14-configuration-reference)

---

## 1. Module Overview

The Audit Management (AM) module provides GovernexPlus with a complete internal audit lifecycle — from maintaining an inventory of what can be audited, through planning, fieldwork execution, findings, management actions, and board-level reporting. It replaces SAP Audit Management for organisations transitioning off the SAP GRC stack.

### What AM Covers

| Capability | Requirement IDs |
|---|---|
| Audit universe — all auditable entities | AM-01 |
| Annual and multi-year audit planning | AM-02 |
| Risk-based plan generation (XI-04) | AM-02, XI-04 |
| Auditor resource and capacity management | AM-03 |
| Engagement lifecycle (6 stages) | AM-10 |
| Work programs and reusable procedure templates | AM-11 |
| Procedure execution with dual sign-off | AM-11 |
| Electronic workpapers with version control | AM-12 |
| Formal audit findings in CCCE format | AM-20, AM-22 |
| Cross-module finding links (XI-03) | XI-03 |
| Management action tracking with escalation | AM-21 |
| Auditor time tracking and utilization | AM-14 |
| Evidence pull from AC/PC/RM (XL-D) | XL-D |
| Committee-ready reporting | AM-30 to AM-32 |

### How AM Replaces SAP Audit Management

SAP Audit Management (part of the GRC suite) provides a structured internal audit workflow but suffers from tight SAP Basis dependency, limited integration with non-SAP systems, and the same 2027 end-of-maintenance timeline as the rest of SAP GRC 12.0. GovernexPlus replaces it with:

- A platform-agnostic audit workflow that integrates equally with SAP, Oracle, Workday, and custom systems
- Direct integration with the AC, PC, and RM modules — violations, control failures, and risk scores are available inside audit engagements without manual export/import
- XL-D evidence pull that creates immutable, SHA-256 hashed point-in-time snapshots of AC/PC/RM data as permanent audit evidence
- LLM-assisted finding narratives — the AI assistant can draft CCCE text based on the procedure conclusions and evidence collected

### Key Statistics at a Glance

- Auditable entity types: 5 (org_unit, process, system, project, vendor)
- Audit plan types: 3 (annual, multi_year, special)
- Engagement stages: 6 (planned, announced, fieldwork, draft_report, final_report, closed)
- Engagement types: 6 (financial, operational, it, compliance, special, follow_up)
- Procedure statuses: 4 (not_started, in_progress, completed, reviewed)
- Finding severity levels: 5 (critical, high, medium, low, observation)
- Finding statuses: 5 (draft, discussed, final, management_response_received, closed)
- Action statuses: 5 (open, in_progress, completed, overdue, closed_verified)

---

## 2. Audit Universe (AM-01)

The audit universe is the inventory of everything the internal audit function can audit. It is the foundation of risk-based planning — without a comprehensive, risk-scored universe, the annual plan is just a list of entities sorted alphabetically.

### 2.1 Auditable Entity Types

| Type | Value | Examples |
|---|---|---|
| Organisational unit | `org_unit` | Finance department, Treasury, Payroll, IT Operations |
| Business process | `process` | Procure-to-Pay, Order-to-Cash, Hire-to-Retire, Financial Close |
| IT system | `system` | SAP ERP, Workday HCM, Salesforce CRM, Azure AD |
| Project | `project` | ERP implementation project, Office 365 migration, Acquisition integration |
| Vendor/Third party | `vendor` | Payroll outsourcer, Cloud provider, Audit firm |

Each entity type has the same data structure. The `entity_type` field is used for filtering in reports and plan generation.

### 2.2 Creating Entities

**Request:**

```json
POST /api/am/entities

{
  "name": "Accounts Payable Process",
  "description": "End-to-end accounts payable process including vendor master management, invoice processing, and payment execution. Key risk area: SoD between invoice approval and payment release.",
  "entity_type": "process",
  "org_unit_id": 8,
  "audit_frequency": "annual",
  "primary_auditor_id": "AUD-0003"
}
```

**Response (HTTP 201):**

```json
{
  "entity_id": "ENT_a9b3c7d2e80f",
  "name": "Accounts Payable Process",
  "description": "End-to-end accounts payable process...",
  "entity_type": "process",
  "org_unit_id": 8,
  "risk_score": null,
  "last_audited_at": null,
  "audit_frequency": "annual",
  "primary_auditor_id": "AUD-0003",
  "is_active": true,
  "created_at": "2026-09-06T08:00:00"
}
```

The `risk_score` is null at creation and is populated by the risk-based scoring endpoint (Section 2.3).

### 2.3 Risk-Based Scoring (XI-04)

The composite risk score for an auditable entity is derived from three dimensions, each fed from a different GovernexPlus module:

| Dimension | Weight | Source |
|---|---|---|
| Inherent risk (RM) | 40% | Enterprise risk scores from the RM module |
| Control effectiveness (PC) | 35% | Process control test results and deficiency counts |
| Access control risk (AC) | 25% | SoD violation counts and access risk from the AC module |

**Computing the risk score:**

```json
POST /api/am/entities/ENT_a9b3c7d2e80f/compute-risk

{
  "weights": {
    "inherent_risk": 0.40,
    "control_effectiveness": 0.35,
    "last_audit_recency": 0.25
  },
  "scores": {
    "inherent_risk": 18.0,
    "control_effectiveness": 12.0,
    "last_audit_recency": 8.0
  }
}
```

The system computes: `(0.40 × 18.0) + (0.35 × 12.0) + (0.25 × 8.0) = 7.2 + 4.2 + 2.0 = 13.4`

**Response:**

```json
{
  "entity_id": "ENT_a9b3c7d2e80f",
  "computed_risk_score": 13.4,
  "inputs": {
    "inherent_risk": 18.0,
    "control_effectiveness": 12.0,
    "last_audit_recency": 8.0
  }
}
```

The `risk_score` on the entity is immediately updated. Entities are automatically sorted by risk score descending in `GET /api/am/entities` responses, making it straightforward to see the highest-risk entities at the top of the list.

The dimension scores should be sourced from the relevant modules before calling this endpoint:
- `inherent_risk`: from `GET /api/rm/risks?org_unit_id=8` — take the maximum or average residual score
- `control_effectiveness`: from `GET /api/pc/controls?org_unit_id=8` — score based on deficiency count and test results
- `last_audit_recency`: calculate days since `last_audited_at`, normalise to 0–25 scale (the longer since the last audit, the higher the score)

### 2.4 Maintaining the Universe

**Annual refresh process:**

1. Run `GET /api/am/entities?is_active=true` to export the full current universe
2. Review for entities that should be added (new systems deployed, new processes, new vendors)
3. Review for entities that should be deactivated (decommissioned systems, completed projects, terminated vendor relationships)
4. Add new entities via `POST /api/am/entities`
5. Deactivate retired entities via `PUT /api/am/entities/{entity_id}` with `{"is_active": false}`
6. Recompute risk scores for all active entities via `POST /api/am/entities/{entity_id}/compute-risk`

**API Endpoints — Audit Universe:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/am/entities` | Create entity |
| GET | `/api/am/entities` | List entities (filters: entity_type, is_active, search) |
| PUT | `/api/am/entities/{entity_id}` | Update entity |
| POST | `/api/am/entities/{entity_id}/compute-risk` | Compute XI-04 risk score |

---

## 3. Audit Planning (AM-02 to AM-04)

The annual audit plan translates the risk universe into a schedule of engagements, allocating audit resources across the highest-priority entities for the year.

### 3.1 Plan Types

| Type | Value | Description |
|---|---|---|
| Annual | `annual` | Standard 12-month audit plan for a single fiscal year |
| Multi-year | `multi_year` | Rolling 3-year strategic plan showing planned engagement coverage |
| Special | `special` | Ad-hoc plan for a specific investigation, regulatory request, or project |

### 3.2 Creating a Plan

**Request:**

```json
POST /api/am/plans

{
  "name": "Internal Audit Plan 2026",
  "description": "Annual risk-based audit plan for fiscal year 2026. Coverage prioritises IT/cyber risks following the Q4 2025 control assessment findings.",
  "plan_type": "annual",
  "fiscal_year": 2026,
  "period_start": "2026-01-01T00:00:00",
  "period_end": "2026-12-31T23:59:59",
  "total_audit_hours": 3200,
  "allocated_budget": 450000.00,
  "prepared_by": "AUD-0001",
  "risk_methodology": "Risk-based prioritisation using composite entity risk scores from RM (40%), PC (35%), and AC (25%) modules. Top 12 entities by score included in plan."
}
```

**Response (HTTP 201):**

```json
{
  "plan_id": "PLAN_e7f2a9b4c01d",
  "name": "Internal Audit Plan 2026",
  "plan_type": "annual",
  "fiscal_year": 2026,
  "period_start": "2026-01-01T00:00:00",
  "period_end": "2026-12-31T23:59:59",
  "total_audit_hours": 3200,
  "allocated_budget": 450000.0,
  "status": "draft",
  "prepared_by": "AUD-0001",
  "approved_by": null,
  "approved_at": null
}
```

Plans begin in `draft` status and must be approved before engagements can be formally launched (advanced past `announced`).

### 3.3 Risk-Based Plan Generation

The most powerful planning feature is the automated risk-based plan generation. This creates a plan and engagements for the top-N highest-risk auditable entities in a single API call.

**Request:**

```json
POST /api/am/plans/generate-risk-based

{
  "fiscal_year": 2026,
  "top_n": 12,
  "prepared_by": "AUD-0001"
}
```

The system:
1. Queries all active auditable entities ordered by `risk_score` descending
2. Takes the top N
3. Creates an `AuditPlan` record with the name "Risk-Based Audit Plan 2026"
4. Creates one `AuditEngagement` in `planned` status for each entity
5. Sets the engagement's `risk_rating` to `high` if the entity's risk score is ≥ 15, otherwise `medium`

**Response:**

```json
{
  "plan_id": "PLAN_f3a8b1c70e2d",
  "fiscal_year": 2026,
  "entities_included": 12,
  "engagements_created": [
    "ENG_aa1bb2cc3dd4",
    "ENG_bb2cc3dd4ee5",
    "..."
  ]
}
```

After generation, the audit team reviews the auto-generated engagements, assigns lead auditors and team members, sets planned dates, and submits the plan for approval.

### 3.4 Resource Allocation

After the risk-based plan is generated, resource allocation involves:

1. **Query available auditors:** `GET /api/am/resources/available?min_hours=160&skill=IT_audit`
2. **Assign to engagements:** Include `lead_auditor_id`, `lead_auditor_name`, and `team_members` in the engagement update
3. **Set planned dates:** Include `planned_start` and `planned_end` based on auditor availability and the entity's priority
4. **Set budget hours:** Include `budget_hours` per engagement

Total `budget_hours` across all engagements in the plan should not exceed the plan's `total_audit_hours`. The system does not automatically enforce this constraint but the dashboard highlights over-allocation.

### 3.5 Plan Approval Workflow

```
draft
  |
  v  [prepared_by submits]
pending_approval
  |
  v  [CAE or audit committee approves]
approved
  |
  v  [first engagement advances to fieldwork]
in_progress
  |
  v  [last engagement closed]
completed
```

**Submit for approval:**

```
PUT /api/am/plans/{plan_id}/submit
{}
```

**Approve:**

```json
PUT /api/am/plans/{plan_id}/approve

{
  "approved_by": "AUD-0001"
}
```

`approved_by` and `approved_at` are stamped on the plan record. Once approved, the plan cannot be reverted to draft. In-year changes are handled through documented amendments (Section 3.6).

### 3.6 In-Year Plan Changes with Audit Trail

Plans sometimes need to change during the year — a new regulatory requirement may require an unplanned audit, or resource constraints may require deferring an engagement. In-year changes are managed by:

1. Adding new engagements to the plan via `POST /api/am/engagements` (with the plan's `plan_id`)
2. Updating existing engagement dates via `PUT /api/am/engagements/{engagement_id}`
3. Recording the reason for the change in the engagement's `objective` or `scope` field

All changes are audit-trailed through the standard GovernexPlus audit log (`AuditLogger`). The plan's `total_audit_hours` can be updated via `PUT /api/am/plans/{plan_id}` to reflect any budget adjustments.

**API Endpoints — Plans:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/am/plans` | Create plan |
| GET | `/api/am/plans` | List plans (filters: status, fiscal_year) |
| GET | `/api/am/plans/{plan_id}` | Get plan |
| PUT | `/api/am/plans/{plan_id}` | Update plan |
| PUT | `/api/am/plans/{plan_id}/submit` | Submit for approval |
| PUT | `/api/am/plans/{plan_id}/approve` | Approve plan |
| POST | `/api/am/plans/generate-risk-based` | Auto-generate risk-based plan |

---

## 4. Auditor Resources (AM-03)

The resource module maintains a roster of internal and external auditors, their skills and certifications, and their available capacity. This information drives resource allocation in planning and time-tracking in execution.

### 4.1 Resource Profile

| Field | Type | Description |
|---|---|---|
| `auditor_id` | string | Unique identifier |
| `name` | string | Full name |
| `email` | string | Contact email |
| `title` | string | Job title (e.g. "Senior Auditor", "IT Audit Manager") |
| `skills` | JSON array | List of skill tags: `financial_audit`, `IT_audit`, `data_analytics`, `SAP`, `Oracle`, etc. |
| `certifications` | JSON array | List of held certifications |
| `available_hours_per_month` | float | Monthly capacity (default 160 hours = full-time) |
| `is_active` | boolean | Whether the resource is available for assignment |
| `is_external` | boolean | True for co-sourced or outsourced auditors |

**Supported certification values:** `CIA` (Certified Internal Auditor), `CISA` (Certified Information Systems Auditor), `CPA` (Certified Public Accountant), `CISSP` (Certified Information Systems Security Professional), `CFE` (Certified Fraud Examiner), `CRMA` (Certification in Risk Management Assurance). The field is a free-form array — any certification acronym can be stored.

### 4.2 Capacity Planning

**Create a resource:**

```json
POST /api/am/resources

{
  "name": "Layla Hassan",
  "email": "l.hassan@acme.com",
  "title": "Senior IT Auditor",
  "skills": ["IT_audit", "SAP", "data_analytics", "penetration_testing"],
  "certifications": ["CISA", "CISSP"],
  "available_hours_per_month": 140.0,
  "is_external": false
}
```

**Response (HTTP 201):**

```json
{
  "auditor_id": "AUD_b8e3f1a72c04",
  "name": "Layla Hassan",
  "email": "l.hassan@acme.com",
  "title": "Senior IT Auditor",
  "skills": ["IT_audit", "SAP", "data_analytics", "penetration_testing"],
  "certifications": ["CISA", "CISSP"],
  "available_hours_per_month": 140.0,
  "is_active": true,
  "is_external": false
}
```

`available_hours_per_month` of 140.0 accounts for 20 hours per month of non-audit activities (training, admin, meetings). Adjust this value to reflect actual capacity after overhead.

### 4.3 Availability Query

To find auditors available for a new engagement:

```
GET /api/am/resources/available?min_hours=80&skill=IT_audit
```

This returns all active auditors with `available_hours_per_month >= 80` and `IT_audit` in their `skills` array.

**Response:**

```json
{
  "total": 3,
  "auditors": [
    {
      "auditor_id": "AUD_b8e3f1a72c04",
      "name": "Layla Hassan",
      "skills": ["IT_audit", "SAP", "data_analytics"],
      "available_hours_per_month": 140.0
    },
    ...
  ]
}
```

Note: `available_hours_per_month` is a static capacity figure on the resource profile. It does not dynamically subtract committed hours from other engagements. For true availability, cross-reference with the time summary of active engagements (`GET /api/am/engagements/{id}/time-summary`) to see how many hours are already committed.

### 4.4 Utilization Reports

```
GET /api/am/auditors/{auditor_id}/utilization
```

**Response:**

```json
{
  "auditor_id": "AUD_b8e3f1a72c04",
  "total_hours_logged": 312.5,
  "available_hours_per_month": 140.0,
  "utilization_pct": 223.2
}
```

`utilization_pct` here is cumulative since the first time entry — not monthly. For monthly utilization, filter time entries by date range in a separate query. A utilization above 100% monthly indicates the auditor is over-committed and additional resources should be requested.

### 4.5 External Auditors

External (co-sourced) auditors are created with `is_external: true`. They appear in all the same resource queries. Co-sourced engagement costs should be tracked in the engagement's `budget` metadata and reconciled against actual invoices outside the system.

**API Endpoints — Resources:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/am/resources` | Create auditor resource |
| GET | `/api/am/resources` | List resources (filters: is_external, is_active) |
| PUT | `/api/am/resources/{auditor_id}` | Update resource |
| GET | `/api/am/resources/available` | Query available auditors |
| GET | `/api/am/auditors/{auditor_id}/utilization` | Utilization report |

---

## 5. Engagement Lifecycle (AM-10)

An audit engagement is a single, bounded audit project. It has a defined scope, a team, a set of procedures, findings, and a formal report. The engagement lifecycle has six sequential stages.

### 5.1 Engagement Types

| Type | Value | Description |
|---|---|---|
| Financial | `financial` | Review of financial statements, reconciliations, journal entries |
| Operational | `operational` | Process effectiveness, efficiency, and internal controls |
| IT | `it` | IT general controls, application controls, cybersecurity |
| Compliance | `compliance` | Regulatory compliance, policy adherence |
| Special | `special` | Fraud investigation, whistleblower report, board-directed inquiry |
| Follow-up | `follow_up` | Verification that prior audit actions have been implemented |

### 5.2 Creating an Engagement

**Request:**

```json
POST /api/am/engagements

{
  "plan_id": "PLAN_e7f2a9b4c01d",
  "entity_id": "ENT_a9b3c7d2e80f",
  "title": "Accounts Payable Process Audit 2026",
  "objective": "To assess whether the Accounts Payable process is designed and operating effectively, with particular focus on segregation of duties, vendor master controls, and payment authorisation.",
  "scope": "Scope covers all AP transactions processed between 2026-01-01 and 2026-06-30. Excludes inter-company transactions. Sample size: all transactions above SAR 50,000; statistical sample of 75 for transactions below.",
  "engagement_type": "operational",
  "lead_auditor_id": "AUD-0003",
  "lead_auditor_name": "Khalid Al-Mansouri",
  "team_members": ["AUD_b8e3f1a72c04", "AUD-0007"],
  "planned_start": "2026-09-15T00:00:00",
  "planned_end": "2026-10-31T23:59:59",
  "budget_hours": 240,
  "risk_rating": "high",
  "methodology": "IPPF 2024 Standards. Risk-based approach using SoD violation data from AC module and control test results from PC module."
}
```

**Response (HTTP 201):**

```json
{
  "engagement_id": "ENG_c3d4e5f6a7b8",
  "plan_id": 1,
  "entity_id": 3,
  "title": "Accounts Payable Process Audit 2026",
  "objective": "To assess whether the Accounts Payable process...",
  "scope": "Scope covers all AP transactions...",
  "engagement_type": "operational",
  "status": "planned",
  "lead_auditor_id": "AUD-0003",
  "lead_auditor_name": "Khalid Al-Mansouri",
  "team_members": ["AUD_b8e3f1a72c04", "AUD-0007"],
  "planned_start": "2026-09-15T00:00:00",
  "planned_end": "2026-10-31T23:59:59",
  "actual_start": null,
  "actual_end": null,
  "budget_hours": 240,
  "actual_hours": 0,
  "risk_rating": "high"
}
```

### 5.3 The 6-Stage Pipeline

```
PLANNED --> ANNOUNCED --> FIELDWORK --> DRAFT_REPORT --> FINAL_REPORT --> CLOSED
```

**Stage 1: PLANNED**
The engagement has been approved in the audit plan. Scope is defined, the team is assigned, and dates are set. The auditee has not yet been notified.

Key activities in this stage:
- Finalise scope statement and audit objectives
- Assign all team members
- Create or clone a work program (Section 6)
- Request relevant data from the auditee in advance
- Pull initial evidence from AC/PC/RM via XL-D (Section 11)

**Stage 2: ANNOUNCED**
The auditee has been formally notified. An engagement letter is distributed.

Key activities:
- Send engagement letter to auditee management
- Schedule kick-off meeting
- Request access to systems, documents, and personnel
- Distribute fieldwork schedule

**Stage 3: FIELDWORK**
Active evidence collection and procedure execution. `actual_start` is automatically stamped when the engagement advances to this stage.

Key activities:
- Execute audit procedures (Section 6.4)
- Collect and attach evidence to workpapers
- Document conclusions for each procedure
- Draft preliminary findings as they are identified
- Record time entries daily (Section 10)

**Stage 4: DRAFT_REPORT**
Fieldwork is complete. Findings are drafted in CCCE format and shared with the auditee for factual accuracy review.

Key activities:
- Complete all procedure sign-offs (preparer + reviewer)
- Create formal finding records (Section 8)
- Run repeat-finding check for each finding
- Share draft report with auditee management
- Record management responses to findings

**Stage 5: FINAL_REPORT**
Management responses have been received. The final report is prepared incorporating responses and recommendations.

Key activities:
- Record management response for each finding
- Update finding status to `management_response_received`
- Prepare final report document
- Create action items from findings (Section 9)
- Obtain final report sign-off from Chief Audit Executive

**Stage 6: CLOSED**
The engagement is complete. Workpapers are archived. `actual_end` is automatically stamped.

Key activities:
- Verify all workpapers are in `final` status
- Archive workpaper files
- Schedule follow-up audit if required
- Close the engagement record

### 5.4 Advancing Stages

Engagement status advances are explicit and validated. The system enforces that stages can only move forward, not backward.

**Advance to next stage:**

```
PUT /api/am/engagements/{engagement_id}/advance
{}
```

**Response:**

```json
{
  "engagement_id": "ENG_c3d4e5f6a7b8",
  "status": "announced",
  "actual_start": null,
  "actual_end": null,
  ...
}
```

When advanced to `fieldwork`, `actual_start` is automatically set to UTC now. When advanced to `closed`, `actual_end` is automatically set.

If the engagement is already in `closed` status, the advance endpoint returns HTTP 400 with `"Engagement cannot be advanced further"`.

To set the stage explicitly (for example, to record a retrospective status), use `PUT /api/am/engagements/{engagement_id}` with a `status` field (no validation is applied in direct updates, so use with care).

### 5.5 Budget vs Actual Tracking

As time is logged against the engagement (Section 10), `actual_hours` accumulates. Compare budget vs actual at any time:

```
GET /api/am/engagements/{engagement_id}/time-summary
```

**Response:**

```json
{
  "engagement_id": "ENG_c3d4e5f6a7b8",
  "total_hours": 187.5,
  "budget_hours": 240,
  "by_auditor": {
    "AUD-0003": 82.0,
    "AUD_b8e3f1a72c04": 75.5,
    "AUD-0007": 30.0
  },
  "by_activity": {
    "planning": 20.0,
    "fieldwork": 132.0,
    "reporting": 25.5,
    "review": 10.0
  },
  "entries": [...]
}
```

At 187.5 of 240 budgeted hours with fieldwork still in progress, the lead auditor should monitor for budget overrun and either accelerate procedures or request a budget increase from the CAE.

**API Endpoints — Engagements:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/am/engagements` | Create engagement |
| GET | `/api/am/engagements` | List engagements (filters: status, type, lead_auditor_id) |
| GET | `/api/am/engagements/{engagement_id}` | Get engagement |
| PUT | `/api/am/engagements/{engagement_id}` | Update engagement |
| PUT | `/api/am/engagements/{engagement_id}/advance` | Advance to next stage |

---

## 6. Work Programs and Procedures (AM-11 to AM-12)

Work programs define the structured set of audit procedures to be executed during fieldwork. Templates can be created once and reused across engagements of the same type.

### 6.1 Work Program Templates

A work program template is a reusable document that defines the standard procedures for an audit type. For example, an "AP Process Audit" template would list all the standard procedures (vendor master testing, invoice matching, payment authorisation testing, etc.) that should be performed for any AP audit.

Templates have `is_template: true`. When cloned for a specific engagement, the clone has `is_template: false` and belongs to that engagement's context.

### 6.2 Creating Templates

**Request:**

```json
POST /api/am/work-programs

{
  "name": "Accounts Payable Audit - Standard Program",
  "description": "Standard work program for AP process audits. Covers vendor master controls, invoice processing, and payment authorisation.",
  "audit_type": "operational",
  "is_template": true,
  "procedures": [
    {
      "ref": "AP-01",
      "title": "Vendor Master Change Testing",
      "description": "Select all vendor master changes in the period. Test 25 or all, whichever is lower. Verify: (1) dual approval obtained, (2) supporting documentation on file, (3) changed fields match supporting docs.",
      "expected_hours": 12
    },
    {
      "ref": "AP-02",
      "title": "SoD Violation Review",
      "description": "Obtain SoD violation report from AC module for FI-MM conflicts. Identify users with both vendor master change and payment release capabilities. Review compensating control evidence for each.",
      "expected_hours": 8
    },
    {
      "ref": "AP-03",
      "title": "Invoice Processing Controls",
      "description": "Three-way match testing: select 50 invoices above SAR 10,000 from statistical sample. Verify PO, GR, and invoice quantities and amounts agree within tolerance.",
      "expected_hours": 20
    },
    {
      "ref": "AP-04",
      "title": "Payment Authorisation Testing",
      "description": "Select all payments above SAR 100,000 and statistical sample of 30 below. Verify payment approval chain matches the delegation of authority matrix.",
      "expected_hours": 16
    }
  ]
}
```

**Response (HTTP 201):**

```json
{
  "program_id": "WP_d9f1a3b72e08",
  "name": "Accounts Payable Audit - Standard Program",
  "audit_type": "operational",
  "is_template": true,
  "version": 1,
  "procedures": [...]
}
```

### 6.3 Cloning for Engagement

When starting a new AP audit, clone the template rather than creating procedures from scratch:

```json
POST /api/am/work-programs/WP_d9f1a3b72e08/clone

{
  "name": "AP Audit 2026 - Work Program (Clone of Standard)"
}
```

**Response:**

```json
{
  "program_id": "WP_e0a2b4c83f19",
  "name": "AP Audit 2026 - Work Program (Clone of Standard)",
  "is_template": false,
  "version": 1,
  "procedures": [...]
}
```

The clone starts with all the template procedures. The auditor then customises the cloned program for the specific engagement — adjusting sample sizes, adding entity-specific procedures, or removing procedures that are out of scope.

### 6.4 Procedure Execution

Each procedure in an engagement has a lifecycle that records its execution, conclusion, hours, and sign-offs.

**Create a procedure on an engagement:**

```json
POST /api/am/engagements/ENG_c3d4e5f6a7b8/procedures

{
  "ref_number": "AP-01",
  "title": "Vendor Master Change Testing",
  "description": "Select all vendor master changes in the period. Test 25 or all, whichever is lower...",
  "assigned_to_id": "AUD_b8e3f1a72c04",
  "assigned_to_name": "Layla Hassan"
}
```

**Procedure status flow:**

```
not_started --> in_progress --> completed --> reviewed
```

**Update to in_progress:**

```json
PUT /api/am/procedures/{procedure_id}

{
  "status": "in_progress"
}
```

**Mark complete (preparer sign-off — Step 1 of dual sign-off):**

```json
PUT /api/am/procedures/{procedure_id}/complete

{
  "preparer_id": "AUD_b8e3f1a72c04",
  "conclusion": "Tested 25 vendor master changes from the period. 24 of 25 had dual approval with supporting documentation. Exception: Change ID VMC-0441 (bank account change for vendor VP-0441) was approved by a single approver. This change was subsequently used in the AP incident INC-0221. See workpaper WPR-0012 for detailed testing. FINDING RAISED: AP-F001.",
  "hours_spent": 14.5
}
```

### 6.5 Dual Sign-Off

Dual sign-off is the internal audit standard control that prevents a single auditor from both performing and approving their own work.

**Step 1: Preparer completes**

The auditor who performed the work documents their conclusion and records hours via `PUT /api/am/procedures/{procedure_id}/complete`. Status advances from `in_progress` to `completed`. Fields populated: `preparer_id`, `prepared_at`, `conclusion`, `hours_spent`.

**Step 2: Reviewer signs off**

A different auditor (typically the audit supervisor or manager) reviews the work and either approves or sends it back for revision.

```json
PUT /api/am/procedures/{procedure_id}/review

{
  "reviewer_id": "AUD-0003",
  "review_notes": "Concur with conclusion. The VMC-0441 exception is correctly identified and cross-referenced to the incident report. Finding text is clear and supported by evidence in WPR-0012."
}
```

Status advances to `reviewed`. Fields populated: `reviewer_id`, `reviewed_at`, `review_notes`.

The system does not prevent the same user from acting as both preparer and reviewer — this is a process control that must be enforced through team structure and supervision.

### 6.6 Cross-References

Procedures can reference other procedures, workpapers, or findings:

```json
PUT /api/am/procedures/{procedure_id}

{
  "cross_references": ["AP-02", "WPR-0012", "AP-F001"]
}
```

Cross-references are stored as a free-form JSON array of reference strings. They appear in procedure detail views and are included in the engagement report.

**API Endpoints — Work Programs and Procedures:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/am/work-programs` | Create work program / template |
| GET | `/api/am/work-programs/templates` | List templates (filter: audit_type) |
| POST | `/api/am/work-programs/{program_id}/clone` | Clone template for engagement |
| POST | `/api/am/engagements/{engagement_id}/procedures` | Create procedure |
| GET | `/api/am/engagements/{engagement_id}/procedures` | List procedures |
| PUT | `/api/am/procedures/{procedure_id}` | Update procedure |
| PUT | `/api/am/procedures/{procedure_id}/complete` | Preparer sign-off |
| PUT | `/api/am/procedures/{procedure_id}/review` | Reviewer sign-off |

---

## 7. Electronic Workpapers (AM-12)

Workpapers are the documentary evidence that supports audit conclusions. Every material conclusion in an engagement must be supported by one or more workpapers. GovernexPlus supports both inline text workpapers and file-reference workpapers.

### 7.1 Document Types

| Type | Value | Description |
|---|---|---|
| Narrative | `narrative` | Written analysis, process descriptions, interview notes |
| Schedule | `schedule` | Data tables, reconciliations, calculations |
| Confirmation | `confirmation` | External confirmations, management representations |
| Extract | `extract` | System-generated reports, data extracts, queries |
| Screenshot | `screenshot` | System screenshots, configuration evidence |

### 7.2 Creating Workpapers

**Request:**

```json
POST /api/am/engagements/ENG_c3d4e5f6a7b8/workpapers

{
  "title": "Vendor Master Change Population - Q1-Q2 2026",
  "description": "Complete population of vendor master changes for the audit scope period. Source: SAP change log table CDHDR/CDPOS filtered for business object KRED.",
  "document_type": "extract",
  "content": "| Change ID | Date       | User     | Field Changed      | Old Value         | New Value          | Approver 1 | Approver 2 |\n|-----------|------------|----------|--------------------|-------------------|--------------------|------------|------------|\n| VMC-0438  | 2026-01-12 | USR-0055 | Bank Account IBAN  | SA44000000000000  | SA44000000000001   | MGR-0010   | MGR-0022   |\n| VMC-0439  | 2026-02-03 | USR-0055 | Payment Terms      | 30 days           | 45 days            | MGR-0010   | MGR-0022   |\n| VMC-0440  | 2026-03-15 | USR-0060 | Vendor Name        | Al-Rashid Trading | Al-Rashid Trading  | MGR-0010   | MGR-0022   |\n| VMC-0441  | 2026-04-28 | USR-0075 | Bank Account IBAN  | SA44000000000100  | SA44000000000999   | MGR-0012   |    —       |",
  "procedure_id": "PROC_a1b2c3d4e5f6",
  "preparer_id": "AUD_b8e3f1a72c04",
  "cross_references": ["AP-01", "AP-F001"]
}
```

**Response (HTTP 201):**

```json
{
  "workpaper_id": "WPR_f8a7b6c5d4e3",
  "engagement_id": 5,
  "procedure_id": "PROC_a1b2c3d4e5f6",
  "title": "Vendor Master Change Population - Q1-Q2 2026",
  "document_type": "extract",
  "content": "| Change ID | ...",
  "version": 1,
  "status": "draft",
  "review_status": "pending_review",
  "preparer_id": "AUD_b8e3f1a72c04",
  "prepared_at": "2026-09-06T13:00:00",
  "reviewer_id": null,
  "reviewed_at": null
}
```

### 7.3 Version Management

When a workpaper requires significant revision (e.g. additional data is added, or an error is corrected after review), a new version should be created rather than overwriting the original. This is done by creating a new workpaper with `previous_version_id` set in the metadata field pointing to the prior workpaper ID:

```json
POST /api/am/engagements/ENG_c3d4e5f6a7b8/workpapers

{
  "title": "Vendor Master Change Population - Q1-Q2 2026 (v2)",
  "document_type": "extract",
  "content": "...(updated with corrected VMC-0441 details)...",
  "preparer_id": "AUD_b8e3f1a72c04",
  "metadata": {
    "previous_version_id": "WPR_f8a7b6c5d4e3",
    "version_notes": "Added approver field for VMC-0441. Confirmed single-approver exception after re-querying SAP."
  }
}
```

The prior version is retained with `status: "superseded"` (set manually via `PUT /api/am/workpapers/{workpaper_id}` with `{"status": "superseded"}`).

### 7.4 Review Workflow

```
draft (review_status: pending_review)
    |
    |-- reviewer approves --> final (review_status: reviewed)
    |
    `-- reviewer rejects --> draft (review_status: revision_needed)
```

**Submit for review (explicitly):**

```
PUT /api/am/workpapers/{workpaper_id}/submit-review
{}
```

This sets `review_status` to `pending_review`. If the workpaper was already in `pending_review` from creation, this is a no-op.

**Reviewer approves:**

```json
PUT /api/am/workpapers/{workpaper_id}/review

{
  "reviewer_id": "AUD-0003",
  "approved": true,
  "review_note": "Population verified against SAP extract. VMC-0441 exception clearly marked."
}
```

When `approved: true`, `status` advances to `final` and `review_status` becomes `reviewed`.

**Reviewer sends back:**

```json
PUT /api/am/workpapers/{workpaper_id}/review

{
  "reviewer_id": "AUD-0003",
  "approved": false,
  "review_note": "VMC-0441 approver field shows a dash. Please confirm whether this is a genuine exception (single approver) or a data extraction issue. Recheck SAP before raising a finding."
}
```

When `approved: false`, `review_status` becomes `revision_needed`. The preparer updates the workpaper and resubmits.

### 7.5 Cross-References

The `cross_references` array links a workpaper to related procedures, other workpapers, and findings:

```json
{
  "cross_references": ["AP-01", "WPR_a9b8c7d6e5f4", "AP-F001"]
}
```

Cross-references are bidirectional by convention — if workpaper A references finding F001, auditors also update finding F001 to note it is supported by workpaper A (via the finding's own metadata or the procedure's `evidence_ids` field).

### 7.6 Inline Text vs File-Based

**Inline text:** Store content directly in the `content` field as markdown text, a data table, or a narrative. Best for: interview summaries, process narratives, small data extracts.

**File-based:** Store file metadata in `file_name`, `file_path`, and `file_size` fields. The file itself is stored in the configured object store (S3-compatible or local filesystem, per the `WORKPAPER_STORAGE_PATH` environment variable). Best for: Excel schedules, PDF confirmations, large screenshots.

Both types can coexist — a workpaper can have both `content` (for a brief narrative summary) and `file_name` (for the supporting spreadsheet).

**API Endpoints — Workpapers:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/am/engagements/{engagement_id}/workpapers` | Create workpaper |
| GET | `/api/am/engagements/{engagement_id}/workpapers` | List workpapers |
| PUT | `/api/am/workpapers/{workpaper_id}` | Update workpaper |
| PUT | `/api/am/workpapers/{workpaper_id}/submit-review` | Submit for review |
| PUT | `/api/am/workpapers/{workpaper_id}/review` | Approve or return |

---

## 8. Audit Findings — CCCE Format (AM-20, AM-22)

Audit findings are the formal, documented observations that result from audit procedures. GovernexPlus enforces the CCCE (Condition, Criteria, Cause, Effect) finding structure, which is the international standard for internal audit findings under the IIA's International Professional Practices Framework.

### 8.1 Finding Structure — CCCE

A complete audit finding has five components:

**Condition — What was found**

The specific, factual gap, exception, or control failure identified during fieldwork. This is what the auditor actually observed. It must be specific, quantified where possible, and grounded in evidence.

Example: *"Of 25 vendor master bank account changes tested, one change (VMC-0441, dated 28 April 2026) was approved by a single approver (MGR-0012 only). The second required approver field was blank in the SAP workflow log. This single-exception change was subsequently used to re-route a payment of SAR 125,000 to an unverified account."*

**Criteria — What should be**

The policy, procedure, regulation, or control standard that the condition falls short of. This is the benchmark against which the exception is measured.

Example: *"Per the Accounts Payable Policy (AP-POL-2024, Section 4.3), all vendor bank account changes require dual approval from two authorised approvers with Grade 6 or above. This control is also required by the company's internal SoD policy and the SoD ruleset deployed in the GovernexPlus AC module (rule FI-MM-003)."*

**Cause — Why it happened**

The root cause of the gap. Not just what happened, but why the control failed. Root causes are typically people (training, awareness), process (design gap, missing step), or technology (system configuration, missing automation).

Example: *"Root cause (process): The SAP approval workflow was configured to allow a single approver to process vendor changes when the primary approver is on leave, as a workaround implemented in 2024. This exception path was never subject to compensating control review and was not documented in the risk register."*

**Effect — What is the risk**

The actual or potential impact of the condition — financial, reputational, regulatory, or operational. This is the answer to "so what?"

Example: *"The AP incident INC_d8e7a1c4f930 (SAR 125,000 fraudulent payment) has been directly attributed to this control failure. The same workflow path was available to 14 other users as at the audit date. Estimated maximum exposure from the uncorrected configuration: SAR 2.1M based on average payment values processed through this vendor category."*

**Recommendation — What to do**

Specific, actionable steps the organisation should take to remediate the condition and prevent recurrence. Avoid vague recommendations like "improve controls."

Example: *"1. Immediately remove the single-approver exception path from the SAP vendor master workflow configuration. 2. Implement a compensating SoD rule in the AC module for the leave-absence scenario requiring escalation to a different approver rather than single-approval override. 3. Run a lookback review of all single-approver vendor changes in the past 24 months and verify each against business justification. 4. Update the AP risk register entry (RISK_a3f7b2c81d04) to reflect the identified control failure."*

### 8.2 Severity Levels

| Severity | Value | Definition |
|---|---|---|
| Critical | `critical` | Actual financial loss, fraud, or regulatory violation has occurred, or the control failure exposes the organisation to an imminent high-probability material loss. Requires immediate escalation to the CAE and Audit Committee. |
| High | `high` | Significant control failure or exposure. No actual loss, but material risk. Requires management action within 30 days. |
| Medium | `medium` | Moderate control weakness. Risk is limited in scope or financial exposure. Requires management action within 90 days. |
| Low | `low` | Minor process improvement. Risk is low. Requires management action within 180 days. |
| Observation | `observation` | Best-practice recommendation. No formal finding raised. Management response optional. |

### 8.3 Creating Findings

**Step 1.** Complete all relevant audit procedures and collect supporting workpapers.
**Step 2.** Draft the finding text in CCCE format.
**Step 3.** Create the finding record.

**Request:**

```json
POST /api/am/engagements/ENG_c3d4e5f6a7b8/findings

{
  "ref_number": "AP-F001",
  "title": "Single-Approver Vendor Bank Account Change Led to SAR 125,000 Fraudulent Payment",
  "severity": "critical",
  "category": "segregation_of_duties",
  "condition": "Of 25 vendor master bank account changes tested, one change (VMC-0441, dated 28 April 2026) was approved by a single approver (MGR-0012 only). The second required approver field was blank in the SAP workflow log. This single-exception change was subsequently used to re-route a payment of SAR 125,000 to an unverified account.",
  "criteria": "Per the Accounts Payable Policy (AP-POL-2024, Section 4.3), all vendor bank account changes require dual approval from two authorised approvers with Grade 6 or above. This control is also required by the company's internal SoD policy and the SoD ruleset deployed in the GovernexPlus AC module (rule FI-MM-003).",
  "cause": "Root cause (process): The SAP approval workflow was configured to allow a single approver to process vendor changes when the primary approver is on leave, as a workaround implemented in 2024. This exception path was never subject to compensating control review and was not documented in the risk register.",
  "effect": "The AP incident INC_d8e7a1c4f930 (SAR 125,000 fraudulent payment) has been directly attributed to this control failure. The same workflow path was available to 14 other users as at the audit date. Estimated maximum exposure: SAR 2.1M based on average payment values processed through this vendor category.",
  "recommendation": "1. Immediately remove the single-approver exception path from the SAP vendor master workflow configuration. 2. Implement a compensating SoD rule in the AC module for the leave-absence scenario. 3. Run a lookback review of all single-approver vendor changes in the past 24 months. 4. Update the AP risk register entry (RISK_a3f7b2c81d04) to reflect the identified control failure."
}
```

**Response (HTTP 201):**

```json
{
  "finding_id": "FND_a1b2c3d4e5f6",
  "engagement_id": 5,
  "ref_number": "AP-F001",
  "title": "Single-Approver Vendor Bank Account Change Led to SAR 125,000 Fraudulent Payment",
  "severity": "critical",
  "category": "segregation_of_duties",
  "condition": "Of 25 vendor master bank account changes tested...",
  "criteria": "Per the Accounts Payable Policy...",
  "cause": "Root cause (process)...",
  "effect": "The AP incident INC_d8e7a1c4f930...",
  "recommendation": "1. Immediately remove...",
  "status": "draft",
  "repeat_finding": false,
  "prior_finding_id": null,
  "management_response": null,
  "management_action_owner": null,
  "management_target_date": null,
  "risk_id": null,
  "control_id": null,
  "violation_id": null
}
```

### 8.4 Cross-Module Links (XI-03)

After creating the finding, link it to the relevant records in RM, PC, and AC.

**Link to EnterpriseRisk:**

```json
POST /api/am/findings/FND_a1b2c3d4e5f6/link-risk

{
  "risk_id": "RISK_a3f7b2c81d04"
}
```

**Link to ProcessControl:**

```json
POST /api/am/findings/FND_a1b2c3d4e5f6/link-control

{
  "control_id": "CTRL-008"
}
```

**Link to RiskViolation (AC module):**

```json
POST /api/am/findings/FND_a1b2c3d4e5f6/link-violation

{
  "violation_id": "VOL_c7d8e9f0a1b2"
}
```

These links create the XI-03 cross-module integration — a finding has a direct pointer to the enterprise risk it affects, the control it tested, and any SoD violation from the AC module that supports it. Board-level reports can then show findings grouped by risk, demonstrating the connection between control failures and risk exposures.

### 8.5 Repeat Finding Detection

Repeat findings (prior-year findings that have recurred because management action was not completed or not effective) are flagged automatically.

```
GET /api/am/findings/{finding_id}/check-repeat
```

The system searches for other active findings with the same `title` in earlier engagements. If any are found, `repeat_finding` is set to `true` on the current finding and `prior_finding_id` is set to the most recent prior finding's internal ID.

**Response:**

```json
{
  "finding_id": "FND_a1b2c3d4e5f6",
  "is_repeat": true,
  "prior_findings": ["FND_x1y2z3a4b5c6"]
}
```

Repeat findings should be flagged in the engagement report as an elevated risk — they indicate management action from prior cycles was ineffective. The severity of a repeat finding should typically be escalated one level (e.g. from Medium to High) per the organisation's audit escalation policy.

### 8.6 Management Response

After the draft report is issued, management provides a formal response to each finding:

```json
PUT /api/am/findings/FND_a1b2c3d4e5f6/management-response

{
  "management_response": "Management accepts the finding. The single-approver workflow exception path was implemented as an emergency measure in 2024 and should have been removed upon return of the primary approver. We will remove this configuration immediately and implement the compensating SoD rule. A lookback review will be completed by 31 October 2026.",
  "management_action_owner": "VP Finance",
  "management_target_date": "2026-10-31T23:59:59"
}
```

When this endpoint is called, `status` automatically advances to `management_response_received`.

### 8.7 Finding Status Lifecycle

```
draft
  |
  v  [discussed with auditee]
discussed
  |
  v  [finalised in draft report]
final
  |
  v  [management response recorded]
management_response_received
  |
  v  [all actions verified closed]
closed
```

Status transitions other than `management_response_received` (which is automatic) require an explicit `status` update via `PUT /api/am/findings/{finding_id}`.

**API Endpoints — Findings:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/am/engagements/{engagement_id}/findings` | Create finding |
| GET | `/api/am/findings` | List findings (filters: status, severity, engagement_id) |
| PUT | `/api/am/findings/{finding_id}` | Update finding |
| PUT | `/api/am/findings/{finding_id}/management-response` | Record management response |
| POST | `/api/am/findings/{finding_id}/link-risk` | Link to EnterpriseRisk |
| POST | `/api/am/findings/{finding_id}/link-control` | Link to ProcessControl |
| POST | `/api/am/findings/{finding_id}/link-violation` | Link to RiskViolation |
| GET | `/api/am/findings/{finding_id}/check-repeat` | Check for repeat finding |

---

## 9. Action Tracking (AM-21)

Management actions translate each finding's recommendation into concrete, tracked commitments. An action has an owner, a due date, and a verification requirement.

### 9.1 Creating Actions from Findings

Each finding's recommendation should result in one or more action items. Best practice is one action per discrete recommendation step.

**Request:**

```json
POST /api/am/findings/FND_a1b2c3d4e5f6/actions

{
  "description": "Remove single-approver exception path from SAP vendor master workflow configuration (transaction SPRO, FI-AP-AP-I). Validate change in development, quality, and production environments. Obtain change approval from IT Change Advisory Board.",
  "owner_id": "USR-0055",
  "owner_name": "Sami Al-Otaibi (IT SAP Basis Lead)",
  "due_date": "2026-09-30T23:59:59"
}
```

**Response (HTTP 201):**

```json
{
  "action_id": "ACT_b7c8d9e0f1a2",
  "finding_id": 7,
  "description": "Remove single-approver exception path...",
  "owner_id": "USR-0055",
  "owner_name": "Sami Al-Otaibi (IT SAP Basis Lead)",
  "due_date": "2026-09-30T23:59:59",
  "status": "open",
  "escalation_level": 0,
  "evidence_of_closure": null,
  "evidence_ids": [],
  "verified_by": null,
  "completed_at": null
}
```

### 9.2 Status Lifecycle

```
open --> in_progress --> completed --> closed_verified
  |
  `----> overdue   (auto-set when due_date passes without completion)
```

| Status | Meaning |
|---|---|
| `open` | Action assigned; owner has not started |
| `in_progress` | Owner is actively working on the action |
| `completed` | Owner claims completion with evidence; awaiting verifier sign-off |
| `overdue` | Due date passed without completion |
| `closed_verified` | Verifier has confirmed the action is effectively completed |

Update status as work progresses:

```json
PUT /api/am/actions/{action_id}

{
  "status": "in_progress"
}
```

### 9.3 Closing with Evidence

When an action is complete, the owner provides evidence of closure before the auditor can verify it:

```json
PUT /api/am/actions/ACT_b7c8d9e0f1a2/close

{
  "evidence_of_closure": "Single-approver exception path removed via SAP transport TR-20260915-001, approved by CAB on 12 September 2026 and transported to production on 14 September 2026. Post-transport verification confirmed the workflow now requires two approvers at all times. SAP system log extract attached as evidence document EV-0044.",
  "evidence_ids": ["EV-0044"]
}
```

**Response:**

```json
{
  "action_id": "ACT_b7c8d9e0f1a2",
  "status": "completed",
  "completed_at": "2026-09-14T16:30:00",
  "evidence_of_closure": "Single-approver exception path removed...",
  "evidence_ids": ["EV-0044"],
  "verified_by": null
}
```

### 9.4 Independent Verification

After the owner closes an action, an auditor (typically the lead auditor or a senior team member) independently verifies that the action is effectively implemented:

```json
PUT /api/am/actions/ACT_b7c8d9e0f1a2/close

{
  "evidence_of_closure": "Single-approver exception path removed...",
  "evidence_ids": ["EV-0044"],
  "verified_by": "AUD-0003"
}
```

When `verified_by` is provided, `status` advances to `closed_verified` and `verified_at` is stamped. This closes the action and it is excluded from future overdue reports.

The `verified_by` auditor should be different from the action owner. The system does not enforce this — process controls and team structure ensure independence.

### 9.5 Due Date Extensions

If a due date needs to be extended (with documented justification), update the action:

```json
PUT /api/am/actions/ACT_b7c8d9e0f1a2

{
  "due_date": "2026-10-31T23:59:59",
  "description": "Remove single-approver exception path... NOTE: Due date extended from 2026-09-30 to 2026-10-31 per CAB scheduling constraints. Extension approved by CAE on 2026-09-20."
}
```

All changes to actions are captured in the platform audit log. Extensions should be used sparingly — repeated extensions on the same action are a finding-in-themselves and should be escalated.

### 9.6 Overdue Detection and Escalation

**Detect and mark overdue actions:**

```
GET /api/am/actions/overdue
```

This endpoint queries all actions where `due_date < now` and status is `open` or `in_progress`, marks them as `overdue`, and returns them.

**Response:**

```json
{
  "total_overdue": 4,
  "actions": [
    {
      "action_id": "ACT_d3e4f5a6b7c8",
      "description": "Implement compensating SoD rule...",
      "owner_name": "Sami Al-Otaibi",
      "due_date": "2026-09-15T23:59:59",
      "status": "overdue",
      "escalation_level": 0,
      "days_overdue": 21
    },
    ...
  ]
}
```

**Escalate all overdue actions:**

```
POST /api/am/actions/escalate
{}
```

This increments `escalation_level` on every overdue action and stamps `last_escalated_at`. The notification delivery module sends escalation alerts based on `escalation_level`:

| Level | Recipients | Triggered by |
|---|---|---|
| 0 → 1 | Action owner | First escalation (action overdue) |
| 1 → 2 | Action owner + direct manager | Second escalation (7 days later) |
| 2 → 3 | Owner + manager + departmental VP | Third escalation (14 days later) |
| 3+ | All above + CAE | Subsequent escalations (monthly) |

The scheduler runs the escalation job weekly by default (configurable via `AM_ESCALATION_FREQUENCY`).

### 9.7 Follow-Up Audits

When a high-severity finding has actions that were not completed by the due date or where management's response was inadequate, a follow-up audit engagement should be planned. Create a follow-up engagement with `engagement_type: "follow_up"`:

```json
POST /api/am/engagements

{
  "title": "AP SoD Control - Follow-Up Audit 2026",
  "engagement_type": "follow_up",
  "objective": "Verify that all management actions from the AP Audit 2026 (finding AP-F001) have been effectively implemented and are operating as designed.",
  "scope": "Limited to the vendor master change workflow configuration and the compensating SoD rule implementation.",
  "planned_start": "2026-12-01T00:00:00",
  "planned_end": "2026-12-15T23:59:59",
  "budget_hours": 40
}
```

**API Endpoints — Actions:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/am/findings/{finding_id}/actions` | Create action |
| PUT | `/api/am/actions/{action_id}` | Update action |
| PUT | `/api/am/actions/{action_id}/close` | Close with evidence and/or verify |
| GET | `/api/am/actions/overdue` | Get and mark overdue actions |
| POST | `/api/am/actions/escalate` | Escalate all overdue actions |

---

## 10. Time Tracking (AM-14)

Time tracking records the hours each auditor spends on each engagement, broken down by activity type. This data feeds resource utilization reports and budget-vs-actual analysis.

### 10.1 Recording Time

Time is recorded at the engagement level (and optionally linked to a specific procedure).

**Request:**

```json
POST /api/am/engagements/ENG_c3d4e5f6a7b8/time

{
  "auditor_id": "AUD_b8e3f1a72c04",
  "auditor_name": "Layla Hassan",
  "date": "2026-09-20",
  "hours": 7.5,
  "activity_type": "fieldwork",
  "description": "Tested vendor master change population (procedures AP-01 and AP-02). Documented exception VMC-0441. Prepared workpaper WPR_f8a7b6c5d4e3.",
  "procedure_id": "PROC_a1b2c3d4e5f6"
}
```

**Response (HTTP 201):**

```json
{
  "engagement_id": 5,
  "procedure_id": "PROC_a1b2c3d4e5f6",
  "auditor_id": "AUD_b8e3f1a72c04",
  "auditor_name": "Layla Hassan",
  "date": "2026-09-20T00:00:00",
  "hours": 7.5,
  "activity_type": "fieldwork",
  "description": "Tested vendor master change population..."
}
```

`actual_hours` on the engagement is incremented by the logged hours immediately.

### 10.2 Activity Types

| Type | Value | Typical Activities |
|---|---|---|
| Planning | `planning` | Risk assessment, scope development, work program preparation, resource planning |
| Fieldwork | `fieldwork` | Procedure execution, data analysis, interviews, evidence collection |
| Reporting | `reporting` | Finding documentation, draft report preparation, workpaper finalisation |
| Review | `review` | Workpaper review, finding review, supervisor quality checks |
| Admin | `admin` | Team meetings, status updates, travel, training |

All time logged should be assigned to one of these types. The time summary shows hours by activity type, enabling analysis of audit efficiency (e.g. what percentage of time is spent on fieldwork vs reporting).

### 10.3 Time Summary per Engagement

```
GET /api/am/engagements/{engagement_id}/time-summary
```

See Section 5.5 for the full response example. Key fields:

- `total_hours`: cumulative actual hours across all auditors
- `budget_hours`: from the engagement record
- `by_auditor`: hours broken down by auditor ID
- `by_activity`: hours broken down by activity type
- `entries`: all individual time entries

### 10.4 Auditor Utilization

```
GET /api/am/auditors/{auditor_id}/utilization
```

**Response:**

```json
{
  "auditor_id": "AUD_b8e3f1a72c04",
  "total_hours_logged": 312.5,
  "available_hours_per_month": 140.0,
  "utilization_pct": 223.2
}
```

Note that `total_hours_logged` is all-time cumulative, not monthly. For monthly utilization analysis, filter time entries by date range and compute the percentage manually against `available_hours_per_month`.

**API Endpoints — Time Tracking:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/am/engagements/{engagement_id}/time` | Log time entry |
| GET | `/api/am/engagements/{engagement_id}/time-summary` | Time summary report |
| GET | `/api/am/auditors/{auditor_id}/utilization` | Auditor utilization |

---

## 11. Evidence in Audit Context

Evidence management in GovernexPlus goes beyond file attachments. The XL-D integration enables auditors to pull immutable, point-in-time snapshots of data from AC, PC, and RM modules directly into an engagement as formal audit evidence.

### 11.1 Attaching Evidence to Procedures and Workpapers

Evidence can be referenced in two ways:

1. **`evidence_ids` on procedures:** A JSON array of evidence document IDs (from the evidence store). These IDs reference GRCEvidence records that can be attached from any source.

2. **`content` on workpapers:** Inline text content that serves as evidence (e.g. a pasted data extract, an interview record).

3. **`file_name` / `file_path` on workpapers:** Reference to a file uploaded to the document store.

### 11.2 Evidence Agent (XL-D)

The XL-D Evidence Agent pulls live data from other GovernexPlus modules, serialises it to canonical JSON, computes a SHA-256 hash for integrity, and stores it as an immutable GRCEvidence record linked to the engagement. This creates an unalterable audit trail — the data as it existed at a specific point in time is preserved permanently.

**Pull evidence for an engagement:**

```json
POST /api/am/engagements/ENG_c3d4e5f6a7b8/pull-evidence

{
  "source": "sod_violations",
  "filters": {
    "rule_ids": ["FI-MM-001", "FI-MM-003"],
    "from": "2026-01-01",
    "to": "2026-06-30",
    "user_ids": ["USR-0075"]
  },
  "title": "SoD Violations - USR-0075 - AP Audit Scope Period",
  "pulled_by": "AUD_b8e3f1a72c04"
}
```

**Response:**

```json
{
  "evidence_id": "EV_c4d5e6f7a8b9",
  "engagement_id": "ENG_c3d4e5f6a7b8",
  "source": "sod_violations",
  "title": "SoD Violations - USR-0075 - AP Audit Scope Period",
  "record_count": 3,
  "sha256_hash": "e3b0c44298fc1c149afb...",
  "pulled_by": "AUD_b8e3f1a72c04",
  "pulled_at": "2026-09-20T14:00:00",
  "immutable": true
}
```

The evidence can also be pulled at the procedure level:

```json
POST /api/am/procedures/{procedure_id}/pull-evidence

{
  "source": "sod_violations",
  "filters": { ... },
  "title": "SoD Evidence for AP-02",
  "pulled_by": "AUD_b8e3f1a72c04"
}
```

### 11.3 Supported Sources

| Source | Value | Description |
|---|---|---|
| SoD Violations | `sod_violations` | RiskViolation records from the AC module. Filters: `rule_ids`, `from`, `to`, `user_ids` |
| CCM Executions | `ccm_executions` | Continuous control monitoring execution results from PC. Filters: `from`, `to`, `control_ids` |
| Firefighter Sessions | `firefighter_sessions` | Emergency access sessions with embedded activities from the Firefighter module. Filters: `from`, `to`, `user_ids` |
| Risk Baseline | `risk_baseline` | EnterpriseRisk records with latest assessments from RM. Filters: `risk_ids` |

### 11.4 Point-in-Time Snapshots

The key audit-quality feature of XL-D is immutability. Once an evidence record is created:

- The source data snapshot cannot be modified
- The SHA-256 hash is computed at pull time and stored permanently
- Any subsequent change to the source data in AC/PC/RM does NOT change the evidence record
- Re-pulling the same source at a later date may produce a different hash if the underlying data has changed — this difference itself can be used as evidence of change

This immutability satisfies auditing standards that require evidence to be preserved in its original form and ensures that the engagement's evidence file reflects the true state of the system at the time of the audit.

### 11.5 Evidence in Engagement Reports

The engagement report (`GET /api/am/engagements/{engagement_id}/report`) includes all findings and actions. Evidence IDs referenced in procedures and workpapers should be documented in the workpaper cross-references. A full evidence inventory for the engagement can be obtained by querying:

```
GET /api/evidence?engagement_id=ENG_c3d4e5f6a7b8
```

(From the evidence management module endpoints.)

**API Endpoints — Evidence:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/am/engagements/{engagement_id}/pull-evidence` | Pull XL-D evidence for engagement |
| POST | `/api/am/procedures/{procedure_id}/pull-evidence` | Pull XL-D evidence for procedure |

---

## 12. AM Reporting (AM-30 to AM-32)

### 12.1 Engagement Report

The engagement report is the primary deliverable of an internal audit. It aggregates the engagement record, all findings in CCCE format, severity summary, and all management actions.

```
GET /api/am/engagements/{engagement_id}/report
```

**Response structure:**

```json
{
  "engagement": { ... },
  "findings_count": 3,
  "severity_summary": {
    "critical": 1,
    "high": 1,
    "medium": 1
  },
  "findings": [
    {
      "finding_id": "FND_a1b2c3d4e5f6",
      "ref_number": "AP-F001",
      "title": "Single-Approver Vendor Bank Account Change...",
      "severity": "critical",
      "condition": "...",
      "criteria": "...",
      "cause": "...",
      "effect": "...",
      "recommendation": "...",
      "management_response": "Management accepts the finding...",
      "management_target_date": "2026-10-31T23:59:59"
    },
    ...
  ],
  "actions": [
    {
      "action_id": "ACT_b7c8d9e0f1a2",
      "description": "Remove single-approver exception path...",
      "owner_name": "Sami Al-Otaibi",
      "due_date": "2026-09-30T23:59:59",
      "status": "completed"
    },
    ...
  ],
  "report_generated_at": "2026-10-31T08:00:00"
}
```

This response payload maps directly to the formal audit report. The GovernexPlus report export engine formats it into the organisation's report template (Word/PDF).

### 12.2 Audit Dashboard

The internal audit department dashboard provides real-time status across all engagements and findings.

```
GET /api/am/dashboard
```

**Response:**

```json
{
  "total_auditable_entities": 48,
  "engagements_in_progress": 4,
  "open_findings": 23,
  "critical_open_findings": 2,
  "overdue_actions": 5
}
```

`engagements_in_progress` counts engagements in `announced`, `fieldwork`, or `draft_report` status. `open_findings` excludes findings in `closed` status. `critical_open_findings` counts critical-severity findings that are not yet closed. `overdue_actions` counts actions in `overdue` status.

### 12.3 Committee Report

The audit committee report provides a board-level summary across all engagements for a fiscal year.

```
GET /api/am/committee-report?fiscal_year=2026
```

**Response:**

```json
{
  "fiscal_year": 2026,
  "audit_plans": 1,
  "total_engagements": 12,
  "completed_engagements": 7,
  "completion_rate": 58.3,
  "open_findings": 14,
  "critical_findings": 2,
  "high_findings": 5,
  "overdue_management_actions": 5,
  "generated_at": "2026-09-06T14:00:00"
}
```

The committee report is designed to fit on a single page of a board pack. The AI assistant can narrate it into a board memo: `POST /api/ai/grc-assist` with `{"module": "am", "action": "committee_memo", "fiscal_year": 2026}`.

### 12.4 Auditor Utilization Report

Query utilization for all auditors by iterating:

```
GET /api/am/resources
GET /api/am/auditors/{auditor_id}/utilization   (for each resource)
```

Aggregate into a team utilization table. A future API enhancement (`GET /api/am/team-utilization`) will return this in a single call.

### 12.5 Finding Aging Report

Identify findings that have been open for extended periods:

```
GET /api/am/findings?status=draft
GET /api/am/findings?status=discussed
GET /api/am/findings?status=final
GET /api/am/findings?status=management_response_received
```

For each finding, compute `days_open = today - created_at`. Findings open beyond the following thresholds should be escalated:

| Severity | Escalation Threshold |
|---|---|
| Critical | 7 days without management response |
| High | 30 days without management response |
| Medium | 90 days without management response |
| Low | 180 days without management response |

### 12.6 PPTX/PDF Export

Export an engagement report, committee report, or audit plan via the reporting engine:

```json
POST /api/reports/export

{
  "report_type": "engagement_report",
  "format": "pdf",
  "engagement_id": "ENG_c3d4e5f6a7b8"
}
```

```json
POST /api/reports/export

{
  "report_type": "audit_committee",
  "format": "pptx",
  "fiscal_year": 2026
}
```

Templates are configurable per tenant. Contact your GovernexPlus administrator to customise the report template with your organisation's branding and standard cover page.

---

## 13. Integration with Other Modules

### AM → RM (XI-03: Findings to Risks)

- Audit findings are linked to enterprise risks via `POST /api/am/findings/{finding_id}/link-risk`
- A finding linked to a risk triggers the risk owner to reconsider the residual score (via an ad-hoc assessment)
- The risk's `related_finding_ids` array is updated to maintain bidirectional traceability

### AM → PC (Findings to Controls)

- Audit findings are linked to process controls via `POST /api/am/findings/{finding_id}/link-control`
- A finding against a control should trigger a control deficiency record in the PC module
- The PC module then feeds back into XL-A (RM module) to update the system-indicated residual risk

### AM → AC (Evidence from SoD violations)

- XL-D evidence pull from `sod_violations` source retrieves AC module violation data
- This provides auditors with the factual basis for findings related to access control weaknesses
- Firefighter session data (`firefighter_sessions`) is also available via XL-D for privileged access audits

### XI-04: Audit Planning from RM + PC + AC

- The audit universe risk score formula (`RM 40% + PC 35% + AC 25%`) consumes live data from all three modules
- High RM residual scores drive the RM 40% component
- Control failures (deficiencies, failed tests) from PC drive the PC 35% component
- SoD violation counts and access risk scores from AC drive the AC 25% component
- This creates a dynamic, data-driven audit prioritisation that updates as risk conditions change throughout the year

---

## 14. Configuration Reference

### All AM API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/am/entities` | Create auditable entity |
| GET | `/api/am/entities` | List entities |
| PUT | `/api/am/entities/{entity_id}` | Update entity |
| POST | `/api/am/entities/{entity_id}/compute-risk` | Compute XI-04 risk score |
| POST | `/api/am/plans` | Create audit plan |
| GET | `/api/am/plans` | List plans |
| GET | `/api/am/plans/{plan_id}` | Get plan |
| PUT | `/api/am/plans/{plan_id}` | Update plan |
| PUT | `/api/am/plans/{plan_id}/submit` | Submit for approval |
| PUT | `/api/am/plans/{plan_id}/approve` | Approve plan |
| POST | `/api/am/plans/generate-risk-based` | Auto-generate plan |
| POST | `/api/am/resources` | Create auditor resource |
| GET | `/api/am/resources` | List resources |
| PUT | `/api/am/resources/{auditor_id}` | Update resource |
| GET | `/api/am/resources/available` | Query available auditors |
| GET | `/api/am/auditors/{auditor_id}/utilization` | Utilization report |
| POST | `/api/am/engagements` | Create engagement |
| GET | `/api/am/engagements` | List engagements |
| GET | `/api/am/engagements/{engagement_id}` | Get engagement |
| PUT | `/api/am/engagements/{engagement_id}` | Update engagement |
| PUT | `/api/am/engagements/{engagement_id}/advance` | Advance stage |
| GET | `/api/am/engagements/{engagement_id}/report` | Engagement report |
| GET | `/api/am/engagements/{engagement_id}/time-summary` | Time summary |
| POST | `/api/am/work-programs` | Create work program |
| GET | `/api/am/work-programs/templates` | List templates |
| POST | `/api/am/work-programs/{program_id}/clone` | Clone template |
| POST | `/api/am/engagements/{engagement_id}/procedures` | Create procedure |
| GET | `/api/am/engagements/{engagement_id}/procedures` | List procedures |
| PUT | `/api/am/procedures/{procedure_id}` | Update procedure |
| PUT | `/api/am/procedures/{procedure_id}/complete` | Preparer sign-off |
| PUT | `/api/am/procedures/{procedure_id}/review` | Reviewer sign-off |
| POST | `/api/am/engagements/{engagement_id}/workpapers` | Create workpaper |
| GET | `/api/am/engagements/{engagement_id}/workpapers` | List workpapers |
| PUT | `/api/am/workpapers/{workpaper_id}` | Update workpaper |
| PUT | `/api/am/workpapers/{workpaper_id}/submit-review` | Submit for review |
| PUT | `/api/am/workpapers/{workpaper_id}/review` | Approve or return |
| POST | `/api/am/engagements/{engagement_id}/findings` | Create finding |
| GET | `/api/am/findings` | List findings |
| PUT | `/api/am/findings/{finding_id}` | Update finding |
| PUT | `/api/am/findings/{finding_id}/management-response` | Record response |
| POST | `/api/am/findings/{finding_id}/link-risk` | Link to risk |
| POST | `/api/am/findings/{finding_id}/link-control` | Link to control |
| POST | `/api/am/findings/{finding_id}/link-violation` | Link to violation |
| GET | `/api/am/findings/{finding_id}/check-repeat` | Check repeat |
| POST | `/api/am/findings/{finding_id}/actions` | Create action |
| PUT | `/api/am/actions/{action_id}` | Update action |
| PUT | `/api/am/actions/{action_id}/close` | Close with evidence |
| GET | `/api/am/actions/overdue` | Get overdue actions |
| POST | `/api/am/actions/escalate` | Escalate overdue actions |
| POST | `/api/am/engagements/{engagement_id}/time` | Log time entry |
| POST | `/api/am/engagements/{engagement_id}/pull-evidence` | XL-D evidence pull |
| POST | `/api/am/procedures/{procedure_id}/pull-evidence` | XL-D procedure evidence |
| GET | `/api/am/dashboard` | Audit dashboard |
| GET | `/api/am/committee-report` | Committee report |

### Engagement Type Configuration

Engagement types are fixed at the database enum level: `financial`, `operational`, `it`, `compliance`, `special`, `follow_up`. Additional types require a schema migration.

### Finding Severity Definitions

The five severity levels map to action urgency:

| Severity | Required Response Time | Escalation |
|---|---|---|
| Critical | Immediate (same business day) | CAE + Audit Committee notification within 24 hours |
| High | 30 days to management response | CAE notification within 48 hours |
| Medium | 90 days to management response | Audit manager notification |
| Low | 180 days to management response | No mandatory escalation |
| Observation | Discretionary | No formal tracking required |

### Action Escalation Rules

Default escalation schedule (configurable via `AM_ESCALATION_*` environment variables):

| Variable | Default | Description |
|---|---|---|
| `AM_ESCALATION_FREQUENCY` | `weekly` | How often the escalation job runs |
| `AM_ESCALATION_L1_DAYS` | `0` | Days overdue before level-1 escalation (owner reminder) |
| `AM_ESCALATION_L2_DAYS` | `7` | Days overdue before level-2 escalation (manager) |
| `AM_ESCALATION_L3_DAYS` | `14` | Days overdue before level-3 escalation (VP) |
| `AM_ESCALATION_L4_DAYS` | `30` | Days overdue before level-4 escalation (CAE) |
| `AM_CRITICAL_RESPONSE_HOURS` | `24` | Hours before critical finding escalates to Audit Committee |

---

*Last updated: 2026-09-06 | GovernexPlus AM Module | Requirements AM-01 through AM-32, XI-03, XI-04, XL-D*
