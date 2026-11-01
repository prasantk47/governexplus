"""
GovernexPlus Extensive Data Seeder
Seeds realistic enterprise GRC data across all modules via API
"""
import urllib.request, json, urllib.error, sys, time, random
from datetime import datetime, timedelta

BASE = "https://governexplus.com/api"
TENANT = "acme-corp-demo"
TOKEN = None
H = {"Content-Type": "application/json"}
COUNTS = {}

def login():
    global TOKEN
    d, e = call("POST", "/auth/login", {"username": "acme_admin", "password": "AcmeP@ss2026!", "tenant_id": TENANT})
    if d:
        TOKEN = d["access_token"]
        H["Authorization"] = f"Bearer {TOKEN}"
        print(f"Logged in as acme_admin @ {TENANT}")
    else:
        print(f"LOGIN FAILED: {e}"); sys.exit(1)

def call(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=H, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=20)
        return json.loads(resp.read()), None
    except urllib.error.HTTPError as e:
        return None, f"{e.code}: {e.read().decode()[:120]}"

def post(path, body):  return call("POST", path, body)
def get(path):         return call("GET", path)
def put(path, body):   return call("PUT", path, body)

def section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

def ok(name, result, err):
    if result:
        COUNTS[name] = COUNTS.get(name, 0) + 1
        return True
    else:
        print(f"  WARN [{name}]: {err}")
        return False

def dt(days_offset=0, fmt="%Y-%m-%dT%H:%M:%S"):
    return (datetime.utcnow() + timedelta(days=days_offset)).strftime(fmt)

def dts(days_offset=0):
    return (datetime.utcnow() + timedelta(days=days_offset)).strftime("%Y-%m-%d")

# ─────────────────────────────────────────────────────────────
# 1. ENTERPRISE RISKS (30 risks)
# ─────────────────────────────────────────────────────────────
RISKS = [
    # Strategic
    {"title":"Digital Transformation Programme Delay","category":"strategic","status":"open","inherent_likelihood":3,"inherent_impact":5,"velocity":"rapid","risk_owner_name":"CEO Office","contingency_plan":"Activate vendor escalation protocol; bring in additional SI resources."},
    {"title":"Loss of Key Talent in Technology Division","category":"strategic","status":"open","inherent_likelihood":4,"inherent_impact":4,"velocity":"gradual","risk_owner_name":"CHRO","contingency_plan":"Invoke succession plan; accelerate cross-training programme."},
    {"title":"Merger Integration Risk - DataVault Acquisition","category":"strategic","status":"assessed","inherent_likelihood":3,"inherent_impact":5,"velocity":"moderate","risk_owner_name":"CFO","contingency_plan":"Stage integration; maintain parallel operations for 6 months."},
    {"title":"Regulatory Change - Basel IV Capital Requirements","category":"strategic","status":"open","inherent_likelihood":4,"inherent_impact":4,"velocity":"gradual","risk_owner_name":"CRO","contingency_plan":"Engage external regulatory counsel; build capital buffer."},
    {"title":"Board Succession Planning Gap","category":"strategic","status":"identified","inherent_likelihood":2,"inherent_impact":4,"velocity":"gradual","risk_owner_name":"Company Secretary","contingency_plan":"Initiate board skills matrix review."},
    # Operational
    {"title":"Segregation of Duties Breakdown in Procure-to-Pay","category":"operational","status":"open","inherent_likelihood":4,"inherent_impact":4,"velocity":"sudden","risk_owner_name":"VP Finance","contingency_plan":"Implement compensating controls; manual dual-approval until SoD fixed."},
    {"title":"Insider Threat via Privileged SAP Access","category":"operational","status":"open","inherent_likelihood":3,"inherent_impact":5,"velocity":"sudden","risk_owner_name":"CISO","contingency_plan":"Revoke elevated access; enable Firefighter log monitoring."},
    {"title":"Critical Supplier Single-Source Dependency","category":"operational","status":"open","inherent_likelihood":3,"inherent_impact":5,"velocity":"rapid","risk_owner_name":"COO","contingency_plan":"Qualify backup suppliers; increase safety stock by 30%."},
    {"title":"Manual Process Errors in Month-End Close","category":"operational","status":"open","inherent_likelihood":4,"inherent_impact":3,"velocity":"moderate","risk_owner_name":"CFO","contingency_plan":"Automate reconciliation steps; introduce 4-eye check."},
    {"title":"Warehouse Management System Outage","category":"operational","status":"open","inherent_likelihood":2,"inherent_impact":4,"velocity":"sudden","risk_owner_name":"VP Operations","contingency_plan":"Activate manual picking process; contact DR site."},
    {"title":"Ghost Employee in Payroll System","category":"operational","status":"open","inherent_likelihood":2,"inherent_impact":4,"velocity":"gradual","risk_owner_name":"CHRO","contingency_plan":"Conduct headcount reconciliation; HR/Finance joint audit."},
    {"title":"Third-Party API Dependency - Payment Gateway","category":"operational","status":"assessed","inherent_likelihood":3,"inherent_impact":4,"velocity":"sudden","risk_owner_name":"CTO","contingency_plan":"Integrate secondary payment provider; test monthly."},
    # Financial
    {"title":"Foreign Exchange Exposure - USD/AUD Volatility","category":"financial","status":"open","inherent_likelihood":4,"inherent_impact":4,"velocity":"rapid","risk_owner_name":"CFO","contingency_plan":"Implement FX hedging strategy; review quarterly."},
    {"title":"Liquidity Risk - Working Capital Squeeze","category":"financial","status":"open","inherent_likelihood":3,"inherent_impact":5,"velocity":"rapid","risk_owner_name":"CFO","contingency_plan":"Draw down revolving credit facility; accelerate receivables."},
    {"title":"Revenue Concentration Risk - Top 3 Clients","category":"financial","status":"open","inherent_likelihood":3,"inherent_impact":4,"velocity":"gradual","risk_owner_name":"CEO","contingency_plan":"Diversification programme; minimum 2 new Tier-1 clients p.a."},
    {"title":"Insurance Coverage Gap - Cyber Liability","category":"financial","status":"identified","inherent_likelihood":3,"inherent_impact":4,"velocity":"moderate","risk_owner_name":"CFO","contingency_plan":"Engage broker; benchmark against industry coverage levels."},
    {"title":"Tax Compliance Risk - Transfer Pricing","category":"financial","status":"assessed","inherent_likelihood":2,"inherent_impact":4,"velocity":"gradual","risk_owner_name":"Head of Tax","contingency_plan":"Engage Big-4 transfer pricing specialists; update TP documentation."},
    # Compliance
    {"title":"GDPR Data Residency Violation - Cloud Migration","category":"compliance","status":"open","inherent_likelihood":3,"inherent_impact":5,"velocity":"sudden","risk_owner_name":"DPO","contingency_plan":"Halt non-compliant data migration; engage DPA notification process."},
    {"title":"AI Model Bias in Credit Scoring","category":"compliance","status":"open","inherent_likelihood":3,"inherent_impact":5,"velocity":"rapid","risk_owner_name":"CRO","contingency_plan":"Suspend AI model; revert to manual scoring for affected segments."},
    {"title":"Anti-Bribery & Corruption Exposure - APAC Expansion","category":"compliance","status":"open","inherent_likelihood":3,"inherent_impact":5,"velocity":"gradual","risk_owner_name":"General Counsel","contingency_plan":"Mandatory FCPA training; third-party due diligence enhancement."},
    {"title":"Modern Slavery Risk in Supply Chain","category":"compliance","status":"identified","inherent_likelihood":2,"inherent_impact":4,"velocity":"gradual","risk_owner_name":"Chief Sustainability Officer","contingency_plan":"Supply chain audit programme; supplier code of conduct enforcement."},
    {"title":"APRA CPS 234 Non-Compliance - Information Security","category":"compliance","status":"open","inherent_likelihood":3,"inherent_impact":5,"velocity":"moderate","risk_owner_name":"CISO","contingency_plan":"Engage external auditor; remediate gaps within 90 days."},
    # IT / Cyber
    {"title":"Ransomware Attack on Core Banking Platform","category":"it_cyber","status":"open","inherent_likelihood":4,"inherent_impact":5,"velocity":"sudden","risk_owner_name":"CISO","contingency_plan":"Activate IRP; isolate affected segments; restore from air-gapped backup."},
    {"title":"Unpatched SAP Vulnerabilities (CVE-2024-22125)","category":"it_cyber","status":"open","inherent_likelihood":4,"inherent_impact":4,"velocity":"rapid","risk_owner_name":"CISO","contingency_plan":"Emergency patching window within 72h; WAF rule deployment."},
    {"title":"Shadow IT - Unsanctioned Cloud Services","category":"it_cyber","status":"open","inherent_likelihood":5,"inherent_impact":3,"velocity":"gradual","risk_owner_name":"CTO","contingency_plan":"Deploy CASB solution; enforce Cloud Access Policy."},
    {"title":"Data Exfiltration via Compromised Vendor Account","category":"it_cyber","status":"assessed","inherent_likelihood":3,"inherent_impact":5,"velocity":"sudden","risk_owner_name":"CISO","contingency_plan":"Revoke vendor credentials; implement zero-trust vendor access."},
    {"title":"DDoS Attack on Customer Portal","category":"it_cyber","status":"open","inherent_likelihood":3,"inherent_impact":4,"velocity":"sudden","risk_owner_name":"CTO","contingency_plan":"Activate DDoS mitigation service; rate limiting; CDN failover."},
    # Reputational
    {"title":"Social Media Crisis - Customer Data Leak","category":"reputational","status":"open","inherent_likelihood":3,"inherent_impact":5,"velocity":"sudden","risk_owner_name":"CCO","contingency_plan":"Activate crisis comms plan; CEO statement within 2 hours."},
    {"title":"Executive Misconduct Allegation","category":"reputational","status":"identified","inherent_likelihood":2,"inherent_impact":5,"velocity":"sudden","risk_owner_name":"Board Chair","contingency_plan":"Independent investigation; interim leadership plan activated."},
    {"title":"ESG Rating Downgrade Risk","category":"reputational","status":"identified","inherent_likelihood":3,"inherent_impact":3,"velocity":"gradual","risk_owner_name":"CFO","contingency_plan":"Accelerate ESG reporting improvements; engage ratings agency."},
]

