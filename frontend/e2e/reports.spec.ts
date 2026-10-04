/**
 * J12 — Reports: All 101
 * TC-RPT-001 through TC-RPT-101
 *
 * Backend design:
 *   reports.router prefix /reports — has GET /{report_id} (by slug), POST /{id}/run, GET /{id}/download
 *   reporting.router prefix /reporting — has POST /schedules, GET /schedules, POST /quick/sod-violations
 *
 * DEF-004 MAJ: 101 named report slugs may 404 if not pre-seeded in the DB.
 * Each test:
 *   1. GET /reports/{slug}  — expects 200 (fails with 404 if not seeded → DEF-004)
 *   2. GET /reporting/reports/{slug}/download?format=csv — expects 200
 *   3. XLSX export
 *   4. PDF export
 *
 * Export tests DO NOT accept 501 — if the guide mandates exports, 501 IS a defect.
 */
import { test, expect } from '@playwright/test';
import { getToken, apiGet } from './helpers';

const BASE_URL = 'http://localhost:9000';

// Report catalog: [slug, display_name, allowed_persona]
const REPORTS: Array<[string, string, 'P03' | 'P04' | 'P05' | 'P06' | 'P09' | 'P10' | 'P19' | 'P20']> = [
  // ARA / SoD (001-015)
  ['sod-violations', 'SoD Violations Summary', 'P06'],
  ['sod-violations-by-rule', 'Violations by Rule', 'P06'],
  ['sod-violations-by-user', 'Violations by User', 'P06'],
  ['sod-violations-trend', 'Violations Trend', 'P04'],
  ['mitigation-effectiveness', 'Mitigation Effectiveness', 'P04'],
  ['open-vs-remediated', 'Open vs Remediated', 'P04'],
  ['role-sod-risk', 'Role-Level SoD Risk', 'P06'],
  ['sod-ruleset-coverage', 'SoD Ruleset Coverage', 'P06'],
  ['top-violated-rules', 'Top Violated Rules', 'P04'],
  ['cross-system-sod', 'Cross-System SoD', 'P06'],
  ['sod-simulation', 'SoD Simulation', 'P06'],
  ['access-risk-by-department', 'Risk by Department', 'P04'],
  ['orphaned-accounts', 'Orphaned Accounts', 'P06'],
  ['dormant-users', 'Dormant Users', 'P06'],
  ['access-pattern-anomalies', 'Access Anomalies', 'P03'],
  // ARM (016-023)
  ['pending-approvals-aging', 'Pending Approvals Aging', 'P06'],
  ['request-volume', 'Request Volume', 'P06'],
  ['approval-sla', 'Approval SLA', 'P06'],
  ['rejection-analysis', 'Rejection Analysis', 'P06'],
  ['auto-approved-vs-manual', 'Auto vs Manual', 'P06'],
  ['provisioning-lag', 'Provisioning Lag', 'P06'],
  ['requests-by-role', 'Requests by Role', 'P06'],
  ['high-risk-requests', 'High-Risk Requests', 'P06'],
  // EAM (024-031)
  ['ff-activity', 'FF Activity Log', 'P03'],
  ['ff-usage-by-id', 'FF Usage by ID', 'P03'],
  ['ff-controller-signoff', 'Controller Sign-Off', 'P03'],
  ['ff-overdue-reviews', 'Overdue Reviews', 'P03'],
  ['ff-session-duration', 'Session Duration', 'P03'],
  ['ff-transactions', 'Transactions by Session', 'P03'],
  ['ff-critical-tcodes', 'Critical Tcodes', 'P03'],
  ['ff-id-inventory', 'FF ID Inventory', 'P03'],
  // Certification (032-039)
  ['certification-completion', 'Campaign Completion', 'P04'],
  ['certification-by-reviewer', 'By Reviewer', 'P04'],
  ['overdue-certifications', 'Overdue Certs', 'P04'],
  ['certification-revocations', 'Revocations', 'P04'],
  ['certification-comparison', 'Campaign Comparison', 'P04'],
  ['self-certification', 'Self-Certification', 'P04'],
  ['sod-in-certifications', 'SoD in Certs', 'P04'],
  ['certification-coverage', 'Cert Coverage', 'P04'],
  // JML (040-047)
  ['jml-hire-sla', 'New Hire SLA', 'P04'],
  ['jml-termination-sla', 'Termination SLA', 'P04'],
  ['jml-transfer-recert', 'Transfer Re-Cert', 'P04'],
  ['jml-orphaned-post-transfer', 'Orphaned Post-Transfer', 'P04'],
  ['jml-event-volume', 'JML Event Volume', 'P04'],
  ['jml-role-mapping', 'Role Mapping by Job', 'P06'],
  ['jml-dept-profile', 'Department Profile', 'P06'],
  ['jml-compliance-score', 'JML Compliance Score', 'P04'],
  // BRM (048-053)
  ['role-inventory', 'Role Inventory', 'P06'],
  ['role-assignment', 'Role Assignment', 'P06'],
  ['role-comparison', 'Role Comparison', 'P06'],
  ['composite-role-usage', 'Composite Role Usage', 'P06'],
  ['role-mining', 'Role Mining', 'P06'],
  ['role-cleanup', 'Role Clean-Up', 'P06'],
  // Risk Management (054-065)
  ['risk-register', 'Risk Register', 'P05'],
  ['risk-heatmap', 'Risk Heatmap', 'P05'],
  ['risk-by-category', 'Risk by Category', 'P05'],
  ['risk-trend', 'Risk Trend', 'P05'],
  ['kri-dashboard', 'KRI Dashboard', 'P05'],
  ['kri-breaches', 'KRI Breaches', 'P05'],
  ['incident-log', 'Incident Log', 'P05'],
  ['risk-by-owner', 'Risk by Owner', 'P05'],
  ['top-risks', 'Top 10 Risks', 'P05'],
  ['residual-risk', 'Residual Risk', 'P05'],
  ['risk-treatment', 'Risk Treatment', 'P05'],
  ['risk-appetite', 'Risk Appetite', 'P05'],
  // Process Control (066-073)
  ['control-inventory', 'Control Inventory', 'P10'],
  ['control-testing', 'Control Test Results', 'P10'],
  ['deficiency-tracker', 'Deficiency Tracker', 'P10'],
  ['control-effectiveness', 'Control Effectiveness', 'P10'],
  ['overdue-tests', 'Overdue Tests', 'P10'],
  ['deficiency-aging', 'Deficiency Aging', 'P10'],
  ['ccm-monitoring', 'CCM Monitoring', 'P10'],
  ['sox-itgc-coverage', 'SOX ITGC Coverage', 'P04'],
  // Audit Management (074-079)
  ['audit-plan', 'Audit Plan Status', 'P19'],
  ['audit-findings', 'Audit Findings', 'P19'],
  ['finding-closure', 'Finding Closure Rate', 'P19'],
  ['audit-engagement', 'Audit Engagement', 'P19'],
  ['findings-by-risk', 'Findings by Risk', 'P19'],
  ['outstanding-remediation', 'Outstanding Remediation', 'P19'],
  // Compliance (080-083)
  ['framework-coverage', 'Framework Coverage', 'P04'],
  ['compliance-posture', 'Compliance Posture', 'P04'],
  ['policy-attestation', 'Policy Attestation', 'P04'],
  ['compliance-gaps', 'Compliance Gaps', 'P04'],
  // TPRM (084-089)
  ['vendor-inventory', 'Vendor Inventory', 'P20'],
  ['assessment-completion', 'Assessment Completion', 'P20'],
  ['vendor-risk-distribution', 'Vendor Risk Distribution', 'P20'],
  ['fourth-party-risk', 'Fourth-Party Risk', 'P20'],
  ['overdue-reassessments', 'Overdue Reassessments', 'P20'],
  ['vendor-sla', 'Vendor SLA', 'P20'],
  // BCM (090-093)
  ['bia-summary', 'BIA Summary', 'P05'],
  ['bcm-plan-test', 'BCM Plan Test', 'P05'],
  ['rto-rpo', 'RTO/RPO Achievement', 'P05'],
  ['critical-assets', 'Critical Assets', 'P05'],
  // Fraud (094-097)
  ['fraud-alerts', 'Fraud Alerts', 'P05'],
  ['fraud-cases', 'Fraud Cases', 'P05'],
  ['fraud-rule-effectiveness', 'Fraud Rule Effectiveness', 'P05'],
  ['alert-to-case', 'Alert-to-Case Rate', 'P05'],
  // Survey (098-099)
  ['survey-responses', 'Survey Responses', 'P04'],
  ['survey-completion', 'Survey Completion', 'P04'],
  // Template Library (100-101)
  ['library-adoption', 'Library Adoption', 'P03'],
  ['pack-import-history', 'Pack Import History', 'P03'],
];

