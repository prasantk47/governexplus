import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MagnifyingGlassIcon, ExclamationTriangleIcon, CheckCircleIcon, PlusIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

const statusColors: Record<string, string> = {
  clear: 'bg-green-100 text-green-700',
  pending_review: 'bg-yellow-100 text-yellow-800',
  true_match: 'bg-red-100 text-red-700',
  false_positive: 'bg-gray-100 text-gray-500',
  escalated: 'bg-orange-100 text-orange-700',
};

export function SanctionsScreening() {
  const qc = useQueryClient();
  const [showScreen, setShowScreen] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    entity_name: '', entity_type: 'vendor',
    entity_country: '', entity_reference: '',
    watchlists: ['OFAC', 'UN', 'EU', 'UK_HMT'],
  });
  const [resolveForm, setResolveForm] = useState({
    resolution: 'false_positive', resolution_notes: '', resolved_by: '',
  });

  const { data: statsData } = useQuery({
    queryKey: ['screening-stats'],
    queryFn: () => api.get('/sanctions-screening/summary/stats').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['sanctions-screenings'],
    queryFn: () => api.get('/sanctions-screening').then(r => r.data),
    refetchInterval: 60000,
  });

  const screenMut = useMutation({
    mutationFn: (body: any) => api.post('/sanctions-screening', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sanctions-screenings'] }); qc.invalidateQueries({ queryKey: ['screening-stats'] }); setShowScreen(false); },
  });

  const resolveMut = useMutation({
    mutationFn: ({ id, ...body }: any) => api.put(`/sanctions-screening/${id}/resolve`, body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sanctions-screenings'] }); qc.invalidateQueries({ queryKey: ['screening-stats'] }); setResolvingId(null); },
  });

  const stats = statsData || {};
  const screenings = data?.screenings || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sanctions & Watchlist Screening"
        subtitle="Screen vendors, employees, and counterparties against OFAC, UN, EU, UK watchlists"
        actions={
          <button onClick={() => setShowScreen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> Screen Entity
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Screened" value={stats.total_screened ?? '—'} icon={MagnifyingGlassIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Pending Review" value={stats.pending_review ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={stats.pending_review > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
        <StatCard title="True Matches" value={stats.true_matches ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={stats.true_matches > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Clear" value={stats.clear ?? '—'} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
      </div>

      {stats.pending_review > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
            <span className="text-sm font-semibold text-yellow-800">
              {stats.pending_review} screening result(s) require manual review
            </span>
          </div>
        </div>
      )}

      <Card>
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Screening Results</h2>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : screenings.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No screening records. Screen an entity to begin.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead><tr className="border-b border-gray-100">
                {['Entity', 'Type', 'Country', 'Screened', 'Watchlists', 'Result', 'Actions'].map(h => (
                  <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                ))}
              </tr></thead>
              <tbody className="divide-y divide-gray-50">
                {screenings.map((s: any) => (
                  <tr key={s.screening_id} className={s.match_found && s.status === 'pending_review' ? 'bg-yellow-50/30' : ''}>
                    <td className="py-2 pr-4">
                      <div className="text-xs font-medium text-gray-900">{s.entity_name}</div>
                      <div className="text-xs text-gray-400">{s.entity_reference || s.screening_id}</div>
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600 capitalize">{s.entity_type}</td>
                    <td className="py-2 pr-4 text-xs text-gray-600">{s.entity_country || '—'}</td>
                    <td className="py-2 pr-4 text-xs text-gray-600">
                      {s.screened_at ? new Date(s.screened_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-500">
                      {(s.watchlists_checked || []).join(', ')}
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[s.status] || 'bg-gray-100 text-gray-500'}`}>
                        {s.status?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-2">
                      {s.status === 'pending_review' && (
                        <button onClick={() => setResolvingId(s.screening_id)}
                          className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">Resolve</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Screen Entity Modal */}
      {showScreen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Screen Entity</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Entity Name *</label>
                <input value={form.entity_name} onChange={e => setForm(f => ({ ...f, entity_name: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Entity Type</label>
                  <select value={form.entity_type} onChange={e => setForm(f => ({ ...f, entity_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['vendor', 'employee', 'customer', 'counterparty', 'individual', 'organization'].map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Country</label>
                  <input value={form.entity_country} onChange={e => setForm(f => ({ ...f, entity_country: e.target.value }))}
                    placeholder="e.g. US, RU, IR" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Reference ID</label>
                <input value={form.entity_reference} onChange={e => setForm(f => ({ ...f, entity_reference: e.target.value }))}
                  placeholder="Vendor/employee ID" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-2">Watchlists to Check</label>
                <div className="flex flex-wrap gap-2">
                  {['OFAC', 'UN', 'EU', 'UK_HMT', 'INTERPOL'].map(wl => (
                    <label key={wl} className="flex items-center gap-1.5 text-xs font-medium text-gray-700 cursor-pointer">
                      <input type="checkbox" checked={form.watchlists.includes(wl)}
                        onChange={e => setForm(f => ({
                          ...f,
                          watchlists: e.target.checked ? [...f.watchlists, wl] : f.watchlists.filter(w => w !== wl),
                        }))} className="rounded" />
                      {wl}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => screenMut.mutate(form)}
                disabled={screenMut.isPending || !form.entity_name}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {screenMut.isPending ? 'Screening…' : 'Run Screening'}
              </button>
              <button onClick={() => setShowScreen(false)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Resolve Modal */}
      {resolvingId && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Resolve Screening</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Resolution</label>
                <select value={resolveForm.resolution} onChange={e => setResolveForm(f => ({ ...f, resolution: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="false_positive">False Positive — Not a match</option>
                  <option value="true_match">True Match — Confirmed hit</option>
                  <option value="escalated">Escalated — Requires further review</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Resolved By</label>
                <input value={resolveForm.resolved_by} onChange={e => setResolveForm(f => ({ ...f, resolved_by: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Notes</label>
                <textarea value={resolveForm.resolution_notes} onChange={e => setResolveForm(f => ({ ...f, resolution_notes: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={() => resolveMut.mutate({ id: resolvingId, ...resolveForm })}
                disabled={resolveMut.isPending}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {resolveMut.isPending ? 'Resolving…' : 'Resolve'}
              </button>
              <button onClick={() => setResolvingId(null)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
