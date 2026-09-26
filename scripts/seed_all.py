#!/usr/bin/env python3
"""
Comprehensive Seed Script — Seeds ALL modules for UAT

Creates realistic data across:
- Audit logs (user, role, risk, firefighter, approver, system events)
- Access Requests (various statuses, risk levels, SLA)
- Firefighter sessions (active, completed, revoked, with activities)
- Risk violations (via rule engine evaluation)

Run:
    python scripts/seed_all.py
    python scripts/seed_all.py --clear
"""

import asyncio
import sys
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import db_manager
from db.models.audit import AuditLog, AuditAction
from audit.logger import audit_logger

# Access Request imports
from core.access_request import (
    AccessRequestManager, AccessRequestStatus, RequestType, ApprovalAction
)
from core.rules import RuleEngine
from core.rules.models import UserAccess, Entitlement

# Firefighter imports
from core.firefighter import (
    FirefighterManager, ReasonCode, RequestPriority, SessionStatus
)
from connectors.sap.mock_connector import SAPMockConnector
from connectors.base import ConnectionConfig, ConnectionType

# ===========================================================================
# Config
# ===========================================================================

TENANT = "tenant_default"

USERS = [
    ("JSMITH", "John Smith", "john.smith@company.com", "Finance"),
    ("MBROWN", "Mary Brown", "mary.brown@company.com", "Procurement"),
    ("DWILSON", "David Wilson", "david.wilson@company.com", "IT Operations"),
    ("LJONES", "Lisa Jones", "lisa.jones@company.com", "Human Resources"),
    ("RGARCIA", "Robert Garcia", "robert.garcia@company.com", "Finance"),
    ("SLEE", "Sarah Lee", "sarah.lee@company.com", "Sales"),
    ("KTAYLOR", "Kevin Taylor", "kevin.taylor@company.com", "Engineering"),
    ("AWHITE", "Ashley White", "ashley.white@company.com", "Legal & Compliance"),
    ("MTHOMAS", "Matthew Thomas", "matthew.thomas@company.com", "Operations"),
    ("JMARTIN", "Jessica Martin", "jessica.martin@company.com", "Marketing"),
    ("CCLARK", "Charles Clark", "charles.clark@company.com", "IT Operations"),
    ("NWALKER", "Nancy Walker", "nancy.walker@company.com", "Procurement"),
    ("PHARRIS", "Paul Harris", "paul.harris@company.com", "Finance"),
    ("EKING", "Emily King", "emily.king@company.com", "Quality Assurance"),
    ("TWRIGHT", "Thomas Wright", "thomas.wright@company.com", "R&D"),
]

SAP_ROLES = [
    "Z_AP_CLERK", "Z_AR_CLERK", "Z_PURCHASER", "Z_GL_ACCOUNTANT",
    "Z_BUYER", "Z_HR_ADMIN", "Z_IT_ADMIN", "Z_SECURITY_ADMIN",
    "Z_AUDITOR", "Z_CONTROLLER", "Z_SALES_REP", "Z_MRP_PLANNER",
]

FF_IDS = ["FF_EMERGENCY_01", "FF_EMERGENCY_02", "FF_SAP_ADMIN_01", "FF_BASIS_01"]

APPROVERS = ["SEC_OFFICER", "LINE_MGR_01", "COMPLIANCE_MGR", "IT_MANAGER", "CISO"]

JUSTIFICATIONS = [
    "User needs access for quarterly close activities",
    "New hire onboarding — role required per job description",
    "Project Phoenix requires temporary elevated access",
    "Audit preparation — reviewer needs read access to GL",
    "Department transfer — migrating roles from old position",
    "SOX compliance testing — temporary auditor access needed",
    "Emergency production fix — change ticket CHG0045678",
    "Month-end processing requires AP clerk privileges",
    "Cross-training program — temporary purchasing access",
    "Regulatory requirement — compliance role assignment",
]

