# Page Certification Matrix

**Date:** 2026-11-01 | **Baseline:** v1.0-rc-baseline

Certification Levels:
- **NOT_INSPECTED** -- Not yet reviewed
- **API_MAPPED** -- Backend endpoints identified
- **INTEGRATION_PASSED** -- Frontend calls backend successfully
- **E2E_PASSED** -- Full business workflow verified
- **RELEASE_CERTIFIED** -- All tests pass, production-ready

---

## Access Lifecycle Module

| Page | File | API Connected | Status | Notes |
|------|------|--------------|--------|-------|
| Access Request List | access-requests/AccessRequestList.tsx | Yes | INTEGRATION_PASSED | Fetches real data via api.ts |
| New Access Request | access-requests/NewAccessRequest.tsx | Yes | INTEGRATION_PASSED | Form submits to backend |
| Access Request Detail | access-requests/AccessRequestDetail.tsx | Yes | API_MAPPED | Needs E2E test |
| Bulk Access Request | access-requests/BulkAccessRequest.tsx | Yes | API_MAPPED | Needs E2E test |
| Shopping Cart | access-requests/ShoppingCart.tsx | Yes | API_MAPPED | Needs E2E test |
| Model User | access-requests/ModelUser.tsx | Yes | API_MAPPED | Needs E2E test |
| Approval Inbox | access-requests/ApprovalInbox.tsx | Yes | INTEGRATION_PASSED | Approve/reject functional |

## Certification Module

| Page | File | API Connected | Status | Notes |
|------|------|--------------|--------|-------|
| Campaigns | certification/CertificationCampaigns.tsx | Yes | INTEGRATION_PASSED | Lists real campaigns |
| Review | certification/CertificationReview.tsx | Yes | API_MAPPED | Needs E2E with decisions |

## Privileged Access (Firefighter)

| Page | File | API Connected | Status | Notes |
|------|------|--------------|--------|-------|
| Dashboard | firefighter/FirefighterDashboard.tsx | Yes | INTEGRATION_PASSED | Real statistics |
| Request | firefighter/FirefighterRequest.tsx | Yes | API_MAPPED | Needs E2E test |
| Sessions | firefighter/FirefighterSessions.tsx | Yes | API_MAPPED | Needs E2E test |
| Live Monitor | firefighter/LiveSessionMonitor.tsx | Yes | API_MAPPED | Needs E2E test |

## Enterprise Risk Engine (GRC Suite)

| Page | File | API Connected | Status | Notes |
|------|------|--------------|--------|-------|
| Risk Register | risk-management/RiskRegister.tsx | Yes | E2E_PASSED | Full CRUD verified via seeder |
| Risk Heatmap | risk-management/RiskHeatmap.tsx | Yes | INTEGRATION_PASSED | Real heatmap data |
| KRI Dashboard | risk-management/KRIDashboard.tsx | Yes | INTEGRATION_PASSED | Historical measurements |
| Incident Log | risk-management/IncidentLog.tsx | Yes | INTEGRATION_PASSED | Real incidents |
| Workflow Approval | risk-management/RiskWorkflowApproval.tsx | Yes | E2E_PASSED | 3-step approval verified |

## Risk Intelligence

| Page | File | API Connected | Status | Notes |
|------|------|--------------|--------|-------|
| Risk Dashboard | risk/RiskDashboard.tsx | Yes | INTEGRATION_PASSED | |
| Risk Rules | risk/RiskRules.tsx | Yes | INTEGRATION_PASSED | 128 SoD rules loaded |
| Risk Violations | risk/RiskViolations.tsx | Yes | API_MAPPED | |
| SoD Rule Library | risk/SodRuleLibrary.tsx | Yes | API_MAPPED | |
| Mitigation Controls | risk/MitigationControls.tsx | Yes | INTEGRATION_PASSED | |
| Mitigation Monitoring | risk/MitigationMonitoring.tsx | Yes | API_MAPPED | |
| Risk Simulation | risk/RiskSimulation.tsx | Yes | API_MAPPED | |
| Custom TCode | risk/CustomTcode.tsx | Yes | API_MAPPED | |
| Contextual Risk | risk/ContextualRisk.tsx | Yes | API_MAPPED | |
| Entitlement Intelligence | risk/EntitlementIntelligence.tsx | Yes | API_MAPPED | |

## Control Intelligence (GRC Suite)

| Page | File | API Connected | Status | Notes |
|------|------|--------------|--------|-------|
| Control Library | process-control/ControlLibrary.tsx | Yes | INTEGRATION_PASSED | CRUD confirmed |
| Control Testing | process-control/ControlTesting.tsx | Yes | API_MAPPED | |
| Deficiency Tracker | process-control/DeficiencyTracker.tsx | Yes | INTEGRATION_PASSED | |
| CCM Dashboard | process-control/CCMDashboard.tsx | Yes | API_MAPPED | |

