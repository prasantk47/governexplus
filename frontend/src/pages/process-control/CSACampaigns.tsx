import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ClipboardDocumentCheckIcon, ClockIcon, CheckCircleIcon, PlusIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface CSA {
  assessment_id: string;
  control_id: string;
  assessor_id?: string;
  assessor_name?: string;
  period: string;
  status: string;
  design_effectiveness?: string;
  operating_effectiveness?: string;
  overall_rating?: string;
  questionnaire_responses?: Record<string, any>;
  submitted_at?: string;
  due_date?: string;
  created_at: string;
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  in_progress: 'bg-blue-100 text-blue-700',
  submitted: 'bg-indigo-100 text-indigo-700',
  reviewed: 'bg-green-100 text-green-700',
  overdue: 'bg-red-100 text-red-700',
};

const ratingColors: Record<string, string> = {
  effective: 'text-green-600',
  partially_effective: 'text-yellow-600',
  ineffective: 'text-red-600',
  not_tested: 'text-gray-400',
};

export function CSACampaigns() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  const [submitForm, setSubmitForm] = useState({
    design_effectiveness: 'effective',
    operating_effectiveness: 'effective',
    overall_rating: 'effective',
    notes: '',
  });
  const [form, setForm] = useState({
    control_id: '', assessor_name: '', period: '',
    due_date: '', description: '',
  });

  const { data: pending, isLoading } = useQuery({
    queryKey: ['csa-pending'],
    queryFn: () => api.get('/process-control/self-assessments/pending').then(r => r.data),
    refetchInterval: 60000,
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api.post('/process-control/self-assessment-campaigns', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['csa-pending'] }); setShowCreate(false); },
  });

  const submitMut = useMutation({
    mutationFn: ({ id, ...body }: any) =>
      api.put(`/process-control/self-assessments/${id}/submit`, body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['csa-pending'] }); setSubmittingId(null); },
  });

  const assessments: CSA[] = pending?.assessments || [];
  const overdue = assessments.filter(a => a.status === 'overdue').length;
  const submitted = assessments.filter(a => a.status === 'submitted').length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Control Self-Assessment"
        subtitle="CSA campaigns — control owners assess their own controls"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            <PlusIcon className="h-4 w-4" /> New Campaign
          </button>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <StatCard title="Pending Assessments" value={assessments.length || '—'} icon={ClipboardDocumentCheckIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Overdue" value={overdue || '—'} icon={ClockIcon} iconBgColor={overdue > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Submitted" value={submitted || '—'} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
      </div>

      <Card>
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Pending Self-Assessments</h2>
        {isLoading ? (
          <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
        ) : assessments.length === 0 ? (
          <div className="text-xs text-gray-400 text-center py-8">No pending assessments</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Control ID', 'Assessor', 'Period', 'Status', 'Due Date', 'Design', 'Operating', 'Actions'].map(h => (
                    <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {assessments.map(a => (
                  <tr key={a.assessment_id} className={a.status === 'overdue' ? 'bg-red-50/30' : ''}>
                    <td className="py-2 pr-4 text-xs font-medium text-gray-900">{a.control_id}</td>
                    <td className="py-2 pr-4 text-xs text-gray-600">{a.assessor_name || '—'}</td>
                    <td className="py-2 pr-4 text-xs text-gray-600">{a.period || '—'}</td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[a.status] || 'bg-gray-100 text-gray-600'}`}>
                        {a.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-600">
                      {a.due_date ? new Date(a.due_date).toLocaleDateString() : '—'}
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`text-xs font-medium capitalize ${ratingColors[a.design_effectiveness || ''] || 'text-gray-400'}`}>
                        {a.design_effectiveness?.replace(/_/g, ' ') || '—'}
                      </span>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`text-xs font-medium capitalize ${ratingColors[a.operating_effectiveness || ''] || 'text-gray-400'}`}>
                        {a.operating_effectiveness?.replace(/_/g, ' ') || '—'}
                      </span>
                    </td>
                    <td className="py-2">
                      {a.status !== 'submitted' && a.status !== 'reviewed' && (
                        <button onClick={() => setSubmittingId(a.assessment_id)}
                          className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">Submit</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Submit assessment modal */}
      {submittingId && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Submit Self-Assessment</h3>
            <div className="space-y-3">
              {[
                { key: 'design_effectiveness', label: 'Design Effectiveness' },
                { key: 'operating_effectiveness', label: 'Operating Effectiveness' },
                { key: 'overall_rating', label: 'Overall Rating' },
              ].map(field => (
                <div key={field.key}>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{field.label}</label>
                  <select value={(submitForm as any)[field.key]}
                    onChange={e => setSubmitForm(f => ({ ...f, [field.key]: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['effective', 'partially_effective', 'ineffective', 'not_tested'].map(o => (
                      <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
              ))}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Notes</label>
                <textarea value={submitForm.notes} onChange={e => setSubmitForm(f => ({ ...f, notes: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={() => submitMut.mutate({ id: submittingId, ...submitForm })}
                disabled={submitMut.isPending}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {submitMut.isPending ? 'Submitting…' : 'Submit'}
              </button>
              <button onClick={() => setSubmittingId(null)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Create campaign modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Create CSA Campaign</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Control ID *</label>
                <input value={form.control_id} onChange={e => setForm(f => ({ ...f, control_id: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="e.g. CTRL-001" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Assessor Name</label>
                  <input value={form.assessor_name} onChange={e => setForm(f => ({ ...f, assessor_name: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Period</label>
                  <input value={form.period} onChange={e => setForm(f => ({ ...f, period: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="e.g. Q4 2026" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Due Date</label>
                <input type="date" value={form.due_date} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createMut.mutate(form)} disabled={createMut.isPending || !form.control_id}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Creating…' : 'Create Campaign'}
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
