import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ShieldCheckIcon,
  XMarkIcon,
  ChatBubbleLeftRightIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  Table,
  Select,
  SearchInput,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type WbCategory = 'fraud' | 'corruption' | 'safety' | 'harassment' | 'other';
type WbStatus = 'new' | 'under_review' | 'investigating' | 'closed' | 'dismissed';
type WbPriority = 'critical' | 'high' | 'medium' | 'low';

interface WhistleblowerCase {
  id: string;
  case_reference: string;
  category: WbCategory;
  status: WbStatus;
  priority: WbPriority;
  submitted_at: string;
  assigned_to?: string;
  summary?: string;
  details?: string;
  is_anonymous: boolean;
  messages?: { sender: string; content: string; sent_at: string }[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_VARIANT: Record<WbStatus, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  new: 'danger',
  under_review: 'warning',
  investigating: 'info',
  closed: 'success',
  dismissed: 'neutral',
};

const PRIORITY_VARIANT: Record<WbPriority, 'danger' | 'warning' | 'info' | 'success'> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'success',
};

const CATEGORY_VARIANT: Record<WbCategory, 'danger' | 'warning' | 'info' | 'success' | 'neutral'> = {
  fraud: 'danger',
  corruption: 'warning',
  safety: 'info',
  harassment: 'warning',
  other: 'neutral',
};

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'new', label: 'New' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'investigating', label: 'Investigating' },
  { value: 'closed', label: 'Closed' },
  { value: 'dismissed', label: 'Dismissed' },
];

