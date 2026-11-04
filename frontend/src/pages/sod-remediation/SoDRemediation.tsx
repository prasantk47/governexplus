import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { WrenchScrewdriverIcon, ClockIcon, CheckCircleIcon, PlusIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

const statusColors: Record<string, string> = {
  open: 'bg-blue-100 text-blue-700',
  in_remediation: 'bg-yellow-100 text-yellow-800',
  pending_validation: 'bg-purple-100 text-purple-700',
  validated: 'bg-green-100 text-green-700',
  accepted_risk: 'bg-orange-100 text-orange-700',
  closed: 'bg-gray-100 text-gray-500',
};

const priorityColors: Record<string, string> = {
  low: 'text-gray-500',
  medium: 'text-yellow-600',
  high: 'text-orange-600',
  critical: 'text-red-600',
};

const nextStatus: Record<string, string> = {
  open: 'in_remediation',
  in_remediation: 'pending_validation',
  pending_validation: 'validated',
  validated: 'closed',
};

export function SoDRemediation() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    violation_id: '', user_id: '', rule_id: '',
    remediation_type: 'role_removal', assigned_to: '',
    due_date: '', priority: 'medium',
  });

  const { data: statsData } = useQuery({
    queryKey: ['sod-remediation-stats'],
    queryFn: () => api.get('/sod-remediation/summary/stats').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['sod-remediations'],
    queryFn: () => api.get('/sod-remediation').then(r => r.data),
    refetchInterval: 60000,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/sod-remediation', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sod-remediations'] }); qc.invalidateQueries({ queryKey: ['sod-remediation-stats'] }); setShowCreate(false); },
  });

  const transitionMut = useMutation({
    mutationFn: ({ id, status, ...body }: any) =>
      api.put(`/sod-remediation/${id}/transition`, { status, ...body }).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sod-remediations'] }); qc.invalidateQueries({ queryKey: ['sod-remediation-stats'] }); },
  });

  const stats = statsData || {};
  const remediations = data?.remediations || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="SoD Remediation"
        subtitle="End-to-end SoD violation remediation lifecycle management"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> New Remediation
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Open" value={stats.open ?? '—'} icon={WrenchScrewdriverIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="In Remediation" value={stats.in_remediation ?? '—'} icon={WrenchScrewdriverIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Pending Validation" value={stats.pending_validation ?? '—'} icon={ClockIcon} iconBgColor="stat-icon-purple" iconColor="" />
        <StatCard title="Overdue" value={stats.overdue ?? '—'} icon={ClockIcon} iconBgColor={stats.overdue > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
      </div>

      <Card>
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Remediation Workflow</h2>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : remediations.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No SoD remediations in progress</div>
        ) : (
          <div className="space-y-3">
            {remediations.map((r: any) => {
              const isOverdue = r.due_date && new Date(r.due_date) < new Date() && r.status !== 'closed';
              const next = nextStatus[r.status];
              return (
                <div key={r.remediation_id} className={`flex items-center justify-between p-3 border rounded-xl ${isOverdue ? 'border-red-200 bg-red-50/20' : 'border-gray-100'}`}>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[r.status] || 'bg-gray-100 text-gray-500'}`}>
                        {r.status?.replace(/_/g, ' ')}
                      </span>
                      <span className={`text-xs font-semibold uppercase ${priorityColors[r.priority] || 'text-gray-500'}`}>{r.priority}</span>
                    </div>
                    <div className="text-xs text-gray-900 font-medium mt-1">
                      Violation: {r.violation_id || r.remediation_id} · User: {r.user_id || '—'}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      Type: {r.remediation_type?.replace(/_/g, ' ')} · Owner: {r.assigned_to || 'Unassigned'}
                      {r.due_date && <span className={` · Due: ${new Date(r.due_date).toLocaleDateString()} ${isOverdue ? '(OVERDUE)' : ''}`}></span>}
                    </div>
                  </div>
                  {next && (
                    <button onClick={() => transitionMut.mutate({ id: r.remediation_id, status: next })}
                      disabled={transitionMut.isPending}
                      className="text-xs text-indigo-600 hover:text-indigo-800 font-medium whitespace-nowrap">
                      → {next.replace(/_/g, ' ')}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">New SoD Remediation</h3>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Violation ID</label>
                  <input value={form.violation_id} onChange={e => setForm(f => ({ ...f, violation_id: e.target.value }))}
                    placeholder="e.g. RISKV-001" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">User ID</label>
                  <input value={form.user_id} onChange={e => setForm(f => ({ ...f, user_id: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Remediation Type</label>
                  <select value={form.remediation_type} onChange={e => setForm(f => ({ ...f, remediation_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['role_removal', 'role_redesign', 'compensating_control', 'org_change', 'accepted_risk'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Priority</label>
                  <select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['low', 'medium', 'high', 'critical'].map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Assigned To</label>
                  <input value={form.assigned_to} onChange={e => setForm(f => ({ ...f, assigned_to: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Due Date</label>
                  <input type="date" value={form.due_date} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate(form)}
                disabled={createMut.isPending}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Creating…' : 'Create Remediation'}
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
