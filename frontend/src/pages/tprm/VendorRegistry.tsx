import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  BuildingOffice2Icon,
  ExclamationTriangleIcon,
  CalendarDaysIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  Table,
  Modal,
  Input,
  Select,
  SearchInput,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type VendorTier = '1' | '2' | '3';
type VendorStatus = 'active' | 'inactive' | 'under_review' | 'suspended' | 'offboarded';

interface Vendor {
  id: string;
  vendor_name: string;
  vendor_code: string;
  tier: VendorTier;
  status: VendorStatus;
  country: string;
  risk_score: number;
  last_assessment_date?: string;
  next_assessment_date?: string;
  contract_expiry?: string;
  created_at?: string;
}

interface VendorForm {
  vendor_name: string;
  vendor_code: string;
  tier: VendorTier | '';
  status: VendorStatus;
  country: string;
  contract_expiry: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_FORM: VendorForm = {
  vendor_name: '',
  vendor_code: '',
  tier: '',
  status: 'active',
  country: '',
  contract_expiry: '',
};

const TIER_VARIANT: Record<VendorTier, 'danger' | 'warning' | 'neutral'> = {
  '1': 'danger',
  '2': 'warning',
  '3': 'neutral',
};

const TIER_LABEL: Record<VendorTier, string> = {
  '1': 'Tier 1 — Critical',
  '2': 'Tier 2 — Important',
  '3': 'Tier 3 — Standard',
};

const STATUS_VARIANT: Record<VendorStatus, 'success' | 'warning' | 'info' | 'danger' | 'neutral'> = {
  active: 'success',
  inactive: 'neutral',
  under_review: 'warning',
  suspended: 'danger',
  offboarded: 'neutral',
};

const TIER_OPTIONS = [
  { value: '1', label: 'Tier 1 — Critical' },
  { value: '2', label: 'Tier 2 — Important' },
  { value: '3', label: 'Tier 3 — Standard' },
];

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'suspended', label: 'Suspended' },
  { value: 'offboarded', label: 'Offboarded' },
];

// ─── Risk Score Meter ─────────────────────────────────────────────────────────

