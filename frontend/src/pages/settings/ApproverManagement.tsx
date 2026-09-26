import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  UserGroupIcon,
  CheckCircleIcon,
  ClockIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { approverManagementApi } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
  Table,
  Pagination,
  SearchInput,
  Select,
  Badge,
  StatusBadge,
  Modal,
  Input,
  Textarea,
  LoadingState,
  ErrorState,
  EmptyState,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';

const APPROVER_TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'LINE_MANAGER', label: 'Line Manager' },
  { value: 'ROLE_OWNER', label: 'Role Owner' },
  { value: 'PROCESS_OWNER', label: 'Process Owner' },
  { value: 'DATA_OWNER', label: 'Data Owner' },
  { value: 'SECURITY_OFFICER', label: 'Security Officer' },
  { value: 'COMPLIANCE_OFFICER', label: 'Compliance Officer' },
  { value: 'SYSTEM_OWNER', label: 'System Owner' },
  { value: 'DELEGATE', label: 'Delegate' },
  { value: 'GOVERNANCE_DESK', label: 'Governance Desk' },
  { value: 'CISO', label: 'CISO' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
  { value: 'suspended', label: 'Suspended' },
];

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';

const TYPE_BADGE_COLORS: Record<string, BadgeVariant> = {
  LINE_MANAGER: 'info',
  ROLE_OWNER: 'info',
  PROCESS_OWNER: 'success',
  DATA_OWNER: 'warning',
  SECURITY_OFFICER: 'danger',
  COMPLIANCE_OFFICER: 'warning',
  SYSTEM_OWNER: 'info',
  DELEGATE: 'neutral',
  AI_RECOMMENDED: 'info',
  GOVERNANCE_DESK: 'info',
  CISO: 'danger',
};

const TYPE_LABELS: Record<string, string> = {
  LINE_MANAGER: 'Line Manager',
  ROLE_OWNER: 'Role Owner',
  PROCESS_OWNER: 'Process Owner',
  DATA_OWNER: 'Data Owner',
  SECURITY_OFFICER: 'Security Officer',
  COMPLIANCE_OFFICER: 'Compliance Officer',
  SYSTEM_OWNER: 'System Owner',
  DELEGATE: 'Delegate',
  AI_RECOMMENDED: 'AI Recommended',
  GOVERNANCE_DESK: 'Governance Desk',
  CISO: 'CISO',
};

interface ApproverForm {
  approver_id: string;
  name: string;
  email: string;
  approver_type: string;
  department: string;
  job_title: string;
  process_scope: string;
  system_scope: string;
}

const emptyForm: ApproverForm = {
  approver_id: '',
  name: '',
  email: '',
  approver_type: 'LINE_MANAGER',
  department: '',
  job_title: '',
  process_scope: '',
  system_scope: '',
};

