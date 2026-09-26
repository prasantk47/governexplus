import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
  ClockIcon,
  CheckCircleIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/react/24/outline';
import {
  PageHeader,
  Card,
  Button,
  Table,
  Badge,
  Modal,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import { processControlApi } from '../../services/processControlApi';

// ─── Types ────────────────────────────────────────────────────────────────────

type DeficiencySeverity =
  | 'significant_deficiency'
  | 'material_weakness'
  | 'control_gap'
  | 'observation';

type DeficiencyStatus =
  | 'open'
  | 'in_remediation'
  | 'remediated'
  | 'verified'
  | 'closed'
  | 'accepted';

type DeficiencySource =
  | 'internal_audit'
  | 'external_audit'
  | 'control_testing'
  | 'self_assessment'
  | 'ccm'
  | 'management';

interface Deficiency {
  id: string;
  deficiency_id: string;
  title: string;
  description: string;
  control_id: string;
  control_name: string;
  source: DeficiencySource;
  severity: DeficiencySeverity;
  owner: string;
  due_date: string;
  status: DeficiencyStatus;
  remediation_plan: string;
  created_at: string;
  updated_at?: string;
}

interface CreateDeficiencyForm {
  title: string;
  description: string;
  control_id: string;
  source: DeficiencySource;
  severity: DeficiencySeverity;
  owner: string;
  due_date: string;
}

interface RemediateForm {
  remediation_plan: string;
  evidence_ids: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const SEVERITIES: DeficiencySeverity[] = [
  'observation',
  'control_gap',
  'significant_deficiency',
  'material_weakness',
];

const SOURCES: DeficiencySource[] = [
  'internal_audit',
  'external_audit',
  'control_testing',
  'self_assessment',
  'ccm',
  'management',
];

const STATUSES: DeficiencyStatus[] = [
  'open',
  'in_remediation',
  'remediated',
  'verified',
  'closed',
  'accepted',
];

const severityVariant: Record<
  DeficiencySeverity,
  'danger' | 'warning' | 'info' | 'default'
> = {
  material_weakness: 'danger',
  significant_deficiency: 'warning',
  control_gap: 'info',
  observation: 'default',
};

const statusVariant: Record<
  DeficiencyStatus,
  'danger' | 'warning' | 'info' | 'success' | 'neutral' | 'default'
> = {
  open: 'danger',
  in_remediation: 'warning',
  remediated: 'info',
  verified: 'success',
  closed: 'neutral',
  accepted: 'neutral',
};

const sourceVariant: Record<DeficiencySource, 'info' | 'warning' | 'success' | 'default' | 'neutral'> = {
  internal_audit: 'info',
  external_audit: 'warning',
  control_testing: 'default',
  self_assessment: 'default',
  ccm: 'success',
  management: 'neutral',
};

const emptyCreateForm: CreateDeficiencyForm = {
  title: '',
  description: '',
  control_id: '',
  source: 'control_testing',
  severity: 'control_gap',
  owner: '',
  due_date: '',
};

const emptyRemediateForm: RemediateForm = {
  remediation_plan: '',
  evidence_ids: '',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function labelFor(val: string): string {
  return val.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function fmtDate(iso: string): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function isOverdue(deficiency: Deficiency): boolean {
  if (!deficiency.due_date) return false;
  if (deficiency.status === 'closed' || deficiency.status === 'verified') return false;
  return new Date(deficiency.due_date) < new Date();
}

// ─── Component ────────────────────────────────────────────────────────────────

export function DeficiencyTracker() {
  const queryClient = useQueryClient();

  // Filters
  const [search, setSearch] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSource, setFilterSource] = useState('');

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [remediateTarget, setRemediateTarget] = useState<Deficiency | null>(null);
  const [verifyTarget, setVerifyTarget] = useState<Deficiency | null>(null);

  // Forms
  const [createForm, setCreateForm] = useState<CreateDeficiencyForm>(emptyCreateForm);
  const [remediateForm, setRemediateForm] = useState<RemediateForm>(emptyRemediateForm);

  // ─── Queries ──────────────────────────────────────────────────────────────

  const { data: controlsData } = useQuery({
    queryKey: ['controls-list-for-deficiency'],
    queryFn: () => processControlApi.listControls().then((r) => r.data),
  });

  const { data, isLoading } = useQuery({
    queryKey: [
      'deficiencies',
      filterSeverity,
      filterStatus,
      filterSource,
    ],
    queryFn: () =>
      processControlApi
        .listDeficiencies({
          severity: filterSeverity || undefined,
          status: filterStatus || undefined,
          source: filterSource || undefined,
        })
        .then((r) => r.data),
  });

  // ─── Mutations ────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      processControlApi.createDeficiency(payload),
    onSuccess: () => {
      toast.success('Deficiency created');
      queryClient.invalidateQueries({ queryKey: ['deficiencies'] });
      setShowCreateModal(false);
      setCreateForm(emptyCreateForm);
    },
    onError: () => toast.error('Failed to create deficiency'),
  });

  const remediateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) =>
      processControlApi.remediateDeficiency(id, payload),
    onSuccess: () => {
      toast.success('Remediation plan submitted');
      queryClient.invalidateQueries({ queryKey: ['deficiencies'] });
      setRemediateTarget(null);
      setRemediateForm(emptyRemediateForm);
    },
    onError: () => toast.error('Failed to submit remediation'),
  });

  const verifyMutation = useMutation({
    mutationFn: (id: string) => processControlApi.verifyDeficiency(id),
    onSuccess: () => {
      toast.success('Deficiency verified and closed');
      queryClient.invalidateQueries({ queryKey: ['deficiencies'] });
      setVerifyTarget(null);
    },
    onError: () => toast.error('Failed to verify deficiency'),
  });

  // ─── Data processing ──────────────────────────────────────────────────────

  const controls = Array.isArray(controlsData)
    ? controlsData
    : (controlsData as any)?.controls ?? [];

  const allDeficiencies: Deficiency[] = Array.isArray(data) ? data : (data as any)?.deficiencies ?? [];

  const filtered = allDeficiencies.filter((d) => {
    const matchSearch =
      !search ||
      d.title?.toLowerCase().includes(search.toLowerCase()) ||
      d.deficiency_id?.toLowerCase().includes(search.toLowerCase()) ||
      d.owner?.toLowerCase().includes(search.toLowerCase()) ||
      d.control_name?.toLowerCase().includes(search.toLowerCase());
    return matchSearch;
  });

  // Stats
  const totalCount = allDeficiencies.length;
  const openCount = allDeficiencies.filter((d) => d.status === 'open').length;
  const inRemediationCount = allDeficiencies.filter(
    (d) => d.status === 'in_remediation'
  ).length;
  const overdueCount = allDeficiencies.filter(isOverdue).length;

  // ─── Handlers ─────────────────────────────────────────────────────────────

  function handleCreate() {
    if (!createForm.title) {
      toast.error('Title is required');
      return;
    }
    createMutation.mutate(createForm as unknown as Record<string, unknown>);
  }

  function handleRemediate() {
    if (!remediateTarget) return;
    if (!remediateForm.remediation_plan) {
      toast.error('Remediation plan is required');
      return;
    }
    const payload = {
      remediation_plan: remediateForm.remediation_plan,
      evidence_ids: remediateForm.evidence_ids
        ? remediateForm.evidence_ids.split(',').map((s) => s.trim()).filter(Boolean)
        : [],
    };
    remediateMutation.mutate({ id: remediateTarget.id, payload: payload as Record<string, unknown> });
  }

  function openRemediate(d: Deficiency) {
    setRemediateTarget(d);
    setRemediateForm({
      remediation_plan: d.remediation_plan ?? '',
      evidence_ids: '',
    });
  }

  // ─── Table columns ────────────────────────────────────────────────────────

  const columns = [
    {
      key: 'deficiency_id',
      header: 'ID',
      render: (d: Deficiency) => (
        <span className="text-xs font-mono text-indigo-600 dark:text-indigo-400">
          {d.deficiency_id ?? d.id.slice(0, 8)}
        </span>
      ),
    },
    {
      key: 'title',
      header: 'Title',
      render: (d: Deficiency) => (
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{d.title}</p>
          {d.description && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-1">
              {d.description}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'control_name',
      header: 'Control',
      render: (d: Deficiency) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">
          {d.control_name ?? d.control_id ?? '—'}
        </span>
      ),
    },
    {
      key: 'source',
      header: 'Source',
      render: (d: Deficiency) => (
        <Badge variant={sourceVariant[d.source] ?? 'default'}>
          {labelFor(d.source)}
        </Badge>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (d: Deficiency) => (
        <Badge variant={severityVariant[d.severity] ?? 'default'} dot>
          {labelFor(d.severity)}
        </Badge>
      ),
    },
    {
      key: 'owner',
      header: 'Owner',
      render: (d: Deficiency) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{d.owner ?? '—'}</span>
      ),
    },
    {
      key: 'due_date',
      header: 'Due Date',
      render: (d: Deficiency) => (
        <span
          className={`text-sm font-medium ${
            isOverdue(d)
              ? 'text-red-600 dark:text-red-400'
              : 'text-gray-600 dark:text-gray-400'
          }`}
        >
          {fmtDate(d.due_date)}
          {isOverdue(d) && <span className="ml-1 text-xs">(Overdue)</span>}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (d: Deficiency) => (
        <Badge variant={statusVariant[d.status] ?? 'default'} dot>
          {labelFor(d.status)}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (d: Deficiency) => (
        <div className="flex items-center gap-1.5">
          {(d.status === 'open' || d.status === 'in_remediation') && (
            <Button
              size="sm"
              variant="ghost"
              icon={<WrenchScrewdriverIcon className="h-3.5 w-3.5" />}
              onClick={() => openRemediate(d)}
            >
              Remediate
            </Button>
          )}
          {d.status === 'remediated' && (
            <Button
              size="sm"
              variant="success"
              icon={<CheckCircleIcon className="h-3.5 w-3.5" />}
              onClick={() => setVerifyTarget(d)}
              loading={verifyMutation.isPending && verifyTarget?.id === d.id}
            >
              Verify
            </Button>
          )}
        </div>
      ),
    },
  ];

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div>
      <PageHeader
        title="Deficiency Tracker"
        subtitle="Track, remediate, and verify control deficiencies"
        actions={
          <Button
            icon={<PlusIcon className="h-4 w-4" />}
            onClick={() => setShowCreateModal(true)}
          >
            Log Deficiency
          </Button>
        }
      />

      {/* Stat Cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard
          title="Total Deficiencies"
          value={totalCount}
          icon={ShieldExclamationIcon}
          iconBgColor="bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400"
          iconColor="text-indigo-600"
        />
        <StatCard
          title="Open"
          value={openCount}
          icon={ExclamationTriangleIcon}
          iconBgColor="bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400"
          iconColor="text-red-600"
        />
        <StatCard
          title="In Remediation"
          value={inRemediationCount}
          icon={WrenchScrewdriverIcon}
          iconBgColor="bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400"
          iconColor="text-amber-600"
        />
        <StatCard
          title="Overdue"
          value={overdueCount}
          icon={ClockIcon}
          iconBgColor="bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400"
          iconColor="text-orange-600"
        />
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <div className="flex flex-wrap gap-3 items-center">
          <FunnelIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />

          <div className="relative flex-1 min-w-[200px]">
            <MagnifyingGlassIcon className="h-4 w-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by title, ID, control, owner..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-4 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Severities</option>
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {labelFor(s)}
              </option>
            ))}
          </select>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {labelFor(s)}
              </option>
            ))}
          </select>

          <select
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Sources</option>
            {SOURCES.map((s) => (
              <option key={s} value={s}>
                {labelFor(s)}
              </option>
            ))}
          </select>
        </div>
      </Card>

      {/* Deficiencies table */}
      <Card padding="none">
        <Table
          columns={columns}
          data={filtered}
          loading={isLoading}
          emptyMessage="No deficiencies found. The control environment looks clean!"
        />
      </Card>

      {/* Create Deficiency Modal */}
      <Modal
        open={showCreateModal}
        onClose={() => {
          setShowCreateModal(false);
          setCreateForm(emptyCreateForm);
        }}
        title="Log Deficiency"
        subtitle="Record a control deficiency for tracking and remediation"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              loading={createMutation.isPending}
              icon={<ExclamationTriangleIcon className="h-4 w-4" />}
            >
              Log Deficiency
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Title */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Title *
              </label>
              <input
                type="text"
                value={createForm.title}
                onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                placeholder="e.g. AP invoice approval bypass for FI posting"
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Description */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Description
              </label>
              <textarea
                value={createForm.description}
                onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                rows={3}
                placeholder="Describe the deficiency, root cause, and potential impact..."
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
              />
            </div>

            {/* Control */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Related Control
              </label>
              <select
                value={createForm.control_id}
                onChange={(e) => setCreateForm({ ...createForm, control_id: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">No linked control</option>
                {controls.map((c: any) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Source */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Source
              </label>
              <select
                value={createForm.source}
                onChange={(e) =>
                  setCreateForm({ ...createForm, source: e.target.value as DeficiencySource })
                }
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {SOURCES.map((s) => (
                  <option key={s} value={s}>
                    {labelFor(s)}
                  </option>
                ))}
              </select>
            </div>

            {/* Severity */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Severity
              </label>
              <select
                value={createForm.severity}
                onChange={(e) =>
                  setCreateForm({ ...createForm, severity: e.target.value as DeficiencySeverity })
                }
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {labelFor(s)}
                  </option>
                ))}
              </select>
            </div>

            {/* Owner */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Owner
              </label>
              <input
                type="text"
                value={createForm.owner}
                onChange={(e) => setCreateForm({ ...createForm, owner: e.target.value })}
                placeholder="Responsible owner or team"
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Due Date */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Remediation Due Date
              </label>
              <input
                type="date"
                value={createForm.due_date}
                onChange={(e) => setCreateForm({ ...createForm, due_date: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
        </div>
      </Modal>

      {/* Remediate Modal */}
      <Modal
        open={!!remediateTarget}
        onClose={() => {
          setRemediateTarget(null);
          setRemediateForm(emptyRemediateForm);
        }}
        title="Submit Remediation Plan"
        subtitle={remediateTarget?.title ?? undefined}
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setRemediateTarget(null)}>
              Cancel
            </Button>
            <Button
              onClick={handleRemediate}
              loading={remediateMutation.isPending}
              icon={<WrenchScrewdriverIcon className="h-4 w-4" />}
            >
              Submit Plan
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Remediation Plan *
            </label>
            <textarea
              value={remediateForm.remediation_plan}
              onChange={(e) => setRemediateForm({ ...remediateForm, remediation_plan: e.target.value })}
              rows={5}
              placeholder="Describe the corrective actions, timeline, and responsible parties..."
              className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Supporting Evidence IDs (comma-separated)
            </label>
            <input
              type="text"
              value={remediateForm.evidence_ids}
              onChange={(e) => setRemediateForm({ ...remediateForm, evidence_ids: e.target.value })}
              placeholder="e.g. EVD-001, EVD-002"
              className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      </Modal>

      {/* Verify Confirmation Modal */}
      <Modal
        open={!!verifyTarget}
        onClose={() => setVerifyTarget(null)}
        title="Verify Remediation"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setVerifyTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="success"
              onClick={() => verifyTarget && verifyMutation.mutate(verifyTarget.id)}
              loading={verifyMutation.isPending}
              icon={<CheckCircleIcon className="h-4 w-4" />}
            >
              Confirm Verified
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-gray-700 dark:text-gray-300">
            Confirm that the remediation for{' '}
            <span className="font-semibold">{verifyTarget?.title}</span> has been
            independently verified and the deficiency is resolved.
          </p>
          <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800">
            <p className="text-xs text-emerald-700 dark:text-emerald-400">
              This action will close the deficiency and stamp the audit trail with your
              verification timestamp and user identity.
            </p>
          </div>
        </div>
      </Modal>
    </div>
  );
}
