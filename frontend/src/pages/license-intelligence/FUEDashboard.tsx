import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
  ReferenceLine,
} from 'recharts';
import {
  ExclamationTriangleIcon,
  ArrowPathIcon,
  ArrowDownTrayIcon,
  InformationCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CheckCircleIcon,
  ClockIcon,
  UserGroupIcon,
  DocumentTextIcon,
  BoltIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

// ─── API layer ────────────────────────────────────────────────────────────────

const api = axios.create({ baseURL: '/license-intelligence' });

const licenseApi = {
  getPosition: (contractId?: string) =>
    api.get('/dashboard/position', { params: contractId ? { contract_id: contractId } : {} }),
  getTrends: (days: number, contractId?: string) =>
    api.get('/dashboard/trends', { params: { days, ...(contractId ? { contract_id: contractId } : {}) } }),
  getClassificationSummary: () => api.get('/classifications/summary'),
  getByDepartment: () => api.get('/classifications/by-department'),
  getDrivers: () => api.get('/dashboard/drivers'),
  getCandidates: () => api.get('/dashboard/candidates'),
  getReclamationCases: () => api.get('/reclamation/cases'),
  classify: () => api.post('/classify'),
  calculate: (contractId: string) => api.post(`/consumption/calculate/${contractId}`),
};

// ─── Types ────────────────────────────────────────────────────────────────────

interface PositionData {
  contracted_fue: number;
  consumed_fue: number;
  available_fue: number;
  utilisation_pct: number;
  contract_reference: string;
  contract_id: string;
  last_synced: string;
  contracts?: Array<{ id: string; reference: string }>;
}

interface TrendPoint {
  date: string;
  consumed: number;
  contracted: number;
}

interface UseTypeEntry {
  use_type: string;
  user_count: number;
  fue_ratio: number;
  fue_contribution: number;
  color: string;
}

interface ClassificationSummary {
  entries: UseTypeEntry[];
  total_users: number;
  total_fue: number;
}

interface DepartmentRow {
  department: string;
  advanced: number;
  core: number;
  self_service: number;
  developer: number;
  total_users: number;
  fue_impact: number;
}

interface DriverRow {
  role_name: string;
  users_affected: number;
  mapped_use_type: string;
  avg_fue_if_removed: number;
  total_fue_potential: number;
  details?: Array<{ auth_object: string; field: string; value: string }>;
}

interface Candidate {
  username: string;
  current_type: string;
  fue: number;
  inactive_days: number;
  last_activity: string;
  reason: string;
}

interface ReclamationCase {
  id: string;
  username: string;
  trigger: string;
  current_fue: number;
  projected_fue: number;
  fue_released: number;
  status: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const USE_TYPE_COLORS: Record<string, string> = {
  Advanced: '#ef4444',
  Core: '#f59e0b',
  'Self-Service': '#22c55e',
  Developer: '#8b5cf6',
  Unclassified: '#6b7280',
};

const USE_TYPE_BG: Record<string, string> = {
  Advanced: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  Core: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  'Self-Service': 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  Developer: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
  Unclassified: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
};

const RECLAMATION_STATUS_STYLES: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  approved: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  rejected: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  in_review: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300',
};

// ─── Mock fallbacks (used when API has no data yet) ────────────────────────────

const MOCK_POSITION: PositionData = {
  contracted_fue: 1250,
  consumed_fue: 987,
  available_fue: 263,
  utilisation_pct: 78.96,
  contract_reference: 'SAP-LIC-2024-0042',
  contract_id: 'contract-001',
  last_synced: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
  contracts: [{ id: 'contract-001', reference: 'SAP-LIC-2024-0042' }],
};

const MOCK_TRENDS: TrendPoint[] = Array.from({ length: 30 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (29 - i));
  return {
    date: d.toISOString().split('T')[0],
    consumed: 920 + Math.round(Math.sin(i / 4) * 30 + i * 2.3),
    contracted: 1250,
  };
});

const MOCK_CLASSIFICATION: ClassificationSummary = {
  total_users: 1420,
  total_fue: 987,
  entries: [
    { use_type: 'Advanced', user_count: 310, fue_ratio: 1.0, fue_contribution: 310, color: '#ef4444' },
    { use_type: 'Core', user_count: 480, fue_ratio: 0.5, fue_contribution: 240, color: '#f59e0b' },
    { use_type: 'Self-Service', user_count: 390, fue_ratio: 0.3, fue_contribution: 117, color: '#22c55e' },
    { use_type: 'Developer', user_count: 95, fue_ratio: 1.5, fue_contribution: 142.5, color: '#8b5cf6' },
    { use_type: 'Unclassified', user_count: 145, fue_ratio: 1.0, fue_contribution: 145, color: '#6b7280' },
  ],
};

