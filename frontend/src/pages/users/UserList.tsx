import { useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  UserPlusIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline';

interface User {
  id: string;
  name: string;
  email: string;
  department: string;
  title: string;
  manager: string;
  status: 'active' | 'inactive' | 'suspended';
  riskScore: number;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  totalRoles: number;
  activeViolations: number;
  lastLogin: string;
}

const mockUsers: User[] = [
  {
    id: 'USR-001',
    name: 'John Smith',
    email: 'jsmith@company.com',
    department: 'Finance',
    title: 'Senior Accountant',
    manager: 'Sarah Director',
    status: 'active',
    riskScore: 72,
    riskLevel: 'high',
    totalRoles: 8,
    activeViolations: 2,
    lastLogin: '2024-01-20',
  },
  {
    id: 'USR-002',
    name: 'Mary Brown',
    email: 'mbrown@company.com',
    department: 'IT',
    title: 'System Administrator',
    manager: 'IT Manager',
    status: 'active',
    riskScore: 65,
    riskLevel: 'high',
    totalRoles: 12,
    activeViolations: 1,
    lastLogin: '2024-01-20',
  },
  {
    id: 'USR-003',
    name: 'Tom Davis',
    email: 'tdavis@company.com',
    department: 'Procurement',
    title: 'Purchasing Manager',
    manager: 'Procurement Director',
    status: 'active',
    riskScore: 45,
    riskLevel: 'medium',
    totalRoles: 5,
    activeViolations: 0,
    lastLogin: '2024-01-19',
  },
  {
    id: 'USR-004',
    name: 'Alice Wilson',
    email: 'awilson@company.com',
    department: 'HR',
    title: 'HR Specialist',
    manager: 'HR Director',
    status: 'active',
    riskScore: 38,
    riskLevel: 'medium',
    totalRoles: 4,
    activeViolations: 1,
    lastLogin: '2024-01-20',
  },
  {
    id: 'USR-005',
    name: 'Bob Johnson',
    email: 'bjohnson@company.com',
    department: 'Finance',
    title: 'Financial Analyst',
    manager: 'Sarah Director',
    status: 'active',
    riskScore: 85,
    riskLevel: 'critical',
    totalRoles: 10,
    activeViolations: 3,
    lastLogin: '2024-01-18',
  },
  {
    id: 'USR-006',
    name: 'Carol White',
    email: 'cwhite@company.com',
    department: 'Sales',
    title: 'Sales Representative',
    manager: 'Sales Manager',
    status: 'inactive',
    riskScore: 15,
    riskLevel: 'low',
    totalRoles: 2,
    activeViolations: 0,
    lastLogin: '2023-10-15',
  },
  {
    id: 'USR-007',
    name: 'David Lee',
    email: 'dlee@company.com',
    department: 'Engineering',
    title: 'DevOps Engineer',
    manager: 'Engineering Manager',
    status: 'active',
    riskScore: 58,
    riskLevel: 'high',
    totalRoles: 15,
    activeViolations: 1,
    lastLogin: '2024-01-20',
  },
  {
    id: 'USR-008',
    name: 'Emma Garcia',
    email: 'egarcia@company.com',
    department: 'Finance',
    title: 'AP Clerk',
    manager: 'Sarah Director',
    status: 'suspended',
    riskScore: 25,
    riskLevel: 'low',
    totalRoles: 3,
    activeViolations: 0,
    lastLogin: '2024-01-10',
  },
];

const riskLevelConfig = {
  low: { color: 'bg-green-100 text-green-800', barColor: 'bg-green-500' },
  medium: { color: 'bg-yellow-100 text-yellow-800', barColor: 'bg-yellow-500' },
  high: { color: 'bg-orange-100 text-orange-800', barColor: 'bg-orange-500' },
  critical: { color: 'bg-red-100 text-red-800', barColor: 'bg-red-500' },
};

const statusConfig = {
  active: { color: 'bg-green-100 text-green-800', label: 'Active' },
  inactive: { color: 'bg-gray-100 text-gray-800', label: 'Inactive' },
  suspended: { color: 'bg-red-100 text-red-800', label: 'Suspended' },
};

export function UserList() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [departmentFilter, setDepartmentFilter] = useState<string>('all');

  const departments = [...new Set(mockUsers.map((u) => u.department))];

  const filteredUsers = mockUsers.filter((user) => {
    const matchesSearch =
      user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || user.status === statusFilter;
    const matchesRisk = riskFilter === 'all' || user.riskLevel === riskFilter;
    const matchesDept = departmentFilter === 'all' || user.department === departmentFilter;
    return matchesSearch && matchesStatus && matchesRisk && matchesDept;
  });

  const highRiskCount = mockUsers.filter(
    (u) => u.riskLevel === 'high' || u.riskLevel === 'critical'
  ).length;
  const violationsCount = mockUsers.reduce((acc, u) => acc + u.activeViolations, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Users</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage users and monitor their access risk profiles
          </p>
        </div>
        <button
          onClick={() => toast.success('Opening user creation form...')}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
        >
          <UserPlusIcon className="h-5 w-5 mr-2" />
          Add User
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <UserCircleIcon className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">Total Users</div>
              <div className="text-2xl font-bold text-gray-900">{mockUsers.length}</div>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <ShieldCheckIcon className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">Active</div>
              <div className="text-2xl font-bold text-gray-900">
                {mockUsers.filter((u) => u.status === 'active').length}
              </div>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-orange-100 rounded-lg">
              <ExclamationTriangleIcon className="h-6 w-6 text-orange-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">High Risk</div>
              <div className="text-2xl font-bold text-orange-600">{highRiskCount}</div>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-red-100 rounded-lg">
              <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">Violations</div>
              <div className="text-2xl font-bold text-red-600">{violationsCount}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white shadow rounded-lg p-4">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name, email, or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <FunnelIcon className="h-5 w-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="suspended">Suspended</option>
            </select>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">All Risk Levels</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">All Departments</option>
              {departments.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Department
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Risk Score
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Roles
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Violations
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredUsers.map((user) => {
              const riskInfo = riskLevelConfig[user.riskLevel];
              const statusInfo = statusConfig[user.status];

              return (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <div className="h-10 w-10 flex-shrink-0">
                        <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                          <span className="text-sm font-medium text-gray-600">
                            {user.name
                              .split(' ')
                              .map((n) => n[0])
                              .join('')}
                          </span>
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">{user.name}</div>
                        <div className="text-sm text-gray-500">{user.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">{user.department}</div>
                    <div className="text-sm text-gray-500">{user.title}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${statusInfo.color}`}
                    >
                      {statusInfo.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                        <div
                          className={`h-2 rounded-full ${riskInfo.barColor}`}
                          style={{ width: `${user.riskScore}%` }}
                        />
                      </div>
                      <span
                        className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${riskInfo.color}`}
                      >
                        {user.riskScore}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {user.totalRoles}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {user.activeViolations > 0 ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        {user.activeViolations}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-500">None</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <Link
                      to={`/users/${user.id}`}
                      className="text-primary-600 hover:text-primary-900"
                    >
                      View Profile
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredUsers.length === 0 && (
          <div className="text-center py-12">
            <UserCircleIcon className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-gray-500">No users found matching your criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}
