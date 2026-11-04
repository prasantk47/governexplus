import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DocumentTextIcon, CheckCircleIcon, ClockIcon,
  ExclamationTriangleIcon, PlusIcon, ArrowUpTrayIcon,
} from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface Policy {
  policy_id: string;
  title: string;
  policy_type: string;
  status: string;
  owner: string;
  version: string;
  effective_date?: string;
  next_review_date?: string;
  acknowledgment_rate?: number;
  total_acknowledgments?: number;
  pending_acknowledgments?: number;
  created_at: string;
}

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  submitted: 'bg-blue-100 text-blue-700',
  under_review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-700',
  published: 'bg-indigo-100 text-indigo-700',
  archived: 'bg-gray-100 text-gray-500',
  retired: 'bg-red-100 text-red-700',
};

export function PolicyList() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    title: '', policy_type: 'corporate', owner: '', description: '',
    version: '1.0', review_frequency: 'annual',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['policies', statusFilter],
    queryFn: () => api.get('/policies', { params: statusFilter ? { status: statusFilter } : {} }).then(r => r.data),
    refetchInterval: 60000,
  });

  const { data: dueReview } = useQuery({
    queryKey: ['policies-due-review'],
    queryFn: () => api.get('/policies/due-review').then(r => r.data),
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/policies', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['policies'] }); setShowCreate(false); setForm({ title: '', policy_type: 'corporate', owner: '', description: '', version: '1.0', review_frequency: 'annual' }); },
  });

  const publishMut = useMutation({
    mutationFn: ({ id, published_by }: { id: string; published_by: string }) =>
      api.put(`/policies/${id}/publish`, { published_by }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['policies'] }),
  });

  const policies: Policy[] = data?.policies || [];

  const totalPublished = policies.filter(p => p.status === 'published').length;
  const totalDraft = policies.filter(p => p.status === 'draft').length;
  const dueReviewCount = dueReview?.policies?.length || 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Policy Hub"
        subtitle="Manage policy lifecycle from draft to retirement"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors">
            <PlusIcon className="h-4 w-4" /> New Policy
          </button>
        }
      />

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Total Policies" value={policies.length || '—'} icon={DocumentTextIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Published" value={totalPublished || '—'} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Drafts" value={totalDraft || '—'} icon={DocumentTextIcon} iconBgColor="stat-icon-gray" iconColor="" />
        <StatCard title="Due Review" value={dueReviewCount || '—'} icon={ClockIcon} iconBgColor={dueReviewCount > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
      </div>

      {/* Due review alert */}
      {dueReviewCount > 0 && (
        <Card>
          <div className="flex items-center gap-2 mb-3">
            <ExclamationTriangleIcon className="h-4 w-4 text-orange-500" />
            <h2 className="text-sm font-semibold text-gray-900">Policies Due for Review</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {(dueReview?.policies || []).map((p: Policy) => (
              <span key={p.policy_id} className="inline-block px-3 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                {p.title}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Filter + Table */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-900">Policy Register</h2>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-xs">
            <option value="">All Statuses</option>
            {['draft', 'submitted', 'under_review', 'approved', 'published', 'archived', 'retired'].map(s => (
              <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : policies.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No policies found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Title', 'Type', 'Status', 'Version', 'Owner', 'Next Review', 'Ack Rate', 'Actions'].map(h => (
                    <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {policies.map(p => (
                  <tr key={p.policy_id}>
                    <td className="py-2 pr-4 max-w-[220px]">
                      <div className="font-medium text-gray-900 truncate">{p.title}</div>
                      <div className="text-xs text-gray-400">{p.policy_id}</div>
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600 capitalize">{p.policy_type}</td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[p.status] || 'bg-gray-100 text-gray-600'}`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600">v{p.version}</td>
                    <td className="py-2 pr-4 text-xs text-gray-600">{p.owner || '—'}</td>
                    <td className="py-2 pr-4 text-xs text-gray-600">
                      {p.next_review_date ? new Date(p.next_review_date).toLocaleDateString() : '—'}
                    </td>
                    <td className="py-2 pr-4">
                      {p.acknowledgment_rate != null ? (
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-gray-200 rounded-full h-1.5">
                            <div className="h-1.5 rounded-full bg-indigo-500" style={{ width: `${p.acknowledgment_rate}%` }} />
                          </div>
                          <span className="text-xs text-gray-600">{p.acknowledgment_rate}%</span>
                        </div>
                      ) : <span className="text-xs text-gray-400">—</span>}
                    </td>
                    <td className="py-2 flex gap-2">
                      {p.status === 'approved' && (
                        <button onClick={() => publishMut.mutate({ id: p.policy_id, published_by: 'current_user' })}
                          className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                          <ArrowUpTrayIcon className="h-3 w-3" /> Publish
                        </button>
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
            <h3 className="text-base font-semibold text-gray-900">Create New Policy</h3>
            <div className="grid grid-cols-1 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Type</label>
                  <select value={form.policy_type} onChange={e => setForm(f => ({ ...f, policy_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['corporate', 'it_security', 'hr', 'finance', 'compliance', 'operational'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Review Frequency</label>
                  <select value={form.review_frequency} onChange={e => setForm(f => ({ ...f, review_frequency: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['monthly', 'quarterly', 'semi_annual', 'annual', 'biennial'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Owner</label>
                <input value={form.owner} onChange={e => setForm(f => ({ ...f, owner: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={3} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate(form)} disabled={createMut.isPending || !form.title}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Creating…' : 'Create Policy'}
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
