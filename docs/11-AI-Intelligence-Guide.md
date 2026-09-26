# GovernexPlus — AI Intelligence & Copilot Guide

**Version:** 2.0
**Applies to:** GovernexPlus 2.x
**Last updated:** 2026-09-06

---

## Table of Contents

1. [AI Architecture Overview](#1-ai-architecture-overview)
2. [GRC Health Score](#2-grc-health-score)
3. [Proactive Attention Items](#3-proactive-attention-items)
4. [AI Explain](#4-ai-explain)
5. [AI Investigate](#5-ai-investigate)
6. [AI Recommend](#6-ai-recommend)
7. [Role-Personalized Dashboards](#7-role-personalized-dashboards)
8. [One-Click Fix Preview](#8-one-click-fix-preview)
9. [Role Redesign Copilot](#9-role-redesign-copilot)
10. [Migration Copilot](#10-migration-copilot)
11. [Audit Evidence Agent](#11-audit-evidence-agent)
12. [GRC Digital Twin](#12-grc-digital-twin)
13. [LLM Integration](#13-llm-integration)

---

## 1. AI Architecture Overview

GovernexPlus embeds an AI intelligence layer that sits horizontally across all four GRC pillars:

```
┌──────────────────────────────────────────────────────────────────┐
│               GRC AI Intelligence Layer                          │
│  Health Score │ Attention Items │ Explain │ Recommend │ Copilots │
└──────────┬───────────┬──────────────┬──────────────┬────────────┘
           │           │              │              │
    ┌──────▼──┐  ┌─────▼─────┐  ┌────▼──────┐  ┌───▼─────────┐
    │ Access  │  │  Process  │  │   Risk    │  │   Audit     │
    │ Control │  │  Control  │  │ Management│  │ Management  │
    │  (AC)   │  │  (PC)     │  │  (RM)     │  │  (AM)       │
    └─────────┘  └───────────┘  └───────────┘  └─────────────┘
```

The AI layer is implemented across several modules:

| Module | Location | Purpose |
|---|---|---|
| GRC Health Score Engine | `core/ai/risk_intelligence.py` | Composite health scoring across all 4 pillars |
| NLP Engine | `core/ai/nlp_engine.py` | Text parsing, intent classification for natural language queries |
| Remediation Advisor | `core/ai/remediation_advisor.py` | Generates structured recommendations for violations and findings |
| GRC Assistant | `core/ai/grc_assistant.py` | Conversational copilot interface |
| AI Router | `api/routers/ai_grc.py` | REST endpoints for all AI features |
| GRC Intelligence | `core/intelligence/` | Cross-module correlation and digital twin logic |

The AI layer operates on data already in the GovernexPlus database. LLM calls are made only for natural-language narrative generation, explanation enrichment, and conversational copilot responses. All scoring, correlation, and recommendation logic runs deterministically in Python without LLM dependency — the LLM enhances but does not gate any core GRC function.

---

## 2. GRC Health Score

### 2.1 Composite Score Formula

The GRC Health Score is a single 0–100 number that represents the overall governance posture of the organization. It is a weighted average of four pillar scores:

```
Health Score = (AC_score × 0.30) + (PC_score × 0.25) + (RM_score × 0.25) + (AM_score × 0.20)
```

| Pillar | Weight | Abbrev | What it measures |
|---|---|---|---|
| Access Control | 30% | AC | SoD violations, over-privileged users, certification compliance, firefighter hygiene |
| Process Control | 25% | PC | CCM rule pass rate, control effectiveness, deficiency rate |
| Risk Management | 25% | RM | Open high/critical risks, mitigation coverage, risk trend |
| Audit Management | 20% | AM | Open findings, overdue findings, evidence completeness, repeat finding rate |

### 2.2 Pillar Scoring Logic

**Access Control (AC) Score**

| Sub-metric | Weight | Formula |
|---|---|---|
| Critical SoD violation rate | 35% | `100 × (1 − critical_violations / total_users)`, clamped 0–100 |
| Certification compliance | 25% | `100 × certified_items / total_certifiable_items` |
| Over-provisioned users | 20% | `100 × (1 − over_provisioned_users / total_users)` |
| Firefighter review compliance | 20% | `100 × reviewed_sessions / total_sessions_last_30d` |

**Process Control (PC) Score**

| Sub-metric | Weight | Formula |
|---|---|---|
| CCM rule pass rate | 40% | `100 × passed_controls / total_controls` |
| Open deficiency rate | 35% | `100 × (1 − open_deficiencies / total_controls)` |
| Overdue remediation rate | 25% | `100 × on_time_remediations / total_due_remediations` |

**Risk Management (RM) Score**

| Sub-metric | Weight | Formula |
|---|---|---|
| Critical open risks | 40% | `100 × (1 − critical_open / total_risks)` |
| Mitigation coverage | 35% | `100 × mitigated_risks / total_risks` |
| Risk trend (30-day) | 25% | Positive trend = +15 pts; stable = 0; negative = −15 pts |

**Audit Management (AM) Score**

| Sub-metric | Weight | Formula |
|---|---|---|
| Open finding rate | 40% | `100 × (1 − open_findings / total_findings)` |
| Overdue finding rate | 35% | `100 × on_time_findings / total_due_findings` |
| Repeat finding rate | 25% | `100 × (1 − repeat_findings / total_findings)` |

### 2.3 Interpreting the Score

| Score Range | Label | Interpretation |
|---|---|---|
| 90–100 | Excellent | Strong governance posture. Minimal open risks and findings. |
| 75–89 | Good | Generally well-controlled with manageable exposure. |
| 60–74 | Fair | Notable gaps requiring attention. Elevated violation or finding counts. |
| 40–59 | At Risk | Significant governance weaknesses. Executive attention recommended. |
| 0–39 | Critical | Severe governance breakdown. Immediate remediation required. |

The GRC Health Score is displayed on the main dashboard and is recalculated every 4 hours (configurable) or on demand via `POST /api/v1/intelligence/health-score/refresh`.

---

## 3. Proactive Attention Items

### 3.1 What Triggers Attention Items

The attention item engine (`core/intelligence/attention_engine.py`) scans for conditions across all GRC modules every hour and generates prioritized items requiring human action. Trigger conditions:

| Trigger | Severity | Module |
|---|---|---|
| New critical SoD violation detected | Critical | AC |
| Access certification campaign past due | High | AC |
| Firefighter session not reviewed within SLA | High | AC |
| User never had access reviewed (>365 days) | Medium | AC |
| CCM rule failed 3+ times in 24 hours → deficiency auto-created | Critical | PC |
| Control with no test evidence for 90+ days | Medium | PC |
| Overdue control deficiency remediation | High | PC |
| Critical risk with no mitigation (>30 days old) | Critical | RM |
| Risk re-review overdue | Medium | RM |
| Repeat finding (same control, same root cause) | High | AM |
| Audit finding response overdue | High | AM |
| Evidence collection <70% for active audit | Medium | AM |
| Health Score dropped >10 points in 7 days | High | All |
| New user with critical-risk role assigned (no approval record) | Critical | AC |

### 3.2 Priority Ranking

Attention items are ranked by a composite priority score:

```
priority_score = (severity_weight × 40) + (age_days × 2) + (module_weight × 10) + (user_impact × 15)
```

Where:
- `severity_weight`: Critical=4, High=3, Medium=2, Low=1
- `age_days`: Days since the condition was first detected (older = higher priority, up to 30 days)
- `module_weight`: Determined by tenant's configured pillar priorities
- `user_impact`: Number of affected users / 10, capped at 10

Items are presented on the dashboard sorted by `priority_score` descending. The top 10 items are shown by default; the full list is available via `GET /api/v1/intelligence/attention-items`.

### 3.3 Action Buttons

Each attention item surfaces between one and three action buttons:

| Button | Action | Available For |
|---|---|---|
| Fix | Opens a one-click fix preview modal | SoD violations, over-provisioned access, deficiencies |
| Review | Opens the relevant detail screen | Firefighter sessions, certifications, audit findings |
| Escalate | Sends escalation notification to the next approver level | Overdue items |
| Dismiss | Marks as acknowledged with a mandatory reason | All items (audit-logged) |
| Snooze | Suppresses for a configurable period (1, 3, 7 days) | Medium/Low severity only |

---

## 4. AI Explain

### 4.1 Supported Object Types

The AI Explain feature (`POST /api/v1/intelligence/explain`) generates a natural-language explanation for any GRC object, making complex technical information accessible to non-specialist users.

| Object Type | `object_type` Value | What is explained |
|---|---|---|
| SoD Risk Violation | `risk_violation` | Why the combination is a risk, what could go wrong, regulatory context |
| User Access Profile | `user_access` | Summary of the user's access landscape, risk profile, and anomalies |
| Control | `control` | What the control does, how it works, what it protects against |
| Audit Finding | `finding` | Root cause, business impact, typical remediation approaches |
| CCM Rule | `ccm_rule` | What the rule monitors, how it detects anomalies, what to do when it fires |
| Firefighter Session | `ff_session` | Summary of session activity, flagged transactions, recommended follow-up |
| Risk Record | `risk` | Risk description, likelihood/impact rationale, relationship to other risks |

### 4.2 How Explanations Are Generated

1. GovernexPlus fetches the full object record and related data from the database (violations, user assignments, historical activity, regulatory tags).
2. A structured prompt is constructed with the object data and organizational context.
3. The prompt is sent to the configured LLM provider.
4. The LLM response is post-processed to ensure it is under 400 words, does not hallucinate specific regulatory article numbers, and includes an actionable next-step.
5. The explanation is returned alongside the structured data and cached for 24 hours (or until the underlying object changes).

When `LLM_PROVIDER=none`, explanations fall back to a template-based system that produces structured but non-narrative explanations using conditional logic.

### 4.3 Example Explanations

**SoD Violation — FI-001 (Vendor Create + AP Payment):**

> "This violation means that [User: John Smith] has the ability to both create new vendor records in SAP and process outgoing payments to those vendors — without any other user involved in either step. This combination is a classic segregation of duties conflict because a single person could set up a fictitious vendor with their own bank account and then authorize a payment to that vendor, resulting in fraudulent disbursements. This risk pattern is a focus area for SOX Section 302 controls and is typically cited in external audit findings for AP processes. Recommended action: Remove John's vendor creation access (FK01, XK01) or restrict payment authorization to a separate role. If business justification exists for this access combination, assign a compensating mitigation control and ensure all payment transactions to vendors created by John are reviewed by a second approver."

**Audit Finding — ITGC-AC-004 (User Access Not Reviewed):**

> "This finding indicates that 47 SAP user accounts have not had their access formally reviewed or certified in over 12 months. Regular access reviews are a fundamental IT General Control required by virtually all compliance frameworks (SOX ITGC, ISO 27001 A.9, PCI DSS 7.3). Without periodic review, terminated employees or users who changed roles may retain access they no longer need, creating both insider threat risk and compliance exposure. The typical remediation is to launch an access certification campaign covering all affected users, have their managers certify each role assignment as appropriate, and revoke access for roles that cannot be justified. This finding has been classified High severity due to the number of affected accounts and the time elapsed since the last review."

---

## 5. AI Investigate

### 5.1 Risk Investigation

The AI Investigate feature (`POST /api/v1/intelligence/investigate`) performs a cross-module deep-dive on a specific risk, violation, or user and returns a structured investigation report.

For a **SoD violation investigation**, the report includes:

- **Violation Details:** Rule, user, roles, tcodes involved, detection date.
- **Usage Analysis:** Were the conflicting tcodes actually used together? When was each last used? Frequency trends.
- **Historical Context:** Has this user had this violation before? Was it previously mitigated?
- **Related Violations:** Are other users in the same department affected by the same rule?
- **Organizational Context:** Is this user in a financial control role? What is their risk tier?
- **Process Control Cross-Reference:** Are there CCM rules monitoring the transactions involved? Have they recently fired?
- **Audit Cross-Reference:** Have there been prior audit findings related to this control area?
- **Recommended Actions:** Ranked list of remediation options with effort/impact estimates.

### 5.2 Cross-Module Correlation

The investigation engine correlates data across all four GRC pillars:

```
User "John Smith" — SoD Violation FI-001
    │
    ├── AC: 3 additional violations (FI-003, MM-007, HR-002)
    │   └── Last access review: 14 months ago
    │
    ├── PC: CCM rule CCM-FI-001 fired 2× last week (high-value payments)
    │   └── No deficiency created (below threshold)
    │
    ├── RM: Associated risk RM-0042 "AP Fraud Risk" rated High
    │   └── No mitigation assigned (31 days open)
    │
    └── AM: Related finding ITGC-AP-003 from 2025 audit (repeat finding)
        └── Finding remediation 12 days overdue
```

This cross-module view is presented as a connected timeline in the investigation report, giving the reviewer a complete picture of the control environment around the investigated object.

---

## 6. AI Recommend

### 6.1 Violation Recommendations

For each SoD violation, the Remediation Advisor (`core/ai/remediation_advisor.py`) generates a ranked set of remediation recommendations:

| Option | Code | Description | Estimated Effort | Risk Reduction |
|---|---|---|---|---|
| Remove Conflicting Access | `remove_access` | Remove the lower-priority function (Function B) from the user's roles. | Low | High |
| Assign Mitigation Control | `assign_mitigation` | Accept the violation and assign a compensating control (e.g., transaction monitoring, dual approval). | Medium | Medium |
| Accept Risk | `accept_risk` | Formally accept the violation with a documented business justification and expiry date. | Low | None |
| Role Redesign | `redesign_role` | Restructure the user's role assignments to eliminate the conflict at the role level. | High | High |
| Org-Level Restriction | `org_restrict` | Add organizational level restrictions to limit the conflict to non-overlapping org units. | Medium | Medium–High |

The advisor scores each option based on the user's actual usage data (options involving unused access score higher for removal), the availability of suitable mitigation controls in the catalog, and the organizational risk appetite setting.

### 6.2 Deficiency Recommendations

For CCM-generated control deficiencies, recommendations include:

- **Immediate Actions:** Close the specific instance that triggered the deficiency (e.g., reverse the unauthorized payment, lock the user account).
- **Short-term Actions (1–5 days):** Configure a compensating control, tighten the CCM rule threshold, or add an approval step.
- **Long-term Actions (1–4 weeks):** Redesign the process, update the policy, implement a preventive control.
- **Root Cause Options:** Technical (misconfiguration), process (procedure not followed), people (training gap), policy (policy gap).

### 6.3 Effort and Impact Ratings

Each recommendation is annotated with:

| Rating | Scale | Values |
|---|---|---|
| Effort | Qualitative | Low (hours), Medium (days), High (weeks) |
| Risk Reduction | % | Estimated percentage reduction in the associated risk score |
| Business Disruption | Qualitative | Minimal, Moderate, Significant |
| Reversibility | Boolean | Whether the action can be undone easily |

---

## 7. Role-Personalized Dashboards

GovernexPlus serves a different dashboard view based on the authenticated user's primary role. Each view surfaces the data most relevant to that role's daily responsibilities.

### 7.1 CFO View (`risk_manager` + finance context)

Focus: Financial risk exposure and control effectiveness.

- GRC Health Score with AC and PC pillar emphasis.
- Financial SoD violation summary (FI + MM categories only).
- Top 5 open financial risks by score.
- AP/AR process control pass rate trend (30 days).
- Month-end close control status widget.
- High-value transaction anomalies from CCM-FI rules.

### 7.2 CISO View (`security_admin` or `tenant_admin`)

Focus: Access governance and technical security posture.

- Full GRC Health Score with all pillars.
- Critical violations requiring immediate action.
- Firefighter sessions: active, pending review, overdue.
- Privileged access users by risk score.
- Recent user provisioning activity.
- Failed RFC connections and sync errors.
- Access certification campaign completion rates.

### 7.3 CAE View (Chief Audit Executive — `compliance_officer`)

Focus: Audit posture and compliance status.

- AM pillar score and trend.
- Active audit program status and completion %.
- Open findings by severity and age.
- Repeat finding rate (rolling 12 months).
- Evidence completeness by audit.
- Upcoming certification campaign due dates.
- Regulatory framework compliance scores (SOX, ISO 27001, PCI DSS).

### 7.4 Control Owner View (`control_owner`)

Focus: Assigned controls and deficiencies.

- Controls assigned to the user (status: pass/fail/not tested).
- CCM alerts on assigned controls.
- Open deficiencies and their remediation deadlines.
- Evidence items awaiting upload.
- Upcoming testing due dates.
- Chat with the AI assistant pre-filtered to their control scope.

### 7.5 Auditor View (`auditor`)

Focus: Evidence gathering and audit trail.

- Audit program in scope with completion tracker.
- Evidence completeness heat map by control area.
- Recent access changes for selected users.
- Firefighter session review history.
- SoD violation heat map.
- Export buttons for PDF evidence packages.
- No write actions available — read-only enforcement.

### 7.6 Employee View (`employee`)

Focus: Self-service access management.

- My current roles and access (simplified list, no technical auth object detail).
- My open access requests and their approval status.
- My pending approvals (delegated approvals if configured).
- Password reset widget.
- Request new access button.
- AI chatbot: "What does this role give me access to?"

---

## 8. One-Click Fix Preview

The One-Click Fix Preview feature allows authorized users to preview the exact changes that a recommended remediation will make before committing them. This eliminates the fear of accidental misconfiguration and enables non-technical users to self-serve remediations.

### 8.1 Remove Access Preview

Triggered from a violation's Recommend panel or an attention item's Fix button.

The preview modal shows:
- **User:** Display name, SAP user ID, department.
- **Roles to be removed:** Each role that contains the conflicting function, with the specific tcodes/auth objects that create the conflict highlighted in red.
- **Roles to be retained:** All other roles, shown in green.
- **Downstream impact analysis:** Any other violations that would be resolved as a side effect of this removal.
- **New violations introduced:** Any new violations that would be created (e.g., removing a role creates a different SoD conflict — rare but detected).
- **Business capability lost:** Human-readable description of what the user can no longer do after the removal.
- **SAP provisioning command preview:** The exact BAPI call that will be executed, shown in a technical detail panel for security admins.

On confirmation, the remove-access action creates an access request in `SYSTEM_REMEDIATION` state, which is auto-approved and provisioned immediately.

### 8.2 Assign Mitigation Preview

Shows:
- **Violation:** Rule name and user.
- **Available mitigations:** List of controls from the mitigation catalog that are tagged for this violation type, with their effectiveness ratings.
- **Selected mitigation:** Detail of the chosen control (what it does, who owns it, how frequently it runs).
- **Monitoring commitment:** What evidence will be collected automatically (CCM rules that will be configured) and what manual review is required.
- **Risk score change:** The projected violation risk score after the mitigation is assigned (typically −30 to −50% of the raw score).
- **Expiry:** Mitigation assignments expire after a configurable period (default: 1 year) and require renewal.

### 8.3 Remediate Deficiency Preview

Shows:
- **Deficiency:** Control, deficiency description, severity.
- **Remediation plan template:** Pre-populated remediation steps based on the deficiency type.
- **Assigned owner:** The user who will own the remediation (defaulting to the control owner).
- **Due date:** Pre-calculated based on severity SLA.
- **Evidence required:** What artifacts must be uploaded to close the deficiency.
- **SLA impact:** How this deficiency is affecting the process control pillar score.

---

## 9. Role Redesign Copilot

The Role Redesign Copilot (`core/role_intelligence/`) analyzes the complete SAP role landscape and produces actionable consolidation and cleanup proposals.

### 9.1 Landscape Analysis

The initial analysis (`POST /api/v1/role-intelligence/analyze`) scans all roles in the connected SAP system and computes:

- Total role count.
- Role types: single vs. composite.
- Role age distribution (by creation date).
- Role assignment distribution (how many users per role).
- Usage analysis: % of roles where >80% of tcodes are never used.
- SoD risk distribution: % of roles that contribute to high/critical violations.

### 9.2 Unused Role Detection

A role is classified as unused when all of the following conditions are met for >90% of its assigned users:
- No SM20 transaction usage recorded for any of the role's tcodes in the configured lookback period (default: 90 days).
- The role was not assigned within the last 30 days (recently assigned roles are excluded from unused detection).
- The role is not a technical/batch role type.

Unused roles are surfaced as candidates for revocation in a prioritized list, estimated to save N% of the total authorization surface area.

### 9.3 Duplicate Role Detection

Two roles are considered duplicate candidates when:
- They share >90% of the same tcode set.
- They have the same or highly similar names (Levenshtein distance < 3 after normalization).
- They share the same organizational level values.

Duplicate detection uses a Jaccard similarity coefficient on the tcode sets:
```
similarity = |tcodes_A ∩ tcodes_B| / |tcodes_A ∪ tcodes_B|
```
Pairs with similarity > 0.90 are flagged as duplicate candidates.

### 9.4 Similar Role Grouping

Roles with similarity between 0.60 and 0.90 are grouped into clusters using a graph-based community detection algorithm. Each cluster represents a family of roles that could potentially be consolidated into a single parameterized role using org-level restrictions.

### 9.5 Consolidation Proposals

For each duplicate/similar cluster, the copilot generates a consolidation proposal:

```json
{
  "proposal_id": "PROP-001",
  "proposal_type": "consolidation",
  "roles_to_merge": ["Z_FI_AP_CLERK_01", "Z_FI_AP_CLERK_02", "Z_FI_AP_CLERK_03"],
  "proposed_role_name": "Z_FI_AP_CLERK",
  "users_affected": 23,
  "tcode_union": ["FK01", "FB60", "FB65", "MIR7", "MIRO"],
  "sod_violations_after_merge": 1,
  "sod_violations_before_merge": 4,
  "estimated_effort_days": 2,
  "risk_reduction": "high",
  "executive_summary": "Three near-identical AP Clerk roles can be merged into one role parameterized by company code, reducing the authorization footprint by 67% and eliminating 3 SoD violations caused by overlapping tcode coverage across the role variants."
}
```

### 9.6 Role Split Proposals (SoD-Clean Redesign)

When a single role contains both sides of a critical SoD conflict and is assigned to many users, the copilot proposes a role split:

```json
{
  "proposal_id": "PROP-007",
  "proposal_type": "split",
  "role_to_split": "Z_FI_FULL_ACCESS",
  "conflict_rule": "FI-001",
  "proposed_role_a": {
    "name": "Z_FI_AP_VENDOR_MAINT",
    "tcodes": ["FK01", "FK02", "XK01", "XK02"],
    "users_to_assign": ["user1", "user2", "user7"]
  },
  "proposed_role_b": {
    "name": "Z_FI_AP_PAYMENTS",
    "tcodes": ["F110", "F-53", "F-58"],
    "users_to_assign": ["user3", "user4", "user5", "user6"]
  },
  "users_requiring_both": ["user8"],
  "recommendation_for_dual_users": "User user8 requires both functions. Recommend formal exception with mitigation control CCM-FI-001.",
  "estimated_effort_days": 5
}
```

### 9.7 Executive Summary Generation

The copilot generates an executive-level summary report (downloadable as PPTX or PDF) covering:
- Current role landscape health score.
- Top 10 risk-reducing proposals.
- Estimated authorization surface reduction (%).
- Estimated SoD violation reduction (#).
- Implementation timeline and effort estimate.
- Recommended phasing (quick wins → structural changes → long-term optimization).

---

## 10. Migration Copilot

The Migration Copilot (`core/migration/`) assists organizations migrating from SAP ECC 6.0 to SAP S/4HANA by analyzing the GRC impact of the migration.

### 10.1 ECC→S/4HANA Impact Analysis

The impact analysis (`POST /api/v1/migration/analyze`) evaluates:
- Which existing ECC roles contain deprecated transaction codes.
- Which BAPIs used by GovernexPlus for provisioning/firefighter are affected.
- Which SoD rules require updates for S/4HANA tcode changes.
- Which authorization objects are simplified or removed in S/4HANA.

### 10.2 Tcode Mapping (ECC→S/4HANA)

The copilot maintains a comprehensive tcode mapping table (3,200+ entries in `core/migration/tcode_mapping.py`):

| ECC Tcode | S/4HANA Equivalent | Status | Notes |
|---|---|---|---|
| `FK01` | `BP` | Changed | Vendor creation now via Business Partner |
| `XK01` | `BP` | Changed | Extended vendor creation merged into BP |
| `FD01` | `BP` | Changed | Customer creation merged into BP |
| `MM60` | Removed | Deprecated | Replaced by S/4HANA MRP Live |
| `MD01` | `MD01N` | Changed | New MRP planning transaction |
| `VF01` | `VF01` | Unchanged | Billing document still applies |
| `SE16` | `SE16` | Unchanged | Still available (restricted in cloud) |
| `PFCG` | `PFCG` | Unchanged | Role maintenance unchanged |

### 10.3 Business Partner Consolidation Detection

The copilot identifies ECC users who have roles with both vendor and customer maintenance tcodes that will converge onto the BP transaction in S/4HANA. If a user currently has `FK01` and `FD01` in separate roles (which are not an SoD conflict in ECC), these may create a new SoD conflict in S/4HANA via the unified `BP` tcode if the SoD rule is defined at the tcode level.

### 10.4 Fiori App Opportunities

For each classic GUI tcode in the current role landscape, the copilot identifies whether a Fiori app equivalent exists and flags it as a Fiori opportunity. This supports the Fiori adoption planning process alongside the S/4HANA migration.

### 10.5 Per-Role Migration Plan

The copilot generates a detailed migration plan for each SAP role:

- List of deprecated tcodes that must be replaced.
- Recommended S/4HANA replacement tcodes and authorization objects.
- New SoD conflicts that will be introduced by tcode changes.
- Pre-migration SoD baseline vs. post-migration projected SoD count.
- Effort estimate for role remediation.

### 10.6 Migration Readiness Report

The readiness report (downloadable as PPTX) provides:
- Overall migration readiness score (0–100).
- Roles ready to migrate as-is (%).
- Roles requiring modification before migration (% + count).
- Estimated total remediation effort in person-days.
- Critical blockers (violations that must be resolved before go-live).
- Recommended pre-migration access certification campaign scope.

---

## 11. Audit Evidence Agent

The Audit Evidence Agent (`core/audit_evidence/`) automates the collection, assessment, and packaging of audit evidence from across the GovernexPlus data model.

### 11.1 Available Requirement Types

| Requirement Type | Code | Description |
|---|---|---|
| User Access Listing | `user_access_listing` | Complete listing of users and their role assignments as of a point-in-time. |
| Access Certification Evidence | `access_cert` | Certification campaign results showing who reviewed which access and what actions were taken. |
| SoD Violation Register | `sod_violations` | All violations detected in-period with risk scores and mitigation status. |
| Firefighter Log | `ff_log` | All firefighter sessions with duration, tcodes executed, reviewer sign-off. |
| Control Test Evidence | `control_test` | CCM rule results, pass/fail records, and exception handling documentation. |
| Risk Register | `risk_register` | All risks with likelihood, impact, mitigation, and acceptance decisions. |
| Change Evidence | `change_evidence` | Audit trail of all access changes (grants, revocations, role changes) in-period. |

### 11.2 Auto-Collection from DB Sources

The agent automatically collects evidence from 11 database sources:

| Source | DB Table(s) | Evidence Collected |
|---|---|---|
| User master | `users`, `user_roles` | Current user list with roles and employment status |
| Role assignments | `user_role_assignments` | Point-in-time role assignment snapshots |
| Access certifications | `certification_campaigns`, `certification_items` | Certification results and certifier decisions |
| SoD analysis | `risk_violations` | Violation records with risk scores |
| Firefighter | `firefighter_sessions`, `firefighter_session_activities` | Session logs and activity records |
| Audit logs | `audit_log` | System-generated immutable audit trail |
| Risk register | `risk_records`, `risk_mitigations` | Risk and mitigation records |
| CCM results | `ccm_rule_results` | Control monitoring results |
| Findings | `audit_findings` | Finding records and response status |
| Provisioning | `access_requests`, `provisioning_log` | Change evidence for access provisioning |
| Workflow | `workflow_instances`, `approval_decisions` | Approval decisions and timestamps |

### 11.3 Completeness Scoring

For each audit requirement, the agent calculates a completeness score:

```
completeness_score = (collected_items / expected_items) × 100
```

Where `expected_items` is determined by the audit scope (date range, in-scope systems, in-scope controls).

A completeness score of 100% means all expected evidence items have been collected and are available for download. Scores below 80% generate a gap report identifying missing items.

### 11.4 Gap Detection

The agent detects evidence gaps by comparing:
- Controls in scope vs. controls with test evidence on file.
- Users in scope vs. users with certification decisions.
- Firefighter sessions in period vs. sessions with reviewer sign-off.
- Risks in scope vs. risks with documented mitigation or acceptance decisions.

Gaps are reported as: `{gap_type}: {count} items missing ({% of expected})`.

### 11.5 Per-Control Evidence Assessment

For each in-scope control, the agent produces a control-level evidence assessment:

```json
{
  "control_id": "ITGC-AC-001",
  "control_name": "User Access Review",
  "evidence_items": [
    {
      "item_type": "access_cert",
      "description": "Q3 2026 Access Certification Campaign Results",
      "status": "collected",
      "file_ref": "evidence/cert_q3_2026.pdf",
      "collected_at": "2026-09-01T08:00:00Z"
    },
    {
      "item_type": "user_access_listing",
      "description": "User-Role Matrix as of 2026-09-01",
      "status": "collected",
      "file_ref": "evidence/user_role_matrix_20260901.xlsx",
      "collected_at": "2026-09-01T08:01:00Z"
    }
  ],
  "completeness_score": 100,
  "gaps": [],
  "assessment": "Sufficient evidence collected. No gaps identified."
}
```

---

## 12. GRC Digital Twin

The GRC Digital Twin (`core/intelligence/digital_twin.py`) provides a real-time simulation environment that mirrors the organization's current GRC state.

### 12.1 Full State Snapshot

The digital twin maintains a complete in-memory graph representation of:
- All users and their access profiles.
- All roles and their authorization objects.
- All active SoD violations.
- All open risks and their mitigation status.
- All active controls and their current pass/fail state.
- All open findings and their remediation status.

The snapshot is refreshed every 15 minutes from the database. A point-in-time snapshot can be requested via `POST /api/v1/intelligence/digital-twin/snapshot`.

### 12.2 Root Cause Grouping

The digital twin's root cause analysis engine groups violations and findings by their common underlying causes:

| Root Cause Category | Detection Method | Example |
|---|---|---|
| Role design flaw | Multiple users share the same violating role | 15 users have FI-001 via Z_FI_FULL_ACCESS |
| Orphaned access (role retained after transfer) | Role assignment date predates job change by <30 days | User transferred 60 days ago, still has old department role |
| Segregation by exception pattern | Violation accepted as exception >2 years ago, still open | Exception accepted 2023-01-01, still active |
| Firefighter creep | User holds firefighter role outside active session | FF role not revoked after session ended |
| Access accumulation | User has gained roles continuously for >2 years with no review | 47 roles assigned over 36 months, 0 reviews |

### 12.3 What-If User Move Simulation

The digital twin supports what-if simulation of organizational changes before they are executed in SAP. This is particularly valuable for HR-initiated role transfers.

`POST /api/v1/intelligence/digital-twin/simulate-user-move`:

```json
{
  "user_id": "user-uuid",
  "current_roles": ["Z_FI_AP_CLERK", "Z_MM_PURCHASING"],
  "new_roles": ["Z_SD_SALES_REP", "Z_FI_BILLING_CLERK"],
  "effective_date": "2026-10-01"
}
```

Response includes:
- Violations resolved by the move (roles being removed).
- New violations introduced by the move (roles being added).
- Net risk change (positive = improvement).
- Roles recommended for revocation (current roles not included in new assignment).
- Recommended access certification trigger.

### 12.4 Repeat Finding Prediction

Using historical finding data, the digital twin predicts the probability of a finding repeating based on:
- Same control as a prior finding.
- Same root cause category.
- Remediation was applied but root cause (role design flaw) was not addressed.
- Time since prior finding close date.

Findings with a repeat probability >70% are flagged proactively in the audit management module before the auditor formally raises the issue.

---

## 13. LLM Integration

### 13.1 Supported Providers

GovernexPlus supports four LLM provider modes, selectable via the `LLM_PROVIDER` environment variable:

| Provider | Value | Models Supported | Best For |
|---|---|---|---|
| OpenAI | `openai` | GPT-4o, GPT-4o-mini, GPT-4-turbo | Best narrative quality; cloud-hosted |
| Azure OpenAI | `azure` | GPT-4o, GPT-4-turbo (via deployment) | Enterprise; data residency requirements |
| Anthropic | `anthropic` | Claude Sonnet 4.5, Claude Opus 4.5 | Long context; complex explanations |
| Ollama (local) | `ollama` | Llama 3.1, Mistral, Phi-3, Gemma 2 | Air-gapped/on-premise; data privacy |
| Disabled | `none` | — | Template-based fallback; no external calls |

### 13.2 Configuration

**OpenAI:**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

**Azure OpenAI:**
```env
LLM_PROVIDER=azure
AZURE_OPENAI_KEY=...
AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-prod
```

**Anthropic:**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5
```

**Ollama (local):**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1
```

### 13.3 Risk Narratives

Risk narratives are LLM-generated text summaries attached to risk records in the risk register. They are generated automatically when a new risk is created or when the risk score changes significantly (>15 points).

A risk narrative includes:
- Plain-language description of the risk scenario.
- Likely business impact if the risk materializes.
- Historical analogues or industry examples (drawn from the LLM's training data, clearly labeled as illustrative).
- Connection to applicable regulatory requirements.
- Suggested mitigation strategy in non-technical language.

Narratives are limited to 300 words and are reviewed before publication if `NARRATIVE_REVIEW_REQUIRED=true` is set.

### 13.4 Finding Draft Generation

When an auditor identifies a new finding, the AI assistant can draft the finding description and management response template:

`POST /api/v1/ai-grc/draft-finding`:

```json
{
  "control_id": "ITGC-AC-001",
  "violation_ids": ["viol-uuid-1", "viol-uuid-2"],
  "auditor_notes": "Identified 15 users with SoD violations in AP area, no compensating controls documented"
}
```

The draft includes:
- **Condition:** Factual description of what was found (populated from violation data).
- **Criteria:** The policy or control requirement that was not met.
- **Cause:** Root cause analysis based on the digital twin's root cause grouping.
- **Effect:** Potential business impact.
- **Recommendation:** Remediation recommendation from the Remediation Advisor.
- **Management Response Template:** Pre-filled response template for the control owner to complete.

Finding drafts are saved as `DRAFT` status and require auditor review before being promoted to `ISSUED` status.

---

*For configuration of LLM providers and AI feature toggles, see the [Configuration Reference Guide](./09-Configuration-Reference-Guide.md). For deployment of the AI-enabled platform, see the [Deployment & Operations Guide](./12-Deployment-Operations-Guide.md).*
