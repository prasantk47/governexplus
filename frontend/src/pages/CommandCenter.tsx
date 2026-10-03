/**
 * Governex+ Command Center
 * AI-native GRC home screen — "Tell me what is wrong, why it matters, and what I should do next"
 */
import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  SparklesIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  DocumentMagnifyingGlassIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ArrowRightIcon,
  BoltIcon,
  ClockIcon,
  KeyIcon,
  ChartBarIcon,
  CpuChipIcon,
  ClipboardDocumentCheckIcon,
  XMarkIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import {
  ExclamationCircleIcon,
  ExclamationTriangleIcon as SolidWarningIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/solid';
import {
  intelligenceApi,
  AttentionItem,
  FixPreview,
} from '../services/intelligenceApi';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardHeader } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

// ─── Mocked fallback data (used while backend endpoint is being built) ──────────

const MOCK_HEALTH: import('../services/intelligenceApi').HealthScore = {
  overall: 86,
  trend: 4,
  trend_label: 'from last month',
  components: { access: 78, controls: 91, risk: 82, audit: 88 },
  narrative: 'Your organization is generally healthy with minor access conflicts requiring attention.',
};

const MOCK_ATTENTION: AttentionItem[] = [
  {
    id: 'a1',
    severity: 'critical',
    title: 'Critical access conflict detected',
    description: 'User JSMITH holds conflicting roles: AP Clerk + Payment Approver in SAP ECC.',
    action_label: 'Fix',
    action_type: 'fix',
    object_type: 'sod_violation',
    object_id: 'VIO-2024-001',
    link: '/risk/violations',
  },
  {
    id: 'a2',
    severity: 'critical',
    title: 'Payment control failed last execution',
    description: 'Automated control "Vendor Bank Account Change" did not run on schedule. Last success: 3 days ago.',
    action_label: 'Review',
    action_type: 'review',
    link: '/process-control/testing',
  },
  {
    id: 'a3',
    severity: 'high',
    title: 'Audit finding overdue by 12 days',
    description: 'Finding #AF-089 "Segregation of Duties in Payroll" requires management response by Jan 14.',
    action_label: 'Escalate',
    action_type: 'escalate',
    link: '/audit-management/findings',
    due_in: '12 days overdue',
  },
  {
    id: 'a4',
    severity: 'high',
    title: 'KRI breach: Open violations exceed threshold',
    description: '47 open SoD violations vs. target of 30. Trend worsening over 2 weeks.',
    action_label: 'Investigate',
    action_type: 'investigate',
    link: '/risk-management/kri',
    object_type: 'kri',
    object_id: 'KRI-SOD-001',
  },
  {
    id: 'a5',
    severity: 'medium',
    title: '8 access certifications expiring soon',
    description: 'Campaign "Q1 2026 Access Review" closes in 5 days. 8 items still pending review.',
    action_label: 'Review',
    action_type: 'review',
    link: '/certification/review',
    due_in: '5 days',
  },
  {
    id: 'a6',
    severity: 'medium',
    title: 'Privileged access session without post-activity log',
    description: 'Emergency access session FF-338 (MRODRIGUEZ, Jan 28) is missing its mandatory log entry.',
    action_label: 'Review',
    action_type: 'review',
    link: '/privileged-access/sessions',
  },
  {
    id: 'a7',
    severity: 'low',
    title: '14 dormant accounts still active',
    description: '14 user accounts have had no login in 90+ days. Review for deprovisioning.',
    action_label: 'Investigate',
    action_type: 'investigate',
    link: '/users/inactive',
  },
];

