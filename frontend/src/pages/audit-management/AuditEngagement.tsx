import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  ChevronRightIcon,
  BriefcaseIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import { auditManagementApi } from '../../services/auditManagementApi';
import {
  PageHeader,
  Card,
  Badge,
  Button,
  Modal,
  Input,
  Select,
  Textarea,
  SearchInput,
  LoadingState,
  ErrorState,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AuditEngagement {
  id: string;
  title: string;
  objective: string;
  scope: string;
  engagement_type: string;
  plan_id: string | null;
  entity_id: string | null;
  entity_name: string | null;
  lead_auditor: string;
  team_members: string[];
  planned_start: string;
  planned_end: string;
  budget_hours: number;
  actual_hours: number;
  status: string;
}

interface CreateEngagementForm {
  title: string;
  objective: string;
  scope: string;
  engagement_type: string;
  plan_id: string;
  entity_id: string;
  lead_auditor: string;
  team_members: string;
  planned_start: string;
  planned_end: string;
  budget_hours: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PIPELINE_STAGES = [
  { key: 'planned', label: 'Planned' },
  { key: 'announced', label: 'Announced' },
  { key: 'fieldwork', label: 'Fieldwork' },
  { key: 'draft_report', label: 'Draft Report' },
  { key: 'final_report', label: 'Final Report' },
  { key: 'closed', label: 'Closed' },
];

const STATUS_BADGE: Record<string, 'neutral' | 'info' | 'warning' | 'success' | 'danger'> = {
  planned: 'neutral',
  announced: 'info',
  fieldwork: 'warning',
  draft_report: 'warning',
  final_report: 'success',
  closed: 'neutral',
};

const STATUS_FILTER_OPTIONS = [
  { value: '', label: 'All Statuses' },
  ...PIPELINE_STAGES.map((s) => ({ value: s.key, label: s.label })),
];

const TYPE_OPTIONS = [
  { value: 'internal', label: 'Internal Audit' },
  { value: 'compliance', label: 'Compliance' },
  { value: 'operational', label: 'Operational' },
  { value: 'financial', label: 'Financial' },
  { value: 'it', label: 'IT Audit' },
  { value: 'advisory', label: 'Advisory' },
];

const TYPE_FILTER_OPTIONS = [{ value: '', label: 'All Types' }, ...TYPE_OPTIONS];

const TYPE_BADGE: Record<string, 'info' | 'warning' | 'success' | 'neutral' | 'danger'> = {
  internal: 'info',
  compliance: 'warning',
  operational: 'neutral',
  financial: 'success',
  it: 'info',
  advisory: 'neutral',
};

const EMPTY_FORM: CreateEngagementForm = {
  title: '', objective: '', scope: '', engagement_type: 'internal',
  plan_id: '', entity_id: '', lead_auditor: '', team_members: '',
  planned_start: '', planned_end: '', budget_hours: '',
};

function formatDate(iso: string): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: '2-digit' });
}

function getNextStageLabel(status: string): string {
  const idx = PIPELINE_STAGES.findIndex((s) => s.key === status);
  if (idx < 0 || idx >= PIPELINE_STAGES.length - 1) return '';
  return PIPELINE_STAGES[idx + 1].label;
}

// ─── Pipeline Progress Dots ───────────────────────────────────────────────────

