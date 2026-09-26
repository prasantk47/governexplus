import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  MagnifyingGlassIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ChevronRightIcon,
  CubeIcon,
  ServerStackIcon,
  SwatchIcon,
  RectangleGroupIcon,
  DocumentTextIcon,
  LinkIcon,
  CircleStackIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  PageHeader,
  Card,
  Button,
  Badge,
  SearchInput,
} from '../../components/ui';

// ── Types ──────────────────────────────────────────────────────────────────────

interface FioriApp {
  id: string;
  title: string;
  semantic_object: string;
  semantic_action: string;
  catalog: string;
  space?: string;
  target_mapping?: string;
  odata_service?: string;
  backend_transactions: string[];
  auth_objects: string[];
  description?: string;
}

interface FioriCatalog {
  id: string;
  name: string;
  app_count: number;
  assigned_to: string[];
}

type LayerStatus = 'pass' | 'fail' | 'warning' | 'unknown';

interface ChainLayer {
  name: string;
  label: string;
  detail: string;
  status: LayerStatus;
  notes?: string;
}

interface TraceResult {
  user_id: string;
  app_id: string;
  overall: 'pass' | 'fail' | 'warning';
  layers: ChainLayer[];
  summary: string;
}

interface DiagnoseResult {
  user_id: string;
  app_id: string;
  root_cause: string;
  affected_layer: string;
  recommendation: string;
  missing_objects: string[];
}

// ── Layer status icon ─────────────────────────────────────────────────────────

const LAYER_ICONS: Record<string, React.FC<{ className?: string }>> = {
  launchpad: RectangleGroupIcon,
  business_role: ShieldCheckIcon,
  catalog: SwatchIcon,
  space_page: DocumentTextIcon,
  tile: CubeIcon,
  target_mapping: LinkIcon,
  odata_service: CircleStackIcon,
  backend_auth: ServerStackIcon,
};

function LayerStatusIcon({ status }: { status: LayerStatus }) {
  if (status === 'pass') return <CheckCircleIcon className="h-5 w-5 text-emerald-500" />;
  if (status === 'fail') return <XCircleIcon className="h-5 w-5 text-red-500" />;
  if (status === 'warning') return <ExclamationTriangleIcon className="h-5 w-5 text-amber-500" />;
  return <div className="h-5 w-5 rounded-full border-2 border-gray-300 bg-gray-50" />;
}