FF_REASONS = [
    ("Production incident — system P01 database lock", ReasonCode.PROD_INCIDENT, RequestPriority.CRITICAL),
    ("Month-end close processing", ReasonCode.MONTH_END, RequestPriority.HIGH),
    ("Scheduled change CHG0098765", ReasonCode.CHANGE_MANAGEMENT, RequestPriority.MEDIUM),
    ("External audit evidence collection", ReasonCode.AUDIT_REQUEST, RequestPriority.MEDIUM),
    ("Data correction for vendor master", ReasonCode.DATA_CORRECTION, RequestPriority.HIGH),
    ("Quarterly system maintenance window", ReasonCode.SYSTEM_MAINTENANCE, RequestPriority.MEDIUM),
    ("Security incident investigation", ReasonCode.SECURITY_INCIDENT, RequestPriority.CRITICAL),
    ("Disaster recovery drill", ReasonCode.DISASTER_RECOVERY, RequestPriority.CRITICAL),
]

FF_ACTIVITIES = [
    ("TCODE_EXECUTE", {"tcode": "SE16N", "table": "BKPF", "desc": "View accounting documents"}, True),
    ("TCODE_EXECUTE", {"tcode": "FB01", "desc": "Post accounting document"}, False),
    ("DATA_CHANGE", {"tcode": "FK02", "vendor": "V00100", "field": "payment_terms"}, True),
    ("TCODE_EXECUTE", {"tcode": "SU01", "user": "TEMP_USER", "desc": "User maintenance"}, True),
    ("REPORT_RUN", {"tcode": "FAGLL03", "desc": "GL line items report"}, False),
    ("TCODE_EXECUTE", {"tcode": "SM37", "desc": "Job monitoring"}, False),
    ("DATA_CHANGE", {"tcode": "ME22N", "po": "4500012345", "desc": "Change PO"}, True),
    ("TCODE_EXECUTE", {"tcode": "PFCG", "role": "Z_AP_CLERK", "desc": "Role maintenance"}, True),
    ("REPORT_RUN", {"tcode": "SUIM", "desc": "User information system"}, False),
    ("TCODE_EXECUTE", {"tcode": "SM21", "desc": "System log review"}, False),
]


# ===========================================================================
# Seed Audit Logs
# ===========================================================================

