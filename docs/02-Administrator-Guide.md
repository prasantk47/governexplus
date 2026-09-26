# GovernexPlus — Platform Administrator Guide

**Version:** 2.0 | **Date:** September 2026 | **Audience:** Platform Administrators | **Classification:** Internal

---

## Table of Contents

1. [Admin Roles & Responsibilities](#1-admin-roles--responsibilities)
2. [Initial Setup](#2-initial-setup)
3. [Tenant Management](#3-tenant-management)
4. [User Management](#4-user-management)
5. [System Configuration](#5-system-configuration)
6. [Connector Setup](#6-connector-setup)
7. [Monitoring & Maintenance](#7-monitoring--maintenance)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Admin Roles & Responsibilities

### 1.1 Role Hierarchy

GovernexPlus has two layers of administrative roles:

**Platform-Level Roles** (cross-tenant, managed by GovernexPlus operations team or your IT department):

| Role | Description | Scope |
|---|---|---|
| `platform_admin` | Full platform access; creates and manages tenants; cross-tenant data access for support | All tenants |
| `platform_support` | Read-only cross-tenant access; cannot modify tenant data | All tenants (read) |
| `platform_billing` | Tenant licensing and usage data access; no operational data | All tenants (billing) |

**Tenant-Level Roles** (scoped to a single tenant, managed by that tenant's admin):

| Role | Description |
|---|---|
| `tenant_admin` | Full access within the tenant; manages users, configuration, connectors |
| `security_admin` | Manages AC pillar: SoD rules, Risk Intelligence Engine, firefighter IDs, certifications |
| `risk_manager` | Full RM pillar access plus read access to AC/PC/AM |
| `process_owner` | PC pillar: controls, testing, sign-off for their process area |
| `auditor` | Full AM pillar; read access to AC/RM/PC data for evidence |
| `approver` | Manages approval inbox; read access to relevant AC data |
| `user` | End user: submit access requests, view own access profile |
| `read_only` | Read-only access to dashboards and reports |

### 1.2 Platform Administrator Responsibilities

As a platform administrator, you are responsible for:

1. **Tenant lifecycle management**: Creating new tenants, configuring modules and limits, suspending or deactivating tenants that violate terms of service or whose licenses expire

2. **Platform health monitoring**: Reviewing system health endpoints, API performance metrics, database size trends, and error rates across all tenants

3. **Security oversight**: Monitoring audit logs for suspicious cross-tenant activity, reviewing failed authentication patterns, ensuring JWT secrets are rotated regularly

4. **Upgrade management**: Applying application updates, running database migrations, coordinating downtime windows with tenants

5. **Connector management**: Managing platform-level connector credentials (SAP system credentials stored at platform level for shared-tenant deployments), validating connector health

6. **Support escalation**: Investigating tenant-reported issues, accessing tenant data for debugging (always logged in audit trail), resetting stuck workflows or locked accounts

7. **Compliance**: Maintaining the platform's own compliance posture — data retention, backup verification, security configuration review

### 1.3 The Golden Rule: Every Cross-Tenant Access is Logged

When a platform administrator accesses any tenant's data, the action is recorded in the immutable audit log with:
- Platform admin's identity
- Target tenant ID
- Action performed
- Timestamp
- Stated reason (mandatory for production data access)

This is enforced at both the middleware layer and the ORM layer. There is no way to access tenant data without generating an audit record.

---

## 2. Initial Setup

### 2.1 Prerequisites

Before deploying GovernexPlus, ensure you have:

- **Docker**: version 24.0 or later
- **Docker Compose**: version 2.20 or later
- **PostgreSQL**: 15 or later (for production; SQLite is used for development)
- **Domain name**: With SSL certificate (Let's Encrypt or commercial CA)
- **SMTP server**: For email notifications
- **Minimum server resources**: 4 vCPU, 8 GB RAM, 100 GB SSD (see Section 9.3 of Product Overview for sizing guidance)

### 2.2 Environment Variables (.env Configuration)

The application is entirely configured via environment variables. Copy the provided `.env.production.example` to `.env` and populate all values before starting the application.

**Critical Variables (required):**

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/governexplus
# For SQLite (development only):
# DATABASE_URL=sqlite+aiosqlite:///./grc_platform.db

# Security — NEVER use the default in production
JWT_SECRET=<generate with: python -c "import secrets; print(secrets.token_hex(64))">
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=60

# Application
APP_ENV=production          # development | staging | production
DEBUG=false
SECRET_KEY=<another 64-byte random hex>

# Initial platform admin (created on first startup)
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=<strong password, min 16 chars>

# CORS (comma-separated list of allowed origins)
CORS_ORIGINS=https://grc.yourdomain.com,https://admin.yourdomain.com
```

**Email Configuration:**

```bash
SMTP_HOST=smtp.yourdomain.com
SMTP_PORT=587
SMTP_USER=grc-notifications@yourdomain.com
SMTP_PASSWORD=<smtp password>
SMTP_FROM=GovernexPlus <grc-notifications@yourdomain.com>
SMTP_TLS=true
SMTP_STARTTLS=true
```

**Optional Configuration:**

```bash
# Rate limiting (requests per minute)
RATE_LIMIT_AUTH=10          # Login/register endpoints
RATE_LIMIT_DEFAULT=60       # All other endpoints

# Session
SESSION_TIMEOUT_MINUTES=60
MAX_CONCURRENT_SESSIONS=3   # Per user
FAILED_LOGIN_LOCKOUT=5      # Number of failed attempts before lockout
LOCKOUT_DURATION_MINUTES=30

# Logging
LOG_LEVEL=INFO              # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT=json             # json | text
LOG_FILE=/var/log/governexplus/app.log
AUDIT_LOG_RETENTION_DAYS=2555   # 7 years

# AI Features
OPENAI_API_KEY=<optional, for AI narrative generation>
AI_MODEL=gpt-4o             # Model to use for AI features
AI_MAX_TOKENS=4096
AI_ENABLED=true

# File Storage
EVIDENCE_STORAGE_PATH=/data/evidence
MAX_UPLOAD_SIZE_MB=50
ALLOWED_UPLOAD_TYPES=pdf,docx,xlsx,png,jpg,jpeg,csv,zip

# Backup
BACKUP_PATH=/data/backups
BACKUP_RETENTION_DAYS=90
```

> **Security Warning**: Never commit the `.env` file to version control. Use a secrets manager (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault) for production credentials.

### 2.3 Database Setup

#### Development (SQLite)

SQLite requires no separate server. Set `DATABASE_URL=sqlite+aiosqlite:///./grc_platform.db` and proceed directly to migrations.

#### Production (PostgreSQL)

1. **Create the database and user:**

```sql
-- Connect as postgres superuser
CREATE DATABASE governexplus ENCODING 'UTF8' LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8';
CREATE USER governexplus_user WITH ENCRYPTED PASSWORD '<strong password>';
GRANT ALL PRIVILEGES ON DATABASE governexplus TO governexplus_user;

-- Grant schema privileges (PostgreSQL 15+)
\c governexplus
GRANT ALL ON SCHEMA public TO governexplus_user;
```

2. **Configure connection pooling** (recommended for production):

```bash
# Add to .env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

3. **Verify connectivity:**

```bash
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine('postgresql+asyncpg://user:password@localhost/governexplus')
async def test():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT 1'))
        print('Connection OK:', result.fetchone())
asyncio.run(test())
"
```

### 2.4 Running Database Migrations (Alembic)

GovernexPlus uses Alembic for database schema management. All migrations must be applied before starting the application.

**Apply all pending migrations:**

```bash
# From the project root directory
alembic upgrade head
```

**Check current migration status:**

```bash
alembic current
```

**View migration history:**

```bash
alembic history --verbose
```

**Rollback one migration (use with extreme caution in production):**

```bash
alembic downgrade -1
```

**Rollback to a specific revision:**

```bash
alembic downgrade <revision_id>
```

> **Important**: Always take a full database backup before running migrations in production. The `downgrade` path is provided for emergency rollback only and may result in data loss if new data was written after the migration being rolled back.

**Expected migration sequence:**

```
20260117_000001_initial_schema           ← Base schema
20260822_121800_add_operations_intel...  ← Operations Intelligence
20260822_183956_add_engine_persist...    ← Engine persistence tables
20260826_100000_add_orchestration...     ← Orchestration + shopping carts
20260903_100000_add_grc_suite_tables     ← Full GRC suite
20260904_120000_add_mfa_columns...       ← MFA support
20260904_150000_xl_a_xl_c_cross_mod...   ← Cross-module integration
```

### 2.5 Seeding Initial Data

After running migrations, seed the platform with initial reference data:

```bash
# Seed all reference data (SoD rules, role templates, framework mappings)
python scripts/seed_all.py

# Seed approver configurations only
python scripts/seed_approvers.py
```

The seed script is **idempotent** — it can be safely re-run without creating duplicates. It uses `INSERT ... ON CONFLICT DO NOTHING` semantics.

**What gets seeded:**

- 128 built-in SoD rules across 12 SAP modules
- Standard role templates (SAP_BASIS, SAP_FIORI, etc.)
- Regulatory framework mappings (SOX, ISO 27001, COBIT)
- Default notification templates
- Default workflow configurations
- Default KRI templates

### 2.6 Creating the First Platform Admin

On first startup, if `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set in `.env`, the application automatically creates the platform admin user. This happens in the FastAPI lifespan startup handler.

If this automatic creation fails or you need to create the admin manually:

```bash
python -c "
import asyncio
from services.auth_service import AuthService
from db.session import get_db

async def create_admin():
    async for db in get_db():
        service = AuthService(db)
        user = await service.create_user(
            email='admin@yourdomain.com',
            password='<strong_password>',
            full_name='Platform Administrator',
            roles=['platform_admin'],
            tenant_id='platform'
        )
        print(f'Created admin: {user.id}')
        break

asyncio.run(create_admin())
"
```

### 2.7 Starting the Application

**Development:**

```bash
# Backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

**Production (Docker Compose):**

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f api

# Check health
curl https://grc.yourdomain.com/health
```

**Verify startup:**

```bash
# API health check
curl http://localhost:8000/health
# Expected: {"status": "healthy", "version": "2.0.0", "db": "connected"}

# API docs (development only)
open http://localhost:8000/docs
```

---

## 3. Tenant Management

### 3.1 Tenant Data Model

Each tenant record contains:

```
Tenant
├── id (UUID)
├── name (display name)
├── slug (URL-safe identifier, e.g., "acme-corp")
├── plan (starter | professional | enterprise)
├── status (active | suspended | trial | cancelled)
├── configuration
│   ├── timezone
│   ├── locale (en | ar)
│   ├── date_format
│   └── fiscal_year_start_month
├── modules (ac | rm | pc | am — enabled modules)
├── features (sso | ai | analytics | advanced_reporting)
├── limits
│   ├── max_users
│   ├── max_systems
│   ├── max_api_calls_per_day
│   └── max_storage_gb
└── contacts
    ├── primary_contact_email
    ├── billing_contact_email
    └── technical_contact_email
```

### 3.2 Creating a New Tenant

**Via Admin UI:**

1. Log in to GovernexPlus with a `platform_admin` account
2. Navigate to **Admin → Tenant Management**
3. Click **New Tenant**
4. Complete the onboarding wizard:
   - **Step 1 — Basic Info**: Tenant name, slug, plan tier, primary contact
   - **Step 2 — Configuration**: Timezone, locale, fiscal year settings
   - **Step 3 — Modules**: Enable/disable the four GRC pillars
   - **Step 4 — Limits**: Set user count, system count, API call quotas
   - **Step 5 — Features**: Enable SSO, AI, advanced analytics as licensed
   - **Step 6 — Initial Admin**: Create the tenant's first `tenant_admin` user
5. Click **Create Tenant**

[Screenshot: Tenant Onboarding Wizard Step 1 — Basic Information form]

**Via API (for automated provisioning):**

```bash
curl -X POST https://grc.yourdomain.com/api/admin/tenants \
  -H "Authorization: Bearer <platform_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ACME Corporation",
    "slug": "acme-corp",
    "plan": "enterprise",
    "configuration": {
      "timezone": "America/New_York",
      "locale": "en",
      "fiscal_year_start_month": 1
    },
    "modules": ["ac", "rm", "pc", "am"],
    "features": ["sso", "ai", "analytics"],
    "limits": {
      "max_users": 500,
      "max_systems": 20,
      "max_api_calls_per_day": 10000
    },
    "primary_contact_email": "grc-admin@acme.com"
  }'
```

### 3.3 Tenant Configuration

After creation, tenant configuration can be modified at any time by either a `platform_admin` or the tenant's `tenant_admin`.

**Key configuration settings:**

**Timezone and Locale:**
- Affects all date/time display and report generation
- Affects email notification delivery timing (e.g., "daily digest at 8am" uses tenant timezone)
- Arabic locale enables RTL layout for all tenant users

**Fiscal Year:**
- Sets the fiscal year boundary for period-based reports
- Affects SOX sign-off period labeling
- Risk assessment "periods" align to fiscal year quarters

**Module Enablement:**
- Modules can be enabled or disabled per tenant without data loss
- Disabling a module hides the UI and blocks API endpoints for that module
- Module-specific data is retained even when module is disabled (for future re-enablement)

**Session and Security Settings (tenant-level overrides):**

```bash
# Tenant admins can configure:
SESSION_TIMEOUT_MINUTES=30      # Override default (shorter = more secure)
REQUIRE_MFA=true                # Mandate MFA for all tenant users
PASSWORD_MIN_LENGTH=14          # Stricter than platform default
PASSWORD_COMPLEXITY=high        # Require uppercase, lowercase, number, symbol
LOGIN_HOURS_RESTRICTION=true    # Restrict login to business hours
LOGIN_HOURS_START=08:00
LOGIN_HOURS_END=18:00
LOGIN_HOURS_TIMEZONE=America/New_York
```

### 3.4 Tenant Limits

Limits protect platform resources and enforce licensing:

| Limit | Description | Action When Exceeded |
|---|---|---|
| `max_users` | Maximum active user accounts | New user creation fails; admin notified |
| `max_systems` | Maximum connected SAP/target systems | New system connection fails; admin notified |
| `max_api_calls_per_day` | Daily API call budget | 429 Too Many Requests after limit; resets at midnight UTC |
| `max_storage_gb` | Evidence and document storage | Upload fails; admin notified |

**Checking tenant usage:**

```bash
curl -X GET https://grc.yourdomain.com/api/admin/tenants/acme-corp/usage \
  -H "Authorization: Bearer <platform_admin_token>"
```

Response:
```json
{
  "tenant_id": "acme-corp",
  "users": {"current": 287, "limit": 500},
  "systems": {"current": 5, "limit": 20},
  "api_calls_today": {"current": 4231, "limit": 10000},
  "storage_gb": {"current": 12.4, "limit": 100}
}
```

**Adjusting limits (requires platform_admin):**

```bash
curl -X PATCH https://grc.yourdomain.com/api/admin/tenants/acme-corp \
  -H "Authorization: Bearer <platform_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"limits": {"max_users": 750}}'
```

### 3.5 Tenant Features

Features are premium capabilities that can be enabled per tenant:

| Feature Key | Description |
|---|---|
| `sso` | SAML 2.0 / OAuth 2.0 SSO integration |
| `ai` | AI assistance features (GRC Assistant, Remediation Advisor) |
| `analytics` | Advanced analytics (custom dashboards, drill-down reporting) |
| `advanced_reporting` | PPTX/PDF board reports, committee dashboards |
| `api_access` | Direct API access (for integration/automation use cases) |
| `migration_copilot` | SAP GRC AC 12.0 migration assistance |
| `digital_twin` | Risk simulation / what-if analysis |

### 3.6 Suspending and Activating Tenants

**Suspend a tenant** (blocks all logins and API access, data preserved):

```bash
curl -X POST https://grc.yourdomain.com/api/admin/tenants/acme-corp/suspend \
  -H "Authorization: Bearer <platform_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"reason": "License payment overdue - 30 days", "notify_contacts": true}'
```

Effects of suspension:
- All user login attempts return `403 Tenant Suspended`
- All API calls return `403 Tenant Suspended`
- Scheduled jobs (certification sweeps, CCM rules) are paused
- Notification delivery is paused
- Data is fully preserved and immediately accessible upon reactivation

**Reactivate a tenant:**

```bash
curl -X POST https://grc.yourdomain.com/api/admin/tenants/acme-corp/activate \
  -H "Authorization: Bearer <platform_admin_token>"
```

**Delete a tenant** (permanent, irreversible — requires confirmation):

```bash
curl -X DELETE https://grc.yourdomain.com/api/admin/tenants/acme-corp \
  -H "Authorization: Bearer <platform_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"confirmation": "DELETE acme-corp", "reason": "Customer offboarded"}'
```

> **Warning**: Tenant deletion is irreversible and removes all tenant data. Ensure data export has been completed and confirmed by the tenant before proceeding.

---

## 4. User Management

### 4.1 Creating Users

**Via Admin UI (tenant_admin):**

1. Navigate to **Admin → Users → New User**
2. Complete the form:
   - Full name
   - Email address (used as login username)
   - Department and manager (from org hierarchy)
   - Roles to assign
   - Temporary password (user must change on first login)
   - Send welcome email (checkbox)
3. Click **Create User**

[Screenshot: Create User form with role assignment dropdown and temporary password option]

**Via API:**

```bash
curl -X POST https://grc.yourdomain.com/api/users \
  -H "Authorization: Bearer <admin_token>" \
  -H "X-Tenant-ID: acme-corp" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane.smith@acme.com",
    "full_name": "Jane Smith",
    "department": "Finance",
    "manager_user_id": "user_manager_id",
    "roles": ["approver", "risk_manager"],
    "temp_password": "Welcome2026!",
    "force_password_change": true,
    "send_welcome_email": true
  }'
```

**Bulk User Import (CSV):**

For large user populations, use the bulk import endpoint:

```bash
curl -X POST https://grc.yourdomain.com/api/admin/users/import \
  -H "Authorization: Bearer <admin_token>" \
  -F "file=@users.csv" \
  -F "send_welcome_emails=true"
```

CSV format:
```csv
email,full_name,department,manager_email,roles
jane.smith@acme.com,Jane Smith,Finance,john.doe@acme.com,"approver,risk_manager"
```

### 4.2 Password Policies

Password policy is configurable per tenant:

| Setting | Default | Recommended Production |
|---|---|---|
| Minimum length | 12 | 14+ |
| Maximum length | 128 | 128 |
| Uppercase required | Yes | Yes |
| Lowercase required | Yes | Yes |
| Number required | Yes | Yes |
| Symbol required | No | Yes |
| Password history | 10 | 24 |
| Max age (days) | 90 | 90 |
| Min age (days) | 1 | 1 |
| Common password check | Yes | Yes |
| Username similarity check | Yes | Yes |

**Configuring password policy (tenant_admin):**

Navigate to **Admin → Security → Password Policy** and adjust settings.

Or via API:

```bash
curl -X PUT https://grc.yourdomain.com/api/admin/security/password-policy \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "min_length": 14,
    "require_uppercase": true,
    "require_lowercase": true,
    "require_number": true,
    "require_symbol": true,
    "history_count": 24,
    "max_age_days": 90
  }'
```

### 4.3 MFA Setup (TOTP)

**For individual users (self-service):**

1. Log in to GovernexPlus
2. Navigate to **Profile → Security**
3. Click **Set Up MFA**
4. Scan the QR code with an authenticator app (Google Authenticator, Microsoft Authenticator, Authy)
5. Enter the 6-digit TOTP code to confirm setup
6. Save the backup codes in a secure location

[Screenshot: MFA Setup page with QR code and backup codes panel]

**Mandating MFA for all tenant users:**

```bash
curl -X PUT https://grc.yourdomain.com/api/admin/security/mfa-policy \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "require_mfa": true,
    "grace_period_days": 7,
    "enforcement_date": "2026-10-01",
    "notify_users": true
  }'
```

When `require_mfa` is enabled with a grace period, users without MFA enrolled are shown a prompt to set it up but can still log in during the grace period. After the enforcement date, users without MFA cannot log in.

**Admin-resetting MFA for a locked-out user:**

```bash
curl -X POST https://grc.yourdomain.com/api/admin/users/user_id/mfa/reset \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"reason": "User lost authenticator app, identity verified via video call"}'
```

This action is logged to the audit trail with the stated reason.

### 4.4 Role Assignment

**Assigning roles to a user:**

```bash
curl -X PUT https://grc.yourdomain.com/api/users/user_id/roles \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "roles": ["security_admin", "approver"],
    "effective_from": "2026-09-01",
    "effective_to": null,
    "reason": "Promoted to SAP Security team lead"
  }'
```

**Role assignment considerations:**

- Users can hold multiple roles; permissions are additive (union of all role permissions)
- Role assignments can be time-limited (set `effective_to` for temporary roles)
- All role changes are logged to the audit trail
- Changing a user's roles does not invalidate existing sessions — new permissions take effect on next login (or next token refresh if using refresh tokens)

**Role descriptions for assignment:**

| Role | Appropriate For |
|---|---|
| `tenant_admin` | IT/GRC team lead managing the platform configuration |
| `security_admin` | SAP Security analyst with full AC pillar access |
| `risk_manager` | Risk management function lead |
| `process_owner` | Business process owner responsible for controls |
| `auditor` | Internal audit team member |
| `approver` | Manager or role owner who approves access requests |
| `user` | Any employee who needs to submit access requests |
| `read_only` | Executive stakeholder who needs dashboard access only |

### 4.5 Account Lockout & Unlock

**Lockout behavior:**

After the configured number of failed login attempts (default: 5), the account is locked. The user receives an email notification. The lockout duration is configurable (default: 30 minutes auto-unlock; alternatively, require admin unlock).

**Admin-unlocking an account:**

Via UI: **Admin → Users → Find User → Unlock Account**

Via API:
```bash
curl -X POST https://grc.yourdomain.com/api/admin/users/user_id/unlock \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"reason": "User called helpdesk, identity verified"}'
```

**Viewing locked accounts:**

```bash
curl -X GET "https://grc.yourdomain.com/api/admin/users?status=locked" \
  -H "Authorization: Bearer <admin_token>"
```

**Force-logout all sessions for a user (security incident response):**

```bash
curl -X POST https://grc.yourdomain.com/api/admin/users/user_id/logout-all \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Suspected account compromise"}'
```

This blacklists all existing tokens for the user, invalidating all active sessions immediately.

### 4.6 User Deactivation vs. Deletion

**Deactivate** (preferred for departed employees — preserves audit history):

```bash
curl -X POST https://grc.yourdomain.com/api/users/user_id/deactivate \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Employee terminated 2026-08-31", "revoke_access": true}'
```

Effects:
- User cannot log in
- All active sessions invalidated
- User's approval workflows reassigned to manager
- Access requests pending the user's approval escalated
- Firefighter ID assignments transferred to backup owner
- User's data preserved for audit trail (access history, approval decisions, etc.)

**Delete** (use only if the user record itself must be removed — rare):

Requires `platform_admin` role and explicit confirmation. Generates audit log entry. Preserves audit trail records by replacing user reference with anonymized identifier.

---

## 5. System Configuration

### 5.1 CORS Origins

CORS (Cross-Origin Resource Sharing) restricts which browser origins can make API calls. Misconfiguration is a security risk.

**Correct configuration:**

```bash
# .env
CORS_ORIGINS=https://grc.yourdomain.com,https://grc-admin.yourdomain.com
```

**What NOT to do:**

```bash
# NEVER set this in production — allows any origin
CORS_ORIGINS=*
```

**Multiple origin support for development:**

```bash
# Development only
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://staging.yourdomain.com
```

The middleware also supports the `CORS_ALLOW_CREDENTIALS=true` setting (required for cookie-based auth) and `CORS_ALLOW_HEADERS` for custom headers.

### 5.2 Rate Limiting

Rate limiting is implemented using slowapi (Starlette-compatible ratelimit middleware).

**Default limits:**

| Endpoint Category | Limit | Rationale |
|---|---|---|
| `/auth/login` | 10 / minute | Prevent brute force |
| `/auth/register` | 5 / minute | Prevent account spam |
| `/auth/forgot-password` | 5 / minute | Prevent email spam |
| All other endpoints | 60 / minute | General protection |

**Adjusting limits:**

```bash
# .env
RATE_LIMIT_AUTH=10
RATE_LIMIT_DEFAULT=60
RATE_LIMIT_ANALYSIS=20      # Risk Intelligence Engine and complex analysis endpoints
RATE_LIMIT_EXPORT=10        # PDF/Excel export endpoints
```

**Rate limit headers returned to clients:**

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1725624060
```

When a client exceeds the limit, the API returns `429 Too Many Requests` with a `Retry-After` header.

**Exempting internal service accounts from rate limiting:**

```bash
RATE_LIMIT_EXEMPT_IPS=10.0.0.0/8,172.16.0.0/12   # Internal networks
RATE_LIMIT_EXEMPT_API_KEYS=<internal_service_key>
```

### 5.3 JWT Secret Management

The JWT secret is the most sensitive configuration value. Any party with the JWT secret can forge valid tokens and impersonate any user.

**Best practices:**

1. **Generate a strong secret**: minimum 512 bits (64 bytes hex)

   ```bash
   python -c "import secrets; print(secrets.token_hex(64))"
   ```

2. **Rotate the secret regularly**: Every 90 days, or immediately after a suspected compromise

3. **Rotation procedure** (minimizes disruption):
   - Set `JWT_SECRET_NEW=<new secret>` in addition to `JWT_SECRET=<old secret>`
   - Restart application instances one at a time (rolling restart)
   - Application accepts tokens signed with either secret during rotation window
   - After all users have re-authenticated (typically 24-48 hours), remove `JWT_SECRET` and rename `JWT_SECRET_NEW` to `JWT_SECRET`
   - Force-logout all users if immediate rotation is required: `POST /api/admin/security/rotate-jwt?force=true`

4. **Use a secrets manager**: Never store the JWT secret in the `.env` file on disk in production. Use:
   - AWS Secrets Manager: `JWT_SECRET=$AWS_SECRET_ARN:jwt_secret`
   - Azure Key Vault: `JWT_SECRET=@azurekeyvault:<vault-name>/<secret-name>`
   - HashiCorp Vault: Inject at container start via Vault Agent

### 5.4 Session Timeout

Session timeout is enforced by JWT token expiry. The default access token lifetime is 60 minutes.

**Configuration:**

```bash
JWT_EXPIRY_MINUTES=60           # Access token lifetime
REFRESH_TOKEN_EXPIRY_DAYS=7    # Refresh token lifetime (if using refresh tokens)
SESSION_IDLE_TIMEOUT_MINUTES=30 # Frontend inactivity timeout (separate from JWT)
```

The frontend enforces an idle timeout independently of the JWT expiry — if a user is inactive for `SESSION_IDLE_TIMEOUT_MINUTES`, they are shown a "session about to expire" warning and then redirected to login.

### 5.5 Logging Configuration

GovernexPlus produces two types of logs:

**Application Logs** (operational):

```bash
LOG_LEVEL=INFO                  # DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_FORMAT=json                 # json (structured) | text (human-readable)
LOG_FILE=/var/log/governexplus/app.log
LOG_ROTATION=daily              # none | daily | size
LOG_RETENTION_DAYS=30           # How long to keep rotated logs
```

JSON log format (recommended for log aggregation tools):
```json
{
  "timestamp": "2026-09-06T14:23:01.234Z",
  "level": "INFO",
  "logger": "api.routers.access_requests",
  "message": "Access request submitted",
  "request_id": "req_abc123",
  "tenant_id": "acme-corp",
  "user_id": "user_456",
  "duration_ms": 142
}
```

**Audit Logs** (compliance):

Audit logs are separate from application logs and are always written in JSON format to both the database (for querying) and optionally to a file or SIEM.

```bash
AUDIT_LOG_DB=true               # Write to database (always enabled)
AUDIT_LOG_FILE=/var/log/governexplus/audit.log   # Optional file mirror
AUDIT_LOG_SIEM=syslog           # syslog | splunk | sentinel | none
AUDIT_SIEM_HOST=splunk.yourdomain.com
AUDIT_SIEM_PORT=514
```

---

## 6. Connector Setup

### 6.1 SAP RFC Connector

The SAP RFC connector enables direct read/write operations to SAP systems via the RFC protocol.

**Prerequisites:**
- SAP system reachable from the GovernexPlus server (network connectivity)
- RFC-enabled SAP user with the following authorizations:
  - `S_RFC`: RFC access (function group SUSO, SUSR, etc.)
  - `S_USER_GRP`: User maintenance authorization
  - `S_USER_AGR`: Role assignment authorization
  - `P_ABAP`: ABAP program execution (for log extraction)

**Required SAP user authorizations (minimum):**

```
Authorization Object: S_RFC
  ACTVT = 16 (Execute)
  RFC_NAME = SUSR* (User management function groups)

Authorization Object: S_USER_GRP
  ACTVT = 03 (Display)
  CLASS = * (All user groups)

Authorization Object: S_USER_AGR
  ACTVT = 03, 22 (Display, Assign)
  ACT_GROUP = * (All roles)
```

**Configuring the SAP connection in GovernexPlus:**

1. Navigate to **Admin → Connectors → SAP Systems → Add System**
2. Complete the connection form:

| Field | Example | Description |
|---|---|---|
| System ID | PRD | SAP System ID (SID) |
| Display Name | SAP S/4HANA Production | Human-readable name |
| Application Server | sap-prd-app01.acme.com | FQDN or IP |
| System Number | 00 | SAP instance number |
| Client | 100 | SAP client |
| RFC User | GOVERNEX_RFC | Dedicated RFC user in SAP |
| RFC Password | (stored encrypted) | RFC user password |
| Language | EN | Logon language |
| Environment | Production | Production / Test / Development |

3. Click **Test Connection** to verify

[Screenshot: SAP System connection form with test connection result panel]

**Connection string format (for `.env` configuration):**

```bash
SAP_SYSTEMS='[
  {
    "sid": "PRD",
    "name": "SAP S/4HANA Production",
    "ashost": "sap-prd-app01.acme.com",
    "sysnr": "00",
    "client": "100",
    "user": "GOVERNEX_RFC",
    "password": "<encrypted>",
    "lang": "EN"
  }
]'
```

**Mock connector (development/testing):**

If no SAP system is available, the mock connector provides realistic simulated data:

```bash
SAP_CONNECTOR_MODE=mock         # real | mock
SAP_MOCK_USER_COUNT=500         # Number of simulated users
SAP_MOCK_ROLE_COUNT=200         # Number of simulated roles
SAP_MOCK_VIOLATION_RATE=0.15    # 15% of users have violations
```

### 6.2 Azure AD App Registration

**Step 1: Register the application in Azure AD:**

1. Log in to Azure Portal → Azure Active Directory → App Registrations
2. Click **New Registration**:
   - Name: `GovernexPlus`
   - Supported account types: `Accounts in this organizational directory only`
   - Redirect URI (Web): `https://grc.yourdomain.com/auth/callback/azure`
3. After creation, note the **Application (client) ID** and **Directory (tenant) ID**

**Step 2: Create a client secret:**

1. Go to **Certificates & Secrets → New Client Secret**
2. Set expiry to 24 months
3. Copy the **Value** immediately (shown only once)

**Step 3: Grant API permissions:**

Required Microsoft Graph permissions:

| Permission | Type | Purpose |
|---|---|---|
| `User.Read.All` | Application | Read all user profiles |
| `Group.Read.All` | Application | Read group memberships |
| `AuditLog.Read.All` | Application | Read sign-in logs |
| `Directory.Read.All` | Application | Read organizational data |

Grant admin consent for all permissions.

**Step 4: Configure in GovernexPlus:**

```bash
AZURE_AD_TENANT_ID=<directory-tenant-id>
AZURE_AD_CLIENT_ID=<application-client-id>
AZURE_AD_CLIENT_SECRET=<client-secret-value>
AZURE_AD_ENABLED=true
AZURE_AD_SYNC_GROUPS=true
AZURE_AD_SYNC_INTERVAL_MINUTES=60
```

**Testing the connection:**

```bash
curl -X POST https://grc.yourdomain.com/api/connectors/azure-ad/test \
  -H "Authorization: Bearer <admin_token>"
```

### 6.3 Workday Integration

**Prerequisites:**
- Workday Integration System User (ISU) account
- Workday Integration Security Group with permissions for:
  - Worker data (Get Workers, Put Workers)
  - Organizational data (Get Organizations)
  - Security data (if using Workday for access governance)

**REST API configuration:**

```bash
WORKDAY_BASE_URL=https://wd2-impl-services1.workday.com/ccx/api/v1/<tenant>
WORKDAY_CLIENT_ID=<OAuth client ID>
WORKDAY_CLIENT_SECRET=<OAuth client secret>
WORKDAY_USERNAME=<ISU username>
WORKDAY_PASSWORD=<ISU password>
WORKDAY_ENABLED=true
WORKDAY_SYNC_INTERVAL_MINUTES=15
```

**Event subscriptions (for real-time JML triggers):**

Configure a Workday Studio integration to POST lifecycle events to:
```
https://grc.yourdomain.com/api/connectors/workday/events
```

Supported event types:
- `worker.hired` → Triggers joiner workflow
- `worker.transferred` → Triggers mover workflow
- `worker.terminated` → Triggers leaver workflow (access revocation)

### 6.4 SuccessFactors Integration

```bash
SF_API_URL=https://api4.successfactors.com
SF_COMPANY_ID=<company ID>
SF_API_KEY=<API key>
SF_USERNAME=<API user>
SF_PASSWORD=<API password>
SF_ENABLED=true
SF_SYNC_INTERVAL_MINUTES=30
```

**Event subscription:**

SuccessFactors sends employee change events via intelligent services. Configure the GovernexPlus webhook URL in the SuccessFactors Integration Center:
```
https://grc.yourdomain.com/api/connectors/successfactors/events
```

### 6.5 Testing All Connectors

**Bulk connector health check:**

```bash
curl -X GET https://grc.yourdomain.com/api/connectors/health \
  -H "Authorization: Bearer <admin_token>"
```

Response:
```json
{
  "connectors": [
    {"name": "SAP PRD", "type": "sap_rfc", "status": "connected", "last_sync": "2026-09-06T14:00:00Z"},
    {"name": "Azure AD", "type": "azure_ad", "status": "connected", "last_sync": "2026-09-06T14:15:00Z"},
    {"name": "Workday", "type": "workday", "status": "error", "error": "Authentication failed", "last_sync": "2026-09-06T13:45:00Z"}
  ]
}
```

---

## 7. Monitoring & Maintenance

### 7.1 Health Check Endpoints

GovernexPlus exposes standard health check endpoints for monitoring systems:

**Simple health check (load balancer probe):**

```
GET /health
Response: {"status": "healthy", "version": "2.0.0"}
HTTP 200 = healthy, HTTP 503 = unhealthy
```

**Detailed health check (monitoring systems):**

```
GET /health/detailed
Authorization: Bearer <monitoring_token>

Response:
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2026-09-06T14:23:01Z",
  "components": {
    "database": {"status": "healthy", "latency_ms": 12},
    "cache": {"status": "healthy", "latency_ms": 3},
    "scheduler": {"status": "running", "next_run": "2026-09-06T15:00:00Z"},
    "connectors": {
      "sap_prd": {"status": "connected"},
      "azure_ad": {"status": "connected"}
    }
  },
  "metrics": {
    "active_tenants": 47,
    "requests_last_hour": 12453,
    "avg_response_ms": 145,
    "error_rate_percent": 0.02
  }
}
```

**Readiness probe (Kubernetes):**
```
GET /health/ready
HTTP 200 = ready to serve traffic, HTTP 503 = not ready
```

**Liveness probe (Kubernetes):**
```
GET /health/alive
HTTP 200 = process is alive
```

### 7.2 Audit Log Review

**Searching audit logs via UI:**

Navigate to **Admin → Audit Logs** and filter by:
- Date range
- Tenant
- User
- Action type
- Resource type
- IP address
- Result (success / failure)

[Screenshot: Audit Log search interface with filter panel and results table]

**Audit log API queries:**

```bash
# Get all admin actions in the last 24 hours
curl -X GET "https://grc.yourdomain.com/api/audit?action_prefix=admin.&hours=24" \
  -H "Authorization: Bearer <admin_token>"

# Get all cross-tenant access by platform admins
curl -X GET "https://grc.yourdomain.com/api/audit?action=cross_tenant_access&limit=100" \
  -H "Authorization: Bearer <admin_token>"

# Get all failed login attempts in the last hour
curl -X GET "https://grc.yourdomain.com/api/audit?action=auth.login.failed&hours=1" \
  -H "Authorization: Bearer <admin_token>"
```

**High-priority audit events to monitor daily:**

| Event | What to Check |
|---|---|
| `auth.login.failed` | Bursts of failures from single IP = brute force attempt |
| `admin.cross_tenant_access` | All entries — should match known support tickets |
| `security.jwt_secret_rotation` | Confirm expected, with reason |
| `user.role.assigned` | `platform_admin` role granted — should be very rare |
| `tenant.suspended` / `tenant.deleted` | Always verify authorization |
| `connector.test.failed` | Credential expiry or network change |
| `mfa.reset` | Admin-reset MFA — verify user identity was verified |

### 7.3 Database Backup & Restore

**Automated backup (PostgreSQL):**

Configure daily automated backups using `pg_dump`:

```bash
# /etc/cron.d/governexplus-backup
0 2 * * * postgres pg_dump -Fc governexplus > /data/backups/governexplus_$(date +%Y%m%d).dump
# Retain 90 days
0 3 * * * find /data/backups -name "*.dump" -mtime +90 -delete
```

Or use the built-in backup trigger:

```bash
curl -X POST https://grc.yourdomain.com/api/admin/maintenance/backup \
  -H "Authorization: Bearer <platform_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"type": "full", "destination": "s3://your-bucket/backups/"}'
```

**Verifying backup integrity:**

```bash
# Restore to test database and verify row counts
pg_restore -d governexplus_test /data/backups/governexplus_20260906.dump
psql -d governexplus_test -c "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 20;"
```

**Restore procedure (disaster recovery):**

1. Provision new database server (PostgreSQL 15+)
2. Create database and user (same as initial setup)
3. Restore backup: `pg_restore -d governexplus /data/backups/latest.dump`
4. Verify row counts and recent data timestamps
5. Update `DATABASE_URL` in `.env` to point to new server
6. Restart application

**Target recovery metrics:**
- Recovery Time Objective (RTO): 2 hours
- Recovery Point Objective (RPO): 24 hours (daily backup), or near-zero with streaming replication

### 7.4 Log Rotation

Configure log rotation for application logs:

```bash
# /etc/logrotate.d/governexplus
/var/log/governexplus/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    postrotate
        docker kill -s HUP governexplus_api 2>/dev/null || true
    endscript
}
```

### 7.5 Performance Monitoring

**Key metrics to monitor:**

| Metric | Warning Threshold | Critical Threshold |
|---|---|---|
| API response time (p95) | >500ms | >2000ms |
| Database query time (p95) | >100ms | >500ms |
| Risk Intelligence Engine analysis duration | >5 min (full run) | >30 min |
| Error rate | >0.1% | >1% |
| Database connection pool utilization | >70% | >90% |
| Disk usage (database) | >70% | >85% |
| Memory usage | >80% | >90% |

**Prometheus metrics endpoint (optional):**

```bash
METRICS_ENABLED=true
METRICS_PATH=/metrics
METRICS_AUTH_TOKEN=<prometheus-scrape-token>
```

```yaml
# prometheus.yml scrape config
- job_name: 'governexplus'
  bearer_token: '<metrics-auth-token>'
  static_configs:
    - targets: ['grc.yourdomain.com:8000']
  metrics_path: /metrics
```

**Grafana dashboard:**

Import the GovernexPlus Grafana dashboard template from `docs/grafana-dashboard.json`. Provides visualizations for:
- Request rate and error rate
- Response time percentiles
- Active users by tenant
- Risk Intelligence Engine analysis queue depth
- Database performance
- Connector health status

### 7.6 Applying Updates

**Patch updates (no schema changes):**

```bash
# Pull new images
docker-compose -f docker-compose.prod.yml pull

# Rolling restart (zero downtime with multiple replicas)
docker-compose -f docker-compose.prod.yml up -d --no-deps api

# Verify
curl https://grc.yourdomain.com/health
```

**Minor/major updates (with schema changes):**

1. Put the application in maintenance mode: `POST /api/admin/maintenance/enable`
2. Take database backup
3. Pull new application image
4. Run migrations: `alembic upgrade head`
5. Restart application
6. Disable maintenance mode: `POST /api/admin/maintenance/disable`
7. Run smoke tests

**Maintenance mode:**

When maintenance mode is enabled:
- All non-admin API calls return `503 Service Temporarily Unavailable`
- Admin endpoints remain accessible
- A configurable maintenance message is displayed to users

---

## 8. Troubleshooting

### 8.1 Common Issues & Solutions

#### Problem: Application fails to start — "JWT_SECRET not set"

**Symptom:** Application exits on startup with `ValueError: JWT_SECRET must be set in production`

**Cause:** `APP_ENV=production` is set but `JWT_SECRET` is not in the environment.

**Solution:**
```bash
# Generate and set JWT_SECRET
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(64))")
# Or add to .env file
echo "JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(64))")" >> .env
```

#### Problem: Alembic migration fails — "relation already exists"

**Symptom:** `alembic upgrade head` fails with `ProgrammingError: relation "users" already exists`

**Cause:** Database was partially initialized (e.g., via SQLAlchemy `create_all`) before Alembic was configured.

**Solution:**
```bash
# Stamp the database at the initial revision without running the migration
alembic stamp 20260117_000001_initial_schema
# Then run remaining migrations
alembic upgrade head
```

#### Problem: Tenant users cannot log in — "Tenant suspended"

**Symptom:** All users of a specific tenant receive 403 with `{"detail": "Tenant suspended"}`

**Cause:** Tenant was suspended (intentionally or incorrectly).

**Solution:**
```bash
# Check tenant status
curl -X GET https://grc.yourdomain.com/api/admin/tenants/tenant-slug \
  -H "Authorization: Bearer <platform_admin_token>"

# Reactivate if suspension was in error
curl -X POST https://grc.yourdomain.com/api/admin/tenants/tenant-slug/activate \
  -H "Authorization: Bearer <platform_admin_token>"
```

#### Problem: SAP connector returns "RFC_ERROR_SYSTEM_FAILURE"

**Symptom:** SAP system connection test fails with RFC error

**Common causes and solutions:**

| Cause | Diagnostic | Solution |
|---|---|---|
| Network connectivity | `telnet sap-host 3300` | Open firewall rule for SAP port |
| Wrong system number | Check SAP instance list | Verify `sysnr` parameter |
| RFC user locked | Check SM04 in SAP | Unlock user in SAP (SU01) |
| Missing RFC authorization | Check SU53 in SAP | Add `S_RFC` authorization |
| SAP system down | Check SM50 in SAP | Wait for SAP to restart |

#### Problem: Risk Intelligence Engine analysis takes too long

**Symptom:** Full landscape Risk Intelligence Engine analysis runs >30 minutes

**Solutions:**

1. **Reduce batch size:**
   ```bash
   ARA_BATCH_SIZE=100    # Process 100 users at a time (default: 500)
   ARA_BATCH_DELAY=0.1   # 100ms delay between batches to reduce DB load
   ```

2. **Enable parallel processing:**
   ```bash
   ARA_WORKERS=4         # Number of parallel analysis workers
   ```

3. **Optimize database:** Run `ANALYZE` and `VACUUM` on the database:
   ```sql
   VACUUM ANALYZE users, roles, user_roles, risk_violations;
   ```

4. **Add database indexes:** Check that all foreign keys are indexed (see migration scripts for index definitions)

#### Problem: Email notifications not being delivered

**Symptom:** Users not receiving notification emails

**Diagnostic steps:**
1. Check SMTP configuration in `.env`
2. Test SMTP directly:
   ```bash
   python -c "
   import smtplib
   from email.mime.text import MIMEText
   msg = MIMEText('Test')
   msg['Subject'] = 'Test'
   msg['From'] = 'test@domain.com'
   msg['To'] = 'your-email@domain.com'
   with smtplib.SMTP('smtp.host', 587) as s:
       s.starttls()
       s.login('user', 'pass')
       s.send_message(msg)
   print('Sent successfully')
   "
   ```
3. Check notification delivery log: `GET /api/admin/notifications/delivery-log`
4. Verify email isn't in spam (check SPF/DKIM configuration for your domain)

#### Problem: Rate limit errors during batch operations

**Symptom:** API integration returns `429 Too Many Requests` frequently

**Solution:** Use API keys with elevated rate limits for integration service accounts:

```bash
curl -X POST https://grc.yourdomain.com/api/admin/api-keys \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Integration Service Account",
    "rate_limit_multiplier": 10,
    "allowed_ips": ["10.0.0.0/8"],
    "expiry_days": 365
  }'
```

#### Problem: Audit log fills disk

**Symptom:** Disk usage growing rapidly, audit log is the largest consumer

**Solution:**
1. Configure log rotation (Section 7.4)
2. Archive old audit logs to object storage:
   ```bash
   curl -X POST https://grc.yourdomain.com/api/admin/audit/archive \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{"before_date": "2025-01-01", "destination": "s3://bucket/audit-archive/"}'
   ```
3. Increase disk allocation or migrate to PostgreSQL table partitioning

### 8.2 Accessing Application Logs in Docker

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# API only, last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 api

# Filter for errors
docker-compose -f docker-compose.prod.yml logs api 2>&1 | grep -i error

# Follow and filter
docker-compose -f docker-compose.prod.yml logs -f api | grep -v "GET /health"
```

### 8.3 Database Diagnostics

```bash
# Connect to PostgreSQL
psql -U governexplus_user -d governexplus

# Check slow queries
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;

# Check table sizes
SELECT schemaname, tablename,
       pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_relation_size(schemaname||'.'||tablename) DESC;

# Check connection pool utilization
SELECT count(*), state FROM pg_stat_activity GROUP BY state;

# Check for long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND (now() - pg_stat_activity.query_start) > interval '5 minutes';
```

### 8.4 Getting Support

For issues not resolved by this guide:

1. **Check the knowledge base**: docs.governexplus.io/kb
2. **Search known issues**: github.com/governexplus/platform/issues
3. **Submit a support ticket**: support.governexplus.io (include tenant ID, timestamp of issue, and relevant log excerpts)
4. **Emergency support** (platform down, data integrity concern): support-emergency@governexplus.io — 24/7 response SLA

When submitting a support ticket, always include:
- GovernexPlus version (`GET /health` → version field)
- Deployment type (SaaS / on-premise / hybrid)
- Affected tenant ID(s)
- Approximate time of issue occurrence
- Steps to reproduce
- Relevant log excerpts (sanitize sensitive data)
- What you have already tried

---

*This guide is maintained by the GovernexPlus Platform Engineering team. For corrections or additions, contact platform-docs@governexplus.io*

*Last updated: September 2026 | Version 2.0*
