import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ExclamationTriangleIcon, CheckCircleIcon, ClockIcon,
  XCircleIcon, PlusIcon, ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface PolicyException {
  exception_id: string;
  policy_id: string;
  policy_title?: string;
  title: string;
  justification: string;
  exception_risk: string;
  status: string;
  requested_by: string;
  approved_by?: string;
  expiry_date?: string;
  effective_date?: string;
  renewal_count: number;
  compensating_controls?: string;
  days_until_expiry?: number;
  is_expired: boolean;
  expiring_soon: boolean;
  created_at: string;
}

const statusColors: Record<string, string> = {
  pending_approval: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-700',
  active: 'bg-indigo-100 text-indigo-700',
  rejected: 'bg-red-100 text-red-700',
  expired: 'bg-gray-100 text-gray-500',
  revoked: 'bg-red-100 text-red-700',
  renewal_pending: 'bg-orange-100 text-orange-800',
};

const riskColors: Record<string, string> = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-700',
};

export function PolicyExceptionRegister() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [approveForm, setApproveForm] = useState({ approved_by: '', expiry_date: '', conditions: '' });
  const [form, setForm] = useState({
    policy_id: '', policy_title: '', policy_section: '', title: '',
    justification: '', exception_risk: 'medium', compensating_controls: '',
    requested_by: '', org_unit: '', expiry_date: '', effective_date: '',
    scope_description: '', business_impact_if_denied: '',
  });

  const { data: summary } = useQuery({
    queryKey: ['policy-exception-summary'],
    queryFn: () => api.get('/policy-exceptions/summary').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data: listData, isLoading } = useQuery({
    queryKey: ['policy-exceptions', statusFilter],
    queryFn: () => api.get('/policy-exceptions', { params: statusFilter ? { status: statusFilter } : { include_expired: false } }).then(r => r.data),
    refetchInterval: 60000,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/policy-exceptions', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['policy-exceptions'] }); qc.invalidateQueries({ queryKey: ['policy-exception-summary'] }); setShowCreate(false); },
  });

  const approveMut = useMutation({
    mutationFn: ({ id, ...body }: { id: string; approved_by: string; expiry_date?: string; conditions?: string }) =>
      api.post(`/policy-exceptions/${id}/approve`, body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['policy-exceptions'] }); qc.invalidateQueries({ queryKey: ['policy-exception-summary'] }); setApprovingId(null); },
  });

  const rejectMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post(`/policy-exceptions/${id}/reject`, { reason }).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['policy-exceptions'] }); qc.invalidateQueries({ queryKey: ['policy-exception-summary'] }); },
  });

  const renewMut = useMutation({
    mutationFn: ({ id }: { id: string }) =>
      api.post(`/policy-exceptions/${id}/renew`, { extension_days: 365 }).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['policy-exceptions'] }); qc.invalidateQueries({ queryKey: ['policy-exception-summary'] }); },
  });

  const exceptions: PolicyException[] = listData?.exceptions || [];
  const s = summary;

  const handleCreate = () => {
    const body: any = { ...form };
    if (!body.expiry_date) delete body.expiry_date;
    if (!body.effective_date) delete body.effective_date;
    createMut.mutate(body);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Policy Exception Register"
        subtitle="Time-bound policy deviations with approval, compensating controls, and expiry tracking"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors">
            <PlusIcon className="h-4 w-4" /> New Exception
          </button>
        }
      />

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <StatCard title="Total" value={s?.total ?? '—'} icon={ExclamationTriangleIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Pending Approval" value={s?.pending_approval ?? '—'} icon={ClockIcon} iconBgColor={s?.pending_approval > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Active" value={s?.active ?? '—'} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Expired" value={s?.expired ?? '—'} icon={XCircleIcon} iconBgColor={s?.expired > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Expiring (30d)" value={s?.expiring_30d ?? '—'} icon={ClockIcon} iconBgColor={s?.expiring_30d > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
      </div>

      {/* Table */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-900">Exception Register</h2>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-xs">
            <option value="">All Statuses</option>
            {['pending_approval', 'active', 'rejected', 'expired', 'revoked'].map(s => (
              <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : exceptions.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No exceptions found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Exception', 'Policy', 'Risk', 'Status', 'Requested By', 'Expiry', 'Days Left', 'Actions'].map(h => (
                    <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {exceptions.map(exc => (
                  <tr key={exc.exception_id} className={exc.is_expired ? 'opacity-60' : exc.expiring_soon ? 'bg-orange-50/40' : ''}>
                    <td className="py-2 pr-4 max-w-[180px]">
                      <div className="font-medium text-gray-900 truncate">{exc.title}</div>
                      <div className="text-xs text-gray-400">{exc.exception_id}</div>
                    </td>
                    <td className="py-2 pr-4 max-w-[160px]">
                      <div className="text-xs text-gray-900 truncate">{exc.policy_title || exc.policy_id}</div>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${riskColors[exc.exception_risk] || 'bg-gray-100 text-gray-600'}`}>
                        {exc.exception_risk}
                      </span>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[exc.status] || 'bg-gray-100 text-gray-600'}`}>
                        {exc.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600">{exc.requested_by}</td>
                    <td className="py-2 pr-4 text-xs text-gray-600">
                      {exc.expiry_date ? new Date(exc.expiry_date).toLocaleDateString() : '—'}
                    </td>
                    <td className="py-2 pr-4">
                      {exc.days_until_expiry != null ? (
                        <span className={`text-xs font-semibold ${exc.is_expired ? 'text-red-600' : exc.expiring_soon ? 'text-orange-600' : 'text-green-600'}`}>
                          {exc.is_expired ? 'Expired' : `${exc.days_until_expiry}d`}
                        </span>
                      ) : <span className="text-xs text-gray-400">—</span>}
                    </td>
                    <td className="py-2">
                      <div className="flex gap-2">
                        {exc.status === 'pending_approval' && (
                          <>
                            <button onClick={() => setApprovingId(exc.exception_id)}
                              className="text-xs text-green-600 hover:text-green-800 font-medium">Approve</button>
                            <button onClick={() => rejectMut.mutate({ id: exc.exception_id, reason: 'Rejected by reviewer' })}
                              className="text-xs text-red-600 hover:text-red-800 font-medium">Reject</button>
                          </>
                        )}
                        {exc.status === 'active' && exc.expiring_soon && (
                          <button onClick={() => renewMut.mutate({ id: exc.exception_id })}
                            className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                            <ArrowPathIcon className="h-3 w-3" /> Renew
                          </button>
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

      {/* Approve modal */}
      {approvingId && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Approve Exception</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Approved By *</label>
                <input value={approveForm.approved_by} onChange={e => setApproveForm(f => ({ ...f, approved_by: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Expiry Date</label>
                <input type="date" value={approveForm.expiry_date} onChange={e => setApproveForm(f => ({ ...f, expiry_date: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Conditions</label>
                <textarea value={approveForm.conditions} onChange={e => setApproveForm(f => ({ ...f, conditions: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => approveMut.mutate({ id: approvingId, ...approveForm, expiry_date: approveForm.expiry_date || undefined })}
                disabled={approveMut.isPending || !approveForm.approved_by}
                className="flex-1 bg-green-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-green-700 disabled:opacity-50">
                {approveMut.isPending ? 'Approving…' : 'Approve'}
              </button>
              <button onClick={() => setApprovingId(null)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Submit Policy Exception Request</h3>
            <div className="grid grid-cols-1 gap-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Policy ID *</label>
                  <input value={form.policy_id} onChange={e => setForm(f => ({ ...f, policy_id: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="POL-001" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Policy Title</label>
                  <input value={form.policy_title} onChange={e => setForm(f => ({ ...f, policy_title: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Exception Title *</label>
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Policy Section / Clause</label>
                <input value={form.policy_section} onChange={e => setForm(f => ({ ...f, policy_section: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="e.g. Section 4.2" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Business Justification *</label>
                <textarea value={form.justification} onChange={e => setForm(f => ({ ...f, justification: e.target.value }))}
                  rows={3} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Scope Description</label>
                <textarea value={form.scope_description} onChange={e => setForm(f => ({ ...f, scope_description: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Affected systems, users, or processes..." />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Compensating Controls</label>
                <textarea value={form.compensating_controls} onChange={e => setForm(f => ({ ...f, compensating_controls: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Exception Risk</label>
                  <select value={form.exception_risk} onChange={e => setForm(f => ({ ...f, exception_risk: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['low', 'medium', 'high', 'critical'].map(r => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Org Unit</label>
                  <input value={form.org_unit} onChange={e => setForm(f => ({ ...f, org_unit: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Requested By *</label>
                <input value={form.requested_by} onChange={e => setForm(f => ({ ...f, requested_by: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
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
              <button onClick={handleCreate} disabled={createMut.isPending || !form.policy_id || !form.justification || !form.requested_by}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Submitting…' : 'Submit Request'}
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
