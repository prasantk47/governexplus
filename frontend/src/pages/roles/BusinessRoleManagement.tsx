import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../services/api';
import {
  PlusIcon,
  FunnelIcon,
  ArrowDownTrayIcon,
  MagnifyingGlassIcon,
  SparklesIcon,
  PencilSquareIcon,
  TrashIcon,
  EyeIcon,
  ShieldExclamationIcon,
  UserGroupIcon,
  RectangleStackIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  DocumentDuplicateIcon,
  ChartBarIcon,
  CubeTransparentIcon,
} from '@heroicons/react/24/outline';
import { StatCard } from '../../components/StatCard';

// ---- Types ----------------------------------------------------------------

type RoleType = 'single' | 'composite' | 'business' | 'derived';
type RoleStatus = 'draft' | 'review' | 'active' | 'retired';
type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

interface SodConflict {
  rule: string;
  severity: RiskLevel;
  conflictingFunction: string;
}

interface Role {
  id: string;
  name: string;
  description: string;
  type: RoleType;
  status: RoleStatus;
  owner: string;
  ownerEmail: string;
  usersAssigned: number;
  riskLevel: RiskLevel;
  businessProcess: string;
  system: string;
  lastModified: string;
  createdDate: string;
  sodConflicts: SodConflict[];
  childRoles?: string[];
  parentRole?: string;
  transactions: string[];
  lastReviewed?: string;
}

type TabKey = 'all' | 'active' | 'draft' | 'retired' | 'high-risk';

// ---- Fetch helper ---------------------------------------------------------

async function fetchRoles(): Promise<Role[]> {
  const res = await api.get('/role-studio/roles');
  return res.data?.roles ?? res.data ?? [];
}

async function deleteRole(roleId: string): Promise<void> {
  await api.delete(`/role-studio/roles/${roleId}`);
}

// ---- Sub-components -------------------------------------------------------

const ROLE_TYPE_CONFIG: Record<RoleType, { label: string; color: string }> = {
  single: { label: 'Single', color: 'bg-blue-100 text-blue-800' },
  composite: { label: 'Composite', color: 'bg-purple-100 text-purple-800' },
  business: { label: 'Business', color: 'bg-indigo-100 text-indigo-800' },
  derived: { label: 'Derived', color: 'bg-cyan-100 text-cyan-800' },
};

const ROLE_STATUS_CONFIG: Record<RoleStatus, { label: string; color: string; icon: React.ComponentType<{ className?: string }> }> = {
  draft: { label: 'Draft', color: 'bg-gray-100 text-gray-700', icon: PencilSquareIcon },
  review: { label: 'Under Review', color: 'bg-yellow-100 text-yellow-800', icon: ClockIcon },
  active: { label: 'Active', color: 'bg-green-100 text-green-800', icon: CheckCircleIcon },
  retired: { label: 'Retired', color: 'bg-red-100 text-red-700', icon: XCircleIcon },
};

const RISK_CONFIG: Record<RiskLevel, { label: string; color: string }> = {
  low: { label: 'Low', color: 'bg-green-100 text-green-800' },
  medium: { label: 'Medium', color: 'bg-yellow-100 text-yellow-800' },
  high: { label: 'High', color: 'bg-orange-100 text-orange-800' },
  critical: { label: 'Critical', color: 'bg-red-100 text-red-800' },
};

