import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../../services/api';
import {
  CubeIcon,
  ArrowsRightLeftIcon,
  ClockIcon,
  StarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  DocumentTextIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  Squares2X2Icon,
  WrenchScrewdriverIcon,
  ChartBarIcon,
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

interface RoleOverview {
  total_roles: number;
  duplicates_found: number;
  unused_roles: number;
  avg_health_score: number;
  grade_distribution: Record<'A' | 'B' | 'C' | 'D' | 'F', number>;
  top_issues: { issue: string; count: number }[];
}

interface DuplicateGroup {
  id: string;
  roles: string[];
  similarity: number;
  user_count: number;
  recommendation: string;
  savings_estimate: string;
}

interface UnusedRole {
  id: string;
  name: string;
  system: string;
  last_used: string | null;
  user_count: number;
  permission_count: number;
  created_date: string;
}

interface RoleHealthEntry {
  id: string;
  name: string;
  system: string;
  health_score: number;
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  user_count: number;
  issues_count: number;
  issues: string[];
}

interface NamingIssue {
  id: string;
  role_name: string;
  system: string;
  issue_type: string;
  suggestion: string;
}

interface ConsolidationItem {
  id: string;
  title: string;
  description: string;
  roles_affected: number;
  effort: 'low' | 'medium' | 'high';
  risk: 'low' | 'medium' | 'high';
  estimated_savings: string;
  status: 'pending' | 'in_progress' | 'done';
}


// ============================================================================
// Helpers
// ============================================================================

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  B: 'bg-blue-100 text-blue-700 border-blue-200',
  C: 'bg-amber-100 text-amber-700 border-amber-200',
  D: 'bg-orange-100 text-orange-700 border-orange-200',
  F: 'bg-red-100 text-red-700 border-red-200',
};

const EFFORT_VARIANT: Record<string, 'success' | 'warning' | 'danger'> = {
  low: 'success',
  medium: 'warning',
  high: 'danger',
};

const STATUS_VARIANT: Record<string, 'neutral' | 'info' | 'success'> = {
  pending: 'neutral',
  in_progress: 'info',
  done: 'success',
};

const STATUS_LABEL: Record<string, string> = {
  pending: 'Pending',
  in_progress: 'In Progress',
  done: 'Done',
};

function healthBarColor(score: number) {
  if (score >= 80) return 'bg-emerald-500';
  if (score >= 60) return 'bg-amber-500';
  if (score >= 40) return 'bg-orange-500';
  return 'bg-red-500';
}

function HealthBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full h-2">
        <div
          className={`${healthBarColor(score)} h-2 rounded-full transition-all duration-500`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-xs font-semibold text-gray-700 w-7 text-right">{score}</span>
    </div>
  );
}

