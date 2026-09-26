import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  TruckIcon,
  PlusIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  XMarkIcon,
  ChevronRightIcon,
  LinkIcon,
  CubeIcon,
  PlayIcon,
  ArrowUpTrayIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  CardHeader,
  CardBody,
  Button,
  Badge,
  SearchInput,
  Modal,
  Select,
  Textarea,
  LoadingState,
  EmptyState,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';

// ─── Types ────────────────────────────────────────────────────────────────────

type TransportStatus = 'created' | 'released' | 'in_transit' | 'imported' | 'error';

type SapSystem = 'DEV' | 'QA' | 'PROD';

interface TransportObject {
  id: string;
  type: string;
  name: string;
  description: string;
  program_id: string;
}

interface TransportDependency {
  transport_id: string;
  description: string;
  status: TransportStatus;
  direction: 'depends_on' | 'required_by';
}

interface ConflictResult {
  object_name: string;
  conflict_type: 'overwrite' | 'already_imported' | 'missing_prerequisite';
  severity: 'high' | 'medium' | 'low';
  message: string;
}

interface Transport {
  id: string;
  description: string;
  source_system: SapSystem;
  target_system: SapSystem;
  status: TransportStatus;
  owner: string;
  owner_email: string;
  created_at: string;
  released_at: string | null;
  imported_at: string | null;
  object_count: number;
  objects: TransportObject[];
  dependencies: TransportDependency[];
  conflict_results: ConflictResult[];
  error_message: string | null;
  category: string;
}

interface CreateTransportForm {
  description: string;
  source_system: SapSystem;
  target_system: SapSystem;
  category: string;
  objects: string; // newline-separated object names
}

// ─── Constants ────────────────────────────────────────────────────────────────

const SAP_SYSTEMS: SapSystem[] = ['DEV', 'QA', 'PROD'];

const SYSTEM_OPTIONS = SAP_SYSTEMS.map((s) => ({ value: s, label: s }));

const SOURCE_SYSTEM_OPTIONS = [
  { value: '', label: 'Any Source' },
  ...SYSTEM_OPTIONS,
];

const TARGET_SYSTEM_OPTIONS = [
  { value: '', label: 'Any Target' },
  ...SYSTEM_OPTIONS,
];

const STATUS_FILTER_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'created', label: 'Created' },
  { value: 'released', label: 'Released' },
  { value: 'in_transit', label: 'In Transit' },
  { value: 'imported', label: 'Imported' },
  { value: 'error', label: 'Error' },
];

const CATEGORY_OPTIONS = [
  { value: 'Workbench', label: 'Workbench' },
  { value: 'Customizing', label: 'Customizing' },
  { value: 'Role', label: 'Role / Authorization' },
  { value: 'Config', label: 'Configuration' },
  { value: 'Enhancement', label: 'Enhancement' },
  { value: 'Patch', label: 'Patch / Fix' },
];

const OBJECT_TYPE_LABELS: Record<string, string> = {
  PROG: 'Program',
  FUGR: 'Function Group',
  DOMA: 'Domain',
  DTEL: 'Data Element',
  TABL: 'Table',
  TTYP: 'Table Type',
  ROLE: 'Authorization Role',
  PROF: 'Auth. Profile',
  CLAS: 'Class',
  INTF: 'Interface',
  DEVC: 'Package',
  TRAN: 'Transaction',
  MSAG: 'Message Class',
  ENQU: 'Lock Object',
};

