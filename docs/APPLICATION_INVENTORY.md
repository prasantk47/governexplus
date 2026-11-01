# GovernexPlus Application Inventory

**Baseline Tag:** `v1.0-rc-baseline` (commit `ebe9f11`)
**Date:** 2026-11-01
**Prepared for:** v1.0 Release Stabilization

---

## 1. Environment Versions

| Component | Production (212.47.75.51) | Dev (local) |
|-----------|--------------------------|-------------|
| Python | 3.12.3 | 3.12.10 |
| Node.js | 20.20.2 | 24.14.0 |
| PostgreSQL | 16.15 | N/A (SQLite local) |
| Redis | 7.0.15 | N/A |
| pip packages | 109 | 73 (requirements.txt) |
| OS | Ubuntu 24.04 | Windows 11 Pro |

---

## 2. Backend API Routes

**Total Router Files:** 81
**Total Routes (routers):** 1,163
**Routes in main.py:** 6
**Grand Total Routes:** 1,169

| Method | Count | % |
|--------|-------|---|
| GET | 604 | 51.6% |
| POST | 436 | 37.3% |
| PUT | 91 | 7.8% |
| DELETE | 32 | 2.7% |

### Top Routers by Route Count

| Router | Prefix | Routes |
|--------|--------|--------|
| audit_mgmt.py | /audit-management | 60 |
| risk_mgmt.py | /risk-management | 45 |
| role_engineering.py | /role-studio | 41 |
| process_ctrl.py | /process-control | 37 |
| ara.py | /risk-intelligence | 33 |
| tenants.py | /tenants | 32 |
| integrations.py | /integrations | 29 |
| firefighter.py | /privileged-access | 28 |
| security_controls.py | /security-controls | 27 |
| governex_plus.py | /governex | 26 |
| provisioning.py | /provisioning | 26 |
| sod_rules.py | /risk-rules | 25 |
| workflows.py | /workflows | 24 |
| ai_copilot.py | /ai-copilot | 23 |
| mitigation.py | /mitigation | 23 |

### Complete Router List

