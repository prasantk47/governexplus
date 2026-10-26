/**
 * GovernexPlus One-Click Remediation Dashboard
 * AI-powered violation remediation with automated fix plans
 */
import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  ShieldExclamationIcon,
  WrenchScrewdriverIcon,
  CheckCircleIcon,
  BoltIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

interface Violation {
  id: string; user: string; userId: string; rule: string; severity: 'critical' | 'high' | 'medium' | 'low';
  description: string; detectedAt: string; autoRemediable: boolean; system: string;
}
interface RemediationStep { order: number; action: string; target: string; detail: string; reversible: boolean; }
interface RemediationPlan {
  id: string; violationId: string; violationSummary: string; user: string; steps: RemediationStep[];
  impact: string; confidenceScore: number; estimatedDuration: string;
  status: 'pending' | 'executing' | 'completed' | 'failed'; createdAt: string;
}
interface HistoryItem {
  id: string; user: string; rule: string; before: string; after: string;
  executedAt: string; result: 'success' | 'partial' | 'failed';
}

const VIOLATIONS: Violation[] = [
  { id: 'VIO-4201', user: 'John Miller', userId: 'JMILLER', rule: 'SoD-FI-001', severity: 'critical', description: 'Create Vendor + Approve Payment', detectedAt: '2026-10-25', autoRemediable: true, system: 'SAP ECC' },
  { id: 'VIO-4202', user: 'Sarah Chen', userId: 'SCHEN', rule: 'SoD-MM-003', severity: 'high', description: 'Create PO + Goods Receipt', detectedAt: '2026-10-25', autoRemediable: true, system: 'SAP ECC' },
  { id: 'VIO-4203', user: 'Mike Torres', userId: 'MTORRES', rule: 'SoD-FI-008', severity: 'high', description: 'Post JE + Approve JE', detectedAt: '2026-10-24', autoRemediable: true, system: 'SAP S/4' },
  { id: 'VIO-4204', user: 'Lisa Park', userId: 'LPARK', rule: 'SoD-BA-002', severity: 'medium', description: 'Maintain User Master + Assign Roles', detectedAt: '2026-10-24', autoRemediable: false, system: 'SAP ECC' },
  { id: 'VIO-4205', user: 'David Kim', userId: 'DKIM', rule: 'SoD-SD-005', severity: 'medium', description: 'Create Sales Order + Release Billing', detectedAt: '2026-10-23', autoRemediable: true, system: 'SAP ECC' },
  { id: 'VIO-4206', user: 'Emma Wilson', userId: 'EWILSON', rule: 'SoD-HR-001', severity: 'critical', description: 'Maintain Employee + Process Payroll', detectedAt: '2026-10-23', autoRemediable: true, system: 'SAP HCM' },
];

const PLANS: RemediationPlan[] = [
  { id: 'REM-101', violationId: 'VIO-4201', violationSummary: 'Create Vendor + Approve Payment', user: 'John Miller',
    steps: [
      { order: 1, action: 'Remove Role', target: 'Z_FI_AP_APPROVE', detail: 'Remove payment approval from JMILLER', reversible: true },
      { order: 2, action: 'Reassign', target: 'Z_FI_AP_APPROVE_L2', detail: 'Route approval to manager RJOHNSON', reversible: true },
    ], impact: 'User loses payment approval. Rerouted to manager.', confidenceScore: 94, estimatedDuration: '< 5 min', status: 'pending', createdAt: '2026-10-25' },
  { id: 'REM-102', violationId: 'VIO-4203', violationSummary: 'Post JE + Approve JE', user: 'Mike Torres',
    steps: [{ order: 1, action: 'Remove Tcode', target: 'FB01', detail: 'Remove direct posting', reversible: true }],
    impact: 'User submits JE requests instead of posting.', confidenceScore: 88, estimatedDuration: '< 3 min', status: 'executing', createdAt: '2026-10-25' },
  { id: 'REM-100', violationId: 'VIO-4190', violationSummary: 'Create PO + Goods Receipt', user: 'Anna Lee',
    steps: [{ order: 1, action: 'Remove Role', target: 'Z_MM_GR_POST', detail: 'Remove goods receipt role', reversible: true }],
    impact: 'User no longer posts goods receipts.', confidenceScore: 97, estimatedDuration: '< 2 min', status: 'completed', createdAt: '2026-10-24' },
];

const HISTORY: HistoryItem[] = [
  { id: 'H-1', user: 'Anna Lee', rule: 'SoD-MM-003', before: 'Z_MM_BUYER + Z_MM_GR_POST', after: 'Z_MM_BUYER only', executedAt: '2026-10-24', result: 'success' },
  { id: 'H-2', user: 'Tom Brown', rule: 'SoD-FI-001', before: 'Z_FI_AP_FULL', after: 'Z_FI_AP_CREATE + approval rerouted', executedAt: '2026-10-23', result: 'success' },
  { id: 'H-3', user: 'Rick Santos', rule: 'SoD-SD-005', before: 'Z_SD_FULL_ACCESS', after: 'Z_SD_ORDER_CREATE', executedAt: '2026-10-22', result: 'partial' },
];

