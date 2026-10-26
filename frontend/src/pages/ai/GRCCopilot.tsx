/**
 * GovernexPlus Deep GRC Copilot
 * Context-aware conversational AI for GRC operations
 */
import { useState, useRef, useEffect } from 'react';
import {
  SparklesIcon,
  PaperAirplaneIcon,
  UserCircleIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  ChartBarIcon,
  DocumentTextIcon,
  ArrowPathIcon,
  LightBulbIcon,
  BoltIcon,
} from '@heroicons/react/24/outline';

interface Message {
  id: string; role: 'user' | 'assistant'; content: string; timestamp: Date;
  dataCards?: DataCard[];
}
interface DataCard {
  title: string; type: 'table' | 'metric' | 'alert' | 'action';
  data: Record<string, unknown>;
}

const SUGGESTED_PROMPTS = [
  { icon: ExclamationTriangleIcon, text: "What's my current risk posture?", color: 'text-red-500' },
  { icon: ShieldCheckIcon, text: 'Show critical SoD violations', color: 'text-amber-500' },
  { icon: DocumentTextIcon, text: 'Prepare quarterly SOX evidence', color: 'text-indigo-500' },
  { icon: ChartBarIcon, text: 'Who has the most access in Finance?', color: 'text-emerald-500' },
  { icon: BoltIcon, text: 'What happens if I remove role Z_FI_AP_APPROVE from John Miller?', color: 'text-violet-500' },
  { icon: LightBulbIcon, text: 'Suggest risk mitigation priorities', color: 'text-sky-500' },
];

const CONTEXT_METRICS = [
  { label: 'Risk Score', value: '55/100', trend: '+3', color: 'text-amber-600 dark:text-amber-400' },
  { label: 'Critical Violations', value: '4', trend: '+1', color: 'text-red-600 dark:text-red-400' },
  { label: 'Pending Approvals', value: '12', trend: '-2', color: 'text-indigo-600 dark:text-indigo-400' },
  { label: 'Active FF Sessions', value: '2', trend: '0', color: 'text-violet-600 dark:text-violet-400' },
];

