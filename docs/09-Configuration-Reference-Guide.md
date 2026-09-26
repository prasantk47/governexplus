# GovernexPlus — Configuration & Setup Reference

**Version:** 2.0
**Applies to:** GovernexPlus 2.x
**Last updated:** 2026-09-06

---

## Table of Contents

1. [Environment Variables](#1-environment-variables)
2. [SoD Rule Configuration](#2-sod-rule-configuration)
3. [Workflow Configuration](#3-workflow-configuration)
4. [Notification Configuration](#4-notification-configuration)
5. [Firefighter Configuration](#5-firefighter-configuration)
6. [Risk Scoring Configuration](#6-risk-scoring-configuration)
7. [CCM Rule Configuration](#7-ccm-rule-configuration)
8. [Report Configuration](#8-report-configuration)
9. [i18n Configuration](#9-i18n-configuration)
10. [RBAC Role Definitions](#10-rbac-role-definitions)

---

## 1. Environment Variables

All environment variables are read at startup via `python-dotenv` from a `.env` file in the project root, or from the host environment. Production deployments should inject these via Docker secrets, Kubernetes ConfigMaps/Secrets, or a secrets manager such as HashiCorp Vault or AWS Secrets Manager. Never commit `.env` files containing secrets to source control.

### 1.1 Authentication & Security

| Variable | Type | Default | Description | Example |
|---|---|---|---|---|
| `JWT_SECRET` | `string` | Auto-generated (dev warning) | HMAC secret used to sign and verify JWT tokens. **Required in production.** Minimum 32 characters recommended; use 64+ hex characters for production. | `a3f8c2...` |
| `JWT_ALGORITHM` | `string` | `HS256` | JWT signing algorithm. Supported values: `HS256`, `HS384`, `HS512`, `RS256` (RS256 requires RSA key pair). | `HS256` |
| `JWT_EXPIRY_HOURS` | `integer` | `8` | Number of hours before a JWT access token expires. After expiry the user must re-authenticate. | `8` |
| `JWT_REFRESH_EXPIRY_DAYS` | `integer` | `7` | Lifetime in days for refresh tokens when refresh-token flow is enabled. | `7` |
| `HTTPS_ENABLED` | `boolean` | `false` | When `true`, the application sets `Strict-Transport-Security` headers and rejects non-HTTPS origins in CORS validation. Set to `true` in all production environments. | `true` |

### 1.2 Database

| Variable | Type | Default | Description | Example |
|---|---|---|---|---|
| `DATABASE_URL` | `string` | `sqlite:///./grc_platform.db` | SQLAlchemy connection URL. Use PostgreSQL for all non-development environments. Supports PostgreSQL (`postgresql+asyncpg://`) and SQLite. | `postgresql+asyncpg://grc:secret@db:5432/governex` |
| `DB_ECHO` | `boolean` | `false` | When `true`, SQLAlchemy logs every SQL statement to stdout. Useful for query debugging. Never enable in production. | `false` |
| `AUTO_MIGRATE` | `boolean` | `false` | When `true`, the application runs `alembic upgrade head` automatically on startup. Recommended for development; use explicit migration commands in production. | `false` |
| `DB_POOL_SIZE` | `integer` | `10` | Number of persistent connections maintained in the SQLAlchemy connection pool. | `20` |
| `DB_MAX_OVERFLOW` | `integer` | `20` | Maximum connections allowed above `DB_POOL_SIZE` during traffic spikes. | `40` |
| `DB_POOL_TIMEOUT` | `integer` | `30` | Seconds to wait for a connection from the pool before raising an error. | `30` |
| `DB_POOL_RECYCLE` | `integer` | `3600` | Seconds after which a connection is recycled. Prevents stale connections on PostgreSQL. | `3600` |

### 1.3 CORS & Networking

| Variable | Type | Default | Description | Example |
|---|---|---|---|---|
| `CORS_ORIGINS` | `string` (comma-separated) | `http://localhost:5173` | Allowed CORS origins. In production, list only your exact frontend origin(s). Wildcards are not permitted in production mode. | `https://grc.acme.com,https://grc-staging.acme.com` |
| `API_PREFIX` | `string` | `/api/v1` | URL prefix for all API routes. | `/api/v1` |
| `HOST` | `string` | `0.0.0.0` | Uvicorn bind host. | `0.0.0.0` |
| `PORT` | `integer` | `8000` | Uvicorn bind port. | `8000` |
| `WORKERS` | `integer` | `4` | Number of Uvicorn/Gunicorn worker processes. Rule of thumb: `2 × CPU_count + 1`. | `9` |

### 1.4 Rate Limiting

| Variable | Type | Default | Description | Example |
|---|---|---|---|---|
| `RATE_LIMIT_DEFAULT` | `string` | `60/minute` | Default rate limit applied to all API endpoints. Format: `{count}/{period}` where period is `second`, `minute`, or `hour`. | `60/minute` |
| `RATE_LIMIT_AUTH` | `string` | `10/minute` | Rate limit applied specifically to `/api/v1/auth/*` endpoints. Prevents brute-force attacks. | `10/minute` |
| `RATE_LIMIT_STORAGE` | `string` | `memory://` | Storage backend for rate limit counters. Use `redis://host:6379` in multi-worker deployments to share state across workers. | `redis://redis:6379` |

### 1.5 Multi-Tenancy

| Variable | Type | Default | Description | Example |
|---|---|---|---|---|
| `DEFAULT_TENANT_ID` | `string` | `default` | Tenant identifier used when no tenant context is resolved from the JWT claim. Primarily for single-tenant deployments. | `acme-corp` |
| `TENANT_ISOLATION_MODE` | `string` | `strict` | Controls tenant isolation enforcement. `strict` = hard-fail on cross-tenant access; `audit` = log but allow (for migration only). | `strict` |

### 1.6 AI / LLM Integration

| Variable | Type | Default | Description | Example |
|---|---|---|---|---|
| `OPENAI_API_KEY` | `string` | — | OpenAI API key for GPT-4 / GPT-4o models. Used for AI narrative generation, risk explanations, and GRC Copilot features. | `sk-...` |
| `OPENAI_MODEL` | `string` | `gpt-4o` | OpenAI model identifier. | `gpt-4o` |
| `AZURE_OPENAI_KEY` | `string` | — | Azure OpenAI Service API key. Used when `LLM_PROVIDER=azure`. | `abc123...` |
| `AZURE_OPENAI_ENDPOINT` | `string` | — | Azure OpenAI endpoint URL including deployment name. | `https://myresource.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | `string` | — | Azure OpenAI deployment name. | `gpt-4o-prod` |
| `ANTHROPIC_API_KEY` | `string` | — | Anthropic API key for Claude models. Used when `LLM_PROVIDER=anthropic`. | `sk-ant-...` |
| `ANTHROPIC_MODEL` | `string` | `claude-sonnet-4-5` | Anthropic model identifier. | `claude-opus-4-5` |
| `LLM_PROVIDER` | `string` | `openai` | Active LLM provider. Values: `openai`, `azure`, `anthropic`, `ollama`, `none`. When `none`, AI features return structured fallback responses. | `azure` |
| `OLLAMA_BASE_URL` | `string` | `http://localhost:11434` | Ollama API base URL for local LLM inference. Used when `LLM_PROVIDER=ollama`. | `http://ollama:11434` |
| `OLLAMA_MODEL` | `string` | `llama3.1` | Ollama model to use for inference. | `mistral` |

### 1.7 SAP Connectivity

| Variable | Type | Default | Description | Example |
|---|---|---|---|---|
| `SAP_HOST` | `string` | — | SAP application server hostname or IP address. | `sap-ecc.acme.com` |
| `SAP_SYSNR` | `string` | `00` | SAP system number (two digits). | `00` |
| `SAP_CLIENT` | `string` | `100` | SAP logon client number. | `100` |
| `SAP_USER` | `string` | — | SAP RFC service user name. This user must have RFC authorization objects assigned. | `GNX_RFC` |
| `SAP_PASSWORD` | `string` | — | Password for the SAP RFC service user. | `secret` |
| `SAP_LANGUAGE` | `string` | `EN` | SAP logon language. | `EN` |
| `SAP_USE_MOCK` | `boolean` | `true` | When `true`, the mock SAP connector is used instead of live RFC calls. Set to `false` in production environments with live SAP. | `false` |
| `SAP_MSG_HOST` | `string` | — | Message server host for load-balanced SAP connections. | `sap-msg.acme.com` |
| `SAP_MSG_SERVICE` | `string` | — | Message server service name or port. | `sapmsP01` |
| `SAP_LOGON_GROUP` | `string` | — | SAP logon group for load balancing. | `PUBLIC` |
| `SAP_SNC_LIB` | `string` | — | Path to the SAP SNC library (SAPCRYPTOLIB) for encrypted RFC connections. | `/usr/lib/libsapcrypto.so` |
| `SAP_SNC_MY_NAME` | `string` | — | SNC identity of the GovernexPlus RFC client. | `p:CN=GNX,O=ACME,C=US` |
| `SAP_SNC_PARTNER_NAME` | `string` | — | SNC identity of the SAP application server. | `p:CN=SAP,O=ACME,C=US` |

### 1.8 Azure AD Integration

| Variable | Type | Default | Description | Example |
|---|---|---|---|---|
| `AZURE_CLIENT_ID` | `string` | — | Azure AD application (client) ID for the GovernexPlus app registration. | `11111111-...` |
| `AZURE_CLIENT_SECRET` | `string` | — | Client secret for the Azure AD app registration. | `secret~value` |
| `AZURE_TENANT_ID` | `string` | — | Azure AD directory (tenant) ID. | `22222222-...` |
| `AZURE_GRAPH_SCOPES` | `string` | `https://graph.microsoft.com/.default` | Microsoft Graph API scopes requested during token acquisition. | `https://graph.microsoft.com/.default` |
| `AZURE_SYNC_INTERVAL_HOURS` | `integer` | `6` | How frequently the Azure AD user/group sync job runs. | `6` |

### 1.9 Workday Integration

| Variable | Type | Default | Description | Example |
|---|---|---|---|---|
| `WORKDAY_API_URL` | `string` | — | Workday RaaS or REST API base URL. | `https://wd2-impl-services1.workday.com/ccx/service/acme/Human_Resources/v42.0` |
| `WORKDAY_USERNAME` | `string` | — | Workday integration system user (ISU) username. | `ISU_GNX` |
| `WORKDAY_PASSWORD` | `string` | — | Password for the Workday ISU. | `secret` |
| `WORKDAY_TENANT` | `string` | — | Workday tenant name. | `acme` |
| `WORKDAY_SYNC_INTERVAL_HOURS` | `integer` | `12` | How frequently the Workday JML sync job runs. | `12` |

### 1.10 SuccessFactors Integration

| Variable | Type | Default | Description | Example |
|---|---|---|---|---|
| `SF_API_URL` | `string` | — | SAP SuccessFactors OData API base URL. | `https://api4.successfactors.com` |
| `SF_COMPANY_ID` | `string` | — | SuccessFactors company ID. | `ACME` |
| `SF_USERNAME` | `string` | — | SuccessFactors API username (format: `user@companyId`). | `sfadmin@ACME` |
| `SF_API_KEY` | `string` | — | SuccessFactors API key or password for basic auth. | `secret` |
| `SF_SYNC_INTERVAL_HOURS` | `integer` | `12` | How frequently the SuccessFactors JML sync job runs. | `12` |

### 1.11 Logging

| Variable | Type | Default | Description | Example |
|---|---|---|---|---|
| `LOG_LEVEL` | `string` | `INFO` | Minimum log level. Values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. | `WARNING` |
| `LOG_FORMAT` | `string` | `json` | Log output format. `json` produces structured JSON logs suitable for ELK/Loki ingestion. `text` produces human-readable output for development. | `json` |
| `LOG_FILE` | `string` | — | Optional file path for log output in addition to stdout. | `/var/log/governex/app.log` |
| `SENTRY_DSN` | `string` | — | Sentry Data Source Name for error tracking and performance monitoring. | `https://key@sentry.io/12345` |
| `SENTRY_ENVIRONMENT` | `string` | `production` | Sentry environment tag. | `production` |

---

## 2. SoD Rule Configuration

### 2.1 Built-in Rule Categories

GovernexPlus ships with **121 pre-built SoD rules** in `core/rules/sod_ruleset.py`, covering all major SAP functional areas:

| Category | Code | Rule Count | Examples |
|---|---|---|---|
| Financial Accounting | FI | 24 | Vendor create + AP payment; Journal entry + approval |
| Materials Management | MM | 18 | Purchase order create + goods receipt + invoice verify |
| Sales & Distribution | SD | 15 | Customer create + credit limit + billing |
| Human Resources | HR | 12 | Employee hire + payroll posting + salary change |
| Basis Administration | BA | 10 | User admin + role admin + audit log deletion |
| Treasury | TR | 8 | Bank account create + payment release |
| Asset Accounting | AA | 8 | Asset create + retirement + depreciation |
| Warehouse Management | WM | 7 | Goods movement + inventory adjustment |
| Quality Management | QM | 6 | Inspection lot create + usage decision |
| Plant Maintenance | PM | 5 | Work order create + technical completion + settlement |
| Project Systems | PS | 5 | Project create + settlement + cost planning |
| Cross-Application | XP | 3 | Debug with replace + system administration |

Rules are loaded into both the standalone rule engine (`core/rules/engine.py`) and the Risk Intelligence Engine (`core/ara/rules.py`) via bridge modules at startup.

### 2.2 Custom Rule Schema

Custom SoD rules can be created via the API (`POST /api/v1/sod-rules/`) or imported via CSV. A rule defines two conflicting permission sets (functions A and B) and declares the conflict severity.

```json
{
  "rule_id": "CUSTOM-001",
  "rule_name": "Custom AP Vendor + Payment",
  "description": "Segregation between vendor master maintenance and payment processing",
  "category": "FI",
  "risk_level": "critical",
  "function_a": {
    "label": "Vendor Master Maintenance",
    "tcodes": ["FK01", "FK02", "XK01", "XK02"],
    "auth_objects": [
      { "object": "F_LFA1_BUK", "field": "ACTVT", "values": ["01", "02"] }
    ]
  },
  "function_b": {
    "label": "Outgoing Payment Processing",
    "tcodes": ["F110", "F-53", "F-58"],
    "auth_objects": [
      { "object": "F_BKPF_BUK", "field": "ACTVT", "values": ["01", "02"] }
    ]
  },
  "mitigation_hint": "Require dual-control approval for payments to recently created vendors",
  "regulatory_references": ["SOX Section 302", "ITGC-AP-01"],
  "active": true,
  "tenant_id": "acme-corp"
}
```

### 2.3 Rule Import CSV Format

Bulk rule imports are accepted via `POST /api/v1/sod-rules/import` with a CSV file attachment. The required columns are:

```csv
rule_id,rule_name,category,risk_level,function_a_label,function_a_tcodes,function_b_label,function_b_tcodes,description,active
CUSTOM-001,Vendor Create + Payment,FI,critical,Vendor Master,FK01|XK01,Outgoing Payment,F110|F-53,Creates vendors then pays them,true
CUSTOM-002,PO Create + Invoice Verify,MM,high,Purchase Order Create,ME21N|ME21,Invoice Verify,MIRO|MIR7,Full P2P cycle in one user,true
```

Field notes:
- `rule_id`: Must be unique per tenant. Existing rule IDs are never overwritten (idempotent import).
- `risk_level`: One of `low`, `medium`, `high`, `critical`.
- `function_a_tcodes` / `function_b_tcodes`: Pipe-delimited list of SAP transaction codes.
- `active`: `true` or `false`. Inactive rules are stored but not evaluated.

### 2.4 Tenant Rule Preferences

Each tenant can configure rule evaluation behavior independently. These settings are stored in the `tenant_configurations` table and managed via `PUT /api/v1/admin/tenants/{tenant_id}/rule-config`.

```json
{
  "tenant_id": "acme-corp",
  "rule_evaluation": {
    "include_inactive_users": false,
    "include_firefighter_sessions": true,
    "org_level_sensitivity": "full",
    "apply_mitigated_rule_suppression": true,
    "risk_appetite_override": {
      "FI": "zero_tolerance",
      "HR": "low",
      "MM": "medium"
    }
  },
  "rule_exclusions": ["CUSTOM-005", "XP-003"],
  "default_simulation_scope": "all_active_users"
}
```

---

## 3. Workflow Configuration

### 3.1 Approval Stage Types

GovernexPlus workflows support the following stage types, which can be combined in any sequence:

| Stage Type | Code | Description |
|---|---|---|
| Manager Approval | `manager` | Routes to the requester's direct manager (resolved via `manager_user_id`). |
| Role Owner Approval | `role_owner` | Routes to the designated owner of each requested role. |
| Security Admin Approval | `security_admin` | Routes to any user with the `security_admin` role in the tenant. |
| Risk Manager Approval | `risk_manager` | Routes to the risk manager when the request involves high/critical SoD violations. |
| Compliance Officer Approval | `compliance_officer` | Routes to the compliance officer for regulatory-sensitive roles. |
| IT Helpdesk Approval | `it_helpdesk` | Routes to IT helpdesk queue (for provisioning confirmation). |
| Custom Approver | `custom` | Routes to a specific named user or group defined in the workflow definition. |
| Auto-Approve | `auto` | Automatically approves the stage if configured conditions are met (e.g., no SoD violations, low risk score). |

### 3.2 Workflow Definition Schema

Workflows are defined in `core/workflow/orchestrator.py` and stored in the `workflow_definitions` table. Example multi-stage workflow:

```json
{
  "workflow_id": "std-access-request-v2",
  "name": "Standard Access Request — Dual Approval",
  "trigger": "access_request_submitted",
  "applies_to": {
    "request_type": ["role_assignment", "bulk_access"],
    "risk_level": ["low", "medium", "high", "critical"]
  },
  "stages": [
    {
      "stage_id": 1,
      "stage_type": "manager",
      "label": "Line Manager Approval",
      "sla_hours": 48,
      "escalation_after_hours": 24,
      "escalate_to": "security_admin"
    },
    {
      "stage_id": 2,
      "stage_type": "risk_manager",
      "label": "Risk Review",
      "condition": "risk_score >= 70 OR sod_violations > 0",
      "sla_hours": 24,
      "escalation_after_hours": 12,
      "escalate_to": "compliance_officer"
    },
    {
      "stage_id": 3,
      "stage_type": "security_admin",
      "label": "Security Sign-off",
      "sla_hours": 24,
      "escalation_after_hours": 8,
      "escalate_to": "tenant_admin"
    }
  ],
  "on_approve": "provision_access",
  "on_reject": "notify_requester_rejection",
  "parallel_stages": false
}
```

### 3.3 Escalation Timeouts

Escalation is triggered automatically by the scheduler (`core/scheduler/automation_jobs.py`) running every 15 minutes.

| Configuration Key | Default | Description |
|---|---|---|
| `escalation_check_interval_minutes` | `15` | How often the scheduler checks for overdue approvals. |
| `manager_sla_hours` | `48` | Default SLA for manager approval stages. |
| `security_admin_sla_hours` | `24` | Default SLA for security admin stages. |
| `max_escalation_depth` | `3` | Maximum number of escalation hops before auto-rejection. |
| `auto_reject_on_max_escalation` | `false` | When `true`, requests auto-reject after max escalation depth is reached. |

### 3.4 Delegation Rules

Approvers may delegate their approval authority via `POST /api/v1/approvals/delegations`. Delegation configuration:

```json
{
  "delegator_user_id": "user-uuid",
  "delegate_user_id": "user-uuid-2",
  "start_date": "2026-09-10",
  "end_date": "2026-09-20",
  "scope": "all",
  "reason": "Annual leave",
  "notify_delegator_on_action": true
}
```

`scope` values: `all` (full delegation), `low_risk_only`, `specific_workflows` (with `workflow_ids` array).

### 3.5 SLA Configuration

SLA breach tracking is recorded in the `workflow_sla_events` table. Per-tenant SLA overrides:

```json
{
  "tenant_id": "acme-corp",
  "sla_config": {
    "critical_request_sla_hours": 4,
    "high_request_sla_hours": 24,
    "medium_request_sla_hours": 48,
    "low_request_sla_hours": 72,
    "firefighter_approval_sla_minutes": 30,
    "notify_approver_at_percent": 75,
    "breach_notification_channels": ["email", "in_app"]
  }
}
```

---

## 4. Notification Configuration

### 4.1 Email Templates

Email notifications are rendered from Jinja2 templates stored in `core/notifications/templates/`. Each event type maps to a template file:

| Event | Template File | Variables Available |
|---|---|---|
| Access request submitted | `access_request_submitted.html` | `requester_name`, `request_id`, `roles_requested`, `approval_link` |
| Approval required | `approval_required.html` | `approver_name`, `requester_name`, `request_id`, `risk_summary`, `approve_link`, `reject_link` |
| Request approved | `request_approved.html` | `requester_name`, `request_id`, `provisioned_roles`, `effective_date` |
| Request rejected | `request_rejected.html` | `requester_name`, `request_id`, `rejection_reason`, `approver_name` |
| Escalation triggered | `escalation_triggered.html` | `new_approver_name`, `original_approver_name`, `request_id`, `hours_overdue` |
| Firefighter session started | `firefighter_session_started.html` | `user_name`, `session_id`, `reason`, `system`, `start_time`, `monitor_link` |
| Certification task assigned | `certification_task_assigned.html` | `certifier_name`, `campaign_name`, `due_date`, `item_count`, `review_link` |
| SoD violation detected | `sod_violation_detected.html` | `user_name`, `rule_name`, `risk_level`, `violation_id`, `details_link` |
| Password reset | `password_reset.html` | `user_name`, `reset_link`, `expiry_hours` |

### 4.2 Email SMTP Configuration

| Variable | Type | Default | Description |
|---|---|---|---|
| `SMTP_HOST` | `string` | `localhost` | SMTP server hostname. |
| `SMTP_PORT` | `integer` | `587` | SMTP server port. |
| `SMTP_USER` | `string` | — | SMTP authentication username. |
| `SMTP_PASSWORD` | `string` | — | SMTP authentication password. |
| `SMTP_USE_TLS` | `boolean` | `true` | Enable STARTTLS. |
| `SMTP_FROM_ADDRESS` | `string` | `noreply@governex.app` | Sender address for all notification emails. |
| `SMTP_FROM_NAME` | `string` | `GovernexPlus` | Display name for the sender. |

### 4.3 Notification Channels

| Channel | Configuration Key | Description |
|---|---|---|
| Email | `email` | SMTP-based HTML email (default enabled). |
| In-App | `in_app` | Bell-icon notifications in the GovernexPlus UI (always enabled). |
| Microsoft Teams | `teams_webhook_url` | Incoming webhook URL for Teams channel messages. |
| Slack | `slack_webhook_url` | Incoming webhook URL for Slack channel messages. |
| ServiceNow | `snow_instance_url` | Creates ServiceNow incidents for critical violations. |
| PagerDuty | `pagerduty_routing_key` | Triggers PagerDuty alerts for P0-severity events. |

### 4.4 Per-User Delivery Preferences

Users can configure their notification preferences via `PUT /api/v1/users/me/notification-preferences`:

```json
{
  "channels": {
    "email": true,
    "in_app": true,
    "teams": false,
    "slack": true
  },
  "digest_mode": "immediate",
  "digest_schedule": null,
  "quiet_hours": {
    "enabled": true,
    "start": "22:00",
    "end": "07:00",
    "timezone": "America/New_York"
  },
  "event_subscriptions": {
    "approval_required": true,
    "escalation": true,
    "sod_violation": true,
    "certification_due": true,
    "system_alerts": false
  }
}
```

`digest_mode` options: `immediate`, `hourly_digest`, `daily_digest`.

---

## 5. Firefighter Configuration

### 5.1 Reason Code Catalog

Firefighter access requests require a reason code drawn from a configurable catalog. Default reason codes:

| Code | Label | Requires Ticket | Requires Manager Pre-Approval |
|---|---|---|---|
| `PROD_INCIDENT` | Production Incident Response | Yes | No (post-approval within 2h) |
| `MONTH_END_CLOSE` | Month-End / Year-End Close Support | Yes | Yes |
| `BATCH_FAILURE` | Batch Job Failure Recovery | Yes | No |
| `DATA_CORRECTION` | Data Correction / Hotfix | Yes | Yes |
| `AUDIT_SUPPORT` | Auditor Support Access | Yes | Yes |
| `SYSTEM_UPGRADE` | System Upgrade / Patching | Yes | Yes |
| `DR_TEST` | Disaster Recovery Test | Yes | Yes |
| `VENDOR_SUPPORT` | Vendor / Consultant Access | Yes | Yes |
| `TRAINING` | Training Environment Only | No | No |

Reason codes are managed via `PUT /api/v1/admin/firefighter/reason-codes`.

### 5.2 Ticket Reference Policies

| Setting | Default | Description |
|---|---|---|
| `require_ticket_reference` | `true` | When `true`, a ServiceNow/Jira ticket number is mandatory for all firefighter requests except `TRAINING`. |
| `ticket_validation_enabled` | `false` | When `true`, GovernexPlus calls the ITSM API to validate that the referenced ticket exists and is open. |
| `ticket_pattern` | `^(INC|CHG|PRB)\d{7}$` | Regular expression for ticket number validation. |
| `itsm_base_url` | — | Base URL of the ITSM system for ticket validation. |

### 5.3 Session Duration Limits

| Setting | Default | Description |
|---|---|---|
| `max_session_duration_hours` | `8` | Maximum allowed firefighter session duration. Sessions are automatically terminated at expiry. |
| `default_session_duration_hours` | `4` | Default duration when the requester does not specify. |
| `extension_allowed` | `true` | Allow session duration extension requests. |
| `max_extension_hours` | `4` | Maximum hours by which a session can be extended. |
| `extension_requires_approval` | `true` | Whether session extensions require re-approval. |
| `max_concurrent_sessions_per_user` | `1` | Users may not hold multiple active firefighter sessions simultaneously. |

### 5.4 Review Requirements

| Setting | Default | Description |
|---|---|---|
| `review_required_within_hours` | `24` | Firefighter session activity logs must be reviewed within this window. |
| `reviewer_role` | `security_admin` | Role required to perform session reviews. |
| `auto_flag_sensitive_tcodes` | `true` | Sessions containing sensitive transaction codes (e.g., `SE16`, `SU01`, `SE38`) are automatically flagged for mandatory review. |
| `sensitive_tcode_list` | `SE16,SE16N,SU01,SU10,SE38,SA38,SM30,SM31` | Comma-separated list of transaction codes that trigger mandatory review. |
| `notify_manager_on_session_close` | `true` | Sends the requester's manager a summary email when a session closes. |

---

## 6. Risk Scoring Configuration

### 6.1 Likelihood / Impact Scales

GovernexPlus supports three risk matrix sizes configurable per tenant:

**3×3 Matrix (default)**

| | Low Impact (1) | Medium Impact (2) | High Impact (3) |
|---|---|---|---|
| Low Likelihood (1) | 1 — Low | 2 — Low | 3 — Medium |
| Medium Likelihood (2) | 2 — Low | 4 — Medium | 6 — High |
| High Likelihood (3) | 3 — Medium | 6 — High | 9 — Critical |

**5×5 Matrix (enterprise)**

| | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 5 | 5 | 10 | 15 | 20 | 25 |
| 4 | 4 | 8 | 12 | 16 | 20 |
| 3 | 3 | 6 | 9 | 12 | 15 |
| 2 | 2 | 4 | 6 | 8 | 10 |
| 1 | 1 | 2 | 3 | 4 | 5 |

Score bands for 5×5: `1–5` Low, `6–11` Medium, `12–18` High, `19–25` Critical.

Select matrix size per tenant via `PUT /api/v1/admin/tenants/{tenant_id}/risk-config`:

```json
{
  "risk_matrix": "5x5",
  "score_bands": {
    "low": [1, 5],
    "medium": [6, 11],
    "high": [12, 18],
    "critical": [19, 25]
  }
}
```

### 6.2 Context Modifiers

Context modifiers adjust raw SoD risk scores based on organizational context:

| Modifier | Factor Range | Trigger |
|---|---|---|
| Executive user | +25% | User holds VP/Director/C-level job title |
| Segregated duties user | −15% | User is formally designated as a control owner for the conflicting function |
| Service account | −30% | User type = `service_account` with monitored usage policy |
| External contractor | +20% | User employment type = `contractor` |
| Finance department | +10% | User department code matches finance org units |
| HR department | +15% | User department code matches HR org units |

### 6.3 Usage Modifiers

Usage modifiers lower risk scores for access that is assigned but demonstrably unused:

| Modifier | Factor | Condition |
|---|---|---|
| Never used (180+ days) | −50% | No SM20 usage recorded in 180 days |
| Rarely used (30–180 days) | −20% | Last usage 30–180 days ago |
| Actively used | +0% | Usage within the last 30 days |
| High-frequency use | +15% | Transaction used more than 20× in the last 30 days |

Usage modifier configuration:

```json
{
  "usage_scoring": {
    "enabled": true,
    "lookback_days": 180,
    "never_used_threshold_days": 180,
    "rarely_used_threshold_days": 30,
    "high_frequency_threshold_count": 20
  }
}
```

### 6.4 Risk Appetite and Tolerance Thresholds

| Setting | Default | Description |
|---|---|---|
| `risk_appetite` | `medium` | Organization-level risk appetite declaration. Values: `zero_tolerance`, `low`, `medium`, `high`. |
| `tolerance_threshold_score` | `70` | Risk scores above this threshold require mandatory mitigation or exception approval. |
| `auto_escalate_threshold` | `85` | Risk scores above this trigger immediate escalation to the risk manager. |
| `acceptable_without_review` | `30` | Risk scores at or below this are automatically accepted without review. |
| `review_period_days` | `90` | Accepted risks must be reviewed every N days. |

---

## 7. CCM Rule Configuration

### 7.1 Continuous Control Monitoring Rule Types

| Rule Type | Code | Description | Example |
|---|---|---|---|
| Threshold Breach | `threshold` | Triggers when a numeric value exceeds a defined limit. | Payment > $1,000,000 without dual authorization. |
| Frequency Anomaly | `frequency` | Triggers when an action occurs more frequently than expected. | >10 user creations per day. |
| Pattern Match | `pattern` | Triggers when data matches a defined pattern or regular expression. | Vendor bank account changed within 24h of new payment. |
| Segregation Check | `segregation` | Triggers when a single user performs both sides of a controlled process. | Same user approved and posted a journal entry. |
| Time-Based | `time_window` | Triggers when actions occur outside approved time windows. | Payroll posting after 18:00 on a non-business day. |
| Value Comparison | `comparison` | Triggers when a field value deviates from a reference value by more than a threshold. | Invoice amount exceeds PO by >5%. |
| Absence Check | `absence` | Triggers when an expected action did NOT occur within a time window. | Period-end reconciliation not completed within 3 days of month-end. |

### 7.2 CCM Rule Schema

```json
{
  "rule_id": "CCM-FI-001",
  "rule_name": "High-Value Payment Without Dual Control",
  "rule_type": "threshold",
  "category": "FI",
  "severity": "critical",
  "description": "Detects outgoing payments above threshold that were not dual-authorized",
  "data_source": "sap_fi_documents",
  "query_template": "SELECT * FROM fi_payment_docs WHERE amount > {threshold} AND approval_count < 2",
  "parameters": {
    "threshold": 100000
  },
  "schedule": "*/15 * * * *",
  "deficiency_threshold": 1,
  "auto_create_finding": true,
  "finding_severity": "high",
  "owner_role": "control_owner",
  "remediation_sla_days": 5,
  "active": true
}
```

### 7.3 Scheduling Frequency

CCM rules can be scheduled using standard cron syntax or frequency shortcuts:

| Shortcut | Cron Expression | Description |
|---|---|---|
| `real_time` | `* * * * *` | Every minute (near-real-time). |
| `every_15_min` | `*/15 * * * *` | Every 15 minutes. |
| `hourly` | `0 * * * *` | Top of every hour. |
| `daily` | `0 6 * * *` | Daily at 06:00. |
| `weekly` | `0 6 * * 1` | Weekly on Monday at 06:00. |
| `month_end` | `0 6 28-31 * *` | Daily during last 4 days of each month. |

### 7.4 Auto-Deficiency Thresholds

When a CCM rule fires more than `deficiency_threshold` times within `deficiency_window_hours`, the system automatically creates a control deficiency record:

```json
{
  "deficiency_auto_creation": {
    "enabled": true,
    "deficiency_threshold": 3,
    "deficiency_window_hours": 24,
    "auto_assign_owner": true,
    "default_owner_role": "control_owner",
    "severity_escalation_on_repeat": true,
    "repeat_threshold": 5
  }
}
```

---

## 8. Report Configuration

### 8.1 PDF Templates

PDF reports are generated using `WeasyPrint` with Jinja2 HTML templates. Template files are located in `core/export/templates/pdf/`.

| Report | Template | Key Sections |
|---|---|---|
| SoD Violation Summary | `sod_violation_report.html` | Executive summary, violation table, heat map, mitigation status |
| User Access Review | `user_access_review.html` | User list, role matrix, last login, usage analysis |
| Firefighter Activity | `firefighter_activity_report.html` | Session log, tcode activity, reviewer sign-off |
| Risk Assessment | `risk_assessment_report.html` | Risk register, scores, trend chart, appetite comparison |
| Audit Evidence Package | `audit_evidence_package.html` | Control listing, evidence attachments, completeness score |
| Certification Results | `certification_results.html` | Campaign summary, certifier actions, revocation list |

PDF branding configuration:

```json
{
  "pdf_branding": {
    "logo_path": "/static/brand/logo.png",
    "primary_color": "#6366f1",
    "secondary_color": "#1e1b4b",
    "font_family": "Inter",
    "header_text": "GovernexPlus GRC Platform",
    "footer_text": "CONFIDENTIAL — {tenant_name} — Generated {date}",
    "watermark_text": null
  }
}
```

### 8.2 PPTX Branding

PowerPoint executive summary reports are generated using `python-pptx`. Template `.pptx` files are stored in `core/export/templates/pptx/`. Branding is applied at render time:

```json
{
  "pptx_branding": {
    "template_path": "/static/brand/exec-template.pptx",
    "title_font": "Calibri",
    "title_font_size": 36,
    "body_font": "Calibri",
    "body_font_size": 18,
    "accent_color_hex": "6366F1",
    "company_name": "ACME Corporation",
    "report_classification": "INTERNAL USE ONLY"
  }
}
```

### 8.3 Supported Export Formats

| Format | Content Types | Notes |
|---|---|---|
| PDF | All reports | Server-side rendered; returned as `application/pdf`. |
| PPTX | Executive summaries | PowerPoint 2016+ compatible. |
| XLSX | Tabular data exports | Column widths auto-sized; conditional formatting for risk levels. |
| CSV | Raw data exports | UTF-8 BOM encoded for Excel compatibility. |
| JSON | API consumers | Full structured export with metadata envelope. |

---

## 9. i18n Configuration

### 9.1 Supported Locales

GovernexPlus ships with full translations for the following locales:

| Locale Code | Language | Script | RTL |
|---|---|---|---|
| `en` | English | Latin | No |
| `de` | German | Latin | No |
| `fr` | French | Latin | No |
| `es` | Spanish | Latin | No |
| `pt-BR` | Brazilian Portuguese | Latin | No |
| `ja` | Japanese | CJK | No |
| `zh-CN` | Simplified Chinese | CJK | No |
| `ar` | Arabic | Arabic | Yes |
| `he` | Hebrew | Hebrew | Yes |

The active locale is detected in order: user preference → `Accept-Language` header → tenant default → `en`.

### 9.2 Translation File Format

Translation files are JSON files stored in `frontend/src/i18n/locales/{locale}.json`:

```json
{
  "common": {
    "save": "Save",
    "cancel": "Cancel",
    "delete": "Delete",
    "loading": "Loading..."
  },
  "risk": {
    "violations": "SoD Violations",
    "severity": {
      "low": "Low",
      "medium": "Medium",
      "high": "High",
      "critical": "Critical"
    }
  },
  "access_request": {
    "new_request": "New Access Request",
    "submitted_success": "Your access request has been submitted successfully."
  }
}
```

### 9.3 Adding a New Locale

1. Copy `frontend/src/i18n/locales/en.json` to `{locale}.json`.
2. Translate all string values. Keys must not be changed.
3. Register the locale in `frontend/src/i18n/index.ts` under the `supportedLocales` array.
4. If the locale is RTL, add it to the `rtlLocales` array — the frontend applies `dir="rtl"` to the `<html>` element automatically.
5. Add backend locale support by creating `core/i18n/locales/{locale}.json` for server-rendered notification emails and PDF reports.
6. Submit via PR and request QA sign-off from a native speaker.

### 9.4 RTL Settings

When an RTL locale is active, the frontend applies the following changes automatically:

- `<html dir="rtl">` attribute set.
- Tailwind CSS RTL utilities (`rtl:ml-auto`, `rtl:space-x-reverse`) active via the `tailwindcss-rtl` plugin.
- Sidebar layout mirrors to the right side.
- Table column ordering remains LTR (data tables are not mirrored).
- Chart axis labels are mirrored.
- PDF reports use a separate RTL-compatible template with right-aligned body text.

---

## 10. RBAC Role Definitions

### 10.1 Built-in Roles

#### `platform_admin`
Cross-tenant super-administrator. This role is only assignable by a GovernexPlus operator and is never visible inside a tenant's own user management screens.

| Permission Area | Access Level |
|---|---|
| Tenant management | Full CRUD |
| All tenant data | Read/Write (with audit log) |
| System configuration | Full |
| User management (all tenants) | Full |
| Audit logs | Full, immutable |

#### `tenant_admin`
Full administrator within a single tenant. Cannot access other tenants' data.

| Permission Area | Access Level |
|---|---|
| Tenant configuration | Full |
| User management | Full CRUD |
| Role management | Full CRUD |
| All GRC modules | Full |
| Audit logs (own tenant) | Read |

#### `security_admin`
SAP access governance specialist. Manages SoD rules, firefighter access, and provisioning.

| Permission Area | Access Level |
|---|---|
| SoD rules | Full CRUD |
| Firefighter sessions | Approve, monitor, review |
| Access requests | Approve/reject |
| Role library | Full CRUD |
| User access reports | Read |
| Risk analysis | Read |

#### `risk_manager`
Owns the risk register and mitigation strategy.

| Permission Area | Access Level |
|---|---|
| Risk register | Full CRUD |
| SoD violations | Read, assign mitigation |
| Mitigation controls | Full CRUD |
| Risk simulations | Full |
| Risk reports | Full |
| Risk Intelligence Engine rule configuration | Read/Write |

#### `auditor`
Read-only access to all GRC data for audit purposes. Cannot modify any records.

| Permission Area | Access Level |
|---|---|
| All GRC modules | Read only |
| Audit logs | Read only |
| Evidence packages | Read + Download |
| Reports | Generate + Download |
| User data | Read only (masked PII) |

#### `compliance_officer`
Owns control frameworks, certifications, and regulatory compliance posture.

| Permission Area | Access Level |
|---|---|
| Control frameworks | Full CRUD |
| Certification campaigns | Full CRUD |
| Compliance assessments | Full |
| Audit management | Full |
| Findings | Full CRUD |
| Process controls | Full CRUD |

#### `control_owner`
Responsible for specific controls assigned to them. Scoped to their control portfolio.

| Permission Area | Access Level |
|---|---|
| Assigned controls | Read + Update |
| CCM rule results | Read (assigned rules) |
| Deficiencies | Read + Respond |
| Evidence upload | Write (own controls) |

#### `employee`
End user. Can submit access requests and view their own access profile.

| Permission Area | Access Level |
|---|---|
| Access requests | Submit own |
| Approval inbox | Approve delegated requests |
| Own user profile | Read |
| Own risk summary | Read |
| Password reset | Self-service |

### 10.2 Permission Matrix Summary

| Permission | platform_admin | tenant_admin | security_admin | risk_manager | auditor | compliance_officer | control_owner | employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Manage tenants | W | — | — | — | — | — | — | — |
| Manage users | W | W | R | R | R | R | — | Self |
| SoD rules CRUD | W | W | W | R | R | R | — | — |
| Run Risk Intelligence Engine | W | W | W | W | R | R | — | — |
| Approve requests | W | W | W | W | — | W | — | Delegated |
| Firefighter approve | W | W | W | — | — | — | — | — |
| Risk register | W | W | R | W | R | R | — | — |
| Mitigation controls | W | W | W | W | R | R | — | — |
| Certifications | W | W | R | R | R | W | — | R (own) |
| Audit management | W | W | R | R | R | W | R | — |
| CCM rules | W | W | R | R | R | W | R (own) | — |
| Reports | W | W | W | W | R | W | R (own) | — |
| System settings | W | W | — | — | — | — | — | — |

`W` = Read + Write, `R` = Read only, `—` = No access, `Self` = Own record only.

### 10.3 Custom Role Creation

Custom roles can be created via `POST /api/v1/admin/roles` by a `tenant_admin` or `platform_admin`. A custom role is composed by selecting a base role and adding or removing specific permission scopes:

```json
{
  "role_name": "ap_specialist",
  "display_name": "Accounts Payable Specialist",
  "base_role": "employee",
  "additional_permissions": [
    "access_requests:view_all",
    "risk:view_violations",
    "reports:generate:ap_reports"
  ],
  "removed_permissions": [],
  "description": "AP team members who need visibility into AP-related violations",
  "tenant_id": "acme-corp"
}
```

Custom roles are subject to the same JWT claim embedding as built-in roles. They appear in the approval workflow stage configuration and can be assigned as approver types.

---

*For additional configuration assistance, refer to the [SAP Integration Guide](./10-SAP-Integration-Guide.md), [AI Intelligence Guide](./11-AI-Intelligence-Guide.md), and [Deployment & Operations Guide](./12-Deployment-Operations-Guide.md).*
