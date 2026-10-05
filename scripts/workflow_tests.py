"""
Comprehensive Workflow Tests — Full Business Scenarios
Tests submit → approve → complete flows across all modules.
"""
import paramiko
import json
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('212.47.75.51', username='root', password='l4yiVUCmI51v3aJ4g0wZvg', timeout=15)

# Login
_, out, _ = ssh.exec_command(
    "curl -s -X POST http://127.0.0.1:8000/auth/login "
    "-H 'Content-Type: application/json' "
    """-d '{"username":"qa_tenant_admin","password":"QaP@ss2026!Tenant","tenant_id":"qa-tenant-001"}'"""
)
login_resp = json.loads(out.read().decode())
token = login_resp['access_token']
AUTH = f'Authorization: Bearer {token}'
user_id = login_resp.get('user_id', 'qa_tenant_admin')

results = []
TOTAL_SCENARIOS = 0


def run(method, path, body=None, no_auth=False):
    auth_h = '' if no_auth else f"-H '{AUTH}'"
    data = json.dumps(body) if body else '{}'
    if method == 'GET':
        cmd = (f"curl -s -w '\\n__HTTP:%{{http_code}}' {auth_h} "
               f"-H 'Content-Type: application/json' http://127.0.0.1:8000{path}")
    elif method == 'DELETE':
        cmd = (f"curl -s -w '\\n__HTTP:%{{http_code}}' -X DELETE {auth_h} "
               f"-H 'Content-Type: application/json' http://127.0.0.1:8000{path}")
    else:
        cmd = (f"curl -s -w '\\n__HTTP:%{{http_code}}' -X {method} {auth_h} "
               f"-H 'Content-Type: application/json' -d '{data}' http://127.0.0.1:8000{path}")
    _, out, _ = ssh.exec_command(cmd)
    raw = out.read().decode()
    parts = raw.rsplit('__HTTP:', 1)
    code = parts[1].strip() if len(parts) > 1 else '?'
    body_text = parts[0].strip() if len(parts) > 1 else raw
    try:
        d = json.loads(body_text)
        if isinstance(d, list):
            d = {'_items': d, 'total': len(d)}
    except Exception:
        d = {'_raw': body_text[:300]}
    return code, d


def log(module, scenario, step, code, ok_codes, detail=''):
    global TOTAL_SCENARIOS
    s = 'PASS' if code in ok_codes else 'FAIL'
    results.append((module, scenario, step, code, s, detail))
    icon = '  ' if s == 'PASS' else '  FAIL:'
    if s == 'FAIL':
        print(f'{icon} {module}/{scenario}/{step} HTTP {code} {detail[:60]}')
    return s == 'PASS'


# ============================================================================
print('=' * 90)
print('COMPREHENSIVE WORKFLOW TESTS — ALL MODULES')
print('=' * 90)

# ============================================================================
# 1. ACCESS REQUESTS: Create → Submit → Approve
# ============================================================================
print('\n[1] ACCESS REQUESTS: Create → Submit → Approve')

code, d = run('POST', '/access-requests/', {
    'requester_user_id': user_id,
    'requester_name': 'QA Admin',
    'target_user_id': user_id,
    'target_user_name': 'QA Admin',
    'requested_roles': ['SAP_ALL'],
    'business_justification': 'Workflow test — need SAP access for audit',
    'priority': 'high'
})
ok = log('AccessReq', 'Lifecycle', 'Create Request', code, ['200', '201'], str(d.get('request_id', d.get('id', ''))))
req_id = d.get('request_id', d.get('id', ''))

if ok and req_id:
    code, d = run('GET', f'/access-requests/{req_id}')
    log('AccessReq', 'Lifecycle', 'Get Request', code, ['200'], d.get('status', ''))

    code, d = run('POST', f'/access-requests/{req_id}/submit')
    log('AccessReq', 'Lifecycle', 'Submit Request', code, ['200', '201'], str(d.get('status', '')))

    code, d = run('POST', f'/access-requests/{req_id}/approve/step1', {
        'approver_id': user_id,
        'decision': 'approved',
        'comments': 'Workflow test approval'
    })
    log('AccessReq', 'Lifecycle', 'Approve Step', code, ['200', '201'], str(d.get('status', '')))

# Preview risk
code, d = run('POST', '/access-requests/preview-risk', {
    'target_user_id': user_id,
    'requested_roles': ['SAP_ALL']
})
log('AccessReq', 'Risk', 'Preview Risk', code, ['200'], str(d.get('risk_score', d.get('overall_risk', ''))))

# Statistics
code, d = run('GET', '/access-requests/statistics')
log('AccessReq', 'Stats', 'Get Statistics', code, ['200', '404'], str(list(d.keys())[:3]))

code, d = run('GET', '/access-requests/approvals/pending')
log('AccessReq', 'Stats', 'Pending Approvals', code, ['200'], '')

# ============================================================================
# 2. CERTIFICATION: Create Campaign → Generate Items → Certify
# ============================================================================
print('\n[2] CERTIFICATION: Create → Generate → Start → Certify')

