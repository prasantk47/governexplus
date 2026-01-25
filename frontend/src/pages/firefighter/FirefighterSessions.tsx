import { useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  FireIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  PlayIcon,
  StopIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';

interface Session {
  id: string;
  user: string;
  userId: string;
  firefighterId: string;
  system: string;
  reason: string;
  startTime: string;
  endTime: string | null;
  duration: string;
  status: 'active' | 'completed' | 'terminated';
  actions: number;
  anomalies: number;
  approvedBy: string;
}

const mockSessions: Session[] = [
  {
    id: 'FF-2024-001',
    user: 'Tom Davis',
    userId: 'tdavis',
    firefighterId: 'FF_EMERGENCY_SAP_01',
    system: 'SAP ECC',
    reason: 'Month-end closing support - need to correct posting errors',
    startTime: '2024-01-20 14:30',
    endTime: null,
    duration: '2h 15m (ongoing)',
    status: 'active',
    actions: 28,
    anomalies: 0,
    approvedBy: 'John Manager',
  },
  {
    id: 'FF-2024-002',
    user: 'Mary Brown',
    userId: 'mbrown',
    firefighterId: 'FF_ADMIN_AWS',
    system: 'AWS Production',
    reason: 'Critical infrastructure patch deployment',
    startTime: '2024-01-20 15:45',
    endTime: null,
    duration: '45m (ongoing)',
    status: 'active',
    actions: 12,
    anomalies: 0,
    approvedBy: 'IT Security Team',
  },
  {
    id: 'FF-2024-003',
    user: 'John Smith',
    userId: 'jsmith',
    firefighterId: 'FF_EMERGENCY_SAP_01',
    system: 'SAP ECC',
    reason: 'Emergency vendor master data correction',
    startTime: '2024-01-19 09:00',
    endTime: '2024-01-19 11:30',
    duration: '2h 30m',
    status: 'completed',
    actions: 45,
    anomalies: 0,
    approvedBy: 'Sarah Director',
  },
  {
    id: 'FF-2024-004',
    user: 'David Lee',
    userId: 'dlee',
    firefighterId: 'FF_ADMIN_DB',
    system: 'Production Database',
    reason: 'Database performance issue investigation',
    startTime: '2024-01-18 16:00',
    endTime: '2024-01-18 18:00',
    duration: '2h 00m',
    status: 'completed',
    actions: 28,
    anomalies: 2,
    approvedBy: 'DBA Manager',
  },
  {
    id: 'FF-2024-005',
    user: 'Alice Wilson',
    userId: 'awilson',
    firefighterId: 'FF_HR_ADMIN',
    system: 'Workday',
    reason: 'Emergency payroll correction',
    startTime: '2024-01-17 10:00',
    endTime: '2024-01-17 11:00',
    duration: '1h 00m',
    status: 'completed',
    actions: 12,
    anomalies: 0,
    approvedBy: 'Auto-approved',
  },
  {
    id: 'FF-2024-006',
    user: 'Bob Johnson',
    userId: 'bjohnson',
    firefighterId: 'FF_EMERGENCY_SAP_02',
    system: 'SAP ECC',
    reason: 'System error investigation',
    startTime: '2024-01-16 14:00',
    endTime: '2024-01-16 14:45',
    duration: '45m',
    status: 'terminated',
    actions: 8,
    anomalies: 3,
    approvedBy: 'IT Manager',
  },
  {
    id: 'FF-2024-007',
    user: 'Carol White',
    userId: 'cwhite',
    firefighterId: 'FF_NETWORK_ADMIN',
    system: 'Network Infrastructure',
    reason: 'Network outage remediation',
    startTime: '2024-01-15 08:30',
    endTime: '2024-01-15 09:15',
    duration: '45m',
    status: 'completed',
    actions: 15,
    anomalies: 0,
    approvedBy: 'Network Manager',
  },
];

const statusConfig = {
  active: { color: 'bg-green-100 text-green-800', label: 'Active', icon: PlayIcon },
  completed: { color: 'bg-gray-100 text-gray-800', label: 'Completed', icon: CheckCircleIcon },
  terminated: { color: 'bg-red-100 text-red-800', label: 'Terminated', icon: StopIcon },
};

export function FirefighterSessions() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dateFilter, setDateFilter] = useState<string>('all');

  const filteredSessions = mockSessions.filter((session) => {
    const matchesSearch =
      session.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
      session.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      session.firefighterId.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || session.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const activeCount = mockSessions.filter((s) => s.status === 'active').length;
  const completedCount = mockSessions.filter((s) => s.status === 'completed').length;
  const totalAnomalies = mockSessions.reduce((acc, s) => acc + s.anomalies, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Firefighter Sessions</h1>
          <p className="mt-1 text-sm text-gray-500">
            View and manage all emergency access sessions
          </p>
        </div>
        <Link
          to="/firefighter/request"
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-orange-600 hover:bg-orange-700"
        >
          <FireIcon className="h-5 w-5 mr-2" />
          New Request
        </Link>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="stat-card-accent border-green-400">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-green">
              <PlayIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Active Now</div>
              <div className="stat-value text-green-600">{activeCount}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-gray">
              <CheckCircleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Completed (30d)</div>
              <div className="stat-value">{completedCount}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-blue">
              <ClockIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Avg Duration</div>
              <div className="stat-value">1h 25m</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-red">
              <ExclamationTriangleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Anomalies (30d)</div>
              <div className="stat-value text-red-600">{totalAnomalies}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by user, session ID, or firefighter ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-orange-500 focus:border-orange-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-5 w-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-orange-500 focus:border-orange-500"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="terminated">Terminated</option>
            </select>
            <select
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-orange-500 focus:border-orange-500"
            >
              <option value="all">All Time</option>
              <option value="today">Today</option>
              <option value="week">This Week</option>
              <option value="month">This Month</option>
            </select>
          </div>
        </div>
      </div>

      {/* Sessions Table */}
      <div className="card overflow-hidden">
        <table className="min-w-full divide-y divide-gray-100">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Session
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                System
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Duration
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Anomalies
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Review
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {filteredSessions.map((session) => {
              const statusInfo = statusConfig[session.status];
              const StatusIcon = statusInfo.icon;

              return (
                <tr key={session.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <FireIcon className="h-4 w-4 text-orange-500 mr-2" />
                      <div>
                        <div className="text-sm font-medium text-primary-600">{session.id}</div>
                        <div className="text-xs text-gray-500">{session.firefighterId}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{session.user}</div>
                    <div className="text-xs text-gray-500">Approved by: {session.approvedBy}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {session.system}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusInfo.color}`}
                    >
                      <StatusIcon className="h-3 w-3 mr-1" />
                      {statusInfo.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{session.duration}</div>
                    <div className="text-xs text-gray-500">{session.startTime}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {session.actions}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {session.anomalies > 0 ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
                        {session.anomalies}
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        <CheckCircleIcon className="h-3 w-3 mr-1" />
                        None
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => toast.success(`Opening session log for ${session.id}...`)}
                      className="text-primary-600 hover:text-primary-900 mr-3"
                    >
                      <EyeIcon className="h-4 w-4 inline mr-1" />
                      View Log
                    </button>
                    {session.status === 'active' && (
                      <button
                        onClick={() => toast.success(`Session ${session.id} terminated`)}
                        className="text-red-600 hover:text-red-900"
                      >
                        <StopIcon className="h-4 w-4 inline mr-1" />
                        End
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredSessions.length === 0 && (
          <div className="text-center py-12">
            <FireIcon className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-gray-500">No sessions found matching your criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}