const PRIORITY_OPTIONS = [
  { value: '', label: 'All Priorities' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function WhistleblowerInbox() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [viewingCase, setViewingCase] = useState<WhistleblowerCase | null>(null);
  const [replyMessage, setReplyMessage] = useState('');
  const [newStatus, setNewStatus] = useState<WbStatus | ''>('');
  const [assignTo, setAssignTo] = useState('');

  // ── Queries ──

  const { data: casesData, isLoading } = useQuery<WhistleblowerCase[]>({
    queryKey: ['wb-cases', statusFilter, priorityFilter],
    queryFn: () =>
      api
        .get('/whistleblower/cases', {
          params: {
            ...(statusFilter ? { status: statusFilter } : {}),
            ...(priorityFilter ? { priority: priorityFilter } : {}),
          },
        })
        .then(r => r.data?.cases ?? r.data ?? []),
  });

  const { data: caseDetail } = useQuery<WhistleblowerCase>({
    queryKey: ['wb-case-detail', viewingCase?.id],
    queryFn: () => api.get(`/whistleblower/cases/${viewingCase!.id}`).then(r => r.data),
    enabled: !!viewingCase,
  });

  const cases: WhistleblowerCase[] = casesData ?? [];

  const filtered = cases.filter(c => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.case_reference.toLowerCase().includes(q) ||
      (c.summary ?? '').toLowerCase().includes(q) ||
      (c.assigned_to ?? '').toLowerCase().includes(q)
    );
  });

  // ── Stats ──

  const totalCases = cases.length;
  const openCases = cases.filter(c => c.status !== 'closed' && c.status !== 'dismissed').length;
  const investigating = cases.filter(c => c.status === 'investigating').length;
  const avgCycleTime = (() => {
    const closed = cases.filter(c => c.status === 'closed' && c.submitted_at);
    if (!closed.length) return 0;
    return Math.round(
      closed.reduce((sum, c) => sum + (Date.now() - new Date(c.submitted_at).getTime()), 0) /
        closed.length /
        (1000 * 60 * 60 * 24)
    );
  })();

  // ── Mutations ──

  const updateCaseMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      api.patch(`/whistleblower/cases/${id}`, data),
    onSuccess: () => {
      toast.success('Case updated');
      queryClient.invalidateQueries({ queryKey: ['wb-cases'] });
      queryClient.invalidateQueries({ queryKey: ['wb-case-detail', viewingCase?.id] });
      setNewStatus('');
      setAssignTo('');
    },
    onError: () => toast.error('Failed to update case'),
  });

  const sendMessageMutation = useMutation({
    mutationFn: ({ id, message }: { id: string; message: string }) =>
      api.post(`/whistleblower/cases/${id}/messages`, { content: message }),
    onSuccess: () => {
      toast.success('Message sent');
      queryClient.invalidateQueries({ queryKey: ['wb-case-detail', viewingCase?.id] });
      setReplyMessage('');
    },
    onError: () => toast.error('Failed to send message'),
  });

  // ── Columns ──

  const columns = [
    {
      key: 'case_reference',
      header: 'Reference',
      render: (c: WhistleblowerCase) => (
        <span className="text-sm font-mono font-medium text-indigo-600 dark:text-indigo-400">
          {c.case_reference}
        </span>
      ),
    },
    {
      key: 'category',
      header: 'Category',
      render: (c: WhistleblowerCase) => (
        <Badge variant={CATEGORY_VARIANT[c.category]} size="sm">
          {c.category}
        </Badge>
      ),
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (c: WhistleblowerCase) => (
        <Badge variant={PRIORITY_VARIANT[c.priority]} size="sm">
          {c.priority}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (c: WhistleblowerCase) => (
        <Badge variant={STATUS_VARIANT[c.status]} dot size="sm">
          {c.status.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'submitted_at',
      header: 'Submitted',
      render: (c: WhistleblowerCase) => (
        <span className="text-sm text-gray-500">
          {new Date(c.submitted_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'assigned_to',
      header: 'Assigned To',
      render: (c: WhistleblowerCase) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">
          {c.assigned_to || <span className="text-gray-400 italic">Unassigned</span>}
        </span>
      ),
    },
    {
      key: 'anonymous',
      header: 'Anonymous',
      render: (c: WhistleblowerCase) => (
        <span className={`text-xs ${c.is_anonymous ? 'text-gray-400' : 'text-green-600 dark:text-green-400'}`}>
          {c.is_anonymous ? 'Yes' : 'No'}
        </span>
      ),
    },
  ];

  const activeCase = caseDetail ?? viewingCase;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Whistleblower Inbox"
        subtitle="Investigate and manage confidential compliance reports"
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Cases" value={totalCases} icon={ShieldCheckIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Open Cases" value={openCases} icon={ShieldCheckIcon} iconBgColor="stat-icon-red" iconColor="" />
        <StatCard title="Investigating" value={investigating} icon={ShieldCheckIcon} iconBgColor="stat-icon-yellow" iconColor="" />
        <StatCard title="Avg Cycle Time (days)" value={avgCycleTime} icon={ShieldCheckIcon} iconBgColor="stat-icon-green" iconColor="" />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by reference, summary, or assignee..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} options={STATUS_OPTIONS} />
          <Select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} options={PRIORITY_OPTIONS} />
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        onRowClick={c => setViewingCase(c)}
        emptyMessage="No whistleblower cases found."
      />

      {/* Case Detail Side Panel */}
      {viewingCase && activeCase && (
        <div className="fixed inset-y-0 right-0 w-[520px] bg-white dark:bg-slate-900 border-l border-gray-200 dark:border-slate-700 shadow-2xl z-40 flex flex-col">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700 flex-shrink-0">
            <div>
              <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 font-mono">
                {activeCase.case_reference}
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant={STATUS_VARIANT[activeCase.status]} dot size="sm">
                  {activeCase.status.replace('_', ' ')}
                </Badge>
                <Badge variant={CATEGORY_VARIANT[activeCase.category]} size="sm">
                  {activeCase.category}
                </Badge>
                {activeCase.is_anonymous && (
                  <span className="text-xs text-gray-400 flex items-center gap-1">
                    <UserIcon className="h-3 w-3" /> Anonymous
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={() => setViewingCase(null)}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-400 transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Summary */}
            {activeCase.summary && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Summary</p>
                <p className="text-sm text-gray-800 dark:text-gray-200">{activeCase.summary}</p>
              </div>
            )}

            {activeCase.details && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Details</p>
                <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                  {activeCase.details}
                </p>
              </div>
            )}

            {/* Message Thread */}
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                <ChatBubbleLeftRightIcon className="h-3.5 w-3.5" /> Messages
              </p>
              {(activeCase.messages ?? []).length > 0 ? (
                <div className="space-y-3">
                  {(activeCase.messages ?? []).map((msg, i) => (
                    <div
                      key={i}
                      className={`rounded-lg px-3 py-2 text-sm ${
                        msg.sender === 'system'
                          ? 'bg-gray-50 dark:bg-slate-800 text-gray-600 dark:text-gray-400'
                          : 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-800 dark:text-indigo-200'
                      }`}
                    >
                      <p className="font-medium text-xs mb-0.5 capitalize">{msg.sender}</p>
                      <p>{msg.content}</p>
                      <p className="text-xs opacity-60 mt-1">{new Date(msg.sent_at).toLocaleString()}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">No messages yet.</p>
              )}

              {/* Reply Box */}
              <div className="mt-4 space-y-2">
                <textarea
                  value={replyMessage}
                  onChange={e => setReplyMessage(e.target.value)}
                  rows={3}
                  placeholder="Write a reply to the reporter..."
                  className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
                <Button
                  size="sm"
                  disabled={!replyMessage.trim()}
                  loading={sendMessageMutation.isPending}
                  onClick={() => {
                    if (replyMessage.trim()) {
                      sendMessageMutation.mutate({ id: activeCase.id, message: replyMessage });
                    }
                  }}
                >
                  Send Reply
                </Button>
              </div>
            </div>

            {/* Update Status */}
            <div className="border-t border-gray-200 dark:border-slate-700 pt-5 space-y-3">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Update Case</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">New Status</label>
                  <select
                    value={newStatus}
                    onChange={e => setNewStatus(e.target.value as WbStatus)}
                    className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">No change</option>
                    {STATUS_OPTIONS.filter(o => o.value).map(o => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Assign To</label>
                  <input
                    type="text"
                    value={assignTo}
                    onChange={e => setAssignTo(e.target.value)}
                    placeholder="Investigator name"
                    className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
              <Button
                size="sm"
                disabled={!newStatus && !assignTo}
                loading={updateCaseMutation.isPending}
                onClick={() => {
                  const updates: Record<string, unknown> = {};
                  if (newStatus) updates.status = newStatus;
                  if (assignTo) updates.assigned_to = assignTo;
                  if (Object.keys(updates).length > 0) {
                    updateCaseMutation.mutate({ id: activeCase.id, data: updates });
                  }
                }}
              >
                Update Case
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
