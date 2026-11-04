import { useQuery } from '@tanstack/react-query';
import { ChartBarIcon, ShieldCheckIcon, ExclamationTriangleIcon, BanknotesIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

export function BoardDashboard() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ['board-executive-summary'],
    queryFn: () => api.get('/board-reporting/executive-summary').then(r => r.data),
    refetchInterval: 120000,
  });

  const { data: trendData } = useQuery({
    queryKey: ['board-trend-data'],
    queryFn: () => api.get('/board-reporting/trend-data?days=90').then(r => r.data),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Board & Executive Dashboard" subtitle="Cross-module GRC executive summary" />
        <div className="text-xs text-gray-400 text-center py-16">Loading executive summary…</div>
      </div>
    );
  }

  const risk = summary?.risk || {};
  const access = summary?.access_risk || {};
  const audit = summary?.audit || {};
  const sox = summary?.sox || {};
  const privacy = summary?.privacy || {};
  const oploss = summary?.operational_loss || {};

  const hasAlerts = (risk.critical > 0) || (sox.material_weaknesses > 0) || (privacy.open_breaches > 0) || (privacy.overdue_dsars > 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Board & Executive Dashboard"
        subtitle={`Cross-module GRC snapshot · As of ${summary?.as_of ? new Date(summary.as_of).toLocaleString() : 'now'}`}
      />

      {hasAlerts && (
        <div className="grid gap-2">
          {risk.critical > 0 && (
            <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-xl">
              <ExclamationTriangleIcon className="h-5 w-5 text-red-500 flex-shrink-0" />
              <span className="text-sm text-red-800 font-medium">{risk.critical} critical enterprise risk(s) require board attention</span>
            </div>
          )}
          {sox.material_weaknesses > 0 && (
            <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-xl">
              <ExclamationTriangleIcon className="h-5 w-5 text-red-500 flex-shrink-0" />
              <span className="text-sm text-red-800 font-medium">{sox.material_weaknesses} SOX material weakness(es) identified</span>
            </div>
          )}
          {privacy.open_breaches > 0 && (
            <div className="flex items-center gap-3 p-3 bg-orange-50 border border-orange-200 rounded-xl">
              <ExclamationTriangleIcon className="h-5 w-5 text-orange-500 flex-shrink-0" />
              <span className="text-sm text-orange-800 font-medium">{privacy.open_breaches} open data breach incident(s)</span>
            </div>
          )}
          {privacy.overdue_dsars > 0 && (
            <div className="flex items-center gap-3 p-3 bg-orange-50 border border-orange-200 rounded-xl">
              <ExclamationTriangleIcon className="h-5 w-5 text-orange-500 flex-shrink-0" />
              <span className="text-sm text-orange-800 font-medium">{privacy.overdue_dsars} overdue DSAR request(s) — GDPR 30-day deadline</span>
            </div>
          )}
        </div>
      )}

      {/* Risk Section */}
      <div>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Enterprise Risk</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard title="Total Risks" value={risk.total_risks ?? '—'} icon={ChartBarIcon} iconBgColor="stat-icon-blue" iconColor="" />
          <StatCard title="Critical" value={risk.critical ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={risk.critical > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
          <StatCard title="High" value={risk.high ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={risk.high > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
          <StatCard title="KRIs in Breach" value={risk.kris_in_breach ?? '—'} icon={ChartBarIcon} iconBgColor={risk.kris_in_breach > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        </div>
      </div>

      {/* Access Risk Section */}
      <div>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Access & SoD Risk</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard title="Open Violations" value={access.open_violations ?? '—'} icon={ShieldCheckIcon} iconBgColor={access.open_violations > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
          <StatCard title="Critical Violations" value={access.critical_violations ?? '—'} icon={ShieldCheckIcon} iconBgColor={access.critical_violations > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
          <StatCard title="Open Findings" value={audit.open_findings ?? '—'} icon={ChartBarIcon} iconBgColor={audit.open_findings > 0 ? 'stat-icon-orange' : 'stat-icon-green'} iconColor="" />
          <StatCard title="Critical Findings" value={audit.critical_findings ?? '—'} icon={ExclamationTriangleIcon} iconBgColor={audit.critical_findings > 0 ? 'stat-icon-red' : 'stat-icon-green'} iconColor="" />
        </div>
      </div>

      {/* SOX & Privacy */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-4">SOX / ICFR Status</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">Key Controls</span>
              <span className="text-xs font-semibold text-gray-900">{sox.key_controls ?? '—'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">Material Weaknesses</span>
              <span className={`text-xs font-bold ${sox.material_weaknesses > 0 ? 'text-red-600' : 'text-green-600'}`}>{sox.material_weaknesses ?? '—'}</span>
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Privacy & Data Protection</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">Open Breaches</span>
              <span className={`text-xs font-bold ${privacy.open_breaches > 0 ? 'text-red-600' : 'text-green-600'}`}>{privacy.open_breaches ?? '—'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">Overdue DSARs</span>
              <span className={`text-xs font-bold ${privacy.overdue_dsars > 0 ? 'text-orange-600' : 'text-green-600'}`}>{privacy.overdue_dsars ?? '—'}</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Operational Loss */}
      <Card>
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Operational Loss (Last 30 Days)</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-xl font-bold text-gray-900">{oploss.incidents_30d ?? '—'}</div>
            <div className="text-xs text-gray-500 mt-0.5">Incidents</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-red-600">
              {oploss.gross_loss_30d != null ? `$${Number(oploss.gross_loss_30d).toLocaleString()}` : '—'}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">Gross Loss</div>
          </div>
        </div>
      </Card>

      {trendData?.buckets && trendData.buckets.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-4">90-Day Trend</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead><tr className="border-b border-gray-100">
                {['Week', 'New Risks', 'Violations Detected'].map(h => (
                  <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                ))}
              </tr></thead>
              <tbody className="divide-y divide-gray-50">
                {trendData.buckets.slice(-8).map((b: any) => (
                  <tr key={b.week_start}>
                    <td className="py-1.5 pr-4 text-xs text-gray-600">{b.week_start}</td>
                    <td className="py-1.5 pr-4 text-xs font-medium text-gray-900">{b.risks_created}</td>
                    <td className="py-1.5 pr-4 text-xs font-medium text-orange-600">{b.violations_detected}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
