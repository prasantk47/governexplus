import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShieldCheckIcon, DocumentCheckIcon, ClipboardDocumentListIcon, PlusIcon, CheckIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

type TabType = 'controls' | 'signoffs' | 'close-tasks';

const effectivenessColor: Record<string, string> = {
  effective: 'bg-green-100 text-green-700',
  deficiency: 'bg-yellow-100 text-yellow-800',
  significant_deficiency: 'bg-orange-100 text-orange-700',
  material_weakness: 'bg-red-100 text-red-700',
  not_tested: 'bg-gray-100 text-gray-500',
};

const signoffStatusColor: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  signed: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  escalated: 'bg-orange-100 text-orange-700',
};

export function SOXICFRModule() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<TabType>('controls');
  const [showCreateControl, setShowCreateControl] = useState(false);
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [showCreateSignoff, setShowCreateSignoff] = useState(false);
  const [signingId, setSigningId] = useState<string | null>(null);

  const [ctrlForm, setCtrlForm] = useState({
    title: '', financial_statement_area: '', process_name: '',
    control_owner: '', control_type: 'process_level', frequency: 'monthly',
    sox_section: '404', is_key_control: true, is_automated: false,
  });
  const [taskForm, setTaskForm] = useState({
    period: '', title: '', task_type: 'reconciliation',
    assigned_to: '', due_date: '', is_critical_path: false,
  });
  const [signoffForm, setSignoffForm] = useState({
    period: '', sox_section: '404', signoff_type: 'cfo',
    signer_name: '', signer_title: '',
  });
  const [signForm, setSignForm] = useState({
    conclusion: 'effective', conclusion_notes: '', exceptions_noted: '',
  });

  const { data: summaryData } = useQuery({
    queryKey: ['icfr-summary'],
    queryFn: () => api.get('/sox-icfr/summary').then(r => r.data),
  });

  const { data: controlsData, isLoading: ctrlLoading } = useQuery({
    queryKey: ['icfr-controls'],
    queryFn: () => api.get('/sox-icfr/controls').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data: signoffsData, isLoading: soLoading } = useQuery({
    queryKey: ['sox-signoffs'],
    queryFn: () => api.get('/sox-icfr/signoffs').then(r => r.data),
    enabled: tab === 'signoffs',
  });

  const { data: tasksData, isLoading: taskLoading } = useQuery({
    queryKey: ['close-tasks'],
    queryFn: () => api.get('/sox-icfr/close-tasks').then(r => r.data),
    enabled: tab === 'close-tasks',
  });

  const createCtrlMut = useMutation({
    mutationFn: (body: any) => api.post('/sox-icfr/controls', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['icfr-controls'] }); qc.invalidateQueries({ queryKey: ['icfr-summary'] }); setShowCreateControl(false); },
  });

  const createSignoffMut = useMutation({
    mutationFn: (body: any) => api.post('/sox-icfr/signoffs', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sox-signoffs'] }); setShowCreateSignoff(false); },
  });

  const signMut = useMutation({
    mutationFn: ({ id, ...body }: any) => api.post(`/sox-icfr/signoffs/${id}/sign`, body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sox-signoffs'] }); setSigningId(null); },
  });

  const createTaskMut = useMutation({
    mutationFn: (body: any) => api.post('/sox-icfr/close-tasks', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['close-tasks'] }); setShowCreateTask(false); },
  });

  const completeTaskMut = useMutation({
    mutationFn: (task_id: string) => api.put(`/sox-icfr/close-tasks/${task_id}/complete`, { completed_by: 'current_user' }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['close-tasks'] }),
  });

  const summary = summaryData || {};
  const controls = controlsData?.controls || [];
  const signoffs = signoffsData?.signoffs || [];
  const tasks = tasksData?.tasks || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="SOX / ICFR"
        subtitle="Internal Controls over Financial Reporting — SOX 302 & 404 compliance"
        actions={
          <div className="flex gap-2">
            {tab === 'controls' && (
              <button onClick={() => setShowCreateControl(true)}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
                <PlusIcon className="h-4 w-4" /> Add Control
              </button>
            )}
            {tab === 'signoffs' && (
              <button onClick={() => setShowCreateSignoff(true)}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
                <PlusIcon className="h-4 w-4" /> New Sign-off
              </button>
            )}
            {tab === 'close-tasks' && (
              <button onClick={() => setShowCreateTask(true)}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
                <PlusIcon className="h-4 w-4" /> Add Task
              </button>
            )}
          </div>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Key Controls" value={summary.key_controls ?? '—'} icon={ShieldCheckIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Effectiveness" value={summary.effectiveness_rate != null ? `${summary.effectiveness_rate}%` : '—'} icon={DocumentCheckIcon} iconBgColor={summary.effectiveness_rate >= 80 ? 'stat-icon-green' : 'stat-icon-orange'} iconColor="" />
        <StatCard title="Material Weaknesses" value={summary.material_weaknesses ?? '—'} icon={ShieldCheckIcon} iconBgColor={summary.material_weaknesses > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Not Tested" value={summary.not_tested ?? '—'} icon={ClipboardDocumentListIcon} iconBgColor={summary.not_tested > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
      </div>

      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl w-fit">
        {(['controls', 'signoffs', 'close-tasks'] as TabType[]).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${tab === t ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
            {t.replace(/-/g, ' ')}
          </button>
        ))}
      </div>

      {tab === 'controls' && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4">ICFR Control Matrix</h2>
          {ctrlLoading ? <div className="text-xs text-gray-400 text-center py-8">Loading...</div> : controls.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-8">No ICFR controls defined</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-gray-100">
                  {['Control', 'Process', 'Owner', 'Type', 'Key', 'SOX', 'Effectiveness'].map(h => (
                    <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                  ))}
                </tr></thead>
                <tbody className="divide-y divide-gray-50">
                  {controls.map((c: any) => (
                    <tr key={c.control_id}>
                      <td className="py-2 pr-4">
                        <div className="text-xs font-medium text-gray-900">{c.title}</div>
                        <div className="text-xs text-gray-400">{c.control_id}</div>
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-600">{c.process_name || '—'}</td>
                      <td className="py-2 pr-4 text-xs text-gray-600">{c.control_owner || '—'}</td>
                      <td className="py-2 pr-4 text-xs text-gray-600 capitalize">{(c.control_type || '').replace(/_/g, ' ')}</td>
                      <td className="py-2 pr-4">
                        {c.is_key_control ? <span className="text-xs font-bold text-indigo-600">KEY</span> : <span className="text-xs text-gray-400">—</span>}
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-600">{c.sox_section}</td>
                      <td className="py-2 pr-4">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${effectivenessColor[c.overall_effectiveness] || 'bg-gray-100 text-gray-500'}`}>
                          {(c.overall_effectiveness || 'not_tested').replace(/_/g, ' ')}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {tab === 'signoffs' && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Management Sign-offs</h2>
          {soLoading ? <div className="text-xs text-gray-400 text-center py-8">Loading...</div> : signoffs.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-8">No sign-offs recorded</div>
          ) : (
            <div className="space-y-3">
              {signoffs.map((s: any) => (
                <div key={s.signoff_id} className="flex items-center justify-between p-3 border border-gray-100 rounded-xl">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{s.signer_name} — {s.signer_title}</div>
                    <div className="text-xs text-gray-500 mt-0.5">SOX §{s.sox_section} · {s.period} · {s.signoff_type?.toUpperCase()}</div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {s.total_key_controls} key controls · {s.material_weaknesses} material weaknesses
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${signoffStatusColor[s.status] || 'bg-gray-100 text-gray-500'}`}>
                      {s.status}
                    </span>
                    {s.status === 'pending' && (
                      <button onClick={() => setSigningId(s.signoff_id)}
                        className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                        <CheckIcon className="h-3.5 w-3.5" /> Sign
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {tab === 'close-tasks' && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Financial Close Checklist</h2>
          {taskLoading ? <div className="text-xs text-gray-400 text-center py-8">Loading...</div> : tasks.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-8">No close tasks defined</div>
          ) : (
            <div className="space-y-2">
              {tasks.map((t: any) => (
                <div key={t.task_id} className={`flex items-center justify-between p-3 border rounded-xl ${t.is_critical_path ? 'border-orange-200 bg-orange-50/30' : 'border-gray-100'}`}>
                  <div className="flex items-center gap-3">
                    <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${t.status === 'completed' ? 'bg-green-500 border-green-500' : 'border-gray-300'}`}>
                      {t.status === 'completed' && <CheckIcon className="h-2.5 w-2.5 text-white" />}
                    </div>
                    <div>
                      <div className={`text-xs font-medium ${t.status === 'completed' ? 'text-gray-400 line-through' : 'text-gray-900'}`}>{t.title}</div>
                      <div className="text-xs text-gray-400">{t.assigned_to || 'Unassigned'} · {t.period} · {t.task_type}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {t.is_critical_path && <span className="text-xs font-medium text-orange-600">Critical</span>}
                    {t.due_date && <span className="text-xs text-gray-500">{new Date(t.due_date).toLocaleDateString()}</span>}
                    {t.status !== 'completed' && (
                      <button onClick={() => completeTaskMut.mutate(t.task_id)}
                        className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">Complete</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Create Control Modal */}
      {showCreateControl && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Add ICFR Control</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Control Title *</label>
                <input value={ctrlForm.title} onChange={e => setCtrlForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Financial Statement Area</label>
                  <input value={ctrlForm.financial_statement_area} onChange={e => setCtrlForm(f => ({ ...f, financial_statement_area: e.target.value }))}
                    placeholder="e.g. Revenue" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Process Name</label>
                  <input value={ctrlForm.process_name} onChange={e => setCtrlForm(f => ({ ...f, process_name: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Type</label>
                  <select value={ctrlForm.control_type} onChange={e => setCtrlForm(f => ({ ...f, control_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['entity_level', 'process_level', 'it_general', 'it_application'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">SOX §</label>
                  <select value={ctrlForm.sox_section} onChange={e => setCtrlForm(f => ({ ...f, sox_section: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    <option value="302">302</option>
                    <option value="404">404</option>
                  </select>
                </div>
                <div className="flex items-end pb-2">
                  <label className="flex items-center gap-2 text-xs font-medium text-gray-700 cursor-pointer">
                    <input type="checkbox" checked={ctrlForm.is_key_control}
                      onChange={e => setCtrlForm(f => ({ ...f, is_key_control: e.target.checked }))} className="rounded" />
                    Key Control
                  </label>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Control Owner</label>
                <input value={ctrlForm.control_owner} onChange={e => setCtrlForm(f => ({ ...f, control_owner: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createCtrlMut.mutate(ctrlForm)}
                disabled={createCtrlMut.isPending || !ctrlForm.title}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createCtrlMut.isPending ? 'Adding…' : 'Add Control'}
              </button>
              <button onClick={() => setShowCreateControl(false)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Sign modal */}
      {signingId && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Sign Off</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Conclusion</label>
                <select value={signForm.conclusion} onChange={e => setSignForm(f => ({ ...f, conclusion: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="effective">Effective</option>
                  <option value="ineffective">Ineffective</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Conclusion Notes</label>
                <textarea value={signForm.conclusion_notes} onChange={e => setSignForm(f => ({ ...f, conclusion_notes: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Exceptions Noted</label>
                <textarea value={signForm.exceptions_noted} onChange={e => setSignForm(f => ({ ...f, exceptions_noted: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={() => signMut.mutate({ id: signingId, ...signForm })}
                disabled={signMut.isPending}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {signMut.isPending ? 'Signing…' : 'Sign'}
              </button>
              <button onClick={() => setSigningId(null)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Sign-off Modal */}
      {showCreateSignoff && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Create Sign-off Request</h3>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Period *</label>
                  <input value={signoffForm.period} onChange={e => setSignoffForm(f => ({ ...f, period: e.target.value }))}
                    placeholder="e.g. Q4 2026" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">SOX Section</label>
                  <select value={signoffForm.sox_section} onChange={e => setSignoffForm(f => ({ ...f, sox_section: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    <option value="302">302</option>
                    <option value="404">404</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Signoff Type</label>
                  <select value={signoffForm.signoff_type} onChange={e => setSignoffForm(f => ({ ...f, signoff_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['ceo', 'cfo', 'controller', 'external_auditor'].map(t => (
                      <option key={t} value={t}>{t.toUpperCase()}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Signer Name *</label>
                  <input value={signoffForm.signer_name} onChange={e => setSignoffForm(f => ({ ...f, signer_name: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title</label>
                <input value={signoffForm.signer_title} onChange={e => setSignoffForm(f => ({ ...f, signer_title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createSignoffMut.mutate(signoffForm)}
                disabled={createSignoffMut.isPending || !signoffForm.signer_name || !signoffForm.period}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createSignoffMut.isPending ? 'Creating…' : 'Create Sign-off'}
              </button>
              <button onClick={() => setShowCreateSignoff(false)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Task Modal */}
      {showCreateTask && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Add Close Task</h3>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Period *</label>
                  <input value={taskForm.period} onChange={e => setTaskForm(f => ({ ...f, period: e.target.value }))}
                    placeholder="e.g. Q4 2026" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Task Type</label>
                  <select value={taskForm.task_type} onChange={e => setTaskForm(f => ({ ...f, task_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['reconciliation', 'journal', 'approval', 'review', 'disclosure', 'sign_off'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
                <input value={taskForm.title} onChange={e => setTaskForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Assigned To</label>
                  <input value={taskForm.assigned_to} onChange={e => setTaskForm(f => ({ ...f, assigned_to: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Due Date</label>
                  <input type="date" value={taskForm.due_date} onChange={e => setTaskForm(f => ({ ...f, due_date: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createTaskMut.mutate(taskForm)}
                disabled={createTaskMut.isPending || !taskForm.title || !taskForm.period}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createTaskMut.isPending ? 'Adding…' : 'Add Task'}
              </button>
              <button onClick={() => setShowCreateTask(false)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
