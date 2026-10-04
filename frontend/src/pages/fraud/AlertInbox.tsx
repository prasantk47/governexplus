import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  BellAlertIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  Table,
  Modal,
  Select,
  SearchInput,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

type AlertStatus = 'open' | 'investigating' | 'confirmed_fraud' | 'false_positive' | 'dismissed';

interface FraudAlert {
  id: string;
  rule_id?: string;
  user_id: string;
  system_id: string;
  alert_type: string;
  description: string;
  risk_score: number;
  status: AlertStatus;
  triggered_at: string;
  reviewed_by?: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_VARIANT: Record<AlertStatus, 'danger' | 'warning' | 'success' | 'neutral' | 'info'> = {
  open: 'danger',
  investigating: 'warning',
  confirmed_fraud: 'danger',
  false_positive: 'neutral',
  dismissed: 'neutral',
};

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'open', label: 'Open' },
  { value: 'investigating', label: 'Investigating' },
  { value: 'confirmed_fraud', label: 'Confirmed Fraud' },
  { value: 'false_positive', label: 'False Positive' },
  { value: 'dismissed', label: 'Dismissed' },
];


function riskScoreVariant(score: number): 'success' | 'warning' | 'danger' {
  if (score < 40) return 'success';
  if (score < 70) return 'warning';
  return 'danger';
}

// ─── Component ────────────────────────────────────────────────────────────────

