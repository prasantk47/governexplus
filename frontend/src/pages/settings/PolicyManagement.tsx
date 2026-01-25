import { useState } from 'react';
import {
  CodeBracketIcon,
  DocumentTextIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  PlayIcon,
  PencilIcon,
  TrashIcon,
  ArrowPathIcon,
  DocumentDuplicateIcon,
  EyeIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline';

interface Policy {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  status: 'active' | 'draft' | 'testing' | 'archived';
  lastModified: string;
  modifiedBy: string;
  appliedTo: number;
  violations: number;
  code: string;
}

const mockPolicies: Policy[] = [
  {
    id: 'POL-001',
    name: 'High-Risk Access Approval',
    description: 'Require dual approval for high-risk access requests',
    category: 'Access Control',
    version: '2.1.0',
    status: 'active',
    lastModified: '2024-01-15',
    modifiedBy: 'Security Admin',
    appliedTo: 1250,
    violations: 0,
    code: `policy "high_risk_approval" {
  description = "Require dual approval for high-risk access"

  when {
    request.risk_level in ["high", "critical"]
    request.type == "access_request"
  }

  then {
    require_approvals(2)
    require_approver_role("security_admin")
    set_sla("24h")
    notify("security_team")
  }
}`,
  },
  {
    id: 'POL-002',
    name: 'SoD Violation Prevention',
    description: 'Block requests that would create SoD conflicts',
    category: 'Risk Management',
    version: '1.5.0',
    status: 'active',
    lastModified: '2024-01-10',
    modifiedBy: 'Risk Manager',
    appliedTo: 3420,
    violations: 12,
    code: `policy "sod_prevention" {
  description = "Prevent SoD violations at request time"

  when {
    simulation.has_sod_conflict == true
    simulation.conflict_severity in ["high", "critical"]
  }

  then {
    block_request()
    set_message("Request blocked: Critical SoD conflict detected")
    create_violation_record()
    notify("risk_team", "compliance_team")
  }
}`,
  },
  {
    id: 'POL-003',
    name: 'Firefighter Session Limits',
    description: 'Enforce time limits on emergency access sessions',
    category: 'Privileged Access',
    version: '1.2.0',
    status: 'active',
    lastModified: '2024-01-12',
    modifiedBy: 'Security Admin',
    appliedTo: 89,
    violations: 3,
    code: `policy "firefighter_limits" {
  description = "Enforce emergency access time limits"

  when {
    session.type == "firefighter"
    session.duration > "4h"
  }

  then {
    terminate_session()
    create_audit_log("forced_termination")
    notify("security_admin", "manager")
    require_review_within("24h")
  }
}`,
  },
  {
    id: 'POL-004',
    name: 'Dormant Access Cleanup',
    description: 'Auto-revoke access not used in 90 days',
    category: 'Entitlement Governance',
    version: '1.0.0',
    status: 'testing',
    lastModified: '2024-01-18',
    modifiedBy: 'IT Admin',
    appliedTo: 0,
    violations: 0,
    code: `policy "dormant_cleanup" {
  description = "Automatically revoke unused access"

  schedule = "daily at 02:00"

  when {
    entitlement.last_used > "90d"
    entitlement.is_sensitive == true
  }

  then {
    flag_for_review()
    notify("manager", "user")
    if (no_response_within("7d")) {
      revoke_access()
      create_audit_log("auto_revoked")
    }
  }
}`,
  },
  {
    id: 'POL-005',
    name: 'Geo-Restricted Access',
    description: 'Block access from unauthorized countries',
    category: 'Contextual Security',
    version: '1.1.0',
    status: 'draft',
    lastModified: '2024-01-17',
    modifiedBy: 'Security Admin',
    appliedTo: 0,
    violations: 0,
    code: `policy "geo_restriction" {
  description = "Block access from high-risk locations"

  blocked_countries = ["RU", "CN", "KP", "IR"]

  when {
    request.geo_location.country in blocked_countries
    user.travel_exception != true
  }

  then {
    block_request()
    require_mfa()
    alert_security("geo_violation")
    log_event("blocked_geo_access")
  }
}`,
  },
];

const categories = [
  'Access Control',
  'Risk Management',
  'Privileged Access',
  'Entitlement Governance',
  'Contextual Security',
  'Compliance',
];

export function PolicyManagement() {
  const [policies, setPolicies] = useState<Policy[]>(mockPolicies);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'code'>('list');
  const [isTestMode, setIsTestMode] = useState(false);

  const filteredPolicies = policies.filter(
    (p) =>
      (p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.description.toLowerCase().includes(searchTerm.toLowerCase())) &&
      (categoryFilter === '' || p.category === categoryFilter) &&
      (statusFilter === '' || p.status === statusFilter)
  );

  const stats = {
    total: policies.length,
    active: policies.filter((p) => p.status === 'active').length,
    testing: policies.filter((p) => p.status === 'testing').length,
    draft: policies.filter((p) => p.status === 'draft').length,
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'testing': return 'bg-blue-100 text-blue-800';
      case 'draft': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Policy-as-Code</h1>
          <p className="text-sm text-gray-500">
            Manage governance policies with version control and testing
          </p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm flex items-center gap-2">
            <ArrowPathIcon className="h-4 w-4" />
            Sync from Git
          </button>
          <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm flex items-center gap-2">
            <CodeBracketIcon className="h-4 w-4" />
            New Policy
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
          <div className="text-sm text-gray-500">Total Policies</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-green-600">{stats.active}</div>
          <div className="text-sm text-gray-500">Active</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-blue-600">{stats.testing}</div>
          <div className="text-sm text-gray-500">Testing</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-2xl font-bold text-yellow-600">{stats.draft}</div>
          <div className="text-sm text-gray-500">Draft</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="Search policies..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="testing">Testing</option>
            <option value="draft">Draft</option>
            <option value="archived">Archived</option>
          </select>
          <div className="flex border border-gray-300 rounded-md overflow-hidden">
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-2 text-sm ${viewMode === 'list' ? 'bg-primary-600 text-white' : 'bg-white text-gray-700'}`}
            >
              List
            </button>
            <button
              onClick={() => setViewMode('code')}
              className={`px-3 py-2 text-sm ${viewMode === 'code' ? 'bg-primary-600 text-white' : 'bg-white text-gray-700'}`}
            >
              Code
            </button>
          </div>
        </div>
      </div>

      {/* Policies List */}
      {viewMode === 'list' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Policy</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Version</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Applied To</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Violations</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredPolicies.map((policy) => (
                <tr key={policy.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <CodeBracketIcon className="h-5 w-5 text-gray-400" />
                      <div>
                        <div className="text-sm font-medium text-gray-900">{policy.name}</div>
                        <div className="text-xs text-gray-500">{policy.description}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">{policy.category}</td>
                  <td className="px-6 py-4">
                    <span className="text-sm font-mono text-gray-600">v{policy.version}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(policy.status)}`}>
                      {policy.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">{policy.appliedTo.toLocaleString()}</td>
                  <td className="px-6 py-4">
                    <span className={`text-sm font-medium ${policy.violations > 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {policy.violations}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setSelectedPolicy(policy)}
                        className="p-1.5 text-gray-400 hover:text-gray-600"
                        title="View Code"
                      >
                        <EyeIcon className="h-4 w-4" />
                      </button>
                      <button className="p-1.5 text-gray-400 hover:text-blue-600" title="Test">
                        <BeakerIcon className="h-4 w-4" />
                      </button>
                      <button className="p-1.5 text-gray-400 hover:text-gray-600" title="Edit">
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button className="p-1.5 text-gray-400 hover:text-gray-600" title="Duplicate">
                        <DocumentDuplicateIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Code View */}
      {viewMode === 'code' && (
        <div className="space-y-4">
          {filteredPolicies.map((policy) => (
            <div key={policy.id} className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CodeBracketIcon className="h-5 w-5 text-gray-400" />
                  <div>
                    <span className="text-sm font-medium text-gray-900">{policy.name}</span>
                    <span className="ml-2 text-xs font-mono text-gray-500">v{policy.version}</span>
                  </div>
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(policy.status)}`}>
                    {policy.status}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button className="text-xs text-primary-600 hover:text-primary-700">Edit</button>
                  <button className="text-xs text-gray-500 hover:text-gray-700">History</button>
                </div>
              </div>
              <pre className="p-4 bg-gray-900 text-gray-100 text-sm overflow-x-auto">
                <code>{policy.code}</code>
              </pre>
            </div>
          ))}
        </div>
      )}

      {/* Policy Detail Modal */}
      {selectedPolicy && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <h2 className="text-lg font-semibold text-gray-900">{selectedPolicy.name}</h2>
                  <span className="text-sm font-mono text-gray-500">v{selectedPolicy.version}</span>
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(selectedPolicy.status)}`}>
                    {selectedPolicy.status}
                  </span>
                </div>
                <button
                  onClick={() => setSelectedPolicy(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  &times;
                </button>
              </div>
              <p className="text-sm text-gray-500 mt-1">{selectedPolicy.description}</p>
            </div>

            <div className="p-6 space-y-6">
              {/* Metadata */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <span className="text-xs text-gray-500">Category</span>
                  <p className="text-sm font-medium text-gray-900">{selectedPolicy.category}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Last Modified</span>
                  <p className="text-sm font-medium text-gray-900">{selectedPolicy.lastModified}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Modified By</span>
                  <p className="text-sm font-medium text-gray-900">{selectedPolicy.modifiedBy}</p>
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-green-50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-green-600">{selectedPolicy.appliedTo.toLocaleString()}</p>
                  <p className="text-sm text-green-700">Applied To</p>
                </div>
                <div className={`${selectedPolicy.violations > 0 ? 'bg-red-50' : 'bg-gray-50'} rounded-lg p-4 text-center`}>
                  <p className={`text-2xl font-bold ${selectedPolicy.violations > 0 ? 'text-red-600' : 'text-gray-600'}`}>
                    {selectedPolicy.violations}
                  </p>
                  <p className={`text-sm ${selectedPolicy.violations > 0 ? 'text-red-700' : 'text-gray-600'}`}>Violations</p>
                </div>
              </div>

              {/* Code */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Policy Code</h4>
                <pre className="p-4 bg-gray-900 text-gray-100 text-sm rounded-lg overflow-x-auto">
                  <code>{selectedPolicy.code}</code>
                </pre>
              </div>

              {/* Test Mode */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-medium text-blue-800">Test Mode</h4>
                    <p className="text-xs text-blue-600">Run policy against sample data without enforcement</p>
                  </div>
                  <button className="px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 flex items-center gap-1">
                    <BeakerIcon className="h-4 w-4" />
                    Run Test
                  </button>
                </div>
              </div>
            </div>

            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between">
              <div className="flex gap-2">
                <button className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-md text-sm">
                  Deactivate
                </button>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedPolicy(null)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm"
                >
                  Close
                </button>
                <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm">
                  Edit Policy
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
