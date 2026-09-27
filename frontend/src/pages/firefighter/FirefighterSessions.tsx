import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { firefighterApi } from '../../services/api';
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

const statusConfig = {
  active: { color: 'bg-green-100 text-green-800', label: 'Active', icon: PlayIcon },
  completed: { color: 'bg-gray-100 text-gray-800', label: 'Completed', icon: CheckCircleIcon },
  terminated: { color: 'bg-red-100 text-red-800', label: 'Terminated', icon: StopIcon },
};

export function FirefighterSessions() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dateFilter, setDateFilter] = useState<string>('all');
  const [viewingSession, setViewingSession] = useState<Session | null>(null);

  const { data: sessionsData } = useQuery({
    queryKey: ['firefighter', 'sessions'],
    queryFn: () => firefighterApi.listSessions().then(r => r.data),
  });
  const sessions: Session[] = Array.isArray(sessionsData) ? sessionsData : (sessionsData as any)?.sessions || [];

  const handleEndSession = async (sessionId: string) => {
    try {
      const userId = localStorage.getItem('userId') || 'admin';
      await firefighterApi.endSession(sessionId, userId);
      toast.success(`Session ${sessionId} ended`);
      queryClient.invalidateQueries({ queryKey: ['firefighter', 'sessions'] });
    } catch {
      toast.error('Failed to end session');
    }
  };

  // Compute avg duration from actual data
  const parseDuration = (d: string): number => {
    const hMatch = d.match(/(\d+)\s*h/);
    const mMatch = d.match(/(\d+)\s*m/);
    return (hMatch ? parseInt(hMatch[1]) * 60 : 0) + (mMatch ? parseInt(mMatch[1]) : 0);
  };
  const avgMins = sessions.length > 0
    ? Math.round(sessions.reduce((sum, s) => sum + parseDuration(s.duration), 0) / sessions.length)
    : 0;
  const avgDurationStr = avgMins > 0 ? `${Math.floor(avgMins / 60)}h ${avgMins % 60}m` : '0m';

  const filteredSessions = sessions.filter((session) => {
    const matchesSearch =
      session.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(session.id).toLowerCase().includes(searchTerm.toLowerCase()) ||
      session.firefighterId.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || session.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const activeCount = sessions.filter((s) => s.status === 'active').length;
  const completedCount = sessions.filter((s) => s.status === 'completed').length;
  const totalAnomalies = sessions.reduce((acc, s) => acc + s.anomalies, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Privileged Access Sessions</h1>
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
              <div className="stat-value">{avgDurationStr}</div>
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
              placeholder="Search by user, session ID, or privileged access ID..."
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
                      onClick={() => setViewingSession(session)}
                      className="text-primary-600 hover:text-primary-900 mr-3"
                    >
                      <EyeIcon className="h-4 w-4 inline mr-1" />
                      View Log
                    </button>
                    {session.status === 'active' && (
                      <button
                        onClick={() => handleEndSession(session.id)}
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

      {/* Session Detail Modal */}
      {viewingSession && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Session Log: {viewingSession.id}</h2>
              <button onClick={() => setViewingSession(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <div className="p-5 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div><p className="text-xs text-gray-500">User</p><p className="text-sm font-medium">{viewingSession.user}</p></div>
                <div><p className="text-xs text-gray-500">Privileged Access ID</p><p className="text-sm font-medium">{viewingSession.firefighterId}</p></div>
                <div><p className="text-xs text-gray-500">System</p><p className="text-sm">{viewingSession.system}</p></div>
                <div><p className="text-xs text-gray-500">Status</p><span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig[viewingSession.status].color}`}>{statusConfig[viewingSession.status].label}</span></div>
                <div><p className="text-xs text-gray-500">Duration</p><p className="text-sm">{viewingSession.duration}</p></div>
                <div><p className="text-xs text-gray-500">Actions Performed</p><p className="text-sm">{viewingSession.actions}</p></div>
                <div><p className="text-xs text-gray-500">Anomalies</p><p className="text-sm">{viewingSession.anomalies > 0 ? <span className="text-red-600 font-medium">{viewingSession.anomalies}</span> : 'None'}</p></div>
                <div><p className="text-xs text-gray-500">Approved By</p><p className="text-sm">{viewingSession.approvedBy}</p></div>
                <div><p className="text-xs text-gray-500">Start Time</p><p className="text-sm">{viewingSession.startTime}</p></div>
                <div><p className="text-xs text-gray-500">End Time</p><p className="text-sm">{viewingSession.endTime || 'In progress'}</p></div>
              </div>
              <div><p className="text-xs text-gray-500">Reason</p><p className="text-sm bg-gray-50 dark:bg-gray-700 p-2 rounded">{viewingSession.reason}</p></div>
            </div>
            <div className="flex justify-end gap-2 p-5 border-t border-gray-200 dark:border-gray-700">
              {viewingSession.status === 'active' && (
                <button onClick={() => { handleEndSession(viewingSession.id); setViewingSession(null); }} className="px-4 py-2 text-sm text-white bg-red-600 rounded-md hover:bg-red-700">End Session</button>
              )}
              <button onClick={() => setViewingSession(null)} className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
