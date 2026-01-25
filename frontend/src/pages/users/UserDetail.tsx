import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeftIcon,
  UserIcon,
  EnvelopeIcon,
  BuildingOfficeIcon,
  CalendarIcon,
  ShieldExclamationIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  KeyIcon,
} from '@heroicons/react/24/outline';

interface UserRole {
  id: string;
  name: string;
  system: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  grantedDate: string;
  grantedBy: string;
  lastUsed: string;
  status: 'active' | 'pending_review';
}

interface UserActivity {
  id: string;
  action: string;
  timestamp: string;
  system: string;
  details: string;
  risk: 'normal' | 'elevated' | 'high';
}

const mockUser = {
  id: 'USR-001',
  name: 'John Smith',
  email: 'john.smith@company.com',
  department: 'Finance',
  title: 'Senior Financial Analyst',
  manager: 'Sarah Director',
  status: 'active',
  lastLogin: '2024-01-20 09:15',
  createdDate: '2022-03-15',
  riskScore: 65,
  violations: 2,
  pendingRequests: 1,
};

const mockRoles: UserRole[] = [
  {
    id: 'ROLE-001',
    name: 'SAP_FI_AP_CLERK',
    system: 'SAP ECC',
    riskLevel: 'low',
    grantedDate: '2022-06-15',
    grantedBy: 'Sarah Director',
    lastUsed: '2024-01-19',
    status: 'active',
  },
  {
    id: 'ROLE-002',
    name: 'SAP_FI_GL_ACCOUNTANT',
    system: 'SAP ECC',
    riskLevel: 'high',
    grantedDate: '2023-01-10',
    grantedBy: 'Risk Committee',
    lastUsed: '2024-01-20',
    status: 'active',
  },
  {
    id: 'ROLE-003',
    name: 'WORKDAY_VIEWER',
    system: 'Workday',
    riskLevel: 'low',
    grantedDate: '2022-03-15',
    grantedBy: 'HR Admin',
    lastUsed: '2024-01-18',
    status: 'active',
  },
  {
    id: 'ROLE-004',
    name: 'AWS_READ_ONLY',
    system: 'AWS',
    riskLevel: 'medium',
    grantedDate: '2023-08-20',
    grantedBy: 'IT Manager',
    lastUsed: '2023-11-05',
    status: 'pending_review',
  },
];

const mockActivities: UserActivity[] = [
  {
    id: 'ACT-001',
    action: 'GL Posting',
    timestamp: '2024-01-20 14:32',
    system: 'SAP ECC',
    details: 'Posted journal entry JE-2024-0456',
    risk: 'normal',
  },
  {
    id: 'ACT-002',
    action: 'Vendor Payment',
    timestamp: '2024-01-20 11:15',
    system: 'SAP ECC',
    details: 'Executed payment run for vendor batch',
    risk: 'elevated',
  },
  {
    id: 'ACT-003',
    action: 'Report Access',
    timestamp: '2024-01-19 16:45',
    system: 'SAP ECC',
    details: 'Accessed financial report FI-001',
    risk: 'normal',
  },
  {
    id: 'ACT-004',
    action: 'Mass Update',
    timestamp: '2024-01-19 10:20',
    system: 'SAP ECC',
    details: 'Updated 150 vendor records',
    risk: 'high',
  },
  {
    id: 'ACT-005',
    action: 'Login',
    timestamp: '2024-01-20 09:15',
    system: 'SSO',
    details: 'Successful authentication',
    risk: 'normal',
  },
];

const mockViolations = [
  {
    id: 'VIO-001',
    rule: 'Create Vendor / Execute Payment',
    severity: 'critical',
    detectedDate: '2024-01-15',
    status: 'open',
  },
  {
    id: 'VIO-002',
    rule: 'Post GL / Approve GL',
    severity: 'high',
    detectedDate: '2024-01-10',
    status: 'mitigated',
  },
];

