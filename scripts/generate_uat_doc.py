#!/usr/bin/env python3
"""Generate comprehensive UAT Word document for GovernexPlus."""
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
import datetime

doc = Document()

# ── Styles ──────────────────────────────────────────────────────
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(11)
style.paragraph_format.space_after = Pt(6)

for level in range(1, 5):
    h = doc.styles[f'Heading {level}']
    h.font.name = 'Calibri'
    h.font.color.rgb = RGBColor(0x1E, 0x3A, 0x5F)

# Helper
def add_step_table(doc, steps):
    """Add a UAT step table: Step | Action | Expected Result"""
    t = doc.add_table(rows=1, cols=3)
    t.style = 'Light Grid Accent 1'
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    hdr = t.rows[0].cells
    hdr[0].text = 'Step'
    hdr[1].text = 'Action'
    hdr[2].text = 'Expected Result'
    for cell in hdr:
        for p in cell.paragraphs:
            p.runs[0].bold = True
            p.runs[0].font.size = Pt(10)
    for step_num, action, expected in steps:
        row = t.add_row().cells
        row[0].text = str(step_num)
        row[1].text = action
        row[2].text = expected
        for cell in row:
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(10)
    # Column widths
    for row in t.rows:
        row.cells[0].width = Cm(1.5)
        row.cells[1].width = Cm(8)
        row.cells[2].width = Cm(8)
    doc.add_paragraph()

def add_config_box(doc, title, items):
    """Add a configuration requirements box."""
    p = doc.add_paragraph()
    run = p.add_run(f'Configuration: {title}')
    run.bold = True
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x8B, 0x00, 0x00)
    for item in items:
        bp = doc.add_paragraph(item, style='List Bullet')
        bp.paragraph_format.space_after = Pt(2)
        for r in bp.runs:
            r.font.size = Pt(10)

# ══════════════════════════════════════════════════════════════
# COVER PAGE
# ══════════════════════════════════════════════════════════════
doc.add_paragraph()
doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('GovernexPlus')
run.font.size = Pt(36)
run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x5F)
run.bold = True

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('User Acceptance Testing (UAT)\nComplete Feature Guide & Test Procedures')
run.font.size = Pt(20)
run.font.color.rgb = RGBColor(0x4B, 0x5C, 0x6B)

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run(f'Version 1.0 | {datetime.date.today().strftime("%B %d, %Y")}')
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(0x6B, 0x7B, 0x8D)

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Intelligent Governance, Risk & Compliance Platform')
run.font.size = Pt(12)
run.italic = True

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# TABLE OF CONTENTS
# ══════════════════════════════════════════════════════════════
doc.add_heading('Table of Contents', level=1)
toc_items = [
    '1. Document Overview',
    '2. Environment Setup & Configuration',
    '3. Test Personas & Credentials',
    '4. Module 1: Authentication & Session Management',
    '5. Module 2: Dashboard & Navigation',
    '6. Module 3: User Management',
    '7. Module 4: Access Request Management',
    '8. Module 5: Certification Campaigns',
    '9. Module 6: SoD Rule Management',
    '10. Module 7: Access Risk Analysis (ARA)',
    '11. Module 8: Firefighter / Emergency Access',
    '12. Module 9: Enterprise Risk Management',
    '13. Module 10: Process Control & SOX',
    '14. Module 11: Audit Management',
    '15. Module 12: JML (Joiner / Mover / Leaver)',
    '16. Module 13: Identity Correlation',
    '17. Module 14: TPRM (Third-Party Risk Management)',
    '18. Module 15: Fraud Detection & Case Management',
    '19. Module 16: BCM (Business Continuity Management)',
    '20. Module 17: Whistleblower Portal',
    '21. Module 18: Surveys & Assessments',
    '22. Module 19: Template Library',
    '23. Module 20: Reporting & Analytics',
    '24. Module 21: Platform Administration',
    '25. Module 22: SAP Integration & Data Sync',
    '26. Cross-Module E2E Workflows',
    '27. UAT Sign-Off',
]
for item in toc_items:
    p = doc.add_paragraph(item)
    p.paragraph_format.space_after = Pt(2)
doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 1. DOCUMENT OVERVIEW
# ══════════════════════════════════════════════════════════════
doc.add_heading('1. Document Overview', level=1)
doc.add_paragraph(
    'This document provides a comprehensive guide to every feature in GovernexPlus, '
    'including step-by-step test procedures for User Acceptance Testing (UAT). '
    'Each module section includes:'
)
doc.add_paragraph('Feature description and business purpose', style='List Bullet')
doc.add_paragraph('Configuration prerequisites', style='List Bullet')
doc.add_paragraph('Step-by-step test procedures with expected results', style='List Bullet')
doc.add_paragraph('User persona requirements', style='List Bullet')

doc.add_heading('Priority Classification', level=2)
doc.add_paragraph(
    'P0 (Critical): Core journeys that must pass for release sign-off. '
    'P1 (Important): Important features; failures can be deferred with product owner approval.'
)

doc.add_heading('Test Result Recording', level=2)
t = doc.add_table(rows=1, cols=5)
t.style = 'Light Grid Accent 1'
hdr = t.rows[0].cells
for i, h in enumerate(['Scenario', 'Tester', 'Date', 'Result', 'Notes']):
    hdr[i].text = h
    hdr[i].paragraphs[0].runs[0].bold = True
row = t.add_row().cells
row[0].text = 'UAT-XX Step N'
row[1].text = ''
row[2].text = ''
row[3].text = 'PASS / FAIL / BLOCKED'
row[4].text = ''
doc.add_paragraph()
doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 2. ENVIRONMENT SETUP & CONFIGURATION
# ══════════════════════════════════════════════════════════════
doc.add_heading('2. Environment Setup & Configuration', level=1)

doc.add_heading('2.1 System Architecture', level=2)
doc.add_paragraph(
    'GovernexPlus consists of three main components:\n'
    '- Backend API: FastAPI (Python) running on port 9000\n'
    '- Frontend: React/TypeScript SPA served via Nginx on port 4500\n'
    '- Database: PostgreSQL 15\n'
    '- Optional: SAP NW RFC SDK for live SAP integration'
)

doc.add_heading('2.2 Docker Deployment (Recommended for UAT)', level=2)
doc.add_paragraph('Run the QA stack using Docker Compose:')
p = doc.add_paragraph()
run = p.add_run(
    'cd /opt/governexplus/app\n'
    'docker compose -f docker-compose.qa.yml up -d --build\n'
    'docker exec app-api-1 python scripts/seed_users.py'
)
run.font.name = 'Consolas'
run.font.size = Pt(9)

