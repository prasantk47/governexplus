import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon, MagnifyingGlassIcon, CheckCircleIcon,
  ExclamationTriangleIcon, GlobeAltIcon, DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { PageHeader, Card, Button, Badge } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface Framework {
  framework_id: string; name: string; short_name: string; region: string;
  status: string; is_mandatory: boolean; total_obligations: number;
  compliant_count: number; non_compliant_count: number; not_assessed_count: number;
}

interface Obligation {
  obligation_id: string; framework_id: string; reference_code: string; title: string;
  compliance_status: string; penalty_risk: string; is_key_obligation: boolean;
  owner_name: string; last_assessed_date: string | null;
}

interface Dashboard {
  overall_compliance_score: number; total_frameworks: number; total_obligations: number;
  by_status: Record<string, number>; non_compliant_count: number; not_assessed_count: number;
  critical_gaps: any[];
}

const complianceColors: Record<string, string> = {
  compliant: 'bg-green-100 text-green-700',
  partially_compliant: 'bg-yellow-100 text-yellow-700',
  non_compliant: 'bg-red-100 text-red-700',
  not_assessed: 'bg-gray-100 text-gray-600',
  exempted: 'bg-blue-100 text-blue-700',
};

const penaltyColors: Record<string, string> = {
  critical: 'text-red-600', high: 'text-orange-600', medium: 'text-yellow-600', low: 'text-green-600',
};

