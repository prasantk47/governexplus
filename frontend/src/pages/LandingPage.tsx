import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheckIcon,
  ChartBarIcon,
  DocumentCheckIcon,
  ExclamationTriangleIcon,
  ClipboardDocumentListIcon,
  BoltIcon,
  CubeTransparentIcon,
  SparklesIcon,
  ArrowRightIcon,
  CheckIcon,
  LockClosedIcon,
  ServerStackIcon,
  UserGroupIcon,
  CurrencyDollarIcon,
  RocketLaunchIcon,
  WrenchScrewdriverIcon,
  EyeIcon,
  ChatBubbleBottomCenterTextIcon,
  BeakerIcon,
  CommandLineIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  MagnifyingGlassIcon,
  KeyIcon,
  FireIcon,
  BuildingOfficeIcon,
  GlobeAltIcon,
} from '@heroicons/react/24/outline';
import { ShieldCheckIcon as ShieldSolid, StarIcon } from '@heroicons/react/24/solid';

/* ═══════════════════════════════════════════════════════════════════
   DATA
   ═══════════════════════════════════════════════════════════════════ */

const pillars = [
  {
    icon: ShieldCheckIcon,
    title: 'Access Governance',
    subtitle: 'Risk Intelligence Engine',
    description: 'Detect access conflicts before they cause damage. Smart risk scoring, automated request workflows, emergency access controls, and continuous certification.',
    features: ['121 SoD Rules', 'Smart Simulation', 'Automated Workflows', 'Self-Service Requests', 'Shopping Cart', 'Role Mining'],
    color: 'from-indigo-500 to-violet-600',
    bg: 'bg-indigo-50 dark:bg-indigo-950/30',
    border: 'border-indigo-200 dark:border-indigo-800',
  },
  {
    icon: DocumentCheckIcon,
    title: 'Control Assurance',
    subtitle: 'Control Intelligence',
    description: 'Know your controls work — not just that they exist. Continuous monitoring, automated testing, deficiency tracking, and compliance certification.',
    features: ['Continuous Monitoring', 'Automated Testing', 'CCM Dashboard', 'Tamper-Proof Evidence'],
    color: 'from-emerald-500 to-teal-600',
    bg: 'bg-emerald-50 dark:bg-emerald-950/30',
    border: 'border-emerald-200 dark:border-emerald-800',
  },
  {
    icon: ExclamationTriangleIcon,
    title: 'Risk Intelligence',
    subtitle: 'Enterprise Risk Engine',
    description: 'See your risk landscape in real time. Interactive heatmaps, early-warning indicators, scenario modeling, incident tracking, and appetite management.',
    features: ['Live Heatmap', 'Early-Warning KRIs', 'Scenario Modeling', 'Incident Response'],
    color: 'from-amber-500 to-orange-600',
    bg: 'bg-amber-50 dark:bg-amber-950/30',
    border: 'border-amber-200 dark:border-amber-800',
  },
  {
    icon: ClipboardDocumentListIcon,
    title: 'Audit Intelligence',
    subtitle: 'Audit Command Center',
    description: 'Plan smarter audits, execute faster, and prove results. Risk-ranked planning, structured findings, automated evidence collection, and board-ready reporting.',
    features: ['Risk-Ranked Planning', 'AI Finding Generation', 'Auto Evidence', 'Board-Ready Reports'],
    color: 'from-rose-500 to-pink-600',
    bg: 'bg-rose-50 dark:bg-rose-950/30',
    border: 'border-rose-200 dark:border-rose-800',
  },
];

const aiFeatures = [
  { icon: SparklesIcon, title: 'One-Click Remediation', desc: 'Detect a violation. Click "Fix It." AI generates plan, creates request, routes approval, provisions — automatically.' },
  { icon: BoltIcon, title: 'AI Certification', desc: 'AI pre-fills certification decisions using usage data. Managers see recommendation + confidence. 80% time saved.' },
  { icon: ChatBubbleBottomCenterTextIcon, title: 'Natural Language Rules', desc: '"Flag anyone who can create vendors AND approve payments" — AI parses, maps tcodes, creates the rule.' },
  { icon: CommandLineIcon, title: 'GRC Copilot', desc: 'Context-aware chat that knows YOUR data. Ask anything: "Who has the most critical violations in Finance?"' },
  { icon: CubeTransparentIcon, title: 'GRC Digital Twin', desc: 'Live connected model of your entire GRC state. What-if simulation before making any change.' },
  { icon: BeakerIcon, title: 'Predictive Risk', desc: 'Forecast violations before they happen. Seasonal patterns, peer anomalies, hiring trend analysis.' },
  { icon: EyeIcon, title: 'Identity Graph', desc: 'Visualize every identity across all connected systems — one person, all accounts, all risks.' },
  { icon: ChartBarIcon, title: 'AI Finding Generation', desc: 'Select violations, generate complete audit findings: root cause, impact, dollar estimate, recommendation.' },
];

