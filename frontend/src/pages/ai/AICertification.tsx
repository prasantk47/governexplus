/**
 * GovernexPlus AI Certification Recommendations
 * AI pre-fills certification decisions using usage data
 */
import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  DocumentCheckIcon,
  SparklesIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

interface CertItem {
  id: string; user: string; department: string; role: string; roleId: string;
  lastUsed: string; usagePercent: number; recommendation: 'certify' | 'revoke' | 'review';
  confidence: number; reason: string; riskLevel: 'low' | 'medium' | 'high' | 'critical';
}

const ITEMS: CertItem[] = [
  { id: 'CI-001', user: 'John Miller', department: 'Finance', role: 'Z_FI_AP_CLERK', roleId: 'R001', lastUsed: '2026-10-24', usagePercent: 92, recommendation: 'certify', confidence: 96, reason: 'Active daily use, core job function', riskLevel: 'low' },
  { id: 'CI-002', user: 'John Miller', department: 'Finance', role: 'Z_FI_GL_POST', roleId: 'R002', lastUsed: '2026-10-25', usagePercent: 78, recommendation: 'certify', confidence: 89, reason: 'Regular use for period-end postings', riskLevel: 'medium' },
  { id: 'CI-003', user: 'Sarah Chen', department: 'Procurement', role: 'Z_MM_BUYER', roleId: 'R003', lastUsed: '2026-10-25', usagePercent: 95, recommendation: 'certify', confidence: 98, reason: 'Primary purchasing role, daily use', riskLevel: 'low' },
  { id: 'CI-004', user: 'Sarah Chen', department: 'Procurement', role: 'Z_SD_SALES_REP', roleId: 'R004', lastUsed: '2026-04-15', usagePercent: 3, recommendation: 'revoke', confidence: 94, reason: 'Not used in 6 months. Not related to job function.', riskLevel: 'high' },
  { id: 'CI-005', user: 'Mike Torres', department: 'IT', role: 'SAP_BC_ADMIN', roleId: 'R005', lastUsed: '2026-10-20', usagePercent: 45, recommendation: 'review', confidence: 62, reason: 'Moderate use but high-privilege. Manager review needed.', riskLevel: 'critical' },
  { id: 'CI-006', user: 'Lisa Park', department: 'HR', role: 'Z_HR_PAYROLL', roleId: 'R006', lastUsed: '2026-10-25', usagePercent: 88, recommendation: 'certify', confidence: 93, reason: 'Active payroll processing role', riskLevel: 'medium' },
  { id: 'CI-007', user: 'Lisa Park', department: 'HR', role: 'Z_FI_AP_APPROVE', roleId: 'R007', lastUsed: '2026-07-10', usagePercent: 8, recommendation: 'revoke', confidence: 91, reason: 'Rarely used. Creates SoD with payroll role.', riskLevel: 'critical' },
  { id: 'CI-008', user: 'David Kim', department: 'Sales', role: 'Z_SD_ORDER_CREATE', roleId: 'R008', lastUsed: '2026-10-25', usagePercent: 97, recommendation: 'certify', confidence: 99, reason: 'Core sales role, used daily', riskLevel: 'low' },
  { id: 'CI-009', user: 'Emma Wilson', department: 'Finance', role: 'Z_FI_AR_CLERK', roleId: 'R009', lastUsed: '2026-08-01', usagePercent: 12, recommendation: 'revoke', confidence: 87, reason: 'Transferred from AR to AP 3 months ago. Role no longer needed.', riskLevel: 'medium' },
  { id: 'CI-010', user: 'Tom Brown', department: 'Warehouse', role: 'Z_WM_OPERATOR', roleId: 'R010', lastUsed: '2026-10-24', usagePercent: 82, recommendation: 'certify', confidence: 95, reason: 'Active warehouse operations role', riskLevel: 'low' },
];

