import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {

  ExclamationTriangleIcon,
  BoltIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
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
  SearchInput,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type ActivationSeverity = 'critical' | 'high' | 'medium' | 'low';
type ActivationStatus = 'active' | 'contained' | 'recovering' | 'resolved' | 'closed';

interface IncidentActivation {
  id: string;
  activation_name: string;
  plan_id: string;
  plan_name?: string;
  activated_by: string;
  severity: ActivationSeverity;
  status: ActivationStatus;
  activated_at: string;
  resolved_at?: string;
  impacted_processes: string[];
  description?: string;
}

interface ActivationForm {
  activation_name: string;
  plan_id: string;
  severity: ActivationSeverity | '';
  description: string;
  impacted_processes: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_FORM: ActivationForm = {
  activation_name: '',
  plan_id: '',
  severity: '',
  description: '',
  impacted_processes: '',
};

const SEVERITY_VARIANT: Record<ActivationSeverity, 'danger' | 'warning' | 'info' | 'success'> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'success',
};

const STATUS_VARIANT: Record<ActivationStatus, 'danger' | 'warning' | 'info' | 'success' | 'neutral'> = {
  active: 'danger',
  contained: 'warning',
  recovering: 'info',
  resolved: 'success',
  closed: 'neutral',
};

const SEVERITY_OPTIONS: { value: ActivationSeverity; label: string }[] = [
  { value: 'critical', label: 'Critical — Major disruption' },
  { value: 'high', label: 'High — Significant impact' },
  { value: 'medium', label: 'Medium — Limited impact' },
  { value: 'low', label: 'Low — Minimal impact' },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function IncidentActivation() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<ActivationForm>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof ActivationForm, string>>>({});

  // ── Queries ──

  const { data: activationsData, isLoading } = useQuery<IncidentActivation[]>({
    queryKey: ['bcm-activations', statusFilter],
    queryFn: () =>
      api
        .get('/bcm/activations', { params: statusFilter ? { status: statusFilter } : {} })
        .then(r => r.data?.activations ?? r.data ?? []),
    refetchInterval: 30_000,
  });

  const { data: plansData } = useQuery<{ id: string; plan_name: string }[]>({
    queryKey: ['bcm-plans-list'],
    queryFn: () => api.get('/bcm/plans').then(r => r.data?.plans ?? r.data ?? []),
  });

  const activations: IncidentActivation[] = activationsData ?? [];
  const plans = plansData ?? [];

  const filtered = activations.filter(a => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      a.activation_name.toLowerCase().includes(q) ||
      a.activated_by.toLowerCase().includes(q) ||
      (a.plan_name ?? '').toLowerCase().includes(q)
    );
  });

  const activeIncidents = activations.filter(a => a.status === 'active' || a.status === 'contained');

  // ── Mutations ──

  const activateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/bcm/activations', data),
    onSuccess: () => {
      toast.success('BCM plan activated — incident declared');
      queryClient.invalidateQueries({ queryKey: ['bcm-activations'] });
      closeModal();
    },
    onError: () => toast.error('Failed to activate plan'),
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: ActivationStatus }) =>
      api.patch(`/bcm/activations/${id}`, { status }),
    onSuccess: () => {
      toast.success('Incident status updated');
      queryClient.invalidateQueries({ queryKey: ['bcm-activations'] });
    },
    onError: () => toast.error('Failed to update status'),
  });

  // ── Handlers ──

  function closeModal() {
    setShowModal(false);
    setForm(EMPTY_FORM);
    setFormErrors({});
  }

  function validate(): boolean {
    const errors: Partial<Record<keyof ActivationForm, string>> = {};
    if (!form.activation_name.trim()) errors.activation_name = 'Activation name is required';
    if (!form.severity) errors.severity = 'Severity is required';
    if (!form.plan_id) errors.plan_id = 'Plan selection is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
    activateMutation.mutate({
      ...form,
      impacted_processes: form.impacted_processes
        ? form.impacted_processes.split(',').map(s => s.trim()).filter(Boolean)
        : [],
    });
  }

  function setField<K extends keyof ActivationForm>(key: K, value: ActivationForm[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Columns ──

  const columns = [
    {
      key: 'activation_name',
      header: 'Incident',
      render: (a: IncidentActivation) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{a.activation_name}</div>
          <div className="text-xs text-gray-400">{a.plan_name || a.plan_id}</div>
        </div>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (a: IncidentActivation) => (
        <Badge variant={SEVERITY_VARIANT[a.severity]} size="sm">
          {a.severity}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (a: IncidentActivation) => (
        <Badge variant={STATUS_VARIANT[a.status]} dot size="sm">
          {a.status.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'activated_by',
      header: 'Activated By',
      render: (a: IncidentActivation) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{a.activated_by}</span>
      ),
    },
    {
      key: 'activated_at',
      header: 'Activated',
      render: (a: IncidentActivation) => (
        <span className="text-sm text-gray-500">
          {new Date(a.activated_at).toLocaleString()}
        </span>
      ),
    },
    {
      key: 'impacted',
      header: 'Impacted Processes',
      render: (a: IncidentActivation) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {(a.impacted_processes ?? []).length} process{(a.impacted_processes ?? []).length !== 1 ? 'es' : ''}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (a: IncidentActivation) =>
        a.status === 'active' ? (
          <div className="flex justify-end gap-1">
            <Button
              size="sm"
              variant="ghost"
              onClick={e => {
                e.stopPropagation();
                updateStatusMutation.mutate({ id: a.id, status: 'contained' });
              }}
            >
              Contain
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={e => {
                e.stopPropagation();
                updateStatusMutation.mutate({ id: a.id, status: 'resolved' });
              }}
            >
              Resolve
            </Button>
          </div>
        ) : a.status === 'contained' || a.status === 'recovering' ? (
          <Button
            size="sm"
            variant="ghost"
            onClick={e => {
              e.stopPropagation();
              updateStatusMutation.mutate({ id: a.id, status: 'resolved' });
            }}
          >
            Resolve
          </Button>
        ) : null,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Incident Activation"
        subtitle="Declare and manage active BCM incident activations"
        actions={
          <Button
            icon={<BoltIcon className="h-4 w-4" />}
            onClick={() => setShowModal(true)}
            variant="danger"
          >
            Activate Plan
          </Button>
        }
      />

      {/* Active Incident Banner */}
      {activeIncidents.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-700 rounded-lg px-5 py-4">
          <div className="flex items-start gap-3">
            <ExclamationTriangleIcon className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-red-700 dark:text-red-400">
                {activeIncidents.length} Active Incident{activeIncidents.length > 1 ? 's' : ''}
              </p>
              <ul className="mt-1 space-y-0.5">
                {activeIncidents.map(a => (
                  <li key={a.id} className="text-sm text-red-600 dark:text-red-300">
                    {a.activation_name} — {a.severity.toUpperCase()} — {a.status}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by incident name, plan, or activator..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            options={[
              { value: '', label: 'All Statuses' },
              { value: 'active', label: 'Active' },
              { value: 'contained', label: 'Contained' },
              { value: 'recovering', label: 'Recovering' },
              { value: 'resolved', label: 'Resolved' },
              { value: 'closed', label: 'Closed' },
            ]}
          />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        emptyMessage="No incident activations found. Plans are activated when an incident is declared."
      />

      {/* Activate Modal */}
      <Modal
        open={showModal}
        onClose={closeModal}
        title="Activate BCM Plan"
        subtitle="This will declare a formal incident and activate the selected plan"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={closeModal}>Cancel</Button>
            <Button
              variant="danger"
              onClick={handleSubmit}
              loading={activateMutation.isPending}
              icon={<BoltIcon className="h-4 w-4" />}
            >
              Activate Plan
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
            <p className="text-xs text-amber-700 dark:text-amber-400 font-medium">
              Activating a BCM plan declares a formal incident. Ensure this action is authorised.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Incident / Activation Name"
                required
                value={form.activation_name}
                onChange={e => setField('activation_name', e.target.value)}
                error={formErrors.activation_name}
                placeholder="e.g. Primary DC Flood — 2026-10-04"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                BCM Plan to Activate <span className="text-red-500">*</span>
              </label>
              <select
                value={form.plan_id}
                onChange={e => setField('plan_id', e.target.value)}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select plan...</option>
                {plans.map(p => (
                  <option key={p.id} value={p.id}>{p.plan_name}</option>
                ))}
              </select>
              {formErrors.plan_id && (
                <p className="text-xs text-red-500 mt-1">{formErrors.plan_id}</p>
              )}
            </div>
            <Select
              label="Severity"
              required
              value={form.severity}
              onChange={e => setField('severity', e.target.value as ActivationSeverity)}
              options={[{ value: '', label: 'Select severity...' }, ...SEVERITY_OPTIONS]}
              error={formErrors.severity}
            />
            <div className="sm:col-span-2">
              <Input
                label="Impacted Processes (comma-separated)"
                value={form.impacted_processes}
                onChange={e => setField('impacted_processes', e.target.value)}
                placeholder="e.g. Order Processing, Customer Support, Finance"
              />
            </div>
          </div>
          <Textarea
            label="Incident Description"
            value={form.description}
            onChange={e => setField('description', e.target.value)}
            rows={3}
            placeholder="Describe what happened, current situation, and immediate actions taken..."
          />
        </div>
      </Modal>
    </div>
  );
}
