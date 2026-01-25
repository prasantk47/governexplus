import { useState } from 'react';
import toast from 'react-hot-toast';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  FireIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';

interface Violation {
  id: string;
  user: string;
  userId: string;
  department: string;
  type: 'SoD Conflict' | 'Excessive Access' | 'Sensitive Access' | 'Dormant Account';
  rule: string;
  riskLevel: 'critical' | 'high' | 'medium' | 'low';
  detectedDate: string;
  status: 'open' | 'in_review' | 'mitigated' | 'accepted';
  mitigation?: string;
  systems: string[];
}

const mockViolations: Violation[] = [
  {
    id: 'VIO-2024-001',
    user: 'John Smith',
    userId: 'jsmith',
    department: 'Finance',
    type: 'SoD Conflict',
    rule: 'Create Vendor / Approve Payment',
    riskLevel: 'critical',
    detectedDate: '2024-01-20',
    status: 'open',
    systems: ['SAP ECC', 'SAP S/4HANA'],
  },
  {
    id: 'VIO-2024-002',
    user: 'Mary Brown',
    userId: 'mbrown',
    department: 'IT',
    type: 'Excessive Access',
    rule: 'Admin access without business need',
    riskLevel: 'high',
    detectedDate: '2024-01-19',
    status: 'in_review',
    systems: ['Azure AD', 'AWS'],
  },
  {
    id: 'VIO-2024-003',
    user: 'Tom Davis',
    userId: 'tdavis',
    department: 'Procurement',
    type: 'SoD Conflict',
    rule: 'Create PO / Approve PO',
    riskLevel: 'high',
    detectedDate: '2024-01-18',
    status: 'mitigated',
    mitigation: 'Dual approval workflow implemented',
    systems: ['SAP ECC'],
  },
  {
    id: 'VIO-2024-004',
    user: 'Alice Wilson',
    userId: 'awilson',
    department: 'HR',
    type: 'Sensitive Access',
    rule: 'Payroll data access',
    riskLevel: 'medium',
    detectedDate: '2024-01-17',
    status: 'open',
    systems: ['Workday'],
  },
  {
    id: 'VIO-2024-005',
    user: 'Bob Johnson',
    userId: 'bjohnson',
    department: 'Finance',
    type: 'SoD Conflict',
    rule: 'Create GL Entry / Post GL Entry',
    riskLevel: 'critical',
    detectedDate: '2024-01-16',
    status: 'open',
    systems: ['SAP ECC'],
  },
  {
    id: 'VIO-2024-006',
    user: 'Carol White',
    userId: 'cwhite',
    department: 'Sales',
    type: 'Dormant Account',
    rule: 'No login activity for 90+ days',
    riskLevel: 'low',
    detectedDate: '2024-01-15',
    status: 'accepted',
    mitigation: 'Employee on extended leave',
    systems: ['Salesforce'],
  },
  {
    id: 'VIO-2024-007',
    user: 'David Lee',
    userId: 'dlee',
    department: 'Engineering',
    type: 'Excessive Access',
    rule: 'Production DB admin without justification',
    riskLevel: 'high',
    detectedDate: '2024-01-14',
    status: 'in_review',
    systems: ['AWS RDS', 'MongoDB Atlas'],
  },
  {
    id: 'VIO-2024-008',
    user: 'Emma Garcia',
    userId: 'egarcia',
    department: 'Finance',
    type: 'SoD Conflict',
    rule: 'Create Invoice / Approve Invoice',
    riskLevel: 'critical',
    detectedDate: '2024-01-13',
    status: 'mitigated',
    mitigation: 'Invoice approval removed',
    systems: ['SAP ECC'],
  },
];

const riskLevelConfig = {
  critical: { color: 'bg-red-100 text-red-800', label: 'Critical', priority: 1 },
  high: { color: 'bg-orange-100 text-orange-800', label: 'High', priority: 2 },
  medium: { color: 'bg-yellow-100 text-yellow-800', label: 'Medium', priority: 3 },
  low: { color: 'bg-green-100 text-green-800', label: 'Low', priority: 4 },
};

const statusConfig = {
  open: { color: 'bg-red-100 text-red-800', label: 'Open', icon: ExclamationTriangleIcon },
  in_review: { color: 'bg-blue-100 text-blue-800', label: 'In Review', icon: ShieldExclamationIcon },
  mitigated: { color: 'bg-green-100 text-green-800', label: 'Mitigated', icon: CheckCircleIcon },
  accepted: { color: 'bg-gray-100 text-gray-800', label: 'Accepted', icon: CheckCircleIcon },
};

