"""Full CRUD audit v2 — tests all extended modules on server."""
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
    "curl -s -X POST http://127.0.0.1:8000/auth/login "
    "-H 'Content-Type: application/json' "
    """-d '{"username":"qa_tenant_admin","password":"QaP@ss2026!Tenant","tenant_id":"qa-tenant-001"}'"""
)
token = json.loads(out.read().decode())['access_token']
AUTH = f'Authorization: Bearer {token}'

results = []


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
    except Exception:
        d = {'_raw': body_text[:200]}
    return code, d


def log(mod, op, code, ok_codes, detail=''):
    s = 'PASS' if code in ok_codes else 'FAIL'
    results.append((mod, op, code, s, detail))
    if s == 'FAIL':
        print(f'  FAIL: {mod} {op} HTTP {code} {detail[:80]}')


print('=== CRUD AUDIT v2 ===\n')

# --- TPRM ---
print('[TPRM]')
code, d = run('POST', '/tprm/vendors', {
    'vendor_name': 'Audit Vendor', 'vendor_code': 'AV003',
    'tier': 'tier2', 'country': 'US'
})
log('TPRM', 'Create Vendor', code, ['200', '201'], str(d.get('id', '')))
vid = d.get('id', '')
if vid:
    code, d = run('GET', f'/tprm/vendors/{vid}')
    log('TPRM', 'Get Vendor', code, ['200'], d.get('vendor_name', ''))
    code, d = run('PUT', f'/tprm/vendors/{vid}', {'vendor_name': 'Audit Vendor Updated'})
    log('TPRM', 'Update Vendor', code, ['200'], d.get('vendor_name', ''))

# --- JML ---
print('[JML]')
code, d = run('POST', '/jml/policies', {
    'policy_name': 'Audit Onboarding', 'event_type': 'JOINER',
    'description': 'Auto onboard IT'
})
log('JML', 'Create Policy', code, ['200', '201'], str(d.get('id', '')))
pid = d.get('id', '')
if pid:
    code, d = run('GET', f'/jml/policies/{pid}')
    log('JML', 'Get Policy', code, ['200'], d.get('policy_name', ''))

# --- BCM ---
print('[BCM]')
code, d = run('POST', '/bcm/bia', {
    'process_name': 'Order Mgmt', 'process_owner': 'VP Sales',
    'criticality': 'high', 'rto_hours': 8, 'rpo_hours': 2
})
log('BCM', 'Create BIA', code, ['200', '201'], str(d.get('id', '')))
bia_id = d.get('id', '')
if bia_id:
    code, d = run('GET', f'/bcm/bia/{bia_id}')
    log('BCM', 'Get BIA', code, ['200'], d.get('process_name', ''))

code, d = run('POST', '/bcm/plans', {
    'plan_name': 'Sales Continuity', 'plan_type': 'bcp',
    'scope': 'Sales ops', 'owner_name': 'VP Sales'
})
log('BCM', 'Create Plan', code, ['200', '201'], str(d.get('id', '')))

# --- Fraud ---
print('[Fraud]')
code, d = run('POST', '/fraud/rules', {
    'rule_name': 'Large Payment Flag', 'rule_type': 'threshold',
    'description': 'Flag payments >100K', 'risk_score_weight': 5.0
})
log('Fraud', 'Create Rule', code, ['200', '201'], str(d.get('id', '')))
frid = d.get('id', '')
if frid:
    code, d = run('GET', '/fraud/rules')
    log('Fraud', 'List Rules', code, ['200'], f"total={d.get('total', '')}")
    code, d = run('PUT', f'/fraud/rules/{frid}', {'rule_name': 'Large Payment v2'})
    log('Fraud', 'Update Rule', code, ['200'], d.get('rule_name', ''))

code, d = run('POST', '/fraud/cases', {
    'title': 'Suspicious Transfer', 'severity': 'high',
    'description': 'Wire transfer anomaly detected'
})
log('Fraud', 'Create Case', code, ['200', '201'], str(d.get('id', '')))

