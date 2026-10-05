# GovernexPlus — UAT Master Plan (2000 Tests)

**Version:** 1.0
**Date:** 2026-10-05
**Product:** GovernexPlus v1.0-RC
**Surface:** 912 API endpoints · 100+ pages · 81 DB models · 90+ enums · 22 personas

---

## Coverage Strategy

Every test is **UI-driven** (Playwright) unless marked `[API]` (backend-only features
with no UI). Each test is a standalone spec that logs in, performs actions, asserts
outcomes, and captures screenshots as evidence.

### Test ID Convention
`UAT-{group}{sequence}` — e.g., `UAT-A001`, `UAT-B042`, `UAT-G015`

### Priority Tiers
| Tier | Count | Gate Rule |
|------|-------|-----------|
| **@P0** | ~600 | Must all PASS for release |
| **@P1** | ~900 | Failures accepted in writing |
| **@P2** | ~500 | Nice-to-have, logged only |

---

## Group A — Authentication, Session & Navigation (80 tests)

### A.1 Login & Authentication (UAT-A001..A025) — @P0

| ID | Test | Steps |
|----|------|-------|
| A001 | Valid login — Business User | Enter credentials → dashboard loads, JWT in storage |
| A002 | Valid login — Platform Admin | Platform admin sees cross-tenant view |
| A003 | Valid login — Tenant Admin | Tenant admin sees tenant-scoped view |
| A004 | Valid login — CISO | CISO sees risk-focused dashboard |
| A005 | Valid login — Compliance Officer | Compliance nav items visible |
| A006 | Valid login — Risk Manager | Risk management nav items visible |
| A007 | Valid login — IT Security Admin | Security admin nav items visible |
| A008 | Valid login — Line Manager | Manager sees approval items |
| A009 | Valid login — Business User (Requestor) | Requestor sees request access |
| A010 | Valid login — External Auditor | Read-only view enforced |
| A011 | Valid login — SOX Control Owner | Process control access |
| A012 | Valid login — FF Owner | Firefighter management access |
| A013 | Valid login — FF Controller | FF monitoring access |
| A014 | Valid login — HR Manager | JML/Identity access |
| A015 | Valid login — Internal Auditor | Audit management access |
| A016 | Valid login — Vendor Manager | TPRM access |
| A017 | Valid login — Role Owner | Role studio access |
| A018 | Invalid password — error shown | Wrong password → error toast, no redirect |
| A019 | Empty username — validation | Submit empty form → validation error |
| A020 | Empty password — validation | Username only → validation error |
| A021 | Account lockout after N failures | Exceed threshold → lockout message |
| A022 | Session persistence — page refresh | Refresh after login → stays logged in |
| A023 | Session timeout — idle expiry | Wait > timeout → redirect to login |
| A024 | Logout — clears JWT | Click sign out → JWT removed, redirect |
| A025 | Direct URL while logged out | Navigate /dashboard → redirect to /login |

### A.2 Dashboard & Navigation (UAT-A026..A050) — @P0

| ID | Test | Steps |
|----|------|-------|
| A026 | Command Center loads | Stats cards render with data |
| A027 | Health score widget | GRC health score shows 0-100 |
| A028 | Attention items list | Priority items listed |
| A029 | Sidebar — all module groups visible | 8+ top-level groups |
| A030 | Sidebar — expand/collapse groups | Click group → children toggle |
| A031 | Navigate to Access Requests | Page loads without error |
| A032 | Navigate to Certification | Page loads without error |
| A033 | Navigate to Risk Dashboard | Page loads without error |
| A034 | Navigate to Firefighter | Page loads without error |
| A035 | Navigate to Risk Management | Page loads without error |
| A036 | Navigate to Process Control | Page loads without error |
| A037 | Navigate to Audit Management | Page loads without error |
| A038 | Navigate to JML | Page loads without error |
| A039 | Navigate to TPRM | Page loads without error |
| A040 | Navigate to Fraud | Page loads without error |
| A041 | Navigate to BCM | Page loads without error |
| A042 | Navigate to Whistleblower | Page loads without error |
| A043 | Navigate to Surveys | Page loads without error |
| A044 | Navigate to Reports | Page loads without error |
| A045 | Navigate to Template Library | Page loads without error |
| A046 | Navigate to Settings | Page loads without error |
| A047 | Dark mode toggle | Theme switches, persists on refresh |
| A048 | Light mode toggle back | Theme reverts cleanly |
| A049 | Mobile responsive — sidebar collapse | 375px width → hamburger menu |
| A050 | Mobile responsive — menu open | Hamburger → drawer with all items |

### A.3 RBAC Enforcement (UAT-A051..A080) — @P0

| ID | Test | Steps |
|----|------|-------|
| A051 | Business User cannot access Settings | Navigate /settings → blocked/redirect |
| A052 | Business User cannot access Risk Rules | Navigate /risk/rules → blocked |
| A053 | Business User cannot access EAM | Navigate /privileged-access → blocked |
| A054 | External Auditor — read-only on certifications | View cert → no edit buttons |
| A055 | External Auditor — cannot create campaigns | No "Create Campaign" button |
| A056 | External Auditor — cannot modify risks | No edit/create on risk pages |
| A057 | Line Manager — cannot access SoD rules | /risk/rules → blocked |
| A058 | Line Manager — cannot access EAM IDs | /privileged-access → limited |
| A059 | SOX Control Owner — cannot access mass admin | /settings/mass-admin → blocked |
| A060 | Tenant Admin — cannot access platform tenants | /admin/tenants → blocked |
| A061 | Platform Admin — sees all tenants | Cross-tenant list visible |
| A062 | Platform Admin — can switch tenant context | Tenant selector works |
| A063 | FF Owner — can approve FF requests | FF approval buttons visible |
| A064 | FF Controller — can monitor sessions | Monitoring dashboard loads |
| A065 | HR Manager — can manage JML policies | CRUD on JML policies |
| A066 | Vendor Manager — can manage vendors | CRUD on vendors |
| A067 | Internal Auditor — can manage audits | CRUD on audit engagements |
| A068 | Role Owner — can access role studio | Pack builder loads |
| A069 | Risk Manager — can access TPRM | TPRM overview loads |
| A070 | Compliance Officer — can manage certs | Campaign CRUD available |
| A071 | CISO — can view risk intelligence | ARA dashboard loads |
| A072 | IT Security — can manage SoD rules | Rule CRUD available |
| A073 | Process Owner — can manage controls | Process control CRUD |
| A074 | Mitigation Monitor — can view mitigations | Mitigation dashboard loads |
| A075 | Read-Only Viewer — all pages read-only | No create/edit/delete buttons |
| A076 | Risk Owner — can manage risk register | Risk CRUD available |
| A077 | Firefighter Session User — can start sessions | FF session check-in available |
| A078 | Multi-role user — combined permissions | User with 2 roles sees union of nav |
| A079 | Tenant isolation — User A cannot see Tenant B data | Cross-tenant query blocked |
| A080 | API RBAC — direct API call without permission | 403 returned |

---

## Group B — Access Request Lifecycle (130 tests)

### B.1 Submit Access Request (UAT-B001..B030) — @P0

| ID | Test | Steps |
|----|------|-------|
| B001 | Open request page | Role catalog / search loads |
| B002 | Search roles by name | Filter works, results update |
| B003 | Search roles by description | Keyword search on descriptions |
| B004 | Browse role catalog | Pagination works |
| B005 | View role details | Click role → detail popup/panel |
| B006 | Add single role to cart | Cart badge increments |
| B007 | Add multiple roles to cart | Cart shows all selected |
| B008 | Remove role from cart | Cart count decrements |
| B009 | Clear entire cart | Cart empties |
| B010 | Enter business justification | Text field accepts input |
| B011 | Submit request — success | Toast "submitted", request ID shown |
| B012 | Submit request — missing justification | Validation error |
| B013 | Submit request — empty cart | Validation error |
| B014 | View My Requests after submit | New request in list, status "Pending" |
| B015 | Request detail view | Shows role, justification, status, timeline |
| B016 | Cancel pending request | Status changes to "Cancelled" |
| B017 | Re-submit after cancel | New request created |
| B018 | Duplicate request prevention | Warning if same role already requested |
| B019 | Request for another user (delegation) | Submit on behalf of another user |
| B020 | Bulk access request (CSV) | Upload CSV → batch creation |
| B021 | Bulk request — invalid CSV format | Validation errors shown |
| B022 | Bulk request — partial success | Some created, some errored |
| B023 | Model User — select template | Template loads with pre-defined roles |
| B024 | Model User — apply template | Roles from template added to request |
| B025 | Shopping cart — create cart via API | Cart ID returned |
| B026 | Shopping cart — add to cart | Item added |
| B027 | Shopping cart — check conflicts | Conflict analysis runs |
| B028 | Shopping cart — submit cart | Cart converted to access request |
| B029 | Request with long justification (2000 chars) | Accepted without truncation |
| B030 | Request with special characters in justification | XSS/injection safe |

