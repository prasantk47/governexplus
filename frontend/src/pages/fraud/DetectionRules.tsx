import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
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

type RuleType = 'velocity' | 'threshold' | 'pattern' | 'anomaly';

interface FraudRule {
  id: string;
  rule_name: string;
  rule_type: RuleType;
  description: string;
  risk_score: number;
  is_active: boolean;
  trigger_count: number;
  last_triggered_at?: string;
  conditions?: string;
  created_at?: string;
}

interface RuleForm {
  rule_name: string;
  rule_type: RuleType | '';
  description: string;
  risk_score: number;
  conditions: string;
  is_active: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_FORM: RuleForm = {
  rule_name: '',
  rule_type: '',
  description: '',
  risk_score: 50,
  conditions: '{}',
  is_active: true,
};

const RULE_TYPE_VARIANT: Record<RuleType, 'info' | 'warning' | 'neutral' | 'danger'> = {
  velocity: 'info',
  threshold: 'warning',
  pattern: 'neutral',
  anomaly: 'danger',
};

const RULE_TYPE_OPTIONS: { value: RuleType; label: string }[] = [
  { value: 'velocity', label: 'Velocity' },
  { value: 'threshold', label: 'Threshold' },
  { value: 'pattern', label: 'Pattern' },
  { value: 'anomaly', label: 'Anomaly' },
];

function riskScoreVariant(score: number): 'success' | 'warning' | 'danger' {
  if (score < 40) return 'success';
  if (score < 70) return 'warning';
  return 'danger';
}

// ─── Component ────────────────────────────────────────────────────────────────

export function DetectionRules() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState<FraudRule | null>(null);
  const [form, setForm] = useState<RuleForm>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof RuleForm, string>>>({});

  // ── Queries ──

  const { data: rulesData, isLoading } = useQuery<FraudRule[]>({
    queryKey: ['fraud-rules', typeFilter],
    queryFn: () =>
      api
        .get('/fraud/rules', { params: typeFilter ? { rule_type: typeFilter } : {} })
        .then(r => r.data?.rules ?? r.data ?? []),
  });

  const rules: FraudRule[] = rulesData ?? [];

  const filtered = rules.filter(r => {
    if (!search) return true;
    const q = search.toLowerCase();
    return r.rule_name.toLowerCase().includes(q) || r.description.toLowerCase().includes(q);
  });