def seed_risks():
    section("RISKS — 30 enterprise risks")
    created_ids = []
    for r in RISKS:
        result, err = post("/risk-management/risks", r)
        if ok("risks", result, err):
            rid = result.get("id") or result.get("risk_id")
            created_ids.append(rid)
            print(f"  + [{r['category'].upper()[:3]}] {r['title'][:55]}  score={result.get('inherent_score','?')}")
        time.sleep(0.05)
    print(f"\n  Total risks created: {COUNTS.get('risks',0)}")
    return created_ids

# ─────────────────────────────────────────────────────────────
# 2. KRI MEASUREMENTS (add readings to existing KRIs)
# ─────────────────────────────────────────────────────────────
def seed_kri_measurements():
    section("KRIs — Add historical measurements")
    kri_dash, _ = get("/risk-management/kris/dashboard")
    if not kri_dash:
        print("  No KRIs found"); return
    kris = kri_dash.get("kris", [])
    print(f"  Found {len(kris)} KRIs — adding 6 months of readings each")
    for kri in kris:
        kri_id = kri.get("kri_id") or kri.get("id")
        base_val = kri.get("current_value") or kri.get("threshold_red", 20)
        if not kri_id: continue
        for month in range(6, 0, -1):
            val = round(float(base_val) * (0.7 + 0.1 * (6-month)) + random.uniform(-2, 2), 1)
            r, e = post(f"/risk-management/kris/{kri_id}/measurements", {
                "value": val,
                "measured_at": dt(-30 * month),
                "notes": f"Monthly reading - {datetime.utcnow().replace(day=1) - timedelta(days=30*month-1):%B %Y}",
                "source": "automated"
            })
            ok("kri_measurements", r, e)
        print(f"  + {kri.get('kri_name','?')[:45]} — 6 readings added")
    print(f"\n  Total KRI measurements: {COUNTS.get('kri_measurements',0)}")

# ─────────────────────────────────────────────────────────────
# 3. RISK WORKFLOWS (multiple pending approvals)
# ─────────────────────────────────────────────────────────────
WORKFLOWS = [
    {"workflow_type":"risk_proposal","object_type":"risk","title":"Risk Proposal: Ransomware Attack on Core Banking"},
    {"workflow_type":"risk_approval","object_type":"risk","title":"Risk Acceptance: FX Exposure USD/AUD"},
    {"workflow_type":"risk_proposal","object_type":"risk","title":"Risk Proposal: GDPR Data Residency Violation"},
    {"workflow_type":"assessment_approval","object_type":"risk","title":"Assessment Approval: Q4 Operational Risk Review"},
    {"workflow_type":"risk_proposal","object_type":"risk","title":"Risk Proposal: Critical Supplier Dependency"},
    {"workflow_type":"response_approval","object_type":"risk","title":"Response Plan Approval: Unpatched SAP CVE-2024-22125"},
    {"workflow_type":"risk_approval","object_type":"risk","title":"Risk Acceptance: Board Succession Planning Gap"},
    {"workflow_type":"assessment_approval","object_type":"risk","title":"Assessment Approval: Insider Threat Review"},
]

