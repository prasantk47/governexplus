"""
GovernexPlus — Full Tenant Onboarding Seeder
=============================================
Creates a complete demo tenant "AcmeCorp" with realistic data
across every table in the platform.

Run:  python scripts/full_tenant_seed.py
      or on server: python /opt/governexplus/app/scripts/full_tenant_seed.py
"""
from __future__ import annotations
import os, sys, uuid, random, datetime, hashlib

# Allow running from repo root or scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATABASE_URL", os.getenv("DATABASE_URL", "postgresql://grc_user:G0v3rn3x_Pr0d_2026!@localhost:5432/governexplus"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, echo=False)

TENANT_ID = "acme-corp-demo"
NOW = datetime.datetime.utcnow()

def dt(days_ago=0, hours_ago=0):
    return NOW - datetime.timedelta(days=days_ago, hours=hours_ago)

def uid():
    return str(uuid.uuid4())

# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("GovernexPlus Full Tenant Seeder")
print(f"Tenant: {TENANT_ID}")
print("=" * 60)

with Session(engine) as db:
    # ── 0. Check/clean existing tenant ──────────────────────────────────────
    exists = db.execute(text("SELECT id FROM tenants WHERE tenant_id = :tid"), {"tid": TENANT_ID}).fetchone()
    if exists:
        print(f"Tenant {TENANT_ID} already exists — cleaning up for fresh seed...")
        db.execute(text("DELETE FROM tenants WHERE tenant_id = :tid"), {"tid": TENANT_ID})
        db.commit()

    # ── 1. TENANT ────────────────────────────────────────────────────────────
    print("\n[1/30] Creating tenant...")
    tenant_id_pk = uid()
    db.execute(text("""
        INSERT INTO tenants (id, tenant_id, name, display_name, status, tier, max_users, settings, created_at, updated_at)
        VALUES (:id, :tid, :name, :dn, 'active', 'enterprise', 500,
            '{"modules":["access","risk","audit","process_control","jml","tprm","fraud","bcm","whistleblower","survey"],"sap_systems":["ECC","S4HANA"]}',
            :now, :now)
    """), {"id": tenant_id_pk, "tid": TENANT_ID, "name": "AcmeCorp", "dn": "Acme Corporation Ltd", "now": NOW})
    db.commit()
    print(f"  ✓ Tenant: Acme Corporation Ltd ({TENANT_ID})")

    # ── 2. USERS ─────────────────────────────────────────────────────────────
    print("\n[2/30] Creating users...")
    hashed_pw = pwd_ctx.hash("AcmeP@ss2026!")

    users = [
        ("u-admin",    "acme_admin",      "Adam Admin",       "IT Administration",   "admin",            "tenant_admin"),
        ("u-ciso",     "acme_ciso",       "Clara CISO",       "Information Security","ciso",             "ciso"),
        ("u-comp",     "acme_compliance", "Carl Compliance",  "Compliance",          "compliance_officer","compliance_officer"),
        ("u-risk",     "acme_risk",       "Rachel Risk",      "Risk Management",     "risk_manager",     "risk_manager"),
        ("u-audit",    "acme_auditor",    "Alan Auditor",     "Internal Audit",      "auditor",          "auditor"),
        ("u-mgr",      "acme_manager",    "Mark Manager",     "Finance",             "line_manager",     "line_manager"),
        ("u-user1",    "john.smith",      "John Smith",       "Accounts Payable",    "business_user",    "business_user"),
        ("u-user2",    "sarah.jones",     "Sarah Jones",      "Accounts Receivable", "business_user",    "business_user"),
        ("u-user3",    "mike.chen",       "Mike Chen",        "Procurement",         "business_user",    "business_user"),
        ("u-user4",    "lisa.wang",       "Lisa Wang",        "Treasury",            "business_user",    "business_user"),
        ("u-user5",    "tom.brown",       "Tom Brown",        "HR",                  "business_user",    "business_user"),
        ("u-user6",    "anna.lee",        "Anna Lee",         "Sales",               "business_user",    "business_user"),
        ("u-user7",    "david.kim",       "David Kim",        "IT Security",         "security_admin",   "security_admin"),
        ("u-ff",       "ff_controller",   "Frank Controller", "Finance",             "firefighter",      "business_user"),
        ("u-prov",     "provisioner",     "Pat Provisioner",  "IT Operations",       "provisioner",      "business_user"),
    ]

    for uid_short, username, full_name, dept, role_type, user_type in users:
        emp_id = "EMP" + str(random.randint(1000, 9999))
        db.execute(text("""
            INSERT INTO users (id, tenant_id, username, email, full_name, hashed_password,
                department, employee_id, user_type, is_active, is_admin, created_at, updated_at)
            VALUES (:id, :tid, :un, :email, :fn, :pw, :dept, :emp, :ut, true, :is_admin, :now, :now)
            ON CONFLICT (tenant_id, username) DO NOTHING
        """), {
            "id": uid_short, "tid": TENANT_ID, "un": username,
            "email": f"{username.replace('.','_')}@acmecorp.com",
            "fn": full_name, "pw": hashed_pw, "dept": dept,
            "emp": emp_id, "ut": user_type,
            "is_admin": user_type in ("tenant_admin", "ciso"),
            "now": NOW
        })
    db.commit()
    print(f"  ✓ {len(users)} users created")

    # ── 3. ROLES ─────────────────────────────────────────────────────────────
    print("\n[3/30] Creating SAP roles...")
    roles = [
        ("r-fi-01", "Z_FI_AP_FULL",      "Finance AP Full Access",          "FI", "SAP ECC"),
        ("r-fi-02", "Z_FI_AP_CREATE",     "Finance AP Create Only",          "FI", "SAP ECC"),
        ("r-fi-03", "Z_FI_AP_APPROVE",    "Finance AP Approval",             "FI", "SAP ECC"),
        ("r-fi-04", "Z_FI_GL_POST",       "GL Posting",                      "FI", "SAP ECC"),
        ("r-mm-01", "Z_MM_BUYER",         "MM Purchasing Buyer",             "MM", "SAP ECC"),
        ("r-mm-02", "Z_MM_GR_POST",       "MM Goods Receipt",                "MM", "SAP ECC"),
        ("r-mm-03", "Z_MM_VENDOR_CREATE", "Vendor Master Create",            "MM", "SAP ECC"),
        ("r-sd-01", "Z_SD_ORDER_CREATE",  "SD Sales Order Create",           "SD", "SAP ECC"),
        ("r-sd-02", "Z_SD_BILLING",       "SD Billing Release",              "SD", "SAP ECC"),
        ("r-hr-01", "Z_HR_PAYROLL",       "HR Payroll Processing",           "HR", "SAP HCM"),
        ("r-hr-02", "Z_HR_MAINTAIN",      "HR Employee Maintain",            "HR", "SAP HCM"),
        ("r-ba-01", "Z_BC_USER_ADMIN",    "BC User Administration",          "BC", "SAP ECC"),
        ("r-tr-01", "Z_TR_PAYMENT",       "Treasury Payment Run",            "TR", "SAP ECC"),
        ("r-basis", "SAP_ALL",            "Full SAP Authorization (Basis)",  "BC", "SAP ECC"),
    ]
    for rid, rname, rdesc, rcat, sys_name in roles:
        db.execute(text("""
            INSERT INTO roles (id, tenant_id, role_name, description, category, system_name,
                is_active, created_at, updated_at)
            VALUES (:id, :tid, :rn, :rd, :rc, :sys, true, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": rid, "tid": TENANT_ID, "rn": rname, "rd": rdesc,
               "rc": rcat, "sys": sys_name, "now": NOW})
    db.commit()
    print(f"  ✓ {len(roles)} SAP roles created")

    # ── 4. USER-ROLE ASSIGNMENTS (including SoD conflicts) ──────────────────
    print("\n[4/30] Assigning roles to users...")
    assignments = [
        ("u-user1", "r-fi-01"),  # John: AP Full — conflict
        ("u-user1", "r-fi-03"),  # John: AP Approve — SoD conflict with AP Full
        ("u-user1", "r-mm-03"),  # John: Vendor Create — triple conflict
        ("u-user2", "r-fi-02"),  # Sarah: AP Create only — clean
        ("u-user3", "r-mm-01"),  # Mike: Buyer
        ("u-user3", "r-mm-02"),  # Mike: GR Post — SoD conflict
        ("u-user4", "r-tr-01"),  # Lisa: Treasury
        ("u-user5", "r-hr-01"),  # Tom: Payroll
        ("u-user5", "r-hr-02"),  # Tom: HR Maintain — SoD conflict
        ("u-user6", "r-sd-01"),  # Anna: Sales Orders
        ("u-user6", "r-sd-02"),  # Anna: Billing — SoD conflict
        ("u-mgr",   "r-fi-03"),  # Mark: Approval (clean)
        ("u-admin", "r-ba-01"),  # Admin: User Admin
        ("u-ff",    "r-fi-04"),  # Frank: GL Post
    ]
    for usr, rol in assignments:
        db.execute(text("""
            INSERT INTO user_roles (id, tenant_id, user_id, role_id, assigned_at, assigned_by, is_active, created_at, updated_at)
            VALUES (:id, :tid, :uid, :rid, :now, 'seed', true, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": uid(), "tid": TENANT_ID, "uid": usr, "rid": rol, "now": NOW})
    db.commit()
    print(f"  ✓ {len(assignments)} user-role assignments")

    # ── 5. RISK VIOLATIONS ───────────────────────────────────────────────────
    print("\n[5/30] Creating risk violations...")
    violations = [
        ("v-001", "u-user1", "SoD-FI-001", "Create Vendor AND Approve Payment", "critical", "open"),
        ("v-002", "u-user1", "SoD-FI-003", "Post Journal Entry AND Approve Journal Entry", "high", "open"),
        ("v-003", "u-user3", "SoD-MM-003", "Create Purchase Order AND Post Goods Receipt", "high", "open"),
        ("v-004", "u-user5", "SoD-HR-001", "Maintain Employee AND Process Payroll", "critical", "open"),
        ("v-005", "u-user6", "SoD-SD-005", "Create Sales Order AND Release Billing Document", "medium", "mitigated"),
        ("v-006", "u-user1", "SoD-MM-001", "Create Vendor AND Create Purchase Order", "high", "open"),
        ("v-007", "u-user2", "SoD-FI-002", "Approve Payment AND Release Payment Run", "medium", "open"),
        ("v-008", "u-user4", "SoD-TR-001", "Initiate Payment AND Release Payment (Treasury)", "critical", "in_review"),
    ]
    for vid, user_id, rule_id, desc, sev, status in violations:
        score_map = {"critical": 90, "high": 70, "medium": 50, "low": 25}
        db.execute(text("""
            INSERT INTO risk_violations (id, tenant_id, user_id, rule_id, description,
                severity_score, status, detected_at, created_at, updated_at)
            VALUES (:id, :tid, :uid, :rid, :desc, :score, :status, :detected, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": vid, "tid": TENANT_ID, "uid": user_id, "rid": rule_id,
               "desc": desc, "score": score_map[sev], "status": status,
               "detected": dt(random.randint(1, 30)), "now": NOW})
    db.commit()
    print(f"  ✓ {len(violations)} risk violations")

    # ── 6. ACCESS REQUESTS ───────────────────────────────────────────────────
    print("\n[6/30] Creating access requests...")
    requests_data = [
        ("ar-001", "u-user2", "Sarah needs GL posting for month-end close", "approved"),
        ("ar-002", "u-user3", "Mike needs billing role for Q4 project", "pending_approval"),
        ("ar-003", "u-user6", "Anna needs treasury view for reporting", "approved"),
        ("ar-004", "u-user1", "John needs HR read access for workforce planning", "rejected"),
        ("ar-005", "u-user5", "Tom needs SD access for cross-departmental project", "draft"),
        ("ar-006", "u-user7", "David needs Basis admin for security review", "approved"),
    ]
    for ar_id, user_id, justification, status in requests_data:
        db.execute(text("""
            INSERT INTO access_requests (id, tenant_id, requester_id, justification,
                status, priority, business_justification, created_at, updated_at)
            VALUES (:id, :tid, :uid, :just, :status, 'normal', :just, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": ar_id, "tid": TENANT_ID, "uid": user_id,
               "just": justification, "status": status, "now": dt(random.randint(0, 14))})
    db.commit()
    print(f"  ✓ {len(requests_data)} access requests")

    # ── 7. MITIGATION CONTROLS ───────────────────────────────────────────────
    print("\n[7/30] Creating mitigation controls...")
    mitigations = [
        ("mc-001", "Compensating Control: Dual Approval", "Requires secondary approval from Finance Director for all AP transactions", "detective"),
        ("mc-002", "Monthly Vendor Reconciliation", "Monthly reconciliation of new vendors vs approved vendor list reviewed by CFO", "detective"),
        ("mc-003", "Segregated GR Log Review", "Daily review of goods receipts by Procurement Manager independent of PO creator", "detective"),
        ("mc-004", "Payroll Supervisor Sign-off", "Payroll runs require explicit supervisor sign-off before execution", "preventive"),
        ("mc-005", "Automated Payment Threshold Alert", "System alert triggered for payments exceeding AUD 50,000 to Finance Controller", "detective"),
    ]
    for mc_id, name, desc, ctrl_type in mitigations:
        db.execute(text("""
            INSERT INTO mitigation_controls (id, tenant_id, name, description, control_type,
                status, owner, effectiveness, created_at, updated_at)
            VALUES (:id, :tid, :name, :desc, :ct, 'active', 'u-comp', 'effective', :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": mc_id, "tid": TENANT_ID, "name": name, "desc": desc,
               "ct": ctrl_type, "now": NOW})
    db.commit()
    print(f"  ✓ {len(mitigations)} mitigation controls")

    # ── 8. FIREFIGHTER ───────────────────────────────────────────────────────
    print("\n[8/30] Creating firefighter data...")
    # FF ID Configs
    ff_ids = [
        ("ffc-001", "FF_ACME_FI", "Finance Emergency Access", "Finance"),
        ("ffc-002", "FF_ACME_BASIS", "Basis Emergency Access", "IT"),
        ("ffc-003", "FF_ACME_HR", "HR Emergency Access", "HR"),
    ]
    for fid, ff_id, desc, scope in ff_ids:
        db.execute(text("""
            INSERT INTO firefighter_id_configs (id, tenant_id, firefighter_id, description,
                scope, is_active, created_at, updated_at)
            VALUES (:id, :tid, :ffid, :desc, :scope, true, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": fid, "tid": TENANT_ID, "ffid": ff_id, "desc": desc, "scope": scope, "now": NOW})

    # FF Requests
    ff_requests = [
        ("ffr-001", "u-ff",    "ffc-001", "Critical month-end AP posting failure", "approved"),
        ("ffr-002", "u-admin", "ffc-002", "Emergency basis configuration for system outage", "approved"),
        ("ffr-003", "u-user7", "ffc-001", "Urgent vendor payment for system maintenance", "pending"),
        ("ffr-004", "u-user5", "ffc-003", "Emergency payroll correction for terminated employee", "rejected"),
    ]
    for fr_id, user_id, ff_cfg_id, reason, status in ff_requests:
        db.execute(text("""
            INSERT INTO firefighter_requests (id, tenant_id, requester_id, firefighter_config_id,
                reason, status, requested_at, created_at, updated_at)
            VALUES (:id, :tid, :uid, :ffc, :reason, :status, :now, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": fr_id, "tid": TENANT_ID, "uid": user_id, "ffc": ff_cfg_id,
               "reason": reason, "status": status, "now": dt(random.randint(1, 10))})

    # FF Sessions
    db.execute(text("""
        INSERT INTO firefighter_sessions (id, tenant_id, request_id, user_id, firefighter_id,
            status, started_at, ended_at, created_at, updated_at)
        VALUES (:id, :tid, :req, :uid, 'FF_ACME_FI', 'completed', :start, :end, :now, :now)
        ON CONFLICT DO NOTHING
    """), {"id": "ffs-001", "tid": TENANT_ID, "req": "ffr-001", "uid": "u-ff",
           "start": dt(5, 2), "end": dt(5, 0), "now": dt(5)})

    # FF Activities
    for i, activity in enumerate(["Login to SAP ECC", "Executed T-Code FB60", "Posted Invoice #INV-2026-4501", "Logged out"]):
        db.execute(text("""
            INSERT INTO firefighter_activities (id, tenant_id, session_id, activity_type,
                description, transaction_code, timestamp, created_at)
            VALUES (:id, :tid, 'ffs-001', 'transaction', :desc, :tcode, :ts, :now)
            ON CONFLICT DO NOTHING
        """), {"id": f"ffa-{i:03d}", "tid": TENANT_ID, "desc": activity,
               "tcode": ["", "FB60", "FB60", ""][i],
               "ts": dt(5, 2 - i * 0.3), "now": NOW})
    db.commit()
    print(f"  ✓ {len(ff_ids)} FF IDs, {len(ff_requests)} requests, 1 session, 4 activities")

    # ── 9. CERTIFICATION CAMPAIGNS ───────────────────────────────────────────
    print("\n[9/30] Creating certification campaigns...")
    campaigns = [
        ("cc-001", "Q4 2026 User Access Review", "Quarterly review of all user access rights", "completed", dt(60), dt(30)),
        ("cc-002", "SOX Critical Controls Certification", "Annual SOX 404 control certification", "active",   dt(15), dt(0) + datetime.timedelta(days=15)),
        ("cc-003", "Privileged Access Certification",     "Semi-annual privileged access review",  "draft",    dt(2),  dt(0)  + datetime.timedelta(days=30)),
    ]
    for cc_id, name, desc, status, start, end in campaigns:
        db.execute(text("""
            INSERT INTO certification_campaigns (id, tenant_id, name, description, status,
                campaign_type, start_date, end_date, created_by, created_at, updated_at)
            VALUES (:id, :tid, :name, :desc, :status, 'access_review', :start, :end,
                'u-comp', :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": cc_id, "tid": TENANT_ID, "name": name, "desc": desc,
               "status": status, "start": start, "end": end, "now": NOW})
    db.commit()
    print(f"  ✓ {len(campaigns)} certification campaigns")

    # ── 10. ENTERPRISE RISK REGISTER ─────────────────────────────────────────
    print("\n[10/30] Creating risk register...")
    risks = [
        ("er-001", "Unauthorized Financial Transactions",   "Financial",   5, 5, "open"),
        ("er-002", "Excessive User Privileges",             "Access",      4, 4, "in_treatment"),
        ("er-003", "Payroll Fraud via Segregation Failure", "Financial",   5, 4, "open"),
        ("er-004", "SAP System Downtime - Month End",       "Operational", 3, 5, "in_treatment"),
        ("er-005", "Vendor Master Data Manipulation",       "Financial",   4, 5, "open"),
        ("er-006", "Inadequate Audit Trail Coverage",       "Compliance",  3, 4, "open"),
        ("er-007", "Data Breach via Excessive Access",      "IT Security", 4, 5, "in_treatment"),
        ("er-008", "Regulatory Non-Compliance (SOX 404)",   "Compliance",  2, 5, "monitoring"),
    ]
    for rid, title, cat, likelihood, impact, status in risks:
        risk_score = likelihood * impact
        db.execute(text("""
            INSERT INTO enterprise_risks (id, tenant_id, title, description, category,
                likelihood, impact, inherent_risk_score, residual_risk_score,
                status, owner_id, created_at, updated_at)
            VALUES (:id, :tid, :title, :desc, :cat, :lik, :imp, :score, :rscore,
                :status, 'u-risk', :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": rid, "tid": TENANT_ID, "title": title,
               "desc": f"Risk of {title.lower()} impacting Acme Corporation operations and compliance posture.",
               "cat": cat, "lik": likelihood, "imp": impact,
               "score": risk_score, "rscore": max(risk_score - random.randint(2, 6), 2),
               "status": status, "now": dt(random.randint(1, 90))})
    db.commit()
    print(f"  ✓ {len(risks)} enterprise risks")

    # ── 11. KRIs ─────────────────────────────────────────────────────────────
    print("\n[11/30] Creating KRIs...")
    kris = [
        ("kri-001", "SoD Violation Rate",           "% of users with active SoD conflicts",   8.5, 5.0, 10.0, "breached"),
        ("kri-002", "Unreviewed Privileged Access",  "# FF sessions without formal review",     3,   0,   5,   "at_risk"),
        ("kri-003", "Overdue Certifications",        "# certification items past due date",     12,  0,   10,  "breached"),
        ("kri-004", "Failed Login Attempts",         "# failed logins per day (avg)",           45,  0,   100, "normal"),
        ("kri-005", "Critical Open Findings",        "# critical audit findings open > 30 days", 4, 0,   3,   "breached"),
    ]
    for kri_id, name, desc, current, low, high, status in kris:
        db.execute(text("""
            INSERT INTO key_risk_indicators (id, tenant_id, name, description, current_value,
                lower_threshold, upper_threshold, status, frequency, owner_id, risk_id,
                created_at, updated_at)
            VALUES (:id, :tid, :name, :desc, :curr, :low, :high, :status,
                'monthly', 'u-risk', 'er-002', :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": kri_id, "tid": TENANT_ID, "name": name, "desc": desc,
               "curr": current, "low": low, "high": high, "status": status, "now": NOW})
    db.commit()
    print(f"  ✓ {len(kris)} KRIs")

    # ── 12. PROCESS CONTROLS ─────────────────────────────────────────────────
    print("\n[12/30] Creating process controls...")
    controls = [
        ("pc-001", "AP Invoice Approval Workflow",        "Three-way match enforced for all invoices > AUD 5,000", "preventive", "automated"),
        ("pc-002", "Monthly Bank Reconciliation",         "All bank accounts reconciled monthly by Finance Manager", "detective", "manual"),
        ("pc-003", "Vendor Master Change Approval",       "All vendor master changes require dual approval",        "preventive", "hybrid"),
        ("pc-004", "Quarterly Access Review",             "All user access reviewed and recertified quarterly",     "detective", "manual"),
        ("pc-005", "Automated SoD Conflict Detection",    "Real-time SoD violation alerts via GovernexPlus ARA",    "detective", "automated"),
        ("pc-006", "Payroll Calculation Verification",    "Independent verification of payroll calculations",       "detective", "manual"),
        ("pc-007", "IT Change Management",                "All SAP changes go through formal change management",    "preventive", "hybrid"),
        ("pc-008", "Privileged Access Monitoring",        "All firefighter sessions logged and reviewed",           "detective", "automated"),
    ]
    for pc_id, name, desc, ctrl_type, nature in controls:
        db.execute(text("""
            INSERT INTO process_controls (id, tenant_id, name, description, control_type,
                control_nature, frequency, status, owner_id, created_at, updated_at)
            VALUES (:id, :tid, :name, :desc, :ct, :cn, 'monthly', 'active', 'u-comp', :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": pc_id, "tid": TENANT_ID, "name": name, "desc": desc,
               "ct": ctrl_type, "cn": nature, "now": dt(random.randint(30, 120))})
    db.commit()
    print(f"  ✓ {len(controls)} process controls")

    # ── 13. CONTROL TESTS ────────────────────────────────────────────────────
    print("\n[13/30] Creating control tests...")
    tests = [
        ("ct-001", "pc-001", "pass",    "3-way match verified for 100% of Q3 invoices. 0 exceptions found."),
        ("ct-002", "pc-002", "pass",    "All 12 bank accounts reconciled. 2 timing differences <AUD 500 explained."),
        ("ct-003", "pc-003", "fail",    "3 vendor master changes found without dual approval. Escalated to manager."),
        ("ct-004", "pc-004", "pass",    "Q3 access review completed. 14 users had access removed."),
        ("ct-005", "pc-005", "pass",    "ARA running continuously. 8 new violations detected and notified same day."),
        ("ct-006", "pc-006", "partial", "Payroll verification performed. 1 employee record had incorrect allowance."),
    ]
    for ct_id, ctrl_id, result, notes in tests:
        db.execute(text("""
            INSERT INTO control_tests (id, tenant_id, control_id, test_date, result,
                notes, tested_by, sample_size, exceptions_found, created_at, updated_at)
            VALUES (:id, :tid, :cid, :tdate, :result, :notes, 'u-audit',
                :sample, :exc, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": ct_id, "tid": TENANT_ID, "cid": ctrl_id, "tdate": dt(random.randint(1, 30)),
               "result": result, "notes": notes,
               "sample": random.randint(20, 100),
               "exc": 0 if result == "pass" else random.randint(1, 5),
               "now": dt(random.randint(1, 30))})
    db.commit()
    print(f"  ✓ {len(tests)} control tests")

    # ── 14. CONTROL DEFICIENCIES ──────────────────────────────────────────────
    print("\n[14/30] Creating control deficiencies...")
    deficiencies = [
        ("cd-001", "pc-003", "significant_deficiency", "Vendor master change approval bypassed", "open"),
        ("cd-002", "pc-006", "deficiency",             "Payroll allowance miscalculation",        "in_remediation"),
        ("cd-003", "pc-004", "material_weakness",      "Access reviews delayed by 45 days",       "remediated"),
    ]
    for did, ctrl_id, severity, desc, status in deficiencies:
        db.execute(text("""
            INSERT INTO control_deficiencies (id, tenant_id, control_id, severity, description,
                status, identified_date, owner_id, created_at, updated_at)
            VALUES (:id, :tid, :cid, :sev, :desc, :status, :idate, 'u-comp', :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": did, "tid": TENANT_ID, "cid": ctrl_id, "sev": severity,
               "desc": desc, "status": status,
               "idate": dt(random.randint(5, 30)), "now": dt(random.randint(0, 5))})
    db.commit()
    print(f"  ✓ {len(deficiencies)} control deficiencies")

    # ── 15. AUDIT MANAGEMENT ─────────────────────────────────────────────────
    print("\n[15/30] Creating audit management data...")
    # Auditable entities
    audit_entities = [
        ("ae-001", "Accounts Payable Process",        "process"),
        ("ae-002", "Payroll Processing",              "process"),
        ("ae-003", "SAP ECC System Security",         "system"),
        ("ae-004", "Vendor Management",               "process"),
        ("ae-005", "Financial Reporting Controls",    "control"),
    ]
    for ae_id, name, etype in audit_entities:
        db.execute(text("""
            INSERT INTO auditable_entities (id, tenant_id, name, entity_type, risk_rating,
                last_audit_date, created_at, updated_at)
            VALUES (:id, :tid, :name, :etype, 'high', :last, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": ae_id, "tid": TENANT_ID, "name": name, "etype": etype,
               "last": dt(random.randint(90, 365)), "now": NOW})

    # Audit plans
    db.execute(text("""
        INSERT INTO audit_plans (id, tenant_id, name, description, status, plan_type,
            fiscal_year, start_date, end_date, created_by, created_at, updated_at)
        VALUES (:id, :tid, 'FY2026 Internal Audit Plan',
            'Annual risk-based internal audit plan for FY2026',
            'approved', 'annual', 2026, :start, :end, 'u-audit', :now, :now)
        ON CONFLICT DO NOTHING
    """), {"id": "ap-001", "tid": TENANT_ID, "start": dt(300), "end": dt(0) + datetime.timedelta(days=65), "now": dt(300)})

    # Audit engagement
    db.execute(text("""
        INSERT INTO audit_engagements (id, tenant_id, plan_id, name, description,
            engagement_type, status, risk_rating, auditable_entity_id,
            lead_auditor_id, start_date, end_date, created_at, updated_at)
        VALUES (:id, :tid, 'ap-001',
            'Accounts Payable SoD Controls Review',
            'Review of SoD controls in AP process and effectiveness of compensating controls',
            'controls', 'fieldwork', 'high', 'ae-001',
            'u-audit', :start, :end, :now, :now)
        ON CONFLICT DO NOTHING
    """), {"id": "ae-eng-001", "tid": TENANT_ID, "start": dt(20), "end": dt(0) + datetime.timedelta(days=10), "now": dt(20)})

    # Audit findings
    findings = [
        ("af-001", "ae-eng-001", "Segregation of Duties Violation in AP",
         "6 users identified with conflicting AP roles (create vendor AND approve payment). High risk of unauthorized transactions.",
         "critical", "open"),
        ("af-002", "ae-eng-001", "Vendor Master Change Controls Inadequate",
         "Change approval workflow bypassed in 3 instances. No detective control in place.",
         "high", "in_progress"),
        ("af-003", "ae-eng-001", "Excessive System Access - Finance Users",
         "4 finance users have SAP_ALL profile beyond business need.",
         "high", "open"),
    ]
    for fid, eng_id, title, desc, severity, status in findings:
        db.execute(text("""
            INSERT INTO audit_findings (id, tenant_id, engagement_id, title, description,
                severity, status, owner_id, due_date, created_at, updated_at)
            VALUES (:id, :tid, :eid, :title, :desc, :sev, :status,
                'u-audit', :due, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": fid, "tid": TENANT_ID, "eid": eng_id, "title": title,
               "desc": desc, "sev": severity, "status": status,
               "due": dt(0) + datetime.timedelta(days=30), "now": dt(5)})
    db.commit()
    print(f"  ✓ {len(audit_entities)} entities, 1 plan, 1 engagement, {len(findings)} findings")

    # ── 16. JML POLICIES & EVENTS ────────────────────────────────────────────
    print("\n[16/30] Creating JML policies and events...")
    jml_policies = [
        ("jml-pol-001", "Joiner Policy - Standard Employee",    "joiner",    "Provision standard access on day 1 based on role"),
        ("jml-pol-002", "Mover Policy - Departmental Transfer", "mover",     "Adjust access within 24h of confirmed transfer"),
        ("jml-pol-003", "Leaver Policy - Resignation",         "leaver",    "Revoke all access on last working day"),
        ("jml-pol-004", "Leaver Policy - Termination (Cause)", "leaver",    "Immediate access revocation upon termination for cause"),
    ]
    for pol_id, name, pol_type, desc in jml_policies:
        db.execute(text("""
            INSERT INTO jml_policies (id, tenant_id, name, policy_type, description,
                is_active, created_at, updated_at)
            VALUES (:id, :tid, :name, :ptype, :desc, true, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": pol_id, "tid": TENANT_ID, "name": name, "ptype": pol_type, "desc": desc, "now": NOW})

    jml_events = [
        ("jml-evt-001", "joiner",    "u-user2", "jml-pol-001", "completed", "New hire onboarded — AR Specialist"),
        ("jml-evt-002", "mover",     "u-user3", "jml-pol-002", "completed", "Transfer from Purchasing to Supply Chain"),
        ("jml-evt-003", "leaver",    "u-user4", "jml-pol-003", "pending",   "Resignation submitted — last day Nov 15"),
        ("jml-evt-004", "leaver",    "u-user6", "jml-pol-004", "completed", "Immediate termination — policy violation"),
    ]
    for evt_id, evt_type, user_id, pol_id, status, notes in jml_events:
        db.execute(text("""
            INSERT INTO jml_events (id, tenant_id, event_type, user_id, policy_id,
                status, notes, triggered_at, created_at, updated_at)
            VALUES (:id, :tid, :etype, :uid, :pid, :status, :notes, :now, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": evt_id, "tid": TENANT_ID, "etype": evt_type, "uid": user_id,
               "pid": pol_id, "status": status, "notes": notes,
               "now": dt(random.randint(1, 20))})
    db.commit()
    print(f"  ✓ {len(jml_policies)} JML policies, {len(jml_events)} events")

    # ── 17. TPRM ─────────────────────────────────────────────────────────────
    print("\n[17/30] Creating TPRM vendors...")
    vendors = [
        ("ven-001", "CloudSoft Solutions",     "IT Services",   "critical",    "active",   "high"),
        ("ven-002", "Apex Consulting Group",   "Consulting",    "high",        "active",   "medium"),
        ("ven-003", "FastShip Logistics",      "Logistics",     "medium",      "active",   "low"),
        ("ven-004", "DataSafe Analytics",      "Data Services", "critical",    "active",   "high"),
        ("ven-005", "OfficeMax Supplies",      "Procurement",   "low",         "active",   "low"),
        ("ven-006", "TechMaint Systems",       "Maintenance",   "high",        "suspended","critical"),
    ]
    for vid, name, cat, criticality, status, risk_rating in vendors:
        db.execute(text("""
            INSERT INTO vendors (id, tenant_id, name, category, criticality, status,
                risk_rating, contact_email, created_at, updated_at)
            VALUES (:id, :tid, :name, :cat, :crit, :status, :rr,
                :email, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": vid, "tid": TENANT_ID, "name": name, "cat": cat,
               "crit": criticality, "status": status, "rr": risk_rating,
               "email": f"vendor@{name.lower().replace(' ','-')}.com", "now": NOW})

    # Vendor assessments
    db.execute(text("""
        INSERT INTO vendor_assessments (id, tenant_id, vendor_id, assessment_date,
            overall_score, status, assessed_by, created_at, updated_at)
        VALUES (:id, :tid, 'ven-001', :adate, 72, 'completed', 'u-risk', :now, :now)
        ON CONFLICT DO NOTHING
    """), {"id": "va-001", "tid": TENANT_ID, "adate": dt(45), "now": dt(45)})

    # Vendor issues
    db.execute(text("""
        INSERT INTO vendor_issues (id, tenant_id, vendor_id, title, description,
            severity, status, raised_by, created_at, updated_at)
        VALUES (:id, :tid, 'ven-006', 'Data Access Breach Incident',
            'Vendor accessed client data outside contractual scope during maintenance window.',
            'critical', 'open', 'u-ciso', :now, :now)
        ON CONFLICT DO NOTHING
    """), {"id": "vi-001", "tid": TENANT_ID, "now": dt(3)})
    db.commit()
    print(f"  ✓ {len(vendors)} vendors, 1 assessment, 1 issue")

    # ── 18. FRAUD DETECTION ──────────────────────────────────────────────────
    print("\n[18/30] Creating fraud detection data...")
    fraud_rules = [
        ("fr-001", "Duplicate Vendor Payment Detection",  "payment_duplicate",  "Flags duplicate invoice numbers or amounts within 30 days"),
        ("fr-002", "Round Dollar Amount Anomaly",         "payment_anomaly",    "Flags payments in exact round amounts (common fraud indicator)"),
        ("fr-003", "After-Hours Transaction Monitor",     "access_anomaly",     "Flags financial transactions outside business hours"),
        ("fr-004", "Dormant Account Activation",         "access_anomaly",     "Flags accounts unused for 90+ days suddenly becoming active"),
        ("fr-005", "Vendor Self-Approval Detection",      "authorization_bypass","User approves payment to vendor they created"),
    ]
    for frid, name, ftype, desc in fraud_rules:
        db.execute(text("""
            INSERT INTO fraud_rules (id, tenant_id, name, rule_type, description,
                is_active, threshold, created_at, updated_at)
            VALUES (:id, :tid, :name, :rtype, :desc, true, 3, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": frid, "tid": TENANT_ID, "name": name, "rtype": ftype, "desc": desc, "now": NOW})

    fraud_alerts = [
        ("fa-001", "fr-001", "u-user1", "Duplicate invoice INV-2026-4421 detected — AUD 45,000",          "high",     "open"),
        ("fa-002", "fr-003", "u-user3", "Purchase Order raised at 11:47 PM on Sunday",                    "medium",   "investigating"),
        ("fa-003", "fr-005", "u-user1", "User JSMITH approved payment to vendor JSMITH created",           "critical", "open"),
        ("fa-004", "fr-002", "u-user4", "3 payments of exactly AUD 10,000 to same vendor in 7 days",      "high",     "open"),
    ]
    for fa_id, rule_id, user_id, desc, severity, status in fraud_alerts:
        db.execute(text("""
            INSERT INTO fraud_alerts (id, tenant_id, rule_id, user_id, description,
                severity, status, detected_at, created_at, updated_at)
            VALUES (:id, :tid, :rid, :uid, :desc, :sev, :status, :det, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": fa_id, "tid": TENANT_ID, "rid": rule_id, "uid": user_id,
               "desc": desc, "sev": severity, "status": status,
               "det": dt(random.randint(0, 7)), "now": NOW})

    # Fraud case
    db.execute(text("""
        INSERT INTO fraud_cases (id, tenant_id, title, description, severity, status,
            assigned_to, created_at, updated_at)
        VALUES (:id, :tid, 'AP Vendor Self-Approval Investigation',
            'Investigation into unauthorized vendor payment approvals by AP user JSMITH. Potential financial exposure AUD 45,000.',
            'critical', 'open', 'u-ciso', :now, :now)
        ON CONFLICT DO NOTHING
    """), {"id": "fc-001", "tid": TENANT_ID, "now": dt(2)})
    db.commit()
    print(f"  ✓ {len(fraud_rules)} fraud rules, {len(fraud_alerts)} alerts, 1 case")

    # ── 19. BCM ──────────────────────────────────────────────────────────────
    print("\n[19/30] Creating BCM data...")
    # BIA Records
    bias = [
        ("bia-001", "Finance Payment Processing",  "critical", 4,  "Finance"),
        ("bia-002", "SAP ECC Core Operations",     "critical", 2,  "IT"),
        ("bia-003", "Payroll Run",                 "critical", 1,  "HR"),
        ("bia-004", "Procurement Ordering",        "high",     8,  "Procurement"),
        ("bia-005", "Customer Order Processing",   "high",     24, "Sales"),
    ]
    for bid, name, crit, rto_hours, dept in bias:
        db.execute(text("""
            INSERT INTO bia_records (id, tenant_id, process_name, criticality,
                rto_hours, rpo_hours, department, created_at, updated_at)
            VALUES (:id, :tid, :name, :crit, :rto, :rpo, :dept, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": bid, "tid": TENANT_ID, "name": name, "crit": crit,
               "rto": rto_hours, "rpo": rto_hours // 2 + 1, "dept": dept, "now": NOW})

    # BCM Plans
    bcm_plans = [
        ("bcp-001", "SAP ECC Business Continuity Plan",     "it_disaster_recovery", "approved"),
        ("bcp-002", "Finance Operations Continuity Plan",   "business_continuity",  "approved"),
        ("bcp-003", "HR Payroll Contingency Plan",          "business_continuity",  "draft"),
    ]
    for bp_id, name, plan_type, status in bcm_plans:
        db.execute(text("""
            INSERT INTO bcm_plans (id, tenant_id, name, plan_type, status,
                owner_id, version, last_tested, created_at, updated_at)
            VALUES (:id, :tid, :name, :ptype, :status, 'u-admin', '1.0',
                :tested, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": bp_id, "tid": TENANT_ID, "name": name, "ptype": plan_type,
               "status": status, "tested": dt(90), "now": dt(90)})

    # BCM Test exercise
    db.execute(text("""
        INSERT INTO bcm_test_exercises (id, tenant_id, plan_id, exercise_type,
            exercise_date, outcome, notes, created_at, updated_at)
        VALUES (:id, :tid, 'bcp-001', 'tabletop', :edate, 'successful',
            'SAP failover tested. RTO of 2 hours achieved. Minor gap in data sync identified.',
            :now, :now)
        ON CONFLICT DO NOTHING
    """), {"id": "bce-001", "tid": TENANT_ID, "edate": dt(60), "now": dt(60)})
    db.commit()
    print(f"  ✓ {len(bias)} BIA records, {len(bcm_plans)} BCM plans, 1 exercise")

    # ── 20. WHISTLEBLOWER ────────────────────────────────────────────────────
    print("\n[20/30] Creating whistleblower cases...")
    wb_cases = [
        ("wb-001", "REF-2026-001", "Suspected vendor kickback arrangement in procurement", "fraud",           "critical", "investigating"),
        ("wb-002", "REF-2026-002", "Manager requesting inappropriate system access",       "policy_violation", "high",     "open"),
        ("wb-003", "REF-2026-003", "Possible payroll manipulation for departed employee",  "fraud",           "high",     "resolved"),
    ]
    for wc_id, ref, desc, cat, priority, status in wb_cases:
        db.execute(text("""
            INSERT INTO whistleblower_cases (id, tenant_id, case_reference, description,
                category, priority, status, is_anonymous, created_at, updated_at)
            VALUES (:id, :tid, :ref, :desc, :cat, :priority, :status, true, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": wc_id, "tid": TENANT_ID, "ref": ref, "desc": desc,
               "cat": cat, "priority": priority, "status": status,
               "now": dt(random.randint(3, 30))})
    db.commit()
    print(f"  ✓ {len(wb_cases)} whistleblower cases")

    # ── 21. SURVEYS ──────────────────────────────────────────────────────────
    print("\n[21/30] Creating surveys...")
    db.execute(text("""
        INSERT INTO standalone_surveys (id, tenant_id, title, description, survey_type,
            status, created_by, created_at, updated_at)
        VALUES (:id, :tid, 'Q4 2026 IT Security Awareness Survey',
            'Annual survey to measure staff IT security awareness and compliance knowledge',
            'awareness', 'active', 'u-ciso', :now, :now)
        ON CONFLICT DO NOTHING
    """), {"id": "sv-001", "tid": TENANT_ID, "now": dt(10)})
    db.execute(text("""
        INSERT INTO standalone_surveys (id, tenant_id, title, description, survey_type,
            status, created_by, created_at, updated_at)
        VALUES (:id, :tid, 'Control Owner Attestation Survey - Q4 2026',
            'Quarterly attestation by control owners confirming control effectiveness',
            'attestation', 'active', 'u-comp', :now, :now)
        ON CONFLICT DO NOTHING
    """), {"id": "sv-002", "tid": TENANT_ID, "now": dt(5)})
    db.commit()
    print("  ✓ 2 surveys")

    # ── 22. ORG UNITS ────────────────────────────────────────────────────────
    print("\n[22/30] Creating org units...")
    org_units = [
        ("ou-001", None,       "Acme Corporation",  "company"),
        ("ou-002", "ou-001",   "Finance",           "division"),
        ("ou-003", "ou-001",   "Information Technology", "division"),
        ("ou-004", "ou-001",   "Human Resources",   "division"),
        ("ou-005", "ou-001",   "Procurement",       "division"),
        ("ou-006", "ou-002",   "Accounts Payable",  "department"),
        ("ou-007", "ou-002",   "Accounts Receivable","department"),
        ("ou-008", "ou-002",   "Treasury",          "department"),
        ("ou-009", "ou-003",   "IT Security",       "department"),
        ("ou-010", "ou-003",   "SAP Basis",         "department"),
    ]
    for ou_id, parent, name, unit_type in org_units:
        db.execute(text("""
            INSERT INTO org_units (id, tenant_id, name, unit_type, parent_id, is_active, created_at, updated_at)
            VALUES (:id, :tid, :name, :ut, :parent, true, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": ou_id, "tid": TENANT_ID, "name": name, "ut": unit_type,
               "parent": parent, "now": NOW})
    db.commit()
    print(f"  ✓ {len(org_units)} org units")

    # ── 23. SECURITY CONTROLS ────────────────────────────────────────────────
    print("\n[23/30] Creating security controls...")
    sec_controls = [
        ("sc-001", "SAP-AUTH-001", "Password Complexity Policy",          "Access Control",   "SAP ECC"),
        ("sc-002", "SAP-AUTH-002", "Session Timeout Configuration",       "Access Control",   "SAP ECC"),
        ("sc-003", "SAP-AUTH-003", "Failed Login Lockout Policy",         "Access Control",   "SAP ECC"),
        ("sc-004", "SAP-LOG-001",  "Security Audit Log (SM19/SM20)",      "Audit & Logging",  "SAP ECC"),
        ("sc-005", "SAP-LOG-002",  "Table Change Logging",                "Audit & Logging",  "SAP ECC"),
        ("sc-006", "SAP-NET-001",  "SAP Gateway Security (gw/acl_mode)",  "Network Security", "SAP ECC"),
        ("sc-007", "SAP-NET-002",  "ICM HTTPS Configuration",             "Network Security", "SAP ECC"),
        ("sc-008", "SAP-SYS-001",  "Default Password Profile Parameters", "System Security",  "SAP ECC"),
    ]
    for sc_id, ctrl_id, name, category, system in sec_controls:
        db.execute(text("""
            INSERT INTO sap_security_controls (id, tenant_id, control_id, name, category,
                system_name, status, risk_level, created_at, updated_at)
            VALUES (:id, :tid, :cid, :name, :cat, :sys, 'active', 'medium', :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": sc_id, "tid": TENANT_ID, "cid": ctrl_id, "name": name,
               "cat": category, "sys": system, "now": NOW})
    db.commit()
    print(f"  ✓ {len(sec_controls)} security controls")

    # ── 24. APPROVER CONFIGURATIONS ──────────────────────────────────────────
    print("\n[24/30] Creating approver configurations...")
    approvers = [
        ("apr-001", "u-mgr",     "line_manager",    "Finance",    ["access_request", "certification"]),
        ("apr-002", "u-ciso",    "security",        "IT Security", ["firefighter", "privileged_access"]),
        ("apr-003", "u-comp",    "compliance",      "Compliance",  ["risk_exception", "mitigation"]),
        ("apr-004", "u-admin",   "technical",       "IT Admin",    ["role_change", "mass_admin"]),
    ]
    for ap_id, user_id, ap_type, dept, approval_types in approvers:
        db.execute(text("""
            INSERT INTO approver_models (id, tenant_id, user_id, approver_type,
                department, approval_types, is_available, created_at, updated_at)
            VALUES (:id, :tid, :uid, :atype, :dept, :atypes, true, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": ap_id, "tid": TENANT_ID, "uid": user_id, "atype": ap_type,
               "dept": dept, "atypes": str(approval_types), "now": NOW})
    db.commit()
    print(f"  ✓ {len(approvers)} approver configurations")

    # ── 25. NOTIFICATION PREFERENCES ────────────────────────────────────────
    print("\n[25/30] Creating notification preferences...")
    for user_id in ["u-admin", "u-ciso", "u-comp", "u-risk", "u-audit"]:
        db.execute(text("""
            INSERT INTO notification_preferences (id, tenant_id, user_id,
                email_enabled, in_app_enabled, violation_alerts, approval_requests,
                certification_reminders, created_at, updated_at)
            VALUES (:id, :tid, :uid, true, true, true, true, true, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": uid(), "tid": TENANT_ID, "uid": user_id, "now": NOW})
    db.commit()
    print("  ✓ 5 notification preferences")

    # ── 26. RISK INCIDENTS ───────────────────────────────────────────────────
    print("\n[26/30] Creating risk incidents...")
    incidents = [
        ("ri-001", "er-001", "Unauthorized Payment Approved", "A payment of AUD 85,000 was approved without proper dual authorization", "high",   "investigating"),
        ("ri-002", "er-003", "Payroll Ghost Employee Detected", "System flagged a payroll record for an employee who left 3 months ago", "critical","contained"),
        ("ri-003", "er-004", "SAP System Outage - 4 Hours", "SAP ECC unavailable during month-end close due to basis configuration error", "high", "resolved"),
    ]
    for inc_id, risk_id, title, desc, severity, status in incidents:
        db.execute(text("""
            INSERT INTO risk_incidents (id, tenant_id, risk_id, title, description,
                severity, status, occurred_at, reported_by, created_at, updated_at)
            VALUES (:id, :tid, :rid, :title, :desc, :sev, :status, :occ,
                'u-risk', :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": inc_id, "tid": TENANT_ID, "rid": risk_id, "title": title,
               "desc": desc, "sev": severity, "status": status,
               "occ": dt(random.randint(5, 30)), "now": dt(random.randint(0, 5))})
    db.commit()
    print(f"  ✓ {len(incidents)} risk incidents")

    # ── 27. POLICY DOCUMENTS ─────────────────────────────────────────────────
    print("\n[27/30] Creating policy documents...")
    policies = [
        ("pol-001", "Information Security Policy",       "security",   "approved"),
        ("pol-002", "Access Control Policy",             "access",     "approved"),
        ("pol-003", "Segregation of Duties Policy",      "access",     "approved"),
        ("pol-004", "Privileged Access Management Policy","access",    "approved"),
        ("pol-005", "Data Classification Policy",        "data",       "in_review"),
        ("pol-006", "Incident Response Policy",          "security",   "approved"),
        ("pol-007", "Vendor Risk Management Policy",     "risk",       "approved"),
        ("pol-008", "Business Continuity Policy",        "operations", "approved"),
    ]
    for pol_id, name, pol_type, status in policies:
        db.execute(text("""
            INSERT INTO policy_documents (id, tenant_id, name, policy_type, status,
                version, owner_id, effective_date, review_date, created_at, updated_at)
            VALUES (:id, :tid, :name, :ptype, :status, '2.0', 'u-comp',
                :eff, :rev, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": pol_id, "tid": TENANT_ID, "name": name, "ptype": pol_type,
               "status": status, "eff": dt(180), "rev": dt(0) + datetime.timedelta(days=185),
               "now": dt(180)})
    db.commit()
    print(f"  ✓ {len(policies)} policy documents")

    # ── 28. AUDIT LOG ENTRIES ────────────────────────────────────────────────
    print("\n[28/30] Creating audit log entries...")
    audit_actions = [
        ("u-admin",  "USER_CREATE",         "users",           "u-user1",  "Created user john.smith"),
        ("u-admin",  "ROLE_ASSIGN",         "user_roles",      "r-fi-01",  "Assigned Z_FI_AP_FULL to john.smith"),
        ("u-ciso",   "VIOLATION_REVIEW",    "risk_violations", "v-001",    "Reviewed critical SoD violation"),
        ("u-comp",   "CERT_LAUNCH",         "certification",   "cc-002",   "Launched SOX certification campaign"),
        ("u-mgr",    "ACCESS_APPROVE",      "access_requests", "ar-001",   "Approved GL posting access request"),
        ("u-audit",  "FINDING_CREATE",      "audit_findings",  "af-001",   "Logged critical AP SoD finding"),
        ("u-user1",  "LOGIN",               "sessions",        "u-user1",  "User login from 192.168.1.45"),
        ("u-ff",     "FF_SESSION_START",    "ff_sessions",     "ffs-001",  "Started firefighter session FF_ACME_FI"),
        ("u-admin",  "POLICY_PUBLISH",      "policy_documents","pol-001",  "Published Information Security Policy v2.0"),
        ("u-risk",   "RISK_UPDATE",         "enterprise_risks","er-001",   "Updated risk residual score after control implementation"),
    ]
    for user_id, action, resource, resource_id, description in audit_actions:
        db.execute(text("""
            INSERT INTO audit_logs (id, tenant_id, user_id, action, resource_type,
                resource_id, description, ip_address, created_at)
            VALUES (:id, :tid, :uid, :action, :res, :rid, :desc, '10.0.0.1', :now)
            ON CONFLICT DO NOTHING
        """), {"id": uid(), "tid": TENANT_ID, "uid": user_id, "action": action,
               "res": resource, "rid": resource_id, "desc": description,
               "now": dt(random.randint(0, 30))})
    db.commit()
    print(f"  ✓ {len(audit_actions)} audit log entries")

    # ── 29. SYNC CONFIGURATION ───────────────────────────────────────────────
    print("\n[29/30] Creating system connectors...")
    sync_configs = [
        ("sc-syn-001", "SAP ECC 6.0 Production",  "sap_ecc",      "10.0.1.100", "active"),
        ("sc-syn-002", "SAP S/4HANA Dev",         "sap_s4hana",   "10.0.1.101", "active"),
        ("sc-syn-003", "Azure Active Directory",  "azure_ad",     "graph.microsoft.com", "active"),
        ("sc-syn-004", "ServiceNow ITSM",         "servicenow",   "acme.service-now.com", "inactive"),
    ]
    for sc_id, name, connector_type, host, status in sync_configs:
        db.execute(text("""
            INSERT INTO sync_configs (id, tenant_id, name, connector_type, host, status,
                sync_frequency, last_sync_at, created_at, updated_at)
            VALUES (:id, :tid, :name, :ctype, :host, :status, 'daily', :last, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": sc_id, "tid": TENANT_ID, "name": name, "ctype": connector_type,
               "host": host, "status": status, "last": dt(1), "now": NOW})
    db.commit()
    print(f"  ✓ {len(sync_configs)} system connectors")

    # ── 30. RISK APPETITE ────────────────────────────────────────────────────
    print("\n[30/30] Creating risk appetite statements...")
    appetites = [
        ("ra-001", "Access Control",   3, 15, "Acme has LOW appetite for unauthorized access. Maximum tolerated risk score: 15/25."),
        ("ra-002", "Financial Fraud",  1, 10, "Acme has ZERO appetite for financial fraud. Any incident triggers immediate board escalation."),
        ("ra-003", "Operational Risk", 5, 20, "Acme has MEDIUM appetite for operational disruptions. Tolerated RTO: 4 hours."),
        ("ra-004", "Compliance",       2, 12, "Acme has LOW appetite for regulatory non-compliance. All critical controls must be effective."),
        ("ra-005", "Technology Risk",  4, 18, "Acme has MODERATE appetite for technology risk. DR plan tested annually."),
    ]
    for ra_id, category, score, threshold, statement in appetites:
        db.execute(text("""
            INSERT INTO risk_appetites (id, tenant_id, category, appetite_score,
                threshold, statement, approved_by, created_at, updated_at)
            VALUES (:id, :tid, :cat, :score, :thresh, :stmt, 'u-risk', :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": ra_id, "tid": TENANT_ID, "cat": category, "score": score,
               "thresh": threshold, "stmt": statement, "now": dt(90)})
    db.commit()
    print(f"  ✓ {len(appetites)} risk appetite statements")

    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("SEED COMPLETE — Validating row counts...")
    print("=" * 60)

    table_checks = [
        ("tenants",               "tenant_id = 'acme-corp-demo'"),
        ("users",                 f"tenant_id = '{TENANT_ID}'"),
        ("roles",                 f"tenant_id = '{TENANT_ID}'"),
        ("user_roles",            f"tenant_id = '{TENANT_ID}'"),
        ("risk_violations",       f"tenant_id = '{TENANT_ID}'"),
        ("access_requests",       f"tenant_id = '{TENANT_ID}'"),
        ("mitigation_controls",   f"tenant_id = '{TENANT_ID}'"),
        ("firefighter_requests",  f"tenant_id = '{TENANT_ID}'"),
        ("firefighter_sessions",  f"tenant_id = '{TENANT_ID}'"),
        ("certification_campaigns",f"tenant_id = '{TENANT_ID}'"),
        ("enterprise_risks",      f"tenant_id = '{TENANT_ID}'"),
        ("key_risk_indicators",   f"tenant_id = '{TENANT_ID}'"),
        ("process_controls",      f"tenant_id = '{TENANT_ID}'"),
        ("control_tests",         f"tenant_id = '{TENANT_ID}'"),
        ("control_deficiencies",  f"tenant_id = '{TENANT_ID}'"),
        ("audit_plans",           f"tenant_id = '{TENANT_ID}'"),
        ("audit_engagements",     f"tenant_id = '{TENANT_ID}'"),
        ("audit_findings",        f"tenant_id = '{TENANT_ID}'"),
        ("jml_policies",          f"tenant_id = '{TENANT_ID}'"),
        ("jml_events",            f"tenant_id = '{TENANT_ID}'"),
        ("vendors",               f"tenant_id = '{TENANT_ID}'"),
        ("fraud_rules",           f"tenant_id = '{TENANT_ID}'"),
        ("fraud_alerts",          f"tenant_id = '{TENANT_ID}'"),
        ("bcm_plans",             f"tenant_id = '{TENANT_ID}'"),
        ("whistleblower_cases",   f"tenant_id = '{TENANT_ID}'"),
        ("standalone_surveys",    f"tenant_id = '{TENANT_ID}'"),
        ("org_units",             f"tenant_id = '{TENANT_ID}'"),
        ("sap_security_controls", f"tenant_id = '{TENANT_ID}'"),
        ("policy_documents",      f"tenant_id = '{TENANT_ID}'"),
        ("audit_logs",            f"tenant_id = '{TENANT_ID}'"),
        ("sync_configs",          f"tenant_id = '{TENANT_ID}'"),
        ("risk_appetites",        f"tenant_id = '{TENANT_ID}'"),
    ]

    total_rows = 0
    populated = 0
    for table, where in table_checks:
        try:
            row = db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {where}")).scalar()
            status_icon = "✓" if row > 0 else "✗"
            if row > 0:
                populated += 1
            total_rows += row
            print(f"  {status_icon} {table:<35} {row:>4} rows")
        except Exception as e:
            print(f"  ? {table:<35} ERROR: {e}")

    print("=" * 60)
    print(f"  Tables populated: {populated}/{len(table_checks)}")
    print(f"  Total rows created: {total_rows}")
    print(f"  Tenant: {TENANT_ID}")
    print(f"  Login: acme_admin / AcmeP@ss2026!")
    print("=" * 60)
