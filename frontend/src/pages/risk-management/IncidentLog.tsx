import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  EyeIcon,
  PencilSquareIcon,
  LinkIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  CheckCircleIcon,
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

// ─── Types ────────────────────────────────────────────────────────────────────

type IncidentSeverity = 'low' | 'medium' | 'high' | 'critical';
type IncidentStatus = 'open' | 'investigating' | 'contained' | 'resolved' | 'closed';

interface Incident {
  id: string;
  incident_id: string;
  title: string;
  description: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  financial_impact: number | null;
  currency: string;
  linked_risk_id: string | null;
  linked_risk_title: string | null;
  reported_by: string;
  reported_at: string;
  occurred_at: string | null;
  resolved_at: string | null;
  category: string;
  root_cause: string;
  corrective_action: string;
}

interface IncidentFormData {
  title: string;
  description: string;
  severity: IncidentSeverity | '';
  status: IncidentStatus;
  financial_impact: string;
  currency: string;
  category: string;
  reported_by: string;
  occurred_at: string;
  root_cause: string;
  corrective_action: string;
}

interface LinkRiskFormData {
  risk_id: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SEVERITY_VARIANT: Record<IncidentSeverity, 'success' | 'warning' | 'danger'> = {
  low: 'success',
  medium: 'warning',
  high: 'danger',
  critical: 'danger',
};

const SEVERITY_LABEL: Record<IncidentSeverity, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
};

const STATUS_VARIANT: Record<IncidentStatus, 'danger' | 'warning' | 'info' | 'success' | 'neutral'> = {
  open: 'danger',
  investigating: 'warning',
  contained: 'info',
  resolved: 'success',
  closed: 'neutral',
};

const STATUS_LABEL: Record<IncidentStatus, string> = {
  open: 'Open',
  investigating: 'Investigating',
  contained: 'Contained',
  resolved: 'Resolved',
  closed: 'Closed',
};

const SEVERITY_OPTIONS: { value: IncidentSeverity; label: string }[] = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
];

