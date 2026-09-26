import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ShieldCheckIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ClockIcon,
  PauseCircleIcon,
  ArrowPathIcon,
  CalendarDaysIcon,
  ChartPieIcon,
  BellAlertIcon,
} from '@heroicons/react/24/outline';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  Table,
  SearchInput,
  Select,
} from '../../components/ui';
import { api } from '../../services/api';

// ─── Types ────────────────────────────────────────────────────────────────────

type ControlStatus = 'active' | 'expiring' | 'expired' | 'suspended';
type ControlType =
  | 'Preventive'
  | 'Detective'
  | 'Corrective'
  | 'Compensating'
  | 'Manual';

interface MitigationControl {
  id: string;
  name: string;
  type: ControlType;
  status: ControlStatus;
  assignedViolations: number;
  expiryDate: string;
  healthScore: number;
  lastReviewed: string;
  owner: string;
  description: string;
}

interface ControlStats {
  total: number;
  healthy: number;
  expiringSoon: number;
  expired: number;
  suspended: number;
  healthScore: number;
}

interface ExpiringControl {
  id: string;
  name: string;
  expiryDate: string;
  daysUntilExpiry: number;
  status: ControlStatus;
}

// Effectiveness data for pie chart
const EFFECTIVENESS_DATA = [
  { label: 'Effective', value: 5, color: '#22c55e', pct: 50 },
  { label: 'Partially Effective', value: 3, color: '#f59e0b', pct: 30 },
  { label: 'Ineffective', value: 2, color: '#ef4444', pct: 20 },
];

// ─── API helpers ──────────────────────────────────────────────────────────────

const mitigationApi = {
  listControls: () =>
    api
      .get('/mitigation-monitoring/')
      .then((r) => r.data)
      .catch(() => []),

  getExpiring: () =>
    api
      .get('/mitigation-monitoring/expiring')
      .then((r) => r.data)
      .catch(() => []),

  getStats: () =>
    api
      .get('/mitigation-monitoring/stats')
      .then((r) => r.data)
      .catch(() => null),

  recertify: (controlId: string) =>
    api
      .post(`/mitigation-monitoring/${controlId}/recertify`)
      .then((r) => r.data),
};

// ─── Sub-components ───────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  ControlStatus,
  { label: string; variant: 'success' | 'warning' | 'danger' | 'neutral'; icon: React.ElementType }
> = {
  active: { label: 'Active', variant: 'success', icon: CheckCircleIcon },
  expiring: { label: 'Expiring Soon', variant: 'warning', icon: ClockIcon },
  expired: { label: 'Expired', variant: 'danger', icon: XCircleIcon },
  suspended: { label: 'Suspended', variant: 'neutral', icon: PauseCircleIcon },
};

function StatusBadgeControl({ status }: { status: ControlStatus }) {
  const cfg = STATUS_CONFIG[status];
  const Icon = cfg.icon;
  return (
    <Badge variant={cfg.variant} size="sm">
      <Icon className="h-3 w-3 mr-1 inline-block" />
      {cfg.label}
    </Badge>
  );
}

