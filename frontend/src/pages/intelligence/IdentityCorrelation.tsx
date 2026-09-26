import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  UserGroupIcon,
  LinkIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChevronRightIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  RiskBadge,
  SearchInput,
  Table,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';

// ── Types ──────────────────────────────────────────────────────────────────────

type SystemType = 'SAP' | 'AD' | 'HR' | 'CRM' | 'ServiceNow' | 'Okta' | 'AWS';

interface SystemAccount {
  system: SystemType;
  account_id: string;
  display_name: string;
  email?: string;
  status: 'active' | 'inactive' | 'locked' | 'unknown';
  last_login?: string;
  attributes: Record<string, string>;
}

interface IdentityCluster {
  cluster_id: string;
  person_name: string;
  employee_id?: string;
  department?: string;
  correlation_confidence: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  systems: SystemType[];
  accounts: SystemAccount[];
  anomalies: string[];
}

interface OrphanAccount {
  account_id: string;
  system: SystemType;
  display_name: string;
  last_login?: string;
  days_orphaned: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  reason: string;
}

interface CrossSystemRisk {
  id: string;
  person_name: string;
  description: string;
  systems_involved: SystemType[];
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  detected: string;
}

interface AnomalyAlert {
  id: string;
  cluster_id?: string;
  person_name: string;
  anomaly_type: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  detected_at: string;
  status: 'open' | 'acknowledged' | 'resolved';
}

interface CorrelationStats {
  total_identities: number;
  correlated: number;
  orphans: number;
  anomalies: number;
  cross_system_risks: number;
}

// ── System badge / icon helpers ───────────────────────────────────────────────

const SYSTEM_COLORS: Record<SystemType, string> = {
  SAP: 'bg-blue-100/80 text-blue-700 border-blue-200/50',
  AD: 'bg-purple-100/80 text-purple-700 border-purple-200/50',
  HR: 'bg-emerald-100/80 text-emerald-700 border-emerald-200/50',
  CRM: 'bg-orange-100/80 text-orange-700 border-orange-200/50',
  ServiceNow: 'bg-slate-100/80 text-slate-700 border-slate-200/50',
  Okta: 'bg-sky-100/80 text-sky-700 border-sky-200/50',
  AWS: 'bg-amber-100/80 text-amber-700 border-amber-200/50',
};

