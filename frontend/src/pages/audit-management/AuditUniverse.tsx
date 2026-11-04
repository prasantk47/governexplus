import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BuildingOfficeIcon, ChartBarIcon, PlusIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface AuditableEntity {
  entity_id: string;
  name: string;
  entity_type: string;
  description?: string;
  owner_name?: string;
  inherent_risk_score?: number;
  residual_risk_score?: number;
  audit_frequency?: string;
  last_audited_at?: string;
  next_audit_date?: string;
  status: string;
  created_at: string;
}

const riskColor = (score?: number) => {
  if (!score) return 'text-gray-400';
  if (score >= 15) return 'text-red-600';
  if (score >= 9) return 'text-orange-600';
  if (score >= 4) return 'text-yellow-600';
  return 'text-green-600';
};

const riskBg = (score?: number) => {
  if (!score) return 'bg-gray-100';
  if (score >= 15) return 'bg-red-100';
  if (score >= 9) return 'bg-orange-100';
  if (score >= 4) return 'bg-yellow-100';
  return 'bg-green-100';
};

const statusColors: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  inactive: 'bg-gray-100 text-gray-500',
  under_review: 'bg-yellow-100 text-yellow-800',
};

export function AuditUniverse() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: '', entity_type: 'business_unit', description: '',
    owner_name: '', audit_frequency: 'annual',
    inherent_risk_score: '9',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['audit-entities'],
    queryFn: () => api.get('/audit-management/entities').then(r => r.data),
    refetchInterval: 60000,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/audit-management/entities', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['audit-entities'] }); setShowCreate(false); },
  });

  const computeRiskMut = useMutation({
    mutationFn: (id: string) => api.post(`/audit-management/entities/${id}/compute-risk`, {}).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['audit-entities'] }),
  });

  const entities: AuditableEntity[] = data?.entities || [];
  const highRisk = entities.filter(e => (e.inherent_risk_score || 0) >= 15).length;
  const dueForAudit = entities.filter(e => e.next_audit_date && new Date(e.next_audit_date) <= new Date()).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Universe"
        subtitle="All auditable entities with risk-based audit scheduling"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> Add Entity
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <StatCard title="Total Entities" value={entities.length || '—'} icon={BuildingOfficeIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="High Risk" value={highRisk || '—'} icon={ChartBarIcon} iconBgColor={highRisk > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Due for Audit" value={dueForAudit || '—'} icon={ArrowPathIcon} iconBgColor={dueForAudit > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
      </div>

      <Card>
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Auditable Entity Register</h2>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : entities.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No entities in audit universe</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Entity', 'Type', 'Status', 'Inherent Risk', 'Frequency', 'Last Audited', 'Next Audit', 'Actions'].map(h => (
                    <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {entities.sort((a, b) => (b.inherent_risk_score || 0) - (a.inherent_risk_score || 0)).map(e => (
                  <tr key={e.entity_id}>
                    <td className="py-2 pr-4">
                      <div className="font-medium text-gray-900">{e.name}</div>
                      {e.owner_name && <div className="text-xs text-gray-400">{e.owner_name}</div>}
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600 capitalize">{e.entity_type.replace(/_/g, ' ')}</td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[e.status] || 'bg-gray-100 text-gray-600'}`}>
                        {e.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-2 pr-4">
                      {e.inherent_risk_score != null ? (
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${riskBg(e.inherent_risk_score)} ${riskColor(e.inherent_risk_score)}`}>
                          {e.inherent_risk_score}
                        </span>
                      ) : <span className="text-xs text-gray-400">—</span>}
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600 capitalize">{e.audit_frequency || '—'}</td>
                    <td className="py-2 pr-4 text-xs text-gray-600">
                      {e.last_audited_at ? new Date(e.last_audited_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="py-2 pr-4">
                      {e.next_audit_date ? (
                        <span className={`text-xs font-medium ${new Date(e.next_audit_date) <= new Date() ? 'text-red-600' : 'text-gray-600'}`}>
                          {new Date(e.next_audit_date).toLocaleDateString()}
                        </span>
                      ) : <span className="text-xs text-gray-400">—</span>}
                    </td>
                    <td className="py-2">
                      <button onClick={() => computeRiskMut.mutate(e.entity_id)}
                        className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">Compute Risk</button>
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
            <h3 className="text-base font-semibold text-gray-900">Add Auditable Entity</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Entity Name *</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Type</label>
                  <select value={form.entity_type} onChange={e => setForm(f => ({ ...f, entity_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['business_unit', 'process', 'system', 'subsidiary', 'location', 'project'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Audit Frequency</label>
                  <select value={form.audit_frequency} onChange={e => setForm(f => ({ ...f, audit_frequency: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['quarterly', 'semi_annual', 'annual', 'biennial', 'as_needed'].map(f => (
                      <option key={f} value={f}>{f.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Inherent Risk Score</label>
                  <input type="number" min="1" max="25" value={form.inherent_risk_score}
                    onChange={e => setForm(f => ({ ...f, inherent_risk_score: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Owner</label>
                  <input value={form.owner_name} onChange={e => setForm(f => ({ ...f, owner_name: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate({ ...form, inherent_risk_score: parseFloat(form.inherent_risk_score) })}
                disabled={createMut.isPending || !form.name}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Adding…' : 'Add Entity'}
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
