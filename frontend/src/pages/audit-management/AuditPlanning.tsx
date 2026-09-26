import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  SparklesIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { auditManagementApi } from '../../services/auditManagementApi';
import {
  PageHeader,
  Card,
  Badge,
  Button,
  Table,
  Modal,
  Input,
  Select,
  Textarea,
  LoadingState,
  ErrorState,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AuditPlan {
  id: string;
  name: string;
  description: string;
  plan_type: string;
  fiscal_year: number;
  total_audit_hours: number;
  status: string;
  engagement_count: number;
}

interface CreatePlanForm {
  name: string;
  description: string;
  plan_type: string;
  fiscal_year: string;
  total_audit_hours: string;
}

interface GeneratePlanForm {
  fiscal_year: string;
  max_engagements: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PLAN_TYPE_OPTIONS = [
  { value: 'annual', label: 'Annual' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'ad_hoc', label: 'Ad Hoc' },
  { value: 'regulatory', label: 'Regulatory' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'approved', label: 'Approved' },
  { value: 'active', label: 'Active' },
  { value: 'closed', label: 'Closed' },
];

const FISCAL_YEAR_OPTIONS = Array.from({ length: 6 }, (_, i) => {
  const y = new Date().getFullYear() - 1 + i;
  return { value: String(y), label: String(y) };
});

const PLAN_TYPE_FILTER_OPTIONS = [{ value: '', label: 'All Types' }, ...PLAN_TYPE_OPTIONS];

function planTypeBadge(pt: string): 'info' | 'warning' | 'neutral' | 'success' {
  const m: Record<string, 'info' | 'warning' | 'neutral' | 'success'> = {
    annual: 'info', quarterly: 'warning', ad_hoc: 'neutral', regulatory: 'success',
  };
  return m[pt] ?? 'neutral';
}

function statusBadge(s: string): 'neutral' | 'info' | 'warning' | 'success' | 'danger' {
  const m: Record<string, 'neutral' | 'info' | 'warning' | 'success' | 'danger'> = {
    draft: 'neutral', submitted: 'info', approved: 'success', active: 'success', closed: 'neutral',
  };
  return m[s] ?? 'neutral';
}

const EMPTY_CREATE: CreatePlanForm = {
  name: '', description: '', plan_type: 'annual',
  fiscal_year: String(new Date().getFullYear()), total_audit_hours: '',
};

const EMPTY_GENERATE: GeneratePlanForm = {
  fiscal_year: String(new Date().getFullYear()), max_engagements: '10',
};

// ─── Component ────────────────────────────────────────────────────────────────

export function AuditPlanning() {
  const qc = useQueryClient();

  // Filters
  const [fiscalYearFilter, setFiscalYearFilter] = useState('');
  const [planTypeFilter, setPlanTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Modals
  const [showCreate, setShowCreate] = useState(false);
  const [showGenerate, setShowGenerate] = useState(false);
  const [confirmSubmit, setConfirmSubmit] = useState<AuditPlan | null>(null);
  const [confirmApprove, setConfirmApprove] = useState<AuditPlan | null>(null);

  // Form state
  const [createForm, setCreateForm] = useState<CreatePlanForm>(EMPTY_CREATE);
  const [generateForm, setGenerateForm] = useState<GeneratePlanForm>(EMPTY_GENERATE);
  const [approveComments, setApproveComments] = useState('');

  // ── Queries ──────────────────────────────────────────────────────────────────

  const { data, isLoading, error } = useQuery<AuditPlan[]>({
    queryKey: ['audit-management', 'plans', { fiscalYearFilter, planTypeFilter, statusFilter }],
    queryFn: async () => {
      const res = await auditManagementApi.listPlans({
        fiscal_year: fiscalYearFilter || undefined,
        plan_type: planTypeFilter || undefined,
        status: statusFilter || undefined,
      });
      return res.data;
    },
  });

  // ── Mutations ─────────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (form: CreatePlanForm) =>
      auditManagementApi.createPlan({
        ...form,
        fiscal_year: parseInt(form.fiscal_year),
        total_audit_hours: parseInt(form.total_audit_hours),
      }),
    onSuccess: () => {
      toast.success('Audit plan created successfully');
      qc.invalidateQueries({ queryKey: ['audit-management', 'plans'] });
      setShowCreate(false);
      setCreateForm(EMPTY_CREATE);
    },
    onError: () => toast.error('Failed to create audit plan'),
  });

  const generateMutation = useMutation({
    mutationFn: (form: GeneratePlanForm) =>
      auditManagementApi.generateRiskBasedPlan({
        fiscal_year: parseInt(form.fiscal_year),
        max_engagements: parseInt(form.max_engagements),
      }),
    onSuccess: () => {
      toast.success('Risk-based plan generated successfully');
      qc.invalidateQueries({ queryKey: ['audit-management', 'plans'] });
      setShowGenerate(false);
      setGenerateForm(EMPTY_GENERATE);
    },
    onError: () => toast.error('Failed to generate risk-based plan'),
  });

  const submitMutation = useMutation({
    mutationFn: (id: string) => auditManagementApi.submitPlan(id),
    onSuccess: () => {
      toast.success('Plan submitted for approval');
      qc.invalidateQueries({ queryKey: ['audit-management', 'plans'] });
      setConfirmSubmit(null);
    },
    onError: () => toast.error('Failed to submit plan'),
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, comments }: { id: string; comments: string }) =>
      auditManagementApi.approvePlan(id, { comments }),
    onSuccess: () => {
      toast.success('Plan approved');
      qc.invalidateQueries({ queryKey: ['audit-management', 'plans'] });
      setConfirmApprove(null);
      setApproveComments('');
    },
    onError: () => toast.error('Failed to approve plan'),
  });

  // ── Table columns ─────────────────────────────────────────────────────────────

  const columns = [
    {
      key: 'id',
      header: 'Plan ID',
      render: (p: AuditPlan) => (
        <span className="text-xs font-mono text-gray-500 dark:text-gray-400">{p.id.slice(0, 8)}</span>
      ),
    },
    {
      key: 'name',
      header: 'Name',
      render: (p: AuditPlan) => (
        <div className="flex items-center gap-2">
          <DocumentTextIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
          <span className="font-medium text-gray-900 dark:text-gray-100">{p.name}</span>
        </div>
      ),
    },
    {
      key: 'fiscal_year',
      header: 'Fiscal Year',
      render: (p: AuditPlan) => (
        <span className="font-medium text-gray-700 dark:text-gray-300">{p.fiscal_year}</span>
      ),
    },
    {
      key: 'plan_type',
      header: 'Type',
      render: (p: AuditPlan) => (
        <Badge variant={planTypeBadge(p.plan_type)}>
          {p.plan_type.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'total_audit_hours',
      header: 'Total Hours',
      render: (p: AuditPlan) => (
        <span className="text-gray-700 dark:text-gray-300">{p.total_audit_hours.toLocaleString()}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (p: AuditPlan) => (
        <Badge variant={statusBadge(p.status)} dot>{p.status}</Badge>
      ),
    },
    {
      key: 'engagement_count',
      header: 'Engagements',
      render: (p: AuditPlan) => (
        <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 text-xs font-semibold">
          {p.engagement_count}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (p: AuditPlan) => (
        <div className="flex items-center gap-2">
          {p.status === 'draft' && (
            <Button size="sm" variant="secondary" onClick={() => setConfirmSubmit(p)}>
              Submit
            </Button>
          )}
          {p.status === 'submitted' && (
            <Button size="sm" variant="success" onClick={() => setConfirmApprove(p)}>
              Approve
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Planning"
        subtitle="Manage annual and ad hoc audit plans, allocate hours, and track completion"
        breadcrumbs={[{ label: 'Audit Management' }, { label: 'Planning' }]}
        actions={
          <>
            <Button
              variant="secondary"
              size="sm"
              icon={<SparklesIcon className="h-4 w-4" />}
              onClick={() => setShowGenerate(true)}
            >
              Generate Risk-Based Plan
            </Button>
            <Button
              variant="primary"
              size="sm"
              icon={<PlusIcon className="h-4 w-4" />}
              onClick={() => setShowCreate(true)}
            >
              Create Plan
            </Button>
          </>
        }
      />

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="w-36">
            <Select
              label="Fiscal Year"
              value={fiscalYearFilter}
              onChange={(e) => setFiscalYearFilter(e.target.value)}
              options={[{ value: '', label: 'All Years' }, ...FISCAL_YEAR_OPTIONS]}
            />
          </div>
          <div className="w-40">
            <Select
              label="Plan Type"
              value={planTypeFilter}
              onChange={(e) => setPlanTypeFilter(e.target.value)}
              options={PLAN_TYPE_FILTER_OPTIONS}
            />
          </div>
          <div className="w-40">
            <Select
              label="Status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={STATUS_OPTIONS}
            />
          </div>
        </div>
      </Card>

      {/* Table */}
      {isLoading && <LoadingState />}
      {error && <ErrorState message="Failed to load audit plans" />}
      {!isLoading && !error && (
        <Table
          columns={columns}
          data={data ?? []}
          emptyMessage="No audit plans found. Create one to get started."
        />
      )}

      {/* Create Plan Modal */}
      <Modal
        open={showCreate}
        onClose={() => { setShowCreate(false); setCreateForm(EMPTY_CREATE); }}
        title="Create Audit Plan"
        subtitle="Define a new audit plan with budget and scope"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setShowCreate(false); setCreateForm(EMPTY_CREATE); }}>
              Cancel
            </Button>
            <Button
              variant="primary"
              loading={createMutation.isPending}
              onClick={() => createMutation.mutate(createForm)}
              disabled={!createForm.name || !createForm.fiscal_year || !createForm.total_audit_hours}
            >
              Create Plan
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input
            label="Plan Name"
            required
            value={createForm.name}
            onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="e.g. FY2027 Annual Audit Plan"
          />
          <Textarea
            label="Description"
            value={createForm.description}
            onChange={(e) => setCreateForm((f) => ({ ...f, description: e.target.value }))}
            placeholder="Scope and objectives of this audit plan..."
            rows={3}
          />
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Plan Type"
              required
              value={createForm.plan_type}
              onChange={(e) => setCreateForm((f) => ({ ...f, plan_type: e.target.value }))}
              options={PLAN_TYPE_OPTIONS}
            />
            <Select
              label="Fiscal Year"
              required
              value={createForm.fiscal_year}
              onChange={(e) => setCreateForm((f) => ({ ...f, fiscal_year: e.target.value }))}
              options={FISCAL_YEAR_OPTIONS}
            />
          </div>
          <Input
            label="Total Audit Hours"
            type="number"
            required
            min="1"
            value={createForm.total_audit_hours}
            onChange={(e) => setCreateForm((f) => ({ ...f, total_audit_hours: e.target.value }))}
            placeholder="e.g. 2000"
          />
        </div>
      </Modal>

      {/* Generate Risk-Based Plan Modal */}
      <Modal
        open={showGenerate}
        onClose={() => { setShowGenerate(false); setGenerateForm(EMPTY_GENERATE); }}
        title="Generate Risk-Based Plan"
        subtitle="AI-assisted plan generation based on entity risk scores"
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setShowGenerate(false); setGenerateForm(EMPTY_GENERATE); }}>
              Cancel
            </Button>
            <Button
              variant="primary"
              icon={<SparklesIcon className="h-4 w-4" />}
              loading={generateMutation.isPending}
              onClick={() => generateMutation.mutate(generateForm)}
            >
              Generate Plan
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="p-3 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 text-sm text-indigo-700 dark:text-indigo-300">
            The system will analyze entity risk scores and suggest an optimal audit schedule for the selected fiscal year.
          </div>
          <Select
            label="Fiscal Year"
            required
            value={generateForm.fiscal_year}
            onChange={(e) => setGenerateForm((f) => ({ ...f, fiscal_year: e.target.value }))}
            options={FISCAL_YEAR_OPTIONS}
          />
          <Input
            label="Max Engagements"
            type="number"
            required
            min="1"
            max="100"
            value={generateForm.max_engagements}
            onChange={(e) => setGenerateForm((f) => ({ ...f, max_engagements: e.target.value }))}
            helpText="Maximum number of engagements to include in the generated plan"
          />
        </div>
      </Modal>

      {/* Confirm Submit Modal */}
      <Modal
        open={!!confirmSubmit}
        onClose={() => setConfirmSubmit(null)}
        title="Submit Plan for Approval"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmSubmit(null)}>Cancel</Button>
            <Button
              variant="primary"
              loading={submitMutation.isPending}
              onClick={() => confirmSubmit && submitMutation.mutate(confirmSubmit.id)}
            >
              Confirm Submit
            </Button>
          </>
        }
      >
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Submit <span className="font-semibold text-gray-900 dark:text-gray-100">"{confirmSubmit?.name}"</span> for
          approval? Once submitted, it will be locked for editing until an approver reviews it.
        </p>
      </Modal>

      {/* Confirm Approve Modal */}
      <Modal
        open={!!confirmApprove}
        onClose={() => { setConfirmApprove(null); setApproveComments(''); }}
        title="Approve Audit Plan"
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setConfirmApprove(null); setApproveComments(''); }}>Cancel</Button>
            <Button
              variant="success"
              loading={approveMutation.isPending}
              onClick={() =>
                confirmApprove &&
                approveMutation.mutate({ id: confirmApprove.id, comments: approveComments })
              }
            >
              Approve Plan
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Approving <span className="font-semibold text-gray-900 dark:text-gray-100">"{confirmApprove?.name}"</span>.
            This will activate the plan and allow engagements to begin.
          </p>
          <Textarea
            label="Approval Comments (optional)"
            value={approveComments}
            onChange={(e) => setApproveComments(e.target.value)}
            placeholder="Any notes for the audit team..."
            rows={3}
          />
        </div>
      </Modal>
    </div>
  );
}
