import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  BookOpenIcon, CheckCircleIcon, MagnifyingGlassIcon,
  SparklesIcon, ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolid } from '@heroicons/react/24/solid';
import api from '../../services/api';

interface LibraryItem {
  id: string;
  item_code: string;
  name: string;
  description: string;
  module: string;
  item_type: string;
  compliance_frameworks: string[];
  industry_tags: string[];
  severity?: string;
  activation_count: number;
  is_active: boolean;
  activation?: { is_customized: boolean; pending_update_version?: string } | null;
}

interface LibraryStats {
  total_library_items: number;
  active_for_tenant: number;
  customized: number;
  pending_updates: number;
  adoption_rate: number;
  by_module: Record<string, number>;
}

const MODULE_LABELS: Record<string, string> = {
  ara: 'Access Risk', arm: 'Access Requests', jml: 'Identity Lifecycle',
  certification: 'Certification', privileged_access: 'Privileged Access',
  risk_management: 'Risk Management', bcm: 'BCM', compliance: 'Compliance',
  survey: 'Survey', all: 'All Modules',
};

const TYPE_LABELS: Record<string, string> = {
  sod_rule: 'SoD Rule', mitigation: 'Mitigation', workflow: 'Workflow',
  risk_scenario: 'Risk Scenario', control: 'Control',
  certification_template: 'Certification', bia_template: 'BIA Template',
  bcm_plan_template: 'BCM Plan', survey_template: 'Survey',
  notification_template: 'Notification', report_template: 'Report',
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
};