| File | Prefix | GET | POST | PUT | DEL | Total |
|------|--------|-----|------|-----|-----|-------|
| access_reports.py | /access-reports | 6 | 0 | 0 | 0 | 6 |
| access_requests.py | /access-requests | 9 | 7 | 1 | 0 | 17 |
| admin.py | /admin | 7 | 6 | 1 | 2 | 16 |
| ai.py | /ai | 11 | 8 | 1 | 0 | 20 |
| ai_copilot.py | /ai-copilot | 13 | 10 | 0 | 0 | 23 |
| ai_grc.py | (none) | 0 | 10 | 0 | 0 | 10 |
| approvals.py | /approvals | 2 | 3 | 0 | 0 | 5 |
| approver_management.py | /approver-management | 4 | 4 | 1 | 1 | 10 |
| ara.py | /risk-intelligence | 17 | 14 | 1 | 1 | 33 |
| arm.py | /access-lifecycle | 6 | 4 | 0 | 2 | 12 |
| audit.py | /audit | 7 | 1 | 0 | 0 | 8 |
| audit_evidence.py | /audit-evidence | 4 | 2 | 0 | 0 | 6 |
| audit_mgmt.py | /audit-management | 20 | 22 | 18 | 0 | 60 |
| auth.py | /auth | 2 | 8 | 0 | 0 | 10 |
| bcm.py | /bcm | 7 | 4 | 4 | 0 | 15 |
| certification.py | /certification | 8 | 11 | 0 | 0 | 19 |
| config.py | /config | 6 | 5 | 0 | 0 | 11 |
| control_objectives.py | /control-objectives | 3 | 3 | 1 | 0 | 7 |
| cross_system.py | /cross-system | 10 | 10 | 0 | 0 | 20 |
| custom_tcode.py | /custom-tcode | 5 | 1 | 0 | 0 | 6 |
| dashboard.py | /dashboard | 17 | 2 | 0 | 0 | 19 |
| digital_twin.py | /digital-twin | 3 | 1 | 0 | 0 | 4 |
| drift.py | /drift | 4 | 1 | 0 | 0 | 5 |
| evidence_agent.py | /evidence-agent | 1 | 2 | 0 | 0 | 3 |
| fiori.py | /fiori | 5 | 2 | 0 | 0 | 7 |
| firefighter.py | /privileged-access | 18 | 10 | 0 | 0 | 28 |
| firefighter_monitoring.py | /privileged-access/monitoring | 10 | 7 | 0 | 0 | 17 |
| frameworks.py | /frameworks | 3 | 2 | 2 | 1 | 8 |
| fraud.py | /fraud | 6 | 3 | 3 | 1 | 13 |
| governex_plus.py | /governex | 15 | 11 | 0 | 0 | 26 |
| grc_dashboard.py | /grc | 2 | 0 | 0 | 0 | 2 |
| grc_intelligence.py | /grc-intelligence | 4 | 4 | 0 | 0 | 8 |
| i18n.py | /i18n | 3 | 0 | 0 | 0 | 3 |
| identity_correlation.py | /identity-correlation | 6 | 2 | 0 | 0 | 8 |
| integrations.py | /integrations | 17 | 9 | 1 | 2 | 29 |
| jml.py | /jml | 6 | 4 | 1 | 1 | 12 |
| library.py | /library | 9 | 9 | 0 | 0 | 18 |
| mass_admin.py | /mass-admin | 3 | 11 | 0 | 0 | 14 |
| metrics.py | (none) | 1 | 0 | 0 | 0 | 1 |
| migration.py | /migration | 7 | 4 | 0 | 0 | 11 |
| migration_copilot.py | /migration-copilot | 2 | 1 | 0 | 0 | 3 |
| mitigation.py | /mitigation | 13 | 9 | 1 | 0 | 23 |
| mitigation_monitoring.py | /controls-monitoring | 8 | 2 | 1 | 0 | 11 |
| mobile.py | /mobile | 9 | 6 | 0 | 0 | 15 |
| model_user.py | /model-user | 3 | 4 | 1 | 0 | 8 |
| notifications.py | /notifications | 9 | 11 | 1 | 0 | 21 |
| notification_delivery.py | /notification-delivery | 4 | 3 | 1 | 0 | 8 |
| org_hierarchy.py | /org | 3 | 1 | 1 | 1 | 6 |
| org_rules.py | /org-rules | 5 | 3 | 2 | 1 | 11 |
| policy_mgmt.py | /policies | 4 | 2 | 6 | 0 | 12 |
| process_ctrl.py | /process-control | 15 | 12 | 9 | 1 | 37 |
| provisioning.py | /provisioning | 11 | 13 | 2 | 0 | 26 |
| question_library.py | /questionnaires | 5 | 4 | 3 | 0 | 12 |
| reporting.py | /reporting | 9 | 8 | 2 | 2 | 21 |
| reports.py | /reports | 7 | 1 | 0 | 0 | 8 |
| repo_sync.py | /repo-sync | 5 | 6 | 1 | 0 | 12 |
| retention.py | /retention | 2 | 2 | 1 | 0 | 5 |
| risk_analysis.py | /risk | 5 | 4 | 0 | 0 | 9 |
| risk_mgmt.py | /risk-management | 20 | 17 | 7 | 1 | 45 |
| risk_scenarios.py | /risk-scenarios | 5 | 5 | 4 | 0 | 14 |
| role_engineering.py | /role-studio | 17 | 21 | 1 | 2 | 41 |
| role_intelligence.py | /role-intelligence | 8 | 1 | 0 | 0 | 9 |
| role_methodology.py | /role-methodology | 2 | 1 | 2 | 0 | 5 |
| role_redesign.py | /role-redesign | 2 | 3 | 0 | 0 | 5 |
| security_controls.py | /security-controls | 14 | 11 | 1 | 1 | 27 |
| setup.py | /setup | 11 | 10 | 0 | 0 | 21 |
| smtp_config.py | /settings | 1 | 1 | 1 | 1 | 4 |
| sod_rules.py | /risk-rules | 16 | 6 | 2 | 1 | 25 |
| sso.py | /auth | 6 | 1 | 0 | 0 | 7 |
| subprocess_mgmt.py | /subprocesses | 3 | 3 | 1 | 1 | 8 |
| survey.py | /surveys | 7 | 3 | 1 | 1 | 12 |
| tenants.py | /tenants | 14 | 15 | 1 | 2 | 32 |
| timeline.py | /timeline | 4 | 1 | 0 | 0 | 5 |
| tprm.py | /tprm | 7 | 4 | 3 | 0 | 14 |
| transport.py | /transport | 7 | 1 | 1 | 0 | 9 |
| troubleshooter.py | /troubleshooter | 4 | 2 | 0 | 0 | 6 |
| upgrade.py | /upgrade | 5 | 2 | 0 | 0 | 7 |
| user_profiles.py | /user-profiles | 17 | 4 | 0 | 0 | 21 |
| users.py | /users | 9 | 3 | 1 | 2 | 15 |
| whistleblower.py | /whistleblower | 5 | 3 | 1 | 0 | 9 |
| workflows.py | /workflows | 14 | 9 | 1 | 0 | 24 |