def seed_workflows():
    section("RISK WORKFLOWS — 8 approval workflows")
    ids = []
    for i, w in enumerate(WORKFLOWS):
        w["object_id"] = str(100 + i)
        w["description"] = f"Submitted for review by Risk Team on {dts()}"
        r, e = post("/risk-management/workflows", w)
        if ok("workflows", r, e):
            wf_id = r.get("workflow_id")
            ids.append(wf_id)
            print(f"  + [{w['workflow_type']}] {w['title'][:50]}")
        time.sleep(0.05)
    # Partially approve some
    if ids and len(ids) >= 3:
        # Approve step 1 on first 3
        for wf_id in ids[:3]:
            post(f"/risk-management/workflows/{wf_id}/steps/1/decide", {
                "decision": "approve",
                "comments": "Step 1 reviewed and approved. Escalating."
            })
        print(f"  (3 workflows advanced to step 2)")
    print(f"\n  Total workflows: {COUNTS.get('workflows',0)}")
    return ids

# ─────────────────────────────────────────────────────────────
# 4. AUDIT PLANS & ENGAGEMENTS
# ─────────────────────────────────────────────────────────────
AUDIT_PLANS = [
    {"name":"FY2027 Internal Audit Plan","plan_type":"annual","fiscal_year":2027,"status":"draft","description":"Annual internal audit plan covering all risk domains.","planned_hours":2400,"budget_amount":850000},
    {"name":"Q1 FY2027 Operational Audit","plan_type":"special","fiscal_year":2027,"status":"approved","description":"Q1 focus: P2P controls, inventory, payroll.","planned_hours":480,"budget_amount":180000},
    {"name":"Cyber Security Audit Programme 2027","plan_type":"multi_year","fiscal_year":2027,"status":"draft","description":"Thematic review of all cyber security controls.","planned_hours":600,"budget_amount":220000},
]

ENGAGEMENTS = [
    {"title":"Procure-to-Pay Controls Review","engagement_type":"financial","status":"planning","lead_auditor_name":"Alan Auditor","planned_start":dts(-30),"planned_end":dts(15),"scope":"Full P2P cycle including vendor master, PO, GR, AP"},
    {"title":"SAP Access & Privilege Management Audit","engagement_type":"it","status":"fieldwork","lead_auditor_name":"Alan Auditor","planned_start":dts(-45),"planned_end":dts(0),"scope":"SAP access controls, SoD, Firefighter usage"},
    {"title":"Payroll Process Integrity Review","engagement_type":"operational","status":"fieldwork","lead_auditor_name":"Sarah Chen","planned_start":dts(-20),"planned_end":dts(10),"scope":"HR master data, payroll run, bank account changes"},
    {"title":"Treasury & FX Risk Controls","engagement_type":"financial","status":"planning","lead_auditor_name":"James Wilson","planned_start":dts(5),"planned_end":dts(45),"scope":"FX hedging policy, limits, dealer confirmations"},
    {"title":"Cloud Migration Security Assurance","engagement_type":"it","status":"planning","lead_auditor_name":"Emma Thompson","planned_start":dts(10),"planned_end":dts(50),"scope":"AWS/Azure security config, IAM, data classification"},
    {"title":"Vendor Management Programme Review","engagement_type":"operational","status":"planning","lead_auditor_name":"Alan Auditor","planned_start":dts(20),"planned_end":dts(60),"scope":"TPRM programme, contract compliance, vendor onboarding"},
    {"title":"GDPR Data Protection Compliance Audit","engagement_type":"compliance","status":"fieldwork","lead_auditor_name":"Mark Davies","planned_start":dts(-15),"planned_end":dts(20),"scope":"Data inventory, consent management, DSAR processes"},
    {"title":"Business Continuity Planning Effectiveness","engagement_type":"operational","status":"planning","lead_auditor_name":"Sarah Chen","planned_start":dts(30),"planned_end":dts(70),"scope":"BCP documentation, testing, DR procedures"},
]

FINDINGS = [
    {"title":"Critical SoD Conflict: Vendor Create + Payment Approve","severity":"critical","status":"open","finding_type":"control_deficiency","description":"User A.Smith has both MM_VENDOR_CREATE and FI_PAYMENT_APPROVE roles active. High fraud risk.","recommendation":"Revoke FI_PAYMENT_APPROVE from A.Smith immediately; implement role segregation policy.","management_response":"Agreed. IT to action within 5 business days.","due_date":dts(10)},
    {"title":"User Access Review Overdue by 60+ Days","severity":"high","status":"open","finding_type":"process_gap","description":"Quarterly access review for Finance division not completed. 47 user accounts unreviewed.","recommendation":"Complete access review within 14 days; implement automated reminder workflow.","management_response":"HR & IT to co-own; access review committee to be formed.","due_date":dts(14)},
    {"title":"Vendor Master Changes Without Dual Authorisation","severity":"high","status":"open","finding_type":"control_deficiency","description":"14 vendor bank account changes made in last quarter without second approver sign-off.","recommendation":"Enforce 4-eyes principle in SAP for all vendor bank changes; configure approval workflow.","management_response":"CFO has mandated immediate change to approval matrix.","due_date":dts(7)},
    {"title":"Firefighter Log Review Not Performed","severity":"high","status":"open","finding_type":"monitoring_gap","description":"SAP Firefighter (emergency access) logs for October not reviewed by control owner.","recommendation":"Monthly FF log review to be assigned to IT Security team with evidence retention.","management_response":"Process owner identified; review to occur within 48 hours.","due_date":dts(3)},
    {"title":"Password Policy Non-Compliance - Service Accounts","severity":"medium","status":"open","finding_type":"policy_breach","description":"23 SAP service accounts have passwords that have not been rotated in 365+ days.","recommendation":"Enforce automated password rotation for all service accounts; use privileged vault.","management_response":"CyberArk implementation scheduled Q1 2027.","due_date":dts(45)},
    {"title":"Missing Reconciliation Controls for Intercompany Transactions","severity":"medium","status":"in_progress","finding_type":"control_gap","description":"Intercompany eliminations not subject to automated matching; manual process error-prone.","recommendation":"Implement automated intercompany reconciliation in SAP Group Reporting.","management_response":"SAP project team engaged; go-live Q2 2027.","due_date":dts(90)},
    {"title":"Third Party Data Access Not Logged","severity":"high","status":"open","finding_type":"monitoring_gap","description":"CloudSecure Pty Ltd (Tier 1 vendor) accesses production systems without activity logging.","recommendation":"Implement PAM solution for all Tier 1 vendor access; log all sessions.","management_response":"CISO to action PAM RFP within 30 days.","due_date":dts(30)},
    {"title":"Disaster Recovery Test Overdue","severity":"medium","status":"open","finding_type":"process_gap","description":"Last DR test was 18 months ago. APRA CPS 232 requires annual testing.","recommendation":"Schedule DR test within 60 days; document results and evidence.","management_response":"CTO has committed to Q1 2027 DR test.","due_date":dts(60)},
    {"title":"Segregation: GL Posting + Period Close","severity":"medium","status":"open","finding_type":"control_deficiency","description":"Controller role permits both journal entry posting and period close execution.","recommendation":"Split GL_PERIOD_CLOSE to separate role; assign to Finance Director only.","management_response":"SAP role redesign in next maintenance window.","due_date":dts(21)},
    {"title":"Incomplete KYC for 3 High-Value Clients","severity":"high","status":"open","finding_type":"compliance_gap","description":"3 clients with >$10M AUM have outdated KYC documentation (2+ years old).","recommendation":"Immediate KYC refresh within 30 days; risk-based KYC review schedule.","management_response":"Compliance team to contact clients this week.","due_date":dts(30)},
]