export function RegulatoryIntelligence() {
  const qc = useQueryClient();
  const [activeFramework, setActiveFramework] = useState<string | null>(null);
  const [showCreateFW, setShowCreateFW] = useState(false);
  const [showCreateObl, setShowCreateObl] = useState(false);
  const [search, setSearch] = useState('');

  const [fwForm, setFwForm] = useState({ name: '', short_name: '', description: '', region: 'global', is_mandatory: true, external_reference: '', owner_name: '' });
  const [oblForm, setOblForm] = useState({ reference_code: '', title: '', description: '', obligation_type: '', owner_name: '', penalty_risk: 'medium', is_key_obligation: false });

  const { data: dashboard } = useQuery<Dashboard>({
    queryKey: ['reg-dashboard'],
    queryFn: () => api.get('/regulatory/dashboard').then(r => r.data),
  });

  const { data: fwData } = useQuery({
    queryKey: ['reg-frameworks'],
    queryFn: () => api.get('/regulatory/frameworks').then(r => r.data),
  });

  const { data: oblData } = useQuery({
    queryKey: ['reg-obligations', activeFramework],
    queryFn: () => api.get('/regulatory/obligations', { params: activeFramework ? { framework_id: activeFramework } : {} }).then(r => r.data),
  });

  const frameworks: Framework[] = fwData?.frameworks || [];
  const obligations: Obligation[] = (oblData?.obligations || []).filter((o: Obligation) =>
    !search || o.title.toLowerCase().includes(search.toLowerCase()) || o.reference_code?.includes(search)
  );

  const createFWMutation = useMutation({
    mutationFn: (data: any) => api.post('/regulatory/frameworks', data),
    onSuccess: () => { toast.success('Framework created'); setShowCreateFW(false); qc.invalidateQueries({ queryKey: ['reg-frameworks'] }); qc.invalidateQueries({ queryKey: ['reg-dashboard'] }); },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  });

  const createOblMutation = useMutation({
    mutationFn: (data: any) => api.post('/regulatory/obligations', data),
    onSuccess: () => { toast.success('Obligation created'); setShowCreateObl(false); qc.invalidateQueries({ queryKey: ['reg-obligations', activeFramework] }); },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  });

  const assessMutation = useMutation({
    mutationFn: ({ obligation_id, compliance_status }: any) =>
      api.post(`/regulatory/obligations/${obligation_id}/assess`, { compliance_status }),
    onSuccess: () => { toast.success('Assessment recorded'); qc.invalidateQueries({ queryKey: ['reg-obligations'] }); qc.invalidateQueries({ queryKey: ['reg-dashboard'] }); },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed'),
  });

  const d = dashboard;
  const scoreColor = !d ? 'text-gray-400' : d.overall_compliance_score >= 80 ? 'text-green-600' : d.overall_compliance_score >= 60 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className="space-y-6">
      <PageHeader
        title="Regulatory Intelligence"
        subtitle="Framework management, obligation tracking, and compliance evidence"
        actions={
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => setShowCreateObl(true)} icon={<PlusIcon className="h-4 w-4" />}>
              Add Obligation
            </Button>
            <Button size="sm" icon={<PlusIcon className="h-4 w-4" />} onClick={() => setShowCreateFW(true)}>
              New Framework
            </Button>
          </div>
        }
      />

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <div className="text-center">
            <div className={`text-3xl font-bold ${scoreColor}`}>{d?.overall_compliance_score ?? '—'}%</div>
            <div className="text-xs text-gray-500 mt-1">Overall Compliance</div>
          </div>
        </Card>
        <StatCard title="Frameworks" value={d?.total_frameworks ?? 0} icon={GlobeAltIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Non-Compliant" value={d?.non_compliant_count ?? 0} icon={ExclamationTriangleIcon} iconBgColor={d?.non_compliant_count ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Not Assessed" value={d?.not_assessed_count ?? 0} icon={DocumentTextIcon} iconBgColor={d?.not_assessed_count ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
      </div>

      {/* Critical Gaps */}
      {d?.critical_gaps && d.critical_gaps.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <ExclamationTriangleIcon className="h-4 w-4 text-red-500" />
            Critical Compliance Gaps
          </h2>
          <div className="space-y-2">
            {d.critical_gaps.map((gap: any) => (
              <div key={gap.obligation_id} className="flex items-start gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex-1">
                  <div className="text-xs font-mono text-red-700">{gap.obligation_id}</div>
                  <div className="text-sm font-medium text-gray-900">{gap.title}</div>
                  {gap.gaps_identified && <div className="text-xs text-red-600 mt-0.5">{gap.gaps_identified}</div>}
                </div>
                <span className={`text-xs font-semibold ${penaltyColors[gap.penalty_risk] || 'text-gray-600'}`}>{gap.penalty_risk} penalty</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Frameworks Panel */}
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Frameworks</h2>
          <div className="space-y-2">
            {frameworks.map(f => {
              const pct = f.total_obligations > 0 ? Math.round(f.compliant_count / f.total_obligations * 100) : 0;
              return (
                <button
                  key={f.framework_id}
                  onClick={() => setActiveFramework(activeFramework === f.framework_id ? null : f.framework_id)}
                  className={`w-full text-left p-3 rounded-xl border transition-colors ${activeFramework === f.framework_id ? 'border-indigo-400 bg-indigo-50' : 'border-gray-200 hover:border-indigo-300 hover:bg-gray-50'}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-semibold text-gray-900">{f.short_name || f.name}</span>
                    <span className={`text-xs font-bold ${pct >= 80 ? 'text-green-600' : pct >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>{pct}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-1.5 mb-1">
                    <div className={`h-1.5 rounded-full ${pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-yellow-500' : 'bg-red-500'}`} style={{ width: `${pct}%` }} />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>{f.total_obligations} obligations</span>
                    <span>{f.non_compliant_count} gaps</span>
                  </div>
                </button>
              );
            })}
            {frameworks.length === 0 && <p className="text-xs text-gray-400 text-center py-4">No frameworks yet</p>}
          </div>
        </Card>

        {/* Obligations Table */}
        <div className="lg:col-span-2">
          <Card padding="none">
            <div className="px-4 py-3 border-b border-white/20 flex items-center gap-3">
              <h2 className="text-sm font-semibold text-gray-900 flex-1">
                {activeFramework ? `Obligations — ${frameworks.find(f => f.framework_id === activeFramework)?.short_name || activeFramework}` : 'All Obligations'}
              </h2>
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
                <input className="pl-7 pr-3 py-1.5 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Search..." value={search} onChange={e => setSearch(e.target.value)} />
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/20">
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">Ref / Title</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">Compliance</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">Penalty Risk</th>
                    <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">Assess</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {obligations.length === 0 ? (
                    <tr><td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-400">
                      {activeFramework ? 'No obligations for this framework' : 'Select a framework or create obligations'}
                    </td></tr>
                  ) : obligations.map(o => (
                    <tr key={o.obligation_id} className="hover:bg-white/20">
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-1">
                          {o.is_key_obligation && <span className="text-xs text-purple-600 font-semibold">★</span>}
                          <div>
                            {o.reference_code && <div className="text-xs font-mono text-indigo-600">{o.reference_code}</div>}
                            <div className="text-sm text-gray-900 max-w-xs truncate">{o.title}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-2">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${complianceColors[o.compliance_status] || 'bg-gray-100 text-gray-600'}`}>
                          {o.compliance_status?.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-4 py-2">
                        <span className={`text-xs font-semibold ${penaltyColors[o.penalty_risk] || 'text-gray-500'}`}>{o.penalty_risk}</span>
                      </td>
                      <td className="px-4 py-2 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {['compliant','partially_compliant','non_compliant'].map(status => (
                            <button key={status}
                              onClick={() => assessMutation.mutate({ obligation_id: o.obligation_id, compliance_status: status })}
                              className={`text-xs px-1.5 py-0.5 rounded border transition-colors ${o.compliance_status === status ? 'border-indigo-400 bg-indigo-50 text-indigo-700' : 'border-gray-200 text-gray-500 hover:border-indigo-300'}`}
                              title={status.replace(/_/g, ' ')}
                            >
                              {status === 'compliant' ? '✓' : status === 'non_compliant' ? '✗' : '~'}
                            </button>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>

      {/* Create Framework Modal */}
      {showCreateFW && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Add Regulatory Framework</h2>
            <div className="space-y-3">
              {[{ label: 'Full Name *', key: 'name', placeholder: 'Sarbanes-Oxley Act' }, { label: 'Short Name', key: 'short_name', placeholder: 'SOX' }, { label: 'Owner Name', key: 'owner_name', placeholder: 'John Smith' }, { label: 'External Reference URL', key: 'external_reference', placeholder: 'https://...' }].map(f => (
                <div key={f.key}>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{f.label}</label>
                  <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder={f.placeholder} value={(fwForm as any)[f.key]} onChange={e => setFwForm(p => ({ ...p, [f.key]: e.target.value }))} />
                </div>
              ))}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Region</label>
                <select className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  value={fwForm.region} onChange={e => setFwForm(p => ({ ...p, region: e.target.value }))}>
                  {['global','us','eu','apac','emea','uk','india','singapore','other'].map(r => <option key={r} value={r}>{r.toUpperCase()}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea rows={2} className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                  value={fwForm.description} onChange={e => setFwForm(p => ({ ...p, description: e.target.value }))} />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <Button variant="secondary" onClick={() => setShowCreateFW(false)}>Cancel</Button>
              <Button onClick={() => createFWMutation.mutate(fwForm)} disabled={createFWMutation.isPending || !fwForm.name}>
                {createFWMutation.isPending ? 'Creating...' : 'Create Framework'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Create Obligation Modal */}
      {showCreateObl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Add Obligation</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Framework *</label>
                <select className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  value={activeFramework || ''} onChange={e => setActiveFramework(e.target.value)}>
                  <option value="">Select framework...</option>
                  {frameworks.map(f => <option key={f.framework_id} value={f.framework_id}>{f.short_name || f.name}</option>)}
                </select>
              </div>
              {[{ label: 'Reference Code', key: 'reference_code', placeholder: 'SOX 302(a)' }, { label: 'Title *', key: 'title', placeholder: 'Management assessment of internal controls' }, { label: 'Owner Name', key: 'owner_name', placeholder: 'CFO' }].map(f => (
                <div key={f.key}>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{f.label}</label>
                  <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder={f.placeholder} value={(oblForm as any)[f.key]} onChange={e => setOblForm(p => ({ ...p, [f.key]: e.target.value }))} />
                </div>
              ))}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Penalty Risk</label>
                <select className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  value={oblForm.penalty_risk} onChange={e => setOblForm(p => ({ ...p, penalty_risk: e.target.value }))}>
                  {['critical','high','medium','low'].map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea rows={2} className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                  value={oblForm.description} onChange={e => setOblForm(p => ({ ...p, description: e.target.value }))} />
              </div>
              <label className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer">
                <input type="checkbox" checked={oblForm.is_key_obligation} onChange={e => setOblForm(p => ({ ...p, is_key_obligation: e.target.checked }))} className="rounded" />
                Key obligation (high-penalty / regulator-focus)
              </label>
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <Button variant="secondary" onClick={() => setShowCreateObl(false)}>Cancel</Button>
              <Button onClick={() => createOblMutation.mutate({ ...oblForm, framework_id: activeFramework })}
                disabled={createOblMutation.isPending || !oblForm.title || !activeFramework}>
                {createOblMutation.isPending ? 'Creating...' : 'Create Obligation'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
