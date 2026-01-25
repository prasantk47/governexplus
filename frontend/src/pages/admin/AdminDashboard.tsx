import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  BuildingOffice2Icon,
  UserGroupIcon,
  CurrencyDollarIcon,
  ServerStackIcon,
  PlusIcon,
  ArrowRightOnRectangleIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  MagnifyingGlassIcon,
  EllipsisVerticalIcon,
  PlayIcon,
  PauseIcon,
  PencilIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  GlobeAltIcon,
  ShieldCheckIcon,
  BellIcon,
  Cog6ToothIcon,
  SparklesIcon,
  ChevronRightIcon,
  CalendarDaysIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { ShieldCheckIcon as ShieldCheckSolid } from '@heroicons/react/24/solid';
import clsx from 'clsx';

interface DashboardStats {
  tenants: { total: number; active: number; trial: number; suspended: number };
  users: { total: number; active_today: number; new_this_month: number };
  revenue: { mrr: number; arr: number; growth: number };
  systems: { connected: number; sync_healthy: number };
}

interface Tenant {
  id: string;
  name: string;
  slug: string;
  admin_email: string;
  tier: string;
  status: string;
  users_count: number;
  created_at: string;
  last_activity: string;
}

interface Activity {
  id: string;
  type: 'tenant_created' | 'user_login' | 'payment' | 'alert';
  message: string;
  time: string;
  tenant?: string;
}

const statusConfig: Record<string, { color: string; bgColor: string; label: string; icon: any }> = {
  active: { color: 'text-emerald-600', bgColor: 'bg-emerald-50 border-emerald-200', label: 'Active', icon: CheckCircleIcon },
  trial: { color: 'text-blue-600', bgColor: 'bg-blue-50 border-blue-200', label: 'Trial', icon: ClockIcon },
  suspended: { color: 'text-red-600', bgColor: 'bg-red-50 border-red-200', label: 'Suspended', icon: XCircleIcon },
  pending: { color: 'text-amber-600', bgColor: 'bg-amber-50 border-amber-200', label: 'Pending', icon: ClockIcon },
};

const tierConfig: Record<string, { color: string; bgColor: string; label: string; gradient: string }> = {
  starter: { color: 'text-slate-700', bgColor: 'bg-slate-100', label: 'Starter', gradient: 'from-slate-500 to-slate-600' },
  professional: { color: 'text-indigo-700', bgColor: 'bg-indigo-100', label: 'Professional', gradient: 'from-indigo-500 to-purple-600' },
  enterprise: { color: 'text-amber-700', bgColor: 'bg-gradient-to-r from-amber-100 to-yellow-100', label: 'Enterprise', gradient: 'from-amber-500 to-yellow-500' },
};

