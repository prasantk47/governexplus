import { useState } from 'react';
import toast from 'react-hot-toast';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ShieldExclamationIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

interface SodRule {
  id: string;
  name: string;
  description: string;
  category: string;
  riskLevel: 'high' | 'critical';
  function1: string;
  function2: string;
  system: string;
  status: 'active' | 'inactive' | 'draft';
  violations: number;
  lastModified: string;
  owner: string;
}

const mockRules: SodRule[] = [
  {
    id: 'SOD-001',
    name: 'Create Vendor / Execute Payment',
    description: 'Prevents users from both creating vendors and executing payments to those vendors',
    category: 'Procure to Pay',
    riskLevel: 'critical',
    function1: 'FK01 - Create Vendor',
    function2: 'F110 - Payment Run',
    system: 'SAP ECC',
    status: 'active',
    violations: 12,
    lastModified: '2024-01-10',
    owner: 'Finance Control',
  },
  {
    id: 'SOD-002',
    name: 'Create PO / Release PO',
    description: 'Separates purchase order creation from release approval',
    category: 'Procurement',
    riskLevel: 'high',
    function1: 'ME21N - Create PO',
    function2: 'ME29N - Release PO',
    system: 'SAP ECC',
    status: 'active',
    violations: 8,
    lastModified: '2024-01-08',
    owner: 'Procurement',
  },
  {
    id: 'SOD-003',
    name: 'Post GL / Approve GL',
    description: 'Prevents same user from posting and approving general ledger entries',
    category: 'Financial Accounting',
    riskLevel: 'critical',
    function1: 'FB01 - Post Document',
    function2: 'FB02 - Change/Approve Document',
    system: 'SAP ECC',
    status: 'active',
    violations: 5,
    lastModified: '2024-01-15',
    owner: 'Finance Control',
  },
  {
    id: 'SOD-004',
    name: 'Create User / Assign Roles',
    description: 'Separates user creation from role assignment in IAM',
    category: 'Identity Management',
    riskLevel: 'critical',
    function1: 'Create User Account',
    function2: 'Assign IAM Roles',
    system: 'Azure AD',
    status: 'active',
    violations: 2,
    lastModified: '2024-01-12',
    owner: 'IT Security',
  },
  {
    id: 'SOD-005',
    name: 'HR Data Change / Payroll Execution',
    description: 'Prevents HR staff from both changing employee data and processing payroll',
    category: 'HR Management',
    riskLevel: 'high',
    function1: 'Update Employee Master',
    function2: 'Execute Payroll',
    system: 'Workday',
    status: 'active',
    violations: 0,
    lastModified: '2024-01-05',
    owner: 'HR Control',
  },
  {
    id: 'SOD-006',
    name: 'Deploy Code / Approve Deployment',
    description: 'Separates code deployment from deployment approval in CI/CD',
    category: 'IT Operations',
    riskLevel: 'high',
    function1: 'Deploy to Production',
    function2: 'Approve Deployment',
    system: 'AWS',
    status: 'active',
    violations: 3,
    lastModified: '2024-01-14',
    owner: 'DevOps',
  },
  {
    id: 'SOD-007',
    name: 'Create Invoice / Process Payment',
    description: 'Prevents same user from creating and paying invoices',
    category: 'Accounts Payable',
    riskLevel: 'critical',
    function1: 'MIRO - Enter Invoice',
    function2: 'F110 - Payment Run',
    system: 'SAP ECC',
    status: 'inactive',
    violations: 0,
    lastModified: '2024-01-02',
    owner: 'Finance Control',
  },
  {
    id: 'SOD-008',
    name: 'Goods Receipt / Invoice Verification',
    description: 'Three-way match control for goods receipt and invoice',
    category: 'Procure to Pay',
    riskLevel: 'high',
    function1: 'MIGO - Goods Receipt',
    function2: 'MIRO - Invoice Verification',
    system: 'SAP ECC',
    status: 'draft',
    violations: 0,
    lastModified: '2024-01-18',
    owner: 'Procurement',
  },
];

const riskConfig = {
  high: { color: 'bg-orange-100 text-orange-800', label: 'High Risk' },
  critical: { color: 'bg-red-100 text-red-800', label: 'Critical Risk' },
};

