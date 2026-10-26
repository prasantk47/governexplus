/**
 * GovernexPlus Identity Graph Visualization
 * Cross-system identity correlation with visual graph
 */
import { useState } from 'react';
import {
  MagnifyingGlassIcon,
  UserCircleIcon,
  ServerStackIcon,
  ExclamationTriangleIcon,
  GlobeAltIcon,
} from '@heroicons/react/24/outline';

interface SystemAccount {
  system: string; systemType: string; username: string; roles: number;
  lastLogin: string; status: 'active' | 'locked' | 'dormant'; riskLevel: 'low' | 'medium' | 'high' | 'critical';
}
interface IdentityProfile {
  userId: string; fullName: string; email: string; department: string; manager: string;
  accounts: SystemAccount[]; totalRoles: number; riskScore: number;
}
interface OrphanAccount { system: string; username: string; lastLogin: string; roles: number; }

const USERS: Record<string, IdentityProfile> = {
  'JMILLER': {
    userId: 'JMILLER', fullName: 'John Miller', email: 'john.miller@company.com', department: 'Finance', manager: 'Robert Johnson',
    accounts: [
      { system: 'SAP ECC', systemType: 'ERP', username: 'JMILLER', roles: 7, lastLogin: '2026-10-25', status: 'active', riskLevel: 'high' },
      { system: 'SAP S/4HANA', systemType: 'ERP', username: 'JOHN.MILLER', roles: 4, lastLogin: '2026-10-24', status: 'active', riskLevel: 'medium' },
      { system: 'Azure AD', systemType: 'IDM', username: 'john.miller@company.com', roles: 3, lastLogin: '2026-10-25', status: 'active', riskLevel: 'low' },
      { system: 'ServiceNow', systemType: 'ITSM', username: 'john.miller', roles: 2, lastLogin: '2026-10-20', status: 'active', riskLevel: 'low' },
      { system: 'Workday', systemType: 'HCM', username: 'JMiller', roles: 1, lastLogin: '2026-09-15', status: 'dormant', riskLevel: 'low' },
    ],
    totalRoles: 17, riskScore: 72,
  },
  'SCHEN': {
    userId: 'SCHEN', fullName: 'Sarah Chen', email: 'sarah.chen@company.com', department: 'Procurement', manager: 'David Kim',
    accounts: [
      { system: 'SAP ECC', systemType: 'ERP', username: 'SCHEN', roles: 5, lastLogin: '2026-10-25', status: 'active', riskLevel: 'medium' },
      { system: 'Azure AD', systemType: 'IDM', username: 'sarah.chen@company.com', roles: 2, lastLogin: '2026-10-25', status: 'active', riskLevel: 'low' },
      { system: 'Ariba', systemType: 'Procurement', username: 'sarah.chen', roles: 3, lastLogin: '2026-10-24', status: 'active', riskLevel: 'low' },
    ],
    totalRoles: 10, riskScore: 45,
  },
};

const ORPHANS: OrphanAccount[] = [
  { system: 'SAP ECC', username: 'TEMP_AUDIT_2025', lastLogin: '2025-12-15', roles: 4 },
  { system: 'SAP ECC', username: 'SVC_LEGACY_RPT', lastLogin: '2025-06-01', roles: 2 },
  { system: 'Azure AD', username: 'contractor.old@company.com', lastLogin: '2026-03-10', roles: 5 },
  { system: 'ServiceNow', username: 'integration_user_v1', lastLogin: '2025-09-20', roles: 3 },
];