### B.2 Approve / Reject Access Request (UAT-B031..B060) — @P0

| ID | Test | Steps |
|----|------|-------|
| B031 | Approver sees pending requests | Approval inbox populated |
| B032 | Approver opens request detail | Full request info visible |
| B033 | Risk preview in approval | SoD analysis shown |
| B034 | Approve request — success | Status → "Approved", toast |
| B035 | Reject request — with reason | Status → "Rejected", reason saved |
| B036 | Reject request — without reason | Validation: reason required |
| B037 | Bulk approve — select multiple | Multi-select checkboxes |
| B038 | Bulk approve — confirm | All selected → "Approved" |
| B039 | Bulk reject — with single reason | All selected → "Rejected" |
| B040 | Approver comment on request | Comment saved, visible to requester |
| B041 | Requester sees approval status | "Approved" in My Requests |
| B042 | Requester sees rejection + reason | "Rejected" with reason text |
| B043 | Multi-level approval — first approver | First level → "Pending Level 2" |
| B044 | Multi-level approval — second approver | Second level → "Approved" |
| B045 | Approval delegation — OOO setup | Delegate to backup approver |
| B046 | Approval delegation — backup receives | Backup sees delegated requests |
| B047 | Approval timeout / escalation | SLA exceeded → escalated |
| B048 | Approver management — create approver | New approver configured |
| B049 | Approver management — edit approver | Approver details updated |
| B050 | Approver management — deactivate | Approver marked inactive |
| B051 | Approver management — toggle availability | Online/offline toggle |
| B052 | Approver management — OOO dates | Date range set |
| B053 | Approval workflow visualization | Workflow steps shown |
| B054 | Approval history / audit trail | All actions timestamped |
| B055 | Concurrent approval — two approvers | No double-approval |
| B056 | Approve already-cancelled request | Error: request no longer pending |
| B057 | Request list — sort by date | Sorting works |
| B058 | Request list — sort by status | Sorting works |
| B059 | Request list — filter by status | Filter works |
| B060 | Request list — pagination | Next/prev page works |

### B.3 SoD & Risk Analysis in Requests (UAT-B061..B090) — @P0

| ID | Test | Steps |
|----|------|-------|
| B061 | Request role with SoD conflict | Warning displayed |
| B062 | SoD conflict details shown | Conflicting roles, rule ID, severity |
| B063 | Submit despite SoD warning | Request created with risk flag |
| B064 | SoD blocked request (if configured) | Submission prevented |
| B065 | Risk preview — single role | Risk score shown |
| B066 | Risk preview — multiple roles | Cumulative risk shown |
| B067 | Risk simulation — what-if analysis | Simulate adding role → risk delta |
| B068 | ARA integration in request flow | ARA violations listed |
| B069 | Mitigation suggestion in request | Suggested mitigations shown |
| B070 | Accept risk with justification | Risk acceptance recorded |
| B071 | View violation after request approved | Violation in risk dashboard |
| B072 | SoD rule with custom rule | Custom rule triggers correctly |
| B073 | Cross-system SoD check | SoD across SAP + non-SAP |
| B074 | Entitlement-level SoD | Auth object level conflict |
| B075 | Transaction code SoD | Tcode pair conflict |
| B076 | Composite role SoD | Child roles checked |
| B077 | Risk simulation — empty state | No roles → "No risks found" |
| B078 | Risk simulation — high severity | Critical severity highlighted |
| B079 | Violation remediation tracking | Remediation status updated |
| B080 | Risk analysis report export | PDF/CSV export works |
| B081 | Request with mitigation attached | Mitigation linked to request |
| B082 | Mitigation control effectiveness | Control rated as effective/ineffective |
| B083 | Risk score calculation accuracy | Score matches rule configuration |
| B084 | Violation count on dashboard | Count matches actual violations |
| B085 | Violation list — sort by severity | Sorting works |
| B086 | Violation list — filter by user | Filter works |
| B087 | Violation list — filter by rule | Filter works |
| B088 | Violation detail — AI explanation | AI-generated narrative shown |
| B089 | Violation detail — remediation actions | Action buttons available |
| B090 | Violation export | Export to CSV/PDF |

### B.4 Role Management (UAT-B091..B130) — @P1

| ID | Test | Steps |
|----|------|-------|
| B091 | Role list loads | All roles displayed |
| B092 | Role search by name | Filter works |
| B093 | Role detail view | Click role → permissions, assignments |
| B094 | Create role — basic | Name, description → saved |
| B095 | Create role — with permissions | Add auth objects → saved |
| B096 | Edit role — change name | Updated in list |
| B097 | Edit role — add permission | New permission saved |
| B098 | Edit role — remove permission | Permission removed |
| B099 | Delete/deprecate role | Role marked deprecated |
| B100 | Role designer — canvas loads | Visual role builder |
| B101 | Role designer — add auth object | Drag/select → added to role |
| B102 | Role designer — test role | Test execution runs |
| B103 | Role catalog — filter by type | Single/composite filter |
| B104 | Role catalog — sort by risk | Risk-based sorting |
| B105 | Role assignment list | Users assigned to role |
| B106 | Business role management | BRM hierarchy view |
| B107 | Role methodology — view | Naming conventions page |
| B108 | Role methodology — update | Save methodology changes |
| B109 | Pack Builder — create pack | New pack saved |
| B110 | Pack Builder — add roles to pack | Roles added |
| B111 | Pack Builder — save version | Version v1 created |
| B112 | Pack Builder — new version | Version incremented |
| B113 | Pack Builder — risk check | SoD analysis on pack |
| B114 | Pack Builder — compare versions | Diff view between versions |
| B115 | Role Mining — configure params | Min users, threshold set |
| B116 | Role Mining — run analysis | Mining job executes |
| B117 | Role Mining — view results | Suggested clusters shown |
| B118 | Role Mining — create from cluster | Role pre-populated from mining |
| B119 | Role Intelligence — view analytics | Role usage patterns |
| B120 | Role Intelligence — recommendations | Optimization suggestions |
| B121 | Role Drift Detection — view drifts | Drifted roles listed |
| B122 | Role Drift Detection — compare | Before/after diff |
| B123 | Role Redesign — trigger | Redesign workflow starts |
| B124 | Role Redesign — review proposal | Proposed changes shown |
| B125 | Role transport management | Transport list |
| B126 | Role transport — create request | Transport request created |
| B127 | Custom tcode management — list | Custom tcodes shown |
| B128 | Custom tcode — add | New tcode added |
| B129 | Org rules — list | Organizational rules shown |
| B130 | Org rules — create/edit/delete | CRUD works |

---

## Group C — Certification & Compliance (150 tests)

### C.1 Certification Campaigns (UAT-C001..C040) — @P0