def seed_audit():
    section("AUDIT — Plans, Engagements, Findings")
    for p in AUDIT_PLANS:
        r, e = post("/audit-management/plans", p)
        if ok("audit_plans", r, e):
            print(f"  + Plan: {p['name'][:55]}")
        time.sleep(0.05)

    for eng in ENGAGEMENTS:
        r, e = post("/audit-management/engagements", eng)
        if ok("engagements", r, e):
            print(f"  + Engagement: {eng['title'][:55]}")
        time.sleep(0.05)

    # Get engagement IDs for findings — use engagement_id (string), not id (integer)
    engs_data, _ = get("/audit-management/engagements")
    engs = engs_data if isinstance(engs_data, list) else engs_data.get("engagements", []) if engs_data else []
    eng_ids = [e.get("engagement_id") or e.get("id") for e in engs if e.get("engagement_id") or e.get("id")]

    for i, f in enumerate(FINDINGS):
        eng_id = eng_ids[i % len(eng_ids)] if eng_ids else None
        if not eng_id:
            print(f"  SKIP finding (no engagements): {f['title'][:50]}")
            continue
        r, e = post(f"/audit-management/engagements/{eng_id}/findings", f)
        if ok("findings", r, e):
            print(f"  + Finding [{f['severity'].upper()}]: {f['title'][:50]}")
        time.sleep(0.05)

    print(f"\n  Audit plans: {COUNTS.get('audit_plans',0)}  |  Engagements: {COUNTS.get('engagements',0)}  |  Findings: {COUNTS.get('findings',0)}")

# ─────────────────────────────────────────────────────────────
# 5. TPRM — Vendors, Assessments, Issues, Contracts
# ─────────────────────────────────────────────────────────────
VENDORS = [
    {"vendor_name":"Apex Consulting Group","vendor_type":"professional_services","tier":"tier2","status":"active","country":"Australia","industry":"Consulting","annual_spend":1200000,"contract_start":dts(-365),"contract_end":dts(365),"primary_contact_name":"John Apex","primary_contact_email":"john@apex.com","risk_rating":"medium","criticality":"high","data_access":True,"pii_access":True},
    {"vendor_name":"CloudSecure Pty Ltd","vendor_type":"technology","tier":"tier1","status":"active","country":"Australia","industry":"Cybersecurity","annual_spend":4500000,"contract_start":dts(-180),"contract_end":dts(540),"primary_contact_name":"Lisa Cloud","primary_contact_email":"lisa@cloudsecure.com","risk_rating":"high","criticality":"critical","data_access":True,"pii_access":True},
    {"vendor_name":"DataVault Solutions","vendor_type":"technology","tier":"tier1","status":"active","country":"USA","industry":"Data Management","annual_spend":3200000,"contract_start":dts(-90),"contract_end":dts(635),"primary_contact_name":"Mark Vault","primary_contact_email":"mark@datavault.com","risk_rating":"high","criticality":"critical","data_access":True,"pii_access":False},
    {"vendor_name":"Global Logistics Ltd","vendor_type":"logistics","tier":"tier3","status":"pending_review","country":"Singapore","industry":"Logistics","annual_spend":800000,"contract_start":dts(-540),"contract_end":dts(180),"primary_contact_name":"Wei Chang","primary_contact_email":"wei@globallogistics.com","risk_rating":"medium","criticality":"medium","data_access":False,"pii_access":False},
    {"vendor_name":"SecureNet Analytics","vendor_type":"technology","tier":"tier2","status":"active","country":"UK","industry":"Analytics","annual_spend":950000,"contract_start":dts(-270),"contract_end":dts(365),"primary_contact_name":"Sarah Net","primary_contact_email":"sarah@securenet.com","risk_rating":"medium","criticality":"high","data_access":True,"pii_access":False},
    {"vendor_name":"AuditPro Services","vendor_type":"professional_services","tier":"tier3","status":"active","country":"Australia","industry":"Audit","annual_spend":420000,"contract_start":dts(-365),"contract_end":dts(0),"primary_contact_name":"Tom Audit","primary_contact_email":"tom@auditpro.com","risk_rating":"low","criticality":"low","data_access":False,"pii_access":False},
    {"vendor_name":"PaySecure Gateway","vendor_type":"fintech","tier":"tier1","status":"active","country":"Australia","industry":"Payments","annual_spend":2800000,"contract_start":dts(-730),"contract_end":dts(365),"primary_contact_name":"Anna Pay","primary_contact_email":"anna@paysecure.com","risk_rating":"critical","criticality":"critical","data_access":True,"pii_access":True},
    {"vendor_name":"HRConnect Outsourcing","vendor_type":"hr_services","tier":"tier2","status":"active","country":"India","industry":"HR Services","annual_spend":1600000,"contract_start":dts(-180),"contract_end":dts(545),"primary_contact_name":"Raj HR","primary_contact_email":"raj@hrconnect.com","risk_rating":"high","criticality":"high","data_access":True,"pii_access":True},
    {"vendor_name":"BuildRight Facilities","vendor_type":"facilities","tier":"tier4","status":"active","country":"Australia","industry":"Facilities","annual_spend":280000,"contract_start":dts(-365),"contract_end":dts(365),"primary_contact_name":"Bob Build","primary_contact_email":"bob@buildright.com","risk_rating":"low","criticality":"low","data_access":False,"pii_access":False},
    {"vendor_name":"TechRecruit Staffing","vendor_type":"staffing","tier":"tier3","status":"active","country":"Australia","industry":"Staffing","annual_spend":750000,"contract_start":dts(-90),"contract_end":dts(275),"primary_contact_name":"Carol Tech","primary_contact_email":"carol@techrecruit.com","risk_rating":"medium","criticality":"medium","data_access":False,"pii_access":False},
    {"vendor_name":"LegalEdge Counsel","vendor_type":"professional_services","tier":"tier2","status":"active","country":"Australia","industry":"Legal","annual_spend":560000,"contract_start":dts(-540),"contract_end":dts(180),"primary_contact_name":"Peter Law","primary_contact_email":"peter@legaledge.com","risk_rating":"medium","criticality":"medium","data_access":True,"pii_access":False},
    {"vendor_name":"CloudHost Infrastructure","vendor_type":"technology","tier":"tier1","status":"active","country":"USA","industry":"Cloud Infrastructure","annual_spend":5200000,"contract_start":dts(-365),"contract_end":dts(730),"primary_contact_name":"Amy Cloud","primary_contact_email":"amy@cloudhost.com","risk_rating":"critical","criticality":"critical","data_access":True,"pii_access":True},
]

