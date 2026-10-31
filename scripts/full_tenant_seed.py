"""
GovernexPlus -- Full Tenant Onboarding Seeder v3 (Schema-Correct)
=================================================================
Populates every major table with realistic Acme Corporation demo data.
Uses correct column names and integer FK lookups via RETURNING id.

Run on server:
  cd /opt/governexplus/app
  source venv/bin/activate
  DATABASE_URL="postgresql://governex:G0v3rn3x_Pr0d_2026!@localhost:5432/governexplus" \
    python scripts/full_tenant_seed.py
"""
from __future__ import annotations
import os, sys, uuid, datetime, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL",
    "postgresql://governex:G0v3rn3x_Pr0d_2026!@localhost:5432/governexplus")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

try:
    from passlib.context import CryptContext
    _ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    HASHED_PW = _ctx.hash("AcmeP@ss2026!")
except Exception:
    HASHED_PW = "$2b$12$kqGNpUWQrjwmGh5dPwfAZeabfvOXPqJRLmXX7O./jZ6aW4izshZty"

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, echo=False)

TID = "acme-corp-demo"
NOW = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

def dt(days=0, hours=0):
    return NOW - datetime.timedelta(days=days, hours=hours)

def new_id():
    return str(uuid.uuid4())

print("=" * 60)
print("GovernexPlus Full Tenant Seeder v3")
print(f"Tenant: {TID}")
print("=" * 60)

# FK lookup maps (populated as we insert)
user_pk = {}    # user_id_str -> users.id (integer)
role_pk = {}    # role_id_str -> roles.id (integer)
ou_pk   = {}    # unit_id_str -> org_units.id (integer)
risk_pk = {}    # risk_id_str -> enterprise_risks.id (integer)
ctrl_pk = {}    # control_id_str -> process_controls.id (integer)
test_pk = {}    # test_id_str -> control_tests.id (integer)
plan_pk = None  # audit_plans.id (integer)
eng_pk  = {}    # engagement_id_str -> audit_engagements.id (integer)