const MOCK_DEPARTMENTS: DepartmentRow[] = [
  { department: 'Finance', advanced: 85, core: 120, self_service: 60, developer: 15, total_users: 280, fue_impact: 230 },
  { department: 'IT', advanced: 65, core: 45, self_service: 20, developer: 55, total_users: 185, fue_impact: 210 },
  { department: 'Procurement', advanced: 45, core: 90, self_service: 80, developer: 5, total_users: 220, fue_impact: 136 },
  { department: 'HR', advanced: 30, core: 75, self_service: 110, developer: 5, total_users: 220, fue_impact: 103 },
  { department: 'Sales', advanced: 50, core: 80, self_service: 95, developer: 8, total_users: 233, fue_impact: 136 },
  { department: 'Operations', advanced: 35, core: 70, self_service: 25, developer: 7, total_users: 137, fue_impact: 93 },
];

const MOCK_DRIVERS: DriverRow[] = [
  {
    role_name: 'SAP_FI_AP_PROCESSOR',
    users_affected: 142,
    mapped_use_type: 'Advanced',
    avg_fue_if_removed: 0.5,
    total_fue_potential: 71,
    details: [{ auth_object: 'F_BKPF_BUK', field: 'ACTVT', value: '01,02,06' }],
  },
  {
    role_name: 'SAP_MM_PURCHASING',
    users_affected: 98,
    mapped_use_type: 'Advanced',
    avg_fue_if_removed: 0.5,
    total_fue_potential: 49,
    details: [{ auth_object: 'M_BEST_BSA', field: 'BSART', value: '*' }],
  },
  {
    role_name: 'SAP_SD_BILLING',
    users_affected: 76,
    mapped_use_type: 'Core',
    avg_fue_if_removed: 0.3,
    total_fue_potential: 15.2,
    details: [{ auth_object: 'V_VBRK_FKA', field: 'FKART', value: 'F2' }],
  },
  {
    role_name: 'Z_CUSTOM_DEVELOPER_ACCESS',
    users_affected: 55,
    mapped_use_type: 'Developer',
    avg_fue_if_removed: 1.0,
    total_fue_potential: 55,
    details: [{ auth_object: 'S_DEVELOP', field: 'ACTVT', value: '01,02,03,16' }],
  },
  {
    role_name: 'SAP_CO_REPORTING',
    users_affected: 189,
    mapped_use_type: 'Core',
    avg_fue_if_removed: 0.3,
    total_fue_potential: 37.8,
    details: [{ auth_object: 'K_CCA', field: 'ACTVT', value: '03' }],
  },
];

const MOCK_CANDIDATES: Candidate[] = [
  { username: 'U12345', current_type: 'Advanced', fue: 1.0, inactive_days: 92, last_activity: '2026-08-18', reason: 'Inactive >90 days' },
  { username: 'U23456', current_type: 'Advanced', fue: 1.0, inactive_days: 0, last_activity: '2026-11-10', reason: 'Unclassified access' },
  { username: 'U34567', current_type: 'Developer', fue: 1.5, inactive_days: 45, last_activity: '2026-10-04', reason: 'No dev activity logged' },
  { username: 'U45678', current_type: 'Core', fue: 0.5, inactive_days: 150, last_activity: '2026-06-21', reason: 'Inactive >90 days' },
  { username: 'U56789', current_type: 'Advanced', fue: 1.0, inactive_days: 30, last_activity: '2026-10-20', reason: 'Duplicate account suspected' },
];

