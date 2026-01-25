import { Outlet } from 'react-router-dom';
import { ShieldCheckIcon } from '@heroicons/react/24/outline';

export function AuthLayout() {
  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      {/* Glass card */}
      <div className="max-w-md w-full relative z-10">
        <div className="glass-card p-8 space-y-8">
          {/* Logo and header */}
          <div className="text-center">
            <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center shadow-lg">
              <ShieldCheckIcon className="h-9 w-9 text-white" />
            </div>
            <h2 className="mt-6 text-2xl font-bold text-gray-900 tracking-tight">
              Governex+
            </h2>
            <p className="mt-2 text-sm text-gray-500">
              Intelligent Governance — Secure. Compliant. Intelligent.
            </p>
          </div>

          {/* Form content */}
          <Outlet />
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-gray-400">
          2024 Governex+ Platform. Enterprise GRC Solution.
        </p>
      </div>
    </div>
  );
}
