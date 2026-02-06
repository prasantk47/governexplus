# Governex+ Platform Documentation

## Overview

Governex+ is an enterprise-grade Governance, Risk, and Compliance (GRC) platform built to replace SAP GRC Access Control. It provides comprehensive access risk management, Separation of Duties (SoD) enforcement, emergency access management, and compliance automation across multi-system enterprise environments.

**Platform URL:** governexplus.com

---

## Architecture

```
Frontend (React 18 + TypeScript + Tailwind CSS)
    ↓ REST API (HTTPS)
API Layer (FastAPI + Pydantic Schemas)
    ↓
Service Layer (Business Logic + Audit Logging)
    ↓
Repository Layer (SQLAlchemy ORM + Tenant Isolation)
    ↓
PostgreSQL 15 (Multi-Tenant Database)
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS 3.4, React Query v5, React Router v6 |
| UI Components | Custom glassmorphism component library, Headless UI, Heroicons |
| API | FastAPI (Python 3.11+), Pydantic v2, JWT Authentication |
| Database | PostgreSQL 15, SQLAlchemy 2.0+, Alembic migrations |
| Auth | JWT (PyJWT), bcrypt password hashing, RBAC |
| Deployment | Docker Compose (PostgreSQL, API, Frontend containers) |
| Charts | Recharts |

---

## Modules

### 1. Dashboard

**Path:** `/dashboard`

The main dashboard provides an at-a-glance overview of the organization's GRC posture:

- **Stats cards**: Active violations, pending approvals, certification progress, active firefighter sessions
- **Risk score gauge**: Organization-wide risk score (0-100) with trend indicator
- **Violation trends**: 6-month line chart of violation counts
- **Access request trends**: Approved/pending/rejected request volumes
- **Pending approvals table**: Top 5 items awaiting approval
- **Recent activity feed**: Latest audit log entries
- **Quick actions**: One-click navigation to common tasks

### 2. Access Request Management (ARM)

**Path:** `/access-requests`

Self-service access request lifecycle management:

- **My Requests** (`/access-requests`): View all submitted requests with status tracking
- **New Request** (`/access-requests/new`): Multi-step wizard for requesting role/access
- **Bulk Request** (`/access-requests/bulk`): Submit access requests for multiple users
- **Approval Inbox** (`/approvals`): Queue for managers to approve/reject/forward requests

**Workflow:**
1. User selects target system and role
2. Real-time risk analysis runs (SoD check, risk scoring)
3. Business justification captured
4. Request routed through approval chain (manager → role owner → security)
5. Approved access provisioned to target system
6. Full audit trail maintained

### 3. Risk Management

**Path:** `/risk`

Comprehensive access risk analysis and violation management:

- **Risk Dashboard** (`/risk`): Organization risk score, violation metrics, AI insights
- **SoD Rules** (`/risk/rules`): Create and manage Separation of Duties rules
- **Rule Library** (`/risk/sod-rules`): Pre-built SoD rule templates (SAP, Oracle, etc.)
- **Violations** (`/risk/violations`): Active violations with filtering, export, and mitigation workflows
- **Risk Simulation** (`/risk/simulation`): "What-if" analysis for role assignments
- **Entitlement Intelligence** (`/risk/entitlements`): AI-powered analysis of entitlement patterns
- **Contextual Risk** (`/risk/contextual`): Real-time risk scoring based on behavior context

**Risk Levels:** Critical, High, Medium, Low

**Violation Types:**
- SoD Conflicts (e.g., Create Vendor + Approve Payment)
- Excessive Access (privileges beyond business need)
- Sensitive Access (payroll, financial data)
- Dormant Accounts (no activity for 90+ days)

### 4. User Management

**Path:** `/users`

Enterprise user lifecycle management with database persistence:

- **User List** (`/users`): Browse all users with search, filters (department, status, risk level)
- **User Detail** (`/users/:id`): Profile, role assignments, risk score, activity log
- **Create/Edit Users**: Full CRUD operations with audit logging
- **Inactive Users** (`/users/inactive`): Users flagged for deprovisioning

**User Properties:**
- User ID, name, email, department, manager
- Status (active, inactive, locked, suspended)
- Risk score (calculated from assigned roles)
- Role assignments with effective dates
- Last login, MFA status, password expiry

### 5. Role Engineering

**Path:** `/roles`

Role lifecycle management and design:

- **Role Catalog** (`/roles`): Browse all roles with type, risk level, user count
- **Role Designer** (`/roles/designer`): Visual role composition tool

**Role Types:**
- Single: Individual technical roles
- Business: Composite business-function roles
- Composite: Aggregations of single roles
- Derived: Roles derived from templates
- Emergency: Firefighter access profiles

### 6. Firefighter (Emergency Access)

**Path:** `/firefighter`

Privileged emergency access management (PAM):

- **Dashboard** (`/firefighter`): Active sessions, recent sessions, available firefighter IDs
- **Request Access** (`/firefighter/request`): Submit emergency access request with:
  - Reason code selection (Production Incident, Change Management, Audit, Security Incident, etc.)
  - Duration selection with auto-termination
  - Ticket reference (mandatory for some reason codes)
  - Business justification
  - Planned actions list
  - Acknowledgment checkbox
- **Sessions** (`/firefighter/sessions`): Historical session list
- **Live Monitor** (`/firefighter/monitor`): Real-time session monitoring with action log

**Security Controls:**
- All actions logged in real-time
- Auto-terminate after duration expires
- Post-session controller review (SLA-based)
- Anomaly detection during session
- Approval chain based on reason code

### 7. Certification (Access Reviews)

**Path:** `/certification`

Periodic access certification campaigns:

- **Campaigns** (`/certification`): Active and scheduled certification campaigns
- **My Reviews** (`/certification/review`): Items assigned to current user for review

### 8. Compliance

**Path:** `/compliance`

Regulatory compliance tracking and evidence management.

### 9. Security Controls

**Path:** `/security-controls`

IT general control management:

- **Dashboard** (`/security-controls`): Control effectiveness overview
- **All Controls** (`/security-controls/list`): Browse, filter, and manage controls
- **Import** (`/security-controls/import`): Bulk import controls from CSV/Excel

### 10. Reports

**Path:** `/reports`

Pre-built and custom report generation:

- Compliance reports (SOX, SOD, access review)
- User access reports
- Violation reports with CSV export
- Audit trail reports

### 11. Password Self-Service

**Path:** `/password`

- **Change Password** (`/password/change`): Change platform password with policy enforcement
- **Reset in Systems** (`/password/reset`): Coordinated password reset across connected systems

### 12. AI Assistant

**Path:** `/ai`

AI-powered assistant for GRC queries, risk analysis recommendations, and natural language access to platform data.

### 13. Settings

**Path:** `/settings`

Platform configuration:

- **General** (`/settings`): Organization settings, branding, notifications
- **Policies** (`/settings/policies`): Policy-as-code management for access rules

### 14. Integrations

**Path:** `/integrations`

System connector management for SAP, Azure AD, AWS, Workday, Salesforce, and other enterprise systems.

---

## Authentication & Authorization

### Authentication Flow

1. User navigates to platform → redirected to login page
2. Credentials submitted to `/auth/login`
3. Server validates against database (bcrypt hash) or falls back to demo authentication
4. JWT access token (30 min) and refresh token (7 days) returned
5. Access token included in all API requests via `Authorization: Bearer <token>`
6. Frontend automatically refreshes token before expiry

### Role-Based Access Control (RBAC)

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| `super_admin` | Full platform access | All permissions |
| `admin` | Tenant administrator | User management, role management, settings |
| `security_admin` | Security operations | Risk rules, violations, firefighter management |
| `manager` | Department manager | Approve requests, view reports, certify access |
| `end_user` | Standard user | Submit requests, view own data, change password |

### Multi-Tenant Isolation

- All database queries filtered by `tenant_id`
- Tenant ID extracted from JWT token or request header (`X-Tenant-ID`)
- Row-level security ensures strict data isolation
- Each tenant has independent configuration

---

## API Reference

### Base URL
```
https://governexplus.com/api
```

### Authentication Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Authenticate user |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Invalidate session |
| GET | `/auth/profile` | Get current user profile |
| GET | `/auth/status` | Check auth status |
| POST | `/auth/verify` | Verify token validity |

### User Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users` | List users (paginated, filterable) |
| GET | `/users/{user_id}` | Get user details |
| POST | `/users` | Create user |
| PUT | `/users/{user_id}` | Update user |
| DELETE | `/users/{user_id}` | Delete user |
| GET | `/users/{user_id}/roles` | Get user's role assignments |