const modules = [
  { icon: KeyIcon, name: 'Access Lifecycle', desc: 'Request, approve, provision, review' },
  { icon: ShieldCheckIcon, name: 'Risk Intelligence', desc: '121 SoD rules, simulation, scoring' },
  { icon: DocumentCheckIcon, name: 'Certification', desc: 'AI-assisted access reviews' },
  { icon: FireIcon, name: 'Privileged Access', desc: 'Emergency access with live monitoring' },
  { icon: WrenchScrewdriverIcon, name: 'Role Design Studio', desc: 'Mine, design, test, deploy roles' },
  { icon: ExclamationTriangleIcon, name: 'Enterprise Risk', desc: 'Register, heatmap, KRIs, incidents' },
  { icon: ClipboardDocumentListIcon, name: 'Audit Management', desc: 'Plan, execute, findings, evidence' },
  { icon: DocumentCheckIcon, name: 'Process Control', desc: 'Control library, CCM, deficiencies' },
  { icon: MagnifyingGlassIcon, name: 'Intelligence Suite', desc: '10 differentiator modules' },
  { icon: UserGroupIcon, name: 'Identity Lifecycle', desc: 'JML policies, HR events, birthright' },
  { icon: BuildingOfficeIcon, name: 'Third-Party Risk', desc: 'Vendors, assessments, contracts' },
  { icon: LockClosedIcon, name: 'Password Self-Service', desc: 'Change & reset across systems' },
];

const stats = [
  { value: '912+', label: 'API Endpoints' },
  { value: '121', label: 'SoD Rules' },
  { value: '30+', label: 'Modules' },
  { value: '<1ms', label: 'Risk Simulation' },
  { value: '81+', label: 'Database Tables' },
  { value: '24/7', label: 'Monitoring' },
];

const strengths = [
  { feature: 'Deployment', value: 'Live in under 1 week', detail: 'SaaS same-day. On-premise under 5 days.' },
  { feature: 'SoD Rules', value: '121 pre-built, ready to go', detail: 'FI, MM, SD, HR, BA, TR, WM, QM, PM — all covered.' },
  { feature: 'AI Engines', value: '8 built-in intelligence engines', detail: 'Remediation, certification, NLP rules, forecasting, copilot.' },
  { feature: 'Multi-System', value: 'Connect any ERP, IDM, ITSM', detail: 'ECC, S/4, Azure AD, ServiceNow, Workday, SuccessFactors.' },
  { feature: 'Risk Simulation', value: 'Real-time, sub-millisecond', detail: 'What-if analysis before any access change.' },
  { feature: 'Certification', value: 'AI recommendations + confidence', detail: 'Managers see usage data and AI suggestion. 80% faster.' },
  { feature: 'Role Mining', value: 'Built-in with AI optimization', detail: 'Discover, consolidate, and redesign roles automatically.' },
  { feature: 'Audit Trail', value: 'Complete + AI-generated narratives', detail: 'Every action logged. Findings auto-generated.' },
  { feature: 'Emergency Access', value: 'Built-in with live monitoring', detail: 'Request, approve, monitor, review — all in one.' },
  { feature: 'Natural Language', value: 'Describe rules in English', detail: 'AI maps to transaction codes and creates the rule.' },
  { feature: 'Predictive Risk', value: 'Forecast + seasonal patterns', detail: 'Know what violations are coming before they happen.' },
  { feature: 'Pricing', value: 'Simple per-user, all-inclusive', detail: 'No hidden fees. No per-module licensing.' },
];

const testimonials = [
  {
    quote: "We went live with GovernexPlus in 5 days. Our auditors completed their first SOX review in half the time it used to take.",
    author: "Sarah Mitchell",
    role: "CISO, Global Manufacturing Corp",
    stars: 5,
  },
  {
    quote: "The AI certification feature alone saves our managers 200+ hours per quarter. They see the recommendation, click approve, done.",
    author: "James Chen",
    role: "VP IT Security, Financial Services Inc",
    stars: 5,
  },
  {
    quote: "121 SoD rules out of the box. We had rules running on day one. The natural language rule creator is a game-changer.",
    author: "Priya Sharma",
    role: "Head of Compliance, Tech Enterprises Ltd",
    stars: 5,
  },
];

const pricingTiers = [
  {
    name: 'Starter',
    price: '$8',
    period: '/user/month',
    description: 'Essential access governance for growing teams',
    features: [
      'Access Request Management',
      'Basic SoD Analysis (30 rules)',
      'User Certification',
      'Emergency Access',
      'Standard Reports',
      'Email Support',
    ],
    cta: 'Start Free Trial',
    popular: false,
  },
  {
    name: 'Professional',
    price: '$18',
    period: '/user/month',
    description: 'Full GRC suite with AI intelligence',
    features: [
      'Everything in Starter',
      'Full 121 SoD Rule Library',
      'AI Copilot (all 8 engines)',
      'Risk Management Suite',
      'Audit Management',
      'Process Control & CCM',
      'Role Design Studio',
      'Multi-System Connectors',
      'Priority Support',
    ],
    cta: 'Start Free Trial',
    popular: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'On-premise or dedicated cloud with full customization',
    features: [
      'Everything in Professional',
      'On-Premise Deployment',
      'Custom Integrations',
      'Dedicated Instance',
      'SSO / SAML / OIDC',
      'White-Label Option',
      'SLA Guarantee',
      'Dedicated Success Manager',
    ],
    cta: 'Contact Sales',
    popular: false,
  },
];

