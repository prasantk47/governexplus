/**
 * Governex+ Platform - Dashboard Layout
 * Domain: governexplus.com
 * Glassmorphism Design
 */
import { useState, useMemo } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
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
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
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
    name: 'Dashboard',
    href: '/dashboard',
    icon: HomeIcon,
    permissions: [PERMISSIONS.VIEW_DASHBOARD],
  },
  {
    name: 'Access Requests',
    href: '/access-requests',
    icon: KeyIcon,
    permissions: [PERMISSIONS.VIEW_ACCESS_REQUESTS, PERMISSIONS.VIEW_MY_REQUESTS],
    children: [
      { name: 'My Requests', href: '/access-requests', permissions: [PERMISSIONS.VIEW_MY_REQUESTS] },
      { name: 'New Request', href: '/access-requests/new', permissions: [PERMISSIONS.CREATE_ACCESS_REQUEST] },
      { name: 'Bulk Request', href: '/access-requests/bulk', permissions: [PERMISSIONS.CREATE_BULK_ACCESS_REQUEST] },
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
    name: 'Firefighter',
    href: '/firefighter',
    icon: FireIcon,
    permissions: [PERMISSIONS.VIEW_FIREFIGHTER],
    children: [
      { name: 'Dashboard', href: '/firefighter', permissions: [PERMISSIONS.VIEW_FIREFIGHTER] },
      { name: 'Request Access', href: '/firefighter/request', permissions: [PERMISSIONS.REQUEST_FIREFIGHTER] },
      { name: 'Sessions', href: '/firefighter/sessions', permissions: [PERMISSIONS.VIEW_FIREFIGHTER] },
      { name: 'Live Monitor', href: '/firefighter/monitor', permissions: [PERMISSIONS.VIEW_LIVE_SESSIONS] },
    ],
  },
  {
    name: 'Risk Management',
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
    ],
  },
  {
    name: 'Users',
    href: '/users',
    icon: UserGroupIcon,
    permissions: [PERMISSIONS.VIEW_USERS],
  },
  {
    name: 'Role Engineering',
    href: '/roles',
    icon: BuildingOfficeIcon,
    permissions: [PERMISSIONS.VIEW_ROLES],
    children: [
      { name: 'Role Catalog', href: '/roles', permissions: [PERMISSIONS.VIEW_ROLES] },
      { name: 'Role Designer', href: '/roles/designer', permissions: [PERMISSIONS.DESIGN_ROLES] },
    ],
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
    name: 'AI Assistant',
    href: '/ai',
    icon: SparklesIcon,
    permissions: [PERMISSIONS.VIEW_DASHBOARD],
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
      { name: 'Policies', href: '/settings/policies', permissions: [PERMISSIONS.VIEW_POLICIES] },
    ],
  },
];