const recColors: Record<string, { bg: string; text: string; icon: typeof CheckCircleIcon }> = {
  certify: { bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-400', icon: CheckCircleIcon },
  revoke: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-700 dark:text-red-400', icon: XCircleIcon },
  review: { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-400', icon: ExclamationTriangleIcon },
};

export function AICertification() {
  const [filter, setFilter] = useState<'all' | 'certify' | 'revoke' | 'review'>('all');

  const { data: items = ITEMS } = useQuery({ queryKey: ['ai-cert-items'], queryFn: () => api.get('/ai-copilot/certification/recommendations/current').then(r => r.data?.items ?? ITEMS).catch(() => ITEMS) });
  const applyAll = useMutation({ mutationFn: () => api.post('/ai-copilot/certification/apply/current') });

  const filtered = filter === 'all' ? items : items.filter((i: CertItem) => i.recommendation === filter);
  const certifyCount = items.filter((i: CertItem) => i.recommendation === 'certify').length;
  const revokeCount = items.filter((i: CertItem) => i.recommendation === 'revoke').length;
  const reviewCount = items.filter((i: CertItem) => i.recommendation === 'review').length;
  const avgConfidence = items.length > 0 ? Math.round(items.reduce((s: number, i: CertItem) => s + i.confidence, 0) / items.length) : 0;

  const stats = [
    { label: 'Items to Review', value: items.length, icon: DocumentCheckIcon, color: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400' },
    { label: 'AI: Certify', value: certifyCount, icon: CheckCircleIcon, color: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400' },
    { label: 'AI: Revoke', value: revokeCount, icon: XCircleIcon, color: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400' },
    { label: 'Avg Confidence', value: `${avgConfidence}%`, icon: SparklesIcon, color: 'bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">AI Certification Recommendations</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">AI pre-fills certification decisions using role usage data and risk analysis</p>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-700 dark:text-gray-300">
            <ArrowPathIcon className="h-4 w-4" /> Refresh
          </button>
          <button onClick={() => applyAll.mutate()}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg">
            <SparklesIcon className="h-4 w-4" /> Apply All AI Recommendations
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(s => (
          <div key={s.label} className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-gray-200 dark:border-slate-700">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${s.color}`}><s.icon className="h-5 w-5" /></div>
              <div><p className="text-2xl font-bold text-gray-900 dark:text-white">{s.value}</p><p className="text-xs text-gray-500 dark:text-gray-400">{s.label}</p></div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary Bar */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Summary:</span>
          <div className="flex-1 h-3 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden flex">
            <div className="bg-emerald-500 h-full" style={{ width: `${(certifyCount / items.length) * 100}%` }} title={`${certifyCount} certify`} />
            <div className="bg-red-500 h-full" style={{ width: `${(revokeCount / items.length) * 100}%` }} title={`${revokeCount} revoke`} />
            <div className="bg-amber-500 h-full" style={{ width: `${(reviewCount / items.length) * 100}%` }} title={`${reviewCount} review`} />
          </div>
          <div className="flex gap-4 text-xs">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" />{certifyCount} Certify</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" />{revokeCount} Revoke</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" />{reviewCount} Review</span>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        {(['all', 'certify', 'revoke', 'review'] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${filter === f ? 'bg-indigo-600 text-white' : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'}`}>
            {f === 'all' ? `All (${items.length})` : `${f.charAt(0).toUpperCase() + f.slice(1)} (${items.filter((i: CertItem) => i.recommendation === f).length})`}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-slate-700/50">
            <tr>{['User', 'Dept', 'Role', 'Last Used', 'Usage', 'AI Recommendation', 'Confidence', 'Reason'].map(h => <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
            {filtered.map((item: CertItem) => {
              const rec = recColors[item.recommendation];
              const Icon = rec.icon;
              return (
                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/30">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{item.user}</td>
                  <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">{item.department}</td>
                  <td className="px-4 py-3 text-sm font-mono text-gray-700 dark:text-gray-300">{item.role}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{item.lastUsed}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-12 h-1.5 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${item.usagePercent > 50 ? 'bg-emerald-500' : item.usagePercent > 20 ? 'bg-amber-500' : 'bg-red-500'}`} style={{ width: `${item.usagePercent}%` }} />
                      </div>
                      <span className="text-xs text-gray-600 dark:text-gray-400">{item.usagePercent}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full ${rec.bg} ${rec.text}`}>
                      <Icon className="h-3.5 w-3.5" /> {item.recommendation}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <div className="w-10 h-1.5 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
                        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${item.confidence}%` }} />
                      </div>
                      <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{item.confidence}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600 dark:text-gray-400 max-w-[200px] truncate" title={item.reason}>{item.reason}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
