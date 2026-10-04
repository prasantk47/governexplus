# GovernexPlus v1.0 — QA Test Plan

**Version:** 1.1 (revised per Stage 1 review)
**Date:** 2026-10-04
**Author:** QA Architect

---

## 1. Scope

Full functional, RBAC, integration, and export coverage for all 18 test journeys,
101 reports, and every page/action enumerated in the Implementation Guide.

### In Scope
- All 18 test journeys (J01–J18)
- Every guide page and "What you can do" action → traceability matrix §5
- All 101 reports: filter, non-empty fixture data, CSV + XLSX + PDF export, scheduled delivery
- All 22 personas: nav-allowed and nav-denied verified per persona
- Config effects: workflow/SLA/RBAC/notification changes take effect without restart
- Connector lifecycle: add → test-connection → sync → scheduler run-now → history
- BRM: role designer stepper → design-time risk check → approval → SAP generation → diff
- Extended modules: whistleblower, BCM, fraud, survey logic branching
- Template Library behavioral depth: CoW, 3-way update diff, ARA simulation
- Notifications: Mailpit verifies email body for every key event
- Audit log: every write creates an immutable record
- Release hygiene: QA credentials absent from release images

### Out of Scope (v1.0)
- Performance / load testing
- SAP live-system integration (mocked)
- Mobile layout, multi-browser (Chrome only for Playwright)

---

## 2. Test Environments

| Service | URL | Purpose |
|---|---|---|
| API | `http://localhost:9000` | Backend tests (pytest) |
| Frontend | `http://localhost:4500` | E2E Playwright |
| Mailpit UI | `http://localhost:8025` | Email capture verification |
| SAP Mock | `http://localhost:9100` | SAP RFC/SOAP stub |
| AAD Mock | `http://localhost:9101` | Azure AD Graph stub |
| HR Mock | `http://localhost:9102` | HR / SCIM stub |

Stack: `docker compose -f docker-compose.qa.yml up --build -d`
Seed: `python qa/seed_qa.py`

---

## 3. Test Personas (22)

| ID | Role | Key Permissions | Nav Denied (sample) |
|---|---|---|---|
| P01 | Platform Admin | All — cross-tenant | — |
| P02 | Tenant Admin | All within tenant | /platform/tenants |
| P03 | CISO | Risk, EAM, violations, certs | /settings/mass-admin |
| P04 | Compliance Officer | Certifications, SoD, compliance | /eam/ids/create |
| P05 | Risk Manager | Risk register, KRIs, TPRM | /eam/ids |
| P06 | IT Security Admin | SoD rules, roles, connectors | /risk-management/register |
| P07 | Line Manager | Approve requests, certify directs | /settings, /risk/rules |
| P08 | Business User | Submit requests, own certs | /risk/rules, /certifications/campaigns |
| P09 | External Auditor | Read-only: reports, certs, violations | POST anywhere |
| P10 | SOX Control Owner | Process controls, compliance | /settings/mass-admin |
| P11 | FF Owner | Own FF IDs (recert), NOT session user | /eam/controller |
| P12 | FF Controller | All FF log reviews, sign-off | /eam/ids/create |
| P13 | HR Manager | JML events only | /settings, /eam |
| P14 | Process Owner | Controls, deficiency remediation | /settings, /eam/ids |
| P15 | IT Operations | Connectors read, audit log read | /settings/mass-admin |
| P16 | Read-Only Viewer | Dashboard + reports read | POST /access-requests/submit |
| P17 | Firefighter (session user) | Request/end own FF sessions | /eam/controller, /eam/ids/create |
| P18 | Mitigation Monitor | Mitigations, test controls read | /ara/rules, /settings |
| P19 | Internal Auditor | Audit-management write, reports | /settings/mass-admin |
| P20 | Vendor Manager | TPRM full | /settings, /risk/rules |
| P21 | Role Owner | Approve own-role requests, cert | /settings/mass-admin |
| P22 | Risk Owner | Own-risk update, mitigations | /settings, /certifications/campaigns |

---

## 4. Test Journeys (18)

