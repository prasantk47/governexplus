import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  MagnifyingGlassIcon,
  ShieldCheckIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  DocumentDuplicateIcon,
  BookOpenIcon,
  ArrowDownTrayIcon,
} from '@heroicons/react/24/outline';
import { securityControlsApi } from '../../services/api';

interface Control {
  id: number;
  control_id: string;
  control_name: string;
  business_area: string;
  control_type: string;
  category: string;
  description: string;
  profile_parameter: string | null;
  default_risk_rating: string;
  status: string;
  is_automated: boolean;
}

interface Template {
  control_id: string;
  control_name: string;
  category: string;
  description: string;
  profile_parameter?: string;
  expected_value?: string;
  default_risk_rating: string;
  is_automated: boolean;
  compliance_frameworks: string[];
}

const ratingConfig = {
  GREEN: { color: 'bg-green-100 text-green-800', icon: CheckCircleIcon },
  YELLOW: { color: 'bg-yellow-100 text-yellow-800', icon: ExclamationTriangleIcon },
  RED: { color: 'bg-red-100 text-red-800', icon: XCircleIcon },
};

const statusConfig = {
  active: { color: 'bg-green-100 text-green-800', label: 'Active' },
  inactive: { color: 'bg-gray-100 text-gray-800', label: 'Inactive' },
  draft: { color: 'bg-blue-100 text-blue-800', label: 'Draft' },
  deprecated: { color: 'bg-red-100 text-red-800', label: 'Deprecated' },
};

