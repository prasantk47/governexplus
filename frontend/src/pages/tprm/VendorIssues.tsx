import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
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

type IssueSeverity = 'critical' | 'high' | 'medium' | 'low';
type IssueStatus = 'open' | 'in_remediation' | 'resolved' | 'accepted' | 'closed';

interface VendorIssue {
  id: string;
  vendor_id: string;
  vendor_name?: string;
  issue_title: string;
  severity: IssueSeverity;
  status: IssueStatus;
  due_date?: string;
  owner?: string;
  description?: string;
  created_at?: string;
}

interface IssueForm {
  vendor_id: string;
  issue_title: string;
  severity: IssueSeverity | '';
  status: IssueStatus;
  due_date: string;
  owner: string;
  description: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_FORM: IssueForm = {
  vendor_id: '',
  issue_title: '',
  severity: '',
  status: 'open',
  due_date: '',
  owner: '',
  description: '',
};

const SEVERITY_VARIANT: Record<IssueSeverity, 'danger' | 'warning' | 'info' | 'success'> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'success',
};

const STATUS_VARIANT: Record<IssueStatus, 'danger' | 'warning' | 'info' | 'success' | 'neutral'> = {
  open: 'danger',
  in_remediation: 'warning',
  resolved: 'success',
  accepted: 'info',
  closed: 'neutral',
};

