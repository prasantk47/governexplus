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
  GlobeAltIcon,
  LockClosedIcon,
  ServerStackIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';
import { ShieldCheckIcon as ShieldSolid } from '@heroicons/react/24/solid';

const pillars = [
  {
    icon: ShieldCheckIcon,
    title: 'Access Governance',
    subtitle: 'Risk Intelligence Engine',
    description: 'Detect access conflicts before they cause damage. Smart risk scoring, automated request workflows, emergency access controls, and continuous certification.',
    features: ['Conflict Detection', 'Smart Simulation', 'Automated Workflows', 'Self-Service Requests'],
    color: 'from-indigo-500 to-violet-600',
    bg: 'bg-indigo-50 dark:bg-indigo-950/30',
    border: 'border-indigo-200 dark:border-indigo-800',
  },
  {
    icon: DocumentCheckIcon,
    title: 'Control Assurance',
    subtitle: 'Control Intelligence',
    description: 'Know your controls work — not just that they exist. Continuous monitoring, automated testing, deficiency tracking, and compliance certification.',
    features: ['Continuous Monitoring', 'Automated Testing', 'Compliance Certification', 'Tamper-Proof Evidence'],
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
    features: ['Risk-Ranked Planning', 'Structured Findings', 'Auto Evidence Collection', 'Board-Ready Reports'],
    color: 'from-rose-500 to-pink-600',
    bg: 'bg-rose-50 dark:bg-rose-950/30',
    border: 'border-rose-200 dark:border-rose-800',
  },
];

const aiFeatures = [
  { icon: SparklesIcon, title: 'GRC Health Score', desc: 'Real-time composite health across all four pillars with trend analysis' },
  { icon: BoltIcon, title: 'AI Explain & Investigate', desc: 'Ask "why is this risky?" and get plain-English explanations with evidence' },
  { icon: CubeTransparentIcon, title: 'GRC Digital Twin', desc: 'Live connected model of your entire GRC state with what-if simulation' },
  { icon: ChartBarIcon, title: 'Role Redesign Copilot', desc: 'AI-driven role optimization, duplicate detection, and consolidation proposals' },
];

const stats = [
  { value: '4', label: 'GRC Pillars' },
  { value: '128+', label: 'Risk Rules' },
  { value: '183', label: 'Features Built' },
  { value: '<1ms', label: 'Risk Simulation' },
  { value: '100%', label: 'Compliance Ready' },
  { value: '24/7', label: 'Monitoring' },
];

