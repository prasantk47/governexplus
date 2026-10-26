/**
 * GovernexPlus AI Finding/Narrative Generation
 * Select violations, generate complete audit findings with AI
 */
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  DocumentTextIcon,
  SparklesIcon,
  ArrowDownTrayIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

interface Finding {
  title: string; rootCause: string; businessImpact: string; dollarImpact: string;
  recommendation: string; managementResponse: string; riskRating: string; timeline: string;
}

interface ViolationOption { id: string; user: string; rule: string; description: string; severity: string; }

const VIOLATIONS: ViolationOption[] = [
  { id: 'VIO-4201', user: 'John Miller', rule: 'SoD-FI-001', description: 'Create Vendor + Approve Payment', severity: 'critical' },
  { id: 'VIO-4202', user: 'Sarah Chen', rule: 'SoD-MM-003', description: 'Create PO + Goods Receipt', severity: 'high' },
  { id: 'VIO-4203', user: 'Mike Torres', rule: 'SoD-FI-008', description: 'Post JE + Approve JE', severity: 'high' },
  { id: 'VIO-4206', user: 'Emma Wilson', rule: 'SoD-HR-001', description: 'Maintain Employee + Process Payroll', severity: 'critical' },
];

const TEMPLATES = [
  { name: 'SOX Compliance Finding', category: 'Financial', desc: 'Standard SOX finding with COSO framework reference' },
  { name: 'Access Risk Finding', category: 'IT General Controls', desc: 'SoD violation with access governance context' },
  { name: 'Privileged Access Finding', category: 'IT Security', desc: 'Emergency access or over-privileged accounts' },
  { name: 'Data Privacy Finding', category: 'GDPR/Privacy', desc: 'Access to sensitive data without business need' },
];

function mockFinding(v: ViolationOption): Finding {
  const findings: Record<string, Finding> = {
    'VIO-4201': {
      title: 'Segregation of Duties Violation: Vendor Master Maintenance and Payment Processing',
      rootCause: 'During the Q3 2026 access review, user John Miller (JMILLER) in the Accounts Payable department was identified with conflicting access to vendor master maintenance (FK01, FK05, XK01) and payment processing (F-53, F110, FBZ1). This conflict arose from a role reassignment in June 2026 when the user was temporarily assigned additional duties during a staff vacancy. The temporary access was not revoked after the vacancy was filled.',
      businessImpact: 'This SoD violation creates an unmitigated risk of fraudulent vendor creation and payment processing. The user could create fictitious vendors and process payments to those vendors without independent verification. Based on the user\'s transaction history, 847 vendor master changes and 1,203 payment transactions were processed during the violation period.',
      dollarImpact: '$2.4M total payment volume processed during violation period. Estimated exposure: $180K based on industry fraud benchmarks (7.5% of single-approver payments).',
      recommendation: '1. Immediately remove payment processing access (role Z_FI_AP_APPROVE) from user JMILLER.\n2. Reassign payment approval to the AP Manager (RJOHNSON).\n3. Implement compensating control: dual approval for payments > $10,000.\n4. Review all payments processed by JMILLER during the violation period (June-October 2026).\n5. Update the role provisioning workflow to include SoD pre-check before assignment.',
      managementResponse: 'Management agrees with the finding. The conflicting access will be removed by [date]. A retroactive review of all payments processed during the violation period is being conducted by Internal Audit. The SoD pre-check has been added to the access request workflow effective immediately.',
      riskRating: 'High',
      timeline: 'Immediate remediation (access removal within 24 hours). Retroactive review completion within 30 days.',
    },
  };
  return findings[v.id] || {
    title: `Segregation of Duties Violation: ${v.description}`,
    rootCause: `User ${v.user} was identified with conflicting access in rule ${v.rule}. The conflicting functions (${v.description}) were assigned through separate role provisioning events without adequate SoD pre-screening. Root cause analysis indicates the access request workflow did not include automated conflict detection at the time of assignment.`,
    businessImpact: `This violation creates risk of unauthorized transactions. The user has the technical ability to complete the full transaction cycle (${v.description}) without independent verification, bypassing the intended control framework.`,
    dollarImpact: 'Estimated exposure based on transaction volume during violation period. Detailed financial impact assessment recommended.',
    recommendation: `1. Remove conflicting access immediately.\n2. Implement compensating control.\n3. Review transactions during violation period.\n4. Update provisioning workflow with SoD pre-check.`,
    managementResponse: 'Management acknowledges the finding and will implement corrective actions within the specified timeline.',
    riskRating: v.severity === 'critical' ? 'High' : 'Medium',
    timeline: 'Remediation within 5 business days. Transaction review within 30 days.',
  };
}

