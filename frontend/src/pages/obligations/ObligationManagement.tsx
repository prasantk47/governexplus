import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  ScaleIcon,
  CheckBadgeIcon,
  ExclamationCircleIcon,
  ClockIcon,
  ClipboardDocumentCheckIcon,
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

type ComplianceStatus = 'compliant' | 'partially_compliant' | 'non_compliant' | 'not_assessed';

interface Obligation {
  id: string;
  obligation_id: string;
  title: string;
  regulation_name: string;
  jurisdiction: string;
  category?: string;
  obligation_type?: string;
  compliance_status: ComplianceStatus;
  owner: string;
  next_review_date?: string;
  section_reference?: string;
  created_at: string;
}

interface ObligationForm {
  title: string;
  regulation_name: string;
  jurisdiction: string;
  category: string;
  obligation_type: string;
  owner: string;
  section_reference: string;
}

interface AssessForm {
  compliance_rating: 'compliant' | 'partially_compliant' | 'non_compliant' | '';
  evidence_summary: string;
}

interface ObligationStats {
  total: number;
  compliant: number;
  non_compliant: number;
  overdue_reviews: number;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_FORM: ObligationForm = {
  title: '',
  regulation_name: '',
  jurisdiction: '',
  category: '',
  obligation_type: '',
  owner: '',
  section_reference: '',
};

const EMPTY_ASSESS: AssessForm = {
  compliance_rating: '',
  evidence_summary: '',
};

const STATUS_VARIANT: Record<ComplianceStatus, 'success' | 'warning' | 'danger' | 'neutral'> = {
  compliant: 'success',
  partially_compliant: 'warning',
  non_compliant: 'danger',
  not_assessed: 'neutral',
};

const STATUS_FILTER_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'compliant', label: 'Compliant' },
  { value: 'partially_compliant', label: 'Partially Compliant' },
  { value: 'non_compliant', label: 'Non-Compliant' },
  { value: 'not_assessed', label: 'Not Assessed' },
];

