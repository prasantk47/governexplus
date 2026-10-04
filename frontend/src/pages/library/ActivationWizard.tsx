import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  RocketLaunchIcon, CheckCircleIcon, ChevronRightIcon,
  ChevronLeftIcon, SparklesIcon,
} from '@heroicons/react/24/outline';
import api from '../../services/api';

interface LibraryItem {
  id: string;
  item_code: string;
  name: string;
  module: string;
  item_type: string;
  compliance_frameworks: string[];
  severity?: string;
  is_active: boolean;
}

const WIZARD_MODULES = [
  { id: 'ara', label: 'Access Risk (SoD Rules)', types: ['sod_rule', 'mitigation'] },
  { id: 'arm', label: 'Access Requests (Workflows)', types: ['workflow'] },
  { id: 'certification', label: 'Certification Templates', types: ['certification_template', 'workflow'] },
  { id: 'privileged_access', label: 'Privileged Access', types: ['workflow', 'notification_template'] },
  { id: 'jml', label: 'Identity Lifecycle', types: ['workflow'] },
  { id: 'risk_management', label: 'Risk Scenarios', types: ['risk_scenario'] },
  { id: 'compliance', label: 'Controls', types: ['control'] },
  { id: 'bcm', label: 'BCM Templates', types: ['bia_template', 'bcm_plan_template'] },
];

const FRAMEWORKS = ['SOX', 'ISO27001', 'PCI-DSS', 'GDPR', 'COSO', 'ITGC', 'ISO22301'];