def seed_audit_logs():
    """Create a rich variety of audit log entries across all categories."""
    print("\n--- Seeding Audit Logs ---")
    count = 0

    now = datetime.utcnow()

    # User events
    for user_id, name, email, dept in USERS[:8]:
        # Logins
        for d in range(random.randint(3, 10)):
            audit_logger.log(
                action=AuditAction.USER_LOGIN,
                actor_user_id=user_id,
                actor_username=name,
                target_type="User",
                target_id=user_id,
                target_name=name,
                source_ip=f"10.0.{random.randint(1,10)}.{random.randint(1,254)}",
                success=random.random() > 0.1,
                error_message="Invalid credentials" if random.random() < 0.1 else None,
            )
            count += 1

    # User CRUD events
    for user_id, name, email, dept in USERS[8:12]:
        audit_logger.log(
            action=AuditAction.USER_CREATED,
            actor_user_id="ADMIN",
            actor_username="System Admin",
            target_type="User",
            target_id=user_id,
            target_name=name,
            details={"department": dept, "email": email},
            success=True,
            compliance_relevant=True,
            compliance_tags=["SOX", "GRC"],
        )
        count += 1

    # Some user modifications
    for user_id, name, email, dept in USERS[:4]:
        audit_logger.log(
            action=AuditAction.USER_MODIFIED,
            actor_user_id="ADMIN",
            actor_username="System Admin",
            target_type="User",
            target_id=user_id,
            target_name=name,
            old_values={"department": "General"},
            new_values={"department": dept},
            success=True,
            compliance_relevant=True,
            compliance_tags=["GRC"],
        )
        count += 1

    # User lock/unlock
    audit_logger.log(
        action=AuditAction.USER_LOCKED,
        actor_user_id="SYSTEM",
        actor_username="System",
        actor_type="system",
        target_type="User",
        target_id="RGARCIA",
        target_name="Robert Garcia",
        details={"reason": "3 failed login attempts"},
        success=True,
    )
    count += 1

    audit_logger.log(
        action=AuditAction.USER_UNLOCKED,
        actor_user_id="SEC_OFFICER",
        actor_username="Security Officer",
        target_type="User",
        target_id="RGARCIA",
        target_name="Robert Garcia",
        details={"reason": "Password reset verified"},
        success=True,
    )
    count += 1

    # Role events
    for i in range(8):
        user_id, name, _, _ = random.choice(USERS)
        role = random.choice(SAP_ROLES)
        audit_logger.log(
            action=AuditAction.ROLE_ASSIGNED,
            actor_user_id="ADMIN",
            actor_username="System Admin",
            target_type="User",
            target_id=user_id,
            target_name=name,
            details={"role_id": role, "role_name": role.replace("Z_", "").replace("_", " ").title()},
            success=True,
            compliance_relevant=True,
            compliance_tags=["SOX"],
        )
        count += 1

    for i in range(3):
        role = random.choice(SAP_ROLES)
        audit_logger.log(
            action=AuditAction.ROLE_CREATED,
            actor_user_id="ADMIN",
            actor_username="System Admin",
            target_type="Role",
            target_id=role,
            target_name=role.replace("Z_", "").replace("_", " ").title(),
            success=True,
            compliance_relevant=True,
            compliance_tags=["SOX", "GRC"],
        )
        count += 1

    # Risk events
    for i in range(5):
        user_id, name, _, _ = random.choice(USERS)
        severity = random.choice(["CRITICAL", "HIGH", "MEDIUM", "LOW"])
        audit_logger.log(
            action=AuditAction.RISK_ANALYSIS_RUN,
            actor_user_id="SYSTEM",
            actor_username="Risk Engine",
            actor_type="system",
            target_type="User",
            target_id=user_id,
            target_name=name,
            details={"rules_evaluated": random.randint(5, 25), "violations_found": random.randint(0, 5)},
            success=True,
        )
        count += 1

    for i in range(6):
        user_id, name, _, _ = random.choice(USERS)
        severity = random.choice(["CRITICAL", "HIGH", "MEDIUM", "LOW"])
        audit_logger.log(
            action=AuditAction.VIOLATION_DETECTED,
            actor_user_id="SYSTEM",
            actor_username="Risk Engine",
            actor_type="system",
            target_type="User",
            target_id=user_id,
            target_name=name,
            details={
                "rule_id": f"SOD-{random.randint(1,50):03d}",
                "rule_name": random.choice([
                    "Finance Posting vs Approval",
                    "Vendor Master vs Payment",
                    "Purchase Order vs Goods Receipt",
                    "Payroll Processing vs HR Admin",
                ]),
                "severity": severity,
            },
            success=True,
            compliance_relevant=True,
            compliance_tags=["SOX", "SoD"],
        )
        count += 1

    # Firefighter events
    for i in range(4):
        user_id, name, _, _ = random.choice(USERS[:5])
        ff_id = random.choice(FF_IDS)
        session_id = f"FFS-{datetime.utcnow().strftime('%y%m%d%H%M')}-{random.randint(100,999):03X}"
        req_id = f"FFR-{datetime.utcnow().strftime('%y%m%d%H%M')}-{random.randint(100,999):03X}"

        audit_logger.log(
            action=AuditAction.FF_REQUEST_SUBMITTED,
            actor_user_id=user_id,
            actor_username=name,
            target_type="firefighter",
            target_id=ff_id,
            details={"request_id": req_id, "reason": random.choice(FF_REASONS)[0]},
            success=True,
            compliance_relevant=True,
            compliance_tags=["SOX", "EAM"],
        )
        count += 1

        audit_logger.log(
            action=AuditAction.FF_REQUEST_APPROVED,
            actor_user_id=random.choice(APPROVERS),
            actor_username="Approver",
            target_type="firefighter",
            target_id=req_id,
            details={"firefighter_id": ff_id, "approved_for": user_id},
            success=True,
            compliance_relevant=True,
            compliance_tags=["SOX", "EAM"],
        )
        count += 1

        audit_logger.log(
            action=AuditAction.FF_SESSION_STARTED,
            actor_user_id=user_id,
            actor_username=name,
            target_type="firefighter_session",
            target_id=session_id,
            details={"firefighter_id": ff_id, "request_id": req_id},
            success=True,
            compliance_relevant=True,
            compliance_tags=["SOX", "EAM"],
        )
        count += 1

        # Some activities
        for j in range(random.randint(2, 5)):
            act_type, act_details, sensitive = random.choice(FF_ACTIVITIES)
            audit_logger.log(
                action=AuditAction.FF_ACTIVITY_LOGGED,
                actor_user_id=user_id,
                actor_username=name,
                target_type="firefighter_session",
                target_id=session_id,
                details={"action_type": act_type, **act_details, "is_sensitive": sensitive},
                success=True,
                compliance_relevant=sensitive,
                compliance_tags=["EAM"] if sensitive else None,
            )
            count += 1

        audit_logger.log(
            action=AuditAction.FF_SESSION_ENDED,
            actor_user_id=user_id,
            actor_username=name,
            target_type="firefighter_session",
            target_id=session_id,
            details={"firefighter_id": ff_id, "reason": "Normal completion"},
            success=True,
            compliance_relevant=True,
            compliance_tags=["SOX", "EAM"],
        )
        count += 1

    # One revoked session
    audit_logger.log(
        action=AuditAction.FF_SESSION_REVOKED,
        actor_user_id="SEC_OFFICER",
        actor_username="Security Officer",
        target_type="firefighter_session",
        target_id="FFS-REVOKED-001",
        details={"reason": "Security policy violation detected", "firefighter_id": "FF_EMERGENCY_01"},
        success=True,
        compliance_relevant=True,
        compliance_tags=["SOX", "EAM", "SECURITY"],
    )
    count += 1

    # One rejected request
    audit_logger.log(
        action=AuditAction.FF_REQUEST_REJECTED,
        actor_user_id="COMPLIANCE_MGR",
        actor_username="Compliance Manager",
        target_type="firefighter",
        target_id="FFR-REJECTED-001",
        details={"reason": "Insufficient justification", "requester": "KTAYLOR"},
        success=True,
        compliance_relevant=True,
        compliance_tags=["EAM"],
    )
    count += 1

    # Approver events
    for i, approver in enumerate(APPROVERS[:3]):
        audit_logger.log(
            action=AuditAction.APPROVER_CREATED,
            actor_user_id="ADMIN",
            actor_username="System Admin",
            target_type="Approver",
            target_id=approver,
            target_name=approver.replace("_", " ").title(),
            details={"approver_type": random.choice(["LINE_MANAGER", "SECURITY_OFFICER", "COMPLIANCE_MANAGER"])},
            success=True,
            compliance_relevant=True,
            compliance_tags=["GRC"],
        )
        count += 1

    audit_logger.log(
        action=AuditAction.APPROVER_OOO_SET,
        actor_user_id="ADMIN",
        actor_username="System Admin",
        target_type="Approver",
        target_id="LINE_MGR_01",
        target_name="Line Manager 01",
        details={
            "ooo_until": (datetime.utcnow() + timedelta(days=5)).isoformat(),
            "delegate_id": "IT_MANAGER",
            "reason": "Annual leave",
            "approved_by": "ADMIN",
        },
        success=True,
        compliance_relevant=True,
        compliance_tags=["GRC"],
    )
    count += 1

    # System events
    audit_logger.log(
        action=AuditAction.SYSTEM_CONFIG_CHANGED,
        actor_user_id="ADMIN",
        actor_username="System Admin",
        actor_type="system",
        target_type="config",
        target_id="password_policy",
        details={"setting": "min_password_length"},
        old_values={"min_password_length": 8},
        new_values={"min_password_length": 12},
        success=True,
        compliance_relevant=True,
        compliance_tags=["SOX", "SECURITY"],
    )
    count += 1

    for i in range(2):
        audit_logger.log(
            action=AuditAction.RULE_CREATED,
            actor_user_id="ADMIN",
            actor_username="System Admin",
            target_type="Rule",
            target_id=f"SOD-CUSTOM-{i+1:03d}",
            target_name=f"Custom SoD Rule {i+1}",
            success=True,
            compliance_relevant=True,
            compliance_tags=["SOX", "SoD"],
        )
        count += 1

    audit_logger.log(
        action=AuditAction.REPORT_GENERATED,
        actor_user_id="AWHITE",
        actor_username="Ashley White",
        target_type="Report",
        target_id="RPT-SOD-001",
        target_name="SoD Violations Summary",
        details={"format": "pdf", "period": "30d"},
        success=True,
    )
    count += 1

    audit_logger.log(
        action=AuditAction.DATA_EXPORT,
        actor_user_id="AWHITE",
        actor_username="Ashley White",
        target_type="AuditLog",
        target_id="export-2024-02",
        details={"format": "csv", "records": 500},
        success=True,
        compliance_relevant=True,
        compliance_tags=["GRC"],
    )
    count += 1

    # A few failed actions
    audit_logger.log(
        action=AuditAction.USER_MODIFIED,
        actor_user_id="SLEE",
        actor_username="Sarah Lee",
        target_type="User",
        target_id="ADMIN",
        target_name="System Admin",
        success=False,
        error_message="Insufficient permissions: MANAGE_USERS required",
    )
    count += 1

    audit_logger.log(
        action=AuditAction.ROLE_ASSIGNED,
        actor_user_id="KTAYLOR",
        actor_username="Kevin Taylor",
        target_type="User",
        target_id="KTAYLOR",
        details={"role_id": "Z_SECURITY_ADMIN"},
        success=False,
        error_message="Self-assignment not permitted for privileged roles",
    )
    count += 1

    print(f"  Created {count} audit log entries")
    return count


