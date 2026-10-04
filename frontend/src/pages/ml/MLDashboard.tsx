/**
 * ML Analytics Dashboard
 * GovernexPlus Machine Learning capabilities visualization
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  CpuChipIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  CircleStackIcon,
  SparklesIcon,
  CheckBadgeIcon,
} from '@heroicons/react/24/outline';
import { StatCard } from '../../components/StatCard';
import {
  PageHeader,
  Card,
  Badge,
  Table,
} from '../../components/ui';

// ─── Mock Data ────────────────────────────────────────────────────────────────

interface MlModel {
  id: string;
  model_name: string;
  model_type: 'anomaly' | 'clustering' | 'nlp' | 'risk_prediction';
  status: 'active' | 'training' | 'disabled';
  accuracy: number;
  last_trained: string;
  data_points: number;
  version: string;
}

interface AnomalyDetection {
  id: string;
  user_id: string;
  system: string;
  anomaly_type: string;
  confidence: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  detected_at: string;
  acknowledged: boolean;
}

const MOCK_MODELS: MlModel[] = [
  {
    id: '1',
    model_name: 'SoD Violation Predictor',
    model_type: 'risk_prediction',
    status: 'active',
    accuracy: 94.2,
    last_trained: '2026-09-28T08:00:00Z',
    data_points: 412_000,
    version: '3.1.2',
  },
  {
    id: '2',
    model_name: 'User Behaviour Anomaly Detector',
    model_type: 'anomaly',
    status: 'active',
    accuracy: 91.8,
    last_trained: '2026-10-01T03:00:00Z',
    data_points: 1_240_000,
    version: '2.4.0',
  },
  {
    id: '3',
    model_name: 'Role Clustering Engine',
    model_type: 'clustering',
    status: 'active',
    accuracy: 88.5,
    last_trained: '2026-09-25T12:00:00Z',
    data_points: 87_000,
    version: '1.8.1',
  },
  {
    id: '4',
    model_name: 'Audit NLP Summariser',
    model_type: 'nlp',
    status: 'active',
    accuracy: 87.1,
    last_trained: '2026-09-20T09:00:00Z',
    data_points: 63_000,
    version: '1.2.3',
  },
  {
    id: '5',
    model_name: 'Fraud Pattern Classifier',
    model_type: 'risk_prediction',
    status: 'training',
    accuracy: 79.3,
    last_trained: '2026-10-03T22:00:00Z',
    data_points: 195_000,
    version: '2.0.0-rc1',
  },
  {
    id: '6',
    model_name: 'Vendor Risk Scorer',
    model_type: 'risk_prediction',
    status: 'active',
    accuracy: 85.9,
    last_trained: '2026-09-15T07:00:00Z',
    data_points: 34_000,
    version: '1.5.0',
  },
];

const MOCK_ANOMALIES: AnomalyDetection[] = [
  {
    id: 'a1',
    user_id: 'BMILLER',
    system: 'SAP ECC',
    anomaly_type: 'Off-hours access surge',
    confidence: 97,
    severity: 'critical',
    detected_at: '2026-10-04T02:14:00Z',
    acknowledged: false,
  },
  {
    id: 'a2',
    user_id: 'JSMITH',
    system: 'SAP S/4HANA',
    anomaly_type: 'Unusual transaction volume',
    confidence: 88,
    severity: 'high',
    detected_at: '2026-10-03T16:42:00Z',
    acknowledged: false,
  },
  {
    id: 'a3',
    user_id: 'PATEL_K',
    system: 'Salesforce',
    anomaly_type: 'Bulk export from CRM',
    confidence: 82,
    severity: 'high',
    detected_at: '2026-10-03T11:28:00Z',
    acknowledged: false,
  },
  {
    id: 'a4',
    user_id: 'HWANG',
    system: 'SAP HR',
    anomaly_type: 'Privilege escalation pattern',
    confidence: 75,
    severity: 'medium',
    detected_at: '2026-10-02T09:05:00Z',
    acknowledged: true,
  },
  {
    id: 'a5',
    user_id: 'CHEN_W',
    system: 'Active Directory',
    anomaly_type: 'Dormant account activated',
    confidence: 69,
    severity: 'medium',
    detected_at: '2026-10-01T14:57:00Z',
    acknowledged: true,
  },
];

// ─── Constants ────────────────────────────────────────────────────────────────

const MODEL_TYPE_VARIANT: Record<MlModel['model_type'], 'info' | 'warning' | 'neutral' | 'danger'> = {
  anomaly: 'danger',
  clustering: 'info',
  nlp: 'neutral',
  risk_prediction: 'warning',
};

const MODEL_TYPE_LABEL: Record<MlModel['model_type'], string> = {
  anomaly: 'Anomaly Detection',
  clustering: 'Clustering',
  nlp: 'NLP',
  risk_prediction: 'Risk Prediction',
};

const MODEL_STATUS_VARIANT: Record<MlModel['status'], 'success' | 'warning' | 'neutral'> = {
  active: 'success',
  training: 'warning',
  disabled: 'neutral',
};

const SEVERITY_VARIANT: Record<AnomalyDetection['severity'], 'danger' | 'warning' | 'info' | 'success'> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'success',
};

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

// ─── Component ────────────────────────────────────────────────────────────────

export function MLDashboard() {
  const [acknowledgedIds, setAcknowledgedIds] = useState<Set<string>>(
    new Set(MOCK_ANOMALIES.filter(a => a.acknowledged).map(a => a.id))
  );

  // useQuery with initialData so it renders immediately without API calls
  const { data: models } = useQuery<MlModel[]>({
    queryKey: ['ml-models'],
    queryFn: () => Promise.resolve(MOCK_MODELS),
    initialData: MOCK_MODELS,
    staleTime: Infinity,
  });

  const { data: anomalies } = useQuery<AnomalyDetection[]>({
    queryKey: ['ml-anomalies'],
    queryFn: () => Promise.resolve(MOCK_ANOMALIES),
    initialData: MOCK_ANOMALIES,
    staleTime: Infinity,
  });

  // ── Stats ──

  const activeModels = (models ?? []).filter(m => m.status === 'active').length;
  const anomaliesDetected7d = (anomalies ?? []).length;
  const avgAccuracy = Math.round(
    (models ?? []).filter(m => m.status === 'active').reduce((s, m) => s + m.accuracy, 0) /
      Math.max(1, (models ?? []).filter(m => m.status === 'active').length)
  );
  const totalDataPoints = (models ?? []).reduce((s, m) => s + m.data_points, 0);

  // ── Model Columns ──

  const modelColumns = [
    {
      key: 'model_name',
      header: 'Model',
      render: (m: MlModel) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{m.model_name}</div>
          <div className="text-xs text-gray-400 font-mono">v{m.version}</div>
        </div>
      ),
    },
    {
      key: 'model_type',
      header: 'Type',
      render: (m: MlModel) => (
        <Badge variant={MODEL_TYPE_VARIANT[m.model_type]} size="sm">
          {MODEL_TYPE_LABEL[m.model_type]}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (m: MlModel) => (
        <div className="flex items-center gap-1.5">
          {m.status === 'training' && (
            <div className="h-2 w-2 rounded-full bg-yellow-400 animate-pulse" />
          )}
          <Badge variant={MODEL_STATUS_VARIANT[m.status]} dot={m.status !== 'training'} size="sm">
            {m.status}
          </Badge>
        </div>
      ),
    },
    {
      key: 'accuracy',
      header: 'Accuracy',
      render: (m: MlModel) => (
        <div className="flex items-center gap-2">
          <div className="w-20 h-1.5 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${m.accuracy >= 90 ? 'bg-green-500' : m.accuracy >= 80 ? 'bg-yellow-400' : 'bg-red-400'}`}
              style={{ width: `${m.accuracy}%` }}
            />
          </div>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{m.accuracy}%</span>
        </div>
      ),
    },
    {
      key: 'last_trained',
      header: 'Last Trained',
      render: (m: MlModel) => (
        <span className="text-sm text-gray-500">
          {new Date(m.last_trained).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'data_points',
      header: 'Data Points',
      render: (m: MlModel) => (
        <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
          {formatNumber(m.data_points)}
        </span>
      ),
    },
  ];

  const unacknowledged = (anomalies ?? []).filter(a => !acknowledgedIds.has(a.id));

  return (
    <div className="space-y-6">
      <PageHeader
        title="ML Analytics Dashboard"
        subtitle="Machine learning model performance, anomaly detections, and predictive insights"
      />

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard title="Models Active" value={activeModels} icon={CpuChipIcon} iconBgColor="stat-icon-indigo" iconColor="" />
        <StatCard title="Anomalies (7d)" value={anomaliesDetected7d} icon={ExclamationTriangleIcon} iconBgColor="stat-icon-red" iconColor="" />
        <StatCard title="Avg Accuracy" value={`${avgAccuracy}%`} icon={CheckBadgeIcon} iconBgColor="stat-icon-green" iconColor="" />
        <StatCard title="Data Points" value={formatNumber(totalDataPoints)} icon={CircleStackIcon} iconBgColor="stat-icon-blue" iconColor="" />
      </div>

      {/* ML Models Table */}
      <Card padding="none">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-slate-700 flex items-center gap-2">
          <CpuChipIcon className="h-5 w-5 text-indigo-500" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">ML Models</h2>
          <span className="ml-auto text-xs text-gray-400">{(models ?? []).length} models</span>
        </div>
        <Table
          columns={modelColumns}
          data={models ?? []}
          loading={false}
          emptyMessage="No models found."
        />
      </Card>

      {/* Anomaly Feed */}
      <Card padding="none">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-slate-700 flex items-center gap-2">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Recent Anomaly Detections</h2>
          {unacknowledged.length > 0 && (
            <span className="ml-auto inline-flex items-center gap-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-xs font-medium px-2 py-0.5 rounded-full">
              {unacknowledged.length} unreviewed
            </span>
          )}
        </div>

        <div className="divide-y divide-gray-100 dark:divide-slate-700/60">
          {(anomalies ?? []).map(anomaly => (
            <div
              key={anomaly.id}
              className={`px-5 py-4 flex items-start gap-4 ${
                acknowledgedIds.has(anomaly.id) ? 'opacity-60' : ''
              }`}
            >
              <div className={`h-2.5 w-2.5 rounded-full flex-shrink-0 mt-1.5 ${
                anomaly.severity === 'critical'
                  ? 'bg-red-500'
                  : anomaly.severity === 'high'
                  ? 'bg-orange-400'
                  : 'bg-yellow-400'
              }`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant={SEVERITY_VARIANT[anomaly.severity]} size="sm">
                    {anomaly.severity}
                  </Badge>
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {anomaly.anomaly_type}
                  </span>
                </div>
                <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
                  <span className="font-mono">{anomaly.user_id}</span>
                  <span>{anomaly.system}</span>
                  <span>Confidence: {anomaly.confidence}%</span>
                  <span>{new Date(anomaly.detected_at).toLocaleString()}</span>
                </div>
              </div>
              <button
                onClick={() => {
                  setAcknowledgedIds(prev => {
                    const next = new Set(prev);
                    if (next.has(anomaly.id)) {
                      next.delete(anomaly.id);
                    } else {
                      next.add(anomaly.id);
                    }
                    return next;
                  });
                }}
                className={`flex-shrink-0 text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  acknowledgedIds.has(anomaly.id)
                    ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                    : 'bg-indigo-100 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400 hover:bg-indigo-200 dark:hover:bg-indigo-900/40'
                }`}
              >
                {acknowledgedIds.has(anomaly.id) ? (
                  <span className="flex items-center gap-1">
                    <SparklesIcon className="h-3.5 w-3.5" /> Reviewed
                  </span>
                ) : 'Investigate'}
              </button>
            </div>
          ))}
        </div>

        {(anomalies ?? []).length === 0 && (
          <div className="text-center py-10 text-gray-400">
            <ShieldCheckIcon className="h-10 w-10 mx-auto mb-2 opacity-40" />
            <p className="text-sm">No anomalies detected recently. Systems are healthy.</p>
          </div>
        )}
      </Card>

      {/* Model Performance Summary */}
      <Card padding="md">
        <div className="flex items-center gap-2 mb-5">
          <ChartBarIcon className="h-5 w-5 text-indigo-500" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Model Performance Summary</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {(models ?? [])
            .filter(m => m.status === 'active')
            .slice(0, 4)
            .map(m => (
              <div key={m.id} className="text-center p-4 bg-gray-50 dark:bg-slate-800 rounded-xl">
                <p className={`text-2xl font-bold ${m.accuracy >= 90 ? 'text-green-600' : m.accuracy >= 80 ? 'text-yellow-600' : 'text-red-600'}`}>
                  {m.accuracy}%
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-tight">{m.model_name}</p>
              </div>
            ))}
        </div>
      </Card>
    </div>
  );
}

export default MLDashboard;