export default function ContentLibrary() {
  const [search, setSearch] = useState('');
  const [module, setModule] = useState('');
  const [itemType, setItemType] = useState('');
  const [framework, setFramework] = useState('');
  const [page, setPage] = useState(1);
  const qc = useQueryClient();

  const { data: stats } = useQuery<LibraryStats>({
    queryKey: ['library-stats'],
    queryFn: () => api.get('/library/stats').then(r => r.data),
  });

  const { data, isLoading } = useQuery<{ items: LibraryItem[]; total: number; pages: number; facets: { modules: string[]; item_types: string[] } }>({
    queryKey: ['library-items', search, module, itemType, framework, page],
    queryFn: () => api.get('/library/items', {
      params: { search: search || undefined, module: module || undefined,
                item_type: itemType || undefined, compliance_framework: framework || undefined,
                page, page_size: 30 }
    }).then(r => r.data),
    placeholderData: (prev: any) => prev,
  });

  const activateMutation = useMutation({
    mutationFn: (itemId: string) => api.post(`/library/items/${itemId}/activate`),
    onSuccess: () => {
      toast.success('Item activated');
      qc.invalidateQueries({ queryKey: ['library-items'] });
      qc.invalidateQueries({ queryKey: ['library-stats'] });
    },
    onError: () => toast.error('Activation failed'),
  });

  const deactivateMutation = useMutation({
    mutationFn: (itemId: string) => api.post(`/library/items/${itemId}/deactivate`),
    onSuccess: () => {
      toast.success('Item deactivated');
      qc.invalidateQueries({ queryKey: ['library-items'] });
      qc.invalidateQueries({ queryKey: ['library-stats'] });
    },
    onError: () => toast.error('Deactivation failed'),
  });

  const items: LibraryItem[] = data?.items || [];
  const facets = data?.facets || { modules: [], item_types: [] };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookOpenIcon className="h-8 w-8 text-indigo-500" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Content Library</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Global template library — activate what you need, customize freely
            </p>
          </div>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Library Items', value: stats.total_library_items, icon: BookOpenIcon, color: 'indigo' },
            { label: 'Active for Tenant', value: stats.active_for_tenant, icon: CheckCircleIcon, color: 'green' },
            { label: 'Customized', value: stats.customized, icon: SparklesIcon, color: 'purple' },
            { label: 'Adoption Rate', value: `${stats.adoption_rate}%`, icon: ArrowPathIcon, color: 'blue' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-slate-700">
              <div className={`inline-flex p-2 rounded-lg bg-${color}-50 dark:bg-${color}-900/20 mb-2`}>
                <Icon className={`h-5 w-5 text-${color}-600 dark:text-${color}-400`} />
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">{value}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-slate-700">
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-48">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name, code, description..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); }}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <select value={module} onChange={e => { setModule(e.target.value); setPage(1); }}
            className="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none">
            <option value="">All Modules</option>
            {facets.modules.map((m: string) => <option key={m} value={m}>{MODULE_LABELS[m] || m}</option>)}
          </select>
          <select value={itemType} onChange={e => { setItemType(e.target.value); setPage(1); }}
            className="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none">
            <option value="">All Types</option>
            {facets.item_types.map((t: string) => <option key={t} value={t}>{TYPE_LABELS[t] || t}</option>)}
          </select>
          <select value={framework} onChange={e => { setFramework(e.target.value); setPage(1); }}
            className="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none">
            <option value="">All Frameworks</option>
            {['SOX', 'ISO27001', 'PCI-DSS', 'GDPR', 'COSO', 'ITGC', 'ISO22301', 'NIST-SP800-34'].map(f =>
              <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-gray-500 dark:text-gray-400">Loading library...</div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center text-gray-500 dark:text-gray-400">
            <BookOpenIcon className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p>No items found. Try adjusting filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-700">
              <thead className="bg-gray-50 dark:bg-slate-700/50">
                <tr>
                  {['Code', 'Name', 'Module', 'Type', 'Frameworks', 'Severity', 'Used By', 'Status', ''].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-slate-700">
                {items.map(item => (
                  <tr key={item.id} className={`hover:bg-gray-50 dark:hover:bg-slate-700/30 ${item.is_active ? 'bg-green-50/30 dark:bg-green-900/5' : ''}`}>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600 dark:text-gray-400">{item.item_code}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-sm text-gray-900 dark:text-white max-w-xs truncate">{item.name}</div>
                      {item.description && <div className="text-xs text-gray-500 dark:text-gray-400 max-w-xs truncate">{item.description}</div>}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{MODULE_LABELS[item.module] || item.module}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 rounded-full text-xs bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-300">
                        {TYPE_LABELS[item.item_type] || item.item_type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {item.compliance_frameworks.slice(0, 3).map(f => (
                          <span key={f} className="px-1.5 py-0.5 rounded text-xs bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-400">{f}</span>
                        ))}
                        {item.compliance_frameworks.length > 3 && (
                          <span className="text-xs text-gray-400">+{item.compliance_frameworks.length - 3}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {item.severity && (
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${SEVERITY_COLORS[item.severity] || ''}`}>
                          {item.severity}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{item.activation_count} tenants</td>
                    <td className="px-4 py-3">
                      {item.is_active ? (
                        <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
                          <CheckCircleSolid className="h-4 w-4" />
                          <span className="text-xs font-medium">Active</span>
                          {item.activation?.is_customized && (
                            <span className="ml-1 px-1 py-0.5 rounded text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300">Custom</span>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400 dark:text-gray-500">Inactive</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {item.is_active ? (
                        <button
                          onClick={() => deactivateMutation.mutate(item.id)}
                          disabled={deactivateMutation.isPending}
                          className="text-xs px-2 py-1 rounded border border-gray-300 dark:border-slate-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 disabled:opacity-50"
                        >
                          Deactivate
                        </button>
                      ) : (
                        <button
                          onClick={() => activateMutation.mutate(item.id)}
                          disabled={activateMutation.isPending}
                          className="text-xs px-2 py-1 rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                        >
                          Activate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="px-4 py-3 border-t border-gray-200 dark:border-slate-700 flex items-center justify-between">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {data.total} items · Page {page} of {data.pages}
            </span>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                className="px-3 py-1 text-sm rounded border border-gray-300 dark:border-slate-600 disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-700 dark:text-gray-300">
                Previous
              </button>
              <button onClick={() => setPage(p => Math.min(data.pages, p + 1))} disabled={page === data.pages}
                className="px-3 py-1 text-sm rounded border border-gray-300 dark:border-slate-600 disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-700 dark:text-gray-300">
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
