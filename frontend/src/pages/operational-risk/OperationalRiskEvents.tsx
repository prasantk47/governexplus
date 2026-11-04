import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BanknotesIcon, ExclamationTriangleIcon, ChartBarIcon, PlusIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

const eventTypeColors: Record<string, string> = {
  internal_fraud: 'bg-red-100 text-red-700',
  external_fraud: 'bg-red-100 text-red-700',
  employment_practices: 'bg-orange-100 text-orange-700',
  clients_products_practices: 'bg-yellow-100 text-yellow-800',
  damage_to_assets: 'bg-purple-100 text-purple-700',
  business_disruption: 'bg-blue-100 text-blue-700',
  execution_delivery: 'bg-gray-100 text-gray-700',
  system_failures: 'bg-pink-100 text-pink-700',
};

export function OperationalRiskEvents() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    title: '', description: '', event_type: 'execution_delivery',
    business_line: 'retail_banking', event_date: '',
    gross_loss_amount: '', is_near_miss: false, assigned_owner: '',
  });

  const { data: summaryData } = useQuery({
    queryKey: ['oploss-summary'],
    queryFn: () => api.get('/operational-risk/loss-database/summary').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['operational-loss-events'],
    queryFn: () => api.get('/operational-risk/loss-events').then(r => r.data),
    refetchInterval: 60000,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/operational-risk/loss-events', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['operational-loss-events'] }); qc.invalidateQueries({ queryKey: ['oploss-summary'] }); setShowCreate(false); },
  });

  const summary = summaryData || {};
  const events = data?.events || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operational Risk Events"
        subtitle="Basel II/III loss event capture and RCSA — 8 event categories"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> Report Event
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Events (1Y)" value={summary.total_events ?? '—'} icon={ChartBarIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Near Misses" value={summary.near_misses ?? '—'} icon={ExclamationTriangleIcon} iconBgColor="stat-icon-orange" iconColor="" />
        <StatCard title="Gross Loss" value={summary.total_gross_loss != null ? `$${Number(summary.total_gross_loss).toLocaleString()}` : '—'} icon={BanknotesIcon} iconBgColor={summary.total_gross_loss > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Net Loss" value={summary.total_net_loss != null ? `$${Number(summary.total_net_loss).toLocaleString()}` : '—'} icon={BanknotesIcon} iconBgColor="stat-icon-purple" iconColor="" />
      </div>

      {/* Loss by Event Type */}
      {summary.by_event_type && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Loss by Basel II Event Type</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(summary.by_event_type as Record<string, any>).filter(([, v]) => v.count > 0).map(([type, stats]: any) => (
              <div key={type} className="p-3 bg-gray-50 rounded-xl">
                <div className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium mb-2 ${eventTypeColors[type] || 'bg-gray-100 text-gray-600'}`}>
                  {type.replace(/_/g, ' ')}
                </div>
                <div className="text-sm font-bold text-gray-900">{stats.count}</div>
                <div className="text-xs text-gray-500">${Number(stats.total_gross_loss).toLocaleString()}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Loss Event Register</h2>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : events.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No loss events recorded</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead><tr className="border-b border-gray-100">
                {['Event', 'Type', 'Business Line', 'Date', 'Gross Loss', 'Near Miss', 'Status'].map(h => (
                  <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                ))}
              </tr></thead>
              <tbody className="divide-y divide-gray-50">
                {events.map((e: any) => (
                  <tr key={e.event_id}>
                    <td className="py-2 pr-4">
                      <div className="text-xs font-medium text-gray-900">{e.title}</div>
                      <div className="text-xs text-gray-400">{e.event_id}</div>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${eventTypeColors[e.event_type] || 'bg-gray-100 text-gray-500'}`}>
                        {(e.event_type || '').replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600 capitalize">{(e.business_line || '—').replace(/_/g, ' ')}</td>
                    <td className="py-2 pr-4 text-xs text-gray-600">{e.event_date ? new Date(e.event_date).toLocaleDateString() : '—'}</td>
                    <td className="py-2 pr-4 text-xs font-medium text-red-600">
                      {e.gross_loss_amount != null ? `$${Number(e.gross_loss_amount).toLocaleString()}` : '—'}
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`text-xs font-medium ${e.is_near_miss ? 'text-orange-600' : 'text-gray-400'}`}>
                        {e.is_near_miss ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${e.status === 'closed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-800'}`}>
                        {e.status}
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
            <h3 className="text-base font-semibold text-gray-900">Report Loss Event</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Event Type</label>
                  <select value={form.event_type} onChange={e => setForm(f => ({ ...f, event_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['internal_fraud', 'external_fraud', 'employment_practices', 'clients_products_practices', 'damage_to_assets', 'business_disruption', 'execution_delivery', 'system_failures'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Business Line</label>
                  <select value={form.business_line} onChange={e => setForm(f => ({ ...f, business_line: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['corporate_finance', 'trading_sales', 'retail_banking', 'commercial_banking', 'payment_settlement', 'agency_services', 'asset_management', 'retail_brokerage'].map(l => (
                      <option key={l} value={l}>{l.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Event Date</label>
                  <input type="date" value={form.event_date} onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Gross Loss (USD)</label>
                  <input type="number" min="0" value={form.gross_loss_amount}
                    onChange={e => setForm(f => ({ ...f, gross_loss_amount: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <label className="flex items-center gap-2 text-xs font-medium text-gray-700 cursor-pointer">
                <input type="checkbox" checked={form.is_near_miss}
                  onChange={e => setForm(f => ({ ...f, is_near_miss: e.target.checked }))} className="rounded" />
                Near Miss (no actual loss occurred)
              </label>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate({ ...form, gross_loss_amount: form.gross_loss_amount ? parseFloat(form.gross_loss_amount) : undefined })}
                disabled={createMut.isPending || !form.title}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Reporting…' : 'Report Event'}
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
