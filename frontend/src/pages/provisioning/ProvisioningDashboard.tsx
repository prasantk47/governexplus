import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../services/api';
import {
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  QueueListIcon,
  ArrowDownTrayIcon,
  FunnelIcon,
  CogIcon,
  ExclamationTriangleIcon,
  PlayIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  SearchInput,
  Select,
  Table,
} from '../../components/ui';

// ======================== Types ========================

type ProvisioningAction = 'Add Role' | 'Remove Role' | 'Lock Account' | 'Unlock Account';
type ProvisioningStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'retrying';
type TabKey = 'queue' | 'completed' | 'failed' | 'all';

interface ProvisioningTask {
  id: string;
  requestId: string;
  user: string;
  userId: string;
  action: ProvisioningAction;
  role: string;
  targetSystem: string;
  status: ProvisioningStatus;
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
  retryCount: number;
  errorMessage: string | null;
  provisionedBy: string | null;
}

// ======================== Helpers ========================

const STATUS_CONFIG: Record<
  ProvisioningStatus,
  { variant: 'warning' | 'info' | 'success' | 'danger' | 'neutral'; label: string }
> = {
  queued:     { variant: 'neutral',  label: 'Queued' },
  processing: { variant: 'info',     label: 'Processing' },
  completed:  { variant: 'success',  label: 'Completed' },
  failed:     { variant: 'danger',   label: 'Failed' },
  retrying:   { variant: 'warning',  label: 'Retrying' },
};

