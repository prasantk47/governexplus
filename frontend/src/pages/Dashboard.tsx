/**
 * Governex+ Platform - Main Dashboard
 * Domain: governexplus.com
 * Glassmorphism Design
 */
import { useQuery } from '@tanstack/react-query';
import {
  ExclamationTriangleIcon,
  ClockIcon,
  UserGroupIcon,
  FireIcon,
  DocumentCheckIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
} from '@heroicons/react/24/outline';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { StatCard } from '../components/StatCard';
import { RiskChart } from '../components/charts/RiskChart';
import { ViolationsTrend, AccessRequestsTrend } from '../components/charts/ViolationsTrend';
import { PendingApprovalsTable } from '../components/tables/PendingApprovalsTable';
import { RecentActivityList } from '../components/RecentActivityList';

interface DashboardStats {
  totalUsers: number;
  activeViolations: number;
  pendingApprovals: number;
  certificationProgress: number;
  activeFirefighterSessions: number;
  riskScore: number;
  riskTrend: 'up' | 'down' | 'stable';
}

export function Dashboard() {
  const { data: stats } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.get('/dashboard/stats').then((res) => res.data),
  });

  // Mock data for demonstration
  const mockStats: DashboardStats = {
    totalUsers: 1250,
    activeViolations: 45,
    pendingApprovals: 12,
    certificationProgress: 78,
    activeFirefighterSessions: 2,
    riskScore: 42,
    riskTrend: 'down',
  };

  const displayStats = stats || mockStats;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="glass-card p-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            Overview of your GRC platform status and key metrics
          </p>
        </div>
        <div className="flex space-x-3">
          <Link to="/access-requests/new" className="btn-primary glossy">
            New Access Request
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Active Violations"
          value={displayStats.activeViolations}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-red"
          iconColor=""
          trend={displayStats.riskTrend === 'down' ? -12 : 8}
          link="/risk/violations"
        />
        <StatCard
          title="Pending Approvals"
          value={displayStats.pendingApprovals}
          icon={ClockIcon}
          iconBgColor="stat-icon-blue"
          iconColor=""
          link="/approvals"
        />
        <StatCard
          title="Certification Progress"
          value={`${displayStats.certificationProgress}%`}
          icon={DocumentCheckIcon}
          iconBgColor="stat-icon-green"
          iconColor=""
          link="/certification"
        />
        <StatCard
          title="Active FF Sessions"
          value={displayStats.activeFirefighterSessions}
          icon={FireIcon}
          iconBgColor="stat-icon-orange"
          iconColor=""
          link="/firefighter/sessions"
        />
      </div>

      {/* Risk Overview */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Risk Score Card */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-900">
              Organization Risk Score
            </h2>
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium backdrop-blur-sm ${
                displayStats.riskScore < 40
                  ? 'bg-green-100/80 text-green-700'
                  : displayStats.riskScore < 70
                  ? 'bg-yellow-100/80 text-yellow-700'
                  : 'bg-red-100/80 text-red-700'
              }`}
            >
              {displayStats.riskScore < 40
                ? 'Low Risk'
                : displayStats.riskScore < 70
                ? 'Medium Risk'
                : 'High Risk'}
            </span>
          </div>
          <div className="flex items-baseline">
            <span className="text-4xl font-bold text-gray-900 tracking-tight">
              {displayStats.riskScore}
            </span>
            <span className="ml-2 text-sm text-gray-400">/ 100</span>
            <span
              className={`ml-4 flex items-center text-sm font-medium ${
                displayStats.riskTrend === 'down'
                  ? 'text-green-600'
                  : 'text-red-600'
              }`}
            >
              {displayStats.riskTrend === 'down' ? (
                <ArrowTrendingDownIcon className="h-4 w-4 mr-1" />
              ) : (
                <ArrowTrendingUpIcon className="h-4 w-4 mr-1" />
              )}
              {displayStats.riskTrend === 'down' ? '-5%' : '+3%'}
            </span>
          </div>
          <div className="mt-4">
            <div className="w-full bg-gray-200/50 rounded-full h-2 backdrop-blur-sm">
              <div
                className={`h-2 rounded-full transition-all duration-500 ${
                  displayStats.riskScore < 40
                    ? 'bg-gradient-to-r from-green-400 to-green-500'
                    : displayStats.riskScore < 70
                    ? 'bg-gradient-to-r from-yellow-400 to-yellow-500'
                    : 'bg-gradient-to-r from-red-400 to-red-500'
                }`}
                style={{ width: `${displayStats.riskScore}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Risk Distribution Chart */}
        <div className="glass-card p-6">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">
            Violations by Risk Level
          </h2>
          <RiskChart />
        </div>
      </div>

      {/* Trends Grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Violations Trend */}
        <div className="glass-card p-6">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">
            Violation Trends (Last 6 Months)
          </h2>
          <ViolationsTrend compact />
        </div>

        {/* Access Requests Trend */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-900">
              Access Requests (Last 6 Months)
            </h2>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-gradient-to-br from-emerald-400 to-emerald-500 rounded-full shadow-sm"></span>
                Approved
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-gradient-to-br from-amber-400 to-amber-500 rounded-full shadow-sm"></span>
                Pending
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-gradient-to-br from-red-400 to-red-500 rounded-full shadow-sm"></span>
                Rejected
              </span>
            </div>
          </div>
          <AccessRequestsTrend compact />
        </div>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Pending Approvals */}
        <div className="glass-card overflow-hidden">
          <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-900">
              Pending Approvals
            </h2>
            <Link
              to="/approvals"
              className="text-xs text-gray-600 hover:text-gray-800 font-medium transition-colors"
            >
              View all
            </Link>
          </div>
          <PendingApprovalsTable limit={5} />
        </div>

        {/* Recent Activity */}
        <div className="glass-card overflow-hidden">
          <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-900">
              Recent Activity
            </h2>
            <Link
              to="/audit"
              className="text-xs text-gray-600 hover:text-gray-800 font-medium transition-colors"
            >
              View all
            </Link>
          </div>
          <RecentActivityList limit={5} />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="glass-card p-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Link
            to="/access-requests/new"
            className="glass-btn flex flex-col items-center p-4 rounded-xl hover:bg-gray-50/50 transition-all duration-300 group"
          >
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-gray-500 to-gray-700 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300">
              <UserGroupIcon className="h-6 w-6 text-white" />
            </div>
            <span className="mt-3 text-xs font-medium text-gray-700">
              Request Access
            </span>
          </Link>
          <Link
            to="/firefighter/request"
            className="glass-btn flex flex-col items-center p-4 rounded-xl hover:bg-gray-50/50 transition-all duration-300 group"
          >
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-gray-500 to-gray-700 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300">
              <FireIcon className="h-6 w-6 text-white" />
            </div>
            <span className="mt-3 text-xs font-medium text-gray-700">
              Emergency Access
            </span>
          </Link>
          <Link
            to="/risk/violations"
            className="glass-btn flex flex-col items-center p-4 rounded-xl hover:bg-gray-50/50 transition-all duration-300 group"
          >
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-gray-500 to-gray-700 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300">
              <ExclamationTriangleIcon className="h-6 w-6 text-white" />
            </div>
            <span className="mt-3 text-xs font-medium text-gray-700">
              View Violations
            </span>
          </Link>
          <Link
            to="/reports"
            className="glass-btn flex flex-col items-center p-4 rounded-xl hover:bg-gray-50/50 transition-all duration-300 group"
          >
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-gray-500 to-gray-700 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300">
              <DocumentCheckIcon className="h-6 w-6 text-white" />
            </div>
            <span className="mt-3 text-xs font-medium text-gray-700">
              Run Reports
            </span>
          </Link>
        </div>
      </div>
    </div>
  );
}
