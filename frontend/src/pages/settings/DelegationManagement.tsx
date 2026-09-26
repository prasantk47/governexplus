import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  UserIcon,
  ArrowRightIcon,
  CalendarDaysIcon,
  PlusIcon,
  PencilIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  FunnelIcon,
  InformationCircleIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  SearchInput,
  Select,
  Table,
  Modal,
  Input,
  Textarea,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type DelegationScope =
  | 'ALL'
  | 'ACCESS_REQUESTS'
  | 'CERTIFICATIONS'
  | 'FIREFIGHTER'
  | 'RISK_EXCEPTIONS'
  | 'SOD_VIOLATIONS';

type DelegationStatus = 'active' | 'upcoming' | 'expired' | 'revoked';

interface Delegation {
  id: string;
  delegator_id: string;
  delegator_name: string;
  delegator_email: string;
  delegator_department: string;
  delegate_id: string;
  delegate_name: string;
  delegate_email: string;
  delegate_department: string;
  start_date: string;
  end_date: string;
  scope: DelegationScope;
  reason: string;
  status: DelegationStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
  items_handled: number;
}

interface DelegationListResponse {
  items: Delegation[];
  total: number;
}

interface DelegationStats {
  active: number;
  upcoming: number;
  expired_this_month: number;
  users_without_delegate: number;
}

