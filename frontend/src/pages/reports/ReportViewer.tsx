import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  ArrowLeftIcon,
  ArrowDownTrayIcon,
  PlayIcon,
  ClockIcon,
  DocumentChartBarIcon,
  TableCellsIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';

interface ReportExecution {
  id: string;
  date: string;
  status: 'completed' | 'failed' | 'running';
  duration: string;
  records: number;
  downloadUrl: string;
}

const mockReport = {
  id: 'RPT-001',
  name: 'SoD Violations Summary',
  description: 'Overview of all segregation of duties violations by risk level and status',
  category: 'Risk',
  format: 'PDF',
  createdBy: 'System',
  createdDate: '2023-06-15',
  lastModified: '2024-01-10',
  schedule: 'Weekly - Every Monday at 8:00 AM',
  recipients: ['compliance@company.com', 'risk@company.com'],
};

const mockExecutions: ReportExecution[] = [
  {
    id: 'EXEC-001',
    date: '2024-01-20 08:00',
    status: 'completed',
    duration: '2m 15s',
    records: 145,
    downloadUrl: '#',
  },
  {
    id: 'EXEC-002',
    date: '2024-01-13 08:00',
    status: 'completed',
    duration: '2m 08s',
    records: 142,
    downloadUrl: '#',
  },
  {
    id: 'EXEC-003',
    date: '2024-01-06 08:00',
    status: 'completed',
    duration: '2m 22s',
    records: 138,
    downloadUrl: '#',
  },
  {
    id: 'EXEC-004',
    date: '2023-12-30 08:00',
    status: 'failed',
    duration: '0m 45s',
    records: 0,
    downloadUrl: '#',
  },
  {
    id: 'EXEC-005',
    date: '2023-12-23 08:00',
    status: 'completed',
    duration: '2m 10s',
    records: 135,
    downloadUrl: '#',
  },
];

const mockPreviewData = [
  { rule: 'Create Vendor / Execute Payment', violations: 12, riskLevel: 'Critical', users: 8 },
  { rule: 'Create PO / Release PO', violations: 8, riskLevel: 'High', users: 5 },
  { rule: 'Post GL / Approve GL', violations: 5, riskLevel: 'Critical', users: 3 },
  { rule: 'Create User / Assign Roles', violations: 2, riskLevel: 'Critical', users: 2 },
  { rule: 'Deploy Code / Approve Deployment', violations: 3, riskLevel: 'High', users: 2 },
];

const statusConfig = {
  completed: { color: 'bg-green-100 text-green-800', label: 'Completed' },
  failed: { color: 'bg-red-100 text-red-800', label: 'Failed' },
  running: { color: 'bg-yellow-100 text-yellow-800', label: 'Running' },
};

