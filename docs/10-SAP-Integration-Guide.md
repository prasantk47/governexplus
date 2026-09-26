# GovernexPlus — SAP Integration & Connectivity Guide

**Version:** 2.0
**Applies to:** GovernexPlus 2.x
**Last updated:** 2026-09-06

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Connection Configuration](#3-connection-configuration)
4. [User & Role Extraction](#4-user--role-extraction)
5. [Authorization Extraction](#5-authorization-extraction)
6. [Transaction Usage Data](#6-transaction-usage-data)
7. [Firefighter Operations](#7-firefighter-operations)
8. [Provisioning via RFC](#8-provisioning-via-rfc)
9. [S/4HANA Specifics](#9-s4hana-specifics)
10. [Mock / Simulation Mode](#10-mock--simulation-mode)
11. [Azure AD Integration](#11-azure-ad-integration)
12. [Workday & SuccessFactors Integration](#12-workday--successfactors-integration)

---

## 1. Overview

GovernexPlus connects to SAP ECC 6.0, SAP S/4HANA (on-premise and private cloud), and SAP BTP environments to extract user master data, role and authorization objects, transaction usage statistics, and to perform provisioning and firefighter operations.

The integration layer is implemented in `connectors/sap/` and is orchestrated by `core/integrations/connectors.py`. The connector design follows a provider abstraction pattern — all SAP-specific logic is encapsulated behind a `SAPConnector` interface, allowing mock, RFC, and future REST-based implementations to be swapped without changes to the business logic layer.

**Data flow:**

```
SAP System (ECC / S/4HANA)
       │
       │  pyrfc (RFC/BAPI calls)
       │
connectors/sap/connector.py
       │
core/integrations/connectors.py   ←— scheduler / on-demand sync
       │
DB (PostgreSQL) — users, roles, violations, usage
       │
API layer — ARA, dashboards, reports, firefighter
```

**Integration capabilities summary:**

| Capability | ECC 6.0 | S/4HANA OP | S/4HANA Cloud |
|---|:---:|:---:|:---:|
| User master extraction | Yes | Yes | REST (limited) |
| Role/profile extraction | Yes | Yes | REST (limited) |
| Authorization object extraction | Yes | Yes | No |
| Transaction usage (SM20/STAD) | Yes | Yes | No |
| Firefighter lock/unlock | Yes | Yes | No |
| Provisioning (role assign/remove) | Yes | Yes | Partial |
| Fiori app catalog | No | Yes | Yes |
| Business Partner sync | No | Yes | Yes |

---

## 2. Prerequisites

### 2.1 SAP NetWeaver RFC SDK

GovernexPlus uses the `pyrfc` Python library, which is a Cython wrapper around the SAP NetWeaver RFC SDK (NWRFC SDK). The NWRFC SDK must be installed on the GovernexPlus server before the `pyrfc` package can be used.

**Installation steps:**

1. Download the NWRFC SDK from the SAP Service Marketplace (SAP ONE Support Launchpad → Software Downloads → Search "NWRFC").
   - Package name: `NWRFC_SDK_<version>_<os>.zip`
   - Required version: 7.50 or higher.

2. Extract and install the SDK libraries:
   ```bash
   # Linux (recommended deployment OS)
   mkdir -p /usr/local/sap/nwrfcsdk
   unzip nwrfc750P_<patch>.zip -d /usr/local/sap/nwrfcsdk/

   # Add to LD_LIBRARY_PATH
   echo '/usr/local/sap/nwrfcsdk/lib' | tee /etc/ld.so.conf.d/nwrfcsdk.conf
   ldconfig

   # Set required environment variable
   export SAPNWRFC_HOME=/usr/local/sap/nwrfcsdk
   ```

3. Install `pyrfc`:
   ```bash
   pip install pyrfc==3.3.1
   ```

4. Verify installation:
   ```python
   import pyrfc
   print(pyrfc.__version__)
   ```

> **Docker note:** When running GovernexPlus in Docker, the NWRFC SDK libraries must be copied into the container image. See the `Dockerfile.prod` comments for the multi-stage build approach that copies SDK files from a private registry or build arg.

### 2.2 SAP RFC Service User Setup

A dedicated RFC service user must be created in each SAP system. This user should be of type `S` (System) in SAP, which prevents interactive logon and excludes the user from SoD analysis.

**Minimum authorizations required:**

| Authorization Object | Field | Value | Purpose |
|---|---|---|---|
| `S_RFC` | `RFC_TYPE` | `FUGR` | Allow function group RFC calls |
| `S_RFC` | `RFC_NAME` | `SUSR*`, `BAPI*`, `SUIM*`, `RFC1` | Allow required function groups |
| `S_TCODE` | `TCD` | `SM20`, `STAD` | Allow audit log extraction |
| `S_USER_GRP` | `ACTVT` | `03`, `05` | Read user master data |
| `S_USER_GRP` | `CLASS` | `*` | All user groups |
| `S_USER_AGR` | `ACTVT` | `03` | Read role assignments |
| `S_TABU_DIS` | `ACTVT` | `03` | Read authorization tables |
| `S_TABU_DIS` | `DICBERCLS` | `SS`, `SC` | System and customer table access |

A pre-built SAP role `ZGX_RFC_READ` is provided in `docs/sap-role-exports/ZGX_RFC_READ.txt` and can be imported via transaction `PFCG`.

For provisioning and firefighter operations, an additional privileged user (type `S`) with the following objects is required:

| Authorization Object | Field | Value | Purpose |
|---|---|---|---|
| `S_USER_AGR` | `ACTVT` | `01`, `02`, `06` | Assign/remove roles |
| `S_USER_GRP` | `ACTVT` | `01`, `02`, `05` | Create/modify users |
| `S_USER_PWD` | `ACTVT` | `03`, `05` | Reset passwords |

---

## 3. Connection Configuration

### 3.1 Direct Application Server Connection

The simplest connection type. Connects to a single SAP application server instance.

Environment variables:

```env
SAP_HOST=sap-ecc.acme.com
SAP_SYSNR=00
SAP_CLIENT=100
SAP_USER=GNX_RFC
SAP_PASSWORD=SecretPassword123
SAP_LANGUAGE=EN
SAP_USE_MOCK=false
```

Programmatic connection parameters passed to `pyrfc.Connection`:

```python
conn_params = {
    "ashost": settings.SAP_HOST,
    "sysnr": settings.SAP_SYSNR,
    "client": settings.SAP_CLIENT,
    "user": settings.SAP_USER,
    "passwd": settings.SAP_PASSWORD,
    "lang": settings.SAP_LANGUAGE,
}
```

### 3.2 Load-Balanced Connection (Message Server)

For production SAP systems with multiple application server instances, use message server-based load balancing:

```env
SAP_MSG_HOST=sap-msg.acme.com
SAP_MSG_SERVICE=sapmsP01
SAP_LOGON_GROUP=PUBLIC
SAP_SYSNR=01
SAP_CLIENT=100
SAP_USER=GNX_RFC
SAP_PASSWORD=SecretPassword123
```

```python
conn_params = {
    "mshost": settings.SAP_MSG_HOST,
    "msserv": settings.SAP_MSG_SERVICE,
    "sysid": settings.SAP_SYSID,
    "group": settings.SAP_LOGON_GROUP,
    "client": settings.SAP_CLIENT,
    "user": settings.SAP_USER,
    "passwd": settings.SAP_PASSWORD,
}
```

### 3.3 SNC (Secure Network Communication) Setup

SNC encrypts the RFC communication channel using X.509 certificates, eliminating the need to transmit the RFC user password over the network. SNC is strongly recommended for production environments.

**Requirements:**
- SAP Cryptographic Library (`libsapcrypto.so`) installed on the GovernexPlus server.
- A PKCS#12 certificate for the GovernexPlus client identity, created by your PKI.
- The GovernexPlus SNC identity registered in SAP transaction `SM30` (table `VSNCSYSACL`).

**Environment variables for SNC:**

```env
SAP_SNC_LIB=/usr/lib/libsapcrypto.so
SAP_SNC_MY_NAME=p:CN=GNX-PROD,O=ACME,C=US
SAP_SNC_PARTNER_NAME=p:CN=SAP-PRD,O=ACME,C=US
SAP_SNC_QOP=9
```

`SAP_SNC_QOP` (Quality of Protection):
- `1` — Authentication only
- `2` — Integrity protection
- `3` — Privacy (encryption)
- `9` — Maximum available (recommended)

```python
conn_params.update({
    "snc_lib": settings.SAP_SNC_LIB,
    "snc_myname": settings.SAP_SNC_MY_NAME,
    "snc_partnername": settings.SAP_SNC_PARTNER_NAME,
    "snc_qop": settings.SAP_SNC_QOP,
})
```

When SNC is enabled, `user` and `passwd` parameters are omitted from the connection dictionary — identity is established via the certificate.

### 3.4 Connection Pooling

The SAP connector maintains a connection pool of `pyrfc.Connection` instances per SAP system per GovernexPlus tenant. Pool configuration:

| Parameter | Default | Description |
|---|---|---|
| `SAP_POOL_SIZE` | `5` | Maximum simultaneous RFC connections per system. |
| `SAP_CONNECTION_TIMEOUT` | `30` | Seconds before an idle connection is closed. |
| `SAP_CALL_TIMEOUT` | `120` | Seconds before a single RFC call is aborted. |

---

## 4. User & Role Extraction

### 4.1 BAPIs Used

| BAPI | Purpose |
|---|---|
| `BAPI_USER_GETLIST` | Enumerate all SAP user IDs filtered by user group, logon date range, or user type. |
| `BAPI_USER_GET_DETAIL` | Retrieve full user master record for a single user (logon data, personal data, role assignments, profile assignments). |
| `SUSR_USER_AUTH_FOR_OBJ_GET` | Retrieve all authorization values for a specific object for a given user. |
| `PRGN_ACTIVITY_GROUPS_LOAD_RFC` | Load role/profile data from the source system for role comparison. |

### 4.2 Tables Read Directly

For high-volume extraction, GovernexPlus uses `RFC_READ_TABLE` to read SAP tables directly. This is faster than calling individual BAPIs for each user.

| Table | Content | Used For |
|---|---|---|
| `USR02` | User logon data (password hash, lock status, last logon) | User sync |
| `USR21` | User address key (links to ADR6) | Name/email resolution |
| `ADR6` | Email addresses | Contact data |
| `AGR_USERS` | Role-to-user assignment with validity dates | Role assignment sync |
| `AGR_AGRS` | Composite role members | Role hierarchy |
| `AGR_1251` | Authorization object values within roles | Authorization extraction |
| `AGR_1252` | Organization-level values for roles | Org-level auth values |
| `UST04` | User-to-profile assignments | Profile-based auth |
| `UST10S` | Single profiles (expanded) | Profile authorization data |
| `UST12` | Authorization values per profile | Auth value extraction |

### 4.3 Sync Scheduling

User and role data is synchronized on two schedules:

| Sync Type | Default Schedule | Trigger | Scope |
|---|---|---|---|
| Full sync | Daily at 02:00 | Scheduler | All users, all roles, all authorizations |
| Delta sync | Every 4 hours | Scheduler | Users with `MODDA` (last modified date) after last sync |
| On-demand sync | Manual | API: `POST /api/v1/integrations/sap/sync` | Specific user or all users |
| Event-triggered sync | Within 5 minutes | JML hire/transfer/terminate event | Specific user only |

### 4.4 Delta vs Full Sync

**Full sync:**
- Reads the complete `USR02` and `AGR_USERS` tables.
- Compares against the GovernexPlus database and applies creates, updates, and soft-deletes.
- Duration: 5–30 minutes depending on user count.
- Recommended to run during off-peak hours.

**Delta sync:**
- Reads only records where `MODDA >= last_sync_timestamp`.
- Much faster (typically 30 seconds for <1,000 changes).
- May miss deletions — full sync is required to detect removed assignments.

Delta sync configuration:

```json
{
  "delta_sync": {
    "enabled": true,
    "interval_hours": 4,
    "missed_delta_threshold": 3,
    "fallback_to_full_sync_on_miss": true
  }
}
```

---

## 5. Authorization Extraction

### 5.1 Authorization Object Model

SAP authorization objects are the atomic unit of access control. Each object has a name (e.g., `F_BKPF_BUK`), up to 10 fields (e.g., `ACTVT`, `BUKRS`), and each field has a set of permitted values (e.g., `01`, `02`, `03`).

GovernexPlus extracts the full authorization object/field/value matrix for each user by:
1. Expanding the user's role assignments → profiles → authorization objects.
2. Supplementing with direct profile assignments.
3. Resolving composite roles to their member single roles.
4. Applying org-level variable substitutions (from `AGR_1252`).

### 5.2 Profile Generation Data

When SAP role profiles are in a "not generated" state (i.e., authorization data has changed but `PFCG` generation has not been run), the authorizations in `AGR_1251` may be stale. GovernexPlus detects ungenerated profiles via:

```python
# Check AGR_DEFINE.GENERATE_FLAG
# G = generated, N = not generated, _ = new (never generated)
ungenerated = [r for r in roles if r['GENERATE_FLAG'] != 'G']
```

Ungenerated roles are flagged in the UI with a warning icon and excluded from the authoritative authorization matrix until regenerated in SAP.

### 5.3 Org-Level Values

Authorization objects in SAP may contain organization-level fields (e.g., `BUKRS` — company code, `WERKS` — plant, `VKORG` — sales org). These are stored in `AGR_1252` as variable mappings.

GovernexPlus resolves org-level values during extraction and expands variable placeholders to their concrete values, enabling accurate SoD analysis at the org-level (e.g., detecting a user who can create vendors in company code 1000 AND process payments in company code 1000 — a genuine conflict — versus one who operates in different company codes — potentially acceptable under org-level controls).

---

## 6. Transaction Usage Data

Usage-aware risk scoring is one of GovernexPlus's key differentiators over SAP GRC. The platform extracts actual transaction usage to determine whether assigned access is actively exercised.

### 6.1 SM20 Audit Log Extraction

The SAP security audit log (`SM20`) records every transaction start, authorization failure, and sensitive system action.

**Extraction process:**
1. Call `BAPI_XMI_LOGON` to connect to the XMI log interface.
2. Call `BAPI_XMI_GET_AUDITMESSAGES` with date/time range and filter for transaction starts (`AU5` message class).
3. Parse returned records: `MANDT`, `MANDTCHAR`, `UNAME`, `TERMINAL`, `DATUM`, `UZEIT`, `TCOD`, `REPNA`.
4. Upsert into `user_tcode_usage` table with aggregated counts per user/tcode/date.

The SM20 extraction is configured to look back 90 days on first run and then incrementally daily.

### 6.2 STAD Work Process Statistics

`STAD` (Statistical Records Display) provides more granular per-dialog-step statistics including CPU time, database reads, and network bytes. GovernexPlus uses STAD data to:
- Identify high-resource transactions (potential data exfiltration signals).
- Corroborate SM20 usage data.
- Detect batch program executions that don't appear in SM20.

STAD is extracted via `TH_WPINFO_BY_TASKTYPE` or direct table reads from `MONI`/`MONDD`.

### 6.3 Usage-Based Risk Scoring

After extraction, usage data is joined with the authorization matrix to compute usage modifiers for each user-role-tcode combination:

| Usage Status | Last Used | Risk Modifier |
|---|---|---|
| Never used | — | −50% |
| Dormant | >180 days | −40% |
| Stale | 90–180 days | −25% |
| Infrequent | 30–90 days | −10% |
| Active | <30 days | 0% |
| Frequent | <30 days, >20 uses | +15% |

---

## 7. Firefighter Operations

### 7.1 User Lock/Unlock

GovernexPlus uses the following BAPIs for firefighter session management:

| Operation | BAPI | Parameters |
|---|---|---|
| Lock user account (pre-FF) | `SUSR_USER_LOCK` | `BNAME` (username) |
| Assign firefighter role | `BAPI_USER_ACTGROUPS_ASSIGN` | `USERNAME`, `ACTIVITYGROUPS` table |
| Unlock firefighter account | `SUSR_USER_UNLOCK` | `BNAME` |
| Remove firefighter role | `BAPI_USER_ACTGROUPS_ASSIGN` | Remove from `ACTIVITYGROUPS` |
| Re-lock account post-session | `SUSR_USER_LOCK` | `BNAME` |

**Firefighter flow:**
1. Approver approves firefighter request in GovernexPlus.
2. GovernexPlus assigns the firefighter role to the SAP user via RFC.
3. User performs their work in SAP (session recorded via SM20).
4. Session expires or user manually ends the session.
5. GovernexPlus removes the firefighter role via RFC.
6. SM20 activity during the session window is captured and stored.
7. Reviewer reviews the session activity log within the configured SLA.

### 7.2 Password Reset

Emergency password resets during firefighter sessions are supported via:

```python
result = conn.call(
    "SUSR_USER_CHANGE_PASSWORD",
    BNAME=username,
    PASSWORD=new_password,
    NEW_PASSWORD=new_password,
)
```

Passwords set via GovernexPlus firefighter reset are marked as `FORCE_CHANGE=X` — the user must change the password on next logon.

### 7.3 Session Activity Capture

During an active firefighter session, GovernexPlus polls SM20 every 5 minutes (configurable) to capture:
- All transaction codes executed.
- All authorization failures (potential probing).
- Any sensitive object accesses (debug with replace, table views, user admin).

This data is stored in `firefighter_session_activities` and presented to the reviewer in the session review UI with a timeline view.

---

## 8. Provisioning via RFC

### 8.1 Role Assignment

```python
result = conn.call(
    "BAPI_USER_ACTGROUPS_ASSIGN",
    USERNAME=username,
    ACTIVITYGROUPS=[
        {
            "AGR_NAME": role_name,
            "FROM_DAT": from_date,  # YYYYMMDD
            "TO_DAT": to_date,      # YYYYMMDD or "99991231"
        }
    ],
)
```

After role assignment, `BAPI_TRANSACTION_COMMIT` must be called to commit the change.

### 8.2 Role Removal

To remove specific roles while preserving others, GovernexPlus:
1. Fetches the current role assignment list via `BAPI_USER_GET_DETAIL`.
2. Removes the target roles from the list.
3. Calls `BAPI_USER_ACTGROUPS_ASSIGN` with the modified list (SAP replaces the full assignment set).

### 8.3 Provisioning Workflow Integration

Role provisioning is triggered by the workflow engine upon final approval:

```
Access Request Approved
        │
core/workflow/orchestrator.py → "provision_access" action
        │
core/integrations/connectors.py → SAPConnector.assign_roles()
        │
pyrfc → BAPI_USER_ACTGROUPS_ASSIGN
        │
Audit log entry created
        │
Requester notification sent
```

If the RFC call fails, the provisioning attempt is retried up to 3 times with exponential backoff. Persistent failures create a `PROVISIONING_FAILED` alert visible to the `security_admin`.

---

## 9. S/4HANA Specifics

### 9.1 Business Partner (BP) Migration

In S/4HANA, SAP has merged the Vendor (LFA1) and Customer (KNA1) master records into the Business Partner (BP) model. This affects SoD rules in the following ways:

- Transaction codes for vendor/customer maintenance have changed: `FK01`→`BP`, `XK01`→`BP`, `FD01`→`BP`.
- GovernexPlus maintains a tcode mapping table (`core/migration/tcode_mapping.py`) that translates ECC tcodes to S/4HANA equivalents for SoD rule evaluation.
- Rules referencing old vendor/customer tcodes are automatically re-evaluated against S/4HANA BP authorizations using the `F_BP_GUID` and `F_BUPA_RLT` authorization objects.

### 9.2 Fiori App Catalog

S/4HANA Fiori apps are controlled via `PFCG` roles and Fiori catalog/group assignments stored in the backend ABAP system. GovernexPlus extracts the Fiori app catalog from:

| Object | Description |
|---|---|
| `SSM_CUST` | Fiori launchpad customizing |
| `/UI2/CCDF` | Catalog group and tile assignments |
| `AGR_HIER` | Role hierarchy for Fiori roles |

Each Fiori app ID is mapped to the corresponding backend authorization objects, enabling SoD analysis at the app level (not just tcode level). This mapping is maintained in `core/fiori/app_mapping.py`.

### 9.3 Simplified Authorization Objects

S/4HANA introduces simplified authorization checks for certain objects. GovernexPlus handles these via:

- **Central Finance (CFIN):** Authorization objects `F_BKPF_BUK` still apply; GL account objects are simplified.
- **Universal Journal (ACDOCA):** New authorization object `F_ACDOCA` for universal journal access.
- **Material Ledger:** `F_CKMLMVT` replaces some CO objects.

The tcode-to-auth-object mapping in `core/rules/sod_ruleset.py` includes S/4HANA-specific entries for all rules where the authorization model differs from ECC.

---

## 10. Mock / Simulation Mode

### 10.1 When to Use Mock Mode

Mock mode (`SAP_USE_MOCK=true`) is the default and is suitable for:
- Development and CI/CD pipelines without SAP access.
- Demo and evaluation deployments.
- UAT testing of GovernexPlus features without a test SAP system.
- Training environments.

### 10.2 How the Mock Connector Works

`connectors/sap/mock_connector.py` implements the same interface as the live RFC connector. It returns:
- A set of 50 synthetic SAP users with realistic role assignments.
- 15 SAP roles covering common FI, MM, SD, HR, and Basis functions.
- Authorization objects and values consistent with common SoD violations.
- Simulated SM20 usage data for 90 days, with realistic usage patterns (80% of users use <20% of their assigned tcodes).
- Simulated provisioning responses (always succeeds unless `MOCK_PROVISIONING_FAIL_RATE` is set to a non-zero value).

### 10.3 Mock Data Customization

Custom mock data can be injected by placing JSON files in `connectors/sap/mock_data/`:

```
connectors/sap/mock_data/
├── users.json         # User master records
├── roles.json         # Role definitions
├── role_assignments.json  # User-to-role mappings
├── auth_values.json   # Authorization object values per role
└── usage.json         # SM20 usage simulation data
```

The mock connector reads from these files at startup. This allows functional testers to build realistic violation scenarios without live SAP access.

### 10.4 Switching from Mock to Live

1. Set `SAP_USE_MOCK=false` in the environment.
2. Set all `SAP_*` connection parameters.
3. Verify connectivity: `POST /api/v1/integrations/sap/test-connection`.
4. Run an on-demand full sync: `POST /api/v1/integrations/sap/sync?type=full`.
5. Verify user and role counts in the admin dashboard.

---

## 11. Azure AD Integration

### 11.1 App Registration

Create an Azure AD App Registration for GovernexPlus in the Azure Portal:

1. Navigate to Azure Active Directory → App registrations → New registration.
2. Name: `GovernexPlus GRC`.
3. Supported account types: Accounts in this organizational directory only.
4. Redirect URI: `https://your-governex-host/api/v1/auth/azure/callback` (for SSO, if enabled).
5. Note the **Application (client) ID** and **Directory (tenant) ID**.
6. Under Certificates & secrets → New client secret. Copy the value immediately.

### 11.2 Graph API Permissions

Add the following Microsoft Graph API application permissions (not delegated):

| Permission | Type | Purpose |
|---|---|---|
| `User.Read.All` | Application | Read all user profiles |
| `Group.Read.All` | Application | Read group memberships |
| `Directory.Read.All` | Application | Read directory objects |
| `AuditLog.Read.All` | Application | Read Azure AD sign-in logs |
| `UserAuthenticationMethod.Read.All` | Application | Read MFA registration status |

Grant admin consent for all permissions after adding them.

### 11.3 User/Group Sync

The Azure AD sync job runs on the schedule configured by `AZURE_SYNC_INTERVAL_HOURS`. It:

1. Calls `GET /v1.0/users?$select=id,userPrincipalName,displayName,mail,department,jobTitle,accountEnabled,lastSignInDateTime`.
2. For each user, calls `GET /v1.0/users/{id}/memberOf` to retrieve group memberships.
3. Maps Azure AD groups to GovernexPlus roles based on the group-to-role mapping table (`azure_group_role_mappings`).
4. Resolves the SAP user ID via the `extensionAttribute1` field (configurable) or via `onPremisesSamAccountName`.
5. Updates the GovernexPlus user profile with Azure AD attributes (department, job title, manager, MFA status).

Group-to-role mapping configuration:

```json
{
  "azure_group_role_mappings": [
    {
      "azure_group_id": "aad-group-uuid-1",
      "azure_group_name": "GNX-SecurityAdmins",
      "governex_role": "security_admin"
    },
    {
      "azure_group_id": "aad-group-uuid-2",
      "azure_group_name": "GNX-RiskManagers",
      "governex_role": "risk_manager"
    }
  ]
}
```

### 11.4 Azure AD SSO (SAML / OIDC)

GovernexPlus supports Azure AD SSO via OpenID Connect. When configured, users are redirected to the Azure AD login page and returned to GovernexPlus with a JWT that maps their Azure AD claims to GovernexPlus roles.

```env
AZURE_SSO_ENABLED=true
AZURE_SSO_CLIENT_ID=<app-client-id>
AZURE_SSO_CLIENT_SECRET=<client-secret>
AZURE_SSO_TENANT_ID=<directory-tenant-id>
AZURE_SSO_REDIRECT_URI=https://grc.acme.com/api/v1/auth/azure/callback
```

---

## 12. Workday & SuccessFactors Integration

### 12.1 Workday Setup

GovernexPlus connects to Workday via the Workday REST API or RaaS (Report-as-a-Service) endpoints. An Integration System User (ISU) is required.

**Create ISU in Workday:**
1. Navigate to Create Integration System User.
2. Assign the ISU to an Integration System Security Group with the following domain security policies:
   - Worker Data: All Workers (View)
   - Staffing (View)
   - Job and Position (View)
   - Organization and Roles (View)

**Workday API configuration:**

```env
WORKDAY_API_URL=https://wd2-impl-services1.workday.com/ccx/service/acme/Human_Resources/v42.0
WORKDAY_USERNAME=ISU_GNX@acme
WORKDAY_PASSWORD=SecretPassword
WORKDAY_TENANT=acme
```

### 12.2 JML Event Processing — Workday

GovernexPlus polls the Workday API for Joiner, Mover, Leaver events:

| Event Type | Workday Trigger | GovernexPlus Action |
|---|---|---|
| Joiner (Hire) | `Hire` business process completion | Create user profile, trigger provisioning workflow |
| Mover (Transfer) | `Transfer` or `Change Job` completion | Update department/role, re-evaluate SoD, trigger access review |
| Mover (Promotion) | `Promote Employee` completion | Update job title, evaluate role changes |
| Leaver (Terminate) | `Terminate Employee` completion | Trigger immediate access revocation workflow |
| Leaver (Resignation) | `End Employment` completion | As above, with configurable grace period |
| Leave of Absence | `Place on Leave` completion | Optionally suspend (not terminate) SAP access |

The Workday sync job polls for change events using the `Changed_Workers` RaaS report with an `Effective_From` filter set to the last sync timestamp.

### 12.3 SuccessFactors Setup

GovernexPlus connects to SAP SuccessFactors via the OData V2 API.

```env
SF_API_URL=https://api4.successfactors.com
SF_COMPANY_ID=ACME
SF_USERNAME=sfadmin@ACME
SF_API_KEY=base64encodedpassword
```

**Entities consumed:**

| OData Entity | Fields Used | Purpose |
|---|---|---|
| `User` | `userId`, `username`, `email`, `firstName`, `lastName`, `department`, `jobTitle`, `manager`, `status` | User profile sync |
| `EmpJob` | `userId`, `startDate`, `endDate`, `jobCode`, `companyId`, `costCenter` | Employment record |
| `EmpEmployment` | `userId`, `originalStartDate`, `lastDateWorked`, `terminationDate` | JML status |

### 12.4 JML Event Processing — SuccessFactors

SuccessFactors JML events are detected by polling `EmpEmployment` with a filter on `lastModifiedDateTime >= last_sync`:

```
GET /odata/v2/EmpEmployment?$filter=lastModifiedDateTime ge datetime'2026-09-05T02:00:00'
    &$select=userId,originalStartDate,lastDateWorked,terminationDate
    &$format=json
```

The connector maps `terminationDate` being set to a Leaver event, and `originalStartDate` being a future date relative to the last sync to a Joiner event. Transfer/Mover events are detected via changes in `companyId` or `jobCode`.

---

*For deployment configuration, see the [Deployment & Operations Guide](./12-Deployment-Operations-Guide.md). For environment variable reference, see the [Configuration Reference Guide](./09-Configuration-Reference-Guide.md).*
