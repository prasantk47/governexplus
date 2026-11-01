import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowRightIcon,
  FunnelIcon,
  PaperAirplaneIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { riskManagementApi } from '../../services/riskManagementApi';
import {
  PageHeader,
  Card,
  Badge,
  Button,
  Modal,
  Textarea,
  Select,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type WorkflowStatus = 'pending' | 'in_progress' | 'approved' | 'rejected' | 'withdrawn';
type WorkflowType = 'risk_proposal' | 'risk_approval' | 'assessment_approval' | 'response_approval';
type StepStatus = 'pending' | 'approved' | 'rejected' | 'delegated';

interface WorkflowStep {
  id: number;
  step_number: number;
  step_name: string;
  approver_role: string;
  approver_user_id?: string;
  approver_name?: string;
  status: StepStatus;
  decision?: string;
  comments?: string;
  decided_at?: string;
}

interface Workflow {
  id: number;
  workflow_id: string;
  workflow_type: WorkflowType;
  object_id: string;
  object_type: string;
  title?: string;
  description?: string;
  total_steps: number;
  current_step: number;
  status: WorkflowStatus;
  submitted_by?: string;
  submitted_at?: string;
  completed_at?: string;
  steps?: WorkflowStep[];
  created_at: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const WF_TYPE_LABELS: Record<WorkflowType, string> = {
  risk_proposal:       'Risk Proposal',
  risk_approval:       'Risk Approval',
  assessment_approval: 'Assessment Approval',
  response_approval:   'Response Plan Approval',
};

const WF_STATUS_VARIANT: Record<WorkflowStatus, 'neutral' | 'info' | 'success' | 'danger' | 'warning'> = {
  pending:     'warning',
  in_progress: 'info',
  approved:    'success',
  rejected:    'danger',
  withdrawn:   'neutral',
};

const STEP_STATUS_ICON: Record<StepStatus, React.ReactNode> = {
  pending:  <ClockIcon className="h-4 w-4 text-amber-500" />,
  approved: <CheckCircleIcon className="h-4 w-4 text-emerald-500" />,
  rejected: <XCircleIcon className="h-4 w-4 text-red-500" />,
  delegated: <ArrowRightIcon className="h-4 w-4 text-indigo-500" />,
};

const WF_TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'risk_proposal', label: 'Risk Proposal' },
  { value: 'risk_approval', label: 'Risk Approval' },
  { value: 'assessment_approval', label: 'Assessment Approval' },
  { value: 'response_approval', label: 'Response Plan Approval' },
];

const WF_STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'withdrawn', label: 'Withdrawn' },
];