doc.add_heading('2.3 Service Ports', level=2)
t = doc.add_table(rows=1, cols=3)
t.style = 'Light Grid Accent 1'
hdr = t.rows[0].cells
hdr[0].text = 'Service'
hdr[1].text = 'Port'
hdr[2].text = 'URL'
for cell in hdr:
    cell.paragraphs[0].runs[0].bold = True
for service, port, url in [
    ('Frontend', '4500', 'http://localhost:4500'),
    ('Backend API', '9000', 'http://localhost:9000'),
    ('API Docs', '9000', 'http://localhost:9000/docs'),
    ('Mailpit (SMTP)', '8025', 'http://localhost:8025'),
    ('SAP Mock', '9100', 'http://localhost:9100'),
    ('AAD Mock', '9101', 'http://localhost:9101'),
    ('HR Mock', '9102', 'http://localhost:9102'),
]:
    row = t.add_row().cells
    row[0].text = service
    row[1].text = port
    row[2].text = url
doc.add_paragraph()

doc.add_heading('2.4 Environment Variables', level=2)
t = doc.add_table(rows=1, cols=3)
t.style = 'Light Grid Accent 1'
hdr = t.rows[0].cells
hdr[0].text = 'Variable'
hdr[1].text = 'Description'
hdr[2].text = 'Example'
for cell in hdr:
    cell.paragraphs[0].runs[0].bold = True
for var, desc, example in [
    ('DATABASE_URL', 'PostgreSQL connection string', 'postgresql://grc_user:pw@db:5432/grc_qa'),
    ('JWT_SECRET', 'Secret key for JWT signing', 'your-secret-key-here'),
    ('DEFAULT_TENANT_ID', 'Default tenant for login', 'gvnx'),
    ('CORS_ORIGINS', 'Allowed frontend origins', 'http://localhost:4500'),
    ('APP_ENV', 'Environment mode', 'testing / production'),
    ('SAP_CONNECTOR_MODE', 'SAP connection mode', 'mock / live'),
    ('SAP_HOST', 'SAP application server', '10.56.7.4'),
    ('SAP_SYSNR', 'SAP system number', '01'),
    ('SAP_CLIENT', 'SAP client', '100'),
    ('SAP_USER', 'SAP RFC user', 'GOVNX_RFC'),
    ('SAP_PASSWD', 'SAP RFC password', '***'),
    ('RATE_LIMIT_AUTH', 'Auth endpoint rate limit', '10/minute'),
    ('RATE_LIMIT_DEFAULT', 'Default API rate limit', '60/minute'),
    ('SESSION_TIMEOUT_MINUTES', 'Session idle timeout', '30'),
    ('ACCOUNT_LOCKOUT_THRESHOLD', 'Failed login attempts before lock', '5'),
]:
    row = t.add_row().cells
    row[0].text = var
    row[1].text = desc
    row[2].text = example
doc.add_paragraph()

doc.add_heading('2.5 SAP Integration Configuration', level=2)
doc.add_paragraph(
    'For live SAP connectivity (beyond mock mode), the following must be configured:'
)
doc.add_paragraph('Install SAP NW RFC SDK on the server (download from SAP Support Portal)', style='List Bullet')
doc.add_paragraph('Set LD_LIBRARY_PATH=/usr/local/sap/nwrfcsdk/lib', style='List Bullet')
doc.add_paragraph('Install pyrfc: pip install pyrfc', style='List Bullet')
doc.add_paragraph('Create RFC user in SAP (type Communication/System) with SAP_ALL or S_RFC auth', style='List Bullet')
doc.add_paragraph('Set SAP_CONNECTOR_MODE=live and provide SAP_HOST/SYSNR/CLIENT/USER/PASSWD', style='List Bullet')
doc.add_paragraph('Verify network connectivity: server must reach SAP on port 33XX (XX=system number)', style='List Bullet')

doc.add_heading('2.6 Initial Data Seeding', level=2)
doc.add_paragraph('After deployment, seed the database with test data:')
p = doc.add_paragraph()
run = p.add_run(
    '# Seed 22 QA personas + 30 sample users\n'
    'docker exec app-api-1 python scripts/seed_users.py\n\n'
    '# Seed SoD rules (121 rules auto-loaded on startup)\n'
    '# Seed template library (42 templates auto-loaded on startup)\n\n'
    '# Optional: seed process controls\n'
    'docker exec app-api-1 python scripts/seed_sql.py'
)
run.font.name = 'Consolas'
run.font.size = Pt(9)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 3. TEST PERSONAS
# ══════════════════════════════════════════════════════════════
doc.add_heading('3. Test Personas & Credentials', level=1)
doc.add_paragraph(
    'GovernexPlus uses 22 test personas representing different RBAC roles. '
    'All personas use tenant ID: qa-tenant-001'
)

t = doc.add_table(rows=1, cols=5)
t.style = 'Light Grid Accent 1'
hdr = t.rows[0].cells
for i, h in enumerate(['ID', 'Role', 'Username', 'Password', 'Used In']):
    hdr[i].text = h
    hdr[i].paragraphs[0].runs[0].bold = True

personas = [
    ('P01', 'Platform Admin', 'qa_platform_admin', 'QaP@ss2026!Platform', 'Config, Library'),
    ('P02', 'Tenant Admin', 'qa_tenant_admin', 'QaP@ss2026!Tenant', 'Dashboard, Users, Settings'),
    ('P03', 'CISO', 'qa_ciso', 'QaP@ss2026!CISO', 'Security Controls, CCM'),
    ('P04', 'Compliance Officer', 'qa_compliance', 'QaP@ss2026!Compliance', 'Certification, Audit'),
    ('P05', 'Risk Manager', 'qa_risk_manager', 'QaP@ss2026!Risk', 'ARA, Risk Mgmt, TPRM, BCM'),
    ('P06', 'IT Security Admin', 'qa_it_security', 'QaP@ss2026!Security', 'SoD, FF, Fraud, Whistleblower'),
    ('P07', 'Line Manager', 'qa_line_manager', 'QaP@ss2026!LineMgr', 'Approvals, JML'),
    ('P08', 'Business User', 'qa_requestor', 'QaP@ss2026!Request', 'Access Requests, Surveys'),
    ('P09', 'External Auditor', 'qa_ext_auditor', 'QaP@ss2026!ExtAudit', 'Audit (read-only)'),
    ('P10', 'SOX Control Owner', 'qa_sox_owner', 'QaP@ss2026!SOX', 'Process Control'),
    ('P11', 'FF Owner', 'qa_ff_owner', 'QaP@ss2026!FFOwner', 'FF Approvals'),
    ('P12', 'FF Controller', 'qa_ff_controller', 'QaP@ss2026!FFCtrl', 'FF Monitoring'),
    ('P13', 'HR Manager', 'qa_hr_manager', 'QaP@ss2026!HRMgr', 'JML, Identity'),
    ('P14', 'Process Owner', 'qa_process_owner', 'QaP@ss2026!Process', 'Process Control'),
    ('P15', 'IT Operations', 'qa_it_ops', 'QaP@ss2026!ITOps', 'Mass Admin'),
    ('P16', 'Viewer', 'qa_viewer', 'QaP@ss2026!View', 'Read-only access'),
    ('P17', 'Firefighter User', 'qa_firefighter', 'QaP@ss2026!FFUser', 'FF Sessions'),
    ('P18', 'Mitigation Monitor', 'qa_mitigation_monitor', 'QaP@ss2026!MitMon', 'Mitigations'),
    ('P19', 'Internal Auditor', 'qa_int_auditor', 'QaP@ss2026!IntAudit', 'Audit, CCM'),
    ('P20', 'Vendor Manager', 'qa_vendor_manager', 'QaP@ss2026!Vendor', 'TPRM'),
    ('P21', 'Role Owner', 'qa_role_owner', 'QaP@ss2026!RoleOwn', 'Pack Builder, Role Mining'),
    ('P22', 'Risk Owner', 'qa_risk_owner', 'QaP@ss2026!RiskOwn', 'Risk Register'),
]
for pid, role, user, pw, used in personas:
    row = t.add_row().cells
    row[0].text = pid
    row[1].text = role
    row[2].text = user
    row[3].text = pw
    row[4].text = used
    for cell in row:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.size = Pt(9)
doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# MODULES — Each with: Description, Config, Flow Steps
# ══════════════════════════════════════════════════════════════

modules = [
    {
        'num': 4, 'title': 'Authentication & Session Management', 'priority': 'P0',
        'desc': 'Secure login with JWT tokens, session persistence, account lockout, and logout. Supports multi-tenant authentication with tenant ID selection.',
        'config': [
            'JWT_SECRET must be set (auto-generated in dev with warning)',
            'SESSION_TIMEOUT_MINUTES controls idle timeout (default: 30)',
            'ACCOUNT_LOCKOUT_THRESHOLD controls failed attempts before lock (default: 5)',
            'RATE_LIMIT_AUTH limits auth endpoints (default: 10/minute)',
        ],
        'url': '/login',
        'persona': 'P08 (Business User)',
        'steps': [
            (1, 'Navigate to /login', 'Login page renders with GovernexPlus branding, username, password, and tenant ID fields'),
            (2, 'Enter tenant ID: qa-tenant-001', 'Tenant field populated'),
            (3, 'Enter username and password, click Sign In', 'Redirect to /dashboard, welcome message shows user name'),
            (4, 'Refresh page (F5)', 'Dashboard reloads, session persists, no redirect to login'),
            (5, 'Open DevTools > Local Storage', 'JWT token present under "accessToken" key'),
            (6, 'Click profile menu > Sign Out', 'Redirect to /login, JWT cleared from storage'),
            (7, 'Navigate to /dashboard while logged out', 'Redirect to /login (auth guard active)'),
            (8, 'Enter invalid password, click Sign In', 'Error message "Invalid credentials", stays on login page'),
            (9, 'Enter wrong password 6 times', 'Account lockout message after configured threshold'),
        ],
    },
    {
        'num': 5, 'title': 'Dashboard & Navigation', 'priority': 'P0',
        'desc': 'Central command center with stat cards, health score, attention items, and sidebar navigation to all modules. Supports dark mode and responsive layout.',
        'config': [
            'Dark mode: Tailwind "class" strategy, persisted in localStorage',
            'Sidebar groups: Dashboard, Access Governance, Risk & Compliance, Identity, Emergency Access, Extended Modules, Reports, Settings',
        ],
        'url': '/dashboard',
        'persona': 'P02 (Tenant Admin)',
        'steps': [
            (1, 'Login and view dashboard', 'Stat cards: Total Users, Active Risks, Open Requests, Pending Reviews'),
            (2, 'Verify sidebar navigation', 'Left sidebar shows all module groups with icons'),
            (3, 'Click each sidebar item', 'Each page loads without errors (no blank page, no 500)'),
            (4, 'Toggle dark mode', 'UI switches to dark theme, navy backgrounds, white text'),
            (5, 'Toggle back to light mode', 'Light theme restored, no visual glitches'),
            (6, 'Resize browser to 375px width', 'Sidebar collapses to hamburger menu'),
            (7, 'Open hamburger menu', 'Navigation drawer slides in, all items accessible'),
        ],
    },
    {
        'num': 6, 'title': 'User Management', 'priority': 'P0',
        'desc': 'Full CRUD for user accounts: create, search, edit, deactivate/reactivate, assign/remove roles. User detail page with tabs for roles, entitlements, risk profile, and activity log.',
        'config': [
            'Users are tenant-scoped (multi-tenant isolation)',
            'User model: username, full_name, email, department, status, risk_score',
            'Role assignment: many-to-many via UserRole table',
        ],
        'url': '/users',
        'persona': 'P02 (Tenant Admin)',
        'steps': [
            (1, 'Navigate to Settings > Users', 'User list table loads with columns: Name, Username, Email, Department, Status'),
            (2, 'Click Create User', 'Create user form opens'),
            (3, 'Fill: username=uat_test_user, name=UAT Test, email=uat@test.com, dept=QA', 'Fields populated'),
            (4, 'Click Save', 'Success toast "User created", user appears in table'),
            (5, 'Search for "uat_test_user"', 'Table filters to show only the new user'),
            (6, 'Click user row > Edit', 'Edit form opens pre-populated'),
            (7, 'Change department to Engineering, click Save', 'Success toast, table reflects change'),
            (8, 'Click Deactivate on the user', 'Status changes to Inactive'),
            (9, 'Click Reactivate', 'Status changes back to Active'),
            (10, 'Open user > Roles tab > Assign Role', 'Role selector appears, role assigned on save'),
        ],
    },
    {
        'num': 7, 'title': 'Access Request Management', 'priority': 'P0',
        'desc': 'End-to-end access request lifecycle: submit request with role selection from catalog, SoD pre-check, multi-level approval workflow, provisioning, and audit trail.',
        'config': [
            'Approval workflow: configurable single/multi-level',
            'SoD pre-check: runs ARA rules before submission',
            'Provisioning: auto-provision on approval (when SAP connected)',
            'Shopping cart: multi-role request support',
        ],
        'url': '/access-requests',
        'persona': 'P08 (Business User) submits, P07 (Line Manager) approves',
        'steps': [
            (1, 'Login as P08, navigate to Access Requests', 'Access request list loads'),
            (2, 'Click New Request', 'Request form with role catalog opens'),
            (3, 'Browse/search role catalog', 'Roles listed with descriptions and risk levels'),
            (4, 'Select a role (e.g., SAP_FI_POST), add to cart', 'Role added to shopping cart'),
            (5, 'SoD pre-check runs automatically', 'If violations found: warning displayed with risk details'),
            (6, 'Enter justification: "Need FI posting for month-end close"', 'Justification field populated'),
            (7, 'Click Submit', 'Success toast, request shows status "Pending Approval"'),
            (8, 'Navigate to My Requests', 'New request visible with pending status'),
            (9, 'Logout > Login as P07 (Line Manager)', 'Dashboard loads for approver'),
            (10, 'Navigate to Approvals', 'Pending request from P08 visible'),
            (11, 'Click request > Review details', 'Requester info, requested roles, justification, SoD check results shown'),
            (12, 'Click Approve', 'Status changes to "Approved", provisioning triggered'),
            (13, 'Login as P08, check My Requests', 'Request shows "Approved" status'),
            (14, 'Test rejection: Submit another request, login as P07, click Reject with reason', 'Request marked "Rejected" with reason'),
        ],
    },
    {
        'num': 8, 'title': 'Certification Campaigns', 'priority': 'P0',
        'desc': 'Periodic user access review campaigns. Compliance officer creates campaigns, assigns reviewers, reviewers certify/revoke access, with full audit trail and progress tracking.',
        'config': [
            'Campaign types: User Access Review, Role Review, Entitlement Review',
            'Scope: All Users, by Department, by Role, Custom Selection',
            'Reviewer assignment: by manager, by role owner, custom',
            'Auto-close: campaigns can auto-close when all items reviewed',
        ],
        'url': '/certification',
        'persona': 'P04 (Compliance Officer) creates, P07 (Line Manager) reviews',
        'steps': [
            (1, 'Login as P04, navigate to Certification', 'Campaign list loads with stats'),
            (2, 'Click Create Campaign', 'Campaign creation form opens'),
            (3, 'Fill: name="Q4 Access Review", type=User Access, scope=All Users, reviewer=P07', 'Form populated'),
            (4, 'Click Create (Save as Draft)', 'Campaign appears with "Draft" status'),
            (5, 'Click Launch Campaign', 'Status changes to "Active", review items generated'),
            (6, 'Logout > Login as P07', 'Reviewer dashboard'),
            (7, 'Navigate to My Reviews', 'Review items for the campaign visible'),
            (8, 'Click first item > Certify (keep access)', 'Item marked with green checkmark'),
            (9, 'Click next item > Revoke, enter reason', 'Item marked with red X, revocation queued'),
            (10, 'Bulk select items > Bulk Certify', 'All selected items certified'),
            (11, 'Login as P04, view campaign progress', 'Progress bar shows % complete, per-reviewer breakdown'),
            (12, 'Generate campaign report', 'Report shows all decisions with timestamps and reviewers'),
        ],
    },
    {
        'num': 9, 'title': 'SoD Rule Management', 'priority': 'P0',
        'desc': '121 pre-loaded Separation of Duties rules covering SAP modules (FI, MM, SD, HR, BA, TR, AA, WM, QM, PM, PS). Create custom rules, enable/disable, and view rule impact.',
        'config': [
            'SoD ruleset: 121 rules auto-loaded from SoDRulesetLibrary on startup',
            'Two rule engines: core/rules/engine.py (128 rules) + core/ara/rules.py (129 rules)',
            'Custom rules: tenant-specific, never overwrite built-in rule IDs',
            'Rule modules: FI, MM, SD, HR, BA, TR, AA, WM, QM, PM, PS, XP',
        ],
        'url': '/risk/sod-rules',
        'persona': 'P06 (IT Security Admin)',
        'steps': [
            (1, 'Navigate to Risk > SoD Rules', 'Rule table loads with 120+ pre-loaded rules'),
            (2, 'Verify columns: Rule ID, Name, Module, Functions, Risk Level', 'All columns visible'),
            (3, 'Search "FI" in search box', 'Finance module rules filtered'),
            (4, 'Filter by module dropdown', 'Correct rules shown per module'),
            (5, 'Click a rule to view details', 'Detail view: description, function 1, function 2, tcodes, risk level'),
            (6, 'Click Create Rule', 'Rule creation form opens'),
            (7, 'Fill: name="Custom UAT Rule", functions, risk level', 'Form populated'),
            (8, 'Save', 'Custom rule appears in list marked as "Custom"'),
            (9, 'Toggle a built-in rule to disabled', 'Rule marked disabled'),
            (10, 'Re-enable the rule', 'Rule active again'),
        ],
    },
    {
        'num': 10, 'title': 'Access Risk Analysis (ARA)', 'priority': 'P0',
        'desc': 'Run SoD violation analysis across all users or specific users. Violations are DB-persisted, with AI-generated narratives explaining risks in business language.',
        'config': [
            'ARA engine: per-tenant instance (Dict registry pattern)',
            'Violation persistence: background task writes to RiskViolation table',
            'AI narratives: LLM-generated risk explanations (configurable)',
            'Severity mapping: Critical > High > Medium > Low',
        ],
        'url': '/risk/violations',
        'persona': 'P05 (Risk Manager)',
        'steps': [
            (1, 'Navigate to Risk > ARA Dashboard', 'Page loads with violation summary stats'),
            (2, 'Click Run Analysis (scope: All Users)', 'Progress indicator shows, analysis executes'),
            (3, 'View results', 'Violations listed: User, Rule, Conflicting Roles, Severity'),
            (4, 'Click a violation', 'Detail view with rule description, affected tcodes, user info'),
            (5, 'View AI narrative section', 'Plain-language risk explanation displayed'),
            (6, 'Filter by severity "Critical"', 'Only critical violations shown'),
            (7, 'Navigate away and return', 'Violations persist (DB-stored, not in-memory)'),
            (8, 'Export violations to CSV/PDF', 'File downloads with violation data'),
        ],
    },
    {
        'num': 11, 'title': 'Firefighter / Emergency Access', 'priority': 'P0',
        'desc': 'Request, approve, and monitor emergency privileged access. Complete audit trail with session logging, controller review, and auto-expiry.',
        'config': [
            'FF IDs: pre-configured emergency access identities',
            'Approval: FF Owner must approve before session starts',
            'Session duration: configurable, auto-expires',
            'Logging: all actions during FF session recorded',
            'Controller: monitors active sessions in real-time',
        ],
        'url': '/privileged-access',
        'persona': 'P06 (requester), P11 (FF Owner), P12 (FF Controller), P17 (FF User)',
        'steps': [
            (1, 'Login as P06, navigate to Privileged Access', 'FF dashboard loads with stats'),
            (2, 'Click Request Emergency Access', 'Request form opens'),
            (3, 'Select FF ID, reason code, enter justification, set duration', 'Form populated'),
            (4, 'Submit request', 'Toast "Request submitted", status "Pending Approval"'),
            (5, 'Login as P11 (FF Owner)', 'FF Owner view'),
            (6, 'View pending request, review details', 'Request details: requester, reason, FF ID, duration'),
            (7, 'Click Approve', 'Status changes to "Approved"'),
            (8, 'Login as P17 (FF User), start session', 'Session timer starts, activity logging begins'),
            (9, 'Perform actions during session', 'Each action logged in session log'),
            (10, 'End session (check-out)', 'Session closed, duration recorded'),
            (11, 'Login as P12 (Controller), view session log', 'Complete activity log with timestamps'),
            (12, 'Controller completes review', 'Review recorded in audit trail'),
        ],
    },
    {
        'num': 12, 'title': 'Enterprise Risk Management', 'priority': 'P1',
        'desc': 'Full risk register with assessment, risk heatmap, risk responses, KRI dashboard, risk incidents, scenarios with Monte Carlo simulation, and risk appetite management.',
        'config': [
            'Risk categories: IT_CYBER, OPERATIONAL, FINANCIAL, COMPLIANCE, STRATEGIC, etc.',
            'Risk matrix: 5x5 (Likelihood x Impact)',
            'KRI thresholds: warning and breach levels configurable per indicator',
            'Risk appetite: per-category tolerance settings',
        ],
        'url': '/risk-management',
        'persona': 'P05 (Risk Manager)',
        'steps': [
            (1, 'Navigate to Risk Management > Register', 'Risk register table loads'),
            (2, 'Click Create Risk', 'Risk creation form opens'),
            (3, 'Fill: title, category, description, likelihood=4, impact=5', 'Form populated'),
            (4, 'Save', 'Risk appears with calculated score (4x5=20)'),
            (5, 'Add risk assessment', 'Assessment recorded, status changes'),
            (6, 'Navigate to Risk Heatmap', '5x5 matrix with risks plotted as dots'),
            (7, 'Click a cell to drill down', 'Risks in that zone listed'),
            (8, 'Add risk response: Mitigate, assign owner, due date', 'Response attached to risk'),
            (9, 'Navigate to KRI Dashboard', 'Key Risk Indicators listed'),
            (10, 'Create KRI with thresholds', 'KRI appears with status (Normal/Warning/Breach)'),
            (11, 'Navigate to Risk Incidents, report incident', 'Incident created with lifecycle tracking'),
        ],
    },
    {
        'num': 13, 'title': 'Process Control & SOX', 'priority': 'P1',
        'desc': 'Control library, control testing, deficiency management, CCM (Continuous Controls Monitoring), SOX sign-off certification, and evidence management.',
        'config': [
            'Control types: Preventive, Detective, Corrective',
            'Control nature: Manual, Automated, IT-Dependent',
            'Testing frequency: Daily, Weekly, Monthly, Quarterly, Annual',
            'Deficiency classification: Control Gap, Significant Deficiency, Material Weakness',
        ],
        'url': '/process-control',
        'persona': 'P10 (SOX Control Owner), P14 (Process Owner)',
        'steps': [
            (1, 'Navigate to Process Control > Controls', 'Control library loads'),
            (2, 'Create control: name, type=Preventive, nature=Manual, frequency=Daily', 'Control created in Draft status'),
            (3, 'Activate control', 'Status changes to Active'),
            (4, 'Navigate to Testing > Create Test', 'Test form opens for selected control'),
            (5, 'Execute test: record result (Effective/Ineffective)', 'Test result saved, deficiency auto-created if ineffective'),
            (6, 'Navigate to Deficiencies', 'Deficiency from failed test visible'),
            (7, 'Add remediation plan, track lifecycle', 'Open > In Remediation > Remediated > Verified Closed'),
            (8, 'Navigate to CCM Dashboard', 'CCM rules and results visible'),
            (9, 'Create CCM rule with threshold condition', 'Rule executes, PASS/FAIL result shown'),
            (10, 'SOX sign-off certification', 'Sign-off recorded with timestamp and signer'),
        ],
    },
    {
        'num': 14, 'title': 'Audit Management', 'priority': 'P1',
        'desc': 'Complete audit lifecycle: planning, engagements, findings, management actions, workpapers, and report generation. External auditor has read-only access.',
        'config': [
            'Audit types: IT, Financial, Operational, Compliance',
            'Finding severity: Critical, High, Medium, Low, Observation',
            'Engagement lifecycle: Planned > Announced > Fieldwork > Draft Report > Final Report > Closed',
            'External auditor: read-only RBAC role (P09)',
        ],
        'url': '/audit-management',
        'persona': 'P19 (Internal Auditor), P09 (External Auditor - read only)',
        'steps': [
            (1, 'Login as P19, navigate to Audit Management', 'Audit management dashboard loads'),
            (2, 'Create Audit Plan: name, type=Annual, fiscal year', 'Plan created in Draft status'),
            (3, 'Create Engagement under plan', 'Engagement created: Planned > Announced > Fieldwork'),
            (4, 'Add Finding: title, severity=Critical, description, recommendation', 'Finding attached to engagement'),
            (5, 'Record management response and action plan', 'Action tracked: Open > In Progress > Completed'),
            (6, 'Create and submit workpaper', 'Workpaper submitted for review'),
            (7, 'Complete engagement, generate report', 'Final report generated with all findings'),
            (8, 'Login as P09 (External Auditor)', 'External auditor view'),
            (9, 'View engagements and findings (read-only)', 'All data visible but no create/edit buttons'),
        ],
    },
    {
        'num': 15, 'title': 'JML (Joiner / Mover / Leaver)', 'priority': 'P0',
        'desc': 'Automated identity lifecycle management. Define policies for joiners (auto-provision birthright roles), movers (re-provision on department change), and leavers (auto-revoke all access).',
        'config': [
            'JML policies: per-event-type (joiner/mover/leaver) per org unit',
            'Birthright roles: auto-assigned roles for new joiners',
            'HR integration: events triggered by HR system feed or manual entry',
            'Approval: mover/leaver events can require line manager approval',
        ],
        'url': '/jml',
        'persona': 'P13 (HR Manager), P07 (Line Manager)',
        'steps': [
            (1, 'Login as P13, navigate to JML Policies', 'Policy list loads with stats'),
            (2, 'Click Create Policy', 'Policy creation form opens'),
            (3, 'Fill: name="Finance Joiner", event_type=Joiner, org_unit=Finance, birthright_roles=ROLE_FI_VIEWER', 'Form populated'),
            (4, 'Save', 'Policy created with "Joiner" badge'),
            (5, 'Search and filter policies by event type', 'Filters work correctly'),
            (6, 'Trigger joiner event for Finance department', 'Event processed, birthright roles auto-assigned'),
            (7, 'Trigger mover event: Finance > Marketing', 'Old roles queued for removal, new roles queued for grant'),
            (8, 'Login as P07, review and approve JML items', 'Pending items visible, approve/reject available'),
            (9, 'Trigger leaver event', 'All roles revoked, account deactivated'),
            (10, 'View JML event log', 'All events listed with status and timestamps'),
        ],
    },
    {
        'num': 16, 'title': 'Identity Correlation', 'priority': 'P1',
        'desc': 'Cross-system identity correlation engine. Matches user accounts across SAP, HR, AD, and other systems. Identifies orphan accounts, conflicts, and mismatches.',
        'config': [
            'Identity sources: SAP, HR System, Azure AD (configurable)',
            'Correlation rules: match by email, employee ID, or custom field',
            'Per-tenant engine instance',
        ],
        'url': '/intelligence/identity',
        'persona': 'P13 (HR Manager)',
        'steps': [
            (1, 'Navigate to Identity Correlation', 'Overview stats: total identities, correlated, orphaned, conflicting'),
            (2, 'Click Run Correlation', 'Engine executes, progress shown'),
            (3, 'View matched identities', 'Successfully correlated accounts listed'),
            (4, 'View orphan accounts', 'Accounts with no HR record match'),
            (5, 'Link orphan to HR record', 'Account linked, removed from orphan list'),
            (6, 'View conflicts', 'Mismatched attributes across systems'),
            (7, 'Resolve conflict: choose authoritative source', 'Conflict resolved'),
        ],
    },
    {
        'num': 17, 'title': 'TPRM (Third-Party Risk Management)', 'priority': 'P1',
        'desc': 'Vendor registry with risk tiering, assessments, issue tracking, and contract management. Dashboard shows vendor risk distribution and overdue assessments.',
        'config': [
            'Vendor risk tiers: Critical, High, Medium, Low',
            'Assessment questionnaires: configurable per vendor type',
            'Contract monitoring: expiry alerts',
        ],
        'url': '/tprm',
        'persona': 'P20 (Vendor Manager)',
        'steps': [
            (1, 'Navigate to TPRM > Vendors', 'Vendor list loads'),
            (2, 'Click Add Vendor', 'Vendor creation form opens'),
            (3, 'Fill: name="Acme Cloud", category=Cloud Provider, risk_tier=High', 'Form populated'),
            (4, 'Save', 'Vendor appears with "High" risk badge'),
            (5, 'Click vendor > Start Assessment', 'Assessment questionnaire opens'),
            (6, 'Complete and submit assessment', 'Risk score calculated, status = Submitted'),
            (7, 'Create vendor issue', 'Issue created with lifecycle tracking'),
            (8, 'Add vendor contract with dates and value', 'Contract listed, expiry monitored'),
            (9, 'View TPRM Dashboard', 'Vendor count, risk distribution, overdue assessments'),
        ],
    },
    {
        'num': 18, 'title': 'Fraud Detection & Case Management', 'priority': 'P0',
        'desc': 'Rule-based fraud detection with alert inbox, case management with investigation workflow, and fraud dashboard.',
        'config': [
            'Fraud rule types: transaction, behavioral, threshold',
            'Alert severity: Critical, High, Medium, Low',
            'Case lifecycle: Open > Investigating > Closed',
        ],
        'url': '/fraud',
        'persona': 'P06 (IT Security Admin)',
        'steps': [
            (1, 'Navigate to Fraud > Rules', 'Fraud rule list loads'),
            (2, 'Create Rule: name="Duplicate Payment", type=transaction, severity=High', 'Rule created'),
            (3, 'Enable/disable rule toggle', 'Toggle works'),
            (4, 'Navigate to Fraud > Alerts', 'Alert inbox loads'),
            (5, 'Click alert > view details', 'Triggered rule, transaction, user, amount, timestamp'),
            (6, 'Click Open Case from alert', 'Case creation form pre-populated with alert data'),
            (7, 'Navigate to Fraud > Cases', 'Case list loads'),
            (8, 'Create standalone case: title, description, severity', 'Case created with reference number'),
            (9, 'Add investigation notes, assign investigator', 'Notes saved, investigator assigned'),
            (10, 'Update status: Investigating > Closed, record outcome', 'Full audit trail recorded'),
            (11, 'View Fraud Dashboard', 'Open cases, active alerts, rules count, severity chart'),
        ],
    },
    {
        'num': 19, 'title': 'BCM (Business Continuity Management)', 'priority': 'P1',
        'desc': 'Business Impact Analysis (BIA), continuity plans, exercises, and incident activation with full lifecycle tracking.',
        'config': [
            'BIA parameters: RTO (Recovery Time Objective), RPO (Recovery Point Objective)',
            'Plan types: BCP, DR, Crisis Management',
            'Exercise types: Tabletop, Partial, Full',
        ],
        'url': '/bcm',
        'persona': 'P05 (Risk Manager)',
        'steps': [
            (1, 'Navigate to BCM > BIA', 'BIA list loads'),
            (2, 'Create BIA: process, RTO=4h, RPO=1h, impact=Critical', 'BIA record created'),
            (3, 'Navigate to BCM > Plans', 'Plan list loads'),
            (4, 'Create Plan: name="IT DR Plan", type=DR, priority=Critical', 'Plan created in Draft'),
            (5, 'Activate plan', 'Status changes to Active'),
            (6, 'Create Exercise: name, linked plan, type=Full, date', 'Exercise created'),
            (7, 'Record exercise outcome and lessons learned', 'Results saved'),
            (8, 'Navigate to BCM > Activations', 'Activation list loads'),
            (9, 'Activate Incident: linked plan, reason, severity=Critical', 'Activation created'),
            (10, 'Track recovery: Activated > Recovered > Closed', 'Full incident lifecycle recorded'),
        ],
    },
    {
        'num': 20, 'title': 'Whistleblower Portal', 'priority': 'P0',
        'desc': 'Anonymous reporting portal. Submissions and case tracking are PUBLIC (no authentication required). Investigators manage cases through authenticated inbox.',
        'config': [
            'Public routes: /whistleblower/submit and /whistleblower/intake (NO auth required)',
            'Protected routes: /whistleblower/inbox (investigator only)',
            'Reference codes: unique per submission for anonymous tracking',
            'Two-way anonymous messaging between submitter and investigator',
        ],
        'url': '/whistleblower/intake (public) | /whistleblower/inbox (protected)',
        'persona': 'Anonymous (public), P06 (IT Security / Investigator)',
        'steps': [
            (1, 'Navigate to /whistleblower/intake WITHOUT logging in', 'Page loads publicly, form visible'),
            (2, 'Fill: category=Fraud, description="Suspected invoice manipulation"', 'Form populated'),
            (3, 'Select priority=High, click Submit', 'Confirmation screen with unique reference code (e.g. WB-A1B2C3D4)'),
            (4, 'Save the reference code', 'Code displayed prominently'),
            (5, 'Enter reference code in tracking section', 'Case status shown (Open), submission details visible'),
            (6, 'Login as P06 (Investigator)', 'Investigator view'),
            (7, 'Navigate to /whistleblower/inbox', 'Submitted case visible in list'),
            (8, 'Click case, add investigator message', 'Message added to thread'),
            (9, 'Change case status to "Investigating"', 'Status updated'),
            (10, '(No login) Track case, see investigator message', 'Status shows "Investigating", message visible'),
            (11, 'Submit anonymous reply with additional details', 'Reply submitted'),
            (12, '(As P06) Refresh case, see anonymous reply', 'Reply visible in thread, sender shows "Submitter"'),
            (13, 'Close case with outcome notes', 'Case closed, full audit trail'),
        ],
    },
    {
        'num': 21, 'title': 'Surveys & Assessments', 'priority': 'P1',
        'desc': 'Create and distribute surveys with multiple question types. Track responses, view analytics, and export results.',
        'config': [
            'Question types: Multiple Choice, Rating (1-5), Free Text, Yes/No',
            'Survey lifecycle: Draft > Published > Distributed > Closed',
            'Distribution: select recipients from user list',
        ],
        'url': '/surveys',
        'persona': 'P02 (Tenant Admin) creates, P08 (Business User) responds',
        'steps': [
            (1, 'Navigate to Surveys > Designer', 'Survey list loads'),
            (2, 'Click Create Survey', 'Survey creation form opens'),
            (3, 'Fill: title="Security Assessment", add 3 questions (MC, Rating, Text)', 'Questions added'),
            (4, 'Save as Draft', 'Survey saved'),
            (5, 'Click Publish', 'Status changes to "Published"'),
            (6, 'Navigate to Distribution', 'Distribution page opens'),
            (7, 'Select recipients (P08, P07), click Distribute', 'Surveys sent to 2 recipients'),
            (8, 'Login as P08, view assigned survey', 'Survey visible in inbox'),
            (9, 'Answer all questions, click Submit', 'Toast "Survey submitted"'),
            (10, 'Login as P02, navigate to Analytics', 'Response rate, charts, and text responses shown'),
            (11, 'Export results to CSV', 'CSV file downloads'),
        ],
    },
    {
        'num': 22, 'title': 'Template Library', 'priority': 'P1',
        'desc': 'Pre-built template packs (42 day-one templates) for SoD rules, mitigations, workflows, controls, and risk scenarios. Activation wizard, copy-on-write editing, and update review.',
        'config': [
            'Day-one seeder: 42 templates loaded on startup (idempotent)',
            'Template types: SoD Rules, Mitigations, Workflows, Controls, Risk Scenarios',
            'Copy-on-write: first edit creates tenant-local copy',
            'Versioning: template packs support multiple versions with update review',
        ],
        'url': '/library',
        'persona': 'P02 (Tenant Admin), P01 (Platform Admin)',
        'steps': [
            (1, 'Navigate to Library > Content', 'Template packs visible (42+ from seeder)'),
            (2, 'Search and filter by category', 'Filter works'),
            (3, 'Click a pack to view items', 'Versioned items listed with descriptions'),
            (4, 'Navigate to Activation Wizard', 'Template selection for activation'),
            (5, 'Select a pack, preview items, click Activate', 'Items copied to tenant'),
            (6, 'Navigate to Active Content', 'Activated items visible'),
            (7, 'Edit an activated item', 'Copy-on-write: tenant-local copy created'),
            (8, 'Navigate to Update Review', 'Pending updates listed (if new version available)'),
            (9, 'Accept/Reject/Defer updates', 'Update actions recorded'),
            (10, 'Login as P01 (Platform Admin)', 'Platform admin sees all packs across tenants'),
        ],
    },
    {
        'num': 23, 'title': 'Reporting & Analytics', 'priority': 'P1',
        'desc': 'Report catalog with multiple report types. Run reports with parameters, drill-down to details, and export to CSV/PDF.',
        'config': [
            'Report types: SoD Violations, User Access, Role Usage, Certification Status, FF Activity, Risk Register, Compliance Status',
            'Export formats: CSV, PDF',
            'Dashboard widgets reflect live data',
        ],
        'url': '/reports',
        'persona': 'P02 (Tenant Admin)',
        'steps': [
            (1, 'Navigate to Reports', 'Report catalog loads with categories'),
            (2, 'Search reports', 'Filter works'),
            (3, 'Select "SoD Violations Summary"', 'Report config page opens'),
            (4, 'Set parameters: date range, scope', 'Parameters set'),
            (5, 'Click Generate/Run', 'Report executes, results displayed'),
            (6, 'Click a row to drill down', 'Detail view opens'),
            (7, 'Export to CSV', 'CSV file downloads'),
            (8, 'Export to PDF', 'PDF file downloads'),
            (9, 'Return to dashboard', 'Dashboard widgets reflect report data'),
        ],
    },
    {
        'num': 24, 'title': 'Platform Administration', 'priority': 'P1',
        'desc': 'Platform-level settings: tenant configuration, system settings, RBAC permissions, and audit trail. Platform admin has cross-tenant access.',
        'config': [
            'Platform admin: cross-tenant access requires platform_admin role',
            'Tenant settings: branding, session timeout, lockout threshold, CORS origins',
            'RBAC: role-based access control with granular permissions',
        ],
        'url': '/settings',
        'persona': 'P01 (Platform Admin), P02 (Tenant Admin)',
        'steps': [
            (1, 'Login as P01, navigate to Settings', 'Platform admin settings visible'),
            (2, 'View and modify system configuration', 'Settings form with current values'),
            (3, 'Change a setting (e.g., session timeout)', 'Setting updated'),
            (4, 'View audit trail', 'All admin actions logged with timestamps'),
            (5, 'Login as P02 (Tenant Admin)', 'Tenant-level settings only'),
            (6, 'View tenant settings', 'Tenant-specific config displayed'),
            (7, 'Modify tenant settings', 'Changes saved'),
            (8, 'Verify P02 cannot access platform-level settings', 'Platform settings not visible or blocked'),
        ],
    },
    {
        'num': 25, 'title': 'SAP Integration & Data Sync', 'priority': 'P1',
        'desc': 'SAP RFC connectivity for extracting users, roles, authorizations, and SoD-relevant data. Supports mock mode for testing and live mode for production.',
        'config': [
            'SAP_CONNECTOR_MODE: mock (default) or live',
            'SAP connection: SAP_HOST, SAP_SYSNR, SAP_CLIENT, SAP_USER, SAP_PASSWD',
            'SAP NW RFC SDK: required for live mode (install at /usr/local/sap/nwrfcsdk/)',
            'pyrfc: Python SAP RFC library (pip install pyrfc)',
            'RFC user: type Communication (C) or System (B) with S_RFC authorization',
            'Network: server must reach SAP on port 33XX (XX = system number)',
        ],
        'url': 'Backend configuration (no dedicated UI page)',
        'persona': 'P01 (Platform Admin)',
        'steps': [
            (1, 'Verify SAP NW RFC SDK installed', 'LD_LIBRARY_PATH set, pyrfc importable'),
            (2, 'Configure SAP connection in .env', 'SAP_HOST, SYSNR, CLIENT, USER, PASSWD set'),
            (3, 'Set SAP_CONNECTOR_MODE=live', 'Live mode enabled'),
            (4, 'Run connection test script', 'RFC_PING succeeds, system info returned'),
            (5, 'Extract user list from SAP (BAPI_USER_GETLIST)', 'User count returned, first users listed'),
            (6, 'Extract role list from SAP', 'Roles with descriptions returned'),
            (7, 'Extract user-role assignments', 'Assignment data returned'),
            (8, 'Run SoD analysis against real SAP data', 'Violations detected based on actual role assignments'),
            (9, 'Verify data synced to GovernexPlus database', 'Users and roles visible in UI'),
            (10, 'Test mock fallback: set SAP_CONNECTOR_MODE=mock', 'System works with simulated data'),
        ],
    },
]

