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

const riskLevelConfig = {
  critical: { color: 'bg-red-100 text-red-800', label: 'Critical' },
  high: { color: 'bg-orange-100 text-orange-800', label: 'High' },
  medium: { color: 'bg-yellow-100 text-yellow-800', label: 'Medium' },
  low: { color: 'bg-green-100 text-green-800', label: 'Low' },
};

const statusConfig = {
  open: { color: 'bg-red-100 text-red-800', label: 'Open' },
  in_review: { color: 'bg-blue-100 text-blue-800', label: 'In Review' },
  mitigated: { color: 'bg-green-100 text-green-800', label: 'Mitigated' },
};

export function RiskDashboard() {
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Risk Dashboard</h1>
          <p className="page-subtitle">
            Real-time view of your organization's access risk posture
          </p>
        </div>
        <div className="flex space-x-2">
          <Link
            to="/risk/rules"
            className="btn-secondary"
          >
            <ChartBarIcon className="h-4 w-4 mr-1.5" />
            Manage Rules
          </Link>
          <Link
            to="/risk/violations"
            className="btn-primary"
          >
            <ExclamationTriangleIcon className="h-4 w-4 mr-1.5" />
            View Violations
          </Link>
        </div>
      </div>

      {/* Risk Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-card-accent border-blue-400">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-blue">
              <ShieldCheckIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Risk Score</div>
              <div className="flex items-baseline gap-2">
                <div className="stat-value">{riskMetrics[0].value}</div>
                <span className="flex items-center text-xs font-medium text-green-600">
                  <ArrowTrendingDownIcon className="h-3 w-3" />
                  {riskMetrics[0].change}%
                </span>
              </div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-red">
              <ExclamationTriangleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Active Violations</div>
              <div className="flex items-baseline gap-2">
                <div className="stat-value text-red-500">{riskMetrics[1].value}</div>
                <span className="flex items-center text-xs font-medium text-green-600">
                  <ArrowTrendingDownIcon className="h-3 w-3" />
                  {riskMetrics[1].change}%
                </span>
              </div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-orange">
              <ShieldExclamationIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Critical SoD</div>
              <div className="flex items-baseline gap-2">
                <div className="stat-value text-orange-500">{riskMetrics[2].value}</div>
                <span className="flex items-center text-xs font-medium text-green-600">
                  <ArrowTrendingDownIcon className="h-3 w-3" />
                  {riskMetrics[2].change}%
                </span>
              </div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-yellow">
              <UserGroupIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">High Risk Users</div>
              <div className="flex items-baseline gap-2">
                <div className="stat-value">{riskMetrics[3].value}</div>
                <span className="flex items-center text-xs font-medium text-red-600">
                  <ArrowTrendingUpIcon className="h-3 w-3" />
                  {riskMetrics[3].change}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Overview Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Risk Score Gauge */}
        <div className="card">
          <div className="card-header">
            <h2 className="section-title">Organization Risk Score</h2>
          </div>
          <div className="card-body">
          <div className="flex items-center justify-center py-4">
            <div className="relative">
              <svg width="160" height="160" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="8"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="#22c55e"
                  strokeWidth="8"
                  strokeDasharray={`${42 * 2.51} ${100 * 2.51}`}
                  strokeLinecap="round"
                  transform="rotate(-90 50 50)"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-gray-900">42</span>
                <span className="text-xs text-gray-500">/ 100</span>
              </div>
            </div>
          </div>
          <div className="mt-4 text-center">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
              <CheckCircleIcon className="h-3.5 w-3.5 mr-1" />
              Low Risk
            </span>
            <p className="mt-2 text-xs text-gray-500">
              Your organization's risk score has improved by 5% this month
            </p>
          </div>
          </div>
        </div>

        {/* Risk by Category */}
        <div className="card">
          <div className="card-header">
            <h2 className="section-title">Violations by Category</h2>
          </div>
          <div className="card-body">
            <div className="space-y-3">
              {riskByCategory.map((item) => (
                <div key={item.category}>
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-gray-700">{item.category}</span>
                    <span className="text-gray-500">{item.count} violations</span>
                  </div>
                  <div className="mt-1 w-full bg-gray-100 rounded-full h-1.5">
                    <div
                      className="bg-primary-600 h-1.5 rounded-full"
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Violations */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h2 className="section-title">Recent Violations</h2>
          <Link
            to="/risk/violations"
            className="text-xs text-primary-600 hover:text-primary-700 font-medium"
          >
            View all
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Violation ID
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  User
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Type
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Risk Level
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Date
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {recentViolations.map((violation) => (
                <tr key={violation.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-xs font-medium text-primary-600">
                    {violation.id}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-900">
                    {violation.user}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                    {violation.type}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${
                        riskLevelConfig[violation.riskLevel as keyof typeof riskLevelConfig].color
                      }`}
                    >
                      {riskLevelConfig[violation.riskLevel as keyof typeof riskLevelConfig].label}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${
                        statusConfig[violation.status as keyof typeof statusConfig].color
                      }`}
                    >
                      {statusConfig[violation.status as keyof typeof statusConfig].label}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                    {violation.date}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Risk Insights */}
      <div className="card">
        <div className="card-header">
          <h2 className="section-title">AI Risk Insights</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center">
                <ShieldExclamationIcon className="h-5 w-5 text-yellow-600" />
                <span className="ml-2 text-xs font-medium text-yellow-800">High-Risk Pattern</span>
              </div>
              <p className="mt-1.5 text-xs text-yellow-700">
                3 users in Finance have accumulated excessive privileges.
              </p>
            </div>
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center">
                <ChartBarIcon className="h-5 w-5 text-blue-600" />
                <span className="ml-2 text-xs font-medium text-blue-800">Trending Risk</span>
              </div>
              <p className="mt-1.5 text-xs text-blue-700">
                SoD violations have decreased 15% since automated controls.
              </p>
            </div>
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
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
      </div>
    </div>
  );
}
