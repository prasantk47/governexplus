import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../../services/api';
import {
  MagnifyingGlassIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  UserIcon,
  DocumentMagnifyingGlassIcon,
  LightBulbIcon,
  ShieldExclamationIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ArrowPathIcon,
  ListBulletIcon,
  UsersIcon,
  ClipboardDocumentListIcon,
} from '@heroicons/react/24/outline';
import {
  Badge,
  Button,
  Card,
  PageHeader,
  LoadingState,
} from '../../components/ui';

// ============================================================================
// Types
// ============================================================================

interface DiagnoseRequest {
  user_id: string;
  transaction_code: string;
  system: string;
}

interface DiagnosticStep {
  step: number;
  label: string;
  detail: string;
  status: 'pass' | 'fail' | 'warning' | 'info';
}

interface DiagnoseResult {
  user_id: string;
  transaction_code: string;
  system: string;
  access_status: 'access_granted' | 'access_denied' | 'partial_access';
  root_cause: string;
  confidence: number;
  estimated_fix_time: string;
  diagnostic_chain: DiagnosticStep[];
  recommended_fix: string;
  risk_impact: string;
  diagnosed_at: string;
}

interface CommonTransaction {
  code: string;
  description: string;
  module: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
}

interface HistoryEntry {
  id: string;
  user_id: string;
  transaction_code: string;
  system: string;
  access_status: 'access_granted' | 'access_denied' | 'partial_access';
  diagnosed_at: string;
}

interface BatchEntry {
  user_id: string;
}

// ============================================================================
// Systems constant
// ============================================================================

const SYSTEMS = [
  'SAP ECC PRD',
  'SAP ECC QA',
  'SAP ECC DEV',
  'SAP S/4HANA PRD',
  'SAP S/4HANA QA',
  'SAP S/4HANA DEV',
  'SAP BW/4HANA',
  'GovernexPlus',
  'Active Directory',
  'Azure AD',
];

// ============================================================================
// Helpers
// ============================================================================

const statusConfig: Record<
  DiagnoseResult['access_status'],
  { label: string; variant: 'success' | 'danger' | 'warning'; color: string }
> = {
  access_granted: { label: 'Access Granted', variant: 'success', color: 'text-emerald-700' },
  access_denied: { label: 'Access Denied', variant: 'danger', color: 'text-red-700' },
  partial_access: { label: 'Partial Access', variant: 'warning', color: 'text-amber-700' },
};

const stepStatusIcon = (status: DiagnosticStep['status']) => {
  switch (status) {
    case 'pass':
      return <CheckCircleIcon className="h-5 w-5 text-emerald-500 flex-shrink-0" />;
    case 'fail':
      return <XCircleIcon className="h-5 w-5 text-red-500 flex-shrink-0" />;
    case 'warning':
      return <ExclamationTriangleIcon className="h-5 w-5 text-amber-500 flex-shrink-0" />;
    default:
      return <ClipboardDocumentListIcon className="h-5 w-5 text-blue-400 flex-shrink-0" />;
  }
};

const riskLevelVariant = (level: CommonTransaction['risk_level']) => {
  const map: Record<string, 'success' | 'warning' | 'danger'> = {
    low: 'success',
    medium: 'warning',
    high: 'danger',
    critical: 'danger',
  };
  return map[level] ?? 'default';
};

const accessStatusHistoryVariant = (
  s: HistoryEntry['access_status']
): 'success' | 'danger' | 'warning' => {
  if (s === 'access_granted') return 'success';
  if (s === 'access_denied') return 'danger';
  return 'warning';
};

const accessStatusHistoryLabel = (s: HistoryEntry['access_status']): string => {
  if (s === 'access_granted') return 'Granted';
  if (s === 'access_denied') return 'Denied';
  return 'Partial';
};

function formatDate(iso: string) {
  return new Date(iso || new Date()).toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ============================================================================
// Sub-components
// ============================================================================

function ConfidenceBar({ value }: { value: number }) {
  const color =
    value >= 85 ? 'bg-emerald-500' : value >= 60 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-gray-200 rounded-full h-2.5">
        <div
          className={`${color} h-2.5 rounded-full transition-all duration-500`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-sm font-semibold text-gray-700 w-10 text-right">{value}%</span>
    </div>
  );
}

function DiagnosticStepRow({ step }: { step: DiagnosticStep }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left"
        onClick={() => setExpanded((v) => !v)}
      >
        {stepStatusIcon(step.status)}
        <span className="text-xs text-gray-400 font-mono w-6 flex-shrink-0">
          {String(step.step).padStart(2, '0')}
        </span>
        <span className="flex-1 text-sm font-medium text-gray-800">{step.label}</span>
        {expanded ? (
          <ChevronDownIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRightIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
        )}
      </button>
      {expanded && (
        <div className="px-12 pb-3 text-sm text-gray-600">{step.detail}</div>
      )}
    </div>
  );
}

