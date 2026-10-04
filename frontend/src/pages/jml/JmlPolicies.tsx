import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  DocumentTextIcon,
  UserPlusIcon,

  UserMinusIcon,
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

type EventType = 'joiner' | 'mover' | 'leaver';

interface JmlPolicy {
  id: string;
  policy_name: string;
  event_type: EventType;
  org_unit: string;
  birthright_roles: string[];
  is_active: boolean;
  description: string;
  created_at?: string;
}

interface JmlPolicyForm {
  policy_name: string;
  event_type: EventType | '';
  org_unit: string;
  description: string;
  birthright_roles: string;
  is_active: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_FORM: JmlPolicyForm = {
  policy_name: '',
  event_type: '',
  org_unit: '',
  description: '',
  birthright_roles: '',
  is_active: true,
};

const EVENT_TYPE_OPTIONS: { value: EventType; label: string }[] = [
  { value: 'joiner', label: 'Joiner' },
  { value: 'mover', label: 'Mover' },
  { value: 'leaver', label: 'Leaver' },
];

const EVENT_TYPE_VARIANT: Record<EventType, 'success' | 'info' | 'danger'> = {
  joiner: 'success',
  mover: 'info',
  leaver: 'danger',
};

const EVENT_TYPE_LABEL: Record<EventType, string> = {
  joiner: 'Joiner',
  mover: 'Mover',
  leaver: 'Leaver',
};

// ─── Component ────────────────────────────────────────────────────────────────

export function JmlPolicies() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [eventFilter, setEventFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<JmlPolicy | null>(null);
  const [form, setForm] = useState<JmlPolicyForm>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof JmlPolicyForm, string>>>({});

  // ── Queries ──

  const { data: policiesData, isLoading } = useQuery<JmlPolicy[]>({
    queryKey: ['jml-policies', eventFilter],
    queryFn: () =>
      api
        .get('/jml/policies', { params: eventFilter ? { event_type: eventFilter } : {} })
        .then(r => r.data?.policies ?? r.data ?? []),
  });

  const policies: JmlPolicy[] = policiesData ?? [];

  const filtered = policies.filter(p => {
    const q = search.toLowerCase();
    return (
      !search ||
      p.policy_name.toLowerCase().includes(q) ||
      p.org_unit.toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/jml/policies', data),
    onSuccess: () => {
      toast.success('Policy created successfully');
      queryClient.invalidateQueries({ queryKey: ['jml-policies'] });
      closeModal();
    },
    onError: () => toast.error('Failed to create policy'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      api.put(`/jml/policies/${id}`, data),
    onSuccess: () => {
      toast.success('Policy updated successfully');
      queryClient.invalidateQueries({ queryKey: ['jml-policies'] });
      closeModal();
    },
    onError: () => toast.error('Failed to update policy'),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/jml/policies/${id}`, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jml-policies'] });
    },
    onError: () => toast.error('Failed to update policy status'),
  });

  // ── Handlers ──

  function openCreate() {
    setEditingPolicy(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
    setShowModal(true);
  }

  function openEdit(policy: JmlPolicy) {
    setEditingPolicy(policy);
    setForm({
      policy_name: policy.policy_name,
      event_type: policy.event_type,
      org_unit: policy.org_unit,
      description: policy.description ?? '',
      birthright_roles: (policy.birthright_roles ?? []).join(', '),
      is_active: policy.is_active,
    });
    setFormErrors({});
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setEditingPolicy(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
  }

  function validate(): boolean {
    const errors: Partial<Record<keyof JmlPolicyForm, string>> = {};
    if (!form.policy_name.trim()) errors.policy_name = 'Policy name is required';
    if (!form.event_type) errors.event_type = 'Event type is required';
    if (!form.org_unit.trim()) errors.org_unit = 'Org unit is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
    const payload = {
      ...form,
      birthright_roles: form.birthright_roles
        ? form.birthright_roles.split(',').map(s => s.trim()).filter(Boolean)
        : [],
    };
    if (editingPolicy) {
      updateMutation.mutate({ id: editingPolicy.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  }

  function setField<K extends keyof JmlPolicyForm>(key: K, value: JmlPolicyForm[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Stats ──

  const totalCount = policies.length;
  const activeCount = policies.filter(p => p.is_active).length;
  const joinerCount = policies.filter(p => p.event_type === 'joiner').length;
  const leaverCount = policies.filter(p => p.event_type === 'leaver').length;

  // ── Columns ──

  const columns = [
    {
      key: 'policy_name',
      header: 'Policy Name',
      render: (p: JmlPolicy) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{p.policy_name}</div>
          {p.description && (
            <div className="text-xs text-gray-400 truncate max-w-xs">{p.description}</div>
          )}
        </div>
      ),
    },
    {
      key: 'event_type',
      header: 'Event Type',
      render: (p: JmlPolicy) => (
        <Badge variant={EVENT_TYPE_VARIANT[p.event_type]} size="sm">
          {EVENT_TYPE_LABEL[p.event_type]}
        </Badge>
      ),
    },
    {
      key: 'org_unit',
      header: 'Org Unit',
      render: (p: JmlPolicy) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{p.org_unit}</span>
      ),
    },
    {
      key: 'roles',
      header: 'Birthright Roles',
      render: (p: JmlPolicy) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {(p.birthright_roles ?? []).length} role{(p.birthright_roles ?? []).length !== 1 ? 's' : ''}
        </span>
      ),
    },
    {
      key: 'is_active',
      header: 'Active',
      render: (p: JmlPolicy) => (
        <button
          onClick={e => {
            e.stopPropagation();
            toggleMutation.mutate({ id: p.id, is_active: !p.is_active });
          }}
          className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none ${
            p.is_active ? 'bg-indigo-600' : 'bg-gray-200 dark:bg-slate-600'
          }`}
          title={p.is_active ? 'Deactivate' : 'Activate'}
        >
          <span
            className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ${
              p.is_active ? 'translate-x-4' : 'translate-x-0'
            }`}
          />
        </button>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (p: JmlPolicy) => (
        <Button size="sm" variant="ghost" onClick={e => { e.stopPropagation(); openEdit(p); }}>
          Edit
        </Button>
      ),
    },
  ];

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="JML Policies"
        subtitle="Manage Joiner, Mover, and Leaver provisioning policies"
        actions={
          <Button icon={<PlusIcon className="h-4 w-4" />} onClick={openCreate}>
            Create Policy
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Policies" value={totalCount} icon={DocumentTextIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Active" value={activeCount} icon={DocumentTextIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Joiners" value={joinerCount} icon={UserPlusIcon} iconBgColor="stat-icon-indigo" iconColor="" />
        <StatCard title="Leavers" value={leaverCount} icon={UserMinusIcon} iconBgColor="stat-icon-red" iconColor="" />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by policy name or org unit..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={eventFilter}
            onChange={e => setEventFilter(e.target.value)}
            options={[
              { value: '', label: 'All Event Types' },
              ...EVENT_TYPE_OPTIONS,
            ]}
          />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        onRowClick={p => openEdit(p)}
        emptyMessage="No JML policies found. Click 'Create Policy' to add your first policy."
      />

      {/* Create / Edit Modal */}
      <Modal
        open={showModal}
        onClose={closeModal}
        title={editingPolicy ? 'Edit JML Policy' : 'Create JML Policy'}
        subtitle={editingPolicy ? `Editing: ${editingPolicy.policy_name}` : 'Define a new provisioning policy'}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={closeModal}>Cancel</Button>
            <Button onClick={handleSubmit} loading={isSaving}>
              {editingPolicy ? 'Save Changes' : 'Create Policy'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Policy Name"
                required
                value={form.policy_name}
                onChange={e => setField('policy_name', e.target.value)}
                error={formErrors.policy_name}
                placeholder="e.g. Finance Joiner Provisioning"
              />
            </div>
            <Select
              label="Event Type"
              required
              value={form.event_type}
              onChange={e => setField('event_type', e.target.value as EventType)}
              options={[{ value: '', label: 'Select event type...' }, ...EVENT_TYPE_OPTIONS]}
              error={formErrors.event_type}
            />
            <Input
              label="Org Unit"
              required
              value={form.org_unit}
              onChange={e => setField('org_unit', e.target.value)}
              error={formErrors.org_unit}
              placeholder="e.g. Finance, IT, HR"
            />
          </div>
          <Textarea
            label="Description"
            value={form.description}
            onChange={e => setField('description', e.target.value)}
            rows={3}
            placeholder="Describe the policy purpose and scope..."
          />
          <Input
            label="Birthright Roles (comma-separated)"
            value={form.birthright_roles}
            onChange={e => setField('birthright_roles', e.target.value)}
            placeholder="e.g. ROLE_FI_VIEWER, ROLE_HR_SELF_SERVICE"
          />
          <label className="flex items-center gap-3 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={e => setField('is_active', e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">Policy is active</span>
          </label>
        </div>
      </Modal>
    </div>
  );
}