| ID | Test | Steps |
|----|------|-------|
| C001 | Campaign list loads | Campaigns displayed |
| C002 | Campaign statistics | Total, active, completed counts |
| C003 | Create campaign — basic | Name, type, scope → saved |
| C004 | Create campaign — user access review | Review type configured |
| C005 | Create campaign — role review | Role-based review |
| C006 | Create campaign — SoD review | SoD-focused review |
| C007 | Create campaign — set reviewers | Reviewer assignment |
| C008 | Create campaign — set deadline | Due date configured |
| C009 | Launch campaign | Status → "Active" |
| C010 | Campaign progress bar | Shows % complete |
| C011 | Reviewer — see assigned items | My Reviews populated |
| C012 | Reviewer — open review item | User access details shown |
| C013 | Reviewer — certify (approve) | Item marked certified |
| C014 | Reviewer — revoke (remove access) | Item marked for revocation |
| C015 | Reviewer — flag for review | Item flagged |
| C016 | Reviewer — add comment | Comment saved |
| C017 | Reviewer — bulk certify | Select all → certify |
| C018 | Reviewer — bulk revoke | Select all → revoke |
| C019 | Campaign dashboard — completion stats | Real-time progress |
| C020 | Campaign dashboard — reviewer breakdown | Per-reviewer progress |
| C021 | Campaign deadline reminder | Notification before deadline |
| C022 | Campaign auto-close on completion | All items reviewed → "Completed" |
| C023 | Campaign report generation | Summary report available |
| C024 | Campaign audit trail | All decisions logged |
| C025 | Revocation execution | Revoked roles actually removed |
| C026 | Re-certification after revocation | User requests role back |
| C027 | Campaign template reuse | Clone previous campaign |
| C028 | Campaign filter by status | Active/Completed/Draft filter |
| C029 | Campaign sort by date | Sorting works |
| C030 | Campaign search | Search by name |
| C031 | Multiple concurrent campaigns | Two active campaigns |
| C032 | Campaign with 100+ items | Performance test |
| C033 | Campaign closed — no further reviews | Reviewed items locked |
| C034 | Partial review — deadline passed | Unreviewed items auto-handled |
| C035 | Campaign edit while active | Some fields editable |
| C036 | Campaign cancel | Status → "Cancelled" |
| C037 | Campaign re-open | Cancelled → re-activated |
| C038 | Certification evidence package | Evidence PDF generated |
| C039 | Cross-campaign reporting | Summary across campaigns |
| C040 | Campaign integration with JML | Leaver triggers revocation |

### C.2 Process Control (UAT-C041..C080) — @P1

| ID | Test | Steps |
|----|------|-------|
| C041 | Control library loads | All controls displayed |
| C042 | Create control — preventive | Control type = Preventive |
| C043 | Create control — detective | Control type = Detective |
| C044 | Create control — corrective | Control type = Corrective |
| C045 | Control detail view | Full control information |
| C046 | Edit control | Updated successfully |
| C047 | Control status lifecycle | Draft → Active → Under Review → Retired |
| C048 | Create control test | Test planned |
| C049 | Execute control test — walkthrough | Test type = Walkthrough |
| C050 | Execute control test — design | Test type = Design |
| C051 | Execute control test — OE | Test type = Operating Effectiveness |
| C052 | Record test result — effective | Result = Effective |
| C053 | Record test result — ineffective | Result = Ineffective |
| C054 | Test evidence attachment | Evidence linked to test |
| C055 | Deficiency from failed test | Deficiency created |
| C056 | Deficiency list | All deficiencies shown |
| C057 | Deficiency severity classification | Significant Deficiency / Material Weakness / Control Gap |
| C058 | Deficiency remediation tracking | Remediation plan attached |
| C059 | Deficiency status lifecycle | Open → In Remediation → Remediated → Verified |
| C060 | Control Self-Assessment (CSA) | CSA form submitted |
| C061 | CCM rule creation | Automated control monitor |
| C062 | CCM rule execution | Rule runs, results captured |
| C063 | CCM dashboard | Exception summary |
| C064 | CCM exception detection | Exception flagged |
| C065 | CCM exception review | Accept/investigate exception |
| C066 | Sign-off certification | SOX sign-off |
| C067 | Sign-off with exceptions | Certified with noted exceptions |
| C068 | Sign-off refused | Refused with reason |
| C069 | Sub-process creation | Sub-process linked to parent |
| C070 | Sub-process hierarchy | Tree view |
| C071 | Control-to-process mapping | Control linked to process |
| C072 | Control objective management | Objectives CRUD |
| C073 | Framework requirement mapping | Control → framework requirement |
| C074 | Evidence management — upload | Evidence file uploaded |
| C075 | Evidence management — link to control | Evidence linked |
| C076 | Evidence status lifecycle | Active → Archived |
| C077 | Policy document management | Policy CRUD |
| C078 | Policy version management | Policy versioning |
| C079 | Questionnaire management | Question library |
| C080 | Questionnaire response | Response submitted |

### C.3 Audit Management (UAT-C081..C120) — @P1

| ID | Test | Steps |
|----|------|-------|
| C081 | Audit dashboard loads | Pipeline overview |
| C082 | Create audit plan — annual | Plan type = Annual |
| C083 | Create audit plan — special | Plan type = Special |
| C084 | Risk-based plan generation | Auto-generate from risk data |
| C085 | Audit plan approval workflow | Plan → Pending Approval → Approved |
| C086 | Create engagement | Engagement linked to plan |
| C087 | Engagement type — financial | Type = Financial |
| C088 | Engagement type — IT | Type = IT |
| C089 | Engagement type — compliance | Type = Compliance |
| C090 | Engagement status lifecycle | Planned → Announced → Fieldwork → Draft Report → Final Report → Closed |
| C091 | Announcement creation | Audit announcement sent |
| C092 | Work program creation | Program steps defined |
| C093 | Audit procedure management | Procedures CRUD |
| C094 | Procedure status tracking | Not Started → In Progress → Completed → Reviewed |
| C095 | Workpaper management | Workpaper CRUD |
| C096 | Workpaper review workflow | Draft → Reviewed / Revision Needed |
| C097 | Finding creation | Finding with severity, description |
| C098 | Finding severity — critical | Severity = Critical |
| C099 | Finding severity — high | Severity = High |
| C100 | Finding severity — observation | Severity = Observation |
| C101 | Finding status lifecycle | Draft → Discussed → Final → Mgmt Response → Closed |
| C102 | Management response to finding | Response recorded |
| C103 | Management action plan | Action plan attached to finding |
| C104 | Action tracking | Action status: Open → In Progress → Completed |
| C105 | Overdue action alert | Overdue actions flagged |
| C106 | Auditor time tracking | Time entries recorded |
| C107 | Auditor resource management | Resources allocated |
| C108 | Audit dimension management | Business process, legal entity dimensions |
| C109 | Audit entity management | Auditable entities CRUD |
| C110 | Entity risk rating | Risk-based prioritization |
| C111 | Audit committee report | Committee report generation |
| C112 | Engagement list — filter by status | Status filter works |
| C113 | Engagement list — sort by date | Sorting works |
| C114 | Finding list — filter by severity | Severity filter works |
| C115 | Finding export | Export to CSV/PDF |
| C116 | Audit trail for engagement | All actions logged |
| C117 | Follow-up engagement | Follow-up linked to original |
| C118 | Multiple concurrent engagements | Two engagements active |
| C119 | Engagement with 50+ findings | Performance test |
| C120 | Read-only access for ext auditor | P09 sees but cannot edit |

### C.4 Frameworks & Compliance (UAT-C121..C150) — @P1

| ID | Test | Steps |
|----|------|-------|
| C121 | Framework list | Available frameworks shown |
| C122 | Framework — COSO | COSO framework loaded |
| C123 | Framework — COBIT | COBIT framework loaded |
| C124 | Framework — ISO 27001 | ISO framework loaded |
| C125 | Framework — SOX | SOX framework loaded |
| C126 | Framework — Custom | Custom framework created |
| C127 | Framework requirements | Requirements listed |
| C128 | Requirement-to-control mapping | Mapping CRUD |
| C129 | Compliance dashboard | Compliance status overview |
| C130 | Compliance assessment | Assessment form |
| C131 | Security controls dashboard | Controls overview |
| C132 | Security controls list | All controls shown |
| C133 | Security control detail | Control configuration |
| C134 | Security control — create | New control saved |
| C135 | Security control — evaluate | Evaluation runs |
| C136 | Security control — batch evaluate | Batch eval runs |
| C137 | Security control — import CSV | CSV import works |
| C138 | Security control — import template | Template download works |
| C139 | Security control — value mappings | Parameter mappings shown |
| C140 | Security control categories | Category filter works |
| C141 | Security control risk rating | Green/Yellow/Red rating |
| C142 | SoD rule library — list all | 120+ rules shown |
| C143 | SoD rule — view detail | Rule detail with tcodes |
| C144 | SoD rule — create custom | Custom rule saved |
| C145 | SoD rule — edit | Rule updated |
| C146 | SoD rule — delete | Rule removed |
| C147 | SoD rule — enable/disable | Toggle works |
| C148 | SoD rule — filter by module | FI/MM/SD filter |
| C149 | SoD rule — search | Search by name/description |
| C150 | SoD rule — export | Export to CSV |

---

## Group D — Risk Management (150 tests)

### D.1 Enterprise Risk Register (UAT-D001..D040) — @P0