function RoleTypeBadge({ type }: { type: RoleType }) {
  const cfg = ROLE_TYPE_CONFIG[type];
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

function RoleStatusBadge({ status }: { status: RoleStatus }) {
  const cfg = ROLE_STATUS_CONFIG[status];
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cfg.color}`}>
      <Icon className="h-3 w-3" />
      {cfg.label}
    </span>
  );
}

function RiskLevelBadge({ level }: { level: RiskLevel }) {
  const cfg = RISK_CONFIG[level];
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

// ---- Role Detail Drawer ---------------------------------------------------

interface RoleDetailDrawerProps {
  role: Role | null;
  onClose: () => void;
}

function RoleDetailDrawer({ role, onClose }: RoleDetailDrawerProps) {
  if (!role) return null;

  return (
    <div className="fixed inset-0 z-40 flex justify-end" aria-modal="true" role="dialog">
      <div className="fixed inset-0 bg-black/30" onClick={onClose} />
      <div className="relative z-50 flex flex-col w-full max-w-xl bg-white shadow-xl overflow-y-auto">
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div>
            <p className="text-xs text-gray-500 font-mono">{role.id}</p>
            <h2 className="text-lg font-semibold text-gray-900 mt-0.5">{role.name}</h2>
            <div className="flex items-center gap-2 mt-1">
              <RoleTypeBadge type={role.type} />
              <RoleStatusBadge status={role.status} />
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-200"
            aria-label="Close"
          >
            <XCircleIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 px-6 py-4 space-y-6">
          {/* Description */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-1">Description</h3>
            <p className="text-sm text-gray-600">{role.description}</p>
          </div>

          {/* Key Details */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Details</h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
              {[
                { label: 'Owner', value: role.owner },
                { label: 'Business Process', value: role.businessProcess },
                { label: 'System', value: role.system },
                { label: 'Users Assigned', value: String(role.usersAssigned) },
                { label: 'Risk Level', value: <RiskLevelBadge level={role.riskLevel} /> },
                { label: 'Last Modified', value: role.lastModified },
                { label: 'Created', value: role.createdDate },
                { label: 'Last Reviewed', value: role.lastReviewed ?? 'Never' },
              ].map(({ label, value }) => (
                <div key={label}>
                  <dt className="text-xs text-gray-500">{label}</dt>
                  <dd className="text-sm font-medium text-gray-900 mt-0.5">{value}</dd>
                </div>
              ))}
            </dl>
          </div>

          {/* SoD Conflicts */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1.5">
              <ShieldExclamationIcon className="h-4 w-4 text-orange-500" />
              SoD Conflicts ({role.sodConflicts.length})
            </h3>
            {role.sodConflicts.length === 0 ? (
              <p className="text-sm text-gray-400 italic">No SoD conflicts detected.</p>
            ) : (
              <div className="space-y-2">
                {role.sodConflicts.map((c) => (
                  <div
                    key={c.rule}
                    className="flex items-center justify-between rounded-md border border-gray-200 px-3 py-2 bg-gray-50"
                  >
                    <div>
                      <span className="text-xs font-mono text-gray-700">{c.rule}</span>
                      <p className="text-xs text-gray-500 mt-0.5">{c.conflictingFunction}</p>
                    </div>
                    <RiskLevelBadge level={c.severity} />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Transactions */}
          {role.transactions.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Transactions / Authorizations</h3>
              <div className="flex flex-wrap gap-1.5">
                {role.transactions.map((t) => (
                  <span key={t} className="px-2 py-0.5 rounded bg-gray-100 text-gray-700 text-xs font-mono">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Child / Parent Roles */}
          {role.childRoles && role.childRoles.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">
                Included Roles ({role.childRoles.length})
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {role.childRoles.map((r) => (
                  <span key={r} className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 text-xs font-mono">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}
          {role.parentRole && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-1">Parent Role</h3>
              <span className="px-2 py-0.5 rounded bg-cyan-50 text-cyan-700 text-xs font-mono">
                {role.parentRole}
              </span>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex gap-2">
          <button className="flex-1 btn-secondary text-sm flex items-center justify-center gap-2">
            <PencilSquareIcon className="h-4 w-4" />
            Edit Role
          </button>
          <button className="flex-1 btn-secondary text-sm flex items-center justify-center gap-2">
            <DocumentDuplicateIcon className="h-4 w-4" />
            Clone Role
          </button>
        </div>
      </div>
    </div>
  );
}

// ---- Role Mining Modal ----------------------------------------------------

function RoleMiningModal({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState<1 | 2>(1);
  const suggestions = [
    {
      suggestedName: 'FI Junior Accountant',
      basis: '38 users share identical FI authorization patterns (FB01, FB03, FS10N)',
      coverage: 38,
      riskLevel: 'low' as RiskLevel,
      businessProcess: 'Record-to-Report (R2R)',
    },
    {
      suggestedName: 'MM Goods Receipt Clerk',
      basis: '22 users share MIGO + MB51 + MB52 with no additional transactions',
      coverage: 22,
      riskLevel: 'low' as RiskLevel,
      businessProcess: 'Procure-to-Pay (P2P)',
    },
    {
      suggestedName: 'SD Order Entry Clerk',
      basis: '61 users assigned VA01 + VA02 only — candidate for a restricted derived role',
      coverage: 61,
      riskLevel: 'low' as RiskLevel,
      businessProcess: 'Order-to-Cash (O2C)',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/30" onClick={onClose} />
      <div className="relative z-50 bg-white rounded-xl shadow-2xl w-full max-w-2xl mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <SparklesIcon className="h-5 w-5 text-indigo-500" />
            <h2 className="text-lg font-semibold text-gray-900">AI Role Mining</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XCircleIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="px-6 py-4">
          {step === 1 ? (
            <div>
              <p className="text-sm text-gray-600 mb-4">
                Analyze existing user assignments to identify access pattern clusters and propose
                new consolidated roles, reducing role sprawl and improving auditability.
              </p>
              <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-4 mb-4">
                <p className="text-xs font-medium text-indigo-700 uppercase tracking-wide mb-1">
                  Analysis scope
                </p>
                <p className="text-sm text-indigo-900">
                  1,247 users across SAP ECC, S4HANA, HCM — scanning 4,832 role assignments
                </p>
              </div>
              <button
                onClick={() => setStep(2)}
                className="w-full py-2.5 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 flex items-center justify-center gap-2"
              >
                <SparklesIcon className="h-4 w-4" />
                Run Role Mining Analysis
              </button>
            </div>
          ) : (
            <div>
              <p className="text-sm text-gray-600 mb-4">
                Found <strong>{suggestions.length} candidate roles</strong> based on access pattern
                clustering. Review and accept suggestions to create draft roles.
              </p>
              <div className="space-y-3">
                {suggestions.map((s, i) => (
                  <div key={i} className="rounded-lg border border-gray-200 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-gray-900">{s.suggestedName}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{s.businessProcess}</p>
                        <p className="text-xs text-gray-600 mt-1">{s.basis}</p>
                      </div>
                      <div className="flex flex-col items-end gap-1.5 shrink-0">
                        <RiskLevelBadge level={s.riskLevel} />
                        <span className="text-xs text-gray-500">{s.coverage} users</span>
                      </div>
                    </div>
                    <div className="mt-3 flex gap-2">
                      <button className="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 font-medium">
                        Create as Draft
                      </button>
                      <button className="px-3 py-1 text-xs bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-50 font-medium">
                        Dismiss
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 flex justify-end">
          <button onClick={onClose} className="text-sm text-gray-600 hover:text-gray-800">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ---- Main Component -------------------------------------------------------

const TABS: { key: TabKey; label: string }[] = [
  { key: 'all', label: 'All Roles' },
  { key: 'active', label: 'Active' },
  { key: 'draft', label: 'Draft' },
  { key: 'retired', label: 'Retired' },
  { key: 'high-risk', label: 'High Risk' },
];

const BUSINESS_PROCESSES = [
  'All Processes',
  'Procure-to-Pay (P2P)',
  'Order-to-Cash (O2C)',
  'Record-to-Report (R2R)',
  'Hire-to-Retire (H2R)',
  'IT Administration',
];

export function BusinessRoleManagement() {
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<TabKey>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [processFilter, setProcessFilter] = useState('All Processes');
  const [typeFilter, setTypeFilter] = useState<RoleType | 'all'>('all');
  const [selectedRoleIds, setSelectedRoleIds] = useState<Set<string>>(new Set());
  const [detailRole, setDetailRole] = useState<Role | null>(null);
  const [showMining, setShowMining] = useState(false);

  const { data: rolesData, isLoading, isError, refetch } = useQuery<Role[]>({
    queryKey: ['business-roles'],
    queryFn: fetchRoles,
    staleTime: 60_000,
  });

  const roles: Role[] = rolesData ?? [];

  const deleteMutation = useMutation({
    mutationFn: (roleId: string) => deleteRole(roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-roles'] });
      setSelectedRoleIds(new Set());
    },
  });

  // ---- Stats ---------------------------------------------------------------

  const stats = {
    total: roles.length,
    active: roles.filter((r) => r.status === 'active').length,
    review: roles.filter((r) => r.status === 'review').length,
    highRisk: roles.filter((r) => r.riskLevel === 'high' || r.riskLevel === 'critical').length,
  };

  // ---- Filtering -----------------------------------------------------------

  const filteredRoles = roles.filter((role) => {
    const matchesTab =
      activeTab === 'all' ||
      (activeTab === 'active' && role.status === 'active') ||
      (activeTab === 'draft' && role.status === 'draft') ||
      (activeTab === 'retired' && role.status === 'retired') ||
      (activeTab === 'high-risk' && (role.riskLevel === 'high' || role.riskLevel === 'critical'));

    const matchesSearch =
      searchTerm === '' ||
      String(role.id).toLowerCase().includes(searchTerm.toLowerCase()) ||
      (role.name ?? '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (role.owner ?? '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (role.businessProcess ?? '').toLowerCase().includes(searchTerm.toLowerCase());

    const matchesProcess =
      processFilter === 'All Processes' || role.businessProcess === processFilter;

    const matchesType = typeFilter === 'all' || role.type === typeFilter;

    return matchesTab && matchesSearch && matchesProcess && matchesType;
  });

  // ---- Selection -----------------------------------------------------------

  const allVisibleSelected =
    filteredRoles.length > 0 && filteredRoles.every((r) => selectedRoleIds.has(r.id));

  function toggleSelectAll() {
    if (allVisibleSelected) {
      setSelectedRoleIds(new Set());
    } else {
      setSelectedRoleIds(new Set(filteredRoles.map((r) => r.id)));
    }
  }

  function toggleSelectRole(id: string) {
    setSelectedRoleIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // ---- CSV Export ----------------------------------------------------------

  function handleExport() {
    const headers = [
      'Role ID', 'Name', 'Type', 'Status', 'Owner', 'Users Assigned',
      'Risk Level', 'Business Process', 'System', 'SoD Conflicts', 'Last Modified',
    ];
    const rows = filteredRoles.map((r) => [
      r.id, r.name, r.type, r.status, r.owner, String(r.usersAssigned),
      r.riskLevel, r.businessProcess, r.system, String(r.sodConflicts.length), r.lastModified,
    ]);
    const csv = [headers, ...rows].map((row) => row.map((c) => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `business_roles_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  // ---- Render --------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Role Design Studio</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage role lifecycle, ownership, risk analysis, and mining across your SAP landscape
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowMining(true)}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-indigo-300 bg-indigo-50 text-indigo-700 text-sm font-medium hover:bg-indigo-100 transition-colors"
          >
            <SparklesIcon className="h-4 w-4" />
            Role Mining
          </button>
          <button
            onClick={handleExport}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-gray-300 bg-white text-gray-700 text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            <ArrowDownTrayIcon className="h-4 w-4" />
            Export
          </button>
          <button className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors">
            <PlusIcon className="h-4 w-4" />
            Create Role
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard
          title="Total Roles"
          value={stats.total}
          icon={RectangleStackIcon}
          iconBgColor="bg-blue-100 text-blue-600"
          iconColor="text-blue-600"
        />
        <StatCard
          title="Active Roles"
          value={stats.active}
          icon={CheckCircleIcon}
          iconBgColor="bg-green-100 text-green-600"
          iconColor="text-green-600"
        />
        <StatCard
          title="Under Review"
          value={stats.review}
          icon={ClockIcon}
          iconBgColor="bg-yellow-100 text-yellow-600"
          iconColor="text-yellow-600"
        />
        <StatCard
          title="High Risk Roles"
          value={stats.highRisk}
          icon={ShieldExclamationIcon}
          iconBgColor="bg-red-100 text-red-600"
          iconColor="text-red-600"
          trend={2}
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6" aria-label="Role lifecycle tabs">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => {
                  setActiveTab(tab.key);
                  setSelectedRoleIds(new Set());
                }}
                className={`pb-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
                {tab.key === 'all' && (
                  <span className="ml-1.5 rounded-full bg-gray-100 text-gray-600 px-2 py-0.5 text-xs">
                    {roles.length}
                  </span>
                )}
                {tab.key === 'high-risk' && stats.highRisk > 0 && (
                  <span className="ml-1.5 rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs">
                    {stats.highRisk}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-48 max-w-xs">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Search roles, owners..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>

        {/* Business process filter */}
        <div className="flex items-center gap-1.5">
          <FunnelIcon className="h-4 w-4 text-gray-400" />
          <select
            value={processFilter}
            onChange={(e) => setProcessFilter(e.target.value)}
            className="border border-gray-300 rounded-md text-sm py-2 pl-2 pr-8 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white text-gray-700"
          >
            {BUSINESS_PROCESSES.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        {/* Role type filter */}
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as RoleType | 'all')}
          className="border border-gray-300 rounded-md text-sm py-2 pl-2 pr-8 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white text-gray-700"
        >
          <option value="all">All Types</option>
          <option value="single">Single</option>
          <option value="composite">Composite</option>
          <option value="business">Business</option>
          <option value="derived">Derived</option>
        </select>

        {/* Refresh */}
        <button
          onClick={() => refetch()}
          className="p-2 rounded-md border border-gray-300 bg-white text-gray-500 hover:text-gray-700 hover:bg-gray-50"
          title="Refresh"
        >
          <ArrowPathIcon className="h-4 w-4" />
        </button>

        <div className="ml-auto text-sm text-gray-500">
          {filteredRoles.length} of {roles.length} roles
        </div>
      </div>

      {/* Bulk actions */}
      {selectedRoleIds.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-2.5 bg-primary-50 border border-primary-200 rounded-lg">
          <span className="text-sm text-primary-700 font-medium">
            {selectedRoleIds.size} role{selectedRoleIds.size > 1 ? 's' : ''} selected
          </span>
          <div className="flex items-center gap-2 ml-auto">
            <button className="px-3 py-1.5 text-xs font-medium bg-white border border-gray-300 rounded text-gray-700 hover:bg-gray-50">
              Bulk Edit Owner
            </button>
            <button className="px-3 py-1.5 text-xs font-medium bg-white border border-gray-300 rounded text-gray-700 hover:bg-gray-50">
              Run Risk Analysis
            </button>
            <button className="px-3 py-1.5 text-xs font-medium bg-white border border-orange-300 rounded text-orange-700 hover:bg-orange-50">
              Retire Selected
            </button>
            <button
              onClick={() => setSelectedRoleIds(new Set())}
              className="px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-gray-700"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16 text-gray-400">
            <ArrowPathIcon className="h-6 w-6 animate-spin mr-2" />
            <span className="text-sm">Loading roles...</span>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-400">
            <XCircleIcon className="h-8 w-8 text-red-400 mb-2" />
            <p className="text-sm">Failed to load roles. Showing cached data.</p>
            <button onClick={() => refetch()} className="mt-2 text-sm text-primary-600 hover:underline">
              Retry
            </button>
          </div>
        ) : filteredRoles.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-400">
            <CubeTransparentIcon className="h-8 w-8 mb-2" />
            <p className="text-sm">No roles match the current filters.</p>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left w-8">
                  <input
                    type="checkbox"
                    checked={allVisibleSelected}
                    onChange={toggleSelectAll}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    aria-label="Select all visible roles"
                  />
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Owner
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Users
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Business Process
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SoD Conflicts
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Modified
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredRoles.map((role) => {
                const isSelected = selectedRoleIds.has(role.id);
                const conflictCount = role.sodConflicts.length;
                const criticalConflicts = role.sodConflicts.filter((c) => c.severity === 'critical').length;

                return (
                  <tr
                    key={role.id}
                    className={`hover:bg-gray-50 transition-colors ${isSelected ? 'bg-primary-50' : ''}`}
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectRole(role.id)}
                        className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        aria-label={`Select ${role.name}`}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-gray-900 truncate max-w-48" title={role.name}>
                          {role.name}
                        </p>
                        <p className="text-xs text-gray-400 font-mono mt-0.5">{role.id}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <RoleTypeBadge type={role.type} />
                    </td>
                    <td className="px-4 py-3">
                      <RoleStatusBadge status={role.status} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <div className="h-6 w-6 rounded-full bg-gray-200 flex items-center justify-center shrink-0">
                          <span className="text-xs font-medium text-gray-600">
                            {role.owner.split(' ').map((n) => n[0]).join('').slice(0, 2)}
                          </span>
                        </div>
                        <span className="text-gray-700 text-sm truncate max-w-28" title={role.owner}>
                          {role.owner}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1 text-gray-700">
                        <UserGroupIcon className="h-3.5 w-3.5 text-gray-400" />
                        <span className="font-medium">{role.usersAssigned}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <RiskLevelBadge level={role.riskLevel} />
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-gray-600 text-xs">{role.businessProcess}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {conflictCount === 0 ? (
                        <span className="text-green-600 text-xs font-medium">None</span>
                      ) : (
                        <div className="flex items-center justify-end gap-1">
                          <ShieldExclamationIcon
                            className={`h-4 w-4 ${
                              criticalConflicts > 0 ? 'text-red-500' : 'text-orange-400'
                            }`}
                          />
                          <span
                            className={`text-xs font-semibold ${
                              criticalConflicts > 0 ? 'text-red-600' : 'text-orange-600'
                            }`}
                          >
                            {conflictCount}
                          </span>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{role.lastModified}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setDetailRole(role)}
                          title="View details"
                          className="p-1.5 rounded text-gray-400 hover:text-primary-600 hover:bg-primary-50"
                        >
                          <EyeIcon className="h-4 w-4" />
                        </button>
                        <button
                          title="Edit role"
                          className="p-1.5 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50"
                        >
                          <PencilSquareIcon className="h-4 w-4" />
                        </button>
                        <button
                          title="Clone role"
                          className="p-1.5 rounded text-gray-400 hover:text-indigo-600 hover:bg-indigo-50"
                        >
                          <DocumentDuplicateIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => {
                            if (window.confirm(`Delete role "${role.name}"? This cannot be undone.`)) {
                              deleteMutation.mutate(role.id);
                            }
                          }}
                          disabled={deleteMutation.isPending}
                          title="Delete role"
                          className="p-1.5 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 disabled:opacity-40"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Role usage analytics strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-400">
          <div className="flex items-center gap-3">
            <ChartBarIcon className="h-6 w-6 text-blue-500 shrink-0" />
            <div>
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">
                Most Assigned Role
              </p>
              <p className="text-sm font-semibold text-gray-900 mt-0.5">
                {roles.reduce((a, b) => (a.usersAssigned > b.usersAssigned ? a : b), roles[0])?.name ?? '-'}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {Math.max(...roles.map((r) => r.usersAssigned))} users
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-400">
          <div className="flex items-center gap-3">
            <ShieldExclamationIcon className="h-6 w-6 text-red-500 shrink-0" />
            <div>
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">
                Most SoD Conflicts
              </p>
              <p className="text-sm font-semibold text-gray-900 mt-0.5">
                {roles.reduce((a, b) => (a.sodConflicts.length > b.sodConflicts.length ? a : b), roles[0])?.name ?? '-'}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {Math.max(...roles.map((r) => r.sodConflicts.length))} conflicts
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-400">
          <div className="flex items-center gap-3">
            <UserGroupIcon className="h-6 w-6 text-green-500 shrink-0" />
            <div>
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">
                Total Role Assignments
              </p>
              <p className="text-sm font-semibold text-gray-900 mt-0.5">
                {roles.reduce((acc, r) => acc + r.usersAssigned, 0).toLocaleString()}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">across all active roles</p>
            </div>
          </div>
        </div>
      </div>

      {/* Detail Drawer */}
      {detailRole && (
        <RoleDetailDrawer role={detailRole} onClose={() => setDetailRole(null)} />
      )}

      {/* Role Mining Modal */}
      {showMining && (
        <RoleMiningModal onClose={() => setShowMining(false)} />
      )}
    </div>
  );
}
