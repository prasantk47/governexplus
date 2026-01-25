/**
 * Predictive Analytics Page
 * Risk predictions, trends analysis, and forecasting
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
  UserGroupIcon,
  ShieldCheckIcon,
  ClockIcon,
  LightBulbIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import api from '../../services/api';

export function PredictiveAnalytics() {
  const [timeRange, setTimeRange] = useState(30);

  // Fetch risk distribution
  const { data: riskDistribution } = useQuery({
    queryKey: ['riskDistribution'],
    queryFn: async () => {
      const response = await api.get('/ml/analytics/risk-distribution');
      return response.data;
    },
  });

  // Fetch trends
  const { data: trendsData } = useQuery({
    queryKey: ['mlTrends', timeRange],
    queryFn: async () => {
      const response = await api.get('/ml/analytics/trends', {
        params: { days: timeRange }
      });
      return response.data;
    },
  });

  // Fetch predictions summary
  const { data: predictionsSummary } = useQuery({
    queryKey: ['predictionsSummary'],
    queryFn: async () => {
      const response = await api.get('/ml/analytics/predictions-summary');
      return response.data;
    },
  });

  // Fetch advanced statistics
  const { data: advancedStats } = useQuery({
    queryKey: ['advancedMLStats'],
    queryFn: async () => {
      const response = await api.get('/ml/statistics/advanced');
      return response.data;
    },
  });

  const distribution = riskDistribution?.distribution || {};
  const trends = trendsData?.trends || [];

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'critical': return 'bg-red-500';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      default: return 'bg-green-500';
    }
  };

  const getRiskTextColor = (level: string) => {
    switch (level) {
      case 'critical': return 'text-red-600';
      case 'high': return 'text-orange-600';
      case 'medium': return 'text-yellow-600';
      default: return 'text-green-600';
    }
  };

  // Calculate max values for chart scaling
  const maxRiskScore = Math.max(...trends.map((t: any) => t.avg_risk_score), 60);
  const maxAnomalies = Math.max(...trends.map((t: any) => t.anomalies_detected), 30);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <ChartBarIcon className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Predictive Analytics</h1>
            <p className="text-sm text-gray-500">Risk predictions, trends, and forecasting</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="border border-gray-300 rounded-lg text-sm px-3 py-2"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={60}>Last 60 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <Link to="/ml" className="btn-secondary">
            Back to ML Dashboard
          </Link>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <ChartBarIcon className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Avg Risk Score</p>
              <p className="text-2xl font-bold text-gray-900">{riskDistribution?.avg_risk_score || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <UserGroupIcon className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Total Users</p>
              <p className="text-2xl font-bold text-gray-900">{riskDistribution?.total_users?.toLocaleString() || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <ShieldCheckIcon className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Predictions Today</p>
              <p className="text-2xl font-bold text-gray-900">{predictionsSummary?.today?.total_predictions?.toLocaleString() || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <ExclamationTriangleIcon className="h-5 w-5 text-orange-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Anomalies Today</p>
              <p className="text-2xl font-bold text-orange-600">{predictionsSummary?.today?.anomaly_detections || 0}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Distribution */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-medium text-gray-900">Risk Distribution</h2>
          </div>
          <div className="p-4">
            {/* Visual Bar Chart */}
            <div className="space-y-4">
              {Object.entries(distribution).map(([level, data]: [string, any]) => (
                <div key={level}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700 capitalize">{level}</span>
                    <span className="text-sm text-gray-500">{data.count} ({data.percentage}%)</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-4">
                    <div
                      className={clsx('h-4 rounded-full', getRiskColor(level))}
                      style={{ width: `${data.percentage}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">Score range: {data.range}</p>
                </div>
              ))}
            </div>

            {/* Summary Stats */}
            <div className="mt-6 pt-4 border-t border-gray-200 grid grid-cols-2 gap-4">
              <div className="text-center">
                <p className="text-xl font-bold text-gray-900">{riskDistribution?.avg_risk_score || 0}</p>
                <p className="text-xs text-gray-500">Average Score</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold text-gray-900">{riskDistribution?.median_risk_score || 0}</p>
                <p className="text-xs text-gray-500">Median Score</p>
              </div>
            </div>
          </div>
        </div>

        {/* Risk Trend Chart */}
        <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-900">Risk Trend Over Time</h2>
            {trendsData?.summary && (
              <span className={clsx(
                'flex items-center gap-1 text-sm font-medium',
                trendsData.summary.risk_change < 0 ? 'text-green-600' : trendsData.summary.risk_change > 0 ? 'text-red-600' : 'text-gray-600'
              )}>
                {trendsData.summary.risk_change < 0 ? (
                  <ArrowTrendingDownIcon className="h-4 w-4" />
                ) : trendsData.summary.risk_change > 0 ? (
                  <ArrowTrendingUpIcon className="h-4 w-4" />
                ) : null}
                {trendsData.summary.risk_change > 0 ? '+' : ''}{trendsData.summary.risk_change}
              </span>
            )}
          </div>
          <div className="p-4">
            {/* Simple Line Chart using divs */}
            <div className="h-48 flex items-end gap-1">
              {trends.slice(-30).map((day: any, idx: number) => (
                <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                  <div
                    className="w-full bg-primary-500 rounded-t"
                    style={{ height: `${(day.avg_risk_score / maxRiskScore) * 100}%` }}
                    title={`${day.date}: ${day.avg_risk_score}`}
                  />
                </div>
              ))}
            </div>
            <div className="flex justify-between text-xs text-gray-400 mt-2">
              <span>{trends[0]?.date?.slice(5)}</span>
              <span>{trends[trends.length - 1]?.date?.slice(5)}</span>
            </div>

            {/* Legend */}
            <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-4 gap-4 text-center">
              <div>
                <p className="text-lg font-semibold text-primary-600">
                  {trendsData?.summary?.total_predictions?.toLocaleString() || 0}
                </p>
                <p className="text-xs text-gray-500">Total Predictions</p>
              </div>
              <div>
                <p className="text-lg font-semibold text-red-600">
                  {trendsData?.summary?.total_anomalies || 0}
                </p>
                <p className="text-xs text-gray-500">Anomalies</p>
              </div>
              <div>
                <p className="text-lg font-semibold text-yellow-600">
                  {trendsData?.summary?.total_recommendations || 0}
                </p>
                <p className="text-xs text-gray-500">Recommendations</p>
              </div>
              <div>
                <p className={clsx(
                  'text-lg font-semibold',
                  trendsData?.summary?.risk_change < 0 ? 'text-green-600' : 'text-red-600'
                )}>
                  {trendsData?.summary?.risk_change > 0 ? '+' : ''}{trendsData?.summary?.risk_change || 0}
                </p>
                <p className="text-xs text-gray-500">Risk Change</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Anomaly Trend */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h2 className="text-sm font-medium text-gray-900 flex items-center gap-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-orange-500" />
            Anomaly Detection Trend
          </h2>
        </div>
        <div className="p-4">
          <div className="h-32 flex items-end gap-1">
            {trends.slice(-30).map((day: any, idx: number) => (
              <div key={idx} className="flex-1 flex flex-col items-center">
                <div
                  className={clsx(
                    'w-full rounded-t',
                    day.anomalies_detected > 15 ? 'bg-red-500' :
                    day.anomalies_detected > 10 ? 'bg-orange-500' : 'bg-yellow-500'
                  )}
                  style={{ height: `${(day.anomalies_detected / maxAnomalies) * 100}%` }}
                  title={`${day.date}: ${day.anomalies_detected} anomalies`}
                />
              </div>
            ))}
          </div>
          <div className="flex justify-between text-xs text-gray-400 mt-2">
            <span>{trends[0]?.date?.slice(5)}</span>
            <span>{trends[trends.length - 1]?.date?.slice(5)}</span>
          </div>
        </div>
      </div>

      {/* Model Accuracy & Impact */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Model Accuracy */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-medium text-gray-900 flex items-center gap-2">
              <AdjustmentsHorizontalIcon className="h-5 w-5 text-blue-500" />
              Model Accuracy
            </h2>
          </div>
          <div className="p-4 space-y-4">
            {advancedStats?.accuracy && Object.entries(advancedStats.accuracy).map(([model, data]: [string, any]) => (
              <div key={model}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700 capitalize">{model.replace(/_/g, ' ')}</span>
                  <span className="text-sm text-green-600">{data.improvement}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-gradient-to-r from-blue-500 to-green-500 h-3 rounded-full"
                      style={{ width: `${data.current * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-gray-900 w-16 text-right">
                    {(data.current * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">Baseline: {(data.baseline * 100).toFixed(1)}%</p>
              </div>
            ))}
          </div>
        </div>

        {/* ML Impact */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-medium text-gray-900 flex items-center gap-2">
              <LightBulbIcon className="h-5 w-5 text-yellow-500" />
              ML Impact Metrics
            </h2>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-green-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-green-600">{advancedStats?.impact?.risk_reduction_30d || '0%'}</p>
                <p className="text-xs text-green-700 mt-1">Risk Reduction (30d)</p>
              </div>
              <div className="p-4 bg-blue-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-blue-600">{advancedStats?.impact?.false_positive_reduction || '0%'}</p>
                <p className="text-xs text-blue-700 mt-1">False Positive Reduction</p>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-purple-600">{advancedStats?.impact?.automated_decisions_pct || '0%'}</p>
                <p className="text-xs text-purple-700 mt-1">Automated Decisions</p>
              </div>
              <div className="p-4 bg-orange-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-orange-600">{advancedStats?.impact?.time_saved_hours_weekly || 0}</p>
                <p className="text-xs text-orange-700 mt-1">Hours Saved/Week</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Processing Stats */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h2 className="text-sm font-medium text-gray-900 flex items-center gap-2">
            <ClockIcon className="h-5 w-5 text-gray-500" />
            Processing Statistics
          </h2>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-xl font-semibold text-gray-900">
                {advancedStats?.processing?.predictions_today?.toLocaleString() || 0}
              </p>
              <p className="text-xs text-gray-500">Predictions Today</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-xl font-semibold text-gray-900">
                {advancedStats?.processing?.predictions_this_week?.toLocaleString() || 0}
              </p>
              <p className="text-xs text-gray-500">This Week</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-xl font-semibold text-gray-900">
                {advancedStats?.processing?.anomalies_analyzed?.toLocaleString() || 0}
              </p>
              <p className="text-xs text-gray-500">Anomalies Analyzed</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-xl font-semibold text-gray-900">
                {advancedStats?.processing?.recommendations_generated || 0}
              </p>
              <p className="text-xs text-gray-500">Recommendations</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-xl font-semibold text-green-600">
                {advancedStats?.processing?.avg_prediction_latency_ms || 0}ms
              </p>
              <p className="text-xs text-gray-500">Avg Latency</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-xl font-semibold text-orange-600">
                {advancedStats?.processing?.p99_latency_ms || 0}ms
              </p>
              <p className="text-xs text-gray-500">P99 Latency</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
