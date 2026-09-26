import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowPathIcon,
  ArrowUpIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentTextIcon,
  ShieldExclamationIcon,
  WrenchScrewdriverIcon,
  ListBulletIcon,
  ClipboardDocumentListIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  RiskBadge,
  Table,
  Select,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';

// ── Types ──────────────────────────────────────────────────────────────────────

interface SapVersion {
  id: string;
  label: string;
  release_date?: string;
  eol_date?: string;
}

interface AffectedRole {
  role_id: string;
  role_name: string;
  impact: 'deprecated_objects' | 'new_requirements' | 'behavior_change' | 'no_change';
  objects_affected: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  action_required: string;
}

interface DeprecatedObject {
  object_id: string;
  object_type: string;
  description: string;
  replacement?: string;
  replacement_notes?: string;
  affects_roles: number;
}

interface NewRequirement {
  id: string;
  description: string;
  affected_area: string;
  implementation_steps: string[];
  risk_if_ignored: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
}

interface UpgradeAnalysisResult {
  from_version: string;
  to_version: string;
  overall_risk: 'low' | 'medium' | 'high' | 'critical';
  affected_roles_count: number;
  deprecated_objects_count: number;
  new_requirements_count: number;
  estimated_effort_days: number;
  affected_roles: AffectedRole[];
  deprecated_objects: DeprecatedObject[];
  new_requirements: NewRequirement[];
  summary: string;
}

interface RemediationPlan {
  phases: {
    phase: number;
    name: string;
    duration_days: number;
    tasks: string[];
    owner: string;
  }[];
  total_duration_days: number;
  prerequisites: string[];
}

// ── Impact badge config ───────────────────────────────────────────────────────

const IMPACT_LABELS: Record<AffectedRole['impact'], { label: string; variant: 'danger' | 'warning' | 'info' | 'neutral' }> = {
  deprecated_objects: { label: 'Deprecated Objects', variant: 'danger' },
  new_requirements: { label: 'New Requirements', variant: 'warning' },
  behavior_change: { label: 'Behavior Change', variant: 'info' },
  no_change: { label: 'No Change', variant: 'neutral' },
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100/80 text-red-700 border-red-200/50',
  high: 'bg-orange-100/80 text-orange-700 border-orange-200/50',
  medium: 'bg-amber-100/80 text-amber-700 border-amber-200/50',
  low: 'bg-green-100/80 text-green-700 border-green-200/50',
};

// ── Component ─────────────────────────────────────────────────────────────────

