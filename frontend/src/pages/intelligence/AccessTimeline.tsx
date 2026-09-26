import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  MagnifyingGlassIcon,
  ArrowPathIcon,
  UserPlusIcon,
  UserMinusIcon,
  ArrowUpTrayIcon,
  AdjustmentsHorizontalIcon,
  LockClosedIcon,
  LockOpenIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
  Badge,
} from '../../components/ui';

// ── Types ──────────────────────────────────────────────────────────────────────

type EventType =
  | 'role_assigned'
  | 'role_removed'
  | 'transport_imported'
  | 'org_value_changed'
  | 'user_locked'
  | 'user_unlocked';

type ImpactType = 'access_gained' | 'access_lost' | 'access_modified';

interface TimelineEvent {
  id: string;
  timestamp: string;
  event_type: EventType;
  actor: string;
  action: string;
  detail: string;
  impact: ImpactType;
  subject: string;
}

interface InvestigateResult {
  user_id: string;
  transaction: string;
  date: string;
  root_cause: string;
  confidence: number;
  contributing_events: string[];
  remediation_steps: string[];
}

interface RecentChange {
  id: string;
  timestamp: string;
  type: string;
  subject: string;
  actor: string;
  summary: string;
  impact: ImpactType;
}

// ── Event type config ─────────────────────────────────────────────────────────

const EVENT_CONFIG: Record<
  EventType,
  { label: string; icon: React.FC<{ className?: string }>; color: string }
> = {
  role_assigned: { label: 'Role Assigned', icon: UserPlusIcon, color: 'text-emerald-600 bg-emerald-50 border-emerald-200' },
  role_removed: { label: 'Role Removed', icon: UserMinusIcon, color: 'text-red-600 bg-red-50 border-red-200' },
  transport_imported: { label: 'Transport Imported', icon: ArrowUpTrayIcon, color: 'text-blue-600 bg-blue-50 border-blue-200' },
  org_value_changed: { label: 'Org Value Changed', icon: AdjustmentsHorizontalIcon, color: 'text-amber-600 bg-amber-50 border-amber-200' },
  user_locked: { label: 'User Locked', icon: LockClosedIcon, color: 'text-red-600 bg-red-50 border-red-200' },
  user_unlocked: { label: 'User Unlocked', icon: LockOpenIcon, color: 'text-emerald-600 bg-emerald-50 border-emerald-200' },
};

const IMPACT_CONFIG: Record<ImpactType, { label: string; variant: 'success' | 'danger' | 'warning' }> = {
  access_gained: { label: 'Access Gained', variant: 'success' },
  access_lost: { label: 'Access Lost', variant: 'danger' },
  access_modified: { label: 'Access Modified', variant: 'warning' },
};

function formatTimestamp(ts: string): { date: string; time: string } {
  const d = new Date(ts);
  return {
    date: d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
    time: d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
  };
}

// ── Component ─────────────────────────────────────────────────────────────────

