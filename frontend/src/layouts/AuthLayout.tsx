import { Outlet } from 'react-router-dom';
import { ShieldCheckIcon, CheckBadgeIcon, LockClosedIcon, ChartBarIcon, UserGroupIcon } from '@heroicons/react/24/outline';

const features = [
  {
    icon: ShieldCheckIcon,
    title: 'Risk Intelligence Engine',
    description: '128+ pre-built SoD rules with usage-aware scoring and AI recommendations',
  },
  {
    icon: LockClosedIcon,
    title: 'Access Lifecycle Manager',
    description: 'Automated provisioning, certification campaigns, and access reviews',
  },
  {
    icon: CheckBadgeIcon,
    title: 'Control Intelligence',
    description: 'SOX, COSO, and ISO 27001 ready with continuous monitoring and evidence',
  },
  {
    icon: UserGroupIcon,
    title: 'Privileged Access Governor',
    description: 'Emergency elevated access with real-time session monitoring and AI review',
  },
];

export function AuthLayout() {
  return (
    <div className="min-h-screen flex bg-white dark:bg-slate-950">
      {/* Left panel — brand */}
      <div className="hidden lg:flex lg:w-[52%] relative overflow-hidden"
        style={{
          background: 'linear-gradient(145deg, #0a0f1e 0%, #0f1b3e 40%, #1a1060 70%, #0d0a2e 100%)',
        }}
      >
        {/* Subtle dot-grid overlay */}
        <div className="absolute inset-0"
          style={{
            backgroundImage: 'radial-gradient(rgba(99,102,241,0.18) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
        />

        {/* Glow orbs */}
        <div className="absolute top-[-80px] left-[-80px] w-[420px] h-[420px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.25) 0%, transparent 70%)' }}
        />
        <div className="absolute bottom-[-120px] right-[-100px] w-[500px] h-[500px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(139,92,246,0.2) 0%, transparent 70%)' }}
        />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(67,56,202,0.12) 0%, transparent 70%)' }}
        />

        <div className="relative z-10 flex flex-col justify-between px-14 py-14 w-full">
          {/* Top: logo + brand name */}
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #6366f1, #4338ca)', boxShadow: '0 8px 24px rgba(99,102,241,0.4)' }}
            >
              <ShieldCheckIcon className="h-6 w-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold text-white tracking-tight">
                Governex<span className="text-indigo-400">+</span>
              </span>
              <p className="text-[10px] tracking-[0.2em] uppercase text-indigo-400/70 font-medium">GRC Platform</p>
            </div>
          </div>

          {/* Middle: headline + features */}
          <div className="mt-auto mb-auto pt-16">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full mb-6"
              style={{ background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.25)' }}
            >
              <ChartBarIcon className="h-3.5 w-3.5 text-indigo-300" />
              <span className="text-xs font-semibold text-indigo-300 tracking-wide">Enterprise Grade Security</span>
            </div>

            <h1 className="text-[38px] font-bold leading-[1.15] text-white mb-5 tracking-tight"
              style={{ textShadow: '0 2px 20px rgba(0,0,0,0.3)' }}
            >
              Intelligent<br />
              Governance &amp;<br />
              <span className="text-transparent bg-clip-text"
                style={{ backgroundImage: 'linear-gradient(135deg, #818cf8, #c4b5fd)' }}
              >
                Risk Control
              </span>
            </h1>

            <p className="text-base text-indigo-200/70 leading-relaxed max-w-sm mb-10">
              A unified platform for access governance, SoD risk analysis,
              compliance automation, and real-time audit intelligence.
            </p>

            {/* Feature list */}
            <div className="space-y-4">
              {features.map((f) => (
                <div key={f.title} className="flex items-start gap-3.5">
                  <div className="mt-0.5 w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: 'rgba(99,102,241,0.18)', border: '1px solid rgba(99,102,241,0.25)' }}
                  >
                    <f.icon className="h-4 w-4 text-indigo-300" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white leading-tight">{f.title}</p>
                    <p className="text-xs text-indigo-200/60 mt-0.5 leading-relaxed">{f.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Bottom: stats */}
          <div className="mt-12 pt-8"
            style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}
          >
            <div className="grid grid-cols-3 gap-6">
              {[
                { value: '1,014', label: 'API Endpoints' },
                { value: '99.9%', label: 'Uptime SLA' },
                { value: '4 Pillars', label: 'AC + PC + RM + AM' },
              ].map((stat) => (
                <div key={stat.label}>
                  <div className="text-2xl font-bold text-white tracking-tight">{stat.value}</div>
                  <div className="text-xs text-indigo-300/60 mt-0.5 font-medium">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right panel — login form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 sm:px-12 bg-gray-50 dark:bg-slate-950">
        <div className="w-full max-w-[420px]">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #6366f1, #4338ca)' }}
            >
              <ShieldCheckIcon className="h-6 w-6 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900 dark:text-white tracking-tight">
              Governex<span className="text-indigo-500">+</span>
            </span>
          </div>

          {/* Form header */}
          <div className="mb-8">
            <h2 className="text-[28px] font-bold text-gray-900 dark:text-white tracking-tight leading-tight">
              Welcome back
            </h2>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Sign in to your governance platform
            </p>
          </div>

          {/* White card wrapping the outlet form */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 shadow-xl shadow-gray-200/80 dark:shadow-black/40 border border-gray-100 dark:border-slate-800">
            <Outlet />
          </div>

          <p className="mt-6 text-center text-xs text-gray-400 dark:text-gray-600">
            &copy; 2026 Governex+ Platform &mdash; Enterprise GRC Solution
          </p>
        </div>
      </div>
    </div>
  );
}
