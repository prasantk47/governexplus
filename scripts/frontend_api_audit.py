"""Cross-reference frontend API calls against server OpenAPI spec."""
import re

# Frontend endpoints extracted from the agent's analysis
FRONTEND_CALLS = """
POST /auth/login
POST /auth/logout
POST /auth/refresh
GET /auth/profile
GET /access-requests
GET /access-requests/{id}
POST /access-requests
POST /access-requests/{id}/submit
POST /access-requests/{id}/approve/{stepId}
POST /access-requests/{id}/reject/{stepId}
POST /access-requests/preview-risk
GET /access-requests/approvals/pending
GET /access-requests/my-requests
GET /access-requests/statistics
GET /access-requests/statistics/sla
POST /approvals/{id}/approve
POST /approvals/{id}/reject
GET /certification/campaigns
GET /certification/campaigns/{id}
POST /certification/campaigns
GET /certification/my-reviews
POST /certification/campaigns/{campaignId}/items/{itemId}/decision
POST /certification/campaigns/{campaignId}/bulk-certify
GET /privileged-access/reason-codes
GET /privileged-access/reason-codes/{code}
GET /privileged-access/firefighters
GET /privileged-access/firefighters/{id}/status
POST /privileged-access/requests
GET /privileged-access/requests
GET /privileged-access/requests/{id}
GET /privileged-access/requests/pending
POST /privileged-access/requests/{id}/approve
POST /privileged-access/requests/{id}/reject
GET /privileged-access/sessions
GET /privileged-access/sessions/active
GET /privileged-access/sessions/{id}
GET /privileged-access/sessions/{id}/credentials
POST /privileged-access/sessions/{id}/end
POST /privileged-access/sessions/{id}/revoke
POST /privileged-access/sessions/{id}/extend
POST /privileged-access/sessions/{sessionId}/activity
GET /privileged-access/sessions/{sessionId}/activities
GET /privileged-access/sessions/{sessionId}/controller-review
POST /privileged-access/sessions/{sessionId}/controller-review/start
POST /privileged-access/sessions/{sessionId}/controller-review/complete
POST /privileged-access/sessions/{id}/review
GET /privileged-access/reviews/pending
GET /privileged-access/sessions/{sessionId}/audit-evidence
GET /privileged-access/sessions/{sessionId}/audit-evidence/export
GET /privileged-access/audit/sessions
GET /privileged-access/statistics
POST /risk/analyze/user
POST /risk/analyze/batch
GET /risk/rules
GET /risk/rules/{id}
GET /risk/violations
POST /risk/simulate/add-role
PUT /risk-rules/custom/{id}
POST /risk-rules/custom
PUT /risk-rules/builtin/{id}/toggle
DELETE /risk-rules/custom/{id}
GET /users
GET /users/stats
GET /users/departments
GET /users/{userId}
POST /users
PUT /users/{userId}
DELETE /users/{userId}
GET /users/{userId}/roles
POST /users/{userId}/roles
DELETE /users/{userId}/roles/{roleId}
GET /users/{userId}/entitlements
GET /users/{userId}/transactions
GET /users/{userId}/risk-profile
POST /users/{userId}/recalculate-risk
GET /role-studio/roles
GET /role-studio/roles/{roleId}
POST /role-studio/roles
PUT /role-studio/roles/{roleId}
POST /role-studio/roles/{roleId}/test
GET /role-studio/catalog
DELETE /role-studio/roles/{roleId}
GET /reporting/reports
GET /reporting/reports/{reportId}
POST /reporting/reports/{reportId}/execute
GET /reporting/reports/{reportId}/export
GET /reports/dashboard-summary
GET /dashboard/stats
GET /dashboard/summary/risk
GET /dashboard/summary/certification
GET /dashboard/summary/firefighter
POST /ai/risk/analyze
POST /ai/query
POST /ai/roles/mine
POST /ai/remediation/plan
POST /ai/chat
GET /security-controls/controls
GET /security-controls/controls/{controlId}
POST /security-controls/controls
PUT /security-controls/controls/{controlId}
DELETE /security-controls/controls/{controlId}
GET /security-controls/controls/categories
GET /security-controls/controls/business-areas
GET /security-controls/controls/{controlId}/mappings
POST /security-controls/controls/{controlId}/mappings
POST /security-controls/controls/{controlId}/evaluate
POST /security-controls/evaluate/batch
POST /security-controls/evaluate/parameters
GET /security-controls/evaluations
GET /security-controls/evaluations/report/{systemId}
POST /security-controls/exceptions
GET /security-controls/exceptions
POST /security-controls/exceptions/{exceptionId}/approve
GET /security-controls/systems
GET /security-controls/systems/{systemId}
GET /security-controls/dashboard
POST /security-controls/import
POST /security-controls/import/file
GET /security-controls/export
GET /security-controls/import/template
GET /security-controls/templates
POST /security-controls/templates/{controlId}/adopt
POST /security-controls/seed-defaults
GET /audit/logs
GET /audit/logs/actions
GET /audit/logs/user/{userId}
GET /audit/logs/target/{targetType}/{targetId}
GET /audit/reports/summary
POST /audit/reports/compliance
GET /audit/export/csv
GET /approver-management
GET /approver-management/stats
GET /approver-management/types
GET /approver-management/{approverId}
POST /approver-management
PUT /approver-management/{approverId}
DELETE /approver-management/{approverId}
POST /approver-management/{approverId}/toggle-availability
POST /approver-management/{approverId}/set-ooo
POST /approver-management/{approverId}/clear-ooo
GET /access-lifecycle/catalog
POST /access-lifecycle/cart
POST /access-lifecycle/cart/{cartId}/add
POST /access-lifecycle/cart/{cartId}/check-conflicts
POST /access-lifecycle/cart/{cartId}/submit
GET /access-lifecycle/cart/{cartId}
DELETE /access-lifecycle/cart/{cartId}/items/{roleId}
GET /workflows/builder/palette
POST /workflows/builder/validate
POST /workflows/builder/preview
POST /workflows/builder/export
GET /workflows/builder/templates
GET /workflows/builder/templates/{name}
GET /settings/smtp
PUT /settings/smtp
POST /settings/smtp/test
DELETE /settings/smtp
GET /risk-management/risks
GET /risk-management/risks/{id}
POST /risk-management/risks
PUT /risk-management/risks/{id}
DELETE /risk-management/risks/{id}
POST /risk-management/risks/{riskId}/assessments
GET /risk-management/risks/{riskId}/assessments
PUT /risk-management/assessments/{id}/submit
PUT /risk-management/assessments/{id}/review
POST /risk-management/assessment-campaigns
POST /risk-management/appetites
GET /risk-management/appetites
GET /risk-management/risks/{riskId}/appetite-check
POST /risk-management/kris
GET /risk-management/kris/dashboard
POST /risk-management/kris/{kriId}/measurements
GET /risk-management/kris/{kriId}/history
POST /risk-management/risks/{riskId}/responses
GET /risk-management/risks/{riskId}/responses
PUT /risk-management/responses/{id}/status
POST /risk-management/incidents
PUT /risk-management/incidents/{id}
GET /risk-management/incidents
POST /risk-management/incidents/{id}/link-risk
GET /risk-management/heatmap
GET /risk-management/trends
GET /risk-management/top-risks
GET /risk-management/overdue-reviews
POST /risk-management/risks/{riskId}/review-attestation
GET /audit-management/entities
POST /audit-management/entities
PUT /audit-management/entities/{id}
POST /audit-management/entities/{id}/compute-risk
GET /audit-management/plans
GET /audit-management/plans/{id}
POST /audit-management/plans
PUT /audit-management/plans/{id}
PUT /audit-management/plans/{id}/submit
PUT /audit-management/plans/{id}/approve
POST /audit-management/plans/generate-risk-based
GET /audit-management/engagements
GET /audit-management/engagements/{id}
POST /audit-management/engagements
PUT /audit-management/engagements/{id}
PUT /audit-management/engagements/{id}/advance
GET /audit-management/findings
POST /audit-management/engagements/{engId}/findings
PUT /audit-management/findings/{id}
PUT /audit-management/findings/{id}/management-response
POST /audit-management/findings/{id}/link-risk
POST /audit-management/findings/{id}/link-control
POST /audit-management/findings/{findingId}/actions
PUT /audit-management/actions/{id}
PUT /audit-management/actions/{id}/close
GET /audit-management/actions/overdue
POST /audit-management/actions/escalate
GET /audit-management/dashboard
GET /audit-management/committee-report
GET /audit-management/engagements/{id}/report
GET /process-control/controls
GET /process-control/controls/{id}
POST /process-control/controls
PUT /process-control/controls/{id}
PUT /process-control/controls/{id}/retire
POST /process-control/controls/{controlId}/tests
PUT /process-control/tests/{testId}/result
GET /process-control/controls/{controlId}/tests
GET /process-control/deficiencies
POST /process-control/deficiencies
PUT /process-control/deficiencies/{id}
PUT /process-control/deficiencies/{id}/remediate
PUT /process-control/deficiencies/{id}/verify
POST /process-control/self-assessment-campaigns
PUT /process-control/self-assessments/{id}/submit
GET /process-control/self-assessments/pending
GET /process-control/ccm-rules
POST /process-control/ccm-rules
POST /process-control/ccm-rules/{ruleId}/execute
POST /process-control/ccm/run-all
GET /process-control/ccm/dashboard
POST /process-control/evidence
GET /process-control/evidence
GET /process-control/evidence/{id}
PUT /process-control/evidence/{id}/legal-hold
POST /process-control/signoffs
PUT /process-control/signoffs/{id}/submit
GET /process-control/signoffs/hierarchy
GET /process-control/signoffs/pending
GET /process-control/dashboard
GET /process-control/controls/{controlId}/audit-package
GET /process-control/frameworks/{frameworkId}/coverage
GET /provisioning/connector-types
GET /provisioning/connectors
GET /provisioning/connectors/{connectorId}
POST /provisioning/connectors
DELETE /provisioning/connectors/{connectorId}
POST /provisioning/connectors/{connectorId}/connect
POST /provisioning/connectors/{connectorId}/disconnect
POST /provisioning/connectors/{connectorId}/test
GET /provisioning/connectors/{connectorId}/users
GET /provisioning/connectors/{connectorId}/users/{userId}
GET /provisioning/connectors/{connectorId}/users/{userId}/roles
GET /provisioning/connectors/{connectorId}/roles
POST /provisioning/provision/user
POST /provisioning/provision/roles/assign
POST /provisioning/provision/roles/revoke
POST /provisioning/provision/deprovision
GET /provisioning/tasks
GET /provisioning/tasks/{taskId}
POST /provisioning/tasks/{taskId}/cancel
GET /provisioning/queue/status
POST /provisioning/queue/start
POST /provisioning/queue/stop
POST /provisioning/queue/tasks/{taskId}/retry
POST /provisioning/tasks/retry-failed
GET /library/pack-builder
POST /library/packs/export
GET /library/stats
GET /library/items
POST /library/items/{itemId}/activate
POST /library/items/{itemId}/deactivate
GET /mass-admin/jobs
POST /mass-admin/jobs
GET /mass-admin/jobs/{jobId}
POST /mass-admin/jobs/{jobId}/cancel
GET /fraud/cases
POST /fraud/cases
PUT /fraud/cases/{id}
GET /jml/policies
POST /jml/policies
PUT /jml/policies/{id}
PATCH /jml/policies/{id}
GET /tprm/vendors
POST /bcm/plans
GET /bcm/plans
POST /bcm/exercises
GET /workflows/builder/palette
GET /identity-correlation/stats
GET /identity-correlation/clusters
GET /identity-correlation/orphans
GET /frameworks
GET /admin/dashboard/stats
GET /admin/tenants
GET /admin/activities
POST /admin/tenants/{tenantId}/suspend
POST /admin/tenants/{tenantId}/activate
POST /whistleblower/submit
GET /whistleblower/status/{ref}
POST /survey/surveys
GET /survey/surveys
PUT /survey/surveys/{id}
DELETE /survey/surveys/{id}
""".strip()

