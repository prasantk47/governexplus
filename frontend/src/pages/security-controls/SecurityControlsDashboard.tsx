import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ShieldCheckIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ArrowUpTrayIcon,
  ClipboardDocumentCheckIcon,
  ServerStackIcon,
  DocumentMagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { securityControlsApi } from '../../services/api';

interface DashboardStats {
  total_controls: number;
  category_breakdown: Record<string, number>;
  evaluation_summary: Record<string, number>;
  pending_exceptions: number;
  recent_evaluations: any[];
}

const ratingConfig = {
  GREEN: { color: 'bg-green-100 text-green-800', icon: CheckCircleIcon, label: 'Compliant' },
  YELLOW: { color: 'bg-yellow-100 text-yellow-800', icon: ExclamationTriangleIcon, label: 'Warning' },
  RED: { color: 'bg-red-100 text-red-800', icon: XCircleIcon, label: 'Critical' },
};

export function SecurityControlsDashboard() {
  const { data: dashboardData, isLoading } = useQuery<DashboardStats>({
    queryKey: ['securityControlsDashboard'],
    queryFn: async () => {
      const response = await securityControlsApi.getDashboard();
      return response.data;
    },
  });

  const { data: systemProfiles } = useQuery({
    queryKey: ['systemProfiles'],
    queryFn: async () => {
      const response = await securityControlsApi.getSystemProfiles();
      return response.data.systems || [];
    },
  });

  const totalEvaluations = dashboardData?.evaluation_summary
    ? Object.values(dashboardData.evaluation_summary).reduce((a, b) => a + b, 0)
    : 0;

  const greenPercentage = dashboardData?.evaluation_summary?.GREEN
    ? Math.round((dashboardData.evaluation_summary.GREEN / totalEvaluations) * 100)
    : 0;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">SAP Security Controls</h1>
          <p className="page-subtitle">
            Monitor and evaluate SAP system security configurations
          </p>
        </div>
        <div className="flex space-x-2">
          <Link to="/security-controls/import" className="btn-secondary">
            <ArrowUpTrayIcon className="h-4 w-4 mr-1.5" />
            Import Controls
          </Link>
          <Link to="/security-controls/evaluate" className="btn-primary">
            <ClipboardDocumentCheckIcon className="h-4 w-4 mr-1.5" />
            Run Evaluation
          </Link>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-card-accent border-blue-400">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-blue">
              <ShieldCheckIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Total Controls</div>
              <div className="stat-value">{dashboardData?.total_controls || 0}</div>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-green">
              <CheckCircleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Compliant</div>
              <div className="flex items-baseline gap-2">
                <div className="stat-value text-green-600">
                  {dashboardData?.evaluation_summary?.GREEN || 0}
                </div>
                {totalEvaluations > 0 && (
                  <span className="text-xs text-gray-500">{greenPercentage}%</span>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-yellow">
              <ExclamationTriangleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Warnings</div>
              <div className="stat-value text-yellow-600">
                {dashboardData?.evaluation_summary?.YELLOW || 0}
              </div>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-red">
              <XCircleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Critical</div>
              <div className="stat-value text-red-600">
                {dashboardData?.evaluation_summary?.RED || 0}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Compliance Score */}
        <div className="card">
          <div className="card-header">
            <h2 className="section-title">Compliance Score</h2>
          </div>
          <div className="card-body">
            <div className="flex items-center justify-center py-4">
              <div className="relative">
                <svg width="160" height="160" viewBox="0 0 100 100">
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="#e5e7eb"
                    strokeWidth="8"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke={greenPercentage >= 70 ? '#22c55e' : greenPercentage >= 40 ? '#eab308' : '#ef4444'}
                    strokeWidth="8"
                    strokeDasharray={`${greenPercentage * 2.51} ${100 * 2.51}`}
                    strokeLinecap="round"
                    transform="rotate(-90 50 50)"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-bold text-gray-900">{greenPercentage}%</span>
                  <span className="text-xs text-gray-500">Compliant</span>
                </div>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-xs">
                <span className="flex items-center">
                  <span className="w-3 h-3 rounded-full bg-green-500 mr-2"></span>
                  Compliant (GREEN)
                </span>
                <span className="font-medium">{dashboardData?.evaluation_summary?.GREEN || 0}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="flex items-center">
                  <span className="w-3 h-3 rounded-full bg-yellow-500 mr-2"></span>
                  Warning (YELLOW)
                </span>
                <span className="font-medium">{dashboardData?.evaluation_summary?.YELLOW || 0}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="flex items-center">
                  <span className="w-3 h-3 rounded-full bg-red-500 mr-2"></span>
                  Critical (RED)
                </span>
                <span className="font-medium">{dashboardData?.evaluation_summary?.RED || 0}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Controls by Category */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="section-title">Controls by Category</h2>
            <Link
              to="/security-controls/list"
              className="text-xs text-primary-600 hover:text-primary-700 font-medium"
            >
              View all
            </Link>
          </div>
          <div className="card-body">
            <div className="space-y-3">
              {dashboardData?.category_breakdown &&
                Object.entries(dashboardData.category_breakdown)
                  .slice(0, 6)
                  .map(([category, count]) => (
                    <div key={category}>
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-gray-700 truncate max-w-[200px]">
                          {category}
                        </span>
                        <span className="text-gray-500">{count} controls</span>
                      </div>
                      <div className="mt-1 w-full bg-gray-100 rounded-full h-1.5">
                        <div
                          className="bg-primary-600 h-1.5 rounded-full"
                          style={{
                            width: `${Math.min(
                              ((count as number) / (dashboardData?.total_controls || 1)) * 100,
                              100
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
            </div>
          </div>
        </div>
      </div>

      {/* System Profiles */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h2 className="section-title">System Security Profiles</h2>
          <Link
            to="/security-controls/systems"
            className="text-xs text-primary-600 hover:text-primary-700 font-medium"
          >
            View all systems
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  System ID
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Type
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Score
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  GREEN
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  YELLOW
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  RED
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Last Evaluation
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {systemProfiles && systemProfiles.length > 0 ? (
                systemProfiles.map((profile: any) => (
                  <tr key={profile.system_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-xs font-medium text-primary-600">
                      <Link to={`/security-controls/systems/${profile.system_id}`}>
                        {profile.system_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                      {profile.system_type || 'SAP'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                          <div
                            className={`h-2 rounded-full ${
                              profile.security_score >= 70
                                ? 'bg-green-500'
                                : profile.security_score >= 40
                                ? 'bg-yellow-500'
                                : 'bg-red-500'
                            }`}
                            style={{ width: `${profile.security_score}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium">{profile.security_score}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-green-600 font-medium">
                      {profile.green_count}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-yellow-600 font-medium">
                      {profile.yellow_count}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-red-600 font-medium">
                      {profile.red_count}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                      {profile.last_evaluation_date
                        ? new Date(profile.last_evaluation_date).toLocaleDateString()
                        : 'Never'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                    <ServerStackIcon className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                    No systems evaluated yet. Run an evaluation to see results.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Evaluations */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h2 className="section-title">Recent Evaluations</h2>
          <Link
            to="/security-controls/evaluations"
            className="text-xs text-primary-600 hover:text-primary-700 font-medium"
          >
            View all
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Evaluation ID
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Control
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  System
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Rating
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Date
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {dashboardData?.recent_evaluations && dashboardData.recent_evaluations.length > 0 ? (
                dashboardData.recent_evaluations.slice(0, 5).map((evaluation: any) => (
                  <tr key={evaluation.evaluation_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-xs font-medium text-gray-900">
                      {evaluation.evaluation_id}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                      {evaluation.control_id}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                      {evaluation.system_id}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${
                          ratingConfig[evaluation.risk_rating as keyof typeof ratingConfig]?.color ||
                          'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {evaluation.risk_rating}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                      {evaluation.evaluation_date
                        ? new Date(evaluation.evaluation_date).toLocaleDateString()
                        : '-'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-500">
                    <DocumentMagnifyingGlassIcon className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                    No evaluations yet. Run an evaluation to see results.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <div className="card-header">
          <h2 className="section-title">Quick Actions</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <Link
              to="/security-controls/list"
              className="p-3 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <ShieldCheckIcon className="h-5 w-5 text-gray-600" />
              <span className="mt-2 block text-xs font-medium text-gray-800">Browse Controls</span>
              <span className="text-xs text-gray-500">View all security controls</span>
            </Link>
            <Link
              to="/security-controls/evaluate"
              className="p-3 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
            >
              <ClipboardDocumentCheckIcon className="h-5 w-5 text-blue-600" />
              <span className="mt-2 block text-xs font-medium text-blue-800">Run Evaluation</span>
              <span className="text-xs text-blue-600">Evaluate system controls</span>
            </Link>
            <Link
              to="/security-controls/import"
              className="p-3 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 transition-colors"
            >
              <ArrowUpTrayIcon className="h-5 w-5 text-green-600" />
              <span className="mt-2 block text-xs font-medium text-green-800">Import Controls</span>
              <span className="text-xs text-green-600">Import from CSV/JSON</span>
            </Link>
            <Link
              to="/security-controls/exceptions"
              className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg hover:bg-yellow-100 transition-colors"
            >
              <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600" />
              <span className="mt-2 block text-xs font-medium text-yellow-800">Exceptions</span>
              <span className="text-xs text-yellow-600">
                {dashboardData?.pending_exceptions || 0} pending
              </span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