const MOCK_INSIGHTS: import('../services/intelligenceApi').Insight[] = [
  {
    id: 'i1',
    title: 'Vendor payment risk spike',
    narrative:
      'Vendor payment risk increased 23% this week. I found 3 related access issues — 2 users with excessive AP permissions — and 2 failed automated controls. This pattern often precedes audit findings.',
    severity: 'high',
    trend: '+23%',
    related_count: 5,
    category: 'Risk',
  },
  {
    id: 'i2',
    title: 'Role cleanup opportunity identified',
    narrative:
      '31 users hold roles they have never exercised in 6+ months. Removing them would reduce your SoD exposure by an estimated 18% and simplify your next access certification cycle.',
    severity: 'medium',
    trend: '-18% projected',
    related_count: 31,
    category: 'Access',
  },
  {
    id: 'i3',
    title: 'Control testing cadence is ahead of schedule',
    narrative:
      'Your team completed 94% of Q1 control tests — 8 days early. Only 3 controls remain. If the current pace holds, you are on track for a clean SOX opinion this quarter.',
    severity: 'info',
    trend: '94% complete',
    related_count: 3,
    category: 'Controls',
  },
];

const MOCK_MODULE_STATS = [
  {
    label: 'Access Risk',
    value: 23,
    trend: 3,
    link: '/risk/violations',
    color: 'red',
    icon: ExclamationTriangleIcon,
    sub: 'open violations',
  },
  {
    label: 'Control Health',
    value: '91%',
    trend: -2,
    link: '/process-control/ccm',
    color: 'emerald',
    icon: ShieldCheckIcon,
    sub: 'passing',
  },
  {
    label: 'Enterprise Risk',
    value: 72,
    trend: 5,
    link: '/risk-management/register',
    color: 'amber',
    icon: ChartBarIcon,
    sub: 'risk score',
  },
  {
    label: 'Audit Status',
    value: 12,
    trend: 0,
    link: '/audit-management/findings',
    color: 'blue',
    icon: ClipboardDocumentCheckIcon,
    sub: 'open findings',
  },
];

const MOCK_ACTIVITY = [
  { id: '1', timestamp: '2 min ago', actor: 'J. Smith', action: 'Approved', object: 'Access request AR-1204', module: 'Access' },
  { id: '2', timestamp: '18 min ago', actor: 'System', action: 'Detected', object: 'SoD violation VIO-2024-001', module: 'Risk' },
  { id: '3', timestamp: '1 hr ago', actor: 'M. Rodriguez', action: 'Completed', object: 'Control test CT-0882', module: 'Controls' },
  { id: '4', timestamp: '2 hrs ago', actor: 'A. Patel', action: 'Submitted', object: 'Certification review CR-056', module: 'Cert' },
  { id: '5', timestamp: '4 hrs ago', actor: 'System', action: 'Generated', object: 'KRI report KRI-SOD-001', module: 'Risk' },
];

const SUGGESTION_CHIPS = [
  'What should I worry about?',
  'Show my top risks',
  'Which controls are failing?',
  'Overdue findings',
];

// ─── Sub-components ──────────────────────────────────────────────────────────

interface CircularProgressProps {
  score: number;
  size?: number;
  strokeWidth?: number;
}