# ===========================================================================
# Seed Access Requests
# ===========================================================================

async def seed_access_requests(request_manager):
    """Create access requests in various states."""
    print("\n--- Seeding Access Requests ---")
    count = 0

    # Draft requests
    for i in range(2):
        user = USERS[i]
        target = USERS[i + 5]
        req = await request_manager.create_request(
            tenant_id="tenant_default",
            requester_user_id=user[0],
            requester_name=user[1],
            requester_email=user[2],
            target_user_id=target[0],
            target_user_name=target[1],
            requested_roles=[random.choice(SAP_ROLES)],
            business_justification=random.choice(JUSTIFICATIONS),
            request_type=RequestType.NEW_ACCESS,
        )
        count += 1
        print(f"  Draft: {req.request_id}")

    # Submitted → Pending Approval requests
    for i in range(4):
        user = USERS[i + 2]
        target = USERS[i + 7]
        roles = random.sample(SAP_ROLES, random.randint(1, 3))
        req = await request_manager.create_request(
            tenant_id="tenant_default",
            requester_user_id=user[0],
            requester_name=user[1],
            requester_email=user[2],
            target_user_id=target[0],
            target_user_name=target[1],
            requested_roles=roles,
            business_justification=random.choice(JUSTIFICATIONS),
            request_type=random.choice([RequestType.NEW_ACCESS, RequestType.MODIFY_ACCESS]),
        )
        await request_manager.submit_request(req.request_id)
        count += 1
        print(f"  Submitted: {req.request_id} (roles: {roles})")

    # Approved requests
    for i in range(3):
        user = USERS[i + 6]
        target = USERS[i + 10]
        req = await request_manager.create_request(
            tenant_id="tenant_default",
            requester_user_id=user[0],
            requester_name=user[1],
            requester_email=user[2],
            target_user_id=target[0],
            target_user_name=target[1],
            requested_roles=[random.choice(SAP_ROLES)],
            business_justification=random.choice(JUSTIFICATIONS),
            request_type=RequestType.NEW_ACCESS,
        )
        submitted = await request_manager.submit_request(req.request_id)
        # Approve the first step — use the step's actual approver_ids
        if submitted.approval_steps:
            step = submitted.approval_steps[0]
            actor = step.approver_ids[0] if step.approver_ids else "ADMIN"
            await request_manager.process_approval(
                request_id=req.request_id,
                step_id=step.step_id,
                action=ApprovalAction.APPROVE,
                actor_id=actor,
                comments="Approved — business justification verified",
            )
        count += 1
        print(f"  Approved: {req.request_id}")

    # Rejected requests
    for i in range(2):
        user = USERS[i + 9]
        target = USERS[i + 12]
        req = await request_manager.create_request(
            tenant_id="tenant_default",
            requester_user_id=user[0],
            requester_name=user[1],
            requester_email=user[2],
            target_user_id=target[0],
            target_user_name=target[1],
            requested_roles=random.sample(SAP_ROLES, 2),
            business_justification="Need access for basic job functions — low priority request",
            request_type=RequestType.NEW_ACCESS,
        )
        submitted = await request_manager.submit_request(req.request_id)
        if submitted.approval_steps:
            step = submitted.approval_steps[0]
            actor = step.approver_ids[0] if step.approver_ids else "ADMIN"
            await request_manager.process_approval(
                request_id=req.request_id,
                step_id=step.step_id,
                action=ApprovalAction.REJECT,
                actor_id=actor,
                comments="Insufficient justification — SoD conflict detected",
            )
        count += 1
        print(f"  Rejected: {req.request_id}")

    # Temporary access request
    req = await request_manager.create_request(
        tenant_id="tenant_default",
        requester_user_id="JSMITH",
        requester_name="John Smith",
        requester_email="john.smith@company.com",
        target_user_id="MBROWN",
        target_user_name="Mary Brown",
        requested_roles=["Z_AUDITOR"],
        business_justification="SOX compliance testing — temporary auditor access for Q4 review",
        request_type=RequestType.TEMPORARY_ACCESS,
        is_temporary=True,
        end_date=datetime.now() + timedelta(days=30),
    )
    await request_manager.submit_request(req.request_id)
    count += 1
    print(f"  Temporary: {req.request_id}")

    print(f"  Created {count} access requests")
    return count