| # | Journey | Priority | New in v1.1 |
|---|---|---|---|
| J01 | Authentication & Session Management | P0 | — |
| J02 | Access Request Full Approval Chain | P0 | — |
| J03 | SoD Conflict Detection & Mitigation | P0 | — |
| J04 | Emergency Access (Firefighter) Lifecycle | P0 | — |
| J05 | Access Certification Campaign | P0 | — |
| J06 | JML — Hire + Transfer + Terminate | P0 | Transfer added |
| J07 | *(merged into J06)* | — | — |
| J08 | Risk Register & KRI Management | P1 | — |
| J09 | Template Library — Full Depth | P1 | CoW behavioral, 3-way diff, ARA sim |
| J10 | Process Controls — Create, Test, Deficiency | P1 | — |
| J11 | TPRM — Vendor Assessment | P1 | — |
| J12 | Reports — All 101 | P1 | Expanded from 10 → 101 |
| J13 | RBAC Enforcement Matrix — All 22 Personas | P0 | Expanded 16 → 22 |
| J14 | Notifications & Audit Log | P1 | — |
| J15 | Config Effects | P1 | **NEW** |
| J16 | Admin & Connectors | P1 | **NEW** |
| J17 | BRM — Role Lifecycle | P1 | **NEW** |
| J18 | Extended Modules | P1 | **NEW** |

---

## 5. Page / Action Traceability Matrix

Every guide page and action → case IDs. Prefix convention:
- `TC-Jnn-nnn` = existing journey case
- `TC-PAGE-nnn` = parametrized page-sweep case (J13 RBAC sweep)
- `TC-RPT-nnn` = report case (J12)

### Dashboard
| Page | Action | Case IDs |
|---|---|---|
| /dashboard | View KPI tiles | TC-PAGE-001 |
| /dashboard | View pending tasks list | TC-PAGE-001 |
| /dashboard | Click task → navigate | TC-PAGE-001 |

### ARA — Access Risk Analysis
| Page | Action | Case IDs |
|---|---|---|
| /ara | View SoD summary stats | TC-PAGE-002 |
| /ara/analyze | Run single-user SoD analysis | TC-J03-001 |
| /ara/analyze | Run bulk analysis | TC-J03-005 |
| /ara/violations | View open violations | TC-J03-001 |
| /ara/violations | Filter by severity / module | TC-PAGE-003 |
| /ara/violations | Assign mitigation | TC-J03-004 |
| /ara/violations | Accept risk | TC-PAGE-003 |
| /ara/mitigations | List mitigations | TC-PAGE-004 |
| /ara/mitigations | Create mitigation | TC-PAGE-004 |
| /ara/mitigations | Link to violation | TC-J03-004 |
| /ara/mitigations | Monitor attestation (P18) | TC-PAGE-004 |
| /ara/simulate | What-if simulation (add role) | TC-J09-010 |
| /ara/simulate | What-if simulation (remove role) | TC-J09-010 |

### Risk / SoD Rules
| Page | Action | Case IDs |
|---|---|---|
| /risk/rules | List SoD rules | TC-PAGE-005 |
| /risk/rules | Create custom rule | TC-PAGE-005 |
| /risk/rules | Edit rule functions/tcodes | TC-PAGE-005 |
| /risk/rules | Disable rule | TC-PAGE-005 |
| /risk/sod-rules | Browse library rules | TC-J09-001 |
| /risk/violations | View violations | TC-J03-001 |
| /risk/simulation | Role-change simulation | TC-J09-010 |
| /risk/entitlements | View entitlement data | TC-PAGE-006 |
| /risk/contextual | Contextual risk view | TC-PAGE-006 |
| /risk/mitigation | Mitigation controls | TC-J03-004 |

### ARM — Access Request Management
| Page | Action | Case IDs |
|---|---|---|
| /access-requests | Submit new request | TC-J02-001 |
| /access-requests | Add to shopping cart | TC-PAGE-007 |
| /access-requests | Submit cart | TC-PAGE-007 |
| /access-requests/pending | View pending approvals (manager) | TC-J02-002 |
| /access-requests/pending | Approve request | TC-J02-002 |
| /access-requests/pending | Reject request | TC-J02-004 |
| /access-requests/pending | View SoD conflict warning | TC-J02-005 |
| /access-requests/history | View request history | TC-PAGE-007 |
| /access-requests | Role Owner approves (own roles) | TC-J02-003 (P21) |

