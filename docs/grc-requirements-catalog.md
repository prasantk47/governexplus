# Governex+ — GRC Suite Requirements Catalog
### Four Pillars: Access Control (SoD) · Process Control · Risk Management · Audit Management

Requirement IDs: AC = Access Control, PC = Process Control, RM = Risk Management, AM = Audit Management, XI = Cross-module Integration, NF = Non-functional.
Priority: M = Must-have (MVP), S = Should-have (v1.x), C = Could-have (differentiator/roadmap).

---

## 1. Access Control / SoD (AC) — largely existing in Governex+, listed for completeness

### 1.1 Risk & Ruleset (Risk Library)
| ID | Requirement | Priority |
|----|-------------|----------|
| AC-01 | Deliver a pre-built SoD risk library (functions, risks, rule sets) covering standard SAP business processes (P2P, O2C, R2R, HR/Payroll, Basis) | M |
| AC-02 | Support custom risks, functions, and rule sets, including Z-transactions and custom authorization objects | M |
| AC-03 | Risk attributes: risk ID, description, risk level (High/Medium/Low/Critical), business process, risk type (SoD, critical action, critical permission), status | M |
| AC-04 | Multi-language risk library (English + Arabic minimum), with per-language descriptions maintained centrally | S |
| AC-05 | Rule set versioning, change history, and transport/promotion between environments | S |
| AC-06 | Risk library import/export (Excel/CSV) and migration from SAP GRC rulesets | S |

### 1.2 Access Risk Analysis (ARA)
| ID | Requirement | Priority |
|----|-------------|----------|
| AC-10 | User-level, role-level, and profile-level risk analysis at permission (authorization object) level, not just transaction level | M |
| AC-11 | Simulation ("what-if") analysis before assigning roles/access | M |
| AC-12 | Batch/scheduled full-landscape risk analysis with delta processing | M |
| AC-13 | Mitigating controls: define, assign to users/roles/risks, with control owner, validity dates, and monitor | M |
| AC-14 | Remediation view: which role/authorization causes the violation, drill-down to auth object values | M |
| AC-15 | Org-level analysis: filter and aggregate violations by company code, plant, branch, cost center, or custom org attribute | M |
| AC-16 | Branch/org ranking dashboards by violation count and weighted risk score | S |
| AC-17 | Usage-based analysis: compare assigned vs. actually used access (transaction usage data) to prioritize remediation | S |
| AC-18 | Dormant/inactive account detection with critical access flagging | S |

### 1.3 Access Request Management (ARM)
| ID | Requirement | Priority |
|----|-------------|----------|
| AC-20 | Self-service access request with role catalog / business-friendly descriptions | M |
| AC-21 | Multi-stage approval workflows (manager, role owner, security, custom stages) with delegation and escalation | M |
| AC-22 | Inline risk analysis during request approval, with mitigation assignment before provisioning | M |
| AC-23 | Automated provisioning/de-provisioning to SAP and connected systems (Azure AD, Okta, etc.) | M |
| AC-24 | JML (joiner/mover/leaver) automation driven by HR events (Workday, SuccessFactors) | S |

### 1.4 Emergency Access Management (Firefighter)
| ID | Requirement | Priority |
|----|-------------|----------|
| AC-30 | Firefighter ID assignment with owner/controller model, reason codes, and validity periods | M |
| AC-31 | Full session logging: transactions executed, changes made, audit log capture during FF sessions | M |
| AC-32 | Post-session review workflow with controller sign-off and status tracking | M |
| AC-33 | Firefighter usage reporting and dashboards (frequency, top users, unreviewed sessions) | S |

### 1.5 Access Certification (UAR)
| ID | Requirement | Priority |
|----|-------------|----------|
| AC-40 | Periodic user access review campaigns by manager, role owner, or risk owner | M |
| AC-41 | Certification of mitigating control assignments and firefighter assignments | S |
| AC-42 | Auto-removal workflows for rejected access, with completion tracking and audit trail | M |
| AC-43 | Campaign progress dashboards and escalation for overdue reviewers | S |

### 1.6 Role Engineering
| ID | Requirement | Priority |
|----|-------------|----------|
| AC-50 | Role design/maintenance with SoD check at role build time ("clean at construction") | M |
| AC-51 | Role mining from usage data; role comparison and consolidation suggestions | C |
| AC-52 | Business role model (composite/business roles mapped to technical roles across systems) | S |

---

## 2. Process Control (PC)

