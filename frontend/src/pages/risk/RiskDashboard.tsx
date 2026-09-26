import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
  CheckCircleIcon,
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
} from '../../components/ui';
import { dashboardApi, riskApi } from '../../services/api';

interface RiskMetric {
  label: string;
  value: number;
  change: number;
  changeType: 'increase' | 'decrease';
}

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

interface ViolationRow {
  id: string;
  user: string;
  type: string;
  rule?: string;
  riskLevel: string;
  date: string;
  status: string;
}

export function RiskDashboard() {
  const { data: riskMetricsData } = useQuery({
    queryKey: ['dashboardRiskMetrics'],
    queryFn: () => dashboardApi.getRiskMetrics().then(r => r.data),
  });

  const { data: violationsData } = useQuery({
    queryKey: ['recentViolations'],
    queryFn: () => riskApi.listViolations({ limit: 5 }).then(r => r.data),
  });

  const riskMetrics: RiskMetric[] = Array.isArray(riskMetricsData) ? riskMetricsData : [];
  const recentViolations: ViolationRow[] = Array.isArray(violationsData) ? violationsData : (violationsData as any)?.violations || [];
  const riskByCategory: { category: string; count: number; percentage: number }[] =
    (riskMetricsData as any)?.byCategory || [];

  const columns = [
    {
      key: 'violation',
      header: 'Violation ID',
      render: (v: ViolationRow) => (
        <span className="text-sm font-medium text-primary-600">{v.id}</span>
      ),
    },
    {
      key: 'user',
      header: 'User',
      render: (v: ViolationRow) => (
        <span className="text-sm text-gray-900">{v.user}</span>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (v: ViolationRow) => (
        <span className="text-sm text-gray-500">{v.type}</span>
      ),
    },
    {
      key: 'risk',
      header: 'Risk Level',
      render: (v: ViolationRow) => <RiskBadge level={v.riskLevel} />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (v: ViolationRow) => (
        <Badge variant={statusVariant[v.status] || 'neutral'} size="sm">
          {statusLabel[v.status] || v.status}
        </Badge>
      ),
    },
    {
      key: 'date',
      header: 'Date',
      render: (v: ViolationRow) => (
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
          value={riskMetrics[0]?.value ?? 0}
          icon={ShieldCheckIcon}
          iconBgColor="stat-icon-blue"
          iconColor=""
          trend={-(riskMetrics[0]?.change ?? 0)}
        />
        <StatCard
          title="Active Violations"
          value={riskMetrics[1]?.value ?? 0}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-red"
          iconColor=""
          trend={-(riskMetrics[1]?.change ?? 0)}
        />
        <StatCard
          title="Critical SoD"
          value={riskMetrics[2]?.value ?? 0}
          icon={ShieldExclamationIcon}
          iconBgColor="stat-icon-orange"
          iconColor=""
          trend={-(riskMetrics[2]?.change ?? 0)}
        />
        <StatCard
          title="High Risk Users"
          value={riskMetrics[3]?.value ?? 0}
          icon={UserGroupIcon}
          iconBgColor="stat-icon-yellow"
          iconColor=""
          trend={riskMetrics[3]?.change ?? 0}
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
