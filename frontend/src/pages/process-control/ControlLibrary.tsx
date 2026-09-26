import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
  StarIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarSolidIcon } from '@heroicons/react/24/solid';
import {
  PageHeader,
  Card,
  Button,
  Table,
  Badge,
  Modal,
} from '../../components/ui';
import { processControlApi } from '../../services/processControlApi';

interface Control {
  id: string;
  control_id: string;
  name: string;
  description: string;
  control_type: string;
  control_nature: string;
  frequency: string;
  process_name: string;
  owner: string;
  status: string;
  is_key_control: boolean;
  framework_mappings: string[];
  risk_ids: string[];
  automation_level: string;
}

interface ControlFormData {
  name: string;
  description: string;
  control_type: string;
  control_nature: string;
  frequency: string;
  process_name: string;
  owner: string;
  is_key_control: boolean;
  framework_mappings: string;
  automation_level: string;
  risk_ids: string;
}

const controlTypeVariant: Record<string, 'info' | 'warning' | 'success' | 'default'> = {
  preventive: 'success',
  detective: 'info',
  corrective: 'warning',
  directive: 'default',
};

const controlNatureVariant: Record<string, 'info' | 'warning' | 'success' | 'default'> = {
  manual: 'warning',
  automated: 'success',
  semi_automated: 'info',
};

const statusVariant: Record<string, 'success' | 'warning' | 'neutral' | 'danger' | 'default'> = {
  active: 'success',
  inactive: 'neutral',
  draft: 'warning',
  retired: 'danger',
};

const FRAMEWORKS = ['SOX', 'ISO27001', 'GDPR', 'PCI-DSS', 'NIST', 'COSO', 'COBIT'];
const CONTROL_TYPES = ['preventive', 'detective', 'corrective', 'directive'];
const CONTROL_NATURES = ['manual', 'automated', 'semi_automated'];
const FREQUENCIES = ['daily', 'weekly', 'monthly', 'quarterly', 'annually', 'continuous'];
const AUTOMATION_LEVELS = ['fully_automated', 'partially_automated', 'manual'];

const emptyForm: ControlFormData = {
  name: '',
  description: '',
  control_type: 'preventive',
  control_nature: 'manual',
  frequency: 'monthly',
  process_name: '',
  owner: '',
  is_key_control: false,
  framework_mappings: '',
  automation_level: 'manual',
  risk_ids: '',
};

