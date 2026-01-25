import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  PlusIcon,
  BuildingOfficeIcon,
  ExclamationTriangleIcon,
  UserGroupIcon,
  CubeIcon,
} from '@heroicons/react/24/outline';

interface Role {
  id: string;
  name: string;
  description: string;
  system: string;
  type: 'business' | 'technical' | 'composite';
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  userCount: number;
  permissions: number;
  sodConflicts: number;
  lastModified: string;
  owner: string;
}

const mockRoles: Role[] = [
  {
    id: 'ROLE-001',
    name: 'SAP_MM_BUYER',
    description: 'Procurement buyer role with purchase order creation',
    system: 'SAP ECC',
    type: 'business',
    riskLevel: 'medium',
    userCount: 45,
    permissions: 28,
    sodConflicts: 2,
    lastModified: '2024-01-15',
    owner: 'Procurement Director',
  },
  {
    id: 'ROLE-002',
    name: 'SAP_FI_AP_CLERK',
    description: 'Accounts payable processing clerk',
    system: 'SAP ECC',
    type: 'business',
    riskLevel: 'low',
    userCount: 32,
    permissions: 15,
    sodConflicts: 0,
    lastModified: '2024-01-10',
    owner: 'Finance Director',
  },
  {
    id: 'ROLE-003',
    name: 'AWS_ADMIN_FULL',
    description: 'Full administrative access to AWS resources',
    system: 'AWS',
    type: 'technical',
    riskLevel: 'critical',
    userCount: 5,
    permissions: 150,
    sodConflicts: 8,
    lastModified: '2024-01-20',
    owner: 'Cloud Security',
  },
  {
    id: 'ROLE-004',
    name: 'HR_BENEFITS_ADMIN',
    description: 'HR benefits administration and management',
    system: 'Workday',
    type: 'business',
    riskLevel: 'high',
    userCount: 8,
    permissions: 42,
    sodConflicts: 3,
    lastModified: '2024-01-18',
    owner: 'HR Director',
  },
  {
    id: 'ROLE-005',
    name: 'SALES_MANAGER',
    description: 'Sales management with reporting access',
    system: 'Salesforce',
    type: 'composite',
    riskLevel: 'low',
    userCount: 25,
    permissions: 35,
    sodConflicts: 0,
    lastModified: '2024-01-12',
    owner: 'Sales Director',
  },
  {
    id: 'ROLE-006',
    name: 'SAP_FI_GL_ACCOUNTANT',
    description: 'General ledger accounting and posting',
    system: 'SAP ECC',
    type: 'business',
    riskLevel: 'high',
    userCount: 18,
    permissions: 45,
    sodConflicts: 5,
    lastModified: '2024-01-16',
    owner: 'Finance Director',
  },
  {
    id: 'ROLE-007',
    name: 'DB_READ_ONLY',
    description: 'Read-only access to production database',
    system: 'Oracle DB',
    type: 'technical',
    riskLevel: 'low',
    userCount: 120,
    permissions: 5,
    sodConflicts: 0,
    lastModified: '2024-01-08',
    owner: 'DBA Team',
  },
  {
    id: 'ROLE-008',
    name: 'AZURE_AD_ADMIN',
    description: 'Azure Active Directory administration',
    system: 'Azure AD',
    type: 'technical',
    riskLevel: 'critical',
    userCount: 3,
    permissions: 85,
    sodConflicts: 4,
    lastModified: '2024-01-19',
    owner: 'IT Security',
  },
];

const riskConfig = {
  low: { color: 'bg-green-100 text-green-800' },
  medium: { color: 'bg-yellow-100 text-yellow-800' },
  high: { color: 'bg-orange-100 text-orange-800' },
  critical: { color: 'bg-red-100 text-red-800' },
};

const typeConfig = {
  business: { color: 'bg-blue-100 text-blue-800', label: 'Business' },
  technical: { color: 'bg-purple-100 text-purple-800', label: 'Technical' },
  composite: { color: 'bg-indigo-100 text-indigo-800', label: 'Composite' },
};

export function RoleList() {
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [systemFilter, setSystemFilter] = useState<string>('all');

  const systems = [...new Set(mockRoles.map((r) => r.system))];

  const filteredRoles = mockRoles.filter((role) => {
    const matchesSearch =
      role.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      role.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = typeFilter === 'all' || role.type === typeFilter;
    const matchesRisk = riskFilter === 'all' || role.riskLevel === riskFilter;
    const matchesSystem = systemFilter === 'all' || role.system === systemFilter;
    return matchesSearch && matchesType && matchesRisk && matchesSystem;
  });

  const totalUsers = mockRoles.reduce((acc, r) => acc + r.userCount, 0);
  const highRiskRoles = mockRoles.filter((r) => r.riskLevel === 'high' || r.riskLevel === 'critical').length;
  const rolesWithConflicts = mockRoles.filter((r) => r.sodConflicts > 0).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Role Catalog</h1>
          <p className="mt-1 text-sm text-gray-500">
            Browse and manage roles across all connected systems
          </p>
        </div>
        <div className="flex space-x-3">
          <Link
            to="/roles/designer"
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            Create Role
          </Link>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <CubeIcon className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">Total Roles</div>
              <div className="text-2xl font-bold text-gray-900">{mockRoles.length}</div>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <UserGroupIcon className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">Total Assignments</div>
              <div className="text-2xl font-bold text-gray-900">{totalUsers}</div>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-orange-100 rounded-lg">
              <ExclamationTriangleIcon className="h-6 w-6 text-orange-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">High-Risk Roles</div>
              <div className="text-2xl font-bold text-orange-600">{highRiskRoles}</div>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-red-100 rounded-lg">
              <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">With SoD Conflicts</div>
              <div className="text-2xl font-bold text-red-600">{rolesWithConflicts}</div>
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
              placeholder="Search roles..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <FunnelIcon className="h-5 w-5 text-gray-400" />
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">All Types</option>
              <option value="business">Business</option>
              <option value="technical">Technical</option>
              <option value="composite">Composite</option>
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
              value={systemFilter}
              onChange={(e) => setSystemFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">All Systems</option>
              {systems.map((system) => (
                <option key={system} value={system}>
                  {system}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Roles Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Role
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                System
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Risk
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Users
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                SoD Conflicts
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredRoles.map((role) => {
              const riskInfo = riskConfig[role.riskLevel];
              const typeInfo = typeConfig[role.type];

              return (
                <tr key={role.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <div className="p-2 bg-gray-100 rounded-lg mr-3">
                        <BuildingOfficeIcon className="h-5 w-5 text-gray-600" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">{role.name}</div>
                        <div className="text-xs text-gray-500">{role.description}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex px-2 py-0.5 rounded bg-gray-100 text-xs text-gray-700">
                      {role.system}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${typeInfo.color}`}
                    >
                      {typeInfo.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${riskInfo.color}`}
                    >
                      {role.riskLevel.charAt(0).toUpperCase() + role.riskLevel.slice(1)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {role.userCount}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {role.sodConflicts > 0 ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
                        {role.sodConflicts}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-500">None</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <Link
                      to={`/roles/designer/${role.id}`}
                      className="text-primary-600 hover:text-primary-900 mr-3"
                    >
                      Edit
                    </Link>
                    <button className="text-gray-600 hover:text-gray-900">
                      Clone
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredRoles.length === 0 && (
          <div className="text-center py-12">
            <CubeIcon className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-gray-500">No roles found matching your criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}
