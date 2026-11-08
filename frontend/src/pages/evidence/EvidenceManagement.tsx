import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  DocumentTextIcon,
  FolderOpenIcon,
  ShieldCheckIcon,
  ArchiveBoxIcon,
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
  Textarea,
  SearchInput,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type EvidenceType = 'document' | 'screenshot' | 'log_extract' | 'report' | 'attestation';

interface EvidenceItem {
  id: string;
  evidence_id: string;
  title: string;
  evidence_type: EvidenceType;
  category: string;
  sensitivity: string;
  collected_by: string;
  legal_hold: boolean;
  status: string;
  created_at: string;
}

interface EvidencePackage {
  id: string;
  package_id: string;
  title: string;
  package_type: string;
  item_count: number;
  status: string;
  compiled_by: string;
  created_at: string;
}

interface EvidenceSummary {
  total_items: number;
  total_packages: number;
  by_type: Record<string, number>;
  legal_hold_count: number;
}

interface EvidenceForm {
  title: string;
  evidence_type: EvidenceType | '';
  category: string;
  content_text: string;
  source_system: string;
}

interface PackageForm {
  title: string;
  package_type: string;
  description: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_EVIDENCE_FORM: EvidenceForm = {
  title: '',
  evidence_type: '',
  category: '',
  content_text: '',
  source_system: '',
};

const EMPTY_PACKAGE_FORM: PackageForm = {
  title: '',
  package_type: '',
  description: '',
};

const TYPE_OPTIONS = [
  { value: 'document', label: 'Document' },
  { value: 'screenshot', label: 'Screenshot' },
  { value: 'log_extract', label: 'Log Extract' },
  { value: 'report', label: 'Report' },
  { value: 'attestation', label: 'Attestation' },
];

const STATUS_VARIANT: Record<string, 'success' | 'warning' | 'info' | 'danger' | 'neutral'> = {
  collected: 'info',
  verified: 'success',
  rejected: 'danger',
  archived: 'neutral',
  draft: 'neutral',
  pending: 'warning',
  compiled: 'success',
  submitted: 'info',
};

// ─── Component ────────────────────────────────────────────────────────────────

export function EvidenceManagement() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<'items' | 'packages'>('items');
  const [search, setSearch] = useState('');
  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [showPackageModal, setShowPackageModal] = useState(false);
  const [evidenceForm, setEvidenceForm] = useState<EvidenceForm>(EMPTY_EVIDENCE_FORM);
  const [packageForm, setPackageForm] = useState<PackageForm>(EMPTY_PACKAGE_FORM);
  const [evidenceErrors, setEvidenceErrors] = useState<Partial<Record<keyof EvidenceForm, string>>>({});
  const [packageErrors, setPackageErrors] = useState<Partial<Record<keyof PackageForm, string>>>({});

  // ── Queries ──

  const { data: summaryData } = useQuery<EvidenceSummary>({
    queryKey: ['evidence-summary'],
    queryFn: () =>
      api.get('/evidence/summary').then(r => r.data ?? { total_items: 0, total_packages: 0, by_type: {}, legal_hold_count: 0 }),
  });

  const summary: EvidenceSummary = summaryData ?? { total_items: 0, total_packages: 0, by_type: {}, legal_hold_count: 0 };

  const { data: itemsData, isLoading: itemsLoading } = useQuery<EvidenceItem[]>({
    queryKey: ['evidence-items'],
    queryFn: () =>
      api.get('/evidence/items').then(r => r.data?.items ?? r.data ?? []),
    enabled: tab === 'items',
  });

  const items: EvidenceItem[] = itemsData ?? [];

  const { data: packagesData, isLoading: packagesLoading } = useQuery<EvidencePackage[]>({
    queryKey: ['evidence-packages'],
    queryFn: () =>
      api.get('/evidence/packages').then(r => r.data?.packages ?? r.data ?? []),
    enabled: tab === 'packages',
  });

  const packages: EvidencePackage[] = packagesData ?? [];

  // ── Filtering ──