### EAM — Emergency Access Management
| Page | Action | Case IDs |
|---|---|---|
| /firefighter | Dashboard: active sessions, overdue reviews | TC-PAGE-008 |
| /eam/ids | List FF IDs | TC-PAGE-008 |
| /eam/ids/create | Create FF ID with owner/controller | TC-PAGE-008 |
| /eam/sessions/request | Request FF session (P17) | TC-J04-001 |
| /eam/sessions | View own sessions (P11/P17) | TC-J04-002 |
| /eam/sessions/{id}/start | Start session | TC-J04-002 |
| /eam/sessions/{id}/end | End session | TC-J04-003 |
| /eam/controller | Controller: pending reviews | TC-J04-004 |
| /eam/logs | View session activity log | TC-J04-004 |
| /eam/logs | Review + sign-off | TC-J04-004 |
| /eam/logs | Flag violation | TC-J04-005 |
| /eam/ids | Recertify FF ID (P11) | TC-PAGE-008 |

### Certification
| Page | Action | Case IDs |
|---|---|---|
| /certifications | Dashboard: open campaigns, completion | TC-PAGE-009 |
| /certifications/campaigns | Launch campaign from template | TC-J05-001 |
| /certifications/campaigns | View campaign status | TC-PAGE-009 |
| /certifications/campaigns | Close campaign early | TC-PAGE-009 |
| /certifications/my-items | View assigned review items | TC-J05-002 |
| /certifications/my-items | Certify item | TC-J05-003 |
| /certifications/my-items | Revoke item | TC-J05-004 |
| /certifications/{id}/report | Download completion report | TC-J05-005 |
| /certifications | External auditor: read-only | TC-J05-006 |

### JML — Joiner/Mover/Leaver
| Page | Action | Case IDs |
|---|---|---|
| /jml | Dashboard: pending events, SLA | TC-PAGE-010 |
| /jml/onboarding | Create new hire event | TC-J06-001 |
| /jml/onboarding | View provisioning status | TC-J06-002 |
| /jml/transfers | Create transfer event | TC-J06-004 |
| /jml/transfers | Verify old roles removed | TC-J06-005 |
| /jml/transfers | Verify re-cert task created | TC-J06-005 |
| /jml/offboarding | Create termination event | TC-J06-006 |
| /jml/offboarding | Verify access revoked within SLA | TC-J06-006 |
| /jml/policies | Configure JML policies | TC-PAGE-010 |

### BRM — Business Role Management
| Page | Action | Case IDs |
|---|---|---|
| /role-management | Role inventory list | TC-J17-001 |
| /role-management/designer | Open role designer stepper | TC-J17-001 |
| /role-management/designer | Step 1: define role metadata | TC-J17-001 |
| /role-management/designer | Step 2: add auth objects/tcodes | TC-J17-001 |
| /role-management/designer | Step 3: design-time risk check | TC-J17-002 |
| /role-management/designer | Step 4: submit for approval | TC-J17-003 |
| /role-management/designer | Approve role design | TC-J17-003 |
| /role-management/designer | Generate role in SAP (mock) | TC-J17-004 |
| /role-management/comparison | Role comparison diff | TC-J17-005 |
| /role-management/mining | Role mining suggestions | TC-J17-006 |
| /role-management/methodology | Configure role methodology | TC-PAGE-011 |

### Risk Management
| Page | Action | Case IDs |
|---|---|---|
| /risk-management | Dashboard: risk summary, KRI status | TC-PAGE-012 |
| /risk-management/register | Create risk | TC-J08-001 |
| /risk-management/register | Edit risk likelihood/impact | TC-PAGE-012 |
| /risk-management/register | Assign risk owner (P22) | TC-PAGE-012 |
| /risk-management/register | Add treatment action | TC-PAGE-012 |
| /risk-management/heatmap | View heatmap | TC-J08-003 |
| /risk-management/kri | View KRI dashboard | TC-J08-002 |
| /risk-management/kri | Update KRI value | TC-J08-002 |
| /risk-management/incidents | Log incident | TC-PAGE-012 |

