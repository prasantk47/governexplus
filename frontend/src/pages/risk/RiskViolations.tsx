import { useState } from 'react';
import toast from 'react-hot-toast';
import {
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  FireIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  SearchInput,
  Select,
  Table,
  Badge,
  RiskBadge,
} from '../../components/ui';

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
    id: 'VIO-2024-001', user: 'John Smith', userId: 'jsmith', department: 'Finance',
    type: 'SoD Conflict', rule: 'Create Vendor / Approve Payment', riskLevel: 'critical',
    detectedDate: '2024-01-20', status: 'open', systems: ['SAP ECC', 'SAP S/4HANA'],
  },
  {
    id: 'VIO-2024-002', user: 'Mary Brown', userId: 'mbrown', department: 'IT',
    type: 'Excessive Access', rule: 'Admin access without business need', riskLevel: 'high',
    detectedDate: '2024-01-19', status: 'in_review', systems: ['Azure AD', 'AWS'],
  },
  {
    id: 'VIO-2024-003', user: 'Tom Davis', userId: 'tdavis', department: 'Procurement',
    type: 'SoD Conflict', rule: 'Create PO / Approve PO', riskLevel: 'high',
    detectedDate: '2024-01-18', status: 'mitigated', mitigation: 'Dual approval workflow implemented',
    systems: ['SAP ECC'],
  },
  {
    id: 'VIO-2024-004', user: 'Alice Wilson', userId: 'awilson', department: 'HR',
    type: 'Sensitive Access', rule: 'Payroll data access', riskLevel: 'medium',
    detectedDate: '2024-01-17', status: 'open', systems: ['Workday'],
  },
  {
    id: 'VIO-2024-005', user: 'Bob Johnson', userId: 'bjohnson', department: 'Finance',
    type: 'SoD Conflict', rule: 'Create GL Entry / Post GL Entry', riskLevel: 'critical',
    detectedDate: '2024-01-16', status: 'open', systems: ['SAP ECC'],
  },
  {
    id: 'VIO-2024-006', user: 'Carol White', userId: 'cwhite', department: 'Sales',
    type: 'Dormant Account', rule: 'No login activity for 90+ days', riskLevel: 'low',
    detectedDate: '2024-01-15', status: 'accepted', mitigation: 'Employee on extended leave',
    systems: ['Salesforce'],
  },
  {
    id: 'VIO-2024-007', user: 'David Lee', userId: 'dlee', department: 'Engineering',
    type: 'Excessive Access', rule: 'Production DB admin without justification', riskLevel: 'high',
    detectedDate: '2024-01-14', status: 'in_review', systems: ['AWS RDS', 'MongoDB Atlas'],
  },
  {
    id: 'VIO-2024-008', user: 'Emma Garcia', userId: 'egarcia', department: 'Finance',
    type: 'SoD Conflict', rule: 'Create Invoice / Approve Invoice', riskLevel: 'critical',
    detectedDate: '2024-01-13', status: 'mitigated', mitigation: 'Invoice approval removed',
    systems: ['SAP ECC'],
  },
];

const statusVariant: Record<string, 'danger' | 'info' | 'success' | 'neutral'> = {
  open: 'danger',
  in_review: 'info',
  mitigated: 'success',
  accepted: 'neutral',
};

const statusLabel: Record<string, string> = {
  open: 'Open',
  in_review: 'In Review',
  mitigated: 'Mitigated',
  accepted: 'Accepted',
};

export function RiskViolations() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');

  const handleExportReport = () => {
    const headers = ['ID', 'User', 'User ID', 'Department', 'Type', 'Rule', 'Risk Level', 'Status', 'Detected Date', 'Systems', 'Mitigation'];
    const rows = filteredViolations.map(v => [
      v.id, v.user, v.userId, v.department, v.type, v.rule, v.riskLevel, v.status,
      v.detectedDate, v.systems.join('; '), v.mitigation || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

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
  const mitigatedCount = mockViolations.filter((v) => v.status === 'mitigated').length;

  const columns = [
    {
      key: 'violation',
      header: 'Violation',
      render: (v: Violation) => (
        <div>
          <div className="text-sm font-medium text-primary-600">{v.id}</div>
          <div className="text-xs text-gray-400 max-w-xs truncate">{v.rule}</div>
        </div>
      ),
    },
    {
      key: 'user',
      header: 'User / Department',
      render: (v: Violation) => (
        <div>
          <div className="text-sm font-medium text-gray-900">{v.user}</div>
          <div className="text-xs text-gray-400">{v.department}</div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (v: Violation) => (
        <span className="text-sm text-gray-600">{v.type}</span>
      ),
    },
    {
      key: 'risk',
      header: 'Risk',
      render: (v: Violation) => <RiskBadge level={v.riskLevel} />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (v: Violation) => (
        <Badge variant={statusVariant[v.status] || 'neutral'} size="sm">
          {statusLabel[v.status] || v.status}
        </Badge>
      ),
    },
    {
      key: 'systems',
      header: 'Systems',
      render: (v: Violation) => (
        <div className="flex flex-wrap gap-1">
          {v.systems.map((system) => (
            <Badge key={system} variant="neutral" size="sm">{system}</Badge>
          ))}
        </div>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (v: Violation) => (
        <div className="flex justify-end gap-2">
          <button
            onClick={() => toast.success(`Opening violation ${v.id}...`)}
            className="text-xs font-medium text-primary-600 hover:text-primary-800 transition-colors"
          >
            View
          </button>
          {v.status === 'open' && (
            <button
              onClick={() => toast.success(`Opening mitigation workflow for ${v.id}...`)}
              className="text-xs font-medium text-green-600 hover:text-green-800 transition-colors"
            >
              Mitigate
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Violations"
        subtitle="View and manage all active SoD conflicts and access violations"
        actions={
          <Button size="sm" onClick={handleExportReport}>
            Export Report
          </Button>
        }
      />

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <StatCard title="Critical Open" value={criticalCount} icon={ExclamationCircleIcon} iconBgColor="stat-icon-red" iconColor="" />
        <StatCard title="High Open" value={highCount} icon={FireIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Total Open" value={openCount} icon={ClockIcon} iconBgColor="stat-icon-yellow" iconColor="" />
        <StatCard title="Mitigated (30d)" value={mitigatedCount} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col lg:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by user, ID, or rule..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClear={() => setSearchTerm('')}
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Status' },
                { value: 'open', label: 'Open' },
                { value: 'in_review', label: 'In Review' },
                { value: 'mitigated', label: 'Mitigated' },
                { value: 'accepted', label: 'Accepted' },
              ]}
            />
            <Select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Risk' },
                { value: 'critical', label: 'Critical' },
                { value: 'high', label: 'High' },
                { value: 'medium', label: 'Medium' },
                { value: 'low', label: 'Low' },
              ]}
            />
            <Select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Types' },
                { value: 'SoD Conflict', label: 'SoD Conflict' },
                { value: 'Excessive Access', label: 'Excessive Access' },
                { value: 'Sensitive Access', label: 'Sensitive Access' },
                { value: 'Dormant Account', label: 'Dormant Account' },
              ]}
            />
          </div>
        </div>
      </Card>

      {/* Violations Table */}
      <Table
        columns={columns}
        data={filteredViolations}
        emptyMessage="No violations found matching your criteria"
      />
    </div>
  );
}
