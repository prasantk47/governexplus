import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  PlusIcon,
  ExclamationTriangleIcon,
  UserGroupIcon,
  CubeIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';
import { rolesApi } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  SearchInput,
  Select,
  Table,
  Pagination,
  RiskBadge,
  Badge,
  ErrorState,
} from '../../components/ui';

interface Role {
  id: number;
  role_id: string;
  role_name: string;
  description: string | null;
  role_type: string;
  risk_level: string;
  source_system: string;
  user_count: number;
  permission_count: number;
  sod_conflict_count: number;
  is_sensitive: boolean;
  status: string;
  owner_user_id: string | null;
  created_at: string;
}

interface RolesResponse {
  items: Role[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

const typeVariant: Record<string, 'info' | 'neutral' | 'warning' | 'success' | 'danger'> = {
  single: 'neutral',
  business: 'info',
  composite: 'warning',
  derived: 'success',
  emergency: 'danger',
  technical: 'neutral',
};

export function RoleList() {
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [page, setPage] = useState(1);
  const limit = 20;

  const { data: rolesData, isLoading, error, refetch } = useQuery<RolesResponse>({
    queryKey: ['roles', { searchTerm, typeFilter, riskFilter, page }],
    queryFn: async () => {
      const response = await rolesApi.list({
        search: searchTerm || undefined,
        role_type: typeFilter !== 'all' ? typeFilter : undefined,
        risk_level: riskFilter !== 'all' ? riskFilter : undefined,
        limit,
        offset: (page - 1) * limit,
      });
      return response.data;
    },
  });

  const roles = rolesData?.items || [];
  const total = rolesData?.total || 0;

  const totalAssignments = roles.reduce((acc, r) => acc + (r.user_count || 0), 0);
  const highRiskCount = roles.filter((r) => r.risk_level === 'high' || r.risk_level === 'critical').length;
  const sensitiveCount = roles.filter((r) => r.is_sensitive).length;

  const columns = [
    {
      key: 'role',
      header: 'Role',
      render: (role: Role) => (
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center flex-shrink-0">
            <CubeIcon className="h-4 w-4 text-gray-600" />
          </div>
          <div>
            <div className="text-sm font-medium text-gray-900">{role.role_id}</div>
            <div className="text-xs text-gray-400 max-w-xs truncate">{role.role_name}</div>
          </div>
        </div>
      ),
    },
    {
      key: 'source_system',
      header: 'System',
      render: (role: Role) => (
        <Badge variant="neutral" size="sm">{role.source_system || 'SAP'}</Badge>
      ),
    },
    {
      key: 'role_type',
      header: 'Type',
      render: (role: Role) => (
        <Badge variant={typeVariant[role.role_type] || 'neutral'} size="sm">
          {role.role_type?.charAt(0).toUpperCase() + role.role_type?.slice(1)}
        </Badge>
      ),
    },
    {
      key: 'risk_level',
      header: 'Risk',
      render: (role: Role) => <RiskBadge level={role.risk_level} />,
    },
    {
      key: 'user_count',
      header: 'Users',
      render: (role: Role) => (
        <span className="text-sm text-gray-600">{role.user_count || 0}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (role: Role) => (
        <Link
          to={`/roles/designer/${role.role_id}`}
          className="text-xs font-medium text-primary-600 hover:text-primary-800 transition-colors"
        >
          View
        </Link>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Role Catalog"
        subtitle="Browse and manage roles across all connected systems"
        actions={
          <Button size="sm" icon={<PlusIcon className="h-4 w-4" />} href="/roles/designer">
            Create Role
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <StatCard title="Total Roles" value={total} icon={CubeIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Assignments" value={totalAssignments} icon={UserGroupIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="High Risk" value={highRiskCount} icon={ExclamationTriangleIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Sensitive" value={sensitiveCount} icon={ShieldExclamationIcon} iconBgColor="stat-icon-red" iconColor="" />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col lg:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search roles..."
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
              onClear={() => { setSearchTerm(''); setPage(1); }}
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Select
              value={typeFilter}
              onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
              options={[
                { value: 'all', label: 'All Types' },
                { value: 'single', label: 'Single' },
                { value: 'business', label: 'Business' },
                { value: 'composite', label: 'Composite' },
                { value: 'derived', label: 'Derived' },
                { value: 'emergency', label: 'Emergency' },
              ]}
            />
            <Select
              value={riskFilter}
              onChange={(e) => { setRiskFilter(e.target.value); setPage(1); }}
              options={[
                { value: 'all', label: 'All Risk' },
                { value: 'critical', label: 'Critical' },
                { value: 'high', label: 'High' },
                { value: 'medium', label: 'Medium' },
                { value: 'low', label: 'Low' },
              ]}
            />
          </div>
        </div>
      </Card>

      {/* Table */}
      {error ? (
        <Card><ErrorState title="Failed to load roles" message="Please try again." onRetry={() => refetch()} /></Card>
      ) : (
        <>
          <Table columns={columns} data={roles} loading={isLoading} emptyMessage="No roles found matching your criteria" />
          {total > limit && (
            <Card padding="none">
              <Pagination total={total} page={page} pageSize={limit} onPageChange={setPage} />
            </Card>
          )}
        </>
      )}
    </div>
  );
}
