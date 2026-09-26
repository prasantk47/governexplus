import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  BellIcon,
  PaperAirplaneIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  EnvelopeIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
  ChatBubbleLeftRightIcon,
  EyeIcon,
  XMarkIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  CardHeader,
  CardBody,
  LoadingState,
  EmptyState,
} from '../../components/ui';
import { StatCard } from '../../components/StatCard';

// ─── Types ────────────────────────────────────────────────────────────────────

type NotificationType =
  | 'access_request_submitted'
  | 'approval_required'
  | 'access_approved'
  | 'access_rejected'
  | 'certification_due'
  | 'certification_reminder'
  | 'risk_alert'
  | 'sod_violation'
  | 'firefighter_session_started'
  | 'firefighter_session_ended'
  | 'password_reset'
  | 'user_provisioned'
  | 'user_deprovisioned'
  | 'policy_violation'
  | 'system_alert';

type Channel = 'email' | 'slack';
type DeliveryStatus = 'delivered' | 'failed' | 'pending' | 'retrying';

interface NotificationHistoryItem {
  id: string;
  type: NotificationType;
  recipient: string;
  channel: Channel;
  status: DeliveryStatus;
  sentAt: string;
  subject: string;
  errorMessage?: string;
  retryCount: number;
}

interface NotificationTemplate {
  id: string;
  type: NotificationType;
  channel: Channel;
  subject: string;
  bodyPreview: string;
  placeholders: string[];
  lastUpdated: string;
}

interface NotificationPreferences {
  userId: string;
  emailEnabled: boolean;
  slackEnabled: boolean;
  slackChannel: string;
  disabledTypes: NotificationType[];
}

