"""Deep CRUD audit script for GovernexPlus server."""
import paramiko
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('212.47.75.51', username='root', password='l4yiVUCmI51v3aJ4g0wZvg', timeout=15)

# Login
_, out, _ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8000/auth/login '
    '-H "Content-Type: application/json" '
    '-d \'{"username":"qa_tenant_admin","password":"QaP@ss2026!Tenant","tenant_id":"qa-tenant-001"}\''
)
token = json.loads(out.read().decode())['access_token']
AUTH = f'Authorization: Bearer {token}'

results = []


def run(method, path, body=None):
    if method == 'GET':
        cmd = (
            f'curl -s -w "\\n__HTTP:%{{http_code}}" '
            f'-H "{AUTH}" -H "Content-Type: application/json" '
            f'http://127.0.0.1:8000{path}'
        )
    elif method == 'DELETE':
        cmd = (
            f'curl -s -w "\\n__HTTP:%{{http_code}}" -X DELETE '
            f'-H "{AUTH}" -H "Content-Type: application/json" '
            f'http://127.0.0.1:8000{path}'
        )
    else:
        data = json.dumps(body) if body else '{}'
        cmd = (
            f"curl -s -w '\\n__HTTP:%{{http_code}}' -X {method} "
            f"-H '{AUTH}' -H 'Content-Type: application/json' "
            f"-d '{data}' http://127.0.0.1:8000{path}"
        )
    _, out, _ = ssh.exec_command(cmd)
    raw = out.read().decode()
    parts = raw.rsplit('__HTTP:', 1)
    code = parts[1].strip() if len(parts) > 1 else '?'
    body_text = parts[0].strip() if len(parts) > 1 else raw
    try:
        d = json.loads(body_text)
    except Exception:
        d = {'_raw': body_text[:200]}
    return code, d


def log(module, op, code, ok_codes, detail=''):
    is_ok = code in ok_codes
    status = 'PASS' if is_ok else 'FAIL'
    results.append((module, op, code, status, detail))
    if not is_ok:
        print(f'  FAIL: {module} {op} HTTP {code} {detail[:80]}')


# ============================================
# 1. TPRM CRUD
# ============================================
print('Testing TPRM...')
code, d = run('POST', '/tprm/vendors', {
    'vendor_name': 'Test Vendor CRUD', 'vendor_code': 'TV001',
    'tier': 2, 'contact_email': 'test@vendor.com', 'country': 'US'
})
log('TPRM', 'Create Vendor', code, ['200', '201'], str(d.get('id', '')))
vid = d.get('id', '')

code, d = run('GET', '/tprm/vendors')
log('TPRM', 'List Vendors', code, ['200'], f"total={d.get('total', '?')}")

if vid:
    code, d = run('GET', f'/tprm/vendors/{vid}')
    log('TPRM', 'Get Vendor', code, ['200'], d.get('vendor_name', ''))

    code, d = run('PUT', f'/tprm/vendors/{vid}', {
        'vendor_name': 'Test Vendor Updated', 'contact_email': 'updated@vendor.com'
    })
    log('TPRM', 'Update Vendor', code, ['200'], d.get('vendor_name', ''))

    code, d = run('POST', '/tprm/assessments', {
        'vendor_id': vid, 'assessment_name': 'Q4 Review', 'due_date': '2026-12-31'
    })
    log('TPRM', 'Create Assessment', code, ['200', '201'], str(d.get('id', '')))

    code, d = run('POST', '/tprm/contracts', {
        'vendor_id': vid, 'contract_name': 'SaaS Agreement',
        'start_date': '2026-01-01', 'end_date': '2027-01-01',
        'value': 50000, 'currency': 'USD'
    })
    log('TPRM', 'Create Contract', code, ['200', '201'], str(d.get('id', '')))

    code, d = run('DELETE', f'/tprm/vendors/{vid}')
    log('TPRM', 'Delete Vendor', code, ['200', '204'], '')

# ============================================
# 2. JML CRUD
# ============================================
print('Testing JML...')
code, d = run('POST', '/jml/policies', {
    'policy_name': 'Test Onboarding Policy', 'event_type': 'JOINER',
    'description': 'Automated onboarding',
    'trigger_conditions': {'department': 'IT'},
    'birthright_roles': ['SAP_BASIC']
})
log('JML', 'Create Policy', code, ['200', '201'], str(d.get('id', '')))

code, d = run('GET', '/jml/policies')
log('JML', 'List Policies', code, ['200'], f"total={d.get('total', '?')}")

# ============================================
# 3. BCM CRUD
# ============================================
print('Testing BCM...')
code, d = run('POST', '/bcm/bia', {
    'process_name': 'Payment Processing', 'process_owner': 'CFO',
    'criticality': 'critical', 'rto_hours': 4, 'rpo_hours': 1
})
log('BCM', 'Create BIA', code, ['200', '201'], str(d.get('id', '')))

