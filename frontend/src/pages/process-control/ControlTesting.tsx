import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  ClipboardDocumentCheckIcon,
  BeakerIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import {
  PageHeader,
  Card,
  Button,
  Table,
  Badge,
  Modal,
} from '../../components/ui';
import { processControlApi } from '../../services/processControlApi';

// ─── Types ────────────────────────────────────────────────────────────────────

type TestType = 'design' | 'operating_effectiveness' | 'walkthrough';
type TestResult = 'effective' | 'ineffective' | 'partially_effective' | '';
type TestStatus = 'planned' | 'in_progress' | 'completed' | 'cancelled';

interface Control {
  id: string;
  control_id: string;
  name: string;
}

interface ControlTest {
  id: string;
  test_id: string;
  control_id: string;
  control_name: string;
  test_type: TestType;
  period: string;
  tester: string;
  sample_size: number;
  population_size: number;
  result: TestResult;
  exceptions: number;
  conclusion: string;
  status: TestStatus;
  created_at: string;
  evidence_ids: string[];
}

interface CreateTestForm {
  control_id: string;
  test_type: TestType;
  period: string;
  sample_size: number;
  population_size: number;
  tester: string;
}

interface RecordResultForm {
  result: TestResult;
  exceptions: number;
  conclusion: string;
  evidence_ids: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const TEST_TYPES: TestType[] = ['design', 'operating_effectiveness', 'walkthrough'];
const TEST_RESULTS: Exclude<TestResult, ''>[] = ['effective', 'ineffective', 'partially_effective'];
const TEST_STATUSES: TestStatus[] = ['planned', 'in_progress', 'completed', 'cancelled'];

const resultVariant: Record<string, 'success' | 'danger' | 'warning' | 'default'> = {
  effective: 'success',
  ineffective: 'danger',
  partially_effective: 'warning',
};

const statusVariant: Record<string, 'info' | 'warning' | 'success' | 'neutral' | 'danger' | 'default'> = {
  planned: 'info',
  in_progress: 'warning',
  completed: 'success',
  cancelled: 'neutral',
};

const testTypeVariant: Record<string, 'info' | 'success' | 'warning' | 'default'> = {
  design: 'info',
  operating_effectiveness: 'success',
  walkthrough: 'warning',
};

const emptyCreateForm: CreateTestForm = {
  control_id: '',
  test_type: 'operating_effectiveness',
  period: '',
  sample_size: 25,
  population_size: 100,
  tester: '',
};

const emptyResultForm: RecordResultForm = {
  result: '',
  exceptions: 0,
  conclusion: '',
  evidence_ids: '',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function labelFor(val: string): string {
  return val.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ControlTesting() {
  const queryClient = useQueryClient();

  // Filters
  const [search, setSearch] = useState('');
  const [filterControl, setFilterControl] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterResult, setFilterResult] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showResultModal, setShowResultModal] = useState<ControlTest | null>(null);

  // Forms
  const [createForm, setCreateForm] = useState<CreateTestForm>(emptyCreateForm);
  const [resultForm, setResultForm] = useState<RecordResultForm>(emptyResultForm);

  // ─── Queries ──────────────────────────────────────────────────────────────

  const { data: controlsData } = useQuery({
    queryKey: ['controls-list-for-testing'],
    queryFn: () => processControlApi.listControls().then((r) => r.data),
  });

  // We fetch tests for each selected control, or a global list when no filter
  const { data: testsData, isLoading } = useQuery({
    queryKey: ['control-tests-all', filterControl, filterType, filterResult, filterStatus],
    queryFn: async () => {
      if (filterControl) {
        const r = await processControlApi.getControlTests(filterControl);
        return r.data;
      }
      // Fall back: fetch tests for all controls (aggregate)
      const controls: Control[] = Array.isArray(controlsData)
        ? controlsData
        : (controlsData as any)?.controls ?? [];
      if (controls.length === 0) return [];
      const results = await Promise.all(
        controls.slice(0, 50).map((c) =>
          processControlApi.getControlTests(c.id).then((r) => r.data).catch(() => [])
        )
      );
      return results.flat();
    },
    enabled: !filterControl || !!filterControl,
  });

  // ─── Mutations ────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      processControlApi.createTest(createForm.control_id, payload),
    onSuccess: () => {
      toast.success('Test created successfully');
      queryClient.invalidateQueries({ queryKey: ['control-tests-all'] });
      setShowCreateModal(false);
      setCreateForm(emptyCreateForm);
    },
    onError: () => toast.error('Failed to create test'),
  });

  const recordResultMutation = useMutation({
    mutationFn: ({ testId, payload }: { testId: string; payload: Record<string, unknown> }) =>
      processControlApi.recordTestResult(testId, payload),
    onSuccess: () => {
      toast.success('Test result recorded');
      queryClient.invalidateQueries({ queryKey: ['control-tests-all'] });
      setShowResultModal(null);
      setResultForm(emptyResultForm);
    },
    onError: () => toast.error('Failed to record result'),
  });

  // ─── Data processing ──────────────────────────────────────────────────────

  const controls: Control[] = Array.isArray(controlsData)
    ? controlsData
    : (controlsData as any)?.controls ?? [];

  const allTests: ControlTest[] = Array.isArray(testsData) ? testsData : [];

  const filteredTests = allTests.filter((t) => {
    const matchSearch =
      !search ||
      t.test_id?.toLowerCase().includes(search.toLowerCase()) ||
      t.control_name?.toLowerCase().includes(search.toLowerCase()) ||
      t.tester?.toLowerCase().includes(search.toLowerCase());
    const matchType = !filterType || t.test_type === filterType;
    const matchResult = !filterResult || t.result === filterResult;
    const matchStatus = !filterStatus || t.status === filterStatus;
    return matchSearch && matchType && matchResult && matchStatus;
  });

  // ─── Handlers ─────────────────────────────────────────────────────────────

  function handleCreate() {
    if (!createForm.control_id) {
      toast.error('Please select a control');
      return;
    }
    if (!createForm.period) {
      toast.error('Please enter a testing period');
      return;
    }
    const payload = {
      test_type: createForm.test_type,
      period: createForm.period,
      sample_size: createForm.sample_size,
      population_size: createForm.population_size,
      tester: createForm.tester,
    };
    createMutation.mutate(payload as Record<string, unknown>);
  }

  function handleRecordResult() {
    if (!showResultModal) return;
    if (!resultForm.result) {
      toast.error('Please select a result');
      return;
    }
    const payload = {
      result: resultForm.result,
      exceptions: resultForm.exceptions,
      conclusion: resultForm.conclusion,
      evidence_ids: resultForm.evidence_ids
        ? resultForm.evidence_ids.split(',').map((s) => s.trim()).filter(Boolean)
        : [],
    };
    recordResultMutation.mutate({ testId: showResultModal.id, payload: payload as Record<string, unknown> });
  }

  function openRecordResult(test: ControlTest) {
    setShowResultModal(test);
    setResultForm({
      result: test.result || '',
      exceptions: test.exceptions ?? 0,
      conclusion: test.conclusion ?? '',
      evidence_ids: (test.evidence_ids ?? []).join(', '),
    });
  }

  // ─── Table columns ────────────────────────────────────────────────────────

  const columns = [
    {
      key: 'test_id',
      header: 'Test ID',
      render: (t: ControlTest) => (
        <span className="text-xs font-mono text-indigo-600 dark:text-indigo-400">
          {t.test_id ?? t.id.slice(0, 8)}
        </span>
      ),
    },
    {
      key: 'control_name',
      header: 'Control',
      render: (t: ControlTest) => (
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {t.control_name ?? t.control_id}
        </span>
      ),
    },
    {
      key: 'test_type',
      header: 'Type',
      render: (t: ControlTest) => (
        <Badge variant={testTypeVariant[t.test_type] ?? 'default'}>
          {labelFor(t.test_type)}
        </Badge>
      ),
    },
    {
      key: 'period',
      header: 'Period',
      render: (t: ControlTest) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">{t.period ?? '—'}</span>
      ),
    },
    {
      key: 'tester',
      header: 'Tester',
      render: (t: ControlTest) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{t.tester ?? '—'}</span>
      ),
    },
    {
      key: 'sample',
      header: 'Sample / Pop.',
      render: (t: ControlTest) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {t.sample_size ?? '—'} / {t.population_size ?? '—'}
        </span>
      ),
    },
    {
      key: 'result',
      header: 'Result',
      render: (t: ControlTest) =>
        t.result ? (
          <Badge variant={resultVariant[t.result] ?? 'default'} dot>
            {labelFor(t.result)}
          </Badge>
        ) : (
          <span className="text-xs text-gray-400">Pending</span>
        ),
    },
    {
      key: 'exceptions',
      header: 'Exceptions',
      render: (t: ControlTest) => (
        <span
          className={`text-sm font-medium ${
            (t.exceptions ?? 0) > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-600 dark:text-gray-400'
          }`}
        >
          {t.exceptions ?? 0}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (t: ControlTest) => (
        <Badge variant={statusVariant[t.status] ?? 'default'} dot>
          {labelFor(t.status)}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (t: ControlTest) => (
        <Button
          size="sm"
          variant="ghost"
          icon={<ClipboardDocumentCheckIcon className="h-4 w-4" />}
          onClick={() => openRecordResult(t)}
          disabled={t.status === 'cancelled'}
        >
          Record Result
        </Button>
      ),
    },
  ];

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div>
      <PageHeader
        title="Control Testing"
        subtitle="Design and operating effectiveness tests, walkthroughs, and results"
        actions={
          <Button
            icon={<PlusIcon className="h-4 w-4" />}
            onClick={() => setShowCreateModal(true)}
          >
            New Test
          </Button>
        }
      />

      {/* Filters */}
      <Card className="mb-6">
        <div className="flex flex-wrap gap-3 items-center">
          <FunnelIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />

          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <MagnifyingGlassIcon className="h-4 w-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by test ID, control, tester..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-4 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Control filter */}
          <select
            value={filterControl}
            onChange={(e) => setFilterControl(e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Controls</option>
            {controls.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          {/* Test type filter */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Types</option>
            {TEST_TYPES.map((t) => (
              <option key={t} value={t}>
                {labelFor(t)}
              </option>
            ))}
          </select>

          {/* Result filter */}
          <select
            value={filterResult}
            onChange={(e) => setFilterResult(e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Results</option>
            {TEST_RESULTS.map((r) => (
              <option key={r} value={r}>
                {labelFor(r)}
              </option>
            ))}
          </select>

          {/* Status filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Statuses</option>
            {TEST_STATUSES.map((s) => (
              <option key={s} value={s}>
                {labelFor(s)}
              </option>
            ))}
          </select>
        </div>
      </Card>

      {/* Tests table */}
      <Card padding="none">
        <Table
          columns={columns}
          data={filteredTests}
          loading={isLoading}
          emptyMessage="No tests found. Create your first control test to get started."
        />
      </Card>

      {/* Create Test Modal */}
      <Modal
        open={showCreateModal}
        onClose={() => {
          setShowCreateModal(false);
          setCreateForm(emptyCreateForm);
        }}
        title="Create Control Test"
        subtitle="Define a new testing procedure for a control"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              loading={createMutation.isPending}
              icon={<BeakerIcon className="h-4 w-4" />}
            >
              Create Test
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Control */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Control *
              </label>
              <select
                value={createForm.control_id}
                onChange={(e) => setCreateForm({ ...createForm, control_id: e.target.value })}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select a control…</option>
                {controls.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Test Type */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Test Type
              </label>
              <select
                value={createForm.test_type}
                onChange={(e) =>
                  setCreateForm({ ...createForm, test_type: e.target.value as TestType })
                }
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {TEST_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {labelFor(t)}
                  </option>
                ))}
              </select>
            </div>

            {/* Period */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Testing Period *
              </label>
              <input
                type="text"
                value={createForm.period}
                onChange={(e) => setCreateForm({ ...createForm, period: e.target.value })}
                placeholder="e.g. Q3 2026, Jan 2026"
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Sample size */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Sample Size
              </label>
              <input
                type="number"
                min={1}
                value={createForm.sample_size}
                onChange={(e) =>
                  setCreateForm({ ...createForm, sample_size: parseInt(e.target.value, 10) || 1 })
                }
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Population size */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Population Size
              </label>
              <input
                type="number"
                min={1}
                value={createForm.population_size}
                onChange={(e) =>
                  setCreateForm({ ...createForm, population_size: parseInt(e.target.value, 10) || 1 })
                }
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Tester */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Tester
              </label>
              <input
                type="text"
                value={createForm.tester}
                onChange={(e) => setCreateForm({ ...createForm, tester: e.target.value })}
                placeholder="Tester name or user ID"
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
        </div>
      </Modal>

      {/* Record Result Modal */}
      <Modal
        open={!!showResultModal}
        onClose={() => {
          setShowResultModal(null);
          setResultForm(emptyResultForm);
        }}
        title="Record Test Result"
        subtitle={
          showResultModal
            ? `Test ${showResultModal.test_id ?? showResultModal.id.slice(0, 8)} · ${showResultModal.test_type ? labelFor(showResultModal.test_type) : ''}`
            : undefined
        }
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowResultModal(null)}>
              Cancel
            </Button>
            <Button
              onClick={handleRecordResult}
              loading={recordResultMutation.isPending}
              icon={<CheckCircleIcon className="h-4 w-4" />}
            >
              Save Result
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {/* Result */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Result *
            </label>
            <select
              value={resultForm.result}
              onChange={(e) => setResultForm({ ...resultForm, result: e.target.value as TestResult })}
              className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Select a result…</option>
              {TEST_RESULTS.map((r) => (
                <option key={r} value={r}>
                  {labelFor(r)}
                </option>
              ))}
            </select>
          </div>

          {/* Exceptions */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Number of Exceptions
            </label>
            <input
              type="number"
              min={0}
              value={resultForm.exceptions}
              onChange={(e) =>
                setResultForm({ ...resultForm, exceptions: parseInt(e.target.value, 10) || 0 })
              }
              className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Conclusion */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Conclusion / Notes
            </label>
            <textarea
              value={resultForm.conclusion}
              onChange={(e) => setResultForm({ ...resultForm, conclusion: e.target.value })}
              rows={4}
              placeholder="Summarize findings, exceptions, and auditor conclusions..."
              className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
          </div>

          {/* Evidence IDs */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Evidence IDs (comma-separated)
            </label>
            <input
              type="text"
              value={resultForm.evidence_ids}
              onChange={(e) => setResultForm({ ...resultForm, evidence_ids: e.target.value })}
              placeholder="e.g. EVD-001, EVD-002"
              className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {resultForm.result === 'ineffective' && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <ExclamationCircleIcon className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-700 dark:text-red-400">
                An ineffective result will automatically trigger a deficiency recommendation. Ensure
                your conclusion documents the root cause and corrective action required.
              </p>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