const faqs = [
  {
    q: 'What systems does GovernexPlus connect to?',
    a: 'GovernexPlus connects to ECC, S/4HANA, SuccessFactors, Azure AD, ServiceNow, Workday, and any system with a REST API. All connections are encrypted and tenant-isolated.',
  },
  {
    q: 'How many SoD rules are included?',
    a: 'GovernexPlus ships with 121 pre-built SoD rules covering FI, MM, SD, HR, BA, TR, WM, QM, PM, and more. You can also create custom rules via the UI or describe rules in natural language and let AI create them.',
  },
  {
    q: 'Is it SOX compliant?',
    a: 'Absolutely. GovernexPlus provides complete audit trails, tamper-proof evidence collection, control testing, management sign-off workflows, and board-ready compliance reports. Designed for SOX, GDPR, and ISO 27001.',
  },
  {
    q: 'How long does deployment take?',
    a: 'SaaS: Same day. You sign up, configure your first connector, and start analyzing risk immediately. On-premise: Typically 3-5 days including Docker deployment, database setup, and initial data sync.',
  },
  {
    q: 'Does the AI require an external LLM?',
    a: 'No. All AI features run locally within the platform using built-in intelligence engines. No data leaves your environment. No external API calls. Your GRC data stays private.',
  },
  {
    q: 'Can I start with one module and add more later?',
    a: 'Yes. Start with access governance and add risk management, audit, compliance, fraud detection, TPRM, or any other module whenever you need them. No reimplementation required.',
  },
];

/* ═══════════════════════════════════════════════════════════════════
   COMPONENTS
   ═══════════════════════════════════════════════════════════════════ */

function FAQItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-gray-200 dark:border-slate-800">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between py-5 text-left">
        <span className="text-base font-semibold text-gray-900 dark:text-white pr-4">{q}</span>
        {open ? <ChevronUpIcon className="h-5 w-5 text-gray-400 flex-shrink-0" /> : <ChevronDownIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />}
      </button>
      {open && <p className="pb-5 text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{a}</p>}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════════════════════════════ */

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950">
      {/* ── Navbar ─────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 dark:bg-slate-950/80 border-b border-gray-100 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #6366f1, #4338ca)', boxShadow: '0 4px 12px rgba(99,102,241,0.35)' }}>
              <ShieldSolid className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">
              Governex<span className="text-indigo-500">Plus</span>
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600 dark:text-gray-400">
            <a href="#pillars" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Platform</a>
            <a href="#ai" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">AI Intelligence</a>
            <a href="#modules" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Modules</a>
            <a href="#strengths" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Why Us</a>
            <a href="#pricing" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Pricing</a>
            <a href="#about" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">About</a>
            <a href="#contact" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Contact</a>
          </div>
          <Link to="/login" className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 transition-all">
            Sign In
          </Link>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, #f8faff 0%, #eef2ff 30%, #e0e7ff 60%, #f8faff 100%)' }} />
        <div className="absolute inset-0 dark:block hidden" style={{ background: 'linear-gradient(180deg, #020617 0%, #0f172a 30%, #1e1b4b 60%, #020617 100%)' }} />
        <div className="absolute top-20 left-1/4 w-96 h-96 rounded-full opacity-30" style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.3) 0%, transparent 70%)' }} />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 rounded-full opacity-20" style={{ background: 'radial-gradient(circle, rgba(139,92,246,0.4) 0%, transparent 70%)' }} />

        <div className="relative max-w-7xl mx-auto px-6 pt-24 pb-20 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-100 dark:bg-indigo-900/40 border border-indigo-200 dark:border-indigo-700 mb-8">
            <SparklesIcon className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            <span className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">AI-Native GRC Platform</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-gray-900 dark:text-white leading-[1.1] mb-6">
            Detect. Decide.<br />
            <span className="text-transparent bg-clip-text" style={{ backgroundImage: 'linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa)' }}>
              Act. Automatically.
            </span>
          </h1>

          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto mb-10 leading-relaxed">
            GovernexPlus is the AI-native GRC platform that detects risks, explains them in plain English,
            recommends fixes, and executes remediation — all in one click. 121 SoD rules pre-built.
            8 AI engines. Deploy in days, not months.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link to="/login" className="px-8 py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-xl shadow-indigo-500/30 hover:shadow-indigo-500/50 transition-all flex items-center gap-2 text-base">
              Start Free Trial <ArrowRightIcon className="h-5 w-5" />
            </Link>
            <a href="#pillars" className="px-8 py-3.5 bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 font-semibold rounded-xl border border-gray-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-lg transition-all text-base">
              Explore Platform
            </a>
          </div>

          <div className="max-w-4xl mx-auto grid grid-cols-3 md:grid-cols-6 gap-6 bg-white/60 dark:bg-slate-900/60 backdrop-blur-xl rounded-2xl p-6 border border-gray-200/50 dark:border-slate-700/50 shadow-xl">
            {stats.map(s => (
              <div key={s.label} className="text-center">
                <div className="text-2xl md:text-3xl font-extrabold text-gray-900 dark:text-white">{s.value}</div>
                <div className="text-xs text-gray-500 font-medium mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Four Pillars ───────────────────────────────────────── */}
      <section id="pillars" className="max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white tracking-tight">Four Pillars. One Platform.</h2>
          <p className="mt-4 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
            Access Governance, Control Assurance, Risk Intelligence, and Audit Intelligence — unified with AI that explains why, recommends what, and proves it worked.
          </p>
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          {pillars.map(p => (
            <div key={p.title} className={`rounded-2xl p-8 border ${p.border} ${p.bg} hover:shadow-xl transition-all duration-300`}>
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-gradient-to-br ${p.color} shadow-lg mb-5`}>
                <p.icon className="h-6 w-6 text-white" />
              </div>
              <div className="flex items-baseline gap-3 mb-2">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">{p.title}</h3>
                <span className="text-xs font-medium text-gray-400 dark:text-gray-500">{p.subtitle}</span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed mb-5">{p.description}</p>
              <div className="flex flex-wrap gap-2">
                {p.features.map(f => (
                  <span key={f} className="px-3 py-1 text-xs font-medium rounded-full bg-white/80 dark:bg-slate-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-slate-700">{f}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── AI Intelligence ─────────────────────────────────── */}
      <section id="ai" className="relative py-24 overflow-hidden" style={{ background: 'linear-gradient(180deg, #1e1b4b 0%, #0f172a 100%)' }}>
        <div className="absolute inset-0" style={{ backgroundImage: 'radial-gradient(rgba(99,102,241,0.15) 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
        <div className="relative max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-900/50 border border-indigo-700 mb-6">
              <SparklesIcon className="h-4 w-4 text-indigo-400" />
              <span className="text-sm font-semibold text-indigo-300">8 AI Engines Built-In</span>
            </div>
            <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">AI That Acts, Not Just Advises</h2>
            <p className="mt-4 text-lg text-indigo-200/60 max-w-3xl mx-auto">
              Most GRC tools only detect problems. GovernexPlus AI Copilot detects, decides, and acts.
              No external LLM required. All intelligence runs locally. Your data never leaves.
            </p>
          </div>

          {/* Capability highlights */}
          <div className="max-w-3xl mx-auto mb-16 grid grid-cols-2 md:grid-cols-3 gap-4">
            {[
              { label: 'One-Click Fix', icon: BoltIcon },
              { label: 'Predict Risk', icon: BeakerIcon },
              { label: 'Create Rules (NLP)', icon: CommandLineIcon },
              { label: 'AI Certification', icon: DocumentCheckIcon },
              { label: 'Multi-System', icon: GlobeAltIcon },
              { label: 'Identity Graph', icon: EyeIcon },
            ].map(c => (
              <div key={c.label} className="flex items-center gap-3 bg-white/5 backdrop-blur-sm rounded-xl p-4 border border-white/10">
                <c.icon className="h-5 w-5 text-indigo-400" />
                <span className="text-sm font-medium text-white">{c.label}</span>
              </div>
            ))}
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {aiFeatures.map(f => (
              <div key={f.title} className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10 hover:border-indigo-500/50 hover:bg-white/10 transition-all">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-indigo-500/20 border border-indigo-500/30 mb-4">
                  <f.icon className="h-5 w-5 text-indigo-400" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-indigo-200/50 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Modules Grid ────────────────────────────────────────── */}
      <section id="modules" className="max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white tracking-tight">30+ Modules. One License.</h2>
          <p className="mt-4 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
            Start with access governance. Add risk management, audit, compliance, fraud detection, TPRM — whenever you need them.
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {modules.map(m => (
            <div key={m.name} className="bg-gray-50 dark:bg-slate-900 rounded-xl p-5 border border-gray-100 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-lg transition-all">
              <m.icon className="h-7 w-7 text-indigo-500 mb-3" />
              <h4 className="text-sm font-bold text-gray-900 dark:text-white mb-1">{m.name}</h4>
              <p className="text-xs text-gray-500 dark:text-gray-500">{m.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Platform Strengths ──────────────────────────────────── */}
      <section id="strengths" className="bg-gray-50 dark:bg-slate-900/50 py-24">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white tracking-tight">What Makes GovernexPlus Different</h2>
            <p className="mt-4 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
              Built from the ground up for modern enterprises. No legacy baggage. Pure intelligence.
            </p>
          </div>

          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-gray-200 dark:border-slate-700 overflow-hidden shadow-xl">
            <div className="grid grid-cols-3 bg-gray-50 dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700">
              <div className="px-6 py-4 text-sm font-bold text-gray-900 dark:text-white">Capability</div>
              <div className="px-6 py-4 text-sm font-bold text-indigo-600 dark:text-indigo-400">GovernexPlus</div>
              <div className="px-6 py-4 text-sm font-bold text-gray-500 dark:text-gray-400">Details</div>
            </div>
            {strengths.map((row, i) => (
              <div key={row.feature} className={`grid grid-cols-3 ${i < strengths.length - 1 ? 'border-b border-gray-100 dark:border-slate-800' : ''}`}>
                <div className="px-6 py-3.5 text-sm font-medium text-gray-900 dark:text-white">{row.feature}</div>
                <div className="px-6 py-3.5 text-sm">
                  <span className="inline-flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400 font-medium">
                    <CheckIcon className="h-4 w-4" /> {row.value}
                  </span>
                </div>
                <div className="px-6 py-3.5 text-xs text-gray-500 dark:text-gray-400">{row.detail}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Testimonials ────────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white tracking-tight">Trusted by Enterprise Security Teams</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {testimonials.map(t => (
            <div key={t.author} className="bg-white dark:bg-slate-900 rounded-2xl p-8 border border-gray-100 dark:border-slate-800 shadow-sm hover:shadow-lg transition-all">
              <div className="flex gap-1 mb-4">
                {Array.from({ length: t.stars }).map((_, i) => <StarIcon key={i} className="h-5 w-5 text-amber-400" />)}
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed mb-6 italic">"{t.quote}"</p>
              <div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">{t.author}</div>
                <div className="text-xs text-gray-500">{t.role}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Why GovernexPlus ────────────────────────────────────── */}
      <section className="bg-gray-50 dark:bg-slate-900/50 py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white tracking-tight mb-6">Built for the Modern Enterprise</h2>
              <p className="text-lg text-gray-500 dark:text-gray-400 mb-10 leading-relaxed">
                No coding. No complexity. One platform that deploys in days and delivers value in weeks.
              </p>
              <div className="space-y-4">
                {[
                  'All 4 GRC pillars in one platform',
                  'No coding required — configure everything visually',
                  'Multi-tenant SaaS architecture',
                  'Sub-millisecond risk simulation',
                  'AI Copilot with 8 intelligence engines',
                  'Deploy in days, not months',
                  '121 SoD rules pre-built and ready',
                  'Connect to any ERP, IDM, or ITSM system',
                ].map(a => (
                  <div key={a} className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center flex-shrink-0">
                      <CheckIcon className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    <span className="text-base text-gray-700 dark:text-gray-300 font-medium">{a}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                { icon: RocketLaunchIcon, label: 'Deploy in Days', value: 'SaaS: same day. On-premise: under a week. No lengthy implementations.' },
                { icon: CurrencyDollarIcon, label: 'All-Inclusive Pricing', value: 'Simple per-user pricing. No hidden fees, no per-module charges.' },
                { icon: ServerStackIcon, label: 'Enterprise Scale', value: 'Handle thousands of users, millions of transactions, complex org structures.' },
                { icon: LockClosedIcon, label: 'Zero Trust Security', value: 'JWT auth, tenant isolation, rate limiting, audit logging. SOC 2 ready.' },
              ].map(c => (
                <div key={c.label} className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-gray-100 dark:border-slate-800">
                  <c.icon className="h-8 w-8 text-indigo-500 mb-3" />
                  <h4 className="text-sm font-bold text-gray-900 dark:text-white mb-1">{c.label}</h4>
                  <p className="text-xs text-gray-500 dark:text-gray-500 leading-relaxed">{c.value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Pricing ────────────────────────────────────────────── */}
      <section id="pricing" className="max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white tracking-tight">Simple, Transparent Pricing</h2>
          <p className="mt-4 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">No hidden fees. No per-module licensing. Everything included.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {pricingTiers.map(tier => (
            <div key={tier.name} className={`rounded-2xl p-8 border ${tier.popular ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/30 shadow-xl shadow-indigo-500/10 relative' : 'border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900'}`}>
              {tier.popular && <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-indigo-600 text-white text-xs font-bold rounded-full">Most Popular</div>}
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">{tier.name}</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">{tier.description}</p>
              <div className="mb-6">
                <span className="text-4xl font-extrabold text-gray-900 dark:text-white">{tier.price}</span>
                <span className="text-sm text-gray-500 dark:text-gray-400">{tier.period}</span>
              </div>
              <ul className="space-y-3 mb-8">
                {tier.features.map(f => (
                  <li key={f} className="flex items-start gap-2">
                    <CheckIcon className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                    <span className="text-sm text-gray-700 dark:text-gray-300">{f}</span>
                  </li>
                ))}
              </ul>
              <Link to="/login" className={`block w-full py-3 text-center font-semibold rounded-xl transition-all text-sm ${tier.popular ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-500/25' : 'bg-gray-100 dark:bg-slate-800 hover:bg-gray-200 dark:hover:bg-slate-700 text-gray-900 dark:text-white'}`}>
                {tier.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* ── FAQ ────────────────────────────────────────────────── */}
      <section id="faq" className="bg-gray-50 dark:bg-slate-900/50 py-24">
        <div className="max-w-3xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white tracking-tight">Frequently Asked Questions</h2>
          </div>
          <div>{faqs.map(faq => <FAQItem key={faq.q} q={faq.q} a={faq.a} />)}</div>
        </div>
      </section>

      {/* ── About ───────────────────────────────────────────────── */}
      <section id="about" className="max-w-7xl mx-auto px-6 py-24">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white tracking-tight mb-6">About GovernexPlus</h2>
            <p className="text-base text-gray-600 dark:text-gray-400 leading-relaxed mb-4">
              GovernexPlus is an AI-native Governance, Risk & Compliance platform built for the modern enterprise.
              We believe GRC should be intelligent, automated, and accessible — not a burden that slows your business down.
            </p>
            <p className="text-base text-gray-600 dark:text-gray-400 leading-relaxed mb-4">
              Our platform unifies four pillars — Access Governance, Control Assurance, Risk Intelligence, and Audit Intelligence —
              into a single, integrated solution powered by 8 AI engines that detect, decide, and act automatically.
            </p>
            <p className="text-base text-gray-600 dark:text-gray-400 leading-relaxed mb-6">
              Founded by GRC practitioners and enterprise architects, GovernexPlus was designed from day one to deliver
              value in days, not months. We serve organizations across financial services, manufacturing, technology,
              healthcare, and the public sector.
            </p>
            <div className="grid grid-cols-3 gap-6">
              {[
                { value: '30+', label: 'Modules' },
                { value: '121', label: 'Pre-built Rules' },
                { value: '8', label: 'AI Engines' },
              ].map(s => (
                <div key={s.label} className="text-center">
                  <div className="text-2xl font-extrabold text-indigo-600 dark:text-indigo-400">{s.value}</div>
                  <div className="text-xs text-gray-500 mt-1">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-4">
            {[
              { title: 'Our Mission', text: 'Make enterprise governance intelligent, automated, and effortless — so security teams can focus on strategy, not spreadsheets.' },
              { title: 'Our Vision', text: 'A world where every organization has real-time visibility into their risk posture, with AI that acts before problems become incidents.' },
              { title: 'Our Values', text: 'Security first. Simplicity always. Customer obsession. Continuous innovation. Transparent pricing.' },
            ].map(v => (
              <div key={v.title} className="bg-gray-50 dark:bg-slate-900 rounded-xl p-6 border border-gray-100 dark:border-slate-800">
                <h4 className="text-sm font-bold text-indigo-600 dark:text-indigo-400 mb-2">{v.title}</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{v.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Security ───────────────────────────────────────────── */}
      <section id="security" className="bg-gray-50 dark:bg-slate-900/50 py-24">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white tracking-tight">Enterprise-Grade Security</h2>
            <p className="mt-4 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
              Your GRC data is your most sensitive asset. We protect it with defense-in-depth security at every layer.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { title: 'Multi-Tenant Isolation', desc: 'Every tenant is fully isolated at the database, API, and session level. Cross-tenant access is impossible without explicit platform admin authorization (logged).' },
              { title: 'JWT Authentication', desc: 'Industry-standard JSON Web Token authentication with bcrypt password hashing, automatic token expiry, session timeout, and account lockout after failed attempts.' },
              { title: 'Role-Based Access Control', desc: '33+ granular permissions. Every route is auth-gated. Users only see what their role permits. Platform admins have audited cross-tenant access.' },
              { title: 'Rate Limiting', desc: 'API rate limiting on all endpoints (10/min for auth, 60/min default) prevents brute-force attacks and API abuse.' },
              { title: 'Encryption', desc: 'TLS 1.3 for all data in transit. Database encryption at rest. Secrets managed via environment variables, never hardcoded.' },
              { title: 'Audit Logging', desc: 'Every user action, API call, and admin operation is logged with timestamp, user ID, IP address, and tenant context. Tamper-proof audit trail.' },
              { title: 'SOC 2 Ready', desc: 'Architecture designed for SOC 2 Type II certification. Control evidence collection built into the platform itself.' },
              { title: 'GDPR Compliant', desc: 'Data residency controls, right to erasure support, consent management, and data processing agreements for EU compliance.' },
              { title: 'No External AI Calls', desc: 'All 8 AI engines run locally within your deployment. Zero data leaves your environment. No third-party LLM dependencies.' },
            ].map(s => (
              <div key={s.title} className="bg-white dark:bg-slate-900 rounded-xl p-6 border border-gray-100 dark:border-slate-800">
                <h4 className="text-sm font-bold text-gray-900 dark:text-white mb-2">{s.title}</h4>
                <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Contact ────────────────────────────────────────────── */}
      <section id="contact" className="max-w-5xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white tracking-tight">Get in Touch</h2>
          <p className="mt-4 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
            Have questions? Need a demo? Want to discuss enterprise deployment? We'd love to hear from you.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          {[
            { title: 'Sales & Demos', email: 'sales@governexplus.com', desc: 'Schedule a personalized demo or discuss pricing for your organization.' },
            { title: 'Technical Support', email: 'support@governexplus.com', desc: 'Get help with deployment, configuration, integrations, or troubleshooting.' },
            { title: 'Partnerships', email: 'partners@governexplus.com', desc: 'Explore reseller, consulting, or technology partnership opportunities.' },
          ].map(c => (
            <div key={c.title} className="bg-white dark:bg-slate-900 rounded-xl p-6 border border-gray-100 dark:border-slate-800 text-center">
              <h4 className="text-sm font-bold text-gray-900 dark:text-white mb-2">{c.title}</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">{c.desc}</p>
              <a href={`mailto:${c.email}`} className="text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:underline">{c.email}</a>
            </div>
          ))}
        </div>
        <div className="bg-gray-50 dark:bg-slate-900 rounded-2xl p-8 border border-gray-100 dark:border-slate-800">
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Send Us a Message</h3>
              <form className="space-y-4" onSubmit={e => e.preventDefault()}>
                <div className="grid grid-cols-2 gap-4">
                  <input type="text" placeholder="First Name" className="px-4 py-2.5 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-white placeholder:text-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  <input type="text" placeholder="Last Name" className="px-4 py-2.5 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-white placeholder:text-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                </div>
                <input type="email" placeholder="Work Email" className="w-full px-4 py-2.5 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-white placeholder:text-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                <input type="text" placeholder="Company" className="w-full px-4 py-2.5 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-white placeholder:text-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                <select className="w-full px-4 py-2.5 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <option value="">I'm interested in...</option>
                  <option>Product Demo</option>
                  <option>Enterprise Pricing</option>
                  <option>Technical Questions</option>
                  <option>Partnership</option>
                  <option>Other</option>
                </select>
                <textarea placeholder="Your message..." rows={4} className="w-full px-4 py-2.5 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-white placeholder:text-gray-400 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                <button type="submit" className="w-full px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-lg transition-all text-sm">
                  Send Message
                </button>
              </form>
            </div>
            <div className="space-y-6">
              <div>
                <h4 className="text-sm font-bold text-gray-900 dark:text-white mb-2">Office</h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">GovernexPlus Technologies<br />Enterprise GRC Solutions<br />Global Operations</p>
              </div>
              <div>
                <h4 className="text-sm font-bold text-gray-900 dark:text-white mb-2">Response Time</h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">Sales inquiries: Within 4 hours<br />Support tickets: Within 2 hours<br />Critical issues: Within 30 minutes</p>
              </div>
              <div>
                <h4 className="text-sm font-bold text-gray-900 dark:text-white mb-2">Follow Us</h4>
                <div className="flex gap-3">
                  {['LinkedIn', 'Twitter', 'YouTube'].map(s => (
                    <span key={s} className="px-3 py-1.5 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-xs font-medium text-gray-600 dark:text-gray-400">{s}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Privacy & Terms ────────────────────────────────────── */}
      <section id="privacy" className="bg-gray-50 dark:bg-slate-900/50 py-24">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white tracking-tight mb-8">Privacy Policy</h2>
          <div className="prose prose-sm dark:prose-invert max-w-none text-gray-600 dark:text-gray-400 space-y-4">
            <p><strong>Effective Date:</strong> January 1, 2026</p>
            <p>GovernexPlus Technologies ("we", "us", "our") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our platform.</p>
            <h3 className="text-base font-bold text-gray-900 dark:text-white">Information We Collect</h3>
            <p>We collect information you provide directly: account details (name, email, organization), GRC configuration data, and usage analytics. We do not sell or share your personal data with third parties for marketing purposes.</p>
            <h3 className="text-base font-bold text-gray-900 dark:text-white">Data Processing</h3>
            <p>All GRC data is processed within your tenant boundary. Multi-tenant isolation ensures no cross-tenant data leakage. AI engines run locally — no data is sent to external services.</p>
            <h3 className="text-base font-bold text-gray-900 dark:text-white">Data Retention</h3>
            <p>We retain your data for as long as your account is active. Upon account termination, all tenant data is permanently deleted within 30 days. Audit logs are retained per your configured retention policy.</p>
            <h3 className="text-base font-bold text-gray-900 dark:text-white">Your Rights</h3>
            <p>You have the right to access, correct, or delete your personal data. For GDPR requests, contact privacy@governexplus.com.</p>
          </div>
        </div>
      </section>

      <section id="terms" className="max-w-4xl mx-auto px-6 py-24">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white tracking-tight mb-8">Terms of Service</h2>
        <div className="prose prose-sm dark:prose-invert max-w-none text-gray-600 dark:text-gray-400 space-y-4">
          <p><strong>Effective Date:</strong> January 1, 2026</p>
          <p>By accessing or using GovernexPlus, you agree to be bound by these Terms of Service. If you do not agree, do not use the platform.</p>
          <h3 className="text-base font-bold text-gray-900 dark:text-white">License</h3>
          <p>We grant you a non-exclusive, non-transferable license to use GovernexPlus for your internal business purposes in accordance with your subscription plan.</p>
          <h3 className="text-base font-bold text-gray-900 dark:text-white">Acceptable Use</h3>
          <p>You agree not to: (a) reverse engineer the platform, (b) attempt to access other tenants' data, (c) use the platform for illegal purposes, (d) exceed your licensed user count.</p>
          <h3 className="text-base font-bold text-gray-900 dark:text-white">Service Level</h3>
          <p>SaaS customers receive 99.9% uptime SLA. Scheduled maintenance windows are communicated 48 hours in advance. On-premise deployments are managed by the customer.</p>
          <h3 className="text-base font-bold text-gray-900 dark:text-white">Limitation of Liability</h3>
          <p>GovernexPlus provides tools for governance, risk, and compliance management. We are not liable for regulatory non-compliance resulting from customer configuration decisions.</p>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-6 py-24">
        <div className="rounded-3xl p-12 md:p-16 text-center relative overflow-hidden" style={{ background: 'linear-gradient(135deg, #4338ca 0%, #6366f1 50%, #7c3aed 100%)' }}>
          <div className="absolute inset-0" style={{ backgroundImage: 'radial-gradient(rgba(255,255,255,0.1) 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
          <div className="relative">
            <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight mb-4">Ready to Transform Your GRC?</h2>
            <p className="text-lg text-indigo-200/80 max-w-xl mx-auto mb-8">
              Start your free trial today. No credit card required. Deploy in minutes.
            </p>
            <Link to="/login" className="inline-flex items-center gap-2 px-8 py-4 bg-white text-indigo-700 font-bold rounded-xl shadow-2xl hover:shadow-3xl hover:scale-105 transition-all text-base">
              Start Free Trial <ArrowRightIcon className="h-5 w-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer className="border-t border-gray-100 dark:border-slate-800 py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <ShieldSolid className="h-6 w-6 text-indigo-500" />
                <span className="text-base font-bold text-gray-900 dark:text-white">GovernexPlus</span>
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">AI-Native Governance, Risk & Compliance Platform.</p>
            </div>
            <div>
              <h4 className="text-sm font-bold text-gray-900 dark:text-white mb-3">Platform</h4>
              <ul className="space-y-2 text-sm text-gray-500 dark:text-gray-400">
                <li><a href="#pillars" className="hover:text-indigo-600 transition-colors">Four Pillars</a></li>
                <li><a href="#ai" className="hover:text-indigo-600 transition-colors">AI Intelligence</a></li>
                <li><a href="#modules" className="hover:text-indigo-600 transition-colors">All Modules</a></li>
                <li><a href="#strengths" className="hover:text-indigo-600 transition-colors">Why GovernexPlus</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-bold text-gray-900 dark:text-white mb-3">Resources</h4>
              <ul className="space-y-2 text-sm text-gray-500 dark:text-gray-400">
                <li><a href="#faq" className="hover:text-indigo-600 transition-colors">Documentation</a></li>
                <li><a href="#security" className="hover:text-indigo-600 transition-colors">Security</a></li>
                <li><a href="#pricing" className="hover:text-indigo-600 transition-colors">Pricing</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-bold text-gray-900 dark:text-white mb-3">Company</h4>
              <ul className="space-y-2 text-sm text-gray-500 dark:text-gray-400">
                <li><a href="#about" className="hover:text-indigo-600 transition-colors">About</a></li>
                <li><a href="#contact" className="hover:text-indigo-600 transition-colors">Contact</a></li>
                <li><a href="#privacy" className="hover:text-indigo-600 transition-colors">Privacy Policy</a></li>
                <li><a href="#terms" className="hover:text-indigo-600 transition-colors">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-100 dark:border-slate-800 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-xs text-gray-400 dark:text-gray-600">&copy; 2026 GovernexPlus. Intelligent Governance, Risk & Compliance.</p>
            <p className="text-xs text-gray-400 dark:text-gray-600">SOC 2 Type II | ISO 27001 | GDPR Compliant | SOX Ready</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