code, d = run('POST', '/certification/campaigns', {
    'name': 'Workflow Test Campaign',
    'description': 'End-to-end certification test',
    'campaign_type': 'user_access',
    'owner_id': user_id,
    'owner_name': 'QA Admin'
})
log('Cert', 'Lifecycle', 'Create Campaign', code, ['200', '201'], d.get('campaign_id', ''))
camp_id = d.get('campaign_id', '')

if camp_id:
    code, d = run('GET', f'/certification/campaigns/{camp_id}')
    log('Cert', 'Lifecycle', 'Get Campaign', code, ['200'], d.get('status', ''))

    code, d = run('POST', f'/certification/campaigns/{camp_id}/generate-items')
    log('Cert', 'Lifecycle', 'Generate Items', code, ['200', '201'], str(d.get('total_items', d.get('items_generated', ''))))

    code, d = run('POST', f'/certification/campaigns/{camp_id}/start')
    log('Cert', 'Lifecycle', 'Start Campaign', code, ['200'], d.get('status', ''))

    code, d = run('GET', f'/certification/campaigns/{camp_id}/statistics')
    log('Cert', 'Lifecycle', 'Get Statistics', code, ['200'], str(list(d.keys())[:3]))

code, d = run('GET', '/certification/campaigns')
log('Cert', 'List', 'List Campaigns', code, ['200'], str(d.get('total', len(d) if isinstance(d, list) else '')))

code, d = run('GET', '/certification/my-reviews')
log('Cert', 'Reviews', 'My Reviews', code, ['200'], '')

# ============================================================================
# 3. PRIVILEGED ACCESS (Firefighter): Request → Approve → Session → End → Review
# ============================================================================
print('\n[3] PRIVILEGED ACCESS: Request → Approve → Session → Review')

code, d = run('GET', '/privileged-access/reason-codes')
log('Firefighter', 'Setup', 'List Reason Codes', code, ['200'], str(d.get('total', len(d) if isinstance(d, list) else '')))

code, d = run('GET', '/privileged-access/firefighters')
log('Firefighter', 'Setup', 'List Firefighters', code, ['200'], '')

code, d = run('POST', '/privileged-access/requests', {
    'requester_user_id': user_id,
    'requester_name': 'QA Admin',
    'target_system': 'SAP_PRD',
    'firefighter_id': 'FF001',
    'reason_code': 'EMERGENCY',
    'business_justification': 'Critical production fix needed',
    'duration_hours': 2
})
log('Firefighter', 'Lifecycle', 'Create Request', code, ['200', '201'], str(d.get('request_id', d.get('id', ''))))
ff_req_id = d.get('request_id', d.get('id', ''))

if ff_req_id:
    code, d = run('GET', f'/privileged-access/requests/{ff_req_id}')
    log('Firefighter', 'Lifecycle', 'Get Request', code, ['200'], d.get('status', ''))

    code, d = run('POST', f'/privileged-access/requests/{ff_req_id}/approve', {
        'approver_id': user_id,
        'comments': 'Emergency approved'
    })
    log('Firefighter', 'Lifecycle', 'Approve Request', code, ['200'], d.get('status', ''))

code, d = run('GET', '/privileged-access/sessions')
log('Firefighter', 'Sessions', 'List Sessions', code, ['200'], '')

code, d = run('GET', '/privileged-access/sessions/active')
log('Firefighter', 'Sessions', 'Active Sessions', code, ['200'], '')

code, d = run('GET', '/privileged-access/reviews/pending')
log('Firefighter', 'Reviews', 'Pending Reviews', code, ['200'], '')

code, d = run('GET', '/privileged-access/statistics')
log('Firefighter', 'Stats', 'Statistics', code, ['200'], str(list(d.keys())[:3]))

# ============================================================================
# 4. RISK ANALYSIS: Analyze User → Get Violations → Simulate
# ============================================================================
print('\n[4] RISK ANALYSIS: Analyze → Violations → Simulate')

code, d = run('POST', '/risk/analyze/user', {'user_id': user_id})
log('Risk', 'Analysis', 'Analyze User', code, ['200'], str(d.get('total_violations', d.get('risk_score', ''))))

code, d = run('GET', '/risk/violations')
log('Risk', 'Violations', 'List Violations', code, ['200'], str(d.get('total', '')))

code, d = run('GET', '/risk/rules')
log('Risk', 'Rules', 'List Rules', code, ['200'], str(d.get('total', '')))

code, d = run('GET', f'/risk/simulate/add-role?user_id={user_id}&role_id=SAP_ALL')
log('Risk', 'Simulation', 'Simulate Add Role', code, ['200'], str(d.get('new_violations', d.get('risk_delta', ''))))

# ============================================================================
# 5. ROLE STUDIO: Create → Test → Submit → Approve → Activate
# ============================================================================
print('\n[5] ROLE STUDIO: Create → Test → Submit → Approve → Activate')

code, d = run('POST', '/role-studio/roles?created_by=qa_admin', {
    'name': 'Z_WF_TEST_ROLE',
    'description': 'Workflow test role',
    'role_type': 'single',
    'business_process': 'Finance',
    'department': 'Accounting',
    'owner': user_id
})
log('RoleStudio', 'Lifecycle', 'Create Role', code, ['200', '201'], str(d.get('role_id', d.get('id', ''))))
role_id = d.get('role_id', d.get('id', ''))

