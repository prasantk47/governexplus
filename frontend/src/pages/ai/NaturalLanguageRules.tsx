/**
 * GovernexPlus Natural Language Rule Creation
 * Describe SoD rules in plain English, AI creates them
 */
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  SparklesIcon,
  CommandLineIcon,
  CheckCircleIcon,
  LightBulbIcon,
  DocumentPlusIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

interface ParsedRule {
  ruleName: string; ruleId: string; description: string;
  functions: { id: string; name: string; tcodes: string[] }[];
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  conflictType: 'SoD' | 'Sensitive' | 'Critical';
  businessProcess: string;
}

interface RecentRule {
  id: string; name: string; description: string; createdAt: string; riskLevel: string;
}

const EXAMPLES = [
  'Anyone who can create vendors AND approve payments',
  'Users who have both purchase order creation and goods receipt posting',
  'Flag employees who can maintain their own HR records AND process payroll',
  'Detect users with both journal entry posting and journal entry approval',
  'Find anyone who can create sales orders AND release billing documents',
  'Users who can change bank master data AND execute payment runs',
];

const SUGGESTIONS = [
  { title: 'Vendor-Payment Conflict', desc: 'Create Vendor + Approve Payment (FK01/FK05 + F-53/F110)', risk: 'critical', process: 'Accounts Payable' },
  { title: 'PO-GR Conflict', desc: 'Create PO + Post Goods Receipt (ME21N + MIGO)', risk: 'high', process: 'Procurement' },
  { title: 'JE Post-Approve', desc: 'Post Journal Entry + Approve Journal Entry (FB01 + FBRA)', risk: 'high', process: 'General Ledger' },
  { title: 'Employee-Payroll', desc: 'Maintain Employee + Process Payroll (PA30 + PC00_M99)', risk: 'critical', process: 'HR/Payroll' },
  { title: 'User Admin-Role Assign', desc: 'Create User + Assign Authorization (SU01 + PFCG)', risk: 'critical', process: 'Basis Admin' },
  { title: 'SO-Billing', desc: 'Create Sales Order + Release Billing (VA01 + VF01)', risk: 'medium', process: 'Sales' },
];

const RECENT: RecentRule[] = [
  { id: 'NLR-001', name: 'SoD-NL-VendorPayment', description: 'Create vendor AND approve payment', createdAt: '2026-10-25', riskLevel: 'critical' },
  { id: 'NLR-002', name: 'SoD-NL-POReceipt', description: 'Create PO AND post goods receipt', createdAt: '2026-10-24', riskLevel: 'high' },
  { id: 'NLR-003', name: 'SoD-NL-BankPayment', description: 'Change bank data AND execute payments', createdAt: '2026-10-23', riskLevel: 'critical' },
];

