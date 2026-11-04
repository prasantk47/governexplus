import { useQuery } from '@tanstack/react-query';
import {
  GlobeAltIcon,
  FireIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import { firefighterApi } from '../../services/api';

interface RegionalKPI {
  ffids: number;
  active_sessions: number;
  pending_reviews: number;
}

interface DashboardData {
  global_kpis: {
    total_ffids: number;
    active_ffids: number;
    total_sessions_all_time: number;
    active_sessions_now: number;
    pending_log_reviews: number;
    break_glass_sessions: number;
    certifications_due: number;
    ffids_without_controller: number;
  };
  by_region: Record<string, RegionalKPI>;
}

const regionColors: Record<string, string> = {
  APAC: 'from-blue-500 to-blue-600',
  EMEA: 'from-purple-500 to-purple-600',
  AMER: 'from-green-500 to-green-600',
  MEA: 'from-orange-500 to-orange-600',
  GLOBAL: 'from-indigo-500 to-indigo-600',
  UNASSIGNED: 'from-gray-400 to-gray-500',
};

const regionLabels: Record<string, string> = {
  APAC: 'Asia Pacific',
  EMEA: 'Europe, Middle East & Africa',
  AMER: 'Americas',
  MEA: 'Middle East & Africa',
  GLOBAL: 'Global',
  UNASSIGNED: 'Unassigned',
};

export function RegionalDashboard() {
  const { data, isLoading, error } = useQuery<DashboardData>({
    queryKey: ['ff-regional-dashboard'],
    queryFn: () => firefighterApi.getRegionalDashboard().then(r => r.data),
    refetchInterval: 30000,
  });

  const { data: ffidsData } = useQuery({
    queryKey: ['ff-regional-ffids'],
    queryFn: () => firefighterApi.listFirefighters().then(r => r.data),
  });
  const allFFIDs: any[] = Array.isArray(ffidsData) ? ffidsData : (ffidsData as any)?.firefighter_ids || [];

  const global = data?.global_kpis;
  const regions = data?.by_region || {};

  return (
    <div className="space-y-6">
      <PageHeader
        title="Regional EAM Dashboard"
        subtitle="Enterprise firefighter monitoring with regional breakdown — refreshes every 30s"
      />

      {/* Global KPIs */}
      {isLoading ? (
        <div className="text-sm text-gray-400 py-10 text-center">Loading dashboard...</div>
      ) : error ? (
        <div className="text-sm text-red-500 py-10 text-center">Failed to load dashboard data</div>
      ) : global && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard
              title="Active FFIDs"
              value={global.active_ffids}
              icon={FireIcon}
              iconBgColor="stat-icon-orange"
              iconColor=""
            />
            <StatCard
              title="Active Sessions"
              value={global.active_sessions_now}
              icon={ClockIcon}
              iconBgColor="stat-icon-blue"
              iconColor=""
            />
            <StatCard
              title="Pending Log Reviews"
              value={global.pending_log_reviews}
              icon={ExclamationTriangleIcon}
              iconBgColor={global.pending_log_reviews > 0 ? 'stat-icon-orange' : 'stat-icon-green'}
              iconColor=""
            />
            <StatCard
              title="Break-Glass Sessions"
              value={global.break_glass_sessions}
              icon={ShieldExclamationIcon}
              iconBgColor={global.break_glass_sessions > 0 ? 'stat-icon-red' : 'stat-icon-green'}
              iconColor=""
            />
          </div>

          {/* Governance Alerts */}
          {(global.certifications_due > 0 || global.ffids_without_controller > 0) && (
            <Card>
              <h2 className="text-sm font-semibold text-gray-900 mb-3">Governance Alerts</h2>
              <div className="space-y-2">
                {global.certifications_due > 0 && (
                  <div className="flex items-center gap-3 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                    <ClockIcon className="h-4 w-4 text-yellow-600" />
                    <span className="text-sm text-yellow-700">
                      <strong>{global.certifications_due}</strong> FFID(s) are due for periodic certification review
                    </span>
                    <a href="/privileged-access/certification" className="ml-auto text-xs text-yellow-700 underline font-medium">Review now</a>
                  </div>
                )}
                {global.ffids_without_controller > 0 && (
                  <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg p-3">
                    <ExclamationTriangleIcon className="h-4 w-4 text-red-600" />
                    <span className="text-sm text-red-700">
                      <strong>{global.ffids_without_controller}</strong> active FFID(s) have no controller assigned — EAM policy violation
                    </span>
                    <a href="/privileged-access/registry" className="ml-auto text-xs text-red-700 underline font-medium">Fix now</a>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Regional Breakdown */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(regions).map(([region, kpi]) => {
              const gradient = regionColors[region] || 'from-gray-400 to-gray-500';
              const label = regionLabels[region] || region;
              const regionFFIDs = allFFIDs.filter(f => f.region === region);
              const noController = regionFFIDs.filter(f => f.status === 'active' && !f.controller_id).length;
              return (
                <Card key={region} padding="none" className="overflow-hidden">
                  <div className={`bg-gradient-to-r ${gradient} px-5 py-4`}>
                    <div className="flex items-center gap-2">
                      <GlobeAltIcon className="h-5 w-5 text-white/80" />
                      <div>
                        <div className="text-white font-semibold text-sm">{region}</div>
                        <div className="text-white/70 text-xs">{label}</div>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 space-y-3">
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div>
                        <div className="text-xl font-bold text-gray-900">{kpi.ffids}</div>
                        <div className="text-xs text-gray-500">FFIDs</div>
                      </div>
                      <div>
                        <div className={`text-xl font-bold ${kpi.active_sessions > 0 ? 'text-green-600' : 'text-gray-400'}`}>
                          {kpi.active_sessions}
                        </div>
                        <div className="text-xs text-gray-500">Active</div>
                      </div>
                      <div>
                        <div className={`text-xl font-bold ${kpi.pending_reviews > 0 ? 'text-orange-600' : 'text-gray-400'}`}>
                          {kpi.pending_reviews}
                        </div>
                        <div className="text-xs text-gray-500">Pending</div>
                      </div>
                    </div>

                    {/* Per-FFID list */}
                    {regionFFIDs.length > 0 && (
                      <div className="border-t border-white/20 pt-3 space-y-1.5">
                        {regionFFIDs.map(f => (
                          <div key={f.ffid} className="flex items-center justify-between text-xs">
                            <span className="font-mono text-indigo-700 font-medium">{f.ffid}</span>
                            <div className="flex items-center gap-1.5">
                              {f.in_use && <span className="inline-block h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />}
                              <span className={`text-xs ${f.in_use ? 'text-green-600' : 'text-gray-400'}`}>
                                {f.in_use ? 'In Use' : f.status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {noController > 0 && (
                      <div className="text-xs text-red-600 bg-red-50 rounded-lg px-2 py-1 flex items-center gap-1">
                        <ExclamationTriangleIcon className="h-3 w-3" />
                        {noController} FFID(s) without controller
                      </div>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>

          {/* Global summary footer */}
          <Card>
            <h2 className="text-sm font-semibold text-gray-900 mb-3">Global Summary</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
              {[
                { label: 'Total FFIDs Registered', value: global.total_ffids },
                { label: 'Total Sessions (All Time)', value: global.total_sessions_all_time },
                { label: 'Break-Glass Events', value: global.break_glass_sessions },
                { label: 'Certifications Due', value: global.certifications_due },
              ].map(item => (
                <div key={item.label} className="bg-gray-50/60 rounded-xl p-3">
                  <div className="text-2xl font-bold text-gray-900">{item.value}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{item.label}</div>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
