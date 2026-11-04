import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircleIcon, ExclamationTriangleIcon, ClockIcon,
  ArrowPathIcon, XCircleIcon, PlusIcon,
} from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface Acceptance {
  acceptance_id: string;
  risk_id: string;
  risk_title: string;
  decision: string;
  rationale: string;
  conditions?: string;
  financial_exposure?: number;
  authorized_by: string;
  authorized_by_role?: string;
  authorized_at?: string;
  effective_date?: string;
  expiry_date?: string;
  renewal_reminder_days: number;
  residual_score_snapshot?: number;
  risk_level_snapshot?: string;
  renewal_count: number;
  is_active: boolean;
  days_until_expiry?: number;
  is_expired: boolean;
  expiring_soon: boolean;
  created_at: string;
}

const decisionColors: Record<string, string> = {
  accepted: 'bg-green-100 text-green-800',
  conditionally_accepted: 'bg-yellow-100 text-yellow-800',
  rejected: 'bg-red-100 text-red-800',
  expired: 'bg-gray-100 text-gray-600',
};

const riskLevelColors: Record<string, string> = {
  low: 'text-green-600',
  medium: 'text-yellow-600',
  high: 'text-orange-600',
  critical: 'text-red-600',
  unknown: 'text-gray-400',
};

export function RiskAcceptanceRegister() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [includeExpired, setIncludeExpired] = useState(false);
  const [form, setForm] = useState({
    risk_id: '', rationale: '', authorized_by: '', authorized_by_role: '',
    decision: 'accepted', conditions: '', financial_exposure: '',
    expiry_date: '', effective_date: '',
  });

  const { data: summary } = useQuery({
    queryKey: ['risk-acceptance-summary'],
    queryFn: () => api.get('/risk-management/acceptances/summary').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data: listData, isLoading } = useQuery({
    queryKey: ['risk-acceptances', includeExpired],
    queryFn: () => api.get('/risk-management/acceptances', { params: { include_expired: includeExpired } }).then(r => r.data),
    refetchInterval: 60000,
  });

  const { data: expiring } = useQuery({
    queryKey: ['risk-acceptances-expiring'],
    queryFn: () => api.get('/risk-management/acceptances', { params: { expiring_days: 30 } }).then(r => r.data),
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/risk-management/acceptances', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['risk-acceptances'] }); qc.invalidateQueries({ queryKey: ['risk-acceptance-summary'] }); setShowCreate(false); setForm({ risk_id: '', rationale: '', authorized_by: '', authorized_by_role: '', decision: 'accepted', conditions: '', financial_exposure: '', expiry_date: '', effective_date: '' }); },
  });

  const revokeMut = useMutation({
    mutationFn: ({ id, revoked_by }: { id: string; revoked_by: string }) =>
      api.post(`/risk-management/acceptances/${id}/revoke`, { revoked_by }).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['risk-acceptances'] }); qc.invalidateQueries({ queryKey: ['risk-acceptance-summary'] }); },
  });

  const renewMut = useMutation({
    mutationFn: ({ id }: { id: string }) =>
      api.post(`/risk-management/acceptances/${id}/renew`, { extension_days: 365 }).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['risk-acceptances'] }); qc.invalidateQueries({ queryKey: ['risk-acceptance-summary'] }); },
  });

  const acceptances: Acceptance[] = listData?.acceptances || [];
  const s = summary;

  const handleCreate = () => {
    const body: any = { ...form };
    if (body.financial_exposure) body.financial_exposure = parseFloat(body.financial_exposure);
    else delete body.financial_exposure;
    if (!body.expiry_date) delete body.expiry_date;
    if (!body.effective_date) delete body.effective_date;
    if (!body.conditions) delete body.conditions;
    createMut.mutate(body);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Acceptance Register"
        subtitle="Formal risk acceptance decisions with rationale, authorization, and expiry tracking"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors">
            <PlusIcon className="h-4 w-4" /> New Acceptance
          </button>
        }
      />

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Accepted" value={s?.total ?? '—'} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Expired" value={s?.expired ?? '—'} icon={XCircleIcon} iconBgColor={s?.expired > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Expiring (30d)" value={s?.expiring_30d ?? '—'} icon={ClockIcon} iconBgColor={s?.expiring_30d > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Active" value={s?.active ?? '—'} icon={CheckCircleIcon} iconBgColor="stat-icon-blue" iconColor="" />
      </div>

      {/* Expiring soon alert */}
      {(expiring?.acceptances?.length > 0) && (
        <Card>
          <div className="flex items-center gap-2 mb-3">
            <ExclamationTriangleIcon className="h-4 w-4 text-orange-500" />
            <h2 className="text-sm font-semibold text-gray-900">Expiring Within 30 Days</h2>
          </div>
          <div className="space-y-2">
            {expiring.acceptances.map((a: Acceptance) => (
              <div key={a.acceptance_id} className="flex items-center justify-between bg-orange-50 border border-orange-200 rounded-lg p-3">
                <div>
                  <span className="text-sm font-medium text-gray-900">{a.risk_title || a.risk_id}</span>
                  <span className="ml-2 text-xs text-orange-700">{a.days_until_expiry} days left</span>
                </div>
                <button onClick={() => renewMut.mutate({ id: a.acceptance_id })}
                  className="flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800">
                  <ArrowPathIcon className="h-3.5 w-3.5" /> Renew
                </button>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Table */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-900">Acceptance Register</h2>
          <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
            <input type="checkbox" checked={includeExpired} onChange={e => setIncludeExpired(e.target.checked)} className="rounded" />
            Include expired
          </label>
        </div>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : acceptances.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No acceptances found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Risk', 'Decision', 'Risk Level', 'Authorized By', 'Expiry', 'Days Left', 'Renewals', 'Actions'].map(h => (
                    <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {acceptances.map(a => (
                  <tr key={a.acceptance_id} className={a.is_expired ? 'opacity-60' : a.expiring_soon ? 'bg-orange-50/40' : ''}>
                    <td className="py-2 pr-4 max-w-[200px]">
                      <div className="font-medium text-gray-900 truncate">{a.risk_title || a.risk_id}</div>
                      <div className="text-xs text-gray-400">{a.risk_id}</div>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${decisionColors[a.decision] || 'bg-gray-100 text-gray-600'}`}>
                        {a.decision.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`text-xs font-semibold capitalize ${riskLevelColors[a.risk_level_snapshot || 'unknown']}`}>
                        {a.risk_level_snapshot || '—'}
                      </span>
                    </td>
                    <td className="py-2 pr-4">
                      <div className="text-xs text-gray-900">{a.authorized_by}</div>
                      {a.authorized_by_role && <div className="text-xs text-gray-400">{a.authorized_by_role}</div>}
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600">
                      {a.expiry_date ? new Date(a.expiry_date).toLocaleDateString() : 'No expiry'}
                    </td>
                    <td className="py-2 pr-4">
                      {a.days_until_expiry != null ? (
                        <span className={`text-xs font-semibold ${a.is_expired ? 'text-red-600' : a.expiring_soon ? 'text-orange-600' : 'text-green-600'}`}>
                          {a.is_expired ? 'Expired' : `${a.days_until_expiry}d`}
                        </span>
                      ) : <span className="text-xs text-gray-400">—</span>}
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600">{a.renewal_count || 0}</td>
                    <td className="py-2 flex gap-2">
                      {!a.is_expired && (
                        <>
                          <button onClick={() => renewMut.mutate({ id: a.acceptance_id })}
                            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">Renew</button>
                          <button onClick={() => revokeMut.mutate({ id: a.acceptance_id, revoked_by: 'current_user' })}
                            className="text-xs text-red-600 hover:text-red-800 font-medium">Revoke</button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Record Risk Acceptance</h3>
            <div className="grid grid-cols-1 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Risk ID *</label>
                <input value={form.risk_id} onChange={e => setForm(f => ({ ...f, risk_id: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="e.g. RISK-001" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Decision *</label>
                <select value={form.decision} onChange={e => setForm(f => ({ ...f, decision: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="accepted">Accepted</option>
                  <option value="conditionally_accepted">Conditionally Accepted</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Rationale *</label>
                <textarea value={form.rationale} onChange={e => setForm(f => ({ ...f, rationale: e.target.value }))}
                  rows={3} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Conditions (optional)</label>
                <textarea value={form.conditions} onChange={e => setForm(f => ({ ...f, conditions: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  placeholder="Any conditions attached to this acceptance..." />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Authorized By *</label>
                  <input value={form.authorized_by} onChange={e => setForm(f => ({ ...f, authorized_by: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Role</label>
                  <input value={form.authorized_by_role} onChange={e => setForm(f => ({ ...f, authorized_by_role: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="e.g. CRO" />
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
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Max Financial Exposure (USD)</label>
                <input type="number" value={form.financial_exposure} onChange={e => setForm(f => ({ ...f, financial_exposure: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="0" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={handleCreate} disabled={createMut.isPending || !form.risk_id || !form.rationale || !form.authorized_by}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Saving…' : 'Record Acceptance'}
              </button>
              <button onClick={() => setShowCreate(false)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
