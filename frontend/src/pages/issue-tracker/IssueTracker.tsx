import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon, MagnifyingGlassIcon, ExclamationTriangleIcon,
  CheckCircleIcon, ClockIcon, ArrowRightIcon, FunnelIcon,
} from '@heroicons/react/24/outline';
import { PageHeader, Card, Button, Badge } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface Issue {
  issue_id: string;
  title: string;
  issue_type: string;
  source_module: string;
  severity: string;
  status: string;
  owner_name: string;
  due_date: string | null;
  created_at: string;
  remediation_progress: number;
  regulatory_impact: boolean;
  financial_impact: number | null;
}

interface Summary {
  total: number; open: number; overdue: number; critical_open: number; high_open: number;
  by_status: Record<string, number>; by_severity: Record<string, number>; by_module: Record<string, number>;
}

const severityColors: Record<string, string> = {
  critical: 'bg-red-100 text-red-700 border-red-200',
  high: 'bg-orange-100 text-orange-700 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  low: 'bg-blue-100 text-blue-700 border-blue-200',
  informational: 'bg-gray-100 text-gray-600 border-gray-200',
};

const statusVariant: Record<string, any> = {
  open: 'danger', assigned: 'warning', in_remediation: 'info',
  pending_validation: 'warning', closed: 'success', accepted: 'default', overdue: 'danger',
};

const issueTypes = [
  'control_deficiency','risk_exposure','audit_finding','access_violation',
  'fraud_case','vendor_issue','policy_breach','compliance_gap','operational',
];
const sourceModules = ['risk','control','audit','fraud','access','vendor','manual','ccm','compliance'];

interface CreateForm {
  title: string; description: string; issue_type: string; source_module: string;
  severity: string; owner_id: string; owner_name: string; due_date: string;
  remediation_plan: string; regulatory_impact: boolean; financial_impact: string;
}

