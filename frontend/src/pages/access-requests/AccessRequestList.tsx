import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  PlusIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentTextIcon,
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

interface AccessRequest {
  id: string;
  role: string;
  system: string;
  status: 'pending' | 'approved' | 'rejected' | 'in_review';
  requestDate: string;
  approver: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  businessJustification: string;
}

const mockRequests: AccessRequest[] = [
  { id: 'REQ-2024-001', role: 'SAP_MM_BUYER', system: 'SAP ECC', status: 'pending', requestDate: '2024-01-20', approver: 'John Manager', riskLevel: 'medium', businessJustification: 'Need to process purchase orders for Q1 projects' },
  { id: 'REQ-2024-002', role: 'SAP_FI_AP_CLERK', system: 'SAP ECC', status: 'approved', requestDate: '2024-01-18', approver: 'Sarah Director', riskLevel: 'low', businessJustification: 'Accounts payable processing role' },
  { id: 'REQ-2024-003', role: 'ADMIN_FULL_ACCESS', system: 'Azure AD', status: 'in_review', requestDate: '2024-01-19', approver: 'IT Security Team', riskLevel: 'critical', businessJustification: 'Emergency admin access for system maintenance' },
  { id: 'REQ-2024-004', role: 'HR_BENEFITS_ADMIN', system: 'Workday', status: 'rejected', requestDate: '2024-01-15', approver: 'HR Manager', riskLevel: 'high', businessJustification: 'Requesting for benefits administration tasks' },
  { id: 'REQ-2024-005', role: 'READ_ONLY_REPORTS', system: 'Salesforce', status: 'approved', requestDate: '2024-01-17', approver: 'Sales Director', riskLevel: 'low', businessJustification: 'View sales reports for quarterly planning' },
];

const statusVariant: Record<string, 'warning' | 'success' | 'danger' | 'info'> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
  in_review: 'info',
};

const statusLabel: Record<string, string> = {
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
  in_review: 'In Review',
};

export function AccessRequestList() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredRequests = mockRequests.filter((req) => {
    const matchesSearch =
      req.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      req.role.toLowerCase().includes(searchTerm.toLowerCase()) ||
      req.system.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || req.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const columns = [
    {
      key: 'id',
      header: 'Request ID',
      render: (r: AccessRequest) => (
        <span className="text-sm font-medium text-primary-600">{r.id}</span>
      ),
    },
    {
      key: 'role',
      header: 'Role / System',
      render: (r: AccessRequest) => (
        <div>
          <div className="text-sm font-medium text-gray-900">{r.role}</div>
          <div className="text-xs text-gray-400">{r.system}</div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (r: AccessRequest) => (
        <Badge variant={statusVariant[r.status] || 'neutral'} size="sm">
          {statusLabel[r.status] || r.status}
        </Badge>
      ),
    },
    {
      key: 'risk',
      header: 'Risk Level',
      render: (r: AccessRequest) => <RiskBadge level={r.riskLevel} />,
    },
    {
      key: 'date',
      header: 'Date',
      render: (r: AccessRequest) => (
        <span className="text-sm text-gray-500">{r.requestDate}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (r: AccessRequest) => (
        <Link
          to={`/access-requests/${r.id}`}
          className="text-xs font-medium text-primary-600 hover:text-primary-800 transition-colors"
        >
          View Details
        </Link>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Access Requests"
        subtitle="View and manage your access requests across all systems"
        actions={
          <Button size="sm" icon={<PlusIcon className="h-4 w-4" />} href="/access-requests/new">
            New Request
          </Button>
        }
      />

      {/* Request Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <StatCard title="Total Requests" value={mockRequests.length} icon={DocumentTextIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Pending" value={mockRequests.filter((r) => r.status === 'pending').length} icon={ClockIcon} iconBgColor="stat-icon-yellow" iconColor="" />
        <StatCard title="Approved" value={mockRequests.filter((r) => r.status === 'approved').length} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Rejected" value={mockRequests.filter((r) => r.status === 'rejected').length} icon={XCircleIcon} iconBgColor="stat-icon-red" iconColor="" />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search requests..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClear={() => setSearchTerm('')}
            />
          </div>
          <div className="flex items-center gap-2">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={[
                { value: 'all', label: 'All Status' },
                { value: 'pending', label: 'Pending' },
                { value: 'in_review', label: 'In Review' },
                { value: 'approved', label: 'Approved' },
                { value: 'rejected', label: 'Rejected' },
              ]}
            />
          </div>
        </div>
      </Card>

      {/* Requests Table */}
      <Table
        columns={columns}
        data={filteredRequests}
        emptyMessage="No requests found matching your criteria"
      />
    </div>
  );
}