for mod in modules:
    doc.add_heading(f'{mod["num"]}. Module {mod["num"]-3}: {mod["title"]}', level=1)

    # Priority badge
    p = doc.add_paragraph()
    run = p.add_run(f'Priority: {mod["priority"]}')
    run.bold = True
    if mod['priority'] == 'P0':
        run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
    else:
        run.font.color.rgb = RGBColor(0x00, 0x66, 0xCC)

    p = doc.add_paragraph()
    run = p.add_run(f'URL: ')
    run.bold = True
    p.add_run(mod['url'])

    p = doc.add_paragraph()
    run = p.add_run(f'Persona: ')
    run.bold = True
    p.add_run(mod['persona'])

    doc.add_heading('Description', level=2)
    doc.add_paragraph(mod['desc'])

    doc.add_heading('Configuration Requirements', level=2)
    for item in mod['config']:
        doc.add_paragraph(item, style='List Bullet')

    doc.add_heading('Test Steps', level=2)
    add_step_table(doc, mod['steps'])

    doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# CROSS-MODULE E2E WORKFLOWS
# ══════════════════════════════════════════════════════════════
doc.add_heading('26. Cross-Module E2E Workflows', level=1)
doc.add_paragraph(
    'These workflows prove the system works as a whole by chaining actions across multiple modules.'
)