const systemColors: Record<string, { bg: string; border: string; text: string }> = {
  'SAP ECC': { bg: 'bg-blue-100 dark:bg-blue-900/30', border: 'border-blue-300 dark:border-blue-700', text: 'text-blue-700 dark:text-blue-400' },
  'SAP S/4HANA': { bg: 'bg-indigo-100 dark:bg-indigo-900/30', border: 'border-indigo-300 dark:border-indigo-700', text: 'text-indigo-700 dark:text-indigo-400' },
  'Azure AD': { bg: 'bg-sky-100 dark:bg-sky-900/30', border: 'border-sky-300 dark:border-sky-700', text: 'text-sky-700 dark:text-sky-400' },
  'ServiceNow': { bg: 'bg-emerald-100 dark:bg-emerald-900/30', border: 'border-emerald-300 dark:border-emerald-700', text: 'text-emerald-700 dark:text-emerald-400' },
  'Workday': { bg: 'bg-orange-100 dark:bg-orange-900/30', border: 'border-orange-300 dark:border-orange-700', text: 'text-orange-700 dark:text-orange-400' },
  'Ariba': { bg: 'bg-purple-100 dark:bg-purple-900/30', border: 'border-purple-300 dark:border-purple-700', text: 'text-purple-700 dark:text-purple-400' },
};
const defaultSysColor = { bg: 'bg-gray-100 dark:bg-gray-900/30', border: 'border-gray-300 dark:border-gray-700', text: 'text-gray-700 dark:text-gray-400' };

