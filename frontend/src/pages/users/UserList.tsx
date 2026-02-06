import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  UserPlusIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  UserCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { usersApi, CreateUserRequest } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Input,
  Select,
  SearchInput,
  Table,
  Pagination,
  Modal,
  StatusBadge,
  RiskBadge,
  Badge,
  LoadingState,
  ErrorState,
} from '../../components/ui';

interface User {
  id: number;
  user_id: string;
  username: string;
  email: string | null;
  full_name: string | null;
  department: string | null;
  title: string | null;
  status: string;
  risk_score: number;
  risk_level: string;
  violation_count: number;
  role_count: number;
  last_login: string | null;
}

interface UsersResponse {
  items: User[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

interface UserStats {
  total_users: number;
  active_users: number;
  inactive_users: number;
  suspended_users: number;
  high_risk_users: number;
  users_with_violations: number;
  departments: { name: string; count: number }[];
}

const riskBarColor: Record<string, string> = {
  low: 'bg-emerald-500',
  medium: 'bg-amber-500',
  high: 'bg-orange-500',
  critical: 'bg-red-500',
};

export function UserList() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [departmentFilter, setDepartmentFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newUser, setNewUser] = useState<CreateUserRequest>({
    user_id: '',
    username: '',
    full_name: '',
    email: '',
    department: '',
    title: '',
    password: '',
  });

  const limit = 20;

  const { data: usersData, isLoading, error, refetch } = useQuery<UsersResponse>({
    queryKey: ['users', { searchTerm, statusFilter, riskFilter, departmentFilter, page }],
    queryFn: async () => {
      const response = await usersApi.list({
        search: searchTerm || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        risk_level: riskFilter !== 'all' ? riskFilter : undefined,
        department: departmentFilter !== 'all' ? departmentFilter : undefined,
        limit,
        offset: (page - 1) * limit,
      });
      return response.data;
    },
  });

  const { data: statsData } = useQuery<UserStats>({
    queryKey: ['userStats'],
    queryFn: async () => {
      const response = await usersApi.getStats();
      return response.data;
    },
  });

  const { data: departmentsData } = useQuery<string[]>({
    queryKey: ['userDepartments'],
    queryFn: async () => {
      const response = await usersApi.getDepartments();
      return response.data;
    },
  });

  const createUserMutation = useMutation({
    mutationFn: (userData: CreateUserRequest) => usersApi.create(userData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      queryClient.invalidateQueries({ queryKey: ['userStats'] });
      toast.success('User created successfully!');
      setShowAddModal(false);
      setNewUser({ user_id: '', username: '', full_name: '', email: '', department: '', title: '', password: '' });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create user');
    },
  });

  const handleAddUser = () => {
    if (!newUser.user_id || !newUser.username || !newUser.full_name) {
      toast.error('User ID, username, and full name are required');
      return;
    }
    createUserMutation.mutate(newUser);
  };

  const users = usersData?.items || [];
  const total = usersData?.total || 0;
  const departments = departmentsData || [];
  const stats = statsData || { total_users: 0, active_users: 0, high_risk_users: 0, users_with_violations: 0 };

  const columns = [
    {
      key: 'user',
      header: 'User',
      render: (user: User) => (
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-semibold text-primary-700">
              {(user.full_name || user.username).split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)}
            </span>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-900">{user.full_name || user.username}</div>
            <div className="text-xs text-gray-400">{user.email || user.user_id}</div>
          </div>
        </div>
      ),
    },
    {
      key: 'department',
      header: 'Department',
      render: (user: User) => (
        <span className="text-sm text-gray-600">{user.department || '-'}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (user: User) => <StatusBadge status={user.status} />,
    },
    {
      key: 'risk_score',
      header: 'Risk',
      render: (user: User) => (
        <div className="flex items-center gap-2">
          <div className="w-14 bg-gray-100 rounded-full h-1.5">
            <div
              className={`h-1.5 rounded-full ${riskBarColor[user.risk_level] || 'bg-gray-300'}`}
              style={{ width: `${Math.min(user.risk_score, 100)}%` }}
            />
          </div>
          <span className="text-xs font-medium text-gray-500 w-6">{Math.round(user.risk_score)}</span>
        </div>
      ),
    },
    {
      key: 'violations',
      header: 'Violations',
      render: (user: User) =>
        user.violation_count > 0 ? (
          <Badge variant="danger" size="sm">{user.violation_count}</Badge>
        ) : (
          <span className="text-xs text-gray-400">None</span>
        ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (user: User) => (
        <Link
          to={`/users/${user.user_id}`}
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
        title="User Management"
        subtitle="Manage users and monitor their access risk profiles"
        actions={
          <>
            <Button variant="ghost" size="sm" onClick={() => refetch()} icon={<ArrowPathIcon className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />}>
              Refresh
            </Button>
            <Button size="sm" onClick={() => setShowAddModal(true)} icon={<UserPlusIcon className="h-4 w-4" />}>
              Add User
            </Button>
          </>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <StatCard title="Total Users" value={stats.total_users} icon={UserCircleIcon} iconBgColor="stat-icon-blue" iconColor="" link="/users" />
        <StatCard title="Active" value={stats.active_users} icon={ShieldCheckIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="High Risk" value={stats.high_risk_users} icon={ExclamationTriangleIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="With Violations" value={stats.users_with_violations} icon={ExclamationTriangleIcon} iconBgColor="stat-icon-red" iconColor="" />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col lg:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by name, email, or ID..."
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
              onClear={() => { setSearchTerm(''); setPage(1); }}
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              options={[
                { value: 'all', label: 'All Status' },
                { value: 'active', label: 'Active' },
                { value: 'inactive', label: 'Inactive' },
                { value: 'suspended', label: 'Suspended' },
                { value: 'locked', label: 'Locked' },
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
            <Select
              value={departmentFilter}
              onChange={(e) => { setDepartmentFilter(e.target.value); setPage(1); }}
              options={[
                { value: 'all', label: 'All Departments' },
                ...departments.map((d) => ({ value: d, label: d })),
              ]}
            />
          </div>
        </div>
      </Card>

      {/* Table */}
      {error ? (
        <Card><ErrorState title="Failed to load users" message="Please try again." onRetry={() => refetch()} /></Card>
      ) : (
        <>
          <Table columns={columns} data={users} loading={isLoading} emptyMessage="No users found matching your criteria" />
          {total > limit && (
            <Card padding="none">
              <Pagination total={total} page={page} pageSize={limit} onPageChange={setPage} />
            </Card>
          )}
        </>
      )}

      {/* Add User Modal */}
      <Modal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Add New User"
        subtitle="Create a new user account"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setShowAddModal(false)}>Cancel</Button>
            <Button size="sm" onClick={handleAddUser} loading={createUserMutation.isPending}>Create User</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="User ID"
              required
              value={newUser.user_id}
              onChange={(e) => setNewUser({ ...newUser, user_id: e.target.value })}
              placeholder="USR001"
            />
            <Input
              label="Username"
              required
              value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
              placeholder="jsmith"
            />
          </div>
          <Input
            label="Full Name"
            required
            value={newUser.full_name}
            onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
            placeholder="John Smith"
          />
          <Input
            label="Email"
            type="email"
            value={newUser.email}
            onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
            placeholder="jsmith@company.com"
          />
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Department"
              value={newUser.department}
              onChange={(e) => setNewUser({ ...newUser, department: e.target.value })}
              placeholder="Select..."
              options={[
                { value: 'Finance', label: 'Finance' },
                { value: 'IT', label: 'IT' },
                { value: 'HR', label: 'HR' },
                { value: 'Procurement', label: 'Procurement' },
                { value: 'Sales', label: 'Sales' },
                { value: 'Engineering', label: 'Engineering' },
                { value: 'Operations', label: 'Operations' },
              ]}
            />
            <Input
              label="Job Title"
              value={newUser.title}
              onChange={(e) => setNewUser({ ...newUser, title: e.target.value })}
              placeholder="Senior Accountant"
            />
          </div>
          <Input
            label="Password"
            type="password"
            value={newUser.password}
            onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
            placeholder="For platform login (min 8 chars)"
            helpText="Optional - for direct platform login"
          />
        </div>
      </Modal>
    </div>
  );
}