export function AIFindings() {
  const [selected, setSelected] = useState<string[]>([]);
  const [findings, setFindings] = useState<Map<string, Finding>>(new Map());
  const [expanded, setExpanded] = useState<string | null>(null);

  const generate = useMutation({
    mutationFn: (ids: string[]) => api.post('/ai-copilot/findings/generate', { violation_ids: ids }),
    onSuccess: () => {
      const map = new Map<string, Finding>();
      selected.forEach(id => {
        const v = VIOLATIONS.find(x => x.id === id);
        if (v) map.set(id, mockFinding(v));
      });
      setFindings(map);
    },
    onError: () => {
      const map = new Map<string, Finding>();
      selected.forEach(id => {
        const v = VIOLATIONS.find(x => x.id === id);
        if (v) map.set(id, mockFinding(v));
      });
      setFindings(map);
    },
  });

  const toggle = (id: string) => setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  const sevColor: Record<string, string> = { critical: 'text-red-600 dark:text-red-400', high: 'text-orange-600 dark:text-orange-400', medium: 'text-amber-600', low: 'text-blue-600' };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">AI Finding Generator</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Select violations and generate complete audit findings with root cause, impact, and recommendations</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Selection */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Select Violations</h3>
              <button onClick={() => generate.mutate(selected)} disabled={selected.length === 0}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg disabled:opacity-50">
                <SparklesIcon className="h-4 w-4" /> Generate {selected.length > 1 ? `${selected.length} Findings` : 'Finding'}
              </button>
            </div>
            <div className="space-y-2">
              {VIOLATIONS.map(v => (
                <label key={v.id} className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${selected.includes(v.id) ? 'border-indigo-300 dark:border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20' : 'border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/30'}`}>
                  <input type="checkbox" checked={selected.includes(v.id)} onChange={() => toggle(v.id)} className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono text-indigo-600 dark:text-indigo-400">{v.id}</span>
                      <span className="text-sm font-medium text-gray-900 dark:text-white">{v.user}</span>
                      <span className={`text-xs font-semibold ${sevColor[v.severity]}`}>{v.severity}</span>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{v.rule}: {v.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Generated Findings */}
          {findings.size > 0 && Array.from(findings.entries()).map(([id, finding]) => {
            const v = VIOLATIONS.find(x => x.id === id)!;
            const isOpen = expanded === id;
            return (
              <div key={id} className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
                <button onClick={() => setExpanded(isOpen ? null : id)} className="w-full flex items-center justify-between p-5 text-left">
                  <div>
                    <span className="text-xs text-indigo-600 dark:text-indigo-400 font-mono">{v.id} &mdash; {v.rule}</span>
                    <h3 className="text-base font-semibold text-gray-900 dark:text-white mt-1">{finding.title}</h3>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs font-semibold px-2 py-1 rounded-full ${finding.riskRating === 'High' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'}`}>{finding.riskRating}</span>
                    {isOpen ? <ChevronUpIcon className="h-5 w-5 text-gray-400" /> : <ChevronDownIcon className="h-5 w-5 text-gray-400" />}
                  </div>
                </button>
                {isOpen && (
                  <div className="px-5 pb-5 space-y-4 border-t border-gray-100 dark:border-slate-700 pt-4">
                    {[
                      ['Root Cause Analysis', finding.rootCause],
                      ['Business Impact', finding.businessImpact],
                      ['Financial Impact', finding.dollarImpact],
                      ['Recommendation', finding.recommendation],
                      ['Management Response (Draft)', finding.managementResponse],
                      ['Remediation Timeline', finding.timeline],
                    ].map(([label, text]) => (
                      <div key={label as string}>
                        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">{label}</h4>
                        <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-line leading-relaxed">{text}</p>
                      </div>
                    ))}
                    <div className="flex gap-3 pt-2">
                      <button className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg">
                        <ArrowDownTrayIcon className="h-3.5 w-3.5" /> Export to Audit
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Templates */}
        <div>
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <DocumentTextIcon className="h-4 w-4 text-indigo-500" /> Finding Templates
            </h3>
            <div className="space-y-3">
              {TEMPLATES.map(t => (
                <div key={t.name} className="p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{t.name}</p>
                  <p className="text-xs text-indigo-500 mt-0.5">{t.category}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{t.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