# Parse server paths
server_paths = {}
with open('d:/Governexplus/scripts/server_paths.txt') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        parts = line.split(' ')
        path = parts[-1]
        methods = parts[:-1]
        for m in methods:
            server_paths.setdefault(path, set()).add(m)

# Normalize path: replace {anything} with {_}
def normalize(path):
    return re.sub(r'\{[^}]+\}', '{_}', path)

# Build normalized server lookup
server_normalized = {}
for path, methods in server_paths.items():
    norm = normalize(path)
    server_normalized.setdefault(norm, set()).update(methods)

# Parse frontend calls
missing = []
found = []
method_mismatch = []

for line in FRONTEND_CALLS.split('\n'):
    line = line.strip()
    if not line:
        continue
    parts = line.split(' ', 1)
    method = parts[0]
    path = parts[1]
    norm = normalize(path)

    if norm in server_normalized:
        if method in server_normalized[norm]:
            found.append((method, path))
        else:
            method_mismatch.append((method, path, server_normalized[norm]))
    else:
        missing.append((method, path))

print(f"=== FRONTEND API AUDIT ===\n")
print(f"Total frontend calls: {len(found) + len(missing) + len(method_mismatch)}")
print(f"Matched:              {len(found)}")
print(f"Missing on server:    {len(missing)}")
print(f"Method mismatch:      {len(method_mismatch)}")

if missing:
    print(f"\n--- MISSING ENDPOINTS ({len(missing)}) ---")
    print("These frontend API calls have NO matching server endpoint:\n")
    for method, path in sorted(missing, key=lambda x: x[1]):
        print(f"  {method:6s} {path}")

if method_mismatch:
    print(f"\n--- METHOD MISMATCHES ({len(method_mismatch)}) ---")
    print("Frontend calls with wrong HTTP method:\n")
    for method, path, server_methods in sorted(method_mismatch, key=lambda x: x[1]):
        print(f"  {method:6s} {path}  (server has: {', '.join(sorted(server_methods))})")

print(f"\n--- MATCHED ({len(found)}) ---")
for method, path in sorted(found, key=lambda x: x[1]):
    print(f"  {method:6s} {path}")