# ===========================================================================
# Seed Firefighter Sessions
# ===========================================================================

async def seed_firefighter_sessions(ff_manager, sap_connector):
    """Create firefighter requests and sessions."""
    print("\n--- Seeding Firefighter Sessions ---")
    count = 0

    for i, (reason_text, reason_code, priority) in enumerate(FF_REASONS[:6]):
        user = USERS[i % len(USERS)]
        ff_id = FF_IDS[i % len(FF_IDS)]

        try:
            request = await ff_manager.submit_request(
                requester_user_id=user[0],
                requester_name=user[1],
                requester_email=user[2],
                target_system="SAP_PRD",
                firefighter_id=ff_id,
                reason_code=reason_code,
                reason=reason_text,
                business_justification=f"Business critical: {reason_text}",
                planned_actions=["Review system logs", "Execute corrective transaction"],
                duration=timedelta(hours=random.choice([1, 2, 4])),
                priority=priority,
                ticket_reference=f"INC{random.randint(1000000, 9999999)}",
            )
            count += 1
            print(f"  Request: {request.request_id} ({reason_code.value})")

            # Approve most of them
            if i < 5:
                # Use the actual resolved approver from the request
                approver = request.approvers[0] if request.approvers else "ff.owner@company.com"
                session = await ff_manager.approve_request(
                    request_id=request.request_id,
                    approver_id=approver,
                    comments="Approved — priority justified",
                )
                print(f"    Session: {session.session_id} (ACTIVE)")

                # Log activities for active sessions
                for j in range(random.randint(3, 8)):
                    act_type, act_details, sensitive = random.choice(FF_ACTIVITIES)
                    try:
                        await ff_manager.log_activity(
                            session_id=session.session_id,
                            action_type=act_type,
                            action_details=act_details,
                            client_ip=f"10.0.{random.randint(1,5)}.{random.randint(1,254)}",
                            is_sensitive=sensitive,
                        )
                    except Exception:
                        pass

                # End some sessions
                if i < 3:
                    try:
                        await ff_manager.end_session(
                            session_id=session.session_id,
                            ended_by=user[0],
                            reason="Task completed successfully",
                        )
                        print(f"    Ended: {session.session_id} (COMPLETED)")
                        # Re-unlock the FF ID for next request
                        sap_connector.mock_users[ff_id]['lock_status'] = 0
                        if ff_id in ff_manager.active_sessions_by_ff:
                            del ff_manager.active_sessions_by_ff[ff_id]
                    except Exception as e:
                        print(f"    End failed: {e}")

                # Revoke one
                if i == 3:
                    try:
                        await ff_manager.revoke_session(
                            session_id=session.session_id,
                            revoked_by="SEC_OFFICER",
                            reason="Security policy violation — restricted TCode executed",
                        )
                        print(f"    Revoked: {session.session_id}")
                        sap_connector.mock_users[ff_id]['lock_status'] = 0
                        if ff_id in ff_manager.active_sessions_by_ff:
                            del ff_manager.active_sessions_by_ff[ff_id]
                    except Exception as e:
                        print(f"    Revoke failed: {e}")

            else:
                # Reject the last one
                try:
                    approver = request.approvers[0] if request.approvers else "ff.owner@company.com"
                    await ff_manager.reject_request(
                        request_id=request.request_id,
                        approver_id=approver,
                        reason="No valid ticket reference — change management policy requires approved CR",
                    )
                    print(f"    Rejected: {request.request_id}")
                except Exception as e:
                    print(f"    Reject failed: {e}")

        except Exception as e:
            print(f"  Error creating FF request: {e}")

    print(f"  Created {count} firefighter requests")
    return count


