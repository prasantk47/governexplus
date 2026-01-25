import { useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  InboxIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

interface ApprovalItem {
  id: string;
  type: 'access_request' | 'role_change' | 'certification' | 'firefighter';
  requester: string;
  requesterDept: string;
  summary: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  submittedDate: string;
  dueDate: string;
  priority: 'normal' | 'high' | 'urgent';
  sodConflicts: boolean;
}

const mockApprovals: ApprovalItem[] = [
  {
    id: 'REQ-2024-001',
    type: 'access_request',
    requester: 'John Smith',
    requesterDept: 'Finance',
    summary: 'SAP_FI_AP_CLERK, SAP_FI_GL_ACCOUNTANT',
    riskLevel: 'high',
    submittedDate: '2024-01-15',
    dueDate: '2024-01-18',
    priority: 'urgent',
    sodConflicts: true,
  },
  {
    id: 'REQ-2024-002',
    type: 'access_request',
    requester: 'Emily Davis',
    requesterDept: 'Sales',
    summary: 'SALESFORCE_ADMIN',
    riskLevel: 'high',
    submittedDate: '2024-01-16',
    dueDate: '2024-01-19',
    priority: 'high',
    sodConflicts: false,
  },
  {
    id: 'CERT-2024-015',
    type: 'certification',
    requester: 'System',
    requesterDept: 'IT',
    summary: 'Q1 User Access Certification - Finance Team',
    riskLevel: 'medium',
    submittedDate: '2024-01-10',
    dueDate: '2024-01-25',
    priority: 'normal',
    sodConflicts: false,
  },
  {
    id: 'FF-2024-008',
    type: 'firefighter',
    requester: 'Mike Brown',
    requesterDept: 'IT Operations',
    summary: 'Emergency AWS Admin Access',
    riskLevel: 'critical',
    submittedDate: '2024-01-17',
    dueDate: '2024-01-17',
    priority: 'urgent',
    sodConflicts: false,
  },
  {
    id: 'REQ-2024-003',
    type: 'access_request',
    requester: 'Lisa Chen',
    requesterDept: 'HR',
    summary: 'WORKDAY_HR_ADMIN',
    riskLevel: 'medium',
    submittedDate: '2024-01-14',
    dueDate: '2024-01-21',
    priority: 'normal',
    sodConflicts: false,
  },
  {
    id: 'ROLE-2024-001',
    type: 'role_change',
    requester: 'IT Security',
    requesterDept: 'IT',
    summary: 'AWS_DEVELOPER role modification',
    riskLevel: 'medium',
    submittedDate: '2024-01-16',
    dueDate: '2024-01-23',
    priority: 'normal',
    sodConflicts: false,
  },
];

const typeConfig = {
  access_request: { color: 'bg-blue-100 text-blue-800', label: 'Access Request' },
  role_change: { color: 'bg-purple-100 text-purple-800', label: 'Role Change' },
  certification: { color: 'bg-indigo-100 text-indigo-800', label: 'Certification' },
  firefighter: { color: 'bg-orange-100 text-orange-800', label: 'Firefighter' },
};

const riskConfig = {
  low: { color: 'bg-green-100 text-green-800' },
  medium: { color: 'bg-yellow-100 text-yellow-800' },
  high: { color: 'bg-orange-100 text-orange-800' },
  critical: { color: 'bg-red-100 text-red-800' },
};

const priorityConfig = {
  normal: { color: 'text-gray-500' },
  high: { color: 'text-orange-600' },
  urgent: { color: 'text-red-600' },
};

export function ApprovalInbox() {
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');

  const filteredApprovals = mockApprovals.filter((item) => {
    const matchesSearch =
      item.requester.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.summary.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = typeFilter === 'all' || item.type === typeFilter;
    const matchesPriority = priorityFilter === 'all' || item.priority === priorityFilter;
    return matchesSearch && matchesType && matchesPriority;
  });

  const urgentCount = mockApprovals.filter((a) => a.priority === 'urgent').length;
  const highRiskCount = mockApprovals.filter(
    (a) => a.riskLevel === 'high' || a.riskLevel === 'critical'
  ).length;
  const overdueCount = mockApprovals.filter(
    (a) => new Date(a.dueDate) < new Date()
  ).length;

  const handleQuickApprove = async (id: string) => {
    try {
      await api.post(`/approvals/${id}/approve`, { quickApproval: true });
      toast.success(`Request ${id} has been approved`);
    } catch (error) {
      toast.error('Failed to approve request. Please try again.');
    }
  };

  const handleQuickReject = async (id: string) => {
    try {
      await api.post(`/approvals/${id}/reject`, { quickReject: true });
      toast.success(`Request ${id} has been rejected`);
    } catch (error) {
      toast.error('Failed to reject request. Please try again.');
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="page-title">Approval Inbox</h1>
        <p className="page-subtitle">
          Pending approvals requiring your action
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="stat-card-accent border-blue-400">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-blue">
              <InboxIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Total Pending</div>
              <div className="stat-value">{mockApprovals.length}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-red">
              <ExclamationTriangleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Urgent</div>
              <div className="stat-value text-red-500">{urgentCount}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-orange">
              <ExclamationTriangleIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">High Risk</div>
              <div className="stat-value text-orange-500">{highRiskCount}</div>
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="flex items-center gap-4">
            <div className="stat-icon stat-icon-gray">
              <ClockIcon className="h-5 w-5" />
            </div>
            <div>
              <div className="stat-label">Overdue</div>
              <div className="stat-value">{overdueCount}</div>
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
                placeholder="Search by requester, ID, or summary..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <FunnelIcon className="h-4 w-4 text-gray-400" />
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="text-xs border border-gray-300 rounded-md px-2 py-1.5 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="all">All Types</option>
                <option value="access_request">Access Requests</option>
                <option value="role_change">Role Changes</option>
                <option value="certification">Certifications</option>
                <option value="firefighter">Firefighter</option>
              </select>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="text-xs border border-gray-300 rounded-md px-2 py-1.5 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="all">All Priorities</option>
                <option value="urgent">Urgent</option>
                <option value="high">High</option>
                <option value="normal">Normal</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Approval Items */}
      <div className="space-y-3">
        {filteredApprovals.map((item) => {
          const typeInfo = typeConfig[item.type];
          const riskInfo = riskConfig[item.riskLevel];
          const priorityInfo = priorityConfig[item.priority];

          return (
            <div key={item.id} className="card">
              <div className="card-body">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${typeInfo.color}`}>
                        {typeInfo.label}
                      </span>
                      <span className={`inline-flex px-1.5 py-0.5 rounded text-xs font-medium ${riskInfo.color}`}>
                        {item.riskLevel.charAt(0).toUpperCase() + item.riskLevel.slice(1)}
                      </span>
                      {item.sodConflicts && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                          <ExclamationTriangleIcon className="h-3 w-3 mr-0.5" />
                          SoD
                        </span>
                      )}
                      {item.priority !== 'normal' && (
                        <span className={`text-xs font-medium ${priorityInfo.color}`}>
                          {item.priority.toUpperCase()}
                        </span>
                      )}
                    </div>
                    <Link
                      to={`/access-requests/${item.id}`}
                      className="text-sm font-semibold text-gray-900 hover:text-primary-600"
                    >
                      {item.id}
                    </Link>
                    <p className="mt-0.5 text-xs text-gray-600">{item.summary}</p>
                    <div className="mt-1.5 flex items-center gap-3 text-xs text-gray-500">
                      <span>{item.requester}</span>
                      <span>•</span>
                      <span>{item.requesterDept}</span>
                      <span>•</span>
                      <span>Due: {item.dueDate}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 ml-4">
                    <Link
                      to={`/access-requests/${item.id}`}
                      className="btn-secondary"
                    >
                      <EyeIcon className="h-3.5 w-3.5 mr-1" />
                      Review
                    </Link>
                    <button
                      onClick={() => handleQuickApprove(item.id)}
                      className="inline-flex items-center px-2.5 py-1 border border-transparent rounded-md text-xs font-medium text-white bg-green-600 hover:bg-green-700"
                    >
                      <CheckCircleIcon className="h-3.5 w-3.5 mr-0.5" />
                      Approve
                    </button>
                    <button
                      onClick={() => handleQuickReject(item.id)}
                      className="inline-flex items-center px-2.5 py-1 border border-transparent rounded-md text-xs font-medium text-white bg-red-600 hover:bg-red-700"
                    >
                      <XCircleIcon className="h-3.5 w-3.5 mr-0.5" />
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        {filteredApprovals.length === 0 && (
          <div className="card">
            <div className="card-body text-center py-8">
              <InboxIcon className="mx-auto h-8 w-8 text-gray-400" />
              <p className="mt-2 text-xs text-gray-500">No pending approvals matching your criteria</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
