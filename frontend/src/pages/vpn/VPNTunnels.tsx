/**
 * VPN Tunnel Management
 * Manage Cisco AnyConnect VPN tunnels for SAP system connectivity.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';

const API = '/api/vpn';

function api(path: string, opts?: RequestInit) {
  const token = localStorage.getItem('token');
  return fetch(`${API}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...opts?.headers },
  }).then(async r => {
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || r.statusText);
    return data;
  });
}

interface Tunnel {
  id: string;
  name: string;
  provider: string;
  gateway: string;
  group: string;
  username: string;
  auth_type: string;
  status: string;
  enabled: boolean;
  local_ip?: string;
  remote_ip?: string;
  connected_at?: string;
  uptime_seconds?: number;
  last_error?: string;
  linked_connector_ids: string[];
  split_tunnel: boolean;
  routes: string[];
  mtu: number;
  idle_timeout: number;
  reconnect_attempts: number;
}

const STATUS_COLORS: Record<string, string> = {
  connected: 'bg-green-500',
  connecting: 'bg-yellow-500 animate-pulse',
  reconnecting: 'bg-yellow-500 animate-pulse',
  disconnected: 'bg-gray-400',
  error: 'bg-red-500',
  disconnecting: 'bg-orange-400',
};

export function VPNTunnels() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: '', provider: 'cisco_anyconnect', gateway: '', group: '',
    username: '', password: '', auth_type: 'password', split_tunnel: true,
    routes: '', mtu: 1406, idle_timeout: 3600, reconnect_attempts: 3,
    linked_connector_ids: '',
  });

  const { data: tunnels = [], isLoading } = useQuery<Tunnel[]>({
    queryKey: ['vpn-tunnels'],
    queryFn: () => api('/'),
    refetchInterval: 10000,
  });

  const { data: acStatus } = useQuery({
    queryKey: ['vpn-anyconnect-status'],
    queryFn: () => api('/status/anyconnect'),
  });

  const createMut = useMutation({
    mutationFn: (body: any) => api('/', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['vpn-tunnels'] }); setShowCreate(false); toast.success('Tunnel created'); },
    onError: (e: any) => toast.error(e.message),
  });

  const connectMut = useMutation({
    mutationFn: (id: string) => api(`/${id}/connect`, { method: 'POST' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['vpn-tunnels'] }); toast.success('VPN connected'); },
    onError: (e: any) => toast.error(`Connect failed: ${e.message}`),
  });

  const disconnectMut = useMutation({
    mutationFn: (id: string) => api(`/${id}/disconnect`, { method: 'POST' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['vpn-tunnels'] }); toast.success('VPN disconnected'); },
    onError: (e: any) => toast.error(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api(`/${id}`, { method: 'DELETE' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['vpn-tunnels'] }); toast.success('Tunnel deleted'); },
    onError: (e: any) => toast.error(e.message),
  });

  const testMut = useMutation({
    mutationFn: (id: string) => api(`/${id}/test`, { method: 'POST' }),
    onSuccess: (d: any) => toast.success(d.reachable ? 'Gateway reachable' : 'Gateway unreachable'),
    onError: (e: any) => toast.error(e.message),
  });

  const handleCreate = () => {
    createMut.mutate({
      ...form,
      routes: form.routes ? form.routes.split(',').map(s => s.trim()) : [],
      linked_connector_ids: form.linked_connector_ids ? form.linked_connector_ids.split(',').map(s => s.trim()) : [],
    });
  };

  const formatUptime = (s: number) => {
    if (!s) return '-';
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">VPN Tunnels</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manage Cisco AnyConnect tunnels for SAP system connectivity
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium"
        >
          {showCreate ? 'Cancel' : 'New Tunnel'}
        </button>
      </div>

      {/* AnyConnect Status Banner */}
      {acStatus && (
        <div className={`rounded-lg p-3 text-sm ${acStatus.anyconnect_installed ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300' : 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300'}`}>
          Cisco AnyConnect CLI: {acStatus.anyconnect_installed ? 'Installed' : 'Not Found'}
          {acStatus.connected && ' — Active connection detected'}
        </div>
      )}

      {/* Create Form */}
      {showCreate && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">New VPN Tunnel</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Tunnel Name</label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-gray-900 dark:text-white" placeholder="SAP Prod VPN" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">VPN Gateway</label>
              <input value={form.gateway} onChange={e => setForm(f => ({ ...f, gateway: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-gray-900 dark:text-white" placeholder="vpn.customer.com" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">VPN Group / Profile</label>
              <input value={form.group} onChange={e => setForm(f => ({ ...f, group: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-gray-900 dark:text-white" placeholder="SAP-Access" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Provider</label>
              <select value={form.provider} onChange={e => setForm(f => ({ ...f, provider: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-gray-900 dark:text-white">
                <option value="cisco_anyconnect">Cisco AnyConnect</option>
                <option value="openconnect">OpenConnect</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Username</label>
              <input value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-gray-900 dark:text-white" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
              <input type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-gray-900 dark:text-white" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Split Tunnel Routes (comma-separated IPs)</label>
              <input value={form.routes} onChange={e => setForm(f => ({ ...f, routes: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-gray-900 dark:text-white" placeholder="10.0.1.0, 10.0.2.0" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Linked SAP Connector IDs (comma-separated)</label>
              <input value={form.linked_connector_ids} onChange={e => setForm(f => ({ ...f, linked_connector_ids: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-gray-900 dark:text-white" placeholder="sap-prod-001, sap-dev-001" />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => setShowCreate(false)}
              className="px-4 py-2 border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm">Cancel</button>
            <button onClick={handleCreate} disabled={!form.name || !form.gateway}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium disabled:opacity-50">
              Create Tunnel
            </button>
          </div>
        </div>
      )}

      {/* Tunnel Cards */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading tunnels...</div>
      ) : tunnels.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No VPN tunnels configured. Click "New Tunnel" to add one for your SAP system.
        </div>
      ) : (
        <div className="grid gap-4">
          {tunnels.map(t => (
            <div key={t.id} className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${STATUS_COLORS[t.status] || 'bg-gray-400'}`} />
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{t.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {t.gateway} {t.group && `(${t.group})`} — {t.provider.replace('_', ' ')}
                    </p>
                  </div>
                </div>
                <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                  t.status === 'connected' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                  t.status === 'error' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                  'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-400'
                }`}>
                  {t.status}
                </span>
              </div>

              {/* Connection Details */}
              {t.status === 'connected' && (
                <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Local IP:</span>
                    <span className="ml-2 text-gray-900 dark:text-white font-mono">{t.local_ip || '-'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Remote:</span>
                    <span className="ml-2 text-gray-900 dark:text-white font-mono">{t.remote_ip || t.gateway}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Uptime:</span>
                    <span className="ml-2 text-gray-900 dark:text-white">{formatUptime(t.uptime_seconds || 0)}</span>
                  </div>
                </div>
              )}

              {t.last_error && t.status === 'error' && (
                <div className="mt-3 p-2 rounded bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-xs font-mono">
                  {t.last_error}
                </div>
              )}

              {t.linked_connector_ids.length > 0 && (
                <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  Linked connectors: {t.linked_connector_ids.join(', ')}
                </div>
              )}

              {/* Actions */}
              <div className="mt-4 flex gap-2">
                {t.status !== 'connected' ? (
                  <button onClick={() => connectMut.mutate(t.id)} disabled={connectMut.isPending}
                    className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50">
                    {connectMut.isPending ? 'Connecting...' : 'Connect'}
                  </button>
                ) : (
                  <button onClick={() => disconnectMut.mutate(t.id)} disabled={disconnectMut.isPending}
                    className="px-3 py-1.5 bg-orange-600 text-white rounded-lg text-sm hover:bg-orange-700 disabled:opacity-50">
                    Disconnect
                  </button>
                )}
                <button onClick={() => testMut.mutate(t.id)} disabled={testMut.isPending}
                  className="px-3 py-1.5 border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-slate-700">
                  Test
                </button>
                <button onClick={() => { if (confirm('Delete this tunnel?')) deleteMut.mutate(t.id); }}
                  className="px-3 py-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg text-sm ml-auto">
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