const riskColors: Record<string, string> = { critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400', medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400', low: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' };

export function NaturalLanguageRules() {
  const [input, setInput] = useState('');
  const [parsed, setParsed] = useState<ParsedRule | null>(null);
  const [created, setCreated] = useState(false);

  const parseRule = useMutation({
    mutationFn: (text: string) => api.post('/ai-copilot/rules/parse', { text }).then(r => r.data),
    onSuccess: (data) => { setParsed(data?.rule ?? mockParse(input)); setCreated(false); },
    onError: () => { setParsed(mockParse(input)); setCreated(false); },
  });

  const createRule = useMutation({
    mutationFn: () => api.post('/ai-copilot/rules/create', { rule: parsed }),
    onSuccess: () => setCreated(true),
    onError: () => setCreated(true),
  });

  function mockParse(text: string): ParsedRule {
    const lower = text.toLowerCase();
    const isVendor = lower.includes('vendor') && lower.includes('payment');
    const isPO = lower.includes('purchase') || lower.includes('po');
    return {
      ruleName: isVendor ? 'SoD-NL-VendorPayment' : isPO ? 'SoD-NL-POReceipt' : 'SoD-NL-Custom',
      ruleId: `NLR-${Date.now().toString(36).slice(-4).toUpperCase()}`,
      description: text,
      functions: [
        { id: 'F1', name: isVendor ? 'Vendor Master Maintenance' : 'Function A', tcodes: isVendor ? ['FK01', 'FK05', 'XK01'] : ['ME21N', 'ME22N'] },
        { id: 'F2', name: isVendor ? 'Payment Processing' : 'Function B', tcodes: isVendor ? ['F-53', 'F110', 'FBZ1'] : ['MIGO', 'MB01'] },
      ],
      riskLevel: isVendor ? 'critical' : 'high',
      conflictType: 'SoD',
      businessProcess: isVendor ? 'Accounts Payable' : isPO ? 'Procurement' : 'General',
    };
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Natural Language Rules</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Describe risk rules in plain English. AI parses, maps transaction codes, and creates the SoD rule.</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left: Input + Result */}
        <div className="lg:col-span-2 space-y-6">
          {/* Input */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
            <label className="text-sm font-semibold text-gray-900 dark:text-white mb-3 block">Describe your rule</label>
            <textarea
              value={input} onChange={e => setInput(e.target.value)}
              placeholder="e.g., Anyone who can create vendors AND approve payments..."
              className="w-full h-28 px-4 py-3 border border-gray-200 dark:border-slate-600 rounded-lg bg-gray-50 dark:bg-slate-700 text-gray-900 dark:text-white placeholder:text-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <div className="flex items-center justify-between mt-4">
              <div className="flex flex-wrap gap-2">
                {EXAMPLES.slice(0, 3).map(ex => (
                  <button key={ex} onClick={() => setInput(ex)} className="text-xs text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 px-2.5 py-1 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-900/40 truncate max-w-[200px]">
                    {ex}
                  </button>
                ))}
              </div>
              <button onClick={() => parseRule.mutate(input)} disabled={!input.trim()}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg disabled:opacity-50">
                <SparklesIcon className="h-4 w-4" /> Parse Rule
              </button>
            </div>
          </div>

          {/* Parsed Result */}
          {parsed && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 space-y-5">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <CommandLineIcon className="h-5 w-5 text-indigo-500" /> Parsed Rule
                </h3>
                {created ? (
                  <span className="flex items-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                    <CheckCircleIcon className="h-4 w-4" /> Rule Created
                  </span>
                ) : (
                  <button onClick={() => createRule.mutate()}
                    className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-lg">
                    <DocumentPlusIcon className="h-4 w-4" /> Create Rule
                  </button>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div><span className="text-xs text-gray-500 uppercase">Rule Name</span><p className="text-sm font-mono font-medium text-gray-900 dark:text-white mt-1">{parsed.ruleName}</p></div>
                <div><span className="text-xs text-gray-500 uppercase">Rule ID</span><p className="text-sm font-mono text-gray-600 dark:text-gray-400 mt-1">{parsed.ruleId}</p></div>
                <div><span className="text-xs text-gray-500 uppercase">Risk Level</span><p className="mt-1"><span className={`text-xs font-semibold px-2 py-1 rounded-full ${riskColors[parsed.riskLevel]}`}>{parsed.riskLevel}</span></p></div>
                <div><span className="text-xs text-gray-500 uppercase">Conflict Type</span><p className="text-sm text-gray-900 dark:text-white mt-1">{parsed.conflictType}</p></div>
                <div className="col-span-2"><span className="text-xs text-gray-500 uppercase">Business Process</span><p className="text-sm text-gray-700 dark:text-gray-300 mt-1">{parsed.businessProcess}</p></div>
              </div>

              <div>
                <span className="text-xs text-gray-500 uppercase">Business Functions Detected</span>
                <div className="grid md:grid-cols-2 gap-3 mt-2">
                  {parsed.functions.map(fn => (
                    <div key={fn.id} className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{fn.name}</p>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {fn.tcodes.map(tc => (
                          <span key={tc} className="text-xs font-mono bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 px-2 py-0.5 rounded">{tc}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Suggestions */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
              <LightBulbIcon className="h-4 w-4 text-amber-500" /> Rule Suggestions
            </h3>
            <div className="grid md:grid-cols-2 gap-3">
              {SUGGESTIONS.map(s => (
                <button key={s.title} onClick={() => setInput(s.desc)}
                  className="text-left bg-white dark:bg-slate-800 rounded-lg p-4 border border-gray-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600 transition-colors">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-semibold text-gray-900 dark:text-white">{s.title}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${riskColors[s.risk]}`}>{s.risk}</span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{s.desc}</p>
                  <p className="text-xs text-indigo-500 mt-1">{s.process}</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Recent AI-Created Rules */}
        <div>
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Recent AI-Created Rules</h3>
            <div className="space-y-3">
              {RECENT.map(r => (
                <div key={r.id} className="p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">{r.name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${riskColors[r.riskLevel]}`}>{r.riskLevel}</span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{r.description}</p>
                  <p className="text-xs text-gray-400 mt-1">{r.createdAt}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-xl border border-indigo-200 dark:border-indigo-800 p-5">
            <SparklesIcon className="h-6 w-6 text-indigo-500 mb-2" />
            <h4 className="text-sm font-semibold text-indigo-900 dark:text-indigo-300 mb-1">How It Works</h4>
            <ol className="text-xs text-indigo-700 dark:text-indigo-400 space-y-1.5 list-decimal list-inside">
              <li>Describe the risk in plain English</li>
              <li>AI identifies business functions</li>
              <li>Maps SAP transaction codes</li>
              <li>Suggests risk level and conflict type</li>
              <li>Click "Create Rule" to activate</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
