#!/usr/bin/env python3
"""Seed realistic demo data for GvnX tenant."""
from dotenv import load_dotenv
load_dotenv()

from db.database import db_manager
from db.models.user import User, Role, UserRole
from db.models.risk import RiskViolation, MitigationControl
from db.models.firefighter import FirefighterRequest
from db.models.audit import CertificationCampaignLog
from db.models.risk_management import (
    EnterpriseRisk, RiskAssessment, RiskAppetite,
    KeyRiskIndicator, RiskIncident,
)
from db.models.process_control import (
    ProcessControl, ControlTest, ControlDeficiency,
    CCMRule, GRCEvidence, SignOffCertification,
)
from db.models.audit_management import (
    AuditableEntity, AuditPlan, AuditEngagement,
    AuditFinding, AuditorResource,
)
from db.models.grc_foundation import OrgUnit, FrameworkDefinition, FrameworkRequirement
from passlib.context import CryptContext
from datetime import datetime, timedelta
import random
import uuid

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
T = "gvnx"
now = datetime.utcnow()


def rid():
    return uuid.uuid4().hex[:12]


NAMES = [
    "Rahul Sharma", "Priya Patel", "Amit Kumar", "Sneha Reddy", "Vikram Singh",
    "Anjali Gupta", "Rajesh Nair", "Meera Joshi", "Suresh Iyer", "Deepa Menon",
    "Arjun Das", "Kavitha Rao", "Manoj Pillai", "Lakshmi Subramanian", "Kiran Desai",
    "Neha Agarwal", "Sanjay Mehta", "Ritu Bhatt", "Anil Raju", "Swati Chopra",
    "Gaurav Verma", "Pooja Saxena", "Nitin Kulkarni", "Divya Krishnan", "Rohit Tiwari",
    "Isha Malhotra", "Varun Sinha", "Shruti Kaur", "Pranav Bose", "Megha Dhawan",
    "Tarun Jain", "Nandini Hegde", "Ashok Mishra", "Pallavi Chatterjee", "Vivek Pandey",
    "Sunita Yadav", "Hemant Goel", "Rashmi Banerjee", "Siddharth Kapoor", "Ananya Sen",
    "Dinesh Thakur", "Jayashree Nayak", "Manish Aggarwal", "Rekha Devi", "Pankaj Bajaj",
    "Usha Sundaram", "Abhishek Chauhan", "Geeta Mahajan", "Ramesh Bhat", "Sarita Mohan",
]

DEPTS = ["Finance", "IT", "HR", "Procurement", "Sales"]

ROLE_DEFS = [
    ("Z_FI_AP_CLERK", "AP Clerk"), ("Z_FI_AP_MANAGER", "AP Manager"),
    ("Z_FI_GL_ACCOUNTANT", "GL Accountant"), ("Z_FI_PAYMENT_ADMIN", "Payment Administrator"),
    ("Z_FI_VENDOR_ADMIN", "Vendor Administrator"), ("Z_FI_AR_CLERK", "AR Clerk"),
    ("Z_FI_TREASURY", "Treasury Analyst"), ("Z_FI_CONTROLLER", "Financial Controller"),
    ("Z_MM_BUYER", "Procurement Buyer"), ("Z_MM_PO_APPROVER", "PO Approver"),
    ("Z_MM_WAREHOUSE", "Warehouse Manager"), ("Z_MM_INVOICE", "Invoice Processor"),
    ("Z_SD_SALES_REP", "Sales Representative"), ("Z_SD_ORDER_ADMIN", "Order Administrator"),
    ("Z_SD_BILLING", "Billing Specialist"), ("Z_SD_PRICING", "Pricing Manager"),
    ("Z_HR_ADMIN", "HR Administrator"), ("Z_HR_PAYROLL", "Payroll Processor"),
    ("Z_HR_RECRUITER", "Recruiter"), ("Z_HR_BENEFITS", "Benefits Coordinator"),
    ("Z_IT_BASIS", "Basis Administrator"), ("Z_IT_SECURITY", "Security Administrator"),
    ("Z_IT_DEVELOPER", "ABAP Developer"), ("Z_IT_TRANSPORT", "Transport Manager"),
    ("SAP_ALL", "Full Authorization"), ("SAP_NEW", "New Authorization"),
    ("Z_FIORI_AP", "Fiori AP User"), ("Z_FIORI_MM", "Fiori MM User"),
    ("Z_BW_REPORTER", "BW Report Viewer"), ("Z_GRC_ADMIN", "GRC Administrator"),
]