VENDOR_ISSUES = [
    {"title":"SOC 2 Report Expired - CloudSecure","severity":"high","status":"open","description":"CloudSecure SOC 2 Type II report expired 45 days ago. No updated report received.","due_date":dts(14)},
    {"title":"Data Processing Agreement Missing - HRConnect","severity":"critical","status":"open","description":"HRConnect processes employee PII but no DPA in place. GDPR non-compliance.","due_date":dts(7)},
    {"title":"Penetration Test Results Outstanding - DataVault","severity":"medium","status":"open","description":"Annual pen test due. DataVault has not provided results for current year.","due_date":dts(21)},
    {"title":"Business Continuity Plan Not Shared - PaySecure","severity":"high","status":"open","description":"PaySecure BCP not received despite contract requirement. Gateway is critical dependency.","due_date":dts(10)},
    {"title":"Sub-contractor Disclosure - Apex Consulting","severity":"medium","status":"open","description":"Apex engaged 3 sub-contractors without prior notification per contract clause 4.2.","due_date":dts(14)},
    {"title":"Security Incident Not Reported Timely - CloudHost","severity":"high","status":"open","description":"CloudHost had a security incident on 15 Oct but only notified Acme on 28 Oct (13 days).","due_date":dts(5)},
    {"title":"ISMS Certification Lapsed - SecureNet","severity":"medium","status":"in_progress","description":"ISO 27001 certification expired. Recertification audit scheduled for Dec 2026.","due_date":dts(60)},
]

def seed_tprm():
    section("TPRM — 12 vendors, 7 issues")
    vendor_ids = []
    for v in VENDORS:
        r, e = post("/tprm/vendors", v)
        if ok("tprm_vendors", r, e):
            vid = r.get("id") or r.get("vendor_id")
            vendor_ids.append(vid)
            print(f"  + {v['vendor_name']:<32} Tier:{v['tier']}  Risk:{v['risk_rating']}")
        time.sleep(0.05)

    # Get vendor IDs from DB
    vdata, _ = get("/tprm/vendors")
    vlist = vdata if isinstance(vdata, list) else vdata.get("vendors", []) if vdata else []
    vids = [v.get("id") or v.get("vendor_id") for v in vlist if v.get("id") or v.get("vendor_id")]

    for i, issue in enumerate(VENDOR_ISSUES):
        if vids:
            issue["vendor_id"] = vids[i % len(vids)]
        r, e = post("/tprm/issues", issue)
        if ok("tprm_issues", r, e):
            print(f"  + Issue [{issue['severity'].upper()}]: {issue['title'][:50]}")
        time.sleep(0.05)

    print(f"\n  Vendors: {COUNTS.get('tprm_vendors',0)}  |  Issues: {COUNTS.get('tprm_issues',0)}")

# ─────────────────────────────────────────────────────────────
# 6. JML EVENTS
# ─────────────────────────────────────────────────────────────
JML_EVENTS = [
    {"employee_id":"EMP-2026-001","employee_name":"Alice Johnson","event_type":"joiner","effective_date":dts(-30),"new_position":"Senior Financial Analyst","new_org_unit":"Finance","source_system":"Workday","metadata":{"manager":"CFO","notes":"Access provisioned for SAP FI, Concur, PowerBI"}},
    {"employee_id":"EMP-2026-002","employee_name":"Marcus Williams","event_type":"joiner","effective_date":dts(-14),"new_position":"SAP Basis Administrator","new_org_unit":"IT","source_system":"Workday","metadata":{"manager":"CTO","notes":"Admin access provisioned; security training completed"}},
    {"employee_id":"EMP-2026-003","employee_name":"Priya Sharma","event_type":"joiner","effective_date":dts(-7),"new_position":"Risk Analyst","new_org_unit":"Risk & Compliance","source_system":"Workday","metadata":{"manager":"CRO","notes":"SAP read-only access pending"}},
    {"employee_id":"EMP-2026-004","employee_name":"David Chen","event_type":"joiner","effective_date":dts(7),"new_position":"IT Auditor","new_org_unit":"Internal Audit","source_system":"Workday","metadata":{"manager":"CAE","notes":"Start date upcoming; access requests queued"}},
    {"employee_id":"EMP-2026-005","employee_name":"Sophie Turner","event_type":"joiner","effective_date":dts(14),"new_position":"Treasury Analyst","new_org_unit":"Treasury","source_system":"Workday","metadata":{"manager":"CFO","notes":"FX system access to be provisioned on start date"}},
    {"employee_id":"EMP-2025-089","employee_name":"Robert Davis","event_type":"leaver","effective_date":dts(-5),"previous_job_function":"AP Clerk","previous_org_unit":"Finance","source_system":"Workday","metadata":{"manager":"VP Finance","notes":"All access revoked on last working day"}},
    {"employee_id":"EMP-2025-043","employee_name":"Karen Wilson","event_type":"leaver","effective_date":dts(-10),"previous_job_function":"System Administrator","previous_org_unit":"IT","source_system":"Workday","metadata":{"manager":"CTO","notes":"Privileged access revoked; credentials rotated"}},
    {"employee_id":"EMP-2025-112","employee_name":"Tom Bradley","event_type":"leaver","effective_date":dts(-15),"previous_job_function":"Account Manager","previous_org_unit":"Sales","source_system":"Workday","metadata":{"manager":"CSO","notes":"CRM and email access revoked"}},
    {"employee_id":"EMP-2024-055","employee_name":"James Wilson","event_type":"mover","effective_date":dts(-20),"previous_job_function":"IT Support Analyst","previous_org_unit":"IT Operations","new_position":"Security Analyst","new_org_unit":"IT Security","source_system":"Workday","metadata":{"manager":"CISO","notes":"Removed ITSUPPORT role; added SECANALYST role"}},
    {"employee_id":"EMP-2024-067","employee_name":"Emma Thompson","event_type":"mover","effective_date":dts(-35),"previous_job_function":"Risk Analyst","previous_org_unit":"Finance","new_position":"Senior Risk Manager","new_org_unit":"Risk & Compliance","source_system":"Workday","metadata":{"manager":"CRO","notes":"Elevated access to risk dashboard"}},
    {"employee_id":"EMP-2024-078","employee_name":"Michael Brown","event_type":"mover","effective_date":dts(-45),"previous_job_function":"Senior Accountant","previous_org_unit":"Finance","new_position":"Financial Controller","new_org_unit":"Finance","source_system":"Workday","metadata":{"manager":"CFO","notes":"Period close access granted; SoD review completed"}},
    {"employee_id":"EMP-2023-134","employee_name":"Lisa Anderson","event_type":"mover","effective_date":dts(-60),"previous_job_function":"Senior Buyer","previous_org_unit":"Procurement","new_position":"Procurement Manager","new_org_unit":"Procurement","source_system":"Workday","metadata":{"manager":"COO","notes":"Manager-level access provisioned"}},
    {"employee_id":"EMP-2025-091","employee_name":"Ryan O'Brien","event_type":"rehire","effective_date":dts(-5),"new_position":"Cloud Architect","new_org_unit":"Technology","source_system":"Workday","metadata":{"manager":"CTO","notes":"Rehired after 18-month gap; fresh background check completed"}},
    {"employee_id":"EMP-2026-006","employee_name":"Natalie Park","event_type":"joiner","effective_date":dts(-10),"new_position":"SAP Consultant (Contractor)","new_org_unit":"IT","source_system":"Workday","metadata":{"manager":"CTO","notes":"Fixed-term via Apex Consulting; limited SAP dev access","end_date":dts(80)}},
    {"employee_id":"EMP-2026-007","employee_name":"Carlos Mendes","event_type":"joiner","effective_date":dts(-20),"new_position":"GRC Implementation Consultant","new_org_unit":"Risk","source_system":"Workday","metadata":{"manager":"CRO","notes":"GovernexPlus implementation support; read-only production access","end_date":dts(40)}},
]