code, d = run('GET', '/bcm/bia')
log('BCM', 'List BIAs', code, ['200'], f"total={d.get('total', '?')}")

code, d = run('POST', '/bcm/plans', {
    'plan_name': 'IT DRP', 'plan_type': 'drp',
    'scope': 'All IT systems', 'owner_name': 'CTO', 'version': '1.0'
})
log('BCM', 'Create Plan', code, ['200', '201'], str(d.get('id', '')))

code, d = run('GET', '/bcm/plans')
log('BCM', 'List Plans', code, ['200'], f"total={d.get('total', '?')}")

# ============================================
# 4. Fraud CRUD
# ============================================
print('Testing Fraud...')
code, d = run('POST', '/fraud/rules', {
    'rule_name': 'Large Payment Check', 'description': 'Flag payments > 100K',
    'detection_type': 'threshold', 'conditions': {'amount_gt': 100000},
    'severity': 'high'
})
log('Fraud', 'Create Rule', code, ['200', '201'], str(d.get('id', '')))

code, d = run('GET', '/fraud/rules')
log('Fraud', 'List Rules', code, ['200'], f"total={d.get('total', '?')}")

code, d = run('GET', '/fraud/alerts')
log('Fraud', 'List Alerts', code, ['200'], f"total={d.get('total', '?')}")

code, d = run('GET', '/fraud/cases')
log('Fraud', 'List Cases', code, ['200'], f"total={d.get('total', '?')}")

# ============================================
# 5. Surveys CRUD
# ============================================
print('Testing Surveys...')
code, d = run('POST', '/surveys/', {
    'title': 'IT Security Survey', 'survey_type': 'risk_assessment',
    'description': 'Annual security questionnaire',
    'questions': [{'id': 'q1', 'text': 'Rate password strength', 'type': 'rating'}]
})
log('Surveys', 'Create Survey', code, ['200', '201'], str(d.get('id', '')))
sid = d.get('id', '')

code, d = run('GET', '/surveys/')
log('Surveys', 'List Surveys', code, ['200'], f"total={d.get('total', '?')}")

if sid:
    code, d = run('GET', f'/surveys/{sid}')
    log('Surveys', 'Get Survey', code, ['200'], d.get('title', ''))

# ============================================
# 6. Whistleblower
# ============================================
print('Testing Whistleblower...')
code, d = run('GET', '/whistleblower/cases')
log('Whistleblower', 'List Cases', code, ['200'], f"total={d.get('total', '?')}")

# Public submission (no auth needed)
_, out, _ = ssh.exec_command(
    "curl -s -w '\\n__HTTP:%{http_code}' -X POST "
    "-H 'Content-Type: application/json' "
    "-d '{\"category\":\"fraud\",\"description\":\"Test report\",\"is_anonymous\":true}' "
    "http://127.0.0.1:8000/whistleblower/submit"
)
raw = out.read().decode()
parts = raw.rsplit('__HTTP:', 1)
wb_code = parts[1].strip() if len(parts) > 1 else '?'
try:
    wb_d = json.loads(parts[0].strip())
except Exception:
    wb_d = {}
log('Whistleblower', 'Public Submit', wb_code, ['200', '201'],
    wb_d.get('reference_number', str(wb_d)[:40]))

# ============================================
# 7. Certification
# ============================================
print('Testing Certification...')
code, d = run('POST', '/certification/campaigns', {
    'campaign_name': 'Q4 Access Review', 'campaign_type': 'user_access',
    'scope': {'systems': ['SAP']}, 'due_date': '2026-12-31'
})
log('Certification', 'Create Campaign', code, ['200', '201'],
    str(d.get('id', d.get('campaign_id', d.get('detail', '')))))

# ============================================
# 8. Workflows
# ============================================
print('Testing Workflows...')
code, d = run('GET', '/workflows/')
log('Workflows', 'List Workflows', code, ['200'],
    f"count={len(d.get('workflows', []))}")

code, d = run('GET', '/workflows/builder/palette')
log('Workflows', 'Builder Palette', code, ['200'],
    f"triggers={len(d.get('triggers', []))}")

# ============================================
# 9. Role Studio full flow
# ============================================
print('Testing Role Studio...')
code, d = run('POST', '/role-studio/roles/risk-check', {
    'permissions': ['FB01', 'FK01', 'ME21N', 'MIGO', 'VF01'], 'system': 'SAP'
})
log('RoleStudio', 'Risk Check (5 perms)', code, ['200'],
    f"violations={len(d.get('violations', []))} perms={d.get('permissions_checked', '?')}")

code, d = run('POST', '/role-studio/roles/mining', {
    'threshold': 0.5, 'department': 'Finance'
})
log('RoleStudio', 'Mining', code, ['200'],
    f"patterns={len(d.get('patterns', d.get('clusters', [])))}")

