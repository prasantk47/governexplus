import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { firefighterApi } from '../../services/api';
import toast from 'react-hot-toast';
import {
  EyeIcon,
  ExclamationTriangleIcon,
  StopIcon,
  PlayIcon,
  // ClockIcon,
  UserIcon,
  ServerIcon,
  CommandLineIcon,
  ShieldExclamationIcon,
  // ArrowPathIcon,
  BellAlertIcon,
  VideoCameraIcon,
} from '@heroicons/react/24/outline';

interface ActiveSession {
  id: string;
  user: string;
  userId: string;
  firefighterId: string;
  system: string;
  reason: string;
  startTime: string;
  duration: number;
  maxDuration: number;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  status: 'active' | 'warning' | 'overtime';
  activityCount: number;
  anomalyCount: number;
  recentCommands: {
    timestamp: string;
    command: string;
    risk: 'safe' | 'sensitive' | 'dangerous';
  }[];
}

interface ActivityLog {
  id: string;
  sessionId: string;
  timestamp: string;
  type: 'command' | 'transaction' | 'data_access' | 'config_change';
  action: string;
  target: string;
  risk: 'safe' | 'sensitive' | 'dangerous';
  flagged: boolean;
}

export function LiveSessionMonitor() {
  const queryClient = useQueryClient();
  const [selectedSession, setSelectedSession] = useState<ActiveSession | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(10);
  const [emergencyStopping, setEmergencyStopping] = useState(false);

  const { data: sessionsData, refetch: refetchSessions } = useQuery({
    queryKey: ['firefighter', 'activeSessions'],
    queryFn: () => firefighterApi.getActiveSessions().then(r => r.data),
    refetchInterval: autoRefresh ? refreshInterval * 1000 : false,
  });
  const sessions: ActiveSession[] = Array.isArray(sessionsData) ? sessionsData : (sessionsData as any)?.sessions || [];

  const { data: activitiesData } = useQuery({
    queryKey: ['firefighter', 'sessionActivities', selectedSession?.id],
    queryFn: () => firefighterApi.getSessionActivities(selectedSession!.id).then(r => r.data),
    enabled: !!selectedSession,
  });
  const activityLog: ActivityLog[] = Array.isArray(activitiesData) ? activitiesData : (activitiesData as any)?.activities || [];

  useEffect(() => {
    if (autoRefresh) {
      refetchSessions();
    }
  }, [autoRefresh, refetchSessions]);

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'critical': return 'text-red-600 bg-red-100';
      case 'high': return 'text-orange-600 bg-orange-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      default: return 'text-green-600 bg-green-100';
    }
  };

  const getCommandRiskColor = (risk: string) => {
    switch (risk) {
      case 'dangerous': return 'bg-red-100 text-red-800 border-red-200';
      case 'sensitive': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const formatDuration = (minutes: number) => {
    const h = Math.floor(minutes / 60);
    const m = Math.floor(minutes % 60);
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  };

  const getProgressColor = (duration: number, maxDuration: number) => {
    const pct = (duration / maxDuration) * 100;
    if (pct >= 100) return 'bg-red-500';
    if (pct >= 75) return 'bg-orange-500';
    if (pct >= 50) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const handleTerminateSession = async (sessionId: string) => {
    try {
      const userId = localStorage.getItem('userId') || 'admin';
      await firefighterApi.revokeSession(sessionId, userId, 'Terminated via live monitor');
      toast.success(`Session ${sessionId} terminated`);
      queryClient.invalidateQueries({ queryKey: ['firefighter', 'activeSessions'] });
    } catch {
      toast.error(`Failed to terminate session ${sessionId}`);
    }
  };

  const handleEmergencyStopAll = async () => {
    if (!sessions.length) return;
    setEmergencyStopping(true);
    const userId = localStorage.getItem('userId') || 'admin';
    let succeeded = 0;
    let failed = 0;
    for (const session of sessions) {
      try {
        await firefighterApi.revokeSession(session.id, userId, 'Emergency stop all');
        succeeded++;
      } catch {
        failed++;
      }
    }
    setEmergencyStopping(false);
    queryClient.invalidateQueries({ queryKey: ['firefighter', 'activeSessions'] });
    if (failed > 0) {
      toast.error(`Stopped ${succeeded} sessions, ${failed} failed`);
    } else {
      toast.success(`All ${succeeded} sessions terminated`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Live Session Monitor</h1>
          <p className="text-sm text-gray-500">
            Real-time monitoring of active firefighter sessions
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-primary-600"
              />
              Auto-refresh
            </label>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              disabled={!autoRefresh}
              className="border border-gray-300 rounded-md px-2 py-1 text-sm disabled:bg-gray-100"
            >
              <option value={5}>5s</option>
              <option value={10}>10s</option>
              <option value={30}>30s</option>
              <option value={60}>60s</option>
            </select>
          </div>
          <button
            onClick={handleEmergencyStopAll}
            disabled={emergencyStopping || sessions.length === 0}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm flex items-center gap-2 disabled:opacity-50"
          >
            <StopIcon className="h-4 w-4" />
            {emergencyStopping ? 'Stopping...' : 'Emergency Stop All'}
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <PlayIcon className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{sessions.length}</p>
              <p className="text-xs text-gray-500">Active Sessions</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <ExclamationTriangleIcon className="h-5 w-5 text-orange-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-orange-600">
                {sessions.filter((s) => s.status === 'warning' || s.status === 'overtime').length}
              </p>
              <p className="text-xs text-gray-500">Requires Attention</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <ShieldExclamationIcon className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-red-600">
                {sessions.reduce((acc, s) => acc + s.anomalyCount, 0)}
              </p>
              <p className="text-xs text-gray-500">Anomalies Detected</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <CommandLineIcon className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {sessions.reduce((acc, s) => acc + s.activityCount, 0)}
              </p>
              <p className="text-xs text-gray-500">Total Activities</p>
            </div>
          </div>
        </div>
      </div>

      {/* Active Sessions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`bg-white rounded-lg shadow overflow-hidden ${
              session.status === 'overtime' ? 'ring-2 ring-red-500' :
              session.status === 'warning' ? 'ring-2 ring-orange-500' : ''
            }`}
          >
            {/* Session Header */}
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                    <UserIcon className="h-5 w-5 text-gray-600" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">{session.user}</span>
                      <span className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${getRiskColor(session.riskLevel)}`}>
                        {session.riskLevel}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">{session.firefighterId}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {session.status === 'warning' && (
                    <span className="flex items-center gap-1 text-xs text-orange-600">
                      <BellAlertIcon className="h-4 w-4" />
                      Near limit
                    </span>
                  )}
                  {session.status === 'overtime' && (
                    <span className="flex items-center gap-1 text-xs text-red-600 animate-pulse">
                      <ExclamationTriangleIcon className="h-4 w-4" />
                      Overtime!
                    </span>
                  )}
                  <button
                    onClick={() => setSelectedSession(session)}
                    className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
                    title="View Details"
                  >
                    <EyeIcon className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleTerminateSession(session.id)}
                    className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded"
                    title="Terminate Session"
                  >
                    <StopIcon className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* System & Reason */}
              <div className="flex items-center gap-2 text-sm mb-3">
                <ServerIcon className="h-4 w-4 text-gray-400" />
                <span className="text-gray-900">{session.system}</span>
              </div>
              <p className="text-xs text-gray-500 truncate">{session.reason}</p>

              {/* Duration Progress */}
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                  <span>Duration: {formatDuration(session.duration)}</span>
                  <span>Max: {formatDuration(session.maxDuration)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${getProgressColor(session.duration, session.maxDuration)}`}
                    style={{ width: `${Math.min((session.duration / session.maxDuration) * 100, 100)}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Recent Commands */}
            <div className="p-4 bg-gray-50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-700">Recent Commands</span>
                <span className="text-xs text-gray-500">{session.activityCount} total</span>
              </div>
              <div className="space-y-1">
                {(session.recentCommands ?? []).slice(0, 3).map((cmd, i) => (
                  <div
                    key={i}
                    className={`flex items-center justify-between p-2 rounded border text-xs ${getCommandRiskColor(cmd.risk)}`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-gray-400 font-mono">{cmd.timestamp}</span>
                      <span className="font-medium truncate max-w-[200px]">{cmd.command}</span>
                    </div>
                    {cmd.risk !== 'safe' && (
                      <ExclamationTriangleIcon className="h-4 w-4 flex-shrink-0" />
                    )}
                  </div>
                ))}
              </div>
              {session.anomalyCount > 0 && (
                <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                  <ExclamationTriangleIcon className="h-4 w-4 inline mr-1" />
                  {session.anomalyCount} anomalies detected - click to review
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Activity Feed */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Activity Feed</h2>
          <div className="flex items-center gap-2 text-sm">
            <span className="flex items-center gap-1 text-green-600">
              <span className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></span>
              Live
            </span>
          </div>
        </div>
        <div className="divide-y divide-gray-100 max-h-80 overflow-y-auto">
          {activityLog.map((activity) => (
            <div
              key={activity.id}
              className={`px-4 py-3 hover:bg-gray-50 ${activity.flagged ? 'bg-red-50' : ''}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 font-mono w-16">{activity.timestamp}</span>
                  <span className={`inline-flex px-1.5 py-0.5 rounded text-xs ${
                    activity.risk === 'dangerous' ? 'bg-red-100 text-red-700' :
                    activity.risk === 'sensitive' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {activity.type}
                  </span>
                  <span className="text-sm text-gray-900">{activity.action}</span>
                  <span className="text-sm text-gray-500">{activity.target}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{activity.sessionId}</span>
                  {activity.flagged && (
                    <ExclamationTriangleIcon className="h-4 w-4 text-red-500" />
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Session Detail Modal */}
      {selectedSession && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">Session Details: {selectedSession.id}</h2>
                <button
                  onClick={() => setSelectedSession(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  &times;
                </button>
              </div>
            </div>
            <div className="p-6 space-y-6">
              {/* User Info */}
              <div className="flex items-center gap-4">
                <div className="h-16 w-16 rounded-full bg-gray-200 flex items-center justify-center">
                  <UserIcon className="h-8 w-8 text-gray-600" />
                </div>
                <div>
                  <div className="text-lg font-medium text-gray-900">{selectedSession.user}</div>
                  <div className="text-sm text-gray-500">{selectedSession.userId}</div>
                  <div className="text-xs text-gray-400">{selectedSession.firefighterId}</div>
                </div>
              </div>

              {/* Session Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-50 rounded-lg p-3 text-center">
                  <p className="text-xl font-bold text-gray-900">{formatDuration(selectedSession.duration)}</p>
                  <p className="text-xs text-gray-500">Duration</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3 text-center">
                  <p className="text-xl font-bold text-gray-900">{selectedSession.activityCount}</p>
                  <p className="text-xs text-gray-500">Activities</p>
                </div>
                <div className={`rounded-lg p-3 text-center ${selectedSession.anomalyCount > 0 ? 'bg-red-50' : 'bg-gray-50'}`}>
                  <p className={`text-xl font-bold ${selectedSession.anomalyCount > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                    {selectedSession.anomalyCount}
                  </p>
                  <p className={`text-xs ${selectedSession.anomalyCount > 0 ? 'text-red-600' : 'text-gray-500'}`}>Anomalies</p>
                </div>
              </div>

              {/* Reason */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Reason for Access</h4>
                <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">{selectedSession.reason}</p>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <button className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm flex items-center justify-center gap-2">
                  <VideoCameraIcon className="h-4 w-4" />
                  View Session Recording
                </button>
                <button
                  onClick={() => { handleTerminateSession(selectedSession.id); setSelectedSession(null); }}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm flex items-center gap-2"
                >
                  <StopIcon className="h-4 w-4" />
                  Terminate
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