| ID | Test | Steps |
|----|------|-------|
| D001 | Risk register loads | All risks displayed |
| D002 | Create risk — strategic | Category = Strategic |
| D003 | Create risk — operational | Category = Operational |
| D004 | Create risk — financial | Category = Financial |
| D005 | Create risk — compliance | Category = Compliance |
| D006 | Create risk — IT/Cyber | Category = IT_Cyber |
| D007 | Create risk — reputational | Category = Reputational |
| D008 | Risk detail view | Full risk information |
| D009 | Edit risk | Updated successfully |
| D010 | Risk status lifecycle | Identified → Assessed → Mitigated → Accepted → Closed |
| D011 | Risk assessment — create | Assessment for risk |
| D012 | Risk assessment — periodic | Type = Periodic |
| D013 | Risk assessment — ad-hoc | Type = Ad-hoc |
| D014 | Risk assessment — consensus | Type = Consensus |
| D015 | Risk assessment — likelihood rating | 1-5 scale |
| D016 | Risk assessment — impact rating | 1-5 scale |
| D017 | Risk heatmap | Likelihood × Impact matrix |
| D018 | Risk heatmap — drill-down | Click cell → risks in that zone |
| D019 | Risk appetite setting | Appetite per category |
| D020 | Risk appetite breach detection | Risk exceeds appetite → alert |
| D021 | Risk response — accept | Response type = Accept |
| D022 | Risk response — mitigate | Response type = Mitigate |
| D023 | Risk response — transfer | Response type = Transfer |
| D024 | Risk response — avoid | Response type = Avoid |
| D025 | Risk response tracking | Planned → In Progress → Completed |
| D026 | Risk incident reporting | Incident logged |
| D027 | Risk incident — severity | Low/Medium/High/Critical |
| D028 | Risk incident — investigation | Incident investigated |
| D029 | Risk incident — resolution | Incident resolved |
| D030 | Business objective management | Objectives CRUD |
| D031 | Objective-risk linking | Risk linked to objective |
| D032 | Risk scenario creation | Scenario defined |
| D033 | Risk scenario — types | Single/Cascading/Compound/Stress |
| D034 | Risk scenario — velocity | Sudden/Rapid/Moderate/Gradual |
| D035 | Monte Carlo simulation | Simulation runs |
| D036 | Monte Carlo — distribution types | Normal/Lognormal/Triangular |
| D037 | Monte Carlo — results | Probability distribution shown |
| D038 | Risk opportunity management | Opportunity CRUD |
| D039 | Risk dashboard KPIs | Key metrics displayed |
| D040 | Risk register export | Export to CSV/PDF |

### D.2 KRI Dashboard (UAT-D041..D060) — @P0

| ID | Test | Steps |
|----|------|-------|
| D041 | KRI dashboard loads | All KRIs displayed |
| D042 | Create KRI | New KRI defined |
| D043 | KRI — link to risk | KRI associated with risk |
| D044 | KRI — set thresholds | Warning/breach thresholds |
| D045 | Record KRI measurement | Value recorded |
| D046 | KRI status — normal | Within threshold → green |
| D047 | KRI status — warning | Near threshold → yellow |
| D048 | KRI status — breach | Exceeds threshold → red |
| D049 | KRI trend chart | Time series visualization |
| D050 | KRI alert on breach | Alert triggered |
| D051 | KRI measurement history | Historical values shown |
| D052 | KRI bulk measurement | Multiple KRIs at once |
| D053 | KRI dashboard filter | Filter by status/risk |
| D054 | KRI dashboard sort | Sort by status/name |
| D055 | KRI export | Export to CSV |
| D056 | Incident log | All incidents listed |
| D057 | Incident — create | New incident reported |
| D058 | Incident — link to risk | Risk association |
| D059 | Incident — investigation notes | Notes added |
| D060 | Incident — close | Incident resolved and closed |

### D.3 Access Risk Analysis — ARA (UAT-D061..D090) — @P0

| ID | Test | Steps |
|----|------|-------|
| D061 | ARA dashboard loads | Risk overview |
| D062 | Run full analysis — all users | Analysis completes |
| D063 | Run analysis — specific user | Single user analysis |
| D064 | Analysis results — violations | Violations listed |
| D065 | Violation detail view | Full violation info |
| D066 | Violation — user info | Affected user shown |
| D067 | Violation — rule info | Triggered rule shown |
| D068 | Violation — conflicting roles | Conflicting roles listed |
| D069 | Violation — severity | Low/Medium/High/Critical |
| D070 | Violation — AI narrative | AI-generated explanation |
| D071 | Violation persistence | Violations saved to DB |
| D072 | Violation status update | Open → In Progress → Mitigated |
| D073 | Violation — accept risk | Risk acceptance recorded |
| D074 | Violation — false positive | Marked as false positive |
| D075 | Violation — remediation | Remediation plan attached |
| D076 | Violation list — filter severity | Filter works |
| D077 | Violation list — filter user | Filter works |
| D078 | Violation list — filter rule | Filter works |
| D079 | Violation list — sort | Sort by date/severity |
| D080 | Violation export | CSV/PDF export |
| D081 | ARA — cross-system analysis | Multi-system SoD |
| D082 | ARA — entitlement-level | Auth object analysis |
| D083 | ARA — usage-aware scoring | Usage data impacts score |
| D084 | ARA — batch analysis | Multiple users at once |
| D085 | ARA — scheduled analysis | Automated periodic run |
| D086 | ARA — rule library integration | Library rules used |
| D087 | ARA — custom rule analysis | Custom rules evaluated |
| D088 | Mitigation controls list | All mitigations shown |
| D089 | Mitigation control — create | New mitigation saved |
| D090 | Mitigation control — link to violation | Mitigation assigned |

### D.4 Mitigation & Monitoring (UAT-D091..D120) — @P1

| ID | Test | Steps |
|----|------|-------|
| D091 | Mitigation control detail | Full mitigation info |
| D092 | Mitigation control — edit | Updated successfully |
| D093 | Mitigation — effectiveness review | Effectiveness rated |
| D094 | Mitigation — periodic review | Review scheduled |
| D095 | Mitigation monitoring dashboard | All monitors shown |
| D096 | Mitigation monitor — create | New monitor configured |
| D097 | Mitigation monitor — alert | Alert on ineffective control |
| D098 | Risk rule management — list | All rules shown |
| D099 | Risk rule — create | New rule saved |
| D100 | Risk rule — edit | Rule updated |
| D101 | Risk rule — delete | Rule removed |
| D102 | Risk rule — enable/disable | Toggle works |
| D103 | Risk rule — tenant preferences | Per-tenant rule config |
| D104 | Contextual risk analysis | Contextual factors applied |
| D105 | Entitlement intelligence | Entitlement matrix view |
| D106 | Cross-system risk view | Multi-system risk rollup |
| D107 | Risk intelligence dashboard | GRC intelligence overview |
| D108 | AI risk remediation suggestions | AI suggests fixes |
| D109 | AI risk narrative | AI explains risk in business terms |
| D110 | Risk simulation — add role | What-if: adding a role |
| D111 | Risk simulation — remove role | What-if: removing a role |
| D112 | Risk simulation — compare | Before/after comparison |
| D113 | Risk report — heatmap | Heatmap report generated |
| D114 | Risk report — trend | Trend report over time |
| D115 | Risk report — top 10 risks | Top risks report |
| D116 | Risk report — by category | Category breakdown |
| D117 | Risk report — by owner | Owner responsibility report |
| D118 | Risk dashboard widgets | All widgets render |
| D119 | Risk dashboard refresh | Data refreshes on reload |
| D120 | Risk data export — full register | Complete export |

### D.5 Additional Risk Features (UAT-D121..D150) — @P2

