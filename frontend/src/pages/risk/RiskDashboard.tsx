import { Link } from 'react-router-dom';
import {
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
  CheckCircleIcon,
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Table,
  Badge,
  RiskBadge,
  StatusBadge,
} from '../../components/ui';

interface RiskMetric {
  label: string;
  value: number;
  change: number;
  changeType: 'increase' | 'decrease';
}

const riskMetrics: RiskMetric[] = [
  { label: 'Overall Risk Score', value: 42, change: 5, changeType: 'decrease' },
  { label: 'Active Violations', value: 45, change: 12, changeType: 'decrease' },
  { label: 'Critical SoD Conflicts', value: 8, change: 2, changeType: 'decrease' },
  { label: 'Users at High Risk', value: 23, change: 3, changeType: 'increase' },
];

const recentViolations = [
  {
    id: 'VIO-001',
    user: 'John Smith',
    type: 'SoD Conflict',
    rule: 'Create Vendor / Approve Payment',
    riskLevel: 'critical',
    date: '2024-01-20',
    status: 'open',
  },
  {
    id: 'VIO-002',
    user: 'Mary Brown',
    type: 'Excessive Access',
    rule: 'Admin access without business need',
    riskLevel: 'high',
    date: '2024-01-19',
    status: 'in_review',
  },
  {
    id: 'VIO-003',
    user: 'Tom Davis',
    type: 'SoD Conflict',
    rule: 'Create PO / Approve PO',
    riskLevel: 'high',
    date: '2024-01-18',
    status: 'mitigated',
  },
  {
    id: 'VIO-004',
    user: 'Alice Wilson',
    type: 'Sensitive Access',
    rule: 'Payroll data access',
    riskLevel: 'medium',
    date: '2024-01-17',
    status: 'open',
  },
  {
    id: 'VIO-005',
    user: 'Bob Johnson',
    type: 'SoD Conflict',
    rule: 'Create GL Entry / Post GL Entry',
    riskLevel: 'critical',
    date: '2024-01-16',
    status: 'open',
  },
];

const riskByCategory = [
  { category: 'SoD Conflicts', count: 28, percentage: 45 },
  { category: 'Excessive Privileges', count: 18, percentage: 29 },
  { category: 'Sensitive Access', count: 12, percentage: 19 },
  { category: 'Dormant Accounts', count: 7, percentage: 11 },
];

const statusVariant: Record<string, 'danger' | 'info' | 'success'> = {
  open: 'danger',
  in_review: 'info',
  mitigated: 'success',
};

const statusLabel: Record<string, string> = {
  open: 'Open',
  in_review: 'In Review',
  mitigated: 'Mitigated',
};

