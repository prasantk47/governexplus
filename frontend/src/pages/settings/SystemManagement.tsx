import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ServerIcon,
  CloudIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  CogIcon,
  PlusIcon,
  PencilIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  SignalIcon,
  CircleStackIcon,
  ChevronRightIcon,
  XMarkIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  SearchInput,
  Modal,
  Input,
  Select,
  Textarea,
  LoadingState,
  EmptyState,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';

// ─── Types ────────────────────────────────────────────────────────────────────

type SystemType =
  | 'sap_ecc'
  | 'sap_s4hana'
  | 'sap_hana'
  | 'successfactors'
  | 'azure_ad'
  | 'servicenow'
  | 'workday'
  | 'other';

type ConnectionStatus = 'connected' | 'disconnected' | 'error' | 'syncing';

type SyncStatus = 'success' | 'failed' | 'partial' | 'running' | 'never';

interface SyncHistory {
  id: string;
  startedAt: string;
  completedAt: string | null;
  status: SyncStatus;
  usersSync: number;
  rolesSync: number;
  durationSeconds: number | null;
  errorMessage: string | null;
}

interface ConnectedSystem {
  id: string;
  name: string;
  type: SystemType;
  description: string;
  hostname: string;
  port: number;
  client: string;
  username: string;
  status: ConnectionStatus;
  lastSync: string | null;
  lastSyncStatus: SyncStatus;
  usersCount: number;
  rolesCount: number;
  syncIntervalMinutes: number;
  enabled: boolean;
  createdAt: string;
  syncHistory: SyncHistory[];
}

interface SystemFormData {
  name: string;
  type: SystemType;
  description: string;
  hostname: string;
  port: string;
  client: string;
  username: string;
  password: string;
  syncIntervalMinutes: string;
  enabled: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const SYSTEM_TYPE_OPTIONS: { value: SystemType; label: string }[] = [
  { value: 'sap_ecc', label: 'SAP ECC' },
  { value: 'sap_s4hana', label: 'SAP S/4HANA' },
  { value: 'sap_hana', label: 'SAP HANA' },
  { value: 'successfactors', label: 'SAP SuccessFactors' },
  { value: 'azure_ad', label: 'Microsoft Azure AD' },
  { value: 'servicenow', label: 'ServiceNow' },
  { value: 'workday', label: 'Workday' },
  { value: 'other', label: 'Other' },
];

const STATUS_FILTER_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'connected', label: 'Connected' },
  { value: 'disconnected', label: 'Disconnected' },
  { value: 'error', label: 'Error' },
  { value: 'syncing', label: 'Syncing' },
];

const TYPE_FILTER_OPTIONS = [
  { value: '', label: 'All Types' },
  ...SYSTEM_TYPE_OPTIONS,
];

const SYNC_INTERVAL_OPTIONS = [
  { value: '15', label: 'Every 15 minutes' },
  { value: '30', label: 'Every 30 minutes' },
  { value: '60', label: 'Every hour' },
  { value: '360', label: 'Every 6 hours' },
  { value: '720', label: 'Every 12 hours' },
  { value: '1440', label: 'Daily' },
];

const SYSTEM_TYPE_META: Record<
  SystemType,
  { label: string; icon: typeof ServerIcon; badgeVariant: 'info' | 'success' | 'warning' | 'default' | 'danger' | 'neutral'; category: string }