const SEVERITY_OPTIONS = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const STATUS_OPTIONS = [
  { value: 'open', label: 'Open' },
  { value: 'in_remediation', label: 'In Remediation' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'closed', label: 'Closed' },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function VendorIssues() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingIssue, setEditingIssue] = useState<VendorIssue | null>(null);
  const [form, setForm] = useState<IssueForm>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof IssueForm, string>>>({});

  // ── Queries ──

  const { data: issuesData, isLoading } = useQuery<VendorIssue[]>({
    queryKey: ['tprm-issues', severityFilter, statusFilter],
    queryFn: () =>
      api
        .get('/tprm/issues', {
          params: {
            ...(severityFilter ? { severity: severityFilter } : {}),
            ...(statusFilter ? { status: statusFilter } : {}),
          },
        })
        .then(r => r.data?.issues ?? r.data ?? []),
  });

  const { data: vendorsData } = useQuery<{ id: string; vendor_name: string }[]>({
    queryKey: ['tprm-vendors-list'],
    queryFn: () => api.get('/tprm/vendors').then(r => r.data?.vendors ?? r.data ?? []),
  });

  const issues: VendorIssue[] = issuesData ?? [];
  const vendors = vendorsData ?? [];

  const filtered = issues.filter(i => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      i.issue_title.toLowerCase().includes(q) ||
      (i.vendor_name ?? '').toLowerCase().includes(q) ||
      (i.owner ?? '').toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/tprm/issues', data),
    onSuccess: () => {
      toast.success('Issue logged successfully');
      queryClient.invalidateQueries({ queryKey: ['tprm-issues'] });
      closeModal();
    },
    onError: () => toast.error('Failed to log issue'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      api.put(`/tprm/issues/${id}`, data),
    onSuccess: () => {
      toast.success('Issue updated');
      queryClient.invalidateQueries({ queryKey: ['tprm-issues'] });
      closeModal();
    },
    onError: () => toast.error('Failed to update issue'),
  });

  // ── Handlers ──

  function openCreate() {
    setEditingIssue(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
    setShowModal(true);
  }

  function openEdit(issue: VendorIssue) {
    setEditingIssue(issue);
    setForm({
      vendor_id: issue.vendor_id,
      issue_title: issue.issue_title,
      severity: issue.severity,
      status: issue.status,
      due_date: issue.due_date ?? '',
      owner: issue.owner ?? '',
      description: issue.description ?? '',
    });
    setFormErrors({});
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setEditingIssue(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
  }

  function validate(): boolean {
    const errors: Partial<Record<keyof IssueForm, string>> = {};
    if (!form.issue_title.trim()) errors.issue_title = 'Issue title is required';
    if (!form.severity) errors.severity = 'Severity is required';
    if (!form.vendor_id) errors.vendor_id = 'Vendor is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
    if (editingIssue) {
      updateMutation.mutate({ id: editingIssue.id, data: form });
    } else {
      createMutation.mutate(form);
    }
  }

  function setField<K extends keyof IssueForm>(key: K, value: IssueForm[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Columns ──

  const columns = [
    {
      key: 'issue_title',
      header: 'Issue',
      render: (i: VendorIssue) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100 max-w-xs truncate">
            {i.issue_title}
          </div>
          {i.description && (
            <div className="text-xs text-gray-400 truncate max-w-xs">{i.description}</div>
          )}
        </div>
      ),
    },
    {
      key: 'vendor',
      header: 'Vendor',
      render: (i: VendorIssue) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{i.vendor_name || i.vendor_id}</span>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (i: VendorIssue) => (
        <Badge variant={SEVERITY_VARIANT[i.severity]} size="sm">
          {i.severity}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (i: VendorIssue) => (
        <Badge variant={STATUS_VARIANT[i.status]} dot size="sm">
          {i.status.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'due_date',
      header: 'Due Date',
      render: (i: VendorIssue) => {
        if (!i.due_date) return <span className="text-sm text-gray-400">—</span>;
        const isOverdue = new Date(i.due_date) < new Date() && i.status === 'open';
        return (
          <span className={`text-sm ${isOverdue ? 'text-red-600 font-medium' : 'text-gray-600 dark:text-gray-400'}`}>
            {new Date(i.due_date).toLocaleDateString()}
          </span>
        );
      },
    },
    {
      key: 'owner',
      header: 'Owner',
      render: (i: VendorIssue) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{i.owner || '—'}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (i: VendorIssue) => (
        <Button size="sm" variant="ghost" onClick={e => { e.stopPropagation(); openEdit(i); }}>
          Edit
        </Button>
      ),
    },
  ];

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vendor Issues"
        subtitle="Track and remediate issues identified during vendor assessments"
        actions={
          <Button icon={<PlusIcon className="h-4 w-4" />} onClick={openCreate}>
            Log Issue
          </Button>
        }
      />

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by title, vendor, or owner..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value)}
            options={[{ value: '', label: 'All Severities' }, ...SEVERITY_OPTIONS]}
          />
          <Select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            options={[{ value: '', label: 'All Statuses' }, ...STATUS_OPTIONS]}
          />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        onRowClick={i => openEdit(i)}
        emptyMessage="No vendor issues found. Click 'Log Issue' to record a new finding."
      />

      {/* Modal */}
      <Modal
        open={showModal}
        onClose={closeModal}
        title={editingIssue ? 'Edit Issue' : 'Log Vendor Issue'}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={closeModal}>Cancel</Button>
            <Button
              onClick={handleSubmit}
              loading={isSaving}
              variant={!editingIssue ? 'danger' : 'primary'}
              icon={!editingIssue ? <ExclamationTriangleIcon className="h-4 w-4" /> : undefined}
            >
              {editingIssue ? 'Save Changes' : 'Log Issue'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Issue Title"
                required
                value={form.issue_title}
                onChange={e => setField('issue_title', e.target.value)}
                error={formErrors.issue_title}
                placeholder="e.g. Missing data encryption at rest"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Vendor <span className="text-red-500">*</span>
              </label>
              <select
                value={form.vendor_id}
                onChange={e => setField('vendor_id', e.target.value)}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select vendor...</option>
                {vendors.map(v => (
                  <option key={v.id} value={v.id}>{v.vendor_name}</option>
                ))}
              </select>
              {formErrors.vendor_id && (
                <p className="text-xs text-red-500 mt-1">{formErrors.vendor_id}</p>
              )}
            </div>

            <Select
              label="Severity"
              required
              value={form.severity}
              onChange={e => setField('severity', e.target.value as IssueSeverity)}
              options={[{ value: '', label: 'Select severity...' }, ...SEVERITY_OPTIONS]}
              error={formErrors.severity}
            />

            <Select
              label="Status"
              value={form.status}
              onChange={e => setField('status', e.target.value as IssueStatus)}
              options={STATUS_OPTIONS}
            />

            <Input
              label="Owner"
              value={form.owner}
              onChange={e => setField('owner', e.target.value)}
              placeholder="Responsible person"
            />

            <Input
              label="Due Date"
              type="date"
              value={form.due_date}
              onChange={e => setField('due_date', e.target.value)}
            />
          </div>

          <Textarea
            label="Description"
            value={form.description}
            onChange={e => setField('description', e.target.value)}
            rows={3}
            placeholder="Describe the issue, its impact, and remediation steps..."
          />
        </div>
      </Modal>
    </div>
  );
}
