"""Re-test CRUD operations with corrected payloads."""
import paramiko
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('212.47.75.51', username='root', password='l4yiVUCmI51v3aJ4g0wZvg', timeout=15)

_, out, _ = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8000/auth/login '
    '-H "Content-Type: application/json" '
    "-d '{\"username\":\"qa_tenant_admin\",\"password\":\"QaP@ss2026!Tenant\",\"tenant_id\":\"qa-tenant-001\"}'"
)
token = json.loads(out.read().decode())['access_token']
AUTH = f'Authorization: Bearer {token}'

# Get OpenAPI schema for field discovery
_, out, _ = ssh.exec_command('curl -s http://127.0.0.1:8000/openapi.json')
openapi = json.loads(out.read().decode())
schemas = openapi.get('components', {}).get('schemas', {})

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
    is_ok = code in ok_codes
    s = 'PASS' if is_ok else 'FAIL'
    results.append((mod, op, code, s, detail))
    if not is_ok:
        print(f'  FAIL: {mod} {op} HTTP {code} {detail[:80]}')


def get_schema(ref_path):
    """Resolve $ref and print schema."""
    if not ref_path:
        return {}
    name = ref_path.split('/')[-1]
    s = schemas.get(name, {})
    if s:
        print(f'  Schema {name}: required={s.get("required", [])} '
              f'props={list(s.get("properties", {}).keys())[:12]}')
    return s


print('=== CORRECTED CRUD TESTS ===\n')

# --- TPRM: tier is string ---
print('[TPRM]')
code, d = run('POST', '/tprm/vendors', {
    'vendor_name': 'Audit Vendor Inc', 'vendor_code': 'AV001',
    'tier': 'tier2', 'country': 'US'
})
log('TPRM', 'Create Vendor', code, ['200', '201'], str(d.get('id', '')))
vid = d.get('id', '')
if vid:
    code, d = run('GET', f'/tprm/vendors/{vid}')
    log('TPRM', 'Get Vendor', code, ['200'], d.get('vendor_name', ''))
    code, d = run('PUT', f'/tprm/vendors/{vid}', {'vendor_name': 'Audit Vendor Updated'})
    log('TPRM', 'Update Vendor', code, ['200'], d.get('vendor_name', ''))
    code, d = run('DELETE', f'/tprm/vendors/{vid}')
    log('TPRM', 'Delete Vendor', code, ['200', '204'], '')

# --- JML ---
print('[JML]')
code, d = run('POST', '/jml/policies', {
    'policy_name': 'Audit Onboarding', 'event_type': 'JOINER',
    'description': 'Auto onboard IT staff'
})
log('JML', 'Create Policy', code, ['200', '201'], str(d.get('id', '')))

# --- BCM ---
print('[BCM]')
code, d = run('POST', '/bcm/bia', {
    'process_name': 'Order Management', 'process_owner': 'VP Sales',
    'criticality': 'high', 'rto_hours': 8, 'rpo_hours': 2
})
log('BCM', 'Create BIA', code, ['200', '201'], str(d.get('id', '')))

code, d = run('POST', '/bcm/plans', {
    'plan_name': 'Sales Continuity', 'plan_type': 'bcp',
    'scope': 'Sales operations', 'owner_name': 'VP Sales'
})
log('BCM', 'Create Plan', code, ['200', '201'], str(d.get('id', '')))

# --- Fraud Rules ---
print('[Fraud]')
# Discover schema
post_ep = openapi['paths'].get('/fraud/rules', {}).get('post', {})
ref = (post_ep.get('requestBody', {}).get('content', {})
       .get('application/json', {}).get('schema', {}).get('$ref', ''))
get_schema(ref)

code, d = run('POST', '/fraud/rules', {
    'rule_name': 'Large Payment Flag', 'rule_type': 'threshold',
    'description': 'Flag payments exceeding 100K',
    'severity': 'high', 'conditions': {'amount_gt': 100000}
})
log('Fraud', 'Create Rule', code, ['200', '201'], str(d.get('id', '')))

