import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowPathIcon,
  CalendarDaysIcon,
  ExclamationCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  Table,
  SearchInput,
  Select,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type JmlEventType = 'joiner' | 'mover' | 'leaver';
type JmlEventStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'manual_review';

interface JmlEvent {
  id: string;
  event_type: JmlEventType;
  employee_name: string;
  employee_id: string;
  old_position?: string;
  new_position?: string;
  effective_date: string;
  status: JmlEventStatus;
  error_message?: string;
  actions_taken?: string[];
  created_at?: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EVENT_TYPE_VARIANT: Record<JmlEventType, 'success' | 'info' | 'danger'> = {
  joiner: 'success',
  mover: 'info',
  leaver: 'danger',
};

const STATUS_VARIANT: Record<JmlEventStatus, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  pending: 'warning',
  processing: 'info',
  completed: 'success',
  failed: 'danger',
  manual_review: 'warning',
};

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'manual_review', label: 'Manual Review' },
];

const EVENT_TYPE_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Types' },
  { value: 'joiner', label: 'Joiner' },
  { value: 'mover', label: 'Mover' },
  { value: 'leaver', label: 'Leaver' },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function HrEventMonitor() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [viewingEvent, setViewingEvent] = useState<JmlEvent | null>(null);

  // ── Queries ──

  const { data: eventsData, isLoading } = useQuery<JmlEvent[]>({
    queryKey: ['jml-events', statusFilter, eventTypeFilter],
    queryFn: () =>
      api
        .get('/jml/events', {
          params: {
            ...(statusFilter ? { status: statusFilter } : {}),
            ...(eventTypeFilter ? { event_type: eventTypeFilter } : {}),
          },
        })
        .then(r => r.data?.events ?? r.data ?? []),
    refetchInterval: 30_000,
  });

  const events: JmlEvent[] = eventsData ?? [];

  const filtered = events.filter(e => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      e.employee_name.toLowerCase().includes(q) ||
      e.employee_id.toLowerCase().includes(q) ||
      (e.new_position ?? '').toLowerCase().includes(q)
    );
  });

  // ── Mutations ──

  const retryMutation = useMutation({
    mutationFn: (id: string) => api.post(`/jml/events/${id}/retry`),
    onSuccess: () => {
      toast.success('Event queued for retry');
      queryClient.invalidateQueries({ queryKey: ['jml-events'] });
    },
    onError: () => toast.error('Failed to retry event'),
  });

  // ── Stats ──

  const today = new Date().toISOString().slice(0, 10);
  const eventsToday = events.filter(e => (e.created_at ?? e.effective_date ?? '').startsWith(today)).length;
  const pendingCount = events.filter(e => e.status === 'pending' || e.status === 'processing').length;
  const failedCount = events.filter(e => e.status === 'failed').length;

  // ── Columns ──

  const columns = [
    {
      key: 'employee',
      header: 'Employee',
      render: (e: JmlEvent) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{e.employee_name}</div>
          <div className="text-xs text-gray-400 font-mono">{e.employee_id}</div>
        </div>
      ),
    },
    {
      key: 'event_type',
      header: 'Event',
      render: (e: JmlEvent) => (
        <Badge variant={EVENT_TYPE_VARIANT[e.event_type]} size="sm">
          {e.event_type.charAt(0).toUpperCase() + e.event_type.slice(1)}
        </Badge>
      ),
    },
    {
      key: 'position',
      header: 'Position Change',
      render: (e: JmlEvent) => (
        <div className="text-sm text-gray-600 dark:text-gray-400">
          {e.old_position && e.new_position ? (
            <span>
              <span className="text-gray-500">{e.old_position}</span>
              <span className="mx-1 text-gray-400">→</span>
              <span className="text-gray-900 dark:text-gray-100">{e.new_position}</span>
            </span>
          ) : e.new_position ? (
            <span className="text-gray-900 dark:text-gray-100">{e.new_position}</span>
          ) : e.old_position ? (
            <span className="line-through text-gray-400">{e.old_position}</span>
          ) : (
            <span className="text-gray-400">—</span>
          )}
        </div>
      ),
    },
    {
      key: 'effective_date',
      header: 'Effective Date',
      render: (e: JmlEvent) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {e.effective_date ? new Date(e.effective_date).toLocaleDateString() : '—'}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (e: JmlEvent) => (
        <div>
          <Badge variant={STATUS_VARIANT[e.status]} dot size="sm">
            {e.status.replace('_', ' ')}
          </Badge>
          {e.error_message && (
            <p className="text-xs text-red-500 mt-0.5 max-w-[180px] truncate" title={e.error_message}>
              {e.error_message}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (e: JmlEvent) => (
        <div className="flex justify-end gap-2">
          {e.status === 'failed' && (
            <Button
              size="sm"
              variant="ghost"
              icon={<ArrowPathIcon className="h-3.5 w-3.5" />}
              loading={retryMutation.isPending}
              onClick={ev => { ev.stopPropagation(); retryMutation.mutate(e.id); }}
            >
              Retry
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={ev => { ev.stopPropagation(); setViewingEvent(e); }}
          >
            Details
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="HR Event Monitor"
        subtitle="Real-time stream of Joiner, Mover, and Leaver events from HR systems"
      />

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard title="Events Today" value={eventsToday} icon={CalendarDaysIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Pending / Processing" value={pendingCount} icon={ClockIcon} iconBgColor="stat-icon-yellow" iconColor="" />
        <StatCard title="Failed" value={failedCount} icon={ExclamationCircleIcon} iconBgColor="stat-icon-red" iconColor="" />
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by employee name or ID..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={eventTypeFilter}
            onChange={e => setEventTypeFilter(e.target.value)}
            options={EVENT_TYPE_FILTER_OPTIONS}
          />
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
        onRowClick={e => setViewingEvent(e)}
        emptyMessage="No HR events found matching the current filters."
      />

      {/* Detail Modal */}
      {viewingEvent && (
        <div className="fixed inset-y-0 right-0 w-[440px] bg-white dark:bg-slate-900 border-l border-gray-200 dark:border-slate-700 shadow-2xl z-40 overflow-y-auto">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700">
            <div>
              <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                {viewingEvent.employee_name}
              </h2>
              <p className="text-xs text-gray-500 mt-0.5 font-mono">{viewingEvent.employee_id}</p>
            </div>
            <button
              onClick={() => setViewingEvent(null)}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-400 hover:text-gray-600 transition-colors"
            >
              ×
            </button>
          </div>
          <div className="p-6 space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Event Type</p>
                <Badge variant={EVENT_TYPE_VARIANT[viewingEvent.event_type]} size="sm">
                  {viewingEvent.event_type}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Status</p>
                <Badge variant={STATUS_VARIANT[viewingEvent.status]} dot size="sm">
                  {viewingEvent.status.replace('_', ' ')}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Effective Date</p>
                <p className="text-sm text-gray-800 dark:text-gray-200">
                  {viewingEvent.effective_date
                    ? new Date(viewingEvent.effective_date).toLocaleDateString()
                    : '—'}
                </p>
              </div>
              {viewingEvent.old_position && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Previous Position</p>
                  <p className="text-sm text-gray-800 dark:text-gray-200">{viewingEvent.old_position}</p>
                </div>
              )}
              {viewingEvent.new_position && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">New Position</p>
                  <p className="text-sm text-gray-800 dark:text-gray-200">{viewingEvent.new_position}</p>
                </div>
              )}
            </div>

            {viewingEvent.error_message && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
                <p className="text-xs font-medium text-red-700 dark:text-red-400 mb-1">Error</p>
                <p className="text-sm text-red-600 dark:text-red-300">{viewingEvent.error_message}</p>
              </div>
            )}

            {(viewingEvent.actions_taken ?? []).length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Actions Taken</p>
                <ul className="space-y-1">
                  {(viewingEvent.actions_taken ?? []).map((action, i) => (
                    <li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2">
                      <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-indigo-500 flex-shrink-0" />
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {viewingEvent.status === 'failed' && (
              <Button
                icon={<ArrowPathIcon className="h-4 w-4" />}
                onClick={() => { retryMutation.mutate(viewingEvent.id); setViewingEvent(null); }}
                loading={retryMutation.isPending}
                className="w-full justify-center"
              >
                Retry Event
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