export function RiskDashboard() {
  const columns = [
    {
      key: 'violation',
      header: 'Violation ID',
      render: (v: typeof recentViolations[0]) => (
        <span className="text-sm font-medium text-primary-600">{v.id}</span>
      ),
    },
    {
      key: 'user',
      header: 'User',
      render: (v: typeof recentViolations[0]) => (
        <span className="text-sm text-gray-900">{v.user}</span>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (v: typeof recentViolations[0]) => (
        <span className="text-sm text-gray-500">{v.type}</span>
      ),
    },
    {
      key: 'risk',
      header: 'Risk Level',
      render: (v: typeof recentViolations[0]) => <RiskBadge level={v.riskLevel} />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (v: typeof recentViolations[0]) => (
        <Badge variant={statusVariant[v.status] || 'neutral'} size="sm">
          {statusLabel[v.status] || v.status}
        </Badge>
      ),
    },
    {
      key: 'date',
      header: 'Date',
      render: (v: typeof recentViolations[0]) => (
        <span className="text-sm text-gray-500">{v.date}</span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Dashboard"
        subtitle="Real-time view of your organization's access risk posture"
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" icon={<ChartBarIcon className="h-4 w-4" />} href="/risk/rules">
              Manage Rules
            </Button>
            <Button size="sm" icon={<ExclamationTriangleIcon className="h-4 w-4" />} href="/risk/violations">
              View Violations
            </Button>
          </div>
        }
      />

      {/* Risk Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Risk Score"
          value={riskMetrics[0].value}
          icon={ShieldCheckIcon}
          iconBgColor="stat-icon-blue"
          iconColor=""
          trend={-riskMetrics[0].change}
        />
        <StatCard
          title="Active Violations"
          value={riskMetrics[1].value}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-red"
          iconColor=""
          trend={-riskMetrics[1].change}
        />
        <StatCard
          title="Critical SoD"
          value={riskMetrics[2].value}
          icon={ShieldExclamationIcon}
          iconBgColor="stat-icon-orange"
          iconColor=""
          trend={-riskMetrics[2].change}
        />
        <StatCard
          title="High Risk Users"
          value={riskMetrics[3].value}
          icon={UserGroupIcon}
          iconBgColor="stat-icon-yellow"
          iconColor=""
          trend={riskMetrics[3].change}
        />
      </div>

      {/* Risk Overview Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Risk Score Gauge */}
        <Card>
          <div className="px-6 py-4 border-b border-white/20">
            <h2 className="text-sm font-semibold text-gray-900">Organization Risk Score</h2>
          </div>
          <div className="p-6">
            <div className="flex items-center justify-center py-4">
              <div className="relative">
                <svg width="160" height="160" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" strokeWidth="8" />
                  <circle
                    cx="50" cy="50" r="40" fill="none" stroke="#22c55e" strokeWidth="8"
                    strokeDasharray={`${42 * 2.51} ${100 * 2.51}`}
                    strokeLinecap="round" transform="rotate(-90 50 50)"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-bold text-gray-900">42</span>
                  <span className="text-xs text-gray-500">/ 100</span>
                </div>
              </div>
            </div>
            <div className="mt-4 text-center">
              <Badge variant="success" size="sm">
                <CheckCircleIcon className="h-3.5 w-3.5 mr-1" />
                Low Risk
              </Badge>
              <p className="mt-2 text-xs text-gray-500">
                Your organization's risk score has improved by 5% this month
              </p>
            </div>
          </div>
        </Card>

        {/* Risk by Category */}
        <Card>
          <div className="px-6 py-4 border-b border-white/20">
            <h2 className="text-sm font-semibold text-gray-900">Violations by Category</h2>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {riskByCategory.map((item) => (
                <div key={item.category}>
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-gray-700">{item.category}</span>
                    <span className="text-gray-500">{item.count} violations</span>
                  </div>
                  <div className="mt-1 w-full bg-gray-100/60 rounded-full h-1.5">
                    <div
                      className="bg-primary-600 h-1.5 rounded-full transition-all duration-500"
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* Recent Violations */}
      <Card padding="none">
        <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">Recent Violations</h2>
          <Link
            to="/risk/violations"
            className="text-xs text-primary-600 hover:text-primary-800 font-medium transition-colors"
          >
            View all
          </Link>
        </div>
        <Table columns={columns} data={recentViolations} emptyMessage="No recent violations" />
      </Card>

      {/* Risk Insights */}
      <Card>
        <div className="px-6 py-4 border-b border-white/20">
          <h2 className="text-sm font-semibold text-gray-900">AI Risk Insights</h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 bg-yellow-50/80 border border-yellow-200/60 rounded-xl backdrop-blur-sm">
              <div className="flex items-center">
                <ShieldExclamationIcon className="h-5 w-5 text-yellow-600" />
                <span className="ml-2 text-xs font-medium text-yellow-800">High-Risk Pattern</span>
              </div>
              <p className="mt-1.5 text-xs text-yellow-700">
                3 users in Finance have accumulated excessive privileges.
              </p>
            </div>
            <div className="p-3 bg-blue-50/80 border border-blue-200/60 rounded-xl backdrop-blur-sm">
              <div className="flex items-center">
                <ChartBarIcon className="h-5 w-5 text-blue-600" />
                <span className="ml-2 text-xs font-medium text-blue-800">Trending Risk</span>
              </div>
              <p className="mt-1.5 text-xs text-blue-700">
                SoD violations have decreased 15% since automated controls.
              </p>
            </div>
            <div className="p-3 bg-green-50/80 border border-green-200/60 rounded-xl backdrop-blur-sm">
              <div className="flex items-center">
                <CheckCircleIcon className="h-5 w-5 text-green-600" />
                <span className="ml-2 text-xs font-medium text-green-800">Compliance Status</span>
              </div>
              <p className="mt-1.5 text-xs text-green-700">
                92% of critical controls are operating effectively.
              </p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