function CircularProgress({ score, size = 140, strokeWidth = 10 }: CircularProgressProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const color =
    score >= 80 ? '#6366f1' : score >= 60 ? '#f59e0b' : '#ef4444';
  const glowColor =
    score >= 80 ? '#818cf8' : score >= 60 ? '#fbbf24' : '#f87171';

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="transform -rotate-90 drop-shadow-lg"
    >
      <defs>
        <linearGradient id="ring-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={glowColor} />
          <stop offset="100%" stopColor={color} />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {/* Track */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-gray-200 dark:text-slate-700"
      />
      {/* Progress */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="url(#ring-gradient)"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        filter="url(#glow)"
        style={{ transition: 'stroke-dashoffset 1s ease-in-out' }}
      />
    </svg>
  );
}

function MiniBar({ value, label }: { value: number; label: string }) {
  const color =
    value >= 80
      ? 'bg-emerald-500'
      : value >= 60
      ? 'bg-amber-500'
      : 'bg-red-500';
  const textColor =
    value >= 80
      ? 'text-emerald-600 dark:text-emerald-400'
      : value >= 60
      ? 'text-amber-600 dark:text-amber-400'
      : 'text-red-600 dark:text-red-400';

  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-gray-500 dark:text-gray-400 w-14 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-gray-200 dark:bg-slate-700 overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-700`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className={`text-[11px] font-semibold w-7 text-right ${textColor}`}>{value}</span>
    </div>
  );
}

const SEVERITY_CONFIG = {
  critical: {
    icon: ExclamationCircleIcon,
    badgeVariant: 'danger' as const,
    bg: 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800/50',
    iconColor: 'text-red-500',
    label: 'Critical',
  },
  high: {
    icon: SolidWarningIcon,
    badgeVariant: 'danger' as const,
    bg: 'bg-orange-50 dark:bg-orange-900/10 border-orange-200 dark:border-orange-800/50',
    iconColor: 'text-orange-500',
    label: 'High',
  },
  medium: {
    icon: InformationCircleIcon,
    badgeVariant: 'warning' as const,
    bg: 'bg-amber-50 dark:bg-amber-900/10 border-amber-200 dark:border-amber-800/50',
    iconColor: 'text-amber-500',
    label: 'Medium',
  },
  low: {
    icon: InformationCircleIcon,
    badgeVariant: 'info' as const,
    bg: 'bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800/50',
    iconColor: 'text-blue-500',
    label: 'Low',
  },
};

const ACTION_CONFIG = {
  fix: { variant: 'danger' as const, icon: BoltIcon },
  review: { variant: 'secondary' as const, icon: DocumentMagnifyingGlassIcon },
  escalate: { variant: 'danger' as const, icon: ArrowTrendingUpIcon },
  investigate: { variant: 'secondary' as const, icon: MagnifyingGlassIcon },
};

interface FixModalProps {
  item: AttentionItem;
  preview: FixPreview | null;
  loading: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

function FixModal({ item, preview, loading, onConfirm, onClose }: FixModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg border border-gray-200 dark:border-slate-700 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700 bg-red-50 dark:bg-red-900/10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <BoltIcon className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Quick Fix Preview</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">Review before applying</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
          >
            <XMarkIcon className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-8 gap-3">
              <ArrowPathIcon className="h-5 w-5 animate-spin text-indigo-500" />
              <span className="text-sm text-gray-500 dark:text-gray-400">Analyzing fix options…</span>
            </div>
          ) : preview ? (
            <>
              <div>
                <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{preview.title}</p>
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{preview.description}</p>
              </div>

              <div className="rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 p-3.5">
                <p className="text-xs font-semibold text-amber-700 dark:text-amber-400 mb-1">Impact</p>
                <p className="text-sm text-amber-800 dark:text-amber-300">{preview.impact}</p>
              </div>

              {preview.steps && preview.steps.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Steps that will be taken:</p>
                  <ol className="space-y-1.5">
                    {preview.steps.map((step, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <span className="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 text-xs font-bold flex items-center justify-center">
                          {i + 1}
                        </span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 pt-1">
                <span>
                  Reversible: <span className={preview.reversible ? 'text-emerald-600 dark:text-emerald-400 font-semibold' : 'text-red-500 font-semibold'}>{preview.reversible ? 'Yes' : 'No'}</span>
                </span>
                <span>Effort: <span className="font-semibold text-gray-700 dark:text-gray-300">{preview.estimated_effort}</span></span>
              </div>
            </>
          ) : (
            <div className="py-4">
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{item.title}</p>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{item.description}</p>
              <p className="mt-3 text-xs text-gray-400 dark:text-gray-500">Fix preview is not available for this item. Proceeding will open the relevant module.</p>
            </div>
          )}
        </div>

        <div className="flex gap-3 px-6 pb-5">
          <Button variant="secondary" className="flex-1" onClick={onClose}>
            Cancel
          </Button>
          {preview ? (
            <Button variant="danger" className="flex-1" onClick={onConfirm} icon={<BoltIcon className="h-4 w-4" />}>
              Apply Fix
            </Button>
          ) : item.link ? (
            <Button variant="primary" href={item.link} className="flex-1" icon={<ArrowRightIcon className="h-4 w-4" />} iconPosition="right">
              Open Module
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function CommandCenter() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const searchRef = useRef<HTMLInputElement>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [fixModalItem, setFixModalItem] = useState<AttentionItem | null>(null);
  const [fixPreview, setFixPreview] = useState<FixPreview | null>(null);
  const [showAllAttention, setShowAllAttention] = useState(false);

  // Data queries — fall back to mock on error
  const { data: healthScore, isLoading: healthLoading } = useQuery({
    queryKey: ['grc-health-score'],
    queryFn: () => intelligenceApi.getHealthScore().then((r) => r.data ?? MOCK_HEALTH),
    placeholderData: MOCK_HEALTH,
    retry: false,
  });

  const { data: attentionItems, isLoading: attentionLoading } = useQuery({
    queryKey: ['grc-attention'],
    queryFn: () =>
      intelligenceApi.getAttentionItems({ role: user?.role }).then((r) => {
        const d = r.data;
        return Array.isArray(d) ? d : (d as any)?.items ?? [];
      }),
    placeholderData: MOCK_ATTENTION,
    retry: false,
  });

  const { data: insights, isLoading: insightsLoading } = useQuery({
    queryKey: ['grc-insights'],
    queryFn: () => intelligenceApi.getInsights().then((r) => {
      const d = r.data;
      return Array.isArray(d) ? d : (d as any)?.items ?? [];
    }),
    placeholderData: MOCK_INSIGHTS,
    retry: false,
  });

  // Fix preview mutation
  const fixPreviewMutation = useMutation({
    mutationFn: ({ objectType, objectId }: { objectType: string; objectId: string }) =>
      intelligenceApi.previewFix(objectType, objectId).then((r) => r.data),
    onSuccess: (data) => setFixPreview(data),
    onError: () => setFixPreview(null),
  });

  const quickFixMutation = useMutation({
    mutationFn: ({ objectType, objectId }: { objectType: string; objectId: string }) =>
      intelligenceApi.quickFix(objectType, objectId).then((r) => r.data),
    onSuccess: (data) => {
      toast.success(data.message || 'Fix applied successfully');
      setFixModalItem(null);
      setFixPreview(null);
    },
    onError: () => {
      toast.error('Fix could not be applied. Please open the module to proceed.');
      setFixModalItem(null);
    },
  });

  // Map API response shape to component's expected shape
  const rawHealth = healthScore || MOCK_HEALTH;
  const health = {
    overall: rawHealth.overall ?? rawHealth.overall_score ?? MOCK_HEALTH.overall,
    trend: (typeof rawHealth.trend === 'number' ? rawHealth.trend : MOCK_HEALTH.trend) as number,
    trend_label: (rawHealth as any).trend_label || 'from last assessment',
    narrative: (rawHealth as any).narrative || 'Your organization\'s GRC health is being monitored continuously.',
    components: rawHealth.components ?? {
      access: rawHealth.pillars?.access_control?.score ?? 78,
      controls: rawHealth.pillars?.process_control?.score ?? 91,
      risk: rawHealth.pillars?.risk_management?.score ?? 82,
      audit: rawHealth.pillars?.audit_management?.score ?? 88,
    },
  };
  const items: AttentionItem[] = attentionItems || MOCK_ATTENTION;
  const allInsights = insights || MOCK_INSIGHTS;

  // Sort attention items: critical first, then high, medium, low
  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
  const sortedItems = [...items].sort(
    (a, b) => severityOrder[a.severity] - severityOrder[b.severity]
  );
  const visibleItems = showAllAttention ? sortedItems : sortedItems.slice(0, 5);

  const handleFixClick = useCallback(
    (item: AttentionItem) => {
      setFixModalItem(item);
      setFixPreview(null);
      if (item.object_type && item.object_id) {
        fixPreviewMutation.mutate({ objectType: item.object_type, objectId: item.object_id });
      }
    },
    [fixPreviewMutation]
  );

  const handleFixConfirm = useCallback(() => {
    if (!fixModalItem) return;
    if (fixModalItem.object_type && fixModalItem.object_id) {
      quickFixMutation.mutate({
        objectType: fixModalItem.object_type,
        objectId: fixModalItem.object_id,
      });
    } else if (fixModalItem.link) {
      navigate(fixModalItem.link);
      setFixModalItem(null);
    }
  }, [fixModalItem, quickFixMutation, navigate]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/ai?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const handleChipClick = (chip: string) => {
    navigate(`/ai?q=${encodeURIComponent(chip)}`);
  };

  // Greeting based on time of day
  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const displayName = user?.name?.split(' ')[0] || 'there';

  const criticalCount = items.filter((i) => i.severity === 'critical').length;
  const highCount = items.filter((i) => i.severity === 'high').length;

  return (
    <div className="space-y-8 pb-12">
      {/* ── Hero Row: Greeting + Health Score ─────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600 via-indigo-700 to-indigo-900 shadow-xl shadow-indigo-900/30 p-6 sm:p-8">
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-20 -right-20 w-72 h-72 rounded-full bg-white/5 blur-3xl" />
          <div className="absolute bottom-0 left-1/3 w-64 h-64 rounded-full bg-indigo-500/20 blur-3xl" />
          <svg
            className="absolute top-0 right-0 w-64 h-64 text-white/[0.03]"
            fill="currentColor"
            viewBox="0 0 200 200"
          >
            <circle cx="150" cy="50" r="120" />
          </svg>
        </div>

        <div className="relative flex flex-col sm:flex-row items-start sm:items-center justify-between gap-8">
          {/* Greeting text */}
          <div className="flex-1 min-w-0">
            <p className="text-indigo-200 text-sm font-medium mb-1">{greeting},</p>
            <h1 className="text-3xl font-bold text-white tracking-tight">{displayName}</h1>
            <p className="mt-2 text-indigo-200 text-sm max-w-md leading-relaxed">
              {health.narrative || 'Your organization\'s GRC health is being monitored continuously.'}
            </p>

            {/* Alert summary pills */}
            <div className="flex flex-wrap gap-2 mt-4">
              {criticalCount > 0 && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-500/20 border border-red-400/30 text-red-200 text-xs font-semibold">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
                  {criticalCount} Critical
                </span>
              )}
              {highCount > 0 && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-orange-500/20 border border-orange-400/30 text-orange-200 text-xs font-semibold">
                  <span className="w-1.5 h-1.5 rounded-full bg-orange-400" />
                  {highCount} High
                </span>
              )}
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/30 border border-indigo-400/30 text-indigo-200 text-xs font-semibold">
                {items.length} total items need attention
              </span>
            </div>
          </div>

          {/* Health Score Ring */}
          <div className="flex flex-col items-center gap-4 shrink-0">
            <div className="relative">
              {healthLoading ? (
                <div className="w-[140px] h-[140px] rounded-full bg-white/10 animate-pulse" />
              ) : (
                <CircularProgress score={health.overall} size={140} strokeWidth={10} />
              )}
              {/* Center label */}
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-4xl font-bold text-white leading-none">{health.overall}</span>
                <span className="text-indigo-200 text-xs font-medium mt-0.5">GRC Health</span>
              </div>
            </div>

            {/* Trend badge */}
            <div className="flex items-center gap-1.5 text-sm">
              {health.trend >= 0 ? (
                <ArrowTrendingUpIcon className="h-4 w-4 text-emerald-300" />
              ) : (
                <ArrowTrendingDownIcon className="h-4 w-4 text-red-300" />
              )}
              <span className={health.trend >= 0 ? 'text-emerald-300 font-semibold' : 'text-red-300 font-semibold'}>
                {health.trend >= 0 ? '+' : ''}{health.trend}%
              </span>
              <span className="text-indigo-300 text-xs">{health.trend_label || 'from last assessment'}</span>
            </div>

            {/* Component bars */}
            <div className="w-48 space-y-2 bg-white/10 rounded-xl px-4 py-3">
              <MiniBar value={health.components.access} label="Access" />
              <MiniBar value={health.components.controls} label="Controls" />
              <MiniBar value={health.components.risk} label="Risk" />
              <MiniBar value={health.components.audit} label="Audit" />
            </div>
          </div>
        </div>
      </div>

      {/* ── Main Grid ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left column — spans 2 on xl */}
        <div className="xl:col-span-2 space-y-6">

          {/* ── Attention Section ─────────────────────────── */}
          <Card padding="none" className="overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-slate-700">
              <div className="flex items-center gap-2.5">
                {criticalCount > 0 && (
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
                  </span>
                )}
                <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                  {items.length} {items.length === 1 ? 'thing needs' : 'things need'} your attention
                </h2>
              </div>
              {attentionLoading && (
                <ArrowPathIcon className="h-4 w-4 text-gray-400 animate-spin" />
              )}
            </div>

            {/* Items */}
            <div className="divide-y divide-gray-100 dark:divide-slate-700/60">
              {visibleItems.map((item) => {
                const sev = SEVERITY_CONFIG[item.severity] || SEVERITY_CONFIG['medium'] || Object.values(SEVERITY_CONFIG)[0];
                const act = ACTION_CONFIG[item.action_type] || ACTION_CONFIG['review'] || Object.values(ACTION_CONFIG)[0];
                if (!sev || !act) return null;
                const SevIcon = sev.icon;
                const ActIcon = act.icon;

                return (
                  <div
                    key={item.id}
                    className="flex items-start gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-slate-700/30 transition-colors group"
                  >
                    {/* Severity icon */}
                    <div className={`mt-0.5 shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${sev.bg}`}>
                      <SevIcon className={`h-4 w-4 ${sev.iconColor}`} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <Badge variant={sev.badgeVariant} size="sm">{sev.label}</Badge>
                        {item.due_in && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-gray-400 dark:text-gray-500">
                            <ClockIcon className="h-3 w-3" />
                            {item.due_in}
                          </span>
                        )}
                      </div>
                      <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 leading-snug">
                        {item.title}
                      </p>
                      <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400 leading-relaxed line-clamp-2">
                        {item.description}
                      </p>
                    </div>

                    {/* Action button */}
                    <div className="shrink-0 flex items-center gap-2 opacity-70 group-hover:opacity-100 transition-opacity">
                      {item.action_type === 'fix' ? (
                        <Button
                          variant={act.variant}
                          size="sm"
                          icon={<ActIcon className="h-3.5 w-3.5" />}
                          onClick={() => handleFixClick(item)}
                        >
                          {item.action_label}
                        </Button>
                      ) : (
                        <Button
                          variant={act.variant}
                          size="sm"
                          href={item.link}
                          icon={<ActIcon className="h-3.5 w-3.5" />}
                        >
                          {item.action_label}
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Show more / less */}
            {sortedItems.length > 5 && (
              <div className="px-5 py-3 border-t border-gray-100 dark:border-slate-700/60 bg-gray-50 dark:bg-slate-800/50">
                <button
                  onClick={() => setShowAllAttention(!showAllAttention)}
                  className="text-sm text-indigo-600 dark:text-indigo-400 font-medium hover:underline flex items-center gap-1"
                >
                  {showAllAttention ? (
                    <>Show less</>
                  ) : (
                    <>Show {sortedItems.length - 5} more items <ArrowRightIcon className="h-3.5 w-3.5" /></>
                  )}
                </button>
              </div>
            )}
          </Card>

          {/* ── Ask GRC AI ────────────────────────────────── */}
          <Card padding="lg" className="relative overflow-hidden">
            {/* Background sparkle */}
            <div className="absolute top-0 right-0 w-48 h-48 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

            <div className="relative">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-7 h-7 rounded-lg bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center">
                  <SparklesIcon className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                </div>
                <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Ask anything about GRC</h2>
              </div>

              <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative flex-1">
                  <SparklesIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-indigo-400 pointer-events-none" />
                  <input
                    ref={searchRef}
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="What are my biggest risks this week?"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700/50 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500 transition-all"
                  />
                </div>
                <Button
                  type="submit"
                  variant="primary"
                  icon={<ArrowRightIcon className="h-4 w-4" />}
                  iconPosition="right"
                >
                  Ask
                </Button>
              </form>

              {/* Suggestion chips */}
              <div className="flex flex-wrap gap-2 mt-3">
                {SUGGESTION_CHIPS.map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => handleChipClick(chip)}
                    className="text-xs px-3 py-1.5 rounded-full border border-gray-200 dark:border-slate-600 text-gray-600 dark:text-gray-300 hover:border-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-all font-medium"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          </Card>

          {/* ── Module Stat Tiles ─────────────────────────── */}
          <div>
            <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3 px-0.5">
              Quick Access
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {MOCK_MODULE_STATS.map((stat) => {
                const Icon = stat.icon;
                const colorMap: Record<string, { bg: string; icon: string; text: string }> = {
                  red: {
                    bg: 'bg-red-100 dark:bg-red-900/30',
                    icon: 'text-red-600 dark:text-red-400',
                    text: 'text-red-700 dark:text-red-300',
                  },
                  emerald: {
                    bg: 'bg-emerald-100 dark:bg-emerald-900/30',
                    icon: 'text-emerald-600 dark:text-emerald-400',
                    text: 'text-emerald-700 dark:text-emerald-300',
                  },
                  amber: {
                    bg: 'bg-amber-100 dark:bg-amber-900/30',
                    icon: 'text-amber-600 dark:text-amber-400',
                    text: 'text-amber-700 dark:text-amber-300',
                  },
                  blue: {
                    bg: 'bg-blue-100 dark:bg-blue-900/30',
                    icon: 'text-blue-600 dark:text-blue-400',
                    text: 'text-blue-700 dark:text-blue-300',
                  },
                };
                const c = colorMap[stat.color] || colorMap.blue;

                return (
                  <a
                    key={stat.label}
                    href={stat.link}
                    onClick={(e) => { e.preventDefault(); navigate(stat.link); }}
                    className="group block"
                  >
                    <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-4 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer">
                      <div className={`w-9 h-9 rounded-lg ${c.bg} flex items-center justify-center mb-3`}>
                        <Icon className={`h-5 w-5 ${c.icon}`} />
                      </div>
                      <div className="flex items-end justify-between">
                        <div>
                          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 leading-none">{stat.value}</p>
                          <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">{stat.sub}</p>
                        </div>
                        {stat.trend !== 0 && (
                          <span className={`flex items-center text-xs font-semibold ${stat.trend > 0 ? 'text-red-500' : 'text-emerald-500'}`}>
                            {stat.trend > 0 ? <ArrowTrendingUpIcon className="h-3.5 w-3.5" /> : <ArrowTrendingDownIcon className="h-3.5 w-3.5" />}
                            {Math.abs(stat.trend)}%
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-xs font-semibold text-gray-700 dark:text-gray-300 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                        {stat.label}
                      </p>
                    </div>
                  </a>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right column ──────────────────────────────────────────────── */}
        <div className="space-y-6">

          {/* ── AI Insights ──────────────────────────────── */}
          <Card padding="none" className="overflow-hidden">
            <div className="flex items-center gap-2.5 px-5 py-4 border-b border-gray-200 dark:border-slate-700 bg-gradient-to-r from-indigo-50 dark:from-indigo-900/20 to-transparent">
              <div className="w-7 h-7 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center">
                <CpuChipIcon className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">AI Insights</h2>
                <p className="text-[11px] text-gray-500 dark:text-gray-400">Updated just now</p>
              </div>
            </div>

            <div className="divide-y divide-gray-100 dark:divide-slate-700/60">
              {insightsLoading
                ? Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="px-5 py-4 space-y-2 animate-pulse">
                      <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-3/4" />
                      <div className="h-3 bg-gray-100 dark:bg-slate-700/50 rounded w-full" />
                      <div className="h-3 bg-gray-100 dark:bg-slate-700/50 rounded w-5/6" />
                    </div>
                  ))
                : allInsights.slice(0, 3).map((insight: any) => {
                    const severityColors: Record<string, string> = {
                      critical: 'border-red-400',
                      high: 'border-orange-400',
                      medium: 'border-amber-400',
                      info: 'border-indigo-400',
                    };
                    const borderColor = severityColors[insight.severity || 'info'];

                    return (
                      <div
                        key={insight.id}
                        className={`px-5 py-4 border-l-4 ${borderColor} hover:bg-gray-50 dark:hover:bg-slate-700/20 transition-colors`}
                      >
                        <div className="flex items-start justify-between gap-2 mb-1.5">
                          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 leading-snug">
                            {insight.title}
                          </p>
                          {insight.trend && (
                            <span className="shrink-0 text-[11px] font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 px-2 py-0.5 rounded-full whitespace-nowrap">
                              {insight.trend}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                          {insight.narrative}
                        </p>
                        <div className="mt-3 flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            href="/ai"
                            icon={<MagnifyingGlassIcon className="h-3.5 w-3.5" />}
                            className="text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20"
                          >
                            Investigate
                          </Button>
                          {insight.related_count && (
                            <span className="text-[11px] text-gray-400 dark:text-gray-500">
                              {insight.related_count} related items
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
            </div>

            <div className="px-5 py-3 border-t border-gray-100 dark:border-slate-700/60 bg-gray-50 dark:bg-slate-800/40">
              <Button
                variant="ghost"
                size="sm"
                href="/ai"
                icon={<SparklesIcon className="h-4 w-4" />}
                className="w-full justify-center text-indigo-600 dark:text-indigo-400"
              >
                Open AI Assistant
              </Button>
            </div>
          </Card>

          {/* ── Recent Activity ──────────────────────────── */}
          <Card padding="none" className="overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-slate-700">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Recent Activity</h2>
              <Button variant="ghost" size="sm" href="/audit" className="text-xs text-gray-500 hover:text-indigo-600">
                View all
              </Button>
            </div>

            <div className="divide-y divide-gray-100 dark:divide-slate-700/60">
              {MOCK_ACTIVITY.map((activity) => {
                const moduleColors: Record<string, string> = {
                  Access: 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400',
                  Risk: 'bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400',
                  Controls: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400',
                  Cert: 'bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400',
                };
                const moduleColor = moduleColors[activity.module] || moduleColors.Access;
                const initial = activity.actor === 'System' ? 'S' : (activity.actor ?? '').split(' ').map((n: string) => n[0] ?? '').join('');

                return (
                  <div key={activity.id} className="flex items-start gap-3 px-5 py-3.5 hover:bg-gray-50 dark:hover:bg-slate-700/20 transition-colors">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 ${moduleColor}`}>
                      {initial}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-800 dark:text-gray-200 leading-snug">
                        <span className="font-semibold">{activity.actor}</span>
                        {' '}{activity.action}{' '}
                        <span className="text-gray-500 dark:text-gray-400">{activity.object}</span>
                      </p>
                      <p className="text-[11px] text-gray-400 dark:text-gray-500 mt-0.5">{activity.timestamp}</p>
                    </div>
                    <span className={`shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded ${moduleColor}`}>
                      {activity.module}
                    </span>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* ── Quick Actions ─────────────────────────────── */}
          <Card padding="md">
            <CardHeader title="Quick Actions" />
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'New Request', icon: KeyIcon, href: '/access-requests/new', color: 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30' },
                { label: 'Run Analysis', icon: ChartBarIcon, href: '/risk', color: 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/30' },
                { label: 'My Reviews', icon: ClipboardDocumentCheckIcon, href: '/certification/review', color: 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/30' },
                { label: 'Emergency Access', icon: BoltIcon, href: '/privileged-access/request', color: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30' },
              ].map((action) => {
                const Icon = action.icon;
                return (
                  <a
                    key={action.label}
                    href={action.href}
                    onClick={(e) => { e.preventDefault(); navigate(action.href); }}
                    className="flex flex-col items-center gap-2 p-3 rounded-xl border border-gray-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-sm transition-all group cursor-pointer"
                  >
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${action.color}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 text-center group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {action.label}
                    </span>
                  </a>
                );
              })}
            </div>
          </Card>
        </div>
      </div>

      {/* ── Fix Modal ──────────────────────────────────────────────────── */}
      {fixModalItem && (
        <FixModal
          item={fixModalItem}
          preview={fixPreview}
          loading={fixPreviewMutation.isPending}
          onConfirm={handleFixConfirm}
          onClose={() => {
            setFixModalItem(null);
            setFixPreview(null);
          }}
        />
      )}
    </div>
  );
}
