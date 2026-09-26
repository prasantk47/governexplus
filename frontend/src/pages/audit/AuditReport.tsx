import { useState, Fragment } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ClipboardDocumentListIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  UserGroupIcon,
  ArrowDownTrayIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  UserIcon,
  KeyIcon,
} from '@heroicons/react/24/outline';
import { auditApi } from '../../services/api';
import {
  PageHeader,
  Card,
  SearchInput,
  Select,
  Badge,
  LoadingState,
  ErrorState,
  EmptyState,
  Pagination,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';

// ============================================================================
// Constants
// ============================================================================

const CATEGORY_OPTIONS = [
  { value: '', label: 'All Categories' },
  { value: 'user', label: 'User Management' },
  { value: 'role', label: 'Role Management' },
  { value: 'risk', label: 'Risk & Violations' },
  { value: 'firefighter', label: 'Privileged Access' },
  { value: 'approver', label: 'Approver Management' },
  { value: 'system', label: 'System / Rules' },
];

const TARGET_TYPE_OPTIONS = [
  { value: '', label: 'All Targets' },
  { value: 'User', label: 'User' },
  { value: 'Role', label: 'Role' },
  { value: 'Approver', label: 'Approver' },
  { value: 'firefighter', label: 'Privileged Access ID' },
  { value: 'firefighter_session', label: 'Privileged Access Session' },
  { value: 'user', label: 'User (risk)' },
];

const DATE_RANGE_OPTIONS = [
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: '90', label: 'Last 90 days' },
  { value: '180', label: 'Last 6 months' },
  { value: '365', label: 'Last year' },
];

const ACTION_LABELS: Record<string, string> = {
  user_login: 'User Login',
  user_logout: 'User Logout',
  user_created: 'User Created',
  user_modified: 'User Modified',
  user_deleted: 'User Deleted',
  user_locked: 'User Locked',
  user_unlocked: 'User Unlocked',
  role_assigned: 'Role Assigned',
  role_removed: 'Role Removed',
  role_created: 'Role Created',
  role_modified: 'Role Modified',
  risk_analysis_run: 'Risk Analysis Run',
  violation_detected: 'Violation Detected',
  violation_mitigated: 'Violation Mitigated',
  violation_remediated: 'Violation Remediated',
  ff_request_submitted: 'FF Request Submitted',
  ff_request_approved: 'FF Request Approved',
  ff_request_rejected: 'FF Request Rejected',
  ff_session_started: 'FF Session Started',
  ff_session_ended: 'FF Session Ended',
  ff_session_revoked: 'FF Session Revoked',
  ff_activity_logged: 'FF Activity Logged',
  approver_created: 'Approver Created',
  approver_modified: 'Approver Modified',
  approver_deleted: 'Approver Deleted',
  approver_ooo_set: 'Approver OOO',
  approver_availability_toggled: 'Availability Toggled',
  system_config_changed: 'Config Changed',
  rule_created: 'Rule Created',
  rule_modified: 'Rule Modified',
  report_generated: 'Report Generated',
  data_export: 'Data Export',
  data_import: 'Data Import',
};

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';

const COLOR_MAP: Record<string, BadgeVariant> = {
  blue: 'info', indigo: 'info', cyan: 'info', purple: 'info',
  green: 'success', emerald: 'success',
  yellow: 'warning', amber: 'warning', orange: 'warning',
  red: 'danger',
  gray: 'neutral', grey: 'neutral',
};

function toBadgeVariant(color: string | undefined): BadgeVariant {
  if (!color) return 'neutral';
  return COLOR_MAP[color] ?? 'neutral';
}

const ACTION_BADGE_COLORS: Record<string, string> = {
  user_login: 'blue', user_logout: 'gray',
  user_created: 'green', user_modified: 'yellow', user_deleted: 'red',
  user_locked: 'red', user_unlocked: 'green',
  role_assigned: 'green', role_removed: 'red',
  role_created: 'green', role_modified: 'yellow',
  risk_analysis_run: 'purple',
  violation_detected: 'red', violation_mitigated: 'yellow', violation_remediated: 'green',
  ff_request_submitted: 'blue', ff_request_approved: 'green', ff_request_rejected: 'red',
  ff_session_started: 'orange', ff_session_ended: 'gray', ff_session_revoked: 'red',
  ff_activity_logged: 'blue',
  approver_created: 'green', approver_modified: 'yellow', approver_deleted: 'red',
  approver_ooo_set: 'orange', approver_availability_toggled: 'cyan',
  system_config_changed: 'purple', rule_created: 'green', rule_modified: 'yellow',
  report_generated: 'blue', data_export: 'indigo', data_import: 'indigo',
};

