import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ClipboardDocumentCheckIcon,
  DocumentTextIcon,
  CogIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { securityControlsApi } from '../../services/api';

const ratingConfig = {
  GREEN: { color: 'bg-green-100 text-green-800 border-green-200', icon: CheckCircleIcon, label: 'Compliant' },
  YELLOW: { color: 'bg-yellow-100 text-yellow-800 border-yellow-200', icon: ExclamationTriangleIcon, label: 'Warning' },
  RED: { color: 'bg-red-100 text-red-800 border-red-200', icon: XCircleIcon, label: 'Critical' },
};

export function SecurityControlDetail() {
  const { controlId } = useParams<{ controlId: string }>();
  const [activeTab, setActiveTab] = useState('details');

  const { data: control, isLoading } = useQuery({
    queryKey: ['securityControl', controlId],
    queryFn: async () => {
      const response = await securityControlsApi.get(controlId!);
      return response.data;
    },
    enabled: !!controlId,
  });

  const { data: evaluationsData } = useQuery({
    queryKey: ['controlEvaluations', controlId],
    queryFn: async () => {
      const response = await securityControlsApi.getEvaluations({
        control_id: controlId,
        limit: 10,
      });
      return response.data;
    },
    enabled: !!controlId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!control) {
    return (
      <div className="text-center py-12">
        <h2 className="text-lg font-medium text-gray-900">Control not found</h2>
        <Link to="/security-controls/list" className="mt-4 btn-primary inline-block">
          Back to Controls
        </Link>
      </div>
    );
  }

  const RatingIcon = ratingConfig[control.default_risk_rating as keyof typeof ratingConfig]?.icon || ExclamationTriangleIcon;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-4">
          <Link
            to="/security-controls/list"
            className="mt-1 p-1 rounded hover:bg-gray-100"
          >
            <ArrowLeftIcon className="h-5 w-5 text-gray-500" />
          </Link>
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="page-title">{control.control_id}</h1>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                  ratingConfig[control.default_risk_rating as keyof typeof ratingConfig]?.color ||
                  'bg-gray-100 text-gray-800 border-gray-200'
                }`}
              >
                <RatingIcon className="h-3 w-3 mr-1" />
                {control.default_risk_rating}
              </span>
            </div>
            <p className="page-subtitle mt-1">{control.control_name}</p>
          </div>
        </div>
        <Link
          to={`/security-controls/evaluate?control=${controlId}`}
          className="btn-primary"
        >
          <ClipboardDocumentCheckIcon className="h-4 w-4 mr-1.5" />
          Evaluate Control
        </Link>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-6">
          {['details', 'mappings', 'evaluations'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-1 border-b-2 text-sm font-medium ${
                activeTab === tab
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'details' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Main Info */}
          <div className="lg:col-span-2 space-y-5">
            <div className="card">
              <div className="card-header">
                <h2 className="section-title">Control Details</h2>
              </div>
              <div className="card-body space-y-4">
                <div>
                  <label className="text-xs font-medium text-gray-500">Description</label>
                  <p className="mt-1 text-sm text-gray-900">{control.description}</p>
                </div>
                {control.purpose && (
                  <div>
                    <label className="text-xs font-medium text-gray-500">Purpose</label>
                    <p className="mt-1 text-sm text-gray-900">{control.purpose}</p>
                  </div>
                )}
                {control.procedure && (
                  <div>
                    <label className="text-xs font-medium text-gray-500">Procedure</label>
                    <p className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">{control.procedure}</p>
                  </div>
                )}
                {control.recommendation && (
                  <div>
                    <label className="text-xs font-medium text-gray-500">Recommendation</label>
                    <p className="mt-1 text-sm text-gray-900">{control.recommendation}</p>
                  </div>
                )}
                {control.comment && (
                  <div>
                    <label className="text-xs font-medium text-gray-500">Comments</label>
                    <p className="mt-1 text-sm text-gray-900">{control.comment}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Technical Details */}
            {control.profile_parameter && control.profile_parameter !== 'N/A' && (
              <div className="card">
                <div className="card-header">
                  <h2 className="section-title">Technical Parameters</h2>
                </div>
                <div className="card-body">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <CogIcon className="h-4 w-4 text-gray-500" />
                      <span className="text-xs font-medium text-gray-500">Profile Parameter</span>
                    </div>
                    <code className="text-sm font-mono bg-white px-3 py-2 rounded border block">
                      {control.profile_parameter}
                    </code>
                    {control.expected_value && (
                      <div className="mt-3">
                        <span className="text-xs font-medium text-gray-500">Expected Value</span>
                        <p className="mt-1 text-sm text-gray-900">{control.expected_value}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-5">
            {/* Classification */}
            <div className="card">
              <div className="card-header">
                <h2 className="section-title">Classification</h2>
              </div>
              <div className="card-body space-y-3">
                <div>
                  <label className="text-xs font-medium text-gray-500">Business Area</label>
                  <p className="mt-0.5 text-sm text-gray-900">{control.business_area}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500">Control Type</label>
                  <p className="mt-0.5 text-sm text-gray-900">{control.control_type}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500">Category</label>
                  <p className="mt-0.5 text-sm text-gray-900">{control.category}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500">Status</label>
                  <p className="mt-0.5">
                    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                      control.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {control.status}
                    </span>
                  </p>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500">Automated</label>
                  <p className="mt-0.5 text-sm text-gray-900">
                    {control.is_automated ? 'Yes' : 'No'}
                  </p>
                </div>
              </div>
            </div>

            {/* Compliance */}
            {control.compliance_frameworks && control.compliance_frameworks.length > 0 && (
              <div className="card">
                <div className="card-header">
                  <h2 className="section-title">Compliance Frameworks</h2>
                </div>
                <div className="card-body">
                  <div className="flex flex-wrap gap-2">
                    {control.compliance_frameworks.map((framework: string) => (
                      <span
                        key={framework}
                        className="inline-flex px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800"
                      >
                        {framework}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'mappings' && (
        <div className="card">
          <div className="card-header">
            <h2 className="section-title">Value Mappings</h2>
            <p className="text-xs text-gray-500 mt-1">
              Defines how different values map to risk ratings
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Condition
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Rating
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Recommendation
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Comment
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {control.value_mappings && control.value_mappings.length > 0 ? (
                  control.value_mappings.map((mapping: any, index: number) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-900">
                        {mapping.value_condition}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${
                            ratingConfig[mapping.risk_rating as keyof typeof ratingConfig]?.color ||
                            'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {mapping.risk_rating}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 max-w-xs">
                        {mapping.recommendation || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 max-w-xs">
                        {mapping.comment || '-'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-500">
                      No value mappings defined for this control.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'evaluations' && (
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <div>
              <h2 className="section-title">Evaluation History</h2>
              <p className="text-xs text-gray-500 mt-1">
                Past evaluations of this control
              </p>
            </div>
            <Link
              to={`/security-controls/evaluate?control=${controlId}`}
              className="btn-secondary text-xs"
            >
              New Evaluation
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
                    System
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Actual Value
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Rating
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Date
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Evaluated By
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {evaluationsData?.items && evaluationsData.items.length > 0 ? (
                  evaluationsData.items.map((evaluation: any) => (
                    <tr key={evaluation.evaluation_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap text-xs font-medium text-gray-900">
                        {evaluation.evaluation_id}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                        {evaluation.system_id}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-900">
                        {evaluation.actual_value || '-'}
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
                          ? new Date(evaluation.evaluation_date).toLocaleString()
                          : '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                        {evaluation.evaluated_by || '-'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                      <ClockIcon className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                      No evaluations recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
