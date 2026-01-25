import { useState } from 'react';
import {
  ChartBarIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  UserGroupIcon,
  ShieldExclamationIcon,
  ArrowTrendingDownIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  CheckCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

interface EntitlementIssue {
  id: string;
  type: 'unused' | 'excessive' | 'dormant' | 'orphaned';
  user: string;
  userId: string;
  department: string;
  entitlement: string;
  system: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  lastUsed: string | null;
  daysSinceUse: number | null;
  recommendation: string;
  potentialSavings?: string;
}

const mockIssues: EntitlementIssue[] = [
  {
    id: 'ENT-001',
    type: 'unused',
    user: 'John Smith',
    userId: 'jsmith',
    department: 'Finance',
    entitlement: 'AP Payment Run',
    system: 'SAP S/4HANA',
    riskLevel: 'high',
    lastUsed: null,
    daysSinceUse: 180,
    recommendation: 'Remove access - never used since assignment',
    potentialSavings: '$1,200/year',
  },
  {
    id: 'ENT-002',
    type: 'excessive',
    user: 'Mary Jones',
    userId: 'mjones',
    department: 'IT',
    entitlement: 'SAP_ALL',
    system: 'SAP S/4HANA',
    riskLevel: 'critical',
    lastUsed: '2024-01-15',
    daysSinceUse: 3,
    recommendation: 'Replace with role-specific access',
  },
  {
    id: 'ENT-003',
    type: 'dormant',
    user: 'Robert Wilson',
    userId: 'rwilson',
    department: 'Sales',
    entitlement: 'CRM Admin',
    system: 'Salesforce',
    riskLevel: 'medium',
    lastUsed: '2023-09-10',
    daysSinceUse: 130,
    recommendation: 'Review with manager - extended non-use',
    potentialSavings: '$500/year',
  },
  {
    id: 'ENT-004',
    type: 'orphaned',
    user: 'Sarah Brown (Terminated)',
    userId: 'sbrown',
    department: 'HR',
    entitlement: 'HR Master Data',
    system: 'Workday',
    riskLevel: 'critical',
    lastUsed: '2023-11-30',
    daysSinceUse: 49,
    recommendation: 'Immediate removal - terminated employee',
  },
  {
    id: 'ENT-005',
    type: 'unused',
    user: 'David Lee',
    userId: 'dlee',
    department: 'Operations',
    entitlement: 'Warehouse Admin',
    system: 'SAP EWM',
    riskLevel: 'medium',
    lastUsed: null,
    daysSinceUse: 90,
    recommendation: 'Remove access - assigned but never used',
    potentialSavings: '$800/year',
  },
  {
    id: 'ENT-006',
    type: 'excessive',
    user: 'Tom Chen',
    userId: 'tchen',
    department: 'IT',
    entitlement: 'Domain Admin',
    system: 'Active Directory',
    riskLevel: 'critical',
    lastUsed: '2024-01-17',
    daysSinceUse: 1,
    recommendation: 'Reduce to specific admin functions needed',
  },
  {
    id: 'ENT-007',
    type: 'dormant',
    user: 'Ana Garcia',
    userId: 'agarcia',
    department: 'Finance',
    entitlement: 'Journal Entry Posting',
    system: 'SAP S/4HANA',
    riskLevel: 'high',
    lastUsed: '2023-10-15',
    daysSinceUse: 95,
    recommendation: 'Review - no GL postings in 3+ months',
    potentialSavings: '$600/year',
  },
  {
    id: 'ENT-008',
    type: 'unused',
    user: 'Multiple Users (15)',
    userId: 'group',
    department: 'Various',
    entitlement: 'Legacy ERP Access',
    system: 'Oracle EBS',
    riskLevel: 'low',
    lastUsed: null,
    daysSinceUse: 365,
    recommendation: 'System decommissioned - remove all access',
    potentialSavings: '$15,000/year',
  },
];

const typeConfig = {
  unused: { label: 'Unused Access', color: 'bg-blue-100 text-blue-800', icon: ClockIcon },
  excessive: { label: 'Excessive Privileges', color: 'bg-red-100 text-red-800', icon: ShieldExclamationIcon },
  dormant: { label: 'Dormant Access', color: 'bg-yellow-100 text-yellow-800', icon: ArrowTrendingDownIcon },
  orphaned: { label: 'Orphaned Account', color: 'bg-purple-100 text-purple-800', icon: UserGroupIcon },
};

export function EntitlementIntelligence() {
  const [issues, setIssues] = useState<EntitlementIssue[]>(mockIssues);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [selectedIssues, setSelectedIssues] = useState<string[]>([]);

  const filteredIssues = issues.filter(
    (issue) =>
      (issue.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
        issue.entitlement.toLowerCase().includes(searchTerm.toLowerCase()) ||
        issue.system.toLowerCase().includes(searchTerm.toLowerCase())) &&
      (typeFilter === '' || issue.type === typeFilter) &&
      (riskFilter === '' || issue.riskLevel === riskFilter)
  );

  const stats = {
    total: issues.length,
    unused: issues.filter((i) => i.type === 'unused').length,
    excessive: issues.filter((i) => i.type === 'excessive').length,
    dormant: issues.filter((i) => i.type === 'dormant').length,
    orphaned: issues.filter((i) => i.type === 'orphaned').length,
    critical: issues.filter((i) => i.riskLevel === 'critical').length,
    potentialSavings: '$18,100',
  };

  const toggleSelect = (id: string) => {
    setSelectedIssues((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (selectedIssues.length === filteredIssues.length) {
      setSelectedIssues([]);
    } else {
      setSelectedIssues(filteredIssues.map((i) => i.id));
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-green-100 text-green-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Entitlement Intelligence</h1>
          <p className="text-sm text-gray-500">
            AI-powered detection of unused, excessive, and orphaned access
          </p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm">
            Export Report
          </button>
          <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm">
            Run Analysis
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-2">
            <ChartBarIcon className="h-5 w-5 text-gray-400" />
            <span className="text-xs text-gray-500">Total Issues</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-2">
            <ClockIcon className="h-5 w-5 text-blue-500" />
            <span className="text-xs text-gray-500">Unused</span>
          </div>
          <p className="text-2xl font-bold text-blue-600">{stats.unused}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-2">
            <ShieldExclamationIcon className="h-5 w-5 text-red-500" />
            <span className="text-xs text-gray-500">Excessive</span>
          </div>
          <p className="text-2xl font-bold text-red-600">{stats.excessive}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-2">
            <ArrowTrendingDownIcon className="h-5 w-5 text-yellow-500" />
            <span className="text-xs text-gray-500">Dormant</span>
          </div>
          <p className="text-2xl font-bold text-yellow-600">{stats.dormant}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-2">
            <UserGroupIcon className="h-5 w-5 text-purple-500" />
            <span className="text-xs text-gray-500">Orphaned</span>
          </div>
          <p className="text-2xl font-bold text-purple-600">{stats.orphaned}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
            <span className="text-xs text-gray-500">Critical</span>
          </div>
          <p className="text-2xl font-bold text-red-600">{stats.critical}</p>
        </div>
        <div className="bg-green-50 rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs text-green-600 font-medium">Potential Savings</span>
          </div>
          <p className="text-2xl font-bold text-green-600">{stats.potentialSavings}</p>
        </div>
      </div>

      {/* Filters and Bulk Actions */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search users, entitlements, or systems..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All Types</option>
            <option value="unused">Unused Access</option>
            <option value="excessive">Excessive Privileges</option>
            <option value="dormant">Dormant Access</option>
            <option value="orphaned">Orphaned Account</option>
          </select>
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All Risk Levels</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          {selectedIssues.length > 0 && (
            <div className="flex items-center gap-2 ml-4 pl-4 border-l border-gray-300">
              <span className="text-sm text-gray-500">{selectedIssues.length} selected</span>
              <button className="px-3 py-1.5 bg-red-100 text-red-700 rounded-md text-sm hover:bg-red-200">
                Revoke Selected
              </button>
              <button className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-md text-sm hover:bg-blue-200">
                Create Review
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Issues Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedIssues.length === filteredIssues.length && filteredIssues.length > 0}
                  onChange={selectAll}
                  className="h-4 w-4 rounded border-gray-300 text-primary-600"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Entitlement</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">System</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Used</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Recommendation</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredIssues.map((issue) => {
              const TypeIcon = typeConfig[issue.type].icon;
              return (
                <tr key={issue.id} className={`hover:bg-gray-50 ${selectedIssues.includes(issue.id) ? 'bg-primary-50' : ''}`}>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIssues.includes(issue.id)}
                      onChange={() => toggleSelect(issue.id)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${typeConfig[issue.type].color}`}>
                      <TypeIcon className="h-3 w-3" />
                      {typeConfig[issue.type].label}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm font-medium text-gray-900">{issue.user}</div>
                    <div className="text-xs text-gray-500">{issue.department}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">{issue.entitlement}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{issue.system}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getRiskColor(issue.riskLevel)}`}>
                      {issue.riskLevel}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-900">
                      {issue.lastUsed || 'Never'}
                    </div>
                    {issue.daysSinceUse && (
                      <div className="text-xs text-gray-500">{issue.daysSinceUse} days ago</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-xs text-gray-600 max-w-xs">{issue.recommendation}</div>
                    {issue.potentialSavings && (
                      <div className="text-xs text-green-600 font-medium mt-1">
                        Savings: {issue.potentialSavings}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        className="p-1.5 text-green-600 hover:bg-green-50 rounded"
                        title="Accept & Revoke"
                      >
                        <CheckCircleIcon className="h-4 w-4" />
                      </button>
                      <button
                        className="p-1.5 text-gray-400 hover:bg-gray-100 rounded"
                        title="Dismiss"
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* AI Insights */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <span className="text-2xl">AI</span> Insights & Recommendations
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-900 mb-2">High Impact Finding</h4>
            <p className="text-xs text-gray-600">
              15 users have access to legacy Oracle EBS system that was decommissioned.
              Removing this access could save $15,000/year in license costs.
            </p>
          </div>
          <div className="bg-white rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Risk Pattern Detected</h4>
            <p className="text-xs text-gray-600">
              2 IT administrators have SAP_ALL and Domain Admin access simultaneously.
              This creates a critical cross-system privilege escalation risk.
            </p>
          </div>
          <div className="bg-white rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Optimization Opportunity</h4>
            <p className="text-xs text-gray-600">
              23% of Finance department entitlements haven't been used in 90+ days.
              Consider implementing quarterly access reviews for this department.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