---

## 3. Database Models and Tables

**Total Model Classes:** 141
**Total Unique Tables:** 141
**Model Files:** 18 (in db/models/)
**Alembic Migrations:** 14 (linear chain)

### Module Naming Convention

GovernexPlus uses SAP-independent module names:

| SAP GRC Name (avoid) | GovernexPlus Name | Sidebar Label | Route Prefix |
|---|---|---|---|
| Access Control (AC) | Access Governance | **Access Lifecycle** | /access-requests |
| — | Certification | **Certification** | /certification |
| — | Privileged Access | **Privileged Access** | /privileged-access |
| — | SoD/Risk Analysis | **Risk Intelligence** | /risk |
| — | Role Management | **Role Design Studio** | /roles |
| Risk Management (RM) | Enterprise Risk | **Enterprise Risk Engine** | /risk-management |
| Process Control (PC) | Process Control | **Control Intelligence** | /process-control |
| Audit Management (AM) | Audit Management | **Audit Command Center** | /audit-management |

### Models by Domain

| Domain | File | Models | Tables |
|--------|------|--------|--------|
| Core Auth | tenant.py, user.py, approver.py | 8 | tenants, admin_sessions, users, roles, user_roles, user_entitlements, approvers, approval_rules |
| Audit/Logging | audit.py | 4 | audit_logs, access_request_logs, certification_campaigns, certification_items |
| GRC Foundation | grc_foundation.py | 3 | org_units, framework_definitions, framework_requirements |
| Risk Intelligence | risk.py | 4 | risk_violations, mitigation_controls, risk_rules, tenant_rule_preferences |
| Firefighter | firefighter.py | 4 | firefighter_requests, firefighter_sessions, firefighter_activities, firefighter_id_configs |
| Operations | operations.py | 14 | org_rules, bulk_jobs, sync_configs, sync_history, transport_records, notification_records, notification_preferences, custom_tcodes, model_templates, org_user_assignments, org_role_restrictions, orchestration_contexts, mitigation_monitor, shopping_carts |
| Intelligence | intelligence.py | 11 | troubleshooter_users/roles/transactions, role_intelligence, drift_snapshots, fiori_apps, identity_accounts, identity_clusters, migration_mappings, timeline_events, audit_evidence |
| Engines | engines.py | 4 | engine_evidence, engine_findings, engine_execution_plans, engine_decision_workflows |
| Process Control | process_control.py | 14 | process_controls, control_tests, control_deficiencies, control_self_assessments, ccm_rules, ccm_executions, grc_evidence, signoff_certifications, control_objectives, subprocesses, policy_documents, question_library, questionnaires, questionnaire_responses |
| Risk Management | risk_management.py | 14 | enterprise_risks, risk_assessments, risk_appetites, key_risk_indicators, kri_measurements, risk_responses, risk_incidents, business_objectives, risk_scenarios, monte_carlo_simulations, risk_opportunities, risk_workflows, risk_workflow_steps, kri_data_sources |
| SAP Security | sap_security_controls.py | 5 | sap_security_controls, control_value_mappings, control_evaluations, control_exceptions, system_security_profiles |
| Audit Management | audit_management.py | 12 | auditable_entities, audit_plans, audit_engagements, audit_work_programs, audit_procedures, audit_workpapers, audit_findings, audit_actions, auditor_time_entries, auditor_resources, audit_dimensions, audit_announcements |
| Extended Modules | extended_modules.py | 18 | jml_policies, jml_events, vendors, vendor_assessments, vendor_issues, vendor_contracts, fraud_rules, fraud_alerts, fraud_cases, bia_records, bcm_plans, bcm_test_exercises, incident_activations, whistleblower_cases, whistleblower_messages, standalone_surveys, survey_distributions, survey_answers |
| Template Library | template_library.py | 4 | template_packs, template_pack_versions, template_items, tenant_item_activations |

