import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
  EyeIcon,
  ExclamationTriangleIcon,
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
  SearchInput,
} from '../../components/ui';

// ─── Types ───────────────────────────────────────────────────────────────────

type RiskCategory = 'strategic' | 'operational' | 'financial' | 'compliance' | 'it_cyber';
type RiskStatus = 'open' | 'in_review' | 'mitigated' | 'accepted' | 'closed';

interface Risk {
  id: string;
  risk_id: string;
  title: string;
  description: string;
  category: RiskCategory;
  owner: string;
  owner_email?: string;
  inherent_likelihood: number;
  inherent_impact: number;
  residual_likelihood: number;
  residual_impact: number;
  status: RiskStatus;
  treatment: string;
  review_date?: string;
  created_at: string;
  updated_at?: string;
}

interface RiskFormData {
  title: string;
  description: string;
  category: RiskCategory | '';
  owner: string;
  owner_email: string;
  inherent_likelihood: number;
  inherent_impact: number;
  residual_likelihood: number;
  residual_impact: number;
  status: RiskStatus;
  treatment: string;
  review_date: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const EMPTY_FORM: RiskFormData = {
  title: '',
  description: '',
  category: '',
  owner: '',
  owner_email: '',
  inherent_likelihood: 1,
  inherent_impact: 1,
  residual_likelihood: 1,
  residual_impact: 1,
  status: 'open',
  treatment: '',
  review_date: '',
};

function scoreVariant(score: number): 'success' | 'warning' | 'danger' {
  if (score <= 5) return 'success';
  if (score <= 12) return 'warning';
  return 'danger';
}

function scoreLabel(score: number): string {
  if (score <= 5) return 'Low';
  if (score <= 12) return 'Medium';
  if (score <= 19) return 'High';
  return 'Critical';
}

function ScoreBadge({ likelihood, impact }: { likelihood: number; impact: number }) {
  const score = likelihood * impact;
  return (
    <Badge variant={scoreVariant(score)} size="sm">
      {score} ({scoreLabel(score)})
    </Badge>
  );
}

const CATEGORY_LABELS: Record<RiskCategory, string> = {
  strategic: 'Strategic',
  operational: 'Operational',
  financial: 'Financial',
  compliance: 'Compliance',
  it_cyber: 'IT / Cyber',
};

const STATUS_LABELS: Record<RiskStatus, string> = {
  open: 'Open',
  in_review: 'In Review',
  mitigated: 'Mitigated',
  accepted: 'Accepted',
  closed: 'Closed',
};

const STATUS_VARIANT: Record<RiskStatus, 'danger' | 'warning' | 'info' | 'success' | 'neutral'> = {
  open: 'danger',
  in_review: 'info',
  mitigated: 'success',
  accepted: 'neutral',
  closed: 'neutral',
};

const SCALE_OPTIONS = [1, 2, 3, 4, 5].map(n => ({ value: String(n), label: String(n) }));

const CATEGORY_OPTIONS = [
  { value: 'strategic', label: 'Strategic' },
  { value: 'operational', label: 'Operational' },
  { value: 'financial', label: 'Financial' },
  { value: 'compliance', label: 'Compliance' },
  { value: 'it_cyber', label: 'IT / Cyber' },
];

const STATUS_OPTIONS: { value: RiskStatus; label: string }[] = [
  { value: 'open', label: 'Open' },
  { value: 'in_review', label: 'In Review' },
  { value: 'mitigated', label: 'Mitigated' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'closed', label: 'Closed' },
];

// ─── Validation ───────────────────────────────────────────────────────────────

function validateForm(form: RiskFormData): Partial<Record<keyof RiskFormData, string>> {
  const errors: Partial<Record<keyof RiskFormData, string>> = {};
  if (!form.title.trim()) errors.title = 'Title is required';
  if (!form.category) errors.category = 'Category is required';
  if (!form.owner.trim()) errors.owner = 'Risk owner is required';
  if (!form.description.trim()) errors.description = 'Description is required';
  return errors;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function RiskRegister() {
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const [showModal, setShowModal] = useState(false);
  const [editingRisk, setEditingRisk] = useState<Risk | null>(null);
  const [form, setForm] = useState<RiskFormData>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof RiskFormData, string>>>({});

  const [deleteTarget, setDeleteTarget] = useState<Risk | null>(null);
  const [viewingRisk, setViewingRisk] = useState<Risk | null>(null);

  // ── Queries ──

  const { data: risksData, isLoading } = useQuery<Risk[]>({
    queryKey: ['risk-register', categoryFilter, statusFilter],
    queryFn: () =>
      riskManagementApi
        .listRisks({
          category: categoryFilter || undefined,
          status: statusFilter || undefined,
        })
        .then(r => r.data?.risks ?? r.data ?? []),
  });

  const risks: Risk[] = risksData ?? [];

  const filteredRisks = risks.filter(r => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      r.title.toLowerCase().includes(q) ||
      r.risk_id?.toLowerCase().includes(q) ||
      r.owner.toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createMutation = useMutation({
    mutationFn: (data: RiskFormData) => riskManagementApi.createRisk(data),
    onSuccess: () => {
      toast.success('Risk created successfully');
      queryClient.invalidateQueries({ queryKey: ['risk-register'] });
      closeModal();
    },
    onError: () => toast.error('Failed to create risk'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: RiskFormData }) =>
      riskManagementApi.updateRisk(id, data),
    onSuccess: () => {
      toast.success('Risk updated successfully');
      queryClient.invalidateQueries({ queryKey: ['risk-register'] });
      closeModal();
    },
    onError: () => toast.error('Failed to update risk'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => riskManagementApi.deleteRisk(id),
    onSuccess: () => {
      toast.success('Risk deleted');
      queryClient.invalidateQueries({ queryKey: ['risk-register'] });
      setDeleteTarget(null);
    },
    onError: () => toast.error('Failed to delete risk'),
  });

  // ── Handlers ──

  function openCreate() {
    setEditingRisk(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
    setShowModal(true);
  }

  function openEdit(risk: Risk) {
    setEditingRisk(risk);
    setForm({
      title: risk.title,
      description: risk.description,
      category: risk.category,
      owner: risk.owner,
      owner_email: risk.owner_email ?? '',
      inherent_likelihood: risk.inherent_likelihood,
      inherent_impact: risk.inherent_impact,
      residual_likelihood: risk.residual_likelihood,
      residual_impact: risk.residual_impact,
      status: risk.status,
      treatment: risk.treatment ?? '',
      review_date: risk.review_date ?? '',
    });
    setFormErrors({});
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setEditingRisk(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
  }

  function handleSubmit() {
    const errors = validateForm(form);
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }
    if (editingRisk) {
      updateMutation.mutate({ id: editingRisk.id, data: form });
    } else {
      createMutation.mutate(form);
    }
  }

  function setField<K extends keyof RiskFormData>(key: K, value: RiskFormData[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Stats ──

  const openCount = risks.filter(r => r.status === 'open').length;
  const highCount = risks.filter(r => r.inherent_likelihood * r.inherent_impact >= 13).length;
  const mitigatedCount = risks.filter(r => r.status === 'mitigated').length;
  const inReviewCount = risks.filter(r => r.status === 'in_review').length;

  // ── Columns ──

  const columns = [
    {
      key: 'risk_id',
      header: 'Risk ID',
      render: (r: Risk) => (
        <span className="text-sm font-mono font-medium text-indigo-600 dark:text-indigo-400">
          {r.risk_id || r.id}
        </span>
      ),
    },
    {
      key: 'title',
      header: 'Title',
      render: (r: Risk) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100 max-w-xs truncate">{r.title}</div>
          <div className="text-xs text-gray-400 capitalize">{CATEGORY_LABELS[r.category] ?? r.category}</div>
        </div>
      ),
    },
    {
      key: 'owner',
      header: 'Owner',
      render: (r: Risk) => (
        <div>
          <div className="text-sm text-gray-700 dark:text-gray-300">{r.owner}</div>
          {r.owner_email && (
            <div className="text-xs text-gray-400">{r.owner_email}</div>
          )}
        </div>
      ),
    },
    {
      key: 'inherent',
      header: 'Inherent Score',
      render: (r: Risk) => (
        <ScoreBadge likelihood={r.inherent_likelihood} impact={r.inherent_impact} />
      ),
    },
    {
      key: 'residual',
      header: 'Residual Score',
      render: (r: Risk) => (
        <ScoreBadge likelihood={r.residual_likelihood} impact={r.residual_impact} />
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (r: Risk) => (
        <Badge variant={STATUS_VARIANT[r.status] ?? 'neutral'} dot size="sm">
          {STATUS_LABELS[r.status] ?? r.status}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (r: Risk) => (
        <div className="flex justify-end gap-2">
          <button
            onClick={e => { e.stopPropagation(); setViewingRisk(r); }}
            className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors"
            title="View"
          >
            <EyeIcon className="h-4 w-4" />
          </button>
          <button
            onClick={e => { e.stopPropagation(); openEdit(r); }}
            className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors"
            title="Edit"
          >
            <PencilSquareIcon className="h-4 w-4" />
          </button>
          <button
            onClick={e => { e.stopPropagation(); setDeleteTarget(r); }}
            className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            title="Delete"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Register"
        subtitle="Manage and track enterprise risks across all categories"
        actions={
          <Button
            icon={<PlusIcon className="h-4 w-4" />}
            onClick={openCreate}
          >
            Add Risk
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard
          title="Open Risks"
          value={openCount}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-red"
          iconColor=""
        />
        <StatCard
          title="High / Critical"
          value={highCount}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-orange"
          iconColor=""
        />
        <StatCard
          title="In Review"
          value={inReviewCount}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-yellow"
          iconColor=""
        />
        <StatCard
          title="Mitigated"
          value={mitigatedCount}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-green"
          iconColor=""
        />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by title, ID, or owner..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={categoryFilter}
            onChange={e => setCategoryFilter(e.target.value)}
            options={[{ value: '', label: 'All Categories' }, ...CATEGORY_OPTIONS]}
          />
          <Select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            options={[{ value: '', label: 'All Status' }, ...STATUS_OPTIONS]}
          />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filteredRisks}
        loading={isLoading}
        onRowClick={r => setViewingRisk(r)}
        emptyMessage="No risks found. Click 'Add Risk' to create your first risk entry."
      />

      {/* Create / Edit Modal */}
      <Modal
        open={showModal}
        onClose={closeModal}
        title={editingRisk ? 'Edit Risk' : 'Add Risk'}
        subtitle={editingRisk ? `Editing: ${editingRisk.risk_id || editingRisk.id}` : 'Register a new risk in the register'}
        size="xl"
        footer={
          <>
            <Button variant="secondary" onClick={closeModal}>Cancel</Button>
            <Button onClick={handleSubmit} loading={isSaving}>
              {editingRisk ? 'Save Changes' : 'Create Risk'}
            </Button>
          </>
        }
      >
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Risk Title"
                required
                value={form.title}
                onChange={e => setField('title', e.target.value)}
                error={formErrors.title}
                placeholder="e.g. Unauthorised data access via privileged accounts"
              />
            </div>

            <Select
              label="Category"
              required
              value={form.category}
              onChange={e => setField('category', e.target.value as RiskCategory)}
              options={CATEGORY_OPTIONS}
              placeholder="Select category..."
              error={formErrors.category}
            />

            <Select
              label="Status"
              value={form.status}
              onChange={e => setField('status', e.target.value as RiskStatus)}
              options={STATUS_OPTIONS}
            />

            <Input
              label="Risk Owner"
              required
              value={form.owner}
              onChange={e => setField('owner', e.target.value)}
              error={formErrors.owner}
              placeholder="Full name"
            />

            <Input
              label="Owner Email"
              type="email"
              value={form.owner_email}
              onChange={e => setField('owner_email', e.target.value)}
              placeholder="owner@company.com"
            />
          </div>

          <Textarea
            label="Description"
            required
            value={form.description}
            onChange={e => setField('description', e.target.value)}
            error={formErrors.description}
            rows={3}
            placeholder="Describe the risk, its cause, and potential impact..."
          />

          {/* Inherent risk */}
          <div>
            <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-3">
              Inherent Risk (before controls)
            </p>
            <div className="grid grid-cols-2 gap-4">
              <Select
                label="Likelihood (1–5)"
                value={String(form.inherent_likelihood)}
                onChange={e => setField('inherent_likelihood', Number(e.target.value))}
                options={SCALE_OPTIONS}
              />
              <Select
                label="Impact (1–5)"
                value={String(form.inherent_impact)}
                onChange={e => setField('inherent_impact', Number(e.target.value))}
                options={SCALE_OPTIONS}
              />
            </div>
            <div className="mt-2 flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              Inherent Score:
              <ScoreBadge
                likelihood={form.inherent_likelihood}
                impact={form.inherent_impact}
              />
            </div>
          </div>

          {/* Residual risk */}
          <div>
            <p className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-3">
              Residual Risk (after controls)
            </p>
            <div className="grid grid-cols-2 gap-4">
              <Select
                label="Likelihood (1–5)"
                value={String(form.residual_likelihood)}
                onChange={e => setField('residual_likelihood', Number(e.target.value))}
                options={SCALE_OPTIONS}
              />
              <Select
                label="Impact (1–5)"
                value={String(form.residual_impact)}
                onChange={e => setField('residual_impact', Number(e.target.value))}
                options={SCALE_OPTIONS}
              />
            </div>
            <div className="mt-2 flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              Residual Score:
              <ScoreBadge
                likelihood={form.residual_likelihood}
                impact={form.residual_impact}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Review Date"
              type="date"
              value={form.review_date}
              onChange={e => setField('review_date', e.target.value)}
            />
            <Select
              label="Treatment"
              value={form.treatment}
              onChange={e => setField('treatment', e.target.value)}
              options={[
                { value: '', label: 'Select treatment...' },
                { value: 'mitigate', label: 'Mitigate' },
                { value: 'accept', label: 'Accept' },
                { value: 'transfer', label: 'Transfer' },
                { value: 'avoid', label: 'Avoid' },
              ]}
            />
          </div>
        </div>
      </Modal>

      {/* View Detail Modal */}
      {viewingRisk && (
        <Modal
          open
          onClose={() => setViewingRisk(null)}
          title="Risk Detail"
          subtitle={viewingRisk.risk_id || viewingRisk.id}
          size="lg"
          footer={
            <>
              <Button variant="secondary" onClick={() => setViewingRisk(null)}>Close</Button>
              <Button onClick={() => { openEdit(viewingRisk); setViewingRisk(null); }}>
                Edit
              </Button>
            </>
          }
        >
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Category</p>
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                  {CATEGORY_LABELS[viewingRisk.category] ?? viewingRisk.category}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Status</p>
                <Badge variant={STATUS_VARIANT[viewingRisk.status] ?? 'neutral'} dot size="sm">
                  {STATUS_LABELS[viewingRisk.status] ?? viewingRisk.status}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Owner</p>
                <p className="text-sm text-gray-800 dark:text-gray-200">{viewingRisk.owner}</p>
                {viewingRisk.owner_email && (
                  <p className="text-xs text-gray-400">{viewingRisk.owner_email}</p>
                )}
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Review Date</p>
                <p className="text-sm text-gray-800 dark:text-gray-200">
                  {viewingRisk.review_date ?? '—'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Inherent Score</p>
                <ScoreBadge
                  likelihood={viewingRisk.inherent_likelihood}
                  impact={viewingRisk.inherent_impact}
                />
                <p className="text-xs text-gray-400 mt-1">
                  L{viewingRisk.inherent_likelihood} × I{viewingRisk.inherent_impact}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Residual Score</p>
                <ScoreBadge
                  likelihood={viewingRisk.residual_likelihood}
                  impact={viewingRisk.residual_impact}
                />
                <p className="text-xs text-gray-400 mt-1">
                  L{viewingRisk.residual_likelihood} × I{viewingRisk.residual_impact}
                </p>
              </div>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Description</p>
              <p className="text-sm text-gray-700 dark:text-gray-300">{viewingRisk.description}</p>
            </div>
            {viewingRisk.treatment && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Treatment</p>
                <p className="text-sm text-gray-700 dark:text-gray-300 capitalize">{viewingRisk.treatment}</p>
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete Risk"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button
              variant="danger"
              loading={deleteMutation.isPending}
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Are you sure you want to delete{' '}
          <span className="font-semibold text-gray-900 dark:text-gray-100">
            {deleteTarget?.title}
          </span>
          ? This action cannot be undone.
        </p>
      </Modal>
    </div>
  );
}
