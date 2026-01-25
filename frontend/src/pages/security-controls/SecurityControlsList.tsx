import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ShieldCheckIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
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
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<string>('');
  const [businessArea, setBusinessArea] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [page, setPage] = useState(0);
  const limit = 20;

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
      return response.data.categories || [];
    },
  });

  const { data: businessAreasData } = useQuery({
    queryKey: ['controlBusinessAreas'],
    queryFn: async () => {
      const response = await securityControlsApi.getBusinessAreas();
      return response.data.business_areas || [];
    },
  });

  const controls: Control[] = controlsData?.items || [];
  const total = controlsData?.total || 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Security Controls</h1>
          <p className="page-subtitle">
            Browse and manage SAP security controls ({total} total)
          </p>
        </div>
        <div className="flex space-x-2">
          <Link to="/security-controls" className="btn-secondary">
            Back to Dashboard
          </Link>
        </div>
      </div>

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
    </div>
  );
}
