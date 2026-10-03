import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  BuildingOfficeIcon,
  PlusIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  CalendarDaysIcon,
  FunnelIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  CardHeader,
  CardBody,
  Button,
  Badge,
  Modal,
  Input,
  LoadingState,
  EmptyState,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';

// ─── Types ────────────────────────────────────────────────────────────────────

type OrgField = 'BUKRS' | 'WERKS' | 'EKORG' | 'VKORG' | 'GSBER' | 'KOKRS';
type ConditionType = 'equals' | 'in_list' | 'range' | 'hierarchy';

interface OrgRule {
  id: string;
  name: string;
  org_field: OrgField;
  condition_type: ConditionType;
  condition_value: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface OrgRuleStats {
  total: number;
  active: number;
  org_fields_covered: number;
  last_updated: string;
}

interface HierarchyNode {
  id: string;
  label: string;
  field: OrgField;
  value: string;
  children?: HierarchyNode[];
}

interface OrgRuleForm {
  name: string;
  org_field: OrgField;
  condition_type: ConditionType;
  condition_value: string;
  description: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const ORG_FIELD_OPTIONS: { value: OrgField; label: string; description: string }[] = [
  { value: 'BUKRS', label: 'BUKRS', description: 'Company Code' },
  { value: 'WERKS', label: 'WERKS', description: 'Plant' },
  { value: 'EKORG', label: 'EKORG', description: 'Purchasing Organisation' },
  { value: 'VKORG', label: 'VKORG', description: 'Sales Organisation' },
  { value: 'GSBER', label: 'GSBER', description: 'Business Area' },
  { value: 'KOKRS', label: 'KOKRS', description: 'Controlling Area' },
];

const CONDITION_TYPE_OPTIONS: { value: ConditionType; label: string; hint: string }[] = [
  { value: 'equals', label: 'Equals', hint: 'Exact single value match' },
  { value: 'in_list', label: 'In List', hint: 'Comma-separated list of values' },
  { value: 'range', label: 'Range', hint: 'Numeric range, e.g. 1000 - 1999' },
  { value: 'hierarchy', label: 'Hierarchy', hint: 'Match node and all descendants' },
];

const ORG_FIELD_COLORS: Record<OrgField, string> = {
  BUKRS: 'blue',
  WERKS: 'purple',
  EKORG: 'green',
  VKORG: 'yellow',
  GSBER: 'orange',
  KOKRS: 'indigo',
};

const CONDITION_COLORS: Record<ConditionType, string> = {
  equals: 'gray',
  in_list: 'blue',
  range: 'green',
  hierarchy: 'purple',
};

const EMPTY_FORM: OrgRuleForm = {
  name: '',
  org_field: 'BUKRS',
  condition_type: 'equals',
  condition_value: '',
  description: '',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  try {
    return new Date(iso || new Date()).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

function getOrgFieldLabel(field: OrgField): string {
  return ORG_FIELD_OPTIONS.find((o) => o.value === field)?.description ?? field;
}

// ─── Hierarchy Tree Node ──────────────────────────────────────────────────────

function HierarchyTreeNode({ node, depth = 0 }: { node: HierarchyNode; depth?: number }) {
  const [expanded, setExpanded] = useState(depth < 1);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div>
      <div
        className={`flex items-center gap-2 py-1.5 px-2 rounded-lg cursor-pointer hover:bg-white/5 transition-colors group ${
          depth === 0 ? 'mt-1' : ''
        }`}
        style={{ paddingLeft: `${8 + depth * 20}px` }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDownIcon className="h-3.5 w-3.5 text-white/40 flex-shrink-0" />
          ) : (
            <ChevronRightIcon className="h-3.5 w-3.5 text-white/40 flex-shrink-0" />
          )
        ) : (
          <span className="h-3.5 w-3.5 flex-shrink-0" />
        )}
        <BuildingOfficeIcon className="h-4 w-4 text-white/40 flex-shrink-0" />
        <span className="text-sm text-white/80 font-medium">{node.label}</span>
        <span
          className={`ml-auto text-xs px-1.5 py-0.5 rounded font-mono opacity-0 group-hover:opacity-100 transition-opacity bg-white/10 text-white/60`}
        >
          {node.value}
        </span>
        <Badge variant={ORG_FIELD_COLORS[node.field] as any}>{node.field}</Badge>
      </div>
      {hasChildren && expanded && (
        <div>
          {node.children!.map((child) => (
            <HierarchyTreeNode key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function OrgRules() {
  const queryClient = useQueryClient();

  // UI state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<OrgRule | null>(null);
  const [showHierarchy, setShowHierarchy] = useState(false);
  const [form, setForm] = useState<OrgRuleForm>(EMPTY_FORM);
  const [fieldFilter, setFieldFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // ── Data queries ────────────────────────────────────────────────────────────

  const {
    data: rulesData,
    isLoading: rulesLoading,
    error: _rulesError,
  } = useQuery<OrgRule[]>({
    queryKey: ['org-rules'],
    queryFn: async () => {
      try {
        const res = await api.get('/org-rules/');
        return res.data?.rules ?? res.data ?? [];
      } catch {
        return [];
      }
    },
  });

  const { data: statsData } = useQuery<OrgRuleStats | null>({
    queryKey: ['org-rules-stats'],
    queryFn: async () => {
      try {
        const res = await api.get('/org-rules/stats');
        return res.data;
      } catch {
        return null;
      }
    },
  });

  const { data: hierarchyData } = useQuery<HierarchyNode[]>({
    queryKey: ['org-rules-hierarchy'],
    queryFn: async () => {
      try {
        const res = await api.get('/org-rules/hierarchy');
        return res.data?.nodes ?? res.data ?? [];
      } catch {
        return [];
      }
    },
    enabled: showHierarchy,
  });

  // ── Mutations ───────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: async (payload: OrgRuleForm) => {
      const res = await api.post('/org-rules/', payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-rules'] });
      queryClient.invalidateQueries({ queryKey: ['org-rules-stats'] });
      setShowCreateModal(false);
      setForm(EMPTY_FORM);
    },
    onError: () => {
      toast.error('Failed to create org rule. Please try again.');
    },
  });

  const toggleMutation = useMutation({
    mutationFn: async (rule: OrgRule) => {
      const res = await api.put(`/org-rules/${rule.id}/toggle`);
      return res.data;
    },
    onMutate: async (rule) => {
      await queryClient.cancelQueries({ queryKey: ['org-rules'] });
      const prev = queryClient.getQueryData<OrgRule[]>(['org-rules']);
      queryClient.setQueryData<OrgRule[]>(['org-rules'], (old) =>
        (old ?? []).map((r) => (r.id === rule.id ? { ...r, is_active: !r.is_active } : r))
      );
      return { prev };
    },
    onError: (_err, _rule, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(['org-rules'], ctx.prev);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['org-rules'] });
      queryClient.invalidateQueries({ queryKey: ['org-rules-stats'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await api.delete(`/org-rules/${id}`);
      return res.data;
    },
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['org-rules'] });
      const prev = queryClient.getQueryData<OrgRule[]>(['org-rules']);
      queryClient.setQueryData<OrgRule[]>(['org-rules'], (old) =>
        (old ?? []).filter((r) => r.id !== id)
      );
      return { prev };
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(['org-rules'], ctx.prev);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['org-rules'] });
      queryClient.invalidateQueries({ queryKey: ['org-rules-stats'] });
      setShowDeleteConfirm(null);
    },
  });

  // ── Derived data ─────────────────────────────────────────────────────────────

  const rules: OrgRule[] = rulesData ?? [];

  const defaultStats: OrgRuleStats = {
    total: 0,
    active: 0,
    org_fields_covered: 0,
    last_updated: new Date().toISOString(),
  };
  const stats: OrgRuleStats = statsData ?? defaultStats;

  const filteredRules = rules.filter((r) => {
    if (fieldFilter && r.org_field !== fieldFilter) return false;
    if (statusFilter === 'active' && !r.is_active) return false;
    if (statusFilter === 'inactive' && r.is_active) return false;
    return true;
  });

  const conditionHint = CONDITION_TYPE_OPTIONS.find((o) => o.value === form.condition_type)?.hint ?? '';

  const isFormValid = form.name.trim() !== '' && form.condition_value.trim() !== '';

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="SAP Org Rules"
        subtitle="Define and manage organisational field restrictions for SAP access policies"
        actions={
          <button
            onClick={() => { setForm(EMPTY_FORM); setShowCreateModal(true); }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-primary-500 hover:bg-primary-600 text-white transition-colors"
          >
            <PlusIcon className="h-4 w-4" />
            New Rule
          </button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Rules"
          value={stats.total}
          icon={FunnelIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Active Rules"
          value={stats.active}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
        <StatCard
          title="Org Fields Covered"
          value={stats.org_fields_covered}
          icon={BuildingOfficeIcon}
          iconBgColor="stat-icon-purple"
          iconColor="text-purple-400"
        />
        <StatCard
          title="Last Updated"
          value={formatDate(stats.last_updated)}
          icon={CalendarDaysIcon}
          iconBgColor="stat-icon-yellow"
          iconColor="text-yellow-400"
        />
      </div>

      {/* Filters & Hierarchy Toggle */}
      <Card padding="md">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-[260px]">
            <label className="text-sm text-white/50 whitespace-nowrap">Org Field</label>
            <select
              value={fieldFilter}
              onChange={(e) => setFieldFilter(e.target.value)}
              className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              <option value="">All Fields</option>
              {ORG_FIELD_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.value} — {o.description}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-white/50 whitespace-nowrap">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              <option value="">All</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
          {(fieldFilter || statusFilter) && (
            <button
              onClick={() => { setFieldFilter(''); setStatusFilter(''); }}
              className="flex items-center gap-1 text-xs text-white/40 hover:text-white/70 transition-colors"
            >
              <XMarkIcon className="h-3.5 w-3.5" />
              Clear filters
            </button>
          )}
          <div className="ml-auto">
            <Button
              variant={showHierarchy ? 'primary' : 'secondary'}
              onClick={() => setShowHierarchy(!showHierarchy)}
            >
              <BuildingOfficeIcon className="h-4 w-4 mr-1.5" />
              {showHierarchy ? 'Hide Hierarchy' : 'View Hierarchy'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Org Hierarchy Tree */}
      {showHierarchy && (
        <Card padding="none">
          <CardHeader
            title="SAP Organisational Hierarchy"
            subtitle="Visualise org field relationships for rule scoping"
          />
          <CardBody>
            {hierarchyData && hierarchyData.length > 0 ? (
              <div className="space-y-1">
                {hierarchyData.map((node) => (
                  <HierarchyTreeNode key={node.id} node={node} depth={0} />
                ))}
              </div>
            ) : (
              <div className="py-6 text-center text-sm text-white/40">
                Loading hierarchy data...
              </div>
            )}
          </CardBody>
        </Card>
      )}

      {/* Rules Table */}
      <Card padding="none">
        <CardHeader
          title={`Organisational Rules${filteredRules.length !== rules.length ? ` (${filteredRules.length} of ${rules.length})` : ` (${rules.length})`}`}
          subtitle="Each rule constrains access based on an SAP organisational field value"
        />

        {rulesLoading && <LoadingState />}

        {!rulesLoading && filteredRules.length === 0 && (
          <EmptyState
            title="No org rules found"
            description={
              fieldFilter || statusFilter
                ? 'Try adjusting your filters'
                : 'Create your first organisational rule to restrict access by SAP org fields'
            }
          />
        )}

        {!rulesLoading && filteredRules.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="px-6 py-3 text-left text-xs font-medium text-white/40 uppercase tracking-wider">
                    Rule Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-white/40 uppercase tracking-wider">
                    Org Field
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-white/40 uppercase tracking-wider">
                    Condition
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-white/40 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-white/40 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredRules.map((rule) => (
                  <tr key={rule.id} className="hover:bg-white/[0.03] transition-colors group">
                    {/* Rule Name */}
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-0.5">
                        <span className="text-sm font-medium text-white">{rule.name}</span>
                        {rule.description && (
                          <span className="text-xs text-white/40 max-w-xs truncate">
                            {rule.description}
                          </span>
                        )}
                        <span className="text-xs text-white/25">
                          Updated {formatDate(rule.updated_at)}
                        </span>
                      </div>
                    </td>

                    {/* Org Field */}
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1">
                        <Badge variant={ORG_FIELD_COLORS[rule.org_field] as any}>
                          {rule.org_field}
                        </Badge>
                        <span className="text-xs text-white/40">
                          {getOrgFieldLabel(rule.org_field)}
                        </span>
                      </div>
                    </td>

                    {/* Condition */}
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1">
                        <Badge variant={CONDITION_COLORS[rule.condition_type] as any}>
                          {rule.condition_type.replace('_', ' ')}
                        </Badge>
                        <code className="text-xs text-white/60 bg-white/5 rounded px-1.5 py-0.5 font-mono max-w-[180px] truncate block">
                          {rule.condition_value}
                        </code>
                      </div>
                    </td>

                    {/* Status */}
                    <td className="px-6 py-4">
                      <button
                        onClick={() => toggleMutation.mutate(rule)}
                        disabled={toggleMutation.isPending}
                        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors cursor-pointer ${
                          rule.is_active
                            ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                            : 'bg-white/10 text-white/40 hover:bg-white/15'
                        }`}
                        title="Click to toggle"
                      >
                        {rule.is_active ? (
                          <>
                            <CheckCircleIcon className="h-3.5 w-3.5" />
                            Active
                          </>
                        ) : (
                          <>
                            <XCircleIcon className="h-3.5 w-3.5" />
                            Inactive
                          </>
                        )}
                      </button>
                    </td>

                    {/* Actions */}
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => toggleMutation.mutate(rule)}
                          disabled={toggleMutation.isPending}
                          className="p-1.5 rounded-lg hover:bg-white/10 text-white/40 hover:text-white transition-colors"
                          title={rule.is_active ? 'Deactivate rule' : 'Activate rule'}
                        >
                          <ArrowPathIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => setShowDeleteConfirm(rule)}
                          className="p-1.5 rounded-lg hover:bg-white/10 text-white/40 hover:text-red-400 transition-colors"
                          title="Delete rule"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* ── Create Rule Modal ──────────────────────────────────────────────────── */}
      {showCreateModal && (
        <Modal
          open={showCreateModal}
          title="Create Organisational Rule"
          onClose={() => {
            setShowCreateModal(false);
            setForm(EMPTY_FORM);
          }}
        >
          <div className="space-y-4">
            {/* Name */}
            <Input
              label="Rule Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Company Code — Germany"
              required
            />

            {/* Org Field */}
            <div className="space-y-1">
              <label className="block text-xs font-medium text-white/60 uppercase tracking-wide">
                Org Field <span className="text-red-400">*</span>
              </label>
              <select
                value={form.org_field}
                onChange={(e) => setForm({ ...form, org_field: e.target.value as OrgField })}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 focus:outline-none focus:ring-1 focus:ring-primary-500"
              >
                {ORG_FIELD_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.value} — {o.description}
                  </option>
                ))}
              </select>
            </div>

            {/* Condition Type */}
            <div className="space-y-1">
              <label className="block text-xs font-medium text-white/60 uppercase tracking-wide">
                Condition Type <span className="text-red-400">*</span>
              </label>
              <select
                value={form.condition_type}
                onChange={(e) =>
                  setForm({ ...form, condition_type: e.target.value as ConditionType })
                }
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 focus:outline-none focus:ring-1 focus:ring-primary-500"
              >
                {CONDITION_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              {conditionHint && (
                <p className="text-xs text-white/35 mt-1">{conditionHint}</p>
              )}
            </div>

            {/* Condition Value */}
            <Input
              label="Condition Value"
              value={form.condition_value}
              onChange={(e) => setForm({ ...form, condition_value: e.target.value })}
              placeholder={
                form.condition_type === 'in_list'
                  ? '1000, 1100, 1200'
                  : form.condition_type === 'range'
                  ? '1000 - 1999'
                  : form.condition_type === 'hierarchy'
                  ? 'Root node value, e.g. FIN_ROOT'
                  : 'Exact value, e.g. 1000'
              }
              required
            />

            {/* Description */}
            <div className="space-y-1">
              <label className="block text-xs font-medium text-white/60 uppercase tracking-wide">
                Description
              </label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={3}
                placeholder="Optional: explain the purpose of this rule"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 placeholder-white/25 focus:outline-none focus:ring-1 focus:ring-primary-500 resize-none"
              />
            </div>

            {/* Preview */}
            {form.name && form.condition_value && (
              <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3 text-xs text-white/50 space-y-1">
                <p className="font-medium text-white/60 uppercase tracking-wide text-[10px]">
                  Preview
                </p>
                <p>
                  <span className="text-white/70">WHERE</span>{' '}
                  <span className="font-mono text-blue-400">{form.org_field}</span>{' '}
                  <span className="text-white/70">{form.condition_type.replace('_', ' ')}</span>{' '}
                  <span className="font-mono text-green-400">{form.condition_value}</span>
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowCreateModal(false);
                  setForm(EMPTY_FORM);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={() => createMutation.mutate(form)}
                disabled={!isFormValid || createMutation.isPending}
              >
                {createMutation.isPending ? 'Creating...' : 'Create Rule'}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ── Delete Confirmation Modal ──────────────────────────────────────────── */}
      {showDeleteConfirm && (
        <Modal
          open={!!showDeleteConfirm}
          title="Delete Org Rule"
          onClose={() => setShowDeleteConfirm(null)}
        >
          <div className="space-y-4">
            <p className="text-sm text-white/70">
              Are you sure you want to delete{' '}
              <span className="font-semibold text-white">"{showDeleteConfirm.name}"</span>?
            </p>
            <p className="text-xs text-white/40">
              This rule restricts{' '}
              <span className="font-mono text-white/60">{showDeleteConfirm.org_field}</span> using a{' '}
              <span className="text-white/60">{showDeleteConfirm.condition_type.replace('_', ' ')}</span> condition.
              Removing it may expand access scope for affected users.
            </p>
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-xs text-red-400">
              This action cannot be undone.
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" onClick={() => setShowDeleteConfirm(null)}>
                Cancel
              </Button>
              <button
                onClick={() => deleteMutation.mutate(showDeleteConfirm.id)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete Rule'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