| ID | Test | Steps |
|----|------|-------|
| D121 | Digital twin — view | Digital twin visualization |
| D122 | Digital twin — create | Twin created |
| D123 | Retention policy — list | Policies shown |
| D124 | Retention policy — create | New policy saved |
| D125 | Retention policy — apply | Policy applied to data |
| D126 | Model user — list templates | Templates shown |
| D127 | Model user — create template | New template saved |
| D128 | Model user — apply template | Template applied |
| D129 | Model user — delete template | Template removed |
| D130 | Org hierarchy — view | Org tree displayed |
| D131 | Org hierarchy — create node | New org unit |
| D132 | Org hierarchy — edit node | Unit updated |
| D133 | Org hierarchy — delete node | Unit removed |
| D134 | Access reports — user access | User access report |
| D135 | Access reports — role usage | Role usage report |
| D136 | Access reports — SoD summary | SoD summary report |
| D137 | Access reports — critical access | Critical access report |
| D138 | Access reports — inactive users | Inactive users report |
| D139 | Access reports — change log | Access change log |
| D140 | User profiles — view | Profile details |
| D141 | User profiles — access summary | All access shown |
| D142 | User profiles — risk profile | Risk visualization |
| D143 | User profiles — activity log | Recent activity |
| D144 | User profiles — entitlements | Auth objects listed |
| D145 | User profiles — role history | Role assignment history |
| D146 | Dashboard — risk metrics | Risk metric widgets |
| D147 | Dashboard — compliance status | Compliance widget |
| D148 | Dashboard — pending actions | Action items count |
| D149 | Dashboard — recent activity | Activity feed |
| D150 | Dashboard — quick actions | Action shortcuts |

---

## Group E — Emergency Access & Firefighter (120 tests)

### E.1 Firefighter ID Management (UAT-E001..E030) — @P0

| ID | Test | Steps |
|----|------|-------|
| E001 | FF dashboard loads | Active sessions, recent sessions |
| E002 | FF statistics | Request counts, session counts |
| E003 | FF ID list | Configured FF IDs shown |
| E004 | Request emergency access — form | FF ID, reason, duration fields |
| E005 | Request emergency access — submit | Request created, status "Pending" |
| E006 | Request — reason code selection | Reason codes dropdown |
| E007 | Request — custom reason text | Free text reason |
| E008 | Request — duration selection | Duration options |
| E009 | Request — priority selection | Low/Medium/High/Critical |
| E010 | FF Owner — see pending requests | Approval inbox |
| E011 | FF Owner — request details | Full request info |
| E012 | FF Owner — approve request | Status → Approved |
| E013 | FF Owner — reject request | Status → Rejected, reason |
| E014 | FF Controller — monitoring dashboard | Active session overview |
| E015 | FF Controller — session details | Session info, activity log |
| E016 | Approved request — start session | Check-in successful |
| E017 | Active session — timer running | Duration countdown |
| E018 | Active session — activity logging | Actions captured |
| E019 | Active session — end session | Check-out, duration recorded |
| E020 | Session auto-expire | Timeout → session closed |
| E021 | Session extend request | Extension requested |
| E022 | Session extend — approved | Duration extended |
| E023 | Session log — view all actions | Complete activity trail |
| E024 | Session log — timestamps | All actions timestamped |
| E025 | FF session audit trail | Audit log entries |
| E026 | FF request list — filter by status | Status filter |
| E027 | FF session list — filter by date | Date range filter |
| E028 | FF report generation | FF activity report |
| E029 | Multiple concurrent FF sessions | Two users with active sessions |
| E030 | FF request — cancel | Request cancelled before approval |

### E.2 Firefighter Monitoring (UAT-E031..E060) — @P0

| ID | Test | Steps |
|----|------|-------|
| E031 | Live session monitor — loads | Active sessions listed |
| E032 | Live monitor — real-time activities | New actions appear |
| E033 | Controller review — start | Review initiated |
| E034 | Controller review — complete | Review submitted |
| E035 | Controller review — flag issue | Issue flagged for investigation |
| E036 | Session activity export | Export to CSV |
| E037 | Session risk assessment | Risk score for session |
| E038 | Post-session review requirement | Review required after session |
| E039 | Session screenshot capture | Screenshot evidence |
| E040 | Multiple controller notification | All controllers notified |
| E041 | FF request — duplicate prevention | Same FF ID request blocked |
| E042 | FF request — blackout period | Request during blackout → blocked |
| E043 | Session — revoke mid-session | Owner revokes → session terminated |
| E044 | Session — force close | Controller force-closes |
| E045 | FF metrics — total sessions | Count matches |
| E046 | FF metrics — avg duration | Average calculated |
| E047 | FF metrics — by FF ID | Per-ID breakdown |
| E048 | FF metrics — by requester | Per-requester breakdown |
| E049 | FF metrics — trend over time | Trend chart |
| E050 | FF integration with CCM | CCM monitors FF activity |
| E051 | FF exception in CCM | FF exception flagged |
| E052 | FF reason code management [API] | CRUD on reason codes |
| E053 | FF configuration [API] | FF settings management |
| E054 | FF notification — request submitted | Notification to owner |
| E055 | FF notification — approved | Notification to requester |
| E056 | FF notification — rejected | Notification to requester |
| E057 | FF notification — session started | Notification to controller |
| E058 | FF notification — session ended | Notification to owner + controller |
| E059 | FF notification — extension request | Notification to owner |
| E060 | FF notification — auto-expired | Notification to all parties |

### E.3 Provisioning & Mass Admin (UAT-E061..E090) — @P1

| ID | Test | Steps |
|----|------|-------|
| E061 | Provisioning dashboard | Connector status |
| E062 | Provisioning — list connectors | All connectors shown |
| E063 | Provisioning — connector detail | Config and status |
| E064 | Provisioning — test connection | Connection test runs |
| E065 | Provisioning — create connector | New connector saved |
| E066 | Provisioning — user query | Query users from target |
| E067 | Provisioning — role query | Query roles from target |
| E068 | Provisioning — assign role | Role assigned via connector |
| E069 | Provisioning — remove role | Role removed via connector |
| E070 | Provisioning — task queue | Pending tasks shown |
| E071 | Provisioning — task status | Task progress tracked |
| E072 | Provisioning — retry failed task | Failed task retried |
| E073 | Mass admin — dashboard | Bulk operations overview |
| E074 | Mass admin — create bulk job | Job configured |
| E075 | Mass admin — user role assignment | Bulk role assignment |
| E076 | Mass admin — user role removal | Bulk role removal |
| E077 | Mass admin — job progress | Progress bar |
| E078 | Mass admin — job results | Success/failure counts |
| E079 | Mass admin — cancel job | Running job cancelled |
| E080 | Mass admin — job history | Historical jobs listed |
| E081 | Mass admin — CSV import | Users from CSV |
| E082 | Mass admin — error handling | Failed items shown |
| E083 | Mass admin — retry failed items | Retry individual failures |
| E084 | Repo sync — view status | Sync status displayed |
| E085 | Repo sync — trigger manual sync | Sync initiated |
| E086 | Repo sync — sync history | Past syncs listed |
| E087 | Repo sync — configure schedule | Schedule set |
| E088 | Integration list | All integrations shown |
| E089 | Integration — SAP RFC connection | RFC connector configured |
| E090 | Integration — test SAP connection | Connection test |

### E.4 Additional Operations (UAT-E091..E120) — @P2

| ID | Test | Steps |
|----|------|-------|
| E091 | Workflow builder — palette | Node types available |
| E092 | Workflow builder — create workflow | Workflow saved |
| E093 | Workflow builder — validate | Validation runs |
| E094 | Workflow builder — preview | Workflow preview |
| E095 | Workflow builder — export policy | Policy generated |
| E096 | Notification center — list | All notifications |
| E097 | Notification center — mark read | Notification read |
| E098 | Notification center — preferences | User prefs saved |
| E099 | Notification delivery — list | Delivery queue |
| E100 | Notification delivery — status | Delivery status tracking |
| E101 | SMTP settings — configure | SMTP saved |
| E102 | SMTP settings — test send | Test email sent |
| E103 | i18n — language list [API] | Languages returned |
| E104 | i18n — translations [API] | Translations loaded |
| E105 | Mobile API — dashboard [API] | Mobile dashboard data |
| E106 | Mobile API — approvals [API] | Mobile approval list |
| E107 | Mobile API — submit approval [API] | Approval via mobile |
| E108 | Mobile API — notifications [API] | Mobile notifications |
| E109 | Setup wizard — system check | Health check |
| E110 | Setup wizard — configuration | Initial config |
| E111 | Setup wizard — data import | Import initial data |
| E112 | GRC intelligence — overview [API] | GRC metrics |
| E113 | GRC intelligence — analysis [API] | GRC analysis |
| E114 | GovernEx advanced — features [API] | Advanced features |
| E115 | GovernEx advanced — analytics [API] | Analytics data |
| E116 | Cross-system — overview [API] | Cross-system view |
| E117 | Cross-system — comparison [API] | System comparison |
| E118 | Audit log — view | All audit entries |
| E119 | Audit log — filter by action | Action filter |
| E120 | Audit log — filter by user | User filter |