const riskConfig = {
  low: { color: 'bg-green-100 text-green-800' },
  medium: { color: 'bg-yellow-100 text-yellow-800' },
  high: { color: 'bg-orange-100 text-orange-800' },
  critical: { color: 'bg-red-100 text-red-800' },
};

const activityRiskConfig = {
  normal: { color: 'text-gray-500' },
  elevated: { color: 'text-yellow-600' },
  high: { color: 'text-red-600' },
};

export function UserDetail() {
  useParams(); // Used for user ID extraction
  const [activeTab, setActiveTab] = useState<'roles' | 'activity' | 'violations'>('roles');

  const user = mockUser;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Link
            to="/users"
            className="mr-4 p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <div className="flex items-center">
            <div className="h-16 w-16 bg-primary-100 rounded-full flex items-center justify-center mr-4">
              <UserIcon className="h-8 w-8 text-primary-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{user.name}</h1>
              <p className="text-sm text-gray-500">
                {user.title} • {user.department}
              </p>
            </div>
          </div>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
            Edit User
          </button>
          <button className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm font-medium">
            Revoke All Access
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User Info Card */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">User Information</h2>
          <div className="space-y-4">
            <div className="flex items-center">
              <EnvelopeIcon className="h-5 w-5 text-gray-400 mr-3" />
              <div>
                <div className="text-xs text-gray-500">Email</div>
                <div className="text-sm text-gray-900">{user.email}</div>
              </div>
            </div>
            <div className="flex items-center">
              <BuildingOfficeIcon className="h-5 w-5 text-gray-400 mr-3" />
              <div>
                <div className="text-xs text-gray-500">Department</div>
                <div className="text-sm text-gray-900">{user.department}</div>
              </div>
            </div>
            <div className="flex items-center">
              <UserIcon className="h-5 w-5 text-gray-400 mr-3" />
              <div>
                <div className="text-xs text-gray-500">Manager</div>
                <div className="text-sm text-gray-900">{user.manager}</div>
              </div>
            </div>
            <div className="flex items-center">
              <CalendarIcon className="h-5 w-5 text-gray-400 mr-3" />
              <div>
                <div className="text-xs text-gray-500">Account Created</div>
                <div className="text-sm text-gray-900">{user.createdDate}</div>
              </div>
            </div>
            <div className="flex items-center">
              <ClockIcon className="h-5 w-5 text-gray-400 mr-3" />
              <div>
                <div className="text-xs text-gray-500">Last Login</div>
                <div className="text-sm text-gray-900">{user.lastLogin}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Risk Score */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk Profile</h2>
          <div className="flex items-center justify-center mb-4">
            <div className="relative w-28 h-28">
              <svg className="w-full h-full" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" strokeWidth="10" />
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  fill="none"
                  stroke={user.riskScore > 70 ? '#ef4444' : user.riskScore > 40 ? '#f59e0b' : '#22c55e'}
                  strokeWidth="10"
                  strokeDasharray={`${user.riskScore * 2.83} ${100 * 2.83}`}
                  strokeLinecap="round"
                  transform="rotate(-90 50 50)"
                />
                <text x="50" y="50" textAnchor="middle" dy="0.3em" className="text-2xl font-bold" fill="#111827">
                  {user.riskScore}
                </text>
              </svg>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Active Violations</span>
              <span className="font-medium text-red-600">{user.violations}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Pending Requests</span>
              <span className="font-medium text-yellow-600">{user.pendingRequests}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Roles Assigned</span>
              <span className="font-medium text-gray-900">{mockRoles.length}</span>
            </div>
          </div>
        </div>

        {/* Active Violations */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Active Violations</h2>
          {mockViolations.length > 0 ? (
            <div className="space-y-3">
              {mockViolations.map((violation) => (
                <div
                  key={violation.id}
                  className={`p-3 rounded-lg border ${
                    violation.severity === 'critical'
                      ? 'bg-red-50 border-red-200'
                      : 'bg-orange-50 border-orange-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <ShieldExclamationIcon
                        className={`h-5 w-5 ${
                          violation.severity === 'critical' ? 'text-red-600' : 'text-orange-600'
                        }`}
                      />
                      <span className="ml-2 text-sm font-medium text-gray-900">
                        {violation.rule}
                      </span>
                    </div>
                    <span
                      className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                        violation.status === 'open'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {violation.status}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">Detected: {violation.detectedDate}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-4">
              <CheckCircleIcon className="mx-auto h-8 w-8 text-green-500" />
              <p className="mt-2 text-sm text-gray-500">No active violations</p>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('roles')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'roles'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <KeyIcon className="h-5 w-5 inline mr-2" />
              Assigned Roles ({mockRoles.length})
            </button>
            <button
              onClick={() => setActiveTab('activity')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'activity'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <ClockIcon className="h-5 w-5 inline mr-2" />
              Activity Log
            </button>
            <button
              onClick={() => setActiveTab('violations')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'violations'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <ExclamationTriangleIcon className="h-5 w-5 inline mr-2" />
              Violations ({mockViolations.length})
            </button>
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'roles' && (
            <div className="space-y-3">
              {mockRoles.map((role) => {
                const riskInfo = riskConfig[role.riskLevel];
                return (
                  <div
                    key={role.id}
                    className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center">
                      <div className="p-2 bg-white rounded-lg mr-4">
                        <KeyIcon className="h-5 w-5 text-gray-600" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">{role.name}</div>
                        <div className="text-xs text-gray-500">
                          {role.system} • Granted: {role.grantedDate} by {role.grantedBy}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-xs text-gray-500">
                        Last used: {role.lastUsed}
                      </div>
                      <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${riskInfo.color}`}>
                        {role.riskLevel.charAt(0).toUpperCase() + role.riskLevel.slice(1)}
                      </span>
                      {role.status === 'pending_review' && (
                        <span className="inline-flex px-2 py-0.5 rounded bg-yellow-100 text-yellow-800 text-xs">
                          Pending Review
                        </span>
                      )}
                      <button className="text-red-600 hover:text-red-900 text-sm">
                        Revoke
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {activeTab === 'activity' && (
            <div className="space-y-3">
              {mockActivities.map((activity) => {
                const riskInfo = activityRiskConfig[activity.risk];
                return (
                  <div key={activity.id} className="flex items-start p-4 bg-gray-50 rounded-lg">
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-900">{activity.action}</span>
                        <span className="text-xs text-gray-500">{activity.timestamp}</span>
                      </div>
                      <p className="mt-1 text-sm text-gray-600">{activity.details}</p>
                      <div className="mt-2 flex items-center gap-3">
                        <span className="inline-flex px-2 py-0.5 rounded bg-gray-200 text-xs text-gray-700">
                          {activity.system}
                        </span>
                        {activity.risk !== 'normal' && (
                          <span className={`text-xs font-medium ${riskInfo.color}`}>
                            {activity.risk.toUpperCase()} RISK
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {activeTab === 'violations' && (
            <div className="space-y-3">
              {mockViolations.map((violation) => (
                <div
                  key={violation.id}
                  className={`p-4 rounded-lg border ${
                    violation.severity === 'critical'
                      ? 'bg-red-50 border-red-200'
                      : 'bg-orange-50 border-orange-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <ShieldExclamationIcon
                        className={`h-6 w-6 ${
                          violation.severity === 'critical' ? 'text-red-600' : 'text-orange-600'
                        }`}
                      />
                      <div className="ml-3">
                        <div className="text-sm font-medium text-gray-900">{violation.rule}</div>
                        <div className="text-xs text-gray-500">
                          {violation.id} • Detected: {violation.detectedDate}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span
                        className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          violation.severity === 'critical'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-orange-100 text-orange-800'
                        }`}
                      >
                        {violation.severity.charAt(0).toUpperCase() + violation.severity.slice(1)}
                      </span>
                      <span
                        className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          violation.status === 'open'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {violation.status.charAt(0).toUpperCase() + violation.status.slice(1)}
                      </span>
                      <button className="text-primary-600 hover:text-primary-900 text-sm">
                        View Details
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
