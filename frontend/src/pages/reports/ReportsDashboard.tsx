import { useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  MagnifyingGlassIcon,
  DocumentChartBarIcon,
  ClockIcon,
  ArrowDownTrayIcon,
  PlayIcon,
  CalendarIcon,
  ChartBarIcon,
  ShieldExclamationIcon,
  UserGroupIcon,
  ClipboardDocumentCheckIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

interface Report {
  id: string;
  name: string;
  description: string;
  category: 'compliance' | 'risk' | 'access' | 'audit';
  format: 'pdf' | 'excel' | 'csv';
  lastRun: string;
  schedule: string | null;
  createdBy: string;
}

interface ScheduledReport {
  id: string;
  reportName: string;
  schedule: string;
  nextRun: string;
  recipients: string[];
  status: 'active' | 'paused';
}

const mockReports: Report[] = [
  {
    id: 'RPT-001',
    name: 'SoD Violations Summary',
    description: 'Overview of all segregation of duties violations by risk level and status',
    category: 'risk',
    format: 'pdf',
    lastRun: '2024-01-19',
    schedule: 'Weekly',
    createdBy: 'System',
  },
  {
    id: 'RPT-002',
    name: 'User Access Review',
    description: 'Complete list of user access rights across all systems',
    category: 'access',
    format: 'excel',
    lastRun: '2024-01-18',
    schedule: 'Monthly',
    createdBy: 'System',
  },
  {
    id: 'RPT-003',
    name: 'Certification Campaign Status',
    description: 'Progress and completion rates for active certification campaigns',
    category: 'compliance',
    format: 'pdf',
    lastRun: '2024-01-20',
    schedule: null,
    createdBy: 'Compliance Team',
  },
  {
    id: 'RPT-004',
    name: 'Firefighter Session Audit',
    description: 'Detailed log of all firefighter/emergency access sessions',
    category: 'audit',
    format: 'excel',
    lastRun: '2024-01-17',
    schedule: 'Daily',
    createdBy: 'System',
  },
  {
    id: 'RPT-005',
    name: 'High-Risk Users Report',
    description: 'Users with elevated risk scores and their access details',
    category: 'risk',
    format: 'pdf',
    lastRun: '2024-01-15',
    schedule: 'Weekly',
    createdBy: 'Risk Management',
  },
  {
    id: 'RPT-006',
    name: 'Access Request History',
    description: 'Complete history of access requests with approval workflow details',
    category: 'access',
    format: 'csv',
    lastRun: '2024-01-16',
    schedule: null,
    createdBy: 'System',
  },
  {
    id: 'RPT-007',
    name: 'Role Assignment Matrix',
    description: 'Matrix showing role assignments across users and systems',
    category: 'access',
    format: 'excel',
    lastRun: '2024-01-14',
    schedule: 'Monthly',
    createdBy: 'System',
  },
  {
    id: 'RPT-008',
    name: 'Compliance Summary Report',
    description: 'Executive summary of compliance status across all controls',
    category: 'compliance',
    format: 'pdf',
    lastRun: '2024-01-12',
    schedule: 'Quarterly',
    createdBy: 'Compliance Team',
  },
];

const mockScheduledReports: ScheduledReport[] = [
  {
    id: 'SCH-001',
    reportName: 'SoD Violations Summary',
    schedule: 'Every Monday at 8:00 AM',
    nextRun: '2024-01-22 08:00',
    recipients: ['compliance@company.com', 'risk@company.com'],
    status: 'active',
  },
  {
    id: 'SCH-002',
    reportName: 'Firefighter Session Audit',
    schedule: 'Daily at 6:00 AM',
    nextRun: '2024-01-21 06:00',
    recipients: ['security@company.com'],
    status: 'active',
  },
  {
    id: 'SCH-003',
    reportName: 'User Access Review',
    schedule: 'First of every month at 9:00 AM',
    nextRun: '2024-02-01 09:00',
    recipients: ['it-admin@company.com', 'audit@company.com'],
    status: 'active',
  },
];

const categoryConfig = {
  compliance: { color: 'bg-blue-100 text-blue-800', icon: ClipboardDocumentCheckIcon, label: 'Compliance' },
  risk: { color: 'bg-red-100 text-red-800', icon: ShieldExclamationIcon, label: 'Risk' },
  access: { color: 'bg-green-100 text-green-800', icon: UserGroupIcon, label: 'Access' },
  audit: { color: 'bg-purple-100 text-purple-800', icon: DocumentChartBarIcon, label: 'Audit' },
};

export function ReportsDashboard() {
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [activeTab, setActiveTab] = useState<'reports' | 'scheduled'>('reports');

  const filteredReports = mockReports.filter((report) => {
    const matchesSearch =
      report.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      report.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || report.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const handleRunReport = async (reportId: string) => {
    const toastId = toast.loading('Generating report...');
    try {
      await api.post(`/reports/${reportId}/run`);
      toast.success('Report generation started. You will be notified when it is ready.', { id: toastId });
    } catch (error) {
      toast.error('Failed to run report. Please try again.', { id: toastId });
    }
  };

  const handleDownload = async (reportId: string) => {
    const toastId = toast.loading('Preparing download...');
    try {
      const response = await api.get(`/reports/${reportId}/download`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report-${reportId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Download started', { id: toastId });
    } catch (error) {
      toast.error('Failed to download report. Please try again.', { id: toastId });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
          <p className="mt-1 text-sm text-gray-500">
            Generate, schedule, and download compliance and audit reports
          </p>
        </div>
        <button
          onClick={() => toast.success('Opening custom report builder...')}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
        >
          <DocumentChartBarIcon className="h-5 w-5 mr-2" />
          Create Custom Report
        </button>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <DocumentChartBarIcon className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">Available Reports</div>
              <div className="text-2xl font-bold text-gray-900">{mockReports.length}</div>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <CalendarIcon className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">Scheduled</div>
              <div className="text-2xl font-bold text-green-600">{mockScheduledReports.length}</div>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-lg">
              <ClockIcon className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">Run Today</div>
              <div className="text-2xl font-bold text-purple-600">3</div>
            </div>
          </div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="flex items-center">
            <div className="p-2 bg-orange-100 rounded-lg">
              <ChartBarIcon className="h-6 w-6 text-orange-600" />
            </div>
            <div className="ml-4">
              <div className="text-sm font-medium text-gray-500">This Week</div>
              <div className="text-2xl font-bold text-orange-600">12</div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('reports')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'reports'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <DocumentChartBarIcon className="h-5 w-5 inline mr-2" />
              Report Library
            </button>
            <button
              onClick={() => setActiveTab('scheduled')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'scheduled'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <CalendarIcon className="h-5 w-5 inline mr-2" />
              Scheduled Reports ({mockScheduledReports.length})
            </button>
          </nav>
        </div>

        {activeTab === 'reports' && (
          <div className="p-6">
            {/* Filters */}
            <div className="flex flex-col lg:flex-row gap-4 mb-6">
              <div className="flex-1 relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search reports..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="all">All Categories</option>
                <option value="compliance">Compliance</option>
                <option value="risk">Risk</option>
                <option value="access">Access</option>
                <option value="audit">Audit</option>
              </select>
            </div>

            {/* Reports Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredReports.map((report) => {
                const catConfig = categoryConfig[report.category];
                const CategoryIcon = catConfig.icon;
                return (
                  <div key={report.id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start">
                        <div className={`p-2 ${catConfig.color.split(' ')[0]} rounded-lg`}>
                          <CategoryIcon className={`h-5 w-5 ${catConfig.color.split(' ')[1]}`} />
                        </div>
                        <div className="ml-3">
                          <h3 className="text-sm font-medium text-gray-900">{report.name}</h3>
                          <p className="mt-1 text-xs text-gray-500">{report.description}</p>
                          <div className="mt-2 flex items-center gap-2">
                            <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${catConfig.color}`}>
                              {catConfig.label}
                            </span>
                            <span className="text-xs text-gray-400">
                              Last run: {report.lastRun}
                            </span>
                            {report.schedule && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-50 text-xs text-blue-700">
                                <CalendarIcon className="h-3 w-3 mr-1" />
                                {report.schedule}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="mt-4 flex items-center gap-2">
                      <button
                        onClick={() => handleRunReport(report.id)}
                        className="inline-flex items-center px-3 py-1.5 border border-transparent rounded text-xs font-medium text-white bg-primary-600 hover:bg-primary-700"
                      >
                        <PlayIcon className="h-3 w-3 mr-1" />
                        Run Now
                      </button>
                      <button
                        onClick={() => handleDownload(report.id)}
                        className="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded text-xs font-medium text-gray-700 bg-white hover:bg-gray-50"
                      >
                        <ArrowDownTrayIcon className="h-3 w-3 mr-1" />
                        Download Last
                      </button>
                      <Link
                        to={`/reports/${report.id}`}
                        className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-primary-600 hover:text-primary-700"
                      >
                        View Details
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>

            {filteredReports.length === 0 && (
              <div className="text-center py-12">
                <DocumentChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
                <p className="mt-2 text-gray-500">No reports found matching your criteria</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'scheduled' && (
          <div className="p-6">
            <div className="space-y-4">
              {mockScheduledReports.map((schedule) => (
                <div key={schedule.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">{schedule.reportName}</h3>
                      <div className="mt-1 flex items-center gap-4 text-xs text-gray-500">
                        <span className="flex items-center">
                          <CalendarIcon className="h-3 w-3 mr-1" />
                          {schedule.schedule}
                        </span>
                        <span className="flex items-center">
                          <ClockIcon className="h-3 w-3 mr-1" />
                          Next: {schedule.nextRun}
                        </span>
                      </div>
                      <div className="mt-2 text-xs text-gray-500">
                        Recipients: {schedule.recipients.join(', ')}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span
                        className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          schedule.status === 'active'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {schedule.status.charAt(0).toUpperCase() + schedule.status.slice(1)}
                      </span>
                      <button
                        onClick={() => toast.success(`Editing schedule ${schedule.id}...`)}
                        className="text-primary-600 hover:text-primary-700 text-sm"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => toast.success(`Schedule ${schedule.id} deleted`)}
                        className="text-red-600 hover:text-red-700 text-sm"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
