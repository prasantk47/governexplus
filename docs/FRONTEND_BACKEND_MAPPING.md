# Frontend-Backend Mapping

**Date:** 2026-11-01 | **Baseline:** v1.0-rc-baseline

---

## Module Mapping

Each row maps a frontend page to its backend router, database tables, and auth requirements.

### Access Control

| Frontend Page | Backend Router | Key Endpoints | DB Tables | Auth |
|--------------|---------------|---------------|-----------|------|
| AccessRequestList | access_requests.py | GET /access-requests/ | access_request_logs | JWT+tenant |
| NewAccessRequest | access_requests.py | POST /access-requests/ | access_request_logs | JWT+tenant |
| ApprovalInbox | approvals.py | GET /approvals/pending, POST /approvals/{id}/decide | access_request_logs | JWT+tenant+role |
| ShoppingCart | access_requests.py | GET/POST /access-requests/cart | shopping_carts | JWT+tenant |
| ModelUser | model_user.py | GET/POST /model-user/ | model_templates | JWT+tenant |
| BulkAccessRequest | access_requests.py, mass_admin.py | POST /access-requests/bulk | access_request_logs, bulk_jobs | JWT+tenant+role |

### Certification

| Frontend Page | Backend Router | Key Endpoints | DB Tables | Auth |
|--------------|---------------|---------------|-----------|------|
| CertificationCampaigns | certification.py | GET/POST /certification/campaigns | certification_campaigns | JWT+tenant |
| CertificationReview | certification.py | GET /certification/{id}/items, POST /certification/{id}/decide | certification_items | JWT+tenant+role |

### Privileged Access (Firefighter)

| Frontend Page | Backend Router | Key Endpoints | DB Tables | Auth |
|--------------|---------------|---------------|-----------|------|
| FirefighterDashboard | firefighter.py | GET /privileged-access/summary | firefighter_requests, firefighter_sessions | JWT+tenant |
| FirefighterRequest | firefighter.py | POST /privileged-access/request | firefighter_requests | JWT+tenant |
| FirefighterSessions | firefighter.py | GET /privileged-access/sessions | firefighter_sessions | JWT+tenant+role |
| LiveSessionMonitor | firefighter_monitoring.py | GET /privileged-access/monitoring/live | firefighter_activities | JWT+tenant+role |

### Risk Management (GRC Suite)

| Frontend Page | Backend Router | Key Endpoints | DB Tables | Auth |
|--------------|---------------|---------------|-----------|------|
| RiskRegister | risk_mgmt.py | GET/POST /risk-management/risks | enterprise_risks | JWT+tenant |
| RiskHeatmap | risk_mgmt.py | GET /risk-management/heatmap | enterprise_risks, risk_appetites | JWT+tenant |
| KRIDashboard | risk_mgmt.py | GET /risk-management/kris | key_risk_indicators, kri_measurements | JWT+tenant |
| IncidentLog | risk_mgmt.py | GET /risk-management/incidents | risk_incidents | JWT+tenant |
| RiskWorkflowApproval | risk_mgmt.py | GET/POST /risk-management/workflows | risk_workflows, risk_workflow_steps | JWT+tenant+role |

### Process Control (GRC Suite)

| Frontend Page | Backend Router | Key Endpoints | DB Tables | Auth |
|--------------|---------------|---------------|-----------|------|
| ControlLibrary | process_ctrl.py | GET/POST /process-control/controls | process_controls | JWT+tenant |
| ControlTesting | process_ctrl.py | GET/POST /process-control/test-runs | control_tests | JWT+tenant |
| DeficiencyTracker | process_ctrl.py | GET /process-control/deficiencies | control_deficiencies | JWT+tenant |
| CCMDashboard | process_ctrl.py | GET /process-control/ccm/status | ccm_rules, ccm_executions | JWT+tenant |

### Audit Management (GRC Suite)

