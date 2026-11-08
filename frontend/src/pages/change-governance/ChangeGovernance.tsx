import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  DocumentTextIcon,
  ClockIcon,
  CheckCircleIcon,
  ArrowPathIcon,
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

type ChangeDomain = 'master_data' | 'financial_config' | 'security_access' | 'grc_config' | 'it_platform' | 'org_reference' | 'policy_control';
type ChangeCategory = 'standard' | 'normal' | 'high_risk' | 'emergency';
type ChangeStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'implementing' | 'verified' | 'closed';

interface ChangeRecord {
  id: string;
  change_id: string;
  title: string;
  domain: ChangeDomain;
  category: ChangeCategory;
  status: ChangeStatus;
  risk_level: string;
  requester: string;
  justification?: string;
  object_type?: string;
  before_value?: string;
  after_value?: string;
  created_at: string;
}

interface ChangeForm {
  title: string;
  domain: ChangeDomain | '';
  category: ChangeCategory | '';
  risk_level: string;
  requester: string;
  justification: string;
  object_type: string;
  before_value: string;
  after_value: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_FORM: ChangeForm = {
  title: '',
  domain: '',
  category: '',
  risk_level: '',
  requester: '',
  justification: '',
  object_type: '',
  before_value: '',
  after_value: '',
};

const STATUS_VARIANT: Record<ChangeStatus, 'neutral' | 'info' | 'success' | 'danger' | 'warning'> = {
  draft: 'neutral',
  submitted: 'info',
  approved: 'success',
  rejected: 'danger',
  implementing: 'warning',
  verified: 'info',
  closed: 'success',
};

const DOMAIN_OPTIONS = [
  { value: 'master_data', label: 'Master Data' },
  { value: 'financial_config', label: 'Financial Config' },
  { value: 'security_access', label: 'Security & Access' },
  { value: 'grc_config', label: 'GRC Config' },
  { value: 'it_platform', label: 'IT Platform' },
  { value: 'org_reference', label: 'Org Reference' },
  { value: 'policy_control', label: 'Policy & Control' },
];

const CATEGORY_OPTIONS = [
  { value: 'standard', label: 'Standard' },
  { value: 'normal', label: 'Normal' },
  { value: 'high_risk', label: 'High Risk' },
  { value: 'emergency', label: 'Emergency' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'implementing', label: 'Implementing' },
  { value: 'verified', label: 'Verified' },
  { value: 'closed', label: 'Closed' },
];

const TRANSITIONS: Record<ChangeStatus, { label: string; target: string }[]> = {
  draft: [{ label: 'Submit', target: 'submitted' }],
  submitted: [
    { label: 'Approve', target: 'approved' },
    { label: 'Reject', target: 'rejected' },
  ],
  approved: [{ label: 'Start Implementation', target: 'implementing' }],
  rejected: [{ label: 'Resubmit', target: 'submitted' }],
  implementing: [{ label: 'Mark Verified', target: 'verified' }],
  verified: [{ label: 'Close', target: 'closed' }],
  closed: [],
};

// ─── Component ────────────────────────────────────────────────────────────────

export function ChangeGovernance() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<ChangeForm>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof ChangeForm, string>>>({});

  // ── Queries ──

  const { data: changesData, isLoading } = useQuery<ChangeRecord[]>({
    queryKey: ['change-governance', statusFilter],
    queryFn: () =>
      api
        .get('/change-governance/', { params: statusFilter ? { status: statusFilter } : {} })
        .then(r => r.data?.changes ?? r.data ?? []),
  });

  const changes: ChangeRecord[] = changesData ?? [];

