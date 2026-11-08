import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  BoltIcon,
  BellAlertIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  EyeIcon,
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

type AlertSeverity = 'critical' | 'high' | 'medium' | 'low';
type AlertStatus = 'open' | 'acknowledged' | 'resolved' | 'dismissed';

interface MonitoringRule {
  id: string;
  name: string;
  module: string;
  event_type: string;
  condition_type: string;
  severity: AlertSeverity;
  is_active: boolean;
  frequency: string;
  created_at: string;
}

interface MonitoringAlert {
  id: string;
  alert_id: string;
  title: string;
  module: string;
  severity: AlertSeverity;
  status: AlertStatus;
  acknowledged_by?: string;
  resolved_by?: string;
  created_at: string;
}

interface DashboardData {
  active_rules: number;
  open_alerts: number;
  by_severity: Record<string, number>;
}

interface RuleForm {
  name: string;
  module: string;
  event_type: string;
  condition_type: string;
  severity: AlertSeverity | '';
  frequency_minutes: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_RULE_FORM: RuleForm = {
  name: '',
  module: '',
  event_type: '',
  condition_type: '',
  severity: '',
  frequency_minutes: '60',
};

const SEVERITY_VARIANT: Record<AlertSeverity, 'danger' | 'warning' | 'info' | 'success'> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'success',
};

const ALERT_STATUS_VARIANT: Record<AlertStatus, 'danger' | 'warning' | 'success' | 'neutral'> = {
  open: 'danger',
  acknowledged: 'warning',
  resolved: 'success',
  dismissed: 'neutral',
};

const SEVERITY_OPTIONS = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const MODULE_OPTIONS = [
  { value: '', label: 'Select module...' },
  { value: 'access', label: 'Access' },
  { value: 'risk', label: 'Risk' },
  { value: 'compliance', label: 'Compliance' },
  { value: 'audit', label: 'Audit' },
  { value: 'sod', label: 'SoD' },
  { value: 'config', label: 'Config' },
  { value: 'auth', label: 'Auth' },
];