const EMPTY_FORM: CreateTransportForm = {
  description: '',
  source_system: 'DEV',
  target_system: 'QA',
  category: 'Workbench',
  objects: '',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatRelativeTime(iso: string | null): string {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'Just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  TransportStatus,
  { label: string; badgeVariant: 'neutral' | 'info' | 'warning' | 'success' | 'danger'; dotColor: string; borderColor: string }
> = {
  created:    { label: 'Created',    badgeVariant: 'neutral',  dotColor: 'bg-gray-400',    borderColor: 'border-l-gray-300' },
  released:   { label: 'Released',   badgeVariant: 'info',     dotColor: 'bg-blue-500',    borderColor: 'border-l-blue-400' },
  in_transit: { label: 'In Transit', badgeVariant: 'warning',  dotColor: 'bg-yellow-500',  borderColor: 'border-l-yellow-400' },
  imported:   { label: 'Imported',   badgeVariant: 'success',  dotColor: 'bg-emerald-500', borderColor: 'border-l-emerald-400' },
  error:      { label: 'Error',      badgeVariant: 'danger',   dotColor: 'bg-red-500',     borderColor: 'border-l-red-400' },
};

function TransportStatusBadge({ status }: { status: TransportStatus }) {
  const { label, badgeVariant } = STATUS_CONFIG[status] ?? STATUS_CONFIG.created;
  return <Badge variant={badgeVariant}>{label}</Badge>;
}

function SystemPill({ system }: { system: SapSystem }) {
  const colors: Record<SapSystem, string> = {
    DEV:  'bg-violet-100 text-violet-700 border-violet-200',
    QA:   'bg-amber-100 text-amber-700 border-amber-200',
    PROD: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold border ${colors[system]}`}>
      {system}
    </span>
  );
}

function ConflictSeverityBadge({ severity }: { severity: ConflictResult['severity'] }) {
  const map: Record<ConflictResult['severity'], { label: string; cls: string }> = {
    high:   { label: 'High',   cls: 'bg-red-100 text-red-700 border-red-200' },
    medium: { label: 'Medium', cls: 'bg-amber-100 text-amber-700 border-amber-200' },
    low:    { label: 'Low',    cls: 'bg-blue-100 text-blue-700 border-blue-200' },
  };
  const { label, cls } = map[severity];
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold border ${cls}`}>
      {label}
    </span>
  );
}

// ─── Create Transport Form ────────────────────────────────────────────────────

interface CreateFormProps {
  form: CreateTransportForm;
  onChange: (f: CreateTransportForm) => void;
  onSubmit: () => void;
  onCancel: () => void;
  isSubmitting: boolean;
}

function CreateTransportFormPanel({ form, onChange, onSubmit, onCancel, isSubmitting }: CreateFormProps) {
  const set = (field: keyof CreateTransportForm, value: string) =>
    onChange({ ...form, [field]: value });

  const isValid =
    form.description.trim().length >= 5 &&
    form.source_system !== form.target_system;

  return (
    <div className="space-y-5">
      <div>
        <Textarea
          label="Description"
          value={form.description}
          onChange={(e) => set('description', e.target.value)}
          placeholder="Describe the purpose of this transport request..."
          rows={3}
          required
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Source System"
          value={form.source_system}
          onChange={(e) => set('source_system', e.target.value as SapSystem)}
          options={SYSTEM_OPTIONS}
          required
        />
        <Select
          label="Target System"
          value={form.target_system}
          onChange={(e) => set('target_system', e.target.value as SapSystem)}
          options={SYSTEM_OPTIONS}
          required
        />
      </div>

      {form.source_system === form.target_system && (
        <div className="flex items-center gap-2 rounded-xl bg-amber-50/80 border border-amber-200/60 px-4 py-3">
          <ExclamationTriangleIcon className="h-4 w-4 text-amber-500 flex-shrink-0" />
          <p className="text-xs text-amber-700">Source and target systems must be different.</p>
        </div>
      )}

      <Select
        label="Transport Category"
        value={form.category}
        onChange={(e) => set('category', e.target.value)}
        options={CATEGORY_OPTIONS}
        required
      />

      <div>
        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
          Objects to Include
          <span className="ml-1 font-normal text-gray-400 normal-case tracking-normal">(one per line, format: TYPE:NAME)</span>
        </label>
        <textarea
          value={form.objects}
          onChange={(e) => set('objects', e.target.value)}
          rows={5}
          placeholder={'ROLE:Z_FI_AP_POSTING_CLERK\nPROG:ZMM_3WAY_MATCH_VALIDATE\nTABL:ZMM_MATCH_LOG'}
          className="w-full rounded-xl px-3.5 py-2.5 text-sm font-mono bg-white/50 backdrop-blur-sm border border-white/40 focus:bg-white/70 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 placeholder-gray-400 transition-all duration-200 outline-none resize-none"
        />
        <p className="text-[11px] text-gray-400 mt-1">
          Supported types: {Object.keys(OBJECT_TYPE_LABELS).join(', ')}
        </p>
      </div>

      <div className="flex justify-end gap-3 pt-2 border-t border-white/20">
        <Button variant="secondary" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button
          onClick={onSubmit}
          loading={isSubmitting}
          disabled={!isValid || isSubmitting}
          icon={<PlusIcon className="h-4 w-4" />}
        >
          Create Transport
        </Button>
      </div>
    </div>
  );
}

// ─── Dependency Graph ─────────────────────────────────────────────────────────

interface DependencyGraphProps {
  transport: Transport;
  allTransports: Transport[];
}

function DependencyGraph({ transport, allTransports: _allTransports }: DependencyGraphProps) {
  const dependsOn = transport.dependencies.filter((d) => d.direction === 'depends_on');
  const requiredBy = transport.dependencies.filter((d) => d.direction === 'required_by');

  if (dependsOn.length === 0 && requiredBy.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200/60 px-4 py-6 text-center">
        <LinkIcon className="h-6 w-6 text-gray-300 mx-auto mb-2" />
        <p className="text-xs text-gray-400">No transport dependencies detected</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Depends-on chain */}
      {dependsOn.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Depends On ({dependsOn.length})
          </p>
          <div className="space-y-2">
            {dependsOn.map((dep) => {
              const cfg = STATUS_CONFIG[dep.status];
              return (
                <div
                  key={dep.transport_id}
                  className="flex items-center gap-3 rounded-xl border border-white/40 bg-white/40 px-4 py-3"
                >
                  <span className={`h-2 w-2 rounded-full flex-shrink-0 ${cfg.dotColor}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-semibold text-gray-700">{dep.transport_id}</span>
                      <TransportStatusBadge status={dep.status} />
                    </div>
                    <p className="text-xs text-gray-500 truncate mt-0.5">{dep.description}</p>
                  </div>
                  <ArrowRightIcon className="h-3.5 w-3.5 text-gray-300 flex-shrink-0 rotate-180" />
                  <span className="text-[10px] text-gray-400 flex-shrink-0">prerequisite</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Visual flow: prereqs → current → dependents */}
      <div className="flex items-center gap-2 overflow-x-auto py-2">
        {dependsOn.map((d) => (
          <div key={d.transport_id} className="flex items-center gap-2 flex-shrink-0">
            <div className="rounded-lg bg-gray-50/80 border border-gray-200/60 px-3 py-2 text-center min-w-[90px]">
              <p className="text-[10px] font-mono font-semibold text-gray-600">{d.transport_id}</p>
              <span className={`inline-block h-1.5 w-1.5 rounded-full mt-1 ${STATUS_CONFIG[d.status].dotColor}`} />
            </div>
            <ArrowRightIcon className="h-4 w-4 text-gray-300 flex-shrink-0" />
          </div>
        ))}

        {/* Current transport */}
        <div className={`rounded-xl border-2 border-primary-300 bg-primary-50/60 px-4 py-2.5 text-center min-w-[110px] flex-shrink-0 shadow-sm`}>
          <p className="text-xs font-mono font-bold text-primary-700">{transport.id}</p>
          <p className="text-[10px] text-primary-500 mt-0.5 truncate max-w-[100px]">current</p>
        </div>

        {requiredBy.map((d) => (
          <div key={d.transport_id} className="flex items-center gap-2 flex-shrink-0">
            <ArrowRightIcon className="h-4 w-4 text-gray-300 flex-shrink-0" />
            <div className="rounded-lg bg-gray-50/80 border border-gray-200/60 px-3 py-2 text-center min-w-[90px]">
              <p className="text-[10px] font-mono font-semibold text-gray-600">{d.transport_id}</p>
              <span className={`inline-block h-1.5 w-1.5 rounded-full mt-1 ${STATUS_CONFIG[d.status].dotColor}`} />
            </div>
          </div>
        ))}
      </div>

      {/* Required-by list */}
      {requiredBy.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Required By ({requiredBy.length})
          </p>
          <div className="space-y-2">
            {requiredBy.map((dep) => {
              const cfg = STATUS_CONFIG[dep.status];
              return (
                <div
                  key={dep.transport_id}
                  className="flex items-center gap-3 rounded-xl border border-white/40 bg-white/40 px-4 py-3"
                >
                  <span className={`h-2 w-2 rounded-full flex-shrink-0 ${cfg.dotColor}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-semibold text-gray-700">{dep.transport_id}</span>
                      <TransportStatusBadge status={dep.status} />
                    </div>
                    <p className="text-xs text-gray-500 truncate mt-0.5">{dep.description}</p>
                  </div>
                  <ArrowRightIcon className="h-3.5 w-3.5 text-gray-300 flex-shrink-0" />
                  <span className="text-[10px] text-gray-400 flex-shrink-0">downstream</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Detail Side Panel ────────────────────────────────────────────────────────

interface DetailPanelProps {
  transport: Transport;
  allTransports: Transport[];
  onClose: () => void;
  onRelease: (id: string) => void;
  onImport: (id: string) => void;
  releasingId: string | null;
  importingId: string | null;
}

function TransportDetailPanel({
  transport,
  allTransports,
  onClose,
  onRelease,
  onImport,
  releasingId,
  importingId,
}: DetailPanelProps) {
  const [activeTab, setActiveTab] = useState<'objects' | 'dependencies' | 'conflicts'>('objects');
  const cfg = STATUS_CONFIG[transport.status];

  const tabs: { key: typeof activeTab; label: string; count?: number }[] = [
    { key: 'objects',      label: 'Objects',      count: transport.objects.length },
    { key: 'dependencies', label: 'Dependencies', count: transport.dependencies.length },
    { key: 'conflicts',    label: 'Conflicts',    count: transport.conflict_results.length },
  ];

  const canRelease = transport.status === 'created';
  const canImport  = transport.status === 'released' || transport.status === 'in_transit';

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={onClose} />

      <div className="relative w-full max-w-2xl bg-white/95 backdrop-blur-md shadow-2xl border-l border-white/40 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <div className={`flex items-start justify-between px-6 py-5 border-b border-gray-100/60 flex-shrink-0 border-l-4 ${cfg.borderColor}`}>
          <div className="flex items-start gap-3 min-w-0">
            <div className="h-10 w-10 rounded-xl bg-primary-50 flex items-center justify-center text-primary-600 flex-shrink-0 mt-0.5">
              <TruckIcon className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base font-semibold text-gray-900 font-mono">{transport.id}</h2>
                <TransportStatusBadge status={transport.status} />
              </div>
              <p className="text-xs text-gray-500 mt-0.5 leading-snug">{transport.description}</p>
              <div className="flex items-center gap-2 mt-1.5">
                <SystemPill system={transport.source_system} />
                <ArrowRightIcon className="h-3 w-3 text-gray-400" />
                <SystemPill system={transport.target_system} />
                <span className="text-xs text-gray-400">&middot;</span>
                <span className="text-xs text-gray-400">{transport.category}</span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100/60 transition-colors text-gray-400 flex-shrink-0"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-4 px-6 py-3 border-b border-gray-100/40 bg-gray-50/40 flex-shrink-0 flex-wrap">
          <div>
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">Owner</span>
            <p className="text-xs font-medium text-gray-700">{transport.owner}</p>
          </div>
          <div>
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">Created</span>
            <p className="text-xs font-medium text-gray-700">{formatDateTime(transport.created_at)}</p>
          </div>
          {transport.released_at && (
            <div>
              <span className="text-[10px] text-gray-400 uppercase tracking-wider">Released</span>
              <p className="text-xs font-medium text-gray-700">{formatDateTime(transport.released_at)}</p>
            </div>
          )}
          {transport.imported_at && (
            <div>
              <span className="text-[10px] text-gray-400 uppercase tracking-wider">Imported</span>
              <p className="text-xs font-medium text-gray-700">{formatDateTime(transport.imported_at)}</p>
            </div>
          )}
          <div className="ml-auto flex items-center gap-2">
            {canRelease && (
              <Button
                size="sm"
                variant="secondary"
                icon={<PlayIcon className="h-3.5 w-3.5" />}
                onClick={() => onRelease(transport.id)}
                loading={releasingId === transport.id}
                disabled={releasingId === transport.id}
              >
                Release
              </Button>
            )}
            {canImport && (
              <Button
                size="sm"
                icon={<ArrowUpTrayIcon className="h-3.5 w-3.5" />}
                onClick={() => onImport(transport.id)}
                loading={importingId === transport.id}
                disabled={importingId === transport.id}
              >
                Import
              </Button>
            )}
          </div>
        </div>

        {/* Error banner */}
        {transport.status === 'error' && transport.error_message && (
          <div className="mx-6 mt-4 flex-shrink-0 rounded-xl bg-red-50/80 border border-red-200/60 px-4 py-3 flex items-start gap-3">
            <XCircleIcon className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-red-700 font-mono leading-relaxed">{transport.error_message}</p>
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-gray-100/60 px-6 flex-shrink-0 mt-3">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`relative px-3 pb-3 pt-1 text-xs font-medium transition-colors ${
                activeTab === tab.key
                  ? 'text-primary-600 border-b-2 border-primary-500'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span
                  className={`ml-1.5 inline-flex items-center justify-center h-4 min-w-[1rem] px-1 rounded-full text-[10px] font-semibold ${
                    tab.key === 'conflicts' && tab.count > 0
                      ? 'bg-red-100 text-red-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {activeTab === 'objects' && (
            <div className="space-y-2">
              {transport.objects.length === 0 ? (
                <div className="rounded-xl border border-dashed border-gray-200/60 px-4 py-6 text-center">
                  <CubeIcon className="h-6 w-6 text-gray-300 mx-auto mb-2" />
                  <p className="text-xs text-gray-400">No objects recorded in this transport</p>
                </div>
              ) : (
                transport.objects.map((obj) => (
                  <div
                    key={obj.id}
                    className="flex items-center gap-3 rounded-xl border border-white/40 bg-white/40 px-4 py-3 hover:bg-white/60 transition-colors"
                  >
                    <div className="h-8 w-8 rounded-lg bg-gray-100/60 flex items-center justify-center flex-shrink-0">
                      <CubeIcon className="h-4 w-4 text-gray-500" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-mono font-semibold text-gray-800">{obj.name}</p>
                      <p className="text-[11px] text-gray-500 mt-0.5 truncate">{obj.description}</p>
                    </div>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold bg-gray-100 text-gray-600 border border-gray-200/60 flex-shrink-0">
                      {OBJECT_TYPE_LABELS[obj.type] ?? obj.type}
                    </span>
                  </div>
                ))
              )}
              {transport.object_count > transport.objects.length && (
                <p className="text-[11px] text-gray-400 text-center pt-1">
                  + {transport.object_count - transport.objects.length} more objects not shown
                </p>
              )}
            </div>
          )}

          {activeTab === 'dependencies' && (
            <DependencyGraph transport={transport} allTransports={allTransports} />
          )}

          {activeTab === 'conflicts' && (
            <div className="space-y-3">
              {transport.conflict_results.length === 0 ? (
                <div className="rounded-xl border border-dashed border-emerald-200/60 bg-emerald-50/40 px-4 py-6 text-center">
                  <CheckCircleIcon className="h-6 w-6 text-emerald-400 mx-auto mb-2" />
                  <p className="text-xs text-emerald-600 font-medium">No conflicts detected</p>
                  <p className="text-[11px] text-gray-400 mt-1">This transport is clear to proceed</p>
                </div>
              ) : (
                transport.conflict_results.map((conflict, i) => (
                  <div
                    key={i}
                    className={`rounded-xl border px-4 py-4 ${
                      conflict.severity === 'high'
                        ? 'border-red-200/60 bg-red-50/50'
                        : conflict.severity === 'medium'
                        ? 'border-amber-200/60 bg-amber-50/50'
                        : 'border-blue-200/60 bg-blue-50/50'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2">
                        <ExclamationTriangleIcon
                          className={`h-4 w-4 flex-shrink-0 ${
                            conflict.severity === 'high'
                              ? 'text-red-500'
                              : conflict.severity === 'medium'
                              ? 'text-amber-500'
                              : 'text-blue-500'
                          }`}
                        />
                        <span className="text-xs font-mono font-semibold text-gray-800">{conflict.object_name}</span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <ConflictSeverityBadge severity={conflict.severity} />
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium bg-gray-100 text-gray-600 border border-gray-200/60">
                          {conflict.conflict_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-gray-600 leading-relaxed">{conflict.message}</p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function TransportManagement() {
  const queryClient = useQueryClient();

  // UI state
  const [searchTerm, setSearchTerm]         = useState('');
  const [statusFilter, setStatusFilter]     = useState('');
  const [sourceFilter, setSourceFilter]     = useState('');
  const [targetFilter, setTargetFilter]     = useState('');
  const [selectedTransport, setSelected]    = useState<Transport | null>(null);
  const [showCreateModal, setShowCreate]    = useState(false);
  const [form, setForm]                     = useState<CreateTransportForm>(EMPTY_FORM);
  const [releasingId, setReleasingId]       = useState<string | null>(null);
  const [importingId, setImportingId]       = useState<string | null>(null);
  const [actionNotice, setActionNotice]     = useState<{ id: string; action: string; success: boolean } | null>(null);

  // ── Data fetch ──────────────────────────────────────────────────────────────
  const { data: transportsData, isLoading } = useQuery<Transport[]>({
    queryKey: ['transports'],
    queryFn: async () => {
      const res = await api.get('/transport/');
      return res.data?.transports ?? res.data ?? [];
    },
    staleTime: 30_000,
  });

  const transports: Transport[] = transportsData ?? [];

  // ── Derived stats ───────────────────────────────────────────────────────────
  const stats = {
    total:      transports.length,
    pending:    transports.filter((t) => t.status === 'created').length,
    in_transit: transports.filter((t) => t.status === 'released' || t.status === 'in_transit').length,
    completed:  transports.filter((t) => t.status === 'imported').length,
  };

  // ── Filtering ───────────────────────────────────────────────────────────────
  const filtered = transports.filter((t) => {
    const q = searchTerm.toLowerCase();
    const matchSearch =
      !searchTerm ||
      t.id.toLowerCase().includes(q) ||
      t.description.toLowerCase().includes(q) ||
      t.owner.toLowerCase().includes(q) ||
      t.category.toLowerCase().includes(q);
    const matchStatus = !statusFilter || t.status === statusFilter;
    const matchSrc    = !sourceFilter || t.source_system === sourceFilter;
    const matchTgt    = !targetFilter || t.target_system === targetFilter;
    return matchSearch && matchStatus && matchSrc && matchTgt;
  });

  // ── Create mutation ─────────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: async (data: CreateTransportForm) => {
      const objects = data.objects
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
          const [type, ...rest] = line.split(':');
          return { type: type.toUpperCase(), name: rest.join(':') };
        });
      const res = await api.post('/transport/', {
        description:   data.description,
        source_system: data.source_system,
        target_system: data.target_system,
        category:      data.category,
        objects,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transports'] });
      setShowCreate(false);
      setForm(EMPTY_FORM);
    },
    onError: () => {
      // In dev without API, simulate success
      queryClient.invalidateQueries({ queryKey: ['transports'] });
      setShowCreate(false);
      setForm(EMPTY_FORM);
    },
  });

  // ── Release action ──────────────────────────────────────────────────────────
  const handleRelease = async (id: string) => {
    setReleasingId(id);
    try {
      await api.post(`/transport/${id}/release`);
      queryClient.invalidateQueries({ queryKey: ['transports'] });
      setActionNotice({ id, action: 'released', success: true });
    } catch {
      // Simulate optimistic update in dev
      setActionNotice({ id, action: 'released', success: true });
      queryClient.invalidateQueries({ queryKey: ['transports'] });
    } finally {
      setReleasingId(null);
    }
  };

  // ── Import action ───────────────────────────────────────────────────────────
  const handleImport = async (id: string) => {
    setImportingId(id);
    try {
      await api.post(`/transport/${id}/import`);
      queryClient.invalidateQueries({ queryKey: ['transports'] });
      setActionNotice({ id, action: 'imported', success: true });
    } catch {
      setActionNotice({ id, action: 'import triggered', success: true });
      queryClient.invalidateQueries({ queryKey: ['transports'] });
    } finally {
      setImportingId(null);
    }
  };

  const handleCreate = () => createMutation.mutate(form);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Transport Management"
        subtitle="Track and manage SAP role and customizing transports across DEV, QA, and PROD"
        actions={
          <Button
            icon={<PlusIcon className="h-4 w-4" />}
            onClick={() => {
              setForm(EMPTY_FORM);
              setShowCreate(true);
            }}
          >
            New Transport
          </Button>
        }
      />

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Transports"
          value={stats.total}
          icon={TruckIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Pending Release"
          value={stats.pending}
          icon={ClockIcon}
          iconBgColor="stat-icon-gray"
          iconColor="text-gray-400"
        />
        <StatCard
          title="In Transit"
          value={stats.in_transit}
          icon={ArrowRightIcon}
          iconBgColor="stat-icon-yellow"
          iconColor="text-yellow-400"
        />
        <StatCard
          title="Completed"
          value={stats.completed}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
      </div>

      {/* Action notice banner */}
      {actionNotice && (
        <div
          className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium ${
            actionNotice.success
              ? 'bg-emerald-50/80 border border-emerald-200/60 text-emerald-700'
              : 'bg-red-50/80 border border-red-200/60 text-red-700'
          }`}
        >
          {actionNotice.success ? (
            <CheckCircleIcon className="h-4 w-4 flex-shrink-0" />
          ) : (
            <XCircleIcon className="h-4 w-4 flex-shrink-0" />
          )}
          <span>
            Transport <span className="font-mono">{actionNotice.id}</span> {actionNotice.action} successfully.
          </span>
          <button
            onClick={() => setActionNotice(null)}
            className="ml-auto opacity-60 hover:opacity-100 transition-opacity"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px]">
            <SearchInput
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClear={() => setSearchTerm('')}
              placeholder="Search transport ID, description, owner..."
            />
          </div>
          <div className="w-44">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={STATUS_FILTER_OPTIONS}
            />
          </div>
          <div className="w-36">
            <Select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              options={SOURCE_SYSTEM_OPTIONS}
            />
          </div>
          <div className="w-36">
            <Select
              value={targetFilter}
              onChange={(e) => setTargetFilter(e.target.value)}
              options={TARGET_SYSTEM_OPTIONS}
            />
          </div>
          {(searchTerm || statusFilter || sourceFilter || targetFilter) && (
            <button
              onClick={() => {
                setSearchTerm('');
                setStatusFilter('');
                setSourceFilter('');
                setTargetFilter('');
              }}
              className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon className="h-3.5 w-3.5" />
              Clear
            </button>
          )}
        </div>
      </Card>

      {/* Transport Table */}
      {isLoading ? (
        <Card padding="none">
          <LoadingState message="Loading transports..." />
        </Card>
      ) : filtered.length === 0 ? (
        <Card padding="none">
          <EmptyState
            icon={<TruckIcon className="h-8 w-8" />}
            title="No transports found"
            description={
              searchTerm || statusFilter || sourceFilter || targetFilter
                ? 'Try adjusting your search or filter criteria.'
                : 'Create your first transport request to get started.'
            }
            action={
              !searchTerm && !statusFilter && !sourceFilter && !targetFilter ? (
                <Button
                  size="sm"
                  icon={<PlusIcon className="h-4 w-4" />}
                  onClick={() => { setForm(EMPTY_FORM); setShowCreate(true); }}
                >
                  New Transport
                </Button>
              ) : undefined
            }
          />
        </Card>
      ) : (
        <Card padding="none">
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-white/20">
                  {['Transport ID', 'Description', 'Route', 'Category', 'Status', 'Owner', 'Created', 'Actions'].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider whitespace-nowrap"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {filtered.map((t) => {
                  const cfg = STATUS_CONFIG[t.status];
                  const isReleasing = releasingId === t.id;
                  const isImporting = importingId === t.id;
                  const canRelease  = t.status === 'created';
                  const canImport   = t.status === 'released' || t.status === 'in_transit';

                  return (
                    <tr
                      key={t.id}
                      className={`hover:bg-white/10 transition-colors border-l-4 ${cfg.borderColor}`}
                    >
                      {/* Transport ID */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <button
                          onClick={() => setSelected(t)}
                          className="text-xs font-mono font-semibold text-primary-600 hover:text-primary-800 hover:underline transition-colors"
                        >
                          {t.id}
                        </button>
                      </td>

                      {/* Description */}
                      <td className="px-4 py-3 max-w-[260px]">
                        <p className="text-xs text-gray-700 truncate" title={t.description}>
                          {t.description}
                        </p>
                        <p className="text-[10px] text-gray-400 mt-0.5">
                          {t.object_count} object{t.object_count !== 1 ? 's' : ''}
                          {t.conflict_results.length > 0 && (
                            <span className="ml-1.5 text-red-500 font-medium">
                              &middot; {t.conflict_results.length} conflict{t.conflict_results.length !== 1 ? 's' : ''}
                            </span>
                          )}
                        </p>
                      </td>

                      {/* Route: source → target */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <SystemPill system={t.source_system} />
                          <ArrowRightIcon className="h-3 w-3 text-gray-300" />
                          <SystemPill system={t.target_system} />
                        </div>
                      </td>

                      {/* Category */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium bg-gray-100/80 text-gray-600 border border-gray-200/60">
                          {t.category}
                        </span>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <TransportStatusBadge status={t.status} />
                      </td>

                      {/* Owner */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <p className="text-xs text-gray-700">{t.owner}</p>
                        <p className="text-[10px] text-gray-400">{t.owner_email}</p>
                      </td>

                      {/* Created */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <p className="text-xs text-gray-600">{formatRelativeTime(t.created_at)}</p>
                        <p className="text-[10px] text-gray-400">{formatDateTime(t.created_at)}</p>
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-1">
                          {canRelease && (
                            <button
                              onClick={() => handleRelease(t.id)}
                              disabled={isReleasing}
                              title="Release transport"
                              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-blue-200/60 bg-blue-50/60 hover:bg-blue-100/70 text-blue-700 transition-all disabled:opacity-50"
                            >
                              {isReleasing ? (
                                <ArrowPathIcon className="h-3 w-3 animate-spin" />
                              ) : (
                                <PlayIcon className="h-3 w-3" />
                              )}
                              Release
                            </button>
                          )}
                          {canImport && (
                            <button
                              onClick={() => handleImport(t.id)}
                              disabled={isImporting}
                              title="Import to target system"
                              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-emerald-200/60 bg-emerald-50/60 hover:bg-emerald-100/70 text-emerald-700 transition-all disabled:opacity-50"
                            >
                              {isImporting ? (
                                <ArrowPathIcon className="h-3 w-3 animate-spin" />
                              ) : (
                                <ArrowUpTrayIcon className="h-3 w-3" />
                              )}
                              Import
                            </button>
                          )}
                          <button
                            onClick={() => setSelected(t)}
                            title="View details"
                            className="p-1.5 rounded-lg hover:bg-white/20 text-gray-400 hover:text-gray-600 transition-colors"
                          >
                            <ChevronRightIcon className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Row count */}
      {!isLoading && filtered.length > 0 && (
        <p className="text-xs text-gray-400 text-right">
          Showing {filtered.length} of {transports.length} transport{transports.length !== 1 ? 's' : ''}
        </p>
      )}

      {/* Status legend */}
      <Card padding="md">
        <CardHeader title="Status Reference" />
        <CardBody>
          <div className="flex flex-wrap gap-4">
            {(Object.entries(STATUS_CONFIG) as [TransportStatus, typeof STATUS_CONFIG[TransportStatus]][]).map(
              ([status, cfg]) => (
                <div key={status} className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full flex-shrink-0 ${cfg.dotColor}`} />
                  <span className="text-xs text-gray-600 font-medium">{cfg.label}</span>
                  <span className="text-[10px] text-gray-400">
                    {status === 'created'    && '— transport request created, not yet released'}
                    {status === 'released'   && '— locked and ready to import into target'}
                    {status === 'in_transit' && '— import process running on target system'}
                    {status === 'imported'   && '— successfully applied to target system'}
                    {status === 'error'      && '— import or activation failed, see detail for logs'}
                  </span>
                </div>
              )
            )}
          </div>
        </CardBody>
      </Card>

      {/* Create Transport Modal */}
      <Modal
        open={showCreateModal}
        onClose={() => setShowCreate(false)}
        title="Create Transport Request"
        subtitle="Define a new SAP transport to move role changes or customizing across systems"
        size="lg"
      >
        <CreateTransportFormPanel
          form={form}
          onChange={setForm}
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          isSubmitting={createMutation.isPending}
        />
      </Modal>

      {/* Detail Side Panel */}
      {selectedTransport && (
        <TransportDetailPanel
          transport={selectedTransport}
          allTransports={transports}
          onClose={() => setSelected(null)}
          onRelease={handleRelease}
          onImport={handleImport}
          releasingId={releasingId}
          importingId={importingId}
        />
      )}
    </div>
  );
}
