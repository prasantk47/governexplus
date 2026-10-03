import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  PlayIcon,
  StopIcon,
  PlusIcon,
  ArrowPathIcon,
  EyeIcon,
  UserGroupIcon,
  ArrowLeftIcon,
  ExclamationTriangleIcon,
  BriefcaseIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
  Table,
  Modal,
  Input,
  Select,
  Textarea,
  LoadingState,
  ErrorState,
  EmptyState,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';

// ─── Types ────────────────────────────────────────────────────────────────────

type OperationType =
  | 'assign_role'
  | 'remove_role'
  | 'lock_user'
  | 'unlock_user'
  | 'change_department'
  | 'expire_role'
  | 'extend_role';

type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

interface UserResult {
  username: string;
  display_name: string;
  status: 'pending' | 'success' | 'failed' | 'skipped';
  message: string;
  processed_at?: string;
}

interface MassAdminJob {
  job_id: string;
  operation: OperationType;
  status: JobStatus;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  created_by: string;
  total_users: number;
  processed_users: number;
  failed_users: number;
  parameters: Record<string, string>;
  target_users: string[];
}

interface MassAdminJobDetail extends MassAdminJob {
  user_results: UserResult[];
}

interface MassAdminStats {
  total_jobs: number;
  running: number;
  completed: number;
  failed: number;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const OPERATION_OPTIONS = [
  { value: 'assign_role', label: 'Assign Role' },
  { value: 'remove_role', label: 'Remove Role' },
  { value: 'lock_user', label: 'Lock User' },
  { value: 'unlock_user', label: 'Unlock User' },
  { value: 'change_department', label: 'Change Department' },
  { value: 'expire_role', label: 'Expire Role' },
  { value: 'extend_role', label: 'Extend Role' },
];

const OPERATION_LABELS: Record<OperationType, string> = {
  assign_role: 'Assign Role',
  remove_role: 'Remove Role',
  lock_user: 'Lock User',
  unlock_user: 'Unlock User',
  change_department: 'Change Department',
  expire_role: 'Expire Role',
  extend_role: 'Extend Role',
};

const OPERATION_COLORS: Record<OperationType, string> = {
  assign_role: 'bg-green-100 text-green-800',
  remove_role: 'bg-red-100 text-red-800',
  lock_user: 'bg-orange-100 text-orange-800',
  unlock_user: 'bg-blue-100 text-blue-800',
  change_department: 'bg-purple-100 text-purple-800',
  expire_role: 'bg-gray-100 text-gray-800',
  extend_role: 'bg-indigo-100 text-indigo-800',
};

const STATUS_COLORS: Record<JobStatus, string> = {
  queued: 'bg-yellow-100 text-yellow-800',
  running: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-800',
};

const USER_RESULT_COLORS: Record<string, string> = {
  success: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  pending: 'bg-yellow-100 text-yellow-800',
  skipped: 'bg-gray-100 text-gray-700',
};

// ─── Helper components ────────────────────────────────────────────────────────

function ProgressBar({ value, total }: { value: number; total: number }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 bg-gray-200 rounded-full h-2">
        <div
          className="bg-primary-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 whitespace-nowrap">{value}/{total}</span>
    </div>
  );
}

function StatusPill({ status }: { status: JobStatus }) {
  const color = STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-800';
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {status === 'running' && <ArrowPathIcon className="w-3 h-3 animate-spin" />}
      {status === 'completed' && <CheckCircleIcon className="w-3 h-3" />}
      {status === 'failed' && <XCircleIcon className="w-3 h-3" />}
      {status === 'queued' && <ClockIcon className="w-3 h-3" />}
      {status === 'cancelled' && <StopIcon className="w-3 h-3" />}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function OperationPill({ op }: { op: OperationType }) {
  const color = OPERATION_COLORS[op] ?? 'bg-gray-100 text-gray-800';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {OPERATION_LABELS[op] ?? op}
    </span>
  );
}

