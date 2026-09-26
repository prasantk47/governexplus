import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowPathIcon,
  ArrowDownTrayIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ServerStackIcon,
  ChartBarIcon,
  UserGroupIcon,
  DocumentTextIcon,
  FunnelIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Select,
  Badge,
  RiskBadge,
  Table,
} from '../../components/ui';

// ============================================================================
// Types
// ============================================================================

type MappingStatus = 'compatible' | 'replaced' | 'obsolete';
type EffortLevel = 'low' | 'medium' | 'high';
type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
type ProcessArea =
  | 'Finance'
  | 'Procurement'
  | 'Logistics'
  | 'HR'
  | 'Sales'
  | 'Basis';

interface TransactionMapping {
  id: string;
  eccTcode: string;
  eccDescription: string;
  s4Equivalent: string | null;
  fioriApp: string | null;
  status: MappingStatus;
  processArea: ProcessArea;
  notes: string;
}

interface RoleAssessment {
  id: string;
  roleName: string;
  processArea: ProcessArea;
  readinessScore: number;
  supportedTcodes: number;
  changedTcodes: number;
  obsoleteTcodes: number;
  totalTcodes: number;
  effortEstimate: EffortLevel;
  riskLevel: RiskLevel;
}

interface UserImpact {
  userId: string;
  userName: string;
  department: string;
  affectedRoles: number;
  accessLossRisk: RiskLevel;
  retrainingRequired: boolean;
}

interface MigrationPhase {
  phase: number;
  title: string;
  duration: string;
  tasks: string[];
  status: 'completed' | 'in_progress' | 'pending';
}

interface MigrationData {
  overallReadiness: number;
  rolesAnalyzed: number;
  compatible: number;
  needsChanges: number;
  obsolete: number;
  transactionMappings: TransactionMapping[];
  roleAssessments: RoleAssessment[];
  userImpacts: UserImpact[];
  migrationPlan: MigrationPhase[];
}

// ============================================================================
// Helpers
// ============================================================================

const mappingStatusConfig: Record<
  MappingStatus,
  { variant: 'success' | 'warning' | 'danger'; label: string }
> = {
  compatible: { variant: 'success', label: 'Compatible' },
  replaced: { variant: 'warning', label: 'Replaced' },
  obsolete: { variant: 'danger', label: 'Obsolete' },
};

const effortConfig: Record<
  EffortLevel,
  { color: string; label: string }
> = {
  low: { color: 'text-green-700 bg-green-50 border-green-200', label: 'Low' },
  medium: { color: 'text-amber-700 bg-amber-50 border-amber-200', label: 'Medium' },
  high: { color: 'text-red-700 bg-red-50 border-red-200', label: 'High' },
};

const phaseStatusConfig: Record<
  MigrationPhase['status'],
  { color: string; label: string; iconColor: string }
> = {
  completed: { color: 'border-emerald-300 bg-emerald-50', label: 'Completed', iconColor: 'text-emerald-600' },
  in_progress: { color: 'border-blue-300 bg-blue-50', label: 'In Progress', iconColor: 'text-blue-600' },
  pending: { color: 'border-gray-200 bg-gray-50', label: 'Pending', iconColor: 'text-gray-400' },
};

function readinessColor(score: number): string {
  if (score >= 80) return 'bg-emerald-500';
  if (score >= 60) return 'bg-amber-500';
  return 'bg-red-500';
}

function readinessTextColor(score: number): string {
  if (score >= 80) return 'text-emerald-700';
  if (score >= 60) return 'text-amber-700';
  return 'text-red-700';
}

// ============================================================================
// Component
// ============================================================================

