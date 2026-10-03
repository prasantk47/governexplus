import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowDownTrayIcon,
  DocumentCheckIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  FolderOpenIcon,
  CalendarDaysIcon,
  ArrowPathIcon,
  ChartBarIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Badge,
} from '../../components/ui';

// ============================================================================
// Types
// ============================================================================

type CategoryKey =
  | 'user_access'
  | 'role_changes'
  | 'approvals'
  | 'sod_violations'
  | 'mitigations'
  | 'firefighter'
  | 'certifications'
  | 'provisioning';

interface CategoryConfig {
  key: CategoryKey;
  label: string;
  description: string;
}

interface CategoryResult {
  category: CategoryKey;
  label: string;
  itemCount: number;
  complianceScore: number;
  keyFindings: string[];
}

interface EvidencePackage {
  id: string;
  generatedAt: string;
  generatedBy: string;
  dateFrom: string;
  dateTo: string;
  categories: CategoryKey[];
  overallComplianceScore: number;
  totalItems: number;
  status: 'complete' | 'generating' | 'failed';
  results: CategoryResult[];
}

interface CollectRequest {
  date_from: string;
  date_to: string;
  categories: CategoryKey[];
}

// ============================================================================
// Constants
// ============================================================================

const CATEGORIES: CategoryConfig[] = [
  {
    key: 'user_access',
    label: 'User Access',
    description: 'User account changes, role assignments, and access grants',
  },
  {
    key: 'role_changes',
    label: 'Role Changes',
    description: 'Authorization object modifications and role transports',
  },
  {
    key: 'approvals',
    label: 'Approvals',
    description: 'Access request approvals, rejections, and escalations',
  },
  {
    key: 'sod_violations',
    label: 'SoD Violations',
    description: 'Segregation of duties conflicts detected and remediated',
  },
  {
    key: 'mitigations',
    label: 'Mitigations',
    description: 'Compensating controls and approved risk acceptances',
  },
  {
    key: 'firefighter',
    label: 'Privileged Access',
    description: 'Emergency access sessions and controller reviews',
  },
  {
    key: 'certifications',
    label: 'Certifications',
    description: 'Access certification campaign decisions and outcomes',
  },
  {
    key: 'provisioning',
    label: 'Provisioning',
    description: 'System provisioning actions and connector audit trails',
  },
];

// ============================================================================
// Helpers
// ============================================================================

function scoreColor(score: number): string {
  if (score >= 90) return 'text-emerald-700';
  if (score >= 75) return 'text-amber-700';
  return 'text-red-700';
}

function scoreBarColor(score: number): string {
  if (score >= 90) return 'bg-emerald-500';
  if (score >= 75) return 'bg-amber-500';
  return 'bg-red-500';
}

function scoreVariant(score: number): 'success' | 'warning' | 'danger' {
  if (score >= 90) return 'success';
  if (score >= 75) return 'warning';
  return 'danger';
}

// ============================================================================
// Sub-components
// ============================================================================

