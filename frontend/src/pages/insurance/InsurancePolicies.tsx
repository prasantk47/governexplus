import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShieldCheckIcon, BanknotesIcon, ExclamationTriangleIcon, PlusIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

const policyTypeLabels: Record<string, string> = {
  cyber: 'Cyber',
  general_liability: 'General Liability',
  directors_officers: 'D&O',
  errors_omissions: 'E&O',
  property: 'Property',
  business_interruption: 'Business Interruption',
  professional_liability: 'Professional Liability',
  workers_compensation: 'Workers Compensation',
};

export function InsurancePolicies() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [expiringFilter, setExpiringFilter] = useState<number | null>(null);
  const [form, setForm] = useState({
    insurer_name: '', policy_number: '', policy_type: 'cyber',
    coverage_amount: '', annual_premium: '', currency: 'USD',
    effective_date: '', expiry_date: '', policy_owner: '',
  });

  const { data: coverageData } = useQuery({
    queryKey: ['insurance-coverage'],
    queryFn: () => api.get('/insurance/summary/coverage').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['insurance-policies', expiringFilter],
    queryFn: () => {
      const url = expiringFilter
        ? `/insurance?expiring_within_days=${expiringFilter}`
        : '/insurance';
      return api.get(url).then(r => r.data);
    },
    refetchInterval: 60000,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/insurance', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['insurance-policies'] }); qc.invalidateQueries({ queryKey: ['insurance-coverage'] }); setShowCreate(false); },
  });

  const coverage = coverageData || {};
  const policies = data?.policies || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Insurance & Risk Transfer"
        subtitle="Insurance policy register with risk coverage mapping and renewal alerts"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> Add Policy
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Active Policies" value={coverage.active_policies ?? '—'} icon={ShieldCheckIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Expiring (90d)" value={coverage.expiring_within_90_days ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={coverage.expiring_within_90_days > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Total Premium" value={coverage.total_annual_premium != null ? `$${Number(coverage.total_annual_premium).toLocaleString()}` : '—'} icon={BanknotesIcon} iconBgColor="stat-icon-purple" iconColor="" />
        <StatCard title="Total Coverage" value={coverage.total_coverage_amount != null ? `$${(Number(coverage.total_coverage_amount) / 1000000).toFixed(1)}M` : '—'} icon={ShieldCheckIcon} iconBgColor="stat-icon-green" iconColor="" />
      </div>

      {/* Expiry filter */}
      <div className="flex gap-2">
        <span className="text-xs font-medium text-gray-500 self-center">Filter:</span>
        {[null, 30, 60, 90].map(d => (
          <button key={d ?? 'all'} onClick={() => setExpiringFilter(d)}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${expiringFilter === d ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            {d === null ? 'All' : `Expiring in ${d}d`}
          </button>
        ))}
      </div>

      <Card>
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Policy Register</h2>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : policies.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No insurance policies on record</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead><tr className="border-b border-gray-100">
                {['Policy', 'Type', 'Insurer', 'Coverage', 'Premium (p.a.)', 'Effective', 'Expiry', 'Status'].map(h => (
                  <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                ))}
              </tr></thead>
              <tbody className="divide-y divide-gray-50">
                {policies.map((p: any) => {
                  const expiryDate = p.expiry_date ? new Date(p.expiry_date) : null;
                  const daysToExpiry = expiryDate ? Math.ceil((expiryDate.getTime() - Date.now()) / 86400000) : null;
                  const isExpiring = daysToExpiry !== null && daysToExpiry <= 90 && daysToExpiry > 0;
                  const isExpired = daysToExpiry !== null && daysToExpiry <= 0;
                  return (
                    <tr key={p.policy_id} className={isExpired ? 'bg-red-50/20' : isExpiring ? 'bg-orange-50/20' : ''}>
                      <td className="py-2 pr-4">
                        <div className="text-xs font-medium text-gray-900">{p.policy_number || p.policy_id}</div>
                        <div className="text-xs text-gray-400">{p.policy_owner || '—'}</div>
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-600">{policyTypeLabels[p.policy_type] || p.policy_type}</td>
                      <td className="py-2 pr-4 text-xs text-gray-900 font-medium">{p.insurer_name}</td>
                      <td className="py-2 pr-4 text-xs text-gray-700">
                        {p.coverage_amount != null ? `$${Number(p.coverage_amount).toLocaleString()}` : '—'}
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-700">
                        {p.annual_premium != null ? `$${Number(p.annual_premium).toLocaleString()}` : '—'}
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-600">{p.effective_date ? new Date(p.effective_date).toLocaleDateString() : '—'}</td>
                      <td className="py-2 pr-4">
                        <span className={`text-xs font-medium ${isExpired ? 'text-red-600' : isExpiring ? 'text-orange-600' : 'text-gray-600'}`}>
                          {expiryDate ? expiryDate.toLocaleDateString() : '—'}
                          {isExpiring && daysToExpiry !== null && <span className="ml-1 text-orange-600">({daysToExpiry}d)</span>}
                        </span>
                      </td>
                      <td className="py-2 pr-4">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${isExpired ? 'bg-red-100 text-red-700' : p.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {isExpired ? 'expired' : p.status}
                        </span>
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
            <h3 className="text-base font-semibold text-gray-900">Add Insurance Policy</h3>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Insurer Name *</label>
                  <input value={form.insurer_name} onChange={e => setForm(f => ({ ...f, insurer_name: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Policy Number</label>
                  <input value={form.policy_number} onChange={e => setForm(f => ({ ...f, policy_number: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Policy Type</label>
                <select value={form.policy_type} onChange={e => setForm(f => ({ ...f, policy_type: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  {Object.entries(policyTypeLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Coverage Amount</label>
                  <input type="number" value={form.coverage_amount} onChange={e => setForm(f => ({ ...f, coverage_amount: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Annual Premium</label>
                  <input type="number" value={form.annual_premium} onChange={e => setForm(f => ({ ...f, annual_premium: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Effective Date</label>
                  <input type="date" value={form.effective_date} onChange={e => setForm(f => ({ ...f, effective_date: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Expiry Date</label>
                  <input type="date" value={form.expiry_date} onChange={e => setForm(f => ({ ...f, expiry_date: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate({ ...form, coverage_amount: form.coverage_amount ? parseFloat(form.coverage_amount) : undefined, annual_premium: form.annual_premium ? parseFloat(form.annual_premium) : undefined })}
                disabled={createMut.isPending || !form.insurer_name}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Adding…' : 'Add Policy'}
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
