/**
 * Governex+ Platform - Model User / Reference User Access Requests
 * Clone access from a reference/template user to a target user.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowLeftIcon,
  MagnifyingGlassIcon,
  UserIcon,
  UsersIcon,
  DocumentDuplicateIcon,
  ArrowsRightLeftIcon,
  CheckCircleIcon,
  XCircleIcon,
  CheckIcon,
  XMarkIcon,
  SparklesIcon,
  ClockIcon,
  ShieldCheckIcon,
  BoltIcon,
  ChevronRightIcon,
  ArrowPathIcon,
  PlusCircleIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ModelTemplate {
  id: string;
  name: string;
  department: string;
  position: string;
  roles_count: number;
  roles: string[];
  last_updated: string;
  usage_count: number;
  compliance_rate: number;
  description?: string;
}

interface UserSearchResult {
  id: string;
  username: string;
  display_name: string;
  email: string;
  department: string;
  position: string;
  avatar_initials: string;
}

interface RoleGap {
  role_id: string;
  role_name: string;
  system: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  model_user_has: boolean;
  target_user_has: boolean;
  action: 'request' | 'skip';
  business_process?: string;
}

interface ComparisonResult {
  model_user: UserSearchResult;
  target_user: UserSearchResult;
  total_model_roles: number;
  total_target_roles: number;
  gaps: RoleGap[];
  overlap_count: number;
  gap_count: number;
  extra_count: number;
}

interface ModelUserStats {
  model_templates: number;
  active_comparisons: number;
  requests_generated: number;
  compliance_rate: number;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const modelUserApi = {
  getStats: () => api.get('/model-user/stats').catch(() => ({ data: null })),
  getTemplates: () => api.get('/model-user/templates').catch(() => ({ data: { items: [] } })),
  compare: (payload: { model_user_id: string; target_user_id: string }) =>
    api.post('/model-user/compare', payload),
  generateRequest: (payload: { model_user_id: string; target_user_id: string; role_ids: string[]; justification: string }) =>
    api.post('/model-user/generate-request', payload),
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const riskColors: Record<string, string> = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
};

function StatCard({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: string | number; color: string }) {
  return (
    <div className="bg-white shadow rounded-lg p-5 flex items-center gap-4">
      <div className={`flex-shrink-0 p-3 rounded-lg ${color}`}>
        <Icon className="h-6 w-6" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  );
}

function UserSearchPanel({
  label,
  searchTerm,
  onSearchChange,
  results,
  selectedUser,
  onSelectUser,
  isSearching,
  placeholder,
}: {
  label: string;
  searchTerm: string;
  onSearchChange: (v: string) => void;
  results: UserSearchResult[];
  selectedUser: UserSearchResult | null;
  onSelectUser: (u: UserSearchResult) => void;
  isSearching: boolean;
  placeholder?: string;
}) {
  return (
    <div className="flex-1 min-w-0">
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>

      {selectedUser ? (
        <div className="flex items-center gap-3 p-4 border-2 border-primary-500 bg-primary-50 rounded-lg">
          <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center text-sm font-bold text-primary-700 flex-shrink-0">
            {selectedUser.avatar_initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 truncate">{selectedUser.display_name}</p>
            <p className="text-xs text-gray-500 truncate">{selectedUser.username} · {selectedUser.department}</p>
            <p className="text-xs text-gray-400 truncate">{selectedUser.position}</p>
          </div>
          <button
            onClick={() => onSelectUser(null as any)}
            className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 rounded"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={placeholder ?? 'Search by name, username or department…'}
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      )}

      {!selectedUser && searchTerm.length >= 1 && (
        <div className="mt-1 border border-gray-200 rounded-md shadow-sm bg-white overflow-hidden max-h-48 overflow-y-auto z-10 relative">
          {isSearching ? (
            <div className="p-3 text-sm text-gray-400 text-center">Searching…</div>
          ) : results.length === 0 ? (
            <div className="p-3 text-sm text-gray-400 text-center">No users found</div>
          ) : (
            results.map((u) => (
              <button
                key={u.id}
                onClick={() => onSelectUser(u)}
                className="w-full flex items-center gap-3 px-3 py-2 hover:bg-gray-50 text-left border-b border-gray-100 last:border-0"
              >
                <div className="h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-xs font-bold text-gray-600 flex-shrink-0">
                  {u.avatar_initials}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{u.display_name}</p>
                  <p className="text-xs text-gray-500 truncate">{u.username} · {u.department} · {u.position}</p>
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Comparison builder (fallback when API is unavailable)
// Derives gaps from actual role lists on the user objects, if present.
// ---------------------------------------------------------------------------

function buildMockComparison(
  modelUser: UserSearchResult,
  targetUser: UserSearchResult
): ComparisonResult {
  // UserSearchResult may carry a `roles` field depending on the API response shape.
  const modelRoles: string[] = (modelUser as any).roles ?? [];
  const targetRoles: string[] = (targetUser as any).roles ?? [];

  const targetRoleSet = new Set(targetRoles);
  const modelRoleSet = new Set(modelRoles);

  const gaps: RoleGap[] = [];

  // Roles the model user has but the target user does not (true gaps)
  modelRoles.forEach((roleId) => {
    gaps.push({
      role_id: roleId,
      role_name: roleId,
      system: 'UNKNOWN',
      risk_level: 'low',
      model_user_has: true,
      target_user_has: targetRoleSet.has(roleId),
      action: targetRoleSet.has(roleId) ? 'skip' : 'request',
    });
  });

  // Roles the target user has but the model user does not (extras)
  targetRoles.forEach((roleId) => {
    if (!modelRoleSet.has(roleId)) {
      gaps.push({
        role_id: roleId,
        role_name: roleId,
        system: 'UNKNOWN',
        risk_level: 'low',
        model_user_has: false,
        target_user_has: true,
        action: 'skip',
      });
    }
  });

  const overlapCount = modelRoles.filter((r) => targetRoleSet.has(r)).length;
  const gapCount = modelRoles.filter((r) => !targetRoleSet.has(r)).length;
  const extraCount = targetRoles.filter((r) => !modelRoleSet.has(r)).length;

  return {
    model_user: modelUser,
    target_user: targetUser,
    total_model_roles: modelRoles.length,
    total_target_roles: targetRoles.length,
    gaps,
    overlap_count: overlapCount,
    gap_count: gapCount,
    extra_count: extraCount,
  };
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function ModelUser() {
  const queryClient = useQueryClient();

  // --- UI state ---
  const [modelSearch, setModelSearch] = useState('');
  const [targetSearch, setTargetSearch] = useState('');
  const [modelUser, setModelUser] = useState<UserSearchResult | null>(null);
  const [targetUser, setTargetUser] = useState<UserSearchResult | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [gapActions, setGapActions] = useState<Record<string, 'request' | 'skip'>>({});
  const [justification, setJustification] = useState('');
  const [requestSent, setRequestSent] = useState(false);
  const [activeTab, setActiveTab] = useState<'compare' | 'templates'>('compare');

  // --- Data queries ---
  const { data: statsData } = useQuery({
    queryKey: ['modelUserStats'],
    queryFn: () => modelUserApi.getStats(),
  });
  const stats: ModelUserStats = (statsData as any)?.data ?? { model_templates: 0, active_comparisons: 0, requests_generated: 0, compliance_rate: 0 };

  const { data: templatesData, isLoading: templatesLoading } = useQuery({
    queryKey: ['modelUserTemplates'],
    queryFn: () => modelUserApi.getTemplates(),
  });
  const templates: ModelTemplate[] = (templatesData as any)?.data?.items ?? [];

  const modelResults: UserSearchResult[] = [];
  const targetResults: UserSearchResult[] = [];

  // --- Comparison mutation ---
  const compareMutation = useMutation({
    mutationFn: (payload: { model_user_id: string; target_user_id: string }) =>
      modelUserApi.compare(payload),
    onSuccess: (res: any) => {
      const result: ComparisonResult = res?.data ?? buildMockComparison(modelUser!, targetUser!);
      setComparison(result);
      // Initialise gap actions from server defaults
      const initialActions: Record<string, 'request' | 'skip'> = {};
      result.gaps.forEach((g) => {
        initialActions[g.role_id] = g.action;
      });
      setGapActions(initialActions);
      setRequestSent(false);
    },
    onError: () => {
      toast.error('Gap analysis failed — the comparison service is unavailable.');
    },
  });

  // --- Generate request mutation ---
  const generateMutation = useMutation({
    mutationFn: (payload: { model_user_id: string; target_user_id: string; role_ids: string[]; justification: string }) =>
      modelUserApi.generateRequest(payload),
    onSuccess: () => {
      toast.success('Access request generated successfully!');
      setRequestSent(true);
      queryClient.invalidateQueries({ queryKey: ['modelUserStats'] });
    },
    onError: () => {
      toast.error('Failed to generate access request. Please try again.');
    },
  });

  const handleCompare = () => {
    if (!modelUser || !targetUser) return;
    compareMutation.mutate({ model_user_id: modelUser.id, target_user_id: targetUser.id });
  };

  const toggleGapAction = (roleId: string) => {
    setGapActions((prev) => ({
      ...prev,
      [roleId]: prev[roleId] === 'request' ? 'skip' : 'request',
    }));
  };

  const requestAll = () => {
    if (!comparison) return;
    const next: Record<string, 'request' | 'skip'> = {};
    comparison.gaps.forEach((g) => {
      next[g.role_id] = g.model_user_has && !g.target_user_has ? 'request' : 'skip';
    });
    setGapActions(next);
  };

  const skipAll = () => {
    if (!comparison) return;
    const next: Record<string, 'request' | 'skip'> = {};
    comparison.gaps.forEach((g) => { next[g.role_id] = 'skip'; });
    setGapActions(next);
  };

  const handleGenerateRequest = () => {
    if (!modelUser || !targetUser || !comparison) return;
    const roleIds = Object.entries(gapActions)
      .filter(([, action]) => action === 'request')
      .map(([id]) => id);
    if (roleIds.length === 0) {
      toast.error('No roles selected to request.');
      return;
    }
    if (justification.trim().length < 10) {
      toast.error('Please provide a justification (at least 10 characters).');
      return;
    }
    generateMutation.mutate({
      model_user_id: modelUser.id,
      target_user_id: targetUser.id,
      role_ids: roleIds,
      justification: justification.trim(),
    });
  };

  const handleUseTemplate = (template: ModelTemplate) => {
    setActiveTab('compare');
    toast.success(`Template "${template.name}" loaded — search for a target user to compare.`);
  };

  const requestedCount = Object.values(gapActions).filter((a) => a === 'request').length;
  const gapsOnly = comparison?.gaps.filter((g) => g.model_user_has && !g.target_user_has) ?? [];

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------------ */}
      {/* Header                                                              */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Link
            to="/access-requests"
            className="mr-4 p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Model User Access Request</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Clone access from a reference user or template — request only the missing roles.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <SparklesIcon className="h-5 w-5 text-primary-500" />
          <span className="text-sm text-primary-600 font-medium">AI-Assisted Gap Analysis</span>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Stats cards                                                         */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={DocumentDuplicateIcon}
          label="Model Templates"
          value={stats.model_templates}
          color="bg-blue-50 text-blue-600"
        />
        <StatCard
          icon={ArrowsRightLeftIcon}
          label="Active Comparisons"
          value={stats.active_comparisons}
          color="bg-purple-50 text-purple-600"
        />
        <StatCard
          icon={BoltIcon}
          label="Requests Generated"
          value={stats.requests_generated}
          color="bg-orange-50 text-orange-600"
        />
        <StatCard
          icon={ShieldCheckIcon}
          label="Compliance Rate"
          value={`${stats.compliance_rate}%`}
          color="bg-green-50 text-green-600"
        />
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Tab switcher                                                        */}
      {/* ------------------------------------------------------------------ */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {[
            { id: 'compare', label: 'User Comparison', icon: ArrowsRightLeftIcon },
            { id: 'templates', label: 'Model Templates', icon: DocumentDuplicateIcon },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as any)}
              className={`flex items-center gap-2 pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
                activeTab === id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* ================================================================== */}
      {/* TAB: User Comparison                                                */}
      {/* ================================================================== */}
      {activeTab === 'compare' && (
        <div className="space-y-6">
          {/* User selection panel */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-1">Select Users to Compare</h2>
            <p className="text-sm text-gray-500 mb-5">
              Search for a model user (reference) and a target user, then run the gap analysis.
            </p>

            <div className="flex flex-col md:flex-row items-start gap-4">
              {/* Model user search */}
              <UserSearchPanel
                label="Model User (Reference)"
                searchTerm={modelSearch}
                onSearchChange={(v) => {
                  setModelSearch(v);
                  if (modelUser) setModelUser(null);
                }}
                results={modelResults}
                selectedUser={modelUser}
                onSelectUser={(u) => {
                  setModelUser(u || null);
                  setModelSearch('');
                  setComparison(null);
                }}
                isSearching={false}
                placeholder="Search reference user…"
              />

              {/* Arrow */}
              <div className="hidden md:flex flex-col items-center justify-center pt-8">
                <ChevronRightIcon className="h-6 w-6 text-gray-400" />
              </div>

              {/* Target user search */}
              <UserSearchPanel
                label="Target User (Receiving Access)"
                searchTerm={targetSearch}
                onSearchChange={(v) => {
                  setTargetSearch(v);
                  if (targetUser) setTargetUser(null);
                }}
                results={targetResults}
                selectedUser={targetUser}
                onSelectUser={(u) => {
                  setTargetUser(u || null);
                  setTargetSearch('');
                  setComparison(null);
                }}
                isSearching={false}
                placeholder="Search target user…"
              />
            </div>

            <div className="mt-5 flex justify-end">
              <button
                onClick={handleCompare}
                disabled={!modelUser || !targetUser || compareMutation.isPending}
                className="flex items-center gap-2 px-5 py-2 bg-primary-600 text-white text-sm font-medium rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {compareMutation.isPending ? (
                  <>
                    <ArrowPathIcon className="h-4 w-4 animate-spin" />
                    Analysing…
                  </>
                ) : (
                  <>
                    <ArrowsRightLeftIcon className="h-4 w-4" />
                    Run Gap Analysis
                  </>
                )}
              </button>
            </div>
          </div>

          {/* ---------------------------------------------------------------- */}
          {/* Comparison result                                                 */}
          {/* ---------------------------------------------------------------- */}
          {comparison && (
            <>
              {/* Side-by-side summary */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Model user card */}
                <div className="bg-white shadow rounded-lg p-5 border-l-4 border-primary-500">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center text-sm font-bold text-primary-700">
                      {comparison.model_user.avatar_initials}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{comparison.model_user.display_name}</p>
                      <p className="text-xs text-gray-500">{comparison.model_user.position}</p>
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 mb-3">Model User (Reference)</div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold text-primary-600">{comparison.total_model_roles}</span>
                    <span className="text-sm text-gray-500">roles assigned</span>
                  </div>
                  <div className="mt-1 text-xs text-gray-400">{comparison.model_user.department}</div>
                </div>

                {/* Overlap stats */}
                <div className="bg-white shadow rounded-lg p-5 flex flex-col items-center justify-center text-center">
                  <ArrowsRightLeftIcon className="h-8 w-8 text-gray-300 mb-2" />
                  <div className="space-y-1">
                    <div>
                      <span className="text-xl font-bold text-green-600">{comparison.overlap_count}</span>
                      <span className="text-xs text-gray-500 ml-1">shared</span>
                    </div>
                    <div>
                      <span className="text-xl font-bold text-orange-500">{comparison.gap_count}</span>
                      <span className="text-xs text-gray-500 ml-1">gaps</span>
                    </div>
                    <div>
                      <span className="text-xl font-bold text-blue-500">{comparison.extra_count}</span>
                      <span className="text-xs text-gray-500 ml-1">extra (target only)</span>
                    </div>
                  </div>
                </div>

                {/* Target user card */}
                <div className="bg-white shadow rounded-lg p-5 border-l-4 border-gray-300">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="h-10 w-10 rounded-full bg-gray-100 flex items-center justify-center text-sm font-bold text-gray-600">
                      {comparison.target_user.avatar_initials}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{comparison.target_user.display_name}</p>
                      <p className="text-xs text-gray-500">{comparison.target_user.position}</p>
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 mb-3">Target User (Receiving Access)</div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold text-gray-700">{comparison.total_target_roles}</span>
                    <span className="text-sm text-gray-500">roles assigned</span>
                  </div>
                  <div className="mt-1 text-xs text-gray-400">{comparison.target_user.department}</div>
                </div>
              </div>

              {/* Gap table */}
              <div className="bg-white shadow rounded-lg">
                <div className="p-5 border-b border-gray-200 flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-gray-900">Role Gap Analysis</h3>
                    <p className="text-sm text-gray-500 mt-0.5">
                      {comparison.gap_count} gap{comparison.gap_count !== 1 ? 's' : ''} found — select which roles to request.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={requestAll}
                      className="text-xs px-3 py-1.5 border border-primary-300 text-primary-700 rounded-md hover:bg-primary-50 transition-colors"
                    >
                      Request All Gaps
                    </button>
                    <button
                      onClick={skipAll}
                      className="text-xs px-3 py-1.5 border border-gray-300 text-gray-600 rounded-md hover:bg-gray-50 transition-colors"
                    >
                      Skip All
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role Name</th>
                        <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">System</th>
                        <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Business Process</th>
                        <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Risk</th>
                        <th className="px-5 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                          {comparison.model_user.display_name.split(' ')[0]} Has
                        </th>
                        <th className="px-5 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                          {comparison.target_user.display_name.split(' ')[0]} Has
                        </th>
                        <th className="px-5 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {comparison.gaps.map((gap) => {
                        const isGap = gap.model_user_has && !gap.target_user_has;
                        const action = gapActions[gap.role_id] ?? gap.action;
                        return (
                          <tr
                            key={gap.role_id}
                            className={`${isGap && action === 'request' ? 'bg-orange-50' : ''} hover:bg-gray-50 transition-colors`}
                          >
                            <td className="px-5 py-3">
                              <div className="text-sm font-medium text-gray-900">{gap.role_name}</div>
                              {isGap && (
                                <div className="text-xs text-orange-600 font-medium mt-0.5">Missing from target</div>
                              )}
                            </td>
                            <td className="px-5 py-3">
                              <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                {gap.system}
                              </span>
                            </td>
                            <td className="px-5 py-3 text-sm text-gray-500">{gap.business_process ?? '—'}</td>
                            <td className="px-5 py-3">
                              <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${riskColors[gap.risk_level]}`}>
                                {gap.risk_level}
                              </span>
                            </td>
                            <td className="px-5 py-3 text-center">
                              {gap.model_user_has ? (
                                <CheckCircleIcon className="h-5 w-5 text-green-500 mx-auto" />
                              ) : (
                                <XCircleIcon className="h-5 w-5 text-gray-300 mx-auto" />
                              )}
                            </td>
                            <td className="px-5 py-3 text-center">
                              {gap.target_user_has ? (
                                <CheckCircleIcon className="h-5 w-5 text-green-500 mx-auto" />
                              ) : (
                                <XCircleIcon className="h-5 w-5 text-red-400 mx-auto" />
                              )}
                            </td>
                            <td className="px-5 py-3 text-center">
                              {isGap ? (
                                <button
                                  onClick={() => toggleGapAction(gap.role_id)}
                                  className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                                    action === 'request'
                                      ? 'bg-primary-100 text-primary-800 border-primary-300 hover:bg-primary-200'
                                      : 'bg-gray-100 text-gray-600 border-gray-300 hover:bg-gray-200'
                                  }`}
                                >
                                  {action === 'request' ? (
                                    <><CheckIcon className="h-3 w-3" /> Request</>
                                  ) : (
                                    <><XMarkIcon className="h-3 w-3" /> Skipped</>
                                  )}
                                </button>
                              ) : (
                                <span className="text-xs text-gray-400 italic">
                                  {gap.target_user_has && !gap.model_user_has ? 'Extra' : 'Has access'}
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Generate request panel */}
                {gapsOnly.length > 0 && !requestSent && (
                  <div className="p-5 border-t border-gray-200 bg-gray-50">
                    <div className="flex flex-col md:flex-row md:items-end gap-4">
                      <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Business Justification <span className="text-red-500">*</span>
                        </label>
                        <textarea
                          value={justification}
                          onChange={(e) => setJustification(e.target.value)}
                          rows={2}
                          placeholder="Explain the business reason for cloning access from the model user…"
                          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500 resize-none"
                        />
                        <p className="mt-0.5 text-xs text-gray-400">{justification.length}/500 characters</p>
                      </div>
                      <div className="flex-shrink-0">
                        <button
                          onClick={handleGenerateRequest}
                          disabled={requestedCount === 0 || justification.trim().length < 10 || generateMutation.isPending}
                          className="flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white text-sm font-medium rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                        >
                          {generateMutation.isPending ? (
                            <><ArrowPathIcon className="h-4 w-4 animate-spin" /> Generating…</>
                          ) : (
                            <><PlusCircleIcon className="h-4 w-4" /> Generate Request ({requestedCount} role{requestedCount !== 1 ? 's' : ''})</>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Success state */}
                {requestSent && (
                  <div className="p-5 border-t border-gray-200 bg-green-50">
                    <div className="flex items-center gap-3">
                      <CheckCircleIcon className="h-6 w-6 text-green-500 flex-shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-green-800">Access request generated successfully!</p>
                        <p className="text-xs text-green-700 mt-0.5">
                          {requestedCount} role{requestedCount !== 1 ? 's' : ''} requested for {comparison.target_user.display_name} — pending approval workflow.
                        </p>
                      </div>
                      <div className="ml-auto flex gap-2">
                        <Link
                          to="/access-requests"
                          className="text-xs px-3 py-1.5 bg-white border border-green-300 text-green-700 rounded-md hover:bg-green-50 transition-colors"
                        >
                          View Requests
                        </Link>
                        <button
                          onClick={() => {
                            setComparison(null);
                            setModelUser(null);
                            setTargetUser(null);
                            setRequestSent(false);
                            setJustification('');
                            setGapActions({});
                          }}
                          className="text-xs px-3 py-1.5 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                        >
                          New Comparison
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Empty state when no comparison yet */}
          {!comparison && !compareMutation.isPending && (
            <div className="bg-white shadow rounded-lg p-12 text-center">
              <ArrowsRightLeftIcon className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-base font-medium text-gray-900 mb-1">No Comparison Yet</h3>
              <p className="text-sm text-gray-500 max-w-sm mx-auto">
                Select a model user and a target user above, then click <strong>Run Gap Analysis</strong> to identify missing roles.
              </p>
              <p className="text-xs text-gray-400 mt-3">
                Alternatively, use a pre-built template from the <button onClick={() => setActiveTab('templates')} className="text-primary-600 underline hover:no-underline">Model Templates</button> tab.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ================================================================== */}
      {/* TAB: Model Templates                                                */}
      {/* ================================================================== */}
      {activeTab === 'templates' && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-5 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-gray-900">Pre-Built Model Templates</h2>
              <p className="text-sm text-gray-500 mt-0.5">
                Curated role bundles by department and position — use them as a model user for rapid comparison.
              </p>
            </div>
            <span className="text-xs text-gray-400">{templates.length} templates</span>
          </div>

          {templatesLoading ? (
            <div className="p-12 text-center">
              <ArrowPathIcon className="h-8 w-8 text-gray-300 mx-auto animate-spin mb-3" />
              <p className="text-sm text-gray-400">Loading templates…</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Template Name</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Department</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Position</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Roles Included</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Compliance</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Updated</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Used</th>
                    <th className="px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {templates.map((tpl) => (
                    <tr key={tpl.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-9 w-9 rounded-lg bg-primary-50 flex items-center justify-center flex-shrink-0">
                            <UsersIcon className="h-5 w-5 text-primary-600" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">{tpl.name}</p>
                            {tpl.description && (
                              <p className="text-xs text-gray-400 mt-0.5 max-w-xs truncate">{tpl.description}</p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                          {tpl.department}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-sm text-gray-600">{tpl.position}</td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-1">
                          <span className="text-sm font-semibold text-gray-900">{tpl.roles_count}</span>
                          <span className="text-xs text-gray-400">roles</span>
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {tpl.roles.slice(0, 3).map((r) => (
                            <span key={r} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                              {r}
                            </span>
                          ))}
                          {tpl.roles.length > 3 && (
                            <span className="text-xs text-gray-400">+{tpl.roles.length - 3} more</span>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-1.5">
                          <div className="flex-1 bg-gray-200 rounded-full h-1.5 w-16">
                            <div
                              className={`h-1.5 rounded-full ${
                                tpl.compliance_rate >= 95 ? 'bg-green-500' :
                                tpl.compliance_rate >= 85 ? 'bg-yellow-500' : 'bg-red-500'
                              }`}
                              style={{ width: `${tpl.compliance_rate}%` }}
                            />
                          </div>
                          <span className={`text-xs font-medium ${
                            tpl.compliance_rate >= 95 ? 'text-green-700' :
                            tpl.compliance_rate >= 85 ? 'text-yellow-700' : 'text-red-700'
                          }`}>
                            {tpl.compliance_rate}%
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          <ClockIcon className="h-3.5 w-3.5" />
                          {new Date(tpl.last_updated).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                        </div>
                      </td>
                      <td className="px-5 py-4 text-sm text-gray-500">{tpl.usage_count}×</td>
                      <td className="px-5 py-4 text-right">
                        <button
                          onClick={() => handleUseTemplate(tpl)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                        >
                          <UserIcon className="h-3.5 w-3.5" />
                          Use as Model
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