  const filtered = changes.filter(c => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.change_id.toLowerCase().includes(q) ||
      c.title.toLowerCase().includes(q) ||
      c.requester.toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/change-governance/', data),
    onSuccess: () => {
      toast.success('Change request created');
      queryClient.invalidateQueries({ queryKey: ['change-governance'] });
      closeModal();
    },
    onError: () => toast.error('Failed to create change request'),
  });

  const transitionMutation = useMutation({
    mutationFn: ({ id, target }: { id: string; target: string }) =>
      api.put(`/change-governance/${id}/transition`, { target_status: target }),
    onSuccess: () => {
      toast.success('Status updated');
      queryClient.invalidateQueries({ queryKey: ['change-governance'] });
    },
    onError: () => toast.error('Transition failed'),
  });

  // ── Handlers ──

  function openCreate() {
    setForm(EMPTY_FORM);
    setFormErrors({});
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setForm(EMPTY_FORM);
    setFormErrors({});
  }

  function validate(): boolean {
    const errors: Partial<Record<keyof ChangeForm, string>> = {};
    if (!form.title.trim()) errors.title = 'Title is required';
    if (!form.domain) errors.domain = 'Domain is required';
    if (!form.category) errors.category = 'Category is required';
    if (!form.requester.trim()) errors.requester = 'Requester is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
    createMutation.mutate({ ...form });
  }

  function setField<K extends keyof ChangeForm>(key: K, value: ChangeForm[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Stats ──

  const totalCount = changes.length;
  const pendingCount = changes.filter(c => c.status === 'submitted').length;
  const implementedCount = changes.filter(c => c.status === 'implementing' || c.status === 'verified').length;
  const closedCount = changes.filter(c => c.status === 'closed').length;

  // ── Columns ──

  const columns = [
    {
      key: 'change_id',
      header: 'Change ID',
      render: (c: ChangeRecord) => (
        <span className="text-sm font-mono font-medium text-indigo-600 dark:text-indigo-400">
          {c.change_id}
        </span>
      ),
    },
    {
      key: 'title',
      header: 'Title',
      render: (c: ChangeRecord) => (
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100 max-w-xs truncate">
          {c.title}
        </div>
      ),
    },
    {
      key: 'domain',
      header: 'Domain',
      render: (c: ChangeRecord) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">
          {c.domain.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'category',
      header: 'Category',
      render: (c: ChangeRecord) => (
        <Badge variant={c.category === 'emergency' ? 'danger' : c.category === 'high_risk' ? 'warning' : 'neutral'} size="sm">
          {c.category.replace(/_/g, ' ')}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (c: ChangeRecord) => (
        <Badge variant={STATUS_VARIANT[c.status]} dot size="sm">
          {c.status.replace(/_/g, ' ')}
        </Badge>
      ),
    },
    {
      key: 'risk_level',
      header: 'Risk Level',
      render: (c: ChangeRecord) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{c.risk_level || '—'}</span>
      ),
    },
    {
      key: 'requester',
      header: 'Requester',
      render: (c: ChangeRecord) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{c.requester}</span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (c: ChangeRecord) => (
        <span className="text-sm text-gray-500">
          {new Date(c.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (c: ChangeRecord) => {
        const transitions = TRANSITIONS[c.status] ?? [];
        if (transitions.length === 0) return null;
        return (
          <div className="flex justify-end gap-1">
            {transitions.map(t => (
              <Button
                key={t.target}
                size="sm"
                variant="ghost"
                onClick={e => {
                  e.stopPropagation();
                  transitionMutation.mutate({ id: c.id, target: t.target });
                }}
              >
                {t.label}
              </Button>
            ))}
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Change Governance"
        subtitle="Track configuration and policy changes across domains"
        actions={
          <Button icon={<PlusIcon className="h-4 w-4" />} onClick={openCreate}>
            New Change
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Changes" value={totalCount} icon={DocumentTextIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Pending Approval" value={pendingCount} icon={ClockIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Implemented" value={implementedCount} icon={ArrowPathIcon} iconBgColor="stat-icon-yellow" iconColor="" />
        <StatCard title="Closed" value={closedCount} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by change ID, title, or requester..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            options={STATUS_OPTIONS}
          />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        emptyMessage="No change requests found. Click 'New Change' to create one."
      />

      {/* Create Modal */}
      <Modal
        open={showModal}
        onClose={closeModal}
        title="New Change Request"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={closeModal}>Cancel</Button>
            <Button onClick={handleSubmit} loading={createMutation.isPending}>
              Create Change
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
                value={form.title}
                onChange={e => setField('title', e.target.value)}
                error={formErrors.title}
                placeholder="Brief description of the change"
              />
            </div>
            <Select
              label="Domain"
              required
              value={form.domain}
              onChange={e => setField('domain', e.target.value as ChangeDomain)}
              options={[{ value: '', label: 'Select domain...' }, ...DOMAIN_OPTIONS]}
              error={formErrors.domain}
            />
            <Select
              label="Category"
              required
              value={form.category}
              onChange={e => setField('category', e.target.value as ChangeCategory)}
              options={[{ value: '', label: 'Select category...' }, ...CATEGORY_OPTIONS]}
              error={formErrors.category}
            />
            <Input
              label="Risk Level"
              value={form.risk_level}
              onChange={e => setField('risk_level', e.target.value)}
              placeholder="e.g. High, Medium, Low"
            />
            <Input
              label="Requester"
              required
              value={form.requester}
              onChange={e => setField('requester', e.target.value)}
              error={formErrors.requester}
              placeholder="Name or user ID"
            />
            <Input
              label="Object Type"
              value={form.object_type}
              onChange={e => setField('object_type', e.target.value)}
              placeholder="e.g. GL Account, Auth Object"
            />
            <Input
              label="Before Value"
              value={form.before_value}
              onChange={e => setField('before_value', e.target.value)}
              placeholder="Current value"
            />
            <Input
              label="After Value"
              value={form.after_value}
              onChange={e => setField('after_value', e.target.value)}
              placeholder="Proposed value"
            />
          </div>
          <Textarea
            label="Justification"
            value={form.justification}
            onChange={e => setField('justification', e.target.value)}
            rows={3}
            placeholder="Business justification for this change..."
          />
        </div>
      </Modal>
    </div>
  );
}
