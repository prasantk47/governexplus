import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  UserIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  ClipboardDocumentCheckIcon,
} from '@heroicons/react/24/outline';

interface CertificationItem {
  id: string;
  user: string;
  userId: string;
  department: string;
  role: string;
  system: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  lastUsed: string;
  grantedDate: string;
  decision: 'pending' | 'certified' | 'revoked';
  anomalies: string[];
}

const mockItems: CertificationItem[] = [
  {
    id: 'CERT-001',
    user: 'John Smith',
    userId: 'jsmith',
    department: 'Finance',
    role: 'SAP_FI_AP_CLERK',
    system: 'SAP ECC',
    riskLevel: 'low',
    lastUsed: '2024-01-18',
    grantedDate: '2023-06-15',
    decision: 'pending',
    anomalies: [],
  },
  {
    id: 'CERT-002',
    user: 'John Smith',
    userId: 'jsmith',
    department: 'Finance',
    role: 'SAP_FI_GL_ACCOUNTANT',
    system: 'SAP ECC',
    riskLevel: 'high',
    lastUsed: '2024-01-19',
    grantedDate: '2023-08-20',
    decision: 'pending',
    anomalies: ['SoD conflict with SAP_FI_AP_CLERK'],
  },
  {
    id: 'CERT-003',
    user: 'Emily Davis',
    userId: 'edavis',
    department: 'Finance',
    role: 'SAP_MM_BUYER',
    system: 'SAP ECC',
    riskLevel: 'medium',
    lastUsed: '2024-01-15',
    grantedDate: '2023-04-10',
    decision: 'pending',
    anomalies: [],
  },
  {
    id: 'CERT-004',
    user: 'Emily Davis',
    userId: 'edavis',
    department: 'Finance',
    role: 'AWS_DEVELOPER',
    system: 'AWS',
    riskLevel: 'medium',
    lastUsed: '2023-10-05',
    grantedDate: '2023-03-01',
    decision: 'pending',
    anomalies: ['Not used in 90+ days'],
  },
  {
    id: 'CERT-005',
    user: 'Michael Brown',
    userId: 'mbrown',
    department: 'Finance',
    role: 'WORKDAY_VIEWER',
    system: 'Workday',
    riskLevel: 'low',
    lastUsed: '2024-01-10',
    grantedDate: '2023-01-15',
    decision: 'certified',
    anomalies: [],
  },
  {
    id: 'CERT-006',
    user: 'Sarah Wilson',
    userId: 'swilson',
    department: 'Finance',
    role: 'SAP_FI_AP_MANAGER',
    system: 'SAP ECC',
    riskLevel: 'high',
    lastUsed: '2024-01-17',
    grantedDate: '2022-12-01',
    decision: 'pending',
    anomalies: [],
  },
  {
    id: 'CERT-007',
    user: 'David Lee',
    userId: 'dlee',
    department: 'Finance',
    role: 'SALESFORCE_ADMIN',
    system: 'Salesforce',
    riskLevel: 'high',
    lastUsed: '2023-08-15',
    grantedDate: '2023-02-20',
    decision: 'pending',
    anomalies: ['Not used in 90+ days', 'Role no longer needed'],
  },
];

const riskConfig = {
  low: { color: 'bg-green-100 text-green-800' },
  medium: { color: 'bg-yellow-100 text-yellow-800' },
  high: { color: 'bg-orange-100 text-orange-800' },
  critical: { color: 'bg-red-100 text-red-800' },
};