### Process Control
| Page | Action | Case IDs |
|---|---|---|
| /process-control | Control library list | TC-J10-001 |
| /process-control | Create control | TC-J10-001 |
| /process-control | Link control to framework | TC-PAGE-013 |
| /process-control/testing | Schedule test | TC-J10-002 |
| /process-control/testing | Record test result (pass) | TC-PAGE-013 |
| /process-control/testing | Record test result (fail) → raise deficiency | TC-J10-003 |
| /process-control/deficiencies | View deficiency tracker | TC-J10-003 |
| /process-control/deficiencies | Assign remediation owner | TC-PAGE-013 |
| /process-control/deficiencies | Mark remediated with evidence | TC-J10-004 |
| /process-control/ccm | View CCM continuous monitoring | TC-PAGE-013 |

### Audit Management
| Page | Action | Case IDs |
|---|---|---|
| /audit-management | Dashboard | TC-PAGE-014 |
| /audit-management/planning | Create audit program | TC-J19-001 (P19) |
| /audit-management/planning | Assign auditors | TC-PAGE-014 |
| /audit-management/engagement | Create audit engagement | TC-PAGE-014 |
| /audit-management/findings | Log finding | TC-PAGE-014 |
| /audit-management/findings | Assign remediation | TC-PAGE-014 |
| /audit-management/findings | Close finding | TC-PAGE-014 |

### Compliance
| Page | Action | Case IDs |
|---|---|---|
| /compliance | Compliance posture dashboard | TC-PAGE-015 |
| /compliance/frameworks | Map control to SOX / ISO27001 | TC-PAGE-015 |
| /compliance/policies | Create policy | TC-PAGE-015 |
| /compliance/attestations | Assign attestation task | TC-PAGE-015 |
| /compliance/attestations | Complete attestation | TC-PAGE-015 |

### TPRM — Third-Party Risk
| Page | Action | Case IDs |
|---|---|---|
| /tprm | Dashboard | TC-PAGE-016 |
| /tprm/vendors | Add vendor | TC-J11-001 |
| /tprm/vendors | Assign tier | TC-J11-001 |
| /tprm/assessments | Issue questionnaire | TC-J11-002 |
| /tprm/assessments | View responses | TC-J11-003 |
| /tprm/assessments | Score vendor | TC-J11-003 |
| /tprm/contracts | Add contract | TC-PAGE-016 |
| /tprm/contracts | Set renewal reminder | TC-PAGE-016 |

### BCM — Business Continuity Management
| Page | Action | Case IDs |
|---|---|---|
| /bcm | Dashboard | TC-J18-006 |
| /bcm/bia | Create BIA | TC-J18-006 |
| /bcm/bia | Record RTO/RPO | TC-J18-006 |
| /bcm/plans | Create BCM plan | TC-J18-007 |
| /bcm/testing | Schedule plan test | TC-J18-007 |
| /bcm/testing | Record test outcome | TC-J18-007 |

### Fraud
| Page | Action | Case IDs |
|---|---|---|
| /fraud | Dashboard | TC-J18-008 |
| /fraud/rules | Create fraud rule | TC-J18-008 |
| /fraud/rules | Enable/disable rule | TC-J18-008 |
| /fraud/alerts | View alerts | TC-J18-009 |
| /fraud/alerts | Escalate to case | TC-J18-009 |
| /fraud/cases | Manage case | TC-J18-009 |
| /fraud/cases | Close case | TC-J18-009 |

### Survey
| Page | Action | Case IDs |
|---|---|---|
| /surveys | Create survey | TC-J18-010 |
| /surveys | Add conditional branch logic | TC-J18-011 |
| /surveys/distribution | Distribute to group | TC-J18-010 |
| /surveys/responses | View response analytics | TC-J18-010 |