function layerStatusBadgeVariant(status: LayerStatus) {
  if (status === 'pass') return 'success' as const;
  if (status === 'fail') return 'danger' as const;
  if (status === 'warning') return 'warning' as const;
  return 'neutral' as const;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function FioriAnalyzer() {
  const [appSearch, setAppSearch] = useState('');
  const [catalogSearch, setCatalogSearch] = useState('');
  const [selectedApp, setSelectedApp] = useState<FioriApp | null>(null);
  const [userId, setUserId] = useState('');
  const [traceResult, setTraceResult] = useState<TraceResult | null>(null);
  const [diagnoseResult, setDiagnoseResult] = useState<DiagnoseResult | null>(null);
  const [activeTab, setActiveTab] = useState<'apps' | 'catalogs'>('apps');

  // ── Data queries ──────────────────────────────────────────────────────────
  const { data: appsData, isLoading: appsLoading } = useQuery<FioriApp[]>({
    queryKey: ['fiori-apps'],
    queryFn: () => api.get('/fiori/apps').then((r) => r.data),
  });

  const { data: catalogsData, isLoading: catalogsLoading } = useQuery<FioriCatalog[]>({
    queryKey: ['fiori-catalogs'],
    queryFn: () => api.get('/fiori/catalogs').then((r) => r.data),
  });

  const apps: FioriApp[] = appsData ?? [];
  const catalogs: FioriCatalog[] = catalogsData ?? [];

  // ── Mutations ─────────────────────────────────────────────────────────────
  const traceMutation = useMutation({
    mutationFn: (payload: { app_id: string; user_id: string }) =>
      api.post('/fiori/trace', payload).then((r) => r.data as TraceResult),
    onSuccess: (data) => {
      setTraceResult(data);
      setDiagnoseResult(null);
      toast.success('Access trace completed');
    },
    onError: () => {
      toast.error('Trace failed');
    },
  });

  const diagnoseMutation = useMutation({
    mutationFn: (payload: { app_id: string; user_id: string }) =>
      api.post('/fiori/diagnose', payload).then((r) => r.data as DiagnoseResult),
    onSuccess: (data) => {
      setDiagnoseResult(data);
      toast.success('Diagnosis complete');
    },
    onError: () => {
      toast.error('Diagnosis failed');
    },
  });

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleTrace = () => {
    if (!selectedApp || !userId.trim()) {
      toast.error('Select an app and enter a user ID before tracing');
      return;
    }
    traceMutation.mutate({ app_id: selectedApp.id, user_id: userId.trim() });
  };

  const handleDiagnose = () => {
    if (!selectedApp || !userId.trim()) {
      toast.error('Select an app and enter a user ID before diagnosing');
      return;
    }
    diagnoseMutation.mutate({ app_id: selectedApp.id, user_id: userId.trim() });
  };

  // ── Filtered lists ────────────────────────────────────────────────────────
  const filteredApps = apps.filter(
    (a) =>
      a.title.toLowerCase().includes(appSearch.toLowerCase()) ||
      a.id.toLowerCase().includes(appSearch.toLowerCase()) ||
      a.catalog.toLowerCase().includes(appSearch.toLowerCase())
  );

  const filteredCatalogs = catalogs.filter(
    (c) =>
      c.name.toLowerCase().includes(catalogSearch.toLowerCase()) ||
      c.id.toLowerCase().includes(catalogSearch.toLowerCase())
  );

  const isTracing = traceMutation.isPending;
  const isDiagnosing = diagnoseMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Fiori Security Analyzer"
        subtitle="Trace tile-to-backend authorization chains and diagnose access issues"
        breadcrumbs={[{ label: 'Intelligence' }, { label: 'Fiori Analyzer' }]}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Left panel: App / Catalog browser ── */}
        <div className="lg:col-span-1 space-y-4">
          {/* Tab switcher */}
          <div className="flex rounded-xl overflow-hidden border border-white/30 bg-white/30 backdrop-blur-sm">
            <button
              onClick={() => setActiveTab('apps')}
              className={`flex-1 px-4 py-2.5 text-xs font-semibold transition-all duration-200 ${
                activeTab === 'apps'
                  ? 'bg-white/80 text-primary-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Fiori Apps
            </button>
            <button
              onClick={() => setActiveTab('catalogs')}
              className={`flex-1 px-4 py-2.5 text-xs font-semibold transition-all duration-200 ${
                activeTab === 'catalogs'
                  ? 'bg-white/80 text-primary-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Catalogs
            </button>
          </div>

          {activeTab === 'apps' && (
            <Card padding="none">
              <div className="px-4 py-3 border-b border-white/20">
                <SearchInput
                  placeholder="Search apps..."
                  value={appSearch}
                  onChange={(e) => setAppSearch(e.target.value)}
                  onClear={() => setAppSearch('')}
                />
              </div>
              <div className="divide-y divide-gray-50/50 max-h-[480px] overflow-y-auto">
                {appsLoading ? (
                  <div className="flex items-center justify-center py-10">
                    <ArrowPathIcon className="h-6 w-6 animate-spin text-primary-500" />
                  </div>
                ) : filteredApps.length === 0 ? (
                  <p className="text-xs text-gray-400 text-center py-8">No apps found</p>
                ) : (
                  filteredApps.map((app) => (
                    <button
                      key={app.id}
                      onClick={() => {
                        setSelectedApp(app);
                        setTraceResult(null);
                        setDiagnoseResult(null);
                      }}
                      className={`w-full text-left px-4 py-3 transition-colors hover:bg-white/40 ${
                        selectedApp?.id === app.id ? 'bg-primary-50/60' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-primary-600">{app.id}</span>
                        {selectedApp?.id === app.id && (
                          <ChevronRightIcon className="h-3.5 w-3.5 text-primary-500" />
                        )}
                      </div>
                      <p className="text-sm font-medium text-gray-900 mt-0.5 leading-tight">{app.title}</p>
                      <p className="text-xs text-gray-400 mt-0.5 truncate">{app.catalog}</p>
                    </button>
                  ))
                )}
              </div>
            </Card>
          )}

          {activeTab === 'catalogs' && (
            <Card padding="none">
              <div className="px-4 py-3 border-b border-white/20">
                <SearchInput
                  placeholder="Search catalogs..."
                  value={catalogSearch}
                  onChange={(e) => setCatalogSearch(e.target.value)}
                  onClear={() => setCatalogSearch('')}
                />
              </div>
              <div className="divide-y divide-gray-50/50 max-h-[480px] overflow-y-auto">
                {catalogsLoading ? (
                  <div className="flex items-center justify-center py-10">
                    <ArrowPathIcon className="h-6 w-6 animate-spin text-primary-500" />
                  </div>
                ) : filteredCatalogs.length === 0 ? (
                  <p className="text-xs text-gray-400 text-center py-8">No catalogs found</p>
                ) : (
                  filteredCatalogs.map((cat) => (
                    <div key={cat.id} className="px-4 py-3">
                      <p className="text-sm font-medium text-gray-900">{cat.name}</p>
                      <p className="text-xs text-gray-400 truncate mt-0.5">{cat.id}</p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <Badge variant="neutral" size="sm">{cat.app_count} apps</Badge>
                        {cat.assigned_to.slice(0, 2).map((r) => (
                          <Badge key={r} variant="info" size="sm">{r}</Badge>
                        ))}
                        {cat.assigned_to.length > 2 && (
                          <Badge variant="neutral" size="sm">+{cat.assigned_to.length - 2}</Badge>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Card>
          )}
        </div>

        {/* ── Right panel: Trace / Results ── */}
        <div className="lg:col-span-2 space-y-4">
          {/* Trace panel */}
          <Card>
            <div className="px-6 py-4 border-b border-white/20">
              <h2 className="text-sm font-semibold text-gray-900">Trace Access Chain</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {selectedApp
                  ? `Selected: ${selectedApp.title} (${selectedApp.id})`
                  : 'Select an app from the browser to begin'}
              </p>
            </div>
            <div className="p-6">
              <div className="flex flex-col sm:flex-row gap-3">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-600 uppercase tracking-wider mb-1.5">
                    User ID
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. JSMITH or john.smith@corp.com"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    className="w-full rounded-xl px-3.5 py-2.5 text-sm bg-white/50 backdrop-blur-sm border border-white/40 focus:bg-white/70 focus:border-primary-400 focus:ring-2 focus:ring-primary-100 placeholder-gray-400 transition-all duration-200 outline-none"
                  />
                </div>
                <div className="flex items-end gap-2">
                  <Button
                    onClick={handleTrace}
                    loading={isTracing}
                    disabled={!selectedApp || !userId.trim()}
                    icon={<MagnifyingGlassIcon className="h-4 w-4" />}
                  >
                    Trace Access
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={handleDiagnose}
                    loading={isDiagnosing}
                    disabled={!selectedApp || !userId.trim()}
                    icon={<ExclamationTriangleIcon className="h-4 w-4" />}
                  >
                    Diagnose
                  </Button>
                </div>
              </div>
              <p className="mt-2 text-xs text-gray-400">
                Use <span className="font-medium text-gray-600">Diagnose</span> when a user sees the tile but gets an error on launch.
              </p>
            </div>
          </Card>

          {/* Selected app detail */}
          {selectedApp && !traceResult && !diagnoseResult && (
            <Card>
              <div className="px-6 py-4 border-b border-white/20">
                <h2 className="text-sm font-semibold text-gray-900">App Details</h2>
              </div>
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider">Semantic Object</p>
                    <p className="mt-1 font-medium text-gray-900">{selectedApp.semantic_object}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider">Action</p>
                    <p className="mt-1 font-medium text-gray-900">{selectedApp.semantic_action}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider">OData Service</p>
                    <p className="mt-1 font-mono text-xs text-primary-700 bg-primary-50/50 px-2 py-1 rounded-lg">
                      {selectedApp.odata_service ?? 'N/A'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider">Target Mapping</p>
                    <p className="mt-1 font-mono text-xs text-gray-700">{selectedApp.target_mapping ?? 'N/A'}</p>
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Backend Transactions</p>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedApp.backend_transactions.map((t) => (
                      <Badge key={t} variant="neutral" size="sm">
                        <span className="font-mono">{t}</span>
                      </Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Required Auth Objects</p>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedApp.auth_objects.map((o) => (
                      <Badge key={o} variant="info" size="sm">
                        <span className="font-mono">{o}</span>
                      </Badge>
                    ))}
                  </div>
                </div>

                {selectedApp.description && (
                  <p className="text-xs text-gray-500 border-t border-white/20 pt-3">{selectedApp.description}</p>
                )}
              </div>
            </Card>
          )}

          {/* Trace result — authorization chain */}
          {traceResult && (
            <Card>
              <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-gray-900">Authorization Chain</h2>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {traceResult.user_id} — {traceResult.app_id}
                  </p>
                </div>
                <Badge
                  variant={
                    traceResult.overall === 'pass'
                      ? 'success'
                      : traceResult.overall === 'warning'
                      ? 'warning'
                      : 'danger'
                  }
                >
                  {traceResult.overall === 'pass' ? 'Access Granted' : traceResult.overall === 'warning' ? 'Warning' : 'Access Denied'}
                </Badge>
              </div>
              <div className="p-6">
                {/* Chain visualization */}
                <div className="relative">
                  {traceResult.layers.map((layer, idx) => {
                    const Icon = LAYER_ICONS[layer.name] ?? ShieldCheckIcon;
                    const isLast = idx === traceResult.layers.length - 1;
                    return (
                      <div key={layer.name} className="flex items-start gap-4">
                        {/* Connector line + status icon */}
                        <div className="flex flex-col items-center">
                          <div
                            className={`flex-shrink-0 h-9 w-9 rounded-full flex items-center justify-center border-2 ${
                              layer.status === 'pass'
                                ? 'border-emerald-200 bg-emerald-50'
                                : layer.status === 'fail'
                                ? 'border-red-200 bg-red-50'
                                : layer.status === 'warning'
                                ? 'border-amber-200 bg-amber-50'
                                : 'border-gray-200 bg-gray-50'
                            }`}
                          >
                            <LayerStatusIcon status={layer.status} />
                          </div>
                          {!isLast && (
                            <div
                              className={`w-0.5 h-8 mt-1 ${
                                layer.status === 'pass' ? 'bg-emerald-200' : 'bg-gray-200'
                              }`}
                            />
                          )}
                        </div>

                        {/* Layer info */}
                        <div className={`pb-${isLast ? '0' : '2'} flex-1`}>
                          <div className="flex items-center gap-2 mb-0.5">
                            <Icon className="h-3.5 w-3.5 text-gray-400" />
                            <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
                              {layer.label}
                            </span>
                            <Badge variant={layerStatusBadgeVariant(layer.status)} size="sm">
                              {layer.status}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-600">{layer.detail}</p>
                          {layer.notes && (
                            <p className="mt-1 text-xs text-red-600 bg-red-50/60 rounded-lg px-2 py-1 border border-red-100">
                              {layer.notes}
                            </p>
                          )}
                          {!isLast && <div className="mt-2" />}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Summary */}
                <div
                  className={`mt-4 p-3 rounded-xl text-sm border ${
                    traceResult.overall === 'pass'
                      ? 'bg-emerald-50/60 border-emerald-200/60 text-emerald-800'
                      : 'bg-red-50/60 border-red-200/60 text-red-800'
                  }`}
                >
                  {traceResult.summary}
                </div>
              </div>
            </Card>
          )}

          {/* Diagnose result */}
          {diagnoseResult && (
            <Card>
              <div className="px-6 py-4 border-b border-white/20">
                <h2 className="text-sm font-semibold text-gray-900">Diagnosis — Root Cause Analysis</h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {diagnoseResult.user_id} sees tile but gets error on app launch
                </p>
              </div>
              <div className="p-6 space-y-4">
                <div className="p-3 bg-red-50/60 border border-red-200/60 rounded-xl">
                  <p className="text-xs font-semibold text-red-700 uppercase tracking-wider mb-1">Root Cause</p>
                  <p className="text-sm text-red-800">{diagnoseResult.root_cause}</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Affected Layer</p>
                    <Badge variant="danger">{diagnoseResult.affected_layer}</Badge>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Missing Auth Objects</p>
                    <div className="space-y-1">
                      {diagnoseResult.missing_objects.map((obj) => (
                        <p key={obj} className="font-mono text-xs bg-gray-100/60 text-gray-700 px-2 py-1 rounded-lg">
                          {obj}
                        </p>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-blue-50/60 border border-blue-200/60 rounded-xl">
                  <p className="text-xs font-semibold text-blue-700 uppercase tracking-wider mb-1">Recommendation</p>
                  <p className="text-sm text-blue-800">{diagnoseResult.recommendation}</p>
                </div>
              </div>
            </Card>
          )}

          {/* Empty state */}
          {!selectedApp && !traceResult && !diagnoseResult && (
            <Card>
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <SwatchIcon className="h-12 w-12 text-gray-300 mb-4" />
                <h3 className="text-sm font-medium text-gray-700 mb-1">Select a Fiori App</h3>
                <p className="text-xs text-gray-400 max-w-xs">
                  Choose a Fiori app from the browser on the left, then enter a user ID and click Trace Access to see the full authorization chain.
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
