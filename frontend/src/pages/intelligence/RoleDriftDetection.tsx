import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowPathIcon,
  ArrowDownTrayIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ServerStackIcon,
  ShieldExclamationIcon,
  MagnifyingGlassIcon,
  ArrowsRightLeftIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  Select,
} from '../../components/ui';

// ============================================================================
// Types
// ============================================================================

type DriftSeverity = 'none' | 'minor' | 'critical';
type DriftType = 'auth_value' | 'org_level' | 'transport' | 'missing_object' | 'none';

interface SystemHash {
  system: string;
  hash: string;
  lastChecked: string;
}

interface DriftResult {
  id: string;
  roleId: string;
  roleName: string;
  processArea: string;
  hashes: {
    dev: string;
    qa: string;
    prod: string;
  };
  severity: DriftSeverity;
  driftType: DriftType;
  driftedSystems: string[];
}

interface DriftDetail {
  field: string;
  system: string;
  expected: string;
  actual: string;
  type: 'missing' | 'different' | 'extra';
}

interface RoleDriftData {
  totalMonitored: number;
  driftedRoles: number;
  criticalDrifts: number;
  systemsCompared: number;
  systems: SystemHash[];
  driftResults: DriftResult[];
  driftDetails: Record<string, DriftDetail[]>;
}

// ============================================================================
// Helpers
// ============================================================================

const severityConfig: Record<
  DriftSeverity,
  { label: string; variant: 'success' | 'warning' | 'danger'; rowClass: string }
> = {
  none: { label: 'Aligned', variant: 'success', rowClass: '' },
  minor: { label: 'Minor Drift', variant: 'warning', rowClass: 'bg-amber-50/30' },
  critical: { label: 'Critical Drift', variant: 'danger', rowClass: 'bg-red-50/30' },
};

const driftTypeLabel: Record<DriftType, string> = {
  none: 'None',
  auth_value: 'Auth Value Mismatch',
  org_level: 'Org Level Mismatch',
  transport: 'Transport Gap',
  missing_object: 'Missing Object',
};

const detailTypeConfig: Record<
  DriftDetail['type'],
  { label: string; color: string }
> = {
  missing: { label: 'Missing', color: 'text-red-700 bg-red-50 border-red-200' },
  different: { label: 'Different', color: 'text-amber-700 bg-amber-50 border-amber-200' },
  extra: { label: 'Extra', color: 'text-blue-700 bg-blue-50 border-blue-200' },
};