# ===========================================================================
# Seed Risk Evaluations
# ===========================================================================

def seed_risk_evaluations(rule_engine):
    """Run risk analysis on sample users to generate violations."""
    print("\n--- Seeding Risk Evaluations ---")

    # Users with conflicting entitlements (SoD violations)
    test_users = [
        UserAccess(
            user_id="JSMITH", username="JSMITH", full_name="John Smith",
            department="Finance",
            entitlements=[
                Entitlement(auth_object="S_TCODE", field="TCD", value="FB01"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="F110"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="FK01"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="MIRO"),
            ],
            roles=["Z_AP_CLERK", "Z_GL_ACCOUNTANT"],
        ),
        UserAccess(
            user_id="MBROWN", username="MBROWN", full_name="Mary Brown",
            department="Procurement",
            entitlements=[
                Entitlement(auth_object="S_TCODE", field="TCD", value="ME21N"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="MIGO"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="MIRO"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="ME22N"),
            ],
            roles=["Z_PURCHASER", "Z_BUYER"],
        ),
        UserAccess(
            user_id="DWILSON", username="DWILSON", full_name="David Wilson",
            department="IT Operations",
            entitlements=[
                Entitlement(auth_object="S_TCODE", field="TCD", value="SU01"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="PFCG"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="SE16"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="SM37"),
                Entitlement(auth_object="S_DEVELOP", field="ACTVT", value="01"),
            ],
            roles=["Z_IT_ADMIN", "Z_SECURITY_ADMIN"],
        ),
        UserAccess(
            user_id="RGARCIA", username="RGARCIA", full_name="Robert Garcia",
            department="Finance",
            entitlements=[
                Entitlement(auth_object="S_TCODE", field="TCD", value="FB01"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="F-28"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="FBL5N"),
            ],
            roles=["Z_AP_CLERK", "Z_AR_CLERK"],
        ),
        UserAccess(
            user_id="LJONES", username="LJONES", full_name="Lisa Jones",
            department="Human Resources",
            entitlements=[
                Entitlement(auth_object="S_TCODE", field="TCD", value="PA20"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="PA30"),
                Entitlement(auth_object="S_TCODE", field="TCD", value="PC00_M99_CALC"),
            ],
            roles=["Z_HR_ADMIN"],
        ),
    ]

    total_violations = 0
    results = rule_engine.evaluate_batch(test_users)
    for user_id, violations in results.items():
        print(f"  {user_id}: {len(violations)} violations")
        total_violations += len(violations)

    stats = rule_engine.get_statistics()
    print(f"  Total rules: {stats.get('rules_loaded', 0)}")
    print(f"  Total evaluations: {stats.get('evaluations_performed', 0)}")
    print(f"  Total violations: {stats.get('violations_found', 0)}")
    return total_violations


