import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ComputerDesktopIcon, ShieldCheckIcon, ClockIcon, PlusIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-500',
  submitted: 'bg-blue-100 text-blue-700',
  under_review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  implemented: 'bg-indigo-100 text-indigo-700',
  closed: 'bg-green-100 text-green-700',
  rolled_back: 'bg-orange-100 text-orange-700',
};

const riskColors: Record<string, string> = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

const nextStatus: Record<string, { label: string; status: string }> = {
  pending: { label: 'Approve', status: 'approved' },
  approved: { label: 'Mark Implemented', status: 'implemented' },
  implemented: { label: 'Close', status: 'closed' },
};

export function ITChangeRisk() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    title: '', description: '', change_type: 'standard',
    risk_level: 'medium', planned_date: '', requester: '',
    rollback_plan: '', change_reference: '',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['it-change-risks'],
    queryFn: () => api.get('/it-change-risk').then(r => r.data),
    refetchInterval: 60000,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/it-change-risk', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['it-change-risks'] }); setShowCreate(false); },
  });

  const transitionMut = useMutation({
    mutationFn: ({ id, status, ...body }: any) =>
      api.put(`/it-change-risk/${id}/transition`, { status, ...body }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['it-change-risks'] }),
  });

  const changes = data?.changes || [];
  const pending = changes.filter((c: any) => !['closed', 'rejected', 'rolled_back'].includes(c.status)).length;
  const highRisk = changes.filter((c: any) => ['high', 'critical'].includes(c.risk_level)).length;
  const rolledBack = changes.filter((c: any) => c.status === 'rolled_back').length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="IT Change Risk (ITGC)"
        subtitle="IT general controls — change risk assessment and approval workflow"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> New Change
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Changes" value={changes.length || '—'} icon={ComputerDesktopIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Pending Review" value={pending || '—'} icon={ClockIcon} iconBgColor={pending > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
        <StatCard title="High / Critical Risk" value={highRisk || '—'} icon={ShieldCheckIcon} iconBgColor={highRisk > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Rolled Back" value={rolledBack || '—'} icon={ShieldCheckIcon} iconBgColor={rolledBack > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
      </div>

      <Card>
        <h2 className="text-sm font-semibold text-gray-900 mb-4">IT Change Register</h2>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : changes.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No IT change risks tracked</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead><tr className="border-b border-gray-100">
                {['Change', 'Type', 'Risk Level', 'Planned', 'Requester', 'Status', 'Actions'].map(h => (
                  <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                ))}
              </tr></thead>
              <tbody className="divide-y divide-gray-50">
                {changes.map((c: any) => {
                  const next = nextStatus[c.status];
                  return (
                    <tr key={c.change_risk_id}>
                      <td className="py-2 pr-4">
                        <div className="text-xs font-medium text-gray-900">{c.title}</div>
                        <div className="text-xs text-gray-400">{c.change_reference || c.change_risk_id}</div>
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-600 capitalize">{c.change_type?.replace(/_/g, ' ')}</td>
                      <td className="py-2 pr-4">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${riskColors[c.risk_level] || 'bg-gray-100 text-gray-500'}`}>
                          {c.risk_level}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-600">{c.planned_date ? new Date(c.planned_date).toLocaleDateString() : '—'}</td>
                      <td className="py-2 pr-4 text-xs text-gray-600">{c.requester || '—'}</td>
                      <td className="py-2 pr-4">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[c.status] || 'bg-gray-100 text-gray-500'}`}>
                          {c.status?.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-2">
                        {next && (
                          <button onClick={() => transitionMut.mutate({ id: c.change_risk_id, status: next.status })}
                            disabled={transitionMut.isPending}
                            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">{next.label}</button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">New IT Change Risk Assessment</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Change Type</label>
                  <select value={form.change_type} onChange={e => setForm(f => ({ ...f, change_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['standard', 'emergency', 'normal', 'major', 'minor'].map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Risk Level</label>
                  <select value={form.risk_level} onChange={e => setForm(f => ({ ...f, risk_level: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['low', 'medium', 'high', 'critical'].map(l => <option key={l} value={l}>{l}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Planned Date</label>
                  <input type="date" value={form.planned_date} onChange={e => setForm(f => ({ ...f, planned_date: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Requester</label>
                  <input value={form.requester} onChange={e => setForm(f => ({ ...f, requester: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Rollback Plan</label>
                <textarea value={form.rollback_plan} onChange={e => setForm(f => ({ ...f, rollback_plan: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Describe rollback procedure..." />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate(form)}
                disabled={createMut.isPending || !form.title}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Creating…' : 'Create Change'}
              </button>
              <button onClick={() => setShowCreate(false)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