const MOCK_RECLAMATION: ReclamationCase[] = [
  { id: 'RC-001', username: 'U12345', trigger: 'Inactive >90 days', current_fue: 1.0, projected_fue: 0.0, fue_released: 1.0, status: 'approved' },
  { id: 'RC-002', username: 'U34567', trigger: 'No dev activity', current_fue: 1.5, projected_fue: 0.5, fue_released: 1.0, status: 'in_review' },
  { id: 'RC-003', username: 'U78901', trigger: 'Role reclassified', current_fue: 1.0, projected_fue: 0.5, fue_released: 0.5, status: 'pending' },
  { id: 'RC-004', username: 'U89012', trigger: 'Inactive >90 days', current_fue: 1.0, projected_fue: 0.0, fue_released: 1.0, status: 'completed' },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtNumber(n: number, decimals = 0) {
  return n.toLocaleString('en-US', { maximumFractionDigits: decimals });
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getUtilColour(pct: number): string {
  if (pct >= 85) return 'text-red-600 dark:text-red-400';
  if (pct >= 70) return 'text-amber-500 dark:text-amber-400';
  return 'text-green-600 dark:text-green-400';
}

function getUtilBg(pct: number): string {
  if (pct >= 85) return 'from-red-500 to-red-600';
  if (pct >= 70) return 'from-amber-400 to-amber-500';
  return 'from-green-500 to-green-600';
}

function staleness(iso: string): { label: string; stale: boolean } {
  const diffHrs = (Date.now() - new Date(iso).getTime()) / 3_600_000;
  if (diffHrs < 2) return { label: `${Math.round(diffHrs * 60)}m ago`, stale: false };
  if (diffHrs < 24) return { label: `${Math.round(diffHrs)}h ago`, stale: false };
  const diffDays = Math.round(diffHrs / 24);
  return { label: `${diffDays}d ago`, stale: diffDays > 1 };
}

function downloadCsv(position: PositionData) {
  const rows = [
    ['Metric', 'Value'],
    ['Contracted FUE', position.contracted_fue],
    ['Consumed FUE', position.consumed_fue],
    ['Available FUE', position.available_fue],
    ['Utilisation %', position.utilisation_pct.toFixed(2)],
    ['Contract Reference', position.contract_reference],
  ];
  const csv = rows.map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `fue-position-${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Toast({ message, type, onClose }: { message: string; type: 'success' | 'error'; onClose: () => void }) {
  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-xl px-5 py-4 shadow-2xl border backdrop-blur-sm transition-all
        ${type === 'success'
          ? 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/80 dark:border-green-700 dark:text-green-200'
          : 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/80 dark:border-red-700 dark:text-red-200'
        }`}
    >
      {type === 'success'
        ? <CheckCircleIcon className="h-5 w-5 flex-shrink-0" />
        : <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" />}
      <span className="text-sm font-medium">{message}</span>
      <button onClick={onClose} className="ml-2 text-current opacity-60 hover:opacity-100 text-lg leading-none">&times;</button>
    </div>
  );
}

function SectionHeader({ title, subtitle, icon: Icon }: { title: string; subtitle?: string; icon?: React.ElementType }) {
  return (
    <div className="flex items-start gap-3 mb-5">
      {Icon && (
        <div className="flex-shrink-0 h-9 w-9 rounded-lg bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center">
          <Icon className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
        </div>
      )}
      <div>
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">{title}</h2>
        {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  );
}

function UseTypeBadge({ type }: { type: string }) {
  const cls = USE_TYPE_BG[type] ?? USE_TYPE_BG['Unclassified'];
  return <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>{type}</span>;
}

function CircularProgress({ pct }: { pct: number }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const fill = Math.min(pct / 100, 1) * circ;
  const color = pct >= 85 ? '#ef4444' : pct >= 70 ? '#f59e0b' : '#22c55e';
  return (
    <svg width="96" height="96" className="transform -rotate-90">
      <circle cx="48" cy="48" r={r} fill="none" stroke="currentColor" strokeWidth="8"
        className="text-gray-200 dark:text-gray-700" />
      <circle cx="48" cy="48" r={r} fill="none" stroke={color} strokeWidth="8"
        strokeDasharray={`${fill} ${circ}`} strokeLinecap="round" />
    </svg>
  );
}

function LoadingCard({ rows = 1 }: { rows?: number }) {
  return (
    <div className="animate-pulse space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-8 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      ))}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function FUEDashboard() {
  const qc = useQueryClient();

  // UI state
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [trendDays, setTrendDays] = useState<30 | 90 | 180 | 365>(90);
  const [selectedContract, setSelectedContract] = useState<string | undefined>(undefined);
  const [reviewTab, setReviewTab] = useState<'candidates' | 'reclamation'>('candidates');
  const [expandedDriver, setExpandedDriver] = useState<number | null>(null);
  const [deptSort, setDeptSort] = useState<'fue_impact' | 'total_users'>('fue_impact');

  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  }, []);

  // ── Queries ────────────────────────────────────────────────────────────────

  const { data: position, isLoading: posLoading } = useQuery<PositionData>({
    queryKey: ['fue-position', selectedContract],
    queryFn: () => licenseApi.getPosition(selectedContract).then(r => r.data).catch(() => MOCK_POSITION),
    staleTime: 5 * 60_000,
    placeholderData: MOCK_POSITION,
  });

  const { data: trends, isLoading: trendLoading } = useQuery<TrendPoint[]>({
    queryKey: ['fue-trends', trendDays, selectedContract],
    queryFn: () => licenseApi.getTrends(trendDays, selectedContract).then(r => r.data).catch(() => MOCK_TRENDS),
    staleTime: 5 * 60_000,
    placeholderData: MOCK_TRENDS,
  });

  const { data: classificationSummary, isLoading: classLoading } = useQuery<ClassificationSummary>({
    queryKey: ['fue-classification-summary'],
    queryFn: () => licenseApi.getClassificationSummary().then(r => r.data).catch(() => MOCK_CLASSIFICATION),
    staleTime: 5 * 60_000,
    placeholderData: MOCK_CLASSIFICATION,
  });

  const { data: departments, isLoading: deptLoading } = useQuery<DepartmentRow[]>({
    queryKey: ['fue-departments'],
    queryFn: () => licenseApi.getByDepartment().then(r => r.data).catch(() => MOCK_DEPARTMENTS),
    staleTime: 5 * 60_000,
    placeholderData: MOCK_DEPARTMENTS,
  });

  const { data: drivers, isLoading: driversLoading } = useQuery<DriverRow[]>({
    queryKey: ['fue-drivers'],
    queryFn: () => licenseApi.getDrivers().then(r => r.data).catch(() => MOCK_DRIVERS),
    staleTime: 5 * 60_000,
    placeholderData: MOCK_DRIVERS,
  });

  const { data: candidates } = useQuery<Candidate[]>({
    queryKey: ['fue-candidates'],
    queryFn: () => licenseApi.getCandidates().then(r => r.data).catch(() => MOCK_CANDIDATES),
    staleTime: 5 * 60_000,
    placeholderData: MOCK_CANDIDATES,
  });

  const { data: reclamationCases } = useQuery<ReclamationCase[]>({
    queryKey: ['fue-reclamation'],
    queryFn: () => licenseApi.getReclamationCases().then(r => r.data).catch(() => MOCK_RECLAMATION),
    staleTime: 5 * 60_000,
    placeholderData: MOCK_RECLAMATION,
  });

  // ── Mutations ──────────────────────────────────────────────────────────────

  const classifyMutation = useMutation({
    mutationFn: () => licenseApi.classify(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fue-classification-summary'] });
      qc.invalidateQueries({ queryKey: ['fue-departments'] });
      qc.invalidateQueries({ queryKey: ['fue-candidates'] });
      showToast('Classification job started. Results will refresh shortly.', 'success');
    },
    onError: () => showToast('Classification failed. Please try again.', 'error'),
  });

  const calculateMutation = useMutation({
    mutationFn: () => licenseApi.calculate(position?.contract_id ?? 'default'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fue-position'] });
      qc.invalidateQueries({ queryKey: ['fue-trends'] });
      showToast('Consumption recalculated.', 'success');
    },
    onError: () => showToast('Calculation failed. Please try again.', 'error'),
  });

  // ── Derived values ─────────────────────────────────────────────────────────

  const sortedDepts = useMemo(() => {
    if (!departments) return [];
    return [...departments].sort((a, b) => b[deptSort] - a[deptSort]);
  }, [departments, deptSort]);

  const sync = position ? staleness(position.last_synced) : null;

  const trendData = useMemo(() => {
    if (!trends) return [];
    return trends.map(t => ({
      ...t,
      displayDate: new Date(t.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    }));
  }, [trends]);

  const isOver = position ? position.consumed_fue > position.contracted_fue : false;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#060c1a] text-gray-900 dark:text-white">
      {/* ── Header ── */}
      <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-30">
        <div className="max-w-screen-2xl mx-auto px-6 py-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            {/* Title + freshness */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center shadow">
                  <ChartBarIcon className="h-4 w-4 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-gray-900 dark:text-white leading-tight">
                    SAP License Intelligence
                  </h1>
                  <p className="text-xs text-gray-500 dark:text-gray-400">FUE Optimisation Dashboard</p>
                </div>
              </div>

              {sync && (
                <div className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${
                  sync.stale
                    ? 'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-900/30 dark:border-amber-700 dark:text-amber-400'
                    : 'bg-gray-100 border-gray-200 text-gray-600 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-400'
                }`}>
                  {sync.stale
                    ? <ExclamationTriangleIcon className="h-3.5 w-3.5" />
                    : <ClockIcon className="h-3.5 w-3.5" />}
                  <span>Synced {sync.label}</span>
                  {sync.stale && <span className="font-semibold ml-0.5">— data may be stale</span>}
                </div>
              )}
            </div>

            {/* Controls */}
            <div className="flex items-center gap-2 flex-wrap">
              {/* Contract selector */}
              {position?.contracts && position.contracts.length > 1 && (
                <select
                  value={selectedContract ?? position.contract_id}
                  onChange={e => setSelectedContract(e.target.value)}
                  className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5
                    bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  {position.contracts.map(c => (
                    <option key={c.id} value={c.id}>{c.reference}</option>
                  ))}
                </select>
              )}

              <button
                onClick={() => calculateMutation.mutate()}
                disabled={calculateMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600
                  rounded-lg bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300
                  hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
              >
                <ArrowPathIcon className={`h-4 w-4 ${calculateMutation.isPending ? 'animate-spin' : ''}`} />
                Calculate
              </button>

              <button
                onClick={() => position && downloadCsv(position)}
                disabled={posLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600
                  rounded-lg bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300
                  hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
              >
                <ArrowDownTrayIcon className="h-4 w-4" />
                Export
              </button>

              <button
                onClick={() => classifyMutation.mutate()}
                disabled={classifyMutation.isPending}
                className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium rounded-lg
                  bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm disabled:opacity-50 transition-colors"
              >
                <BoltIcon className={`h-4 w-4 ${classifyMutation.isPending ? 'animate-pulse' : ''}`} />
                {classifyMutation.isPending ? 'Classifying…' : 'Classify Now'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Disclaimer banner ── */}
      <div className="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800">
        <div className="max-w-screen-2xl mx-auto px-6 py-2.5 flex items-center gap-2">
          <InformationCircleIcon className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
          <p className="text-xs text-amber-800 dark:text-amber-300">
            <strong>Estimates only.</strong> All FUE figures are for internal optimisation and negotiation planning.
            The customer's SAP contract and SAP's official measurement tool determine legally binding counts.
          </p>
        </div>
      </div>

      {/* ── Page body ── */}
      <div className="max-w-screen-2xl mx-auto px-6 py-8 space-y-10">

        {/* ══════════════════════════════════════════════════════════════════
            Section 1: License Position Cards
        ══════════════════════════════════════════════════════════════════ */}
        <section>
          <SectionHeader
            title="License Position"
            subtitle={position?.contract_reference ? `Contract: ${position.contract_reference}` : undefined}
            icon={DocumentTextIcon}
          />
          {posLoading ? (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
              {[0,1,2,3].map(i => (
                <div key={i} className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
                  <LoadingCard rows={3} />
                </div>
              ))}
            </div>
          ) : position ? (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
              {/* Contracted */}
              <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 relative overflow-hidden">
                <div className="absolute top-0 right-0 h-20 w-20 rounded-bl-full bg-indigo-50 dark:bg-indigo-900/20" />
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Contracted FUE</p>
                <p className="mt-2 text-4xl font-bold text-gray-900 dark:text-white">{fmtNumber(position.contracted_fue)}</p>
                <p className="mt-1 text-xs text-gray-400 dark:text-gray-500 truncate">{position.contract_reference}</p>
                <div className="absolute top-4 right-4 h-9 w-9 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center shadow-sm">
                  <DocumentTextIcon className="h-4 w-4 text-white" />
                </div>
              </div>

              {/* Consumed */}
              <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 relative overflow-hidden">
                <div className={`absolute top-0 right-0 h-20 w-20 rounded-bl-full ${
                  position.utilisation_pct >= 85 ? 'bg-red-50 dark:bg-red-900/20'
                  : position.utilisation_pct >= 70 ? 'bg-amber-50 dark:bg-amber-900/20'
                  : 'bg-green-50 dark:bg-green-900/20'
                }`} />
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Consumed FUE</p>
                <p className={`mt-2 text-4xl font-bold ${getUtilColour(position.utilisation_pct)}`}>
                  {fmtNumber(position.consumed_fue)}
                </p>
                <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">of {fmtNumber(position.contracted_fue)} contracted</p>
                <div className={`absolute top-4 right-4 h-9 w-9 rounded-lg bg-gradient-to-br ${getUtilBg(position.utilisation_pct)} flex items-center justify-center shadow-sm`}>
                  <ChartBarIcon className="h-4 w-4 text-white" />
                </div>
              </div>

              {/* Available */}
              <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 relative overflow-hidden">
                <div className={`absolute top-0 right-0 h-20 w-20 rounded-bl-full ${
                  position.available_fue < 0 ? 'bg-red-50 dark:bg-red-900/20' : 'bg-green-50 dark:bg-green-900/20'
                }`} />
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Available FUE</p>
                <p className={`mt-2 text-4xl font-bold ${position.available_fue < 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                  {position.available_fue < 0 ? '−' : ''}{fmtNumber(Math.abs(position.available_fue))}
                </p>
                <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                  {position.available_fue < 0 ? 'Over contracted limit' : 'Remaining headroom'}
                </p>
                <div className={`absolute top-4 right-4 h-9 w-9 rounded-lg bg-gradient-to-br ${position.available_fue < 0 ? 'from-red-500 to-red-600' : 'from-green-500 to-green-600'} flex items-center justify-center shadow-sm`}>
                  <CheckCircleIcon className="h-4 w-4 text-white" />
                </div>
              </div>

              {/* Utilisation */}
              <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 flex items-center gap-4">
                <div className="relative flex-shrink-0">
                  <CircularProgress pct={position.utilisation_pct} />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className={`text-lg font-bold ${getUtilColour(position.utilisation_pct)}`}>
                      {position.utilisation_pct.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Utilisation</p>
                  <p className={`mt-1 text-sm font-medium ${getUtilColour(position.utilisation_pct)}`}>
                    {position.utilisation_pct >= 85 ? 'Critical — at risk'
                      : position.utilisation_pct >= 70 ? 'Warning — monitor closely'
                      : 'Healthy'}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">Target &lt;70%</p>
                </div>
              </div>
            </div>
          ) : null}
        </section>

        {/* ══════════════════════════════════════════════════════════════════
            Section 2: FUE Consumption Trend
        ══════════════════════════════════════════════════════════════════ */}
        <section>
          <div className="flex items-center justify-between mb-5">
            <SectionHeader title="FUE Consumption Trend" subtitle="Contracted vs consumed over time" icon={ChartBarIcon} />
            <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
              {([30, 90, 180, 365] as const).map(d => (
                <button
                  key={d}
                  onClick={() => setTrendDays(d)}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                    trendDays === d
                      ? 'bg-white dark:bg-gray-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  {d === 365 ? '1y' : `${d}d`}
                </button>
              ))}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
            {trendLoading ? (
              <div className="h-64 flex items-center justify-center">
                <ArrowPathIcon className="h-6 w-6 text-gray-400 animate-spin" />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={trendData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                  <defs>
                    <linearGradient id="consumedGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={isOver ? '#ef4444' : '#6366f1'} stopOpacity={0.25} />
                      <stop offset="95%" stopColor={isOver ? '#ef4444' : '#6366f1'} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-gray-700" />
                  <XAxis
                    dataKey="displayDate"
                    tick={{ fontSize: 11, fill: '#9ca3af' }}
                    axisLine={false}
                    tickLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#9ca3af' }}
                    axisLine={false}
                    tickLine={false}
                    domain={['auto', 'auto']}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'var(--tooltip-bg, #fff)',
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                    formatter={(val: number, name: string) => [fmtNumber(val), name === 'consumed' ? 'Consumed FUE' : 'Contracted FUE']}
                    labelFormatter={(l: string) => `Date: ${l}`}
                  />
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    formatter={(v: string) => v === 'consumed' ? 'Consumed FUE' : 'Contracted FUE'}
                    wrapperStyle={{ fontSize: 12 }}
                  />
                  {/* Contracted flat reference */}
                  <ReferenceLine
                    y={position?.contracted_fue}
                    stroke="#6b7280"
                    strokeDasharray="6 3"
                    strokeWidth={1.5}
                    label={{ value: 'Contract', position: 'insideTopRight', fontSize: 10, fill: '#6b7280' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="contracted"
                    stroke="#9ca3af"
                    strokeWidth={1.5}
                    strokeDasharray="4 2"
                    fill="none"
                    dot={false}
                    activeDot={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="consumed"
                    stroke={isOver ? '#ef4444' : '#6366f1'}
                    strokeWidth={2.5}
                    fill="url(#consumedGradient)"
                    dot={false}
                    activeDot={{ r: 4, strokeWidth: 2 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        {/* ══════════════════════════════════════════════════════════════════
            Section 3: Use Type Distribution
        ══════════════════════════════════════════════════════════════════ */}
        <section>
          <SectionHeader title="Use Type Distribution" subtitle="User classification breakdown by FUE contribution" icon={UserGroupIcon} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Donut */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Users by Type</p>
              {classLoading ? <LoadingCard rows={4} /> : classificationSummary ? (
                <div className="flex items-center gap-6">
                  <div className="flex-shrink-0">
                    <ResponsiveContainer width={180} height={180}>
                      <PieChart>
                        <Pie
                          data={classificationSummary.entries}
                          cx="50%"
                          cy="50%"
                          innerRadius={55}
                          outerRadius={82}
                          paddingAngle={2}
                          dataKey="user_count"
                          nameKey="use_type"
                        >
                          {classificationSummary.entries.map((entry, i) => (
                            <Cell key={i} fill={USE_TYPE_COLORS[entry.use_type] ?? '#6b7280'} />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(v: number, name: string) => [fmtNumber(v) + ' users', name]}
                          contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="space-y-2.5 flex-1">
                    {classificationSummary.entries.map((e, i) => {
                      const pct = classificationSummary.total_users > 0
                        ? ((e.user_count / classificationSummary.total_users) * 100).toFixed(1)
                        : '0';
                      return (
                        <div key={i} className="flex items-center gap-2">
                          <span className="h-2.5 w-2.5 rounded-full flex-shrink-0" style={{ background: USE_TYPE_COLORS[e.use_type] ?? '#6b7280' }} />
                          <span className="text-xs text-gray-600 dark:text-gray-400 flex-1 truncate">{e.use_type}</span>
                          <span className="text-xs font-semibold text-gray-800 dark:text-gray-200">{fmtNumber(e.user_count)}</span>
                          <span className="text-xs text-gray-400 w-10 text-right">{pct}%</span>
                        </div>
                      );
                    })}
                    <div className="pt-2 border-t border-gray-100 dark:border-gray-700">
                      <div className="flex justify-between text-xs font-semibold">
                        <span className="text-gray-600 dark:text-gray-400">Total</span>
                        <span className="text-gray-900 dark:text-white">{fmtNumber(classificationSummary.total_users)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>

            {/* FUE contribution bar */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">FUE Contribution by Type</p>
              {classLoading ? <LoadingCard rows={5} /> : classificationSummary ? (
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart
                    data={classificationSummary.entries}
                    layout="vertical"
                    margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" className="dark:stroke-gray-700" />
                    <XAxis type="number" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="use_type" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} width={80} />
                    <Tooltip
                      formatter={(v: number) => [fmtNumber(v, 1) + ' FUE', 'Contribution']}
                      contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    />
                    <Bar dataKey="fue_contribution" radius={[0, 4, 4, 0]}>
                      {classificationSummary.entries.map((e, i) => (
                        <Cell key={i} fill={USE_TYPE_COLORS[e.use_type] ?? '#6b7280'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : null}
              {classificationSummary && (
                <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 flex justify-between items-center">
                  <span className="text-xs text-gray-500 dark:text-gray-400">Total FUE</span>
                  <span className="text-sm font-bold text-gray-900 dark:text-white">{fmtNumber(classificationSummary.total_fue, 1)}</span>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* ══════════════════════════════════════════════════════════════════
            Section 4: Department Breakdown
        ══════════════════════════════════════════════════════════════════ */}
        <section>
          <div className="flex items-center justify-between mb-5">
            <SectionHeader title="Department Breakdown" subtitle="FUE consumption by organisational unit" icon={UserGroupIcon} />
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 dark:text-gray-400">Sort by:</span>
              <select
                value={deptSort}
                onChange={e => setDeptSort(e.target.value as 'fue_impact' | 'total_users')}
                className="text-xs border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1
                  bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-indigo-500 outline-none"
              >
                <option value="fue_impact">FUE Impact</option>
                <option value="total_users">Total Users</option>
              </select>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
            {deptLoading ? (
              <div className="p-6"><LoadingCard rows={6} /></div>
            ) : (
              <>
                <div className="p-6 border-b border-gray-100 dark:border-gray-700">
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={sortedDepts} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-gray-700" />
                      <XAxis dataKey="department" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                      <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey="advanced" name="Advanced" stackId="a" fill={USE_TYPE_COLORS['Advanced']} radius={[0,0,0,0]} />
                      <Bar dataKey="core" name="Core" stackId="a" fill={USE_TYPE_COLORS['Core']} />
                      <Bar dataKey="self_service" name="Self-Service" stackId="a" fill={USE_TYPE_COLORS['Self-Service']} />
                      <Bar dataKey="developer" name="Developer" stackId="a" fill={USE_TYPE_COLORS['Developer']} radius={[4,4,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-700/50">
                      <tr>
                        {['Department', 'Advanced', 'Core', 'Self-Service', 'Developer', 'Total Users', 'FUE Impact'].map(h => (
                          <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                      {sortedDepts.map((row, i) => (
                        <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/40 transition-colors">
                          <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{row.department}</td>
                          <td className="px-4 py-3 text-red-600 dark:text-red-400 font-medium">{fmtNumber(row.advanced)}</td>
                          <td className="px-4 py-3 text-amber-600 dark:text-amber-400 font-medium">{fmtNumber(row.core)}</td>
                          <td className="px-4 py-3 text-green-600 dark:text-green-400 font-medium">{fmtNumber(row.self_service)}</td>
                          <td className="px-4 py-3 text-purple-600 dark:text-purple-400 font-medium">{fmtNumber(row.developer)}</td>
                          <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{fmtNumber(row.total_users)}</td>
                          <td className="px-4 py-3">
                            <span className="inline-flex items-center gap-1 font-bold text-gray-900 dark:text-white">
                              {fmtNumber(row.fue_impact, 1)}
                              <span className="text-xs font-normal text-gray-400">FUE</span>
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        </section>

        {/* ══════════════════════════════════════════════════════════════════
            Section 5: Top License Drivers
        ══════════════════════════════════════════════════════════════════ */}
        <section>
          <SectionHeader title="Top License Drivers" subtitle="Roles / authorisations pushing users into higher use types" icon={ExclamationTriangleIcon} />
          <div className="mb-3 flex items-center gap-2 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
            <InformationCircleIcon className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
            <p className="text-xs text-amber-800 dark:text-amber-300">
              These are illustrative estimates based on role-to-use-type mapping. Actual FUE impact requires SAP official measurement.
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
            {driversLoading ? (
              <div className="p-6"><LoadingCard rows={5} /></div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-700/50">
                  <tr>
                    {['Role / Object', 'Users Affected', 'Maps To', 'Avg FUE if Removed', 'FUE Potential', ''].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {(drivers ?? []).map((row, i) => (
                    <>
                      <tr
                        key={`row-${i}`}
                        className="hover:bg-gray-50 dark:hover:bg-gray-700/40 transition-colors cursor-pointer"
                        onClick={() => setExpandedDriver(expandedDriver === i ? null : i)}
                      >
                        <td className="px-4 py-3">
                          <span className="font-mono text-xs font-semibold text-gray-900 dark:text-white">{row.role_name}</span>
                        </td>
                        <td className="px-4 py-3 font-medium text-gray-700 dark:text-gray-300">{fmtNumber(row.users_affected)}</td>
                        <td className="px-4 py-3"><UseTypeBadge type={row.mapped_use_type} /></td>
                        <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{row.avg_fue_if_removed.toFixed(2)}</td>
                        <td className="px-4 py-3">
                          <span className="font-bold text-indigo-600 dark:text-indigo-400">{fmtNumber(row.total_fue_potential, 1)} FUE</span>
                        </td>
                        <td className="px-4 py-3 text-gray-400">
                          {expandedDriver === i
                            ? <ChevronUpIcon className="h-4 w-4" />
                            : <ChevronDownIcon className="h-4 w-4" />}
                        </td>
                      </tr>
                      {expandedDriver === i && row.details && (
                        <tr key={`detail-${i}`} className="bg-indigo-50/50 dark:bg-indigo-900/10">
                          <td colSpan={6} className="px-6 py-3">
                            <table className="w-full text-xs">
                              <thead>
                                <tr className="text-gray-500 dark:text-gray-400">
                                  <th className="text-left py-1 pr-4 font-semibold">Auth Object</th>
                                  <th className="text-left py-1 pr-4 font-semibold">Field</th>
                                  <th className="text-left py-1 font-semibold">Value</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-indigo-100 dark:divide-indigo-900/40">
                                {row.details.map((d, j) => (
                                  <tr key={j}>
                                    <td className="py-1 pr-4 font-mono text-indigo-700 dark:text-indigo-300">{d.auth_object}</td>
                                    <td className="py-1 pr-4 text-gray-600 dark:text-gray-400">{d.field}</td>
                                    <td className="py-1 font-mono text-gray-700 dark:text-gray-300">{d.value}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>

        {/* ══════════════════════════════════════════════════════════════════
            Section 6: Review Candidates & Reclamation
        ══════════════════════════════════════════════════════════════════ */}
        <section>
          <SectionHeader title="Review Candidates & Reclamation" subtitle="Users flagged for review and active reclamation cases" icon={UserGroupIcon} />
          {/* Tabs */}
          <div className="flex gap-1 mb-4 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl w-fit">
            <button
              onClick={() => setReviewTab('candidates')}
              className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                reviewTab === 'candidates'
                  ? 'bg-white dark:bg-gray-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Review Candidates
              {candidates && (
                <span className="ml-2 inline-flex items-center justify-center h-4 w-4 text-xs rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400">
                  {candidates.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setReviewTab('reclamation')}
              className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                reviewTab === 'reclamation'
                  ? 'bg-white dark:bg-gray-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Reclamation Cases
              {reclamationCases && (
                <span className="ml-2 inline-flex items-center justify-center h-4 w-4 text-xs rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400">
                  {reclamationCases.length}
                </span>
              )}
            </button>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
            {reviewTab === 'candidates' ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-700/50">
                    <tr>
                      {['Username', 'Current Type', 'FUE', 'Inactive Days', 'Last Activity', 'Reason', 'Actions'].map(h => (
                        <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {(candidates ?? []).map((c, i) => (
                      <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/40 transition-colors">
                        <td className="px-4 py-3 font-mono text-xs font-semibold text-gray-900 dark:text-white">{c.username}</td>
                        <td className="px-4 py-3"><UseTypeBadge type={c.current_type} /></td>
                        <td className="px-4 py-3 font-medium text-gray-700 dark:text-gray-300">{c.fue.toFixed(1)}</td>
                        <td className="px-4 py-3">
                          <span className={`font-medium ${c.inactive_days > 90 ? 'text-red-600 dark:text-red-400' : c.inactive_days > 30 ? 'text-amber-500 dark:text-amber-400' : 'text-gray-600 dark:text-gray-400'}`}>
                            {c.inactive_days > 0 ? c.inactive_days : '—'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">{fmtDate(c.last_activity)}</td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                            {c.reason}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            <button className="px-2.5 py-1 text-xs font-medium rounded-md bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-800 transition-colors">
                              Review
                            </button>
                            <button className="px-2.5 py-1 text-xs font-medium rounded-md bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-800 transition-colors">
                              Reclaim
                            </button>
                            <button className="px-2.5 py-1 text-xs font-medium rounded-md bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                              Dismiss
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-700/50">
                    <tr>
                      {['Case ID', 'Username', 'Trigger', 'Current FUE', 'Projected FUE', 'FUE Released', 'Status', 'Actions'].map(h => (
                        <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {(reclamationCases ?? []).map((r, i) => (
                      <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/40 transition-colors">
                        <td className="px-4 py-3 font-mono text-xs font-semibold text-indigo-600 dark:text-indigo-400">{r.id}</td>
                        <td className="px-4 py-3 font-mono text-xs text-gray-900 dark:text-white">{r.username}</td>
                        <td className="px-4 py-3 text-xs text-gray-600 dark:text-gray-400">{r.trigger}</td>
                        <td className="px-4 py-3 font-medium text-gray-700 dark:text-gray-300">{r.current_fue.toFixed(1)}</td>
                        <td className="px-4 py-3 font-medium text-green-600 dark:text-green-400">{r.projected_fue.toFixed(1)}</td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center gap-1 font-bold text-green-600 dark:text-green-400">
                            <span className="text-green-500">↓</span>{r.fue_released.toFixed(1)} FUE
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${RECLAMATION_STATUS_STYLES[r.status] ?? RECLAMATION_STATUS_STYLES['pending']}`}>
                            {r.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            {r.status === 'pending' && (
                              <>
                                <button className="px-2.5 py-1 text-xs font-medium rounded-md bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300 hover:bg-green-200 transition-colors">
                                  Approve
                                </button>
                                <button className="px-2.5 py-1 text-xs font-medium rounded-md bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300 hover:bg-red-200 transition-colors">
                                  Reject
                                </button>
                              </>
                            )}
                            <button className="px-2.5 py-1 text-xs font-medium rounded-md bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                              View
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        {/* Footer spacing */}
        <div className="h-8" />
      </div>

      {/* Toast */}
      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
}
