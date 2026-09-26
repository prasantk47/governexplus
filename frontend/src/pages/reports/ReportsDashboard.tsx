import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  DocumentChartBarIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  UserGroupIcon,
  ShieldCheckIcon,
  FireIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowTrendingUpIcon,
  ClipboardDocumentListIcon,
  BoltIcon,
} from '@heroicons/react/24/outline';
import { reportsApi } from '../../services/api';
import {
  PageHeader,
  Card,
  Select,
  Badge,
  LoadingState,
  ErrorState,
  EmptyState,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';

// ============================================================================
// Constants
// ============================================================================

const DATE_RANGE_OPTIONS = [
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: '90', label: 'Last 90 days' },
  { value: '180', label: 'Last 6 months' },
  { value: '365', label: 'Last year' },
];

const TAB_KEYS = ['access', 'firefighter', 'risk', 'users'] as const;
type TabKey = (typeof TAB_KEYS)[number];

const TABS: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: 'access', label: 'Access Requests', icon: DocumentChartBarIcon },
  { key: 'firefighter', label: 'Privileged Access', icon: FireIcon },
  { key: 'risk', label: 'Risk & Compliance', icon: ShieldCheckIcon },
  { key: 'users', label: 'Users & Audit', icon: UserGroupIcon },
];

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';

const COLOR_TO_VARIANT: Record<string, BadgeVariant> = {
  blue: 'info', indigo: 'info', cyan: 'info', purple: 'info',
  green: 'success', emerald: 'success',
  yellow: 'warning', amber: 'warning', orange: 'warning',
  red: 'danger',
  gray: 'neutral', grey: 'neutral',
};

function toBadgeVariant(color: string | undefined): BadgeVariant {
  if (!color) return 'neutral';
  return COLOR_TO_VARIANT[color] ?? 'neutral';
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'gray',
  submitted: 'blue',
  pending_risk_review: 'yellow',
  pending_approval: 'orange',
  approved: 'green',
  rejected: 'red',
  provisioning: 'blue',
  provisioned: 'green',
  failed: 'red',
  cancelled: 'gray',
  expired: 'gray',
  active: 'green',
  completed: 'blue',
  revoked: 'red',
  open: 'red',
  mitigated: 'yellow',
  remediated: 'green',
};

const STATUS_LABELS: Record<string, string> = {
  draft: 'Draft',
  submitted: 'Submitted',
  pending_risk_review: 'Risk Review',
  pending_approval: 'Pending Approval',
  approved: 'Approved',
  rejected: 'Rejected',
  provisioning: 'Provisioning',
  provisioned: 'Provisioned',
  failed: 'Failed',
  cancelled: 'Cancelled',
  expired: 'Expired',
  active: 'Active',
  completed: 'Completed',
  revoked: 'Revoked',
  open: 'Open',
  mitigated: 'Mitigated',
  remediated: 'Remediated',
};

const RISK_COLORS: Record<string, string> = {
  low: 'green',
  medium: 'yellow',
  high: 'orange',
  critical: 'red',
};

const CATEGORY_LABELS: Record<string, string> = {
  user: 'User Management',
  role: 'Role Management',
  risk: 'Risk & Violations',
  firefighter: 'Privileged Access',
  approver: 'Approver Management',
  system: 'System / Rules',
};

const CATEGORY_COLORS: Record<string, string> = {
  user: 'blue',
  role: 'purple',
  risk: 'red',
  firefighter: 'orange',
  approver: 'cyan',
  system: 'gray',
};