export function AccessTimeline() {
  const [searchId, setSearchId] = useState('');
  const [activeSubject, setActiveSubject] = useState('');
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);

  // Investigate panel state
  const [invUserId, setInvUserId] = useState('');
  const [invTransaction, setInvTransaction] = useState('');
  const [invDate, setInvDate] = useState('');
  const [investigateResult, setInvestigateResult] = useState<InvestigateResult | null>(null);

  // ── Recent changes query ──────────────────────────────────────────────────
  const { data: recentData, isLoading: recentLoading } = useQuery<RecentChange[]>({
    queryKey: ['timeline-recent'],
    queryFn: () => api.get('/timeline/recent').then((r) => r.data),
  });

  const recentChanges: RecentChange[] = recentData ?? [];

  // ── Timeline fetch (on demand) ────────────────────────────────────────────
  const handleSearch = async () => {
    if (!searchId.trim()) {
      toast.error('Enter a user ID or role ID');
      return;
    }
    setIsLoadingEvents(true);
    setActiveSubject(searchId.trim());
    try {
      const res = await api.get('/timeline/events', { params: { subject_id: searchId.trim() } });
      setEvents(res.data ?? []);
    } catch {
      setEvents([]);
      toast.error('Failed to load timeline data');
    } finally {
      setIsLoadingEvents(false);
    }
  };

  // ── Investigate mutation ──────────────────────────────────────────────────
  const investigateMutation = useMutation({
    mutationFn: (payload: { user_id: string; transaction: string; date: string }) =>
      api.post('/timeline/investigate', payload).then((r) => r.data as InvestigateResult),
    onSuccess: (data) => {
      setInvestigateResult(data);
      toast.success('Root cause analysis complete');
    },
    onError: () => {
      toast.error('Investigation failed');
    },
  });

  const handleInvestigate = () => {
    if (!invUserId.trim() || !invTransaction.trim() || !invDate) {
      toast.error('Fill in user ID, transaction, and date');
      return;
    }
    investigateMutation.mutate({ user_id: invUserId.trim(), transaction: invTransaction.trim(), date: invDate });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Access Timeline"
        subtitle="Visual history of access changes for users and roles"
        breadcrumbs={[{ label: 'Intelligence' }, { label: 'Access Timeline' }]}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Main timeline column ── */}
        <div className="lg:col-span-2 space-y-4">
          {/* Search bar */}
          <Card padding="md">
            <div className="flex gap-3">
              <div className="flex-1">
                <input
                  type="text"
                  placeholder="Enter User ID or Role ID (e.g. JSMITH, Z_FIN_AP_PROCESSOR)"
                  value={searchId}
                  onChange={(e) => setSearchId(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="w-full rounded-xl px-3.5 py-2.5 text-sm bg-white/50 backdrop-blur-sm border border-white/40 focus:bg-white/70 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 placeholder-gray-400 transition-all duration-200 outline-none"
                />
              </div>
              <Button
                onClick={handleSearch}
                loading={isLoadingEvents}
                icon={<MagnifyingGlassIcon className="h-4 w-4" />}
              >
                Search
              </Button>
            </div>
          </Card>

          {/* Timeline */}
          {isLoadingEvents ? (
            <Card>
              <div className="flex items-center justify-center py-16">
                <ArrowPathIcon className="h-8 w-8 animate-spin text-primary-500" />
              </div>
            </Card>
          ) : events.length > 0 ? (
            <Card padding="none">
              <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-gray-900">Access History</h2>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {events.length} events for <span className="font-medium text-gray-700">{activeSubject}</span>
                  </p>
                </div>
                <div className="flex gap-2">
                  <Badge variant="success" size="sm">
                    {events.filter((e) => e.impact === 'access_gained').length} gained
                  </Badge>
                  <Badge variant="danger" size="sm">
                    {events.filter((e) => e.impact === 'access_lost').length} lost
                  </Badge>
                  <Badge variant="warning" size="sm">
                    {events.filter((e) => e.impact === 'access_modified').length} modified
                  </Badge>
                </div>
              </div>

              <div className="p-6">
                <div className="relative">
                  {/* Vertical timeline line */}
                  <div className="absolute left-5 top-0 bottom-0 w-px bg-gray-200/60" />

                  <div className="space-y-6">
                    {events.map((event, _idx) => {
                      const cfg = EVENT_CONFIG[event.event_type];
                      const impactCfg = IMPACT_CONFIG[event.impact];
                      const EventIcon = cfg.icon;
                      const { date, time } = formatTimestamp(event.timestamp);
                      return (
                        <div key={event.id} className="flex gap-4">
                          {/* Icon bubble */}
                          <div
                            className={`relative z-10 flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center border ${cfg.color}`}
                          >
                            <EventIcon className="h-4 w-4" />
                          </div>

                          {/* Event card */}
                          <div className="flex-1 min-w-0">
                            <div className="glass-card p-4">
                              <div className="flex items-start justify-between gap-3 flex-wrap">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-xs font-semibold text-gray-700">{cfg.label}</span>
                                    <Badge variant={impactCfg.variant} size="sm">{impactCfg.label}</Badge>
                                  </div>
                                  <p className="mt-1.5 text-sm text-gray-800 leading-relaxed">{event.detail}</p>
                                  <div className="mt-2 flex items-center gap-3 text-xs text-gray-400">
                                    <span className="flex items-center gap-1">
                                      <ClockIcon className="h-3.5 w-3.5" />
                                      {date} at {time}
                                    </span>
                                    <span>Actor: <span className="font-medium text-gray-600">{event.actor}</span></span>
                                  </div>
                                </div>
                                <span className="text-xs text-gray-300 font-mono flex-shrink-0">{event.id}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </Card>
          ) : activeSubject ? (
            <Card>
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <ClockIcon className="h-10 w-10 text-gray-300 mb-3" />
                <p className="text-sm text-gray-500">No events found for <strong>{activeSubject}</strong></p>
              </div>
            </Card>
          ) : (
            <Card>
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <ClockIcon className="h-10 w-10 text-gray-300 mb-3" />
                <h3 className="text-sm font-medium text-gray-700 mb-1">Search for a User or Role</h3>
                <p className="text-xs text-gray-400 max-w-xs">
                  Enter a User ID or Role ID above to load the full access change history as a visual timeline.
                </p>
              </div>
            </Card>
          )}

          {/* Investigate panel */}
          <Card>
            <div className="px-6 py-4 border-b border-white/20">
              <h2 className="text-sm font-semibold text-gray-900">Investigate Access Loss</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Enter context to get AI-powered root cause analysis for a specific access issue
              </p>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1.5">User ID</label>
                  <input
                    type="text"
                    placeholder="e.g. JSMITH"
                    value={invUserId}
                    onChange={(e) => setInvUserId(e.target.value)}
                    className="w-full rounded-xl px-3.5 py-2.5 text-sm bg-white/50 backdrop-blur-sm border border-white/40 focus:bg-white/70 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 placeholder-gray-400 transition-all outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1.5">Transaction</label>
                  <input
                    type="text"
                    placeholder="e.g. FB50 or ME21N"
                    value={invTransaction}
                    onChange={(e) => setInvTransaction(e.target.value)}
                    className="w-full rounded-xl px-3.5 py-2.5 text-sm bg-white/50 backdrop-blur-sm border border-white/40 focus:bg-white/70 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 placeholder-gray-400 transition-all outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1.5">Issue Date</label>
                  <input
                    type="date"
                    value={invDate}
                    onChange={(e) => setInvDate(e.target.value)}
                    className="w-full rounded-xl px-3.5 py-2.5 text-sm bg-white/50 backdrop-blur-sm border border-white/40 focus:bg-white/70 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 transition-all outline-none"
                  />
                </div>
              </div>
              <Button
                onClick={handleInvestigate}
                loading={investigateMutation.isPending}
                icon={<MagnifyingGlassIcon className="h-4 w-4" />}
                variant="secondary"
              >
                Run Investigation
              </Button>

              {investigateResult && (
                <div className="mt-4 space-y-4 border-t border-white/20 pt-4">
                  {/* Root cause */}
                  <div className="p-3 bg-red-50/60 border border-red-200/60 rounded-xl">
                    <div className="flex items-center justify-between mb-1.5">
                      <p className="text-xs font-semibold text-red-700 uppercase tracking-wider">Root Cause</p>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs text-gray-500">Confidence</span>
                        <Badge variant={investigateResult.confidence >= 85 ? 'success' : 'warning'} size="sm">
                          {investigateResult.confidence}%
                        </Badge>
                      </div>
                    </div>
                    <p className="text-sm text-red-800 leading-relaxed">{investigateResult.root_cause}</p>
                  </div>

                  {/* Contributing events */}
                  <div>
                    <p className="text-xs font-medium text-gray-600 uppercase tracking-wider mb-2">Contributing Events</p>
                    <ul className="space-y-1.5">
                      {investigateResult.contributing_events.map((e, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                          <ExclamationTriangleIcon className="h-3.5 w-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                          {e}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Remediation steps */}
                  <div>
                    <p className="text-xs font-medium text-gray-600 uppercase tracking-wider mb-2">Remediation Steps</p>
                    <ol className="space-y-1.5">
                      {investigateResult.remediation_steps.map((s, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                          <CheckCircleIcon className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                          {s}
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* ── Right sidebar: Recent changes ── */}
        <div className="space-y-4">
          <Card padding="none">
            <div className="px-4 py-3 border-b border-white/20">
              <h2 className="text-sm font-semibold text-gray-900">Recent Changes</h2>
              <p className="text-xs text-gray-500 mt-0.5">Last 24 hours across all users and roles</p>
            </div>
            <div className="divide-y divide-gray-50/50 max-h-[600px] overflow-y-auto">
              {recentLoading ? (
                <div className="flex items-center justify-center py-10">
                  <ArrowPathIcon className="h-5 w-5 animate-spin text-primary-500" />
                </div>
              ) : (
                recentChanges.map((change) => {
                  const cfg = EVENT_CONFIG[change.type as EventType] ?? {
                    label: change.type,
                    icon: ClockIcon,
                    color: 'text-gray-500 bg-gray-50 border-gray-200',
                  };
                  const impactCfg = IMPACT_CONFIG[change.impact];
                  const ChangeIcon = cfg.icon;
                  const { date, time } = formatTimestamp(change.timestamp);
                  return (
                    <div key={change.id} className="px-4 py-3 hover:bg-white/30 transition-colors">
                      <div className="flex items-start gap-3">
                        <div className={`flex-shrink-0 h-7 w-7 rounded-full flex items-center justify-center border text-xs ${cfg.color}`}>
                          <ChangeIcon className="h-3.5 w-3.5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-xs font-semibold text-gray-700 truncate">{change.subject}</span>
                            <Badge variant={impactCfg.variant} size="sm">{impactCfg.label}</Badge>
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{change.summary}</p>
                          <p className="text-xs text-gray-400 mt-1">{date} {time}</p>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </Card>

          {/* Change summary */}
          <Card>
            <div className="px-4 py-3 border-b border-white/20">
              <h2 className="text-sm font-semibold text-gray-900">24h Summary</h2>
            </div>
            <div className="p-4 space-y-3">
              {[
                { label: 'Roles Assigned', value: recentChanges.filter((c) => c.type === 'role_assigned').length, color: 'text-emerald-600' },
                { label: 'Roles Removed', value: recentChanges.filter((c) => c.type === 'role_removed').length, color: 'text-red-600' },
                { label: 'Transports Imported', value: recentChanges.filter((c) => c.type === 'transport_imported').length, color: 'text-blue-600' },
                { label: 'Org Changes', value: recentChanges.filter((c) => c.type === 'org_value_changed').length, color: 'text-amber-600' },
                { label: 'User Lock/Unlock', value: recentChanges.filter((c) => c.type === 'user_locked' || c.type === 'user_unlocked').length, color: 'text-gray-600' },
              ].map((row) => (
                <div key={row.label} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">{row.label}</span>
                  <span className={`font-semibold ${row.color}`}>{row.value}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