---

## Group F — Identity & Lifecycle (200 tests)

### F.1 JML Policies (UAT-F001..F030) — @P0

| ID | Test | Steps |
|----|------|-------|
| F001 | JML policies list | All policies displayed |
| F002 | JML statistics | Total, active, by type counts |
| F003 | Create policy — joiner | Event type = Joiner |
| F004 | Create policy — mover | Event type = Mover |
| F005 | Create policy — leaver | Event type = Leaver |
| F006 | Policy — set org unit | Org unit assigned |
| F007 | Policy — set birthright roles | Roles configured |
| F008 | Policy — toggle active | Active/inactive toggle |
| F009 | Policy detail view | Full policy info |
| F010 | Edit policy | Updated successfully |
| F011 | Delete policy | Policy removed |
| F012 | Policy search | Search by name |
| F013 | Policy filter by event type | Joiner/Mover/Leaver filter |
| F014 | Policy sort | Sort by name/date |
| F015 | Policy validation — name required | Validation error |
| F016 | Policy validation — event type required | Validation error |
| F017 | Policy validation — org unit required | Validation error |
| F018 | HR Event Monitor loads | Event list |
| F019 | Joiner event processing | Birthright roles assigned |
| F020 | Mover event processing | Old roles removed, new granted |
| F021 | Leaver event processing | All access revoked |
| F022 | JML audit trail | Events logged |
| F023 | JML → Certification integration | Leaver triggers review |
| F024 | JML → Access Request integration | Joiner creates request |
| F025 | JML with multiple policies | Priority resolution |
| F026 | JML event — manual trigger | Manual event creation |
| F027 | JML event — API trigger [API] | Event via API |
| F028 | JML event status tracking | Event lifecycle |
| F029 | JML report | Event summary report |
| F030 | JML dashboard stats | Active events, pending actions |

### F.2 Identity Correlation (UAT-F031..F060) — @P1

| ID | Test | Steps |
|----|------|-------|
| F031 | Identity correlation page loads | Overview stats |
| F032 | Total identities count | Count matches data |
| F033 | Correlated identities | Successfully matched |
| F034 | Orphan accounts | No HR match |
| F035 | Conflicting identities | Attribute mismatches |
| F036 | Run correlation | Engine executes |
| F037 | Correlation results | Matched pairs shown |
| F038 | Orphan list | Orphan accounts listed |
| F039 | Manual correlation | Link orphan to HR record |
| F040 | Conflict resolution | Resolve attribute conflict |
| F041 | Multi-system identity view | All systems for one identity |
| F042 | Identity cluster management | Clusters shown |
| F043 | SAP migration mapping | ECC → S/4 mapping |
| F044 | Migration analyzer | Impact analysis |
| F045 | Migration copilot | AI-guided migration |
| F046 | Fiori analyzer — app list | Fiori tiles shown |
| F047 | Fiori analyzer — tile-role mapping | Mapping view |
| F048 | Access timeline | User access history |
| F049 | Timeline — filter by date | Date range filter |
| F050 | Timeline — filter by event type | Event type filter |
| F051 | Upgrade analyzer | Upgrade impact |
| F052 | Troubleshooter — access issue | Diagnosis runs |
| F053 | Troubleshooter — remediation | Fix suggestion |
| F054 | Role intelligence — analytics | Usage patterns |
| F055 | Role drift — detection | Drift identified |
| F056 | Role drift — comparison | Before/after diff |
| F057 | Audit evidence center | Evidence catalog |
| F058 | Evidence — link to control | Evidence-control mapping |
| F059 | Evidence agent — generate [API] | AI evidence generation |
| F060 | Evidence agent — review [API] | Evidence review |

### F.3 TPRM — Third-Party Risk (UAT-F061..F090) — @P1

| ID | Test | Steps |
|----|------|-------|
| F061 | Vendor registry loads | Vendor list |
| F062 | Create vendor | New vendor saved |
| F063 | Vendor — name and category | Fields populated |
| F064 | Vendor — risk tier | Tier assigned |
| F065 | Vendor — contact info | Contact details saved |
| F066 | Vendor detail view | Full vendor info |
| F067 | Edit vendor | Updated successfully |
| F068 | Vendor search | Search by name |
| F069 | Vendor filter by status | Active/inactive filter |
| F070 | Vendor filter by risk tier | High/Medium/Low filter |
| F071 | Vendor assessment — create | Assessment initiated |
| F072 | Vendor assessment — questionnaire | Questionnaire form |
| F073 | Vendor assessment — submit | Assessment submitted |
| F074 | Vendor assessment — risk score | Score calculated |
| F075 | Vendor assessment — status lifecycle | Draft → Submitted → Reviewed → Approved |
| F076 | Vendor assessment — history | Past assessments listed |
| F077 | Vendor issue — create | Issue logged |
| F078 | Vendor issue — severity | Low/Medium/High/Critical |
| F079 | Vendor issue — status tracking | Open → In Progress → Resolved |
| F080 | Vendor issue — remediation plan | Plan attached |
| F081 | Vendor contract management | Contracts CRUD |
| F082 | Vendor contract — dates | Start/end dates |
| F083 | Vendor contract — status | Active/Expired/Terminated |
| F084 | Vendor risk overview | Risk summary across vendors |
| F085 | Vendor risk heatmap | Visual risk distribution |
| F086 | TPRM dashboard | Module overview |
| F087 | TPRM — export vendor list | CSV export |
| F088 | TPRM — assessment scoring page | Scoring interface |
| F089 | TPRM — issue tracking page | Issues list view |
| F090 | TPRM — compliance integration | Vendor compliance tracking |

### F.4 Fraud Detection (UAT-F091..F120) — @P0

| ID | Test | Steps |
|----|------|-------|
| F091 | Fraud rules list | All rules displayed |
| F092 | Create fraud rule | New rule saved |
| F093 | Fraud rule — type (transaction) | Rule type = Transaction |
| F094 | Fraud rule — conditions | Conditions configured |
| F095 | Fraud rule — severity | Severity set |
| F096 | Edit fraud rule | Rule updated |
| F097 | Delete fraud rule | Rule removed |
| F098 | Fraud rule — enable/disable | Toggle works |
| F099 | Fraud alert inbox | Alerts displayed |
| F100 | Fraud alert — view detail | Alert info shown |
| F101 | Fraud alert — triggered rule | Rule that triggered |
| F102 | Fraud alert — affected transaction | Transaction details |
| F103 | Fraud alert — dismiss | Alert dismissed |
| F104 | Fraud alert — escalate | Alert escalated |
| F105 | Fraud alert — open case | Case created from alert |
| F106 | Fraud case list | All cases shown |
| F107 | Fraud case — create standalone | Case without alert |
| F108 | Fraud case — detail view | Full case info |
| F109 | Fraud case — status lifecycle | Open → Investigating → Closed/Escalated |
| F110 | Fraud case — assign investigator | Investigator assigned |
| F111 | Fraud case — add notes | Investigation notes |
| F112 | Fraud case — link alert | Alert linked to case |
| F113 | Fraud case — loss amount | Financial impact recorded |
| F114 | Fraud case — severity update | Severity changed |
| F115 | Fraud case — close with outcome | Outcome recorded |
| F116 | Fraud case — escalate | Case escalated |
| F117 | Fraud dashboard | Module overview |
| F118 | Fraud case search | Search by reference |
| F119 | Fraud case filter by status | Status filter |
| F120 | Fraud case export | Export to CSV |

### F.5 BCM — Business Continuity (UAT-F121..F150) — @P1