def seed_jml():
    section("JML — 15 lifecycle events (joiners/leavers/movers/contractors)")
    for e in JML_EVENTS:
        r, err = post("/jml/events", e)
        if ok("jml_events", r, err):
            etype = e["event_type"]
            print(f"  + [{etype:<10}] {e['employee_name']:<25} {e.get('new_position') or e.get('previous_job_function','')[:35]}")
        time.sleep(0.05)
    print(f"\n  JML events: {COUNTS.get('jml_events',0)}")

# ─────────────────────────────────────────────────────────────
# 7. BCM PLANS & INCIDENTS
# ─────────────────────────────────────────────────────────────
BCM_PLANS = [
    {"plan_name":"Business Continuity Plan - Finance Operations","plan_type":"bcp","status":"active","version":"3.2","owner_name":"CFO","description":"Ensures continuity of financial operations during disruption.","next_review_date":dts(90)},
    {"plan_name":"IT Disaster Recovery Plan","plan_type":"drp","status":"active","version":"2.1","owner_name":"CTO","description":"IT recovery procedures for core infrastructure and SAP platform.","next_review_date":dts(60)},
    {"plan_name":"Crisis Management Plan","plan_type":"crisis","status":"draft","version":"1.0","owner_name":"CEO","description":"Executive crisis management and communication procedures.","next_review_date":dts(30)},
    {"plan_name":"Pandemic & Health Emergency Response","plan_type":"bcp","status":"active","version":"2.0","owner_name":"CHRO","description":"Remote working and health emergency response procedures.","next_review_date":dts(180)},
    {"plan_name":"Cyber Incident Response Plan","plan_type":"drp","status":"active","version":"1.5","owner_name":"CISO","description":"Procedures for responding to cyber security incidents including ransomware.","next_review_date":dts(120)},
    {"plan_name":"Supply Chain Disruption Response","plan_type":"bcp","status":"active","version":"1.1","owner_name":"COO","description":"Response procedures for critical supply chain disruptions.","next_review_date":dts(120)},
]

BCM_ACTIVATIONS = [
    {"activation_reason":"SAP S/4HANA production system unavailable for 3.5 hours due to database failover issue.","incident_type":"it_outage","severity":"high","activated_by":"CTO","initial_notes":"DB team restored primary. Failover config corrected. Post-mortem completed."},
    {"activation_reason":"PaySecure gateway experienced intermittent failures affecting 12% of transactions.","incident_type":"service_degradation","severity":"medium","activated_by":"CFO","initial_notes":"Switched to backup payment provider for 4 hours."},
    {"activation_reason":"Sophisticated ransomware attempt detected and blocked by EDR. Phishing vector via finance team.","incident_type":"cyber_incident","severity":"critical","activated_by":"CISO","initial_notes":"2 endpoints quarantined. Phishing awareness training mandated."},
    {"activation_reason":"Rack P-12 power failure affected 3 non-critical servers for 2 hours.","incident_type":"facility_incident","severity":"medium","activated_by":"CTO","initial_notes":"UPS replaced. Servers restored."},
    {"activation_reason":"Global Logistics Ltd reported a data breach potentially affecting Acme shipment manifests.","incident_type":"data_breach","severity":"high","activated_by":"General Counsel","initial_notes":"Legal notified. Breach notification assessment underway."},
]

def seed_bcm():
    section("BCM — 6 plans, 5 activations")
    plan_ids = []
    for p in BCM_PLANS:
        r, e = post("/bcm/plans", p)
        if ok("bcm_plans", r, e):
            pid = r.get("id") or r.get("plan_id")
            if pid:
                plan_ids.append(pid)
            print(f"  + [{p['plan_type'].upper()}] {p['plan_name'][:55]}")
        time.sleep(0.05)

    # Get plan IDs from DB if we didn't capture them above
    if not plan_ids:
        pdata, _ = get("/bcm/plans")
        plist = pdata if isinstance(pdata, list) else pdata.get("plans", []) if pdata else []
        plan_ids = [p.get("id") for p in plist if p.get("id")]

    # Only use active plans for activations
    active_plan_ids = plan_ids  # all newly created plans are active except crisis (index 2)
    active_plan_ids_filtered = [p for j, p in enumerate(plan_ids) if j != 2]  # skip draft crisis plan
    use_ids = active_plan_ids_filtered if active_plan_ids_filtered else plan_ids
    for i, act in enumerate(BCM_ACTIVATIONS):
        if not use_ids:
            print(f"  SKIP activation (no plans): {act['activation_reason'][:40]}")
            continue
        act["plan_id"] = use_ids[i % len(use_ids)]
        r, e = post("/bcm/activations", act)
        if ok("bcm_activations", r, e):
            print(f"  + Activation [{act['severity'].upper()}]: {act['activation_reason'][:50]}")
        time.sleep(0.05)

    print(f"\n  BCM plans: {COUNTS.get('bcm_plans',0)}  |  Activations: {COUNTS.get('bcm_activations',0)}")