function formatDate(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ============================================================================
// Breakdown Bar Component — horizontal bar with label + count
// ============================================================================

function BreakdownBar({
  items,
  total,
}: {
  items: { key: string; count: number; color: string; label: string }[];
  total: number;
}) {
  if (!items.length) return null;
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.key} className="flex items-center gap-3">
          <Badge variant={toBadgeVariant(item.color)}>{item.label}</Badge>
          <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
            <div
              className="h-full rounded-full bg-white/20"
              style={{ width: `${Math.min(100, (item.count / (total || 1)) * 100)}%` }}
            />
          </div>
          <span className="text-xs text-white/50 font-mono w-12 text-right">{item.count}</span>
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Tab Content Components
// ============================================================================

function AccessRequestsTab({ data }: { data: any }) {
  const ar = data.access_requests;
  const sla = ar.sla || {};
  const byStatus = ar.by_status || {};
  const recent = ar.recent || [];

  const statusItems = Object.entries(byStatus).map(([key, count]) => ({
    key,
    count: count as number,
    color: STATUS_COLORS[key] || 'gray',
    label: STATUS_LABELS[key] || key,
  }));

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Requests"
          value={ar.total_requests ?? 0}
          icon={DocumentChartBarIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Pending Approval"
          value={ar.pending_approval ?? 0}
          icon={ClockIcon}
          iconBgColor="stat-icon-orange"
          iconColor="text-orange-400"
        />
        <StatCard
          title="Overdue"
          value={ar.overdue ?? 0}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-red"
          iconColor="text-red-400"
        />
        <StatCard
          title="Avg Approval Time"
          value={`${sla.average_approval_hours ?? 0}h`}
          icon={ArrowTrendingUpIcon}
          iconBgColor="stat-icon-purple"
          iconColor="text-purple-400"
        />
      </div>

      {/* SLA Compliance Bar */}
      <Card padding="md">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-white/80">SLA Compliance</span>
          <span className="text-sm font-bold text-white">{sla.sla_compliance_rate ?? 100}%</span>
        </div>
        <div className="h-3 rounded-full bg-white/5 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              (sla.sla_compliance_rate ?? 100) >= 90
                ? 'bg-green-500/60'
                : (sla.sla_compliance_rate ?? 100) >= 70
                  ? 'bg-yellow-500/60'
                  : 'bg-red-500/60'
            }`}
            style={{ width: `${sla.sla_compliance_rate ?? 100}%` }}
          />
        </div>
        <div className="flex justify-between mt-1 text-[10px] text-white/30">
          <span>{sla.overdue_count ?? 0} overdue</span>
          <span>{sla.requests_completed_today ?? 0} completed today</span>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* By Status */}
        <Card padding="md">
          <div className="text-sm font-medium text-white/80 mb-3">Requests by Status</div>
          <BreakdownBar items={statusItems} total={ar.total_requests || 1} />
        </Card>

        {/* Risk Score */}
        <Card padding="md">
          <div className="text-sm font-medium text-white/80 mb-3">Risk Overview</div>
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className="text-3xl font-bold text-white">
                {Math.round(ar.average_risk_score ?? 0)}
              </div>
              <div className="text-[10px] text-white/40 mt-1">Avg Risk Score</div>
            </div>
            <div className="flex-1 h-3 rounded-full bg-white/5 overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  (ar.average_risk_score ?? 0) >= 70
                    ? 'bg-red-500/60'
                    : (ar.average_risk_score ?? 0) >= 40
                      ? 'bg-yellow-500/60'
                      : 'bg-green-500/60'
                }`}
                style={{ width: `${Math.min(100, ar.average_risk_score ?? 0)}%` }}
              />
            </div>
          </div>
        </Card>
      </div>

      {/* Recent Requests Table */}
      <Card padding="none">
        <div className="px-4 py-3 border-b border-white/10">
          <span className="text-sm font-medium text-white/80">Recent Access Requests</span>
        </div>
        {recent.length === 0 ? (
          <EmptyState title="No requests" description="No access requests in this period" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">Request ID</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">Requester</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">Target</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">Risk</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">Status</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">Created</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((r: any) => (
                  <tr key={r.request_id} className="border-b border-white/5 hover:bg-white/5">
                    <td className="px-4 py-2.5 text-xs font-mono text-white/80">{r.request_id}</td>
                    <td className="px-4 py-2.5 text-xs text-white/70">{r.requester_user_id}</td>
                    <td className="px-4 py-2.5 text-xs text-white/70">{r.target_user_id}</td>
                    <td className="px-4 py-2.5">
                      <Badge variant={toBadgeVariant(RISK_COLORS[r.risk_level])}>
                        {r.risk_level || 'N/A'}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge variant={toBadgeVariant(STATUS_COLORS[r.status])}>
                        {STATUS_LABELS[r.status] || r.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-white/50">{formatDate(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function FirefighterTab({ data }: { data: any }) {
  const ff = data.firefighter;
  const recent = ff.recent_sessions || [];

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Sessions"
          value={ff.total_sessions ?? 0}
          icon={FireIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Active Now"
          value={ff.active_sessions ?? 0}
          icon={BoltIcon}
          iconBgColor="stat-icon-red"
          iconColor="text-red-400"
        />
        <StatCard
          title="Completed"
          value={ff.completed_sessions ?? 0}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
        <StatCard
          title="Pending Reviews"
          value={ff.pending_reviews ?? 0}
          icon={ClipboardDocumentListIcon}
          iconBgColor="stat-icon-orange"
          iconColor="text-orange-400"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Session Status Breakdown */}
        <Card padding="md">
          <div className="text-sm font-medium text-white/80 mb-3">Sessions by Status</div>
          <BreakdownBar
            items={[
              { key: 'active', count: ff.active_sessions ?? 0, color: 'green', label: 'Active' },
              { key: 'completed', count: ff.completed_sessions ?? 0, color: 'blue', label: 'Completed' },
              { key: 'revoked', count: ff.revoked_sessions ?? 0, color: 'red', label: 'Revoked' },
            ]}
            total={ff.total_sessions || 1}
          />
        </Card>

        {/* Requests Summary */}
        <Card padding="md">
          <div className="text-sm font-medium text-white/80 mb-3">Request Summary</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="glass-card rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-white">{ff.total_requests ?? 0}</div>
              <div className="text-[10px] text-white/40 mt-1">Total Requests</div>
            </div>
            <div className="glass-card rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-orange-400">{ff.pending_requests ?? 0}</div>
              <div className="text-[10px] text-white/40 mt-1">Pending Approval</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Recent Sessions Table */}
      <Card padding="none">
        <div className="px-4 py-3 border-b border-white/10">
          <span className="text-sm font-medium text-white/80">Recent Privileged Access Sessions</span>
        </div>
        {recent.length === 0 ? (
          <EmptyState title="No sessions" description="No privileged access sessions in this period" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">Session ID</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">User</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">FF ID</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">Status</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">Activities</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">Sensitive</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">Review</th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-white/50 uppercase">Started</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((s: any) => (
                  <tr key={s.session_id} className="border-b border-white/5 hover:bg-white/5">
                    <td className="px-4 py-2.5 text-xs font-mono text-white/80">{s.session_id}</td>
                    <td className="px-4 py-2.5 text-xs text-white/70">{s.requester_user_id}</td>
                    <td className="px-4 py-2.5 text-xs text-white/70">{s.firefighter_id}</td>
                    <td className="px-4 py-2.5">
                      <Badge variant={toBadgeVariant(STATUS_COLORS[s.status])}>
                        {STATUS_LABELS[s.status] || s.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-white/60 font-mono">{s.activity_count ?? 0}</td>
                    <td className="px-4 py-2.5">
                      {(s.sensitive_action_count ?? 0) > 0 ? (
                        <span className="text-xs text-red-400 font-medium">{s.sensitive_action_count}</span>
                      ) : (
                        <span className="text-xs text-white/30">0</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      {s.requires_review ? (
                        s.review_status ? (
                          <Badge variant={s.review_status === 'approved' ? 'success' : 'warning'}>
                            {s.review_status}
                          </Badge>
                        ) : (
                          <Badge variant="warning">Pending</Badge>
                        )
                      ) : (
                        <span className="text-xs text-white/30">N/A</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-white/50">{formatDate(s.start_time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function RiskTab({ data }: { data: any }) {
  const risk = data.risk;
  const byCategory = risk.rules_by_category || {};
  const byType = risk.rules_by_type || {};

  const categoryItems = Object.entries(byCategory).map(([key, count]) => ({
    key,
    count: count as number,
    color: CATEGORY_COLORS[key] || 'gray',
    label: key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
  }));

  const typeItems = Object.entries(byType).map(([key, count]) => ({
    key,
    count: count as number,
    color: key === 'sod' ? 'red' : key === 'sensitive_access' ? 'orange' : key === 'critical_transaction' ? 'purple' : 'blue',
    label: key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
  }));

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Rules"
          value={risk.total_rules ?? 0}
          icon={ShieldCheckIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Evaluations Run"
          value={risk.evaluations_performed ?? 0}
          icon={ArrowTrendingUpIcon}
          iconBgColor="stat-icon-purple"
          iconColor="text-purple-400"
        />
        <StatCard
          title="Violations Found"
          value={risk.violations_found ?? 0}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-red"
          iconColor="text-red-400"
        />
        <StatCard
          title="Rule Categories"
          value={Object.keys(byCategory).length}
          icon={ClipboardDocumentListIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Rules by Category */}
        <Card padding="md">
          <div className="text-sm font-medium text-white/80 mb-3">Rules by Category</div>
          {categoryItems.length > 0 ? (
            <BreakdownBar items={categoryItems} total={risk.total_rules || 1} />
          ) : (
            <div className="text-xs text-white/30 italic">No rules loaded</div>
          )}
        </Card>

        {/* Rules by Type */}
        <Card padding="md">
          <div className="text-sm font-medium text-white/80 mb-3">Rules by Type</div>
          {typeItems.length > 0 ? (
            <BreakdownBar items={typeItems} total={risk.total_rules || 1} />
          ) : (
            <div className="text-xs text-white/30 italic">No rules loaded</div>
          )}
        </Card>
      </div>
    </div>
  );
}

function UsersAuditTab({ data }: { data: any }) {
  const audit = data.audit;
  const byCategory = audit.by_category || {};

  const categoryItems = Object.entries(byCategory).map(([key, count]) => ({
    key,
    count: count as number,
    color: CATEGORY_COLORS[key] || 'gray',
    label: CATEGORY_LABELS[key] || key,
  }));

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Audit Events"
          value={audit.total_entries ?? 0}
          icon={ClipboardDocumentListIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Failed Actions"
          value={audit.failed_actions ?? 0}
          icon={XCircleIcon}
          iconBgColor="stat-icon-red"
          iconColor="text-red-400"
        />
        <StatCard
          title="Compliance Events"
          value={audit.compliance_entries ?? 0}
          icon={ShieldCheckIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
        <StatCard
          title="Categories"
          value={Object.keys(byCategory).length}
          icon={UserGroupIcon}
          iconBgColor="stat-icon-purple"
          iconColor="text-purple-400"
        />
      </div>

      {/* Audit Events by Category */}
      <Card padding="md">
        <div className="text-sm font-medium text-white/80 mb-3">Events by Module</div>
        {categoryItems.length > 0 ? (
          <BreakdownBar items={categoryItems} total={audit.total_entries || 1} />
        ) : (
          <div className="text-xs text-white/30 italic">No audit events in this period</div>
        )}
      </Card>

      {/* Failure Rate */}
      {audit.total_entries > 0 && (
        <Card padding="md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-white/80">Success Rate</span>
            <span className="text-sm font-bold text-white">
              {Math.round(((audit.total_entries - audit.failed_actions) / audit.total_entries) * 100)}%
            </span>
          </div>
          <div className="h-3 rounded-full bg-white/5 overflow-hidden">
            <div
              className="h-full rounded-full bg-green-500/60"
              style={{
                width: `${((audit.total_entries - audit.failed_actions) / audit.total_entries) * 100}%`,
              }}
            />
          </div>
          <div className="flex justify-between mt-1 text-[10px] text-white/30">
            <span>{audit.total_entries - audit.failed_actions} successful</span>
            <span>{audit.failed_actions} failed</span>
          </div>
        </Card>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ReportsDashboard() {
  const [days, setDays] = useState('30');
  const [activeTab, setActiveTab] = useState<TabKey>('access');

  const {
    data: summary,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['reports-dashboard-summary', days],
    queryFn: async () => {
      const response = await reportsApi.getDashboardSummary(parseInt(days));
      return response.data;
    },
  });

  const ar = summary?.access_requests || {};
  const ff = summary?.firefighter || {};
  const risk = summary?.risk || {};
  const audit = summary?.audit || {};

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        subtitle="Operational reports across Access Requests, Privileged Access, Risk, and Audit"
        actions={
          <div className="w-40">
            <Select
              value={days}
              onChange={(e) => setDays(e.target.value)}
              options={DATE_RANGE_OPTIONS}
            />
          </div>
        }
      />

      {/* Executive Summary */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard
          title="Access Requests"
          value={ar.total_requests ?? 0}
          icon={DocumentChartBarIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Pending Approvals"
          value={ar.pending_approval ?? 0}
          icon={ClockIcon}
          iconBgColor="stat-icon-orange"
          iconColor="text-orange-400"
        />
        <StatCard
          title="Active FF Sessions"
          value={ff.active_sessions ?? 0}
          icon={FireIcon}
          iconBgColor="stat-icon-red"
          iconColor="text-red-400"
        />
        <StatCard
          title="Violations Found"
          value={risk.violations_found ?? 0}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-purple"
          iconColor="text-purple-400"
        />
        <StatCard
          title="SLA Compliance"
          value={`${ar.sla?.sla_compliance_rate ?? 100}%`}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
        <StatCard
          title="Audit Events"
          value={audit.total_entries ?? 0}
          icon={ClipboardDocumentListIcon}
          iconBgColor="stat-icon-gray"
          iconColor="text-gray-400"
        />
      </div>

      {/* Tabs */}
      <div>
        <div className="flex gap-1 border-b border-white/10 mb-6">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? 'border-blue-400 text-blue-400'
                    : 'border-transparent text-white/40 hover:text-white/60'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {isLoading && <LoadingState />}
        {error && <ErrorState message="Failed to load reports data" />}

        {!isLoading && !error && summary && (
          <>
            {activeTab === 'access' && <AccessRequestsTab data={summary} />}
            {activeTab === 'firefighter' && <FirefighterTab data={summary} />}
            {activeTab === 'risk' && <RiskTab data={summary} />}
            {activeTab === 'users' && <UsersAuditTab data={summary} />}
          </>
        )}
      </div>
    </div>
  );
}
