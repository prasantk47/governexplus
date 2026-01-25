import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams, Link } from 'react-router-dom';
import {
  ClipboardDocumentCheckIcon,
  PlayIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ServerStackIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import { securityControlsApi } from '../../services/api';

interface Control {
  control_id: string;
  name: string;
  category: string;
  description?: string;
}

interface EvaluationResult {
  control_id: string;
  risk_rating: 'GREEN' | 'YELLOW' | 'RED';
  message: string;
  recommendation?: string;
}

const ratingConfig = {
  GREEN: { color: 'bg-green-100 text-green-800 border-green-200', icon: CheckCircleIcon, label: 'Compliant' },
  YELLOW: { color: 'bg-yellow-100 text-yellow-800 border-yellow-200', icon: ExclamationTriangleIcon, label: 'Warning' },
  RED: { color: 'bg-red-100 text-red-800 border-red-200', icon: XCircleIcon, label: 'Critical' },
};

export function SecurityControlsEvaluate() {
  const [searchParams] = useSearchParams();
  const preselectedControl = searchParams.get('control');
  const queryClient = useQueryClient();

  const [selectedSystem, setSelectedSystem] = useState('');
  const [selectedClient, setSelectedClient] = useState('100');
  const [selectedControls, setSelectedControls] = useState<string[]>(
    preselectedControl ? [preselectedControl] : []
  );
  const [evaluationResults, setEvaluationResults] = useState<EvaluationResult[]>([]);
  const [evaluatedBy] = useState('admin@governexplus.com');

  // Fetch available systems
  const { data: systems } = useQuery({
    queryKey: ['systemProfiles'],
    queryFn: async () => {
      const response = await securityControlsApi.getSystemProfiles();
      return response.data.systems || [];
    },
  });

  // Fetch available controls
  const { data: controls, isLoading: controlsLoading } = useQuery({
    queryKey: ['securityControls'],
    queryFn: async () => {
      const response = await securityControlsApi.list({ limit: 500 });
      return response.data.items || [];
    },
  });

  // Batch evaluation mutation
  const evaluateMutation = useMutation({
    mutationFn: async () => {
      const evaluations = selectedControls.map(controlId => ({
        control_id: controlId,
      }));

      const response = await securityControlsApi.batchEvaluate({
        system_id: selectedSystem,
        client: selectedClient,
        evaluated_by: evaluatedBy,
        evaluations,
      });

      return response.data;
    },
    onSuccess: (data) => {
      // Map API response to expected format
      const results = (data.evaluations || []).map((eval: any) => ({
        control_id: eval.control_id,
        risk_rating: eval.risk_rating,
        message: eval.finding || eval.message || '',
        recommendation: eval.recommendation || '',
      }));
      setEvaluationResults(results);
      queryClient.invalidateQueries({ queryKey: ['securityControlsDashboard'] });
      queryClient.invalidateQueries({ queryKey: ['systemProfiles'] });
    },
  });

  const handleSelectAll = () => {
    if (controls) {
      if (selectedControls.length === controls.length) {
        setSelectedControls([]);
      } else {
        setSelectedControls(controls.map((c: Control) => c.control_id));
      }
    }
  };

  const handleToggleControl = (controlId: string) => {
    setSelectedControls(prev =>
      prev.includes(controlId)
        ? prev.filter(id => id !== controlId)
        : [...prev, controlId]
    );
  };

  const handleRunEvaluation = () => {
    if (selectedSystem && selectedControls.length > 0) {
      setEvaluationResults([]);
      evaluateMutation.mutate();
    }
  };

  const summaryStats = {
    total: evaluationResults.length,
    green: evaluationResults.filter(r => r.risk_rating === 'GREEN').length,
    yellow: evaluationResults.filter(r => r.risk_rating === 'YELLOW').length,
    red: evaluationResults.filter(r => r.risk_rating === 'RED').length,
  };

  // Group controls by category for better organization
  const controlsByCategory = controls?.reduce((acc: Record<string, Control[]>, control: Control) => {
    const cat = control.category || 'Uncategorized';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(control);
    return acc;
  }, {}) || {};

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Run Security Evaluation</h1>
          <p className="page-subtitle">
            Evaluate SAP system security controls and identify compliance gaps
          </p>
        </div>
        <Link to="/security-controls" className="btn-secondary">
          Back to Dashboard
        </Link>
      </div>

      {/* Configuration Panel */}
      <div className="card">
        <div className="card-header">
          <h2 className="section-title flex items-center gap-2">
            <ServerStackIcon className="h-5 w-5 text-gray-500" />
            Evaluation Configuration
          </h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* System Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Target System *
              </label>
              <select
                value={selectedSystem}
                onChange={(e) => setSelectedSystem(e.target.value)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
              >
                <option value="">Select a system...</option>
                {systems?.map((system: any) => (
                  <option key={system.system_id} value={system.system_id}>
                    {system.system_id} ({system.system_type || 'SAP'})
                  </option>
                ))}
                <option value="SAP_PRD_100">SAP_PRD_100 (Production)</option>
                <option value="SAP_DEV_200">SAP_DEV_200 (Development)</option>
                <option value="SAP_QAS_300">SAP_QAS_300 (Quality)</option>
              </select>
            </div>

            {/* Client Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Client
              </label>
              <select
                value={selectedClient}
                onChange={(e) => setSelectedClient(e.target.value)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
              >
                <option value="100">100 (Production)</option>
                <option value="200">200 (Development)</option>
                <option value="300">300 (Test)</option>
              </select>
            </div>

            {/* Controls Count */}
            <div className="flex items-end">
              <div className="p-3 bg-blue-50 rounded-lg flex-1">
                <div className="text-xs text-blue-600 font-medium">Selected Controls</div>
                <div className="text-2xl font-bold text-blue-700">
                  {selectedControls.length}
                  <span className="text-sm font-normal text-blue-500">
                    {' '}/ {controls?.length || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Run Button */}
          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-gray-500">
              {!selectedSystem && 'Please select a target system to continue'}
              {selectedSystem && selectedControls.length === 0 && 'Please select at least one control to evaluate'}
              {selectedSystem && selectedControls.length > 0 && `Ready to evaluate ${selectedControls.length} controls`}
            </div>
            <button
              onClick={handleRunEvaluation}
              disabled={!selectedSystem || selectedControls.length === 0 || evaluateMutation.isPending}
              className="btn-primary flex items-center gap-2"
            >
              {evaluateMutation.isPending ? (
                <>
                  <ArrowPathIcon className="h-4 w-4 animate-spin" />
                  Evaluating...
                </>
              ) : (
                <>
                  <PlayIcon className="h-4 w-4" />
                  Run Evaluation
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Results Panel (shown after evaluation) */}
      {evaluationResults.length > 0 && (
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="section-title flex items-center gap-2">
              <ClipboardDocumentCheckIcon className="h-5 w-5 text-gray-500" />
              Evaluation Results
            </h2>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1 text-xs">
                <span className="w-3 h-3 rounded-full bg-green-500"></span>
                {summaryStats.green} Compliant
              </span>
              <span className="flex items-center gap-1 text-xs">
                <span className="w-3 h-3 rounded-full bg-yellow-500"></span>
                {summaryStats.yellow} Warnings
              </span>
              <span className="flex items-center gap-1 text-xs">
                <span className="w-3 h-3 rounded-full bg-red-500"></span>
                {summaryStats.red} Critical
              </span>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Control ID
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Rating
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Message
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Recommendation
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {evaluationResults.map((result, idx) => {
                  const config = ratingConfig[result.risk_rating];
                  const Icon = config?.icon || CheckCircleIcon;
                  return (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap text-xs font-medium text-primary-600">
                        <Link to={`/security-controls/controls/${result.control_id}`}>
                          {result.control_id}
                        </Link>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border ${config?.color}`}>
                          <Icon className="h-3.5 w-3.5" />
                          {result.risk_rating}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-600 max-w-xs truncate">
                        {result.message}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">
                        {result.recommendation || '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Control Selection Panel */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h2 className="section-title flex items-center gap-2">
            <ShieldCheckIcon className="h-5 w-5 text-gray-500" />
            Select Controls to Evaluate
          </h2>
          <button
            onClick={handleSelectAll}
            className="text-xs text-primary-600 hover:text-primary-700 font-medium"
          >
            {selectedControls.length === controls?.length ? 'Deselect All' : 'Select All'}
          </button>
        </div>
        <div className="card-body">
          {controlsLoading ? (
            <div className="flex items-center justify-center py-8">
              <ArrowPathIcon className="h-6 w-6 animate-spin text-gray-400" />
              <span className="ml-2 text-sm text-gray-500">Loading controls...</span>
            </div>
          ) : Object.keys(controlsByCategory).length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <ShieldCheckIcon className="h-10 w-10 mx-auto text-gray-400 mb-2" />
              <p className="text-sm">No controls found. Import controls first.</p>
              <Link to="/security-controls/import" className="text-primary-600 text-sm hover:underline">
                Import Controls
              </Link>
            </div>
          ) : (
            <div className="space-y-4 max-h-[400px] overflow-y-auto">
              {Object.entries(controlsByCategory).map(([category, categoryControls]) => (
                <div key={category} className="border border-gray-200 rounded-lg">
                  <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
                    <h3 className="text-xs font-semibold text-gray-700">{category}</h3>
                  </div>
                  <div className="p-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                    {(categoryControls as Control[]).map((control) => (
                      <label
                        key={control.control_id}
                        className={`flex items-start gap-2 p-2 rounded border cursor-pointer transition-colors ${
                          selectedControls.includes(control.control_id)
                            ? 'bg-primary-50 border-primary-300'
                            : 'bg-white border-gray-200 hover:bg-gray-50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedControls.includes(control.control_id)}
                          onChange={() => handleToggleControl(control.control_id)}
                          className="mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-medium text-gray-900 truncate">
                            {control.control_id}
                          </div>
                          <div className="text-xs text-gray-500 truncate">
                            {control.name}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