function HealthBar({ score }: { score: number }) {
  const color =
    score >= 80
      ? 'bg-green-500'
      : score >= 50
      ? 'bg-amber-500'
      : 'bg-red-500';

  return (
    <div className="flex items-center gap-2 min-w-[110px]">
      <div className="flex-1 bg-gray-100/60 rounded-full h-2 backdrop-blur-sm">
        <div
          className={`${color} h-2 rounded-full transition-all duration-500`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-xs font-medium text-gray-700 w-8 text-right">{score}%</span>
    </div>
  );
}

function SimplePieChart() {
  // Manual SVG pie — no external library needed
  const total = EFFECTIVENESS_DATA.reduce((s, d) => s + d.value, 0);
  let cumulative = 0;
  const segments = EFFECTIVENESS_DATA.map((d) => {
    const startAngle = (cumulative / total) * 360;
    cumulative += d.value;
    const endAngle = (cumulative / total) * 360;
    return { ...d, startAngle, endAngle };
  });

  const polarToCartesian = (cx: number, cy: number, r: number, angleDeg: number) => {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  };

  const arcPath = (cx: number, cy: number, r: number, start: number, end: number) => {
    const s = polarToCartesian(cx, cy, r, start);
    const e = polarToCartesian(cx, cy, r, end);
    const large = end - start > 180 ? 1 : 0;
    return `M ${cx} ${cy} L ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y} Z`;
  };

  return (
    <div className="flex items-center gap-6">
      <svg width="120" height="120" viewBox="0 0 120 120">
        {segments.map((seg, i) => (
          <path
            key={i}
            d={arcPath(60, 60, 52, seg.startAngle, seg.endAngle)}
            fill={seg.color}
            stroke="white"
            strokeWidth="2"
          />
        ))}
        <circle cx="60" cy="60" r="24" fill="white" />
        <text x="60" y="65" textAnchor="middle" className="text-xs" fontSize="11" fontWeight="600" fill="#374151">
          {total}
        </text>
      </svg>
      <div className="space-y-2">
        {EFFECTIVENESS_DATA.map((d) => (
          <div key={d.label} className="flex items-center gap-2">
            <span
              className="inline-block w-3 h-3 rounded-sm flex-shrink-0"
              style={{ backgroundColor: d.color }}
            />
            <span className="text-xs text-gray-600">{d.label}</span>
            <span className="text-xs font-semibold text-gray-800 ml-auto pl-4">{d.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ExpiryTimeline({ items }: { items: ExpiringControl[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-gray-500 py-4 text-center">No upcoming expirations</p>;
  }

  return (
    <div className="relative">
      <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200/80" />
      <div className="space-y-4 pl-10">
        {items.map((ctrl) => {
          const isOverdue = ctrl.daysUntilExpiry < 0;
          const isUrgent = ctrl.daysUntilExpiry >= 0 && ctrl.daysUntilExpiry <= 7;
          const dotColor = isOverdue ? 'bg-red-500' : isUrgent ? 'bg-amber-500' : 'bg-yellow-400';
          const textColor = isOverdue ? 'text-red-700' : isUrgent ? 'text-amber-700' : 'text-yellow-700';
          const bgColor = isOverdue
            ? 'bg-red-50/80 border-red-200/60'
            : isUrgent
            ? 'bg-amber-50/80 border-amber-200/60'
            : 'bg-yellow-50/80 border-yellow-200/60';

          return (
            <div key={ctrl.id} className="relative">
              <div
                className={`absolute -left-6 top-3 w-3 h-3 rounded-full border-2 border-white ${dotColor}`}
              />
              <div className={`p-3 rounded-xl border backdrop-blur-sm ${bgColor}`}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{ctrl.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {ctrl.id} — Expires {ctrl.expiryDate}
                    </p>
                  </div>
                  <span className={`text-xs font-semibold ${textColor} whitespace-nowrap`}>
                    {isOverdue
                      ? `${Math.abs(ctrl.daysUntilExpiry)}d overdue`
                      : ctrl.daysUntilExpiry === 0
                      ? 'Today'
                      : `${ctrl.daysUntilExpiry}d left`}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function MitigationMonitoring() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');

  const { data: controlsData, isLoading: controlsLoading } = useQuery<MitigationControl[]>({
    queryKey: ['mitigation-controls', statusFilter, typeFilter],
    queryFn: () => mitigationApi.listControls(),
  });

  const { data: statsData } = useQuery<ControlStats | null>({
    queryKey: ['mitigation-stats'],
    queryFn: () => mitigationApi.getStats(),
  });

  const { data: expiringData } = useQuery<ExpiringControl[]>({
    queryKey: ['mitigation-expiring'],
    queryFn: () => mitigationApi.getExpiring(),
  });

  const recertifyMutation = useMutation({
    mutationFn: (controlId: string) => mitigationApi.recertify(controlId),
    onSuccess: (_data, controlId) => {
      toast.success(`Control ${controlId} recertified successfully`);
      queryClient.invalidateQueries({ queryKey: ['mitigation-controls'] });
      queryClient.invalidateQueries({ queryKey: ['mitigation-stats'] });
      queryClient.invalidateQueries({ queryKey: ['mitigation-expiring'] });
    },
    onError: (_err, controlId) => {
      toast.error(`Failed to recertify control ${controlId}. Please try again.`);
    },
  });

  const defaultStats: ControlStats = {
    total: 0,
    healthy: 0,
    expiringSoon: 0,
    expired: 0,
    suspended: 0,
    healthScore: 0,
  };

  const controls: MitigationControl[] = controlsData || [];
  const stats: ControlStats = statsData || defaultStats;
  const expiring: ExpiringControl[] = expiringData || [];

  const urgentExpiring = expiring.filter((c) => c.daysUntilExpiry <= 7 && c.daysUntilExpiry >= 0);

  const filteredControls = controls.filter((c) => {
    const matchesSearch =
      c.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.owner.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || c.status === statusFilter;
    const matchesType = typeFilter === 'all' || c.type === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  const columns = [
    {
      key: 'id',
      header: 'Control ID',
      render: (c: MitigationControl) => (
        <div>
          <div className="text-sm font-medium text-primary-600">{c.id}</div>
          <div className="text-xs text-gray-400 max-w-xs truncate">{c.description}</div>
        </div>
      ),
    },
    {
      key: 'name',
      header: 'Name',
      render: (c: MitigationControl) => (
        <div>
          <div className="text-sm font-medium text-gray-900">{c.name}</div>
          <div className="text-xs text-gray-400">{c.owner}</div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (c: MitigationControl) => (
        <Badge variant="neutral" size="sm">{c.type}</Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (c: MitigationControl) => <StatusBadgeControl status={c.status} />,
    },
    {
      key: 'violations',
      header: 'Violations',
      render: (c: MitigationControl) => (
        <span className="text-sm font-semibold text-gray-700">{c.assignedViolations}</span>
      ),
    },
    {
      key: 'expiry',
      header: 'Expiry Date',
      render: (c: MitigationControl) => {
        const today = new Date('2026-08-21');
        const expiry = new Date(c.expiryDate);
        const diff = Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
        const isExpired = diff < 0;
        const isUrgent = diff >= 0 && diff <= 7;
        const isExpiring = diff >= 0 && diff <= 30;
        return (
          <div>
            <div
              className={`text-sm font-medium ${
                isExpired ? 'text-red-600' : isUrgent ? 'text-amber-600' : 'text-gray-700'
              }`}
            >
              {c.expiryDate}
            </div>
            {isExpired && (
              <div className="text-xs text-red-500">{Math.abs(diff)}d overdue</div>
            )}
            {!isExpired && isExpiring && (
              <div className="text-xs text-amber-500">{diff}d remaining</div>
            )}
          </div>
        );
      },
    },
    {
      key: 'health',
      header: 'Health Score',
      render: (c: MitigationControl) => <HealthBar score={c.healthScore} />,
    },
    {
      key: 'reviewed',
      header: 'Last Reviewed',
      render: (c: MitigationControl) => (
        <span className="text-xs text-gray-500">{c.lastReviewed}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (c: MitigationControl) => (
        <div className="flex justify-end gap-2">
          <button
            onClick={() => toast.success(`Opening control ${c.id}...`)}
            className="text-xs font-medium text-primary-600 hover:text-primary-800 transition-colors"
          >
            View
          </button>
          <button
            onClick={() => recertifyMutation.mutate(c.id)}
            disabled={recertifyMutation.isPending}
            className="text-xs font-medium text-green-600 hover:text-green-800 transition-colors disabled:opacity-50"
          >
            Recertify
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mitigation Control Monitoring"
        subtitle="Track health, effectiveness, and expiry status of all active mitigating controls"
        actions={
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              icon={<ArrowPathIcon className="h-4 w-4" />}
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ['mitigation-controls'] });
                queryClient.invalidateQueries({ queryKey: ['mitigation-stats'] });
                queryClient.invalidateQueries({ queryKey: ['mitigation-expiring'] });
                toast.success('Refreshed control data');
              }}
            >
              Refresh
            </Button>
            <Button
              size="sm"
              icon={<ShieldCheckIcon className="h-4 w-4" />}
              onClick={() => toast.success('Export initiated...')}
            >
              Export
            </Button>
          </div>
        }
      />

      {/* Urgent alert banner — controls expiring within 7 days */}
      {urgentExpiring.length > 0 && (
        <div className="flex items-start gap-3 p-4 bg-amber-50/80 border border-amber-300/70 rounded-xl backdrop-blur-sm">
          <BellAlertIcon className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-amber-800">
              {urgentExpiring.length} control{urgentExpiring.length > 1 ? 's' : ''} expiring within 7 days
            </p>
            <p className="text-xs text-amber-700 mt-0.5">
              {urgentExpiring.map((c) =>
                `${c.id} (${c.daysUntilExpiry === 0 ? 'today' : `${c.daysUntilExpiry}d`})`
              ).join(' · ')}{' '}
              — Recertify immediately to avoid control gaps.
            </p>
          </div>
          <button
            className="text-xs font-medium text-amber-700 hover:text-amber-900 transition-colors"
            onClick={() => toast.success('Bulk recertification initiated for urgent controls')}
          >
            Recertify All
          </button>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          title="Total Controls"
          value={stats.total}
          icon={ShieldCheckIcon}
          iconBgColor="stat-icon-blue"
          iconColor=""
        />
        <StatCard
          title="Healthy"
          value={stats.healthy}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor=""
        />
        <StatCard
          title="Expiring Soon"
          value={stats.expiringSoon}
          icon={ClockIcon}
          iconBgColor="stat-icon-yellow"
          iconColor=""
        />
        <StatCard
          title="Expired"
          value={stats.expired}
          icon={XCircleIcon}
          iconBgColor="stat-icon-red"
          iconColor=""
        />
        <StatCard
          title="Health Score"
          value={`${stats.healthScore}%`}
          icon={ChartPieIcon}
          iconBgColor="stat-icon-orange"
          iconColor=""
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Control Effectiveness Pie */}
        <Card>
          <div className="px-6 py-4 border-b border-white/20">
            <h2 className="text-sm font-semibold text-gray-900">Control Effectiveness</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Distribution of controls by operational effectiveness rating
            </p>
          </div>
          <div className="p-6">
            <SimplePieChart />
            <div className="mt-4 grid grid-cols-3 gap-3 text-center">
              {EFFECTIVENESS_DATA.map((d) => (
                <div
                  key={d.label}
                  className="p-2 rounded-lg"
                  style={{ backgroundColor: `${d.color}15`, border: `1px solid ${d.color}40` }}
                >
                  <div className="text-lg font-bold" style={{ color: d.color }}>
                    {d.value}
                  </div>
                  <div className="text-xs text-gray-600 mt-0.5">{d.label}</div>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Expiry Timeline */}
        <Card>
          <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">Expiry Timeline</h2>
              <p className="text-xs text-gray-500 mt-0.5">Upcoming control expirations requiring action</p>
            </div>
            <CalendarDaysIcon className="h-5 w-5 text-gray-400" />
          </div>
          <div className="p-6">
            <ExpiryTimeline items={expiring.slice(0, 6)} />
          </div>
        </Card>
      </div>

      {/* Overall Health Score Bar */}
      <Card>
        <div className="px-6 py-4 border-b border-white/20">
          <h2 className="text-sm font-semibold text-gray-900">Overall Mitigation Health</h2>
        </div>
        <div className="p-6">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>Health Score</span>
                <span>{stats.healthScore}%</span>
              </div>
              <div className="w-full bg-gray-100/60 rounded-full h-3 backdrop-blur-sm">
                <div
                  className={`h-3 rounded-full transition-all duration-700 ${
                    stats.healthScore >= 80
                      ? 'bg-green-500'
                      : stats.healthScore >= 50
                      ? 'bg-amber-500'
                      : 'bg-red-500'
                  }`}
                  style={{ width: `${stats.healthScore}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0%</span>
                <span className="text-amber-600 font-medium">Target: 85%</span>
                <span>100%</span>
              </div>
            </div>
            <div className="flex-shrink-0 text-right">
              <Badge
                variant={
                  stats.healthScore >= 80 ? 'success' : stats.healthScore >= 50 ? 'warning' : 'danger'
                }
                size="sm"
              >
                {stats.healthScore >= 80 ? 'Good Standing' : stats.healthScore >= 50 ? 'Needs Attention' : 'Critical'}
              </Badge>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3 bg-green-50/80 border border-green-200/60 rounded-xl backdrop-blur-sm text-center">
              <div className="text-lg font-bold text-green-700">{stats.healthy}</div>
              <div className="text-xs text-green-600 mt-0.5">Active &amp; Healthy</div>
            </div>
            <div className="p-3 bg-amber-50/80 border border-amber-200/60 rounded-xl backdrop-blur-sm text-center">
              <div className="text-lg font-bold text-amber-700">{stats.expiringSoon}</div>
              <div className="text-xs text-amber-600 mt-0.5">Expiring (30d)</div>
            </div>
            <div className="p-3 bg-red-50/80 border border-red-200/60 rounded-xl backdrop-blur-sm text-center">
              <div className="text-lg font-bold text-red-700">{stats.expired}</div>
              <div className="text-xs text-red-600 mt-0.5">Expired</div>
            </div>
            <div className="p-3 bg-gray-50/80 border border-gray-200/60 rounded-xl backdrop-blur-sm text-center">
              <div className="text-lg font-bold text-gray-700">{stats.suspended}</div>
              <div className="text-xs text-gray-500 mt-0.5">Suspended</div>
            </div>
          </div>
        </div>
      </Card>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col lg:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by control ID, name, or owner..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClear={() => setSearchTerm('')}
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Status' },
                { value: 'active', label: 'Active' },
                { value: 'expiring', label: 'Expiring Soon' },
                { value: 'expired', label: 'Expired' },
                { value: 'suspended', label: 'Suspended' },
              ]}
            />
            <Select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Types' },
                { value: 'Preventive', label: 'Preventive' },
                { value: 'Detective', label: 'Detective' },
                { value: 'Corrective', label: 'Corrective' },
                { value: 'Compensating', label: 'Compensating' },
                { value: 'Manual', label: 'Manual' },
              ]}
            />
          </div>
        </div>
      </Card>

      {/* Controls Health Table */}
      <Card padding="none">
        <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">
            Controls Health Table
            <span className="ml-2 text-xs font-normal text-gray-400">
              ({filteredControls.length} of {controls.length} controls)
            </span>
          </h2>
          <ExclamationTriangleIcon className="h-4 w-4 text-gray-400" />
        </div>
        <Table
          columns={columns}
          data={filteredControls}
          emptyMessage={
            controlsLoading ? 'Loading controls...' : 'No controls match the current filters'
          }
        />
      </Card>
    </div>
  );
}
