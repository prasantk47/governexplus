/**
 * ML Model Management Page
 * View, train, and manage ML models
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  CpuChipIcon,
  PlayIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ChartBarIcon,
  ClockIcon,
  BeakerIcon,
  Cog6ToothIcon,
  DocumentChartBarIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';
import api from '../../services/api';

interface MLModel {
  model_id: string;
  model_type: string;
  status: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  auc_roc?: number;
  training_samples: number;
  features: number;
  last_trained: string;
  version: string;
  description: string;
}

interface TrainingJob {
  job_id: string;
  model_id: string;
  status: string;
  progress: number;
  started_at: string;
  estimated_completion: string;
}

export function ModelManagement() {
  const queryClient = useQueryClient();
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [trainingDays, setTrainingDays] = useState(90);

  // Fetch all models
  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ['mlModels'],
    queryFn: async () => {
      const response = await api.get('/ml/models');
      return response.data;
    },
  });

  // Fetch model details
  const { data: modelDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ['mlModelDetails', selectedModel],
    queryFn: async () => {
      const response = await api.get(`/ml/models/${selectedModel}`);
      return response.data;
    },
    enabled: !!selectedModel,
  });

  // Fetch training jobs
  const { data: trainingJobsData } = useQuery({
    queryKey: ['trainingJobs'],
    queryFn: async () => {
      const response = await api.get('/ml/models/training-jobs');
      return response.data;
    },
    refetchInterval: 5000, // Poll every 5 seconds for progress
  });

  // Fetch feature importance
  const { data: featureImportance } = useQuery({
    queryKey: ['featureImportance'],
    queryFn: async () => {
      const response = await api.get('/ml/analytics/feature-importance');
      return response.data;
    },
  });

  // Train model mutation
  const trainMutation = useMutation({
    mutationFn: async (modelId: string) => {
      const response = await api.post(`/ml/models/${modelId}/train`, null, {
        params: { training_days: trainingDays }
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trainingJobs'] });
    },
  });

  const models: MLModel[] = modelsData?.models || [];
  const trainingJobs: TrainingJob[] = trainingJobsData?.jobs || [];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'training':
        return <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'failed':
        return <ExclamationCircleIcon className="h-5 w-5 text-red-500" />;
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  const getMetricColor = (value: number) => {
    if (value >= 0.9) return 'text-green-600';
    if (value >= 0.8) return 'text-blue-600';
    if (value >= 0.7) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'access': return 'bg-blue-100 text-blue-700';
      case 'behavioral': return 'bg-purple-100 text-purple-700';
      case 'security': return 'bg-red-100 text-red-700';
      case 'temporal': return 'bg-green-100 text-green-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 rounded-lg">
            <CpuChipIcon className="h-6 w-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">ML Model Management</h1>
            <p className="text-sm text-gray-500">Monitor, train, and manage machine learning models</p>
          </div>
        </div>
        <Link to="/ml" className="btn-secondary">
          Back to ML Dashboard
        </Link>
      </div>

      {/* Training Jobs (if any active) */}
      {trainingJobs.filter(j => j.status === 'training' || j.status === 'queued').length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-blue-800 mb-3 flex items-center gap-2">
            <ArrowPathIcon className="h-5 w-5 animate-spin" />
            Active Training Jobs
          </h3>
          <div className="space-y-3">
            {trainingJobs
              .filter(j => j.status === 'training' || j.status === 'queued')
              .map((job) => (
                <div key={job.job_id} className="bg-white rounded-lg p-3 border border-blue-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-900">{job.model_id}</span>
                    <span className="text-xs text-blue-600">{job.status}</span>
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{job.progress}% complete</p>
                </div>
              ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Models List */}
        <div className="lg:col-span-1 bg-white rounded-lg border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-medium text-gray-900">Deployed Models</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {modelsLoading ? (
              <div className="p-4 text-center text-gray-500">Loading models...</div>
            ) : models.length === 0 ? (
              <div className="p-4 text-center text-gray-500">No models found</div>
            ) : (
              models.map((model) => (
                <button
                  key={model.model_id}
                  onClick={() => setSelectedModel(model.model_id)}
                  className={clsx(
                    'w-full p-4 text-left hover:bg-gray-50 transition-colors',
                    selectedModel === model.model_id && 'bg-primary-50'
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      {getStatusIcon(model.status)}
                      <div>
                        <p className="text-sm font-medium text-gray-900">{model.model_id}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{model.model_type}</p>
                        <p className="text-xs text-gray-400 mt-1">v{model.version}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={clsx('text-lg font-bold', getMetricColor(model.accuracy))}>
                        {(model.accuracy * 100).toFixed(1)}%
                      </p>
                      <p className="text-xs text-gray-500">accuracy</p>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Model Details */}
        <div className="lg:col-span-2 space-y-4">
          {!selectedModel ? (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
              <CpuChipIcon className="h-16 w-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Model</h3>
              <p className="text-sm text-gray-500">
                Select a model from the list to view details and performance metrics
              </p>
            </div>
          ) : detailsLoading ? (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
              <div className="animate-spin h-8 w-8 border-2 border-primary-500 border-t-transparent rounded-full mx-auto"></div>
              <p className="mt-4 text-gray-500">Loading model details...</p>
            </div>
          ) : modelDetails ? (
            <>
              {/* Model Header */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold text-gray-900">{modelDetails.model_id}</h3>
                      {getStatusIcon(modelDetails.status)}
                    </div>
                    <p className="text-sm text-gray-500 mt-1">{modelDetails.description}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                      <span>Version: {modelDetails.version}</span>
                      <span>Features: {modelDetails.features}</span>
                      <span>Samples: {modelDetails.training_samples.toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={trainingDays}
                      onChange={(e) => setTrainingDays(Number(e.target.value))}
                      className="text-sm border border-gray-300 rounded px-2 py-1"
                    >
                      <option value={30}>30 days</option>
                      <option value={60}>60 days</option>
                      <option value={90}>90 days</option>
                      <option value={180}>180 days</option>
                    </select>
                    <button
                      onClick={() => trainMutation.mutate(selectedModel)}
                      disabled={trainMutation.isPending}
                      className="btn-primary flex items-center gap-2"
                    >
                      {trainMutation.isPending ? (
                        <ArrowPathIcon className="h-4 w-4 animate-spin" />
                      ) : (
                        <PlayIcon className="h-4 w-4" />
                      )}
                      Retrain Model
                    </button>
                  </div>
                </div>
              </div>

              {/* Performance Metrics */}
              <div className="bg-white rounded-lg border border-gray-200">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h4 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                    <ChartBarIcon className="h-5 w-5 text-blue-500" />
                    Performance Metrics
                  </h4>
                </div>
                <div className="p-4 grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <p className={clsx('text-2xl font-bold', getMetricColor(modelDetails.accuracy))}>
                      {(modelDetails.accuracy * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Accuracy</p>
                  </div>
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <p className={clsx('text-2xl font-bold', getMetricColor(modelDetails.precision))}>
                      {(modelDetails.precision * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Precision</p>
                  </div>
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <p className={clsx('text-2xl font-bold', getMetricColor(modelDetails.recall))}>
                      {(modelDetails.recall * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Recall</p>
                  </div>
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <p className={clsx('text-2xl font-bold', getMetricColor(modelDetails.f1_score))}>
                      {(modelDetails.f1_score * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-gray-500 mt-1">F1 Score</p>
                  </div>
                  {modelDetails.auc_roc && (
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <p className={clsx('text-2xl font-bold', getMetricColor(modelDetails.auc_roc))}>
                        {(modelDetails.auc_roc * 100).toFixed(1)}%
                      </p>
                      <p className="text-xs text-gray-500 mt-1">AUC-ROC</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Training History */}
              <div className="bg-white rounded-lg border border-gray-200">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h4 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                    <ClockIcon className="h-5 w-5 text-orange-500" />
                    Training History
                  </h4>
                </div>
                <div className="p-4">
                  <div className="space-y-3">
                    {modelDetails.training_history?.map((entry: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                            v{entry.version}
                          </span>
                          <span className="text-sm text-gray-600">
                            {new Date(entry.date).toLocaleDateString()}
                          </span>
                        </div>
                        <span className={clsx('text-sm font-medium', getMetricColor(entry.accuracy))}>
                          {(entry.accuracy * 100).toFixed(1)}% accuracy
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Feature Importance */}
              <div className="bg-white rounded-lg border border-gray-200">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h4 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                    <DocumentChartBarIcon className="h-5 w-5 text-purple-500" />
                    Feature Importance
                  </h4>
                </div>
                <div className="p-4">
                  <div className="space-y-2">
                    {modelDetails.feature_importance?.slice(0, 10).map((feature: any) => (
                      <div key={feature.name} className="flex items-center gap-3">
                        <span className={clsx('px-2 py-0.5 rounded text-xs', getCategoryColor(feature.category))}>
                          {feature.category}
                        </span>
                        <span className="text-sm text-gray-700 flex-1">{feature.name.replace(/_/g, ' ')}</span>
                        <div className="w-32 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-primary-600 h-2 rounded-full"
                            style={{ width: `${feature.importance * 100 * 6.5}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500 w-12 text-right">
                          {(feature.importance * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Hyperparameters */}
              <div className="bg-white rounded-lg border border-gray-200">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h4 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                    <Cog6ToothIcon className="h-5 w-5 text-gray-500" />
                    Hyperparameters
                  </h4>
                </div>
                <div className="p-4">
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    {modelDetails.hyperparameters && Object.entries(modelDetails.hyperparameters).map(([key, value]) => (
                      <div key={key} className="text-center p-2 bg-gray-50 rounded">
                        <p className="text-sm font-medium text-gray-900">{String(value)}</p>
                        <p className="text-xs text-gray-500">{key.replace(/_/g, ' ')}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>

      {/* Global Feature Importance */}
      {featureImportance && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-medium text-gray-900 flex items-center gap-2">
              <BeakerIcon className="h-5 w-5 text-green-500" />
              Global Feature Importance (All Models)
            </h2>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              {featureImportance.top_categories?.map((cat: any) => (
                <div key={cat.category} className={clsx('p-4 rounded-lg', getCategoryColor(cat.category))}>
                  <p className="text-lg font-bold">{(cat.total_importance * 100).toFixed(1)}%</p>
                  <p className="text-xs capitalize">{cat.category}</p>
                  <p className="text-xs opacity-75">{cat.feature_count} features</p>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {featureImportance.features?.slice(0, 12).map((feature: any) => (
                <div key={feature.name} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                  <span className={clsx('px-1.5 py-0.5 rounded text-xs', getCategoryColor(feature.category))}>
                    {feature.category.slice(0, 3)}
                  </span>
                  <span className="text-sm text-gray-700 flex-1 truncate">{feature.name.replace(/_/g, ' ')}</span>
                  <span className="text-xs font-medium text-gray-600">{(feature.importance * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