function formatDate(iso?: string) {
  if (!iso) return '—';
  return new Date(iso || new Date()).toLocaleString();
}

// ─── Determine which extra parameter fields are needed ───────────────────────

function ParamFields({
  operation,
  params,
  onChange,
}: {
  operation: OperationType | '';
  params: Record<string, string>;
  onChange: (key: string, value: string) => void;
}) {
  if (!operation) return null;

  const roleOps: OperationType[] = ['assign_role', 'remove_role', 'expire_role', 'extend_role'];
  const showRole = roleOps.includes(operation as OperationType);
  const showDept = operation === 'change_department';
  const showDays = operation === 'extend_role';

  return (
    <div className="space-y-3">
      {showRole && (
        <Input
          label="Role Name"
          placeholder="e.g. Z_FI_DISPLAY"
          value={params.role_name ?? ''}
          onChange={(e) => onChange('role_name', e.target.value)}
          required
        />
      )}
      {showDept && (
        <Input
          label="Department"
          placeholder="e.g. Finance EMEA"
          value={params.department ?? ''}
          onChange={(e) => onChange('department', e.target.value)}
          required
        />
      )}
      {showDays && (
        <Input
          label="Extension (days)"
          type="number"
          placeholder="e.g. 90"
          value={params.extension_days ?? ''}
          onChange={(e) => onChange('extension_days', e.target.value)}
          required
        />
      )}
    </div>
  );
}

// ─── Job Detail Panel ─────────────────────────────────────────────────────────

