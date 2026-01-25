import { useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  UserIcon,
  CalendarIcon,
  DocumentTextIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

interface ApprovalStep {
  id: string;
  approver: string;
  role: string;
  status: 'pending' | 'approved' | 'rejected' | 'waiting';
  date: string | null;
  comments: string | null;
}

interface RequestDetail {
  id: string;
  requester: string;
  requesterDept: string;
  requestDate: string;
  status: 'pending' | 'approved' | 'rejected';
  roles: { name: string; system: string; riskLevel: string }[];
  justification: string;
  duration: string;
  startDate: string;
  endDate: string | null;
  approvalSteps: ApprovalStep[];
  riskScore: number;
  sodConflicts: string[];
}

const mockRequest: RequestDetail = {
  id: 'REQ-2024-001',
  requester: 'John Smith',
  requesterDept: 'Finance',
  requestDate: '2024-01-15',
  status: 'pending',
  roles: [
    { name: 'SAP_FI_AP_CLERK', system: 'SAP ECC', riskLevel: 'low' },
    { name: 'SAP_FI_GL_ACCOUNTANT', system: 'SAP ECC', riskLevel: 'high' },
  ],
  justification:
    'Required for month-end closing activities. I need access to post journal entries and process accounts payable invoices for Q1 financial reporting.',
  duration: 'Permanent',
  startDate: '2024-01-20',
  endDate: null,
  riskScore: 65,
  sodConflicts: ['Create/Post GL Entry - Potential conflict between AP and GL posting'],
  approvalSteps: [
    {
      id: '1',
      approver: 'Sarah Manager',
      role: 'Direct Manager',
      status: 'approved',
      date: '2024-01-16',
      comments: 'Approved - legitimate business need for month-end activities',
    },
    {
      id: '2',
      approver: 'Risk Committee',
      role: 'Risk Approval',
      status: 'pending',
      date: null,
      comments: null,
    },
    {
      id: '3',
      approver: 'IT Security',
      role: 'Security Review',
      status: 'waiting',
      date: null,
      comments: null,
    },
  ],
};

const statusConfig = {
  pending: { color: 'bg-yellow-100 text-yellow-800', icon: ClockIcon },
  approved: { color: 'bg-green-100 text-green-800', icon: CheckCircleIcon },
  rejected: { color: 'bg-red-100 text-red-800', icon: XCircleIcon },
  waiting: { color: 'bg-gray-100 text-gray-500', icon: ClockIcon },
};

const riskConfig: Record<string, { color: string }> = {
  low: { color: 'bg-green-100 text-green-800' },
  medium: { color: 'bg-yellow-100 text-yellow-800' },
  high: { color: 'bg-orange-100 text-orange-800' },
  critical: { color: 'bg-red-100 text-red-800' },
};

export function AccessRequestDetail() {
  const { requestId } = useParams();
  const navigate = useNavigate();
  const [approvalComment, setApprovalComment] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const request = mockRequest;

  const handleApprove = async () => {
    if (isProcessing) return;
    setIsProcessing(true);
    try {
      await api.post(`/access-requests/${requestId}/approve`, {
        comment: approvalComment,
      });
      toast.success(`Request ${requestId} has been approved`);
      navigate('/approvals');
    } catch (error) {
      toast.error('Failed to approve request. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (isProcessing) return;
    if (!approvalComment.trim()) {
      toast.error('Please provide a reason for rejection');
      return;
    }
    setIsProcessing(true);
    try {
      await api.post(`/access-requests/${requestId}/reject`, {
        comment: approvalComment,
      });
      toast.success(`Request ${requestId} has been rejected`);
      navigate('/approvals');
    } catch (error) {
      toast.error('Failed to reject request. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Link
            to="/access-requests"
            className="mr-4 p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Access Request {requestId || request.id}
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              Submitted on {request.requestDate}
            </p>
          </div>
        </div>
        <span
          className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
            statusConfig[request.status].color
          }`}
        >
          {request.status.charAt(0).toUpperCase() + request.status.slice(1)}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Requester Info */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Requester Information</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center">
                <UserIcon className="h-5 w-5 text-gray-400 mr-3" />
                <div>
                  <div className="text-sm text-gray-500">Requester</div>
                  <div className="text-sm font-medium text-gray-900">{request.requester}</div>
                </div>
              </div>
              <div className="flex items-center">
                <DocumentTextIcon className="h-5 w-5 text-gray-400 mr-3" />
                <div>
                  <div className="text-sm text-gray-500">Department</div>
                  <div className="text-sm font-medium text-gray-900">{request.requesterDept}</div>
                </div>
              </div>
              <div className="flex items-center">
                <CalendarIcon className="h-5 w-5 text-gray-400 mr-3" />
                <div>
                  <div className="text-sm text-gray-500">Start Date</div>
                  <div className="text-sm font-medium text-gray-900">{request.startDate}</div>
                </div>
              </div>
              <div className="flex items-center">
                <ClockIcon className="h-5 w-5 text-gray-400 mr-3" />
                <div>
                  <div className="text-sm text-gray-500">Duration</div>
                  <div className="text-sm font-medium text-gray-900">{request.duration}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Requested Roles */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Requested Roles</h2>
            <div className="space-y-3">
              {request.roles.map((role, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div>
                    <div className="text-sm font-medium text-gray-900">{role.name}</div>
                    <div className="text-xs text-gray-500">{role.system}</div>
                  </div>
                  <span
                    className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      riskConfig[role.riskLevel].color
                    }`}
                  >
                    {role.riskLevel.charAt(0).toUpperCase() + role.riskLevel.slice(1)} Risk
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Business Justification */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Business Justification</h2>
            <p className="text-sm text-gray-700 bg-gray-50 p-4 rounded-lg">
              {request.justification}
            </p>
          </div>

          {/* SoD Conflicts */}
          {request.sodConflicts.length > 0 && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-6">
              <div className="flex items-start">
                <ShieldExclamationIcon className="h-6 w-6 text-orange-600 mt-0.5" />
                <div className="ml-3">
                  <h3 className="text-sm font-semibold text-orange-800">
                    Segregation of Duties Conflicts Detected
                  </h3>
                  <ul className="mt-2 list-disc list-inside space-y-1">
                    {request.sodConflicts.map((conflict, idx) => (
                      <li key={idx} className="text-sm text-orange-700">
                        {conflict}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Approval Workflow */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Approval Workflow</h2>
            <div className="space-y-4">
              {request.approvalSteps.map((step, idx) => {
                const StepIcon = statusConfig[step.status].icon;
                return (
                  <div key={step.id} className="flex items-start">
                    <div
                      className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                        step.status === 'approved'
                          ? 'bg-green-100'
                          : step.status === 'rejected'
                          ? 'bg-red-100'
                          : step.status === 'pending'
                          ? 'bg-yellow-100'
                          : 'bg-gray-100'
                      }`}
                    >
                      <StepIcon
                        className={`h-5 w-5 ${
                          step.status === 'approved'
                            ? 'text-green-600'
                            : step.status === 'rejected'
                            ? 'text-red-600'
                            : step.status === 'pending'
                            ? 'text-yellow-600'
                            : 'text-gray-400'
                        }`}
                      />
                    </div>
                    <div className="ml-4 flex-1">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-medium text-gray-900">{step.approver}</div>
                          <div className="text-xs text-gray-500">{step.role}</div>
                        </div>
                        <span
                          className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                            statusConfig[step.status].color
                          }`}
                        >
                          {step.status.charAt(0).toUpperCase() + step.status.slice(1)}
                        </span>
                      </div>
                      {step.comments && (
                        <p className="mt-2 text-sm text-gray-600 bg-gray-50 p-2 rounded">
                          "{step.comments}"
                        </p>
                      )}
                      {step.date && (
                        <p className="mt-1 text-xs text-gray-400">{step.date}</p>
                      )}
                    </div>
                    {idx < request.approvalSteps.length - 1 && (
                      <div className="absolute left-4 mt-8 w-0.5 h-8 bg-gray-200" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Risk Score */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-sm font-medium text-gray-900 mb-4">Request Risk Score</h3>
            <div className="flex items-center justify-center">
              <div className="relative w-24 h-24">
                <svg className="w-full h-full" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" strokeWidth="10" />
                  <circle
                    cx="50"
                    cy="50"
                    r="45"
                    fill="none"
                    stroke={
                      request.riskScore > 70
                        ? '#ef4444'
                        : request.riskScore > 40
                        ? '#f59e0b'
                        : '#22c55e'
                    }
                    strokeWidth="10"
                    strokeDasharray={`${request.riskScore * 2.83} ${100 * 2.83}`}
                    strokeLinecap="round"
                    transform="rotate(-90 50 50)"
                  />
                  <text
                    x="50"
                    y="50"
                    textAnchor="middle"
                    dy="0.3em"
                    className="text-2xl font-bold"
                    fill="#111827"
                  >
                    {request.riskScore}
                  </text>
                </svg>
              </div>
            </div>
            <p className="mt-3 text-xs text-center text-gray-500">
              {request.riskScore > 70
                ? 'High risk - requires additional review'
                : request.riskScore > 40
                ? 'Medium risk - standard approval'
                : 'Low risk'}
            </p>
          </div>

          {/* Approval Actions */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-sm font-medium text-gray-900 mb-4">Approval Decision</h3>
            <textarea
              value={approvalComment}
              onChange={(e) => setApprovalComment(e.target.value)}
              rows={3}
              placeholder="Add comments (optional)..."
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500 mb-4"
            />
            <div className="space-y-2">
              <button
                onClick={handleApprove}
                disabled={isProcessing}
                className="w-full flex items-center justify-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <CheckCircleIcon className="h-5 w-5 mr-2" />
                {isProcessing ? 'Processing...' : 'Approve Request'}
              </button>
              <button
                onClick={handleReject}
                disabled={isProcessing}
                className="w-full flex items-center justify-center px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <XCircleIcon className="h-5 w-5 mr-2" />
                {isProcessing ? 'Processing...' : 'Reject Request'}
              </button>
            </div>
          </div>

          {/* Quick Info */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-sm font-medium text-gray-900 mb-4">Request Timeline</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Submitted</span>
                <span className="font-medium text-gray-900">{request.requestDate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Days Pending</span>
                <span className="font-medium text-gray-900">2 days</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">SLA Status</span>
                <span className="font-medium text-green-600">On Track</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
