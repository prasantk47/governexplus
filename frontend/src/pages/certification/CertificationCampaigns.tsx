import { useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  PlusIcon,
  PlayIcon,
  PauseIcon,
  CheckCircleIcon,
  ClockIcon,
  UserGroupIcon,
  CalendarIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

interface Campaign {
  id: string;
  name: string;
  type: 'user_access' | 'role_membership' | 'manager_review' | 'sensitive_access';
  status: 'active' | 'scheduled' | 'completed' | 'paused';
  startDate: string;
  endDate: string;
  progress: number;
  totalItems: number;
  completedItems: number;
  reviewers: number;
  owner: string;
}

const mockCampaigns: Campaign[] = [
  {
    id: 'CERT-2024-001',
    name: 'Q1 2024 User Access Review',
    type: 'user_access',
    status: 'active',
    startDate: '2024-01-01',
    endDate: '2024-01-31',
    progress: 78,
    totalItems: 1250,
    completedItems: 975,
    reviewers: 45,
    owner: 'Sarah Director',
  },
  {
    id: 'CERT-2024-002',
    name: 'SAP Sensitive Access Review',
    type: 'sensitive_access',
    status: 'active',
    startDate: '2024-01-15',
    endDate: '2024-02-15',
    progress: 35,
    totalItems: 180,
    completedItems: 63,
    reviewers: 12,
    owner: 'IT Security Team',
  },
  {
    id: 'CERT-2024-003',
    name: 'Manager Quarterly Review',
    type: 'manager_review',
    status: 'scheduled',
    startDate: '2024-02-01',
    endDate: '2024-02-28',
    progress: 0,
    totalItems: 850,
    completedItems: 0,
    reviewers: 32,
    owner: 'HR Director',
  },
  {
    id: 'CERT-2024-004',
    name: 'Admin Role Certification',
    type: 'role_membership',
    status: 'completed',
    startDate: '2023-12-01',
    endDate: '2023-12-31',
    progress: 100,
    totalItems: 95,
    completedItems: 95,
    reviewers: 8,
    owner: 'IT Manager',
  },
  {
    id: 'CERT-2024-005',
    name: 'Finance SOX Review',
    type: 'user_access',
    status: 'paused',
    startDate: '2024-01-10',
    endDate: '2024-02-10',
    progress: 45,
    totalItems: 320,
    completedItems: 144,
    reviewers: 15,
    owner: 'Finance Director',
  },
];

const typeConfig = {
  user_access: { label: 'User Access Review', color: 'bg-blue-100 text-blue-800' },
  role_membership: { label: 'Role Membership', color: 'bg-purple-100 text-purple-800' },
  manager_review: { label: 'Manager Review', color: 'bg-green-100 text-green-800' },
  sensitive_access: { label: 'Sensitive Access', color: 'bg-red-100 text-red-800' },
};

const statusConfig = {
  active: { label: 'Active', color: 'bg-green-100 text-green-800', icon: PlayIcon },
  scheduled: { label: 'Scheduled', color: 'bg-blue-100 text-blue-800', icon: CalendarIcon },
  completed: { label: 'Completed', color: 'bg-gray-100 text-gray-800', icon: CheckCircleIcon },
  paused: { label: 'Paused', color: 'bg-yellow-100 text-yellow-800', icon: PauseIcon },
};

export function CertificationCampaigns() {
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredCampaigns = mockCampaigns.filter(
    (c) => statusFilter === 'all' || c.status === statusFilter
  );

  const activeCampaigns = mockCampaigns.filter((c) => c.status === 'active').length;
  const totalPendingReviews = mockCampaigns
    .filter((c) => c.status === 'active')
    .reduce((acc, c) => acc + (c.totalItems - c.completedItems), 0);
  const avgProgress = Math.round(
    mockCampaigns
      .filter((c) => c.status === 'active')
      .reduce((acc, c) => acc + c.progress, 0) / activeCampaigns || 0
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Certification Campaigns</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage and monitor access certification campaigns
          </p>
        </div>
        <button
          onClick={() => toast.success('New Campaign wizard will open here')}
          className="btn-primary"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          New Campaign
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <PlayIcon className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">Active Campaigns</div>
              <div className="text-2xl font-bold text-gray-900">{activeCampaigns}</div>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <ClockIcon className="h-6 w-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">Pending Reviews</div>
              <div className="text-2xl font-bold text-gray-900">{totalPendingReviews}</div>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <ChartBarIcon className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">Avg. Progress</div>
              <div className="text-2xl font-bold text-gray-900">{avgProgress}%</div>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-lg">
              <UserGroupIcon className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">Total Reviewers</div>
              <div className="text-2xl font-bold text-gray-900">
                {mockCampaigns.reduce((acc, c) => acc + c.reviewers, 0)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          {['all', 'active', 'scheduled', 'paused', 'completed'].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-4 py-2 rounded-md text-sm font-medium ${
                statusFilter === status
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              } border border-gray-300`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Campaigns Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {filteredCampaigns.map((campaign) => {
          const typeInfo = typeConfig[campaign.type];
          const statusInfo = statusConfig[campaign.status];
          const StatusIcon = statusInfo.icon;

          return (
            <div
              key={campaign.id}
              className="bg-white shadow rounded-lg overflow-hidden hover:shadow-md transition-shadow"
            >
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusInfo.color}`}
                      >
                        <StatusIcon className="h-3 w-3 mr-1" />
                        {statusInfo.label}
                      </span>
                      <span
                        className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${typeInfo.color}`}
                      >
                        {typeInfo.label}
                      </span>
                    </div>
                    <h3 className="mt-2 text-lg font-semibold text-gray-900">{campaign.name}</h3>
                    <p className="text-sm text-gray-500">{campaign.id}</p>
                  </div>
                </div>

                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Progress</span>
                    <span className="font-medium text-gray-900">
                      {campaign.completedItems} / {campaign.totalItems}
                    </span>
                  </div>
                  <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        campaign.progress === 100
                          ? 'bg-green-500'
                          : campaign.progress > 50
                          ? 'bg-blue-500'
                          : 'bg-yellow-500'
                      }`}
                      style={{ width: `${campaign.progress}%` }}
                    />
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Start Date</span>
                    <p className="font-medium text-gray-900">{campaign.startDate}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">End Date</span>
                    <p className="font-medium text-gray-900">{campaign.endDate}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Reviewers</span>
                    <p className="font-medium text-gray-900">{campaign.reviewers}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Owner</span>
                    <p className="font-medium text-gray-900">{campaign.owner}</p>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-200 flex justify-between">
                  <Link
                    to={`/certification/${campaign.id}`}
                    className="text-sm font-medium text-primary-600 hover:text-primary-700"
                  >
                    View Details
                  </Link>
                  {campaign.status === 'active' && (
                    <Link
                      to="/certification/review"
                      className="text-sm font-medium text-green-600 hover:text-green-700"
                    >
                      Start Review
                    </Link>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {filteredCampaigns.length === 0 && (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <CalendarIcon className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-2 text-gray-500">No campaigns found</p>
        </div>
      )}
    </div>
  );
}