export function CertificationReview() {
  const { campaignId } = useParams();
  const [items, setItems] = useState(mockItems);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterDecision, setFilterDecision] = useState<string>('all');
  const [filterRisk, setFilterRisk] = useState<string>('all');
  const [bulkAction, setBulkAction] = useState<string>('');
  const [selectedItems, setSelectedItems] = useState<string[]>([]);

  const filteredItems = items.filter((item) => {
    const matchesSearch =
      item.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.role.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDecision = filterDecision === 'all' || item.decision === filterDecision;
    const matchesRisk = filterRisk === 'all' || item.riskLevel === filterRisk;
    return matchesSearch && matchesDecision && matchesRisk;
  });

  const pendingCount = items.filter((i) => i.decision === 'pending').length;
  const certifiedCount = items.filter((i) => i.decision === 'certified').length;
  const revokedCount = items.filter((i) => i.decision === 'revoked').length;
  const progress = Math.round(((certifiedCount + revokedCount) / items.length) * 100);

  const handleDecision = (itemId: string, decision: 'certified' | 'revoked') => {
    setItems(items.map((item) => (item.id === itemId ? { ...item, decision } : item)));
  };

  const handleBulkAction = () => {
    if (!bulkAction || selectedItems.length === 0) return;
    setItems(
      items.map((item) =>
        selectedItems.includes(item.id)
          ? { ...item, decision: bulkAction as 'certified' | 'revoked' }
          : item
      )
    );
    setSelectedItems([]);
    setBulkAction('');
  };

  const toggleSelection = (itemId: string) => {
    setSelectedItems(
      selectedItems.includes(itemId)
        ? selectedItems.filter((id) => id !== itemId)
        : [...selectedItems, itemId]
    );
  };

  const selectAllPending = () => {
    const pendingIds = items.filter((i) => i.decision === 'pending').map((i) => i.id);
    setSelectedItems(pendingIds);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Link
            to="/certification"
            className="mr-4 p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Q1 2024 User Access Certification - Finance
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              Campaign ID: {campaignId || 'CERT-2024-Q1-FIN'}
            </p>
          </div>
        </div>
        <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm font-medium">
          Submit Certification
        </button>
      </div>

      {/* Progress */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Certification Progress</h2>
          <span className="text-2xl font-bold text-primary-600">{progress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
          <div
            className="bg-primary-600 h-3 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="p-3 bg-yellow-50 rounded-lg">
            <div className="text-2xl font-bold text-yellow-600">{pendingCount}</div>
            <div className="text-sm text-gray-500">Pending Review</div>
          </div>
          <div className="p-3 bg-green-50 rounded-lg">
            <div className="text-2xl font-bold text-green-600">{certifiedCount}</div>
            <div className="text-sm text-gray-500">Certified</div>
          </div>
          <div className="p-3 bg-red-50 rounded-lg">
            <div className="text-2xl font-bold text-red-600">{revokedCount}</div>
            <div className="text-sm text-gray-500">Revoked</div>
          </div>
        </div>
      </div>

      {/* Filters and Bulk Actions */}
      <div className="bg-white shadow rounded-lg p-4">
        <div className="flex flex-col lg:flex-row gap-4 items-center justify-between">
          <div className="flex flex-1 gap-4 items-center">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by user or role..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <FunnelIcon className="h-5 w-5 text-gray-400" />
              <select
                value={filterDecision}
                onChange={(e) => setFilterDecision(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="all">All Decisions</option>
                <option value="pending">Pending</option>
                <option value="certified">Certified</option>
                <option value="revoked">Revoked</option>
              </select>
              <select
                value={filterRisk}
                onChange={(e) => setFilterRisk(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="all">All Risk</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={selectAllPending}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              Select All Pending
            </button>
            <select
              value={bulkAction}
              onChange={(e) => setBulkAction(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">Bulk Action...</option>
              <option value="certified">Certify Selected</option>
              <option value="revoked">Revoke Selected</option>
            </select>
            <button
              onClick={handleBulkAction}
              disabled={!bulkAction || selectedItems.length === 0}
              className="px-4 py-2 bg-gray-800 text-white rounded-md hover:bg-gray-900 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm font-medium"
            >
              Apply ({selectedItems.length})
            </button>
          </div>
        </div>
      </div>

      {/* Certification Items */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">
                <input
                  type="checkbox"
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedItems(filteredItems.map((i) => i.id));
                    } else {
                      setSelectedItems([]);
                    }
                  }}
                  checked={selectedItems.length === filteredItems.length && filteredItems.length > 0}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Role
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Risk
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Used
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Anomalies
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Decision
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredItems.map((item) => {
              const riskInfo = riskConfig[item.riskLevel];
              return (
                <tr key={item.id} className={`hover:bg-gray-50 ${selectedItems.includes(item.id) ? 'bg-blue-50' : ''}`}>
                  <td className="px-4 py-4">
                    <input
                      type="checkbox"
                      checked={selectedItems.includes(item.id)}
                      onChange={() => toggleSelection(item.id)}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <div className="h-8 w-8 bg-gray-200 rounded-full flex items-center justify-center mr-3">
                        <UserIcon className="h-4 w-4 text-gray-500" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">{item.user}</div>
                        <div className="text-xs text-gray-500">{item.department}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{item.role}</div>
                    <div className="text-xs text-gray-500">{item.system}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${riskInfo.color}`}>
                      {item.riskLevel.charAt(0).toUpperCase() + item.riskLevel.slice(1)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {item.lastUsed}
                  </td>
                  <td className="px-6 py-4">
                    {item.anomalies.length > 0 ? (
                      <div className="space-y-1">
                        {item.anomalies.map((anomaly, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 mr-1"
                          >
                            <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
                            {anomaly}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-sm text-gray-400">None</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {item.decision === 'pending' ? (
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => handleDecision(item.id, 'certified')}
                          className="p-1.5 text-green-600 hover:bg-green-100 rounded"
                          title="Certify"
                        >
                          <CheckCircleIcon className="h-6 w-6" />
                        </button>
                        <button
                          onClick={() => handleDecision(item.id, 'revoked')}
                          className="p-1.5 text-red-600 hover:bg-red-100 rounded"
                          title="Revoke"
                        >
                          <XCircleIcon className="h-6 w-6" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center">
                        {item.decision === 'certified' ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            <CheckCircleIcon className="h-4 w-4 mr-1" />
                            Certified
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            <XCircleIcon className="h-4 w-4 mr-1" />
                            Revoked
                          </span>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredItems.length === 0 && (
          <div className="text-center py-12">
            <ClipboardDocumentCheckIcon className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-gray-500">No items found matching your criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}
