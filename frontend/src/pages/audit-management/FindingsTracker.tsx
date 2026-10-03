import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  ArrowUpIcon,
  CheckCircleIcon,
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
  LoadingState,
  ErrorState,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Finding {
  id: string;
  title: string;
  engagement_id: string;
  engagement_title: string;
  severity: string;
  category: string;
  status: string;
  condition: string;
  criteria: string;
  cause: string;
  effect: string;
  recommendation: string;
  management_response: string | null;
  management_response_status: string;
}

interface Action {
  id: string;
  description: string;
  finding_id: string;
  finding_title: string;
  owner_id: string;
  owner_name: string;
  due_date: string;
  status: string;
  evidence_of_closure: string | null;
}

interface CreateFindingForm {
  [key: string]: unknown;
  engagement_id: string;
  title: string;
  severity: string;
  category: string;
  condition: string;
  criteria: string;
  cause: string;
  effect: string;
  recommendation: string;
}

interface MgmtResponseForm {
  [key: string]: unknown;
  response: string;
  action_owner: string;
  target_date: string;
}

interface CreateActionForm {
  [key: string]: unknown;
  description: string;
  owner_id: string;
  owner_name: string;
  due_date: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

type TabKey = 'findings' | 'actions' | 'overdue';

const SEVERITY_OPTIONS = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const SEVERITY_FILTER = [{ value: '', label: 'All Severities' }, ...SEVERITY_OPTIONS];

const CATEGORY_OPTIONS = [
  { value: 'access_control', label: 'Access Control' },
  { value: 'segregation_of_duties', label: 'Segregation of Duties' },
  { value: 'data_integrity', label: 'Data Integrity' },
  { value: 'process_compliance', label: 'Process Compliance' },
  { value: 'financial_reporting', label: 'Financial Reporting' },
  { value: 'it_general_controls', label: 'IT General Controls' },
  { value: 'operational', label: 'Operational' },
  { value: 'other', label: 'Other' },
];

const FINDING_STATUS_FILTER = [
  { value: '', label: 'All Statuses' },
  { value: 'open', label: 'Open' },
  { value: 'in_remediation', label: 'In Remediation' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'accepted', label: 'Risk Accepted' },
  { value: 'closed', label: 'Closed' },
];

const ACTION_STATUS_FILTER = [
  { value: '', label: 'All Statuses' },
  { value: 'open', label: 'Open' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'escalated', label: 'Escalated' },
];

const SEVERITY_BADGE: Record<string, 'danger' | 'warning' | 'info' | 'success' | 'neutral'> = {
  critical: 'danger',
  high: 'danger',
  medium: 'warning',
  low: 'info',
};

const FINDING_STATUS_BADGE: Record<string, 'warning' | 'info' | 'success' | 'neutral' | 'danger'> = {
  open: 'warning',
  in_remediation: 'info',
  resolved: 'success',
  accepted: 'neutral',
  closed: 'neutral',
};

const ACTION_STATUS_BADGE: Record<string, 'warning' | 'info' | 'success' | 'neutral' | 'danger'> = {
  open: 'warning',
  in_progress: 'info',
  completed: 'success',
  overdue: 'danger',
  escalated: 'danger',
};

const EMPTY_FINDING: CreateFindingForm = {
  engagement_id: '', title: '', severity: 'high', category: 'access_control',
  condition: '', criteria: '', cause: '', effect: '', recommendation: '',
};

const EMPTY_MGMT_RESPONSE: MgmtResponseForm = { response: '', action_owner: '', target_date: '' };

const EMPTY_ACTION: CreateActionForm = { description: '', owner_id: '', owner_name: '', due_date: '' };

function formatDate(iso: string): string {
  if (!iso) return '-';
  return new Date(iso || new Date()).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: '2-digit' });
}

function daysOverdue(dueDate: string): number {
  const due = new Date(dueDate);
  const now = new Date();
  return Math.max(0, Math.floor((now.getTime() - due.getTime()) / 86400000));
}

// ─── Findings Tab ─────────────────────────────────────────────────────────────