workflows = [
    {
        'title': 'Workflow 1: Access Request > SoD Violation > Mitigation',
        'steps': [
            (1, 'P08 submits access request for role with SoD conflict', 'Request created with SoD warning'),
            (2, 'P07 approves despite warning', 'Request approved, violation created in ARA'),
            (3, 'P05 views violation in ARA dashboard', 'Violation visible with AI narrative'),
            (4, 'P05 attaches mitigation control', 'Mitigation linked to violation'),
            (5, 'Violation status changes to "Mitigated"', 'End-to-end flow complete'),
        ]
    },
    {
        'title': 'Workflow 2: JML Joiner > Certification > Revocation',
        'steps': [
            (1, 'HR triggers joiner event for Finance', 'Birthright roles auto-provisioned'),
            (2, 'P04 creates certification campaign', 'Campaign includes the new user'),
            (3, 'P07 reviews and revokes a role', 'Revocation queued'),
            (4, 'Role removed from user profile', 'Audit trail shows full lifecycle'),
        ]
    },
    {
        'title': 'Workflow 3: Firefighter > Audit Finding > Remediation',
        'steps': [
            (1, 'P06 requests emergency access', 'FF request created'),
            (2, 'P11 approves, P17 starts session', 'Session logged'),
            (3, 'P19 creates audit finding referencing FF session', 'Finding linked to session'),
            (4, 'Management action created and tracked', 'Full traceability'),
        ]
    },
    {
        'title': 'Workflow 4: Fraud Alert > Case > Whistleblower Correlation',
        'steps': [
            (1, 'Fraud rule triggers alert', 'Alert in inbox'),
            (2, 'P06 opens case from alert', 'Case created with alert data'),
            (3, 'Whistleblower submits related report', 'Anonymous submission received'),
            (4, 'Investigator links whistleblower report to fraud case', 'Cross-reference established'),
        ]
    },
    {
        'title': 'Workflow 5: Risk > Control > Testing > Deficiency',
        'steps': [
            (1, 'P05 creates risk in register', 'Risk with score'),
            (2, 'P14 creates control to mitigate risk', 'Control linked to risk'),
            (3, 'P10 tests control — fails', 'Deficiency auto-created'),
            (4, 'Remediation tracked through to closure', 'Risk score recalculated'),
        ]
    },
]