# ============================================
# 10. Config CRUD
# ============================================
print('Testing Config...')
code, d = run('POST', '/config/sla', {
    'sla_key': 'access_request_approval', 'value': '48h',
    'description': 'Max time for access request approval'
})
log('Config', 'Upsert SLA', code, ['200'], str(d.get('key', '')))

code, d = run('GET', '/config/feature-flags')
log('Config', 'List Flags', code, ['200'], f"total={d.get('total', '?')}")

# ============================================
# 11. Reporting download
# ============================================
print('Testing Reporting...')
code, d = run('GET', '/reporting/reports/sod-violations/download?format=csv')
log('Reporting', 'Download CSV', code, ['200'], '')

code, d = run('GET', '/reporting/reports/sod-violations/download?format=json')
log('Reporting', 'Download JSON', code, ['200'], '')

# ============================================
# 12. Troubleshooter deep
# ============================================
print('Testing Troubleshooter...')
code, d = run('POST', '/troubleshooter/diagnose', {
    'user_id': 'PCHANG', 'transaction': 'STMS', 'system': 'PRD'
})
log('Troubleshooter', 'Diagnose PCHANG/STMS', code, ['200'],
    f"status={d.get('status', '?')}")

code, d = run('POST', '/troubleshooter/diagnose', {
    'user_id': 'MGARCIA', 'transaction': 'VA01', 'system': 'PRD'
})
log('Troubleshooter', 'Diagnose MGARCIA/VA01', code, ['200'],
    f"status={d.get('status', '?')}")

# ============================================
# 13. Identity Correlation
# ============================================
print('Testing Identity Correlation...')
code, d = run('GET', '/identity-correlation/overview')
log('IdentityCorr', 'Overview', code, ['200'],
    f"accounts={d.get('total_accounts', '?')} clusters={d.get('total_clusters', '?')}")

# ============================================
# 14. Mass Admin
# ============================================
print('Testing Mass Admin...')
code, d = run('GET', '/mass-admin/operations')
log('MassAdmin', 'List Operations', code, ['200'],
    f"ops={len(d.get('operations', []))}")

# ============================================
# 15. Library
# ============================================
print('Testing Library...')
code, d = run('GET', '/library/packs')
log('Library', 'List Packs', code, ['200'], f"total={d.get('total', '?')}")

code, d = run('GET', '/library/active-content')
log('Library', 'Active Content', code, ['200'], f"total={d.get('total', '?')}")

# ============================================
# 16. Access Requests
# ============================================
print('Testing Access Requests...')
code, d = run('GET', '/access-requests/')
log('AccessReq', 'List Requests', code, ['200'], f"total={d.get('total', '?')}")

code, d = run('POST', '/access-requests/', {
    'request_type': 'new_access', 'system_id': 'SAP-PRD',
    'role_id': 'SAP_FI_CLERK', 'justification': 'Need FI access for month-end'
})
log('AccessReq', 'Create Request', code, ['200', '201'],
    str(d.get('id', d.get('request_id', ''))))

# ============================================
# 17. Risk Management
# ============================================
print('Testing Risk Management...')
code, d = run('GET', '/risk-management/risks')
log('RiskMgmt', 'List Risks', code, ['200'], f"total={d.get('total', '?')}")

code, d = run('GET', '/risk-management/dashboard')
log('RiskMgmt', 'Dashboard', code, ['200'], str(list(d.keys())[:3]))

# ============================================
# 18. Audit Management
# ============================================
print('Testing Audit...')
code, d = run('GET', '/audit/plans')
log('Audit', 'List Plans', code, ['200'], f"total={d.get('total', '?')}")

# ============================================
# 19. Dashboard widgets
# ============================================
print('Testing Dashboards...')
code, d = run('GET', '/dashboard/summary/executive')
log('Dashboard', 'Executive Summary', code, ['200'],
    f"health={d.get('health_score', '?')}")

code, d = run('GET', '/dashboard/summary/certification')
log('Dashboard', 'Certification', code, ['200'], str(list(d.keys())[:3]))

code, d = run('GET', '/dashboard/summary/firefighter')
log('Dashboard', 'Firefighter', code, ['200'], str(list(d.keys())[:3]))

ssh.close()

# Print summary
print()
print(f"{'Module':<15} {'Operation':<30} {'HTTP':>4} {'St':<5} Detail")
print('=' * 95)
ok = fail = 0
for module, op, code, status, detail in results:
    if status == 'PASS':
        ok += 1
    else:
        fail += 1
    print(f'{module:<15} {op:<30} {code:>4} {status:<5} {detail[:40]}')

print(f'\n=== DEEP CRUD AUDIT: {ok} PASS / {fail} FAIL / {len(results)} TOTAL ===')
