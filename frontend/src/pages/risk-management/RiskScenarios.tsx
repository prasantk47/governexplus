import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BeakerIcon, ChartBarIcon, PlusIcon, ExclamationTriangleIcon, ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface Scenario {
  scenario_id: string;
  title: string;
  scenario_type: string;
  velocity: string;
  status: string;
  owner_name?: string;
  inherent_likelihood?: number;
  inherent_impact?: number;
  inherent_score?: number;
  residual_score?: number;
  linked_risk_ids?: string[];
  created_at: string;
}

interface Simulation {
  simulation_id: string;
  scenario_id: string;
  iterations: number;
  mean_loss: number;
  p95_loss: number;
  p99_loss: number;
  max_loss: number;
  min_loss: number;
  created_at: string;
}

const typeColors: Record<string, string> = {
  single_event: 'bg-blue-100 text-blue-700',
  cascading: 'bg-orange-100 text-orange-800',
  compound: 'bg-purple-100 text-purple-700',
  stress_test: 'bg-red-100 text-red-700',
};

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600',
  active: 'bg-green-100 text-green-700',
  archived: 'bg-gray-100 text-gray-400',
};

export function RiskScenarios() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: '', description: '', scenario_type: 'single_event',
    velocity: 'moderate', owner_name: '',
    inherent_likelihood: '3', inherent_impact: '3',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['risk-scenarios'],
    queryFn: () => api.get('/risk-management/scenarios').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data: simData } = useQuery({
    queryKey: ['scenario-simulations', selectedId],
    queryFn: () => selectedId
      ? api.get(`/risk-management/scenarios/${selectedId}/simulations`).then(r => r.data)
      : Promise.resolve(null),
    enabled: !!selectedId,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/risk-management/scenarios', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['risk-scenarios'] }); setShowCreate(false); },
  });

  const simulateMut = useMutation({
    mutationFn: (id: string) => api.post(`/risk-management/scenarios/${id}/simulate`, { iterations: 10000 }).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['scenario-simulations', selectedId] }); },
  });

  const scenarios: Scenario[] = data?.scenarios || [];
  const totalActive = scenarios.filter(s => s.status === 'active').length;
  const latestSim: Simulation | null = simData?.simulations?.[0] || null;

  const fmt = (v?: number) => v != null ? `$${(v / 1000).toFixed(0)}K` : '—';

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Scenarios & Monte Carlo"
        subtitle="Cascading scenario modeling with quantitative loss simulation"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> New Scenario
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <StatCard title="Total Scenarios" value={scenarios.length || '—'} icon={BeakerIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Active" value={totalActive || '—'} icon={ExclamationTriangleIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Stress Tests" value={scenarios.filter(s => s.scenario_type === 'stress_test').length || '—'} icon={ChartBarIcon} iconBgColor="stat-icon-red" iconColor="" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scenario list */}
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Scenarios</h2>
          {isLoading ? (
            <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
          ) : scenarios.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-8">No scenarios defined</div>
          ) : (
            <div className="space-y-2">
              {scenarios.map(s => (
                <div key={s.scenario_id}
                  onClick={() => setSelectedId(s.scenario_id)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${selectedId === s.scenario_id ? 'border-indigo-400 bg-indigo-50' : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{s.title}</div>
                      <div className="flex gap-2 mt-1">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${typeColors[s.scenario_type] || 'bg-gray-100 text-gray-600'}`}>
                          {s.scenario_type.replace(/_/g, ' ')}
                        </span>
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[s.status] || 'bg-gray-100 text-gray-600'}`}>
                          {s.status}
                        </span>
                      </div>
                    </div>
                    {s.inherent_score != null && (
                      <span className="text-sm font-bold text-orange-600">{s.inherent_score.toFixed(1)}</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-gray-500 capitalize">Velocity: {s.velocity}</span>
                    <button onClick={e => { e.stopPropagation(); setSelectedId(s.scenario_id); simulateMut.mutate(s.scenario_id); }}
                      className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                      <ArrowPathIcon className="h-3 w-3" /> Simulate
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Monte Carlo results */}
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <BeakerIcon className="h-4 w-4 text-indigo-500" />
            Monte Carlo Simulation Results
          </h2>
          {!selectedId ? (
            <div className="text-xs text-gray-400 text-center py-8">Select a scenario to view simulation results</div>
          ) : simulateMut.isPending ? (
            <div className="text-xs text-gray-400 text-center py-8">Running simulation (10,000 iterations)...</div>
          ) : !latestSim ? (
            <div className="flex flex-col items-center gap-3 py-8">
              <div className="text-xs text-gray-400">No simulation run yet</div>
              <button onClick={() => simulateMut.mutate(selectedId)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700">
                <ArrowPathIcon className="h-4 w-4" /> Run Monte Carlo (10,000 iterations)
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-xs text-gray-500 mb-2">{latestSim.iterations?.toLocaleString()} iterations · {new Date(latestSim.created_at).toLocaleString()}</div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Mean Loss', value: fmt(latestSim.mean_loss), color: 'text-blue-600', bg: 'bg-blue-50' },
                  { label: 'P95 Loss', value: fmt(latestSim.p95_loss), color: 'text-orange-600', bg: 'bg-orange-50' },
                  { label: 'P99 Loss', value: fmt(latestSim.p99_loss), color: 'text-red-600', bg: 'bg-red-50' },
                  { label: 'Max Loss', value: fmt(latestSim.max_loss), color: 'text-red-800', bg: 'bg-red-100' },
                ].map(item => (
                  <div key={item.label} className={`${item.bg} rounded-xl p-3 text-center`}>
                    <div className={`text-lg font-bold ${item.color}`}>{item.value}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{item.label}</div>
                  </div>
                ))}
              </div>
              <button onClick={() => simulateMut.mutate(selectedId)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl border border-indigo-300 text-indigo-600 text-sm font-semibold hover:bg-indigo-50">
                <ArrowPathIcon className="h-4 w-4" /> Re-run Simulation
              </button>
            </div>
          )}
        </Card>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">New Risk Scenario</h3>
            <div className="grid grid-cols-1 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Type</label>
                  <select value={form.scenario_type} onChange={e => setForm(f => ({ ...f, scenario_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['single_event', 'cascading', 'compound', 'stress_test'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Velocity</label>
                  <select value={form.velocity} onChange={e => setForm(f => ({ ...f, velocity: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['sudden', 'rapid', 'moderate', 'gradual'].map(v => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Likelihood (1-5)</label>
                  <input type="number" min="1" max="5" value={form.inherent_likelihood}
                    onChange={e => setForm(f => ({ ...f, inherent_likelihood: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Impact (1-5)</label>
                  <input type="number" min="1" max="5" value={form.inherent_impact}
                    onChange={e => setForm(f => ({ ...f, inherent_impact: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate({ ...form, inherent_likelihood: parseInt(form.inherent_likelihood), inherent_impact: parseInt(form.inherent_impact) })}
                disabled={createMut.isPending || !form.title}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Creating…' : 'Create Scenario'}
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