interface SendNotificationForm {
  notificationType: NotificationType | '';
  recipientEmail: string;
  channels: { email: boolean; slack: boolean };
  contextVariables: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const NOTIFICATION_TYPE_OPTIONS: { value: NotificationType; label: string }[] = [
  { value: 'access_request_submitted', label: 'Access Request Submitted' },
  { value: 'approval_required', label: 'Approval Required' },
  { value: 'access_approved', label: 'Access Approved' },
  { value: 'access_rejected', label: 'Access Rejected' },
  { value: 'certification_due', label: 'Certification Due' },
  { value: 'certification_reminder', label: 'Certification Reminder' },
  { value: 'risk_alert', label: 'Risk Alert' },
  { value: 'sod_violation', label: 'SoD Violation Detected' },
  { value: 'firefighter_session_started', label: 'Privileged Access Session Started' },
  { value: 'firefighter_session_ended', label: 'Privileged Access Session Ended' },
  { value: 'password_reset', label: 'Password Reset' },
  { value: 'user_provisioned', label: 'User Provisioned' },
  { value: 'user_deprovisioned', label: 'User Deprovisioned' },
  { value: 'policy_violation', label: 'Policy Violation' },
  { value: 'system_alert', label: 'System Alert' },
];

const TYPE_LABELS: Record<NotificationType, string> = Object.fromEntries(
  NOTIFICATION_TYPE_OPTIONS.map((o) => [o.value, o.label])
) as Record<NotificationType, string>;

const EMPTY_SEND_FORM: SendNotificationForm = {
  notificationType: '',
  recipientEmail: '',
  channels: { email: true, slack: false },
  contextVariables: '{\n  "request_id": "",\n  "user_name": "",\n  "role_name": ""\n}',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatRelativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatDateTime(isoString: string): string {
  return new Date(isoString).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

function DeliveryStatusBadge({ status }: { status: DeliveryStatus }) {
  const config: Record<DeliveryStatus, { label: string; classes: string; icon: typeof CheckCircleIcon }> = {
    delivered: {
      label: 'Delivered',
      classes: 'bg-green-100 text-green-800',
      icon: CheckCircleIcon,
    },
    failed: {
      label: 'Failed',
      classes: 'bg-red-100 text-red-800',
      icon: XCircleIcon,
    },
    pending: {
      label: 'Pending',
      classes: 'bg-yellow-100 text-yellow-800',
      icon: ClockIcon,
    },
    retrying: {
      label: 'Retrying',
      classes: 'bg-orange-100 text-orange-800',
      icon: ArrowPathIcon,
    },
  };
  const { label, classes, icon: Icon } = config[status];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${classes}`}>
      <Icon className={`h-3 w-3 ${status === 'retrying' ? 'animate-spin' : ''}`} />
      {label}
    </span>
  );
}

// ─── Channel Badge ────────────────────────────────────────────────────────────

function ChannelBadge({ channel }: { channel: Channel }) {
  return channel === 'email' ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
      <EnvelopeIcon className="h-3 w-3" />
      Email
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
      <ChatBubbleLeftRightIcon className="h-3 w-3" />
      Slack
    </span>
  );
}

// ─── Template Detail Modal ────────────────────────────────────────────────────

function TemplateModal({
  template,
  onClose,
}: {
  template: NotificationTemplate;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between px-6 py-5 border-b border-gray-100">
          <div>
            <h2 className="text-base font-semibold text-gray-900">
              {TYPE_LABELS[template.type] ?? template.type}
            </h2>
            <div className="flex items-center gap-2 mt-1">
              <ChannelBadge channel={template.channel} />
              <span className="text-xs text-gray-400">
                Last updated {formatDateTime(template.lastUpdated)}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Subject */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Subject Template
            </p>
            <div className="rounded-xl bg-gray-50 border border-gray-200 px-4 py-3 font-mono text-sm text-gray-800">
              {template.subject}
            </div>
          </div>

          {/* Body Preview */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Body Preview
            </p>
            <div className="rounded-xl bg-gray-50 border border-gray-200 px-4 py-3 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
              {template.bodyPreview}
            </div>
          </div>

          {/* Placeholders */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Available Placeholders
            </p>
            <div className="flex flex-wrap gap-2">
              {template.placeholders.map((p) => (
                <code
                  key={p}
                  className="px-2.5 py-1 rounded-lg bg-primary-50 border border-primary-200/60 text-primary-700 text-xs font-mono"
                >
                  {`{{${p}}}`}
                </code>
              ))}
            </div>
          </div>
        </div>

        <div className="px-6 py-4 bg-gray-50 rounded-b-2xl border-t border-gray-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-xl hover:bg-white text-sm font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Send Notification Tab ────────────────────────────────────────────────────

function SendNotificationTab() {
  const [form, setForm] = useState<SendNotificationForm>(EMPTY_SEND_FORM);
  const [sent, setSent] = useState(false);

  const set = <K extends keyof SendNotificationForm>(
    field: K,
    value: SendNotificationForm[K]
  ) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setSent(false);
  };

  const sendMutation = useMutation({
    mutationFn: async (data: SendNotificationForm) => {
      let context: Record<string, string> = {};
      try {
        context = JSON.parse(data.contextVariables);
      } catch {
        // ignore JSON parse errors — send empty context
      }
      const channels: Channel[] = [];
      if (data.channels.email) channels.push('email');
      if (data.channels.slack) channels.push('slack');

      const res = await api.post('/notification-delivery/send', {
        notification_type: data.notificationType,
        recipient_email: data.recipientEmail,
        channels,
        context,
      });
      return res.data;
    },
    onSuccess: () => {
      setSent(true);
      setForm(EMPTY_SEND_FORM);
    },
    onError: () => {
      toast.error('Failed to send notification. Please try again.');
    },
  });

  const isValid =
    form.notificationType !== '' &&
    form.recipientEmail.trim() !== '' &&
    (form.channels.email || form.channels.slack);

  let contextJsonValid = true;
  try {
    JSON.parse(form.contextVariables);
  } catch {
    contextJsonValid = false;
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Success banner */}
      {sent && (
        <div className="flex items-center gap-3 rounded-xl bg-green-50/80 border border-green-200/60 px-4 py-3">
          <CheckCircleIcon className="h-5 w-5 text-green-600 flex-shrink-0" />
          <p className="text-sm text-green-700 font-medium">
            Notification sent successfully.
          </p>
          <button
            onClick={() => setSent(false)}
            className="ml-auto text-green-500 hover:text-green-700"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        </div>
      )}

      <Card>
        <CardHeader
          title="Send Notification"
          subtitle="Dispatch a notification to one or more channels"
        />
        <CardBody className="space-y-5">
          {/* Notification Type */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Notification Type <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <select
                value={form.notificationType}
                onChange={(e) =>
                  set('notificationType', e.target.value as NotificationType | '')
                }
                className="w-full appearance-none rounded-xl px-3.5 py-2.5 pr-10 text-sm bg-white/50 backdrop-blur-sm border border-white/40 focus:bg-white/70 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 text-gray-800 transition-all outline-none"
              >
                <option value="">Select notification type...</option>
                {NOTIFICATION_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <ChevronDownIcon className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            </div>
          </div>

          {/* Recipient Email */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Recipient Email <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              value={form.recipientEmail}
              onChange={(e) => set('recipientEmail', e.target.value)}
              placeholder="recipient@company.com"
              className="w-full rounded-xl px-3.5 py-2.5 text-sm bg-white/50 backdrop-blur-sm border border-white/40 focus:bg-white/70 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 placeholder-gray-400 transition-all outline-none"
            />
          </div>

          {/* Channels */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Channels <span className="text-red-500">*</span>
            </label>
            <div className="flex items-center gap-6">
              <label className="flex items-center gap-2.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={form.channels.email}
                  onChange={(e) =>
                    set('channels', { ...form.channels, email: e.target.checked })
                  }
                  className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="flex items-center gap-1.5 text-sm text-gray-700">
                  <EnvelopeIcon className="h-4 w-4 text-blue-500" />
                  Email
                </span>
              </label>
              <label className="flex items-center gap-2.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={form.channels.slack}
                  onChange={(e) =>
                    set('channels', { ...form.channels, slack: e.target.checked })
                  }
                  className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="flex items-center gap-1.5 text-sm text-gray-700">
                  <ChatBubbleLeftRightIcon className="h-4 w-4 text-purple-500" />
                  Slack
                </span>
              </label>
            </div>
            {!form.channels.email && !form.channels.slack && (
              <p className="text-xs text-red-500">At least one channel must be selected.</p>
            )}
          </div>

          {/* Context Variables */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Context Variables (JSON)
            </label>
            <textarea
              value={form.contextVariables}
              onChange={(e) => set('contextVariables', e.target.value)}
              rows={6}
              spellCheck={false}
              className={`w-full rounded-xl px-3.5 py-2.5 text-sm font-mono bg-gray-900 text-gray-100 border transition-all outline-none resize-y ${
                contextJsonValid
                  ? 'border-white/20 focus:border-primary-400 focus:ring-2 focus:ring-primary-100/30'
                  : 'border-red-400 focus:ring-2 focus:ring-red-100'
              }`}
            />
            {!contextJsonValid && (
              <p className="text-xs text-red-500">Invalid JSON — please fix before sending.</p>
            )}
            <p className="text-xs text-gray-400">
              Provide template placeholder values as a JSON object. Missing keys will use
              template defaults.
            </p>
          </div>

          {/* Submit */}
          <div className="flex justify-end pt-2">
            <button
              onClick={() => sendMutation.mutate(form)}
              disabled={!isValid || !contextJsonValid || sendMutation.isPending}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-xl text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sendMutation.isPending ? (
                <ArrowPathIcon className="h-4 w-4 animate-spin" />
              ) : (
                <PaperAirplaneIcon className="h-4 w-4" />
              )}
              {sendMutation.isPending ? 'Sending...' : 'Send Notification'}
            </button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

// ─── History Tab ──────────────────────────────────────────────────────────────

function HistoryTab() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const { data: historyData, isLoading } = useQuery<NotificationHistoryItem[]>({
    queryKey: ['notification-history'],
    queryFn: async () => {
      try {
        const res = await api.get('/notification-delivery/history');
        return res.data?.history ?? res.data ?? [];
      } catch {
        return [];
      }
    },
    staleTime: 30_000,
  });

  const history: NotificationHistoryItem[] = historyData ?? [];

  const filtered = history.filter((h) => {
    const matchesStatus = !statusFilter || h.status === statusFilter;
    const matchesChannel = !channelFilter || h.channel === channelFilter;
    return matchesStatus && matchesChannel;
  });

  const handleRetry = async (id: string) => {
    setRetryingId(id);
    try {
      await api.post('/notification-delivery/retry', { notification_id: id });
    } catch {
      toast.error('Failed to retry notification delivery.');
    } finally {
      setTimeout(() => {
        setRetryingId(null);
        queryClient.invalidateQueries({ queryKey: ['notification-history'] });
      }, 1200);
    }
  };

  if (isLoading) {
    return (
      <Card padding="none">
        <LoadingState message="Loading notification history..." />
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card padding="md">
        <div className="flex flex-wrap items-center gap-3">
          <div className="w-44">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full rounded-xl px-3 py-2 text-sm bg-white/50 border border-white/40 text-gray-700 outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100 transition-all"
            >
              <option value="">All Statuses</option>
              <option value="delivered">Delivered</option>
              <option value="failed">Failed</option>
              <option value="pending">Pending</option>
              <option value="retrying">Retrying</option>
            </select>
          </div>
          <div className="w-36">
            <select
              value={channelFilter}
              onChange={(e) => setChannelFilter(e.target.value)}
              className="w-full rounded-xl px-3 py-2 text-sm bg-white/50 border border-white/40 text-gray-700 outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100 transition-all"
            >
              <option value="">All Channels</option>
              <option value="email">Email</option>
              <option value="slack">Slack</option>
            </select>
          </div>
          <span className="text-xs text-gray-400 ml-auto">
            {filtered.length} of {history.length} records
          </span>
        </div>
      </Card>

      {/* Table */}
      {filtered.length === 0 ? (
        <Card padding="none">
          <EmptyState
            icon={<BellIcon className="h-8 w-8" />}
            title="No notifications found"
            description="Try adjusting your filters."
          />
        </Card>
      ) : (
        <Card padding="none">
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-white/20">
                  {[
                    'Notification ID',
                    'Type',
                    'Recipient',
                    'Channel',
                    'Status',
                    'Sent At',
                    'Actions',
                  ].map((col) => (
                    <th
                      key={col}
                      className="px-4 py-3 text-left text-[10px] font-semibold text-gray-400 uppercase tracking-wider whitespace-nowrap"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {filtered.map((item) => (
                  <tr
                    key={item.id}
                    className="hover:bg-white/10 transition-colors group"
                  >
                    {/* ID */}
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-gray-500">{item.id}</span>
                    </td>

                    {/* Type */}
                    <td className="px-4 py-3">
                      <div className="text-xs font-medium text-gray-800 max-w-[160px]">
                        {TYPE_LABELS[item.type] ?? item.type}
                      </div>
                      {item.subject && (
                        <div
                          className="text-[10px] text-gray-400 truncate max-w-[200px]"
                          title={item.subject}
                        >
                          {item.subject}
                        </div>
                      )}
                    </td>

                    {/* Recipient */}
                    <td className="px-4 py-3">
                      <span className="text-xs text-gray-700">{item.recipient}</span>
                    </td>

                    {/* Channel */}
                    <td className="px-4 py-3">
                      <ChannelBadge channel={item.channel} />
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <DeliveryStatusBadge status={item.status} />
                        {item.errorMessage && (
                          <p
                            className="text-[10px] text-red-500 max-w-[180px] truncate"
                            title={item.errorMessage}
                          >
                            {item.errorMessage}
                          </p>
                        )}
                        {item.retryCount > 0 && (
                          <p className="text-[10px] text-gray-400">
                            {item.retryCount} retr{item.retryCount === 1 ? 'y' : 'ies'}
                          </p>
                        )}
                      </div>
                    </td>

                    {/* Sent At */}
                    <td className="px-4 py-3">
                      <div className="text-xs text-gray-700">{formatRelativeTime(item.sentAt)}</div>
                      <div className="text-[10px] text-gray-400">{formatDateTime(item.sentAt)}</div>
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3">
                      {(item.status === 'failed' || item.status === 'retrying') && (
                        <button
                          onClick={() => handleRetry(item.id)}
                          disabled={retryingId === item.id}
                          title="Retry delivery"
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-orange-200/60 bg-orange-50/80 text-orange-700 hover:bg-orange-100 transition-all disabled:opacity-50"
                        >
                          <ArrowPathIcon
                            className={`h-3 w-3 ${retryingId === item.id ? 'animate-spin' : ''}`}
                          />
                          {retryingId === item.id ? 'Retrying...' : 'Retry'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

// ─── Templates Tab ────────────────────────────────────────────────────────────

function TemplatesTab() {
  const [selectedTemplate, setSelectedTemplate] = useState<NotificationTemplate | null>(null);
  const [channelFilter, setChannelFilter] = useState('');
  const [typeSearch, setTypeSearch] = useState('');

  const { data: templatesData, isLoading } = useQuery<NotificationTemplate[]>({
    queryKey: ['notification-templates'],
    queryFn: async () => {
      try {
        const res = await api.get('/notification-delivery/templates');
        return res.data?.templates ?? res.data ?? [];
      } catch {
        return [];
      }
    },
    staleTime: 60_000,
  });

  const templates: NotificationTemplate[] = templatesData ?? [];

  const filtered = templates.filter((t) => {
    const matchesChannel = !channelFilter || t.channel === channelFilter;
    const matchesSearch =
      !typeSearch ||
      (TYPE_LABELS[t.type] ?? t.type).toLowerCase().includes(typeSearch.toLowerCase());
    return matchesChannel && matchesSearch;
  });

  if (isLoading) {
    return (
      <Card padding="none">
        <LoadingState message="Loading notification templates..." />
      </Card>
    );
  }

  return (
    <>
      <div className="space-y-4">
        {/* Filters */}
        <Card padding="md">
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              value={typeSearch}
              onChange={(e) => setTypeSearch(e.target.value)}
              placeholder="Search templates..."
              className="flex-1 min-w-[180px] rounded-xl px-3.5 py-2 text-sm bg-white/50 border border-white/40 text-gray-700 placeholder-gray-400 outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100 transition-all"
            />
            <div className="w-36">
              <select
                value={channelFilter}
                onChange={(e) => setChannelFilter(e.target.value)}
                className="w-full rounded-xl px-3 py-2 text-sm bg-white/50 border border-white/40 text-gray-700 outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100 transition-all"
              >
                <option value="">All Channels</option>
                <option value="email">Email</option>
                <option value="slack">Slack</option>
              </select>
            </div>
            <span className="text-xs text-gray-400 ml-auto">
              {filtered.length} template{filtered.length !== 1 ? 's' : ''}
            </span>
          </div>
        </Card>

        {/* Template cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((tpl) => (
            <div
              key={tpl.id}
              className="glass-card p-5 space-y-3 hover:shadow-lg transition-shadow"
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-gray-900">
                    {TYPE_LABELS[tpl.type] ?? tpl.type}
                  </h3>
                  <div className="flex items-center gap-2 mt-1">
                    <ChannelBadge channel={tpl.channel} />
                    <span className="text-[10px] text-gray-400">
                      Updated {formatDateTime(tpl.lastUpdated)}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedTemplate(tpl)}
                  className="p-1.5 rounded-lg hover:bg-white/40 text-gray-400 hover:text-primary-600 transition-colors flex-shrink-0"
                  title="View template"
                >
                  <EyeIcon className="h-4 w-4" />
                </button>
              </div>

              {/* Subject */}
              <div className="rounded-lg bg-gray-50/60 px-3 py-2">
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-0.5">
                  Subject
                </p>
                <p className="text-xs text-gray-700 font-mono truncate" title={tpl.subject}>
                  {tpl.subject}
                </p>
              </div>

              {/* Body preview */}
              <p className="text-xs text-gray-500 line-clamp-2">{tpl.bodyPreview}</p>

              {/* Placeholders */}
              <div className="flex flex-wrap gap-1.5">
                {tpl.placeholders.slice(0, 4).map((p) => (
                  <code
                    key={p}
                    className="px-1.5 py-0.5 rounded bg-primary-50 border border-primary-100 text-primary-600 text-[10px] font-mono"
                  >
                    {`{{${p}}}`}
                  </code>
                ))}
                {tpl.placeholders.length > 4 && (
                  <span className="text-[10px] text-gray-400 self-center">
                    +{tpl.placeholders.length - 4} more
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Template detail modal */}
      {selectedTemplate && (
        <TemplateModal
          template={selectedTemplate}
          onClose={() => setSelectedTemplate(null)}
        />
      )}
    </>
  );
}

// ─── Preferences Tab ──────────────────────────────────────────────────────────

function PreferencesTab() {
  const queryClient = useQueryClient();
  const userId = 'current-user';

  const { data: prefsData, isLoading } = useQuery<NotificationPreferences>({
    queryKey: ['notification-preferences', userId],
    queryFn: async () => {
      try {
        const res = await api.get(`/notification-delivery/preferences/${userId}`);
        return res.data?.preferences ?? res.data;
      } catch {
        return null;
      }
    },
    staleTime: 60_000,
  });

  const defaultPrefs: NotificationPreferences = {
    userId,
    emailEnabled: true,
    slackEnabled: false,
    slackChannel: '',
    disabledTypes: [],
  };

  const prefs: NotificationPreferences = prefsData ?? defaultPrefs;
  const [local, setLocal] = useState<NotificationPreferences>(prefs);
  const [saved, setSaved] = useState(false);

  // Sync local state when remote prefs load
  const [initialized, setInitialized] = useState(false);
  if (!initialized && prefsData) {
    setLocal(prefsData);
    setInitialized(true);
  }

  const updateMutation = useMutation({
    mutationFn: async (data: NotificationPreferences) => {
      const res = await api.put(`/notification-delivery/preferences/${userId}`, {
        email_enabled: data.emailEnabled,
        slack_enabled: data.slackEnabled,
        slack_channel: data.slackChannel,
        disabled_types: data.disabledTypes,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-preferences', userId] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
    onError: () => {
      toast.error('Failed to save notification preferences. Please try again.');
    },
  });

  const toggleDisabledType = (type: NotificationType) => {
    setLocal((prev) => ({
      ...prev,
      disabledTypes: prev.disabledTypes.includes(type)
        ? prev.disabledTypes.filter((t) => t !== type)
        : [...prev.disabledTypes, type],
    }));
    setSaved(false);
  };

  const ToggleSwitch = ({
    value,
    onChange,
    label,
    description,
  }: {
    value: boolean;
    onChange: (v: boolean) => void;
    label: string;
    description?: string;
  }) => (
    <div className="flex items-center justify-between gap-4 py-3">
      <div>
        <p className="text-sm font-medium text-gray-800">{label}</p>
        {description && <p className="text-xs text-gray-500 mt-0.5">{description}</p>}
      </div>
      <div
        role="checkbox"
        aria-checked={value}
        tabIndex={0}
        onClick={() => onChange(!value)}
        onKeyDown={(e) => e.key === ' ' && onChange(!value)}
        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-1 cursor-pointer flex-shrink-0 ${
          value ? 'bg-primary-500' : 'bg-gray-300'
        }`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform duration-200 ${
            value ? 'translate-x-4' : 'translate-x-0.5'
          }`}
        />
      </div>
    </div>
  );

  if (isLoading) {
    return (
      <Card padding="none">
        <LoadingState message="Loading preferences..." />
      </Card>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Save confirmation */}
      {saved && (
        <div className="flex items-center gap-3 rounded-xl bg-green-50/80 border border-green-200/60 px-4 py-3">
          <CheckCircleIcon className="h-5 w-5 text-green-600 flex-shrink-0" />
          <p className="text-sm text-green-700 font-medium">Preferences saved successfully.</p>
        </div>
      )}

      {/* Channel toggles */}
      <Card>
        <CardHeader
          title="Channel Settings"
          subtitle="Enable or disable notification channels globally"
        />
        <CardBody className="divide-y divide-white/20">
          <ToggleSwitch
            value={local.emailEnabled}
            onChange={(v) => { setLocal((p) => ({ ...p, emailEnabled: v })); setSaved(false); }}
            label="Email Notifications"
            description="Receive notifications via email to your registered address"
          />
          <ToggleSwitch
            value={local.slackEnabled}
            onChange={(v) => { setLocal((p) => ({ ...p, slackEnabled: v })); setSaved(false); }}
            label="Slack Notifications"
            description="Send notifications to a Slack channel or DM"
          />
          {local.slackEnabled && (
            <div className="py-3 space-y-1.5">
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Slack Channel
              </label>
              <input
                type="text"
                value={local.slackChannel}
                onChange={(e) => { setLocal((p) => ({ ...p, slackChannel: e.target.value })); setSaved(false); }}
                placeholder="#channel-name or @username"
                className="w-full rounded-xl px-3.5 py-2.5 text-sm bg-white/50 border border-white/40 focus:bg-white/70 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 placeholder-gray-400 transition-all outline-none"
              />
              <p className="text-xs text-gray-400">
                Use #channel-name for public channels or @username for direct messages.
              </p>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Notification type opt-outs */}
      <Card>
        <CardHeader
          title="Notification Type Preferences"
          subtitle="Uncheck types you do not want to receive. Security-critical alerts cannot be disabled."
        />
        <CardBody className="space-y-1">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
            {NOTIFICATION_TYPE_OPTIONS.map((opt) => {
              const isCritical =
                opt.value === 'risk_alert' ||
                opt.value === 'sod_violation' ||
                opt.value === 'policy_violation' ||
                opt.value === 'firefighter_session_started';
              const isDisabled = local.disabledTypes.includes(opt.value as NotificationType);

              return (
                <label
                  key={opt.value}
                  className={`flex items-center gap-2.5 py-2 cursor-pointer select-none group ${
                    isCritical ? 'cursor-not-allowed opacity-70' : ''
                  }`}
                  title={isCritical ? 'This notification type cannot be disabled' : undefined}
                >
                  <input
                    type="checkbox"
                    checked={!isDisabled}
                    disabled={isCritical}
                    onChange={() => {
                      if (!isCritical) toggleDisabledType(opt.value as NotificationType);
                    }}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 disabled:opacity-50"
                  />
                  <span className="text-sm text-gray-700 group-hover:text-gray-900 transition-colors">
                    {opt.label}
                  </span>
                  {isCritical && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 border border-red-100 text-red-500 font-medium">
                      Required
                    </span>
                  )}
                </label>
              );
            })}
          </div>
        </CardBody>
      </Card>

      {/* Save button */}
      <div className="flex justify-end">
        <button
          onClick={() => updateMutation.mutate(local)}
          disabled={updateMutation.isPending}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-600 text-white rounded-xl text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {updateMutation.isPending ? (
            <ArrowPathIcon className="h-4 w-4 animate-spin" />
          ) : (
            <CheckCircleIcon className="h-4 w-4" />
          )}
          {updateMutation.isPending ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

type Tab = 'send' | 'history' | 'templates' | 'preferences';

const TABS: { id: Tab; label: string; icon: typeof BellIcon }[] = [
  { id: 'send', label: 'Send Notification', icon: PaperAirplaneIcon },
  { id: 'history', label: 'History', icon: ClockIcon },
  { id: 'templates', label: 'Templates', icon: DocumentTextIcon },
  { id: 'preferences', label: 'Preferences', icon: Cog6ToothIcon },
];

export function NotificationCenter() {
  const [activeTab, setActiveTab] = useState<Tab>('send');

  // Stats query
  const { data: historyData } = useQuery<NotificationHistoryItem[]>({
    queryKey: ['notification-history'],
    queryFn: async () => {
      try {
        const res = await api.get('/notification-delivery/history');
        return res.data?.history ?? res.data ?? [];
      } catch {
        return [];
      }
    },
    staleTime: 30_000,
  });

  const history: NotificationHistoryItem[] = historyData ?? [];

  const stats = {
    total: history.length,
    delivered: history.filter((h) => h.status === 'delivered').length,
    failed: history.filter((h) => h.status === 'failed').length,
    retryPending: history.filter((h) => h.status === 'retrying' || h.status === 'pending').length,
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <PageHeader
        title="Notification Center"
        subtitle="Manage email and Slack notification configuration, delivery history, templates, and preferences"
        actions={
          <button
            onClick={() => setActiveTab('send')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-xl text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            <PaperAirplaneIcon className="h-4 w-4" />
            Send Notification
          </button>
        }
      />

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Sent"
          value={stats.total}
          icon={BellIcon}
          iconBgColor="stat-icon-blue"
          iconColor="text-blue-400"
        />
        <StatCard
          title="Delivered"
          value={stats.delivered}
          icon={CheckCircleIcon}
          iconBgColor="stat-icon-green"
          iconColor="text-green-400"
        />
        <StatCard
          title="Failed"
          value={stats.failed}
          icon={XCircleIcon}
          iconBgColor="stat-icon-red"
          iconColor="text-red-400"
        />
        <StatCard
          title="Retry Pending"
          value={stats.retryPending}
          icon={ArrowPathIcon}
          iconBgColor="stat-icon-yellow"
          iconColor="text-yellow-400"
        />
      </div>

      {/* Failed notifications alert */}
      {stats.failed > 0 && (
        <div className="flex items-center gap-3 rounded-xl bg-red-50/80 border border-red-200/60 px-4 py-3">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">
            <span className="font-semibold">{stats.failed}</span> notification
            {stats.failed !== 1 ? 's' : ''} failed to deliver.{' '}
            <button
              onClick={() => setActiveTab('history')}
              className="underline underline-offset-2 hover:text-red-800 transition-colors font-medium"
            >
              View in History
            </button>{' '}
            and retry failed deliveries.
          </p>
        </div>
      )}

      {/* Tab bar */}
      <div className="border-b border-white/20">
        <nav className="flex gap-1">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all -mb-px ${
                  isActive
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
                {tab.id === 'history' && stats.failed > 0 && (
                  <span className="ml-1 inline-flex items-center justify-center h-4 w-4 rounded-full bg-red-500 text-white text-[9px] font-bold">
                    {stats.failed > 9 ? '9+' : stats.failed}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab content */}
      <div className="min-h-[400px]">
        {activeTab === 'send' && <SendNotificationTab />}
        {activeTab === 'history' && <HistoryTab />}
        {activeTab === 'templates' && <TemplatesTab />}
        {activeTab === 'preferences' && <PreferencesTab />}
      </div>
    </div>
  );
}
