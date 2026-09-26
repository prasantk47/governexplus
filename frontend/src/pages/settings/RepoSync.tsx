import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  PauseIcon,
  PlayIcon,
  CogIcon,
  ServerIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  CircleStackIcon,
  CloudIcon,
  ArrowsRightLeftIcon,
  BoltIcon,
  ChartBarIcon,
  XMarkIcon,
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  ScaleIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  CardHeader,
  CardBody,
  Button,
  Badge,
  Select,
  Modal,
  LoadingState,
  EmptyState,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';

// ─── Types ────────────────────────────────────────────────────────────────────

type SystemType = 'sap_ecc' | 'sap_s4hana' | 'azure_ad' | 'ldap' | 'successfactors' | 'workday' | 'other';
type SyncConfigStatus = 'active' | 'paused' | 'error';
type SyncDirection = 'inbound' | 'outbound' | 'bidirectional';
type SyncResultStatus = 'success' | 'partial' | 'failed' | 'running';
type ConflictResolution = 'source_wins' | 'target_wins' | 'manual' | 'newest_wins';

interface SyncConfig {
  id: string;
  systemName: string;
  systemType: SystemType;
  status: SyncConfigStatus;
  direction: SyncDirection;
  lastSync: string | null;
  nextSync: string | null;
  objectsSynced: number;
  scheduleMinutes: number;
  conflictResolution: ConflictResolution;
  syncUsers: boolean;
  syncRoles: boolean;
  syncGroups: boolean;
  enabled: boolean;
}

interface SyncHistoryEntry {
  id: string;
  configId: string;
  systemName: string;
  systemType: SystemType;
  direction: SyncDirection;
  startedAt: string;
  completedAt: string | null;
  status: SyncResultStatus;
  objectsSynced: number;
  usersChanged: number;
  rolesChanged: number;
  errors: number;
  durationSeconds: number | null;
  errorDetails: string | null;
}

interface SyncStats {
  connectedSystems: number;
  lastSync: string | null;
  totalSyncedObjects: number;
  syncHealthPct: number;
  activeSyncs: number;
  pendingConflicts: number;
}

