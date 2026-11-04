import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FlagIcon, CheckCircleIcon, ExclamationTriangleIcon, PlusIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface BusinessObjective {
  objective_id: string;
  title: string;
  description?: string;
  category: string;
  status: string;
  owner_id?: string;
  owner_name?: string;
  target_date?: string;
  linked_risk_ids?: string[];
  created_at: string;
}

const statusColors: Record<string, string> = {
  active: 'bg-blue-100 text-blue-700',
  achieved: 'bg-green-100 text-green-700',
  at_risk: 'bg-orange-100 text-orange-800',
  failed: 'bg-red-100 text-red-700',
};

const categoryColors: Record<string, string> = {
  strategic: 'bg-purple-100 text-purple-700',
  financial: 'bg-green-100 text-green-700',
  operational: 'bg-blue-100 text-blue-700',
  compliance: 'bg-yellow-100 text-yellow-800',
  growth: 'bg-indigo-100 text-indigo-700',
};

export function BusinessObjectives() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [linkingId, setLinkingId] = useState<string | null>(null);
  const [riskIdsInput, setRiskIdsInput] = useState('');
  const [form, setForm] = useState({
    title: '', description: '', category: 'strategic',
    owner_name: '', target_date: '',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['business-objectives'],
    queryFn: () => api.get('/risk-management/objectives').then(r => r.data),
    refetchInterval: 60000,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/risk-management/objectives', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['business-objectives'] }); setShowCreate(false); },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, ...body }: any) => api.put(`/risk-management/objectives/${id}`, body).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['business-objectives'] }),
  });

  const linkMut = useMutation({
    mutationFn: ({ id, risk_ids }: { id: string; risk_ids: string[] }) =>
      api.post(`/risk-management/objectives/${id}/link-risks`, { risk_ids }).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['business-objectives'] }); setLinkingId(null); },
  });

  const objectives: BusinessObjective[] = data?.objectives || [];
  const atRisk = objectives.filter(o => o.status === 'at_risk').length;
  const achieved = objectives.filter(o => o.status === 'achieved').length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Business Objectives"
        subtitle="Link enterprise risks to strategic business objectives"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> New Objective
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Objectives" value={objectives.length || '—'} icon={FlagIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="At Risk" value={atRisk || '—'} icon={ExclamationTriangleIcon} iconBgColor={atRisk > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Achieved" value={achieved || '—'} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Active" value={objectives.filter(o => o.status === 'active').length || '—'} icon={FlagIcon} iconBgColor="stat-icon-indigo" iconColor="" />
      </div>

      <Card>
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Objective Register</h2>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : objectives.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No objectives defined</div>
        ) : (
          <div className="space-y-3">
            {objectives.map(obj => (
              <div key={obj.objective_id} className="border border-gray-100 rounded-xl p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-gray-900">{obj.title}</span>
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${categoryColors[obj.category] || 'bg-gray-100 text-gray-600'}`}>
                        {obj.category}
                      </span>
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[obj.status] || 'bg-gray-100 text-gray-600'}`}>
                        {obj.status.replace(/_/g, ' ')}
                      </span>
                    </div>
                    {obj.description && <p className="text-xs text-gray-500 mt-1">{obj.description}</p>}
                    <div className="flex gap-4 mt-2 text-xs text-gray-500">
                      {obj.owner_name && <span>Owner: {obj.owner_name}</span>}
                      {obj.target_date && <span>Target: {new Date(obj.target_date).toLocaleDateString()}</span>}
                      {obj.linked_risk_ids?.length ? (
                        <span className="text-orange-600">{obj.linked_risk_ids.length} linked risk(s)</span>
                      ) : (
                        <span className="text-gray-400">No linked risks</span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2 ml-4">
                    <button onClick={() => setLinkingId(obj.objective_id)}
                      className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">Link Risks</button>
                    {obj.status === 'active' && (
                      <>
                        <button onClick={() => updateMut.mutate({ id: obj.objective_id, status: 'at_risk' })}
                          className="text-xs text-orange-600 hover:text-orange-800 font-medium">At Risk</button>
                        <button onClick={() => updateMut.mutate({ id: obj.objective_id, status: 'achieved' })}
                          className="text-xs text-green-600 hover:text-green-800 font-medium">Achieved</button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Link risks modal */}
      {linkingId && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Link Risks to Objective</h3>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Risk IDs (comma-separated)</label>
              <input value={riskIdsInput} onChange={e => setRiskIdsInput(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="RISK-001, RISK-002, ..." />
            </div>
            <div className="flex gap-3">
              <button onClick={() => linkMut.mutate({ id: linkingId, risk_ids: riskIdsInput.split(',').map(s => s.trim()).filter(Boolean) })}
                disabled={linkMut.isPending}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {linkMut.isPending ? 'Linking…' : 'Link Risks'}
              </button>
              <button onClick={() => setLinkingId(null)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">New Business Objective</h3>
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
                    {['strategic', 'financial', 'operational', 'compliance', 'growth'].map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Target Date</label>
                  <input type="date" value={form.target_date} onChange={e => setForm(f => ({ ...f, target_date: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Owner</label>
                <input value={form.owner_name} onChange={e => setForm(f => ({ ...f, owner_name: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate(form)} disabled={createMut.isPending || !form.title}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Creating…' : 'Create Objective'}
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
