import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FlagIcon, LinkIcon, PlusIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface ControlObjective {
  objective_id: string;
  title: string;
  description?: string;
  category?: string;
  framework_ref?: string;
  linked_control_ids?: string[];
  linked_risk_ids?: string[];
  status: string;
  created_at: string;
}

const statusColors: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  inactive: 'bg-gray-100 text-gray-500',
  draft: 'bg-yellow-100 text-yellow-800',
  retired: 'bg-red-100 text-red-700',
};

export function ControlObjectives() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    title: '', description: '', category: 'operational',
    framework_ref: '', status: 'active',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['control-objectives'],
    queryFn: () => api.get('/process-control/objectives').then(r => r.data),
    refetchInterval: 60000,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/process-control/objectives', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['control-objectives'] }); setShowCreate(false); },
  });

  const { data: gapsData } = useQuery({
    queryKey: ['control-objectives-gaps'],
    queryFn: () => api.get('/process-control/objectives/gaps').then(r => r.data),
  });

  const objectives: ControlObjective[] = data?.objectives || [];
  const gaps: any[] = gapsData?.gaps || [];
  const withControls = objectives.filter(o => (o.linked_control_ids?.length || 0) > 0).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Control Objectives"
        subtitle="Formal control objectives linking controls to compliance requirements"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> New Objective
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <StatCard title="Total Objectives" value={objectives.length || '—'} icon={FlagIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="With Controls" value={withControls || '—'} icon={LinkIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Coverage Gaps" value={gaps.length || '—'} icon={ExclamationTriangleIcon} iconBgColor={gaps.length > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
      </div>

      {gaps.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Coverage Gaps — Objectives Without Controls</h2>
          <div className="space-y-2">
            {gaps.slice(0, 5).map((g: any) => (
              <div key={g.objective_id} className="flex items-center gap-3 p-2 bg-orange-50 rounded-lg border border-orange-100">
                <ExclamationTriangleIcon className="h-4 w-4 text-orange-500 flex-shrink-0" />
                <div>
                  <span className="text-xs font-medium text-gray-900">{g.title}</span>
                  {g.framework_ref && <span className="ml-2 text-xs text-gray-400">{g.framework_ref}</span>}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Control Objective Register</h2>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : objectives.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No control objectives defined</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Objective', 'Category', 'Framework', 'Status', 'Controls', 'Risks'].map(h => (
                    <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {objectives.map(o => (
                  <tr key={o.objective_id}>
                    <td className="py-2 pr-4">
                      <div className="font-medium text-gray-900 text-xs">{o.title}</div>
                      {o.description && <div className="text-xs text-gray-400 truncate max-w-xs">{o.description}</div>}
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600 capitalize">{o.category?.replace(/_/g, ' ') || '—'}</td>
                    <td className="py-2 pr-4 text-xs text-gray-500">{o.framework_ref || '—'}</td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[o.status] || 'bg-gray-100 text-gray-600'}`}>
                        {o.status}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-xs text-center font-medium text-indigo-600">
                      {o.linked_control_ids?.length || 0}
                    </td>
                    <td className="py-2 pr-4 text-xs text-center font-medium text-orange-600">
                      {o.linked_risk_ids?.length || 0}
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
            <h3 className="text-base font-semibold text-gray-900">New Control Objective</h3>
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
                    {['operational', 'financial', 'compliance', 'strategic', 'it'].map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Framework Ref</label>
                  <input value={form.framework_ref} onChange={e => setForm(f => ({ ...f, framework_ref: e.target.value }))}
                    placeholder="e.g. ISO 27001 A.9.1" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate(form)}
                disabled={createMut.isPending || !form.title}
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
