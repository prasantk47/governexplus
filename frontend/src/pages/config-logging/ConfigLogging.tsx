import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  DocumentMagnifyingGlassIcon,
  ShieldExclamationIcon,
  ServerStackIcon,
  ClipboardDocumentListIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Badge,
  Table,
  Select,
  SearchInput,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ConfigEvent {
  id: string;
  event_id: string;
  event_type: string;
  module: string;
  object_type: string;
  actor: string;
  result: string;
  details?: string;
  created_at: string;
}

interface PrivilegedActivity {
  id: string;
  actor: string;
  action: string;
  module: string;
  risk_level: string;
  timestamp: string;
  details?: string;
}

interface SummaryData {
  total_events: number;
  by_module: Record<string, number>;
  by_event_type: Record<string, number>;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const RESULT_VARIANT: Record<string, 'success' | 'danger' | 'warning' | 'neutral'> = {
  success: 'success',
  failure: 'danger',
  warning: 'warning',
  blocked: 'danger',
  partial: 'warning',
};

const MODULE_OPTIONS = [
  { value: '', label: 'All Modules' },
  { value: 'access', label: 'Access' },
  { value: 'risk', label: 'Risk' },
  { value: 'compliance', label: 'Compliance' },
  { value: 'audit', label: 'Audit' },
  { value: 'auth', label: 'Auth' },
  { value: 'config', label: 'Config' },
  { value: 'admin', label: 'Admin' },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function ConfigLogging() {
  const [tab, setTab] = useState<'events' | 'privileged'>('events');
  const [search, setSearch] = useState('');
  const [moduleFilter, setModuleFilter] = useState('');
  const [objectTypeFilter, setObjectTypeFilter] = useState('');
  const [actorFilter, setActorFilter] = useState('');

  // ── Queries ──

  const { data: summaryData } = useQuery<SummaryData>({
    queryKey: ['config-logging-summary'],
    queryFn: () =>
      api.get('/config-logging/summary').then(r => r.data ?? { total_events: 0, by_module: {}, by_event_type: {} }),
  });

  const summary: SummaryData = summaryData ?? { total_events: 0, by_module: {}, by_event_type: {} };

  const { data: eventsData, isLoading: eventsLoading } = useQuery<ConfigEvent[]>({
    queryKey: ['config-logging-events', moduleFilter, objectTypeFilter, actorFilter],
    queryFn: () =>
      api
        .get('/config-logging/events', {
          params: {
            ...(moduleFilter ? { module: moduleFilter } : {}),
            ...(objectTypeFilter ? { object_type: objectTypeFilter } : {}),
            ...(actorFilter ? { actor: actorFilter } : {}),
          },
        })
        .then(r => r.data?.events ?? r.data ?? []),
    enabled: tab === 'events',
  });

  const events: ConfigEvent[] = eventsData ?? [];

  const { data: privilegedData, isLoading: privilegedLoading } = useQuery<PrivilegedActivity[]>({
    queryKey: ['config-logging-privileged'],
    queryFn: () =>
      api
        .get('/config-logging/reports/privileged-activity')
        .then(r => r.data?.activities ?? r.data ?? []),
    enabled: tab === 'privileged',
  });

  const privileged: PrivilegedActivity[] = privilegedData ?? [];

  // ── Filtering ──

  const filteredEvents = events.filter(e => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      e.event_id.toLowerCase().includes(q) ||
      e.event_type.toLowerCase().includes(q) ||
      e.actor.toLowerCase().includes(q) ||
      e.module.toLowerCase().includes(q)
    );
  });