### Role Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/roles` | List roles (paginated, filterable) |
| GET | `/roles/{role_id}` | Get role details |
| POST | `/roles` | Create role |
| PUT | `/roles/{role_id}` | Update role |
| DELETE | `/roles/{role_id}` | Delete role |
| GET | `/roles/stats` | Get role statistics |

### Risk & Violation Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/risk/violations` | List violations |
| POST | `/risk/violations` | Create violation |
| PUT | `/risk/violations/{id}` | Update violation |
| GET | `/risk/rules` | List SoD rules |
| POST | `/risk/rules` | Create SoD rule |
| POST | `/risk/analyze/{user_id}` | Analyze user risk |
| POST | `/risk/simulate` | Simulate role assignment |

### Firefighter Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/firefighter/sessions` | List sessions |
| POST | `/firefighter/requests` | Request emergency access |
| GET | `/firefighter/reason-codes` | Get reason code catalog |

---

## Database Models

### Core Models

- **User**: Platform users with tenant isolation, risk scores, department
- **Role**: Roles from connected systems (SAP, Azure AD, etc.)
- **UserRole**: Many-to-many assignment with effective/expiry dates
- **RiskViolation**: SoD conflicts and access violations
- **RiskRuleModel**: SoD and risk rule definitions

### Key Fields

All models include:
- `tenant_id`: Multi-tenant isolation key
- `created_at` / `updated_at`: Audit timestamps
- `is_active`: Soft delete support