// Progress stepper
function StepProgress({ steps, total, current }: { steps?: WorkflowStep[]; total: number; current: number }) {
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: total }).map((_, i) => {
        const step = steps?.find(s => s.step_number === i + 1);
        const isActive = i + 1 === current;
        const isDone = step && step.status === 'approved';
        const isRejected = step && step.status === 'rejected';
        return (
          <div key={i} className="flex items-center gap-1">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all ${
                isRejected
                  ? 'bg-red-100 border-red-500 text-red-700 dark:bg-red-900/30'
                  : isDone
                  ? 'bg-emerald-100 border-emerald-500 text-emerald-700 dark:bg-emerald-900/30'
                  : isActive
                  ? 'bg-indigo-100 border-indigo-600 text-indigo-700 dark:bg-indigo-900/30 ring-2 ring-indigo-300 dark:ring-indigo-700'
                  : 'bg-gray-100 border-gray-300 text-gray-400 dark:bg-slate-700 dark:border-slate-600'
              }`}
              title={step?.step_name ?? `Step ${i + 1}`}
            >
              {isRejected ? '✕' : isDone ? '✓' : i + 1}
            </div>
            {i < total - 1 && (
              <div className={`h-0.5 w-4 ${isDone ? 'bg-emerald-400' : 'bg-gray-200 dark:bg-slate-600'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function RiskWorkflowApproval() {
  const queryClient = useQueryClient();

  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('pending');
  const [tab, setTab] = useState<'inbox' | 'all'>('inbox');

  const [selectedWf, setSelectedWf] = useState<Workflow | null>(null);
  const [decideStep, setDecideStep] = useState<WorkflowStep | null>(null);
  const [decideDecision, setDecideDecision] = useState<'approve' | 'reject'>('approve');
  const [decideComments, setDecideComments] = useState('');

  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [submitForm, setSubmitForm] = useState({
    workflow_type: 'risk_approval' as WorkflowType,
    object_id: '',
    object_type: 'risk',
    title: '',
    description: '',
  });

  // ── Queries ──

  const { data: workflowsData, isLoading } = useQuery({
    queryKey: ['risk-workflows', typeFilter, statusFilter, tab],
    queryFn: () =>
      riskManagementApi.listWorkflows({
        workflow_type: typeFilter || undefined,
        status: statusFilter || undefined,
      }).then(r => {
        const d = r.data;
        return Array.isArray(d) ? d : Array.isArray(d?.workflows) ? d.workflows : [];
      }),
    enabled: tab === 'all',
  });

  const { data: inboxData, isLoading: inboxLoading } = useQuery({
    queryKey: ['workflow-inbox'],
    queryFn: () =>
      riskManagementApi.getWorkflowInbox().then(r => {
        const d = r.data;
        return Array.isArray(d?.pending_steps) ? d.pending_steps : [];
      }),
    enabled: tab === 'inbox',
  });

  // ── Workflow detail query ──
  const { data: wfDetail } = useQuery({
    queryKey: ['workflow-detail', selectedWf?.workflow_id],
    queryFn: () =>
      riskManagementApi.getWorkflow(selectedWf!.workflow_id).then(r => r.data),
    enabled: !!selectedWf,
  });

  const workflows: Workflow[] = workflowsData ?? [];
  const inboxItems: any[] = inboxData ?? [];

  // ── Stats ──
  const pendingCount = inboxItems.length;
  const allWorkflows: Workflow[] = workflowsData ?? [];
  const approvedCount = allWorkflows.filter(w => w.status === 'approved').length;
  const rejectedCount = allWorkflows.filter(w => w.status === 'rejected').length;

  // ── Mutations ──

  const decideMutation = useMutation({
    mutationFn: ({ workflowId, step, decision, comments }: {
      workflowId: string; step: number; decision: string; comments: string;
    }) => riskManagementApi.decideWorkflowStep(workflowId, step, { decision, comments }),
    onSuccess: () => {
      toast.success(`Step ${decideDecision === 'approve' ? 'approved' : 'rejected'}`);
      queryClient.invalidateQueries({ queryKey: ['risk-workflows'] });
      queryClient.invalidateQueries({ queryKey: ['workflow-inbox'] });
      queryClient.invalidateQueries({ queryKey: ['workflow-detail'] });
      setDecideStep(null);
      setDecideComments('');
    },
    onError: () => toast.error('Failed to record decision'),
  });

  const withdrawMutation = useMutation({
    mutationFn: (workflowId: string) => riskManagementApi.withdrawWorkflow(workflowId),
    onSuccess: () => {
      toast.success('Workflow withdrawn');
      queryClient.invalidateQueries({ queryKey: ['risk-workflows'] });
      setSelectedWf(null);
    },
    onError: () => toast.error('Failed to withdraw workflow'),
  });

  const submitMutation = useMutation({
    mutationFn: (data: any) => riskManagementApi.createWorkflow(data),
    onSuccess: () => {
      toast.success('Workflow submitted for approval');
      queryClient.invalidateQueries({ queryKey: ['risk-workflows'] });
      setShowSubmitModal(false);
      setSubmitForm({ workflow_type: 'risk_approval', object_id: '', object_type: 'risk', title: '', description: '' });
    },
    onError: () => toast.error('Failed to submit workflow'),
  });

  // ── Handlers ──

  function handleDecide() {
    if (!decideStep || !selectedWf) return;
    decideMutation.mutate({
      workflowId: selectedWf.workflow_id,
      step: decideStep.step_number,
      decision: decideDecision,
      comments: decideComments,
    });
  }

  function openDecide(step: WorkflowStep, decision: 'approve' | 'reject') {
    setDecideStep(step);
    setDecideDecision(decision);
    setDecideComments('');
  }

  // ── Detail Workflow (enriched) ──
  const activeWf: Workflow | null = wfDetail ?? selectedWf;
  const activeSteps: WorkflowStep[] = wfDetail?.steps ?? selectedWf?.steps ?? [];

  const displayLoading = tab === 'inbox' ? inboxLoading : isLoading;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Approval Workflows"
        subtitle="Multi-step approval workflows for risks, assessments, and response plans"
        actions={
          <Button
            icon={<PaperAirplaneIcon className="h-4 w-4" />}
            onClick={() => setShowSubmitModal(true)}
          >
            Submit for Approval
          </Button>
        }
      />

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
              <ClockIcon className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{pendingCount}</p>
              <p className="text-xs text-gray-500">Awaiting My Action</p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
              <CheckCircleIcon className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{approvedCount}</p>
              <p className="text-xs text-gray-500">Approved (all time)</p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <XCircleIcon className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{rejectedCount}</p>
              <p className="text-xs text-gray-500">Rejected (all time)</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Tab + filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden text-xs font-medium">
            <button
              onClick={() => setTab('inbox')}
              className={`px-4 py-2 transition-colors ${
                tab === 'inbox' ? 'bg-indigo-600 text-white' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'
              }`}
            >
              My Inbox {pendingCount > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400 text-[10px] font-bold">
                  {pendingCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setTab('all')}
              className={`px-4 py-2 transition-colors ${
                tab === 'all' ? 'bg-indigo-600 text-white' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'
              }`}
            >
              All Workflows
            </button>
          </div>
          {tab === 'all' && (
            <>
              <Select
                value={typeFilter}
                onChange={e => setTypeFilter(e.target.value)}
                options={WF_TYPE_OPTIONS}
              />
              <Select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                options={WF_STATUS_OPTIONS}
              />
            </>
          )}
        </div>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* List panel */}
        <div className="xl:col-span-2">
          <Card padding="none">
            {displayLoading ? (
              <div className="flex items-center justify-center h-48 text-sm text-gray-400">
                Loading workflows...
              </div>
            ) : tab === 'inbox' ? (
              // ── Inbox ──
              inboxItems.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 gap-3 text-gray-400">
                  <CheckCircleIcon className="h-12 w-12 opacity-40" />
                  <p className="text-sm">Your inbox is clear — no pending approvals</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100 dark:divide-slate-700">
                  {inboxItems.map((item: any) => (
                    <div
                      key={item.id}
                      className="p-4 hover:bg-gray-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors"
                      onClick={() => {
                        if (item.workflow) setSelectedWf(item.workflow);
                      }}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="warning" size="sm" dot>Step {item.step_number}</Badge>
                            <span className="text-xs text-gray-400">{item.step_name}</span>
                          </div>
                          {item.workflow && (
                            <>
                              <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate">
                                {item.workflow.title ?? item.workflow.object_id}
                              </p>
                              <p className="text-xs text-gray-500 mt-0.5">
                                {WF_TYPE_LABELS[item.workflow.workflow_type as WorkflowType] ?? item.workflow.workflow_type}
                                {' · '}{item.workflow.object_id}
                              </p>
                            </>
                          )}
                          <p className="text-xs text-indigo-500 mt-1">Role: {item.approver_role}</p>
                        </div>
                        <div className="flex gap-2 flex-shrink-0">
                          <button
                            onClick={e => { e.stopPropagation(); if (item.workflow) { setSelectedWf(item.workflow); openDecide(item, 'approve'); } }}
                            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 transition-colors"
                          >
                            Approve
                          </button>
                          <button
                            onClick={e => { e.stopPropagation(); if (item.workflow) { setSelectedWf(item.workflow); openDecide(item, 'reject'); } }}
                            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors"
                          >
                            Reject
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )
            ) : (
              // ── All Workflows ──
              workflows.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 gap-3 text-gray-400">
                  <DocumentTextIcon className="h-12 w-12 opacity-40" />
                  <p className="text-sm">No workflows found</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100 dark:divide-slate-700">
                  {workflows.map(wf => (
                    <div
                      key={wf.workflow_id}
                      onClick={() => setSelectedWf(wf)}
                      className={`p-4 cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-slate-700/50 ${
                        selectedWf?.workflow_id === wf.workflow_id ? 'bg-indigo-50 dark:bg-indigo-900/20' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate">
                            {wf.title ?? wf.object_id}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {WF_TYPE_LABELS[wf.workflow_type] ?? wf.workflow_type}
                            {' · '}<span className="font-mono">{wf.workflow_id}</span>
                          </p>
                        </div>
                        <Badge variant={WF_STATUS_VARIANT[wf.status] ?? 'neutral'} size="sm" dot>
                          {wf.status.replace('_', ' ')}
                        </Badge>
                      </div>
                      <StepProgress steps={wf.steps} total={wf.total_steps} current={wf.current_step} />
                      <p className="text-xs text-gray-400 mt-1.5">
                        Step {wf.current_step} of {wf.total_steps}
                        {wf.submitted_at && ` · Submitted ${new Date(wf.submitted_at).toLocaleDateString()}`}
                      </p>
                    </div>
                  ))}
                </div>
              )
            )}
          </Card>
        </div>

        {/* Detail panel */}
        <div className="xl:col-span-1">
          {activeWf ? (
            <Card padding="lg">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {activeWf.title ?? activeWf.object_id}
                  </h3>
                  <p className="text-xs text-gray-500 mt-0.5 font-mono">{activeWf.workflow_id}</p>
                </div>
                <Badge variant={WF_STATUS_VARIANT[activeWf.status] ?? 'neutral'} size="sm" dot>
                  {activeWf.status.replace('_', ' ')}
                </Badge>
              </div>

              <div className="space-y-2 mb-4 text-xs text-gray-600 dark:text-gray-400">
                <div className="flex justify-between">
                  <span>Type</span>
                  <span className="font-medium text-gray-800 dark:text-gray-200">
                    {WF_TYPE_LABELS[activeWf.workflow_type] ?? activeWf.workflow_type}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Object</span>
                  <span className="font-mono text-gray-800 dark:text-gray-200">{activeWf.object_id}</span>
                </div>
                <div className="flex justify-between">
                  <span>Submitted by</span>
                  <span className="font-medium text-gray-800 dark:text-gray-200">{activeWf.submitted_by ?? '—'}</span>
                </div>
              </div>

              {/* Steps */}
              <div className="space-y-2 mb-4">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Approval Steps</p>
                {activeSteps.length === 0
                  ? Array.from({ length: activeWf.total_steps }).map((_, i) => (
                      <div key={i} className="flex items-center gap-3 p-2.5 rounded-xl bg-gray-50 dark:bg-slate-700/50">
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border-2 ${
                          i + 1 === activeWf.current_step
                            ? 'border-indigo-600 bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400'
                            : 'border-gray-300 bg-gray-100 text-gray-400 dark:bg-slate-600 dark:border-slate-500'
                        }`}>{i + 1}</div>
                        <span className="text-xs text-gray-600 dark:text-gray-400">Step {i + 1}</span>
                      </div>
                    ))
                  : activeSteps.map(step => (
                      <div
                        key={step.id}
                        className={`p-2.5 rounded-xl border transition-colors ${
                          step.status === 'pending' && step.step_number === activeWf.current_step
                            ? 'border-indigo-300 dark:border-indigo-700 bg-indigo-50 dark:bg-indigo-900/20'
                            : 'border-transparent bg-gray-50 dark:bg-slate-700/50'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          {STEP_STATUS_ICON[step.status]}
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-gray-800 dark:text-gray-200">
                              {step.step_name ?? `Step ${step.step_number}`}
                            </p>
                            <p className="text-[10px] text-gray-400">{step.approver_role}</p>
                          </div>
                          {step.decided_at && (
                            <span className="text-[10px] text-gray-400">
                              {new Date(step.decided_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                        {step.comments && (
                          <p className="text-[10px] text-gray-500 mt-1 pl-6 italic">"{step.comments}"</p>
                        )}
                        {step.status === 'pending' && step.step_number === activeWf.current_step &&
                          activeWf.status !== 'approved' && activeWf.status !== 'rejected' && (
                          <div className="flex gap-2 mt-2 pl-6">
                            <button
                              onClick={() => openDecide(step, 'approve')}
                              className="px-2.5 py-1 text-[10px] font-medium rounded-lg bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-200 transition-colors"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => openDecide(step, 'reject')}
                              className="px-2.5 py-1 text-[10px] font-medium rounded-lg bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200 transition-colors"
                            >
                              Reject
                            </button>
                          </div>
                        )}
                      </div>
                    ))
                }
              </div>

              {/* Withdraw button */}
              {(activeWf.status === 'pending' || activeWf.status === 'in_progress') && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full"
                  loading={withdrawMutation.isPending}
                  onClick={() => withdrawMutation.mutate(activeWf.workflow_id)}
                >
                  Withdraw Workflow
                </Button>
              )}
            </Card>
          ) : (
            <Card padding="lg">
              <div className="flex flex-col items-center justify-center h-48 gap-3 text-gray-400">
                <FunnelIcon className="h-10 w-10 opacity-30" />
                <p className="text-sm text-center">Select a workflow to view details and take action</p>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Decision Modal */}
      <Modal
        open={!!decideStep}
        onClose={() => setDecideStep(null)}
        title={decideDecision === 'approve' ? 'Approve Step' : 'Reject Step'}
        subtitle={decideStep ? `Step ${decideStep.step_number}: ${decideStep.step_name ?? ''}` : ''}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDecideStep(null)}>Cancel</Button>
            <Button
              variant={decideDecision === 'approve' ? 'primary' : 'danger'}
              loading={decideMutation.isPending}
              onClick={handleDecide}
            >
              {decideDecision === 'approve' ? 'Confirm Approval' : 'Confirm Rejection'}
            </Button>
          </>
        }
      >
        <Textarea
          label="Comments (optional)"
          value={decideComments}
          onChange={e => setDecideComments(e.target.value)}
          rows={3}
          placeholder={decideDecision === 'approve' ? 'Add approval notes...' : 'Reason for rejection...'}
        />
      </Modal>

      {/* Submit for Approval Modal */}
      <Modal
        open={showSubmitModal}
        onClose={() => setShowSubmitModal(false)}
        title="Submit for Approval"
        subtitle="Start a new approval workflow"
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowSubmitModal(false)}>Cancel</Button>
            <Button
              loading={submitMutation.isPending}
              onClick={() => submitMutation.mutate({
                ...submitForm,
                total_steps: submitForm.workflow_type === 'response_approval' ? 2 : 3,
              })}
            >
              Submit
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Select
            label="Workflow Type"
            value={submitForm.workflow_type}
            onChange={e => setSubmitForm(f => ({ ...f, workflow_type: e.target.value as WorkflowType }))}
            options={WF_TYPE_OPTIONS.slice(1)}
          />
          <div className="p-3 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 text-xs text-indigo-700 dark:text-indigo-400">
            {submitForm.workflow_type === 'response_approval'
              ? '2-step approval: Response Owner → CRO'
              : submitForm.workflow_type === 'risk_proposal'
              ? '3-step approval: Risk Owner → Risk Manager → CRO'
              : submitForm.workflow_type === 'risk_approval'
              ? '3-step approval: Dept Head → Risk Committee → Board'
              : '3-step approval: Assessor → Risk Manager → CRO'}
          </div>
          <Select
            label="Object Type"
            value={submitForm.object_type}
            onChange={e => setSubmitForm(f => ({ ...f, object_type: e.target.value }))}
            options={[
              { value: 'risk', label: 'Risk' },
              { value: 'assessment', label: 'Assessment' },
              { value: 'response', label: 'Response Plan' },
            ]}
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Object ID <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={submitForm.object_id}
              onChange={e => setSubmitForm(f => ({ ...f, object_id: e.target.value }))}
              placeholder={submitForm.object_type === 'risk' ? 'e.g. RISK_abc123' : 'Object business key'}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Title</label>
            <input
              type="text"
              value={submitForm.title}
              onChange={e => setSubmitForm(f => ({ ...f, title: e.target.value }))}
              placeholder="Workflow title (optional)"
              className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