SOD_PAIRS = [
    ("Vendor Creation", "Payment Processing"), ("PO Creation", "PO Approval"),
    ("Customer Creation", "Credit Memo"), ("Vendor Change", "Payment Run"),
    ("GL Posting", "Bank Reconciliation"), ("Payroll Processing", "HR Master Data"),
]

RISK_TITLES = [
    "Unauthorized Vendor Payments", "SoD Conflicts in Finance", "Excessive Privileged Access",
    "Payroll Data Manipulation", "Customer Data Breach", "Procurement Fraud",
    "Inadequate Change Management", "Business Continuity Failure", "Regulatory Non-Compliance",
    "Third-Party Vendor Risk", "Financial Reporting Errors", "IT Infrastructure Failure",
    "Employee Fraud", "Supply Chain Disruption", "Cyber Attack",
]

CTRL_DEFS = [
    ("Three-Way Match", "preventive", "automated", "continuous", "Procure-to-Pay"),
    ("Vendor Approval", "preventive", "manual", "continuous", "Vendor Management"),
    ("Payment Authorization", "preventive", "manual", "continuous", "Payment Processing"),
    ("Journal Approval", "preventive", "manual", "continuous", "Record-to-Report"),
    ("Bank Reconciliation", "detective", "manual", "monthly", "Treasury"),
    ("Duplicate Payment Check", "detective", "automated", "daily", "Payment Processing"),
    ("User Access Review", "detective", "manual", "quarterly", "IT Security"),
    ("Segregation of Duties", "preventive", "automated", "continuous", "IT Security"),
    ("Password Policy", "preventive", "automated", "continuous", "IT Security"),
    ("Change Management", "preventive", "manual", "continuous", "IT Operations"),
    ("Inventory Count", "detective", "manual", "quarterly", "Warehouse"),
    ("Credit Limit Check", "preventive", "automated", "continuous", "Order-to-Cash"),
]


