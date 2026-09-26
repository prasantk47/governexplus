import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  CodeBracketIcon,
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
  CheckCircleIcon,
  QuestionMarkCircleIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowDownTrayIcon,
  EyeIcon,
  PlayIcon,
  XMarkIcon,
  LockClosedIcon,
  ClockIcon,
  UserGroupIcon,
  DocumentMagnifyingGlassIcon,
  BeakerIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

// ─── Types ───────────────────────────────────────────────────────────────────

type RiskLevel = 'high' | 'medium' | 'low' | 'unanalyzed';

interface AuthObject {
  name: string;
  description: string;
  fields: string[];
  sensitivityLevel: 'critical' | 'high' | 'medium' | 'low';
}

interface BehaviorPattern {
  pattern: string;
  description: string;
  riskIndicator: boolean;
}

interface TcodeDetail {
  tcode: string;
  description: string;
  program: string;
  riskLevel: RiskLevel;
  authObjectsUsed: AuthObject[];
  lastUsed: string | null;
  usersAssigned: number;
  createdBy: string;
  createdOn: string;
  packageName: string;
  functionGroup: string;
  analysisDate: string | null;
  behaviorPatterns: BehaviorPattern[];
  recommendations: string[];
  riskScore: number | null;
  notes: string;
}

interface CustomTcodeRow {
  tcode: string;
  description: string;
  program: string;
  riskLevel: RiskLevel;
  authObjectsCount: number;
  lastUsed: string | null;
  usersAssigned: number;
  analysisDate: string | null;
}

