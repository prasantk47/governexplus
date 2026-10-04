import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
  ChevronDownIcon,
  ChevronRightIcon,
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

type SurveyType = 'risk_assessment' | 'compliance_check' | 'vendor_due_diligence' | 'csa' | 'general';
type SurveyStatus = 'draft' | 'active' | 'closed' | 'archived';
type QuestionType = 'text' | 'choice' | 'rating' | 'yes_no';

interface SurveyQuestion {
  id?: string;
  question_text: string;
  question_type: QuestionType;
  options?: string[];
  required: boolean;
  order: number;
}

interface Survey {
  id: string;
  survey_name: string;
  description: string;
  survey_type: SurveyType;
  status: SurveyStatus;
  created_by: string;
  due_date?: string;
  question_count: number;
  questions?: SurveyQuestion[];
  created_at?: string;
}

interface SurveyForm {
  survey_name: string;
  description: string;
  survey_type: SurveyType | '';
  status: SurveyStatus;
  due_date: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_SURVEY_FORM: SurveyForm = {
  survey_name: '',
  description: '',
  survey_type: '',
  status: 'draft',
  due_date: '',
};

const SURVEY_TYPE_OPTIONS: { value: SurveyType; label: string }[] = [
  { value: 'risk_assessment', label: 'Risk Assessment' },
  { value: 'compliance_check', label: 'Compliance Check' },
  { value: 'vendor_due_diligence', label: 'Vendor Due Diligence' },
  { value: 'csa', label: 'Control Self-Assessment (CSA)' },
  { value: 'general', label: 'General' },
];

const STATUS_VARIANT: Record<SurveyStatus, 'success' | 'warning' | 'info' | 'neutral'> = {
  draft: 'neutral',
  active: 'success',
  closed: 'warning',
  archived: 'neutral',
};

const STATUS_OPTIONS = [
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'closed', label: 'Closed' },
  { value: 'archived', label: 'Archived' },
];

const QUESTION_TYPE_OPTIONS: { value: QuestionType; label: string }[] = [
  { value: 'text', label: 'Free Text' },
  { value: 'choice', label: 'Multiple Choice' },
  { value: 'rating', label: 'Rating (1–5)' },
  { value: 'yes_no', label: 'Yes / No' },
];

const EMPTY_QUESTION: SurveyQuestion = {
  question_text: '',
  question_type: 'text',
  options: [],
  required: true,
  order: 0,
};

// ─── Component ────────────────────────────────────────────────────────────────