| ID | Test | Steps |
|----|------|-------|
| F121 | BIA summary loads | BIA records shown |
| F122 | Create BIA record | New BIA saved |
| F123 | BIA — process name | Process identified |
| F124 | BIA — RTO/RPO | Recovery times set |
| F125 | BIA — impact level | Criticality assigned |
| F126 | BIA — detail view | Full BIA info |
| F127 | Edit BIA | Updated successfully |
| F128 | BIA search | Search by process |
| F129 | BIA filter by criticality | Filter works |
| F130 | BCM plans list | All plans shown |
| F131 | Create BCM plan | New plan saved |
| F132 | BCM plan — type | DR/BCP/Crisis plan |
| F133 | BCM plan — status lifecycle | Draft → Active → Under Review |
| F134 | BCM plan — detail view | Full plan info |
| F135 | Edit BCM plan | Updated successfully |
| F136 | BCM exercise — create | Exercise defined |
| F137 | BCM exercise — link to plan | Plan association |
| F138 | BCM exercise — execute | Exercise runs |
| F139 | BCM exercise — record outcome | Pass/Fail/Partial |
| F140 | BCM exercise — lessons learned | Notes recorded |
| F141 | Incident activation — create | Activation triggered |
| F142 | Incident activation — severity | Severity set |
| F143 | Incident activation — status tracking | Activated → Recovered → Closed |
| F144 | Incident activation — reason | Activation reason |
| F145 | Incident activation — linked plan | Plan executed |
| F146 | BCM dashboard | Module overview |
| F147 | BCM plan search | Search by name |
| F148 | BCM plan filter by type | Type filter |
| F149 | BCM exercise history | Past exercises |
| F150 | BCM export | Export to CSV |

### F.6 Whistleblower (UAT-F151..F180) — @P0

| ID | Test | Steps |
|----|------|-------|
| F151 | Public submission page — no auth required | /whistleblower/intake loads without login |
| F152 | Submit report — category fraud | Category = Fraud |
| F153 | Submit report — category corruption | Category = Corruption |
| F154 | Submit report — category safety | Category = Safety |
| F155 | Submit report — category harassment | Category = Harassment |
| F156 | Submit report — category other | Category = Other |
| F157 | Submit report — description | Description entered |
| F158 | Submit report — priority high | Priority = High |
| F159 | Submit report — priority medium | Priority = Medium |
| F160 | Submit report — priority low | Priority = Low |
| F161 | Submit report — success | Reference code displayed |
| F162 | Submit report — validation (no description) | Validation error |
| F163 | Submit report — validation (no category) | Validation error |
| F164 | Track case — page loads without auth | /whistleblower/track accessible |
| F165 | Track case — enter reference code | Case status shown |
| F166 | Track case — invalid reference | "Not found" message |
| F167 | Track case — status displayed | Status: Open/Investigating/etc |
| F168 | Track case — messages visible | Investigator messages shown |
| F169 | Anonymous reply — submit | Reply saved |
| F170 | Anonymous reply — case closed | Reply blocked if closed |
| F171 | Investigator inbox | All cases listed |
| F172 | Investigator — open case | Case detail view |
| F173 | Investigator — add message | Message saved |
| F174 | Investigator — change status to Investigating | Status updated |
| F175 | Investigator — change status to Escalated | Status updated |
| F176 | Investigator — close case | Status = Closed |
| F177 | Investigator — view messages thread | Full conversation |
| F178 | Investigator — case search | Search by reference |
| F179 | Investigator — case filter by status | Status filter |
| F180 | Whistleblower — audit trail | All actions logged |

### F.7 Surveys (UAT-F181..F200) — @P1

| ID | Test | Steps |
|----|------|-------|
| F181 | Survey designer loads | Survey list |
| F182 | Create survey | New survey saved |
| F183 | Survey — title and description | Fields populated |
| F184 | Survey — add question (multiple choice) | MC question added |
| F185 | Survey — add question (text) | Text question added |
| F186 | Survey — add question (rating) | Rating question added |
| F187 | Survey — edit question | Question updated |
| F188 | Survey — delete question | Question removed |
| F189 | Survey — reorder questions | Drag/drop reorder |
| F190 | Survey — save draft | Draft saved |
| F191 | Survey — publish | Survey published |
| F192 | Survey distribution | Recipients configured |
| F193 | Survey — distribute to users | Distribution sent |
| F194 | Survey — respondent view | Survey form shown |
| F195 | Survey — submit response | Response saved |
| F196 | Survey — partial save | Draft response saved |
| F197 | Survey analytics | Response statistics |
| F198 | Survey — export results | CSV export |
| F199 | Survey — close | Survey closed |
| F200 | Survey — delete | Survey removed |

---

## Group G — Platform, Config & Reporting (170 tests)

### G.1 Template Library (UAT-G001..G030) — @P1

| ID | Test | Steps |
|----|------|-------|
| G001 | Content library loads | Template packs shown |
| G002 | Template count ≥ 42 | Seeded content present |
| G003 | Template pack — view detail | Pack info, versioned items |
| G004 | Template pack — view items | Items listed |
| G005 | Template categories | SoD rules, mitigations, workflows, controls |
| G006 | Activation wizard — start | Wizard opens |
| G007 | Activation wizard — preview | Items previewed |
| G008 | Activation wizard — confirm | Activation runs |
| G009 | Active content — list | Activated items shown |
| G010 | Active content — edit | Copy-on-write triggered |
| G011 | Active content — revert | Revert to original |
| G012 | Update review — pending | Updates listed |
| G013 | Update review — accept | Update accepted |
| G014 | Update review — reject | Update rejected |
| G015 | Update review — defer | Update deferred |
| G016 | Pack builder — create custom pack | New pack |
| G017 | Pack builder — add items | Items added |
| G018 | Pack builder — save | Pack saved |
| G019 | Library search | Search templates |
| G020 | Library filter by category | Category filter |
| G021 | Library filter by status | Status filter |
| G022 | Platform admin — view all packs | Cross-tenant view |
| G023 | Platform admin — manage packs | Admin CRUD |
| G024 | Template versioning | Version history |
| G025 | Template version comparison | Diff between versions |
| G026 | Bulk activation | Multiple items at once |
| G027 | Deactivate item | Item deactivated |
| G028 | Re-activate item | Item reactivated |
| G029 | Library analytics [API] | Adoption metrics |
| G030 | Library export | Export catalog |

### G.2 Reporting (UAT-G031..G060) — @P1

| ID | Test | Steps |
|----|------|-------|
| G031 | Reports dashboard | Report categories |
| G032 | Report list | All reports shown |
| G033 | Report — SoD Violations Summary | Report runs |
| G034 | Report — User Access Review | Report runs |
| G035 | Report — Role Usage Analysis | Report runs |
| G036 | Report — Certification Status | Report runs |
| G037 | Report — Firefighter Activity | Report runs |
| G038 | Report — Risk Heatmap | Report runs |
| G039 | Report — KRI Dashboard | Report runs |
| G040 | Report — Audit Findings | Report runs |
| G041 | Report — parameter configuration | Date range, filters |
| G042 | Report — generate | Execution succeeds |
| G043 | Report — view results | Data displayed |
| G044 | Report — export CSV | CSV file downloads |
| G045 | Report — export PDF | PDF file downloads |
| G046 | Report — drill-down | Click data → detail view |
| G047 | Report — schedule | Scheduled report |
| G048 | Report — favorites | Report bookmarked |
| G049 | Report — custom report | Custom report builder |
| G050 | Report — share | Share with colleague |
| G051 | Report — RBAC on reports | User sees only allowed reports |
| G052 | Dashboard summary widget | Report summary on dashboard |
| G053 | Reporting — search | Search reports |
| G054 | Reporting — filter by category | Category filter |
| G055 | Reporting — pagination | Multi-page results |
| G056 | Reporting — large dataset | 10,000+ row report |
| G057 | Report viewer — print | Print-friendly view |
| G058 | Report viewer — chart | Data visualization |
| G059 | Report viewer — table | Tabular data |
| G060 | Report history | Past report runs |

### G.3 System Configuration (UAT-G061..G090) — @P1

| ID | Test | Steps |
|----|------|-------|
| G061 | Config page loads | Settings displayed |
| G062 | View session timeout | Current value shown |
| G063 | Change session timeout | Saved successfully |
| G064 | View password policy | Current policy shown |
| G065 | Change password min length | Saved |
| G066 | View rate limits | Current limits shown |
| G067 | Change rate limit | Saved |
| G068 | CORS origins — view | Current origins |
| G069 | CORS origins — update | Origins updated |
| G070 | Tenant settings — view | Tenant config |
| G071 | Tenant settings — update | Config saved |
| G072 | Platform settings — view | Platform config |
| G073 | Platform settings — update | Config saved |
| G074 | Config effect — session timeout | New timeout enforced |
| G075 | Config effect — password policy | New policy enforced |
| G076 | Config effect — rate limit | New limit enforced |
| G077 | System management — systems list | SAP systems shown |
| G078 | System management — add system | New system configured |
| G079 | System management — test connection | Connection test |
| G080 | System management — edit | System updated |
| G081 | Policy management — list | Policies shown |
| G082 | Policy management — create | New policy saved |
| G083 | Policy management — edit | Policy updated |
| G084 | Policy management — versioning | Policy version tracked |
| G085 | Delegation management — list | Delegations shown |
| G086 | Delegation management — create | Delegation saved |
| G087 | Delegation management — date range | Date range configured |
| G088 | Tenant admin — cannot override platform settings | Read-only enforcement |
| G089 | Audit trail for config changes | Config changes logged |
| G090 | Config backup/restore [API] | Backup works |

