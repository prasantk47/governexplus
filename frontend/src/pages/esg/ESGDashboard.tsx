import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  GlobeAltIcon,
  UserGroupIcon,
  BuildingLibraryIcon,
  ChartBarIcon,
  CheckBadgeIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  Table,
  Modal,
  Input,
  Select,
  SearchInput,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type Pillar = 'environmental' | 'social' | 'governance';
type CommitmentStatus = 'on_track' | 'at_risk' | 'behind' | 'completed' | 'not_started';

interface Commitment {
  id: string;
  title: string;
  pillar: Pillar;
  category: string;
  framework: string;
  target_value: number;
  current_value: number;
  progress_pct: number;
  status: CommitmentStatus;
  target_unit: string;
  owner: string;
  created_at: string;
}

interface ESGMetric {
  id: string;
  name: string;
  pillar: Pillar;
  value: number;
  unit: string;
  period: string;
  verified: boolean;
  commitment_id?: string;
  created_at: string;
}

interface ESGDashboardData {
  commitments_by_pillar: Record<string, number>;
  commitments_by_status: Record<string, number>;
  verification_rate: number;
  total_commitments: number;
  total_metrics: number;
}

interface CommitmentForm {
  title: string;
  pillar: Pillar | '';
  category: string;
  framework: string;
  target_value: string;
  target_unit: string;
  owner: string;
}

interface MetricForm {
  name: string;
  pillar: Pillar | '';
  value: string;
  unit: string;
  period: string;
  commitment_id: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_COMMITMENT_FORM: CommitmentForm = {
  title: '',
  pillar: '',
  category: '',
  framework: '',
  target_value: '',
  target_unit: '',
  owner: '',
};

const EMPTY_METRIC_FORM: MetricForm = {
  name: '',
  pillar: '',
  value: '',
  unit: '',
  period: '',
  commitment_id: '',
};

const PILLAR_VARIANT: Record<Pillar, 'success' | 'info' | 'warning'> = {
  environmental: 'success',
  social: 'info',
  governance: 'warning',
};

const PILLAR_LABEL: Record<Pillar, string> = {
  environmental: 'E',
  social: 'S',
  governance: 'G',
};

const PILLAR_ICON: Record<Pillar, typeof GlobeAltIcon> = {
  environmental: GlobeAltIcon,
  social: UserGroupIcon,
  governance: BuildingLibraryIcon,
};

const STATUS_VARIANT: Record<CommitmentStatus, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  on_track: 'success',
  at_risk: 'warning',
  behind: 'danger',
  completed: 'info',
  not_started: 'neutral',
};

const PILLAR_OPTIONS = [
  { value: 'environmental', label: 'Environmental' },
  { value: 'social', label: 'Social' },
  { value: 'governance', label: 'Governance' },
];

// ─── Progress Bar ─────────────────────────────────────────────────────────────