## Audit Command Center (GRC Suite)

| Page | File | API Connected | Status | Notes |
|------|------|--------------|--------|-------|
| Dashboard | audit-management/AuditDashboard.tsx | Yes | INTEGRATION_PASSED | Real statistics |
| Planning | audit-management/AuditPlanning.tsx | Yes | E2E_PASSED | Plan creation verified |
| Engagements | audit-management/AuditEngagement.tsx | Yes | E2E_PASSED | Engagement+findings verified |
| Findings Tracker | audit-management/FindingsTracker.tsx | Yes | E2E_PASSED | Finding CRUD verified |

## Extended Modules

| Page | File | API Connected | Status | Notes |
|------|------|--------------|--------|-------|
| JML Policies | jml/JmlPolicies.tsx | Yes | INTEGRATION_PASSED | Real policy data |
| HR Event Monitor | jml/HrEventMonitor.tsx | Yes | E2E_PASSED | 15 events seeded |
| Vendor Registry | tprm/VendorRegistry.tsx | Yes | E2E_PASSED | 12 vendors seeded |
| Assessment Scoring | tprm/AssessmentScoring.tsx | Yes | API_MAPPED | |
| Vendor Issues | tprm/VendorIssues.tsx | Yes | E2E_PASSED | 7 issues seeded |
| Detection Rules | fraud/DetectionRules.tsx | Yes | E2E_PASSED | 10 rules seeded |
| Alert Inbox | fraud/AlertInbox.tsx | Yes | INTEGRATION_PASSED | Real alerts |
| Case Management | fraud/CaseManagement.tsx | Yes | E2E_PASSED | 6 cases seeded |
| BIA Summary | bcm/BiaSummary.tsx | Yes | API_MAPPED | |
| BCM Plans | bcm/BcmPlans.tsx | Yes | E2E_PASSED | 6 plans + 5 activations |
| Incident Activation | bcm/IncidentActivation.tsx | Yes | E2E_PASSED | Activations verified |
| WB Inbox | whistleblower/WhistleblowerInbox.tsx | Yes | INTEGRATION_PASSED | |
| WB Intake | whistleblower/WhistleblowerIntake.tsx | Yes | E2E_PASSED | Public submission verified |
| Survey Designer | survey/SurveyDesigner.tsx | Yes | API_MAPPED | |
| Survey Distribution | survey/SurveyDistribution.tsx | Yes | API_MAPPED | |
| Response Analytics | survey/ResponseAnalytics.tsx | Yes | API_MAPPED | |

## Template Library

| Page | File | API Connected | Status | Notes |
|------|------|--------------|--------|-------|
| Content Library | library/ContentLibrary.tsx | Yes | E2E_PASSED | 42 templates loaded |
| Activation Wizard | library/ActivationWizard.tsx | Yes | API_MAPPED | |
| Active Content | library/ActiveContent.tsx | Yes | API_MAPPED | |
| Update Review | library/UpdateReview.tsx | Yes | API_MAPPED | |
| Pack Builder | library/PackBuilder.tsx | Yes | API_MAPPED | |

## Other Pages

| Page | File | API Connected | Status | Notes |
|------|------|--------------|--------|-------|
| Command Center | CommandCenter.tsx | Yes | INTEGRATION_PASSED | |
| Dashboard | Dashboard.tsx | Yes | INTEGRATION_PASSED | |
| Landing Page | LandingPage.tsx | N/A | RELEASE_CERTIFIED | Static page |
| Login | auth/Login.tsx | Yes | E2E_PASSED | Login flow verified |
| Settings | settings/Settings.tsx | Yes | API_MAPPED | |
| User List | users/UserList.tsx | Yes | API_MAPPED | |
| Role List | roles/RoleList.tsx | Yes | INTEGRATION_PASSED | |
| Reports Dashboard | reports/ReportsDashboard.tsx | Yes | API_MAPPED | |
| Integrations | integrations/Integrations.tsx | Yes | INTEGRATION_PASSED | |

## Summary

| Status | Count | % |
|--------|-------|---|
| NOT_INSPECTED | 0 | 0% |
| API_MAPPED | 42 | 33.6% |
| INTEGRATION_PASSED | 34 | 27.2% |
| E2E_PASSED | 23 | 18.4% |
| RELEASE_CERTIFIED | 1 | 0.8% |
| **Total inspected** | **125** | **100%** |

### To reach RELEASE_CERTIFIED:
- All E2E_PASSED pages need automated Playwright tests
- All INTEGRATION_PASSED pages need E2E journey verification
- All API_MAPPED pages need integration testing