const statusConfig = {
  active: { color: 'bg-green-100 text-green-800', label: 'Active' },
  inactive: { color: 'bg-gray-100 text-gray-800', label: 'Inactive' },
  draft: { color: 'bg-yellow-100 text-yellow-800', label: 'Draft' },
};

export function RiskRules() {
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [systemFilter, setSystemFilter] = useState<string>('all');

  const categories = [...new Set(mockRules.map((r) => r.category))];
  const systems = [...new Set(mockRules.map((r) => r.system))];

  const filteredRules = mockRules.filter((rule) => {
    const matchesSearch =
      rule.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      rule.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || rule.category === categoryFilter;
    const matchesStatus = statusFilter === 'all' || rule.status === statusFilter;
    const matchesSystem = systemFilter === 'all' || rule.system === systemFilter;
    return matchesSearch && matchesCategory && matchesStatus && matchesSystem;
  });

  const activeRules = mockRules.filter((r) => r.status === 'active').length;
  const totalViolations = mockRules.reduce((acc, r) => acc + r.violations, 0);
  const criticalRules = mockRules.filter((r) => r.riskLevel === 'critical').length;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Segregation of Duties Rules</h1>
          <p className="page-subtitle">
            Manage SoD rules and conflict detection policies
          </p>
        </div>
        <button
          onClick={() => toast.success('Rule creation wizard will open here')}
          className="btn-primary"
        >
          <PlusIcon className="h-4 w-4 mr-1.5" />
          Create Rule
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-blue">
              <ShieldExclamationIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Total Rules</div>
              <div className="stat-value">{mockRules.length}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-green">
              <CheckCircleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Active Rules</div>
              <div className="stat-value text-green-500">{activeRules}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-red">
              <ExclamationTriangleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Total Violations</div>
              <div className="stat-value text-red-500">{totalViolations}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-orange">
              <ShieldExclamationIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Critical Rules</div>
              <div className="stat-value text-orange-500">{criticalRules}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="card-body">
          <div className="flex flex-col lg:flex-row gap-3">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search rules..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <FunnelIcon className="h-4 w-4 text-gray-400" />
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="text-xs border border-gray-300 rounded-md px-2 py-1.5 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="all">All Categories</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-xs border border-gray-300 rounded-md px-2 py-1.5 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="draft">Draft</option>
              </select>
              <select
                value={systemFilter}
                onChange={(e) => setSystemFilter(e.target.value)}
                className="text-xs border border-gray-300 rounded-md px-2 py-1.5 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="all">All Systems</option>
                {systems.map((sys) => (
                  <option key={sys} value={sys}>
                    {sys}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Rules Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rule
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Functions
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                System
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Risk
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
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
            {filteredRules.map((rule) => {
              const riskInfo = riskConfig[rule.riskLevel];
              const statusInfo = statusConfig[rule.status];
              return (
                <tr key={rule.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{rule.name}</div>
                      <div className="text-xs text-gray-500">{rule.category}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-xs">
                      <div className="text-gray-900">{rule.function1}</div>
                      <div className="text-gray-400 my-1">conflicts with</div>
                      <div className="text-gray-900">{rule.function2}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex px-2 py-0.5 rounded bg-gray-100 text-xs text-gray-700">
                      {rule.system}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${riskInfo.color}`}
                    >
                      {riskInfo.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${statusInfo.color}`}
                    >
                      {statusInfo.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {rule.violations > 0 ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
                        {rule.violations}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-500">0</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button
                      onClick={() => toast.success(`Editing rule ${rule.id}...`)}
                      className="text-primary-600 hover:text-primary-900 mr-3"
                    >
                      <PencilIcon className="h-4 w-4 inline" />
                    </button>
                    <button
                      onClick={() => toast.success(`Rule ${rule.id} deleted`)}
                      className="text-red-600 hover:text-red-900"
                    >
                      <TrashIcon className="h-4 w-4 inline" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredRules.length === 0 && (
          <div className="text-center py-12">
            <ShieldExclamationIcon className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-gray-500">No rules found matching your criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}
