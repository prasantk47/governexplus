/**
 * Governex+ Platform - Dashboard Layout
 * Enterprise Design System
 */
import { useState, useMemo } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import {
  Bars3Icon,
  HomeIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  DocumentCheckIcon,
  FireIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  BellIcon,
  MagnifyingGlassIcon,
  KeyIcon,
  BuildingOfficeIcon,
  SparklesIcon,
  LockClosedIcon,
  ClipboardDocumentListIcon,
  ServerStackIcon,
  XMarkIcon,
  ChevronDownIcon,
  CubeTransparentIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { useTranslation } from '../hooks/useTranslation';
import { PERMISSIONS } from '../config/roles';
import clsx from 'clsx';

interface NavChild {
  name: string;
  href: string;
  permissions?: string[];
}

interface NavItem {
  name: string;
  href: string;
  icon: React.ForwardRefExoticComponent<React.SVGProps<SVGSVGElement>>;
  permissions?: string[];
  children?: NavChild[];
}

const navigation: NavItem[] = [
  {
    name: 'Command Center',
    href: '/',
    icon: HomeIcon,
    permissions: [PERMISSIONS.VIEW_DASHBOARD],
  },
  {
    name: 'Access Lifecycle',
    href: '/access-requests',
    icon: KeyIcon,
    permissions: [PERMISSIONS.VIEW_ACCESS_REQUESTS, PERMISSIONS.VIEW_MY_REQUESTS],
    children: [
      { name: 'My Requests', href: '/access-requests', permissions: [PERMISSIONS.VIEW_MY_REQUESTS] },
      { name: 'New Request', href: '/access-requests/new', permissions: [PERMISSIONS.CREATE_ACCESS_REQUEST] },
      { name: 'Bulk Request', href: '/access-requests/bulk', permissions: [PERMISSIONS.CREATE_BULK_ACCESS_REQUEST] },
      { name: 'Shopping Cart', href: '/access-requests/cart', permissions: [PERMISSIONS.CREATE_ACCESS_REQUEST] },
      { name: 'Model User', href: '/access-requests/model-user', permissions: [PERMISSIONS.CREATE_ACCESS_REQUEST] },
      { name: 'Approvals', href: '/approvals', permissions: [PERMISSIONS.APPROVE_ACCESS_REQUEST, PERMISSIONS.FORWARD_ACCESS_REQUEST] },
    ],
  },
  {
    name: 'Password Self-Service',
    href: '/password',
    icon: LockClosedIcon,
    permissions: [PERMISSIONS.VIEW_PASSWORD_SELF_SERVICE],
    children: [
      { name: 'Change Password', href: '/password/change', permissions: [PERMISSIONS.CHANGE_OWN_PASSWORD] },
      { name: 'Reset in Systems', href: '/password/reset', permissions: [PERMISSIONS.RESET_PASSWORD_IN_SYSTEMS] },
    ],
  },
  {
    name: 'Certification',
    href: '/certification',
    icon: DocumentCheckIcon,
    permissions: [PERMISSIONS.VIEW_CERTIFICATIONS],
    children: [
      { name: 'Campaigns', href: '/certification', permissions: [PERMISSIONS.VIEW_CERTIFICATIONS] },
      { name: 'My Reviews', href: '/certification/review', permissions: [PERMISSIONS.APPROVE_CERTIFICATIONS] },
    ],
  },
  {
    name: 'Privileged Access',
    href: '/privileged-access',
    icon: FireIcon,
    permissions: [PERMISSIONS.VIEW_FIREFIGHTER],
    children: [
      { name: 'Dashboard', href: '/privileged-access', permissions: [PERMISSIONS.VIEW_FIREFIGHTER] },
      { name: 'Request Access', href: '/privileged-access/request', permissions: [PERMISSIONS.REQUEST_FIREFIGHTER] },
      { name: 'Sessions', href: '/privileged-access/sessions', permissions: [PERMISSIONS.VIEW_FIREFIGHTER] },
      { name: 'Live Monitor', href: '/privileged-access/monitor', permissions: [PERMISSIONS.VIEW_LIVE_SESSIONS] },
    ],
  },
  {
    name: 'Risk Intelligence',
    href: '/risk',
    icon: ExclamationTriangleIcon,
    permissions: [PERMISSIONS.VIEW_RISK_DASHBOARD],
    children: [
      { name: 'Overview', href: '/risk', permissions: [PERMISSIONS.VIEW_RISK_DASHBOARD] },
      { name: 'SoD Rules', href: '/risk/rules', permissions: [PERMISSIONS.MANAGE_RISK_RULES] },
      { name: 'Rule Library', href: '/risk/sod-rules', permissions: [PERMISSIONS.VIEW_SOD_RULES] },
      { name: 'Violations', href: '/risk/violations', permissions: [PERMISSIONS.VIEW_VIOLATIONS] },
      { name: 'Simulation', href: '/risk/simulation', permissions: [PERMISSIONS.RUN_RISK_SIMULATION] },
      { name: 'Entitlements', href: '/risk/entitlements', permissions: [PERMISSIONS.VIEW_ENTITLEMENT_INTELLIGENCE] },
      { name: 'Contextual', href: '/risk/contextual', permissions: [PERMISSIONS.VIEW_CONTEXTUAL_RISK] },
      { name: 'Mitigation Controls', href: '/risk/mitigation', permissions: [PERMISSIONS.VIEW_MITIGATION] },
      { name: 'Custom T-Codes', href: '/risk/custom-tcode', permissions: [PERMISSIONS.VIEW_RISK_DASHBOARD] },
      { name: 'Mitigation Monitor', href: '/risk/mitigation-monitoring', permissions: [PERMISSIONS.VIEW_MITIGATION] },
    ],
  },
  {
    name: 'Users',
    href: '/users',
    icon: UserGroupIcon,
    permissions: [PERMISSIONS.VIEW_USERS],
  },
  {
    name: 'Role Design Studio',
    href: '/roles',
    icon: BuildingOfficeIcon,
    permissions: [PERMISSIONS.VIEW_ROLES],
    children: [
      { name: 'Role Catalog', href: '/roles', permissions: [PERMISSIONS.VIEW_ROLES] },
      { name: 'Business Roles', href: '/roles/brm', permissions: [PERMISSIONS.VIEW_BRM] },
      { name: 'Role Designer', href: '/roles/designer', permissions: [PERMISSIONS.DESIGN_ROLES] },
    ],
  },
  {
    name: 'Provisioning',
    href: '/provisioning',
    icon: ArrowPathIcon,
    permissions: [PERMISSIONS.VIEW_PROVISIONING],
  },
  {
    name: 'Reports',
    href: '/reports',
    icon: ChartBarIcon,
    permissions: [PERMISSIONS.VIEW_REPORTS],
  },
  {
    name: 'Compliance',
    href: '/compliance',
    icon: ClipboardDocumentListIcon,
    permissions: [PERMISSIONS.VIEW_COMPLIANCE],
  },
  {
    name: 'Security Controls',
    href: '/security-controls',
    icon: ShieldCheckIcon,
    permissions: [PERMISSIONS.VIEW_COMPLIANCE],
    children: [
      { name: 'Dashboard', href: '/security-controls', permissions: [PERMISSIONS.VIEW_COMPLIANCE] },
      { name: 'All Controls', href: '/security-controls/list', permissions: [PERMISSIONS.VIEW_COMPLIANCE] },
      { name: 'Import', href: '/security-controls/import', permissions: [PERMISSIONS.MANAGE_SYSTEM_CONFIG] },
    ],
  },
  {
    name: 'Enterprise Risk Engine',
    href: '/risk-management',
    icon: ExclamationTriangleIcon,
    permissions: [PERMISSIONS.VIEW_RISK_DASHBOARD],
    children: [
      { name: 'Risk Register', href: '/risk-management/register' },
      { name: 'Risk Heatmap', href: '/risk-management/heatmap' },
      { name: 'KRI Dashboard', href: '/risk-management/kri' },
      { name: 'Incidents', href: '/risk-management/incidents' },
    ],
  },
  {
    name: 'Control Intelligence',
    href: '/process-control',
    icon: ClipboardDocumentListIcon,
    permissions: [PERMISSIONS.VIEW_COMPLIANCE],
    children: [
      { name: 'Control Library', href: '/process-control/controls' },
      { name: 'Control Testing', href: '/process-control/testing' },
      { name: 'Deficiencies', href: '/process-control/deficiencies' },
      { name: 'CCM Dashboard', href: '/process-control/ccm' },
    ],
  },
  {
    name: 'Audit Command Center',
    href: '/audit-management',
    icon: DocumentCheckIcon,
    permissions: [PERMISSIONS.VIEW_AUDIT_LOG],
    children: [
      { name: 'Dashboard', href: '/audit-management' },
      { name: 'Planning', href: '/audit-management/planning' },
      { name: 'Engagements', href: '/audit-management/engagements' },
      { name: 'Findings & Actions', href: '/audit-management/findings' },
    ],
  },
  {
    name: 'Audit Report',
    href: '/audit',
    icon: ClipboardDocumentListIcon,
    permissions: [PERMISSIONS.VIEW_AUDIT_LOG],
  },
  {
    name: 'Intelligence',
    href: '/intelligence',
    icon: SparklesIcon,
    permissions: [PERMISSIONS.VIEW_DASHBOARD],
    children: [
      { name: 'Global Search', href: '/intelligence/search' },
      { name: 'Access Troubleshooter', href: '/intelligence/troubleshooter' },
      { name: 'Role Intelligence', href: '/intelligence/role-intelligence' },
      { name: 'Migration Analyzer', href: '/intelligence/migration' },
      { name: 'Role Drift Detection', href: '/intelligence/drift' },
      { name: 'Fiori Analyzer', href: '/intelligence/fiori' },
      { name: 'Access Timeline', href: '/intelligence/timeline' },
      { name: 'Upgrade Analyzer', href: '/intelligence/upgrade' },
      { name: 'Identity Correlation', href: '/intelligence/identity' },
      { name: 'Audit Evidence', href: '/intelligence/audit-evidence' },
      { name: 'AI Assistant', href: '/ai' },
    ],
  },
  {
    name: 'Workflows',
    href: '/workflows/builder',
    icon: CubeTransparentIcon,
    permissions: [PERMISSIONS.VIEW_SETTINGS],
  },
  {
    name: 'Integrations',
    href: '/integrations',
    icon: ServerStackIcon,
    permissions: [PERMISSIONS.MANAGE_INTEGRATIONS],
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Cog6ToothIcon,
    permissions: [PERMISSIONS.VIEW_SETTINGS, PERMISSIONS.MANAGE_SYSTEM_CONFIG],
    children: [
      { name: 'General', href: '/settings', permissions: [PERMISSIONS.VIEW_SETTINGS] },
      { name: 'Systems', href: '/settings/systems', permissions: [PERMISSIONS.MANAGE_INTEGRATIONS] },
      { name: 'Policies', href: '/settings/policies', permissions: [PERMISSIONS.VIEW_POLICIES] },
      { name: 'Approvers', href: '/settings/approvers', permissions: [PERMISSIONS.MANAGE_APPROVERS] },
      { name: 'Delegations', href: '/settings/delegations', permissions: [PERMISSIONS.VIEW_DELEGATIONS] },
      { name: 'Org Rules', href: '/settings/org-rules', permissions: [PERMISSIONS.MANAGE_SYSTEM_CONFIG] },
      { name: 'Mass Admin', href: '/settings/mass-admin', permissions: [PERMISSIONS.MANAGE_SYSTEM_CONFIG] },
      { name: 'Repo Sync', href: '/settings/repo-sync', permissions: [PERMISSIONS.MANAGE_INTEGRATIONS] },
      { name: 'Transports', href: '/settings/transports', permissions: [PERMISSIONS.MANAGE_SYSTEM_CONFIG] },
      { name: 'Notifications', href: '/settings/notifications', permissions: [PERMISSIONS.VIEW_SETTINGS] },
    ],
  },
];

export function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expandedItems, setExpandedItems] = useState<string[]>([]);
  const location = useLocation();
  const { user, logout, hasAnyPermission, getRoleName } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const { locale, setLocale } = useTranslation();

  const filteredNavigation = useMemo(() => {
    return navigation
      .filter((item) => {
        if (!item.permissions || item.permissions.length === 0) return true;
        return hasAnyPermission(item.permissions);
      })
      .map((item) => {
        if (item.children) {
          const filteredChildren = item.children.filter((child) => {
            if (!child.permissions || child.permissions.length === 0) return true;
            return hasAnyPermission(child.permissions);
          });
          return { ...item, children: filteredChildren.length > 0 ? filteredChildren : undefined };
        }
        return item;
      });
  }, [hasAnyPermission]);

  const toggleExpand = (name: string) => {
    setExpandedItems((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  };

  const isActive = (href: string) => {
    if (href === '/' || href === '/dashboard') {
      return location.pathname === '/' || location.pathname === '/dashboard';
    }
    return location.pathname.startsWith(href);
  };

  const SidebarContent = ({ mobile = false }: { mobile?: boolean }) => (
    <div className="flex grow flex-col overflow-y-auto px-3 pb-4">
      {/* Logo */}
      <div className="flex h-[68px] shrink-0 items-center px-2 border-b border-white/[0.06] mb-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center shadow-lg shadow-indigo-900/40">
            <ShieldCheckIcon className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="text-lg font-bold text-white tracking-tight leading-tight">
              Governex<span className="text-indigo-400">+</span>
            </span>
            <p className="text-[10px] text-slate-500 font-medium tracking-widest uppercase leading-none mt-0.5">GRC Platform</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col mt-1">
        <ul role="list" className="flex flex-1 flex-col gap-y-0.5">
          <li>
            <ul role="list" className="-mx-1 space-y-0.5">
              {filteredNavigation.map((item) => (
                <li key={item.name}>
                  {item.children ? (
                    <div>
                      <button
                        onClick={() => toggleExpand(item.name)}
                        className={clsx(
                          isActive(item.href)
                            ? 'bg-indigo-600/20 text-white border-l-2 border-indigo-500 pl-[10px]'
                            : 'text-slate-400 hover:text-white hover:bg-white/[0.06] border-l-2 border-transparent pl-[10px]',
                          'group flex w-full items-center gap-x-3 rounded-r-lg px-3 py-2.5 text-sm font-medium transition-all duration-150'
                        )}
                      >
                        <item.icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
                        <span className="flex-1 text-left">{item.name}</span>
                        <ChevronDownIcon
                          className={clsx(
                            'h-3.5 w-3.5 transition-transform duration-200 text-slate-500',
                            expandedItems.includes(item.name) ? 'rotate-180' : ''
                          )}
                        />
                      </button>
                      <div
                        className={clsx(
                          'overflow-hidden transition-all duration-200',
                          expandedItems.includes(item.name) ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
                        )}
                      >
                        <ul className="mt-0.5 space-y-0.5 ml-2">
                          {item.children.map((child) => (
                            <li key={child.name}>
                              <Link
                                to={child.href}
                                onClick={() => mobile && setSidebarOpen(false)}
                                className={clsx(
                                  location.pathname === child.href
                                    ? 'text-white bg-white/10 border-l-2 border-indigo-400 pl-[10px]'
                                    : 'text-slate-500 hover:text-slate-200 hover:bg-white/[0.04] border-l-2 border-transparent pl-[10px]',
                                  'block rounded-r-lg py-2 pr-3 pl-10 text-sm transition-all duration-150'
                                )}
                              >
                                {child.name}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ) : (
                    <Link
                      to={item.href}
                      onClick={() => mobile && setSidebarOpen(false)}
                      className={clsx(
                        isActive(item.href)
                          ? 'bg-indigo-600/20 text-white border-l-2 border-indigo-500 pl-[10px]'
                          : 'text-slate-400 hover:text-white hover:bg-white/[0.06] border-l-2 border-transparent pl-[10px]',
                        'group flex gap-x-3 rounded-r-lg px-3 py-2.5 text-sm font-medium transition-all duration-150'
                      )}
                    >
                      <item.icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
                      {item.name}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </li>
        </ul>
      </nav>

      {/* User section */}
      <div className="mt-auto pt-3 border-t border-white/[0.06]">
        <div className="flex items-center gap-3 px-2 py-2.5 rounded-xl hover:bg-white/[0.04] transition-colors cursor-default">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center text-white text-sm font-bold shadow-md flex-shrink-0">
            {user?.name?.charAt(0)?.toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white truncate leading-tight">{user?.name || 'User'}</p>
            <span className="inline-block mt-0.5 text-[10px] font-medium px-1.5 py-0.5 rounded bg-indigo-600/30 text-indigo-300 truncate">
              {getRoleName()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen">
      {/* Mobile sidebar */}
      <Transition.Root show={sidebarOpen} as={Fragment}>
        <Dialog as="div" className="relative z-50 lg:hidden" onClose={setSidebarOpen}>
          <Transition.Child
            as={Fragment}
            enter="transition-opacity ease-linear duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="transition-opacity ease-linear duration-300"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-gray-900/80" />
          </Transition.Child>

          <div className="fixed inset-0 flex">
            <Transition.Child
              as={Fragment}
              enter="transition ease-in-out duration-300 transform"
              enterFrom="-translate-x-full"
              enterTo="translate-x-0"
              leave="transition ease-in-out duration-300 transform"
              leaveFrom="translate-x-0"
              leaveTo="-translate-x-full"
            >
              <Dialog.Panel className="relative mr-16 flex w-full max-w-[280px] flex-1">
                <Transition.Child
                  as={Fragment}
                  enter="ease-in-out duration-300"
                  enterFrom="opacity-0"
                  enterTo="opacity-100"
                  leave="ease-in-out duration-300"
                  leaveFrom="opacity-100"
                  leaveTo="opacity-0"
                >
                  <div className="absolute left-full top-0 flex w-16 justify-center pt-5">
                    <button type="button" className="-m-2.5 p-2.5" onClick={() => setSidebarOpen(false)}>
                      <XMarkIcon className="h-6 w-6 text-white" aria-hidden="true" />
                    </button>
                  </div>
                </Transition.Child>
                <div className="glass-sidebar flex-1 pt-0">
                  <SidebarContent mobile />
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition.Root>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-64 lg:flex-col">
        <div className="glass-sidebar flex-1 pt-0">
          <SidebarContent />
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top navbar */}
        <div className="sticky top-0 z-40 glass-nav">
          <div className="flex h-[68px] shrink-0 items-center gap-x-4 px-4 sm:gap-x-6 sm:px-6 lg:px-8">
            <button
              type="button"
              className="-m-2.5 p-2.5 text-gray-500 dark:text-gray-400 lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <Bars3Icon className="h-6 w-6" aria-hidden="true" />
            </button>

            {/* Separator */}
            <div className="h-6 w-px bg-gray-200 dark:bg-gray-700 lg:hidden" />

            <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
              {/* Search */}
              <form className="relative flex flex-1 items-center" action="#" method="GET">
                <MagnifyingGlassIcon
                  className="pointer-events-none absolute left-3.5 h-[18px] w-[18px] text-gray-400"
                  aria-hidden="true"
                />
                <input
                  id="search"
                  name="search"
                  className="block h-10 w-full max-w-lg bg-gray-50 dark:bg-slate-800/80 border border-gray-200 dark:border-slate-700 rounded-xl py-0 pl-10 pr-4 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 transition-all"
                  placeholder="Search users, roles, requests..."
                  type="search"
                />
              </form>

              <div className="flex items-center gap-x-1 lg:gap-x-2">
                {/* Dark mode toggle */}
                <button
                  type="button"
                  onClick={toggleTheme}
                  className="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
                  title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                >
                  {isDark ? (
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
                    </svg>
                  )}
                </button>

                {/* Language toggle — EN / AR */}
                <button
                  type="button"
                  onClick={() => setLocale(locale === 'ar' ? 'en' : 'ar')}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold border border-gray-200 dark:border-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors select-none"
                  title={locale === 'ar' ? 'Switch to English' : 'التبديل إلى العربية'}
                  aria-label="Toggle language"
                >
                  {locale === 'ar' ? (
                    <>
                      <span className="text-base leading-none">🇬🇧</span>
                      <span>EN</span>
                    </>
                  ) : (
                    <>
                      <span className="text-base leading-none">🇸🇦</span>
                      <span>AR</span>
                    </>
                  )}
                </button>

                {/* Notifications */}
                <button
                  type="button"
                  className="relative p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
                >
                  <span className="sr-only">View notifications</span>
                  <BellIcon className="h-5 w-5" aria-hidden="true" />
                  <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center text-[9px] text-white font-bold leading-none">
                    3
                  </span>
                </button>

                {/* Separator */}
                <div className="hidden lg:block h-6 w-px bg-gray-200 dark:bg-gray-700 mx-1" />

                {/* Profile */}
                <div className="flex items-center gap-x-3">
                  <div className="hidden lg:flex lg:items-center gap-2.5 pl-1">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center text-white text-xs font-bold shadow-md">
                      {user?.name?.charAt(0)?.toUpperCase() || 'U'}
                    </div>
                    <div className="flex flex-col">
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100 leading-tight">
                        {user?.name || 'User'}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400 leading-tight">{getRoleName()}</span>
                    </div>
                  </div>
                  <button
                    onClick={logout}
                    className="text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 px-3 py-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                  >
                    Logout
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="py-8">
          <div className="px-4 sm:px-6 lg:px-8">
            <ErrorBoundary>
              <Outlet />
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </div>
  );
}
