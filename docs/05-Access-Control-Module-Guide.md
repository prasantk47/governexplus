# GovernexPlus — Access Control (AC) Module Guide

**SoD Analysis, Access Requests, Emergency Access, Certification, Role Engineering**

> Version: 2026-09 | Platform: GovernexPlus 1.x | Replaces: SAP GRC AC 12.0

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [SoD Rule Library (AC-01 to AC-06)](#2-sod-rule-library)
3. [Risk Intelligence Engine — ARA (AC-10 to AC-18)](#3-risk-intelligence-engine-ara)
4. [Mitigation Controls (AC-13)](#4-mitigation-controls)
5. [Access Lifecycle Manager — ARM (AC-20 to AC-24)](#5-access-lifecycle-manager-arm)
6. [Emergency Access — Firefighter/Privileged Access Governor (AC-30 to AC-33)](#6-emergency-access-firefighterprivileged-access-governor)
7. [Access Certification — UAR (AC-40 to AC-43)](#7-access-certification-uar)
8. [Role Engineering — Role Design Studio (AC-50 to AC-52)](#8-role-engineering-role-design-studio)
9. [Continuous Monitoring](#9-continuous-monitoring)
10. [Reports and Dashboards](#10-reports-and-dashboards)
11. [Configuration Reference](#11-configuration-reference)

---

## 1. Module Overview

### 1.1 What the AC Module Covers

The Access Control (AC) module is the core governance engine of GovernexPlus. It is the direct replacement for SAP GRC Access Control 12.0, engineered to exceed SAP GRC's capabilities at a fraction of the cost with a modern, cloud-native architecture.

The AC module answers two fundamental questions that every audit committee, CFO, and CISO needs answered:

- **Who has access to what, and does it create fraud risk?**
- **How do we issue, review, and revoke access in a controlled, auditable way?**

SAP GRC AC asks "Is there a risk?" GovernexPlus AC asks "How risky is it, why, right now — and exactly what should we do about it?"

### 1.2 Sub-Modules

| Sub-Module | Abbreviation | SAP GRC Equivalent | Description |
|---|---|---|---|
| Risk Intelligence Engine | ARA | GRC-ARA | SoD conflict detection, sensitive access, risk scoring |
| Access Lifecycle Manager | ARM | GRC-ARM | Self-service request portal with inline risk preview |
| Privileged Access Governor | EAM | GRC-EAM | Firefighter IDs, session logging, controller review |
| User Access Review | UAR | GRC-UAR | Periodic certification campaigns with revocation |
| Role Design Studio | BRM | GRC-BRM | Role design, mining, lifecycle management |

### 1.3 Key Statistics

| Metric | Value |
|---|---|
| Built-in SoD rules | 121 in `SoDRulesetLibrary` (128 after bridge merges) |
| Business functions catalogued | 55+ across all processes |
| Business processes covered | FI, MM, SD, HR, BA, TR, AA, WM, QM, PM, PS, XP |
| SOX-relevant rules | 74 |
| GDPR-relevant rules | 6 |
| Cross-process (XP) critical rules | 15 |
| API endpoints | 80+ across all AC sub-modules |
| Dual rule engines | `core/rules/engine.py` + `core/ara/rules.py` (parallel, idempotent) |

### 1.4 Architecture Position

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React/TS)                  │
│  Risk Dashboard │ Request Portal │ Cert Campaigns │ Privileged Access Governor  │
└────────────────────────────┬────────────────────────────┘
                             │ REST API (JWT auth)
┌────────────────────────────▼────────────────────────────┐
│               API Layer (FastAPI, per-tenant)            │
│  /ara  │ /access-requests │ /firefighter │ /certification│
└──────┬───────────┬───────────────┬──────────┬───────────┘
       │           │               │          │
   ARA Engine  ARM Manager    FF Manager  Cert Manager
       │           │               │          │
┌──────▼───────────▼───────────────▼──────────▼───────────┐
│              Database (PostgreSQL / SQLite)               │
│  risk_violations │ access_requests │ ff_sessions │ ...   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. SoD Rule Library

*Reference codes: AC-01 (Rule Catalog), AC-02 (Custom Rules), AC-03 (Import/Export), AC-04 (Versioning), AC-05 (Tenant Preferences), AC-06 (Rule Analytics)*

### 2.1 Built-in Rules: The 12 Categories

The `SoDRulesetLibrary` class in `core/rules/sod_ruleset.py` provides a zero-configuration, pre-built ruleset covering every major SAP business process. On startup, both rule engines load this library automatically via bridge modules.

#### Finance (FI) — 20 rules

The Finance category covers the entire Accounts Payable, Accounts Receivable, and General Ledger process chain. The most critical rules prevent the "complete fraud cycle": a single person controlling master data, transaction entry, and payment execution.

| Rule ID | Name | Severity | SOX |
|---|---|---|---|
| SOD-FI-001 | Vendor Master vs AP Payment | CRITICAL | Yes |
| SOD-FI-002 | Vendor Master vs AP Invoice | HIGH | Yes |
| SOD-FI-003 | AP Invoice vs AP Payment | HIGH | Yes |
| SOD-FI-004 | Customer Master vs AR Cash Application | HIGH | Yes |
| SOD-FI-005 | GL Journal Entry vs Period Close | MEDIUM | Yes |
| SOD-FI-006 | Bank Master vs AP Payment | CRITICAL | Yes |
| SOD-FI-007 | Credit Memo vs AR Cash | HIGH | No |
| SOD-FI-008 | Vendor Master vs Credit Memo | HIGH | Yes |
| SOD-FI-009 | GL Journal Entry vs Bank Master | HIGH | Yes |
| SOD-FI-010 | AP Invoice vs Bank Master | CRITICAL | Yes |
| SOD-FI-011 | Vendor Master vs GL Journal | HIGH | Yes |
| SOD-FI-012 | Customer Master vs Billing | HIGH | Yes |
| SOD-FI-013 | Cost Center vs GL Journal | MEDIUM | No |
| SOD-FI-014 | Profit Center vs Financial Report | MEDIUM | No |
| SOD-FI-015 | Tax Config vs AP Invoice | HIGH | Yes |
| SOD-FI-016 | Tolerance Group vs AP Payment | HIGH | Yes |
| SOD-FI-017 | Internal Order vs GL Journal | MEDIUM | No |
| SOD-FI-018 | Period Close vs Financial Report | MEDIUM | Yes |
| SOD-FI-019 | Credit Memo vs Customer Master | HIGH | Yes |
| SOD-FI-020 | Bank Master vs Credit Memo | HIGH | Yes |

**Example — SOD-FI-001 (Vendor Master vs AP Payment):**

> A user who can both create/modify vendor master records (FK01, FK02, XK01, XK02) and execute payment runs (F110, FBZ1, FBZ2) can create a fictitious vendor and pay them. Business impact: fraudulent payments to fake vendors. Recommendation: separate vendor maintenance from payment processing.

#### Procurement/MM (P2P) — 20 rules

The P2P category enforces the classic purchase-to-pay three-way match control: Requisition → Purchase Order → Goods Receipt → Invoice Verification must each be performed by different individuals.

| Rule ID | Name | Severity |
|---|---|---|
| SOD-MM-001 | PR Creation vs PO Creation | MEDIUM |
| SOD-MM-002 | PO Creation vs Goods Receipt | HIGH |
| SOD-MM-003 | PO Creation vs Invoice Verification | HIGH |
| SOD-MM-004 | Goods Receipt vs Invoice Verification | HIGH |
| SOD-MM-005 | Vendor Master vs PO Creation | CRITICAL |
| SOD-MM-006 | Material Master vs Goods Receipt | MEDIUM |
| SOD-MM-007 | Source List vs PO Creation | MEDIUM |
| SOD-MM-008 | PR Creation vs Goods Receipt | HIGH |
| SOD-MM-009 | PR Creation vs Invoice Verification | MEDIUM |
| SOD-MM-010 | Contract Mgmt vs PO Creation | MEDIUM |
| SOD-MM-011 | Contract Mgmt vs Invoice Verification | HIGH |
| SOD-MM-012 | Info Record vs PO Creation | MEDIUM |
| SOD-MM-013 | Release Strategy vs PO Creation | CRITICAL |
| SOD-MM-014 | Vendor Master vs Goods Receipt | HIGH |
| SOD-MM-015 | Vendor Master vs Invoice Verification | CRITICAL |
| SOD-MM-016 | Material Master vs PO Creation | MEDIUM |
| SOD-MM-017 | Material Master vs Invoice Verification | MEDIUM |
| SOD-MM-018 | Vendor Evaluation vs PO Creation | MEDIUM |
| SOD-MM-019 | Source List vs Vendor Master | HIGH |
| SOD-MM-020 | PO Creation vs AP Payment | CRITICAL |

#### Sales/SD (O2C) — 15 rules

Covers the Order-to-Cash cycle. Key concern: a salesperson cannot set their own prices, release their own credit blocks, and generate their own invoices.

| Rule ID | Name | Severity |
|---|---|---|
| SOD-SD-001 | Sales Order vs Delivery | MEDIUM |
| SOD-SD-002 | Sales Order vs Billing | HIGH |
| SOD-SD-003 | Pricing vs Sales Order | HIGH |
| SOD-SD-004 | Customer Master vs Sales Order | MEDIUM |
| SOD-SD-005 | Credit Management vs Sales Order | HIGH |
| SOD-SD-006 | Returns vs AR Cash Application | HIGH |
| SOD-SD-007 | Delivery vs Billing | MEDIUM |
| SOD-SD-008 | Pricing vs Billing | HIGH |
| SOD-SD-009 | Credit Mgmt vs Billing | HIGH |
| SOD-SD-010 | Returns vs Billing | HIGH |
| SOD-SD-011 | Sales Order vs Credit Mgmt | HIGH |
| SOD-SD-012 | Pricing vs Credit Mgmt | MEDIUM |
| SOD-SD-013 | Customer Master vs Billing | HIGH |
| SOD-SD-014 | Customer Master vs Delivery | MEDIUM |
| SOD-SD-015 | Returns vs Customer Master | MEDIUM |

#### Human Resources (HR) — 10 rules

The most sensitive category. Ghost employee and payroll redirection fraud are the top concerns. All HR rules that touch payroll are marked SOX and GDPR-relevant.

| Rule ID | Name | Severity | SOX | GDPR |
|---|---|---|---|---|
| SOD-HR-001 | Personnel Master vs Payroll | CRITICAL | Yes | Yes |
| SOD-HR-002 | Bank Data vs Payroll | CRITICAL | Yes | Yes |
| SOD-HR-003 | Time Management vs Payroll | HIGH | No | No |
| SOD-HR-004 | Org Structure vs Personnel Master | MEDIUM | No | No |
| SOD-HR-005 | Personnel Master vs Bank Data | CRITICAL | Yes | Yes |
| SOD-HR-006 | Time Management vs Personnel Master | MEDIUM | No | No |
| SOD-HR-007 | Org Structure vs Payroll | HIGH | No | No |
| SOD-HR-008 | Personnel Master vs AP Payment | HIGH | Yes | No |
| SOD-HR-009 | Bank Data vs AP Payment | CRITICAL | Yes | Yes |
| SOD-HR-010 | Personnel Master vs User Admin | HIGH | No | No |

#### Basis/Security (BA) — 16 rules

Basis rules protect the security layer itself. These are the highest-priority rules in any SAP landscape because a Basis administrator who can also create users and assign roles has effectively bypassed all other controls.

| Rule ID | Name | Severity |
|---|---|---|
| SOD-BA-001 | User Admin vs Role Admin | CRITICAL |
| SOD-BA-002 | User Admin vs Table Maintenance | CRITICAL |
| SOD-BA-003 | Role Admin vs Transport Management | HIGH |
| SOD-BA-004 | Program Execution vs Table Maintenance | HIGH |
| SOD-BA-005 | User Admin vs Transport | CRITICAL |
| SOD-BA-006 | Role Admin vs Table Maint | CRITICAL |
| SOD-BA-007 | User Admin vs Audit Log | CRITICAL |
| SOD-BA-008 | Role Admin vs Audit Log | HIGH |
| SOD-BA-009 | User Admin vs Background Jobs | HIGH |
| SOD-BA-010 | Table Maint vs Transport | CRITICAL |
| SOD-BA-011 | Debug/Replace vs Transport | CRITICAL |
| SOD-BA-012 | System Config vs User Admin | HIGH |
| SOD-BA-013 | RFC Admin vs User Admin | HIGH |
| SOD-BA-014 | Program Execution vs Transport | HIGH |
| SOD-BA-015 | Debug/Replace vs Table Maint | CRITICAL |
| SOD-BA-016 | Background Jobs vs Table Maint | HIGH |

#### Treasury (TR) — 5 rules | Asset Accounting (AA) — 5 rules | Warehouse (WM) — 5 rules | Quality (QM) — 3 rules | Plant Maintenance (PM) — 4 rules | Project System (PS) — 3 rules | Cross-Process (XP) — 15 rules

**Cross-Process (XP) rules** are the most dangerous class. They span module boundaries — e.g., a user with both User Administration and AP Payment capability (SOD-XP-001) can create a user, assign it payment authority, and execute payments entirely autonomously. All 15 XP rules are flagged `is_cross_system=True`.

| Rule ID | Name | Severity |
|---|---|---|
| SOD-XP-001 | User Admin vs AP Payment | CRITICAL |
| SOD-XP-002 | User Admin vs GL Journal | CRITICAL |
| SOD-XP-003 | Table Maint vs AP Payment | CRITICAL |
| SOD-XP-006 | Table Maint vs HR Payroll | CRITICAL |
| SOD-XP-007 | Debug/Replace vs AP Payment | CRITICAL |
| SOD-XP-010 | Vendor Master vs Treasury Payment | CRITICAL |
| SOD-XP-014 | User Admin vs Treasury Payment | CRITICAL |
| SOD-XP-015 | System Config vs AP Payment | CRITICAL |

### 2.2 Rule Structure

Each SoD rule in the library is a `SoDRule` dataclass with the following schema:

```
SoDRule
├── rule_id          : str          — Unique ID, e.g. "SOD-FI-001"
├── name             : str          — Short human-readable name
├── description      : str          — What access combination is conflicting
├── risk_level       : RiskLevel    — low | medium | high | critical
├── business_process : BusinessProcess — FI | MM | SD | HR | BASIS | TR | AA | WM | QM | PM | PS | GEN
├── function1        : BusinessFunction — First conflicting function
│   ├── function_id        : str
│   ├── name               : str
│   ├── transaction_codes  : List[str]  — e.g. ["FK01","FK02","XK01"]
│   └── auth_objects       : List[Dict] — e.g. [{"object":"F_LFA1_BUK","field":"ACTVT","values":["01","02"]}]
├── function2        : BusinessFunction — Second conflicting function (same structure)
├── risk_description : str          — What fraud or error can occur
├── business_impact  : str          — Financial/operational consequence
├── recommendation   : str          — Remediation action
├── sox_relevant     : bool         — True if covered by SOX 302/404
├── gdpr_relevant    : bool         — True if involves personal data
├── regulatory_refs  : List[str]    — Additional regulatory references
├── is_active        : bool         — Can be disabled per-tenant
└── is_cross_system  : bool         — True for XP cross-process rules
```

**BusinessFunction structure:**

```
BusinessFunction
├── function_id        : str       — e.g. "FI001"
├── name               : str       — e.g. "Vendor Master Maintenance"
├── description        : str
├── business_process   : BusinessProcess
├── transaction_codes  : List[str] — SAP t-codes
└── auth_objects       : List[Dict]
    ├── object         : str       — Auth object name, e.g. "F_LFA1_BUK"
    ├── field          : str       — Field name, e.g. "ACTVT"
    └── values         : List[str] — Authorized values, e.g. ["01","02","06"]
```

### 2.3 Creating Custom Rules

Custom rules extend the built-in library without modifying the library source. They are added at runtime via API and loaded on engine initialization. The idempotent bridge pattern ensures custom rules are never overwritten by the library loader.

**Step 1: Identify the conflicting transaction codes**

Determine which t-codes constitute Function A and Function B. Example: you want to prevent a user from both maintaining pricing info records (ME11, ME12) and releasing purchase orders for payment (ME29N).

**Step 2: Create the rule via API**

```http
POST /ara/sod/rules
Content-Type: application/json
Authorization: Bearer <token>

{
  "rule_id": "SOD-CUSTOM-001",
  "name": "Info Record vs PO Release",
  "description": "Maintain purchasing info records AND release POs for payment",
  "function_1_tcodes": ["ME11", "ME12", "ME13"],
  "function_2_tcodes": ["ME29N", "ME28"],
  "severity": "high",
  "category": "financial",
  "business_impact": "User can set purchase prices and then approve POs at those prices without independent review"
}
```

**Response:**

```json
{
  "status": "created",
  "rule": {
    "rule_id": "SOD-CUSTOM-001",
    "name": "Info Record vs PO Release",
    "severity": "high",
    "enabled": true,
    "function_1_tcodes": ["ME11", "ME12", "ME13"],
    "function_2_tcodes": ["ME29N", "ME28"]
  }
}
```

**Step 3: Verify the rule is active**

```http
GET /ara/sod/rules/SOD-CUSTOM-001
```

**Step 4: Test the rule against a user**

```http
POST /ara/analyze/user
{
  "access_data": {
    "user_id": "TEST_USER",
    "tcodes": ["ME11", "ME29N"]
  }
}
```

The response will include `SOD-CUSTOM-001` in `sod_conflicts` if the user has both t-codes.

**Step 5: Enable/disable the rule**

```http
PUT /ara/sod/rules/SOD-CUSTOM-001/toggle?enabled=false
```

### 2.4 Rule Import/Export

The platform supports bulk rule management via Excel and CSV. This is the primary mechanism for migrating rules from an existing SAP GRC AC installation.

**Export format (CSV columns):**

```
rule_id, name, description, severity, business_process, sox_relevant, gdpr_relevant,
function_1_id, function_1_name, function_1_tcodes, function_2_id, function_2_name, function_2_tcodes,
risk_description, business_impact, recommendation, is_active
```

**Import endpoint:**

```http
POST /sod-rules/import
Content-Type: multipart/form-data

file: <CSV or XLSX file>
overwrite_existing: false        # Set true to update existing rule_ids
```

Rules with `rule_id` values that already exist in the library (e.g. `SOD-FI-001`) are skipped unless `overwrite_existing=true`. This protects the built-in ruleset from accidental overwrite.

**Export endpoint:**

```http
GET /sod-rules/export?format=csv&include_inactive=false
GET /sod-rules/export?format=xlsx&business_process=FI
```

### 2.5 Rule Versioning and Change History

Every change to a rule's definition is logged with timestamp, actor, and a before/after snapshot. The version chain is stored in the rule's audit history:

```json
{
  "rule_id": "SOD-CUSTOM-001",
  "version": 3,
  "change_history": [
    {
      "version": 1,
      "changed_at": "2026-08-01T09:00:00Z",
      "changed_by": "admin@company.com",
      "change_type": "created",
      "summary": "Initial rule creation"
    },
    {
      "version": 2,
      "changed_at": "2026-08-15T14:30:00Z",
      "changed_by": "security.admin@company.com",
      "change_type": "modified",
      "summary": "Added ME28 to function_2_tcodes",
      "previous": {"function_2_tcodes": ["ME29N"]},
      "current": {"function_2_tcodes": ["ME29N", "ME28"]}
    }
  ]
}
```

**Retrieve rule history:**

```http
GET /sod-rules/{rule_id}/history
```

### 2.6 Tenant Rule Preferences

In a multi-tenant deployment, each tenant can enable or disable individual built-in rules without affecting other tenants. This is critical for organizations with compensating controls already in place.

```http
PUT /ara/sod/rules/SOD-FI-005/toggle?enabled=false
X-Tenant-ID: tenant_acme_corp
```

This call disables `SOD-FI-005` (GL Journal Entry vs Period Close) only for `tenant_acme_corp`. All other tenants continue to see this rule as active.

Tenant rule preferences are stored per-tenant in the rules engine registry (`_rule_engines: Dict[str, RuleEngine]` in `api/routers/risk_analysis.py`).

### 2.7 SoD Rule API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/ara/sod/rules` | List all rules (filter by category, severity) |
| GET | `/ara/sod/rules/{rule_id}` | Get rule detail |
| POST | `/ara/sod/rules` | Create custom rule |
| DELETE | `/ara/sod/rules/{rule_id}` | Delete custom rule |
| PUT | `/ara/sod/rules/{rule_id}/toggle` | Enable/disable rule |
| GET | `/sod-rules` | Legacy rule engine endpoint |
| POST | `/sod-rules/import` | Bulk import rules (CSV/XLSX) |
| GET | `/sod-rules/export` | Export rules (CSV/XLSX) |
| GET | `/sod-rules/{rule_id}/history` | Rule change history |

---

## 3. Risk Intelligence Engine — ARA

*Reference codes: AC-10 (User Analysis), AC-11 (Role Analysis), AC-12 (Batch/Scheduled), AC-13 (Mitigation), AC-14 (What-If), AC-15 (Risk Scoring), AC-16 (Org Ranking), AC-17 (Sensitive Access), AC-18 (Dormant Accounts)*

The Risk Intelligence Engine (`core/ara/`) is GovernexPlus's differentiated intelligence layer. Where SAP GRC performs binary conflict detection (conflict / no conflict), GovernexPlus calculates a continuous, context-modulated risk score and explains why the risk matters right now.

### 3.1 User-Level Analysis

User-level analysis evaluates a user's complete access portfolio against all active SoD rules, sensitive access definitions, and critical action patterns.

**Running a user analysis:**

```http
POST /ara/analyze/user
Content-Type: application/json
Authorization: Bearer <token>

{
  "access_data": {
    "user_id": "JSMITH",
    "roles": ["Z_AP_CLERK", "Z_VENDOR_MAINT"],
    "tcodes": ["FK01", "FK02", "FB60", "F110"],
    "auth_objects": [
      {"object": "F_LFA1_BUK", "field": "ACTVT", "values": ["01","02","06"]},
      {"object": "F_REGU_BUK", "field": "ACTVT", "values": ["01","02"]}
    ]
  },
  "context": {
    "employment_type": "employee",
    "department": "Accounts Payable",
    "is_privileged_user": false,
    "is_emergency_access": false,
    "access_level": "standard",
    "current_location": "internal",
    "previous_violations": 2
  },
  "include_behavioral": true,
  "include_remediation": true
}
```

**Interpreting the response:**

```json
{
  "analysis_id": "ARA-20260906-00412",
  "user_id": "JSMITH",
  "analyzed_at": "2026-09-06T09:15:32Z",
  "duration_ms": 47,
  "summary": {
    "total_risks": 3,
    "critical_count": 1,
    "high_count": 2,
    "medium_count": 0,
    "low_count": 0,
    "aggregate_risk_score": 87.4,
    "max_risk_score": 100.0
  },
  "risks": [
    {
      "risk_id": "ARA-JSMITH-001",
      "rule_id": "SOD-FI-001",
      "title": "Vendor Master vs AP Payment",
      "severity": "critical",
      "final_score": 100.0,
      "base_score": 90,
      "context_multiplier": 1.15,
      "usage_multiplier": 1.05,
      "conflicting_functions": ["FI001", "FI003"],
      "business_impact": "Fraudulent payments to fake vendors",
      "remediation_priority": 1
    }
  ],
  "sod_conflicts": [...],
  "remediation_suggestions": [
    {
      "action": "remove_role",
      "role": "Z_VENDOR_MAINT",
      "impact": "Eliminates 1 critical and 1 high violation",
      "risk_reduction": 62.3
    }
  ]
}
```

Key fields to examine: `aggregate_risk_score` (0–100 composite), `critical_count` (immediate action required), and `remediation_suggestions` (AI-ranked removal recommendations).

### 3.2 Role-Level Analysis

Role analysis evaluates a single role in isolation, identifying conflicts that exist within the role itself — before any user is assigned to it.

```http
GET /ara/analyze/role/Z_FINANCE_MANAGER?tcodes=FB60,F110,FK01
```

**Response:**

```json
{
  "role_id": "Z_FINANCE_MANAGER",
  "risk_summary": {
    "total_risks": 2,
    "critical_count": 1,
    "aggregate_score": 78.5
  },
  "sod_conflicts": [
    {"rule_id": "SOD-FI-003", "severity": "high", ...},
    {"rule_id": "SOD-FI-001", "severity": "critical", ...}
  ],
  "recommendation": "review_required"
}
```

Roles with `critical_count > 0` should be flagged for redesign in the Role Engineering (Role Design Studio) module before deployment.

### 3.3 Cross-Role Conflict Detection

Cross-role conflicts occur when no single role contains a full SoD violation, but the combination of two roles assigned to the same user creates one. GovernexPlus detects these by analyzing the union of all t-codes and auth-objects across a user's entire role portfolio.

Cross-role conflicts are returned in the standard `/ara/analyze/user` response within the `sod_conflicts` array. The `conflict_type` field distinguishes intra-role from cross-role conflicts:

```json
{
  "conflict_id": "CONF-001",
  "rule_id": "SOD-FI-001",
  "conflict_type": "cross_role",
  "role_containing_function_1": "Z_VENDOR_MAINT",
  "role_containing_function_2": "Z_AP_PAYMENT",
  "severity": "critical"
}
```

### 3.4 What-If Simulation

What-if simulation is the pre-provisioning gate. Before an access request is approved, the approver can see exactly what new violations would be created if the requested access is granted.

**Simulate adding a role:**

```http
POST /ara/simulate/access

{
  "user_id": "MBROWN",
  "current_roles": ["Z_AP_CLERK"],
  "current_tcodes": ["FB60", "MIRO"],
  "requested_roles": ["Z_VENDOR_MAINT"],
  "requested_tcodes": ["FK01", "FK02"],
  "request_reason": "Vendor data clean-up project"
}
```

**Response:**

```json
{
  "simulation_id": "SIM-20260906-00087",
  "current_state": {"risk_score": 12.0, "risk_count": 0},
  "simulated_state": {"risk_score": 84.5, "risk_count": 2},
  "impact": {
    "risk_delta": 72.5,
    "new_sod_conflicts": 2,
    "new_sensitive_access": 0
  },
  "new_sod_conflicts": [
    {"rule_id": "SOD-FI-002", "severity": "high"},
    {"rule_id": "SOD-FI-001", "severity": "critical"}
  ],
  "recommendation": "deny",
  "recommendation_reason": "Granting this access would create 1 critical SoD violation (SOD-FI-001: Vendor Master vs AP Payment). This combination allows fraudulent vendor payments."
}
```

**Simulate role changes (add and remove simultaneously):**

```http
POST /ara/simulate/role-change?user_id=MBROWN&add_roles=Z_VENDOR_MAINT&remove_roles=Z_AP_PAYMENT&current_roles=Z_AP_CLERK
```

### 3.5 Risk Scoring Model

GovernexPlus calculates a continuous risk score from 0 to 100 for each detected violation. The model has three components:

```
final_score = min(100, base_score × context_multiplier × usage_multiplier)
```

**Base Score** (derived from rule severity):

| Severity | Base Score Range |
|---|---|
| CRITICAL | 80 – 100 |
| HIGH | 60 – 79 |
| MEDIUM | 35 – 59 |
| LOW | 10 – 34 |

**Context Multipliers** (cumulative):

| Condition | Multiplier |
|---|---|
| Contractor or external user | ×1.25 |
| Privileged/elevated user | ×1.20 |
| User has 3+ previous violations | ×1.15 |
| Access from external network | ×1.10 |
| User has 1–2 previous violations | ×1.05 |
| Standard employee, internal access | ×1.00 |

**Usage Multipliers** (behavioral):

| Condition | Multiplier |
|---|---|
| Both conflicting t-codes used in last 30 days | ×1.20 |
| Conflicting t-codes used off-hours or weekends | ×1.15 |
| One conflicting t-code used, one dormant | ×0.90 |
| Neither conflicting t-code used (dormant access) | ×0.75 |

The aggregate score for a user is: `aggregate_risk_score = weighted average of all violation scores, with critical violations weighted 3×`

### 3.6 Batch and Scheduled Analysis (AC-12)

Batch analysis allows scanning the entire user population in a single API call, ordered by risk descending. This is the engine behind nightly scheduled scans.

```http
POST /ara/analyze/batch

[
  {"user_id": "JSMITH", "roles": ["Z_AP_CLERK","Z_VENDOR_MAINT"], "tcodes": ["FK01","FB60","F110"]},
  {"user_id": "AGARCIA", "roles": ["Z_PURCHASER"], "tcodes": ["ME21N","ME22N","MIRO"]},
  ...
]
```

**Response:**

```json
{
  "total_users": 250,
  "analyzed": 250,
  "failed": 0,
  "results": [
    {"user_id": "JSMITH", "critical_count": 1, "high_count": 2, "aggregate_score": 87.4},
    {"user_id": "AGARCIA", "critical_count": 0, "high_count": 1, "aggregate_score": 41.2},
    ...
  ],
  "analysis_timestamp": "2026-09-06T02:00:00Z"
}
```

**Setting up a scheduled nightly scan:**

Configure the `RiskAnalysisScheduler` in `core/scheduler/automation_jobs.py` with a cron expression. The job pulls all active users from the tenant database, runs batch analysis, and persists results to `risk_violations`.

```python
# core/scheduler/automation_jobs.py
RISK_SCAN_SCHEDULE = "0 2 * * *"  # 2:00 AM daily
```

Or set via environment variable:

```
RISK_SCAN_CRON=0 2 * * *
RISK_SCAN_ENABLED=true
```

### 3.7 Org-Level Ranking (AC-16)

Org-level ranking aggregates risk scores by department, company code, or business unit to identify where the highest concentration of risk exists.

```http
GET /ara/analytics/departments
```

**Response:**

```json
{
  "departments": [
    {"department": "Accounts Payable", "avg_risk_score": 72.1, "critical_violations": 8, "high_violations": 15, "user_count": 23},
    {"department": "Treasury", "avg_risk_score": 68.4, "critical_violations": 3, "high_violations": 9, "user_count": 7},
    {"department": "Procurement", "avg_risk_score": 44.2, "critical_violations": 2, "high_violations": 12, "user_count": 41}
  ]
}
```

Top users and roles by risk:

```http
GET /ara/analytics/leaderboard/users?top_n=10&min_critical=1
GET /ara/analytics/leaderboard/roles?top_n=10
```

### 3.8 Dormant Account Detection (AC-18)

Dormant accounts with sensitive access are a critical audit finding. GovernexPlus identifies users who have high-risk or conflicting access but have not used the system in a configurable number of days.

```http
GET /risk-analysis/dormant-users?days_inactive=90&min_risk_level=high
```

The detection logic cross-references:
1. Users with active SoD violations or sensitive access (from risk_violations table)
2. Last login date from the identity provider or SAP (from connector data)
3. Last t-code usage from the audit log

**Result format:**

```json
{
  "dormant_high_risk_users": [
    {
      "user_id": "RLOPEZ",
      "days_inactive": 127,
      "last_login": "2026-05-02",
      "violation_count": 3,
      "max_severity": "critical",
      "recommendation": "disable_account"
    }
  ]
}
```

### 3.9 Violation Lifecycle

Every violation detected by the Risk Intelligence Engine follows a managed status lifecycle:

```
open → in_progress → mitigated → remediated → accepted → closed
         │               │
         └── rejected ──►┘
```

| Status | Meaning |
|---|---|
| `open` | Violation detected, no action taken |
| `in_progress` | Assigned to an owner for resolution |
| `mitigated` | Mitigation control applied, risk accepted at reduced level |
| `remediated` | Access has been removed or restructured |
| `accepted` | Formally accepted as residual risk (time-bounded) |
| `closed` | Fully resolved and verified |

Status updates are made via:

```http
PUT /risk-analysis/violations/{violation_id}/status
{"status": "in_progress", "assignee": "security.admin@company.com", "notes": "Investigating with AP team"}
```

### 3.10 Risk Intelligence Engine Persistence

All risks detected during `/ara/analyze/user` are automatically persisted to the `risk_violations` database table using a background task. This is non-blocking — persistence failures never affect the API response.

**Persistence flow:**

```
POST /ara/analyze/user
  → engine.analyze_user() [synchronous, returns result]
  → background_tasks.add_task(_persist_risks, result.risks, user_id)
  → response returned immediately
  ↓ (async background)
  → _persist_risks: resolves user FK from external_id
  → RiskViolationRepository.create_violation() per risk
  → committed to risk_violations table
```

**Table columns populated:**

| Column | Source |
|---|---|
| `violation_id` | `"ARA-" + risk.risk_id` |
| `rule_id` | `risk.rule_id or risk.risk_type.value` |
| `severity` | Mapped: critical/high/medium/low → `RiskSeverityLevel` enum |
| `severity_score` | `risk.final_score` (0–100) |
| `conflicting_functions` | `risk.conflicting_functions` (JSON array) |
| `detected_by` | `"ARA_ENGINE"` |

Duplicate violations (same `violation_id` in the same period) are silently skipped via a try/except with `db.rollback()`.

### 3.11 Risk Intelligence Engine API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/ara/analyze/user` | Full user risk analysis |
| POST | `/ara/analyze/batch` | Batch user analysis |
| GET | `/ara/analyze/role/{role_id}` | Role inherent risk analysis |
| POST | `/ara/simulate/access` | Pre-provisioning simulation |
| POST | `/ara/simulate/role-change` | Role change impact simulation |
| GET | `/ara/sod/rules` | List SoD rules |
| GET | `/ara/sod/rules/{rule_id}` | Get SoD rule |
| POST | `/ara/sod/rules` | Create custom rule |
| DELETE | `/ara/sod/rules/{rule_id}` | Delete custom rule |
| PUT | `/ara/sod/rules/{rule_id}/toggle` | Enable/disable rule |
| GET | `/ara/mitigation/controls` | List mitigation controls |
| POST | `/ara/mitigation/controls` | Create mitigation control |
| POST | `/ara/mitigation/assign` | Assign control to risk |
| GET | `/ara/mitigation/assignments/{risk_id}` | Get assignments for risk |
| POST | `/ara/mitigation/exceptions/request` | Request risk exception |
| POST | `/ara/mitigation/exceptions/approve` | Approve exception |
| GET | `/ara/analytics/summary` | Executive summary |
| GET | `/ara/analytics/distribution` | Risk score distribution |
| POST | `/ara/analytics/trend` | Historical risk trend |
| GET | `/ara/analytics/forecast` | Risk forecast |
| GET | `/ara/analytics/leaderboard/users` | Top risk users |
| GET | `/ara/analytics/leaderboard/roles` | Top risk roles |
| GET | `/ara/analytics/departments` | Department risk summary |
| GET | `/ara/analytics/economic-exposure` | Economic risk quantification |
| POST | `/ara/behavioral/record-usage` | Record usage metrics |
| GET | `/ara/behavioral/score/{user_id}` | Behavioral risk score |

---

## 4. Mitigation Controls

*Reference code: AC-13*

A mitigation control is a compensating control that reduces the effective risk of a SoD violation to an acceptable level when access removal is not operationally feasible. GovernexPlus maintains a Mitigation Register that links every accepted violation to its control with validity, owner, and testing schedule.

### 4.1 Creating a Mitigation Control

```http
POST /ara/mitigation/controls

{
  "control_id": "MIT-FI-AP-001",
  "name": "Monthly AP Payment Review by CFO",
  "description": "CFO reviews all vendor payments exceeding $10,000 monthly via automated report",
  "control_type": "detective",
  "risk_reduction_pct": 60.0,
  "applicable_risk_types": ["sod_conflict", "financial"],
  "requires_approval": true,
  "approvers": ["cfo@company.com", "internal.audit@company.com"]
}
```

**Control types:**

| Type | Description |
|---|---|
| `preventive` | Prevents the risk from occurring (e.g., dual approval required) |
| `detective` | Detects after the fact (e.g., exception report, reconciliation) |
| `manual` | Human review process (e.g., manager sign-off, supervisor review) |

**Risk reduction percentage:** The percentage reduction in effective risk score when this control is active. A control with `risk_reduction_pct = 60` on a violation with `final_score = 80` yields an effective score of `80 × (1 - 0.60) = 32`.

### 4.2 Assigning Controls to Violations

A control assignment links a specific risk violation to a mitigation control for a specified period.

```http
POST /ara/mitigation/assign

{
  "risk_id": "ARA-JSMITH-001",
  "control_id": "MIT-FI-AP-001",
  "assigned_by": "ciso@company.com",
  "justification": "JSMITH is the only person with vendor maintenance access during the ERP migration. CFO monthly review is in place as compensating control.",
  "expires_at": "2027-03-31T23:59:59Z"
}
```

**After assignment:**

```http
GET /ara/mitigation/assignments/ARA-JSMITH-001

{
  "risk_id": "ARA-JSMITH-001",
  "is_mitigated": true,
  "assignments": [
    {
      "assignment_id": "ASMT-00123",
      "control_id": "MIT-FI-AP-001",
      "control_name": "Monthly AP Payment Review by CFO",
      "assigned_by": "ciso@company.com",
      "assigned_at": "2026-09-06T10:00:00Z",
      "expires_at": "2027-03-31T23:59:59Z",
      "effective_risk_reduction": 60.0,
      "status": "active"
    }
  ]
}
```

### 4.3 Monitoring and Testing

Each mitigation control has an associated testing schedule. The system tracks control application events, override events, and recurrences:

```http
POST /ara/analytics/record-control-event?control_id=MIT-FI-AP-001&event_type=applied&user_id=cfo@company.com&risks_covered=3
POST /ara/analytics/record-control-event?control_id=MIT-FI-AP-001&event_type=prevented&risks_covered=1
```

Control effectiveness metrics:

```http
GET /ara/analytics/control-effectiveness?control_id=MIT-FI-AP-001

{
  "controls": [
    {
      "control_id": "MIT-FI-AP-001",
      "application_count": 12,
      "override_count": 0,
      "exception_count": 1,
      "recurrence_count": 0,
      "incidents_prevented": 2,
      "effectiveness_score": 91.7,
      "coverage_count": 3
    }
  ]
}
```

### 4.4 Unified Mitigation Register (XL-C Integration)

Mitigation controls registered in the Risk Intelligence Engine are automatically visible in the Process Control module's unified control register (XL-C cross-module integration). A control created in the Risk Intelligence Engine to mitigate `SOD-FI-001` appears in the PC control library with `source = "ARA_MITIGATION"`, allowing Process Control owners to include it in framework mapping and SOX certification.

See Section 11 of the Process Control Module Guide for the reverse linkage.

### 4.5 Risk Exceptions

When a violation cannot be mitigated by a compensating control, it can be formally accepted as a time-bounded risk exception:

```http
POST /ara/mitigation/exceptions/request

{
  "risk_id": "ARA-JSMITH-001",
  "requested_by": "ap.manager@company.com",
  "justification": "Staff shortage during ERP implementation. Will be remediated by Q1 2027.",
  "expires_at": "2027-01-31T23:59:59Z",
  "approvers": ["ciso@company.com", "cfo@company.com"]
}
```

Exceptions require approval by configured approvers:

```http
POST /ara/mitigation/exceptions/approve

{
  "exception_id": "EXC-00045",
  "approved_by": "ciso@company.com",
  "comments": "Approved subject to quarterly management review"
}
```

Expired exceptions automatically revert violations to `open` status and trigger re-notification.

---

## 5. Access Lifecycle Manager — ARM

*Reference codes: AC-20 (Request Portal), AC-21 (Risk Preview), AC-22 (Approval Workflow), AC-23 (Provisioning), AC-24 (JML Automation)*

### 5.1 Request Lifecycle

```
DRAFT
  │  (requester submits)
  ▼
SUBMITTED
  │  (risk analysis + workflow routing)
  ▼
PENDING_APPROVAL
  │  (approvers act)
  ├──► REJECTED ──► [closed]
  │
  ▼
APPROVED
  │  (provisioning engine acts)
  ├──► PROVISIONING_FAILED ──► [escalated]
  │
  ▼
PROVISIONED ──► [can be revoked via UAR campaign]
  │
CANCELLED (by requester, before APPROVED)
```

### 5.2 Creating an Access Request

Access requests can be created by end users via the self-service portal or programmatically via API.

**Step 1: Browse the role catalog**

```http
GET /catalog/roles?business_process=FI&search=accounts+payable
```

**Step 2: Preview risk before submitting**

```http
POST /preview-risk

{
  "target_user_id": "MBROWN",
  "requested_roles": ["Z_AP_CLERK", "Z_VENDOR_READ"]
}
```

If the preview returns `critical_count > 0`, the UI displays a prominent warning with the conflicting functions and recommends an alternative.

**Step 3: Create the request (draft)**

```http
POST /access-requests/
Content-Type: application/json

{
  "requester_user_id": "JSMITH",
  "requester_name": "John Smith",
  "requester_email": "john.smith@company.com",
  "target_user_id": "MBROWN",
  "target_user_name": "Mary Brown",
  "requested_roles": ["Z_AP_CLERK"],
  "business_justification": "Mary is joining the AP team and needs access to enter vendor invoices for the EMEA procurement project starting October 2026.",
  "request_type": "new_access",
  "is_temporary": false,
  "ticket_reference": "INC0045678"
}
```

**Response:**

```json
{
  "request_id": "REQ-20260906-00234",
  "status": "draft",
  "message": "Request created in draft. Use /submit to submit for approval."
}
```

**Step 4: Submit for approval**

```http
POST /access-requests/REQ-20260906-00234/submit
```

On submission, the system:
1. Runs full Risk Intelligence Engine analysis on the target user + requested roles
2. Determines approval workflow stages based on risk level and role sensitivity
3. Notifies the first-stage approvers
4. Returns the request status with current approvers

### 5.3 Model User

The Model User function copies the complete access profile from a reference user to a new user, then runs risk analysis on the copied set before submission.

```http
POST /access-requests/model-user

{
  "requester_user_id": "JSMITH",
  "target_user_id": "TNGUYEN",
  "model_user_id": "MBROWN",
  "business_justification": "Tina Nguyen is replacing Mary Brown in the AP team. Copying identical access profile.",
  "ticket_reference": "CHG0012345"
}
```

The system creates a request for every role the model user holds, runs a consolidated risk preview, and groups them into a single approval workflow. Roles that would introduce critical violations are flagged separately and require additional justification.

### 5.4 Shopping Cart

The Shopping Cart allows requesters to accumulate multiple access items across different systems and business processes, then submit them as a single grouped request for unified approval routing.

**Add an item to the cart:**

```http
POST /arm/cart/items

{
  "requester_user_id": "JSMITH",
  "target_user_id": "TNGUYEN",
  "access_type": "role",
  "access_id": "Z_AP_CLERK",
  "system": "SAP_PROD",
  "justification": "Invoice entry for AP team"
}
```

The system immediately runs an inline SoD check for each item as it is added. If adding an item would create a violation with any item already in the cart, the user sees an inline warning before proceeding.

**Review the cart:**

```http
GET /arm/cart/{requester_user_id}

{
  "cart_id": "CART-TNGUYEN-001",
  "items": [
    {"access_id": "Z_AP_CLERK", "risk_level": "low"},
    {"access_id": "Z_VENDOR_MAINT", "risk_level": "critical", "sod_warning": "SOD-FI-001 conflict with Z_AP_CLERK"}
  ],
  "cart_risk_level": "critical",
  "needs_security_review": true
}
```

**Submit the cart:**

```http
POST /arm/cart/{cart_id}/submit
```

### 5.5 Approval Workflow — MSMP Style

GovernexPlus uses a Multi-Stage, Multi-Path (MSMP) approval engine mirroring SAP GRC's ARM approval workflow.

**Standard approval stages by risk level:**

| Risk Level | Stage 1 | Stage 2 | Stage 3 |
|---|---|---|---|
| LOW | Manager | — | — |
| MEDIUM | Manager | Role Owner | — |
| HIGH | Manager | Role Owner | Security Admin |
| CRITICAL | Manager | Role Owner | Security Admin + CISO |

**Processing an approval decision:**

```http
POST /access-requests/REQ-20260906-00234/approve/STEP-001

{
  "actor_id": "manager@company.com",
  "action": "approve",
  "comments": "Approved. Mary is joining the AP team as of October 1."
}
```

**Available actions:**

| Action | Meaning |
|---|---|
| `approve` | Advance to next stage |
| `reject` | Terminate the request |
| `delegate` | Transfer to another approver (set `delegate_to`) |
| `request_info` | Return to requester for clarification |
| `escalate` | Push to next approval level |

**Self-approval prevention:** The system enforces that the requester cannot approve their own requests. If `actor_id == requester_user_id` on an approve action, a 403 is returned.

**Delegation:**

```http
POST /access-requests/{request_id}/approve/{step_id}

{
  "actor_id": "manager@company.com",
  "action": "delegate",
  "delegate_to": "deputy.manager@company.com",
  "comments": "On leave until Oct 15, delegating to deputy"
}
```

**Auto-hold on critical violations:** When a request contains a critical SoD violation and the approver attempts to approve, the system inserts an automatic hold and routes to the Security Admin stage regardless of the configured workflow. This cannot be bypassed.

**Escalation:** If an approver does not act within the SLA window (configurable per stage, default 48 hours), the system auto-escalates to the next level and sends reminder notifications.

**Conditional stages (risk-based):** The workflow engine evaluates conditions at runtime. A stage marked `condition: "risk_level == 'critical'"` is only inserted when the request's aggregate risk score exceeds the critical threshold.

### 5.6 Inline Risk Preview for Approvers

Approvers see a condensed risk preview inline within the approval task. This includes:

- Traffic light risk rating (red/amber/green)
- Specific SoD violations that would be created
- Usage data: has the user actually used these t-codes before?
- AI recommendation: approve, review, or deny with rationale

The inline preview is served from:

```http
POST /preview-risk
{
  "target_user_id": "TNGUYEN",
  "requested_roles": ["Z_AP_CLERK"]
}
```

### 5.7 Provisioning

Approved requests are automatically sent to the provisioning engine which communicates with the target system via the connector framework.

**Supported provisioning targets:**

| System | Connector | Mechanism |
|---|---|---|
| SAP (production) | `connectors/sap/` | RFC call to SUIM/SU01 |
| SAP (mock/dev) | `connectors/sap/mock_connector.py` | In-memory simulation |
| Azure Active Directory | `connectors/identity/azure_ad.py` | Microsoft Graph API |
| Okta | ITSM connector | Okta Management API |

**Provisioning status flow:**

```
APPROVED → PROVISIONING → PROVISIONED
         └─► PROVISIONING_FAILED (triggers alert + retry)
```

**Manual provisioning fallback:** If automatic provisioning fails after 3 retries, the request enters `PROVISIONING_FAILED` status and a task is created for the helpdesk with exact instructions for manual role assignment.

### 5.8 JML Automation (AC-24)

Joiner/Mover/Leaver automation triggers access request and provisioning events based on HR lifecycle events received from HRIS connectors (Workday, SuccessFactors).

**Joiner event:**

```
HR Event: new_hire (TNGUYEN, Start: 2026-10-01, Dept: Accounts Payable, Position: AP Clerk)
  → JML Manager looks up role template for position "AP Clerk"
  → Creates access request for template roles: ["Z_AP_CLERK", "Z_FI_DISPLAY"]
  → Routes for manager approval with 1-stage fast-track
  → Provisions on approval (before start date)
```

**Mover event:**

```
HR Event: position_change (JSMITH, From: AP Clerk, To: AP Manager)
  → JML Manager computes delta: add ["Z_AP_MANAGER"], remove ["Z_AP_CLERK"]
  → Creates modify_access request with role delta
  → Runs SoD check on combined access
  → Provisions approved changes on effective date
```

**Leaver event:**

```
HR Event: termination (RLOPEZ, Last Day: 2026-09-30)
  → JML Manager immediately disables user account (same-day)
  → Creates remove_access request for all current roles
  → Initiates emergency de-provisioning workflow
  → Sends confirmation to HR and IT
```

---

## 6. Emergency Access — Firefighter/Privileged Access Governor

*Reference codes: AC-30 (FF ID Setup), AC-31 (Request/Approve), AC-32 (Session Mgmt), AC-33 (Controller Review)*

The Privileged Access Governor (branded as Firefighter in GovernexPlus) provides a controlled mechanism for granting elevated SAP access for time-limited emergency purposes while maintaining a complete audit trail.

### 6.1 Firefighter ID Setup

Firefighter IDs are shared or individual elevated SAP user accounts pre-configured with powerful access. They are locked by default and unlocked only for approved emergency sessions.

**Components of a Firefighter ID:**

```
FirefighterID
├── ff_id           : str  — e.g. "FF_FINANCE_01"
├── system          : str  — SAP system ID, e.g. "SAP_PROD"
├── owner_id        : str  — Primary responsible party
├── controller_ids  : List[str] — Users who review session logs
├── allowed_tcodes  : List[str] — Pre-authorized t-codes
├── max_session_hours: float — Maximum session duration (default: 2)
├── requires_ticket : bool  — ServiceNow/ITSM reference required
└── is_active       : bool
```

**Creating a Firefighter ID:**

```http
POST /firefighter/ids

{
  "ff_id": "FF_FINANCE_01",
  "system": "SAP_PROD",
  "description": "Emergency Finance/AP access",
  "owner_id": "finance.manager@company.com",
  "controller_ids": ["internal.audit@company.com", "ciso@company.com"],
  "allowed_tcodes": ["FK01", "FK02", "FB60", "F110", "MIRO", "SE16"],
  "max_session_hours": 4,
  "requires_ticket": true
}
```

### 6.2 Reason Codes

Reason codes enforce vocabulary control over why Firefighter access is being requested. They prevent vague justifications and feed into analytics for abuse detection.

**Pre-configured reason code catalog (`REASON_CODE_CATALOG`):**

| Code | Name | Default Priority | Max Hours |
|---|---|---|---|
| `prod_incident` | Production Incident | CRITICAL | 4 |
| `change_management` | Planned Change | NORMAL | 2 |
| `audit_request` | Audit Investigation | HIGH | 2 |
| `data_correction` | Data Correction | HIGH | 2 |
| `period_close` | Period-End Close | HIGH | 4 |
| `emergency_batch` | Emergency Batch Job | HIGH | 2 |
| `security_incident` | Security Incident Response | CRITICAL | 4 |
| `vendor_escalation` | Vendor Escalation | NORMAL | 1 |

Custom reason codes can be added via:

```http
POST /firefighter/reason-codes

{
  "code": "regulatory_audit",
  "name": "Regulatory Audit Response",
  "default_priority": "HIGH",
  "max_hours": 3,
  "requires_ticket": true,
  "description": "Access required to respond to regulatory examination"
}
```

### 6.3 Request Flow

```
1. User submits FirefighterRequest
        │
        ▼
2. System validates:
   - FF ID exists and is active
   - Reason code is valid
   - Duration within allowed maximum
   - Ticket reference present (if required)
        │
        ▼
3. Request routed to approver(s)
   Priority = CRITICAL → immediate notification (SMS + email)
   Priority = HIGH     → email notification, 30-min SLA
   Priority = NORMAL   → email notification, 4-hour SLA
        │
        ▼
4. Approver acts: approve / deny / conditional_approve
        │
        ▼
5. On approval: SAP account unlocked, session timer starts
```

**Creating a Firefighter request:**

```http
POST /firefighter/requests

{
  "requester_user_id": "JSMITH",
  "requester_name": "John Smith",
  "requester_email": "john.smith@company.com",
  "target_system": "SAP_PROD",
  "firefighter_id": "FF_FINANCE_01",
  "reason_code": "prod_incident",
  "reason": "Month-end payroll run failed — payroll calculation error in PC00_M99_CALC",
  "planned_actions": [
    "Review PA03 payroll control record",
    "Check T549A payroll schema",
    "Restart payroll calculation for period"
  ],
  "business_justification": "400 employees will not receive correct payment unless fixed before midnight",
  "duration_hours": 3,
  "priority": "critical",
  "ticket_reference": "INC0098765"
}
```

### 6.4 Session Management

Once a request is approved, the Firefighter session is initiated with a countdown timer.

**Session status lifecycle:**

```
APPROVED → ACTIVE → COMPLETED
         └─► EXPIRED (timer elapsed without completion)
         └─► TERMINATED (early termination by controller)
```

**Starting a session (after approval):**

```http
POST /firefighter/sessions/{request_id}/start

{
  "user_id": "JSMITH"
}
```

**Response:**

```json
{
  "session_id": "FF-SESSION-20260906-00012",
  "status": "active",
  "ff_id": "FF_FINANCE_01",
  "started_at": "2026-09-06T14:30:00Z",
  "expires_at": "2026-09-06T17:30:00Z",
  "remaining_minutes": 180,
  "sap_user_unlocked": true
}
```

**Extending a session:**

```http
POST /firefighter/sessions/{session_id}/extend

{
  "requested_by": "JSMITH",
  "additional_hours": 1,
  "reason": "Payroll schema requires additional t-code execution"
}
```

Extension requests are routed to the FF controller for approval. Maximum one extension per session.

**Terminating a session early:**

```http
POST /firefighter/sessions/{session_id}/terminate

{
  "terminated_by": "security.admin@company.com",
  "reason": "Work completed"
}
```

On termination or expiration: SAP user account is immediately locked, all open sessions are closed.

### 6.5 Live Monitoring

Controllers can monitor active sessions in real time. The Live Session Monitor page shows all active sessions across all systems with the ability to view the real-time activity log.

```http
GET /firefighter/sessions/active

{
  "active_sessions": [
    {
      "session_id": "FF-SESSION-20260906-00012",
      "user_id": "JSMITH",
      "ff_id": "FF_FINANCE_01",
      "started_at": "2026-09-06T14:30:00Z",
      "remaining_minutes": 127,
      "transaction_log": [
        {"tcode": "PA03", "executed_at": "14:32:15", "system": "SAP_PROD"},
        {"tcode": "PC00_M99_CALC", "executed_at": "14:45:22", "system": "SAP_PROD"}
      ],
      "transaction_count": 2,
      "unauthorized_attempts": 0
    }
  ]
}
```

Unauthorized t-code attempts (t-codes outside the allowed list) trigger an immediate alert to the controller.

### 6.6 Post-Session Review

Within the controller review SLA (configurable, default 24 hours), the assigned controllers must review the session log and provide a sign-off.

```http
GET /firefighter/sessions/{session_id}/review-log

{
  "session_id": "FF-SESSION-20260906-00012",
  "user_id": "JSMITH",
  "duration_minutes": 47,
  "transactions_executed": ["PA03", "T549A", "PC00_M99_CALC"],
  "tables_accessed": ["T549A", "PA0001"],
  "ai_summary": "Session involved payroll schema review and calculation restart. All executed t-codes were within the pre-authorized list. No unauthorized table modifications detected. Payroll recalculation completed successfully.",
  "risk_flags": []
}
```

**Submitting controller review:**

```http
POST /firefighter/sessions/{session_id}/review

{
  "controller_id": "internal.audit@company.com",
  "review_status": "approved",
  "findings": "All actions appropriate and within scope of approved ticket INC0098765",
  "follow_up_required": false
}
```

### 6.7 SAP Operations

The Firefighter module communicates with SAP via the configured connector to perform session management operations:

| Operation | SAP Mechanism | GovernexPlus Call |
|---|---|---|
| Lock user | SU01 BAPI | `connector.lock_user(ff_id)` |
| Unlock user | SU01 BAPI | `connector.unlock_user(ff_id)` |
| Set temp password | SU01 BAPI | `connector.set_password(ff_id, temp_pwd)` |
| Capture t-code log | SM20/SM21 | `connector.get_transaction_log(ff_id, period)` |
| Get active sessions | SM04 | `connector.get_active_sessions()` |

In development environments, `SAP_CONNECTOR_TYPE=sap_mock` uses the `SAPMockConnector` which simulates all operations in-memory without requiring an SAP connection.

### 6.8 Usage Reports and Dashboards

```http
GET /firefighter/analytics/usage-summary?period=30d
GET /firefighter/analytics/by-reason-code
GET /firefighter/analytics/by-user
GET /firefighter/analytics/review-compliance   # % sessions reviewed within SLA
```

### 6.9 Firefighter API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/firefighter/ids` | Create Firefighter ID |
| GET | `/firefighter/ids` | List Firefighter IDs |
| GET | `/firefighter/ids/{ff_id}` | Get Firefighter ID detail |
| POST | `/firefighter/requests` | Submit FF request |
| GET | `/firefighter/requests` | List FF requests |
| POST | `/firefighter/requests/{id}/approve` | Approve/deny FF request |
| POST | `/firefighter/sessions/{request_id}/start` | Start session |
| POST | `/firefighter/sessions/{session_id}/extend` | Request extension |
| POST | `/firefighter/sessions/{session_id}/terminate` | Terminate session |
| GET | `/firefighter/sessions/active` | List active sessions |
| GET | `/firefighter/sessions/{session_id}/review-log` | Get session log |
| POST | `/firefighter/sessions/{session_id}/review` | Submit controller review |
| GET | `/firefighter/reason-codes` | List reason codes |
| POST | `/firefighter/reason-codes` | Create reason code |
| GET | `/firefighter/analytics/usage-summary` | Usage analytics |

---

## 7. Access Certification — UAR

*Reference codes: AC-40 (Campaign Mgmt), AC-41 (Item Generation), AC-42 (Review Process), AC-43 (Revocation)*

Access certification (User Access Review) is the periodic process by which role owners, managers, or business owners certify that each user's access is still appropriate and required. GovernexPlus replaces SAP GRC UAR with a database-backed campaign engine supporting multiple reviewers, bulk decisions, escalation, and automated revocation.

### 7.1 Campaign Types

| Type | Description |
|---|---|
| `user_access` | Manager reviews each direct report's complete access profile |
| `role_membership` | Role owner reviews all users assigned to their role |
| `sensitive_access` | Security team reviews users with sensitive/critical access |
| `sod_violations` | Security reviews all open SoD violations |
| `manager` | Manager certification of their team's access |

### 7.2 Creating a Campaign

```http
POST /certification/campaigns

{
  "name": "Q3 2026 Quarterly Access Review",
  "description": "Mandatory quarterly review of all user access across SAP production systems",
  "campaign_type": "user_access",
  "owner_id": "security.admin@company.com",
  "owner_name": "Security Administration",
  "start_date": "2026-09-15T00:00:00Z",
  "end_date": "2026-09-30T23:59:59Z",
  "included_systems": ["SAP_PROD", "SAP_HR"],
  "included_departments": ["Finance", "Procurement", "HR"],
  "risk_threshold": 30.0,
  "include_sod_only": false
}
```

**Campaign parameters:**

- `risk_threshold`: Only include user-role assignments where the Risk Intelligence Engine risk score exceeds this value (0–100). Set `0` to include all access.
- `include_sod_only`: When `true`, only include access items that have at least one SoD violation.
- `included_departments`: Scope the campaign to specific org units.

### 7.3 Item Generation

On campaign creation, the system automatically generates certification review items. Each item represents one user-role assignment that requires a decision.

**Generation logic:**

1. Query all active user-role assignments for the configured scope
2. Retrieve the last Risk Intelligence Engine risk score for each user-role combination
3. Filter by `risk_threshold` and `include_sod_only` if configured
4. Assign each item to the appropriate reviewer:
   - `user_access` campaign: reviewer = user's direct manager
   - `role_membership` campaign: reviewer = role owner
   - `sensitive_access` campaign: reviewer = security admin

**Getting campaign items:**

```http
GET /certification/campaigns/{campaign_id}/items?reviewer_id=manager@company.com

{
  "total": 47,
  "reviewed": 12,
  "pending": 35,
  "items": [
    {
      "item_id": "CERT-ITEM-001",
      "user_id": "JSMITH",
      "user_name": "John Smith",
      "role_id": "Z_VENDOR_MAINT",
      "role_name": "Vendor Master Maintenance",
      "risk_score": 87.4,
      "risk_level": "critical",
      "sod_violations": ["SOD-FI-001", "SOD-FI-002"],
      "last_used": "2026-08-30",
      "days_since_use": 7,
      "status": "pending"
    }
  ]
}
```

### 7.4 Review Process

**Single item decision:**

```http
POST /certification/campaigns/{campaign_id}/items/{item_id}/certify

{
  "reviewer_id": "manager@company.com",
  "action": "certify",
  "comments": "John still needs this access for the vendor onboarding project running through Q4."
}
```

```http
POST /certification/campaigns/{campaign_id}/items/{item_id}/certify

{
  "reviewer_id": "manager@company.com",
  "action": "revoke",
  "comments": "John moved to AP Manager role. Vendor master maintenance is no longer required."
}
```

**Available actions:**

| Action | Description |
|---|---|
| `certify` | Confirm access is appropriate and still needed |
| `revoke` | Mark for de-provisioning |
| `delegate` | Transfer review to another reviewer |
| `abstain` | Mark as cannot review (escalates automatically) |

**Bulk certification:**

```http
POST /certification/campaigns/{campaign_id}/bulk-certify

{
  "reviewer_id": "manager@company.com",
  "item_ids": ["CERT-ITEM-015", "CERT-ITEM-016", "CERT-ITEM-017"],
  "comments": "Bulk certified - all confirmed appropriate for current roles"
}
```

### 7.5 Revocation Workflow

Items marked `revoke` trigger an automated de-provisioning workflow:

```
REVOKE decision recorded
  │
  ▼
De-provisioning task created
  │
  ▼
Provisioning engine calls connector:
  SAP: Remove role from SU01
  Azure AD: Remove group membership
  Okta: Remove application assignment
  │
  ▼
Confirmation email to reviewer and user
  │
  ▼
Risk Intelligence Engine re-analysis for affected user
  │
  ▼
Certification item status → COMPLETED
```

If automatic de-provisioning fails, a manual task is created for the helpdesk with exact instructions.

### 7.6 Campaign Dashboard and Escalation

```http
GET /certification/campaigns/{campaign_id}/stats

{
  "campaign_id": "CAMP-001",
  "progress_pct": 63.8,
  "total_items": 470,
  "certified": 300,
  "revoked": 45,
  "pending": 125,
  "overdue": 32,
  "days_remaining": 8,
  "revocation_rate": 13.0,
  "status": "in_progress"
}
```

**Escalation:** Items that are not reviewed within the campaign window are automatically escalated to the campaign owner. If still not reviewed 48 hours before campaign close, they are routed to the security admin for decision.

**Auto-certify/auto-revoke rules:** Administrators can configure automatic decisions for specific conditions:

- Auto-certify: access used in the last 30 days
- Auto-revoke: user has been inactive for 90+ days

### 7.7 Mitigating Control Certification

When a certified access item has an associated mitigation control, the certification additionally asks the reviewer to confirm the control is still operating effectively. This creates a dual-sign-off: the manager certifies the access is needed, and the control owner certifies the control is in place.

```http
GET /certification/campaigns/{campaign_id}/items/{item_id}

{
  ...
  "mitigation_control": {
    "control_id": "MIT-FI-AP-001",
    "control_name": "Monthly AP Payment Review by CFO",
    "last_tested": "2026-08-31",
    "test_result": "effective",
    "requires_control_certification": true
  }
}
```

### 7.8 Certification API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/certification/campaigns` | Create campaign |
| GET | `/certification/campaigns` | List campaigns |
| GET | `/certification/campaigns/{id}` | Get campaign detail |
| PUT | `/certification/campaigns/{id}/launch` | Launch campaign |
| GET | `/certification/campaigns/{id}/items` | List review items |
| POST | `/certification/campaigns/{id}/items/{item_id}/certify` | Submit decision |
| POST | `/certification/campaigns/{id}/bulk-certify` | Bulk certify |
| GET | `/certification/campaigns/{id}/stats` | Campaign dashboard |
| POST | `/certification/campaigns/{id}/close` | Close campaign |

---

## 8. Role Engineering — Role Design Studio

*Reference codes: AC-50 (Role Design), AC-51 (Role Mining), AC-52 (Role Lifecycle)*

### 8.1 Role Design with Inline SoD Check

The Role Designer provides a visual workspace for building new SAP roles with real-time SoD validation on every t-code addition.

**Workflow:**

1. Open Role Designer at `/roles/designer`
2. Add t-codes to the role definition one by one
3. After each addition, the frontend calls `POST /ara/simulate/access` with the current t-code set as both "current" and "requested", displaying any intra-role conflicts
4. Save the role definition
5. Run a full role analysis: `GET /ara/analyze/role/{role_id}`

```http
POST /roles

{
  "role_name": "Z_AP_CLERK_V2",
  "description": "Accounts Payable Clerk - clean version without vendor master",
  "transaction_codes": ["FB60", "MIRO", "MIR4", "FBL1N", "FBL5N"],
  "business_process": "FI",
  "risk_level": "low"
}
```

A role that contains internal SoD conflicts (e.g., both FK01 and F110) is flagged `risk_level: high` and blocked from assignment until conflicts are resolved.

### 8.2 Role Mining from Usage Data

Role mining analyzes historical transaction usage logs to identify natural groupings of t-codes that users actually use together. These clusters become candidate role definitions.

```http
POST /roles/mine

{
  "source": "audit_log",
  "period_days": 90,
  "min_user_count": 3,
  "min_usage_frequency": 5,
  "business_process_filter": ["FI", "MM"]
}
```

**Response:** A list of candidate roles ordered by cohesion score:

```json
{
  "candidate_roles": [
    {
      "candidate_id": "MINE-001",
      "suggested_name": "AP_Invoice_Entry_Pattern",
      "tcodes": ["FB60", "MIRO", "MIR4", "FBL1N"],
      "user_count": 12,
      "avg_frequency": 23.4,
      "cohesion_score": 0.87,
      "conflicts": [],
      "recommendation": "Good candidate - no internal SoD conflicts"
    }
  ]
}
```

### 8.3 Role Design Studio — Business Role Management

GovernexPlus supports the SAP role hierarchy:

| Role Type | Description |
|---|---|
| `single` | Direct assignment of t-codes and auth objects |
| `composite` | Container of multiple single roles |
| `derived` | Inherits from parent, overrides org-level fields (cost center, company code) |

```http
GET /roles/business-roles
GET /roles/business-roles/{role_id}
POST /roles/business-roles
PUT /roles/business-roles/{role_id}
DELETE /roles/business-roles/{role_id}
```

### 8.4 Role Comparison and Consolidation

Compare two roles to identify overlap and redundancy:

```http
POST /roles/compare

{
  "role_a": "Z_AP_CLERK",
  "role_b": "Z_AP_CLERK_V2"
}
```

**Response:**

```json
{
  "shared_tcodes": ["FB60", "MIRO", "MIR4"],
  "only_in_a": ["FK01", "FK02"],
  "only_in_b": ["FBL1N", "FBL5N"],
  "overlap_pct": 60.0,
  "recommendation": "Z_AP_CLERK can be replaced by Z_AP_CLERK_V2 after removing FK01/FK02 assignments from affected users"
}
```

Role consolidation creates a migration plan:

```http
POST /roles/consolidate

{
  "source_role": "Z_AP_CLERK",
  "target_role": "Z_AP_CLERK_V2",
  "affected_users": ["JSMITH", "MBROWN"],
  "effective_date": "2026-10-01"
}
```

### 8.5 Role Drift Detection

Role drift occurs when a role's actual assignments in the target system diverge from the GovernexPlus role catalog. The drift detector compares role definitions in the platform against the live SAP role content.

```http
GET /drift/roles?system=SAP_PROD

{
  "drifted_roles": [
    {
      "role_id": "Z_AP_CLERK",
      "platform_tcodes": ["FB60", "MIRO"],
      "live_tcodes": ["FB60", "MIRO", "FK01"],
      "extra_tcodes": ["FK01"],
      "drift_severity": "high",
      "sod_created_by_drift": ["SOD-FI-002"]
    }
  ]
}
```

Role drift alerts are generated automatically by the continuous monitoring engine when a sync with the SAP system detects discrepancies.

### 8.6 Role Redesign Copilot (AI)

The AI assistant (`core/ai/assistant.py`) provides natural-language role redesign guidance:

```http
POST /ai/assistant/query

{
  "query": "How can I redesign Z_FINANCE_MANAGER to eliminate the SOD-FI-001 violation without removing all payment visibility?"
}
```

**Response:**

```json
{
  "recommendation": "Remove transaction F110 (payment run execution) from Z_FINANCE_MANAGER. Replace with F110 read-only access via a new role Z_FI_PAYMENT_DISPLAY that includes only F110 with display authorization (ACTVT=03). This eliminates SOD-FI-001 while preserving payment visibility. Affected users: 3 managers who currently use F110 for payment status checking — they will not lose visibility, only execution capability."
}
```

---

## 9. Continuous Monitoring

GovernexPlus runs continuous monitoring jobs that detect new violations as they are introduced, rather than waiting for the next scheduled scan.

### 9.1 New SoD Conflict Detection

Trigger: Role assignment changes in SAP (via connector sync or manual import)

When a new role is assigned to a user, the system immediately:
1. Fetches the user's complete current role set
2. Adds the new role's t-codes to the analysis input
3. Runs Risk Intelligence Engine analysis
4. Persists any new violations
5. Sends immediate notification to the user's manager and the security team if critical

### 9.2 Critical Access Alerts

Real-time alerts are generated when:
- A user gains a CRITICAL-rated access combination
- A Basis user gains both user administration and role administration
- Treasury payment access is combined with bank account management

Alerts are sent via the notification delivery engine (`core/notifications/delivery.py`) to configured channels: email, Slack, MS Teams, ServiceNow incident creation.

### 9.3 Excessive Privilege Detection

The Risk Intelligence Engine behavioral analytics tracks t-code usage. Users who have significantly more access than they actually use are flagged for access rightsizing:

```http
GET /ara/analytics/excessive-privilege?unused_days=90&min_role_count=5
```

### 9.4 Dormant and Orphan User Detection

- **Dormant:** Active accounts with no login in `N` days (configurable)
- **Orphan:** User accounts with no corresponding employee record in the HRIS

```http
GET /risk-analysis/dormant-users?days_inactive=90
GET /users/orphan-accounts
```

---

## 10. Reports and Dashboards

### 10.1 Risk Dashboard

Available at: `/risk` frontend route | API: `GET /ara/analytics/summary`

Key metrics displayed:
- Total violations by severity (critical/high/medium/low)
- Aggregate portfolio risk score (0–100)
- Top 10 high-risk users
- Risk trend (30-day chart)
- Department risk heatmap

### 10.2 Violation Trends

```http
POST /ara/analytics/trend

{
  "from_date": "2026-06-01T00:00:00Z",
  "to_date": "2026-09-06T23:59:59Z",
  "granularity": "weekly"
}
```

Returns time-series data for rendering the violations trend chart. Supports `daily`, `weekly`, and `monthly` granularity.

### 10.3 Org-Level Ranking

```http
GET /ara/analytics/departments
GET /ara/analytics/heatmap/user-category?top_n=20
GET /ara/analytics/heatmap/role-severity?top_n=20
```

### 10.4 Certification Progress

```http
GET /certification/campaigns/{id}/stats
```

Shows completion percentage, certify/revoke counts, overdue items, and days remaining.

### 10.5 Firefighter Usage

```http
GET /firefighter/analytics/usage-summary
GET /firefighter/analytics/review-compliance
```

### 10.6 Economic Exposure

```http
GET /ara/analytics/economic-exposure

{
  "total_exposure_usd": 4250000,
  "by_severity": {
    "critical": {"count": 12, "exposure_usd": 3100000},
    "high": {"count": 34, "exposure_usd": 950000}
  },
  "top_risk_categories": ["vendor_fraud", "payment_manipulation", "payroll_manipulation"]
}
```

---

## 11. Configuration Reference

### 11.1 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SAP_CONNECTOR_TYPE` | `sap_mock` | Connector type: `sap_mock` or `sap_rfc` |
| `SAP_HOST` | `localhost` | SAP application server hostname |
| `SAP_CLIENT` | `100` | SAP client number |
| `SAP_SYSTEM_NAME` | `SAP_DEV` | SAP system identifier |
| `RISK_SCAN_ENABLED` | `true` | Enable/disable scheduled Risk Intelligence Engine scans |
| `RISK_SCAN_CRON` | `0 2 * * *` | Cron schedule for nightly risk scan |
| `FF_DEFAULT_MAX_HOURS` | `4` | Default maximum firefighter session duration |
| `FF_REVIEW_SLA_HOURS` | `24` | Controller review SLA in hours |
| `FF_APPROVAL_SLA_CRITICAL_MIN` | `15` | Approval SLA for CRITICAL priority (minutes) |
| `FF_APPROVAL_SLA_HIGH_MIN` | `30` | Approval SLA for HIGH priority (minutes) |
| `CERT_ESCALATION_HOURS` | `48` | Hours before campaign close to escalate unreviewed items |
| `DORMANT_USER_DAYS` | `90` | Days of inactivity to flag as dormant |
| `JWT_SECRET` | (auto in dev) | JWT signing secret — required in production |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (restrict in production) |

### 11.2 Complete AC API Endpoint Table

| Method | Path | Sub-Module | Description |
|---|---|---|---|
| POST | `/ara/analyze/user` | Risk Intelligence Engine | User risk analysis |
| POST | `/ara/analyze/batch` | Risk Intelligence Engine | Batch analysis |
| GET | `/ara/analyze/role/{id}` | Risk Intelligence Engine | Role risk analysis |
| POST | `/ara/simulate/access` | Risk Intelligence Engine | Pre-provisioning simulation |
| POST | `/ara/simulate/role-change` | Risk Intelligence Engine | Role change simulation |
| GET | `/ara/sod/rules` | Risk Intelligence Engine | List SoD rules |
| POST | `/ara/sod/rules` | Risk Intelligence Engine | Create rule |
| PUT | `/ara/sod/rules/{id}/toggle` | Risk Intelligence Engine | Enable/disable rule |
| GET | `/ara/mitigation/controls` | Risk Intelligence Engine | List mitigation controls |
| POST | `/ara/mitigation/controls` | Risk Intelligence Engine | Create control |
| POST | `/ara/mitigation/assign` | Risk Intelligence Engine | Assign control to risk |
| POST | `/ara/mitigation/exceptions/request` | Risk Intelligence Engine | Request exception |
| GET | `/ara/analytics/summary` | Risk Intelligence Engine | Executive summary |
| POST | `/ara/analytics/trend` | Risk Intelligence Engine | Risk trend |
| GET | `/ara/analytics/departments` | Risk Intelligence Engine | Dept risk ranking |
| GET | `/ara/analytics/economic-exposure` | Risk Intelligence Engine | Economic quantification |
| GET | `/catalog/roles` | Access Lifecycle Manager | Role catalog |
| POST | `/preview-risk` | Access Lifecycle Manager | Pre-request risk preview |
| POST | `/access-requests/` | Access Lifecycle Manager | Create request |
| POST | `/access-requests/{id}/submit` | Access Lifecycle Manager | Submit request |
| GET | `/access-requests/{id}` | Access Lifecycle Manager | Get request |
| GET | `/access-requests/approvals/pending` | Access Lifecycle Manager | Pending approvals |
| POST | `/access-requests/{id}/approve/{step}` | Access Lifecycle Manager | Process approval |
| POST | `/access-requests/model-user` | Access Lifecycle Manager | Model user copy |
| POST | `/arm/cart/items` | Access Lifecycle Manager | Add to shopping cart |
| POST | `/arm/cart/{id}/submit` | Access Lifecycle Manager | Submit cart |
| POST | `/firefighter/requests` | Privileged Access Governor | Submit FF request |
| POST | `/firefighter/requests/{id}/approve` | Privileged Access Governor | Approve FF request |
| POST | `/firefighter/sessions/{id}/start` | Privileged Access Governor | Start session |
| POST | `/firefighter/sessions/{id}/extend` | Privileged Access Governor | Extend session |
| POST | `/firefighter/sessions/{id}/terminate` | Privileged Access Governor | Terminate session |
| GET | `/firefighter/sessions/active` | Privileged Access Governor | Live session monitor |
| POST | `/firefighter/sessions/{id}/review` | Privileged Access Governor | Controller review |
| POST | `/certification/campaigns` | UAR | Create campaign |
| GET | `/certification/campaigns/{id}/items` | UAR | List review items |
| POST | `/certification/campaigns/{id}/items/{item}/certify` | UAR | Certify/revoke |
| POST | `/certification/campaigns/{id}/bulk-certify` | UAR | Bulk decision |
| POST | `/roles` | Role Design Studio | Create role |
| POST | `/roles/mine` | Role Design Studio | Role mining |
| POST | `/roles/compare` | Role Design Studio | Role comparison |
| GET | `/drift/roles` | Role Design Studio | Role drift detection |
| GET | `/risk-analysis/dormant-users` | Monitoring | Dormant users |
| GET | `/users/orphan-accounts` | Monitoring | Orphan accounts |
| GET | `/reports/access-risk` | Reports | Risk report |
| GET | `/reports/certification` | Reports | Certification report |
| GET | `/reports/firefighter-usage` | Reports | Privileged Access Governor usage report |