function ComplianceGauge({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 40;
  const dash = (score / 100) * circumference;
  const strokeColor =
    score >= 90 ? '#10b981' : score >= 75 ? '#f59e0b' : '#ef4444';

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-28 h-28">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="10"
          />
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke={strokeColor}
            strokeWidth="10"
            strokeDasharray={`${dash} ${circumference}`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-2xl font-bold ${scoreColor(score)}`}>{score}</span>
          <span className="text-[10px] text-gray-400">/ 100</span>
        </div>
      </div>
      <Badge variant={scoreVariant(score)} size="sm" className="mt-2">
        {score >= 90 ? 'Excellent' : score >= 75 ? 'Acceptable' : 'Needs Attention'}
      </Badge>
    </div>
  );
}

// ============================================================================
// Component
// ============================================================================

export function AuditEvidenceCenter() {
  const today = new Date().toISOString().split('T')[0];
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split('T')[0];

  const [dateFrom, setDateFrom] = useState(thirtyDaysAgo);
  const [dateTo, setDateTo] = useState(today);
  const [selectedCategories, setSelectedCategories] = useState<Set<CategoryKey>>(
    new Set(CATEGORIES.map((c) => c.key))
  );
  const [activePackageId, setActivePackageId] = useState<string | null>(null);

  const queryClient = useQueryClient();

  const { data: packagesData } = useQuery<EvidencePackage[]>({
    queryKey: ['audit-evidence-packages'],
    queryFn: () =>
      api
        .get('/audit-evidence/packages')
        .then((res) => res.data)
        .catch(() => []),

  });

  const packages = packagesData ?? [];
  const activePackage =
    activePackageId != null
      ? packages.find((p) => p.id === activePackageId) ?? null
      : null;

  const generateMutation = useMutation<EvidencePackage, Error, CollectRequest>({
    mutationFn: (payload) =>
      api
        .post('/audit-evidence/collect', payload)
        .then((res) => res.data)
        .catch((err) => {
          throw err;
        }),
    onSuccess: (pkg) => {
      queryClient.setQueryData<EvidencePackage[]>(
        ['audit-evidence-packages'],
        (prev) => [pkg, ...(prev ?? [])]
      );
      setActivePackageId(pkg.id);
      toast.success(`Evidence package ${pkg.id} generated — ${(pkg.totalItems ?? 0).toLocaleString()} items collected`);
    },
    onError: () => {
      toast.error('Failed to generate evidence package');
    },
  });

  const handleToggleCategory = (key: CategoryKey) => {
    setSelectedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    setSelectedCategories(new Set(CATEGORIES.map((c) => c.key)));
  };

  const handleClearAll = () => {
    setSelectedCategories(new Set());
  };

  const handleGenerate = () => {
    if (selectedCategories.size === 0) {
      toast.error('Select at least one category');
      return;
    }
    if (!dateFrom || !dateTo) {
      toast.error('Select a valid date range');
      return;
    }
    if (dateFrom > dateTo) {
      toast.error('Start date must be before end date');
      return;
    }
    generateMutation.mutate({
      date_from: dateFrom,
      date_to: dateTo,
      categories: Array.from(selectedCategories),
    });
  };

  const handleExportPackage = (pkg: EvidencePackage) => {
    const blob = new Blob([JSON.stringify(pkg, null, 2)], {
      type: 'application/json;charset=utf-8;',
    });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `audit_evidence_${pkg.id}_${pkg.dateFrom}_${pkg.dateTo}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
    toast.success(`Package ${pkg.id} exported`);
  };

  const totalPackageItems = packages.reduce((s, p) => s + p.totalItems, 0);
  const avgScore =
    packages.length > 0
      ? Math.round(packages.reduce((s, p) => s + p.overallComplianceScore, 0) / packages.length)
      : 0;
  const compliantPackages = packages.filter((p) => p.overallComplianceScore >= 90).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Evidence Center"
        subtitle="Generate comprehensive evidence packages for internal and external audit engagements"
        breadcrumbs={[{ label: 'Intelligence' }, { label: 'Audit Evidence Center' }]}
        actions={
          <Button
            size="sm"
            icon={<DocumentCheckIcon className="h-4 w-4" />}
            onClick={handleGenerate}
            loading={generateMutation.isPending}
            disabled={selectedCategories.size === 0}
          >
            Generate Evidence Package
          </Button>
        }
      />

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Packages Generated"
          value={packages.length}
          icon={FolderOpenIcon}
          iconBgColor="stat-icon-blue"
          iconColor=""
        />
        <StatCard
          title="Total Audit Items"
          value={(totalPackageItems ?? 0).toLocaleString()}
          icon={ChartBarIcon}
          iconBgColor="stat-icon-green"
          iconColor=""
        />
        <StatCard
          title="Avg Compliance Score"
          value={`${avgScore}%`}
          icon={ShieldCheckIcon}
          iconBgColor="stat-icon-yellow"
          iconColor=""
        />
        <StatCard
          title="Fully Compliant"
          value={compliantPackages}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor=""
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Configuration */}
        <div className="space-y-5">
          {/* Date Range */}
          <Card padding="none">
            <div className="px-5 py-4 border-b border-white/20 flex items-center gap-2">
              <CalendarDaysIcon className="h-4 w-4 text-gray-400" />
              <h2 className="text-sm font-semibold text-gray-900">Date Range</h2>
            </div>
            <div className="p-5 space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Start Date</label>
                <input
                  type="date"
                  value={dateFrom}
                  max={dateTo}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full text-sm border border-gray-200/80 rounded-xl px-3 py-2 bg-white/60 focus:outline-none focus:ring-2 focus:ring-primary-400"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">End Date</label>
                <input
                  type="date"
                  value={dateTo}
                  min={dateFrom}
                  max={today}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full text-sm border border-gray-200/80 rounded-xl px-3 py-2 bg-white/60 focus:outline-none focus:ring-2 focus:ring-primary-400"
                />
              </div>
              <div className="flex gap-2 pt-1">
                {[
                  { label: '7d', days: 7 },
                  { label: '30d', days: 30 },
                  { label: '90d', days: 90 },
                ].map(({ label, days }) => (
                  <button
                    key={label}
                    onClick={() => {
                      const from = new Date(Date.now() - days * 24 * 60 * 60 * 1000)
                        .toISOString()
                        .split('T')[0];
                      setDateFrom(from);
                      setDateTo(today);
                    }}
                    className="flex-1 text-xs py-1.5 rounded-lg border border-gray-200/80 text-gray-600 hover:bg-primary-50 hover:border-primary-300 hover:text-primary-700 transition-colors"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </Card>

          {/* Categories */}
          <Card padding="none">
            <div className="px-5 py-4 border-b border-white/20 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-900">Evidence Categories</h2>
              <div className="flex gap-2">
                <button
                  onClick={handleSelectAll}
                  className="text-xs text-primary-600 hover:text-primary-800 font-medium transition-colors"
                >
                  All
                </button>
                <span className="text-gray-300">|</span>
                <button
                  onClick={handleClearAll}
                  className="text-xs text-gray-400 hover:text-gray-600 font-medium transition-colors"
                >
                  None
                </button>
              </div>
            </div>
            <div className="p-4 space-y-2">
              {CATEGORIES.map((cat) => {
                const checked = selectedCategories.has(cat.key);
                return (
                  <label
                    key={cat.key}
                    className={`flex items-start gap-3 p-3 rounded-xl cursor-pointer border transition-all ${
                      checked
                        ? 'border-primary-300 bg-primary-50/60'
                        : 'border-gray-200/60 hover:border-gray-300 hover:bg-gray-50/60'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleToggleCategory(cat.key)}
                      className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-gray-800">{cat.label}</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">{cat.description}</div>
                    </div>
                  </label>
                );
              })}
            </div>
            <div className="px-5 py-4 border-t border-white/20">
              <Button
                fullWidth
                size="md"
                icon={
                  generateMutation.isPending ? (
                    <ArrowPathIcon className="h-4 w-4 animate-spin" />
                  ) : (
                    <DocumentCheckIcon className="h-4 w-4" />
                  )
                }
                onClick={handleGenerate}
                loading={generateMutation.isPending}
                disabled={selectedCategories.size === 0}
              >
                {generateMutation.isPending
                  ? 'Collecting Evidence...'
                  : `Generate Package (${selectedCategories.size} categories)`}
              </Button>
            </div>
          </Card>
        </div>

        {/* Right Columns: Results + History */}
        <div className="lg:col-span-2 space-y-5">
          {/* Active Package Results */}
          {activePackage ? (
            <Card padding="none">
              <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-gray-900">Package Results</h2>
                  <p className="text-xs text-gray-400 mt-0.5">{activePackage.id} — {activePackage.dateFrom} to {activePackage.dateTo}</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={<ArrowDownTrayIcon className="h-4 w-4" />}
                    onClick={() => handleExportPackage(activePackage)}
                  >
                    Export JSON
                  </Button>
                  <button
                    onClick={() => setActivePackageId(null)}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <XCircleIcon className="h-5 w-5" />
                  </button>
                </div>
              </div>

              {/* Compliance Dashboard */}
              <div className="p-6">
                <div className="flex flex-col sm:flex-row gap-6 mb-6">
                  <div className="flex flex-col items-center justify-center">
                    <ComplianceGauge score={activePackage.overallComplianceScore} />
                    <div className="mt-2 text-xs text-gray-500 text-center">
                      Overall Compliance Score
                    </div>
                  </div>
                  <div className="flex-1 grid grid-cols-2 gap-3">
                    <div className="rounded-xl bg-gray-50/80 border border-gray-200/60 p-3">
                      <div className="text-2xl font-bold text-gray-900">
                        {(activePackage.totalItems ?? 0).toLocaleString()}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">Total Audit Items</div>
                    </div>
                    <div className="rounded-xl bg-gray-50/80 border border-gray-200/60 p-3">
                      <div className="text-2xl font-bold text-gray-900">
                        {activePackage.results.length}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">Categories Covered</div>
                    </div>
                    <div className="rounded-xl bg-gray-50/80 border border-gray-200/60 p-3">
                      <div className="text-2xl font-bold text-gray-900">
                        {activePackage.results.filter((r) => r.complianceScore >= 90).length}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">Categories Passing</div>
                    </div>
                    <div className="rounded-xl bg-gray-50/80 border border-gray-200/60 p-3">
                      <div className="text-2xl font-bold text-red-700">
                        {activePackage.results.filter((r) => r.complianceScore < 75).length}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">Categories At Risk</div>
                    </div>
                  </div>
                </div>

                {/* Per-Category Results */}
                <div className="space-y-3">
                  {activePackage.results.map((result) => (
                    <div
                      key={result.category}
                      className="rounded-xl border border-gray-200/60 overflow-hidden"
                    >
                      <div className="px-4 py-3 bg-gray-50/60 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-gray-800">{result.label}</span>
                          <Badge variant="neutral" size="sm">
                            {(result.itemCount ?? 0).toLocaleString()} items
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-20 bg-gray-200/60 rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full transition-all duration-500 ${scoreBarColor(result.complianceScore)}`}
                              style={{ width: `${result.complianceScore}%` }}
                            />
                          </div>
                          <span className={`text-xs font-bold ${scoreColor(result.complianceScore)}`}>
                            {result.complianceScore}%
                          </span>
                        </div>
                      </div>
                      <div className="px-4 py-3 space-y-1.5">
                        {result.keyFindings.map((finding, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs text-gray-600">
                            {result.complianceScore >= 90 ? (
                              <CheckCircleIcon className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                            ) : (
                              <ExclamationTriangleIcon className="h-3.5 w-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                            )}
                            {finding}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          ) : (
            <Card padding="lg">
              <div className="text-center py-10">
                <DocumentCheckIcon className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-sm font-medium text-gray-500">No package selected</p>
                <p className="text-xs text-gray-400 mt-1">
                  Generate a new evidence package or select one from the history below
                </p>
                <Button
                  size="sm"
                  className="mt-4"
                  onClick={handleGenerate}
                  loading={generateMutation.isPending}
                  disabled={selectedCategories.size === 0}
                >
                  Generate Now
                </Button>
              </div>
            </Card>
          )}

          {/* Package History */}
          <Card padding="none">
            <div className="px-6 py-4 border-b border-white/20">
              <h2 className="text-sm font-semibold text-gray-900">Package History</h2>
            </div>
            <div className="divide-y divide-gray-100/60">
              {packages.length === 0 && (
                <div className="py-10 text-center">
                  <FolderOpenIcon className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-400">No packages generated yet</p>
                </div>
              )}
              {packages.map((pkg) => (
                <div
                  key={pkg.id}
                  onClick={() => setActivePackageId(pkg.id === activePackageId ? null : pkg.id)}
                  className={`px-6 py-4 flex items-center justify-between gap-4 cursor-pointer transition-colors ${
                    activePackageId === pkg.id
                      ? 'bg-primary-50/50'
                      : 'hover:bg-gray-50/60'
                  }`}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-mono font-semibold text-gray-900">{pkg.id}</span>
                      <Badge
                        variant={
                          pkg.status === 'complete'
                            ? 'success'
                            : pkg.status === 'generating'
                            ? 'info'
                            : 'danger'
                        }
                        size="sm"
                      >
                        {pkg.status === 'complete'
                          ? 'Complete'
                          : pkg.status === 'generating'
                          ? 'Generating'
                          : 'Failed'}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-[10px] text-gray-400">
                      <span className="flex items-center gap-1">
                        <CalendarDaysIcon className="h-3 w-3" />
                        {pkg.dateFrom} to {pkg.dateTo}
                      </span>
                      <span className="flex items-center gap-1">
                        <ClockIcon className="h-3 w-3" />
                        {pkg.generatedAt}
                      </span>
                      <span>{(pkg.totalItems ?? 0).toLocaleString()} items</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <div className="text-center">
                      <div className={`text-lg font-bold ${scoreColor(pkg.overallComplianceScore)}`}>
                        {pkg.overallComplianceScore}%
                      </div>
                      <div className="text-[10px] text-gray-400">Compliance</div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleExportPackage(pkg);
                      }}
                      className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                      title="Export package"
                    >
                      <ArrowDownTrayIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