function hashCell(hash: string, referenceHash: string, systemLabel: string) {
  const matches = hash === referenceHash;
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${
          matches ? 'bg-emerald-500' : 'bg-red-500'
        }`}
      />
      <span
        className={`text-xs font-mono ${
          matches ? 'text-gray-600' : 'text-red-700 font-semibold'
        }`}
        title={`${systemLabel}: ${hash}`}
      >
        {hash.slice(0, 8)}
      </span>
    </div>
  );
}

// ============================================================================
// Component
// ============================================================================

export function RoleDriftDetection() {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [driftTypeFilter, setDriftTypeFilter] = useState<string>('all');
  const [selectedRole, setSelectedRole] = useState<DriftResult | null>(null);
  const [compareA, setCompareA] = useState<string>('DEV');
  const [compareB, setCompareB] = useState<string>('PROD');
  const [isScanning, setIsScanning] = useState(false);

  const { data: driftData, refetch } = useQuery<RoleDriftData>({
    queryKey: ['role-drift'],
    queryFn: () =>
      api
        .get('/drift/summary')
        .then((res) => res.data)
        .catch(() => ({ totalMonitored: 0, driftedRoles: 0, criticalDrifts: 0, systemsCompared: 0, systems: [], driftResults: [], driftDetails: {} } as RoleDriftData)),
  });

  const data = driftData ?? { totalMonitored: 0, driftedRoles: 0, criticalDrifts: 0, systemsCompared: 0, systems: [], driftResults: [], driftDetails: {} } as RoleDriftData;

  const handleScan = async () => {
    setIsScanning(true);
    try {
      await refetch();
      toast.success('Role drift scan complete');
    } catch {
      toast.error('Scan failed');
    } finally {
      setIsScanning(false);
    }
  };

  const handleExport = () => {
    const rows = data.driftResults.map((r) => [
      r.roleId,
      r.roleName,
      r.processArea,
      r.hashes.dev,
      r.hashes.qa,
      r.hashes.prod,
      r.severity,
      driftTypeLabel[r.driftType],
      r.driftedSystems.join('; '),
    ]);
    const headers = ['Role ID', 'Role Name', 'Process Area', 'DEV Hash', 'QA Hash', 'PROD Hash', 'Severity', 'Drift Type', 'Drifted Systems'];
    const csv = [headers, ...rows].map((r) => r.map((c) => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `role_drift_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
    toast.success('Drift report exported');
  };

  const filteredResults = data.driftResults.filter((r) => {
    const matchesSearch =
      r.roleId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.roleName.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSeverity = severityFilter === 'all' || r.severity === severityFilter;
    const matchesType = driftTypeFilter === 'all' || r.driftType === driftTypeFilter;
    return matchesSearch && matchesSeverity && matchesType;
  });

  const comparisonResults = data.driftResults.filter((r) => {
    const hashA = r.hashes[compareA.toLowerCase() as 'dev' | 'qa' | 'prod'];
    const hashB = r.hashes[compareB.toLowerCase() as 'dev' | 'qa' | 'prod'];
    return hashA !== hashB;
  });

  const systemOptions = [
    { value: 'DEV', label: 'DEV' },
    { value: 'QA', label: 'QA' },
    { value: 'PROD', label: 'PROD' },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Role Drift Detection"
        subtitle="Cross-system role comparison between DEV, QA, and PROD to detect unauthorized changes"
        breadcrumbs={[{ label: 'Intelligence' }, { label: 'Role Drift Detection' }]}
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
              icon={<ArrowPathIcon className={`h-4 w-4 ${isScanning ? 'animate-spin' : ''}`} />}
              loading={isScanning}
              onClick={handleScan}
            >
              Run Scan
            </Button>
          </div>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Roles Monitored"
          value={data.totalMonitored}
          icon={ServerStackIcon}
          iconBgColor="stat-icon-blue"
          iconColor=""
        />
        <StatCard
          title="Drifted Roles"
          value={data.driftedRoles}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-yellow"
          iconColor=""
        />
        <StatCard
          title="Critical Drifts"
          value={data.criticalDrifts}
          icon={ShieldExclamationIcon}
          iconBgColor="stat-icon-red"
          iconColor=""
        />
        <StatCard
          title="Systems Compared"
          value={data.systemsCompared}
          icon={ArrowsRightLeftIcon}
          iconBgColor="stat-icon-green"
          iconColor=""
        />
      </div>

      {/* System Status + Comparison Selector */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* System Status */}
        <Card padding="none">
          <div className="px-6 py-4 border-b border-white/20">
            <h2 className="text-sm font-semibold text-gray-900">System Sync Status</h2>
          </div>
          <div className="p-5 space-y-3">
            {data.systems.map((sys) => (
              <div
                key={sys.system}
                className="flex items-center justify-between py-2 border-b border-gray-100/60 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center">
                    <ServerStackIcon className="h-4 w-4 text-blue-600" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-gray-900">{sys.system}</div>
                    <div className="text-[10px] text-gray-400">Last checked: {sys.lastChecked}</div>
                  </div>
                </div>
                <span className="text-xs font-mono text-gray-500">{sys.hash.slice(0, 12)}...</span>
              </div>
            ))}
          </div>
        </Card>

        {/* System Comparison Selector */}
        <Card padding="none">
          <div className="px-6 py-4 border-b border-white/20">
            <h2 className="text-sm font-semibold text-gray-900">System Comparison</h2>
          </div>
          <div className="p-5">
            <div className="flex items-center gap-3 mb-4">
              <Select
                value={compareA}
                onChange={(e) => setCompareA(e.target.value)}
                options={systemOptions.filter((o) => o.value !== compareB)}
              />
              <ArrowsRightLeftIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
              <Select
                value={compareB}
                onChange={(e) => setCompareB(e.target.value)}
                options={systemOptions.filter((o) => o.value !== compareA)}
              />
            </div>
            <div className="rounded-xl bg-gray-50/80 border border-gray-200/60 p-4">
              <div className="text-xs text-gray-500 mb-3 font-medium">
                {comparisonResults.length} role{comparisonResults.length !== 1 ? 's' : ''} differ between {compareA} and {compareB}
              </div>
              {comparisonResults.length === 0 ? (
                <div className="flex items-center gap-2 text-green-700 text-sm">
                  <CheckCircleIcon className="h-5 w-5" />
                  Systems are fully aligned
                </div>
              ) : (
                <div className="space-y-2 max-h-36 overflow-y-auto pr-1">
                  {comparisonResults.map((r) => (
                    <div
                      key={r.id}
                      className="flex items-center justify-between text-xs"
                    >
                      <span className="font-mono text-gray-700">{r.roleId}</span>
                      <Badge
                        variant={severityConfig[r.severity].variant}
                        size="sm"
                      >
                        {severityConfig[r.severity].label}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search by role ID or name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200/80 rounded-xl bg-white/60 focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent"
              />
            </div>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Severities' },
                { value: 'critical', label: 'Critical Drift' },
                { value: 'minor', label: 'Minor Drift' },
                { value: 'none', label: 'Aligned' },
              ]}
            />
            <Select
              value={driftTypeFilter}
              onChange={(e) => setDriftTypeFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Drift Types' },
                { value: 'auth_value', label: 'Auth Value Mismatch' },
                { value: 'org_level', label: 'Org Level Mismatch' },
                { value: 'transport', label: 'Transport Gap' },
                { value: 'missing_object', label: 'Missing Object' },
              ]}
            />
          </div>
        </div>
      </Card>

      {/* Main Content: Table + Drill-down */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Drift Scan Table */}
        <div className="lg:col-span-2">
          <Card padding="none">
            <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-900">
                Drift Scan Results ({filteredResults.length})
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-gray-100/60">
                    <th className="px-5 py-3 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Role</th>
                    <th className="px-4 py-3 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider">DEV</th>
                    <th className="px-4 py-3 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider">QA</th>
                    <th className="px-4 py-3 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider">PROD</th>
                    <th className="px-4 py-3 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Type</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50/80">
                  {filteredResults.map((result) => {
                    const cfg = severityConfig[result.severity];
                    const isSelected = selectedRole?.id === result.id;
                    return (
                      <tr
                        key={result.id}
                        onClick={() => setSelectedRole(isSelected ? null : result)}
                        className={`cursor-pointer transition-colors ${cfg.rowClass} ${
                          isSelected
                            ? 'ring-2 ring-inset ring-primary-300 bg-primary-50/40'
                            : 'hover:bg-gray-50/60'
                        }`}
                      >
                        <td className="px-5 py-3">
                          <div className="text-xs font-mono font-semibold text-gray-900">{result.roleId}</div>
                          <div className="text-[10px] text-gray-500 mt-0.5">{result.roleName}</div>
                        </td>
                        <td className="px-4 py-3">
                          {hashCell(result.hashes.dev, result.hashes.dev, 'DEV')}
                        </td>
                        <td className="px-4 py-3">
                          {hashCell(result.hashes.qa, result.hashes.dev, 'QA')}
                        </td>
                        <td className="px-4 py-3">
                          {hashCell(result.hashes.prod, result.hashes.dev, 'PROD')}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={cfg.variant} size="sm">
                            {cfg.label}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs text-gray-500">{driftTypeLabel[result.driftType]}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {filteredResults.length === 0 && (
                <div className="py-12 text-center">
                  <CheckCircleIcon className="h-10 w-10 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-400">No drift results match your filters</p>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Drill-down Panel */}
        <div>
          {selectedRole ? (
            <Card padding="none">
              <div className="px-5 py-4 border-b border-white/20">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">Drift Details</h3>
                    <p className="text-xs font-mono text-gray-500 mt-0.5">{selectedRole.roleId}</p>
                  </div>
                  <Badge variant={severityConfig[selectedRole.severity].variant} size="sm">
                    {severityConfig[selectedRole.severity].label}
                  </Badge>
                </div>
              </div>
              <div className="p-5 space-y-4">
                {/* Hash comparison */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Hash Comparison</h4>
                  {(['dev', 'qa', 'prod'] as const).map((sys) => {
                    const hash = selectedRole.hashes[sys];
                    const matches = hash === selectedRole.hashes.dev;
                    return (
                      <div
                        key={sys}
                        className={`flex items-center justify-between px-3 py-2 rounded-lg border text-xs ${
                          matches || sys === 'dev'
                            ? 'border-emerald-200 bg-emerald-50/60'
                            : 'border-red-200 bg-red-50/60'
                        }`}
                      >
                        <span className="font-semibold text-gray-700 uppercase">{sys}</span>
                        <span className={`font-mono ${matches || sys === 'dev' ? 'text-emerald-700' : 'text-red-700 font-bold'}`}>
                          {hash}
                        </span>
                        {sys === 'dev' ? (
                          <Badge variant="neutral" size="sm">Reference</Badge>
                        ) : matches ? (
                          <CheckCircleIcon className="h-4 w-4 text-emerald-500" />
                        ) : (
                          <XCircleIcon className="h-4 w-4 text-red-500" />
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Field-level differences */}
                {data.driftDetails[selectedRole.id] ? (
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      Field Differences ({data.driftDetails[selectedRole.id].length})
                    </h4>
                    {data.driftDetails[selectedRole.id].map((detail, i) => {
                      const cfg = detailTypeConfig[detail.type];
                      return (
                        <div key={i} className="rounded-lg border border-gray-200/60 overflow-hidden">
                          <div className="px-3 py-2 bg-gray-50/80 flex items-center justify-between">
                            <span className="text-xs font-mono font-semibold text-gray-700">{detail.field}</span>
                            <div className="flex items-center gap-1.5">
                              <Badge variant="neutral" size="sm">{detail.system}</Badge>
                              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full border ${cfg.color}`}>
                                {cfg.label}
                              </span>
                            </div>
                          </div>
                          <div className="px-3 py-2 space-y-1 text-xs">
                            <div className="flex justify-between gap-2">
                              <span className="text-gray-400 flex-shrink-0">Expected:</span>
                              <span className="font-mono text-green-700 text-right break-all">{detail.expected}</span>
                            </div>
                            <div className="flex justify-between gap-2">
                              <span className="text-gray-400 flex-shrink-0">Actual:</span>
                              <span className="font-mono text-red-700 text-right break-all">{detail.actual}</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <CheckCircleIcon className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
                    <p className="text-xs text-gray-400">No field-level differences found</p>
                  </div>
                )}

                <Button
                  variant="secondary"
                  size="sm"
                  fullWidth
                  onClick={() => toast.success(`Opening transport request for ${selectedRole.roleId}...`)}
                >
                  Create Transport Request
                </Button>
              </div>
            </Card>
          ) : (
            <Card padding="lg">
              <div className="text-center py-8">
                <ArrowsRightLeftIcon className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500 font-medium">Select a role to inspect</p>
                <p className="text-xs text-gray-400 mt-1">Click any row to see field-level differences</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
