import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  ClockIcon,
  ExclamationTriangleIcon,
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

type Criticality = 'critical' | 'high' | 'medium' | 'low';

interface BiaRecord {
  id: string;
  process_name: string;
  process_owner: string;
  criticality: Criticality;
  rto_hours: number;
  rpo_hours: number;
  recovery_strategy: string;
  description?: string;
  department?: string;
  created_at?: string;
}

interface BiaForm {
  process_name: string;
  process_owner: string;
  criticality: Criticality | '';
  rto_hours: number;
  rpo_hours: number;
  recovery_strategy: string;
  description: string;
  department: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_FORM: BiaForm = {
  process_name: '',
  process_owner: '',
  criticality: '',
  rto_hours: 4,
  rpo_hours: 1,
  recovery_strategy: '',
  description: '',
  department: '',
};

const CRITICALITY_VARIANT: Record<Criticality, 'danger' | 'warning' | 'info' | 'success'> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'success',
};

const CRITICALITY_OPTIONS: { value: Criticality; label: string }[] = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const RECOVERY_STRATEGIES = [
  'Hot Standby',
  'Warm Standby',
  'Cold Standby',
  'Manual Workaround',
  'Outsource',
  'Do Without',
];

// ─── Component ────────────────────────────────────────────────────────────────

