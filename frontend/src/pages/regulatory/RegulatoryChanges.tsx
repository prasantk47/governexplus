import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BuildingLibraryIcon, ExclamationTriangleIcon, CheckCircleIcon, PlusIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

const impactColors: Record<string, string> = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

const statusColors: Record<string, string> = {
  identified: 'bg-blue-100 text-blue-700',
  under_analysis: 'bg-purple-100 text-purple-700',
  action_required: 'bg-orange-100 text-orange-700',
  in_progress: 'bg-yellow-100 text-yellow-800',
  implemented: 'bg-green-100 text-green-700',
  deferred: 'bg-gray-100 text-gray-500',
};

export function RegulatoryChanges() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    title: '', regulation_name: '', jurisdiction: '', issuing_body: '',
    change_type: 'new_requirement', impact_level: 'medium',
    effective_date: '', compliance_deadline: '', assigned_owner: '',
  });

  const { data: statsData } = useQuery({
    queryKey: ['reg-change-stats'],
    queryFn: () => api.get('/regulatory-changes/summary/stats').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['regulatory-changes'],
    queryFn: () => api.get('/regulatory-changes').then(r => r.data),
    refetchInterval: 60000,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/regulatory-changes', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['regulatory-changes'] }); qc.invalidateQueries({ queryKey: ['reg-change-stats'] }); setShowCreate(false); },
  });

  const updateStatusMut = useMutation({
    mutationFn: ({ id, status }: any) => api.put(`/regulatory-changes/${id}`, { status }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['regulatory-changes'] }),
  });

  const stats = statsData || {};
  const changes = data?.changes || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Regulatory Change Management"
        subtitle="Track regulatory developments and ensure timely compliance implementation"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> Add Change
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Changes" value={stats.total ?? '—'} icon={BuildingLibraryIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Overdue" value={stats.overdue ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={stats.overdue > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Critical Impact" value={stats.critical_impact ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={stats.critical_impact > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Implemented" value={stats.by_status?.implemented ?? '—'} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
      </div>

      <Card>
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Regulatory Change Register</h2>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : changes.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No regulatory changes tracked</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead><tr className="border-b border-gray-100">
                {['Change', 'Regulation', 'Jurisdiction', 'Impact', 'Deadline', 'Status', 'Actions'].map(h => (
                  <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                ))}
              </tr></thead>
              <tbody className="divide-y divide-gray-50">
                {changes.map((c: any) => {
                  const isOverdue = c.compliance_deadline && new Date(c.compliance_deadline) < new Date() && c.status !== 'implemented';
                  return (
                    <tr key={c.change_id} className={isOverdue ? 'bg-red-50/20' : ''}>
                      <td className="py-2 pr-4">
                        <div className="text-xs font-medium text-gray-900">{c.title}</div>
                        <div className="text-xs text-gray-400">{c.change_type?.replace(/_/g, ' ')}</div>
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-600">{c.regulation_name || '—'}</td>
                      <td className="py-2 pr-4 text-xs text-gray-600">{c.jurisdiction || '—'}</td>
                      <td className="py-2 pr-4">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${impactColors[c.impact_level] || 'bg-gray-100 text-gray-500'}`}>
                          {c.impact_level}
                        </span>
                      </td>
                      <td className={`py-2 pr-4 text-xs ${isOverdue ? 'text-red-600 font-medium' : 'text-gray-600'}`}>
                        {c.compliance_deadline ? new Date(c.compliance_deadline).toLocaleDateString() : '—'}
                      </td>
                      <td className="py-2 pr-4">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[c.status] || 'bg-gray-100 text-gray-500'}`}>
                          {c.status?.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-2">
                        {c.status !== 'implemented' && (
                          <button onClick={() => updateStatusMut.mutate({ id: c.change_id, status: 'in_progress' })}
                            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">Progress</button>
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
            <h3 className="text-base font-semibold text-gray-900">Add Regulatory Change</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Regulation</label>
                  <input value={form.regulation_name} onChange={e => setForm(f => ({ ...f, regulation_name: e.target.value }))}
                    placeholder="e.g. DORA, Basel IV" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Jurisdiction</label>
                  <input value={form.jurisdiction} onChange={e => setForm(f => ({ ...f, jurisdiction: e.target.value }))}
                    placeholder="e.g. EU, US, UK" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Change Type</label>
                  <select value={form.change_type} onChange={e => setForm(f => ({ ...f, change_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['new_requirement', 'amendment', 'guidance', 'enforcement_action', 'repeal'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Impact Level</label>
                  <select value={form.impact_level} onChange={e => setForm(f => ({ ...f, impact_level: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['low', 'medium', 'high', 'critical'].map(l => <option key={l} value={l}>{l}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Effective Date</label>
                  <input type="date" value={form.effective_date} onChange={e => setForm(f => ({ ...f, effective_date: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Compliance Deadline</label>
                  <input type="date" value={form.compliance_deadline} onChange={e => setForm(f => ({ ...f, compliance_deadline: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate(form)}
                disabled={createMut.isPending || !form.title}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Adding…' : 'Add Change'}
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