export default function ActivationWizard() {
  const [step, setStep] = useState<'framework' | 'modules' | 'preview' | 'done'>('framework');
  const [selectedFrameworks, setSelectedFrameworks] = useState<Set<string>>(new Set(['SOX']));
  const [selectedModules, setSelectedModules] = useState<Set<string>>(new Set(['ara', 'arm', 'certification', 'privileged_access']));
  const [activatedCount, setActivatedCount] = useState(0);
  const qc = useQueryClient();

  // Fetch items matching selected frameworks + modules
  const { data: previewData, isLoading: previewLoading } = useQuery({
    queryKey: ['wizard-preview', Array.from(selectedFrameworks), Array.from(selectedModules)],
    queryFn: async () => {
      // Fetch all items for selected modules (no framework filter — filter client-side for multi-select)
      const allItems: LibraryItem[] = [];
      for (const mod of Array.from(selectedModules)) {
        const res = await api.get('/library/items', { params: { module: mod, page_size: 200 } });
        allItems.push(...(res.data.items || []));
      }
      // Filter by framework
      if (selectedFrameworks.size === 0) return allItems.filter(i => !i.is_active);
      return allItems.filter(i =>
        !i.is_active &&
        i.compliance_frameworks.some(f => selectedFrameworks.has(f))
      );
    },
    enabled: step === 'preview',
  });

  const bulkActivateMutation = useMutation({
    mutationFn: (itemIds: string[]) => api.post('/library/activate-bulk', { item_ids: itemIds }),
    onSuccess: (res) => {
      setActivatedCount(res.data.activated || 0);
      setStep('done');
      qc.invalidateQueries({ queryKey: ['library-items'] });
      qc.invalidateQueries({ queryKey: ['library-stats'] });
      toast.success(`${res.data.activated} templates activated!`);
    },
    onError: () => toast.error('Bulk activation failed'),
  });

  const previewItems: LibraryItem[] = previewData || [];

  const toggleFramework = (f: string) => {
    setSelectedFrameworks(prev => {
      const next = new Set(prev);
      next.has(f) ? next.delete(f) : next.add(f);
      return next;
    });
  };

  const toggleModule = (m: string) => {
    setSelectedModules(prev => {
      const next = new Set(prev);
      next.has(m) ? next.delete(m) : next.add(m);
      return next;
    });
  };

  const handleActivate = () => {
    const ids = previewItems.map(i => i.id);
    if (!ids.length) { toast.error('No items to activate'); return; }
    bulkActivateMutation.mutate(ids);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <RocketLaunchIcon className="h-8 w-8 text-indigo-500" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Activation Wizard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Activate the right templates for your compliance programme in minutes
          </p>
        </div>
      </div>

      {/* Progress */}
      <div className="flex items-center gap-2">
        {(['framework', 'modules', 'preview', 'done'] as const).map((s, i) => (
          <React.Fragment key={s}>
            <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium
              ${step === s ? 'bg-indigo-600 text-white' :
                ['framework', 'modules', 'preview', 'done'].indexOf(step) > i ? 'bg-green-500 text-white' :
                'bg-gray-200 dark:bg-slate-600 text-gray-500 dark:text-gray-400'}`}>
              {['framework', 'modules', 'preview', 'done'].indexOf(step) > i ? '✓' : i + 1}
            </div>
            {i < 3 && <div className={`flex-1 h-1 rounded ${['framework', 'modules', 'preview', 'done'].indexOf(step) > i ? 'bg-green-500' : 'bg-gray-200 dark:bg-slate-700'}`} />}
          </React.Fragment>
        ))}
      </div>
      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 px-1">
        <span>Frameworks</span><span>Modules</span><span>Preview</span><span>Done</span>
      </div>

      {/* Step: Framework */}
      {step === 'framework' && (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-slate-700 space-y-4">
          <h2 className="font-semibold text-gray-900 dark:text-white">Which compliance frameworks apply to your organization?</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {FRAMEWORKS.map(f => (
              <button key={f} onClick={() => toggleFramework(f)}
                className={`p-3 rounded-lg border-2 text-sm font-medium transition-all
                  ${selectedFrameworks.has(f)
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                    : 'border-gray-200 dark:border-slate-600 text-gray-700 dark:text-gray-300 hover:border-indigo-300'}`}>
                {selectedFrameworks.has(f) && <CheckCircleIcon className="h-4 w-4 inline mr-1 text-indigo-500" />}
                {f}
              </button>
            ))}
          </div>
          <div className="flex justify-end">
            <button onClick={() => setStep('modules')} disabled={selectedFrameworks.size === 0}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
              Next <ChevronRightIcon className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step: Modules */}
      {step === 'modules' && (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-slate-700 space-y-4">
          <h2 className="font-semibold text-gray-900 dark:text-white">Which modules are in scope for your deployment?</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {WIZARD_MODULES.map(m => (
              <button key={m.id} onClick={() => toggleModule(m.id)}
                className={`p-4 rounded-lg border-2 text-left transition-all
                  ${selectedModules.has(m.id)
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                    : 'border-gray-200 dark:border-slate-600 hover:border-indigo-300'}`}>
                <div className="flex items-center gap-2">
                  {selectedModules.has(m.id) && <CheckCircleIcon className="h-5 w-5 text-indigo-500 shrink-0" />}
                  <span className="font-medium text-sm text-gray-900 dark:text-white">{m.label}</span>
                </div>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {m.types.join(', ')}
                </div>
              </button>
            ))}
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep('framework')} className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700">
              <ChevronLeftIcon className="h-4 w-4" /> Back
            </button>
            <button onClick={() => setStep('preview')} disabled={selectedModules.size === 0}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
              Preview Templates <ChevronRightIcon className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step: Preview */}
      {step === 'preview' && (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-slate-700 space-y-4">
          <h2 className="font-semibold text-gray-900 dark:text-white">
            {previewLoading ? 'Loading...' : `${previewItems.length} templates will be activated`}
          </h2>
          {!previewLoading && (
            <div className="max-h-80 overflow-y-auto space-y-1">
              {previewItems.map(item => (
                <div key={item.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700/30">
                  <CheckCircleIcon className="h-4 w-4 text-green-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-gray-900 dark:text-white font-medium">{item.name}</span>
                    <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">{item.item_code}</span>
                  </div>
                  {item.severity && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300">
                      {item.severity}
                    </span>
                  )}
                </div>
              ))}
              {previewItems.length === 0 && (
                <p className="text-center text-gray-500 dark:text-gray-400 py-8">
                  All matching templates are already active.
                </p>
              )}
            </div>
          )}
          <div className="flex justify-between">
            <button onClick={() => setStep('modules')} className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700">
              <ChevronLeftIcon className="h-4 w-4" /> Back
            </button>
            <button onClick={handleActivate} disabled={bulkActivateMutation.isPending || previewItems.length === 0}
              className="flex items-center gap-2 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 font-medium">
              {bulkActivateMutation.isPending ? 'Activating...' : `Activate ${previewItems.length} Templates`}
              <RocketLaunchIcon className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step: Done */}
      {step === 'done' && (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-12 shadow-sm border border-gray-100 dark:border-slate-700 text-center space-y-4">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30">
            <SparklesIcon className="h-8 w-8 text-green-600 dark:text-green-400" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            {activatedCount} templates activated!
          </h2>
          <p className="text-gray-500 dark:text-gray-400">
            Your tenant's content library is ready. You can browse and customize individual items in the Content Library.
          </p>
          <div className="flex gap-3 justify-center">
            <a href="/library/content" className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
              View Active Content
            </a>
            <button onClick={() => setStep('framework')} className="px-4 py-2 border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700">
              Run Wizard Again
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
