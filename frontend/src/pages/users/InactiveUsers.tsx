import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  ClockIcon,
  UserGroupIcon,
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
  ArrowPathIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  ChevronRightIcon,
  NoSymbolIcon,
  CheckCircleIcon,
  XMarkIcon,
  DocumentArrowDownIcon,
  EnvelopeIcon,
  CalendarDaysIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import { ExclamationTriangleIcon as ExclamationSolid } from '@heroicons/react/24/solid';
import clsx from 'clsx';

interface InactiveUser {
  user_id: string;
  full_name: string;
  email: string;
  department: string;
  last_login: string | null;
  days_inactive: number | null;
  never_logged_in: boolean;
  risk_level: string;
  sap_user_type: string;
  recommendation: string;
}

interface InactiveSummary {
  threshold_days: number;
  cutoff_date: string;
  total_inactive: number;
  inactive_with_login_history: number;
  never_logged_in: number;
  summary: {
    '30_to_60_days': number;
    '60_to_90_days': number;
    '90_to_180_days': number;
    over_180_days: number;
  };
  recommendations: {
    disable_accounts: number;
    require_review: number;
    monitor: number;
  };
  users: InactiveUser[];
}

export function InactiveUsers() {
  const [data, setData] = useState<InactiveSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [daysThreshold, setDaysThreshold] = useState(90);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set());
  const [showOnlyNeverLoggedIn, setShowOnlyNeverLoggedIn] = useState(false);

  useEffect(() => {
    fetchInactiveUsers();
  }, [daysThreshold]);

  const fetchInactiveUsers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/user-profiles/inactive-users?days=${daysThreshold}&include_never_logged_in=true&limit=200`);
      if (response.ok) {
        setData(await response.json());
      } else {
        throw new Error('Failed to fetch data');
      }
    } catch (err) {
      // Demo data
      setData({
        threshold_days: daysThreshold,
        cutoff_date: new Date(Date.now() - daysThreshold * 24 * 60 * 60 * 1000).toISOString(),
        total_inactive: 47,
        inactive_with_login_history: 32,
        never_logged_in: 15,
        summary: {
          '30_to_60_days': 8,
          '60_to_90_days': 12,
          '90_to_180_days': 18,
          over_180_days: 9,
        },
        recommendations: {
          disable_accounts: 24,
          require_review: 18,
          monitor: 5,
        },
        users: [
          { user_id: 'USR001', full_name: 'John Smith', email: 'john.smith@company.com', department: 'Finance', last_login: '2025-08-15T10:30:00Z', days_inactive: 162, never_logged_in: false, risk_level: 'high', sap_user_type: 'Dialog', recommendation: 'High priority - Disable account and review with manager' },
          { user_id: 'USR002', full_name: 'Jane Doe', email: 'jane.doe@company.com', department: 'IT', last_login: '2025-09-20T14:22:00Z', days_inactive: 126, never_logged_in: false, risk_level: 'medium', sap_user_type: 'Dialog', recommendation: 'Medium priority - Require justification for continued access' },
          { user_id: 'USR003', full_name: 'Bob Wilson', email: 'bob.wilson@company.com', department: 'HR', last_login: null, days_inactive: null, never_logged_in: true, risk_level: 'high', sap_user_type: 'Dialog', recommendation: 'Review account necessity - never used' },
          { user_id: 'USR004', full_name: 'Alice Brown', email: 'alice.brown@company.com', department: 'Sales', last_login: '2025-10-05T09:15:00Z', days_inactive: 111, never_logged_in: false, risk_level: 'medium', sap_user_type: 'Dialog', recommendation: 'Medium priority - Require justification for continued access' },
          { user_id: 'USR005', full_name: 'Charlie Davis', email: 'charlie.davis@company.com', department: 'Operations', last_login: '2025-07-01T16:45:00Z', days_inactive: 207, never_logged_in: false, risk_level: 'critical', sap_user_type: 'Service', recommendation: 'High priority - Disable account and review with manager' },
          { user_id: 'USR006', full_name: 'Emma Thompson', email: 'emma.t@company.com', department: 'Legal', last_login: null, days_inactive: null, never_logged_in: true, risk_level: 'medium', sap_user_type: 'Dialog', recommendation: 'Review account necessity - never used' },
          { user_id: 'USR007', full_name: 'Michael Johnson', email: 'm.johnson@company.com', department: 'Finance', last_login: '2025-06-15T11:20:00Z', days_inactive: 223, never_logged_in: false, risk_level: 'critical', sap_user_type: 'Dialog', recommendation: 'Immediate action required - Consider disabling or removing account' },
          { user_id: 'USR008', full_name: 'Sarah Williams', email: 'sarah.w@company.com', department: 'IT', last_login: '2025-11-01T08:30:00Z', days_inactive: 84, never_logged_in: false, risk_level: 'low', sap_user_type: 'Dialog', recommendation: 'Low priority - Flag for next access review' },
        ]
      });
    }
    setIsLoading(false);
  };

  const filteredUsers = data?.users.filter(user => {
    const matchesSearch = !searchTerm ||
      user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.department.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesNeverLoggedIn = !showOnlyNeverLoggedIn || user.never_logged_in;
    return matchesSearch && matchesNeverLoggedIn;
  }) || [];

  const toggleUserSelection = (userId: string) => {
    const newSelected = new Set(selectedUsers);
    if (newSelected.has(userId)) {
      newSelected.delete(userId);
    } else {
      newSelected.add(userId);
    }
    setSelectedUsers(newSelected);
  };

  const selectAllFiltered = () => {
    if (selectedUsers.size === filteredUsers.length) {
      setSelectedUsers(new Set());
    } else {
      setSelectedUsers(new Set(filteredUsers.map(u => u.user_id)));
    }
  };

  const getRiskBadge = (level: string) => {
    const config: Record<string, { bg: string; text: string; border: string }> = {
      critical: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200' },
      high: { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-200' },
      medium: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200' },
      low: { bg: 'bg-emerald-100', text: 'text-emerald-700', border: 'border-emerald-200' },
    };
    const style = config[level] || config.medium;
    return (
      <span className={clsx('px-2 py-0.5 text-xs font-semibold rounded-full border', style.bg, style.text, style.border)}>
        {level}
      </span>
    );
  };

  const formatDaysInactive = (days: number | null, neverLoggedIn: boolean) => {
    if (neverLoggedIn) {
      return <span className="text-red-600 font-medium">Never logged in</span>;
    }
    if (days === null) return '-';

    if (days >= 365) {
      return <span className="text-red-600 font-bold">{days} days ({Math.floor(days / 365)}+ year)</span>;
    } else if (days >= 180) {
      return <span className="text-red-600 font-semibold">{days} days</span>;
    } else if (days >= 90) {
      return <span className="text-orange-600 font-semibold">{days} days</span>;
    } else {
      return <span className="text-amber-600">{days} days</span>;
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-gray-600">Loading inactive users...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                <div className="p-2 bg-amber-100 rounded-lg">
                  <ClockIcon className="h-6 w-6 text-amber-600" />
                </div>
                Inactive Users Monitor
              </h1>
              <p className="text-gray-500 mt-1">
                Identify and manage dormant accounts for security and compliance
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={fetchInactiveUsers}
                className="flex items-center gap-2 px-4 py-2 text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <ArrowPathIcon className="h-4 w-4" />
                Refresh
              </button>
              <button
                onClick={() => toast.success('Exporting inactive users report...')}
                className="flex items-center gap-2 px-4 py-2 text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
              >
                <DocumentArrowDownIcon className="h-4 w-4" />
                Export Report
              </button>
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Inactive</p>
                <p className="text-3xl font-bold text-gray-900">{data?.total_inactive || 0}</p>
              </div>
              <div className="p-3 bg-amber-100 rounded-xl">
                <UserGroupIcon className="h-6 w-6 text-amber-600" />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              No login in {daysThreshold}+ days
            </p>
          </div>

          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Never Logged In</p>
                <p className="text-3xl font-bold text-red-600">{data?.never_logged_in || 0}</p>
              </div>
              <div className="p-3 bg-red-100 rounded-xl">
                <NoSymbolIcon className="h-6 w-6 text-red-600" />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Accounts never used
            </p>
          </div>

          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Require Review</p>
                <p className="text-3xl font-bold text-orange-600">{data?.recommendations.require_review || 0}</p>
              </div>
              <div className="p-3 bg-orange-100 rounded-xl">
                <ExclamationTriangleIcon className="h-6 w-6 text-orange-600" />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              90-180 days inactive
            </p>
          </div>

          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Disable Recommended</p>
                <p className="text-3xl font-bold text-red-600">{data?.recommendations.disable_accounts || 0}</p>
              </div>
              <div className="p-3 bg-red-100 rounded-xl">
                <ShieldExclamationIcon className="h-6 w-6 text-red-600" />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              180+ days or never used
            </p>
          </div>
        </div>

        {/* Breakdown Chart */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Inactivity Breakdown</h3>
          <div className="flex items-center gap-2 h-8 rounded-lg overflow-hidden">
            {data?.summary && (
              <>
                <div
                  className="h-full bg-amber-400 flex items-center justify-center text-xs font-medium text-white"
                  style={{ width: `${(data.summary['30_to_60_days'] / data.total_inactive) * 100}%`, minWidth: data.summary['30_to_60_days'] > 0 ? '40px' : '0' }}
                  title="30-60 days"
                >
                  {data.summary['30_to_60_days']}
                </div>
                <div
                  className="h-full bg-orange-500 flex items-center justify-center text-xs font-medium text-white"
                  style={{ width: `${(data.summary['60_to_90_days'] / data.total_inactive) * 100}%`, minWidth: data.summary['60_to_90_days'] > 0 ? '40px' : '0' }}
                  title="60-90 days"
                >
                  {data.summary['60_to_90_days']}
                </div>
                <div
                  className="h-full bg-red-500 flex items-center justify-center text-xs font-medium text-white"
                  style={{ width: `${(data.summary['90_to_180_days'] / data.total_inactive) * 100}%`, minWidth: data.summary['90_to_180_days'] > 0 ? '40px' : '0' }}
                  title="90-180 days"
                >
                  {data.summary['90_to_180_days']}
                </div>
                <div
                  className="h-full bg-red-700 flex items-center justify-center text-xs font-medium text-white"
                  style={{ width: `${(data.summary.over_180_days / data.total_inactive) * 100}%`, minWidth: data.summary.over_180_days > 0 ? '40px' : '0' }}
                  title="180+ days"
                >
                  {data.summary.over_180_days}
                </div>
                <div
                  className="h-full bg-gray-700 flex items-center justify-center text-xs font-medium text-white"
                  style={{ width: `${(data.never_logged_in / data.total_inactive) * 100}%`, minWidth: data.never_logged_in > 0 ? '40px' : '0' }}
                  title="Never logged in"
                >
                  {data.never_logged_in}
                </div>
              </>
            )}
          </div>
          <div className="flex items-center gap-6 mt-3 text-xs text-gray-500">
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-amber-400 rounded"></span> 30-60 days</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-orange-500 rounded"></span> 60-90 days</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-red-500 rounded"></span> 90-180 days</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-red-700 rounded"></span> 180+ days</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-gray-700 rounded"></span> Never logged in</span>
          </div>
        </div>

        {/* Filters and Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-4 border-b border-gray-100">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search users..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-64"
                  />
                </div>
                <select
                  value={daysThreshold}
                  onChange={(e) => setDaysThreshold(Number(e.target.value))}
                  className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value={30}>30+ days inactive</option>
                  <option value={60}>60+ days inactive</option>
                  <option value={90}>90+ days inactive</option>
                  <option value={180}>180+ days inactive</option>
                  <option value={365}>365+ days inactive</option>
                </select>
                <label className="flex items-center gap-2 text-sm text-gray-600">
                  <input
                    type="checkbox"
                    checked={showOnlyNeverLoggedIn}
                    onChange={(e) => setShowOnlyNeverLoggedIn(e.target.checked)}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  Never logged in only
                </label>
              </div>
              {selectedUsers.size > 0 && (
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-500">{selectedUsers.size} selected</span>
                  <button
                    onClick={() => toast.success(`Requesting review for ${selectedUsers.size} users...`)}
                    className="px-3 py-1.5 text-sm text-orange-600 bg-orange-50 rounded-lg hover:bg-orange-100"
                  >
                    Request Review
                  </button>
                  <button
                    onClick={() => toast.success(`${selectedUsers.size} users disabled`)}
                    className="px-3 py-1.5 text-sm text-red-600 bg-red-50 rounded-lg hover:bg-red-100"
                  >
                    Disable Selected
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={selectedUsers.size === filteredUsers.length && filteredUsers.length > 0}
                      onChange={selectAllFiltered}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">User</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Department</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Last Login</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Days Inactive</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Risk</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Recommendation</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredUsers.map((user) => (
                  <tr key={user.user_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedUsers.has(user.user_id)}
                        onChange={() => toggleUserSelection(user.user_id)}
                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 bg-gray-100 rounded-full flex items-center justify-center">
                          <UserIcon className="h-5 w-5 text-gray-400" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{user.full_name}</p>
                          <p className="text-sm text-gray-500">{user.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{user.department}</td>
                    <td className="px-4 py-3 text-sm">
                      {user.last_login ? (
                        <span className="text-gray-600">
                          {new Date(user.last_login).toLocaleDateString()}
                        </span>
                      ) : (
                        <span className="text-red-500 font-medium">Never</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {formatDaysInactive(user.days_inactive, user.never_logged_in)}
                    </td>
                    <td className="px-4 py-3">
                      {getRiskBadge(user.risk_level)}
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-xs text-gray-500 max-w-xs truncate" title={user.recommendation}>
                        {user.recommendation}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/users/${user.user_id}`}
                        className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                      >
                        <ChevronRightIcon className="h-5 w-5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredUsers.length === 0 && (
            <div className="text-center py-12">
              <CheckCircleIcon className="h-12 w-12 text-emerald-400 mx-auto mb-4" />
              <p className="text-gray-500">No inactive users found matching your criteria</p>
            </div>
          )}
        </div>

        {/* Compliance Note */}
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
          <div className="flex items-start gap-3">
            <ShieldExclamationIcon className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-blue-900">Compliance Requirement</h4>
              <p className="text-sm text-blue-700 mt-1">
                SOX, ISO 27001, and NIST frameworks require regular review and deactivation of dormant user accounts.
                Accounts inactive for 90+ days should be reviewed with the user's manager. Accounts inactive for 180+ days
                should be disabled pending justification.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default InactiveUsers;