### 2.1 Control Library & Framework
| ID | Requirement | Priority |
|----|-------------|----------|
| PC-01 | Central control library: control ID, objective, description, type (preventive/detective), nature (manual/automated/IT-dependent), frequency, owner | M |
| PC-02 | Hierarchy: organization > process > subprocess > control, with local vs. central control concept (shared controls localized per org unit) | M |
| PC-03 | Map controls to risks (from RM), regulations/policies, and frameworks (COSO 2013 components & 17 principles, COBIT, ISO 27001, SOX, local regulations) | M |
| PC-04 | Control versioning, review dates, and change history | M |
| PC-05 | Regulation/policy management: policy documents, distribution, acknowledgment tracking | S |

### 2.2 Control Evaluation
| ID | Requirement | Priority |
|----|-------------|----------|
| PC-10 | Control design assessment workflows (adequacy of design) with questionnaires | M |
| PC-11 | Operating effectiveness testing: test plans, sampling guidance, test steps, results, evidence attachments | M |
| PC-12 | Self-assessment campaigns (control owner sign-off) with scheduling and reminders | M |
| PC-13 | Issue management: deficiencies raised from failed tests, severity rating, remediation plans, owner, due dates, status workflow | M |
| PC-14 | Sign-off / certification hierarchy (sub-certification rolling up to CFO/CEO-level SOX-style sign-off) | S |
| PC-15 | Evidence repository with versioning, retention, and audit trail | M |

### 2.3 Continuous Control Monitoring (CCM)
| ID | Requirement | Priority |
|----|-------------|----------|
| PC-20 | Automated monitoring rules against SAP configuration (e.g., password parameters, table logging flags, tolerance limits) via existing RFC connector | M |
| PC-21 | Automated monitoring of master data & transactional patterns (e.g., duplicate vendor bank accounts, PO-invoice mismatches, one-time vendor usage) | S |
| PC-22 | Scheduling engine: run frequency per rule, thresholds, and deficiency auto-creation on exceptions | M |
| PC-23 | Rule builder UI (no-code conditions on extracted datasets) + scripted rules for complex logic | S |
| PC-24 | Monitoring of SoD violations from AC as automated control tests (violations above threshold -> control deficiency) | M |
| PC-25 | Coverage for non-SAP sources through existing connectors (Azure AD config, ServiceNow, etc.) | C |

### 2.4 PC Reporting
| ID | Requirement | Priority |
|----|-------------|----------|
| PC-30 | Control status dashboards by org, process, framework; failed controls; open issues aging | M |
| PC-31 | COSO/COBIT coverage maps (which principles/objectives are covered by which controls, gaps highlighted) | S |
| PC-32 | Audit-ready evidence packages export (control + tests + evidence + sign-offs) | S |

---

## 3. Risk Management (RM)

### 3.1 Risk Register & Taxonomy
| ID | Requirement | Priority |
|----|-------------|----------|
| RM-01 | Enterprise risk register: risk ID, title, description, category taxonomy (strategic, operational, financial, compliance, IT/cyber), org unit, risk owner | M |
| RM-02 | Configurable org hierarchy shared with PC (single org model across the suite) | M |
| RM-03 | Risk appetite and tolerance definitions per category/org unit | S |
| RM-04 | Bilingual risk descriptions (EN/AR) | S |

### 3.2 Assessment & Analysis
| ID | Requirement | Priority |
|----|-------------|----------|
| RM-10 | Inherent and residual risk assessment: likelihood x impact scales (configurable 3x3, 4x4, 5x5), qualitative and quantitative (monetary impact) scoring | M |
| RM-11 | Assessment workflows: periodic campaigns, ad-hoc assessments, multi-assessor consensus | M |
| RM-12 | Heat maps (inherent vs. residual), risk trend over time, top-N risks by org/category | M |
| RM-13 | Key Risk Indicators (KRIs): definition, thresholds, manual or automated data feeds, breach alerts | S |
| RM-14 | Scenario analysis and risk aggregation/roll-up across org hierarchy | C |

### 3.3 Risk Response & Monitoring
| ID | Requirement | Priority |
|----|-------------|----------|
| RM-20 | Response plans: accept, mitigate, transfer, avoid — with actions, owners, due dates, progress tracking | M |
| RM-21 | Link risks to controls in PC (risk-control matrix auto-generated) | M |
| RM-22 | Incident/loss event capture linked to risks (feeding likelihood recalibration) | S |
| RM-23 | Risk review cycles with owner attestation and escalation for overdue reviews | M |

### 3.4 RM Reporting
| ID | Requirement | Priority |
|----|-------------|----------|
| RM-30 | Board/committee risk reports (top risks, movements, appetite breaches, KRI status) exportable to PDF/PPTX | M |
| RM-31 | Risk-control coverage report (risks without controls, controls without risks) | S |