interface DelegationForm {
  delegator_id: string;
  delegator_name: string;
  delegate_id: string;
  delegate_name: string;
  start_date: string;
  end_date: string;
  scope: DelegationScope;
  reason: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SCOPE_OPTIONS: { value: DelegationScope | ''; label: string }[] = [
  { value: '', label: 'All Scopes' },
  { value: 'ALL', label: 'All Approvals' },
  { value: 'ACCESS_REQUESTS', label: 'Access Requests' },
  { value: 'CERTIFICATIONS', label: 'Certifications' },
  { value: 'FIREFIGHTER', label: 'Privileged Access Requests' },
  { value: 'RISK_EXCEPTIONS', label: 'Risk Exceptions' },
  { value: 'SOD_VIOLATIONS', label: 'SoD Violations' },
];

const SCOPE_FORM_OPTIONS = SCOPE_OPTIONS.filter((o) => o.value !== '');

const SCOPE_LABELS: Record<DelegationScope, string> = {
  ALL: 'All Approvals',
  ACCESS_REQUESTS: 'Access Requests',
  CERTIFICATIONS: 'Certifications',
  FIREFIGHTER: 'Privileged Access Requests',
  RISK_EXCEPTIONS: 'Risk Exceptions',
  SOD_VIOLATIONS: 'SoD Violations',
};

const SCOPE_BADGE_VARIANT: Record<DelegationScope, 'info' | 'success' | 'warning' | 'danger' | 'neutral' | 'default'> = {
  ALL: 'info',
  ACCESS_REQUESTS: 'success',
  CERTIFICATIONS: 'warning',
  FIREFIGHTER: 'danger',
  RISK_EXCEPTIONS: 'warning',
  SOD_VIOLATIONS: 'danger',
};

const STATUS_TABS = [
  { key: 'active', label: 'Active' },
  { key: 'upcoming', label: 'Upcoming' },
  { key: 'expired', label: 'Expired' },
  { key: 'all', label: 'All' },
] as const;

type TabKey = (typeof STATUS_TABS)[number]['key'];

const EMPTY_FORM: DelegationForm = {
  delegator_id: '',
  delegator_name: '',
  delegate_id: '',
  delegate_name: '',
  start_date: '',
  end_date: '',
  scope: 'ALL',
  reason: '',
};

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const delegationApi = {
  list: (params?: Record<string, string | undefined>) =>
    api.get<DelegationListResponse>('/delegations', { params }),
  getStats: () => api.get<DelegationStats>('/delegations/stats'),
  create: (data: Omit<DelegationForm, 'delegator_name' | 'delegate_name'>) =>
    api.post<Delegation>('/delegations', data),
  update: (id: string, data: Partial<DelegationForm>) =>
    api.put<Delegation>(`/delegations/${id}`, data),
  revoke: (id: string, reason: string) =>
    api.post<Delegation>(`/delegations/${id}/revoke`, { reason }),
  extend: (id: string, new_end_date: string, reason: string) =>
    api.post<Delegation>(`/delegations/${id}/extend`, { new_end_date, reason }),
};

// ---------------------------------------------------------------------------
// Helper components
// ---------------------------------------------------------------------------

function StatusBadgeLocal({ status }: { status: DelegationStatus }) {
  const map: Record<DelegationStatus, { variant: 'success' | 'info' | 'neutral' | 'danger'; label: string }> = {
    active: { variant: 'success', label: 'Active' },
    upcoming: { variant: 'info', label: 'Upcoming' },
    expired: { variant: 'neutral', label: 'Expired' },
    revoked: { variant: 'danger', label: 'Revoked' },
  };
  const { variant, label } = map[status] ?? { variant: 'neutral', label: status };
  return (
    <Badge variant={variant} dot>
      {label}
    </Badge>
  );
}

function DelegationArrow({
  delegator,
  delegate,
}: {
  delegator: { name: string; department: string };
  delegate: { name: string; department: string };
}) {
  return (
    <div className="flex items-center gap-2 min-w-0">
      <div className="flex flex-col min-w-0">
        <span className="text-sm font-medium text-gray-900 truncate">{delegator.name}</span>
        <span className="text-xs text-gray-400 truncate">{delegator.department}</span>
      </div>
      <ArrowRightIcon className="h-4 w-4 flex-shrink-0 text-gray-400" />
      <div className="flex flex-col min-w-0">
        <span className="text-sm font-medium text-gray-900 truncate">{delegate.name}</span>
        <span className="text-xs text-gray-400 truncate">{delegate.department}</span>
      </div>
    </div>
  );
}

function DateRange({ start, end }: { start: string; end: string }) {
  const s = new Date(start);
  const e = new Date(end);
  const daysLeft = Math.ceil((e.getTime() - Date.now()) / 86_400_000);
  const expired = daysLeft < 0;
  const daysLeftLabel = expired
    ? `Ended ${Math.abs(daysLeft)}d ago`
    : `${daysLeft}d remaining`;

  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-sm text-gray-700">
        {s.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
        {' — '}
        {e.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
      </span>
      <span className={`text-xs ${expired ? 'text-gray-400' : daysLeft <= 3 ? 'text-amber-600 font-medium' : 'text-gray-400'}`}>
        {daysLeftLabel}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function DelegationManagement() {
  const queryClient = useQueryClient();

  // Tab & filter state
  const [activeTab, setActiveTab] = useState<TabKey>('active');
  const [searchTerm, setSearchTerm] = useState('');
  const [scopeFilter, setScopeFilter] = useState<DelegationScope | ''>('');

  // Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showExtendModal, setShowExtendModal] = useState(false);
  const [showRevokeModal, setShowRevokeModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedDelegation, setSelectedDelegation] = useState<Delegation | null>(null);

  // Form state
  const [form, setForm] = useState<DelegationForm>(EMPTY_FORM);
  const [extendDate, setExtendDate] = useState('');
  const [extendReason, setExtendReason] = useState('');
  const [revokeReason, setRevokeReason] = useState('');

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------

  const {
    data: delegationsData,
    isLoading,
    error: _listError,
  } = useQuery<DelegationListResponse>({
    queryKey: ['delegations', { activeTab, searchTerm, scopeFilter }],
    queryFn: async () => {
      const params: Record<string, string | undefined> = {
        status: activeTab === 'all' ? undefined : activeTab,
        search: searchTerm || undefined,
        scope: scopeFilter || undefined,
      };
      const res = await delegationApi.list(params);
      return res.data;
    },
    staleTime: 30_000,
  });

  const { data: statsData } = useQuery<DelegationStats>({
    queryKey: ['delegation-stats'],
    queryFn: async () => {
      const res = await delegationApi.getStats();
      return res.data;
    },
    staleTime: 60_000,
  });

  const delegations = delegationsData?.items ?? [];

  // ---------------------------------------------------------------------------
  // Mutations
  // ---------------------------------------------------------------------------

  const createMutation = useMutation({
    mutationFn: (data: DelegationForm) =>
      delegationApi.create({
        delegator_id: data.delegator_id,
        delegate_id: data.delegate_id,
        start_date: data.start_date,
        end_date: data.end_date,
        scope: data.scope,
        reason: data.reason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delegations'] });
      queryClient.invalidateQueries({ queryKey: ['delegation-stats'] });
      setShowCreateModal(false);
      setForm(EMPTY_FORM);
      toast.success('Delegation created successfully');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to create delegation');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<DelegationForm> }) =>
      delegationApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delegations'] });
      setShowEditModal(false);
      setSelectedDelegation(null);
      toast.success('Delegation updated');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to update delegation');
    },
  });

  const extendMutation = useMutation({
    mutationFn: ({ id, date, reason }: { id: string; date: string; reason: string }) =>
      delegationApi.extend(id, date, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delegations'] });
      queryClient.invalidateQueries({ queryKey: ['delegation-stats'] });
      setShowExtendModal(false);
      setSelectedDelegation(null);
      setExtendDate('');
      setExtendReason('');
      toast.success('Delegation extended');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to extend delegation');
    },
  });

  const revokeMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      delegationApi.revoke(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delegations'] });
      queryClient.invalidateQueries({ queryKey: ['delegation-stats'] });
      setShowRevokeModal(false);
      setSelectedDelegation(null);
      setRevokeReason('');
      toast.success('Delegation revoked');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to revoke delegation');
    },
  });

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const openEdit = (d: Delegation) => {
    setSelectedDelegation(d);
    setForm({
      delegator_id: d.delegator_id,
      delegator_name: d.delegator_name,
      delegate_id: d.delegate_id,
      delegate_name: d.delegate_name,
      start_date: d.start_date,
      end_date: d.end_date,
      scope: d.scope,
      reason: d.reason,
    });
    setShowEditModal(true);
  };

  const openExtend = (d: Delegation) => {
    setSelectedDelegation(d);
    setExtendDate(d.end_date);
    setExtendReason('');
    setShowExtendModal(true);
  };

  const openRevoke = (d: Delegation) => {
    setSelectedDelegation(d);
    setRevokeReason('');
    setShowRevokeModal(true);
  };

  const openDetail = (d: Delegation) => {
    setSelectedDelegation(d);
    setShowDetailModal(true);
  };

  const handleCreate = () => {
    if (!form.delegator_id || !form.delegate_id || !form.start_date || !form.end_date) return;
    createMutation.mutate(form);
  };

  const handleUpdate = () => {
    if (!selectedDelegation) return;
    updateMutation.mutate({
      id: selectedDelegation.id,
      data: {
        scope: form.scope,
        end_date: form.end_date,
        reason: form.reason,
      },
    });
  };

  const handleExtend = () => {
    if (!selectedDelegation || !extendDate) return;
    extendMutation.mutate({ id: selectedDelegation.id, date: extendDate, reason: extendReason });
  };

  const handleRevoke = () => {
    if (!selectedDelegation) return;
    revokeMutation.mutate({ id: selectedDelegation.id, reason: revokeReason });
  };

  // ---------------------------------------------------------------------------
  // Tab counts (computed from live data for the badges)
  // ---------------------------------------------------------------------------

  const tabCounts = useMemo(() => {
    return {
      active: delegations.filter((d) => d.status === 'active').length,
      upcoming: delegations.filter((d) => d.status === 'upcoming').length,
      expired: delegations.filter((d) => d.status === 'expired' || d.status === 'revoked').length,
      all: delegations.length,
    };
  }, [delegations]);

  // ---------------------------------------------------------------------------
  // Table columns
  // ---------------------------------------------------------------------------

  const columns = [
    {
      key: 'delegation',
      header: 'Delegation',
      render: (row: Delegation) => (
        <DelegationArrow
          delegator={{ name: row.delegator_name, department: row.delegator_department }}
          delegate={{ name: row.delegate_name, department: row.delegate_department }}
        />
      ),
    },
    {
      key: 'scope',
      header: 'Scope',
      render: (row: Delegation) => (
        <Badge variant={SCOPE_BADGE_VARIANT[row.scope]}>
          {SCOPE_LABELS[row.scope]}
        </Badge>
      ),
    },
    {
      key: 'period',
      header: 'Period',
      render: (row: Delegation) => (
        <DateRange start={row.start_date} end={row.end_date} />
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row: Delegation) => <StatusBadgeLocal status={row.status} />,
    },
    {
      key: 'items_handled',
      header: 'Items Handled',
      render: (row: Delegation) => (
        <span className="text-sm font-medium text-gray-700">{row.items_handled}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row: Delegation) => (
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          {(row.status === 'active' || row.status === 'upcoming') && (
            <>
              <button
                onClick={() => openEdit(row)}
                className="p-1.5 rounded-lg hover:bg-gray-100/60 text-gray-400 hover:text-gray-700 transition-colors"
                title="Edit delegation"
              >
                <PencilIcon className="h-4 w-4" />
              </button>
              <button
                onClick={() => openExtend(row)}
                className="p-1.5 rounded-lg hover:bg-gray-100/60 text-gray-400 hover:text-blue-600 transition-colors"
                title="Extend delegation"
              >
                <CalendarDaysIcon className="h-4 w-4" />
              </button>
              <button
                onClick={() => openRevoke(row)}
                className="p-1.5 rounded-lg hover:bg-gray-100/60 text-gray-400 hover:text-red-500 transition-colors"
                title="Revoke delegation"
              >
                <XCircleIcon className="h-4 w-4" />
              </button>
            </>
          )}
          {(row.status === 'expired' || row.status === 'revoked') && (
            <span className="text-xs text-gray-400 px-1">No actions</span>
          )}
        </div>
      ),
    },
  ];

  // ---------------------------------------------------------------------------
  // Expiring-soon alert
  // ---------------------------------------------------------------------------

  const expiringSoon = delegations.filter((d) => {
    if (d.status !== 'active') return false;
    const daysLeft = Math.ceil((new Date(d.end_date).getTime() - Date.now()) / 86_400_000);
    return daysLeft >= 0 && daysLeft <= 3;
  });

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Page header */}
      <PageHeader
        title="Delegation Management"
        subtitle="Manage approval authority delegations when approvers are unavailable"
        actions={
          <Button
            icon={<PlusIcon className="h-4 w-4" />}
            onClick={() => {
              setForm(EMPTY_FORM);
              setShowCreateModal(true);
            }}
          >
            New Delegation
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Delegations"
          value={statsData?.active ?? 0}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
        <StatCard
          title="Upcoming"
          value={statsData?.upcoming ?? 0}
          icon={ClockIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Expired This Month"
          value={statsData?.expired_this_month ?? 0}
          icon={ArrowPathIcon}
          iconBgColor="stat-icon-yellow"
          iconColor="text-yellow-400"
        />
        <StatCard
          title="Users Without Delegate"
          value={statsData?.users_without_delegate ?? 0}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-red"
          iconColor="text-red-400"
        />
      </div>

      {/* Expiring-soon banner */}
      {expiringSoon.length > 0 && (
        <div className="glass-card p-4 border-l-4 border-amber-400 bg-amber-50/60">
          <div className="flex items-start gap-3">
            <ExclamationTriangleIcon className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-amber-800">
                {expiringSoon.length} delegation{expiringSoon.length > 1 ? 's' : ''} expiring within 3 days
              </p>
              <ul className="mt-1 space-y-0.5">
                {expiringSoon.map((d) => (
                  <li key={d.id} className="text-xs text-amber-700">
                    {d.delegator_name} to {d.delegate_name} — expires{' '}
                    {new Date(d.end_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
                    <button
                      className="ml-2 underline hover:no-underline"
                      onClick={() => openExtend(d)}
                    >
                      Extend
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Tabs + filters */}
      <Card padding="none">
        {/* Tab bar */}
        <div className="flex items-center justify-between px-5 pt-4 pb-0 border-b border-gray-100/50">
          <div className="flex gap-0">
            {STATUS_TABS.map((tab) => {
              const count = tabCounts[tab.key];
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all duration-150 -mb-px ${
                    isActive
                      ? 'border-gray-800 text-gray-900'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                  {count > 0 && (
                    <span
                      className={`ml-1.5 px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${
                        isActive
                          ? 'bg-gray-800 text-white'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Filter bar */}
        <div className="px-5 py-3 flex flex-wrap gap-3 items-center border-b border-gray-100/50 bg-gray-50/30">
          <div className="flex-1 min-w-[200px] max-w-xs">
            <SearchInput
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClear={() => setSearchTerm('')}
              placeholder="Search delegator, delegate..."
            />
          </div>
          <div className="w-48">
            <Select
              value={scopeFilter}
              onChange={(e) => setScopeFilter(e.target.value as DelegationScope | '')}
              options={SCOPE_OPTIONS as { value: string; label: string }[]}
            />
          </div>
          {(searchTerm || scopeFilter) && (
            <button
              onClick={() => { setSearchTerm(''); setScopeFilter(''); }}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
            >
              <FunnelIcon className="h-3.5 w-3.5" />
              Clear filters
            </button>
          )}
        </div>

        {/* Table */}
        <Table
          columns={columns}
          data={delegations}
          loading={isLoading}
          onRowClick={openDetail}
          emptyMessage={
            activeTab === 'active'
              ? 'No active delegations. Create one to cover an upcoming absence.'
              : activeTab === 'upcoming'
              ? 'No upcoming delegations scheduled.'
              : 'No delegations found.'
          }
        />
      </Card>

      {/* ------------------------------------------------------------------- */}
      {/* Create Modal                                                         */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={showCreateModal}
        onClose={() => { setShowCreateModal(false); setForm(EMPTY_FORM); }}
        title="Create Delegation"
        subtitle="Grant temporary approval authority to a substitute approver"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setShowCreateModal(false); setForm(EMPTY_FORM); }}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              loading={createMutation.isPending}
              disabled={
                !form.delegator_id ||
                !form.delegate_id ||
                !form.start_date ||
                !form.end_date ||
                createMutation.isPending
              }
            >
              Create Delegation
            </Button>
          </>
        }
      >
        <div className="space-y-5">
          {/* Delegator */}
          <div className="glass-card bg-gray-50/40 p-4 space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <UserIcon className="h-4 w-4 text-gray-400" />
              <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider">Delegator</span>
              <span className="text-xs text-gray-400">(who is handing off authority)</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="User ID"
                value={form.delegator_id}
                onChange={(e) => setForm({ ...form, delegator_id: e.target.value })}
                placeholder="e.g. USR-LM-001"
                required
              />
              <Input
                label="Display Name"
                value={form.delegator_name}
                onChange={(e) => setForm({ ...form, delegator_name: e.target.value })}
                placeholder="e.g. Sarah Chen"
              />
            </div>
          </div>

          {/* Delegate arrow indicator */}
          <div className="flex items-center justify-center gap-3">
            <div className="flex-1 h-px bg-gray-200" />
            <div className="flex items-center gap-1.5 text-xs text-gray-400 font-medium">
              <ArrowRightIcon className="h-4 w-4 text-gray-400" />
              delegates to
            </div>
            <div className="flex-1 h-px bg-gray-200" />
          </div>

          {/* Delegate */}
          <div className="glass-card bg-blue-50/30 p-4 space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <ShieldCheckIcon className="h-4 w-4 text-blue-400" />
              <span className="text-xs font-semibold text-blue-700 uppercase tracking-wider">Delegate / Substitute</span>
              <span className="text-xs text-blue-500">(who will act on their behalf)</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="User ID"
                value={form.delegate_id}
                onChange={(e) => setForm({ ...form, delegate_id: e.target.value })}
                placeholder="e.g. USR-LM-007"
                required
              />
              <Input
                label="Display Name"
                value={form.delegate_name}
                onChange={(e) => setForm({ ...form, delegate_name: e.target.value })}
                placeholder="e.g. Marcus Webb"
              />
            </div>
          </div>

          {/* Period */}
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Start Date"
              type="date"
              value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              required
            />
            <Input
              label="End Date"
              type="date"
              value={form.end_date}
              min={form.start_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })}
              required
            />
          </div>

          {/* Scope */}
          <Select
            label="Approval Scope"
            value={form.scope}
            onChange={(e) => setForm({ ...form, scope: e.target.value as DelegationScope })}
            options={SCOPE_FORM_OPTIONS as { value: string; label: string }[]}
          />
          <p className="text-xs text-gray-400 -mt-1">Restrict which request types the delegate can approve, or select All Approvals for full authority.</p>

          {/* Reason */}
          <Textarea
            label="Reason / Justification"
            value={form.reason}
            onChange={(e) => setForm({ ...form, reason: e.target.value })}
            placeholder="Why is the delegator unavailable? (recorded in audit trail)"
            rows={3}
          />

          {/* Info callout */}
          <div className="flex items-start gap-2 p-3 rounded-xl bg-blue-50/60 border border-blue-200/50">
            <InformationCircleIcon className="h-4 w-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-blue-700">
              The delegate will receive approval notifications for the selected scope during the specified period.
              All actions taken by the delegate are recorded in the audit trail and attributed to both parties.
            </p>
          </div>
        </div>
      </Modal>

      {/* ------------------------------------------------------------------- */}
      {/* Edit Modal                                                           */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={showEditModal && selectedDelegation !== null}
        onClose={() => { setShowEditModal(false); setSelectedDelegation(null); }}
        title={`Edit Delegation — ${selectedDelegation?.id ?? ''}`}
        subtitle="Modify the scope, end date, or reason for this delegation"
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setShowEditModal(false); setSelectedDelegation(null); }}>
              Cancel
            </Button>
            <Button
              onClick={handleUpdate}
              loading={updateMutation.isPending}
              disabled={updateMutation.isPending}
            >
              Save Changes
            </Button>
          </>
        }
      >
        {selectedDelegation && (
          <div className="space-y-4">
            {/* Read-only principal display */}
            <div className="p-3 rounded-xl bg-gray-50/60 border border-gray-200/50">
              <DelegationArrow
                delegator={{ name: selectedDelegation.delegator_name, department: selectedDelegation.delegator_department }}
                delegate={{ name: selectedDelegation.delegate_name, department: selectedDelegation.delegate_department }}
              />
            </div>

            <Input
              label="End Date"
              type="date"
              value={form.end_date}
              min={form.start_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })}
            />

            <Select
              label="Approval Scope"
              value={form.scope}
              onChange={(e) => setForm({ ...form, scope: e.target.value as DelegationScope })}
              options={SCOPE_FORM_OPTIONS as { value: string; label: string }[]}
            />

            <Textarea
              label="Reason"
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
              rows={3}
            />
          </div>
        )}
      </Modal>

      {/* ------------------------------------------------------------------- */}
      {/* Extend Modal                                                         */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={showExtendModal && selectedDelegation !== null}
        onClose={() => { setShowExtendModal(false); setSelectedDelegation(null); }}
        title="Extend Delegation"
        subtitle="Push the delegation end date further out"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setShowExtendModal(false); setSelectedDelegation(null); }}>
              Cancel
            </Button>
            <Button
              onClick={handleExtend}
              loading={extendMutation.isPending}
              disabled={!extendDate || extendMutation.isPending}
            >
              Extend
            </Button>
          </>
        }
      >
        {selectedDelegation && (
          <div className="space-y-4">
            <div className="p-3 rounded-xl bg-gray-50/60 border border-gray-200/50">
              <p className="text-xs text-gray-500 mb-1">Delegation</p>
              <p className="text-sm font-medium text-gray-900">
                {selectedDelegation.delegator_name} to {selectedDelegation.delegate_name}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                Current end:{' '}
                {new Date(selectedDelegation.end_date).toLocaleDateString('en-GB', {
                  day: '2-digit',
                  month: 'long',
                  year: 'numeric',
                })}
              </p>
            </div>

            <Input
              label="New End Date"
              type="date"
              value={extendDate}
              min={selectedDelegation.end_date}
              onChange={(e) => setExtendDate(e.target.value)}
              required
            />

            <Textarea
              label="Reason for Extension"
              value={extendReason}
              onChange={(e) => setExtendReason(e.target.value)}
              placeholder="e.g. Return-to-office delayed due to travel"
              rows={2}
            />
          </div>
        )}
      </Modal>

      {/* ------------------------------------------------------------------- */}
      {/* Revoke Modal                                                         */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={showRevokeModal && selectedDelegation !== null}
        onClose={() => { setShowRevokeModal(false); setSelectedDelegation(null); }}
        title="Revoke Delegation"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setShowRevokeModal(false); setSelectedDelegation(null); }}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleRevoke}
              loading={revokeMutation.isPending}
              disabled={revokeMutation.isPending}
            >
              Revoke Delegation
            </Button>
          </>
        }
      >
        {selectedDelegation && (
          <div className="space-y-4">
            <div className="flex items-start gap-3 p-3 rounded-xl bg-red-50/60 border border-red-200/50">
              <ExclamationTriangleIcon className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-red-800">Confirm revocation</p>
                <p className="text-xs text-red-700 mt-0.5">
                  This will immediately remove approval authority from{' '}
                  <strong>{selectedDelegation.delegate_name}</strong>. Pending approvals
                  will revert to <strong>{selectedDelegation.delegator_name}</strong>.
                </p>
              </div>
            </div>

            <Textarea
              label="Reason for Revocation"
              value={revokeReason}
              onChange={(e) => setRevokeReason(e.target.value)}
              placeholder="e.g. Delegator has returned early from leave"
              rows={3}
            />
          </div>
        )}
      </Modal>

      {/* ------------------------------------------------------------------- */}
      {/* Detail / History Modal                                               */}
      {/* ------------------------------------------------------------------- */}
      <Modal
        open={showDetailModal && selectedDelegation !== null}
        onClose={() => { setShowDetailModal(false); setSelectedDelegation(null); }}
        title="Delegation Detail"
        size="lg"
        footer={
          <>
            {selectedDelegation && (selectedDelegation.status === 'active' || selectedDelegation.status === 'upcoming') && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={<CalendarDaysIcon className="h-4 w-4" />}
                  onClick={() => { setShowDetailModal(false); openExtend(selectedDelegation); }}
                >
                  Extend
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={<PencilIcon className="h-4 w-4" />}
                  onClick={() => { setShowDetailModal(false); openEdit(selectedDelegation); }}
                >
                  Edit
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  icon={<XCircleIcon className="h-4 w-4" />}
                  onClick={() => { setShowDetailModal(false); openRevoke(selectedDelegation); }}
                >
                  Revoke
                </Button>
              </>
            )}
            <Button variant="secondary" onClick={() => { setShowDetailModal(false); setSelectedDelegation(null); }}>
              Close
            </Button>
          </>
        }
      >
        {selectedDelegation && (
          <div className="space-y-5">
            {/* Header summary */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-gray-400">{selectedDelegation.id}</span>
                <StatusBadgeLocal status={selectedDelegation.status} />
              </div>
              <Badge variant={SCOPE_BADGE_VARIANT[selectedDelegation.scope]}>
                {SCOPE_LABELS[selectedDelegation.scope]}
              </Badge>
            </div>

            {/* Principals */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-gray-50/60 border border-gray-200/50 space-y-1">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Delegator</p>
                <p className="text-sm font-semibold text-gray-900">{selectedDelegation.delegator_name}</p>
                <p className="text-xs text-gray-500">{selectedDelegation.delegator_email}</p>
                <p className="text-xs text-gray-400">{selectedDelegation.delegator_department}</p>
              </div>
              <div className="p-4 rounded-xl bg-blue-50/40 border border-blue-200/50 space-y-1">
                <p className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Delegate</p>
                <p className="text-sm font-semibold text-gray-900">{selectedDelegation.delegate_name}</p>
                <p className="text-xs text-gray-500">{selectedDelegation.delegate_email}</p>
                <p className="text-xs text-gray-400">{selectedDelegation.delegate_department}</p>
              </div>
            </div>

            {/* Period & metrics */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-3 rounded-xl bg-gray-50/60 border border-gray-200/50">
                <p className="text-xs text-gray-500 mb-1">Start Date</p>
                <p className="text-sm font-medium text-gray-900">
                  {new Date(selectedDelegation.start_date).toLocaleDateString('en-GB', {
                    day: '2-digit', month: 'short', year: 'numeric',
                  })}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-gray-50/60 border border-gray-200/50">
                <p className="text-xs text-gray-500 mb-1">End Date</p>
                <p className="text-sm font-medium text-gray-900">
                  {new Date(selectedDelegation.end_date).toLocaleDateString('en-GB', {
                    day: '2-digit', month: 'short', year: 'numeric',
                  })}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-gray-50/60 border border-gray-200/50">
                <p className="text-xs text-gray-500 mb-1">Items Handled</p>
                <p className="text-sm font-semibold text-gray-900">{selectedDelegation.items_handled}</p>
              </div>
            </div>

            {/* Reason */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Reason</p>
              <p className="text-sm text-gray-700 bg-gray-50/60 border border-gray-200/50 rounded-xl px-4 py-3">
                {selectedDelegation.reason || 'No reason recorded.'}
              </p>
            </div>

            {/* Audit trail */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Audit Trail</p>
              <ol className="relative border-l border-gray-200/70 space-y-3 pl-5">
                <li className="relative">
                  <span className="absolute -left-[1.1rem] top-1 w-3 h-3 rounded-full bg-white border-2 border-gray-300" />
                  <p className="text-xs font-medium text-gray-700">Delegation created</p>
                  <p className="text-xs text-gray-400">
                    by {selectedDelegation.created_by} &middot;{' '}
                    {new Date(selectedDelegation.created_at).toLocaleString('en-GB', {
                      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
                    })}
                  </p>
                </li>
                {selectedDelegation.updated_at !== selectedDelegation.created_at && (
                  <li className="relative">
                    <span className="absolute -left-[1.1rem] top-1 w-3 h-3 rounded-full bg-white border-2 border-blue-400" />
                    <p className="text-xs font-medium text-gray-700">Delegation updated</p>
                    <p className="text-xs text-gray-400">
                      {new Date(selectedDelegation.updated_at).toLocaleString('en-GB', {
                        day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
                      })}
                    </p>
                  </li>
                )}
                {selectedDelegation.status === 'expired' && (
                  <li className="relative">
                    <span className="absolute -left-[1.1rem] top-1 w-3 h-3 rounded-full bg-white border-2 border-gray-400" />
                    <p className="text-xs font-medium text-gray-500">Delegation expired</p>
                    <p className="text-xs text-gray-400">
                      {new Date(selectedDelegation.end_date).toLocaleDateString('en-GB', {
                        day: '2-digit', month: 'short', year: 'numeric',
                      })}
                    </p>
                  </li>
                )}
                {selectedDelegation.status === 'revoked' && (
                  <li className="relative">
                    <span className="absolute -left-[1.1rem] top-1 w-3 h-3 rounded-full bg-white border-2 border-red-400" />
                    <p className="text-xs font-medium text-red-700">Delegation revoked</p>
                    <p className="text-xs text-gray-400">
                      {new Date(selectedDelegation.updated_at).toLocaleString('en-GB', {
                        day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
                      })}
                    </p>
                  </li>
                )}
              </ol>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
