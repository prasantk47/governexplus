import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ClipboardDocumentCheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  Table,
  Select,
  SearchInput,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type AssessmentStatus = 'draft' | 'sent' | 'in_progress' | 'completed' | 'overdue';
type RiskRating = 'critical' | 'high' | 'medium' | 'low' | 'not_rated';

interface VendorAssessment {
  id: string;
  vendor_id: string;
  vendor_name?: string;
  assessment_name: string;
  status: AssessmentStatus;
  sent_date?: string;
  due_date?: string;
  overall_score?: number;
  risk_rating: RiskRating;
  assessor?: string;
  responses_summary?: { category: string; score: number; max_score: number }[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_VARIANT: Record<AssessmentStatus, 'success' | 'warning' | 'info' | 'danger' | 'neutral'> = {
  draft: 'neutral',
  sent: 'info',
  in_progress: 'warning',
  completed: 'success',
  overdue: 'danger',
};

const RISK_VARIANT: Record<RiskRating, 'danger' | 'warning' | 'success' | 'neutral' | 'info'> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'success',
  not_rated: 'neutral',
};

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'sent', label: 'Sent' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'overdue', label: 'Overdue' },
];

// ─── Score Progress Bar ───────────────────────────────────────────────────────

function ScoreBar({ score }: { score?: number }) {
  if (score === undefined || score === null) {
    return <span className="text-xs text-gray-400">Not scored</span>;
  }
  const pct = Math.min(100, Math.max(0, score));
  const color =
    pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-yellow-400' : pct >= 40 ? 'bg-orange-400' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-28 h-2 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{score}%</span>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function AssessmentScoring() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [viewingAssessment, setViewingAssessment] = useState<VendorAssessment | null>(null);

  // ── Queries ──

  const { data: assessmentsData, isLoading } = useQuery<VendorAssessment[]>({
    queryKey: ['tprm-assessments', statusFilter],
    queryFn: () =>
      api
        .get('/tprm/assessments', {
          params: statusFilter ? { status: statusFilter } : {},
        })
        .then(r => r.data?.assessments ?? r.data ?? []),
  });

  const assessments: VendorAssessment[] = assessmentsData ?? [];

  const filtered = assessments.filter(a => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      a.assessment_name.toLowerCase().includes(q) ||
      (a.vendor_name ?? '').toLowerCase().includes(q) ||
      (a.assessor ?? '').toLowerCase().includes(q)
    );
  });

  // ── Columns ──

  const columns = [
    {
      key: 'assessment_name',
      header: 'Assessment',
      render: (a: VendorAssessment) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{a.assessment_name}</div>
          {a.assessor && (
            <div className="text-xs text-gray-400">Assessor: {a.assessor}</div>
          )}
        </div>
      ),
    },
    {
      key: 'vendor',
      header: 'Vendor',
      render: (a: VendorAssessment) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{a.vendor_name || a.vendor_id}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (a: VendorAssessment) => (
        <Badge variant={STATUS_VARIANT[a.status]} dot size="sm">
          {a.status.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'due_date',
      header: 'Due Date',
      render: (a: VendorAssessment) => {
        if (!a.due_date) return <span className="text-sm text-gray-400">—</span>;
        const isOverdue = new Date(a.due_date) < new Date() && a.status !== 'completed';
        return (
          <span className={`text-sm ${isOverdue ? 'text-red-600 dark:text-red-400 font-medium' : 'text-gray-600 dark:text-gray-400'}`}>
            {new Date(a.due_date).toLocaleDateString()}
          </span>
        );
      },
    },
    {
      key: 'score',
      header: 'Overall Score',
      render: (a: VendorAssessment) => <ScoreBar score={a.overall_score} />,
    },
    {
      key: 'risk_rating',
      header: 'Risk Rating',
      render: (a: VendorAssessment) => (
        <Badge variant={RISK_VARIANT[a.risk_rating]} size="sm">
          {a.risk_rating.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (a: VendorAssessment) => (
        <Button size="sm" variant="ghost" onClick={e => { e.stopPropagation(); setViewingAssessment(a); }}>
          View
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Assessment Scoring"
        subtitle="Track vendor assessment responses, scores, and risk ratings"
      />

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by assessment name, vendor, or assessor..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            options={STATUS_OPTIONS}
          />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        onRowClick={a => setViewingAssessment(a)}
        emptyMessage="No assessments found. Assessments are created from the Vendor Registry."
      />

      {/* Detail Side Panel */}
      {viewingAssessment && (
        <div className="fixed inset-y-0 right-0 w-[480px] bg-white dark:bg-slate-900 border-l border-gray-200 dark:border-slate-700 shadow-2xl z-40 overflow-y-auto">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700">
            <div>
              <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                {viewingAssessment.assessment_name}
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">{viewingAssessment.vendor_name}</p>
            </div>
            <button
              onClick={() => setViewingAssessment(null)}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-400 transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          <div className="p-6 space-y-6">
            {/* Summary Metrics */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Status</p>
                <Badge variant={STATUS_VARIANT[viewingAssessment.status]} dot size="sm">
                  {viewingAssessment.status.replace('_', ' ')}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Risk Rating</p>
                <Badge variant={RISK_VARIANT[viewingAssessment.risk_rating]} size="sm">
                  {viewingAssessment.risk_rating.replace('_', ' ')}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Due Date</p>
                <p className="text-sm text-gray-800 dark:text-gray-200">
                  {viewingAssessment.due_date
                    ? new Date(viewingAssessment.due_date).toLocaleDateString()
                    : '—'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Assessor</p>
                <p className="text-sm text-gray-800 dark:text-gray-200">{viewingAssessment.assessor || '—'}</p>
              </div>
            </div>

            {/* Overall Score */}
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Overall Score</p>
              <ScoreBar score={viewingAssessment.overall_score} />
            </div>

            {/* Response Categories */}
            {(viewingAssessment.responses_summary ?? []).length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Score Breakdown</p>
                <div className="space-y-3">
                  {(viewingAssessment.responses_summary ?? []).map(cat => (
                    <div key={cat.category}>
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs text-gray-600 dark:text-gray-400">{cat.category}</span>
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                          {cat.score}/{cat.max_score}
                        </span>
                      </div>
                      <div className="h-1.5 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500 rounded-full"
                          style={{ width: `${(cat.score / cat.max_score) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(viewingAssessment.responses_summary ?? []).length === 0 && (
              <div className="text-center py-8">
                <ClipboardDocumentCheckIcon className="h-10 w-10 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-400">No response details available</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