if role_id:
    code, d = run('GET', f'/role-studio/roles/{role_id}')
    log('RoleStudio', 'Lifecycle', 'Get Role', code, ['200'], d.get('name', ''))

    code, d = run('POST', f'/role-studio/roles/{role_id}/test')
    log('RoleStudio', 'Lifecycle', 'Test Role', code, ['200'], str(d.get('overall_result', '')))

    code, d = run('POST', f'/role-studio/roles/{role_id}/submit?submitted_by=qa_admin')
    log('RoleStudio', 'Lifecycle', 'Submit for Review', code, ['200'], d.get('status', ''))

    code, d = run('POST', f'/role-studio/roles/{role_id}/approve?approved_by=qa_admin')
    log('RoleStudio', 'Lifecycle', 'Approve Role', code, ['200'], d.get('status', ''))

    code, d = run('POST', f'/role-studio/roles/{role_id}/activate?activated_by=qa_admin')
    log('RoleStudio', 'Lifecycle', 'Activate Role', code, ['200'], d.get('status', ''))

code, d = run('GET', '/role-studio/catalog')
log('RoleStudio', 'Catalog', 'Get Catalog', code, ['200'], '')

# ============================================================================
# 6. TPRM: Create Vendor → Create Assessment → Create Issue → Dashboard
# ============================================================================
print('\n[6] TPRM: Vendor → Assessment → Issue → Dashboard')

code, d = run('POST', '/tprm/vendors', {
    'vendor_name': 'Workflow Test Vendor', 'vendor_code': 'WF001',
    'tier': 'tier1', 'country': 'US'
})
log('TPRM', 'Vendor', 'Create Vendor', code, ['200', '201'], str(d.get('id', '')))
vid = d.get('id', '')

if vid:
    code, d = run('GET', f'/tprm/vendors/{vid}')
    log('TPRM', 'Vendor', 'Get Vendor', code, ['200'], d.get('vendor_name', ''))

    code, d = run('POST', f'/tprm/vendors/{vid}/assessments', {
        'assessment_type': 'security',
        'assessor_name': 'QA Admin',
        'due_date': '2026-12-31',
        'questionnaire_responses': {'q1': 'compliant', 'q2': 'partial'}
    })
    log('TPRM', 'Assessment', 'Create Assessment', code, ['200', '201'], str(d.get('id', '')))
    assess_id = d.get('id', '')

    code, d = run('POST', f'/tprm/vendors/{vid}/issues', {
        'title': 'Missing encryption policy',
        'severity': 'high',
        'description': 'Vendor lacks data encryption standard',
        'remediation_plan': 'Implement AES-256 by Q4'
    })
    log('TPRM', 'Issues', 'Create Issue', code, ['200', '201'], str(d.get('id', '')))

code, d = run('GET', '/tprm/dashboard')
log('TPRM', 'Dashboard', 'Get Dashboard', code, ['200'], str(list(d.keys())[:3]))

# ============================================================================
# 7. JML: Create Policy → Create Event → Process → Dashboard
# ============================================================================
print('\n[7] JML: Policy → Event → Process → Dashboard')

code, d = run('POST', '/jml/policies', {
    'policy_name': 'WF Test Onboarding', 'event_type': 'JOINER',
    'description': 'Workflow test auto-onboard policy'
})
log('JML', 'Policy', 'Create Policy', code, ['200', '201'], str(d.get('id', '')))
pol_id = d.get('id', '')

if pol_id:
    code, d = run('GET', f'/jml/policies/{pol_id}')
    log('JML', 'Policy', 'Get Policy', code, ['200'], d.get('policy_name', ''))

    code, d = run('PUT', f'/jml/policies/{pol_id}', {
        'description': 'Updated workflow test policy'
    })
    log('JML', 'Policy', 'Update Policy', code, ['200'], '')

code, d = run('POST', '/jml/events', {
    'event_type': 'JOINER',
    'employee_id': 'EMP-WF001',
    'employee_name': 'Jane Workflow',
    'department': 'Engineering',
    'position': 'Developer',
    'effective_date': '2026-10-10'
})
log('JML', 'Events', 'Create Event', code, ['200', '201'], str(d.get('id', d.get('event_id', ''))))
evt_id = d.get('id', d.get('event_id', ''))

if evt_id:
    code, d = run('POST', f'/jml/events/{evt_id}/process')
    log('JML', 'Events', 'Process Event', code, ['200'], str(d.get('status', d.get('actions', ''))))

code, d = run('GET', '/jml/dashboard')
log('JML', 'Dashboard', 'Get Dashboard', code, ['200'], str(list(d.keys())[:3]))

# ============================================================================
# 8. BCM: BIA → Plan → Exercise → Incident Activation → Dashboard
# ============================================================================
print('\n[8] BCM: BIA → Plan → Exercise → Activation → Dashboard')

code, d = run('POST', '/bcm/bia', {
    'process_name': 'WF Test Process', 'process_owner': 'VP Ops',
    'criticality': 'high', 'rto_hours': 4, 'rpo_hours': 1
})
log('BCM', 'BIA', 'Create BIA', code, ['200', '201'], str(d.get('id', '')))