def main():
    with db_manager.session_scope() as s:
        # 1. Org Units
        for name, utype in [("GvnX Corporation", "company"), ("Finance", "department"),
                             ("IT", "department"), ("HR", "department"),
                             ("Procurement", "department"), ("Sales", "department")]:
            s.add(OrgUnit(tenant_id=T, unit_id=f"OU_{rid()}", name=name, unit_type=utype,
                          level=1 if utype == "company" else 2, is_active=True,
                          created_at=now, updated_at=now))
        s.flush()
        print("Org units: 6")

        # 2. Users (50)
        users = []
        for i, name in enumerate(NAMES):
            parts = name.split()
            uid = parts[0].upper()[:6] + str(i).zfill(2)
            u = User(tenant_id=T, user_id=uid, username=uid.lower(),
                     email=f"{parts[0].lower()}.{parts[1].lower()}@gvnx.com",
                     full_name=name, department=DEPTS[i % 5], status="active",
                     is_platform_user=(i < 5),
                     password_hash=pwd_ctx.hash("User@2026!"),
                     risk_score=random.uniform(0, 80),
                     violation_count=random.randint(0, 8),
                     created_at=now, updated_at=now)
            s.add(u)
            users.append(u)
        s.flush()
        print(f"Users: {len(users)}")

        # 3. Roles (30)
        roles = []
        for role_id, desc in ROLE_DEFS:
            rl = "critical" if "ALL" in role_id else random.choice(["low", "medium", "high"])
            r = Role(tenant_id=T, role_id=role_id, role_name=desc,
                     description=f"{desc} role", role_type="single", risk_level=rl,
                     is_sensitive=("ALL" in role_id or "SECURITY" in role_id),
                     user_count=random.randint(2, 30), is_active=True,
                     created_at=now, updated_at=now)
            s.add(r)
            roles.append(r)
        s.flush()
        print(f"Roles: {len(roles)}")

        # 4. User-Role Assignments
        count = 0
        for u in users:
            for r in random.sample(roles, min(random.randint(2, 5), len(roles))):
                s.add(UserRole(tenant_id=T, user_id=u.id, role_id=r.id,
                               assigned_by="SYSTEM", is_active=True,
                               created_at=now, updated_at=now))
                count += 1
        s.flush()
        print(f"Assignments: {count}")

        # 5. Risk Violations (25)
        for i in range(25):
            pair = SOD_PAIRS[i % len(SOD_PAIRS)]
            u = random.choice(users)
            s.add(RiskViolation(
                tenant_id=T, violation_id=f"VIO-{rid()}",
                rule_id=f"SOD-FI-{(i % 12) + 1:03d}",
                rule_name=f"{pair[0]} + {pair[1]}", rule_type="sod",
                user_id=u.id, user_external_id=u.user_id, username=u.full_name,
                severity=random.choice(["low", "medium", "high", "critical"]),
                severity_score=random.randint(30, 95), risk_category="Financial",
                status="open",
                business_impact=f"User can both {pair[0].lower()} and {pair[1].lower()}",
                detected_at=now - timedelta(days=random.randint(1, 60)),
                created_at=now, updated_at=now,
            ))
        s.flush()
        print("Violations: 25")

        # 6. Mitigation Controls (8)
        for i in range(8):
            s.add(MitigationControl(
                tenant_id=T, control_id=f"MIT-{rid()}",
                control_name=f"Compensating Control #{i + 1}",
                description="Independent review of transactions",
                control_type=random.choice(["detective", "preventive"]),
                monitoring_frequency=random.choice(["daily", "weekly", "monthly"]),
                owner_user_id=random.choice(users[:10]).user_id,
                is_active=True, valid_from=now, created_at=now, updated_at=now,
            ))
        s.flush()
        print("Mitigation controls: 8")

        # 7. Enterprise Risks (15)
        risks = []
        for i, title in enumerate(RISK_TITLES):
            cat = ["financial", "operational", "compliance", "it_cyber", "strategic"][i % 5]
            il, ii = random.randint(2, 5), random.randint(2, 5)
            rl, ri = max(1, il - 1), max(1, ii - 1)
            r = EnterpriseRisk(
                tenant_id=T, risk_id=f"RSK-{rid()}", title=title,
                description=f"Risk of {title.lower()} impacting operations",
                category=cat, risk_owner_id=random.choice(users[:10]).user_id,
                risk_owner_name=random.choice(users[:10]).full_name,
                inherent_likelihood=il, inherent_impact=ii, inherent_score=il * ii,
                residual_likelihood=rl, residual_impact=ri, residual_score=rl * ri,
                status=random.choice(["identified", "assessed", "mitigated"]),
                review_frequency="quarterly", is_active=True,
                created_at=now, updated_at=now,
            )
            s.add(r)
            risks.append(r)
        s.flush()
        print(f"Enterprise risks: {len(risks)}")

        # 8. Risk Assessments
        for r in risks:
            s.add(RiskAssessment(
                tenant_id=T, assessment_id=f"ASS-{rid()}", risk_id=r.id,
                assessor_id=random.choice(users[:5]).user_id,
                assessor_name=random.choice(users[:5]).full_name,
                likelihood_score=r.residual_likelihood, impact_score=r.residual_impact,
                overall_score=r.residual_score, assessment_type="periodic",
                status="approved", created_at=now, updated_at=now,
            ))
        print("Risk assessments: 15")

        # 9. KRIs (6)
        for name, g, a, r_val, unit in [
            ("Open SoD Violations", 50, 100, 200, "count"),
            ("Privileged Users", 10, 25, 50, "count"),
            ("Failed Controls", 5, 10, 20, "count"),
            ("Overdue Audit Findings", 3, 8, 15, "count"),
            ("Risk Appetite Utilization", 60, 80, 95, "%"),
            ("Vendor Bank Changes", 20, 50, 100, "count"),
        ]:
            s.add(KeyRiskIndicator(
                tenant_id=T, kri_id=f"KRI-{rid()}", name=name,
                data_source="manual", unit_of_measure=unit, frequency="weekly",
                threshold_green=g, threshold_amber=a, threshold_red=r_val,
                current_value=random.uniform(g * 0.5, r_val * 0.8),
                status=random.choice(["normal", "warning", "breach"]),
                is_active=True, created_at=now, updated_at=now,
            ))
        print("KRIs: 6")

        # 10. Incidents (5)
        for i in range(5):
            s.add(RiskIncident(
                tenant_id=T, incident_id=f"INC-{rid()}",
                title=f"Security Incident #{i + 1}",
                description="Security/compliance incident detected",
                severity=random.choice(["low", "medium", "high", "critical"]),
                financial_impact=random.uniform(5000, 500000), currency="USD",
                occurred_at=now - timedelta(days=random.randint(5, 90)),
                reported_by=random.choice(users[:5]).user_id,
                status=random.choice(["reported", "investigating", "resolved"]),
                created_at=now, updated_at=now,
            ))
        print("Incidents: 5")

        # 11. Process Controls (12)
        controls = []
        for name, ctype, nature, freq, process in CTRL_DEFS:
            c = ProcessControl(
                tenant_id=T, control_id=f"CTL-{rid()}", name=name,
                objective=f"Ensure {name.lower()} is effective",
                control_type=ctype, control_nature=nature, frequency=freq,
                process_name=process, owner_id=random.choice(users[:10]).user_id,
                key_control=(ctype == "preventive"), status="active",
                version=1, is_active=True, created_at=now, updated_at=now,
            )
            s.add(c)
            controls.append(c)
        s.flush()
        print(f"Controls: {len(controls)}")

        # 12. Control Tests
        for c in controls:
            s.add(ControlTest(
                tenant_id=T, test_id=f"TST-{rid()}", control_id=c.id,
                test_type=random.choice(["operating_effectiveness", "design"]),
                testing_period_start=now - timedelta(days=90),
                testing_period_end=now, sample_size=25,
                tester_id=random.choice(users[:5]).user_id,
                tester_name=random.choice(users[:5]).full_name,
                result=random.choice(["effective", "effective", "effective", "ineffective"]),
                exceptions_found=random.randint(0, 5),
                conclusion="Test completed per procedure",
                status="completed", created_at=now, updated_at=now,
            ))
        print("Control tests: 12")

        # 13. Deficiencies (4)
        for i in range(4):
            s.add(ControlDeficiency(
                tenant_id=T, deficiency_id=f"DEF-{rid()}",
                control_id=random.choice(controls).id,
                source=random.choice(["test", "monitoring"]),
                title=f"Control gap #{i + 1}",
                description="Control deficiency identified during testing",
                severity=random.choice(["significant_deficiency", "control_gap", "observation"]),
                remediation_owner_id=random.choice(users[:10]).user_id,
                due_date=now + timedelta(days=random.randint(15, 60)),
                status=random.choice(["open", "in_remediation"]),
                created_at=now, updated_at=now,
            ))
        print("Deficiencies: 4")

        # 14. CCM Rules (5)
        for name, rtype in [("Password Policy", "config_check"), ("Duplicate Payments", "data_pattern"),
                            ("Vendor Bank Changes", "threshold"), ("SoD Bridge", "sod_bridge"),
                            ("PO Limits", "threshold")]:
            s.add(CCMRule(
                tenant_id=T, rule_id=f"CCM-{rid()}", name=name,
                source_system="SAP", rule_type=rtype,
                rule_definition={"check": name.lower().replace(" ", "_")},
                frequency="daily", is_active=True, auto_create_deficiency=True,
                created_at=now, updated_at=now,
            ))
        print("CCM rules: 5")

        # 15. Framework
        fw = FrameworkDefinition(
            tenant_id=T, framework_id=f"FW-{rid()}", name="COSO 2013",
            version="2013", framework_type="coso", is_active=True,
            created_at=now, updated_at=now,
        )
        s.add(fw)
        s.flush()
        for i, title in enumerate(["Control Environment", "Risk Assessment",
                                    "Control Activities", "Information & Communication", "Monitoring"]):
            s.add(FrameworkRequirement(
                tenant_id=T, framework_id=fw.id, requirement_id=f"COSO-{i + 1}",
                title=title, category="COSO Principle", level=1, sort_order=i + 1,
                created_at=now, updated_at=now,
            ))
        print("Framework: COSO 2013 + 5 principles")

        # 16. Audit
        entities = []
        for name, etype in [("Procure-to-Pay", "process"), ("Finance Department", "org_unit"),
                             ("SAP S/4HANA", "system"), ("Payroll", "process"), ("IT Security", "process")]:
            ae = AuditableEntity(
                tenant_id=T, entity_id=f"ENT-{rid()}", name=name,
                entity_type=etype, audit_frequency="annual",
                risk_score=random.uniform(40, 90), is_active=True,
                created_at=now, updated_at=now,
            )
            s.add(ae)
            entities.append(ae)
        s.flush()

        plan = AuditPlan(
            tenant_id=T, plan_id=f"PLAN-{rid()}", name="FY2026 Annual Audit Plan",
            plan_type="annual", fiscal_year=2026, total_audit_hours=2000,
            status="approved", created_at=now, updated_at=now,
        )
        s.add(plan)
        s.flush()

        eng = AuditEngagement(
            tenant_id=T, engagement_id=f"ENG-{rid()}", plan_id=plan.id,
            entity_id=entities[0].id, title="P2P Process Audit FY2026",
            objective="Assess P2P controls", scope="Vendor mgmt, PO, payments",
            engagement_type="operational", status="fieldwork",
            lead_auditor_id=users[0].user_id, lead_auditor_name=users[0].full_name,
            planned_start=now - timedelta(days=30), planned_end=now + timedelta(days=30),
            budget_hours=200, actual_hours=120,
            created_at=now, updated_at=now,
        )
        s.add(eng)
        s.flush()

        findings = [("Dual control bypassed on FK02", "high"),
                    ("Vendor approval delays", "medium"),
                    ("Excessive privileged access", "critical"),
                    ("Missing evidence for payment control", "medium")]
        for i, (title, sev) in enumerate(findings):
            s.add(AuditFinding(
                tenant_id=T, finding_id=f"FND-{rid()}", engagement_id=eng.id,
                ref_number=f"F-{i + 1:03d}", title=title,
                condition=f"{title} identified during testing",
                criteria="Per company policy and regulatory requirements",
                cause="Insufficient controls and monitoring",
                effect="Potential financial loss and compliance exposure",
                recommendation="Strengthen controls and implement monitoring",
                severity=sev, category="operational",
                status="final", created_at=now, updated_at=now,
            ))

        s.add(AuditorResource(
            tenant_id=T, auditor_id=f"AUD-{rid()}", name="Sarah Chen",
            email="sarah.chen@gvnx.com", title="Senior IT Auditor",
            skills=["IT audit", "SAP security", "SoD", "data analytics"],
            certifications=["CISA", "CISSP"], available_hours_per_month=140,
            is_active=True, created_at=now, updated_at=now,
        ))
        print("Audit: 5 entities, 1 plan, 1 engagement, 4 findings, 1 auditor")

        # 17. Risk Appetite
        for cat in ["financial", "operational", "compliance", "it_cyber", "strategic"]:
            s.add(RiskAppetite(
                tenant_id=T, category=cat, appetite_score=10.0, tolerance_score=15.0,
                description=f"{cat.title()} risk appetite", approved_by="CFO",
                created_at=now, updated_at=now,
            ))
        print("Risk appetites: 5")

        # 18. Firefighter Requests
        for i in range(3):
            s.add(FirefighterRequest(
                tenant_id=T, request_id=f"FF-{rid()}",
                firefighter_id=f"FF_SAP_{i + 1:03d}",
                requester_user_id=users[i].user_id,
                requester_name=users[i].full_name,
                reason_code="INCIDENT", reason=f"Production issue #{i + 1}",
                duration_minutes=120,
                status=random.choice(["approved", "completed", "pending"]),
                created_at=now - timedelta(days=random.randint(1, 30)),
                updated_at=now,
            ))
        print("Firefighter requests: 3")

        # 19. Certification Campaign
        s.add(CertificationCampaignLog(
            tenant_id=T, campaign_id=f"CERT-{rid()}",
            campaign_name="Q3-2026 User Access Review",
            campaign_type="user_access", status="in_progress",
            total_items=50, completed_items=35, certified_items=30, revoked_items=5,
            owner_id=users[0].user_id,
            due_date=now + timedelta(days=14),
            created_at=now - timedelta(days=20), updated_at=now,
        ))
        print("Certification campaigns: 1")

        # 20. SOX Signoff
        s.add(SignOffCertification(
            tenant_id=T, certification_id=f"SOC-{rid()}", period="Q3-2026",
            certifier_id=users[0].user_id, certifier_name=users[0].full_name,
            certifier_role="process_owner",
            controls_in_scope=12, controls_effective=10, deficiencies_open=2,
            status="pending", created_at=now, updated_at=now,
        ))
        print("SOX signoffs: 1")

        s.commit()
        print("\n=== GvnX SEED COMPLETE ===")


if __name__ == "__main__":
    main()
