import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ShieldCheckIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  UserIcon,
  LinkIcon,
  ArrowDownTrayIcon,
  EyeIcon,
  XMarkIcon,
  CalendarDaysIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  SearchInput,
  Select,
  Table,
  Modal,
} from '../../components/ui';

// ─── Types ──────────────────────────────────────────────────────────────────

type ControlStatus = 'active' | 'expired' | 'pending_review';
type ControlType =
  | 'Manual Review'
  | 'Automated Monitor'
  | 'Approval Workflow'
  | 'Detective Control'
  | 'Preventive Control'
  | 'System Configuration';

interface MitigatingControl {
  id: string;
  name: string;
  description: string;
  controlType: ControlType;
  owner: string;
  monitor: string;
  linkedRisksCount: number;
  linkedUsersCount: number;
  status: ControlStatus;
  validFrom: string;
  validTo: string;
  reviewFrequency: string;
  lastReviewDate: string;
  nextReviewDate: string;
  riskIds: string[];
  userIds: string[];
  effectiveness: 'high' | 'medium' | 'low' | 'not_rated';
  notes: string;
}

interface ControlFormValues {
  name: string;
  description: string;
  controlType: ControlType;
  owner: string;
  monitor: string;
  validFrom: string;
  validTo: string;
  reviewFrequency: string;
  notes: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const TODAY = new Date('2026-08-21');

function daysUntilExpiry(validTo: string): number {
  const expiry = new Date(validTo);
  return Math.ceil((expiry.getTime() - TODAY.getTime()) / (1000 * 60 * 60 * 24));
}

function isExpiringSoon(validTo: string): boolean {
  const days = daysUntilExpiry(validTo);
  return days >= 0 && days <= 30;
}

const statusVariant: Record<ControlStatus, 'success' | 'danger' | 'warning'> = {
  active: 'success',
  expired: 'danger',
  pending_review: 'warning',
};

const statusLabel: Record<ControlStatus, string> = {
  active: 'Active',
  expired: 'Expired',
  pending_review: 'Pending Review',
};

const effectivenessVariant: Record<string, 'success' | 'info' | 'warning' | 'neutral'> = {
  high: 'success',
  medium: 'info',
  low: 'warning',
  not_rated: 'neutral',
};

const effectivenessLabel: Record<string, string> = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  not_rated: 'Not Rated',
};

const CONTROL_TYPES: ControlType[] = [
  'Manual Review',
  'Automated Monitor',
  'Approval Workflow',
  'Detective Control',
  'Preventive Control',
  'System Configuration',
];

const REVIEW_FREQUENCIES = ['Monthly', 'Quarterly', 'Semi-Annual', 'Annual'];

const EMPTY_FORM: ControlFormValues = {
  name: '',
  description: '',
  controlType: 'Manual Review',
  owner: '',
  monitor: '',
  validFrom: '',
  validTo: '',
  reviewFrequency: 'Quarterly',
  notes: '',
};

type Tab = 'all' | 'active' | 'expiring' | 'pending_review';

// ─── Component ───────────────────────────────────────────────────────────────

