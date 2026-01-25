import { useState } from 'react';
import {
  ShieldExclamationIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  PencilIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  PlayIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';

interface SodRule {
  id: string;
  name: string;
  description: string;
  category: string;
  businessProcess: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  function1: { name: string; transactions: string[] };
  function2: { name: string; transactions: string[] };
  status: 'active' | 'inactive' | 'draft';
  violationCount: number;
  lastRun: string;
  createdBy: string;
  isCustom: boolean;
}

const SOD_CATEGORIES = [
  'Procure-to-Pay (P2P)',
  'Order-to-Cash (O2C)',
  'Hire-to-Retire (H2R)',
  'Record-to-Report (R2R)',
  'IT Administration',
  'Master Data',
];

const mockSodRules: SodRule[] = [
  {
    id: 'SOD-001',
    name: 'AP Processing & Payment Execution',
    description: 'Prevents user from both processing invoices and executing payments',
    category: 'Procure-to-Pay (P2P)',
    businessProcess: 'Accounts Payable',
    severity: 'critical',
    function1: { name: 'Invoice Processing', transactions: ['FB60', 'MIRO', 'FV60'] },
    function2: { name: 'Payment Execution', transactions: ['F110', 'F-53', 'F-58'] },
    status: 'active',
    violationCount: 12,
    lastRun: '2024-01-18 08:00',
    createdBy: 'System',
    isCustom: false,
  },
  {
    id: 'SOD-002',
    name: 'Vendor Master & Payment',
    description: 'Prevents user from maintaining vendors and executing payments to them',
    category: 'Procure-to-Pay (P2P)',
    businessProcess: 'Vendor Management',
    severity: 'critical',
    function1: { name: 'Vendor Maintenance', transactions: ['XK01', 'XK02', 'FK01', 'FK02'] },
    function2: { name: 'Payment Execution', transactions: ['F110', 'F-53', 'F-58'] },
    status: 'active',
    violationCount: 8,
    lastRun: '2024-01-18 08:00',
    createdBy: 'System',
    isCustom: false,
  },
  {
    id: 'SOD-003',
    name: 'Purchase Requisition & Approval',
    description: 'Prevents user from creating and approving their own purchase requisitions',
    category: 'Procure-to-Pay (P2P)',
    businessProcess: 'Procurement',
    severity: 'high',
    function1: { name: 'PR Creation', transactions: ['ME51N', 'ME52N'] },
    function2: { name: 'PR Approval', transactions: ['ME54N', 'ME55'] },
    status: 'active',
    violationCount: 23,
    lastRun: '2024-01-18 08:00',
    createdBy: 'System',
    isCustom: false,
  },
  {
    id: 'SOD-004',
    name: 'Sales Order & Billing',
    description: 'Prevents user from creating sales orders and processing billing',
    category: 'Order-to-Cash (O2C)',
    businessProcess: 'Sales',
    severity: 'high',
    function1: { name: 'Sales Order Processing', transactions: ['VA01', 'VA02'] },
    function2: { name: 'Billing', transactions: ['VF01', 'VF02', 'VF04'] },
    status: 'active',
    violationCount: 5,
    lastRun: '2024-01-18 08:00',
    createdBy: 'System',
    isCustom: false,
  },
  {
    id: 'SOD-005',
    name: 'Customer Master & Credit Management',
    description: 'Prevents user from maintaining customer data and managing credit limits',
    category: 'Order-to-Cash (O2C)',
    businessProcess: 'Customer Management',
    severity: 'medium',
    function1: { name: 'Customer Maintenance', transactions: ['XD01', 'XD02', 'FD01', 'FD02'] },
    function2: { name: 'Credit Management', transactions: ['FD32', 'UKM_BP'] },
    status: 'active',
    violationCount: 3,
    lastRun: '2024-01-18 08:00',
    createdBy: 'System',
    isCustom: false,
  },
  {
    id: 'SOD-006',
    name: 'HR Master Data & Payroll',
    description: 'Prevents user from maintaining employee data and processing payroll',
    category: 'Hire-to-Retire (H2R)',
    businessProcess: 'Human Resources',
    severity: 'critical',
    function1: { name: 'HR Master Data', transactions: ['PA30', 'PA40'] },
    function2: { name: 'Payroll Processing', transactions: ['PC00_M99_CALC', 'PC00_M99_CIPE'] },
    status: 'active',
    violationCount: 2,
    lastRun: '2024-01-18 08:00',
    createdBy: 'System',
    isCustom: false,
  },
  {
    id: 'SOD-007',
    name: 'GL Posting & Period Close',
    description: 'Prevents user from posting to GL and closing periods',
    category: 'Record-to-Report (R2R)',
    businessProcess: 'Financial Reporting',
    severity: 'high',
    function1: { name: 'GL Posting', transactions: ['FB01', 'FB50', 'F-02'] },
    function2: { name: 'Period Close', transactions: ['MMPV', 'OB52', 'S_ALR_87003642'] },
    status: 'active',
    violationCount: 4,
    lastRun: '2024-01-18 08:00',
    createdBy: 'System',
    isCustom: false,
  },
  {
    id: 'SOD-008',
    name: 'User Admin & Role Admin',
    description: 'Prevents user from having both user and role administration access',
    category: 'IT Administration',
    businessProcess: 'Security',
    severity: 'critical',
    function1: { name: 'User Administration', transactions: ['SU01', 'SU10'] },
    function2: { name: 'Role Administration', transactions: ['PFCG', 'SU24'] },
    status: 'active',
    violationCount: 1,
    lastRun: '2024-01-18 08:00',
    createdBy: 'System',
    isCustom: false,
  },
  {
    id: 'SOD-009',
    name: 'Material Master & Inventory Posting',
    description: 'Prevents user from maintaining material data and posting inventory movements',
    category: 'Master Data',
    businessProcess: 'Materials Management',
    severity: 'medium',
    function1: { name: 'Material Maintenance', transactions: ['MM01', 'MM02'] },
    function2: { name: 'Inventory Posting', transactions: ['MIGO', 'MB1A', 'MB1B', 'MB1C'] },
    status: 'active',
    violationCount: 15,
    lastRun: '2024-01-18 08:00',
    createdBy: 'System',
    isCustom: false,
  },
  {
    id: 'SOD-010',
    name: 'Custom: AP Clerk Access Restriction',
    description: 'Custom rule for AP clerks - no access to vendor banking data',
    category: 'Procure-to-Pay (P2P)',
    businessProcess: 'Accounts Payable',
    severity: 'high',
    function1: { name: 'AP Processing', transactions: ['FB60', 'MIRO'] },
    function2: { name: 'Vendor Bank Data', transactions: ['FK02 (Bank Tab)', 'XK02 (Bank Tab)'] },
    status: 'draft',
    violationCount: 0,
    lastRun: '-',
    createdBy: 'Security Admin',
    isCustom: true,
  },
];

export function SodRuleLibrary() {
  const [rules, setRules] = useState<SodRule[]>(mockSodRules);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedRule, setSelectedRule] = useState<SodRule | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const filteredRules = rules.filter(
    (rule) =>
      (rule.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        rule.description.toLowerCase().includes(searchTerm.toLowerCase())) &&
      (categoryFilter === '' || rule.category === categoryFilter) &&
      (severityFilter === '' || rule.severity === severityFilter) &&
      (statusFilter === '' || rule.status === statusFilter)
  );

  const stats = {
    total: rules.length,
    active: rules.filter((r) => r.status === 'active').length,
    critical: rules.filter((r) => r.severity === 'critical').length,
    violations: rules.reduce((acc, r) => acc + r.violationCount, 0),
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-green-100 text-green-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'inactive': return 'bg-gray-100 text-gray-800';
      default: return 'bg-blue-100 text-blue-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SoD Rule Library</h1>
          <p className="text-sm text-gray-500">
            Manage segregation of duties rules for risk detection
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm font-medium flex items-center gap-2"
        >
          <PlusIcon className="h-4 w-4" />
          Create Rule
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
          <div className="text-sm text-gray-500">Total Rules</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-green-600">{stats.active}</div>
          <div className="text-sm text-gray-500">Active Rules</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-red-600">{stats.critical}</div>
          <div className="text-sm text-gray-500">Critical Rules</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-orange-600">{stats.violations}</div>
          <div className="text-sm text-gray-500">Active Violations</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search rules..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All Categories</option>
            {SOD_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="draft">Draft</option>
          </select>
        </div>
      </div>

      {/* Rules Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rule</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Violations</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Run</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredRules.map((rule) => (
              <tr key={rule.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <ShieldExclamationIcon className={`h-5 w-5 ${
                      rule.severity === 'critical' ? 'text-red-500' :
                      rule.severity === 'high' ? 'text-orange-500' :
                      rule.severity === 'medium' ? 'text-yellow-500' :
                      'text-green-500'
                    }`} />
                    <div>
                      <div className="text-sm font-medium text-gray-900 flex items-center gap-2">
                        {rule.name}
                        {rule.isCustom && (
                          <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">Custom</span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500">{rule.id}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900">{rule.category}</div>
                  <div className="text-xs text-gray-500">{rule.businessProcess}</div>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getSeverityColor(rule.severity)}`}>
                    {rule.severity}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(rule.status)}`}>
                    {rule.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`text-sm font-medium ${rule.violationCount > 0 ? 'text-red-600' : 'text-gray-500'}`}>
                    {rule.violationCount}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  <div className="flex items-center gap-1">
                    <ClockIcon className="h-4 w-4" />
                    {rule.lastRun}
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => setSelectedRule(rule)}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="View Details"
                    >
                      <MagnifyingGlassIcon className="h-4 w-4" />
                    </button>
                    <button className="p-1 text-gray-400 hover:text-gray-600" title="Run Now">
                      <PlayIcon className="h-4 w-4" />
                    </button>
                    {rule.isCustom && (
                      <>
                        <button className="p-1 text-gray-400 hover:text-blue-600" title="Edit">
                          <PencilIcon className="h-4 w-4" />
                        </button>
                        <button className="p-1 text-gray-400 hover:text-red-600" title="Delete">
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </>
                    )}
                    <button className="p-1 text-gray-400 hover:text-gray-600" title="Duplicate">
                      <DocumentDuplicateIcon className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Rule Detail Modal */}
      {selectedRule && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">{selectedRule.name}</h2>
                <button
                  onClick={() => setSelectedRule(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <XCircleIcon className="h-6 w-6" />
                </button>
              </div>
              <p className="text-sm text-gray-500 mt-1">{selectedRule.description}</p>
            </div>
            <div className="p-6 space-y-6">
              {/* Rule Details */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-xs text-gray-500">Category</span>
                  <p className="text-sm font-medium text-gray-900">{selectedRule.category}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Business Process</span>
                  <p className="text-sm font-medium text-gray-900">{selectedRule.businessProcess}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Severity</span>
                  <p><span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getSeverityColor(selectedRule.severity)}`}>{selectedRule.severity}</span></p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Status</span>
                  <p><span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(selectedRule.status)}`}>{selectedRule.status}</span></p>
                </div>
              </div>

              {/* Conflicting Functions */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-red-800 mb-2">Function 1: {selectedRule.function1.name}</h4>
                  <div className="space-y-1">
                    {selectedRule.function1.transactions.map((t, i) => (
                      <span key={i} className="inline-block text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded mr-1 mb-1">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-orange-800 mb-2">Function 2: {selectedRule.function2.name}</h4>
                  <div className="space-y-1">
                    {selectedRule.function2.transactions.map((t, i) => (
                      <span key={i} className="inline-block text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded mr-1 mb-1">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Stats */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold text-red-600">{selectedRule.violationCount}</p>
                    <p className="text-xs text-gray-500">Active Violations</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">{selectedRule.lastRun}</p>
                    <p className="text-xs text-gray-500">Last Run</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">{selectedRule.createdBy}</p>
                    <p className="text-xs text-gray-500">Created By</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={() => setSelectedRule(null)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm"
              >
                Close
              </button>
              <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm flex items-center gap-2">
                <PlayIcon className="h-4 w-4" />
                Run Analysis
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
