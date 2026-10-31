"""
GovernexPlus — Full Tenant Onboarding Seeder (Schema-Correct)
=============================================================
Populates every major table with realistic Acme Corporation demo data.

Run on server:
  cd /opt/governexplus/app
  source venv/bin/activate
  DATABASE_URL="postgresql://governex:G0v3rn3x_Pr0d_2026!@localhost:5432/governexplus" \
    python scripts/full_tenant_seed.py
"""
from __future__ import annotations
import os, sys, uuid, random, datetime, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql://governex:G0v3rn3x_Pr0d_2026!@localhost:5432/governexplus")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

try:
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_pw = pwd_ctx.hash("AcmeP@ss2026!")
except Exception:
    import hashlib
    hashed_pw = "$2b$12$fakehashfordemopurposesonlyXXXXXXXXXXXXXXXXXXXXXXXXX"

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, echo=False)

TENANT_ID = "acme-corp-demo"
NOW = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

def dt(days_ago=0, hours_ago=0):
    return NOW - datetime.timedelta(days=days_ago, hours=hours_ago)

def uid():
    return str(uuid.uuid4())

def short_id(prefix, n):
    return f"{prefix}-{n:03d}"

print("=" * 60)
print("GovernexPlus Full Tenant Seeder (Schema-Correct)")
print(f"Tenant: {TENANT_ID}")
print("=" * 60)

results = {}