export function SurveyDesigner() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingSurvey, setEditingSurvey] = useState<Survey | null>(null);
  const [form, setForm] = useState<SurveyForm>(EMPTY_SURVEY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof SurveyForm, string>>>({});
  const [expandedSurveyId, setExpandedSurveyId] = useState<string | null>(null);
  const [addingQuestion, setAddingQuestion] = useState(false);
  const [newQuestion, setNewQuestion] = useState<SurveyQuestion>({ ...EMPTY_QUESTION });
  const [newOptionText, setNewOptionText] = useState('');

  // ── Queries ──

  const { data: surveysData, isLoading } = useQuery<Survey[]>({
    queryKey: ['surveys'],
    queryFn: () => api.get('/surveys').then(r => r.data?.surveys ?? r.data ?? []),
  });

  const { data: expandedSurveyData } = useQuery<Survey>({
    queryKey: ['survey-detail', expandedSurveyId],
    queryFn: () => api.get(`/surveys/${expandedSurveyId}`).then(r => r.data),
    enabled: !!expandedSurveyId,
  });

  const surveys: Survey[] = surveysData ?? [];

  const filtered = surveys.filter(s => {
    if (!search) return true;
    const q = search.toLowerCase();
    return s.survey_name.toLowerCase().includes(q) || s.created_by.toLowerCase().includes(q);
  });

  // ── Mutations ──

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/surveys', data),
    onSuccess: () => {
      toast.success('Survey created');
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
      setShowCreateModal(false);
      setForm(EMPTY_SURVEY_FORM);
    },
    onError: () => toast.error('Failed to create survey'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      api.put(`/surveys/${id}`, data),
    onSuccess: () => {
      toast.success('Survey updated');
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
      queryClient.invalidateQueries({ queryKey: ['survey-detail', editingSurvey?.id] });
      setEditingSurvey(null);
    },
    onError: () => toast.error('Failed to update survey'),
  });

  const addQuestionMutation = useMutation({
    mutationFn: ({ surveyId, question }: { surveyId: string; question: SurveyQuestion }) =>
      api.post(`/surveys/${surveyId}/questions`, question),
    onSuccess: () => {
      toast.success('Question added');
      queryClient.invalidateQueries({ queryKey: ['survey-detail', expandedSurveyId] });
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
      setAddingQuestion(false);
      setNewQuestion({ ...EMPTY_QUESTION });
    },
    onError: () => toast.error('Failed to add question'),
  });

  const deleteQuestionMutation = useMutation({
    mutationFn: ({ surveyId, questionId }: { surveyId: string; questionId: string }) =>
      api.delete(`/surveys/${surveyId}/questions/${questionId}`),
    onSuccess: () => {
      toast.success('Question removed');
      queryClient.invalidateQueries({ queryKey: ['survey-detail', expandedSurveyId] });
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
    },
    onError: () => toast.error('Failed to remove question'),
  });

  // ── Handlers ──

  function validate(): boolean {
    const errors: Partial<Record<keyof SurveyForm, string>> = {};
    if (!form.survey_name.trim()) errors.survey_name = 'Survey name is required';
    if (!form.survey_type) errors.survey_type = 'Survey type is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleCreateSubmit() {
    if (!validate()) return;
    createMutation.mutate(form);
  }

  function openEdit(s: Survey) {
    setEditingSurvey(s);
    setForm({
      survey_name: s.survey_name,
      description: s.description ?? '',
      survey_type: s.survey_type,
      status: s.status,
      due_date: s.due_date ?? '',
    });
    setFormErrors({});
  }

  function handleEditSubmit() {
    if (!validate() || !editingSurvey) return;
    updateMutation.mutate({ id: editingSurvey.id, data: form });
  }

  function toggleExpand(id: string) {
    setExpandedSurveyId(prev => (prev === id ? null : id));
    setAddingQuestion(false);
  }

  function handleAddQuestion() {
    if (!expandedSurveyId || !newQuestion.question_text.trim()) return;
    addQuestionMutation.mutate({
      surveyId: expandedSurveyId,
      question: { ...newQuestion, order: (expandedSurveyData?.questions ?? []).length + 1 },
    });
  }

  function setField<K extends keyof SurveyForm>(key: K, value: SurveyForm[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Columns ──

  const columns = [
    {
      key: 'expand',
      header: '',
      render: (s: Survey) => (
        <button
          onClick={e => { e.stopPropagation(); toggleExpand(s.id); }}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400"
        >
          {expandedSurveyId === s.id ? (
            <ChevronDownIcon className="h-4 w-4" />
          ) : (
            <ChevronRightIcon className="h-4 w-4" />
          )}
        </button>
      ),
    },
    {
      key: 'survey_name',
      header: 'Survey Name',
      render: (s: Survey) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{s.survey_name}</div>
          {s.description && (
            <div className="text-xs text-gray-400 truncate max-w-xs">{s.description}</div>
          )}
        </div>
      ),
    },
    {
      key: 'survey_type',
      header: 'Type',
      render: (s: Survey) => (
        <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">
          {s.survey_type.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (s: Survey) => (
        <Badge variant={STATUS_VARIANT[s.status]} dot size="sm">{s.status}</Badge>
      ),
    },
    {
      key: 'question_count',
      header: 'Questions',
      render: (s: Survey) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">{s.question_count}</span>
      ),
    },
    {
      key: 'created_by',
      header: 'Created By',
      render: (s: Survey) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">{s.created_by}</span>
      ),
    },
    {
      key: 'due_date',
      header: 'Due Date',
      render: (s: Survey) => (
        <span className="text-sm text-gray-500">
          {s.due_date ? new Date(s.due_date).toLocaleDateString() : '—'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (s: Survey) => (
        <Button
          size="sm"
          variant="ghost"
          icon={<PencilSquareIcon className="h-3.5 w-3.5" />}
          onClick={e => { e.stopPropagation(); openEdit(s); }}
        >
          Edit
        </Button>
      ),
    },
  ];

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const expandedQuestions = expandedSurveyData?.questions ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Survey Designer"
        subtitle="Build and manage compliance and risk assessment surveys"
        actions={
          <Button icon={<PlusIcon className="h-4 w-4" />} onClick={() => setShowCreateModal(true)}>
            Create Survey
          </Button>
        }
      />

      {/* Filters */}
      <Card padding="md">
        <SearchInput
          placeholder="Search by survey name or creator..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          onClear={() => setSearch('')}
        />
      </Card>

      {/* Survey Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        emptyMessage="No surveys found. Click 'Create Survey' to build your first survey."
      />

      {/* Inline Question Editor */}
      {expandedSurveyId && (
        <Card padding="md">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                Questions — {surveys.find(s => s.id === expandedSurveyId)?.survey_name}
              </h3>
              <Button
                size="sm"
                icon={<PlusIcon className="h-3.5 w-3.5" />}
                onClick={() => setAddingQuestion(true)}
              >
                Add Question
              </Button>
            </div>

            {expandedQuestions.length > 0 ? (
              <ol className="space-y-2">
                {expandedQuestions.map((q, i) => (
                  <li
                    key={q.id ?? i}
                    className="flex items-start justify-between bg-gray-50 dark:bg-slate-800 rounded-lg px-4 py-3"
                  >
                    <div>
                      <span className="text-xs text-gray-400 mr-2">{i + 1}.</span>
                      <span className="text-sm text-gray-900 dark:text-gray-100">{q.question_text}</span>
                      <span className="ml-2 text-xs text-gray-400 capitalize">({q.question_type.replace('_', ' ')})</span>
                      {q.required && (
                        <span className="ml-1 text-xs text-red-400">*</span>
                      )}
                      {(q.options ?? []).length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {(q.options ?? []).map(opt => (
                            <span key={opt} className="text-xs bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded px-2 py-0.5 text-gray-600 dark:text-gray-400">
                              {opt}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => q.id && deleteQuestionMutation.mutate({ surveyId: expandedSurveyId, questionId: q.id })}
                      className="ml-3 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-gray-400 text-center py-4">No questions yet. Add your first question.</p>
            )}

            {addingQuestion && (
              <div className="border border-gray-200 dark:border-slate-600 rounded-xl p-4 space-y-4 bg-indigo-50/30 dark:bg-indigo-900/10">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">New Question</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="sm:col-span-2">
                    <Input
                      label="Question Text"
                      value={newQuestion.question_text}
                      onChange={e => setNewQuestion(prev => ({ ...prev, question_text: e.target.value }))}
                      placeholder="Enter your question..."
                    />
                  </div>
                  <Select
                    label="Question Type"
                    value={newQuestion.question_type}
                    onChange={e => setNewQuestion(prev => ({ ...prev, question_type: e.target.value as QuestionType, options: [] }))}
                    options={QUESTION_TYPE_OPTIONS}
                  />
                  <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer self-end pb-2">
                    <input
                      type="checkbox"
                      checked={newQuestion.required}
                      onChange={e => setNewQuestion(prev => ({ ...prev, required: e.target.checked }))}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    Required
                  </label>
                </div>

                {newQuestion.question_type === 'choice' && (
                  <div>
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">Options</p>
                    <div className="space-y-2">
                      {(newQuestion.options ?? []).map((opt, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <span className="text-sm text-gray-700 dark:text-gray-300 flex-1 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded px-3 py-1.5">
                            {opt}
                          </span>
                          <button
                            onClick={() => setNewQuestion(prev => ({
                              ...prev,
                              options: (prev.options ?? []).filter((_, j) => j !== i),
                            }))}
                            className="text-gray-400 hover:text-red-500"
                          >
                            <TrashIcon className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={newOptionText}
                          onChange={e => setNewOptionText(e.target.value)}
                          onKeyDown={e => {
                            if (e.key === 'Enter' && newOptionText.trim()) {
                              setNewQuestion(prev => ({
                                ...prev,
                                options: [...(prev.options ?? []), newOptionText.trim()],
                              }));
                              setNewOptionText('');
                            }
                          }}
                          placeholder="Type option and press Enter"
                          className="flex-1 text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            if (newOptionText.trim()) {
                              setNewQuestion(prev => ({ ...prev, options: [...(prev.options ?? []), newOptionText.trim()] }));
                              setNewOptionText('');
                            }
                          }}
                        >
                          Add
                        </Button>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex justify-end gap-2">
                  <Button variant="secondary" size="sm" onClick={() => setAddingQuestion(false)}>Cancel</Button>
                  <Button
                    size="sm"
                    loading={addQuestionMutation.isPending}
                    onClick={handleAddQuestion}
                    disabled={!newQuestion.question_text.trim()}
                  >
                    Add Question
                  </Button>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Create Modal */}
      <Modal
        open={showCreateModal}
        onClose={() => { setShowCreateModal(false); setForm(EMPTY_SURVEY_FORM); }}
        title="Create Survey"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowCreateModal(false)}>Cancel</Button>
            <Button onClick={handleCreateSubmit} loading={isSaving}>Create Survey</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Survey Name"
                required
                value={form.survey_name}
                onChange={e => setField('survey_name', e.target.value)}
                error={formErrors.survey_name}
                placeholder="e.g. Q4 2026 SOX Controls Self-Assessment"
              />
            </div>
            <Select
              label="Survey Type"
              required
              value={form.survey_type}
              onChange={e => setField('survey_type', e.target.value as SurveyType)}
              options={[{ value: '', label: 'Select type...' }, ...SURVEY_TYPE_OPTIONS]}
              error={formErrors.survey_type}
            />
            <Select
              label="Status"
              value={form.status}
              onChange={e => setField('status', e.target.value as SurveyStatus)}
              options={STATUS_OPTIONS}
            />
            <Input
              label="Due Date"
              type="date"
              value={form.due_date}
              onChange={e => setField('due_date', e.target.value)}
            />
          </div>
          <Textarea
            label="Description"
            value={form.description}
            onChange={e => setField('description', e.target.value)}
            rows={3}
            placeholder="Describe the purpose of this survey..."
          />
        </div>
      </Modal>

      {/* Edit Modal */}
      <Modal
        open={!!editingSurvey}
        onClose={() => setEditingSurvey(null)}
        title="Edit Survey"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditingSurvey(null)}>Cancel</Button>
            <Button onClick={handleEditSubmit} loading={updateMutation.isPending}>Save Changes</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Survey Name"
                required
                value={form.survey_name}
                onChange={e => setField('survey_name', e.target.value)}
                error={formErrors.survey_name}
              />
            </div>
            <Select
              label="Survey Type"
              required
              value={form.survey_type}
              onChange={e => setField('survey_type', e.target.value as SurveyType)}
              options={[{ value: '', label: 'Select type...' }, ...SURVEY_TYPE_OPTIONS]}
              error={formErrors.survey_type}
            />
            <Select
              label="Status"
              value={form.status}
              onChange={e => setField('status', e.target.value as SurveyStatus)}
              options={STATUS_OPTIONS}
            />
            <Input
              label="Due Date"
              type="date"
              value={form.due_date}
              onChange={e => setField('due_date', e.target.value)}
            />
          </div>
          <Textarea
            label="Description"
            value={form.description}
            onChange={e => setField('description', e.target.value)}
            rows={3}
          />
        </div>
      </Modal>
    </div>
  );
}