# ===========================================================================
# Main
# ===========================================================================

def seed_db_users():
    """Seed DB user accounts with bcrypt passwords for real authentication."""
    print("\n--- Seeding DB Users ---")
    from passlib.context import CryptContext
    from db.models.user import User

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    default_password = os.getenv("SEED_DEFAULT_PASSWORD", "")
    if not default_password:
        import secrets as _secrets
        default_password = _secrets.token_urlsafe(16)
        print(f"  [!] No SEED_DEFAULT_PASSWORD set — generated: {default_password}")
        print(f"  [!] CHANGE THIS PASSWORD after first login!")

    # Admin accounts + regular users
    accounts = [
        ("admin", "Admin User", "admin@governexplus.com", "IT", "admin"),
        ("security_admin", "Security Admin", "security@governexplus.com", "IT Security", "security_admin"),
        ("manager", "Manager User", "manager@governexplus.com", "Operations", "manager"),
        ("auditor", "Auditor", "auditor@governexplus.com", "Internal Audit", "auditor"),
    ]
    # Add USERS list from config
    for user_id, name, email, dept in USERS:
        accounts.append((user_id, name, email, dept, "end_user"))

    with db_manager.session_scope() as session:
        created = 0
        for username, full_name, email, dept, user_type in accounts:
            exists = session.query(User).filter_by(
                tenant_id=TENANT, username=username
            ).first()
            if exists:
                continue

            user = User(
                tenant_id=TENANT,
                user_id=username,
                username=username,
                email=email,
                full_name=full_name,
                department=dept,
                user_type=user_type,
                status="active",
                password_hash=pwd_ctx.hash(default_password),
            )
            session.add(user)
            created += 1

        session.commit()
        print(f"  Created {created} users (password: {default_password})")