  const filteredItems = items.filter(i => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      i.evidence_id.toLowerCase().includes(q) ||
      i.title.toLowerCase().includes(q) ||
      i.collected_by.toLowerCase().includes(q)
    );
  });

  const filteredPackages = packages.filter(p => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      p.package_id.toLowerCase().includes(q) ||
      p.title.toLowerCase().includes(q) ||
      p.compiled_by.toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createItemMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/evidence/items', data),
    onSuccess: () => {
      toast.success('Evidence item created');
      queryClient.invalidateQueries({ queryKey: ['evidence-items'] });
      queryClient.invalidateQueries({ queryKey: ['evidence-summary'] });
      closeEvidenceModal();
    },
    onError: () => toast.error('Failed to create evidence item'),
  });

  const createPackageMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/evidence/packages', data),
    onSuccess: () => {
      toast.success('Evidence package created');
      queryClient.invalidateQueries({ queryKey: ['evidence-packages'] });
      queryClient.invalidateQueries({ queryKey: ['evidence-summary'] });
      closePackageModal();
    },
    onError: () => toast.error('Failed to create package'),
  });

  // ── Handlers ──

  function closeEvidenceModal() {
    setShowEvidenceModal(false);
    setEvidenceForm(EMPTY_EVIDENCE_FORM);
    setEvidenceErrors({});
  }

  function closePackageModal() {
    setShowPackageModal(false);
    setPackageForm(EMPTY_PACKAGE_FORM);
    setPackageErrors({});
  }

  function validateEvidence(): boolean {
    const errors: Partial<Record<keyof EvidenceForm, string>> = {};
    if (!evidenceForm.title.trim()) errors.title = 'Title is required';
    if (!evidenceForm.evidence_type) errors.evidence_type = 'Type is required';
    setEvidenceErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function validatePackage(): boolean {
    const errors: Partial<Record<keyof PackageForm, string>> = {};
    if (!packageForm.title.trim()) errors.title = 'Title is required';
    setPackageErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleCreateEvidence() {
    if (!validateEvidence()) return;
    createItemMutation.mutate({ ...evidenceForm });
  }

  function handleCreatePackage() {
    if (!validatePackage()) return;
    createPackageMutation.mutate({ ...packageForm });
  }

  function setEvidenceField<K extends keyof EvidenceForm>(key: K, value: EvidenceForm[K]) {
    setEvidenceForm(prev => ({ ...prev, [key]: value }));
    if (evidenceErrors[key]) setEvidenceErrors(prev => ({ ...prev, [key]: undefined }));
  }

  function setPackageField<K extends keyof PackageForm>(key: K, value: PackageForm[K]) {
    setPackageForm(prev => ({ ...prev, [key]: value }));
    if (packageErrors[key]) setPackageErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Item Columns ──

  const itemColumns = [
    {
      key: 'evidence_id',
      header: 'Evidence ID',
      render: (i: EvidenceItem) => (
        <span className="text-sm font-mono font-medium text-indigo-600 dark:text-indigo-400">
          {i.evidence_id}
        </span>
      ),
    },
    {
      key: 'title',
      header: 'Title',
      render: (i: EvidenceItem) => (
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100 max-w-xs truncate">
          {i.title}
        </div>
      ),
    },
    {
      key: 'evidence_type',
      header: 'Type',
      render: (i: EvidenceItem) => (
        <Badge variant="neutral" size="sm">{i.evidence_type.replace(/_/g, ' ')}</Badge>
      ),
    },
    {
      key: 'category',
      header: 'Category',
      render: (i: EvidenceItem) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{i.category || '—'}</span>
      ),
    },
    {
      key: 'sensitivity',
      header: 'Sensitivity',
      render: (i: EvidenceItem) => (
        <Badge
          variant={i.sensitivity === 'high' ? 'danger' : i.sensitivity === 'medium' ? 'warning' : 'neutral'}
          size="sm"
        >
          {i.sensitivity || '—'}
        </Badge>
      ),
    },
    {
      key: 'collected_by',
      header: 'Collected By',
      render: (i: EvidenceItem) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{i.collected_by}</span>
      ),
    },
    {
      key: 'legal_hold',
      header: 'Legal Hold',
      render: (i: EvidenceItem) =>
        i.legal_hold ? (
          <Badge variant="danger" size="sm">Hold</Badge>
        ) : (
          <span className="text-sm text-gray-400">—</span>
        ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (i: EvidenceItem) => (
        <Badge variant={STATUS_VARIANT[i.status] ?? 'neutral'} dot size="sm">
          {i.status.replace(/_/g, ' ')}
        </Badge>
      ),
    },
  ];

  // ── Package Columns ──

  const packageColumns = [
    {
      key: 'package_id',
      header: 'Package ID',
      render: (p: EvidencePackage) => (
        <span className="text-sm font-mono font-medium text-indigo-600 dark:text-indigo-400">
          {p.package_id}
        </span>
      ),
    },
    {
      key: 'title',
      header: 'Title',
      render: (p: EvidencePackage) => (
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100 max-w-xs truncate">
          {p.title}
        </div>
      ),
    },
    {
      key: 'package_type',
      header: 'Type',
      render: (p: EvidencePackage) => (
        <Badge variant="neutral" size="sm">{p.package_type.replace(/_/g, ' ')}</Badge>
      ),
    },
    {
      key: 'item_count',
      header: 'Items',
      render: (p: EvidencePackage) => (
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{p.item_count}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (p: EvidencePackage) => (
        <Badge variant={STATUS_VARIANT[p.status] ?? 'neutral'} dot size="sm">
          {p.status.replace(/_/g, ' ')}
        </Badge>
      ),
    },
    {
      key: 'compiled_by',
      header: 'Compiled By',
      render: (p: EvidencePackage) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{p.compiled_by}</span>
      ),
    },
  ];

  const tabs = [
    { key: 'items' as const, label: 'Evidence Items' },
    { key: 'packages' as const, label: 'Packages' },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Evidence Management"
        subtitle="Collect, organize, and package audit and compliance evidence"
        actions={
          <div className="flex gap-2">
            <Button
              variant="secondary"
              icon={<FolderOpenIcon className="h-4 w-4" />}
              onClick={() => { setPackageForm(EMPTY_PACKAGE_FORM); setPackageErrors({}); setShowPackageModal(true); }}
            >
              New Package
            </Button>
            <Button
              icon={<PlusIcon className="h-4 w-4" />}
              onClick={() => { setEvidenceForm(EMPTY_EVIDENCE_FORM); setEvidenceErrors({}); setShowEvidenceModal(true); }}
            >
              Add Evidence
            </Button>
          </div>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Items" value={summary.total_items} icon={DocumentTextIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Packages" value={summary.total_packages} icon={FolderOpenIcon} iconBgColor="stat-icon-indigo" iconColor="" />
        <StatCard title="Legal Holds" value={summary.legal_hold_count} icon={ShieldCheckIcon} iconBgColor="stat-icon-red" iconColor="" />
        <StatCard title="Archived" value={0} icon={ArchiveBoxIcon} iconBgColor="stat-icon-gray" iconColor="" />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex -mb-px space-x-6">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t.key
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Search */}
      <Card padding="md">
        <SearchInput
          placeholder={tab === 'items' ? 'Search evidence items...' : 'Search packages...'}
          value={search}
          onChange={e => setSearch(e.target.value)}
          onClear={() => setSearch('')}
        />
      </Card>

      {/* Tables */}
      {tab === 'items' && (
        <Table
          columns={itemColumns}
          data={filteredItems}
          loading={itemsLoading}
          emptyMessage="No evidence items found. Click 'Add Evidence' to collect one."
        />
      )}

      {tab === 'packages' && (
        <Table
          columns={packageColumns}
          data={filteredPackages}
          loading={packagesLoading}
          emptyMessage="No evidence packages found. Click 'New Package' to create one."
        />
      )}

      {/* Create Evidence Modal */}
      <Modal
        open={showEvidenceModal}
        onClose={closeEvidenceModal}
        title="Add Evidence Item"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={closeEvidenceModal}>Cancel</Button>
            <Button onClick={handleCreateEvidence} loading={createItemMutation.isPending}>
              Add Evidence
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Title"
                required
                value={evidenceForm.title}
                onChange={e => setEvidenceField('title', e.target.value)}
                error={evidenceErrors.title}
                placeholder="Evidence title"
              />
            </div>
            <Select
              label="Evidence Type"
              required
              value={evidenceForm.evidence_type}
              onChange={e => setEvidenceField('evidence_type', e.target.value as EvidenceType)}
              options={[{ value: '', label: 'Select type...' }, ...TYPE_OPTIONS]}
              error={evidenceErrors.evidence_type}
            />
            <Input
              label="Category"
              value={evidenceForm.category}
              onChange={e => setEvidenceField('category', e.target.value)}
              placeholder="e.g. Financial, IT, HR"
            />
            <Input
              label="Source System"
              value={evidenceForm.source_system}
              onChange={e => setEvidenceField('source_system', e.target.value)}
              placeholder="e.g. SAP ECC, ServiceNow"
            />
          </div>
          <Textarea
            label="Content"
            value={evidenceForm.content_text}
            onChange={e => setEvidenceField('content_text', e.target.value)}
            rows={4}
            placeholder="Evidence content or description..."
          />
        </div>
      </Modal>

      {/* Create Package Modal */}
      <Modal
        open={showPackageModal}
        onClose={closePackageModal}
        title="New Evidence Package"
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={closePackageModal}>Cancel</Button>
            <Button onClick={handleCreatePackage} loading={createPackageMutation.isPending}>
              Create Package
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input
            label="Package Title"
            required
            value={packageForm.title}
            onChange={e => setPackageField('title', e.target.value)}
            error={packageErrors.title}
            placeholder="e.g. Q4 2026 SOX Evidence Package"
          />
          <Input
            label="Package Type"
            value={packageForm.package_type}
            onChange={e => setPackageField('package_type', e.target.value)}
            placeholder="e.g. audit, compliance, regulatory"
          />
          <Textarea
            label="Description"
            value={packageForm.description}
            onChange={e => setPackageField('description', e.target.value)}
            rows={3}
            placeholder="Describe the purpose of this evidence package..."
          />
        </div>
      </Modal>
    </div>
  );
}