function generateResponse(query: string): Message {
  const lower = query.toLowerCase();
  const id = Date.now().toString(36);

  if (lower.includes('risk posture') || lower.includes('risk score')) {
    return {
      id, role: 'assistant', timestamp: new Date(),
      content: `**Current Risk Posture Summary**\n\nYour overall risk score is **55/100** (Medium), up 3 points from last week. Here's the breakdown:\n\n- **SoD Violations**: 18 active (4 critical, 6 high, 8 medium)\n- **Privileged Access**: 2 active firefighter sessions\n- **Certification**: Q3 campaign 78% complete, 12 items pending\n- **Access Requests**: 8 pending approval (2 over SLA)\n\n**Top Risk Driver**: Finance department has 40% of all critical violations. Recommend immediate remediation of VIO-4201 (John Miller: Create Vendor + Approve Payment).\n\n**Trend**: Risk score has been rising for 3 consecutive weeks, driven by Q4 hiring and temporary access grants.`,
      dataCards: [
        { title: 'Risk Distribution', type: 'metric', data: { critical: 4, high: 6, medium: 8, low: 12 } },
        { title: 'Top Action', type: 'action', data: { action: 'Remediate VIO-4201', user: 'John Miller', impact: 'Removes #1 critical risk' } },
      ],
    };
  }

  if (lower.includes('critical') && lower.includes('violation')) {
    return {
      id, role: 'assistant', timestamp: new Date(),
      content: `**4 Critical SoD Violations Found**\n\n| ID | User | Rule | Description | Days Open |\n|---|---|---|---|---|\n| VIO-4201 | John Miller | SoD-FI-001 | Create Vendor + Approve Payment | 5 |\n| VIO-4206 | Emma Wilson | SoD-HR-001 | Maintain Employee + Process Payroll | 8 |\n| VIO-4210 | Rick Santos | SoD-BA-002 | User Admin + Role Assignment | 3 |\n| VIO-4215 | Jane Xu | SoD-FI-012 | Bank Master + Payment Run | 12 |\n\n**Immediate Actions Recommended:**\n1. VIO-4215 has been open 12 days — exceeds 7-day SLA. Escalate to CISO.\n2. VIO-4201 can be auto-remediated (94% confidence). Click "Fix It" in One-Click Remediation.\n3. VIO-4206 requires HR manager approval before remediation.`,
      dataCards: [
        { title: 'SLA Breach', type: 'alert', data: { violation: 'VIO-4215', daysPastSLA: 5, user: 'Jane Xu' } },
      ],
    };
  }

  if (lower.includes('sox') || lower.includes('evidence')) {
    return {
      id, role: 'assistant', timestamp: new Date(),
      content: `**Q3 2026 SOX Evidence Package**\n\nI've prepared your quarterly SOX evidence. Here's what's ready:\n\n**Access Controls (ITGC)**\n- SoD violation report: 18 violations, 14 with mitigating controls ✓\n- User access review: Q3 certification 78% complete (deadline: Oct 31)\n- Privileged access log: 47 FF sessions, all reviewed ✓\n- New access requests: 156 processed, average approval time 1.2 days ✓\n\n**Process Controls**\n- Control testing: 23/25 controls passed, 2 deficiencies noted\n- CCM results: 4 automated monitors, all passing\n\n**Outstanding Items:**\n1. Complete remaining 22% of certification campaign (12 items pending)\n2. Remediate 2 control deficiencies (DEF-001, DEF-002)\n3. Obtain management sign-off on risk exceptions\n\nWant me to generate the audit workpapers?`,
    };
  }

  if (lower.includes('finance') && (lower.includes('access') || lower.includes('most'))) {
    return {
      id, role: 'assistant', timestamp: new Date(),
      content: `**Access Analysis: Finance Department**\n\nTop 5 users by access volume in Finance:\n\n| Rank | User | Roles | Tcodes | Risk Score | Violations |\n|---|---|---|---|---|---|\n| 1 | John Miller | 7 | 34 | 72 | 2 critical |\n| 2 | Emma Wilson | 6 | 28 | 65 | 1 critical |\n| 3 | Tom Brown | 5 | 22 | 45 | 0 |\n| 4 | Lisa Park | 5 | 19 | 38 | 0 |\n| 5 | Anna Lee | 4 | 15 | 25 | 0 |\n\n**Insight**: John Miller has 59% more transaction codes than the department average (34 vs 21). He also has the only two critical violations in Finance. Recommend:\n1. One-click remediation for VIO-4201 and VIO-4202\n2. Role redesign to split his Vendor Management and AP Approval functions\n3. Add to next certification campaign as priority review`,
    };
  }

  if (lower.includes('remove') && lower.includes('role')) {
    return {
      id, role: 'assistant', timestamp: new Date(),
      content: `**Impact Simulation: Remove Z_FI_AP_APPROVE from John Miller**\n\n**Before**: 7 roles, 34 transaction codes, Risk Score: 72\n**After**: 6 roles, 28 transaction codes, Risk Score: 48\n\n**What Changes:**\n- ✅ Resolves VIO-4201 (Create Vendor + Approve Payment) — critical violation eliminated\n- ✅ Risk score drops 24 points (72 → 48)\n- ⚠️ John can no longer approve AP payments\n- ⚠️ 12 open payment approvals will need reassignment\n\n**Recommended Actions:**\n1. Reassign payment approval to Robert Johnson (AP Manager)\n2. Update workflow WF-AP-001 for dual approval routing\n3. No impact on John's other 6 roles — all remain functional\n\n**Confidence**: 94% — This is a clean remediation with no side effects.\n\nWant me to execute this remediation?`,
      dataCards: [
        { title: 'Risk Impact', type: 'metric', data: { before: 72, after: 48, reduction: '33%' } },
      ],
    };
  }

  return {
    id, role: 'assistant', timestamp: new Date(),
    content: `I understand you're asking about: "${query}"\n\nI can help with:\n- **Risk Analysis**: "What's my risk posture?", "Show violations in [department]"\n- **User Analysis**: "Who has the most access in [department]?"\n- **Impact Simulation**: "What happens if I remove [role] from [user]?"\n- **Compliance**: "Prepare SOX evidence", "Show certification status"\n- **Remediation**: "How do I fix [violation]?"\n\nTry asking a specific question and I'll provide detailed analysis with actionable recommendations.`,
  };
}

