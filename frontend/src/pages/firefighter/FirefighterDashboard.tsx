import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  FireIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  UserCircleIcon,
  PlayIcon,
  StopIcon,
} from '@heroicons/react/24/outline';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Table,
  Badge,
  RiskBadge,
  EmptyState,
} from '../../components/ui';

interface ActiveSession {
  id: string;
  user: string;
  userId: string;
  firefighterId: string;
  system: string;
  reason: string;
  startTime: string;
  duration: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  status: 'active' | 'ending_soon';
}

interface RecentSession {
  id: string;
  user: string;
  firefighterId: string;
  system: string;
  startTime: string;
  endTime: string;
  duration: string;
  actions: number;
  anomalies: number;
}

const activeSessions: ActiveSession[] = [
  {
    id: 'FF-001', user: 'Tom Davis', userId: 'tdavis',
    firefighterId: 'FF_EMERGENCY_SAP_01', system: 'SAP ECC',
    reason: 'Month-end closing support', startTime: '2024-01-20 14:30',
    duration: '2h 15m', riskLevel: 'high', status: 'active',
  },
  {
    id: 'FF-002', user: 'Mary Brown', userId: 'mbrown',
    firefighterId: 'FF_ADMIN_AWS', system: 'AWS Production',
    reason: 'Critical infrastructure patch', startTime: '2024-01-20 15:45',
    duration: '45m', riskLevel: 'critical', status: 'ending_soon',
  },
];

const recentSessions: RecentSession[] = [
  {
    id: 'FF-098', user: 'John Smith', firefighterId: 'FF_EMERGENCY_SAP_01',
    system: 'SAP ECC', startTime: '2024-01-19 09:00', endTime: '2024-01-19 11:30',
    duration: '2h 30m', actions: 45, anomalies: 0,
  },
  {
    id: 'FF-097', user: 'David Lee', firefighterId: 'FF_ADMIN_DB',
    system: 'Production Database', startTime: '2024-01-18 16:00', endTime: '2024-01-18 18:00',
    duration: '2h 00m', actions: 28, anomalies: 2,
  },
  {
    id: 'FF-096', user: 'Alice Wilson', firefighterId: 'FF_HR_ADMIN',
    system: 'Workday', startTime: '2024-01-17 10:00', endTime: '2024-01-17 11:00',
    duration: '1h 00m', actions: 12, anomalies: 0,
  },
];

