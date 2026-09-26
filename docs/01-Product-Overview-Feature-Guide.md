# GovernexPlus — Product Overview & Feature Guide

**Version:** 2.0 | **Date:** September 2026 | **Classification:** Public

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Platform Architecture](#2-platform-architecture)
3. [Four Pillars Overview](#3-four-pillars-overview)
   - 3.1 Access Control (AC)
   - 3.2 Risk Management (RM)
   - 3.3 Process Control (PC)
   - 3.4 Audit Management (AM)
4. [Cross-Module Integration (XI)](#4-cross-module-integration-xi)
5. [AI Intelligence Layer](#5-ai-intelligence-layer)
6. [Connectors & Integrations](#6-connectors--integrations)
7. [Non-Functional Capabilities](#7-non-functional-capabilities)
8. [Platform Statistics](#8-platform-statistics)
9. [Licensing & Deployment Models](#9-licensing--deployment-models)

---

## 1. Executive Summary

### What Is GovernexPlus?

GovernexPlus is an enterprise-grade, AI-powered Governance, Risk, and Compliance (GRC) platform purpose-built for organizations running SAP landscapes. It delivers end-to-end coverage of access governance, risk management, process control, and audit management through a single, unified SaaS or on-premise deployment — replacing the fragmented, expensive, and aging SAP GRC Access Control 12.0 suite with a modern, open, and extensible alternative.

GovernexPlus is not a bolt-on compliance tool. It is a full GRC operating system designed to be the authoritative system of record for every governance, risk, and audit function across the enterprise. It connects directly to SAP S/4HANA, ECC 6.0, BTP, SuccessFactors, and adjacent identity ecosystems (Azure AD, Okta, Workday) to provide real-time risk visibility, automated control enforcement, and intelligent audit orchestration.

### Who Is It For?

GovernexPlus serves four primary personas:

| Persona | What They Do in GovernexPlus |
|---|---|
| **SAP Security & GRC Teams** | SoD analysis, access requests, firefighter management, role engineering, access certification |
| **Risk Managers** | Risk register, KRI monitoring, incident management, risk heatmaps, response planning |
| **Process Control Teams** | Control library, control testing, deficiency tracking, SOX sign-off, CCM |
| **Internal & External Auditors** | Audit universe, engagement lifecycle, workpapers, findings, evidence management |

Secondary personas include IT operations teams (connector management, system administration), C-suite stakeholders (board-level dashboards, committee reports), and platform administrators (multi-tenant management, user provisioning).

### Why GovernexPlus Exists — The SAP GRC Crisis

SAP announced that GRC Access Control 12.0 will reach **end of mainstream maintenance on December 31, 2027**, with extended maintenance available only until 2030 at significant premium. Organizations running SAP GRC AC 12.0 face:

- **Mandatory migration** within 3–4 years with no direct upgrade path from AC 12.0 to a modern SAP alternative
- **Escalating maintenance costs** as SAP shifts investment to cloud-only offerings
- **Functional gaps** — SAP GRC AC was designed for monolithic ECC landscapes and does not natively support multi-cloud identity, behavioral analytics, AI-assisted remediation, or unified GRC (risk + audit are separate products)
- **Prohibitive SAP cloud pricing** — SAP's own cloud GRC solutions carry enterprise-tier pricing with long contractual commitments and limited customization

GovernexPlus provides a **proven migration path** from SAP GRC AC 12.0 with a dedicated Migration Copilot that reads existing ruleset exports, role assignments, and control configurations, dramatically reducing migration effort. Organizations can run GovernexPlus in parallel with SAP GRC AC during a transition period, then cut over cleanly.

### Strategic Value Proposition

GovernexPlus delivers five strategic advantages over incumbent solutions:

1. **Usage-Aware Risk Scoring**: Unlike SAP GRC, which flags every theoretical SoD violation equally, GovernexPlus layers behavioral analytics on top of rule-based analysis. A user who holds two conflicting transaction codes but has never executed either in 12 months receives a materially lower risk score than someone who executes both weekly. This reduces false positives by 40–70%, allowing security teams to focus remediation effort where it matters.

2. **Unified GRC**: Access control, risk management, process control, and audit management share a single data model, a single org hierarchy, and a single risk taxonomy. A finding in an audit automatically creates a deficiency in process control, which links to the underlying risk in the risk register, which traces to the SoD violation that triggered the audit. No manual re-keying. No reconciliation between siloed systems.

3. **AI-Native Architecture**: Four embedded AI engines (GRC Assistant, Risk Intelligence, Remediation Advisor, NLP Engine) provide narrative-quality explanations of every risk, automated remediation recommendations, role redesign proposals, and intelligent attention prioritization. These are not bolted-on chatbots — they are integrated into the core workflow engine.

4. **SaaS Economics**: GovernexPlus delivers SAP GRC AC-equivalent functionality at 30–60% lower total cost of ownership through cloud-native multi-tenancy, consumption-based licensing, and elimination of expensive on-premise infrastructure for smaller organizations.

5. **Open Architecture**: REST API-first design with 938 documented endpoints, webhook support, and standard connector framework means GovernexPlus integrates with any ITSM, SIEM, HRMS, or identity platform — not just SAP's ecosystem.

---

## 2. Platform Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GOVERNEXPLUS PLATFORM                         │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    FRONTEND LAYER                            │    │
│  │   React 18 + TypeScript + Vite + Tailwind CSS               │    │
│  │   120+ pages | Dark mode | i18n (EN/AR) | WCAG 2.1 AA       │    │
│  └────────────────────────┬────────────────────────────────────┘    │
│                            │ HTTPS / REST                             │
│  ┌─────────────────────────▼──────────────────────────────────┐    │
│  │                    API GATEWAY LAYER                         │    │
│  │   FastAPI | 938 routes | JWT Auth | Rate Limiting            │    │
│  │   Tenant Middleware | CORS | Audit Logging                   │    │
│  └──────┬──────────┬──────────┬──────────┬──────────┬──────────┘    │
│         │          │          │          │          │                 │
│  ┌──────▼──┐ ┌─────▼──┐ ┌────▼───┐ ┌───▼────┐ ┌──▼─────┐         │
│  │   AC    │ │   RM   │ │   PC   │ │   AM   │ │   AI   │         │
│  │ Access  │ │  Risk  │ │Process │ │ Audit  │ │ Engine │         │
│  │ Control │ │  Mgmt  │ │Control │ │  Mgmt  │ │ Layer  │         │
│  └──────┬──┘ └─────┬──┘ └────┬───┘ └───┬────┘ └──┬─────┘         │
│         └──────────┴──────────┴─────────┴──────────┘                │
│                            │ SQLAlchemy ORM                           │
│  ┌─────────────────────────▼──────────────────────────────────┐    │
│  │                    DATA LAYER                                │    │
│  │   PostgreSQL (prod) | SQLite (dev)                          │    │
│  │   81 tables | Alembic migrations | Tenant-scoped ORM        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    CONNECTOR LAYER                           │    │
│  │   SAP RFC | Azure AD | Okta | Workday | SuccessFactors      │    │
│  │   ServiceNow | LDAP | Custom REST                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

#### Backend

| Component | Technology | Version | Purpose |
|---|---|---|---|
| API Framework | FastAPI | 0.111+ | High-performance async REST API |
| ORM | SQLAlchemy | 2.0+ | Database abstraction + tenant scoping |
| Migrations | Alembic | 1.13+ | Schema versioning |
| Auth | PyJWT + passlib/bcrypt | Latest | JWT token issuance + password hashing |
| Rate Limiting | slowapi | 0.1.9+ | Per-endpoint rate controls |
| Background Jobs | APScheduler | 3.10+ | Scheduled analysis, certification sweeps |
| SAP Connector | pyrfc / mock | Latest | RFC-based SAP system calls |
| Task Queue | Async + BackgroundTasks | — | Async violation persistence, notifications |
| Config | python-decouple | — | Environment-based configuration |

#### Frontend

| Component | Technology | Version | Purpose |
|---|---|---|---|
| UI Framework | React | 18.x | Component-based UI |
| Language | TypeScript | 5.x | Type-safe development |
| Build Tool | Vite | 5.x | Fast dev server + production bundling |
| Styling | Tailwind CSS | 3.x | Utility-first CSS with dark mode |
| State | Zustand | 4.x | Lightweight global state |
| Data Fetching | React Query (TanStack) | 5.x | Server state caching |
| Charts | Recharts | 2.x | Risk heatmaps, trend charts |
| i18n | react-i18next | 13.x | EN/AR bilingual support |
| Testing | Vitest + Playwright | — | Unit + E2E testing |

#### Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| Containerization | Docker + Docker Compose | Service packaging |
| Web Server | Nginx | Reverse proxy + static serving |
| Database (prod) | PostgreSQL 15+ | Primary data store |
| Database (dev) | SQLite | Zero-setup local development |
| Secrets | Environment variables | JWT secret, DB credentials, API keys |
| Logging | Python logging + audit trail | Structured logs + compliance audit log |

### 2.3 Multi-Tenant Architecture

GovernexPlus implements database-level multi-tenancy using a shared schema with automatic tenant scoping:

- Every database table containing tenant-specific data has a `tenant_id` column
- A `ContextVar`-based tenant context is set at request ingress by the tenant middleware
- All SQLAlchemy ORM queries automatically apply `WHERE tenant_id = :current_tenant` via a custom session factory
- INSERT operations automatically stamp `tenant_id` on every new record
- Cross-tenant writes are prevented at the ORM layer and raise an explicit exception
- Platform administrators with the `platform_admin` role can read across tenants for support purposes, and every such cross-tenant access is logged to the audit trail

### 2.4 Security Architecture

```
Request → CORS Check → Rate Limiter → JWT Verification → Tenant Context
        → Role Authorization → Business Logic → Tenant-Scoped DB Query
        → Audit Log Write → Response
```

Key security controls:

- **JWT-only identity**: The `X-User-ID`, `X-User-Roles`, and `X-Is-Admin` HTTP headers are explicitly ignored. User identity is derived solely from the verified JWT signature. This prevents header spoofing attacks.
- **Token blacklisting**: Revoked tokens are maintained in an in-memory cache backed by the audit log, preventing reuse after logout or forced expiry
- **Password security**: bcrypt hashing with configurable work factor; password history enforcement; complexity rules
- **Account lockout**: Configurable failed attempt threshold (default: 5) with automatic unlock or admin-unlock
- **MFA**: TOTP-based two-factor authentication for all user accounts
- **Audit trail**: Every state-changing operation writes a structured audit record with user, tenant, action, resource, timestamp, and IP address

---

## 3. Four Pillars Overview

GovernexPlus is organized around four functional pillars that map directly to the four major domains of enterprise GRC. Each pillar can be licensed and operated independently, but they deliver maximum value when operated together through the Cross-Module Integration (XI) framework.

### 3.1 Access Control (AC)

The Access Control pillar is the largest and most feature-rich pillar in GovernexPlus. It encompasses everything required to manage user access to SAP systems and adjacent platforms — from initial access requests through ongoing certification, emergency access, and role engineering.

#### 3.1.1 Segregation of Duties (SoD) Rule Library

GovernexPlus ships with a **128-rule built-in SoD library** covering the full range of SAP functional modules:

| Module | Description | Rule Count |
|---|---|---|
| FI | Financial Accounting | 22 |
| MM | Materials Management | 18 |
| SD | Sales & Distribution | 14 |
| HR | Human Resources & Payroll | 16 |
| BA | Basis & Administration | 12 |
| TR | Treasury | 10 |
| AA | Asset Accounting | 8 |
| WM | Warehouse Management | 8 |
| QM | Quality Management | 6 |
| PM | Plant Maintenance | 6 |
| PS | Project System | 5 |
| XP | Cross-Process | 3 |

Each rule defines:
- **Rule ID**: Unique identifier (system rules: `FI-001` through `XP-003`; custom rules: `Z-xxx`)
- **Risk Name**: Plain-language name (e.g., "Post and Approve Vendor Invoices")
- **Business Process**: The process the rule protects
- **Conflicting Function Pair A/B**: The two SAP functions that cannot coexist
- **Transaction Code Lists**: Specific T-codes that constitute each function
- **Authorization Object Lists**: SAP auth objects that confer each function
- **Severity**: Critical / High / Medium / Low
- **Regulatory Mapping**: SOX, GDPR, HIPAA, ISO 27001 framework references
- **Remediation Guidance**: AI-generated and human-authored remediation steps

The rule library is **idempotent** — existing or custom rules are never overwritten by system upgrades. Organizations can extend the library with Z-transaction custom rules at any time.

Two rule engines operate in parallel: the core `RuleEngine` (for access requests and inline checks) and the ARA `RulesEngine` (for full risk analysis with usage context). Both are fed from the same `SoDRulesetLibrary` via bridge modules, ensuring consistency.

#### 3.1.2 Risk Intelligence Engine (ARA)

The Risk Intelligence Engine module is the analytical heart of the Access Control pillar. It evaluates every user-role-permission combination against the SoD rule library and produces a risk profile for each user, role, and organizational unit.

**Risk Scoring Model:**

GovernexPlus employs a three-dimensional risk score:

```
Risk Score = (Base Rule Score × Severity Weight)
           + (Context Modifier: org unit sensitivity, system criticality)
           + (Usage Modifier: frequency of transaction execution, last usage date)
```

This contrasts sharply with SAP GRC AC, which applies a flat risk score based solely on rule match. The GovernexPlus usage modifier means that dormant violations — where a user theoretically holds conflicting access but has never exercised it — are scored proportionally lower, allowing security teams to prioritize active violations.

**Analysis Types:**

- **User-Level Analysis**: Full risk profile for a single user across all their roles and authorizations
- **Role-Level Analysis**: Identify which roles contain inherent SoD conflicts (role-level risk)
- **Cross-Role Analysis**: Identify SoD conflicts that only materialize when specific roles are combined
- **What-If Simulation**: Model the risk impact of adding or removing a role before committing the change
- **Org-Level Ranking**: Rank organizational units (branch, department, company code, plant) by aggregate risk exposure
- **Batch Analysis**: Schedule full-landscape analysis nightly or on-demand

**Output Artifacts:**

- Violation detail records (persisted to DB for trend analysis)
- Risk heatmap (org unit × severity matrix)
- Top violators report
- Role risk inventory
- Remediation priority queue

[Screenshot: Risk Intelligence Engine Dashboard showing risk heatmap with violation counts by severity and organizational unit]

#### 3.1.3 Access Lifecycle Manager (ARM)

The Access Lifecycle Manager provides a self-service portal for users to request SAP access, with multi-stage approval workflows and inline SoD risk evaluation.

**Shopping Cart Model:**

Users select roles and authorizations from a catalog (browsable and searchable), add them to a "shopping cart," and submit a single request covering multiple items. The system immediately runs an inline SoD check against the user's existing access plus the requested items, and presents a risk summary to both the requestor and the approvers.

**Approval Workflows:**

Workflows are configurable per:
- Access type (role assignment, authorization object, firefighter ID)
- Risk level (auto-approve low risk, require security review for high risk)
- Organizational scope (regional managers for local requests, global GRC for sensitive access)
- System (SAP production vs. test vs. development)

Workflow stages include:
1. Manager approval (configurable as optional for low-risk)
2. Resource/role owner approval
3. Security review (required when SoD violation detected)
4. Provisioning execution (automatic or manual)
5. Post-provisioning confirmation

**Escalation & Delegation:**

- Configurable escalation timers (e.g., escalate to manager's manager after 48 hours)
- Approver delegation with date ranges (e.g., "delegate to Jane Smith July 15–31")
- Approval inbox with bulk approve/reject capability
- Mobile-optimized approval interface

**Provisioning Integration:**

Once approved, GovernexPlus can execute provisioning directly via:
- SAP RFC connector (role assignment/removal in target systems)
- Azure AD group management
- Okta group/profile push
- ServiceNow ticket creation (for manual provisioning workflows)

[Screenshot: New Access Request page with shopping cart, role search, and inline SoD risk indicator]

#### 3.1.4 Firefighter / Privileged Access Governor (EAM)

The Firefighter module provides controlled, time-limited emergency access to privileged SAP functions, replacing the risky practice of sharing superuser credentials.

**Firefighter ID Management:**

- Define firefighter IDs in SAP systems with broad but audited authority
- Assign permanent owners (ID owners responsible for usage review)
- Assign controllers (approvers of firefighter sessions)
- Configure reason code libraries (valid justifications for emergency access)
- Set time limits (default: 4 hours, configurable up to 72 hours)

**Request & Approval Flow:**

1. User submits firefighter access request with business justification and reason code
2. Controller receives real-time notification (email + in-platform)
3. Controller approves or rejects with comments
4. System activates firefighter ID in SAP for the approved duration
5. User executes emergency task under firefighter ID
6. System deactivates ID at expiry or upon user check-out
7. Controller reviews session activity log within 24 hours (configurable)
8. ID owner conducts periodic review of all session logs

**Live Session Monitoring:**

During an active firefighter session, supervisors can view:
- Active user identity and session duration
- Transaction codes executed in real-time
- Document numbers created or changed
- Alert triggers (e.g., posting above threshold, table maintenance)

**Post-Session Audit:**

Every session generates a complete activity log including:
- All T-codes executed with timestamps
- Documents created, changed, or deleted
- Authorization objects accessed
- Session duration and idle periods

The Activity Analysis AI engine reviews session logs automatically and flags:
- Transactions not consistent with stated reason code
- High-value postings requiring follow-up review
- Access to sensitive tables (USR02, MARA, PA0008, etc.)

[Screenshot: Live Session Monitor showing active firefighter session with real-time T-code execution log]

#### 3.1.5 Access Certification (User Access Review — UAR)

The Certification module automates the periodic review of user access rights, replacing spreadsheet-based UAR processes with a structured, auditable workflow.

**Campaign Types:**

- **Full Landscape Campaign**: All users, all systems, all roles
- **Targeted Campaign**: Specific user groups (e.g., finance department, privileged users)
- **System-Specific Campaign**: Single system or system group
- **Critical Role Campaign**: Users holding high-risk or sensitive roles only
- **Joiner-Mover-Leaver (JML) Triggered**: Automated campaign when org change detected

**Review Item Generation:**

The system generates review items for each campaign by querying the latest access snapshot. Each item presents:
- User name, department, manager
- Role or authorization being reviewed
- Last login date, last transaction execution date
- SoD risk level associated with this access
- Usage statistics for the review period
- AI-generated recommendation (Certify / Review / Revoke)

**Reviewer Workflows:**

- Managers review their direct reports' access
- Role owners review who holds each role
- Bulk certification for trusted users with clean SoD profiles
- Comment requirement for any certify decision where SoD risk exists
- Escalation to security team for high-risk certifications

**Revocation Processing:**

When a reviewer selects "Revoke," the system:
1. Creates a revocation task in the provisioning queue
2. Optionally executes automatically via connector
3. Tracks completion with timestamp and executor
4. Notifies the affected user
5. Logs the decision to the audit trail

**Campaign Dashboards:**

- Completion rate by reviewer and organizational unit
- Overdue reviews with escalation status
- Revocation statistics and risk reduction metrics
- Historical comparison (YoY risk reduction from certification)

[Screenshot: Certification campaign dashboard with reviewer completion rates and pending items]

#### 3.1.6 Role Engineering / Role Design Studio (BRM)

The Role Engineering module provides tools for designing, analyzing, and maintaining SAP roles with built-in SoD governance.

**Role Designer:**

- Visual role composition interface
- Add authorization objects, field values, and transaction codes
- Real-time SoD check as permissions are added
- Compare role to similar roles in landscape
- Preview effective access before saving

**Role Mining:**

- Analyze actual system usage data to identify natural role groupings
- Generate role proposals based on user-function clusters
- Identify over-permissioned roles (users consistently use <30% of role permissions)
- Identify under-permissioned roles (users frequently bypass role through firefighter or manual grants)

**Role Design Studio:**

- Map technical SAP roles to business roles (e.g., "Accounts Payable Clerk" → {MM60, FBL1N, F110})
- Maintain business role catalog with ownership
- Business role request workflow (simpler for end users who don't know T-codes)
- Business role lifecycle management (creation, modification, deprecation, decommission)

**Role Drift Detection:**

Continuously compares current role assignments against the approved role design baseline:
- Identifies unauthorized role modifications in SAP
- Detects role assignments outside the defined user population
- Flags roles with increasing SoD risk over time
- Generates drift report for security review

**Role Comparison & Consolidation:**

- Side-by-side comparison of two or more roles
- Identify redundant roles (>80% permission overlap)
- Merger proposals with impact analysis (how many users, what SoD risk change)
- Role consolidation wizard with review and approval workflow

[Screenshot: Role Designer interface with permission tree, SoD check panel, and comparison view]

---

### 3.2 Risk Management (RM)

The Risk Management pillar provides a comprehensive enterprise risk framework covering risk identification, assessment, treatment, monitoring, and reporting. It integrates natively with the Access Control pillar (SoD violations feed the risk register) and the Process Control and Audit Management pillars (control deficiencies and audit findings link to risks).

#### 3.2.1 Risk Register

The risk register is the central repository of all identified risks across the organization.

**Risk Record Fields:**

- Risk ID (auto-generated, sequential per tenant)
- Risk title and description
- Risk category (Strategic, Operational, Financial, Compliance, Technology, Reputational)
- Risk owner (individual accountable for management)
- Risk steward (day-to-day monitor)
- Inherent risk rating (Likelihood × Impact, 5×5 matrix)
- Control effectiveness assessment
- Residual risk rating (post-control)
- Risk appetite alignment (Within / Near / Exceeds appetite)
- Risk response strategy (Accept, Avoid, Mitigate, Transfer)
- Response plan with milestones
- Related controls (from PC pillar)
- Related findings (from AM pillar)
- Related SoD violations (from AC pillar)
- Last assessment date
- Next review date

**Risk Heatmap:**

Interactive 5×5 heatmap with:
- Color-coded cells (green/yellow/orange/red)
- Drill-down to individual risks in each cell
- Filterable by category, owner, business unit
- Inherent vs. residual view toggle
- Historical comparison (shift arrows showing movement between periods)

[Screenshot: Risk heatmap with 5×5 likelihood/impact grid, color coding, and drill-down panel]

#### 3.2.2 Risk Assessment Workflow

Structured periodic assessment process:

1. **Initiation**: Schedule assessment campaign (annual, semi-annual, or triggered)
2. **Risk Owner Notification**: Owners receive assessment request with pre-populated prior scores
3. **Assessment Form**: Owner completes likelihood, impact, velocity, connectedness ratings
4. **Evidence Attachment**: Upload supporting documentation
5. **Review & Challenge**: Risk manager reviews and may challenge ratings
6. **Approval**: Chief Risk Officer or delegate approves final ratings
7. **Publication**: Updated risk register with trend indicators

#### 3.2.3 Key Risk Indicators (KRIs)

- Define KRI metrics with data source, formula, and frequency
- Set threshold levels (green/amber/red)
- Automated data collection from connected systems
- Dashboard widget for KRI status across risk portfolio
- Alert notification when KRI breaches threshold
- Historical trending with export

#### 3.2.4 Risk Response Plans

For each risk in "Mitigate" status:
- Action owner and due date
- Progress milestones with completion tracking
- Evidence of completion (document upload or system link)
- Residual risk re-assessment upon plan completion
- Overdue escalation to risk owner's manager

#### 3.2.5 Incident Management

- Log risk events and losses
- Link incidents to existing risks (update likelihood/impact)
- Root cause analysis workflow
- Incident timeline and impact quantification
- Near-miss tracking
- Regulatory notification tracking (GDPR breach, SOX restatement)

#### 3.2.6 Risk Reporting

- **Executive Dashboard**: Aggregate risk posture, top risks by category
- **Risk Movement Report**: Risks that improved or deteriorated vs. prior period
- **Risk Appetite Report**: Risks exceeding defined appetite by category
- **KRI Status Report**: All KRIs with threshold status
- **Open Action Items**: Response plan milestones past due
- **Board Report**: Committee-level summary with PPTX/PDF export

---

### 3.3 Process Control (PC)

The Process Control pillar manages the design, implementation, testing, and monitoring of internal controls. It is the operational heart of SOX compliance programs and supports any control framework (COSO, COBIT, ISO 27001, NIST).

#### 3.3.1 Control Library

The central repository of all controls:

**Control Record:**
- Control ID and title
- Control type (Preventive / Detective / Corrective)
- Control frequency (Continuous / Daily / Weekly / Monthly / Quarterly / Annual)
- Control nature (Manual / Automated / IT-Dependent Manual)
- Control owner and executor
- Control description and objective
- Related risk (from RM pillar)
- Related process and sub-process
- Regulatory mapping (SOX Section, COSO component, COBIT objective)
- Testing approach
- Evidence requirements
- Last test date and result
- Control effectiveness rating (Effective / Partially Effective / Ineffective)

**Control Attributes for SOX:**
- PCAOB/AICPA classification
- Management review control (MRC) flag
- IPE (Information Produced by Entity) dependency
- ITGC dependency linkage
- Process flow step reference

#### 3.3.2 Control Testing

Structured testing workflow:

1. **Test Plan Creation**: Define test objectives, population, sample methodology
2. **Sample Selection**: Random, risk-based, or full-population
3. **Evidence Collection**: Upload test documentation, system exports, screenshots
4. **Test Execution**: Document procedures performed and findings
5. **Exception Identification**: Log any deviations from expected control operation
6. **Conclusion**: Effective / Not Effective with supporting rationale
7. **Dual Sign-Off**: Preparer signs, independent reviewer approves
8. **Time Tracking**: Hours logged against test and budget

#### 3.3.3 Deficiency Management

When a control test identifies an exception:

1. **Deficiency Record**: Automatically created from exception
2. **Classification**: Control Deficiency / Significant Deficiency / Material Weakness
3. **Root Cause Analysis**: Structured 5-Why or fishbone template
4. **Management Response**: Control owner provides remediation plan
5. **Remediation Tracking**: Milestone-based with evidence upload
6. **Retest**: Follow-up test after remediation to confirm resolution
7. **Escalation**: Significant Deficiencies escalated to Audit Committee
8. **SoD Bridge (XL-D)**: Deficiencies linked to underlying SoD violations in AC pillar

#### 3.3.4 Continuous Control Monitoring (CCM)

Automated control monitoring for detective controls:

- Define monitoring rules (e.g., "flag all vendor invoices posted without PO reference")
- Connect to data source (SAP table query, HANA view, API feed)
- Set execution frequency (real-time, hourly, daily)
- Configure exception thresholds
- Auto-generate control exceptions when threshold breached
- Dashboard showing CCM coverage and exception trends

**Pre-built CCM Rules for SAP:**
- Duplicate invoice detection (same vendor, amount, date)
- Invoice posting without PO reference (non-PO spend)
- Goods receipt / Invoice mismatch > tolerance
- Payment run without dual authorization
- Master data changes without approval workflow (vendor bank account, pricing)
- Journal entry on last day of period
- Backdated journal entries

#### 3.3.5 SOX Sign-Off Cascade

Structured period-end sign-off workflow:

1. **Control Owner Sign-Off**: Each control owner certifies controls operated effectively
2. **Process Owner Sign-Off**: Process owner certifies all controls in their process
3. **Management Sign-Off**: C-suite certifies financial reporting internal controls
4. **Aggregation**: System aggregates certifications and exceptions
5. **Committee Report**: Board Audit Committee report generated automatically

Sign-off forms include:
- Embedded control summary with test results
- Exception disclosures
- Known deficiencies and remediation status
- Representation statement text
- Digital signature and timestamp

[Screenshot: SOX sign-off dashboard showing cascade status with color-coded completion indicators]

#### 3.3.6 Evidence Management

- Centralized evidence repository with SHA-256 integrity hashing
- Evidence types: documents, screenshots, system extracts, email confirmations
- Version control for superseded evidence
- Legal hold flag (prevents deletion)
- Auto-collection from connected systems (Evidence Agent AI)
- Cross-reference to control tests, audit workpapers, and findings

---

### 3.4 Audit Management (AM)

The Audit Management pillar provides a complete Internal Audit Management System (IAMS) covering the full audit lifecycle from universe maintenance through finding closure and action tracking.

#### 3.4.1 Audit Universe

The audit universe is the master list of all auditable entities:

- Organizational units (legal entities, business units, departments)
- Business processes and sub-processes
- IT applications and systems
- Regulatory requirements
- Key controls (linked from PC pillar)

Each entity carries a **risk-based audit score** calculated automatically:

```
Audit Score = (RM Risk Rating × 40%)
            + (PC Control Maturity Inverse × 35%)
            + (AC Access Risk Exposure × 25%)
```

This unified score (XI-04) ensures the audit plan prioritizes areas with the highest combined risk from all three pillars, not just traditional audit risk assessments.

#### 3.4.2 Audit Planning

**Annual Audit Plan:**

- Display all universe entities ranked by audit score
- Drag-and-drop assignment to quarters
- Resource capacity planning (available auditor-days by quarter)
- Budget allocation per engagement
- Plan approval workflow (Chief Audit Executive → Audit Committee)
- Multi-year planning view

**Risk-Based Plan Generation:**

One-click auto-generation that:
1. Sorts universe entities by composite risk score (descending)
2. Assigns highest-risk entities to earliest quarters
3. Respects resource constraints (don't over-assign any quarter)
4. Leaves buffer capacity for unplanned work (default 20%)
5. Produces draft plan for CAE review and adjustment

#### 3.4.3 Engagement Lifecycle

Every audit engagement passes through a defined 6-stage pipeline:

```
[Planned] → [Announced] → [Fieldwork] → [Draft Report] → [Final Report] → [Closed]
```

**Stage Details:**

| Stage | Key Activities | Who Acts |
|---|---|---|
| Planned | Define scope, objective, team, budget | Audit Manager |
| Announced | Notify auditee, request documentation | Audit Lead |
| Fieldwork | Execute procedures, gather evidence, identify findings | Auditors |
| Draft Report | Compile findings, share with management for response | Audit Lead + Management |
| Final Report | Incorporate responses, issue report | CAE |
| Closed | Verify all actions completed | Audit Lead |

**Engagement Record Fields:**
- Engagement title, type (Internal Audit, IT Audit, SOX, Special Investigation, Advisory)
- Auditee organization and contact
- Lead auditor and team members
- Planned and actual dates
- Budget hours and actual hours
- Scope statement and audit objectives
- Prior engagement findings (linked)
- Status and stage

#### 3.4.4 Work Programs & Procedures

Structured approach to fieldwork documentation:

**Work Program Templates:**
- Reusable templates by audit type (Financial, IT General Controls, SOX, Vendor)
- Template library with versioning
- Clone template to new engagement
- Customize procedures for specific scope

**Procedure Execution:**
- Step-by-step checklist within each procedure
- Evidence attachment per step
- Observation notes per step
- Conclusion per step (Satisfactory / Exception Noted / N/A)
- Dual sign-off: preparer completes, reviewer approves
- Time tracking: log hours against each procedure

#### 3.4.5 Workpapers

Electronic workpaper management:

- Workpaper types: Narrative, Schedule, Extract, Screenshot, Correspondence
- Version control with change history
- Review workflow: Preparer → Senior → Manager → Partner
- Review comments with resolution tracking
- Cross-reference to findings and procedures
- Index numbering (e.g., WP-1.1.A, WP-1.1.B)

#### 3.4.6 Findings (CCCE Format)

Findings follow the internationally recognized CCCE structure:

- **Condition**: What was observed (factual, specific, quantified where possible)
- **Criteria**: The standard, policy, or expectation that was not met
- **Cause**: Root cause of the deviation
- **Effect**: The actual or potential consequence
- **Recommendation**: Specific, actionable steps to remediate

**Additional Finding Attributes:**
- Severity: Critical / High / Medium / Low / Observation
- Finding owner (management responsible for remediation)
- Cross-module links: RM risks, PC controls, AC violations, prior findings
- Repeat finding flag (auto-detected from prior engagements)
- Management response text and agreed action date
- Audit comment on management response adequacy

[Screenshot: Finding detail page showing CCCE fields, severity rating, and cross-module links]

#### 3.4.7 Action Tracking

Every finding generates one or more remediation actions:

- Action title and detailed description
- Owner (person accountable for completion)
- Due date
- Progress updates and milestone notes
- Evidence of completion (document upload)
- Independent verification by auditor
- Overdue escalation (automatic notification at 7, 14, 30 days overdue)
- Status: Open / In Progress / Completed / Verified / Overdue / Cancelled

**Action Dashboard:**
- All open actions with RAG status
- Overdue actions with escalation status
- Completion rate by auditee and time period
- Trend chart: open vs. closed actions over time

---

## 4. Cross-Module Integration (XI)

The XI framework is what separates GovernexPlus from point solutions. Rather than separate systems that require manual data transfer, all four pillars share a unified data model with automated cross-module linkage.

### 4.1 Shared Organizational Hierarchy

A single org hierarchy serves all four pillars:

```
Organization
└── Legal Entity (Company Code)
    └── Division
        └── Department
            └── Team
                └── Individual Users
```

This hierarchy is maintained once (from HRMS or manual entry) and used by:
- AC: for org-level risk ranking and campaign scoping
- RM: for risk ownership and organizational risk roll-up
- PC: for control ownership and sign-off cascade
- AM: for audit universe entity definition and engagement scoping

Changes to the hierarchy propagate automatically to all pillar configurations.

### 4.2 SoD → Deficiency Bridge (XL-D)

When a SoD violation in the AC pillar is confirmed as a control deficiency:

1. Auditor or security analyst marks violation as "confirmed deficiency"
2. System automatically creates a Process Control deficiency record
3. Deficiency links to the underlying SoD rule, the user/role involved, and the control that failed
4. Control testing team can update the deficiency with root cause and remediation plan
5. When remediation is complete, both the deficiency record and the AC violation record are updated
6. SOX sign-off includes SoD-originated deficiencies automatically

### 4.3 Risk-Control-Finding Graph (XL-C)

Unified mitigation register linking the three pillars:

```
SoD Violation (AC)
    ↕ linked
Compensating Control (PC)
    ↕ linked
Risk Record (RM)
    ↕ linked
Audit Finding (AM)
```

Any change to one record notifies owners of linked records. For example, when a compensating control is assessed as ineffective, the linked SoD violation's risk score is automatically elevated, and the linked risk's residual rating is flagged for reassessment.

### 4.4 Unified Risk-Based Audit Score (XI-04)

The audit universe automatically calculates a composite risk score using three inputs:

- **RM Input (40%)**: Risk register rating for the entity's processes
- **PC Input (35%)**: Inverse of control maturity (lower maturity = higher audit priority)
- **AC Input (25%)**: Access risk exposure for users operating within the entity

This formula ensures the audit plan is driven by actual risk data, not just prior-year rotation, management intuition, or regulatory checklists.

### 4.5 Unified Notification & Escalation

A single notification engine serves all four pillars:
- Email delivery with HTML templates
- In-platform notification center
- Webhook integration (Slack, Teams, custom)
- Escalation chains configurable per notification type
- User notification preferences (immediate, daily digest, weekly summary)
- RTL support for Arabic language notifications

### 4.6 Unified Dashboard (Command Center)

The Command Center provides a cross-pillar view for senior GRC stakeholders:

- **AC Widget**: Active SoD violations, pending access requests, open firefighter sessions, upcoming certification campaigns
- **RM Widget**: Top risks by residual rating, KRI threshold breaches, overdue response plans
- **PC Widget**: Control effectiveness by process, open deficiencies by severity, CCM exception rate
- **AM Widget**: Active engagements by stage, overdue audit actions, upcoming plan milestones
- **AI Attention Items**: AI-curated list of items requiring immediate attention (across all pillars)
- **GRC Health Score**: Single numeric score (0–100) representing overall GRC program maturity

[Screenshot: Command Center dashboard with four pillar widgets, AI attention items panel, and GRC Health Score gauge]

---

## 5. AI Intelligence Layer

GovernexPlus embeds four distinct AI engines that provide intelligence across all pillars. These are not external chatbots or generic LLM integrations — they are domain-specific engines trained on GRC patterns and integrated into the core workflow.

### 5.1 GRC Assistant (Conversational AI)

The GRC Assistant is a natural language interface available throughout the platform:

**Capabilities:**
- **Explain**: "Explain this SoD violation to me in plain language" → generates a narrative explanation suitable for a non-technical manager
- **Investigate**: "Why does this user have so many violations?" → deep-dives into role assignments, access history, and contextual factors
- **Recommend**: "What should I do about this risk?" → generates prioritized remediation recommendations
- **Summarize**: "Summarize this audit engagement" → produces an executive summary from engagement data
- **Draft**: "Draft the management response for this finding" → generates a professional management response template

**Integration Points:**
- Risk Intelligence Engine violation detail page (explain this violation)
- Risk record page (recommend treatment)
- Audit finding page (draft response, explain significance)
- Control test page (generate test procedures)
- Role designer (explain permission conflicts)

### 5.2 Risk Intelligence Engine

A specialized AI engine for the Risk Management pillar:

- **Emerging Risk Detection**: Scans violation trends, incident data, and external threat feeds to identify emerging risks before they become material
- **Risk Correlation**: Identifies non-obvious relationships between risks (e.g., a vendor risk and an access risk that compound each other)
- **Impact Quantification**: Estimates financial impact range for risks using historical incident data and industry benchmarks
- **Narrative Generation**: Produces board-quality risk narratives from structured risk data
- **Trend Analysis**: Identifies systematic patterns in risk movements over time

### 5.3 Remediation Advisor

Focused on the AC pillar:

- **Role Redesign Copilot**: Analyzes a role with SoD conflicts and proposes specific permission splits or removals that resolve the conflict while preserving business functionality
- **Remediation Priority Queue**: Ranks all open violations by urgency (impact × exploitability × usage frequency) and generates a daily remediation work plan
- **Mitigation Control Designer**: For violations that cannot be remediated by role redesign, proposes specific compensating control designs (what to monitor, how frequently, who should review)
- **Batch Remediation Analysis**: For large numbers of violations, groups them by root cause and proposes structural fixes (role redesign, process changes) that resolve multiple violations simultaneously

### 5.4 NLP Engine

Natural language processing for unstructured content:

- **Procedure Text Analysis**: Extracts test steps, evidence requirements, and risk indicators from procedure narratives
- **Finding Classification**: Automatically classifies findings by category, severity, and regulatory relevance
- **Evidence Description Generation**: From uploaded documents, generates structured descriptions for workpaper indexing
- **Policy Text Mining**: Reads policy documents and maps policy requirements to controls in the PC library

### 5.5 Digital Twin (Simulation Engine)

The Digital Twin provides a safe simulation environment:

- **What-If Role Assignment**: Simulate adding any role to any user and see the exact SoD impact before touching production
- **Role Consolidation Simulation**: Model the impact of merging two roles on all users currently holding either role
- **Control Removal Simulation**: Model what SoD violations would emerge if a specific compensating control were removed
- **Org Restructuring Simulation**: Simulate access risk impact of proposed org chart changes

### 5.6 Migration Copilot

A specialized AI module for SAP GRC AC 12.0 migration:

- Reads exported ruleset XML/CSV from SAP GRC AC
- Maps SAP GRC rule IDs to GovernexPlus built-in rules (avoiding duplication)
- Identifies SAP GRC rules with no GovernexPlus equivalent (requiring custom rule creation)
- Analyzes SAP GRC mitigation control assignments and recreates in GovernexPlus
- Assesses ECC role landscape for S/4HANA readiness
- Generates migration readiness report with effort estimates

### 5.7 Evidence Agent

Automated evidence collection for audit and control testing:

- Connects to SAP systems via RFC to extract relevant data automatically
- Generates formatted evidence packages (Excel/PDF) for specified control tests
- Timestamps and hashes evidence at collection time
- Tags evidence to specific control tests and audit procedures
- Reduces manual evidence collection effort by 50–70% for ITGC and access controls

---

## 6. Connectors & Integrations

### 6.1 SAP Connectors

**SAP RFC Connector:**
- Direct RFC/BAPI calls to SAP S/4HANA and ECC 6.0
- User master data extraction (SU01 equivalent)
- Role assignment read and write
- Authorization object queries
- Transaction usage log extraction (SM20, STAD)
- Firefighter ID management
- Table extraction for CCM rules

**SAP Fiori Integration:**
- GovernexPlus tiles available in SAP Fiori Launchpad
- Single sign-on from Fiori to GovernexPlus via SAML
- Deep-link navigation from GovernexPlus to specific Fiori apps

**SAP SuccessFactors HRMS:**
- Real-time employee lifecycle events (hire, transfer, promotion, termination)
- Org hierarchy synchronization
- Position and job code feed for access entitlement rules
- JML (Joiner-Mover-Leaver) trigger source

**SAP BTP (Business Technology Platform):**
- API access via BTP API Management
- Identity propagation via BTP Identity Authentication Service

### 6.2 Identity Connectors

**Microsoft Azure AD:**
- OAuth 2.0 + SAML SSO integration
- Group membership synchronization
- Conditional access policy feed
- Privileged Identity Management (PIM) integration
- Sign-in risk alerts fed to Risk Intelligence Engine context

**Okta:**
- SAML SSO and SCIM provisioning
- Okta group synchronization
- Lifecycle event webhooks (user.lifecycle.create, user.lifecycle.deactivate)

**LDAP / Active Directory:**
- On-premise Active Directory synchronization
- Group membership queries
- Password synchronization support

### 6.3 HRMS Connectors

**Workday:**
- Worker lifecycle events via Workday Studio or REST API
- Org hierarchy and supervisory organization
- Position management feed
- EEO and job classification data (for access entitlement rules)

**SuccessFactors:**
- Employee Central real-time integration
- Position-based entitlement rules
- Termination date feed for JML revocation trigger

### 6.4 ITSM Connectors

**ServiceNow:**
- Access request tickets created automatically in ServiceNow
- Approval workflow bridging (approvals in either system)
- Incident creation from GovernexPlus alerts
- Change management integration (change request required before access modification)

**Jira (via REST):**
- Audit finding action items synced as Jira issues
- Two-way status sync
- Sprint/epic linking for remediation projects

### 6.5 Security Connectors

**SIEM Integration:**
- Syslog and JSON log export to Splunk, Microsoft Sentinel, IBM QRadar
- Structured security events: SoD violation, firefighter session, failed auth, admin action
- Real-time streaming via webhook

**Threat Intelligence:**
- MITRE ATT&CK mapping for access control risks
- CVE feed integration for SAP system vulnerability correlation

### 6.6 Custom Integration Framework

- **REST API**: All 938 platform endpoints are documented and available for integration
- **Webhooks**: Subscribe to events (violation created, request approved, finding raised) with payload delivery to any HTTPS endpoint
- **SCIM 2.0**: Standard user provisioning protocol for identity sync
- **Export APIs**: Bulk export of risk data, violations, control results, and audit data in JSON, CSV, or Excel format

---

## 7. Non-Functional Capabilities

### 7.1 Multi-Tenancy

GovernexPlus is built multi-tenant from the ground up:

- **Complete data isolation**: Every tenant's data is logically separated at the database row level
- **Independent configuration**: Each tenant has its own settings, rule library, org hierarchy, workflows, and user population
- **Independent feature flags**: Features can be enabled or disabled per tenant (e.g., AI features, specific connectors)
- **Usage limits**: Configurable per tenant (max users, max systems, max API calls per day)
- **Independent upgrade scheduling**: Tenant administrators can defer non-critical updates
- **Tenant onboarding wizard**: Self-service or platform-admin-guided tenant creation in <10 minutes

### 7.2 Authentication & MFA

- **Username/password** with bcrypt hashing
- **TOTP MFA** (Google Authenticator, Microsoft Authenticator, Authy compatible)
- **SAML 2.0 SSO** with Azure AD, Okta, PingFederate, ADFS
- **Session management**: Configurable session timeout (default: 60 minutes), concurrent session limits
- **Account lockout**: Configurable threshold (default: 5 failed attempts), automatic or admin-unlock

### 7.3 Audit Trail

Every state-changing operation generates an audit record:

```json
{
  "event_id": "uuid",
  "timestamp": "2026-09-06T14:23:01Z",
  "tenant_id": "tenant_abc",
  "user_id": "user_123",
  "user_email": "john.smith@acme.com",
  "action": "access_request.approve",
  "resource_type": "AccessRequest",
  "resource_id": "req_456",
  "details": {"role": "MM60", "system": "PRD", "decision": "approved"},
  "ip_address": "10.0.1.45",
  "user_agent": "Mozilla/5.0 ...",
  "result": "success"
}
```

Audit logs are:
- Immutable (no update or delete operations)
- Searchable with full-text and field filters
- Exportable in JSON, CSV, or syslog format
- Retained for 7 years by default (configurable)
- Accessible to auditors in read-only mode

### 7.4 Internationalization (i18n)

- Full UI translation in **English** and **Arabic (Modern Standard)**
- RTL (right-to-left) layout support for Arabic
- Locale-aware date, time, and number formatting
- Arabic-locale PDF and PPTX export
- Additional languages available via translation file extension (community-supported: French, German, Spanish)

### 7.5 Export Capabilities

| Format | Content |
|---|---|
| PDF | Risk reports, audit reports, engagement reports, committee presentations |
| PPTX | Executive dashboards, board reports, committee presentations |
| Excel (XLSX) | Risk register, violation lists, control results, finding trackers, action plans |
| CSV | Data exports for analytics tools |
| JSON | API responses, webhook payloads, bulk data export |

### 7.6 Accessibility

- WCAG 2.1 Level AA compliance
- Screen reader compatibility (tested with NVDA, JAWS, VoiceOver)
- Keyboard navigation throughout
- Sufficient color contrast ratios (minimum 4.5:1)
- Focus indicators on all interactive elements
- Alternative text on all images and icons

### 7.7 Performance & Scalability

- API response time: <200ms for standard queries, <2s for complex analysis
- Risk Intelligence Engine batch analysis: Full 10,000-user landscape in <30 minutes
- Concurrent users: 500+ per tenant instance
- Database connection pooling with configurable pool size
- Redis caching layer for frequent read operations (optional)
- Horizontal scaling via Docker Swarm or Kubernetes (see deployment guide)

---

## 8. Platform Statistics

| Metric | Value | Notes |
|---|---|---|
| **API Routes** | 938 | All authenticated and rate-limited |
| **Database Tables** | 81 | PostgreSQL, all with tenant_id scoping |
| **Built-in SoD Rules** | 128 | Across 12 SAP functional modules |
| **Frontend Pages** | 120+ | React components, full TypeScript |
| **GRC Pillars** | 4 | AC, RM, PC, AM |
| **AI Engines** | 4 | Assistant, Risk Intelligence, Remediation, NLP |
| **Connector Types** | 8 | SAP, Azure AD, Okta, Workday, SF, ServiceNow, Jira, SIEM |
| **Supported Languages** | 2 | English, Arabic (RTL) |
| **Export Formats** | 5 | PDF, PPTX, Excel, CSV, JSON |
| **Authentication Methods** | 3 | Username/password, TOTP MFA, SAML SSO |
| **Alembic Migrations** | 12+ | Full schema version history |
| **Test Coverage** | >80% | Unit + integration + E2E |
| **Documentation Pages** | 250+ | Admin, user, API, and developer guides |

---

## 9. Licensing & Deployment Models

### 9.1 SaaS (Cloud-Hosted)

GovernexPlus cloud is hosted on a shared infrastructure with complete tenant isolation.

**Ideal for:**
- Organizations that prefer OpEx over CapEx
- SME and mid-market SAP customers
- Organizations without dedicated infrastructure teams
- Pilot programs and proof-of-concept deployments

**Characteristics:**
- Zero infrastructure management
- Automatic updates (major versions opt-in, patch automatic)
- 99.9% SLA
- Data residency options: US, EU, APAC
- Backups managed by GovernexPlus team
- Shared infrastructure with tenant data isolation

**Licensing Tiers:**

| Tier | Users | Pillars | AI Features | Price Model |
|---|---|---|---|---|
| Starter | Up to 100 | AC only | Basic | Per-user/month |
| Professional | Up to 500 | AC + RM | Standard | Per-user/month |
| Enterprise | Unlimited | All 4 pillars | Full AI suite | Annual contract |

### 9.2 On-Premise

GovernexPlus is fully deployable on customer infrastructure using Docker and Docker Compose or Kubernetes.

**Ideal for:**
- Organizations with strict data sovereignty requirements
- Financial services and government organizations with regulatory restrictions on cloud hosting
- Organizations with existing on-premise SAP landscapes
- Large enterprises with dedicated IT infrastructure teams

**Characteristics:**
- Full control over data and infrastructure
- Customer manages upgrades (upgrade tooling provided)
- Customer manages backups and disaster recovery
- Can deploy in air-gapped environments (no internet connectivity required)
- Requires PostgreSQL 15+ and Docker 24+

**Minimum Infrastructure Requirements:**

| Component | Minimum | Recommended |
|---|---|---|
| Application Server | 4 vCPU, 8 GB RAM | 8 vCPU, 16 GB RAM |
| Database Server | 4 vCPU, 16 GB RAM | 8 vCPU, 32 GB RAM |
| Storage | 100 GB SSD | 500 GB SSD |
| Network | 1 Gbps | 10 Gbps |

### 9.3 Hybrid Deployment

**Ideal for:**
- Organizations with SAP on-premise but preference for cloud GRC
- Organizations requiring on-premise data processing but cloud reporting
- MSP/SI partners managing GRC for multiple clients

**Characteristics:**
- Application layer in cloud, data processing on-premise
- SAP RFC connector runs on-premise (network-adjacent to SAP systems)
- Evidence and workpapers stored on-premise
- Dashboards and reporting accessible from cloud
- Data synchronization via encrypted channels

### 9.4 Private SaaS / Dedicated Instance

For organizations requiring the operational simplicity of SaaS with the isolation of on-premise:

- Single-tenant cloud instance
- Dedicated database instance
- Customer-specific upgrade scheduling
- Custom domain (grc.yourdomain.com)
- Available in any major cloud region (AWS, Azure, GCP)

### 9.5 Migration Licensing

Organizations migrating from SAP GRC AC 12.0 are eligible for:
- **Migration Copilot**: Included at no additional cost for the first 12 months
- **Parallel run**: Ability to run GovernexPlus alongside SAP GRC AC during transition
- **Rule import**: One-time professional services engagement to migrate custom rules, mitigation assignments, and historical data
- **Training credits**: Included user training sessions for the GRC team

---

*For pricing inquiries, deployment sizing, or proof-of-concept requests, contact the GovernexPlus team at sales@governexplus.io*

*Documentation maintained by the GovernexPlus Product Team. Last updated: September 2026.*