function ResultPanel({ result }: { result: DiagnoseResult }) {
  const cfg = statusConfig[result.access_status];
  return (
    <div className="space-y-5">
      {/* Status + meta */}
      <div className="flex flex-wrap items-start gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex-1 min-w-[200px]">
          <p className="text-xs text-gray-500 mb-1">Access Status</p>
          <Badge variant={cfg.variant} size="md">
            {cfg.label}
          </Badge>
        </div>
        <div className="flex-1 min-w-[160px]">
          <p className="text-xs text-gray-500 mb-1">Estimated Fix Time</p>
          <div className="flex items-center gap-1.5 text-sm font-medium text-gray-800">
            <ClockIcon className="h-4 w-4 text-gray-400" />
            {result.estimated_fix_time}
          </div>
        </div>
        <div className="flex-1 min-w-[200px]">
          <p className="text-xs text-gray-500 mb-2">Confidence</p>
          <ConfidenceBar value={result.confidence} />
        </div>
      </div>

      {/* Root cause */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
          <DocumentMagnifyingGlassIcon className="h-4 w-4 text-gray-400" />
          Root Cause
        </h3>
        <p className="text-sm text-gray-600 leading-relaxed bg-red-50 border border-red-100 rounded-lg p-4">
          {result.root_cause}
        </p>
      </div>

      {/* Diagnostic chain */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
          <ListBulletIcon className="h-4 w-4 text-gray-400" />
          Diagnostic Chain
        </h3>
        <div className="space-y-2">
          {(result.diagnostic_chain ?? []).map((step) => (
            <DiagnosticStepRow key={step.step} step={step} />
          ))}
        </div>
      </div>

      {/* Recommended fix */}
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
        <h3 className="text-sm font-semibold text-emerald-800 mb-1 flex items-center gap-2">
          <LightBulbIcon className="h-4 w-4" />
          Recommended Fix
        </h3>
        <p className="text-sm text-emerald-700">{result.recommended_fix}</p>
      </div>

      {/* Risk impact */}
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
        <h3 className="text-sm font-semibold text-blue-800 mb-1 flex items-center gap-2">
          <ShieldExclamationIcon className="h-4 w-4" />
          Risk Impact if Fix Applied
        </h3>
        <p className="text-sm text-blue-700">{result.risk_impact}</p>
      </div>
    </div>
  );
}

// ============================================================================
// Main component
// ============================================================================

export function AccessTroubleshooter() {
  const [form, setForm] = useState<DiagnoseRequest>({
    user_id: '',
    transaction_code: '',
    system: 'SAP ECC PRD',
  });
  const [activeTab, setActiveTab] = useState<'single' | 'batch'>('single');
  const [batchUsers, setBatchUsers] = useState('');
  const [expandedHistory, setExpandedHistory] = useState(false);

  // Common transactions
  const { data: transactionsData } = useQuery<CommonTransaction[]>({
    queryKey: ['troubleshooter-transactions'],
    queryFn: () =>
      api.get('/troubleshooter/transactions').then((r) => r.data),
  });
  const transactions: CommonTransaction[] = Array.isArray(transactionsData)
    ? transactionsData
    : Array.isArray((transactionsData as any)?.transactions)
      ? (transactionsData as any).transactions
      : [];

  // History
  const { data: historyData } = useQuery<HistoryEntry[]>({
    queryKey: ['troubleshooter-history'],
    queryFn: () =>
      api.get('/troubleshooter/history').then((r) => r.data),
  });
  const history: HistoryEntry[] = Array.isArray(historyData)
    ? historyData
    : Array.isArray((historyData as any)?.records)
      ? (historyData as any).records
      : [];

  // Single diagnose
  const {
    mutate: diagnose,
    isPending,
    data: result,
    reset: resetResult,
  } = useMutation<DiagnoseResult, Error, DiagnoseRequest>({
    mutationFn: (payload) =>
      api.post('/troubleshooter/diagnose', payload).then((r) => r.data),
  });

  // Batch diagnose
  const {
    mutate: diagnoseBatch,
    isPending: isBatchPending,
    data: batchResults,
  } = useMutation<DiagnoseResult[], Error, { users: BatchEntry[]; transaction_code: string; system: string }>({
    mutationFn: (payload) =>
      api.post('/troubleshooter/diagnose/batch', payload).then((r) => r.data),
  });

  const handleDiagnose = () => {
    if (!form.user_id.trim() || !form.transaction_code.trim()) return;
    diagnose(form);
  };

  const handleBatchDiagnose = () => {
    const users = batchUsers
      .split(/[\n,;]+/)
      .map((u) => u.trim())
      .filter(Boolean)
      .map((u) => ({ user_id: u }));
    if (!users.length || !form.transaction_code.trim()) return;
    diagnoseBatch({ users, transaction_code: form.transaction_code, system: form.system });
  };

  const handleTransactionClick = (code: string) => {
    setForm((f) => ({ ...f, transaction_code: code }));
    resetResult();
  };

  const displayResult: DiagnoseResult | null = result ?? null;

  const tabs = [
    { id: 'single' as const, label: 'Single User' },
    { id: 'batch' as const, label: 'Batch Mode' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Access Troubleshooter"
        subtitle="AI-powered diagnostic trace for access issues — enter a user, transaction, and system to get an instant root-cause analysis."
      />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left column: form + quick access */}
        <div className="xl:col-span-1 space-y-5">
          {/* Input form */}
          <Card>
            <div className="px-4 py-3 border-b border-gray-200">
              <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
                {tabs.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setActiveTab(t.id)}
                    className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      activeTab === t.id
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4 space-y-4">
              {/* System */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  System
                </label>
                <select
                  value={form.system}
                  onChange={(e) => setForm((f) => ({ ...f, system: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
                >
                  {SYSTEMS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              {/* Transaction code */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Transaction Code
                </label>
                <input
                  type="text"
                  value={form.transaction_code}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      transaction_code: e.target.value.toUpperCase(),
                    }))
                  }
                  placeholder="e.g. FB60"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>

              {/* Single or batch user input */}
              {activeTab === 'single' ? (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    User ID
                  </label>
                  <div className="relative">
                    <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input
                      type="text"
                      value={form.user_id}
                      onChange={(e) =>
                        setForm((f) => ({
                          ...f,
                          user_id: e.target.value.toUpperCase(),
                        }))
                      }
                      placeholder="e.g. JSMITH"
                      className="w-full pl-9 border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    User IDs{' '}
                    <span className="text-gray-400 font-normal">(one per line, or comma-separated)</span>
                  </label>
                  <textarea
                    value={batchUsers}
                    onChange={(e) => setBatchUsers(e.target.value)}
                    rows={5}
                    placeholder={'JSMITH\nAMUELLER\nTLOPES'}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                  />
                </div>
              )}

              {activeTab === 'single' ? (
                <Button
                  fullWidth
                  icon={<MagnifyingGlassIcon className="h-4 w-4" />}
                  loading={isPending}
                  onClick={handleDiagnose}
                  disabled={!form.user_id.trim() || !form.transaction_code.trim()}
                >
                  {isPending ? 'Diagnosing...' : 'Diagnose Access'}
                </Button>
              ) : (
                <Button
                  fullWidth
                  icon={<UsersIcon className="h-4 w-4" />}
                  loading={isBatchPending}
                  onClick={handleBatchDiagnose}
                  disabled={!batchUsers.trim() || !form.transaction_code.trim()}
                >
                  {isBatchPending ? 'Running batch...' : 'Run Batch Diagnosis'}
                </Button>
              )}
            </div>
          </Card>

          {/* Quick access — common transactions */}
          <Card>
            <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-2">
              <ListBulletIcon className="h-4 w-4 text-gray-400" />
              <h3 className="text-sm font-medium text-gray-800">Common Transactions</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {transactions.slice(0, 8).map((tx) => (
                <button
                  key={tx.code}
                  onClick={() => handleTransactionClick(tx.code)}
                  className={`w-full flex items-center justify-between px-4 py-2.5 hover:bg-gray-50 transition-colors text-left ${
                    form.transaction_code === tx.code ? 'bg-indigo-50' : ''
                  }`}
                >
                  <div>
                    <span className="text-sm font-mono font-medium text-gray-900">
                      {tx.code}
                    </span>
                    <span className="ml-2 text-xs text-gray-500">{tx.description}</span>
                  </div>
                  <Badge variant={riskLevelVariant(tx.risk_level)} size="sm">
                    {tx.risk_level}
                  </Badge>
                </button>
              ))}
            </div>
          </Card>

          {/* History */}
          <Card>
            <button
              onClick={() => setExpandedHistory((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-3 border-b border-gray-200 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <ClockIcon className="h-4 w-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-800">Recent Diagnoses</span>
                <Badge variant="default" size="sm">
                  {history.length}
                </Badge>
              </div>
              {expandedHistory ? (
                <ChevronDownIcon className="h-4 w-4 text-gray-400" />
              ) : (
                <ChevronRightIcon className="h-4 w-4 text-gray-400" />
              )}
            </button>
            {expandedHistory && (
              <div className="divide-y divide-gray-100">
                {history.map((entry) => (
                  <button
                    key={entry.id}
                    onClick={() =>
                      setForm({
                        user_id: entry.user_id,
                        transaction_code: entry.transaction_code,
                        system: entry.system,
                      })
                    }
                    className="w-full flex items-start justify-between px-4 py-3 hover:bg-gray-50 transition-colors text-left gap-3"
                  >
                    <div>
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className="text-sm font-mono font-medium text-gray-900">
                          {entry.user_id}
                        </span>
                        <span className="text-gray-400 text-xs">/</span>
                        <span className="text-sm font-mono text-gray-700">
                          {entry.transaction_code}
                        </span>
                      </div>
                      <p className="text-xs text-gray-400">{entry.system}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {formatDate(entry.diagnosed_at)}
                      </p>
                    </div>
                    <Badge
                      variant={accessStatusHistoryVariant(entry.access_status)}
                      size="sm"
                    >
                      {accessStatusHistoryLabel(entry.access_status)}
                    </Badge>
                  </button>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Right column: results */}
        <div className="xl:col-span-2">
          {activeTab === 'single' && (
            <>
              {isPending && (
                <Card className="p-12">
                  <LoadingState message="Running diagnostic trace..." />
                </Card>
              )}

              {!isPending && displayResult && (
                <Card>
                  <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <DocumentMagnifyingGlassIcon className="h-5 w-5 text-indigo-500" />
                      <span className="text-sm font-semibold text-gray-800">
                        Diagnostic Result
                      </span>
                      <span className="text-xs text-gray-400">
                        {displayResult.user_id} / {displayResult.transaction_code} /{' '}
                        {displayResult.system}
                      </span>
                    </div>
                    <button
                      onClick={() => {
                        resetResult();
                        setForm((f) => ({ ...f, user_id: '', transaction_code: '' }));
                      }}
                      className="p-1 text-gray-400 hover:text-gray-600 rounded"
                      title="Clear result"
                    >
                      <ArrowPathIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="p-5">
                    <ResultPanel result={displayResult} />
                  </div>
                </Card>
              )}

              {!isPending && !displayResult && (
                <Card className="flex flex-col items-center justify-center p-16 text-center">
                  <DocumentMagnifyingGlassIcon className="h-16 w-16 text-gray-200 mb-4" />
                  <h3 className="text-base font-medium text-gray-700 mb-2">
                    No diagnosis yet
                  </h3>
                  <p className="text-sm text-gray-400 max-w-xs">
                    Enter a user ID and transaction code, then click Diagnose Access to get a
                    full AI-powered root-cause analysis.
                  </p>
                </Card>
              )}
            </>
          )}

          {activeTab === 'batch' && (
            <>
              {isBatchPending && (
                <Card className="p-12">
                  <LoadingState message="Running batch diagnosis..." />
                </Card>
              )}

              {!isBatchPending && batchResults && batchResults.length > 0 && (
                <Card>
                  <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-2">
                    <UsersIcon className="h-5 w-5 text-indigo-500" />
                    <span className="text-sm font-semibold text-gray-800">
                      Batch Results — {batchResults.length} users
                    </span>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {batchResults.map((r, idx) => {
                      const cfg = statusConfig[r.access_status];
                      return (
                        <div key={idx} className="px-4 py-3 flex items-start gap-4">
                          <div className="min-w-[90px]">
                            <p className="text-sm font-mono font-semibold text-gray-900">
                              {r.user_id}
                            </p>
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant={cfg.variant} size="sm">
                                {cfg.label}
                              </Badge>
                              <span className="text-xs text-gray-500">
                                Confidence {r.confidence}%
                              </span>
                            </div>
                            <p className="text-xs text-gray-600 line-clamp-2">{r.root_cause}</p>
                          </div>
                          <div className="text-xs text-gray-400 whitespace-nowrap">
                            {r.estimated_fix_time}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              )}

              {!isBatchPending && !batchResults && (
                <Card className="flex flex-col items-center justify-center p-16 text-center">
                  <UsersIcon className="h-16 w-16 text-gray-200 mb-4" />
                  <h3 className="text-base font-medium text-gray-700 mb-2">
                    Batch mode
                  </h3>
                  <p className="text-sm text-gray-400 max-w-xs">
                    Paste a list of user IDs to diagnose them all against the same transaction
                    and system simultaneously.
                  </p>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