function ProgressBar({ pct }: { pct: number }) {
  const clamped = Math.min(100, Math.max(0, pct));
  const color =
    clamped >= 75 ? 'bg-green-500' : clamped >= 50 ? 'bg-yellow-400' : clamped >= 25 ? 'bg-orange-400' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${clamped}%` }} />
      </div>
      <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{Math.round(clamped)}%</span>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ESGDashboard() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<'commitments' | 'metrics' | 'dashboard'>('commitments');
  const [search, setSearch] = useState('');
  const [showCommitmentModal, setShowCommitmentModal] = useState(false);
  const [showMetricModal, setShowMetricModal] = useState(false);
  const [commitmentForm, setCommitmentForm] = useState<CommitmentForm>(EMPTY_COMMITMENT_FORM);
  const [metricForm, setMetricForm] = useState<MetricForm>(EMPTY_METRIC_FORM);
  const [commitmentErrors, setCommitmentErrors] = useState<Partial<Record<keyof CommitmentForm, string>>>({});
  const [metricErrors, setMetricErrors] = useState<Partial<Record<keyof MetricForm, string>>>({});

  // ── Queries ──

  const { data: dashData } = useQuery<ESGDashboardData>({
    queryKey: ['esg-dashboard'],
    queryFn: () =>
      api.get('/esg/dashboard').then(r => r.data ?? {
        commitments_by_pillar: {},
        commitments_by_status: {},
        verification_rate: 0,
        total_commitments: 0,
        total_metrics: 0,
      }),
  });

  const dash: ESGDashboardData = dashData ?? {
    commitments_by_pillar: {},
    commitments_by_status: {},
    verification_rate: 0,
    total_commitments: 0,
    total_metrics: 0,
  };

  const { data: commitmentsData, isLoading: commitmentsLoading } = useQuery<Commitment[]>({
    queryKey: ['esg-commitments'],
    queryFn: () =>
      api.get('/esg/commitments').then(r => r.data?.commitments ?? r.data ?? []),
    enabled: tab === 'commitments' || tab === 'dashboard',
  });

  const commitments: Commitment[] = commitmentsData ?? [];

  const { data: metricsData, isLoading: metricsLoading } = useQuery<ESGMetric[]>({
    queryKey: ['esg-metrics'],
    queryFn: () =>
      api.get('/esg/metrics').then(r => r.data?.metrics ?? r.data ?? []),
    enabled: tab === 'metrics' || tab === 'dashboard',
  });

  const metrics: ESGMetric[] = metricsData ?? [];

  // ── Filtering ──

  const filteredCommitments = commitments.filter(c => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.title.toLowerCase().includes(q) ||
      c.category.toLowerCase().includes(q) ||
      c.framework.toLowerCase().includes(q) ||
      c.owner.toLowerCase().includes(q)
    );
  });

  const filteredMetrics = metrics.filter(m => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      m.name.toLowerCase().includes(q) ||
      m.pillar.toLowerCase().includes(q) ||
      m.period.toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createCommitmentMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/esg/commitments', data),
    onSuccess: () => {
      toast.success('Commitment created');
      queryClient.invalidateQueries({ queryKey: ['esg-commitments'] });
      queryClient.invalidateQueries({ queryKey: ['esg-dashboard'] });
      closeCommitmentModal();
    },
    onError: () => toast.error('Failed to create commitment'),
  });

  const createMetricMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/esg/metrics', data),
    onSuccess: () => {
      toast.success('Metric recorded');
      queryClient.invalidateQueries({ queryKey: ['esg-metrics'] });
      queryClient.invalidateQueries({ queryKey: ['esg-dashboard'] });
      closeMetricModal();
    },
    onError: () => toast.error('Failed to record metric'),
  });

  // ── Handlers ──

  function closeCommitmentModal() {
    setShowCommitmentModal(false);
    setCommitmentForm(EMPTY_COMMITMENT_FORM);
    setCommitmentErrors({});
  }

  function closeMetricModal() {
    setShowMetricModal(false);
    setMetricForm(EMPTY_METRIC_FORM);
    setMetricErrors({});
  }

  function validateCommitment(): boolean {
    const errors: Partial<Record<keyof CommitmentForm, string>> = {};
    if (!commitmentForm.title.trim()) errors.title = 'Title is required';
    if (!commitmentForm.pillar) errors.pillar = 'Pillar is required';
    if (!commitmentForm.owner.trim()) errors.owner = 'Owner is required';
    setCommitmentErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function validateMetric(): boolean {
    const errors: Partial<Record<keyof MetricForm, string>> = {};
    if (!metricForm.name.trim()) errors.name = 'Name is required';
    if (!metricForm.pillar) errors.pillar = 'Pillar is required';
    if (!metricForm.value) errors.value = 'Value is required';
    setMetricErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleCreateCommitment() {
    if (!validateCommitment()) return;
    createCommitmentMutation.mutate({
      ...commitmentForm,
      target_value: commitmentForm.target_value ? Number(commitmentForm.target_value) : undefined,
    });
  }

  function handleCreateMetric() {
    if (!validateMetric()) return;
    createMetricMutation.mutate({
      ...metricForm,
      value: Number(metricForm.value),
      commitment_id: metricForm.commitment_id || undefined,
    });
  }

  function setCommitmentField<K extends keyof CommitmentForm>(key: K, value: CommitmentForm[K]) {
    setCommitmentForm(prev => ({ ...prev, [key]: value }));
    if (commitmentErrors[key]) setCommitmentErrors(prev => ({ ...prev, [key]: undefined }));
  }

  function setMetricField<K extends keyof MetricForm>(key: K, value: MetricForm[K]) {
    setMetricForm(prev => ({ ...prev, [key]: value }));
    if (metricErrors[key]) setMetricErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Commitment Columns ──

  const commitmentColumns = [
    {
      key: 'title',
      header: 'Commitment',
      render: (c: Commitment) => (
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100 max-w-xs truncate">
          {c.title}
        </div>
      ),
    },
    {
      key: 'pillar',
      header: 'Pillar',
      render: (c: Commitment) => (
        <Badge variant={PILLAR_VARIANT[c.pillar]} size="sm">
          {PILLAR_LABEL[c.pillar]} — {c.pillar}
        </Badge>
      ),
    },
    {
      key: 'category',
      header: 'Category',
      render: (c: Commitment) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{c.category || '—'}</span>
      ),
    },
    {
      key: 'framework',
      header: 'Framework',
      render: (c: Commitment) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{c.framework || '—'}</span>
      ),
    },
    {
      key: 'target',
      header: 'Target',
      render: (c: Commitment) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">
          {c.target_value} {c.target_unit}
        </span>
      ),
    },
    {
      key: 'current',
      header: 'Current',
      render: (c: Commitment) => (
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {c.current_value} {c.target_unit}
        </span>
      ),
    },
    {
      key: 'progress',
      header: 'Progress',
      render: (c: Commitment) => <ProgressBar pct={c.progress_pct} />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (c: Commitment) => (
        <Badge variant={STATUS_VARIANT[c.status]} dot size="sm">
          {c.status.replace(/_/g, ' ')}
        </Badge>
      ),
    },
  ];

  // ── Metric Columns ──

  const metricColumns = [
    {
      key: 'name',
      header: 'Metric',
      render: (m: ESGMetric) => (
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{m.name}</div>
      ),
    },
    {
      key: 'pillar',
      header: 'Pillar',
      render: (m: ESGMetric) => (
        <Badge variant={PILLAR_VARIANT[m.pillar]} size="sm">
          {PILLAR_LABEL[m.pillar]}
        </Badge>
      ),
    },
    {
      key: 'value',
      header: 'Value',
      render: (m: ESGMetric) => (
        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{m.value}</span>
      ),
    },
    {
      key: 'unit',
      header: 'Unit',
      render: (m: ESGMetric) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{m.unit || '—'}</span>
      ),
    },
    {
      key: 'period',
      header: 'Period',
      render: (m: ESGMetric) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{m.period}</span>
      ),
    },
    {
      key: 'verified',
      header: 'Verified',
      render: (m: ESGMetric) =>
        m.verified ? (
          <Badge variant="success" size="sm">Verified</Badge>
        ) : (
          <span className="text-sm text-gray-400">Pending</span>
        ),
    },
  ];

  const tabItems = [
    { key: 'commitments' as const, label: 'Commitments' },
    { key: 'metrics' as const, label: 'Metrics' },
    { key: 'dashboard' as const, label: 'Dashboard' },
  ];

  // ── Dashboard Summary ──

  const envCount = dash.commitments_by_pillar?.environmental ?? 0;
  const socCount = dash.commitments_by_pillar?.social ?? 0;
  const govCount = dash.commitments_by_pillar?.governance ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="ESG Dashboard"
        subtitle="Environmental, Social, and Governance commitments and metrics"
        actions={
          <div className="flex gap-2">
            <Button
              variant="secondary"
              icon={<ChartBarIcon className="h-4 w-4" />}
              onClick={() => { setMetricForm(EMPTY_METRIC_FORM); setMetricErrors({}); setShowMetricModal(true); }}
            >
              Record Metric
            </Button>
            <Button
              icon={<PlusIcon className="h-4 w-4" />}
              onClick={() => { setCommitmentForm(EMPTY_COMMITMENT_FORM); setCommitmentErrors({}); setShowCommitmentModal(true); }}
            >
              New Commitment
            </Button>
          </div>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Environmental" value={envCount} icon={GlobeAltIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Social" value={socCount} icon={UserGroupIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Governance" value={govCount} icon={BuildingLibraryIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Verification Rate" value={`${Math.round(dash.verification_rate)}%`} icon={CheckBadgeIcon} iconBgColor="stat-icon-indigo" iconColor="" />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex -mb-px space-x-6">
          {tabItems.map(t => (
            <button
              key={t.key}
              onClick={() => { setTab(t.key); setSearch(''); }}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t.key
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Commitments Tab */}
      {tab === 'commitments' && (
        <>
          <Card padding="md">
            <SearchInput
              placeholder="Search commitments..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </Card>
          <Table
            columns={commitmentColumns}
            data={filteredCommitments}
            loading={commitmentsLoading}
            emptyMessage="No ESG commitments found. Click 'New Commitment' to add one."
          />
        </>
      )}

      {/* Metrics Tab */}
      {tab === 'metrics' && (
        <>
          <Card padding="md">
            <SearchInput
              placeholder="Search metrics..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </Card>
          <Table
            columns={metricColumns}
            data={filteredMetrics}
            loading={metricsLoading}
            emptyMessage="No ESG metrics recorded. Click 'Record Metric' to add one."
          />
        </>
      )}

      {/* Dashboard Tab */}
      {tab === 'dashboard' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Commitments by Pillar */}
          <Card padding="lg">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Commitments by Pillar</h3>
            <div className="space-y-3">
              {(['environmental', 'social', 'governance'] as Pillar[]).map(pillar => {
                const Icon = PILLAR_ICON[pillar];
                const count = dash.commitments_by_pillar?.[pillar] ?? 0;
                const total = dash.total_commitments || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={pillar} className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${
                      pillar === 'environmental' ? 'bg-green-100 dark:bg-green-900/30' :
                      pillar === 'social' ? 'bg-blue-100 dark:bg-blue-900/30' :
                      'bg-orange-100 dark:bg-orange-900/30'
                    }`}>
                      <Icon className={`h-5 w-5 ${
                        pillar === 'environmental' ? 'text-green-600 dark:text-green-400' :
                        pillar === 'social' ? 'text-blue-600 dark:text-blue-400' :
                        'text-orange-600 dark:text-orange-400'
                      }`} />
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium text-gray-900 dark:text-gray-100 capitalize">{pillar}</span>
                        <span className="text-gray-500">{count} ({pct}%)</span>
                      </div>
                      <div className="w-full h-2 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            pillar === 'environmental' ? 'bg-green-500' :
                            pillar === 'social' ? 'bg-blue-500' : 'bg-orange-500'
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Commitments by Status */}
          <Card padding="lg">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Commitments by Status</h3>
            <div className="space-y-2">
              {Object.entries(dash.commitments_by_status ?? {}).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800 last:border-0">
                  <Badge variant={STATUS_VARIANT[status as CommitmentStatus] ?? 'neutral'} dot size="sm">
                    {status.replace(/_/g, ' ')}
                  </Badge>
                  <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{count}</span>
                </div>
              ))}
              {Object.keys(dash.commitments_by_status ?? {}).length === 0 && (
                <p className="text-sm text-gray-400 text-center py-4">No status data available</p>
              )}
            </div>
          </Card>

          {/* Verification Rate */}
          <Card padding="lg">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Metric Verification Rate</h3>
            <div className="flex items-center justify-center py-6">
              <div className="text-center">
                <div className="text-4xl font-bold text-indigo-600 dark:text-indigo-400">
                  {Math.round(dash.verification_rate)}%
                </div>
                <p className="text-sm text-gray-500 mt-1">of metrics are verified</p>
                <p className="text-xs text-gray-400 mt-2">
                  {dash.total_metrics} total metrics recorded
                </p>
              </div>
            </div>
          </Card>

          {/* Summary */}
          <Card padding="lg">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">ESG Summary</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-800">
                <span className="text-sm text-gray-600 dark:text-gray-400">Total Commitments</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{dash.total_commitments}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-800">
                <span className="text-sm text-gray-600 dark:text-gray-400">Total Metrics</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{dash.total_metrics}</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">Frameworks Covered</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {[...new Set(commitments.map(c => c.framework).filter(Boolean))].length}
                </span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Create Commitment Modal */}
      <Modal
        open={showCommitmentModal}
        onClose={closeCommitmentModal}
        title="New ESG Commitment"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={closeCommitmentModal}>Cancel</Button>
            <Button onClick={handleCreateCommitment} loading={createCommitmentMutation.isPending}>
              Create Commitment
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Title"
                required
                value={commitmentForm.title}
                onChange={e => setCommitmentField('title', e.target.value)}
                error={commitmentErrors.title}
                placeholder="e.g. Reduce carbon emissions by 30%"
              />
            </div>
            <Select
              label="Pillar"
              required
              value={commitmentForm.pillar}
              onChange={e => setCommitmentField('pillar', e.target.value as Pillar)}
              options={[{ value: '', label: 'Select pillar...' }, ...PILLAR_OPTIONS]}
              error={commitmentErrors.pillar}
            />
            <Input
              label="Category"
              value={commitmentForm.category}
              onChange={e => setCommitmentField('category', e.target.value)}
              placeholder="e.g. Emissions, Diversity, Ethics"
            />
            <Input
              label="Framework"
              value={commitmentForm.framework}
              onChange={e => setCommitmentField('framework', e.target.value)}
              placeholder="e.g. GRI, SASB, TCFD"
            />
            <Input
              label="Target Value"
              type="number"
              value={commitmentForm.target_value}
              onChange={e => setCommitmentField('target_value', e.target.value)}
              placeholder="e.g. 30"
            />
            <Input
              label="Target Unit"
              value={commitmentForm.target_unit}
              onChange={e => setCommitmentField('target_unit', e.target.value)}
              placeholder="e.g. %, tCO2e, hours"
            />
            <Input
              label="Owner"
              required
              value={commitmentForm.owner}
              onChange={e => setCommitmentField('owner', e.target.value)}
              error={commitmentErrors.owner}
              placeholder="Responsible person or team"
            />
          </div>
        </div>
      </Modal>

      {/* Record Metric Modal */}
      <Modal
        open={showMetricModal}
        onClose={closeMetricModal}
        title="Record ESG Metric"
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={closeMetricModal}>Cancel</Button>
            <Button onClick={handleCreateMetric} loading={createMetricMutation.isPending}>
              Record Metric
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Metric Name"
                required
                value={metricForm.name}
                onChange={e => setMetricField('name', e.target.value)}
                error={metricErrors.name}
                placeholder="e.g. Carbon Emissions"
              />
            </div>
            <Select
              label="Pillar"
              required
              value={metricForm.pillar}
              onChange={e => setMetricField('pillar', e.target.value as Pillar)}
              options={[{ value: '', label: 'Select pillar...' }, ...PILLAR_OPTIONS]}
              error={metricErrors.pillar}
            />
            <Input
              label="Value"
              required
              type="number"
              value={metricForm.value}
              onChange={e => setMetricField('value', e.target.value)}
              error={metricErrors.value}
              placeholder="e.g. 1500"
            />
            <Input
              label="Unit"
              value={metricForm.unit}
              onChange={e => setMetricField('unit', e.target.value)}
              placeholder="e.g. tCO2e, %, count"
            />
            <Input
              label="Period"
              value={metricForm.period}
              onChange={e => setMetricField('period', e.target.value)}
              placeholder="e.g. Q4 2026, FY2026"
            />
            <div className="sm:col-span-2">
              <Input
                label="Commitment ID (optional)"
                value={metricForm.commitment_id}
                onChange={e => setMetricField('commitment_id', e.target.value)}
                placeholder="Link to a specific commitment"
              />
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