const RATING_OPTIONS = [
  { value: 'compliant', label: 'Compliant' },
  { value: 'partially_compliant', label: 'Partially Compliant' },
  { value: 'non_compliant', label: 'Non-Compliant' },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function ObligationManagement() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAssessModal, setShowAssessModal] = useState(false);
  const [assessTarget, setAssessTarget] = useState<Obligation | null>(null);
  const [form, setForm] = useState<ObligationForm>(EMPTY_FORM);
  const [assessForm, setAssessForm] = useState<AssessForm>(EMPTY_ASSESS);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof ObligationForm, string>>>({});
  const [assessErrors, setAssessErrors] = useState<Partial<Record<keyof AssessForm, string>>>({});

  // ── Queries ──

  const { data: statsData } = useQuery<ObligationStats>({
    queryKey: ['obligations-stats'],
    queryFn: () =>
      api.get('/obligations/summary/stats').then(r => r.data ?? { total: 0, compliant: 0, non_compliant: 0, overdue_reviews: 0 }),
  });

  const stats: ObligationStats = statsData ?? { total: 0, compliant: 0, non_compliant: 0, overdue_reviews: 0 };

  const { data: obligationsData, isLoading } = useQuery<Obligation[]>({
    queryKey: ['obligations', statusFilter],
    queryFn: () =>
      api
        .get('/obligations/', { params: statusFilter ? { compliance_status: statusFilter } : {} })
        .then(r => r.data?.obligations ?? r.data ?? []),
  });

  const obligations: Obligation[] = obligationsData ?? [];

  const filtered = obligations.filter(o => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      o.obligation_id.toLowerCase().includes(q) ||
      o.title.toLowerCase().includes(q) ||
      o.regulation_name.toLowerCase().includes(q) ||
      o.owner.toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/obligations/', data),
    onSuccess: () => {
      toast.success('Obligation created');
      queryClient.invalidateQueries({ queryKey: ['obligations'] });
      queryClient.invalidateQueries({ queryKey: ['obligations-stats'] });
      closeCreateModal();
    },
    onError: () => toast.error('Failed to create obligation'),
  });

  const assessMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      api.post(`/obligations/${id}/assess`, data),
    onSuccess: () => {
      toast.success('Assessment recorded');
      queryClient.invalidateQueries({ queryKey: ['obligations'] });
      queryClient.invalidateQueries({ queryKey: ['obligations-stats'] });
      closeAssessModal();
    },
    onError: () => toast.error('Assessment failed'),
  });

  // ── Handlers ──

  function openCreateModal() {
    setForm(EMPTY_FORM);
    setFormErrors({});
    setShowCreateModal(true);
  }

  function closeCreateModal() {
    setShowCreateModal(false);
    setForm(EMPTY_FORM);
    setFormErrors({});
  }

  function openAssessModal(obligation: Obligation) {
    setAssessTarget(obligation);
    setAssessForm(EMPTY_ASSESS);
    setAssessErrors({});
    setShowAssessModal(true);
  }

  function closeAssessModal() {
    setShowAssessModal(false);
    setAssessTarget(null);
    setAssessForm(EMPTY_ASSESS);
    setAssessErrors({});
  }

  function validateCreate(): boolean {
    const errors: Partial<Record<keyof ObligationForm, string>> = {};
    if (!form.title.trim()) errors.title = 'Title is required';
    if (!form.regulation_name.trim()) errors.regulation_name = 'Regulation is required';
    if (!form.owner.trim()) errors.owner = 'Owner is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function validateAssess(): boolean {
    const errors: Partial<Record<keyof AssessForm, string>> = {};
    if (!assessForm.compliance_rating) errors.compliance_rating = 'Rating is required';
    setAssessErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleCreate() {
    if (!validateCreate()) return;
    createMutation.mutate({ ...form });
  }

  function handleAssess() {
    if (!validateAssess() || !assessTarget) return;
    assessMutation.mutate({ id: assessTarget.id, data: { ...assessForm } });
  }

  function setField<K extends keyof ObligationForm>(key: K, value: ObligationForm[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Columns ──

  const columns = [
    {
      key: 'obligation_id',
      header: 'Obligation ID',
      render: (o: Obligation) => (
        <span className="text-sm font-mono font-medium text-indigo-600 dark:text-indigo-400">
          {o.obligation_id}
        </span>
      ),
    },
    {
      key: 'title',
      header: 'Title',
      render: (o: Obligation) => (
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100 max-w-xs truncate">
          {o.title}
        </div>
      ),
    },
    {
      key: 'regulation_name',
      header: 'Regulation',
      render: (o: Obligation) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{o.regulation_name}</span>
      ),
    },
    {
      key: 'jurisdiction',
      header: 'Jurisdiction',
      render: (o: Obligation) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{o.jurisdiction || '—'}</span>
      ),
    },
    {
      key: 'compliance_status',
      header: 'Status',
      render: (o: Obligation) => (
        <Badge variant={STATUS_VARIANT[o.compliance_status]} dot size="sm">
          {o.compliance_status.replace(/_/g, ' ')}
        </Badge>
      ),
    },
    {
      key: 'owner',
      header: 'Owner',
      render: (o: Obligation) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{o.owner}</span>
      ),
    },
    {
      key: 'next_review_date',
      header: 'Next Review',
      render: (o: Obligation) => {
        const isOverdue = o.next_review_date && new Date(o.next_review_date) < new Date();
        return (
          <span className={`text-sm ${isOverdue ? 'text-red-600 dark:text-red-400 font-medium' : 'text-gray-500'}`}>
            {o.next_review_date ? new Date(o.next_review_date).toLocaleDateString() : '—'}
          </span>
        );
      },
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (o: Obligation) => (
        <Button
          size="sm"
          variant="ghost"
          icon={<ClipboardDocumentCheckIcon className="h-4 w-4" />}
          onClick={e => { e.stopPropagation(); openAssessModal(o); }}
        >
          Assess
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Obligation Management"
        subtitle="Track regulatory obligations and compliance assessments"
        actions={
          <Button icon={<PlusIcon className="h-4 w-4" />} onClick={openCreateModal}>
            New Obligation
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total" value={stats.total} icon={ScaleIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Compliant" value={stats.compliant} icon={CheckBadgeIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Non-Compliant" value={stats.non_compliant} icon={ExclamationCircleIcon} iconBgColor="stat-icon-red" iconColor="" />
        <StatCard title="Overdue Reviews" value={stats.overdue_reviews} icon={ClockIcon} iconBgColor="stat-icon-orange" iconColor="" />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search obligations..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            options={STATUS_FILTER_OPTIONS}
          />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        emptyMessage="No obligations found. Click 'New Obligation' to add one."
      />

      {/* Create Modal */}
      <Modal
        open={showCreateModal}
        onClose={closeCreateModal}
        title="New Obligation"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={closeCreateModal}>Cancel</Button>
            <Button onClick={handleCreate} loading={createMutation.isPending}>
              Create Obligation
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
                placeholder="Obligation title"
              />
            </div>
            <Input
              label="Regulation Name"
              required
              value={form.regulation_name}
              onChange={e => setField('regulation_name', e.target.value)}
              error={formErrors.regulation_name}
              placeholder="e.g. SOX Section 404"
            />
            <Input
              label="Jurisdiction"
              value={form.jurisdiction}
              onChange={e => setField('jurisdiction', e.target.value)}
              placeholder="e.g. United States"
            />
            <Input
              label="Category"
              value={form.category}
              onChange={e => setField('category', e.target.value)}
              placeholder="e.g. Financial Reporting"
            />
            <Input
              label="Obligation Type"
              value={form.obligation_type}
              onChange={e => setField('obligation_type', e.target.value)}
              placeholder="e.g. Disclosure, Control, Certification"
            />
            <Input
              label="Owner"
              required
              value={form.owner}
              onChange={e => setField('owner', e.target.value)}
              error={formErrors.owner}
              placeholder="Responsible person or team"
            />
            <Input
              label="Section Reference"
              value={form.section_reference}
              onChange={e => setField('section_reference', e.target.value)}
              placeholder="e.g. Section 302(a)"
            />
          </div>
        </div>
      </Modal>

      {/* Assess Modal */}
      <Modal
        open={showAssessModal}
        onClose={closeAssessModal}
        title={`Assess: ${assessTarget?.title ?? ''}`}
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={closeAssessModal}>Cancel</Button>
            <Button onClick={handleAssess} loading={assessMutation.isPending}>
              Submit Assessment
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Select
            label="Compliance Rating"
            required
            value={assessForm.compliance_rating}
            onChange={e => {
              setAssessForm(prev => ({ ...prev, compliance_rating: e.target.value as AssessForm['compliance_rating'] }));
              if (assessErrors.compliance_rating) setAssessErrors(prev => ({ ...prev, compliance_rating: undefined }));
            }}
            options={[{ value: '', label: 'Select rating...' }, ...RATING_OPTIONS]}
            error={assessErrors.compliance_rating}
          />
          <Textarea
            label="Evidence Summary"
            value={assessForm.evidence_summary}
            onChange={e => setAssessForm(prev => ({ ...prev, evidence_summary: e.target.value }))}
            rows={4}
            placeholder="Describe the evidence supporting this assessment..."
          />
        </div>
      </Modal>
    </div>
  );
}
