/**
 * ML Analytics Dashboard
 * Governex+ Machine Learning capabilities visualization
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  CpuChipIcon,
  ExclamationTriangleIcon,
  LightBulbIcon,
  ChartBarIcon,
  UserGroupIcon,
  ShieldCheckIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface MLMetric {
  label: string;
  value: number | string;
  change?: number;
  trend?: 'up' | 'down' | 'stable';
  status?: 'good' | 'warning' | 'critical';
}

interface AnomalyAlert {
  id: string;
  type: string;
  severity: 'critical' | 'warning' | 'info';
  user: string;
  description: string;
  timestamp: string;
  acknowledged: boolean;
}

interface Recommendation {
  id: string;
  type: string;
  title: string;
  confidence: number;
  impact: string;
  status: 'pending' | 'accepted' | 'rejected';
}

export function MLDashboard() {
  const [isLoading, setIsLoading] = useState(true);
  const [metrics, setMetrics] = useState<Record<string, MLMetric>>({});
  const [anomalies, setAnomalies] = useState<AnomalyAlert[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  useEffect(() => {
    // Simulate loading ML data
    const loadData = async () => {
      await new Promise(resolve => setTimeout(resolve, 1000));

      setMetrics({
        riskPrediction: {
          label: 'Avg Predicted Risk',
          value: 42,
          change: -5,
          trend: 'down',
          status: 'good'
        },
        anomaliesDetected: {
          label: 'Active Anomalies',
          value: 7,
          change: 2,
          trend: 'up',
          status: 'warning'
        },
        recommendationsGenerated: {
          label: 'Pending Recommendations',
          value: 23,
          status: 'good'
        },
        modelAccuracy: {
          label: 'Model Accuracy',
          value: '94.2%',
          change: 1.2,
          trend: 'up',
          status: 'good'
        },
        usersAnalyzed: {
          label: 'Users Analyzed',
          value: '1,250',
          status: 'good'
        },
        rolesOptimized: {
          label: 'Roles Optimized',
          value: 52,
          status: 'good'
        }
      });

      setAnomalies([
        {
          id: '1',
          type: 'DATA_EXFILTRATION',
          severity: 'critical',
          user: 'mbrown',
          description: 'Downloaded 5,000+ records from customer table',
          timestamp: '2 hours ago',
          acknowledged: false
        },
        {
          id: '2',
          type: 'UNUSUAL_TIME',
          severity: 'warning',
          user: 'jsmith',
          description: 'Login at 3:42 AM from new location',
          timestamp: '4 hours ago',
          acknowledged: false
        },
        {
          id: '3',
          type: 'PRIVILEGE_ESCALATION',
          severity: 'warning',
          user: 'tdavis',
          description: 'Attempted access to admin functions',
          timestamp: '6 hours ago',
          acknowledged: true
        },
      ]);

      setRecommendations([
        {
          id: '1',
          type: 'REMOVE_ACCESS',
          title: 'Remove unused SAP_SD_USER role',
          confidence: 92,
          impact: '-5 risk points',
          status: 'pending'
        },
        {
          id: '2',
          type: 'ADD_ACCESS',
          title: 'Add SAP_FI_DISPLAY to Finance team',
          confidence: 87,
          impact: 'Productivity boost',
          status: 'pending'
        },
        {
          id: '3',
          type: 'CONSOLIDATE',
          title: 'Merge 3 procurement roles',
          confidence: 78,
          impact: '-2 risk points',
          status: 'accepted'
        },
      ]);

      setIsLoading(false);
    };

    loadData();
  }, []);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-700 border-red-200';
      case 'warning': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      default: return 'bg-blue-100 text-blue-700 border-blue-200';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good': return 'text-green-600';
      case 'warning': return 'text-yellow-600';
      case 'critical': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3">
          <CpuChipIcon className="h-8 w-8 text-primary-500 animate-pulse" />
          <span className="text-gray-500">Loading ML Analytics...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <CpuChipIcon className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">ML Analytics Dashboard</h1>
            <p className="text-sm text-gray-500">Machine Learning powered insights and predictions</p>
          </div>
        </div>
        <Link
          to="/ai"
          className="btn-primary flex items-center gap-2"
        >
          <LightBulbIcon className="h-4 w-4" />
          Open AI Assistant
        </Link>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {Object.entries(metrics).map(([key, metric]) => (
          <div key={key} className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">{metric.label}</p>
            <div className="flex items-baseline gap-2">
              <span className={clsx('text-2xl font-semibold', getStatusColor(metric.status || 'good'))}>
                {metric.value}
              </span>
              {metric.change !== undefined && (
                <span className={clsx(
                  'text-xs flex items-center',
                  metric.trend === 'down' ? 'text-green-600' : metric.trend === 'up' ? 'text-red-600' : 'text-gray-500'
                )}>
                  {metric.trend === 'down' ? (
                    <ArrowTrendingDownIcon className="h-3 w-3 mr-0.5" />
                  ) : metric.trend === 'up' ? (
                    <ArrowTrendingUpIcon className="h-3 w-3 mr-0.5" />
                  ) : null}
                  {metric.change > 0 ? '+' : ''}{metric.change}%
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Anomaly Detection */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
              <h2 className="text-sm font-medium text-gray-900">Anomaly Detection</h2>
            </div>
            <Link to="/ml/anomalies" className="text-xs text-primary-600 hover:text-primary-700">
              View all
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {anomalies.map(anomaly => (
              <div key={anomaly.id} className="p-4 hover:bg-gray-50">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={clsx(
                        'px-2 py-0.5 text-xs font-medium rounded border',
                        getSeverityColor(anomaly.severity)
                      )}>
                        {anomaly.severity.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500">{anomaly.type.replace('_', ' ')}</span>
                    </div>
                    <p className="text-sm text-gray-900">{anomaly.description}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>User: {anomaly.user}</span>
                      <span>{anomaly.timestamp}</span>
                    </div>
                  </div>
                  {anomaly.acknowledged ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-500" />
                  ) : (
                    <button className="text-xs text-primary-600 hover:text-primary-700">
                      Investigate
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Smart Recommendations */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <LightBulbIcon className="h-5 w-5 text-yellow-500" />
              <h2 className="text-sm font-medium text-gray-900">Smart Recommendations</h2>
            </div>
            <Link to="/ml/recommendations" className="text-xs text-primary-600 hover:text-primary-700">
              View all
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {recommendations.map(rec => (
              <div key={rec.id} className="p-4 hover:bg-gray-50">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{rec.title}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>Confidence: {rec.confidence}%</span>
                      <span>Impact: {rec.impact}</span>
                    </div>
                  </div>
                  {rec.status === 'pending' ? (
                    <div className="flex gap-2">
                      <button className="p-1 text-green-600 hover:bg-green-50 rounded">
                        <CheckCircleIcon className="h-5 w-5" />
                      </button>
                      <button className="p-1 text-red-600 hover:bg-red-50 rounded">
                        <XCircleIcon className="h-5 w-5" />
                      </button>
                    </div>
                  ) : (
                    <span className={clsx(
                      'text-xs px-2 py-0.5 rounded',
                      rec.status === 'accepted' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                    )}>
                      {rec.status}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Advanced ML Capabilities */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link
          to="/ml/analytics"
          className="bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg p-4 text-white hover:from-primary-600 hover:to-primary-700 transition-colors"
        >
          <ChartBarIcon className="h-8 w-8 mb-2 opacity-80" />
          <h3 className="font-medium">Predictive Analytics</h3>
          <p className="text-xs opacity-80 mt-1">Risk trends, forecasting, and insights</p>
        </Link>

        <Link
          to="/ml/ueba"
          className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg p-4 text-white hover:from-purple-600 hover:to-purple-700 transition-colors"
        >
          <UserGroupIcon className="h-8 w-8 mb-2 opacity-80" />
          <h3 className="font-medium">User Behavior Analytics</h3>
          <p className="text-xs opacity-80 mt-1">UEBA profiling and peer analysis</p>
        </Link>

        <Link
          to="/ml/models"
          className="bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-lg p-4 text-white hover:from-indigo-600 hover:to-indigo-700 transition-colors"
        >
          <CpuChipIcon className="h-8 w-8 mb-2 opacity-80" />
          <h3 className="font-medium">Model Management</h3>
          <p className="text-xs opacity-80 mt-1">Train, monitor, and manage ML models</p>
        </Link>

        <Link
          to="/ai"
          className="bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-lg p-4 text-white hover:from-yellow-600 hover:to-yellow-700 transition-colors"
        >
          <LightBulbIcon className="h-8 w-8 mb-2 opacity-80" />
          <h3 className="font-medium">AI Assistant</h3>
          <p className="text-xs opacity-80 mt-1">Natural language GRC interactions</p>
        </Link>
      </div>

      {/* Model Performance */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheckIcon className="h-5 w-5 text-primary-500" />
          <h2 className="text-sm font-medium text-gray-900">ML Model Performance</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-2xl font-semibold text-green-600">94.2%</p>
            <p className="text-xs text-gray-500">Risk Model Accuracy</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-2xl font-semibold text-green-600">91.8%</p>
            <p className="text-xs text-gray-500">Anomaly Precision</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-2xl font-semibold text-green-600">87.5%</p>
            <p className="text-xs text-gray-500">Recommendation Accuracy</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-2xl font-semibold text-primary-600">1.2M</p>
            <p className="text-xs text-gray-500">Training Data Points</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default MLDashboard;