const DETAIL_KEY_LABELS: Record<string, string> = {
  ooo_until: 'OOO Until',
  delegate_id: 'Delegate',
  reason: 'Reason / Justification',
  approved_by: 'Approved By',
  is_available: 'Available',
  action: 'Action',
  previous_ooo: 'Previous OOO',
  role_id: 'Role ID',
  role_name: 'Role Name',
  request_id: 'Request ID',
  firefighter_id: 'Privileged Access ID',
  rule_id: 'Rule ID',
  rule_name: 'Rule Name',
  severity: 'Severity',
  session_id: 'Session ID',
  action_type: 'Activity Type',
};

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function formatDetailValue(key: string, value: any): string {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (key.includes('until') || key.includes('date') || key.includes('_at')) {
    try { return formatTimestamp(String(value)); } catch { return String(value); }
  }
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
}

// ============================================================================
// Detail Panel — renders expanded row with action-specific formatting
// ============================================================================

function DetailPanel({ log }: { log: any }) {
  const details = log.details;
  const oldValues = log.old_values;
  const newValues = log.new_values;
  const action = log.action as string;

  const hasDetails = details && Object.keys(details).length > 0;
  const hasChanges = (oldValues && Object.keys(oldValues).length > 0) ||
    (newValues && Object.keys(newValues).length > 0);

  const isOOO = action === 'approver_ooo_set';
  const isOOOClear = isOOO && details?.action === 'cleared';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Left: Event Info */}
      <div className="space-y-3">
        <div className="glass-card rounded-lg p-3">
          <div className="text-xs font-medium text-white/60 mb-2">Event Summary</div>
          <div className="space-y-1.5 text-xs">
            <div className="flex gap-2">
              <UserIcon className="h-3.5 w-3.5 text-white/40 mt-0.5 shrink-0" />
              <span className="text-white/50">Performed by:</span>
              <span className="text-white font-medium">
                {log.actor_username || log.actor_user_id || 'System'}
              </span>
              {log.actor_type && log.actor_type !== 'user' && (
                <Badge variant="neutral">{log.actor_type}</Badge>
              )}
            </div>
            {(log.target_name || log.target_id) && (
              <div className="flex gap-2">
                <KeyIcon className="h-3.5 w-3.5 text-white/40 mt-0.5 shrink-0" />
                <span className="text-white/50">Target:</span>
                <span className="text-white">{log.target_name || log.target_id}</span>
                {log.target_type && (
                  <span className="text-white/40">({log.target_type})</span>
                )}
              </div>
            )}
            <div className="flex gap-2">
              <ClockIcon className="h-3.5 w-3.5 text-white/40 mt-0.5 shrink-0" />
              <span className="text-white/50">When:</span>
              <span className="text-white">{formatTimestamp(log.timestamp)}</span>
            </div>
          </div>
        </div>

        {log.compliance_relevant && (
          <div className="glass-card rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <ShieldCheckIcon className="h-4 w-4 text-blue-400" />
              <span className="text-xs font-medium text-blue-400">Compliance Relevant</span>
            </div>
            {log.compliance_tags?.length > 0 && (
              <div className="flex gap-1.5 mt-1.5">
                {log.compliance_tags.map((tag: string) => (
                  <Badge key={tag} variant="info">{tag}</Badge>
                ))}
              </div>
            )}
          </div>
        )}

        {!log.success && log.error_message && (
          <div className="glass-card rounded-lg p-3 border border-red-500/20">
            <div className="flex items-center gap-2 mb-1">
              <XCircleIcon className="h-4 w-4 text-red-400" />
              <span className="text-xs font-medium text-red-400">Error</span>
            </div>
            <p className="text-xs text-red-300/80 mt-1">{log.error_message}</p>
          </div>
        )}
      </div>

      {/* Right: Details & Changes */}
      <div className="space-y-3">
        {/* OOO-specific rendering */}
        {isOOO && hasDetails && (
          <div className="glass-card rounded-lg p-3">
            <div className="text-xs font-medium text-white/60 mb-2">
              {isOOOClear ? 'OOO Cleared' : 'Out-of-Office Details'}
            </div>
            {isOOOClear ? (
              <div className="space-y-2 text-xs">
                <div className="flex items-center gap-2 text-green-400">
                  <CheckCircleIcon className="h-3.5 w-3.5" />
                  <span>OOO status has been cleared</span>
                </div>
                {details.previous_ooo && (
                  <div className="mt-2 pl-2 border-l-2 border-white/10 space-y-1">
                    <div className="text-white/40 font-medium mb-1">Previous OOO:</div>
                    {Object.entries(details.previous_ooo).map(([k, v]) => (
                      <div key={k} className="flex gap-2">
                        <span className="text-white/40 min-w-[100px]">{DETAIL_KEY_LABELS[k] || k}:</span>
                        <span className="text-white/70">{formatDetailValue(k, v)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-2 text-xs">
                {details.reason && (
                  <div className="p-2 rounded bg-yellow-500/10 border border-yellow-500/20">
                    <div className="text-yellow-400/80 font-medium mb-0.5">Reason</div>
                    <div className="text-white/80">{details.reason}</div>
                  </div>
                )}
                {details.approved_by && (
                  <div className="flex gap-2">
                    <span className="text-white/50">Approved by:</span>
                    <span className="text-white font-medium">{details.approved_by}</span>
                  </div>
                )}
                {details.delegate_id && (
                  <div className="flex gap-2">
                    <span className="text-white/50">Delegated to:</span>
                    <span className="text-white font-medium">{details.delegate_id}</span>
                  </div>
                )}
                {details.ooo_until && (
                  <div className="flex gap-2">
                    <span className="text-white/50">Until:</span>
                    <span className="text-white">{formatDetailValue('ooo_until', details.ooo_until)}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Generic details for non-OOO actions */}
        {hasDetails && !isOOO && (
          <div className="glass-card rounded-lg p-3">
            <div className="text-xs font-medium text-white/60 mb-2">Details</div>
            <div className="space-y-1.5 text-xs">
              {Object.entries(details).map(([key, value]) => (
                <div key={key} className="flex items-start gap-2">
                  <span className="text-white/40 min-w-[120px] shrink-0">
                    {DETAIL_KEY_LABELS[key] || key}:
                  </span>
                  <span className="text-white/80 break-all">
                    {formatDetailValue(key, value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Change tracking (old → new values) */}
        {hasChanges && (
          <div className="glass-card rounded-lg overflow-hidden">
            <div className="text-xs font-medium text-white/60 p-3 pb-2">Changes (Before → After)</div>
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left px-3 py-1.5 text-white/40 font-medium">Field</th>
                  <th className="text-left px-3 py-1.5 text-white/40 font-medium">Before</th>
                  <th className="text-left px-3 py-1.5 text-white/40 font-medium">After</th>
                </tr>
              </thead>
              <tbody>
                {(() => {
                  const allKeys = new Set([
                    ...Object.keys(oldValues || {}),
                    ...Object.keys(newValues || {}),
                  ]);
                  return Array.from(allKeys).map((key) => {
                    const oldVal = oldValues?.[key];
                    const newVal = newValues?.[key];
                    const changed = JSON.stringify(oldVal) !== JSON.stringify(newVal);
                    return (
                      <tr key={key} className={`border-b border-white/5 ${changed ? 'bg-white/[0.02]' : ''}`}>
                        <td className="px-3 py-1.5 text-white/60 font-mono">{key}</td>
                        <td className="px-3 py-1.5 text-red-400/70">
                          {oldVal !== undefined ? formatDetailValue(key, oldVal) : '-'}
                        </td>
                        <td className="px-3 py-1.5 text-green-400/70">
                          {newVal !== undefined ? formatDetailValue(key, newVal) : '-'}
                        </td>
                      </tr>
                    );
                  });
                })()}
              </tbody>
            </table>
          </div>
        )}

        {!hasDetails && !hasChanges && (
          <div className="glass-card rounded-lg p-3 text-center">
            <span className="text-white/30 text-xs italic">No additional details recorded</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function AuditReport() {
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [targetTypeFilter, setTargetTypeFilter] = useState('');
  const [dateRange, setDateRange] = useState('30');
  const [complianceOnly, setComplianceOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const limit = 25;

  const getDateParams = () => {
    const days = parseInt(dateRange) || 30;
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    return { start_date: start.toISOString(), end_date: end.toISOString() };
  };

  // Fetch logs — all filtering is server-side
  const { data: logsData, isLoading, error } = useQuery({
    queryKey: ['audit-logs', { searchTerm, categoryFilter, targetTypeFilter, dateRange, complianceOnly, page }],
    queryFn: async () => {
      const dates = getDateParams();
      const response = await auditApi.getLogs({
        ...dates,
        category: categoryFilter || undefined,
        target_type: targetTypeFilter || undefined,
        search: searchTerm || undefined,
        compliance_only: complianceOnly || undefined,
        limit,
        offset: (page - 1) * limit,
      });
      return response.data;
    },
  });

  const { data: summaryData } = useQuery({
    queryKey: ['audit-summary', dateRange],
    queryFn: async () => {
      const response = await auditApi.getSummary(parseInt(dateRange) || 30);
      return response.data;
    },
  });

  const toggleRow = (id: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const logs = logsData?.logs || [];
  const totalPages = logsData ? Math.ceil(logsData.total / limit) : 0;

  const handleExport = async () => {
    try {
      const dates = getDateParams();
      const response = await auditApi.exportCsv({
        start_date: dates.start_date,
        end_date: dates.end_date,
      });
      const csvData = response.data;
      if (csvData.data?.length > 0) {
        const headers = csvData.columns.join(',');
        const rows = csvData.data.map((row: any) =>
          csvData.columns.map((col: string) =>
            `"${(row[col] || '').toString().replace(/"/g, '""')}"`
          ).join(',')
        );
        const csv = [headers, ...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-report-${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch {
      // export failed
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Report"
        subtitle="Complete audit trail — every change, approval, and system event with full details"
        actions={
          <button
            onClick={handleExport}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-white/10 hover:bg-white/20 text-white/80 transition-colors"
          >
            <ArrowDownTrayIcon className="h-4 w-4" />
            Export CSV
          </button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Events"
          value={summaryData?.total_entries ?? 0}
          icon={ClipboardDocumentListIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Unique Actors"
          value={summaryData?.unique_actors ?? 0}
          icon={UserGroupIcon}
          iconBgColor="stat-icon-purple"
          iconColor="text-purple-400"
        />
        <StatCard
          title="Failed Actions"
          value={summaryData?.failed_actions ?? 0}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-red"
          iconColor="text-red-400"
        />
        <StatCard
          title="Period"
          value={`${dateRange}d`}
          icon={ClockIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[200px]">
            <SearchInput
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
              placeholder="Search actor, target name or ID..."
            />
          </div>
          <div className="w-48">
            <Select
              value={categoryFilter}
              onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
              options={CATEGORY_OPTIONS}
            />
          </div>
          <div className="w-40">
            <Select
              value={targetTypeFilter}
              onChange={(e) => { setTargetTypeFilter(e.target.value); setPage(1); }}
              options={TARGET_TYPE_OPTIONS}
            />
          </div>
          <div className="w-36">
            <Select
              value={dateRange}
              onChange={(e) => { setDateRange(e.target.value); setPage(1); }}
              options={DATE_RANGE_OPTIONS}
            />
          </div>
          <button
            onClick={() => { setComplianceOnly(!complianceOnly); setPage(1); }}
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-all border ${
              complianceOnly
                ? 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                : 'bg-white/5 text-white/50 border-white/10 hover:bg-white/10'
            }`}
          >
            <ShieldCheckIcon className="h-3.5 w-3.5" />
            Compliance Only
          </button>
        </div>
      </Card>

      {/* Top Actions & Top Actors */}
      {summaryData && (summaryData.top_actions?.length > 0 || summaryData.top_actors?.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {summaryData.top_actions?.length > 0 && (
            <Card padding="md">
              <div className="text-sm font-medium text-white/80 mb-3">Top Actions</div>
              <div className="space-y-1.5">
                {summaryData.top_actions.slice(0, 8).map((item: any) => (
                  <div key={item.action} className="flex items-center gap-3">
                    <Badge variant={toBadgeVariant(ACTION_BADGE_COLORS[item.action])}>
                      {ACTION_LABELS[item.action] || item.action}
                    </Badge>
                    <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-white/20"
                        style={{ width: `${Math.min(100, (item.count / (summaryData.total_entries || 1)) * 100 * 3)}%` }}
                      />
                    </div>
                    <span className="text-xs text-white/50 font-mono w-12 text-right">{item.count}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
          {summaryData.top_actors?.length > 0 && (
            <Card padding="md">
              <div className="text-sm font-medium text-white/80 mb-3">Most Active Users</div>
              <div className="space-y-1.5">
                {summaryData.top_actors.slice(0, 8).map((item: any) => (
                  <div key={item.user_id} className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-lg bg-white/10 flex items-center justify-center shrink-0">
                      <UserIcon className="h-3.5 w-3.5 text-white/50" />
                    </div>
                    <span className="text-xs text-white/80 min-w-[80px] truncate">{item.user_id}</span>
                    <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-purple-500/30"
                        style={{ width: `${Math.min(100, (item.count / (summaryData.top_actors[0]?.count || 1)) * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-white/50 font-mono w-12 text-right">{item.count}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Audit Log Table */}
      <Card padding="none">
        {isLoading && <LoadingState />}
        {error && <ErrorState message="Failed to load audit logs" />}
        {!isLoading && !error && (
          <>
            {logs.length === 0 ? (
              <EmptyState
                title="No audit entries found"
                description="Adjust your filters or time range to see audit events"
              />
            ) : (
              <>
                <div className="px-4 py-2 border-b border-white/5 flex items-center justify-between">
                  <span className="text-xs text-white/40">
                    Showing {(page - 1) * limit + 1}–{Math.min(page * limit, logsData.total)} of {logsData.total} entries
                  </span>
                  <span className="text-xs text-white/30">Click a row to expand details</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="w-8 px-2 py-3"></th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-white/50 uppercase tracking-wider">Timestamp</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-white/50 uppercase tracking-wider">Action</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-white/50 uppercase tracking-wider">Performed By</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-white/50 uppercase tracking-wider">Target</th>
                        <th className="text-left px-4 py-3 text-xs font-medium text-white/50 uppercase tracking-wider">Result</th>
                        <th className="w-10 px-4 py-3"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {logs.map((log: any) => (
                        <Fragment key={log.id}>
                          <tr
                            className={`border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors ${
                              expandedRows.has(log.id) ? 'bg-white/[0.03]' : ''
                            } ${!log.success ? 'border-l-2 border-l-red-500/50' : ''}`}
                            onClick={() => toggleRow(log.id)}
                          >
                            <td className="px-2 py-3">
                              <button className="p-0.5 rounded hover:bg-white/10 transition-colors">
                                {expandedRows.has(log.id) ? (
                                  <ChevronDownIcon className="h-4 w-4 text-white/50" />
                                ) : (
                                  <ChevronRightIcon className="h-4 w-4 text-white/30" />
                                )}
                              </button>
                            </td>
                            <td className="px-4 py-3">
                              <span className="text-white/60 text-xs font-mono whitespace-nowrap">
                                {formatTimestamp(log.timestamp)}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <Badge variant={toBadgeVariant(ACTION_BADGE_COLORS[log.action])}>
                                {ACTION_LABELS[log.action] || log.action}
                              </Badge>
                            </td>
                            <td className="px-4 py-3">
                              <div className="text-white text-xs font-medium">
                                {log.actor_username || log.actor_user_id || 'System'}
                              </div>
                              {log.actor_type && log.actor_type !== 'user' && (
                                <span className="text-white/30 text-[10px]">{log.actor_type}</span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <div className="text-white/80 text-xs">
                                {log.target_name || log.target_id || '-'}
                              </div>
                              {log.target_type && (
                                <span className="text-white/30 text-[10px]">{log.target_type}</span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              {log.success ? (
                                <span className="inline-flex items-center gap-1 text-xs text-green-400">
                                  <CheckCircleIcon className="h-3.5 w-3.5" /> OK
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-xs text-red-400">
                                  <XCircleIcon className="h-3.5 w-3.5" /> Fail
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              {log.compliance_relevant && (
                                <ShieldCheckIcon className="h-4 w-4 text-blue-400" title="Compliance relevant" />
                              )}
                            </td>
                          </tr>
                          {expandedRows.has(log.id) && (
                            <tr className="bg-white/[0.02]">
                              <td colSpan={7} className="px-4 py-4">
                                <DetailPanel log={log} />
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>

                {totalPages > 1 && (
                  <div className="p-4 border-t border-white/10">
                    <Pagination
                      page={page}
                      total={logsData?.total ?? 0}
                      pageSize={limit}
                      onPageChange={setPage}
                    />
                  </div>
                )}
              </>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