---

## 4. Audit Management (AM)

### 4.1 Audit Universe & Planning
| ID | Requirement | Priority |
|----|-------------|----------|
| AM-01 | Audit universe: auditable entities (org units, processes, systems, projects) with risk scoring | M |
| AM-02 | Risk-based annual/multi-year audit plan, consuming risk scores from RM and violation/deficiency data from AC/PC | M |
| AM-03 | Resource planning: auditor skills, availability, allocation to engagements | S |
| AM-04 | Plan approval workflow and in-year plan changes with audit trail | M |

### 4.2 Engagement Execution
| ID | Requirement | Priority |
|----|-------------|----------|
| AM-10 | Audit engagement lifecycle: announce > plan > fieldwork > report > follow-up, with status workflow | M |
| AM-11 | Work programs: reusable procedure templates per audit type (IT audit, financial, operational, GxP/pharma) | M |
| AM-12 | Working papers: document management with versioning, review notes, preparer/reviewer sign-off, cross-referencing | M |
| AM-13 | Attach external evidence (e.g., EarlyWatch Alert reports, system extracts) to procedures as working papers | M |
| AM-14 | Time tracking per auditor per engagement | S |

### 4.3 Findings & Follow-up
| ID | Requirement | Priority |
|----|-------------|----------|
| AM-20 | Findings: condition, criteria, cause, effect, recommendation; severity rating; management response capture | M |
| AM-21 | Action tracking: owners, due dates, status, evidence of closure, overdue escalation to management | M |
| AM-22 | Link findings to risks (RM), controls (PC), and access violations (AC) | M |
| AM-23 | Follow-up audits and re-testing workflow | S |

### 4.4 AM Reporting
| ID | Requirement | Priority |
|----|-------------|----------|
| AM-30 | Audit report generation from findings (templated Word/PDF output) | M |
| AM-31 | Audit committee dashboards: plan progress, findings by severity/status, overdue actions | M |
| AM-32 | External auditor / regulator read-only access with scoped visibility | C |

---

## 5. Cross-Module Integration (XI) — the differentiator

| ID | Requirement | Priority |
|----|-------------|----------|
| XI-01 | Single org hierarchy, user model, and master data shared across all four modules | M |
| XI-02 | SoD violations (AC) surface as control deficiencies (PC) when thresholds are breached | M |
| XI-03 | Risks (RM) <-> controls (PC) <-> audit findings (AM) fully linked; navigate from any object to related objects | M |
| XI-04 | Audit planning (AM) consumes live risk scores (RM), control failure rates (PC), and violation trends (AC) | M |
| XI-05 | Unified GRC dashboard: one executive view across access risk, control health, enterprise risk, audit status | M |
| XI-06 | Common workflow engine, notification engine, and delegation model across modules | M |
| XI-07 | Framework mapping layer (COSO/COBIT/ISO) shared by PC and AM | S |
| XI-08 | AI assistance: risk description drafting, control suggestion for a given risk, finding write-up assistance, SoD remediation recommendations | C |

---

## 6. Non-Functional (NF) — applies suite-wide

| ID | Requirement | Priority |
|----|-------------|----------|
| NF-01 | Multi-tenant isolation (existing Governex+ architecture) extended to all new modules | M |
| NF-02 | RBAC within the platform itself, including auditor independence (auditors see, cannot edit operational data) | M |
| NF-03 | Full audit trail on all objects (who/what/when, before/after values) — the GRC product must itself be auditable | M |
| NF-04 | Localization: English + Arabic UI with RTL support | S |
| NF-05 | Document retention policies and legal hold | S |
| NF-06 | SSO (Azure AD/Okta via existing connectors), MFA | M |
| NF-07 | API-first: all module functions exposed via REST API | M |
| NF-08 | Report/dashboard export: PDF, Excel, PPTX | M |
| NF-09 | Performance: risk analysis across 50k+ users, permission-level, within batch windows | M |
| NF-10 | Deployment: Docker/Kubernetes, on-prem and cloud (data-residency for Middle East clients) | M |

---

## Suggested Build Sequence

1. **Phase 1 — Risk Management (RM)**: fastest to build, creates the risk backbone PC needs. (~2-3 months MVP)
2. **Phase 2 — Process Control (PC)** including CCM leveraging the existing SAP RFC connector, plus XI-02 (SoD -> deficiencies). (~3-4 months)
3. **Phase 3 — Audit Management (AM)**: built last so it can consume RM/PC/AC data for risk-based planning. (~3 months)
4. **Continuous — XI/NF hardening**: unified dashboard, framework mapping, AI assistance.