code, d = run('POST', '/bcm/plans', {
    'plan_name': 'WF Emergency Plan', 'plan_type': 'bcp',
    'scope': 'Full business operations', 'owner_name': 'VP Ops'
})
log('BCM', 'Plans', 'Create Plan', code, ['200', '201'], str(d.get('id', '')))
plan_id = d.get('id', '')

if plan_id:
    code, d = run('GET', '/bcm/plans')
    log('BCM', 'Plans', 'List Plans', code, ['200'], str(d.get('total', '')))

    code, d = run('PUT', f'/bcm/plans/{plan_id}', {
        'status': 'approved'
    })
    log('BCM', 'Plans', 'Approve Plan', code, ['200'], d.get('status', ''))

code, d = run('POST', '/bcm/exercises', {
    'exercise_name': 'WF Tabletop Exercise',
    'exercise_type': 'tabletop',
    'plan_id': plan_id or 'BCMP_test',
    'scheduled_date': '2026-11-01',
    'coordinator': 'QA Admin'
})
log('BCM', 'Exercises', 'Create Exercise', code, ['200', '201'], str(d.get('id', '')))

code, d = run('POST', '/bcm/activations', {
    'activation_name': 'WF Test Activation',
    'severity': 'high',
    'plan_id': plan_id or 'BCMP_test',
    'activated_by': 'QA Admin',
    'description': 'Test incident activation'
})
log('BCM', 'Activations', 'Create Activation', code, ['200', '201'], str(d.get('id', '')))

code, d = run('GET', '/bcm/dashboard')
log('BCM', 'Dashboard', 'Get Dashboard', code, ['200'], str(list(d.keys())[:3]))

# ============================================================================
# 9. FRAUD: Create Rule → Create Case → Update → Close → Dashboard
# ============================================================================
print('\n[9] FRAUD: Rule → Alert → Case → Investigate → Close')

code, d = run('POST', '/fraud/rules', {
    'rule_name': 'WF Velocity Check', 'rule_type': 'velocity',
    'description': 'Flag >5 transfers/hour', 'risk_score_weight': 7.0
})
log('Fraud', 'Rules', 'Create Rule', code, ['200', '201'], str(d.get('id', '')))
rule_id = d.get('id', '')

if rule_id:
    code, d = run('PUT', f'/fraud/rules/{rule_id}', {
        'description': 'Updated: Flag >10 transfers/hour',
        'is_active': True
    })
    log('Fraud', 'Rules', 'Update Rule', code, ['200'], '')

code, d = run('POST', '/fraud/cases', {
    'title': 'WF Suspicious Wire Transfer',
    'severity': 'critical',
    'description': 'Multiple high-value transfers to new beneficiary'
})
log('Fraud', 'Cases', 'Create Case', code, ['200', '201'], str(d.get('id', '')))
case_id = d.get('id', '')

if case_id:
    code, d = run('GET', f'/fraud/cases/{case_id}')
    log('Fraud', 'Cases', 'Get Case', code, ['200'], d.get('status', ''))

    code, d = run('PUT', f'/fraud/cases/{case_id}', {
        'status': 'investigating',
        'assigned_to': user_id
    })
    log('Fraud', 'Cases', 'Assign & Investigate', code, ['200'], d.get('status', ''))

    code, d = run('PUT', f'/fraud/cases/{case_id}', {
        'status': 'closed',
        'resolution_notes': 'Confirmed legitimate transfers after review'
    })
    log('Fraud', 'Cases', 'Close Case', code, ['200'], d.get('status', ''))

code, d = run('GET', '/fraud/alerts')
log('Fraud', 'Alerts', 'List Alerts', code, ['200'], str(d.get('total', '')))

code, d = run('GET', '/fraud/dashboard')
log('Fraud', 'Dashboard', 'Get Dashboard', code, ['200'], str(list(d.keys())[:3]))

# ============================================================================
# 10. SURVEYS: Create → Distribute → Respond → Analytics → Dashboard
# ============================================================================
print('\n[10] SURVEYS: Create → Distribute → Respond → Analytics')

code, d = run('POST', '/surveys/', {
    'title': 'WF Security Survey',
    'survey_type': 'general',
    'description': 'Workflow test security awareness survey',
    'questions': [
        {'question_id': 'wfq1', 'question_text': 'Rate password policy?', 'question_type': 'rating'},
        {'question_id': 'wfq2', 'question_text': 'Do you use MFA?', 'question_type': 'yes_no'}
    ]
})
log('Surveys', 'Lifecycle', 'Create Survey', code, ['200', '201'], str(d.get('id', '')))
srv_id = d.get('id', '')