const ACTION_CONFIG: Record<ProvisioningAction, { color: string }> = {
  'Add Role':       { color: 'text-green-700 bg-green-50 border-green-200' },
  'Remove Role':    { color: 'text-red-700 bg-red-50 border-red-200' },
  'Lock Account':   { color: 'text-orange-700 bg-orange-50 border-orange-200' },
  'Unlock Account': { color: 'text-blue-700 bg-blue-50 border-blue-200' },
};

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function ActionPill({ action }: { action: ProvisioningAction }) {
  const cfg = ACTION_CONFIG[action] ?? { color: 'text-gray-700 bg-gray-50 border-gray-200' };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium ${cfg.color}`}>
      {action}
    </span>
  );
}

// ======================== Main Component ========================

export function ProvisioningDashboard() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabKey>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [systemFilter, setSystemFilter] = useState('all');
  const [actionFilter, setActionFilter] = useState('all');
  const [retryingIds, setRetryingIds] = useState<Set<string>>(new Set());

  // ---- Fetch tasks ----
  const { data: tasksData, isLoading } = useQuery({
    queryKey: ['provisioning', 'tasks'],
    queryFn: () => api.get('/provisioning/tasks').then((res) => res.data),
  });

  const tasks: ProvisioningTask[] = (() => {
    if (!tasksData) return [];
    if (Array.isArray(tasksData)) return tasksData;
    if (Array.isArray(tasksData?.tasks)) return tasksData.tasks;
    return [];
  })();

  // ---- Retry single task ----
  const retryMutation = useMutation({
    mutationFn: (taskId: string) =>
      api.post(`/provisioning/tasks/${taskId}/retry`).then((res) => res.data),
    onMutate: (taskId) => {
      setRetryingIds((prev) => new Set(prev).add(taskId));
    },
    onSettled: (_, __, taskId) => {
      setRetryingIds((prev) => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
      queryClient.invalidateQueries({ queryKey: ['provisioning', 'tasks'] });
    },
  });

  // ---- Retry all failed ----
  const retryAllMutation = useMutation({
    mutationFn: () =>
      api.post('/provisioning/tasks/retry-failed').then((res) => res.data),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['provisioning', 'tasks'] });
    },
  });

  // ---- Export ----
  function handleExport() {
    const blob = new Blob([JSON.stringify(tasks, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `provisioning-tasks-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ---- Stats ----
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  const inQueueCount     = tasks.filter((t) => t.status === 'queued').length;
  const processingCount  = tasks.filter((t) => t.status === 'processing' || t.status === 'retrying').length;
  const completedToday   = tasks.filter(
    (t) => t.status === 'completed' && t.completedAt && new Date(t.completedAt) >= todayStart
  ).length;
  const failedCount      = tasks.filter((t) => t.status === 'failed').length;

  // ---- Filter logic ----
  const tabFiltered = tasks.filter((t) => {
    if (activeTab === 'queue')     return t.status === 'queued' || t.status === 'processing' || t.status === 'retrying';
    if (activeTab === 'completed') return t.status === 'completed';
    if (activeTab === 'failed')    return t.status === 'failed';
    return true;
  });

  const uniqueSystems = Array.from(new Set(tasks.map((t) => t.targetSystem)));
  const uniqueActions = Array.from(new Set(tasks.map((t) => t.action)));

  const filteredTasks = tabFiltered.filter((t) => {
    const q = searchTerm.toLowerCase();
    const matchesSearch =
      !q ||
      String(t.id).toLowerCase().includes(q) ||
      String(t.requestId ?? '').toLowerCase().includes(q) ||
      (t.user ?? '').toLowerCase().includes(q) ||
      (t.role ?? '').toLowerCase().includes(q) ||
      (t.targetSystem ?? '').toLowerCase().includes(q);
    const matchesSystem = systemFilter === 'all' || t.targetSystem === systemFilter;
    const matchesAction = actionFilter === 'all' || t.action === actionFilter;
    return matchesSearch && matchesSystem && matchesAction;
  });

  const failedTasks = tasks.filter((t) => t.status === 'failed');

  // ---- Table columns ----
  const columns = [
    {
      key: 'id',
      header: 'Task ID',
      render: (t: ProvisioningTask) => (
        <div>
          <div className="text-sm font-medium text-primary-600">{t.id}</div>
          <div className="text-xs text-gray-400 mt-0.5">Req: {t.requestId}</div>
        </div>
      ),
    },
    {
      key: 'user',
      header: 'User',
      render: (t: ProvisioningTask) => (
        <div>
          <div className="text-sm font-medium text-gray-900">{t.user}</div>
          <div className="text-xs text-gray-400">{t.userId}</div>
        </div>
      ),
    },
    {
      key: 'action',
      header: 'Action',
      render: (t: ProvisioningTask) => <ActionPill action={t.action} />,
    },
    {
      key: 'role',
      header: 'Role / System',
      render: (t: ProvisioningTask) => (
        <div>
          <div className="text-sm text-gray-900 font-medium">{t.role}</div>
          <div className="text-xs text-gray-400">{t.targetSystem}</div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (t: ProvisioningTask) => {
        const cfg = STATUS_CONFIG[t.status] ?? { variant: 'neutral' as const, label: t.status };
        return (
          <div className="space-y-1">
            <Badge variant={cfg.variant} size="sm">{cfg.label}</Badge>
            {t.retryCount > 0 && (
              <div className="text-xs text-gray-400">{t.retryCount} {t.retryCount === 1 ? 'retry' : 'retries'}</div>
            )}
          </div>
        );
      },
    },
    {
      key: 'timestamp',
      header: 'Timestamp',
      render: (t: ProvisioningTask) => (
        <div>
          <div className="text-xs text-gray-500">{formatTimestamp(t.createdAt)}</div>
          {t.completedAt && (
            <div className="text-xs text-green-600 mt-0.5">Done: {formatTimestamp(t.completedAt)}</div>
          )}
        </div>
      ),
    },
    {
      key: 'error',
      header: 'Error',
      render: (t: ProvisioningTask) =>
        t.errorMessage ? (
          <div className="max-w-xs">
            <span className="text-xs text-red-600 line-clamp-2" title={t.errorMessage}>
              {t.errorMessage}
            </span>
          </div>
        ) : (
          <span className="text-xs text-gray-300">—</span>
        ),
    },
    {
      key: 'actions',
      header: '',
      render: (t: ProvisioningTask) => {
        if (t.status !== 'failed') return null;
        const isRetrying = retryingIds.has(t.id) || retryMutation.isPending && retryMutation.variables === t.id;
        return (
          <Button
            variant="secondary"
            size="sm"
            icon={<ArrowPathIcon className={`h-3.5 w-3.5 ${isRetrying ? 'animate-spin' : ''}`} />}
            onClick={() => retryMutation.mutate(t.id)}
            disabled={isRetrying}
          >
            Retry
          </Button>
        );
      },
    },
  ];

  // ---- Tab config ----
  const TABS: { key: TabKey; label: string; count: number }[] = [
    { key: 'queue',     label: 'Queue',     count: inQueueCount + processingCount },
    { key: 'completed', label: 'Completed', count: tasks.filter((t) => t.status === 'completed').length },
    { key: 'failed',    label: 'Failed',    count: failedCount },
    { key: 'all',       label: 'All',       count: tasks.length },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Automated Provisioning"
        subtitle="Monitor and manage role assignment tasks across connected target systems"
        actions={
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              icon={<ArrowDownTrayIcon className="h-4 w-4" />}
              onClick={handleExport}
            >
              Export
            </Button>
            {failedTasks.length > 0 && (
              <Button
                size="sm"
                icon={<ArrowPathIcon className={`h-4 w-4 ${retryAllMutation.isPending ? 'animate-spin' : ''}`} />}
                onClick={() => retryAllMutation.mutate()}
                disabled={retryAllMutation.isPending}
              >
                Retry All Failed ({failedTasks.length})
              </Button>
            )}
          </div>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="In Queue"
          value={inQueueCount}
          icon={QueueListIcon}
          iconBgColor="stat-icon-blue"
          iconColor=""
        />
        <StatCard
          title="Processing"
          value={processingCount}
          icon={CogIcon}
          iconBgColor="stat-icon-yellow"
          iconColor=""
        />
        <StatCard
          title="Completed Today"
          value={completedToday}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor=""
        />
        <StatCard
          title="Failed"
          value={failedCount}
          icon={XCircleIcon}
          iconBgColor="stat-icon-red"
          iconColor=""
        />
      </div>

      {/* Status Monitoring Strip */}
      <Card>
        <div className="px-6 py-4 border-b border-white/20 flex items-center gap-2">
          <ShieldCheckIcon className="h-4 w-4 text-gray-500" />
          <h2 className="text-sm font-semibold text-gray-900">System Connectivity</h2>
        </div>
        <div className="px-6 py-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {uniqueSystems.map((system) => {
              const systemTasks = tasks.filter((t) => t.targetSystem === system);
              const hasFailed   = systemTasks.some((t) => t.status === 'failed');
              const hasActive   = systemTasks.some((t) => t.status === 'processing' || t.status === 'retrying');
              const statusLabel = hasFailed ? 'Degraded' : hasActive ? 'Active' : 'Idle';
              const dotColor    = hasFailed ? 'bg-red-500' : hasActive ? 'bg-green-500 animate-pulse' : 'bg-gray-300';
              const textColor   = hasFailed ? 'text-red-700' : hasActive ? 'text-green-700' : 'text-gray-500';
              return (
                <div
                  key={system}
                  className="flex items-center gap-2 px-3 py-2 bg-gray-50/60 border border-gray-200/60 rounded-lg"
                >
                  <span className={`h-2 w-2 rounded-full flex-shrink-0 ${dotColor}`} />
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-gray-800 truncate">{system}</div>
                    <div className={`text-xs ${textColor}`}>{statusLabel}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Card>

      {/* Tabs + Filters */}
      <Card padding="none">
        {/* Tab bar */}
        <div className="flex items-center justify-between border-b border-white/20 px-6">
          <div className="flex gap-0">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`
                  flex items-center gap-1.5 px-4 py-3.5 text-sm font-medium border-b-2 transition-colors
                  ${activeTab === tab.key
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
                `}
              >
                {tab.label}
                <span
                  className={`
                    inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full text-xs font-semibold
                    ${activeTab === tab.key ? 'bg-primary-100 text-primary-700' : 'bg-gray-100 text-gray-600'}
                  `}
                >
                  {tab.count}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Filters */}
        <div className="px-6 py-3 border-b border-white/20 flex flex-wrap items-center gap-3">
          <SearchInput
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search task ID, user, role..."
          />
          <div className="flex items-center gap-2 ml-auto">
            <FunnelIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <Select
              value={systemFilter}
              onChange={(e) => setSystemFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Systems' },
                ...uniqueSystems.map((s) => ({ value: s, label: s })),
              ]}
            />
            <Select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Actions' },
                ...uniqueActions.map((a) => ({ value: a, label: a })),
              ]}
            />
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16 text-sm text-gray-400">
            <ArrowPathIcon className="h-5 w-5 animate-spin mr-2" />
            Loading provisioning tasks...
          </div>
        ) : (
          <Table
            columns={columns}
            data={filteredTasks}
            emptyMessage={
              activeTab === 'queue'
                ? 'No tasks currently queued or processing.'
                : activeTab === 'completed'
                ? 'No completed tasks found.'
                : activeTab === 'failed'
                ? 'No failed tasks — all systems operating normally.'
                : 'No provisioning tasks match the current filters.'
            }
          />
        )}
      </Card>

      {/* Failed Tasks Detail Panel */}
      {activeTab === 'failed' && failedTasks.length > 0 && (
        <Card>
          <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <XCircleIcon className="h-4 w-4 text-red-500" />
              <h2 className="text-sm font-semibold text-gray-900">Failed Task Details</h2>
            </div>
            <Button
              size="sm"
              icon={<ArrowPathIcon className={`h-4 w-4 ${retryAllMutation.isPending ? 'animate-spin' : ''}`} />}
              onClick={() => retryAllMutation.mutate()}
              disabled={retryAllMutation.isPending}
            >
              Retry All Failed
            </Button>
          </div>
          <div className="divide-y divide-gray-100/60">
            {failedTasks.map((task) => {
              const isRetrying = retryingIds.has(task.id);
              return (
                <div key={task.id} className="px-6 py-4 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                  <div className="space-y-1.5 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-gray-900">{task.id}</span>
                      <span className="text-xs text-gray-400">|</span>
                      <span className="text-sm text-gray-600">{task.user}</span>
                      <ActionPill action={task.action} />
                    </div>
                    <div className="text-xs text-gray-500">
                      {task.role !== 'N/A' ? `${task.role} on ` : ''}{task.targetSystem}
                      {' '}· {task.retryCount} {task.retryCount === 1 ? 'retry' : 'retries'} attempted
                    </div>
                    {task.errorMessage && (
                      <div className="flex items-start gap-1.5 p-2.5 bg-red-50 border border-red-200/60 rounded-lg max-w-xl">
                        <ExclamationTriangleIcon className="h-3.5 w-3.5 text-red-500 flex-shrink-0 mt-0.5" />
                        <span className="text-xs text-red-700">{task.errorMessage}</span>
                      </div>
                    )}
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={<ArrowPathIcon className={`h-3.5 w-3.5 ${isRetrying ? 'animate-spin' : ''}`} />}
                    onClick={() => retryMutation.mutate(task.id)}
                    disabled={isRetrying || retryMutation.isPending}
                  >
                    {isRetrying ? 'Retrying...' : 'Retry'}
                  </Button>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Audit Trail */}
      <Card>
        <div className="px-6 py-4 border-b border-white/20 flex items-center gap-2">
          <ClockIcon className="h-4 w-4 text-gray-500" />
          <h2 className="text-sm font-semibold text-gray-900">Provisioning Audit Trail</h2>
        </div>
        <div className="divide-y divide-gray-100/60">
          {tasks
            .slice()
            .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
            .slice(0, 8)
            .map((task) => {
              const cfg = STATUS_CONFIG[task.status] ?? { variant: 'neutral' as const, label: task.status };
              return (
                <div key={task.id} className="flex items-start gap-3 px-6 py-3">
                  <div className="mt-0.5 flex-shrink-0">
                    {task.status === 'completed' && <CheckCircleIcon className="h-4 w-4 text-green-500" />}
                    {task.status === 'failed'    && <XCircleIcon className="h-4 w-4 text-red-500" />}
                    {task.status === 'queued'    && <ClockIcon className="h-4 w-4 text-gray-400" />}
                    {task.status === 'processing' && <PlayIcon className="h-4 w-4 text-blue-500" />}
                    {task.status === 'retrying'  && <ArrowPathIcon className="h-4 w-4 text-amber-500 animate-spin" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-sm font-medium text-gray-900">{task.user}</span>
                      <span className="text-xs text-gray-400">—</span>
                      <ActionPill action={task.action} />
                      {task.role !== 'N/A' && (
                        <span className="text-xs text-gray-600">{task.role}</span>
                      )}
                      <span className="text-xs text-gray-400">on</span>
                      <span className="text-xs text-gray-600">{task.targetSystem}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-gray-400">{task.id}</span>
                      <span className="text-xs text-gray-300">·</span>
                      <Badge variant={cfg.variant} size="sm">{cfg.label}</Badge>
                      {task.provisionedBy && (
                        <>
                          <span className="text-xs text-gray-300">·</span>
                          <span className="text-xs text-gray-400">by {task.provisionedBy}</span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="flex-shrink-0 text-xs text-gray-400 whitespace-nowrap">
                    {formatTimestamp(task.updatedAt)}
                  </div>
                </div>
              );
            })}
        </div>
        {tasks.length > 8 && (
          <div className="px-6 py-3 border-t border-white/20">
            <button
              className="text-xs text-primary-600 hover:text-primary-800 font-medium transition-colors"
              onClick={() => {
                setActiveTab('all');
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
            >
              View all {tasks.length} provisioning events
            </button>
          </div>
        )}
      </Card>
    </div>
  );
}