export function ApproverManagement() {
  const queryClient = useQueryClient();

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const limit = 20;

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showOOOModal, setShowOOOModal] = useState(false);
  const [selectedApprover, setSelectedApprover] = useState<any>(null);
  const [form, setForm] = useState<ApproverForm>(emptyForm);
  const [oooUntil, setOooUntil] = useState('');
  const [oooDelegateId, setOooDelegateId] = useState('');
  const [oooReason, setOooReason] = useState('');

  // Data fetching
  const { data: approversData, isLoading, error } = useQuery({
    queryKey: ['approvers', { searchTerm, typeFilter, statusFilter, page }],
    queryFn: async () => {
      const response = await approverManagementApi.list({
        search: searchTerm || undefined,
        approver_type: typeFilter || undefined,
        status: statusFilter || undefined,
        limit,
        offset: (page - 1) * limit,
      });
      return response.data;
    },
  });

  const { data: statsData } = useQuery({
    queryKey: ['approver-stats'],
    queryFn: async () => {
      const response = await approverManagementApi.getStats();
      return response.data;
    },
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await approverManagementApi.create(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvers'] });
      queryClient.invalidateQueries({ queryKey: ['approver-stats'] });
      setShowAddModal(false);
      setForm(emptyForm);
      toast.success('Approver created successfully');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to create approver');
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: any }) => {
      const response = await approverManagementApi.update(id, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvers'] });
      queryClient.invalidateQueries({ queryKey: ['approver-stats'] });
      setShowEditModal(false);
      setSelectedApprover(null);
      toast.success('Approver updated successfully');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to update approver');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await approverManagementApi.delete(id);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvers'] });
      queryClient.invalidateQueries({ queryKey: ['approver-stats'] });
      toast.success('Approver deleted');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to delete approver');
    },
  });

  const toggleAvailabilityMutation = useMutation({
    mutationFn: async ({ id, is_available }: { id: string; is_available: boolean }) => {
      const response = await approverManagementApi.toggleAvailability(id, { is_available });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvers'] });
      queryClient.invalidateQueries({ queryKey: ['approver-stats'] });
    },
  });

  const setOOOMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: any }) => {
      const response = await approverManagementApi.setOOO(id, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvers'] });
      queryClient.invalidateQueries({ queryKey: ['approver-stats'] });
      setShowOOOModal(false);
      setSelectedApprover(null);
      toast.success('Out-of-office set');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Failed to set OOO');
    },
  });

  const clearOOOMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await approverManagementApi.clearOOO(id);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvers'] });
      queryClient.invalidateQueries({ queryKey: ['approver-stats'] });
      toast.success('OOO cleared');
    },
  });

  // Handlers
  const handleCreate = () => {
    createMutation.mutate({
      approver_id: form.approver_id,
      name: form.name,
      email: form.email || undefined,
      approver_type: form.approver_type,
      department: form.department || undefined,
      job_title: form.job_title || undefined,
      process_scope: form.process_scope ? form.process_scope.split(',').map((s) => s.trim()).filter(Boolean) : [],
      system_scope: form.system_scope ? form.system_scope.split(',').map((s) => s.trim()).filter(Boolean) : [],
    });
  };

  const handleUpdate = () => {
    if (!selectedApprover) return;
    updateMutation.mutate({
      id: selectedApprover.approver_id,
      data: {
        name: form.name,
        email: form.email || undefined,
        approver_type: form.approver_type,
        department: form.department || undefined,
        job_title: form.job_title || undefined,
        process_scope: form.process_scope ? form.process_scope.split(',').map((s) => s.trim()).filter(Boolean) : [],
        system_scope: form.system_scope ? form.system_scope.split(',').map((s) => s.trim()).filter(Boolean) : [],
      },
    });
  };

  const handleEdit = (approver: any) => {
    setSelectedApprover(approver);
    setForm({
      approver_id: approver.approver_id,
      name: approver.name,
      email: approver.email || '',
      approver_type: approver.approver_type,
      department: approver.department || '',
      job_title: approver.job_title || '',
      process_scope: (approver.process_scope || []).join(', '),
      system_scope: (approver.system_scope || []).join(', '),
    });
    setShowEditModal(true);
  };

  const handleOOO = (approver: any) => {
    setSelectedApprover(approver);
    setOooUntil('');
    setOooDelegateId('');
    setOooReason('');
    setShowOOOModal(true);
  };

  const handleSetOOO = () => {
    if (!selectedApprover || !oooUntil) return;
    setOOOMutation.mutate({
      id: selectedApprover.approver_id,
      data: {
        ooo_until: new Date(oooUntil).toISOString(),
        delegate_id: oooDelegateId || undefined,
        reason: oooReason || undefined,
      },
    });
  };

  const totalPages = approversData ? Math.ceil(approversData.total / limit) : 0;

  const columns = [
    {
      key: 'name',
      header: 'Name',
      render: (row: any) => (
        <div>
          <div className="font-medium text-white">{row.name}</div>
          <div className="text-xs text-white/50">{row.approver_id}</div>
        </div>
      ),
    },
    {
      key: 'approver_type',
      header: 'Type',
      render: (row: any) => (
        <Badge variant={TYPE_BADGE_COLORS[row.approver_type] || 'neutral'}>
          {TYPE_LABELS[row.approver_type] || row.approver_type}
        </Badge>
      ),
    },
    {
      key: 'email',
      header: 'Email',
      render: (row: any) => (
        <span className="text-white/70">{row.email || '-'}</span>
      ),
    },
    {
      key: 'department',
      header: 'Department',
      render: (row: any) => (
        <span className="text-white/70">{row.department || '-'}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row: any) => <StatusBadge status={row.status} />,
    },
    {
      key: 'is_available',
      header: 'Available',
      render: (row: any) => (
        <button
          onClick={() =>
            toggleAvailabilityMutation.mutate({
              id: row.approver_id,
              is_available: !row.is_available,
            })
          }
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium cursor-pointer transition-colors ${
            row.is_available
              ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
              : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
          }`}
        >
          {row.is_available ? 'Yes' : 'No'}
        </button>
      ),
    },
    {
      key: 'is_ooo',
      header: 'OOO',
      render: (row: any) =>
        row.is_ooo ? (
          <div className="flex items-center gap-1">
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400">
              OOO
            </span>
            <button
              onClick={() => clearOOOMutation.mutate(row.approver_id)}
              className="text-xs text-white/40 hover:text-white/70 underline"
            >
              Clear
            </button>
          </div>
        ) : (
          <span className="text-white/40">-</span>
        ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row: any) => (
        <div className="flex items-center gap-1">
          <button
            onClick={() => handleEdit(row)}
            className="p-1.5 rounded-lg hover:bg-white/10 text-white/50 hover:text-white transition-colors"
            title="Edit"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => handleOOO(row)}
            className="p-1.5 rounded-lg hover:bg-white/10 text-white/50 hover:text-yellow-400 transition-colors"
            title="Set OOO"
          >
            <ClockIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => {
              if (confirm(`Delete approver "${row.name}"?`)) {
                deleteMutation.mutate(row.approver_id);
              }
            }}
            className="p-1.5 rounded-lg hover:bg-white/10 text-white/50 hover:text-red-400 transition-colors"
            title="Delete"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Approver Management"
        subtitle="Manage who holds each approver persona for the approval workflow"
        actions={
          <button
            onClick={() => { setForm(emptyForm); setShowAddModal(true); }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-primary-500 hover:bg-primary-600 text-white transition-colors"
          >
            <PlusIcon className="h-4 w-4" />
            Add Approver
          </button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Approvers"
          value={statsData?.total ?? 0}
          icon={UserGroupIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Active"
          value={statsData?.active ?? 0}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
        <StatCard
          title="Available"
          value={statsData?.available ?? 0}
          icon={UserGroupIcon}
          iconBgColor="stat-icon-purple"
          iconColor="text-purple-400"
        />
        <StatCard
          title="Out of Office"
          value={statsData?.ooo ?? 0}
          icon={ClockIcon}
          iconBgColor="stat-icon-yellow"
          iconColor="text-yellow-400"
        />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <SearchInput
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              placeholder="Search approvers..."
            />
          </div>
          <div className="w-48">
            <Select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
              options={APPROVER_TYPE_OPTIONS}
            />
          </div>
          <div className="w-40">
            <Select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              options={STATUS_OPTIONS}
            />
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card padding="none">
        {isLoading && <LoadingState />}
        {error && <ErrorState message="Failed to load approvers" />}
        {!isLoading && !error && approversData && (
          <>
            {approversData.items.length === 0 ? (
              <EmptyState
                title="No approvers found"
                description="Add approvers to configure your approval workflow"
              />
            ) : (
              <>
                <Table columns={columns} data={approversData.items} />
                {totalPages > 1 && (
                  <div className="p-4 border-t border-white/10">
                    <Pagination
                      page={page}
                      total={approversData?.total ?? 0}
                      pageSize={limit}
                      onPageChange={setPage}
                    />
                  </div>
                )}
              </>
            )}
          </>
        )}
      </Card>

      {/* Add Modal */}
      {showAddModal && (
        <Modal
          open={showAddModal}
          title="Add Approver"
          onClose={() => setShowAddModal(false)}
        >
          <div className="space-y-4">
            <Input
              label="Approver ID"
              value={form.approver_id}
              onChange={(e) => setForm({ ...form, approver_id: e.target.value })}
              placeholder="e.g., APP-LM-001"
              required
            />
            <Input
              label="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Full name"
              required
            />
            <Input
              label="Email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="email@example.com"
            />
            <Select
              label="Approver Type"
              value={form.approver_type}
              onChange={(e) => setForm({ ...form, approver_type: e.target.value })}
              options={APPROVER_TYPE_OPTIONS.filter((o) => o.value !== '')}
            />
            <Input
              label="Department"
              value={form.department}
              onChange={(e) => setForm({ ...form, department: e.target.value })}
              placeholder="e.g., IT Security"
            />
            <Input
              label="Job Title"
              value={form.job_title}
              onChange={(e) => setForm({ ...form, job_title: e.target.value })}
              placeholder="e.g., Chief Security Officer"
            />
            <Input
              label="Process Scope"
              value={form.process_scope}
              onChange={(e) => setForm({ ...form, process_scope: e.target.value })}
              placeholder="Comma-separated: P2P, O2C, HR"
            />
            <Input
              label="System Scope"
              value={form.system_scope}
              onChange={(e) => setForm({ ...form, system_scope: e.target.value })}
              placeholder="Comma-separated: SAP_PRD, SAP_QAS"
            />
            <div className="flex justify-end gap-3 pt-4">
              <Button variant="secondary" onClick={() => setShowAddModal(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleCreate}
                disabled={!form.approver_id || !form.name || createMutation.isPending}
              >
                {createMutation.isPending ? 'Creating...' : 'Create Approver'}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Edit Modal */}
      {showEditModal && selectedApprover && (
        <Modal
          open={showEditModal}
          title={`Edit: ${selectedApprover.name}`}
          onClose={() => {
            setShowEditModal(false);
            setSelectedApprover(null);
          }}
        >
          <div className="space-y-4">
            <Input
              label="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
            <Input
              label="Email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
            <Select
              label="Approver Type"
              value={form.approver_type}
              onChange={(e) => setForm({ ...form, approver_type: e.target.value })}
              options={APPROVER_TYPE_OPTIONS.filter((o) => o.value !== '')}
            />
            <Input
              label="Department"
              value={form.department}
              onChange={(e) => setForm({ ...form, department: e.target.value })}
            />
            <Input
              label="Job Title"
              value={form.job_title}
              onChange={(e) => setForm({ ...form, job_title: e.target.value })}
            />
            <Input
              label="Process Scope"
              value={form.process_scope}
              onChange={(e) => setForm({ ...form, process_scope: e.target.value })}
              placeholder="Comma-separated"
            />
            <Input
              label="System Scope"
              value={form.system_scope}
              onChange={(e) => setForm({ ...form, system_scope: e.target.value })}
              placeholder="Comma-separated"
            />
            <div className="flex justify-end gap-3 pt-4">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowEditModal(false);
                  setSelectedApprover(null);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleUpdate}
                disabled={!form.name || updateMutation.isPending}
              >
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* OOO Modal */}
      {showOOOModal && selectedApprover && (
        <Modal
          open={showOOOModal}
          title={`Set Out-of-Office: ${selectedApprover.name}`}
          onClose={() => {
            setShowOOOModal(false);
            setSelectedApprover(null);
          }}
        >
          <div className="space-y-4">
            <Input
              label="OOO Until"
              type="datetime-local"
              value={oooUntil}
              onChange={(e) => setOooUntil(e.target.value)}
              required
            />
            <Select
              label="Delegate To (optional)"
              value={oooDelegateId}
              onChange={(e) => setOooDelegateId(e.target.value)}
              options={[
                { value: '', label: 'No delegate' },
                ...(approversData?.items || [])
                  .filter((a: any) => a.approver_id !== selectedApprover.approver_id && a.status === 'active')
                  .map((a: any) => ({
                    value: a.approver_id,
                    label: `${a.name} (${TYPE_LABELS[a.approver_type] || a.approver_type})`,
                  })),
              ]}
            />
            <Textarea
              label="Reason / Justification"
              value={oooReason}
              onChange={(e) => setOooReason(e.target.value)}
              placeholder="Why is this approver going out of office? (recorded in audit trail)"
              rows={3}
            />
            <div className="flex justify-end gap-3 pt-4">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowOOOModal(false);
                  setSelectedApprover(null);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSetOOO}
                disabled={!oooUntil || setOOOMutation.isPending}
              >
                {setOOOMutation.isPending ? 'Setting...' : 'Set OOO'}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