const statusBadge: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  locked: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  dormant: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
};
const riskBadge: Record<string, string> = {
  low: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

type Tab = 'profile' | 'department' | 'orphans';

export function IdentityGraph() {
  const [search, setSearch] = useState('');
  const [activeUser, setActiveUser] = useState<IdentityProfile | null>(null);
  const [tab, setTab] = useState<Tab>('profile');

  const doSearch = () => {
    const key = search.toUpperCase().trim();
    const found = USERS[key] || Object.values(USERS).find(u => u.fullName.toLowerCase().includes(search.toLowerCase()));
    setActiveUser(found || null);
    if (found) setTab('profile');
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Identity Graph</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Visualize every identity across all connected systems &mdash; one person, all accounts, all risks</p>
      </div>

      {/* Search */}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <MagnifyingGlassIcon className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => e.key === 'Enter' && doSearch()}
            placeholder="Search by user ID or name (try JMILLER or SCHEN)..."
            className="w-full pl-10 pr-4 py-2.5 border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-white placeholder:text-gray-400 focus:ring-2 focus:ring-indigo-500 focus:outline-none" />
        </div>
        <button onClick={doSearch} className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg">Search</button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-slate-700">
        <nav className="flex gap-6">
          {([['profile', 'Identity Profile'], ['department', 'Department View'], ['orphans', 'Orphan Accounts']] as [Tab, string][]).map(([key, label]) => (
            <button key={key} onClick={() => setTab(key)}
              className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${tab === key ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 dark:border-indigo-400' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'}`}>
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Profile Tab */}
      {tab === 'profile' && activeUser && (
        <div className="space-y-6">
          {/* User Card + Visual Graph */}
          <div className="grid lg:grid-cols-3 gap-6">
            {/* User Info */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
              <div className="flex items-center gap-4 mb-5">
                <div className="w-14 h-14 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                  <UserCircleIcon className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white">{activeUser.fullName}</h3>
                  <p className="text-sm text-gray-500">{activeUser.department}</p>
                </div>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">User ID</span><span className="font-mono text-gray-900 dark:text-white">{activeUser.userId}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Email</span><span className="text-gray-900 dark:text-white">{activeUser.email}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Manager</span><span className="text-gray-900 dark:text-white">{activeUser.manager}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Connected Systems</span><span className="font-semibold text-gray-900 dark:text-white">{activeUser.accounts.length}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Total Roles</span><span className="font-semibold text-gray-900 dark:text-white">{activeUser.totalRoles}</span></div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Risk Score</span>
                  <span className={`font-bold ${activeUser.riskScore >= 70 ? 'text-red-600' : activeUser.riskScore >= 40 ? 'text-amber-600' : 'text-emerald-600'}`}>{activeUser.riskScore}/100</span>
                </div>
              </div>
            </div>

            {/* Visual Graph */}
            <div className="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Identity Correlation Graph</h3>
              <div className="relative min-h-[280px] flex items-center justify-center">
                {/* Center node */}
                <div className="absolute z-10 w-20 h-20 rounded-full bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                  <div className="text-center">
                    <UserCircleIcon className="h-6 w-6 text-white mx-auto" />
                    <span className="text-[10px] text-white font-medium">{activeUser.userId}</span>
                  </div>
                </div>
                {/* System nodes in circle */}
                {activeUser.accounts.map((acc, i) => {
                  const angle = (i * 360 / activeUser.accounts.length - 90) * Math.PI / 180;
                  const radius = 120;
                  const x = Math.cos(angle) * radius;
                  const y = Math.sin(angle) * radius;
                  const sc = systemColors[acc.system] || defaultSysColor;
                  return (
                    <div key={acc.system} className="absolute" style={{ transform: `translate(${x}px, ${y}px)` }}>
                      {/* Connection line (CSS) */}
                      <div className="absolute left-1/2 top-1/2 w-px bg-gray-300 dark:bg-slate-600 origin-center"
                        style={{ height: `${radius - 30}px`, transform: `rotate(${Math.atan2(-y, -x) * 180 / Math.PI + 90}deg) translateX(-50%)`, transformOrigin: 'top center' }} />
                      {/* Node */}
                      <div className={`relative z-10 px-3 py-2 rounded-lg border ${sc.border} ${sc.bg} text-center min-w-[90px]`}>
                        <ServerStackIcon className={`h-4 w-4 mx-auto ${sc.text}`} />
                        <p className={`text-xs font-semibold mt-1 ${sc.text}`}>{acc.system}</p>
                        <p className="text-[10px] text-gray-500 dark:text-gray-400">{acc.username}</p>
                        <p className="text-[10px] text-gray-400">{acc.roles} roles</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Account Details */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
            <div className="p-5 border-b border-gray-200 dark:border-slate-700">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Account Details</h3>
            </div>
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-slate-700/50">
                <tr>{['System', 'Username', 'Type', 'Roles', 'Last Login', 'Status', 'Risk'].map(h => <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                {activeUser.accounts.map(acc => (
                  <tr key={acc.system}>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{acc.system}</td>
                    <td className="px-4 py-3 text-sm font-mono text-gray-600 dark:text-gray-400">{acc.username}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{acc.systemType}</td>
                    <td className="px-4 py-3 text-sm font-semibold text-gray-900 dark:text-white">{acc.roles}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{acc.lastLogin}</td>
                    <td className="px-4 py-3"><span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${statusBadge[acc.status]}`}>{acc.status}</span></td>
                    <td className="px-4 py-3"><span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${riskBadge[acc.riskLevel]}`}>{acc.riskLevel}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'profile' && !activeUser && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-12 text-center">
          <GlobeAltIcon className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-gray-400">Search for a user to view their identity graph</p>
          <p className="text-xs text-gray-400 mt-1">Try: JMILLER, SCHEN, John Miller</p>
        </div>
      )}

      {/* Department Tab */}
      {tab === 'department' && (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.values(USERS).map(u => (
            <div key={u.userId} onClick={() => { setActiveUser(u); setTab('profile'); }}
              className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 cursor-pointer hover:border-indigo-300 dark:hover:border-indigo-600 transition-colors">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                  <UserCircleIcon className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">{u.fullName}</p>
                  <p className="text-xs text-gray-500">{u.department}</p>
                </div>
              </div>
              <div className="flex justify-between text-xs text-gray-500">
                <span>{u.accounts.length} systems</span>
                <span>{u.totalRoles} roles</span>
                <span className={u.riskScore >= 70 ? 'text-red-600 font-semibold' : u.riskScore >= 40 ? 'text-amber-600 font-semibold' : 'text-emerald-600'}>Risk: {u.riskScore}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Orphans Tab */}
      {tab === 'orphans' && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
          <div className="p-5 border-b border-gray-200 dark:border-slate-700">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <ExclamationTriangleIcon className="h-4 w-4 text-amber-500" /> Orphan Accounts
            </h3>
            <p className="text-xs text-gray-500 mt-1">Accounts without linked identities &mdash; potential security risk</p>
          </div>
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-slate-700/50">
              <tr>{['System', 'Username', 'Last Login', 'Roles', 'Action'].map(h => <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
              {ORPHANS.map(o => (
                <tr key={`${o.system}-${o.username}`}>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{o.system}</td>
                  <td className="px-4 py-3 text-sm font-mono text-gray-600 dark:text-gray-400">{o.username}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{o.lastLogin}</td>
                  <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">{o.roles}</td>
                  <td className="px-4 py-3">
                    <button className="text-xs text-red-600 dark:text-red-400 font-medium hover:underline">Investigate</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
