import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ClipboardDocumentCheckIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { PageHeader, Card, Button, Badge } from '../../components/ui';
import { firefighterApi } from '../../services/api';

interface FFID {
  ffid: string;
  description: string;
  target_system: string;
  emergency_function: string;
  region: string;
  owner_name: string;
  owner_id: string;
  controller_name: string;
  controller_id: string;
  risk_level: string;
  certification_status: string;
  next_certification_due: string | null;
  last_certification_date: string | null;
  last_certified_by: string;
  certification_frequency_days: number;
}

export function FFIDCertification() {
  const queryClient = useQueryClient();
  const [decisions, setDecisions] = useState<Record<string, { decision: string; notes: string }>>({});
  const [submitting, setSubmitting] = useState<string | null>(null);
  const certifier = localStorage.getItem('userId') || 'admin';

  const { data: raw, isLoading } = useQuery({
    queryKey: ['ffid-certification-due'],
    queryFn: () => firefighterApi.getCertificationDue().then(r => r.data),
  });

  const { data: allRaw } = useQuery({
    queryKey: ['ffid-all-cert'],
    queryFn: () => firefighterApi.listFirefighters().then(r => r.data),
  });

  const dueFFIDs: FFID[] = Array.isArray(raw) ? raw : (raw as any)?.ffids || [];
  const allFFIDs: FFID[] = Array.isArray(allRaw) ? allRaw : (allRaw as any)?.firefighter_ids || [];

  const certified = allFFIDs.filter(f => f.certification_status === 'current');

  const certifyMutation = useMutation({
    mutationFn: ({ ffid, decision, notes }: { ffid: string; decision: string; notes: string }) =>
      firefighterApi.certifyFFID(ffid, { certified_by: certifier, decision, notes }),
    onSuccess: (_, vars) => {
      toast.success(`FFID ${vars.ffid} ${vars.decision === 'retain' ? 'retained' : 'removed'}`);
      queryClient.invalidateQueries({ queryKey: ['ffid-certification-due'] });
      queryClient.invalidateQueries({ queryKey: ['ffid-all-cert'] });
      queryClient.invalidateQueries({ queryKey: ['ffid-registry'] });
      setDecisions(prev => { const n = { ...prev }; delete n[vars.ffid]; return n; });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Certification failed'),
  });

  const handleSubmit = async (ffid: string) => {
    const d = decisions[ffid];
    if (!d?.decision) {
      toast.error('Select retain or remove before submitting');
      return;
    }
    setSubmitting(ffid);
    try {
      await certifyMutation.mutateAsync({ ffid, decision: d.decision, notes: d.notes || '' });
    } finally {
      setSubmitting(null);
    }
  };

  const setDecision = (ffid: string, decision: string, notes: string = '') => {
    setDecisions(prev => ({ ...prev, [ffid]: { decision, notes: prev[ffid]?.notes || notes } }));
  };

  const riskColors: Record<string, string> = {
    low: 'text-green-700', medium: 'text-yellow-700', high: 'text-orange-700', critical: 'text-red-700',
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="FFID Certification"
        subtitle="Periodic access review — retain or remove firefighter ID assignments"
      />

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Due / Overdue', value: dueFFIDs.length, color: dueFFIDs.length > 0 ? 'text-red-600' : 'text-green-600', icon: ClockIcon },
          { label: 'Certified (Current)', value: certified.length, color: 'text-green-600', icon: CheckCircleIcon },
          { label: 'Total FFIDs', value: allFFIDs.length, color: 'text-gray-700', icon: ClipboardDocumentCheckIcon },
        ].map(s => (
          <Card key={s.label}>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-gray-100 flex items-center justify-center">
                <s.icon className="h-5 w-5 text-gray-500" />
              </div>
              <div>
                <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                <div className="text-xs text-gray-500">{s.label}</div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Due / Overdue FFIDs */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <ExclamationTriangleIcon className="h-4 w-4 text-orange-500" />
          <h2 className="text-sm font-semibold text-gray-900">FFIDs Requiring Certification</h2>
          {dueFFIDs.length > 0 && (
            <Badge variant="warning" size="sm">{dueFFIDs.length} due</Badge>
          )}
        </div>

        {isLoading ? (
          <div className="text-sm text-gray-400 py-8 text-center">Loading...</div>
        ) : dueFFIDs.length === 0 ? (
          <div className="text-center py-10">
            <CheckCircleIcon className="h-10 w-10 text-green-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-gray-700">All FFIDs are certified and current</p>
            <p className="text-xs text-gray-400 mt-1">Next review cycle will be triggered automatically</p>
          </div>
        ) : (
          <div className="space-y-4">
            {dueFFIDs.map(f => {
              const d = decisions[f.ffid];
              const isOverdue = f.certification_status === 'overdue' || f.certification_status === 'never';
              return (
                <div
                  key={f.ffid}
                  className={`border rounded-xl p-4 ${isOverdue ? 'border-red-200 bg-red-50/40' : 'border-yellow-200 bg-yellow-50/40'}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono font-semibold text-indigo-700 text-sm">{f.ffid}</span>
                        <Badge variant={isOverdue ? 'danger' : 'warning'} size="sm">
                          {f.certification_status === 'never' ? 'Never Certified' : f.certification_status}
                        </Badge>
                        <span className={`text-xs font-medium ${riskColors[f.risk_level] || 'text-gray-600'}`}>
                          {f.risk_level} risk
                        </span>
                      </div>
                      <p className="text-xs text-gray-600 mb-2">{f.description}</p>
                      <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-gray-500">
                        <span>Function: <span className="text-gray-700">{f.emergency_function}</span></span>
                        <span>System: <span className="text-gray-700">{f.target_system}</span></span>
                        <span>Owner: <span className="text-gray-700">{f.owner_name || f.owner_id || '—'}</span></span>
                        <span>Controller: <span className="text-gray-700">{f.controller_name || f.controller_id || '—'}</span></span>
                        <span>Region: <span className="text-gray-700">{f.region || '—'}</span></span>
                        <span>Last certified: <span className="text-gray-700">{f.last_certification_date || 'Never'}</span></span>
                      </div>
                    </div>

                    {/* Decision */}
                    <div className="flex-shrink-0 space-y-2 min-w-48">
                      <div className="flex gap-2">
                        <button
                          onClick={() => setDecision(f.ffid, 'retain')}
                          className={`flex-1 flex items-center justify-center gap-1 py-1.5 px-3 rounded-lg text-xs font-medium border transition-colors ${d?.decision === 'retain' ? 'bg-green-600 text-white border-green-600' : 'border-gray-200 text-gray-600 hover:border-green-400 hover:text-green-700'}`}
                        >
                          <CheckCircleIcon className="h-3.5 w-3.5" />
                          Retain
                        </button>
                        <button
                          onClick={() => setDecision(f.ffid, 'remove')}
                          className={`flex-1 flex items-center justify-center gap-1 py-1.5 px-3 rounded-lg text-xs font-medium border transition-colors ${d?.decision === 'remove' ? 'bg-red-600 text-white border-red-600' : 'border-gray-200 text-gray-600 hover:border-red-400 hover:text-red-700'}`}
                        >
                          <XCircleIcon className="h-3.5 w-3.5" />
                          Remove
                        </button>
                      </div>
                      {d?.decision && (
                        <>
                          <textarea
                            rows={2}
                            className="w-full text-xs border border-gray-200 rounded-lg px-2 py-1.5 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            placeholder="Notes (optional)"
                            value={d.notes}
                            onChange={e => setDecisions(prev => ({ ...prev, [f.ffid]: { ...prev[f.ffid], notes: e.target.value } }))}
                          />
                          <Button
                            size="sm"
                            onClick={() => handleSubmit(f.ffid)}
                            disabled={submitting === f.ffid}
                            className="w-full text-xs"
                          >
                            {submitting === f.ffid ? 'Submitting...' : 'Submit Decision'}
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* Certified FFIDs */}
      {certified.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <CheckCircleIcon className="h-4 w-4 text-green-500" />
            Certified &amp; Current
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/20">
                  <th className="pb-2 text-left text-xs text-gray-500">FFID</th>
                  <th className="pb-2 text-left text-xs text-gray-500">Region</th>
                  <th className="pb-2 text-left text-xs text-gray-500">Last Certified</th>
                  <th className="pb-2 text-left text-xs text-gray-500">Certified By</th>
                  <th className="pb-2 text-left text-xs text-gray-500">Next Due</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {certified.map(f => (
                  <tr key={f.ffid} className="text-xs">
                    <td className="py-2 font-mono font-semibold text-indigo-700">{f.ffid}</td>
                    <td className="py-2 text-gray-600">{f.region || '—'}</td>
                    <td className="py-2 text-gray-600">{f.last_certification_date || '—'}</td>
                    <td className="py-2 text-gray-600">{f.last_certified_by || '—'}</td>
                    <td className="py-2 text-gray-600">{f.next_certification_due || '—'}</td>
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