async def main():
    print("=" * 60)
    print("  Governex+ Comprehensive Seed Script")
    print("=" * 60)

    # Init DB
    db_manager.init()
    db_manager.create_tables()

    # Check --clear flag
    if "--clear" in sys.argv:
        print("\n[!] Clearing existing audit logs...")
        with db_manager.session_scope() as session:
            session.query(AuditLog).delete()
            session.commit()
        print("  Cleared.")

    # Seed DB users with bcrypt passwords
    seed_db_users()

    # Initialize managers
    rule_engine = RuleEngine()
    _seed_session = db_manager.SessionLocal()
    request_manager = AccessRequestManager(db=_seed_session, rule_engine=rule_engine)

    mock_config = ConnectionConfig(
        name="SAP_DEV",
        connection_type=ConnectionType.RFC,
        host="mock.sap.local",
        sap_client="100"
    )
    sap_connector = SAPMockConnector(mock_config)
    sap_connector.connect()
    ff_manager = FirefighterManager(sap_connector=sap_connector)

    # Register firefighter IDs in mock connector and unlock them
    for ff_id in FF_IDS:
        if ff_id not in sap_connector.mock_users:
            sap_connector.mock_users[ff_id] = {
                'user_id': ff_id,
                'username': ff_id,
                'full_name': f'Firefighter Account {ff_id}',
                'email': 'firefighter@company.com',
                'department': 'IT',
                'function': 'Emergency Access',
                'user_type': 'S',
                'cost_center': 'CC3000',
                'company_code': '1000',
                'roles': ['Z_FIREFIGHTER_FULL'],
                'profiles': ['SAP_ALL'],
                'valid_from': '20200101',
                'valid_to': '99991231',
                'last_login': '00000000',
                'lock_status': 64,  # Locked — will be unlocked by manager on approve
            }
        # Ensure unlocked for initial availability check
        sap_connector.mock_users[ff_id]['lock_status'] = 0

    # Seed all modules
    audit_count = seed_audit_logs()
    ar_count = await seed_access_requests(request_manager)
    ff_count = await seed_firefighter_sessions(ff_manager, sap_connector)
    risk_violations = seed_risk_evaluations(rule_engine)

    print("\n" + "=" * 60)
    print("  Seed Complete!")
    print("=" * 60)
    print(f"  Audit Logs:       {audit_count} entries")
    print(f"  Access Requests:  {ar_count} requests")
    print(f"  FF Sessions:      {ff_count} requests/sessions")
    print(f"  Risk Violations:  {risk_violations} violations")
    print("=" * 60)

    # Return managers for UAT testing
    return request_manager, ff_manager, rule_engine


if __name__ == "__main__":
    asyncio.run(main())
