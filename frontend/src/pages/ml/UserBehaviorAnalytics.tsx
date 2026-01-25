/**
 * User Behavior Analytics (UEBA) Page
 * Advanced user behavior profiling, peer analysis, and risk tracking
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  UserCircleIcon,
  UsersIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ClockIcon,
  MapPinIcon,
  ShieldExclamationIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import api from '../../services/api';

interface UserProfile {
  user_id: string;
  risk_score: number;
  risk_level: string;
  risk_trend: string;
  behavioral_metrics: {
    login_regularity: number;
    access_pattern_consistency: number;
    data_access_volume_percentile: number;
    session_duration_avg_minutes: number;
    transaction_frequency_daily: number;
    off_hours_activity_ratio: number;
    peer_deviation_score: number;
  };
  access_patterns: {
    primary_systems: string[];
    typical_login_hours: { start: number; end: number };
    typical_locations: string[];
    most_used_transactions: string[];
  };
  risk_factors: Record<string, number>;
  anomaly_history: {
    total_anomalies_30d: number;
    critical_anomalies_30d: number;
    false_positive_rate: number;
  };
}

interface HighRiskUser {
  user_id: string;
  risk_score: number;
  risk_level: string;
  risk_trend: string;
  anomaly_count_30d: number;
  peer_deviation: number;
}

export function UserBehaviorAnalytics() {
  const [searchUser, setSearchUser] = useState('');
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [riskFilter, setRiskFilter] = useState<string>('all');

  // Fetch high-risk users
  const { data: highRiskData, isLoading: highRiskLoading } = useQuery({
    queryKey: ['highRiskUsers'],
    queryFn: async () => {
      const response = await api.get('/ml/ueba/high-risk-users', {
        params: { min_risk_score: 40, limit: 20 }
      });
      return response.data;
    },
  });

  // Fetch user profile when selected
  const { data: userProfile, isLoading: profileLoading } = useQuery({
    queryKey: ['userProfile', selectedUser],
    queryFn: async () => {
      const response = await api.get(`/ml/ueba/profile/${selectedUser}`);
      return response.data as UserProfile;
    },
    enabled: !!selectedUser,
  });

  // Fetch peer comparison
  const { data: peerData } = useQuery({
    queryKey: ['peerComparison', selectedUser],
    queryFn: async () => {
      const response = await api.get(`/ml/ueba/peers/${selectedUser}`);
      return response.data;
    },
    enabled: !!selectedUser,
  });

  // Fetch activity timeline
  const { data: timelineData } = useQuery({
    queryKey: ['activityTimeline', selectedUser],
    queryFn: async () => {
      const response = await api.get(`/ml/ueba/timeline/${selectedUser}`, {
        params: { days: 14 }
      });
      return response.data;
    },
    enabled: !!selectedUser,
  });

  // Fetch behavioral drift
  const { data: driftData } = useQuery({
    queryKey: ['behavioralDrift'],
    queryFn: async () => {
      const response = await api.get('/ml/ueba/behavioral-drift', {
        params: { days: 30 }
      });
      return response.data;
    },
  });

  const highRiskUsers: HighRiskUser[] = highRiskData?.users || [];

  const filteredUsers = highRiskUsers.filter(user => {
    if (riskFilter === 'all') return true;
    return user.risk_level === riskFilter;
  });

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'critical': return 'text-red-600 bg-red-100';
      case 'high': return 'text-orange-600 bg-orange-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      default: return 'text-green-600 bg-green-100';
    }
  };

  const getTrendIcon = (trend: string) => {
    if (trend === 'increasing') return <ArrowTrendingUpIcon className="h-4 w-4 text-red-500" />;
    if (trend === 'decreasing') return <ArrowTrendingDownIcon className="h-4 w-4 text-green-500" />;
    return <span className="h-4 w-4 text-gray-400">—</span>;
  };

  const handleSearch = () => {
    if (searchUser.trim()) {
      setSelectedUser(searchUser.trim().toLowerCase());
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-lg">
            <UsersIcon className="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">User Behavior Analytics</h1>
            <p className="text-sm text-gray-500">Advanced UEBA with peer analysis and behavioral profiling</p>
          </div>
        </div>
        <Link to="/ml" className="btn-secondary">
          Back to ML Dashboard
        </Link>
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[250px]">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchUser}
                onChange={(e) => setSearchUser(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search user by ID..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-4 w-4 text-gray-400" />
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="border border-gray-300 rounded-lg text-sm px-3 py-2"
            >
              <option value="all">All Risk Levels</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <button onClick={handleSearch} className="btn-primary">
            Analyze User
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* High Risk Users List */}
        <div className="lg:col-span-1 bg-white rounded-lg border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-900 flex items-center gap-2">
              <ShieldExclamationIcon className="h-5 w-5 text-red-500" />
              High Risk Users
            </h2>
            <span className="text-xs text-gray-500">{filteredUsers.length} users</span>
          </div>
          <div className="max-h-[500px] overflow-y-auto divide-y divide-gray-100">
            {highRiskLoading ? (
              <div className="p-4 text-center text-gray-500">Loading...</div>
            ) : filteredUsers.length === 0 ? (
              <div className="p-4 text-center text-gray-500">No users found</div>
            ) : (
              filteredUsers.map((user) => (
                <button
                  key={user.user_id}
                  onClick={() => setSelectedUser(user.user_id)}
                  className={clsx(
                    'w-full p-3 text-left hover:bg-gray-50 transition-colors',
                    selectedUser === user.user_id && 'bg-primary-50'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <UserCircleIcon className="h-8 w-8 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{user.user_id}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className={clsx('px-1.5 py-0.5 rounded text-xs font-medium', getRiskColor(user.risk_level))}>
                            {user.risk_level}
                          </span>
                          {getTrendIcon(user.risk_trend)}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={clsx('text-lg font-bold', getRiskColor(user.risk_level).split(' ')[0])}>
                        {user.risk_score}
                      </p>
                      <p className="text-xs text-gray-500">{user.anomaly_count_30d} anomalies</p>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* User Profile Details */}
        <div className="lg:col-span-2 space-y-4">
          {!selectedUser ? (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
              <UserCircleIcon className="h-16 w-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Select a User</h3>
              <p className="text-sm text-gray-500">
                Select a user from the list or search by user ID to view their behavior analytics
              </p>
            </div>
          ) : profileLoading ? (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
              <div className="animate-spin h-8 w-8 border-2 border-primary-500 border-t-transparent rounded-full mx-auto"></div>
              <p className="mt-4 text-gray-500">Loading profile...</p>
            </div>
          ) : userProfile ? (
            <>
              {/* Profile Header */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-gray-100 rounded-full">
                      <UserCircleIcon className="h-12 w-12 text-gray-600" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{userProfile.user_id}</h3>
                      <div className="flex items-center gap-3 mt-1">
                        <span className={clsx('px-2 py-1 rounded text-sm font-medium', getRiskColor(userProfile.risk_level))}>
                          {userProfile.risk_level.toUpperCase()} RISK
                        </span>
                        <span className="flex items-center gap-1 text-sm text-gray-500">
                          {getTrendIcon(userProfile.risk_trend)}
                          {userProfile.risk_trend}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-3xl font-bold text-gray-900">{userProfile.risk_score}</p>
                    <p className="text-sm text-gray-500">Risk Score</p>
                  </div>
                </div>
              </div>

              {/* Behavioral Metrics */}
              <div className="bg-white rounded-lg border border-gray-200">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h4 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                    <ChartBarIcon className="h-5 w-5 text-blue-500" />
                    Behavioral Metrics
                  </h4>
                </div>
                <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <p className="text-2xl font-semibold text-blue-600">
                      {Math.round(userProfile.behavioral_metrics.login_regularity * 100)}%
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Login Regularity</p>
                  </div>
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <p className="text-2xl font-semibold text-green-600">
                      {Math.round(userProfile.behavioral_metrics.access_pattern_consistency * 100)}%
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Pattern Consistency</p>
                  </div>
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <p className="text-2xl font-semibold text-purple-600">
                      {userProfile.behavioral_metrics.transaction_frequency_daily}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Daily Transactions</p>
                  </div>
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <p className={clsx(
                      'text-2xl font-semibold',
                      userProfile.behavioral_metrics.off_hours_activity_ratio > 0.15 ? 'text-red-600' : 'text-green-600'
                    )}>
                      {Math.round(userProfile.behavioral_metrics.off_hours_activity_ratio * 100)}%
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Off-Hours Activity</p>
                  </div>
                </div>
              </div>

              {/* Access Patterns & Peer Comparison */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Access Patterns */}
                <div className="bg-white rounded-lg border border-gray-200">
                  <div className="px-4 py-3 border-b border-gray-200">
                    <h4 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                      <MapPinIcon className="h-5 w-5 text-green-500" />
                      Access Patterns
                    </h4>
                  </div>
                  <div className="p-4 space-y-3">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Primary Systems</p>
                      <div className="flex flex-wrap gap-1">
                        {userProfile.access_patterns.primary_systems.map((sys) => (
                          <span key={sys} className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                            {sys}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Login Hours</p>
                      <p className="text-sm text-gray-900">
                        {userProfile.access_patterns.typical_login_hours.start}:00 - {userProfile.access_patterns.typical_login_hours.end}:00
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Locations</p>
                      <div className="flex flex-wrap gap-1">
                        {userProfile.access_patterns.typical_locations.map((loc) => (
                          <span key={loc} className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                            {loc}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Peer Comparison */}
                <div className="bg-white rounded-lg border border-gray-200">
                  <div className="px-4 py-3 border-b border-gray-200">
                    <h4 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                      <UsersIcon className="h-5 w-5 text-purple-500" />
                      Peer Comparison
                    </h4>
                  </div>
                  <div className="p-4">
                    {peerData ? (
                      <div className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-gray-500">User Risk Score</span>
                          <span className="text-lg font-bold">{peerData.user_risk_score}</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-gray-500">Peer Group Average</span>
                          <span className="text-lg font-semibold text-gray-600">{peerData.peer_group_avg_risk}</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-gray-500">Deviation</span>
                          <span className={clsx(
                            'text-lg font-semibold',
                            peerData.deviation_from_peers > 0 ? 'text-red-600' : 'text-green-600'
                          )}>
                            {peerData.deviation_from_peers > 0 ? '+' : ''}{peerData.deviation_from_peers}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-gray-500">Percentile</span>
                          <span className="text-lg font-semibold">{peerData.percentile_in_group}%</span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-gray-500 text-sm">Loading peer data...</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Activity Timeline */}
              {timelineData && (
                <div className="bg-white rounded-lg border border-gray-200">
                  <div className="px-4 py-3 border-b border-gray-200">
                    <h4 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                      <ClockIcon className="h-5 w-5 text-orange-500" />
                      Activity Timeline (14 Days)
                    </h4>
                  </div>
                  <div className="p-4">
                    <div className="grid grid-cols-7 gap-1">
                      {timelineData.timeline.slice(0, 14).map((day: any, idx: number) => (
                        <div
                          key={idx}
                          className={clsx(
                            'p-2 rounded text-center text-xs',
                            day.anomalies_detected > 0 ? 'bg-red-100' :
                            day.risk_score > 50 ? 'bg-yellow-100' : 'bg-green-100'
                          )}
                          title={`${day.date}: ${day.transaction_count} transactions, ${day.anomalies_detected} anomalies`}
                        >
                          <p className="font-medium">{day.risk_score}</p>
                          <p className="text-gray-500">{day.date.slice(-5)}</p>
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 grid grid-cols-4 gap-4 text-center">
                      <div>
                        <p className="text-lg font-semibold">{timelineData.summary.avg_daily_transactions}</p>
                        <p className="text-xs text-gray-500">Avg Transactions/Day</p>
                      </div>
                      <div>
                        <p className="text-lg font-semibold text-red-600">{timelineData.summary.total_anomalies}</p>
                        <p className="text-xs text-gray-500">Total Anomalies</p>
                      </div>
                      <div>
                        <p className="text-lg font-semibold">{timelineData.summary.avg_risk_score}</p>
                        <p className="text-xs text-gray-500">Avg Risk Score</p>
                      </div>
                      <div>
                        <p className="text-lg font-semibold text-orange-600">{timelineData.summary.total_sensitive_access}</p>
                        <p className="text-xs text-gray-500">Sensitive Access</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Risk Factors */}
              <div className="bg-white rounded-lg border border-gray-200">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h4 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                    <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
                    Risk Factors
                  </h4>
                </div>
                <div className="p-4">
                  <div className="space-y-3">
                    {Object.entries(userProfile.risk_factors).map(([factor, value]) => (
                      <div key={factor} className="flex items-center justify-between">
                        <span className="text-sm text-gray-700 capitalize">{factor.replace(/_/g, ' ')}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-32 bg-gray-200 rounded-full h-2">
                            <div
                              className={clsx(
                                'h-2 rounded-full',
                                (value as number) > 10 ? 'bg-red-500' :
                                (value as number) > 5 ? 'bg-yellow-500' : 'bg-green-500'
                              )}
                              style={{ width: `${Math.min((value as number) * 5, 100)}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium w-8">{value as number}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>

      {/* Behavioral Drift Section */}
      {driftData && driftData.drifting_users.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-medium text-gray-900 flex items-center gap-2">
              <ArrowTrendingUpIcon className="h-5 w-5 text-orange-500" />
              Behavioral Drift Detected
            </h2>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {driftData.drifting_users.map((user: any) => (
                <div
                  key={user.user_id}
                  className="p-3 bg-orange-50 border border-orange-200 rounded-lg cursor-pointer hover:bg-orange-100"
                  onClick={() => setSelectedUser(user.user_id)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-gray-900">{user.user_id}</span>
                    <span className={clsx(
                      'px-2 py-0.5 rounded text-xs font-medium',
                      user.drift_direction === 'positive' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                    )}>
                      {user.drift_score > 0 ? '+' : ''}{user.drift_score}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600">
                    Affected: {user.affected_metrics.join(', ')}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Confidence: {Math.round(user.confidence * 100)}%
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
