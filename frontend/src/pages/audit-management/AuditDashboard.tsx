import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ClipboardDocumentListIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import { auditManagementApi } from '../../services/auditManagementApi';
import { PageHeader, Card, CardHeader, Badge, Button, LoadingState, ErrorState } from '../../components/ui';
import { StatCard } from '../../components/StatCard';

// ─── Types ────────────────────────────────────────────────────────────────────

interface EngagementsByStatus {
  planned: number;
  announced: number;
  fieldwork: number;
  draft_report: number;
  final_report: number;
  closed: number;
}

interface FindingsBySeverity {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

interface OverdueAction {
  id: string;
  description: string;
  finding_id: string;
  finding_title: string;
  owner_name: string;
  due_date: string;
  days_overdue: number;
}

interface DashboardData {
  active_engagements: number;
  open_findings: number;
  overdue_actions: number;
  plan_completion_pct: number;
  engagements_by_status: EngagementsByStatus;
  findings_by_severity: FindingsBySeverity;
  overdue_action_list: OverdueAction[];
}

// ─── Pipeline Stage Config ────────────────────────────────────────────────────

const PIPELINE_STAGES: { key: keyof EngagementsByStatus; label: string; variant: 'neutral' | 'info' | 'warning' | 'danger' | 'success' | 'default' }[] = [
  { key: 'planned', label: 'Planned', variant: 'neutral' },
  { key: 'announced', label: 'Announced', variant: 'info' },
  { key: 'fieldwork', label: 'Fieldwork', variant: 'warning' },
  { key: 'draft_report', label: 'Draft Report', variant: 'warning' },
  { key: 'final_report', label: 'Final Report', variant: 'success' },
  { key: 'closed', label: 'Closed', variant: 'neutral' },
];

const SEVERITY_CONFIG: { key: keyof FindingsBySeverity; label: string; bg: string; text: string; border: string }[] = [
  { key: 'critical', label: 'Critical', bg: 'bg-red-50 dark:bg-red-900/20', text: 'text-red-700 dark:text-red-400', border: 'border-red-200 dark:border-red-800' },
  { key: 'high', label: 'High', bg: 'bg-orange-50 dark:bg-orange-900/20', text: 'text-orange-700 dark:text-orange-400', border: 'border-orange-200 dark:border-orange-800' },
  { key: 'medium', label: 'Medium', bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-700 dark:text-amber-400', border: 'border-amber-200 dark:border-amber-800' },
  { key: 'low', label: 'Low', bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-700 dark:text-emerald-400', border: 'border-emerald-200 dark:border-emerald-800' },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: '2-digit' });
}

// ─── Component ────────────────────────────────────────────────────────────────

export function AuditDashboard() {
  const qc = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery<DashboardData>({
    queryKey: ['audit-management', 'dashboard'],
    queryFn: async () => {
      const res = await auditManagementApi.getDashboard();
      return res.data;
    },
  });

  const escalateMutation = useMutation({
    mutationFn: () => auditManagementApi.escalateActions(),
    onSuccess: () => {
      toast.success('Overdue actions escalated successfully');
      qc.invalidateQueries({ queryKey: ['audit-management', 'dashboard'] });
    },
    onError: () => toast.error('Failed to escalate actions'),
  });

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message="Failed to load audit dashboard" />;

  const byStatus = data?.engagements_by_status ?? ({} as EngagementsByStatus);
  const bySeverity = data?.findings_by_severity ?? ({} as FindingsBySeverity);
  const overdueList = data?.overdue_action_list ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Management"
        subtitle="Internal audit lifecycle — plans, engagements, findings, and actions"
        breadcrumbs={[{ label: 'Audit Management' }, { label: 'Dashboard' }]}
        actions={
          <Button
            variant="ghost"
            size="sm"
            icon={<ArrowPathIcon className="h-4 w-4" />}
            onClick={() => refetch()}
          >
            Refresh
          </Button>
        }
      />

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          title="Active Engagements"
          value={data?.active_engagements ?? 0}
          icon={ClipboardDocumentListIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
          link="/audit-management/engagements"
        />
        <StatCard
          title="Open Findings"
          value={data?.open_findings ?? 0}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-red"
          iconColor="text-red-400"
          link="/audit-management/findings"
        />
        <StatCard
          title="Overdue Actions"
          value={data?.overdue_actions ?? 0}
          icon={ClockIcon}
          iconBgColor="stat-icon-orange"
          iconColor="text-orange-400"
        />
        <StatCard
          title="Plan Completion"
          value={`${data?.plan_completion_pct ?? 0}%`}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
          link="/audit-management/planning"
        />
      </div>

      {/* Status Pipeline + Severity side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Engagements by Status */}
        <Card className="lg:col-span-2">
          <CardHeader title="Engagements by Status" subtitle="Pipeline overview across all audit stages" />
          <div className="flex items-stretch gap-0 overflow-x-auto">
            {PIPELINE_STAGES.map((stage, idx) => {
              const count = byStatus[stage.key] ?? 0;
              const isLast = idx === PIPELINE_STAGES.length - 1;
              return (
                <div key={stage.key} className="flex items-center flex-1 min-w-0">
                  <div className="flex-1 flex flex-col items-center py-4 px-3 text-center">
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">{count}</div>
                    <Badge variant={stage.variant} size="sm">{stage.label}</Badge>
                  </div>
                  {!isLast && (
                    <ChevronRightIcon className="h-4 w-4 text-gray-300 dark:text-gray-600 flex-shrink-0" />
                  )}
                </div>
              );
            })}
          </div>
        </Card>

        {/* Findings by Severity */}
        <Card>
          <CardHeader title="Findings by Severity" />
          <div className="grid grid-cols-2 gap-3">
            {SEVERITY_CONFIG.map((sev) => (
              <div
                key={sev.key}
                className={`rounded-xl border p-3 ${sev.bg} ${sev.border}`}
              >
                <div className={`text-2xl font-bold ${sev.text}`}>{bySeverity[sev.key] ?? 0}</div>
                <div className={`text-xs font-medium mt-0.5 ${sev.text}`}>{sev.label}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Overdue Actions Table */}
      <Card padding="none">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-slate-700 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Overdue Actions</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Remediation actions past their due date</p>
          </div>
          {overdueList.length > 0 && (
            <Button
              variant="danger"
              size="sm"
              loading={escalateMutation.isPending}
              onClick={() => escalateMutation.mutate()}
            >
              Escalate All
            </Button>
          )}
        </div>

        {overdueList.length === 0 ? (
          <div className="py-16 text-center">
            <CheckCircleIcon className="h-12 w-12 text-emerald-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-gray-600 dark:text-gray-400">No overdue actions</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">All remediation actions are on track</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 dark:border-slate-700">
                  {['Action ID', 'Description', 'Finding', 'Owner', 'Due Date', 'Days Overdue', ''].map((h) => (
                    <th key={h} className="px-5 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-slate-700/50">
                {overdueList.map((action) => (
                  <tr key={action.id} className="hover:bg-gray-50/50 dark:hover:bg-slate-700/30 transition-colors">
                    <td className="px-5 py-3.5 text-xs font-mono text-gray-500 dark:text-gray-400">
                      {action.id.slice(0, 8)}
                    </td>
                    <td className="px-5 py-3.5 text-sm text-gray-900 dark:text-gray-100 max-w-xs truncate">
                      {action.description}
                    </td>
                    <td className="px-5 py-3.5 text-sm text-indigo-600 dark:text-indigo-400 max-w-[180px] truncate">
                      {action.finding_title}
                    </td>
                    <td className="px-5 py-3.5 text-sm text-gray-700 dark:text-gray-300">
                      {action.owner_name}
                    </td>
                    <td className="px-5 py-3.5 text-sm font-medium text-red-600 dark:text-red-400 whitespace-nowrap">
                      {formatDate(action.due_date)}
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge variant="danger">{action.days_overdue}d overdue</Badge>
                    </td>
                    <td className="px-5 py-3.5">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          toast.success(`Action ${action.id.slice(0, 8)} escalated`);
                        }}
                      >
                        Escalate
                      </Button>
                    </td>
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
