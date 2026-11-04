import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { UserGroupIcon, ClockIcon, PlusIcon, BriefcaseIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface AuditorResource {
  resource_id?: string;
  auditor_id: string;
  tenant_id: string;
  full_name: string;
  email?: string;
  title?: string;
  specializations?: string[];
  certifications?: string[];
  is_external: boolean;
  available_hours_per_month: number;
  is_active: boolean;
  created_at: string;
}

export function AuditResources() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    full_name: '', email: '', title: '',
    is_external: false, available_hours_per_month: 160,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['audit-resources'],
    queryFn: () => api.get('/audit-management/resources').then(r => r.data),
    refetchInterval: 60000,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/audit-management/resources', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['audit-resources'] }); setShowCreate(false); },
  });

  const resources: AuditorResource[] = data?.resources || [];
  const internal = resources.filter(r => !r.is_external).length;
  const external = resources.filter(r => r.is_external).length;
  const totalCapacity = resources.reduce((s, r) => s + (r.available_hours_per_month || 0), 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Resources"
        subtitle="Auditor team capacity and skill management"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> Add Auditor
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Auditors" value={resources.length || '—'} icon={UserGroupIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Internal" value={internal || '—'} icon={BriefcaseIcon} iconBgColor="stat-icon-indigo" iconColor="" />
        <StatCard title="External" value={external || '—'} icon={UserGroupIcon} iconBgColor="stat-icon-purple" iconColor="" />
        <StatCard title="Monthly Capacity (h)" value={totalCapacity || '—'} icon={ClockIcon} iconBgColor="stat-icon-green" iconColor="" />
      </div>

      <Card>
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Auditor Register</h2>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : resources.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No auditors registered</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Auditor', 'Title', 'Type', 'Monthly Capacity', 'Certifications', 'Status'].map(h => (
                    <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {resources.map(r => (
                  <tr key={r.auditor_id}>
                    <td className="py-2 pr-4">
                      <div className="font-medium text-gray-900 text-xs">{r.full_name}</div>
                      {r.email && <div className="text-xs text-gray-400">{r.email}</div>}
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600">{r.title || '—'}</td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${r.is_external ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}`}>
                        {r.is_external ? 'External' : 'Internal'}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-xs font-medium text-gray-700">{r.available_hours_per_month}h</td>
                    <td className="py-2 pr-4">
                      {r.certifications && r.certifications.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {r.certifications.slice(0, 3).map(c => (
                            <span key={c} className="inline-block px-1.5 py-0.5 bg-green-50 text-green-700 rounded text-xs">{c}</span>
                          ))}
                        </div>
                      ) : <span className="text-xs text-gray-400">—</span>}
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${r.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {r.is_active ? 'Active' : 'Inactive'}
                      </span>
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
            <h3 className="text-base font-semibold text-gray-900">Add Auditor</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Full Name *</label>
                <input value={form.full_name} onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Email</label>
                  <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Title</label>
                  <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                    placeholder="e.g. Senior Auditor" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Monthly Hours</label>
                  <input type="number" min="1" max="300" value={form.available_hours_per_month}
                    onChange={e => setForm(f => ({ ...f, available_hours_per_month: parseInt(e.target.value) }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div className="flex items-end pb-2">
                  <label className="flex items-center gap-2 text-xs font-medium text-gray-700 cursor-pointer">
                    <input type="checkbox" checked={form.is_external}
                      onChange={e => setForm(f => ({ ...f, is_external: e.target.checked }))}
                      className="rounded" />
                    External Auditor
                  </label>
                </div>
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate(form)}
                disabled={createMut.isPending || !form.full_name}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Adding…' : 'Add Auditor'}
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