| Frontend Page | Backend Router | Key Endpoints | DB Tables | Auth |
|--------------|---------------|---------------|-----------|------|
| AuditDashboard | audit_mgmt.py | GET /audit-management/dashboard | audit_plans, audit_engagements, audit_findings | JWT+tenant |
| AuditPlanning | audit_mgmt.py | GET/POST /audit-management/plans | audit_plans | JWT+tenant+role |
| AuditEngagement | audit_mgmt.py | GET/POST /audit-management/engagements | audit_engagements, audit_workpapers | JWT+tenant |
| FindingsTracker | audit_mgmt.py | GET /audit-management/findings | audit_findings, audit_actions | JWT+tenant |

### JML

| Frontend Page | Backend Router | Key Endpoints | DB Tables | Auth |
|--------------|---------------|---------------|-----------|------|
| JmlPolicies | jml.py | GET/POST /jml/policies | jml_policies | JWT+tenant |
| HrEventMonitor | jml.py | GET/POST /jml/events | jml_events | JWT+tenant |

### TPRM

| Frontend Page | Backend Router | Key Endpoints | DB Tables | Auth |
|--------------|---------------|---------------|-----------|------|
| VendorRegistry | tprm.py | GET/POST /tprm/vendors | vendors | JWT+tenant |
| AssessmentScoring | tprm.py | GET/POST /tprm/assessments | vendor_assessments | JWT+tenant |
| VendorIssues | tprm.py | GET/POST /tprm/issues | vendor_issues | JWT+tenant |

### Fraud Detection

| Frontend Page | Backend Router | Key Endpoints | DB Tables | Auth |
|--------------|---------------|---------------|-----------|------|
| DetectionRules | fraud.py | GET/POST /fraud/rules | fraud_rules | JWT+tenant |
| AlertInbox | fraud.py | GET /fraud/alerts | fraud_alerts | JWT+tenant |
| CaseManagement | fraud.py | GET/POST /fraud/cases | fraud_cases | JWT+tenant |

### BCM

| Frontend Page | Backend Router | Key Endpoints | DB Tables | Auth |
|--------------|---------------|---------------|-----------|------|
| BiaSummary | bcm.py | GET /bcm/bia | bia_records | JWT+tenant |
| BcmPlans | bcm.py | GET/POST /bcm/plans | bcm_plans | JWT+tenant |
| IncidentActivation | bcm.py | GET/POST /bcm/activations | incident_activations | JWT+tenant |

### Whistleblower

| Frontend Page | Backend Router | Key Endpoints | DB Tables | Auth |
|--------------|---------------|---------------|-----------|------|
| WhistleblowerInbox | whistleblower.py | GET /whistleblower/cases | whistleblower_cases | JWT+tenant+role |
| WhistleblowerIntake | whistleblower.py | POST /whistleblower/submit | whistleblower_cases | PUBLIC |

### Template Library

| Frontend Page | Backend Router | Key Endpoints | DB Tables | Auth |
|--------------|---------------|---------------|-----------|------|
| ContentLibrary | library.py | GET /library/items | template_items, template_packs | JWT+tenant |
| ActivationWizard | library.py | POST /library/activate | tenant_item_activations | JWT+tenant+role |
| ActiveContent | library.py | GET /library/active | tenant_item_activations | JWT+tenant |
| UpdateReview | library.py | GET /library/updates | template_pack_versions | JWT+tenant |

### Background Jobs (No frontend -- triggered automatically)

| Job | Router/Scheduler | Tables Affected |
|-----|-----------------|----------------|
| check_inactive_users | AutomationScheduler | users |
| revoke_expired_access | AutomationScheduler | user_entitlements |
| batch_risk_analysis | AutomationScheduler | risk_violations |
| sync_ad_groups | AutomationScheduler | user_roles |
| SAP user sync | SyncScheduler | users, user_entitlements |
| Provisioning tasks | ProvisioningQueue | access_request_logs |