### Migration Chain (base -> head)

1. `20260117_000001` — Initial schema (base)
2. `20260822_121800` — Operations + Intelligence + Security
3. `20260822_183956` — Engine persistence tables
4. `20260826_100000` — Orchestration + shopping carts
5. `20260903_100000` — GRC suite tables
6. `20260904_120000` — MFA columns to users
7. `20260904_150000` — XL-A / XL-C cross-module
8. `20260918_100000` — SAP GRC gap models
9. `20261004_100000` — Extended modules (JML, TPRM, BCM, Fraud, WB, Survey)
10. `20261004_200000` — Template library
11. `20261005_100000` — Template columns on functional tables
12. `20261005_200000` — Platform config
13. `20261031_100000` — Risk module enhancements (HEAD)

---

## 4. Frontend

**Total Route Definitions:** ~130 (including aliases)
**Total Page Components:** 125 .tsx files
**Module Directories:** 24
**Service/API Files:** 6 (1,399 LOC)
**Context Providers:** 3 (Auth, Theme, FormConfig)
**Layouts:** 2 (DashboardLayout, AuthLayout)

### Pages by Module

| Module | Pages | Route Prefix |
|--------|-------|-------------|
| access-requests | 7 | /access-requests |
| admin | 3 | /admin |
| ai | 8 | /ai |
| audit | 1 | /audit |
| audit-management | 4 | /audit-management |
| auth | 1 | /login |
| bcm | 3 | /bcm |
| certification | 2 | /certification |
| compliance | 2 | /compliance |
| firefighter | 4 | /privileged-access |
| fraud | 3 | /fraud |
| intelligence | 10 | /intelligence |
| integrations | 1 | /integrations |
| jml | 2 | /jml |
| library | 5 | /library |
| ml | 4 | /ml |
| password | 2 | /password |
| process-control | 4 | /process-control |
| provisioning | 1 | /provisioning |
| reports | 2 | /reports |
| risk | 10 | /risk |
| risk-management | 5 | /risk-management |
| roles | 3 | /roles |
| security-controls | 5 | /security-controls |
| settings | 12 | /settings |
| survey | 3 | /surveys |
| tprm | 3 | /tprm |
| users | 3 | /users |
| whistleblower | 2 | /whistleblower |
| workflows | 7 | /workflows |
| Root (Dashboard, CommandCenter, Landing) | 3 | / |

---

## 5. Authentication & Authorization

