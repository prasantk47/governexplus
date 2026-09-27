import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { riskApi, api } from '../../services/api';
import toast from 'react-hot-toast';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ShieldExclamationIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

interface SodRule {
  id: string;
  name: string;
  description: string;
  category: string;
  riskLevel: 'high' | 'critical';
  function1: string;
  function2: string;
  system: string;
  status: 'active' | 'inactive' | 'draft';
  violations: number;
  lastModified: string;
  owner: string;
}


const riskConfig = {
  high: { color: 'bg-orange-100 text-orange-800', label: 'High Risk' },
  critical: { color: 'bg-red-100 text-red-800', label: 'Critical Risk' },
};

const statusConfig = {
  active: { color: 'bg-green-100 text-green-800', label: 'Active' },
  inactive: { color: 'bg-gray-100 text-gray-800', label: 'Inactive' },
  draft: { color: 'bg-yellow-100 text-yellow-800', label: 'Draft' },
};

interface RuleFormData {
  name: string;
  description: string;
  severity: string;
  rule_definition: { function1: string; function2: string };
  applies_to_systems: string[];
  is_enabled: boolean;
}

const emptyFormData: RuleFormData = {
  name: '',
  description: '',
  severity: 'high',
  rule_definition: { function1: '', function2: '' },
  applies_to_systems: ['*'],
  is_enabled: true,
};