export function BiaSummary() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [criticalityFilter, setCriticalityFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingRecord, setEditingRecord] = useState<BiaRecord | null>(null);
  const [form, setForm] = useState<BiaForm>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof BiaForm, string>>>({});

  // ── Queries ──

  const { data: biaData, isLoading } = useQuery<BiaRecord[]>({
    queryKey: ['bcm-bia', criticalityFilter],
    queryFn: () =>
      api
        .get('/bcm/bia', { params: criticalityFilter ? { criticality: criticalityFilter } : {} })
        .then(r => r.data?.records ?? r.data ?? []),
  });

  const records: BiaRecord[] = biaData ?? [];

  const filtered = records.filter(r => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      r.process_name.toLowerCase().includes(q) ||
      r.process_owner.toLowerCase().includes(q) ||
      (r.department ?? '').toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/bcm/bia', data),
    onSuccess: () => {
      toast.success('BIA process added');
      queryClient.invalidateQueries({ queryKey: ['bcm-bia'] });
      closeModal();
    },
    onError: () => toast.error('Failed to add process'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      api.put(`/bcm/bia/${id}`, data),
    onSuccess: () => {
      toast.success('Process updated');
      queryClient.invalidateQueries({ queryKey: ['bcm-bia'] });
      closeModal();
    },
    onError: () => toast.error('Failed to update process'),
  });

  // ── Handlers ──

  function openCreate() {
    setEditingRecord(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
    setShowModal(true);
  }

  function openEdit(record: BiaRecord) {
    setEditingRecord(record);
    setForm({
      process_name: record.process_name,
      process_owner: record.process_owner,
      criticality: record.criticality,
      rto_hours: record.rto_hours,
      rpo_hours: record.rpo_hours,
      recovery_strategy: record.recovery_strategy ?? '',
      description: record.description ?? '',
      department: record.department ?? '',
    });
    setFormErrors({});
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setEditingRecord(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
  }

  function validate(): boolean {
    const errors: Partial<Record<keyof BiaForm, string>> = {};
    if (!form.process_name.trim()) errors.process_name = 'Process name is required';
    if (!form.process_owner.trim()) errors.process_owner = 'Process owner is required';
    if (!form.criticality) errors.criticality = 'Criticality is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
    if (editingRecord) {
      updateMutation.mutate({ id: editingRecord.id, data: form });
    } else {
      createMutation.mutate(form);
    }
  }

  function setField<K extends keyof BiaForm>(key: K, value: BiaForm[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Columns ──

  const columns = [
    {
      key: 'process_name',
      header: 'Process',
      render: (r: BiaRecord) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{r.process_name}</div>
          {r.department && <div className="text-xs text-gray-400">{r.department}</div>}
        </div>
      ),
    },
    {
      key: 'process_owner',
      header: 'Owner',
      render: (r: BiaRecord) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{r.process_owner}</span>
      ),
    },
    {
      key: 'criticality',
      header: 'Criticality',
      render: (r: BiaRecord) => (
        <Badge variant={CRITICALITY_VARIANT[r.criticality]} size="sm">
          {r.criticality}
        </Badge>
      ),
    },
    {
      key: 'rto',
      header: 'RTO',
      render: (r: BiaRecord) => (
        <div className="flex items-center gap-1.5">
          <ClockIcon className="h-3.5 w-3.5 text-gray-400" />
          <span className="text-sm text-gray-700 dark:text-gray-300">{r.rto_hours}h</span>
        </div>
      ),
    },
    {
      key: 'rpo',
      header: 'RPO',
      render: (r: BiaRecord) => (
        <div className="flex items-center gap-1.5">
          <ClockIcon className="h-3.5 w-3.5 text-gray-400" />
          <span className="text-sm text-gray-700 dark:text-gray-300">{r.rpo_hours}h</span>
        </div>
      ),
    },
    {
      key: 'recovery_strategy',
      header: 'Recovery Strategy',
      render: (r: BiaRecord) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">{r.recovery_strategy || '—'}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (r: BiaRecord) => (
        <Button size="sm" variant="ghost" onClick={e => { e.stopPropagation(); openEdit(r); }}>
          Edit
        </Button>
      ),
    },
  ];

  const criticalCount = records.filter(r => r.criticality === 'critical').length;
  const highCount = records.filter(r => r.criticality === 'high').length;
  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Business Impact Analysis"
        subtitle="Identify and classify business processes by criticality, RTO, and RPO"
        actions={
          <Button icon={<PlusIcon className="h-4 w-4" />} onClick={openCreate}>
            Add Process
          </Button>
        }
      />

      {criticalCount > 0 && (
        <div className="flex items-center gap-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-400">
            <span className="font-semibold">{criticalCount} critical</span> and{' '}
            <span className="font-semibold">{highCount} high</span> criticality processes require up-to-date recovery strategies.
          </p>
        </div>
      )}

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by process name, owner, or department..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={criticalityFilter}
            onChange={e => setCriticalityFilter(e.target.value)}
            options={[{ value: '', label: 'All Criticalities' }, ...CRITICALITY_OPTIONS]}
          />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        onRowClick={r => openEdit(r)}
        emptyMessage="No BIA records found. Add your first business process to get started."
      />

      {/* Modal */}
      <Modal
        open={showModal}
        onClose={closeModal}
        title={editingRecord ? 'Edit BIA Process' : 'Add Business Process'}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={closeModal}>Cancel</Button>
            <Button onClick={handleSubmit} loading={isSaving}>
              {editingRecord ? 'Save Changes' : 'Add Process'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Process Name"
                required
                value={form.process_name}
                onChange={e => setField('process_name', e.target.value)}
                error={formErrors.process_name}
                placeholder="e.g. Order-to-Cash Processing"
              />
            </div>
            <Input
              label="Process Owner"
              required
              value={form.process_owner}
              onChange={e => setField('process_owner', e.target.value)}
              error={formErrors.process_owner}
              placeholder="Owner name"
            />
            <Input
              label="Department"
              value={form.department}
              onChange={e => setField('department', e.target.value)}
              placeholder="e.g. Finance"
            />
            <Select
              label="Criticality"
              required
              value={form.criticality}
              onChange={e => setField('criticality', e.target.value as Criticality)}
              options={[{ value: '', label: 'Select criticality...' }, ...CRITICALITY_OPTIONS]}
              error={formErrors.criticality}
            />
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Recovery Strategy
              </label>
              <select
                value={form.recovery_strategy}
                onChange={e => setField('recovery_strategy', e.target.value)}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select strategy...</option>
                {RECOVERY_STRATEGIES.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <Input
              label="RTO (hours)"
              type="number"
              value={String(form.rto_hours)}
              onChange={e => setField('rto_hours', Number(e.target.value))}
            />
            <Input
              label="RPO (hours)"
              type="number"
              value={String(form.rpo_hours)}
              onChange={e => setField('rpo_hours', Number(e.target.value))}
            />
          </div>
          <Textarea
            label="Description"
            value={form.description}
            onChange={e => setField('description', e.target.value)}
            rows={3}
            placeholder="Describe the process, its dependencies, and business impact if disrupted..."
          />
        </div>
      </Modal>
    </div>
  );
}