export function MitigationControls() {
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<Tab>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [effectivenessFilter, setEffectivenessFilter] = useState('all');

  const [selectedControl, setSelectedControl] = useState<MitigatingControl | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showFormModal, setShowFormModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [editingControl, setEditingControl] = useState<MitigatingControl | null>(null);
  const [formValues, setFormValues] = useState<ControlFormValues>(EMPTY_FORM);
  const [controlToDelete, setControlToDelete] = useState<MitigatingControl | null>(null);

  // ── Data Fetching ─────────────────────────────────────────────────────────

  const { data: controlsData, isError: _isError } = useQuery<MitigatingControl[]>({
    queryKey: ['mitigation-controls'],
    queryFn: () =>
      api
        .get('/mitigation/controls')
        .then((res) => res.data?.controls || res.data || []),
    retry: 1,
  });

  const controls: MitigatingControl[] = controlsData ?? [];

  // ── Mutations ─────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (values: ControlFormValues) =>
      api.post('/mitigation/controls', values).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mitigation-controls'] });
      toast.success('Mitigating control created successfully.');
      setShowFormModal(false);
      setFormValues(EMPTY_FORM);
    },
    onError: () => toast.error('Failed to create control. Please try again.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: ControlFormValues }) =>
      api.put(`/mitigation/controls/${id}`, values).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mitigation-controls'] });
      toast.success('Mitigating control updated successfully.');
      setShowFormModal(false);
      setEditingControl(null);
      setFormValues(EMPTY_FORM);
    },
    onError: () => toast.error('Failed to update control. Please try again.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/mitigation/controls/${id}`).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mitigation-controls'] });
      toast.success('Mitigating control deleted.');
      setShowDeleteConfirm(false);
      setControlToDelete(null);
    },
    onError: () => toast.error('Failed to delete control. Please try again.'),
  });

  const certifyMutation = useMutation({
    mutationFn: (id: string) =>
      api.post(`/mitigation/controls/${id}/certify`).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mitigation-controls'] });
      toast.success('Control certified and review date updated.');
    },
    onError: () => toast.error('Failed to certify control. Please try again.'),
  });

  // ── Stats ─────────────────────────────────────────────────────────────────

  const totalControls = controls.length;
  const activeControls = controls.filter((c) => c.status === 'active').length;
  const expiringSoonCount = controls.filter(
    (c) => c.status === 'active' && isExpiringSoon(c.validTo)
  ).length;
  const pendingReviewCount = controls.filter((c) => c.status === 'pending_review').length;

  // ── Filtering ─────────────────────────────────────────────────────────────

  const tabFiltered = controls.filter((c) => {
    if (activeTab === 'active') return c.status === 'active' && !isExpiringSoon(c.validTo);
    if (activeTab === 'expiring') return c.status === 'active' && isExpiringSoon(c.validTo);
    if (activeTab === 'pending_review') return c.status === 'pending_review';
    return true;
  });

  const filtered = tabFiltered.filter((c) => {
    const term = searchTerm.toLowerCase();
    const matchesSearch =
      c.id.toLowerCase().includes(term) ||
      c.name.toLowerCase().includes(term) ||
      c.owner.toLowerCase().includes(term) ||
      c.description.toLowerCase().includes(term);
    const matchesType = typeFilter === 'all' || c.controlType === typeFilter;
    const matchesEffectiveness =
      effectivenessFilter === 'all' || c.effectiveness === effectivenessFilter;
    return matchesSearch && matchesType && matchesEffectiveness;
  });

  // ── Handlers ─────────────────────────────────────────────────────────────

  function openCreate() {
    setEditingControl(null);
    setFormValues(EMPTY_FORM);
    setShowFormModal(true);
  }

  function openEdit(control: MitigatingControl) {
    setEditingControl(control);
    setFormValues({
      name: control.name,
      description: control.description,
      controlType: control.controlType,
      owner: control.owner,
      monitor: control.monitor,
      validFrom: control.validFrom,
      validTo: control.validTo,
      reviewFrequency: control.reviewFrequency,
      notes: control.notes,
    });
    setShowFormModal(true);
  }

  function openDetail(control: MitigatingControl) {
    setSelectedControl(control);
    setShowDetailModal(true);
  }

  function openDeleteConfirm(control: MitigatingControl) {
    setControlToDelete(control);
    setShowDeleteConfirm(true);
  }

  function handleFormSubmit() {
    if (editingControl) {
      updateMutation.mutate({ id: editingControl.id, values: formValues });
    } else {
      createMutation.mutate(formValues);
    }
  }

  function handleExport() {
    const headers = [
      'ID', 'Name', 'Control Type', 'Owner', 'Monitor',
      'Status', 'Valid From', 'Valid To', 'Linked Risks', 'Linked Users',
      'Effectiveness', 'Review Frequency', 'Next Review',
    ];
    const rows = filtered.map((c) => [
      c.id, c.name, c.controlType, c.owner, c.monitor,
      c.status, c.validFrom, c.validTo, c.linkedRisksCount, c.linkedUsersCount,
      c.effectiveness, c.reviewFrequency, c.nextReviewDate,
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${cell}"`).join(','))
      .join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `mitigating_controls_${TODAY.toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
    toast.success(`Exported ${filtered.length} controls to CSV.`);
  }

  // ── Table Columns ─────────────────────────────────────────────────────────

  const columns = [
    {
      key: 'control',
      header: 'Control',
      render: (c: MitigatingControl) => (
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex-shrink-0">
            <ShieldCheckIcon className="h-5 w-5 text-primary-500" />
          </div>
          <div>
            <button
              onClick={() => openDetail(c)}
              className="text-sm font-medium text-primary-600 hover:text-primary-800 transition-colors text-left"
            >
              {c.name}
            </button>
            <div className="text-xs text-gray-400 mt-0.5">{c.id}</div>
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (c: MitigatingControl) => (
        <span className="text-sm text-gray-600">{c.controlType}</span>
      ),
    },
    {
      key: 'ownership',
      header: 'Owner / Monitor',
      render: (c: MitigatingControl) => (
        <div>
          <div className="flex items-center gap-1 text-sm text-gray-900">
            <UserIcon className="h-3.5 w-3.5 text-gray-400" />
            {c.owner}
          </div>
          <div className="text-xs text-gray-400 mt-0.5">{c.monitor}</div>
        </div>
      ),
    },
    {
      key: 'linked',
      header: 'Linked',
      render: (c: MitigatingControl) => (
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1 text-xs text-gray-600">
            <LinkIcon className="h-3.5 w-3.5 text-gray-400" />
            <span>{c.linkedRisksCount} risks</span>
          </div>
          <div className="flex items-center gap-1 text-xs text-gray-600">
            <UserGroupIcon className="h-3.5 w-3.5 text-gray-400" />
            <span>{c.linkedUsersCount} users</span>
          </div>
        </div>
      ),
    },
    {
      key: 'effectiveness',
      header: 'Effectiveness',
      render: (c: MitigatingControl) => (
        <Badge variant={effectivenessVariant[c.effectiveness]} size="sm">
          {effectivenessLabel[c.effectiveness]}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (c: MitigatingControl) => (
        <div className="flex flex-col gap-1">
          <Badge variant={statusVariant[c.status]} size="sm">
            {statusLabel[c.status]}
          </Badge>
          {c.status === 'active' && isExpiringSoon(c.validTo) && (
            <span className="inline-flex items-center gap-0.5 text-xs text-amber-600 font-medium">
              <ExclamationTriangleIcon className="h-3.5 w-3.5" />
              Expires in {daysUntilExpiry(c.validTo)}d
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'validity',
      header: 'Valid To',
      render: (c: MitigatingControl) => (
        <div className="flex items-center gap-1 text-sm text-gray-600">
          <CalendarDaysIcon className="h-3.5 w-3.5 text-gray-400" />
          {c.validTo}
        </div>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (c: MitigatingControl) => (
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={() => openDetail(c)}
            className="p-1 text-gray-400 hover:text-primary-600 transition-colors"
            title="View details"
          >
            <EyeIcon className="h-4 w-4" />
          </button>
          {c.status === 'pending_review' && (
            <button
              onClick={() => certifyMutation.mutate(c.id)}
              className="p-1 text-gray-400 hover:text-green-600 transition-colors"
              title="Certify / complete review"
            >
              <CheckCircleIcon className="h-4 w-4" />
            </button>
          )}
          <button
            onClick={() => openEdit(c)}
            className="p-1 text-gray-400 hover:text-blue-600 transition-colors"
            title="Edit"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => openDeleteConfirm(c)}
            className="p-1 text-gray-400 hover:text-red-600 transition-colors"
            title="Delete"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: 'all', label: 'All Controls', count: totalControls },
    { id: 'active', label: 'Active', count: activeControls },
    { id: 'expiring', label: 'Expiring Soon', count: expiringSoonCount },
    { id: 'pending_review', label: 'Pending Review', count: pendingReviewCount },
  ];

  const isMutating = createMutation.isPending || updateMutation.isPending;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Mitigating Controls"
        subtitle="Manage compensating controls assigned to SoD conflicts that cannot be remediated"
        actions={
          <>
            <Button
              variant="secondary"
              size="sm"
              icon={<ArrowDownTrayIcon className="h-4 w-4" />}
              onClick={handleExport}
            >
              Export
            </Button>
            <Button
              size="sm"
              icon={<PlusIcon className="h-4 w-4" />}
              onClick={openCreate}
            >
              New Control
            </Button>
          </>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <StatCard
          title="Total Controls"
          value={totalControls}
          icon={ShieldCheckIcon}
          iconBgColor="stat-icon-blue"
          iconColor=""
        />
        <StatCard
          title="Active"
          value={activeControls}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor=""
        />
        <StatCard
          title="Expiring in 30 Days"
          value={expiringSoonCount}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-orange"
          iconColor=""
        />
        <StatCard
          title="Pending Review"
          value={pendingReviewCount}
          icon={ClockIcon}
          iconBgColor="stat-icon-yellow"
          iconColor=""
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200/60">
        <nav className="-mb-px flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
              <span
                className={`inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-medium ${
                  activeTab === tab.id
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </nav>
      </div>

      {/* Expiring Banner */}
      {activeTab === 'expiring' && expiringSoonCount > 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <ExclamationTriangleIcon className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-800">
              {expiringSoonCount} control{expiringSoonCount > 1 ? 's' : ''} expire within 30 days
            </p>
            <p className="text-xs text-amber-700 mt-0.5">
              Review and renew these controls before expiry to avoid unmitigated SoD violations.
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col lg:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by name, ID, owner, or description..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClear={() => setSearchTerm('')}
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Types' },
                ...CONTROL_TYPES.map((t) => ({ value: t, label: t })),
              ]}
            />
            <Select
              value={effectivenessFilter}
              onChange={(e) => setEffectivenessFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Effectiveness' },
                { value: 'high', label: 'High' },
                { value: 'medium', label: 'Medium' },
                { value: 'low', label: 'Low' },
                { value: 'not_rated', label: 'Not Rated' },
              ]}
            />
          </div>
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        emptyMessage="No mitigating controls found matching your criteria."
      />

      {/* Detail Modal */}
      <Modal
        open={showDetailModal}
        onClose={() => { setShowDetailModal(false); setSelectedControl(null); }}
        title={selectedControl?.name ?? ''}
        subtitle={selectedControl?.id}
        size="lg"
        footer={
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => { setShowDetailModal(false); setSelectedControl(null); }}
            >
              Close
            </Button>
            {selectedControl && (
              <>
                {selectedControl.status === 'pending_review' && (
                  <Button
                    variant="success"
                    size="sm"
                    icon={<CheckCircleIcon className="h-4 w-4" />}
                    onClick={() => {
                      certifyMutation.mutate(selectedControl.id);
                      setShowDetailModal(false);
                    }}
                  >
                    Certify Control
                  </Button>
                )}
                <Button
                  size="sm"
                  icon={<PencilIcon className="h-4 w-4" />}
                  onClick={() => {
                    setShowDetailModal(false);
                    openEdit(selectedControl);
                  }}
                >
                  Edit
                </Button>
              </>
            )}
          </>
        }
      >
        {selectedControl && (
          <div className="space-y-6">
            {/* Description */}
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Description</p>
              <p className="text-sm text-gray-700 leading-relaxed">{selectedControl.description}</p>
            </div>

            {/* Key Fields Grid */}
            <div className="grid grid-cols-2 gap-x-8 gap-y-4">
              <div>
                <p className="text-xs text-gray-500">Control Type</p>
                <p className="text-sm font-medium text-gray-900 mt-0.5">{selectedControl.controlType}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Effectiveness</p>
                <div className="mt-0.5">
                  <Badge variant={effectivenessVariant[selectedControl.effectiveness]} size="sm">
                    {effectivenessLabel[selectedControl.effectiveness]}
                  </Badge>
                </div>
              </div>
              <div>
                <p className="text-xs text-gray-500">Owner</p>
                <p className="text-sm font-medium text-gray-900 mt-0.5">{selectedControl.owner}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Monitor</p>
                <p className="text-sm font-medium text-gray-900 mt-0.5">{selectedControl.monitor}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Valid From</p>
                <p className="text-sm font-medium text-gray-900 mt-0.5">{selectedControl.validFrom}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Valid To</p>
                <p className={`text-sm font-medium mt-0.5 ${isExpiringSoon(selectedControl.validTo) ? 'text-amber-600' : 'text-gray-900'}`}>
                  {selectedControl.validTo}
                  {isExpiringSoon(selectedControl.validTo) && (
                    <span className="ml-1 text-xs">
                      ({daysUntilExpiry(selectedControl.validTo)} days)
                    </span>
                  )}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Review Frequency</p>
                <p className="text-sm font-medium text-gray-900 mt-0.5">{selectedControl.reviewFrequency}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Next Review</p>
                <p className="text-sm font-medium text-gray-900 mt-0.5">{selectedControl.nextReviewDate}</p>
              </div>
            </div>

            {/* Linked Risks / Users */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg bg-blue-50 border border-blue-100 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <LinkIcon className="h-4 w-4 text-blue-600" />
                  <p className="text-xs font-semibold text-blue-800 uppercase tracking-wide">Linked Risks</p>
                </div>
                <p className="text-2xl font-bold text-blue-700">{selectedControl.linkedRisksCount}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {selectedControl.riskIds.slice(0, 5).map((id) => (
                    <span key={id} className="inline-block text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                      {id}
                    </span>
                  ))}
                  {selectedControl.riskIds.length > 5 && (
                    <span className="text-xs text-blue-500">+{selectedControl.riskIds.length - 5} more</span>
                  )}
                </div>
              </div>
              <div className="rounded-lg bg-purple-50 border border-purple-100 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <UserGroupIcon className="h-4 w-4 text-purple-600" />
                  <p className="text-xs font-semibold text-purple-800 uppercase tracking-wide">Linked Users</p>
                </div>
                <p className="text-2xl font-bold text-purple-700">{selectedControl.linkedUsersCount}</p>
                <p className="mt-2 text-xs text-purple-600">
                  {selectedControl.userIds.length} user ID{selectedControl.userIds.length !== 1 ? 's' : ''} assigned
                </p>
              </div>
            </div>

            {/* Notes */}
            {selectedControl.notes && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Notes</p>
                <p className="text-sm text-gray-600 leading-relaxed">{selectedControl.notes}</p>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Create / Edit Modal */}
      <Modal
        open={showFormModal}
        onClose={() => { setShowFormModal(false); setEditingControl(null); setFormValues(EMPTY_FORM); }}
        title={editingControl ? `Edit Control — ${editingControl.id}` : 'New Mitigating Control'}
        subtitle={
          editingControl
            ? 'Update the control details below.'
            : 'Define a new compensating control to mitigate an unresolvable SoD conflict.'
        }
        size="lg"
        footer={
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => { setShowFormModal(false); setEditingControl(null); setFormValues(EMPTY_FORM); }}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              loading={isMutating}
              onClick={handleFormSubmit}
              disabled={!formValues.name.trim() || !formValues.owner.trim() || !formValues.validFrom || !formValues.validTo}
            >
              {editingControl ? 'Save Changes' : 'Create Control'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {/* Name */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Control Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formValues.name}
              onChange={(e) => setFormValues((v) => ({ ...v, name: e.target.value }))}
              placeholder="e.g. Independent Payment Review"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={formValues.description}
              onChange={(e) => setFormValues((v) => ({ ...v, description: e.target.value }))}
              placeholder="Describe what this control does and which SoD conflict it mitigates..."
              rows={3}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition resize-none"
            />
          </div>

          {/* Control Type + Review Frequency */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Control Type <span className="text-red-500">*</span>
              </label>
              <select
                value={formValues.controlType}
                onChange={(e) => setFormValues((v) => ({ ...v, controlType: e.target.value as ControlType }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              >
                {CONTROL_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Review Frequency</label>
              <select
                value={formValues.reviewFrequency}
                onChange={(e) => setFormValues((v) => ({ ...v, reviewFrequency: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              >
                {REVIEW_FREQUENCIES.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Owner + Monitor */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Owner <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formValues.owner}
                onChange={(e) => setFormValues((v) => ({ ...v, owner: e.target.value }))}
                placeholder="Full name"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Monitor</label>
              <input
                type="text"
                value={formValues.monitor}
                onChange={(e) => setFormValues((v) => ({ ...v, monitor: e.target.value }))}
                placeholder="Full name"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              />
            </div>
          </div>

          {/* Valid From / To */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Valid From <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                value={formValues.validFrom}
                onChange={(e) => setFormValues((v) => ({ ...v, validFrom: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Valid To <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                value={formValues.validTo}
                onChange={(e) => setFormValues((v) => ({ ...v, validTo: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              value={formValues.notes}
              onChange={(e) => setFormValues((v) => ({ ...v, notes: e.target.value }))}
              placeholder="Evidence location, exceptions process, escalation path..."
              rows={2}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition resize-none"
            />
          </div>

          {/* Validation hint */}
          {formValues.validFrom && formValues.validTo && formValues.validTo <= formValues.validFrom && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
              <XMarkIcon className="h-4 w-4 text-red-500 flex-shrink-0" />
              <p className="text-xs text-red-700">Valid To date must be after Valid From date.</p>
            </div>
          )}
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        open={showDeleteConfirm}
        onClose={() => { setShowDeleteConfirm(false); setControlToDelete(null); }}
        title="Delete Mitigating Control"
        size="sm"
        footer={
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => { setShowDeleteConfirm(false); setControlToDelete(null); }}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={deleteMutation.isPending}
              onClick={() => controlToDelete && deleteMutation.mutate(controlToDelete.id)}
            >
              Delete Control
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <div className="flex items-start gap-3 rounded-lg bg-red-50 border border-red-200 px-4 py-3">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">This action cannot be undone.</p>
              <p className="text-xs text-red-700 mt-0.5">
                Deleting this control will leave associated SoD violations unmitigated.
              </p>
            </div>
          </div>
          {controlToDelete && (
            <p className="text-sm text-gray-600">
              Are you sure you want to delete{' '}
              <span className="font-semibold text-gray-900">{controlToDelete.name}</span>{' '}
              ({controlToDelete.id})?
            </p>
          )}
        </div>
      </Modal>
    </div>
  );
}