export function IssueTracker() {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [moduleFilter, setModuleFilter] = useState('');
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<Issue | null>(null);
  const [form, setForm] = useState<CreateForm>({
    title: '', description: '', issue_type: 'operational', source_module: 'manual',
    severity: 'medium', owner_id: '', owner_name: '', due_date: '',
    remediation_plan: '', regulatory_impact: false, financial_impact: '',
  });

  const { data: summaryData } = useQuery<Summary>({
    queryKey: ['issue-summary'],
    queryFn: () => api.get('/issues/summary').then(r => r.data),
  });

  const { data: issuesData } = useQuery({
    queryKey: ['issues', statusFilter, severityFilter, moduleFilter, overdueOnly],
    queryFn: () => api.get('/issues', {
      params: {
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        source_module: moduleFilter || undefined,
        overdue_only: overdueOnly || undefined,
        limit: 200,
      }
    }).then(r => r.data),
  });

  const issues: Issue[] = issuesData?.issues || [];
  const filtered = issues.filter(i =>
    !search || i.title.toLowerCase().includes(search.toLowerCase()) || i.issue_id.includes(search)
  );

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/issues', data),
    onSuccess: () => {
      toast.success('Issue created');
      setShowCreate(false);
      setForm({ title: '', description: '', issue_type: 'operational', source_module: 'manual', severity: 'medium', owner_id: '', owner_name: '', due_date: '', remediation_plan: '', regulatory_impact: false, financial_impact: '' });
      qc.invalidateQueries({ queryKey: ['issues'] });
      qc.invalidateQueries({ queryKey: ['issue-summary'] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed to create issue'),
  });

  const statusMutation = useMutation({
    mutationFn: ({ issue_id, new_status, notes }: any) =>
      api.post(`/issues/${issue_id}/status`, { new_status, notes }),
    onSuccess: () => {
      toast.success('Status updated');
      qc.invalidateQueries({ queryKey: ['issues'] });
      qc.invalidateQueries({ queryKey: ['issue-summary'] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Invalid status transition'),
  });

  const s = summaryData;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Issue Tracker"
        subtitle="Common GRC issue lifecycle — risk, controls, audit, fraud, access, vendor"
        actions={
          <Button size="sm" icon={<PlusIcon className="h-4 w-4" />} onClick={() => setShowCreate(true)}>
            New Issue
          </Button>
        }
      />

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <StatCard title="Total Issues" value={s?.total ?? 0} icon={FunnelIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Open" value={s?.open ?? 0} icon={ExclamationTriangleIcon} iconBgColor={s?.open ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Overdue" value={s?.overdue ?? 0} icon={ClockIcon} iconBgColor={s?.overdue ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Critical Open" value={s?.critical_open ?? 0} icon={ExclamationTriangleIcon} iconBgColor={s?.critical_open ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="High Open" value={s?.high_open ?? 0} icon={ExclamationTriangleIcon} iconBgColor={s?.high_open ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-48">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg bg-white/50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Search issues..." value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          {[
            { label: 'Status', value: statusFilter, setter: setStatusFilter, options: ['open','assigned','in_remediation','pending_validation','closed','accepted','overdue'] },
            { label: 'Severity', value: severityFilter, setter: setSeverityFilter, options: ['critical','high','medium','low','informational'] },
            { label: 'Module', value: moduleFilter, setter: setModuleFilter, options: sourceModules },
          ].map(f => (
            <select key={f.label} className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white/50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={f.value} onChange={e => f.setter(e.target.value)}>
              <option value="">All {f.label}</option>
              {f.options.map(o => <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>)}
            </select>
          ))}
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={overdueOnly} onChange={e => setOverdueOnly(e.target.checked)} className="rounded" />
            Overdue only
          </label>
        </div>
      </Card>

      {/* Issue Table */}
      <Card padding="none">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/20 bg-gray-50/50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Issue</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type / Module</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Severity</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Owner</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Due</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Progress</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {filtered.length === 0 ? (
                <tr><td colSpan={8} className="px-4 py-10 text-center text-sm text-gray-400">No issues found</td></tr>
              ) : filtered.map(issue => {
                const isOverdue = issue.due_date && new Date(issue.due_date) < new Date() && !['closed','accepted'].includes(issue.status);
                return (
                  <tr key={issue.issue_id} className="hover:bg-white/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-start gap-2">
                        {issue.regulatory_impact && <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">REG</span>}
                        <div>
                          <div className="text-xs font-mono text-indigo-600">{issue.issue_id}</div>
                          <div className="text-sm font-medium text-gray-900 max-w-xs truncate">{issue.title}</div>
                          {issue.financial_impact && <div className="text-xs text-gray-400">Impact: ${issue.financial_impact.toLocaleString()}</div>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-xs font-medium text-gray-900">{issue.issue_type?.replace(/_/g, ' ')}</div>
                      <div className="text-xs text-gray-500">{issue.source_module}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${severityColors[issue.severity] || 'bg-gray-100 text-gray-600 border-gray-200'}`}>
                        {issue.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={statusVariant[issue.status] || 'default'} size="sm">
                        {issue.status?.replace(/_/g, ' ')}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">{issue.owner_name || '—'}</td>
                    <td className="px-4 py-3">
                      {issue.due_date ? (
                        <span className={`text-xs ${isOverdue ? 'text-red-600 font-semibold' : 'text-gray-500'}`}>
                          {new Date(issue.due_date).toLocaleDateString()}
                          {isOverdue && ' ⚠'}
                        </span>
                      ) : <span className="text-xs text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-1.5 w-16">
                          <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${issue.remediation_progress || 0}%` }} />
                        </div>
                        <span className="text-xs text-gray-500">{issue.remediation_progress || 0}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => setSelected(issue)} className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-0.5 ml-auto">
                        Manage <ArrowRightIcon className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Issue Detail Panel */}
      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="text-xs font-mono text-indigo-600 mb-1">{selected.issue_id}</div>
                <h2 className="text-lg font-semibold text-gray-900">{selected.title}</h2>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
              <div><span className="text-xs text-gray-500">Severity</span><div className="font-medium">{selected.severity}</div></div>
              <div><span className="text-xs text-gray-500">Status</span><div className="font-medium">{selected.status}</div></div>
              <div><span className="text-xs text-gray-500">Source</span><div className="font-medium">{selected.source_module}</div></div>
              <div><span className="text-xs text-gray-500">Type</span><div className="font-medium">{selected.issue_type?.replace(/_/g,' ')}</div></div>
              <div><span className="text-xs text-gray-500">Owner</span><div className="font-medium">{selected.owner_name || '—'}</div></div>
              <div><span className="text-xs text-gray-500">Due</span><div className="font-medium">{selected.due_date ? new Date(selected.due_date).toLocaleDateString() : '—'}</div></div>
            </div>
            <div className="border-t pt-4">
              <h3 className="text-xs font-semibold text-gray-700 uppercase mb-3">Change Status</h3>
              <div className="flex flex-wrap gap-2">
                {['assigned','in_remediation','pending_validation','closed','accepted'].map(s => (
                  <button
                    key={s}
                    onClick={() => { statusMutation.mutate({ issue_id: selected.issue_id, new_status: s }); setSelected(null); }}
                    className="px-3 py-1.5 text-xs font-medium border border-gray-200 rounded-lg hover:border-indigo-400 hover:text-indigo-700 transition-colors"
                  >
                    → {s.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Create New Issue</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
                <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  value={form.title} onChange={e => setForm(p => ({ ...p, title: e.target.value }))} placeholder="Describe the issue" />
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea rows={3} className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                  value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} />
              </div>
              {[
                { label: 'Issue Type', key: 'issue_type', options: issueTypes },
                { label: 'Source Module', key: 'source_module', options: sourceModules },
                { label: 'Severity', key: 'severity', options: ['critical','high','medium','low','informational'] },
              ].map(f => (
                <div key={f.key}>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{f.label}</label>
                  <select className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={(form as any)[f.key]} onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}>
                    {f.options.map(o => <option key={o} value={o}>{o.replace(/_/g,' ')}</option>)}
                  </select>
                </div>
              ))}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Owner Name</label>
                <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  value={form.owner_name} onChange={e => setForm(p => ({ ...p, owner_name: e.target.value }))} placeholder="Assigned to" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Due Date</label>
                <input type="date" className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  value={form.due_date} onChange={e => setForm(p => ({ ...p, due_date: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Financial Impact (USD)</label>
                <input type="number" className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  value={form.financial_impact} onChange={e => setForm(p => ({ ...p, financial_impact: e.target.value }))} placeholder="0" />
              </div>
              <div className="flex items-center gap-2 mt-4">
                <input type="checkbox" id="reg_impact" checked={form.regulatory_impact} onChange={e => setForm(p => ({ ...p, regulatory_impact: e.target.checked }))} className="rounded" />
                <label htmlFor="reg_impact" className="text-xs text-gray-700">Regulatory impact</label>
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-700 mb-1">Remediation Plan</label>
                <textarea rows={2} className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                  value={form.remediation_plan} onChange={e => setForm(p => ({ ...p, remediation_plan: e.target.value }))} />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
              <Button onClick={() => createMutation.mutate({
                ...form,
                financial_impact: form.financial_impact ? parseInt(form.financial_impact) : null,
                due_date: form.due_date || null,
              })} disabled={createMutation.isPending || !form.title}>
                {createMutation.isPending ? 'Creating...' : 'Create Issue'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
