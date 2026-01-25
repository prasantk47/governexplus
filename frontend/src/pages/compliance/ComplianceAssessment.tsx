import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  ClipboardDocumentCheckIcon,
  PlayIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import api from '../../services/api';

interface Framework {
  framework_id: string;
  name: string;
  short_name: string;
  description: string;
}

interface Objective {
  objective_id: string;
  reference_id: string;
  name: string;
  description: string;
  category: string;
  is_key_control: boolean;
  risk_level: string;
  status: string;
}

interface AssessmentResult {
  objective_id: string;
  reference_id: string;
  name: string;
  status: string;
  score: number;
  findings: string[];
  gaps: string[];
  recommendations: string[];
}

const statusConfig = {
  compliant: { color: 'bg-green-100 text-green-800 border-green-200', icon: CheckCircleIcon, label: 'Compliant' },
  partially_compliant: { color: 'bg-yellow-100 text-yellow-800 border-yellow-200', icon: ExclamationTriangleIcon, label: 'Partial' },
  non_compliant: { color: 'bg-red-100 text-red-800 border-red-200', icon: XCircleIcon, label: 'Non-Compliant' },
  not_assessed: { color: 'bg-gray-100 text-gray-800 border-gray-200', icon: DocumentTextIcon, label: 'Not Assessed' },
};