export function ReportViewer() {
  const { reportId } = useParams();
  const [activeTab, setActiveTab] = useState<'preview' | 'history' | 'settings'>('preview');
  const [isRunning, setIsRunning] = useState(false);
  const report = mockReport;

  const handleRunNow = async () => {
    if (isRunning) return;
    setIsRunning(true);
    const toastId = toast.loading('Generating report...');
    try {
      await api.post(`/reports/${reportId || report.id}/run`);
      toast.success('Report generation started successfully', { id: toastId });
    } catch (error) {
      toast.error('Failed to run report. Please try again.', { id: toastId });
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Link
            to="/reports"
            className="mr-4 p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <div className="flex items-center">
            <div className="p-3 bg-red-100 rounded-lg mr-4">
              <DocumentChartBarIcon className="h-8 w-8 text-red-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{report.name}</h1>
              <p className="text-sm text-gray-500">{report.description}</p>
            </div>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleRunNow}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
          >
            <PlayIcon className="h-5 w-5 mr-2" />
            Run Now
          </button>
          <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
            <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
            Download Latest
          </button>
        </div>
      </div>

      {/* Report Info Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm text-gray-500">Category</div>
          <div className="mt-1 text-lg font-semibold text-gray-900">{report.category}</div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm text-gray-500">Format</div>
          <div className="mt-1 text-lg font-semibold text-gray-900">{report.format}</div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm text-gray-500">Schedule</div>
          <div className="mt-1 text-lg font-semibold text-gray-900">Weekly</div>
        </div>
        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm text-gray-500">Last Run</div>
          <div className="mt-1 text-lg font-semibold text-gray-900">Jan 20, 2024</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('preview')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'preview'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <TableCellsIcon className="h-5 w-5 inline mr-2" />
              Data Preview
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'history'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <ClockIcon className="h-5 w-5 inline mr-2" />
              Execution History
            </button>
            <button
              onClick={() => setActiveTab('settings')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'settings'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <FunnelIcon className="h-5 w-5 inline mr-2" />
              Report Settings
            </button>
          </nav>
        </div>

        {activeTab === 'preview' && (
          <div className="p-6">
            {/* Chart Placeholder */}
            <div className="mb-6 p-6 bg-gray-50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-900 mb-4">Violations by Risk Level</h3>
              <div className="flex items-end justify-between h-48 gap-4">
                <div className="flex-1 flex flex-col items-center">
                  <div className="w-full bg-red-500 rounded-t" style={{ height: '80%' }} />
                  <span className="mt-2 text-xs text-gray-500">Critical (19)</span>
                </div>
                <div className="flex-1 flex flex-col items-center">
                  <div className="w-full bg-orange-500 rounded-t" style={{ height: '50%' }} />
                  <span className="mt-2 text-xs text-gray-500">High (11)</span>
                </div>
                <div className="flex-1 flex flex-col items-center">
                  <div className="w-full bg-yellow-500 rounded-t" style={{ height: '20%' }} />
                  <span className="mt-2 text-xs text-gray-500">Medium (0)</span>
                </div>
                <div className="flex-1 flex flex-col items-center">
                  <div className="w-full bg-green-500 rounded-t" style={{ height: '10%' }} />
                  <span className="mt-2 text-xs text-gray-500">Low (0)</span>
                </div>
              </div>
            </div>

            {/* Data Table */}
            <h3 className="text-sm font-medium text-gray-900 mb-4">Report Data (Top 5 Rules)</h3>
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rule
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Violations
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Risk Level
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Affected Users
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {mockPreviewData.map((row, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{row.rule}</td>
                    <td className="px-6 py-4 text-sm text-gray-900">{row.violations}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          row.riskLevel === 'Critical'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-orange-100 text-orange-800'
                        }`}
                      >
                        {row.riskLevel}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">{row.users}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="p-6">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Execution Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Records
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {mockExecutions.map((execution) => {
                  const statusInfo = statusConfig[execution.status];
                  return (
                    <tr key={execution.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-900">{execution.date}</td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${statusInfo.color}`}
                        >
                          {statusInfo.label}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">{execution.duration}</td>
                      <td className="px-6 py-4 text-sm text-gray-900">{execution.records}</td>
                      <td className="px-6 py-4 text-right">
                        {execution.status === 'completed' && (
                          <button className="inline-flex items-center text-primary-600 hover:text-primary-700 text-sm">
                            <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
                            Download
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="p-6 space-y-6">
            {/* Schedule Settings */}
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-4">Schedule Configuration</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-500 mb-2">Frequency</label>
                  <select className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500">
                    <option>Daily</option>
                    <option selected>Weekly</option>
                    <option>Monthly</option>
                    <option>Quarterly</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-500 mb-2">Day</label>
                  <select className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500">
                    <option selected>Monday</option>
                    <option>Tuesday</option>
                    <option>Wednesday</option>
                    <option>Thursday</option>
                    <option>Friday</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-500 mb-2">Time</label>
                  <input
                    type="time"
                    defaultValue="08:00"
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-500 mb-2">Timezone</label>
                  <select className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500">
                    <option>UTC</option>
                    <option selected>US/Eastern</option>
                    <option>US/Pacific</option>
                    <option>Europe/London</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Recipients */}
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-4">Email Recipients</h3>
              <div className="space-y-2">
                {report.recipients.map((email, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-sm text-gray-900">{email}</span>
                    <button className="text-red-600 hover:text-red-700 text-sm">Remove</button>
                  </div>
                ))}
                <input
                  type="email"
                  placeholder="Add email recipient..."
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            </div>

            {/* Filters */}
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-4">Report Filters</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-500 mb-2">Risk Level</label>
                  <select className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500">
                    <option selected>All</option>
                    <option>Critical Only</option>
                    <option>High and Critical</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-500 mb-2">Status</label>
                  <select className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500">
                    <option selected>All</option>
                    <option>Open Only</option>
                    <option>Mitigated Only</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="pt-4 flex justify-end gap-3">
              <button className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
                Cancel
              </button>
              <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm font-medium">
                Save Changes
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
