import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DocumentTextIcon, CheckBadgeIcon, ClockIcon, PlusIcon,
  PencilSquareIcon, ArrowUpTrayIcon,
} from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import api from '../../services/api';

interface Engagement {
  engagement_id: string;
  title: string;
}

interface Workpaper {
  workpaper_id: string;
  title: string;
  workpaper_type: string;
  status: string;
  review_status: string;
  prepared_by: string;
  reviewed_by?: string;
  file_name?: string;
  file_size?: number;
  content?: string;
  procedure_id?: string;
  created_at: string;
  updated_at?: string;
}

const reviewColors: Record<string, string> = {
  pending_review: 'bg-yellow-100 text-yellow-800',
  in_review: 'bg-blue-100 text-blue-700',
  reviewed: 'bg-indigo-100 text-indigo-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
};

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  final: 'bg-green-100 text-green-700',
  superseded: 'bg-gray-100 text-gray-500',
};

export function AuditWorkpapers() {
  const qc = useQueryClient();
  const [selectedEngagementId, setSelectedEngagementId] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    title: '', workpaper_type: 'narrative', prepared_by: '',
    content: '', file_name: '',
  });

  const { data: engagementsData } = useQuery({
    queryKey: ['audit-engagements'],
    queryFn: () => api.get('/audit-management/engagements').then(r => r.data),
  });

  const engagements: Engagement[] = engagementsData?.engagements || [];

  const { data: workpapersData, isLoading } = useQuery({
    queryKey: ['audit-workpapers', selectedEngagementId],
    queryFn: () => selectedEngagementId
      ? api.get(`/audit-management/engagements/${selectedEngagementId}/workpapers`).then(r => r.data)
      : Promise.resolve({ workpapers: [] }),
    enabled: !!selectedEngagementId,
  });

  const createMut = useMutation({
    mutationFn: (body: any) =>
      api.post(`/audit-management/engagements/${selectedEngagementId}/workpapers`, body).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['audit-workpapers', selectedEngagementId] });
      setShowCreate(false);
      setForm({ title: '', workpaper_type: 'narrative', prepared_by: '', content: '', file_name: '' });
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, ...body }: { id: string; [k: string]: any }) =>
      api.put(`/audit-management/workpapers/${id}`, body).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['audit-workpapers', selectedEngagementId] }),
  });

  const workpapers: Workpaper[] = workpapersData?.workpapers || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Workpapers"
        subtitle="Electronic workpaper management with e-sign-off and version control"
        actions={
          selectedEngagementId ? (
            <button onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors">
              <PlusIcon className="h-4 w-4" /> New Workpaper
            </button>
          ) : null
        }
      />

      {/* Engagement selector */}
      <Card>
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700 whitespace-nowrap">Select Engagement</label>
          <select
            value={selectedEngagementId}
            onChange={e => setSelectedEngagementId(e.target.value)}
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">— Select an audit engagement —</option>
            {engagements.map(e => (
              <option key={e.engagement_id} value={e.engagement_id}>{e.title} ({e.engagement_id})</option>
            ))}
          </select>
        </div>
      </Card>

      {selectedEngagementId && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Workpapers</h2>
          {isLoading ? (
            <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
          ) : workpapers.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-8">No workpapers for this engagement</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    {['Title', 'Type', 'Status', 'Review Status', 'Prepared By', 'Reviewed By', 'Last Updated', 'Actions'].map(h => (
                      <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {workpapers.map(wp => (
                    <tr key={wp.workpaper_id}>
                      <td className="py-2 pr-4 max-w-[200px]">
                        <div className="font-medium text-gray-900 truncate flex items-center gap-1">
                          <DocumentTextIcon className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                          {wp.title}
                        </div>
                        <div className="text-xs text-gray-400">{wp.workpaper_id}</div>
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-600 capitalize">{wp.workpaper_type?.replace(/_/g, ' ')}</td>
                      <td className="py-2 pr-4">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[wp.status] || 'bg-gray-100 text-gray-600'}`}>
                          {wp.status}
                        </span>
                      </td>
                      <td className="py-2 pr-4">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${reviewColors[wp.review_status] || 'bg-gray-100 text-gray-600'}`}>
                          {wp.review_status?.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-600">{wp.prepared_by}</td>
                      <td className="py-2 pr-4 text-xs text-gray-600">{wp.reviewed_by || '—'}</td>
                      <td className="py-2 pr-4 text-xs text-gray-600">
                        {wp.updated_at ? new Date(wp.updated_at).toLocaleDateString() : new Date(wp.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-2">
                        <div className="flex gap-2">
                          {wp.review_status === 'pending_review' && (
                            <button
                              onClick={() => updateMut.mutate({ id: wp.workpaper_id, review_status: 'reviewed', reviewed_by: 'current_user' })}
                              className="flex items-center gap-1 text-xs text-green-600 hover:text-green-800 font-medium">
                              <CheckBadgeIcon className="h-3.5 w-3.5" /> Sign Off
                            </button>
                          )}
                          {wp.status === 'draft' && (
                            <button
                              onClick={() => updateMut.mutate({ id: wp.workpaper_id, status: 'final' })}
                              className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                              <ArrowUpTrayIcon className="h-3.5 w-3.5" /> Finalize
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
      )}

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">New Workpaper</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Type</label>
                  <select value={form.workpaper_type} onChange={e => setForm(f => ({ ...f, workpaper_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['narrative', 'test_of_controls', 'substantive', 'analytical', 'lead_schedule', 'flowchart'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Prepared By *</label>
                  <input value={form.prepared_by} onChange={e => setForm(f => ({ ...f, prepared_by: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Content</label>
                <textarea value={form.content} onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
                  rows={4} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono text-xs"
                  placeholder="Workpaper content, findings, notes..." />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate(form)} disabled={createMut.isPending || !form.title || !form.prepared_by}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Creating…' : 'Create Workpaper'}
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