export function MigrationAnalyzer() {
  const [processAreaFilter, setProcessAreaFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [mappingStatusFilter, setMappingStatusFilter] = useState<string>('all');
  const [selectedRole, setSelectedRole] = useState<RoleAssessment | null>(null);
  const [activeTab, setActiveTab] = useState<'mappings' | 'roles' | 'users' | 'plan'>('mappings');

  const { data: migrationData, isLoading } = useQuery<MigrationData>({
    queryKey: ['migration-analysis'],
    queryFn: () =>
      api
        .get('/migration/transactions/mapping')
        .then((res) => res.data),
  });

  const data: MigrationData = migrationData ?? {
    overallReadiness: 0,
    rolesAnalyzed: 0,
    compatible: 0,
    needsChanges: 0,
    obsolete: 0,
    transactionMappings: [],
    roleAssessments: [],
    userImpacts: [],
    migrationPlan: [],
  };

  const handleExport = () => {
    const rows = data.transactionMappings.map((m) => [
      m.eccTcode,
      m.eccDescription,
      m.s4Equivalent ?? 'N/A',
      m.fioriApp ?? 'N/A',
      m.status,
      m.processArea,
      m.notes,
    ]);
    const headers = ['ECC TCode', 'Description', 'S/4 Equivalent', 'Fiori App', 'Status', 'Process Area', 'Notes'];
    const csv = [headers, ...rows].map((r) => r.map((c) => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `migration_analysis_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
    toast.success('Transaction mapping exported to CSV');
  };

  const filteredMappings = data.transactionMappings.filter((m) => {
    const matchesArea = processAreaFilter === 'all' || m.processArea === processAreaFilter;
    const matchesStatus = mappingStatusFilter === 'all' || m.status === mappingStatusFilter;
    return matchesArea && matchesStatus;
  });

  const filteredRoles = data.roleAssessments.filter((r) => {
    const matchesArea = processAreaFilter === 'all' || r.processArea === processAreaFilter;
    const matchesRisk = riskFilter === 'all' || r.riskLevel === riskFilter;
    return matchesArea && matchesRisk;
  });

  const mappingColumns = [
    {
      key: 'ecc',
      header: 'ECC TCode',
      render: (m: TransactionMapping) => (
        <div>
          <div className="text-sm font-mono font-semibold text-gray-900">{m.eccTcode}</div>
          <div className="text-xs text-gray-500 truncate max-w-[180px]">{m.eccDescription}</div>
        </div>
      ),
    },
    {
      key: 's4',
      header: 'S/4HANA Equivalent',
      render: (m: TransactionMapping) =>
        m.s4Equivalent ? (
          <span className="text-sm font-mono text-blue-700">{m.s4Equivalent}</span>
        ) : (
          <span className="text-xs text-gray-400 italic">None</span>
        ),
    },
    {
      key: 'fiori',
      header: 'Fiori App',
      render: (m: TransactionMapping) =>
        m.fioriApp ? (
          <span className="text-xs text-gray-700">{m.fioriApp}</span>
        ) : (
          <span className="text-xs text-gray-400 italic">None</span>
        ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (m: TransactionMapping) => {
        const cfg = mappingStatusConfig[m.status];
        return (
          <Badge variant={cfg.variant} size="sm">
            {cfg.label}
          </Badge>
        );
      },
    },
    {
      key: 'area',
      header: 'Process Area',
      render: (m: TransactionMapping) => (
        <Badge variant="neutral" size="sm">{m.processArea}</Badge>
      ),
    },
    {
      key: 'notes',
      header: 'Notes',
      render: (m: TransactionMapping) => (
        <span className="text-xs text-gray-500 max-w-[200px] truncate block">{m.notes}</span>
      ),
    },
  ];

  const tabs = [
    { key: 'mappings' as const, label: 'Transaction Mapping', count: data.transactionMappings.length },
    { key: 'roles' as const, label: 'Role Assessment', count: data.roleAssessments.length },
    { key: 'users' as const, label: 'User Impact', count: data.userImpacts.length },
    { key: 'plan' as const, label: 'Migration Plan', count: data.migrationPlan.length },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="ECC to S/4HANA Migration Analyzer"
        subtitle="Assess security impact, role readiness, and user access changes for your S/4HANA migration"
        breadcrumbs={[{ label: 'Intelligence' }, { label: 'Migration Analyzer' }]}
        actions={
          <div className="flex gap-2">
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
              icon={<ArrowPathIcon className="h-4 w-4" />}
              loading={isLoading}
              onClick={() => toast.success('Re-running migration analysis...')}
            >
              Re-analyze
            </Button>
          </div>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="glass-card p-5 flex flex-col items-center justify-center text-center lg:col-span-1">
          <div className="text-3xl font-bold text-primary-600">{data.overallReadiness}%</div>
          <div className="text-xs text-gray-500 mt-1 font-medium">Overall Readiness</div>
          <div className="mt-3 w-full bg-gray-100/60 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${readinessColor(data.overallReadiness)}`}
              style={{ width: `${data.overallReadiness}%` }}
            />
          </div>
        </div>
        <StatCard
          title="Roles Analyzed"
          value={data.rolesAnalyzed}
          icon={ChartBarIcon}
          iconBgColor="stat-icon-blue"
          iconColor=""
        />
        <StatCard
          title="Compatible"
          value={data.compatible}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor=""
        />
        <StatCard
          title="Needs Changes"
          value={data.needsChanges}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-yellow"
          iconColor=""
        />
        <StatCard
          title="Obsolete"
          value={data.obsolete}
          icon={XCircleIcon}
          iconBgColor="stat-icon-red"
          iconColor=""
        />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          <FunnelIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
          <div className="flex flex-wrap gap-2">
            <Select
              value={processAreaFilter}
              onChange={(e) => setProcessAreaFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Process Areas' },
                { value: 'Finance', label: 'Finance' },
                { value: 'Procurement', label: 'Procurement' },
                { value: 'Logistics', label: 'Logistics' },
                { value: 'HR', label: 'HR' },
                { value: 'Sales', label: 'Sales' },
                { value: 'Basis', label: 'Basis' },
              ]}
            />
            <Select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Risk Levels' },
                { value: 'critical', label: 'Critical' },
                { value: 'high', label: 'High' },
                { value: 'medium', label: 'Medium' },
                { value: 'low', label: 'Low' },
              ]}
            />
            <Select
              value={mappingStatusFilter}
              onChange={(e) => setMappingStatusFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Statuses' },
                { value: 'compatible', label: 'Compatible' },
                { value: 'replaced', label: 'Replaced' },
                { value: 'obsolete', label: 'Obsolete' },
              ]}
            />
          </div>
        </div>
      </Card>

      {/* Tabs */}
      <div className="border-b border-gray-200/60">
        <nav className="flex gap-0 -mb-px overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.key
                  ? 'border-primary-600 text-primary-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
              <span
                className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${
                  activeTab === tab.key
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-500'
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </nav>
      </div>

      {/* Transaction Mapping Tab */}
      {activeTab === 'mappings' && (
        <Card padding="none">
          <div className="px-6 py-4 border-b border-white/20">
            <h2 className="text-sm font-semibold text-gray-900">
              Transaction Code Mapping ({filteredMappings.length})
            </h2>
          </div>
          <Table
            columns={mappingColumns}
            data={filteredMappings}
            emptyMessage="No transaction mappings match the selected filters"
          />
        </Card>
      )}

      {/* Role Assessment Tab */}
      {activeTab === 'roles' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-3">
            {filteredRoles.map((role) => (
              <Card
                key={role.id}
                padding="md"
                hover
                className={`cursor-pointer transition-all ${
                  selectedRole?.id === role.id ? 'ring-2 ring-primary-400' : ''
                }`}
                onClick={() => setSelectedRole(selectedRole?.id === role.id ? null : role)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-mono font-semibold text-gray-900">{role.roleName}</span>
                      <Badge variant="neutral" size="sm">{role.processArea}</Badge>
                      <RiskBadge level={role.riskLevel} />
                    </div>
                    <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
                      <span className="text-green-700 font-medium">{role.supportedTcodes} supported</span>
                      <span className="text-amber-700 font-medium">{role.changedTcodes} changed</span>
                      <span className="text-red-700 font-medium">{role.obsoleteTcodes} obsolete</span>
                      <span className="text-gray-400">of {role.totalTcodes} total</span>
                    </div>
                    <div className="mt-2 w-full bg-gray-100/60 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full transition-all duration-500 ${readinessColor(role.readinessScore)}`}
                        style={{ width: `${role.readinessScore}%` }}
                      />
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <span className={`text-2xl font-bold ${readinessTextColor(role.readinessScore)}`}>
                      {role.readinessScore}%
                    </span>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${effortConfig[role.effortEstimate].color}`}
                    >
                      {effortConfig[role.effortEstimate].label} effort
                    </span>
                  </div>
                </div>
              </Card>
            ))}
            {filteredRoles.length === 0 && (
              <Card padding="lg">
                <p className="text-center text-sm text-gray-400">No roles match the selected filters</p>
              </Card>
            )}
          </div>

          {/* Role Detail Panel */}
          <div>
            {selectedRole ? (
              <Card padding="none">
                <div className="px-5 py-4 border-b border-white/20">
                  <h3 className="text-sm font-semibold text-gray-900">Role Detail</h3>
                  <p className="text-xs text-gray-500 font-mono mt-0.5">{selectedRole.roleName}</p>
                </div>
                <div className="p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">Readiness Score</span>
                    <span className={`text-lg font-bold ${readinessTextColor(selectedRole.readinessScore)}`}>
                      {selectedRole.readinessScore}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-100/60 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${readinessColor(selectedRole.readinessScore)}`}
                      style={{ width: `${selectedRole.readinessScore}%` }}
                    />
                  </div>
                  <div className="space-y-2 text-xs">
                    {[
                      { label: 'Supported Tcodes', value: selectedRole.supportedTcodes, color: 'text-green-700' },
                      { label: 'Changed Tcodes', value: selectedRole.changedTcodes, color: 'text-amber-700' },
                      { label: 'Obsolete Tcodes', value: selectedRole.obsoleteTcodes, color: 'text-red-700' },
                      { label: 'Total Tcodes', value: selectedRole.totalTcodes, color: 'text-gray-700' },
                    ].map((item) => (
                      <div key={item.label} className="flex justify-between py-1 border-b border-gray-100/60">
                        <span className="text-gray-500">{item.label}</span>
                        <span className={`font-semibold ${item.color}`}>{item.value}</span>
                      </div>
                    ))}
                  </div>
                  <div className="pt-2 space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Effort Estimate</span>
                      <span className={`font-semibold px-2 py-0.5 rounded-full border text-[10px] ${effortConfig[selectedRole.effortEstimate].color}`}>
                        {effortConfig[selectedRole.effortEstimate].label}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Risk Level</span>
                      <RiskBadge level={selectedRole.riskLevel} />
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Process Area</span>
                      <Badge variant="neutral" size="sm">{selectedRole.processArea}</Badge>
                    </div>
                  </div>
                </div>
              </Card>
            ) : (
              <Card padding="lg">
                <div className="text-center py-8">
                  <ServerStackIcon className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                  <p className="text-sm text-gray-400">Select a role to see details</p>
                </div>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* User Impact Tab */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card padding="md">
              <div className="flex items-center gap-3">
                <UserGroupIcon className="h-8 w-8 text-blue-500" />
                <div>
                  <div className="text-2xl font-bold text-gray-900">{data.userImpacts.length}</div>
                  <div className="text-xs text-gray-500">Users Affected</div>
                </div>
              </div>
            </Card>
            <Card padding="md">
              <div className="flex items-center gap-3">
                <ExclamationTriangleIcon className="h-8 w-8 text-amber-500" />
                <div>
                  <div className="text-2xl font-bold text-gray-900">
                    {data.userImpacts.filter((u) => u.retrainingRequired).length}
                  </div>
                  <div className="text-xs text-gray-500">Require Retraining</div>
                </div>
              </div>
            </Card>
            <Card padding="md">
              <div className="flex items-center gap-3">
                <XCircleIcon className="h-8 w-8 text-red-500" />
                <div>
                  <div className="text-2xl font-bold text-gray-900">
                    {data.userImpacts.filter((u) => u.accessLossRisk === 'high' || u.accessLossRisk === 'critical').length}
                  </div>
                  <div className="text-xs text-gray-500">High Access Loss Risk</div>
                </div>
              </div>
            </Card>
          </div>

          <Card padding="none">
            <div className="px-6 py-4 border-b border-white/20">
              <h2 className="text-sm font-semibold text-gray-900">User Impact Assessment</h2>
            </div>
            <div className="divide-y divide-gray-100/60">
              {data.userImpacts.map((user) => (
                <div key={user.userId} className="px-6 py-4 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-900">{user.userName}</div>
                    <div className="text-xs text-gray-500">{user.department}</div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <div className="text-center">
                      <div className="text-lg font-bold text-gray-900">{user.affectedRoles}</div>
                      <div className="text-[10px] text-gray-400">Affected roles</div>
                    </div>
                    <RiskBadge level={user.accessLossRisk} />
                    {user.retrainingRequired ? (
                      <Badge variant="warning" size="sm">Retraining needed</Badge>
                    ) : (
                      <Badge variant="success" size="sm">No retraining</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Migration Plan Tab */}
      {activeTab === 'plan' && (
        <div className="space-y-4">
          {data.migrationPlan.map((phase) => {
            const cfg = phaseStatusConfig[phase.status];
            return (
              <div
                key={phase.phase}
                className={`glass-card p-5 border-l-4 ${cfg.color}`}
              >
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                        Phase {phase.phase}
                      </span>
                      <Badge
                        variant={
                          phase.status === 'completed'
                            ? 'success'
                            : phase.status === 'in_progress'
                            ? 'info'
                            : 'neutral'
                        }
                        size="sm"
                      >
                        {cfg.label}
                      </Badge>
                    </div>
                    <h3 className="text-base font-semibold text-gray-900 mt-0.5">{phase.title}</h3>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-500 flex-shrink-0">
                    <ClockIcon className="h-4 w-4" />
                    {phase.duration}
                  </div>
                </div>
                <ul className="space-y-1.5">
                  {phase.tasks.map((task, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                      {phase.status === 'completed' ? (
                        <CheckCircleIcon className={`h-4 w-4 flex-shrink-0 mt-0.5 ${cfg.iconColor}`} />
                      ) : phase.status === 'in_progress' ? (
                        <ArrowPathIcon className={`h-4 w-4 flex-shrink-0 mt-0.5 ${cfg.iconColor}`} />
                      ) : (
                        <DocumentTextIcon className={`h-4 w-4 flex-shrink-0 mt-0.5 ${cfg.iconColor}`} />
                      )}
                      {task}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