if srv_id:
    code, d = run('PUT', f'/surveys/{srv_id}', {'status': 'active'})
    log('Surveys', 'Lifecycle', 'Activate Survey', code, ['200'], d.get('status', d.get('survey_name', '')))

    code, d = run('POST', f'/surveys/{srv_id}/distribute', {
        'distribution_type': 'targeted',
        'target_users': [user_id],
        'due_date': '2026-11-30'
    })
    log('Surveys', 'Distribution', 'Distribute Survey', code, ['200', '201'], str(d.get('id', d.get('distribution_id', ''))))
    dist_id = d.get('id', d.get('distribution_id', ''))

    code, d = run('GET', f'/surveys/{srv_id}/analytics')
    log('Surveys', 'Analytics', 'Get Analytics', code, ['200'], str(list(d.keys())[:3]))

    code, d = run('GET', f'/surveys/{srv_id}/responses')
    log('Surveys', 'Responses', 'List Responses', code, ['200'], '')

code, d = run('GET', '/surveys/dashboard')
log('Surveys', 'Dashboard', 'Get Dashboard', code, ['200'], str(list(d.keys())[:3]))

# ============================================================================
# 11. WHISTLEBLOWER: Submit → Track → Reply → Admin List → Update → Close
# ============================================================================
print('\n[11] WHISTLEBLOWER: Submit → Track → Reply → Admin Manage → Close')

code, d = run('POST', '/whistleblower/submit', {
    'category': 'corruption',
    'title': 'WF Test: Vendor Kickback Allegation',
    'description': 'Procurement manager receiving undisclosed payments from vendor',
    'priority': 'high',
    'is_anonymous': True
}, no_auth=True)
log('Whistleblower', 'Public', 'Anonymous Submit', code, ['200', '201'], d.get('case_reference', '')[:20])
case_ref = d.get('case_reference', '')

if case_ref:
    code, d = run('GET', f'/whistleblower/track/{case_ref}', no_auth=True)
    log('Whistleblower', 'Public', 'Track Case', code, ['200'], d.get('status', ''))

    code, d = run('POST', f'/whistleblower/track/{case_ref}/reply', {
        'message_body': 'I have additional evidence — a recording from Oct 2.'
    }, no_auth=True)
    log('Whistleblower', 'Public', 'Anonymous Reply', code, ['200', '201'], '')

# Admin side
code, d = run('GET', '/whistleblower/cases')
log('Whistleblower', 'Admin', 'List All Cases', code, ['200'], f"total={d.get('total', '?')}")
cases = d.get('cases', [])

if cases:
    wbc_id = cases[0].get('id', '')
    if wbc_id:
        code, d = run('GET', f'/whistleblower/cases/{wbc_id}')
        log('Whistleblower', 'Admin', 'Get Case Detail', code, ['200'], d.get('status', ''))

        code, d = run('PUT', f'/whistleblower/cases/{wbc_id}', {
            'status': 'under_investigation',
            'assigned_to': user_id,
            'priority': 'high'
        })
        log('Whistleblower', 'Admin', 'Assign & Investigate', code, ['200'], d.get('status', ''))

        code, d = run('POST', f'/whistleblower/cases/{wbc_id}/messages', {
            'message_body': 'Thank you for your report. We are investigating.',
            'is_visible_to_submitter': True
        })
        log('Whistleblower', 'Admin', 'Send Message', code, ['200', '201'], '')

        code, d = run('GET', f'/whistleblower/cases/{wbc_id}/messages')
        log('Whistleblower', 'Admin', 'View Thread', code, ['200'], f"msgs={d.get('total_messages', '?')}")

code, d = run('GET', '/whistleblower/dashboard')
log('Whistleblower', 'Dashboard', 'Get Dashboard', code, ['200'], str(list(d.keys())[:3]))

# ============================================================================
# 12. RISK MANAGEMENT: Create → Assess → KRI → Incident → Heatmap
# ============================================================================
print('\n[12] RISK MANAGEMENT: Register → Assess → Respond → Review')

code, d = run('POST', '/risk-management/risks', {
    'risk_name': 'WF Cyber Attack Risk',
    'risk_category': 'operational',
    'risk_owner': user_id,
    'description': 'Risk of ransomware attack on core systems',
    'likelihood': 4,
    'impact': 5
})
log('RiskMgmt', 'Register', 'Create Risk', code, ['200', '201'], str(d.get('id', '')))
risk_id = d.get('id', '')

if risk_id:
    code, d = run('GET', f'/risk-management/risks/{risk_id}')
    log('RiskMgmt', 'Register', 'Get Risk', code, ['200'], d.get('risk_name', ''))

    code, d = run('POST', f'/risk-management/risks/{risk_id}/assessments', {
        'assessor_id': user_id,
        'likelihood': 4,
        'impact': 5,
        'comments': 'High probability given recent threat intel'
    })
    log('RiskMgmt', 'Assess', 'Create Assessment', code, ['200', '201'], '')

    code, d = run('POST', f'/risk-management/risks/{risk_id}/responses', {
        'response_type': 'mitigate',
        'description': 'Deploy EDR + network segmentation',
        'owner_id': user_id,
        'target_date': '2026-12-31'
    })
    log('RiskMgmt', 'Respond', 'Create Response', code, ['200', '201'], '')

    code, d = run('POST', f'/risk-management/risks/{risk_id}/review-attestation', {
        'reviewer_id': user_id,
        'comments': 'Risk remains elevated, mitigation in progress'
    })
    log('RiskMgmt', 'Review', 'Review Attestation', code, ['200'], '')