export function RiskRules() {
  const queryClient = useQueryClient();
  const { data: rulesData } = useQuery({
    queryKey: ['risk-rules'],
    queryFn: () => riskApi.listRules().then(r => r.data),
  });
  const rules: SodRule[] = Array.isArray(rulesData) ? rulesData : (rulesData as any)?.rules || [];

  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [systemFilter, setSystemFilter] = useState<string>('all');

  // Modal state
  const [showFormModal, setShowFormModal] = useState(false);
  const [editingRule, setEditingRule] = useState<SodRule | null>(null);
  const [formData, setFormData] = useState<RuleFormData>(emptyFormData);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const openCreateModal = () => {
    setEditingRule(null);
    setFormData(emptyFormData);
    setShowFormModal(true);
  };

  const openEditModal = (rule: SodRule) => {
    setEditingRule(rule);
    setFormData({
      name: rule.name,
      description: rule.description,
      severity: rule.riskLevel,
      rule_definition: { function1: rule.function1, function2: rule.function2 },
      applies_to_systems: [rule.system],
      is_enabled: rule.status === 'active',
    });
    setShowFormModal(true);
  };

  const handleFormSubmit = async () => {
    if (!formData.name.trim()) { toast.error('Rule name is required'); return; }
    setFormSubmitting(true);
    try {
      const payload = {
        name: formData.name,
        description: formData.description,
        severity: formData.severity,
        rule_definition: formData.rule_definition,
        applies_to_systems: formData.applies_to_systems,
        is_enabled: formData.is_enabled,
      };
      if (editingRule) {
        await api.put(`/risk-rules/custom/${editingRule.id}`, payload);
        toast.success(`Rule "${formData.name}" updated`);
      } else {
        await api.post('/risk-rules/custom', payload);
        toast.success(`Rule "${formData.name}" created`);
      }
      setShowFormModal(false);
      queryClient.invalidateQueries({ queryKey: ['risk-rules'] });
    } catch {
      toast.error(editingRule ? 'Failed to update rule' : 'Failed to create rule');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDelete = async (ruleId: string) => {
    try {
      await api.put(`/risk-rules/builtin/${ruleId}/toggle`, null, { params: { enabled: false, reason: 'Deactivated via UI' } });
      toast.success('Rule deactivated');
      setDeleteConfirmId(null);
      queryClient.invalidateQueries({ queryKey: ['risk-rules'] });
    } catch {
      try {
        await api.delete(`/risk-rules/custom/${ruleId}`);
        toast.success('Rule deleted');
        setDeleteConfirmId(null);
        queryClient.invalidateQueries({ queryKey: ['risk-rules'] });
      } catch {
        toast.error('Failed to remove rule');
      }
    }
  };

  const categories = [...new Set(rules.map((r) => r.category))];
  const systems = [...new Set(rules.map((r) => r.system))];

  const filteredRules = rules.filter((rule) => {
    const matchesSearch =
      rule.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      rule.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || rule.category === categoryFilter;
    const matchesStatus = statusFilter === 'all' || rule.status === statusFilter;
    const matchesSystem = systemFilter === 'all' || rule.system === systemFilter;
    return matchesSearch && matchesCategory && matchesStatus && matchesSystem;
  });

  const activeRules = rules.filter((r) => r.status === 'active').length;
  const totalViolations = rules.reduce((acc, r) => acc + r.violations, 0);
  const criticalRules = rules.filter((r) => r.riskLevel === 'critical').length;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Segregation of Duties Rules</h1>
          <p className="page-subtitle">
            Manage SoD rules and conflict detection policies
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="btn-primary"
        >
          <PlusIcon className="h-4 w-4 mr-1.5" />
          Create Rule
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-blue">
              <ShieldExclamationIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Total Rules</div>
              <div className="stat-value">{rules.length}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-green">
              <CheckCircleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Active Rules</div>
              <div className="stat-value text-green-500">{activeRules}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-red">
              <ExclamationTriangleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Total Violations</div>
              <div className="stat-value text-red-500">{totalViolations}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-orange">
              <ShieldExclamationIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Critical Rules</div>
              <div className="stat-value text-orange-500">{criticalRules}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="card-body">
          <div className="flex flex-col lg:flex-row gap-3">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search rules..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <FunnelIcon className="h-4 w-4 text-gray-400" />
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="text-xs border border-gray-300 rounded-md px-2 py-1.5 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="all">All Categories</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-xs border border-gray-300 rounded-md px-2 py-1.5 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="draft">Draft</option>
              </select>
              <select
                value={systemFilter}
                onChange={(e) => setSystemFilter(e.target.value)}
                className="text-xs border border-gray-300 rounded-md px-2 py-1.5 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="all">All Systems</option>
                {systems.map((sys) => (
                  <option key={sys} value={sys}>
                    {sys}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Rules Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rule
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Functions
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                System
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Risk
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Violations
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredRules.map((rule) => {
              const riskInfo = riskConfig[rule.riskLevel];
              const statusInfo = statusConfig[rule.status];
              return (
                <tr key={rule.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{rule.name}</div>
                      <div className="text-xs text-gray-500">{rule.category}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-xs">
                      <div className="text-gray-900">{rule.function1}</div>
                      <div className="text-gray-400 my-1">conflicts with</div>
                      <div className="text-gray-900">{rule.function2}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex px-2 py-0.5 rounded bg-gray-100 text-xs text-gray-700">
                      {rule.system}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${riskInfo.color}`}
                    >
                      {riskInfo.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${statusInfo.color}`}
                    >
                      {statusInfo.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {rule.violations > 0 ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
                        {rule.violations}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-500">0</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button
                      onClick={() => openEditModal(rule)}
                      className="text-primary-600 hover:text-primary-900 mr-3"
                    >
                      <PencilIcon className="h-4 w-4 inline" />
                    </button>
                    <button
                      onClick={() => setDeleteConfirmId(rule.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      <TrashIcon className="h-4 w-4 inline" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredRules.length === 0 && (
          <div className="text-center py-12">
            <ShieldExclamationIcon className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-gray-500">No rules found matching your criteria</p>
          </div>
        )}
      </div>

      {/* Create / Edit Rule Modal */}
      {showFormModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {editingRule ? 'Edit Rule' : 'Create New Rule'}
              </h2>
              <button onClick={() => setShowFormModal(false)} className="text-gray-400 hover:text-gray-600">
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Rule Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                  placeholder="e.g., Purchase Order / Vendor Master"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={2}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Function 1</label>
                  <input
                    type="text"
                    value={formData.rule_definition.function1}
                    onChange={(e) => setFormData({ ...formData, rule_definition: { ...formData.rule_definition, function1: e.target.value } })}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g., AP01"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Function 2</label>
                  <input
                    type="text"
                    value={formData.rule_definition.function2}
                    onChange={(e) => setFormData({ ...formData, rule_definition: { ...formData.rule_definition, function2: e.target.value } })}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g., AP02"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Severity</label>
                  <select
                    value={formData.severity}
                    onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">System</label>
                  <input
                    type="text"
                    value={formData.applies_to_systems[0] === '*' ? '' : formData.applies_to_systems[0]}
                    onChange={(e) => setFormData({ ...formData, applies_to_systems: [e.target.value || '*'] })}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g., SAP ECC (blank = all)"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.is_enabled}
                  onChange={(e) => setFormData({ ...formData, is_enabled: e.target.checked })}
                  className="h-4 w-4 rounded border-gray-300 text-primary-600"
                />
                <label className="text-sm text-gray-700 dark:text-gray-300">Active</label>
              </div>
            </div>
            <div className="flex justify-end gap-2 p-5 border-t border-gray-200 dark:border-gray-700">
              <button onClick={() => setShowFormModal(false)} className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200">Cancel</button>
              <button
                onClick={handleFormSubmit}
                disabled={formSubmitting}
                className="btn-primary"
              >
                {formSubmitting ? 'Saving...' : editingRule ? 'Update Rule' : 'Create Rule'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-sm w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Deactivate Rule?</h3>
            <p className="text-sm text-gray-500 mb-4">This will deactivate the rule. It will no longer trigger during risk analysis.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteConfirmId(null)} className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200">Cancel</button>
              <button onClick={() => handleDelete(deleteConfirmId)} className="px-4 py-2 text-sm text-white bg-red-600 rounded-md hover:bg-red-700">Deactivate</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
