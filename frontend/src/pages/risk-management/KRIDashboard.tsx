import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  ChartBarIcon,
  SignalIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  PencilSquareIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { riskManagementApi } from '../../services/riskManagementApi';
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
  Textarea,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type KRIStatus = 'normal' | 'warning' | 'breach';
type KRIDirection = 'lower_better' | 'higher_better' | 'target_range';

interface KRI {
  id: string;
  name: string;
  description: string;
  risk_id: string;
  risk_title: string;
  unit: string;
  direction: KRIDirection;
  threshold_green: number;
  threshold_amber: number;
  threshold_red: number;
  current_value: number | null;
  status: KRIStatus;
  last_measured_at: string | null;
  owner: string;
  frequency: string;
}

interface KRIDashboardData {
  kris: KRI[];
  summary: {
    total: number;
    normal: number;
    warning: number;
    breach: number;
  };
}

interface KRIMeasurement {
  measured_at: string;
  value: number;
  notes: string;
  measured_by: string;
  status: KRIStatus;
}

interface KRIFormData {
  name: string;
  description: string;
  risk_id: string;
  unit: string;
  direction: KRIDirection | '';
  threshold_green: string;
  threshold_amber: string;
  threshold_red: string;
  owner: string;
  frequency: string;
}

interface MeasurementFormData {
  value: string;
  notes: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_VARIANT: Record<KRIStatus, 'success' | 'warning' | 'danger'> = {
  normal: 'success',
  warning: 'warning',
  breach: 'danger',
};

const STATUS_LABEL: Record<KRIStatus, string> = {
  normal: 'Normal',
  warning: 'Warning',
  breach: 'Breach',
};

const EMPTY_KRI_FORM: KRIFormData = {
  name: '',
  description: '',
  risk_id: '',
  unit: '',
  direction: '',
  threshold_green: '',
  threshold_amber: '',
  threshold_red: '',
  owner: '',
  frequency: 'monthly',
};

const EMPTY_MEASUREMENT: MeasurementFormData = {
  value: '',
  notes: '',
};

function validateKRIForm(form: KRIFormData): Partial<Record<keyof KRIFormData, string>> {
  const errors: Partial<Record<keyof KRIFormData, string>> = {};
  if (!form.name.trim()) errors.name = 'Name is required';
  if (!form.direction) errors.direction = 'Direction is required';
  if (!form.unit.trim()) errors.unit = 'Unit is required';
  if (!form.threshold_green || isNaN(Number(form.threshold_green))) errors.threshold_green = 'Valid number required';
  if (!form.threshold_amber || isNaN(Number(form.threshold_amber))) errors.threshold_amber = 'Valid number required';
  if (!form.threshold_red || isNaN(Number(form.threshold_red))) errors.threshold_red = 'Valid number required';
  return errors;
}

// Mini sparkline
function KRISparkline({ data }: { data: KRIMeasurement[] }) {
  if (data.length < 2) {
    return <p className="text-xs text-gray-400">Insufficient data for chart</p>;
  }
  const values = data.map(d => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 300;
  const height = 80;
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 16) - 8;
    return `${x},${y}`;
  });
  const lastStatus = data[data.length - 1]?.status ?? 'normal';
  const color = lastStatus === 'breach' ? '#ef4444' : lastStatus === 'warning' ? '#f59e0b' : '#10b981';
  return (
    <div>
      <svg width={width} height={height} className="overflow-visible w-full">
        <polyline
          points={points.join(' ')}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {values.map((v, i) => {
          const x = (i / (values.length - 1)) * width;
          const y = height - ((v - min) / range) * (height - 16) - 8;
          return <circle key={i} cx={x} cy={y} r={3} fill={color} />;
        })}
      </svg>
      <div className="flex justify-between text-[10px] text-gray-400 mt-1">
        {data.map((d, i) => (
          <span key={i}>{new Date(d.measured_at || new Date()).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' })}</span>
        ))}
      </div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function KRIDashboard() {
  const queryClient = useQueryClient();

  const [showCreateKRI, setShowCreateKRI] = useState(false);
  const [kriForm, setKRIForm] = useState<KRIFormData>(EMPTY_KRI_FORM);
  const [kriFormErrors, setKRIFormErrors] = useState<Partial<Record<keyof KRIFormData, string>>>({});

  const [measuringKRI, setMeasuringKRI] = useState<KRI | null>(null);
  const [measureForm, setMeasureForm] = useState<MeasurementFormData>(EMPTY_MEASUREMENT);
  const [measureErrors, setMeasureErrors] = useState<Partial<Record<keyof MeasurementFormData, string>>>({});

  const [historyKRI, setHistoryKRI] = useState<KRI | null>(null);

  // ── Queries ──

  const { data: dashData, isLoading } = useQuery<KRIDashboardData>({
    queryKey: ['kri-dashboard'],
    queryFn: () =>
      riskManagementApi
        .getKRIDashboard()
        .then(r => r.data),
  });

  const { data: historyData, isLoading: historyLoading } = useQuery<KRIMeasurement[]>({
    queryKey: ['kri-history', historyKRI?.id],
    queryFn: () =>
      riskManagementApi
        .getKRIHistory(historyKRI!.id)
        .then(r => r.data?.measurements ?? r.data ?? []),
    enabled: !!historyKRI,
  });

  const kris: KRI[] = dashData?.kris ?? [];
  const summary = dashData?.summary ?? { total: 0, normal: 0, warning: 0, breach: 0 };

  // ── Mutations ──

  const createKRIMutation = useMutation({
    mutationFn: (data: KRIFormData) =>
      riskManagementApi.createKRI({
        ...data,
        threshold_green: Number(data.threshold_green),
        threshold_amber: Number(data.threshold_amber),
        threshold_red: Number(data.threshold_red),
      }),
    onSuccess: () => {
      toast.success('KRI created successfully');
      queryClient.invalidateQueries({ queryKey: ['kri-dashboard'] });
      setShowCreateKRI(false);
      setKRIForm(EMPTY_KRI_FORM);
    },
    onError: () => toast.error('Failed to create KRI'),
  });

  const recordMeasurementMutation = useMutation({
    mutationFn: ({ kriId, data }: { kriId: string; data: MeasurementFormData }) =>
      riskManagementApi.recordKRIMeasurement(kriId, {
        value: Number(data.value),
        notes: data.notes,
      }),
    onSuccess: () => {
      toast.success('Measurement recorded');
      queryClient.invalidateQueries({ queryKey: ['kri-dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['kri-history', measuringKRI?.id] });
      setMeasuringKRI(null);
      setMeasureForm(EMPTY_MEASUREMENT);
    },
    onError: () => toast.error('Failed to record measurement'),
  });

  // ── Handlers ──

  function setKRIField<K extends keyof KRIFormData>(key: K, value: KRIFormData[K]) {
    setKRIForm(prev => ({ ...prev, [key]: value }));
    if (kriFormErrors[key]) setKRIFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  function handleCreateKRI() {
    const errors = validateKRIForm(kriForm);
    if (Object.keys(errors).length > 0) { setKRIFormErrors(errors); return; }
    createKRIMutation.mutate(kriForm);
  }

  function handleRecordMeasurement() {
    const errors: Partial<Record<keyof MeasurementFormData, string>> = {};
    if (!measureForm.value || isNaN(Number(measureForm.value))) {
      errors.value = 'Valid numeric value is required';
    }
    if (Object.keys(errors).length > 0) { setMeasureErrors(errors); return; }
    recordMeasurementMutation.mutate({ kriId: measuringKRI!.id, data: measureForm });
  }

  // ── Columns ──

  const columns = [
    {
      key: 'name',
      header: 'KRI Name',
      render: (k: KRI) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{k.name}</div>
          <div className="text-xs text-gray-400 mt-0.5">{k.risk_title || k.risk_id}</div>
        </div>
      ),
    },
    {
      key: 'current_value',
      header: 'Current Value',
      render: (k: KRI) => (
        <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
          {k.current_value !== null ? `${k.current_value} ${k.unit}` : '—'}
        </span>
      ),
    },
    {
      key: 'thresholds',
      header: 'Thresholds (G / A / R)',
      render: (k: KRI) => (
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-emerald-600 font-medium">{k.threshold_green}</span>
          <span className="text-gray-300 dark:text-gray-600">/</span>
          <span className="text-amber-600 font-medium">{k.threshold_amber}</span>
          <span className="text-gray-300 dark:text-gray-600">/</span>
          <span className="text-red-600 font-medium">{k.threshold_red}</span>
          <span className="text-gray-400 ml-1">{k.unit}</span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (k: KRI) => (
        <Badge variant={STATUS_VARIANT[k.status]} dot size="sm">
          {STATUS_LABEL[k.status]}
        </Badge>
      ),
    },
    {
      key: 'last_measured_at',
      header: 'Last Measured',
      render: (k: KRI) => (
        <span className="text-xs text-gray-500">
          {k.last_measured_at
            ? new Date(k.last_measured_at || new Date()).toLocaleDateString('en-GB')
            : 'Never'}
        </span>
      ),
    },
    {
      key: 'owner',
      header: 'Owner',
      render: (k: KRI) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">{k.owner}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (k: KRI) => (
        <div className="flex justify-end gap-2">
          <button
            onClick={e => { e.stopPropagation(); setHistoryKRI(k); }}
            className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors"
            title="View history"
          >
            <ChartBarIcon className="h-4 w-4" />
          </button>
          <button
            onClick={e => { e.stopPropagation(); setMeasuringKRI(k); setMeasureForm(EMPTY_MEASUREMENT); setMeasureErrors({}); }}
            className="p-1.5 rounded-lg text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors"
            title="Record measurement"
          >
            <PencilSquareIcon className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="KRI Dashboard"
        subtitle="Monitor Key Risk Indicators and threshold breaches"
        actions={
          <Button
            icon={<PlusIcon className="h-4 w-4" />}
            onClick={() => { setShowCreateKRI(true); setKRIForm(EMPTY_KRI_FORM); setKRIFormErrors({}); }}
          >
            Create KRI
          </Button>
        }
      />

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard
          title="Total KRIs"
          value={summary.total}
          icon={SignalIcon}
          iconBgColor="stat-icon-blue"
          iconColor=""
        />
        <StatCard
          title="Normal"
          value={summary.normal}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor=""
        />
        <StatCard
          title="Warning"
          value={summary.warning}
          icon={ClockIcon}
          iconBgColor="stat-icon-yellow"
          iconColor=""
        />
        <StatCard
          title="Breach"
          value={summary.breach}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-red"
          iconColor=""
        />
      </div>

      {/* Status breakdown mini-bar */}
      {summary.total > 0 && (
        <Card padding="md">
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-gray-500 w-24 flex-shrink-0">Status split</span>
            <div className="flex-1 flex h-3 rounded-full overflow-hidden">
              {summary.normal > 0 && (
                <div
                  className="bg-emerald-500 transition-all"
                  style={{ width: `${(summary.normal / summary.total) * 100}%` }}
                  title={`Normal: ${summary.normal}`}
                />
              )}
              {summary.warning > 0 && (
                <div
                  className="bg-amber-400 transition-all"
                  style={{ width: `${(summary.warning / summary.total) * 100}%` }}
                  title={`Warning: ${summary.warning}`}
                />
              )}
              {summary.breach > 0 && (
                <div
                  className="bg-red-500 transition-all"
                  style={{ width: `${(summary.breach / summary.total) * 100}%` }}
                  title={`Breach: ${summary.breach}`}
                />
              )}
            </div>
            <div className="flex items-center gap-3 text-xs flex-shrink-0">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" />{summary.normal} normal</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400" />{summary.warning} warning</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" />{summary.breach} breach</span>
            </div>
          </div>
        </Card>
      )}

      {/* KRI Table */}
      <Table
        columns={columns}
        data={kris}
        loading={isLoading}
        onRowClick={k => setHistoryKRI(k)}
        emptyMessage="No KRIs configured. Create your first KRI to start monitoring."
      />

      {/* Create KRI Modal */}
      <Modal
        open={showCreateKRI}
        onClose={() => setShowCreateKRI(false)}
        title="Create KRI"
        subtitle="Define a new Key Risk Indicator with thresholds"
        size="xl"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowCreateKRI(false)}>Cancel</Button>
            <Button onClick={handleCreateKRI} loading={createKRIMutation.isPending}>
              Create KRI
            </Button>
          </>
        }
      >
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="KRI Name"
                required
                value={kriForm.name}
                onChange={e => setKRIField('name', e.target.value)}
                error={kriFormErrors.name}
                placeholder="e.g. Number of failed login attempts per day"
              />
            </div>

            <Input
              label="Linked Risk ID"
              value={kriForm.risk_id}
              onChange={e => setKRIField('risk_id', e.target.value)}
              placeholder="RISK-001"
            />

            <Input
              label="Owner"
              value={kriForm.owner}
              onChange={e => setKRIField('owner', e.target.value)}
              placeholder="Name of responsible person"
            />

            <Input
              label="Unit"
              required
              value={kriForm.unit}
              onChange={e => setKRIField('unit', e.target.value)}
              error={kriFormErrors.unit}
              placeholder="e.g. %, count, days"
            />

            <Select
              label="Direction"
              required
              value={kriForm.direction}
              onChange={e => setKRIField('direction', e.target.value as KRIDirection)}
              options={[
                { value: 'lower_better', label: 'Lower is better' },
                { value: 'higher_better', label: 'Higher is better' },
                { value: 'target_range', label: 'Target range' },
              ]}
              placeholder="Select direction..."
              error={kriFormErrors.direction}
            />

            <Select
              label="Measurement Frequency"
              value={kriForm.frequency}
              onChange={e => setKRIField('frequency', e.target.value)}
              options={[
                { value: 'daily', label: 'Daily' },
                { value: 'weekly', label: 'Weekly' },
                { value: 'monthly', label: 'Monthly' },
                { value: 'quarterly', label: 'Quarterly' },
              ]}
            />
          </div>

          <div>
            <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-3">
              Thresholds
            </p>
            <div className="grid grid-cols-3 gap-4">
              <Input
                label="Green threshold"
                type="number"
                required
                value={kriForm.threshold_green}
                onChange={e => setKRIField('threshold_green', e.target.value)}
                error={kriFormErrors.threshold_green}
                placeholder="e.g. 5"
                className="border-emerald-200 focus:border-emerald-400"
              />
              <Input
                label="Amber threshold"
                type="number"
                required
                value={kriForm.threshold_amber}
                onChange={e => setKRIField('threshold_amber', e.target.value)}
                error={kriFormErrors.threshold_amber}
                placeholder="e.g. 15"
                className="border-amber-200 focus:border-amber-400"
              />
              <Input
                label="Red threshold"
                type="number"
                required
                value={kriForm.threshold_red}
                onChange={e => setKRIField('threshold_red', e.target.value)}
                error={kriFormErrors.threshold_red}
                placeholder="e.g. 30"
                className="border-red-200 focus:border-red-400"
              />
            </div>
          </div>

          <Textarea
            label="Description"
            value={kriForm.description}
            onChange={e => setKRIField('description', e.target.value)}
            rows={2}
            placeholder="Brief description of what this KRI measures and why it matters"
          />
        </div>
      </Modal>

      {/* Record Measurement Modal */}
      <Modal
        open={!!measuringKRI}
        onClose={() => setMeasuringKRI(null)}
        title="Record Measurement"
        subtitle={measuringKRI?.name}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setMeasuringKRI(null)}>Cancel</Button>
            <Button onClick={handleRecordMeasurement} loading={recordMeasurementMutation.isPending}>
              Record
            </Button>
          </>
        }
      >
        {measuringKRI && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 dark:bg-slate-700/50">
              <div className="text-sm">
                <span className="text-gray-500">Thresholds: </span>
                <span className="text-emerald-600 font-medium">{measuringKRI.threshold_green}</span>
                <span className="text-gray-400 mx-1">/</span>
                <span className="text-amber-600 font-medium">{measuringKRI.threshold_amber}</span>
                <span className="text-gray-400 mx-1">/</span>
                <span className="text-red-600 font-medium">{measuringKRI.threshold_red}</span>
                <span className="text-gray-400 ml-1">{measuringKRI.unit}</span>
              </div>
            </div>
            <Input
              label={`Value (${measuringKRI.unit})`}
              required
              type="number"
              value={measureForm.value}
              onChange={e => {
                setMeasureForm(prev => ({ ...prev, value: e.target.value }));
                if (measureErrors.value) setMeasureErrors(prev => ({ ...prev, value: undefined }));
              }}
              error={measureErrors.value}
              placeholder="Enter current measurement"
            />
            <Textarea
              label="Notes"
              value={measureForm.notes}
              onChange={e => setMeasureForm(prev => ({ ...prev, notes: e.target.value }))}
              rows={2}
              placeholder="Optional notes about this measurement..."
            />
          </div>
        )}
      </Modal>

      {/* History Modal */}
      <Modal
        open={!!historyKRI}
        onClose={() => setHistoryKRI(null)}
        title="KRI History"
        subtitle={historyKRI?.name}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setHistoryKRI(null)}>Close</Button>
            <Button
              onClick={() => { setMeasuringKRI(historyKRI); setHistoryKRI(null); setMeasureForm(EMPTY_MEASUREMENT); setMeasureErrors({}); }}
            >
              Record Measurement
            </Button>
          </>
        }
      >
        {historyKRI && (
          <div className="space-y-5">
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center p-3 rounded-xl bg-gray-50 dark:bg-slate-700/50">
                <p className="text-xs text-gray-500">Current</p>
                <p className="text-xl font-bold text-gray-800 dark:text-gray-200 mt-1">
                  {historyKRI.current_value !== null ? historyKRI.current_value : '—'}
                </p>
                <p className="text-xs text-gray-400">{historyKRI.unit}</p>
              </div>
              <div className="text-center p-3 rounded-xl bg-gray-50 dark:bg-slate-700/50">
                <p className="text-xs text-gray-500">Status</p>
                <div className="mt-1">
                  <Badge variant={STATUS_VARIANT[historyKRI.status]} dot size="md">
                    {STATUS_LABEL[historyKRI.status]}
                  </Badge>
                </div>
              </div>
              <div className="text-center p-3 rounded-xl bg-gray-50 dark:bg-slate-700/50">
                <p className="text-xs text-gray-500">Last Measured</p>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mt-1">
                  {historyKRI.last_measured_at
                    ? new Date(historyKRI.last_measured_at || new Date()).toLocaleDateString('en-GB')
                    : 'Never'}
                </p>
              </div>
            </div>

            {historyLoading ? (
              <div className="flex justify-center py-8">
                <svg className="animate-spin h-6 w-6 text-indigo-500" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              </div>
            ) : (historyData ?? []).length === 0 ? (
              <div className="py-8 text-center text-sm text-gray-400">
                No measurement history. Record your first value to begin tracking.
              </div>
            ) : (
              <>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Trend</p>
                  <KRISparkline data={historyData ?? []} />
                </div>

                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
                    Measurement History
                  </p>
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {(historyData ?? []).slice().reverse().map((m, i) => (
                      <div key={i} className="flex items-center gap-3 p-2.5 rounded-xl bg-gray-50 dark:bg-slate-700/50">
                        <Badge variant={STATUS_VARIANT[m.status]} size="sm">
                          {m.value} {historyKRI.unit}
                        </Badge>
                        <span className="text-xs text-gray-500 flex-1">
                          {new Date(m.measured_at || new Date()).toLocaleString('en-GB')}
                        </span>
                        {m.notes && (
                          <span className="text-xs text-gray-400 max-w-xs truncate">{m.notes}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