---

## Data Seeding

Seed scripts for demo/testing data:

```bash
# Seed users (30+ sample users)
python scripts/seed_users.py --tenant tenant_default --count 30

# Seed roles (30 SAP-style roles)
python scripts/seed_roles.py --tenant tenant_default --count 30

# Seed violations (SoD rules + sample violations)
python scripts/seed_violations.py --tenant tenant_default

# Clear and reseed
python scripts/seed_users.py --tenant tenant_default --clear
```

---

## UI Component Library

All pages use a shared glassmorphism component library for visual consistency:

| Component | Path | Usage |
|-----------|------|-------|
| `Button` | `components/ui/Button.tsx` | Primary, secondary, danger, ghost, success variants |
| `Card` | `components/ui/Card.tsx` | Glass-card container with padding options |
| `Input` | `components/ui/Input.tsx` | Text input, select, textarea, search input |
| `Badge` | `components/ui/Badge.tsx` | Status, risk level, severity badges |
| `Table` | `components/ui/Table.tsx` | Generic typed table with pagination |
| `PageHeader` | `components/ui/PageHeader.tsx` | Page title, subtitle, action buttons |
| `Modal` | `components/ui/Modal.tsx` | Dialog with Headless UI |
| `EmptyState` | `components/ui/EmptyState.tsx` | Empty, loading, error states |
| `StatCard` | `components/StatCard.tsx` | Dashboard metric cards |

### Design System

- **Theme**: Glassmorphism with frosted glass effects
- **Border radius**: `rounded-xl` (16px) for cards, `rounded-xl` (12px) for buttons
- **Shadows**: `shadow-glass`, `shadow-glass-hover`, `shadow-glass-sm`
- **Backgrounds**: Semi-transparent with `backdrop-blur` effects
- **Colors**: Primary blue (#0284c7), with status colors (red/orange/yellow/green)

---

## Deployment

### Docker Compose

```bash
docker-compose up -d
```

Services:
- **db**: PostgreSQL 15 on port 5432
- **api**: FastAPI on port 8000
- **frontend**: React (Vite) on port 3000

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://grc_user:...@db:5432/grc_platform` |
| `JWT_SECRET` | JWT signing secret | Auto-generated |
| `CORS_ORIGINS` | Allowed frontend origins | `https://governexplus.com` |

---

## Audit Logging

All CRUD operations are logged with:
- User ID and tenant ID
- Action type (CREATE, UPDATE, DELETE, LOGIN, LOGOUT)
- Entity type and ID
- Before/after values (for updates)
- IP address and timestamp
- Searchable via audit log API

---

## Compliance Frameworks Supported

- SOX (Sarbanes-Oxley)
- SOD (Separation of Duties)
- GDPR (Data Protection)
- ISO 27001 (Information Security)
- NIST Cybersecurity Framework
- Custom control frameworks