# --- Surveys ---
print('[Surveys]')
code, d = run('POST', '/surveys/', {
    'title': 'Security Awareness 2026', 'survey_type': 'general',
    'description': 'Annual check',
    'questions': [{'question_id': 'q1', 'question_text': 'Rate password policy?', 'question_type': 'rating'}]
})
log('Surveys', 'Create Survey', code, ['200', '201'], str(d.get('id', '')))
sid = d.get('id', '')
if sid:
    code, d = run('GET', f'/surveys/{sid}')
    log('Surveys', 'Get Survey', code, ['200'], str(d.get('survey_name', d.get('title', ''))))
    code, d = run('PUT', f'/surveys/{sid}', {'title': 'Security Awareness v2', 'status': 'active'})
    log('Surveys', 'Update Survey', code, ['200'], str(d.get('survey_name', d.get('title', ''))))
code, d = run('GET', '/surveys/dashboard')
log('Surveys', 'Dashboard', code, ['200'], str(list(d.keys())[:3]))

# --- Whistleblower ---
print('[Whistleblower]')
code, d = run('POST', '/whistleblower/submit', {
    'category': 'fraud', 'title': 'Suspicious Activity',
    'description': 'Vendor payment concern', 'is_anonymous': True
}, no_auth=True)
log('Whistleblower', 'Public Submit', code, ['200', '201'],
    d.get('case_reference', str(d.get('detail', '')))[:20])
ref = d.get('case_reference', '')
if ref:
    code, d = run('GET', f'/whistleblower/track/{ref}', no_auth=True)
    log('Whistleblower', 'Public Track', code, ['200'], d.get('status', ''))
    code, d = run('POST', f'/whistleblower/track/{ref}/reply',
                  {'message_body': 'More info available'}, no_auth=True)
    log('Whistleblower', 'Public Reply', code, ['200', '201'], '')

code, d = run('GET', '/whistleblower/cases')
log('Whistleblower', 'List Cases (admin)', code, ['200'], f"total={d.get('total', '?')}")
code, d = run('GET', '/whistleblower/dashboard')
log('Whistleblower', 'Dashboard', code, ['200'], str(list(d.keys())[:3]))

# --- Certification ---
print('[Certification]')
code, d = run('POST', '/certification/campaigns', {
    'name': 'Q4 User Access Review', 'description': 'Quarterly review',
    'campaign_type': 'user_access', 'owner_id': 'qa_tenant_admin',
    'owner_name': 'QA Admin'
})
log('Certification', 'Create Campaign', code, ['200', '201'],
    d.get('campaign_id', str(d.get('detail', '')))[:20])
cid = d.get('campaign_id', '')
if cid:
    code, d = run('GET', f'/certification/campaigns/{cid}')
    log('Certification', 'Get Campaign', code, ['200'], d.get('name', ''))

# --- Config ---
print('[Config]')
code, d = run('POST', '/config/sla', {
    'module': 'access_request', 'sla_key': 'approval_timeout',
    'value': '48h', 'description': 'Max approval time'
})
log('Config', 'Upsert SLA', code, ['200'], '')

# --- Risk Mgmt ---
print('[Risk Mgmt]')
code, d = run('GET', '/risk-management/heatmap')
log('RiskMgmt', 'Heatmap', code, ['200'], '')
code, d = run('GET', '/risk-management/appetites')
log('RiskMgmt', 'Appetites', code, ['200'], '')

# --- Audit ---
print('[Audit]')
code, d = run('GET', '/audit/logs?limit=5')
log('Audit', 'Logs', code, ['200'], f"total={d.get('total', '?')}")

# --- Dashboards ---
print('[Dashboards]')
for path, name in [
    ('/fraud/dashboard', 'Fraud Dashboard'),
    ('/bcm/dashboard', 'BCM Dashboard'),
    ('/tprm/dashboard', 'TPRM Dashboard'),
    ('/jml/dashboard', 'JML Dashboard'),
]:
    code, d = run('GET', path)
    log('Dashboard', name, code, ['200'], str(list(d.keys())[:3]))

ssh.close()

# Summary
print()
print(f"{'Module':<15} {'Operation':<25} {'HTTP':>4} {'St':<5} Detail")
print('=' * 85)
ok = fail = 0
for mod, op, code, s, detail in results:
    if s == 'PASS':
        ok += 1
    else:
        fail += 1
    print(f'{mod:<15} {op:<25} {code:>4} {s:<5} {detail[:35]}')

print(f'\n=== CRUD AUDIT v2: {ok} PASS / {fail} FAIL / {len(results)} TOTAL ===')
