/**
 * GovernexPlus Predictive Risk Forecasting
 * Forecast risk trends, seasonal patterns, peer anomalies
 */
import { useState } from 'react';
import {
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  CalendarDaysIcon,
  UserGroupIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';

interface ForecastPoint { month: string; actual?: number; forecast?: number; }
interface ViolationForecast { category: string; current: number; predicted30d: number; trend: 'up' | 'down' | 'stable'; confidence: number; }
interface SeasonalPattern { period: string; riskFactor: string; severity: 'high' | 'medium' | 'low'; description: string; }
interface PeerAnomaly { user: string; department: string; deviationScore: number; detail: string; accessCount: number; peerAvg: number; }

const TREND_DATA: ForecastPoint[] = [
  { month: 'May', actual: 42 }, { month: 'Jun', actual: 38 }, { month: 'Jul', actual: 45 },
  { month: 'Aug', actual: 51 }, { month: 'Sep', actual: 48 }, { month: 'Oct', actual: 55 },
  { month: 'Nov', forecast: 58 }, { month: 'Dec', forecast: 65 }, { month: 'Jan', forecast: 52 },
];

const VIOLATION_FORECASTS: ViolationForecast[] = [
  { category: 'Financial (FI)', current: 18, predicted30d: 22, trend: 'up', confidence: 87 },
  { category: 'Procurement (MM)', current: 12, predicted30d: 10, trend: 'down', confidence: 82 },
  { category: 'Sales (SD)', current: 8, predicted30d: 11, trend: 'up', confidence: 78 },
  { category: 'HR/Payroll', current: 5, predicted30d: 5, trend: 'stable', confidence: 91 },
  { category: 'Basis Admin', current: 7, predicted30d: 9, trend: 'up', confidence: 74 },
  { category: 'Warehouse (WM)', current: 3, predicted30d: 3, trend: 'stable', confidence: 88 },
];

const SEASONAL: SeasonalPattern[] = [
  { period: 'Q4 Close (Dec)', riskFactor: 'Year-end close pressure', severity: 'high', description: 'Historically 40% spike in firefighter requests and SoD exceptions during year-end close. Additional temporary access grants increase violation surface.' },
  { period: 'Q1 Hiring (Jan-Feb)', riskFactor: 'New employee onboarding', severity: 'medium', description: 'Mass onboarding creates 15-20 new access requests weekly. Role copy from existing users propagates violations to new hires.' },
  { period: 'Mid-Year Review (Jul)', riskFactor: 'Certification campaigns', severity: 'medium', description: 'Annual certification drives 60% of access removals but also rubber-stamp approvals on complex roles.' },
  { period: 'Budget Season (Sep-Oct)', riskFactor: 'Cross-department access', severity: 'low', description: 'Finance users request temporary access to budget planning modules. Short-lived but creates temporary SoD conflicts.' },
];

const ANOMALIES: PeerAnomaly[] = [
  { user: 'John Miller', department: 'Finance', deviationScore: 3.2, detail: 'Has 12 roles vs department average of 5. 3 high-risk SoD conflicts.', accessCount: 12, peerAvg: 5 },
  { user: 'Sarah Chen', department: 'Procurement', deviationScore: 2.8, detail: 'Uses 23 unique tcodes vs peer average of 9. Several unused high-privilege tcodes.', accessCount: 23, peerAvg: 9 },
  { user: 'Mike Torres', department: 'IT', deviationScore: 2.1, detail: 'SAP_ALL profile assigned. Only IT admin with full system access.', accessCount: 1, peerAvg: 0 },
  { user: 'Lisa Park', department: 'HR', deviationScore: 1.9, detail: 'Access to payroll AND employee master. Only HR user with both.', accessCount: 8, peerAvg: 4 },
];

const trendIcons: Record<string, { icon: typeof ArrowTrendingUpIcon; color: string }> = {
  up: { icon: ArrowTrendingUpIcon, color: 'text-red-500' },
  down: { icon: ArrowTrendingDownIcon, color: 'text-emerald-500' },
  stable: { icon: ChartBarIcon, color: 'text-gray-400' },
};

export function PredictiveRisk() {
  const [forecastDays, setForecastDays] = useState<30 | 60 | 90>(30);
  const currentScore = 55;
  const forecastScore = forecastDays === 30 ? 58 : forecastDays === 60 ? 62 : 65;
  const maxVal = Math.max(...TREND_DATA.map(d => d.actual || d.forecast || 0));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Predictive Risk Forecasting</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">AI-powered risk trend analysis, seasonal patterns, and peer anomaly detection</p>
        </div>
        <div className="flex gap-1 bg-gray-100 dark:bg-slate-700 rounded-lg p-1">
          {([30, 60, 90] as const).map(d => (
            <button key={d} onClick={() => setForecastDays(d)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${forecastDays === d ? 'bg-white dark:bg-slate-600 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 dark:text-gray-400'}`}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Current Risk Score', value: currentScore, sub: 'Active violations', color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-100 dark:bg-amber-900/30', icon: ExclamationTriangleIcon },
          { label: `${forecastDays}-Day Forecast`, value: forecastScore, sub: `${forecastScore > currentScore ? '+' : ''}${forecastScore - currentScore} from today`, color: forecastScore > currentScore ? 'text-red-600 dark:text-red-400' : 'text-emerald-600', bg: forecastScore > currentScore ? 'bg-red-100 dark:bg-red-900/30' : 'bg-emerald-100', icon: ArrowTrendingUpIcon },
          { label: 'Trend Direction', value: 'Rising', sub: 'Based on hiring + role changes', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/30', icon: ArrowTrendingUpIcon },
          { label: 'Forecast Confidence', value: '84%', sub: 'Based on 6 months data', color: 'text-indigo-600 dark:text-indigo-400', bg: 'bg-indigo-100 dark:bg-indigo-900/30', icon: SparklesIcon },
        ].map(s => (
          <div key={s.label} className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-gray-200 dark:border-slate-700">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${s.bg} ${s.color}`}><s.icon className="h-5 w-5" /></div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{s.value}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{s.label}</p>
                <p className="text-xs text-gray-400 mt-0.5">{s.sub}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Risk Score Trend & Forecast</h3>
        <div className="flex items-end gap-3 h-48">
          {TREND_DATA.map((d, i) => {
            const val = d.actual || d.forecast || 0;
            const h = (val / maxVal) * 100;
            return (
              <div key={d.month} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{val}</span>
                <div className={`w-full rounded-t-md transition-all ${d.forecast ? 'bg-indigo-300 dark:bg-indigo-600 border-2 border-dashed border-indigo-400' : 'bg-indigo-500'}`}
                  style={{ height: `${h}%`, minHeight: 8 }} />
                <span className="text-xs text-gray-500">{d.month}</span>
              </div>
            );
          })}
        </div>
        <div className="flex gap-4 mt-3 text-xs text-gray-500">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-indigo-500" /> Actual</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-indigo-300 border border-dashed border-indigo-400" /> Forecast</span>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Violation Forecast */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
          <div className="p-5 border-b border-gray-200 dark:border-slate-700">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <ChartBarIcon className="h-4 w-4 text-indigo-500" /> Violation Forecast by Category
            </h3>
          </div>
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-slate-700/50">
              <tr>{['Category', 'Current', '30d Forecast', 'Trend', 'Confidence'].map(h => <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
              {VIOLATION_FORECASTS.map(vf => {
                const t = trendIcons[vf.trend];
                return (
                  <tr key={vf.category}>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{vf.category}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{vf.current}</td>
                    <td className="px-4 py-3 text-sm font-semibold text-gray-900 dark:text-white">{vf.predicted30d}</td>
                    <td className="px-4 py-3"><t.icon className={`h-4 w-4 ${t.color}`} /></td>
                    <td className="px-4 py-3 text-xs text-gray-500">{vf.confidence}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Seasonal Patterns */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <CalendarDaysIcon className="h-4 w-4 text-indigo-500" /> Seasonal Risk Patterns
          </h3>
          <div className="space-y-3">
            {SEASONAL.map(s => (
              <div key={s.period} className="p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold text-gray-900 dark:text-white">{s.period}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${s.severity === 'high' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' : s.severity === 'medium' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'}`}>{s.severity}</span>
                </div>
                <p className="text-xs text-indigo-600 dark:text-indigo-400 font-medium">{s.riskFactor}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{s.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Peer Anomalies */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        <div className="p-5 border-b border-gray-200 dark:border-slate-700">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <UserGroupIcon className="h-4 w-4 text-indigo-500" /> Peer Group Anomalies
          </h3>
          <p className="text-xs text-gray-500 mt-1">Users whose access patterns deviate significantly from department peers</p>
        </div>
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-slate-700/50">
            <tr>{['User', 'Department', 'Deviation', 'User Access', 'Peer Avg', 'Detail'].map(h => <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
            {ANOMALIES.map(a => (
              <tr key={a.user}>
                <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{a.user}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{a.department}</td>
                <td className="px-4 py-3">
                  <span className={`text-sm font-bold ${a.deviationScore >= 3 ? 'text-red-600 dark:text-red-400' : a.deviationScore >= 2 ? 'text-amber-600 dark:text-amber-400' : 'text-gray-600'}`}>
                    {a.deviationScore.toFixed(1)}σ
                  </span>
                </td>
                <td className="px-4 py-3 text-sm font-semibold text-gray-900 dark:text-white">{a.accessCount}</td>
                <td className="px-4 py-3 text-sm text-gray-500">{a.peerAvg}</td>
                <td className="px-4 py-3 text-xs text-gray-600 dark:text-gray-400 max-w-[250px]">{a.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
