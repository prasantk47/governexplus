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
import {
  PageHeader,
  Card,
  CardHeader,
  CardBody,
  Button,
  Badge,
} from '../components/ui';

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
      <PageHeader
        title="Dashboard"
        subtitle="Overview of your GRC platform status and key metrics"
        actions={
          <Button size="sm" href="/access-requests/new">
            New Access Request
          </Button>
        }
      />

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
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-900">
              Organization Risk Score
            </h2>
            <Badge
              variant={
                displayStats.riskScore < 40
                  ? 'success'
                  : displayStats.riskScore < 70
                  ? 'warning'
                  : 'danger'
              }
              size="sm"
            >
              {displayStats.riskScore < 40
                ? 'Low Risk'
                : displayStats.riskScore < 70
                ? 'Medium Risk'
                : 'High Risk'}
            </Badge>
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
        </Card>

        {/* Risk Distribution Chart */}
        <Card padding="lg">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">
            Violations by Risk Level
          </h2>
          <RiskChart />
        </Card>
      </div>

      {/* Trends Grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card padding="lg">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">
            Violation Trends (Last 6 Months)
          </h2>
          <ViolationsTrend compact />
        </Card>

        <Card padding="lg">
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
        </Card>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card padding="none">
          <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-900">
              Pending Approvals
            </h2>
            <Link
              to="/approvals"
              className="text-xs text-primary-600 hover:text-primary-800 font-medium transition-colors"
            >
              View all
            </Link>
          </div>
          <PendingApprovalsTable limit={5} />
        </Card>

        <Card padding="none">
          <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-900">
              Recent Activity
            </h2>
            <Link
              to="/audit"
              className="text-xs text-primary-600 hover:text-primary-800 font-medium transition-colors"
            >
              View all
            </Link>
          </div>
          <RecentActivityList limit={5} />
        </Card>
      </div>

      {/* Quick Actions */}
      <Card padding="lg">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { to: '/access-requests/new', icon: UserGroupIcon, label: 'Request Access' },
            { to: '/firefighter/request', icon: FireIcon, label: 'Emergency Access' },
            { to: '/risk/violations', icon: ExclamationTriangleIcon, label: 'View Violations' },
            { to: '/reports', icon: DocumentCheckIcon, label: 'Run Reports' },
          ].map((action) => (
            <Link
              key={action.to}
              to={action.to}
              className="glass-card flex flex-col items-center p-4 rounded-xl hover:shadow-glass-hover transition-all duration-300 group"
            >
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-gray-500 to-gray-700 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300">
                <action.icon className="h-6 w-6 text-white" />
              </div>
              <span className="mt-3 text-xs font-medium text-gray-700">
                {action.label}
              </span>
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}