code, d = run('GET', '/risk-management/heatmap')
log('RiskMgmt', 'Dashboard', 'Heatmap', code, ['200'], '')

code, d = run('GET', '/risk-management/top-risks')
log('RiskMgmt', 'Dashboard', 'Top Risks', code, ['200'], '')

code, d = run('GET', '/risk-management/trends')
log('RiskMgmt', 'Dashboard', 'Trends', code, ['200'], '')

# KRI
code, d = run('POST', '/risk-management/kris', {
    'kri_name': 'WF Failed Login Attempts',
    'risk_id': risk_id or 'test',
    'threshold_warning': 50,
    'threshold_critical': 100,
    'measurement_frequency': 'daily',
    'owner_id': user_id
})
log('RiskMgmt', 'KRI', 'Create KRI', code, ['200', '201'], str(d.get('id', '')))
kri_id = d.get('id', d.get('kri_id', ''))

if kri_id:
    code, d = run('POST', f'/risk-management/kris/{kri_id}/measurements', {
        'value': 75,
        'measured_by': user_id,
        'notes': 'Above warning threshold'
    })
    log('RiskMgmt', 'KRI', 'Record Measurement', code, ['200', '201'], '')

code, d = run('GET', '/risk-management/kris/dashboard')
log('RiskMgmt', 'KRI', 'KRI Dashboard', code, ['200'], '')

# Incident
code, d = run('POST', '/risk-management/incidents', {
    'title': 'WF Phishing Attempt Detected',
    'description': 'CFO impersonation email detected by SOC',
    'severity': 'high',
    'reported_by': user_id
})
log('RiskMgmt', 'Incident', 'Create Incident', code, ['200', '201'], str(d.get('id', '')))

# ============================================================================
# 13. SECURITY CONTROLS: Create → Evaluate → Exception → Dashboard
# ============================================================================
print('\n[13] SECURITY CONTROLS: Create → Evaluate → Exception')

code, d = run('POST', '/security-controls/controls', {
    'control_id': 'WF-CTRL-001',
    'name': 'WF Password Complexity',
    'description': 'Enforce minimum 12-char passwords',
    'category': 'access_control',
    'business_area': 'IT Security',
    'control_type': 'preventive'
})
log('SecCtrl', 'Controls', 'Create Control', code, ['200', '201'], str(d.get('control_id', d.get('id', ''))))
ctrl_id = d.get('control_id', d.get('id', ''))

if ctrl_id:
    code, d = run('POST', f'/security-controls/controls/{ctrl_id}/evaluate', {
        'system_id': 'SAP_PRD',
        'evaluator_id': user_id,
    })
    log('SecCtrl', 'Evaluate', 'Evaluate Control', code, ['200'], str(d.get('result', d.get('status', ''))))

code, d = run('GET', '/security-controls/dashboard')
log('SecCtrl', 'Dashboard', 'Get Dashboard', code, ['200'], str(list(d.keys())[:3]))

# ============================================================================
# 14. AUDIT MANAGEMENT: Entity → Plan → Engagement → Finding → Action
# ============================================================================
print('\n[14] AUDIT MANAGEMENT: Plan → Engage → Find → Act')

code, d = run('POST', '/audit-management/entities', {
    'name': 'WF Finance Department',
    'entity_type': 'department',
    'risk_rating': 'high'
})
log('AuditMgmt', 'Entity', 'Create Entity', code, ['200', '201'], str(d.get('id', '')))

code, d = run('POST', '/audit-management/plans', {
    'name': 'WF Annual Audit Plan 2026',
    'fiscal_year': '2026',
    'description': 'Comprehensive annual audit plan',
    'owner_id': user_id
})
log('AuditMgmt', 'Plan', 'Create Plan', code, ['200', '201'], str(d.get('id', d.get('plan_id', ''))))
plan_id = d.get('id', d.get('plan_id', ''))

code, d = run('POST', '/audit-management/engagements', {
    'title': 'WF Finance Process Audit',
    'engagement_type': 'operational',
    'plan_id': plan_id or 'test',
    'lead_auditor': user_id,
    'scope': 'Accounts payable and receivable',
    'start_date': '2026-10-15',
    'end_date': '2026-11-15'
})
log('AuditMgmt', 'Engagement', 'Create Engagement', code, ['200', '201'], str(d.get('id', '')))
eng_id = d.get('id', d.get('engagement_id', ''))

if eng_id:
    code, d = run('POST', f'/audit-management/engagements/{eng_id}/findings', {
        'title': 'WF Segregation of Duties Gap',
        'severity': 'high',
        'description': 'AP clerk can both create and approve POs',
        'recommendation': 'Implement maker-checker workflow'
    })
    log('AuditMgmt', 'Finding', 'Create Finding', code, ['200', '201'], str(d.get('id', '')))
    finding_id = d.get('id', d.get('finding_id', ''))

    if finding_id:
        code, d = run('PUT', f'/audit-management/findings/{finding_id}/management-response', {
            'response': 'Agreed. Will implement by Q1 2027.',
            'action_owner': user_id,
            'target_date': '2027-03-31'
        })
        log('AuditMgmt', 'Finding', 'Management Response', code, ['200'], '')