function PipelineDots({ currentStatus }: { currentStatus: string }) {
  const currentIdx = PIPELINE_STAGES.findIndex((s) => s.key === currentStatus);
  return (
    <div className="flex items-center gap-1">
      {PIPELINE_STAGES.map((stage, idx) => {
        const isPast = idx < currentIdx;
        const isCurrent = idx === currentIdx;
        return (
          <div key={stage.key} className="flex items-center">
            <div
              title={stage.label}
              className={`w-2 h-2 rounded-full transition-colors ${
                isCurrent
                  ? 'bg-indigo-500 ring-2 ring-indigo-200 dark:ring-indigo-800'
                  : isPast
                  ? 'bg-emerald-400'
                  : 'bg-gray-200 dark:bg-gray-700'
              }`}
            />
            {idx < PIPELINE_STAGES.length - 1 && (
              <div className={`w-3 h-px ${idx < currentIdx ? 'bg-emerald-400' : 'bg-gray-200 dark:bg-gray-700'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function AuditEngagement() {
  const qc = useQueryClient();

  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [leadSearch, setLeadSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [confirmAdvance, setConfirmAdvance] = useState<AuditEngagement | null>(null);
  const [form, setForm] = useState<CreateEngagementForm>(EMPTY_FORM);

  // ── Query ──────────────────────────────────────────────────────────────────

  const { data, isLoading, error } = useQuery<AuditEngagement[]>({
    queryKey: ['audit-management', 'engagements', { statusFilter, typeFilter, leadSearch }],
    queryFn: async () => {
      const res = await auditManagementApi.listEngagements({
        status: statusFilter || undefined,
        engagement_type: typeFilter || undefined,
        lead_auditor: leadSearch || undefined,
      });
      return res.data;
    },
  });

  // ── Mutations ─────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (f: CreateEngagementForm) =>
      auditManagementApi.createEngagement({
        ...f,
        budget_hours: parseInt(f.budget_hours),
        team_members: f.team_members ? f.team_members.split(',').map((s) => s.trim()).filter(Boolean) : [],
        plan_id: f.plan_id || null,
        entity_id: f.entity_id || null,
      }),
    onSuccess: () => {
      toast.success('Engagement created successfully');
      qc.invalidateQueries({ queryKey: ['audit-management', 'engagements'] });
      setShowCreate(false);
      setForm(EMPTY_FORM);
    },
    onError: () => toast.error('Failed to create engagement'),
  });

  const advanceMutation = useMutation({
    mutationFn: (id: string) => auditManagementApi.advanceEngagement(id),
    onSuccess: () => {
      toast.success('Engagement advanced to next stage');
      qc.invalidateQueries({ queryKey: ['audit-management', 'engagements'] });
      setConfirmAdvance(null);
    },
    onError: () => toast.error('Failed to advance engagement'),
  });

  const engagements = data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Engagements"
        subtitle="Track audit engagements through the full fieldwork-to-report lifecycle"
        breadcrumbs={[{ label: 'Audit Management' }, { label: 'Engagements' }]}
        actions={
          <Button
            variant="primary"
            size="sm"
            icon={<PlusIcon className="h-4 w-4" />}
            onClick={() => setShowCreate(true)}
          >
            New Engagement
          </Button>
        }
      />

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[200px]">
            <SearchInput
              value={leadSearch}
              onChange={(e) => setLeadSearch(e.target.value)}
              onClear={() => setLeadSearch('')}
              placeholder="Search by lead auditor..."
            />
          </div>
          <div className="w-44">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={STATUS_FILTER_OPTIONS}
            />
          </div>
          <div className="w-44">
            <Select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              options={TYPE_FILTER_OPTIONS}
            />
          </div>
        </div>
      </Card>

      {/* Table */}
      {isLoading && <LoadingState />}
      {error && <ErrorState message="Failed to load engagements" />}
      {!isLoading && !error && (
        <Card padding="none">
          {engagements.length === 0 ? (
            <div className="py-16 text-center">
              <BriefcaseIcon className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-sm text-gray-500 dark:text-gray-400">No engagements found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100 dark:border-slate-700">
                    {['ID', 'Title', 'Type', 'Entity', 'Lead Auditor', 'Period', 'Progress', 'Hours', 'Status', 'Actions'].map((h) => (
                      <th key={h} className="px-4 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50 dark:divide-slate-700/50">
                  {engagements.map((eng) => {
                    const nextLabel = getNextStageLabel(eng.status);
                    return (
                      <tr key={eng.id} className="hover:bg-gray-50/50 dark:hover:bg-slate-700/30 transition-colors">
                        <td className="px-4 py-3.5 text-xs font-mono text-gray-400 dark:text-gray-500">
                          {eng.id.slice(0, 8)}
                        </td>
                        <td className="px-4 py-3.5 max-w-[200px]">
                          <p className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">{eng.title}</p>
                          {eng.objective && (
                            <p className="text-xs text-gray-400 dark:text-gray-500 truncate mt-0.5">{eng.objective}</p>
                          )}
                        </td>
                        <td className="px-4 py-3.5">
                          <Badge variant={TYPE_BADGE[eng.engagement_type] ?? 'neutral'}>
                            {eng.engagement_type}
                          </Badge>
                        </td>
                        <td className="px-4 py-3.5 text-sm text-gray-600 dark:text-gray-400 max-w-[120px] truncate">
                          {eng.entity_name ?? '-'}
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-1.5">
                            <UserIcon className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                            <span className="text-sm text-gray-700 dark:text-gray-300">{eng.lead_auditor}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3.5 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                          <div>{formatDate(eng.planned_start)}</div>
                          <div className="flex items-center gap-0.5 text-gray-300 dark:text-gray-600">
                            <ChevronRightIcon className="h-3 w-3" />
                            {formatDate(eng.planned_end)}
                          </div>
                        </td>
                        <td className="px-4 py-3.5">
                          <PipelineDots currentStatus={eng.status} />
                        </td>
                        <td className="px-4 py-3.5 text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                          <span className="font-medium text-gray-900 dark:text-gray-100">{eng.actual_hours}</span>
                          <span className="text-gray-400">/{eng.budget_hours}h</span>
                        </td>
                        <td className="px-4 py-3.5">
                          <Badge variant={STATUS_BADGE[eng.status] ?? 'neutral'} dot>
                            {eng.status.replace('_', ' ')}
                          </Badge>
                        </td>
                        <td className="px-4 py-3.5">
                          {eng.status !== 'closed' && nextLabel && (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => setConfirmAdvance(eng)}
                            >
                              → {nextLabel}
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Create Engagement Modal */}
      <Modal
        open={showCreate}
        onClose={() => { setShowCreate(false); setForm(EMPTY_FORM); }}
        title="New Audit Engagement"
        subtitle="Create a new audit engagement under a plan"
        size="xl"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setShowCreate(false); setForm(EMPTY_FORM); }}>
              Cancel
            </Button>
            <Button
              variant="primary"
              loading={createMutation.isPending}
              onClick={() => createMutation.mutate(form)}
              disabled={!form.title || !form.lead_auditor || !form.planned_start || !form.planned_end || !form.budget_hours}
            >
              Create Engagement
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input
            label="Title"
            required
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            placeholder="e.g. Accounts Payable Process Audit"
          />
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Engagement Type"
              required
              value={form.engagement_type}
              onChange={(e) => setForm((f) => ({ ...f, engagement_type: e.target.value }))}
              options={TYPE_OPTIONS}
            />
            <Input
              label="Lead Auditor"
              required
              value={form.lead_auditor}
              onChange={(e) => setForm((f) => ({ ...f, lead_auditor: e.target.value }))}
              placeholder="Full name or username"
            />
          </div>
          <Textarea
            label="Objective"
            value={form.objective}
            onChange={(e) => setForm((f) => ({ ...f, objective: e.target.value }))}
            placeholder="What is the audit designed to achieve?"
            rows={2}
          />
          <Textarea
            label="Scope"
            value={form.scope}
            onChange={(e) => setForm((f) => ({ ...f, scope: e.target.value }))}
            placeholder="Processes, systems, and time period in scope..."
            rows={2}
          />
          <Input
            label="Team Members (comma-separated)"
            value={form.team_members}
            onChange={(e) => setForm((f) => ({ ...f, team_members: e.target.value }))}
            placeholder="e.g. alice, bob, carol"
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Plan ID (optional)"
              value={form.plan_id}
              onChange={(e) => setForm((f) => ({ ...f, plan_id: e.target.value }))}
              placeholder="Leave blank if ad hoc"
            />
            <Input
              label="Entity ID (optional)"
              value={form.entity_id}
              onChange={(e) => setForm((f) => ({ ...f, entity_id: e.target.value }))}
              placeholder="Auditable entity ID"
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Input
              label="Planned Start"
              type="date"
              required
              value={form.planned_start}
              onChange={(e) => setForm((f) => ({ ...f, planned_start: e.target.value }))}
            />
            <Input
              label="Planned End"
              type="date"
              required
              value={form.planned_end}
              onChange={(e) => setForm((f) => ({ ...f, planned_end: e.target.value }))}
            />
            <Input
              label="Budget Hours"
              type="number"
              required
              min="1"
              value={form.budget_hours}
              onChange={(e) => setForm((f) => ({ ...f, budget_hours: e.target.value }))}
              placeholder="e.g. 120"
            />
          </div>
        </div>
      </Modal>

      {/* Confirm Advance Modal */}
      <Modal
        open={!!confirmAdvance}
        onClose={() => setConfirmAdvance(null)}
        title="Advance Engagement Stage"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmAdvance(null)}>Cancel</Button>
            <Button
              variant="primary"
              loading={advanceMutation.isPending}
              onClick={() => confirmAdvance && advanceMutation.mutate(confirmAdvance.id)}
            >
              Advance to {getNextStageLabel(confirmAdvance?.status ?? '')}
            </Button>
          </>
        }
      >
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Move <span className="font-semibold text-gray-900 dark:text-gray-100">"{confirmAdvance?.title}"</span> from{' '}
          <Badge variant={STATUS_BADGE[confirmAdvance?.status ?? ''] ?? 'neutral'}>
            {confirmAdvance?.status?.replace('_', ' ')}
          </Badge>{' '}
          to{' '}
          <Badge variant="info">{getNextStageLabel(confirmAdvance?.status ?? '')}</Badge>?
        </p>
      </Modal>
    </div>
  );
}
