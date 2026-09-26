# GovernexPlus — Risk Management (RM) Module Guide

**Enterprise Risk Register, Assessments, KRIs, Response Plans, Incidents, Heatmap**

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Risk Register (RM-01 to RM-04)](#2-risk-register-rm-01-to-rm-04)
   - 2.1 [Risk Structure](#21-risk-structure)
   - 2.2 [Risk Scoring](#22-risk-scoring)
   - 2.3 [Creating a Risk](#23-creating-a-risk)
   - 2.4 [Updating Risks](#24-updating-risks)
   - 2.5 [Risk Status Lifecycle](#25-risk-status-lifecycle)
   - 2.6 [Linking to Controls and Findings](#26-linking-to-controls-and-findings)
   - 2.7 [Control Coverage Signal (XL-A)](#27-control-coverage-signal-xl-a)
3. [Risk Assessment (RM-10 to RM-12)](#3-risk-assessment-rm-10-to-rm-12)
   - 3.1 [Assessment Types](#31-assessment-types)
   - 3.2 [Creating Assessments](#32-creating-assessments)
   - 3.3 [Assessment Workflow](#33-assessment-workflow)
   - 3.4 [Residual Score Update](#34-residual-score-update)
   - 3.5 [Assessment Campaigns](#35-assessment-campaigns)
   - 3.6 [Multi-Assessor Consensus](#36-multi-assessor-consensus)
4. [Risk Appetite and Tolerance (RM-03)](#4-risk-appetite-and-tolerance-rm-03)
   - 4.1 [Setting Appetite](#41-setting-appetite)
   - 4.2 [Appetite vs Tolerance](#42-appetite-vs-tolerance)
   - 4.3 [Breach Detection](#43-breach-detection)
   - 4.4 [System-Indicated Residual](#44-system-indicated-residual)
5. [Key Risk Indicators — KRI (RM-13)](#5-key-risk-indicators--kri-rm-13)
   - 5.1 [KRI Structure](#51-kri-structure)
   - 5.2 [Creating KRIs](#52-creating-kris)
   - 5.3 [Recording Measurements](#53-recording-measurements)
   - 5.4 [Traffic-Light Status Logic](#54-traffic-light-status-logic)
   - 5.5 [KRI Dashboard](#55-kri-dashboard)
   - 5.6 [Breach Alerts and Notifications](#56-breach-alerts-and-notifications)
6. [Risk Response Plans (RM-20)](#6-risk-response-plans-rm-20)
   - 6.1 [Response Types](#61-response-types)
   - 6.2 [Creating Response Plans](#62-creating-response-plans)
   - 6.3 [Status Tracking](#63-status-tracking)
   - 6.4 [Effectiveness Rating](#64-effectiveness-rating)
7. [Incidents and Loss Events (RM-22)](#7-incidents-and-loss-events-rm-22)
   - 7.1 [Incident Structure](#71-incident-structure)
   - 7.2 [Reporting an Incident](#72-reporting-an-incident)
   - 7.3 [Linking to Risks](#73-linking-to-risks)
   - 7.4 [Root Cause Analysis](#74-root-cause-analysis)
   - 7.5 [Corrective Actions](#75-corrective-actions)
   - 7.6 [Status Lifecycle](#76-status-lifecycle)
8. [Risk Review and Attestation (RM-23)](#8-risk-review-and-attestation-rm-23)
   - 8.1 [Review Frequency Setup](#81-review-frequency-setup)
   - 8.2 [Overdue Review Detection](#82-overdue-review-detection)
   - 8.3 [Review Attestation](#83-review-attestation)
   - 8.4 [Escalation for Overdue Reviews](#84-escalation-for-overdue-reviews)
9. [RM Reporting (RM-12, RM-30, RM-31)](#9-rm-reporting-rm-12-rm-30-rm-31)
   - 9.1 [Risk Heatmap](#91-risk-heatmap)
   - 9.2 [Risk Trends](#92-risk-trends)
   - 9.3 [Top Risks](#93-top-risks)
   - 9.4 [Risk-Control Coverage](#94-risk-control-coverage)
   - 9.5 [Overdue Reviews Report](#95-overdue-reviews-report)
   - 9.6 [Board/Committee Risk Reports](#96-boardcommittee-risk-reports)
   - 9.7 [PPTX/PDF Export](#97-pptxpdf-export)
10. [Integration with Other Modules](#10-integration-with-other-modules)
11. [Configuration Reference](#11-configuration-reference)

---

## 1. Module Overview

The Risk Management (RM) module provides GovernexPlus with a full enterprise risk lifecycle — from the initial identification of a risk through assessment, appetite monitoring, response planning, incident recording, and board-level reporting. It is the GRC equivalent of SAP GRC Risk Management 12.0 and supersedes that product entirely for customers who have adopted GovernexPlus.

### What RM Covers

| Capability | Requirement IDs |
|---|---|
| Enterprise risk register with bilingual support | RM-01, RM-02, RM-04 |
| Inherent and residual risk scoring | RM-01 |
| Risk appetite and tolerance framework | RM-03 |
| Periodic, ad-hoc, and consensus assessments | RM-10, RM-11 |
| Assessment workflow (draft → approved) | RM-12 |
| Key Risk Indicators with traffic-light status | RM-13 |
| Risk response plans (accept/mitigate/transfer/avoid) | RM-20 |
| Incident and loss-event recording | RM-22 |
| Risk review attestation and scheduling | RM-23 |
| Heatmap, trends, coverage, and board reports | RM-25 to RM-31 |
| Control-failure feedback to residual risk (XL-A) | XL-A cross-module |

### How RM Replaces SAP GRC Risk Management

SAP GRC Risk Management 12.0 reaches general maintenance end in December 2027 (extended support to 2030). GovernexPlus replaces it with:

- No SAP Basis dependency — runs on PostgreSQL/SQLite with a standard Python/FastAPI stack
- SaaS economics — multi-tenant from the ground up, no per-landscape licensing
- Actionable risk — KRIs connect to live data rather than requiring manual uploads
- XL-A integration — control failures from the Process Control module automatically adjust the system-indicated residual risk score
- LLM narratives — the AI assistant can generate plain-language board summaries directly from register data

### Key Statistics at a Glance

- Risk categories: 6 (strategic, operational, financial, compliance, it_cyber, reputational)
- Scoring dimensions: likelihood 1–5, impact 1–5, score = L × I (max 25)
- Risk zones: low (1–5), medium (6–11), high (12–19), critical (20–25)
- KRI statuses: normal, warning, breach
- Response types: accept, mitigate, transfer, avoid
- Assessment workflow states: draft, submitted, reviewed, approved
- Incident states: reported, investigating, resolved, closed

---

## 2. Risk Register (RM-01 to RM-04)

The risk register is the canonical source of truth for every identified organisational risk. All other RM sub-modules — assessments, appetite checks, KRIs, responses, incidents — link back to a record in the register.

### 2.1 Risk Structure

Each `EnterpriseRisk` record carries the following key fields:

| Field | Type | Description |
|---|---|---|
| `risk_id` | string | Unique identifier within the tenant (e.g. `RISK_a3f7b2c81d04`) |
| `title` | string | Short, clear risk title (English) |
| `description` | text | Full description in English |
| `description_ar` | text | Full description in Arabic (bilingual tenants) |
| `category` | enum | `strategic`, `operational`, `financial`, `compliance`, `it_cyber`, `reputational` |
| `org_unit_id` | integer | Foreign key to organisational unit |
| `risk_owner_id` | string | User ID of the assigned risk owner |
| `risk_owner_name` | string | Display name of the risk owner (denormalised for reporting) |
| `status` | enum | Current lifecycle status |
| `next_review_date` | datetime | Scheduled next review |
| `review_frequency` | string | `monthly`, `quarterly`, `semi_annual`, `annual` |
| `related_control_ids` | JSON array | List of ProcessControl IDs that address this risk |
| `related_finding_ids` | JSON array | List of AuditFinding IDs linked to this risk |
| `is_active` | boolean | Soft-delete flag |

**Scoring fields:**

| Field | Type | Description |
|---|---|---|
| `inherent_likelihood` | integer 1–5 | Likelihood before controls |
| `inherent_impact` | integer 1–5 | Impact before controls |
| `inherent_score` | float | `inherent_likelihood × inherent_impact` |
| `residual_likelihood` | integer 1–5 | Likelihood after controls (assessor-owned) |
| `residual_impact` | integer 1–5 | Impact after controls (assessor-owned) |
| `residual_score` | float | `residual_likelihood × residual_impact` (assessor-owned) |
| `control_coverage` | string | `effective`, `degraded`, `failed`, `uncontrolled` (XL-A computed) |
| `system_indicated_residual` | float | Residual score adjusted for control degradation (XL-A computed) |
| `coverage_computed_at` | datetime | When XL-A last ran the coverage calculation |

**Appetite fields:**

| Field | Type | Description |
|---|---|---|
| `risk_appetite` | float | Acceptable risk score for this specific risk |
| `risk_tolerance` | float | Maximum tolerable score before escalation |

### 2.2 Risk Scoring

The scoring model uses a standard 5×5 likelihood-impact matrix. Scores are computed as:

```
score = likelihood × impact
```

Zone boundaries applied throughout the module:

| Zone | Score Range | Colour |
|---|---|---|
| Low | 1–5 | Green |
| Medium | 6–11 | Yellow |
| High | 12–19 | Amber |
| Critical | 20–25 | Red |

**Inherent score** reflects the risk if no controls exist. **Residual score** reflects the risk after controls are in place, as assessed by the risk owner or assessment team. The **system-indicated residual** (XL-A) adjusts the assessor's residual score upward when linked controls are found to be degraded or failed — providing an independent check that the assumed control effectiveness is warranted.

The system never silently overwrites the assessor's `residual_score`. The XL-A output is always stored in separate read-only fields (`control_coverage`, `system_indicated_residual`, `coverage_computed_at`) so the auditor-owned residual remains unmodified.

### 2.3 Creating a Risk

**Step 1.** Gather the risk information: title, category, responsible org unit, risk owner, inherent scores, and initial review schedule.

**Step 2.** Call `POST /api/rm/risks`.

**Request:**

```json
POST /api/rm/risks
Authorization: Bearer <token>

{
  "title": "Unauthorised Access to Financial Reporting Systems",
  "description": "Risk that users gain access to financial modules beyond their required job functions, enabling manipulation of financial statements.",
  "description_ar": "خطر حصول المستخدمين على صلاحيات تتجاوز متطلبات وظائفهم في الأنظمة المالية",
  "category": "it_cyber",
  "org_unit_id": 12,
  "risk_owner_id": "USR-0042",
  "risk_owner_name": "Ahmed Al-Rashid",
  "inherent_likelihood": 4,
  "inherent_impact": 5,
  "residual_likelihood": 2,
  "residual_impact": 4,
  "risk_appetite": 8,
  "risk_tolerance": 15,
  "review_frequency": "quarterly",
  "next_review_date": "2026-12-01T00:00:00",
  "related_control_ids": ["CTRL-001", "CTRL-008"]
}
```

**Response (HTTP 201):**

```json
{
  "risk_id": "RISK_a3f7b2c81d04",
  "tenant_id": "acme_corp",
  "title": "Unauthorised Access to Financial Reporting Systems",
  "description": "Risk that users gain access to financial modules...",
  "description_ar": "خطر حصول المستخدمين على صلاحيات تتجاوز متطلبات وظائفهم...",
  "category": "it_cyber",
  "org_unit_id": 12,
  "risk_owner_id": "USR-0042",
  "risk_owner_name": "Ahmed Al-Rashid",
  "inherent_likelihood": 4,
  "inherent_impact": 5,
  "inherent_score": 20.0,
  "residual_likelihood": 2,
  "residual_impact": 4,
  "residual_score": 8.0,
  "risk_appetite": 8.0,
  "risk_tolerance": 15.0,
  "status": "identified",
  "control_coverage": null,
  "system_indicated_residual": null,
  "coverage_computed_at": null,
  "next_review_date": "2026-12-01T00:00:00",
  "review_frequency": "quarterly",
  "related_control_ids": ["CTRL-001", "CTRL-008"],
  "related_finding_ids": [],
  "is_active": true,
  "created_at": "2026-09-06T08:00:00"
}
```

**Step 3.** Once the risk is created, trigger the XL-A coverage computation (see Section 2.7) to populate the control-coverage fields.

### 2.4 Updating Risks

Risks are updated via `PUT /api/rm/risks/{risk_id}`. Only the fields included in the request body are modified — omitted fields remain unchanged.

When `inherent_likelihood` and `inherent_impact` are both provided, `inherent_score` is **not** automatically recomputed by the PUT endpoint. The caller must either include the pre-computed `inherent_score` or accept that the stored score may be stale. Best practice is to always send all three fields together when updating scoring dimensions.

When `residual_likelihood` or `residual_impact` are updated, the `system_indicated_residual` field (XL-A) becomes stale. Call `POST /api/rm/risks/{risk_id}/recompute-coverage` after any scoring update to refresh the XL-A output.

**Request example — updating residual scores after a control improvement:**

```json
PUT /api/rm/risks/RISK_a3f7b2c81d04

{
  "residual_likelihood": 1,
  "residual_impact": 3,
  "residual_score": 3.0
}
```

### 2.5 Risk Status Lifecycle

```
identified
    |
    v
assessed      <-- after first assessment is created
    |
    v
mitigated     <-- after a response plan reaches 'completed'
    |     \
    v      v
accepted   closed
```

| Status | Meaning |
|---|---|
| `identified` | Risk has been logged but not yet formally assessed |
| `assessed` | At least one assessment record exists; inherent/residual scores are set |
| `mitigated` | A response plan has been executed and verified effective |
| `accepted` | Board or risk committee has formally accepted the residual risk |
| `closed` | Risk is no longer active (expired, merged, or superseded) |

Status transitions are manual — the system automatically advances status to `assessed` when an assessment is created (POST /risks/{id}/assessments), but all other transitions require an explicit `status` field in a PUT request.

### 2.6 Linking to Controls and Findings

Two JSON array fields on each risk store cross-module references:

**`related_control_ids`** — list of ProcessControl `control_id` strings. These are the controls the organisation relies on to reduce the likelihood or impact of this risk. The XL-A coverage computation (Section 2.7) reads this array to inspect each control's health.

**`related_finding_ids`** — list of AuditFinding `finding_id` strings. When an internal audit uncovers an issue directly related to a risk, the finding is linked here. The AM module also links findings to risks via `POST /api/am/findings/{finding_id}/link-risk`.

To add a control link at risk-creation time, include its ID in `related_control_ids`. To add it later:

```json
PUT /api/rm/risks/RISK_a3f7b2c81d04

{
  "related_control_ids": ["CTRL-001", "CTRL-008", "CTRL-022"]
}
```

### 2.7 Control Coverage Signal (XL-A)

The XL-A feedback loop answers the question: *"Given the current health of the controls we rely on, is our assumed residual risk position still valid?"*

**Triggering recomputation:**

```
POST /api/rm/risks/{risk_id}/recompute-coverage
```

This endpoint has no request body. It reads the risk's `related_control_ids`, queries the Process Control module for each control's open deficiencies and latest test results, then calculates a coverage signal.

**Coverage signal values:**

| Signal | Condition | Degradation Factor |
|---|---|---|
| `effective` | All controls tested effective, no open deficiencies | × 1.0 |
| `degraded` | One or more significant deficiencies or partial test results | × 1.25 |
| `failed` | Any material weakness or ineffective test result | × 1.5 |
| `uncontrolled` | No controls linked, or all linked controls are inactive | Risk score = inherent score |

**How system_indicated_residual is computed:**

```
system_indicated_residual = min(residual_score × degradation_factor, inherent_score)
```

The result is capped at `inherent_score` — the system-indicated residual can never exceed the inherent risk.

**Response example:**

```json
{
  "risk_id": "RISK_a3f7b2c81d04",
  "control_coverage": "degraded",
  "system_indicated_residual": 10.0,
  "coverage_computed_at": "2026-09-06T09:15:00",
  "controls_evaluated": [
    {"control_id": "CTRL-001", "status": "effective"},
    {"control_id": "CTRL-008", "status": "significant_deficiency"}
  ]
}
```

This means the assessor's stated residual_score of 8.0 is being amplified by 1.25 to 10.0 because one control has a significant deficiency. The appetite check will flag this as a potential breach even though the assessor's score is nominally within appetite.

**API Endpoints — Risk Register:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/rm/risks` | Create risk |
| GET | `/api/rm/risks` | List risks (filters: category, status, org_unit_id, owner_id, search) |
| GET | `/api/rm/risks/{risk_id}` | Get single risk |
| PUT | `/api/rm/risks/{risk_id}` | Update risk |
| DELETE | `/api/rm/risks/{risk_id}` | Soft-delete risk |
| POST | `/api/rm/risks/{risk_id}/recompute-coverage` | Trigger XL-A coverage recomputation |

---

## 3. Risk Assessment (RM-10 to RM-12)

A risk assessment is a formal, point-in-time scoring event performed by an individual assessor or a team. Multiple assessments can exist for the same risk, building a historical scoring trail that feeds the trend reports.

### 3.1 Assessment Types

| Type | Value | When to Use |
|---|---|---|
| Periodic | `periodic` | Scheduled review at the risk's `review_frequency` cadence |
| Ad-hoc | `adhoc` | Triggered by a specific event — a control failure, an incident, or a regulatory change |
| Consensus | `consensus` | Multi-assessor exercise where scores are averaged across several reviewers |

### 3.2 Creating Assessments

An assessment captures the assessor's view of likelihood and impact at a specific moment, including written rationales that explain the scores. Monetary impact can also be recorded for financial risk quantification.

**Request:**

```json
POST /api/rm/risks/RISK_a3f7b2c81d04/assessments

{
  "assessment_type": "periodic",
  "assessor_id": "USR-0042",
  "assessor_name": "Ahmed Al-Rashid",
  "likelihood_score": 2,
  "impact_score": 4,
  "likelihood_rationale": "Two compensating controls are now operational. SoD rules in AC reduce the likelihood of unauthorised access being undetected.",
  "impact_rationale": "Financial misstatement impact remains high given reporting obligations under IFRS 17.",
  "monetary_impact": 450000.00,
  "currency": "SAR",
  "comments": "Quarterly assessment Q3 2026"
}
```

**Response (HTTP 201):**

```json
{
  "assessment_id": "ASMT_7f3a9b2e4c10",
  "risk_id": "RISK_a3f7b2c81d04",
  "assessor_id": "USR-0042",
  "assessor_name": "Ahmed Al-Rashid",
  "likelihood_score": 2,
  "impact_score": 4,
  "overall_score": 8.0,
  "assessment_type": "periodic",
  "likelihood_rationale": "Two compensating controls are now operational...",
  "impact_rationale": "Financial misstatement impact remains high...",
  "monetary_impact": 450000.00,
  "currency": "SAR",
  "status": "draft",
  "comments": "Quarterly assessment Q3 2026",
  "created_at": "2026-09-06T10:00:00"
}
```

When an assessment is created, the parent risk's `last_assessed_at` is updated and its `status` is automatically advanced to `assessed`.

### 3.3 Assessment Workflow

```
draft
  |
  v  [assessor submits]
submitted
  |
  v  [risk manager reviews]
reviewed
  |
  v  [CRO or committee approves]
approved
```

**Submit assessment:**

```
PUT /api/rm/assessments/{assessment_id}/submit
{}
```

Only assessments in `draft` status can be submitted. An HTTP 400 is returned if the assessment is already in a later status.

**Review assessment:**

```json
PUT /api/rm/assessments/{assessment_id}/review

{
  "reviewed_by": "USR-0100",
  "comments": "Scores validated against Q3 control testing results. Approved."
}
```

The reviewer's ID and timestamp are recorded, and status advances to `reviewed`.

### 3.4 Residual Score Update

When an assessment is approved, the risk owner should update the parent risk's `residual_likelihood`, `residual_impact`, and `residual_score` to reflect the approved assessment scores. This is done via `PUT /api/rm/risks/{risk_id}`:

```json
PUT /api/rm/risks/RISK_a3f7b2c81d04

{
  "residual_likelihood": 2,
  "residual_impact": 4,
  "residual_score": 8.0
}
```

The system does not automatically copy assessment scores to the risk to preserve auditor oversight — a reviewer must make a deliberate decision to accept the assessor's scores as the new residual position.

After updating residual scores, trigger `POST /api/rm/risks/{risk_id}/recompute-coverage` to refresh the XL-A system_indicated_residual.

### 3.5 Assessment Campaigns

An assessment campaign bulk-creates draft assessments for all active risks matching a filter. This is used for annual or quarterly bulk re-assessments.

**Request:**

```json
POST /api/rm/assessment-campaigns

{
  "category": "it_cyber",
  "assessor_id": "USR-0042",
  "assessor_name": "Ahmed Al-Rashid"
}
```

Omitting `category` creates assessments for all active risks in the tenant. Each generated assessment is initialised with the risk's current residual scores (falling back to inherent scores if residual is not set) and placed in `draft` status for the assessor to review and update.

**Response:**

```json
{
  "campaign_id": "CAMP_b8e21f093a7c",
  "assessments_created": 14,
  "assessment_ids": ["ASMT_...", "ASMT_...", "..."]
}
```

### 3.6 Multi-Assessor Consensus

For consensus assessments, multiple assessors independently submit assessments of type `consensus` against the same risk. The risk manager then averages the scores manually (or using the trend API) and records a final approved assessment that represents the consensus position. The system does not automatically average scores — the multi-assessor pattern is implemented by creating multiple individual assessment records and letting the reviewer synthesise them.

**API Endpoints — Assessments:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/rm/risks/{risk_id}/assessments` | Create assessment |
| GET | `/api/rm/risks/{risk_id}/assessments` | List assessments for a risk |
| PUT | `/api/rm/assessments/{assessment_id}/submit` | Submit for review |
| PUT | `/api/rm/assessments/{assessment_id}/review` | Review and advance |
| POST | `/api/rm/assessment-campaigns` | Run bulk assessment campaign |

---

## 4. Risk Appetite and Tolerance (RM-03)

Risk appetite defines how much risk the organisation is willing to accept in pursuit of its objectives. Risk tolerance is the maximum variation around appetite that is acceptable before escalation is required.

### 4.1 Setting Appetite

Appetite records are scoped to a `category` and optionally an `org_unit_id`. A record with `category: "all"` and no org unit serves as the organisation-wide default.

**Create or update appetite:**

```json
POST /api/rm/appetites

{
  "category": "it_cyber",
  "org_unit_id": null,
  "appetite_score": 8,
  "tolerance_score": 15,
  "description": "IT and cyber risks with residual score above 8 require CRO attention. Above 15 requires Board notification within 5 business days.",
  "approved_by": "USR-0010",
  "effective_from": "2026-01-01T00:00:00",
  "effective_to": "2026-12-31T23:59:59"
}
```

The endpoint performs an upsert: if an appetite record already exists for the same `category` and `org_unit_id` combination, it is updated in place. This avoids creating duplicate records during the annual appetite review cycle.

**Response (HTTP 201 or 200):**

```json
{
  "category": "it_cyber",
  "org_unit_id": null,
  "appetite_score": 8.0,
  "tolerance_score": 15.0,
  "description": "IT and cyber risks with residual score above 8...",
  "approved_by": "USR-0010",
  "approved_at": "2026-09-06T10:30:00",
  "effective_from": "2026-01-01T00:00:00",
  "effective_to": "2026-12-31T23:59:59"
}
```

### 4.2 Appetite vs Tolerance

| Concept | Score Range | Meaning |
|---|---|---|
| Within appetite | `residual_score <= appetite_score` | Acceptable — no action required |
| Approaching tolerance | `appetite_score < residual_score <= tolerance_score` | Appetite breached — risk owner action required |
| Tolerance breach | `residual_score > tolerance_score` | Tolerance breached — escalation to senior management or board required |

The appetite check uses a lookup hierarchy: the system first tries to find an appetite record matching the risk's specific `category`. If none exists, it falls back to the `category: "all"` record. If neither exists, appetite fields in the response are returned as `null`.

### 4.3 Breach Detection

Run an appetite check at any time:

```
GET /api/rm/risks/{risk_id}/appetite-check
```

**Response:**

```json
{
  "risk_id": "RISK_a3f7b2c81d04",
  "risk_title": "Unauthorised Access to Financial Reporting Systems",
  "residual_score": 8.0,
  "appetite_score": 8.0,
  "tolerance_score": 15.0,
  "appetite_breach": false,
  "tolerance_breach": false,
  "status": "within_appetite",

  "control_coverage": "degraded",
  "system_indicated_residual": 10.0,
  "coverage_computed_at": "2026-09-06T09:15:00",
  "indicated_appetite_breach": true,
  "indicated_tolerance_breach": false,
  "indicated_status": "appetite_breach"
}
```

The response contains two independent assessments:

1. **Assessor view** — based on `residual_score` set by the risk owner. In this example, 8.0 is exactly at the appetite threshold so no breach is flagged.
2. **System-indicated view (XL-A)** — based on `system_indicated_residual` of 10.0, which exceeds the appetite of 8.0. `indicated_appetite_breach: true` is an early-warning signal that the control degradation has eroded the assumed risk position.

`status` values: `within_appetite`, `appetite_breach`, `tolerance_breach`.
`indicated_status` values: `within_appetite`, `appetite_breach`, `tolerance_breach`, `unknown` (if coverage has never been computed).

### 4.4 System-Indicated Residual

The `system_indicated_residual` is populated by the XL-A recompute-coverage endpoint (Section 2.7). It is evaluated against appetite using the same thresholds as the assessor's score. This creates an independent signal that is particularly valuable when:

- A control has recently failed a test but the risk register has not yet been updated
- A new audit finding has been raised against a key control
- The risk committee wants to understand the "worst case" residual position given current control health

**API Endpoints — Appetite:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/rm/appetites` | Create or update appetite |
| GET | `/api/rm/appetites` | List appetite records (filters: category, org_unit_id) |
| GET | `/api/rm/risks/{risk_id}/appetite-check` | Run appetite breach check for a risk |

---

## 5. Key Risk Indicators — KRI (RM-13)

Key Risk Indicators are quantitative metrics that signal changes in a risk's exposure before a risk event occurs. A KRI measures something observable and correlated with the risk — for example, the number of failed login attempts (correlated with cyber risk) or the number of overdue access recertifications (correlated with access control risk).

### 5.1 KRI Structure

| Field | Type | Description |
|---|---|---|
| `kri_id` | string | Unique identifier |
| `name` | string | KRI name (e.g. "Failed Authentication Attempts - Monthly") |
| `description` | text | What the KRI measures and why it matters |
| `risk_id` | integer | FK to the `enterprise_risks` table (optional — KRIs can be standalone) |
| `data_source` | string | Where measurements come from: `manual`, `siem`, `ac`, `hris`, `erp` |
| `unit_of_measure` | string | e.g. `count`, `percentage`, `days`, `USD` |
| `frequency` | string | `daily`, `weekly`, `monthly`, `quarterly` |
| `threshold_green` | float | Upper boundary of the normal (green) zone |
| `threshold_amber` | float | Upper boundary of the warning (amber) zone |
| `threshold_red` | float | Lower boundary of the breach (red) zone |
| `current_value` | float | Most recently recorded measurement |
| `last_measured_at` | datetime | When the current value was recorded |
| `status` | enum | Current traffic-light: `normal`, `warning`, `breach` |
| `owner_id` | string | Person responsible for the KRI |

Threshold design: `threshold_green < threshold_amber < threshold_red`. A value below `threshold_green` is normal. A value between `threshold_green` and `threshold_amber` (inclusive) triggers a warning. A value at or above `threshold_amber` (exclusive — i.e. `>= threshold_red`) triggers breach. Values between `threshold_amber` and `threshold_red` are in the warning zone.

More precisely: `normal` if `current_value <= threshold_green`; `warning` if `threshold_green < current_value < threshold_red`; `breach` if `current_value >= threshold_red`.

### 5.2 Creating KRIs

**Request:**

```json
POST /api/rm/kris

{
  "name": "Privileged Account Usage Outside Business Hours",
  "description": "Count of privileged account logons between 18:00 and 07:00 on weekdays, and all day on weekends. Elevated activity suggests either policy violation or compromised credentials.",
  "risk_id": 1,
  "data_source": "siem",
  "unit_of_measure": "count",
  "frequency": "weekly",
  "threshold_green": 5,
  "threshold_amber": 15,
  "threshold_red": 25,
  "owner_id": "USR-0042"
}
```

**Response (HTTP 201):**

```json
{
  "kri_id": "KRI_f9a03b1e72c8",
  "name": "Privileged Account Usage Outside Business Hours",
  "description": "Count of privileged account logons between 18:00 and 07:00...",
  "risk_id": 1,
  "data_source": "siem",
  "unit_of_measure": "count",
  "frequency": "weekly",
  "threshold_green": 5.0,
  "threshold_amber": 15.0,
  "threshold_red": 25.0,
  "current_value": null,
  "last_measured_at": null,
  "status": "normal",
  "owner_id": "USR-0042",
  "is_active": true
}
```

### 5.3 Recording Measurements

Measurements can be recorded manually or via automated feeds from connected systems.

**Manual measurement:**

```json
POST /api/rm/kris/KRI_f9a03b1e72c8/measurements

{
  "value": 18,
  "measured_by": "USR-0042",
  "source": "manual",
  "notes": "Week of 2026-09-01. Includes 3 legitimate after-hours incidents approved via firefighter request FF-0221."
}
```

**Response:**

```json
{
  "measurement": {
    "kri_id": "KRI_f9a03b1e72c8",
    "value": 18.0,
    "measured_at": "2026-09-06T10:45:00",
    "measured_by": "USR-0042",
    "source": "manual",
    "notes": "Week of 2026-09-01..."
  },
  "kri_status": "warning"
}
```

After each measurement, `current_value`, `last_measured_at`, and `status` on the KRI record are updated atomically.

**Automated feeds:** Automated integrations (SIEM, AC module, HRIS) post measurements by calling the same endpoint with `source` set to the system name. The GovernexPlus scheduler can be configured to call this endpoint on the KRI's `frequency` schedule.

### 5.4 Traffic-Light Status Logic

Status is recomputed on every measurement using the following logic (implemented in `api/routers/risk_mgmt.py → _kri_status()`):

```
if current_value is None:
    status = "normal"          # no data yet — assume normal
elif current_value >= threshold_red:
    status = "breach"
elif current_value >= threshold_amber:
    status = "warning"
else:
    status = "normal"
```

This means values above `threshold_amber` (the amber threshold) but below `threshold_red` are classified as `warning`. Values at or above `threshold_red` are classified as `breach`. This is intentional: the amber zone is the pre-breach warning zone.

### 5.5 KRI Dashboard

The KRI dashboard provides a grouped traffic-light summary across all active KRIs.

```
GET /api/rm/kris/dashboard
```

**Response:**

```json
{
  "total_kris": 12,
  "normal": 8,
  "warning": 3,
  "breach": 1,
  "kris": [
    {
      "kri_id": "KRI_f9a03b1e72c8",
      "name": "Privileged Account Usage Outside Business Hours",
      "current_value": 18.0,
      "threshold_amber": 15.0,
      "threshold_red": 25.0,
      "status": "warning",
      "current_status": "warning",
      "last_measured_at": "2026-09-06T10:45:00"
    },
    ...
  ]
}
```

Each KRI in the response includes a `current_status` field that re-evaluates the status at query time based on `current_value` against thresholds. This ensures the dashboard reflects the most current position even if the stored `status` field is slightly behind.

**Measurement history:**

```
GET /api/rm/kris/{kri_id}/history
```

Returns all measurement records in reverse chronological order, enabling sparkline charts in the dashboard.

### 5.6 Breach Alerts and Notifications

When a measurement tips a KRI into `breach` status, the notification delivery system sends alerts to:

1. The KRI owner (`owner_id`)
2. The risk owner of the linked risk (if `risk_id` is set)
3. Any subscribers configured in the notification rules for `kri_breach` events

Notification delivery is handled by the GovernexPlus notification engine (see the Notifications module). Risk managers should configure notification rules for `kri_breach` events during system setup.

**API Endpoints — KRIs:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/rm/kris` | Create KRI |
| GET | `/api/rm/kris/dashboard` | Traffic-light dashboard |
| POST | `/api/rm/kris/{kri_id}/measurements` | Record measurement |
| GET | `/api/rm/kris/{kri_id}/history` | Measurement history |

---

## 6. Risk Response Plans (RM-20)

A risk response plan documents the concrete steps the organisation will take to address a risk. Every risk should have at least one response plan that aligns with the chosen response strategy.

### 6.1 Response Types

| Type | Value | When to Use |
|---|---|---|
| Accept | `accept` | Risk is within appetite; no additional action taken; formally acknowledged |
| Mitigate | `mitigate` | Controls or process improvements are implemented to reduce likelihood or impact |
| Transfer | `transfer` | Risk is shifted to a third party (insurance, contractual indemnity, outsourcing) |
| Avoid | `avoid` | The activity that creates the risk is discontinued entirely |

### 6.2 Creating Response Plans

A response plan consists of a high-level description, an owner, a due date, and a list of specific action items. Action items are stored as a JSON array within the response record.

**Request:**

```json
POST /api/rm/risks/RISK_a3f7b2c81d04/responses

{
  "response_type": "mitigate",
  "description": "Implement enhanced SoD controls for financial reporting transactions and deploy automated access review for all finance role assignments.",
  "owner_id": "USR-0042",
  "owner_name": "Ahmed Al-Rashid",
  "due_date": "2026-12-31T23:59:59",
  "actions": [
    {
      "seq": 1,
      "title": "Configure SoD rules for T-codes FB01, FB60, F110 in AC module",
      "due_date": "2026-10-15",
      "owner": "USR-0055",
      "status": "not_started"
    },
    {
      "seq": 2,
      "title": "Run access recertification campaign for all users with F-module roles",
      "due_date": "2026-11-30",
      "owner": "USR-0042",
      "status": "not_started"
    },
    {
      "seq": 3,
      "title": "Deploy automated quarterly access review for finance roles",
      "due_date": "2026-12-31",
      "owner": "USR-0060",
      "status": "not_started"
    }
  ]
}
```

**Response (HTTP 201):**

```json
{
  "response_id": "RESP_c4d71a903e2f",
  "risk_id": 1,
  "response_type": "mitigate",
  "description": "Implement enhanced SoD controls...",
  "owner_id": "USR-0042",
  "owner_name": "Ahmed Al-Rashid",
  "due_date": "2026-12-31T23:59:59",
  "status": "planned",
  "effectiveness_rating": null,
  "completed_at": null,
  "actions": [ ... ]
}
```

### 6.3 Status Tracking

Response plan status is managed via a dedicated endpoint:

```json
PUT /api/rm/responses/{response_id}/status

{
  "status": "in_progress"
}
```

Valid transitions:

```
planned --> in_progress --> completed
                   |
                   v
                overdue   (auto-set by scheduler when due_date passes)
```

When `status` is set to `completed`, the `completed_at` timestamp is automatically recorded.

Individual action items within the `actions` JSON array are updated by including the full modified array in the status update or a PUT to the response record. The action item statuses are stored as embedded JSON and are not enforced by the system — they serve as a structured checklist for the response owner.

### 6.4 Effectiveness Rating

After a mitigate or transfer response is completed, the risk owner should record an effectiveness rating to indicate whether the response actually reduced the risk to the expected level:

```json
PUT /api/rm/responses/RESP_c4d71a903e2f/status

{
  "status": "completed",
  "effectiveness_rating": 4
}
```

`effectiveness_rating` is an integer on a 1–5 scale where 5 = fully effective and 1 = ineffective. This feeds into the risk trend analysis and KRI design for future cycles.

**API Endpoints — Responses:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/rm/risks/{risk_id}/responses` | Create response plan |
| GET | `/api/rm/risks/{risk_id}/responses` | List response plans for a risk |
| PUT | `/api/rm/responses/{response_id}/status` | Update status and effectiveness |

---

## 7. Incidents and Loss Events (RM-22)

The incident module records risk events that have materialised — actual losses, near-misses, or operational failures. Incidents provide empirical evidence for likelihood calibration and contribute to the historical loss database required by frameworks like Basel III and Solvency II.

### 7.1 Incident Structure

| Field | Type | Description |
|---|---|---|
| `incident_id` | string | Unique identifier |
| `title` | string | Concise incident name |
| `description` | text | Full incident description |
| `severity` | enum | `low`, `medium`, `high`, `critical` |
| `financial_impact` | float | Estimated monetary loss |
| `currency` | string | ISO 4217 currency code (default `USD`) |
| `occurred_at` | datetime | When the incident occurred |
| `detected_at` | datetime | When the incident was detected (set automatically at creation) |
| `reported_by` | string | User ID of the person reporting |
| `root_cause` | text | Root cause analysis narrative |
| `corrective_actions` | JSON array | Corrective actions being taken |
| `status` | enum | Lifecycle status |
| `risk_id` | integer | FK to linked enterprise risk (optional) |

### 7.2 Reporting an Incident

**Request:**

```json
POST /api/rm/incidents

{
  "title": "Unauthorised AP Vendor Master Change - Production",
  "description": "A user with both AP change and payment approval access modified vendor bank account details for supplier #VP-0441 and subsequently approved a payment. The modification was detected during the monthly reconciliation review.",
  "severity": "high",
  "financial_impact": 125000.00,
  "currency": "SAR",
  "occurred_at": "2026-08-28T14:30:00",
  "reported_by": "USR-0099",
  "corrective_actions": [
    "Immediately revoked dual-role access for the affected user",
    "Initiated vendor bank account re-verification process",
    "Payment placed on hold pending investigation"
  ]
}
```

**Response (HTTP 201):**

```json
{
  "incident_id": "INC_d8e7a1c4f930",
  "title": "Unauthorised AP Vendor Master Change - Production",
  "severity": "high",
  "financial_impact": 125000.0,
  "currency": "SAR",
  "occurred_at": "2026-08-28T14:30:00",
  "detected_at": "2026-09-06T11:00:00",
  "reported_by": "USR-0099",
  "status": "reported",
  "root_cause": null,
  "corrective_actions": ["Immediately revoked dual-role access...", "..."],
  "risk_id": null
}
```

### 7.3 Linking to Risks

After reporting, link the incident to the relevant risk in the register. This enables likelihood recalibration — if several incidents materialise against the same risk, the next periodic assessment should reflect an upward revision to the likelihood score.

```json
POST /api/rm/incidents/INC_d8e7a1c4f930/link-risk

{
  "risk_id": "RISK_a3f7b2c81d04"
}
```

**Response:**

```json
{
  "incident_id": "INC_d8e7a1c4f930",
  "linked_risk_id": "RISK_a3f7b2c81d04",
  "success": true
}
```

The system does not automatically adjust the risk's likelihood score — that requires a deliberate ad-hoc assessment (Section 3). However, the link creates the data trail needed for the CRO to see which risks are materialising most frequently when reviewing the register.

### 7.4 Root Cause Analysis

Root cause is recorded as free text in the `root_cause` field. Update it as the investigation progresses:

```json
PUT /api/rm/incidents/INC_d8e7a1c4f930

{
  "root_cause": "Inadequate SoD controls in the Accounts Payable module. The user was granted vendor master change access as part of a temporary project role that was never revoked after project completion (JML failure). No compensating control was in place to detect the dual-role combination.",
  "status": "investigating"
}
```

### 7.5 Corrective Actions

The `corrective_actions` array is updated by providing the full updated array in a PUT request. Each element can be a string (simple action description) or a structured object with owner and due date:

```json
PUT /api/rm/incidents/INC_d8e7a1c4f930

{
  "corrective_actions": [
    {
      "action": "Revoke dual-role access",
      "owner": "USR-0042",
      "due_date": "2026-09-06",
      "status": "completed"
    },
    {
      "action": "Implement SoD rule for AP change + AP payment combination",
      "owner": "USR-0055",
      "due_date": "2026-10-01",
      "status": "in_progress"
    },
    {
      "action": "Run JML audit for all project-granted roles older than 90 days",
      "owner": "USR-0060",
      "due_date": "2026-10-15",
      "status": "not_started"
    }
  ]
}
```

### 7.6 Status Lifecycle

```
reported --> investigating --> resolved --> closed
```

| Status | Meaning |
|---|---|
| `reported` | Initial submission; investigation not yet started |
| `investigating` | Active investigation underway; root cause being determined |
| `resolved` | Root cause identified; corrective actions completed |
| `closed` | Incident formally closed; all follow-up actions verified |

When status is set to `resolved`, `resolved_at` is automatically stamped.

**API Endpoints — Incidents:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/rm/incidents` | Report incident |
| GET | `/api/rm/incidents` | List incidents (filters: status, severity) |
| PUT | `/api/rm/incidents/{incident_id}` | Update incident |
| POST | `/api/rm/incidents/{incident_id}/link-risk` | Link incident to risk |

---

## 8. Risk Review and Attestation (RM-23)

Every risk in the register must be periodically reviewed to confirm that the scoring, ownership, and response plans remain current. The review attestation mechanism creates a formal paper trail of who reviewed a risk and when.

### 8.1 Review Frequency Setup

Review frequency is set per-risk in the `review_frequency` field:

| Value | Review Interval |
|---|---|
| `monthly` | 30 days |
| `quarterly` | 90 days |
| `semi_annual` | 180 days |
| `annual` | 365 days |

High-criticality risks (score 20–25) should be reviewed monthly. High-risk (12–19) risks quarterly. Medium (6–11) and low (1–5) risks semi-annually or annually respectively. The organisation's risk policy should specify minimum review frequencies by risk zone.

### 8.2 Overdue Review Detection

Run the overdue review report at any time:

```
GET /api/rm/overdue-reviews
```

**Response:**

```json
{
  "total_overdue": 3,
  "risks": [
    {
      "risk_id": "RISK_b7c43a1d8e90",
      "title": "Regulatory Capital Calculation Error",
      "status": "assessed",
      "next_review_date": "2026-08-01T00:00:00",
      "risk_owner_name": "Fatima Al-Zahra",
      "residual_score": 12.0,
      "days_overdue": 36
    },
    ...
  ]
}
```

The scheduler runs this check nightly and sends reminder notifications to risk owners for risks that are 7, 14, and 30 days overdue. At 30 days overdue, the notification is escalated to the risk owner's manager.

### 8.3 Review Attestation

When a risk owner completes their review (confirms scores are current, response plans are progressing, and ownership is correct), they record an attestation:

```json
POST /api/rm/risks/RISK_b7c43a1d8e90/review-attestation

{
  "attested_by": "USR-0075",
  "notes": "Scores confirmed as current. Control CTRL-012 has been upgraded to annual testing from quarterly — residual scores will be reassessed after next test completion."
}
```

**Response:**

```json
{
  "risk_id": "RISK_b7c43a1d8e90",
  "attested_by": "USR-0075",
  "attested_at": "2026-09-06T12:00:00",
  "next_review_date": "2026-12-05T12:00:00"
}
```

The attestation:
1. Updates `last_assessed_at` to now
2. Computes the next `next_review_date` using the risk's `review_frequency` (90 days for quarterly)
3. Updates `risk_owner_id` to the `attested_by` user (confirming ownership has not changed, or transferring it if a different user attests)

### 8.4 Escalation for Overdue Reviews

The GovernexPlus scheduler runs a nightly escalation job that:

1. Queries `GET /api/rm/overdue-reviews`
2. For risks 1–6 days overdue: sends a reminder to the risk owner
3. For risks 7–13 days overdue: sends a second reminder and copies the risk manager
4. For risks 14–29 days overdue: escalates to the risk owner's manager
5. For risks 30+ days overdue: flags the risk in the dashboard with a red overdue badge and notifies the Chief Risk Officer

Escalation rules are configurable in the notification delivery module settings.

---

## 9. RM Reporting (RM-12, RM-30, RM-31)

### 9.1 Risk Heatmap

The risk heatmap provides a visual representation of the entire risk portfolio on a 5×5 likelihood-impact grid.

```
GET /api/rm/heatmap
```

The endpoint returns all 25 cells of the 5×5 grid, each with:
- `likelihood` (1–5)
- `impact` (1–5)
- `score` (likelihood × impact)
- `count` (number of risks in this cell)
- `zone` (low/medium/high/critical)

Risks are plotted using their **residual** scores by default. When residual scores are not set, inherent scores are used as a fallback.

**Response (abbreviated):**

```json
{
  "total_risks": 42,
  "unscored": 3,
  "heatmap": [
    {"likelihood": 1, "impact": 1, "score": 1, "count": 5, "zone": "low"},
    {"likelihood": 1, "impact": 2, "score": 2, "count": 3, "zone": "low"},
    ...
    {"likelihood": 4, "impact": 5, "score": 20, "count": 2, "zone": "critical"},
    {"likelihood": 5, "impact": 5, "score": 25, "count": 0, "zone": "critical"}
  ]
}
```

**ASCII representation of a 5×5 heatmap:**

```
Impact -->
          1     2     3     4     5
        +-----+-----+-----+-----+-----+
      5 | MED | MED | HIGH| CRIT| CRIT|
        +-----+-----+-----+-----+-----+
      4 | LOW | MED | HIGH| HIGH| CRIT|
L     3 | LOW | MED | MED | HIGH| HIGH|
I       +-----+-----+-----+-----+-----+
K     2 | LOW | LOW | MED | MED | HIGH|
E       +-----+-----+-----+-----+-----+
L     1 | LOW | LOW | LOW | LOW | MED |
I       +-----+-----+-----+-----+-----+
H
O
O
D
```

Cell drill-down: `GET /api/rm/risks?inherent_likelihood=4&inherent_impact=5` (filter by specific cell coordinates using the list endpoint's query parameters).

### 9.2 Risk Trends

```
GET /api/rm/trends?period_months=12
```

Returns the average risk assessment score per month over the requested period, computed from all assessment records with `created_at` within the window.

**Response:**

```json
{
  "period_months": 12,
  "trend": [
    {"month": "2025-09", "avg_score": 11.4, "count": 8},
    {"month": "2025-10", "avg_score": 10.2, "count": 12},
    {"month": "2025-11", "avg_score": 9.8, "count": 9},
    ...
    {"month": "2026-08", "avg_score": 8.6, "count": 14}
  ]
}
```

A declining average score over time indicates the risk management programme is effectively reducing residual risk. An increasing trend signals deterioration and should trigger a management review.

### 9.3 Top Risks

```
GET /api/rm/top-risks?limit=10
```

Returns the top N active risks ordered by `residual_score` descending (with null residual scores ranked last). This drives the "top risks" section of board risk reports.

### 9.4 Risk-Control Coverage

```
GET /api/rm/risk-control-coverage
```

**Response:**

```json
{
  "total_risks": 42,
  "covered": 35,
  "uncovered": 7,
  "coverage_pct": 83.3
}
```

Risks with an empty `related_control_ids` array are considered uncovered. A coverage percentage below 80% should be flagged in the risk committee report. Individual uncovered risks can be retrieved via `GET /api/rm/risks` filtered by any risks you identify manually, or by filtering for risks whose `related_control_ids` is empty (this can be checked in the response data).

### 9.5 Overdue Reviews Report

```
GET /api/rm/overdue-reviews
```

Returns all risks where `next_review_date` is in the past. See Section 8.2 for details.

### 9.6 Board/Committee Risk Reports

The following combination of endpoints provides everything needed for a board-level risk report:

1. `GET /api/rm/top-risks?limit=15` — top 15 risks by residual score
2. `GET /api/rm/heatmap` — portfolio heatmap
3. `GET /api/rm/trends?period_months=12` — 12-month trend
4. `GET /api/rm/risk-control-coverage` — coverage metrics
5. `GET /api/rm/overdue-reviews` — overdue review summary
6. `GET /api/rm/kris/dashboard` — KRI traffic-light summary
7. `GET /api/rm/incidents?status=reported&status=investigating` — open incidents

The GovernexPlus AI assistant (XL-C) can narrate these data points into a board-ready risk summary in plain English or Arabic. Call `POST /api/ai/grc-assist` with `{"module": "rm", "action": "board_summary"}`.

### 9.7 PPTX/PDF Export

Risk reports can be exported via the reporting engine:

```json
POST /api/reports/export

{
  "report_type": "risk_summary",
  "format": "pptx",
  "fiscal_year": 2026,
  "include_heatmap": true,
  "include_top_risks": true,
  "include_kri_dashboard": true
}
```

The export engine generates a formatted PowerPoint or PDF using the same data as the API endpoints. Templates are configurable per tenant.

---

## 10. Integration with Other Modules

### RM → PC (Risk Management to Process Control)

- Risks are linked to controls via `related_control_ids` on the `EnterpriseRisk` record
- The risk-control matrix shows which controls address which risks
- `POST /api/rm/risks/{risk_id}/recompute-coverage` (XL-A) reads control health from the PC module to compute the system-indicated residual

### RM → AM (Risk Management to Audit Management)

- Risk scores from RM feed the audit universe risk scoring formula: `composite = RM 40% + PC 35% + AC 25%`
- High-risk entities (those whose composite score is driven by elevated RM scores) are prioritised in the annual audit plan
- This feed is the XI-04 risk-based planning integration

### PC → RM (Process Control to Risk Management — XL-A)

- When a control fails a test or accumulates deficiencies, the PC module can trigger `recompute-coverage` on all risks that reference that control
- This updates `control_coverage` and `system_indicated_residual` without touching the assessor's residual score
- The appetite check then reflects the updated system-indicated position

### AM → RM (Audit Management to Risk Management — XI-03)

- Audit findings are linked to risks via `POST /api/am/findings/{finding_id}/link-risk`
- The linked finding IDs are stored in `related_finding_ids` on the risk
- A finding linked to a risk signals that the risk has materialised in the audit context and should be reviewed by the risk owner

### AC → RM (Access Control to Risk Management)

- SoD violation counts from the Access Control module are one input to the KRI framework
- For example, a KRI measuring "open SoD violations in FI module" can be fed directly from `GET /api/ara/violations`
- Elevated violation counts should trigger an ad-hoc assessment of the related IT/cyber or compliance risks

---

## 11. Configuration Reference

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `RM_DEFAULT_REVIEW_FREQUENCY` | `quarterly` | Default review frequency for new risks |
| `RM_HEATMAP_CRITICAL_THRESHOLD` | `20` | Score above which a cell is classified as critical |
| `RM_HEATMAP_HIGH_THRESHOLD` | `12` | Score above which a cell is classified as high |
| `RM_HEATMAP_MEDIUM_THRESHOLD` | `6` | Score above which a cell is classified as medium |
| `RM_OVERDUE_ESCALATION_DAYS_1` | `7` | Days overdue before first escalation |
| `RM_OVERDUE_ESCALATION_DAYS_2` | `14` | Days overdue before manager notification |
| `RM_OVERDUE_ESCALATION_DAYS_3` | `30` | Days overdue before CRO notification |

### Complete RM API Endpoint Table

| Method | Path | Description |
|---|---|---|
| POST | `/api/rm/risks` | Create risk |
| GET | `/api/rm/risks` | List risks |
| GET | `/api/rm/risks/{risk_id}` | Get risk |
| PUT | `/api/rm/risks/{risk_id}` | Update risk |
| DELETE | `/api/rm/risks/{risk_id}` | Soft-delete risk |
| POST | `/api/rm/risks/{risk_id}/recompute-coverage` | XL-A coverage recompute |
| POST | `/api/rm/risks/{risk_id}/assessments` | Create assessment |
| GET | `/api/rm/risks/{risk_id}/assessments` | List assessments |
| PUT | `/api/rm/assessments/{assessment_id}/submit` | Submit assessment |
| PUT | `/api/rm/assessments/{assessment_id}/review` | Review assessment |
| POST | `/api/rm/assessment-campaigns` | Run campaign |
| POST | `/api/rm/appetites` | Set appetite |
| GET | `/api/rm/appetites` | List appetites |
| GET | `/api/rm/risks/{risk_id}/appetite-check` | Check appetite breach |
| POST | `/api/rm/kris` | Create KRI |
| GET | `/api/rm/kris/dashboard` | KRI dashboard |
| POST | `/api/rm/kris/{kri_id}/measurements` | Record measurement |
| GET | `/api/rm/kris/{kri_id}/history` | KRI history |
| POST | `/api/rm/risks/{risk_id}/responses` | Create response plan |
| GET | `/api/rm/risks/{risk_id}/responses` | List responses |
| PUT | `/api/rm/responses/{response_id}/status` | Update response status |
| POST | `/api/rm/incidents` | Report incident |
| GET | `/api/rm/incidents` | List incidents |
| PUT | `/api/rm/incidents/{incident_id}` | Update incident |
| POST | `/api/rm/incidents/{incident_id}/link-risk` | Link incident to risk |
| GET | `/api/rm/overdue-reviews` | Overdue review report |
| POST | `/api/rm/risks/{risk_id}/review-attestation` | Record attestation |
| GET | `/api/rm/heatmap` | Risk heatmap |
| GET | `/api/rm/trends` | Risk score trends |
| GET | `/api/rm/top-risks` | Top risks by score |
| GET | `/api/rm/risk-control-coverage` | Control coverage report |

### Risk Scoring Configuration

The 5×5 scoring matrix is fixed: `score = likelihood × impact`. Zone thresholds are configurable via environment variables. Category values are fixed at the database level as an enum and cannot be changed without a schema migration:

```
strategic | operational | financial | compliance | it_cyber | reputational
```

### KRI Threshold Configuration

KRI thresholds are set per-KRI record and are not global. There is no system-wide KRI threshold configuration. Each KRI's `threshold_green`, `threshold_amber`, and `threshold_red` must be set individually based on the unit of measure and the specific metric being tracked.

Recommended practice: set thresholds during KRI creation based on:
1. Historical baseline data (what is "normal" for this metric)
2. The point at which action is required (amber threshold)
3. The point at which the risk owner must immediately escalate (red threshold)

---

*Last updated: 2026-09-06 | GovernexPlus RM Module | Requirements RM-01 through RM-31, XL-A*