function RiskMeter({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  const color =
    pct >= 75 ? 'bg-red-500' : pct >= 50 ? 'bg-orange-400' : pct >= 25 ? 'bg-yellow-400' : 'bg-green-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-1.5 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{score}</span>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function VendorRegistry() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [tierFilter, setTierFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null);
  const [form, setForm] = useState<VendorForm>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof VendorForm, string>>>({});

  // ── Queries ──

  const { data: vendorsData, isLoading } = useQuery<Vendor[]>({
    queryKey: ['tprm-vendors', tierFilter, statusFilter],
    queryFn: () =>
      api
        .get('/tprm/vendors', {
          params: {
            ...(tierFilter ? { tier: tierFilter } : {}),
            ...(statusFilter ? { status: statusFilter } : {}),
          },
        })
        .then(r => r.data?.vendors ?? r.data ?? []),
  });

  const vendors: Vendor[] = vendorsData ?? [];

  const filtered = vendors.filter(v => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      v.vendor_name.toLowerCase().includes(q) ||
      v.vendor_code.toLowerCase().includes(q) ||
      v.country.toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/tprm/vendors', data),
    onSuccess: () => {
      toast.success('Vendor added successfully');
      queryClient.invalidateQueries({ queryKey: ['tprm-vendors'] });
      closeModal();
    },
    onError: () => toast.error('Failed to add vendor'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      api.put(`/tprm/vendors/${id}`, data),
    onSuccess: () => {
      toast.success('Vendor updated successfully');
      queryClient.invalidateQueries({ queryKey: ['tprm-vendors'] });
      closeModal();
    },
    onError: () => toast.error('Failed to update vendor'),
  });

  // ── Handlers ──

  function openCreate() {
    setEditingVendor(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
    setShowModal(true);
  }

  function openEdit(vendor: Vendor) {
    setEditingVendor(vendor);
    setForm({
      vendor_name: vendor.vendor_name,
      vendor_code: vendor.vendor_code,
      tier: vendor.tier,
      status: vendor.status,
      country: vendor.country,
      contract_expiry: vendor.contract_expiry ?? '',
    });
    setFormErrors({});
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setEditingVendor(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
  }

  function validate(): boolean {
    const errors: Partial<Record<keyof VendorForm, string>> = {};
    if (!form.vendor_name.trim()) errors.vendor_name = 'Vendor name is required';
    if (!form.tier) errors.tier = 'Tier is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
    if (editingVendor) {
      updateMutation.mutate({ id: editingVendor.id, data: form });
    } else {
      createMutation.mutate(form);
    }
  }

  function setField<K extends keyof VendorForm>(key: K, value: VendorForm[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Stats ──

  const totalCount = vendors.length;
  const highRiskCount = vendors.filter(v => v.tier === '1').length;
  const today = new Date().toISOString().slice(0, 10);
  const overdueCount = vendors.filter(
    v => v.next_assessment_date && v.next_assessment_date < today
  ).length;
  const expiringCount = vendors.filter(v => {
    if (!v.contract_expiry) return false;
    const diff = new Date(v.contract_expiry).getTime() - Date.now();
    return diff > 0 && diff < 90 * 24 * 60 * 60 * 1000;
  }).length;

  // ── Columns ──

  const columns = [
    {
      key: 'vendor',
      header: 'Vendor',
      render: (v: Vendor) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{v.vendor_name}</div>
          <div className="text-xs text-gray-400 font-mono">{v.vendor_code}</div>
        </div>
      ),
    },
    {
      key: 'tier',
      header: 'Tier',
      render: (v: Vendor) => (
        <Badge variant={TIER_VARIANT[v.tier]} size="sm">
          Tier {v.tier}
        </Badge>
      ),
    },
    {
      key: 'country',
      header: 'Country',
      render: (v: Vendor) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{v.country || '—'}</span>
      ),
    },
    {
      key: 'risk_score',
      header: 'Risk Score',
      render: (v: Vendor) => <RiskMeter score={v.risk_score ?? 0} />,
    },
    {
      key: 'last_assessment',
      header: 'Last Assessment',
      render: (v: Vendor) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {v.last_assessment_date
            ? new Date(v.last_assessment_date).toLocaleDateString()
            : '—'}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (v: Vendor) => (
        <Badge variant={STATUS_VARIANT[v.status]} dot size="sm">
          {v.status.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (v: Vendor) => (
        <Button size="sm" variant="ghost" onClick={e => { e.stopPropagation(); openEdit(v); }}>
          Edit
        </Button>
      ),
    },
  ];

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vendor Registry"
        subtitle="Manage third-party vendors, tiers, and risk assessments"
        actions={
          <Button icon={<PlusIcon className="h-4 w-4" />} onClick={openCreate}>
            Add Vendor
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Vendors" value={totalCount} icon={BuildingOffice2Icon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="High Risk (Tier 1)" value={highRiskCount} icon={ShieldExclamationIcon} iconBgColor="stat-icon-red" iconColor="" />
        <StatCard title="Assessments Overdue" value={overdueCount} icon={ExclamationTriangleIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Contracts Expiring (90d)" value={expiringCount} icon={CalendarDaysIcon} iconBgColor="stat-icon-yellow" iconColor="" />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by vendor name, code, or country..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={tierFilter}
            onChange={e => setTierFilter(e.target.value)}
            options={[{ value: '', label: 'All Tiers' }, ...TIER_OPTIONS]}
          />
          <Select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            options={[{ value: '', label: 'All Statuses' }, ...STATUS_OPTIONS]}
          />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        onRowClick={v => openEdit(v)}
        emptyMessage="No vendors found. Click 'Add Vendor' to register your first third party."
      />

      {/* Create / Edit Modal */}
      <Modal
        open={showModal}
        onClose={closeModal}
        title={editingVendor ? 'Edit Vendor' : 'Add Vendor'}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={closeModal}>Cancel</Button>
            <Button onClick={handleSubmit} loading={isSaving}>
              {editingVendor ? 'Save Changes' : 'Add Vendor'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Vendor Name"
                required
                value={form.vendor_name}
                onChange={e => setField('vendor_name', e.target.value)}
                error={formErrors.vendor_name}
                placeholder="e.g. Acme Software Ltd"
              />
            </div>
            <Input
              label="Vendor Code"
              value={form.vendor_code}
              onChange={e => setField('vendor_code', e.target.value)}
              placeholder="e.g. ACME-001"
            />
            <Select
              label="Tier"
              required
              value={form.tier}
              onChange={e => setField('tier', e.target.value as VendorTier)}
              options={[{ value: '', label: 'Select tier...' }, ...TIER_OPTIONS]}
              error={formErrors.tier}
            />
            <Select
              label="Status"
              value={form.status}
              onChange={e => setField('status', e.target.value as VendorStatus)}
              options={STATUS_OPTIONS}
            />
            <Input
              label="Country"
              value={form.country}
              onChange={e => setField('country', e.target.value)}
              placeholder="e.g. Germany"
            />
            <Input
              label="Contract Expiry"
              type="date"
              value={form.contract_expiry}
              onChange={e => setField('contract_expiry', e.target.value)}
            />
          </div>
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
            <p className="text-xs text-blue-700 dark:text-blue-400">
              <strong>Tier Guide:</strong> {Object.values(TIER_LABEL).join(' | ')}
            </p>
          </div>
        </div>
      </Modal>
    </div>
  );
}