function JobDetailPanel({
  jobId,
  onBack,
  onCancel,
}: {
  jobId: string;
  onBack: () => void;
  onCancel: (id: string) => void;
}) {
  const { data, isLoading, error } = useQuery<MassAdminJobDetail>({
    queryKey: ['mass-admin-job', jobId],
    queryFn: async () => {
      const res = await api.get(`/mass-admin/jobs/${jobId}`);
      return res.data;
    },
    refetchInterval: (data) =>
      data?.state?.data?.status === 'running' ? 3000 : false,
  });

  if (isLoading) return <LoadingState message="Loading job details..." />;
  if (error || !data) return <ErrorState message="Failed to load job details." />;

  const pct =
    data.total_users > 0
      ? Math.round((data.processed_users / data.total_users) * 100)
      : 0;

  const resultColumns = [
    {
      key: 'username',
      header: 'Username',
      render: (r: UserResult) => (
        <span className="font-mono text-sm text-gray-800">{r.username}</span>
      ),
    },
    {
      key: 'display_name',
      header: 'Display Name',
      render: (r: UserResult) => (
        <span className="text-sm text-gray-700">{r.display_name}</span>
      ),
    },
    {
      key: 'status',
      header: 'Result',
      render: (r: UserResult) => (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
            USER_RESULT_COLORS[r.status] ?? 'bg-gray-100 text-gray-800'
          }`}
        >
          {(r.status ?? 'unknown').charAt(0).toUpperCase() + (r.status ?? 'unknown').slice(1)}
        </span>
      ),
    },
    {
      key: 'message',
      header: 'Message',
      render: (r: UserResult) => (
        <span className="text-xs text-gray-600">{r.message}</span>
      ),
    },
    {
      key: 'processed_at',
      header: 'Processed At',
      render: (r: UserResult) => (
        <span className="text-xs text-gray-500">{formatDate(r.processed_at)}</span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Back + header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <ArrowLeftIcon className="w-4 h-4" />
          Back to jobs
        </button>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Job {data.job_id}
          </h2>
          <div className="flex items-center gap-2 mt-1">
            <OperationPill op={data.operation} />
            <StatusPill status={data.status} />
          </div>
        </div>
        {data.status === 'running' && (
          <Button
            variant="danger"
            size="sm"
            icon={<StopIcon className="w-4 h-4" />}
            onClick={() => onCancel(data.job_id)}
          >
            Cancel Job
          </Button>
        )}
      </div>

      {/* Meta cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white/60 backdrop-blur border border-gray-200 rounded-xl p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Created</p>
          <p className="mt-1 text-sm font-medium text-gray-800">{formatDate(data.created_at)}</p>
        </div>
        <div className="bg-white/60 backdrop-blur border border-gray-200 rounded-xl p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Created By</p>
          <p className="mt-1 text-sm font-medium text-gray-800">{data.created_by}</p>
        </div>
        <div className="bg-white/60 backdrop-blur border border-gray-200 rounded-xl p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Started</p>
          <p className="mt-1 text-sm font-medium text-gray-800">{formatDate(data.started_at)}</p>
        </div>
        <div className="bg-white/60 backdrop-blur border border-gray-200 rounded-xl p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Completed</p>
          <p className="mt-1 text-sm font-medium text-gray-800">{formatDate(data.completed_at)}</p>
        </div>
      </div>

      {/* Progress */}
      <Card>
        <div className="p-6 space-y-4">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Progress</h3>
          <div className="flex items-center gap-4">
            <div className="flex-1 bg-gray-200 rounded-full h-3">
              <div
                className="bg-primary-600 h-3 rounded-full transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-sm font-medium text-gray-700 w-12 text-right">{pct}%</span>
          </div>
          <div className="flex gap-6 text-sm text-gray-600">
            <span>
              <span className="font-semibold text-gray-900">{data.total_users}</span> total
            </span>
            <span>
              <span className="font-semibold text-green-700">{data.processed_users - data.failed_users}</span> succeeded
            </span>
            <span>
              <span className="font-semibold text-red-700">{data.failed_users}</span> failed
            </span>
          </div>

          {/* Parameters */}
          {Object.keys(data.parameters).length > 0 && (
            <div className="mt-2 pt-4 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Parameters</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(data.parameters).map(([k, v]) => (
                  <span key={k} className="px-2.5 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                    <span className="font-medium">{k}:</span> {v}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Per-user results */}
      <Card>
        <div className="p-6">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
            Per-User Results ({data.user_results?.length ?? 0})
          </h3>
          {data.user_results && data.user_results.length > 0 ? (
            <Table columns={resultColumns} data={data.user_results} />
          ) : (
            <EmptyState
              icon={<ClockIcon className="w-8 h-8 text-gray-400" />}
              title="No results yet"
              description="Results will appear as the job processes each user."
            />
          )}
        </div>
      </Card>
    </div>
  );
}

// ─── Create Job Form (inside a modal) ─────────────────────────────────────────

interface CreateJobFormProps {
  onClose: () => void;
  onSubmit: (payload: {
    operation: OperationType;
    target_users: string[];
    parameters: Record<string, string>;
  }) => void;
  isSubmitting: boolean;
}

function CreateJobForm({ onClose, onSubmit, isSubmitting }: CreateJobFormProps) {
  const [operation, setOperation] = useState<OperationType | ''>('');
  const [usersRaw, setUsersRaw] = useState('');
  const [params, setParams] = useState<Record<string, string>>({});

  const handleParamChange = (key: string, value: string) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!operation) {
      toast.error('Please select an operation type.');
      return;
    }
    const users = usersRaw
      .split(',')
      .map((u) => u.trim())
      .filter(Boolean);
    if (users.length === 0) {
      toast.error('Please enter at least one target user.');
      return;
    }
    onSubmit({ operation: operation as OperationType, target_users: users, parameters: params });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <Select
        label="Operation Type"
        value={operation}
        onChange={(e) => {
          setOperation(e.target.value as OperationType | '');
          setParams({});
        }}
        options={[{ value: '', label: 'Select operation…' }, ...OPERATION_OPTIONS]}
        required
      />

      <Textarea
        label="Target Users"
        placeholder="jsmith, mweber, lchen, aproctor"
        value={usersRaw}
        onChange={(e) => setUsersRaw(e.target.value)}
        rows={4}
        required
      />
      <p className="text-xs text-gray-400 -mt-2">Enter usernames separated by commas</p>

      <ParamFields operation={operation} params={params} onChange={handleParamChange} />

      {operation && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex gap-2">
          <ExclamationTriangleIcon className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-amber-800">
            This will run <strong>{OPERATION_LABELS[operation as OperationType]}</strong> on all
            listed users. The operation cannot be undone after completion.
          </p>
        </div>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <Button variant="secondary" type="button" onClick={onClose}>
          Cancel
        </Button>
        <Button
          variant="primary"
          type="submit"
          loading={isSubmitting}
          icon={<PlayIcon className="w-4 h-4" />}
        >
          Create &amp; Queue Job
        </Button>
      </div>
    </form>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function MassAdmin() {
  const queryClient = useQueryClient();
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [operationFilter, setOperationFilter] = useState('');

  // Stats
  const { data: stats } = useQuery<MassAdminStats | null>({
    queryKey: ['mass-admin-stats'],
    queryFn: async () => {
      try {
        const res = await api.get('/mass-admin/stats');
        return res.data;
      } catch {
        return null;
      }
    },
    refetchInterval: 10000,
  });

  // Jobs list
  const { data: jobsRaw, isLoading, error } = useQuery<MassAdminJob[]>({
    queryKey: ['mass-admin-jobs', { statusFilter, operationFilter }],
    queryFn: async () => {
      try {
        const res = await api.get('/mass-admin/jobs', {
          params: {
            status: statusFilter || undefined,
            operation: operationFilter || undefined,
          },
        });
        return res.data?.jobs ?? res.data ?? [];
      } catch {
        return [];
      }
    },
    refetchInterval: 5000,
  });

  const jobs: MassAdminJob[] = jobsRaw ?? [];

  // Create job
  const createMutation = useMutation({
    mutationFn: async (payload: {
      operation: OperationType;
      target_users: string[];
      parameters: Record<string, string>;
    }) => {
      const res = await api.post('/mass-admin/jobs', payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mass-admin-jobs'] });
      queryClient.invalidateQueries({ queryKey: ['mass-admin-stats'] });
      setShowCreateModal(false);
      toast.success('Bulk job created and queued.');
    },
    onError: () => {
      toast.error('Failed to create job.');
    },
  });

  // Cancel job
  const cancelMutation = useMutation({
    mutationFn: async (jobId: string) => {
      const res = await api.post(`/mass-admin/jobs/${jobId}/cancel`);
      return res.data;
    },
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: ['mass-admin-jobs'] });
      queryClient.invalidateQueries({ queryKey: ['mass-admin-job', jobId] });
      queryClient.invalidateQueries({ queryKey: ['mass-admin-stats'] });
      toast.success('Job cancellation requested.');
    },
    onError: () => {
      toast.error('Failed to cancel job.');
    },
  });

  // If a job is selected, render the detail panel
  if (selectedJobId) {
    return (
      <div className="p-6 space-y-6">
        <JobDetailPanel
          jobId={selectedJobId}
          onBack={() => setSelectedJobId(null)}
          onCancel={(id) => cancelMutation.mutate(id)}
        />
      </div>
    );
  }

  // Job table columns
  const columns = [
    {
      key: 'job_id',
      header: 'Job ID',
      render: (j: MassAdminJob) => (
        <span className="font-mono text-sm font-medium text-primary-700">{j.job_id}</span>
      ),
    },
    {
      key: 'operation',
      header: 'Operation',
      render: (j: MassAdminJob) => <OperationPill op={j.operation} />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (j: MassAdminJob) => <StatusPill status={j.status} />,
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (j: MassAdminJob) => (
        <span className="text-xs text-gray-500">{formatDate(j.created_at)}</span>
      ),
    },
    {
      key: 'created_by',
      header: 'By',
      render: (j: MassAdminJob) => (
        <span className="text-sm text-gray-700">{j.created_by}</span>
      ),
    },
    {
      key: 'progress',
      header: 'Progress',
      render: (j: MassAdminJob) => (
        <ProgressBar value={j.processed_users} total={j.total_users} />
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (j: MassAdminJob) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedJobId(j.job_id)}
            className="p-1.5 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded transition-colors"
            title="View details"
          >
            <EyeIcon className="w-4 h-4" />
          </button>
          {j.status === 'running' && (
            <button
              onClick={() => cancelMutation.mutate(j.job_id)}
              className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
              title="Cancel job"
              disabled={cancelMutation.isPending}
            >
              <StopIcon className="w-4 h-4" />
            </button>
          )}
        </div>
      ),
    },
  ];

  const displayStats = stats ?? { total_jobs: 0, running: 0, completed: 0, failed: 0 };

  return (
    <div className="p-6 space-y-6">
      {/* Page header */}
      <PageHeader
        title="Mass Administration"
        subtitle="Run bulk operations across users — assign roles, lock accounts, change departments, and more."
        actions={
          <Button
            variant="primary"
            icon={<PlusIcon className="w-4 h-4" />}
            onClick={() => setShowCreateModal(true)}
          >
            New Bulk Job
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Jobs"
          value={displayStats.total_jobs}
          icon={BriefcaseIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Running"
          value={displayStats.running}
          icon={ArrowPathIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Completed"
          value={displayStats.completed}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
        <StatCard
          title="Failed"
          value={displayStats.failed}
          icon={XCircleIcon}
          iconBgColor="stat-icon-red"
          iconColor="text-red-400"
        />
      </div>

      {/* Filters + Job queue */}
      <Card>
        <div className="p-6 space-y-4">
          {/* Filter row */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="w-full sm:w-56">
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                options={[
                  { value: '', label: 'All Statuses' },
                  { value: 'queued', label: 'Queued' },
                  { value: 'running', label: 'Running' },
                  { value: 'completed', label: 'Completed' },
                  { value: 'failed', label: 'Failed' },
                  { value: 'cancelled', label: 'Cancelled' },
                ]}
              />
            </div>
            <div className="w-full sm:w-56">
              <Select
                value={operationFilter}
                onChange={(e) => setOperationFilter(e.target.value)}
                options={[{ value: '', label: 'All Operations' }, ...OPERATION_OPTIONS]}
              />
            </div>
            <div className="flex-1" />
            <Button
              variant="ghost"
              size="sm"
              icon={<ArrowPathIcon className="w-4 h-4" />}
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ['mass-admin-jobs'] });
                queryClient.invalidateQueries({ queryKey: ['mass-admin-stats'] });
              }}
            >
              Refresh
            </Button>
          </div>

          {/* Table */}
          {isLoading ? (
            <LoadingState message="Loading jobs..." />
          ) : error ? (
            <ErrorState message="Failed to load job queue." />
          ) : jobs.length === 0 ? (
            <EmptyState
              icon={<UserGroupIcon className="w-8 h-8 text-gray-400" />}
              title="No bulk jobs found"
              description="Create your first bulk job to get started."
              action={
                <Button
                  variant="primary"
                  size="sm"
                  icon={<PlusIcon className="w-4 h-4" />}
                  onClick={() => setShowCreateModal(true)}
                >
                  New Bulk Job
                </Button>
              }
            />
          ) : (
            <Table columns={columns} data={jobs} />
          )}
        </div>
      </Card>

      {/* Running jobs banner */}
      {displayStats.running > 0 && (
        <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-xl px-4 py-3">
          <ArrowPathIcon className="w-5 h-5 text-blue-500 animate-spin flex-shrink-0" />
          <p className="text-sm text-blue-800">
            <span className="font-semibold">{displayStats.running}</span> job
            {displayStats.running > 1 ? 's are' : ' is'} currently running. The table
            auto-refreshes every 5 seconds.
          </p>
        </div>
      )}

      {/* Create job modal */}
      <Modal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create Bulk Job"
        size="md"
      >
        <CreateJobForm
          onClose={() => setShowCreateModal(false)}
          onSubmit={(payload) => createMutation.mutate(payload)}
          isSubmitting={createMutation.isPending}
        />
      </Modal>
    </div>
  );
}