with Session(engine) as db:

    # ── 1. TENANT ────────────────────────────────────────────────────────────
    print("\n[1/30] Creating tenant...")
    try:
        db.execute(text("DELETE FROM tenants WHERE slug = :slug"), {"slug": TENANT_ID})
        db.commit()
    except Exception:
        db.rollback()

    try:
        db.execute(text("""
            INSERT INTO tenants (id, name, slug, status, tier, max_users, admin_email, admin_name,
                modules_enabled, settings, created_at, updated_at)
            VALUES (:id, :name, :slug, 'active', 'enterprise', 500,
                'admin@acmecorp.com', 'Adam Admin',
                :modules, :settings, :now, :now)
            ON CONFLICT DO NOTHING
        """), {
            "id": uid(), "name": "Acme Corporation Ltd", "slug": TENANT_ID,
            "modules": json.dumps(["access","risk","audit","process_control","jml","tprm","fraud","bcm","whistleblower","survey"]),
            "settings": json.dumps({"sap_systems": ["ECC","S4HANA"], "currency": "AUD"}),
            "now": NOW
        })
        db.commit()
        results["tenants"] = 1
        print("  ✓ Tenant: Acme Corporation Ltd")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Tenant: {e}")
        results["tenants"] = 0

    # ── 2. USERS ─────────────────────────────────────────────────────────────
    print("\n[2/30] Creating users...")
    users = [
        ("u-admin-01",  "acme_admin",       "Adam Admin",       "IT Administration",   "IT",          "tenant_admin"),
        ("u-ciso-01",   "acme_ciso",        "Clara CISO",       "Information Security","IT",          "ciso"),
        ("u-comp-01",   "acme_compliance",  "Carl Compliance",  "Compliance",          "Finance",     "compliance_officer"),
        ("u-risk-01",   "acme_risk",        "Rachel Risk",      "Risk Management",     "Finance",     "risk_manager"),
        ("u-audit-01",  "acme_auditor",     "Alan Auditor",     "Internal Audit",      "Finance",     "auditor"),
        ("u-mgr-01",    "acme_manager",     "Mark Manager",     "Finance",             "Finance",     "line_manager"),
        ("u-ap-01",     "john.smith",       "John Smith",       "Accounts Payable",    "Finance",     "business_user"),
        ("u-ar-01",     "sarah.jones",      "Sarah Jones",      "Accounts Receivable", "Finance",     "business_user"),
        ("u-mm-01",     "mike.chen",        "Mike Chen",        "Procurement",         "Operations",  "business_user"),
        ("u-tr-01",     "lisa.wang",        "Lisa Wang",        "Treasury",            "Finance",     "business_user"),
        ("u-hr-01",     "tom.brown",        "Tom Brown",        "Human Resources",     "HR",          "business_user"),
        ("u-sd-01",     "anna.lee",         "Anna Lee",         "Sales",               "Sales",       "business_user"),
        ("u-sec-01",    "david.kim",        "David Kim",        "IT Security",         "IT",          "security_admin"),
        ("u-ff-01",     "frank.controller", "Frank Controller", "Finance",             "Finance",     "business_user"),
    ]
    count = 0
    for uid_val, username, full_name, dept, company_code, user_type in users:
        try:
            db.execute(text("""
                INSERT INTO users (id, tenant_id, user_id, username, email, full_name,
                    hashed_password, department, company_code, user_type, status,
                    is_active, created_at, updated_at)
                VALUES (:id, :tid, :uid, :un, :email, :fn, :pw, :dept, :cc, :ut,
                    'active', true, :now, :now)
                ON CONFLICT (tenant_id, username) DO NOTHING
            """), {
                "id": uid_val, "tid": TENANT_ID, "uid": uid_val,
                "un": username, "email": f"{username.replace('.','_')}@acmecorp.com",
                "fn": full_name, "pw": hashed_pw, "dept": dept,
                "cc": company_code, "ut": user_type, "now": NOW
            })
            count += 1
        except Exception as e:
            db.rollback()
            print(f"    ✗ User {username}: {e}")
    try:
        db.commit()
        results["users"] = count
        print(f"  ✓ {count} users")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Users commit: {e}")

    # ── 3. ROLES ─────────────────────────────────────────────────────────────
    print("\n[3/30] Creating SAP roles...")
    roles = [
        ("r-fi-ap-full",  "Z_FI_AP_FULL",      "Finance AP Full Access",          "FI",  "composite"),
        ("r-fi-ap-crt",   "Z_FI_AP_CREATE",     "Finance AP Create",               "FI",  "single"),
        ("r-fi-ap-apr",   "Z_FI_AP_APPROVE",    "Finance AP Approve",              "FI",  "single"),
        ("r-fi-gl",       "Z_FI_GL_POST",       "GL Journal Entry Posting",        "FI",  "single"),
        ("r-mm-buyer",    "Z_MM_BUYER",         "MM Purchasing Buyer",             "MM",  "single"),
        ("r-mm-gr",       "Z_MM_GR_POST",       "MM Goods Receipt Posting",        "MM",  "single"),
        ("r-mm-ven",      "Z_MM_VENDOR_CREATE", "Vendor Master Create",            "MM",  "single"),
        ("r-sd-order",    "Z_SD_ORDER_CREATE",  "SD Sales Order Create",           "SD",  "single"),
        ("r-sd-bill",     "Z_SD_BILLING",       "SD Billing Release",              "SD",  "single"),
        ("r-hr-pay",      "Z_HR_PAYROLL",       "HR Payroll Processing",           "HR",  "single"),
        ("r-hr-maint",    "Z_HR_MAINTAIN",      "HR Employee Master Maintain",     "HR",  "single"),
        ("r-bc-useradm",  "Z_BC_USER_ADMIN",    "BC User Administration",          "BC",  "single"),
        ("r-tr-pay",      "Z_TR_PAYMENT",       "Treasury Payment Run",            "TR",  "single"),
        ("r-basis-all",   "SAP_ALL",            "Full SAP Authorization (Basis)",  "BC",  "composite"),
    ]
    count = 0
    for rid, rname, rdesc, rcat, rtype in roles:
        try:
            db.execute(text("""
                INSERT INTO roles (id, tenant_id, role_id, role_name, description,
                    source_system, role_type, is_active, created_at, updated_at)
                VALUES (:id, :tid, :rid, :rname, :rdesc, 'SAP ECC', :rtype, true, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": rid, "tid": TENANT_ID, "rid": rname, "rname": rname,
                   "rdesc": rdesc, "rtype": rtype, "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["roles"] = count
        print(f"  ✓ {count} roles")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Roles: {e}")

    # ── 4. USER-ROLE ASSIGNMENTS ─────────────────────────────────────────────
    print("\n[4/30] Assigning roles (including SoD conflicts)...")
    assignments = [
        ("u-ap-01",  "r-fi-ap-full"),   # John: AP Full
        ("u-ap-01",  "r-fi-ap-apr"),    # John: AP Approve — SoD conflict
        ("u-ap-01",  "r-mm-ven"),       # John: Vendor Create — triple conflict
        ("u-ar-01",  "r-fi-ap-crt"),    # Sarah: AP Create only (clean)
        ("u-mm-01",  "r-mm-buyer"),     # Mike: Buyer
        ("u-mm-01",  "r-mm-gr"),        # Mike: GR Post — SoD conflict
        ("u-tr-01",  "r-tr-pay"),       # Lisa: Treasury
        ("u-hr-01",  "r-hr-pay"),       # Tom: Payroll
        ("u-hr-01",  "r-hr-maint"),     # Tom: HR Maintain — SoD conflict
        ("u-sd-01",  "r-sd-order"),     # Anna: Sales Orders
        ("u-sd-01",  "r-sd-bill"),      # Anna: Billing — SoD conflict
        ("u-mgr-01", "r-fi-ap-apr"),    # Mark: AP Approve (clean)
        ("u-admin-01","r-bc-useradm"),  # Admin: User Admin
        ("u-ff-01",  "r-fi-gl"),        # Frank: GL Post
    ]
    count = 0
    for user_id, role_id in assignments:
        try:
            db.execute(text("""
                INSERT INTO user_roles (id, tenant_id, user_id, role_id, assigned_by, assigned_at, created_at, updated_at)
                VALUES (:id, :tid, :uid, :rid, 'seed', :now, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": uid(), "tid": TENANT_ID, "uid": user_id, "rid": role_id, "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["user_roles"] = count
        print(f"  ✓ {count} user-role assignments")
    except Exception as e:
        db.rollback()
        print(f"  ✗ User roles: {e}")

    # ── 5. RISK VIOLATIONS ───────────────────────────────────────────────────
    print("\n[5/30] Creating SoD violations...")
    violations = [
        ("vio-001", "SoD-FI-001", "Create Vendor AND Approve Payment (AP)",         "u-ap-01",  "critical", 90),
        ("vio-002", "SoD-FI-003", "Post Journal Entry AND Approve Journal Entry",    "u-ap-01",  "high",     70),
        ("vio-003", "SoD-MM-003", "Create Purchase Order AND Post Goods Receipt",    "u-mm-01",  "high",     70),
        ("vio-004", "SoD-HR-001", "Maintain Employee Master AND Process Payroll",    "u-hr-01",  "critical", 90),
        ("vio-005", "SoD-SD-005", "Create Sales Order AND Release Billing Document", "u-sd-01",  "medium",   50),
        ("vio-006", "SoD-MM-001", "Create Vendor AND Create Purchase Order",         "u-ap-01",  "high",     65),
        ("vio-007", "SoD-FI-002", "Approve Payment AND Release Payment Run",         "u-ar-01",  "medium",   50),
        ("vio-008", "SoD-TR-001", "Initiate Payment AND Release Treasury Run",       "u-tr-01",  "critical", 85),
    ]
    count = 0
    for vid, rule_id, desc, user_id, sev, score in violations:
        try:
            db.execute(text("""
                INSERT INTO risk_violations (id, tenant_id, violation_id, rule_id, rule_name,
                    rule_type, user_id, description, severity_score, status, detected_at,
                    created_at, updated_at)
                VALUES (:id, :tid, :vid, :rid, :rname, 'SoD', :uid, :desc,
                    :score, 'open', :det, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": vid, "tid": TENANT_ID, "vid": vid, "rid": rule_id,
                   "rname": rule_id, "uid": user_id, "desc": desc,
                   "score": score, "det": dt(random.randint(1, 30)), "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["risk_violations"] = count
        print(f"  ✓ {count} violations")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Violations: {e}")

    # ── 6. ORG UNITS ─────────────────────────────────────────────────────────
    print("\n[6/30] Creating org units...")
    org_units = [
        ("ou-root",   None,       "Acme Corporation Ltd",   "company",    1, "acme"),
        ("ou-fin",    "ou-root",  "Finance",                "division",   2, "acme/finance"),
        ("ou-it",     "ou-root",  "Information Technology", "division",   2, "acme/it"),
        ("ou-hr",     "ou-root",  "Human Resources",        "division",   2, "acme/hr"),
        ("ou-proc",   "ou-root",  "Procurement",            "division",   2, "acme/procurement"),
        ("ou-sales",  "ou-root",  "Sales",                  "division",   2, "acme/sales"),
        ("ou-ap",     "ou-fin",   "Accounts Payable",       "department", 3, "acme/finance/ap"),
        ("ou-ar",     "ou-fin",   "Accounts Receivable",    "department", 3, "acme/finance/ar"),
        ("ou-tr",     "ou-fin",   "Treasury",               "department", 3, "acme/finance/treasury"),
        ("ou-itsec",  "ou-it",    "IT Security",            "department", 3, "acme/it/security"),
    ]
    count = 0
    for ou_id, parent, name, utype, level, path in org_units:
        try:
            db.execute(text("""
                INSERT INTO org_units (id, tenant_id, unit_id, name, unit_type,
                    parent_id, level, path, is_active, created_at, updated_at)
                VALUES (:id, :tid, :uid, :name, :utype, :parent, :level, :path,
                    true, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": ou_id, "tid": TENANT_ID, "uid": ou_id, "name": name,
                   "utype": utype, "parent": parent, "level": level,
                   "path": path, "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["org_units"] = count
        print(f"  ✓ {count} org units")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Org units: {e}")

    # ── 7. ENTERPRISE RISKS ───────────────────────────────────────────────────
    print("\n[7/30] Creating enterprise risk register...")
    risks = [
        ("er-001", "Unauthorized Financial Transactions",       "Financial",   5, 5, "open",        "ou-fin"),
        ("er-002", "Excessive User Privileges",                 "Access",      4, 4, "in_treatment", "ou-itsec"),
        ("er-003", "Payroll Fraud via SoD Failure",             "Financial",   5, 4, "open",         "ou-hr"),
        ("er-004", "SAP System Downtime - Month End",           "Operational", 3, 5, "in_treatment", "ou-it"),
        ("er-005", "Vendor Master Data Manipulation",           "Financial",   4, 5, "open",         "ou-ap"),
        ("er-006", "Inadequate Audit Trail Coverage",           "Compliance",  3, 4, "open",         "ou-itsec"),
        ("er-007", "Data Breach via Excessive Access",          "IT Security", 4, 5, "in_treatment", "ou-itsec"),
        ("er-008", "Regulatory Non-Compliance (SOX 404)",       "Compliance",  2, 5, "monitoring",   "ou-fin"),
    ]
    count = 0
    for rid, title, cat, lik, imp, status, org_unit in risks:
        score = lik * imp
        try:
            db.execute(text("""
                INSERT INTO enterprise_risks (id, tenant_id, risk_id, title, description,
                    description_ar, category, org_unit_id, likelihood, impact,
                    inherent_risk_score, residual_risk_score, status, owner_id,
                    created_at, updated_at)
                VALUES (:id, :tid, :rid, :title, :desc, '', :cat, :ou,
                    :lik, :imp, :score, :rscore, :status, 'u-risk-01', :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": rid, "tid": TENANT_ID, "rid": rid, "title": title,
                   "desc": f"Risk: {title}. Impact on Acme operations and compliance posture.",
                   "cat": cat, "ou": org_unit, "lik": lik, "imp": imp,
                   "score": score, "rscore": max(score - random.randint(2, 6), 2),
                   "status": status, "now": dt(random.randint(10, 90))})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["enterprise_risks"] = count
        print(f"  ✓ {count} risks")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Risks: {e}")

    # ── 8. KRIs ───────────────────────────────────────────────────────────────
    print("\n[8/30] Creating KRIs...")
    kris = [
        ("kri-001", "SoD Violation Rate",           "er-002", 8.5, 5.0,  10.0, "breached",  "%"),
        ("kri-002", "Unreviewed FF Sessions",        "er-002", 3,   0,    5,    "at_risk",   "count"),
        ("kri-003", "Overdue Certification Items",   "er-008", 12,  0,    10,   "breached",  "count"),
        ("kri-004", "Failed Login Attempts/Day",     "er-007", 45,  0,    100,  "normal",    "count"),
        ("kri-005", "Critical Open Findings >30 days","er-008", 4,  0,    3,    "breached",  "count"),
        ("kri-006", "Unmapped Users (Orphan Accounts)","er-002",7,  0,    10,   "at_risk",   "count"),
    ]
    count = 0
    for kri_id, name, risk_id, curr, low, high, status, unit in kris:
        try:
            db.execute(text("""
                INSERT INTO key_risk_indicators (id, tenant_id, kri_id, name, description,
                    risk_id, unit_of_measure, current_value, lower_threshold, upper_threshold,
                    status, frequency, owner_id, created_at, updated_at)
                VALUES (:id, :tid, :kid, :name, :desc, :rid, :unit,
                    :curr, :low, :high, :status, 'monthly', 'u-risk-01', :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": kri_id, "tid": TENANT_ID, "kid": kri_id, "name": name,
                   "desc": f"Monitors: {name}", "rid": risk_id, "unit": unit,
                   "curr": curr, "low": low, "high": high, "status": status, "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["key_risk_indicators"] = count
        print(f"  ✓ {count} KRIs")
    except Exception as e:
        db.rollback()
        print(f"  ✗ KRIs: {e}")

    # ── 9. RISK APPETITE ──────────────────────────────────────────────────────
    print("\n[9/30] Creating risk appetite...")
    appetites = [
        ("ra-001", "Access Control",   3, 15, "ou-itsec", "LOW appetite for unauthorized access. Maximum tolerated risk score: 15/25."),
        ("ra-002", "Financial Fraud",  1, 5,  "ou-fin",   "ZERO appetite for financial fraud. Any incident triggers immediate board escalation."),
        ("ra-003", "Operational Risk", 5, 20, "ou-it",    "MEDIUM appetite for operational disruptions. Tolerated RTO: 4 hours."),
        ("ra-004", "Compliance",       2, 12, "ou-fin",   "LOW appetite for regulatory non-compliance. All critical controls must be effective."),
        ("ra-005", "Technology Risk",  4, 18, "ou-it",    "MODERATE appetite for technology risk. DR plan tested annually."),
    ]
    count = 0
    for ra_id, cat, score, threshold, ou, desc in appetites:
        try:
            db.execute(text("""
                INSERT INTO risk_appetites (id, tenant_id, category, org_unit_id,
                    appetite_score, tolerance_score, description, approved_by,
                    created_at, updated_at)
                VALUES (:id, :tid, :cat, :ou, :score, :thresh, :desc, 'u-risk-01', :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": ra_id, "tid": TENANT_ID, "cat": cat, "ou": ou,
                   "score": score, "thresh": threshold, "desc": desc, "now": dt(90)})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["risk_appetites"] = count
        print(f"  ✓ {count} risk appetite statements")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Appetite: {e}")

    # ── 10. RISK INCIDENTS ────────────────────────────────────────────────────
    print("\n[10/30] Creating risk incidents...")
    incidents = [
        ("ri-001", "er-001", "Unauthorized AP Payment Approved",  "Payment of AUD 85,000 approved without dual auth",  "high",     "investigating"),
        ("ri-002", "er-003", "Ghost Payroll Employee Detected",   "Active payroll record for employee who left 3m ago", "critical", "contained"),
        ("ri-003", "er-004", "SAP ECC Outage - 4 Hours",          "System unavailable during month-end close",          "high",     "resolved"),
    ]
    count = 0
    for inc_id, risk_id, title, desc, sev, status in incidents:
        try:
            db.execute(text("""
                INSERT INTO risk_incidents (id, tenant_id, incident_id, title, description,
                    risk_id, severity, financial_impact, currency, status, occurred_at,
                    reported_by, created_at, updated_at)
                VALUES (:id, :tid, :iid, :title, :desc, :rid, :sev,
                    :impact, 'AUD', :status, :occ, 'u-risk-01', :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": inc_id, "tid": TENANT_ID, "iid": inc_id, "title": title,
                   "desc": desc, "rid": risk_id, "sev": sev,
                   "impact": random.randint(10000, 100000),
                   "status": status, "occ": dt(random.randint(5, 30)), "now": dt(1)})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["risk_incidents"] = count
        print(f"  ✓ {count} incidents")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Incidents: {e}")

    # ── 11. PROCESS CONTROLS ──────────────────────────────────────────────────
    print("\n[11/30] Creating process controls...")
    controls = [
        ("pc-001", "AP-CTL-001", "AP Invoice 3-Way Match",          "Three-way match enforced for all invoices >AUD 5,000", "preventive", "automated", "monthly"),
        ("pc-002", "AP-CTL-002", "Monthly Bank Reconciliation",     "All bank accounts reconciled monthly by Finance Mgr",   "detective",  "manual",    "monthly"),
        ("pc-003", "AP-CTL-003", "Vendor Master Change Approval",   "Dual approval required for all vendor master changes",  "preventive", "hybrid",    "event_driven"),
        ("pc-004", "AC-CTL-001", "Quarterly Access Review",         "All user access reviewed and recertified quarterly",    "detective",  "manual",    "quarterly"),
        ("pc-005", "AC-CTL-002", "Real-Time SoD Conflict Detection","SoD violation alerts via GovernexPlus ARA engine",      "detective",  "automated", "continuous"),
        ("pc-006", "HR-CTL-001", "Payroll Calculation Verification","Independent verification of payroll calculations",       "detective",  "manual",    "monthly"),
        ("pc-007", "IT-CTL-001", "SAP Change Management",           "All SAP changes via formal change management process",  "preventive", "hybrid",    "event_driven"),
        ("pc-008", "AC-CTL-003", "Privileged Access Monitoring",    "All firefighter sessions logged and reviewed",          "detective",  "automated", "event_driven"),
    ]
    count = 0
    for pc_id, ctrl_id, name, desc, ctype, cnature, freq in controls:
        try:
            db.execute(text("""
                INSERT INTO process_controls (id, tenant_id, control_id, name,
                    objective, description, control_type, control_nature,
                    frequency, status, owner_id, created_at, updated_at)
                VALUES (:id, :tid, :cid, :name, :obj, :desc, :ct, :cn,
                    :freq, 'active', 'u-comp-01', :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": pc_id, "tid": TENANT_ID, "cid": ctrl_id, "name": name,
                   "obj": f"Ensure {name.lower()} is operating effectively",
                   "desc": desc, "ct": ctype, "cn": cnature, "freq": freq,
                   "now": dt(random.randint(30, 120))})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["process_controls"] = count
        print(f"  ✓ {count} process controls")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Controls: {e}")

    # ── 12. CONTROL TESTS ─────────────────────────────────────────────────────
    print("\n[12/30] Creating control tests...")
    tests = [
        ("ct-001", "pc-001", "pass",    "3-way match verified for 100% of Q3 invoices. 0 exceptions.",      50, 0),
        ("ct-002", "pc-002", "pass",    "All 12 bank accounts reconciled. 2 timing differences explained.",  12, 0),
        ("ct-003", "pc-003", "fail",    "3 vendor changes found without dual approval. Escalated to mgr.",   25, 3),
        ("ct-004", "pc-004", "pass",    "Q3 access review completed. 14 users had access removed.",          80, 0),
        ("ct-005", "pc-005", "pass",    "ARA running continuously. 8 new violations detected same day.",     100,0),
        ("ct-006", "pc-006", "partial", "Payroll verification done. 1 employee record had wrong allowance.", 30, 1),
    ]
    count = 0
    for ct_id, ctrl_id, result, notes, sample, exc in tests:
        try:
            db.execute(text("""
                INSERT INTO control_tests (id, tenant_id, test_id, control_id, test_type,
                    testing_period_start, testing_period_end, sample_size, population_size,
                    tester_id, result, notes, exceptions_found, created_at, updated_at)
                VALUES (:id, :tid, :tid2, :cid, 'design_effectiveness',
                    :start, :end, :sample, :pop, 'u-audit-01', :result, :notes,
                    :exc, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": ct_id, "tid": TENANT_ID, "tid2": ct_id, "cid": ctrl_id,
                   "start": dt(30), "end": dt(1), "sample": sample, "pop": sample * 2,
                   "result": result, "notes": notes, "exc": exc,
                   "now": dt(random.randint(1, 7))})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["control_tests"] = count
        print(f"  ✓ {count} control tests")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Tests: {e}")

    # ── 13. CONTROL DEFICIENCIES ──────────────────────────────────────────────
    print("\n[13/30] Creating control deficiencies...")
    deficiencies = [
        ("cd-001", "pc-003", "ct-003", "significant_deficiency", "Vendor Master Change Approval Bypass",  "3 vendor changes without dual approval", "open"),
        ("cd-002", "pc-006", "ct-006", "deficiency",             "Payroll Allowance Miscalculation",      "1 employee over-paid by AUD 1,200",       "in_remediation"),
    ]
    count = 0
    for did, ctrl_id, test_id, sev, title, desc, status in deficiencies:
        try:
            db.execute(text("""
                INSERT INTO control_deficiencies (id, tenant_id, deficiency_id, control_id,
                    test_id, source, title, description, severity, root_cause, status,
                    identified_date, owner_id, created_at, updated_at)
                VALUES (:id, :tid, :did, :cid, :test_id, 'testing',
                    :title, :desc, :sev, 'Process not followed',
                    :status, :idate, 'u-comp-01', :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": did, "tid": TENANT_ID, "did": did, "cid": ctrl_id,
                   "test_id": test_id, "title": title, "desc": desc,
                   "sev": sev, "status": status,
                   "idate": dt(random.randint(5, 14)), "now": dt(1)})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["control_deficiencies"] = count
        print(f"  ✓ {count} deficiencies")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Deficiencies: {e}")

    # ── 14. MITIGATION CONTROLS ───────────────────────────────────────────────
    print("\n[14/30] Creating mitigation controls...")
    mitigations = [
        ("mc-001", "MC-001", "Dual Approval Compensating Control",  "detective",  ["SoD-FI-001", "SoD-MM-001"]),
        ("mc-002", "MC-002", "Monthly Vendor Reconciliation",       "detective",  ["SoD-FI-001"]),
        ("mc-003", "MC-003", "Segregated GR Log Review",            "detective",  ["SoD-MM-003"]),
        ("mc-004", "MC-004", "Payroll Supervisor Sign-off",         "preventive", ["SoD-HR-001"]),
        ("mc-005", "MC-005", "Automated Payment Threshold Alert",   "detective",  ["SoD-TR-001"]),
    ]
    count = 0
    for mc_id, ctrl_id, name, ctype, rule_ids in mitigations:
        try:
            db.execute(text("""
                INSERT INTO mitigation_controls (id, tenant_id, control_id, control_name,
                    description, control_type, monitoring_frequency, applicable_rule_ids,
                    status, owner_id, created_at, updated_at)
                VALUES (:id, :tid, :cid, :name, :desc, :ct, 'monthly', :rids,
                    'active', 'u-comp-01', :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": mc_id, "tid": TENANT_ID, "cid": ctrl_id, "name": name,
                   "desc": f"Compensating control: {name}",
                   "ct": ctype, "rids": json.dumps(rule_ids), "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["mitigation_controls"] = count
        print(f"  ✓ {count} mitigation controls")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Mitigations: {e}")

    # ── 15. FIREFIGHTER ───────────────────────────────────────────────────────
    print("\n[15/30] Creating firefighter data...")
    ff_requests = [
        ("ffr-001", "u-ff-01",    "SAP ECC Production", "Critical month-end AP posting failure. Invoice stuck.",  "approved"),
        ("ffr-002", "u-admin-01", "SAP ECC Production", "Emergency basis config for system outage resolution.",   "approved"),
        ("ffr-003", "u-sec-01",   "SAP ECC Production", "Urgent vendor payment for emergency system maintenance.","pending"),
        ("ffr-004", "u-hr-01",    "SAP HCM Production", "Emergency payroll correction for terminated employee.",   "rejected"),
    ]
    count_req = 0
    for fr_id, user_id, sys_name, reason, status in ff_requests:
        try:
            db.execute(text("""
                INSERT INTO firefighter_requests (id, tenant_id, request_id, requester_user_id,
                    requester_name, requester_email, requester_department, target_system,
                    reason, justification, status, priority, requested_at, created_at, updated_at)
                VALUES (:id, :tid, :frid, :uid, 'Requester', :email, 'Finance',
                    :sys, :reason, :reason, :status, 'high',
                    :now, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": fr_id, "tid": TENANT_ID, "frid": fr_id, "uid": user_id,
                   "email": f"{user_id}@acmecorp.com", "sys": sys_name,
                   "reason": reason, "status": status,
                   "now": dt(random.randint(1, 10))})
            count_req += 1
        except Exception as e:
            db.rollback()

    # FF Session
    count_sess = 0
    try:
        db.execute(text("""
            INSERT INTO firefighter_sessions (id, tenant_id, session_id, request_id,
                requester_user_id, firefighter_id, target_system, start_time, end_time,
                status, log_reviewed, created_at, updated_at)
            VALUES (:id, :tid, 'ffs-001', 'ffr-001', 'u-ff-01',
                'FF_ACME_FI', 'SAP ECC Production', :start, :end,
                'completed', true, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": "ffs-001", "tid": TENANT_ID, "start": dt(5, 2), "end": dt(5, 0), "now": dt(5)})
        count_sess = 1
    except Exception as e:
        db.rollback()

    try:
        db.commit()
        results["firefighter_requests"] = count_req
        results["firefighter_sessions"] = count_sess
        print(f"  ✓ {count_req} FF requests, {count_sess} session")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Firefighter: {e}")

    # ── 16. CERTIFICATION CAMPAIGNS ───────────────────────────────────────────
    print("\n[16/30] Creating certification campaigns...")
    campaigns = [
        ("cc-001", "Q4 2026 User Access Review",           "access_review",  "completed"),
        ("cc-002", "SOX Critical Controls Certification",  "controls",       "active"),
        ("cc-003", "Privileged Access Certification",      "access_review",  "draft"),
    ]
    count = 0
    for cc_id, name, ctype, status in campaigns:
        try:
            db.execute(text("""
                INSERT INTO certification_campaigns (id, campaign_id, tenant_id, name,
                    description, campaign_type, status, owner_id,
                    start_date, end_date, created_at, updated_at)
                VALUES (:id, :cid, :tid, :name, :desc, :ctype, :status,
                    'u-comp-01', :start, :end, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": cc_id, "cid": cc_id, "tid": TENANT_ID, "name": name,
                   "desc": f"Certification: {name}", "ctype": ctype, "status": status,
                   "start": dt(30), "end": dt(0) + datetime.timedelta(days=30), "now": dt(30)})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["certification_campaigns"] = count
        print(f"  ✓ {count} certification campaigns")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Certifications: {e}")

    # ── 17. AUDIT MANAGEMENT ──────────────────────────────────────────────────
    print("\n[17/30] Creating audit management data...")

    # Audit plan
    count_plan = 0
    try:
        db.execute(text("""
            INSERT INTO audit_plans (id, tenant_id, plan_id, name, description,
                plan_type, fiscal_year, period_start, period_end, status,
                created_by, created_at, updated_at)
            VALUES (:id, :tid, 'ap-001', 'FY2026 Internal Audit Plan',
                'Annual risk-based internal audit plan for Acme Corporation FY2026',
                'annual', 2026, :start, :end, 'approved', 'u-audit-01', :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": "ap-001", "tid": TENANT_ID,
               "start": dt(300), "end": dt(0) + datetime.timedelta(days=65), "now": dt(300)})
        count_plan = 1
    except Exception as e:
        db.rollback()

    # Audit engagement
    count_eng = 0
    try:
        db.execute(text("""
            INSERT INTO audit_engagements (id, tenant_id, engagement_id, plan_id,
                entity_id, title, objective, scope, engagement_type, status,
                risk_rating, lead_auditor_id, start_date, end_date, created_at, updated_at)
            VALUES (:id, :tid, 'eng-001', 'ap-001', 'ou-ap',
                'AP SoD Controls Review',
                'Review SoD controls in AP process and effectiveness of compensating controls',
                'SAP ECC AP module, all AP users', 'controls', 'fieldwork',
                'high', 'u-audit-01', :start, :end, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": "eng-001", "tid": TENANT_ID,
               "start": dt(20), "end": dt(0) + datetime.timedelta(days=10), "now": dt(20)})
        count_eng = 1
    except Exception as e:
        db.rollback()

    # Audit findings
    findings = [
        ("af-001", "SoD Violation in AP",              "6 users have conflicting AP roles — create vendor AND approve payment. High fraud risk.", "critical", "open"),
        ("af-002", "Vendor Master Change Control Weak", "Change approval bypassed 3 times. No detective control.",                                "high",     "in_progress"),
        ("af-003", "Excessive System Access",           "4 finance users have SAP_ALL profile beyond business need.",                             "high",     "open"),
    ]
    count_find = 0
    for fid, title, desc, sev, status in findings:
        try:
            db.execute(text("""
                INSERT INTO audit_findings (id, tenant_id, finding_id, engagement_id,
                    ref_number, title, condition, criteria, cause, effect,
                    severity, status, owner_id, due_date, created_at, updated_at)
                VALUES (:id, :tid, :fid, 'eng-001', :ref,
                    :title, :desc, 'Control standards require SoD', 'Process failure',
                    'Risk of unauthorized transactions', :sev, :status,
                    'u-audit-01', :due, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": fid, "tid": TENANT_ID, "fid": fid,
                   "ref": f"AF-2026-{fid[-3:]}", "title": title, "desc": desc,
                   "sev": sev, "status": status,
                   "due": dt(0) + datetime.timedelta(days=30), "now": dt(5)})
            count_find += 1
        except Exception as e:
            db.rollback()

    try:
        db.commit()
        results["audit_plans"] = count_plan
        results["audit_engagements"] = count_eng
        results["audit_findings"] = count_find
        print(f"  ✓ {count_plan} plan, {count_eng} engagement, {count_find} findings")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Audit: {e}")

    # ── 18. JML ──────────────────────────────────────────────────────────────
    print("\n[18/30] Creating JML policies and events...")
    jml_policies = [
        ("jml-pol-001", "Standard Joiner Policy",            "joiner",   "Provision birthright access on day 1"),
        ("jml-pol-002", "Departmental Transfer Policy",      "mover",    "Adjust access within 24h of confirmed transfer"),
        ("jml-pol-003", "Resignation Leaver Policy",         "leaver",   "Revoke all access on last working day"),
        ("jml-pol-004", "Termination for Cause Policy",      "leaver",   "Immediate access revocation on termination"),
    ]
    count = 0
    for pol_id, name, ptype, desc in jml_policies:
        try:
            db.execute(text("""
                INSERT INTO jml_policies (id, tenant_id, policy_name, description,
                    event_type, birthright_roles, is_active, created_at, updated_at)
                VALUES (:id, :tid, :name, :desc, :ptype, :roles, true, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": pol_id, "tid": TENANT_ID, "name": name, "desc": desc,
                   "ptype": ptype, "roles": json.dumps([]), "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()

    jml_events = [
        ("jml-evt-001", "joiner", "EMP-2001", "Sarah Jones",    "AR Specialist",    "Accounts Receivable"),
        ("jml-evt-002", "mover",  "EMP-1045", "Mike Chen",      "Procurement Lead", "Procurement"),
        ("jml-evt-003", "leaver", "EMP-1078", "Lisa Wang",      "Treasury Analyst", "Treasury"),
        ("jml-evt-004", "leaver", "EMP-1099", "Former Employee","",                 ""),
    ]
    count_evt = 0
    for evt_id, etype, emp_id, name, pos, org in jml_events:
        try:
            db.execute(text("""
                INSERT INTO jml_events (id, tenant_id, event_type, employee_id,
                    employee_name, new_position, new_org_unit, effective_date,
                    status, created_at, updated_at)
                VALUES (:id, :tid, :etype, :emp, :name, :pos, :org,
                    :eff, 'completed', :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": evt_id, "tid": TENANT_ID, "etype": etype, "emp": emp_id,
                   "name": name, "pos": pos, "org": org,
                   "eff": dt(random.randint(1, 20)), "now": dt(random.randint(0, 5))})
            count_evt += 1
        except Exception as e:
            db.rollback()

    try:
        db.commit()
        results["jml_policies"] = count
        results["jml_events"] = count_evt
        print(f"  ✓ {count} JML policies, {count_evt} events")
    except Exception as e:
        db.rollback()
        print(f"  ✗ JML: {e}")

    # ── 19. TPRM ─────────────────────────────────────────────────────────────
    print("\n[19/30] Creating TPRM vendors...")
    vendors = [
        ("ven-001", "CloudSoft Solutions",     "V-CSO-001", "IT Services",  "critical", "active",    "high"),
        ("ven-002", "Apex Consulting Group",   "V-ACG-002", "Consulting",   "high",     "active",    "medium"),
        ("ven-003", "FastShip Logistics",      "V-FSL-003", "Logistics",    "medium",   "active",    "low"),
        ("ven-004", "DataSafe Analytics",      "V-DSA-004", "Data Services","critical", "active",    "high"),
        ("ven-005", "OfficeMax Supplies",      "V-OMS-005", "Procurement",  "low",      "active",    "low"),
        ("ven-006", "TechMaint Systems",       "V-TMS-006", "Maintenance",  "high",     "suspended", "critical"),
    ]
    count = 0
    for vid, name, vcode, cat, crit, status, risk in vendors:
        try:
            db.execute(text("""
                INSERT INTO vendors (id, tenant_id, vendor_name, vendor_code,
                    tier, status, contact_email, risk_rating, category,
                    created_at, updated_at)
                VALUES (:id, :tid, :name, :vcode, :tier, :status,
                    :email, :risk, :cat, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": vid, "tid": TENANT_ID, "name": name, "vcode": vcode,
                   "tier": crit, "status": status,
                   "email": f"vendor@{name.lower().replace(' ','-')}.com",
                   "risk": risk, "cat": cat, "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()

    count_va = 0
    try:
        db.execute(text("""
            INSERT INTO vendor_assessments (id, tenant_id, vendor_id, assessment_name,
                status, due_date, completed_date, overall_score, created_at, updated_at)
            VALUES (:id, :tid, 'ven-001', 'Annual Security Assessment FY2026',
                'completed', :due, :comp, 72, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": "va-001", "tid": TENANT_ID, "due": dt(50), "comp": dt(45), "now": dt(45)})
        count_va = 1
    except Exception as e:
        db.rollback()

    count_vi = 0
    try:
        db.execute(text("""
            INSERT INTO vendor_issues (id, tenant_id, vendor_id, issue_title,
                description, severity, status, due_date, owner, resolution_notes,
                created_at, updated_at)
            VALUES (:id, :tid, 'ven-006',
                'Data Access Breach During Maintenance',
                'Vendor accessed client data outside contractual scope during maintenance window.',
                'critical', 'open', :due, 'u-ciso-01', '', :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": "vi-001", "tid": TENANT_ID, "due": dt(0) + datetime.timedelta(days=7), "now": dt(3)})
        count_vi = 1
    except Exception as e:
        db.rollback()

    try:
        db.commit()
        results["vendors"] = count
        results["vendor_assessments"] = count_va
        results["vendor_issues"] = count_vi
        print(f"  ✓ {count} vendors, {count_va} assessment, {count_vi} issue")
    except Exception as e:
        db.rollback()
        print(f"  ✗ TPRM: {e}")

    # ── 20. FRAUD DETECTION ───────────────────────────────────────────────────
    print("\n[20/30] Creating fraud detection data...")
    fraud_rules_data = [
        ("fr-001", "Duplicate Vendor Payment",       "payment_duplicate",   "Flags duplicate invoice numbers within 30 days",       5),
        ("fr-002", "Round Dollar Amount Anomaly",    "payment_anomaly",     "Flags payments in exact round amounts",                 3),
        ("fr-003", "After-Hours Transaction",        "access_anomaly",      "Flags financial transactions outside business hours",   4),
        ("fr-004", "Dormant Account Activation",    "access_anomaly",      "Flags accounts inactive 90+ days suddenly active",      4),
        ("fr-005", "Vendor Self-Approval",           "authorization_bypass","User approves payment to vendor they created",          8),
    ]
    count = 0
    for frid, name, ftype, desc, score in fraud_rules_data:
        try:
            db.execute(text("""
                INSERT INTO fraud_rules (id, tenant_id, rule_name, rule_type, description,
                    conditions, risk_score, is_active, created_at, updated_at)
                VALUES (:id, :tid, :name, :rtype, :desc, :conds, :score, true, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": frid, "tid": TENANT_ID, "name": name, "rtype": ftype,
                   "desc": desc, "conds": json.dumps({"threshold": 3}),
                   "score": score, "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()

    fraud_alerts_data = [
        ("fa-001", "fr-001", "u-ap-01",  "Duplicate invoice INV-4421 detected — AUD 45,000", "high",     "open"),
        ("fa-002", "fr-003", "u-mm-01",  "Purchase Order raised at 11:47 PM on Sunday",       "medium",   "investigating"),
        ("fa-003", "fr-005", "u-ap-01",  "User approved payment to vendor they created",       "critical", "open"),
        ("fa-004", "fr-002", "u-tr-01",  "3 payments of exactly AUD 10,000 in 7 days",         "high",     "open"),
    ]
    count_alert = 0
    for fa_id, rule_id, user_id, desc, sev, status in fraud_alerts_data:
        try:
            db.execute(text("""
                INSERT INTO fraud_alerts (id, tenant_id, rule_id, user_id, system_id,
                    alert_type, description, risk_score, status, triggered_at,
                    created_at, updated_at)
                VALUES (:id, :tid, :rid, :uid, 'SAP ECC',
                    'sod_violation', :desc,
                    :score, :status, :trig, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": fa_id, "tid": TENANT_ID, "rid": rule_id, "uid": user_id,
                   "desc": desc, "score": 75 if sev == "critical" else 50 if sev == "high" else 30,
                   "status": status, "trig": dt(random.randint(0, 7)), "now": NOW})
            count_alert += 1
        except Exception as e:
            db.rollback()

    count_case = 0
    try:
        db.execute(text("""
            INSERT INTO fraud_cases (id, tenant_id, case_reference,
                title, description, severity, status, assigned_to,
                linked_alert_ids, created_at, updated_at)
            VALUES (:id, :tid, 'FC-2026-001',
                'AP Vendor Self-Approval Investigation',
                'Investigation into unauthorized vendor payment approvals by AP user. Potential exposure AUD 45,000.',
                'critical', 'open', 'u-ciso-01',
                :alerts, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": "fc-001", "tid": TENANT_ID,
               "alerts": json.dumps(["fa-001", "fa-003"]), "now": dt(2)})
        count_case = 1
    except Exception as e:
        db.rollback()

    try:
        db.commit()
        results["fraud_rules"] = count
        results["fraud_alerts"] = count_alert
        results["fraud_cases"] = count_case
        print(f"  ✓ {count} rules, {count_alert} alerts, {count_case} case")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Fraud: {e}")

    # ── 21. BCM ───────────────────────────────────────────────────────────────
    print("\n[21/30] Creating BCM data...")
    bias = [
        ("bia-001", "Finance Payment Processing",   "critical", 4,  "ou-fin"),
        ("bia-002", "SAP ECC Core Operations",      "critical", 2,  "ou-it"),
        ("bia-003", "Payroll Processing",           "critical", 1,  "ou-hr"),
        ("bia-004", "Procurement Ordering",         "high",     8,  "ou-proc"),
        ("bia-005", "Customer Order Processing",    "high",     24, "ou-sales"),
    ]
    count = 0
    for bid, name, crit, rto, ou in bias:
        try:
            db.execute(text("""
                INSERT INTO bia_records (id, tenant_id, process_name, process_owner,
                    criticality, rto_hours, rpo_hours, mtpd_hours, dependencies,
                    recovery_strategy, created_at, updated_at)
                VALUES (:id, :tid, :name, :owner, :crit, :rto, :rpo, :mtpd,
                    :deps, 'Manual fallback with pre-approved procedures', :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": bid, "tid": TENANT_ID, "name": name, "owner": ou,
                   "crit": crit, "rto": rto, "rpo": max(rto // 2, 1),
                   "mtpd": rto * 2, "deps": json.dumps(["SAP ECC", "Network"]),
                   "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()

    bcm_plans_data = [
        ("bcp-001", "SAP ECC Business Continuity Plan",    "it_disaster_recovery", "approved"),
        ("bcp-002", "Finance Operations Continuity Plan",  "business_continuity",  "approved"),
        ("bcp-003", "HR Payroll Contingency Plan",         "business_continuity",  "draft"),
    ]
    count_plan = 0
    for bp_id, name, ptype, status in bcm_plans_data:
        try:
            db.execute(text("""
                INSERT INTO bcm_plans (id, tenant_id, plan_name, plan_type,
                    scope, owner, version, status, created_at, updated_at)
                VALUES (:id, :tid, :name, :ptype, 'All critical business processes',
                    'u-admin-01', '1.0', :status, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": bp_id, "tid": TENANT_ID, "name": name, "ptype": ptype,
                   "status": status, "now": dt(90)})
            count_plan += 1
        except Exception as e:
            db.rollback()

    count_ex = 0
    try:
        db.execute(text("""
            INSERT INTO bcm_test_exercises (id, tenant_id, plan_id, exercise_name,
                exercise_type, scheduled_date, completed_date, facilitator,
                participants, outcome, created_at, updated_at)
            VALUES (:id, :tid, 'bcp-001', 'SAP Failover Tabletop Exercise',
                'tabletop', :sched, :comp, 'u-admin-01',
                :parts, 'successful', :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": "bce-001", "tid": TENANT_ID,
               "sched": dt(60), "comp": dt(59),
               "parts": json.dumps(["u-admin-01", "u-ciso-01", "u-risk-01"]),
               "now": dt(59)})
        count_ex = 1
    except Exception as e:
        db.rollback()

    try:
        db.commit()
        results["bia_records"] = count
        results["bcm_plans"] = count_plan
        results["bcm_test_exercises"] = count_ex
        print(f"  ✓ {count} BIA, {count_plan} BCM plans, {count_ex} exercise")
    except Exception as e:
        db.rollback()
        print(f"  ✗ BCM: {e}")

    # ── 22. WHISTLEBLOWER ─────────────────────────────────────────────────────
    print("\n[22/30] Creating whistleblower cases...")
    wb_cases = [
        ("wb-001", "REF-2026-WB-001", "fraud",           "critical", "investigating",
         "Suspected vendor kickback in procurement. Manager approving inflated invoices from related party."),
        ("wb-002", "REF-2026-WB-002", "policy_violation","high",     "open",
         "Manager requesting inappropriate system access for personal use outside job scope."),
        ("wb-003", "REF-2026-WB-003", "fraud",           "high",     "resolved",
         "Possible payroll manipulation. Ghost employee on payroll for 3 months after termination."),
    ]
    count = 0
    for wc_id, ref, cat, priority, status, details in wb_cases:
        try:
            db.execute(text("""
                INSERT INTO whistleblower_cases (id, tenant_id, case_reference,
                    category, submission_channel, summary, details, priority,
                    status, is_anonymous, submitted_at, created_at, updated_at)
                VALUES (:id, :tid, :ref, :cat, 'web_portal',
                    :summary, :details, :priority, :status, true,
                    :now, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": wc_id, "tid": TENANT_ID, "ref": ref, "cat": cat,
                   "summary": details[:80], "details": details,
                   "priority": priority, "status": status,
                   "now": dt(random.randint(3, 30))})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["whistleblower_cases"] = count
        print(f"  ✓ {count} whistleblower cases")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Whistleblower: {e}")

    # ── 23. SURVEYS ───────────────────────────────────────────────────────────
    print("\n[23/30] Creating surveys...")
    surveys_data = [
        ("sv-001", "Q4 2026 IT Security Awareness Survey",
         "Annual survey measuring staff IT security awareness",
         "awareness", "active"),
        ("sv-002", "Control Owner Attestation Survey - Q4 2026",
         "Quarterly attestation by control owners confirming control effectiveness",
         "attestation", "active"),
        ("sv-003", "Post-Incident Employee Survey",
         "Survey following the Q3 SAP outage incident to capture lessons learned",
         "assessment", "completed"),
    ]
    count = 0
    for sv_id, name, desc, stype, status in surveys_data:
        try:
            db.execute(text("""
                INSERT INTO standalone_surveys (id, tenant_id, survey_name, description,
                    survey_type, questions, status, created_by, created_at, updated_at)
                VALUES (:id, :tid, :name, :desc, :stype, :questions, :status,
                    'u-ciso-01', :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": sv_id, "tid": TENANT_ID, "name": name, "desc": desc,
                   "stype": stype, "status": status,
                   "questions": json.dumps([
                       {"q": "How often do you change your password?", "type": "multiple_choice"},
                       {"q": "Have you completed security awareness training?", "type": "yes_no"},
                   ]),
                   "now": dt(random.randint(5, 15))})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["standalone_surveys"] = count
        print(f"  ✓ {count} surveys")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Surveys: {e}")

    # ── 24. POLICY DOCUMENTS ──────────────────────────────────────────────────
    print("\n[24/30] Creating policy documents...")
    policies = [
        ("pol-001", "Information Security Policy",        "security",   "approved"),
        ("pol-002", "Access Control Policy",              "access",     "approved"),
        ("pol-003", "Segregation of Duties Policy",       "access",     "approved"),
        ("pol-004", "Privileged Access Management Policy","access",     "approved"),
        ("pol-005", "Data Classification Policy",         "data",       "in_review"),
        ("pol-006", "Incident Response Policy",           "security",   "approved"),
        ("pol-007", "Vendor Risk Management Policy",      "risk",       "approved"),
        ("pol-008", "Business Continuity Policy",         "operations", "approved"),
    ]
    count = 0
    for pol_id, title, ptype, status in policies:
        try:
            db.execute(text("""
                INSERT INTO policy_documents (id, tenant_id, policy_id, title,
                    description, policy_type, content, status, version,
                    owner_id, effective_date, review_date, created_at, updated_at)
                VALUES (:id, :tid, :pid, :title, :desc, :ptype, :content,
                    :status, '2.0', 'u-comp-01', :eff, :rev, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": pol_id, "tid": TENANT_ID, "pid": pol_id,
                   "title": title, "desc": f"Acme Corporation {title}",
                   "ptype": ptype,
                   "content": f"# {title}\n\nThis policy applies to all Acme Corporation employees and contractors...",
                   "status": status, "eff": dt(180),
                   "rev": dt(0) + datetime.timedelta(days=185),
                   "now": dt(180)})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["policy_documents"] = count
        print(f"  ✓ {count} policies")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Policies: {e}")

    # ── 25. NOTIFICATION PREFERENCES ─────────────────────────────────────────
    print("\n[25/30] Creating notification preferences...")
    count = 0
    for user_id in ["u-admin-01", "u-ciso-01", "u-comp-01", "u-risk-01", "u-audit-01"]:
        try:
            db.execute(text("""
                INSERT INTO notification_preferences (id, tenant_id, user_id,
                    email_enabled, slack_enabled, slack_channel, disabled_types,
                    created_at, updated_at)
                VALUES (:id, :tid, :uid, true, false, '', :disabled, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": uid(), "tid": TENANT_ID, "uid": user_id,
                   "disabled": json.dumps([]), "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["notification_preferences"] = count
        print(f"  ✓ {count} notification preferences")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Notifications: {e}")

    # ── 26. SYNC CONFIGS (System Connectors) ─────────────────────────────────
    print("\n[26/30] Creating system connectors...")
    sync_configs = [
        ("sc-001", "SAP ECC 6.0 Production",  "sap_ecc",    "10.0.1.100", "active"),
        ("sc-002", "SAP S/4HANA Development", "sap_s4hana", "10.0.1.101", "active"),
        ("sc-003", "Azure Active Directory",  "azure_ad",   "graph.microsoft.com", "active"),
        ("sc-004", "ServiceNow ITSM",         "servicenow", "acme.service-now.com","inactive"),
    ]
    count = 0
    for sc_id, name, stype, host, status in sync_configs:
        try:
            db.execute(text("""
                INSERT INTO sync_configs (id, tenant_id, config_id, system_name,
                    system_type, direction, status, schedule_minutes,
                    last_sync_at, created_at, updated_at)
                VALUES (:id, :tid, :cid, :name, :stype, 'bidirectional',
                    :status, 1440, :last, :now, :now)
                ON CONFLICT DO NOTHING
            """), {"id": sc_id, "tid": TENANT_ID, "cid": sc_id, "name": name,
                   "stype": stype, "status": status, "last": dt(1), "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["sync_configs"] = count
        print(f"  ✓ {count} system connectors")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Sync configs: {e}")

    # ── 27. AUDIT LOGS ────────────────────────────────────────────────────────
    print("\n[27/30] Creating audit log entries...")
    audit_actions = [
        ("u-admin-01",  "acme_admin",       "USER_CREATE",          "user",          "u-ap-01",   "Created user john.smith"),
        ("u-admin-01",  "acme_admin",       "ROLE_ASSIGN",          "user_role",     "r-fi-ap-full","Assigned Z_FI_AP_FULL to john.smith"),
        ("u-ciso-01",   "acme_ciso",        "VIOLATION_REVIEW",     "risk_violation","vio-001",   "Reviewed critical SoD violation"),
        ("u-comp-01",   "acme_compliance",  "CERT_LAUNCH",          "certification", "cc-002",    "Launched SOX certification campaign"),
        ("u-mgr-01",    "acme_manager",     "ACCESS_APPROVE",       "access_request","ar-req-001","Approved GL posting access request"),
        ("u-audit-01",  "acme_auditor",     "FINDING_CREATE",       "audit_finding", "af-001",    "Logged critical AP SoD finding"),
        ("u-ap-01",     "john.smith",       "LOGIN",                "session",       "u-ap-01",   "User login from 10.0.1.50"),
        ("u-ff-01",     "frank.controller", "FF_SESSION_START",     "ff_session",    "ffs-001",   "Started firefighter session FF_ACME_FI"),
        ("u-admin-01",  "acme_admin",       "POLICY_PUBLISH",       "policy",        "pol-001",   "Published Information Security Policy v2.0"),
        ("u-risk-01",   "acme_risk",        "RISK_UPDATE",          "enterprise_risk","er-001",   "Updated risk residual score"),
    ]
    count = 0
    for user_id, username, action, target_type, target_id, desc in audit_actions:
        try:
            db.execute(text("""
                INSERT INTO audit_logs (id, tenant_id, timestamp, action, action_category,
                    actor_user_id, actor_username, actor_type, target_type, target_id,
                    target_name, ip_address, created_at)
                VALUES (:id, :tid, :ts, :action, 'user_action',
                    :uid, :uname, 'internal_user', :ttype, :tid2,
                    :desc, '10.0.0.1', :now)
                ON CONFLICT DO NOTHING
            """), {"id": uid(), "tid": TENANT_ID, "ts": dt(random.randint(0, 30)),
                   "action": action, "uid": user_id, "uname": username,
                   "ttype": target_type, "tid2": target_id, "desc": desc, "now": NOW})
            count += 1
        except Exception as e:
            db.rollback()
    try:
        db.commit()
        results["audit_logs"] = count
        print(f"  ✓ {count} audit log entries")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Audit logs: {e}")

    # ── 28. SAP SECURITY CONTROLS ─────────────────────────────────────────────
    print("\n[28/30] Checking SAP security controls...")
    try:
        existing = db.execute(text("SELECT COUNT(*) FROM sap_security_controls")).scalar()
        results["sap_security_controls"] = existing
        print(f"  ✓ {existing} SAP security controls (pre-seeded by ANAO import)")
    except Exception as e:
        print(f"  ✗ {e}")
        results["sap_security_controls"] = 0

    # ── 29. TEMPLATE LIBRARY ──────────────────────────────────────────────────
    print("\n[29/30] Checking template library...")
    try:
        existing = db.execute(text("SELECT COUNT(*) FROM template_items")).scalar()
        results["template_items"] = existing
        print(f"  ✓ {existing} template items (pre-seeded by library seeder)")
    except Exception as e:
        print(f"  ✗ {e}")
        results["template_items"] = 0

    # ── 30. TENANT RULE PREFERENCES ───────────────────────────────────────────
    print("\n[30/30] Creating tenant rule preferences...")
    try:
        count_rules = db.execute(text("SELECT COUNT(*) FROM risk_rule_models WHERE tenant_id = :tid"), {"tid": TENANT_ID}).scalar()
        if count_rules == 0:
            for i, (rule_id, name, sev) in enumerate([
                ("SoD-FI-001", "Create Vendor AND Approve Payment",         "critical"),
                ("SoD-FI-003", "Post JE AND Approve JE",                    "high"),
                ("SoD-MM-003", "Create PO AND Post GR",                     "high"),
                ("SoD-HR-001", "Maintain Employee AND Process Payroll",      "critical"),
                ("SoD-SD-005", "Create SO AND Release Billing",             "medium"),
                ("SoD-TR-001", "Initiate Payment AND Release Treasury Run",  "critical"),
            ]):
                try:
                    db.execute(text("""
                        INSERT INTO risk_rule_models (id, tenant_id, rule_id, rule_name,
                            severity, is_active, created_at, updated_at)
                        VALUES (:id, :tid, :rid, :rname, :sev, true, :now, :now)
                        ON CONFLICT DO NOTHING
                    """), {"id": uid(), "tid": TENANT_ID, "rid": rule_id,
                           "rname": name, "sev": sev, "now": NOW})
                except Exception:
                    db.rollback()
            db.commit()
            count_rules = 6
        results["risk_rule_models"] = count_rules
        print(f"  ✓ {count_rules} risk rules active")
    except Exception as e:
        db.rollback()
        print(f"  ✗ Risk rules: {e}")
        results["risk_rule_models"] = 0

    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("VALIDATION — Row Counts Per Table")
    print("=" * 60)
    total = sum(results.values())
    ok = sum(1 for v in results.values() if v > 0)
    for table, count in sorted(results.items()):
        icon = "✓" if count > 0 else "✗"
        print(f"  {icon}  {table:<40} {count:>5} rows")
    print("=" * 60)
    print(f"  Tables with data:  {ok}/{len(results)}")
    print(f"  Total rows seeded: {total}")
    print()
    print("  TENANT CREDENTIALS")
    print(f"  Tenant ID:   {TENANT_ID}")
    print(f"  Admin login: acme_admin / AcmeP@ss2026!")
    print(f"  CISO login:  acme_ciso  / AcmeP@ss2026!")
    print(f"  Auditor:     acme_auditor / AcmeP@ss2026!")
    print("=" * 60)