code, d = run('GET', '/audit-management/dashboard')
log('AuditMgmt', 'Dashboard', 'Get Dashboard', code, ['200'], str(list(d.keys())[:3]))

# ============================================================================
# 15. PROCESS CONTROL: Control → Test → Deficiency → Remediate
# ============================================================================
print('\n[15] PROCESS CONTROL: Control → Test → Deficiency → Remediate')

code, d = run('POST', '/process-control/controls', {
    'control_name': 'WF Invoice Approval',
    'control_type': 'manual',
    'description': 'All invoices >$5K require manager approval',
    'owner_id': user_id,
    'frequency': 'per_occurrence',
    'process_area': 'Accounts Payable'
})
log('ProcessCtrl', 'Control', 'Create Control', code, ['200', '201'], str(d.get('id', d.get('control_id', ''))))
pc_ctrl_id = d.get('id', d.get('control_id', ''))

if pc_ctrl_id:
    code, d = run('POST', f'/process-control/controls/{pc_ctrl_id}/tests', {
        'test_type': 'walkthrough',
        'tester_id': user_id,
        'sample_size': 25,
        'period_start': '2026-07-01',
        'period_end': '2026-09-30'
    })
    log('ProcessCtrl', 'Testing', 'Create Test', code, ['200', '201'], str(d.get('id', d.get('test_id', ''))))
    test_id = d.get('id', d.get('test_id', ''))

    if test_id:
        code, d = run('PUT', f'/process-control/tests/{test_id}/result', {
            'result': 'effective_with_exceptions',
            'exceptions_found': 3,
            'notes': '3 of 25 samples lacked proper approval'
        })
        log('ProcessCtrl', 'Testing', 'Record Result', code, ['200'], d.get('result', ''))

code, d = run('POST', '/process-control/deficiencies', {
    'title': 'WF Missing Invoice Approvals',
    'severity': 'significant',
    'description': '12% exception rate in invoice approval control',
    'control_id': pc_ctrl_id or 'test',
    'owner_id': user_id
})
log('ProcessCtrl', 'Deficiency', 'Create Deficiency', code, ['200', '201'], str(d.get('id', '')))
def_id = d.get('id', d.get('deficiency_id', ''))

if def_id:
    code, d = run('PUT', f'/process-control/deficiencies/{def_id}/remediate', {
        'remediation_plan': 'Implement automated approval workflow by Q1 2027',
        'target_date': '2027-03-31',
        'owner_id': user_id
    })
    log('ProcessCtrl', 'Deficiency', 'Submit Remediation', code, ['200'], '')

code, d = run('GET', '/process-control/dashboard')
log('ProcessCtrl', 'Dashboard', 'Get Dashboard', code, ['200'], str(list(d.keys())[:3]))

# ============================================================================
# 16. ACCESS LIFECYCLE (Shopping Cart): Cart → Add → Check → Submit
# ============================================================================
print('\n[16] ACCESS LIFECYCLE: Cart → Add Items → Check Conflicts → Submit')

code, d = run('POST', '/access-lifecycle/cart', {
    'requester_id': user_id
})
log('ShoppingCart', 'Lifecycle', 'Create Cart', code, ['200', '201'], str(d.get('cart_id', d.get('id', ''))))
cart_id = d.get('cart_id', d.get('id', ''))

if cart_id:
    code, d = run('POST', f'/access-lifecycle/cart/{cart_id}/items', {
        'role_id': 'SAP_FI_CLERK',
        'justification': 'Need for month-end close'
    })
    log('ShoppingCart', 'Lifecycle', 'Add Item', code, ['200', '201'], '')

    code, d = run('POST', f'/access-lifecycle/cart/{cart_id}/check-conflicts')
    log('ShoppingCart', 'Lifecycle', 'Check Conflicts', code, ['200'], str(d.get('has_conflicts', '')))

    code, d = run('POST', f'/access-lifecycle/cart/{cart_id}/submit', {
        'justification': 'Workflow test submission'
    })
    log('ShoppingCart', 'Lifecycle', 'Submit Cart', code, ['200', '201'], str(d.get('request_id', '')))

# ============================================================================
# 17. MASS ADMIN: Create Job → Monitor → Dashboard
# ============================================================================
print('\n[17] MASS ADMIN: Create Job → Monitor')

code, d = run('POST', '/mass-admin/jobs', {
    'operation': 'bulk_user_lock',
    'target_users': ['user1', 'user2', 'user3'],
    'parameters': {'reason': 'Security audit lockdown'}
})
log('MassAdmin', 'Jobs', 'Create Job', code, ['200', '201'], str(d.get('job_id', '')))
job_id = d.get('job_id', '')

if job_id:
    code, d = run('GET', f'/mass-admin/jobs/{job_id}')
    log('MassAdmin', 'Jobs', 'Get Job Status', code, ['200'], d.get('status', ''))

code, d = run('GET', '/mass-admin/jobs')
log('MassAdmin', 'Jobs', 'List Jobs', code, ['200'], str(d.get('total', len(d.get('jobs', [])))))

code, d = run('POST', '/mass-admin/preview', {
    'operation': 'bulk_role_assign',
    'params': {
        'user_ids': ['user1', 'user2'],
        'role_ids': ['SAP_FI_CLERK']
    }
})
log('MassAdmin', 'Preview', 'Preview Impact', code, ['200'], '')

