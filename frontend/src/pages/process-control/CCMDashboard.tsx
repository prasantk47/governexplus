import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  PlayIcon,
  BoltIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  CpuChipIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import {
  PageHeader,
  Card,
  CardHeader,
  Button,
  Table,
  Badge,
  Modal,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import { processControlApi } from '../../services/processControlApi';

// ─── Types ────────────────────────────────────────────────────────────────────

type CCMRuleType =
  | 'threshold'
  | 'duplicate_detection'
  | 'pattern_match'
  | 'segregation'
  | 'authorization'
  | 'completeness';

type CCMFrequency = 'real_time' | 'hourly' | 'daily' | 'weekly' | 'monthly';
type CCMRunResult = 'pass' | 'fail' | 'error' | 'skipped';

interface CCMRule {
  id: string;
  rule_id: string;
  name: string;
  description: string;
  source_system: string;
  rule_type: CCMRuleType;
  frequency: CCMFrequency;
  threshold: number | null;
  auto_create_deficiency: boolean;
  is_active: boolean;
  last_run: string | null;
  last_result: CCMRunResult | null;
  last_run_findings: number;
  created_at: string;
}

interface CCMDashboardData {
  total_rules: number;
  active_rules: number;
  pass_rate: number;
  failed_last_run: number;
  recent_executions: CCMExecution[];
  findings_trend: { date: string; count: number }[];
}

interface CCMExecution {
  id: string;
  rule_id: string;
  rule_name: string;
  executed_at: string;
  result: CCMRunResult;
  findings: number;
  duration_ms: number;
}

interface CreateCCMRuleForm {
  name: string;
  description: string;
  source_system: string;
  rule_type: CCMRuleType;
  frequency: CCMFrequency;
  threshold: string;
  auto_create_deficiency: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const RULE_TYPES: CCMRuleType[] = [
  'threshold',
  'duplicate_detection',
  'pattern_match',
  'segregation',
  'authorization',
  'completeness',
];

const FREQUENCIES: CCMFrequency[] = [
  'real_time',
  'hourly',
  'daily',
  'weekly',
  'monthly',
];

const SOURCE_SYSTEMS = ['SAP ECC', 'SAP S/4HANA', 'SAP BW', 'Active Directory', 'Oracle', 'Workday', 'Other'];

const ruleTypeVariant: Record<CCMRuleType, 'info' | 'warning' | 'success' | 'danger' | 'default' | 'neutral'> = {
  threshold: 'info',
  duplicate_detection: 'warning',
  pattern_match: 'default',
  segregation: 'danger',
  authorization: 'warning',
  completeness: 'neutral',
};

const resultVariant: Record<CCMRunResult, 'success' | 'danger' | 'warning' | 'neutral'> = {
  pass: 'success',
  fail: 'danger',
  error: 'warning',
  skipped: 'neutral',
};

const frequencyVariant: Record<CCMFrequency, 'success' | 'info' | 'default' | 'warning' | 'neutral'> = {
  real_time: 'success',
  hourly: 'info',
  daily: 'default',
  weekly: 'warning',
  monthly: 'neutral',
};

const emptyForm: CreateCCMRuleForm = {
  name: '',
  description: '',
  source_system: 'SAP S/4HANA',
  rule_type: 'threshold',
  frequency: 'daily',
  threshold: '',
  auto_create_deficiency: true,
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function labelFor(val: string): string {
  return val.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function fmtDateTime(iso: string | null): string {
  if (!iso) return 'Never';
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ─── Component ────────────────────────────────────────────────────────────────

export function CCMDashboard() {
  const queryClient = useQueryClient();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [form, setForm] = useState<CreateCCMRuleForm>(emptyForm);
  const [executingRuleId, setExecutingRuleId] = useState<string | null>(null);

  // ─── Queries ──────────────────────────────────────────────────────────────

  const { data: dashboardData } = useQuery({
    queryKey: ['ccm-dashboard'],
    queryFn: () => processControlApi.getCCMDashboard().then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: rulesData, isLoading: rulesLoading } = useQuery({
    queryKey: ['ccm-rules'],
    queryFn: () => processControlApi.listCCMRules().then((r) => r.data),
    refetchInterval: 30_000,
  });

  // ─── Mutations ────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      processControlApi.createCCMRule(payload),
    onSuccess: () => {
      toast.success('CCM rule created');
      queryClient.invalidateQueries({ queryKey: ['ccm-rules'] });
      queryClient.invalidateQueries({ queryKey: ['ccm-dashboard'] });
      setShowCreateModal(false);
      setForm(emptyForm);
    },
    onError: () => toast.error('Failed to create CCM rule'),
  });

  const executeMutation = useMutation({
    mutationFn: (ruleId: string) => {
      setExecutingRuleId(ruleId);
      return processControlApi.executeCCMRule(ruleId);
    },
    onSuccess: (_, ruleId) => {
      toast.success('Rule executed successfully');
      queryClient.invalidateQueries({ queryKey: ['ccm-rules'] });
      queryClient.invalidateQueries({ queryKey: ['ccm-dashboard'] });
      if (executingRuleId === ruleId) setExecutingRuleId(null);
    },
    onError: () => {
      toast.error('Rule execution failed');
      setExecutingRuleId(null);
    },
  });

  const runAllMutation = useMutation({
    mutationFn: () => processControlApi.runAllCCM(),
    onSuccess: () => {
      toast.success('All CCM rules queued for execution');
      queryClient.invalidateQueries({ queryKey: ['ccm-rules'] });
      queryClient.invalidateQueries({ queryKey: ['ccm-dashboard'] });
    },
    onError: () => toast.error('Failed to trigger run-all'),
  });

  // ─── Data processing ──────────────────────────────────────────────────────

  const dashboard: CCMDashboardData | null = dashboardData ?? null;
  const rules: CCMRule[] = Array.isArray(rulesData) ? rulesData : (rulesData as any)?.rules ?? [];

  const totalRules = dashboard?.total_rules ?? rules.length;
  const activeRules = dashboard?.active_rules ?? rules.filter((r) => r.is_active).length;
  const passRate = dashboard?.pass_rate ?? 0;
  const failedLastRun =
    dashboard?.failed_last_run ??
    rules.filter((r) => r.last_result === 'fail').length;

  // ─── Handlers ─────────────────────────────────────────────────────────────

  function handleCreate() {
    if (!form.name) {
      toast.error('Rule name is required');
      return;
    }
    if (!form.source_system) {
      toast.error('Source system is required');
      return;
    }
    const payload: Record<string, unknown> = {
      name: form.name,
      description: form.description,
      source_system: form.source_system,
      rule_type: form.rule_type,
      frequency: form.frequency,
      auto_create_deficiency: form.auto_create_deficiency,
    };
    if (form.threshold !== '') {
      payload.threshold = parseFloat(form.threshold);
    }
    createMutation.mutate(payload);
  }

  // ─── Table columns ────────────────────────────────────────────────────────

  const columns = [
    {
      key: 'rule_id',
      header: 'Rule ID',
      render: (r: CCMRule) => (
        <span className="text-xs font-mono text-indigo-600 dark:text-indigo-400">
          {r.rule_id ?? String(r.id).slice(0, 8)}
        </span>
      ),
    },
    {
      key: 'name',
      header: 'Name',
      render: (r: CCMRule) => (
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{r.name}</p>
          {r.description && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-1">
              {r.description}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'source_system',
      header: 'Source System',
      render: (r: CCMRule) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{r.source_system}</span>
      ),
    },
    {
      key: 'rule_type',
      header: 'Rule Type',
      render: (r: CCMRule) => (
        <Badge variant={ruleTypeVariant[r.rule_type] ?? 'default'}>
          {labelFor(r.rule_type)}
        </Badge>
      ),
    },
    {
      key: 'frequency',
      header: 'Frequency',
      render: (r: CCMRule) => (
        <Badge variant={frequencyVariant[r.frequency] ?? 'default'}>
          {labelFor(r.frequency)}
        </Badge>
      ),
    },
    {
      key: 'last_run',
      header: 'Last Run',
      render: (r: CCMRule) => (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {fmtDateTime(r.last_run)}
        </span>
      ),
    },
    {
      key: 'last_result',
      header: 'Last Result',
      render: (r: CCMRule) =>
        r.last_result ? (
          <div className="flex items-center gap-2">
            <Badge variant={resultVariant[r.last_result]} dot>
              {labelFor(r.last_result)}
            </Badge>
            {r.last_run_findings > 0 && (
              <span className="text-xs font-medium text-red-600 dark:text-red-400">
                {r.last_run_findings} finding{r.last_run_findings !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        ) : (
          <span className="text-xs text-gray-400">Not run</span>
        ),
    },
    {
      key: 'actions',
      header: '',
      render: (r: CCMRule) => (
        <div className="flex items-center gap-1.5">
          {r.is_active ? (
            <Badge variant="success" size="sm" dot>
              Active
            </Badge>
          ) : (
            <Badge variant="neutral" size="sm" dot>
              Inactive
            </Badge>
          )}
          <Button
            size="sm"
            variant="ghost"
            icon={<PlayIcon className="h-3.5 w-3.5" />}
            onClick={() => executeMutation.mutate(r.id)}
            loading={executeMutation.isPending && executingRuleId === r.id}
            disabled={!r.is_active}
          >
            Execute
          </Button>
        </div>
      ),
    },
  ];

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div>
      <PageHeader
        title="Continuous Control Monitoring"
        subtitle="Automated rule execution, real-time findings, and deficiency escalation"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              icon={<ArrowPathIcon className="h-4 w-4" />}
              onClick={() => runAllMutation.mutate()}
              loading={runAllMutation.isPending}
            >
              Run All
            </Button>
            <Button
              icon={<PlusIcon className="h-4 w-4" />}
              onClick={() => setShowCreateModal(true)}
            >
              Add Rule
            </Button>
          </div>
        }
      />

      {/* Stat Cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard
          title="Total Rules"
          value={totalRules}
          icon={CpuChipIcon}
          iconBgColor="bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400"
          iconColor="text-indigo-600"
        />
        <StatCard
          title="Pass Rate"
          value={`${Math.round(passRate)}%`}
          icon={CheckCircleIcon}
          iconBgColor="bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400"
          iconColor="text-emerald-600"
        />
        <StatCard
          title="Failed Last Run"
          value={failedLastRun}
          icon={XCircleIcon}
          iconBgColor="bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400"
          iconColor="text-red-600"
        />
        <StatCard
          title="Active Rules"
          value={activeRules}
          icon={BoltIcon}
          iconBgColor="bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400"
          iconColor="text-amber-600"
        />
      </div>

      {/* Recent executions from dashboard */}
      {dashboard?.recent_executions && dashboard.recent_executions.length > 0 && (
        <Card className="mb-6">
          <CardHeader
            title="Recent Executions"
            subtitle="Last 10 rule execution results"
          />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 dark:border-slate-700">
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Rule
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Executed
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Result
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Findings
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Duration
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-slate-700/50">
                {dashboard.recent_executions.slice(0, 10).map((ex) => (
                  <tr key={ex.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/30">
                    <td className="px-3 py-2 text-gray-900 dark:text-gray-100 font-medium">
                      {ex.rule_name}
                    </td>
                    <td className="px-3 py-2 text-gray-500 dark:text-gray-400 text-xs">
                      {fmtDateTime(ex.executed_at)}
                    </td>
                    <td className="px-3 py-2">
                      <Badge variant={resultVariant[ex.result]} dot>
                        {labelFor(ex.result)}
                      </Badge>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`font-medium ${
                          ex.findings > 0
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-gray-500 dark:text-gray-400'
                        }`}
                      >
                        {ex.findings}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-500 dark:text-gray-400 text-xs">
                      {ex.duration_ms != null ? `${ex.duration_ms}ms` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Rules table */}
      <Card padding="none">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-slate-700">
          <div>
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
              CCM Rules
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {rules.length} rule{rules.length !== 1 ? 's' : ''} configured
            </p>
          </div>
          {runAllMutation.isPending && (
            <div className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400">
              <ArrowPathIcon className="h-4 w-4 animate-spin" />
              Running all rules…
            </div>
          )}
        </div>
        <Table
          columns={columns}
          data={rules}
          loading={rulesLoading}
          emptyMessage="No CCM rules configured. Add your first automated monitoring rule."
        />
      </Card>

      {/* Warning banner for failed rules */}
      {failedLastRun > 0 && (
        <div className="mt-4 flex items-start gap-3 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-800 dark:text-red-300">
              {failedLastRun} rule{failedLastRun !== 1 ? 's' : ''} failed in the last run
            </p>
            <p className="text-xs text-red-600 dark:text-red-400 mt-0.5">
              Review the findings and check whether deficiencies have been automatically raised.
              Rules with auto_create_deficiency enabled will have logged items to the Deficiency
              Tracker.
            </p>
          </div>
        </div>
      )}

      {/* Create Rule Modal */}
      <Modal
        open={showCreateModal}
        onClose={() => {
          setShowCreateModal(false);
          setForm(emptyForm);
        }}
        title="Add CCM Rule"
        subtitle="Configure an automated continuous control monitoring rule"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              loading={createMutation.isPending}
              icon={<CpuChipIcon className="h-4 w-4" />}
            >
              Create Rule
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Name */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Rule Name *
              </label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Duplicate Invoice Detection — SAP AP"
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Description */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Description
              </label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={2}
                placeholder="Describe what this rule monitors and why..."
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
              />
            </div>

            {/* Source System */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Source System *
              </label>
              <select
                value={form.source_system}
                onChange={(e) => setForm({ ...form, source_system: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {SOURCE_SYSTEMS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            {/* Rule Type */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Rule Type
              </label>
              <select
                value={form.rule_type}
                onChange={(e) =>
                  setForm({ ...form, rule_type: e.target.value as CCMRuleType })
                }
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {RULE_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {labelFor(t)}
                  </option>
                ))}
              </select>
            </div>

            {/* Frequency */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Execution Frequency
              </label>
              <select
                value={form.frequency}
                onChange={(e) =>
                  setForm({ ...form, frequency: e.target.value as CCMFrequency })
                }
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {FREQUENCIES.map((f) => (
                  <option key={f} value={f}>
                    {labelFor(f)}
                  </option>
                ))}
              </select>
            </div>

            {/* Threshold */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Threshold{' '}
                <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <input
                type="number"
                value={form.threshold}
                onChange={(e) => setForm({ ...form, threshold: e.target.value })}
                placeholder="e.g. 1000.00"
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Auto create deficiency */}
            <div className="col-span-2">
              <label className="flex items-center gap-2.5 text-sm text-gray-700 dark:text-gray-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={form.auto_create_deficiency}
                  onChange={(e) =>
                    setForm({ ...form, auto_create_deficiency: e.target.checked })
                  }
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span>
                  Automatically create a deficiency when this rule fails
                </span>
              </label>
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-500 ml-7">
                When enabled, a new deficiency will be logged to the Deficiency Tracker with
                severity &quot;control_gap&quot; for each failed execution.
              </p>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