interface Stats {
  total: number;
  high: number;
  medium: number;
  low: number;
  unanalyzed: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const riskConfig: Record<
  RiskLevel,
  { label: string; badgeClass: string; textClass: string; dotClass: string; icon: React.ElementType }
> = {
  high: {
    label: 'High',
    badgeClass: 'bg-red-100 text-red-800',
    textClass: 'text-red-700',
    dotClass: 'bg-red-500',
    icon: ShieldExclamationIcon,
  },
  medium: {
    label: 'Medium',
    badgeClass: 'bg-amber-100 text-amber-800',
    textClass: 'text-amber-700',
    dotClass: 'bg-amber-400',
    icon: ExclamationTriangleIcon,
  },
  low: {
    label: 'Low',
    badgeClass: 'bg-green-100 text-green-800',
    textClass: 'text-green-700',
    dotClass: 'bg-green-500',
    icon: CheckCircleIcon,
  },
  unanalyzed: {
    label: 'Unanalyzed',
    badgeClass: 'bg-gray-100 text-gray-600',
    textClass: 'text-gray-500',
    dotClass: 'bg-gray-400',
    icon: QuestionMarkCircleIcon,
  },
};

const authSensitivityConfig: Record<
  AuthObject['sensitivityLevel'],
  { label: string; class: string }
> = {
  critical: { label: 'Critical', class: 'bg-red-100 text-red-800' },
  high:     { label: 'High',     class: 'bg-orange-100 text-orange-800' },
  medium:   { label: 'Medium',   class: 'bg-amber-100 text-amber-800' },
  low:      { label: 'Low',      class: 'bg-green-100 text-green-800' },
};

function RiskBadge({ level }: { level: RiskLevel }) {
  const cfg = riskConfig[level];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${cfg.badgeClass}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dotClass}`} />
      {cfg.label}
    </span>
  );
}

function RiskScoreBar({ score }: { score: number }) {
  const color =
    score >= 70 ? 'bg-red-500' : score >= 40 ? 'bg-amber-400' : 'bg-green-500';
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${color}`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className={`text-sm font-bold ${color.replace('bg-', 'text-')}`}>
        {score}
      </span>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function CustomTcode() {
  const queryClient = useQueryClient();

  const [searchTerm, setSearchTerm]       = useState('');
  const [riskFilter, setRiskFilter]       = useState<RiskLevel | ''>('');
  const [selectedTcode, setSelectedTcode] = useState<TcodeDetail | null>(null);
  const [showDetail, setShowDetail]       = useState(false);
  const [analyzingSet, setAnalyzingSet]   = useState<Set<string>>(new Set());

  // ── Data Fetching ──────────────────────────────────────────────────────────

  const { data: statsData } = useQuery<Stats>({
    queryKey: ['custom-tcode-stats'],
    queryFn: () =>
      api.get('/custom-tcode/stats').then((r) => r.data),
    retry: 1,
  });
  const stats: Stats = statsData ?? { total: 0, high: 0, medium: 0, low: 0, unanalyzed: 0 };

  const { data: tcodesData, isError: tcodesError } = useQuery<CustomTcodeRow[]>({
    queryKey: ['custom-tcodes'],
    queryFn: () =>
      api.get('/custom-tcode/').then((r) => r.data?.tcodes ?? r.data ?? []),
    retry: 1,
  });
  const tcodes: CustomTcodeRow[] = tcodesError || !tcodesData ? [] : tcodesData;

  // ── Detail Fetch (on demand) ───────────────────────────────────────────────

  const detailQuery = useQuery<TcodeDetail>({
    queryKey: ['custom-tcode-detail', selectedTcode?.tcode],
    queryFn: () =>
      api
        .get(`/custom-tcode/${selectedTcode!.tcode}`)
        .then((r) => r.data),
    enabled: showDetail && !!selectedTcode?.tcode,
    retry: 1,
  });

  const detailData: TcodeDetail =
    detailQuery.data ?? {
      ...(selectedTcode as any),
      authObjectsUsed: [],
      behaviorPatterns: [],
      recommendations: [],
      riskScore: null,
      createdBy: '—',
      createdOn: '—',
      packageName: '—',
      functionGroup: '—',
      notes: '',
    };

  // ── Analyze Mutation ───────────────────────────────────────────────────────

  const analyzeMutation = useMutation({
    mutationFn: (tcode: string) =>
      api.post('/custom-tcode/analyze', { tcode }).then((r) => r.data),
    onMutate: (tcode) => {
      setAnalyzingSet((prev) => new Set(prev).add(tcode));
    },
    onSuccess: (_data, tcode) => {
      queryClient.invalidateQueries({ queryKey: ['custom-tcodes'] });
      queryClient.invalidateQueries({ queryKey: ['custom-tcode-stats'] });
      queryClient.invalidateQueries({ queryKey: ['custom-tcode-detail', tcode] });
      toast.success(`Analysis complete for ${tcode}.`);
      setAnalyzingSet((prev) => {
        const next = new Set(prev);
        next.delete(tcode);
        return next;
      });
    },
    onError: (_err, tcode) => {
      toast.error(`Analysis failed for ${tcode}. Please retry.`);
      setAnalyzingSet((prev) => {
        const next = new Set(prev);
        next.delete(tcode);
        return next;
      });
    },
  });

  // ── Filtering ─────────────────────────────────────────────────────────────

  const filtered = tcodes.filter((t) => {
    const term = searchTerm.toLowerCase();
    const matchesSearch =
      t.tcode.toLowerCase().includes(term) ||
      t.description.toLowerCase().includes(term) ||
      t.program.toLowerCase().includes(term);
    const matchesRisk = riskFilter === '' || t.riskLevel === riskFilter;
    return matchesSearch && matchesRisk;
  });

  // ── Export ─────────────────────────────────────────────────────────────────

  function handleExport() {
    const headers = [
      'TCode', 'Description', 'Program', 'Risk Level',
      'Auth Objects', 'Last Used', 'Users Assigned', 'Analysis Date',
    ];
    const rows = filtered.map((t) => [
      t.tcode, t.description, t.program, t.riskLevel,
      t.authObjectsCount, t.lastUsed ?? 'Never', t.usersAssigned, t.analysisDate ?? 'Not analyzed',
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${cell}"`).join(','))
      .join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `custom_tcode_analysis_2026-08-21.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
    toast.success(`Exported ${filtered.length} custom T-codes to CSV.`);
  }

  // ── Open Detail ────────────────────────────────────────────────────────────

  function openDetail(row: CustomTcodeRow) {
    setSelectedTcode(row as any);
    setShowDetail(true);
  }

  function closeDetail() {
    setShowDetail(false);
    setSelectedTcode(null);
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <CodeBracketIcon className="h-7 w-7 text-primary-600" />
            Custom T-Code Analysis
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Risk analysis of Z- and Y-prefix custom transaction codes across SAP systems
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExport}
            className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium transition-colors"
          >
            <ArrowDownTrayIcon className="h-4 w-4" />
            Export Report
          </button>
          <button
            onClick={() => {
              const unanalyzed = tcodes.filter((t) => t.riskLevel === 'unanalyzed');
              if (unanalyzed.length === 0) {
                toast('All T-codes are already analyzed.', { icon: '✓' });
                return;
              }
              unanalyzed.forEach((t) => analyzeMutation.mutate(t.tcode));
            }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium transition-colors"
          >
            <PlayIcon className="h-4 w-4" />
            Analyze All Unanalyzed
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center gap-2 mb-3">
            <CodeBracketIcon className="h-5 w-5 text-gray-400" />
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Total Custom</span>
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.total}</p>
          <p className="text-xs text-gray-400 mt-1">Z/Y transactions</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-red-100 p-5">
          <div className="flex items-center gap-2 mb-3">
            <ShieldExclamationIcon className="h-5 w-5 text-red-500" />
            <span className="text-xs font-medium text-red-600 uppercase tracking-wide">High Risk</span>
          </div>
          <p className="text-3xl font-bold text-red-600">{stats.high}</p>
          <p className="text-xs text-red-400 mt-1">Immediate review needed</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-amber-100 p-5">
          <div className="flex items-center gap-2 mb-3">
            <ExclamationTriangleIcon className="h-5 w-5 text-amber-500" />
            <span className="text-xs font-medium text-amber-600 uppercase tracking-wide">Medium Risk</span>
          </div>
          <p className="text-3xl font-bold text-amber-600">{stats.medium}</p>
          <p className="text-xs text-amber-400 mt-1">Monitor &amp; review</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-green-100 p-5">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircleIcon className="h-5 w-5 text-green-500" />
            <span className="text-xs font-medium text-green-600 uppercase tracking-wide">Low Risk</span>
          </div>
          <p className="text-3xl font-bold text-green-600">{stats.low}</p>
          <p className="text-xs text-green-400 mt-1">Acceptable risk level</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-3">
            <QuestionMarkCircleIcon className="h-5 w-5 text-gray-400" />
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Unanalyzed</span>
          </div>
          <p className="text-3xl font-bold text-gray-500">{stats.unanalyzed}</p>
          <p className="text-xs text-gray-400 mt-1">Pending analysis</p>
        </div>
      </div>

      {/* Unanalyzed Warning Banner */}
      {stats.unanalyzed > 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <ExclamationCircleIcon className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-amber-800">
              {stats.unanalyzed} custom T-code{stats.unanalyzed !== 1 ? 's' : ''} have not been analyzed
            </p>
            <p className="text-xs text-amber-700 mt-0.5">
              Unanalyzed Z-transactions carry unknown risk. Run analysis to classify and apply appropriate controls.
            </p>
          </div>
          <button
            onClick={() => setRiskFilter('unanalyzed')}
            className="flex-shrink-0 text-xs font-medium text-amber-700 underline hover:text-amber-900"
          >
            View unanalyzed
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by T-code, description, or program name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
            />
          </div>
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value as RiskLevel | '')}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
            >
              <option value="">All Risk Levels</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="unanalyzed">Unanalyzed</option>
            </select>
          </div>
          {(searchTerm || riskFilter) && (
            <button
              onClick={() => { setSearchTerm(''); setRiskFilter(''); }}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 px-2 py-2"
            >
              <XMarkIcon className="h-4 w-4" />
              Clear
            </button>
          )}
          <span className="text-xs text-gray-400 whitespace-nowrap">
            {filtered.length} of {tcodes.length} records
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-100">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                T-Code / Description
              </th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Program
              </th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Risk Level
              </th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Auth Objects
              </th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Last Used
              </th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Users Assigned
              </th>
              <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-5 py-12 text-center text-sm text-gray-400">
                  No custom T-codes match your search criteria.
                </td>
              </tr>
            ) : (
              filtered.map((row) => {
                const cfg = riskConfig[row.riskLevel];
                const isAnalyzing = analyzingSet.has(row.tcode);
                return (
                  <tr key={row.tcode} className="hover:bg-gray-50/60 transition-colors">
                    {/* T-Code / Description */}
                    <td className="px-5 py-4">
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5">
                          <cfg.icon className={`h-5 w-5 ${cfg.textClass}`} />
                        </div>
                        <div>
                          <button
                            onClick={() => openDetail(row)}
                            className="text-sm font-semibold text-primary-600 hover:text-primary-800 transition-colors font-mono"
                          >
                            {row.tcode}
                          </button>
                          <p className="text-xs text-gray-500 mt-0.5">{row.description}</p>
                        </div>
                      </div>
                    </td>

                    {/* Program */}
                    <td className="px-5 py-4">
                      <span className="text-xs font-mono text-gray-600 bg-gray-100 px-1.5 py-0.5 rounded">
                        {row.program}
                      </span>
                    </td>

                    {/* Risk Level */}
                    <td className="px-5 py-4">
                      <RiskBadge level={row.riskLevel} />
                    </td>

                    {/* Auth Objects */}
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-1.5">
                        <LockClosedIcon className="h-3.5 w-3.5 text-gray-400" />
                        <span className="text-sm text-gray-700 font-medium">
                          {row.authObjectsCount > 0 ? row.authObjectsCount : '—'}
                        </span>
                        {row.authObjectsCount > 0 && (
                          <span className="text-xs text-gray-400">objects</span>
                        )}
                      </div>
                    </td>

                    {/* Last Used */}
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-1.5">
                        <ClockIcon className="h-3.5 w-3.5 text-gray-400" />
                        <span className="text-sm text-gray-600">
                          {row.lastUsed ?? <span className="text-gray-400 italic">Never</span>}
                        </span>
                      </div>
                    </td>

                    {/* Users Assigned */}
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-1.5">
                        <UserGroupIcon className="h-3.5 w-3.5 text-gray-400" />
                        <span className="text-sm text-gray-700 font-medium">{row.usersAssigned}</span>
                      </div>
                    </td>

                    {/* Actions */}
                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openDetail(row)}
                          className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                          title="View full analysis"
                        >
                          <EyeIcon className="h-4 w-4" />
                        </button>
                        {row.riskLevel === 'unanalyzed' && (
                          <button
                            onClick={() => analyzeMutation.mutate(row.tcode)}
                            disabled={isAnalyzing}
                            className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg transition-colors ${
                              isAnalyzing
                                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                : 'bg-primary-50 text-primary-700 hover:bg-primary-100'
                            }`}
                            title="Run analysis"
                          >
                            <PlayIcon className="h-3.5 w-3.5" />
                            {isAnalyzing ? 'Analyzing…' : 'Analyze'}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Detail Modal */}
      {showDetail && selectedTcode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={closeDetail}
          />

          {/* Panel */}
          <div className="relative w-full max-w-3xl max-h-[90vh] mx-4 bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden">

            {/* Modal Header */}
            <div className="flex items-start justify-between px-6 py-5 border-b border-gray-100 bg-gray-50/60">
              <div>
                <div className="flex items-center gap-3">
                  <DocumentMagnifyingGlassIcon className="h-6 w-6 text-primary-600 flex-shrink-0" />
                  <h2 className="text-lg font-bold text-gray-900 font-mono">
                    {detailData.tcode}
                  </h2>
                  <RiskBadge level={detailData.riskLevel} />
                </div>
                <p className="mt-1 text-sm text-gray-500 ml-9">{detailData.description}</p>
              </div>
              <button
                onClick={closeDetail}
                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="overflow-y-auto flex-1 px-6 py-5 space-y-6">

              {/* Loading state */}
              {detailQuery.isLoading && (
                <div className="flex items-center justify-center py-10 text-sm text-gray-400 gap-2">
                  <BeakerIcon className="h-5 w-5 animate-pulse" />
                  Loading full analysis…
                </div>
              )}

              {/* Risk Score */}
              {detailData.riskScore !== null && (
                <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Composite Risk Score
                  </p>
                  <RiskScoreBar score={detailData.riskScore} />
                  <p className="text-xs text-gray-400 mt-1.5">
                    Score factors: auth object sensitivity, bypass patterns, user count, audit trail gaps
                  </p>
                </div>
              )}

              {/* Metadata Grid */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  T-Code Metadata
                </p>
                <div className="grid grid-cols-2 gap-x-8 gap-y-3">
                  {[
                    { label: 'Program',        value: detailData.program },
                    { label: 'Package',        value: detailData.packageName },
                    { label: 'Function Group', value: detailData.functionGroup },
                    { label: 'Created By',     value: detailData.createdBy },
                    { label: 'Created On',     value: detailData.createdOn },
                    { label: 'Analysis Date',  value: detailData.analysisDate ?? 'Not yet analyzed' },
                    { label: 'Users Assigned', value: String(detailData.usersAssigned) },
                    { label: 'Last Used',      value: detailData.lastUsed ?? 'Never' },
                  ].map(({ label, value }) => (
                    <div key={label}>
                      <p className="text-xs text-gray-400">{label}</p>
                      <p className="text-sm font-medium text-gray-800 font-mono mt-0.5">{value}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Auth Objects */}
              {detailData.authObjectsUsed.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-2">
                    <LockClosedIcon className="h-4 w-4" />
                    Authorization Objects Checked ({detailData.authObjectsUsed.length})
                  </p>
                  <div className="space-y-2">
                    {detailData.authObjectsUsed.map((obj) => {
                      const scfg = authSensitivityConfig[obj.sensitivityLevel];
                      return (
                        <div
                          key={obj.name}
                          className="flex items-start justify-between gap-4 rounded-lg border border-gray-100 bg-gray-50/70 px-4 py-3"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <span className="text-sm font-semibold font-mono text-gray-800">
                                {obj.name}
                              </span>
                              <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${scfg.class}`}>
                                {scfg.label}
                              </span>
                            </div>
                            <p className="text-xs text-gray-500">{obj.description}</p>
                            <div className="flex flex-wrap gap-1 mt-1.5">
                              {obj.fields.map((f) => (
                                <span
                                  key={f}
                                  className="text-xs bg-white border border-gray-200 text-gray-600 px-1.5 py-0.5 rounded font-mono"
                                >
                                  {f}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Behavior Patterns */}
              {detailData.behaviorPatterns.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-2">
                    <BeakerIcon className="h-4 w-4" />
                    Behavior Patterns Detected
                  </p>
                  <div className="space-y-2">
                    {detailData.behaviorPatterns.map((bp, i) => (
                      <div
                        key={i}
                        className={`rounded-lg border px-4 py-3 flex items-start gap-3 ${
                          bp.riskIndicator
                            ? 'border-red-100 bg-red-50/60'
                            : 'border-green-100 bg-green-50/60'
                        }`}
                      >
                        {bp.riskIndicator ? (
                          <ExclamationTriangleIcon className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
                        ) : (
                          <CheckCircleIcon className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                        )}
                        <div>
                          <p className={`text-sm font-medium ${bp.riskIndicator ? 'text-red-800' : 'text-green-800'}`}>
                            {bp.pattern}
                          </p>
                          <p className="text-xs text-gray-600 mt-0.5 leading-relaxed">
                            {bp.description}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {detailData.recommendations.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                    Recommendations
                  </p>
                  <ol className="space-y-2">
                    {detailData.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-3">
                        <span className="flex-shrink-0 inline-flex items-center justify-center h-5 w-5 rounded-full bg-primary-100 text-primary-700 text-xs font-bold mt-0.5">
                          {i + 1}
                        </span>
                        <p className="text-sm text-gray-700 leading-relaxed">{rec}</p>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Notes */}
              {detailData.notes && (
                <div className="rounded-lg border border-blue-100 bg-blue-50/50 px-4 py-3">
                  <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">Notes</p>
                  <p className="text-sm text-blue-800 leading-relaxed">{detailData.notes}</p>
                </div>
              )}

              {/* Unanalyzed state */}
              {detailData.riskLevel === 'unanalyzed' && (
                <div className="flex flex-col items-center gap-3 py-6 text-center">
                  <QuestionMarkCircleIcon className="h-10 w-10 text-gray-300" />
                  <p className="text-sm font-medium text-gray-600">
                    This T-code has not been analyzed yet.
                  </p>
                  <p className="text-xs text-gray-400 max-w-sm">
                    Running analysis will inspect authorization objects, check for behavioral risk patterns,
                    and assign a risk score.
                  </p>
                  <button
                    onClick={() => {
                      analyzeMutation.mutate(detailData.tcode);
                      closeDetail();
                    }}
                    disabled={analyzingSet.has(detailData.tcode)}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <PlayIcon className="h-4 w-4" />
                    {analyzingSet.has(detailData.tcode) ? 'Analyzing…' : 'Run Analysis Now'}
                  </button>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 bg-gray-50/60">
              <div className="text-xs text-gray-400">
                {detailData.analysisDate
                  ? `Last analyzed: ${detailData.analysisDate}`
                  : 'Analysis pending'}
              </div>
              <div className="flex items-center gap-2">
                {detailData.riskLevel !== 'unanalyzed' && (
                  <button
                    onClick={() => {
                      analyzeMutation.mutate(detailData.tcode);
                      closeDetail();
                    }}
                    disabled={analyzingSet.has(detailData.tcode)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <PlayIcon className="h-3.5 w-3.5" />
                    Re-Analyze
                  </button>
                )}
                <button
                  onClick={closeDetail}
                  className="px-4 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
