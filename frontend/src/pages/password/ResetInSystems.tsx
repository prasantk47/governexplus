import { useState } from 'react';
import {
  ServerStackIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

interface SystemAccount {
  id: string;
  systemName: string;
  systemType: string;
  accountId: string;
  lastPasswordChange: string;
  status: 'active' | 'expired' | 'locked';
}

const mockSystems: SystemAccount[] = [
  {
    id: '1',
    systemName: 'SAP ERP Production',
    systemType: 'SAP S/4HANA',
    accountId: 'JSMITH01',
    lastPasswordChange: '2024-01-15',
    status: 'active',
  },
  {
    id: '2',
    systemName: 'Active Directory',
    systemType: 'Microsoft AD',
    accountId: 'john.smith@company.com',
    lastPasswordChange: '2024-01-10',
    status: 'active',
  },
  {
    id: '3',
    systemName: 'Oracle Financials',
    systemType: 'Oracle Cloud',
    accountId: 'JSMITH',
    lastPasswordChange: '2023-12-01',
    status: 'expired',
  },
  {
    id: '4',
    systemName: 'Salesforce CRM',
    systemType: 'Salesforce',
    accountId: 'john.smith@company.com',
    lastPasswordChange: '2024-01-20',
    status: 'active',
  },
  {
    id: '5',
    systemName: 'ServiceNow ITSM',
    systemType: 'ServiceNow',
    accountId: 'john.smith',
    lastPasswordChange: '2023-11-15',
    status: 'locked',
  },
];

const statusConfig = {
  active: { color: 'bg-green-100 text-green-800', label: 'Active' },
  expired: { color: 'bg-yellow-100 text-yellow-800', label: 'Password Expired' },
  locked: { color: 'bg-red-100 text-red-800', label: 'Locked' },
};

export function ResetInSystems() {
  const [selectedSystems, setSelectedSystems] = useState<string[]>([]);
  const [isResetting, setIsResetting] = useState(false);
  const [resetResults, setResetResults] = useState<Map<string, 'success' | 'failed' | 'pending'>>(new Map());

  const handleSelectAll = () => {
    if (selectedSystems.length === mockSystems.length) {
      setSelectedSystems([]);
    } else {
      setSelectedSystems(mockSystems.map((s) => s.id));
    }
  };

  const handleSelect = (id: string) => {
    setSelectedSystems((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const handleResetPasswords = async () => {
    setIsResetting(true);
    const results = new Map<string, 'success' | 'failed' | 'pending'>();

    // Set all selected as pending
    selectedSystems.forEach((id) => results.set(id, 'pending'));
    setResetResults(new Map(results));

    // Simulate async password reset for each system
    for (const id of selectedSystems) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      // Simulate 90% success rate
      const success = Math.random() > 0.1;
      results.set(id, success ? 'success' : 'failed');
      setResetResults(new Map(results));
    }

    setIsResetting(false);
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Password Reset in Systems</h1>
          <p className="page-subtitle">
            Reset your password across multiple connected systems
          </p>
        </div>
        <button
          onClick={handleResetPasswords}
          disabled={selectedSystems.length === 0 || isResetting}
          className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ArrowPathIcon className={`h-4 w-4 mr-1.5 ${isResetting ? 'animate-spin' : ''}`} />
          {isResetting ? 'Resetting...' : `Reset Selected (${selectedSystems.length})`}
        </button>
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <ServerStackIcon className="h-5 w-5 text-blue-400" />
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">How it works</h3>
            <div className="mt-1 text-sm text-blue-700">
              <ol className="list-decimal list-inside space-y-1">
                <li>Select the systems where you want to reset your password</li>
                <li>Click "Reset Selected" to initiate password reset</li>
                <li>New passwords will be sent to your registered email</li>
              </ol>
            </div>
          </div>
        </div>
      </div>

      {/* Systems Table */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h2 className="section-title">Your System Accounts</h2>
          <button
            onClick={handleSelectAll}
            className="text-xs text-primary-600 hover:text-primary-700 font-medium"
          >
            {selectedSystems.length === mockSystems.length ? 'Deselect All' : 'Select All'}
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left">
                  <input
                    type="checkbox"
                    checked={selectedSystems.length === mockSystems.length}
                    onChange={handleSelectAll}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  System
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Account ID
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Last Changed
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Reset Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {mockSystems.map((system) => (
                <tr key={system.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedSystems.includes(system.id)}
                      onChange={() => handleSelect(system.id)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-lg bg-gray-100 flex items-center justify-center">
                        <ServerStackIcon className="h-4 w-4 text-gray-500" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">{system.systemName}</div>
                        <div className="text-xs text-gray-500">{system.systemType}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 font-mono">{system.accountId}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{system.lastPasswordChange}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                        statusConfig[system.status].color
                      }`}
                    >
                      {statusConfig[system.status].label}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {resetResults.has(system.id) && (
                      <span className="flex items-center gap-1 text-xs">
                        {resetResults.get(system.id) === 'pending' && (
                          <>
                            <ClockIcon className="h-4 w-4 text-yellow-500 animate-pulse" />
                            <span className="text-yellow-600">Resetting...</span>
                          </>
                        )}
                        {resetResults.get(system.id) === 'success' && (
                          <>
                            <CheckCircleIcon className="h-4 w-4 text-green-500" />
                            <span className="text-green-600">Success</span>
                          </>
                        )}
                        {resetResults.get(system.id) === 'failed' && (
                          <>
                            <ExclamationCircleIcon className="h-4 w-4 text-red-500" />
                            <span className="text-red-600">Failed</span>
                          </>
                        )}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Password Policy Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="card-body">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                <ClockIcon className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Password Expiry</p>
                <p className="text-xs text-gray-500">90 days policy</p>
              </div>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-green-100 flex items-center justify-center">
                <CheckCircleIcon className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Synced Systems</p>
                <p className="text-xs text-gray-500">{mockSystems.length} connected</p>
              </div>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-yellow-100 flex items-center justify-center">
                <ExclamationCircleIcon className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Expiring Soon</p>
                <p className="text-xs text-gray-500">2 accounts</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