const CONDITION_OPTIONS = [
  { value: '', label: 'Select condition...' },
  { value: 'threshold', label: 'Threshold' },
  { value: 'pattern', label: 'Pattern Match' },
  { value: 'anomaly', label: 'Anomaly Detection' },
  { value: 'absence', label: 'Absence Check' },
  { value: 'frequency', label: 'Frequency Exceeded' },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function ContinuousMonitoring() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<'rules' | 'alerts'>('rules');
  const [search, setSearch] = useState('');
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [ruleForm, setRuleForm] = useState<RuleForm>(EMPTY_RULE_FORM);
  const [ruleErrors, setRuleErrors] = useState<Partial<Record<keyof RuleForm, string>>>({});

  // ── Queries ──

  const { data: dashboardData } = useQuery<DashboardData>({
    queryKey: ['monitoring-dashboard'],
    queryFn: () =>
      api.get('/monitoring/dashboard').then(r => r.data ?? { active_rules: 0, open_alerts: 0, by_severity: {} }),
  });

  const dashboard: DashboardData = dashboardData ?? { active_rules: 0, open_alerts: 0, by_severity: {} };

  const { data: rulesData, isLoading: rulesLoading } = useQuery<MonitoringRule[]>({
    queryKey: ['monitoring-rules'],
    queryFn: () =>
      api.get('/monitoring/rules').then(r => r.data?.rules ?? r.data ?? []),
    enabled: tab === 'rules',
  });

  const rules: MonitoringRule[] = rulesData ?? [];

  const { data: alertsData, isLoading: alertsLoading } = useQuery<MonitoringAlert[]>({
    queryKey: ['monitoring-alerts'],
    queryFn: () =>
      api.get('/monitoring/alerts').then(r => r.data?.alerts ?? r.data ?? []),
    enabled: tab === 'alerts',
  });

  const alerts: MonitoringAlert[] = alertsData ?? [];

  // ── Filtering ──

  const filteredRules = rules.filter(r => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      r.name.toLowerCase().includes(q) ||
      r.module.toLowerCase().includes(q) ||
      r.event_type.toLowerCase().includes(q)
    );
  });

  const filteredAlerts = alerts.filter(a => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      a.alert_id.toLowerCase().includes(q) ||
      a.title.toLowerCase().includes(q) ||
      a.module.toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createRuleMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/monitoring/rules', data),
    onSuccess: () => {
      toast.success('Monitoring rule created');
      queryClient.invalidateQueries({ queryKey: ['monitoring-rules'] });
      queryClient.invalidateQueries({ queryKey: ['monitoring-dashboard'] });
      closeRuleModal();
    },
    onError: () => toast.error('Failed to create rule'),
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (id: string) => api.put(`/monitoring/alerts/${id}/acknowledge`),
    onSuccess: () => {
      toast.success('Alert acknowledged');
      queryClient.invalidateQueries({ queryKey: ['monitoring-alerts'] });
      queryClient.invalidateQueries({ queryKey: ['monitoring-dashboard'] });
    },
    onError: () => toast.error('Failed to acknowledge alert'),
  });

  const resolveMutation = useMutation({
    mutationFn: (id: string) => api.put(`/monitoring/alerts/${id}/resolve`),
    onSuccess: () => {
      toast.success('Alert resolved');
      queryClient.invalidateQueries({ queryKey: ['monitoring-alerts'] });
      queryClient.invalidateQueries({ queryKey: ['monitoring-dashboard'] });
    },
    onError: () => toast.error('Failed to resolve alert'),
  });

  // ── Handlers ──

  function closeRuleModal() {
    setShowRuleModal(false);
    setRuleForm(EMPTY_RULE_FORM);
    setRuleErrors({});
  }

  function validateRule(): boolean {
    const errors: Partial<Record<keyof RuleForm, string>> = {};
    if (!ruleForm.name.trim()) errors.name = 'Name is required';
    if (!ruleForm.module) errors.module = 'Module is required';
    if (!ruleForm.severity) errors.severity = 'Severity is required';
    setRuleErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleCreateRule() {
    if (!validateRule()) return;
    createRuleMutation.mutate({
      ...ruleForm,
      frequency_minutes: Number(ruleForm.frequency_minutes) || 60,
    });
  }

  function setRuleField<K extends keyof RuleForm>(key: K, value: RuleForm[K]) {
    setRuleForm(prev => ({ ...prev, [key]: value }));
    if (ruleErrors[key]) setRuleErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Rule Columns ──

  const ruleColumns = [
    {
      key: 'name',
      header: 'Rule Name',
      render: (r: MonitoringRule) => (
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{r.name}</div>
      ),
    },
    {
      key: 'module',
      header: 'Module',
      render: (r: MonitoringRule) => (
        <Badge variant="neutral" size="sm">{r.module}</Badge>
      ),
    },
    {
      key: 'event_type',
      header: 'Event Type',
      render: (r: MonitoringRule) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{r.event_type.replace(/_/g, ' ')}</span>
      ),
    },
    {
      key: 'condition_type',
      header: 'Condition',
      render: (r: MonitoringRule) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{r.condition_type.replace(/_/g, ' ')}</span>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (r: MonitoringRule) => (
        <Badge variant={SEVERITY_VARIANT[r.severity]} size="sm">{r.severity}</Badge>
      ),
    },
    {
      key: 'is_active',
      header: 'Active',
      render: (r: MonitoringRule) => (
        <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${r.is_active ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}`}>
          <span className={`h-2 w-2 rounded-full ${r.is_active ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'}`} />
          {r.is_active ? 'Active' : 'Inactive'}
        </span>
      ),
    },
    {
      key: 'frequency',
      header: 'Frequency',
      render: (r: MonitoringRule) => (
        <span className="text-sm text-gray-500">{r.frequency}</span>
      ),
    },
  ];

  // ── Alert Columns ──

  const alertColumns = [
    {
      key: 'alert_id',
      header: 'Alert ID',
      render: (a: MonitoringAlert) => (
        <span className="text-sm font-mono font-medium text-indigo-600 dark:text-indigo-400">
          {a.alert_id}
        </span>
      ),
    },
    {
      key: 'title',
      header: 'Title',
      render: (a: MonitoringAlert) => (
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100 max-w-xs truncate">
          {a.title}
        </div>
      ),
    },
    {
      key: 'module',
      header: 'Module',
      render: (a: MonitoringAlert) => (
        <Badge variant="neutral" size="sm">{a.module}</Badge>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (a: MonitoringAlert) => (
        <Badge variant={SEVERITY_VARIANT[a.severity]} size="sm">{a.severity}</Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (a: MonitoringAlert) => (
        <Badge variant={ALERT_STATUS_VARIANT[a.status]} dot size="sm">
          {a.status.replace(/_/g, ' ')}
        </Badge>
      ),
    },
    {
      key: 'acknowledged_by',
      header: 'Acknowledged By',
      render: (a: MonitoringAlert) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{a.acknowledged_by || '—'}</span>
      ),
    },
    {
      key: 'created_at',
      header: 'Time',
      render: (a: MonitoringAlert) => (
        <span className="text-sm text-gray-500">{new Date(a.created_at).toLocaleString()}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (a: MonitoringAlert) => (
        <div className="flex justify-end gap-1">
          {a.status === 'open' && (
            <Button
              size="sm"
              variant="ghost"
              icon={<EyeIcon className="h-4 w-4" />}
              onClick={e => { e.stopPropagation(); acknowledgeMutation.mutate(a.id); }}
            >
              Acknowledge
            </Button>
          )}
          {(a.status === 'open' || a.status === 'acknowledged') && (
            <Button
              size="sm"
              variant="ghost"
              icon={<CheckCircleIcon className="h-4 w-4" />}
              onClick={e => { e.stopPropagation(); resolveMutation.mutate(a.id); }}
            >
              Resolve
            </Button>
          )}
        </div>
      ),
    },
  ];

  const tabs = [
    { key: 'rules' as const, label: 'Rules' },
    { key: 'alerts' as const, label: 'Alerts' },
  ];

  const criticalAlerts = dashboard.by_severity?.critical ?? 0;
  const highAlerts = dashboard.by_severity?.high ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Continuous Monitoring"
        subtitle="Automated rules and real-time alerts for GRC events"
        actions={
          tab === 'rules' ? (
            <Button
              icon={<PlusIcon className="h-4 w-4" />}
              onClick={() => { setRuleForm(EMPTY_RULE_FORM); setRuleErrors({}); setShowRuleModal(true); }}
            >
              New Rule
            </Button>
          ) : undefined
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Active Rules" value={dashboard.active_rules} icon={BoltIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Open Alerts" value={dashboard.open_alerts} icon={BellAlertIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Critical Alerts" value={criticalAlerts} icon={ExclamationTriangleIcon} iconBgColor="stat-icon-red" iconColor="" />
        <StatCard title="High Alerts" value={highAlerts} icon={ShieldCheckIcon} iconBgColor="stat-icon-yellow" iconColor="" />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex -mb-px space-x-6">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => { setTab(t.key); setSearch(''); }}
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
          placeholder={tab === 'rules' ? 'Search rules...' : 'Search alerts...'}
          value={search}
          onChange={e => setSearch(e.target.value)}
          onClear={() => setSearch('')}
        />
      </Card>

      {/* Tables */}
      {tab === 'rules' && (
        <Table
          columns={ruleColumns}
          data={filteredRules}
          loading={rulesLoading}
          emptyMessage="No monitoring rules configured. Click 'New Rule' to create one."
        />
      )}

      {tab === 'alerts' && (
        <Table
          columns={alertColumns}
          data={filteredAlerts}
          loading={alertsLoading}
          emptyMessage="No alerts. All monitoring checks are passing."
        />
      )}

      {/* Create Rule Modal */}
      <Modal
        open={showRuleModal}
        onClose={closeRuleModal}
        title="New Monitoring Rule"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={closeRuleModal}>Cancel</Button>
            <Button onClick={handleCreateRule} loading={createRuleMutation.isPending}>
              Create Rule
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
                value={ruleForm.name}
                onChange={e => setRuleField('name', e.target.value)}
                error={ruleErrors.name}
                placeholder="e.g. Detect Emergency Access Requests"
              />
            </div>
            <Select
              label="Module"
              required
              value={ruleForm.module}
              onChange={e => setRuleField('module', e.target.value)}
              options={MODULE_OPTIONS}
              error={ruleErrors.module}
            />
            <Input
              label="Event Type"
              value={ruleForm.event_type}
              onChange={e => setRuleField('event_type', e.target.value)}
              placeholder="e.g. access_granted, config_changed"
            />
            <Select
              label="Condition Type"
              value={ruleForm.condition_type}
              onChange={e => setRuleField('condition_type', e.target.value)}
              options={CONDITION_OPTIONS}
            />
            <Select
              label="Severity"
              required
              value={ruleForm.severity}
              onChange={e => setRuleField('severity', e.target.value as AlertSeverity)}
              options={[{ value: '', label: 'Select severity...' }, ...SEVERITY_OPTIONS]}
              error={ruleErrors.severity}
            />
            <Input
              label="Frequency (minutes)"
              type="number"
              value={ruleForm.frequency_minutes}
              onChange={e => setRuleField('frequency_minutes', e.target.value)}
              placeholder="60"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
