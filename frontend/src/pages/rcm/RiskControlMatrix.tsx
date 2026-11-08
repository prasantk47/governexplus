import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  ViewColumnsIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Badge,
  Table,
  SearchInput,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type CoverageLevel = 'full' | 'partial' | 'none';

interface MatrixEntry {
  id: string;
  risk_id: string;
  risk_title: string;
  risk_category: string;
  risk_score: number;
  controls: { id: string; name: string; effectiveness?: number }[];
  coverage: CoverageLevel;
}

interface CoverageGap {
  risk_id: string;
  risk_title: string;
  risk_score: number;
  gap_type: string;
  recommendation?: string;
}

interface EffectivenessData {
  total_controls: number;
  average_effectiveness: number;
  by_rating: Record<string, number>;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const COVERAGE_VARIANT: Record<CoverageLevel, 'success' | 'warning' | 'danger'> = {
  full: 'success',
  partial: 'warning',
  none: 'danger',
};

const COVERAGE_LABEL: Record<CoverageLevel, string> = {
  full: 'Full',
  partial: 'Partial',
  none: 'None',
};

// ─── Component ────────────────────────────────────────────────────────────────

export function RiskControlMatrix() {
  const [search, setSearch] = useState('');

  // ── Queries ──

  const { data: matrixData, isLoading } = useQuery<MatrixEntry[]>({
    queryKey: ['rcm-matrix'],
    queryFn: () =>
      api.get('/rcm/matrix').then(r => r.data?.matrix ?? r.data ?? []),
  });

  const matrix: MatrixEntry[] = matrixData ?? [];

  const { data: gapsData } = useQuery<CoverageGap[]>({
    queryKey: ['rcm-coverage-gaps'],
    queryFn: () =>
      api.get('/rcm/coverage-gaps').then(r => r.data?.gaps ?? r.data ?? []),
  });

  const gaps: CoverageGap[] = gapsData ?? [];

  const { data: effectivenessData } = useQuery<EffectivenessData>({
    queryKey: ['rcm-effectiveness'],
    queryFn: () =>
      api.get('/rcm/control-effectiveness').then(r => r.data ?? { total_controls: 0, average_effectiveness: 0, by_rating: {} }),
  });

  const effectiveness: EffectivenessData = effectivenessData ?? { total_controls: 0, average_effectiveness: 0, by_rating: {} };

  // ── Filtering ──

  const filtered = matrix.filter(m => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      m.risk_title.toLowerCase().includes(q) ||
      m.risk_category.toLowerCase().includes(q) ||
      m.controls.some(c => c.name.toLowerCase().includes(q))
    );
  });

  // ── Stats ──

  const totalRisks = matrix.length;
  const totalControls = effectiveness.total_controls;
  const coveredCount = matrix.filter(m => m.coverage === 'full').length;
  const coveragePct = totalRisks > 0 ? Math.round((coveredCount / totalRisks) * 100) : 0;
  const effectivenessPct = Math.round(effectiveness.average_effectiveness);

  // ── Score Color ──

  function scoreColor(score: number): string {
    if (score >= 75) return 'text-red-600 dark:text-red-400';
    if (score >= 50) return 'text-orange-500 dark:text-orange-400';
    if (score >= 25) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-green-600 dark:text-green-400';
  }

  // ── Columns ──

  const columns = [
    {
      key: 'risk_title',
      header: 'Risk',
      render: (m: MatrixEntry) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{m.risk_title}</div>
          <div className="text-xs text-gray-400">{m.risk_id}</div>
        </div>
      ),
    },
    {
      key: 'risk_category',
      header: 'Category',
      render: (m: MatrixEntry) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{m.risk_category}</span>
      ),
    },
    {
      key: 'risk_score',
      header: 'Risk Score',
      render: (m: MatrixEntry) => (
        <span className={`text-sm font-semibold ${scoreColor(m.risk_score)}`}>
          {m.risk_score}
        </span>
      ),
    },
    {
      key: 'controls',
      header: 'Controls',
      render: (m: MatrixEntry) => (
        <div className="text-sm text-gray-700 dark:text-gray-300 max-w-xs">
          {m.controls.length > 0
            ? m.controls.map(c => c.name).join(', ')
            : <span className="text-gray-400 italic">No controls mapped</span>
          }
        </div>
      ),
    },
    {
      key: 'coverage',
      header: 'Coverage',
      render: (m: MatrixEntry) => (
        <Badge variant={COVERAGE_VARIANT[m.coverage]} dot size="sm">
          {COVERAGE_LABEL[m.coverage]}
        </Badge>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk-Control Matrix"
        subtitle="Map risks to controls and identify coverage gaps"
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Risks" value={totalRisks} icon={ExclamationTriangleIcon} iconBgColor="stat-icon-red" iconColor="" />
        <StatCard title="Total Controls" value={totalControls} icon={ShieldCheckIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Coverage %" value={`${coveragePct}%`} icon={ViewColumnsIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Effectiveness %" value={`${effectivenessPct}%`} icon={ChartBarIcon} iconBgColor="stat-icon-indigo" iconColor="" />
      </div>

      {/* Coverage Gaps Alert */}
      {gaps.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-sm font-semibold text-red-800 dark:text-red-300">
                {gaps.length} Coverage Gap{gaps.length > 1 ? 's' : ''} Detected
              </h3>
              <ul className="mt-1 text-sm text-red-700 dark:text-red-400 space-y-1">
                {gaps.slice(0, 5).map(g => (
                  <li key={g.risk_id}>
                    <span className="font-medium">{g.risk_title}</span>
                    {' — '}
                    <span>{g.gap_type.replace(/_/g, ' ')}</span>
                    {g.recommendation && (
                      <span className="text-red-500 dark:text-red-500"> ({g.recommendation})</span>
                    )}
                  </li>
                ))}
                {gaps.length > 5 && (
                  <li className="text-red-500">...and {gaps.length - 5} more</li>
                )}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Filter */}
      <Card padding="md">
        <SearchInput
          placeholder="Search risks, categories, or controls..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          onClear={() => setSearch('')}
        />
      </Card>

      {/* Matrix Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        emptyMessage="No risk-control mappings found."
      />
    </div>
  );
}
