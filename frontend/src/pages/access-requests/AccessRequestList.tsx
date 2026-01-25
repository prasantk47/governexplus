import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  PlusIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  EyeIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

interface AccessRequest {
  id: string;
  role: string;
  system: string;
  status: 'pending' | 'approved' | 'rejected' | 'in_review';
  requestDate: string;
  approver: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  businessJustification: string;
}

const mockRequests: AccessRequest[] = [
  {
    id: 'REQ-2024-001',
    role: 'SAP_MM_BUYER',
    system: 'SAP ECC',
    status: 'pending',
    requestDate: '2024-01-20',
    approver: 'John Manager',
    riskLevel: 'medium',
    businessJustification: 'Need to process purchase orders for Q1 projects',
  },
  {
    id: 'REQ-2024-002',
    role: 'SAP_FI_AP_CLERK',
    system: 'SAP ECC',
    status: 'approved',
    requestDate: '2024-01-18',
    approver: 'Sarah Director',
    riskLevel: 'low',
    businessJustification: 'Accounts payable processing role',
  },
  {
    id: 'REQ-2024-003',
    role: 'ADMIN_FULL_ACCESS',
    system: 'Azure AD',
    status: 'in_review',
    requestDate: '2024-01-19',
    approver: 'IT Security Team',
    riskLevel: 'critical',
    businessJustification: 'Emergency admin access for system maintenance',
  },
  {
    id: 'REQ-2024-004',
    role: 'HR_BENEFITS_ADMIN',
    system: 'Workday',
    status: 'rejected',
    requestDate: '2024-01-15',
    approver: 'HR Manager',
    riskLevel: 'high',
    businessJustification: 'Requesting for benefits administration tasks',
  },
  {
    id: 'REQ-2024-005',
    role: 'READ_ONLY_REPORTS',
    system: 'Salesforce',
    status: 'approved',
    requestDate: '2024-01-17',
    approver: 'Sales Director',
    riskLevel: 'low',
    businessJustification: 'View sales reports for quarterly planning',
  },
];

const statusConfig = {
  pending: { label: 'Pending', color: 'bg-yellow-100 text-yellow-800', icon: ClockIcon },
  approved: { label: 'Approved', color: 'bg-green-100 text-green-800', icon: CheckCircleIcon },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-800', icon: XCircleIcon },
  in_review: { label: 'In Review', color: 'bg-blue-100 text-blue-800', icon: EyeIcon },
};

const riskConfig = {
  low: { label: 'Low', color: 'bg-green-100 text-green-800' },
  medium: { label: 'Medium', color: 'bg-yellow-100 text-yellow-800' },
  high: { label: 'High', color: 'bg-orange-100 text-orange-800' },
  critical: { label: 'Critical', color: 'bg-red-100 text-red-800' },
};

export function AccessRequestList() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredRequests = mockRequests.filter((req) => {
    const matchesSearch =
      req.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      req.role.toLowerCase().includes(searchTerm.toLowerCase()) ||
      req.system.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || req.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Access Requests</h1>
          <p className="mt-1 text-sm text-gray-500">
            View and manage your access requests across all systems
          </p>
        </div>
        <Link
          to="/access-requests/new"
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          New Request
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white shadow rounded-lg p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search requests..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-5 w-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="in_review">In Review</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>
      </div>

      {/* Request Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm font-medium text-gray-500">Total Requests</div>
          <div className="mt-1 text-3xl font-semibold text-gray-900">{mockRequests.length}</div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm font-medium text-gray-500">Pending</div>
          <div className="mt-1 text-3xl font-semibold text-yellow-600">
            {mockRequests.filter((r) => r.status === 'pending').length}
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm font-medium text-gray-500">Approved</div>
          <div className="mt-1 text-3xl font-semibold text-green-600">
            {mockRequests.filter((r) => r.status === 'approved').length}
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm font-medium text-gray-500">Rejected</div>
          <div className="mt-1 text-3xl font-semibold text-red-600">
            {mockRequests.filter((r) => r.status === 'rejected').length}
          </div>
        </div>
      </div>

      {/* Requests Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Request ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Role / System
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Risk Level
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredRequests.map((request) => {
              const statusInfo = statusConfig[request.status];
              const riskInfo = riskConfig[request.riskLevel];
              const StatusIcon = statusInfo.icon;

              return (
                <tr key={request.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-primary-600">{request.id}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{request.role}</div>
                    <div className="text-sm text-gray-500">{request.system}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusInfo.color}`}
                    >
                      <StatusIcon className="h-3 w-3 mr-1" />
                      {statusInfo.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${riskInfo.color}`}
                    >
                      {riskInfo.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {request.requestDate}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <Link
                      to={`/access-requests/${request.id}`}
                      className="text-primary-600 hover:text-primary-900"
                    >
                      View Details
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredRequests.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No requests found matching your criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}
