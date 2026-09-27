import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { accessRequestApi } from '../../services/api';
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
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Debounce search input — wait 300 ms before firing a new request
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const { data: requests = [] } = useQuery({
    queryKey: ['accessRequests', statusFilter, debouncedSearch],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (debouncedSearch) params.search = debouncedSearch;
      const res = await accessRequestApi.list(params);
      return res.data?.requests || res.data || [];
    },
  });

  // Client-side fallback filter in case the backend ignores the params
  const filteredRequests = (requests as AccessRequest[]).filter((req) => {
    const matchesSearch =
      !searchTerm ||
      String(req.id).toLowerCase().includes(searchTerm.toLowerCase()) ||
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
        <StatCard title="Total Requests" value={(requests as AccessRequest[]).length} icon={DocumentTextIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Pending" value={(requests as AccessRequest[]).filter((r) => r.status === 'pending').length} icon={ClockIcon} iconBgColor="stat-icon-yellow" iconColor="" />
        <StatCard title="Approved" value={(requests as AccessRequest[]).filter((r) => r.status === 'approved').length} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Rejected" value={(requests as AccessRequest[]).filter((r) => r.status === 'rejected').length} icon={XCircleIcon} iconBgColor="stat-icon-red" iconColor="" />
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