const advantages = [
  'All 4 GRC pillars in one platform',
  'No coding required — configure everything visually',
  'Multi-tenant SaaS architecture',
  'Sub-millisecond risk simulation',
  'AI-native intelligence layer',
  'Deploy in days, not months',
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950">
      {/* ── Navbar ──────────────────────────────────── */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 dark:bg-slate-950/80 border-b border-gray-100 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #6366f1, #4338ca)', boxShadow: '0 4px 12px rgba(99,102,241,0.35)' }}
            >
              <ShieldSolid className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">
              Governex<span className="text-indigo-500">+</span>
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600 dark:text-gray-400">
            <a href="#pillars" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Modules</a>
            <a href="#ai" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">AI Intelligence</a>
            <a href="#why" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Why Governex+</a>
          </div>
          <Link
            to="/login"
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 transition-all"
          >
            Sign In
          </Link>
        </div>
      </nav>

      {/* ── Hero ──────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0"
          style={{
            background: 'linear-gradient(180deg, #f8faff 0%, #eef2ff 30%, #e0e7ff 60%, #f8faff 100%)',
          }}
        />
        <div className="absolute inset-0 dark:block hidden"
          style={{
            background: 'linear-gradient(180deg, #020617 0%, #0f172a 30%, #1e1b4b 60%, #020617 100%)',
          }}
        />
        <div className="absolute top-20 left-1/4 w-96 h-96 rounded-full opacity-30"
          style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.3) 0%, transparent 70%)' }}
        />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 rounded-full opacity-20"
          style={{ background: 'radial-gradient(circle, rgba(139,92,246,0.4) 0%, transparent 70%)' }}
        />

        <div className="relative max-w-7xl mx-auto px-6 pt-24 pb-20 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-100 dark:bg-indigo-900/40 border border-indigo-200 dark:border-indigo-700 mb-8">
            <SparklesIcon className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            <span className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">AI-Native GRC Platform</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-gray-900 dark:text-white leading-[1.1] mb-6">
            Intelligent<br />
            Governance, Risk &<br />
            <span className="text-transparent bg-clip-text"
              style={{ backgroundImage: 'linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa)' }}
            >
              Compliance
            </span>
          </h1>

          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Four integrated pillars. One unified platform. Zero coding required.
            AI-powered risk intelligence that detects, explains,
            recommends, and acts — automatically.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link
              to="/login"
              className="px-8 py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-xl shadow-indigo-500/30 hover:shadow-indigo-500/50 transition-all flex items-center gap-2 text-base"
            >
              Get Started <ArrowRightIcon className="h-5 w-5" />
            </Link>
            <a
              href="#pillars"
              className="px-8 py-3.5 bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 font-semibold rounded-xl border border-gray-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-lg transition-all text-base"
            >
              Explore Modules
            </a>
          </div>

          {/* Stats bar */}
          <div className="max-w-4xl mx-auto grid grid-cols-3 md:grid-cols-6 gap-6 bg-white/60 dark:bg-slate-900/60 backdrop-blur-xl rounded-2xl p-6 border border-gray-200/50 dark:border-slate-700/50 shadow-xl">
            {stats.map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl md:text-3xl font-extrabold text-gray-900 dark:text-white">{s.value}</div>
                <div className="text-xs text-gray-500 dark:text-gray-500 font-medium mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Four Pillars ──────────────────────────── */}
      <section id="pillars" className="max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white tracking-tight">Four Pillars. One Platform.</h2>
          <p className="mt-4 text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
            Everything traditional GRC does — plus AI intelligence that explains why, recommends what, and proves it worked.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {pillars.map((p) => (
            <div
              key={p.title}
              className={`rounded-2xl p-8 border ${p.border} ${p.bg} hover:shadow-xl transition-all duration-300 group`}
            >
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-gradient-to-br ${p.color} shadow-lg mb-5`}>
                <p.icon className="h-6 w-6 text-white" />
              </div>
              <div className="flex items-baseline gap-3 mb-2">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">{p.title}</h3>
                <span className="text-xs font-medium text-gray-400 dark:text-gray-500">{p.subtitle}</span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed mb-5">{p.description}</p>
              <div className="flex flex-wrap gap-2">
                {p.features.map((f) => (
                  <span key={f} className="px-3 py-1 text-xs font-medium rounded-full bg-white/80 dark:bg-slate-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-slate-700">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── AI Intelligence ──────────────────────── */}
      <section id="ai" className="relative py-24 overflow-hidden"
        style={{ background: 'linear-gradient(180deg, #1e1b4b 0%, #0f172a 100%)' }}
      >
        <div className="absolute inset-0"
          style={{
            backgroundImage: 'radial-gradient(rgba(99,102,241,0.15) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />
        <div className="relative max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-900/50 border border-indigo-700 mb-6">
              <SparklesIcon className="h-4 w-4 text-indigo-400" />
              <span className="text-sm font-semibold text-indigo-300">AI-Powered</span>
            </div>
            <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
              GRC Intelligence That Thinks
            </h2>
            <p className="mt-4 text-lg text-indigo-200/60 max-w-2xl mx-auto">
              Don't just detect risks. Understand them, explain them, and fix them — with AI that reasons across all four pillars.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {aiFeatures.map((f) => (
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

      {/* ── Why Governex+ ──────────────────────── */}
      <section id="why" className="max-w-7xl mx-auto px-6 py-24">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white tracking-tight mb-6">
              Why Organizations Choose Governex+
            </h2>
            <p className="text-lg text-gray-500 dark:text-gray-400 mb-10 leading-relaxed">
              Built for the modern enterprise. No coding. No complexity. No four separate products.
              One platform that deploys in days and delivers value in weeks.
            </p>
            <div className="space-y-4">
              {advantages.map((a) => (
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
              { icon: GlobeAltIcon, label: 'Cloud Native', value: 'Secure multi-tenant architecture with automatic data isolation per organization' },
              { icon: LockClosedIcon, label: 'Enterprise Security', value: 'Single sign-on, multi-factor authentication, and role-based access built in' },
              { icon: ServerStackIcon, label: 'Enterprise Scale', value: 'Handle thousands of users, millions of transactions, and complex org structures' },
              { icon: UserGroupIcon, label: 'Start Small, Grow Big', value: 'Begin with one module. Add more anytime. No reimplementation needed.' },
            ].map((c) => (
              <div key={c.label} className="bg-gray-50 dark:bg-slate-900 rounded-2xl p-6 border border-gray-100 dark:border-slate-800">
                <c.icon className="h-8 w-8 text-indigo-500 mb-3" />
                <h4 className="text-sm font-bold text-gray-900 dark:text-white mb-1">{c.label}</h4>
                <p className="text-xs text-gray-500 dark:text-gray-500 leading-relaxed">{c.value}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-6 pb-24">
        <div className="rounded-3xl p-12 md:p-16 text-center relative overflow-hidden"
          style={{ background: 'linear-gradient(135deg, #4338ca 0%, #6366f1 50%, #7c3aed 100%)' }}
        >
          <div className="absolute inset-0"
            style={{
              backgroundImage: 'radial-gradient(rgba(255,255,255,0.1) 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          />
          <div className="relative">
            <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight mb-4">
              Ready to modernize your GRC?
            </h2>
            <p className="text-lg text-indigo-200/80 max-w-xl mx-auto mb-8">
              Start with one module. Scale to the full platform. No migration risk.
            </p>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 px-8 py-4 bg-white text-indigo-700 font-bold rounded-xl shadow-2xl hover:shadow-3xl hover:scale-105 transition-all text-base"
            >
              Launch Platform <ArrowRightIcon className="h-5 w-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────── */}
      <footer className="border-t border-gray-100 dark:border-slate-800 py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <ShieldSolid className="h-5 w-5 text-indigo-500" />
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">Governex+</span>
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-600">
            &copy; 2026 Governex+ Platform. Intelligent Governance, Risk & Compliance.
          </p>
        </div>
      </footer>
    </div>
  );
}