export function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expandedItems, setExpandedItems] = useState<string[]>([]);
  const location = useLocation();
  const { user, logout, hasAnyPermission, getRoleName } = useAuth();

  // Filter navigation based on user permissions
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

  const isActive = (href: string) => location.pathname.startsWith(href);

  // Sidebar content (shared between mobile and desktop)
  const SidebarContent = ({ mobile = false }: { mobile?: boolean }) => (
    <div className="flex grow flex-col gap-y-4 overflow-y-auto px-4 pb-4">
      {/* Logo */}
      <div className="flex h-14 shrink-0 items-center">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-gray-600 to-gray-800 flex items-center justify-center shadow-lg">
            <ShieldCheckIcon className="h-5 w-5 text-white" />
          </div>
          <span className="text-sm font-semibold text-white tracking-tight">
            Governex+
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col">
        <ul role="list" className="flex flex-1 flex-col gap-y-5">
          <li>
            <ul role="list" className="-mx-2 space-y-0.5">
              {filteredNavigation.map((item) => (
                <li key={item.name}>
                  {item.children ? (
                    <div>
                      <button
                        onClick={() => toggleExpand(item.name)}
                        className={clsx(
                          isActive(item.href)
                            ? 'bg-white/15 text-white'
                            : 'text-white/70 hover:text-white hover:bg-white/10',
                          'group flex w-full items-center gap-x-2.5 rounded-xl px-3 py-2 text-xs leading-5 font-medium transition-all duration-200'
                        )}
                      >
                        <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                        <span className="flex-1 text-left">{item.name}</span>
                        <ChevronDownIcon
                          className={clsx(
                            'h-3.5 w-3.5 transition-transform duration-200',
                            expandedItems.includes(item.name) ? 'rotate-180' : ''
                          )}
                        />
                      </button>
                      <div
                        className={clsx(
                          'overflow-hidden transition-all duration-200',
                          expandedItems.includes(item.name) ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                        )}
                      >
                        <ul className="mt-1 px-2 space-y-0.5">
                          {item.children.map((child) => (
                            <li key={child.name}>
                              <Link
                                to={child.href}
                                onClick={() => mobile && setSidebarOpen(false)}
                                className={clsx(
                                  location.pathname === child.href
                                    ? 'bg-white/15 text-white'
                                    : 'text-white/60 hover:text-white hover:bg-white/10',
                                  'block rounded-lg py-1.5 pr-2 pl-8 text-xs leading-5 transition-all duration-200'
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
                          ? 'bg-white/15 text-white'
                          : 'text-white/70 hover:text-white hover:bg-white/10',
                        'group flex gap-x-2.5 rounded-xl px-3 py-2 text-xs leading-5 font-medium transition-all duration-200'
                      )}
                    >
                      <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                      {item.name}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </li>
        </ul>
      </nav>

      {/* User section at bottom */}
      <div className="mt-auto">
        <div className="glass-btn rounded-xl p-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gray-500 to-gray-700 flex items-center justify-center text-white text-xs font-semibold">
              {user?.name?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">{user?.name || 'User'}</p>
              <p className="text-[10px] text-white/60 truncate">{getRoleName()}</p>
            </div>
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
            <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-sm" />
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
              <Dialog.Panel className="relative mr-16 flex w-full max-w-xs flex-1">
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
                <div className="glass-sidebar flex-1">
                  <SidebarContent mobile />
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition.Root>

      {/* Static sidebar for desktop */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-60 lg:flex-col">
        <div className="glass-sidebar flex-1 pt-2">
          <SidebarContent />
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-60">
        {/* Top navbar - glassmorphism */}
        <div className="sticky top-0 z-40 glass-nav">
          <div className="flex h-14 shrink-0 items-center gap-x-4 px-4 sm:gap-x-6 sm:px-6 lg:px-8">
            <button
              type="button"
              className="-m-2.5 p-2.5 text-gray-700 lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <Bars3Icon className="h-5 w-5" aria-hidden="true" />
            </button>

            <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
              {/* Search */}
              <form className="relative flex flex-1" action="#" method="GET">
                <MagnifyingGlassIcon
                  className="pointer-events-none absolute inset-y-0 left-0 h-full w-4 text-gray-400"
                  aria-hidden="true"
                />
                <input
                  id="search"
                  name="search"
                  className="glass-input block h-9 w-full max-w-md my-auto border-0 py-0 pl-8 pr-4 text-xs text-gray-900 placeholder:text-gray-400 focus:ring-0"
                  placeholder="Search users, roles, requests..."
                  type="search"
                />
              </form>

              <div className="flex items-center gap-x-3 lg:gap-x-4">
                {/* Notifications */}
                <button
                  type="button"
                  className="glass-btn p-2 text-gray-600 hover:text-gray-900 transition-colors"
                >
                  <span className="sr-only">View notifications</span>
                  <BellIcon className="h-5 w-5" aria-hidden="true" />
                </button>

                {/* Profile dropdown */}
                <div className="flex items-center gap-x-3">
                  <span className="hidden lg:flex lg:flex-col lg:items-end">
                    <span className="text-xs font-medium text-gray-700" aria-hidden="true">
                      {user?.name || 'User'}
                    </span>
                    <span className="text-[10px] text-gray-400">{getRoleName()}</span>
                  </span>
                  <button
                    onClick={logout}
                    className="btn-secondary text-xs py-1.5 px-3"
                  >
                    Logout
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="py-6">
          <div className="px-4 sm:px-6 lg:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