export function ComplianceAssessment() {
  const queryClient = useQueryClient();
  const [selectedFramework, setSelectedFramework] = useState('');
  const [selectedObjectives, setSelectedObjectives] = useState<string[]>([]);
  const [assessmentResults, setAssessmentResults] = useState<AssessmentResult[]>([]);
  const [expandedCategories, setExpandedCategories] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  // Fetch frameworks
  const { data: frameworksData, isLoading: frameworksLoading } = useQuery({
    queryKey: ['complianceFrameworks'],
    queryFn: async () => {
      const response = await api.get('/compliance/frameworks');
      return response.data;
    },
  });

  // Fetch objectives for selected framework
  const { data: objectivesData, isLoading: objectivesLoading } = useQuery({
    queryKey: ['complianceObjectives', selectedFramework],
    queryFn: async () => {
      const response = await api.get('/compliance/objectives', {
        params: { framework_id: selectedFramework }
      });
      return response.data;
    },
    enabled: !!selectedFramework,
  });

  const frameworks = frameworksData?.frameworks || [];
  const objectives = objectivesData?.objectives || [];

  // Group objectives by category
  const objectivesByCategory = objectives.reduce((acc: Record<string, Objective[]>, obj: Objective) => {
    const cat = obj.category || 'Uncategorized';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(obj);
    return acc;
  }, {});

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev =>
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  const handleSelectAll = () => {
    if (selectedObjectives.length === objectives.length) {
      setSelectedObjectives([]);
    } else {
      setSelectedObjectives(objectives.map((o: Objective) => o.objective_id));
    }
  };

  const handleToggleObjective = (objectiveId: string) => {
    setSelectedObjectives(prev =>
      prev.includes(objectiveId)
        ? prev.filter(id => id !== objectiveId)
        : [...prev, objectiveId]
    );
  };

  const handleRunAssessment = async () => {
    if (!selectedFramework || selectedObjectives.length === 0) return;

    setIsRunning(true);
    setAssessmentResults([]);

    try {
      // Simulate running assessments for each objective
      const results: AssessmentResult[] = [];

      for (const objectiveId of selectedObjectives) {
        const objective = objectives.find((o: Objective) => o.objective_id === objectiveId);
        if (!objective) continue;

        // Simulate assessment (in real app, would call API)
        const statuses = ['compliant', 'partially_compliant', 'non_compliant'];
        const randomStatus = statuses[Math.floor(Math.random() * 10) > 7 ? Math.floor(Math.random() * 3) : 0];
        const score = randomStatus === 'compliant' ? 100 : randomStatus === 'partially_compliant' ? 65 : 30;

        const result: AssessmentResult = {
          objective_id: objectiveId,
          reference_id: objective.reference_id,
          name: objective.name,
          status: randomStatus,
          score,
          findings: randomStatus !== 'compliant' ? [`Finding for ${objective.reference_id}`] : [],
          gaps: randomStatus === 'non_compliant' ? [`Gap identified in ${objective.reference_id}`] : [],
          recommendations: randomStatus !== 'compliant' ? [`Review and remediate ${objective.reference_id}`] : [],
        };

        results.push(result);

        // Create assessment via API
        try {
          await api.post(`/compliance/objectives/${objectiveId}/assessments`, {
            status: randomStatus,
            score,
            findings: result.findings,
            gaps: result.gaps,
            recommendations: result.recommendations,
          }, {
            params: { assessed_by: 'admin@governexplus.com' }
          });
        } catch (err) {
          console.error('Failed to save assessment:', err);
        }
      }

      setAssessmentResults(results);
      queryClient.invalidateQueries({ queryKey: ['complianceFrameworks'] });
      queryClient.invalidateQueries({ queryKey: ['complianceObjectives'] });
    } finally {
      setIsRunning(false);
    }
  };

  const summaryStats = {
    total: assessmentResults.length,
    compliant: assessmentResults.filter(r => r.status === 'compliant').length,
    partial: assessmentResults.filter(r => r.status === 'partially_compliant').length,
    nonCompliant: assessmentResults.filter(r => r.status === 'non_compliant').length,
  };

  const overallScore = assessmentResults.length > 0
    ? Math.round(assessmentResults.reduce((acc, r) => acc + r.score, 0) / assessmentResults.length)
    : 0;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Compliance Assessment</h1>
          <p className="page-subtitle">
            Assess compliance status against regulatory frameworks
          </p>
        </div>
        <Link to="/compliance" className="btn-secondary">
          Back to Dashboard
        </Link>
      </div>

      {/* Configuration Panel */}
      <div className="card">
        <div className="card-header">
          <h2 className="section-title flex items-center gap-2">
            <ShieldCheckIcon className="h-5 w-5 text-gray-500" />
            Assessment Configuration
          </h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Framework Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Framework *
              </label>
              <select
                value={selectedFramework}
                onChange={(e) => {
                  setSelectedFramework(e.target.value);
                  setSelectedObjectives([]);
                  setAssessmentResults([]);
                }}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                disabled={frameworksLoading}
              >
                <option value="">Select a framework...</option>
                {frameworks.map((fw: Framework) => (
                  <option key={fw.framework_id} value={fw.framework_id}>
                    {fw.short_name} - {fw.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Assessment Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Assessment Type
              </label>
              <select
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
              >
                <option value="full">Full Assessment</option>
                <option value="key_controls">Key Controls Only</option>
                <option value="gap_analysis">Gap Analysis</option>
              </select>
            </div>

            {/* Objectives Count */}
            <div className="flex items-end">
              <div className="p-3 bg-blue-50 rounded-lg flex-1">
                <div className="text-xs text-blue-600 font-medium">Selected Objectives</div>
                <div className="text-2xl font-bold text-blue-700">
                  {selectedObjectives.length}
                  <span className="text-sm font-normal text-blue-500">
                    {' '}/ {objectives.length || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Run Button */}
          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-gray-500">
              {!selectedFramework && 'Please select a framework to continue'}
              {selectedFramework && selectedObjectives.length === 0 && 'Please select at least one objective to assess'}
              {selectedFramework && selectedObjectives.length > 0 && `Ready to assess ${selectedObjectives.length} objectives`}
            </div>
            <button
              onClick={handleRunAssessment}
              disabled={!selectedFramework || selectedObjectives.length === 0 || isRunning}
              className="btn-primary flex items-center gap-2"
            >
              {isRunning ? (
                <>
                  <ArrowPathIcon className="h-4 w-4 animate-spin" />
                  Running Assessment...
                </>
              ) : (
                <>
                  <PlayIcon className="h-4 w-4" />
                  Run Assessment
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Results Panel */}
      {assessmentResults.length > 0 && (
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="section-title flex items-center gap-2">
              <ClipboardDocumentCheckIcon className="h-5 w-5 text-gray-500" />
              Assessment Results
            </h2>
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className={`text-2xl font-bold ${
                  overallScore >= 80 ? 'text-green-600' :
                  overallScore >= 60 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {overallScore}%
                </div>
                <div className="text-xs text-gray-500">Overall Score</div>
              </div>
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1 text-xs">
                  <span className="w-3 h-3 rounded-full bg-green-500"></span>
                  {summaryStats.compliant} Compliant
                </span>
                <span className="flex items-center gap-1 text-xs">
                  <span className="w-3 h-3 rounded-full bg-yellow-500"></span>
                  {summaryStats.partial} Partial
                </span>
                <span className="flex items-center gap-1 text-xs">
                  <span className="w-3 h-3 rounded-full bg-red-500"></span>
                  {summaryStats.nonCompliant} Non-Compliant
                </span>
              </div>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Reference
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Objective
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Score
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Findings
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {assessmentResults.map((result) => {
                  const config = statusConfig[result.status as keyof typeof statusConfig] || statusConfig.not_assessed;
                  const Icon = config.icon;
                  return (
                    <tr key={result.objective_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap text-xs font-medium text-primary-600">
                        {result.reference_id}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-600 max-w-xs truncate">
                        {result.name}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border ${config.color}`}>
                          <Icon className="h-3.5 w-3.5" />
                          {config.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                result.score >= 80 ? 'bg-green-500' :
                                result.score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                              }`}
                              style={{ width: `${result.score}%` }}
                            />
                          </div>
                          <span className="text-xs font-medium">{result.score}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {result.findings.length > 0 ? result.findings.join(', ') : '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Objectives Selection Panel */}
      {selectedFramework && (
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="section-title flex items-center gap-2">
              <DocumentTextIcon className="h-5 w-5 text-gray-500" />
              Select Control Objectives
            </h2>
            <button
              onClick={handleSelectAll}
              className="text-xs text-primary-600 hover:text-primary-700 font-medium"
            >
              {selectedObjectives.length === objectives.length ? 'Deselect All' : 'Select All'}
            </button>
          </div>
          <div className="card-body">
            {objectivesLoading ? (
              <div className="flex items-center justify-center py-8">
                <ArrowPathIcon className="h-6 w-6 animate-spin text-gray-400" />
                <span className="ml-2 text-sm text-gray-500">Loading objectives...</span>
              </div>
            ) : Object.keys(objectivesByCategory).length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <ShieldCheckIcon className="h-10 w-10 mx-auto text-gray-400 mb-2" />
                <p className="text-sm">No objectives found for this framework.</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {Object.entries(objectivesByCategory).map(([category, categoryObjectives]) => (
                  <div key={category} className="border border-gray-200 rounded-lg">
                    <button
                      onClick={() => toggleCategory(category)}
                      className="w-full px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between hover:bg-gray-100"
                    >
                      <h3 className="text-xs font-semibold text-gray-700">{category}</h3>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">
                          {(categoryObjectives as Objective[]).filter(o => selectedObjectives.includes(o.objective_id)).length} / {(categoryObjectives as Objective[]).length}
                        </span>
                        {expandedCategories.includes(category) ? (
                          <ChevronDownIcon className="h-4 w-4 text-gray-400" />
                        ) : (
                          <ChevronRightIcon className="h-4 w-4 text-gray-400" />
                        )}
                      </div>
                    </button>
                    {expandedCategories.includes(category) && (
                      <div className="p-3 space-y-2">
                        {(categoryObjectives as Objective[]).map((objective) => (
                          <label
                            key={objective.objective_id}
                            className={`flex items-start gap-2 p-2 rounded border cursor-pointer transition-colors ${
                              selectedObjectives.includes(objective.objective_id)
                                ? 'bg-primary-50 border-primary-300'
                                : 'bg-white border-gray-200 hover:bg-gray-50'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={selectedObjectives.includes(objective.objective_id)}
                              onChange={() => handleToggleObjective(objective.objective_id)}
                              className="mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-medium text-gray-900">
                                  {objective.reference_id}
                                </span>
                                {objective.is_key_control && (
                                  <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 text-xs rounded">
                                    Key Control
                                  </span>
                                )}
                                <span className={`px-1.5 py-0.5 text-xs rounded ${
                                  objective.risk_level === 'high' ? 'bg-red-100 text-red-700' :
                                  objective.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-green-100 text-green-700'
                                }`}>
                                  {objective.risk_level}
                                </span>
                              </div>
                              <div className="text-xs text-gray-500 truncate mt-0.5">
                                {objective.name}
                              </div>
                            </div>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