export function AdminDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTenant, setSelectedTenant] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  const adminUser = JSON.parse(localStorage.getItem('admin_user') || '{}');

  useEffect(() => {
    // Check authentication
    const token = localStorage.getItem('admin_token');
    if (!token) {
      navigate('/admin');
      return;
    }
    fetchDashboardData();

    // Update time every minute
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, [navigate]);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    try {
      const statsRes = await fetch('/api/admin/dashboard/stats', {
        headers: { Authorization: `Bearer ${localStorage.getItem('admin_token')}` }
      });
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }

      const tenantsRes = await fetch('/api/admin/tenants', {
        headers: { Authorization: `Bearer ${localStorage.getItem('admin_token')}` }
      });
      if (tenantsRes.ok) {
        const data = await tenantsRes.json();
        setTenants(data.tenants || []);
      }
    } catch (err) {
      // Mock data for demo
      setStats({
        tenants: { total: 12, active: 8, trial: 3, suspended: 1 },
        users: { total: 1847, active_today: 423, new_this_month: 156 },
        revenue: { mrr: 47500, arr: 570000, growth: 18.5 },
        systems: { connected: 34, sync_healthy: 97 }
      });
      setTenants([
        { id: 'tenant_acme', name: 'Acme Corporation', slug: 'acme', admin_email: 'admin@acme.com', tier: 'enterprise', status: 'active', users_count: 456, created_at: '2024-06-15', last_activity: '2026-01-24' },
        { id: 'tenant_globex', name: 'Globex Industries', slug: 'globex', admin_email: 'cto@globex.com', tier: 'professional', status: 'active', users_count: 189, created_at: '2024-08-22', last_activity: '2026-01-24' },
        { id: 'tenant_wayne', name: 'Wayne Enterprises', slug: 'wayne', admin_email: 'security@wayne.com', tier: 'enterprise', status: 'active', users_count: 892, created_at: '2024-03-10', last_activity: '2026-01-24' },
        { id: 'tenant_stark', name: 'Stark Industries', slug: 'stark', admin_email: 'jarvis@stark.com', tier: 'enterprise', status: 'trial', users_count: 234, created_at: '2026-01-10', last_activity: '2026-01-24' },
        { id: 'tenant_initech', name: 'Initech Solutions', slug: 'initech', admin_email: 'admin@initech.com', tier: 'starter', status: 'trial', users_count: 23, created_at: '2026-01-17', last_activity: '2026-01-23' },
        { id: 'tenant_umbrella', name: 'Umbrella Corp', slug: 'umbrella', admin_email: 'security@umbrella.com', tier: 'professional', status: 'suspended', users_count: 67, created_at: '2024-09-01', last_activity: '2026-01-10' },
      ]);
      setActivities([
        { id: '1', type: 'tenant_created', message: 'New tenant "Stark Industries" started trial', time: '2 hours ago', tenant: 'Stark Industries' },
        { id: '2', type: 'payment', message: 'Payment received from Acme Corporation', time: '4 hours ago', tenant: 'Acme Corporation' },
        { id: '3', type: 'user_login', message: '156 new users this month across all tenants', time: '1 day ago' },
        { id: '4', type: 'alert', message: 'High API usage detected for Wayne Enterprises', time: '2 days ago', tenant: 'Wayne Enterprises' },
      ]);
    }
    setIsLoading(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    navigate('/admin');
  };

  const handleSuspendTenant = async (tenantId: string) => {
    try {
      await fetch(`/api/admin/tenants/${tenantId}/suspend`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('admin_token')}` }
      });
      fetchDashboardData();
    } catch (err) {
      setTenants(tenants.map(t => t.id === tenantId ? { ...t, status: 'suspended' } : t));
    }
    setSelectedTenant(null);
  };

  const handleActivateTenant = async (tenantId: string) => {
    try {
      await fetch(`/api/admin/tenants/${tenantId}/activate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('admin_token')}` }
      });
      fetchDashboardData();
    } catch (err) {
      setTenants(tenants.map(t => t.id === tenantId ? { ...t, status: 'active' } : t));
    }
    setSelectedTenant(null);
  };

  const filteredTenants = tenants.filter(t => {
    const matchesSearch = !searchTerm ||
      t.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.admin_email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = !filterStatus || t.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-indigo-200 rounded-full animate-spin border-t-indigo-600" />
            <ShieldCheckSolid className="absolute inset-0 m-auto h-8 w-8 text-indigo-600" />
          </div>
          <p className="mt-4 text-slate-600 font-medium">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-slate-200/50 sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-6">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="absolute inset-0 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl blur opacity-40" />
                  <div className="relative w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                    <ShieldCheckIcon className="h-6 w-6 text-white" />
                  </div>
                </div>
                <div>
                  <span className="font-bold text-slate-900 text-lg">Governex<span className="text-indigo-600">+</span></span>
                  <span className="ml-2 px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs font-semibold rounded-full">Admin</span>
                </div>
              </div>

              <nav className="hidden md:flex items-center gap-1">
                <button className="px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg">Dashboard</button>
                <button onClick={() => toast.success('Opening Tenants...')} className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors">Tenants</button>
                <button onClick={() => toast.success('Opening Analytics...')} className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors">Analytics</button>
                <button onClick={() => toast.success('Opening Settings...')} className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors">Settings</button>
              </nav>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => toast.success('Opening notifications...')}
                className="relative p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <BellIcon className="h-5 w-5" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
              </button>
              <button
                onClick={() => toast.success('Opening settings...')}
                className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <Cog6ToothIcon className="h-5 w-5" />
              </button>

              <div className="w-px h-8 bg-slate-200 mx-2" />

              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <p className="text-sm font-medium text-slate-900">{adminUser.name || 'Admin'}</p>
                  <p className="text-xs text-slate-500">{adminUser.email}</p>
                </div>
                <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold shadow-lg">
                  {(adminUser.name || 'A').charAt(0)}
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="Logout"
                >
                  <ArrowRightOnRectangleIcon className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto px-6 py-8">
        {/* Welcome Section */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 text-sm text-slate-500 mb-1">
              <CalendarDaysIcon className="h-4 w-4" />
              <span>{currentTime.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</span>
            </div>
            <h1 className="text-3xl font-bold text-slate-900">
              Welcome back, {(adminUser.name || 'Admin').split(' ')[0]}
            </h1>
            <p className="text-slate-500 mt-1">Here's what's happening with your platform today.</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchDashboardData}
              className="flex items-center gap-2 px-4 py-2.5 text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors shadow-sm"
            >
              <ArrowPathIcon className="h-4 w-4" />
              Refresh
            </button>
            <Link
              to="/admin/onboard"
              className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl hover:from-indigo-600 hover:to-purple-700 transition-all shadow-lg shadow-indigo-500/25"
            >
              <PlusIcon className="h-5 w-5" />
              <span className="font-medium">Onboard Tenant</span>
            </Link>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Tenants Card */}
          <div className="group relative bg-white rounded-2xl p-6 shadow-sm border border-slate-100 hover:shadow-lg hover:border-indigo-200 transition-all duration-300">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-xl shadow-lg shadow-indigo-500/30">
                  <BuildingOffice2Icon className="h-6 w-6 text-white" />
                </div>
                <span className="flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                  <ArrowTrendingUpIcon className="h-3 w-3" />
                  +2 this month
                </span>
              </div>
              <p className="text-sm font-medium text-slate-500">Total Tenants</p>
              <p className="text-3xl font-bold text-slate-900 mt-1">{stats?.tenants.total || 0}</p>
              <div className="flex gap-3 mt-3 text-xs">
                <span className="flex items-center gap-1 text-emerald-600">
                  <CheckCircleIcon className="h-3 w-3" />
                  {stats?.tenants.active} active
                </span>
                <span className="flex items-center gap-1 text-blue-600">
                  <ClockIcon className="h-3 w-3" />
                  {stats?.tenants.trial} trial
                </span>
              </div>
            </div>
          </div>

          {/* Users Card */}
          <div className="group relative bg-white rounded-2xl p-6 shadow-sm border border-slate-100 hover:shadow-lg hover:border-emerald-200 transition-all duration-300">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-teal-500/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl shadow-lg shadow-emerald-500/30">
                  <UserGroupIcon className="h-6 w-6 text-white" />
                </div>
                <span className="flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                  <ArrowTrendingUpIcon className="h-3 w-3" />
                  +{stats?.users.new_this_month} new
                </span>
              </div>
              <p className="text-sm font-medium text-slate-500">Total Users</p>
              <p className="text-3xl font-bold text-slate-900 mt-1">{stats?.users.total?.toLocaleString() || 0}</p>
              <div className="flex gap-3 mt-3 text-xs">
                <span className="flex items-center gap-1 text-emerald-600">
                  <GlobeAltIcon className="h-3 w-3" />
                  {stats?.users.active_today} online now
                </span>
              </div>
            </div>
          </div>

          {/* Revenue Card */}
          <div className="group relative bg-white rounded-2xl p-6 shadow-sm border border-slate-100 hover:shadow-lg hover:border-amber-200 transition-all duration-300">
            <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 to-orange-500/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl shadow-lg shadow-amber-500/30">
                  <CurrencyDollarIcon className="h-6 w-6 text-white" />
                </div>
                <span className="flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                  <ArrowTrendingUpIcon className="h-3 w-3" />
                  +{stats?.revenue.growth}%
                </span>
              </div>
              <p className="text-sm font-medium text-slate-500">Monthly Revenue</p>
              <p className="text-3xl font-bold text-slate-900 mt-1">
                ${stats?.revenue.mrr?.toLocaleString() || 0}
              </p>
              <div className="flex gap-3 mt-3 text-xs">
                <span className="text-slate-500">
                  ARR: ${stats?.revenue.arr?.toLocaleString() || 0}
                </span>
              </div>
            </div>
          </div>

          {/* Systems Card */}
          <div className="group relative bg-white rounded-2xl p-6 shadow-sm border border-slate-100 hover:shadow-lg hover:border-purple-200 transition-all duration-300">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-pink-500/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl shadow-lg shadow-purple-500/30">
                  <ServerStackIcon className="h-6 w-6 text-white" />
                </div>
                <span className="flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                  {stats?.systems.sync_healthy}% healthy
                </span>
              </div>
              <p className="text-sm font-medium text-slate-500">Connected Systems</p>
              <p className="text-3xl font-bold text-slate-900 mt-1">{stats?.systems.connected || 0}</p>
              <div className="mt-3">
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-500"
                    style={{ width: `${stats?.systems.sync_healthy || 0}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Tenants List - Takes 2 columns */}
          <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="p-6 border-b border-slate-100">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">All Tenants</h2>
                  <p className="text-sm text-slate-500">Manage your platform tenants</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Search tenants..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent w-48 md:w-64 transition-all"
                    />
                  </div>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  >
                    <option value="">All Status</option>
                    <option value="active">Active</option>
                    <option value="trial">Trial</option>
                    <option value="suspended">Suspended</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-50/50">
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Organization
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Tier
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Users
                    </th>
                    <th className="px-6 py-4 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredTenants.map((tenant) => {
                    const status = statusConfig[tenant.status] || statusConfig.pending;
                    const tier = tierConfig[tenant.tier] || tierConfig.starter;
                    const StatusIcon = status.icon;

                    return (
                      <tr key={tenant.id} className="group hover:bg-slate-50/50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className={clsx('w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center text-white font-bold shadow-md', tier.gradient)}>
                              {tenant.name.charAt(0)}
                            </div>
                            <div>
                              <p className="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors">
                                {tenant.name}
                              </p>
                              <p className="text-sm text-slate-500">{tenant.admin_email}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className={clsx('px-3 py-1 text-xs font-semibold rounded-full', tier.bgColor, tier.color)}>
                            {tier.label}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={clsx('inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full border', status.bgColor, status.color)}>
                            <StatusIcon className="h-3.5 w-3.5" />
                            {status.label}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <UserGroupIcon className="h-4 w-4 text-slate-400" />
                            <span className="font-medium text-slate-900">{tenant.users_count}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="relative inline-block">
                            <button
                              onClick={() => setSelectedTenant(selectedTenant === tenant.id ? null : tenant.id)}
                              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                            >
                              <EllipsisVerticalIcon className="h-5 w-5 text-slate-400" />
                            </button>
                            {selectedTenant === tenant.id && (
                              <div className="absolute right-0 mt-1 w-48 bg-white rounded-xl shadow-xl border border-slate-200 py-1 z-20 animate-fade-in">
                                <Link
                                  to={`/admin/tenants/${tenant.id}`}
                                  className="flex items-center gap-2 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                                >
                                  <PencilIcon className="h-4 w-4" />
                                  View Details
                                </Link>
                                {tenant.status === 'active' || tenant.status === 'trial' ? (
                                  <button
                                    onClick={() => handleSuspendTenant(tenant.id)}
                                    className="flex items-center gap-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 w-full transition-colors"
                                  >
                                    <PauseIcon className="h-4 w-4" />
                                    Suspend Tenant
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => handleActivateTenant(tenant.id)}
                                    className="flex items-center gap-2 px-4 py-2.5 text-sm text-emerald-600 hover:bg-emerald-50 w-full transition-colors"
                                  >
                                    <PlayIcon className="h-4 w-4" />
                                    Activate Tenant
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {filteredTenants.length === 0 && (
              <div className="text-center py-12">
                <BuildingOffice2Icon className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500">No tenants found</p>
              </div>
            )}
          </div>

          {/* Activity Feed */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="p-6 border-b border-slate-100">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">Recent Activity</h2>
                  <p className="text-sm text-slate-500">Platform events</p>
                </div>
                <button
                  onClick={() => toast.success('Opening all activities...')}
                  className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                >
                  View all
                </button>
              </div>
            </div>

            <div className="p-4 space-y-4">
              {activities.map((activity, idx) => (
                <div key={activity.id} className="flex gap-3 p-3 rounded-xl hover:bg-slate-50 transition-colors">
                  <div className={clsx(
                    'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0',
                    activity.type === 'tenant_created' && 'bg-indigo-100 text-indigo-600',
                    activity.type === 'payment' && 'bg-emerald-100 text-emerald-600',
                    activity.type === 'user_login' && 'bg-blue-100 text-blue-600',
                    activity.type === 'alert' && 'bg-amber-100 text-amber-600',
                  )}>
                    {activity.type === 'tenant_created' && <BuildingOffice2Icon className="h-5 w-5" />}
                    {activity.type === 'payment' && <CurrencyDollarIcon className="h-5 w-5" />}
                    {activity.type === 'user_login' && <UserGroupIcon className="h-5 w-5" />}
                    {activity.type === 'alert' && <ExclamationTriangleIcon className="h-5 w-5" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-900 font-medium">{activity.message}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{activity.time}</p>
                  </div>
                  <ChevronRightIcon className="h-5 w-5 text-slate-300 flex-shrink-0" />
                </div>
              ))}
            </div>

            {/* Quick Actions */}
            <div className="p-4 border-t border-slate-100 bg-slate-50/50">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Quick Actions</p>
              <div className="grid grid-cols-2 gap-2">
                <Link
                  to="/admin/onboard"
                  className="flex items-center gap-2 p-3 bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/50 transition-all text-sm font-medium text-slate-700"
                >
                  <PlusIcon className="h-4 w-4 text-indigo-600" />
                  Add Tenant
                </Link>
                <button
                  onClick={() => toast.success('Opening reports...')}
                  className="flex items-center gap-2 p-3 bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/50 transition-all text-sm font-medium text-slate-700"
                >
                  <ChartBarIcon className="h-4 w-4 text-indigo-600" />
                  Reports
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in { animation: fade-in 0.2s ease-out; }
      `}</style>
    </div>
  );
}

export default AdminDashboard;
