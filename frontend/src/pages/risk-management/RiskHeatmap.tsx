import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowPathIcon,
  ChevronUpIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import { riskManagementApi } from '../../services/riskManagementApi';
import { PageHeader, Card, CardHeader, Badge } from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

interface HeatmapCell {
  likelihood: number;
  impact: number;
  inherent_count: number;
  residual_count: number;
  risks: HeatmapRisk[];
}

interface HeatmapRisk {
  id: string;
  risk_id: string;
  title: string;
  owner: string;
  status: string;
}

interface HeatmapData {
  cells: HeatmapCell[];
  top_risks: TopRisk[];
}

interface TopRisk {
  id: string;
  risk_id: string;
  title: string;
  category: string;
  inherent_score: number;
  residual_score: number;
  owner: string;
  status: string;
}

interface TrendPoint {
  month: string;
  avg_inherent: number;
  avg_residual: number;
  open_count: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function cellColor(score: number): string {
  if (score <= 4) return 'bg-emerald-100 dark:bg-emerald-900/30 hover:bg-emerald-200 dark:hover:bg-emerald-900/50';
  if (score <= 9) return 'bg-amber-100 dark:bg-amber-900/30 hover:bg-amber-200 dark:hover:bg-amber-900/50';
  if (score <= 15) return 'bg-orange-100 dark:bg-orange-900/30 hover:bg-orange-200 dark:hover:bg-orange-900/50';
  return 'bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50';
}

function cellTextColor(score: number): string {
  if (score <= 4) return 'text-emerald-700 dark:text-emerald-400';
  if (score <= 9) return 'text-amber-700 dark:text-amber-400';
  if (score <= 15) return 'text-orange-700 dark:text-orange-400';
  return 'text-red-700 dark:text-red-400';
}

function scoreLabel(score: number): string {
  if (score <= 4) return 'Low';
  if (score <= 9) return 'Medium';
  if (score <= 15) return 'High';
  return 'Critical';
}

function scoreVariant(score: number): 'success' | 'warning' | 'danger' {
  if (score <= 5) return 'success';
  if (score <= 12) return 'warning';
  return 'danger';
}

// Mini sparkline from trend data
function Sparkline({ data, field }: { data: TrendPoint[]; field: 'avg_inherent' | 'avg_residual' }) {
  if (data.length < 2) return null;
  const values = data.map(d => d[field]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 200;
  const height = 48;
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 8) - 4;
    return `${x},${y}`;
  });
  const color = field === 'avg_inherent' ? '#ef4444' : '#f97316';
  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {values.map((v, i) => {
        const x = (i / (values.length - 1)) * width;
        const y = height - ((v - min) / range) * (height - 8) - 4;
        return <circle key={i} cx={x} cy={y} r={3} fill={color} />;
      })}
    </svg>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function RiskHeatmap() {
  const [view, setView] = useState<'inherent' | 'residual'>('inherent');
  const [selectedCell, setSelectedCell] = useState<HeatmapCell | null>(null);

  const { data: heatmapData, isLoading: heatmapLoading, refetch } = useQuery<HeatmapData>({
    queryKey: ['risk-heatmap'],
    queryFn: () => riskManagementApi.getHeatmap().then(r => r.data),
  });

  const { data: trendsData, isLoading: trendsLoading } = useQuery<TrendPoint[]>({
    queryKey: ['risk-trends'],
    queryFn: () => riskManagementApi.getTrends(12).then(r => r.data?.trend ?? r.data ?? []),
  });

  const { data: topRisksData } = useQuery<TopRisk[]>({
    queryKey: ['risk-top'],
    queryFn: () => riskManagementApi.getTopRisks(10).then(r => r.data?.risks ?? r.data ?? []),
  });

  const cells: HeatmapCell[] = heatmapData?.cells ?? [];
  const topRisks: TopRisk[] = topRisksData ?? heatmapData?.top_risks ?? [];
  const trends: TrendPoint[] = trendsData ?? [];

  function getCellData(likelihood: number, impact: number): HeatmapCell | null {
    return cells.find(c => c.likelihood === likelihood && c.impact === impact) ?? null;
  }

  function getCellCount(likelihood: number, impact: number): number {
    const cell = getCellData(likelihood, impact);
    if (!cell) return 0;
    return view === 'inherent' ? cell.inherent_count : cell.residual_count;
  }

  function handleCellClick(likelihood: number, impact: number) {
    const cell = getCellData(likelihood, impact);
    if (cell && (view === 'inherent' ? cell.inherent_count : cell.residual_count) > 0) {
      setSelectedCell(cell);
    }
  }

  const isLoading = heatmapLoading;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Heatmap"
        subtitle="Visual representation of risk distribution by likelihood and impact"
        actions={
          <button
            onClick={() => refetch()}
            className="p-2 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors"
            title="Refresh"
          >
            <ArrowPathIcon className="h-5 w-5" />
          </button>
        }
      />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Heatmap */}
        <div className="xl:col-span-2">
          <Card padding="lg">
            <CardHeader
              title="Risk Matrix (5×5)"
              subtitle={view === 'inherent' ? 'Inherent risk — before controls' : 'Residual risk — after controls'}
              action={
                <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden text-xs font-medium">
                  <button
                    onClick={() => setView('inherent')}
                    className={`px-3 py-1.5 transition-colors ${
                      view === 'inherent'
                        ? 'bg-indigo-600 text-white'
                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'
                    }`}
                  >
                    Inherent
                  </button>
                  <button
                    onClick={() => setView('residual')}
                    className={`px-3 py-1.5 transition-colors ${
                      view === 'residual'
                        ? 'bg-indigo-600 text-white'
                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'
                    }`}
                  >
                    Residual
                  </button>
                </div>
              }
            />

            {isLoading ? (
              <div className="flex items-center justify-center h-72">
                <div className="flex flex-col items-center gap-3">
                  <svg className="animate-spin h-8 w-8 text-indigo-500" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span className="text-sm text-gray-500">Loading heatmap...</span>
                </div>
              </div>
            ) : (
              <div className="mt-4">
                {/* Y-axis label */}
                <div className="flex gap-3">
                  <div className="flex flex-col items-center justify-center w-8">
                    <span
                      className="text-xs font-semibold text-gray-500 dark:text-gray-400 tracking-wider"
                      style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
                    >
                      LIKELIHOOD
                    </span>
                  </div>

                  <div className="flex-1">
                    {/* Grid rows: likelihood 5 (top) → 1 (bottom) */}
                    <div className="space-y-1">
                      {[5, 4, 3, 2, 1].map(likelihood => (
                        <div key={likelihood} className="flex gap-1 items-center">
                          <span className="w-5 text-xs text-gray-400 text-right flex-shrink-0">
                            {likelihood}
                          </span>
                          {[1, 2, 3, 4, 5].map(impact => {
                            const score = likelihood * impact;
                            const count = getCellCount(likelihood, impact);
                            return (
                              <button
                                key={impact}
                                onClick={() => handleCellClick(likelihood, impact)}
                                className={`flex-1 aspect-square flex flex-col items-center justify-center rounded-lg transition-all duration-150 border-2 ${
                                  count > 0 ? 'border-transparent cursor-pointer' : 'border-transparent cursor-default'
                                } ${cellColor(score)}`}
                                title={`L${likelihood} × I${impact} = ${score} (${scoreLabel(score)}) — ${count} risk${count !== 1 ? 's' : ''}`}
                              >
                                <span className={`text-xs font-bold ${cellTextColor(score)}`}>
                                  {score}
                                </span>
                                {count > 0 && (
                                  <span className={`text-[10px] font-semibold ${cellTextColor(score)} opacity-80`}>
                                    {count}
                                  </span>
                                )}
                              </button>
                            );
                          })}
                        </div>
                      ))}
                    </div>

                    {/* X axis */}
                    <div className="flex gap-1 mt-1">
                      <span className="w-5 flex-shrink-0" />
                      {[1, 2, 3, 4, 5].map(i => (
                        <span key={i} className="flex-1 text-center text-xs text-gray-400">
                          {i}
                        </span>
                      ))}
                    </div>
                    <p className="text-center text-xs font-semibold text-gray-500 dark:text-gray-400 tracking-wider mt-1">
                      IMPACT
                    </p>
                  </div>
                </div>

                {/* Legend */}
                <div className="flex items-center gap-4 mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 flex-wrap">
                  {[
                    { label: 'Low (1–4)', bg: 'bg-emerald-200', text: 'text-emerald-700' },
                    { label: 'Medium (5–9)', bg: 'bg-amber-200', text: 'text-amber-700' },
                    { label: 'High (10–15)', bg: 'bg-orange-200', text: 'text-orange-700' },
                    { label: 'Critical (16–25)', bg: 'bg-red-200', text: 'text-red-700' },
                  ].map(item => (
                    <div key={item.label} className="flex items-center gap-1.5">
                      <span className={`w-4 h-4 rounded ${item.bg}`} />
                      <span className={`text-xs font-medium ${item.text}`}>{item.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Trend Chart */}
          <Card padding="lg" className="mt-6">
            <CardHeader
              title="Risk Score Trend"
              subtitle="Average inherent and residual scores over time"
            />
            {trendsLoading ? (
              <div className="h-32 flex items-center justify-center text-sm text-gray-400">
                Loading trends...
              </div>
            ) : trends.length === 0 ? (
              <div className="h-32 flex items-center justify-center text-sm text-gray-400">
                No trend data available
              </div>
            ) : (
              <div className="mt-4">
                <div className="flex items-end gap-6 overflow-x-auto pb-2">
                  <div>
                    <div className="flex items-center gap-3 mb-3">
                      <div className="flex items-center gap-1.5">
                        <span className="w-8 h-0.5 bg-red-500 block" />
                        <span className="text-xs text-gray-500">Inherent</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-8 h-0.5 bg-orange-500 block" />
                        <span className="text-xs text-gray-500">Residual</span>
                      </div>
                    </div>
                    <Sparkline data={trends} field="avg_inherent" />
                  </div>
                </div>
                <div className="flex justify-between mt-2">
                  {trends.map((t, i) => (
                    <span key={i} className="text-[10px] text-gray-400 text-center"
                      style={{ flex: 1 }}>
                      {t.month}
                    </span>
                  ))}
                </div>
                <div className="mt-4 grid grid-cols-3 gap-4">
                  {trends.length > 0 && (
                    <>
                      <div className="text-center">
                        <p className="text-xs text-gray-500">Latest Inherent</p>
                        <p className="text-lg font-bold text-red-600">
                          {(trends[trends.length - 1]?.avg_inherent ?? 0).toFixed(1)}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-gray-500">Latest Residual</p>
                        <p className="text-lg font-bold text-orange-500">
                          {(trends[trends.length - 1]?.avg_residual ?? 0).toFixed(1)}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-gray-500">Open Risks</p>
                        <p className="text-lg font-bold text-gray-700 dark:text-gray-300">
                          {trends[trends.length - 1].open_count}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Top Risks Sidebar */}
        <div className="xl:col-span-1">
          <Card padding="lg">
            <CardHeader title="Top 10 Risks" subtitle="Highest inherent score" />
            <div className="space-y-3 mt-2">
              {topRisks.length === 0 ? (
                <p className="text-sm text-gray-400 py-4 text-center">No risk data</p>
              ) : (
                topRisks.slice(0, 10).map((risk, idx) => (
                  <div
                    key={risk.id}
                    className="flex items-start gap-3 p-3 rounded-xl bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                  >
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-400 text-xs font-bold flex items-center justify-center">
                      {idx + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-gray-800 dark:text-gray-200 truncate">
                        {risk.title}
                      </p>
                      <p className="text-[10px] text-gray-400 mt-0.5">{risk.owner}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant={scoreVariant(risk.inherent_score)} size="sm">
                          I:{risk.inherent_score}
                        </Badge>
                        {risk.residual_score !== risk.inherent_score && (
                          <>
                            <span className="text-gray-300 dark:text-gray-600">→</span>
                            <Badge variant={scoreVariant(risk.residual_score)} size="sm">
                              R:{risk.residual_score}
                            </Badge>
                          </>
                        )}
                      </div>
                    </div>
                    {risk.inherent_score > risk.residual_score ? (
                      <ChevronDownIcon className="h-4 w-4 text-emerald-500 flex-shrink-0 mt-1" />
                    ) : (
                      <ChevronUpIcon className="h-4 w-4 text-red-500 flex-shrink-0 mt-1" />
                    )}
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Cell detail overlay */}
      {selectedCell && (
        <div
          className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
          onClick={() => setSelectedCell(null)}
        >
          <div
            className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                  Cell: L{selectedCell.likelihood} × I{selectedCell.impact} = {selectedCell.likelihood * selectedCell.impact}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  {scoreLabel(selectedCell.likelihood * selectedCell.impact)} risk zone
                </p>
              </div>
              <button
                onClick={() => setSelectedCell(null)}
                className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
              >
                ✕
              </button>
            </div>
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {selectedCell.risks.length === 0 ? (
                <p className="text-sm text-gray-400">No risks in this cell</p>
              ) : (
                selectedCell.risks.map(r => (
                  <div
                    key={r.id}
                    className="p-3 rounded-xl bg-gray-50 dark:bg-slate-700/50"
                  >
                    <p className="text-xs font-mono text-indigo-600 dark:text-indigo-400">{r.risk_id}</p>
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mt-0.5">{r.title}</p>
                    <p className="text-xs text-gray-400">{r.owner}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
