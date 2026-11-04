import { useQuery } from '@tanstack/react-query';
import {
  ChartBarIcon, ShieldCheckIcon, ExclamationTriangleIcon,
  ClockIcon, ArrowTrendingUpIcon, GlobeAltIcon,
} from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface ModuleHealth {
  module: string; health_score: number; total: number; open?: number;
  open_deficiencies?: number; open_issues?: number;
}

export function GRCAnalytics() {
  const { data: summary } = useQuery({
    queryKey: ['analytics-summary'],
    queryFn: () => api.get('/analytics/executive-summary').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data: moduleHealth } = useQuery({
    queryKey: ['analytics-module-health'],
    queryFn: () => api.get('/analytics/module-health').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data: controlEffectiveness } = useQuery({
    queryKey: ['analytics-control-effectiveness'],
    queryFn: () => api.get('/analytics/control-effectiveness').then(r => r.data),
  });

  const { data: issuesAging } = useQuery({
    queryKey: ['analytics-issues-aging'],
    queryFn: () => api.get('/analytics/issues-aging').then(r => r.data),
  });

  const { data: findingsBySeverity } = useQuery({
    queryKey: ['analytics-findings-severity'],
    queryFn: () => api.get('/analytics/audit-findings-by-severity').then(r => r.data),
  });

  const { data: violationsByModule } = useQuery({
    queryKey: ['analytics-violations-module'],
    queryFn: () => api.get('/analytics/violations-by-module').then(r => r.data),
  });

  const { data: kriTrend } = useQuery({
    queryKey: ['analytics-kri-trend'],
    queryFn: () => api.get('/analytics/kri-breach-trend').then(r => r.data),
  });

  const s = summary;
  const ce = controlEffectiveness;
  const ia = issuesAging;
  const modules: ModuleHealth[] = moduleHealth?.modules || [];

  const healthColor = (score: number) =>
    score >= 80 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : 'text-red-600';

  const healthBg = (score: number) =>
    score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : 'bg-red-500';

  const severityColors: Record<string, string> = {
    critical: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-yellow-500', low: 'bg-blue-500',
  };

  const agingBuckets = ia ? [
    { label: '0–7 days', value: ia.aging_buckets?.['0-7d'] || 0, color: 'bg-green-400' },
    { label: '8–30 days', value: ia.aging_buckets?.['8-30d'] || 0, color: 'bg-yellow-400' },
    { label: '31–90 days', value: ia.aging_buckets?.['31-90d'] || 0, color: 'bg-orange-400' },
    { label: '91–180 days', value: ia.aging_buckets?.['91-180d'] || 0, color: 'bg-red-400' },
    { label: '180+ days', value: ia.aging_buckets?.['180d+'] || 0, color: 'bg-red-700' },
  ] : [];

  const maxAging = Math.max(...agingBuckets.map(b => b.value), 1);

  return (
    <div className="space-y-6">
      <PageHeader
        title="GRC Analytics"
        subtitle="Cross-module intelligence, trends, and enterprise risk posture"
      />

      {/* Executive Summary KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Open Risks" value={s?.risk?.open ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={s?.risk?.open > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Critical Risks" value={s?.risk?.critical ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={s?.risk?.critical > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Open Conflicts" value={s?.access_conflicts?.open ?? '—'} icon={ShieldCheckIcon} iconBgColor={s?.access_conflicts?.open > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Open Findings" value={s?.audit?.open_findings ?? '—'} icon={ChartBarIcon} iconBgColor={s?.audit?.open_findings > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Control Deficiencies" value={s?.controls?.open_deficiencies ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={s?.controls?.open_deficiencies > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="CCM Failures (30d)" value={s?.controls?.ccm_failures_30d ?? '—'} icon={ClockIcon} iconBgColor={s?.controls?.ccm_failures_30d > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Overdue Issues" value={s?.issues?.overdue ?? '—'} icon={ClockIcon} iconBgColor={s?.issues?.overdue > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        <StatCard title="Open Fraud Cases" value={s?.fraud?.open_cases ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={s?.fraud?.open_cases > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Module Health Scores */}
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <GlobeAltIcon className="h-4 w-4 text-indigo-500" />
            Module Health Scores
          </h2>
          <div className="space-y-3">
            {modules.map(m => (
              <div key={m.module}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-gray-700">{m.module}</span>
                  <span className={`text-sm font-bold ${healthColor(m.health_score)}`}>{m.health_score}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className={`h-2 rounded-full ${healthBg(m.health_score)} transition-all`} style={{ width: `${m.health_score}%` }} />
                </div>
                <div className="flex justify-between text-xs text-gray-400 mt-0.5">
                  <span>{m.total} total</span>
                  <span>{m.open || m.open_deficiencies || m.open_issues || 0} open</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Control Effectiveness */}
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <ShieldCheckIcon className="h-4 w-4 text-green-500" />
            Control Effectiveness
          </h2>
          {ce ? (
            <div className="space-y-4">
              <div className="text-center">
                <div className={`text-3xl font-bold ${healthColor(ce.effectiveness_rate)}`}>{ce.effectiveness_rate}%</div>
                <div className="text-xs text-gray-500 mt-1">Effective controls</div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Effective', value: ce.effective, color: 'text-green-600', bg: 'bg-green-50' },
                  { label: 'Partially', value: ce.partially_effective, color: 'text-yellow-600', bg: 'bg-yellow-50' },
                  { label: 'Ineffective', value: ce.ineffective, color: 'text-red-600', bg: 'bg-red-50' },
                  { label: 'Not Tested', value: ce.not_tested, color: 'text-gray-500', bg: 'bg-gray-50' },
                ].map(item => (
                  <div key={item.label} className={`${item.bg} rounded-xl p-3 text-center`}>
                    <div className={`text-xl font-bold ${item.color}`}>{item.value}</div>
                    <div className="text-xs text-gray-500">{item.label}</div>
                  </div>
                ))}
              </div>
              <div className="text-xs text-gray-500 text-center">{ce.total_controls} total controls</div>
            </div>
          ) : <div className="text-xs text-gray-400 text-center py-8">Loading...</div>}
        </Card>

        {/* Issue Aging */}
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <ClockIcon className="h-4 w-4 text-orange-500" />
            Issue Age Distribution
          </h2>
          {ia ? (
            <div className="space-y-3">
              <div className="text-xs text-gray-500 mb-2">{ia.total_open} open issues</div>
              {agingBuckets.map(b => (
                <div key={b.label} className="flex items-center gap-3">
                  <div className="w-20 text-xs text-gray-600">{b.label}</div>
                  <div className="flex-1 bg-gray-100 rounded-full h-4 relative overflow-hidden">
                    <div className={`h-4 rounded-full ${b.color} transition-all`} style={{ width: `${Math.round(b.value / maxAging * 100)}%` }} />
                  </div>
                  <div className="w-6 text-xs font-semibold text-gray-700 text-right">{b.value}</div>
                </div>
              ))}
            </div>
          ) : <div className="text-xs text-gray-400 text-center py-8">Loading...</div>}
        </Card>

        {/* Audit Findings by Severity */}
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <ChartBarIcon className="h-4 w-4 text-purple-500" />
            Open Audit Findings by Severity
          </h2>
          {findingsBySeverity?.by_severity?.length > 0 ? (
            <div className="space-y-3">
              {findingsBySeverity.by_severity.map((item: any) => {
                const max = Math.max(...findingsBySeverity.by_severity.map((x: any) => x.count), 1);
                return (
                  <div key={item.severity} className="flex items-center gap-3">
                    <div className="w-20 text-xs text-gray-600 capitalize">{item.severity}</div>
                    <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                      <div className={`h-4 rounded-full ${severityColors[item.severity] || 'bg-gray-400'}`}
                        style={{ width: `${Math.round(item.count / max * 100)}%` }} />
                    </div>
                    <div className="w-6 text-xs font-semibold text-gray-700 text-right">{item.count}</div>
                  </div>
                );
              })}
            </div>
          ) : <div className="text-xs text-gray-400 text-center py-8">No open findings</div>}
        </Card>

        {/* Access Conflicts by Category */}
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <ShieldCheckIcon className="h-4 w-4 text-red-500" />
            Access Conflicts by Category
          </h2>
          {violationsByModule?.by_category?.length > 0 ? (
            <div className="space-y-2">
              {violationsByModule.by_category.map((item: any) => {
                const max = Math.max(...violationsByModule.by_category.map((x: any) => x.count), 1);
                return (
                  <div key={item.category} className="flex items-center gap-3">
                    <div className="w-16 text-xs text-gray-600 uppercase">{item.category}</div>
                    <div className="flex-1 bg-gray-100 rounded-full h-3 overflow-hidden">
                      <div className="h-3 rounded-full bg-indigo-500" style={{ width: `${Math.round(item.count / max * 100)}%` }} />
                    </div>
                    <div className="w-6 text-xs font-semibold text-gray-700 text-right">{item.count}</div>
                  </div>
                );
              })}
            </div>
          ) : <div className="text-xs text-gray-400 text-center py-8">No violations data</div>}
        </Card>

        {/* KRI Breach Trend */}
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <ArrowTrendingUpIcon className="h-4 w-4 text-orange-500" />
            Risk Indicator Breach Trend (6 months)
          </h2>
          {kriTrend?.trend?.length > 0 ? (
            <div className="flex items-end gap-2 h-28">
              {kriTrend.trend.map((item: any) => {
                const max = Math.max(...kriTrend.trend.map((x: any) => x.breaches), 1);
                const height = item.breaches > 0 ? Math.max(Math.round(item.breaches / max * 100), 8) : 4;
                return (
                  <div key={item.period} className="flex-1 flex flex-col items-center gap-1">
                    <div className="text-xs font-semibold text-gray-700">{item.breaches}</div>
                    <div className="w-full flex items-end justify-center" style={{ height: '72px' }}>
                      <div
                        className={`w-full rounded-t ${item.breaches > 0 ? 'bg-orange-400' : 'bg-gray-200'}`}
                        style={{ height: `${height}%` }}
                      />
                    </div>
                    <div className="text-xs text-gray-400 text-center">{item.period.split(' ')[0]}</div>
                  </div>
                );
              })}
            </div>
          ) : <div className="text-xs text-gray-400 text-center py-8">No breach data</div>}
        </Card>
      </div>
    </div>
  );
}