interface SyncConflict {
  id: string;
  systemName: string;
  objectType: 'user' | 'role' | 'group';
  objectId: string;
  objectName: string;
  sourceValue: string;
  targetValue: string;
  detectedAt: string;
  resolution: ConflictResolution | null;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const SCHEDULE_OPTIONS = [
  { value: '15', label: 'Every 15 minutes' },
  { value: '30', label: 'Every 30 minutes' },
  { value: '60', label: 'Every hour' },
  { value: '180', label: 'Every 3 hours' },
  { value: '360', label: 'Every 6 hours' },
  { value: '720', label: 'Every 12 hours' },
  { value: '1440', label: 'Daily' },
];

const CONFLICT_RESOLUTION_OPTIONS = [
  { value: 'source_wins', label: 'Source always wins' },
  { value: 'target_wins', label: 'Target always wins' },
  { value: 'newest_wins', label: 'Newest value wins' },
  { value: 'manual', label: 'Manual review required' },
];

const SYSTEM_TYPE_META: Record<SystemType, { label: string; icon: typeof ServerIcon; badgeVariant: 'info' | 'success' | 'warning' | 'neutral' | 'default' }> = {
  sap_ecc:        { label: 'SAP ECC',         icon: ServerIcon,       badgeVariant: 'info' },
  sap_s4hana:     { label: 'SAP S/4HANA',     icon: ServerIcon,       badgeVariant: 'info' },
  azure_ad:       { label: 'Azure AD',         icon: ShieldCheckIcon,  badgeVariant: 'warning' },
  ldap:           { label: 'LDAP',             icon: CircleStackIcon,  badgeVariant: 'neutral' },
  successfactors: { label: 'SuccessFactors',   icon: UserGroupIcon,    badgeVariant: 'success' },
  workday:        { label: 'Workday',          icon: UserGroupIcon,    badgeVariant: 'success' },
  other:          { label: 'Other',            icon: CloudIcon,        badgeVariant: 'default' },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return 'Never';
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function formatFutureTime(isoString: string | null): string {
  if (!isoString) return '-';
  const diff = new Date(isoString).getTime() - Date.now();
  if (diff <= 0) return 'Overdue';
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `in ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `in ${hours}h`;
  return `in ${Math.floor(hours / 24)}d`;
}

function formatDateTime(isoString: string | null): string {
  if (!isoString) return '-';
  return new Date(isoString).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return '-';
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function scheduleLabel(minutes: number): string {
  return SCHEDULE_OPTIONS.find((o) => o.value === String(minutes))?.label ?? `${minutes} min`;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SyncStatusDot({ status }: { status: SyncConfigStatus }) {
  const map: Record<SyncConfigStatus, { dot: string; label: string; text: string }> = {
    active:  { dot: 'bg-emerald-500', label: 'Active',  text: 'text-emerald-600' },
    paused:  { dot: 'bg-amber-400',   label: 'Paused',  text: 'text-amber-600'   },
    error:   { dot: 'bg-red-500',     label: 'Error',   text: 'text-red-600'     },
  };
  const { dot, label, text } = map[status];
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${text}`}>
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

function ResultBadge({ status }: { status: SyncResultStatus }) {
  const map: Record<SyncResultStatus, { label: string; variant: 'success' | 'danger' | 'warning' | 'info' }> = {
    success: { label: 'Success', variant: 'success' },
    partial: { label: 'Partial', variant: 'warning' },
    failed:  { label: 'Failed',  variant: 'danger'  },
    running: { label: 'Running', variant: 'info'    },
  };
  const { label, variant } = map[status];
  return <Badge variant={variant}>{label}</Badge>;
}

function DirectionIcon({ direction }: { direction: SyncDirection }) {
  const map: Record<SyncDirection, { icon: typeof ArrowDownTrayIcon; label: string; cls: string }> = {
    inbound:       { icon: ArrowDownTrayIcon, label: 'Inbound',       cls: 'text-blue-500' },
    outbound:      { icon: ArrowUpTrayIcon,   label: 'Outbound',      cls: 'text-purple-500' },
    bidirectional: { icon: ArrowsRightLeftIcon, label: 'Bidirectional', cls: 'text-indigo-500' },
  };
  const { icon: Icon, label, cls } = map[direction];
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium ${cls}`}>
      <Icon className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}

function SystemTypeChip({ type }: { type: SystemType }) {
  const { label, icon: Icon, badgeVariant } = SYSTEM_TYPE_META[type] ?? SYSTEM_TYPE_META.other;
  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon className="h-3.5 w-3.5 text-gray-500" />
      <Badge variant={badgeVariant}>{label}</Badge>
    </span>
  );
}

// ─── Schedule Modal ────────────────────────────────────────────────────────────

interface ScheduleModalProps {
  config: SyncConfig;
  open: boolean;
  onClose: () => void;
  onSave: (configId: string, scheduleMinutes: number, conflictResolution: ConflictResolution, syncUsers: boolean, syncRoles: boolean, syncGroups: boolean) => void;
  isSaving: boolean;
}

function ScheduleModal({ config, open, onClose, onSave, isSaving }: ScheduleModalProps) {
  const [schedule, setSchedule] = useState(String(config.scheduleMinutes));
  const [resolution, setResolution] = useState<ConflictResolution>(config.conflictResolution);
  const [syncUsers, setSyncUsers] = useState(config.syncUsers);
  const [syncRoles, setSyncRoles] = useState(config.syncRoles);
  const [syncGroups, setSyncGroups] = useState(config.syncGroups);

  const handleSave = () => {
    onSave(config.id, parseInt(schedule, 10), resolution, syncUsers, syncRoles, syncGroups);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Configure Sync — ${config.systemName}`}
      subtitle="Set sync schedule, object scope, and conflict resolution strategy"
      size="md"
    >
      <div className="space-y-5">
        {/* Schedule */}
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Sync Schedule
          </p>
          <Select
            label="Sync Interval"
            value={schedule}
            onChange={(e) => setSchedule(e.target.value)}
            options={SCHEDULE_OPTIONS}
          />
          <p className="text-xs text-gray-400 mt-1.5">
            Next sync will run {formatFutureTime(config.nextSync)} — updating will reschedule
          </p>
        </div>

        {/* Object scope */}
        <div className="border-t border-white/20 pt-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Object Scope
          </p>
          <div className="space-y-2.5">
            {(
              [
                { key: 'users',  label: 'Users',  state: syncUsers,  setState: setSyncUsers  },
                { key: 'roles',  label: 'Roles',  state: syncRoles,  setState: setSyncRoles  },
                { key: 'groups', label: 'Groups', state: syncGroups, setState: setSyncGroups },
              ] as const
            ).map(({ key, label, state, setState }) => (
              <label key={key} className="flex items-center gap-3 cursor-pointer select-none">
                <div
                  role="checkbox"
                  aria-checked={state}
                  tabIndex={0}
                  onClick={() => setState(!state)}
                  onKeyDown={(e) => e.key === ' ' && setState(!state)}
                  className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-1 cursor-pointer ${
                    state ? 'bg-primary-500' : 'bg-gray-300'
                  }`}
                >
                  <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform duration-200 ${state ? 'translate-x-4' : 'translate-x-0.5'}`} />
                </div>
                <span className="text-sm text-gray-700 font-medium">Sync {label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Conflict resolution */}
        <div className="border-t border-white/20 pt-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Conflict Resolution
          </p>
          <Select
            label="When a conflict is detected"
            value={resolution}
            onChange={(e) => setResolution(e.target.value as ConflictResolution)}
            options={CONFLICT_RESOLUTION_OPTIONS}
          />
          <div className="mt-3 rounded-xl bg-amber-50/60 border border-amber-200/60 px-3.5 py-2.5 flex items-start gap-2">
            <ExclamationTriangleIcon className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-amber-700">
              {resolution === 'manual'
                ? 'Manual mode: all conflicts will queue for human review before being applied.'
                : resolution === 'source_wins'
                ? 'Source wins: incoming system data always overwrites the repository value.'
                : resolution === 'target_wins'
                ? 'Target wins: existing repository values are preserved when conflicts arise.'
                : 'Newest wins: the most recently modified value is applied automatically.'}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-2 border-t border-white/20">
          <Button variant="secondary" onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button onClick={handleSave} loading={isSaving}>
            Save Configuration
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ─── Conflict Panel ────────────────────────────────────────────────────────────

interface ConflictPanelProps {
  conflicts: SyncConflict[];
  onResolve: (conflictId: string, resolution: 'keep_source' | 'keep_target') => void;
  resolvingId: string | null;
}

function ConflictPanel({ conflicts, onResolve, resolvingId }: ConflictPanelProps) {
  const objectTypeIcon: Record<SyncConflict['objectType'], typeof ServerIcon> = {
    user:  UserGroupIcon,
    role:  ShieldCheckIcon,
    group: CircleStackIcon,
  };

  if (conflicts.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200/60 px-4 py-8 text-center">
        <CheckCircleIcon className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
        <p className="text-sm font-medium text-gray-600">No conflicts pending</p>
        <p className="text-xs text-gray-400 mt-1">All sync conflicts have been resolved.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {conflicts.map((conflict) => {
        const Icon = objectTypeIcon[conflict.objectType];
        const isResolving = resolvingId === conflict.id;
        return (
          <div
            key={conflict.id}
            className="rounded-xl border border-amber-200/60 bg-amber-50/40 px-4 py-3.5 space-y-3"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <div className="h-7 w-7 rounded-lg bg-amber-100/80 flex items-center justify-center text-amber-600 flex-shrink-0">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-gray-900 truncate">{conflict.objectName}</p>
                  <p className="text-xs text-gray-400">
                    {conflict.systemName} &middot; {conflict.objectType} &middot; {conflict.objectId}
                  </p>
                </div>
              </div>
              <span className="text-xs text-gray-400 flex-shrink-0">{formatRelativeTime(conflict.detectedAt)}</span>
            </div>

            {/* Values */}
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-lg bg-blue-50/60 border border-blue-200/40 px-3 py-2">
                <p className="text-[10px] font-semibold text-blue-600 uppercase tracking-wider mb-1">Source (Incoming)</p>
                <p className="text-xs text-gray-700">{conflict.sourceValue}</p>
              </div>
              <div className="rounded-lg bg-gray-50/60 border border-gray-200/40 px-3 py-2">
                <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Target (Repository)</p>
                <p className="text-xs text-gray-700">{conflict.targetValue}</p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => onResolve(conflict.id, 'keep_source')}
                disabled={isResolving}
                className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-blue-200/60 bg-blue-50/60 hover:bg-blue-100/60 text-blue-700 transition-all disabled:opacity-50"
              >
                {isResolving ? <ArrowPathIcon className="h-3.5 w-3.5 animate-spin" /> : <ArrowDownTrayIcon className="h-3.5 w-3.5" />}
                Use Source
              </button>
              <button
                onClick={() => onResolve(conflict.id, 'keep_target')}
                disabled={isResolving}
                className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-gray-200/60 bg-white/50 hover:bg-white/70 text-gray-700 transition-all disabled:opacity-50"
              >
                <ScaleIcon className="h-3.5 w-3.5" />
                Keep Target
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Progress Bar ──────────────────────────────────────────────────────────────

function SyncProgressBar({ systemName, onCancel }: { systemName: string; onCancel: () => void }) {
  return (
    <div className="rounded-xl border border-blue-200/60 bg-blue-50/40 px-4 py-3 flex items-center gap-4">
      <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-blue-800">Syncing {systemName}…</p>
        <div className="mt-1.5 h-1.5 bg-blue-100 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500 rounded-full animate-pulse" style={{ width: '60%' }} />
        </div>
      </div>
      <button
        onClick={onCancel}
        className="p-1 rounded-lg hover:bg-blue-100/60 text-blue-400 hover:text-blue-600 transition-colors flex-shrink-0"
        title="Cancel sync"
      >
        <XMarkIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function RepoSync() {
  const queryClient = useQueryClient();

  // UI state
  const [activeTab, setActiveTab] = useState<'configs' | 'history' | 'conflicts'>('configs');
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [syncingName, setSyncingName] = useState<string>('');
  const [configuringConfig, setConfiguringConfig] = useState<SyncConfig | null>(null);
  const [resolvingConflictId, setResolvingConflictId] = useState<string | null>(null);
  const [conflicts, setConflicts] = useState<SyncConflict[]>([]);
  const [historyFilter, setHistoryFilter] = useState('');

  // ── Data queries ────────────────────────────────────────────────────────────

  const { data: statsData } = useQuery<SyncStats>({
    queryKey: ['repo-sync-stats'],
    queryFn: async () => {
      try {
        const res = await api.get('/repo-sync/stats');
        return res.data;
      } catch {
        return null;
      }
    },
    staleTime: 30_000,
  });

  const { data: configsData, isLoading: configsLoading } = useQuery<SyncConfig[]>({
    queryKey: ['repo-sync-configs'],
    queryFn: async () => {
      try {
        const res = await api.get('/repo-sync/configs');
        return res.data?.configs ?? res.data ?? [];
      } catch {
        return [];
      }
    },
    staleTime: 30_000,
  });

  const { data: historyData, isLoading: historyLoading } = useQuery<SyncHistoryEntry[]>({
    queryKey: ['repo-sync-history'],
    queryFn: async () => {
      try {
        const res = await api.get('/repo-sync/history');
        return res.data?.history ?? res.data ?? [];
      } catch {
        return [];
      }
    },
    staleTime: 30_000,
  });

  const defaultStats: SyncStats = {
    connectedSystems: 0,
    lastSync: null,
    totalSyncedObjects: 0,
    syncHealthPct: 0,
    activeSyncs: 0,
    pendingConflicts: 0,
  };

  const stats = statsData ?? defaultStats;
  const configs = configsData ?? [];
  const history = historyData ?? [];

  // ── Mutations ───────────────────────────────────────────────────────────────

  const triggerSyncMutation = useMutation({
    mutationFn: async (systemId: string) => {
      await api.post(`/repo-sync/trigger/${systemId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repo-sync-history'] });
      queryClient.invalidateQueries({ queryKey: ['repo-sync-stats'] });
      queryClient.invalidateQueries({ queryKey: ['repo-sync-configs'] });
    },
  });

  const updateScheduleMutation = useMutation({
    mutationFn: async ({
      configId,
      scheduleMinutes,
      conflictResolution,
      syncUsers,
      syncRoles,
      syncGroups,
    }: {
      configId: string;
      scheduleMinutes: number;
      conflictResolution: ConflictResolution;
      syncUsers: boolean;
      syncRoles: boolean;
      syncGroups: boolean;
    }) => {
      await api.put(`/repo-sync/configs/${configId}/schedule`, {
        schedule_minutes: scheduleMinutes,
        conflict_resolution: conflictResolution,
        sync_users: syncUsers,
        sync_roles: syncRoles,
        sync_groups: syncGroups,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repo-sync-configs'] });
      setConfiguringConfig(null);
    },
    onError: () => {
      // Optimistically close in dev mode
      setConfiguringConfig(null);
    },
  });

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleSyncNow = async (config: SyncConfig) => {
    setSyncingId(config.id);
    setSyncingName(config.systemName);
    try {
      await triggerSyncMutation.mutateAsync(config.id);
    } catch {
      // Silently handle in dev
    } finally {
      setTimeout(() => {
        setSyncingId(null);
        setSyncingName('');
      }, 2000);
    }
  };

  const handlePauseToggle = async (config: SyncConfig) => {
    try {
      const action = config.status === 'paused' ? 'resume' : 'pause';
      await api.post(`/repo-sync/configs/${config.id}/${action}`);
      queryClient.invalidateQueries({ queryKey: ['repo-sync-configs'] });
    } catch {
      queryClient.invalidateQueries({ queryKey: ['repo-sync-configs'] });
    }
  };

  const handleSaveSchedule = (
    configId: string,
    scheduleMinutes: number,
    conflictResolution: ConflictResolution,
    syncUsers: boolean,
    syncRoles: boolean,
    syncGroups: boolean,
  ) => {
    updateScheduleMutation.mutate({ configId, scheduleMinutes, conflictResolution, syncUsers, syncRoles, syncGroups });
  };

  const handleResolveConflict = async (conflictId: string, resolution: 'keep_source' | 'keep_target') => {
    setResolvingConflictId(conflictId);
    try {
      await api.post(`/repo-sync/conflicts/${conflictId}/resolve`, { resolution });
    } catch {
      // Silently handle dev
    } finally {
      setTimeout(() => {
        setConflicts((prev) => prev.filter((c) => c.id !== conflictId));
        setResolvingConflictId(null);
      }, 800);
    }
  };

  // ── Filtered history ────────────────────────────────────────────────────────

  const filteredHistory = history.filter((h) => {
    if (!historyFilter) return true;
    if (historyFilter === 'success') return h.status === 'success';
    if (historyFilter === 'partial') return h.status === 'partial';
    if (historyFilter === 'failed') return h.status === 'failed';
    return h.systemName.toLowerCase().includes(historyFilter.toLowerCase());
  });

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Page header */}
      <PageHeader
        title="Repository Synchronization"
        subtitle="Manage scheduled sync of users, roles, and groups from connected identity systems"
        actions={
          <Button
            icon={<ArrowPathIcon className="h-4 w-4" />}
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ['repo-sync-stats'] });
              queryClient.invalidateQueries({ queryKey: ['repo-sync-configs'] });
              queryClient.invalidateQueries({ queryKey: ['repo-sync-history'] });
            }}
          >
            Refresh
          </Button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Connected Systems"
          value={stats.connectedSystems}
          icon={ServerIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Last Sync"
          value={formatRelativeTime(stats.lastSync)}
          icon={ClockIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
        <StatCard
          title="Total Synced Objects"
          value={stats.totalSyncedObjects.toLocaleString()}
          icon={CircleStackIcon}
          iconBgColor="stat-icon-purple"
          iconColor="text-purple-400"
        />
        <StatCard
          title="Sync Health"
          value={`${stats.syncHealthPct}%`}
          icon={ChartBarIcon}
          iconBgColor={stats.syncHealthPct >= 90 ? 'stat-icon-green' : stats.syncHealthPct >= 70 ? 'stat-icon-yellow' : 'stat-icon-red'}
          iconColor={stats.syncHealthPct >= 90 ? 'text-green-400' : stats.syncHealthPct >= 70 ? 'text-yellow-400' : 'text-red-400'}
        />
      </div>

      {/* Live sync progress banner */}
      {syncingId && (
        <SyncProgressBar
          systemName={syncingName}
          onCancel={() => { setSyncingId(null); setSyncingName(''); }}
        />
      )}

      {/* Conflict count alert */}
      {conflicts.length > 0 && (
        <div
          className="flex items-center gap-3 rounded-xl border border-amber-200/60 bg-amber-50/60 px-4 py-3 cursor-pointer hover:bg-amber-50/80 transition-colors"
          onClick={() => setActiveTab('conflicts')}
        >
          <ExclamationTriangleIcon className="h-5 w-5 text-amber-500 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-amber-800">
              {conflicts.length} sync conflict{conflicts.length !== 1 ? 's' : ''} pending resolution
            </p>
            <p className="text-xs text-amber-600 mt-0.5">
              Review and resolve attribute conflicts to keep your repository accurate.
            </p>
          </div>
          <Badge variant="warning">{conflicts.length}</Badge>
        </div>
      )}

      {/* Tab bar */}
      <div className="flex border-b border-white/30">
        {([
            { key: 'configs'   as const, label: 'Sync Configurations', icon: CogIcon,   badge: undefined as number | undefined },
            { key: 'history'   as const, label: 'Sync History',        icon: ClockIcon, badge: undefined as number | undefined },
            { key: 'conflicts' as const, label: 'Conflict Resolution',  icon: ScaleIcon, badge: conflicts.length as number | undefined },
          ] as const).map(({ key, label, icon: Icon, badge }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`inline-flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === key
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
            {badge !== undefined && badge > 0 && (
              <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold">
                {badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Tab: Sync Configurations ─────────────────────────────────────── */}
      {activeTab === 'configs' && (
        <Card padding="none">
          <CardHeader title="Sync Configurations" subtitle="Scheduled sync jobs per connected system" />
          {configsLoading ? (
            <LoadingState message="Loading sync configurations…" />
          ) : configs.length === 0 ? (
            <EmptyState
              icon={<ServerIcon className="h-8 w-8" />}
              title="No sync configurations"
              description="Add connected systems in System Management to configure repository sync."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-white/20">
                    {['System', 'Type', 'Status', 'Direction', 'Last Sync', 'Next Sync', 'Objects', 'Schedule', 'Actions'].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {configs.map((cfg) => {
                    const isSyncingThis = syncingId === cfg.id;
                    return (
                      <tr key={cfg.id} className="hover:bg-white/10 transition-colors group">
                        {/* System */}
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-gray-900 whitespace-nowrap">{cfg.systemName}</p>
                        </td>
                        {/* Type */}
                        <td className="px-4 py-3 whitespace-nowrap">
                          <SystemTypeChip type={cfg.systemType} />
                        </td>
                        {/* Status */}
                        <td className="px-4 py-3 whitespace-nowrap">
                          <SyncStatusDot status={isSyncingThis ? 'active' : cfg.status} />
                        </td>
                        {/* Direction */}
                        <td className="px-4 py-3 whitespace-nowrap">
                          <DirectionIcon direction={cfg.direction} />
                        </td>
                        {/* Last Sync */}
                        <td className="px-4 py-3">
                          <p className="text-xs text-gray-700 whitespace-nowrap">{formatRelativeTime(cfg.lastSync)}</p>
                          <p className="text-[10px] text-gray-400 whitespace-nowrap">{formatDateTime(cfg.lastSync)}</p>
                        </td>
                        {/* Next Sync */}
                        <td className="px-4 py-3">
                          {cfg.status === 'paused' ? (
                            <span className="text-xs text-amber-500 font-medium">Paused</span>
                          ) : cfg.status === 'error' ? (
                            <span className="text-xs text-red-500 font-medium">Stalled</span>
                          ) : (
                            <span className="text-xs text-gray-600 whitespace-nowrap">{formatFutureTime(cfg.nextSync)}</span>
                          )}
                        </td>
                        {/* Objects */}
                        <td className="px-4 py-3">
                          <span className="text-sm font-semibold text-gray-800">
                            {cfg.objectsSynced.toLocaleString()}
                          </span>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            {cfg.syncUsers  && <span className="text-[10px] text-blue-500 font-medium">Users</span>}
                            {cfg.syncRoles  && <span className="text-[10px] text-purple-500 font-medium">Roles</span>}
                            {cfg.syncGroups && <span className="text-[10px] text-indigo-500 font-medium">Groups</span>}
                          </div>
                        </td>
                        {/* Schedule */}
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-xs text-gray-600">{scheduleLabel(cfg.scheduleMinutes)}</span>
                        </td>
                        {/* Actions */}
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1 opacity-70 group-hover:opacity-100 transition-opacity">
                            {/* Sync Now */}
                            <button
                              onClick={() => handleSyncNow(cfg)}
                              disabled={isSyncingThis || !cfg.enabled || cfg.status === 'error'}
                              title="Sync now"
                              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-gray-200/60 bg-white/40 hover:bg-blue-50/60 hover:border-blue-200/60 hover:text-blue-700 text-gray-600 transition-all disabled:opacity-40 whitespace-nowrap"
                            >
                              {isSyncingThis ? (
                                <ArrowPathIcon className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <BoltIcon className="h-3.5 w-3.5" />
                              )}
                              Sync Now
                            </button>
                            {/* Pause / Resume */}
                            <button
                              onClick={() => handlePauseToggle(cfg)}
                              disabled={cfg.status === 'error'}
                              title={cfg.status === 'paused' ? 'Resume sync' : 'Pause sync'}
                              className="p-1.5 rounded-lg hover:bg-amber-50/60 hover:text-amber-600 text-gray-400 transition-colors disabled:opacity-40"
                            >
                              {cfg.status === 'paused' ? (
                                <PlayIcon className="h-4 w-4" />
                              ) : (
                                <PauseIcon className="h-4 w-4" />
                              )}
                            </button>
                            {/* Configure */}
                            <button
                              onClick={() => setConfiguringConfig(cfg)}
                              title="Configure schedule"
                              className="p-1.5 rounded-lg hover:bg-gray-100/60 hover:text-gray-700 text-gray-400 transition-colors"
                            >
                              <CogIcon className="h-4 w-4" />
                            </button>
                          </div>
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

      {/* ── Tab: Sync History ────────────────────────────────────────────── */}
      {activeTab === 'history' && (
        <Card padding="none">
          <CardHeader
            title="Sync History"
            subtitle="Log of all completed and failed sync runs across systems"
            action={
              <div className="w-44">
                <Select
                  value={historyFilter}
                  onChange={(e) => setHistoryFilter(e.target.value)}
                  options={[
                    { value: '',        label: 'All Results'  },
                    { value: 'success', label: 'Success only' },
                    { value: 'partial', label: 'Partial only' },
                    { value: 'failed',  label: 'Failed only'  },
                  ]}
                />
              </div>
            }
          />
          {historyLoading ? (
            <LoadingState message="Loading sync history…" />
          ) : filteredHistory.length === 0 ? (
            <EmptyState
              icon={<ClockIcon className="h-8 w-8" />}
              title="No history found"
              description="Sync history will appear here after the first scheduled or manual sync runs."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-white/20">
                    {['Timestamp', 'System', 'Direction', 'Objects Synced', 'Changes', 'Errors', 'Duration', 'Result'].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {filteredHistory.map((entry) => (
                    <tr key={entry.id} className={`hover:bg-white/10 transition-colors ${entry.status === 'failed' ? 'bg-red-50/20' : entry.status === 'partial' ? 'bg-amber-50/20' : ''}`}>
                      {/* Timestamp */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <p className="text-xs font-medium text-gray-700">{formatDateTime(entry.startedAt)}</p>
                        <p className="text-[10px] text-gray-400">{formatRelativeTime(entry.startedAt)}</p>
                      </td>
                      {/* System */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <SystemTypeChip type={entry.systemType} />
                          <span className="text-xs text-gray-600 truncate max-w-[120px]" title={entry.systemName}>
                            {entry.systemName}
                          </span>
                        </div>
                      </td>
                      {/* Direction */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <DirectionIcon direction={entry.direction} />
                      </td>
                      {/* Objects */}
                      <td className="px-4 py-3">
                        <span className="text-sm font-semibold text-gray-800">
                          {entry.objectsSynced.toLocaleString()}
                        </span>
                      </td>
                      {/* Changes */}
                      <td className="px-4 py-3">
                        <div className="text-xs text-gray-600 whitespace-nowrap">
                          <span className="text-blue-600 font-medium">{entry.usersChanged}</span> users,{' '}
                          <span className="text-purple-600 font-medium">{entry.rolesChanged}</span> roles
                        </div>
                      </td>
                      {/* Errors */}
                      <td className="px-4 py-3">
                        {entry.errors > 0 ? (
                          <div>
                            <span className="text-sm font-semibold text-red-600">{entry.errors}</span>
                            {entry.errorDetails && (
                              <p className="text-[10px] text-red-500 mt-0.5 max-w-[160px] truncate" title={entry.errorDetails}>
                                {entry.errorDetails}
                              </p>
                            )}
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400">0</span>
                        )}
                      </td>
                      {/* Duration */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-xs text-gray-600 inline-flex items-center gap-1">
                          <ClockIcon className="h-3 w-3" />
                          {formatDuration(entry.durationSeconds)}
                        </span>
                      </td>
                      {/* Result */}
                      <td className="px-4 py-3">
                        <ResultBadge status={entry.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!historyLoading && filteredHistory.length > 0 && (
            <div className="px-4 py-3 border-t border-white/20">
              <p className="text-xs text-gray-400">
                Showing {filteredHistory.length} of {history.length} sync run{history.length !== 1 ? 's' : ''}
              </p>
            </div>
          )}
        </Card>
      )}

      {/* ── Tab: Conflict Resolution ─────────────────────────────────────── */}
      {activeTab === 'conflicts' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Conflicts list */}
          <div className="lg:col-span-2">
            <Card padding="none">
              <CardHeader
                title="Pending Conflicts"
                subtitle="Objects where source and repository values diverged during sync"
              />
              <CardBody>
                <ConflictPanel
                  conflicts={conflicts}
                  onResolve={handleResolveConflict}
                  resolvingId={resolvingConflictId}
                />
              </CardBody>
            </Card>
          </div>

          {/* Resolution guide */}
          <div className="space-y-4">
            <Card padding="md">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Resolution Strategies
              </p>
              <dl className="space-y-3">
                {[
                  { term: 'Use Source', def: 'Overwrites the repository value with the incoming system value.', color: 'text-blue-600' },
                  { term: 'Keep Target', def: 'Ignores the incoming change and preserves the existing repository value.', color: 'text-gray-600' },
                  { term: 'Newest Wins', def: 'Automatically picks the most recently modified attribute (set globally per system).', color: 'text-purple-600' },
                  { term: 'Manual', def: 'Queues the conflict for review — no change is applied until you decide.', color: 'text-amber-600' },
                ].map(({ term, def, color }) => (
                  <div key={term}>
                    <dt className={`text-xs font-semibold ${color}`}>{term}</dt>
                    <dd className="text-xs text-gray-500 mt-0.5 leading-relaxed">{def}</dd>
                  </div>
                ))}
              </dl>
            </Card>

            <Card padding="md">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Conflict Summary
              </p>
              <div className="space-y-2">
                {(['user', 'role', 'group'] as const).map((type) => {
                  const count = conflicts.filter((c) => c.objectType === type).length;
                  const Icon = type === 'user' ? UserGroupIcon : type === 'role' ? ShieldCheckIcon : CircleStackIcon;
                  const color = type === 'user' ? 'text-blue-500' : type === 'role' ? 'text-purple-500' : 'text-indigo-500';
                  return (
                    <div key={type} className="flex items-center justify-between">
                      <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${color}`}>
                        <Icon className="h-3.5 w-3.5" />
                        {type.charAt(0).toUpperCase() + type.slice(1)}s
                      </span>
                      <span className={`text-xs font-bold ${count > 0 ? 'text-amber-600' : 'text-gray-400'}`}>
                        {count}
                      </span>
                    </div>
                  );
                })}
              </div>
              {conflicts.length > 0 && (
                <button
                  onClick={() => {
                    conflicts.forEach((c) => handleResolveConflict(c.id, 'keep_source'));
                  }}
                  className="mt-4 w-full inline-flex items-center justify-center gap-1.5 px-3 py-2.5 text-xs font-semibold rounded-xl border border-red-200/60 bg-red-50/60 hover:bg-red-100/60 text-red-700 transition-all"
                >
                  <ArrowDownTrayIcon className="h-3.5 w-3.5" />
                  Resolve All — Use Source
                </button>
              )}
            </Card>
          </div>
        </div>
      )}

      {/* Schedule / Configure modal */}
      {configuringConfig && (
        <ScheduleModal
          config={configuringConfig}
          open={true}
          onClose={() => setConfiguringConfig(null)}
          onSave={handleSaveSchedule}
          isSaving={updateScheduleMutation.isPending}
        />
      )}
    </div>
  );
}
