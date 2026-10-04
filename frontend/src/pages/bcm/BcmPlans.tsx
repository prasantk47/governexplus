import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  DocumentTextIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  Table,
  Modal,
  Input,
  Select,
  Textarea,
  SearchInput,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type PlanType = 'bcp' | 'drp' | 'crp' | 'eop' | 'pandemic';
type PlanStatus = 'draft' | 'approved' | 'active' | 'under_review' | 'retired';
type ExerciseType = 'tabletop' | 'walkthrough' | 'simulation' | 'full_test';
type ExerciseOutcome = 'passed' | 'passed_with_issues' | 'failed' | 'not_completed';

interface BcmPlan {
  id: string;
  plan_name: string;
  plan_type: PlanType;
  scope: string;
  owner: string;
  version: string;
  status: PlanStatus;
  last_tested?: string;
  next_test_date?: string;
  created_at?: string;
}

interface BcmExercise {
  id: string;
  exercise_name: string;
  plan_id: string;
  plan_name?: string;
  exercise_type: ExerciseType;
  scheduled_date: string;
  outcome?: ExerciseOutcome;
  participants?: number;
  facilitator?: string;
  notes?: string;
}

interface PlanForm {
  plan_name: string;
  plan_type: PlanType | '';
  scope: string;
  owner: string;
  version: string;
  status: PlanStatus;
  next_test_date: string;
}