# ============================================================================
# 18. LIBRARY: List → Activate → Deactivate
# ============================================================================
print('\n[18] TEMPLATE LIBRARY: Browse → Activate → Deactivate')

code, d = run('GET', '/library/stats')
log('Library', 'Browse', 'Get Stats', code, ['200'], str(list(d.keys())[:3]))

code, d = run('GET', '/library/items')
log('Library', 'Browse', 'List Items', code, ['200'], str(d.get('total', '')))
items = d.get('items', [])
if items:
    item_id = items[0].get('id', '')
    if item_id:
        code, d = run('POST', f'/library/items/{item_id}/activate')
        log('Library', 'Activate', 'Activate Item', code, ['200', '409'], str(d.get('status', d.get('detail', '')[:30])))

# ============================================================================
# 19. WORKFLOWS BUILDER: Palette → Validate → Templates
# ============================================================================
print('\n[19] WORKFLOWS: Builder → Validate → Templates')

code, d = run('GET', '/workflows/builder/palette')
log('Workflows', 'Builder', 'Get Palette', code, ['200'], str(list(d.keys())[:3]))

code, d = run('GET', '/workflows/builder/templates')
log('Workflows', 'Builder', 'List Templates', code, ['200'], '')

code, d = run('POST', '/workflows/builder/validate', {
    'workflow_name': 'WF Test Approval',
    'steps': [
        {'type': 'approval', 'approver': user_id, 'timeout_hours': 48},
        {'type': 'notification', 'recipients': [user_id]}
    ]
})
log('Workflows', 'Builder', 'Validate Workflow', code, ['200'], str(d.get('valid', d.get('is_valid', ''))))

# ============================================================================
# 20. AUDIT LOGS & CONFIG
# ============================================================================
print('\n[20] AUDIT LOGS & SYSTEM CONFIG')

code, d = run('GET', '/audit/logs?limit=10')
log('Audit', 'Logs', 'Query Logs', code, ['200'], f"total={d.get('total', '?')}")

code, d = run('GET', '/audit/logs/actions')
log('Audit', 'Logs', 'List Actions', code, ['200'], '')

code, d = run('GET', '/audit/reports/summary')
log('Audit', 'Reports', 'Summary Report', code, ['200'], '')

code, d = run('POST', '/config/sla', {
    'module': 'certification',
    'sla_key': 'campaign_timeout',
    'value': '30d',
    'description': 'Max campaign duration'
})
log('Config', 'SLA', 'Upsert SLA', code, ['200'], '')

# ============================================================================
# 21. PROVISIONING: Connectors → Tasks
# ============================================================================
print('\n[21] PROVISIONING: Connectors → Tasks')

code, d = run('GET', '/provisioning/connector-types')
log('Provisioning', 'Setup', 'List Connector Types', code, ['200'], '')

code, d = run('GET', '/provisioning/connectors')
log('Provisioning', 'Setup', 'List Connectors', code, ['200'], '')

code, d = run('GET', '/provisioning/tasks')
log('Provisioning', 'Tasks', 'List Tasks', code, ['200'], '')

code, d = run('GET', '/provisioning/queue/status')
log('Provisioning', 'Queue', 'Queue Status', code, ['200'], '')

# ============================================================================
# 22. AI ASSISTANT
# ============================================================================
print('\n[22] AI ASSISTANT')

code, d = run('POST', '/ai/query', {
    'question': 'What are the top SoD risks?'
})
log('AI', 'Query', 'Ask Question', code, ['200'], str(d.get('answer', ''))[:30])

code, d = run('POST', '/ai/risk/analyze', {
    'user_id': user_id
})
log('AI', 'Risk', 'AI Risk Analysis', code, ['200'], '')

# ============================================================================
# 23. IDENTITY CORRELATION
# ============================================================================
print('\n[23] IDENTITY CORRELATION')

code, d = run('GET', '/identity-correlation/overview')
log('IdCorrelation', 'Overview', 'Get Overview', code, ['200'], str(list(d.keys())[:3]))

code, d = run('GET', '/identity-correlation/clusters')
log('IdCorrelation', 'Clusters', 'List Clusters', code, ['200'], '')

code, d = run('GET', '/identity-correlation/orphans')
log('IdCorrelation', 'Orphans', 'List Orphans', code, ['200'], '')

# ============================================================================
# DONE — Summary
# ============================================================================
ssh.close()

print('\n' + '=' * 90)
print(f"{'Module':<16} {'Scenario':<14} {'Step':<25} {'HTTP':>4} {'St':<5} Detail")
print('=' * 90)
ok = fail = 0
for mod, scenario, step, code, s, detail in results:
    if s == 'PASS':
        ok += 1
    else:
        fail += 1
    print(f'{mod:<16} {scenario:<14} {step:<25} {code:>4} {s:<5} {detail[:30]}')

print(f'\n{"=" * 90}')
print(f'WORKFLOW TESTS: {ok} PASS / {fail} FAIL / {len(results)} TOTAL')
print(f'{"=" * 90}')