  // ── Mutations ──

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/fraud/rules', data),
    onSuccess: () => {
      toast.success('Detection rule created');
      queryClient.invalidateQueries({ queryKey: ['fraud-rules'] });
      closeModal();
    },
    onError: () => toast.error('Failed to create rule'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      api.put(`/fraud/rules/${id}`, data),
    onSuccess: () => {
      toast.success('Rule updated');
      queryClient.invalidateQueries({ queryKey: ['fraud-rules'] });
      closeModal();
    },
    onError: () => toast.error('Failed to update rule'),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/fraud/rules/${id}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fraud-rules'] }),
    onError: () => toast.error('Failed to toggle rule'),
  });

  // ── Handlers ──

  function openCreate() {
    setEditingRule(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
    setShowModal(true);
  }

  function openEdit(rule: FraudRule) {
    setEditingRule(rule);
    setForm({
      rule_name: rule.rule_name,
      rule_type: rule.rule_type,
      description: rule.description ?? '',
      risk_score: rule.risk_score,
      conditions: rule.conditions ?? '{}',
      is_active: rule.is_active,
    });
    setFormErrors({});
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setEditingRule(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
  }

  function validate(): boolean {
    const errors: Partial<Record<keyof RuleForm, string>> = {};
    if (!form.rule_name.trim()) errors.rule_name = 'Rule name is required';
    if (!form.rule_type) errors.rule_type = 'Rule type is required';
    if (form.risk_score < 1 || form.risk_score > 100) errors.risk_score = 'Must be 1–100';
    try {
      JSON.parse(form.conditions);
    } catch {
      errors.conditions = 'Conditions must be valid JSON';
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
    const payload = { ...form, conditions: JSON.parse(form.conditions) };
    if (editingRule) {
      updateMutation.mutate({ id: editingRule.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  }

  function setField<K extends keyof RuleForm>(key: K, value: RuleForm[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Columns ──

  const columns = [
    {
      key: 'rule_name',
      header: 'Rule Name',
      render: (r: FraudRule) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{r.rule_name}</div>
          <div className="text-xs text-gray-400 truncate max-w-xs">{r.description}</div>
        </div>
      ),
    },
    {
      key: 'rule_type',
      header: 'Type',
      render: (r: FraudRule) => (
        <Badge variant={RULE_TYPE_VARIANT[r.rule_type]} size="sm">
          {r.rule_type}
        </Badge>
      ),
    },
    {
      key: 'risk_score',
      header: 'Risk Score',
      render: (r: FraudRule) => (
        <Badge variant={riskScoreVariant(r.risk_score)} size="sm">
          {r.risk_score}
        </Badge>
      ),
    },
    {
      key: 'is_active',
      header: 'Active',
      render: (r: FraudRule) => (
        <button
          onClick={e => {
            e.stopPropagation();
            toggleMutation.mutate({ id: r.id, is_active: !r.is_active });
          }}
          className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none ${
            r.is_active ? 'bg-indigo-600' : 'bg-gray-200 dark:bg-slate-600'
          }`}
        >
          <span
            className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ${
              r.is_active ? 'translate-x-4' : 'translate-x-0'
            }`}
          />
        </button>
      ),
    },
    {
      key: 'trigger_count',
      header: 'Triggers',
      render: (r: FraudRule) => (
        <span className="text-sm font-mono text-gray-600 dark:text-gray-400">{r.trigger_count ?? 0}</span>
      ),
    },
    {
      key: 'last_triggered',
      header: 'Last Triggered',
      render: (r: FraudRule) => (
        <span className="text-sm text-gray-500">
          {r.last_triggered_at ? new Date(r.last_triggered_at).toLocaleDateString() : '—'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (r: FraudRule) => (
        <Button size="sm" variant="ghost" onClick={e => { e.stopPropagation(); openEdit(r); }}>
          Edit
        </Button>
      ),
    },
  ];

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Detection Rules"
        subtitle="Configure fraud detection rules, thresholds, and triggers"
        actions={
          <Button icon={<PlusIcon className="h-4 w-4" />} onClick={openCreate}>
            Create Rule
          </Button>
        }
      />

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search rules..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
            options={[{ value: '', label: 'All Types' }, ...RULE_TYPE_OPTIONS]}
          />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        onRowClick={r => openEdit(r)}
        emptyMessage="No detection rules configured. Click 'Create Rule' to add your first rule."
      />

      {/* Modal */}
      <Modal
        open={showModal}
        onClose={closeModal}
        title={editingRule ? 'Edit Detection Rule' : 'Create Detection Rule'}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={closeModal}>Cancel</Button>
            <Button
              onClick={handleSubmit}
              loading={isSaving}
              icon={<ShieldExclamationIcon className="h-4 w-4" />}
            >
              {editingRule ? 'Save Changes' : 'Create Rule'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Rule Name"
                required
                value={form.rule_name}
                onChange={e => setField('rule_name', e.target.value)}
                error={formErrors.rule_name}
                placeholder="e.g. High Frequency Transactions"
              />
            </div>
            <Select
              label="Rule Type"
              required
              value={form.rule_type}
              onChange={e => setField('rule_type', e.target.value as RuleType)}
              options={[{ value: '', label: 'Select type...' }, ...RULE_TYPE_OPTIONS]}
              error={formErrors.rule_type}
            />
            <Input
              label="Risk Score (1–100)"
              type="number"
              value={String(form.risk_score)}
              onChange={e => setField('risk_score', Number(e.target.value))}
              error={formErrors.risk_score}
            />
          </div>
          <Textarea
            label="Description"
            value={form.description}
            onChange={e => setField('description', e.target.value)}
            rows={2}
            placeholder="Describe what this rule detects..."
          />
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Conditions (JSON)
            </label>
            <textarea
              value={form.conditions}
              onChange={e => setField('conditions', e.target.value)}
              rows={5}
              className="w-full text-sm font-mono border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
              placeholder={'{\n  "threshold": 10,\n  "window_minutes": 60\n}'}
            />
            {formErrors.conditions && (
              <p className="text-xs text-red-500 mt-1">{formErrors.conditions}</p>
            )}
          </div>
          <label className="flex items-center gap-3 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={e => setField('is_active', e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">Rule is active</span>
          </label>
        </div>
      </Modal>
    </div>
  );
}