### Whistleblower
| Page | Action | Case IDs |
|---|---|---|
| /whistleblower/intake | Submit anonymous report (no auth) | TC-J18-001 |
| /whistleblower/intake | Receive tracking token | TC-J18-001 |
| /whistleblower/track/{ref} | Follow up with token (no auth) | TC-J18-002 |
| /whistleblower | Inbox: view submissions (P19) | TC-J18-003 |
| /whistleblower | Add internal note | TC-J18-003 |
| /whistleblower | Close case | TC-J18-003 |

### Template Library
| Page | Action | Case IDs |
|---|---|---|
| /library/content | Browse items, filter by module/type | TC-J09-001 |
| /library/wizard | Run activation wizard | TC-J09-006 |
| /library/wizard | Map org / owner / system | TC-J09-006 |
| /library/wizard | View per-item background job results | TC-J09-007 |
| /library/active | View active content | TC-J09-002 |
| /library/active | View effective payload | TC-J09-002 |
| /library/active | Customize activated item (CoW) | TC-J09-003 |
| /library/active | Deactivate item | TC-J09-008 |
| /library/active | Reactivate item | TC-J09-008 |
| /library/updates | View pending updates | TC-J09-005 |
| /library/updates | Apply update (unmodified item) | TC-J09-009-a |
| /library/updates | Keep-mine (customized item) | TC-J09-009-b |
| /library/updates | Customized item untouched by global update | TC-J09-009-c |
| /library/pack-builder | Select items for export | TC-J09-004-b |
| /library/pack-builder | Export pack JSON | TC-J09-004-b |

### Reports
| Page | Action | Case IDs |
|---|---|---|
| /reports | Browse catalog | TC-PAGE-017 |
| /reports/{id} | Render with filter | TC-RPT-001 through TC-RPT-101 |
| /reports/{id} | Export CSV | TC-RPT-001 through TC-RPT-101 |
| /reports/{id} | Export XLSX | TC-RPT-001 through TC-RPT-101 |
| /reports/{id} | Export PDF | TC-RPT-001 through TC-RPT-101 |
| /reports/scheduled | Schedule a report | TC-J12-SCHED |
| /reports/scheduled | Verify delivery via Mailpit | TC-J12-SCHED |

### Admin / Settings
| Page | Action | Case IDs |
|---|---|---|
| /settings | View system config | TC-J15-001 |
| /settings/users | Create/edit/disable users | TC-PAGE-018 |
| /settings/connectors | Add SAP connector | TC-J16-001 |
| /settings/connectors | Test connection | TC-J16-002 |
| /settings/connectors | Run sync | TC-J16-003 |
| /settings/connectors | Job Scheduler: run-now | TC-J16-004 |
| /settings/connectors | Job Scheduler: view history | TC-J16-004 |
| /settings/org-rules | Edit ARM workflow stages | TC-J15-001 |
| /settings/org-rules | Change SLA timer | TC-J15-002 |
| /settings/org-rules | Flip RBAC grant (no restart) | TC-J15-003 |
| /settings/mass-admin | Run mass role assignment | TC-PAGE-018 |
| /settings/audit-log | View immutable audit log | TC-J14-004 |
| /platform/tenants | Tenant management (P01 only) | TC-J13-010 |

---

## 6. Report Catalog (101)

### Access Risk / SoD (15)
TC-RPT-001 through TC-RPT-015

| TC | Report Name |
|---|---|
| TC-RPT-001 | SoD Violations Summary |
| TC-RPT-002 | Violations by SoD Rule |
| TC-RPT-003 | Violations by User |
| TC-RPT-004 | Violations Trend (30-day) |
| TC-RPT-005 | Mitigation Effectiveness |
| TC-RPT-006 | Open vs. Remediated Violations |
| TC-RPT-007 | Role-Level SoD Risk |
| TC-RPT-008 | SoD Ruleset Coverage |
| TC-RPT-009 | Top 10 Most Violated Rules |
| TC-RPT-010 | Cross-System SoD Analysis |
| TC-RPT-011 | SoD What-If Simulation |
| TC-RPT-012 | Access Risk by Department |
| TC-RPT-013 | Orphaned Accounts |
| TC-RPT-014 | Dormant Users |
| TC-RPT-015 | Access Pattern Anomalies |