# --- Surveys ---
print('[Surveys]')
code, d = run('POST', '/surveys/', {
    'title': 'Security Awareness 2026',
    'survey_type': 'general',
    'description': 'Annual security awareness check',
    'questions': [{
        'question_id': 'q1',
        'question_text': 'How would you rate password policy?',
        'question_type': 'rating'
    }]
})
log('Surveys', 'Create Survey', code, ['200', '201'], str(d.get('id', '')))
sid = d.get('id', '')
if sid:
    code, d = run('GET', f'/surveys/{sid}')
    log('Surveys', 'Get Survey', code, ['200'], d.get('title', ''))
    code, d = run('PUT', f'/surveys/{sid}', {'title': 'Security Awareness v2', 'status': 'active'})
    log('Surveys', 'Update Survey', code, ['200'], d.get('title', ''))

# --- Whistleblower: PUBLIC endpoints ---
print('[Whistleblower]')
# Discover submit schema
wb_post = openapi['paths'].get('/whistleblower/submit', {}).get('post', {})
ref = (wb_post.get('requestBody', {}).get('content', {})
       .get('application/json', {}).get('schema', {}).get('$ref', ''))
get_schema(ref)

code, d = run('POST', '/whistleblower/submit', {
    'category': 'fraud',
    'title': 'Suspicious Activity Report',
    'description': 'Suspicious vendor payment observed',
    'is_anonymous': True
}, no_auth=True)
log('Whistleblower', 'Public Submit', code, ['200', '201'],
    d.get('reference_number', str(d.get('detail', ''))[:40]))
ref_num = d.get('reference_number', '')
if ref_num:
    code, d = run('GET', f'/whistleblower/track/{ref_num}', no_auth=True)
    log('Whistleblower', 'Public Track', code, ['200'], d.get('status', ''))

# --- Certification ---
print('[Certification]')
cert_post = openapi['paths'].get('/certification/campaigns', {}).get('post', {})
ref = (cert_post.get('requestBody', {}).get('content', {})
       .get('application/json', {}).get('schema', {}).get('$ref', ''))
s = get_schema(ref)
req_fields = s.get('required', [])

code, d = run('POST', '/certification/campaigns', {
    'name': 'Q4 User Access Review',
    'description': 'Quarterly user access certification',
    'campaign_type': 'user_access',
    'owner_id': 'qa_tenant_admin',
    'owner_name': 'QA Admin',
    'start_date': '2026-10-01',
    'end_date': '2026-12-31',
})
log('Certification', 'Create Campaign', code, ['200', '201'],
    str(d.get('id', d.get('campaign_id', str(d.get('detail', ''))[:40]))))

# --- Config SLA ---
print('[Config]')
cfg_post = openapi['paths'].get('/config/sla', {}).get('post', {})
ref = (cfg_post.get('requestBody', {}).get('content', {})
       .get('application/json', {}).get('schema', {}).get('$ref', ''))
get_schema(ref)

code, d = run('POST', '/config/sla', {
    'module': 'access_request',
    'sla_key': 'approval_timeout',
    'value': '48h',
    'description': 'Max time for access request approval'
})
log('Config', 'Upsert SLA', code, ['200'], str(d.get('key', '')))

# --- Risk Management ---
print('[Risk Management]')
code, d = run('GET', '/risk-management/heatmap')
log('RiskMgmt', 'Heatmap', code, ['200'], str(list(d.keys())[:3]))

code, d = run('GET', '/risk-management/appetites')
log('RiskMgmt', 'Appetites', code, ['200'], str(list(d.keys())[:3]))

# --- Audit Logs ---
print('[Audit]')
code, d = run('GET', '/audit/logs?limit=5')
log('Audit', 'Logs', code, ['200'], f"total={d.get('total', '?')}")

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

print(f'\n=== CRUD RETEST: {ok} PASS / {fail} FAIL / {len(results)} TOTAL ===')