interface FindingsTabProps {
  engagementFilter: string;
  setEngagementFilter: (v: string) => void;
  severityFilter: string;
  setSeverityFilter: (v: string) => void;
  statusFilter: string;
  setStatusFilter: (v: string) => void;
}

function FindingsTab({
  engagementFilter, setEngagementFilter,
  severityFilter, setSeverityFilter,
  statusFilter, setStatusFilter,
}: FindingsTabProps) {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [mgmtResponseFinding, setMgmtResponseFinding] = useState<Finding | null>(null);
  const [findingForm, setFindingForm] = useState<CreateFindingForm>(EMPTY_FINDING);
  const [mgmtForm, setMgmtForm] = useState<MgmtResponseForm>(EMPTY_MGMT_RESPONSE);
  const [showActionModal, setShowActionModal] = useState<Finding | null>(null);
  const [actionForm, setActionForm] = useState<CreateActionForm>(EMPTY_ACTION);

  const { data, isLoading, error } = useQuery<Finding[]>({
    queryKey: ['audit-management', 'findings', { severityFilter, statusFilter, engagementFilter }],
    queryFn: async () => {
      const res = await auditManagementApi.listFindings({
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        engagement_id: engagementFilter || undefined,
      });
      const d = res.data;
      if (Array.isArray(d)) return d;
      const arr = d?.findings ?? d?.items ?? d?.data;
      return Array.isArray(arr) ? arr : [];
    },
  });

  const createMutation = useMutation({
    mutationFn: (f: CreateFindingForm) =>
      auditManagementApi.createFinding(f.engagement_id, f),
    onSuccess: () => {
      toast.success('Finding created');
      qc.invalidateQueries({ queryKey: ['audit-management', 'findings'] });
      setShowCreate(false);
      setFindingForm(EMPTY_FINDING);
    },
    onError: () => toast.error('Failed to create finding'),
  });

  const mgmtResponseMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: MgmtResponseForm }) =>
      auditManagementApi.recordMgmtResponse(id, data),
    onSuccess: () => {
      toast.success('Management response recorded');
      qc.invalidateQueries({ queryKey: ['audit-management', 'findings'] });
      setMgmtResponseFinding(null);
      setMgmtForm(EMPTY_MGMT_RESPONSE);
    },
    onError: () => toast.error('Failed to record response'),
  });

  const createActionMutation = useMutation({
    mutationFn: ({ findingId, data }: { findingId: string; data: CreateActionForm }) =>
      auditManagementApi.createAction(findingId, data),
    onSuccess: () => {
      toast.success('Action created');
      qc.invalidateQueries({ queryKey: ['audit-management', 'findings'] });
      qc.invalidateQueries({ queryKey: ['audit-management', 'actions'] });
      setShowActionModal(null);
      setActionForm(EMPTY_ACTION);
    },
    onError: () => toast.error('Failed to create action'),
  });

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message="Failed to load findings" />;

  const findings = data ?? [];

  return (
    <>
      {/* Filters + Create */}
      <div className="flex flex-wrap gap-3 items-end mb-4">
        <div className="w-40">
          <Select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} options={SEVERITY_FILTER} />
        </div>
        <div className="w-44">
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} options={FINDING_STATUS_FILTER} />
        </div>
        <Input
          className="w-56"
          value={engagementFilter}
          onChange={(e) => setEngagementFilter(e.target.value)}
          placeholder="Filter by engagement ID..."
        />
        <div className="ml-auto">
          <Button variant="primary" size="sm" icon={<PlusIcon className="h-4 w-4" />} onClick={() => setShowCreate(true)}>
            Create Finding
          </Button>
        </div>
      </div>

      {/* Table */}
      <Card padding="none">
        {findings.length === 0 ? (
          <div className="py-12 text-center">
            <ExclamationTriangleIcon className="h-10 w-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
            <p className="text-sm text-gray-400 dark:text-gray-500">No findings match your filters</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 dark:border-slate-700">
                  {['ID', 'Title', 'Engagement', 'Severity', 'Category', 'Status', 'Mgmt Response', 'Actions'].map((h) => (
                    <th key={h} className="px-4 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-slate-700/50">
                {findings.map((f) => (
                  <tr key={f.id} className="hover:bg-gray-50/50 dark:hover:bg-slate-700/30 transition-colors">
                    <td className="px-4 py-3.5 text-xs font-mono text-gray-400">{String(f.id).slice(0, 8)}</td>
                    <td className="px-4 py-3.5 max-w-[180px]">
                      <p className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">{f.title}</p>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-indigo-600 dark:text-indigo-400 max-w-[160px] truncate">
                      {f.engagement_title || String(f.engagement_id).slice(0, 8)}
                    </td>
                    <td className="px-4 py-3.5">
                      <Badge variant={SEVERITY_BADGE[f.severity] ?? 'neutral'} dot>
                        {f.severity.charAt(0).toUpperCase() + f.severity.slice(1)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-gray-600 dark:text-gray-400">
                      {f.category.replace(/_/g, ' ')}
                    </td>
                    <td className="px-4 py-3.5">
                      <Badge variant={FINDING_STATUS_BADGE[f.status] ?? 'neutral'} dot>
                        {f.status.replace(/_/g, ' ')}
                      </Badge>
                    </td>
                    <td className="px-4 py-3.5">
                      {f.management_response ? (
                        <Badge variant="success">Provided</Badge>
                      ) : (
                        <Badge variant="neutral">Pending</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex gap-1.5">
                        {!f.management_response && (
                          <Button size="sm" variant="secondary" onClick={() => { setMgmtResponseFinding(f); setMgmtForm(EMPTY_MGMT_RESPONSE); }}>
                            Respond
                          </Button>
                        )}
                        <Button size="sm" variant="ghost" onClick={() => { setShowActionModal(f); setActionForm(EMPTY_ACTION); }}>
                          + Action
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Create Finding Modal */}
      <Modal
        open={showCreate}
        onClose={() => { setShowCreate(false); setFindingForm(EMPTY_FINDING); }}
        title="Create Audit Finding"
        subtitle="Document a finding using the CCCE framework"
        size="xl"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setShowCreate(false); setFindingForm(EMPTY_FINDING); }}>Cancel</Button>
            <Button
              variant="primary"
              loading={createMutation.isPending}
              disabled={!findingForm.title || !findingForm.engagement_id}
              onClick={() => createMutation.mutate(findingForm)}
            >
              Create Finding
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Engagement ID"
              required
              value={findingForm.engagement_id}
              onChange={(e) => setFindingForm((f) => ({ ...f, engagement_id: e.target.value }))}
              placeholder="Engagement UUID"
            />
            <Input
              label="Finding Title"
              required
              value={findingForm.title}
              onChange={(e) => setFindingForm((f) => ({ ...f, title: e.target.value }))}
              placeholder="e.g. Excessive access in AP module"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Severity"
              required
              value={findingForm.severity}
              onChange={(e) => setFindingForm((f) => ({ ...f, severity: e.target.value }))}
              options={SEVERITY_OPTIONS}
            />
            <Select
              label="Category"
              required
              value={findingForm.category}
              onChange={(e) => setFindingForm((f) => ({ ...f, category: e.target.value }))}
              options={CATEGORY_OPTIONS}
            />
          </div>
          <div className="border-t border-gray-100 dark:border-slate-700 pt-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">CCCE Framework</p>
            <div className="grid grid-cols-2 gap-4">
              <Textarea
                label="Condition (What is)"
                required
                value={findingForm.condition}
                onChange={(e) => setFindingForm((f) => ({ ...f, condition: e.target.value }))}
                placeholder="Describe the current state observed..."
                rows={3}
              />
              <Textarea
                label="Criteria (What should be)"
                required
                value={findingForm.criteria}
                onChange={(e) => setFindingForm((f) => ({ ...f, criteria: e.target.value }))}
                placeholder="Expected standard, policy, or control..."
                rows={3}
              />
              <Textarea
                label="Cause (Why it happened)"
                value={findingForm.cause}
                onChange={(e) => setFindingForm((f) => ({ ...f, cause: e.target.value }))}
                placeholder="Root cause analysis..."
                rows={3}
              />
              <Textarea
                label="Effect (Impact)"
                value={findingForm.effect}
                onChange={(e) => setFindingForm((f) => ({ ...f, effect: e.target.value }))}
                placeholder="Business risk or impact of the finding..."
                rows={3}
              />
            </div>
          </div>
          <Textarea
            label="Recommendation"
            value={findingForm.recommendation}
            onChange={(e) => setFindingForm((f) => ({ ...f, recommendation: e.target.value }))}
            placeholder="Recommended remediation steps..."
            rows={3}
          />
        </div>
      </Modal>

      {/* Management Response Modal */}
      <Modal
        open={!!mgmtResponseFinding}
        onClose={() => { setMgmtResponseFinding(null); setMgmtForm(EMPTY_MGMT_RESPONSE); }}
        title="Management Response"
        subtitle={`Finding: ${mgmtResponseFinding?.title ?? ''}`}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setMgmtResponseFinding(null); setMgmtForm(EMPTY_MGMT_RESPONSE); }}>Cancel</Button>
            <Button
              variant="primary"
              loading={mgmtResponseMutation.isPending}
              disabled={!mgmtForm.response}
              onClick={() =>
                mgmtResponseFinding &&
                mgmtResponseMutation.mutate({ id: mgmtResponseFinding.id, data: mgmtForm })
              }
            >
              Record Response
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Textarea
            label="Management Response"
            required
            value={mgmtForm.response}
            onChange={(e) => setMgmtForm((f) => ({ ...f, response: e.target.value }))}
            placeholder="Management's response to the finding and planned remediation..."
            rows={4}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Action Owner"
              value={mgmtForm.action_owner}
              onChange={(e) => setMgmtForm((f) => ({ ...f, action_owner: e.target.value }))}
              placeholder="Person responsible"
            />
            <Input
              label="Target Date"
              type="date"
              value={mgmtForm.target_date}
              onChange={(e) => setMgmtForm((f) => ({ ...f, target_date: e.target.value }))}
            />
          </div>
        </div>
      </Modal>

      {/* Create Action for Finding Modal */}
      <Modal
        open={!!showActionModal}
        onClose={() => { setShowActionModal(null); setActionForm(EMPTY_ACTION); }}
        title="Create Remediation Action"
        subtitle={`Finding: ${showActionModal?.title ?? ''}`}
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setShowActionModal(null); setActionForm(EMPTY_ACTION); }}>Cancel</Button>
            <Button
              variant="primary"
              loading={createActionMutation.isPending}
              disabled={!actionForm.description || !actionForm.due_date}
              onClick={() =>
                showActionModal &&
                createActionMutation.mutate({ findingId: showActionModal.id, data: actionForm })
              }
            >
              Create Action
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Textarea
            label="Action Description"
            required
            value={actionForm.description}
            onChange={(e) => setActionForm((f) => ({ ...f, description: e.target.value }))}
            placeholder="Describe the remediation action..."
            rows={3}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Owner Name"
              value={actionForm.owner_name}
              onChange={(e) => setActionForm((f) => ({ ...f, owner_name: e.target.value }))}
              placeholder="Display name"
            />
            <Input
              label="Owner ID"
              value={actionForm.owner_id}
              onChange={(e) => setActionForm((f) => ({ ...f, owner_id: e.target.value }))}
              placeholder="Username or user ID"
            />
          </div>
          <Input
            label="Due Date"
            type="date"
            required
            value={actionForm.due_date}
            onChange={(e) => setActionForm((f) => ({ ...f, due_date: e.target.value }))}
          />
        </div>
      </Modal>
    </>
  );
}

// ─── Actions Tab ──────────────────────────────────────────────────────────────

function ActionsTab() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [closeAction, setCloseAction] = useState<Action | null>(null);
  const [closureEvidence, setClosureEvidence] = useState('');

  const { data, isLoading, error } = useQuery<Action[]>({
    queryKey: ['audit-management', 'actions', { statusFilter }],
    queryFn: async () => {
      const res = await auditManagementApi.listFindings({ action_status: statusFilter || undefined });
      const d = res.data;
      if (Array.isArray(d)) return d;
      const arr = d?.actions ?? d?.items ?? d?.data;
      return Array.isArray(arr) ? arr : [];
    },
  });

  const closeMutation = useMutation({
    mutationFn: ({ id, evidence }: { id: string; evidence: string }) =>
      auditManagementApi.closeAction(id, { evidence_of_closure: evidence }),
    onSuccess: () => {
      toast.success('Action closed with evidence');
      qc.invalidateQueries({ queryKey: ['audit-management', 'actions'] });
      qc.invalidateQueries({ queryKey: ['audit-management', 'dashboard'] });
      setCloseAction(null);
      setClosureEvidence('');
    },
    onError: () => toast.error('Failed to close action'),
  });

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message="Failed to load actions" />;

  const actions = (data ?? []) as unknown as Action[];

  return (
    <>
      <div className="flex gap-3 mb-4">
        <div className="w-44">
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} options={ACTION_STATUS_FILTER} />
        </div>
      </div>

      <Card padding="none">
        {actions.length === 0 ? (
          <div className="py-12 text-center">
            <CheckCircleIcon className="h-10 w-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
            <p className="text-sm text-gray-400 dark:text-gray-500">No actions found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 dark:border-slate-700">
                  {['ID', 'Description', 'Finding', 'Owner', 'Due Date', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="px-4 py-3.5 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-slate-700/50">
                {actions.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-50/50 dark:hover:bg-slate-700/30 transition-colors">
                    <td className="px-4 py-3.5 text-xs font-mono text-gray-400">{String(a.id).slice(0, 8)}</td>
                    <td className="px-4 py-3.5 text-sm text-gray-900 dark:text-gray-100 max-w-[200px] truncate">{a.description}</td>
                    <td className="px-4 py-3.5 text-sm text-indigo-600 dark:text-indigo-400 max-w-[160px] truncate">{a.finding_title}</td>
                    <td className="px-4 py-3.5 text-sm text-gray-700 dark:text-gray-300">{a.owner_name}</td>
                    <td className="px-4 py-3.5 text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">{formatDate(a.due_date)}</td>
                    <td className="px-4 py-3.5">
                      <Badge variant={ACTION_STATUS_BADGE[a.status] ?? 'neutral'} dot>
                        {a.status.replace(/_/g, ' ')}
                      </Badge>
                    </td>
                    <td className="px-4 py-3.5">
                      {a.status !== 'completed' && (
                        <Button
                          size="sm"
                          variant="success"
                          onClick={() => { setCloseAction(a); setClosureEvidence(''); }}
                        >
                          Close
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Close Action Modal */}
      <Modal
        open={!!closeAction}
        onClose={() => { setCloseAction(null); setClosureEvidence(''); }}
        title="Close Remediation Action"
        subtitle={closeAction?.description}
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => { setCloseAction(null); setClosureEvidence(''); }}>Cancel</Button>
            <Button
              variant="success"
              loading={closeMutation.isPending}
              disabled={!closureEvidence.trim()}
              onClick={() => closeAction && closeMutation.mutate({ id: closeAction.id, evidence: closureEvidence })}
            >
              Close with Evidence
            </Button>
          </>
        }
      >
        <Textarea
          label="Evidence of Closure"
          required
          value={closureEvidence}
          onChange={(e) => setClosureEvidence(e.target.value)}
          placeholder="Describe the evidence that demonstrates the action has been completed..."
          rows={5}
        />
      </Modal>
    </>
  );
}

// ─── Overdue Tab ──────────────────────────────────────────────────────────────

function OverdueTab() {
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery<Action[]>({
    queryKey: ['audit-management', 'actions', 'overdue'],
    queryFn: async () => {
      const res = await auditManagementApi.getOverdueActions();
      const d = res.data;
      if (Array.isArray(d)) return d;
      const arr = d?.actions ?? d?.items ?? d?.data;
      return Array.isArray(arr) ? arr : [];
    },
  });

  const escalateAllMutation = useMutation({
    mutationFn: () => auditManagementApi.escalateActions(),
    onSuccess: () => {
      toast.success('All overdue actions escalated');
      qc.invalidateQueries({ queryKey: ['audit-management', 'actions', 'overdue'] });
      qc.invalidateQueries({ queryKey: ['audit-management', 'dashboard'] });
    },
    onError: () => toast.error('Failed to escalate actions'),
  });

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message="Failed to load overdue actions" />;

  const actions = data ?? [];

  return (
    <>
      <div className="flex justify-between items-center mb-4">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          <span className="font-semibold text-red-600 dark:text-red-400">{actions.length}</span> action{actions.length !== 1 ? 's' : ''} past due date
        </p>
        {actions.length > 0 && (
          <Button
            variant="danger"
            size="sm"
            icon={<ArrowUpIcon className="h-4 w-4" />}
            loading={escalateAllMutation.isPending}
            onClick={() => escalateAllMutation.mutate()}
          >
            Escalate All
          </Button>
        )}
      </div>

      {actions.length === 0 ? (
        <div className="py-16 text-center">
          <CheckCircleIcon className="h-12 w-12 text-emerald-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">No overdue actions</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">All remediation actions are on track</p>
        </div>
      ) : (
        <div className="space-y-3">
          {actions.map((a) => {
            const overdueDays = daysOverdue(a.due_date);
            return (
              <Card key={a.id} className="border-l-4 border-l-red-400">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono text-gray-400">{String(a.id).slice(0, 8)}</span>
                      <Badge variant="danger">{overdueDays}d overdue</Badge>
                    </div>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{a.description}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Finding: <span className="text-indigo-600 dark:text-indigo-400">{a.finding_title}</span>
                    </p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                      <span className="flex items-center gap-1">
                        <ClockIcon className="h-3.5 w-3.5" />
                        Due: <span className="text-red-600 dark:text-red-400 font-medium">{formatDate(a.due_date)}</span>
                      </span>
                      <span>Owner: {a.owner_name}</span>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="danger"
                    icon={<ArrowUpIcon className="h-3.5 w-3.5" />}
                    onClick={() => toast.success(`Action ${String(a.id).slice(0, 8)} escalated`)}
                  >
                    Escalate
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function FindingsTracker() {
  const [activeTab, setActiveTab] = useState<TabKey>('findings');

  // Finding filters lifted to allow resetting on tab switch
  const [engagementFilter, setEngagementFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [findingStatusFilter, setFindingStatusFilter] = useState('');

  const tabs: { key: TabKey; label: string; icon: typeof ExclamationTriangleIcon }[] = [
    { key: 'findings', label: 'Findings', icon: ExclamationTriangleIcon },
    { key: 'actions', label: 'Actions', icon: CheckCircleIcon },
    { key: 'overdue', label: 'Overdue', icon: ClockIcon },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Findings & Actions"
        subtitle="Track audit findings, management responses, and remediation actions"
        breadcrumbs={[{ label: 'Audit Management' }, { label: 'Findings & Actions' }]}
      />

      {/* Tab Bar */}
      <div className="flex gap-1 p-1 bg-gray-100 dark:bg-slate-800 rounded-xl w-fit">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.key
                  ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {activeTab === 'findings' && (
        <FindingsTab
          engagementFilter={engagementFilter}
          setEngagementFilter={setEngagementFilter}
          severityFilter={severityFilter}
          setSeverityFilter={setSeverityFilter}
          statusFilter={findingStatusFilter}
          setStatusFilter={setFindingStatusFilter}
        />
      )}
      {activeTab === 'actions' && <ActionsTab />}
      {activeTab === 'overdue' && <OverdueTab />}
    </div>
  );
}