for wf in workflows:
    doc.add_heading(wf['title'], level=2)
    add_step_table(doc, wf['steps'])

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# SIGN-OFF
# ══════════════════════════════════════════════════════════════
doc.add_heading('27. UAT Sign-Off', level=1)
doc.add_paragraph(
    'By signing below, the undersigned confirms that User Acceptance Testing has been '
    'completed for GovernexPlus v1.0 and the results are as documented in this report.'
)

t = doc.add_table(rows=5, cols=4)
t.style = 'Light Grid Accent 1'
hdr = t.rows[0].cells
hdr[0].text = 'Role'
hdr[1].text = 'Name'
hdr[2].text = 'Signature'
hdr[3].text = 'Date'
for cell in hdr:
    cell.paragraphs[0].runs[0].bold = True

roles = ['Project Sponsor', 'Product Owner', 'QA Lead', 'Business Representative']
for i, role in enumerate(roles):
    t.rows[i + 1].cells[0].text = role

doc.add_paragraph()
doc.add_paragraph()

p = doc.add_paragraph()
run = p.add_run('Overall Result:  ')
run.bold = True
p.add_run('PASS / CONDITIONAL PASS / FAIL')

p = doc.add_paragraph()
run = p.add_run('Notes: ')
run.bold = True
p.add_run('_' * 60)

# ── Save ──────────────────────────────────────────────────────
output_path = 'd:/Governexplus/qa/GovernexPlus_UAT_Complete_Guide.docx'
doc.save(output_path)
print(f'Document saved to: {output_path}')
print(f'Modules: {len(modules)}')
print(f'Total test steps: {sum(len(m["steps"]) for m in modules)}')
print(f'Cross-module workflows: {len(workflows)}')