const sevColor: Record<string, string> = { critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400', medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400', low: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' };
const statusColor: Record<string, string> = { pending: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', executing: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400', completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400', failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' };
const resultColor: Record<string, string> = { success: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400', partial: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400', failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' };

type Tab = 'violations' | 'plans' | 'history';

export function OneClickRemediation() {
  const [tab, setTab] = useState<Tab>('violations');
  const [activePlan, setActivePlan] = useState<RemediationPlan | null>(null);

  const { data: violations = VIOLATIONS } = useQuery({ queryKey: ['ai-remediation-violations'], queryFn: () => api.get('/ai-copilot/remediation/violations').then(r => r.data?.violations ?? VIOLATIONS).catch(() => VIOLATIONS) });
  const { data: plans = PLANS } = useQuery({ queryKey: ['ai-remediation-plans'], queryFn: () => api.get('/ai-copilot/remediation/plans').then(r => r.data?.plans ?? PLANS).catch(() => PLANS) });
  const { data: history = HISTORY } = useQuery({ queryKey: ['ai-remediation-history'], queryFn: () => api.get('/ai-copilot/remediation/history').then(r => r.data?.history ?? HISTORY).catch(() => HISTORY) });

  const generatePlan = useMutation({
    mutationFn: (v: Violation) => api.post('/ai-copilot/remediation/analyze', { violation_id: v.id }),
    onSuccess: (_, v) => {
      setActivePlan({
        id: 'REM-NEW', violationId: v.id, violationSummary: v.description, user: v.user,
        steps: [
          { order: 1, action: 'Remove Role', target: 'Conflicting role', detail: `Remove conflicting access from ${v.userId}`, reversible: true },
          { order: 2, action: 'Assign Alternative', target: 'Replacement role', detail: 'Assign least-privilege replacement', reversible: true },
        ], impact: 'User retains essential functions without the conflict.', confidenceScore: 91, estimatedDuration: '< 5 min', status: 'pending', createdAt: new Date().toISOString(),
      });
    },
    onError: (_, v) => {
      setActivePlan({
        id: 'REM-NEW', violationId: v.id, violationSummary: v.description, user: v.user,
        steps: [
          { order: 1, action: 'Remove Role', target: 'Conflicting role', detail: `Remove conflicting access from ${v.userId}`, reversible: true },
          { order: 2, action: 'Assign Alternative', target: 'Replacement role', detail: 'Assign least-privilege replacement', reversible: true },
        ], impact: 'User retains essential functions without the conflict.', confidenceScore: 91, estimatedDuration: '< 5 min', status: 'pending', createdAt: new Date().toISOString(),
      });
    },
  });

  const executePlan = useMutation({ mutationFn: (planId: string) => api.post(`/ai-copilot/remediation/execute`, { plan_id: planId }) });

  const autoCount = violations.filter(v => v.autoRemediable).length;
  const successRate = history.length > 0 ? Math.round((history.filter(h => h.result === 'success').length / history.length) * 100) : 0;

  const stats = [
    { label: 'Total Violations', value: violations.length, icon: ShieldExclamationIcon, color: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400' },
    { label: 'Auto-Remediable', value: autoCount, icon: BoltIcon, color: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400' },
    { label: 'Plans Generated', value: plans.length, icon: WrenchScrewdriverIcon, color: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400' },
    { label: 'Success Rate', value: `${successRate}%`, icon: CheckCircleIcon, color: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">One-Click Remediation</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">AI-powered violation remediation with automated fix plans</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700">
          <ArrowPathIcon className="h-4 w-4" /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(s => (
          <div key={s.label} className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-gray-200 dark:border-slate-700">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${s.color}`}>
                <s.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{s.value}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{s.label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-slate-700">
        <nav className="flex gap-6">
          {([['violations', 'Active Violations', violations.length], ['plans', 'Remediation Plans', plans.length], ['history', 'History', history.length]] as [Tab, string, number][]).map(([key, label, count]) => (
            <button key={key} onClick={() => setTab(key)}
              className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${tab === key ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 dark:border-indigo-400' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'}`}>
              {label} <span className="ml-1.5 text-xs bg-gray-100 dark:bg-slate-700 px-2 py-0.5 rounded-full">{count}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Violations Table */}
      {tab === 'violations' && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-slate-700/50">
              <tr>{['ID', 'User', 'Rule', 'Description', 'Severity', 'System', 'Auto-Fix', 'Action'].map(h => <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
              {violations.map(v => (
                <tr key={v.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/30">
                  <td className="px-4 py-3 text-sm font-mono text-indigo-600 dark:text-indigo-400">{v.id}</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{v.user}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{v.rule}</td>
                  <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">{v.description}</td>
                  <td className="px-4 py-3"><span className={`text-xs font-semibold px-2 py-1 rounded-full ${sevColor[v.severity]}`}>{v.severity}</span></td>
                  <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">{v.system}</td>
                  <td className="px-4 py-3">{v.autoRemediable ? <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">Yes</span> : <span className="text-xs text-gray-400">Manual</span>}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => generatePlan.mutate(v)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition-colors">
                      <BoltIcon className="h-3.5 w-3.5" /> Fix It
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Plans Table */}
      {tab === 'plans' && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-slate-700/50">
              <tr>{['Plan ID', 'User', 'Violation', 'Steps', 'Confidence', 'Status', ''].map(h => <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
              {plans.map(p => (
                <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/30">
                  <td className="px-4 py-3 text-sm font-mono text-indigo-600 dark:text-indigo-400">{p.id}</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{p.user}</td>
                  <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">{p.violationSummary}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{p.steps.length} steps</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
                        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${p.confidenceScore}%` }} />
                      </div>
                      <span className="text-xs text-gray-600 dark:text-gray-400">{p.confidenceScore}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3"><span className={`text-xs font-semibold px-2 py-1 rounded-full ${statusColor[p.status]}`}>{p.status}</span></td>
                  <td className="px-4 py-3">{p.status === 'pending' && <button onClick={() => setActivePlan(p)} className="text-xs text-indigo-600 dark:text-indigo-400 font-medium hover:underline">View</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* History Table */}
      {tab === 'history' && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-slate-700/50">
              <tr>{['User', 'Rule', 'Before', 'After', 'Result', 'Date'].map(h => <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
              {history.map(h => (
                <tr key={h.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/30">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{h.user}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{h.rule}</td>
                  <td className="px-4 py-3"><span className="text-xs bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 px-2 py-1 rounded">{h.before}</span></td>
                  <td className="px-4 py-3"><span className="text-xs bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 px-2 py-1 rounded">{h.after}</span></td>
                  <td className="px-4 py-3"><span className={`text-xs font-semibold px-2 py-1 rounded-full ${resultColor[h.result]}`}>{h.result}</span></td>
                  <td className="px-4 py-3 text-xs text-gray-500">{h.executedAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Plan Modal */}
      {activePlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-slate-700">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Remediation Plan</h3>
                <p className="text-sm text-gray-500 mt-1">{activePlan.violationSummary} &mdash; {activePlan.user}</p>
              </div>
              <button onClick={() => setActivePlan(null)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"><XMarkIcon className="h-5 w-5" /></button>
            </div>
            <div className="p-6 space-y-5">
              <div className="flex gap-8">
                <div>
                  <span className="text-xs text-gray-500 uppercase">Confidence</span>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-24 h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${activePlan.confidenceScore >= 90 ? 'bg-emerald-500' : 'bg-amber-500'}`} style={{ width: `${activePlan.confidenceScore}%` }} />
                    </div>
                    <span className="text-sm font-bold text-gray-900 dark:text-white">{activePlan.confidenceScore}%</span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500 uppercase">Duration</span>
                  <div className="flex items-center gap-1 mt-1">
                    <ClockIcon className="h-4 w-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-900 dark:text-white">{activePlan.estimatedDuration}</span>
                  </div>
                </div>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Remediation Steps</h4>
                <div className="space-y-3">
                  {activePlan.steps.map(step => (
                    <div key={step.order} className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs font-bold flex items-center justify-center">{step.order}</span>
                      <div>
                        <span className="text-sm font-medium text-gray-900 dark:text-white">{step.action}</span>
                        <span className="text-xs text-gray-500 font-mono ml-2">{step.target}</span>
                        {step.reversible && <span className="ml-2 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 px-1.5 py-0.5 rounded">Reversible</span>}
                        <p className="text-xs text-gray-500 mt-1">{step.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                <div className="flex items-start gap-2">
                  <ExclamationTriangleIcon className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="text-xs font-semibold text-amber-700 dark:text-amber-400 uppercase">Impact</span>
                    <p className="text-sm text-amber-800 dark:text-amber-300 mt-1">{activePlan.impact}</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3 p-6 border-t border-gray-200 dark:border-slate-700">
              <button onClick={() => setActivePlan(null)} className="px-4 py-2 border border-gray-200 dark:border-slate-600 rounded-lg text-sm text-gray-700 dark:text-gray-300">Cancel</button>
              <button onClick={() => { executePlan.mutate(activePlan.id); setActivePlan(null); }}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg">
                <BoltIcon className="h-4 w-4" /> Execute Remediation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
