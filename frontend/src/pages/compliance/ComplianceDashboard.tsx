import { useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../services/api';
import {
  ShieldCheckIcon,
  DocumentCheckIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  DocumentTextIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline';

interface ComplianceFramework {
  id: string;
  name: string;
  shortName: string;
  description: string;
  totalControls: number;
  compliantControls: number;
  partialControls: number;
  nonCompliantControls: number;
  complianceScore: number;
  lastAssessment: string;
  nextAssessment: string;
  trend: 'up' | 'down' | 'stable';
  trendValue: number;
}

interface ControlGap {
  id: string;
  framework: string;
  controlId: string;
  controlName: string;
  status: 'non_compliant' | 'partial';
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  remediationPlan: string;
  dueDate: string;
  owner: string;
}

export function ComplianceDashboard() {
  const [_selectedFramework, setSelectedFramework] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'gaps' | 'controls'>('overview');

  const { data: frameworksData } = useQuery({
    queryKey: ['complianceFrameworks'],
    queryFn: () => api.get('/compliance/frameworks').then((r) => r.data),
  });

  const { data: controlGapsData } = useQuery({
    queryKey: ['complianceControlGaps'],
    queryFn: () => api.get('/compliance/gaps').then((r) => r.data),
  });

  const frameworks: ComplianceFramework[] = frameworksData || [];
  const controlGaps: ControlGap[] = controlGapsData || [];

  const overallScore = frameworks.length
    ? Math.round(frameworks.reduce((acc, f) => acc + f.complianceScore, 0) / frameworks.length)
    : 0;

  const totalGaps = controlGaps.length;
  const criticalGaps = controlGaps.filter((g) => g.severity === 'critical').length;

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 75) return 'text-yellow-600';
    if (score >= 60) return 'text-orange-600';
    return 'text-red-600';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 90) return 'bg-green-100';
    if (score >= 75) return 'bg-yellow-100';
    if (score >= 60) return 'bg-orange-100';
    return 'bg-red-100';
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-green-100 text-green-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Compliance Dashboard</h1>
          <p className="text-sm text-gray-500">
            Track compliance across multiple regulatory frameworks
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => toast.success('Exporting compliance report...')}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm"
          >
            Export Report
          </button>
          <Link
            to="/compliance/assessment"
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm"
          >
            Run Assessment
          </Link>
        </div>
      </div>

      {/* Overall Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Overall Compliance</p>
              <p className={`text-3xl font-bold ${getScoreColor(overallScore)}`}>{overallScore}%</p>
            </div>
            <div className={`p-3 rounded-full ${getScoreBgColor(overallScore)}`}>
              <ShieldCheckIcon className={`h-6 w-6 ${getScoreColor(overallScore)}`} />
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Frameworks</p>
              <p className="text-3xl font-bold text-gray-900">{frameworks.length}</p>
            </div>
            <div className="p-3 rounded-full bg-blue-100">
              <DocumentCheckIcon className="h-6 w-6 text-blue-600" />
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Open Gaps</p>
              <p className="text-3xl font-bold text-orange-600">{totalGaps}</p>
            </div>
            <div className="p-3 rounded-full bg-orange-100">
              <ExclamationTriangleIcon className="h-6 w-6 text-orange-600" />
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Critical Gaps</p>
              <p className="text-3xl font-bold text-red-600">{criticalGaps}</p>
            </div>
            <div className="p-3 rounded-full bg-red-100">
              <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {(['overview', 'gaps', 'controls'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-6 py-4 text-sm font-medium border-b-2 ${
                  activeTab === tab
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab === 'overview' && 'Framework Overview'}
                {tab === 'gaps' && `Control Gaps (${totalGaps})`}
                {tab === 'controls' && 'Control Mapping'}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* Framework Overview Tab */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {frameworks.map((framework) => (
                <div
                  key={framework.id}
                  className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => setSelectedFramework(framework.id)}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{framework.shortName}</h3>
                      <p className="text-xs text-gray-500">{framework.description}</p>
                    </div>
                    <div className={`flex items-center gap-1 text-sm ${
                      framework.trend === 'up' ? 'text-green-600' :
                      framework.trend === 'down' ? 'text-red-600' : 'text-gray-500'
                    }`}>
                      {framework.trend === 'up' && <ArrowTrendingUpIcon className="h-4 w-4" />}
                      {framework.trend === 'down' && <ArrowTrendingDownIcon className="h-4 w-4" />}
                      {framework.trendValue !== 0 && `${framework.trendValue > 0 ? '+' : ''}${framework.trendValue}%`}
                    </div>
                  </div>

                  {/* Score */}
                  <div className="flex items-center gap-4 mb-3">
                    <div className={`text-3xl font-bold ${getScoreColor(framework.complianceScore)}`}>
                      {framework.complianceScore}%
                    </div>
                    <div className="flex-1">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            framework.complianceScore >= 90 ? 'bg-green-500' :
                            framework.complianceScore >= 75 ? 'bg-yellow-500' :
                            framework.complianceScore >= 60 ? 'bg-orange-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${framework.complianceScore}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Control Stats */}
                  <div className="grid grid-cols-3 gap-2 text-center text-xs mb-3">
                    <div className="bg-green-50 rounded p-2">
                      <div className="font-bold text-green-700">{framework.compliantControls}</div>
                      <div className="text-green-600">Compliant</div>
                    </div>
                    <div className="bg-yellow-50 rounded p-2">
                      <div className="font-bold text-yellow-700">{framework.partialControls}</div>
                      <div className="text-yellow-600">Partial</div>
                    </div>
                    <div className="bg-red-50 rounded p-2">
                      <div className="font-bold text-red-700">{framework.nonCompliantControls}</div>
                      <div className="text-red-600">Non-Compliant</div>
                    </div>
                  </div>

                  {/* Dates */}
                  <div className="flex items-center justify-between text-xs text-gray-500 pt-3 border-t border-gray-100">
                    <div className="flex items-center gap-1">
                      <ClockIcon className="h-3 w-3" />
                      Last: {framework.lastAssessment}
                    </div>
                    <div className="flex items-center gap-1">
                      <CalendarIcon className="h-3 w-3" />
                      Next: {framework.nextAssessment}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Control Gaps Tab */}
          {activeTab === 'gaps' && (
            <div className="space-y-4">
              {controlGaps.map((gap) => (
                <div key={gap.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(gap.severity)}`}>
                        {gap.severity}
                      </span>
                      <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                        {gap.framework}
                      </span>
                      <span className="text-xs text-gray-500">{gap.controlId}</span>
                    </div>
                    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                      gap.status === 'non_compliant' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {gap.status === 'non_compliant' ? 'Non-Compliant' : 'Partial'}
                    </span>
                  </div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">{gap.controlName}</h4>
                  <p className="text-sm text-gray-600 mb-3">{gap.description}</p>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
                      <DocumentTextIcon className="h-3 w-3" />
                      Remediation Plan
                    </div>
                    <p className="text-sm text-gray-700">{gap.remediationPlan}</p>
                  </div>
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100 text-xs text-gray-500">
                    <span>Owner: {gap.owner}</span>
                    <span className="text-orange-600 font-medium">Due: {gap.dueDate}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Control Mapping Tab */}
          {activeTab === 'controls' && (
            <div className="text-center py-12">
              <ChartBarIcon className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Control Mapping Matrix</h3>
              <p className="text-sm text-gray-500 mb-4">
                View how GOVERNEX+ controls map to regulatory requirements
              </p>
              <button
                onClick={() => toast.success('Generating control matrix...')}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm"
              >
                Generate Control Matrix
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Upcoming Assessments */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Upcoming Assessments</h3>
        <div className="space-y-3">
          {frameworks
            .sort((a, b) => new Date(a.nextAssessment).getTime() - new Date(b.nextAssessment).getTime())
            .slice(0, 4)
            .map((framework) => (
              <div key={framework.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${getScoreBgColor(framework.complianceScore)}`}>
                    <ShieldCheckIcon className={`h-5 w-5 ${getScoreColor(framework.complianceScore)}`} />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-900">{framework.name}</div>
                    <div className="text-xs text-gray-500">{framework.totalControls} controls</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium text-gray-900">{framework.nextAssessment}</div>
                  <div className="text-xs text-gray-500">Next Assessment</div>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