export function AlertInbox() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('open');
  const [minRiskScore, setMinRiskScore] = useState('');
  const [confirmTarget, setConfirmTarget] = useState<{
    alert: FraudAlert;
    newStatus: AlertStatus;
  } | null>(null);
  const [openCaseTarget, setOpenCaseTarget] = useState<FraudAlert | null>(null);

  // ── Queries ──

  const { data: alertsData, isLoading } = useQuery<FraudAlert[]>({
    queryKey: ['fraud-alerts', statusFilter],
    queryFn: () =>
      api
        .get('/fraud/alerts', {
          params: statusFilter ? { status: statusFilter } : {},
        })
        .then(r => r.data?.alerts ?? r.data ?? []),
    refetchInterval: 15_000,
  });

  const alerts: FraudAlert[] = alertsData ?? [];

  const filtered = alerts.filter(a => {
    const q = search.toLowerCase();
    const matchSearch =
      !search ||
      a.description.toLowerCase().includes(q) ||
      a.user_id.toLowerCase().includes(q) ||
      a.system_id.toLowerCase().includes(q);
    const matchScore = !minRiskScore || a.risk_score >= Number(minRiskScore);
    return matchSearch && matchScore;
  });

  // ── Mutations ──

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: AlertStatus }) =>
      api.patch(`/fraud/alerts/${id}`, { status }),
    onSuccess: () => {
      toast.success('Alert status updated');
      queryClient.invalidateQueries({ queryKey: ['fraud-alerts'] });
      setConfirmTarget(null);
    },
    onError: () => toast.error('Failed to update alert status'),
  });

  const openCaseMutation = useMutation({
    mutationFn: (alertId: string) => api.post('/fraud/cases', { alert_id: alertId }),
    onSuccess: () => {
      toast.success('Case opened from alert');
      queryClient.invalidateQueries({ queryKey: ['fraud-alerts'] });
      queryClient.invalidateQueries({ queryKey: ['fraud-cases'] });
      setOpenCaseTarget(null);
    },
    onError: () => toast.error('Failed to open case'),
  });

  // ── Columns ──

  const columns = [
    {
      key: 'description',
      header: 'Alert',
      render: (a: FraudAlert) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100 max-w-xs truncate">
            {a.description}
          </div>
          <div className="text-xs text-gray-400">{a.alert_type}</div>
        </div>
      ),
    },
    {
      key: 'user_id',
      header: 'User',
      render: (a: FraudAlert) => (
        <span className="text-sm font-mono text-gray-700 dark:text-gray-300">{a.user_id}</span>
      ),
    },
    {
      key: 'system_id',
      header: 'System',
      render: (a: FraudAlert) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">{a.system_id}</span>
      ),
    },
    {
      key: 'risk_score',
      header: 'Risk Score',
      render: (a: FraudAlert) => (
        <Badge variant={riskScoreVariant(a.risk_score)} size="sm">
          {a.risk_score}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (a: FraudAlert) => (
        <Badge variant={STATUS_VARIANT[a.status]} dot size="sm">
          {a.status.replace('_', ' ')}
        </Badge>
      ),
    },
    {
      key: 'triggered_at',
      header: 'Triggered',
      render: (a: FraudAlert) => (
        <span className="text-sm text-gray-500">
          {new Date(a.triggered_at).toLocaleString()}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (a: FraudAlert) => (
        <div className="flex justify-end gap-1">
          {a.status === 'open' && (
            <Button
              size="sm"
              variant="ghost"
              onClick={e => {
                e.stopPropagation();
                setConfirmTarget({ alert: a, newStatus: 'investigating' });
              }}
            >
              Investigate
            </Button>
          )}
          {(a.status === 'open' || a.status === 'investigating') && (
            <>
              <Button
                size="sm"
                variant="ghost"
                onClick={e => {
                  e.stopPropagation();
                  setOpenCaseTarget(a);
                }}
              >
                Open Case
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={e => {
                  e.stopPropagation();
                  setConfirmTarget({ alert: a, newStatus: 'dismissed' });
                }}
              >
                Dismiss
              </Button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Alert Inbox"
        subtitle="Triage and investigate fraud detection alerts"
        actions={
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
              <BellAlertIcon className="h-4 w-4 text-red-500" />
              {alerts.filter(a => a.status === 'open').length} open alerts
            </span>
          </div>
        }
      />

      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <SearchInput
              placeholder="Search by description, user, or system..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onClear={() => setSearch('')}
            />
          </div>
          <Select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            options={STATUS_OPTIONS}
          />
          <div className="flex items-center gap-2">
            <MagnifyingGlassIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <select
              value={minRiskScore}
              onChange={e => setMinRiskScore(e.target.value)}
              className="text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Min Score</option>
              <option value="25">25+</option>
              <option value="50">50+</option>
              <option value="75">75+</option>
              <option value="90">90+</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Table */}
      <Table
        columns={columns}
        data={filtered}
        loading={isLoading}
        emptyMessage="No fraud alerts found. The detection engine will surface alerts here."
      />

      {/* Status Change Confirm Modal */}
      <Modal
        open={!!confirmTarget}
        onClose={() => setConfirmTarget(null)}
        title="Confirm Status Change"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmTarget(null)}>Cancel</Button>
            <Button
              loading={updateStatusMutation.isPending}
              onClick={() => {
                if (confirmTarget) {
                  updateStatusMutation.mutate({
                    id: confirmTarget.alert.id,
                    status: confirmTarget.newStatus,
                  });
                }
              }}
            >
              Confirm
            </Button>
          </>
        }
      >
        {confirmTarget && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Change alert status to{' '}
              <span className="font-semibold text-gray-900 dark:text-gray-100">
                {confirmTarget.newStatus.replace('_', ' ')}
              </span>
              ?
            </p>
            <p className="text-xs text-gray-400 truncate">{confirmTarget.alert.description}</p>
          </div>
        )}
      </Modal>

      {/* Open Case Modal */}
      <Modal
        open={!!openCaseTarget}
        onClose={() => setOpenCaseTarget(null)}
        title="Open Fraud Case"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpenCaseTarget(null)}>Cancel</Button>
            <Button
              loading={openCaseMutation.isPending}
              onClick={() => openCaseTarget && openCaseMutation.mutate(openCaseTarget.id)}
            >
              Open Case
            </Button>
          </>
        }
      >
        {openCaseTarget && (
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Open a new fraud case from this alert?
            <br />
            <span className="text-xs text-gray-400 mt-1 block">{openCaseTarget.description}</span>
          </p>
        )}
      </Modal>
    </div>
  );
}