for (let i = 0; i < REPORTS.length; i++) {
  const [slug, name, persona] = REPORTS[i];
  const tc = String(i + 1).padStart(3, '0');

  test(`TC-RPT-${tc}: ${name} — render + exports`, async () => {
    const token = await getToken(persona);

    // 1. Render — GET /reports/{slug}
    // Will 404 until DEF-004 (report catalog seeding) is fixed
    const renderRes = await fetch(`${BASE_URL}/reports/${slug}`, {
      headers: { Authorization: `Bearer ${token}`, 'X-Tenant-ID': 'qa-tenant-001' },
    });
    expect(renderRes.status, `${name}: render`).toBe(200);

    // 2. CSV export — GET /reporting/reports/{slug}/download?format=csv
    const csvRes = await fetch(`${BASE_URL}/reporting/reports/${slug}/download?format=csv`, {
      headers: { Authorization: `Bearer ${token}`, 'X-Tenant-ID': 'qa-tenant-001' },
    });
    expect(csvRes.status, `${name}: CSV export`).toBe(200);
    const csvCt = csvRes.headers.get('content-type') || '';
    expect(csvCt, `${name}: CSV content-type`).toMatch(/csv|text/i);

    // 3. XLSX export
    const xlsxRes = await fetch(`${BASE_URL}/reporting/reports/${slug}/download?format=xlsx`, {
      headers: { Authorization: `Bearer ${token}`, 'X-Tenant-ID': 'qa-tenant-001' },
    });
    expect(xlsxRes.status, `${name}: XLSX export`).toBe(200);

    // 4. PDF export
    const pdfRes = await fetch(`${BASE_URL}/reporting/reports/${slug}/download?format=pdf`, {
      headers: { Authorization: `Bearer ${token}`, 'X-Tenant-ID': 'qa-tenant-001' },
    });
    expect(pdfRes.status, `${name}: PDF export`).toBe(200);
  });
}

// RBAC: P09 External Auditor can read SoD violations report
test('TC-RPT-RBAC: P09 External Auditor can read sod-violations report', async () => {
  const token = await getToken('P09');
  const res = await fetch(`${BASE_URL}/reports/sod-violations`, {
    headers: { Authorization: `Bearer ${token}`, 'X-Tenant-ID': 'qa-tenant-001' },
  });
  expect(res.status).toBe(200);
});

// RBAC: P08 Business User cannot access SoD violation reports
test('TC-RPT-RBAC-DENY: P08 Business User cannot read SoD violation reports', async () => {
  const token = await getToken('P08');
  const res = await fetch(`${BASE_URL}/reports/sod-violations`, {
    headers: { Authorization: `Bearer ${token}`, 'X-Tenant-ID': 'qa-tenant-001' },
  });
  expect(res.status).toBe(403);
});