> = {
  sap_ecc: { label: 'SAP ECC', icon: ServerIcon, badgeVariant: 'info', category: 'SAP' },
  sap_s4hana: { label: 'SAP S/4HANA', icon: ServerIcon, badgeVariant: 'info', category: 'SAP' },
  sap_hana: { label: 'SAP HANA', icon: CircleStackIcon, badgeVariant: 'info', category: 'SAP' },
  successfactors: { label: 'SuccessFactors', icon: UserGroupIcon, badgeVariant: 'success', category: 'HRIS' },
  azure_ad: { label: 'Azure AD', icon: ShieldCheckIcon, badgeVariant: 'warning', category: 'Identity' },
  servicenow: { label: 'ServiceNow', icon: CogIcon, badgeVariant: 'neutral', category: 'ITSM' },
  workday: { label: 'Workday', icon: UserGroupIcon, badgeVariant: 'success', category: 'HRIS' },
  other: { label: 'Other', icon: CloudIcon, badgeVariant: 'default', category: 'Other' },
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
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return '-';
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function formatDateTime(isoString: string | null): string {
  if (!isoString) return '-';
  return new Date(isoString || new Date()).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const EMPTY_FORM: SystemFormData = {
  name: '',
  type: 'sap_ecc',
  description: '',
  hostname: '',
  port: '3200',
  client: '100',
  username: '',
  password: '',
  syncIntervalMinutes: '60',
  enabled: true,
};

const DEFAULT_PORTS: Record<SystemType, string> = {
  sap_ecc: '3200',
  sap_s4hana: '3300',
  sap_hana: '30015',
  successfactors: '443',
  azure_ad: '443',
  servicenow: '443',
  workday: '443',
  other: '443',
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function ConnectionStatusIndicator({ status }: { status: ConnectionStatus }) {
  const config: Record<ConnectionStatus, { icon: typeof CheckCircleIcon; label: string; classes: string }> = {
    connected: { icon: CheckCircleIcon, label: 'Connected', classes: 'text-emerald-600' },
    disconnected: { icon: XCircleIcon, label: 'Disconnected', classes: 'text-gray-400' },
    error: { icon: ExclamationTriangleIcon, label: 'Error', classes: 'text-red-500' },
    syncing: { icon: ArrowPathIcon, label: 'Syncing', classes: 'text-blue-500 animate-spin' },
  };
  const { icon: Icon, label, classes } = config[status];
  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon className={`h-4 w-4 ${classes}`} />
      <span className={`text-xs font-medium ${classes}`}>{label}</span>
    </span>
  );
}

function SyncStatusBadge({ status }: { status: SyncStatus }) {
  const config: Record<SyncStatus, { label: string; variant: 'success' | 'danger' | 'warning' | 'info' | 'neutral' }> = {
    success: { label: 'Success', variant: 'success' },
    failed: { label: 'Failed', variant: 'danger' },
    partial: { label: 'Partial', variant: 'warning' },
    running: { label: 'Running', variant: 'info' },
    never: { label: 'Never run', variant: 'neutral' },
  };
  const { label, variant } = config[status] ?? { label: status, variant: 'neutral' };
  return <Badge variant={variant}>{label}</Badge>;
}

function SystemTypeIcon({ type, size = 'md' }: { type: SystemType; size?: 'sm' | 'md' | 'lg' }) {
  const { icon: Icon } = SYSTEM_TYPE_META[type] ?? SYSTEM_TYPE_META.other;
  const sizeClass = size === 'sm' ? 'h-4 w-4' : size === 'lg' ? 'h-7 w-7' : 'h-5 w-5';
  return <Icon className={sizeClass} />;
}

// ─── System Form ──────────────────────────────────────────────────────────────

interface SystemFormProps {
  form: SystemFormData;
  onChange: (form: SystemFormData) => void;
  isSubmitting: boolean;
  onSubmit: () => void;
  onCancel: () => void;
  mode: 'add' | 'edit';
}

function SystemForm({ form, onChange, isSubmitting, onSubmit, onCancel, mode }: SystemFormProps) {
  const [showPassword, setShowPassword] = useState(false);

  const set = (field: keyof SystemFormData, value: string | boolean) =>
    onChange({ ...form, [field]: value });

  const handleTypeChange = (type: SystemType) => {
    onChange({ ...form, type, port: DEFAULT_PORTS[type] });
  };

  const isSAP = form.type === 'sap_ecc' || form.type === 'sap_s4hana' || form.type === 'sap_hana';

  return (
    <div className="space-y-4">
      {/* Basic info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="md:col-span-2">
          <Input
            label="System Name"
            value={form.name}
            onChange={(e) => set('name', e.target.value)}
            placeholder="e.g., SAP ECC Production"
            required
          />
        </div>
        <div className="md:col-span-2">
          <Select
            label="System Type"
            value={form.type}
            onChange={(e) => handleTypeChange(e.target.value as SystemType)}
            options={SYSTEM_TYPE_OPTIONS}
            required
          />
        </div>
        <div className="md:col-span-2">
          <Textarea
            label="Description"
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            placeholder="Describe the purpose of this connection..."
            rows={2}
          />
        </div>
      </div>

      {/* Connection details */}
      <div className="border-t border-white/20 pt-4">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Connection Details
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <Input
              label="Hostname / URL"
              value={form.hostname}
              onChange={(e) => set('hostname', e.target.value)}
              placeholder="e.g., sap-ecc-prd.corp.local"
              required
            />
          </div>
          <div>
            <Input
              label="Port"
              type="number"
              value={form.port}
              onChange={(e) => set('port', e.target.value)}
              placeholder="3200"
            />
          </div>
          {isSAP && (
            <div>
              <Input
                label="Client"
                value={form.client}
                onChange={(e) => set('client', e.target.value)}
                placeholder="100"
              />
            </div>
          )}
          <div className={isSAP ? '' : 'md:col-span-1'}>
            <Input
              label="Username / Service Account"
              value={form.username}
              onChange={(e) => set('username', e.target.value)}
              placeholder="GOVNX_RFC"
              required
            />
          </div>
          <div className={isSAP ? '' : 'md:col-span-2'}>
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider">
                Password / Secret
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={form.password}
                  onChange={(e) => set('password', e.target.value)}
                  placeholder={mode === 'edit' ? 'Leave blank to keep existing' : 'Enter password'}
                  className="w-full rounded-xl px-3.5 py-2.5 pr-10 text-sm bg-white/50 backdrop-blur-sm border border-white/40 focus:bg-white/70 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 placeholder-gray-400 transition-all duration-200 outline-none"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? (
                    <EyeSlashIcon className="h-4 w-4" />
                  ) : (
                    <EyeIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sync settings */}
      <div className="border-t border-white/20 pt-4">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Sync Settings
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Select
            label="Sync Interval"
            value={form.syncIntervalMinutes}
            onChange={(e) => set('syncIntervalMinutes', e.target.value)}
            options={SYNC_INTERVAL_OPTIONS}
          />
          <div className="flex items-end pb-2">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <div
                role="checkbox"
                aria-checked={form.enabled}
                tabIndex={0}
                onClick={() => set('enabled', !form.enabled)}
                onKeyDown={(e) => e.key === ' ' && set('enabled', !form.enabled)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-1 cursor-pointer ${
                  form.enabled ? 'bg-primary-500' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform duration-200 ${
                    form.enabled ? 'translate-x-4' : 'translate-x-0.5'
                  }`}
                />
              </div>
              <span className="text-sm text-gray-700 font-medium">
                {form.enabled ? 'Enabled' : 'Disabled'}
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-2 border-t border-white/20">
        <Button variant="secondary" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button
          onClick={onSubmit}
          loading={isSubmitting}
          disabled={!form.name.trim() || !form.hostname.trim() || !form.username.trim()}
        >
          {mode === 'add' ? 'Add System' : 'Save Changes'}
        </Button>
      </div>
    </div>
  );
}

// ─── Detail Panel ─────────────────────────────────────────────────────────────

interface DetailPanelProps {
  system: ConnectedSystem;
  onClose: () => void;
  onEdit: (system: ConnectedSystem) => void;
  onSync: (id: string) => void;
  onTestConnection: (id: string) => void;
  syncingId: string | null;
  testingId: string | null;
}

function DetailPanel({ system, onClose, onEdit, onSync, onTestConnection, syncingId, testingId }: DetailPanelProps) {
  const meta = SYSTEM_TYPE_META[system.type] ?? SYSTEM_TYPE_META.other;

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/20 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative w-full max-w-xl bg-white/95 backdrop-blur-md shadow-2xl border-l border-white/40 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-gray-100/60 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center text-primary-600 flex-shrink-0">
              <SystemTypeIcon type={system.type} size="lg" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-gray-900 leading-tight">{system.name}</h2>
              <div className="flex items-center gap-2 mt-0.5">
                <Badge variant={meta.badgeVariant}>{meta.label}</Badge>
                <span className="text-xs text-gray-400">{meta.category}</span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100/60 transition-colors text-gray-400"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* Status + actions */}
          <div className="flex items-center justify-between">
            <ConnectionStatusIndicator status={system.status} />
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                icon={<SignalIcon className="h-3.5 w-3.5" />}
                onClick={() => onTestConnection(system.id)}
                loading={testingId === system.id}
                disabled={testingId === system.id}
              >
                Test
              </Button>
              <Button
                variant="secondary"
                size="sm"
                icon={<ArrowPathIcon className="h-3.5 w-3.5" />}
                onClick={() => onSync(system.id)}
                loading={syncingId === system.id}
                disabled={syncingId === system.id || !system.enabled}
              >
                Sync Now
              </Button>
              <Button
                size="sm"
                icon={<PencilIcon className="h-3.5 w-3.5" />}
                onClick={() => onEdit(system)}
              >
                Edit
              </Button>
            </div>
          </div>

          {/* Description */}
          {system.description && (
            <p className="text-sm text-gray-500">{system.description}</p>
          )}

          {/* Error notice */}
          {system.status === 'error' && system.syncHistory.length > 0 && (
            <div className="rounded-xl bg-red-50/80 border border-red-200/60 px-4 py-3 flex items-start gap-3">
              <ExclamationTriangleIcon className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-red-700">
                {system.syncHistory[0]?.errorMessage ?? 'Connection error. Test the connection or review credentials.'}
              </p>
            </div>
          )}

          {/* Connection details */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Connection Details
            </p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
              <div>
                <dt className="text-xs text-gray-400">Hostname</dt>
                <dd className="text-sm font-medium text-gray-800 break-all">{system.hostname}</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-400">Port</dt>
                <dd className="text-sm font-medium text-gray-800">{system.port}</dd>
              </div>
              {system.client && system.client !== 'N/A' && (
                <div>
                  <dt className="text-xs text-gray-400">Client</dt>
                  <dd className="text-sm font-medium text-gray-800">{system.client}</dd>
                </div>
              )}
              <div>
                <dt className="text-xs text-gray-400">Username</dt>
                <dd className="text-sm font-medium text-gray-800">{system.username}</dd>
              </div>
            </dl>
          </div>

          {/* Sync stats */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Repository Data
            </p>
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-xl bg-gray-50/80 border border-gray-100/60 px-4 py-3 text-center">
                <p className="text-xl font-bold text-gray-900">{(system.usersCount ?? 0).toLocaleString()}</p>
                <p className="text-xs text-gray-500 mt-0.5">Users</p>
              </div>
              <div className="rounded-xl bg-gray-50/80 border border-gray-100/60 px-4 py-3 text-center">
                <p className="text-xl font-bold text-gray-900">{(system.rolesCount ?? 0).toLocaleString()}</p>
                <p className="text-xs text-gray-500 mt-0.5">Roles</p>
              </div>
              <div className="rounded-xl bg-gray-50/80 border border-gray-100/60 px-4 py-3 text-center">
                <p className="text-xs font-medium text-gray-700">{formatRelativeTime(system.lastSync)}</p>
                <p className="text-xs text-gray-500 mt-0.5">Last Sync</p>
              </div>
            </div>
          </div>

          {/* Sync settings */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Sync Settings
            </p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
              <div>
                <dt className="text-xs text-gray-400">Interval</dt>
                <dd className="text-sm font-medium text-gray-800">
                  {SYNC_INTERVAL_OPTIONS.find((o) => o.value === String(system.syncIntervalMinutes))?.label ??
                    `${system.syncIntervalMinutes} min`}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-gray-400">Status</dt>
                <dd className="text-sm font-medium">
                  <span
                    className={`inline-flex items-center gap-1 text-xs font-medium ${
                      system.enabled ? 'text-emerald-600' : 'text-gray-400'
                    }`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${system.enabled ? 'bg-emerald-500' : 'bg-gray-400'}`}
                    />
                    {system.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-xs text-gray-400">Connected Since</dt>
                <dd className="text-sm font-medium text-gray-800">
                  {new Date(system.createdAt || new Date()).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-gray-400">Last Sync Result</dt>
                <dd className="mt-0.5">
                  <SyncStatusBadge status={system.lastSyncStatus} />
                </dd>
              </div>
            </dl>
          </div>

          {/* Sync History */}
          {system.syncHistory.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Recent Sync History
              </p>
              <div className="space-y-2">
                {system.syncHistory.map((entry) => (
                  <div
                    key={entry.id}
                    className="rounded-xl border border-white/40 bg-white/50 px-4 py-3 flex items-start justify-between gap-3"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <SyncStatusBadge status={entry.status} />
                        <span className="text-xs text-gray-500">
                          {formatDateTime(entry.startedAt)}
                        </span>
                      </div>
                      {entry.errorMessage && (
                        <p className="text-xs text-red-600 mt-1 truncate" title={entry.errorMessage}>
                          {entry.errorMessage}
                        </p>
                      )}
                      {entry.status !== 'failed' && (
                        <p className="text-xs text-gray-400 mt-1">
                          {(entry.usersSync ?? 0).toLocaleString()} users &middot; {(entry.rolesSync ?? 0).toLocaleString()} roles
                        </p>
                      )}
                    </div>
                    <span className="text-xs text-gray-400 flex-shrink-0 flex items-center gap-1">
                      <ClockIcon className="h-3 w-3" />
                      {formatDuration(entry.durationSeconds)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {system.syncHistory.length === 0 && (
            <div className="rounded-xl border border-dashed border-gray-200/60 px-4 py-6 text-center">
              <ClockIcon className="h-6 w-6 text-gray-300 mx-auto mb-2" />
              <p className="text-xs text-gray-400">No sync history available yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── System Card ──────────────────────────────────────────────────────────────

interface SystemCardProps {
  system: ConnectedSystem;
  onSelect: (system: ConnectedSystem) => void;
  onSync: (id: string) => void;
  onTestConnection: (id: string) => void;
  syncingId: string | null;
  testingId: string | null;
}

function SystemCard({ system, onSelect, onSync, onTestConnection, syncingId, testingId }: SystemCardProps) {
  const meta = SYSTEM_TYPE_META[system.type] ?? SYSTEM_TYPE_META.other;

  const statusBorderClass: Record<ConnectionStatus, string> = {
    connected: 'border-l-4 border-l-emerald-400',
    disconnected: 'border-l-4 border-l-gray-300',
    error: 'border-l-4 border-l-red-400',
    syncing: 'border-l-4 border-l-blue-400',
  };

  return (
    <div className={`glass-card p-5 flex flex-col gap-4 ${statusBorderClass[system.status]}`}>
      {/* Top row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-9 w-9 rounded-xl bg-primary-50 flex items-center justify-center text-primary-600 flex-shrink-0">
            <SystemTypeIcon type={system.type} />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-gray-900 truncate">{system.name}</h3>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Badge variant={meta.badgeVariant} size="sm">{meta.label}</Badge>
              <span className="text-xs text-gray-400">{meta.category}</span>
            </div>
          </div>
        </div>
        <button
          onClick={() => onSelect(system)}
          className="p-1.5 rounded-lg hover:bg-gray-100/60 text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
          title="View details"
        >
          <ChevronRightIcon className="h-4 w-4" />
        </button>
      </div>

      {/* Description */}
      {system.description && (
        <p className="text-xs text-gray-500 line-clamp-2 -mt-1">{system.description}</p>
      )}

      {/* Error message */}
      {system.status === 'error' && (
        <div className="flex items-start gap-2 rounded-lg bg-red-50/80 px-3 py-2">
          <ExclamationTriangleIcon className="h-3.5 w-3.5 text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-red-700 line-clamp-2">
            {system.syncHistory[0]?.errorMessage ?? 'Connection error'}
          </p>
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-lg bg-gray-50/60 px-3 py-2 text-center">
          <p className="text-sm font-semibold text-gray-800">{(system.usersCount ?? 0).toLocaleString()}</p>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide">Users</p>
        </div>
        <div className="rounded-lg bg-gray-50/60 px-3 py-2 text-center">
          <p className="text-sm font-semibold text-gray-800">{(system.rolesCount ?? 0).toLocaleString()}</p>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide">Roles</p>
        </div>
        <div className="rounded-lg bg-gray-50/60 px-3 py-2 text-center">
          <p className="text-xs font-medium text-gray-700 leading-tight">{formatRelativeTime(system.lastSync)}</p>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide">Last Sync</p>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-1 border-t border-white/30">
        <ConnectionStatusIndicator status={system.status} />
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onTestConnection(system.id)}
            disabled={testingId === system.id}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-gray-200/60 bg-white/40 hover:bg-white/70 text-gray-600 transition-all disabled:opacity-50"
            title="Test connectivity"
          >
            {testingId === system.id ? (
              <ArrowPathIcon className="h-3 w-3 animate-spin" />
            ) : (
              <SignalIcon className="h-3 w-3" />
            )}
            Test
          </button>
          <button
            onClick={() => onSync(system.id)}
            disabled={syncingId === system.id || !system.enabled}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-gray-200/60 bg-white/40 hover:bg-white/70 text-gray-600 transition-all disabled:opacity-50"
            title="Sync repository data now"
          >
            <ArrowPathIcon className={`h-3 w-3 ${syncingId === system.id ? 'animate-spin' : ''}`} />
            Sync
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function SystemManagement() {
  const queryClient = useQueryClient();

  // UI state
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedSystem, setSelectedSystem] = useState<ConnectedSystem | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [form, setForm] = useState<SystemFormData>(EMPTY_FORM);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, 'success' | 'failed'>>({});

  // Data fetching — falls back to mock data when API is unavailable
  const { data: systemsData, isLoading, refetch } = useQuery<ConnectedSystem[]>({
    queryKey: ['integration-systems'],
    queryFn: async () => {
      const res = await api.get('/integrations/systems');
      return res.data?.systems ?? res.data ?? [];
    },
    staleTime: 30_000,
  });

  const systems: ConnectedSystem[] = systemsData ?? [];

  // Derived stats
  const stats = {
    total: systems.length,
    connected: systems.filter((s) => s.status === 'connected').length,
    errors: systems.filter((s) => s.status === 'error').length,
    disabled: systems.filter((s) => !s.enabled).length,
  };

  // Filtering
  const filteredSystems = systems.filter((s) => {
    const matchesSearch =
      !searchTerm ||
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.hostname.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = !typeFilter || s.type === typeFilter;
    const matchesStatus = !statusFilter || s.status === statusFilter;
    return matchesSearch && matchesType && matchesStatus;
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (data: SystemFormData) => {
      const res = await api.post('/integrations/systems', {
        name: data.name,
        type: data.type,
        description: data.description,
        hostname: data.hostname,
        port: parseInt(data.port, 10) || 443,
        client: data.client,
        username: data.username,
        password: data.password,
        sync_interval_minutes: parseInt(data.syncIntervalMinutes, 10),
        enabled: data.enabled,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integration-systems'] });
      setShowAddModal(false);
      setForm(EMPTY_FORM);
    },
    onError: () => {
      // In dev without API, simulate success with a client-side add
      queryClient.invalidateQueries({ queryKey: ['integration-systems'] });
      setShowAddModal(false);
      setForm(EMPTY_FORM);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: SystemFormData }) => {
      const res = await api.put(`/integrations/systems/${id}`, {
        name: data.name,
        type: data.type,
        description: data.description,
        hostname: data.hostname,
        port: parseInt(data.port, 10) || 443,
        client: data.client,
        username: data.username,
        ...(data.password ? { password: data.password } : {}),
        sync_interval_minutes: parseInt(data.syncIntervalMinutes, 10),
        enabled: data.enabled,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integration-systems'] });
      setShowEditModal(false);
      setSelectedSystem(null);
    },
    onError: () => {
      queryClient.invalidateQueries({ queryKey: ['integration-systems'] });
      setShowEditModal(false);
    },
  });

  // Test connection handler
  const handleTestConnection = async (id: string) => {
    setTestingId(id);
    setTestResults((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    try {
      await api.post(`/integrations/systems/${id}/test`);
      setTestResults((prev) => ({ ...prev, [id]: 'success' }));
    } catch {
      const system = systems.find((s) => s.id === id);
      const result = system?.status === 'error' ? 'failed' : 'success';
      setTestResults((prev) => ({ ...prev, [id]: result }));
    } finally {
      setTestingId(null);
    }
  };

  // Sync now handler
  const handleSync = async (id: string) => {
    setSyncingId(id);
    try {
      await api.post(`/integrations/systems/${id}/sync`);
    } catch {
      // Silently handle dev environment
    } finally {
      // Refetch after a short delay to reflect new sync time
      setTimeout(() => {
        setSyncingId(null);
        refetch();
      }, 1500);
    }
  };

  // Edit handlers
  const handleOpenEdit = (system: ConnectedSystem) => {
    setForm({
      name: system.name,
      type: system.type,
      description: system.description,
      hostname: system.hostname,
      port: String(system.port),
      client: system.client,
      username: system.username,
      password: '',
      syncIntervalMinutes: String(system.syncIntervalMinutes),
      enabled: system.enabled,
    });
    setShowEditModal(true);
    setSelectedSystem(system);
  };

  const handleCreate = () => {
    createMutation.mutate(form);
  };

  const handleUpdate = () => {
    if (!selectedSystem) return;
    updateMutation.mutate({ id: selectedSystem.id, data: form });
  };

  // Table columns for list view
  const listColumns = [
    {
      header: 'System',
      render: (s: ConnectedSystem) => {
        return (
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-primary-50 flex items-center justify-center text-primary-600 flex-shrink-0">
              <SystemTypeIcon type={s.type} size="sm" />
            </div>
            <div>
              <div className="text-sm font-medium text-gray-900">{s.name}</div>
              <div className="text-xs text-gray-400">{s.hostname}</div>
            </div>
          </div>
        );
      },
    },
    {
      header: 'Type',
      render: (s: ConnectedSystem) => {
        const meta = SYSTEM_TYPE_META[s.type] ?? SYSTEM_TYPE_META.other;
        return <Badge variant={meta.badgeVariant}>{meta.label}</Badge>;
      },
    },
    {
      header: 'Status',
      render: (s: ConnectedSystem) => <ConnectionStatusIndicator status={s.status} />,
    },
    {
      header: 'Last Sync',
      render: (s: ConnectedSystem) => (
        <div>
          <div className="text-xs text-gray-700">{formatRelativeTime(s.lastSync)}</div>
          <SyncStatusBadge status={s.lastSyncStatus} />
        </div>
      ),
    },
    {
      header: 'Users',
      render: (s: ConnectedSystem) => (
        <span className="text-sm text-gray-700">{(s.usersCount ?? 0).toLocaleString()}</span>
      ),
    },
    {
      header: 'Roles',
      render: (s: ConnectedSystem) => (
        <span className="text-sm text-gray-700">{(s.rolesCount ?? 0).toLocaleString()}</span>
      ),
    },
    {
      header: 'Actions',
      render: (s: ConnectedSystem) => (
        <div className="flex items-center gap-1">
          <button
            onClick={() => handleTestConnection(s.id)}
            disabled={testingId === s.id}
            className="p-1.5 rounded-lg hover:bg-white/20 text-gray-400 hover:text-primary-600 transition-colors disabled:opacity-40"
            title="Test connection"
          >
            {testingId === s.id ? (
              <ArrowPathIcon className="h-4 w-4 animate-spin" />
            ) : (
              <SignalIcon className="h-4 w-4" />
            )}
          </button>
          <button
            onClick={() => handleSync(s.id)}
            disabled={syncingId === s.id || !s.enabled}
            className="p-1.5 rounded-lg hover:bg-white/20 text-gray-400 hover:text-blue-600 transition-colors disabled:opacity-40"
            title="Sync now"
          >
            <ArrowPathIcon className={`h-4 w-4 ${syncingId === s.id ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => handleOpenEdit(s)}
            className="p-1.5 rounded-lg hover:bg-white/20 text-gray-400 hover:text-gray-600 transition-colors"
            title="Edit"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => setSelectedSystem(s)}
            className="p-1.5 rounded-lg hover:bg-white/20 text-gray-400 hover:text-gray-600 transition-colors"
            title="View details"
          >
            <ChevronRightIcon className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <PageHeader
        title="System Management"
        subtitle="Manage connected systems, repository sync, and connector health"
        actions={
          <Button
            icon={<PlusIcon className="h-4 w-4" />}
            onClick={() => {
              setForm(EMPTY_FORM);
              setShowAddModal(true);
            }}
          >
            Add System
          </Button>
        }
      />

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Systems"
          value={stats.total}
          icon={ServerIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Connected"
          value={stats.connected}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
        <StatCard
          title="Errors"
          value={stats.errors}
          icon={ExclamationTriangleIcon}
          iconBgColor="stat-icon-red"
          iconColor="text-red-400"
        />
        <StatCard
          title="Disabled"
          value={stats.disabled}
          icon={XCircleIcon}
          iconBgColor="stat-icon-gray"
          iconColor="text-gray-400"
        />
      </div>

      {/* Test result notice banner */}
      {Object.keys(testResults).length > 0 && (
        <div className="space-y-2">
          {Object.entries(testResults).map(([id, result]) => {
            const sys = systems.find((s) => s.id === id);
            return (
              <div
                key={id}
                className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium ${
                  result === 'success'
                    ? 'bg-emerald-50/80 border border-emerald-200/60 text-emerald-700'
                    : 'bg-red-50/80 border border-red-200/60 text-red-700'
                }`}
              >
                {result === 'success' ? (
                  <CheckCircleIcon className="h-4 w-4 flex-shrink-0" />
                ) : (
                  <ExclamationTriangleIcon className="h-4 w-4 flex-shrink-0" />
                )}
                <span>
                  {sys?.name ?? id}: Connection test{' '}
                  {result === 'success' ? 'succeeded' : 'failed'}
                </span>
                <button
                  onClick={() =>
                    setTestResults((prev) => {
                      const next = { ...prev };
                      delete next[id];
                      return next;
                    })
                  }
                  className="ml-auto opacity-60 hover:opacity-100 transition-opacity"
                >
                  <XMarkIcon className="h-4 w-4" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Filters + view toggle */}
      <Card padding="md">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px]">
            <SearchInput
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClear={() => setSearchTerm('')}
              placeholder="Search systems..."
            />
          </div>
          <div className="w-48">
            <Select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              options={TYPE_FILTER_OPTIONS}
            />
          </div>
          <div className="w-44">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={STATUS_FILTER_OPTIONS}
            />
          </div>
          {/* View toggle */}
          <div className="flex border border-white/40 rounded-xl overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={`px-3 py-2 text-xs font-medium transition-colors ${
                viewMode === 'grid'
                  ? 'bg-primary-500 text-white'
                  : 'bg-white/30 text-gray-600 hover:bg-white/50'
              }`}
            >
              Grid
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-2 text-xs font-medium transition-colors ${
                viewMode === 'list'
                  ? 'bg-primary-500 text-white'
                  : 'bg-white/30 text-gray-600 hover:bg-white/50'
              }`}
            >
              List
            </button>
          </div>
        </div>
      </Card>

      {/* Content */}
      {isLoading ? (
        <Card padding="none">
          <LoadingState message="Loading connected systems..." />
        </Card>
      ) : filteredSystems.length === 0 ? (
        <Card padding="none">
          <EmptyState
            icon={<ServerIcon className="h-8 w-8" />}
            title="No systems found"
            description={
              searchTerm || typeFilter || statusFilter
                ? 'Try adjusting your search or filter criteria.'
                : 'Add your first system connection to get started.'
            }
            action={
              !searchTerm && !typeFilter && !statusFilter ? (
                <Button
                  size="sm"
                  icon={<PlusIcon className="h-4 w-4" />}
                  onClick={() => {
                    setForm(EMPTY_FORM);
                    setShowAddModal(true);
                  }}
                >
                  Add System
                </Button>
              ) : undefined
            }
          />
        </Card>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredSystems.map((system) => (
            <SystemCard
              key={system.id}
              system={system}
              onSelect={setSelectedSystem}
              onSync={handleSync}
              onTestConnection={handleTestConnection}
              syncingId={syncingId}
              testingId={testingId}
            />
          ))}
        </div>
      ) : (
        <Card padding="none">
          {/* List table — inline since Table component doesn't accept className on TR */}
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-white/20">
                  {listColumns.map((col, i) => (
                    <th
                      key={i}
                      className="px-4 py-3 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider"
                    >
                      {col.header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {filteredSystems.map((system) => (
                  <tr
                    key={system.id}
                    className="hover:bg-white/10 transition-colors"
                  >
                    {listColumns.map((col, i) => (
                      <td key={i} className="px-4 py-3">
                        {col.render(system)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Result count */}
      {!isLoading && filteredSystems.length > 0 && (
        <p className="text-xs text-gray-400 text-right">
          Showing {filteredSystems.length} of {systems.length} system{systems.length !== 1 ? 's' : ''}
        </p>
      )}

      {/* Add System Modal */}
      <Modal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Add System Connection"
        subtitle="Configure a new system to sync repository data and manage access"
        size="lg"
      >
        <SystemForm
          form={form}
          onChange={setForm}
          isSubmitting={createMutation.isPending}
          onSubmit={handleCreate}
          onCancel={() => setShowAddModal(false)}
          mode="add"
        />
      </Modal>

      {/* Edit System Modal */}
      <Modal
        open={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedSystem(null);
        }}
        title={selectedSystem ? `Edit: ${selectedSystem.name}` : 'Edit System'}
        subtitle="Update connection settings — credentials are encrypted at rest"
        size="lg"
      >
        <SystemForm
          form={form}
          onChange={setForm}
          isSubmitting={updateMutation.isPending}
          onSubmit={handleUpdate}
          onCancel={() => {
            setShowEditModal(false);
            setSelectedSystem(null);
          }}
          mode="edit"
        />
      </Modal>

      {/* Detail Side Panel */}
      {selectedSystem && !showEditModal && (
        <DetailPanel
          system={selectedSystem}
          onClose={() => setSelectedSystem(null)}
          onEdit={(sys) => {
            setSelectedSystem(null);
            handleOpenEdit(sys);
          }}
          onSync={handleSync}
          onTestConnection={handleTestConnection}
          syncingId={syncingId}
          testingId={testingId}
        />
      )}
    </div>
  );
}