### G.4 User Management (UAT-G091..G120) — @P0

| ID | Test | Steps |
|----|------|-------|
| G091 | User list loads | Users displayed |
| G092 | User stats | Total, active, inactive counts |
| G093 | Create user — form | All fields present |
| G094 | Create user — submit | User created |
| G095 | Create user — validation (missing username) | Error shown |
| G096 | Create user — validation (missing email) | Error shown |
| G097 | Create user — validation (duplicate username) | Error shown |
| G098 | User search by name | Filter works |
| G099 | User search by email | Filter works |
| G100 | User search by department | Filter works |
| G101 | User filter by status | Active/inactive |
| G102 | User filter by department | Department dropdown |
| G103 | User detail view | Full user info |
| G104 | User — roles tab | Assigned roles shown |
| G105 | User — entitlements tab | Auth objects shown |
| G106 | User — risk profile | Risk visualization |
| G107 | User — activity log | Recent actions |
| G108 | Edit user — change name | Updated |
| G109 | Edit user — change email | Updated |
| G110 | Edit user — change department | Updated |
| G111 | Edit user — assign role | Role added |
| G112 | Edit user — remove role | Role removed |
| G113 | Deactivate user | Status → inactive |
| G114 | Reactivate user | Status → active |
| G115 | Delete user | User removed |
| G116 | Inactive users page | Filtered list |
| G117 | User list — sort by name | Sorting works |
| G118 | User list — sort by department | Sorting works |
| G119 | User list — pagination | Multi-page |
| G120 | User export | CSV export |

### G.5 AI & Intelligence (UAT-G121..G150) — @P2

| ID | Test | Steps |
|----|------|-------|
| G121 | AI assistant page loads | Chat interface |
| G122 | AI query — text question | Response returned |
| G123 | AI — role mining request | Mining results |
| G124 | AI — remediation suggestion | Remediation plan |
| G125 | AI — risk analysis | Risk narrative |
| G126 | AI — explain violation | Violation explanation |
| G127 | AI — investigate issue | Investigation steps |
| G128 | AI — preview fix | Fix preview |
| G129 | AI — quick fix | Auto-remediation |
| G130 | AI — personalized dashboard | Tailored view |
| G131 | AI — conversation history | Past queries |
| G132 | AI — clear conversation | History cleared |
| G133 | Global search — page loads | Search bar |
| G134 | Global search — query | Results returned |
| G135 | Global search — filter results | Category filter |
| G136 | GRC intelligence — health score | Score displayed |
| G137 | GRC intelligence — attention items | Items listed |
| G138 | GRC intelligence — module status | Per-module health |
| G139 | ML dashboard — model status | Model info |
| G140 | ML dashboard — predictions | Prediction data |
| G141 | Password change | New password set |
| G142 | Password change — validation | Policy enforced |
| G143 | Password reset in systems | System password reset |
| G144 | Notification preferences | User prefs |
| G145 | Notification list — view | All notifications |
| G146 | Notification — mark read | Status updated |
| G147 | Notification — mark all read | Bulk update |
| G148 | Notification — filter | Filter by type |
| G149 | Notification — real-time delivery | New notification appears |
| G150 | Notification — click-through | Navigate to source |

### G.6 Cross-Module Workflows (UAT-G151..G170) — @P0

| ID | Test | Steps |
|----|------|-------|
| G151 | **E2E: Joiner → Request → Approve → Certify** | New hire gets access, approved, later certified |
| G152 | **E2E: SoD Violation → Mitigation → Accept** | Violation found → mitigation applied → risk accepted |
| G153 | **E2E: FF Request → Approve → Session → Review** | Emergency access full cycle |
| G154 | **E2E: Risk Identified → KRI → Incident → Close** | Risk lifecycle with monitoring |
| G155 | **E2E: Vendor Onboard → Assess → Issue → Resolve** | TPRM full cycle |
| G156 | **E2E: Whistleblower → Investigate → Close** | Whistleblower full cycle |
| G157 | **E2E: Fraud Alert → Case → Investigate → Close** | Fraud full cycle |
| G158 | **E2E: Audit Plan → Engage → Find → Action** | Audit management full cycle |
| G159 | **E2E: Control Create → Test → Deficiency → Remediate** | Process control full cycle |
| G160 | **E2E: BCM Plan → Exercise → Activate → Recover** | BCM full cycle |
| G161 | **E2E: Survey Create → Distribute → Respond → Analyze** | Survey full cycle |
| G162 | **E2E: Template Activate → Customize → Update Review** | Library full cycle |
| G163 | **E2E: Role Create → Pack → Risk Check → Deploy** | Role engineering full cycle |
| G164 | **E2E: Leaver → Revoke All → Certify Removal** | Leaver lifecycle |
| G165 | **E2E: Config Change → Effect Verified → Audit Log** | Config change lifecycle |
| G166 | **E2E: Bulk Request → Bulk Approve → Provision** | Mass access lifecycle |
| G167 | **E2E: SoD Rule Create → Analysis → Violation → Remediate** | SoD lifecycle |
| G168 | **E2E: Risk Assessment → Response → KRI Monitor** | Risk management lifecycle |
| G169 | **E2E: Incident Report → Investigate → Link Risk → Close** | Incident lifecycle |
| G170 | **E2E: Multi-Module Dashboard Verification** | All module data reflected on dashboards |

---

## Summary

| Group | Description | Tests | @P0 | @P1 | @P2 |
|-------|-------------|-------|-----|-----|-----|
| **A** | Auth, Navigation, RBAC | 80 | 80 | 0 | 0 |
| **B** | Access Request Lifecycle | 130 | 90 | 40 | 0 |
| **C** | Certification & Compliance | 150 | 40 | 110 | 0 |
| **D** | Risk Management | 150 | 90 | 30 | 30 |
| **E** | Emergency Access & Operations | 120 | 60 | 30 | 30 |
| **F** | Identity & Extended Modules | 200 | 90 | 110 | 0 |
| **G** | Platform, Config & Reporting | 170 | 50 | 60 | 60 |
| | **TOTAL** | **1000** | **500** | **380** | **120** |

### Scaling to 2000

The 1000 tests above cover every feature end-to-end. To reach 2000, add:

| Multiplier Layer | Additional Tests | Method |
|------------------|-----------------|--------|
| **RBAC × Feature** | +400 | Each P0 test × 3 unauthorized personas (verify denial) |
| **Negative / Validation** | +250 | Each form × 5 validation scenarios (empty, too long, XSS, SQL injection, invalid enum) |
| **State Transitions** | +150 | Each enum × invalid transitions (e.g., Closed → Open) |
| **Pagination & Performance** | +50 | Each list page with 100/500/1000 items |
| **Dark Mode Visual** | +100 | Each page renders correctly in dark mode |
| **Concurrent / Race** | +50 | Parallel edits, double-submit, stale data |
| **TOTAL** | **+1000** | |

**Grand Total: 2000 tests**

---

## Execution Plan

| Phase | Tests | Duration | Stack |
|-------|-------|----------|-------|
| 1 — Smoke (P0 happy path) | 200 | ~30 min | Fresh stack |
| 2 — Core P0 (all P0) | 500 | ~2 hours | Same stack |
| 3 — Full P0 + P1 | 880 | ~4 hours | Fresh stack |
| 4 — Complete (all 2000) | 2000 | ~8 hours | Fresh stack |

### Infrastructure Requirements
- Playwright + Chromium (headless)
- Docker Compose QA stack (API + PostgreSQL + Frontend)
- Seed data: 22 personas + test fixtures
- Screenshot evidence: `qa/uat-evidence/UAT-{group}{seq}/step-{nn}.png`
- Results: `qa/UAT_RESULTS.md`
- Defects: `qa/DEFECT_LOG.md`
