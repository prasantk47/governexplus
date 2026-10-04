import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  BriefcaseIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  BellAlertIcon,
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
  Textarea,
  SearchInput,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type CaseSeverity = 'critical' | 'high' | 'medium' | 'low';
type CaseStatus = 'open' | 'under_investigation' | 'pending_review' | 'closed' | 'escalated';

interface FraudCase {
  id: string;
  case_reference: string;
  title: string;
  severity: CaseSeverity;
  status: CaseStatus;
  assigned_to: string;
  opened_at: string;
  closed_at?: string;
  loss_amount?: number;
  description?: string;
}

interface CaseForm {
  title: string;
  severity: CaseSeverity | '';
  status: CaseStatus;
  assigned_to: string;
  loss_amount: string;
  description: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_FORM: CaseForm = {
  title: '',
  severity: '',
  status: 'open',
  assigned_to: '',
  loss_amount: '',
  description: '',
};

const SEVERITY_VARIANT: Record<CaseSeverity, 'danger' | 'warning' | 'info' | 'success'> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'success',
};

const STATUS_VARIANT: Record<CaseStatus, 'danger' | 'warning' | 'info' | 'success' | 'neutral'> = {
  open: 'danger',
  under_investigation: 'warning',
  pending_review: 'info',
  closed: 'success',
  escalated: 'danger',
};

const SEVERITY_OPTIONS = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const STATUS_OPTIONS_FILTER = [
  { value: '', label: 'All Statuses' },
  { value: 'open', label: 'Open' },
  { value: 'under_investigation', label: 'Under Investigation' },
  { value: 'pending_review', label: 'Pending Review' },
  { value: 'closed', label: 'Closed' },
  { value: 'escalated', label: 'Escalated' },
];

const STATUS_OPTIONS = STATUS_OPTIONS_FILTER.filter(o => o.value !== '');

function formatCurrency(amount?: number): string {
  if (amount === undefined || amount === null) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact' }).format(amount);
}

// ─── Component ────────────────────────────────────────────────────────────────