  const filteredPrivileged = privileged.filter(p => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      p.actor.toLowerCase().includes(q) ||
      p.action.toLowerCase().includes(q) ||
      p.module.toLowerCase().includes(q)
    );
  });

  // ── Stats ──

  const topModules = Object.entries(summary.by_module)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 1);
  const topModule = topModules.length > 0 ? `${topModules[0][0]} (${topModules[0][1]})` : '—';

  const topTypes = Object.entries(summary.by_event_type)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 1);
  const topType = topTypes.length > 0 ? `${topTypes[0][0]} (${topTypes[0][1]})` : '—';

  // ── Event Columns ──

  const eventColumns = [
    {
      key: 'event_id',
      header: 'Event ID',
      render: (e: ConfigEvent) => (
        <span className="text-sm font-mono font-medium text-indigo-600 dark:text-indigo-400">
          {e.event_id}
        </span>
      ),
    },
    {
      key: 'event_type',
      header: 'Event Type',
      render: (e: ConfigEvent) => (
        <span className="text-sm text-gray-900 dark:text-gray-100">{e.event_type.replace(/_/g, ' ')}</span>
      ),
    },
    {
      key: 'module',
      header: 'Module',
      render: (e: ConfigEvent) => (
        <Badge variant="neutral" size="sm">{e.module}</Badge>
      ),
    },
    {
      key: 'object_type',
      header: 'Object Type',
      render: (e: ConfigEvent) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{e.object_type || '—'}</span>
      ),
    },
    {
      key: 'actor',
      header: 'Actor',
      render: (e: ConfigEvent) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{e.actor}</span>
      ),
    },
    {
      key: 'result',
      header: 'Result',
      render: (e: ConfigEvent) => (
        <Badge variant={RESULT_VARIANT[e.result] ?? 'neutral'} dot size="sm">
          {e.result}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      header: 'Time',
      render: (e: ConfigEvent) => (
        <span className="text-sm text-gray-500">
          {new Date(e.created_at).toLocaleString()}
        </span>
      ),
    },
  ];

  // ── Privileged Columns ──

  const privilegedColumns = [
    {
      key: 'actor',
      header: 'Actor',
      render: (p: PrivilegedActivity) => (
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{p.actor}</span>
      ),
    },
    {
      key: 'action',
      header: 'Action',
      render: (p: PrivilegedActivity) => (
        <span className="text-sm text-gray-700 dark:text-gray-300">{p.action.replace(/_/g, ' ')}</span>
      ),
    },
    {
      key: 'module',
      header: 'Module',
      render: (p: PrivilegedActivity) => (
        <Badge variant="neutral" size="sm">{p.module}</Badge>
      ),
    },
    {
      key: 'risk_level',
      header: 'Risk Level',
      render: (p: PrivilegedActivity) => (
        <Badge
          variant={p.risk_level === 'critical' ? 'danger' : p.risk_level === 'high' ? 'warning' : 'info'}
          size="sm"
        >
          {p.risk_level}
        </Badge>
      ),
    },
    {
      key: 'timestamp',
      header: 'Time',
      render: (p: PrivilegedActivity) => (
        <span className="text-sm text-gray-500">{new Date(p.timestamp).toLocaleString()}</span>
      ),
    },
    {
      key: 'details',
      header: 'Details',
      render: (p: PrivilegedActivity) => (
        <span className="text-sm text-gray-500 max-w-xs truncate block">{p.details || '—'}</span>
      ),
    },
  ];

  const tabs = [
    { key: 'events' as const, label: 'Event Log' },
    { key: 'privileged' as const, label: 'Privileged Activity' },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Configuration Logging"
        subtitle="Audit trail of configuration events and privileged activities"
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Events" value={summary.total_events} icon={ClipboardDocumentListIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Top Module" value={topModule} icon={ServerStackIcon} iconBgColor="stat-icon-indigo" iconColor="" />
        <StatCard title="Top Event Type" value={topType} icon={DocumentMagnifyingGlassIcon} iconBgColor="stat-icon-purple" iconColor="" />
        <StatCard title="Privileged Events" value={privileged.length} icon={ShieldExclamationIcon} iconBgColor="stat-icon-red" iconColor="" />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex -mb-px space-x-6">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t.key
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search events..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          {tab === 'events' && (
            <>
              <Select
                value={moduleFilter}
                onChange={e => setModuleFilter(e.target.value)}
                options={MODULE_OPTIONS}
              />
              <Select
                value={objectTypeFilter}
                onChange={e => setObjectTypeFilter(e.target.value)}
                options={[
                  { value: '', label: 'All Object Types' },
                  { value: 'role', label: 'Role' },
                  { value: 'user', label: 'User' },
                  { value: 'config', label: 'Config' },
                  { value: 'rule', label: 'Rule' },
                  { value: 'policy', label: 'Policy' },
                ]}
              />
              <Select
                value={actorFilter}
                onChange={e => setActorFilter(e.target.value)}
                options={[{ value: '', label: 'All Actors' }]}
              />
            </>
          )}
        </div>
      </Card>

      {/* Tables */}
      {tab === 'events' && (
        <Table
          columns={eventColumns}
          data={filteredEvents}
          loading={eventsLoading}
          emptyMessage="No configuration events recorded."
        />
      )}

      {tab === 'privileged' && (
        <Table
          columns={privilegedColumns}
          data={filteredPrivileged}
          loading={privilegedLoading}
          emptyMessage="No privileged activity detected."
        />
      )}
    </div>
  );
}
