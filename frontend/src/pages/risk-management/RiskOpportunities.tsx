import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SparklesIcon, CheckCircleIcon, PlusIcon, ArrowTrendingUpIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface Opportunity {
  opportunity_id: string;
  title: string;
  description?: string;
  category: string;
  status: string;
  owner_name?: string;
  probability?: number;
  potential_benefit?: number;
  estimated_value?: number;
  target_date?: string;
  linked_risk_ids?: string[];
  created_at: string;
}

const statusColors: Record<string, string> = {
  identified: 'bg-blue-100 text-blue-700',
  evaluating: 'bg-yellow-100 text-yellow-800',
  pursuing: 'bg-indigo-100 text-indigo-700',
  realized: 'bg-green-100 text-green-700',
  declined: 'bg-gray-100 text-gray-500',
};

const categoryColors: Record<string, string> = {
  strategic: 'bg-purple-100 text-purple-700',
  financial: 'bg-green-100 text-green-700',
  operational: 'bg-blue-100 text-blue-700',
  innovation: 'bg-indigo-100 text-indigo-700',
  market: 'bg-orange-100 text-orange-800',
};

export function RiskOpportunities() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    title: '', description: '', category: 'strategic', owner_name: '',
    probability: '50', potential_benefit: '', target_date: '',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['risk-opportunities'],
    queryFn: () => api.get('/risk-management/opportunities').then(r => r.data),
    refetchInterval: 60000,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/risk-management/opportunities', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['risk-opportunities'] }); setShowCreate(false); },
  });

  const realizeMut = useMutation({
    mutationFn: (id: string) => api.put(`/risk-management/opportunities/${id}/realize`, {}).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['risk-opportunities'] }),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.put(`/risk-management/opportunities/${id}`, { status }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['risk-opportunities'] }),
  });

  const opps: Opportunity[] = data?.opportunities || [];
  const realized = opps.filter(o => o.status === 'realized').length;
  const pursuing = opps.filter(o => o.status === 'pursuing').length;
  const totalValue = opps.filter(o => o.estimated_value).reduce((s, o) => s + (o.estimated_value || 0), 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Opportunities"
        subtitle="Positive risk tracking — opportunities to create value from uncertainty"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> New Opportunity
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total" value={opps.length || '—'} icon={SparklesIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Pursuing" value={pursuing || '—'} icon={ArrowTrendingUpIcon} iconBgColor="stat-icon-indigo" iconColor="" />
        <StatCard title="Realized" value={realized || '—'} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Est. Value" value={totalValue > 0 ? `$${(totalValue / 1000).toFixed(0)}K` : '—'} icon={SparklesIcon} iconBgColor="stat-icon-green" iconColor="" />
      </div>

      <Card>
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Opportunity Register</h2>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : opps.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No opportunities identified</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Title', 'Category', 'Status', 'Probability', 'Est. Value', 'Owner', 'Target Date', 'Actions'].map(h => (
                    <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {opps.map(o => (
                  <tr key={o.opportunity_id}>
                    <td className="py-2 pr-4 max-w-[200px]">
                      <div className="font-medium text-gray-900 truncate">{o.title}</div>
                      <div className="text-xs text-gray-400">{o.opportunity_id}</div>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${categoryColors[o.category] || 'bg-gray-100 text-gray-600'}`}>
                        {o.category}
                      </span>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[o.status] || 'bg-gray-100 text-gray-600'}`}>
                        {o.status}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600">{o.probability != null ? `${o.probability}%` : '—'}</td>
                    <td className="py-2 pr-4 text-xs text-gray-600">
                      {o.estimated_value ? `$${(o.estimated_value / 1000).toFixed(0)}K` : '—'}
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600">{o.owner_name || '—'}</td>
                    <td className="py-2 pr-4 text-xs text-gray-600">
                      {o.target_date ? new Date(o.target_date).toLocaleDateString() : '—'}
                    </td>
                    <td className="py-2">
                      <div className="flex gap-2">
                        {o.status === 'identified' && (
                          <button onClick={() => updateMut.mutate({ id: o.opportunity_id, status: 'pursuing' })}
                            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">Pursue</button>
                        )}
                        {o.status === 'pursuing' && (
                          <button onClick={() => realizeMut.mutate(o.opportunity_id)}
                            className="text-xs text-green-600 hover:text-green-800 font-medium">Realize</button>
                        )}
                        {!['realized', 'declined'].includes(o.status) && (
                          <button onClick={() => updateMut.mutate({ id: o.opportunity_id, status: 'declined' })}
                            className="text-xs text-gray-500 hover:text-gray-700 font-medium">Decline</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">New Risk Opportunity</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Category</label>
                  <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['strategic', 'financial', 'operational', 'innovation', 'market'].map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Probability %</label>
                  <input type="number" min="0" max="100" value={form.probability}
                    onChange={e => setForm(f => ({ ...f, probability: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Est. Value (USD)</label>
                  <input type="number" value={form.potential_benefit}
                    onChange={e => setForm(f => ({ ...f, potential_benefit: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="0" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Target Date</label>
                  <input type="date" value={form.target_date}
                    onChange={e => setForm(f => ({ ...f, target_date: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Owner</label>
                <input value={form.owner_name} onChange={e => setForm(f => ({ ...f, owner_name: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate({ ...form, probability: parseInt(form.probability), potential_benefit: form.potential_benefit ? parseFloat(form.potential_benefit) : undefined })}
                disabled={createMut.isPending || !form.title}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Creating…' : 'Create Opportunity'}
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