export function CaseManagement() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingCase, setEditingCase] = useState<FraudCase | null>(null);
  const [form, setForm] = useState<CaseForm>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof CaseForm, string>>>({});

  // ── Queries ──

  const { data: casesData, isLoading } = useQuery<FraudCase[]>({
    queryKey: ['fraud-cases', statusFilter],
    queryFn: () =>
      api
        .get('/fraud/cases', { params: statusFilter ? { status: statusFilter } : {} })
        .then(r => r.data?.cases ?? r.data ?? []),
  });

  const cases: FraudCase[] = casesData ?? [];

  const filtered = cases.filter(c => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.case_reference.toLowerCase().includes(q) ||
      c.title.toLowerCase().includes(q) ||
      c.assigned_to.toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/fraud/cases', data),
    onSuccess: () => {
      toast.success('Case opened');
      queryClient.invalidateQueries({ queryKey: ['fraud-cases'] });
      closeModal();
    },
    onError: () => toast.error('Failed to open case'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      api.put(`/fraud/cases/${id}`, data),
    onSuccess: () => {
      toast.success('Case updated');
      queryClient.invalidateQueries({ queryKey: ['fraud-cases'] });
      closeModal();
    },
    onError: () => toast.error('Failed to update case'),
  });

  // ── Handlers ──

  function openCreate() {
    setEditingCase(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
    setShowModal(true);
  }

  function openEdit(c: FraudCase) {
    setEditingCase(c);
    setForm({
      title: c.title,
      severity: c.severity,
      status: c.status,
      assigned_to: c.assigned_to,
      loss_amount: c.loss_amount !== undefined ? String(c.loss_amount) : '',
      description: c.description ?? '',
    });
    setFormErrors({});
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setEditingCase(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
  }

  function validate(): boolean {
    const errors: Partial<Record<keyof CaseForm, string>> = {};
    if (!form.title.trim()) errors.title = 'Title is required';
    if (!form.severity) errors.severity = 'Severity is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
    const payload = {
      ...form,
      loss_amount: form.loss_amount ? Number(form.loss_amount) : undefined,
    };
    if (editingCase) {
      updateMutation.mutate({ id: editingCase.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  }

  function setField<K extends keyof CaseForm>(key: K, value: CaseForm[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Stats ──

  const openAlerts = cases.filter(c => c.status === 'open' || c.status === 'under_investigation').length;
  const openCases = cases.filter(c => c.status !== 'closed').length;
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
  const confirmedFraud30d = cases.filter(
    c => c.status === 'closed' && (c.closed_at ?? '') >= thirtyDaysAgo
  ).length;

  // ── Columns ──

  const columns = [
    {
      key: 'case_reference',
      header: 'Case Ref',
      render: (c: FraudCase) => (
        <span className="text-sm font-mono font-medium text-indigo-600 dark:text-indigo-400">
          {c.case_reference}
        </span>
      ),
    },
    {
      key: 'title',
      header: 'Title',
      render: (c: FraudCase) => (
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100 max-w-xs truncate">
          {c.title}
        </div>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (c: FraudCase) => (
        <Badge variant={SEVERITY_VARIANT[c.severity]} size="sm">
          {c.severity}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (c: FraudCase) => (
        <Badge variant={STATUS_VARIANT[c.status]} dot size="sm">
          {c.status.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'assigned_to',
      header: 'Assigned To',
      render: (c: FraudCase) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{c.assigned_to || '—'}</span>
      ),
    },
    {
      key: 'opened_at',
      header: 'Opened',
      render: (c: FraudCase) => (
        <span className="text-sm text-gray-500">
          {new Date(c.opened_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'loss_amount',
      header: 'Loss Amount',
      render: (c: FraudCase) => (
        <span className={`text-sm font-medium ${c.loss_amount ? 'text-red-600 dark:text-red-400' : 'text-gray-400'}`}>
          {formatCurrency(c.loss_amount)}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (c: FraudCase) => (
        <Button size="sm" variant="ghost" onClick={e => { e.stopPropagation(); openEdit(c); }}>
          Edit
        </Button>
      ),
    },
  ];

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Case Management"
        subtitle="Track fraud investigations and case outcomes"
        actions={
          <Button icon={<PlusIcon className="h-4 w-4" />} onClick={openCreate}>
            Open Case
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard title="Active Alerts" value={openAlerts} icon={BellAlertIcon} iconBgColor="stat-icon-red" iconColor="" />
        <StatCard title="Open Cases" value={openCases} icon={BriefcaseIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Resolved (30d)" value={confirmedFraud30d} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by case reference, title, or assignee..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            options={STATUS_OPTIONS_FILTER}
          />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        onRowClick={c => openEdit(c)}
        emptyMessage="No fraud cases found. Cases can be opened manually or from the Alert Inbox."
      />

      {/* Modal */}
      <Modal
        open={showModal}
        onClose={closeModal}
        title={editingCase ? 'Edit Case' : 'Open Fraud Case'}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={closeModal}>Cancel</Button>
            <Button
              onClick={handleSubmit}
              loading={isSaving}
              icon={<ExclamationTriangleIcon className="h-4 w-4" />}
            >
              {editingCase ? 'Save Changes' : 'Open Case'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Case Title"
                required
                value={form.title}
                onChange={e => setField('title', e.target.value)}
                error={formErrors.title}
                placeholder="Brief description of the fraud case"
              />
            </div>
            <Select
              label="Severity"
              required
              value={form.severity}
              onChange={e => setField('severity', e.target.value as CaseSeverity)}
              options={[{ value: '', label: 'Select severity...' }, ...SEVERITY_OPTIONS]}
              error={formErrors.severity}
            />
            <Select
              label="Status"
              value={form.status}
              onChange={e => setField('status', e.target.value as CaseStatus)}
              options={STATUS_OPTIONS}
            />
            <Input
              label="Assigned To"
              value={form.assigned_to}
              onChange={e => setField('assigned_to', e.target.value)}
              placeholder="Investigator name or ID"
            />
            <Input
              label="Estimated Loss Amount (USD)"
              type="number"
              value={form.loss_amount}
              onChange={e => setField('loss_amount', e.target.value)}
              placeholder="0"
            />
          </div>
          <Textarea
            label="Description"
            value={form.description}
            onChange={e => setField('description', e.target.value)}
            rows={3}
            placeholder="Describe the suspected fraud, evidence, and investigation plan..."
          />
        </div>
      </Modal>
    </div>
  );
}
