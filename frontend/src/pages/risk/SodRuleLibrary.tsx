import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { riskApi, api } from '../../services/api';
import {
  ShieldExclamationIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  // FunnelIcon,
  PencilIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  PlayIcon,
  // CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';

interface SodRule {
  id: string;
  name: string;
  description: string;
  category: string;
  businessProcess: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  function1: { name: string; transactions: string[] };
  function2: { name: string; transactions: string[] };
  status: 'active' | 'inactive' | 'draft';
  violationCount: number;
  lastRun: string;
  createdBy: string;
  isCustom: boolean;
}

const SOD_CATEGORIES = [
  'Procure-to-Pay (P2P)',
  'Order-to-Cash (O2C)',
  'Hire-to-Retire (H2R)',
  'Record-to-Report (R2R)',
  'IT Administration',
  'Master Data',
];


interface RuleFormData {
  name: string;
  description: string;
  category: string;
  businessProcess: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  function1Name: string;
  function1Transactions: string;
  function2Name: string;
  function2Transactions: string;
  status: 'active' | 'inactive' | 'draft';
}

const emptyForm: RuleFormData = {
  name: '',
  description: '',
  category: '',
  businessProcess: '',
  severity: 'medium',
  function1Name: '',
  function1Transactions: '',
  function2Name: '',
  function2Transactions: '',
  status: 'draft',
};

function formFromRule(rule: SodRule): RuleFormData {
  return {
    name: rule.name,
    description: rule.description,
    category: rule.category,
    businessProcess: rule.businessProcess,
    severity: rule.severity,
    function1Name: rule.function1.name,
    function1Transactions: rule.function1.transactions.join(', '),
    function2Name: rule.function2.name,
    function2Transactions: rule.function2.transactions.join(', '),
    status: rule.status,
  };
}

function formToPayload(form: RuleFormData) {
  return {
    name: form.name,
    description: form.description,
    category: form.category,
    business_process: form.businessProcess,
    severity: form.severity,
    function1: {
      name: form.function1Name,
      transactions: form.function1Transactions.split(',').map((t) => t.trim()).filter(Boolean),
    },
    function2: {
      name: form.function2Name,
      transactions: form.function2Transactions.split(',').map((t) => t.trim()).filter(Boolean),
    },
    status: form.status,
  };
}

function RuleFormModal({
  title,
  initial,
  onClose,
  onSubmit,
  isSubmitting,
}: {
  title: string;
  initial: RuleFormData;
  onClose: () => void;
  onSubmit: (data: RuleFormData) => void;
  isSubmitting: boolean;
}) {
  const [form, setForm] = useState<RuleFormData>(initial);
  const set = (field: keyof RuleFormData, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XCircleIcon className="h-6 w-6" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rule Name *</label>
            <input type="text" value={form.name} onChange={(e) => set('name', e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea value={form.description} onChange={(e) => set('description', e.target.value)} rows={2}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select value={form.category} onChange={(e) => set('category', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500">
                <option value="">Select Category</option>
                {SOD_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Business Process</label>
              <input type="text" value={form.businessProcess} onChange={(e) => set('businessProcess', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Severity</label>
              <select value={form.severity} onChange={(e) => set('severity', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select value={form.status} onChange={(e) => set('status', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500">
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-red-700">Function 1</h4>
              <input type="text" placeholder="Function name" value={form.function1Name} onChange={(e) => set('function1Name', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm" />
              <input type="text" placeholder="Transactions (comma-separated)" value={form.function1Transactions} onChange={(e) => set('function1Transactions', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm" />
            </div>
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-orange-700">Function 2</h4>
              <input type="text" placeholder="Function name" value={form.function2Name} onChange={(e) => set('function2Name', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm" />
              <input type="text" placeholder="Transactions (comma-separated)" value={form.function2Transactions} onChange={(e) => set('function2Transactions', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm" />
            </div>
          </div>
        </div>
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3">
          <button onClick={onClose}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm">
            Cancel
          </button>
          <button onClick={() => onSubmit(form)} disabled={!form.name || isSubmitting}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm disabled:opacity-50">
            {isSubmitting ? 'Saving...' : 'Save Rule'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function SodRuleLibrary() {
  const queryClient = useQueryClient();
  const { data: rulesData } = useQuery({
    queryKey: ['sod-rules'],
    queryFn: () => riskApi.listRules().then(r => r.data),
  });
  const rules: SodRule[] = Array.isArray(rulesData) ? rulesData : (rulesData as any)?.rules || [];
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedRule, setSelectedRule] = useState<SodRule | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingRule, setEditingRule] = useState<SodRule | null>(null);
  const [deleteConfirmRule, setDeleteConfirmRule] = useState<SodRule | null>(null);

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: RuleFormData) => api.post('/risk-rules/custom', formToPayload(data)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sod-rules'] });
      toast.success('Rule created successfully');
      setShowCreateModal(false);
    },
    onError: () => toast.error('Failed to create rule'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: RuleFormData }) =>
      api.put(`/risk-rules/custom/${id}`, formToPayload(data)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sod-rules'] });
      toast.success('Rule updated successfully');
      setEditingRule(null);
    },
    onError: () => toast.error('Failed to update rule'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/risk-rules/custom/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sod-rules'] });
      toast.success('Rule deleted successfully');
      setDeleteConfirmRule(null);
    },
    onError: () => toast.error('Failed to delete rule'),
  });

  const runNowMutation = useMutation({
    mutationFn: () => api.post('/risk-rules/analyze', { scope: 'all' }),
    onSuccess: (res) => {
      const count = res.data?.violations_found ?? res.data?.total ?? 'N/A';
      toast.success(`Analysis complete. ${count} violations found.`);
      queryClient.invalidateQueries({ queryKey: ['sod-rules'] });
    },
    onError: () => toast.error('Analysis failed'),
  });

  const handleDuplicate = (rule: SodRule) => {
    setEditingRule(null);
    setShowCreateModal(true);
    // The create modal will be opened with pre-filled data via duplicateSource
    setDuplicateSource(rule);
  };
  const [duplicateSource, setDuplicateSource] = useState<SodRule | null>(null);

  const filteredRules = rules.filter(
    (rule) =>
      (rule.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        rule.description.toLowerCase().includes(searchTerm.toLowerCase())) &&
      (categoryFilter === '' || rule.category === categoryFilter) &&
      (severityFilter === '' || rule.severity === severityFilter) &&
      (statusFilter === '' || rule.status === statusFilter)
  );

  const stats = {
    total: rules.length,
    active: rules.filter((r) => r.status === 'active').length,
    critical: rules.filter((r) => r.severity === 'critical').length,
    violations: rules.reduce((acc, r) => acc + r.violationCount, 0),
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-green-100 text-green-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'inactive': return 'bg-gray-100 text-gray-800';
      default: return 'bg-blue-100 text-blue-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SoD Rule Library</h1>
          <p className="text-sm text-gray-500">
            Manage segregation of duties rules for risk detection
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm font-medium flex items-center gap-2"
        >
          <PlusIcon className="h-4 w-4" />
          Create Rule
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
          <div className="text-sm text-gray-500">Total Rules</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-green-600">{stats.active}</div>
          <div className="text-sm text-gray-500">Active Rules</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-red-600">{stats.critical}</div>
          <div className="text-sm text-gray-500">Critical Rules</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-orange-600">{stats.violations}</div>
          <div className="text-sm text-gray-500">Active Violations</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search rules..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All Categories</option>
            {SOD_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="draft">Draft</option>
          </select>
        </div>
      </div>

      {/* Rules Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rule</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Violations</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Run</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredRules.map((rule) => (
              <tr key={rule.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <ShieldExclamationIcon className={`h-5 w-5 ${
                      rule.severity === 'critical' ? 'text-red-500' :
                      rule.severity === 'high' ? 'text-orange-500' :
                      rule.severity === 'medium' ? 'text-yellow-500' :
                      'text-green-500'
                    }`} />
                    <div>
                      <div className="text-sm font-medium text-gray-900 flex items-center gap-2">
                        {rule.name}
                        {rule.isCustom && (
                          <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">Custom</span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500">{rule.id}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900">{rule.category}</div>
                  <div className="text-xs text-gray-500">{rule.businessProcess}</div>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getSeverityColor(rule.severity)}`}>
                    {rule.severity}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(rule.status)}`}>
                    {rule.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`text-sm font-medium ${rule.violationCount > 0 ? 'text-red-600' : 'text-gray-500'}`}>
                    {rule.violationCount}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  <div className="flex items-center gap-1">
                    <ClockIcon className="h-4 w-4" />
                    {rule.lastRun}
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => setSelectedRule(rule)}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="View Details"
                    >
                      <MagnifyingGlassIcon className="h-4 w-4" />
                    </button>
                    <button
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Run Now"
                      onClick={() => runNowMutation.mutate()}
                    >
                      <PlayIcon className="h-4 w-4" />
                    </button>
                    {rule.isCustom && (
                      <>
                        <button
                          className="p-1 text-gray-400 hover:text-blue-600"
                          title="Edit"
                          onClick={() => setEditingRule(rule)}
                        >
                          <PencilIcon className="h-4 w-4" />
                        </button>
                        <button
                          className="p-1 text-gray-400 hover:text-red-600"
                          title="Delete"
                          onClick={() => setDeleteConfirmRule(rule)}
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </>
                    )}
                    <button
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Duplicate"
                      onClick={() => handleDuplicate(rule)}
                    >
                      <DocumentDuplicateIcon className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Rule Detail Modal */}
      {selectedRule && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">{selectedRule.name}</h2>
                <button
                  onClick={() => setSelectedRule(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <XCircleIcon className="h-6 w-6" />
                </button>
              </div>
              <p className="text-sm text-gray-500 mt-1">{selectedRule.description}</p>
            </div>
            <div className="p-6 space-y-6">
              {/* Rule Details */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-xs text-gray-500">Category</span>
                  <p className="text-sm font-medium text-gray-900">{selectedRule.category}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Business Process</span>
                  <p className="text-sm font-medium text-gray-900">{selectedRule.businessProcess}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Severity</span>
                  <p><span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getSeverityColor(selectedRule.severity)}`}>{selectedRule.severity}</span></p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Status</span>
                  <p><span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(selectedRule.status)}`}>{selectedRule.status}</span></p>
                </div>
              </div>

              {/* Conflicting Functions */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-red-800 mb-2">Function 1: {selectedRule.function1.name}</h4>
                  <div className="space-y-1">
                    {selectedRule.function1.transactions.map((t, i) => (
                      <span key={i} className="inline-block text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded mr-1 mb-1">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-orange-800 mb-2">Function 2: {selectedRule.function2.name}</h4>
                  <div className="space-y-1">
                    {selectedRule.function2.transactions.map((t, i) => (
                      <span key={i} className="inline-block text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded mr-1 mb-1">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Stats */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold text-red-600">{selectedRule.violationCount}</p>
                    <p className="text-xs text-gray-500">Active Violations</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">{selectedRule.lastRun}</p>
                    <p className="text-xs text-gray-500">Last Run</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">{selectedRule.createdBy}</p>
                    <p className="text-xs text-gray-500">Created By</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={() => setSelectedRule(null)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm"
              >
                Close
              </button>
              <button
                onClick={() => { runNowMutation.mutate(); setSelectedRule(null); }}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm flex items-center gap-2"
              >
                <PlayIcon className="h-4 w-4" />
                Run Analysis
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create / Duplicate Rule Modal */}
      {showCreateModal && (
        <RuleFormModal
          title={duplicateSource ? `Duplicate Rule: ${duplicateSource.name}` : 'Create New Rule'}
          initial={duplicateSource ? { ...formFromRule(duplicateSource), name: `${duplicateSource.name} (Copy)`, status: 'draft' } : emptyForm}
          onClose={() => { setShowCreateModal(false); setDuplicateSource(null); }}
          onSubmit={(data) => createMutation.mutate(data)}
          isSubmitting={createMutation.isPending}
        />
      )}

      {/* Edit Rule Modal */}
      {editingRule && (
        <RuleFormModal
          title={`Edit Rule: ${editingRule.name}`}
          initial={formFromRule(editingRule)}
          onClose={() => setEditingRule(null)}
          onSubmit={(data) => updateMutation.mutate({ id: editingRule.id, data })}
          isSubmitting={updateMutation.isPending}
        />
      )}

      {/* Delete Confirmation */}
      {deleteConfirmRule && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Delete Rule</h2>
            <p className="text-sm text-gray-600 mb-4">
              Are you sure you want to delete <strong>{deleteConfirmRule.name}</strong>? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirmRule(null)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteConfirmRule.id)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