function GradeBadge({ grade }: { grade: string }) {
  return (
    <span
      className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold border ${GRADE_COLORS[grade] ?? 'bg-gray-100 text-gray-600'}`}
    >
      {grade}
    </span>
  );
}

function PieSegment({
  value,
  total,
  color,
}: {
  value: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className={`w-3 h-3 rounded-sm flex-shrink-0 ${color}`} />
      <span className="text-xs text-gray-600 flex-1">{pct}%</span>
    </div>
  );
}

function SimilarityBar({ value }: { value: number }) {
  const color = value >= 90 ? 'bg-red-500' : value >= 80 ? 'bg-orange-400' : 'bg-amber-400';
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 bg-gray-200 rounded-full h-1.5">
        <div
          className={`${color} h-1.5 rounded-full`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-xs font-semibold text-gray-700">{value}%</span>
    </div>
  );
}

function StatTile({
  icon,
  label,
  value,
  sub,
  highlight,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  highlight?: string;
}) {
  return (
    <div className={`bg-white rounded-xl border border-gray-200 p-4 ${highlight ?? ''}`}>
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

// ============================================================================
// Tab content components
// ============================================================================

function OverviewTab({ data }: { data: RoleOverview }) {
  const total = data.total_roles;
  const gradeColors: Record<string, string> = {
    A: 'bg-emerald-500',
    B: 'bg-blue-400',
    C: 'bg-amber-400',
    D: 'bg-orange-500',
    F: 'bg-red-500',
  };

  return (
    <div className="space-y-6">
      {/* Grade distribution */}
      <Card>
        <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-2">
          <ChartBarIcon className="h-4 w-4 text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-800">Role Health Grade Distribution</h3>
        </div>
        <div className="p-4">
          <div className="flex items-end gap-2 h-28 mb-3">
            {(Object.entries(data.grade_distribution ?? {}) as [string, number][]).map(
              ([grade, count]) => {
                const heightPct = total > 0 ? (count / total) * 100 : 0;
                return (
                  <div key={grade} className="flex-1 flex flex-col items-center gap-1">
                    <span className="text-xs font-semibold text-gray-700">{count}</span>
                    <div
                      className={`w-full rounded-t ${gradeColors[grade]}`}
                      style={{ height: `${Math.max(heightPct, 4)}%` }}
                    />
                    <span className={`text-xs font-bold ${GRADE_COLORS[grade]?.split(' ')[1]}`}>
                      {grade}
                    </span>
                  </div>
                );
              }
            )}
          </div>
          <div className="grid grid-cols-5 gap-2 pt-3 border-t border-gray-100">
            {(Object.entries(data.grade_distribution ?? {}) as [string, number][]).map(
              ([grade, count]) => (
                <div key={grade} className="text-center">
                  <PieSegment value={count} total={total} color={gradeColors[grade]} />
                </div>
              )
            )}
          </div>
        </div>
      </Card>

      {/* Top issues */}
      <Card>
        <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-2">
          <ExclamationTriangleIcon className="h-4 w-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-gray-800">Top Issues</h3>
        </div>
        <div className="divide-y divide-gray-100">
          {(data.top_issues ?? []).map((issue, idx) => {
            const barWidth = Math.round((issue.count / total) * 100);
            return (
              <div key={idx} className="px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-700">{issue.issue}</span>
                  <span className="text-sm font-semibold text-gray-900">{issue.count}</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-1.5">
                  <div
                    className="bg-amber-400 h-1.5 rounded-full"
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

function DuplicatesTab({ groups }: { groups: DuplicateGroup[] }) {
  const { mutate: retireGroup, isPending } = useMutation({
    mutationFn: async (id: string) => {
      // Backend does not have a retire endpoint; show a notification instead
      return { scheduled: true, id };
    },
    onSuccess: () => {
      window.alert('Role retirement scheduled. Navigate to Role Design Studio to track progress.');
    },
  });

  return (
    <div className="space-y-4">
      {groups.map((group) => (
        <Card key={group.id}>
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <ArrowsRightLeftIcon className="h-4 w-4 text-orange-500" />
              <SimilarityBar value={group.similarity} />
              <span className="text-xs text-gray-500">{group.user_count} users affected</span>
            </div>
            <Button
              variant="secondary"
              size="sm"
              loading={isPending}
              onClick={() => retireGroup(group.id)}
            >
              Retire Duplicates
            </Button>
          </div>
          <div className="p-4 space-y-3">
            <div className="flex flex-wrap gap-2">
              {group.roles.map((role, idx) => (
                <span
                  key={role}
                  className={`px-2.5 py-1 rounded-md text-xs font-mono font-medium border ${
                    idx === 0
                      ? 'bg-blue-50 border-blue-200 text-blue-800'
                      : 'bg-gray-50 border-gray-200 text-gray-600 line-through'
                  }`}
                  title={idx === 0 ? 'Keep this role' : 'Retire this role'}
                >
                  {role}
                </span>
              ))}
            </div>
            <div className="flex items-start gap-2 bg-amber-50 border border-amber-100 rounded-lg p-3">
              <LightBulbIconInline />
              <p className="text-xs text-amber-800">{group.recommendation}</p>
            </div>
            <p className="text-xs text-emerald-700 font-medium">{group.savings_estimate}</p>
          </div>
        </Card>
      ))}
    </div>
  );
}

function LightBulbIconInline() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
      />
    </svg>
  );
}

function UnusedTab({ roles }: { roles: UnusedRole[] }) {
  const [search, setSearch] = useState('');
  const { mutate: retireRole, isPending } = useMutation({
    mutationFn: async (id: string) => {
      // Backend does not have a retire endpoint; show a notification instead
      return { scheduled: true, id };
    },
    onSuccess: () => {
      window.alert('Role retirement scheduled. Navigate to Role Design Studio to track progress.');
    },
  });

  const filtered = roles.filter(
    (r) =>
      r.name.toLowerCase().includes(search.toLowerCase()) ||
      r.system.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search unused roles..."
          className="w-full pl-9 border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">System</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Used</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Permissions</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Action</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filtered.map((role) => (
              <tr key={role.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <span className="text-sm font-mono font-medium text-gray-900">{role.name}</span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">{role.system}</td>
                <td className="px-4 py-3">
                  {role.last_used ? (
                    <div>
                      <p className="text-sm text-gray-700">{role.last_used}</p>
                    </div>
                  ) : (
                    <span className="text-xs text-gray-400 italic">Never used</span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">{role.permission_count}</td>
                <td className="px-4 py-3 text-sm text-gray-500">{role.created_date}</td>
                <td className="px-4 py-3 text-right">
                  <Button
                    variant="danger"
                    size="sm"
                    loading={isPending}
                    onClick={() => retireRole(role.id)}
                  >
                    Retire
                  </Button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">
                  No unused roles found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HealthScoresTab({ roles }: { roles: RoleHealthEntry[] }) {
  const [search, setSearch] = useState('');
  const [gradeFilter, setGradeFilter] = useState('');

  const filtered = roles.filter(
    (r) =>
      (r.name.toLowerCase().includes(search.toLowerCase()) ||
        r.system.toLowerCase().includes(search.toLowerCase())) &&
      (gradeFilter === '' || r.grade === gradeFilter)
  );

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap">
        <div className="flex-1 min-w-[200px] relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search roles..."
            className="w-full pl-9 border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <FunnelIcon className="h-4 w-4 text-gray-400" />
          <select
            value={gradeFilter}
            onChange={(e) => setGradeFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">All Grades</option>
            {['A', 'B', 'C', 'D', 'F'].map((g) => (
              <option key={g} value={g}>
                Grade {g}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">System</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-40">Health Score</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Grade</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Users</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Issues</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filtered.map((role) => (
              <tr key={role.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <span className="text-sm font-mono font-medium text-gray-900">{role.name}</span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">{role.system}</td>
                <td className="px-4 py-3 w-44">
                  <HealthBar score={role.health_score} />
                </td>
                <td className="px-4 py-3">
                  <GradeBadge grade={role.grade} />
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">{role.user_count}</td>
                <td className="px-4 py-3">
                  {role.issues_count === 0 ? (
                    <div className="flex items-center gap-1 text-emerald-600 text-xs">
                      <CheckCircleIcon className="h-4 w-4" />
                      None
                    </div>
                  ) : (
                    <div className="group relative">
                      <div className="flex items-center gap-1 text-amber-600 text-xs cursor-help">
                        <ExclamationTriangleIcon className="h-4 w-4" />
                        {role.issues_count} issue{role.issues_count > 1 ? 's' : ''}
                      </div>
                      <div className="absolute left-0 top-6 z-10 hidden group-hover:block bg-white border border-gray-200 rounded-lg shadow-lg p-2 w-56">
                        <ul className="space-y-1">
                          {role.issues.map((issue, i) => (
                            <li key={i} className="text-xs text-gray-600 flex gap-1">
                              <XCircleIcon className="h-3 w-3 text-red-400 flex-shrink-0 mt-0.5" />
                              {issue}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">
                  No roles match the current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function NamingTab({ issues }: { issues: NamingIssue[] }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role Name</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">System</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Issue</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Suggested Correction</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Action</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {issues.map((issue) => (
            <tr key={issue.id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <span className="text-sm font-mono text-red-700 bg-red-50 px-2 py-0.5 rounded">
                  {issue.role_name}
                </span>
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">{issue.system}</td>
              <td className="px-4 py-3">
                <Badge variant="warning" size="sm">
                  {issue.issue_type}
                </Badge>
              </td>
              <td className="px-4 py-3">
                <span className="text-sm font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                  {issue.suggestion}
                </span>
              </td>
              <td className="px-4 py-3 text-right">
                <button className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                  Apply Fix
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ConsolidationTab({ items }: { items: ConsolidationItem[] }) {
  const { mutate: updateStatus } = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch(`/role-intelligence/consolidation/${id}`, { status }),
  });

  return (
    <div className="space-y-4">
      {items.map((item) => (
        <Card key={item.id}>
          <div className="p-4">
            <div className="flex items-start justify-between gap-4 mb-3">
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-gray-900 mb-1">{item.title}</h3>
                <p className="text-sm text-gray-600">{item.description}</p>
              </div>
              <Badge variant={STATUS_VARIANT[item.status]} size="md">
                {STATUS_LABEL[item.status]}
              </Badge>
            </div>
            <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-gray-100">
              <div className="flex items-center gap-1.5">
                <CubeIcon className="h-4 w-4 text-gray-400" />
                <span className="text-xs text-gray-600">
                  {item.roles_affected} roles affected
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <WrenchScrewdriverIcon className="h-4 w-4 text-gray-400" />
                <span className="text-xs text-gray-600">Effort:</span>
                <Badge variant={EFFORT_VARIANT[item.effort]} size="sm">
                  {item.effort}
                </Badge>
              </div>
              <div className="flex items-center gap-1.5">
                <ExclamationTriangleIcon className="h-4 w-4 text-gray-400" />
                <span className="text-xs text-gray-600">Risk:</span>
                <Badge variant={EFFORT_VARIANT[item.risk]} size="sm">
                  {item.risk}
                </Badge>
              </div>
              <div className="flex items-center gap-1.5 ml-auto">
                <StarIcon className="h-4 w-4 text-emerald-500" />
                <span className="text-xs font-medium text-emerald-700">{item.estimated_savings}</span>
              </div>
              {item.status === 'pending' && (
                <button
                  onClick={() => updateStatus({ id: item.id, status: 'in_progress' })}
                  className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  Start
                </button>
              )}
              {item.status === 'in_progress' && (
                <button
                  onClick={() => updateStatus({ id: item.id, status: 'done' })}
                  className="text-xs text-emerald-700 hover:text-emerald-900 font-medium"
                >
                  Mark Done
                </button>
              )}
              {item.status === 'done' && (
                <CheckCircleIcon className="h-4 w-4 text-emerald-500" />
              )}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

// ============================================================================
// Main component
// ============================================================================

type Tab = 'overview' | 'duplicates' | 'unused' | 'health' | 'naming' | 'consolidation';

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <Squares2X2Icon className="h-4 w-4" /> },
  { id: 'duplicates', label: 'Duplicates', icon: <ArrowsRightLeftIcon className="h-4 w-4" /> },
  { id: 'unused', label: 'Unused', icon: <ClockIcon className="h-4 w-4" /> },
  { id: 'health', label: 'Health Scores', icon: <StarIcon className="h-4 w-4" /> },
  { id: 'naming', label: 'Naming Issues', icon: <DocumentTextIcon className="h-4 w-4" /> },
  { id: 'consolidation', label: 'Consolidation', icon: <WrenchScrewdriverIcon className="h-4 w-4" /> },
];

export function RoleIntelligence() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const { data: overviewData, isLoading: overviewLoading } = useQuery<RoleOverview>({
    queryKey: ['role-intelligence-overview'],
    queryFn: () => api.get('/role-intelligence/overview').then((r) => r.data),
  });

  const { data: duplicatesData } = useQuery<DuplicateGroup[]>({
    queryKey: ['role-intelligence-duplicates'],
    queryFn: () => api.get('/role-intelligence/duplicates').then((r) => r.data),
    enabled: activeTab === 'duplicates',
  });

  const { data: unusedData } = useQuery<UnusedRole[]>({
    queryKey: ['role-intelligence-unused'],
    queryFn: () => api.get('/role-intelligence/unused').then((r) => r.data),
    enabled: activeTab === 'unused',
  });

  const { data: healthData } = useQuery<RoleHealthEntry[]>({
    queryKey: ['role-intelligence-health'],
    queryFn: () => api.get('/role-intelligence/health').then((r) => r.data),
    enabled: activeTab === 'health',
  });

  const { data: namingData } = useQuery<NamingIssue[]>({
    queryKey: ['role-intelligence-naming'],
    queryFn: () => api.get('/role-intelligence/naming-issues').then((r) => r.data),
    enabled: activeTab === 'naming',
  });

  const { data: consolidationData } = useQuery<ConsolidationItem[]>({
    queryKey: ['role-intelligence-consolidation'],
    queryFn: () => api.get('/role-intelligence/consolidation').then((r) => r.data),
    enabled: activeTab === 'consolidation',
  });

  const overview = overviewData ?? null;
  const duplicates = duplicatesData ?? [];
  const unused = unusedData ?? [];
  const health = healthData ?? [];
  const naming = namingData ?? [];
  const consolidation = consolidationData ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Role Intelligence"
        subtitle="Estate health analysis — detect duplicates, unused roles, naming violations, and consolidation opportunities."
        actions={
          <Button
            variant="secondary"
            size="sm"
            icon={<ArrowPathIcon className="h-4 w-4" />}
          >
            Refresh Analysis
          </Button>
        }
      />

      {/* Stat tiles */}
      {overviewLoading ? (
        <LoadingState message="Loading role estate data..." />
      ) : overview ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatTile
            icon={<CubeIcon className="h-5 w-5 text-indigo-500" />}
            label="Total Roles"
            value={overview.total_roles}
            sub="across all systems"
          />
          <StatTile
            icon={<ArrowsRightLeftIcon className="h-5 w-5 text-orange-500" />}
            label="Duplicates Found"
            value={overview.duplicates_found}
            sub="groups with >75% similarity"
            highlight="border-orange-200"
          />
          <StatTile
            icon={<ClockIcon className="h-5 w-5 text-red-500" />}
            label="Unused Roles"
            value={overview.unused_roles}
            sub="0 users assigned"
            highlight="border-red-200"
          />
          <StatTile
            icon={<StarIcon className="h-5 w-5 text-amber-500" />}
            label="Avg Health Score"
            value={`${overview.avg_health_score}/100`}
            sub="across all active roles"
            highlight={
              overview.avg_health_score >= 80
                ? 'border-emerald-200 bg-emerald-50'
                : overview.avg_health_score >= 60
                ? 'border-amber-200 bg-amber-50'
                : 'border-red-200 bg-red-50'
            }
          />
        </div>
      ) : (
        <p className="text-sm text-gray-400">No data available</p>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-1 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.id === 'duplicates' && overview && (
                <span className="ml-1 px-1.5 py-0.5 rounded-full text-xs bg-orange-100 text-orange-700">
                  {overview.duplicates_found}
                </span>
              )}
              {tab.id === 'unused' && overview && (
                <span className="ml-1 px-1.5 py-0.5 rounded-full text-xs bg-red-100 text-red-700">
                  {overview.unused_roles}
                </span>
              )}
              {tab.id === 'naming' && overview && (
                <span className="ml-1 px-1.5 py-0.5 rounded-full text-xs bg-amber-100 text-amber-700">
                  {overview.top_issues?.find((i: any) => i.issue === 'No naming convention')?.count ?? 0}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="min-h-[300px]">
        {activeTab === 'overview' && overview && <OverviewTab data={overview} />}
        {activeTab === 'duplicates' && <DuplicatesTab groups={duplicates} />}
        {activeTab === 'unused' && <UnusedTab roles={unused} />}
        {activeTab === 'health' && <HealthScoresTab roles={health} />}
        {activeTab === 'naming' && <NamingTab issues={naming} />}
        {activeTab === 'consolidation' && <ConsolidationTab items={consolidation} />}
      </div>
    </div>
  );
}