export function UpgradeAnalyzer() {
  const [fromVersion, setFromVersion] = useState('');
  const [toVersion, setToVersion] = useState('');
  const [result, setResult] = useState<UpgradeAnalysisResult | null>(null);
  const [remediationPlan, setRemediationPlan] = useState<RemediationPlan | null>(null);
  const [activeSection, setActiveSection] = useState<'roles' | 'deprecated' | 'requirements'>('roles');

  // ── Versions query ────────────────────────────────────────────────────────
  const { data: versionsData } = useQuery<SapVersion[]>({
    queryKey: ['upgrade-versions'],
    queryFn: () => api.get('/upgrade/versions').then((r) => r.data),
  });

  const versions: SapVersion[] = versionsData ?? [];
  const versionOptions = [
    { value: '', label: 'Select version...' },
    ...versions.map((v) => ({ value: v.id, label: v.label })),
  ];

  // ── Analyze mutation ──────────────────────────────────────────────────────
  const analyzeMutation = useMutation({
    mutationFn: (payload: { from_version: string; to_version: string }) =>
      api.post('/upgrade/analyze', payload).then((r) => r.data as UpgradeAnalysisResult),
    onSuccess: (data) => {
      setResult(data);
      setRemediationPlan(null);
      toast.success('Impact analysis complete');
    },
    onError: () => {
      toast.error('Analysis failed');
    },
  });

  // ── Remediation plan mutation ─────────────────────────────────────────────
  const remediationMutation = useMutation({
    mutationFn: (payload: { from_version: string; to_version: string }) =>
      api.get('/upgrade/remediation-plan', { params: payload }).then((r) => r.data as RemediationPlan),
    onSuccess: (data) => {
      setRemediationPlan(data);
      toast.success('Remediation plan loaded');
    },
    onError: () => {
      toast.error('Failed to load remediation plan');
    },
  });

  const handleAnalyze = () => {
    if (!fromVersion || !toVersion) {
      toast.error('Select both source and target versions');
      return;
    }
    if (fromVersion === toVersion) {
      toast.error('Source and target versions must differ');
      return;
    }
    analyzeMutation.mutate({ from_version: fromVersion, to_version: toVersion });
  };

  const handleLoadPlan = () => {
    remediationMutation.mutate({ from_version: fromVersion, to_version: toVersion });
  };

  // ── Table columns ─────────────────────────────────────────────────────────
  const rolesColumns = [
    {
      key: 'role',
      header: 'Role',
      render: (r: AffectedRole) => (
        <div>
          <p className="text-sm font-medium text-gray-900">{r.role_name}</p>
          <p className="text-xs text-gray-400 font-mono">{r.role_id}</p>
        </div>
      ),
    },
    {
      key: 'impact',
      header: 'Impact Type',
      render: (r: AffectedRole) => {
        const cfg = IMPACT_LABELS[r.impact];
        return <Badge variant={cfg.variant} size="sm">{cfg.label}</Badge>;
      },
    },
    {
      key: 'objects',
      header: 'Objects',
      render: (r: AffectedRole) => (
        <span className="text-sm text-gray-700">{r.objects_affected}</span>
      ),
    },
    {
      key: 'risk',
      header: 'Risk',
      render: (r: AffectedRole) => <RiskBadge level={r.risk_level} />,
    },
    {
      key: 'action',
      header: 'Action Required',
      render: (r: AffectedRole) => (
        <p className="text-xs text-gray-600 max-w-xs">{r.action_required}</p>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Upgrade Impact Analyzer"
        subtitle="Assess SAP security impact before a version upgrade"
        breadcrumbs={[{ label: 'Intelligence' }, { label: 'Upgrade Analyzer' }]}
      />

      {/* Version selector */}
      <Card>
        <div className="px-6 py-4 border-b border-white/20">
          <h2 className="text-sm font-semibold text-gray-900">Version Selection</h2>
        </div>
        <div className="p-6">
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1">
              <Select
                label="From Version"
                value={fromVersion}
                onChange={(e) => { setFromVersion(e.target.value); setResult(null); }}
                options={versionOptions}
              />
            </div>
            <div className="flex items-center pb-2.5">
              <ArrowUpIcon className="h-5 w-5 text-gray-400 rotate-90" />
            </div>
            <div className="flex-1">
              <Select
                label="To Version"
                value={toVersion}
                onChange={(e) => { setToVersion(e.target.value); setResult(null); }}
                options={versionOptions}
              />
            </div>
            <Button
              onClick={handleAnalyze}
              loading={analyzeMutation.isPending}
              disabled={!fromVersion || !toVersion}
              icon={<ArrowPathIcon className="h-4 w-4" />}
            >
              Analyze Impact
            </Button>
          </div>
          {fromVersion && toVersion && fromVersion !== toVersion && (
            <p className="mt-2 text-xs text-gray-400">
              Analyzing upgrade path from{' '}
              <span className="font-medium text-gray-600">
                {versions.find((v) => v.id === fromVersion)?.label}
              </span>{' '}
              to{' '}
              <span className="font-medium text-gray-600">
                {versions.find((v) => v.id === toVersion)?.label}
              </span>
            </p>
          )}
        </div>
      </Card>

      {/* Results */}
      {result && (
        <>
          {/* Summary stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Affected Roles"
              value={result.affected_roles_count}
              icon={ShieldExclamationIcon}
              iconBgColor="stat-icon-orange"
              iconColor=""
            />
            <StatCard
              title="Deprecated Objects"
              value={result.deprecated_objects_count}
              icon={XCircleIcon}
              iconBgColor="stat-icon-red"
              iconColor=""
            />
            <StatCard
              title="New Requirements"
              value={result.new_requirements_count}
              icon={ListBulletIcon}
              iconBgColor="stat-icon-blue"
              iconColor=""
            />
            <StatCard
              title="Effort (days)"
              value={result.estimated_effort_days}
              icon={ClipboardDocumentListIcon}
              iconBgColor="stat-icon-yellow"
              iconColor=""
            />
          </div>

          {/* Summary banner */}
          <div
            className={`p-4 rounded-xl border text-sm ${
              result.overall_risk === 'critical'
                ? 'bg-red-50/60 border-red-200/60 text-red-800'
                : result.overall_risk === 'high'
                ? 'bg-orange-50/60 border-orange-200/60 text-orange-800'
                : 'bg-amber-50/60 border-amber-200/60 text-amber-800'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <ExclamationTriangleIcon className="h-4 w-4 flex-shrink-0" />
              <span className="font-semibold">
                Overall Risk:{' '}
                <span className="uppercase">{result.overall_risk}</span>
              </span>
            </div>
            <p className="leading-relaxed">{result.summary}</p>
          </div>

          {/* Section tabs */}
          <div className="flex gap-2">
            {(['roles', 'deprecated', 'requirements'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveSection(tab)}
                className={`px-4 py-2 text-xs font-semibold rounded-xl transition-all duration-200 border ${
                  activeSection === tab
                    ? 'bg-primary-600 text-white border-primary-600 shadow-md'
                    : 'bg-white/50 text-gray-600 border-white/40 hover:bg-white/70'
                }`}
              >
                {tab === 'roles' && `Affected Roles (${result.affected_roles_count})`}
                {tab === 'deprecated' && `Deprecated Objects (${result.deprecated_objects_count})`}
                {tab === 'requirements' && `New Requirements (${result.new_requirements_count})`}
              </button>
            ))}
          </div>

          {/* Affected roles */}
          {activeSection === 'roles' && (
            <Table
              columns={rolesColumns}
              data={result.affected_roles}
              emptyMessage="No affected roles"
            />
          )}

          {/* Deprecated objects */}
          {activeSection === 'deprecated' && (
            <div className="space-y-3">
              {result.deprecated_objects.map((obj) => (
                <Card key={obj.object_id} padding="md">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-sm font-semibold text-red-700">{obj.object_id}</span>
                        <Badge variant="neutral" size="sm">{obj.object_type}</Badge>
                        <Badge variant="danger" size="sm">{obj.affects_roles} roles affected</Badge>
                      </div>
                      <p className="text-sm text-gray-700">{obj.description}</p>
                    </div>
                    {obj.replacement && (
                      <div className="flex-shrink-0 text-right">
                        <p className="text-xs text-gray-400 uppercase tracking-wider">Replacement</p>
                        <p className="font-mono text-sm font-semibold text-emerald-700">{obj.replacement}</p>
                      </div>
                    )}
                  </div>
                  {obj.replacement_notes && (
                    <div className="mt-3 pt-3 border-t border-white/20">
                      <p className="text-xs text-gray-500">
                        <span className="font-medium text-gray-600">Migration note: </span>
                        {obj.replacement_notes}
                      </p>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}

          {/* New requirements */}
          {activeSection === 'requirements' && (
            <div className="space-y-4">
              {result.new_requirements.map((req) => (
                <Card key={req.id} padding="none">
                  <div className="px-5 py-4 border-b border-white/20 flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-gray-400 font-mono">{req.id}</span>
                        <Badge variant="neutral" size="sm">{req.affected_area}</Badge>
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${PRIORITY_COLORS[req.priority]}`}
                        >
                          {req.priority.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-gray-900">{req.description}</p>
                    </div>
                  </div>
                  <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Implementation Steps</p>
                      <ol className="space-y-1.5">
                        {req.implementation_steps.map((step, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                            <span className="flex-shrink-0 h-4 w-4 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-[10px] font-bold mt-0.5">
                              {i + 1}
                            </span>
                            {step}
                          </li>
                        ))}
                      </ol>
                    </div>
                    <div className="p-3 bg-amber-50/60 border border-amber-200/60 rounded-xl h-fit">
                      <p className="text-xs font-semibold text-amber-700 uppercase tracking-wider mb-1">Risk if Ignored</p>
                      <p className="text-xs text-amber-800">{req.risk_if_ignored}</p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* Remediation plan */}
          <Card>
            <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-gray-900">Remediation Plan</h2>
                <p className="text-xs text-gray-500 mt-0.5">Phased implementation plan for the upgrade</p>
              </div>
              {!remediationPlan && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleLoadPlan}
                  loading={remediationMutation.isPending}
                  icon={<DocumentTextIcon className="h-4 w-4" />}
                >
                  Load Plan
                </Button>
              )}
            </div>
            {remediationPlan ? (
              <div className="p-6 space-y-5">
                {/* Prerequisites */}
                <div>
                  <p className="text-xs font-medium text-gray-600 uppercase tracking-wider mb-2">Prerequisites</p>
                  <ul className="space-y-1.5">
                    {remediationPlan.prerequisites.map((p, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                        <CheckCircleIcon className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Phases */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-xs font-medium text-gray-600 uppercase tracking-wider">Phases</p>
                    <Badge variant="info" size="sm">Total: {remediationPlan.total_duration_days} days</Badge>
                  </div>
                  <div className="space-y-3">
                    {remediationPlan.phases.map((phase) => (
                      <div key={phase.phase} className="p-4 bg-white/40 backdrop-blur-sm rounded-xl border border-white/30">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="h-6 w-6 rounded-full bg-primary-600 text-white text-xs font-bold flex items-center justify-center">
                              {phase.phase}
                            </span>
                            <span className="text-sm font-semibold text-gray-900">{phase.name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="neutral" size="sm">{phase.owner}</Badge>
                            <Badge variant="info" size="sm">{phase.duration_days}d</Badge>
                          </div>
                        </div>
                        <ul className="space-y-1 mt-2">
                          {phase.tasks.map((task, i) => (
                            <li key={i} className="flex items-start gap-1.5 text-xs text-gray-500">
                              <WrenchScrewdriverIcon className="h-3 w-3 text-gray-400 flex-shrink-0 mt-0.5" />
                              {task}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-6 text-center">
                <ClipboardDocumentListIcon className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-400">Click Load Plan to fetch the phased remediation plan for this upgrade</p>
              </div>
            )}
          </Card>
        </>
      )}

      {/* Empty state */}
      {!result && !analyzeMutation.isPending && (
        <Card>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <ArrowUpIcon className="h-12 w-12 text-gray-300 mb-4" />
            <h3 className="text-sm font-medium text-gray-700 mb-1">No Analysis Yet</h3>
            <p className="text-xs text-gray-400 max-w-xs">
              Select a source and target SAP version above and click Analyze Impact to see the full security impact assessment.
            </p>
          </div>
        </Card>
      )}

      {analyzeMutation.isPending && (
        <Card>
          <div className="flex flex-col items-center justify-center py-16">
            <ArrowPathIcon className="h-10 w-10 text-primary-500 animate-spin mb-4" />
            <p className="text-sm text-gray-600">Analyzing upgrade impact...</p>
            <p className="text-xs text-gray-400 mt-1">Checking roles, auth objects, and transport history</p>
          </div>
        </Card>
      )}
    </div>
  );
}