interface ExerciseForm {
  plan_id: string;
  exercise_name: string;
  exercise_type: ExerciseType;
  scheduled_date: string;
  outcome: ExerciseOutcome | '';
  facilitator: string;
  notes: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_PLAN_FORM: PlanForm = {
  plan_name: '',
  plan_type: '',
  scope: '',
  owner: '',
  version: '1.0',
  status: 'draft',
  next_test_date: '',
};

const EMPTY_EXERCISE_FORM: ExerciseForm = {
  plan_id: '',
  exercise_name: '',
  exercise_type: 'tabletop',
  scheduled_date: '',
  outcome: '',
  facilitator: '',
  notes: '',
};

const PLAN_TYPE_VARIANT: Record<PlanType, 'info' | 'success' | 'warning' | 'danger' | 'neutral'> = {
  bcp: 'info',
  drp: 'warning',
  crp: 'success',
  eop: 'danger',
  pandemic: 'neutral',
};

const PLAN_TYPE_LABEL: Record<PlanType, string> = {
  bcp: 'BCP',
  drp: 'DRP',
  crp: 'CRP',
  eop: 'EOP',
  pandemic: 'Pandemic',
};

const PLAN_STATUS_VARIANT: Record<PlanStatus, 'success' | 'warning' | 'info' | 'neutral' | 'danger'> = {
  draft: 'neutral',
  approved: 'success',
  active: 'info',
  under_review: 'warning',
  retired: 'danger',
};

const OUTCOME_VARIANT: Record<ExerciseOutcome, 'success' | 'warning' | 'danger' | 'neutral'> = {
  passed: 'success',
  passed_with_issues: 'warning',
  failed: 'danger',
  not_completed: 'neutral',
};

const PLAN_TYPE_OPTIONS: { value: PlanType; label: string }[] = [
  { value: 'bcp', label: 'Business Continuity Plan (BCP)' },
  { value: 'drp', label: 'Disaster Recovery Plan (DRP)' },
  { value: 'crp', label: 'Crisis Response Plan (CRP)' },
  { value: 'eop', label: 'Emergency Operations Plan (EOP)' },
  { value: 'pandemic', label: 'Pandemic Response Plan' },
];

const PLAN_STATUS_OPTIONS = [
  { value: 'draft', label: 'Draft' },
  { value: 'approved', label: 'Approved' },
  { value: 'active', label: 'Active' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'retired', label: 'Retired' },
];

const EXERCISE_TYPE_OPTIONS: { value: ExerciseType; label: string }[] = [
  { value: 'tabletop', label: 'Tabletop Exercise' },
  { value: 'walkthrough', label: 'Walkthrough' },
  { value: 'simulation', label: 'Simulation' },
  { value: 'full_test', label: 'Full Test' },
];

const OUTCOME_OPTIONS: { value: ExerciseOutcome; label: string }[] = [
  { value: 'passed', label: 'Passed' },
  { value: 'passed_with_issues', label: 'Passed with Issues' },
  { value: 'failed', label: 'Failed' },
  { value: 'not_completed', label: 'Not Completed' },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function BcmPlans() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'plans' | 'exercises'>('plans');
  const [search, setSearch] = useState('');
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [showExerciseModal, setShowExerciseModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<BcmPlan | null>(null);
  const [editingExercise, setEditingExercise] = useState<BcmExercise | null>(null);
  const [planForm, setPlanForm] = useState<PlanForm>(EMPTY_PLAN_FORM);
  const [exerciseForm, setExerciseForm] = useState<ExerciseForm>(EMPTY_EXERCISE_FORM);
  const [planErrors, setPlanErrors] = useState<Partial<Record<keyof PlanForm, string>>>({});
  const [exerciseErrors, setExerciseErrors] = useState<Partial<Record<keyof ExerciseForm, string>>>({});

  // ── Queries ──

  const { data: plansData, isLoading: plansLoading } = useQuery<BcmPlan[]>({
    queryKey: ['bcm-plans'],
    queryFn: () => api.get('/bcm/plans').then(r => r.data?.plans ?? r.data ?? []),
  });

  const { data: exercisesData, isLoading: exercisesLoading } = useQuery<BcmExercise[]>({
    queryKey: ['bcm-exercises'],
    queryFn: () => api.get('/bcm/exercises').then(r => r.data?.exercises ?? r.data ?? []),
  });

  const plans: BcmPlan[] = plansData ?? [];
  const exercises: BcmExercise[] = exercisesData ?? [];

  const today = new Date().toISOString().slice(0, 10);

  const filteredPlans = plans.filter(p => {
    if (!search) return true;
    const q = search.toLowerCase();
    return p.plan_name.toLowerCase().includes(q) || p.owner.toLowerCase().includes(q);
  });

  const filteredExercises = exercises.filter(e => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      e.exercise_name.toLowerCase().includes(q) ||
      (e.plan_name ?? '').toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const createPlanMutation = useMutation({
    mutationFn: (data: any) => api.post('/bcm/plans', data),
    onSuccess: () => {
      toast.success('BCM plan created');
      queryClient.invalidateQueries({ queryKey: ['bcm-plans'] });
      setShowPlanModal(false);
      setEditingPlan(null);
      setPlanForm(EMPTY_PLAN_FORM);
    },
    onError: () => toast.error('Failed to create plan'),
  });

  const updatePlanMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      api.put(`/bcm/plans/${id}`, data),
    onSuccess: () => {
      toast.success('Plan updated');
      queryClient.invalidateQueries({ queryKey: ['bcm-plans'] });
      setShowPlanModal(false);
      setEditingPlan(null);
    },
    onError: () => toast.error('Failed to update plan'),
  });

  const createExerciseMutation = useMutation({
    mutationFn: (data: any) => api.post('/bcm/exercises', data),
    onSuccess: () => {
      toast.success('Exercise logged');
      queryClient.invalidateQueries({ queryKey: ['bcm-exercises'] });
      setShowExerciseModal(false);
      setEditingExercise(null);
      setExerciseForm(EMPTY_EXERCISE_FORM);
    },
    onError: () => toast.error('Failed to log exercise'),
  });

  const updateExerciseMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      api.put(`/bcm/exercises/${id}`, data),
    onSuccess: () => {
      toast.success('Exercise updated');
      queryClient.invalidateQueries({ queryKey: ['bcm-exercises'] });
      setShowExerciseModal(false);
      setEditingExercise(null);
    },
    onError: () => toast.error('Failed to update exercise'),
  });

  // ── Handlers ──

  function openCreatePlan() {
    setEditingPlan(null);
    setPlanForm(EMPTY_PLAN_FORM);
    setPlanErrors({});
    setShowPlanModal(true);
  }

  function openEditPlan(plan: BcmPlan) {
    setEditingPlan(plan);
    setPlanForm({
      plan_name: plan.plan_name,
      plan_type: plan.plan_type,
      scope: plan.scope ?? '',
      owner: plan.owner,
      version: plan.version,
      status: plan.status,
      next_test_date: plan.next_test_date ?? '',
    });
    setPlanErrors({});
    setShowPlanModal(true);
  }

  function openCreateExercise() {
    setEditingExercise(null);
    setExerciseForm(EMPTY_EXERCISE_FORM);
    setExerciseErrors({});
    setShowExerciseModal(true);
  }

  function openEditExercise(ex: BcmExercise) {
    setEditingExercise(ex);
    setExerciseForm({
      plan_id: ex.plan_id,
      exercise_name: ex.exercise_name,
      exercise_type: ex.exercise_type,
      scheduled_date: ex.scheduled_date,
      outcome: ex.outcome ?? '',
      facilitator: ex.facilitator ?? '',
      notes: ex.notes ?? '',
    });
    setExerciseErrors({});
    setShowExerciseModal(true);
  }

  function handlePlanSubmit() {
    const errors: Partial<Record<keyof PlanForm, string>> = {};
    if (!planForm.plan_name.trim()) errors.plan_name = 'Plan name is required';
    if (!planForm.plan_type) errors.plan_type = 'Plan type is required';
    setPlanErrors(errors);
    if (Object.keys(errors).length > 0) return;

    if (editingPlan) {
      updatePlanMutation.mutate({ id: editingPlan.id, data: planForm });
    } else {
      createPlanMutation.mutate(planForm);
    }
  }

  function handleExerciseSubmit() {
    const errors: Partial<Record<keyof ExerciseForm, string>> = {};
    if (!exerciseForm.exercise_name.trim()) errors.exercise_name = 'Exercise name is required';
    if (!exerciseForm.scheduled_date) errors.scheduled_date = 'Scheduled date is required';
    setExerciseErrors(errors);
    if (Object.keys(errors).length > 0) return;

    if (editingExercise) {
      updateExerciseMutation.mutate({ id: editingExercise.id, data: exerciseForm });
    } else {
      createExerciseMutation.mutate(exerciseForm);
    }
  }

  // ── Plan Columns ──

  const planColumns = [
    {
      key: 'plan_name',
      header: 'Plan Name',
      render: (p: BcmPlan) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{p.plan_name}</div>
          <div className="text-xs text-gray-400">{p.scope}</div>
        </div>
      ),
    },
    {
      key: 'plan_type',
      header: 'Type',
      render: (p: BcmPlan) => (
        <Badge variant={PLAN_TYPE_VARIANT[p.plan_type]} size="sm">
          {PLAN_TYPE_LABEL[p.plan_type]}
        </Badge>
      ),
    },
    {
      key: 'version',
      header: 'Version',
      render: (p: BcmPlan) => (
        <span className="text-sm font-mono text-gray-600 dark:text-gray-400">v{p.version}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (p: BcmPlan) => (
        <Badge variant={PLAN_STATUS_VARIANT[p.status]} dot size="sm">
          {p.status.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'last_tested',
      header: 'Last Tested',
      render: (p: BcmPlan) => (
        <span className="text-sm text-gray-500">
          {p.last_tested ? new Date(p.last_tested).toLocaleDateString() : 'Never'}
        </span>
      ),
    },
    {
      key: 'next_test_date',
      header: 'Next Test',
      render: (p: BcmPlan) => {
        const overdue = p.next_test_date && p.next_test_date < today;
        return (
          <span className={`text-sm ${overdue ? 'text-red-600 font-medium' : 'text-gray-500'}`}>
            {p.next_test_date ? new Date(p.next_test_date).toLocaleDateString() : '—'}
            {overdue && ' (Overdue)'}
          </span>
        );
      },
    },
    {
      key: 'owner',
      header: 'Owner',
      render: (p: BcmPlan) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{p.owner}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (p: BcmPlan) => (
        <Button size="sm" variant="ghost" onClick={e => { e.stopPropagation(); openEditPlan(p); }}>
          Edit
        </Button>
      ),
    },
  ];

  // ── Exercise Columns ──

  const exerciseColumns = [
    {
      key: 'exercise_name',
      header: 'Exercise',
      render: (e: BcmExercise) => (
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{e.exercise_name}</div>
      ),
    },
    {
      key: 'plan_name',
      header: 'Plan',
      render: (e: BcmExercise) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">{e.plan_name || e.plan_id}</span>
      ),
    },
    {
      key: 'exercise_type',
      header: 'Type',
      render: (e: BcmExercise) => (
        <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">
          {e.exercise_type.replace('_', ' ')}
        </span>
      ),
    },
    {
      key: 'scheduled_date',
      header: 'Scheduled',
      render: (e: BcmExercise) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {new Date(e.scheduled_date).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'outcome',
      header: 'Outcome',
      render: (e: BcmExercise) =>
        e.outcome ? (
          <Badge variant={OUTCOME_VARIANT[e.outcome]} size="sm">
            {e.outcome.replace(/_/g, ' ')}
          </Badge>
        ) : (
          <span className="text-xs text-gray-400">Pending</span>
        ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (e: BcmExercise) => (
        <Button size="sm" variant="ghost" onClick={ev => { ev.stopPropagation(); openEditExercise(e); }}>
          Edit
        </Button>
      ),
    },
  ];

  const isPlanSaving = createPlanMutation.isPending || updatePlanMutation.isPending;
  const isExerciseSaving = createExerciseMutation.isPending || updateExerciseMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="BCM Plans & Exercises"
        subtitle="Manage business continuity plans and track test exercises"
        actions={
          activeTab === 'plans' ? (
            <Button icon={<PlusIcon className="h-4 w-4" />} onClick={openCreatePlan}>
              Create Plan
            </Button>
          ) : (
            <Button icon={<PlusIcon className="h-4 w-4" />} onClick={openCreateExercise}>
              Log Exercise
            </Button>
          )
        }
      />

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-slate-700">
        <nav className="-mb-px flex gap-6">
          {(['plans', 'exercises'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => { setActiveTab(tab); setSearch(''); }}
              className={`pb-3 text-sm font-medium capitalize transition-colors border-b-2 ${
                activeTab === tab
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              {tab === 'plans' ? (
                <span className="flex items-center gap-1.5">
                  <DocumentTextIcon className="h-4 w-4" /> Plans
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <BeakerIcon className="h-4 w-4" /> Test Exercises
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Filters */}
      <Card padding="md">
        <SearchInput
          placeholder={activeTab === 'plans' ? 'Search plans...' : 'Search exercises...'}
          value={search}
          onChange={e => setSearch(e.target.value)}
          onClear={() => setSearch('')}
        />
      </Card>

      {/* Tables */}
      {activeTab === 'plans' ? (
        <Table
          columns={planColumns}
          data={filteredPlans}
          loading={plansLoading}
          onRowClick={p => openEditPlan(p)}
          emptyMessage="No BCM plans found. Click 'Create Plan' to add your first plan."
        />
      ) : (
        <Table
          columns={exerciseColumns}
          data={filteredExercises}
          loading={exercisesLoading}
          onRowClick={e => openEditExercise(e)}
          emptyMessage="No exercises logged. Click 'Log Exercise' to record a test."
        />
      )}

      {/* Plan Modal */}
      <Modal
        open={showPlanModal}
        onClose={() => { setShowPlanModal(false); setEditingPlan(null); setPlanForm(EMPTY_PLAN_FORM); }}
        title={editingPlan ? 'Edit BCM Plan' : 'Create BCM Plan'}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowPlanModal(false)}>Cancel</Button>
            <Button onClick={handlePlanSubmit} loading={isPlanSaving}>
              {editingPlan ? 'Save Changes' : 'Create Plan'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Plan Name"
                required
                value={planForm.plan_name}
                onChange={e => setPlanForm(prev => ({ ...prev, plan_name: e.target.value }))}
                error={planErrors.plan_name}
                placeholder="e.g. IT Disaster Recovery Plan 2026"
              />
            </div>
            <Select
              label="Plan Type"
              required
              value={planForm.plan_type}
              onChange={e => setPlanForm(prev => ({ ...prev, plan_type: e.target.value as PlanType }))}
              options={[{ value: '', label: 'Select type...' }, ...PLAN_TYPE_OPTIONS]}
              error={planErrors.plan_type}
            />
            <Select
              label="Status"
              value={planForm.status}
              onChange={e => setPlanForm(prev => ({ ...prev, status: e.target.value as PlanStatus }))}
              options={PLAN_STATUS_OPTIONS}
            />
            <Input
              label="Owner"
              value={planForm.owner}
              onChange={e => setPlanForm(prev => ({ ...prev, owner: e.target.value }))}
              placeholder="Plan owner"
            />
            <Input
              label="Version"
              value={planForm.version}
              onChange={e => setPlanForm(prev => ({ ...prev, version: e.target.value }))}
              placeholder="1.0"
            />
            <div className="sm:col-span-2">
              <Input
                label="Scope"
                value={planForm.scope}
                onChange={e => setPlanForm(prev => ({ ...prev, scope: e.target.value }))}
                placeholder="e.g. All IT systems, Finance processes"
              />
            </div>
            <Input
              label="Next Test Date"
              type="date"
              value={planForm.next_test_date}
              onChange={e => setPlanForm(prev => ({ ...prev, next_test_date: e.target.value }))}
            />
          </div>
        </div>
      </Modal>

      {/* Exercise Modal */}
      <Modal
        open={showExerciseModal}
        onClose={() => { setShowExerciseModal(false); setEditingExercise(null); setExerciseForm(EMPTY_EXERCISE_FORM); }}
        title={editingExercise ? 'Edit Exercise' : 'Log Test Exercise'}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowExerciseModal(false)}>Cancel</Button>
            <Button onClick={handleExerciseSubmit} loading={isExerciseSaving}>
              {editingExercise ? 'Save Changes' : 'Log Exercise'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Exercise Name"
                required
                value={exerciseForm.exercise_name}
                onChange={e => setExerciseForm(prev => ({ ...prev, exercise_name: e.target.value }))}
                error={exerciseErrors.exercise_name}
                placeholder="e.g. Q4 2026 DRP Tabletop"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                BCM Plan
              </label>
              <select
                value={exerciseForm.plan_id}
                onChange={e => setExerciseForm(prev => ({ ...prev, plan_id: e.target.value }))}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select plan...</option>
                {plans.map(p => (
                  <option key={p.id} value={p.id}>{p.plan_name}</option>
                ))}
              </select>
            </div>
            <Select
              label="Exercise Type"
              value={exerciseForm.exercise_type}
              onChange={e => setExerciseForm(prev => ({ ...prev, exercise_type: e.target.value as ExerciseType }))}
              options={EXERCISE_TYPE_OPTIONS}
            />
            <Input
              label="Scheduled Date"
              type="date"
              required
              value={exerciseForm.scheduled_date}
              onChange={e => setExerciseForm(prev => ({ ...prev, scheduled_date: e.target.value }))}
              error={exerciseErrors.scheduled_date}
            />
            <Select
              label="Outcome"
              value={exerciseForm.outcome}
              onChange={e => setExerciseForm(prev => ({ ...prev, outcome: e.target.value as ExerciseOutcome }))}
              options={[{ value: '', label: 'Pending...' }, ...OUTCOME_OPTIONS]}
            />
            <Input
              label="Facilitator"
              value={exerciseForm.facilitator}
              onChange={e => setExerciseForm(prev => ({ ...prev, facilitator: e.target.value }))}
              placeholder="Facilitator name"
            />
          </div>
          <Textarea
            label="Notes"
            value={exerciseForm.notes}
            onChange={e => setExerciseForm(prev => ({ ...prev, notes: e.target.value }))}
            rows={3}
            placeholder="Exercise notes, observations, findings..."
          />
        </div>
      </Modal>
    </div>
  );
}