export function RiskViolations() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');

  const handleExportReport = () => {
    // Generate CSV content
    const headers = ['ID', 'User', 'User ID', 'Department', 'Type', 'Rule', 'Risk Level', 'Status', 'Detected Date', 'Systems', 'Mitigation'];
    const rows = filteredViolations.map(v => [
      v.id,
      v.user,
      v.userId,
      v.department,
      v.type,
      v.rule,
      v.riskLevel,
      v.status,
      v.detectedDate,
      v.systems.join('; '),
      v.mitigation || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `risk_violations_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);

    toast.success(`Exported ${filteredViolations.length} violations to CSV`);
  };

  const filteredViolations = mockViolations.filter((v) => {
    const matchesSearch =
      v.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.rule.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || v.status === statusFilter;
    const matchesRisk = riskFilter === 'all' || v.riskLevel === riskFilter;
    const matchesType = typeFilter === 'all' || v.type === typeFilter;
    return matchesSearch && matchesStatus && matchesRisk && matchesType;
  });

  const criticalCount = mockViolations.filter((v) => v.riskLevel === 'critical' && v.status === 'open').length;
  const highCount = mockViolations.filter((v) => v.riskLevel === 'high' && v.status === 'open').length;
  const openCount = mockViolations.filter((v) => v.status === 'open').length;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Risk Violations</h1>
          <p className="page-subtitle">
            View and manage all active SoD conflicts and access violations
          </p>
        </div>
        <button
          onClick={handleExportReport}
          className="btn-primary"
        >
          Export Report
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="stat-card-accent border-red-400">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-red">
              <ExclamationCircleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Critical Open</div>
              <div className="stat-value text-red-600">{criticalCount}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-orange">
              <FireIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">High Open</div>
              <div className="stat-value text-orange-600">{highCount}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-yellow">
              <ClockIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Total Open</div>
              <div className="stat-value">{openCount}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-green">
              <CheckCircleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Mitigated (30d)</div>
              <div className="stat-value text-green-600">
                {mockViolations.filter((v) => v.status === 'mitigated').length}
              </div>
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
              placeholder="Search by user, ID, or rule..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-5 w-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">All Status</option>
              <option value="open">Open</option>
              <option value="in_review">In Review</option>
              <option value="mitigated">Mitigated</option>
              <option value="accepted">Accepted</option>
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
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">All Types</option>
              <option value="SoD Conflict">SoD Conflict</option>
              <option value="Excessive Access">Excessive Access</option>
              <option value="Sensitive Access">Sensitive Access</option>
              <option value="Dormant Account">Dormant Account</option>
            </select>
          </div>
        </div>
      </div>

      {/* Violations Table */}
      <div className="card overflow-hidden">
        <table className="min-w-full divide-y divide-gray-100">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Violation
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User / Department
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Risk
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Systems
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {filteredViolations.map((violation) => {
              const riskInfo = riskLevelConfig[violation.riskLevel];
              const statusInfo = statusConfig[violation.status];
              const StatusIcon = statusInfo.icon;

              return (
                <tr key={violation.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-primary-600">{violation.id}</div>
                    <div className="text-xs text-gray-500">{violation.rule}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{violation.user}</div>
                    <div className="text-xs text-gray-500">{violation.department}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-700">{violation.type}</span>
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
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusInfo.color}`}
                    >
                      <StatusIcon className="h-3 w-3 mr-1" />
                      {statusInfo.label}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {violation.systems.map((system) => (
                        <span
                          key={system}
                          className="inline-flex px-2 py-0.5 rounded bg-gray-100 text-xs text-gray-600"
                        >
                          {system}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => toast.success(`Opening violation ${violation.id}...`)}
                      className="text-primary-600 hover:text-primary-900 mr-3"
                    >
                      View
                    </button>
                    {violation.status === 'open' && (
                      <button
                        onClick={() => toast.success(`Opening mitigation workflow for ${violation.id}...`)}
                        className="text-green-600 hover:text-green-900"
                      >
                        Mitigate
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredViolations.length === 0 && (
          <div className="text-center py-12">
            <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-gray-500">No violations found matching your criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}
