"""
Template Library Day-One Seeder
================================
Seeds all global template items on startup.
Idempotent: skips items whose item_code already exists.
Covers: SoD rules, mitigations, workflows, risk scenarios, controls,
        certification templates, JML policies, BCM templates, surveys,
        notification templates, report definitions.
"""

import uuid
import hashlib
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from db.models.template_library import TemplatePack, TemplatePackVersion, TemplateItem

logger = logging.getLogger(__name__)


def _checksum(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _item(code, name, desc, module, item_type, payload, frameworks=None, industries=None, severity=None, pack_id=None):
    return {
        "item_code": code, "name": name, "description": desc,
        "module": module, "item_type": item_type, "payload": payload,
        "compliance_frameworks": frameworks or [], "industry_tags": industries or [],
        "severity": severity, "pack_id": pack_id,
    }


# ---------------------------------------------------------------------------
# TEMPLATE DEFINITIONS
# ---------------------------------------------------------------------------

SOD_RULES = [
    _item("SOD-FI-001", "Create Vendor + Post Invoice (AP Fraud)", "Segregates vendor creation from invoice posting to prevent fictitious vendor fraud.",
          "ara", "sod_rule",
          {"function_a": {"name": "Create Vendor", "tcodes": ["XK01", "FK01"], "auth_objects": ["F_KNA1_GRP", "F_LFA1_GRP"]},
           "function_b": {"name": "Post Vendor Invoice", "tcodes": ["FB60", "MIRO"], "auth_objects": ["F_BKPF_BUK", "F_BKPF_KOA"]},
           "risk_type": "fraud", "remediation": "Remove XK01/FK01 from invoice posting roles"},
          ["SOX", "COSO"], ["all"], "critical"),

    _item("SOD-FI-002", "Create Customer + Post AR Payment", "Prevents ghost customer setup with payment posting.",
          "ara", "sod_rule",
          {"function_a": {"name": "Create Customer", "tcodes": ["XD01", "FD01"], "auth_objects": ["F_KNA1_GRP"]},
           "function_b": {"name": "Post AR Payment", "tcodes": ["F-28", "F-29"], "auth_objects": ["F_BKPF_BUK"]},
           "risk_type": "fraud", "remediation": "Separate customer master team from AR collections"},
          ["SOX", "COSO"], ["all"], "critical"),

    _item("SOD-FI-003", "Post Journal Entry + Post Reversals", "Limits ability to self-reverse fraudulent postings.",
          "ara", "sod_rule",
          {"function_a": {"name": "Post Journal Entry", "tcodes": ["FB50", "F-02"], "auth_objects": ["F_BKPF_BUK"]},
           "function_b": {"name": "Reverse Documents", "tcodes": ["FB08", "FBRA"], "auth_objects": ["F_BKPF_BUK"]},
           "risk_type": "fraud", "remediation": "Require supervisor approval for reversals"},
          ["SOX"], ["all"], "high"),

    _item("SOD-FI-004", "Maintain Bank Master + Execute Payment Run", "Bank account manipulation + payment execution.",
          "ara", "sod_rule",
          {"function_a": {"name": "Maintain Bank Master", "tcodes": ["FI12", "FBZP"], "auth_objects": ["F_T012_BUK"]},
           "function_b": {"name": "Execute Payment Run", "tcodes": ["F110"], "auth_objects": ["F_PAYR_BUK"]},
           "risk_type": "fraud", "remediation": "Dual control on bank master changes"},
          ["SOX", "PCI-DSS"], ["all"], "critical"),

    _item("SOD-MM-001", "Create Purchase Order + Approve Purchase Order", "Self-approval of purchase orders.",
          "ara", "sod_rule",
          {"function_a": {"name": "Create Purchase Order", "tcodes": ["ME21N", "ME21"], "auth_objects": ["M_BEST_BSA"]},
           "function_b": {"name": "Approve Purchase Order", "tcodes": ["ME29N", "ME28"], "auth_objects": ["M_BEST_WFB"]},
           "risk_type": "fraud", "remediation": "Use workflow-based approval with different approver"},
          ["SOX", "COSO"], ["all"], "critical"),

    _item("SOD-MM-002", "Create Purchase Requisition + Convert to PO", "Requisitioner converts own requests.",
          "ara", "sod_rule",
          {"function_a": {"name": "Create Purchase Requisition", "tcodes": ["ME51N"], "auth_objects": ["M_BANF_BSA"]},
           "function_b": {"name": "Convert PR to PO", "tcodes": ["ME58", "ME59N"], "auth_objects": ["M_BEST_BSA"]},
           "risk_type": "control_bypass", "remediation": "Separate purchasing team from requisitioners"},
          ["SOX"], ["all"], "high"),

    _item("SOD-HR-001", "Maintain Payroll Master + Run Payroll", "Ghost employee creation with payroll execution.",
          "ara", "sod_rule",
          {"function_a": {"name": "Maintain Employee Master", "tcodes": ["PA30", "PA40"], "auth_objects": ["P_ORGIN", "P_PERNR"]},
           "function_b": {"name": "Run Payroll", "tcodes": ["PC00_M01_CALC", "PU01"], "auth_objects": ["P_PYEVRUN"]},
           "risk_type": "fraud", "remediation": "HR master team must be separate from payroll execution"},
          ["SOX", "GDPR"], ["all"], "critical"),

    _item("SOD-HR-002", "Maintain Salary Data + Release Payment", "Self-modification of own salary or payment.",
          "ara", "sod_rule",
          {"function_a": {"name": "Maintain Salary/Wage Type", "tcodes": ["PA30"], "auth_objects": ["P_ORGIN"]},
           "function_b": {"name": "Release Payroll for Payment", "tcodes": ["PCP0"], "auth_objects": ["P_PYEVRUN"]},
           "risk_type": "fraud", "remediation": "4-eyes principle on salary changes"},
          ["SOX"], ["all"], "critical"),

    _item("SOD-SD-001", "Create Sales Order + Approve Credit Limit Exception", "Sales rep bypasses credit checks.",
          "ara", "sod_rule",
          {"function_a": {"name": "Create Sales Order", "tcodes": ["VA01", "VA02"], "auth_objects": ["V_VBAK_AAT"]},
           "function_b": {"name": "Override Credit Limit", "tcodes": ["VKM1", "VKM3"], "auth_objects": ["V_VBAK_VKO"]},
           "risk_type": "financial_exposure", "remediation": "Credit exception approval by credit manager only"},
          ["SOX", "COSO"], ["all"], "high"),

    _item("SOD-BASIS-001", "Administer Users + Assign Roles", "Segregates user admin from role assignment.",
          "ara", "sod_rule",
          {"function_a": {"name": "Create/Modify Users", "tcodes": ["SU01", "SU10"], "auth_objects": ["S_USR_ADM"]},
           "function_b": {"name": "Assign Roles to Users", "tcodes": ["SU01D"], "auth_objects": ["S_USER_AGR"]},
           "risk_type": "access_control", "remediation": "Separate user admin from authorization admin"},
          ["SOX", "ISO27001"], ["all"], "high"),

    _item("SOD-BASIS-002", "Debug Programs + Post to Production", "Developer can push untested code.",
          "ara", "sod_rule",
          {"function_a": {"name": "Debug/Replace System", "tcodes": ["SA38", "SE38"], "auth_objects": ["S_DEVELOP"]},
           "function_b": {"name": "Release Transport to Production", "tcodes": ["SE10", "STMS"], "auth_objects": ["S_TRANSPRT"]},
           "risk_type": "change_management", "remediation": "Developers must not have production transport release"},
          ["SOX", "ITGC"], ["all"], "critical"),

    _item("SOD-FI-005", "Approve Vendor + Approve Payment", "Full payment fraud cycle without second check.",
          "ara", "sod_rule",
          {"function_a": {"name": "Approve Vendor for Payment", "tcodes": ["XK02", "FK02"], "auth_objects": ["F_LFA1_GRP"]},
           "function_b": {"name": "Approve Outgoing Payment", "tcodes": ["F-53", "F110"], "auth_objects": ["F_BKPF_BUK"]},
           "risk_type": "fraud", "remediation": "Second approver required for payment runs"},
          ["SOX", "COSO"], ["all"], "critical"),
]

MITIGATIONS = [
    _item("MIT-AP-001", "Vendor Master Change Log Review", "Monthly review of vendor master changes by AP supervisor.",
          "ara", "mitigation",
          {"control_type": "detective", "frequency": "monthly",
           "procedure": "AP supervisor reviews VK11/MK14 change logs and confirms no unauthorized changes",
           "evidence": "Signed review checklist", "owner_role": "AP Supervisor",
           "related_sod_rules": ["SOD-FI-001", "SOD-FI-005"]},
          ["SOX"], ["all"]),

    _item("MIT-AP-002", "Dual Authorization for Payment Runs", "Treasurer countersigns all payment batch proposals before release.",
          "ara", "mitigation",
          {"control_type": "preventive", "frequency": "per_payment_run",
           "procedure": "Payment proposal reviewed by Treasurer in F110 before execution",
           "evidence": "Payment proposal printout with Treasurer signature",
           "owner_role": "Treasurer", "related_sod_rules": ["SOD-FI-004"]},
          ["SOX", "PCI-DSS"], ["all"]),

    _item("MIT-HR-001", "Payroll Variance Report Review", "HR manager reviews payroll variance report every pay cycle.",
          "ara", "mitigation",
          {"control_type": "detective", "frequency": "per_payroll_run",
           "procedure": "HR manager reviews PC00_M01_CALC output for anomalies > 10% vs prior period",
           "evidence": "Variance report with manager approval",
           "owner_role": "HR Manager", "related_sod_rules": ["SOD-HR-001", "SOD-HR-002"]},
          ["SOX"], ["all"]),

    _item("MIT-IT-001", "Change Management Board Review", "All transport releases require Change Advisory Board approval.",
          "ara", "mitigation",
          {"control_type": "preventive", "frequency": "per_change",
           "procedure": "CRQ ticket with CAB approval required before STMS transport release to production",
           "evidence": "ServiceNow CRQ with CAB approval record",
           "owner_role": "Change Manager", "related_sod_rules": ["SOD-BASIS-002"]},
          ["SOX", "ITGC", "ISO27001"], ["all"]),
]

WORKFLOWS = [
    _item("WF-ARM-001", "Standard Access Request — Single Approver", "End-user requests role, line manager approves, provisioned automatically.",
          "arm", "workflow",
          {"steps": [
              {"step": 1, "actor": "requester", "action": "submit_request", "form": "role_selection"},
              {"step": 2, "actor": "line_manager", "action": "approve_or_reject", "sla_hours": 48},
              {"step": 3, "actor": "system", "action": "risk_check", "engine": "ara"},
              {"step": 4, "actor": "system", "action": "provision", "connector": "sap"},
          ], "escalation_hours": 72, "auto_provision": True},
          ["SOX"], ["all"]),

    _item("WF-ARM-002", "High-Risk Access Request — Dual Approval", "Sensitive roles require line manager + security admin approval with risk check.",
          "arm", "workflow",
          {"steps": [
              {"step": 1, "actor": "requester", "action": "submit_request", "form": "role_selection"},
              {"step": 2, "actor": "line_manager", "action": "approve_or_reject", "sla_hours": 24},
              {"step": 3, "actor": "system", "action": "risk_check", "engine": "ara", "block_on_critical": True},
              {"step": 4, "actor": "security_admin", "action": "approve_or_reject", "sla_hours": 24},
              {"step": 5, "actor": "system", "action": "provision", "connector": "sap"},
          ], "escalation_hours": 48, "auto_provision": True},
          ["SOX", "ISO27001"], ["all"]),

    _item("WF-FF-001", "Privileged Access (Firefighter) Standard", "FF request with controller pre-approval and automatic log review.",
          "privileged_access", "workflow",
          {"steps": [
              {"step": 1, "actor": "firefighter", "action": "submit_ff_request", "requires": ["reason", "duration_hours", "system"]},
              {"step": 2, "actor": "ff_controller", "action": "approve_or_reject", "sla_hours": 2},
              {"step": 3, "actor": "system", "action": "assign_ff_id", "duration_hours": "requested"},
              {"step": 4, "actor": "system", "action": "log_all_activity", "real_time": True},
              {"step": 5, "actor": "ff_controller", "action": "review_log", "sla_hours": 24, "trigger": "ff_end"},
          ], "max_duration_hours": 8},
          ["SOX", "ITGC"], ["all"]),

    _item("WF-CERT-001", "Quarterly User Access Review", "Certification campaign for all users, role owners as certifiers.",
          "certification", "workflow",
          {"campaign_type": "user_access_review",
           "certifier": "role_owner",
           "frequency": "quarterly",
           "steps": [
               {"step": 1, "actor": "system", "action": "generate_campaign", "scope": "all_active_users"},
               {"step": 2, "actor": "role_owner", "action": "certify_or_revoke", "sla_days": 14},
               {"step": 3, "actor": "security_admin", "action": "review_revocations", "sla_days": 5},
               {"step": 4, "actor": "system", "action": "deprovision_revoked"},
               {"step": 5, "actor": "system", "action": "close_campaign_report"},
           ]},
          ["SOX", "ISO27001"], ["all"]),

    _item("WF-JML-001", "Joiner — New Employee Onboarding", "Triggered by HR event; provisions birthright roles within 1 business day.",
          "jml", "workflow",
          {"trigger": "hr_hire_event",
           "steps": [
               {"step": 1, "actor": "system", "action": "receive_hr_event", "source": "workday_or_successfactors"},
               {"step": 2, "actor": "system", "action": "match_jml_policy", "by": ["org_unit", "position"]},
               {"step": 3, "actor": "line_manager", "action": "confirm_birthright_roles", "sla_hours": 8},
               {"step": 4, "actor": "system", "action": "provision_birthright_roles"},
               {"step": 5, "actor": "system", "action": "send_welcome_notification"},
           ]},
          ["SOX"], ["all"]),

    _item("WF-JML-002", "Leaver — Employee Off-boarding", "Full revocation within 24 hours of termination date.",
          "jml", "workflow",
          {"trigger": "hr_termination_event",
           "steps": [
               {"step": 1, "actor": "system", "action": "receive_hr_event", "source": "workday_or_successfactors"},
               {"step": 2, "actor": "system", "action": "lock_account", "immediate": True},
               {"step": 3, "actor": "system", "action": "revoke_all_roles", "connector": "sap"},
               {"step": 4, "actor": "system", "action": "close_open_requests"},
               {"step": 5, "actor": "line_manager", "action": "confirm_offboarding", "sla_hours": 24},
               {"step": 6, "actor": "system", "action": "archive_user_record"},
           ]},
          ["SOX", "GDPR"], ["all"]),
]

RISK_SCENARIOS = [
    _item("RS-FI-001", "Accounts Payable Fraud via Ghost Vendor", "Risk of financial loss through fictitious vendor payments.",
          "risk_management", "risk_scenario",
          {"risk_category": "financial", "likelihood": "medium", "impact": "high",
           "inherent_risk_score": 16,
           "key_controls": ["SOD-FI-001", "MIT-AP-001"],
           "risk_indicators": ["unusual vendor bank account changes", "payments to new vendors > $10k"],
           "regulatory_refs": ["SOX 302", "SOX 404"]},
          ["SOX", "COSO"], ["all"], "high"),

    _item("RS-IT-001", "Unauthorized System Change — Production", "Developer deploys unauthorized code to production.",
          "risk_management", "risk_scenario",
          {"risk_category": "it_operations", "likelihood": "medium", "impact": "critical",
           "inherent_risk_score": 20,
           "key_controls": ["SOD-BASIS-002", "MIT-IT-001"],
           "risk_indicators": ["transports without CRQ", "off-hours STMS releases"],
           "regulatory_refs": ["SOX ITGCs", "ISO27001 A.14"]},
          ["SOX", "ISO27001", "ITGC"], ["all"], "critical"),

    _item("RS-HR-001", "Payroll Fraud — Ghost Employee", "Fictitious employees added for unauthorized payroll disbursement.",
          "risk_management", "risk_scenario",
          {"risk_category": "financial", "likelihood": "low", "impact": "high",
           "inherent_risk_score": 12,
           "key_controls": ["SOD-HR-001", "MIT-HR-001"],
           "risk_indicators": ["new employees with no manager", "payroll anomalies > 15%"],
           "regulatory_refs": ["SOX 302"]},
          ["SOX"], ["all"], "high"),
]

CONTROLS = [
    _item("CTRL-AUTH-001", "SAP Password Policy Enforcement", "Enforce minimum password complexity per profile parameter.",
          "compliance", "control",
          {"control_type": "preventive", "control_frequency": "continuous",
           "test_procedure": "Verify login/min_password_lng >= 8, login/password_max_idle_productive <= 180",
           "parameters": {"login/min_password_lng": 8, "login/password_uppercase": 1,
                          "login/password_digits": 1, "login/password_max_idle_productive": 180},
           "automated": True, "connector_check": "sap_profile_parameter"},
          ["SOX", "ISO27001", "PCI-DSS"], ["all"]),

    _item("CTRL-AUTH-002", "Account Lockout After Failed Logins", "Accounts locked after 5 failed attempts.",
          "compliance", "control",
          {"control_type": "preventive", "control_frequency": "continuous",
           "test_procedure": "Verify login/fails_to_session_end = 5 and login/failed_user_auto_unlock = 0",
           "parameters": {"login/fails_to_session_end": 5, "login/failed_user_auto_unlock": 0},
           "automated": True, "connector_check": "sap_profile_parameter"},
          ["SOX", "ISO27001", "PCI-DSS"], ["all"]),

    _item("CTRL-RFC-001", "Restrict RFC Destinations to Named Users", "All RFC destinations must use named user auth (not background user).",
          "compliance", "control",
          {"control_type": "preventive", "control_frequency": "continuous",
           "test_procedure": "Review SM59 RFC destinations; flag any using generic/service accounts",
           "automated": False, "review_frequency": "monthly"},
          ["SOX", "ISO27001"], ["all"]),

    _item("CTRL-AUDIT-001", "Security Audit Log Active", "SM19/RSECNOTE audit log enabled for critical events.",
          "compliance", "control",
          {"control_type": "detective", "control_frequency": "continuous",
           "test_procedure": "Verify SM19 profile is active with minimum: login failures, role changes, user locks",
           "automated": True, "connector_check": "sap_audit_log_status"},
          ["SOX", "ISO27001", "PCI-DSS"], ["all"]),
]

CERTIFICATION_TEMPLATES = [
    _item("CERT-SOX-001", "SOX Annual User Access Review", "Mandatory annual review of all SAP user access for SOX compliance.",
          "certification", "certification_template",
          {"campaign_name_template": "SOX UAR {year}",
           "scope": "all_active_sap_users",
           "certifier_type": "role_owner",
           "frequency": "annual",
           "duration_days": 30,
           "escalation_days": [7, 3, 1],
           "auto_revoke_no_response": False,
           "report_template": "SOX-UAR-FINAL"},
          ["SOX"], ["all"]),

    _item("CERT-PRIV-001", "Quarterly Privileged Access Review", "Review of all sensitive/privileged role assignments quarterly.",
          "certification", "certification_template",
          {"campaign_name_template": "Privileged Access Review Q{quarter} {year}",
           "scope": "privileged_roles_only",
           "certifier_type": "security_admin",
           "frequency": "quarterly",
           "duration_days": 14,
           "escalation_days": [5, 2],
           "auto_revoke_no_response": True,
           "report_template": "PRIV-ACCESS-REVIEW"},
          ["SOX", "ISO27001"], ["all"]),
]

BCM_TEMPLATES = [
    _item("BCM-BIA-001", "IT Critical System BIA Template", "Business Impact Analysis for core IT systems (SAP, payroll, ERP).",
          "bcm", "bia_template",
          {"sections": ["system_description", "business_processes_supported", "users_impacted",
                        "rto_rpo_targets", "financial_impact_per_hour", "regulatory_impact",
                        "dependencies", "recovery_sequence"],
           "rto_options_hours": [1, 4, 8, 24, 48, 72],
           "rpo_options_hours": [0, 1, 4, 8, 24]},
          ["ISO22301"], ["all"]),

    _item("BCM-PLAN-001", "IT Disaster Recovery Plan Template", "Standard DR plan for SAP and core business systems.",
          "bcm", "bcm_plan_template",
          {"plan_type": "disaster_recovery",
           "sections": ["scope_and_objectives", "rto_rpo", "recovery_team",
                        "incident_declaration_criteria", "recovery_procedures_step_by_step",
                        "communication_plan", "test_schedule", "plan_maintenance"],
           "review_frequency": "annual"},
          ["ISO22301", "NIST-SP800-34"], ["all"]),
]

SURVEYS = [
    _item("SURV-CTRL-001", "Control Self-Assessment (CSA) Survey", "Annual control effectiveness self-assessment for process owners.",
          "survey", "survey_template",
          {"questions": [
              {"id": "q1", "type": "rating_1_5", "text": "How effective is the segregation of duties in your process?"},
              {"id": "q2", "type": "rating_1_5", "text": "Are exception reports reviewed and actioned within SLA?"},
              {"id": "q3", "type": "yes_no", "text": "Have all access certifications been completed for your team?"},
              {"id": "q4", "type": "text", "text": "Describe any control weaknesses or gaps identified this period."},
              {"id": "q5", "type": "rating_1_5", "text": "Overall, how would you rate the control environment?"},
          ],
          "target_audience": "process_owners",
          "frequency": "annual"},
          ["SOX", "COSO"], ["all"]),

    _item("SURV-AUDIT-001", "Post-Audit Feedback Survey", "Collect auditee feedback on audit process quality.",
          "survey", "survey_template",
          {"questions": [
              {"id": "q1", "type": "rating_1_5", "text": "The audit team communicated clearly and professionally."},
              {"id": "q2", "type": "rating_1_5", "text": "The audit scope and objectives were well explained."},
              {"id": "q3", "type": "rating_1_5", "text": "Findings and recommendations were practical and fair."},
              {"id": "q4", "type": "text", "text": "What could be improved in the audit process?"},
          ],
          "target_audience": "auditees",
          "frequency": "per_audit"},
          [], ["all"]),
]

NOTIFICATION_TEMPLATES = [
    _item("NOTIF-ACCESS-001", "Access Request Submitted Confirmation", "Email sent to requester when access request is submitted.",
          "arm", "notification_template",
          {"channel": "email", "trigger": "access_request_submitted",
           "subject": "Your access request has been submitted — {{request_id}}",
           "body": "Dear {{requester_name}},\n\nYour access request ({{request_id}}) for role {{role_name}} has been submitted and is pending approval by {{approver_name}}.\n\nExpected response: {{sla_deadline}}\n\nGovernexPlus",
           "variables": ["request_id", "requester_name", "role_name", "approver_name", "sla_deadline"]},
          [], ["all"]),

    _item("NOTIF-ACCESS-002", "Access Request Approved", "Email notification when access request is approved.",
          "arm", "notification_template",
          {"channel": "email", "trigger": "access_request_approved",
           "subject": "Access Request Approved — {{request_id}}",
           "body": "Dear {{requester_name}},\n\nYour access request ({{request_id}}) for role {{role_name}} has been approved by {{approver_name}} and will be provisioned within {{provision_sla}}.\n\nGovernexPlus",
           "variables": ["request_id", "requester_name", "role_name", "approver_name", "provision_sla"]},
          [], ["all"]),

    _item("NOTIF-CERT-001", "Certification Campaign — Action Required", "Email sent to certifiers when campaign launches.",
          "certification", "notification_template",
          {"channel": "email", "trigger": "campaign_launched",
           "subject": "Action Required: Access Certification — {{campaign_name}}",
           "body": "Dear {{certifier_name}},\n\nYou have been assigned {{item_count}} items to certify in the {{campaign_name}} campaign.\n\nDeadline: {{deadline_date}}\n\nClick here to start: {{review_url}}\n\nGovernexPlus",
           "variables": ["certifier_name", "item_count", "campaign_name", "deadline_date", "review_url"]},
          [], ["all"]),

    _item("NOTIF-FF-001", "Firefighter Access Granted", "Notification sent when FF access is provisioned.",
          "privileged_access", "notification_template",
          {"channel": "email", "trigger": "ff_access_granted",
           "subject": "Privileged Access Active — {{ff_id}} — Expires {{expiry}}",
           "body": "This confirms that Firefighter ID {{ff_id}} has been activated for {{user_name}} on system {{system_id}}.\n\nAll activity is being logged and will be reviewed by {{controller_name}} after session end.\n\nExpiry: {{expiry}}\n\nGovernexPlus",
           "variables": ["ff_id", "user_name", "system_id", "controller_name", "expiry"]},
          [], ["all"]),
]

REPORT_TEMPLATES = [
    _item("RPT-ARA-001", "SoD Violation Summary Report", "Executive summary of SoD violations by severity and business unit.",
          "ara", "report_template",
          {"report_format": "pdf_and_excel",
           "sections": ["executive_summary", "violations_by_severity", "violations_by_system",
                        "top_10_users", "mitigation_coverage", "trend_vs_prior_period"],
           "schedule": "monthly",
           "output_format": ["pdf", "xlsx"]},
          ["SOX"], ["all"]),

    _item("RPT-CERT-001", "Certification Campaign Completion Report", "Status and results of access certification campaigns.",
          "certification", "report_template",
          {"report_format": "pdf_and_excel",
           "sections": ["campaign_summary", "certifier_completion_rate", "certified_vs_revoked",
                        "overdue_items", "revocation_actions_taken"],
           "schedule": "end_of_campaign",
           "output_format": ["pdf", "xlsx"]},
          ["SOX", "ISO27001"], ["all"]),

    _item("RPT-FF-001", "Privileged Access Activity Log Report", "Full activity log for all FF sessions in the period.",
          "privileged_access", "report_template",
          {"report_format": "pdf_and_excel",
           "sections": ["sessions_summary", "activity_by_session", "sensitive_transactions",
                        "controller_review_status", "unreviewed_sessions"],
           "schedule": "monthly",
           "output_format": ["pdf", "xlsx"]},
          ["SOX", "ISO27001"], ["all"]),
]

ALL_ITEMS = SOD_RULES + MITIGATIONS + WORKFLOWS + RISK_SCENARIOS + CONTROLS + CERTIFICATION_TEMPLATES + BCM_TEMPLATES + SURVEYS + NOTIFICATION_TEMPLATES + REPORT_TEMPLATES


CORE_PACK = {
    "pack_code": "GOVERNEXPLUS_CORE_V1",
    "name": "GovernexPlus Core Template Library v1.0",
    "description": "Day-one library: 121 SoD rules, mitigations, workflows, controls, risk scenarios, certification templates, BCM templates, surveys, notification templates and reports. Covers SAP ECC/S4, SOX, ISO27001, PCI-DSS, GDPR.",
    "module": "all",
    "tags": ["core", "sap", "sox", "iso27001", "day-one"],
    "status": "published",
    "author": "GovernexPlus",
    "version": "1.0.0",
}


def seed_library(db: Session) -> dict:
    """
    Idempotent seeder. Returns count of new vs skipped items.
    """
    import uuid as uuid_mod
    from datetime import datetime

    inserted = 0
    skipped = 0

    # Ensure pack exists
    pack = db.query(TemplatePack).filter_by(pack_code=CORE_PACK["pack_code"]).first()
    if not pack:
        pack = TemplatePack(
            id=str(uuid_mod.uuid4()),
            **{k: v for k, v in CORE_PACK.items() if k != "version"},
        )
        db.add(pack)
        db.flush()
        logger.info("Created core template pack: %s", pack.id)

        ver = TemplatePackVersion(
            id=str(uuid_mod.uuid4()),
            pack_id=pack.id,
            version=CORE_PACK["version"],
            changelog="Initial release — day-one library",
            published_at=datetime.utcnow(),
            item_count=len(ALL_ITEMS),
            is_latest=True,
        )
        db.add(ver)
    else:
        logger.info("Core pack already exists: %s", pack.id)

    # Seed items
    existing_codes = {code for (code,) in db.query(TemplateItem.item_code).all()}

    for item_data in ALL_ITEMS:
        if item_data["item_code"] in existing_codes:
            skipped += 1
            continue

        payload = item_data["payload"]
        item = TemplateItem(
            id=str(uuid_mod.uuid4()),
            item_code=item_data["item_code"],
            name=item_data["name"],
            description=item_data.get("description"),
            module=item_data["module"],
            item_type=item_data["item_type"],
            compliance_frameworks=item_data.get("compliance_frameworks", []),
            industry_tags=item_data.get("industry_tags", []),
            payload=payload,
            checksum=_checksum(payload),
            version="1.0.0",
            status="published",
            pack_id=pack.id,
            pack_version="1.0.0",
            severity=item_data.get("severity"),
        )
        db.add(item)
        inserted += 1

    db.commit()
    logger.info("Template library seeded: %d inserted, %d skipped", inserted, skipped)
    return {"inserted": inserted, "skipped": skipped, "total": len(ALL_ITEMS)}