| Mechanism | Implementation |
|-----------|---------------|
| JWT (HS256) | PyJWT, 30-min access / 7-day refresh |
| Password hashing | bcrypt via passlib |
| MFA | TOTP (pyotp + qrcode) |
| SSO - SAML 2.0 | python3-saml |
| SSO - OIDC | Authorization Code + PKCE |
| LDAP/AD auth | Direct bind |
| Azure AD auth | MSAL (ROPC flow) |
| Rate limiting | slowapi (10/min auth, 60/min default) |
| Token blacklist | In-memory + Redis TTL |
| Account lockout | 5 failures -> 30-min lock |
| Tenant isolation | JWT claim + ContextVar ORM scoping |

### RBAC Roles

| Role | Scope |
|------|-------|
| super_admin | Full platform |
| admin | Tenant-level all |
| security_admin | GRC focus (roles, SoD, firefighter, risk) |
| manager | Approvals, reports |
| end_user | Self-service, own requests |
| platform_admin | Cross-tenant access |
| + 12 specialized | ciso, compliance_officer, risk_manager, auditor, etc. |

---

## 6. Background Jobs & Schedulers

### AutomationScheduler (9 jobs)

| Job | Interval | Purpose |
|-----|----------|---------|
| check_inactive_users | Daily | Lock 90-day inactive accounts |
| revoke_expired_access | Hourly | Revoke roles past valid_to |
| check_contractor_expiry | 12h | Lock expired contractors |
| check_password_expiry | Daily | 14-day password expiry warning |
| deprovision_failed_reviews | 6h | Remove access rejected in certs |
| sync_ad_groups | 2h | Sync AD group -> SAP role |
| batch_risk_analysis | 12h | Full SoD/risk delta analysis |
| ff_pending_review_check | Daily | Escalate overdue FF reviews |
| role_reaffirmation_check | N/A | Overdue role reaffirmation |

### SyncScheduler (7 templates)

Incremental user (1h), full user (daily), incremental role (2h), full role (weekly), entitlement (4h), risk analysis (6h, CRITICAL), usage data (daily).

### ProvisioningQueue

Priority-based async queue, 5 concurrent workers, max 10,000 tasks, retry with exponential backoff.

---

## 7. Connector Integrations

| Connector | Type | Auth | Status |
|-----------|------|------|--------|
| SAP RFC | pyrfc | User/pass | Implemented (mock fallback) |
| Azure AD | Microsoft Graph | OAuth2 / MSAL | Implemented (mock fallback) |
| Okta | REST v1 | API token | Implemented (mock fallback) |
| SuccessFactors | OData v2 | OAuth2 SAML / Basic | Implemented (mock fallback) |
| Workday | REST | TBD | Stub/template |
| ServiceNow | Table API | Basic / OAuth2 | Implemented (mock fallback) |

---

## 8. Key Architectural Patterns

- **Multi-tenant:** ContextVar + ORM automatic SELECT/INSERT scoping (`db/tenant_scoping.py`)
- **Per-tenant engines:** `Dict[str, Engine]` registries per router (risk, identity, mass_admin, role_intelligence, access_requests)
- **Enum handling:** All DB columns VARCHAR(50); all `to_dict()` use `getattr(x, "value", x)` pattern
- **DB-first loading:** Managers query DB, fall back to hardcoded seed
- **Template library:** Copy-on-write activation per tenant; master templates tenant_id=NULL
- **DI pattern:** `Depends(_get_manager)` + `Depends(_get_tenant_id)` on all routes
- **Background tasks:** FastAPI built-in for async write-through; dedicated schedulers for recurring jobs
- **Deployment:** Gunicorn + Uvicorn workers behind systemd; Docker multi-stage available

---

## Discrepancy Notes

| Metric | Expected (docs) | Actual (verified) | Delta |
|--------|-----------------|-------------------|-------|
| API Routes | ~912 | 1,169 | +257 |
| DB Tables | 81 | 141 | +60 |
| Frontend Pages | N/A | 125 | — |

The higher counts reflect growth since the initial estimates: extended modules (JML, TPRM, Fraud, BCM, Whistleblower, Survey), template library, AI copilot, risk management enhancements, and additional intelligence/analytics endpoints.