### Access Requests / ARM (8)
| TC | Report Name |
|---|---|
| TC-RPT-016 | Pending Approvals Aging |
| TC-RPT-017 | Request Volume by Period |
| TC-RPT-018 | Approval Time SLA |
| TC-RPT-019 | Rejection Analysis |
| TC-RPT-020 | Auto-Approved vs. Manual |
| TC-RPT-021 | Provisioning Lag |
| TC-RPT-022 | Requests by Role |
| TC-RPT-023 | High-Risk Request Log |

### Emergency Access / EAM (8)
| TC | Report Name |
|---|---|
| TC-RPT-024 | FF Session Activity Log |
| TC-RPT-025 | FF Usage by ID |
| TC-RPT-026 | Controller Sign-Off Status |
| TC-RPT-027 | Overdue Log Reviews |
| TC-RPT-028 | FF Session Duration Analysis |
| TC-RPT-029 | Transactions by FF Session |
| TC-RPT-030 | Critical Tcodes in FF Sessions |
| TC-RPT-031 | FF ID Inventory & Status |

### Certification (8)
| TC | Report Name |
|---|---|
| TC-RPT-032 | Campaign Completion Rate |
| TC-RPT-033 | Certification by Reviewer |
| TC-RPT-034 | Overdue Certifications |
| TC-RPT-035 | Revocations by Campaign |
| TC-RPT-036 | Historical Campaign Comparison |
| TC-RPT-037 | Self-Certification Detection |
| TC-RPT-038 | SoD Conflicts in Certifications |
| TC-RPT-039 | Certification Coverage by System |

### JML (8)
| TC | Report Name |
|---|---|
| TC-RPT-040 | New Hire Provisioning SLA |
| TC-RPT-041 | Termination Access Removal SLA |
| TC-RPT-042 | Transfer Re-Certification Status |
| TC-RPT-043 | Orphaned Access Post-Transfer |
| TC-RPT-044 | JML Event Volume |
| TC-RPT-045 | Role Mapping by Job Title |
| TC-RPT-046 | Department Access Profile |
| TC-RPT-047 | JML Compliance Score |

### BRM (6)
| TC | Report Name |
|---|---|
| TC-RPT-048 | Role Inventory |
| TC-RPT-049 | Role Assignment by User |
| TC-RPT-050 | Role Design Comparison |
| TC-RPT-051 | Composite Role Usage |
| TC-RPT-052 | Role Mining Candidates |
| TC-RPT-053 | Role Clean-Up Recommendations |

### Risk Management (12)
| TC | Report Name |
|---|---|
| TC-RPT-054 | Risk Register Summary |
| TC-RPT-055 | Risk Heatmap |
| TC-RPT-056 | Risk by Category |
| TC-RPT-057 | Risk Trend Over Time |
| TC-RPT-058 | KRI Dashboard |
| TC-RPT-059 | KRI Threshold Breaches |
| TC-RPT-060 | Incident Log |
| TC-RPT-061 | Risk by Owner |
| TC-RPT-062 | Top 10 Risks |
| TC-RPT-063 | Residual Risk Analysis |
| TC-RPT-064 | Risk Treatment Plan Status |
| TC-RPT-065 | Risk Appetite Utilization |

### Process Control (8)
| TC | Report Name |
|---|---|
| TC-RPT-066 | Control Inventory |
| TC-RPT-067 | Control Test Results |
| TC-RPT-068 | Deficiency Tracker |
| TC-RPT-069 | Control Effectiveness Rate |
| TC-RPT-070 | Overdue Control Tests |
| TC-RPT-071 | Deficiency Aging |
| TC-RPT-072 | CCM Continuous Monitoring |
| TC-RPT-073 | SOX ITGC Coverage |

### Audit Management (6)
| TC | Report Name |
|---|---|
| TC-RPT-074 | Audit Plan Status |
| TC-RPT-075 | Audit Findings Summary |
| TC-RPT-076 | Finding Closure Rate |
| TC-RPT-077 | Audit Engagement Log |
| TC-RPT-078 | Finding by Risk Rating |
| TC-RPT-079 | Outstanding Remediation Actions |