export function ControlLibrary() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterNature, setFilterNature] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterProcess, setFilterProcess] = useState('');
  const [filterKeyControl, setFilterKeyControl] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editControl, setEditControl] = useState<Control | null>(null);
  const [viewControl, setViewControl] = useState<Control | null>(null);
  const [form, setForm] = useState<ControlFormData>(emptyForm);

  const { data, isLoading } = useQuery({
    queryKey: ['controls', filterType, filterNature, filterStatus, filterProcess],
    queryFn: () =>
      processControlApi
        .listControls({
          control_type: filterType || undefined,
          control_nature: filterNature || undefined,
          status: filterStatus || undefined,
          process_name: filterProcess || undefined,
        })
        .then((r) => r.data),
  });

  const { data: viewTests } = useQuery({
    queryKey: ['control-tests', viewControl?.id],
    queryFn: () =>
      processControlApi.getControlTests(viewControl!.id).then((r) => r.data),
    enabled: !!viewControl,
  });

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      processControlApi.createControl(payload),
    onSuccess: () => {
      toast.success('Control created');
      queryClient.invalidateQueries({ queryKey: ['controls'] });
      setShowModal(false);
      setForm(emptyForm);
    },
    onError: () => toast.error('Failed to create control'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) =>
      processControlApi.updateControl(id, payload),
    onSuccess: () => {
      toast.success('Control updated');
      queryClient.invalidateQueries({ queryKey: ['controls'] });
      setShowModal(false);
      setEditControl(null);
      setForm(emptyForm);
    },
    onError: () => toast.error('Failed to update control'),
  });

  const retireMutation = useMutation({
    mutationFn: (id: string) => processControlApi.retireControl(id),
    onSuccess: () => {
      toast.success('Control retired');
      queryClient.invalidateQueries({ queryKey: ['controls'] });
    },
    onError: () => toast.error('Failed to retire control'),
  });

  const controls: Control[] = Array.isArray(data)
    ? data
    : (data as any)?.controls ?? [];

  const filtered = controls.filter((c) => {
    const matchSearch =
      !search ||
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.control_id?.toLowerCase().includes(search.toLowerCase()) ||
      c.process_name?.toLowerCase().includes(search.toLowerCase());
    const matchKey = !filterKeyControl || c.is_key_control;
    return matchSearch && matchKey;
  });

  function openCreate() {
    setEditControl(null);
    setForm(emptyForm);
    setShowModal(true);
  }

  function openEdit(c: Control) {
    setEditControl(c);
    setForm({
      name: c.name,
      description: c.description ?? '',
      control_type: c.control_type,
      control_nature: c.control_nature,
      frequency: c.frequency,
      process_name: c.process_name ?? '',
      owner: c.owner ?? '',
      is_key_control: c.is_key_control,
      framework_mappings: (c.framework_mappings ?? []).join(', '),
      automation_level: c.automation_level ?? 'manual',
      risk_ids: (c.risk_ids ?? []).join(', '),
    });
    setShowModal(true);
  }

  function handleSubmit() {
    const payload = {
      ...form,
      framework_mappings: form.framework_mappings
        ? form.framework_mappings.split(',').map((s) => s.trim()).filter(Boolean)
        : [],
      risk_ids: form.risk_ids
        ? form.risk_ids.split(',').map((s) => s.trim()).filter(Boolean)
        : [],
    };
    if (editControl) {
      updateMutation.mutate({ id: editControl.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  }

  const columns = [
    {
      key: 'control_id',
      header: 'Control ID',
      render: (c: Control) => (
        <span className="text-xs font-mono text-indigo-600 dark:text-indigo-400">
          {c.control_id ?? c.id.slice(0, 8)}
        </span>
      ),
    },
    {
      key: 'name',
      header: 'Name',
      render: (c: Control) => (
        <div className="flex items-center gap-2">
          {c.is_key_control && (
            <StarSolidIcon className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" title="Key Control" />
          )}
          <button
            onClick={() => setViewControl(c)}
            className="text-sm font-medium text-gray-900 dark:text-gray-100 hover:text-indigo-600 dark:hover:text-indigo-400 text-left"
          >
            {c.name}
          </button>
        </div>
      ),
    },
    {
      key: 'control_type',
      header: 'Type',
      render: (c: Control) => (
        <Badge variant={controlTypeVariant[c.control_type] ?? 'default'}>
          {c.control_type?.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'control_nature',
      header: 'Nature',
      render: (c: Control) => (
        <Badge variant={controlNatureVariant[c.control_nature] ?? 'default'}>
          {c.control_nature?.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'frequency',
      header: 'Frequency',
      render: (c: Control) => (
        <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">
          {c.frequency}
        </span>
      ),
    },
    {
      key: 'process_name',
      header: 'Process',
      render: (c: Control) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{c.process_name}</span>
      ),
    },
    {
      key: 'owner',
      header: 'Owner',
      render: (c: Control) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{c.owner}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (c: Control) => (
        <Badge variant={statusVariant[c.status] ?? 'default'} dot>
          {c.status}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (c: Control) => (
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={() => openEdit(c)}>
            Edit
          </Button>
          {c.status !== 'retired' && (
            <Button
              size="sm"
              variant="ghost"
              className="text-red-600 hover:text-red-700"
              onClick={() => retireMutation.mutate(c.id)}
              loading={retireMutation.isPending}
            >
              Retire
            </Button>
          )}
        </div>
      ),
    },
  ];

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div>
      <PageHeader
        title="Control Library"
        subtitle="Manage process controls, testing schedules, and effectiveness"
        actions={
          <Button icon={<PlusIcon className="h-4 w-4" />} onClick={openCreate}>
            Add Control
          </Button>
        }
      />

      {/* Filters */}
      <Card className="mb-6">
        <div className="flex flex-wrap gap-3 items-center">
          <FunnelIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
          <div className="relative flex-1 min-w-[200px]">
            <MagnifyingGlassIcon className="h-4 w-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search controls..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-4 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Types</option>
            {CONTROL_TYPES.map((t) => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
          <select
            value={filterNature}
            onChange={(e) => setFilterNature(e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Natures</option>
            {CONTROL_NATURES.map((n) => (
              <option key={n} value={n}>{n.replace('_', ' ')}</option>
            ))}
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Statuses</option>
            {['active', 'inactive', 'draft', 'retired'].map((s) => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Filter by process..."
            value={filterProcess}
            onChange={(e) => setFilterProcess(e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[160px]"
          />
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={filterKeyControl}
              onChange={(e) => setFilterKeyControl(e.target.checked)}
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <StarIcon className="h-3.5 w-3.5 text-amber-400" />
            Key Controls Only
          </label>
        </div>
      </Card>

      <Card padding="none">
        <Table
          columns={columns}
          data={filtered}
          loading={isLoading}
          emptyMessage="No controls found. Add your first control to get started."
        />
      </Card>

      {/* Create / Edit Modal */}
      <Modal
        open={showModal}
        onClose={() => { setShowModal(false); setEditControl(null); setForm(emptyForm); }}
        title={editControl ? 'Edit Control' : 'Add Control'}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button onClick={handleSubmit} loading={isSaving}>
              {editControl ? 'Save Changes' : 'Create Control'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Control Name *
              </label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="e.g. AP Invoice Approval"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Description
              </label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={3}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                placeholder="Describe the control objective and procedure..."
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Control Type
              </label>
              <select
                value={form.control_type}
                onChange={(e) => setForm({ ...form, control_type: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {CONTROL_TYPES.map((t) => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Control Nature
              </label>
              <select
                value={form.control_nature}
                onChange={(e) => setForm({ ...form, control_nature: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {CONTROL_NATURES.map((n) => (
                  <option key={n} value={n}>{n.replace('_', ' ')}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Frequency
              </label>
              <select
                value={form.frequency}
                onChange={(e) => setForm({ ...form, frequency: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {FREQUENCIES.map((f) => (
                  <option key={f} value={f}>{f.charAt(0).toUpperCase() + f.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Automation Level
              </label>
              <select
                value={form.automation_level}
                onChange={(e) => setForm({ ...form, automation_level: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {AUTOMATION_LEVELS.map((a) => (
                  <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Process Name
              </label>
              <input
                type="text"
                value={form.process_name}
                onChange={(e) => setForm({ ...form, process_name: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="e.g. Accounts Payable"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Control Owner
              </label>
              <input
                type="text"
                value={form.owner}
                onChange={(e) => setForm({ ...form, owner: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Owner name or user ID"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Framework Mappings (comma-separated)
              </label>
              <input
                type="text"
                value={form.framework_mappings}
                onChange={(e) => setForm({ ...form, framework_mappings: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder={`e.g. ${FRAMEWORKS.slice(0, 3).join(', ')}`}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Linked Risk IDs (comma-separated)
              </label>
              <input
                type="text"
                value={form.risk_ids}
                onChange={(e) => setForm({ ...form, risk_ids: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="e.g. RISK-001, RISK-002"
              />
            </div>
            <div className="col-span-2">
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_key_control}
                  onChange={(e) => setForm({ ...form, is_key_control: e.target.checked })}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <StarIcon className="h-4 w-4 text-amber-400" />
                Mark as Key Control
              </label>
            </div>
          </div>
        </div>
      </Modal>

      {/* Detail Side Panel */}
      {viewControl && (
        <div className="fixed inset-y-0 right-0 w-[480px] bg-white dark:bg-slate-900 border-l border-gray-200 dark:border-slate-700 shadow-2xl z-40 overflow-y-auto">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700">
            <div>
              <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                {viewControl.name}
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {viewControl.control_id ?? viewControl.id.slice(0, 8)} · {viewControl.process_name}
              </p>
            </div>
            <button
              onClick={() => setViewControl(null)}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
            >
              <XMarkIcon className="h-5 w-5 text-gray-400" />
            </button>
          </div>
          <div className="p-6 space-y-6">
            {/* Meta */}
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">Type</span>
                <Badge variant={controlTypeVariant[viewControl.control_type] ?? 'default'}>
                  {viewControl.control_type}
                </Badge>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">Nature</span>
                <Badge variant={controlNatureVariant[viewControl.control_nature] ?? 'default'}>
                  {viewControl.control_nature?.replace('_', ' ')}
                </Badge>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">Frequency</span>
                <span className="text-gray-900 dark:text-gray-100 capitalize">{viewControl.frequency}</span>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">Owner</span>
                <span className="text-gray-900 dark:text-gray-100">{viewControl.owner}</span>
              </div>
            </div>

            {viewControl.description && (
              <div>
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide block mb-2">
                  Description
                </span>
                <p className="text-sm text-gray-700 dark:text-gray-300">{viewControl.description}</p>
              </div>
            )}

            {viewControl.framework_mappings?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide block mb-2">
                  Framework Mappings
                </span>
                <div className="flex flex-wrap gap-2">
                  {viewControl.framework_mappings.map((f) => (
                    <Badge key={f} variant="info">{f}</Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Tests */}
            <div>
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide block mb-2">
                Recent Tests
              </span>
              {Array.isArray(viewTests) && viewTests.length > 0 ? (
                <div className="space-y-2">
                  {viewTests.slice(0, 5).map((t: any) => (
                    <div
                      key={t.id}
                      className="flex items-center justify-between bg-gray-50 dark:bg-slate-800 rounded-lg px-3 py-2"
                    >
                      <div>
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                          {t.test_type ?? 'Test'}
                        </span>
                        <span className="text-xs text-gray-400 ml-2">{t.period}</span>
                      </div>
                      <Badge
                        variant={
                          t.result === 'effective'
                            ? 'success'
                            : t.result === 'ineffective'
                            ? 'danger'
                            : 'warning'
                        }
                      >
                        {t.result ?? 'Pending'}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400 dark:text-gray-500">No tests recorded yet.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
