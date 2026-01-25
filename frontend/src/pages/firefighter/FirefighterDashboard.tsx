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
    id: 'FF-001',
    user: 'Tom Davis',
    userId: 'tdavis',
    firefighterId: 'FF_EMERGENCY_SAP_01',
    system: 'SAP ECC',
    reason: 'Month-end closing support',
    startTime: '2024-01-20 14:30',
    duration: '2h 15m',
    riskLevel: 'high',
    status: 'active',
  },
  {
    id: 'FF-002',
    user: 'Mary Brown',
    userId: 'mbrown',
    firefighterId: 'FF_ADMIN_AWS',
    system: 'AWS Production',
    reason: 'Critical infrastructure patch',
    startTime: '2024-01-20 15:45',
    duration: '45m',
    riskLevel: 'critical',
    status: 'ending_soon',
  },
];

const recentSessions: RecentSession[] = [
  {
    id: 'FF-098',
    user: 'John Smith',
    firefighterId: 'FF_EMERGENCY_SAP_01',
    system: 'SAP ECC',
    startTime: '2024-01-19 09:00',
    endTime: '2024-01-19 11:30',
    duration: '2h 30m',
    actions: 45,
    anomalies: 0,
  },
  {
    id: 'FF-097',
    user: 'David Lee',
    firefighterId: 'FF_ADMIN_DB',
    system: 'Production Database',
    startTime: '2024-01-18 16:00',
    endTime: '2024-01-18 18:00',
    duration: '2h 00m',
    actions: 28,
    anomalies: 2,
  },
  {
    id: 'FF-096',
    user: 'Alice Wilson',
    firefighterId: 'FF_HR_ADMIN',
    system: 'Workday',
    startTime: '2024-01-17 10:00',
    endTime: '2024-01-17 11:00',
    duration: '1h 00m',
    actions: 12,
    anomalies: 0,
  },
];

const riskConfig = {
  low: { color: 'bg-green-100 text-green-800' },
  medium: { color: 'bg-yellow-100 text-yellow-800' },
  high: { color: 'bg-orange-100 text-orange-800' },
  critical: { color: 'bg-red-100 text-red-800' },
};

export function FirefighterDashboard() {
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Firefighter Dashboard</h1>
          <p className="page-subtitle">
            Monitor and manage emergency privileged access sessions
          </p>
        </div>
        <Link
          to="/firefighter/request"
          className="inline-flex items-center px-3 py-1.5 border border-transparent rounded-md text-xs font-medium text-white bg-orange-600 hover:bg-orange-700"
        >
          <FireIcon className="h-4 w-4 mr-1.5" />
          Request Emergency Access
        </Link>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="stat-card-accent border-orange-400">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-orange">
              <PlayIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Active Sessions</div>
              <div className="stat-value text-orange-500">{activeSessions.length}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-blue">
              <ClockIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Avg. Duration</div>
              <div className="stat-value">1h 30m</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-green">
              <CheckCircleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Completed (7D)</div>
              <div className="stat-value">23</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-red">
              <ExclamationTriangleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Anomalies (7D)</div>
              <div className="stat-value text-red-500">3</div>
            </div>
          </div>
        </div>
      </div>

      {/* Active Sessions */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <div className="flex items-center">
            <FireIcon className="h-4 w-4 text-orange-500 mr-2" />
            <h2 className="section-title">Active Sessions</h2>
          </div>
          <Link
            to="/firefighter/sessions"
            className="text-xs text-primary-600 hover:text-primary-700 font-medium"
          >
            View All Sessions
          </Link>
        </div>

        {activeSessions.length > 0 ? (
          <div className="divide-y divide-gray-100">
            {activeSessions.map((session) => (
              <div key={session.id} className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start">
                    <div className="flex-shrink-0">
                      <div className="h-10 w-10 rounded-full bg-orange-100 flex items-center justify-center">
                        <UserCircleIcon className="h-6 w-6 text-orange-600" />
                      </div>
                    </div>
                    <div className="ml-3">
                      <div className="flex items-center">
                        <h3 className="text-xs font-semibold text-gray-900">{session.user}</h3>
                        <span
                          className={`ml-2 inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${
                            riskConfig[session.riskLevel].color
                          }`}
                        >
                          {session.riskLevel.toUpperCase()}
                        </span>
                        {session.status === 'ending_soon' && (
                          <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                            <ClockIcon className="h-3 w-3 mr-0.5" />
                            Ending Soon
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500">
                        {session.firefighterId} • {session.system}
                      </p>
                      <p className="mt-0.5 text-xs text-gray-600">{session.reason}</p>
                      <div className="mt-1 flex items-center text-xs text-gray-400">
                        <ClockIcon className="h-3 w-3 mr-1" />
                        Started: {session.startTime} • Duration: {session.duration}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => toast.success(`Opening live monitor for session ${session.id}`)}
                      className="btn-secondary"
                    >
                      Monitor
                    </button>
                    <button
                      onClick={() => toast.success(`Session ${session.id} terminated`)}
                      className="inline-flex items-center px-2.5 py-1 border border-red-300 rounded-md text-xs font-medium text-red-700 bg-white hover:bg-red-50"
                    >
                      <StopIcon className="h-3.5 w-3.5 mr-1" />
                      End
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <CheckCircleIcon className="mx-auto h-8 w-8 text-green-400" />
            <p className="mt-2 text-xs text-gray-500">No active firefighter sessions</p>
          </div>
        )}
      </div>

      {/* Recent Sessions */}
      <div className="card">
        <div className="card-header">
          <h2 className="section-title">Recent Sessions</h2>
        </div>
        <table className="min-w-full divide-y divide-gray-100">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Session
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                User
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                System
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Duration
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Actions
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Anomalies
              </th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                Review
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {recentSessions.map((session) => (
              <tr key={session.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="text-xs font-medium text-primary-600">{session.id}</div>
                  <div className="text-xs text-gray-400">{session.firefighterId}</div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-900">
                  {session.user}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                  {session.system}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                  {session.duration}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                  {session.actions}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {session.anomalies > 0 ? (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                      <ExclamationTriangleIcon className="h-3 w-3 mr-0.5" />
                      {session.anomalies}
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                      <CheckCircleIcon className="h-3 w-3 mr-0.5" />
                      None
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <button
                    onClick={() => toast.success(`Opening session log for ${session.id}`)}
                    className="text-xs text-primary-600 hover:text-primary-900 font-medium"
                  >
                    View Log
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Firefighter IDs Overview */}
      <div className="card">
        <div className="card-header">
          <h2 className="section-title">Available Firefighter IDs</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 border border-gray-100 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-gray-900">FF_EMERGENCY_SAP_01</span>
                <span className="inline-flex px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                  Available
                </span>
              </div>
              <p className="mt-0.5 text-xs text-gray-500">SAP ECC Emergency Admin</p>
            </div>
            <div className="p-3 border border-gray-100 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-gray-900">FF_ADMIN_AWS</span>
                <span className="inline-flex px-1.5 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800">
                  In Use
                </span>
              </div>
              <p className="mt-0.5 text-xs text-gray-500">AWS Production Admin</p>
            </div>
            <div className="p-3 border border-gray-100 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-gray-900">FF_ADMIN_DB</span>
                <span className="inline-flex px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                  Available
                </span>
              </div>
              <p className="mt-0.5 text-xs text-gray-500">Database Admin</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
