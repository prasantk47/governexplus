import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  CubeIcon, ArrowDownTrayIcon,
  CheckCircleIcon, SparklesIcon,
} from '@heroicons/react/24/outline';
import api from '../../services/api';

interface ActiveItem {
  activation_id: string;
  item_code: string;
  name: string;
  module: string;
  item_type: string;
  is_customized: boolean;
}

interface PackMeta {
  pack_code: string;
  name: string;
  version: string;
  description: string;
  author: string;
}

const MODULE_LABELS: Record<string, string> = {
  ara: 'Access Risk', arm: 'Access Requests', jml: 'Identity Lifecycle',
  eam: 'Emergency Access', certification: 'Certification',
  risk_management: 'Risk Management', process_control: 'Process Controls',
  bcm: 'BCM', tprm: 'Third-Party Risk', fraud: 'Fraud',
  compliance: 'Compliance', survey: 'Survey', shared: 'Shared', all: 'All Modules',
};

const TYPE_LABELS: Record<string, string> = {
  sod_rule: 'SoD Rule', mitigation: 'Mitigation', workflow: 'Workflow',
  access_policy: 'Access Policy', control: 'Control', kri: 'KRI',
  certification_template: 'Certification', risk_scenario: 'Risk Scenario',
  jml_policy: 'JML Policy', questionnaire: 'Questionnaire',
  notification: 'Notification', fraud_rule: 'Fraud Rule',
};

export default function PackBuilder() {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [moduleFilter, setModuleFilter] = useState('');
  const [meta, setMeta] = useState<PackMeta>({
    pack_code: '',
    name: '',
    version: '1.0.0',
    description: '',
    author: '',
  });
  const [exportedJson, setExportedJson] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['pack-builder-items'],
    queryFn: () => api.get('/library/pack-builder').then(r => r.data),
  });

  const exportMutation = useMutation({
    mutationFn: () => api.post('/library/packs/export', {
      pack_meta: meta,
      item_codes: Array.from(selected),
    }),
    onSuccess: (res) => {
      setExportedJson(JSON.stringify(res.data, null, 2));
      toast.success('Pack exported successfully');
    },
    onError: () => toast.error('Export failed'),
  });

  const items: ActiveItem[] = (data?.items || []).filter(
    (i: ActiveItem) => !moduleFilter || i.module === moduleFilter,
  );

  const allModules = [...new Set((data?.items || []).map((i: ActiveItem) => i.module))].sort() as string[];

  const toggleItem = (code: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };

  const selectAll = () => setSelected(new Set(items.map((i: ActiveItem) => i.item_code)));
  const clearAll = () => setSelected(new Set());

  const downloadJson = () => {
    if (!exportedJson) return;
    const blob = new Blob([exportedJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${meta.pack_code || 'custom_pack'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const isValid = meta.pack_code && meta.name && meta.version && selected.size > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <CubeIcon className="h-8 w-8 text-indigo-500" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Pack Builder</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Export your active and customized content as a portable pack JSON
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: item selector */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
            <div className="px-4 py-3 border-b border-gray-200 dark:border-slate-700 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <select
                  value={moduleFilter}
                  onChange={e => setModuleFilter(e.target.value)}
                  className="text-sm border border-gray-300 dark:border-slate-600 rounded-lg px-2 py-1.5 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  <option value="">All Modules</option>
                  {allModules.map(m => (
                    <option key={m} value={m}>{MODULE_LABELS[m] || m}</option>
                  ))}
                </select>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {selected.size} selected
                </span>
              </div>
              <div className="flex gap-2">
                <button onClick={selectAll}
                  className="text-xs px-2 py-1 rounded text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20">
                  Select all
                </button>
                <button onClick={clearAll}
                  className="text-xs px-2 py-1 rounded text-gray-500 hover:bg-gray-100 dark:hover:bg-slate-700">
                  Clear
                </button>
              </div>
            </div>

            {isLoading ? (
              <div className="p-8 text-center text-gray-500 dark:text-gray-400">Loading active content...</div>
            ) : items.length === 0 ? (
              <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                <CubeIcon className="h-10 w-10 mx-auto mb-2 opacity-30" />
                <p>No active items to export.</p>
                <a href="/library/wizard" className="text-sm text-indigo-600 hover:underline mt-2 inline-block">
                  Activate some items first →
                </a>
              </div>
            ) : (
              <div className="divide-y divide-gray-200 dark:divide-slate-700 max-h-[480px] overflow-y-auto">
                {items.map((item: ActiveItem) => (
                  <label
                    key={item.item_code}
                    className={`flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-slate-700/30
                      ${selected.has(item.item_code) ? 'bg-indigo-50/50 dark:bg-indigo-900/10' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(item.item_code)}
                      onChange={() => toggleItem(item.item_code)}
                      className="h-4 w-4 text-indigo-600 rounded border-gray-300 dark:border-slate-600 focus:ring-indigo-500"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm text-gray-900 dark:text-white truncate">{item.name}</span>
                        {item.is_customized && (
                          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                            <SparklesIcon className="h-3 w-3" /> Custom
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="font-mono text-xs text-gray-400">{item.item_code}</span>
                        <span className="text-xs text-gray-400">·</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">{MODULE_LABELS[item.module] || item.module}</span>
                        <span className="text-xs text-gray-400">·</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">{TYPE_LABELS[item.item_type] || item.item_type}</span>
                      </div>
                    </div>
                    {selected.has(item.item_code) && (
                      <CheckCircleIcon className="h-4 w-4 text-indigo-500 shrink-0" />
                    )}
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: pack metadata + export */}
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-5 space-y-4">
            <h2 className="font-semibold text-gray-900 dark:text-white text-sm">Pack Metadata</h2>

            {[
              { label: 'Pack Code *', key: 'pack_code', placeholder: 'MY_PACK_V1' },
              { label: 'Name *', key: 'name', placeholder: 'My Custom Pack' },
              { label: 'Version *', key: 'version', placeholder: '1.0.0' },
              { label: 'Author', key: 'author', placeholder: 'Your organization' },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</label>
                <input
                  type="text"
                  value={meta[key as keyof PackMeta]}
                  onChange={e => setMeta(m => ({ ...m, [key]: e.target.value }))}
                  placeholder={placeholder}
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
            ))}

            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Description</label>
              <textarea
                value={meta.description}
                onChange={e => setMeta(m => ({ ...m, description: e.target.value }))}
                placeholder="Brief description of this pack..."
                rows={3}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none resize-none"
              />
            </div>

            <div className="pt-2 space-y-2">
              <button
                onClick={() => exportMutation.mutate()}
                disabled={!isValid || exportMutation.isPending}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <CubeIcon className="h-4 w-4" />
                {exportMutation.isPending ? 'Exporting…' : `Export Pack (${selected.size} items)`}
              </button>
              {!isValid && (
                <p className="text-xs text-gray-400 text-center">
                  {selected.size === 0 ? 'Select at least one item' : 'Fill in required fields (*)'}
                </p>
              )}
            </div>
          </div>

          {/* Exported output */}
          {exportedJson && (
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-900 dark:text-white text-sm">Pack JSON</h2>
                <button
                  onClick={downloadJson}
                  className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-green-600 text-white hover:bg-green-700"
                >
                  <ArrowDownTrayIcon className="h-3.5 w-3.5" />
                  Download
                </button>
              </div>
              <pre className="text-xs font-mono bg-gray-50 dark:bg-slate-900 rounded-lg p-3 max-h-64 overflow-auto text-gray-700 dark:text-gray-300">
                {exportedJson.slice(0, 2000)}{exportedJson.length > 2000 ? '\n…' : ''}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