export function FirefighterDashboard() {
  const recentColumns = [
    {
      key: 'session',
      header: 'Session',
      render: (s: RecentSession) => (
        <div>
          <div className="text-sm font-medium text-primary-600">{s.id}</div>
          <div className="text-xs text-gray-400">{s.firefighterId}</div>
        </div>
      ),
    },
    {
      key: 'user',
      header: 'User',
      render: (s: RecentSession) => <span className="text-sm text-gray-900">{s.user}</span>,
    },
    {
      key: 'system',
      header: 'System',
      render: (s: RecentSession) => <span className="text-sm text-gray-500">{s.system}</span>,
    },
    {
      key: 'duration',
      header: 'Duration',
      render: (s: RecentSession) => <span className="text-sm text-gray-500">{s.duration}</span>,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (s: RecentSession) => <span className="text-sm text-gray-500">{s.actions}</span>,
    },
    {
      key: 'anomalies',
      header: 'Anomalies',
      render: (s: RecentSession) => (
        s.anomalies > 0 ? (
          <Badge variant="danger" size="sm">
            <ExclamationTriangleIcon className="h-3 w-3 mr-0.5" />
            {s.anomalies}
          </Badge>
        ) : (
          <Badge variant="success" size="sm">
            <CheckCircleIcon className="h-3 w-3 mr-0.5" />
            None
          </Badge>
        )
      ),
    },
    {
      key: 'review',
      header: '',
      className: 'text-right',
      render: (s: RecentSession) => (
        <button
          onClick={() => toast.success(`Opening session log for ${s.id}`)}
          className="text-xs text-primary-600 hover:text-primary-800 font-medium transition-colors"
        >
          View Log
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Firefighter Dashboard"
        subtitle="Monitor and manage emergency privileged access sessions"
        actions={
          <Button size="sm" icon={<FireIcon className="h-4 w-4" />} href="/firefighter/request">
            Request Emergency Access
          </Button>
        }
      />

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <StatCard title="Active Sessions" value={activeSessions.length} icon={PlayIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Avg. Duration" value="1h 30m" icon={ClockIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Completed (7D)" value={23} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Anomalies (7D)" value={3} icon={ExclamationTriangleIcon} iconBgColor="stat-icon-red" iconColor="" />
      </div>

      {/* Active Sessions */}
      <Card padding="none">
        <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
          <div className="flex items-center">
            <FireIcon className="h-4 w-4 text-orange-500 mr-2" />
            <h2 className="text-sm font-semibold text-gray-900">Active Sessions</h2>
          </div>
          <Link
            to="/firefighter/sessions"
            className="text-xs text-primary-600 hover:text-primary-800 font-medium transition-colors"
          >
            View All Sessions
          </Link>
        </div>

        {activeSessions.length > 0 ? (
          <div className="divide-y divide-white/10">
            {activeSessions.map((session) => (
              <div key={session.id} className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start">
                    <div className="flex-shrink-0">
                      <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-orange-100 to-orange-200 flex items-center justify-center">
                        <UserCircleIcon className="h-6 w-6 text-orange-600" />
                      </div>
                    </div>
                    <div className="ml-3">
                      <div className="flex items-center gap-2">
                        <h3 className="text-xs font-semibold text-gray-900">{session.user}</h3>
                        <RiskBadge level={session.riskLevel} />
                        {session.status === 'ending_soon' && (
                          <Badge variant="warning" size="sm">
                            <ClockIcon className="h-3 w-3 mr-0.5" />
                            Ending Soon
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-gray-500">
                        {session.firefighterId} &bull; {session.system}
                      </p>
                      <p className="mt-0.5 text-xs text-gray-600">{session.reason}</p>
                      <div className="mt-1 flex items-center text-xs text-gray-400">
                        <ClockIcon className="h-3 w-3 mr-1" />
                        Started: {session.startTime} &bull; Duration: {session.duration}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => toast.success(`Opening live monitor for session ${session.id}`)}
                    >
                      Monitor
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      icon={<StopIcon className="h-3.5 w-3.5" />}
                      onClick={() => toast.success(`Session ${session.id} terminated`)}
                    >
                      End
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-8">
            <EmptyState
              icon={<CheckCircleIcon className="h-8 w-8 text-green-400" />}
              title="No active sessions"
              description="No active firefighter sessions"
            />
          </div>
        )}
      </Card>

      {/* Recent Sessions */}
      <Card padding="none">
        <div className="px-6 py-4 border-b border-white/20">
          <h2 className="text-sm font-semibold text-gray-900">Recent Sessions</h2>
        </div>
        <Table columns={recentColumns} data={recentSessions} emptyMessage="No recent sessions" />
      </Card>

      {/* Firefighter IDs Overview */}
      <Card>
        <div className="px-6 py-4 border-b border-white/20">
          <h2 className="text-sm font-semibold text-gray-900">Available Firefighter IDs</h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              { id: 'FF_EMERGENCY_SAP_01', desc: 'SAP ECC Emergency Admin', status: 'Available' },
              { id: 'FF_ADMIN_AWS', desc: 'AWS Production Admin', status: 'In Use' },
              { id: 'FF_ADMIN_DB', desc: 'Database Admin', status: 'Available' },
            ].map((ff) => (
              <div key={ff.id} className="p-3 bg-white/30 backdrop-blur-sm border border-white/40 rounded-xl">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-900">{ff.id}</span>
                  <Badge variant={ff.status === 'Available' ? 'success' : 'warning'} size="sm">
                    {ff.status}
                  </Badge>
                </div>
                <p className="mt-0.5 text-xs text-gray-500">{ff.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}
