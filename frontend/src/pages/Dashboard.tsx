/**
 * Governex+ Platform - Main Dashboard
 * Enterprise Design System
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
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { Link } from 'react-router-dom';
import { dashboardApi, accessRequestApi, auditApi } from '../services/api';
import { StatCard } from '../components/StatCard';
import { RiskChart } from '../components/charts/RiskChart';
import { ViolationsTrend, AccessRequestsTrend } from '../components/charts/ViolationsTrend';
import { PendingApprovalsTable } from '../components/tables/PendingApprovalsTable';
import { RecentActivityList } from '../components/RecentActivityList';
import {
  PageHeader,
  Card,
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

// ---------------------------------------------------------------------------
// Skeleton helpers
// ---------------------------------------------------------------------------

function StatCardSkeleton() {
  return (
    <div className="glass-card p-5 animate-pulse">
      <div className="flex items-center gap-4">
        <div className="h-11 w-11 rounded-lg bg-gray-200 dark:bg-slate-700" />
        <div className="flex-1">
          <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-24 mb-2" />
          <div className="h-7 bg-gray-200 dark:bg-slate-700 rounded w-16" />
        </div>
      </div>
    </div>
  );
}

function ChartSkeleton({ height = 'h-36' }: { height?: string }) {
  return (
    <div className={`${height} flex items-end gap-3 px-1 animate-pulse`}>
      {[65, 45, 80, 55, 70, 40].map((h, i) => (
        <div
          key={i}
          className="flex-1 bg-gray-200 dark:bg-slate-700 rounded-t-lg"
          style={{ height: `${h}%` }}
        />
      ))}
    </div>
  );
}

function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="animate-pulse divide-y divide-gray-100 dark:divide-slate-700">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-6 py-4">
          <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-24" />
          <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-28 flex-1" />
          <div className="h-5 bg-gray-100 dark:bg-slate-600 rounded-full w-16" />
          <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-20" />
        </div>
      ))}
    </div>
  );
}

function ActivitySkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flow-root px-4 py-2 animate-pulse">
      <ul className="-mb-8">
        {Array.from({ length: rows }).map((_, i) => (
          <li key={i}>
            <div className="relative pb-8">
              {i < rows - 1 && (
                <span className="absolute left-4 top-4 -ml-px h-full w-0.5 bg-gray-100 dark:bg-slate-700" />
              )}
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-full bg-gray-200 dark:bg-slate-700 flex-shrink-0" />
                <div className="flex-1 pt-1">
                  <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-5/6 mb-1.5" />
                  <div className="h-2.5 bg-gray-100 dark:bg-slate-600 rounded w-24" />
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SectionError({ message }: { message?: string }) {
  return (
    <div className="flex items-center gap-2 p-4 text-sm text-red-600 dark:text-red-400">
      <ExclamationCircleIcon className="h-4 w-4 flex-shrink-0" />
      <span>{message || 'Failed to load data. Please refresh.'}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export function Dashboard() {
  const {
    data: stats,
    isLoading: statsLoading,
    isError: statsError,
  } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardApi.getStats().then((res) => res.data),
  });

  const { isLoading: riskLoading, isError: riskError } = useQuery({
    queryKey: ['risk-chart'],
    queryFn: () => dashboardApi.getRiskMetrics().then((res) => res.data),
  });

  const { isLoading: approvalsLoading, isError: approvalsError } = useQuery({
    queryKey: ['pending-approvals', 5],
    queryFn: () =>
      accessRequestApi
        .getPendingApprovals()
        .then((res) => {
          const d = res.data;
          if (Array.isArray(d)) return d;
          if (d?.approvals && Array.isArray(d.approvals)) return d.approvals;
          return [];
        }),
  });

  const { isLoading: activityLoading, isError: activityError } = useQuery({
    queryKey: ['recent-activity', 5],
    queryFn: () =>
      auditApi.getLogs({ limit: 5 }).then((res) => {
          const d = res.data;
          if (Array.isArray(d)) return d;
          if (d?.logs && Array.isArray(d.logs)) return d.logs;
          return [];
        }),
  });

  const displayStats: DashboardStats = stats || {
    totalUsers: 0,
    activeViolations: 0,
    pendingApprovals: 0,
    certificationProgress: 0,
    activeFirefighterSessions: 0,
    riskScore: 0,
    riskTrend: 'stable',
  };

  return (
    <div className="space-y-7">
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
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {statsLoading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : statsError ? (
          <div className="col-span-4">
            <Card padding="md">
              <SectionError message="Dashboard stats unavailable. Check API connectivity." />
            </Card>
          </div>
        ) : (
          <>
            <StatCard
              title="Active Violations"
              value={displayStats.activeViolations}
              icon={ExclamationTriangleIcon}
              iconBgColor="stat-icon-red"
              iconColor=""
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
              title="Active Privileged Sessions"
              value={displayStats.activeFirefighterSessions}
              icon={FireIcon}
              iconBgColor="stat-icon-orange"
              iconColor=""
              link="/firefighter/sessions"
            />
          </>
        )}
      </div>

      {/* Risk Overview */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card padding="lg">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-gray-100 dark:border-slate-800">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 tracking-tight">
              Organization Risk Score
            </h2>
            {!statsLoading && (
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
            )}
          </div>
          {statsLoading ? (
            <div className="animate-pulse">
              <div className="h-12 bg-gray-200 dark:bg-slate-700 rounded w-24 mb-4" />
              <div className="h-2.5 bg-gray-200 dark:bg-slate-700 rounded-full w-full" />
            </div>
          ) : (
            <>
              <div className="flex items-baseline">
                <span className="text-5xl font-bold text-gray-900 dark:text-white tracking-tight">
                  {displayStats.riskScore}
                </span>
                <span className="ml-2 text-sm text-gray-400">/ 100</span>
                <span
                  className={`ml-4 flex items-center text-sm font-medium ${
                    displayStats.riskTrend === 'down'
                      ? 'text-emerald-600'
                      : 'text-red-600'
                  }`}
                >
                  {displayStats.riskTrend === 'down' ? (
                    <ArrowTrendingDownIcon className="h-4 w-4 mr-1" />
                  ) : (
                    <ArrowTrendingUpIcon className="h-4 w-4 mr-1" />
                  )}
                  {displayStats.riskTrend === 'down' ? 'Improving' : 'Increasing'}
                </span>
              </div>
              <div className="mt-5">
                <div className="w-full bg-gray-100 dark:bg-slate-700 rounded-full h-2.5">
                  <div
                    className={`h-2.5 rounded-full transition-all duration-500 ${
                      displayStats.riskScore < 40
                        ? 'bg-emerald-500'
                        : displayStats.riskScore < 70
                        ? 'bg-amber-500'
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${displayStats.riskScore}%` }}
                  />
                </div>
              </div>
            </>
          )}
        </Card>

        <Card padding="lg">
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-5 pb-4 border-b border-gray-100 dark:border-slate-800 tracking-tight">
            Violations by Risk Level
          </h2>
          {riskLoading ? (
            <div className="space-y-4 animate-pulse">
              {['Critical', 'High', 'Medium', 'Low'].map((l) => (
                <div key={l} className="flex items-center gap-4">
                  <div className="w-20 h-3 bg-gray-200 dark:bg-slate-700 rounded" />
                  <div className="flex-1 h-4 bg-gray-100 dark:bg-slate-700 rounded-full" />
                  <div className="w-8 h-3 bg-gray-200 dark:bg-slate-700 rounded" />
                </div>
              ))}
            </div>
          ) : riskError ? (
            <SectionError />
          ) : (
            <RiskChart />
          )}
        </Card>
      </div>

      {/* Trends */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card padding="lg">
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-5 pb-4 border-b border-gray-100 dark:border-slate-800 tracking-tight">
            Violation Trends (Last 6 Months)
          </h2>
          {riskLoading ? (
            <ChartSkeleton />
          ) : riskError ? (
            <SectionError />
          ) : (
            <ViolationsTrend compact />
          )}
        </Card>

        <Card padding="lg">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-gray-100 dark:border-slate-800">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 tracking-tight">
              Access Requests (Last 6 Months)
            </h2>
            <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full" />
                Approved
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-amber-500 rounded-full" />
                Pending
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-red-500 rounded-full" />
                Rejected
              </span>
            </div>
          </div>
          {riskLoading ? (
            <ChartSkeleton />
          ) : riskError ? (
            <SectionError />
          ) : (
            <AccessRequestsTrend compact />
          )}
        </Card>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card padding="none">
          <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-800 flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 tracking-tight">
              Pending Approvals
            </h2>
            <Link
              to="/approvals"
              className="text-sm text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 font-medium transition-colors"
            >
              View all
            </Link>
          </div>
          {approvalsLoading ? (
            <TableSkeleton rows={5} />
          ) : approvalsError ? (
            <SectionError />
          ) : (
            <PendingApprovalsTable limit={5} />
          )}
        </Card>

        <Card padding="none">
          <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-800 flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 tracking-tight">
              Recent Activity
            </h2>
            <Link
              to="/audit"
              className="text-sm text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 font-medium transition-colors"
            >
              View all
            </Link>
          </div>
          {activityLoading ? (
            <ActivitySkeleton rows={5} />
          ) : activityError ? (
            <SectionError />
          ) : (
            <RecentActivityList limit={5} />
          )}
        </Card>
      </div>

      {/* Quick Actions */}
      <Card padding="lg">
        <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-5 pb-4 border-b border-gray-100 dark:border-slate-800 tracking-tight">
          Quick Actions
        </h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { to: '/access-requests/new', icon: UserGroupIcon, label: 'Request Access', bg: 'linear-gradient(135deg,#e0e7ff,#c7d2fe)', color: '#4338ca' },
            { to: '/privileged-access/request', icon: FireIcon, label: 'Emergency Access', bg: 'linear-gradient(135deg,#fed7aa,#fdba74)', color: '#c2410c' },
            { to: '/risk/violations', icon: ExclamationTriangleIcon, label: 'View Violations', bg: 'linear-gradient(135deg,#fecaca,#fca5a5)', color: '#b91c1c' },
            { to: '/reports', icon: DocumentCheckIcon, label: 'Run Reports', bg: 'linear-gradient(135deg,#a7f3d0,#6ee7b7)', color: '#047857' },
          ].map((action) => (
            <Link
              key={action.to}
              to={action.to}
              className="flex flex-col items-center p-5 rounded-xl border border-gray-100 dark:border-slate-800 bg-white dark:bg-slate-900 hover:shadow-lg hover:-translate-y-1 transition-all duration-200 group"
            >
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform mb-3"
                style={{ background: action.bg, color: action.color, width: 52, height: 52 }}
              >
                <action.icon className="h-6 w-6" />
              </div>
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                {action.label}
              </span>
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}
