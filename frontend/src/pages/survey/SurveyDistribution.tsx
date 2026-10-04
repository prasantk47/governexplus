import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PaperAirplaneIcon,
  BellIcon,
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

type DistributionStatus = 'pending' | 'sent' | 'in_progress' | 'completed' | 'expired';

interface SurveyDistribution {
  id: string;
  survey_id: string;
  survey_name?: string;
  recipient_name: string;
  recipient_email: string;
  status: DistributionStatus;
  sent_at?: string;
  due_date?: string;
  completed_at?: string;
}

interface Survey {
  id: string;
  survey_name: string;
  status: string;
}

interface DistributeForm {
  survey_id: string;
  recipients: string;
  due_date: string;
  message: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_FORM: DistributeForm = {
  survey_id: '',
  recipients: '',
  due_date: '',
  message: '',
};

const STATUS_VARIANT: Record<DistributionStatus, 'success' | 'warning' | 'info' | 'neutral' | 'danger'> = {
  pending: 'neutral',
  sent: 'info',
  in_progress: 'warning',
  completed: 'success',
  expired: 'danger',
};

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'sent', label: 'Sent' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'expired', label: 'Expired' },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function SurveyDistribution() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [surveyFilter, setSurveyFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<DistributeForm>(EMPTY_FORM);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof DistributeForm, string>>>({});

  // ── Queries ──

  const { data: surveysData } = useQuery<Survey[]>({
    queryKey: ['surveys-active'],
    queryFn: () =>
      api.get('/surveys', { params: { status: 'active' } }).then(r => r.data?.surveys ?? r.data ?? []),
  });

  const { data: distributionsData, isLoading } = useQuery<SurveyDistribution[]>({
    queryKey: ['survey-distributions', surveyFilter, statusFilter],
    queryFn: () =>
      api
        .get('/surveys/distributions', {
          params: {
            ...(surveyFilter ? { survey_id: surveyFilter } : {}),
            ...(statusFilter ? { status: statusFilter } : {}),
          },
        })
        .then(r => r.data?.distributions ?? r.data ?? []),
  });

  const surveys: Survey[] = surveysData ?? [];
  const distributions: SurveyDistribution[] = distributionsData ?? [];

  const filtered = distributions.filter(d => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      d.recipient_name.toLowerCase().includes(q) ||
      d.recipient_email.toLowerCase().includes(q) ||
      (d.survey_name ?? '').toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const distributeMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/surveys/distribute', data),
    onSuccess: () => {
      toast.success('Survey distributed successfully');
      queryClient.invalidateQueries({ queryKey: ['survey-distributions'] });
      setShowModal(false);
      setForm(EMPTY_FORM);
    },
    onError: () => toast.error('Failed to distribute survey'),
  });

  const reminderMutation = useMutation({
    mutationFn: (id: string) => api.post(`/surveys/distributions/${id}/remind`),
    onSuccess: () => toast.success('Reminder sent'),
    onError: () => toast.error('Failed to send reminder'),
  });

  // ── Handlers ──

  function validate(): boolean {
    const errors: Partial<Record<keyof DistributeForm, string>> = {};
    if (!form.survey_id) errors.survey_id = 'Please select a survey';
    if (!form.recipients.trim()) errors.recipients = 'At least one recipient is required';
    if (!form.due_date) errors.due_date = 'Due date is required';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
    const recipientList = form.recipients
      .split(/[\n,;]/)
      .map(s => s.trim())
      .filter(s => s.includes('@'));
    distributeMutation.mutate({ ...form, recipient_emails: recipientList });
  }

  function setField<K extends keyof DistributeForm>(key: K, value: DistributeForm[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
    if (formErrors[key]) setFormErrors(prev => ({ ...prev, [key]: undefined }));
  }

  // ── Columns ──

  const columns = [
    {
      key: 'recipient',
      header: 'Recipient',
      render: (d: SurveyDistribution) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{d.recipient_name}</div>
          <div className="text-xs text-gray-400">{d.recipient_email}</div>
        </div>
      ),
    },
    {
      key: 'survey_name',
      header: 'Survey',
      render: (d: SurveyDistribution) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{d.survey_name || d.survey_id}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (d: SurveyDistribution) => (
        <Badge variant={STATUS_VARIANT[d.status]} dot size="sm">
          {d.status.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'sent_at',
      header: 'Sent',
      render: (d: SurveyDistribution) => (
        <span className="text-sm text-gray-500">
          {d.sent_at ? new Date(d.sent_at).toLocaleDateString() : '—'}
        </span>
      ),
    },
    {
      key: 'due_date',
      header: 'Due',
      render: (d: SurveyDistribution) => {
        const overdue = d.due_date && new Date(d.due_date) < new Date() && d.status !== 'completed';
        return (
          <span className={`text-sm ${overdue ? 'text-red-600 font-medium' : 'text-gray-500'}`}>
            {d.due_date ? new Date(d.due_date).toLocaleDateString() : '—'}
          </span>
        );
      },
    },
    {
      key: 'completed_at',
      header: 'Completed',
      render: (d: SurveyDistribution) => (
        <span className="text-sm text-gray-500">
          {d.completed_at ? new Date(d.completed_at).toLocaleDateString() : '—'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (d: SurveyDistribution) =>
        (d.status === 'sent' || d.status === 'in_progress') &&
        d.due_date &&
        new Date(d.due_date) < new Date() ? (
          <Button
            size="sm"
            variant="ghost"
            icon={<BellIcon className="h-3.5 w-3.5" />}
            loading={reminderMutation.isPending}
            onClick={e => { e.stopPropagation(); reminderMutation.mutate(d.id); }}
          >
            Remind
          </Button>
        ) : null,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Survey Distribution"
        subtitle="Send surveys and track recipient completion status"
        actions={
          <Button
            icon={<PaperAirplaneIcon className="h-4 w-4" />}
            onClick={() => setShowModal(true)}
          >
            Distribute Survey
          </Button>
        }
      />

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by recipient name, email, or survey..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <select
            value={surveyFilter}
            onChange={e => setSurveyFilter(e.target.value)}
            className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Surveys</option>
            {surveys.map(s => (
              <option key={s.id} value={s.id}>{s.survey_name}</option>
            ))}
          </select>
          <Select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            options={STATUS_OPTIONS}
          />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        emptyMessage="No distributions found. Click 'Distribute Survey' to send your first survey."
      />

      {/* Distribution Modal */}
      <Modal
        open={showModal}
        onClose={() => { setShowModal(false); setForm(EMPTY_FORM); setFormErrors({}); }}
        title="Distribute Survey"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button
              icon={<PaperAirplaneIcon className="h-4 w-4" />}
              onClick={handleSubmit}
              loading={distributeMutation.isPending}
            >
              Send Survey
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Survey <span className="text-red-500">*</span>
              </label>
              <select
                value={form.survey_id}
                onChange={e => setField('survey_id', e.target.value)}
                className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select survey...</option>
                {surveys.map(s => (
                  <option key={s.id} value={s.id}>{s.survey_name}</option>
                ))}
              </select>
              {formErrors.survey_id && (
                <p className="text-xs text-red-500 mt-1">{formErrors.survey_id}</p>
              )}
            </div>
            <Input
              label="Due Date"
              type="date"
              required
              value={form.due_date}
              onChange={e => setField('due_date', e.target.value)}
              error={formErrors.due_date}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Recipients <span className="text-red-500">*</span>
            </label>
            <textarea
              value={form.recipients}
              onChange={e => setField('recipients', e.target.value)}
              rows={5}
              className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
              placeholder="Enter email addresses — one per line, or comma/semicolon separated:&#10;john.doe@company.com&#10;jane.smith@company.com"
            />
            {formErrors.recipients && (
              <p className="text-xs text-red-500 mt-1">{formErrors.recipients}</p>
            )}
            <p className="text-xs text-gray-400 mt-1">
              Separate multiple emails by newline, comma, or semicolon.
            </p>
          </div>

          <Textarea
            label="Custom Message (optional)"
            value={form.message}
            onChange={e => setField('message', e.target.value)}
            rows={3}
            placeholder="Add a personal message to the survey invitation email..."
          />
        </div>
      </Modal>
    </div>
  );
}
