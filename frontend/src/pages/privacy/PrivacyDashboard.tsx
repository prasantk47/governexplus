import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShieldCheckIcon, ExclamationTriangleIcon, DocumentTextIcon, PlusIcon, ClockIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

type TabType = 'activities' | 'dsar' | 'dpia' | 'breaches';

const breachSeverityColor: Record<string, string> = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

const dsarTypeColor: Record<string, string> = {
  access: 'bg-blue-100 text-blue-700',
  erasure: 'bg-red-100 text-red-700',
  rectification: 'bg-yellow-100 text-yellow-800',
  portability: 'bg-purple-100 text-purple-700',
  restriction: 'bg-orange-100 text-orange-700',
  objection: 'bg-gray-100 text-gray-700',
};

export function PrivacyDashboard() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<TabType>('activities');
  const [showCreateActivity, setShowCreateActivity] = useState(false);
  const [showCreateDsar, setShowCreateDsar] = useState(false);
  const [showCreateBreach, setShowCreateBreach] = useState(false);

  const [activityForm, setActivityForm] = useState({
    name: '', purpose: '', legal_basis: 'legitimate_interest',
    transfers_outside_eea: false, dpia_required: false, business_owner: '',
  });
  const [dsarForm, setDsarForm] = useState({
    subject_name: '', subject_email: '', request_type: 'access', description: '',
  });
  const [breachForm, setBreachForm] = useState({
    title: '', description: '', severity: 'medium', breach_type: 'unauthorized_access',
    regulator_notification_required: false,
  });

  const { data: dashData } = useQuery({
    queryKey: ['privacy-dashboard'],
    queryFn: () => api.get('/privacy/dashboard').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data: activitiesData, isLoading: actLoading } = useQuery({
    queryKey: ['processing-activities'],
    queryFn: () => api.get('/privacy/processing-activities').then(r => r.data),
    enabled: tab === 'activities',
  });

  const { data: dsarData, isLoading: dsarLoading } = useQuery({
    queryKey: ['dsar-requests'],
    queryFn: () => api.get('/privacy/dsar').then(r => r.data),
    enabled: tab === 'dsar',
  });

  const { data: dpiaData, isLoading: dpiaLoading } = useQuery({
    queryKey: ['dpia-assessments'],
    queryFn: () => api.get('/privacy/dpia').then(r => r.data),
    enabled: tab === 'dpia',
  });

  const { data: breachData, isLoading: breachLoading } = useQuery({
    queryKey: ['data-breaches'],
    queryFn: () => api.get('/privacy/breaches').then(r => r.data),
    enabled: tab === 'breaches',
  });

  const createActivityMut = useMutation({
    mutationFn: (body: any) => api.post('/privacy/processing-activities', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['processing-activities'] }); qc.invalidateQueries({ queryKey: ['privacy-dashboard'] }); setShowCreateActivity(false); },
  });

  const createDsarMut = useMutation({
    mutationFn: (body: any) => api.post('/privacy/dsar', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['dsar-requests'] }); qc.invalidateQueries({ queryKey: ['privacy-dashboard'] }); setShowCreateDsar(false); },
  });

  const createBreachMut = useMutation({
    mutationFn: (body: any) => api.post('/privacy/breaches', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['data-breaches'] }); qc.invalidateQueries({ queryKey: ['privacy-dashboard'] }); setShowCreateBreach(false); },
  });

  const updateDsarMut = useMutation({
    mutationFn: ({ id, ...body }: any) => api.put(`/privacy/dsar/${id}/status`, body).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dsar-requests'] }),
  });

  const dash = dashData || {};
  const activities = activitiesData?.activities || [];
  const dsars = dsarData?.requests || [];
  const dpias = dpiaData?.assessments || [];
  const breaches = breachData?.breaches || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Privacy & GDPR"
        subtitle="Data protection, subject rights, impact assessments and breach management"
        actions={
          <div className="flex gap-2">
            {tab === 'activities' && <button onClick={() => setShowCreateActivity(true)} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"><PlusIcon className="h-4 w-4" /> Add Activity</button>}
            {tab === 'dsar' && <button onClick={() => setShowCreateDsar(true)} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"><PlusIcon className="h-4 w-4" /> New DSAR</button>}
            {tab === 'breaches' && <button onClick={() => setShowCreateBreach(true)} className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"><PlusIcon className="h-4 w-4" /> Report Breach</button>}
          </div>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Processing Activities" value={dash.processing_activities ?? '—'} icon={DocumentTextIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Open DSARs" value={dash.open_dsars ?? '—'} icon={ClockIcon} iconBgColor={dash.overdue_dsars > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Open Breaches" value={dash.open_breaches ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={dash.open_breaches > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Unnotified Regulator" value={dash.unnotified_regulator ?? '—'} icon={ShieldCheckIcon} iconBgColor={dash.unnotified_regulator > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
      </div>

      {dash.unnotified_regulator > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
            <span className="text-sm font-semibold text-red-800">
              {dash.unnotified_regulator} breach(es) require regulator notification within 72 hours (GDPR Article 33)
            </span>
          </div>
        </div>
      )}

      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl w-fit">
        {(['activities', 'dsar', 'dpia', 'breaches'] as TabType[]).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${tab === t ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
            {t === 'dsar' ? 'DSAR' : t === 'dpia' ? 'DPIA' : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === 'activities' && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Article 30 — Record of Processing Activities</h2>
          {actLoading ? <div className="text-xs text-gray-400 text-center py-8">Loading...</div> : activities.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-8">No processing activities recorded</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-gray-100">
                  {['Activity', 'Purpose', 'Legal Basis', 'EEA Transfer', 'DPIA', 'Owner'].map(h => (
                    <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                  ))}
                </tr></thead>
                <tbody className="divide-y divide-gray-50">
                  {activities.map((a: any) => (
                    <tr key={a.activity_id}>
                      <td className="py-2 pr-4"><div className="text-xs font-medium text-gray-900">{a.name}</div></td>
                      <td className="py-2 pr-4 text-xs text-gray-600 max-w-xs truncate">{a.purpose}</td>
                      <td className="py-2 pr-4 text-xs text-gray-600 capitalize">{(a.legal_basis || '').replace(/_/g, ' ')}</td>
                      <td className="py-2 pr-4"><span className={`text-xs font-medium ${a.transfers_outside_eea ? 'text-orange-600' : 'text-green-600'}`}>{a.transfers_outside_eea ? 'Yes' : 'No'}</span></td>
                      <td className="py-2 pr-4"><span className={`text-xs font-medium ${a.dpia_required ? 'text-orange-600' : 'text-gray-400'}`}>{a.dpia_required ? 'Required' : 'Not required'}</span></td>
                      <td className="py-2 pr-4 text-xs text-gray-600">{a.business_owner || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {tab === 'dsar' && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Data Subject Access Requests</h2>
          {dsarLoading ? <div className="text-xs text-gray-400 text-center py-8">Loading...</div> : dsars.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-8">No DSAR requests</div>
          ) : (
            <div className="space-y-3">
              {dsars.map((r: any) => {
                const deadline = r.deadline ? new Date(r.deadline) : null;
                const isOverdue = deadline && deadline < new Date() && !['completed', 'rejected'].includes(r.status);
                return (
                  <div key={r.dsar_id} className={`flex items-center justify-between p-3 border rounded-xl ${isOverdue ? 'border-red-200 bg-red-50/30' : 'border-gray-100'}`}>
                    <div>
                      <div className="text-sm font-medium text-gray-900">{r.subject_name}</div>
                      <div className="text-xs text-gray-500">{r.subject_email}</div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${dsarTypeColor[r.request_type] || 'bg-gray-100 text-gray-600'}`}>
                          {r.request_type}
                        </span>
                        {deadline && <span className={`text-xs ${isOverdue ? 'text-red-600 font-medium' : 'text-gray-400'}`}>Due: {deadline.toLocaleDateString()}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${r.status === 'completed' ? 'bg-green-100 text-green-700' : r.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-800'}`}>
                        {r.status.replace(/_/g, ' ')}
                      </span>
                      {!['completed', 'rejected'].includes(r.status) && (
                        <button onClick={() => updateDsarMut.mutate({ id: r.dsar_id, status: 'in_progress' })}
                          className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                          {r.status === 'received' ? 'Start' : 'Update'}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}

      {tab === 'dpia' && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Data Protection Impact Assessments</h2>
          {dpiaLoading ? <div className="text-xs text-gray-400 text-center py-8">Loading...</div> : dpias.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-8">No DPIAs recorded</div>
          ) : (
            <div className="space-y-3">
              {dpias.map((d: any) => (
                <div key={d.dpia_id} className="flex items-center justify-between p-3 border border-gray-100 rounded-xl">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{d.title}</div>
                    {d.project_name && <div className="text-xs text-gray-500">{d.project_name}</div>}
                    <div className="text-xs text-gray-400 mt-0.5">{d.conducted_by || 'Unassigned'} · Risk: {d.overall_risk_level || 'Not assessed'}</div>
                  </div>
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${d.status === 'approved' ? 'bg-green-100 text-green-700' : d.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-800'}`}>
                    {d.status.replace(/_/g, ' ')}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {tab === 'breaches' && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Data Breach Incidents</h2>
          {breachLoading ? <div className="text-xs text-gray-400 text-center py-8">Loading...</div> : breaches.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-8">No breaches recorded</div>
          ) : (
            <div className="space-y-3">
              {breaches.map((b: any) => {
                const regDeadline = b.regulator_deadline ? new Date(b.regulator_deadline) : null;
                const regOverdue = regDeadline && regDeadline < new Date() && b.regulator_notification_required && !b.regulator_notified_at;
                return (
                  <div key={b.breach_id} className={`p-3 border rounded-xl ${regOverdue ? 'border-red-300 bg-red-50/40' : 'border-gray-100'}`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${breachSeverityColor[b.severity] || 'bg-gray-100 text-gray-500'}`}>
                            {b.severity}
                          </span>
                          <span className="text-sm font-medium text-gray-900">{b.title}</span>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">{b.breach_type?.replace(/_/g, ' ')} · {b.subjects_affected_count ?? 0} subjects</div>
                        {regDeadline && b.regulator_notification_required && (
                          <div className={`text-xs mt-0.5 font-medium ${regOverdue ? 'text-red-600' : 'text-orange-600'}`}>
                            Regulator deadline: {regDeadline.toLocaleString()} {b.regulator_notified_at ? '(Notified)' : '(Pending)'}
                          </div>
                        )}
                      </div>
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${b.status === 'closed' ? 'bg-gray-100 text-gray-500' : 'bg-orange-100 text-orange-700'}`}>
                        {b.status.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}

      {/* Create Activity Modal */}
      {showCreateActivity && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Add Processing Activity</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Activity Name *</label>
                <input value={activityForm.name} onChange={e => setActivityForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Purpose *</label>
                <textarea value={activityForm.purpose} onChange={e => setActivityForm(f => ({ ...f, purpose: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Legal Basis</label>
                  <select value={activityForm.legal_basis} onChange={e => setActivityForm(f => ({ ...f, legal_basis: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['consent', 'contract', 'legal_obligation', 'vital_interest', 'public_task', 'legitimate_interest'].map(b => (
                      <option key={b} value={b}>{b.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Business Owner</label>
                  <input value={activityForm.business_owner} onChange={e => setActivityForm(f => ({ ...f, business_owner: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-xs font-medium text-gray-700 cursor-pointer">
                  <input type="checkbox" checked={activityForm.transfers_outside_eea}
                    onChange={e => setActivityForm(f => ({ ...f, transfers_outside_eea: e.target.checked }))} className="rounded" />
                  EEA Transfers
                </label>
                <label className="flex items-center gap-2 text-xs font-medium text-gray-700 cursor-pointer">
                  <input type="checkbox" checked={activityForm.dpia_required}
                    onChange={e => setActivityForm(f => ({ ...f, dpia_required: e.target.checked }))} className="rounded" />
                  DPIA Required
                </label>
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createActivityMut.mutate(activityForm)}
                disabled={createActivityMut.isPending || !activityForm.name || !activityForm.purpose}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createActivityMut.isPending ? 'Adding…' : 'Add Activity'}
              </button>
              <button onClick={() => setShowCreateActivity(false)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Create DSAR Modal */}
      {showCreateDsar && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">New DSAR Request</h3>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Subject Name *</label>
                  <input value={dsarForm.subject_name} onChange={e => setDsarForm(f => ({ ...f, subject_name: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Subject Email *</label>
                  <input type="email" value={dsarForm.subject_email} onChange={e => setDsarForm(f => ({ ...f, subject_email: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Request Type</label>
                <select value={dsarForm.request_type} onChange={e => setDsarForm(f => ({ ...f, request_type: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  {['access', 'erasure', 'rectification', 'portability', 'restriction', 'objection'].map(t => (
                    <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea value={dsarForm.description} onChange={e => setDsarForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createDsarMut.mutate(dsarForm)}
                disabled={createDsarMut.isPending || !dsarForm.subject_name || !dsarForm.subject_email}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createDsarMut.isPending ? 'Creating…' : 'Create DSAR'}
              </button>
              <button onClick={() => setShowCreateDsar(false)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Breach Modal */}
      {showCreateBreach && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-red-700">Report Data Breach</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
                <input value={breachForm.title} onChange={e => setBreachForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description *</label>
                <textarea value={breachForm.description} onChange={e => setBreachForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Severity</label>
                  <select value={breachForm.severity} onChange={e => setBreachForm(f => ({ ...f, severity: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['low', 'medium', 'high', 'critical'].map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Breach Type</label>
                  <select value={breachForm.breach_type} onChange={e => setBreachForm(f => ({ ...f, breach_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['unauthorized_access', 'accidental_disclosure', 'ransomware', 'data_theft', 'system_misconfiguration'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
              </div>
              <label className="flex items-center gap-2 text-xs font-medium text-gray-700 cursor-pointer">
                <input type="checkbox" checked={breachForm.regulator_notification_required}
                  onChange={e => setBreachForm(f => ({ ...f, regulator_notification_required: e.target.checked }))} className="rounded" />
                Regulator notification required (triggers 72h countdown)
              </label>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createBreachMut.mutate(breachForm)}
                disabled={createBreachMut.isPending || !breachForm.title || !breachForm.description}
                className="flex-1 bg-red-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-red-700 disabled:opacity-50">
                {createBreachMut.isPending ? 'Reporting…' : 'Report Breach'}
              </button>
              <button onClick={() => setShowCreateBreach(false)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