export function SecurityControlsList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'controls' | 'templates'>('controls');

  // My Controls state
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<string>('');
  const [businessArea, setBusinessArea] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [page, setPage] = useState(0);
  const limit = 20;

  // Template library state
  const [tplSearch, setTplSearch] = useState('');
  const [tplCategory, setTplCategory] = useState<string>('');
  const [tplFramework, setTplFramework] = useState<string>('');
  const [adoptingId, setAdoptingId] = useState<string | null>(null);

  const { data: controlsData, isLoading } = useQuery({
    queryKey: ['securityControls', { search, category, businessArea, status, page }],
    queryFn: async () => {
      const response = await securityControlsApi.list({
        search: search || undefined,
        category: category || undefined,
        business_area: businessArea || undefined,
        status: status || undefined,
        limit,
        offset: page * limit,
      });
      return response.data;
    },
  });

  const { data: categoriesData } = useQuery({
    queryKey: ['controlCategories'],
    queryFn: async () => {
      const response = await securityControlsApi.getCategories();
      return response.data?.categories || [];
    },
  });

  const { data: businessAreasData } = useQuery({
    queryKey: ['controlBusinessAreas'],
    queryFn: async () => {
      const response = await securityControlsApi.getBusinessAreas();
      return response.data?.business_areas || [];
    },
  });

  const controls: Control[] = controlsData?.items || [];
  const total = controlsData?.total || 0;
  const totalPages = Math.ceil(total / limit);

  // Template library queries
  const { data: templatesData, isLoading: tplLoading } = useQuery({
    queryKey: ['controlTemplates', { tplSearch, tplCategory, tplFramework }],
    queryFn: async () => {
      const response = await securityControlsApi.listTemplates({
        search: tplSearch || undefined,
        category: tplCategory || undefined,
        compliance_framework: tplFramework || undefined,
      });
      return response.data;
    },
    enabled: activeTab === 'templates',
  });

  const templates: Template[] = templatesData?.templates || [];
  const tplCategories: string[] = templatesData?.categories || [];

  const adoptMutation = useMutation({
    mutationFn: (controlId: string) => securityControlsApi.adoptTemplate(controlId),
    onMutate: (controlId) => setAdoptingId(controlId),
    onSuccess: (res) => {
      const ctrl = res.data?.control;
      const status = res.data?.status;
      if (status === 'existing') {
        toast.success('Already adopted — opening control');
      } else {
        toast.success(`Adopted as ${ctrl?.control_id}`);
        queryClient.invalidateQueries({ queryKey: ['securityControls'] });
      }
      if (ctrl?.control_id) navigate(`/security-controls/controls/${ctrl.control_id}`);
    },
    onError: () => toast.error('Failed to adopt template'),
    onSettled: () => setAdoptingId(null),
  });

  const seedMutation = useMutation({
    mutationFn: () => securityControlsApi.seedDefaults(),
    onSuccess: (res) => {
      const { inserted, skipped } = res.data;
      toast.success(`Seeded ${inserted} controls (${skipped} already existed)`);
      queryClient.invalidateQueries({ queryKey: ['securityControls'] });
    },
    onError: () => toast.error('Seed failed'),
  });

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Security Controls</h1>
          <p className="page-subtitle">
            {activeTab === 'controls'
              ? `Browse and manage your active SAP security controls (${total} total)`
              : 'Browse the built-in SAP control template library and adopt controls to your environment'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeTab === 'controls' && (
            <button
              onClick={() => seedMutation.mutate()}
              disabled={seedMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <ArrowDownTrayIcon className="h-3.5 w-3.5" />
              {seedMutation.isPending ? 'Seeding…' : 'Seed Defaults'}
            </button>
          )}
          <Link to="/security-controls" className="btn-secondary">
            Back to Dashboard
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('controls')}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'controls'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <ShieldCheckIcon className="h-4 w-4" />
          My Controls
        </button>
        <button
          onClick={() => setActiveTab('templates')}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'templates'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <BookOpenIcon className="h-4 w-4" />
          Template Library
          <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-primary-50 text-primary-700">47</span>
        </button>
      </div>

      {/* ── Template Library Tab ── */}
      {activeTab === 'templates' && (
        <>
          {/* Template Filters */}
          <div className="card">
            <div className="card-body">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="relative">
                  <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search templates…"
                    value={tplSearch}
                    onChange={(e) => setTplSearch(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <select
                  value={tplCategory}
                  onChange={(e) => setTplCategory(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">All Categories</option>
                  {tplCategories.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
                <select
                  value={tplFramework}
                  onChange={(e) => setTplFramework(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">All Frameworks</option>
                  {['SOX', 'ISO27001', 'PCI-DSS', 'NIST', 'GDPR', 'CCPA'].map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Template Table */}
          <div className="card">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-100">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Parameter</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Expected</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Risk</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Frameworks</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {tplLoading ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-500">
                        Loading templates…
                      </td>
                    </tr>
                  ) : templates.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-500">
                        <BookOpenIcon className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                        No templates match your filters.
                      </td>
                    </tr>
                  ) : (
                    templates.map((tpl) => (
                      <tr key={tpl.control_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-xs font-medium text-primary-600">{tpl.control_id}</span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="text-xs text-gray-900 max-w-xs truncate" title={tpl.control_name}>
                            {tpl.control_name}
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                          {tpl.category}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {tpl.profile_parameter && tpl.profile_parameter !== 'N/A' ? (
                            <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                              {tpl.profile_parameter}
                            </code>
                          ) : (
                            <span className="text-xs text-gray-400">N/A</span>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                          {tpl.expected_value || '—'}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${
                            ratingConfig[tpl.default_risk_rating as keyof typeof ratingConfig]?.color || 'bg-gray-100 text-gray-800'
                          }`}>
                            {tpl.default_risk_rating}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {tpl.compliance_frameworks.slice(0, 3).map((f) => (
                              <span key={f} className="inline-flex px-1 py-0.5 rounded text-xs bg-blue-50 text-blue-700">
                                {f}
                              </span>
                            ))}
                            {tpl.compliance_frameworks.length > 3 && (
                              <span className="text-xs text-gray-400">+{tpl.compliance_frameworks.length - 3}</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <button
                            onClick={() => adoptMutation.mutate(tpl.control_id)}
                            disabled={adoptingId === tpl.control_id}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md bg-primary-50 text-primary-700 hover:bg-primary-100 disabled:opacity-50 transition-colors"
                          >
                            <DocumentDuplicateIcon className="h-3.5 w-3.5" />
                            {adoptingId === tpl.control_id ? 'Adopting…' : 'Adopt'}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {!tplLoading && templates.length > 0 && (
              <div className="px-4 py-2 border-t border-gray-100 text-xs text-gray-500">
                {templates.length} template{templates.length !== 1 ? 's' : ''} — click <strong>Adopt</strong> to create a customizable copy in your environment
              </div>
            )}
          </div>
        </>
      )}

      {/* ── My Controls Tab ── */}
      {activeTab === 'controls' && (
        <>
      {/* Filters */}
      <div className="card">
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* Search */}
            <div className="md:col-span-2">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search controls..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(0);
                  }}
                  className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>

            {/* Category Filter */}
            <div>
              <select
                value={category}
                onChange={(e) => {
                  setCategory(e.target.value);
                  setPage(0);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">All Categories</option>
                {categoriesData?.map((cat: string) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            {/* Business Area Filter */}
            <div>
              <select
                value={businessArea}
                onChange={(e) => {
                  setBusinessArea(e.target.value);
                  setPage(0);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">All Business Areas</option>
                {businessAreasData?.map((area: string) => (
                  <option key={area} value={area}>
                    {area}
                  </option>
                ))}
              </select>
            </div>

            {/* Status Filter */}
            <div>
              <select
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value);
                  setPage(0);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="draft">Draft</option>
                <option value="deprecated">Deprecated</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Controls Table */}
      <div className="card">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Control ID
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Name
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Category
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Parameter
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Default Rating
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Automated
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                    Loading controls...
                  </td>
                </tr>
              ) : controls.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                    <ShieldCheckIcon className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                    No controls found. Try adjusting your filters or import controls.
                  </td>
                </tr>
              ) : (
                controls.map((control) => (
                  <tr key={control.control_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Link
                        to={`/security-controls/controls/${control.control_id}`}
                        className="text-xs font-medium text-primary-600 hover:text-primary-700"
                      >
                        {control.control_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-xs text-gray-900 max-w-xs truncate" title={control.control_name}>
                        {control.control_name}
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                      {control.category}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {control.profile_parameter && control.profile_parameter !== 'N/A' ? (
                        <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                          {control.profile_parameter}
                        </code>
                      ) : (
                        <span className="text-xs text-gray-400">N/A</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${
                          ratingConfig[control.default_risk_rating as keyof typeof ratingConfig]?.color ||
                          'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {control.default_risk_rating}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${
                          statusConfig[control.status as keyof typeof statusConfig]?.color ||
                          'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {statusConfig[control.status as keyof typeof statusConfig]?.label || control.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs">
                      {control.is_automated ? (
                        <span className="text-green-600">Yes</span>
                      ) : (
                        <span className="text-gray-400">No</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
            <div className="text-xs text-gray-500">
              Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} controls
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="p-1 rounded border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                <ChevronLeftIcon className="h-4 w-4" />
              </button>
              <span className="text-xs text-gray-600">
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                disabled={page >= totalPages - 1}
                className="p-1 rounded border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                <ChevronRightIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
        </div>
      </>
      )}
    </div>
  );
}
