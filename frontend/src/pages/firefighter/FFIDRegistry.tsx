import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  PencilIcon,
  ArchiveBoxIcon,
  MagnifyingGlassIcon,
  ShieldCheckIcon,
  UserIcon,
  GlobeAltIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { PageHeader, Card, Button, Badge } from '../../components/ui';
import { firefighterApi } from '../../services/api';

interface FFID {
  ffid: string;
  description: string;
  target_system: string;
  emergency_function: string;
  status: string;
  owner_id: string;
  owner_name: string;
  controller_id: string;
  controller_name: string;
  region: string;
  country: string;
  company_codes: string[];
  risk_level: string;
  max_session_hours: number;
  sox_relevant: boolean;
  in_use: boolean;
  certification_status: string;
  next_certification_due: string | null;
  created_at: string;
}

const riskColors: Record<string, string> = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

const certColors: Record<string, string> = {
  current: 'bg-green-100 text-green-700',
  due: 'bg-yellow-100 text-yellow-700',
  overdue: 'bg-red-100 text-red-700',
  never: 'bg-gray-100 text-gray-700',
};

export function FFIDRegistry() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [regionFilter, setRegionFilter] = useState('all');
  const [fnFilter, setFnFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('active');
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);

  const [form, setForm] = useState({
    ffid: '', description: '', target_system: 'SAP_PRD', emergency_function: 'FI',
    region: 'APAC', country: '', company_codes: '', owner_id: '', owner_name: '',
    controller_id: '', controller_name: '', risk_level: 'high', max_session_hours: '4',
  });

  const { data: raw } = useQuery({
    queryKey: ['ffid-registry', regionFilter, fnFilter, statusFilter],
    queryFn: () => firefighterApi.listFirefighters().then(r => r.data),
  });

  const allFFIDs: FFID[] = Array.isArray(raw) ? raw : (raw as any)?.firefighter_ids || [];

  const filtered = allFFIDs.filter(f => {
    const matchSearch = !search || f.ffid.toLowerCase().includes(search.toLowerCase()) || f.description.toLowerCase().includes(search.toLowerCase());
    const matchRegion = regionFilter === 'all' || f.region === regionFilter;
    const matchFn = fnFilter === 'all' || f.emergency_function === fnFilter;
    const matchStatus = statusFilter === 'all' || f.status === statusFilter;
    return matchSearch && matchRegion && matchFn && matchStatus;
  });

  const retireMutation = useMutation({
    mutationFn: (ffid: string) => firefighterApi.retireFirefighter(ffid, localStorage.getItem('userId') || 'admin'),
    onSuccess: () => {
      toast.success('FFID retired');
      queryClient.invalidateQueries({ queryKey: ['ffid-registry'] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed to retire FFID'),
  });

  const handleCreate = async () => {
    if (!form.ffid || !form.description) {
      toast.error('FFID ID and description are required');
      return;
    }
    setCreating(true);
    try {
      await firefighterApi.createFirefighter({
        ffid: form.ffid,
        description: form.description,
        target_system: form.target_system,
        emergency_function: form.emergency_function,
        region: form.region,
        country: form.country,
        company_codes: form.company_codes,
        owner_id: form.owner_id,
        owner_name: form.owner_name,
        controller_id: form.controller_id,
        controller_name: form.controller_name,
        risk_level: form.risk_level,
        max_session_hours: parseInt(form.max_session_hours, 10) || 4,
        created_by: localStorage.getItem('userId') || 'admin',
      });
      toast.success(`FFID ${form.ffid} created`);
      setShowCreate(false);
      setForm({ ffid: '', description: '', target_system: 'SAP_PRD', emergency_function: 'FI', region: 'APAC', country: '', company_codes: '', owner_id: '', owner_name: '', controller_id: '', controller_name: '', risk_level: 'high', max_session_hours: '4' });
      queryClient.invalidateQueries({ queryKey: ['ffid-registry'] });
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Failed to create FFID');
    } finally {
      setCreating(false);
    }
  };

  const regions = ['APAC', 'EMEA', 'AMER', 'MEA', 'GLOBAL'];
  const functions = ['FI', 'MM', 'SD', 'HR', 'BASIS', 'SEC', 'ABAP', 'TR', 'QM', 'PP'];

  return (
    <div className="space-y-6">
      <PageHeader
        title="FFID Registry"
        subtitle="Manage and govern all Firefighter IDs, ownership, and org scope"
        actions={
          <Button size="sm" icon={<PlusIcon className="h-4 w-4" />} onClick={() => setShowCreate(true)}>
            Register FFID
          </Button>
        }
      />

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-48">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg bg-white/50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Search FFID or description..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <select className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white/50 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={regionFilter} onChange={e => setRegionFilter(e.target.value)}>
            <option value="all">All Regions</option>
            {regions.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <select className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white/50 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={fnFilter} onChange={e => setFnFilter(e.target.value)}>
            <option value="all">All Functions</option>
            {functions.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
          <select className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white/50 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="locked">Locked</option>
            <option value="retired">Retired</option>
            <option value="under_review">Under Review</option>
          </select>
        </div>
      </Card>

      {/* FFID Table */}
      <Card padding="none">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/20 bg-gray-50/50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">FFID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Function / System</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Owner / Controller</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Org Scope</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Risk</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Certification</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-sm text-gray-400">No FFIDs found</td>
                </tr>
              ) : filtered.map(f => (
                <tr key={f.ffid} className="hover:bg-white/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {f.in_use && <span className="inline-block h-2 w-2 rounded-full bg-green-500 animate-pulse" title="In use" />}
                      <div>
                        <div className="font-mono font-semibold text-indigo-700 text-xs">{f.ffid}</div>
                        <div className="text-xs text-gray-500 max-w-48 truncate">{f.description}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-xs font-medium text-gray-900">{f.emergency_function}</div>
                    <div className="text-xs text-gray-500">{f.target_system}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <UserIcon className="h-3 w-3 text-gray-400" />
                      <span className="text-xs text-gray-900">{f.owner_name || f.owner_id || <span className="text-red-500">No owner</span>}</span>
                    </div>
                    <div className="flex items-center gap-1 mt-0.5">
                      <ShieldCheckIcon className="h-3 w-3 text-gray-400" />
                      <span className="text-xs text-gray-500">{f.controller_name || f.controller_id || <span className="text-orange-500">No controller</span>}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 text-xs text-gray-900">
                      <GlobeAltIcon className="h-3 w-3 text-gray-400" />
                      {f.region || '—'}
                    </div>
                    {f.company_codes?.length > 0 && (
                      <div className="text-xs text-gray-500 mt-0.5">{f.company_codes.join(', ')}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${riskColors[f.risk_level] || 'bg-gray-100 text-gray-700'}`}>
                      {f.risk_level}
                    </span>
                    {f.sox_relevant && (
                      <div className="text-xs text-gray-400 mt-0.5">SOX</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${certColors[f.certification_status] || 'bg-gray-100 text-gray-700'}`}>
                      {f.certification_status || 'unknown'}
                    </span>
                    {f.next_certification_due && (
                      <div className="text-xs text-gray-400 mt-0.5">Due {f.next_certification_due}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {f.status === 'active' ? (
                      <Badge variant="success" size="sm">
                        <CheckCircleIcon className="h-3 w-3 mr-0.5" />Active
                      </Badge>
                    ) : f.status === 'retired' ? (
                      <Badge variant="danger" size="sm">Retired</Badge>
                    ) : (
                      <Badge variant="warning" size="sm">{f.status}</Badge>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        className="p-1 rounded hover:bg-indigo-50 text-indigo-600 transition-colors"
                        title="Edit"
                        onClick={() => toast('Edit via API: PUT /privileged-access/firefighters/' + f.ffid)}
                      >
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      {f.status === 'active' && !f.in_use && (
                        <button
                          className="p-1 rounded hover:bg-red-50 text-red-600 transition-colors"
                          title="Retire"
                          onClick={() => {
                            if (confirm(`Retire FFID ${f.ffid}? This will prevent new sessions.`)) {
                              retireMutation.mutate(f.ffid);
                            }
                          }}
                        >
                          <ArchiveBoxIcon className="h-4 w-4" />
                        </button>
                      )}
                      {f.in_use && (
                        <span className="text-xs text-green-600 font-medium">In Use</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Register New Firefighter ID</h2>
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: 'FFID *', key: 'ffid', placeholder: 'FF_FI_002' },
                { label: 'Description *', key: 'description', placeholder: 'Finance Emergency - APAC' },
              ].map(f => (
                <div key={f.key} className={f.key === 'description' ? 'col-span-2' : ''}>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{f.label}</label>
                  <input
                    className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder={f.placeholder}
                    value={(form as any)[f.key]}
                    onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                  />
                </div>
              ))}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Emergency Function</label>
                <select className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={form.emergency_function} onChange={e => setForm(prev => ({ ...prev, emergency_function: e.target.value }))}>
                  {functions.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Target System</label>
                <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="SAP_PRD" value={form.target_system} onChange={e => setForm(prev => ({ ...prev, target_system: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Region</label>
                <select className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={form.region} onChange={e => setForm(prev => ({ ...prev, region: e.target.value }))}>
                  {regions.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Country (ISO)</label>
                <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="SG" value={form.country} onChange={e => setForm(prev => ({ ...prev, country: e.target.value }))} />
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-700 mb-1">Company Codes (comma-separated)</label>
                <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="1000,1100,1200" value={form.company_codes} onChange={e => setForm(prev => ({ ...prev, company_codes: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Owner ID</label>
                <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="JSMITH" value={form.owner_id} onChange={e => setForm(prev => ({ ...prev, owner_id: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Owner Name</label>
                <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="John Smith" value={form.owner_name} onChange={e => setForm(prev => ({ ...prev, owner_name: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Controller ID</label>
                <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="ACONTROLLER" value={form.controller_id} onChange={e => setForm(prev => ({ ...prev, controller_id: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Controller Name</label>
                <input className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="Alice Controller" value={form.controller_name} onChange={e => setForm(prev => ({ ...prev, controller_name: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Risk Level</label>
                <select className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={form.risk_level} onChange={e => setForm(prev => ({ ...prev, risk_level: e.target.value }))}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Max Session Hours</label>
                <input type="number" min={1} max={24} className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={form.max_session_hours} onChange={e => setForm(prev => ({ ...prev, max_session_hours: e.target.value }))} />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={creating}>{creating ? 'Creating...' : 'Register FFID'}</Button>
            </div>
          </div>
        </div>
      )}

      {/* Warning for FFIDs without controller */}
      {filtered.some(f => f.status === 'active' && !f.controller_id) && (
        <Card>
          <div className="flex items-center gap-3 text-orange-700 bg-orange-50 rounded-xl p-4">
            <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" />
            <div className="text-sm">
              <span className="font-semibold">{filtered.filter(f => f.status === 'active' && !f.controller_id).length} active FFID(s)</span> have no controller assigned.
              Controller assignment is required by EAM governance policy — please assign a controller for each active FFID.
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