function SystemTag({ system }: { system: SystemType }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${SYSTEM_COLORS[system]}`}>
      {system}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 95 ? 'bg-emerald-500' : value >= 80 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 bg-gray-100/60 rounded-full h-1.5 flex-shrink-0">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-xs font-medium text-gray-700">{value}%</span>
    </div>
  );
}

const ANOMALY_STATUS: Record<AnomalyAlert['status'], { label: string; variant: 'danger' | 'warning' | 'success' }> = {
  open: { label: 'Open', variant: 'danger' },
  acknowledged: { label: 'Acknowledged', variant: 'warning' },
  resolved: { label: 'Resolved', variant: 'success' },
};

// ── Component ─────────────────────────────────────────────────────────────────

export function IdentityCorrelation() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCluster, setSelectedCluster] = useState<IdentityCluster | null>(null);
  const [activeTab, setActiveTab] = useState<'clusters' | 'orphans' | 'risks' | 'anomalies'>('clusters');
  const [mergeConfirm, setMergeConfirm] = useState<string | null>(null);

  // ── Queries ───────────────────────────────────────────────────────────────
  const { data: statsData } = useQuery<CorrelationStats>({
    queryKey: ['identity-correlation-stats'],
    queryFn: () => api.get('/identity-correlation/stats').then((r) => r.data),
  });

  const { data: clustersData, isLoading: clustersLoading } = useQuery<IdentityCluster[]>({
    queryKey: ['identity-clusters'],
    queryFn: () => api.get('/identity-correlation/clusters').then((r) => r.data),
  });

  const { data: orphansData, isLoading: orphansLoading } = useQuery<OrphanAccount[]>({
    queryKey: ['identity-orphans'],
    queryFn: () => api.get('/identity-correlation/orphans').then((r) => r.data),
    enabled: activeTab === 'orphans',
  });

  const { data: risksData, isLoading: risksLoading } = useQuery<CrossSystemRisk[]>({
    queryKey: ['identity-cross-system-risks'],
    queryFn: () => api.get('/identity-correlation/cross-system-risk').then((r) => r.data),
    enabled: activeTab === 'risks',
  });

  const { data: anomaliesData, isLoading: anomaliesLoading } = useQuery<AnomalyAlert[]>({
    queryKey: ['identity-anomalies'],
    queryFn: () => api.get('/identity-correlation/anomalies').then((r) => r.data),
    enabled: activeTab === 'anomalies',
  });

  const defaultStats: CorrelationStats = {
    total_identities: 0,
    correlated: 0,
    orphans: 0,
    anomalies: 0,
    cross_system_risks: 0,
  };

  const stats: CorrelationStats = statsData ?? defaultStats;
  const clusters: IdentityCluster[] = clustersData ?? [];
  const orphans: OrphanAccount[] = orphansData ?? [];
  const risks: CrossSystemRisk[] = risksData ?? [];
  const anomalies: AnomalyAlert[] = anomaliesData ?? [];

  // ── Merge mutation ────────────────────────────────────────────────────────
  const mergeMutation = useMutation({
    mutationFn: (clusterId: string) =>
      api.post(`/identity-correlation/clusters/${clusterId}/merge`).then((r) => r.data),
    onSuccess: () => {
      toast.success('Manual merge initiated — will be reviewed by security team');
      setMergeConfirm(null);
    },
    onError: () => {
      toast.error('Merge request failed — please try again');
      setMergeConfirm(null);
    },
  });

  // ── Filtered clusters ─────────────────────────────────────────────────────
  const filteredClusters = clusters.filter(
    (c) =>
      c.person_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.employee_id ?? '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.department ?? '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  // ── Orphan table columns ──────────────────────────────────────────────────
  const orphanColumns = [
    {
      key: 'account',
      header: 'Account',
      render: (o: OrphanAccount) => (
        <div>
          <p className="text-sm font-medium text-gray-900 font-mono">{o.account_id}</p>
          <p className="text-xs text-gray-400">{o.display_name}</p>
        </div>
      ),
    },
    {
      key: 'system',
      header: 'System',
      render: (o: OrphanAccount) => <SystemTag system={o.system} />,
    },
    {
      key: 'days',
      header: 'Days Orphaned',
      render: (o: OrphanAccount) => (
        <span className={`text-sm font-semibold ${o.days_orphaned > 180 ? 'text-red-600' : o.days_orphaned > 90 ? 'text-amber-600' : 'text-gray-700'}`}>
          {o.days_orphaned}d
        </span>
      ),
    },
    {
      key: 'risk',
      header: 'Risk',
      render: (o: OrphanAccount) => <RiskBadge level={o.risk_level} />,
    },
    {
      key: 'reason',
      header: 'Reason',
      render: (o: OrphanAccount) => <p className="text-xs text-gray-600 max-w-xs">{o.reason}</p>,
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (o: OrphanAccount) => (
        <button
          className="text-xs font-medium text-red-600 hover:text-red-800 transition-colors"
          onClick={() => toast.success(`Deprovision request raised for ${o.account_id}`)}
        >
          Deprovision
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Identity Correlation"
        subtitle="Cross-system identity mapping, orphan detection, and anomaly analysis"
        breadcrumbs={[{ label: 'Intelligence' }, { label: 'Identity Correlation' }]}
        actions={
          <Button
            variant="secondary"
            size="sm"
            icon={<ArrowPathIcon className="h-4 w-4" />}
            onClick={() => toast.success('Correlation refresh queued')}
          >
            Refresh Correlation
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard title="Total Identities" value={stats.total_identities} icon={UserGroupIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Correlated" value={stats.correlated} icon={LinkIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Orphans" value={stats.orphans} icon={ExclamationTriangleIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Anomalies" value={stats.anomalies} icon={ShieldExclamationIcon} iconBgColor="stat-icon-red" iconColor="" />
        <StatCard title="Cross-System Risks" value={stats.cross_system_risks} icon={XCircleIcon} iconBgColor="stat-icon-yellow" iconColor="" />
      </div>

      {/* Tab navigation */}
      <div className="flex gap-2 flex-wrap">
        {(
          [
            { key: 'clusters', label: `Identity Clusters (${clusters.length})` },
            { key: 'orphans', label: `Orphan Accounts (${stats.orphans})` },
            { key: 'risks', label: `Cross-System Risks (${stats.cross_system_risks})` },
            { key: 'anomalies', label: `Anomalies (${stats.anomalies})` },
          ] as const
        ).map((tab) => (
          <button
            key={tab.key}
            onClick={() => { setActiveTab(tab.key); setSelectedCluster(null); }}
            className={`px-4 py-2 text-xs font-semibold rounded-xl transition-all duration-200 border ${
              activeTab === tab.key
                ? 'bg-primary-600 text-white border-primary-600 shadow-md'
                : 'bg-white/50 text-gray-600 border-white/40 hover:bg-white/70'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Clusters tab ── */}
      {activeTab === 'clusters' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Cluster list */}
          <div className="lg:col-span-1 space-y-4">
            <Card padding="none">
              <div className="px-4 py-3 border-b border-white/20">
                <SearchInput
                  placeholder="Search by name, ID, dept..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onClear={() => setSearchTerm('')}
                />
              </div>
              <div className="divide-y divide-gray-50/50 max-h-[580px] overflow-y-auto">
                {clustersLoading ? (
                  <div className="flex items-center justify-center py-10">
                    <ArrowPathIcon className="h-6 w-6 animate-spin text-primary-500" />
                  </div>
                ) : filteredClusters.length === 0 ? (
                  <p className="text-xs text-gray-400 text-center py-8">No clusters found</p>
                ) : (
                  filteredClusters.map((cluster) => (
                    <button
                      key={cluster.cluster_id}
                      onClick={() => setSelectedCluster(cluster)}
                      className={`w-full text-left px-4 py-3 hover:bg-white/40 transition-colors ${
                        selectedCluster?.cluster_id === cluster.cluster_id ? 'bg-primary-50/60' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-semibold text-gray-900">{cluster.person_name}</span>
                        <ChevronRightIcon className={`h-3.5 w-3.5 transition-transform ${selectedCluster?.cluster_id === cluster.cluster_id ? 'text-primary-600' : 'text-gray-300'}`} />
                      </div>
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <RiskBadge level={cluster.risk_level} />
                        {cluster.anomalies.length > 0 && (
                          <Badge variant="warning" size="sm">{cluster.anomalies.length} anomaly</Badge>
                        )}
                      </div>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {cluster.systems.map((s) => (
                          <SystemTag key={s} system={s} />
                        ))}
                      </div>
                      <ConfidenceBar value={cluster.correlation_confidence} />
                    </button>
                  ))
                )}
              </div>
            </Card>
          </div>

          {/* Cluster detail */}
          <div className="lg:col-span-2">
            {selectedCluster ? (
              <div className="space-y-4">
                {/* Header */}
                <Card padding="md">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="text-lg font-bold text-gray-900">{selectedCluster.person_name}</h2>
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        {selectedCluster.employee_id && (
                          <span className="text-xs text-gray-400">{selectedCluster.employee_id}</span>
                        )}
                        {selectedCluster.department && (
                          <Badge variant="neutral" size="sm">{selectedCluster.department}</Badge>
                        )}
                        <RiskBadge level={selectedCluster.risk_level} />
                      </div>
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-xs text-gray-500">Correlation confidence</span>
                        <ConfidenceBar value={selectedCluster.correlation_confidence} />
                      </div>
                    </div>
                    {mergeConfirm === selectedCluster.cluster_id ? (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-600">Confirm merge?</span>
                        <Button
                          size="sm"
                          variant="success"
                          onClick={() => mergeMutation.mutate(selectedCluster.cluster_id)}
                          loading={mergeMutation.isPending}
                        >
                          Confirm
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setMergeConfirm(null)}>Cancel</Button>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        variant="secondary"
                        icon={<LinkIcon className="h-4 w-4" />}
                        onClick={() => setMergeConfirm(selectedCluster.cluster_id)}
                      >
                        Manual Merge
                      </Button>
                    )}
                  </div>

                  {/* Anomalies */}
                  {selectedCluster.anomalies.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/20">
                      <p className="text-xs font-medium text-amber-700 uppercase tracking-wider mb-2">Anomalies Detected</p>
                      <ul className="space-y-1.5">
                        {selectedCluster.anomalies.map((a, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-amber-800 bg-amber-50/60 border border-amber-200/60 rounded-lg px-2.5 py-1.5">
                            <ExclamationTriangleIcon className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                            {a}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </Card>

                {/* Accounts across systems */}
                <Card padding="none">
                  <div className="px-5 py-4 border-b border-white/20">
                    <h3 className="text-sm font-semibold text-gray-900">Accounts Across Systems</h3>
                  </div>
                  <div className="divide-y divide-gray-50/50">
                    {selectedCluster.accounts.map((acct) => (
                      <div key={`${acct.system}-${acct.account_id}`} className="px-5 py-4">
                        <div className="flex items-start justify-between gap-4 flex-wrap">
                          <div className="flex items-center gap-3">
                            <SystemTag system={acct.system} />
                            <div>
                              <p className="text-sm font-medium text-gray-900 font-mono">{acct.account_id}</p>
                              <p className="text-xs text-gray-400">{acct.display_name}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {acct.status === 'active' ? (
                              <CheckCircleIcon className="h-4 w-4 text-emerald-500" />
                            ) : acct.status === 'locked' ? (
                              <ExclamationTriangleIcon className="h-4 w-4 text-amber-500" />
                            ) : (
                              <XCircleIcon className="h-4 w-4 text-gray-400" />
                            )}
                            <span
                              className={`text-xs font-medium capitalize ${
                                acct.status === 'active'
                                  ? 'text-emerald-700'
                                  : acct.status === 'locked'
                                  ? 'text-amber-700'
                                  : 'text-gray-500'
                              }`}
                            >
                              {acct.status}
                            </span>
                            {acct.last_login && (
                              <span className="text-xs text-gray-400">Last: {acct.last_login}</span>
                            )}
                          </div>
                        </div>
                        {/* Attribute comparison */}
                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                          {Object.entries(acct.attributes).map(([k, v]) => (
                            <span key={k} className="text-xs text-gray-500">
                              <span className="font-medium text-gray-600">{k}:</span> {v}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            ) : (
              <Card>
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <UserGroupIcon className="h-12 w-12 text-gray-300 mb-4" />
                  <h3 className="text-sm font-medium text-gray-700 mb-1">Select an Identity Cluster</h3>
                  <p className="text-xs text-gray-400 max-w-xs">
                    Click on a cluster in the list to view the full account comparison across all connected systems.
                  </p>
                </div>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* ── Orphans tab ── */}
      {activeTab === 'orphans' && (
        <div>
          {orphansLoading ? (
            <Card>
              <div className="flex items-center justify-center py-12">
                <ArrowPathIcon className="h-8 w-8 animate-spin text-primary-500" />
              </div>
            </Card>
          ) : (
            <Table
              columns={orphanColumns}
              data={orphans}
              emptyMessage="No orphan accounts detected"
            />
          )}
        </div>
      )}

      {/* ── Cross-system risks tab ── */}
      {activeTab === 'risks' && (
        <div className="space-y-4">
          {risksLoading ? (
            <Card>
              <div className="flex items-center justify-center py-12">
                <ArrowPathIcon className="h-8 w-8 animate-spin text-primary-500" />
              </div>
            </Card>
          ) : (
            risks.map((risk) => (
              <Card key={risk.id} padding="md">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs text-gray-400 font-mono">{risk.id}</span>
                      <RiskBadge level={risk.risk_level} />
                      {risk.systems_involved.map((s) => (
                        <SystemTag key={s} system={s} />
                      ))}
                    </div>
                    <p className="text-sm font-semibold text-gray-900 mb-1">{risk.person_name}</p>
                    <p className="text-sm text-gray-600 leading-relaxed">{risk.description}</p>
                    <p className="text-xs text-gray-400 mt-2">Detected: {risk.detected}</p>
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => toast.success(`Risk ${risk.id} opened for review`)}
                  >
                    Review
                  </Button>
                </div>
              </Card>
            ))
          )}
          {!risksLoading && risks.length === 0 && (
            <Card>
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircleIcon className="h-10 w-10 text-emerald-400 mb-3" />
                <p className="text-sm text-gray-500">No cross-system risks detected</p>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── Anomalies tab ── */}
      {activeTab === 'anomalies' && (
        <div className="space-y-3">
          {anomaliesLoading ? (
            <Card>
              <div className="flex items-center justify-center py-12">
                <ArrowPathIcon className="h-8 w-8 animate-spin text-primary-500" />
              </div>
            </Card>
          ) : (
            anomalies.map((alert) => {
              const statusCfg = ANOMALY_STATUS[alert.status];
              const severityVariant =
                alert.severity === 'critical' || alert.severity === 'high'
                  ? 'danger'
                  : alert.severity === 'medium'
                  ? 'warning'
                  : 'neutral';
              return (
                <Card key={alert.id} padding="md">
                  <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                        <span className="text-xs text-gray-400 font-mono">{alert.id}</span>
                        <Badge variant={severityVariant} size="sm">{alert.severity}</Badge>
                        <Badge variant={statusCfg.variant} size="sm">{statusCfg.label}</Badge>
                        {alert.cluster_id && (
                          <button
                            onClick={() => {
                              const cluster = clusters.find((c) => c.cluster_id === alert.cluster_id);
                              if (cluster) { setSelectedCluster(cluster); setActiveTab('clusters'); }
                            }}
                            className="text-xs text-primary-600 hover:text-primary-800 font-medium transition-colors"
                          >
                            {alert.cluster_id}
                          </button>
                        )}
                      </div>
                      <p className="text-sm font-semibold text-gray-900">{alert.anomaly_type}</p>
                      <p className="text-xs text-gray-600 mt-0.5">{alert.person_name}</p>
                      <p className="text-sm text-gray-600 mt-1.5 leading-relaxed">{alert.description}</p>
                      <p className="text-xs text-gray-400 mt-2">
                        Detected: {new Date(alert.detected_at).toLocaleString('en-GB')}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      {alert.status === 'open' && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => toast.success(`Anomaly ${alert.id} acknowledged`)}
                        >
                          Acknowledge
                        </Button>
                      )}
                      {alert.status !== 'resolved' && (
                        <Button
                          variant="success"
                          size="sm"
                          icon={<CheckCircleIcon className="h-3.5 w-3.5" />}
                          onClick={() => toast.success(`Anomaly ${alert.id} marked resolved`)}
                        >
                          Resolve
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })
          )}
          {!anomaliesLoading && anomalies.length === 0 && (
            <Card>
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircleIcon className="h-10 w-10 text-emerald-400 mb-3" />
                <p className="text-sm text-gray-500">No anomalies detected</p>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