### Compliance (4)
| TC | Report Name |
|---|---|
| TC-RPT-080 | Framework Coverage |
| TC-RPT-081 | Compliance Posture by Framework |
| TC-RPT-082 | Policy Attestation Status |
| TC-RPT-083 | Compliance Gaps |

### TPRM (6)
| TC | Report Name |
|---|---|
| TC-RPT-084 | Vendor Inventory by Tier |
| TC-RPT-085 | Assessment Completion Rate |
| TC-RPT-086 | Vendor Risk Distribution |
| TC-RPT-087 | Fourth-Party Risk |
| TC-RPT-088 | Overdue Reassessments |
| TC-RPT-089 | Vendor SLA Performance |

### BCM (4)
| TC | Report Name |
|---|---|
| TC-RPT-090 | BIA Summary |
| TC-RPT-091 | BCM Plan Test Results |
| TC-RPT-092 | RTO/RPO Achievement |
| TC-RPT-093 | Critical Asset Inventory |

### Fraud (4)
| TC | Report Name |
|---|---|
| TC-RPT-094 | Fraud Alert Summary |
| TC-RPT-095 | Case Management Status |
| TC-RPT-096 | Fraud Rule Effectiveness |
| TC-RPT-097 | Alert-to-Case Conversion Rate |

### Survey (2)
| TC | Report Name |
|---|---|
| TC-RPT-098 | Survey Response Summary |
| TC-RPT-099 | Survey Completion Rate |

### Template Library (2)
| TC | Report Name |
|---|---|
| TC-RPT-100 | Library Adoption Rate |
| TC-RPT-101 | Pack Import History |

---

## 7. Exit Criteria

### GO — All required for v1.0 tag:
- [ ] 0 Blocker defects open
- [ ] 0 Critical defects open
- [ ] **Major = 0** unless each exception is explicitly accepted in writing by the product owner
- [ ] 100% of traceability matrix rows executed (all pages, all actions, all 22 personas)
- [ ] All 101 reports: render, non-empty, CSV + XLSX + PDF export verified
- [ ] All 101 reports: at least one scheduled delivery confirmed via Mailpit per module
- [ ] Full 22-persona RBAC matrix green (every nav-allowed + nav-denied verified)
- [ ] All 18 journeys pass on fresh-stack run #1 and run #2 (Stage 4)
- [ ] Mailpit confirms email body (not just subject) for all 12 notification template events
- [ ] `smoke.sh` passes end-to-end from clean `docker compose up`
- [ ] Release images verified: zero QA credentials, QA seed script not bundled

### NO-GO (immediate blocker):
- Any Blocker or Critical open
- Authentication bypass
- Cross-tenant data leakage
- Financial data accessible without SoD check
- QA passwords or seed data present in release Docker image

---

## 8. Release Hygiene (Stage 5 Gate)

The following must be verified before tagging v1.0.0:

1. `docker build -f Dockerfile.prod .` → inspect image layers for `qa/` files → must be absent
2. `grep -r "QaP@ss" built_image/` → must return empty
3. `qa/seed_qa.py` is NOT called in any production entrypoint or Dockerfile
4. `docker-compose.qa.yml` is `.gitignore`d from the production image build context
5. RELEASE_NOTES.md documents that QA credentials are QA-only and never shipped

---

## 9. Stage 2 Execution Instructions

```bash
# 1. Start stack
docker compose -f docker-compose.qa.yml up --build -d
# 2. Wait for health
until curl -sf http://localhost:9000/health; do sleep 3; done
# 3. Seed personas
python qa/seed_qa.py
# 4. Run backend suite — capture baseline
pytest tests/ -v --tb=short 2>&1 | tee qa/pytest_baseline.txt
# 5. Run E2E — capture baseline
npx playwright test --reporter=html,list 2>&1 | tee qa/playwright_baseline.txt
# 6. Tally into DEFECT_LOG.md — do NOT fix anything first
```