const STATUS_OPTIONS: { value: IncidentStatus; label: string }[] = [
  { value: 'open', label: 'Open' },
  { value: 'investigating', label: 'Investigating' },
  { value: 'contained', label: 'Contained' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
];

const CATEGORY_OPTIONS = [
  { value: 'data_breach', label: 'Data Breach' },
  { value: 'system_outage', label: 'System Outage' },
  { value: 'fraud', label: 'Fraud' },
  { value: 'compliance_violation', label: 'Compliance Violation' },
  { value: 'physical_loss', label: 'Physical Loss' },
  { value: 'process_failure', label: 'Process Failure' },
  { value: 'external_event', label: 'External Event' },
  { value: 'other', label: 'Other' },
];

const EMPTY_FORM: IncidentFormData = {
  title: '',
  description: '',
  severity: '',
  status: 'open',
  financial_impact: '',
  currency: 'USD',
  category: '',
  reported_by: '',
  occurred_at: '',
  root_cause: '',
  corrective_action: '',
};

function validateForm(form: IncidentFormData): Partial<Record<keyof IncidentFormData, string>> {
  const errors: Partial<Record<keyof IncidentFormData, string>> = {};
  if (!form.title.trim()) errors.title = 'Title is required';
  if (!form.severity) errors.severity = 'Severity is required';
  if (!form.reported_by.trim()) errors.reported_by = 'Reporter name is required';
  if (!form.description.trim()) errors.description = 'Description is required';
  if (form.financial_impact && isNaN(Number(form.financial_impact))) {
    errors.financial_impact = 'Must be a valid number';
  }
  return errors;
}

function formatCurrency(value: number | null, currency: string): string {
  if (value === null) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

// ─── Component ────────────────────────────────────────────────────────────────

export function IncidentLog() {
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const [showModal, setShowModal] = useState(false);
  const [editingIncident, setEditingIncident] = useState<Incident | null>(null);
  const [form, setForm] = useState<IncidentFormData>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof IncidentFormData, string>>>({});

  const [viewingIncident, setViewingIncident] = useState<Incident | null>(null);
  const [linkingIncident, setLinkingIncident] = useState<Incident | null>(null);
  const [linkForm, setLinkForm] = useState<LinkRiskFormData>({ risk_id: '' });
  const [linkError, setLinkError] = useState('');

  // ── Queries ──

  const { data: incidentsData, isLoading } = useQuery<Incident[]>({
    queryKey: ['incidents', severityFilter, statusFilter, dateFrom, dateTo],
    queryFn: () =>
      riskManagementApi
        .getIncidents({
          severity: severityFilter || undefined,
          status: statusFilter || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        })
        .then(r => r.data?.incidents ?? r.data ?? []),
  });

  const incidents: Incident[] = incidentsData ?? [];

  const filteredIncidents = incidents.filter(inc => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      inc.title.toLowerCase().includes(q) ||
      inc.incident_id?.toLowerCase().includes(q) ||
      inc.reported_by.toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createMutation = useMutation({
    mutationFn: (data: IncidentFormData) =>
      riskManagementApi.reportIncident({
        ...data,
        financial_impact: data.financial_impact ? Number(data.financial_impact) : null,
        severity: data.severity || undefined,
      }),
    onSuccess: () => {
      toast.success('Incident reported successfully');
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      closeModal();
    },
    onError: () => toast.error('Failed to report incident'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: IncidentFormData }) =>
      riskManagementApi.updateIncident(id, {
        ...data,
        financial_impact: data.financial_impact ? Number(data.financial_impact) : null,
      }),
    onSuccess: () => {
      toast.success('Incident updated');
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      closeModal();
    },
    onError: () => toast.error('Failed to update incident'),
  });

  const linkMutation = useMutation({
    mutationFn: ({ id, riskId }: { id: string; riskId: string }) =>
      riskManagementApi.linkIncidentToRisk(id, { risk_id: riskId }),
    onSuccess: () => {
      toast.success('Incident linked to risk');
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      setLinkingIncident(null);
      setLinkForm({ risk_id: '' });
    },
    onError: () => toast.error('Failed to link incident to risk'),
  });

  // ── Handlers ──

  function openCreate() {
    setEditingIncident(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
    setShowModal(true);
  }

  function openEdit(inc: Incident) {
    setEditingIncident(inc);
    setForm({
      title: inc.title,
      description: inc.description,
      severity: inc.severity,
      status: inc.status,
      financial_impact: inc.financial_impact !== null ? String(inc.financial_impact) : '',
      currency: inc.currency || 'USD',
      category: inc.category || '',
      reported_by: inc.reported_by,
      occurred_at: inc.occurred_at ?? '',
      root_cause: inc.root_cause || '',
      corrective_action: inc.corrective_action || '',
    });
    setFormErrors({});
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setEditingIncident(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
  }

  function handleSubmit() {
    const errors = validateForm(form);
    if (Object.keys(errors).length > 0) { setFormErrors(errors); return; }
    if (editingIncident) {
      updateMutation.mutate({ id: editingIncident.id, data: form });
    } else {
      createMutation.mutate(form);
    }
  }

  function setField<K extends keyof IncidentFormData>(key: K, value: IncidentFormData[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  function handleLinkRisk() {
    if (!linkForm.risk_id.trim()) { setLinkError('Risk ID is required'); return; }
    linkMutation.mutate({ id: linkingIncident!.id, riskId: linkForm.risk_id });
  }

  // ── Stats ──

  const openCount = incidents.filter(i => i.status === 'open').length;
  const criticalCount = incidents.filter(i => i.severity === 'critical').length;
  const investigatingCount = incidents.filter(i => i.status === 'investigating').length;
  const resolvedCount = incidents.filter(i => i.status === 'resolved' || i.status === 'closed').length;

  // ── Columns ──

  const columns = [
    {
      key: 'incident_id',
      header: 'Incident ID',
      render: (inc: Incident) => (
        <span className="text-sm font-mono font-medium text-indigo-600 dark:text-indigo-400">
          {inc.incident_id || inc.id}
        </span>
      ),
    },
    {
      key: 'title',
      header: 'Title',
      render: (inc: Incident) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100 max-w-xs truncate">{inc.title}</div>
          {inc.category && (
            <div className="text-xs text-gray-400 capitalize mt-0.5">
              {inc.category.replace(/_/g, ' ')}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (inc: Incident) => (
        <Badge variant={SEVERITY_VARIANT[inc.severity]} dot size="sm">
          {SEVERITY_LABEL[inc.severity]}
        </Badge>
      ),
    },
    {
      key: 'financial_impact',
      header: 'Financial Impact',
      render: (inc: Incident) => (
        <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">
          {formatCurrency(inc.financial_impact, inc.currency)}
        </span>
      ),
    },
    {
      key: 'linked_risk',
      header: 'Linked Risk',
      render: (inc: Incident) => (
        inc.linked_risk_id ? (
          <span className="text-xs font-mono text-indigo-500">{inc.linked_risk_id}</span>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        )
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (inc: Incident) => (
        <Badge variant={STATUS_VARIANT[inc.status]} dot size="sm">
          {STATUS_LABEL[inc.status]}
        </Badge>
      ),
    },
    {
      key: 'reported_at',
      header: 'Reported',
      render: (inc: Incident) => (
        <span className="text-xs text-gray-500">
          {new Date(inc.reported_at).toLocaleDateString('en-GB')}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (inc: Incident) => (
        <div className="flex justify-end gap-1">
          <button
            onClick={e => { e.stopPropagation(); setViewingIncident(inc); }}
            className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors"
            title="View"
          >
            <EyeIcon className="h-4 w-4" />
          </button>
          <button
            onClick={e => { e.stopPropagation(); openEdit(inc); }}
            className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors"
            title="Edit"
          >
            <PencilSquareIcon className="h-4 w-4" />
          </button>
          <button
            onClick={e => { e.stopPropagation(); setLinkingIncident(inc); setLinkForm({ risk_id: '' }); setLinkError(''); }}
            className="p-1.5 rounded-lg text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors"
            title="Link to risk"
          >
            <LinkIcon className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Incidents & Loss Events"
        subtitle="Track operational incidents, losses, and their root causes"
        actions={
          <Button
            icon={<PlusIcon className="h-4 w-4" />}
            onClick={openCreate}
          >
            Report Incident
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard
          title="Open"
          value={openCount}
          icon={ExclamationCircleIcon}
          iconBgColor="stat-icon-red"
          iconColor=""
        />
        <StatCard
          title="Critical"
          value={criticalCount}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-orange"
          iconColor=""
        />
        <StatCard
          title="Investigating"
          value={investigatingCount}
          icon={ClockIcon}
          iconBgColor="stat-icon-yellow"
          iconColor=""
        />
        <StatCard
          title="Resolved / Closed"
          value={resolvedCount}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor=""
        />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3 flex-wrap">
          <div className="flex-1 min-w-48">
            <SearchInput
              placeholder="Search by title, ID, or reporter..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value)}
            options={[{ value: '', label: 'All Severity' }, ...SEVERITY_OPTIONS]}
          />
          <Select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            options={[{ value: '', label: 'All Status' }, ...STATUS_OPTIONS]}
          />
          <div className="flex items-center gap-2">
            <Input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              placeholder="From"
            />
            <span className="text-gray-400 text-sm">to</span>
            <Input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              placeholder="To"
            />
          </div>
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filteredIncidents}
        loading={isLoading}
        onRowClick={inc => setViewingIncident(inc)}
        emptyMessage="No incidents reported. Click 'Report Incident' to log a new event."
      />

      {/* Create / Edit Modal */}
      <Modal
        open={showModal}
        onClose={closeModal}
        title={editingIncident ? 'Edit Incident' : 'Report Incident'}
        subtitle={editingIncident ? `Editing: ${editingIncident.incident_id || editingIncident.id}` : 'Log a new operational incident or loss event'}
        size="xl"
        footer={
          <>
            <Button variant="secondary" onClick={closeModal}>Cancel</Button>
            <Button onClick={handleSubmit} loading={isSaving}>
              {editingIncident ? 'Save Changes' : 'Report Incident'}
            </Button>
          </>
        }
      >
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Incident Title"
                required
                value={form.title}
                onChange={e => setField('title', e.target.value)}
                error={formErrors.title}
                placeholder="Brief descriptive title"
              />
            </div>

            <Select
              label="Severity"
              required
              value={form.severity}
              onChange={e => setField('severity', e.target.value as IncidentSeverity)}
              options={SEVERITY_OPTIONS}
              placeholder="Select severity..."
              error={formErrors.severity}
            />

            <Select
              label="Status"
              value={form.status}
              onChange={e => setField('status', e.target.value as IncidentStatus)}
              options={STATUS_OPTIONS}
            />

            <Select
              label="Category"
              value={form.category}
              onChange={e => setField('category', e.target.value)}
              options={CATEGORY_OPTIONS}
              placeholder="Select category..."
            />

            <Input
              label="Reported By"
              required
              value={form.reported_by}
              onChange={e => setField('reported_by', e.target.value)}
              error={formErrors.reported_by}
              placeholder="Full name of reporter"
            />

            <Input
              label="Date / Time Occurred"
              type="datetime-local"
              value={form.occurred_at}
              onChange={e => setField('occurred_at', e.target.value)}
            />

            <div className="flex gap-2">
              <div className="flex-1">
                <Input
                  label="Financial Impact"
                  type="number"
                  value={form.financial_impact}
                  onChange={e => setField('financial_impact', e.target.value)}
                  error={formErrors.financial_impact}
                  placeholder="0"
                />
              </div>
              <div className="w-24">
                <Select
                  label="Currency"
                  value={form.currency}
                  onChange={e => setField('currency', e.target.value)}
                  options={[
                    { value: 'USD', label: 'USD' },
                    { value: 'EUR', label: 'EUR' },
                    { value: 'GBP', label: 'GBP' },
                    { value: 'JPY', label: 'JPY' },
                  ]}
                />
              </div>
            </div>
          </div>

          <Textarea
            label="Description"
            required
            value={form.description}
            onChange={e => setField('description', e.target.value)}
            error={formErrors.description}
            rows={3}
            placeholder="Detailed description of what happened, who was affected, and what data/systems were involved..."
          />

          <Textarea
            label="Root Cause"
            value={form.root_cause}
            onChange={e => setField('root_cause', e.target.value)}
            rows={2}
            placeholder="Analysis of the underlying cause..."
          />

          <Textarea
            label="Corrective Action"
            value={form.corrective_action}
            onChange={e => setField('corrective_action', e.target.value)}
            rows={2}
            placeholder="Steps taken or planned to prevent recurrence..."
          />
        </div>
      </Modal>

      {/* View Detail Modal */}
      {viewingIncident && (
        <Modal
          open
          onClose={() => setViewingIncident(null)}
          title="Incident Detail"
          subtitle={viewingIncident.incident_id || viewingIncident.id}
          size="lg"
          footer={
            <>
              <Button variant="secondary" onClick={() => setViewingIncident(null)}>Close</Button>
              <Button
                variant="ghost"
                icon={<LinkIcon className="h-4 w-4" />}
                onClick={() => { setLinkingIncident(viewingIncident); setViewingIncident(null); setLinkForm({ risk_id: '' }); setLinkError(''); }}
              >
                Link Risk
              </Button>
              <Button onClick={() => { openEdit(viewingIncident); setViewingIncident(null); }}>
                Edit
              </Button>
            </>
          }
        >
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Severity</p>
                <Badge variant={SEVERITY_VARIANT[viewingIncident.severity]} dot size="sm">
                  {SEVERITY_LABEL[viewingIncident.severity]}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Status</p>
                <Badge variant={STATUS_VARIANT[viewingIncident.status]} dot size="sm">
                  {STATUS_LABEL[viewingIncident.status]}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Financial Impact</p>
                <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                  {formatCurrency(viewingIncident.financial_impact, viewingIncident.currency)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Category</p>
                <p className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                  {viewingIncident.category?.replace(/_/g, ' ') || '—'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Reported By</p>
                <p className="text-sm text-gray-700 dark:text-gray-300">{viewingIncident.reported_by}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Reported At</p>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  {new Date(viewingIncident.reported_at).toLocaleString('en-GB')}
                </p>
              </div>
              {viewingIncident.occurred_at && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Occurred At</p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    {new Date(viewingIncident.occurred_at).toLocaleString('en-GB')}
                  </p>
                </div>
              )}
              {viewingIncident.linked_risk_id && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Linked Risk</p>
                  <p className="text-sm font-mono text-indigo-600 dark:text-indigo-400">
                    {viewingIncident.linked_risk_id}
                  </p>
                  {viewingIncident.linked_risk_title && (
                    <p className="text-xs text-gray-400">{viewingIncident.linked_risk_title}</p>
                  )}
                </div>
              )}
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Description</p>
              <p className="text-sm text-gray-700 dark:text-gray-300">{viewingIncident.description}</p>
            </div>
            {viewingIncident.root_cause && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Root Cause</p>
                <p className="text-sm text-gray-700 dark:text-gray-300">{viewingIncident.root_cause}</p>
              </div>
            )}
            {viewingIncident.corrective_action && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Corrective Action</p>
                <p className="text-sm text-gray-700 dark:text-gray-300">{viewingIncident.corrective_action}</p>
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Link to Risk Modal */}
      <Modal
        open={!!linkingIncident}
        onClose={() => setLinkingIncident(null)}
        title="Link to Risk"
        subtitle={linkingIncident?.title}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setLinkingIncident(null)}>Cancel</Button>
            <Button onClick={handleLinkRisk} loading={linkMutation.isPending}>
              Link
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Enter the Risk ID to associate this incident with a risk in the register.
          </p>
          <Input
            label="Risk ID"
            required
            value={linkForm.risk_id}
            onChange={e => {
              setLinkForm({ risk_id: e.target.value });
              if (linkError) setLinkError('');
            }}
            error={linkError}
            placeholder="e.g. RISK-001"
          />
        </div>
      </Modal>
    </div>
  );
}