export function GRCCopilot() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = (text: string) => {
    if (!text.trim()) return;
    const userMsg: Message = { id: Date.now().toString(36) + 'u', role: 'user', content: text, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);
    setTimeout(() => {
      setMessages(prev => [...prev, generateResponse(text)]);
      setIsTyping(false);
    }, 800 + Math.random() * 600);
  };

  return (
    <div className="flex h-[calc(100vh-80px)] gap-4">
      {/* Main Chat */}
      <div className="flex-1 flex flex-col bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-slate-700 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
            <SparklesIcon className="h-4 w-4 text-white" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">GRC Copilot</h2>
            <p className="text-xs text-gray-500">Context-aware AI assistant for governance, risk & compliance</p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-indigo-500/20">
                <SparklesIcon className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">GRC Copilot</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto mb-8">
                Ask me anything about your GRC posture. I know your violations, users, roles, and risk data.
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-w-2xl mx-auto">
                {SUGGESTED_PROMPTS.map(p => (
                  <button key={p.text} onClick={() => send(p.text)}
                    className="text-left p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg border border-gray-200 dark:border-slate-600 hover:border-indigo-300 dark:hover:border-indigo-600 transition-colors">
                    <p.icon className={`h-4 w-4 ${p.color} mb-1.5`} />
                    <span className="text-xs text-gray-700 dark:text-gray-300">{p.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map(msg => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
              {msg.role === 'assistant' && (
                <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center mt-1">
                  <SparklesIcon className="h-3.5 w-3.5 text-white" />
                </div>
              )}
              <div className={`max-w-[75%] ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-2xl rounded-br-md px-4 py-3' : 'bg-gray-50 dark:bg-slate-700/50 rounded-2xl rounded-bl-md px-5 py-4'}`}>
                <div className={`text-sm leading-relaxed whitespace-pre-wrap ${msg.role === 'assistant' ? 'text-gray-800 dark:text-gray-200 prose prose-sm dark:prose-invert max-w-none' : ''}`}
                  dangerouslySetInnerHTML={msg.role === 'assistant' ? { __html: msg.content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br/>').replace(/\|/g, '<span class="text-gray-400">|</span>') } : undefined}>
                  {msg.role === 'user' ? msg.content : undefined}
                </div>
                {msg.dataCards && msg.dataCards.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {msg.dataCards.map((card, i) => (
                      <div key={i} className="bg-white dark:bg-slate-800 rounded-lg p-3 border border-gray-200 dark:border-slate-600">
                        <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">{card.title}</span>
                        {card.type === 'action' && (
                          <div className="mt-1">
                            <p className="text-xs text-gray-700 dark:text-gray-300">{String(card.data.action)}</p>
                            <button className="mt-1.5 text-xs bg-indigo-600 text-white px-3 py-1 rounded-md">Execute</button>
                          </div>
                        )}
                        {card.type === 'alert' && (
                          <div className="mt-1 flex items-center gap-2">
                            <ExclamationTriangleIcon className="h-4 w-4 text-amber-500" />
                            <span className="text-xs text-amber-700 dark:text-amber-400">{String(card.data.violation)} — {String(card.data.daysPastSLA)} days past SLA</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gray-200 dark:bg-slate-600 flex items-center justify-center mt-1">
                  <UserCircleIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                </div>
              )}
            </div>
          ))}

          {isTyping && (
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
                <SparklesIcon className="h-3.5 w-3.5 text-white" />
              </div>
              <div className="bg-gray-50 dark:bg-slate-700/50 rounded-2xl rounded-bl-md px-5 py-4">
                <div className="flex gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t border-gray-200 dark:border-slate-700">
          <div className="flex items-end gap-3">
            <textarea ref={inputRef} value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); } }}
              placeholder="Ask about risk, violations, users, compliance..."
              rows={1}
              className="flex-1 px-4 py-2.5 border border-gray-200 dark:border-slate-600 rounded-xl bg-gray-50 dark:bg-slate-700 text-gray-900 dark:text-white placeholder:text-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            <button onClick={() => send(input)} disabled={!input.trim()}
              className="p-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl disabled:opacity-50 transition-colors">
              <PaperAirplaneIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Context Panel */}
      <div className="hidden xl:block w-72 space-y-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
          <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Live Context</h3>
          <div className="space-y-3">
            {CONTEXT_METRICS.map(m => (
              <div key={m.label} className="flex items-center justify-between">
                <span className="text-xs text-gray-500 dark:text-gray-400">{m.label}</span>
                <div className="flex items-center gap-1.5">
                  <span className={`text-sm font-bold ${m.color}`}>{m.value}</span>
                  {m.trend !== '0' && (
                    <span className={`text-xs ${m.trend.startsWith('+') ? 'text-red-500' : 'text-emerald-500'}`}>{m.trend}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
          <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Quick Actions</h3>
          <div className="space-y-2">
            {[
              { label: 'Analyze User', icon: UserCircleIcon },
              { label: 'Check Risk', icon: ExclamationTriangleIcon },
              { label: 'Generate Report', icon: DocumentTextIcon },
              { label: 'Run Simulation', icon: ArrowPathIcon },
            ].map(a => (
              <button key={a.label} onClick={() => send(a.label)}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-slate-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors">
                <a.icon className="h-3.5 w-3.5 text-gray-400" /> {a.label}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-xl border border-indigo-200 dark:border-indigo-800 p-4">
          <SparklesIcon className="h-5 w-5 text-indigo-500 mb-2" />
          <p className="text-xs text-indigo-700 dark:text-indigo-400">
            GRC Copilot uses your tenant data to provide contextual answers. No data leaves your environment.
          </p>
        </div>
      </div>
    </div>
  );
}