with Session(engine) as db:

    # =========================================================
    # CLEANUP -- delete previous seed for this tenant
    # =========================================================
    print("\n[0/30] Cleaning up previous seed data...")
    cleanup_order = [
        "audit_findings",
        "audit_engagements",
        "audit_plans",
        "control_deficiencies",
        "control_tests",
        "risk_violations",
        "user_roles",
        "key_risk_indicators",
        "risk_incidents",
        "risk_appetites",
        "enterprise_risks",
        "mitigation_controls",
        "process_controls",
        "firefighter_sessions",
        "firefighter_requests",
        "certification_campaigns",
        "jml_events",
        "jml_policies",
        "vendor_assessments",
        "vendor_issues",
        "vendors",
        "fraud_alerts",
        "fraud_cases",
        "fraud_rules",
        "bcm_test_exercises",
        "bcm_plans",
        "bia_records",
        "whistleblower_cases",
        "standalone_surveys",
        "policy_documents",
        "notification_preferences",
        "sync_configs",
        "roles",
    ]
    # org_units: has self-FK, clear parent first
    for tbl in cleanup_order:
        try:
            db.execute(text(f"DELETE FROM {tbl} WHERE tenant_id = :tid"), {"tid": TID})
        except Exception:
            db.rollback()
    # org_units self-FK
    try:
        db.execute(text("UPDATE org_units SET parent_id = NULL WHERE tenant_id = :tid"), {"tid": TID})
        db.execute(text("DELETE FROM org_units WHERE tenant_id = :tid"), {"tid": TID})
    except Exception:
        db.rollback()
    # users (after user_roles deleted)
    try:
        db.execute(text("DELETE FROM users WHERE tenant_id = :tid"), {"tid": TID})
    except Exception:
        db.rollback()
    # tenants
    try:
        db.execute(text("DELETE FROM tenants WHERE slug = :tid"), {"tid": TID})
    except Exception:
        db.rollback()
    try:
        db.commit()
        print("  OK: Previous data cleared")
    except Exception as e:
        db.rollback()
        print(f"  WARN: Cleanup partial: {e}")

    # =========================================================
    # 1. TENANT
    # =========================================================
    print("\n[1/30] Creating tenant...")
    try:
        db.execute(text("""
            INSERT INTO tenants (id, name, slug, status, tier, max_users,
                admin_email, admin_name, modules_enabled, settings,
                is_deleted, created_at, updated_at)
            VALUES (:id, :name, :slug, 'active', 'enterprise', 500,
                'admin@acmecorp.com', 'Adam Admin',
                :modules, :settings,
                false, :now, :now)
        """), {
            "id": new_id(), "name": "Acme Corporation Ltd", "slug": TID,
            "modules": json.dumps(["access","risk","audit","process_control",
                                   "jml","tprm","fraud","bcm","whistleblower","survey"]),
            "settings": json.dumps({"sap_systems": ["ECC","S4HANA"], "currency": "AUD",
                                    "timezone": "Australia/Sydney"}),
            "now": NOW,
        })
        db.commit()
        print("  OK: Acme Corporation Ltd")
    except Exception as e:
        db.rollback()
        print(f"  ERR Tenant: {e}")

    # =========================================================
    # 2. USERS  (password_hash, no is_active column)
    # =========================================================
    print("\n[2/30] Creating users...")
    users_data = [
        ("u-admin-01", "acme_admin",       "Adam Admin",        "IT Administration",   "IT",       "tenant_admin"),
        ("u-ciso-01",  "acme_ciso",        "Clara CISO",        "Information Security","IT",       "ciso"),
        ("u-comp-01",  "acme_compliance",  "Carl Compliance",   "Compliance",          "Finance",  "compliance_officer"),
        ("u-risk-01",  "acme_risk",        "Rachel Risk",       "Risk Management",     "Finance",  "risk_manager"),
        ("u-audit-01", "acme_auditor",     "Alan Auditor",      "Internal Audit",      "Finance",  "auditor"),
        ("u-mgr-01",   "acme_manager",     "Mark Manager",      "Finance",             "Finance",  "line_manager"),
        ("u-ap-01",    "john.smith",       "John Smith",        "Accounts Payable",    "Finance",  "business_user"),
        ("u-ar-01",    "sarah.jones",      "Sarah Jones",       "Accounts Receivable", "Finance",  "business_user"),
        ("u-mm-01",    "mike.chen",        "Mike Chen",         "Procurement",         "Operations","business_user"),
        ("u-tr-01",    "lisa.wang",        "Lisa Wang",         "Treasury",            "Finance",  "business_user"),
        ("u-hr-01",    "tom.brown",        "Tom Brown",         "Human Resources",     "HR",       "business_user"),
        ("u-sd-01",    "anna.lee",         "Anna Lee",          "Sales",               "Sales",    "business_user"),
        ("u-sec-01",   "david.kim",        "David Kim",         "IT Security",         "IT",       "security_admin"),
        ("u-ff-01",    "frank.controller", "Frank Controller",  "Finance",             "Finance",  "business_user"),
    ]
    count = 0
    for uid_str, uname, fname, dept, cc, utype in users_data:
        try:
            row = db.execute(text("""
                INSERT INTO users (tenant_id, user_id, username, email, full_name,
                    password_hash, department, company_code, user_type, status,
                    created_at, updated_at)
                VALUES (:tid, :uid, :un, :email, :fn, :pw, :dept, :cc, :ut,
                    'active', :now, :now)
                RETURNING id
            """), {
                "tid": TID, "uid": uid_str, "un": uname,
                "email": f"{uname.replace('.','_')}@acmecorp.com",
                "fn": fname, "pw": HASHED_PW, "dept": dept,
                "cc": cc, "ut": utype, "now": NOW,
            }).fetchone()
            user_pk[uid_str] = row[0]
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR user {uname}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} users")
    except Exception as e:
        db.rollback()
        print(f"  ERR users commit: {e}")

    # =========================================================
    # 3. ROLES
    # =========================================================
    print("\n[3/30] Creating SAP roles...")
    roles_data = [
        ("r-fi-ap-full", "Z_FI_AP_FULL",      "Finance AP Full Access",         "FI", "composite", "high"),
        ("r-fi-ap-crt",  "Z_FI_AP_CREATE",     "Finance AP Create",              "FI", "single",    "medium"),
        ("r-fi-ap-apr",  "Z_FI_AP_APPROVE",    "Finance AP Approve",             "FI", "single",    "high"),
        ("r-fi-gl",      "Z_FI_GL_POST",       "GL Journal Entry Posting",       "FI", "single",    "high"),
        ("r-mm-buyer",   "Z_MM_BUYER",         "MM Purchasing Buyer",            "MM", "single",    "medium"),
        ("r-mm-gr",      "Z_MM_GR_POST",       "MM Goods Receipt Posting",       "MM", "single",    "low"),
        ("r-mm-ven",     "Z_MM_VENDOR_CREATE", "Vendor Master Create",           "MM", "single",    "high"),
        ("r-sd-order",   "Z_SD_ORDER_CREATE",  "SD Sales Order Create",          "SD", "single",    "medium"),
        ("r-sd-bill",    "Z_SD_BILLING",       "SD Billing Release",             "SD", "single",    "high"),
        ("r-hr-pay",     "Z_HR_PAYROLL",       "HR Payroll Processing",          "HR", "single",    "critical"),
        ("r-hr-maint",   "Z_HR_MAINTAIN",      "HR Employee Master Maintain",    "HR", "single",    "high"),
        ("r-bc-useradm", "Z_BC_USER_ADMIN",    "BC User Administration",         "BC", "single",    "critical"),
        ("r-tr-pay",     "Z_TR_PAYMENT",       "Treasury Payment Run",           "TR", "single",    "critical"),
        ("r-basis-all",  "SAP_ALL",            "Full SAP Authorization (Basis)", "BC", "composite", "critical"),
    ]
    count = 0
    for rid, rname, rdesc, rcat, rtype, rlevel in roles_data:
        try:
            row = db.execute(text("""
                INSERT INTO roles (tenant_id, role_id, role_name, description,
                    source_system, role_type, risk_level, is_sensitive, is_active,
                    created_at, updated_at)
                VALUES (:tid, :rid, :rn, :desc,
                    'SAP_ECC', :rt, :rl, true, true,
                    :now, :now)
                RETURNING id
            """), {
                "tid": TID, "rid": rid, "rn": rname, "desc": rdesc,
                "rt": rtype, "rl": rlevel, "now": NOW,
            }).fetchone()
            role_pk[rid] = row[0]
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR role {rname}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} roles")
    except Exception as e:
        db.rollback()
        print(f"  ERR roles commit: {e}")

    # =========================================================
    # 4. USER-ROLE ASSIGNMENTS (integer FKs)
    # =========================================================
    print("\n[4/30] Assigning roles (including SoD conflicts)...")
    assignments = [
        # (user_id_str, role_id_str)
        # Admin
        ("u-admin-01", "r-bc-useradm"),
        # CISO
        ("u-ciso-01", "r-bc-useradm"),
        # John Smith -- SoD conflict: AP Create + AP Approve
        ("u-ap-01", "r-fi-ap-crt"),
        ("u-ap-01", "r-fi-ap-apr"),   # SoD violation!
        # Sarah Jones -- AP + GL
        ("u-ar-01", "r-fi-ap-crt"),
        ("u-ar-01", "r-fi-gl"),       # SoD violation!
        # Mike Chen -- Buyer + GR + Vendor
        ("u-mm-01", "r-mm-buyer"),
        ("u-mm-01", "r-mm-gr"),
        ("u-mm-01", "r-mm-ven"),      # SoD violation!
        # Lisa Wang -- Treasury
        ("u-tr-01", "r-tr-pay"),
        ("u-tr-01", "r-fi-gl"),       # SoD violation!
        # Tom Brown -- HR
        ("u-hr-01", "r-hr-pay"),
        ("u-hr-01", "r-hr-maint"),    # SoD violation!
        # Anna Lee -- SD
        ("u-sd-01", "r-sd-order"),
        ("u-sd-01", "r-sd-bill"),     # SoD violation!
        # Frank Controller -- AP Full (super-user risk)
        ("u-ff-01", "r-fi-ap-full"),
        ("u-ff-01", "r-basis-all"),   # SoD violation: super-user!
        # David Kim -- security admin
        ("u-sec-01", "r-bc-useradm"),
    ]
    count = 0
    for uid_str, rid_str in assignments:
        u_int = user_pk.get(uid_str)
        r_int = role_pk.get(rid_str)
        if u_int is None or r_int is None:
            continue
        try:
            db.execute(text("""
                INSERT INTO user_roles (tenant_id, user_id, role_id, assigned_by,
                    assigned_at, is_active, created_at, updated_at)
                VALUES (:tid, :uid, :rid, 'acme_admin',
                    :now, true, :now, :now)
            """), {"tid": TID, "uid": u_int, "rid": r_int, "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR assignment {uid_str}/{rid_str}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} user-role assignments")
    except Exception as e:
        db.rollback()
        print(f"  ERR assignments commit: {e}")

    # =========================================================
    # 5. SoD VIOLATIONS (integer user FK)
    # =========================================================
    print("\n[5/30] Creating SoD violations...")
    violations = [
        ("v-001", "u-ap-01",  "john.smith",   "SOD-FI-001", "AP Create + AP Approve",       "FI", "critical", 95,
         ["AP_CREATE","AP_APPROVE"], "Vendor payment fraud exposure"),
        ("v-002", "u-ar-01",  "sarah.jones",  "SOD-FI-003", "AP Create + GL Posting",        "FI", "high",    75,
         ["AP_CREATE","GL_POST"],    "Fictitious invoice + GL manipulation"),
        ("v-003", "u-mm-01",  "mike.chen",    "SOD-MM-001", "PO Create + GR Post + Vendor",  "MM", "critical", 90,
         ["PO_CREATE","GR_POST","VENDOR_CREATE"], "Full P2P cycle control bypass"),
        ("v-004", "u-tr-01",  "lisa.wang",    "SOD-FI-005", "Treasury + GL",                 "FI", "critical", 88,
         ["TR_PAYMENT","GL_POST"],  "Treasury self-approving payments"),
        ("v-005", "u-hr-01",  "tom.brown",    "SOD-HR-001", "Payroll Run + HR Maintain",     "HR", "critical", 92,
         ["HR_PAYROLL","HR_MAINT"], "Ghost employee + payroll fraud"),
        ("v-006", "u-sd-01",  "anna.lee",     "SOD-SD-001", "Order Create + Billing",        "SD", "high",    70,
         ["SO_CREATE","SD_BILL"],   "Unauthorized revenue booking"),
        ("v-007", "u-ff-01",  "frank.controller","SOD-BC-001","Super-user + AP Full",        "BC", "critical", 99,
         ["SAP_ALL","AP_FULL"],     "Unrestricted system access"),
        ("v-008", "u-hr-01",  "tom.brown",    "SOD-HR-002", "Dual HR control bypass",        "HR", "high",    80,
         ["HR_PAYROLL","HR_MAINT"], "HR data integrity risk"),
    ]
    count = 0
    for vid, uid_str, uname, rule_id, rule_name, cat, sev, score, funcs, impact in violations:
        u_int = user_pk.get(uid_str)
        if u_int is None:
            continue
        try:
            db.execute(text("""
                INSERT INTO risk_violations (tenant_id, violation_id, rule_id, rule_name, rule_type,
                    user_id, user_external_id, username, severity, severity_score, risk_category,
                    conflicting_functions, business_impact, status, detected_at, detected_by,
                    is_mitigated, created_at, updated_at)
                VALUES (:tid, :vid, :rid, :rn, 'sod', :uid, :uext, :un,
                    :sev, :score, :cat, :funcs, :impact,
                    'open', :det, 'system',
                    false, :now, :now)
            """), {
                "tid": TID, "vid": vid, "rid": rule_id, "rn": rule_name,
                "uid": u_int, "uext": uid_str, "un": uname,
                "sev": sev, "score": score, "cat": cat,
                "funcs": json.dumps(funcs), "impact": impact,
                "det": dt(days=14), "now": NOW,
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR violation {vid}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} violations")
    except Exception as e:
        db.rollback()
        print(f"  ERR violations commit: {e}")

    # =========================================================
    # 6. ORG UNITS (hierarchical, integer PKs)
    # =========================================================
    print("\n[6/30] Creating org units...")
    # Insert top-level first (no parent)
    top_ous = [
        ("ou-corp",   "Acme Corporation", "company",    1),
        ("ou-fin",    "Finance",          "department", 2),
        ("ou-ops",    "Operations",       "department", 2),
        ("ou-it",     "Information Technology","department",2),
        ("ou-hr",     "Human Resources",  "department", 2),
        ("ou-sales",  "Sales",            "department", 2),
    ]
    child_ous = [
        # (unit_id, name, type, level, parent_unit_id_str)
        ("ou-ap",    "Accounts Payable",       "team", 3, "ou-fin"),
        ("ou-ar",    "Accounts Receivable",    "team", 3, "ou-fin"),
        ("ou-gl",    "General Ledger",         "team", 3, "ou-fin"),
        ("ou-treas", "Treasury",               "team", 3, "ou-fin"),
    ]
    count = 0
    # Top-level (no parent)
    for uid_str, name, utype, level in top_ous:
        try:
            row = db.execute(text("""
                INSERT INTO org_units (tenant_id, unit_id, name, unit_type, level,
                    is_active, created_at, updated_at)
                VALUES (:tid, :uid, :name, :utype, :level,
                    true, :now, :now)
                RETURNING id
            """), {"tid": TID, "uid": uid_str, "name": name,
                   "utype": utype, "level": level, "now": NOW}).fetchone()
            ou_pk[uid_str] = row[0]
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR org_unit {name}: {e}")
    # Children
    for uid_str, name, utype, level, parent_str in child_ous:
        parent_int = ou_pk.get(parent_str)
        try:
            row = db.execute(text("""
                INSERT INTO org_units (tenant_id, unit_id, name, unit_type, level,
                    parent_id, is_active, created_at, updated_at)
                VALUES (:tid, :uid, :name, :utype, :level,
                    :pid, true, :now, :now)
                RETURNING id
            """), {"tid": TID, "uid": uid_str, "name": name,
                   "utype": utype, "level": level, "pid": parent_int, "now": NOW}).fetchone()
            ou_pk[uid_str] = row[0]
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR org_unit child {name}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} org units")
    except Exception as e:
        db.rollback()
        print(f"  ERR org units commit: {e}")

    # =========================================================
    # 7. ENTERPRISE RISKS
    # =========================================================
    print("\n[7/30] Creating enterprise risk register...")
    risks = [
        ("risk-001", "Segregation of Duties Breakdown in P2P",
         "operational", "ou-fin", "u-risk-01", 4, 5, 20.0, 2, 4, 8.0, "open"),
        ("risk-002", "Insider Threat via Privileged Access",
         "cybersecurity", "ou-it", "u-ciso-01", 4, 5, 20.0, 3, 4, 12.0, "open"),
        ("risk-003", "Payroll Fraud via HR System Manipulation",
         "fraud", "ou-hr", "u-risk-01", 3, 5, 15.0, 2, 4, 8.0, "open"),
        ("risk-004", "ERP Data Integrity Failure",
         "technology", "ou-it", "u-ciso-01", 3, 4, 12.0, 2, 3, 6.0, "open"),
        ("risk-005", "Vendor Master Data Tampering",
         "fraud", "ou-ops", "u-risk-01", 3, 4, 12.0, 2, 3, 6.0, "in_progress"),
        ("risk-006", "Regulatory Compliance Failure (SOX)",
         "compliance", "ou-fin", "u-comp-01", 2, 5, 10.0, 1, 4, 4.0, "open"),
        ("risk-007", "Business Continuity Risk - IT Outage",
         "operational", "ou-it", "u-ciso-01", 3, 4, 12.0, 2, 3, 6.0, "open"),
        ("risk-008", "Third-Party Vendor Security Breach",
         "cybersecurity", "ou-ops", "u-risk-01", 3, 4, 12.0, 2, 3, 6.0, "open"),
    ]
    count = 0
    for rid, title, cat, ou_str, owner_str, il, ii, isc, rl, ri, rsc, status in risks:
        ou_int = ou_pk.get(ou_str)
        owner_uid = owner_str  # store as string user_id
        try:
            row = db.execute(text("""
                INSERT INTO enterprise_risks (tenant_id, risk_id, title, category,
                    org_unit_id, risk_owner_id, risk_owner_name,
                    inherent_likelihood, inherent_impact, inherent_score,
                    residual_likelihood, residual_impact, residual_score,
                    risk_appetite, status, last_assessed_at, next_review_date,
                    created_at, updated_at)
                VALUES (:tid, :rid, :title, :cat,
                    :ouid, :owner, :oname,
                    :il, :ii, :isc,
                    :rl, :ri, :rsc,
                    5.0, :status, :now, :next,
                    :now, :now)
                RETURNING id
            """), {
                "tid": TID, "rid": rid, "title": title, "cat": cat,
                "ouid": ou_int, "owner": owner_uid,
                "oname": next((u[2] for u in users_data if u[0] == owner_str), owner_str),
                "il": il, "ii": ii, "isc": isc,
                "rl": rl, "ri": ri, "rsc": rsc,
                "status": status, "now": NOW, "next": dt(days=-90),
            }).fetchone()
            risk_pk[rid] = row[0]
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR risk {rid}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} enterprise risks")
    except Exception as e:
        db.rollback()
        print(f"  ERR risks commit: {e}")

    # =========================================================
    # 8. KEY RISK INDICATORS
    # =========================================================
    print("\n[8/30] Creating KRIs...")
    kris = [
        ("kri-001", "SoD Violation Count",       "risk-001", "violations",  10, 20, 30, 23, "breach"),
        ("kri-002", "Privileged User Count",      "risk-002", "users",       5,  10, 15, 8,  "amber"),
        ("kri-003", "Failed Login Attempts",      "risk-002", "events",      50, 100, 200, 45, "green"),
        ("kri-004", "Overdue Access Reviews",     "risk-001", "reviews",     0,  5,  10, 7,  "amber"),
        ("kri-005", "Unresolved Critical Findings","risk-006","findings",    0,  2,  5,  4,  "amber"),
        ("kri-006", "Vendor Risk Score (Avg)",    "risk-008", "score",       30, 50, 70, 62, "amber"),
    ]
    count = 0
    for kid, name, risk_str, unit, tg, ta, tr, val, status in kris:
        risk_int = risk_pk.get(risk_str)
        try:
            db.execute(text("""
                INSERT INTO key_risk_indicators (tenant_id, kri_id, name, risk_id,
                    unit_of_measure, frequency, threshold_green, threshold_amber, threshold_red,
                    current_value, last_measured_at, status, is_active,
                    created_at, updated_at)
                VALUES (:tid, :kid, :name, :rid,
                    :unit, 'monthly', :tg, :ta, :tr,
                    :val, :now, :status, true,
                    :now, :now)
            """), {
                "tid": TID, "kid": kid, "name": name, "rid": risk_int,
                "unit": unit, "tg": tg, "ta": ta, "tr": tr,
                "val": val, "status": status, "now": NOW,
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR kri {kid}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} KRIs")
    except Exception as e:
        db.rollback()
        print(f"  ERR KRI commit: {e}")

    # =========================================================
    # 9. RISK APPETITES
    # =========================================================
    print("\n[9/30] Creating risk appetite statements...")
    appetites = [
        ("operational",  "ou-fin",  3.0, 5.0),
        ("cybersecurity","ou-it",   2.0, 4.0),
        ("fraud",        "ou-fin",  1.0, 3.0),
        ("compliance",   "ou-fin",  1.0, 2.0),
        ("technology",   "ou-it",   4.0, 6.0),
    ]
    count = 0
    for cat, ou_str, appetite, tolerance in appetites:
        ou_int = ou_pk.get(ou_str)
        try:
            db.execute(text("""
                INSERT INTO risk_appetites (tenant_id, category, org_unit_id,
                    appetite_score, tolerance_score, description,
                    approved_by, approved_at, effective_from,
                    created_at, updated_at)
                VALUES (:tid, :cat, :ouid,
                    :app, :tol, :desc,
                    'Board of Directors', :now, :eff,
                    :now, :now)
            """), {
                "tid": TID, "cat": cat, "ouid": ou_int,
                "app": appetite, "tol": tolerance,
                "desc": f"Board-approved risk appetite for {cat} risk category",
                "now": NOW, "eff": dt(days=365),
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR appetite {cat}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} risk appetite statements")
    except Exception as e:
        db.rollback()
        print(f"  ERR appetites commit: {e}")

    # =========================================================
    # 10. RISK INCIDENTS
    # =========================================================
    print("\n[10/30] Creating risk incidents...")
    incidents = [
        ("inc-001", "Unauthorized Vendor Payment",       "risk-001", "critical", 250000.0, dt(30)),
        ("inc-002", "Employee Payroll Overpayment",      "risk-003", "high",     45000.0,  dt(60)),
        ("inc-003", "ERP Access Control Misconfiguration","risk-002","medium",   0.0,      dt(14)),
    ]
    count = 0
    for iid, title, risk_str, sev, fin, occurred in incidents:
        risk_int = risk_pk.get(risk_str)
        try:
            db.execute(text("""
                INSERT INTO risk_incidents (tenant_id, incident_id, title, risk_id,
                    severity, financial_impact, currency,
                    occurred_at, detected_at, root_cause,
                    status, reported_by, created_at, updated_at)
                VALUES (:tid, :iid, :title, :rid,
                    :sev, :fin, 'AUD',
                    :occ, :det, :cause,
                    'under_review', 'acme_auditor', :now, :now)
            """), {
                "tid": TID, "iid": iid, "title": title, "rid": risk_int,
                "sev": sev, "fin": fin,
                "occ": occurred, "det": occurred + datetime.timedelta(days=2),
                "cause": "Control breakdown identified during routine review",
                "now": NOW,
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR incident {iid}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} risk incidents")
    except Exception as e:
        db.rollback()
        print(f"  ERR incidents commit: {e}")

    # =========================================================
    # 11. PROCESS CONTROLS
    # =========================================================
    print("\n[11/30] Creating process controls...")
    controls = [
        ("ctrl-001", "Segregation of Duties - P2P",
         "preventive", "automated", "continuous", "ou-fin",
         "Finance - Accounts Payable", "Purchase-to-Pay"),
        ("ctrl-002", "Payment Dual Approval Control",
         "preventive", "manual", "transaction", "ou-fin",
         "Finance - Treasury",        "Cash Management"),
        ("ctrl-003", "Vendor Master Change Authorization",
         "preventive", "manual", "weekly",      "ou-ops",
         "Procurement",               "Vendor Management"),
        ("ctrl-004", "Payroll Review and Approval",
         "detective", "manual", "monthly",     "ou-hr",
         "Human Resources",            "Payroll Processing"),
        ("ctrl-005", "ERP User Access Review",
         "detective", "manual", "quarterly",   "ou-it",
         "IT Security",               "Access Management"),
        ("ctrl-006", "Journal Entry Review",
         "detective", "manual", "monthly",     "ou-fin",
         "Finance - General Ledger",  "Financial Reporting"),
        ("ctrl-007", "System Integrity Monitoring",
         "detective", "automated", "continuous","ou-it",
         "IT Operations",             "IT Controls"),
        ("ctrl-008", "Third-Party Security Assessment",
         "detective", "manual", "annual",      "ou-ops",
         "Procurement",               "Vendor Management"),
    ]
    count = 0
    for cid, name, ctype, cnature, freq, ou_str, proc, subproc in controls:
        ou_int = ou_pk.get(ou_str)
        try:
            row = db.execute(text("""
                INSERT INTO process_controls (tenant_id, control_id, name,
                    control_type, control_nature, frequency,
                    org_unit_id, process_name, subprocess_name,
                    version, status, key_control, is_active,
                    created_at, updated_at)
                VALUES (:tid, :cid, :name,
                    :ct, :cn, :freq,
                    :ouid, :proc, :subproc,
                    1, 'active', true, true,
                    :now, :now)
                RETURNING id
            """), {
                "tid": TID, "cid": cid, "name": name,
                "ct": ctype, "cn": cnature, "freq": freq,
                "ouid": ou_int, "proc": proc, "subproc": subproc,
                "now": NOW,
            }).fetchone()
            ctrl_pk[cid] = row[0]
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR control {cid}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} process controls")
    except Exception as e:
        db.rollback()
        print(f"  ERR controls commit: {e}")

    # =========================================================
    # 12. CONTROL TESTS
    # =========================================================
    print("\n[12/30] Creating control tests...")
    ctests = [
        ("ct-001", "ctrl-001", "walkthrough", dt(30), dt(20), 25, 250, "effective",   0),
        ("ct-002", "ctrl-002", "sampling",    dt(45), dt(35), 30, 500, "effective",   1),
        ("ct-003", "ctrl-003", "inspection",  dt(60), dt(50), 20, 100, "ineffective", 5),
        ("ct-004", "ctrl-004", "reperformance",dt(30),dt(20),50,1200, "effective",   2),
        ("ct-005", "ctrl-005", "observation", dt(90), dt(75),100, 500, "ineffective", 12),
        ("ct-006", "ctrl-006", "sampling",    dt(30), dt(20), 30, 800, "effective",   1),
    ]
    count = 0
    for tid_str, cid_str, ttype, ps, pe, samp, pop, result, exc in ctests:
        ctrl_int = ctrl_pk.get(cid_str)
        if ctrl_int is None:
            continue
        try:
            row = db.execute(text("""
                INSERT INTO control_tests (tenant_id, test_id, control_id,
                    test_type, testing_period_start, testing_period_end,
                    sample_size, population_size, tester_name,
                    result, exceptions_found, status,
                    created_at, updated_at)
                VALUES (:tid, :testid, :ctrl,
                    :ttype, :ps, :pe,
                    :samp, :pop, 'Alan Auditor',
                    :result, :exc, 'completed',
                    :now, :now)
                RETURNING id
            """), {
                "tid": TID, "testid": tid_str, "ctrl": ctrl_int,
                "ttype": ttype, "ps": ps, "pe": pe,
                "samp": samp, "pop": pop,
                "result": result, "exc": exc, "now": NOW,
            }).fetchone()
            test_pk[tid_str] = row[0]
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR control test {tid_str}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} control tests")
    except Exception as e:
        db.rollback()
        print(f"  ERR control tests commit: {e}")

    # =========================================================
    # 13. CONTROL DEFICIENCIES
    # =========================================================
    print("\n[13/30] Creating control deficiencies...")
    deficiencies = [
        ("def-001", "ctrl-003", "ct-003", "Vendor change requests lack secondary approval",
         "significant", "Inadequate design", dt(30)),
        ("def-002", "ctrl-005", "ct-005", "Access review completion rate below 60%",
         "material", "Operational failure", dt(15)),
    ]
    count = 0
    for did, cid_str, tid_str, title, sev, cause, due in deficiencies:
        ctrl_int = ctrl_pk.get(cid_str)
        test_int = test_pk.get(tid_str)
        if ctrl_int is None:
            continue
        try:
            db.execute(text("""
                INSERT INTO control_deficiencies (tenant_id, deficiency_id,
                    control_id, test_id, source, title, description,
                    severity, root_cause, status, due_date,
                    created_at, updated_at)
                VALUES (:tid, :did,
                    :ctrl, :test, 'testing', :title, :title,
                    :sev, :cause, 'open', :due,
                    :now, :now)
            """), {
                "tid": TID, "did": did,
                "ctrl": ctrl_int, "test": test_int,
                "title": title, "sev": sev,
                "cause": cause, "due": due, "now": NOW,
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR deficiency {did}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} control deficiencies")
    except Exception as e:
        db.rollback()
        print(f"  ERR deficiencies commit: {e}")

    # =========================================================
    # 14. MITIGATION CONTROLS
    # =========================================================
    print("\n[14/30] Creating mitigation controls...")
    mitigations = [
        ("mit-001", "Compensating Control - AP SoD Monitor",
         "compensating", ["SOD-FI-001","SOD-FI-003"], "u-comp-01"),
        ("mit-002", "Manual Vendor Change Approval Log",
         "manual",       ["SOD-MM-001"],               "u-mgr-01"),
        ("mit-003", "Payroll Exception Report Review",
         "detective",    ["SOD-HR-001","SOD-HR-002"],   "u-mgr-01"),
        ("mit-004", "Treasury Payment Independent Verification",
         "preventive",   ["SOD-FI-005"],                "u-ciso-01"),
        ("mit-005", "Super-user Access Monitoring Log",
         "compensating", ["SOD-BC-001"],                "u-sec-01"),
    ]
    count = 0
    for cid, name, ctype, rules, owner_str in mitigations:
        try:
            db.execute(text("""
                INSERT INTO mitigation_controls (tenant_id, control_id, control_name,
                    control_type, applicable_rule_ids,
                    owner_user_id, owner_name,
                    is_active, valid_from,
                    created_at, updated_at)
                VALUES (:tid, :cid, :name,
                    :ctype, :rules,
                    :owner, :oname,
                    true, :now,
                    :now, :now)
            """), {
                "tid": TID, "cid": cid, "name": name,
                "ctype": ctype, "rules": json.dumps(rules),
                "owner": owner_str,
                "oname": next((u[2] for u in users_data if u[0] == owner_str), owner_str),
                "now": NOW,
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR mitigation {cid}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} mitigation controls")
    except Exception as e:
        db.rollback()
        print(f"  ERR mitigations commit: {e}")

    # =========================================================
    # 15. FIREFIGHTER REQUESTS + SESSIONS
    # =========================================================
    print("\n[15/30] Creating firefighter data...")
    ff_requests = [
        ("ff-req-001", "u-ff-01",  "frank.controller", "frank_controller@acmecorp.com",
         "Finance", "SAP_ECC", "ff-001", "Year-end close critical batch job failure", 240),
        ("ff-req-002", "u-sec-01", "david.kim",         "david_kim@acmecorp.com",
         "IT Security", "SAP_ECC", "ff-002", "Security patch deployment requires elevated access", 120),
        ("ff-req-003", "u-admin-01","acme_admin",       "acme_admin@acmecorp.com",
         "IT", "SAP_S4H", "ff-001", "Critical system configuration change for month-end", 60),
        ("ff-req-004", "u-ff-01",  "frank.controller", "frank_controller@acmecorp.com",
         "Finance", "SAP_ECC", "ff-001", "Emergency vendor payment processing", 180),
    ]
    req_count = 0
    for req_id, uid_str, uname, email, dept, sys, ff_id, reason, dur in ff_requests:
        status = "approved" if req_id in ("ff-req-001", "ff-req-002") else "pending"
        try:
            db.execute(text("""
                INSERT INTO firefighter_requests (tenant_id, request_id,
                    requester_user_id, requester_name, requester_email, requester_department,
                    target_system, firefighter_id, reason, business_justification,
                    requested_duration_minutes, status, priority,
                    created_at, updated_at)
                VALUES (:tid, :req,
                    :uid, :uname, :email, :dept,
                    :sys, :ff, :reason, :reason,
                    :dur, :status, 'high',
                    :now, :now)
            """), {
                "tid": TID, "req": req_id,
                "uid": uid_str, "uname": uname, "email": email, "dept": dept,
                "sys": sys, "ff": ff_id, "reason": reason,
                "dur": dur, "status": status, "now": NOW,
            })
            req_count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR FF request {req_id}: {e}")
    # One active session
    sess_count = 0
    try:
        db.execute(text("""
            INSERT INTO firefighter_sessions (tenant_id, session_id, request_id,
                requester_user_id, firefighter_id, target_system,
                start_time, scheduled_end_time, status, mfa_verified,
                reason, created_at, updated_at)
            VALUES (:tid, :sid, 'ff-req-001',
                'u-ff-01', 'ff-001', 'SAP_ECC',
                :start, :end, 'active', true,
                'Year-end close critical batch job failure', :now, :now)
        """), {
            "tid": TID, "sid": f"ffs-{new_id()[:8]}",
            "start": dt(hours=2), "end": dt(hours=-2), "now": NOW,
        })
        sess_count = 1
    except Exception as e:
        db.rollback()
        print(f"    ERR FF session: {e}")
    try:
        db.commit()
        print(f"  OK: {req_count} FF requests, {sess_count} session")
    except Exception as e:
        db.rollback()
        print(f"  ERR FF commit: {e}")

    # =========================================================
    # 16. CERTIFICATION CAMPAIGNS
    # =========================================================
    print("\n[16/30] Creating certification campaigns...")
    campaigns = [
        ("camp-001", "Q4 2026 Full Access Review",
         "user_access", "in_progress", "u-comp-01", "Carl Compliance",
         dt(30), dt(days=-30), 350, 280, 210, 70),
        ("camp-002", "Critical SoD Violations Review",
         "sod_violations", "completed", "u-ciso-01", "Clara CISO",
         dt(90), dt(60), 45, 45, 38, 7),
        ("camp-003", "SAP Super-User Access Review",
         "privileged_access", "planning", "u-sec-01", "David Kim",
         dt(days=-7), dt(days=-37), 12, 0, 0, 0),
    ]
    count = 0
    for cid, name, ctype, status, oid, oname, start, end, total, comp, cert, rev in campaigns:
        try:
            db.execute(text("""
                INSERT INTO certification_campaigns (tenant_id, campaign_id, name, description,
                    campaign_type, status, owner_id, owner_name,
                    start_date, end_date,
                    total_items, completed_items, certified_count, revoked_count,
                    included_systems, included_departments, risk_threshold,
                    created_at)
                VALUES (:tid, :cid, :name, :name,
                    :ctype, :status, :oid, :oname,
                    :start, :end,
                    :total, :comp, :cert, :rev,
                    :systems, :depts, 70,
                    :now)
            """), {
                "tid": TID, "cid": cid, "name": name,
                "ctype": ctype, "status": status,
                "oid": oid, "oname": oname,
                "start": start, "end": end,
                "total": total, "comp": comp, "cert": cert, "rev": rev,
                "systems": json.dumps(["SAP_ECC", "SAP_S4H"]),
                "depts": json.dumps(["Finance", "HR", "IT", "Operations"]),
                "now": NOW,
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR campaign {cid}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} certification campaigns")
    except Exception as e:
        db.rollback()
        print(f"  ERR campaigns commit: {e}")

    # =========================================================
    # 17. AUDIT MANAGEMENT
    # =========================================================
    print("\n[17/30] Creating audit management data...")
    # Audit Plan
    plan_pk_val = None
    try:
        row = db.execute(text("""
            INSERT INTO audit_plans (tenant_id, plan_id, name, description,
                plan_type, fiscal_year, period_start, period_end,
                total_audit_hours, allocated_budget, status,
                prepared_by, created_at, updated_at)
            VALUES (:tid, 'ap-2026', 'FY2026 Internal Audit Plan',
                'Annual risk-based internal audit plan covering all key business processes',
                'annual', 2026, :start, :end,
                2400, 480000.0, 'approved',
                'acme_auditor', :now, :now)
            RETURNING id
        """), {
            "tid": TID, "start": dt(days=365), "end": dt(days=-365), "now": NOW,
        }).fetchone()
        plan_pk_val = row[0]
        plan_pk = plan_pk_val
        print("  OK: 1 audit plan")
    except Exception as e:
        db.rollback()
        print(f"    ERR audit plan: {e}")

    # Audit Engagement
    eng_pk_val = None
    if plan_pk_val:
        try:
            row = db.execute(text("""
                INSERT INTO audit_engagements (tenant_id, engagement_id, plan_id,
                    title, objective, scope,
                    engagement_type, status,
                    lead_auditor_id, lead_auditor_name,
                    team_members, planned_start, planned_end,
                    budget_hours, risk_rating,
                    created_at, updated_at)
                VALUES (:tid, 'eng-001', :plan,
                    'ERP Access Control & SoD Audit',
                    'Evaluate the design and operating effectiveness of access controls and SoD policies in SAP ECC',
                    'Finance, HR, IT departments; SAP ECC and S/4HANA systems',
                    'performance', 'fieldwork',
                    'acme_auditor', 'Alan Auditor',
                    :team, :start, :end,
                    320, 'high',
                    :now, :now)
                RETURNING id
            """), {
                "tid": TID, "plan": plan_pk_val,
                "team": json.dumps(["Alan Auditor", "Clara CISO"]),
                "start": dt(days=30), "end": dt(days=-7), "now": NOW,
            }).fetchone()
            eng_pk_val = row[0]
            eng_pk["eng-001"] = eng_pk_val
            print("  OK: 1 audit engagement")
        except Exception as e:
            db.rollback()
            print(f"    ERR engagement: {e}")

    # Audit Findings
    findings_count = 0
    if eng_pk_val:
        findings = [
            ("af-001", "Critical SoD Violation - AP Create + Approve",
             "John Smith has both AP invoice creation and payment approval rights",
             "SOX Section 404 requires SoD in all payment processes",
             "Rapid user provisioning without SoD analysis",
             "Unauthorized payments totalling ~AUD 250K processed in Q3",
             "Immediately revoke AP Approve role from John Smith",
             "critical", "Access Control"),
            ("af-002", "User Access Review Overdue by 45 Days",
             "Quarterly access review not completed within required timeframe",
             "IT Security Policy requires quarterly access certification",
             "Lack of automated workflow and reviewer accountability",
             "12 users retain access to systems from prior roles",
             "Implement automated campaign workflow with escalation",
             "high", "Access Management"),
            ("af-003", "Vendor Master Changes Without Dual Approval",
             "5 vendor bank account changes made without secondary approval",
             "Fraud prevention policy requires dual authorization",
             "Control breakdown in vendor change process",
             "Potential for fraudulent payment diversion",
             "Implement system-enforced dual approval for vendor changes",
             "high", "Vendor Management"),
        ]
        for fid, title, condition, criteria, cause, effect, rec, sev, cat in findings:
            try:
                db.execute(text("""
                    INSERT INTO audit_findings (tenant_id, finding_id, engagement_id,
                        title, condition, criteria, cause, effect, recommendation,
                        severity, category, status,
                        created_at, updated_at)
                    VALUES (:tid, :fid, :eng,
                        :title, :cond, :crit, :cause, :effect, :rec,
                        :sev, :cat, 'open',
                        :now, :now)
                """), {
                    "tid": TID, "fid": fid, "eng": eng_pk_val,
                    "title": title, "cond": condition, "crit": criteria,
                    "cause": cause, "effect": effect, "rec": rec,
                    "sev": sev, "cat": cat, "now": NOW,
                })
                findings_count += 1
            except Exception as e:
                db.rollback()
                print(f"    ERR finding {fid}: {e}")
    try:
        db.commit()
        print(f"  OK: {findings_count} audit findings")
    except Exception as e:
        db.rollback()
        print(f"  ERR audit commit: {e}")

    # =========================================================
    # 18. JML POLICIES + EVENTS
    # =========================================================
    print("\n[18/30] Creating JML policies and events...")
    jml_policies = [
        (new_id(), "New Hire Provisioning - Finance",
         "JOINER", "Finance",
         ["Z_FI_AP_CREATE", "Z_FI_GL_POST"],
         ["{"action": "provision_roles", "roles": ["r-fi-ap-crt"]}'"]),
        (new_id(), "New Hire Provisioning - IT",
         "JOINER", "IT",
         ["Z_BC_USER_ADMIN"],
         []),
        (new_id(), "Leaver Deprovisioning",
         "LEAVER", None,
         [],
         []),
        (new_id(), "Internal Transfer - Role Review",
         "MOVER", None,
         [],
         []),
    ]
    # Simplified - just insert basic fields
    pol_ids = []
    pol_count = 0
    for pid, name, etype, org, roles, actions in [
        (new_id(), "New Hire Provisioning - Finance", "JOINER", "Finance",  ["Z_FI_AP_CREATE"], [{"action":"provision"}]),
        (new_id(), "New Hire Provisioning - IT",      "JOINER", "IT",       ["Z_BC_USER_ADMIN"],[{"action":"provision"}]),
        (new_id(), "Leaver Deprovisioning",            "LEAVER", None,       [],                 [{"action":"deprovision"}]),
        (new_id(), "Internal Transfer - Role Review",  "MOVER",  None,       [],                 [{"action":"review"}]),
    ]:
        try:
            db.execute(text("""
                INSERT INTO jml_policies (id, tenant_id, policy_name, description,
                    event_type, org_unit, birthright_roles, actions, is_active,
                    created_by, created_at, updated_at)
                VALUES (:id, :tid, :name, :name,
                    :etype, :org, :roles, :actions, true,
                    'acme_admin', :now, :now)
            """), {
                "id": pid, "tid": TID, "name": name,
                "etype": etype, "org": org,
                "roles": json.dumps(roles), "actions": json.dumps(actions),
                "now": NOW,
            })
            pol_ids.append(pid)
            pol_count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR JML policy: {e}")

    ev_count = 0
    jml_events = [
        (new_id(), "JOINER", "EMP-2026-101", "James Wilson",   None,         "Finance Analyst",   "Finance",
         dt(7), pol_ids[0] if pol_ids else None, "completed"),
        (new_id(), "JOINER", "EMP-2026-102", "Emma Thompson",  None,         "IT Security Analyst","IT",
         dt(14), pol_ids[1] if len(pol_ids)>1 else None, "completed"),
        (new_id(), "LEAVER", "EMP-2023-055", "Robert Davis",   "AP Analyst", None,                None,
         dt(3), pol_ids[2] if len(pol_ids)>2 else None, "completed"),
        (new_id(), "MOVER",  "EMP-2021-033", "Jennifer Clark", "AR Analyst", "AP Manager",        "Finance",
         dt(21), pol_ids[3] if len(pol_ids)>3 else None, "pending"),
    ]
    for eid, etype, emp_id, emp_name, old_pos, new_pos, new_org, eff, pol_id, status in jml_events:
        try:
            db.execute(text("""
                INSERT INTO jml_events (id, tenant_id, event_type,
                    employee_id, employee_name, old_position, new_position,
                    new_org_unit, effective_date, hr_system,
                    status, matched_policy_id, actions_taken,
                    created_at, updated_at)
                VALUES (:id, :tid, :etype,
                    :empid, :empname, :oldpos, :newpos,
                    :neworg, :eff, 'Workday',
                    :status, :polid, :actions,
                    :now, :now)
            """), {
                "id": eid, "tid": TID, "etype": etype,
                "empid": emp_id, "empname": emp_name,
                "oldpos": old_pos, "newpos": new_pos,
                "neworg": new_org, "eff": eff, "polid": pol_id,
                "status": status,
                "actions": json.dumps([{"action": "roles_reviewed", "result": "completed"}]),
                "now": NOW,
            })
            ev_count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR JML event: {e}")
    try:
        db.commit()
        print(f"  OK: {pol_count} JML policies, {ev_count} events")
    except Exception as e:
        db.rollback()
        print(f"  ERR JML commit: {e}")

    # =========================================================
    # 19. TPRM VENDORS
    # =========================================================
    print("\n[19/30] Creating TPRM vendors...")
    v_ids = [new_id() for _ in range(6)]
    vendors_data = [
        (v_ids[0], "CloudSecure Pty Ltd",    "VEN-001", 1, 72.5, "Technology - Cloud Security"),
        (v_ids[1], "DataVault Solutions",    "VEN-002", 1, 68.0, "Data Management"),
        (v_ids[2], "Apex Consulting Group",  "VEN-003", 2, 55.0, "Professional Services"),
        (v_ids[3], "TechBridge IT Services", "VEN-004", 2, 61.0, "IT Services"),
        (v_ids[4], "Pinnacle Payroll Co",    "VEN-005", 1, 78.0, "Payroll Services"),
        (v_ids[5], "Global Logistics Ltd",   "VEN-006", 3, 42.0, "Logistics"),
    ]
    v_count = 0
    for vid, vname, vcode, tier, rscore, services in vendors_data:
        try:
            db.execute(text("""
                INSERT INTO vendors (id, tenant_id, vendor_name, vendor_code,
                    tier, status, risk_score,
                    primary_contact, contact_email, country,
                    services_provided,
                    last_assessment_date, next_assessment_date,
                    created_at, updated_at)
                VALUES (:id, :tid, :name, :code,
                    :tier, 'active', :rscore,
                    'Primary Contact', :email, 'Australia',
                    :services,
                    :last, :next,
                    :now, :now)
            """), {
                "id": vid, "tid": TID, "name": vname, "code": vcode,
                "tier": tier, "rscore": rscore,
                "email": f"contact@{vname.lower().replace(' ','-')[:20]}.com",
                "services": json.dumps([services]),
                "last": dt(days=90), "next": dt(days=-275), "now": NOW,
            })
            v_count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR vendor {vname}: {e}")

    # One assessment
    assess_id = new_id()
    a_count = 0
    if v_ids:
        try:
            db.execute(text("""
                INSERT INTO vendor_assessments (id, tenant_id, vendor_id,
                    assessment_name, status, sent_date, due_date,
                    overall_score, risk_rating, assessor,
                    created_at, updated_at)
                VALUES (:id, :tid, :vid,
                    'Annual Security Assessment 2026', 'completed', :sent, :due,
                    72.5, 'medium', 'acme_compliance',
                    :now, :now)
            """), {
                "id": assess_id, "tid": TID, "vid": v_ids[0],
                "sent": dt(days=90), "due": dt(days=60), "now": NOW,
            })
            a_count = 1
        except Exception as e:
            db.rollback()
            print(f"    ERR vendor assessment: {e}")

    # One issue
    i_count = 0
    if v_ids:
        try:
            db.execute(text("""
                INSERT INTO vendor_issues (id, tenant_id, vendor_id,
                    issue_title, description, severity, status,
                    due_date, owner, created_at, updated_at)
                VALUES (:id, :tid, :vid,
                    'MFA Not Enforced on Vendor Portal',
                    'Vendor does not enforce MFA for admin users accessing shared systems',
                    'high', 'open',
                    :due, 'acme_ciso', :now, :now)
            """), {
                "id": new_id(), "tid": TID, "vid": v_ids[0],
                "due": dt(days=-30), "now": NOW,
            })
            i_count = 1
        except Exception as e:
            db.rollback()
            print(f"    ERR vendor issue: {e}")
    try:
        db.commit()
        print(f"  OK: {v_count} vendors, {a_count} assessment, {i_count} issue")
    except Exception as e:
        db.rollback()
        print(f"  ERR TPRM commit: {e}")

    # =========================================================
    # 20. FRAUD DETECTION
    # =========================================================
    print("\n[20/30] Creating fraud detection data...")
    fr_ids = [new_id() for _ in range(5)]
    fraud_rules_data = [
        (fr_ids[0], "Round-Trip Payment Detection",      "BEHAVIORAL",  85.0),
        (fr_ids[1], "Vendor Bank Account Change Pattern","THRESHOLD",   92.0),
        (fr_ids[2], "Ghost Employee Detection",          "STATISTICAL", 88.0),
        (fr_ids[3], "Duplicate Invoice Detection",       "THRESHOLD",   78.0),
        (fr_ids[4], "SoD Conflict + Transaction Spike",  "BEHAVIORAL",  95.0),
    ]
    r_count = 0
    for rid, rname, rtype, rscore in fraud_rules_data:
        try:
            db.execute(text("""
                INSERT INTO fraud_rules (id, tenant_id, rule_name, rule_type,
                    description, conditions, risk_score,
                    is_active, alert_on_breach,
                    created_by, created_at, updated_at)
                VALUES (:id, :tid, :name, :rtype,
                    :name, :cond, :score,
                    true, true,
                    'acme_ciso', :now, :now)
            """), {
                "id": rid, "tid": TID, "name": rname, "rtype": rtype,
                "cond": json.dumps({"type": rtype.lower(), "threshold": rscore}),
                "score": rscore, "now": NOW,
            })
            r_count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR fraud rule: {e}")

    # Fraud alerts
    al_ids = [new_id() for _ in range(4)]
    a_count = 0
    fraud_alerts_data = [
        (al_ids[0], fr_ids[0], "Round-trip payment pattern - John Smith", 85.0, "open"),
        (al_ids[1], fr_ids[1], "Vendor bank account changed 3x in 7 days", 92.0, "investigating"),
        (al_ids[2], fr_ids[4], "SoD user transaction spike - Frank Controller", 95.0, "open"),
        (al_ids[3], fr_ids[2], "Payroll entry without corresponding HR record", 88.0, "closed"),
    ]
    for aid, rule_id, desc, score, status in fraud_alerts_data:
        try:
            db.execute(text("""
                INSERT INTO fraud_alerts (id, tenant_id, rule_id,
                    user_id, alert_type, description, risk_score, status,
                    triggered_at, created_at)
                VALUES (:id, :tid, :rid,
                    'john.smith', 'behavioral_anomaly', :desc, :score, :status,
                    :now, :now)
            """), {
                "id": aid, "tid": TID, "rid": rule_id,
                "desc": desc, "score": score, "status": status, "now": dt(days=7),
            })
            a_count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR fraud alert: {e}")

    # One fraud case
    case_count = 0
    try:
        db.execute(text("""
            INSERT INTO fraud_cases (id, tenant_id, case_reference, title,
                description, severity, status, assigned_to,
                linked_alert_ids, opened_at, loss_amount, created_at, updated_at)
            VALUES (:id, :tid, 'FC-2026-001', 'Suspected Vendor Fraud - Acme P2P',
                'Multiple indicators of vendor payment fraud detected in P2P cycle',
                'high', 'investigating', 'acme_compliance',
                :alerts, :opened, 250000.0, :now, :now)
        """), {
            "id": new_id(), "tid": TID,
            "alerts": json.dumps([al_ids[0], al_ids[1]]),
            "opened": dt(days=14), "now": NOW,
        })
        case_count = 1
    except Exception as e:
        db.rollback()
        print(f"    ERR fraud case: {e}")
    try:
        db.commit()
        print(f"  OK: {r_count} fraud rules, {a_count} alerts, {case_count} case")
    except Exception as e:
        db.rollback()
        print(f"  ERR fraud commit: {e}")

    # =========================================================
    # 21. BCM DATA
    # =========================================================
    print("\n[21/30] Creating BCM data...")
    bia_count = 0
    bia_data = [
        ("SAP ECC - Accounts Payable", 4, 0.5, 24.0),
        ("SAP ECC - Payroll Processing", 5, 0.0, 4.0),
        ("Treasury - Payment Processing", 5, 0.0, 2.0),
        ("HR - Employee Onboarding", 3, 24.0, 72.0),
        ("Procurement - Purchase Orders", 4, 4.0, 48.0),
    ]
    for pname, crit, rpo, rto in bia_data:
        try:
            db.execute(text("""
                INSERT INTO bia_records (id, tenant_id, process_name, process_owner,
                    criticality, rto_hours, rpo_hours, mtpd_hours,
                    dependencies, recovery_strategy,
                    impact_description, last_reviewed, created_at, updated_at)
                VALUES (:id, :tid, :name, 'acme_risk',
                    :crit, :rto, :rpo, :mtpd,
                    :deps, 'Activate DR environment and failover procedures',
                    'Critical business process; outage impacts revenue and compliance',
                    :now, :now, :now)
            """), {
                "id": new_id(), "tid": TID, "name": pname,
                "crit": ["low","low","medium","high","critical"][crit-1],
                "rto": rto, "rpo": rpo, "mtpd": rto * 2,
                "deps": json.dumps(["SAP ECC", "Network", "Active Directory"]),
                "now": dt(days=45),
            })
            bia_count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR BIA {pname}: {e}")

    bcm_plan_ids = [new_id(), new_id(), new_id()]
    plan_count = 0
    bcm_plans_data = [
        (bcm_plan_ids[0], "IT Disaster Recovery Plan",             "DR",    "active"),
        (bcm_plan_ids[1], "Business Continuity Plan - Finance",    "BCP",   "active"),
        (bcm_plan_ids[2], "Crisis Management Plan",                "CRISIS","draft"),
    ]
    for pid, pname, ptype, pstatus in bcm_plans_data:
        try:
            db.execute(text("""
                INSERT INTO bcm_plans (id, tenant_id, plan_name, plan_type,
                    scope, owner, version, status,
                    last_tested, next_test_date,
                    call_tree, recovery_steps,
                    created_at, updated_at)
                VALUES (:id, :tid, :name, :ptype,
                    'All business-critical systems and processes', 'acme_risk',
                    '2.1', :status,
                    :last, :next,
                    :tree, :steps,
                    :now, :now)
            """), {
                "id": pid, "tid": TID, "name": pname, "ptype": ptype,
                "status": pstatus,
                "last": dt(days=90), "next": dt(days=-275),
                "tree": json.dumps([{"role":"CIO","contact":"cio@acmecorp.com"}]),
                "steps": json.dumps([{"step":1,"action":"Activate incident response"},
                                     {"step":2,"action":"Notify stakeholders"},
                                     {"step":3,"action":"Failover to DR site"}]),
                "now": NOW,
            })
            plan_count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR BCM plan {pname}: {e}")

    # BCM exercise
    ex_count = 0
    try:
        db.execute(text("""
            INSERT INTO bcm_test_exercises (id, tenant_id, plan_id,
                exercise_name, exercise_type, scheduled_date, completed_date,
                facilitator, participants, outcome, findings, lessons_learned,
                created_at, updated_at)
            VALUES (:id, :tid, :pid,
                'Q3 2026 DR Tabletop Exercise', 'TABLETOP', :sched, :comp,
                'acme_risk',
                :part, 'PASS',
                'All recovery procedures executed within RTO. Minor gaps in communication tree.',
                'Update call tree with current mobile numbers; Test actual failover annually',
                :now, :now)
        """), {
            "id": new_id(), "tid": TID, "pid": bcm_plan_ids[0],
            "sched": dt(days=90), "comp": dt(days=88),
            "part": json.dumps(["CIO","CFO","CISO","IT Operations"]),
            "now": dt(days=88),
        })
        ex_count = 1
    except Exception as e:
        db.rollback()
        print(f"    ERR BCM exercise: {e}")
    try:
        db.commit()
        print(f"  OK: {bia_count} BIA, {plan_count} BCM plans, {ex_count} exercise")
    except Exception as e:
        db.rollback()
        print(f"  ERR BCM commit: {e}")

    # =========================================================
    # 22. WHISTLEBLOWER CASES
    # =========================================================
    print("\n[22/30] Creating whistleblower cases...")
    wb_data = [
        ("WB-2026-001", "FINANCIAL_MISCONDUCT", "Suspected P2P Fraud",
         "Concerns raised about vendor payment patterns in Q3", "high", "investigating"),
        ("WB-2026-002", "ACCESS_CONTROL", "Unauthorized System Access",
         "Employee observed accessing restricted SAP transactions", "medium", "under_review"),
        ("WB-2026-003", "HR_MISCONDUCT", "Payroll Irregularities",
         "Unexplained payroll adjustments for terminated employees", "high", "closed"),
    ]
    count = 0
    for ref, cat, summary, details, priority, status in wb_data:
        try:
            db.execute(text("""
                INSERT INTO whistleblower_cases (id, tenant_id, case_reference,
                    category, submission_channel, summary, details,
                    submitted_at, is_anonymous, status,
                    assigned_to, priority, created_at, updated_at)
                VALUES (:id, :tid, :ref,
                    :cat, 'web_portal', :summary, :details,
                    :sub, true, :status,
                    'acme_compliance', :priority, :now, :now)
            """), {
                "id": new_id(), "tid": TID, "ref": ref,
                "cat": cat, "summary": summary, "details": details,
                "sub": dt(days=21), "status": status, "priority": priority, "now": NOW,
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR whistleblower {ref}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} whistleblower cases")
    except Exception as e:
        db.rollback()
        print(f"  ERR whistleblower commit: {e}")

    # =========================================================
    # 23. SURVEYS
    # =========================================================
    print("\n[23/30] Creating surveys...")
    surveys = [
        ("GRC Awareness Survey Q4 2026",
         "Measure employee awareness of GRC policies and controls",
         "AWARENESS", "active"),
        ("Access Control Policy Acknowledgment",
         "Annual acknowledgment of access control and acceptable use policies",
         "COMPLIANCE", "completed"),
        ("Risk Culture Assessment 2026",
         "Assess organizational risk culture and appetite understanding",
         "RISK_CULTURE", "draft"),
    ]
    count = 0
    for sname, sdesc, stype, sstatus in surveys:
        try:
            db.execute(text("""
                INSERT INTO standalone_surveys (id, tenant_id, survey_name, description,
                    survey_type, status, created_by, survey_created_at,
                    due_date, allow_anonymous, questions,
                    created_at, updated_at)
                VALUES (:id, :tid, :name, :desc,
                    :stype, :status, 'acme_compliance', :now,
                    :due, true,
                    :questions,
                    :now, :now)
            """), {
                "id": new_id(), "tid": TID, "name": sname, "desc": sdesc,
                "stype": stype, "status": sstatus, "now": NOW,
                "due": dt(days=-30),
                "questions": json.dumps([
                    {"id": "q1", "text": "Do you understand your access control responsibilities?",
                     "type": "rating", "scale": 5},
                    {"id": "q2", "text": "Have you completed your mandatory GRC training?",
                     "type": "yes_no"},
                    {"id": "q3", "text": "Comments on risk management culture",
                     "type": "text"},
                ]),
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR survey {sname}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} surveys")
    except Exception as e:
        db.rollback()
        print(f"  ERR surveys commit: {e}")

    # =========================================================
    # 24. POLICY DOCUMENTS
    # =========================================================
    print("\n[24/30] Creating policy documents...")
    policies = [
        ("pol-001", "Information Security Policy",
         "security", "ISO27001-A.5", "approved"),
        ("pol-002", "Access Control Policy",
         "access", "ISO27001-A.9", "approved"),
        ("pol-003", "Segregation of Duties Policy",
         "governance", "SOX-ITGC-001", "approved"),
        ("pol-004", "Vendor Management Policy",
         "procurement", "ISO27001-A.15", "approved"),
        ("pol-005", "Business Continuity Policy",
         "continuity", "ISO22301", "under_review"),
        ("pol-006", "Data Protection & Privacy Policy",
         "privacy", "GDPR-Art5", "approved"),
        ("pol-007", "Change Management Policy",
         "technology", "ITIL-CHM", "draft"),
        ("pol-008", "Incident Response Policy",
         "security", "NIST-IR", "approved"),
    ]
    count = 0
    for pid, title, ptype, reg_id, status in policies:
        try:
            db.execute(text("""
                INSERT INTO policy_documents (tenant_id, policy_id, title, description,
                    policy_type, regulation_id, content, version, status,
                    author_name, approved_by, published_at, effective_date,
                    created_at, updated_at)
                VALUES (:tid, :pid, :title, :title,
                    :ptype, :reg, :content, 1, :status,
                    'Carl Compliance', 'Board of Directors', :pub, :eff,
                    :now, :now)
            """), {
                "tid": TID, "pid": pid, "title": title,
                "ptype": ptype, "reg": reg_id,
                "content": f"This policy establishes requirements for {title.lower()} "
                            f"across all Acme Corporation systems and processes.",
                "status": status, "pub": dt(days=180), "eff": dt(days=180), "now": NOW,
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR policy {pid}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} policy documents")
    except Exception as e:
        db.rollback()
        print(f"  ERR policies commit: {e}")

    # =========================================================
    # 25. NOTIFICATION PREFERENCES
    # =========================================================
    print("\n[25/30] Creating notification preferences...")
    notif_users = [
        ("u-admin-01", "acme_admin"),
        ("u-ciso-01",  "acme_ciso"),
        ("u-comp-01",  "acme_compliance"),
        ("u-risk-01",  "acme_risk"),
        ("u-audit-01", "acme_auditor"),
    ]
    count = 0
    for uid_str, uname in notif_users:
        try:
            db.execute(text("""
                INSERT INTO notification_preferences (tenant_id, user_id,
                    email_enabled, slack_enabled, slack_channel,
                    disabled_types, created_at, updated_at)
                VALUES (:tid, :uid,
                    true, false, :channel,
                    :disabled, :now, :now)
            """), {
                "tid": TID, "uid": uid_str,
                "channel": f"#grc-{uname}",
                "disabled": json.dumps([]),
                "now": NOW,
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR notification {uname}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} notification preferences")
    except Exception as e:
        db.rollback()
        print(f"  ERR notifications commit: {e}")

    # =========================================================
    # 26. SYNC CONFIGS
    # =========================================================
    print("\n[26/30] Creating system connectors...")
    syncs = [
        ("sync-sap-ecc", "SAP ECC 6.0",        "SAP_ECC",  "inbound",  15, "success", dt(hours=1)),
        ("sync-sap-s4h", "SAP S/4HANA 2023",   "SAP_S4H",  "inbound",  30, "success", dt(hours=1)),
        ("sync-workday",  "Workday HCM",        "WORKDAY",  "inbound",  60, "success", dt(hours=2)),
        ("sync-ad",       "Active Directory",   "LDAP",     "inbound",  5,  "success", dt(hours=0)),
    ]
    count = 0
    for cid, sname, stype, direction, sched, lstatus, lastsync in syncs:
        try:
            db.execute(text("""
                INSERT INTO sync_configs (tenant_id, config_id, system_name, system_type,
                    direction, status, schedule_minutes,
                    last_sync_at, last_sync_status, objects_synced,
                    sync_scope, connection_config, created_at, updated_at)
                VALUES (:tid, :cid, :sname, :stype,
                    :dir, 'active', :sched,
                    :lastsync, :lstatus, :objs,
                    :scope, :conn, :now, :now)
            """), {
                "tid": TID, "cid": cid, "sname": sname, "stype": stype,
                "dir": direction, "sched": sched,
                "lastsync": lastsync, "lstatus": lstatus,
                "objs": 1250 if stype in ("SAP_ECC", "SAP_S4H") else 450,
                "scope": json.dumps({"objects": ["users","roles","authorizations"]}),
                "conn": json.dumps({"host": "erp.acmecorp.com", "client": "100",
                                    "mode": "rfc", "encrypted": True}),
                "now": NOW,
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR sync config {cid}: {e}")
    try:
        db.commit()
        print(f"  OK: {count} system connectors")
    except Exception as e:
        db.rollback()
        print(f"  ERR sync configs commit: {e}")

    # =========================================================
    # 27. AUDIT LOGS
    # =========================================================
    print("\n[27/30] Creating audit log entries...")
    log_entries = [
        ("acme_admin",    "CREATE",  "tenant_management", "tenant",         TID,           "Acme Corporation Ltd"),
        ("acme_admin",    "CREATE",  "user_management",   "user",           "u-admin-01",  "Adam Admin"),
        ("acme_admin",    "CREATE",  "user_management",   "user",           "u-ciso-01",   "Clara CISO"),
        ("acme_admin",    "ASSIGN",  "access_management", "role_assignment","u-ap-01",     "John Smith -> Z_FI_AP_FULL"),
        ("acme_ciso",     "TRIGGER", "risk_analysis",     "sod_scan",       "scan-001",    "Full SoD Analysis - Acme Corp"),
        ("system",        "DETECT",  "risk_analysis",     "violation",      "v-001",       "SoD: AP Create + Approve - John Smith"),
        ("acme_compliance","REVIEW", "certification",     "campaign",       "camp-001",    "Q4 2026 Full Access Review"),
        ("acme_auditor",  "CREATE",  "audit_management",  "finding",        "af-001",      "Critical SoD Violation Finding"),
        ("frank.controller","LOGIN", "authentication",    "session",        "sess-001",    "User login from 10.0.1.15"),
        ("system",        "ALERT",   "fraud_detection",   "fraud_alert",    al_ids[0],     "Round-trip payment pattern detected"),
    ]
    count = 0
    for actor, action, category, ttype, tid_str, tname in log_entries:
        try:
            db.execute(text("""
                INSERT INTO audit_logs (timestamp, action, action_category,
                    actor_username, actor_type,
                    target_type, target_id, target_name,
                    source_system, source_ip, success,
                    details)
                VALUES (:ts, :action, :cat,
                    :actor, :atype,
                    :ttype, :tid, :tname,
                    'GovernexPlus', '10.0.1.15', true,
                    :details)
            """), {
                "ts": dt(days=1), "action": action, "cat": category,
                "actor": actor, "atype": "human" if actor != "system" else "system",
                "ttype": ttype, "tid": tid_str, "tname": tname,
                "details": json.dumps({"tenant": TID, "result": "success"}),
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ERR audit log: {e}")
    try:
        db.commit()
        print(f"  OK: {count} audit log entries")
    except Exception as e:
        db.rollback()
        print(f"  ERR audit logs commit: {e}")

    # =========================================================
    # 28. CHECK SAP SECURITY CONTROLS
    # =========================================================
    print("\n[28/30] Checking SAP security controls...")
    try:
        row = db.execute(text(
            "SELECT COUNT(*) FROM sap_security_controls WHERE tenant_id IS NULL OR tenant_id = ''")
        ).fetchone()
        global_count = row[0]
        row2 = db.execute(text("SELECT COUNT(*) FROM sap_security_controls")).fetchone()
        print(f"  OK: {row2[0]} SAP security controls (global library)")
    except Exception as e:
        print(f"  INFO: {e}")

    # =========================================================
    # 29. CHECK TEMPLATE LIBRARY
    # =========================================================
    print("\n[29/30] Checking template library...")
    try:
        row = db.execute(text("SELECT COUNT(*) FROM template_items")).fetchone()
        print(f"  OK: {row[0]} template items (pre-seeded by library seeder)")
    except Exception as e:
        print(f"  INFO: {e}")

    # =========================================================
    # 30. CHECK PLATFORM USERS (admin login)
    # =========================================================
    print("\n[30/30] Verifying tenant admin login capability...")
    try:
        row = db.execute(text(
            "SELECT user_id, username, password_hash FROM users "
            "WHERE tenant_id = :tid AND username = 'acme_admin'"
        ), {"tid": TID}).fetchone()
        if row:
            print(f"  OK: Admin user '{row[1]}' ready (user_id={row[0]})")
        else:
            print("  WARN: Admin user not found")
    except Exception as e:
        print(f"  ERR: {e}")

    # =========================================================
    # VALIDATION
    # =========================================================
    tables_to_check = [
        "tenants", "users", "roles", "user_roles",
        "risk_violations", "org_units", "enterprise_risks",
        "key_risk_indicators", "risk_appetites", "risk_incidents",
        "process_controls", "control_tests", "control_deficiencies",
        "mitigation_controls", "firefighter_requests", "firefighter_sessions",
        "certification_campaigns",
        "audit_plans", "audit_engagements", "audit_findings",
        "jml_policies", "jml_events",
        "vendors", "vendor_assessments", "vendor_issues",
        "fraud_rules", "fraud_alerts", "fraud_cases",
        "bia_records", "bcm_plans", "bcm_test_exercises",
        "whistleblower_cases", "standalone_surveys",
        "policy_documents", "notification_preferences", "sync_configs",
        "audit_logs", "sap_security_controls", "template_items",
    ]

    print("\n" + "=" * 60)
    print("VALIDATION -- Row Counts Per Table")
    print("=" * 60)
    total_rows = 0
    populated = 0
    for tbl in tables_to_check:
        try:
            if tbl in ("sap_security_controls", "template_items", "audit_logs"):
                row = db.execute(text(f"SELECT COUNT(*) FROM {tbl}")).fetchone()
            else:
                row = db.execute(text(f"SELECT COUNT(*) FROM {tbl} WHERE tenant_id = :tid"),
                                 {"tid": TID}).fetchone()
            n = row[0]
            symbol = "OK" if n > 0 else "--"
            print(f"  {symbol}  {tbl:<40} {n:>5} rows")
            total_rows += n
            if n > 0:
                populated += 1
        except Exception as e:
            print(f"  ??  {tbl:<40} (error: {e})")

    print("=" * 60)
    print(f"  Tables with data:  {populated}/{len(tables_to_check)}")
    print(f"  Total rows seeded: {total_rows}")
    print()
    print("  TENANT CREDENTIALS")
    print(f"  Tenant ID:   {TID}")
    print(f"  Admin login: acme_admin / AcmeP@ss2026!")
    print(f"  CISO login:  acme_ciso  / AcmeP@ss2026!")
    print(f"  Auditor:     acme_auditor / AcmeP@ss2026!")
    print("=" * 60)