# ─────────────────────────────────────────────────────────────
# 8. FRAUD RULES & CASES
# ─────────────────────────────────────────────────────────────
FRAUD_RULES = [
    {"rule_name":"Duplicate Invoice Detection","rule_type":"threshold","description":"Detects invoices with same amount, vendor and date within 30-day window.","threshold_value":0,"is_active":True,"risk_score_weight":7.5,"metadata":{"field":"invoice_amount","operator":"duplicate","window_days":30}},
    {"rule_name":"Ghost Employee Detection","rule_type":"anomaly","description":"Identifies payroll payments to employees with no HR record or terminated status.","is_active":True,"risk_score_weight":9.0,"metadata":{"source":"payroll","cross_check":"hr_master","flag":"no_active_hr_record"}},
    {"rule_name":"Round-Trip Payment Detection","rule_type":"pattern","description":"Detects payments made to vendor followed by refund within 7 days.","threshold_value":10000,"is_active":True,"risk_score_weight":7.0,"metadata":{"pattern":"payment_then_refund","window_days":7}},
    {"rule_name":"Vendor Same-Day Bank Change + Payment","rule_type":"pattern","description":"Flags when vendor bank account is changed and payment processed same day.","is_active":True,"risk_score_weight":9.5,"metadata":{"event_a":"vendor_bank_change","event_b":"payment_run","max_gap_hours":24}},
    {"rule_name":"Excessive Expense Claim - Single Day","rule_type":"threshold","description":"Flags employee expense claims exceeding $2,000 in a single day.","threshold_value":2000,"is_active":True,"risk_score_weight":5.0,"metadata":{"field":"daily_expenses","threshold":2000}},
    {"rule_name":"Split Invoice Detection","rule_type":"pattern","description":"Identifies invoices deliberately split below approval thresholds.","threshold_value":9999,"is_active":True,"risk_score_weight":7.0,"metadata":{"pattern":"sequential_invoices_below_threshold","threshold":10000}},
    {"rule_name":"Vendor Employee Address Match","rule_type":"anomaly","description":"Detects when AP staff process payments to vendors with matching personal addresses.","is_active":True,"risk_score_weight":9.5,"metadata":{"cross_check":["employee_address","vendor_address","employee_bank","vendor_bank"]}},
    {"rule_name":"Weekend/Holiday Posting Anomaly","rule_type":"anomaly","description":"Flags financial postings made outside business hours by non-privileged users.","is_active":True,"risk_score_weight":5.0,"metadata":{"time_filter":"outside_business_hours","user_filter":"non_admin"}},
    {"rule_name":"Manual Journal Above Threshold","rule_type":"threshold","description":"All manual journal entries above $50,000 flagged for review.","threshold_value":50000,"is_active":True,"risk_score_weight":5.5,"metadata":{"field":"journal_amount","threshold":50000,"type":"manual"}},
    {"rule_name":"New Vendor + Immediate Large Payment","rule_type":"velocity","description":"Detects new vendor created within 7 days followed by payment >$100k.","threshold_value":100000,"is_active":True,"risk_score_weight":9.0,"metadata":{"event_a":"vendor_create","event_b":"large_payment","max_gap_days":7,"min_amount":100000}},
]

FRAUD_CASES = [
    {"title":"Suspected Vendor Fraud - Acme P2P Process","case_type":"vendor_fraud","severity":"high","status":"open","description":"Duplicate invoices detected from Apex Consulting Group. Three invoices for identical amounts ($47,200) submitted in October 2026 for same service period.","reported_by":"Fraud Detection System","assigned_to":"Mark Davies","estimated_loss":47200},
    {"title":"Ghost Employee Suspicion - Payroll Division","case_type":"payroll_fraud","severity":"critical","status":"open","description":"Payroll system contains 2 employees with no corresponding HR records. Monthly salary payments of $8,400 each since July 2026.","reported_by":"Internal Audit","assigned_to":"CHRO","estimated_loss":67200},
    {"title":"Split Invoice Scheme - IT Procurement","case_type":"procurement_fraud","severity":"high","status":"open","description":"TechRecruit Staffing submitted 6 invoices of $9,800 each (below $10k approval threshold) within 3 weeks for same project. Total $58,800 bypassed approvals.","reported_by":"AP Supervisor","assigned_to":"CFO","estimated_loss":58800},
    {"title":"Expense Claim Falsification - Sales Team","case_type":"expense_fraud","severity":"medium","status":"open","description":"3 sales staff claimed hotel expenses for a conference that was cancelled. Claims totalling $12,450 submitted with doctored receipts.","reported_by":"Finance Controller","assigned_to":"HR Manager","estimated_loss":12450},
    {"title":"Vendor Bank Account Manipulation","case_type":"vendor_fraud","severity":"critical","status":"closed","description":"Fraudster impersonated CloudSecure and requested bank account update via email. AP team updated account; 2 payments totalling $280,000 sent to fraudulent account.","reported_by":"CloudSecure","assigned_to":"CFO","estimated_loss":280000},
    {"title":"Procurement Kickback Investigation","case_type":"corruption","severity":"critical","status":"open","description":"Anonymous tip received: procurement manager receiving personal payments from Global Logistics Ltd in exchange for contract renewals above market rate.","reported_by":"Whistleblower Portal","assigned_to":"General Counsel","estimated_loss":450000},
]

def seed_fraud():
    section("FRAUD — 10 detection rules, 6 cases")
    for rule in FRAUD_RULES:
        r, e = post("/fraud/rules", rule)
        if ok("fraud_rules", r, e):
            print(f"  + Rule: {rule['rule_name'][:50]}")
        time.sleep(0.05)

    for case in FRAUD_CASES:
        r, e = post("/fraud/cases", case)
        if ok("fraud_cases", r, e):
            print(f"  + Case [{case['severity'].upper()}]: {case['title'][:50]}")
        time.sleep(0.05)

    print(f"\n  Fraud rules: {COUNTS.get('fraud_rules',0)}  |  Cases: {COUNTS.get('fraud_cases',0)}")

