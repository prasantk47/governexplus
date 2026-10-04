import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  CheckCircleIcon, SparklesIcon, DocumentTextIcon,
} from '@heroicons/react/24/outline';
import api from '../../services/api';

interface ActiveItem {
  activation_id: string;
  item_code: string;
  name: string;
  module: string;
  item_type: string;
  is_customized: boolean;
  effective_payload: Record<string, unknown>;
  mappings: Record<string, unknown>;
}

const MODULE_LABELS: Record<string, string> = {
  ara: 'Access Risk', arm: 'Access Requests', jml: 'Identity Lifecycle',
  certification: 'Certification', privileged_access: 'Privileged Access',
  risk_management: 'Risk Management', bcm: 'BCM', compliance: 'Compliance',
  survey: 'Survey', notification: 'Notifications', report: 'Reports',
};

const TYPE_LABELS: Record<string, string> = {
  sod_rule: 'SoD Rule', mitigation: 'Mitigation', workflow: 'Workflow',
  risk_scenario: 'Risk Scenario', control: 'Control',
  certification_template: 'Certification', bia_template: 'BIA Template',
  bcm_plan_template: 'BCM Plan', survey_template: 'Survey',
  notification_template: 'Notification', report_template: 'Report',
};

export default function ActiveContent() {
  const [module, setModule] = useState('');
  const [itemType, setItemType] = useState('');
  const [selectedItem, setSelectedItem] = useState<ActiveItem | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['active-content', module, itemType],
    queryFn: () => api.get('/library/active-content', {
      params: { module: module || undefined, item_type: itemType || undefined }
    }).then(r => r.data),
  });

  const items: ActiveItem[] = data?.items || [];
  const modules = [...new Set(items.map(i => i.module))].sort();
  const itemTypes = [...new Set(items.map(i => i.item_type))].sort();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CheckCircleIcon className="h-8 w-8 text-green-500" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Active Content</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Effective configuration running in your tenant — {items.length} active items
            </p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select value={module} onChange={e => setModule(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none">
          <option value="">All Modules</option>
          {modules.map(m => <option key={m} value={m}>{MODULE_LABELS[m] || m}</option>)}
        </select>
        <select value={itemType} onChange={e => setItemType(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none">
          <option value="">All Types</option>
          {itemTypes.map(t => <option key={t} value={t}>{TYPE_LABELS[t] || t}</option>)}
        </select>
        <span className="self-center text-sm text-gray-500 dark:text-gray-400">{items.length} items</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* List */}
        <div className="lg:col-span-1 space-y-2">
          {isLoading ? (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">Loading...</div>
          ) : items.length === 0 ? (
            <div className="bg-white dark:bg-slate-800 rounded-xl p-8 text-center border border-gray-100 dark:border-slate-700">
              <CheckCircleIcon className="h-10 w-10 mx-auto mb-2 text-gray-300" />
              <p className="text-gray-500 dark:text-gray-400 text-sm">No active content yet.</p>
              <a href="/library/wizard" className="mt-3 inline-block text-sm text-indigo-600 hover:underline">
                Run Activation Wizard →
              </a>
            </div>
          ) : (
            items.map(item => (
              <button
                key={item.activation_id}
                onClick={() => setSelectedItem(item)}
                className={`w-full text-left p-3 rounded-xl border transition-all
                  ${selectedItem?.activation_id === item.activation_id
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                    : 'border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-indigo-300'}`}
              >
                <div className="flex items-start gap-2">
                  <CheckCircleIcon className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-sm text-gray-900 dark:text-white truncate">{item.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{item.item_code}</div>
                  </div>
                </div>
                <div className="mt-2 flex gap-1.5">
                  <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300">
                    {MODULE_LABELS[item.module] || item.module}
                  </span>
                  {item.is_customized && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 flex items-center gap-0.5">
                      <SparklesIcon className="h-3 w-3" /> Custom
                    </span>
                  )}
                </div>
              </button>
            ))
          )}
        </div>

        {/* Detail */}
        <div className="lg:col-span-2">
          {selectedItem ? (
            <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-slate-700 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-mono text-xs text-gray-500 dark:text-gray-400">{selectedItem.item_code}</div>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white mt-1">{selectedItem.name}</h2>
                </div>
                <div className="flex gap-2">
                  <span className="px-2 py-1 rounded-lg text-xs bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300">
                    {TYPE_LABELS[selectedItem.item_type] || selectedItem.item_type}
                  </span>
                  {selectedItem.is_customized && (
                    <span className="px-2 py-1 rounded-lg text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300">
                      Customized
                    </span>
                  )}
                </div>
              </div>

              {Object.keys(selectedItem.mappings || {}).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Tenant Mappings</h3>
                  <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
                    {Object.entries(selectedItem.mappings).map(([k, v]) => (
                      <div key={k} className="flex gap-2 text-sm">
                        <span className="font-medium text-gray-600 dark:text-gray-400">{k}:</span>
                        <span className="text-gray-900 dark:text-white">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                  <DocumentTextIcon className="h-4 w-4" />
                  Effective Payload
                  {selectedItem.is_customized && <span className="text-xs text-purple-600 dark:text-purple-400">(customized)</span>}
                </h3>
                <pre className="bg-gray-50 dark:bg-slate-900 rounded-lg p-4 text-xs text-gray-800 dark:text-gray-200 overflow-auto max-h-96 font-mono">
                  {JSON.stringify(selectedItem.effective_payload, null, 2)}
                </pre>
              </div>

              <div className="flex gap-2">
                <a href={`/library/content`}
                  className="text-sm text-indigo-600 hover:text-indigo-700 dark:text-indigo-400">
                  Browse Library →
                </a>
              </div>
            </div>
          ) : (
            <div className="bg-white dark:bg-slate-800 rounded-xl p-12 text-center shadow-sm border border-gray-100 dark:border-slate-700">
              <DocumentTextIcon className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p className="text-gray-500 dark:text-gray-400">Select an item to view its effective payload</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