# ─────────────────────────────────────────────────────────────
# 9. ACCESS REQUESTS
# ─────────────────────────────────────────────────────────────
ACCESS_REQUESTS = [
    {"request_type":"new_access","requested_by":"EMP-2026-003","requested_for":"EMP-2026-003","system":"SAP ERP","access_level":"read","role_ids":["RISK_ANALYST_RO"],"business_justification":"New Risk Analyst requires read-only access to risk reports and financial data.","urgency":"normal","status":"pending"},
    {"request_type":"new_access","requested_by":"EMP-2026-004","requested_for":"EMP-2026-004","system":"SAP ERP","access_level":"read","role_ids":["AUDIT_READONLY","AUDIT_REPORTING"],"business_justification":"New IT Auditor requires access to audit workpapers and SAP change logs.","urgency":"high","status":"pending"},
    {"request_type":"elevated_access","requested_by":"EMP-2024-055","requested_for":"EMP-2024-055","system":"SAP ERP","access_level":"write","role_ids":["SECURITY_ADMIN"],"business_justification":"Security Analyst needs temporary write access to security audit log tables for investigation.","urgency":"high","status":"pending","duration_days":7},
    {"request_type":"new_access","requested_by":"EMP-2026-007","requested_for":"EMP-2026-007","system":"GovernexPlus GRC","access_level":"admin","role_ids":["GRC_ADMIN"],"business_justification":"GRC consultant requires admin access for implementation configuration.","urgency":"normal","status":"approved"},
    {"request_type":"remove_access","requested_by":"VP Finance","requested_for":"EMP-2025-089","system":"SAP ERP","access_level":"all","business_justification":"Employee Robert Davis left the organisation on 27 Oct 2026. All access must be revoked.","urgency":"critical","status":"completed"},
    {"request_type":"modify_access","requested_by":"EMP-2024-078","requested_for":"EMP-2024-078","system":"SAP ERP","access_level":"write","role_ids":["FI_PERIOD_CLOSE","FI_REPORTING"],"business_justification":"Promotion to Financial Controller. Requires period close and GL reporting access.","urgency":"normal","status":"approved"},
    {"request_type":"new_access","requested_by":"EMP-2026-006","requested_for":"EMP-2026-006","system":"SAP DEV","access_level":"developer","role_ids":["BASIS_DEV","ABAP_DEV"],"business_justification":"SAP Consultant (Natalie Park) requires development system access for customisation work.","urgency":"normal","status":"pending"},
    {"request_type":"new_access","requested_by":"EMP-2026-005","requested_for":"EMP-2026-005","system":"Treasury Management","access_level":"write","role_ids":["TREASURY_ANALYST"],"business_justification":"New Treasury Analyst requires access to FX trading and liquidity management modules.","urgency":"normal","status":"pending"},
    {"request_type":"elevated_access","requested_by":"CISO","requested_for":"EMP-2024-055","system":"SAP PROD","access_level":"firefighter","role_ids":["FF_SECURITY_INVESTIGATION"],"business_justification":"Security incident investigation requires temporary firefighter access to review logs.","urgency":"critical","status":"approved","duration_days":1},
    {"request_type":"new_access","requested_by":"EMP-2026-001","requested_for":"EMP-2026-001","system":"PowerBI Analytics","access_level":"write","role_ids":["FINANCE_ANALYST_PBI"],"business_justification":"Senior Financial Analyst needs access to finance dashboards and self-service BI.","urgency":"normal","status":"completed"},
]

def seed_access_requests():
    section("ACCESS REQUESTS — 10 requests")
    for req in ACCESS_REQUESTS:
        r, e = post("/access-requests/", req)
        if ok("access_requests", r, e):
            print(f"  + [{req['request_type'].upper():<15}] {req['requested_for']:<15} {req['system']:<25} [{req['status']}]")
        time.sleep(0.05)
    print(f"\n  Access requests: {COUNTS.get('access_requests',0)}")

# ─────────────────────────────────────────────────────────────
# 10. WHISTLEBLOWER REPORTS (public endpoint)
# ─────────────────────────────────────────────────────────────
WHISTLEBLOWER_REPORTS = [
    {"category":"corruption","title":"Procurement Manager Receiving Vendor Payments","description":"I have evidence that the procurement manager is receiving payments from a logistics vendor in exchange for awarding contracts above market rate. This has been happening for at least 12 months. I have seen bank statements.","is_anonymous":True,"priority":"high"},
    {"category":"harassment","title":"IT Manager Bullying Team Members","description":"A senior manager in the IT department has been bullying team members and taking credit for their work. Several staff members have raised this internally but HR has done nothing.","is_anonymous":False,"submitter_name":"Concerned Employee","submitter_email":"employee.concern@acme.com","priority":"normal"},
    {"category":"fraud","title":"Duplicate Payments to Consulting Firm - $140k","description":"The accounts payable team processed three duplicate payments to a consulting firm last month. When I raised it with my supervisor, I was told to stay quiet. The total amount is around $140,000.","is_anonymous":True,"priority":"high"},
    {"category":"other","title":"Customer PII Shared Without Consent - Marketing","description":"Customer PII data is being shared with a third party without consent. I was asked to export customer contact lists for an unsanctioned marketing campaign.","is_anonymous":True,"priority":"high"},
    {"category":"safety","title":"Blocked Emergency Exit - Level 12 Fire Hazard","description":"The emergency exit on Level 12 has been blocked by IT equipment for three months. I have reported it to facilities twice but nothing has happened. This is a fire safety risk.","is_anonymous":False,"submitter_name":"Level 12 Staff","priority":"urgent"},
]

def seed_whistleblower():
    section("WHISTLEBLOWER — 5 reports (public endpoint)")
    pub_headers = {"Content-Type": "application/json"}
    for rpt in WHISTLEBLOWER_REPORTS:
        url = f"{BASE}/whistleblower/submit"
        data = json.dumps(rpt).encode()
        req = urllib.request.Request(url, data=data, headers=pub_headers, method="POST")
        try:
            resp = urllib.request.urlopen(req, timeout=20)
            r = json.loads(resp.read())
            COUNTS["wb_reports"] = COUNTS.get("wb_reports", 0) + 1
            ref = r.get("reference_number") or r.get("ref", "?")
            print(f"  + [{rpt['category'].upper():<20}] Anon:{rpt['is_anonymous']}  Ref:{ref}")
        except urllib.error.HTTPError as e:
            print(f"  WARN [wb_reports]: {e.code}: {e.read().decode()[:120]}")
        time.sleep(0.05)
    print(f"\n  Whistleblower reports: {COUNTS.get('wb_reports',0)}")

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("="*65)
    print("  GovernexPlus Extensive Data Seeder")
    print(f"  Target: {BASE}")
    print(f"  Tenant: {TENANT}")
    print("="*65)

    login()

    risk_ids = seed_risks()
    seed_kri_measurements()
    seed_workflows()
    seed_audit()
    seed_tprm()
    seed_jml()
    seed_bcm()
    seed_fraud()
    seed_access_requests()
    seed_whistleblower()

    print("\n" + "="*65)
    print("  SEEDING COMPLETE — SUMMARY")
    print("="*65)
    for module, count in sorted(COUNTS.items()):
        print(f"  {module:<28}: {count}")
    total = sum(COUNTS.values())
    print(f"\n  TOTAL RECORDS CREATED: {total}")
    print("="*65)
